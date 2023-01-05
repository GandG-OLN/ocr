import json

from odoo import _, api, fields, models


class OnesteinAPIConfig(models.Model):
    _inherit = 'onestein.api.config'

    def ocr_invoice(self, document):
        res = self._request("POST", "/ocr/invoice", data=json.dumps({
            "document": document
        }), headers={
            "Content-Type": "application/json"
        })
        return res
