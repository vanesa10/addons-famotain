# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


EXPENSE_TYPE = [
    (1, 'Famotain Expenses'),
    (2, 'Home Expenses'),
    (3, 'Other Expenses')
]


class Expense(models.Model):
    _name = 'accounting.expense'
    _order = 'name desc'

    name = fields.Char('Name', readonly=True, default='New')
    expense_type = fields.Selection(EXPENSE_TYPE, 'Expense Type', readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Char('Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted')], 'State', required=True, default='draft', readonly=True)
    amount = fields.Monetary('Amount', required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    journal_ids = fields.One2many('accounting.journal', 'famotain_expenses_id', 'Journals', readonly=True)
    notes = fields.Text('Notes')

    post_uid = fields.Many2one('res.users', 'Posted By', readonly=True)
    post_date = fields.Datetime('Posted On', readonly=True)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(ir_sequence_date=str(fields.Date.today())[:10]).next_by_code(
                    'accounting.expense'),
            })
        return super(Expense, self).create(vals_list)

    # @api.multi
    # @api.model
    # def unlink(self):
    #     for rec in self:
    #         for journal_account_id in rec.journal_account_ids:
    #             journal_account_id.unlink()
    #         if rec.state in ['draft']:
    #             return super(Journal, self).unlink()
    #         raise UserError(_("You can only delete a draft record"))
