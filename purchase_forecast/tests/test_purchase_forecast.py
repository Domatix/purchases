from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.tests import common


class TestPurchaseForecastFlow(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseForecastFlow, self).setUp()
        # Useful models
        self.so_model = self.env['sale.order']
        self.po_model = self.env['purchase.order']
        self.sf_model = self.env['sale.forecast']
        self.pf_model = self.env['purchase.forecast']
        self.po_line_model = self.env['purchase.order.line']
        self.so_line_model = self.env['sale.order.line']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.product_uom_model = self.env['product.uom']
        self.supplierinfo_model = self.env["product.supplierinfo"]
        self.pricelist_model = self.env['product.pricelist']
        self.partner = self.env.ref('base.res_partner_1')
        self.partner_agrolite = self.env.ref('base.res_partner_2')
        self.productpf = self.env['product.product'].create({
            'name': 'Product Purchase Forecast',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_load_sales(self):
        """ Test purchase forecast flow."""
        uom_id = self.product_uom_model.search([('name', '=', 'Unit(s)')])[0]
        pricelist = self.pricelist_model.search([
            ('name', '=', 'Public Pricelist')])[0]

        so_vals = {
            'partner_id': self.partner_agrolite.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'product_uom': uom_id.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 121.0
                })
            ]
        }
        so_vals2 = {
            'partner_id': self.partner.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'product_uom_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0
                })
            ]
        }
        self.so_model.create(so_vals)
        confirmed_so = self.so_model.create(so_vals2)
        confirmed_so.action_confirm()

        pf_vals = {
            'name': 'Test 1',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),

        }
        pf = self.pf_model.create(pf_vals)
        context = {
            "active_model": 'purchase.forecast',
            "active_ids": [pf.id],
            "active_id": pf.id
            }

        load_sales_wizard_dict = self.env['purchase.sale.forecast.load'].\
            with_context(
                context).create(
            {
                'factor': 3,
                'product_id': self.productpf.id
            })

        load_sales_wizard_dict.load_sales()
        self.assertEqual(
            sum(pf.forecast_lines.mapped('qty')),
            3,
            'Sales are not loaded proper.')

    def test_load_purchases(self):
        """ Test purchase forecast flow."""
        po_vals = {
            'partner_id': self.partner_agrolite.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'date_planned': date.today(),
                    'product_uom': self.productpf.uom_po_id.id,
                    'product_qty': 1.0,
                    'price_unit': 121.0
                })
            ]
        }
        po_vals2 = {
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'date_planned': date.today(),
                    'product_qty': 1.0,
                    'product_uom': self.productpf.uom_po_id.id,
                    'price_unit': 121.0
                })
            ]
        }

        self.po_model.create(po_vals)
        confirmed_so = self.po_model.create(po_vals2)
        confirmed_so.button_confirm()

        pf_vals = {
            'name': 'Test 1',
            'date_from': date.today() - relativedelta(days=1),
            'date_to': date.today() + relativedelta(days=1)

        }
        pf = self.pf_model.create(pf_vals)
        context = {
            "active_model": 'purchase.forecast',
            "active_ids": [pf.id],
            "active_id": pf.id
            }

        load_sales_wizard_dict = self.env['purchase.purchase.forecast.load'].\
            with_context(
                context).create(
            {
                'factor': 3,
                'forecast_id': pf.id,
                'product_id': self.productpf.id
            })
        load_sales_wizard_dict.load_purchases()
        self.assertEqual(
            sum(pf.forecast_lines.mapped('qty')),
            3,
            'Purchases are not loaded proper.')

    def test_purchase_forecast_load_sale_forecast(self):
        """ Test purchase forecast flow."""
        sf_vals = {
            'name': 'Test 2',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),
            'forecast_lines': [
                (0, 0, {
                    'product_id': self.productpf.id,
                    'qty': 1,
                })
            ]
        }
        sf = self.sf_model.create(sf_vals)

        empty_pf_vals = {
            'name': 'Test 3',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),
        }
        empty_pf = self.pf_model.create(empty_pf_vals)
        context = {
            "active_model": 'purchase.forecast',
            "active_ids": [empty_pf.id],
            "active_id": empty_pf.id
            }

        load_sale_forecast_wizard_dict = \
            self.env['forecast.sale.load'].with_context(context).create(
                {
                    'forecast_sales': sf.id
                })
        load_sale_forecast_wizard_dict.button_confirm()
        self.assertEqual(
            sum(empty_pf.forecast_lines.mapped('qty')),
            1,
            'Sales forecasts are not loaded proper.')

    def test_purchase_forecast_recalculate_actual_qty(self):
        """ Test purchase forecast flow."""
        uom_id = self.product_uom_model.search([('name', '=', 'Unit(s)')])[0]
        pricelist = self.pricelist_model.search([
            ('name', '=', 'Public Pricelist')])[0]

        so_vals = {
            'partner_id': self.partner_agrolite.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'product_uom_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0
                })
            ]
        }
        so_vals2 = {
            'partner_id': self.partner.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                (0, 0, {
                    'name': self.productpf.name,
                    'product_id': self.productpf.id,
                    'product_uom_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0
                })
            ]
        }

        pf_vals = {
            'name': 'Test 3',
            'date_from': date.today() + relativedelta(months=-1),
            'date_to': date.today() + relativedelta(months=1),
            'forecast_lines': [
                (0, 0, {
                    'product_id': self.productpf.id,
                    'qty': 1,
                })
            ]
        }
        pf = self.pf_model.create(pf_vals)
        self.so_model.create(so_vals)
        invoiced_so = self.so_model.create(so_vals2)
        invoiced_so.action_confirm()
        invoiced_so.action_invoice_create()
        pf.recalculate_actual_qty()
        self.assertEqual(
            sum(pf.forecast_lines.mapped('actual_qty')),
            1,
            'Actual quantities are not computed proper.')

    def test_create_purchase_forecast(self):
        sf_vals = {
            'name': 'Test 4',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),
            'forecast_lines': [
                (0, 0, {
                    'product_id': self.productpf.id,
                    'qty': 1,
                })
            ]
        }
        sf = self.sf_model.create(sf_vals)
        sf.create_purchase_forecast()
        pf = self.env['purchase.forecast'].search([(
            'sale_forecast_id', '=', sf.id)])
        self.assertEqual(
            sum(pf.forecast_lines.mapped('qty')),
            sum(sf.forecast_lines.mapped('qty')),
            'Purchase forecast not created properly.')

    def test_action_view_purchase_orders(self):
        pf_vals = {
            'name': 'Test 5',
            'date_from': date.today() + relativedelta(months=-1),
            'date_to': date.today() + relativedelta(months=1),
            'forecast_lines': [
                (0, 0, {
                    'partner_id': self.partner_agrolite.id,
                    'product_id': self.productpf.id,
                    'qty': 1,
                })
            ]
        }
        pf = self.pf_model.create(pf_vals)
        pf.action_view_purchase_orders()
        self.assertEqual(
            sum(pf.purchase_order_ids.order_line.mapped('product_qty')),
            sum(pf.forecast_lines.mapped('qty')),
            'Purchase order not created properly.')

    def test_purchase_forecast_load_purchase_forecast(self):
        """ Test purchase forecast flow."""
        pf_vals = {
            'name': 'Test 6',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),
            'forecast_lines': [
                (0, 0, {
                    'product_id': self.productpf.id,
                    'qty': 1,
                })
            ]
        }
        pf = self.pf_model.create(pf_vals)

        empty_pf_vals = {
            'name': 'Test 7',
            'date_from': date.today() + relativedelta(years=1),
            'date_to': date.today() + relativedelta(years=2),
        }
        empty_pf = self.pf_model.create(empty_pf_vals)
        context = {
            "active_model": 'purchase.forecast',
            "active_ids": [empty_pf.id],
            "active_id": empty_pf.id
            }

        load_purchase_forecast_wizard_dict = \
            self.env['self.purchase.forecast.load'].with_context(context).\
            create(
                {
                    'forecast_purchase': pf.id
                })
        load_purchase_forecast_wizard_dict.button_confirm()
        self.assertEqual(
            sum(empty_pf.forecast_lines.mapped('qty')),
            1,
            'Purchase forecasts are not loaded proper.')
