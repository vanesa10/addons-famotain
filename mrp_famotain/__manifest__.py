# -*- coding: utf-8 -*-
{
    'name': "Famotain - MRP",
    'summary': """
        Famotain MRP
    """,
    'author': "Famotain",
    'website': "http://www.famotain.com",
    'version': '0.1',
    'depends': ['base', 'famotain', 'mail', 'uom'],
    'data': [
        'security/ir.model.access.csv',

        'views/mrp_famotain_views.xml'
    ],
}
