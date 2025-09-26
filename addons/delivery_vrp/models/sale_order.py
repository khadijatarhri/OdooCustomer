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

    # models/sale_order.py - MODIFICATIONS POUR DÉPÔT PAR CHAUFFEUR

# Ajouter ces méthodes modifiées à votre classe SaleOrder existante

 def _get_depot_coordinates(self):
    """OBSOLÈTE: Cette méthode n'est plus utilisée avec les dépôts par chauffeur"""
    # Gardé pour compatibilité mais non utilisé
    return {'latitude': 34.0209, 'longitude': -6.8416}

 def _get_driver_coordinates_for_vehicle(self, vehicle):
    """NOUVEAU: Récupérer les coordonnées d'un chauffeur de véhicule"""
    if not vehicle or not vehicle.driver_id:
        _logger.warning(f"Véhicule {vehicle.name if vehicle else 'None'} sans chauffeur")
        return None, None, False
    
    driver = vehicle.driver_id
    
    # 1. Essayer les coordonnées JSON du chauffeur
    if driver.coordinates and isinstance(driver.coordinates, dict):
        try:
            lat = float(driver.coordinates.get('latitude', 0.0))
            lng = float(driver.coordinates.get('longitude', 0.0))
            
            if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 and lng != 0.0):
                _logger.info(f"✓ Coordonnées chauffeur {driver.name}: {lat}, {lng}")
                return lat, lng, True
        except (ValueError, TypeError):
            pass
    
    # 2. Essayer les champs directs
    if hasattr(driver, 'partner_latitude') and hasattr(driver, 'partner_longitude'):
        if driver.partner_latitude and driver.partner_longitude:
            if (driver.partner_latitude != 0.0 and driver.partner_longitude != 0.0):
                return driver.partner_latitude, driver.partner_longitude, True
    
    _logger.warning(f"✗ Aucune coordonnée pour chauffeur {driver.name}")
    return None, None, False

 def action_optimize_delivery_enhanced(self):
    """MODIFIÉ: Action d'optimisation avec dépôts par chauffeur"""
    selected_orders = self.browse(self.env.context.get('active_ids', []))
    
    if not selected_orders:
        raise UserError("Veuillez sélectionner au moins une commande")
    
    # Vérifier les coordonnées des commandes
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
    
    # Récupérer les véhicules avec chauffeurs géolocalisés
    vehicles = self.env['fleet.vehicle'].search([
        ('driver_id', '!=', False),
        ('active', '=', True)
    ])
    
    if not vehicles:
        raise UserError("Aucun véhicule avec chauffeur disponible")
    
    # Vérifier que les chauffeurs ont des coordonnées
    valid_vehicles = []
    for vehicle in vehicles:
        lat, lng, coords_found = self._get_driver_coordinates_for_vehicle(vehicle)
        if coords_found:
            valid_vehicles.append(vehicle)
        else:
            _logger.warning(f"Véhicule {vehicle.name} ignoré - chauffeur sans coordonnées")
    
    if not valid_vehicles:
        raise UserError(
            "Aucun véhicule avec chauffeur géolocalisé disponible. "
            "Veuillez ajouter les coordonnées GPS des chauffeurs dans leurs fiches contact."
        )
    
    # Lancer l'optimisation avec le nouvel algorithme
    optimizer = self.env['vrp.optimizer.enhanced'].create({})
    result = optimizer.solve_vrp_with_driver_based_depots(selected_orders, valid_vehicles)
    
    if not result or 'routes' not in result:
        raise UserError("Impossible de trouver une solution optimale")
    
    # Appliquer les résultats
    self._apply_optimization_results_enhanced(selected_orders, result, valid_vehicles)
    
    return self._reload_view_with_grouping()

 def _prepare_map_data_corrected(self, orders):
    """MODIFIÉ: Préparation données carte avec dépôts par chauffeur"""
    vehicles_data = []
    
    _logger.info("=== PRÉPARATION CARTE AVEC DÉPÔTS CHAUFFEURS ===")
    _logger.info(f"Commandes reçues: {len(orders)}")
    
    # Filtrer seulement les commandes optimisées
    optimized_orders = orders.filtered('assigned_vehicle_id')
    
    if not optimized_orders:
        _logger.warning("Aucune commande optimisée trouvée pour la carte")
        return vehicles_data
    
    _logger.info(f"Commandes optimisées: {len(optimized_orders)}")
    
    # Grouper par véhicule
    vehicles = optimized_orders.mapped('assigned_vehicle_id')
    _logger.info(f"Véhicules trouvés: {[v.name for v in vehicles]}")
    
    for vehicle in vehicles:
        if not vehicle:
            continue
        
        # Récupérer les coordonnées du chauffeur (nouveau dépôt)
        driver_lat, driver_lng, driver_coords_found = self._get_driver_coordinates_for_vehicle(vehicle)
        
        if not driver_coords_found:
            _logger.warning(f"❌ Véhicule {vehicle.name} ignoré - pas de coordonnées chauffeur")
            continue
        
        # Commandes triées par séquence pour ce véhicule
        vehicle_orders = optimized_orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)
        vehicle_orders = vehicle_orders.sorted(lambda x: x.delivery_sequence or 0)
        
        _logger.info(f"=== VÉHICULE {vehicle.name} ===")
        _logger.info(f"Coordonnées chauffeur: {driver_lat}, {driver_lng}")
        _logger.info(f"Commandes triées: {[(o.name, o.delivery_sequence) for o in vehicle_orders]}")
        
        waypoints = []
        
        # 1. DÉPART: Position du chauffeur (nouveau dépôt)
        driver_waypoint = {
            'lat': float(driver_lat),
            'lng': float(driver_lng),
            'name': f'Départ - {vehicle.driver_id.name}',
            'address': f'Position chauffeur: {vehicle.driver_id.name}',
            'sequence': 0,
            'type': 'driver_depot',
            'driver_name': vehicle.driver_id.name,
            'vehicle_name': vehicle.name
        }
        waypoints.append(driver_waypoint)
        _logger.info(f"  ✅ Dépôt chauffeur ajouté: {driver_lat}, {driver_lng}")
        
        # 2. Clients dans l'ordre de livraison
        clients_added = 0
        for order in vehicle_orders:
            lat, lng, coords_found = self._get_order_coordinates_unified(order)
            
            if coords_found:
                waypoint = {
                    'lat': float(lat),
                    'lng': float(lng),
                    'name': order.partner_id.name or 'Client',
                    'address': self._get_clean_address(order.partner_id),
                    'sequence': order.delivery_sequence,
                    'order_name': order.name,
                    'type': 'customer'
                }
                waypoints.append(waypoint)
                clients_added += 1
                _logger.info(f"  ✅ Client: {order.name} - Séq: {order.delivery_sequence}")
            else:
                _logger.warning(f"  ❌ Coordonnées manquantes: {order.name}")
        
        # 3. RETOUR: Position du chauffeur (fin de tournée)
        if clients_added > 0:
            driver_return = {
                'lat': float(driver_lat),
                'lng': float(driver_lng),
                'name': f'Retour - {vehicle.driver_id.name}',
                'address': f'Retour position chauffeur: {vehicle.driver_id.name}',
                'sequence': len(waypoints),
                'type': 'driver_depot_return',
                'driver_name': vehicle.driver_id.name
            }
            waypoints.append(driver_return)
            _logger.info(f"  ✅ Retour chauffeur ajouté")
            
            # Données véhicule pour la carte
            vehicle_data = {
                'vehicle_name': vehicle.name or f'Véhicule {vehicle.id}',
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_id.name if vehicle.driver_id else 'Chauffeur non assigné',
                'driver_coords': {  # Nouvelles infos chauffeur
                    'lat': driver_lat,
                    'lng': driver_lng,
                    'name': vehicle.driver_id.name
                },
                'waypoints': waypoints,
                'total_stops': clients_added,
                'vehicle_color': self._get_vehicle_color_for_map(vehicle.id),
                'depot_type': 'driver_based'  # Indicateur du type de dépôt
            }
            vehicles_data.append(vehicle_data)
            
            _logger.info(f"✅ {vehicle.name} - {len(waypoints)} waypoints, dépôt: chauffeur")
        else:
            _logger.warning(f"❌ Véhicule {vehicle.name} ignoré - aucun client valide")
    
    _logger.info(f"=== DONNÉES CARTE FINALES ===")
    _logger.info(f"Véhicules avec dépôts chauffeurs: {len(vehicles_data)}")
    
    return vehicles_data

 def action_show_map(self):
    """MODIFIÉ: Affichage carte avec nouvelles données chauffeur"""
    selected_orders = self.browse(self.env.context.get('active_ids', []))
    
    _logger.info("=== AFFICHAGE CARTE AVEC DÉPÔTS CHAUFFEURS ===")
    _logger.info(f"Commandes sélectionnées: {len(selected_orders)}")
    
    if not selected_orders:
        raise UserError("Veuillez sélectionner au moins une commande")
    
    # Vérifier qu'il y a des commandes optimisées
    optimized_orders = selected_orders.filtered('assigned_vehicle_id')
    if not optimized_orders:
        raise UserError(
            "Aucune commande optimisée trouvée. "
            "Veuillez d'abord lancer l'optimisation des livraisons avec dépôts chauffeurs."
        )
    
    # Préparer les données avec dépôts chauffeurs
    vehicles_data = self._prepare_map_data_corrected(selected_orders)
    
    _logger.info(f"Données préparées: {len(vehicles_data)} véhicules")
    
    # Validation spéciale pour dépôts chauffeurs
    if not vehicles_data:
        raise UserError(
            "Aucune donnée d'itinéraire générée. "
            "Vérifiez que les chauffeurs ont des coordonnées GPS dans leurs fiches contact."
        )
    
    # Vérification que chaque véhicule a des waypoints valides
    valid_vehicles = []
    for vehicle_data in vehicles_data:
        waypoints = vehicle_data.get('waypoints', [])
        driver_coords = vehicle_data.get('driver_coords', {})
        
        if waypoints and len(waypoints) > 1 and driver_coords:
            valid_vehicles.append(vehicle_data)
            _logger.info(f"✅ {vehicle_data['vehicle_name']} valide - {len(waypoints)} waypoints")
        else:
            _logger.warning(f"❌ {vehicle_data.get('vehicle_name', 'Unknown')} ignoré")
    
    if not valid_vehicles:
        raise UserError(
            "Aucun itinéraire valide trouvé. "
            "Vérifiez les coordonnées des chauffeurs et des clients."
        )
    
    # Sérialisation JSON avec données chauffeurs
    try:
        import json
        vehicles_json = json.dumps(valid_vehicles, ensure_ascii=False, indent=2)
        _logger.info(f"JSON généré pour {len(valid_vehicles)} véhicules avec dépôts chauffeurs")
    except Exception as e:
        _logger.error(f"❌ ERREUR SÉRIALISATION JSON: {e}")
        raise UserError(f"Erreur génération données carte: {e}")
    
    # Créer l'enregistrement map view
    try:
        map_view = self.env['vrp.map.view'].create({
            'vehicles_data': vehicles_json
        })
        _logger.info(f"✅ Map View créé avec dépôts chauffeurs: ID {map_view.id}")
    except Exception as e:
        _logger.error(f"❌ ERREUR CRÉATION MAP VIEW: {e}")
        raise UserError(f"Erreur création vue carte: {e}")
    
    return {
        'type': 'ir.actions.act_window',
        'name': 'Carte Itinéraires VRP - Dépôts Chauffeurs',
        'res_model': 'vrp.map.view',
        'res_id': map_view.id,
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'dialog_size': 'large',
            'default_vehicles_data': valid_vehicles,
            'depot_type': 'driver_based'
        }
    }

 def action_test_driver_coordinates(self):
    """NOUVEAU: Tester les coordonnées des chauffeurs"""
    vehicles = self.env['fleet.vehicle'].search([
        ('driver_id', '!=', False),
        ('active', '=', True)
    ])
    
    if not vehicles:
        raise UserError("Aucun véhicule avec chauffeur trouvé")
    
    results = []
    for vehicle in vehicles:
        driver_lat, driver_lng, coords_found = self._get_driver_coordinates_for_vehicle(vehicle)
        
        results.append({
            'vehicle': vehicle.name,
            'driver': vehicle.driver_id.name,
            'coordinates_found': coords_found,
            'lat': driver_lat if coords_found else 'N/A',
            'lng': driver_lng if coords_found else 'N/A'
        })
    
    # Créer un message détaillé
    message_lines = ["=== TEST COORDONNÉES CHAUFFEURS ===\n"]
    valid_count = 0
    
    for result in results:
        status = "✅" if result['coordinates_found'] else "❌"
        message_lines.append(
            f"{status} {result['vehicle']} - {result['driver']}: "
            f"{result['lat']}, {result['lng']}"
        )
        if result['coordinates_found']:
            valid_count += 1
    
    message_lines.append(f"\nRésultat: {valid_count}/{len(results)} chauffeurs géolocalisés")
    
    if valid_count == 0:
        message_lines.append("\n⚠️  ATTENTION: Aucun chauffeur géolocalisé!")
        message_lines.append("Ajoutez des coordonnées GPS dans les fiches contact des chauffeurs.")
    
    message = "\n".join(message_lines)
    
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': f'Test Coordonnées Chauffeurs',
            'message': message,
            'type': 'success' if valid_count > 0 else 'warning',
            'sticky': True,
        }
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

   

 def _apply_optimization_results_enhanced(self, orders, optimization_result, vehicles):
     """Application des résultats d'optimisation améliorée avec debugging complet"""
    
     _logger.info("=== APPLICATION RÉSULTATS OPTIMISATION ===")
     _logger.info(f"Commandes à traiter: {len(orders)}")
     _logger.info(f"Véhicules disponibles: {[v.name for v in vehicles]}")
    
    # Reset des affectations précédentes
     reset_count = orders.write({
        'assigned_vehicle_id': False,
        'delivery_sequence': 0
     })
     _logger.info(f"Reset effectué sur {len(orders)} commandes")
    
     routes = optimization_result.get('routes', {})
     stats = optimization_result.get('stats', {})
     vehicle_dict = {v.id: v for v in vehicles}
    
     _logger.info(f"Routes à appliquer: {len(routes)} véhicules")
    
     total_applied = 0
     for vehicle_id, order_ids in routes.items():
        if vehicle_id not in vehicle_dict:
            _logger.warning(f"❌ Véhicule {vehicle_id} non trouvé dans la liste disponible")
            continue
        
        vehicle = vehicle_dict[vehicle_id]
        _logger.info(f"\n--- APPLICATION VÉHICULE {vehicle.name} (ID: {vehicle_id}) ---")
        _logger.info(f"Commandes à assigner: {len(order_ids)}")
        
        orders_applied_for_vehicle = 0
        for sequence, order_id in enumerate(order_ids, start=1):  # Commencer à 1 pour la séquence
            # Trouver la commande dans notre liste
            order = orders.filtered(lambda o: o.id == order_id)
            
            if order:
                # Appliquer l'assignation
                try:
                    order.write({
                        'assigned_vehicle_id': vehicle_id,
                        'delivery_sequence': sequence,
                        'manual_assignment': False  # Marquer comme assignation automatique
                    })
                    orders_applied_for_vehicle += 1
                    total_applied += 1
                    _logger.info(f"  ✅ Commande {order.name} (ID: {order.id}): séquence {sequence}")
                    
                except Exception as e:
                    _logger.error(f"  ❌ Erreur assignation commande {order_id}: {e}")
            else:
                _logger.warning(f"  ⚠️  Commande {order_id} non trouvée dans la liste d'entrée")
        
        # Vérification des stats pour ce véhicule
        vehicle_stats = stats.get(vehicle_id, {})
        if vehicle_stats:
            distance_km = vehicle_stats.get('distance', 0) / 1000
            stops = vehicle_stats.get('stops', 0)
            _logger.info(f"  📊 Stats véhicule: {stops} arrêts, {distance_km:.2f}km")
        
        _logger.info(f"  ✅ {vehicle.name}: {orders_applied_for_vehicle}/{len(order_ids)} commandes appliquées")
    
    # Vérification finale
     _logger.info(f"\n=== VÉRIFICATION FINALE APPLICATION ===")
     _logger.info(f"Total commandes appliquées: {total_applied}")
    
    # Vérifier que toutes les commandes ont bien été assignées
     assigned_orders = orders.filtered('assigned_vehicle_id')
     unassigned_orders = orders.filtered(lambda o: not o.assigned_vehicle_id)
    
     _logger.info(f"Commandes assignées après application: {len(assigned_orders)}")
     _logger.info(f"Commandes non assignées: {len(unassigned_orders)}")
    
     if unassigned_orders:
        _logger.warning("❌ COMMANDES NON ASSIGNÉES:")
        for order in unassigned_orders:
            _logger.warning(f"  - {order.name} (ID: {order.id})")
    
    # Log détaillé des assignations finales
     for vehicle in assigned_orders.mapped('assigned_vehicle_id'):
        vehicle_orders = assigned_orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)
        vehicle_orders = vehicle_orders.sorted('delivery_sequence')
        _logger.info(f"\n{vehicle.name} - Assignations finales:")
        for order in vehicle_orders:
            _logger.info(f"  Seq {order.delivery_sequence}: {order.name} (ID: {order.id})")
    
     return {
        'total_applied': total_applied,
        'assigned_count': len(assigned_orders),
        'unassigned_count': len(unassigned_orders)
     }

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

   

 def _get_clean_address(self, partner):
     """Obtenir une adresse propre du partenaire"""
     if not partner:
        return 'Adresse non disponible'
    
     address_parts = []
     if partner.street:
        address_parts.append(partner.street)
     if partner.street2:
        address_parts.append(partner.street2)
     if partner.city:
        address_parts.append(partner.city)
     if partner.zip:
        address_parts.append(partner.zip)
    
     return ', '.join(address_parts) if address_parts else partner.name or 'Adresse non disponible'
    
 def debug_optimization_sequence(self):
     """Debug pour vérifier la cohérence des séquences"""
     for order in self.filtered('assigned_vehicle_id'):
        _logger.info(f"Commande {order.name}: Véhicule {order.assigned_vehicle_id.name}, Séquence {order.delivery_sequence}")

 def debug_optimization_vs_map_data(self, orders):
        """MÉTHODE DEBUG: Comparer optimisation vs données carte"""
        _logger.info("=== DEBUG: OPTIMISATION VS CARTE ===")
        
        optimized_orders = orders.filtered('assigned_vehicle_id')
        
        for vehicle in optimized_orders.mapped('assigned_vehicle_id'):
            vehicle_orders = optimized_orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)
            vehicle_orders = vehicle_orders.sorted('delivery_sequence')
            
            _logger.info(f"\n--- VÉHICULE {vehicle.name} ---")
            _logger.info("ORDRE D'OPTIMISATION:")
            for order in vehicle_orders:
                _logger.info(f"  Séq {order.delivery_sequence}: {order.name} -> {order.partner_id.name}")
            
            # Préparer les données carte pour ce véhicule
            map_data = self._prepare_map_data_corrected(vehicle_orders)
            if map_data:
                _logger.info("ORDRE DANS DONNÉES CARTE:")
                for waypoint in map_data[0]['waypoints']:
                    _logger.info(f"  Séq {waypoint['sequence']}: {waypoint['name']}")


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
    
 def action_debug_vrp_flow_complete(self):
     """DEBUG COMPLET: Tester tout le flux VRP étape par étape"""
     selected_orders = self.browse(self.env.context.get('active_ids', []))
    
     _logger.info("=== DEBUG COMPLET FLUX VRP ===")
     _logger.info(f"ÉTAPE 1: Commandes sélectionnées: {len(selected_orders)}")
    
     if not selected_orders:
        raise UserError("Sélectionnez au moins une commande pour le debug")
    
    # ÉTAPE 1: Vérifier les coordonnées
     _logger.info("\n--- ÉTAPE 1: VÉRIFICATION COORDONNÉES ---")
     for order in selected_orders:
        lat, lng, coords_found = self._get_order_coordinates_unified(order)
        _logger.info(f"Commande {order.name}: coords_found={coords_found}, lat={lat}, lng={lng}")
    
    # ÉTAPE 2: Vérifier les véhicules
     _logger.info("\n--- ÉTAPE 2: VÉRIFICATION VÉHICULES ---")
     vehicles = self.env['fleet.vehicle'].search([
        ('driver_id', '!=', False),
        ('active', '=', True)
     ])
     _logger.info(f"Véhicules trouvés: {len(vehicles)}")
     for vehicle in vehicles:
        _logger.info(f"  - {vehicle.name} (ID: {vehicle.id}) - Chauffeur: {vehicle.driver_id.name}")
    
    # ÉTAPE 3: Test optimisation
     _logger.info("\n--- ÉTAPE 3: TEST OPTIMISATION ---")
     try:
        optimizer = self.env['vrp.optimizer.enhanced'].create({})
        result = optimizer.solve_vrp_with_road_distances(selected_orders, vehicles)
        
        if result and 'routes' in result:
            _logger.info(f"✅ Optimisation réussie: {len(result['routes'])} véhicules")
            for vehicle_id, order_ids in result['routes'].items():
                vehicle_name = vehicles.filtered(lambda v: v.id == vehicle_id).name
                _logger.info(f"  Véhicule {vehicle_name}: {len(order_ids)} commandes")
        else:
            _logger.error("❌ Optimisation échouée")
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'message': 'Optimisation échouée - Vérifiez les logs',
                'type': 'danger'
            }}
     except Exception as e:
        _logger.error(f"❌ Erreur optimisation: {e}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': f'Erreur optimisation: {e}',
            'type': 'danger'
        }}
    
    # ÉTAPE 4: Test application résultats
     _logger.info("\n--- ÉTAPE 4: TEST APPLICATION RÉSULTATS ---")
     try:
        apply_result = self._apply_optimization_results_enhanced(selected_orders, result, vehicles)
        _logger.info(f"✅ Application résultats: {apply_result}")
     except Exception as e:
        _logger.error(f"❌ Erreur application: {e}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': f'Erreur application: {e}',
            'type': 'danger'
        }}
    
    # ÉTAPE 5: Test préparation données carte
     _logger.info("\n--- ÉTAPE 5: TEST PRÉPARATION DONNÉES CARTE ---")
     try:
        vehicles_data = self._prepare_map_data_corrected(selected_orders)
        _logger.info(f"✅ Données carte préparées: {len(vehicles_data)} véhicules")
        
        for v_data in vehicles_data:
            waypoints = v_data.get('waypoints', [])
            _logger.info(f"  {v_data.get('vehicle_name')}: {len(waypoints)} waypoints")
            for wp in waypoints[:3]:  # Log premiers waypoints
                _logger.info(f"    - {wp.get('name')} (seq: {wp.get('sequence')}, coords: {wp.get('lat')}, {wp.get('lng')})")
                
     except Exception as e:
        _logger.error(f"❌ Erreur préparation carte: {e}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': f'Erreur préparation carte: {e}',
            'type': 'danger'
        }}
    
    # ÉTAPE 6: Test sérialisation JSON
     _logger.info("\n--- ÉTAPE 6: TEST SÉRIALISATION JSON ---")
     try:
        import json
        vehicles_json = json.dumps(vehicles_data, ensure_ascii=False)
        _logger.info(f"✅ JSON généré: {len(vehicles_json)} caractères")
     except Exception as e:
        _logger.error(f"❌ Erreur JSON: {e}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': f'Erreur JSON: {e}',
            'type': 'danger'
        }}
    
    # ÉTAPE 7: Test création map view
     _logger.info("\n--- ÉTAPE 7: TEST CRÉATION MAP VIEW ---")
     try:
        map_view = self.env['vrp.map.view'].create({
            'vehicles_data': vehicles_json
        })
        _logger.info(f"✅ Map view créé: ID {map_view.id}")
        
        # Vérifier les données stockées
        stored_data = json.loads(map_view.vehicles_data)
        _logger.info(f"Données stockées: {len(stored_data)} véhicules")
        
     except Exception as e:
        _logger.error(f"❌ Erreur création map view: {e}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'message': f'Erreur map view: {e}',
            'type': 'danger'
        }}
    
     _logger.info("\n=== DEBUG COMPLET TERMINÉ ===")
    
    # Retourner succès avec ouverture de la carte
     return {
        'type': 'ir.actions.act_window',
        'name': 'DEBUG VRP - Carte générée',
        'res_model': 'vrp.map.view',
        'res_id': map_view.id,
        'view_mode': 'form',
        'target': 'new',
        'context': {'dialog_size': 'large'}
     }
    

 def action_create_test_coordinates(self):
     """Créer des coordonnées de test pour les clients des commandes sélectionnées"""
     selected_orders = self.browse(self.env.context.get('active_ids', []))
    
     if not selected_orders:
        raise UserError("Sélectionnez au moins une commande")
    
     # Coordonnées de test autour de Rabat (Maroc)
     test_coordinates = [
        {'lat': 34.0209, 'lng': -6.8416},  # Rabat centre
        {'lat': 33.9716, 'lng': -6.8498},  # Salé
        {'lat': 34.0531, 'lng': -6.7985},  # Témara  
        {'lat': 33.5731, 'lng': -7.5898},  # Casablanca
        {'lat': 31.6295, 'lng': -7.9811},  # Marrakech
        {'lat': 35.7595, 'lng': -5.8340},  # Tanger
        {'lat': 34.2610, 'lng': -6.5802},  # Kénitra
        {'lat': 34.6867, 'lng': -1.9114},  # Oujda
     ]
    
     partners_updated = 0
     for i, order in enumerate(selected_orders):
        if order.partner_id:
            coord_index = i % len(test_coordinates)
            test_coord = test_coordinates[coord_index]
            
            # Utiliser la nouvelle méthode helper
            success = order.partner_id.set_coordinates(test_coord['lat'], test_coord['lng'])
            
            if success:
                partners_updated += 1
                _logger.info(f"✅ Coordonnées test assignées à {order.partner_id.name}: {test_coord}")
            else:
                _logger.warning(f"❌ Impossible d'assigner coordonnées à {order.partner_id.name}")
    
     return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'message': f'Coordonnées de test créées pour {partners_updated} clients',
            'type': 'success'
        }
     }
    
   

 def action_setup_driver_coordinates(self):
    """NOUVEAU: Configurer les coordonnées GPS des chauffeurs"""
    vehicles = self.env['fleet.vehicle'].search([
        ('driver_id', '!=', False),
        ('active', '=', True)
    ])
    
    if not vehicles:
        raise UserError("Aucun véhicule avec chauffeur trouvé")
    
    # Coordonnées de test dans différentes zones du Maroc
    test_coordinates_morocco = [
        {'lat': 34.0209, 'lng': -6.8416, 'city': 'Rabat Centre'},
        {'lat': 33.9716, 'lng': -6.8498, 'city': 'Salé'},
        {'lat': 34.0531, 'lng': -6.7985, 'city': 'Témara'},
        {'lat': 34.2610, 'lng': -6.5802, 'city': 'Kénitra'},
        {'lat': 33.5731, 'lng': -7.5898, 'city': 'Casablanca'},
        {'lat': 31.6295, 'lng': -7.9811, 'city': 'Marrakech'},
        {'lat': 35.7595, 'lng': -5.8340, 'city': 'Tanger'},
        {'lat': 34.6867, 'lng': -1.9114, 'city': 'Oujda'},
        {'lat': 32.8800, 'lng': -6.9200, 'city': 'Beni Mellal'},
        {'lat': 35.1681, 'lng': -5.2683, 'city': 'Al Hoceima'}
    ]
    
    drivers_updated = 0
    for i, vehicle in enumerate(vehicles):
        if vehicle.driver_id:
            # Vérifier si le chauffeur a déjà des coordonnées
            existing_lat, existing_lng, has_coords = self._get_driver_coordinates_for_vehicle(vehicle)
            
            if not has_coords:
                # Assigner des coordonnées de test
                coord_index = i % len(test_coordinates_morocco)
                test_coord = test_coordinates_morocco[coord_index]
                
                # Utiliser la méthode du partenaire pour définir les coordonnées
                success = vehicle.driver_id.set_coordinates(
                    test_coord['lat'], 
                    test_coord['lng']
                )
                
                if success:
                    drivers_updated += 1
                    _logger.info(f"✅ Coordonnées assignées à {vehicle.driver_id.name}: {test_coord['city']}")
                else:
                    _logger.warning(f"❌ Échec assignation pour {vehicle.driver_id.name}")
            else:
                _logger.info(f"⚪ {vehicle.driver_id.name} a déjà des coordonnées")
    
    message = f"Configuration terminée:\n"
    message += f"• {drivers_updated} chauffeurs mis à jour\n"
    message += f"• {len(vehicles) - drivers_updated} chauffeurs avaient déjà des coordonnées\n"
    message += f"• Total véhicules traités: {len(vehicles)}"
    
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Configuration Chauffeurs Terminée',
            'message': message,
            'type': 'success' if drivers_updated > 0 else 'info',
            'sticky': True,
        }
    }

 def action_validate_driver_system(self):
    """NOUVEAU: Valider que le système dépôts chauffeurs est prêt"""
    vehicles = self.env['fleet.vehicle'].search([
        ('driver_id', '!=', False),
        ('active', '=', True)
    ])
    
    if not vehicles:
        raise UserError("Aucun véhicule avec chauffeur configuré")
    
    validation_results = {
        'total_vehicles': len(vehicles),
        'valid_drivers': 0,
        'invalid_drivers': [],
        'ready_for_optimization': False
    }
    
    for vehicle in vehicles:
        lat, lng, coords_found = self._get_driver_coordinates_for_vehicle(vehicle)
        
        if coords_found:
            validation_results['valid_drivers'] += 1
        else:
            validation_results['invalid_drivers'].append({
                'vehicle': vehicle.name,
                'driver': vehicle.driver_id.name,
                'driver_id': vehicle.driver_id.id
            })
    
    validation_results['ready_for_optimization'] = (
        validation_results['valid_drivers'] > 0 and 
        len(validation_results['invalid_drivers']) == 0
    )
    
    # Créer message détaillé
    message_lines = [
        "=== VALIDATION SYSTÈME DÉPÔTS CHAUFFEURS ===\n",
        f"Véhicules total: {validation_results['total_vehicles']}",
        f"Chauffeurs géolocalisés: {validation_results['valid_drivers']}",
        f"Chauffeurs sans coordonnées: {len(validation_results['invalid_drivers'])}"
    ]
    
    if validation_results['invalid_drivers']:
        message_lines.append("\n❌ CHAUFFEURS À GÉOLOCALISER:")
        for invalid in validation_results['invalid_drivers']:
            message_lines.append(f"• {invalid['vehicle']} - {invalid['driver']}")
    
    if validation_results['ready_for_optimization']:
        message_lines.append(f"\n✅ SYSTÈME PRÊT pour optimisation VRP!")
    else:
        message_lines.append(f"\n⚠️  Configurez d'abord tous les chauffeurs")
    
    message = "\n".join(message_lines)
    
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Validation Système Chauffeurs',
            'message': message,
            'type': 'success' if validation_results['ready_for_optimization'] else 'warning',
            'sticky': True,
        }
    }