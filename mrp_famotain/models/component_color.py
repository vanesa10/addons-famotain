# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ComponentColor(models.Model):
    _name = 'mrp_famotain.component_color'
    _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True, index=True, compute="_compute_name")
    component_id = fields.Many2one('mrp_famotain.component', 'Component', required=True, domain=[('active', '=', True)], track_visibility='onchange')
    color = fields.Char('Color', required=True, track_visibility='onchange')

    stock = fields.Float('Stock')
    requirement = fields.Float('Requirement')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')

    @api.multi
    @api.onchange('component_id', 'color')
    @api.depends('component_id', 'color')
    def _compute_name(self):
        for rec in self:
            rec.name = "{} - {}".format(rec.component_id.name, rec.color)