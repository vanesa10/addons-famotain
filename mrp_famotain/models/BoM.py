# -*- coding: utf-8 -*-
import math

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .component import COMPONENT_TYPE_LIST
import logging
_logger = logging.getLogger(__name__)


class BillOfMaterials(models.Model):
    _name = 'mrp_famotain.bom'
    _order = 'sequence, component_id asc'
    _description = 'Bill of Materials'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Bill of Materials', default='New', readonly=True, index=True, tracking=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange', readonly=True,
                         states={'draft': [('readonly', False)], 'approve': [('readonly', False)]})
    component_type = fields.Selection(COMPONENT_TYPE_LIST, 'Component Type', track_visibility='onchange', compute="_compute_component_detail", store=True, readonly=True)
    component_detail_id = fields.Many2one('mrp_famotain.component_detail', 'Component Detail', domain="[('active', '=', True), ('component_id', '=', component_id)]",
                                         track_visibility='onchange', compute="_compute_component_detail", store=True, readonly=True,
                                          states={'draft': [('readonly', False)], 'approve': [('readonly', False), ('required', True)],
                                                  'on_progress': [('readonly', False)], 'done': [('readonly', False)]})
    manufacturing_order_id = fields.Many2one('mrp_famotain.manufacturing_order', 'Manufacturing Order', required=True, track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})

    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', domain="[('manufacturing_order_id', '=', manufacturing_order_id)]", readonly=True, states={'draft': [('readonly', False)]})
    product_id = fields.Many2one('famotain.product', 'Product', related="product_order_id.product_id")
    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', related="product_order_id.sales_order_id")
    color_notes = fields.Char('Color Notes', related="product_order_id.fabric_color")
    qty = fields.Integer('Qty', track_visibility='onchange', compute="_compute_qty", store=True, readonly=True)
    deadline = fields.Date('Deadline', related="manufacturing_order_id.deadline")
    bom_line_ids = fields.One2many('mrp_famotain.bom_line', 'bom_id', 'BoM Lines', readonly=True,
                                          states={'draft': [('readonly', False)], 'approve': [('readonly', False)]})

    unit_qty = fields.Float('Unit Qty', readonly=True, states={'draft': [('readonly', False)], 'approve': [('readonly', False)]}, track_visibility='onchange')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related="component_id.uom_id")
    component_vendor_id = fields.Many2one('mrp_famotain.component_vendor', 'Vendor Material', domain="[('active', '=', True), ('component_id', '=', component_id)]",
                                          track_visibility='onchange', compute="_compute_main_vendor", store=True, readonly=True,
                                          states={'draft': [('readonly', False)], 'approve': [('readonly', False)], 'ready': [('readonly', False), ('required', True)]})
    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Vendor', readonly=True, compute="_compute_vendor", store=True)

    unit_cost = fields.Monetary('Unit Cost', readonly=True, compute="_compute_unit_cost", store=True)
    cost = fields.Monetary('Cost', readonly=True, compute="_compute_cost", store=True)
    is_calculated = fields.Boolean('Calculated by System', track_visibility='onchange', readonly=True, default=False)
    sequence = fields.Integer(required=True, default=10)

    state = fields.Selection([('draft', 'Draft'), ('approve','Approved'), ('on_vendor', 'On Vendor'), ('ready', 'Ready'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    approve_uid = fields.Many2one('res.users', 'Approved By', readonly=True)
    approve_date = fields.Datetime('Approved On', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled On', readonly=True)
    done_uid = fields.Many2one('res.users', 'Mark as Done By', readonly=True)
    done_date = fields.Datetime('Mark as Done On', readonly=True)

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

    @api.multi
    def write(self, vals):
        bom = super(BillOfMaterials, self).write(vals)
        self.manufacturing_order_id._compute_material_cost()
        if 'qty' in vals:
            self.auto_calculate()
        if 'component_id' in vals:
            for bom_line in self.bom_line_ids:
                bom_line.component_id = self.component_id
        return bom

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                for bom_line in rec.bom_line_ids:
                    bom_line.unlink()
                msg = "{} deleted ({}{} {})".format(rec.name, rec.unit_qty, rec.uom_id.name, rec.component_id.name)
                rec.manufacturing_order_id.message_post(body=msg)
                return super(BillOfMaterials, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.multi
    def force_unlink(self):
        for rec in self:
            for bom_line in rec.bom_line_ids:
                bom_line.force_unlink()
            return super(BillOfMaterials, rec).unlink()

    @api.multi
    def auto_calculate(self):
        for rec in self:
            unit_qty = 0
            for bom_line in rec.bom_line_ids:
                unit_qty += bom_line.calculate(rec.qty)
            rec.write({
                'unit_qty': math.ceil(unit_qty) if rec.component_id.component_type in ['fabric', 'webbing'] else unit_qty,
            })

    @api.multi
    @api.onchange('component_id')
    @api.depends('component_id')
    def _compute_main_vendor(self):
        for rec in self:
            for vendor in rec.component_id.component_vendor_ids:
                if not rec.component_vendor_id and vendor.is_main_vendor:
                    rec.component_vendor_id = vendor.id
                    break

    @api.multi
    @api.onchange('component_vendor_id')
    @api.depends('component_vendor_id')
    def _compute_vendor(self):
        for rec in self:
            rec.vendor_id = rec.component_vendor_id.vendor_id.id

    @api.multi
    @api.onchange('component_id')
    @api.depends('component_id')
    def _compute_component_detail(self):
        for rec in self:
            if len(rec.component_id.component_detail_ids) == 1:
                rec.component_detail_id = rec.component_id.component_detail_ids[0]
            rec.component_type = rec.component_id.component_type


    @api.multi
    @api.onchange('component_detail_id', 'component_vendor_id')
    @api.depends('component_detail_id', 'component_vendor_id')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.component_detail_id.price if rec.component_detail_id.price else rec.component_vendor_id.price

    @api.multi
    @api.onchange('unit_qty', 'unit_cost')
    @api.depends('unit_qty', 'unit_cost')
    def _compute_cost(self):
        for rec in self:
            rec.cost = rec.unit_qty * rec.unit_cost

    @api.multi
    @api.onchange('product_order_id')
    @api.depends('product_order_id')
    def _compute_qty(self):
        for rec in self:
            rec.qty = rec.product_order_id.qty

    # @api.multi
    # @api.onchange('qty')
    # @api.depends('qty')
    # def _compute_unit_qty(self):
    #     for rec in self:
    #         rec.auto_calculate()

    @api.multi
    def action_approve(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'approve'
                rec.approve_date = fields.Datetime.now()
                rec.approve_uid = self.env.user.id

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['approve', 'draft']:
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
            else:
                raise UserError(_("can only cancel draft/approve record"))

    @api.multi
    def action_force_cancel(self):
        for rec in self:
            if rec.state not in ['cancel', 'sent']:
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id

    @api.multi
    def action_send_to_vendor(self):
        for rec in self:
            if rec.state in ['approve', 'draft']:
                if rec.component_detail_id:
                    rec.state = 'on_vendor'
                else:
                    raise UserError(_("Please fill component detail first. Can't process bill of materials with no detail"))

    @api.multi
    def action_ready(self):
        for rec in self:
            if rec.state in ['approve', 'draft', 'on_vendor']:
                if rec.component_detail_id:
                    rec.state = 'ready'
                else:
                    raise UserError(_("Please fill component detail first. Can't process bill of materials with no detail"))

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.state in ['approve', 'ready', 'on_vendor']:
                if rec.component_detail_id and rec.component_vendor_id:
                    rec.state = 'done'
                    rec.done_date = fields.Datetime.now()
                    rec.done_uid = self.env.user.id
                else:
                    raise UserError(_("Please fill component detail or vendor first. Can't process bill of materials with no detail"))

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
