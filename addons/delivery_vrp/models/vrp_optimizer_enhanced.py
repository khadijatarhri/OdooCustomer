# models/vrp_optimizer_enhanced.py
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
    _description = 'Enhanced VRP Optimization Engine with Real Road Distances'

    # Configuration des services de routage
    ROUTING_SERVICES = {
        'osrm': {
            'base_url': 'http://router.project-osrm.org/table/v1/driving/',
            'rate_limit': 0.1,  # secondes entre requêtes
            'max_locations': 25,  # limite par requête
            'free': True
        },
        'graphhopper': {
            'base_url': 'https://graphhopper.com/api/1/matrix',
            'rate_limit': 1.0,  # 1 seconde entre requêtes pour version gratuite
            'max_locations': 25,
            'free': True,
            'requires_key': False  # Peut fonctionner sans clé avec limitations
        },
        'openrouteservice': {
            'base_url': 'https://api.openrouteservice.org/v2/matrix/driving-car',
            'rate_limit': 0.5,
            'max_locations': 25,
            'free': True,
            'requires_key': True,  # Clé gratuite nécessaire
            'daily_limit': 2000
        }
    }

   

    def _get_company_settings(self):  
     """Récupérer les paramètres de routage avec valeurs fixes"""  
     return {  
        'routing_service': 'osrm',  # Service gratuit et fiable  
        'openrouteservice_key': '',  
        'graphhopper_key': '',  
        'depot_latitude': 34.0209,  # RABAT par défaut  
        'depot_longitude': -6.8416,  
     }
    def _calculate_euclidean_distance(self, lat1, lon1, lat2, lon2):
        """Distance euclidienne de fallback"""
        R = 6371  # Rayon de la Terre en km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c * 1000  # Retour en mètres

    def _get_osrm_matrix(self, locations):
        """Calculer la matrice de distance via OSRM (gratuit, illimité)"""
        try:
            # Préparer les coordonnées pour OSRM
            coords_str = ";".join([f"{loc['lng']},{loc['lat']}" for loc in locations])
            url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
            
            params = {
                'annotations': 'distance,duration'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data['code'] != 'Ok':
                raise Exception(f"OSRM Error: {data.get('message', 'Unknown error')}")
            
            # Convertir en matrice de distances en mètres
            distance_matrix = data['distances']
            duration_matrix = data['durations']
            
            _logger.info(f"OSRM matrix calculated successfully for {len(locations)} locations")
            return distance_matrix, duration_matrix
            
        except Exception as e:
            _logger.error(f"OSRM request failed: {str(e)}")
            return None, None

    def _get_graphhopper_matrix(self, locations, api_key=None):
        """Calculer la matrice via GraphHopper"""
        try:
            url = "https://graphhopper.com/api/1/matrix"
            
            # Préparer les points
            points = [[loc['lat'], loc['lng']] for loc in locations]
            
            payload = {
                "points": points,
                "out_arrays": ["distances", "times"],
                "vehicle": "car"
            }
            
            params = {}
            if api_key:
                params['key'] = api_key
            
            response = requests.post(url, json=payload, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'distances' not in data:
                raise Exception("Invalid GraphHopper response")
            
            distance_matrix = data['distances']
            duration_matrix = data.get('times', [])
            
            _logger.info(f"GraphHopper matrix calculated successfully for {len(locations)} locations")
            return distance_matrix, duration_matrix
            
        except Exception as e:
            _logger.error(f"GraphHopper request failed: {str(e)}")
            return None, None

    def _get_openrouteservice_matrix(self, locations, api_key):
        """Calculer la matrice via OpenRouteService"""
        try:
            url = "https://api.openrouteservice.org/v2/matrix/driving-car"
            
            # Préparer les coordonnées
            coordinates = [[loc['lng'], loc['lat']] for loc in locations]
            
            payload = {
                "locations": coordinates,
                "metrics": ["distance", "duration"],
                "units": "m"
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': api_key
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'distances' not in data:
                raise Exception("Invalid OpenRouteService response")
            
            distance_matrix = data['distances']
            duration_matrix = data.get('durations', [])
            
            _logger.info(f"OpenRouteService matrix calculated successfully for {len(locations)} locations")
            return distance_matrix, duration_matrix
            
        except Exception as e:
            _logger.error(f"OpenRouteService request failed: {str(e)}")
            return None, None

    def _batch_matrix_calculation(self, locations, service_config, api_key=None):
        """Calculer la matrice par batch pour gérer les limitations"""
        max_locations = service_config['max_locations']
        n_locations = len(locations)
        
        if n_locations <= max_locations:
            # Une seule requête suffit
            if service_config.get('name') == 'osrm':
                return self._get_osrm_matrix(locations)
            elif service_config.get('name') == 'graphhopper':
                return self._get_graphhopper_matrix(locations, api_key)
            elif service_config.get('name') == 'openrouteservice':
                return self._get_openrouteservice_matrix(locations, api_key)
        
        # Gestion des batch pour grandes matrices
        _logger.info(f"Large matrix ({n_locations} locations), using batch processing")
        
        # Initialiser les matrices complètes
        full_distance_matrix = [[0] * n_locations for _ in range(n_locations)]
        full_duration_matrix = [[0] * n_locations for _ in range(n_locations)]
        
        # Calculer par chunks
        batch_size = max_locations
        for i in range(0, n_locations, batch_size):
            end_i = min(i + batch_size, n_locations)
            batch_locations = locations[i:end_i]
            
            # Calculer la sous-matrice
            if service_config.get('name') == 'osrm':
                batch_distances, batch_durations = self._get_osrm_matrix(batch_locations)
            elif service_config.get('name') == 'graphhopper':
                batch_distances, batch_durations = self._get_graphhopper_matrix(batch_locations, api_key)
            elif service_config.get('name') == 'openrouteservice':
                batch_distances, batch_durations = self._get_openrouteservice_matrix(batch_locations, api_key)
            
            if batch_distances is None:
                return None, None
            
            # Insérer dans la matrice complète
            for bi, row in enumerate(batch_distances):
                for bj, distance in enumerate(row):
                    full_distance_matrix[i + bi][i + bj] = distance
                    if batch_durations:
                        full_duration_matrix[i + bi][i + bj] = batch_durations[bi][bj]
            
            # Respecter le rate limiting
            time.sleep(service_config['rate_limit'])
        
        return full_distance_matrix, full_duration_matrix

    def create_road_distance_matrix(self, locations):
        """Créer la matrice de distance routière"""
        settings = self._get_company_settings()
        service_name = settings['routing_service']
        
        if service_name not in self.ROUTING_SERVICES:
            _logger.warning(f"Service {service_name} not supported, falling back to euclidean")
            return self._create_euclidean_matrix(locations)
        
        service_config = self.ROUTING_SERVICES[service_name].copy()
        service_config['name'] = service_name
        
        _logger.info(f"Calculating road distance matrix using {service_name} for {len(locations)} locations")
        
        # Préparer les clés API si nécessaire
        api_key = None
        if service_name == 'openrouteservice':
            api_key = settings['openrouteservice_key']
            if not api_key:
                _logger.error("OpenRouteService requires API key")
                return self._create_euclidean_matrix(locations)
        elif service_name == 'graphhopper':
            api_key = settings.get('graphhopper_key')
        
        try:
            # Calculer la matrice routière
            distance_matrix, duration_matrix = self._batch_matrix_calculation(
                locations, service_config, api_key
            )
            
            if distance_matrix is None:
                _logger.warning("Road distance calculation failed, using euclidean fallback")
                return self._create_euclidean_matrix(locations)
            
            # Convertir en entiers (mètres) pour OR-Tools
            int_matrix = []
            for row in distance_matrix:
                int_row = [int(distance) if distance is not None else 999999 for distance in row]
                int_matrix.append(int_row)
            
            _logger.info(f"Road distance matrix created successfully using {service_name}")
            return int_matrix
            
        except Exception as e:
            _logger.error(f"Error creating road distance matrix: {str(e)}")
            return self._create_euclidean_matrix(locations)

    def _create_euclidean_matrix(self, locations):
        """Fallback vers la distance euclidienne"""
        _logger.info("Using euclidean distance as fallback")
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

    # Dans models/vrp_optimizer_enhanced.py
    # Remplacez la méthode solve_vrp_with_road_distances par cette version corrigée :

    def solve_vrp_with_road_distances(self, sale_orders, vehicles):
     """Résolution du VRP avec distances routières réelles"""
     settings = self._get_company_settings()
    
    # Préparer les locations avec le dépôt
     depot_location = {
        'lat': settings['depot_latitude'], 
        'lng': settings['depot_longitude'],
        'type': 'depot'
     }
    
     locations = [depot_location]
     order_mapping = {}  # Mapping location_index -> order_id
     valid_orders = []
    
    # NOUVELLE LOGIQUE : Récupérer les coordonnées de manière robuste
     for i, order in enumerate(sale_orders):
        lat, lng = 0.0, 0.0
        coords_found = False
        
        # 1. Essayer les coordonnées JSON du partenaire
        partner = order.partner_id
        if partner.coordinates and isinstance(partner.coordinates, dict):
            try:
                lat = float(partner.coordinates.get('latitude', 0.0))
                lng = float(partner.coordinates.get('longitude', 0.0))
                
                if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 and lng != 0.0):
                    coords_found = True
            except (ValueError, TypeError):
                pass
        
        # 2. Si pas trouvé, essayer via VRP order
        if not coords_found:
            vrp_order = self.env['vrp.order'].search([
                ('sale_order_id', '=', order.id)
            ], limit=1)
            
            if vrp_order:
                # Forcer le recalcul
                vrp_order._compute_coordinates()
                if vrp_order.partner_latitude and vrp_order.partner_longitude:
                    if (vrp_order.partner_latitude != 0.0 and vrp_order.partner_longitude != 0.0):
                        lat = vrp_order.partner_latitude
                        lng = vrp_order.partner_longitude
                        coords_found = True
        
        # 3. Si encore pas trouvé, essayer les champs directs
        if not coords_found and hasattr(order, 'partner_latitude') and hasattr(order, 'partner_longitude'):
            if order.partner_latitude and order.partner_longitude:
                if (order.partner_latitude != 0.0 and order.partner_longitude != 0.0):
                    lat = order.partner_latitude
                    lng = order.partner_longitude
                    coords_found = True
        
        # Ajouter seulement si coordonnées valides trouvées
        if coords_found:
            locations.append({
                'lat': lat,
                'lng': lng,
                'type': 'customer',
                'order_id': order.id
            })
            order_mapping[len(valid_orders) + 1] = order.id  # +1 car dépôt = 0
            valid_orders.append(order)
        else:
            _logger.warning(f"Commande {order.name} ignorée - pas de coordonnées valides")

     if not valid_orders:
        raise UserError("Aucune commande avec coordonnées GPS valides")

     _logger.info(f"Starting VRP optimization for {len(valid_orders)} orders with valid coordinates")

    # Calculer la matrice de distance routière
     distance_matrix = self.create_road_distance_matrix(locations)
    
    # Configuration du problème VRP
     data = {
        'distance_matrix': distance_matrix,
        'num_vehicles': len(vehicles),
        'depot': 0,
        'vehicle_capacities': [100] * len(vehicles),  # Capacité par défaut
        'demands': [0] + [1] * len(valid_orders)  # Demande par client
     }

    # Créer le manager et le modèle
     manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['depot']
     )
     routing = pywrapcp.RoutingModel(manager)

    # Callback de distance
     def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

     transit_callback_index = routing.RegisterTransitCallback(distance_callback)
     routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Ajouter contrainte de distance
     dimension_name = 'Distance'
     routing.AddDimension(
        transit_callback_index,
        0,  # slack
        200000,  # distance maximum par véhicule (100km)
        True,  # start cumul to zero
        dimension_name
     )
     distance_dimension = routing.GetDimensionOrDie(dimension_name)
     distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Contrainte de capacité
     def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

     demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
     routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # slack_max
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity'
     )

    # Paramètres de recherche avancés
     search_parameters = pywrapcp.DefaultRoutingSearchParameters()
     search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
     )
     search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
     )
     search_parameters.time_limit.FromSeconds(120)  
     search_parameters.log_search = True

     _logger.info("Starting OR-Tools optimization...")
    
    # Résolution
     solution = routing.SolveWithParameters(search_parameters)

     if solution:
        _logger.info(f"Optimization completed successfully. Total distance: {solution.ObjectiveValue()}m")
        return self._extract_enhanced_solution(
            manager, routing, solution, valid_orders, vehicles, order_mapping
        )
     else:
        _logger.error("No solution found for VRP problem")
        return False

    def _extract_enhanced_solution(self, manager, routing, solution, sale_orders, vehicles, order_mapping):
        """Extraction de la solution avec métriques détaillées"""
        routes = {}
        route_stats = {}
        
        for vehicle_id in range(len(vehicles)):
            vehicle = vehicles[vehicle_id]
            index = routing.Start(vehicle_id)
            route_orders = []
            route_distance = 0
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node > 0:  # Ignorer le dépôt
                    order_id = order_mapping.get(node)
                    if order_id:
                        route_orders.append(order_id)
                
                # Calculer la distance
                if not routing.IsEnd(index):
                    next_index = solution.Value(routing.NextVar(index))
                    route_distance += routing.GetArcCostForVehicle(index, next_index, vehicle_id)
                
                index = solution.Value(routing.NextVar(index))
            
            if route_orders:
                routes[vehicle.id] = route_orders
                route_stats[vehicle.id] = {
                    'distance': route_distance,
                    'stops': len(route_orders),
                    'vehicle_name': vehicle.name,
                    'driver': vehicle.driver_id.name
                }
        
        # Log des statistiques
        total_distance = sum(stats['distance'] for stats in route_stats.values())
        total_stops = sum(stats['stops'] for stats in route_stats.values())
        
        _logger.info(f"Solution summary:")
        _logger.info(f"  - Total distance: {total_distance/1000:.2f} km")
        _logger.info(f"  - Total stops: {total_stops}")
        _logger.info(f"  - Vehicles used: {len(routes)}")
        
        for vehicle_id, stats in route_stats.items():
            _logger.info(f"  - {stats['vehicle_name']}: {stats['distance']/1000:.2f}km, {stats['stops']} stops")

        return {
            'routes': routes,
            'stats': route_stats,
            'total_distance': total_distance,
            'total_stops': total_stops
        }