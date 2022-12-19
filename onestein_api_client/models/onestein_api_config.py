import requests
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from requests.exceptions import HTTPError


class OnesteinAPIConfig(models.Model):
    _name = 'onestein.api.config'

    name = fields.Char(
        required=True
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        default=lambda self: self.env.companies
    )
    api_key = fields.Char(
        required=True
    )

    @api.model
    def _base_url(self):
        return "https://api.onestein.eu/api/v1"

    def get(self):
        domain = [
            "|",
            ("company_ids", "in", self.env.companies.ids),
            ("company_ids", "=", False),
        ]
        configs = self.search(domain, order="id desc")
        if not configs:
            raise UserError(_("No Onestein API configuration found"))
        configs_with_company = configs.filtered(lambda c: c.company_ids)
        if configs_with_company:
            return fields.first(configs_with_company)
        return fields.first(configs)

    def _request(self, method, url, **kwargs):
        self.ensure_one()
        headers = {
            "API-KEY": self.api_key
        }
        if "headers" in kwargs:
            headers.update(kwargs.get("headers", {}))
            kwargs.pop("headers")
        full_url = "%s%s%s" % (self._base_url(), "" if url.startswith("/") else "/", url)

        response = requests.request(
            method=method,
            url=full_url,
            headers=headers,
            **kwargs
        )
        res = response.json()
        if not response.ok:
            message = re.sub('<[^<]+?>', '', res.get("description", res["name"]))
            if response.status_code == 400:
                raise ValidationError(message)
            raise HTTPError(message, response=response)

        return res

    def credit_balance(self, credit_type):
        res = self._request("GET", "/credit/%s" % credit_type)
        return res["result"]
