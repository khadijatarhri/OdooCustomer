from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VrpCustomer(models.Model):
    _name = 'vrp.customer'
    _description = 'Client VRP'
    _order = 'name'

    name = fields.Char('Nom', required=True)
    partner_id = fields.Many2one('res.partner', string='Partenaire Odoo')
    
    # Localisation
    street = fields.Char('Adresse')
    city = fields.Char('Ville')
    zip_code = fields.Char('Code postal')
    latitude = fields.Float('Latitude', digits=(10, 6))
    longitude = fields.Float('Longitude', digits=(10, 6))
    
    # Demande
    demand_weight = fields.Float('Demande poids (kg)', required=True)
    demand_volume = fields.Float('Demande volume (m³)')
    
    # Contraintes temporelles
    ready_time = fields.Float('Heure d\'ouverture', default=8.0)
    due_time = fields.Float('Heure de fermeture', default=18.0)
    service_time = fields.Float('Temps de service (h)', default=0.25)
    
    # Priorité
    priority = fields.Selection([
        ('1', 'Normale'),
        ('2', 'Haute'),
        ('3', 'Critique')
    ], string='Priorité', default='1')
    
    # Statut
    active = fields.Boolean('Actif', default=True)
    
    # Relations
    visit_ids = fields.One2many('vrp.visit', 'customer_id', string='Visites')
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.street = self.partner_id.street
            self.city = self.partner_id.city
            self.zip_code = self.partner_id.zip

    @api.constrains('demand_weight', 'ready_time', 'due_time')
    def _check_constraints(self):
        for record in self:
            if record.demand_weight <= 0:
                raise ValidationError(_('La demande doit être positive'))
            if record.ready_time >= record.due_time:
                raise ValidationError(_('L\'heure d\'ouverture doit être avant l\'heure de fermeture'))
