import time
from datetime import datetime, date, time as t
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)

class BonusRuleInput(models.Model):
    _inherit = 'hr.payslip'

#    state = fields.Selection([
#        ('draft', 'Draft'),
#        ('verify', 'Waiting'),
#        ('validate', 'Validé'),
#        ('done', 'clôturer'),
#        ('cancel', 'Rejected'),
#    ])
    nb_part_of_payslip = fields.Float(string="Nb part", compute="_get_nb_part_of_payslip", states={'done': [('readonly', True)]}, store=True)
    payslip_count_yearly = fields.Integer('Nb payslip yearly', compute="_get_payslip_count_yearly")
    year = fields.Char(string="year", compute='_get_year', store=True)
    holiday_of_payslip = fields.Float(default=0)
    #net_salary = fields.Float()    
        

    @api.depends('date_from')
    def _get_year(self):
        """ for recovering easyly the year of payslip"""
        for payslip in self:
            payslip.year = payslip.date_from.year

    @api.depends('employee_id')
    def _get_payslip_count_yearly(self):
        for payslip in self:
            year = payslip.date_from.year
            count = self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id),('year', '=', year)])
            payslip.payslip_count_yearly = len(count)

    @api.depends('employee_id')
    def _get_nb_part_of_payslip(self):
        for payslip in self:
            if payslip.employee_id:
                payslip.nb_part_of_payslip = payslip.employee_id.ir


    @api.model
    def create(self, vals):
        res = super(BonusRuleInput, self).create(vals)
        if not res.credit_note:
            cr = self._cr
            if res.contract_id.state == 'open':
                self.env.cr.execute("SELECT date_from, date_to FROM hr_payslip WHERE employee_id = %s and year = %s",
                                (res.employee_id.id, res.year))
                date_from_to = self.env.cr.fetchall()
                exist = [item for item in date_from_to if item[0].month == res.date_from.month]
                if exist:
                    raise ValidationError(_(str(res.name)+" existe déjà"))
            else:
                raise ValidationError(_("Le contrat "+ str(res.contract_id.name)+ "n'est pas en cours"))

        return res

#    def action_payslip_validate(self):
#        for payslip in self:
#            if not payslip.number:
#                payslip.compute_sheet()
#            for line in payslip.line_ids:
#                if line.code == "C1060":
#                    self.env['hr.contract'].reinit(contract_ids)
#                    payslip.contract_id.reinit()
#                    break

#            return payslip.write({'state': 'validate'})


    def get_worked_days_per_year(self,employee_id, year):
        worked_days_obj = self.env['employee.worked.days'].search([('employee_id', '=', employee_id),('year', '=', year)])
        if worked_days_obj.exists():
            return worked_days_obj[0].worked_days
        else:
            return 0

    def action_payslip_done(self):
        val = super(BonusRuleInput, self).action_payslip_done()
        for payslip in self:
            if payslip.worked_days_line_ids[0].number_of_days != 0:
                #update or create the worked days in this year
                worked_days_obj = payslip.env['employee.worked.days'].search([('employee_id', '=', payslip.employee_id.id),('year', '=', payslip.date_from.year)])
                if worked_days_obj.exists():
                    worked_days_obj[0].write({
                        'worked_days': worked_days_obj[0].worked_days + payslip.worked_days_line_ids[0].number_of_days
                        })
                else:
                    self.env['employee.worked.days'].create({
                    'year': payslip.date_from.year,
                    'worked_days': payslip.worked_days_line_ids[0].number_of_days,
                    'employee_id': payslip.employee_id.id
                })
                provision_conges = 0.0
                provision_fin_contrat = 0.0
                provision_conges += sum(line.total for line in payslip.line_ids if line.code == 'C1150')
                provision_fin_contrat += sum(line.total for line in payslip.line_ids if line.code == 'C1160')
                payslip.contract_id._get_droit(provision_conges, provision_fin_contrat)
                
                for line in payslip.line_ids:
                    if line.code == "C1060":
                        payslip.contract_id.reinit()
                        break
                
        return val

    def update_recompute_ir(self):
        server_dt = DEFAULT_SERVER_DATE_FORMAT
        for payslip in self:
            year = datetime.strptime(str(payslip.date_from), server_dt).year

            ir_changed = 0
            two_last_payslip = self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id)], order="id desc", limit=2)
            # compute ir recal monthly
            if len(two_last_payslip) > 1:
                if two_last_payslip[1].nb_part_of_payslip != payslip.employee_id.ir:
                    ir_changed = 1
                    for line in self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id)], order="id desc", limit=12):
                        if datetime.strptime(str(line.date_from), server_dt).year == year:
                            cumul_tranche_ipm = 0.0
                            deduction = 0.0
                            payslip_line_ids = self.env['hr.payslip.line'].search([('slip_id', '=', line.id)])
                            cumul_tranche_ipm += sum(
                                payslip_line.total for payslip_line in payslip_line_ids if payslip_line.code == "C2110")

                            for payslip_line in payslip_line_ids:
                                if payslip_line.code == "C2150":
                                    obj_empl = self.env['hr.employee'].browse(payslip.employee_id.id)
                                    if obj_empl:
                                        if payslip.employee_id.ir == 1:
                                            deduction = 0.0

                                        if payslip.employee_id.ir == 1.5:
                                            if cumul_tranche_ipm * 0.1 < 8333:
                                                deduction = 8333
                                            elif cumul_tranche_ipm * 0.1 > 25000:
                                                deduction = 25000
                                            else:
                                                deduction = cumul_tranche_ipm * 0.1

                                        if payslip.employee_id.ir == 2:
                                            if cumul_tranche_ipm * 0.15 < 16666.66666666667:
                                                deduction = 16666.66666666667
                                            elif cumul_tranche_ipm * 0.15 > 54166.66666666667:
                                                deduction = 54166.66666666667
                                            else:
                                                deduction = cumul_tranche_ipm * 0.15

                                        if payslip.employee_id.ir == 2.5:
                                            if cumul_tranche_ipm * 0.2 < 25000:
                                                deduction = 25000
                                            elif cumul_tranche_ipm * 0.2 > 91666.66666666667:
                                                deduction = 91666.66666666667
                                            else:
                                                deduction = cumul_tranche_ipm * 0.2

                                        if payslip.employee_id.ir == 3:
                                            if cumul_tranche_ipm * 0.25 < 33333.33333333333:
                                                deduction = 33333.33333333333
                                            elif cumul_tranche_ipm * 0.25 > 137500:
                                                deduction = 137500
                                            else:
                                                deduction = cumul_tranche_ipm * 0.25

                                        if payslip.employee_id.ir == 3.5:
                                            if cumul_tranche_ipm * 0.3 < 41666.66666666667:
                                                deduction = 41666.66666666667
                                            elif cumul_tranche_ipm * 0.3 > 169166.6666666667:
                                                deduction = 169166.6666666667
                                            else:
                                                deduction = cumul_tranche_ipm * 0.3

                                        if payslip.employee_id.ir == 4:
                                            if cumul_tranche_ipm * 0.35 < 50000:
                                                deduction = 50000
                                            elif cumul_tranche_ipm * 0.35 > 207500:
                                                deduction = 207500
                                            else:
                                                deduction = cumul_tranche_ipm * 0.35

                                        if payslip.employee_id.ir == 4.5:
                                            if cumul_tranche_ipm * 0.4 < 58333.33333:
                                                deduction = 58333.33333
                                            elif cumul_tranche_ipm * 0.4 > 229583.3333:
                                                deduction = 229583.3333
                                            else:
                                                deduction = cumul_tranche_ipm * 0.4

                                        if payslip.employee_id.ir == 5:
                                            if cumul_tranche_ipm * 0.45 < 66666.66667:
                                                deduction = 66666.66667
                                            elif cumul_tranche_ipm * 0.45 > 265000:
                                                deduction = 265000
                                            else:
                                                deduction = cumul_tranche_ipm * 0.45

                                        if cumul_tranche_ipm - deduction > 0:
                                            ir_val_recal = cumul_tranche_ipm - deduction
                                        else:
                                            ir_val_recal = 0
                                        # update ir_recal
                                        obj = self.env['hr.payslip.line'].search(
                                            [('code', '=', payslip_line.code), ('slip_id', '=', line.id)], limit=1)
                                        if obj:
                                            obj.write({'amount': round(ir_val_recal)})
            # end compute ir_recal

            ir_payslip = 0.0
            net_payslip = 0.0
            ir_payslip += sum(payslip_line.total for payslip_line in payslip.line_ids if
                              payslip_line.code == "C2140")
            net_payslip += sum(payslip_line.total for payslip_line in payslip.line_ids if
                               payslip_line.code == "C5000")

            # update the ir_regul of current payslip by doing sum(ir) - sum(ir_recal) of previous payslip
            if ir_changed == 1:
                # in case of regul monthly
                cumul_ir = 0.0
                cumul_ir_recal = 0.0
                for line in self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id)]):
                    if datetime.strptime(str(line.date_from), server_dt).year == year:
                        cumul_ir += sum(payslip_line.total for payslip_line in line.line_ids if
                                         payslip_line.code == "C2140")
                        cumul_ir_recal += sum(
                            payslip_line.total for payslip_line in line.line_ids if
                            payslip_line.code == "C2150")
                        # update ir regul rule
                        [obj.write({'amount': round(cumul_ir - cumul_ir_recal)}) for obj in
                         payslip.line_ids if obj.code == "C2160"]
                # update ir_fin
                [obj.write({'amount': round(ir_payslip - (cumul_ir - cumul_ir_recal))}) for obj in
                 payslip.line_ids if obj.code == "C2170"]
            else:
                [obj.write({'amount': round(ir_payslip)}) for obj in
                payslip.line_ids if obj.code == "C2170"]
   
             # in case of regul yearly
            regul_annuel = [obj for obj in payslip.line_ids if obj.code == 'C2163'] # recover year regul rule
            if len(regul_annuel) > 0: # check if year rugul rule exist
                [obj.write({'amount': round(ir_payslip - regul_annuel[0].total)}) for obj in
                payslip.line_ids if obj.code == "C2170"]
                    
            # defalquer ir_fin du net
            ir_fin = 0.0
            ir_fin += sum(payslip_line.total for payslip_line in payslip.line_ids if
                          payslip_line.code == "C2170")
            [obj.write({'amount': round(net_payslip - ir_fin)}) for obj in
            payslip.line_ids if obj.code == "C5000"]

            # compute_loan_balance
            if payslip.contract_id.motif:
                """get the amount of unpaid loan"""
                val_loan_balance = payslip.loan_balance()
                if val_loan_balance != 0:
                    [payslip_line.write({'amount': round(net_payslip - val_loan_balance)}) for payslip_line in
                     payslip.line_ids if payslip_line.code == "C5000"]

    def get_inputs(self, contract_ids, date_from, date_to):
        res = super(BonusRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        for bonus in self.contract_id.bonus:
            if not ((bonus.date_to < self.date_from or bonus.date_from > self.date_to) or
                    (bonus.date_to <= self.date_from or bonus.date_from >= self.date_to)):
                bonus_line = {
                    'name': str(bonus.salary_rule.name),
                    'code': bonus.salary_rule.code,
                    'contract_id': self.contract_id.id,
                    'amount': bonus.amount,
                }
                res += [bonus_line]
        return res

    def compute_sheet(self):
        for payslip in self:
            if payslip.state == "draft":
                if payslip.contract_id.date_end and payslip.date_from > payslip.contract_id.date_end:
                    raise ValidationError(
                        _("La date du bulletin ne peut pas être supérieur à la date de sortie du contract"))
                
                number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
                # delete old payslip lines
                payslip.line_ids.unlink()
                # set the list of contract for which the rules have to be applied
                # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = payslip.contract_id.ids or \
                    self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
                lines = [(0, 0, line) for line in self.get_payslip_lines(contract_ids, payslip.id)] #  get payslip defined by cybrocys
                payslip.write({
                    'line_ids': lines,
                    'number': number,
                    'holiday_of_payslip': payslip.contract_id.nbj_pris})
                payslip.update_recompute_ir()

    @api.model
    def get_payslip_lines(self, contract_ids, payslip_id):
        """defined by cybrosys we use this function"""
        for record in self:
            def _sum_salary_rule_category(localdict, category, amount):
                if category.parent_id:
                    localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
                if category.code in localdict['categories'].dict:
                    amount += localdict['categories'].dict[category.code]
                localdict['categories'].dict[category.code] = amount
                return localdict

            class BrowsableObject(object):
                def __init__(record, employee_id, dict, env):
                    record.employee_id = employee_id
                    record.dict = dict
                    record.env = env

                def __getattr__(record, attr):
                    return attr in record.dict and record.dict.__getitem__(attr) or 0.0

            class InputLine(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""
                            SELECT sum(amount) as sum
                            FROM hr_payslip as hp, hr_payslip_input as pi
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                          (record.employee_id, from_date, to_date, code))
                    return self.env.cr.fetchone()[0] or 0.0

            class WorkedDays(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def _sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""
                            SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                          (record.employee_id, from_date, to_date, code))
                    return record.env.cr.fetchone()

                def sum(record, code, from_date, to_date=None):
                    res = record._sum(code, from_date, to_date)
                    return res and res[0] or 0.0

                def sum_hours(record, code, from_date, to_date=None):
                    res = record._sum(code, from_date, to_date)
                    return res and res[1] or 0.0

            class Payslips(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                                    FROM hr_payslip as hp, hr_payslip_line as pl
                                    WHERE hp.employee_id = %s AND hp.state = 'done'
                                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                          (record.employee_id, from_date, to_date, code))
                    res = record.env.cr.fetchone()
                    return res and res[0] or 0.0

            # we keep a dict with the result because a value can be overwritten by another rule with the same code
            result_dict = {}
            rules_dict = {}
            worked_days_dict = {}
            inputs_dict = {}
            blacklist = []
            payslip = record.env['hr.payslip'].browse(payslip_id)
            for worked_days_line in payslip.worked_days_line_ids:
                worked_days_dict[worked_days_line.code] = worked_days_line
            for input_line in payslip.input_line_ids:
                inputs_dict[input_line.code] = input_line

            categories = BrowsableObject(payslip.employee_id.id, {}, record.env)
            inputs = InputLine(payslip.employee_id.id, inputs_dict, record.env)
            worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, record.env)
            payslips = Payslips(payslip.employee_id.id, payslip, record.env)
            rules = BrowsableObject(payslip.employee_id.id, rules_dict, record.env)

            baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                             'inputs': inputs}
            # get the ids of the structures on the contracts and their parent id as well
            contracts = record.env['hr.contract'].browse(contract_ids)
            structure_ids = contracts.get_all_structures()
            # get the rules of the structure and thier children
            rule_ids = record.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
            #rule_ids = []
            #for rule in structure_id.rule_ids:
            #    rule_ids.append((rule.id, rule.sequence))
            # run the rules by sequence
            # Appending bonus rules from the contract
            for contract in contracts:
                for bonus in contract.bonus:
                    if not ((bonus.date_to < record.date_from or bonus.date_from > record.date_to)
                            or (bonus.date_to <= record.date_from or bonus.date_from >= record.date_to)):
                        _logger.info('LA VALEUR DE WORK DAYS ' + str(worked_days.WORK100))
                        if bonus.salary_rule.is_prorata:
                            bonus.salary_rule.write({
                                'amount_fix': round(bonus.amount * (worked_days.WORK100.number_of_days) / 30), })
                        else:
                            bonus.salary_rule.write({'amount_fix': round(bonus.amount)})
                        rule_ids.append((bonus.salary_rule.id, bonus.salary_rule.sequence))

            sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
            sorted_rules = record.env['hr.salary.rule'].browse(sorted_rule_ids)

            brut_of_current_payslip = 0.0
            brut_imposable_of_current_payslip = 0.0
            ir_of_current_payslip = 0.0
            
            for contract in contracts:
                employee = contract.employee_id
                localdict = dict(baselocaldict, employee=employee, contract=contract)
                for rule in sorted_rules:
                    key = rule.code + '-' + str(contract.id)
                    localdict['result'] = None
                    localdict['result_qty'] = 1.0
                    localdict['result_rate'] = 100
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        # compute the amount of the rule
                        amount, qty, rate = rule._compute_rule(localdict)

                        # 
                        if rule.category_id.code in ['INDM', 'BASE', 'NOIMP', 'HS']:
                            brut_of_current_payslip += amount
                        # get brut imposable of current payslip
                        if rule.code == 'C1200':
                            brut_imposable_of_current_payslip = amount
                        # get ir of current payslip
                        if rule.code == 'C2140':
                            ir_of_current_payslip += amount

                        if rule.code == 'C1120':  # indemnite de retraite
                            amount = payslip.compute_retirement_balance(brut_of_current_payslip)
                        elif rule.code == 'C1145':  # indemnite de licenciement
                            amount = payslip.compute_retirement_balance(brut_of_current_payslip)
                        elif rule.code == 'C1146':  # indemnite de deces
                            amount = payslip.compute_retirement_balance(brut_of_current_payslip)
                        elif rule.code == 'C1147':  # provision de retraite
                            amount = payslip.compute_provision_retraite(brut_of_current_payslip)
                        elif rule.code == 'C2161': # get ir annuel
                            amount = payslip.get_ir_annuel(brut_imposable_of_current_payslip)
                        elif rule.code == 'C2162': # get cumul ir
                            amount = payslip.get_cumul_ir(ir_of_current_payslip)
                        elif rule.code == 'C2048': # get the trimf annual
                            amount = payslip.get_annual_trimf()
                        elif rule.code == 'C2047': # get cumul trimf
                            amount = payslip.get_cumul_trimf(brut_imposable_of_current_payslip)

                        # check if there is already a rule computed with that code
                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                        # set/overwrite the amount computed for this rule in the localdict
                        tot_rule = amount * qty * rate / 100.0
                        localdict[rule.code] = tot_rule
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                        # create/overwrite the rule in the temporary results
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_percentage': rule.amount_percentage,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                        }
#                     else:
#                         # blacklist this rule and its children
#                         blacklist += [id for id, seq in rule._recursive_search_of_rules()]
                payslips.contract_id._get_duration()

            return [value for code, value in result_dict.items()]

    # for changing the number
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), t.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), t.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            nb_day_leave = 0
            nb_hour_leave = 0
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.name or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, t.min)),
                    tz.localize(datetime.combine(day, t.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours
                    nb_day_leave = current_leave_struct['number_of_days']
                    nb_hour_leave = current_leave_struct['number_of_hours']

            # compute worked days
            work_data = contract.employee_id._get_work_days_data(day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': 30 - nb_day_leave,
                'number_of_hours': 173.33 - nb_hour_leave,
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())
        return res

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    total = fields.Float(compute='_compute_total', string='Total', store='True')
    fonction_employee = fields.Char(string='Fonction Employe', related='employee_id.job_id.name', store=True)
    categorie_employee = fields.Char(string="Categorie Employe", related='employee_id.contract_id.convention_id.name',
                                     store=True)
    payslip_date_from = fields.Date(string="Date de debut", related="slip_id.date_from", store=True)
    payslip_date_to = fields.Date(string="Date de fin", related="slip_id.date_to", store=True)
    year = fields.Char(string="year", compute='_get_year', store=True)

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.depends('payslip_date_to')
    def _get_year(self):
        """ for recovering easyly the year of payslip line in dads report """
        for line in self:
            line.year = line.payslip_date_to.year