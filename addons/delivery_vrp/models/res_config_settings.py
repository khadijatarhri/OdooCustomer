# models/res_config_settings.py
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    vrp_routing_service = fields.Selection(
        related='company_id.vrp_routing_service',
        readonly=False
    )
    
    vrp_openrouteservice_key = fields.Char(
        related='company_id.vrp_openrouteservice_key',
        readonly=False
    )
    
    vrp_graphhopper_key = fields.Char(
        related='company_id.vrp_graphhopper_key',
        readonly=False
    )
    
    vrp_depot_latitude = fields.Float(
        related='company_id.vrp_depot_latitude',
        readonly=False
    )
    
    vrp_depot_longitude = fields.Float(
        related='company_id.vrp_depot_longitude',
        readonly=False
    )
    
    vrp_max_route_distance = fields.Integer(
        related='company_id.vrp_max_route_distance',
        readonly=False
    )
    
    vrp_max_stops_per_route = fields.Integer(
        related='company_id.vrp_max_stops_per_route',
        readonly=False
    )
    
    @api.onchange('vrp_depot_latitude', 'vrp_depot_longitude')
    def _onchange_depot_coordinates(self):
        """Validation des coordonnées du dépôt"""
        if self.vrp_depot_latitude and self.vrp_depot_longitude:
            if not (-90 <= self.vrp_depot_latitude <= 90):
                return {'warning': {
                    'title': 'Latitude Invalide',
                    'message': 'La latitude doit être entre -90 et 90'
                }}
            if not (-180 <= self.vrp_depot_longitude <= 180):
                return {'warning': {
                    'title': 'Longitude Invalide', 
                    'message': 'La longitude doit être entre -180 et 180'
                }}
    
    def action_set_rabat_depot(self):
        """Définir rapidement Rabat comme dépôt"""
        self.vrp_depot_latitude = 34.0209
        self.vrp_depot_longitude = -6.8416
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dépôt Configuré',
                'message': 'Rabat défini comme dépôt principal (34.0209, -6.8416)',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_test_routing_service(self):
        """Tester la connexion au service de routage"""
        optimizer = self.env['vrp.optimizer.enhanced'].create({})
        
        # Test avec Casablanca vers Rabat
        test_locations = [
            {'lat': 33.5731, 'lng': -7.5898, 'name': 'Casablanca'},
            {'lat': 34.0209, 'lng': -6.8416, 'name': 'Rabat'}
        ]
        
        try:
            matrix = optimizer.create_road_distance_matrix(test_locations)
            if matrix and len(matrix) == 2:
                distance_km = matrix[0][1] / 1000
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Test Réussi',
                        'message': f'Service de routage fonctionnel. Distance Casablanca-Rabat: {distance_km:.1f}km',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise Exception("Matrice invalide")
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Échoué',
                    'message': f'Erreur de connexion: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }