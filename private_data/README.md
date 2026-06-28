# Private data storage

This directory is reserved for sensitive local data that should not be committed to GitHub.

## Recommended layout
- faces/: face images, embeddings, and labels for family-member recognition
- maps/: home navigation maps, occupancy grids, or room metadata
- models/: local trained model files and checkpoints
- config/: private runtime configuration, secrets, and local overrides

## Safety rules
- Keep all sensitive files here.
- Do not commit this directory to GitHub.
- Back up this directory regularly to an external drive or backup SD card.
- Use separate access controls if you later add biometric or home-layout data.
