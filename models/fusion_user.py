from odoo import models, fields, api


class FusionUser(models.Model):
    _name = 'fusion.user'
    _description = 'Fusion 360 User'
    _rec_name = 'display_name'

    name = fields.Char(
        string='User Name',
        required=True,
        readonly=True,
        help='Username from Fusion 360'
    )
    display_name = fields.Char(
        string='Display Name',
        required=True,
        readonly=True,
        help='Display name from Fusion 360'
    )
    email = fields.Char(
        string='Email',
        readonly=True,
        help='Email address from Fusion 360'
    )
    fusion_id = fields.Char(
        string='Fusion ID',
        required=True,
        readonly=True,
        copy=False,
        help='Unique identifier from Fusion 360'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        help='Link to Odoo partner/user'
    )
    design_ids = fields.One2many(
        'fusion.design',
        'last_updated_by_id',
        string='Modified Designs'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to hide the user without removing it.'
    )

    _sql_constraints = [
        ('fusion_id_unique', 'UNIQUE(fusion_id)',
         'A user with this Fusion ID already exists!')
    ]

    @api.model
    def sync_from_fusion(self, vals):
        """Sync (create or update) a user record from Fusion 360 data"""
        if not vals.get('fusion_id'):
            return False
        
        # Search for existing user
        existing = self.search([('fusion_id', '=', vals['fusion_id'])], limit=1)
        
        if existing:
            # Update existing user
            existing.write(vals)
            return existing.id
        else:
            # Try to find matching partner by email
            if vals.get('email'):
                partner = self.env['res.partner'].search([
                    ('email', '=ilike', vals['email']),
                    '|',
                    ('active', '=', True),
                    ('active', '=', False)
                ], limit=1)
                if partner:
                    vals['partner_id'] = partner.id
            
            # Create new user
            return self.create(vals).id
