from odoo import models, fields, api  
from odoo.exceptions import UserError  
  
class SaleOrder(models.Model):  
    _inherit = 'sale.order'  
      
    assigned_vehicle_id = fields.Many2one('fleet.vehicle', string='Assigned Vehicle')  
    delivery_sequence = fields.Integer(string='Delivery Sequence', default=0)  
    partner_latitude = fields.Float(related='partner_id.partner_latitude', string='Latitude')  
    partner_longitude = fields.Float(related='partner_id.partner_longitude', string='Longitude')  
  


    manual_assignment = fields.Boolean(string='Manual Vehicle Assignment', default=False)  
    driver_id = fields.Many2one(related='assigned_vehicle_id.driver_id', string='Driver', readonly=True) 

    """starting_point = fields.Char(related='assigned_vehicle_id.depot_id.name', string='Starting Point', readonly=True)"""
    delivery_count = fields.Integer(string='Delivery Count', compute='_compute_delivery_count', store=True)  
  
    @api.depends('order_line')  
    def _compute_delivery_count(self):  
     for order in self:  
        order.delivery_count = len(order.order_line)
 
    
    def action_optimize_delivery(self):  
      """Action appelée par le bouton Optimize"""  
      selected_orders = self.browse(self.env.context.get('active_ids', []))  
      
      if not selected_orders:  
        raise UserError("Veuillez sélectionner au moins une commande")  
  
      # Vérifier que tous les clients ont des coordonnées  
      orders_without_coords = selected_orders.filtered(  
        lambda o: not o.partner_latitude or not o.partner_longitude  
      )  
      if orders_without_coords:  
        raise UserError(  
            f"Les clients suivants n'ont pas de coordonnées : "  
            f"{', '.join(orders_without_coords.mapped('partner_id.name'))}"  
        )  
  
      # Récupérer les véhicules disponibles du module fleet  
      vehicles = self.env['fleet.vehicle'].search([  
        ('driver_id', '!=', False),  
        ('active', '=', True)  
      ])  
      
      if not vehicles:  
        raise UserError("Aucun véhicule avec chauffeur disponible")  
  
      # Lancer l'optimisation OR-Tools  
      optimizer = self.env['vrp.optimizer'].create({})  
      routes = optimizer.solve_vrp(selected_orders, vehicles)  
  
      if not routes:  
        raise UserError("Impossible de trouver une solution optimale")  
  
      # Appliquer les résultats  
      self._apply_optimization_results(selected_orders, routes, vehicles)  
  
      # Recharger la vue avec groupement  
      return self._reload_view_with_grouping()  
  
    def _apply_optimization_results(self, orders, routes, vehicles):  
      """Appliquer les résultats de l'optimisation"""  
      # Reset des affectations précédentes  
      orders.write({  
        'assigned_vehicle_id': False,  
        'delivery_sequence': 0  
      })  
  
      vehicle_dict = {v.id: v for v in vehicles}  
      orders_list = list(orders)  
  
      for vehicle_id, route_indices in routes.items():  
        vehicle = vehicle_dict[vehicle_id]  
        for sequence, order_index in enumerate(route_indices):  
            order = orders_list[order_index]  
            order.write({  
                'assigned_vehicle_id': vehicle_id,  
                'delivery_sequence': sequence + 1  
            })  
  
    def _reload_view_with_grouping(self):  
      """Recharger la vue avec groupement par véhicule"""  
      return {  
        'type': 'ir.actions.act_window',  
        'name': 'Optimized Deliveries',  
        'res_model': 'sale.order',  
        'view_mode': 'tree',  
        'view_id': self.env.ref('delivery_vrp.sale_order_vrp_tree_view').id,  
        'domain': [('id', 'in', self.ids)],  
        'context': {  
            'group_by': ['assigned_vehicle_id'],  
            'expand': True  
        }  
      }
    def action_show_map(self):  
      """Afficher la carte avec les itinéraires"""  
      selected_orders = self.browse(self.env.context.get('active_ids', []))  
      
      if not selected_orders:  
        raise UserError("Veuillez sélectionner au moins une commande")  
  
      # Grouper les commandes par véhicule  
      vehicles_data = self._prepare_map_data(selected_orders)  
      
      return {  
        'type': 'ir.actions.act_window',  
        'name': 'Delivery Routes Map',  
        'res_model': 'vrp.map.view',  
        'view_mode': 'form',  
        'target': 'new',  
        'context': {  
            'default_vehicles_data': vehicles_data,  
        }  
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
      
      return vehicles_data