{
    "name": "Leaflet Map View",
    "description": "Leaflet Map View",
    "version": "18.0.1.0",
    "category": "Operations",
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
    "depends": ["base", "web"],
    "assets": {
        "web.assets_backend": [
            "leaflet_map/static/src/*",
        ]
    },
}