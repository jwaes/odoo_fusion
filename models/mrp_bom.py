# -*- coding: utf-8 -*-
"""Bill of Materials synchronization with Fusion 360.

This module extends the mrp.bom model to handle synchronization with Fusion 360.
It receives a standardized component structure and updates the BOM accordingly.

Data Structure from Fusion
-------------------------
The BOM structure received from Fusion follows this format:
{
    'components': [
        {
            'fusion_uuid': str,      # Unique identifier of the component in Fusion
            'configuration_id': str,  # Configuration ID if component is configured, None otherwise
            'quantity': int,         # Number of occurrences in the assembly
            'name': str,             # Component name from Fusion
            'part_number': str       # Part number from Fusion
        },
        ...
    ]
}

The module will:
1. Find or create the BOM for the product
2. Update quantities of existing components
3. Add new components that weren't in the BOM
4. Remove components that are no longer in the assembly
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def create_or_update_from_fusion(self, product_id, bom_lines):
        """Create or update BoM from Fusion data."""
        _logger.info(f"Creating/updating BoM for product ID: {product_id}")
        
        # Convert product_id to recordset
        product = self.env['product.product'].browse(product_id)
        
        # Find existing BoM for this product
        bom = self.search([('product_id', '=', product_id)], limit=1)
        
        # Prepare BoM values
        vals = {
            'product_id': product_id,
            'product_tmpl_id': product.product_tmpl_id.id,  # Access product_tmpl_id from recordset
            'type': 'normal',
            'bom_line_ids': bom_lines
        }
        
        if not bom:
            _logger.info("Creating new BoM")
            bom = self.create(vals)
        else:
            _logger.info("Updating existing BoM")
            bom.write(vals)
        
        return bom.id

    @api.model
    def sync_from_fusion(self, product_tmpl_id, structure):
        """Sync BOM from Fusion 360 structure.
        
        Args:
            product_tmpl_id: ID of the product template
            structure: Dictionary containing component structure as described in module docstring
            
        Returns:
            int: ID of the created/updated BOM
            
        Example structure:
            {
                'components': [
                    {
                        'fusion_uuid': '123e4567-e89b-12d3-a456-426614174000',
                        'configuration_id': 'config-001',
                        'quantity': 2,
                        'name': 'Part A',
                        'part_number': 'PA-001'
                    },
                    {
                        'fusion_uuid': '987fcdeb-51d3-a456-426614174000',
                        'configuration_id': None,
                        'quantity': 1,
                        'name': 'Part B',
                        'part_number': 'PB-001'
                    }
                ]
            }
        """
        try:
            # Find or create BOM
            bom = self.search([('product_tmpl_id', '=', product_tmpl_id)], limit=1)
            if not bom:
                _logger.info(f"Creating new BOM for product template {product_tmpl_id}")
                bom = self.create({
                    'product_tmpl_id': product_tmpl_id,
                    'type': 'normal'
                })

            # Track which lines to keep
            current_lines = {line.id: False for line in bom.bom_line_ids}
            
            # Process each component
            for comp in structure['components']:
                _logger.debug(f"Processing component: {comp['name']} (UUID: {comp['fusion_uuid']})")
                
                # Find product variant
                product = self.env['product.template'].get_product_variant_by_uuid(
                    comp['fusion_uuid'], 
                    comp['configuration_id']
                )
                if not product:
                    _logger.warning(f"Could not find product for UUID: {comp['fusion_uuid']}")
                    continue

                # Find existing line
                line = bom.bom_line_ids.filtered(
                    lambda l: l.product_id.id == product.id
                )
                
                if line:
                    _logger.debug(f"Updating existing BOM line for {comp['name']}")
                    # Update quantity
                    line.product_qty = comp['quantity']
                    current_lines[line.id] = True
                else:
                    _logger.debug(f"Creating new BOM line for {comp['name']}")
                    # Create new line
                    self.env['mrp.bom.line'].create({
                        'bom_id': bom.id,
                        'product_id': product.id,
                        'product_qty': comp['quantity']
                    })

            # Remove lines that weren't in the structure
            lines_to_remove = [
                line_id for line_id, keep in current_lines.items() 
                if not keep
            ]
            if lines_to_remove:
                _logger.info(f"Removing {len(lines_to_remove)} obsolete BOM lines")
                self.env['mrp.bom.line'].browse(lines_to_remove).unlink()

            _logger.info(f"Successfully synced BOM {bom.id} from Fusion")
            return bom.id

        except Exception as e:
            _logger.error(f"Error syncing BOM from Fusion: {str(e)}")
            raise UserError(f"Failed to sync BOM: {str(e)}")
