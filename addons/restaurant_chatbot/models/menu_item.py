from odoo import models, fields, api  


class MenuItem(models.Model):  
    _name = 'restaurant.menu.item'  
    _description = 'Article du Menu'  
  
    name = fields.Char('Nom', required=True)  
    description = fields.Text('Description')  
    price = fields.Float('Prix')  
    category = fields.Selection([  
        ('starter', 'Entrée'),  
        ('main', 'Plat Principal'),  
        ('dessert', 'Dessert'),  
        ('drink', 'Boisson')  
    ], 'Catégorie')  
    restaurant_id = fields.Many2one('restaurant.restaurant', 'Restaurant')  
    available = fields.Boolean('Disponible', default=True)