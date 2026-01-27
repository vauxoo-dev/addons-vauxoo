from odoo import api, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    @api.model
    def _get_view_group_hierarchy(self):
        result = super()._get_view_group_hierarchy()
        # Add extra_categories: categories that organize groups without privilege_id
        # into separate checkbox sections (instead of all going into "Extra Rights")
        module = "default_warehouse_from_sale_team"
        group_xmlids = [
            f"{module}.group_limited_default_warehouse_spt",
            f"{module}.group_manager_default_warehouse_spt",
            f"{module}.group_limited_default_warehouse_sp",
            f"{module}.group_manager_default_warehouse_sp",
            f"{module}.group_limited_default_warehouse_journal",
            f"{module}.group_manager_default_journal",
        ]
        group_ids = []
        for xmlid in group_xmlids:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record:
                group_ids.append(record.id)
        category = self.env.ref(f"{module}.module_category_default_warehouse", raise_if_not_found=False)
        extra_categories = []
        if category and group_ids:
            extra_categories.append({
                "id": category.id,
                "name": category.name,
                "group_ids": group_ids,
            })
        result["extra_categories"] = extra_categories
        return result
