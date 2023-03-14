# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api
from odoo import tools, _
from odoo.modules.module import get_module_resource

import logging
_logger = logging.getLogger(__name__)


class Vendor(models.Model):
    _name = 'mrp_famotain.vendor'
    # _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, track_visibility='onchange')
    email = fields.Char('Email')
    phone = fields.Char('Phone', track_visibility='onchange')
    address = fields.Text('Address')
    city = fields.Char('City')
    zip_code = fields.Char('Zip Code')

    @api.model
    def _default_image(self):
        image_path = get_module_resource('base', 'static/img', 'avatar.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    image = fields.Binary(
        "Photo", default=_default_image, attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    active = fields.Boolean(default=True)
    notes = fields.Text('Notes', track_visibility='onchange')