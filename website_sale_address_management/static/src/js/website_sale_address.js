/** @odoo-module **/

import websiteSaleAddress from '@website_sale/js/address';
import { rpc } from "@web/core/network/rpc";

websiteSaleAddress.include({
    async _changeCountry(init=false) {
        const countryId = parseInt(this.addressForm.country_id.value);
        if (!countryId) {
            return;
        }
        const data = await rpc(
            `/shop/country_info/${parseInt(countryId)}`,
            {address_type: this.addressType},
        );
        if (this.addressForm.phone){
            if (data.phone_code !== 0) {
                this.addressForm.phone.placeholder = '+' + data.phone_code;
            } else {
                this.addressForm.phone.placeholder = '';
            }
        }
        // populate states and display
        var selectStates = this.addressForm.state_id;
        if (!init || selectStates.options.length === 1) {
            // dont reload state at first loading (done in qweb)
            if (data.states.length || data.state_required) {
                // empty existing options, only keep the placeholder.
                selectStates.options.length = 1;
                // create new options and append them to the select element
                data.states.forEach((state) => {
                    let option = new Option(state[1], state[0]);
                    // Used by localizations
                    option.setAttribute('data-code', state[2]);
                    selectStates.appendChild(option);
                });
                this._showInput('state_id');
            } else {
                this._hideInput('state_id');
            }
        }
        // manage fields order / visibility
        if (data.fields) {
        if (this._getInputDiv('zip') && this._getInputDiv('city')) {
            if (data.zip_before_city) {
                this._getInputDiv('zip').after(this._getInputDiv('city'));
            } else {
                this._getInputDiv('zip').before(this._getInputDiv('city'));
            }
        }
            var all_fields = ['street', 'zip', 'city'];
            all_fields.forEach((fname) => {
                if (data.fields.includes(fname)) {
                    this._showInput(fname);
                } else {
                    this._hideInput(fname);
                }
            });
        }
        const required_fields = this.addressForm.querySelectorAll(':required');
        required_fields.forEach((element) => {
            // remove requirement on previously required fields
            if (
                !data.required_fields.includes(element.name)
                && !this.requiredFields.includes(element.name)
            ) {
                this._markRequired(element.name, false);
            }
        });
        data.required_fields.forEach((fieldName) => {
            this._markRequired(fieldName, true);
        })
    },

    _getInputDiv(name) {
        if (this.addressForm[name]) {
            return this.addressForm[name].parentElement;
        }
        else {
            return;
        }
    },

    _showInput(name) {
        // show parent div, containing label and input
        if (this.addressForm[name]) {
            this.addressForm[name].parentElement.style.display = '';
        }
        else {
            return;
        }
    },
});
