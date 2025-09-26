# models/vrp_optimizer_enhanced.py - MODIFICATION POUR DÉPÔT PAR CHAUFFEUR
from odoo import models, fields, api
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from odoo.exceptions import UserError, ValidationError
import requests
import json
import time
import math
import logging

_logger = logging.getLogger(__name__)

class VRPOptimizerEnhanced(models.TransientModel):
    _name = 'vrp.optimizer.enhanced'
    _description = 'Enhanced VRP Optimization Engine with Driver-Based Depots'

    # Configuration des services de routage (inchangé)
    ROUTING_SERVICES = {
        'osrm': {
            'base_url': 'http://router.project-osrm.org/table/v1/driving/',
            'rate_limit': 0.1,
            'max_locations': 25,
            'free': True
        },
        'graphhopper': {
            'base_url': 'https://graphhopper.com/api/1/matrix',
            'rate_limit': 1.0,
            'max_locations': 25,
            'free': True,
            'requires_key': False
        },
        'openrouteservice': {
            'base_url': 'https://api.openrouteservice.org/v2/matrix/driving-car',
            'rate_limit': 0.5,
            'max_locations': 25,
            'free': True,
            'requires_key': True,
            'daily_limit': 2000
        }
    }

    def _get_company_settings(self):
        """MODIFIÉ: Récupérer les paramètres de routage (sans dépôt fixe)"""
        return {
            'routing_service': getattr(self.env.company, 'vrp_routing_service', 'osrm'),
            'openrouteservice_key': getattr(self.env.company, 'vrp_openrouteservice_key', ''),
            'graphhopper_key': getattr(self.env.company, 'vrp_graphhopper_key', ''),
            # Plus de dépôt fixe - sera calculé par véhicule/chauffeur
        }

    def _get_driver_coordinates(self, vehicle):
        """NOUVEAU: Récupérer les coordonnées d'un chauffeur"""
        if not vehicle.driver_id:
            _logger.error(f"Véhicule {vehicle.name} sans chauffeur assigné")
            return None, None, False
        
        driver = vehicle.driver_id
        
        # 1. Essayer les coordonnées JSON du chauffeur
        if driver.coordinates and isinstance(driver.coordinates, dict):
            try:
                lat = float(driver.coordinates.get('latitude', 0.0))
                lng = float(driver.coordinates.get('longitude', 0.0))
                
                if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 and lng != 0.0):
                    _logger.info(f"✓ Coordonnées chauffeur {driver.name}: {lat}, {lng} (JSON)")
                    return lat, lng, True
            except (ValueError, TypeError):
                pass
        
        # 2. Essayer les champs directs si disponibles
        if hasattr(driver, 'partner_latitude') and hasattr(driver, 'partner_longitude'):
            if driver.partner_latitude and driver.partner_longitude:
                if (driver.partner_latitude != 0.0 and driver.partner_longitude != 0.0):
                    _logger.info(f"✓ Coordonnées chauffeur {driver.name}: {driver.partner_latitude}, {driver.partner_longitude} (champs)")
                    return driver.partner_latitude, driver.partner_longitude, True
        
        _logger.warning(f"✗ Aucune coordonnée trouvée pour le chauffeur {driver.name}")
        return None, None, False

    def _calculate_euclidean_distance(self, lat1, lon1, lat2, lon2):
        """Distance euclidienne de fallback (inchangé)"""
        R = 6371  # Rayon de la Terre en km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c * 1000  # Retour en mètres

    def _get_osrm_matrix(self, locations):
        """Calculer la matrice de distance via OSRM (inchangé)"""
        try:
            coords_str = ";".join([f"{loc['lng']},{loc['lat']}" for loc in locations])
            url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
            
            params = {'annotations': 'distance,duration'}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data['code'] != 'Ok':
                raise Exception(f"OSRM Error: {data.get('message', 'Unknown error')}")
            
            distance_matrix = data['distances']
            duration_matrix = data['durations']
            
            _logger.info(f"OSRM matrix calculée avec succès pour {len(locations)} locations")
            return distance_matrix, duration_matrix
            
        except Exception as e:
            _logger.error(f"Requête OSRM échouée: {str(e)}")
            return None, None

    def create_road_distance_matrix(self, locations):
        """Créer la matrice de distance routière (inchangé)"""
        settings = self._get_company_settings()
        service_name = settings['routing_service']
        
        _logger.info(f"Calcul matrice distance routière avec {service_name} pour {len(locations)} locations")
        
        if service_name not in self.ROUTING_SERVICES:
            _logger.warning(f"Service {service_name} non supporté, fallback euclidien")
            return self._create_euclidean_matrix(locations)
        
        try:
            if service_name == 'osrm':
                distance_matrix, duration_matrix = self._get_osrm_matrix(locations)
            else:
                _logger.info(f"Service {service_name} non implémenté, utilisation OSRM")
                distance_matrix, duration_matrix = self._get_osrm_matrix(locations)
            
            if distance_matrix is None:
                _logger.warning("Calcul distance routière échoué, utilisation fallback euclidien")
                return self._create_euclidean_matrix(locations)
            
            # Convertir en entiers (mètres) pour OR-Tools
            int_matrix = []
            for row in distance_matrix:
                int_row = [int(distance) if distance is not None else 999999 for distance in row]
                int_matrix.append(int_row)
            
            _logger.info(f"Matrice distance routière créée avec succès")
            return int_matrix
            
        except Exception as e:
            _logger.error(f"Erreur création matrice distance routière: {str(e)}")
            return self._create_euclidean_matrix(locations)

    def _create_euclidean_matrix(self, locations):
        """Fallback vers la distance euclidienne (inchangé)"""
        _logger.info("Utilisation distance euclidienne comme fallback")
        matrix = []
        for i, from_loc in enumerate(locations):
            row = []
            for j, to_loc in enumerate(locations):
                if i == j:
                    row.append(0)
                else:
                    distance = self._calculate_euclidean_distance(
                        from_loc['lat'], from_loc['lng'],
                        to_loc['lat'], to_loc['lng']
                    )
                    row.append(int(distance))
            matrix.append(row)
        return matrix

    def solve_vrp_with_driver_based_depots(self, sale_orders, vehicles):
        """MODIFIÉ: Résolution VRP avec dépôts basés sur les chauffeurs"""
        _logger.info(f"=== VRP AVEC DÉPÔTS PAR CHAUFFEUR ===")
        _logger.info(f"Commandes à traiter: {len(sale_orders)}")
        _logger.info(f"Véhicules disponibles: {len(vehicles)}")
        
        # Vérifier que tous les véhicules ont des chauffeurs avec coordonnées
        valid_vehicles = []
        for vehicle in vehicles:
            lat, lng, coords_found = self._get_driver_coordinates(vehicle)
            if coords_found:
                valid_vehicles.append({
                    'vehicle': vehicle,
                    'driver_lat': lat,
                    'driver_lng': lng
                })
                _logger.info(f"✓ Véhicule {vehicle.name} - Chauffeur: {vehicle.driver_id.name} ({lat}, {lng})")
            else:
                _logger.warning(f"✗ Véhicule {vehicle.name} ignoré - pas de coordonnées chauffeur")
        
        if not valid_vehicles:
            raise UserError("Aucun véhicule avec chauffeur géolocalisé disponible")
        
        _logger.info(f"Véhicules valides: {len(valid_vehicles)}")
        
        # Préparer les commandes valides
        valid_orders = []
        for order in sale_orders:
            lat, lng, coords_found = order._get_order_coordinates_unified(order)
            
            if coords_found:
                valid_orders.append({
                    'order': order,
                    'lat': lat,
                    'lng': lng
                })
                _logger.info(f"✓ Commande {order.name}: {lat}, {lng}")
            else:
                _logger.warning(f"✗ Commande {order.name} ignorée - pas de coordonnées")
        
        if not valid_orders:
            raise UserError("Aucune commande avec coordonnées GPS valides")
        
        # NOUVEAU ALGORITHME: Assignation par proximité géographique
        return self._assign_orders_to_nearest_drivers(valid_orders, valid_vehicles)

    def _assign_orders_to_nearest_drivers(self, valid_orders, valid_vehicles):
        """NOUVEAU: Assigner les commandes aux chauffeurs les plus proches"""
        _logger.info("=== ASSIGNATION PAR PROXIMITÉ GÉOGRAPHIQUE ===")
        
        routes = {}
        route_stats = {}
        
        # Pour chaque commande, trouver le chauffeur le plus proche
        for order_data in valid_orders:
            order = order_data['order']
            order_lat = order_data['lat']
            order_lng = order_data['lng']
            
            min_distance = float('inf')
            closest_vehicle = None
            
            # Calculer la distance vers chaque chauffeur
            for vehicle_data in valid_vehicles:
                vehicle = vehicle_data['vehicle']
                driver_lat = vehicle_data['driver_lat']
                driver_lng = vehicle_data['driver_lng']
                
                # Distance euclidienne (rapide pour la sélection initiale)
                distance = self._calculate_euclidean_distance(
                    order_lat, order_lng, 
                    driver_lat, driver_lng
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_vehicle = vehicle
            
            # Assigner la commande au véhicule le plus proche
            if closest_vehicle:
                vehicle_id = closest_vehicle.id
                if vehicle_id not in routes:
                    routes[vehicle_id] = []
                    route_stats[vehicle_id] = {
                        'distance': 0,
                        'stops': 0,
                        'vehicle_name': closest_vehicle.name,
                        'driver': closest_vehicle.driver_id.name,
                        'driver_coords': (
                            next(v['driver_lat'] for v in valid_vehicles if v['vehicle'] == closest_vehicle),
                            next(v['driver_lng'] for v in valid_vehicles if v['vehicle'] == closest_vehicle)
                        )
                    }
                
                routes[vehicle_id].append(order.id)
                route_stats[vehicle_id]['stops'] += 1
                route_stats[vehicle_id]['distance'] += min_distance
                
                _logger.info(f"✅ {order.name} → {closest_vehicle.name} (distance: {min_distance/1000:.2f}km)")
        
        # Optimiser l'ordre des arrêts pour chaque véhicule
        optimized_routes = self._optimize_stops_order_per_vehicle(routes, route_stats, valid_orders)
        
        total_distance = sum(stats['distance'] for stats in route_stats.values())
        total_stops = sum(len(order_ids) for order_ids in routes.values())
        
        _logger.info(f"=== RÉSULTAT ASSIGNATION ===")
        _logger.info(f"Véhicules utilisés: {len(routes)}")
        _logger.info(f"Commandes assignées: {total_stops}")
        _logger.info(f"Distance totale approximative: {total_distance/1000:.2f}km")
        
        return {
            'routes': optimized_routes,
            'stats': route_stats,
            'total_distance': total_distance,
            'total_stops': total_stops,
            'algorithm': 'driver_proximity_based'
        }

    def _optimize_stops_order_per_vehicle(self, routes, route_stats, valid_orders):
        """NOUVEAU: Optimiser l'ordre des arrêts pour chaque véhicule"""
        optimized_routes = {}
        orders_dict = {order_data['order'].id: order_data for order_data in valid_orders}
        
        for vehicle_id, order_ids in routes.items():
            if len(order_ids) <= 2:
                # Pas besoin d'optimiser pour 1-2 arrêts
                optimized_routes[vehicle_id] = order_ids
                continue
            
            # Récupérer les coordonnées du chauffeur
            driver_coords = route_stats[vehicle_id]['driver_coords']
            
            # Créer la liste des points (chauffeur + clients)
            points = [{'lat': driver_coords[0], 'lng': driver_coords[1], 'type': 'driver'}]
            
            for order_id in order_ids:
                order_data = orders_dict[order_id]
                points.append({
                    'lat': order_data['lat'],
                    'lng': order_data['lng'],
                    'order_id': order_id,
                    'type': 'customer'
                })
            
            # Algorithme du plus proche voisin pour optimiser l'ordre
            optimized_order = self._nearest_neighbor_tsp(points, driver_coords)
            optimized_routes[vehicle_id] = optimized_order
            
            _logger.info(f"Ordre optimisé pour {route_stats[vehicle_id]['vehicle_name']}: {len(optimized_order)} arrêts")
        
        return optimized_routes

    def _nearest_neighbor_tsp(self, points, start_coords):
        """Algorithme du plus proche voisin pour optimiser l'ordre des arrêts"""
        if len(points) <= 2:
            return [p['order_id'] for p in points if p['type'] == 'customer']
        
        # Commencer par le point de départ (chauffeur)
        current_pos = start_coords
        unvisited = [p for p in points if p['type'] == 'customer']
        ordered_stops = []
        
        while unvisited:
            # Trouver le client le plus proche
            min_distance = float('inf')
            closest_customer = None
            
            for customer in unvisited:
                distance = self._calculate_euclidean_distance(
                    current_pos[0], current_pos[1],
                    customer['lat'], customer['lng']
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_customer = customer
            
            # Ajouter le client le plus proche
            if closest_customer:
                ordered_stops.append(closest_customer['order_id'])
                current_pos = (closest_customer['lat'], closest_customer['lng'])
                unvisited.remove(closest_customer)
        
        return ordered_stops

    # Méthode de compatibilité - rediriger vers la nouvelle méthode
    def solve_vrp_with_road_distances(self, sale_orders, vehicles):
        """Redirection vers la nouvelle méthode basée sur les chauffeurs"""
        return self.solve_vrp_with_driver_based_depots(sale_orders, vehicles)