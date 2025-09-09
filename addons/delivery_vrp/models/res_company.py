# models/res_company.py
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Configuration VRP
    vrp_routing_service = fields.Selection([
        ('osrm', 'OSRM (Gratuit, Recommandé)'),
        ('graphhopper', 'GraphHopper'),
        ('openrouteservice', 'OpenRouteService'),
    ], string='Service de Routage', default='osrm',
       help="Service utilisé pour calculer les distances routières réelles")
    
    vrp_openrouteservice_key = fields.Char(
        string='Clé API OpenRouteService',
        help="Clé API gratuite obtenue sur openrouteservice.org (2000 requêtes/jour)"
    )
    
    vrp_graphhopper_key = fields.Char(
        string='Clé API GraphHopper',
        help="Clé API GraphHopper (optionnelle pour version gratuite limitée)"
    )
    
    vrp_depot_latitude = fields.Float(
        string='Latitude du Dépôt',
        digits=(10, 6),
        help="Coordonnée latitude du point de départ des livraisons"
    )
    
    vrp_depot_longitude = fields.Float(
        string='Longitude du Dépôt',
        digits=(10, 6),
        help="Coordonnée longitude du point de départ des livraisons"
    )
    
    vrp_max_route_distance = fields.Integer(
        string='Distance Max par Route (km)',
        default=100,
        help="Distance maximale qu'un véhicule peut parcourir"
    )
    
    vrp_max_stops_per_route = fields.Integer(
        string='Arrêts Max par Route',
        default=20,
        help="Nombre maximum d'arrêts par véhicule"
    )
