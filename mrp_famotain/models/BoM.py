# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class BillsOfMaterials(models.Model):
    _name = 'mrp_famotain.bom'
    # _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    product_id = fields.Many2one('famotain.product', 'Product', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for accessories", track_visibility='onchange')
    multiply = fields.Integer('Multiply', default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')