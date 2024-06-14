from datetime import datetime, timedelta

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sales_frequency = fields.Float(string="Sales Frequency")
    average_purchase_amount = fields.Float(string="Average Purchase Amount")
    purchased_product_types = fields.Many2many("product.category", string="Purchased Product Types")
    recommendations = fields.One2many("product.suggestion", "user_id", string="Recommendations")

    def _compute_sales_metrics(self):
        current_date = datetime.now()
        one_year_ago = current_date - timedelta(days=12 * 30)

        partners = self.search([])
        for partner in partners:
            # Obtener todas las facturas del cliente que están pagadas o en proceso de pago
            invoices = self.env["account.move"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("move_type", "=", "out_invoice"),
                    ("payment_state", "in", ["in_payment", "paid", "partial"]),
                    ("invoice_date", ">=", one_year_ago.strftime("%Y-%m-%d")),
                ]
            )

            # Calcular la frecuencia de compra (número de facturas al mes)
            partner.sales_frequency = len(invoices) / 12 if len(invoices) > 0 else 0

            # Calcular el monto promedio de compra
            total_amount = sum(invoice.amount_total for invoice in invoices)
            partner.average_purchase_amount = total_amount / len(invoices) if len(invoices) > 0 else 0

            # Calcular los tipos de productos comprados
            product_category_ids = set()
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    product_category_ids.add(line.product_id.categ_id.id)
            partner.purchased_product_types = [(6, 0, list(product_category_ids))]
