# Odoo Fusion Integration

This module provides integration between Odoo and Autodesk Fusion 360, allowing seamless synchronization of designs and components between the two systems.

## Features

- Sync Fusion 360 designs with Odoo
- Automatically create products from Fusion components
- Track version changes and updates
- Manage product variants based on Fusion configurations
- Store Fusion metadata (UUIDs, version numbers, etc.)
- Configure default product settings for Fusion imports

## Installation

1. Install this module in your Odoo instance
2. Install the companion Fusion 360 add-in
3. Configure the integration settings in Odoo

## Configuration

### Required Settings

1. Go to Manufacturing > Configuration > Settings
2. Find the "Fusion Integration" section
3. Configure:
   - Design reference sequence
   - Product reference sequence
   - Default product category

### Security Groups

- Fusion User: Can view Fusion designs and products
- Fusion Manager: Can configure integration settings

## Usage

### Syncing Designs

1. Open a design in Fusion 360
2. Enable sync in the Fusion add-in
3. Save the design to trigger synchronization
4. View the synced design in Odoo under Manufacturing > Fusion > Designs

### Managing Products

- Products are automatically created from Fusion components
- Product references are generated using the configured sequence
- Products inherit the default category set in configuration
- Product variants are created based on Fusion configurations

### Attributes

- View Fusion-specific attributes under Manufacturing > Fusion > Attributes
- Track which attributes were created from Fusion configurations

## Technical Details

### Models

- `fusion.design`: Stores Fusion design metadata
- `fusion.user`: Manages Fusion user information
- `product.template`: Extended with Fusion-specific fields
- `product.attribute`: Extended to track Fusion origin

### Integration Points

- Uses Fusion 360 API for design data
- Stores component UUIDs for reliable syncing
- Tracks version numbers for change detection
- Maintains bidirectional references between systems

## Support

For issues and feature requests, please contact:
- Website: https://jaco.tech
- Email: [support email]

## License

LGPL-3
