{
    'name': 'Vehicle Routing Problem (VRP)',
    'version': '18.0.1.0',
    'category': 'Operations',
    'summary': 'Optimisation des tournées de véhicules avec Ortools',
    'description': """
        Module VRP pour Odoo
        ===================
        
        Ce module permet d'optimiser les tournées de véhicules en utilisant:
        - Ortools pour l'optimisation
        - Contraintes hard et soft configurables
        - Interface utilisateur intuitive
        - Intégration avec les partenaires Odoo
        - Gestion des véhicules et leurs capacités
        - Planification automatique des tournées
        
        Fonctionnalités:
        - Création et gestion des véhicules
        - Import/Export des clients depuis les partenaires
        - Optimisation automatique des tournées
        - Visualisation des résultats
        - Rapports détaillés
    """,
    'author': 'Khadija',
    'depends': ['base', 'web', 'contacts','sale','fleet','stock'],
    'external_dependencies': {
        'python': ['matplotlib', 'numpy' ,'ortools'],
    },
    'data': [  
     'security/vrp_security.xml',        # 1. Sécurité d'abord  
     'security/ir.model.access.csv',     # 2. Permissions des modèles  
     'data/vrp_data.xml',               # 3. Données de base  
     'views/vrp_vehicle_views.xml',      # 4. Vues des véhicules  
     'views/vrp_customer_views.xml',     # 5. Vues des clients  
     'views/vrp_map_view.xml',
     'views/res_config_settings_views.xml', # 6. Configuration  
     'views/vrp_menus.xml',             # 7. Menus en dernier  
],
    'assets': {    
    'web.assets_backend': [ 
        #'delivery_vrp/static/src/*',  
        'delivery_vrp/static/src/css/vrp_route_map.css',  
        'delivery_vrp/static/src/js/vrp_route_map_widget.js',  
        'delivery_vrp/static/src/xml/vrp_route_map_template.xml',    
    ],    
},

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}