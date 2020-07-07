# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

PRICES_LIST = [('product', 'Product'), ('charge', 'Charge'), ('discount', 'Discount'), ('shipment', 'Shipment')]


class PriceLine(models.Model):
    _name = 'sales__order.price_line'
    _order = 'id asc'

    prices_type = fields.Selection(PRICES_LIST, 'Prices Type', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Char('Name', store=True, compute="_compute_description", readonly=True)

    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', required=True, readonly=True)
    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', readonly=True)

    qty = fields.Integer('Qty', default=1, required=True, readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Monetary('Amount', readonly=True, states={'draft': [('readonly', False)]})
    debit = fields.Monetary('Debit', store=True, compute="_compute_debit_credit", readonly=True)
    credit = fields.Monetary('Credit', store=True, compute="_compute_debit_credit", readonly=True)
    balance = fields.Monetary('Balance', store=True, compute="_compute_debit_credit", readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], 'State', required=True, default='draft', readonly=True)
    notes = fields.Text('Notes')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed On', readonly=True)

    def prepare_vals_list(self, product_order_id=None, sales_order_id=None, amount=None):
        if product_order_id:
            return {
                'sales_order_id': product_order_id.sales_order_id.id,
                'product_order_id': product_order_id.id,
                'description': product_order_id.product_id.display_name,
                'qty': product_order_id.qty,
                'amount': product_order_id.product_id.price,
                'debit': product_order_id.qty * product_order_id.product_id.price,
                'prices_type': 'product'
            }
        if sales_order_id:
            return {
                'sales_order_id': sales_order_id.id,
                'description': 'Charge',
                'qty': 1,
                'amount': amount,
                'debit': amount,
                'prices_type': 'charge'
            }

    @api.model
    def create(self, vals_list):
        price_line = super(PriceLine, self).create(vals_list)
        if price_line.prices_type not in 'product':
            msg = "{} price Rp. {:,} created".format(price_line.description, price_line.debit - price_line.credit)
            price_line.sales_order_id.message_post(body=msg)
        return price_line

    @api.multi
    def write(self, vals):
        price_line = super(PriceLine, self).write(vals)
        self.sales_order_id.compute_total_price()
        return price_line

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                if rec.product_order_id:
                    rec.product_order_id.price_line_id = None
                    rec.product_order_id.unlink()
                msg = "{} Price Rp. {:,} deleted".format(rec.description, rec.debit - rec.credit)
                rec.sales_order_id.message_post(body=msg)
                return super(PriceLine, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.multi
    @api.onchange('prices_type')
    @api.depends('prices_type')
    def _compute_description(self):
        for rec in self:
            rec.description = str(rec.prices_type).title() if rec.prices_type not in ['product'] else rec.product_order_id.product_id.display_name

    @api.multi
    @api.onchange('qty', 'amount', 'prices_type')
    @api.depends('qty', 'amount', 'prices_type')
    def _compute_debit_credit(self):
        for rec in self:
            if rec.prices_type not in ['discount']:
                rec.debit = rec.qty * rec.amount
            else:
                rec.credit = rec.qty * rec.amount
            rec.balance = rec.debit - rec.credit

    @api.multi
    def action_confirm(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'confirm'
                rec.confirm_date = fields.Datetime.now()
                rec.confirm_uid = self.env.user.id
