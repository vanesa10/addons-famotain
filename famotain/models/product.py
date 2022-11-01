# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api
from odoo import tools
from odoo.modules.module import get_module_resource

# TODO: type label diganti charge, isine ada charge 1k-15k, sama charge yg paten kaya magnet, label, tali panjang katun
PRODUCT_TYPE_LIST = [('product', 'Product'), ('package', 'Package'), ('charge', 'Charge'), ('addons', 'Add-ons'), ('label', 'lbl')]


class Product(models.Model):
    _name = 'famotain.product'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'product_type, name asc'
    _description = 'Famotain Products'
    _rec_name = 'display_name'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('web', 'static/src/img', 'placeholder.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    name = fields.Char('Name', required=True, index=True, track_visibility='onchange')
    display_name = fields.Char('Name', readonly=True, compute='_compute_name', store=True, index=True)
    code = fields.Char('Code', index=True, track_visibility='onchange')
    description = fields.Char('Description', track_visibility='onchange')

    category_id = fields.Many2one('famotain.product_category', 'Category', domain=[('active', '=', True)], track_visibility='onchange')
    design_Size_ids = fields.One2many('famotain.design_size', 'product_id', 'Design Sizes')

    image = fields.Binary("Photo", default=_default_image, attachment=True)
    image_medium = fields.Binary("Medium-sized photo", attachment=True)
    image_small = fields.Binary("Small-sized photo", attachment=True)

    price = fields.Monetary('Price', default=0, required=True, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    active = fields.Boolean('Active', readonly=True, default=1, track_visibility='onchange')
    show_on_web = fields.Boolean('Show On Web', readonly=True, default=1, track_visibility='onchange')
    product_type = fields.Selection(PRODUCT_TYPE_LIST, 'Product Type', required=True, default='product', track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'code already exists!')
    ]

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        vals['name'] = str(vals['name']).title()
        if vals['product_type'] in 'product':
            category_id = self.env['famotain.product_category'].browse(vals['category_id'])
            vals['code'] = category_id.get_last_code()
            category_id.set_last_number()
        else:
            vals['category_id'] = ''
        product = super(Product, self).create(vals)
        return product

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        if 'name' in vals.keys() and vals['name']:
            vals['name'] = str(vals['name']).title()
        if ('product_type' in vals.keys() and vals['product_type'] in 'product') or \
                ('category_id' in vals.keys() and vals['category_id']):
            category_id = self.env['famotain.product_category'].browse(vals['category_id'])
            vals['code'] = category_id.get_last_code()
            category_id.set_last_number()
        else:
            if ('product_type' in vals.keys() and vals['product_type'] not in 'product') or self.product_type != 'product':
                vals['category_id'] = ''
        product = super(Product, self).write(vals)
        return product

    # DONE: code hanya untuk product tas saja, dibuat readonly, compute name kalo product, baru dikasi code, yg lain cuma title aja
    @api.multi
    @api.onchange('code', 'category_id', 'name')
    @api.depends('code', 'category_id', 'name')
    def _compute_name(self):
        for rec in self:
            if rec.product_type == 'product':
                rec.display_name = """%s - %s""" % (str(rec.name).title(), rec.code)
            else:
                rec.display_name = str(rec.name).title()

    @api.multi
    @api.onchange('category_id')
    def _onchange_code(self):
        for rec in self:
            rec.code = rec.category_id.get_last_code()

    @api.multi
    def toggle_show_on_web(self):
        for rec in self:
            rec.show_on_web = not rec.show_on_web


class ProductCategory(models.Model):
    _name = "famotain.product_category"
    _description = "Famotain Product Category"

    name = fields.Char('Name', required=True, index=True)
    code = fields.Char('Code', required=True, index=True)
    last_number = fields.Integer('Last Number', default=1, readonly=True)
    active = fields.Boolean('Active', readonly=True, default=1)
    notes = fields.Text('Notes')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'code already exists!')
    ]

    def get_last_code(self):
        return """{}-{:03d}""".format(self.code, self.last_number)

    def set_last_number(self):
        self.last_number = self.last_number + 1
        return self.last_number
