odoo.define("onestein_api_client", function (require) {
    "use strict";

    var widgetRegistry = require("web.widget_registry");
    var Widget = require("web.Widget");
    var rpc = require('web.rpc');

    var CreditBalanceWidget = Widget.extend({
        template: "onestein_api_client.CreditBalance",

        init: function(parent, record, node) {
            this._super.apply(this, arguments);
            this.method = node.attrs.method;
            this.model = record.model;
        },

        willStart: function() {
            return this._super.apply(this, arguments).then(this._getCreditBalance.bind(this));
        },

        _getCreditBalance: function() {
            return rpc.query({
                model: this.model,
                method: this.method,
                args: [],
            }, {
                shadow: true,
            }).then(function (credits) {
                this.credits = credits === -1 ? '-' : credits;
            }.bind(this));
        }
    });

    widgetRegistry.add("onestein_api_credit_balance", CreditBalanceWidget);
});
