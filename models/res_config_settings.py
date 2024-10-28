from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fusion_sequence_id = fields.Many2one(
        'ir.sequence',
        'Fusion Design Sequence',
        config_parameter='odoo_fusion.fusion_sequence_id',
        help='Sequence used for Fusion design codes'
    )
