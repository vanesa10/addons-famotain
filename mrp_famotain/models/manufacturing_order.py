# -*- coding: utf-8 -*-

from odoo import models, fields, api
import math
import logging
_logger = logging.getLogger(__name__)

# BoM: (bisa ditambah/dikurangi manual) taruh di page product order, create waktu confirm po
#  - component_id (auto waktu confirm product order)
#  - component_color_id (milih)
#  - product_order_id
#  - qty [float] (2m, 20pcs, uom nyesuaiin component_id, bisa diganti sesuai kebutuhan saat itu)
#  - vendor_id (vendor yg dipakai) milih
#  - price_calculation (dihitung auto pake normal pricenya component id x kebutuhan)
#  - state (draft, approve, ready, done)
        # draft => po confirm
        # approve => approve po
        # ready => bahan component udah ready
        # done => bahan sudah dipotong


class ManufacturingOrder(models.Model):
    _name = 'mrp_famotain.manufacturing_order'
    _order = 'product_order_id asc'
    _description = 'Manufacturing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Manufacturing Order', default='New', readonly=True, index=True, tracking=True)
    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', required=True, domain=[('state', 'not in', ['done', 'sent', 'cancel'])], track_visibility='onchange')
    product_id = fields.Many2one('famotain.product', 'Product', related="product_order_id.product_id")
    deadline = fields.Date('Deadline', related="product_order_id.deadline")
    net_sales = fields.Monetary('Net Sales', related="product_order_id.total")

    qty = fields.Integer('Qty', track_visibility='onchange', compute="_compute_qty_production_cost", store=True)
    manufactured_by = fields.Many2one('mrp_famotain.vendor', 'Manufactured By', domain=[('active', '=', True), ('is_manufacturer', '=', True)], track_visibility='onchange')

    gross_profit = fields.Monetary('Gross Profit', readonly=True, track_visibility='onchange', compute="_compute_gross_profit", store=True)
    total_cost = fields.Monetary('Total Cost', readonly=True, track_visibility='onchange', compute="compute_total_cost", store=True)
    unit_cost = fields.Monetary('Unit Cost', readonly=True, track_visibility='onchange', compute="compute_total_cost", store=True)
    material_cost = fields.Monetary('Material Cost', readonly=True, track_visibility='onchange', compute="_compute_material_cost", store=True)
    production_cost = fields.Monetary('Production Cost', readonly=True, track_visibility='onchange', compute="_compute_qty_production_cost", store=True)

    bom_ids = fields.One2many('mrp_famotain.bom', 'manufacturing_order_id', 'Bill of Materials')
    bom_line_ids = fields.One2many('mrp_famotain.bom_line', 'manufacturing_order_id', 'BoM Lines')

    state = fields.Selection([('draft', 'Draft'), ('approve','Approved'), ('ready', 'Ready'), ('on_progress', 'On Progress'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    def reset_sequence(self):
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'MRP/%(range_year)s%(range_month)s%(range_day)s/')], limit=1)
        sequences.write({'number_next_actual': 1})
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'BOM.%(range_year)s%(range_month)s%(range_day)s')], limit=1)
        sequences.write({'number_next_actual': 1})

    def prepare_vals_list(self, product_order_id):
        return {
            'product_order_id': product_order_id
        }

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('mrp_famotain.manufacturing_order'),
            })
        manufacturing_order = super(ManufacturingOrder, self).create(vals_list)
        # auto create BoM, BoM line copas dari product order
        manufacturing_order.auto_calculate_bom()
        return manufacturing_order

    @api.one
    def auto_calculate_bom(self):
        bom_ids = self.env['mrp_famotain.bom'].search([('manufacturing_order_id', "=", self.id),
                                                       ('is_calculated', '=', True)])
        for bom in bom_ids:
            bom.unit_qty = 0
        for bom_line_def in self.product_id.bom_line_default_ids:
            pre_bom = self.env['mrp_famotain.bom'].search([('component_id', "=", bom_line_def.component_id.id),
                                                 ('manufacturing_order_id', "=", self.id), ('is_calculated', '=', True)], limit=1)
            pre_bom_unit = pre_bom.unit_qty if pre_bom else 0
            bom_line_vals = {
                'component_id': bom_line_def.component_id.id,
                'product_order_id': self.product_order_id.id,
                'description': bom_line_def.description,
                'qty': bom_line_def.qty,
                'manufacturing_order_id': self.id
            }
            bom_unit = 0
            if bom_line_def.component_id.component_type == 'fabric':
                cut_1 = bom_line_def.height + bom_line_def.component_id.margin_top_bottom
                cut_2 = bom_line_def.width
                if bom_line_def.width > bom_line_def.height:
                    cut_1 = bom_line_def.width + bom_line_def.component_id.margin_top_bottom
                    cut_2 = bom_line_def.height
                bom_unit = ((cut_1 * cut_2 * bom_line_def.qty * self.product_order_id.qty) / ((bom_line_def.component_id.width - 10) * 100))
                bom_line_vals.update({
                    'width': bom_line_def.width,
                    'height': bom_line_def.height,
                })
            elif bom_line_def.component_id.component_type in ['accessories', 'embroidery']:
                bom_unit = bom_line_def.qty * self.product_order_id.qty
            elif bom_line_def.component_id.component_type == 'webbing':
                bom_unit = bom_line_def.length * self.product_order_id.qty / 100
                bom_line_vals.update({
                    'length': bom_line_def.length,
                })
            elif bom_line_def.component_id.component_type == 'print':
                max_print_area = bom_line_def.component_id.max_print_area
                if max_print_area % bom_line_def.width < max_print_area % bom_line_def.height:
                    layout_horizontal = math.floor(max_print_area/bom_line_def.width)
                    vertical = bom_line_def.height
                else:
                    layout_horizontal = math.floor(max_print_area/bom_line_def.height)
                    vertical = bom_line_def.width
                layout_vertical = math.ceil(self.product_order_id.qty/layout_horizontal)
                bom_unit = layout_vertical * vertical / 100
                bom_line_vals.update({
                    'width': bom_line_def.width,
                    'height': bom_line_def.height,
                })
            elif bom_line_def.component_id.component_type == 'others':
                if bom_line_def.length:
                    bom_unit = bom_line_def.length * self.product_order_id.qty / 100
                    bom_line_vals.update({
                        'length': bom_line_def.length,
                    })
                else:
                    bom_unit = bom_line_def.qty * self.product_order_id.qty
            pre_bom_unit += bom_unit
            if pre_bom:
                pre_bom.unit_qty = pre_bom_unit
            else:
                pre_bom = self.env['mrp_famotain.bom'].sudo().create({
                    'component_id': bom_line_def.component_id.id,
                    'manufacturing_order_id': self.id,
                    'unit_qty': pre_bom_unit,
                    'is_calculated': True
                })
            bom_line_vals.update({
                'bom_id': pre_bom.id,
            })
            self.env['mrp_famotain.bom_line'].sudo().create(bom_line_vals)
        bom_ids = self.env['mrp_famotain.bom'].search([('manufacturing_order_id', "=", self.id),
                                                       ('is_calculated', '=', True)])
        for bom in bom_ids:
            if bom.component_id.component_type in ['fabric', 'webbing']:
                bom.unit_qty = math.ceil(bom.unit_qty)
        self._compute_material_cost()

    @api.multi
    @api.onchange('material_cost', 'production_cost')
    @api.depends('material_cost', 'production_cost')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.material_cost + rec.production_cost
            rec.unit_cost = rec.total_cost / rec.qty if rec.qty else 0

    @api.multi
    @api.onchange('bom_ids')
    @api.depends('bom_ids')
    def _compute_material_cost(self):
        for rec in self:
            cost = 0
            for bom in rec.bom_ids:
                cost += bom.cost
            rec.material_cost = cost

    @api.multi
    @api.onchange('total_cost', 'net_sales')
    @api.depends('total_cost', 'net_sales')
    def _compute_gross_profit(self):
        for rec in self:
            rec.gross_profit = rec.net_sales - rec.total_cost

    @api.multi
    @api.onchange('product_order_id')
    @api.depends('product_order_id')
    def _compute_qty_production_cost(self):
        for rec in self:
            rec.qty = rec.product_order_id.qty
            rec.production_cost = rec.product_id.production_cost * rec.qty

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.manufacturing_order_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Manufacturing Order Form',
            'res_model': 'mrp_famotain.manufacturing_order',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class ProductOrder(models.Model):
    _inherit = 'sales__order.product_order'

    manufacturing_order_ids = fields.One2many('mrp_famotain.manufacturing_order', 'product_order_id', 'Manufacturing Orders', readonly=True, track_visibility='onchange',
                                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)]})

    @api.multi
    def action_confirm(self):
        for rec in self:
            super(ProductOrder, self).action_confirm()
            if not rec.manufacturing_order_ids:
                self.env['mrp_famotain.manufacturing_order'].sudo().create({'product_order_id': rec.id})


class Product(models.Model):
    _inherit = 'famotain.product'

    production_cost = fields.Monetary('Production Cost', track_visibility='onchange')