# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DesignSize(models.Model):
    _name = 'famotain.design_size'
    _description = 'Product design sizes'

    name = fields.Char('Description', required=True, index=True)
    width = fields.Float('Width')
    height = fields.Float('Height')
    product_id = fields.Many2one('famotain.product', 'Product', required=True)
    notes = fields.Text('Notes')
