# models/vrp_optimizer.py
from odoo import models, fields, api
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math

class VRPOptimizer(models.TransientModel):
    _name = 'vrp.optimizer'
    _description = 'VRP Optimization Engine'

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calcul de la distance euclidienne entre deux points"""
        R = 6371  # Rayon de la Terre en km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def create_distance_matrix(self, locations):
        """Création de la matrice de distance"""
        matrix = []
        for from_counter, from_node in enumerate(locations):
            matrix.append([])
            for to_counter, to_node in enumerate(locations):
                if from_counter == to_counter:
                    matrix[from_counter].append(0)
                else:
                    distance = self._calculate_distance(
                        from_node['lat'], from_node['lng'],
                        to_node['lat'], to_node['lng']
                    )
                    matrix[from_counter].append(int(distance * 1000))  # Convert to meters
        return matrix

    def solve_vrp(self, sale_orders, vehicles):
        """Résolution du problème VRP"""
        # Préparation des données
        depot_location = {'lat': 0, 'lng': 0}  # À remplacer par votre dépôt
        
        locations = [depot_location]  # Dépôt en premier
        for order in sale_orders:
            locations.append({
                'lat': order.partner_latitude,
                'lng': order.partner_longitude,
                'order_id': order.id
            })

        distance_matrix = self.create_distance_matrix(locations)
        
        # Configuration du problème
        data = {
            'distance_matrix': distance_matrix,
            'num_vehicles': len(vehicles),
            'depot': 0
        }

        # Création du manager et du modèle de routage
        manager = pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            data['num_vehicles'],
            data['depot']
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Configuration des contraintes
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            50000,  # distance maximum par véhicule (50km)
            True,  # start cumul to zero
            dimension_name
        )
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        # Paramètres de recherche
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )

        # Résolution
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            return self._extract_solution(manager, routing, solution, sale_orders, vehicles)
        return False

    def _extract_solution(self, manager, routing, solution, sale_orders, vehicles):
        """Extraction de la solution"""
        routes = {}
        for vehicle_id in range(len(vehicles)):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node > 0:  # Ignorer le dépôt
                    route.append(node - 1)  # -1 car le dépôt est à l'index 0
                index = solution.Value(routing.NextVar(index))
            
            if route:  # Seulement si le véhicule a des livraisons
                routes[vehicles[vehicle_id].id] = route

        return routes