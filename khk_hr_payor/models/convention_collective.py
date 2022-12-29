# -*- coding: utf-8 -*-
from odoo import models, fields


class CoventionCollective(models.Model):
    _name = "convention.collective"
    _description = "convention collective"

    name = fields.Char('Nom convention')
    line_ids = fields.One2many('convention.collective.line', 'conv_id', 'Ligne de convention')


class CoventionCollectiveLine(models.Model):
    _name = "convention.collective.line"
    _description = "Ligne de conventions collective"

    name = fields.Char('Libelle')
    code = fields.Char('Code Grille')
    taux_h = fields.Float('Taux horaire')
    wage = fields.Float('Salaire brut')
    conv_id = fields.Many2one('convention.collective', 'convention')
