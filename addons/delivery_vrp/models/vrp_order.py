# models/vrp_order_cleaned.py - VERSION CORRIGÉE
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

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

    # Coordonnées - calculées depuis le JSON du partenaire
    partner_latitude = fields.Float(string='Latitude', compute='_compute_coordinates', store=True)
    partner_longitude = fields.Float(string='Longitude', compute='_compute_coordinates', store=True)

    @api.depends('sale_order_id.partner_id.coordinates')
    def _compute_coordinates(self):
        for record in self:
            try:
                partner = record.sale_order_id.partner_id
                coordinates = partner.coordinates
                
                if coordinates and isinstance(coordinates, dict):
                    lat = float(coordinates.get('latitude', 0.0))
                    lng = float(coordinates.get('longitude', 0.0))
                    
                    # Validation des coordonnées
                    if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0.0 or lng != 0.0):
                        record.partner_latitude = lat
                        record.partner_longitude = lng
                    else:
                        record.partner_latitude = 0.0
                        record.partner_longitude = 0.0
                else:
                    record.partner_latitude = 0.0
                    record.partner_longitude = 0.0
            except Exception:
                record.partner_latitude = 0.0
                record.partner_longitude = 0.0

    def action_optimize_delivery_enhanced(self):
        """CORRIGÉE: Déléguer à sale.order avec gestion robuste des IDs"""
        # CORRECTION PRINCIPALE : Gestion sécurisée des active_ids
        active_ids = self.env.context.get('active_ids', [])
        
        if not active_ids:
            selected_vrp_orders = self
        else:
            # Vérifier que les vrp orders existent encore
            try:
                existing_vrp_orders = self.env['vrp.order'].browse(active_ids).exists()
                if not existing_vrp_orders:
                    # Si aucun ID valide, récupérer tous les VRP orders disponibles
                    available_vrp_orders = self.env['vrp.order'].search([
                        ('sale_order_id', '!=', False),
                        ('sale_order_id.state', 'in', ['sale', 'done'])
                    ])
                    if not available_vrp_orders:
                        raise UserError(
                            "Aucune commande VRP valide trouvée. "
                            "Veuillez créer des commandes de vente confirmées."
                        )
                    selected_vrp_orders = available_vrp_orders
                else:
                    selected_vrp_orders = existing_vrp_orders
            except Exception as e:
                _logger.error(f"Erreur lors de la récupération des VRP orders: {str(e)}")
                raise UserError(
                    "Erreur lors de la sélection des commandes VRP. "
                    "Veuillez actualiser la page et réessayer."
                )
        
        # Récupérer les sale orders correspondantes
        sale_orders = selected_vrp_orders.mapped('sale_order_id')
        
        if not sale_orders:
            raise UserError("Aucune commande de vente associée trouvée")
        
        # Vérifier que les sale orders existent toujours
        valid_sale_orders = sale_orders.exists()
        if not valid_sale_orders:
            raise UserError("Les commandes de vente associées n'existent plus")
        
        _logger.info(f"Processing {len(valid_sale_orders)} valid sale orders from {len(selected_vrp_orders)} VRP orders")
        
        # Appeler l'optimisation sur les sale orders avec le contexte mis à jour
        result = valid_sale_orders.with_context(active_ids=valid_sale_orders.ids).action_optimize_delivery_enhanced()
        
        # SYNCHRONISATION AUTOMATIQUE après optimisation
        for vrp_order in selected_vrp_orders:
            if vrp_order.sale_order_id.exists():  # Vérifier que le sale order existe encore
                sale_order = vrp_order.sale_order_id
                vrp_order.write({
                    'assigned_vehicle_id': sale_order.assigned_vehicle_id.id if sale_order.assigned_vehicle_id else False,
                    'delivery_sequence': sale_order.delivery_sequence,
                })
        
        # Retourner le résultat de l'optimisation
        return result

    def action_show_map(self):
        """Déléguer à sale.order pour la carte avec gestion sécurisée"""
        sale_orders = self.mapped('sale_order_id').exists()
        if not sale_orders:
            raise UserError("Aucune commande de vente valide trouvée pour afficher la carte")
        return sale_orders.action_show_map()

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