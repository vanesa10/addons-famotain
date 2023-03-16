# -*- coding: utf-8 -*-

from odoo import models, fields, api
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
    _desc = 'Manufacturing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Manufacturing Order', default='New', readonly=True, index=True, tracking=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    component_color_id = fields.Many2one('mrp_famotain.component_color', 'Component Color', domain=[('active', '=', True)], track_visibility='onchange')
    product_order_id = fields.Many2one('sales__order.product_order', 'Product Order', required=True, track_visibility='onchange')

    #TODO: tambah field product_id
    qty = fields.Float('Qty', track_visibility='onchange')
    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Vendor', domain=[('active', '=', True)], track_visibility='onchange')

    price_calculation = fields.Monetary('Price Calculation')

    state = fields.Selection([('draft', 'Draft'), ('approve','Approved'), ('ready', 'Ready'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, default='draft', readonly=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(
                    ir_sequence_date=str(fields.Date.today())[:10]).next_by_code('mrp_famotain.manufacturing_order'),
            })
        return super(ManufacturingOrder, self).create(vals_list)