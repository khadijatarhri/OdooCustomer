#addons/sale_kafka_producer/models/sale_order.py

import json
import logging
import os
from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Import conditionnel de Kafka
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    _logger.warning("kafka-python not installed. Install with: pip3 install kafka-python")


class SaleOrderKafkaProducer(models.Model):
    _inherit = 'sale.order'
    
    # Nouveaux champs
    kafka_sent = fields.Boolean(
        string='Sent to Kafka',
        default=False,
        readonly=True,
        help="Indicates if order was sent to Kafka"
    )
    kafka_sent_date = fields.Datetime(
        string='Kafka Send Date',
        readonly=True
    )
    kafka_message_id = fields.Char(
        string='Kafka Message ID',
        readonly=True,
        help="Kafka topic-partition-offset"
    )
    
    @api.model
    def _get_kafka_config(self):
        """Récupère la config Kafka depuis les variables d'environnement"""
        return {
            'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka-broker:29092'),
            'topic': 'odoo-customer-data',
            'enabled': os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
        }
    
    def _get_kafka_producer(self):
        """Crée un producer Kafka singleton"""
        if not KAFKA_AVAILABLE:
            _logger.error("Kafka library not available")
            return None
        
        config = self._get_kafka_config()
        if not config['enabled']:
            _logger.info("Kafka streaming disabled (KAFKA_ENABLED=false)")
            return None
        
        try:
            if not hasattr(self.env, '_kafka_producer'):
                self.env._kafka_producer = KafkaProducer(
                    bootstrap_servers=config['bootstrap_servers'].split(','),
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    acks=1,
                    retries=3,
                    max_in_flight_requests_per_connection=1
                )
                _logger.info(f"Kafka producer connected: {config['bootstrap_servers']}")
            return self.env._kafka_producer
        except KafkaError as e:
            _logger.error(f"Kafka connection failed: {e}")
            return None
    
    def _prepare_kafka_payload(self):
        """Prépare les données pour Kafka (format attendu par Django)"""
        self.ensure_one()
        partner = self.partner_id
        
        # Construire l'adresse complète
        address_parts = [
            partner.street or '',
            partner.street2 or '',
            partner.city or '',
            partner.state_id.name if partner.state_id else '',
            partner.country_id.name if partner.country_id else ''
        ]
        location = ', '.join(filter(None, address_parts))
        
        return {
            # Format Django attendu
            'id': partner.id,
            'customer_id': partner.ref or str(partner.id),
            'name': partner.name or '',
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'location': location,
            
            # Contexte additionnel
            'order_reference': self.name,
            'order_amount': float(self.amount_total),
            'order_date': self.date_order.isoformat() if self.date_order else None,
            'created_at': datetime.now().isoformat(),
            'source': 'odoo_sale_v18',
            
            # Métadonnées
            'metadata': {
                'odoo_version': '18.0',
                'company': self.company_id.name,
                'salesperson': self.user_id.name if self.user_id else None
            }
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create pour envoyer automatiquement vers Kafka"""
        orders = super().create(vals_list)
        
        # Envoyer chaque commande vers Kafka
        for order in orders:
            order._send_to_kafka_async()
        
        return orders
    
    def write(self, vals):
        """Override write pour détecter les changements critiques"""
        result = super().write(vals)
        
        # Champs critiques qui déclenchent un re-envoi Kafka
        critical_fields = {'partner_id', 'partner_invoice_id', 'partner_shipping_id'}
        if any(field in vals for field in critical_fields):
            self._send_to_kafka_async()
        
        return result
    
    def _send_to_kafka_async(self):
        """Envoie asynchrone vers Kafka avec callbacks"""
        for order in self:
            try:
                producer = order._get_kafka_producer()
                if not producer:
                    continue
                
                config = order._get_kafka_config()
                payload = order._prepare_kafka_payload()
                
                # Envoi asynchrone
                future = producer.send(config['topic'], value=payload)
                
                # Callbacks
                future.add_callback(
                    lambda metadata: order._on_kafka_success(metadata, order.id)
                )
                future.add_errback(
                    lambda exc: order._on_kafka_error(exc, order.id)
                )
                
                _logger.info(f"Kafka send initiated: {order.name}")
                
            except Exception as e:
                _logger.error(f"Kafka send error for {order.name}: {e}")
    
    def _on_kafka_success(self, metadata, order_id):
        """Callback succès"""
        try:
            order = self.browse(order_id)
            message_id = f"{metadata.topic}-{metadata.partition}-{metadata.offset}"
            
            order.sudo().write({
                'kafka_sent': True,
                'kafka_sent_date': fields.Datetime.now(),
                'kafka_message_id': message_id
            })
            
            _logger.info(f"Kafka ACK: {message_id}")
        except Exception as e:
            _logger.error(f"Callback error: {e}")
    
    def _on_kafka_error(self, exception, order_id):
        """Callback erreur"""
        _logger.error(f"Kafka error for order {order_id}: {exception}")
    
    def action_resend_kafka(self):
        """Action manuelle pour renvoyer vers Kafka"""
        for order in self:
            order.write({
                'kafka_sent': False,
                'kafka_sent_date': False,
                'kafka_message_id': False
            })
            order._send_to_kafka_async()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Kafka Streaming',
                'message': f'{len(self)} order(s) sent to Kafka',
                'type': 'success',
                'sticky': False,
            }
        }