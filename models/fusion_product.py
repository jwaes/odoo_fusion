from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class FusionProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    is_fusion_attribute = fields.Boolean('Created from Fusion', default=False, readonly=True)

class FusionProduct(models.Model):
    _inherit = 'product.template'
    
    fusion_uuid = fields.Char('Fusion UUID')
    fusion_design_id = fields.Many2one('fusion.design', string='Fusion Design')
    fusion_version = fields.Integer('Fusion Version')
    
    def action_view_variants(self):
        self.ensure_one()
        action = self.env.ref('product.product_variant_action').read()[0]
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        action['context'] = {
            'default_product_tmpl_id': self.id,
            'create': False
        }
        return action
    
    @api.model
    def create_or_update_from_fusion(self, fusion_data):
        """Create or update Odoo product from Fusion component data."""
        product = self.search([('fusion_uuid', '=', fusion_data['fusion_uuid'])], limit=1)
        
        # Log the current name if product exists
        if product:
            _logger.info(f'Updating product {product.name} (UUID: {fusion_data["fusion_uuid"]})')
            _logger.info(f'Current name: {product.name}')
            _logger.info(f'New name from Fusion: {fusion_data["name"]}')
        
        vals = {
            'name': fusion_data['name'],
            'fusion_uuid': fusion_data['fusion_uuid'],
            'description': fusion_data['description'],
            'fusion_version': fusion_data.get('version_number'),
        }
        
        # Only set default_code if it doesn't exist yet
        if not product or not product.default_code:
            vals['default_code'] = self.env['ir.sequence'].next_by_code('fusion.product.default.code')
        
        if not product:
            _logger.info(f'Creating new product with name: {fusion_data["name"]}')
            product = self.create(vals)
        else:
            _logger.info(f'Updating product with new values: {vals}')
            product.write(vals)
            _logger.info(f'Updated product name to: {product.name}')
            
        # Handle configurations as product variants
        if fusion_data.get('is_configuration') and fusion_data.get('configurations'):
            # Create product attributes if needed
            attr_vals = self.env['product.attribute.value']
            config_attr = self.env['product.attribute'].search([('name', '=', 'Configuration')], limit=1)
            if not config_attr:
                config_attr = self.env['product.attribute'].create({
                    'name': 'Configuration',
                    'create_variant': 'always',
                    'is_fusion_attribute': True
                })
            
            # Create attribute values for each configuration
            for config in fusion_data['configurations']:
                value = attr_vals.search([
                    ('name', '=', config['name']),
                    ('attribute_id', '=', config_attr.id)
                ], limit=1)
                if not value:
                    value = attr_vals.create({
                        'name': config['name'],
                        'attribute_id': config_attr.id
                    })
                
                # Create or update product variant
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product.id),
                    ('product_template_attribute_value_ids.product_attribute_value_id', '=', value.id)
                ], limit=1)
                
                if not variant:
                    # Create product attribute line if needed
                    attr_line = self.env['product.template.attribute.line'].search([
                        ('product_tmpl_id', '=', product.id),
                        ('attribute_id', '=', config_attr.id)
                    ], limit=1)
                    if not attr_line:
                        attr_line = self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': product.id,
                            'attribute_id': config_attr.id,
                            'value_ids': [(4, value.id)]
                        })
                    else:
                        attr_line.write({'value_ids': [(4, value.id)]})
        
        return product
