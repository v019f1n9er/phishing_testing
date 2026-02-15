# Interactive build script for Windows PowerShell (located in scripts/)
# Prompts user for values and runs `docker build` with build-args

# repoDir is parent directory of the scripts folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoDir = Split-Path -Parent $scriptDir
Set-Location $repoDir

$defaultSecret = 'phishing-dashboard-2026-super-secret-key'
$defaultSecure = 'False'
$defaultAdmin = 'admin'
$defaultPass = 'passwd123'

$secret = Read-Host "SECRET_KEY (press Enter to use default: $defaultSecret)"
if ([string]::IsNullOrWhiteSpace($secret)) { $secret = $defaultSecret }

$secure = Read-Host "SESSION_COOKIE_SECURE (True/False) (default: $defaultSecure)"
if ([string]::IsNullOrWhiteSpace($secure)) { $secure = $defaultSecure }

$admin = Read-Host "ADMIN_USER (default: $defaultAdmin)"
if ([string]::IsNullOrWhiteSpace($admin)) { $admin = $defaultAdmin }

$pass = Read-Host -AsSecureString "ADMIN_PASS (will not echo; press Enter to use default)"
if ($pass.Length -eq 0) {
    $plainPass = $defaultPass
} else {
    $plainPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass))
}

Write-Host "Building Docker image 'phishing-dashboard' with provided values..."

docker build `
    --build-arg SECRET_KEY=$("$secret") `
    --build-arg SESSION_COOKIE_SECURE=$("$secure") `
    --build-arg ADMIN_USER=$("$admin") `
    --build-arg ADMIN_PASS=$("$plainPass") `
    -t phishing-dashboard .

if ($LASTEXITCODE -ne 0) { Write-Host "docker build failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host "Build finished. Run the container, for example:`n docker run -d -p 8080:8080 --name phishing-dashboard-container phishing-dashboard"