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
        if (value === allowed_values[i]) {
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
    // During init of a control, the control should register itself. The control will be called with initial the
    // value.
    //
    register(control) {
        let controls = this.by_name[control.key] = this.by_name[control.key] || [];
        if (!controls.includes(control)) {
            this.by_name[control.key].push(control);
        }
        control.set_value(get_persistent_initial_value(control.key, control.allowed_values, control.default_value))
    }

    //
    // Will be when something is selected in a control (like a click event).
    //
    set_value(key, value) {
        set_persistent_value(key, value);
        this.by_name[key].forEach(control => { control.set_value(value) });
    }
}
let registry = new Registry();


//
// Create a Radio control. It will render itself inside jq_container. Options is a list of
// {value, heading (optional), tooltip, src (optional, for images)}. After creation it will
// add itself to the registry to be linked with other controls of the same key. Option values will be
// converted to strings and on_select will be called with a string.
//
export class Radio {

    // Render and register.
    constructor(jq_container, key, heading, options, default_value, on_select) {

        this.key = key;
        this.heading = heading;
        this.ul = $("<ul class='" + key + "'/>");
        this.on_select = on_select;

        jq_container.append(this.ul);

        this.update(options, default_value);
    }

    // Update with new options.
    update(options, default_value) {
        this.default_value = typeof default_value === "undefined" ? this.default_value : String(default_value);
        this.allowed_values = options.map(o => String(o.value));

        this.ul.empty();
        this.ul.append("<span>" + this.heading + "</span>");
        options.forEach(option => {
            let a = $("<a data-ctrl-value='" + option.value + "' title='" + (option.tooltip || '') + "'>");
            if (option.heading) {
                a.append("<span>" + option.heading + "</span>");
            }
            if (option.src) {
                a.append("<img src='" + option.src + "'>");
            }
            this.ul.append(a);
        });

        // Setup click callback.
        this.ul.find('a').each((_, e) => {
            $(e).click(event => {
                registry.set_value(this.key, $(event.delegateTarget).attr('data-ctrl-value'));
            });
        });
    }

    // Get initial value from persistent store and set it, or set default.
    init() {
        registry.register(this);
    }

    // On change callback from registry.
    set_value(new_value) {
        this.value = new_value;

        // Highlight selected.
        this.ul.find('a').each((_, e) => {
            e = $(e);
            if (e.attr('data-ctrl-value') === this.value) {
                e.addClass('selected');
            }
            else {
                e.removeClass('selected');
            }
        });

        // Callback to change graph etc.
        this.on_select(this.key, this.value)
    }
}

