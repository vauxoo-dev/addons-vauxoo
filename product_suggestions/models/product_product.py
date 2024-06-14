from datetime import datetime, timedelta

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    min_price = fields.Float(string="Minimum Price")
    max_price = fields.Float(string="Maximum Price")
    average_price = fields.Float(string="Average Price")
    average_discount = fields.Float(string="Average Discount")

    def _compute_product_metrics(self):
        current_date = datetime.now()
        one_year_ago = current_date - timedelta(days=12 * 30)

        products = self.search([])
        for product in products:
            # Obtener las líneas de factura del producto en los últimos 12 meses
            invoice_lines = self.env["account.move.line"].search(
                [
                    ("product_id", "=", product.id),
                    ("move_id.move_type", "=", "out_invoice"),
                    ("move_id.payment_state", "in", ["in_payment", "paid", "partial"]),
                    ("move_id.invoice_date", ">=", one_year_ago.strftime("%Y-%m-%d")),
                ]
            )

            if invoice_lines:
                # Calcular el rango de precios
                prices = [line.price_unit for line in invoice_lines]
                product.min_price = min(prices)
                product.max_price = max(prices)
                product.average_price = sum(prices) / len(prices)

                # Calcular el promedio de descuentos
                discounts = [(line.price_unit * (line.discount / 100)) for line in invoice_lines]
                product.average_discount = sum(discounts) / len(discounts)
            else:
                product.min_price = 0
                product.max_price = 0
                product.average_price = 0
                product.average_discount = 0
