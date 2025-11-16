{
    'name': 'JBC Attendance Process',
    'version': '18.0',
    'author': 'Sumesh T',
    'category': 'HR',
    'depends': ['base', 'hr','hr_contract','payroll'],
    'data': [
        "security/ir.model.access.csv",
        "views/contract_views.xml",
        "views/process_attendance_view.xml",
        "views/resource_calendar_view.xml",
        "views/hr_payslip_view.xml",
    ],
    'installable': True,
    'application': True,
}
