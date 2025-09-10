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
        'security/vrp_security.xml',
        'security/ir.model.access.csv',
        'views/vrp_vehicle_views.xml',
        'views/vrp_customer_views.xml',
        'views/res_config_settings_views.xml',
        'views/vrp_menus.xml',
        'data/vrp_data.xml',
    ],
    'assets': {    
    'web.assets_backend': [ 
        'delivery_vrp/static/src/*',  
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