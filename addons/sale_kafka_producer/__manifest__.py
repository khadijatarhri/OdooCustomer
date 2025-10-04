{
    'name': 'Sale Kafka Producer',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Stream sale orders to Kafka for data governance',
    'author': 'Your Company',
    'depends': ['sale_management'],  
    'data': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}