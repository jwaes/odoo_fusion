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
        if fusion_data.get('is_configuration'):
            _logger.info(f"Processing configuration instance with ID: {fusion_data['configuration_id']}")
            
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
            
            # Create or get attribute value for this configuration
            attr_vals = self.env['product.attribute.value']
            value = attr_vals.with_context(active_test=False).search([
                ('fusion_uuid', '=', fusion_data['configuration_id']),
                ('attribute_id', '=', config_attr.id)
            ], limit=1)
            
            if not value:
                value = attr_vals.create({
                    'name': fusion_data['name'],
                    'fusion_uuid': fusion_data['configuration_id'],
                    'attribute_id': config_attr.id
                })
                _logger.info(f"Created configuration value: {fusion_data['name']} (UUID: {fusion_data['configuration_id']})")
            
            # Create or update product attribute line
            attr_line = self.env['product.template.attribute.line'].search([
                ('product_tmpl_id', '=', product.id),
                ('attribute_id', '=', config_attr.id)
            ], limit=1)
            
            if not attr_line:
                attr_line = self.env['product.template.attribute.line'].create({
                    'product_tmpl_id': product.id,
                    'attribute_id': config_attr.id,
                    'value_ids': [(6, 0, [value.id])]
                })
                _logger.info("Created attribute line")
            else:
                current_values = attr_line.value_ids.ids
                if value.id not in current_values:
                    attr_line.write({
                        'value_ids': [(4, value.id)]
                    })
                    _logger.info(f"Added configuration value to attribute line: {value.name}")

            # Generate default_code for this variant
            variant = product.product_variant_ids.filtered(
                lambda v: value in v.product_template_attribute_value_ids.product_attribute_value_id
            )
            if variant:
                variant.default_code = f"{product.fusion_generated_default_code}/{re.sub(r'[^a-zA-Z0-9]', '_', value.name)}"
                _logger.info(f"Set variant default_code: {variant.default_code}")
        
        return product.id
    
    @api.model
    def get_product_variant_by_uuid(self, fusion_uuid, config_row_id=None):
        """Get the product variant based on Fusion UUID and configuration row ID."""
        _logger.info(f"Getting product variant for UUID: {fusion_uuid}, Config Row ID: {config_row_id}")
        
        product_tmpl = self.search([('fusion_uuid', '=', fusion_uuid)], limit=1)
        if not product_tmpl:
            _logger.info("Product template not found")
            return False
        
        if not config_row_id:
            # If no configuration row ID is provided, check if there's only one variant
            if product_tmpl.product_variant_count == 1:
                _logger.info(f"Found single variant for {product_tmpl.name}")
                return product_tmpl.product_variant_ids[0].id
            else:
                _logger.warning(f"Multiple variants ({product_tmpl.product_variant_count}) found for {product_tmpl.name}. Using first variant.")
                return product_tmpl.product_variant_ids[0].id if product_tmpl.product_variant_ids else False
        
        # Find the attribute value matching the configuration row ID
        attr_value = self.env['product.attribute.value'].search([
            ('fusion_uuid', '=', config_row_id)
        ], limit=1)
        
        if not attr_value:
            _logger.info(f"Configuration value not found for ID: {config_row_id}")
            # Log existing attribute values for debugging
            existing_values = self.env['product.attribute.value'].search([('fusion_uuid', '!=', False)])
            _logger.info("Available configuration values:")
            for val in existing_values:
                _logger.info(f"  Name: {val.name}, UUID: {val.fusion_uuid}, Attribute: {val.attribute_id.name}")
            return False
        
        # Find the product variant with the matching attribute value
        variant = product_tmpl.product_variant_ids.filtered(
            lambda v: attr_value in v.product_template_attribute_value_ids.product_attribute_value_id
        )
        
        if not variant:
            _logger.info(f"No variant found with configuration: {attr_value.name}")
            # Log available variants for debugging
            _logger.info(f"Available variants for {product_tmpl.name}:")
            for var in product_tmpl.product_variant_ids:
                config_values = var.product_template_attribute_value_ids.product_attribute_value_id
                _logger.info(f"  Variant ID: {var.id}, Configuration values: {config_values.mapped('name')}")
            return False
        
        _logger.info(f"Found variant with configuration: {attr_value.name}")
        return variant[0].id if variant else False
