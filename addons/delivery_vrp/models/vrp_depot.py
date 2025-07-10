from odoo import models, fields, api

class VrpDepot(models.Model):
    _name = 'vrp.depot'
    _description = 'Dépôt VRP'
    _order = 'name'

    name = fields.Char('Nom du dépôt', required=True)
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    
    # Localisation
    street = fields.Char('Adresse')
    city = fields.Char('Ville')
    zip_code = fields.Char('Code postal')
    country_id = fields.Many2one('res.country', string='Pays')
    latitude = fields.Float('Latitude', digits=(10, 6))
    longitude = fields.Float('Longitude', digits=(10, 6))
    
    # Contraintes
    opening_time = fields.Float('Heure d\'ouverture', default=6.0)
    closing_time = fields.Float('Heure de fermeture', default=22.0)
    
    active = fields.Boolean('Actif', default=True)
    
    # Relations
    vehicle_ids = fields.One2many('vrp.vehicle', 'depot_id', string='Véhicules')
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.street = self.partner_id.street
            self.city = self.partner_id.city
            self.zip_code = self.partner_id.zip
            self.country_id = self.partner_id.country_id