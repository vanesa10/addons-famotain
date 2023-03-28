# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from ...famotain.models.encryption import encrypt

import logging
_logger = logging.getLogger(__name__)

INVOICE_LIST = [('down_payment', 'Down Payment'), ('clearance', 'Clearance')]


class Invoice(models.Model):
    _name = 'sales__order.invoice'
    _description = 'Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Invoice', default='New', readonly=True, index=True)
    invoice_type = fields.Selection(INVOICE_LIST, 'Invoice Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')

    invoice_line_ids = fields.One2many('sales__order.invoice_line', 'invoice_id', 'Invoice Lines', readonly=True)

    invoice_date = fields.Date('Invoice Date', default=lambda self: fields.Date.today(), readonly=True)
    due_date = fields.Date('Due Date', default=lambda self: date.today() + relativedelta(days=1), readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, track_visibility='onchange')
    payment_date = fields.Date('Payment Date', readonly=True)

    sales_order_id = fields.Many2one('sales__order.sales__order', 'Sales Order', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain=[('state', '!=', 'send'), ('state', '!=', 'cancel')])
    source_document = fields.Char('Source Document', related="sales_order_id.name", track_visibility='onchange')
    order_date = fields.Datetime('Order Date', related="sales_order_id.create_date")
    invoice_to = fields.Char('Invoice To', related="sales_order_id.customer_id.name", track_visibility='onchange')
    address = fields.Text('Address', related="sales_order_id.customer_id.address")
    phone = fields.Char('Phone', related="sales_order_id.customer_id.phone")

    amount = fields.Monetary('Amount', readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('paid', 'Paid'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes')
    encryption = fields.Char('Encryption', compute='_compute_encryption', store=True, readonly=True)

    paid_uid = fields.Many2one('res.users', 'Paid By', readonly=True)
    paid_date = fields.Datetime('Paid On', readonly=True)

    def create_price_line(self, price_line_id):
        vals = self.env['sales__order.invoice_line'].prepare_vals_list(self, price_line_id)
        return self.env['sales__order.invoice_line'].sudo().create(vals)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(ir_sequence_date=str(fields.Date.today())[:10]).next_by_code(
                    'sales__order.invoice'),
            })
        invoice = super(Invoice, self).create(vals_list)
        # Create invoice line:
        if invoice.sales_order_id:
            for rec in invoice.sales_order_id.price_line_ids:
                invoice.create_price_line(rec)
            msg = "{} ({}) - Rp. {:,} created".format(invoice.name, invoice.invoice_type, invoice.amount)
            invoice.sales_order_id.message_post(body=msg)
        return invoice

    @api.multi
    @api.model
    def unlink(self):
        # check dulu semua record draft or not
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("You can only delete a draft record"))
        # kalau semua record dh aman
        for rec in self:
            msg = "{} ({}) - Rp. {:,} deleted".format(rec.name, rec.invoice_type, rec.amount)
            for invoice_line in rec.invoice_line_ids:
                invoice_line.unlink()
            if rec.sales_order_id:
                rec.sales_order_id.message_post(body=msg)
        super(Invoice, self).unlink()

    @api.multi
    def write(self, vals):
        if 'amount' in vals.keys():
            initial_amount = vals['amount']
        invoice = super(Invoice, self).write(vals)
        if self.state in ['draft']:
            for invoice_line in self.invoice_line_ids:
                invoice_line.unlink()
            if self.sales_order_id:
                for rec in self.sales_order_id.price_line_ids:
                    self.create_price_line(rec)
                if 'amount' in vals.keys():
                    msg = "{} ({}) - Amount Changed Rp. {:,} to Rp. {:,}".format(
                        self.name, self.invoice_type, initial_amount, self.amount)
                    self.sales_order_id.message_post(body=msg)
        return invoice

    @api.multi
    @api.onchange('invoice_type', 'sales_order_id')
    def _onchange_amount(self):
        for rec in self:
            if rec.amount != 0:
                return
            if rec.invoice_type in ['down_payment']:
                #DONE : buat dinamis jadi 80% di setting
                rec.amount = self.env['famotain.settings'].sudo().search(
                    [('key_name', '=', 'down_payment'), ('active', '=', True)]
                    , limit=1).number_value / 100 * rec.sales_order_id.remaining
            elif rec.invoice_type in ['clearance']:
                rec.amount = rec.sales_order_id.remaining

    @api.multi
    @api.onchange('name')
    @api.depends('name')
    def _compute_encryption(self):
        for rec in self:
            rec.encryption = encrypt(rec.name)

    @api.one
    def pay_invoice(self, amount, payment_date):
        if self.state in ['open']:
            self.amount = amount
            self.payment_date = payment_date
            self.state = 'paid'
            self.paid_date = fields.Datetime.now()
            self.paid_uid = self.env.user.id
            # DONE: buat paid di sales order
            if self.sales_order_id:
                self.sales_order_id.compute_invoice()
                msg = "{} ({}) - Rp. {:,} paid".format(self.name, self.invoice_type, self.amount)
                self.sales_order_id.message_post(body=msg)
                # buat auto confirm kalau pay invoice apapun
                if self.sales_order_id.state == 'draft':
                    self.sales_order_id.action_confirm()
        else:
            raise UserError(_("You can only pay an open invoice"))

    @api.multi
    def auto_cancel_or_delete(self):
        for rec in self:
            if rec.state == 'draft':
                rec.unlink()
            elif rec.state == 'open':
                rec.action_cancel()

    @api.multi
    def action_validate(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'open'
            else:
                raise UserError(_("You can only validate draft invoice"))

    @api.multi
    def action_paid(self):
        #DONE: dibuat wizard isi amount sama payment date
        for rec in self:
            if rec.state in ['open']:
                wizard_form = self.env.ref('sales__order.pay_invoice_wizard_form', False)
                view_id = self.env['sales__order.pay_invoice_wizard']
                new = view_id.create({
                    'amount': rec.amount,
                    'payment_date': rec.invoice_date
                })
                return {
                    'name': 'Pay Invoice',
                    'type': 'ir.actions.act_window',
                    'res_model': 'sales__order.pay_invoice_wizard',
                    'res_id': new.id,
                    'view_id': wizard_form.id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new'
                }
            else:
                raise UserError(_("You can only pay an open invoice"))

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['open', 'draft']:
                rec.state = 'cancel'
                msg = "{} ({}) - Rp. {:,} cancelled".format(self.name, self.invoice_type, self.amount)
                self.sales_order_id.message_post(body=msg)
            else:
                raise UserError(_("You can only cancel an open/draft invoice"))

    @api.multi
    def action_force_cancel(self):
        for rec in self:
            if rec.state in ['open', 'draft']:
                rec.state = 'cancel'
                msg = "{} ({}) - Rp. {:,} cancelled (forced)".format(self.name, self.invoice_type, self.amount)
                self.sales_order_id.message_post(body=msg)

    @api.multi
    def print_invoice(self):
        return {
            'name': 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '%s/print_invoice/%s' % (self.env['ir.config_parameter'].sudo().get_param('web.base.url'), self.encryption)
        }

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('sales__order.invoice_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Form',
            'res_model': 'sales__order.invoice',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class PayInvoiceWizard(models.TransientModel):
    _name = 'sales__order.pay_invoice_wizard'
    _description = "Wizard: Pay invoice, choose payment date and fill amount"

    def _default_session(self):
        return self.env['sales__order.invoice'].browse(self._context.get('active_id'))

    payment_date = fields.Date('Payment Date', required=True)
    amount = fields.Monetary('Amount', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    def action_pay(self):
        self._default_session().pay_invoice(self.amount, self.payment_date)


class ReportInvoice(models.AbstractModel):
    _name = 'report.sales__order.report_sales__order_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'sales__order.invoice',
            'docs': self.env['sales__order.invoice'].browse(docids),
            'report_type': data.get('report_type') if data else '',
            'tnc': self.env['famotain.settings'].sudo().search(
                [('key_name', '=', 'terms_conditions'), ('active', '=', True)], limit=1).text_value
        }