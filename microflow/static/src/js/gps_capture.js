/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

function _fetchGPSCoords() {
    return new Promise((resolve) => {
        if (!navigator.geolocation) { resolve(null); return; }
        navigator.geolocation.getCurrentPosition(
            (pos) => resolve(`${pos.coords.latitude}, ${pos.coords.longitude}`),
            () => resolve(null),   // permission denied or timeout → skip silently
            { timeout: 5000 }
        );
    });
}

// Capture the original save BEFORE patching — Odoo 18's patch() does not inject this._super.
const _originalSave = FormController.prototype.save;

patch(FormController.prototype, {
    // Manual button — always captures (even if coordinates already set)
    async action_capture_gps() {
        if (!navigator.geolocation) return alert("GPS non supporté");
        navigator.geolocation.getCurrentPosition(async (pos) => {
            const coords = `${pos.coords.latitude}, ${pos.coords.longitude}`;
            await this.model.root.update({ gps_coordinates: coords });
            await this.model.root.save();
        }, (err) => alert("Erreur GPS : " + err.message));
    },

    // Auto-capture on save when coordinates are not yet set
    async save(...args) {
        if (
            this.model?.root?.resModel === "res.partner" &&
            !this.model.root.data?.gps_coordinates
        ) {
            const coords = await _fetchGPSCoords();
            if (coords) {
                try {
                    await this.model.root.update({ gps_coordinates: coords });
                } catch (_) { /* GPS update failed — continue with save */ }
            }
        }
        return _originalSave.call(this, ...args);
    },
});
