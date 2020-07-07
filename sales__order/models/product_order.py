# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import tools
from odoo.modules.module import get_module_resource
from ...famotain.models.product import PRODUCT_TYPE_LIST
import logging
_logger = logging.getLogger(__name__)


class ProductOrder(models.Model):
    _name = 'sales__order.product_order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id asc'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('web', 'static/src/img', 'placeholder.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', readonly=True, required=True)
    price_line_id = fields.Many2one('sales__order.price_line', 'Price Line', readonly=True)

    product_type = fields.Selection(PRODUCT_TYPE_LIST, 'Product Type', readonly=True)
    product_id = fields.Many2one('famotain.product', 'Product', required=True, readonly=True,
                                 domain=[('active', '=', True)],
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 track_visibility='onchange')
    qty = fields.Integer('Qty', default=1, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    fabric_color = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    ribbon_color = fields.Char('Ribbon Color', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'on_progress': [('readonly', False)]}, track_visibility='onchange')
    design_image = fields.Binary('Design Image', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    design_image_2 = fields.Binary('Design Image 2', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    design_image_3 = fields.Binary('Design Image 3', attachment=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')

    price = fields.Monetary('Price', readonly=True, compute='_compute_price', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('on_progress', 'On Progress'), ('sent', 'Sent'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed On', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled On', readonly=True)
    send_uid = fields.Many2one('res.users', 'Send By', readonly=True)
    send_date = fields.Datetime('Send On', readonly=True)

    def prepare_vals_list(self, product_type=None, sales_order_id=None, qty=0, product_id=None, fabric_color=''):
        return {
            'product_type': product_type,
            'sales_order_id': sales_order_id,
            'qty': qty,
            'product_id': product_id,
            'fabric_color': fabric_color
        }

    def create_price_line(self):
        vals = self.env['sales__order.price_line'].prepare_vals_list(self)
        new_rec = self.env['sales__order.price_line'].sudo().create(vals)
        return new_rec

    @api.model
    def create(self, vals_list):
        tools.image_resize_images(vals_list)
        product_order = super(ProductOrder, self).create(vals_list)
        price_line = product_order.create_price_line()
        product_order.price_line_id = price_line.id
        msg = "{}pcs {} Rp. {:,} product order created".format(product_order.qty, product_order.product_id.display_name, product_order.price)
        product_order.sales_order_id.message_post(body=msg)
        return product_order

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        initial_qty = self.qty
        initial_product_id = self.product_id
        initial_price = self.price
        test = self.env['sales__order.price_line'].browse(self.price_line_id.id)
        for t in test:
            t.qty = vals['qty'] if 'qty' in vals.keys() else self.qty
            if 'product_id' in vals.keys():
                product = self.env['famotain.product'].browse(vals['product_id'])[0]
                t.amount = product.price
                t.debit = t.qty * product.price
                t.description = product.name
        product_order = super(ProductOrder, self).write(vals)
        if any(c in vals.keys() for c in ('qty', 'product_id')):
            msg = "{}pcs {} Rp. {:,} product order changed to {}pcs {} Rp. {:,}".format(
                initial_qty, initial_product_id.display_name, initial_price, self.qty, self.product_id.display_name, self.price)
            self.sales_order_id.message_post(body=msg)
        return product_order

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                if rec.price_line_id:
                    rec.price_line_id.product_order_id = None
                    rec.price_line_id.unlink()
                msg = "{}pcs {} Rp. {:,} product order deleted".format(rec.qty, rec.product_id.display_name,
                                                                         rec.price)
                rec.sales_order_id.message_post(body=msg)
                return super(ProductOrder, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.onchange('product_type')
    def onchange_product_type(self):
        return {'domain': {'product_id': [('product_type', '=', self.product_type)]}}

    @api.multi
    @api.onchange('product_id', 'qty')
    @api.depends('product_id', 'qty')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.product_id.price * rec.qty

    @api.multi
    def action_confirm(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.price_line_id.action_confirm()
                rec.state = 'confirm'
                rec.confirm_date = fields.Datetime.now()
                rec.confirm_uid = self.env.user.id

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['draft', 'confirm']:
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
            else:
                raise UserError(_("You can't cancel this sales order"))

    @api.multi
    def action_send(self):
        for rec in self:
            if rec.state in ['confirm', 'on_progress']:
                rec.state = 'sent'
                rec.send_date = fields.Datetime.now()
                rec.send_uid = self.env.user.id
                rec.design_image = tools.image_resize_image_big(rec.design_image)
                rec.design_image_2 = tools.image_resize_image_big(rec.design_image_2)
                rec.design_image_3 = tools.image_resize_image_big(rec.design_image_3)
            else:
                raise UserError(_("You can only send a confirmed sales order"))

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
