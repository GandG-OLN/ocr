# -*- coding: utf-8 -*-
# by khk
import xlwt
import base64
from io import StringIO
import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models, api
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class PayorPayslipLinesCotisationIpres(models.TransientModel):
    _name = 'payor.payslip.lines.cotisation.ipres'
    _description = 'cotisation ipres modele wizard'

    date_from = fields.Date('Date de debut', required=True,
                            default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date de fin', required=True,
                          default=lambda *a: str(
                              datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def print_report_ipres(self):
        #active_ids = self.env.context.get('active_ids', [])
        datas = {
            'model': 'payor.payslip.lines.cotisation.ipres',
            'form': self.read()[0]
        }
            
        return self.env.ref('khk_hr_payor.cotisation_ipres').report_action(self, data=datas)