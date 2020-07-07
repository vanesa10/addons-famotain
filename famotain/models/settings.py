# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Settings(models.Model):
    _name = 'famotain.settings'
    _description = 'Backend Settings'

    name = fields.Char('Settings', required=True, index=True)
    key_name = fields.Char('Key Name', required=True)
    number_value = fields.Integer('Number Value')
    text_value = fields.Char('Text Value')
    binary_value = fields.Binary("Image", attachment=True)
    notes = fields.Text('Notes')
    active = fields.Boolean('Active', readonly=True, default=1)
