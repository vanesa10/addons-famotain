# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import math
import logging
_logger = logging.getLogger(__name__)

#TODO: ubah semua vannn. haruse 1 MO punya banyak PO.

class ManufacturingOrder(models.Model):
    _name = 'mrp_famotain.manufacturing_order'
    _order = 'sales_order_id asc'
    _description = 'Manufacturing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Manufacturing Order', default='New', readonly=True, index=True, tracking=True)

    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', readonly=True, states={'draft': [('readonly', False)]})
    product_order_ids = fields.One2many('sales__order.product_order', 'manufacturing_order_id', 'Product Orders', readonly=True,
                                        states={'draft': [('readonly', False)], 'approve': [('readonly', False)]},
                                        domain="[('sales_order_id', '=', sales_order_id)]")
    bom_ids = fields.One2many('mrp_famotain.bom', 'manufacturing_order_id', 'Bill of Materials', readonly=True,
                         states={'draft': [('readonly', False)], 'approve': [('readonly', False)], 'ready': [('readonly', False)], 'on_progress': [('readonly', False)]})
    bom_line_ids = fields.One2many('mrp_famotain.bom_line', 'manufacturing_order_id', 'BoM Lines', readonly=True,
                         states={'draft': [('readonly', False)], 'approve': [('readonly', False)], 'ready': [('readonly', False)], 'on_progress': [('readonly', False)]})

    deadline = fields.Date('Deadline', related="sales_order_id.deadline")
    manufactured_by = fields.Many2one('mrp_famotain.vendor', 'Manufactured By', track_visibility='onchange', readonly=True,
                                      domain=[('active', '=', True), ('is_manufacturer', '=', True)],
                                      states={'draft': [('readonly', False)], 'approve': [('readonly', False)], 'ready': [('readonly', False)], 'on_progress': [('readonly', False)]})

    product_qty = fields.Integer('Product Qty', track_visibility='onchange', compute="_compute_sales", store=True, readonly=True, default=1,
                         states={'draft': [('readonly', False)], 'approve': [('readonly', False)]})

    net_sales = fields.Monetary('Net Sales', readonly=True, compute="_compute_sales", store=True, track_visibility='onchange')
    product_unit_sales = fields.Monetary('Product Unit Sales', readonly=True, compute="_compute_sales", store=True, track_visibility='onchange')

    gross_profit = fields.Monetary('Gross Profit', readonly=True, compute="_compute_profit", store=True) #net sales - total cost
    unit_profit = fields.Monetary('Unit Profit', readonly=True, compute="_compute_profit", store=True) #gross profit / product_qty

    total_cost = fields.Monetary('Total Cost', readonly=True, compute="compute_cost", store=True) #material cost + production cost
    unit_cost = fields.Monetary('Unit Cost', readonly=True, compute="compute_cost", store=True) #unit cost / product_qty

    material_cost = fields.Monetary('Material Cost', readonly=True, compute="_compute_material_cost", store=True) #semua costnya bom
    production_cost = fields.Monetary('Production Cost', readonly=True, compute="_compute_sales", store=True) #semua production cost dr product order

    state = fields.Selection([('draft', 'Draft'), ('approve','Approved'), ('ready', 'Ready'), ('on_progress', 'On Progress'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    approve_uid = fields.Many2one('res.users', 'Approved By', readonly=True)
    approve_date = fields.Datetime('Approved On', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled On', readonly=True)
    done_uid = fields.Many2one('res.users', 'Mark as Done By', readonly=True)
    done_date = fields.Datetime('Mark as Done On', readonly=True)

    def reset_sequence(self):
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'MRP/%(range_year)s%(range_month)s%(range_day)s/')], limit=1)
        sequences.write({'number_next_actual': 1})
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'BOM.%(range_year)s%(range_month)s%(range_day)s')], limit=1)
        sequences.write({'number_next_actual': 1})

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('mrp_famotain.manufacturing_order'),
            })
        manufacturing_order = super(ManufacturingOrder, self).create(vals_list)
        # auto create BoM, BoM line copas dari product order
        manufacturing_order.auto_calculate_all_bom()
        return manufacturing_order

    @api.multi
    def write(self, vals):
        mo = super(ManufacturingOrder, self).write(vals)
        auto_calculate = False
        if vals.get('sales_order_id'):
            for bom in self.bom_ids:
                bom.force_unlink()
            self.auto_calculate_all_bom()
            auto_calculate = True
        if vals.get('product_qty'):
            if not auto_calculate:
                self.auto_calculate_all_bom()
        return mo

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                for bom in rec.bom_ids:
                    bom.unlink()
                msg = "{} deleted ({}pcs {})".format(rec.name, rec.qty, rec.product_id.name)
                rec.sales_order_id.message_post(body=msg)
                return super(ManufacturingOrder, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.one
    def auto_calculate_all_bom(self):
        for po in self.product_order_ids:
            bom_ids = self.env['mrp_famotain.bom'].search([('manufacturing_order_id', "=", self.id), ('product_order_id', "=", po.id),
                                                           ('is_calculated', '=', True)])
            for bom in bom_ids:
                bom.unit_qty = 0
            for bom_line_def in po.product_id.bom_line_default_ids:
                pre_bom = self.env['mrp_famotain.bom'].search([('component_id', "=", bom_line_def.component_id.id), ('product_order_id', "=", po.id),
                                                               ('manufacturing_order_id', "=", self.id), ('is_calculated', '=', True)], limit=1)
                pre_bom_unit = pre_bom.unit_qty if pre_bom else 0
                pre_bom_unit += bom_line_def.calculate(po.qty)
                if pre_bom:
                    pre_bom.unit_qty = pre_bom_unit
                else:
                    pre_bom = self.env['mrp_famotain.bom'].sudo().create({
                        'component_id': bom_line_def.component_id.id,
                        'manufacturing_order_id': self.id,
                        'product_order_id': po.id,
                        'unit_qty': pre_bom_unit,
                        'is_calculated': True,
                    })
                bom_line_vals = {
                    'component_id': bom_line_def.component_id.id,
                    'product_order_id': po.id,
                    'description': bom_line_def.description,
                    'qty': bom_line_def.qty,
                    'manufacturing_order_id': self.id,
                    'bom_line_default_id': bom_line_def.id,
                    'bom_id': pre_bom.id,
                    'dont_auto_calculate': True
                }
                if bom_line_def.component_id.component_type in ['fabric', 'print']:
                    bom_line_vals.update({
                        'width': bom_line_def.width,
                        'height': bom_line_def.height,
                    })
                elif bom_line_def.component_id.component_type in ['webbing', 'others']:
                    if bom_line_def.length:
                        bom_line_vals.update({
                            'length': bom_line_def.length,
                        })
                bom_line = self.env['mrp_famotain.bom_line'].search([('manufacturing_order_id', "=", self.id), ('product_order_id', "=", po.id),
                                                                     ('bom_line_default_id', '=', bom_line_def.id)])
                if not bom_line:
                    self.env['mrp_famotain.bom_line'].sudo().create(bom_line_vals)
                else:
                    bom_line.write(bom_line_vals)
            bom_ids = self.env['mrp_famotain.bom'].search([('manufacturing_order_id', "=", self.id), ('product_order_id', "=", po.id),
                                                           ('is_calculated', '=', True)])
            for bom in bom_ids:
                if bom.component_id.component_type in ['fabric', 'webbing']:
                    bom.unit_qty = math.ceil(bom.unit_qty)
            self._compute_material_cost()
            msg = "{}pcs - {} BoM auto calculated".format(self.qty, self.product_id.name)
            self.message_post(body=msg)

    @api.multi
    @api.onchange('product_order_ids')
    @api.depends('product_order_ids')
    def _compute_sales(self):
        for rec in self:
            qty = 0
            net_sales = 0
            unit_sales = 0
            production_cost = 0
            for product_order in rec.product_order_ids:
                net_sales += product_order.total
                unit_sales += product_order.price
                if product_order.product_type == 'product':
                    qty += product_order.qty
                    production_cost += product_order.product_id.production_cost
            rec.net_sales = net_sales
            rec.product_unit_sales = unit_sales
            rec.product_qty = qty
            rec.production_cost = production_cost
            # rec.write({
            #     'net_sales': net_sales,
            #     'product_unit_sales': unit_sales,
            #     'product_qty': qty,
            #     'production_cost': production_cost
            # })

    @api.multi
    @api.onchange('bom_ids')
    @api.depends('bom_ids')
    def _compute_material_cost(self):
        for rec in self:
            material_cost = 0
            for bom in rec.bom_ids:
                material_cost += bom.cost
            rec.material_cost = material_cost
            # rec.write({
            #     'material_cost': material_cost
            # })

    @api.multi
    @api.onchange('net_sales', 'total_cost', 'product_qty')
    @api.depends('net_sales', 'total_cost', 'product_qty')
    def _compute_profit(self):
        for rec in self:
            gross_profit = rec.net_sales - rec.total_cost
            rec.gross_profit = gross_profit
            rec.unit_profit = gross_profit / rec.product_qty
            # rec.write({
            #     'gross_profit': gross_profit,
            #     'unit_profit': gross_profit / rec.product_qty,
            # })

    # @api.multi
    # @api.onchange('gross_profit', 'product_qty')
    # @api.depends('gross_profit', 'product_qty')
    # def _compute_unit_profit(self):
    #     for rec in self:
    #         if rec.product_qty > 0:
    #             rec.write({
    #                 'unit_profit': rec.gross_profit / rec.product_qty,
    #             })

    @api.multi
    @api.onchange('material_cost', 'production_cost', 'product_qty')
    @api.depends('material_cost', 'production_cost', 'product_qty')
    def compute_cost(self):
        for rec in self:
            total_cost = rec.material_cost + rec.production_cost
            rec.total_cost = total_cost
            rec.unit_cost = total_cost / rec.product_qty
            # rec.write({
            #     'total_cost': total_cost,
            #     'unit_cost': total_cost / rec.product_qty,
            # })

    # @api.multi
    # @api.onchange('total_cost', 'product_qty')
    # @api.depends('total_cost', 'product_qty')
    # def compute_unit_cost(self):
    #     for rec in self:
    #         if rec.product_qty > 0:
    #             rec.write({
    #                 'unit_cost': rec.total_cost / rec.product_qty,
    #             })

    @api.multi
    def action_approve(self):
        for rec in self:
            if rec.state in ['draft']:
                # set all bom to approve
                for bom in rec.bom_ids:
                    bom.action_approve()
                rec.state = 'approve'
                rec.approve_date = fields.Datetime.now()
                rec.approve_uid = self.env.user.id

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['draft', 'approve']:
                for bom in rec.bom_ids:
                    bom.action_cancel()
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
            else:
                raise UserError(_("can only cancel draft/approve record"))

    @api.multi
    def action_force_cancel(self):
        for rec in self:
            if rec.state not in ['cancel', 'sent']:
                for bom in rec.bom_ids:
                    bom.action_force_cancel()
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id

    @api.multi
    def action_ready(self):
        for rec in self:
            if rec.state in ['approve', 'draft']:
                bom_ready = True
                for bom in rec.bom_ids:
                    if bom.state in ['draft', 'approve']:
                        bom_ready = False
                        break
                if bom_ready:
                    rec.state = 'ready'
                else:
                    raise UserError(_("Materials aren't all ready"))

    @api.multi
    def action_force_ready(self):
        for rec in self:
            if rec.state in ['approve', 'draft']:
                for bom in rec.bom_ids:
                    bom.action_ready()
                rec.state = 'ready'

    @api.multi
    def action_on_progress(self):
        for rec in self:
            if rec.state in ['approve', 'ready']:
                for bom in rec.bom_ids:
                    bom.action_done()
                rec.state = 'on_progress'

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.state in ['ready', 'on_progress']:
                rec.state = 'done'
                rec.done_date = fields.Datetime.now()
                rec.done_uid = self.env.user.id

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

    manufacturing_order_id = fields.Many2one('mrp_famotain.manufacturing_order', 'Manufacturing Orders', readonly=True)

    @api.multi
    def action_confirm(self):
        for rec in self:
            super(ProductOrder, self).action_confirm()
            if not rec.manufacturing_order_id and rec.product_type != 'charge':
                if rec.product_id.bom_line_default_ids:
                    mo = self.env['mrp_famotain.manufacturing_order'].sudo().create({'product_order_id': rec.id})
                    rec.manufacturing_order_id = mo.id

    @api.multi
    def action_approve(self):
        for rec in self:
            super(ProductOrder, self).action_approve()
            rec.manufacturing_order_id.action_approve()
            # for mo in rec.manufacturing_order_ids:
            #     mo.action_approve()


class SalesOrder(models.Model):
    _inherit = 'sales__order.sales__order'

    manufacturing_order_ids = fields.One2many('mrp_famotain.manufacturing_order', 'sales_order_id', 'Manufacturing Orders', readonly=True,
                                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)]})


class Product(models.Model):
    _inherit = 'famotain.product'

    production_cost = fields.Monetary('Production Cost', track_visibility='onchange')

    @api.multi
    def write(self, vals):
        product = super(Product, self).write(vals)
        # if vals.get('production_cost'):
        #     mo = self.env['mrp_famotain.manufacturing_order'].search([('product_id', '=', self.id), ('state', 'in', ['draft', 'approve', 'ready', 'on_progress'])])
        #     if mo:
        #         mo._compute_qty_production_cost()
        return product