# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

COMPONENT_TYPE_LIST = [('fabric', 'Fabric'), ('accessories', 'Accessories'), ('webbing', 'Webbing'), ('print', 'Print'), ('embroidery', 'Embroidery')]


class Component(models.Model):
    _name = 'mrp_famotain.component'
    # _order = 'name asc'
    _description = 'Component of a product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Component Name', required=True, index=True, track_visibility='onchange')
    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', required=True, track_visibility='onchange')
    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Main Vendor', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    display_name = fields.Char('Display Name', track_visibility='onchange')
    width = fields.Float('Width (cm)', track_visibility='onchange') #only for fabric
    margin_top_bottom = fields.Float('Margin Cutting Top Bottom (cm)', track_visibility='onchange') #only for fabric
    margin_left_right = fields.Float('Margin Cutting Left Right (cm)', track_visibility='onchange') #only for fabric
    max_print_area = fields.Float('Max Print Area (cm)', track_visibility='onchange') #only for printing

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')