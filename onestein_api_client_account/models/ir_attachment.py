import base64
import json
from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    parsed_content = fields.Text(
        'Parsed Content', prefetch=False
    )

    def register_as_main_attachment(self, force=True):
        self.ensure_one()
        super().register_as_main_attachment(force=force)
        if self.res_model and self.res_model == 'account.move':
            move = self.env[self.res_model].browse(self.res_id)
            move.auto_upload_onestein_api()

    def _onestein_api_parse_document(self):
        self.ensure_one()
        if self.parsed_content:
            return json.loads(self.parsed_content)
        res = self.env["onestein.api.config"].get().ocr_invoice(
           self.datas.decode("utf-8")
        )
        self.parsed_content = json.dumps(res["parsed"])
        self.index_content = res["raw_text"]
        return res["parsed"]
