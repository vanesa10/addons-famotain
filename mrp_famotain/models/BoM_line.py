# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .component import COMPONENT_TYPE_LIST
import logging
_logger = logging.getLogger(__name__)


class BoMLineDefault(models.Model):
    _name = 'mrp_famotain.bom_line_default'
    _order = 'sequence, name asc'
    _description = 'BoM Line Default'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', related='component_id.component_type')
    product_id = fields.Many2one('famotain.product', 'Product', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, embroidery, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for fabric, printing, webbing, accessories", default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')
    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.multi
    @api.onchange('component_id', 'product_id', 'description')
    @api.depends('component_id', 'product_id', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {} {}".format(rec.product_id.name, rec.component_id.name, rec.description if rec.description else "")

    # @api.onchange('component_type')
    # def onchange_component_type(self):
    #     return {'domain': {'component_id': [('component_type', '=', self.component_type), ('active', '=', True)]}}


class Product(models.Model):
    _inherit = 'famotain.product'

    bom_line_default_ids = fields.One2many('mrp_famotain.bom_line_default', 'product_id', 'BoM Line Default')


class BoMLine(models.Model):
    _name = 'mrp_famotain.bom_line'
    _order = 'name asc'
    _description = 'BoM Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    bom_id = fields.Many2one('mrp_famotain.bom', 'Bill of Materials', track_visibility='onchange')
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', related='component_id.component_type')
    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', related='manufacturing_order_id.product_order_id')
    product_id = fields.Many2one('famotain.product', 'Product', related='product_order_id.product_id')
    manufacturing_order_id = fields.Many2one('mrp_famotain.manufacturing_order', 'Manufacturing Order', related='bom_id.manufacturing_order_id')

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, embroidery, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for fabric, printing, webbing, accessories", default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')

    def prepare_vals_list(self, component_id, product_order_id, decription, qty, width, height, length=0, bom_id=0, manufacturing_order_id=0):
        return{
            'component_id': component_id,
            'product_order_id': product_order_id,
            'description': decription,
            'qty': qty if qty else 1,
            'width': width if width else False,
            'height': height if height else False,
            'length': length if length else False,
            'bom_id': bom_id if bom_id else False,
            'manufacturing_order_id': manufacturing_order_id if manufacturing_order_id else False
        }

    @api.multi
    @api.onchange('component_id', 'product_id', 'description')
    @api.depends('component_id', 'product_id', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {} {}".format(rec.product_id.name, rec.component_id.name, rec.description if rec.description else "")