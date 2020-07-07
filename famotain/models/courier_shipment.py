# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CourierShipment(models.Model):
    _name = 'famotain.courier_shipment'
    _order = 'name asc'
    _description = 'All Courier Shipment Used'

    name = fields.Char('Courier Shipment', required=True, index=True)
    active = fields.Boolean('Active', readonly=True, default=1)
    notes = fields.Text('Notes')
