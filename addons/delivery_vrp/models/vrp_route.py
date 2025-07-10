from odoo import models, fields, api, _

class VrpRoute(models.Model):
    _name = 'vrp.route'
    _description = 'Tournée VRP'
    _order = 'date desc, name'

    name = fields.Char('Nom de la tournée', required=True)
    date = fields.Date('Date', required=True, default=fields.Date.today)
    vehicle_id = fields.Many2one('vrp.vehicle', string='Véhicule', required=True)
    
    # Statistiques
    total_distance = fields.Float('Distance totale (km)', readonly=True)
    total_duration = fields.Float('Durée totale (h)', readonly=True)
    total_demand = fields.Float('Charge totale (kg)', readonly=True)
    load_rate = fields.Float('Taux de charge (%)', readonly=True, compute='_compute_load_rate')
    
    # Statut
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée')
    ], string='Statut', default='draft')
    
    # Relations
    visit_ids = fields.One2many('vrp.visit', 'route_id', string='Visites')
    optimization_id = fields.Many2one('vrp.optimization', string='Optimisation')
    
    @api.depends('total_demand', 'vehicle_id.capacity_weight')
    def _compute_load_rate(self):
        for route in self:
            if route.vehicle_id.capacity_weight > 0:
                route.load_rate = (route.total_demand / route.vehicle_id.capacity_weight) * 100
            else:
                route.load_rate = 0

    def action_plan(self):
        self.state = 'planned'
        
    def action_start(self):
        self.state = 'in_progress'
        
    def action_complete(self):
        self.state = 'done'
        
    def action_cancel(self):
        self.state = 'cancelled'

class VrpVisit(models.Model):
    _name = 'vrp.visit'
    _description = 'Visite client'
    _order = 'sequence, id'

    sequence = fields.Integer('Séquence', default=1)
    route_id = fields.Many2one('vrp.route', string='Tournée', required=True, ondelete='cascade')
    customer_id = fields.Many2one('vrp.customer', string='Client', required=True)
    
    # Planification
    planned_arrival = fields.Float('Arrivée prévue (h)')
    planned_departure = fields.Float('Départ prévu (h)')
    actual_arrival = fields.Float('Arrivée réelle (h)')
    actual_departure = fields.Float('Départ réel (h)')
    
    # Distance
    distance_from_previous = fields.Float('Distance depuis précédent (km)')
    
    # Statut
    state = fields.Selection([
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('failed', 'Échec')
    ], string='Statut', default='planned')
    
    notes = fields.Text('Notes')
