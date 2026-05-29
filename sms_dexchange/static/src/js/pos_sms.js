/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
// import { rpc } from "@web/core/network/rpc";


patch(PaymentScreen.prototype, {

    
    async afterOrderValidation(isSynced) {
        // Appel standard Odoo (TRÈS IMPORTANT)
        console.log("Super afterOrderValidation OK1");
        await super.afterOrderValidation(isSynced);

        // Si la commande n’a pas été synchronisée, on n’envoie rien
        if (!isSynced) {
            return;
        }

        const order = this.pos.get_order();
        if (!order) {
            return;
        }

        const partner = order.get_partner();
        if (!partner || !partner.phone) {
            return;
        }

        // Sécurité : éviter les doubles envois
        // if (order.sms_sent) {
        //     return;
        // }

        try {
            await this.env.services.orm.call(
                "pos.order",
                "action_send_sms_from_pos",
                [[0]],
                { order_uid: order.uid }
            );

            // await rpc('/pos/sp/send_sms', {
            //     order_uid: order.uid,
            //     // params: {
            //     //     order_uid: order.uid,
            //     // },
            // });

            // Marquer comme envoyé côté frontend
            console.log("SMS Send:", order);

            // Notification de succès
            this.env.services.notification.add(
                // this.env._t("SMS envoyé au client : ") + partner.phone,
                _t("SMS envoyé au client : ") + partner.phone,
                {
                    type: "success",
                    sticky: false,
                }
            );

        } catch (error) {
            console.error("Erreur SMS Dexchange:", error);
            // Notification d'erreur (non bloquante)
            this.env.services.notification.add(
                // this.env._t("Échec d'envoi du SMS"),
                _t("Échec d'envoi du SMS"),
                {
                    type: "warning",
                }
            );
        }
    },
});
