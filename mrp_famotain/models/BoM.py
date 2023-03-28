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

class BillOfMaterials(models.Model):
    _name = 'mrp_famotain.bom'
    _order = 'sequence, component_id asc'
    _desc = 'Bill of Materials'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Bill of Materials', default='New', readonly=True, index=True, tracking=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    component_color_id = fields.Many2one('mrp_famotain.component_color', 'Component Color', domain="[('active', '=', True), ('component_id', '=', component_id)]",
                                         track_visibility='onchange', readonly=False, compute="_compute_component_color", store=True)
    manufacturing_order_id = fields.Many2one('mrp_famotain.manufacturing_order', 'Manufacturing Order', required=True, track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})

    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', related="manufacturing_order_id.product_order_id")
    product_id = fields.Many2one('famotain.product', 'Product', related="manufacturing_order_id.product_id")
    qty = fields.Integer('Qty', related="manufacturing_order_id.qty")

    bom_line_ids = fields.One2many('mrp_famotain.bom_line', 'bom_id', 'BoM Lines')

    unit_qty = fields.Float('Unit Qty', track_visibility='onchange', readonly=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related="component_id.uom_id")
    component_vendor_id = fields.Many2one('mrp_famotain.component_vendor', 'Vendor Material', domain="[('active', '=', True), ('component_id', '=', component_id)]",
                                          track_visibility='onchange', compute="_compute_main_vendor", readonly=False, store=True)

    unit_cost = fields.Monetary('Unit Cost', track_visibility='onchange', compute="_compute_unit_cost", store=True)
    cost = fields.Monetary('Cost', track_visibility='onchange', readonly=True, compute="_compute_cost", store=True)
    is_calculated = fields.Boolean('Calculated by System', track_visibility='onchange', readonly=True, default=False)
    sequence = fields.Integer(required=True, default=10)

    state = fields.Selection([('draft', 'Draft'), ('approve','Approved'), ('ready', 'Ready'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    def prepare_vals_list(self, component_id, manufacturing_order_id):
        return {
            'component_id': component_id,
            'manufacturing_order_id': manufacturing_order_id,
        }

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('mrp_famotain.bom'),
            })
        bom = super(BillOfMaterials, self).create(vals_list)
        bom.manufacturing_order_id._compute_material_cost()
        return bom

    @api.model
    def write(self, vals):
        bom = super(BillOfMaterials, self).write(vals)
        self.manufacturing_order_id._compute_material_cost()
        return bom
    #
    # @api.multi
    # @api.onchange('component_id')
    # def onchange_component_id(self):
    #     for rec in self:
    #         return {'domain': {'component_color_id': [('component_id', '=', rec.component_id.id)]}}

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
    @api.onchange('component_id')
    @api.depends('component_id')
    def _compute_component_color(self):
        for rec in self:
            if len(rec.component_id.component_color_ids) == 1:
                rec.component_color_id = rec.component_id.component_color_ids[0]

    @api.multi
    @api.onchange('component_color_id', 'component_vendor_id')
    @api.depends('component_color_id', 'component_vendor_id')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.component_color_id.price if rec.component_color_id.price else rec.component_vendor_id.price

    @api.multi
    @api.onchange('unit_qty', 'unit_cost')
    @api.depends('unit_qty', 'unit_cost')
    def _compute_cost(self):
        for rec in self:
            rec.cost = rec.unit_qty * rec.unit_cost

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.bom_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill of Materials Form',
            'res_model': 'mrp_famotain.bom',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    #action ready. harus check qty sama ga mbe product order qty
    #button recalculate