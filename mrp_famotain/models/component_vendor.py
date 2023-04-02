# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ComponentVendor(models.Model):
    _name = 'mrp_famotain.component_vendor'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vendor of a Component'

    name = fields.Char('Name', readonly=True, index=True, compute="_compute_name")
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Vendor', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    price = fields.Monetary('Price', required=True, help="normal retail price for selling price calculation", track_visibility='onchange')
    gross_price = fields.Monetary('Gross Price', track_visibility='onchange')
    gross_qty = fields.Float('Gross Qty', help="minimum qty for gross price", track_visibility='onchange')

    is_main_vendor = fields.Boolean('Main Vendor', track_visibility='onchange', default=False)

    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.multi
    def write(self, vals):
        component_vendor = super(ComponentVendor, self).write(vals)
        if vals.get('price'):
            bom = self.env['mrp_famotain.bom'].search([('component_vendor_id', '=', self.id), ('state', 'in', ['draft', 'approve', 'ready'])])
            if bom:
                bom._compute_unit_cost()
        return component_vendor

    @api.multi
    @api.onchange('component_id', 'vendor_id')
    @api.depends('component_id', 'vendor_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {}".format(rec.component_id.name, rec.vendor_id.name)

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.component_vendor_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Component Vendor Form',
            'res_model': 'mrp_famotain.component_vendor',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }