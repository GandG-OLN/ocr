from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_auto_onestein_api_upload = fields.Boolean(
        related='company_id.invoice_auto_onestein_api_upload',
        readonly=False
    )
