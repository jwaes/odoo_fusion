from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def create_or_update_from_fusion(self, product_id, bom_lines):
        """Create or update BoM from Fusion data."""
        _logger.info(f"Creating/updating BoM for product ID: {product_id}")
        
        # Find existing BoM for this product
        bom = self.search([('product_id', '=', product_id)], limit=1)
        
        # Prepare BoM values
        vals = {
            'product_id': product_id,
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
