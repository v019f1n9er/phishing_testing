# Phishing testing — redirect logger (multi-format outputs) - ADDITIONAL FILES

This set contains alternative filenames so they are added to the repository without replacing existing files.

Files added:
- sec_multi.py — main server (same functionality as discussed previously)
- requirements_extra.txt — dependencies for sec_multi.py
- Dockerfile_multi — Dockerfile to build image using the new filenames
- .dockerignore_extra — dockerignore for the extra files
- README_MULTI.md — this README

Usage instructions are the same as described previously. To build and run the Docker image using these extra files:

1. Build:
   docker build -t phishing-redirect-multi -f Dockerfile_multi .

2. Run:
   docker run -d -p 8080:8080 -e TARGET_URL="https://example.com" -v "$(pwd)/data":/data --name phishing-redirect-multi phishing-redirect-multi

Logs will be persisted in ./data (logs.db, logs.csv, logs.txt, logs.sql)

Notes:
- If you want these files moved/renamed or merged into the main filenames, tell me and I will create a PR that replaces or updates the originals.

Thank you.
