from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_auto_onestein_api_upload = fields.Boolean(
        string="Automatically upload invoices to Onestein API"
    )
