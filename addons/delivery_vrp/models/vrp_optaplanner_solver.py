import math
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# Import conditionnel d'OptaPlanner
try:
    from optaplanner import *
    from optaplanner.types import *
    OPTAPLANNER_AVAILABLE = True
except ImportError:
    OPTAPLANNER_AVAILABLE = False

class VrpOptaPlannerSolver:
    """Solver VRP utilisant OptaPlanner, intégré dans Odoo"""
    
    def __init__(self):
        if not OPTAPLANNER_AVAILABLE:
            raise ImportError("OptaPlanner n'est pas disponible")
    
    def solve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Résout le problème VRP avec la configuration donnée"""
        try:
            # Création du problème
            problem = self._create_problem(config)
            
            # Configuration du solver
            solver_config = self._create_solver_config(config)
            solver = SolverFactory.create(solver_config).buildSolver()
            
            # Résolution
            solution = solver.solve(problem)
            
            # Conversion des résultats pour Odoo
            return self._convert_solution_to_odoo(solution)
            
        except Exception as e:
            raise Exception(f"Erreur lors de la résolution VRP: {str(e)}")
    
    def _create_problem(self, config: Dict[str, Any]):
        """Crée le problème VRP à partir de la configuration"""
        # Ici on adapte le code du script précédent
        # en utilisant les données venues d'Odoo
        
        # Création des locations
        locations = {}
        
        # Dépôts
        for vehicle_data in config['vehicles']:
            depot_loc = vehicle_data['depot_location']
            if 'depot' not in locations:
                locations['depot'] = Location(0, "Depot", depot_loc['latitude'], depot_loc['longitude'])
        
        # Clients
        customers = []
        for i, customer_data in enumerate(config['customers'], 1):
            location = Location(
                i, customer_data['name'],
                customer_data['location']['latitude'],
                customer_data['location']['longitude']
            )
            
            customer = Customer(
                customer_data['id'],
                customer_data['name'],
                location,
                customer_data['demand_weight'],
                customer_data['ready_time'] * 60,  # Conversion en minutes
                customer_data['due_time'] * 60,
                customer_data['service_time'] * 60,
                customer_data['priority']
            )
            customers.append(customer)
        
        # Véhicules
        vehicles = []
        for vehicle_data in config['vehicles']:
            vehicle = Vehicle(
                vehicle_data['id'],
                vehicle_data['name'],
                vehicle_data['capacity_weight'],
                locations['depot'],
                vehicle_data['max_distance'],
                vehicle_data['cost_per_km']
            )
            vehicles.append(vehicle)
        
        # Visites
        visits = [Visit(customer) for customer in customers]
        
        # Solution
        solution = VrpSolution()
        solution.vehicles = vehicles
        solution.customers = customers
        solution.visits = visits
        
        return solution
    
    def _create_solver_config(self, config: Dict[str, Any]):
        """Crée la configuration du solver"""
        solver_config = SolverConfig() \
            .withSolutionClass(VrpSolution) \
            .withEntityClasses(Visit) \
            .withConstraintProviderClass(define_constraints) \
            .withTerminationSpentLimit(Duration.ofSeconds(config['optimization_time']))
        
        return solver_config
    
    def _convert_solution_to_odoo(self, solution) -> Dict[str, Any]:
        """Convertit la solution OptaPlanner en format Odoo"""
        # Groupement des visites par véhicule
        vehicle_routes = {}
        for visit in solution.visits:
            if visit.vehicle is not None:
                if visit.vehicle not in vehicle_routes:
                    vehicle_routes[visit.vehicle] = []
                vehicle_routes[visit.vehicle].append(visit)
        
        routes = []
        total_distance = 0
        total_cost = 0
        
        for vehicle, visits in vehicle_routes.items():
            if not visits:
                continue
            
            # Tri des visites par ordre d'arrivée
            visits.sort(key=lambda v: v.calculate_arrival_time())
            
            route_distance = calculate_total_distance(vehicle, visits)
            route_demand = sum(visit.get_demand() for visit in visits)
            route_duration = visits[-1].calculate_departure_time() / 60  # en heures
            
            total_distance += route_distance
            total_cost += route_distance * vehicle.cost_per_km
            
            # Données de la route
            route_data = {
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.name,
                'total_distance': route_distance,
                'total_duration': route_duration,
                'total_demand': route_demand,
                'visits': []
            }
            
            # Données des visites
            for i, visit in enumerate(visits):
                visit_data = {
                    'customer_id': visit.customer.id,
                    'sequence': i + 1,
                    'arrival_time': visit.calculate_arrival_time() / 60,  # en heures
                    'departure_time': visit.calculate_departure_time() / 60,
                    'distance': calculate_visit_distance(visit) / 10  # en km
                }
                route_data['visits'].append(visit_data)
            
            routes.append(route_data)
        
        return {
            'routes': routes,
            'total_distance': total_distance,
            'total_cost': total_cost,
            'vehicles_used': len(vehicle_routes),
            'score': str(solution.get_score()) if solution.get_score() else 'N/A'
        }
