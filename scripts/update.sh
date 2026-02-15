#!/usr/bin/env bash
# Update script for Unix-like shells (located in scripts/)
# Pulls latest code, builds image, preserves DB and restarts container

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

CONTAINER_NAME=phishing-dashboard-container
IMAGE_NAME=phishing-dashboard
DEFAULTS_FILE="$REPO_DIR/.build_defaults"

echo "Pulling latest code from git..."
git pull || { echo "git pull failed"; exit 1; }

# Get defaults: first from .build_defaults (saved by build.sh), fall back to hardcoded defaults
default_secret='phishing-dashboard-2026-super-secret-key'
default_secure='False'
default_admin='admin'
default_pass='passwd123'
default_image_tag='1.0'

if [ -f "$DEFAULTS_FILE" ]; then
  echo "Using saved defaults from $DEFAULTS_FILE (these came from the last build)."
  # shellcheck disable=SC1090
  source "$DEFAULTS_FILE"
  default_secret=${SECRET_KEY:-$default_secret}
  default_secure=${SESSION_COOKIE_SECURE:-$default_secure}
  default_admin=${ADMIN_USER:-$default_admin}
  default_pass=${ADMIN_PASS:-$default_pass}
  default_image_tag=${IMAGE_TAG:-$default_image_tag}
else
  echo "No saved defaults file found; will use container envs (if present) or hardcoded defaults."
fi

# If a container exists, offer its envs as current values but still use saved defaults as defaults
container_exists=false
if [ "$(docker ps -a --format '{{.Names}}' | grep -w "$CONTAINER_NAME")" ]; then
  container_exists=true
  echo "Found existing container: $CONTAINER_NAME — reading its environment values (used only as current values)."
  mapfile -t raw_envs < <(docker inspect $CONTAINER_NAME --format '{{range .Config.Env}}{{println .}}{{end}}')
  for e in "${raw_envs[@]}"; do
    key=${e%%=*}
    value=${e#*=}
    case "$key" in
      SECRET_KEY) container_secret="$value" ;;
      SESSION_COOKIE_SECURE) container_secure="$value" ;;
      ADMIN_USER) container_admin="$value" ;;
      ADMIN_PASS) container_pass="$value" ;;
    esac
  done
fi

read -p "SECRET_KEY (press Enter to use default: $default_secret): " secret
secret=${secret:-$default_secret}
read -p "SESSION_COOKIE_SECURE (True/False) (press Enter to use default: $default_secure): " secure
secure=${secure:-$default_secure}
read -p "ADMIN_USER (press Enter to use default: $default_admin): " admin
admin=${admin:-$default_admin}
read -s -p "ADMIN_PASS (press Enter to use default): " pass
echo
pass=${pass:-$default_pass}
IMAGE_TAG=${IMAGE_TAG:-$default_image_tag}

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
echo "Building Docker image '$IMAGE_NAME:${IMAGE_TAG}'..."
docker build \
  --build-arg SECRET_KEY="$secret" \
  --build-arg SESSION_COOKIE_SECURE="$secure" \
  --build-arg ADMIN_USER="$admin" \
  --build-arg ADMIN_PASS="$pass" \
  -t ${IMAGE_NAME}:${IMAGE_TAG} . || { echo "docker build failed"; exit 1; }

# Stop and remove existing container
if $container_exists; then
  echo "Stopping and removing existing container $CONTAINER_NAME to avoid conflicts..."
  docker stop $CONTAINER_NAME || true
  docker rm $CONTAINER_NAME || true
fi

# Run new container with host DB bind-mounted to /app
echo "Starting new container $CONTAINER_NAME (DB preserved at host path)..."
docker run -d -p 8080:8080 --name $CONTAINER_NAME -v "$HOST_DB_PATH:/app/phishing_data.db:rw" ${IMAGE_NAME}:${IMAGE_TAG} || { echo "docker run failed"; exit 1; }

echo "Update completed — container started using image ${IMAGE_NAME}:${IMAGE_TAG}."
echo "Note: DB file is preserved on host: $HOST_DB_PATH"
echo "Defaults used for this update were taken from: ${DEFAULTS_FILE} (if present)."