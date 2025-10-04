# models/res_partner.py 
from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Champ JSON pour stocker les coordonnées GPS
    coordinates = fields.Json(string='GPS Coordinates', help="Coordonnées GPS au format JSON")
    
    # Champs calculés pour faciliter l'accès
    partner_latitude = fields.Float(string='Latitude', compute='_compute_gps_fields', store=True)
    partner_longitude = fields.Float(string='Longitude', compute='_compute_gps_fields', store=True)
    
    @api.depends('coordinates')
    def _compute_gps_fields(self):
        """Calculer les champs latitude/longitude depuis le JSON coordinates"""
        for partner in self:
            if partner.coordinates and isinstance(partner.coordinates, dict):
                try:
                    lat = float(partner.coordinates.get('latitude', 0.0))
                    lng = float(partner.coordinates.get('longitude', 0.0))
                    
                    # Validation des coordonnées
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        partner.partner_latitude = lat
                        partner.partner_longitude = lng
                    else:
                        partner.partner_latitude = 0.0
                        partner.partner_longitude = 0.0
                except (ValueError, TypeError):
                    partner.partner_latitude = 0.0
                    partner.partner_longitude = 0.0
            else:
                partner.partner_latitude = 0.0
                partner.partner_longitude = 0.0
    
    def set_coordinates(self, latitude, longitude):
        """Méthode helper pour définir les coordonnées"""
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                self.coordinates = {
                    'latitude': float(latitude),
                    'longitude': float(longitude)
                }
                return True
        return False
    
    def get_coordinates(self):
        """Méthode helper pour récupérer les coordonnées"""
        if self.coordinates and isinstance(self.coordinates, dict):
            lat = self.coordinates.get('latitude', 0.0)
            lng = self.coordinates.get('longitude', 0.0)
            return lat, lng
        return 0.0, 0.0