/** @odoo-module **/
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const UNCHECK_CONFIRM_MS = 3000;

class MicroGridField extends Component {
    static template = "microflow.MicroGrid";
    static props = { ...standardFieldProps };
    static supportedTypes = ["one2many"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ saving: false, pendingUncheckId: null });
        this._uncheckTimer = null;

        onWillUnmount(() => this._cancelPendingUncheck());
    }

    // ── Data helpers ──────────────────────────────────────────────────────────

    get lines() {
        const staticList = this.props.record.data[this.props.name];
        if (!staticList || !staticList.records) return [];
        return [...staticList.records]
            .map((r) => ({
                id: r.resId,
                sequence: r.data.sequence || 0,
                amount_expected: r.data.amount_expected || 0,
                is_paid: r.data.is_paid || false,
            }))
            .sort((a, b) => a.sequence - b.sequence);
    }

    get currentLine() {
        return this.lines.find((l) => !l.is_paid) || null;
    }

    get paidCount() {
        return this.lines.filter((l) => l.is_paid).length;
    }

    isCurrent(line) {
        return this.currentLine?.id === line.id;
    }

    formatAmount(amount) {
        return new Intl.NumberFormat("fr-CD", { maximumFractionDigits: 0 }).format(amount);
    }

    // ── Pending uncheck state ─────────────────────────────────────────────────

    _startPendingUncheck(line) {
        this.state.pendingUncheckId = line.id;
        this.notification.add(
            `Case ${line.sequence} — appuyez à nouveau pour annuler cette collecte`,
            { type: "warning", sticky: false }
        );
        this._uncheckTimer = setTimeout(() => {
            this.state.pendingUncheckId = null;
            this._uncheckTimer = null;
        }, UNCHECK_CONFIRM_MS);
    }

    _cancelPendingUncheck() {
        if (this._uncheckTimer) {
            clearTimeout(this._uncheckTimer);
            this._uncheckTimer = null;
        }
        this.state.pendingUncheckId = null;
    }

    // ── Core actions ──────────────────────────────────────────────────────────

    async _doCheck(line) {
        this.state.saving = true;
        try {
            await this.orm.call("micro.cycle.line", "register_collection", [[line.id]]);
            await this.props.record.load();
            this.notification.add("Case ✓ collectée", { type: "success", sticky: false });
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async _doUncheck(line) {
        this.state.saving = true;
        try {
            await this.orm.call("micro.cycle.line", "unregister_collection", [[line.id]]);
            await this.props.record.load();
            this.notification.add(`Case ${line.sequence} annulée`, { type: "info", sticky: false });
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    // ── Main tap handler ──────────────────────────────────────────────────────

    async onCellTap(line) {
        if (this.state.saving || this.props.readonly) return;

        if (line.is_paid) {
            if (this.state.pendingUncheckId === line.id) {
                // Second tap on same paid cell → confirm uncheck
                this._cancelPendingUncheck();
                await this._doUncheck(line);
            } else {
                // First tap on any paid cell → start confirmation window
                this._cancelPendingUncheck();
                this._startPendingUncheck(line);
            }
            return;
        }

        // Tap on unpaid cell → check it (cancel any pending uncheck first)
        this._cancelPendingUncheck();
        await this._doCheck(line);
    }
}

registry.category("fields").add("MicroGrid", {
    component: MicroGridField,
    supportedTypes: ["one2many"],
});

export { MicroGridField };
