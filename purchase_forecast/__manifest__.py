# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 Domatix (http://www.domatix.com)
#                       info <email@domatix.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": 'Purchase Forecast',
    "summary": 'Forecast',
    "version": "11.0.1.0.0",
    "depends": [
        "purchase",
        "sale_forecast",
    ],
    "license": "AGPL-3",
    "author": "Carlos Martínez <carlos@domatix.com>, "
              "Nacho Serra <nacho.serra@domatix.com>, "
              "Nacho HM <nacho@domatix.com>",
    "category": "MPS",
    "website": "https://www.domatix.com",
    "data":  ["security/ir.model.access.csv",
              "wizard/purchase_forecast_load_view.xml",
              "views/purchase_view.xml",
              "views/sale_view.xml"],
    "installable": True,
}
