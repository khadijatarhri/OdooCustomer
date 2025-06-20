{  
    'name': 'Restaurant Chatbot',  
    'version': '1.0',  
    'depends': ['base', 'web'],  
    'data': [  
        'security/ir.model.access.csv',  
        'views/restaurant_views.xml',  
        'views/chatbot_views.xml',  
        'views/templates.xml',  
    ],  
    'assets': {  
        'web.assets_frontend': [  
            'restaurant_chatbot/static/src/js/chatbot.js',  
            'restaurant_chatbot/static/src/css/chatbot.css',  
        ],  
    },  
    'installable': True,  
    'application': True,  
}