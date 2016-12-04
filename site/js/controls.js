import {get_hash} from "./utils";
import {get_cookie} from "./utils";
import {set_cookie} from "./utils";
import {set_hash} from "./utils";

//
// Set persistent value of control (no checking).
//
let set_persistent_value = function(name, value) {
    set_cookie(name, value);
    set_hash(name, value);
};

//
// Get value initial value from persistent storage (will also set
// value to default if not present). The list allowed_values is mostly
// to prevent cookie manipulation all settings with the same name
// should have the same allowed_values.
//
let get_persistent_initial_value = function(name, allowed_values, default_value) {
    var value = get_hash(name);

    if (!value) {
        value = get_cookie(name);
    }

    for (var i = 0; i < allowed_values.length; ++i) {
        if (value == allowed_values[i]) {
            set_persistent_value(name, value, true);
            return value;
        }
    }
    set_persistent_value(name, default_value, true);
    return default_value;
};


//
// Controls registry, singleton for handling page global settings (like version and region).
//
class Registry {

    constructor() {
        this.by_name = {};  // Controls with the same name will be linked.
    }

    //
    // During init of a control, the control should register itself.
    //
    register(control) {
        this.by_name[control.name] = this.by_name[control.name] || [];
        this.by_name[control.name].push(control);
    }

    //
    // Will be called by click events on the controls.
    //
    selected(name, value) {
        set_persistent_value(name, value);
        var controls = this.by_name[name];
        for (var i = 0; i < controls.length; ++i) {
            controls[i].change_selected_value(value);
        }
    }
}
export let registry = new Registry();


//
// Radio control. The control should be a jq of the control
// ul with ctr-name. The callback gets called with name and value when
// the value changes.
//
export let Radio = function(control, default_value, select_callback) {

    if (control.length != 1) { throw "Control is not length 1 was " + control.length + "."; }

    var o = {};
    o.name = control.attr('ctrl-name');

    o.selects = control.find('a');
    o.allowed_values = [];
    o.value = null;
    o.container = null;

    o.selects.each(function() { o.allowed_values.push($(this).attr('ctrl-value')); });

    registry.register(o);

    o.change_selected_value = function(new_value) {

        o.value = new_value;

        // Highlight selected.
        o.selects.each(function(_, element) {
            var e = $(element);
            if (e.attr('ctrl-value') == o.value) {
                e.addClass('selected');
            }
            else {
                $(element).removeClass('selected');
            }
        });

        // Callback to change graph etc.
        select_callback(o.name, o.value)
    };

    // Setup click callback.
    o.selects.each(function(_, element) {
        $(element).click(function(event) {
            registry.selected(o.name, $(event.delegateTarget).attr('ctrl-value'));
        });
    });

    // Set initial value.
    o.change_selected_value(get_persistent_initial_value(o.name, o.allowed_values, default_value));

    return o;
};
