from odoo import http  
from odoo.http import request  
import json
import openai  
import os
  
class ChatbotController(http.Controller):  
  
    @http.route('/chatbot/send_message', type='json', auth='public', methods=['POST'])  
    def send_message(self, restaurant_id, session_id, message, customer_name=None):  
        # Trouver ou créer la conversation  
        conversation = request.env['chatbot.conversation'].sudo().search([  
            ('restaurant_id', '=', restaurant_id),  
            ('session_id', '=', session_id),  
            ('state', '=', 'active')  
        ], limit=1)  
          
        if not conversation:  
            conversation = request.env['chatbot.conversation'].sudo().create({  
                'restaurant_id': restaurant_id,  
                'session_id': session_id,  
                'customer_name': customer_name,  
            })  
          
        # Enregistrer le message du client  
        request.env['chatbot.message'].sudo().create({  
            'conversation_id': conversation.id,  
            'message': message,  
            'is_from_customer': True,  
        })  
          
        # Générer la réponse du chatbot  
        bot_response = self._generate_bot_response(message, restaurant_id)  
          
        # Enregistrer la réponse du bot  
        request.env['chatbot.message'].sudo().create({  
            'conversation_id': conversation.id,  
            'message': bot_response,  
            'is_from_customer': False,  
        })  
          
        return {'response': bot_response}  
  
    def _generate_bot_response(self, message, restaurant_id):  
        # Ici vous intégrerez votre logique LLM  
        restaurant = request.env['restaurant.restaurant'].sudo().browse(restaurant_id)  
          
        # Logique simple pour commencer  
        if 'menu' in message.lower():  
            menu_items = restaurant.menu_item_ids.filtered('available')  
            response = "Voici notre menu:\n"  
            for item in menu_items:  
                response += f"- {item.name}: {item.price}€\n"  
            return response  
          
        return "Bonjour! Comment puis-je vous aider aujourd'hui?"
    
    def _generate_bot_response_with_llm(self, message, restaurant_id):  
        openai.api_key = os.getenv('OPENAI_API_KEY')  

        restaurant = request.env['restaurant.restaurant'].sudo().browse(restaurant_id)  
          
        # Contexte du restaurant  
        context = f"""  
        Vous êtes l'assistant virtuel du restaurant {restaurant.name}.  
        Menu disponible: {[item.name for item in restaurant.menu_item_ids]}  
        Répondez de manière amicale et professionnelle.  
        """  
          
        response = openai.ChatCompletion.create(  
            model="gpt-3.5-turbo",  
            messages=[  
                {"role": "system", "content": context},  
                {"role": "user", "content": message}  
            ]  
        )  
          
        return response.choices[0].message.content