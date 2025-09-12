# models/sale_order_enhanced.py - VERSION CORRIGÉE
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class SaleOrderEnhanced(models.Model):
    _inherit = 'sale.order'
    
    # Nouveaux champs pour l'optimisation avancée
    route_optimization_id = fields.Many2one(
        'vrp.route.optimization', 
        string='Optimization Session',
        help="Session d'optimisation qui a généré cette affectation"
    )
    
    estimated_delivery_time = fields.Float(
        string='Temps de Livraison Estimé (min)',
        help="Temps estimé pour cette livraison basé sur la distance routière"
    )
    
    road_distance_to_depot = fields.Float(
        string='Distance Routière (km)',
        help="Distance routière réelle depuis le dépôt"
    )
    
    delivery_status = fields.Selection([
        ('pending', 'En Attente'),
        ('optimized', 'Optimisé'),
        ('in_progress', 'En Cours'),
        ('delivered', 'Livré'),
        ('failed', 'Échec')
    ], string='Statut de Livraison', default='pending')

    def action_optimize_delivery_enhanced(self):
        """Action d'optimisation améliorée avec gestion robuste des IDs"""
        # CORRECTION PRINCIPALE : Gestion sécurisée des active_ids
        active_ids = self.env.context.get('active_ids', [])
        
        if not active_ids:
            # Si pas d'active_ids, utiliser self
            selected_orders = self
        else:
            # SÉCURISATION : Vérifier que les IDs existent encore
            try:
                existing_orders = self.env['sale.order'].browse(active_ids).exists()
                if not existing_orders:
                    # Si aucun ID valide, essayer de récupérer toutes les commandes disponibles
                    available_orders = self.env['sale.order'].search([
                        ('state', 'in', ['sale', 'done']),
                        ('partner_id', '!=', False)
                    ])
                    if not available_orders:
                        raise UserError(
                            "Aucune commande valide trouvée pour l'optimisation. "
                            "Veuillez créer des commandes de vente confirmées."
                        )
                    selected_orders = available_orders
                else:
                    selected_orders = existing_orders
            except Exception as e:
                _logger.error(f"Erreur lors de la récupération des commandes: {str(e)}")
                raise UserError(
                    "Erreur lors de la sélection des commandes. "
                    "Veuillez actualiser la page et réessayer."
                )
        
        if not selected_orders:
            raise UserError("Veuillez sélectionner au moins une commande valide")

        _logger.info(f"Processing {len(selected_orders)} valid orders for optimization")

        # Forcer le recalcul des coordonnées avant validation  
        self._ensure_coordinates_computed(selected_orders)  
        
        # Validation préalable
        self._validate_orders_for_optimization(selected_orders)
        
        # Créer une session d'optimisation
        optimization_session = self._create_optimization_session(selected_orders)
        
        # Lancer l'optimisation avec l'algorithme amélioré
        try:
            result = self._run_enhanced_optimization(selected_orders, optimization_session)
            
            if result:
                # Appliquer les résultats
                self._apply_enhanced_results(selected_orders, result, optimization_session)
                
                # Notification de succès simple
                total_distance_km = result['total_distance'] / 1000
                vehicles_used = len(result['routes'])
                total_stops = result['total_stops']
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Optimisation VRP Terminée',
                        'message': f'Optimisation réussie: {total_distance_km:.1f} km, {vehicles_used} véhicules, {total_stops} arrêts',
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                raise UserError("Impossible de trouver une solution optimale")
                
        except Exception as e:
            _logger.error(f"Optimization failed: {str(e)}")
            optimization_session.write({'status': 'failed', 'error_message': str(e)})
            raise UserError(f"Erreur d'optimisation: {str(e)}")

    def _ensure_coordinates_computed(self, orders):  
        """Forcer le recalcul des coordonnées GPS depuis le JSON"""  
        # Forcer le recalcul pour les VRP orders liés  
        vrp_orders = self.env['vrp.order'].search([  
            ('sale_order_id', 'in', orders.ids)  
        ])  
        if vrp_orders:  
            # Déclencher manuellement le recalcul  
            for vrp_order in vrp_orders:  
                vrp_order._compute_coordinates()
                
    def _validate_orders_for_optimization(self, orders):
        """Validation robuste avec gestion des coordonnées multiples"""
        orders_without_coords = []
        
        for order in orders:
            partner = order.partner_id
            if not partner:
                orders_without_coords.append(order)
                continue
                
            coordinates = partner.coordinates
            
            # Variables pour stocker les coordonnées trouvées
            lat, lng = 0.0, 0.0
            coords_found = False
            
            # 1. Essayer d'abord les coordonnées JSON du partenaire
            if coordinates and isinstance(coordinates, dict):
                try:
                    lat = float(coordinates.get('latitude', 0.0))
                    lng = float(coordinates.get('longitude', 0.0))
                    
                    # Validation des coordonnées
                    if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 and lng != 0.0):
                        coords_found = True
                except (ValueError, TypeError):
                    pass
            
            # 2. Si pas de coordonnées JSON, essayer les VRP orders liés
            if not coords_found:
                vrp_order = self.env['vrp.order'].search([
                    ('sale_order_id', '=', order.id)
                ], limit=1)
                
                if vrp_order:
                    # Forcer le recalcul des coordonnées
                    vrp_order._compute_coordinates()
                    
                    if vrp_order.partner_latitude and vrp_order.partner_longitude:
                        if (vrp_order.partner_latitude != 0.0 and vrp_order.partner_longitude != 0.0):
                            coords_found = True
            
            # 3. Si toujours pas de coordonnées, essayer les champs directs du partenaire
            if not coords_found:
                if hasattr(partner, 'partner_latitude') and hasattr(partner, 'partner_longitude'):
                    if partner.partner_latitude and partner.partner_longitude:
                        if (partner.partner_latitude != 0.0 and partner.partner_longitude != 0.0):
                            coords_found = True
            
            if not coords_found:
                orders_without_coords.append(order)
        
        if orders_without_coords:
            missing_partners = [o.partner_id.name or 'Client sans nom' for o in orders_without_coords]
            
            # Message d'erreur informatif avec solutions
            error_msg = f"Les clients suivants n'ont pas de coordonnées GPS valides :\n"
            error_msg += f"• {chr(10).join(missing_partners)}\n\n"
            error_msg += f"Solutions possibles :\n"
            error_msg += f"1. Vérifiez que les adresses des clients sont complètes\n"
            error_msg += f"2. Utilisez la géolocalisation automatique si disponible\n"
            error_msg += f"3. Ajoutez manuellement les coordonnées GPS dans le champ 'coordinates'"
            
            raise UserError(error_msg)

    def _create_optimization_session(self, orders):
        """Créer une session d'optimisation pour tracer les résultats"""
        return self.env['vrp.route.optimization'].create({
            'name': f'Optimization {fields.Datetime.now().strftime("%Y-%m-%d %H:%M")}',
            'order_ids': [(6, 0, orders.ids)],
            'status': 'running',
            'user_id': self.env.user.id,
            'company_id': self.env.company.id
        })

    def _run_enhanced_optimization(self, orders, session):
        """Exécuter l'optimisation avec l'algorithme amélioré"""
        # Récupérer les véhicules disponibles
        vehicles = self.env['fleet.vehicle'].search([
            ('driver_id', '!=', False),
            ('active', '=', True)
        ])
        
        if not vehicles:
            raise UserError("Aucun véhicule avec chauffeur disponible")
        
        # Créer l'optimiseur amélioré
        optimizer = self.env['vrp.optimizer.enhanced'].create({})
        
        # Lancer l'optimisation avec distances routières
        _logger.info(f"Starting enhanced VRP optimization for session {session.id}")
        result = optimizer.solve_vrp_with_road_distances(orders, vehicles)
        
        if result:
            _logger.info(f"Routes retournées : {result['routes']}")
            for vehicle_id, order_ids in result['routes'].items():
                _logger.info(f"Véhicule {vehicle_id}: commandes {order_ids}")
            # Enregistrer les statistiques de la session
            session.write({
                'status': 'completed',
                'total_distance': result['total_distance'],
                'total_stops': result['total_stops'],
                'vehicles_used': len(result['routes']),
                'optimization_stats': str(result['stats'])
            })
        
        return result

    def _apply_enhanced_results(self, orders, result, session):
        """Appliquer les résultats de l'optimisation améliorée"""
        # Reset des affectations précédentes
        orders.write({
            'assigned_vehicle_id': False,
            'delivery_sequence': 0,
        })

        routes = result['routes']
        orders_dict = {order.id: order for order in orders}

        for vehicle_id, order_ids in routes.items():
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
            
            for sequence, order_id in enumerate(order_ids):
                if order_id in orders_dict:
                    order = orders_dict[order_id]
                    order.write({
                        'assigned_vehicle_id': vehicle_id,
                        'delivery_sequence': sequence + 1,
                    })
                    _logger.info(f"Commande {order.name} assignée au véhicule {vehicle.name}, séquence {sequence + 1}")

        # SYNCHRONISATION AUTOMATIQUE des VRP orders
        for order in orders.filtered('assigned_vehicle_id'):
            # Trouver le VRP order correspondant
            vrp_order = self.env['vrp.order'].search([
                ('sale_order_id', '=', order.id)
            ], limit=1)
        
            if vrp_order:
                vrp_order.write({
                    'assigned_vehicle_id': order.assigned_vehicle_id.id,
                    'delivery_sequence': order.delivery_sequence,
                })
                _logger.info(f"VRP Order synchronisé: {vrp_order.name} -> Véhicule: {order.assigned_vehicle_id.name}")

        _logger.info(f"VRP Orders synchronisés: {len(orders.filtered('assigned_vehicle_id'))} commandes")

    # Reste du code inchangé...
    def action_show_enhanced_map(self):
        """Afficher la carte avec itinéraires et métriques détaillées"""
        selected_orders = self.browse(self.env.context.get('active_ids', []))
        
        if not selected_orders:
            raise UserError("Veuillez sélectionner au moins une commande")

        optimized_orders = selected_orders.filtered('assigned_vehicle_id')
        if not optimized_orders:
            raise UserError("Les commandes sélectionnées ne sont pas encore optimisées")

        # Préparer les données enrichies pour la carte
        map_data = self._prepare_enhanced_map_data(optimized_orders)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Carte des Itinéraires Optimisés',
            'res_model': 'vrp.enhanced.map.view',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_map_data': map_data,
                'default_show_metrics': True
            }
        }

    def _prepare_enhanced_map_data(self, orders):
        """Préparer les données enrichies pour l'affichage cartographique"""
        company = self.env.company
        
        # Point de dépôt
        depot = {
            'lat': company.vrp_depot_latitude,
            'lng': company.vrp_depot_longitude,
            'name': 'Dépôt Central',
            'type': 'depot'
        }
        
        vehicles_data = []
        
        # Grouper par véhicule et préparer les données
        for vehicle in orders.mapped('assigned_vehicle_id'):
            if not vehicle:
                continue
                
            vehicle_orders = orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)
            vehicle_orders = vehicle_orders.sorted('delivery_sequence')
            
            waypoints = [depot]  # Commencer par le dépôt
            total_distance = 0
            total_time = 0
            
            for order in vehicle_orders:
                waypoint = {
                    'lat': order.partner_latitude,
                    'lng': order.partner_longitude,
                    'name': order.partner_id.name,
                    'address': order.partner_id.contact_address,
                    'sequence': order.delivery_sequence,
                    'order_name': order.name,
                    'estimated_time': order.estimated_delivery_time,
                    'type': 'customer'
                }
                waypoints.append(waypoint)
                total_distance += order.road_distance_to_depot or 0
                total_time += order.estimated_delivery_time or 0
            
            # Retour au dépôt
            waypoints.append(depot)
            
            vehicles_data.append({
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.name,
                'vehicle_plate': vehicle.license_plate,
                'driver_name': vehicle.driver_id.name,
                'driver_phone': vehicle.driver_id.phone,
                'waypoints': waypoints,
                'total_distance': total_distance,
                'total_time': total_time,
                'total_stops': len(vehicle_orders),
                'vehicle_color': self._get_vehicle_color(vehicle.id)
            })
        
        return {
            'vehicles': vehicles_data,
            'depot': depot,
            'optimization_summary': {
                'total_vehicles': len(vehicles_data),
                'total_orders': len(orders),
                'total_distance': sum(v['total_distance'] for v in vehicles_data),
                'total_time': sum(v['total_time'] for v in vehicles_data)
            }
        }

    def _get_vehicle_color(self, vehicle_id):
        """Attribuer une couleur unique à chaque véhicule"""
        colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', 
            '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
        ]
        return colors[vehicle_id % len(colors)]


# Modèle pour tracer les sessions d'optimisation
class VRPRouteOptimization(models.Model):
    _name = 'vrp.route.optimization'
    _description = 'VRP Route Optimization Session'
    _order = 'create_date desc'

    name = fields.Char('Session Name', required=True)
    user_id = fields.Many2one('res.users', 'Optimized By', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True)
    order_ids = fields.Many2many('sale.order', string='Session Orders')

    status = fields.Selection([
        ('running', 'En Cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échec')
    ], 'Status', default='running')
    
    total_distance = fields.Float('Distance Totale (m)')
    total_stops = fields.Integer('Arrêts Totaux')
    vehicles_used = fields.Integer('Véhicules Utilisés')
    optimization_stats = fields.Text('Statistics JSON')
    error_message = fields.Text('Error Message')
    
    create_date = fields.Datetime('Created On', default=fields.Datetime.now)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.total_stops} arrêts, {record.vehicles_used} véhicules)"
            result.append((record.id, name))
        return result