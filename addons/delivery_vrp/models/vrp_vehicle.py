from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VrpVehicle(models.Model):
    _name = 'vrp.vehicle'
    _description = 'Véhicule pour VRP'
    _order = 'name'

    name = fields.Char('Nom du véhicule', required=True)
    code = fields.Char('Code', required=True)
    vehicle_type = fields.Selection([
        ('truck', 'Camion'),
        ('van', 'Fourgon'),
        ('car', 'Voiture'),
        ('motorcycle', 'Moto')
    ], string='Type de véhicule', required=True, default='truck')
    
    # Caractéristiques du véhicule
    capacity_weight = fields.Float('Capacité poids (kg)', required=True)
    capacity_volume = fields.Float('Capacité volume (m³)')
    max_distance = fields.Float('Distance maximale (km)', default=500.0)
    cost_per_km = fields.Float('Coût par km (Dh)', default=0.5)
    
    # Localisation
    depot_id = fields.Many2one('vrp.depot', string='Dépôt', required=True)
    
    # Contraintes de temps
    work_start_time = fields.Float('Heure de début', default=8.0)
    work_end_time = fields.Float('Heure de fin', default=18.0)
    
    # Statut
    active = fields.Boolean('Actif', default=True)
    availability = fields.Selection([
        ('available', 'Disponible'),
        ('in_use', 'En utilisation'),
        ('maintenance', 'En maintenance'),
        ('unavailable', 'Indisponible')
    ], string='Disponibilité', default='available')
    
        
    @api.constrains('capacity_weight', 'max_distance')
    def _check_capacities(self):
        for record in self:
            if record.capacity_weight <= 0:
                raise ValidationError(_('La capacité poids doit être positive'))
            if record.max_distance <= 0:
                raise ValidationError(_('La distance maximale doit être positive'))
