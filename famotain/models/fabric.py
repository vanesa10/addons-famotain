# # -*- coding: utf-8 -*-
#
# from odoo import models, fields, api
# import logging
# _logger = logging.getLogger(__name__)
#
#
# class Fabric(models.Model):
#     _name = 'famotain.fabric'
#     _order = 'name asc'
#     _description = 'All fabrics used in products'
#
#     name = fields.Char('Fabric', required=True, index=True)
#     price = fields.Monetary('Price', computed='_compute_price')
#     price_total = fields.Monetary('Price Total', required=True)
#     qty = fields.Float('Qty', required=True, default=1)
#     width = fields.Float('Width', required=True)
#     currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
#     notes = fields.Text('Notes')
#
#     @api.multi
#     @api.onchange('price_total', 'qty')
#     @api.depends('price_total', 'qty')
#     def _compute_price(self):
#         for rec in self:
#             _logger.info('MASUK')
#             price = (self.price_total / self.qty)
#             rec.price = price
