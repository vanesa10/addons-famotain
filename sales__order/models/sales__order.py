# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import tools
from ...famotain.models.telegram_bot import send_telegram_message
from ...famotain.models.encryption import encrypt
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

# PACKAGING = {
#     '-': '',
#     'plastik': 'Plastik',
#     'tile': 'Tile',
#     'plastik_jinjing': 'Plastik Jinjing',
#     'thank_card': 'Thankyou Card'
# }
# PACKAGING_LIST = [('-', 'No Packaging'), ('plastik', 'Plastik'), ('tile', 'Tile'), ('plastik_jinjing', 'Plastik Jinjing'), ('thank_card', 'Thank you card saja')]
PACKING_LIST = [('-', 'No Pack'), ('pack', 'Packing'), ('sendiri', 'Packing Sendiri')]


class SalesOrder(models.Model):
    _name = 'sales__order.sales__order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    image = fields.Binary("Image", attachment=True, readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    image_medium = fields.Binary("Medium-sized Image", attachment=True, readonly=True)
    image_small = fields.Binary("Small-sized Image", attachment=True, readonly=True)

    name = fields.Char('Sales Order', default='New', readonly=True, index=True, tracking=True)
    deadline = fields.Date('Deadline', default=lambda self: fields.Date.today(), readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    event_date = fields.Date('Event Date', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')

    customer_id = fields.Many2one('sales__order.customer', 'Customer', required=True, domain=[('active', '=', True)], readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    city = fields.Char('City', related="customer_id.city")
    phone = fields.Char('Phone', related="customer_id.phone")
    address = fields.Text('Address', related="customer_id.address")

    product_order_ids = fields.One2many('sales__order.product_order', 'sales_order_id', 'Product Orders', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    price_line_ids = fields.One2many('sales__order.price_line', 'sales_order_id', 'Prices', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    invoice_ids = fields.One2many('sales__order.invoice', 'sales_order_id', 'Invoices', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})

    qty_total = fields.Integer('Qty Total', readonly=False, required=True, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    product = fields.Char('Product', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    add_ons = fields.Char('Add Ons', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    theme = fields.Char('Theme', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    additional_text = fields.Char('Additional Text', help="Penulisan pada design tas", readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    thanks_card_writing = fields.Char('Thanks Card Writing', help="Penulisan pada thank you card", readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    custom_name = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Custom Name', default='no', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    label = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Label', default='no', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')

    packaging_id = fields.Many2one('famotain.product', 'Packaging', domain=[('active', '=', True), ('product_type', '=', 'package')], readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    packing = fields.Selection(PACKING_LIST, 'Packing', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange', default='-')

    custom_request = fields.Text('Custom Request', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')
    customer_notes = fields.Text('Customer Notes', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange')

    courier_id = fields.Many2one('famotain.courier_shipment', 'Courier', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    qty_packaging = fields.Integer('Qty Packaging', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    packaging_type = fields.Selection([('kardus', 'Kardus'), ('karung', 'Karung'), ('plastik', 'Plastik')], 'Packaging Type', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_of_shipment = fields.Date('Date of Shipment', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})
    shipment_receipt_number = fields.Char('Shipment Receipt Number', readonly=False, states={'send': [('readonly', True)], 'cancel': [('readonly', True)]})

    total_price = fields.Monetary('Total Amount', compute='_compute_total_price', readonly=True, store=True, track_visibility='onchange')
    paid = fields.Monetary('Paid', readonly=True, track_visibility='onchange')
    remaining = fields.Monetary('Remaining', compute='_compute_remaining', readonly=True, store=True, track_visibility='onchange')

    url = fields.Char('URL', compute='_compute_url', store=True, readonly=True)
    encryption = fields.Char('Encryption', compute='_compute_url', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('on_progress', 'On Progress'),
        ('done', 'Done'),
        ('send', 'Sent'),
        ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    notes = fields.Text('Internal Notes')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed On', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved By', readonly=True)
    approve_date = fields.Datetime('Approved On', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled On', readonly=True)
    send_uid = fields.Many2one('res.users', 'Sent By', readonly=True)
    send_date = fields.Datetime('Sent On', readonly=True)

    def reset_sequence(self):
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'F%(range_year)s%(range_month)s%(range_day)s')], limit=1)
        sequences.write({'number_next_actual': 1})
        sequences = self.env['ir.sequence'].search([('prefix', '=', 'INV/%(range_year)s%(range_month)s%(range_day)s/')], limit=1)
        sequences.write({'number_next_actual': 1})

    def deadline_notification(self):
        # 1. Deadline hari ini blm dikirim
        # 2. Deadline minggu ini blm dikirim
        # 3. URGENT: deadline minggu ini blm di proses
        sales_order = self.env['sales__order.sales__order'].search([
            ('deadline', '>=', fields.Date.today()), ('deadline', '<', fields.Date.today() + relativedelta(days=10)),
            ('state', '!=', 'cancel')
        ], order="deadline")
        msg = {'today': "", 'urgent': "", 'this_week': "", 'late': ""}
        for rec in sales_order:
            msg_data = {'url': rec.url, 'deadline': rec.deadline.strftime('%d-%b-%Y'), 'name': rec.name}
            if rec.deadline == fields.Date.today():
                msg['today'] += """<a href="{url}">{deadline} - {name}</a>\n""".format(**msg_data)
            elif rec.state not in ['send', 'on_progress', 'done']:
                msg['urgent'] += """<a href="{url}">{deadline} - {name}</a>\n""".format(**msg_data)
            else:
                msg['this_week'] += """<a href="{url}">{deadline} - {name}</a>\n""".format(**msg_data)
        # 4. TERLAMBAT
        sales_order = self.env['sales__order.sales__order'].search([
            ('deadline', '<', fields.Date.today()), ('state', '!=', 'cancel')], order="deadline")
        for rec in sales_order:
            msg_data = {'url': rec.url, 'deadline': rec.deadline.strftime('%d-%b-%Y'), 'name': rec.name}
            msg['late'] += """<a href="{url}">{deadline} - {name}</a>\n""".format(**msg_data)
        notif = """
<b>Deadline Today:</b>
========================
{today}
<b>This Week:</b>
========================
{this_week}
<b>!URGENT!:</b>
========================
{urgent}
<b>!LATE!:</b>
========================
{late}
""".format(**msg)
        send_telegram_message(notif)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('sales__order.sales__order'),
            })
        tools.image_resize_images(vals_list)

        sales_order = super(SalesOrder, self).create(vals_list)
        # DONE: auto create product order with same name as product
        product = self.env['famotain.product'].search(
            [('name', '=ilike', sales_order.product), ('product_type', '=', 'product'), ('active', '=', True)], limit=1)
        if product:
            product_order_vals = self.env['sales__order.product_order'].prepare_vals_list(
                product_type='product', sales_order_id=sales_order.id, qty=sales_order.qty_total, product_id=product.id)
            self.env['sales__order.product_order'].sudo().create(product_order_vals)

        if sales_order.packaging_id:
            package_vals = self.env['sales__order.product_order'].prepare_vals_list(
                product_type='package', sales_order_id=sales_order.id, qty=sales_order.qty_total,
                product_id=sales_order.packaging_id.id, fabric_color=sales_order.packing)
            self.env['sales__order.product_order'].sudo().create(package_vals)

        # create product order label if label = 'yes'
        if sales_order.label == 'yes':
            # DONE: search product yg label -> prepare vals list product order -> create product order
            product_label = self.env['famotain.product'].search([('product_type', '=', 'label'), ('active', '=', True)],
                                                                limit=1)
            product_order_vals = self.env['sales__order.product_order'].prepare_vals_list(
                product_type='label', sales_order_id=sales_order.id, qty=sales_order.qty_total,
                product_id=product_label.id)
            self.env['sales__order.product_order'].sudo().create(product_order_vals)

        # create charge price line if qty < settings
        self.env['famotain.settings'].search([('key_name', '=', 'charge_qty_1'), ('active', '=', True)], limit=1)
        charge = 0
        if sales_order.qty_total < self.env['famotain.settings'].search(
                [('key_name', '=', 'charge_qty_1'), ('active', '=', True)], limit=1).number_value:
            charge = self.env['famotain.settings'].search(
                [('key_name', '=', 'charge_amount_1'), ('active', '=', True)], limit=1).number_value
        elif sales_order.qty_total < self.env['famotain.settings'].search(
                [('key_name', '=', 'charge_qty_2'), ('active', '=', True)], limit=1).number_value:
            charge = self.env['famotain.settings'].search(
                [('key_name', '=', 'charge_amount_2'), ('active', '=', True)], limit=1).number_value
        if charge > 0:
            sales_order._add_price_line(charge)

        msg_data = {
            'name': sales_order.name,
            'customer_name': sales_order.customer_id.name,
            'customer_phone': sales_order.phone,
            'city': sales_order.customer_id.city,
            'deadline': sales_order.deadline.strftime('%d-%b-%Y'),
            'qty_total': sales_order.qty_total,
            'product': sales_order.product,
            'theme': sales_order.theme,
            # 'packaging': sales_order.packaging_id.name if sales_order.packaging_id else '',
            # 'packing': sales_order.packing,
            'url': sales_order.url,
            # 'custom_request': sales_order.custom_request if sales_order.custom_request else '-',
            # 'notes': sales_order.customer_notes if sales_order.customer_notes else '-'
        }
        msg = """
<a href="{url}"><b>{name} CREATED</b></a>
========================
Name : {customer_name}
Phone : {customer_phone}
City: {city}
========================
Deadline : {deadline}
{qty_total}pcs - {product} - {theme}""".format(**msg_data)
        send_telegram_message(msg)
        return sales_order

    def _add_price_line(self, amount):
        vals = self.env['sales__order.price_line'].prepare_vals_list(sales_order_id=self, amount=amount)
        new_rec = self.env['sales__order.price_line'].create(vals)
        return new_rec

    def prepare_vals_list(self, customer_id, qty_total, deadline=None, event_date=None, product='', theme='',
                          packaging_id=None, packing='', label='no', add_ons='', custom_name='no', additional_text='',
                          thanks_card_writing='', custom_request='', notes=''):

        return {
            'customer_id': customer_id, 'deadline': deadline, 'event_date': event_date, 'qty_total': int(qty_total),
            'packaging_id': packaging_id, 'packing': packing, 'label': label, 'custom_name': custom_name,
            'additional_text': additional_text, 'thanks_card_writing': thanks_card_writing,
            'custom_request': custom_request, 'customer_notes': notes, 'product': product, 'theme': theme, 'add_ons': add_ons
        }

    @api.multi
    def write_from_web(self, vals):
        for rec in self:
            diff_qty = rec.qty_total if vals['qty_total'] != rec.qty_total else 0
            diff_packing = True if vals['packing'] != rec.packing else False
            rec.sudo().write(vals)
            product = self.env['famotain.product'].search(
                [('name', '=ilike', rec.product), ('product_type', '=', 'product'), ('active', '=', True)],
                limit=1)
            label = False
            if rec.label == 'yes':
                label = self.env['famotain.product'].search(
                    [('product_type', '=', 'label'), ('active', '=', True)],
                    limit=1)
            packaging = False
            if rec.packaging_id:
                packaging = self.env['famotain.product'].browse(rec.packaging_id.id)
            product_rec = False
            package_rec = False
            label_rec = False
            for product_order in rec.product_order_ids:
                product_order_vals = {}
                product_rec = product_order if product_order.product_type == 'product' else product_rec
                package_rec = product_order if product_order.product_type == 'package' else package_rec
                label_rec = product_order if product_order.product_type == 'label' else label_rec
                if product and product_order.product_type == 'product' and product.id != product_order.product_id.id:
                    product_order_vals.update({'product_id': product.id})
                if packaging and product_order.product_type == 'package' and packaging.id != product_order.product_id.id:
                    product_order_vals.update({'product_id': packaging.id})
                if product_order.product_type == 'package' and diff_packing:
                    product_order_vals.update({'fabric_color': rec.packing})
                if product_order.qty == diff_qty:
                    product_order_vals.update({'qty': rec.qty_total})
                if product_order_vals:
                    product_order.sudo().write(product_order_vals)
            if product and not product_rec:
                product_order_vals = self.env['sales__order.product_order'].prepare_vals_list(
                    product_type='product', sales_order_id=rec.id, qty=rec.qty_total,
                    product_id=product.id)
                self.env['sales__order.product_order'].sudo().create(product_order_vals)
            if product_rec and not product:
                product_rec.sudo().unlink()
            if packaging and not package_rec:
                product_order_vals = self.env['sales__order.product_order'].prepare_vals_list(
                    product_type='package', sales_order_id=rec.id, qty=rec.qty_total,
                    product_id=packaging.id, fabric_color=rec.packing)
                self.env['sales__order.product_order'].sudo().create(product_order_vals)
            if package_rec and not packaging:
                package_rec.sudo().unlink()
            if label and not label_rec:
                product_order_vals = self.env['sales__order.product_order'].prepare_vals_list(
                    product_type='label', sales_order_id=rec.id, qty=rec.qty_total,
                    product_id=label.id)
                self.env['sales__order.product_order'].sudo().create(product_order_vals)
            if label_rec and not label:
                label_rec.sudo().unlink()

            self.env['famotain.settings'].search([('key_name', '=', 'charge_qty_1'), ('active', '=', True)], limit=1)
            charge = 0
            if rec.qty_total < self.env['famotain.settings'].search(
                    [('key_name', '=', 'charge_qty_1'), ('active', '=', True)], limit=1).number_value:
                charge = self.env['famotain.settings'].search(
                    [('key_name', '=', 'charge_amount_1'), ('active', '=', True)], limit=1).number_value
            elif rec.qty_total < self.env['famotain.settings'].search(
                    [('key_name', '=', 'charge_qty_2'), ('active', '=', True)], limit=1).number_value:
                charge = self.env['famotain.settings'].search(
                    [('key_name', '=', 'charge_amount_2'), ('active', '=', True)], limit=1).number_value
            rec_charge = False
            for price_line in rec.price_line_ids:
                if price_line.prices_type == 'charge':
                    rec_charge = price_line
                    if price_line.amount != charge and charge > 0:
                        rec_charge.sudo().write({
                            'amount': charge,
                            'debit': charge,
                        })
                    break
            if charge > 0 and not rec_charge:
                rec._add_price_line(charge)
            if charge == 0 and rec_charge:
                rec_charge.sudo().unlink()

            msg_data = {
                'name': rec.name,
                # 'customer_name': rec.customer_id.name,
                # 'customer_phone': rec.phone,
                # 'city': rec.customer_id.city,
                # 'deadline': rec.deadline.strftime('%d-%b-%Y'),
                'qty_total': rec.qty_total,
                'product': rec.product,
                'theme': rec.theme,
                # 'packaging': rec.packaging_id.name,
                # 'packing': rec.packing,
                'url': rec.url,
                # 'custom_request': rec.custom_request if rec.custom_request else '-',
                # 'notes': rec.customer_notes if rec.customer_notes else '-'
            }
            msg = """
<a href="{url}"><b>{name} EDITED</b></a>
========================
{qty_total}pcs - {product} - {theme}
""".format(**msg_data)
        send_telegram_message(msg)
        return True

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(SalesOrder, self).write(vals)

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                for product_order in rec.product_order_ids:
                    product_order.unlink()
                for price_line in rec.price_line_ids:
                    price_line.unlink()
                for invoice in rec.invoice_ids:
                    invoice.unlink()
                super(SalesOrder, self).unlink()
            else:
                raise UserError(_("You can only delete a draft record"))

    @api.multi
    @api.onchange('packaging_id')
    def _onchange_packing(self):
        for rec in self:
            if not rec.packaging_id:
                rec.packing = '-'
            else:
                rec.packing = 'pack'

    @api.multi
    @api.onchange('product_order_ids')
    @api.depends('product_order_ids')
    def _compute_image(self):
        for rec in self:
            if not rec.image:
                for product in rec.product_order_ids:
                    if product.design_image:
                        rec.image = product.design_image
                        break

    @api.multi
    @api.onchange('name')
    @api.depends('name')
    def _compute_url(self):
        for rec in self:
            rec.encryption = encrypt(rec.name)
            rec.url = '%s/order/%s' % (self.env['ir.config_parameter'].get_param('web.base.url'), rec.encryption)

    @api.multi
    @api.onchange('price_line_ids', 'product_order_ids')
    @api.depends('price_line_ids', 'product_order_ids')
    def _compute_total_price(self):
        for rec in self:
            price = 0
            for product in rec.price_line_ids:
                price += product.debit - product.credit
            rec.total_price = price

    @api.one
    def compute_total_price(self):
        price = 0
        for product in self.price_line_ids:
            price += product.debit - product.credit
        self.write({
            'total_price': price,
            'remaining': price - self.paid
        })

    @api.multi
    def compute_invoice(self):
        for rec in self:
            paid = 0
            for invoice in rec.invoice_ids:
                if invoice.state in ['paid']:
                    paid += invoice.amount
            rec.paid = paid

    @api.multi
    @api.onchange('total_price', 'paid')
    @api.depends('total_price', 'paid')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = rec.total_price - rec.paid

    @api.multi
    def action_confirm(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.state = 'confirm'
                rec.confirm_date = fields.Datetime.now()
                rec.confirm_uid = self.env.user.id
                msg_data = {
                    'name': rec.name,
                    # 'customer_name': rec.customer_id.name,
                    # 'deadline': rec.deadline.strftime('%d-%b-%Y'),
                    'qty_total': rec.qty_total,
                    'product': rec.product,
                    'theme': rec.theme,
                    'url': rec.url
                }
                msg = """
<a href="{url}"><b>{name} CONFIRMED</b></a>
========================
{qty_total}pcs - {product} - {theme}
""".format(**msg_data)
                send_telegram_message(msg)
            else:
                raise UserError(_('You can only confirm a draft sales order'))

    @api.multi
    def action_approve(self):
        for rec in self:
            if rec.state in ['confirm']:
                # DONE: confirm all product order and package order
                for product_order in rec.product_order_ids:
                    product_order.action_confirm()
                for price_line in rec.price_line_ids:
                    price_line.action_confirm()
                rec.state = 'approve'
                rec.approve_date = fields.Datetime.now()
                rec.approve_uid = self.env.user.id
                msg_data = {
                    'name': rec.name,
                    # 'customer_name': rec.customer_id.name,
                    # 'deadline': rec.deadline.strftime('%d-%b-%Y'),
                    'qty_total': rec.qty_total,
                    'product': rec.product,
                    'theme': rec.theme,
                    'url': rec.url
                }
                msg = """
<a href="{url}"><b>{name} APPROVED</b></a>
========================
{qty_total}pcs - {product} - {theme}
""".format(**msg_data)
                send_telegram_message(msg)
            else:
                raise UserError(_('You can only approve a confirmed sales order'))

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state in ['draft']:
                # DONE: cancel all product order and package order
                for product_order in rec.product_order_ids:
                    product_order.action_cancel()
                for invoice in rec.invoice_ids:
                    invoice.action_cancel()
                rec.state = 'cancel'
                rec.cancel_date = fields.Datetime.now()
                rec.cancel_uid = self.env.user.id
            else:
                raise UserError(_("You can't cancel this sales order"))

    @api.multi
    def action_send(self):
        for rec in self:
            if rec.state not in ['approve', 'on_progress', 'done']:
                raise UserError(_("You can only send an approved sales order"))
            #DONE: ga bisa di send sebelum paid
            if rec.remaining != 0:
                raise UserError(_("This sales order isn't fully paid"))
            # DONE: set all products order and package order to done.
            for product_order in rec.product_order_ids:
                product_order.action_send()
            rec.state = 'send'
            rec.send_date = fields.Datetime.now()
            rec.send_uid = self.env.user.id

    @api.multi
    def action_on_progress(self):
        for rec in self:
            if rec.state not in 'approve':
                raise UserError(_("You can only process an approved sales order"))
            rec.state = 'on_progress'

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.state not in ['approve', 'on_progress']:
                raise UserError(_("You can only process an approved sales order"))
            rec.state = 'done'

    def action_url(self):
        return {
            'name': 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.url
        }

    def print_sales_order_quotation(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'sales__order.sales_order_quotation_action_report')

    def print_sales_order_famotain(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'sales__order.sales_order_famotain_action_report')