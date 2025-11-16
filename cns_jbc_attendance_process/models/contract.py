from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    shift_ids = fields.One2many('contract.shift', 'contract_id')


class ContractShift(models.Model):
    _name = 'contract.shift'
    _description = 'Contract Shift'

    contract_id = fields.Many2one('hr.contract', string='Contract')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    shift_id = fields.Many2one('resource.calendar', string='Shift')

    # Restriction for overlapping shifts in the same contract
    @api.constrains('contract_id', 'date_from', 'date_to')
    def _check_overlapping_shifts(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(_("Date To cannot be earlier than Date From."))

                # Check for overlapping shifts in the same contract
                overlapping_shifts = self.search([
                    ('id', '!=', record.id),
                    ('contract_id', '=', record.contract_id.id),
                    ('date_from', '<=', record.date_to),
                    ('date_to', '>=', record.date_from),
                ])

                if overlapping_shifts:
                    raise ValidationError(_(
                        "Shift dates overlap with existing shift(s) in the same contract. "
                        "Please adjust the dates to avoid overlaps."
                    ))

