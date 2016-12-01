
//
// sc2 "namespace" and global constans.
//

var sc2 = {};

var TOT = -2;
var COUNT = 0;
var WINS = 1;
var LOSSES = 2;

window.TOT = TOT;
window.COUNT = COUNT;
window.WINS = WINS;
window.LOSSES = LOSSES;

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

//
// Common graph stuff.
//

sc2.graph = {};

// Insert image tags for resources listed in options ("leagues") and
// call success when loaded.
sc2.graph.load_resources = function(container_selector, options, success) {
    
};

    
export let seasons = sc2.seasons;