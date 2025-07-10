{
    'name': 'Vehicle Routing Problem (VRP)',
    'version': '18.0.1.0',
    'category': 'Operations',
    'summary': 'Optimisation des tournées de véhicules avec OptaPlanner',
    'description': """
        Module VRP pour Odoo
        ===================
        
        Ce module permet d'optimiser les tournées de véhicules en utilisant:
        - OptaPlanner pour l'optimisation
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
    'author': 'Votre Nom',
    'website': 'https://www.votre-site.com',
    'depends': ['base', 'web', 'contacts'],
    'external_dependencies': {
        'python': ['optaplanner', 'matplotlib', 'numpy'],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/vrp_security.xml',
        'views/vrp_vehicle_views.xml',
        'views/vrp_customer_views.xml',
        'views/vrp_route_views.xml',
        'views/vrp_optimization_views.xml',
        'views/vrp_menus.xml',
        'data/vrp_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vrp/static/src/js/vrp_map.js',
            'vrp/static/src/css/vrp_style.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}