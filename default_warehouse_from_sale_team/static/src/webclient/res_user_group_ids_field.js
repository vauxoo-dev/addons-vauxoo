/** @odoo-module **/
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const resUserGroupIdsField = registry.category("fields").get("res_user_group_ids");
const ResUserGroupIdsField = resUserGroupIdsField.component;

patch(ResUserGroupIdsField.prototype, {
    setup() {
        // Pre-compute custom category data BEFORE super (which calls getExtraGroupsArch)
        const { groups, extra_categories } = this.props.record.data.view_group_hierarchy;

        this._dwfstGroupIds = new Set();
        this.dwfstExtraCategories = [];

        if (extra_categories && extra_categories.length) {
            for (const cat of extra_categories) {
                for (const gid of cat.group_ids) {
                    this._dwfstGroupIds.add(gid);
                }
            }
            this.dwfstExtraCategories = extra_categories.map((cat) => ({
                id: cat.id,
                name: cat.name,
                privileges: Object.values(groups)
                    .filter((g) => !g.privilege_id && cat.group_ids.includes(g.id))
                    .map((g) => ({
                        description: g.comment,
                        groupId: g.id,
                        id: "group_" + g.id,
                        name: g.name,
                        groupFieldName: `field_group_${g.id}`,
                    }))
                    .sort((a, b) => a.name.localeCompare(b.name)),
            }));
        }

        super.setup(...arguments);
    },

    getExtraGroupsArch() {
        // Render "Extra Rights" WITHOUT our groups
        const filteredPrivileges = this.extraCategory.privileges.filter(
            (p) => !this._dwfstGroupIds.has(p.groupId)
        );

        let arch = "";
        if (filteredPrivileges.length) {
            arch += `
                <group string="${this.extraCategory.name}" class="o_extra_rights_group">
                    <group>
                        ${filteredPrivileges
                            .filter((_, index) => index % 2 === 0)
                            .map((privilege) => this.getPrivilegeArch(privilege))
                            .join("")}
                    </group>
                    <group>
                        ${filteredPrivileges
                            .filter((_, index) => index % 2 === 1)
                            .map((privilege) => this.getPrivilegeArch(privilege))
                            .join("")}
                    </group>
                </group>`;
        }

        // Render our custom checkbox sections
        for (const cat of this.dwfstExtraCategories) {
            if (cat.privileges.length) {
                arch += `
                    <group string="${cat.name}" class="o_extra_rights_group">
                        <group>
                            ${cat.privileges
                                .filter((_, index) => index % 2 === 0)
                                .map((privilege) => this.getPrivilegeArch(privilege))
                                .join("")}
                        </group>
                        <group>
                            ${cat.privileges
                                .filter((_, index) => index % 2 === 1)
                                .map((privilege) => this.getPrivilegeArch(privilege))
                                .join("")}
                        </group>
                    </group>`;
            }
        }
        return arch;
    },
});
