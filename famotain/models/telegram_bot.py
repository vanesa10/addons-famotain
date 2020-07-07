# -*- coding: utf-8 -*-
from telegram.ext import Updater


def send_telegram_message(msg):
    token = '1072253932:AAGwYrpWE28tA9FK6D9Too-lIwjWymqVeMo'
    group_chat_id = '-421477783'
    _updater = Updater(token, use_context=True)
    _updater.bot.send_message(group_chat_id, msg, parse_mode='HTML')


