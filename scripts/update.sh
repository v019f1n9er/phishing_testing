#!/usr/bin/env bash
# Update script for Unix-like shells (located in scripts/)
# Pulls latest code, builds image, preserves DB and restarts container

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

CONTAINER_NAME=phishing-dashboard-container
IMAGE_NAME=phishing-dashboard

echo "Pulling latest code from git..."
git pull || { echo "git pull failed"; exit 1; }

# Get envs from existing container if present
container_exists=false
if [ "$(docker ps -a --format '{{.Names}}' | grep -w "$CONTAINER_NAME")" ]; then
  container_exists=true
  echo "Found existing container: $CONTAINER_NAME — reading envs..."
  mapfile -t raw_envs < <(docker inspect $CONTAINER_NAME --format '{{range .Config.Env}}{{println .}}{{end}}')
fi

# Defaults
default_secret='phishing-dashboard-2026-super-secret-key'
default_secure='False'
default_admin='admin'
default_pass='passwd123'

if $container_exists; then
  for e in "${raw_envs[@]}"; do
    key=${e%%=*}
    value=${e#*=}
    case "$key" in
      SECRET_KEY) default_secret="$value" ;;
      SESSION_COOKIE_SECURE) default_secure="$value" ;;
      ADMIN_USER) default_admin="$value" ;;
      ADMIN_PASS) default_pass="$value" ;;
    esac
  done
fi

read -p "SECRET_KEY (press Enter to use default): " secret
secret=${secret:-$default_secret}
read -p "SESSION_COOKIE_SECURE (True/False) (press Enter to use default): " secure
secure=${secure:-$default_secure}
read -p "ADMIN_USER (press Enter to use default): " admin
admin=${admin:-$default_admin}
read -s -p "ADMIN_PASS (will not echo; press Enter to use default): " pass
echo
pass=${pass:-$default_pass}

# Ensure DB file is present on host
HOST_DB_PATH="$REPO_DIR/phishing_data.db"
if [ ! -f "$HOST_DB_PATH" ]; then
  if $container_exists; then
    echo "DB not found on host — copying from existing container..."
    docker cp "$CONTAINER_NAME:/app/phishing_data.db" "$HOST_DB_PATH" 2>/dev/null || {
      echo "Unable to copy DB from container; creating empty DB file on host."
      touch "$HOST_DB_PATH"
    }
  else
    echo "DB not found on host and no container exists — creating empty DB file."
    touch "$HOST_DB_PATH"
  fi
else
  echo "Host DB found at $HOST_DB_PATH — will be preserved."
fi

# Build image
echo "Building Docker image '$IMAGE_NAME'..."
docker build \
  --build-arg SECRET_KEY="$secret" \
  --build-arg SESSION_COOKIE_SECURE="$secure" \
  --build-arg ADMIN_USER="$admin" \
  --build-arg ADMIN_PASS="$pass" \
  -t $IMAGE_NAME . || { echo "docker build failed"; exit 1; }

# Stop and remove existing container
if $container_exists; then
  echo "Stopping and removing existing container $CONTAINER_NAME..."
  docker stop $CONTAINER_NAME || true
  docker rm $CONTAINER_NAME || true
fi

# Run new container with host DB bind-mounted to /app
echo "Starting new container $CONTAINER_NAME (DB preserved at host path)..."
docker run -d -p 8080:8080 --name $CONTAINER_NAME -v "$HOST_DB_PATH:/app/phishing_data.db:rw" $IMAGE_NAME || { echo "docker run failed"; exit 1; }

echo "Update completed — container started."
echo "Note: DB file is preserved on host: $HOST_DB_PATH"