# -*- coding: utf-8 -*-
# by khk
#import xlwt
import xlsxwriter as xlwt
import base64
from io import StringIO
import time
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import fields, models, api
from odoo.exceptions import Warning


class PayorTransferOrder(models.TransientModel):
    _name = 'payor.transfer.order'
    _description = 'order de virement'

    date_from = fields.Date('Date de la paie', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    print_format = fields.Selection([('pdf', 'PDF'),
                                     ('xls', 'Excel'), ],
                                    default='pdf', string="Format", required=True)
    transfer_data = fields.Char('Name', )
    file_name = fields.Binary('Transfer order', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    def print_report_transfer_order(self):
        datas = {
            'model': 'payor.transfer.order',
            'form': self.read()[0]
        }
        return self.env.ref('khk_hr_payor.transfer_order').report_action([], data=datas)
