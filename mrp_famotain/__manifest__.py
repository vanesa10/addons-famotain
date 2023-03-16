# -*- coding: utf-8 -*-
{
    'name': "Famotain - MRP",
    'summary': """
        Famotain MRP
    """,
    'author': "Famotain",
    'website': "http://www.famotain.com",
    'version': '0.1',
    'depends': ['base', 'famotain', 'mail', 'uom', 'sales__order'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',

        'views/vendor_views.xml',
        'views/component_views.xml',
        'views/component_color_views.xml',
        'views/component_vendor_views.xml',
        'views/bom_views.xml',
        'views/manufacturing_order_views.xml',

        'views/mrp_famotain_views.xml',
    ],
}
