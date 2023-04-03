# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import math
from .component import COMPONENT_TYPE_LIST
import logging
_logger = logging.getLogger(__name__)


class PriceCalculation(models.Model):
    _name = 'mrp_famotain.price_calculation'
    # _order = 'sales_order_id asc'
    _description = 'Price Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Price Calculation', default='New', readonly=True, index=True, tracking=True)
    qty = fields.Integer('Qty', track_visibility='onchange', default=12)
    bom_ids = fields.One2many('mrp_famotain.bom_calculation', 'price_calculation_id', 'Bill of Materials')
    bom_line_ids = fields.One2many('mrp_famotain.bom_line_calculation', 'price_calculation_id', 'Bill of Materials Line')

    production_cost = fields.Monetary('Unit Production Cost', track_visibility='onchange')
    material_cost = fields.Monetary('Material Cost', readonly=True, store=True, compute='_compute_material_cost')
    total_cost = fields.Monetary('Total Cost', readonly=True, store=True, compute='compute_cost')

    unit_sales = fields.Monetary('Unit Sales', track_visibility='onchange')
    unit_cost = fields.Monetary('Unit Cost', readonly=True, store=True, compute='compute_cost')
    unit_profit = fields.Monetary('Unit Profit', readonly=True, store=True, compute='compute_profit')

    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('mrp_famotain.price_calculation'),
            })
        return super(PriceCalculation, self).create(vals_list)

    @api.multi
    def write(self, vals):
        pc = super(PriceCalculation, self).write(vals)
        if 'bom_ids' in vals.keys():
            self.compute_cost()
            self.compute_profit()
        return pc

    @api.multi
    @api.onchange('bom_ids')
    @api.depends('bom_ids')
    def _compute_material_cost(self):
        for rec in self:
            material_cost = 0
            for bom in rec.bom_ids:
                material_cost += bom.cost
            rec.material_cost = material_cost
            rec.compute_cost()
            rec.compute_profit()

    @api.multi
    @api.onchange('qty', 'production_cost')
    @api.depends('qty', 'production_cost')
    def compute_cost(self):
        for rec in self:
            total_cost = rec.material_cost + (rec.production_cost * rec.qty)
            rec.total_cost = total_cost
            if rec.qty:
                rec.unit_cost = total_cost / rec.qty

    @api.multi
    @api.onchange('unit_sales', 'unit_cost')
    @api.depends('unit_sales', 'unit_cost')
    def compute_profit(self):
        for rec in self:
            rec.unit_profit = rec.unit_sales - rec.unit_cost

    @api.one
    def auto_calculate_all_bom(self):
        for bom in self.bom_ids:
            bom.unlink()
        for bom_line in self.bom_line_ids:
            pre_bom = self.env['mrp_famotain.bom_calculation'].search(
                [('component_id', "=", bom_line.component_id.id), ('price_calculation_id', "=", self.id)], limit=1)
            pre_bom_unit = pre_bom.unit_qty if pre_bom else 0
            pre_bom_unit += bom_line.calculate(self.qty)
            if pre_bom:
                pre_bom.unit_qty = pre_bom_unit
            else:
                self.env['mrp_famotain.bom_calculation'].sudo().create({
                    'component_id': bom_line.component_id.id,
                    'price_calculation_id': self.id,
                    'unit_qty': pre_bom_unit,
                    'is_calculated': True,
                    'sequence': bom_line.sequence
                })
        bom_ids = self.env['mrp_famotain.bom_calculation'].search([('price_calculation_id', "=", self.id)])
        for bom in bom_ids:
            if bom.component_id.component_type in ['fabric', 'webbing']:
                bom.unit_qty = math.ceil(bom.unit_qty)
        self._compute_material_cost()


class BoMLineCalculation(models.Model):
    _name = 'mrp_famotain.bom_line_calculation'
    _order = 'sequence, name asc'
    _description = 'BoM Line Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', related='component_id.component_type')

    price_calculation_id = fields.Many2one('mrp_famotain.price_calculation', 'Price Calculation', readonly=True)
    # bom_id = fields.Many2one('mrp_famotain.bom_calculation', 'BoM Calculation', track_visibility='onchange', readonly=True)

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, embroidery, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for fabric, printing, webbing, accessories", default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')
    sequence = fields.Integer(required=True, default=10)
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.multi
    @api.onchange('component_id', 'description')
    @api.depends('component_id', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {}".format(rec.component_id.name, rec.description if rec.description else "")

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.bom_line_default_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'BoM Line Calculation Form',
            'res_model': 'mrp_famotain.bom_line_calculation',
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


class BillOfMaterialsCalculation(models.Model):
    _name = 'mrp_famotain.bom_calculation'
    _order = 'sequence, component_id asc'
    _description = 'Bill of Materials Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    price_calculation_id = fields.Many2one('mrp_famotain.price_calculation', 'Price Calculation', readonly=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], readonly=True)
    component_vendor_id = fields.Many2one('mrp_famotain.component_vendor', 'Vendor Material',
                                          domain="[('active', '=', True), ('component_id', '=', component_id)]",
                                          track_visibility='onchange', compute="_compute_main_vendor", store=True, readonly=False)
    qty = fields.Integer('Qty', related="price_calculation_id.qty")

    # bom_line_calculation_ids = fields.One2many('mrp_famotain.bom_line_calculation', 'bom_id', 'BoM Lines')

    unit_qty = fields.Float('Unit Qty', readonly=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related="component_id.uom_id")

    unit_cost = fields.Monetary('Unit Cost', readonly=False, compute="_compute_unit_cost", store=True)
    cost = fields.Monetary('Cost', readonly=True, compute="_compute_cost", store=True)

    sequence = fields.Integer(required=True, default=10)
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.multi
    @api.onchange('unit_qty', 'component_id')
    @api.depends('unit_qty', 'component_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {}".format(rec.unit_qty, rec.component_id.name)

    @api.model
    def create(self, vals_list):
        bom = super(BillOfMaterialsCalculation, self).create(vals_list)
        return bom

    @api.multi
    def write(self, vals):
        bom = super(BillOfMaterialsCalculation, self).write(vals)
        return bom

    @api.multi
    def auto_calculate(self):
        for rec in self:
            unit_qty = 0
            for bom_line in rec.bom_line_ids:
                unit_qty += bom_line.calculate(rec.qty)
            rec.write({
                'unit_qty': math.ceil(unit_qty) if rec.component_id.component_type in ['fabric', 'webbing'] else unit_qty
            })

    @api.multi
    @api.onchange('component_id')
    @api.depends('component_id')
    def _compute_main_vendor(self):
        for rec in self:
            for vendor in rec.component_id.component_vendor_ids:
                if vendor.is_main_vendor:
                    rec.component_vendor_id = vendor.id
                    break

    @api.multi
    @api.onchange('component_vendor_id')
    @api.depends('component_vendor_id')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.component_vendor_id.price

    @api.multi
    @api.onchange('unit_qty', 'unit_cost')
    @api.depends('unit_qty', 'unit_cost')
    def _compute_cost(self):
        for rec in self:
            rec.cost = rec.unit_qty * rec.unit_cost

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.bom_calculation_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'BoM Calculation Form',
            'res_model': 'mrp_famotain.bom_calculation',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }