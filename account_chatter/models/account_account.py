# Copyright 2020 Vauxoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class AccountAccount(models.Model):

    _inherit = 'account.account'

    tax_ids = fields.Many2many(tracking=True)
    tag_ids = fields.Many2many(tracking=True)
    group_id = fields.Many2one(tracking=True)
    allowed_journal_ids = fields.Many2many(tracking=True)

    def _mail_track(self, tracked_fields, initial):
        """Perform a field tracking over tax_ids, tag_ids and allowed_journal_ids
        This is performed manually because field tracking over many2many fields is not
        natively supported.
        """
        self.ensure_one()
        changes = set()  # contains onchange tracked fields that changed
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            if col_name not in initial and col_name not in ['tag_ids', 'tax_ids', 'allowed_journal_ids']:
                continue
            initial_value = initial[col_name]
            new_value = self[col_name]

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                tracking_sequence = getattr(
                    # backward compatibility with old parameter name
                    self._fields[col_name], 'tracking', getattr(self._fields[col_name], 'track_sequence', 100))
                if tracking_sequence is True:
                    tracking_sequence = 100
                tracking = self.env['mail.tracking.value'].create_tracking_values(
                    initial_value, new_value, col_name, col_info, tracking_sequence, self._name)
                if tracking:
                    tracking_value_ids.append([0, 0, tracking])
                changes.add(col_name)

        return changes, tracking_value_ids