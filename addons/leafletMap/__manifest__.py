{
    "name": "leafletMap",
    "description": "Leaflet Map View",
    "version": "18.0.1.0",
    "category": "Operations",
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
    "depends": ["base", "web"],
    "data": [  
        "security/ir.model.access.csv",  
    ],  
    "assets": {
        "web.assets_backend": [
            "leafletMap/static/src/*",
        ]
    },
}