# -*- coding: utf-8 -*-
{
    'name': "Famotain",
    'summary': """
        Famotain Base
    """,
    'author': "Famotain",
    'website': "http://www.famotain.com",
    'version': '0.1',
    'depends': ['base', 'mail'],
    'data': [
        'security/famotain_security.xml',
        'security/ir.model.access.csv',
        'data/paper_format.xml',
        'data/settings.xml',
        'data/courier_shipment.xml',
        'data/product_category.xml',
        'views/product_views.xml',
        # 'views/fabric_views.xml',
        'views/courier_shipment_views.xml',
        'views/settings_views.xml',
        'views/product_category_views.xml',
        'views/report_common.xml',
    ],
}
