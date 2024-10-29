from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    fusion_default_category_id = fields.Many2one(
        'product.category',
        string='Default Product Category',
        config_parameter='odoo_fusion.default_category_id',
        help='Default category for products created from Fusion'
    )
    fusion_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Design Reference Sequence',
        config_parameter='odoo_fusion.sequence_id',
        help='Sequence for Fusion design references'
    )
    fusion_product_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Product Reference Sequence',
        config_parameter='odoo_fusion.product_sequence_id',
        help='Sequence for Fusion product references'
    )
