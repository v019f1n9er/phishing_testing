# Update script for Windows PowerShell (located in scripts/)
# Pulls latest code, builds image, preserves DB and restarts container

# repoDir is parent directory of the scripts folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoDir = Split-Path -Parent $scriptDir
Set-Location $repoDir

$containerName = 'phishing-dashboard-container'
$imageName = 'phishing-dashboard'

Write-Host "Pulling latest code from git..."
git pull
if ($LASTEXITCODE -ne 0) { Write-Host "git pull failed"; exit $LASTEXITCODE }

# Get existing envs from running container if present
$envs = @{}
$containerExists = (docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch $containerName) -ne $null
if ($containerExists) {
    Write-Host "Found existing container: $containerName — reading envs..."
    $raw = docker inspect $containerName | ConvertFrom-Json
    foreach ($e in $raw[0].Config.Env) {
        if ($e -match "^([^=]+)=(.*)$") { $envs[$matches[1]] = $matches[2] }
    }
}

# Prompt for build args (default to previous container env or hardcoded defaults)
$defaultSecret = if ($envs.ContainsKey('SECRET_KEY')) { $envs['SECRET_KEY'] } else { 'phishing-dashboard-2026-super-secret-key' }
$defaultSecure = if ($envs.ContainsKey('SESSION_COOKIE_SECURE')) { $envs['SESSION_COOKIE_SECURE'] } else { 'False' }
$defaultAdmin = if ($envs.ContainsKey('ADMIN_USER')) { $envs['ADMIN_USER'] } else { 'admin' }
$defaultPass = if ($envs.ContainsKey('ADMIN_PASS')) { $envs['ADMIN_PASS'] } else { 'passwd123' }

$secret = Read-Host "SECRET_KEY (press Enter to use default)"
if ([string]::IsNullOrWhiteSpace($secret)) { $secret = $defaultSecret }
$secure = Read-Host "SESSION_COOKIE_SECURE (True/False) (press Enter to use default)"
if ([string]::IsNullOrWhiteSpace($secure)) { $secure = $defaultSecure }
$admin = Read-Host "ADMIN_USER (press Enter to use default)"
if ([string]::IsNullOrWhiteSpace($admin)) { $admin = $defaultAdmin }
$pass = Read-Host -AsSecureString "ADMIN_PASS (will not echo; press Enter to use default)"
if ($pass.Length -eq 0) { $plainPass = $defaultPass } else { $plainPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass)) }

# Ensure DB file is present on host to persist across container restart
$hostDbPath = Join-Path $repoDir 'phishing_data.db'
if (-Not (Test-Path $hostDbPath)) {
    if ($containerExists) {
        Write-Host "DB not found on host — copying from existing container..."
        docker cp "$containerName:/app/phishing_data.db" "$hostDbPath" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Unable to copy DB from container; creating empty DB file on host.\nEnsure the app will initialize DB on first run."
            New-Item -Path $hostDbPath -ItemType File | Out-Null
        }
    } else {
        Write-Host "DB not found on host and no container exists — creating empty DB file."
        New-Item -Path $hostDbPath -ItemType File | Out-Null
    }
} else {
    Write-Host "Host DB found at $hostDbPath — will be preserved."
}

# Build image
Write-Host "Building Docker image '$imageName'..."
docker build `
    --build-arg SECRET_KEY=$("$secret") `
    --build-arg SESSION_COOKIE_SECURE=$("$secure") `
    --build-arg ADMIN_USER=$("$admin") `
    --build-arg ADMIN_PASS=$("$plainPass") `
    -t $imageName .
if ($LASTEXITCODE -ne 0) { Write-Host "docker build failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }

# Stop and remove existing container if exists
if ($containerExists) {
    Write-Host "Stopping and removing existing container $containerName..."
    docker stop $containerName | Out-Null
    docker rm $containerName | Out-Null
}

# Run new container with host DB bind-mounted to /app/phishing_data.db
Write-Host "Starting new container $containerName (DB preserved at host path)..."
$pwdEscaped = (Get-Item $repoDir).FullName
# Docker on Windows may require converting path format for mounting; use ${pwd} direct.
docker run -d -p 8080:8080 --name $containerName -v "${pwdEscaped}:/app:rw" phishing-dashboard
if ($LASTEXITCODE -ne 0) { Write-Host "docker run failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host "Update completed — container started."

Write-Host "Note: DB file is preserved on host: $hostDbPath"