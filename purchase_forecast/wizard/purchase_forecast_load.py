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
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from odoo import models, fields, api


class ForecastLoad(models.TransientModel):
    _name = 'forecast.sale.load'
    _description = 'Load forecast from existing sale forecast'

    def _get_default_forecast(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        forecast = False
        if model == 'purchase.forecast':
            forecast = record.id
        return forecast

    forecast_id = fields.Many2one(
        comodel_name='purchase.forecast',
        string='Purchase Forecast',
        default=_get_default_forecast)

    forecast_sales = fields.Many2one(
        comodel_name='sale.forecast',
        string='Sale Forecast')

    factor = fields.Float(string="Factor", default=1)

    @api.multi
    def button_confirm(self):
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

        for line in self.forecast_sales.forecast_lines:
            forecast_line_obj = self.env['purchase.forecast.line']
            materials = get_purchase_materials(
                line.product_id,
                int(line.qty * self.factor)
                )
            for material in materials:
                seller = material['product_id']._select_seller(
                    quantity=material['product_uom_qty'],
                    uom_id=material['product_id'].uom_po_id
                    )

                if not seller:
                    partner = False
                else:
                    partner = seller.name.id
                unit_price = seller.price if seller else 0.0
                used_mat = material['used_in']
                used_in = used_mat.id if used_mat else False
                line_dest = forecast_line_obj.search([
                    ('forecast_id', '=', self.forecast_id.id),
                    ('product_id', '=', material['product_id'].id),
                    ('used_in', '=', used_in)
                    ])
                if line_dest:
                    line_dest.qty += material['product_uom_qty']
                    line_dest.update_supplier()
                else:
                    self.forecast_id.write({'forecast_lines': [(0, 0, {
                        'product_id': material['product_id'].id,
                        'used_in': used_in,
                        'unit_price': unit_price,
                        'qty':  material['product_uom_qty'],
                        'partner_id': partner,
                    })],
                    })


class SelfPurchaseForecastLoad(models.TransientModel):
    _name = 'self.purchase.forecast.load'
    _description = 'Load purchase forecast from existing purchase forecast'

    def _get_default_forecast(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        forecast = False
        if model == 'purchase.forecast':
            forecast = record.id
        return forecast

    forecast_id = fields.Many2one(
        comodel_name='purchase.forecast',
        string='Purchase Forecast',
        default=_get_default_forecast)

    forecast_purchase = fields.Many2one(
        comodel_name='purchase.forecast',
        string='Purchase Forecast')

    factor = fields.Float(string="Factor", default=1)

    @api.multi
    def button_confirm(self):
        forecast_line_obj = self.env['purchase.forecast.line']
        for line in self.forecast_purchase.forecast_lines:
            used_in = line.used_in.id if line.used_in else False
            line_dest = forecast_line_obj.search([
                ('forecast_id', '=', self.forecast_id.id),
                ('product_id', '=', line.product_id.id),
                ('used_in', '=', used_in)
                ])
            if line_dest:
                line_dest.qty += int(line.qty * self.factor)
                line_dest.update_supplier()
            else:
                self.forecast_id.write({'forecast_lines': [(0, 0, {
                    'product_id': line.product_id.id,
                    'used_in': used_in,
                    'unit_price': line.unit_price,
                    'qty': int(line.qty * self.factor),
                    'partner_id': line.partner_id.id,
                })],
                })


class PurchaseForecastLoadFromSale(models.TransientModel):
    _name = 'purchase.forecast.load.from.sale'
    _description = 'Load purchase forecast'

    def _get_default_forecast(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        forecast = False
        if model == 'sale.forecast':
            forecast = record.id
        return forecast

    forecast_id = fields.Many2one(
        comodel_name='sale.forecast',
        string='Sale Forecast',
        default=_get_default_forecast)

    forecast_purchase = fields.Many2one(
        comodel_name='purchase.forecast',
        string='Purchase Forecast')

    @api.multi
    def button_confirm(self):
        for line in self.forecast_purchase.forecast_lines:
            forecast_line_obj = self.env['sale.forecast.line']
            line_dest = forecast_line_obj.search([
                ('forecast_id', '=', self.forecast_id.id),
                ('partner_id', '=', line.partner_id.id),
                ('product_id', '=', line.product_id.id)
                ])
            if line_dest:
                line_dest.unit_price = (line_dest.unit_price * line_dest.qty
                                        + line.unit_price * line.qty) / (
                    line_dest.qty + line.qty)

                line_dest.qty += line.qty
            else:
                self.forecast_id.write({'forecast_lines': [(0, 0, {
                    'product_id': line.product_id.id,
                    'unit_price': line.unit_price,
                    'qty': line.qty,
                    'subtotal': line.subtotal,
                    'partner_id': line.partner_id.id,
                    })],
                })


class PurchaseSaleForecastLoad(models.TransientModel):

    _name = 'purchase.sale.forecast.load'
    _description = 'Load sales for purchase forecast'

    def _get_default_partner(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        partner = False
        if model == 'sale.order':
            partner = record.partner_id
        return partner

    def _get_default_forecast(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        forecast = False
        if model == 'purchase.forecast':
            forecast = record.id
        return forecast

    def _get_default_sale(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        sale = False
        if model == 'sale.order':
            sale = record.id
        return sale

    def _get_default_date_from(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        date_from = False
        if model == 'sale.order':
            date_from = record.date_order
        elif model == 'purchase.forecast':
            reg_date = record.date_from
            cur_year = fields.Date.from_string(reg_date).year
            date_from = fields.Date.from_string(reg_date).replace(
                year=cur_year-1)
        return date_from

    def _get_default_date_to(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        date_to = False
        if model == 'sale.order':
            date_to = record.date_order
        elif model == 'purchase.forecast':
            reg_date = record.date_to
            cur_year = fields.Date.from_string(reg_date).year
            date_to = fields.Date.from_string(reg_date).replace(
                year=cur_year-1)
        return date_to

    partner_id = fields.Many2one("res.partner", string="Partner",
                                 default=_get_default_partner)
    date_from = fields.Date(string="Date from", default=_get_default_date_from)
    date_to = fields.Date(string="Date to", default=_get_default_date_to)
    sale_id = fields.Many2one("sale.order", "Sale",
                              default=_get_default_sale)
    forecast_id = fields.Many2one("purchase.forecast", "Forecast",
                                  default=_get_default_forecast)
    product_categ_id = fields.Many2one("product.category", string="Category")
    product_tmpl_id = fields.Many2one("product.template", string="Template")
    product_id = fields.Many2one("product.product", string="Product")

    factor = fields.Float(string="Factor", default=1)

    @api.onchange('sale_id')
    def sale_onchange(self):
        if self.sale_id:
            self.partner_id = self.sale_id.partner_id.id
            self.date_from = self.sale_id.date_order
            self.date_to = self.sale_id.date_order

    @api.onchange('forecast_id')
    def forecast_onchange(self):
        if self.forecast_id:
            from_date = self.forecast_id.date_from
            to_date = self.forecast_id.date_to
            f_cur_year = fields.Date.from_string(from_date).year
            t_cur_year = fields.Date.from_string(to_date).year
            date_from = fields.Date.from_string(from_date).replace(
                year=f_cur_year-1)
            date_to = fields.Date.from_string(to_date).replace(
                year=t_cur_year-1)
            self.date_from = date_from
            self.date_to = date_to

    @api.multi
    def match_purchase_forecast(self, sales, factor):
        self.ensure_one()
        res = {}
        for sale in sales:
            product = sale['product_id']
            used_in = sale['used_in']
            product = self.env['product.product'].browse(sale['product_id'])
            seller = product._select_seller(
                quantity=sale['product_uom_qty'],
                uom_id=product.uom_po_id
                )

            if not seller:
                partner = False
            else:
                partner = seller.name.id
            if partner not in res:
                res[partner] = {}
            if product not in res[partner]:
                res[partner][product] = {}
            if used_in not in res[partner][product]:
                res[partner][product][used_in] = {'qty': 0.0, 'amount': 0.0}
            product_dict = res[partner][product][used_in]
            sum_qty = product_dict['qty'] + sale['product_uom_qty'] * factor
            sum_subtotal = (product_dict['amount'] +
                            sale['price_subtotal'])
            product_dict['qty'] = sum_qty
            product_dict['amount'] = sum_subtotal
        return res

    @api.multi
    def get_purchase_forecast_lists(self, forecast):
        sale_line_obj = self.env['sale.order.line']
        sale_obj = self.env['sale.order']
        product_obj = self.env['product.product']
        self.ensure_one()
        sales = []
        if self.sale_id:
            sales = self.sale_id
        else:
            sale_domain = [('date_order', '>=', self.date_from),
                           ('date_order', '<=', self.date_to),
                           ('state', 'in', ['sale', 'done'])]
            if self.partner_id:
                sale_domain += [('partner_id', '=', self.partner_id.id)]
            sales = sale_obj.search(sale_domain)
        sale_line_domain = [('order_id', 'in', sales.ids)]
        if self.product_id:
            sale_line_domain += [('product_id', '=', self.product_id.id)]
        elif self.product_tmpl_id:
            sale_line_domain += [('product_tmpl_id', '=',
                                  self.product_tmpl_id.id)]
        elif self.product_categ_id:
            products = product_obj.search([('categ_id', '=',
                                            self.product_categ_id.id)])
            sale_line_domain += [('product_id', 'in', products.ids)]
        sale_lines = sale_line_obj.search(sale_line_domain)
        sale_lines_to_purchase = []

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
                            bom_line.product_id, bom_line.product_qty * qty)
            return materials

        for line in sale_lines:
            materials = get_purchase_materials(
                line.product_id, line.product_uom_qty)
            for material in materials:
                sale_lines_to_purchase.append({
                    'used_in': material['used_in'],
                    'product_id': material['product_id'].id,
                    'product_uom_qty': material['product_uom_qty'],
                    'price_subtotal': material['product_uom_qty'] * material[
                        'product_id'].standard_price
                    })

        return sale_lines_to_purchase

    @api.multi
    def load_sales(self):
        self.ensure_one()
        forecast_line_obj = self.env['purchase.forecast.line']
        forecast = self.forecast_id
        sale_lines = self.get_purchase_forecast_lists(forecast)
        result = self.match_purchase_forecast(sale_lines, self.factor)
        for partner in result.keys():
            for product in result[partner].keys():
                for used_in in result[partner][product].keys():
                    prod_vals = result[partner][product][used_in]

                    seller = product._select_seller(
                        quantity=prod_vals['qty'],
                        uom_id=product.uom_po_id
                        )
                    if not seller:
                        partner_id = False
                    else:
                        partner_id = seller.name.id

                    line = forecast_line_obj.search([
                        ('forecast_id', '=', self.forecast_id.id),
                        ('used_in', '=', used_in.id if used_in else False),
                        ('product_id', '=', product.id)
                        ])
                    if line:
                        line.qty += prod_vals['qty']
                        line.update_supplier()
                    else:
                        forecast_line_vals = {
                            'used_in': used_in.id if used_in else False,
                            'product_id': product.id,
                            'forecast_id': self.forecast_id.id,
                            'partner_id': partner_id,
                            'qty': prod_vals['qty'],
                            'unit_price': seller.price if seller else False
                        }
                        forecast_line_obj.create(forecast_line_vals)
        return True


class PurchasePurchaseForecastLoad(models.TransientModel):

    _name = 'purchase.purchase.forecast.load'

    def _get_default_partner(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        partner = False
        if model == 'purchase.order':
            partner = record.partner_id
        return partner

    def _get_default_forecast(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        forecast = False
        if model == 'purchase.forecast':
            forecast = record.id
        return forecast

    def _get_default_purchase(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        purchase = False
        if model == 'purchase.order':
            purchase = record.id
        return purchase

    def _get_default_date_from(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        date_from = False
        if model == 'purchase.order':
            date_from = record.date_order
        elif model == 'purchase.forecast':
            date_from = record.date_from
        return date_from

    def _get_default_date_to(self):
        model = self.env.context.get('active_model', False)
        record = self.env[model].browse(self.env.context.get('active_id'))
        date_to = False
        if model == 'purchase.order':
            date_to = record.date_order
        elif model == 'purchase.forecast':
            date_to = record.date_to
        return date_to

    partner_id = fields.Many2one("res.partner", string="Partner",
                                 default=_get_default_partner)
    date_from = fields.Date(string="Date from", default=_get_default_date_from)
    date_to = fields.Date(string="Date to", default=_get_default_date_to)
    purchase_id = fields.Many2one("purchase.order", "Purchase",
                                  default=_get_default_purchase)
    forecast_id = fields.Many2one("purchase.forecast", "Forecast",
                                  default=_get_default_forecast)
    product_categ_id = fields.Many2one("product.category", string="Category")
    product_tmpl_id = fields.Many2one("product.template", string="Template")
    product_id = fields.Many2one("product.product", string="Product")
    factor = fields.Float(string="Factor", default=1)

    @api.onchange('purchase_id')
    def purchase_onchange(self):
        if self.purchase_id:
            self.partner_id = self.purchase_id.partner_id.id
            self.date_from = self.purchase_id.date_order
            self.date_to = self.purchase_id.date_order

    @api.onchange('forecast_id')
    def forecast_onchange(self):
        if self.forecast_id:
            self.date_from = self.forecast_id.date_from
            self.date_to = self.forecast_id.date_to

    @api.multi
    def match_purchases_forecast(self, purchases, factor):
        self.ensure_one()
        res = {}
        for purchase in purchases:
            partner = purchase.partner_id.id
            product = purchase.product_id.id
            if partner not in res:
                res[partner] = {}
            if product not in res[partner]:
                res[partner][product] = {'qty': 0.0, 'amount': 0.0}
            product_dict = res[partner][product]
            sum_qty = product_dict['qty'] + purchase.product_qty * factor
            sum_subtotal = (product_dict['amount'] +
                            purchase.price_subtotal)
            product_dict['qty'] = sum_qty
            product_dict['amount'] = sum_subtotal
        return res

    @api.multi
    def get_purchase_forecast_lists(self, forecast):
        purchase_line_obj = self.env['purchase.order.line']
        purchase_obj = self.env['purchase.order']
        product_obj = self.env['product.product']
        self.ensure_one()
        purchases = []
        if self.purchase_id:
            purchases = self.purchase_id
        else:
            purchase_domain = [('date_order', '>=', self.date_from),
                               ('date_order', '<=', self.date_to),
                               ('state', 'in', ['purchase', 'done'])]
            if self.partner_id:
                purchase_domain += [('partner_id', '=', self.partner_id.id)]
            purchases = purchase_obj.search(purchase_domain)
        purchase_line_domain = [('order_id', 'in', purchases.ids)]
        if self.product_id:
            purchase_line_domain += [('product_id', '=', self.product_id.id)]
        elif self.product_tmpl_id:
            purchase_line_domain += [('product_tmpl_id', '=',
                                      self.product_tmpl_id.id)]
        elif self.product_categ_id:
            products = product_obj.search([('categ_id', '=',
                                            self.product_categ_id.id)])
            purchase_line_domain += [('product_id', 'in', products.ids)]
        purchase_lines = purchase_line_obj.search(purchase_line_domain)
        return purchase_lines

    @api.multi
    def load_purchases(self):
        self.ensure_one()
        forecast_line_obj = self.env['purchase.forecast.line']
        forecast = self.forecast_id
        purchase_lines = self.get_purchase_forecast_lists(forecast)
        result = self.match_purchases_forecast(purchase_lines, self.factor)
        for partner in result.keys():
            for product in result[partner].keys():
                prod_vals = result[partner][product]
                line = forecast_line_obj.search([
                    ('forecast_id', '=', self.forecast_id.id),
                    ('used_in', '=', False),
                    ('partner_id', '=', partner),
                    ('product_id', '=', product)
                    ])
                if line:
                    line.qty += prod_vals['qty']
                else:
                    forecast_line_vals = {'product_id': product,
                                          'forecast_id': self.forecast_id.id,
                                          'partner_id': partner,
                                          'qty': prod_vals['qty'],
                                          'unit_price': (prod_vals['amount'] /
                                                         prod_vals['qty'])
                                          }
                    forecast_line_obj.create(forecast_line_vals)
        return True
