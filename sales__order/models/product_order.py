# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from ...famotain.models.product import PRODUCT_TYPE_LIST
from ...tools import image as tools
import logging
_logger = logging.getLogger(__name__)


class ProductOrder(models.Model):
    _name = 'sales__order.product_order'
    _description = 'Product Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline, sequence'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('web', 'static/src/img', 'placeholder.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    name = fields.Char('Product Order', default='New', readonly=True, tracking=True, index=True)
    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', readonly=True, required=True)
    price_line_id = fields.Many2one('sales__order.price_line', 'Price Line', readonly=True)

    deadline = fields.Date('Deadline', readonly=True, compute='_compute_deadline', store=True)
    product_type = fields.Selection(PRODUCT_TYPE_LIST, 'Product Type', readonly=True, required=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)]})
    product_id = fields.Many2one('famotain.product', 'Product', required=True, readonly=True,
                                 domain="[('active', '=', True), ('product_type', '=', product_type)]",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)]},
                                 track_visibility='onchange')
    product_price = fields.Monetary('Product Price', related="product_id.price")
    price = fields.Monetary('Price', related="price_line_id.amount")
    # product_description = fields.Char('Description', related="product_id.description")

    is_customized = fields.Boolean('Custom', track_visibility='onchange', readonly=True, default=False, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    qty = fields.Integer('Qty', default=1, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    fabric_color = fields.Char('Color Notes', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    # ribbon_color = fields.Char('Ribbon Color', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    design_image = fields.Binary('Design Image', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    design_image_small = fields.Binary("Small-sized Design Image", attachment=True, readonly=True)
    # design_image_2 = fields.Binary('Design Image 2', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    # design_image_2_small = fields.Binary("Small-sized Design Image 2", attachment=True, readonly=True)
    # design_image_3 = fields.Binary('Design Image 3', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    # design_image_3_small = fields.Binary("Small-sized Design Image 3", attachment=True, readonly=True)

    total = fields.Monetary('Total', readonly=True, compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('approve','Approved'), ('on_progress', 'On Progress'), ('done', 'Done'), ('sent', 'Sent'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    product_description = fields.Char('Product Description', compute='_compute_product_description', store=True)
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'approve': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    sequence = fields.Integer(required=True, default=10)
    approve_uid = fields.Many2one('res.users', 'Approved By', readonly=True)
    approve_date = fields.Datetime('Approved On', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled On', readonly=True)
    send_uid = fields.Many2one('res.users', 'Send By', readonly=True)
    send_date = fields.Datetime('Send On', readonly=True)

    def prepare_vals_list(self, sales_order_id, product_id, qty=0, fabric_color=''):
        return {
            # 'product_type': product_type,
            'sales_order_id': sales_order_id,
            'qty': qty,
            'product_id': product_id.id,
            'fabric_color': fabric_color,
            'product_type': product_id.product_type
            # 'deadline': sales_order_id.deadline if sales_order_id else None
        }

    def create_price_line(self):
        vals = self.env['sales__order.price_line'].prepare_vals_list(self)
        new_rec = self.env['sales__order.price_line'].sudo().create(vals)
        return new_rec

    def set_empty_product_type(self):
        # product_orders = self.env['sales__order.product_order'].sudo().search([('product_type', 'in', ['label', False])])
        product_orders = self.env['sales__order.product_order'].sudo().search([])
        for po in product_orders:
            if po.product_type in ['label', False] or po.product_type != po.product_id.product_type:
                po.write({
                    'product_type': po.product_id.product_type
                })

    @api.model
    def create(self, vals):
        if vals.get('name') != 'New':
            vals.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('sales__order.product_order_{}'.format(vals.get('product_type') if vals.get('product_type') else 'product')),
            })
        image = False
        if 'design_image' in vals.keys() and vals['design_image']:
            vals.update({
                'design_image_small': tools.image_resize_image_medium(vals['design_image'].encode('ascii'))
            })
            image = True
        # if 'design_image_2' in vals.keys() and vals['design_image_2']:
        #     vals.update({
        #         'design_image_2_small': tools.image_resize_image_medium(vals['design_image_2'].encode('ascii'))
        #     })
        # if 'design_image_3' in vals.keys() and vals['design_image_3']:
        #     vals.update({
        #         'design_image_3_small': tools.image_resize_image_medium(vals['design_image_3'].encode('ascii'))
        #     })
        product_order = super(ProductOrder, self).create(vals)
        product_order.write({
            'deadline': product_order.sales_order_id.deadline,
            'product_type': product_order.product_id.product_type
        })
        # product_order.name = """{}/{}""".format(product_order.qty, product_order.product_id.code)
        price_line = product_order.create_price_line()
        product_order.price_line_id = price_line.id
        # create product order kalo sales order udh confirm/approve/on progress berarti product order state auto confirm
        if product_order.sales_order_id.state in ['confirm', 'approve', 'on_progress']:
            product_order.action_confirm()
        if image and product_order.product_id.product_type in ['product', 'addons', 'charge'] and not product_order.sales_order_id.image:
            product_order.sales_order_id.image = vals['design_image']
        msg = "{}pcs {} Rp. {:,} product order created".format(product_order.qty, product_order.product_id.display_name, product_order.total)
        product_order.sales_order_id.message_post(body=msg)
        return product_order

    @api.multi
    def write(self, vals):
        if 'design_image' in vals.keys() and vals['design_image']:
            vals.update({
                'design_image_small': tools.image_resize_image_medium(vals['design_image'].encode('ascii'))
            })
            if self.product_id.product_type in ['product', 'addons', 'charge'] and not self.sales_order_id.image:
                self.sales_order_id.image = vals['design_image']
        # if 'design_image_2' in vals.keys() and vals['design_image_2']:
        #     vals.update({
        #         'design_image_2_small': tools.image_resize_image_medium(vals['design_image_2'].encode('ascii'))
        #     })
        # if 'design_image_3' in vals.keys() and vals['design_image_3']:
        #     vals.update({
        #         'design_image_3_small': tools.image_resize_image_medium(vals['design_image_3'].encode('ascii'))
        #     })
        initial_qty = self.qty
        initial_product_id = self.product_id
        initial_total = self.total
        initial_fabric_color = self.fabric_color
        product = self.product_id
        if 'product_id' in vals.keys():
            product = self.env['famotain.product'].browse(vals['product_id'])[0]
        vals.update({'product_type': product.product_type})
        test = self.env['sales__order.price_line'].browse(self.price_line_id.id)
        for t in test:
            t.qty = vals['qty'] if 'qty' in vals.keys() else self.qty
            if 'product_id' in vals.keys():
                t.amount = product.price
                t.debit = t.qty * product.price
                t.description = product.name
        product_order = super(ProductOrder, self).write(vals)
        if any(c in vals.keys() for c in ('qty', 'product_id')):
            self.product_id.compute_product_order_count()
            if 'product_id' in vals.keys():
                initial_product_id.compute_product_order_count()
            msg = "{}pcs {} Rp. {:,} product order changed to {}pcs {} Rp. {:,}".format(
                initial_qty, initial_product_id.display_name, initial_total, self.qty, self.product_id.display_name, self.total)
            self.sales_order_id.message_post(body=msg)
        if 'fabric_color' in vals.keys():
            msg = "{} description {} changed to {}".format(
                initial_product_id.display_name, initial_fabric_color, self.fabric_color)
            self.sales_order_id.message_post(body=msg)
        return product_order

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft', 'confirm', 'approve']:
                if rec.state != 'draft':
                    rec.product_id.change_open_order_count(-1)
                    rec.product_id.change_fix_order_qty(rec.qty * -1)
                if rec.price_line_id:
                    rec.price_line_id.product_order_id = None
                    rec.price_line_id.unlink()
                # kalau ada mo di delete juga monya, kecuali kalau charge.
                msg = "{}pcs {} Rp. {:,} product order deleted".format(rec.qty, rec.product_id.display_name,
                                                                         rec.total)
                rec.sales_order_id.message_post(body=msg)
                return super(ProductOrder, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.onchange('product_type')
    def onchange_product_type(self):
        return {'domain': {'product_id': [('product_type', '=', self.product_type)]}}

    # @api.multi
    # @api.onchange('product_id', 'qty')
    # @api.depends('product_id', 'qty')
    # def _compute_name(self):
    #     for rec in self:
    #         rec.name = """{}/{}""".format(rec.qty, rec.product_id.name)

    @api.multi
    @api.onchange('product_id', 'qty')
    @api.depends('product_id', 'qty')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.product_id.price * rec.qty

    @api.multi
    @api.onchange('product_id')
    @api.depends('product_id')
    def _compute_product_description(self):
        for rec in self:
            rec.product_description = rec.product_id.description

    @api.multi
    @api.onchange('sales_order_id')
    @api.depends('sales_order_id')
    def _compute_deadline(self):
        for rec in self:
            rec.deadline = rec.sales_order_id.deadline

    @api.multi
    def action_confirm(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'confirm'
                rec.product_id.change_open_order_count(1)
                rec.product_id.change_fix_order_qty(rec.qty)

    @api.multi
    def action_approve(self):
        for rec in self:
            if rec.state in ['confirm']:
                rec.price_line_id.action_confirm()
                rec.state = 'approve'
                rec.approve_date = fields.Datetime.now()
                rec.approve_uid = self.env.user.id

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
                # rec.product_id.compute_product_order_count()

    @api.multi
    def action_force_cancel(self):
        for rec in self:
            if rec.state not in ['cancel', 'sent']:
                if rec.state != 'draft':
                    if rec.state != 'done':
                        rec.product_id.change_open_order_count(-1)
                    rec.product_id.change_fix_order_qty(rec.qty * -1)
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
                # rec.product_id.compute_product_order_count()

    @api.multi
    def action_on_progress(self):
        for rec in self:
            if rec.state in ['confirm', 'approve']:
                rec.state = 'on_progress'

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.state in ['on_progress']:
                rec.state = 'done'
                rec.product_id.change_open_order_count(-1)

    @api.multi
    def action_send(self):
        for rec in self:
            if rec.state in ['confirm', 'approve', 'on_progress', 'done']:
                if rec.state != 'done':
                    rec.product_id.change_open_order_count(-1)
                rec.state = 'sent'
                rec.send_date = fields.Datetime.now()
                rec.send_uid = self.env.user.id

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('sales__order.product_order_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Product Order Form',
            'res_model': 'sales__order.product_order',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def open_sales_order_record(self):
        rec_id = self.sales_order_id.id
        form_id = self.env.ref('sales__order.sales__order_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order Form',
            'res_model': 'sales__order.sales__order',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class Product(models.Model):
    _inherit = 'famotain.product'

    product_order_ids = fields.One2many('sales__order.product_order', 'product_id', string='Product Orders')
    open_order_count = fields.Integer('Open Order', compute='_compute_product_order_count', store=True)
    fix_order_qty = fields.Integer('Fix Order Qty', compute='_compute_product_order_count', store=True)

    @api.multi
    @api.onchange('product_order_ids')
    @api.depends('product_order_ids')
    def _compute_product_order_count(self):
        for rec in self:
            if rec.product_order_ids:
                order_count = 0
                order_qty = 0
                for r in rec.product_order_ids:
                    if r.state not in ['draft', 'cancel']:
                        order_qty += r.qty
                        if r.state not in ['sent', 'done']:
                            order_count += 1
                rec.open_order_count = order_count
                rec.fix_order_qty = order_qty

    @api.one
    def change_open_order_count(self, count):
        order_count = self.open_order_count + count
        self.write({
            'open_order_count': order_count,
        })

    @api.one
    def change_fix_order_qty(self, qty):
        order_qty = self.fix_order_qty + qty
        self.write({
            'fix_order_qty': order_qty,
        })

    @api.one
    def compute_product_order_count(self):
        order_count = 0
        order_qty = 0
        for r in self.product_order_ids:
            if r.state not in ['draft', 'cancel']:
                order_qty += r.qty
                if r.state not in ['sent', 'done']:
                        order_count += 1
        self.write({
            'open_order_count': order_count,
            'fix_order_qty': order_qty
        })
