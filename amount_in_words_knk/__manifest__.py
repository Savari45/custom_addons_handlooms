# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{

    'name': "Amount In Words",
    'version': '18.0.1.2',
    'license': 'OPL-1',
    'depends': ['sale_management', 'purchase', 'account'],
    'category': 'Sales/Sales',
    'author': 'Kanak Infosystems LLP.',
    'website': "https://www.kanakinfosystems.com",
    'summary': """Display Amount In Words in sale order, invoices and purchase orders, both in forms as well as reports. | Amount | Words | Amount In Words | Amount Words | Total Amount | Total Amount In Words""",
    'description': """Display Amount In Words in sale order, invoices and purchase orders, both in forms as well as reports.""",
    'data': [
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/invoice_view.xml',
        'report/sale_order_report.xml',
        'report/purchase_order_report.xml',
        'report/invoice_order_report.xml',
    ],
    'images': ['static/description/banner.gif'],
    'sequence': 1,
    "application": True,
    "installable": True,
}
