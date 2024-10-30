from odoo import models, fields, api
import logging
import re

_logger = logging.getLogger(__name__)

class FusionProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    is_fusion_attribute = fields.Boolean('Created from Fusion', default=False, readonly=True)

class FusionProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    
    fusion_uuid = fields.Char('Fusion UUID')
    
    _sql_constraints = [
        ('fusion_uuid_uniq', 'unique(fusion_uuid)', 'Fusion UUID must be unique!')
    ]

class FusionProduct(models.Model):
    _inherit = 'product.template'
    
    fusion_uuid = fields.Char('Fusion UUID')
    fusion_version = fields.Integer('Fusion Version')
    fusion_generated_default_code = fields.Char('Fusion Generated Default Code', readonly=True, copy=False)
    fusion_web_url = fields.Char('Fusion Web URL', readonly=True)
    fusion_shared_link_active = fields.Boolean('Fusion Shared Link Active', readonly=True)
    fusion_shared_link_url = fields.Char('Fusion Shared Link URL', readonly=True)
    fusion_shared_link_download = fields.Boolean('Fusion Shared Link Download', readonly=True)
    fusion_date_created = fields.Datetime('Fusion Created Date', readonly=True)
    fusion_date_modified = fields.Datetime('Fusion Modified Date', readonly=True)
    fusion_last_sync = fields.Datetime('Last Fusion Sync', readonly=True)
    fusion_last_updated_by_id = fields.Many2one('fusion.user', string='Last Updated By', readonly=True)

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
        _logger.info(f"Processing Fusion component: {fusion_data['name']}")
        product = self.search([('fusion_uuid', '=', fusion_data['fusion_uuid'])], limit=1)
        
        vals = {
            'name': fusion_data['name'],
            'fusion_uuid': fusion_data['fusion_uuid'],
            'description': fusion_data['description'],
            'fusion_version': fusion_data.get('version_number'),
            'fusion_web_url': fusion_data['fusion_web_url'],
            'fusion_date_created': fusion_data['date_created'],
            'fusion_date_modified': fusion_data['date_modified'],
            'fusion_last_sync': fields.Datetime.now(),
        }

        # Handle shared link data
        shared_link = fusion_data.get('shared_link', {})
        vals.update({
            'fusion_shared_link_active': shared_link.get('is_shared', False),
            'fusion_shared_link_url': shared_link.get('url', ''),
            'fusion_shared_link_download': shared_link.get('allow_download', False),
        })
        
        # Generate and store the default code
        if not product or not product.fusion_generated_default_code:
            vals['fusion_generated_default_code'] = self.env['ir.sequence'].next_by_code('fusion.product.default.code')
        
        # Get default category from settings
        if not product:
            default_category_id = int(self.env['ir.config_parameter'].sudo().get_param('odoo_fusion.default_category_id', '0'))
            if default_category_id:
                vals['categ_id'] = default_category_id
        
        if not product:
            _logger.info("Creating new product")
            product = self.create(vals)
        else:
            _logger.info(f"Updating existing product: {product.name}")
            product.write(vals)

        # Set default_code for single-variant products
        if product.product_variant_count == 1:
            product.product_variant_ids.default_code = product.fusion_generated_default_code
        
        # Handle configurations
        if fusion_data.get('is_configuration') and fusion_data.get('configurations'):
            _logger.info(f"Processing configurations: {len(fusion_data['configurations'])}")
            
            # Create or get configuration attribute
            config_attr = self.env['product.attribute'].search([
                ('name', '=', 'Configuration'),
                ('is_fusion_attribute', '=', True)
            ], limit=1)
            
            if not config_attr:
                config_attr = self.env['product.attribute'].create({
                    'name': 'Configuration',
                    'create_variant': 'always',
                    'is_fusion_attribute': True
                })
                _logger.info("Created Configuration attribute")
            
            # Create attribute values for each configuration
            attr_vals = self.env['product.attribute.value']
            value_ids = []
            
            for config in fusion_data['configurations']:
                # Search by Fusion UUID without company
                value = attr_vals.with_context(active_test=False).search([
                    ('fusion_uuid', '=', config['fusion_uuid']),
                    ('attribute_id', '=', config_attr.id)
                ], limit=1)
                
                if not value:
                    value = attr_vals.create({
                        'name': config['name'],
                        'fusion_uuid': config['fusion_uuid'],
                        'attribute_id': config_attr.id
                    })
                    _logger.info(f"Created attribute value: {config['name']} (UUID: {config['fusion_uuid']})")
                else:
                    # Update name if it changed in Fusion
                    if value.name != config['name']:
                        value.write({'name': config['name']})
                        _logger.info(f"Updated attribute value name from {value.name} to {config['name']}")
                
                value_ids.append(value.id)
            
            # Create or update product attribute line
            attr_line = self.env['product.template.attribute.line'].search([
                ('product_tmpl_id', '=', product.id),
                ('attribute_id', '=', config_attr.id)
            ], limit=1)
            
            if not attr_line:
                attr_line = self.env['product.template.attribute.line'].create({
                    'product_tmpl_id': product.id,
                    'attribute_id': config_attr.id,
                    'value_ids': [(6, 0, value_ids)]
                })
                _logger.info("Created attribute line")
            else:
                attr_line.write({
                    'value_ids': [(6, 0, value_ids)]
                })
                _logger.info("Updated attribute line")

            # Generate default_code for variants
            for variant in product.product_variant_ids:
                config_name = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id == config_attr
                ).name
                variant.default_code = f"{product.fusion_generated_default_code}/{re.sub(r'[^a-zA-Z0-9]', '_', config_name)}"
        
        return product
    
    @api.model
    def get_product_variant_by_uuid(self, fusion_uuid, config_row_id=None):
        """Get the product variant based on Fusion UUID and configuration row ID."""
        _logger.info(f"Getting product variant for UUID: {fusion_uuid}, Config Row ID: {config_row_id}")
        
        product_tmpl = self.search([('fusion_uuid', '=', fusion_uuid)], limit=1)
        if not product_tmpl:
            _logger.info("Product template not found")
            return None
        
        if not config_row_id:
            # If no configuration row ID is provided, check if there's only one variant
            if product_tmpl.product_variant_count == 1:
                return product_tmpl.product_variant_ids.id
            else:
                _logger.warning("Multiple variants found for a non-configured component. This is unexpected.")
                return None
        
        # Find the attribute value matching the configuration row ID
        attr_value = self.env['product.attribute.value'].search([
            ('fusion_uuid', '=', config_row_id)
        ], limit=1)
        
        if not attr_value:
            _logger.info("Attribute value not found")
            return None
        
        # Find the product variant with the matching attribute value
        product_variant = self.env['product.product'].search([
            ('product_tmpl_id', '=', product_tmpl.id),
            ('product_template_variant_value_ids', '=', attr_value.id)
        ], limit=1)
        
        if not product_variant:
            _logger.info("Product variant not found")
            return None
        
        return product_variant.id
