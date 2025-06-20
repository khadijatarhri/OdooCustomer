from odoo import models, fields, api  
  
class ChatbotConversation(models.Model):  
    _name = 'chatbot.conversation'  
    _description = 'Conversation Chatbot'  
  
    restaurant_id = fields.Many2one('restaurant.restaurant', 'Restaurant', required=True)  
    session_id = fields.Char('ID Session', required=True)  
    customer_name = fields.Char('Nom Client')  
    customer_phone = fields.Char('Téléphone Client')  
    message_ids = fields.One2many('chatbot.message', 'conversation_id', 'Messages')  
    state = fields.Selection([  
        ('active', 'Active'),  
        ('closed', 'Fermée')  
    ], default='active')  
    create_date = fields.Datetime('Date de création', default=fields.Datetime.now)  
  
class ChatbotMessage(models.Model):  
    _name = 'chatbot.message'  
    _description = 'Message Chatbot'  
  
    conversation_id = fields.Many2one('chatbot.conversation', 'Conversation', required=True)  
    message = fields.Text('Message', required=True)  
    is_from_customer = fields.Boolean('Du Client', default=True)  
    timestamp = fields.Datetime('Horodatage', default=fields.Datetime.now)