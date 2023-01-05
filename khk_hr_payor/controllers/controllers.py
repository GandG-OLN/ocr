# -*- coding: utf-8 -*-
# from odoo import http


# class KhkHrPayor(http.Controller):
#     @http.route('/khk_hr_payor/khk_hr_payor/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/khk_hr_payor/khk_hr_payor/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('khk_hr_payor.listing', {
#             'root': '/khk_hr_payor/khk_hr_payor',
#             'objects': http.request.env['khk_hr_payor.khk_hr_payor'].search([]),
#         })

#     @http.route('/khk_hr_payor/khk_hr_payor/objects/<model("khk_hr_payor.khk_hr_payor"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('khk_hr_payor.object', {
#             'object': obj
#         })
