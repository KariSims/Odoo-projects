/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class RealEstateDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            stats: {
                total_properties: 0,
                available_properties: 0,
                rented_properties: 0,
                total_rent_income: 0,
                total_maintenance_cost: 0,
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const result = await this.orm.call("real.estate.property", "get_dashboard_stats", []);
        this.state.stats = result;
    }

    viewProperties(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Properties",
            res_model: "real.estate.property",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
        });
    }
}

RealEstateDashboard.template = "real_estate_management_advanced.Dashboard";

registry.category("actions").add("real_estate_management_advanced.dashboard", RealEstateDashboard);
