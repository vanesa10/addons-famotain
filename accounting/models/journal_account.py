# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class JournalAccount(models.Model):
    _name = 'accounting.journal_account'
    _order = 'name desc'

    name = fields.Char('Name', readonly=True, default='New')
    account_id = fields.Many2one('accounting.account', 'Account', required=True, readonly=True, states={'draft': [('readonly', False)]})
    debit = fields.Monetary('Debit', required=True, readonly=True, states={'draft': [('readonly', False)]})
    credit = fields.Monetary('Credit', required=True, readonly=True, states={'draft': [('readonly', False)]})
    balance = fields.Monetary('Balance', readonly=True, compute='_compute_balance', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    journal_id = fields.Many2one('accounting.journal', 'Journal', required=True, readonly=True)

    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted')], 'State', required=True, default='draft', readonly=True)
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(ir_sequence_date=str(fields.Date.today())[:10]).next_by_code(
                    'accounting.journal_account'),
            })
        return super(JournalAccount, self).create(vals_list)

    # @api.multi
    # @api.model
    # def unlink(self):
    #     for rec in self:
    #         if rec.state in ['draft']:
    #             return super(JournalAccount, self).unlink()
    #         raise UserError(_("You can only delete a draft record"))

    @api.multi
    @api.depends('account_id', 'debit', 'credit')
    @api.onchange('account_id', 'debit', 'credit')
    def _compute_balance(self):
        for rec in self:
            balance = 0
            if rec.account_id:
                if rec.account_id.account_type_id.account_type == 'debit':
                    balance = rec.debit - rec.credit
                else:
                    balance = rec.credit - rec.debit
            rec.balance = balance

    @api.multi
    def action_post(self):
        for rec in self:
            rec.state = 'post'
