#!/usr/bin/env bash
# Simple S3 backup script for ghw.db
# Expects /etc/ghw/env to contain S3_BUCKET and AWS credentials or instance role

set -euo pipefail
ROOT_DIR=/opt/ghw
ENV_FILE=/etc/ghw/env
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if [ -z "${S3_BUCKET:-}" ]; then
  echo "S3_BUCKET not set in $ENV_FILE, skipping backup"
  exit 0
fi

TS=$(date +"%F-%H%M")
DB_FILE="$ROOT_DIR/ghw.db"
if [ ! -f "$DB_FILE" ]; then
  echo "DB file not found: $DB_FILE"
  exit 1
fi

aws s3 cp "$DB_FILE" "s3://${S3_BUCKET}/ghw/ghw-${TS}.db"
echo "Uploaded ghw-${TS}.db to s3://${S3_BUCKET}/ghw/"
