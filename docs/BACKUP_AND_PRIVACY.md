# Backup and privacy plan

## 1. Full system image backup to SD card or external drive

Use this when you want to preserve the exact current Raspberry Pi OS installation, including the OS, applications, settings, and your project checkout.

### Recommended approach
- Keep a spare microSD card or USB drive mounted at /mnt/backup.
- Run the image backup script as root.

```bash
sudo ./scripts/backup_sd_image.sh /mnt/backup
```

This creates a disk image file that can be restored later with Raspberry Pi Imager or dd.

## 2. Private-data backup for face data and home-map data

Sensitive data should stay out of GitHub. Keep it in a private location on the Pi and archive it separately.

### Recommended private-data locations
- $HOME/.local/share/robot
- $HOME/.config/robot
- ./private_data/ (local repository folder for faces, maps, models, and config)

### Run the private-data backup

```bash
./scripts/backup_private_data.sh /mnt/backup/private
```

This creates a compressed tar archive that you can copy to a second SD card or external drive.

## 3. Security guidance

- Do not commit facial data, home-map data, or trained model files to GitHub.
- Keep those files in a private directory and add them to a local ignore rule if needed.
- Use a strong user password and consider enabling SSH keys only.
- Consider encrypting the backup drive if it contains private biometric or home-layout data.

## 4. Suggested schedule

- Weekly: full private-data backup
- Monthly or before major changes: full OS image backup
- Before any major experiment: create a fresh private-data backup
