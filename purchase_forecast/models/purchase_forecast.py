# -*- coding: utf-8 -*-
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

from odoo import models, fields, api, exceptions, _
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseForecast(models.Model):
    _name = 'purchase.forecast'
    sale_forecast_id = fields.Many2one(
        comodel_name='sale.forecast',
        string='Sale Forecast')

    name = fields.Char(string='Name', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    forecast_lines = fields.One2many('purchase.forecast.line',
                                     'forecast_id', string="Forecast Lines")

    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='purchase_forecast_id',
        string='Purchase Orders')

    purchase_order_count = fields.Integer(
        string='Purchase Orders Count',
        compute='_compute_purchase_order_count')

    def action_view_purchase_orders(self):
        orders = self.env['purchase.order'].search([
            ('purchase_forecast_id', '=', self.id)])
        if orders:
            return {
                    'name': "Purchase Orders from "+self.name,
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'domain':  [('purchase_forecast_id', '=', self.id)],
                    'type': 'ir.actions.act_window',
                }
        else:
            for line in self.forecast_lines:
                if not line.partner_id:
                    raise exceptions.Warning(_('Error! There are products \
                without a supplier. Please enter a supplier in the product \
                form and click on the "Update Suppliers" button.'))
            for partner_id in self.forecast_lines.mapped('partner_id'):
                lines = self.forecast_lines.search([
                    ('partner_id', '=', partner_id.id),
                    ('forecast_id', '=', self.id)
                    ])
                order = self.env['purchase.order'].create({
                    'partner_id': partner_id.id,
                    'purchase_forecast_id': self.id
                })
                for product in lines.mapped('product_id'):
                    same_product_lines = lines.with_context(
                        product=product).filtered(
                        lambda r: r.product_id == r._context['product'])
                    qty = sum(same_product_lines.mapped('qty'))
                    today = fields.datetime.today()
                    line = {
                                'product_id': product.id,
                                'name': product.name,
                                'product_qty': qty,
                                'product_uom': product.uom_po_id.id,
                                'price_unit': 0.0,
                                'order_id': order.id,
                                'date_planned': today.strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT),
                            }
                    line = self.env['purchase.order.line'].create(line)
                    line.onchange_product_id()
                    line.product_qty = qty
                    line._onchange_quantity()
                    order.order_line = [(4, line.id)]

                order.origin = "Previsión de compra: "+self.name
            return {
                    'name': "Pedidos de compra de "+self.name,
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'domain':  [('purchase_forecast_id', '=', self.id)],
                    'type': 'ir.actions.act_window',
                }

    @api.one
    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        self.purchase_order_count = len(self.purchase_order_ids)

    @api.one
    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.date_from >= self.date_to:
            raise exceptions.Warning(_('Error! Date to must be lower '
                                       'than date from.'))

    @api.multi
    def update_suppliers(self):
        for line in self.forecast_lines:
            if line.product_id:
                seller = line.product_id._select_seller(
                    quantity=line.qty,
                    uom_id=line.product_id.uom_po_id
                    )
                if not seller:
                    partner = False
                else:
                    partner = seller.name.id
                line.partner_id = partner
                line.unit_price = seller.price

    @api.multi
    def recalculate_actual_qty(self):
        sale_obj = self.env['sale.order.line']
        for record in self.forecast_lines:
            if record.product_id:
                if record.partner_id:
                    sale_ids = sale_obj.search([
                        ('product_id', '=', record.product_id.id),
                        ('order_id.partner_id', '=', record.partner_id.id),
                        ('invoice_status', '=', 'invoiced'),
                        ('order_id.confirmation_date', '>=', record.date_from),
                        ('order_id.confirmation_date', '<=', record.date_to)])
                else:
                    sale_ids = sale_obj.search([
                        ('product_id', '=', record.product_id.id),
                        ('invoice_status', '=', 'invoiced'),
                        ('order_id.confirmation_date', '>=', record.date_from),
                        ('order_id.confirmation_date', '<=', record.date_to)])
                record.actual_qty = sum(sale_ids.mapped('product_uom_qty'))


class PurchaseForecastLine(models.Model):

    _name = 'purchase.forecast.line'
    _order = 'partner_id, product_id, forecast_id, qty'

    @api.one
    @api.depends('unit_price', 'qty')
    def _get_subtotal(self):
        self.subtotal = self.unit_price * self.qty

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.unit_price = self.product_id.list_price

    product_id = fields.Many2one('product.product',
                                 domain="[('purchase_ok','=',True)]",
                                 string='Product')
    used_in = fields.Many2one('product.product', string='Used in')
    qty = fields.Float('Quantity', default=1,
                       digits=dp.get_precision('Product Unit of Measure'))
    unit_price = fields.Float('Unit Price',
                              digits=dp.get_precision('Product Price'))
    subtotal = fields.Float('Subtotal', compute=_get_subtotal, store=True,
                            digits=dp.get_precision('Product Price'))
    partner_id = fields.Many2one("res.partner", string="Partner")
    commercial_id = fields.Many2one(comodel_name="res.users",
                                    related="partner_id.user_id",
                                    string="Commercial")
    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency",
        related="partner_id.property_product_pricelist.currency_id")
    date_from = fields.Date(string="Date from", store=True,
                            related="forecast_id.date_from")
    date_to = fields.Date(string="Date to", related="forecast_id.date_to",
                          store=True)
    forecast_id = fields.Many2one('purchase.forecast',
                                  string='Forecast',
                                  ondelete='cascade')
    date = fields.Date("Date")

    actual_qty = fields.Float(
        string='Actual Qty',
        compute='_compute_actual_qty',
        store=True)

    @api.multi
    @api.onchange('qty')
    def update_supplier(self):
        for line in self:
            if line.product_id:
                seller = line.product_id._select_seller(
                    quantity=line.qty,
                    uom_id=line.product_id.uom_po_id
                    )
                if not seller:
                    partner = False
                else:
                    partner = seller.name.id
                line.partner_id = partner
                line.unit_price = seller.price

    @api.depends('forecast_id.forecast_lines')
    def _compute_actual_qty(self):
        sale_obj = self.env['sale.order.line']
        for record in self:
            if record.product_id:
                if record.partner_id:
                    sale_ids = sale_obj.search([
                        ('product_id', '=', record.product_id.id),
                        ('order_id.partner_id', '=', record.partner_id.id),
                        ('invoice_status', '=', 'invoiced'),
                        ('order_id.confirmation_date', '>=', record.date_from),
                        ('order_id.confirmation_date', '<=', record.date_to)])
                else:
                    sale_ids = sale_obj.search([
                        ('product_id', '=', record.product_id.id),
                        ('invoice_status', '=', 'invoiced'),
                        ('order_id.confirmation_date', '>=', record.date_from),
                        ('order_id.confirmation_date', '<=', record.date_to)])
                record.actual_qty = sum(sale_ids.mapped('product_uom_qty'))
