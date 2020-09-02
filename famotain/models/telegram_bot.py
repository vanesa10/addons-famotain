# -*- coding: utf-8 -*-
from telegram.ext import Updater


def send_telegram_message(msg, send_to='admin'):
    chat_id = {
        'admin': '-421477783',
        'design': '-457854010',
        'famotain': '-330715981',
        # 'admin': '1100286010',
        'bella': '998193541',
        'vane': '1100286010',
    }
    token = '1072253932:AAGwYrpWE28tA9FK6D9Too-lIwjWymqVeMo'
    group_chat_id = chat_id[send_to]
    _updater = Updater(token, use_context=True)
    _updater.bot.send_message(group_chat_id, msg, parse_mode='HTML')


