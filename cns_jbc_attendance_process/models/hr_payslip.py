from odoo import models, fields, api
from calendar import monthrange


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    total_days_in_month = fields.Float(
        string='No of Days in Month', compute='_compute_total_days_in_period', store=True)
    total_days_present = fields.Float(
        string='Pay Days', compute='_compute_total_days_present', store=True)

    total_ot_hours = fields.Float(
        string='OT Hours', compute='_compute_hours', store=True)

    lop = fields.Float(
        string='LOP Days', compute='_compute_lop', store=True)

    paid_leave_count = fields.Integer(string='Paid Leave', compute='_compute_hours', store=True)
    late_count = fields.Integer(string='Late Count', compute='_compute_hours', store=True)
    permission_count = fields.Integer(string='Permission count', compute='_compute_hours', store=True)
    late_hr = fields.Float(string='Late Hours', compute='_compute_hours', store=True)
    lop_hours = fields.Float(string='LOP Hours', compute='_compute_hours', store=True)
    perm_hr = fields.Float(string='Permission Hours', compute='_compute_hours', store=True)

    @api.depends('total_days_in_month', 'total_days_present')
    def _compute_lop(self):
        for payslip in self:
            payslip.lop = payslip.total_days_in_month - payslip.total_days_present

    def compute_sheet(self):
        res = super().compute_sheet()
        for slip in self:
            slip._compute_total_days_present()
            slip._compute_hours()
        return res

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_hours(self):
        attendance_obj = self.env['process.attendance.lines']
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                attendance_lines = attendance_obj.search_read(
                    domain=[
                        ('employee_id', '=', payslip.employee_id.id),
                        ('date', '>=', payslip.date_from),
                        ('date', '<=', payslip.date_to),
                        ('attendance', '!=', 'absent'),
                    ],
                    fields=['ot_hours', 'attendance', 'late_count', 'permission_count','permission_hours','late_hours','lop_hours']
                )
                payslip.total_ot_hours = sum(line.get('ot_hours', 0.0) for line in attendance_lines)
                payslip.paid_leave_count = sum(1 for line in attendance_lines if line.get('attendance') == 'paid_leave')
                payslip.late_count = sum(line.get('late_count', 0.0) for line in attendance_lines)
                payslip.late_hr = sum(line.get('late_hours', 0.0) for line in attendance_lines)
                payslip.permission_count = sum(line.get('permission_count', 0.0) for line in attendance_lines)
                payslip.perm_hr = sum(line.get('permission_hours', 0.0) for line in attendance_lines)
                payslip.lop_hours = sum(line.get('lop_hours', 0.0) for line in attendance_lines)
            else:
                payslip.total_ot_hours = 0.0
                payslip.paid_leave_count = 0.00
                payslip.late_count = 0.00
                payslip.late_hr = 0.00
                payslip.permission_count = 0.00
                payslip.perm_hr = 0.00
                payslip.lop_hours = 0.00

    @api.depends('date_from', 'date_to')
    def _compute_total_days_in_period(self):
        for payslip in self:
            if payslip.date_from and payslip.date_to:
                delta = payslip.date_to - payslip.date_from
                payslip.total_days_in_month = delta.days + 1
            else:
                payslip.total_days_in_month = 0.0

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_total_days_present(self):
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                attendance_lines = self.env['process.attendance.lines'].search_count([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('date', '>=', payslip.date_from),
                    ('date', '<=', payslip.date_to),
                    ('attendance', '!=', 'absent'),
                ])
                payslip.total_days_present = attendance_lines
            else:
                payslip.total_days_present = 0.0
