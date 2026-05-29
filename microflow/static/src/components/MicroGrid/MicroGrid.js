/** @odoo-module **/
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";

const CHECK_CONFIRM_MS = 2000;
const UNCHECK_CONFIRM_MS = 3000;
const JUST_PAID_MS = 500;

// ── Dialog saisie montant (cycles variables) ─────────────────────────────────
class AmountInputDialog extends Component {
    static template = "microflow.AmountInputDialog";
    static components = { Dialog };
    static props = {
        lineSeq: Number,
        currency: String,
        onConfirm: Function,
        close: Function,
    };

    setup() {
        this.state = useState({ amount: "" });
    }

    get isAmountValid() {
        const v = parseFloat(this.state.amount);
        return !isNaN(v) && v > 0;
    }

    onKeydown(ev) {
        if (ev.key === "Enter") this.onConfirm();
    }

    onConfirm() {
        const amount = parseFloat(this.state.amount);
        if (!amount || amount <= 0) return;
        this.props.onConfirm(amount);
        this.props.close();
    }
}

class MicroGridField extends Component {
    static template = "microflow.MicroGrid";
    static props = { ...standardFieldProps };
    static supportedTypes = ["one2many"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            saving: false,
            pendingCheckId: null,
            pendingUncheckId: null,
            justPaidId: null,
        });
        this._checkTimer = null;
        this._uncheckTimer = null;
        this._justPaidTimer = null;

        onWillUnmount(() => {
            this._cancelPendingCheck();
            this._cancelPendingUncheck();
            this._clearJustPaid();
        });
    }

    // ── Data helpers ──────────────────────────────────────────────────────────

    get currencySymbol() {
        const cur = this.props.record.data.currency_id;
        return Array.isArray(cur) ? cur[1] : (cur || "");
    }

    get isVariable() {
        return this.props.record.data.cycle_type === "variable";
    }

    get lines() {
        const staticList = this.props.record.data[this.props.name];
        if (!staticList || !staticList.records) return [];
        return [...staticList.records]
            .map((r) => ({
                id: r.resId,
                sequence: r.data.sequence || 0,
                amount_expected: r.data.amount_expected || 0,
                amount_collected: r.data.amount_collected || 0,
                is_paid: r.data.is_paid || false,
                collection_order: r.data.collection_order || 0,
                uncheck_pending: r.data.uncheck_pending || false,
            }))
            .sort((a, b) => a.sequence - b.sequence);
    }

    get currentLine() {
        return this.lines.find((l) => !l.is_paid) || null;
    }

    get paidCount() {
        return this.lines.filter((l) => l.is_paid).length;
    }

    get collectedAmount() {
        if (this.isVariable) {
            return this.lines
                .filter((l) => l.is_paid)
                .reduce((sum, l) => sum + l.amount_collected, 0);
        }
        const perCase = this.props.record.data.amount_per_case || 0;
        return this.paidCount * perCase;
    }

    get totalAmount() {
        if (this.isVariable) return 0;
        const perCase = this.props.record.data.amount_per_case || 0;
        return this.lines.length * perCase;
    }

    isCurrent(line) {
        return this.currentLine?.id === line.id;
    }

    formatAmount(amount) {
        return new Intl.NumberFormat("fr-CD", { maximumFractionDigits: 0 }).format(amount);
    }

    // ── Pending check state (double-tap pour cocher) ──────────────────────────

    _startPendingCheck(line) {
        this.state.pendingCheckId = line.id;
        this.notification.add(
            `Case ${line.sequence} — tapez à nouveau pour confirmer la collecte`,
            { type: "warning", sticky: false }
        );
        this._checkTimer = setTimeout(() => {
            this.state.pendingCheckId = null;
            this._checkTimer = null;
        }, CHECK_CONFIRM_MS);
    }

    _cancelPendingCheck() {
        if (this._checkTimer) {
            clearTimeout(this._checkTimer);
            this._checkTimer = null;
        }
        this.state.pendingCheckId = null;
    }

    // ── Pending uncheck state (double-tap pour décocher) ─────────────────────

    _startPendingUncheck(line) {
        this.state.pendingUncheckId = line.id;
        this.notification.add(
            `Case ${line.sequence} — tapez à nouveau pour annuler cette collecte`,
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

    // ── Just-paid animation ───────────────────────────────────────────────────

    _clearJustPaid() {
        if (this._justPaidTimer) {
            clearTimeout(this._justPaidTimer);
            this._justPaidTimer = null;
        }
        this.state.justPaidId = null;
    }

    // ── Core actions ──────────────────────────────────────────────────────────

    async _doCheck(line) {
        this.state.saving = true;
        try {
            await this.orm.call("micro.cycle.line", "register_collection", [[line.id]]);
            await this.props.record.load();

            this._clearJustPaid();
            this.state.justPaidId = line.id;
            this._justPaidTimer = setTimeout(() => {
                this.state.justPaidId = null;
                this._justPaidTimer = null;
            }, JUST_PAID_MS);

            const perCase = this.props.record.data.amount_per_case || 0;
            const cur = this.currencySymbol;
            this.notification.add(
                `Case ${line.sequence} ✓ — ${this.formatAmount(perCase)} ${cur}\n` +
                `Total : ${this.formatAmount(this.collectedAmount)} / ${this.formatAmount(this.totalAmount)} ${cur}`,
                { type: "success", sticky: false }
            );
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async _doCheckWithAmount(line, amount) {
        this.state.saving = true;
        try {
            await this.orm.call("micro.cycle.line", "register_collection", [[line.id]], { amount });
            await this.props.record.load();

            this._clearJustPaid();
            this.state.justPaidId = line.id;
            this._justPaidTimer = setTimeout(() => {
                this.state.justPaidId = null;
                this._justPaidTimer = null;
            }, JUST_PAID_MS);

            this.notification.add(
                `Case ${line.sequence} ✓ — ${this.formatAmount(amount)} ${this.currencySymbol}`,
                { type: "success", sticky: false }
            );
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    _openAmountDialog(line) {
        this.dialog.add(AmountInputDialog, {
            lineSeq: line.sequence,
            currency: this.currencySymbol,
            onConfirm: (amount) => this._doCheckWithAmount(line, amount),
        });
    }

    async _doUncheck(line) {
        this.state.saving = true;
        try {
            const result = await this.orm.call("micro.cycle.line", "unregister_collection", [[line.id]]);
            await this.props.record.load();
            if (result && result.status === "pending") {
                this.notification.add(
                    `Case ${line.sequence} — demande d'annulation envoyée au Manager`,
                    { type: "warning", sticky: false }
                );
            } else {
                this.notification.add(`Case ${line.sequence} annulée`, { type: "info", sticky: false });
            }
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    // ── Uncheck dialog (ouvert au 2ème tap) ───────────────────────────────────

    _openUncheckDialog(line) {
        this.dialog.add(ConfirmationDialog, {
            title: "Annuler la collecte",
            body: `Case ${line.sequence} — Confirmer l'annulation de cette collecte ?`,
            confirm: () => this._doUncheck(line),
            confirmLabel: "Annuler la collecte",
            cancel: () => {},
            cancelLabel: "Garder",
        });
    }

    // ── Main tap handler ──────────────────────────────────────────────────────

    async onCellTap(line) {
        if (this.state.saving || this.props.readonly) return;
        try {
            if (line.is_paid) {
                this._cancelPendingCheck();
                if (line.uncheck_pending) {
                    this.notification.add(
                        `Case ${line.sequence} — demande d'annulation déjà soumise au Manager`,
                        { type: "warning", sticky: false }
                    );
                    return;
                }
                if (this.state.pendingUncheckId === line.id) {
                    this._cancelPendingUncheck();
                    this._openUncheckDialog(line);
                } else {
                    this._cancelPendingUncheck();
                    this._startPendingUncheck(line);
                }
                return;
            }

            // Case non payée — double-tap requis
            this._cancelPendingUncheck();
            if (this.state.pendingCheckId === line.id) {
                this._cancelPendingCheck();
                this._clearJustPaid();
                if (this.isVariable) {
                    this._openAmountDialog(line);
                } else {
                    await this._doCheck(line);
                }
            } else {
                this._cancelPendingCheck();
                this._startPendingCheck(line);
            }
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        }
    }
}

registry.category("fields").add("MicroGrid", {
    component: MicroGridField,
    supportedTypes: ["one2many"],
});

export { MicroGridField };
