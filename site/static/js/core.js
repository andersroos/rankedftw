
//
// sc2 "namespace" and global constans.
//

var sc2 = {};

var TOT = -2;
var COUNT = 0;
var WINS = 1;
var LOSSES = 2;

// Enum info populated from python.
sc2.enums_info = {};

sc2.default_version = 2;

function PP(data) { return JSON.stringify(data); }

sc2.static_url = 'http://www.rankedftw.com/static/latest/';
sc2.dynamic_url = 'http://www.rankedftw.com/';

//
// Utils.
//

sc2.utils = {}; 

// Reverse each of func.
sc2.utils.rev_each = function(list, fun) {
    for (var i = list.length - 1; i >= 0; --i) {
        fun(list[i], i);
    }
};

// Format an int with spaces.
sc2.utils.format_int = function(int) {
    var str = "" + int;
    var res = "";
    for (var i = 0; i < str.length; i+=3) {
        res = str.substring(str.length - i - 3, str.length - i) + " " + res;
    }
    return $.trim(res);
};

// Return the value value, but make sure it is in the range [min, max].
sc2.utils.min_max = function(min, value, max) {
    return Math.min(Math.max(min, value), max);
};

sc2.utils.doc_ready = function() {
    var deferred = $.Deferred();
    $(function() {
        deferred.resolve();
    });
    return deferred;
};

sc2.utils.get_hash = function(key) {
    var vars = window.location.hash.substring(1).split("&");
    for (var i = 0; i < vars.length; ++i) {
        var pair = vars[i].split('=');
        if (pair[0] == key) {
            return pair[1];
        }
    }
};

sc2.utils.set_hash = function(key, value) {
    var vars = window.location.hash.substring(1).split("&").filter(function(x) { return x !== ''; });
    var item = key + '=' + value;
    for (var i = 0; i < vars.length; ++i) {
        var pair = vars[i].split('=');
        if (pair[0] == key) {
            vars[i] = item;
            item = undefined;
            break;
        }
    }
    if (item) {
        vars.push(item);
    }
    window.history.replaceState('', '', '#' + vars.join('&'));
};

sc2.utils.set_cookie = function(name, value, path, expiry) {
    path = path || "/";
    expiry = expiry || "1 Jan 2100 01:01:01 GMT";
    document.cookie = name + "=" + value + ";expires=" + expiry + ";path=" + path;
};

sc2.utils.get_cookie = function(name) {
    var value;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                value = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return value;
};

//
// HTML
//

sc2.html = {}; 

// Add classes to container.
sc2.html.conf_container = function(jq_container) {
    jq_container.addClass('data-container wait');
};

// Add controls to container and returns of controls container.
sc2.html.add_controls_div = function(jq_container) {
    var controls = $('<div class="controls">');
    var content = $('<div class="content">');
    controls.append(content);
    jq_container.append(controls);
    return content;
};

// Add a control to controls. Buttons is a list of {value: <value>, tooltip:
// <tooltip>, heading: <heading>, src: <optional heading img source>}.
sc2.html.add_control = function(jq_controls, name, heading, options) {
    var ul = $("<ul ctrl-name='" + name + "'>");
    ul.append("<span>" + heading + "</span>");
    for (var i = 0; i < options.length; ++i) {
        var a = $("<a ctrl-value='" + options[i].value + "' title='" + options[i].tooltip + "'>");
        a.append("<span>" + options[i].heading + "</span>");
        if (options[i].src) {
            a.append("<img src='" + options[i].src + "'>");
        }
        ul.append(a);
    }
    jq_controls.append(ul);
};

// Add canvas element to container.
sc2.html.add_canvas = function(jq_container) {
    jq_container.append('<canvas class="graph">');
};

// Add tooltip element to container. Table is a list of <heading, data-class>.
sc2.html.add_tooltip = function(jq_container, data) {
    var tooltip = $('<div class="tooltip">');
    var table = $('<table>');
    for (var i = 0; i < data.length; ++i) {
        var tr = $('<tr>');
        tr.append("<th>" + data[i][0] + "</th>");
        tr.append("<td class='" + data[i][1] + "'></td>");
        table.append(tr);
    }
    tooltip.append(table);
    jq_container.append(tooltip);
};

//
// Seasons.
//

sc2.seasons = {};

sc2.seasons._deferred = $.Deferred();

sc2.seasons.init = function(seasons) {
    sc2.seasons.sorted = seasons;
    sc2.seasons.by_id = {};
    for (var i = 0; i < seasons.length; ++i) {
        sc2.seasons.by_id[seasons[i].id] = seasons[i];
    }
    sc2.seasons._deferred.resolve();
};

sc2.seasons.load = function() {
    if (typeof sc2.seasons.sorted == 'undefined') {
        $.ajax({dataType: "json",
                url: sc2.dynamic_url + 'team/seasons/',
                success: function(data) {
                    sc2.seasons.init(data);
                }});
    }
    return sc2.seasons._deferred;
};

//
// Image resources.
//

sc2.images = {};

sc2.get_image_bank_div = function() {
    var image_bank = $('#sc2-image-bank');
    if (image_bank.length == 0) {
        image_bank = $("<div id='sc2-image_bank' style='display: none;'>");
        image_bank.appendTo('body');
    }
    return image_bank;
};

sc2.images.load_leagues = function() {
    if (typeof this.deferred == 'undefined') {
        this.deferred = $.Deferred();
        var deferred = this.deferred; 

        var image_bank = sc2.get_image_bank_div();

        _.each(sc2.enums_info.league_ranking_ids, function(league_id) {
            var league_tag = sc2.enums_info.league_key_by_ids[league_id];
            var img = $("<img id='league" + league_id + "' src='" + sc2.static_url + "img/leagues/" + league_tag + "-16x16.png' />");
            img.one("load", function() {
                if (_.every(_.map(sc2.enums_info.league_ranking_ids,
                                  function(lid) { return $('#league' + lid)[0].complete; }))) {
                    deferred.resolve();
                }
            });
            img.appendTo(image_bank);
        });
    }

    return this.deferred;
};

sc2.images.load_races = function() {
    if (typeof this.deferred == 'undefined') {
        this.deferred = $.Deferred();
        var deferred = this.deferred; 

        var image_bank = sc2.get_image_bank_div();
        
        _.each(sc2.enums_info.race_ranking_ids, function(race_id) {
            var race_tag = sc2.enums_info.race_key_by_ids[race_id];
            var img = $("<img id='race" + race_id + "' src='" + sc2.static_url + "img/races/" + race_tag + "-16x16.png' />");
            img.one("load", function() {
                if (_.every(_.map(sc2.enums_info.race_ranking_ids,
                        function(rid) { return $('#race' + rid)[0].complete; }))) {
                    deferred.resolve();
                }
                deferred.resolve();
            });
            img.appendTo(image_bank);
        });
    }

    return this.deferred;
};

//
// Common stuff for settings an controls.
//

sc2.controls = {};

sc2.controls.a_event = function(category, name, value) {
    if (typeof ga != 'undefined') {
        ga('send', 'event', category, name, value);
    }
};

// Set persistent value of control (no checking).
sc2.controls.set_persistent_value = function(name, value, skip_event) {
    if (!skip_event) {
        sc2.controls.a_event('controls-set', name, value);
    }
    sc2.utils.set_cookie(name, value);
    sc2.utils.set_hash(name, value);
};

// Get value initial value from persistent storage (will also set
// value to default if not present). The list allowed_values is mostly
// to prevent cookie manipulation all settings with the same name
// should have the same allowed_values.
sc2.controls.get_persistent_initial_value = function(name, allowed_values, default_value) {
    var value = sc2.utils.get_hash(name);

    if (!value) {
        value = sc2.utils.get_cookie(name);
    }

    for (var i = 0; i < allowed_values.length; ++i) {
        if (value == allowed_values[i]) {
            sc2.controls.a_event('controls-load', name, value);
            sc2.controls.set_persistent_value(name, value, true);
            return value;
        }
    }
    sc2.controls.set_persistent_value(name, default_value, true);
    sc2.controls.a_event('controls-set-default', name, default_value);
    return default_value;
};
    

// Init page global control containers.
sc2.controls.init_container = function() {
    
    var o = {};

    var all = {}; // Map of name => list of controls. All controls with the same name are linked.

    // During init of a control, the control will register itself.
    o.register = function(control) {
        all[control.name] = all[control.name] || [];
        all[control.name].push(control);
    };

    // Will be called by click events on the controls, should call
    // change_selected_value on all affected controls.
    o.selected = function(name, value) {
        sc2.controls.set_persistent_value(name, value);
        var controls = all[name];
        for (var i = 0; i < controls.length; ++i) {
            controls[i].change_selected_value(value);
        }
    };
    
    sc2.controls.container = o;
};
sc2.controls.init_container();

// Create a radio control. The control should be a jq of the control
// ul with ctr-name. The callback gets called with name and value when
// the value changes.
sc2.controls.Radio = function(control, default_value, select_callback) {

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

//
// Common statistcs related code.
//

sc2.stats = {};

sc2.stats._deferred = {};

sc2.stats._all_raws_by_mode = {};

// Wrapper object for a filtered and aggregated object.
sc2.stats.Aggregate = function(mode_id, filters, group_by, raw) {
    var object = $.extend({}, filters);

    function create_accessor(type) {
        return function() {
            var data = raw.data;
            for (var i = 0; i < arguments.length; ++i) {
                data = data[arguments[i]];
            }
            if (group_by.length !== arguments.length) {
                data = data[TOT];
            }
            return data[type];
        };
    }

    // Get the count at the id sub path of group_by enums.
    object.count = create_accessor(COUNT);

    // Get the wins at the id sub path of group_by enums.
    object.wins = create_accessor(WINS);

    // Get the losses at the id sub path of group_by enums.
    object.losses = create_accessor(LOSSES);

    return object;
};

// Wrapper object for single raw stat to help with filtering and aggregation.
sc2.stats.Stat = function(mode_id, raw) {

    function copy_non_data(raw) {
        var o = {};
        Object.keys(raw).forEach(function (key) {
            if (key !== 'data') {
                o[key] = raw[key];
            }
        });
        return o;
    }

    var object = copy_non_data(raw);
    var stat = sc2.enums_info.stat[raw.stat_version];

    function get(v, r, l, a) {
        // Get data at index.

        var index = stat.data_size
            * (  stat.version_indices[v] * stat.region_count * stat.league_count * stat.race_count
               + stat.region_indices[r] * stat.league_count * stat.race_count
               + stat.league_indices[l] * stat.race_count
               + stat.race_indices[a]);
        return raw.data.slice(index, index + stat.data_size);
    }

    function filter_sum(filters) {
        // Calculate a sum based on filters, one filter per type (version, region, league, races),
        // each filter maps to a list of type ids. An undefined type list will be regarded as a list with all ids.
        var sum = [0, 0, 0, 0];

        _.each(filters.versions, function(v) {
            _.each(filters.regions, function(r) {
                _.each(filters.leagues, function(l) {
                    _.each(filters.races, function(a) {
                        var data = get(v, r, l, a);
                        for (var i = 0; i < stat.data_size; ++i) {
                            sum[i] += data[i];
                        }
                    });
                });
            });
        });

        return sum;
    }

    function filter_aggregate(filters, group_by) {
        // Calculate a generic filtered map [of maps ..]  of sums. The
        // aggregate will only consist of data points that is in the filter
        // for each dimension (making it possible to aggregate EU + AM but not
        // include SEA). Filters is a map with index lists into the type
        // arrays. The group_by list is the type names of lists that should be
        // included (with sum) in the result. The order of group_by is
        // important. For example group_by = ['regions', 'races'] will return a
        // map of region_ids => map of race_ids => sums. The race_ids map will also
        // include a TOT which is the total in that region. The region_ids map
        // will also include a TOT which is a total of everything.

        if (group_by.length == 0) {
            return filter_sum(filters);
        }

        var result = {};
        var group_by__head = group_by[0];
        var group_by__head_s = group_by__head + 's';
        var group_by__rest = group_by.slice(1, group_by.length);
        var tot = [0, 0, 0, 0];

        for (var fi in filters[group_by__head_s]) {
            var next_filter = $.extend({}, filters);
            next_filter[group_by__head_s] = [filters[group_by__head_s][fi]];
            var next_res = filter_aggregate(next_filter, group_by__rest);
            result[filters[group_by__head_s][fi]] = next_res;
            var sum;
            if (next_res[TOT]) {
                sum = next_res[TOT];
            }
            else {
                sum = next_res;
            }
            for (var i = 0; i < stat.data_size; ++i) {
                tot[i] += sum[i];
            }
        }
        result[TOT] = tot;

        return result;
    }

    object.filter_aggregate = function(filters, group_by) {
        filters.versions = filters.versions || stat.version_ids;
        filters.regions = filters.regions   || stat.region_ids;
        filters.leagues = filters.leagues   || stat.league_ids;
        filters.races = filters.races       || stat.race_ids;

        var aggregated = copy_non_data(raw);
        aggregated.data = filter_aggregate(filters, group_by);
        return sc2.stats.Aggregate(mode_id, filters, group_by, aggregated);
    };

    return object;
};

// Create a stats object for all stats for a mode.
sc2.stats.Mode = function(mode_id) {
    var object = {};

    var raws = sc2.stats._all_raws_by_mode[mode_id];

    // Get stat by ranking id, return another one close to it if not present.
    object.get = function(ranking_id) {
        var raw;
        for (var i = 0; i < raws.length; ++i) {
            raw = raws[i];  // Will cause a missing raws to get another raw.
            if (raw.id === ranking_id) {
                break;
            }
        }
        return sc2.stats.Stat(mode_id, raw);
    };

    // Get lst stat.
    object.get_last = function() {
        return sc2.stats.Stat(mode_id, raws[raws.length - 1])
    };

    // Iterate over raws in order. Skip raws that are of season version lower than min.
    object.each = function(fun, min_version) {
        for (var i = 0; i < raws.length; ++i) {
            if (_.isUndefined(min_version) || min_version <= raws[i].season_version) {
                fun(sc2.stats.Stat(mode_id, raws[i]), i);
            }
        }
    };

    // Iterate over raws in reverse order. Skip raws that are of season version lower than min.
    object.each_reverse = function(fun, min_version) {
        for (var i = raws.length - 1; i >= 0; --i) {
            if (_.isUndefined(min_version) || min_version <= raws[i].season_version) {
                fun(sc2.stats.Stat(mode_id, raws[i]), i);
            }
        }
    };

    return object;
};

// Fetch all rankings raw stat data for mode and store it, returns deferred for callback when fetched.
sc2.stats.load_all_for_mode = function(mode_id) {
    if (typeof sc2.stats._deferred[mode_id] === "undefined") {
        sc2.stats._deferred[mode_id] = $.ajax({
            dataType: "json",
            url: sc2.dynamic_url + 'stats/raw/' + mode_id + '/',
            success: function(data) { sc2.stats._all_raws_by_mode[mode_id] = data; }
        });
    }
    return sc2.stats._deferred[mode_id];
};

//
// Common graph stuff.
//

sc2.graph = {};

// Insert image tags for resources listed in options ("leagues") and
// call success when loaded.
sc2.graph.load_resources = function(container_selector, options, success) {
    
};

sc2.graph.GraphBase = function(container_selector, edges, x_margin) {

    edges = edges || {top: 20, right: 40, bottom: 20, left: 64}; // Spacing inside canvas to graph ares.
    x_margin = x_margin || 20;                                   // Extra spacing on x inside axis, but inside edge.
    
    var o = {};

    //
    // Fixed values.
    //
    
    o.container = $(container_selector);
    o.canvas = $('.graph', o.container);
    o.tooltip = $('.tooltip', o.container);
    o.ctx = o.canvas[0].getContext("2d");
    
    o.edges = edges;

    o.x_margin = x_margin;

    //
    // Calculated after resize or settings changes.
    //

    o.settings = {};
    o.initialized = false;
    o.use_crosshair = true;
    
    o.width = 100;
    o.height = 100;

    o.y_ax = {};
    o.y_ax.top_value;    // The actual value at the top of the graph.
    o.y_ax.bottom_value; // The actual value at the botttom of the graph.
    o.y_per_unit;        // Y-pixels per unit whatever it is.

    o.x_ax = {};
    o.x_ax.left_value;  // The actual leftmost value.
    o.x_ax.right_value; // The actual rightmost value.
    o.x_per_unit;       // X-pixels per unit whatever it is.

    o.points; // Points on the graph, used for mouse over functionality.

    o.race_colors = {};
    o.race_colors[-1] = '#666666'; // Unknown
    o.race_colors[0]  = '#704898'; // Zerg
    o.race_colors[1]  = '#fff080'; // Protoss
    o.race_colors[2]  = '#c94118'; // Terran
    o.race_colors[3]  = '#a0ebff'; // Random
    
    //
    // Drawing functions.
    //

    // Clear, fill canvas with black.
    o.clear = function(alpha) {
        alpha = alpha || 1.0;
        o.ctx.globalAlpha = alpha;
        o.ctx.fillStyle = "#000000";
        o.ctx.fillRect(0, 0, o.canvas.width(), o.canvas.height());
        o.ctx.globalAlpha = 1.0;
    };

    // Creates a gradient (tied to the context).
    o.gradient = function(color0, color1) {
        var gradient = o.ctx.createLinearGradient(0, 0, o.width, o.height);
        gradient.addColorStop(0.0, color0);
        gradient.addColorStop(0.2, color1);
        gradient.addColorStop(0.4, color0);
        gradient.addColorStop(0.5, color1);
        gradient.addColorStop(0.6, color0);
        gradient.addColorStop(0.8, color1);
        gradient.addColorStop(0.9, color0);
        gradient.addColorStop(1.0, color1);
        return gradient
    };

    // Initialize styles for the league colors, needs to be done after each resize.
    o.setup_league_styles = function() {
        o.bronze = o.gradient('#5d3621', '#3d1f17');
        o.silver = o.gradient('#606060', '#808080');
        o.gold = o.gradient('#e8e8e8', '#e8b830');
        o.platinum = o.gradient('#a0a0a0', '#e0e0e0');
        o.diamond = o.gradient('#2080c0', '#3040a0');
        o.master = o.gradient('#078786', '#5aeeee');
        o.grandmaster = '#ff0000';
        o.league_styles = [o.bronze, o.silver, o.gold, o.platinum, o.diamond, o.master, o.grandmaster]
    };

    // Graph line helper.
    o._line_helper = function(points, x_offset, y_offset) {
        x_offset = x_offset || 0;
        y_offset = y_offset || 0;
        o.ctx.beginPath();
        o.ctx.moveTo(points[0].x + x_offset, points[0].y + y_offset);
        for (var i = 1; i < points.length; ++i) {
            o.ctx.lineTo(points[i].x + x_offset, points[i].y + y_offset);
        }
    };
    
    // Draw a line relative to the canvas. Points is a list of {x: x, y: y}. Add x and y offset to each point.
    o.line = function(style, width, points, x_offset, y_offset) {
        o.ctx.strokeStyle = style;
        o.ctx.lineWidth = width;
        o._line_helper(points, x_offset, y_offset);
        o.ctx.stroke();
    };

    // Same as line but points are relative to the graph area.
    o.gline = function(style, width, points) {
        o.line(style, width, points, o.edges.left, o.edges.top);
    };
    
    // Just like line but fill the area in the line with fill style.
    o.area = function(style, points, x_offset, y_offset) {
        o.ctx.fillStyle = style;
        o._line_helper(points, x_offset, y_offset);
        o.ctx.closePath();
        o.ctx.fill();
    };
 
    // Same as area but points are relative to the graph area.
    o.garea = function(style, points) {
        o.area(style, points, o.edges.left, o.edges.top);
    };

    // Just like line but text.
    o.text = function(text, x_offset, y_offset, align, baseline, style) {
        o.ctx.font ="normal 13px sans-serif ";
        o.ctx.textAlign = align || 'center';
        o.ctx.textBaseline = baseline || 'top';
        o.ctx.fillStyle = style || "#ffffff";
        o.ctx.fillText(text, x_offset, y_offset)
    };
    
    // Print the y-axis.
    o.y_axis = function(y_label) {
        y_label = y_label ||  "int";
        
        o.line("#ffffff", 2, [{x: o.edges.left - o.x_margin, y: o.edges.top},
                              {x: o.edges.left - o.x_margin, y: o.edges.top + o.height}]);
        
        for (var pos = 0; pos <= 10; ++pos) {
            var value = (o.y_ax.bottom_value - o.y_ax.top_value) / 10 * pos + o.y_ax.top_value;
            var y = Math.round(o.edges.top + (value - o.y_ax.top_value) * o.y_per_unit) + 0.5;

            var label;

            if (y_label == 'percent') {
                if (Math.max(Math.abs(o.y_ax.top_value), Math.abs(o.y_ax.bottom_value)) < 10) {
                    label = value.toFixed(2) + "%"
                }
                else if (Math.abs(o.y_ax.bottom_value - o.y_ax.top_value) < 10) {
                    label = value.toFixed(1) + "%"
                }
                else {
                    label = Math.round(value) + "%";
                }
            }
            else if (y_label == 'int') {
                if (value == 1) {
                    label = "1";
                }
                else if (o.y_ax.bottom_value > 100000 || o.y_ax.top_value > 10000) {
                    label = Math.round(value / 1000) + "k"
                }
                else {
                    label = Math.round(value);
                }
            }
            else {
                label = Math.round(value);                
            }

            o.text(label, o.edges.left - o.x_margin - 5, y, "right", "middle");

            if (y < (o.edges.top + o.height - 2)) {
                o.line("#ffffff", 1, [{x: o.edges.left - o.x_margin - 3, y: y}, {x: o.edges.left - o.x_margin + 3, y: y}]);
            }
        }
    };

    // Converts epoch (in seconds) to an x value (in the graph).
    o.epoch_to_pixels = function(epoch) {
        return (epoch - o.x_ax.left_value) * o.x_per_unit;
    };

    // Converts a date to an x value (not including the edges).
    o.date_to_pixels = function(year, month, day) {
        day = day || 0;
        month = month || 0;
        return (new Date(year, month, day).getTime() / 1000 - o.x_ax.left_value) * o.x_per_unit;
    };
    
    // Print a time x-axis.
    o.time_x_axis = function(x_label) {
        x_label = x_label || "year";
        

        // Draw season colored base line and labels.

        var seasons = sc2.seasons.sorted;
        var y = o.height;
        var x_from = -o.x_margin; // Start outside actual drawing area.
        var season;
        for (var i = 0; i < seasons.length; ++i) {
            season = seasons[i];
            if (season.end > o.x_ax.left_value && season.start < o.x_ax.right_value) {
                var x_to = Math.min(o.epoch_to_pixels(season.end), o.width);

                // Draw the colored season line, add x_margin to the end (all but the last line will be overwritten by
                // another color causing the last one to be extended just like the first one).
                o.gline(season.color, 2, [{x: x_from, y: y}, {x: x_to + o.x_margin, y: y}]);

                if (x_label == "season") {
                    var label = "Season " + season.id + " (" + season.number + " - " + season.year + ")";
                    var label_width = o.ctx.measureText(label).width;
                    var width = x_to - x_from;
                    if (width > label_width) {
                        var x = sc2.utils.min_max(width / 2, x_from + width / 2, o.width - label_width / 2);
                        o.text(label, o.edges.left + x, o.edges.top + o.height + 3, 'center', 'top');
                    }
                }
                x_from = x_to;
            }
        }

        // Print years/months and year lines.
        
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        function pixel_to_date(x) {
            return new Date((x / o.x_per_unit + o.x_ax.left_value) * 1000);
        }
        
        var start_year = pixel_to_date(-o.x_margin).getFullYear();
        var end_year = pixel_to_date(o.width + o.x_margin).getFullYear();
        
        for (var year = start_year; year <= end_year; ++year) {

            var year_x = o.date_to_pixels(year);
            if (year_x > -o.x_margin && year_x < o.width + o.x_margin) {
                o.gline("#ffffff", 2, [{x: year_x, y: o.height - 7}, {x: year_x, y: o.height + 7}]);
            }
            
            for (var month = 0; month < 12; ++month) {
                var month_start_x = Math.round(o.date_to_pixels(year, month)) + 0.5;
                var month_end_x = Math.round(o.date_to_pixels(year, month + 1)) + 0.5;

                // Month bar.
                if (month_start_x > -o.x_margin && month_start_x < o.width + o.x_margin) {
                    o.gline("#ffffff", 1, [{x: month_start_x, y: o.height - 3}, {x: month_start_x, y: o.height + 3}]);
                }

                // Month label.
                var text_width = o.ctx.measureText(year).width;
                if (x_label == 'month' && month_end_x > text_width / 2 && month_start_x < o.width - text_width / 2) {
                    var text_x = sc2.utils.min_max(0, (month_end_x - month_start_x) / 2 + month_start_x, o.width);
                    o.text(months[month], o.edges.left + text_x, o.edges.top + o.height + 3, 'center', 'top');
                }
            }

            // Draw lotv release line.

            var lotv_label = "LotV Release";
            var lotv_label_width = o.ctx.measureText(lotv_label).width;
            var lotv_release_x = o.date_to_pixels(2015, 10, 9);
            if (lotv_release_x - 10 > 0 && lotv_release_x + 10 < o.width) {
                o.gline('#ffff00', 2, [{x: lotv_release_x, y: o.height + 5}, {x: lotv_release_x, y: o.height - 5}]);
                o.text(lotv_label, o.edges.left + lotv_release_x, o.edges.top + o.height + 3 , 'center', 'top', '#ffff00');
            }
        
            // Year label.
            if (x_label == 'year') {
                var label_x = sc2.utils.min_max(o.ctx.measureText(year).width / 2,
                                            o.date_to_pixels(year, 6),
                                            o.width - o.ctx.measureText(year).width / 2);
                o.text(year, o.edges.left + label_x, o.edges.top + o.height + 3, 'center', 'top');
            }
        }
    };

    // Draw crosshair.
    o.draw_crosshair = function() {
        if (o.crosshair) {
            var x = Math.round(o.crosshair.x + o.edges.left) + 0.5;
            var y = Math.round(o.crosshair.y + o.edges.top) + 0.5;
            o.line("#ffffff", 1, [{x: 0, y: y}, {x: o.canvas.width(), y: y}]);
            o.line("#ffffff", 1, [{x: x, y: 0}, {x: x, y: o.canvas.height()}]);
       }                
    };
    
    // Generic controls change value, use this for callback when registring controls.
    o.controls_change = function(name, value) {
        o.settings[name] = value;

        if (o.initialized) {
            o.new_settings();
            o.redraw();
        }
    };

    // Show mouse stuff.
    o.mouse_on = function(x, y, m) {
        var offset = o.canvas.offset();
        var width = o.update_tooltip(m);
        o.tooltip.show();
        o.tooltip.offset({left: offset.left + Math.min(x + o.edges.left + 20, o.canvas.width() - width - 10),
                          top: offset.top + y + o.edges.top + 20});
        o.crosshair = {x: x, y: y};
        if (o.use_crosshair) {
            o.redraw();
        }
    };

    // Show mouse stuff.
    o.mouse_off = function(x, y, m) {
        o.tooltip.hide();
        if (o.use_crosshair) {
            o.redraw();
        }
        o.crosshair = undefined;
    };
    
    // Callback on mouse move.
    o.mouse_move = function(event) {
        var offset = o.canvas.offset();
        var mouse_x = event.pageX - offset.left - o.edges.left;
        var mouse_y = event.pageY - offset.top - o.edges.top;

        if (mouse_x < -o.edges.left / 2 || mouse_x > o.width + o.edges.right / 2
            || mouse_y < -o.edges.top / 2 || mouse_y > o.height + o.edges.bottom / 2) {
            o.mouse_off();
            return;
        }
        
        // Find best point.

        var min_distance = 1e9;
        var x;
        var y;
        var m;
        for (var i = 0; i < o.points.length; ++i) {
            var point = o.points[i];
            var distance = Math.pow(point.x - mouse_x, 2) + Math.pow(point.y - mouse_y, 2);
            if (distance < min_distance) {
                min_distance = distance;
                x = point.x;
                y = point.y;
                m = point.m;
            }
        }

        if (min_distance < 16 * 16) {
            o.mouse_on(x, y, m);
            return;
        }
        
        o.mouse_off();
    };

    //
    // Callbacks to implement for graphs.
    //

    o.new_settings; // Calculate everyhing needed after new settings. New settings will be set on o.

    o.new_size; // Calculate everything needed after new size. New size will be set on o.

    o.redraw; // Redraw the graph.

    o.update_tooltip; // Update the tooltip data.

    //
    // Functions. 
    //

    // Resize canwas based on 0.30 proportions.
    o.resize_canvas = function() {
        o.canvas[0].width = o.container.width();
        o.canvas[0].height = Math.max(280, Math.round(o.container.width() * 0.30));
    };
    
    // Set new size, call new_size and redraw.
    o.resize = function() {
        o.resize_canvas();
        
        o.width = o.canvas.width() - o.edges.left - o.edges.right;
        o.height = o.canvas.height() - o.edges.top - o.edges.bottom;

        o.new_size();
        o.redraw();
    };

    // Init everything based on the data requested/provided in the constructor.
    o.init = function() {
        window.addEventListener('resize', o.resize, false);
        o.new_settings();
        o.resize();

        o.canvas.on('mousemove', o.mouse_move);
        
        o.container.removeClass('wait');
        o.initialized = true;
    };

    o.resize_canvas();
    
    return o;
};
    
