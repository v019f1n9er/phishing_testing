FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Build-time args with sensible defaults; these can be overridden with
# `--build-arg` during `docker build` or via the provided build scripts.
ARG SECRET_KEY=phishing-dashboard-2026-super-secret-key
ARG SESSION_COOKIE_SECURE=False
ARG ADMIN_USER=admin
ARG ADMIN_PASS=passwd123

# Экспортируем в ENV, чтобы приложение могло читать значения из os.environ
ENV SECRET_KEY=${SECRET_KEY}
ENV SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE}
ENV ADMIN_USER=${ADMIN_USER}
ENV ADMIN_PASS=${ADMIN_PASS}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]
