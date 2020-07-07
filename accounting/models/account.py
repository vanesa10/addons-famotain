# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Account(models.Model):
    _name = 'accounting.account'
    _order = 'account_type_id desc,number asc'
    _description = 'Famotain Account'

    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    account_type_id = fields.Many2one('accounting.account_type', 'Account Type', required=True, readonly=True, states={'draft': [('readonly', False)]})
    number = fields.Char('Number', required=True, readonly=True, states={'draft': [('readonly', False)]})
    account_number = fields.Char('Account Number', compute='_compute_account_number', readonly=True)
    journal_account_ids = fields.One2many('accounting.journal_account', 'account_id', 'Journal Accounts', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], 'State', required=True, default='draft', readonly=True)
    notes = fields.Text('Notes')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed On', readonly=True)

    @api.multi
    @api.depends('number', 'account_type_id.prefix')
    @api.onchange('number', 'account_type_id.prefix')
    def _compute_account_number(self):
        for rec in self:
            rec.account_number = str(rec.account_type_id.prefix and rec.account_type_id.prefix or "0") + str(rec.number and rec.number or "0")

    # @api.multi
    # @api.model
    # def unlink(self):
    #     for rec in self:
    #         if rec.state in ['draft']:
    #             return super(Account, self).unlink()
    #         raise UserError(_("You can only delete a draft record"))

    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.confirm_date = fields.Datetime.now()
            rec.confirm_uid = self.env.user.id
