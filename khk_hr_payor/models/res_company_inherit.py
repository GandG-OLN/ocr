from odoo import models, fields


class PayorResCompanyInherit(models.Model):
    _inherit = 'res.company'

    nbj_alloue = fields.Float(string="Nombre de jour alloue", default="2.0")
    nbj_travail = fields.Float(string="Nombre de jour de travail", default="30")