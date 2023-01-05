# -*- coding: utf-8 -*-
{
    'name': "GPay",

    'summary': """
        Gestion de la paie""",

    'description': """
        
    """,

    'author': "G&G Professional Services",
    'website': "https://www.gandgcorp.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'om_hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/convention_collective_data.xml',
        'data/salary_rule_data.xml',
        'data/custom_format_paper.xml',
        'static/src/css/my_css.xml',
        'views/convention_collective_views.xml',
        'views/employee_bonus_views.xml',
        'views/hr_employee_inherit_views.xml',
        'views/hr_salary_rule_inherit.xml',
        'views/res_company_inherit_views.xml',
        'views/report_bulletin_paie.xml',
        'views/custom_external_layout_bulletin.xml',
        'wizard/cotisation_ipres.xml',
        'views/report_cotisation_ipres.xml',
        'wizard/securite_sociale.xml',
        'views/report_securite_sociale.xml',
        'wizard/declaration_retenues.xml',
        'views/report_declaration_retenues.xml',
        'wizard/transfer_order.xml',
        'views/report_transfer_order.xml',
        'views/menu_reports.xml',
        'views/res_config_settings_inherit_view.xml',
        'views/hr_leave_type_inherit.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
