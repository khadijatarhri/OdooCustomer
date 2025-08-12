import math  
from typing import List, Optional, Dict, Any  
from ortools.constraint_solver import routing_enums_pb2  
from ortools.constraint_solver import pywrapcp  
  
class VrpORToolsSolver:  
    """Solver VRP utilisant OR-Tools, intégré dans Odoo"""  
      
    def __init__(self):  
        pass  
      
    def solve(self, config: Dict[str, Any]) -> Dict[str, Any]:  
        """Résout le problème VRP avec la configuration donnée"""  
        try:  
            # Préparation des données  
            data = self._create_data_model(config)  
              
            # Création du gestionnaire de routage  
            manager = pywrapcp.RoutingIndexManager(  
                len(data['distance_matrix']),  
                len(data['vehicles']),  
                data['depot']  
            )  
              
            # Création du modèle de routage  
            routing = pywrapcp.RoutingModel(manager)  
              
            # Définition de la fonction de coût  
            def distance_callback(from_index, to_index):  
                from_node = manager.IndexToNode(from_index)  
                to_node = manager.IndexToNode(to_index)  
                return data['distance_matrix'][from_node][to_node]  
              
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)  
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)  
              
            # Contraintes de capacité  
            def demand_callback(from_index):  
                from_node = manager.IndexToNode(from_index)  
                return data['demands'][from_node]  
              
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)  
            routing.AddDimensionWithVehicleCapacity(  
                demand_callback_index,  
                0,  # null capacity slack  
                data['vehicle_capacities'],  # vehicle maximum capacities  
                True,  # start cumul to zero  
                'Capacity'  
            )  
              
            # Contraintes de temps  
            def time_callback(from_index, to_index):  
                from_node = manager.IndexToNode(from_index)  
                to_node = manager.IndexToNode(to_index)  
                return data['time_matrix'][from_node][to_node] + data['service_times'][from_node]  
              
            time_callback_index = routing.RegisterTransitCallback(time_callback)  
            routing.AddDimension(  
                time_callback_index,  
                30,  # allow waiting time  
                3000,  # maximum time per vehicle  
                False,  # Don't force start cumul to zero  
                'Time'  
            )  
            #time_dimension = routing.GetDimensionOrDie('Time')  
              
            # Fenêtres de temps pour les clients  
            #for location_idx, time_window in enumerate(data['time_windows']):  
            #    if location_idx == data['depot']:  
            #        continue  
            #    index = manager.NodeToIndex(location_idx)  
            #    time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])  
              
            # Fenêtres de temps pour le dépôt  
            #depot_idx = data['depot']  
            #for vehicle_id in range(len(data['vehicles'])):  
            #    index = routing.Start(vehicle_id)  
            #    time_dimension.CumulVar(index).SetRange(  
            #        data['time_windows'][depot_idx][0],  
            #        data['time_windows'][depot_idx][1]  
            #    )  
              
            # Paramètres de recherche  
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()  
            search_parameters.first_solution_strategy = (  
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC  
            )  
            search_parameters.local_search_metaheuristic = (  
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH  
            )  
            search_parameters.time_limit.FromSeconds(config['optimization_time'])  
              
            # Résolution  
            solution = routing.SolveWithParameters(search_parameters)  
              
            if solution:  
                return self._convert_solution_to_odoo(data, manager, routing, solution)  
            else:  
                status = routing.status()  
                if status == routing.ROUTING_NOT_SOLVED:
                   raise Exception("Problème non résolu - vérifiez les contraintes")  
                elif status == routing.ROUTING_FAIL:
                    raise Exception("Échec du routage - données invalides")  
                elif status == routing.ROUTING_FAIL_TIMEOUT:  
                     raise Exception("Timeout - augmentez le temps d'optimisation")  
                else:  
                     raise Exception(f"Statut inconnu: {status}")
                             
                  
        except Exception as e:  
            raise Exception(f"Erreur lors de la résolution VRP: {str(e)}")  
      
    def _create_data_model(self, config: Dict[str, Any]) -> Dict[str, Any]:  
        """Crée le modèle de données pour OR-Tools"""  
        vehicles = config['vehicles']  
        customers = config['customers']  
          
        #logs pour déboguer  
        print(f"DEBUG - Véhicules reçus: {vehicles}")  
        print(f"DEBUG - Clients reçus: {customers}")  

        # Création de la liste des locations (dépôt + clients)  
        locations = []  
          
        # Ajouter le dépôt (toujours en premier)  
        depot_location = vehicles[0]['depot_location']  
        locations.append((depot_location['latitude'], depot_location['longitude']))  
          
        # Ajouter les clients  
        for customer in customers:  
            locations.append((customer['location']['latitude'], customer['location']['longitude']))  
          
        # Calcul de la matrice des distances  
        distance_matrix = []  
        time_matrix = []  
        for i, loc1 in enumerate(locations):  
            distance_row = []  
            time_row = []  
            for j, loc2 in enumerate(locations):  
                distance = self._calculate_distance(loc1, loc2)  
                distance_row.append(int(distance * 1000))  # en mètres  
                time_row.append(int(distance / 50 * 3600))  # temps en secondes (50 km/h)  
            distance_matrix.append(distance_row)  
            time_matrix.append(time_row)  
          
        # Demandes (dépôt = 0, clients = leur demande)  
        demands = [0]  # dépôt  
        for customer in customers:  
            demands.append(int(customer['demand_weight']))  
          
        # Capacités des véhicules  
        vehicle_capacities = [int(vehicle['capacity_weight']) for vehicle in vehicles]  
          
        # Temps de service  
        service_times = [0]  # dépôt  
        for customer in customers:  
            service_times.append(int(customer.get('service_time', 0) * 60))  # en secondes  
          
        # Fenêtres de temps  
        time_windows = [(0, 24 * 3600)]  # dépôt ouvert 24h  
        for customer in customers:  
            start_time = int(customer.get('ready_time', 0) * 3600)  
            end_time = int(customer.get('due_time', 24) * 3600)  
            time_windows.append((start_time, end_time))  
          
        return {  
            'distance_matrix': distance_matrix,  
            'time_matrix': time_matrix,  
            'demands': demands,  
            'vehicle_capacities': vehicle_capacities,  
            'service_times': service_times,  
            'time_windows': time_windows,  
            'vehicles': vehicles,  
            'customers': customers,  
            'depot': 0  
        }  
      
    def _calculate_distance(self, loc1, loc2):  
        """Calcule la distance entre deux points GPS (formule haversine)"""  
        lat1, lon1 = math.radians(loc1[0]), math.radians(loc1[1])  
        lat2, lon2 = math.radians(loc2[0]), math.radians(loc2[1])  
          
        dlat = lat2 - lat1  
        dlon = lon2 - lon1  
          
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2  
        c = 2 * math.asin(math.sqrt(a))  
          
        # Rayon de la Terre en kilomètres  
        r = 6371  
          
        return c * r  
      
    def _convert_solution_to_odoo(self, data, manager, routing, solution) -> Dict[str, Any]:  
        """Convertit la solution OR-Tools en format Odoo"""  
        routes = []  
        total_distance = 0  
        total_cost = 0  
        vehicles_used = 0  
          
        for vehicle_id in range(len(data['vehicles'])):  
            index = routing.Start(vehicle_id)  
            route_distance = 0  
            route_demand = 0  
            route_visits = []  
            sequence = 1  
              
            while not routing.IsEnd(index):  
                node_index = manager.IndexToNode(index)  
                next_index = solution.Value(routing.NextVar(index))  
                next_node_index = manager.IndexToNode(next_index)  
                  
                if node_index != data['depot']:  # Pas le dépôt  
                    customer_idx = node_index - 1  # -1 car le dépôt est en position 0  
                    customer = data['customers'][customer_idx]  
                      
                    # Calcul du temps d'arrivée  
                    time_var = routing.GetDimensionOrDie('Time').CumulVar(index)  
                    arrival_time = solution.Value(time_var) / 3600.0  # en heures  
                    departure_time = arrival_time + customer.get('service_time', 0) / 60.0  
                      
                    # Distance depuis le point précédent  
                    distance_from_previous = data['distance_matrix'][manager.IndexToNode(routing.Start(vehicle_id)) if sequence == 1 else prev_node][node_index] / 1000.0  
                      
                    route_visits.append({  
                        'customer_id': customer['id'],  
                        'sequence': sequence,  
                        'arrival_time': arrival_time,  
                        'departure_time': departure_time,  
                        'distance': distance_from_previous  
                    })  
                      
                    route_demand += customer['demand_weight']  
                    sequence += 1  
                  
                # Distance pour ce segment  
                route_distance += data['distance_matrix'][node_index][next_node_index] / 1000.0  
                prev_node = node_index  
                index = next_index  
              
            if route_visits:  # Seulement si le véhicule a des visites  
                vehicle = data['vehicles'][vehicle_id]  
                route_duration = route_distance / 50.0  # Estimation à 50 km/h  
                route_cost = route_distance * vehicle['cost_per_km']  
                  
                routes.append({  
                    'vehicle_id': vehicle['id'],  
                    'vehicle_name': vehicle['name'],  
                    'total_distance': route_distance,  
                    'total_duration': route_duration,  
                    'total_demand': route_demand,  
                    'visits': route_visits  
                })  
                  
                total_distance += route_distance  
                total_cost += route_cost  
                vehicles_used += 1  
          
        return {  
            'routes': routes,  
            'total_distance': total_distance,  
            'total_cost': total_cost,  
            'vehicles_used': vehicles_used,  
            'score': f'Distance totale: {total_distance:.2f} km'  
        }
