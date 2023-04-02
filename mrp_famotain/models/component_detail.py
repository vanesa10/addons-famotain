# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ComponentDetail(models.Model):
    _name = 'mrp_famotain.component_detail'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Detail of a Component'

    name = fields.Char('Name', readonly=True, compute="_compute_name", store=True)
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    detail = fields.Char('Detail', required=True, track_visibility='onchange')

    vendor_id = fields.Many2one('mrp_famotain.vendor', 'Vendor', domain=[('active', '=', True)], track_visibility='onchange')
    price = fields.Monetary('Price', help="normal retail price for selling price calculation", track_visibility='onchange')
    gross_price = fields.Monetary('Gross Price', track_visibility='onchange')
    gross_qty = fields.Float('Gross Qty', help="minimum qty for gross price", track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.multi
    @api.onchange('component_id', 'detail')
    @api.depends('component_id', 'detail')
    def _compute_name(self):
        for rec in self:
            if rec.detail in ['.', '-', ' ']:
                rec.name = 'None'
            else:
                rec.name = "{} - {}".format(rec.component_id.name, rec.detail)

    def open_record(self):
        rec_id = self.id
        form_id = self.env.ref('mrp_famotain.component_detail_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Component Detail Form',
            'res_model': 'mrp_famotain.component_detail',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }