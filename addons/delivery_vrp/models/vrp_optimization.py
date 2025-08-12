from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

class VrpOptimization(models.Model):
    _name = 'vrp.optimization'
    _description = 'Optimisation VRP'
    _order = 'create_date desc'

    name = fields.Char('Nom', required=True)
    date = fields.Date('Date', required=True, default=fields.Date.today)
    
    # Paramètres d'optimisation
    optimization_time = fields.Integer('Temps d\'optimisation (s)', default=30)
    vehicle_ids = fields.Many2many('vrp.vehicle', string='Véhicules disponibles')
    customer_ids = fields.Many2many('vrp.customer', string='Clients à visiter')
    
    # Résultats
    total_distance = fields.Float('Distance totale (km)', readonly=True)
    total_cost = fields.Float('Coût total (Dh)', readonly=True)
    vehicles_used = fields.Integer('Véhicules utilisés', readonly=True)
    optimization_score = fields.Char('Score d\'optimisation', readonly=True)
    
    # Statut
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('running', 'En cours'),
        ('done', 'Terminée'),
        ('error', 'Erreur')
    ], string='Statut', default='draft')
    
    # Relations
    route_ids = fields.One2many('vrp.route', 'optimization_id', string='Tournées générées')
    
    # Logs
    log_ids = fields.One2many('vrp.optimization.log', 'optimization_id', string='Logs')
    
    @api.constrains('vehicle_ids', 'customer_ids')
    def _check_data(self):
        for record in self:
            if not record.vehicle_ids:
                raise ValidationError(_('Au moins un véhicule doit être sélectionné'))
            if not record.customer_ids:
                raise ValidationError(_('Au moins un client doit être sélectionné'))

    def action_optimize(self):
        """Lance l'optimisation VRP"""
        try:
            self.state = 'running'
            self._log_message('Début de l\'optimisation')
            
            # Appel du solver VRP
            solver = self.env['vrp.solver']
            result = solver.solve_vrp(self)
            
            if result.get('success'):
                self._process_optimization_result(result)
                self.state = 'done'
                self._log_message('Optimisation terminée avec succès')
            else:
                self.state = 'error'
                self._log_message(f'Erreur: {result.get("error", "Erreur inconnue")}')
                
        except Exception as e:
            self.state = 'error'
            self._log_message(f'Erreur lors de l\'optimisation: {str(e)}')
            _logger.error(f'Erreur VRP: {str(e)}', exc_info=True)
            raise UserError(_('Erreur lors de l\'optimisation: %s') % str(e))

    def _process_optimization_result(self, result):
        """Traite les résultats de l'optimisation"""
        # Supprimer les anciennes tournées
        self.route_ids.unlink()
        
        # Créer les nouvelles tournées
        for route_data in result.get('routes', []):
            route = self.env['vrp.route'].create({
                'name': f"{self.name} - {route_data['vehicle_name']}",
                'date': self.date,
                'vehicle_id': route_data['vehicle_id'],
                'optimization_id': self.id,
                'total_distance': route_data['total_distance'],
                'total_duration': route_data['total_duration'],
                'total_demand': route_data['total_demand'],
                'state': 'planned'
            })
            
            # Créer les visites
            for visit_data in route_data.get('visits', []):
                self.env['vrp.visit'].create({
                    'route_id': route.id,
                    'customer_id': visit_data['customer_id'],
                    'sequence': visit_data['sequence'],
                    'planned_arrival': visit_data['arrival_time'],
                    'planned_departure': visit_data['departure_time'],
                    'distance_from_previous': visit_data['distance'],
                    'state': 'planned'
                })
        
        # Mettre à jour les statistiques globales
        self.total_distance = result.get('total_distance', 0)
        self.total_cost = result.get('total_cost', 0)
        self.vehicles_used = result.get('vehicles_used', 0)
        self.optimization_score = result.get('score', '')

    def _log_message(self, message):
        """Ajoute un log"""
        self.env['vrp.optimization.log'].create({
            'optimization_id': self.id,
            'message': message,
            'timestamp': fields.Datetime.now()
        })

    def action_view_routes(self):
        """Ouvre la vue des tournées générées"""
        return {
            'name': _('Tournées générées'),
            'type': 'ir.actions.act_window',
            'res_model': 'vrp.route',
            'view_mode': 'tree,form',
            'domain': [('optimization_id', '=', self.id)],
            'context': {'default_optimization_id': self.id}
        }

class VrpOptimizationLog(models.Model):
    _name = 'vrp.optimization.log'
    _description = 'Log d\'optimisation VRP'
    _order = 'timestamp desc'

    optimization_id = fields.Many2one('vrp.optimization', string='Optimisation', required=True, ondelete='cascade')
    message = fields.Text('Message', required=True)
    timestamp = fields.Datetime('Horodatage', required=True)
    level = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur')
    ], string='Niveau', default='info')
