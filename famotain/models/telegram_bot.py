# -*- coding: utf-8 -*-
from telegram.ext import Updater


def send_telegram_message(msg, send_to='admin_group'):
    chat_id = {
        'admin_group': '-421477783', #for admin
        'design_group': '-457854010', #for design
        'famotain_report_group': '-330715981', #for report
        # 'admin': '1100286010',
        'bella_user': '998193541',
        'vane_user': '1100286010',
        'late_delivery_group': '-920660317',
        'deadline_today_group': '-881903909',
        'manufacturing_group': '-927849558',
        'urgent_group': '-870240519'
    }
    token = '1072253932:AAGwYrpWE28tA9FK6D9Too-lIwjWymqVeMo'
    group_chat_id = chat_id[send_to]
    _updater = Updater(token, use_context=True)
    _updater.bot.send_message(group_chat_id, msg, parse_mode='HTML')


