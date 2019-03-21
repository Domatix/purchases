from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    product_count = fields.Integer(
        compute='_compute_partner_supplier_product_count',
        string='Product count')

    @api.multi
    def _compute_partner_supplier_product_count(self):
        supplierinfo_obj = self.env['product.supplierinfo']
        supplier_ids = supplierinfo_obj.search([('name', '=', self.id)])
        self.product_count = len(supplier_ids)

    def action_supplier_product(self):
        supplierinfo_obj = self.env['product.supplierinfo']
        supplier_ids = supplierinfo_obj.search([('name', '=', self.id)])
        product_template = supplier_ids.mapped('product_tmpl_id')
        product_variant = product_template.mapped('product_variant_id').ids
        return {
            'name': self.env['product.product']._description,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'domain': "[('id', 'in', " + str(product_variant) + ")]",
            'context': self.env.context
            }
