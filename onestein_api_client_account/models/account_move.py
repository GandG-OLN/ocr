from datetime import datetime
from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare
from odoo.tests.common import Form


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def get_onestein_api_credit_balance(self):
        if not self.env.user.has_group("account.group_account_invoice"):
            raise AccessError(
                _("You need to be in the 'Billing' group.")
            )

        try:
            return self.env["onestein.api.config"].sudo().get().credit_balance("ocr")
        except (Exception,):
            return -1

    def button_onestein_api_ocr_upload(self):
        self.ensure_one()
        if not self.is_purchase_document():
            raise UserError(_("Only Vendor Bills can be imported by the Onestein API"))

        if self.state != "draft":
            raise UserError(
                _("You can only import data to Vendor Bills in draft status")
            )

        attachment = self._get_attachment_for_onestein_api_ocr()
        if not attachment:
            raise UserError(_("No attachment to be scanned by Onestein API"))

        parsed_data = attachment.sudo()._onestein_api_parse_document()

        if parsed_data.get("document_type") != "invoice":
            raise UserError(_("The result from the Onestein API is not a Vendor Bill"))

        self._update_invoice_from_onestein_api_response(parsed_data)

    def _get_attachment_for_onestein_api_ocr(self):
        self.ensure_one()
        main_attachment = self.message_main_attachment_id
        if main_attachment and (
            main_attachment.mimetype == "application/pdf"
            or main_attachment.mimetype.startswith("image")
        ):
            attachment = self.message_main_attachment_id
        else:
            attachment = self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", self.id),
                    ("mimetype", "=", "application/pdf"),
                ],
                limit=1,
            )
        return attachment

    def _update_invoice_from_onestein_api_response(self, data):
        self.ensure_one()

        dict_lines = data.get("lines", {})
        if isinstance(dict_lines, list) and dict_lines:
            # TODO could line (list) contain more than one item?
            dict_lines = dict_lines[0].get("lineitems")

        currency = self.env["res.currency"].search(
            [("name", "=", data.get("currency"))], limit=1
        )
        invoice_date = (
            datetime.strptime(data.get("date"), "%Y-%m-%dT%H:%M:%S")
            if data.get("date")
            else False
        )
        purchase_date = (
            datetime.strptime(data.get("purchasedate"), "%Y-%m-%d").date()
            if data.get("purchasedate")
            else False
        )
        invoice_date_due = (
            datetime.strptime(data.get("payment_due_date"), "%Y-%m-%dT%H:%M:%S")
            if data.get("payment_due_date")
            else False
        )
        invoice_number = data.get("invoice_number")
        partner = self._onestein_api_ocr_match_partner(data)
        partner_bank = self._onestein_api_ocr_match_partner_bank(partner, data)
        with Form(self) as invoice_form:
            if partner:
                invoice_form.partner_id = partner
            if partner_bank:
                invoice_form.invoice_partner_bank_id = partner_bank
            if currency:
                invoice_form.currency_id = currency
            if invoice_date:
                invoice_form.invoice_date = invoice_date
            if invoice_date_due:
                invoice_form.invoice_date_due = invoice_date_due
            if invoice_number:
                invoice_form.ref = invoice_number

            for item in range(0, len(invoice_form.invoice_line_ids)):
                invoice_form.invoice_line_ids.remove(0)

            for dict_line in dict_lines:
                amount = (
                    dict_line.get("amount") and dict_line["amount"] / 100
                )  # not needed?
                vat_amount = (
                    dict_line.get("vat_amount") and dict_line["vat_amount"] / 100
                )  # not needed?
                sku = dict_line.get("sku")
                product = self.env["product.product"]
                if sku:
                    product = self.env["product.product"].search(
                        [("barcode", "=", sku)], limit=1
                    )
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.account_id = (
                        self.journal_id.default_account_id
                    )
                    invoice_line_form.product_id = product
                    invoice_line_form.name = dict_line.get("title") or dict_line.get(
                        "description"
                    )
                    invoice_line_form.quantity = dict_line.get("quantity")
                    invoice_line_form.price_unit = (
                        dict_line.get("amount_each") and dict_line["amount_each"] / 100
                    )
                    # tax
                    tax = self._onestein_api_ocr_match_line_tax(dict_line)
                    if tax:
                        invoice_line_form.tax_ids.clear()
                        invoice_line_form.tax_ids.add(tax)

    def _onestein_api_ocr_match_line_tax(
        self, dict_line, price_include=False, create_if_not_found=False
    ):
        company_id = self.env.context.get("force_company") or self.env.company.id
        domain = [("company_id", "=", company_id), ("type_tax_use", "=", "purchase")]
        if price_include is False:
            domain.append(("price_include", "=", False))
        elif price_include is True:
            domain.append(("price_include", "=", True))
        # with the code above, if you set price_include=None, it will
        # won't depend on the value of the price_include parameter
        if dict_line["vat_percentage"]:
            domain.append(("description", "ilike", dict_line["vat_percentage"]))
            domain.append(("amount_type", "=", "percent"))
        if dict_line["vat_code"]:
            domain.append(("name", "ilike", dict_line["vat_code"]))
            domain.append(("amount_type", "=", "fixed"))
        taxes = self.env["account.tax"].search(domain)
        for tax in taxes:
            tax_amount = tax.amount  # 'amount' field : digits=(16, 4)
            if not float_compare(
                dict_line["vat_percentage"], tax_amount, precision_digits=4
            ):
                return tax
        if create_if_not_found:
            # TODO
            pass
        return self.env["account.tax"]

    def _onestein_api_ocr_match_partner(self, data, create_if_not_found=False):
        company_id = (
            self.env.context.get("force_company") or self.env.user.company_id.id
        )
        domain = ["|", ("company_id", "=", False), ("company_id", "=", company_id)]
        order = "supplier_rank desc"

        """
        In case OCA module 'partner_coc' is installed, returns the value of
        field 'coc_registration_number'. Otherwise if the CoC number is defined somewhere
        else you should extend this method returning its value.
        """
        if self.env["res.partner"]._fields.get("coc_registration_number") and data.get(
            "merchant_coc_number"
        ):
            coc = data["merchant_coc_number"]
            partner = self.env["res.partner"].search(
                domain + [("coc_registration_number", "=", coc)], limit=1
            )
            if partner:
                return partner
            else:
                pass
                # TODO warning
        if data.get("merchant_country_code"):
            country = self.env["res.country"].search(
                [("code", "=", data["merchant_country_code"])], limit=1
            )
            if country:
                domain += [
                    "|",
                    ("country_id", "=", False),
                    ("country_id", "=", country.id),
                ]
            else:
                pass
                # TODO warning
        if data.get("merchant_vat_number"):
            vat = data["merchant_vat_number"].replace(" ", "").upper()
            partner = self.env["res.partner"].search(
                domain + [("parent_id", "=", False), ("vat", "=", vat)],
                limit=1,
                order=order,
            )
            if partner:
                return partner
            else:
                pass
                # TODO warning

        website_domain = False
        email_domain = False
        if data.get("merchant_email") and "@" in data["merchant_email"]:
            partner = self.env["res.partner"].search(
                domain + [("email", "=ilike", data["merchant_email"])],
                limit=1,
                order=order,
            )
            if partner:
                return partner
            else:
                email_domain = data["merchant_email"].split("@")[1]
        if data.get("merchant_website"):
            urlp = urlparse(data["merchant_website"])
            netloc = urlp.netloc
            if not urlp.scheme and not netloc:
                netloc = urlp.path
            if netloc and len(netloc.split(".")) >= 2:
                website_domain = ".".join(netloc.split(".")[-2:])
        if website_domain or email_domain:
            partner_domain = website_domain or email_domain
            partner = self.env["res.partner"].search(
                domain + [("website", "=ilike", "%" + partner_domain + "%")],
                limit=1,
                order=order,
            )
            # I can't search on email addresses with
            # email_domain because of the emails such as
            # @gmail.com, @yahoo.com that may match random partners
            if not partner and website_domain:
                partner = self.env["res.partner"].search(
                    domain + [("email", "=ilike", "%@" + website_domain)],
                    limit=1,
                    order=order,
                )
            if partner:
                return partner
            else:
                pass
                # TODO warning
        if data.get("merchant_id"):
            partner = self.env["res.partner"].search(
                domain + [("ref", "=", data["merchant_id"])], limit=1, order=order
            )
            if partner:
                return partner
            else:
                pass
                # TODO warning
        if data.get("merchant_name"):
            partner = self.env["res.partner"].search(
                domain + [("name", "=ilike", data["merchant_name"])],
                limit=1,
                order=order,
            )
            if partner:
                return partner
            else:
                pass
                # TODO warning
        if data.get("merchant_phone"):
            partner = self.env["res.partner"].search(
                domain + [("phone", "=", data["merchant_phone"])], limit=1, order=order
            )
            if partner:
                return partner
            else:
                pass
                # TODO warning
        if create_if_not_found:
            # TODO
            pass
        return self.env["res.partner"]

    def _onestein_api_ocr_match_partner_bank(self, partner, data, create_if_not_found=False):
        if not partner:
            return self.env["res.partner.bank"]
        if data.get("merchant_bank_account_number"):
            iban = data["merchant_bank_account_number"].replace(" ", "").upper()
            company_id = self.env.context.get("force_company") or self.env.company.id
            bankaccount = self.env["res.partner.bank"].search(
                [
                    ("sanitized_acc_number", "=", iban),
                    ("partner_id", "=", partner.id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            if bankaccount:
                return bankaccount
            else:
                pass
                # TODO warning
        if create_if_not_found:
            # TODO
            pass
        return self.env["res.partner.bank"]

    @api.depends('message_main_attachment_id')
    def auto_upload_onestein_api(self):
        for move in self.filtered(
            lambda m:
            m.invoice_source_email and
            m.partner_id and
            m.message_main_attachment_id and
            m.is_purchase_document() and
            m.company_id.invoice_auto_onestein_api_upload
        ):
            move.button_onestein_api_ocr_upload()
