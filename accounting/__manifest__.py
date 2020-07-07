# -*- coding: utf-8 -*-
{
    'name': "Famotain - Accounting",
    'summary': """
        Famotain Accounting
    """,
    'author': "Famotain",
    'website': "http://www.famotain.com",
    'version': '0.1',
    'depends': ['base', 'famotain'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_type_views.xml',
        'views/account_views.xml',
        'views/journal_views.xml',
        'views/journal_account_views.xml',
        'views/menu_item_views.xml',
    ],
}
