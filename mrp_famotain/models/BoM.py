# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class BillsOfMaterials(models.Model):
    _name = 'mrp_famotain.bom'
    _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, index=True, compute="_compute_name")
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    product_id = fields.Many2one('famotain.product', 'Product', required=True, domain=[('active', '=', True)], track_visibility='onchange')

    width = fields.Float('Width', help="for fabric, embroidery, printing", track_visibility='onchange')
    height = fields.Float('Height', help="for fabric, printing", track_visibility='onchange')
    length = fields.Float('Length', help="for webbing", track_visibility='onchange')
    qty = fields.Integer('Qty', help="for fabric, printing, webbing, accessories", default=1, track_visibility='onchange')

    description = fields.Char('Description', track_visibility='onchange')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.multi
    @api.onchange('component_id', 'product_id', 'description')
    @api.depends('component_id', 'product_id', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {} {}".format(rec.product_id.name, rec.component_id.name, rec.description)

#TODO: buat inherit class ke product. buat nambah field bom_ids di product