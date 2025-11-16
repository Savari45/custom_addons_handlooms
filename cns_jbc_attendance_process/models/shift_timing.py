from odoo import models, fields


def float_to_time(float_time):
    """Convert float time (e.g., 6.75) to HH:MM format (06:45)."""
    hours = int(float_time)
    minutes = round((float_time - hours) * 60)
    return f"{hours:02}:{minutes:02}"

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    shift_start_time = fields.Float(string="Shift Start Time", required=True,
                                    help="Start time of the shift (24-hour format)")
    shift_end_time = fields.Float(string="Shift End Time", required=True, help="End time of the shift (24-hour format)")

    def name_get(self):
        res = []
        for i in self:
            start_time = float_to_time(i.shift_start_time)
            end_time = float_to_time(i.shift_end_time)
            name = f"{i.name} - [{start_time} to {end_time}]"
            res.append((i.id, name))
        return res

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_paid_leave = fields.Boolean(string='Is Paid leave', help="Considered as a Paid Leave in Process Attendance")





