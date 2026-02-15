#!/usr/bin/env bash
# Interactive build script for Unix-like shells (located in scripts/)
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

DEFAULT_SECRET='phishing-dashboard-2026-super-secret-key'
DEFAULT_SECURE='False'
DEFAULT_ADMIN='admin'
DEFAULT_PASS='passwd123'

# image version
IMAGE_TAG='1.0'

read -p "SECRET_KEY (press Enter to use default: $DEFAULT_SECRET): " SECRET
SECRET=${SECRET:-$DEFAULT_SECRET}

read -p "SESSION_COOKIE_SECURE (True/False) (default: $DEFAULT_SECURE): " SECURE
SECURE=${SECURE:-$DEFAULT_SECURE}

read -p "ADMIN_USER (default: $DEFAULT_ADMIN): " ADMIN
ADMIN=${ADMIN:-$DEFAULT_ADMIN}

read -s -p "ADMIN_PASS (press Enter to use default): " PASS
echo
PASS=${PASS:-$DEFAULT_PASS}

IMAGE_NAME='phishing-dashboard'
echo "Building Docker image '$IMAGE_NAME:$IMAGE_TAG' with provided values..."

docker build \
  --build-arg SECRET_KEY="$SECRET" \
  --build-arg SESSION_COOKIE_SECURE="$SECURE" \
  --build-arg ADMIN_USER="$ADMIN" \
  --build-arg ADMIN_PASS="$PASS" \
  -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -ne 0 ]; then
  echo "docker build failed"
  exit 1
fi

# Persist chosen values as defaults for future updates
DEFAULTS_FILE="$REPO_DIR/.build_defaults"
cat > "$DEFAULTS_FILE" <<EOF
SECRET_KEY=$SECRET
SESSION_COOKIE_SECURE=$SECURE
ADMIN_USER=$ADMIN
ADMIN_PASS=$PASS
IMAGE_TAG=$IMAGE_TAG
EOF

echo "Build finished. Saved defaults to $DEFAULTS_FILE"
echo "Run the container, for example:"
echo "docker run -d -p 8080:8080 --name phishing-dashboard-container -v \"$REPO_DIR/phishing_data.db:/app/phishing_data.db:rw\" ${IMAGE_NAME}:${IMAGE_TAG}"