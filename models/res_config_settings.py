from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    fusion_api_key = fields.Char(string='Fusion API Key', config_parameter='odoo_fusion.api_key')
    fusion_api_url = fields.Char(string='Fusion API URL', config_parameter='odoo_fusion.api_url')
    fusion_default_category_id = fields.Many2one(
        'product.category',
        string='Default Product Category',
        config_parameter='odoo_fusion.default_category_id',
        help='Default category for products created from Fusion'
    )
