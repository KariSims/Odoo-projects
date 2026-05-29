/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const TX_TYPE_LABELS   = { savings: "Épargne", credit_repayment: "Remboursement", fees: "Frais" };
const TX_TYPE_BADGES   = { savings: "bg-primary", credit_repayment: "bg-info", fees: "bg-secondary" };
const TX_TYPE_KPI_CLS  = { savings: "mf-kpi-savings", credit_repayment: "mf-kpi-repayment", fees: "mf-kpi-fees" };
const CR_STATE_LABELS  = { pending: "En attente", active: "Actif" };
const CR_STATE_BADGES  = { pending: "bg-warning text-dark", active: "bg-success" };

class ManagerDashboard extends Component {
    static template = "microflow.ManagerDashboard";
    static props = { action: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.state = useState({
            transactions: [],
            credits: [],
            draftCycleCount: 0,
            loading: true,
            saving: false,
            txCollapsed: false,
            crCollapsed: false,
            agentsCollapsed: false,
            selectedIds: {},    // { [id]: true } — plain object, OWL-reactive
        });
        onWillStart(() => this._loadData());
        onMounted(() => {
            this._pollTimer = setInterval(() => this._loadData(), 30_000);
        });
        onWillUnmount(() => {
            clearInterval(this._pollTimer);
        });
    }

    async _loadData() {
        this.state.loading = true;
        const [transactions, credits, draftCycleCount] = await Promise.all([
            this.orm.searchRead(
                "micro.transaction",
                [["state", "=", "draft"]],
                ["name", "partner_id", "agent_id", "amount", "transaction_type", "currency_id", "is_verified"],
                { order: "create_date desc" }
            ),
            this.orm.searchRead(
                "micro.credit",
                [["state", "in", ["pending", "active"]]],
                ["partner_id", "agent_id", "capital", "amount_residual_total", "state", "date_granted", "currency_id"],
                { order: "state asc, date_granted desc" }
            ),
            this.orm.searchCount("micro.cycle", [["state", "=", "draft"]]),
        ]);
        this.state.transactions = transactions;
        this.state.credits = credits;
        this.state.draftCycleCount = draftCycleCount;
        this.state.selectedIds = {};
        this.state.loading = false;
    }

    // ── KPI computed ──────────────────────────────────────────────────────────

    get kpis() {
        const tx = this.state.transactions;
        const cr = this.state.credits;

        const byType = {};
        for (const t of tx) {
            const k = t.transaction_type;
            if (!byType[k]) byType[k] = { count: 0, total: 0, currency: t.currency_id };
            byType[k].count++;
            byType[k].total += t.amount;
        }

        const pendingCredits = cr.filter(c => c.state === "pending");
        const activeCredits  = cr.filter(c => c.state === "active");
        const totalResidual  = activeCredits.reduce((s, c) => s + (c.amount_residual_total || 0), 0);
        const crCurrency     = activeCredits.length ? activeCredits[0].currency_id : null;

        return {
            byType,
            pendingCount: pendingCredits.length,
            activeCount:  activeCredits.length,
            totalResidual,
            crCurrency,
        };
    }

    // ── Selection helpers ──────────────────────────────────────────────────────

    get selectedCount() {
        return Object.keys(this.state.selectedIds).length;
    }

    get allSelected() {
        const tx = this.state.transactions.filter(t => t.is_verified);
        return tx.length > 0 && tx.every(t => this.state.selectedIds[t.id]);
    }

    toggleSelect(id) {
        if (this.state.selectedIds[id]) {
            delete this.state.selectedIds[id];
        } else {
            this.state.selectedIds[id] = true;
        }
    }

    toggleSelectAll() {
        if (this.allSelected) {
            this.state.selectedIds = {};
        } else {
            const next = {};
            for (const t of this.state.transactions) {
                if (t.is_verified) next[t.id] = true;
            }
            this.state.selectedIds = next;
        }
    }

    // ── Vérification physique ─────────────────────────────────────────────────

    async toggleVerified(id) {
        const tx = this.state.transactions.find(t => t.id === id);
        if (!tx) return;
        const newValue = !tx.is_verified;
        tx.is_verified = newValue;  // optimistic update
        try {
            await this.orm.write("micro.transaction", [id], { is_verified: newValue });
        } catch (e) {
            tx.is_verified = !newValue;  // revert on error
            this.notification.add(e.data?.message || "Erreur lors de la mise à jour", { type: "danger" });
        }
    }

    // ── Validation ────────────────────────────────────────────────────────────

    async _doValidate(ids) {
        if (!ids.length) return;
        this.state.saving = true;
        try {
            await this.orm.call("micro.transaction", "action_bulk_confirm", [ids]);
            this.state.selectedIds = {};
            await this._loadData();
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur de validation", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async bulkConfirm() {
        const allIds = this.state.transactions.map(t => t.id);
        const verifiedCount = this.state.transactions.filter(t => t.is_verified).length;
        const unverifiedCount = allIds.length - verifiedCount;

        if (verifiedCount === 0) {
            this.notification.add(
                "Aucune transaction marquée « Reçu ». Cochez les fonds physiquement reçus avant de valider.",
                { type: "warning", sticky: false }
            );
            return;
        }

        const body = unverifiedCount > 0
            ? `Valider ${verifiedCount} transaction(s) vérifiée(s) ? (${unverifiedCount} non reçue(s) seront ignorées)`
            : `Valider ${verifiedCount} transaction(s) vérifiée(s) ?`;

        this.dialogService.add(ConfirmationDialog, {
            body,
            confirmLabel: "Confirmer",
            cancelLabel: "Annuler",
            confirm: () => this._doValidate(allIds),
        });
    }

    async bulkConfirmSelected() {
        await this._doValidate(Object.keys(this.state.selectedIds).map(Number));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    formatAmount(amount, currencyId) {
        const cur = Array.isArray(currencyId) ? currencyId[1] : "";
        return `${(amount || 0).toLocaleString("fr-FR")} ${cur}`;
    }

    txTypeLabel(type)   { return TX_TYPE_LABELS[type]  || type; }
    txTypeBadge(type)   { return TX_TYPE_BADGES[type]  || "bg-secondary"; }
    txTypeKpiCls(type)  { return TX_TYPE_KPI_CLS[type] || "mf-kpi-fees"; }
    crStateLabel(state) { return CR_STATE_LABELS[state] || state; }
    crStateBadge(state) { return CR_STATE_BADGES[state] || "bg-secondary"; }

    // ── Agrégats par agent ────────────────────────────────────────────────────

    get agentSummaries() {
        const map = {};
        for (const tx of this.state.transactions) {
            const [agentId, agentName] = tx.agent_id || [0, "?"];
            if (!map[agentId]) {
                map[agentId] = {
                    id: agentId,
                    name: agentName,
                    total: 0,
                    count: 0,
                    verifiedCount: 0,
                    currency: tx.currency_id,
                };
            }
            map[agentId].total += tx.amount;
            map[agentId].count++;
            if (tx.is_verified) map[agentId].verifiedCount++;
        }
        return Object.values(map).sort((a, b) => b.total - a.total);
    }

    agentProgressPct(ag) {
        return ag.count ? Math.round((ag.verifiedCount / ag.count) * 100) : 0;
    }

    // ── All-clear ─────────────────────────────────────────────────────────────

    get allClear() {
        return (
            !this.state.loading &&
            this.state.transactions.length === 0 &&
            this.state.credits.length === 0
        );
    }

    onToggleAgents() { this.state.agentsCollapsed = !this.state.agentsCollapsed; }
    onToggleTx() { this.state.txCollapsed = !this.state.txCollapsed; }
    onToggleCr() { this.state.crCollapsed = !this.state.crCollapsed; }

    onTransactionClick(ev) {
        if (ev.target.type === "checkbox") return;
        const id = parseInt(ev.currentTarget.dataset.id, 10);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "micro.transaction",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onCreditClick(ev) {
        const id = parseInt(ev.currentTarget.dataset.id, 10);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "micro.credit",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("microflow.manager_dashboard", ManagerDashboard);
