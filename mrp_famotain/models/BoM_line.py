# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .component import COMPONENT_TYPE_LIST
import math
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

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.bom_line_default_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'BoM Line Default Form',
            'res_model': 'mrp_famotain.bom_line_default',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def calculate(self, qty):
        bom_unit = 0
        if self.component_id.component_type == 'fabric':
            cut_1 = self.height + self.component_id.margin_top_bottom
            cut_2 = self.width
            if self.width > self.height:
                cut_1 = self.width + self.component_id.margin_top_bottom
                cut_2 = self.height
            bom_unit = (cut_1 * cut_2 * self.qty * qty) / ((self.component_id.width - (
                    2 * self.component_id.margin_left_right)) * 100)
        elif self.component_id.component_type in ['accessories', 'embroidery']:
            bom_unit = self.qty * qty
        elif self.component_id.component_type == 'webbing':
            bom_unit = self.length * self.qty * qty / 100
        elif self.component_id.component_type == 'print':
            max_print_area = self.component_id.max_print_area
            if max_print_area % self.width < max_print_area % self.height:
                layout_horizontal = math.floor(max_print_area / self.width)
                vertical = self.height
            else:
                layout_horizontal = math.floor(max_print_area / self.height)
                vertical = self.width
            layout_vertical = math.ceil(qty * self.qty / layout_horizontal)
            bom_unit = layout_vertical * vertical / 100
        elif self.component_id.component_type == 'others':
            if self.length:
                bom_unit = self.length * self.qty * qty / 100
            else:
                bom_unit = self.qty * qty
        return bom_unit


class Product(models.Model):
    _inherit = 'famotain.product'

    bom_line_default_ids = fields.One2many('mrp_famotain.bom_line_default', 'product_id', 'BoM Line Default')


class BoMLine(models.Model):
    _name = 'mrp_famotain.bom_line'
    _order = 'sequence, name asc'
    _description = 'BoM Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    bom_id = fields.Many2one('mrp_famotain.bom', 'Bill of Materials', track_visibility='onchange', required=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', related='component_id.component_type')
    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', readonly=True, track_visibility='onchange')
    product_id = fields.Many2one('famotain.product', 'Product', related='product_order_id.product_id')
    manufacturing_order_id = fields.Many2one('mrp_famotain.manufacturing_order', 'Manufacturing Order', related='bom_id.manufacturing_order_id')
    bom_line_default_id = fields.Many2one('mrp_famotain.bom_line_default', 'BoM Line Default', readonly=True)

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, embroidery, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for fabric, printing, webbing, accessories", default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')
    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.model
    def create(self, vals_list):
        bom_line = super(BoMLine, self).create(vals_list)
        if 'dont_auto_calculate' not in vals_list:
            bom_line.bom_id.auto_calculate()
        return bom_line

    @api.multi
    def write(self, vals):
        bom_line = super(BoMLine, self).write(vals)
        if 'dont_auto_calculate' not in vals:
            self.bom_id.auto_calculate()
        return bom_line

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            bom_id = rec.bom_id
            if bom_id.state in ['draft', 'approve']:
                msg = "BoM line {} deleted".format(rec.name)
                rec_unlink = super(BoMLine, self).unlink()
                bom_id.message_post(body=msg)
                bom_id.auto_calculate()
                return rec_unlink
            raise UserError(_("You can only delete bom line on a draft/approved bom"))

    @api.multi
    def force_unlink(self):
        for rec in self:
            return super(BoMLine, rec).unlink()

    @api.multi
    @api.onchange('component_id', 'product_id', 'description')
    @api.depends('component_id', 'product_id', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {} {}".format(rec.product_id.name, rec.component_id.name, rec.description if rec.description else "")

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.bom_line_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'BoM Line Form',
            'res_model': 'mrp_famotain.bom_line',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def calculate(self, qty):
        bom_unit = 0
        if self.component_id.component_type == 'fabric':
            cut_1 = self.height + self.component_id.margin_top_bottom
            cut_2 = self.width
            if self.width > self.height:
                cut_1 = self.width + self.component_id.margin_top_bottom
                cut_2 = self.height
            bom_unit = (cut_1 * cut_2 * self.qty * qty) / ((self.component_id.width - (
                    2 * self.component_id.margin_left_right)) * 100)
        elif self.component_id.component_type in ['accessories', 'embroidery']:
            bom_unit = self.qty * qty
        elif self.component_id.component_type == 'webbing':
            bom_unit = self.length * self.qty * qty / 100
        elif self.component_id.component_type == 'print':
            max_print_area = self.component_id.max_print_area
            if max_print_area % self.width < max_print_area % self.height:
                layout_horizontal = math.floor(max_print_area / self.width)
                vertical = self.height
            else:
                layout_horizontal = math.floor(max_print_area / self.height)
                vertical = self.width
            layout_vertical = math.ceil(qty * self.qty / layout_horizontal)
            bom_unit = layout_vertical * vertical / 100
        elif self.component_id.component_type == 'others':
            if self.length:
                bom_unit = self.length * self.qty * qty / 100
            else:
                bom_unit = self.qty * qty
        return bom_unit


