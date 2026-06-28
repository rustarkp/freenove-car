#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=${1:-/mnt/backup/private}
DATE=$(date +%Y%m%d-%H%M%S)
ARCHIVE_FILE="${BACKUP_DIR}/private-data-${DATE}.tar.gz"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

if [ ! -d "$HOME/.local/share/robot" ]; then
  mkdir -p "$HOME/.local/share/robot"
fi

# Keep private data off GitHub. This archive can be stored on an external drive or SD card backup.
# Add or remove paths here as your project grows.
TAR_PATHS=(
  "$HOME/.local/share/robot"
  "$HOME/.config/robot"
  "$HOME/.ssh"
)

# Create an archive only from paths that exist.
FILES_TO_BACKUP=()
for path in "${TAR_PATHS[@]}"; do
  if [ -e "$path" ]; then
    FILES_TO_BACKUP+=("$path")
  fi
done

if [ ${#FILES_TO_BACKUP[@]} -eq 0 ]; then
  echo "No private data paths found to back up." >&2
  exit 0
fi

tar -czf "$ARCHIVE_FILE" "${FILES_TO_BACKUP[@]}"

echo "Private data backup created: $ARCHIVE_FILE"
