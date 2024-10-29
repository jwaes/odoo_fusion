from odoo import models, fields, api

class FusionUser(models.Model):
    _name = 'fusion.user'
    _description = 'Fusion User'
    
    name = fields.Char('Username', required=True)
    display_name = fields.Char('Display Name')
    email = fields.Char('Email')
    fusion_id = fields.Char('Fusion ID', required=True)
    active = fields.Boolean('Active', default=True)
    
    _sql_constraints = [
        ('fusion_id_uniq', 'unique(fusion_id)', 'Fusion ID must be unique!')
    ]
    
    @api.model
    def get_or_create_from_fusion(self, user_data):
        """Get or create user from Fusion data."""
        if not user_data or not user_data.get('fusion_id'):
            return False
            
        user = self.search([('fusion_id', '=', user_data['fusion_id'])], limit=1)
        if not user:
            vals = {
                'name': user_data.get('name'),
                'display_name': user_data.get('display_name'),
                'email': user_data.get('email'),
                'fusion_id': user_data['fusion_id'],
            }
            user = self.create(vals)
        else:
            # Update existing user data
            user.write({
                'name': user_data.get('name'),
                'display_name': user_data.get('display_name'),
                'email': user_data.get('email'),
            })
        return user
