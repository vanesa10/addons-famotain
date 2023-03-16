# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api, _
from odoo.modules.module import get_module_resource
from ...tools import image as tools

import logging
_logger = logging.getLogger(__name__)


class Vendor(models.Model):
    _name = 'mrp_famotain.vendor'
    _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, track_visibility='onchange')
    email = fields.Char('Email')
    phone = fields.Char('Phone', track_visibility='onchange')
    address = fields.Text('Address')
    city = fields.Char('City', track_visibility='onchange')
    zip_code = fields.Char('Zip Code')

    component_vendor_ids = fields.One2many('mrp_famotain.component_vendor', 'vendor_id', 'Components', track_visibility='onchange')

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')