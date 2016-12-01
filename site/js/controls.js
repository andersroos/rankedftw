

// Create a radio control. The control should be a jq of the control
// ul with ctr-name. The callback gets called with name and value when
// the value changes.
export let Radio = function(control, default_value, select_callback) {

    if (control.length != 1) { throw "Control is not length 1 was " + control.length + "."; }
    
    var o = {};
    o.name = control.attr('ctrl-name');

    o.selects = control.find('a');
    o.allowed_values = [];
    o.value;
    o.container;
    
    o.selects.each(function() { o.allowed_values.push($(this).attr('ctrl-value')); });

    sc2.controls.container.register(o);
    
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
            sc2.controls.container.selected(o.name, $(event.delegateTarget).attr('ctrl-value'));
        });
    });
    
    // Set initial value.
    o.change_selected_value(sc2.controls.get_persistent_initial_value(o.name, o.allowed_values, default_value));
    
    return o;
};

