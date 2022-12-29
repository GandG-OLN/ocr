# -*- coding: utf-8 -*-
# by khk
import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models, api


class PayorDeclarationRetenues(models.TransientModel):
    _name = 'payor.declaration.retenues'
    _description = 'declarations des retenues a la source sur les salaires'

    date_from = fields.Date('Date de debut', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date de fin', required=True, default=lambda *a: str(
        datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def print_report(self):
        active_ids = self.env.context.get('active_ids', [])
        datas = {
            'ids': active_ids,
            'model': 'payor.declaration.retenues',
            'form': self.read()[0]
        }
        return self.env.ref('khk_hr_payor.declaration_retenues').report_action([], data=datas)
