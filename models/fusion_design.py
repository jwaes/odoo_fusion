from odoo import models, fields, api
from odoo.addons.odoo_fusion.models.res_config_settings import FusionSettings

class FusionDesign(models.Model):
    _name = 'fusion.design'
    _description = 'Fusion Design'
    
    name = fields.Char('Name', required=True)
    fusion_uuid = fields.Char('Fusion UUID', required=True)
    version = fields.Char('Version')
    description = fields.Text('Description')
    version_id = fields.Char('Version ID')
    version_number = fields.Integer('Version Number')
    last_updated_by = fields.Many2one('res.users', 'Last Updated By')
    fusion_web_url = fields.Char('Fusion Web URL')
    shared_link = fields.Many2one('fusion.shared.link', 'Shared Link')
    date_created = fields.Datetime('Date Created')
    date_modified = fields.Datetime('Date Modified')
    product_ids = fields.One2many('fusion.product', 'fusion_design_id', string='Fusion Products')
    
    @api.model
    def create_or_update_from_fusion(self, fusion_data):
        """Create or update Odoo fusion design from Fusion data."""
        design = self.search([('fusion_uuid', '=', fusion_data['fusion_uuid'])], limit=1)
        if not design:
            design = self.create({
                'name': fusion_data['name'],
                'fusion_uuid': fusion_data['fusion_uuid'],
                'version': fusion_data['version'],
                'description': fusion_data['description'],
                'version_id': fusion_data['version_id'],
                'version_number': fusion_data['version_number'],
                'last_updated_by': self.env['res.users'].search([('fusion_id', '=', fusion_data['last_updated_by']['fusion_id'])], limit=1).id,
                'fusion_web_url': fusion_data['fusion_web_url'],
                'shared_link': self.env['fusion.shared.link'].create_or_update_from_fusion(fusion_data['shared_link']).id,
                'date_created': fusion_data['date_created'],
                'date_modified': fusion_data['date_modified'],
            })
        else:
            design.write({
                'name': fusion_data['name'],
                'fusion_uuid': fusion_data['fusion_uuid'],
                'version': fusion_data['version'],
                'description': fusion_data['description'],
                'version_id': fusion_data['version_id'],
                'version_number': fusion_data['version_number'],
                'last_updated_by': self.env['res.users'].search([('fusion_id', '=', fusion_data['last_updated_by']['fusion_id'])], limit=1).id,
                'fusion_web_url': fusion_data['fusion_web_url'],
                'shared_link': self.env['fusion.shared.link'].create_or_update_from_fusion(fusion_data['shared_link']).id,
                'date_created': fusion_data['date_created'],
                'date_modified': fusion_data['date_modified'],
            })
        
        # Create or update Fusion Products
        for component in fusion_data['components']:
            product = self.env['fusion.product'].create_or_update_from_fusion(component)
            product.fusion_design_id = design.id
        
        return design
