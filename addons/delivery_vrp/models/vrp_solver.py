from odoo import models, api, _  
import logging  
import math  
from typing import List, Dict, Any  
  
_logger = logging.getLogger(__name__)  
  
class VrpSolver(models.AbstractModel):  
    _name = 'vrp.solver'  
    _description = 'Solver VRP avec OR-Tools'  
  
    @api.model  
    def solve_vrp(self, optimization_record):  
        """  
        Résout le problème VRP pour un enregistrement d'optimisation donné  
        """  
        try:  
            # Import OR-Tools (géré de manière sécurisée)  
            from .vrp_ortools_solver import VrpORToolsSolver  
              
            # Préparation des données  
            vehicles_data = self._prepare_vehicles_data(optimization_record.vehicle_ids)  
            customers_data = self._prepare_customers_data(optimization_record.customer_ids)  
              
            # Configuration du solver  
            solver_config = {  
                'optimization_time': optimization_record.optimization_time,  
                'vehicles': vehicles_data,  
                'customers': customers_data  
            }  
              
            # Résolution  
            solver = VrpORToolsSolver()  
            result = solver.solve(solver_config)  
              
            return {  
                'success': True,  
                'routes': result.get('routes', []),  
                'total_distance': result.get('total_distance', 0),  
                'total_cost': result.get('total_cost', 0),  
                'vehicles_used': result.get('vehicles_used', 0),  
                'score': result.get('score', '')  
            }  
              
        except ImportError:  
            _logger.error('OR-Tools n\'est pas installé')  
            return {  
                'success': False,  
                'error': 'OR-Tools n\'est pas installé. Veuillez l\'installer avec: pip install ortools'  
            }  
        except Exception as e:  
            _logger.error(f'Erreur lors de la résolution VRP: {str(e)}')  
            return {  
                'success': False,  
                'error': str(e)  
            }  
  
    def _prepare_vehicles_data(self, vehicles):  
        """Prépare les données des véhicules pour le solver"""  
        vehicles_data = []  
        for vehicle in vehicles:  
            vehicles_data.append({  
                'id': vehicle.id,  
                'name': vehicle.name,  
                'capacity_weight': vehicle.capacity_weight,  
                'capacity_volume': vehicle.capacity_volume,  
                'max_distance': vehicle.max_distance,  
                'cost_per_km': vehicle.cost_per_km,  
                'depot_location': {  
                    'latitude': vehicle.depot_id.latitude,  
                    'longitude': vehicle.depot_id.longitude  
                }  
            })  
        return vehicles_data  
  
    def _prepare_customers_data(self, customers):  
        """Prépare les données des clients pour le solver"""  
        customers_data = []  
        for customer in customers:  
            customers_data.append({  
                'id': customer.id,  
                'name': customer.name,  
                'location': {  
                    'latitude': customer.latitude,  
                    'longitude': customer.longitude  
                },  
                'demand_weight': customer.demand_weight,  
                'demand_volume': customer.demand_volume,  
                'ready_time': customer.ready_time,  
                'due_time': customer.due_time,  
                'service_time': customer.service_time,  
                'priority': int(customer.priority)  
            })  
        return customers_data