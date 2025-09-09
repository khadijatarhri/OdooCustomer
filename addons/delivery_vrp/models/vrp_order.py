from odoo import models, fields, api  
from odoo.exceptions import UserError  
import math  
import json
try:  
    from ortools.constraint_solver import routing_enums_pb2  
    from ortools.constraint_solver import pywrapcp  
except ImportError:  
    routing_enums_pb2 = None  
    pywrapcp = None  
  
class VrpOrder(models.Model):  
    _name = 'vrp.order'  
    _description = 'VRP Order Wrapper'  
      
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)  
    name = fields.Char(related='sale_order_id.name', string='Delivery Order')  
    partner_id = fields.Many2one(related='sale_order_id.partner_id', string='Customer')  
    delivery_address = fields.Char(string='Delivery Address', compute='_compute_delivery_address', store=True)  
  
    @api.depends('sale_order_id.partner_shipping_id', 'sale_order_id.partner_id')  
    def _compute_delivery_address(self):  
     for record in self:  
        shipping_partner = record.sale_order_id.partner_shipping_id or record.sale_order_id.partner_id  
        if shipping_partner:  
            address_parts = []  
            if shipping_partner.street:  
                address_parts.append(shipping_partner.street)  
            if shipping_partner.city:  
                address_parts.append(shipping_partner.city)  
            if shipping_partner.zip:  
                address_parts.append(shipping_partner.zip)  
            record.delivery_address = ', '.join(address_parts) if address_parts else shipping_partner.name  
        else:  
            record.delivery_address = ''     
             
    # Champs VRP spécifiques  
    assigned_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')  
    delivery_sequence = fields.Integer(string='Seq', default=0)  
    manual_assignment = fields.Boolean(string='Manual Vehicle Assignment', default=False)  
    driver_id = fields.Many2one(related='assigned_vehicle_id.driver_id', string='Driver', readonly=True)  
      
    # Coordonnées  
    # Utilisez des champs computed qui extraient les coordonnées du champ JSON :  
    partner_latitude = fields.Float(string='Latitude', compute='_compute_coordinates', store=True)  
    partner_longitude = fields.Float(string='Longitude', compute='_compute_coordinates', store=True)  
  
    @api.depends('sale_order_id.partner_id.coordinates')  
    def _compute_coordinates(self):  
     for record in self:  
        coordinates = record.sale_order_id.partner_id.coordinates  
        if coordinates and isinstance(coordinates, dict):  
            record.partner_latitude = coordinates.get('latitude', 0.0)  
            record.partner_longitude = coordinates.get('longitude', 0.0)  
        else:  
            record.partner_latitude = 0.0  
            record.partner_longitude = 0.0
  
    def action_optimize_delivery(self):  
        """Optimisation complète avec OR-Tools"""  
        if not routing_enums_pb2 or not pywrapcp:  
            raise UserError("OR-Tools n'est pas installé. Veuillez l'installer avec: pip install ortools")  
          
        selected_orders = self.browse(self.env.context.get('active_ids', []))  
          
        if not selected_orders:  
            raise UserError("Veuillez sélectionner au moins une commande")  
  
        # 1. Vérification des coordonnées des clients  
        orders_without_coords = selected_orders.filtered(  
            lambda o: not o.partner_latitude or not o.partner_longitude  
        )  
        if orders_without_coords:  
            missing_customers = ', '.join(orders_without_coords.mapped('partner_id.name'))  
            raise UserError(f"Les clients suivants n'ont pas de coordonnées : {missing_customers}")  
  
        # 2. Récupération des véhicules disponibles du module fleet  
        vehicles = self.env['fleet.vehicle'].search([  
            ('driver_id', '!=', False),  
            ('active', '=', True)  
        ])  
          
        if not vehicles:  
            raise UserError("Aucun véhicule avec chauffeur disponible")  
  
        # 3. Préparation des données pour OR-Tools  
        locations = []  
        order_mapping = {}  
          
        # Dépôt principal (coordonnées fixes - à adapter selon votre cas)  
        depot_coords = (34.0209, -6.8416)  # Rabat  
        locations.append(depot_coords)  
          
        # Ajouter les coordonnées des clients  
        for i, order in enumerate(selected_orders):  
            locations.append((order.partner_latitude, order.partner_longitude))  
            order_mapping[i + 1] = order  # +1 car index 0 = dépôt  
  
        # 4. Calcul de la matrice de distances euclidiennes  
        def compute_euclidean_distance_matrix(locations):  
            distances = {}  
            for from_counter, from_node in enumerate(locations):  
                distances[from_counter] = {}  
                for to_counter, to_node in enumerate(locations):  
                    if from_counter == to_counter:  
                        distances[from_counter][to_counter] = 0  
                    else:  
                        # Distance euclidienne en mètres  
                        lat1, lon1 = from_node  
                        lat2, lon2 = to_node  
                        distance = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111000  # Approximation  
                        distances[from_counter][to_counter] = int(distance)  
            return distances  
  
        distance_matrix = compute_euclidean_distance_matrix(locations)  
  
        # 5. Configuration du problème OR-Tools  
        data = {}  
        data['distance_matrix'] = distance_matrix  
        data['num_vehicles'] = min(len(vehicles), len(selected_orders))  
        data['depot'] = 0  
  
        # Créer le gestionnaire de routage  
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])  
        routing = pywrapcp.RoutingModel(manager)  
  
        # Fonction de coût de transit  
        def distance_callback(from_index, to_index):  
            from_node = manager.IndexToNode(from_index)  
            to_node = manager.IndexToNode(to_index)  
            return data['distance_matrix'][from_node][to_node]  
  
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)  
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)  
  
        # Contrainte de distance maximale (optionnel)  
        dimension_name = 'Distance'  
        routing.AddDimension(  
            transit_callback_index,  
            0,  # pas de slack  
            300000,  # distance maximale par véhicule (300km)  
            True,  # commencer le cumul à zéro  
            dimension_name)  
        distance_dimension = routing.GetDimensionOrDie(dimension_name)  
        distance_dimension.SetGlobalSpanCostCoefficient(100)  
  
        # 6. Résolution  
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()  
        search_parameters.first_solution_strategy = (  
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)  
        search_parameters.local_search_metaheuristic = (  
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)  
        search_parameters.time_limit.FromSeconds(30)  
  
        solution = routing.SolveWithParameters(search_parameters)  
  
        if not solution:  
            raise UserError("Aucune solution trouvée pour l'optimisation")  
  
        # 7. Application des résultats  
        vehicle_list = list(vehicles)  
          
        for vehicle_id in range(data['num_vehicles']):  
            index = routing.Start(vehicle_id)  
            sequence = 1  
              
            while not routing.IsEnd(index):  
                node_index = manager.IndexToNode(index)  
                if node_index != 0:  # Ignorer le dépôt  
                    order = order_mapping.get(node_index)  
                    if order:  
                        order.write({  
                            'assigned_vehicle_id': vehicle_list[vehicle_id].id,  
                            'delivery_sequence': sequence,  
                            'manual_assignment': False  
                        })  
                        sequence += 1  
                index = solution.Value(routing.NextVar(index))  
  
        return {  
            'type': 'ir.actions.client',  
            'tag': 'display_notification',  
            'params': {  
                'title': 'Optimisation terminée',  
                'message': f'Optimisation réussie pour {len(selected_orders)} commandes avec {data["num_vehicles"]} véhicules',  
                'type': 'success',  
                'sticky': False,  
            }  
        }  
  
    def action_show_map(self):  
        """Affichage de la carte des itinéraires"""  
        selected_orders = self.browse(self.env.context.get('active_ids', []))  
          
        if not selected_orders:  
            raise UserError("Veuillez sélectionner au moins une commande")  
  
        # Préparer les données pour la carte  
        vehicles_data = self._prepare_map_data(selected_orders)  
          
        # Créer un enregistrement temporaire pour la vue carte  
        map_view = self.env['vrp.map.view'].create({  
            'vehicles_data': vehicles_data  
        })  
          
        return {  
            'type': 'ir.actions.act_window',  
            'res_model': 'vrp.map.view',  
            'res_id': map_view.id,  
            'view_mode': 'form',  
            'view_id': self.env.ref('delivery_vrp.vrp_map_view_form').id,  
            'target': 'new',  
            'name': 'Carte des itinéraires'  
        }  
  
    def _prepare_map_data(self, orders):  
        """Préparer les données pour la carte"""  
        vehicles_data = []  
          
        # Grouper par véhicule  
        for vehicle in orders.mapped('assigned_vehicle_id'):  
            if not vehicle:  
                continue  
                  
            vehicle_orders = orders.filtered(lambda o: o.assigned_vehicle_id == vehicle)  
            vehicle_orders = vehicle_orders.sorted('delivery_sequence')  
              
            waypoints = []  
            for order in vehicle_orders:  
                waypoints.append({  
                    'lat': order.partner_latitude,  
                    'lng': order.partner_longitude,  
                    'name': order.partner_id.name,  
                    'address': order.partner_id.contact_address,  
                    'sequence': order.delivery_sequence  
                })  
              
            vehicles_data.append({  
                'vehicle_name': vehicle.name,  
                'vehicle_id': vehicle.id,  
                'driver_name': vehicle.driver_id.name if vehicle.driver_id else '',  
                'waypoints': waypoints  
            })  
          
        return json.dumps(vehicles_data)
