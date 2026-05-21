/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async action_capture_gps() {
        if (!navigator.geolocation) return alert("GPS non supporté");
        
        navigator.geolocation.getCurrentPosition(async (pos) => {
            const coords = `${pos.coords.latitude}, ${pos.coords.longitude}`;
            await this.model.root.update({ gps_coordinates: coords });
            await this.model.root.save();
        }, (err) => alert("Erreur GPS : " + err.message));
    }
});