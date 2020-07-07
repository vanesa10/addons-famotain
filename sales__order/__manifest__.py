# -*- coding: utf-8 -*-
{
    'name': "Famotain - Sales Order",
    'summary': """
        Famotain Sales Order
    """,
    'author': "Famotain",
    'website': "http://www.famotain.com",
    'version': '0.1',
    'depends': ['base', 'famotain', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/sales__order_views.xml',
        'views/invoice_views.xml',
        'views/customer_views.xml',
        'views/product_order_views.xml',
        'views/res_company.xml',
        'report/report_template.xml',
        'report/sales_order_report.xml',
    ],
}
