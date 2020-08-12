# -*- coding: utf-8 -*-
import json
import werkzeug

from odoo import http
from odoo.addons.web.controllers.main import Home
from odoo.http import request, serialize_exception as _serialize_exception
from ...famotain.models.encryption import decrypt
from ...famotain.models.telegram_bot import send_telegram_message

import logging
formatter = '%(asctime)s | %(levelname)s | %(funcName)s | %(lineno)d | %(message)s'
logging.basicConfig(filename='odoo-famotain.log', level=logging.ERROR, format=formatter)
_logger = logging.getLogger(__name__)


class WebsiteController(Home):
    @http.route()
    def index(self, s_action=None, db=None, **kw):
        return werkzeug.utils.redirect('/order/form')


class WebsiteFamotain(http.Controller):
    @http.route('/links', auth='public')
    def links_view(self, **kw):
        try:
            return request.render('web_famotain.links_layout')
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'name': "Server Error",
                'data': se,
                'message': 'Contact admin for more info.'
            }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/form', auth='public')
    def create_order_form_view(self, **kw):
        try:
            packaging_list = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'package'), ('active', '=', True)])
            label = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'label'), ('active', '=', True)], limit=1)
            data = {
                'label': label,
                'packaging_list': packaging_list,
                'action': "/order/action/create"
            }
            return request.render('web_famotain.order_form_layout', data)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'name': "Server Error",
                'data': se,
                'message': 'Contact admin for more info.'
            }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/form/<code>', auth='public')
    def create_order_form_2_view(self, code=None):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            packaging_list = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'package'), ('active', '=', True)])
            label = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'label'), ('active', '=', True)], limit=1)
            data = {
                'label': label,
                'sales_order': sales_order,
                'packaging_list': packaging_list,
                'action': "/order/action/create"
            }
            return request.render('web_famotain.order_form_layout', data)
        except Exception as e:
            se = _serialize_exception(e)
            if se['name'] == "cryptography.fernet.InvalidToken":
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
            else:
                error = {
                    'code': 200,
                    'name': "Server Error",
                    'data': se,
                    'message': 'Contact admin for more info.'
                }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/<code>', auth="public")
    def view_order_form(self, code=None):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            design = False
            design_2 = False
            design_3 = False
            for product_order in sales_order.product_order_ids:
                if product_order.design_image:
                    design = True
                if product_order.design_image_2:
                    design_2 = True
                if product_order.design_image_3:
                    design_3 = True
                if design and design_2 and design_3:
                    break
            data = {
                'sales_order': sales_order,
                'design': design,
                'design_2': design_2,
                'design_3': design_3,
            }
            return request.render('web_famotain.order_layout', data)
        except Exception as e:
            se = _serialize_exception(e)
            if se['name'] == "cryptography.fernet.InvalidToken":
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
            else:
                error = {
                    'code': 200,
                    'name': "Server Error",
                    'data': se,
                    'message': 'Contact admin for more info.'
                }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/<code>/edit', auth='public')
    def edit_order_form_view(self, code=None):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            if sales_order.state != 'draft' and sales_order.state != 'confirm':
                error = {
                    'name': "Your order can't be edited",
                    'message': 'Contact our admin to edit this order.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            packaging_list = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'package'), ('active', '=', True)])
            label = request.env['famotain.product'].sudo().search(
                [('product_type', '=', 'label'), ('active', '=', True)], limit=1)
            data = {
                'edit': True,
                'label': label,
                'sales_order': sales_order,
                'packaging_list': packaging_list,
                'action': '/order/action/edit/%s' % code
            }
            return request.render('web_famotain.order_form_layout', data)
        except Exception as e:
            se = _serialize_exception(e)
            if se['name'] == "cryptography.fernet.InvalidToken":
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
            else:
                error = {
                    'code': 200,
                    'name': "Server Error",
                    'data': se,
                    'message': 'Contact admin for more info.'
                }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/action/create', type='http', methods=['POST'], auth="public", csrf=False)
    def create_order_form(self, **kw):
        try:
            if kw.get('input-packaging') in "-":
                kw['input-packing'] = "-"
                kw['input-packaging'] = ""

            packaging_id = None
            if kw['input-packaging']:
                packaging = request.env['famotain.product'].sudo().search(
                    [('code', '=', kw['input-packaging']), ('product_type', '=', 'package')], limit=1)
                packaging_id = packaging.id

            # search if order exist
            sales_order = request.env['sales__order.sales__order'].sudo().search(
                [('phone', '=', kw.get('input-hp')), ('address', '=', kw.get('input-address')),
                 ('city', '=', kw.get('input-city')), ('qty_total', '=', kw.get('input-qty')),
                 ('deadline', '=', kw.get('input-deadline')), ('event_date', '=', kw.get('input-eventdate')),
                 ('product', '=', kw.get('input-product')), ('theme', '=', kw.get('input-theme')),
                 ('packaging_id', '=', packaging_id), ('packing', '=', kw.get('input-packing')),
                 ('label', '=', kw.get('input-label')), ('custom_name', '=', kw.get('input-customname')),
                 ('additional_text', '=', kw.get('input-additionalwriting')),
                 ('thanks_card_writing', '=', kw.get('input-thankcardwriting')),
                 ('custom_request', '=', kw.get('input-customrequest')), ('customer_notes', '=', kw.get('input-note')),
                 ('add_ons', '=', kw.get('input-addons'))], limit=1)
            if sales_order:
                return werkzeug.utils.redirect('/order/form/created/%s' % sales_order.encryption)

            # create customer
            data_customer = request.env['sales__order.customer'].sudo().prepare_vals(
                name=kw.get('input-name'), phone=kw.get('input-hp'), email=kw.get('input-email'),
                address=kw.get('input-address'), city=kw.get('input-city'), zip_code=kw.get('input-zipcode'),
                contact_by=kw.get('input-orderby'))
            # search if customer is exist
            customer = request.env['sales__order.customer'].sudo().search([('address', '=ilike', data_customer.get('address'))], limit=1)
            if customer:
                customer.sudo().write(data_customer)
            else:
                customer = request.env['sales__order.customer'].sudo().create(data_customer)

            # create sales order
            data_order = request.env['sales__order.sales__order'].sudo().prepare_vals_list(
                customer_id=customer.id, qty_total=kw.get('input-qty'), deadline=kw.get('input-deadline'),
                event_date=kw.get('input-eventdate'), product=kw.get('input-product'), theme=kw.get('input-theme'),
                packaging_id=packaging_id, packing=kw.get('input-packing'), label=kw.get('input-label'),
                custom_name=kw.get('input-customname'), additional_text=kw.get('input-additionalwriting'),
                thanks_card_writing=kw.get('input-thankcardwriting'), custom_request=kw.get('input-customrequest'),
                notes=kw.get('input-note'), add_ons=kw.get('input-addons'))
            sales_order = request.env['sales__order.sales__order'].sudo().create(data_order)
            return werkzeug.utils.redirect('/order/form/created/%s' % sales_order.encryption)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'name': "Server Error",
                'data': se,
                'message': 'Contact admin for more info.'
            }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/action/edit/<code>', type='http', methods=['POST'], auth="public", csrf=False)
    def edit_order_form(self, code=None, **kw):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)

            # check if sales order editable (draft)
            if sales_order.state != 'draft' and sales_order.state != 'confirm':
                error = {
                    'name': "Your order can't be edited",
                    'message': 'Contact our admin to edit this order.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            # edit customer
            data_customer = request.env['sales__order.customer'].sudo().prepare_vals(
                name=kw.get('input-name'), phone=kw.get('input-hp'), email=kw.get('input-email'),
                address=kw.get('input-address'), city=kw.get('input-city'), zip_code=kw.get('input-zipcode'),
                contact_by=kw.get('input-orderby'))
            customer = request.env['sales__order.customer'].sudo().browse(sales_order.customer_id.id)
            customer.sudo().write(data_customer)

            if kw.get('input-packaging') in "-":
                kw['input-packing'] = "-"
                kw['input-packaging'] = ""

            packaging_id = None
            if kw['input-packaging']:
                packaging = request.env['famotain.product'].sudo().search(
                    [('code', '=', kw['input-packaging']), ('product_type', '=', 'package')], limit=1)
                packaging_id = packaging.id

            # edit sales order
            data_order = request.env['sales__order.sales__order'].sudo().prepare_vals_list(
                customer_id=customer.id, qty_total=kw.get('input-qty'), deadline=kw.get('input-deadline'),
                event_date=kw.get('input-eventdate'), product=kw.get('input-product'), theme=kw.get('input-theme'),
                packaging_id=packaging_id, packing=kw.get('input-packing'), label=kw.get('input-label'),
                custom_name=kw.get('input-customname'), additional_text=kw.get('input-additionalwriting'),
                thanks_card_writing=kw.get('input-thankcardwriting'), custom_request=kw.get('input-customrequest'),
                notes=kw.get('input-note'), add_ons=kw.get('input-addons'))
            sales_order.write_from_web(data_order)
            return werkzeug.utils.redirect('/order/form/edited/%s' % sales_order.encryption)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'name': "Server Error",
                'data': se,
                'message': 'Contact admin for more info.'
            }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/action/confirm/<code>', auth="public")
    def confirm_order_form(self, code=None, **kw):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)

            # check if sales order editable (draft)
            if sales_order.state != 'confirm':
                error = {
                    'name': "Your order can't be confirmed",
                    'message': 'Contact our admin to confirm this order.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            sales_order.action_approve()
            return werkzeug.utils.redirect('/order/form/confirmed/%s' % sales_order.encryption)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'name': "Server Error",
                'data': se,
                'message': 'Contact admin for more info.'
            }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)

    @http.route('/order/form/<info>/<code>', auth="public")
    def order_form_info_view(self, code=None, info=''):
        try:
            order = decrypt(code)
            sales_order = request.env['sales__order.sales__order'].sudo().search([('name', '=', order)], limit=1)
            if not sales_order:
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
                _logger.error(json.dumps(error))
                return request.render('web_famotain.error_layout', error)
            data = {
                'sales_order': sales_order,
                'info': info
            }
            return request.render('web_famotain.order_info_layout', data)
        except Exception as e:
            se = _serialize_exception(e)
            if se['name'] == "cryptography.fernet.InvalidToken":
                error = {
                    'name': "Your order can't be found",
                    'message': 'Please check the requested url or contact our admin for more info.'
                }
            else:
                error = {
                    'code': 200,
                    'name': "Server Error",
                    'data': se,
                    'message': 'Contact admin for more info.'
                }
            _logger.error(json.dumps(error))
            return request.render('web_famotain.error_layout', error)
