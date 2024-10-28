from odoo import models, fields, api
from odoo.exceptions import ValidationError
import uuid


class FusionDesign(models.Model):
    _name = 'fusion.design'
    _description = 'Fusion 360 Design'
    _rec_name = 'name'

    name = fields.Char(
        string='Design Name',
        required=True,
        help='Name of the Fusion 360 design'
    )
    default_code = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        help='Unique reference for this design'
    )
    fusion_uuid = fields.Char(
        string='Fusion UUID',
        required=True,
        readonly=True,
        copy=False,
        help='Unique identifier from Fusion 360'
    )
    version_id = fields.Char(
        string='Version ID',
        readonly=True,
        help='Fusion version identifier'
    )
    version_number = fields.Char(
        string='Version Number',
        readonly=True,
        help='Fusion version number'
    )
    last_updated_by = fields.Char(
        string='Last Updated By',
        readonly=True,
        help='User who last updated the design in Fusion'
    )
    fusion_web_url = fields.Char(
        string='Fusion Web URL',
        readonly=True,
        help='URL to view the design in Fusion 360 web interface'
    )
    shared_link = fields.Char(
        string='Shared Link',
        readonly=True,
        help='Shared link to the design'
    )
    date_created = fields.Datetime(
        string='Created in Fusion',
        readonly=True,
        help='Date when the design was created in Fusion'
    )
    date_modified = fields.Datetime(
        string='Modified in Fusion',
        readonly=True,
        help='Date when the design was last modified in Fusion'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('synced', 'Synced'),
        ('error', 'Error')
    ], string='Status', default='draft', required=True)
    
    description = fields.Text(
        string='Description',
        help='Design description from Fusion 360'
    )
    last_sync = fields.Datetime(
        string='Last Synchronization',
        readonly=True
    )
    version = fields.Char(
        string='Version',
        help='Design version in Fusion 360'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to hide the design without removing it.'
    )

    _sql_constraints = [
        ('fusion_uuid_unique', 'UNIQUE(fusion_uuid)',
         'A design with this Fusion UUID already exists!'),
        ('default_code_unique', 'UNIQUE(default_code)',
         'A design with this reference already exists!')
    ]

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
    def sync_from_fusion(self, vals):
        """Sync (create or update) a design record from Fusion 360 data"""
        if not vals.get('fusion_uuid'):
            raise ValidationError('Fusion UUID is required')
        
        # Search for existing design
        existing = self.search([('fusion_uuid', '=', vals['fusion_uuid'])], limit=1)
        
        vals['state'] = 'synced'
        vals['last_sync'] = fields.Datetime.now()
        
        if existing:
            # Update existing design
            existing.write(vals)
            return existing.id
        else:
            # Create new design
            return self.create(vals).id
