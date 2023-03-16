# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.modules.module import get_module_resource
from ...tools import image as tools


class Customer(models.Model):
    _name = 'sales__order.customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char('Name', required=True, track_visibility='onchange')
    email = fields.Char('Email', required=True, track_visibility='onchange')
    phone = fields.Char('Phone', required=True, track_visibility='onchange')
    contact_by = fields.Selection([('WA', 'Whatsapp (WA)'), ('line', 'Line')], track_visibility='onchange')
    address = fields.Text('Address', required=True, track_visibility='onchange')
    city = fields.Char('City', track_visibility='onchange')
    zip_code = fields.Char('Zip Code', track_visibility='onchange')

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

    sales_order_ids = fields.One2many('sales__order.sales__order', 'customer_id', string='Sales Orders')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order Count')
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes')

    def _compute_sale_order_count(self):
        if self.sales_order_ids:
            sale_order_count = 0
            for r in self.sales_order_ids:
                sale_order_count += 1
            self.sale_order_count = sale_order_count

    def prepare_vals(self, name, email, phone, address, contact_by="WA", city="", zip_code=""):
        return {
            'name': str(name).capitalize(),
            'email': str(email).lower(),
            'phone': phone,
            'contact_by': contact_by,
            'address': address,
            'city': city,
            'zip_code': zip_code
        }

    @api.model
    def create(self, vals):
        vals['email'] = str(vals['email']).lower()
        tools.image_resize_images(vals, sizes={'image': (1024, None)})
        return super(Customer, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'email' in vals.keys():
            vals['email'] = str(vals['email']).lower()
        tools.image_resize_images(vals, sizes={'image': (1024, None)})
        return super(Customer, self).write(vals)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        new_name = chosen_name or _('%s (copy)') % self.name
        default = dict(default or {}, name=new_name)
        return super(Customer, self).copy(default)