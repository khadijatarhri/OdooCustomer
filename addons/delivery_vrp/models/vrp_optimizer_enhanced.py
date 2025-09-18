# models/vrp_optimizer_enhanced_corrected.py - VERSION CORRIGÉE
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
        """Récupérer les paramètres de routage centralisés"""
        # Priorité 1: Paramètres de la société si disponibles
        if hasattr(self.env.company, 'vrp_depot_latitude') and self.env.company.vrp_depot_latitude:
            return {
                'routing_service': getattr(self.env.company, 'vrp_routing_service', 'osrm'),
                'openrouteservice_key': getattr(self.env.company, 'vrp_openrouteservice_key', ''),
                'graphhopper_key': getattr(self.env.company, 'vrp_graphhopper_key', ''),
                'depot_latitude': self.env.company.vrp_depot_latitude,
                'depot_longitude': self.env.company.vrp_depot_longitude,
            }
        
        # Priorité 2: Valeurs par défaut (Rabat)
        return {
            'routing_service': 'osrm',
            'openrouteservice_key': '',
            'graphhopper_key': '',
            'depot_latitude': 34.0209,  # Rabat
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
        """Calculer la matrice de distance via OSRM"""
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
        """Créer la matrice de distance routière"""
        settings = self._get_company_settings()
        service_name = settings['routing_service']
        
        _logger.info(f"Calcul matrice distance routière avec {service_name} pour {len(locations)} locations")
        
        if service_name not in self.ROUTING_SERVICES:
            _logger.warning(f"Service {service_name} non supporté, fallback euclidien")
            return self._create_euclidean_matrix(locations)
        
        try:
            # Utiliser OSRM par défaut (gratuit et fiable)
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
        """Fallback vers la distance euclidienne"""
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

    def solve_vrp_with_road_distances(self, sale_orders, vehicles):
        """Résolution du VRP avec distances routières réelles - VERSION CORRIGÉE"""
        settings = self._get_company_settings()
        
        # Préparer les locations avec le dépôt en utilisant les coordonnées centralisées
        depot_location = {
            'lat': settings['depot_latitude'],
            'lng': settings['depot_longitude'],
            'type': 'depot',
            'name': 'Dépôt - Rabat'
        }
        
        locations = [depot_location]
        valid_orders = []
        
        _logger.info(f"=== DÉBUT OPTIMISATION VRP ===")
        _logger.info(f"Dépôt: {depot_location['lat']}, {depot_location['lng']}")
        _logger.info(f"Commandes à traiter: {len(sale_orders)}")
        
        # Utiliser la méthode unifiée des coordonnées depuis sale.order
        for i, order in enumerate(sale_orders):
            # Appeler la méthode unifiée du modèle sale.order
            lat, lng, coords_found = order._get_order_coordinates_unified(order)
            
            if coords_found:
                location = {
                    'lat': lat,
                    'lng': lng,
                    'type': 'customer',
                    'order_id': order.id,
                    'name': order.partner_id.name
                }
                locations.append(location)
                valid_orders.append(order)
                _logger.info(f"✓ Commande {order.name}: {lat}, {lng}")
            else:
                _logger.warning(f"✗ Commande {order.name} ignorée - pas de coordonnées")
        
        if not valid_orders:
            raise UserError("Aucune commande avec coordonnées GPS valides")
        
        _logger.info(f"Commandes valides: {len(valid_orders)}")
        _logger.info(f"Total locations: {len(locations)}")
        
        # Calculer la matrice de distance routière
        distance_matrix = self.create_road_distance_matrix(locations)
        
        # Configuration du problème VRP
        data = {
            'distance_matrix': distance_matrix,
            'num_vehicles': len(vehicles),
            'depot': 0,
            'vehicle_capacities': [100] * len(vehicles),
            'demands': [0] + [1] * len(valid_orders)
        }
        
        # Créer le manager et le modèle OR-Tools
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
            200000,  # distance maximum par véhicule (200km)
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
            data['vehicle_capacities'],
            True,  # start cumul to zero
            'Capacity'
        )
        
        # Paramètres de recherche
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(120)
        search_parameters.log_search = True
        
        _logger.info("Démarrage optimisation OR-Tools...")
        
        # Résolution
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            _logger.info(f"✓ Optimisation réussie. Distance totale: {solution.ObjectiveValue()}m")
            return self._extract_corrected_solution(
                manager, routing, solution, valid_orders, vehicles
            )
        else:
            _logger.error("✗ Aucune solution trouvée pour le problème VRP")
            return False

    def _extract_corrected_solution(self, manager, routing, solution, sale_orders, vehicles):
        """Extraction corrigée de la solution avec mapping précis"""
        routes = {}
        route_stats = {}
        
        _logger.info("=== EXTRACTION SOLUTION ===")
        _logger.info(f"Véhicules disponibles: {len(vehicles)}")
        _logger.info(f"Commandes valides: {len(sale_orders)}")
        
        for vehicle_idx in range(len(vehicles)):
            vehicle = vehicles[vehicle_idx]
            index = routing.Start(vehicle_idx)
            route_order_ids = []
            route_distance = 0
            
            _logger.info(f"Traitement véhicule {vehicle_idx}: {vehicle.name}")
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                
                if node > 0:  # Ignorer le dépôt (node 0)
                    # Le node correspond à l'index dans la liste des locations
                    # node 1 = première commande, node 2 = deuxième commande, etc.
                    order_idx = node - 1  # -1 car node 0 = dépôt
                    if 0 <= order_idx < len(sale_orders):
                        order = sale_orders[order_idx]
                        route_order_ids.append(order.id)
                        _logger.info(f"  - Node {node} -> Commande {order.name} (ID: {order.id})")
                
                # Calculer la distance
                if not routing.IsEnd(index):
                    next_index = solution.Value(routing.NextVar(index))
                    route_distance += routing.GetArcCostForVehicle(index, next_index, vehicle_idx)
                
                index = solution.Value(routing.NextVar(index))
            
            if route_order_ids:
                routes[vehicle.id] = route_order_ids
                route_stats[vehicle.id] = {
                    'distance': route_distance,
                    'stops': len(route_order_ids),
                    'vehicle_name': vehicle.name,
                    'driver': vehicle.driver_id.name if vehicle.driver_id else 'N/A'
                }
                _logger.info(f"✓ {vehicle.name}: {len(route_order_ids)} arrêts, {route_distance/1000:.2f}km")
        
        # Statistiques globales
        total_distance = sum(stats['distance'] for stats in route_stats.values())
        total_stops = sum(stats['stops'] for stats in route_stats.values())
        
        _logger.info(f"=== RÉSUMÉ SOLUTION ===")
        _logger.info(f"Distance totale: {total_distance/1000:.2f} km")
        _logger.info(f"Arrêts totaux: {total_stops}")
        _logger.info(f"Véhicules utilisés: {len(routes)}")
        
        return {
            'routes': routes,
            'stats': route_stats,
            'total_distance': total_distance,
            'total_stops': total_stops
        }