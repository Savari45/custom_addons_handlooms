from odoo import fields, models, api, _
from datetime import timedelta, datetime, time
import pytz
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, ValidationError
import math
from odoo.tools.float_utils import float_round


class ProcessAttendance(models.Model):
    _name = 'process.attendance'
    _description = 'Process Attendance'

    name = fields.Char(string='Reference')
    start_date = fields.Date(default=fields.Date.today())
    end_date = fields.Date(default=fields.Date.today())
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    attendance_line_ids = fields.One2many('process.attendance.lines', 'attendance_id', string="Attendance Lines")

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for record in self:
            if record.start_date and record.end_date:
                if (record.end_date - record.start_date).days > 90:
                    raise ValidationError("The date range cannot be more than 90 days.")

    def fetch_attendance(self):
        self.ensure_one()
        query = """
            DELETE FROM process_attendance_lines
            WHERE date >= %s
            AND date <= %s
        """
        params = [self.start_date, self.end_date]
        if self.employee_ids:
            query += " AND employee_id IN %s"
            params.append(tuple(self.employee_ids.ids))
        self._cr.execute(query, params)

        # Recreate records with shift assignment from contract shifts
        domain = []
        current_date = self.start_date
        if self.employee_ids:
            domain += [('id', 'in', self.employee_ids.ids)]
        employees = self.env['hr.employee'].search(domain)
        attendance_data = []

        while current_date <= self.end_date:
            for emp in employees:
                # Get shift from contract based on date
                shift_id = self._get_employee_shift_for_date(emp, current_date)

                domain = []
                domain += [
                    ('employee_id', '=', emp.id),
                    ('check_in', '>=', current_date.strftime('%Y-%m-%d 00:00:00')),
                    ('check_in', '<=', current_date.strftime('%Y-%m-%d 23:59:59')),
                ]
                attendance_records = self.env['hr.attendance'].search(domain, order='check_in asc')
                check_in = min(attendance_records.mapped('check_in')) if attendance_records else False
                check_out_list = attendance_records.filtered(lambda r: r.check_out).mapped('check_out')
                check_out = max(check_out_list) if check_out_list else False

                attendance_data.append((0, 0, {
                    'employee_id': emp.id,
                    'employee_no': emp.barcode,
                    'resource_calendar_id': shift_id,
                    'date': current_date,
                    'check_in': check_in,
                    'check_out': check_out,
                }))
            current_date += timedelta(days=1)
        self.attendance_line_ids = attendance_data

    def _get_employee_shift_for_date(self, employee, date):
        """
        Get the shift for an employee on a specific date from their contract shifts.
        Returns the shift_id from contract.shift if the date falls within date_from and date_to.
        Otherwise, returns the default resource_calendar_id from the employee.
        """
        contract = employee.contract_id

        if contract:
            # Look for a shift that covers the specific date
            shift = self.env['contract.shift'].search([
                ('contract_id', '=', contract.id),
                ('date_from', '<=', date),
                ('date_to', '>=', date)
            ], limit=1)

            if shift:
                return shift.shift_id.id

        # Fallback to employee's default shift
        return employee.resource_calendar_id.id



class ProcessAttendanceLines(models.Model):
    _name = 'process.attendance.lines'
    _description = 'Process Attendance Lines'

    attendance_id = fields.Many2one('process.attendance', string="Attendance Reference")
    date = fields.Date(string="Date")
    employee_id = fields.Many2one('hr.employee', string="Employee Name", required=True)
    employee_no = fields.Char(string="Employee ID")
    check_in = fields.Datetime(string="Check-in")
    check_out = fields.Datetime(string="Check-out")

    worked_hours = fields.Float(string="Worked Hours", compute='_compute_worked_hours', store=True)
    permission_hours = fields.Float(string="Permission Hours", compute='_compute_leave_attendance_fields', store=True)
    permission_count = fields.Integer(string="Permission Count", compute='_compute_permission_count', store=True)
    leave_days = fields.Float(string="Leave Days",
                              store=True)

    leave_type = fields.Many2many('hr.leave.type', string='Leave Type',
                                  store=True)

    late_hours = fields.Float(string="Late Hours", compute='compute_late_hours', store=True)
    late_count = fields.Integer(string="Late Count", compute='_compute_late_count', store=True)
    ot_hours = fields.Float(string="OT Hours", compute='compute_late_hours', store=True)
    lop_hours = fields.Float(string='LOP Hours', compute='_compute_lop_hours', store=True)

    @api.depends('employee_id', 'date', 'check_in')
    def _compute_lop_hours(self):
        for record in self:
            lop_hours = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('holiday_status_id.name', '=', 'LOP'),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', record.date),
                ('request_date_to', '>=', record.date),
            ])
            print('---------lop_hours',lop_hours)
            if lop_hours:
                leave_unit = lop_hours[0].holiday_status_id.request_unit  # 'day' or 'hour'
                record.lop_hours = (
                    float_round(
                        sum(lop_hours.mapped('number_of_hours')),
                        precision_digits=2
                    )
                    if leave_unit == 'hour'
                    else float_round(
                        sum(lop_hours.mapped('number_of_days')),
                        precision_digits=2))

    attendance = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('week_off', 'Week-off'),
        ('public_holiday', 'Public Holiday'),
        ('paid_leave', 'Paid Leave'),
    ], compute='_compute_leave_attendance_fields', store=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Shift')

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):  # computed
        for i in self:
            i.worked_hours = 0.00
            if i.check_in and i.check_out:
                i.worked_hours = (i.check_out - i.check_in).total_seconds() / 3600.0

    @api.depends('employee_id', 'date', 'check_in')
    def _compute_leave_attendance_fields(self):
        for record in self:
            record.leave_days = 0.0
            record.leave_type = [(5, 0, 0)]  # Clear existing relations
            record.attendance = 'absent'  # Default value
            record.permission_hours = 0.0

            if not record.employee_id or not record.date:
                continue

            approved_permission_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('holiday_status_id.name', '=', 'Permission'),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', record.date),
                ('request_date_to', '>=', record.date),
            ])

            if approved_permission_leaves:
                leave_unit = approved_permission_leaves[0].holiday_status_id.request_unit  # 'day' or 'hour'
                record.permission_hours = (
                    float_round(
                        sum(approved_permission_leaves.mapped('number_of_hours')),
                        precision_digits=2
                    )
                    if leave_unit == 'hour'
                    else float_round(
                        sum(approved_permission_leaves.mapped('number_of_days')),
                        precision_digits=2))

            # ✅ **Fetch Other Approved Leaves**
            other_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('holiday_status_id.name', 'not in', ['Permission', 'OT hours']),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', record.date),
                ('request_date_to', '>=', record.date),
            ])
            other_leave_types = [j.holiday_status_id.id for j in other_leaves]
            combined_leave_types = list(set(other_leave_types))
            if combined_leave_types:
                record.leave_type = [(6, 0, combined_leave_types)]
            if not record.check_in:
                record.leave_days = 1  # Mark as absent
            week_off_days = record.resource_calendar_id.attendance_ids.mapped('dayofweek')
            current_dayofweek = str(record.date.weekday())
            print('-------week_off_days', week_off_days)
            print('-------current_dayofweek', current_dayofweek)

            paid_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('holiday_status_id.is_paid_leave', '=', True),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', record.date),
                ('request_date_to', '>=', record.date),
            ])

            if current_dayofweek not in week_off_days and not record.check_out:
                record.attendance = 'week_off'
            elif record.check_in:
                record.attendance = 'present'
            elif paid_leaves:
                record.attendance = 'paid_leave'
            else:
                record.attendance = 'absent'

    @api.depends('permission_hours')
    def _compute_permission_count(self):
        for record in self:
            if record.permission_hours > 0.00:
                record.permission_count = 1
            else:
                record.permission_count = 0

    @api.depends('late_hours')
    def _compute_late_count(self):
        for i in self:
            i.late_count = 0
            if i.late_hours > 0.00:
                i.late_count = 1

    @api.depends('check_in', 'check_out', 'resource_calendar_id', 'date')
    def compute_late_hours(self):
        for record in self:
            record.late_hours = 0.0
            record.ot_hours = 0.0
            morning_ot = 0.0
            evening_ot = 0.0

            if not record.resource_calendar_id or not record.date or not record.check_in or not record.check_out:
                continue

            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            shift = record.resource_calendar_id

            # Shift start time
            shift_start_hour = int(shift.shift_start_time)
            shift_start_minute = int((shift.shift_start_time % 1) * 60)
            shift_start_time_obj = time(shift_start_hour, shift_start_minute)

            # Shift end time
            shift_end_hour = int(shift.shift_end_time)
            shift_end_minute = int((shift.shift_end_time % 1) * 60)
            shift_end_time_obj = time(shift_end_hour, shift_end_minute)

            # Convert to datetime objects with timezone
            shift_start_datetime = user_tz.localize(datetime.combine(record.date, shift_start_time_obj))
            shift_end_datetime = user_tz.localize(datetime.combine(record.date, shift_end_time_obj))

            check_in_local = pytz.utc.localize(record.check_in).astimezone(user_tz)
            check_out_local = pytz.utc.localize(record.check_out).astimezone(user_tz)

            # Calculate late hours (existing logic)
            allowed_check_in_time = shift_start_datetime
            if check_in_local > allowed_check_in_time:
                total_late_minutes = (check_in_local - allowed_check_in_time).total_seconds() / 60.0
                if total_late_minutes > 30:
                    late_minutes = math.floor(total_late_minutes)
                    record.late_hours = late_minutes / 60.0

            # Calculate morning OT (30 minutes before shift start)
            morning_ot_start = shift_start_datetime - timedelta(minutes=30)
            if check_in_local < morning_ot_start:
                # If check-in is before morning OT start, calculate from actual check-in
                morning_ot_end = min(shift_start_datetime, check_out_local)
                morning_ot_duration = (morning_ot_end - check_in_local).total_seconds() / 3600.0
                morning_ot = max(0.0, morning_ot_duration)

            # Calculate evening OT (only if check-out is more than 30 minutes after shift end)
            if check_out_local > shift_end_datetime:
                overtime_minutes = (check_out_local - shift_end_datetime).total_seconds() / 60.0
                if overtime_minutes > 30:
                    # Calculate OT from shift end time to check-out time
                    evening_ot_duration = (check_out_local - shift_end_datetime).total_seconds() / 3600.0
                    evening_ot = evening_ot_duration

            # Calculate total OT hours (no rounding)
            record.ot_hours = morning_ot + evening_ot
