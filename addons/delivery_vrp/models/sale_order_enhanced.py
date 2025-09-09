# models/sale_order_enhanced.py
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
        """Action d'optimisation améliorée avec distances routières"""
        selected_orders = self.browse(self.env.context.get('active_ids', []))
        
        if not selected_orders:
            raise UserError("Veuillez sélectionner au moins une commande")

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
                
                # Notification de succès
                self._show_optimization_summary(result)
                
                return self._reload_optimized_view(selected_orders)
            else:
                raise UserError("Impossible de trouver une solution optimale")
                
        except Exception as e:
            _logger.error(f"Optimization failed: {str(e)}")
            optimization_session.write({'status': 'failed', 'error_message': str(e)})
            raise UserError(f"Erreur d'optimisation: {str(e)}")

    def _validate_orders_for_optimization(self, orders):
        """Validation complète des commandes avant optimisation"""
        # Vérifier les coordonnées
        orders_without_coords = orders.filtered(
            lambda o: not o.partner_latitude or not o.partner_longitude
        )
        if orders_without_coords:
            missing_partners = orders_without_coords.mapped('partner_id.name')
            raise UserError(
                f"Les clients suivants n'ont pas de coordonnées GPS :\n"
                f"• {chr(10).join(missing_partners)}\n\n"
                f"Veuillez mettre à jour leurs adresses avec les coordonnées géographiques."
            )
        
        # Vérifier les véhicules disponibles
        available_vehicles = self.env['fleet.vehicle'].search([
            ('driver_id', '!=', False),
            ('active', '=', True),
            ('state_id.name', 'not in', ['En Réparation', 'Hors Service'])
        ])
        
        if not available_vehicles:
            raise UserError("Aucun véhicule avec chauffeur disponible")
        
        # Vérifier la configuration du dépôt
        company = self.env.company
        if not company.vrp_depot_latitude or not company.vrp_depot_longitude:
            raise UserError(
                "Coordonnées du dépôt non configurées.\n"
                "Allez dans Configuration > VRP Configuration pour définir l'emplacement de votre dépôt."
            )
        
        _logger.info(f"Validation completed: {len(orders)} orders, {len(available_vehicles)} vehicles available")

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
        
        # Créer l'optimiseur amélioré
        optimizer = self.env['vrp.optimizer.enhanced'].create({})
        
        # Lancer l'optimisation avec distances routières
        _logger.info(f"Starting enhanced VRP optimization for session {session.id}")
        result = optimizer.solve_vrp_with_road_distances(orders, vehicles)
        
        if result:
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
            'route_optimization_id': False,
            'estimated_delivery_time': 0,
            'road_distance_to_depot': 0,
            'delivery_status': 'pending'
        })

        routes = result['routes']
        stats = result['stats']
        orders_dict = {order.id: order for order in orders}

        for vehicle_id, order_ids in routes.items():
            vehicle_stats = stats.get(vehicle_id, {})
            
            for sequence, order_id in enumerate(order_ids):
                if order_id in orders_dict:
                    order = orders_dict[order_id]
                    
                    # Calculer le temps de livraison estimé (basé sur distance et vitesse moyenne)
                    avg_speed_kmh = 40  # Vitesse moyenne en ville
                    distance_km = vehicle_stats.get('distance', 0) / 1000
                    estimated_time = (distance_km / avg_speed_kmh) * 60  # en minutes
                    
                    order.write({
                        'assigned_vehicle_id': vehicle_id,
                        'delivery_sequence': sequence + 1,
                        'route_optimization_id': session.id,
                        'estimated_delivery_time': estimated_time / len(order_ids),  # Répartir le temps
                        'road_distance_to_depot': distance_km / len(order_ids),  # Distance moyenne
                        'delivery_status': 'optimized'
                    })

        _logger.info(f"Applied optimization results: {len(routes)} routes created")

    def _show_optimization_summary(self, result):
        """Afficher un résumé de l'optimisation"""
        total_distance_km = result['total_distance'] / 1000
        vehicles_used = len(result['routes'])
        total_stops = result['total_stops']
        
        # Calculer les économies par rapport à l'approche naïve
        naive_distance = total_stops * 20  # Estimation naïve: 20km par client
        savings_percent = ((naive_distance - total_distance_km) / naive_distance) * 100 if naive_distance > 0 else 0
        
        message = f"""
        <div class="alert alert-success">
            <h4><i class="fa fa-check-circle"/> Optimisation Terminée avec Succès</h4>
            <ul class="list-unstyled">
                <li><strong>📏 Distance totale:</strong> {total_distance_km:.1f} km</li>
                <li><strong>🚚 Véhicules utilisés:</strong> {vehicles_used}</li>
                <li><strong>📍 Arrêts totaux:</strong> {total_stops}</li>
                <li><strong>💰 Économie estimée:</strong> {savings_percent:.1f}%</li>
            </ul>
        </div>
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Optimisation VRP',
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }

    def _reload_optimized_view(self, orders):
        """Recharger la vue avec les résultats d'optimisation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Livraisons Optimisées',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'view_id': self.env.ref('vrp_module.sale_order_vrp_optimized_tree_view').id,
            'domain': [('id', 'in', orders.ids)],
            'context': {
                'group_by': ['assigned_vehicle_id'],
                'expand': True,
                'search_default_optimized': 1
            }
        }

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
    order_ids = fields.Many2many('sale.order', 'Session Orders')
    
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