from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class FusionDesign(models.Model):
    _name = 'fusion.design'
    _description = 'Fusion Design'
    _inherit = ['mail.thread']
    
    name = fields.Char('Name', required=True, tracking=True)
    default_code = fields.Char('Reference', readonly=True, copy=False)
    active = fields.Boolean('Active', default=True)
    
    fusion_uuid = fields.Char('Fusion UUID', readonly=True)
    version = fields.Char('Version', readonly=True)
    version_id = fields.Char('Version ID', readonly=True)
    version_number = fields.Integer('Version Number', readonly=True)
    description = fields.Text('Description')
    
    fusion_web_url = fields.Char('Fusion Web URL', readonly=True)
    shared_link_active = fields.Boolean('Shared Link Active', readonly=True)
    shared_link_url = fields.Char('Shared Link URL', readonly=True)
    shared_link_download = fields.Boolean('Shared Link Download', readonly=True)
    
    date_created = fields.Datetime('Created Date', readonly=True)
    date_modified = fields.Datetime('Modified Date', readonly=True)
    last_sync = fields.Datetime('Last Sync', readonly=True)
    
    last_updated_by_id = fields.Many2one('fusion.user', string='Last Updated By', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('synced', 'Synced'),
        ('error', 'Error')
    ], string='Status', default='draft', tracking=True)
    
    product_ids = fields.One2many('product.template', 'fusion_design_id', string='Products')
    
    _sql_constraints = [
        ('fusion_uuid_uniq', 'unique(fusion_uuid)', 'Fusion UUID must be unique!')
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                vals['default_code'] = self.env['ir.sequence'].next_by_code('fusion.design.default.code')
        return super().create(vals_list)
    
    @api.model
    def create_or_update_from_fusion(self, fusion_data):
        """Create or update design from Fusion data."""
        _logger.info(f"Processing Fusion design: {fusion_data['name']}")
        
        # Find existing design by UUID
        design = self.search([('fusion_uuid', '=', fusion_data['fusion_uuid'])], limit=1)
        
        # Get or create user
        user_data = fusion_data.get('last_updated_by')
        if user_data:
            user = self.env['fusion.user'].get_or_create_from_fusion(user_data)
            fusion_data['last_updated_by_id'] = user.id
        
        vals = {
            'name': fusion_data['name'],
            'fusion_uuid': fusion_data['fusion_uuid'],
            'version': fusion_data['version'],
            'version_id': fusion_data['version_id'],
            'version_number': fusion_data['version_number'],
            'description': fusion_data['description'],
            'fusion_web_url': fusion_data['fusion_web_url'],
            'date_created': fusion_data['date_created'],
            'date_modified': fusion_data['date_modified'],
            'last_sync': fields.Datetime.now(),
            'state': 'synced'
        }
        
        # Handle shared link data
        shared_link = fusion_data.get('shared_link', {})
        vals.update({
            'shared_link_active': shared_link.get('is_shared', False),
            'shared_link_url': shared_link.get('url', ''),
            'shared_link_download': shared_link.get('allow_download', False),
        })
        
        if not design:
            _logger.info("Creating new design")
            design = self.create(vals)
        else:
            _logger.info(f"Updating existing design: {design.name}")
            design.write(vals)
        
        # Get current fusion UUIDs from the design data
        current_fusion_uuids = {comp['fusion_uuid'] for comp in fusion_data.get('components', [])}
        
        # Get existing products linked to this design
        existing_products = self.env['product.template'].search([
            ('fusion_design_id', '=', design.id)
        ])
        
        # Unlink products that are no longer in the design
        for product in existing_products:
            if product.fusion_uuid not in current_fusion_uuids:
                _logger.info(f"Unlinking product {product.name} as it's no longer in the design")
                product.fusion_design_id = False
        
        # Process components
        for component_data in fusion_data.get('components', []):
            _logger.info(f"Processing component: {component_data['name']}")
            product = self.env['product.template'].create_or_update_from_fusion(component_data)
            if product:
                product.fusion_design_id = design.id
                _logger.info(f"Linked product {product.name} to design {design.name}")
        
        return design.id
