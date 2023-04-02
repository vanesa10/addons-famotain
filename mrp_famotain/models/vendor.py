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
    _description = 'Vendor'

    name = fields.Char('Name', required=True, track_visibility='onchange')
    email = fields.Char('Email', track_visibility='onchange')
    phone = fields.Char('Phone', track_visibility='onchange')
    address = fields.Text('Address', track_visibility='onchange')
    city = fields.Char('City', track_visibility='onchange')
    zip_code = fields.Char('Zip Code', track_visibility='onchange')

    is_retailer = fields.Boolean('Retailer', track_visibility='onchange', default=False)
    is_manufacturer = fields.Boolean('Manufacturer', track_visibility='onchange', default=False)

    component_detail_ids = fields.One2many('mrp_famotain.component_detail', 'vendor_id', 'Component Details')
    component_vendor_ids = fields.One2many('mrp_famotain.component_vendor', 'vendor_id', 'Components')

    active = fields.Boolean(default=True, track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')