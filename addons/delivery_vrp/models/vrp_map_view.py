from odoo import models, fields, api
import json

class VRPMapView(models.TransientModel):
    _name = 'vrp.map.view'
    _description = 'VRP Map Viewer'

    vehicles_data = fields.Text('Vehicles Data')

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        vehicles_data = self.env.context.get('default_vehicles_data', [])
        result['vehicles_data'] = json.dumps(vehicles_data)
        return result