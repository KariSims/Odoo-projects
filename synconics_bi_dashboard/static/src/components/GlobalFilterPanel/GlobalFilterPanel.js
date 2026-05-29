/** @odoo-module **/

import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class GlobalFilterPanel extends Component {
  static props = {
    onApplyFilters: Function,
  };

  setup() {
    this.orm = useService("orm");
    this.partnerSearchRef = useRef("partnerSearch");
    this.fieldValueRef = useRef("fieldValue");

    this.state = useState({
      visible: false,
      partnerFields: [],
      // Filter values
      partnerId: null,
      partnerIdDisplay: "",
      partnerField: "",
      partnerFieldMeta: null,
      partnerFieldValue: null,
      partnerFieldValueDisplay: "",
      datePeriod: "",
      dateFrom: "",
      dateTo: "",
      invoiceState: "",
      // Autocomplete state
      partnerSuggestions: [],
      fieldValueSuggestions: [],
      showPartnerDropdown: false,
      showFieldValueDropdown: false,
    });

    onWillStart(async () => {
      try {
        this.state.partnerFields = await this.orm.call(
          "dashboard.chart",
          "get_partner_filter_fields",
          [],
        );
      } catch (e) {
        console.error("GlobalFilterPanel: failed to load partner fields", e);
        this.state.partnerFields = [];
      }
    });
  }

  get activeFilterCount() {
    let count = 0;
    if (this.state.partnerId) count++;
    if (this.state.partnerField && this.state.partnerFieldValue !== null && this.state.partnerFieldValue !== "") count++;
    if (this.state.datePeriod) count++;
    if (this.state.invoiceState) count++;
    return count;
  }

  togglePanel() {
    this.state.visible = !this.state.visible;
  }

  // ── Partner search ────────────────────────────────────────────

  async onPartnerInput(ev) {
    const q = ev.target.value;
    this.state.partnerIdDisplay = q;
    this.state.partnerId = null;
    if (q.length < 2) {
      this.state.partnerSuggestions = [];
      this.state.showPartnerDropdown = false;
      return;
    }
    const results = await this.orm.call("res.partner", "name_search", [], {
      name: q,
      limit: 8,
    });
    this.state.partnerSuggestions = results.map(([id, name]) => ({ id, name }));
    this.state.showPartnerDropdown = this.state.partnerSuggestions.length > 0;
  }

  onPartnerSelect(partner) {
    this.state.partnerId = partner.id;
    this.state.partnerIdDisplay = partner.name;
    this.state.partnerSuggestions = [];
    this.state.showPartnerDropdown = false;
  }

  clearPartner() {
    this.state.partnerId = null;
    this.state.partnerIdDisplay = "";
    this.state.partnerSuggestions = [];
    this.state.showPartnerDropdown = false;
  }

  // ── Partner field selector ────────────────────────────────────

  onPartnerFieldChange(ev) {
    const fieldName = ev.target.value;
    this.state.partnerField = fieldName;
    this.state.partnerFieldMeta = this.state.partnerFields.find(
      (f) => f.name === fieldName,
    ) || null;
    this.state.partnerFieldValue = null;
    this.state.partnerFieldValueDisplay = "";
    this.state.fieldValueSuggestions = [];
    this.state.showFieldValueDropdown = false;
  }

  // ── Partner field value input ─────────────────────────────────

  async _loadM2OSuggestions(q, meta) {
    try {
      const results = await this.orm.call(meta.comodel, "name_search", [], {
        name: q,
        args: meta.domain || [],
        limit: 30,
      });
      this.state.fieldValueSuggestions = results.map(([id, name]) => ({ id, name }));
      this.state.showFieldValueDropdown = this.state.fieldValueSuggestions.length > 0;
    } catch (e) {
      console.error("GlobalFilterPanel: M2O suggestions error", e);
    }
  }

  async onFieldValueFocus(ev) {
    const meta = this.state.partnerFieldMeta;
    if (!meta || !["many2one", "many2many"].includes(meta.type) || !meta.comodel) return;
    // Load all options immediately on focus (no need to type anything)
    await this._loadM2OSuggestions(ev.target.value || "", meta);
  }

  async onFieldValueInput(ev) {
    const q = ev.target.value;
    this.state.partnerFieldValueDisplay = q;
    const meta = this.state.partnerFieldMeta;
    if (!meta) return;

    if (["many2one", "many2many"].includes(meta.type) && meta.comodel) {
      // Don't set partnerFieldValue until user picks from the dropdown
      await this._loadM2OSuggestions(q, meta);
    } else {
      // char / integer / float / boolean: raw value
      this.state.partnerFieldValue = q || null;
      this.state.showFieldValueDropdown = false;
    }
  }

  onFieldValueSelect(item) {
    this.state.partnerFieldValue = item.id;
    this.state.partnerFieldValueDisplay = item.name;
    this.state.fieldValueSuggestions = [];
    this.state.showFieldValueDropdown = false;
  }

  onSelectionValueChange(ev) {
    this.state.partnerFieldValue = ev.target.value || null;
  }

  onBooleanValueChange(ev) {
    this.state.partnerFieldValue = ev.target.checked;
  }

  clearFieldValue() {
    this.state.partnerField = "";
    this.state.partnerFieldMeta = null;
    this.state.partnerFieldValue = null;
    this.state.partnerFieldValueDisplay = "";
    this.state.fieldValueSuggestions = [];
    this.state.showFieldValueDropdown = false;
  }

  hidePartnerDropdown() {
    setTimeout(() => { this.state.showPartnerDropdown = false; }, 200);
  }

  hideFieldValueDropdown() {
    setTimeout(() => { this.state.showFieldValueDropdown = false; }, 200);
  }

  onDateFromChange(ev) {
    this.state.dateFrom = ev.target.value;
  }

  onDateToChange(ev) {
    this.state.dateTo = ev.target.value;
  }

  onInvoiceStateChange(ev) {
    this.state.invoiceState = ev.target.value;
  }

  // ── Period presets ───────────────────────────────────────────

  _fmt(d) {
    // Format a Date object to 'YYYY-MM-DD'
    return d.toISOString().slice(0, 10);
  }

  onDatePeriodChange(ev) {
    const period = ev.target.value;
    this.state.datePeriod = period;
    const today = new Date();

    if (period === "today") {
      const s = this._fmt(today);
      this.state.dateFrom = s;
      this.state.dateTo = s;
    } else if (period === "week") {
      const day = today.getDay() || 7; // Monday = 1 … Sunday = 7
      const mon = new Date(today);
      mon.setDate(today.getDate() - day + 1);
      const sun = new Date(mon);
      sun.setDate(mon.getDate() + 6);
      this.state.dateFrom = this._fmt(mon);
      this.state.dateTo = this._fmt(sun);
    } else if (period === "month") {
      const first = new Date(today.getFullYear(), today.getMonth(), 1);
      const last = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      this.state.dateFrom = this._fmt(first);
      this.state.dateTo = this._fmt(last);
    } else if (period === "ytd") {
      const jan1 = new Date(today.getFullYear(), 0, 1);
      this.state.dateFrom = this._fmt(jan1);
      this.state.dateTo = this._fmt(today);
    } else {
      // 'custom' or '' — clear computed dates so user can enter manually
      this.state.dateFrom = "";
      this.state.dateTo = "";
    }
  }

  // ── Apply / Reset ────────────────────────────────────────────

  applyFilters() {
    const filters = {};
    if (this.state.partnerId) {
      filters.partner_id = this.state.partnerId;
    }
    if (
      this.state.partnerField &&
      this.state.partnerFieldValue !== null &&
      this.state.partnerFieldValue !== ""
    ) {
      filters.partner_field = this.state.partnerField;
      filters.partner_field_value = this.state.partnerFieldValue;
    }
    if (this.state.dateFrom) filters.date_from = this.state.dateFrom;
    if (this.state.dateTo) filters.date_to = this.state.dateTo;
    if (this.state.invoiceState) filters.invoice_state = this.state.invoiceState;

    this.props.onApplyFilters(Object.keys(filters).length > 0 ? filters : null);
  }

  resetFilters() {
    this.state.partnerId = null;
    this.state.partnerIdDisplay = "";
    this.state.partnerField = "";
    this.state.partnerFieldMeta = null;
    this.state.partnerFieldValue = null;
    this.state.partnerFieldValueDisplay = "";
    this.state.datePeriod = "";
    this.state.dateFrom = "";
    this.state.dateTo = "";
    this.state.invoiceState = "";
    this.state.partnerSuggestions = [];
    this.state.fieldValueSuggestions = [];
    this.state.showPartnerDropdown = false;
    this.state.showFieldValueDropdown = false;
    this.props.onApplyFilters(null);
  }
}

GlobalFilterPanel.template = "synconics_bi_dashboard.GlobalFilterPanel";
