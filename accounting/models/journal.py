# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


JOURNAL_TYPE = [
    (1, 'Famotain Expenses'),
    (2, 'Home Expenses'),
    (3, 'Other Expenses'),
    (4, 'Famotain Revenues'),
    (5, 'Others'),
]


class Journal(models.Model):
    _name = 'accounting.journal'
    _order = 'name desc'

    name = fields.Char('Name', readonly=True, default='New')
    journal_type = fields.Selection(JOURNAL_TYPE, 'Journal Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=1)
    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted')], 'State', required=True, default='draft', readonly=True)
    journal_account_ids = fields.One2many('accounting.journal_account', 'journal_id', 'Journal Accounts', readonly=True, states={'draft': [('readonly', False)]})
    sum = fields.Monetary('Sum', compute='_compute_sum', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    famotain_expenses_id = fields.Many2one('accounting.expense', 'Famotain Expenses', readonly=True)

    notes = fields.Text('Notes')

    post_uid = fields.Many2one('res.users', 'Posted By', readonly=True)
    post_date = fields.Datetime('Posted On', readonly=True)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name') != 'New':
            vals_list.update({
                'name': self.env['ir.sequence'].with_context(ir_sequence_date=str(fields.Date.today())[:10]).next_by_code(
                    'accounting.journal'),
            })
        return super(Journal, self).create(vals_list)

    # @api.multi
    # @api.model
    # def unlink(self):
    #     for rec in self:
    #         for journal_account_id in rec.journal_account_ids:
    #             journal_account_id.unlink()
    #         if rec.state in ['draft']:
    #             return super(Journal, self).unlink()
    #         raise UserError(_("You can only delete a draft record"))

    @api.multi
    @api.onchange('journal_account_ids')
    @api.depends('journal_account_ids')
    def _compute_sum(self):
        for rec in self:
            sum = 0
            for journal_account_id in rec.journal_account_ids:
                sum += journal_account_id.debit
            rec.sum = sum

    @api.multi
    def action_post(self):
        for rec in self:
            sum_credit = 0
            sum_debit = 0
            for journal_account_id in rec.journal_account_ids:
                sum_credit += journal_account_id.credit
                sum_debit += journal_account_id.debit
            if sum_debit == sum_credit:
                for journal_account_id in rec.journal_account_ids:
                    journal_account_id.action_post()
                rec.state = 'post'
                rec.post_date = fields.Datetime.now()
                rec.post_uid = self.env.user.id
            else:
                raise UserError(_("Failed to post. This journal is not balanced!"))
