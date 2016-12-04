
//
// Utils.
//

let sc2 = {};

sc2.utils = {};

// Reverse each of func.
sc2.utils.rev_each = function(list, fun) {
    for (var i = list.length - 1; i >= 0; --i) {
        fun(list[i], i);
    }
};

// Return the value value, but make sure it is in the range [min, max].
sc2.utils.min_max = function(min, value, max) {
    return Math.min(Math.max(min, value), max);
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
// Common statistcs related code.
//

sc2.stats = {};

sc2.stats._deferred = {};

sc2.stats._all_raws_by_mode = {};

//
// Common graph stuff.
//

sc2.graph = {};

// Insert image tags for resources listed in options ("leagues") and
// call success when loaded.
sc2.graph.load_resources = function(container_selector, options, success) {
    
};

    
export let seasons = sc2.seasons;