# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api
from odoo import tools
from odoo.modules.module import get_module_resource


PRODUCT_TYPE_LIST = [('product', 'Product'), ('package', 'Package'), ('label', 'Label'), ('addons', 'Add-ons')]


class Product(models.Model):
    _name = 'famotain.product'
    _order = 'product_type, name asc'
    _description = 'Famotain Products'
    _rec_name = 'display_name'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('web', 'static/src/img', 'placeholder.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    name = fields.Char('Name', required=True, index=True)
    display_name = fields.Char('Name', readonly=True, compute='_compute_name', store=True, index=True)
    code = fields.Char('Code', required=True, index=True)
    description = fields.Char('Description')

    design_Size_ids = fields.One2many('famotain.design_size', 'product_id', 'Design Sizes')

    image = fields.Binary("Photo", default=_default_image, attachment=True)
    image_medium = fields.Binary("Medium-sized photo", attachment=True)
    image_small = fields.Binary("Small-sized photo", attachment=True)

    price = fields.Monetary('Price', default=0, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    active = fields.Boolean('Active', readonly=True, default=1)
    product_type = fields.Selection(PRODUCT_TYPE_LIST, 'Product Type', required=True, default='product')
    notes = fields.Text('Notes')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'code already exists!')
    ]

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(Product, self).create(vals)

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(Product, self).write(vals)

    @api.multi
    @api.onchange('code', 'name')
    @api.depends('code', 'name')
    def _compute_name(self):
        for rec in self:
            rec.display_name = """%s - %s""" % (rec.name, rec.code)
