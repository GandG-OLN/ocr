# -*- coding:utf-8 -*-
# by khk
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class DeclarationRetenues(models.TransientModel):
    _name = 'report.khk_hr_payor.report_declaration_retenues_view'
    _description = 'Rapport declaration des retenues'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        server_dt = DEFAULT_SERVER_DATE_FORMAT
        number_month_to_word = {
            "1": "janvier",
            "2": "février",
            "3": "mars",
            "4": "avril",
            "5": "mai",
            "6": "juin",
            "7": "julliet",
            "8": "aout",
            "9": "septembre",
            "10": "octobre",
            "11": "novembre",
            "12": "decembre"
        }
        now = datetime.now()
        register_ids = self.env.context.get('active_ids', [])
        contrib_registers = self.env['payor.declaration.retenues'].browse(register_ids)
        date_from = data['form'].get('date_from', fields.Date.today())
        date_to = data['form'].get('date_to', str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10])
        month_from = datetime.strptime(str(date_from), server_dt).month
        month_to = datetime.strptime(str(date_to), server_dt).month
        year_from = datetime.strptime(str(date_from), server_dt).year
        year_to = datetime.strptime(str(date_to), server_dt).year

        periode = ""
        if month_from == month_to and year_from == year_to:
            periode = number_month_to_word.get(str(month_from)) + " " + str(year_from)
        else:
            periode = number_month_to_word.get(str(month_from)) + " " + str(
                year_from) + " au " + number_month_to_word.get(str(month_to)) + " " + str(year_to)

        total_brut_male = 0.0
        total_ir_male = 0.0
        total_trimf_male = 0.0
        total_cfce_male = 0.0

        total_brut_female = 0.0
        total_ir_female = 0.0
        total_trimf_female = 0.0
        total_cfce_female = 0.0
        
        total_brut_n = 0.0
        total_ir_n = 0.0
        total_trimf_n = 0.0
        total_cfce_n = 0.0

        total_brut_nn = 0.0
        total_ir_nn = 0.0
        total_trimf_nn = 0.0
        total_cfce_nn = 0.0

        dict = {}
        self.env.cr.execute("SELECT hr_payslip_line.id from \
                hr_salary_rule_category as hr_salary_rule_category INNER JOIN hr_payslip_line as \
                hr_payslip_line ON hr_salary_rule_category.id = hr_payslip_line.category_id INNER JOIN \
                hr_employee as hr_employee ON hr_payslip_line.employee_id = hr_employee.id INNER JOIN \
                hr_payslip as hr_payslip ON hr_payslip_line.slip_id = hr_payslip.id AND hr_employee.id \
                = hr_payslip.employee_id where hr_payslip.date_from >= %s  AND hr_payslip.date_to <= \
                %s AND hr_employee.company_id = %s AND hr_payslip_line.code IN ('C1200','C2170','C2050','C2000') ORDER BY \
                hr_employee.name ASC, hr_payslip_line.code ASC",
                            (date_from, date_to, self.env.user.company_id.id))
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        nb_male = 0
        nb_female = 0
        for line in self.env['hr.payslip.line'].browse(line_ids):
            
            if line.code == 'C2170':  # ir_fin
                if line.employee_id.gender == 'male':
                    if line.employee_id.id not in dict:
                        dict[line.employee_id.id] = [line.employee_id.country_id.code, line.employee_id.gender]
                        nb_male += 1
                    total_ir_male += line.total
                if line.employee_id.gender == 'female':
                    if line.employee_id.id not in dict:
                        dict[line.employee_id.id] = [line.employee_id.country_id.code, line.employee_id.gender]
                        nb_female += 1
                    total_ir_female += line.total
                
                if line.employee_id.country_id.code == 'SN':
                    total_ir_n += line.total
                else:
                    total_ir_nn += line.total
                    
            if line.code == 'C2050':  # trimf
                if line.employee_id.gender == 'male':
                    total_trimf_male += line.total
                if line.employee_id.gender == 'female':
                    total_trimf_female += line.total
                    
                if line.employee_id.country_id.code == 'SN':
                    total_trimf_n += line.total
                else:
                    total_trimf_nn += line.total
                    
            if line.code == 'C2000':  # cfce
                if line.employee_id.gender == 'male':
                    total_cfce_male += line.total
                if line.employee_id.gender == 'female':
                    total_cfce_female += line.total
                    
                if line.employee_id.country_id.code == 'SN':
                    total_cfce_n += line.total
                else:
                    total_cfce_nn += line.total
                    
            if line.code == 'C1200':  # brut imposable
                if line.employee_id.gender == 'male':
                    total_brut_male += line.total
                if line.employee_id.gender == 'female':
                    total_brut_female += line.total
                    
                if line.employee_id.country_id.code == 'SN':
                    total_brut_n += line.total
                else:
                    total_brut_nn += line.total
                    
        nb_n = sum(value[0] == 'SN' for value in dict.values())
        nb_nn = sum(value[0] != 'SN' for value in dict.values())
        nb_male = sum(value[1] == 'male' for value in dict.values())
        nb_female = sum(value[1] == 'female' for value in dict.values())

        lines_total_male = [{
            'nb_male_count': nb_male,
            'total_brut_male': int(round(total_brut_male)),
            'total_ir_male': int(round(total_ir_male)),
            'total_trimf_male': int(round(total_trimf_male)),
            'total_cfce_male': int(round(total_cfce_male)),
            'total_total_male': int(round(total_ir_male +
                                          total_trimf_male + total_cfce_male)),
        }]

        lines_total_female = [{
            'nb_female_count': nb_female,
            'total_brut_female': int(round(total_brut_female)),
            'total_ir_female': int(round(total_ir_female)),
            'total_trimf_female': int(round(total_trimf_female)),
            'total_cfce_female': int(round(total_cfce_female)),
            'total_total_female': int(round(total_ir_female +
                                            total_trimf_female + total_cfce_female)),
        }]
        
        line_total_n = [{
            'nb_n_count': nb_n,
            'total_brut_n': int(total_brut_n),
            'total_ir_n': int(total_ir_n),
            'total_trimf_n': int(total_trimf_n),
            'total_cfce_n': int(total_cfce_n),
            'total_total_n': int(total_ir_n + total_trimf_n + total_cfce_n)
        }]
        
        line_total_nn = [{
            'nb_nn_count': nb_nn,
            'total_brut_nn': int(total_brut_nn),
            'total_ir_nn': int(total_ir_nn),
            'total_trimf_nn': int(total_trimf_nn),
            'total_cfce_nn': int(total_cfce_nn),
            'total_total_nn': int(total_ir_nn + total_trimf_nn + total_cfce_nn)
        }]

        lines_total = [{
            'total_brut': int(round(total_brut_male + total_brut_female)),
            'total_ir': int(round(total_ir_male + total_ir_female)),
            'total_trimf': int(round(total_trimf_male + total_trimf_female)),
            'total_cfce': int(round(total_cfce_male + total_cfce_female)),
            'total_total': int(round(total_ir_male + total_trimf_male + total_cfce_male +
                                     total_ir_female + total_trimf_female + total_cfce_female)),
        }]

        return {
            'doc_ids': register_ids,
            #'doc_model': 'hr.contribution.register',
            'docs': contrib_registers,
            'data': data,
            'lines_male': lines_total_male,
            'lines_female': lines_total_female,
            'lines_n': line_total_n,
            'lines_nn': line_total_nn,
            'lines_total': lines_total,
            'current_date': now.strftime("%d/%m/%Y"),
            'periode': periode
        }
