# models/sale_order_corrected.py - VERSION CORRIGÉE
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    assigned_vehicle_id = fields.Many2one('fleet.vehicle', string='Assigned Vehicle')
    delivery_sequence = fields.Integer(string='Delivery Sequence', default=0)
    partner_latitude = fields.Float(related='partner_id.partner_latitude', string='Latitude')
    partner_longitude = fields.Float(related='partner_id.partner_longitude', string='Longitude')
    manual_assignment = fields.Boolean(string='Manual Vehicle Assignment', default=False)
    driver_id = fields.Many2one(related='assigned_vehicle_id.driver_id', string='Driver', readonly=True)
    delivery_count = fields.Integer(string='Delivery Count', compute='_compute_delivery_count', store=True)

    @api.depends('order_line')
    def _compute_delivery_count(self):
        for order in self:
            order.delivery_count = len(order.order_line)

    def _get_depot_coordinates(self):
        """Obtenir les coordonnées du dépôt de manière centralisée"""
        # Priorité 1: Paramètres de la société
        if hasattr(self.env.company, 'vrp_depot_latitude') and self.env.company.vrp_depot_latitude:
            return {
                'latitude': self.env.company.vrp_depot_latitude,
                'longitude': self.env.company.vrp_depot_longitude
            }
        
        # Priorité 2: Valeurs par défaut (Rabat)
        return {
            'latitude': 34.0209,
            'longitude': -6.8416
        }

    def _get_order_coordinates_unified(self, order):
        """Méthode unifiée pour récupérer les coordonnées d'une commande"""
        lat, lng = 0.0, 0.0
        coords_found = False
        
        _logger.info(f"Récupération coordonnées pour commande {order.name}")
        
        # 1. Essayer les coordonnées JSON du partenaire
        partner = order.partner_id
        if partner.coordinates and isinstance(partner.coordinates, dict):
            try:
                lat = float(partner.coordinates.get('latitude', 0.0))
                lng = float(partner.coordinates.get('longitude', 0.0))
                
                if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 and lng != 0.0):
                    coords_found = True
                    _logger.info(f"✓ Coordonnées trouvées via JSON partner: {lat}, {lng}")
            except (ValueError, TypeError) as e:
                _logger.warning(f"Erreur parsing JSON coordinates: {e}")
        
        # 2. Si pas trouvé, essayer via VRP order
        if not coords_found:
            vrp_order = self.env['vrp.order'].search([
                ('sale_order_id', '=', order.id)
            ], limit=1)
            
            if vrp_order:
                vrp_order._compute_coordinates()
                if vrp_order.partner_latitude and vrp_order.partner_longitude:
                    if (vrp_order.partner_latitude != 0.0 and vrp_order.partner_longitude != 0.0):
                        lat = vrp_order.partner_latitude
                        lng = vrp_order.partner_longitude
                        coords_found = True
                        _logger.info(f"✓ Coordonnées trouvées via VRP order: {lat}, {lng}")
        
        # 3. Si encore pas trouvé, essayer les champs directs
        if not coords_found and hasattr(order, 'partner_latitude') and hasattr(order, 'partner_longitude'):
            if order.partner_latitude and order.partner_longitude:
                if (order.partner_latitude != 0.0 and order.partner_longitude != 0.0):
                    lat = order.partner_latitude
                    lng = order.partner_longitude
                    coords_found = True
                    _logger.info(f"✓ Coordonnées trouvées via champs directs: {lat}, {lng}")
        
        if not coords_found:
            _logger.warning(f"✗ Aucune coordonnée valide trouvée pour {order.name}")
        
        return lat, lng, coords_found

    def action_optimize_delivery_enhanced(self):
        """Action d'optimisation améliorée"""
        selected_orders = self.browse(self.env.context.get('active_ids', []))
        
        if not selected_orders:
            raise UserError("Veuillez sélectionner au moins une commande")
        
        # Vérifier les coordonnées avec la nouvelle méthode unifiée
        orders_without_coords = []
        for order in selected_orders:
            lat, lng, coords_found = self._get_order_coordinates_unified(order)
            if not coords_found:
                orders_without_coords.append(order)
        
        if orders_without_coords:
            raise UserError(
                f"Les clients suivants n'ont pas de coordonnées : "
                f"{', '.join(orders_without_coords.mapped('partner_id.name'))}"
            )
        
        # Récupérer les véhicules disponibles
        vehicles = self.env['fleet.vehicle'].search([
            ('driver_id', '!=', False),
            ('active', '=', True)
        ])
        
        if not vehicles:
            raise UserError("Aucun véhicule avec chauffeur disponible")
        
        # Lancer l'optimisation avec le nouvel optimiseur
        optimizer = self.env['vrp.optimizer.enhanced'].create({})
        result = optimizer.solve_vrp_with_road_distances(selected_orders, vehicles)
        
        if not result or 'routes' not in result:
            raise UserError("Impossible de trouver une solution optimale")
        
        # Appliquer les résultats
        self._apply_optimization_results_enhanced(selected_orders, result, vehicles)
        
        return self._reload_view_with_grouping()

    def _apply_optimization_results_enhanced(self, orders, optimization_result, vehicles):
        """Application des résultats d'optimisation améliorée"""
        # Reset des affectations précédentes
        orders.write({
            'assigned_vehicle_id': False,
            'delivery_sequence': 0
        })
        
        routes = optimization_result['routes']
        vehicle_dict = {v.id: v for v in vehicles}
        
        _logger.info(f"Application des résultats pour {len(routes)} véhicules")
        
        for vehicle_id, order_ids in routes.items():
            if vehicle_id not in vehicle_dict:
                _logger.warning(f"Véhicule {vehicle_id} non trouvé dans la liste")
                continue
                
            _logger.info(f"Véhicule {vehicle_id}: {len(order_ids)} commandes")
            
            for sequence, order_id in enumerate(order_ids):
                order = orders.filtered(lambda o: o.id == order_id)
                if order:
                    order.write({
                        'assigned_vehicle_id': vehicle_id,
                        'delivery_sequence': sequence + 1
                    })
                    _logger.info(f"  - Commande {order.name}: séquence {sequence + 1}")

    def _reload_view_with_grouping(self):
        """Recharger la vue avec groupement par véhicule"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Livraisons Optimisées',
            'res_model': 'sale.order',
            'view_mode': 'tree',
            'view_id': self.env.ref('delivery_vrp.sale_order_vrp_tree_view').id,
            'domain': [('id', 'in', self.ids)],
            'context': {
                'group_by': ['assigned_vehicle_id'],
                'expand': True
            }
        }

    def action_show_map(self):
        """Afficher la carte avec les itinéraires corrigés"""
        selected_orders = self.browse(self.env.context.get('active_ids', []))
        
        if not selected_orders:
            raise UserError("Veuillez sélectionner au moins une commande")
        
        # Préparer les données avec la nouvelle méthode
        vehicles_data = self._prepare_map_data_corrected(selected_orders)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Carte des Itinéraires',
            'res_model': 'vrp.map.view',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicles_data': vehicles_data,
                'dialog_size': 'large'
            }
        }

    def _prepare_map_data_corrected(self, orders):
        """Préparation corrigée des données pour la carte"""
        # Obtenir les coordonnées du dépôt de manière centralisée
        depot_coords = self._get_depot_coordinates()
        
        vehicles_data = []
        
        # Filtrer seulement les commandes optimisées
        optimized_orders = orders.filtered('assigned_vehicle_id')
        
        if not optimized_orders:
            _logger.warning("Aucune commande optimisée trouvée pour la carte")
            return vehicles_data
        
        # Grouper par véhicule
        for vehicle in optimized_orders.mapped('assigned_vehicle_id'):
            if not vehicle:
                continue
            
            vehicle_orders = optimized_orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)
            vehicle_orders = vehicle_orders.sorted('delivery_sequence')
            
            _logger.info(f"Préparation route pour véhicule {vehicle.name}: {len(vehicle_orders)} commandes")
            
            # Point de départ - dépôt
            depot_waypoint = {
                'lat': depot_coords['latitude'],
                'lng': depot_coords['longitude'],
                'name': 'Dépôt - Rabat',
                'address': 'Point de départ des livraisons',
                'sequence': 0,
                'type': 'depot'
            }
            
            waypoints = [depot_waypoint]
            
            # Ajouter les points clients dans l'ordre de séquence
            for order in vehicle_orders:
                lat, lng, coords_found = self._get_order_coordinates_unified(order)
                
                if coords_found:
                    waypoint = {
                        'lat': lat,
                        'lng': lng,
                        'name': order.partner_id.name or 'Client',
                        'address': order.partner_id.contact_address or 'Adresse non disponible',
                        'sequence': order.delivery_sequence,
                        'order_name': order.name,
                        'type': 'customer'
                    }
                    waypoints.append(waypoint)
                    _logger.info(f"  ✓ Waypoint ajouté: {order.name} (seq: {order.delivery_sequence})")
                else:
                    _logger.warning(f"  ✗ Coordonnées invalides pour {order.name}")
            
            # Retour au dépôt (optionnel)
            depot_return = depot_waypoint.copy()
            depot_return['name'] = 'Retour Dépôt'
            depot_return['sequence'] = len(waypoints)
            depot_return['type'] = 'depot_return'
            waypoints.append(depot_return)
            
            # Ajouter le véhicule seulement s'il a au moins un client
            if len(waypoints) > 2:  # Dépôt + au moins 1 client + retour
                vehicles_data.append({
                    'vehicle_name': vehicle.name or f'Véhicule {vehicle.id}',
                    'vehicle_id': vehicle.id,
                    'driver_name': vehicle.driver_id.name if vehicle.driver_id else 'Chauffeur non assigné',
                    'waypoints': waypoints,
                    'total_stops': len(waypoints) - 2,  # Exclure dépôt départ et retour
                    'vehicle_color': self._get_vehicle_color_for_map(vehicle.id)
                })
                _logger.info(f"✓ Véhicule {vehicle.name} ajouté avec {len(waypoints)} waypoints")
        
        _logger.info(f"Données carte préparées: {len(vehicles_data)} véhicules")
        return vehicles_data

    def _get_vehicle_color_for_map(self, vehicle_id):
        """Attribuer une couleur unique à chaque véhicule"""
        colors = [
            '#e74c3c',  # Rouge
            '#3498db',  # Bleu
            '#2ecc71',  # Vert
            '#f39c12',  # Orange
            '#9b59b6',  # Violet
            '#1abc9c',  # Turquoise
            '#e67e22',  # Orange foncé
            '#34495e'   # Gris foncé
        ]
        return colors[vehicle_id % len(colors)]