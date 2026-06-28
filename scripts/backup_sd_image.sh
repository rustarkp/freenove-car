#!/usr/bin/env bash
set -euo pipefail

DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=${1:-/mnt/backup}
IMAGE_FILE="${BACKUP_DIR}/raspberrypi-car-${DATE}.img"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

if [ $EUID -ne 0 ]; then
  echo "Please run as root or with sudo." >&2
  exit 1
fi

ROOT_PARTITION=$(mount | grep ' on / ' | cut -d' ' -f1)
if [ -z "$ROOT_PARTITION" ]; then
  echo "Could not determine root partition." >&2
  exit 1
fi

DEVICE=$(echo "$ROOT_PARTITION" | sed 's/[0-9]*$//')
if [ -z "$DEVICE" ]; then
  echo "Could not determine disk device from $ROOT_PARTITION" >&2
  exit 1
fi

echo "Backing up disk: $DEVICE"
echo "Output image: $IMAGE_FILE"

# Create a compressed image of the whole disk.
# This captures the current OS installation, including software and config.
# Note: use a larger external disk or USB drive for the backup target.

sudo dd if="$DEVICE" of="$IMAGE_FILE" bs=4M status=progress conv=fsync
sudo gzip -f "$IMAGE_FILE"

echo "Backup complete: ${IMAGE_FILE}.gz"
