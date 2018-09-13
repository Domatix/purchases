##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from odoo import models, fields, api


class SaleForecast(models.Model):
    _inherit = 'sale.forecast'

    @api.multi
    def _compute_request_count(self):
        for record in self:
            purchase_forecast_id = self.env['purchase.forecast'].search([
                ('sale_forecast_id', '=', record.id)])
            if not purchase_forecast_id:
                record.purchase_forecast_count = '0'
            else:
                record.purchase_forecast_count = len(purchase_forecast_id)

    purchase_forecast_count = fields.Char(compute='_compute_request_count',
                                          type='integer',
                                          string="Photo Requests")

    @api.multi
    def create_purchase_forecast(self):
        purchase_forecast_obj = self.env['purchase.forecast']

        def get_purchase_materials(product, qty):
            materials = []
            if product.purchase_ok:
                materials.append({
                    'product_id': product,
                    'product_uom_qty': qty,
                    'used_in': False
                })
            elif product.bom_ids:
                for bom_line in product.bom_ids[0].bom_line_ids:
                    if bom_line.product_id.purchase_ok:
                        materials.append({
                            'product_id': bom_line.product_id,
                            'product_uom_qty': bom_line.product_qty * qty,
                            'used_in': product,
                        })
                    else:
                        materials += get_purchase_materials(
                                                    bom_line.product_id,
                                                    bom_line.product_qty * qty)
            return materials
        for record in self:
            purchase_forecast_id = self.env['purchase.forecast'].search([
                ('sale_forecast_id', '=', record.id)])
            if purchase_forecast_id:

                return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.forecast',
                    'res_id': purchase_forecast_id.id,
                    'type': 'ir.actions.act_window',
                    }
            vals = {'date_to': record.date_to,
                    'date_from': record.date_from,
                    'name': record.name,
                    # 'warehouse_id': record.warehouse_id.id,
                    'sale_forecast_id': record.id}
            purchase_forecast_id = purchase_forecast_obj.create(vals)

            for line in record.forecast_lines:
                materials = get_purchase_materials(line.product_id, line.qty)
                for material in materials:
                    used_mat = material['used_in']
                    used_in = used_mat.id if used_mat else False
                    purchase_forecast_id.write({'forecast_lines': [(0, 0, {
                                    'product_id': material['product_id'].id,
                                    'used_in': used_in,
                                    'unit_price': line.unit_price,
                                    'qty': material['product_uom_qty'],
                                    })],
                                    })
            purchase_forecast_id.update_suppliers()
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.forecast',
            'res_id': purchase_forecast_id.id,
            'type': 'ir.actions.act_window',
            }
