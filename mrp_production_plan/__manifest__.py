# -*- coding: utf-8 -*-
# © 2021 Morwi Encoders Consulting SA DE CV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    'name': "Plan de producción",

    'description': """
        This module creates production plan from sale and mrp
    """,

    'author': "Morwi Econders",
    'website': "http://www.morwi.mx",
    'category': 'MRP',
    'version': '12.0.1.0.2',
    'depends': [
        'mrp',
        'sale_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_plan.xml',
        'views/mrp_views.xml',
        'views/sale_order_views.xml',
    ],
}
