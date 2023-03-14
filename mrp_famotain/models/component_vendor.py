# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ComponentVendor(models.Model):
    _name = 'mrp_famotain.component_vendor'
    # _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Vendor', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    price = fields.Monetary('Price', help="normal retail price for selling price calculation", track_visibility='onchange')
    gross_price = fields.Monetary('Gross Price', track_visibility='onchange')
    gross_qty = fields.Float('Gross Qty', help="minimum qty for gross price", track_visibility='onchange')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)