{
    'name': 'Odoo Fusion Integration',
    'version': '17.0.1.0.69',  # Bumped version for attribute view fixes
    'category': 'Manufacturing',
    'summary': 'Integration between Odoo and Autodesk Fusion 360',
    'author': 'Jaco Tech',
    'website': 'https://jaco.tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mrp', 'product', 'mail'],
    'data': [
        'security/fusion_security.xml',
        'security/ir.model.access.csv',
        'views/fusion_product_views.xml',
        'views/fusion_user_views.xml',
        'views/fusion_attribute_views.xml',
        'views/res_config_settings_views.xml',
        'data/fusion_sequence.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
}
