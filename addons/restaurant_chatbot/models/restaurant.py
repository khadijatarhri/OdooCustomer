from odoo import models, fields, api  
  
class Restaurant(models.Model):  
    _name = 'restaurant.restaurant'  
    _description = 'Restaurant'  
  
    name = fields.Char('Nom du Restaurant', required=True)  
    address = fields.Text('Adresse')  
    phone = fields.Char('Téléphone')  
    email = fields.Char('Email')  
    menu_item_ids = fields.One2many('restaurant.menu.item', 'restaurant_id', 'Articles du Menu')  
    chatbot_active = fields.Boolean('Chatbot Actif', default=True)