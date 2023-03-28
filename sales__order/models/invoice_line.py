# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class InvoiceLine(models.Model):
    _name = 'sales__order.invoice_line'
    _description = 'Invoice Line'
    _order = 'id asc'

    invoice_id = fields.Many2one('sales__order.invoice', 'Invoice', required=True, readonly=True)
    description = fields.Char('Name', readonly=True)
    qty = fields.Integer('Qty', default=1, required=True, readonly=True)
    amount = fields.Monetary('Amount', readonly=True)
    total = fields.Monetary('Total', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    def prepare_vals_list(self, invoice_id=None, price_line_id=None):
        return {
            'invoice_id': invoice_id.id,
            'description': price_line_id.description,
            'qty': price_line_id.qty,
            'amount': price_line_id.amount,
            'total': price_line_id.debit - price_line_id.credit,
        }