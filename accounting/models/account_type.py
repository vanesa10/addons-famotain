# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountType(models.Model):
    _name = 'accounting.account_type'
    _order = 'prefix asc'
    _description = 'Account Type (Equity, Dividend, Liability, Asset, Revenue, Expense)'

    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    account_type = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], 'Account Type', required=True, default='debit', readonly=True, states={'draft': [('readonly', False)]})
    prefix = fields.Char('Prefix', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], 'State', required=True, default='draft', readonly=True)
    notes = fields.Text('Notes')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed On', readonly=True)

    @api.multi
    @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ['draft']:
                return super(AccountType, self).unlink()
            raise UserError(_("You can only delete a draft record"))

    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.confirm_date = fields.Datetime.now()
            rec.confirm_uid = self.env.user.id
