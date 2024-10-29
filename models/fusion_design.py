from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FusionDesign(models.Model):
    _name = 'fusion.design'
    _description = 'Fusion Design'
    _inherit = ['mail.thread']
    
    active = fields.Boolean(default=True)
    name = fields.Char('Name', required=True)
    fusion_uuid = fields.Char('Fusion UUID', required=True)
    version = fields.Char('Version')
    description = fields.Text('Description')
    version_id = fields.Char('Version ID')
    version_number = fields.Integer('Version Number')
    last_updated_by_id = fields.Many2one('fusion.user', 'Last Updated By')
    fusion_web_url = fields.Char('Fusion Web URL')
    date_created = fields.Datetime('Date Created')
    date_modified = fields.Datetime('Date Modified')
    product_ids = fields.One2many('product.template', 'fusion_design_id', string='Fusion Products')
    default_code = fields.Char('Reference', readonly=True)
    
    # Sync fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('synced', 'Synced'),
        ('error', 'Error')
    ], string='Status', default='draft', required=True, tracking=True)
    last_sync = fields.Datetime('Last Sync')
    
    # Sharing fields
    shared_link_active = fields.Boolean('Shared', default=False)
    shared_link_download = fields.Boolean('Allow Download', default=False)
    shared_link_url = fields.Char('Share URL')

    def _prepare_fusion_vals(self, fusion_data):
        """Prepare values for create/write from fusion data."""
        return {
            'name': fusion_data['name'],
            'fusion_uuid': fusion_data['fusion_uuid'],
            'version': fusion_data['version'],
            'description': fusion_data['description'],
            'version_id': fusion_data['version_id'],
            'version_number': fusion_data['version_number'],
            'last_updated_by_id': self.env['fusion.user'].search([('fusion_id', '=', fusion_data['last_updated_by']['fusion_id'])], limit=1).id,
            'fusion_web_url': fusion_data['fusion_web_url'],
            'date_created': fusion_data['date_created'],
            'date_modified': fusion_data['date_modified'],
            'shared_link_active': fusion_data['shared_link']['is_shared'],
            'shared_link_download': fusion_data['shared_link']['allow_download'],
            'shared_link_url': fusion_data['shared_link']['url'],
            'state': 'synced',
            'last_sync': fields.Datetime.now(),
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                sequence_id = int(self.env['ir.config_parameter'].sudo().get_param(
                    'odoo_fusion.fusion_sequence_id', default=0))
                if not sequence_id:
                    raise ValidationError(
                        'Please configure Fusion Design sequence in Manufacturing Settings')
                sequence = self.env['ir.sequence'].browse(sequence_id)
                vals['default_code'] = sequence.next_by_id()
        return super().create(vals_list)
    
    @api.model
    def create_or_update_from_fusion(self, fusion_data):
        """Create or update Odoo fusion design from Fusion data."""
        design = self.search([('fusion_uuid', '=', fusion_data['fusion_uuid'])], limit=1)
        vals = self._prepare_fusion_vals(fusion_data)
        
        if not design:
            design = self.create(vals)
        else:
            design.write(vals)
        
        # Create or update Fusion Products
        for component in fusion_data['components']:
            product = self.env['product.template'].create_or_update_from_fusion(component)
            product.fusion_design_id = design.id
        
        return design
