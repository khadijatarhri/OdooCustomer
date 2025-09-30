# models/vrp_order.py 
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

class VrpOrder(models.Model):
    _name = 'vrp.order'
    _description = 'VRP Order Wrapper'
    
    # Champs existants
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

    # Champs VRP existants
    assigned_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    delivery_sequence = fields.Integer(string='Seq', default=0)
    manual_assignment = fields.Boolean(string='Manual Vehicle Assignment', default=False)
    driver_id = fields.Many2one(related='assigned_vehicle_id.driver_id', string='Driver', readonly=True)

    # Coordonnées
    partner_latitude = fields.Float(string='Latitude', compute='_compute_coordinates', store=True)
    partner_longitude = fields.Float(string='Longitude', compute='_compute_coordinates', store=True)

    # NOUVELLES FONCTIONNALITÉS SIMPLES
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
        store=True
    )
    
    picked_products = fields.Boolean(
        string='Products Picked',
        default=False
    )
    
    picked_date = fields.Datetime(
        string='Picked Date',
        readonly=True
    )
    
    picked_by = fields.Many2one(
        'res.users',
        string='Picked By',
        readonly=True
    )

    @api.depends('sale_order_id.order_line')
    def _compute_product_count(self):
        """Calculer le nombre de produits dans la commande"""
        for record in self:
            if record.sale_order_id and record.sale_order_id.order_line:
                record.product_count = len(record.sale_order_id.order_line)
            else:
                record.product_count = 0

    @api.depends('sale_order_id.partner_id.coordinates')
    def _compute_coordinates(self):
        for record in self:
            try:
                partner = record.sale_order_id.partner_id
                coordinates = partner.coordinates
                
                if coordinates and isinstance(coordinates, dict):
                    lat = float(coordinates.get('latitude', 0.0))
                    lng = float(coordinates.get('longitude', 0.0))
                    
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

    # NOUVELLES MÉTHODES SIMPLES
    @api.onchange('assigned_vehicle_id')
    def _onchange_assigned_vehicle_id(self):
        """Activer manual_assignment quand on change le véhicule manuellement"""
        if self.assigned_vehicle_id and not self._context.get('from_optimization'):
            self.manual_assignment = True

    def action_toggle_picked_status(self):
        """Basculer le statut picked"""
        for record in self:
            if not record.picked_products:
                record.write({
                    'picked_products': True,
                    'picked_date': fields.Datetime.now(),
                    'picked_by': self.env.user.id
                })
            else:
                record.write({
                    'picked_products': False,
                    'picked_date': False,
                    'picked_by': False
                })

    # MÉTHODES EXISTANTES (conservées)
    def action_optimize_delivery_enhanced(self):
        """Optimisation avec gestion robuste des IDs"""
        active_ids = self.env.context.get('active_ids', [])
        
        if not active_ids:
            selected_vrp_orders = self
        else:
            try:
                existing_vrp_orders = self.env['vrp.order'].browse(active_ids).exists()
                if not existing_vrp_orders:
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
        
        sale_orders = selected_vrp_orders.mapped('sale_order_id')
        
        if not sale_orders:
            raise UserError("Aucune commande de vente associée trouvée")
        
        valid_sale_orders = sale_orders.exists()
        if not valid_sale_orders:
            raise UserError("Les commandes de vente associées n'existent plus")
        
        context_with_flag = dict(self.env.context, from_optimization=True)
        result = valid_sale_orders.with_context(context_with_flag).action_optimize_delivery_enhanced()
        
        # Synchronisation
        for vrp_order in selected_vrp_orders:
            if vrp_order.sale_order_id.exists():
                sale_order = vrp_order.sale_order_id
                vrp_order.with_context(from_optimization=True).write({
                    'assigned_vehicle_id': sale_order.assigned_vehicle_id.id if sale_order.assigned_vehicle_id else False,
                    'delivery_sequence': sale_order.delivery_sequence,
                })
        
        return result

    def action_show_map(self):  
        """Déléguer à la méthode sale.order"""  
        selected_orders = self.browse(self.env.context.get('active_ids', [])) or self  
        
        if not selected_orders:  
            raise UserError("Veuillez sélectionner au moins une commande VRP")  
        
        sale_orders = selected_orders.mapped('sale_order_id')  
        
        if not sale_orders:  
            raise UserError("Aucune commande de vente associée trouvée")  
        
        return sale_orders.with_context(active_ids=sale_orders.ids).action_show_map()