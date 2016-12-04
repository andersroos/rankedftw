import {deferred_doc_ready} from "./utils";
import {stats_data} from "./stats";
import {GraphBase} from "./graph";
import {Radio} from "./controls";
import {Mode} from "./stats";
import {seasons} from "./seasons";
import {images} from "./images";
import {format_int} from "./utils";
import {default_version, enums_info} from "./settings";
import {TOT} from "./stats";


//
// League distribution table.
//
export let LeagueDistributionTable = function(mode_id) {

    var o = {};

    o.settings = {};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        var stats = Mode(mode_id).get_last();

        var filters = {versions: [parseInt(o.settings.v)]};

        var leagues_by_region = stats.filter_aggregate(filters, ['region', 'league']);
        var leagues = stats.filter_aggregate(filters, ['league']);

        _.each(leagues_by_region.regions, function(region) {
            var t = leagues_by_region.count(region);
            $("#r" + region + "-pop .number").text(format_int(t));
            _.each(leagues_by_region.leagues, function(league) {
                var c = leagues_by_region.count(region, league);
                $("#r" + region + "-l" + league + " .number").text(format_int(c));
                $("#r" + region + "-l" + league + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
            });
        });

        var t = leagues.count();
        $("#r-2-pop .number").text(format_int(t));
        _.each(leagues.leagues, function(league) {
            var c = leagues.count(league);
            $("#r-2-l" + league + " .number").text(format_int(c));
            $("#r-2-l" + league + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
        });
    };

    o.init = function() {
        Radio($("#leagues-table-container ul[ctrl-name='v']"), default_version, o.controls_change);
        $("#leagues-table-container.wait").removeClass("wait");
    };

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id)
    ).done(() => o.init());

    return o;
};

//
// League distribution graph.
//
export let LeagueDistributionGraph = function(mode_id) {

    var o = GraphBase('#leagues-graph-container');

    var data = [];   // Filtered and aggregated data.

    var lines = {};  // Lines by league key between leagues.

    // Update units based on resize or new settings.
    o.update_units = function() {
        o.y_ax.top_value = 0;
        o.y_ax.bottom_value = 100;
        o.y_per_unit = o.height / 100;

        o.x_ax.left_value = data[0].data_time;
        o.x_ax.right_value = data[data.length - 1].data_time;
        o.x_per_unit = o.width / (o.x_ax.right_value - o.x_ax.left_value);
    };

    // Update points based on new data or resize.
    o.update_points = function() {

        o.update_units();

        var new_points = [];

        var line = [];
        var last_line;

        // Baseline.

        for (var i = 0; i < data.length; ++i) {
            line.push({x: o.epoch_to_pixels(data[i].data_time), y: o.height});
        }

        // Add up for each league.

        _.each(enums_info.league_ranking_ids, function(league) {
            last_line = line;
            line = [];
            for (var i = 0; i < data.length; ++i) {
                // Push the line and use data index as mouse over key.
                line.push({x: last_line[i].x,
                           y: last_line[i].y - o.y_per_unit * data[i].aggregate.count(league) / data[i].aggregate.count() * 100,
                           m: i});
            }
            $.merge(new_points, line);
            lines[league] = line;
        });

        // Update points.

        o.points = new_points;
    };

    //
    // Graph callbacks.
    //

    o.new_settings = function() {

        // Get new data.

        var version = parseInt(o.settings.v);
        var filters = {versions: [version]};

        if (parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        var all = [];
        var last_season = -1;
        var stats = Mode(mode_id);
        stats.each_reverse(function(stat) {
            var point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: stat.filter_aggregate(filters, ['league']),
            };
            if (o.settings.sx == 'a' || (o.settings.sx == 'sl' && last_season != point.season_id)) {
                all.push(point);
                last_season = point.season_id;
            }
        }, version);
        all.reverse();
        data = all;

        // Update points.

        o.update_points();
    };

    o.new_size = function() {
        o.update_points();
    };

    o.redraw = function() {
        o.clear();
        o.setup_league_styles();

        for (var li = enums_info.league_ranking_ids.length - 1; li >= 0; --li) {
            o
                .garea(o.league_styles[li], [{x: o.width, y: o.height}, {x: 0, y: o.height}]
                .concat(lines[enums_info.league_ranking_ids[li]]));
        }

        o.y_axis("percent");
        o.time_x_axis("year");
        o.draw_crosshair();
    };

    o.update_tooltip = function(m) {
        function format_tooltip_data(c, t) {
            return {n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"};
        }

        var d = data[m];
        var season = seasons.by_id[d.season_id];
        $('.date', o.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        var t = d.aggregate.count();
        _.each(d.aggregate.leagues, function(league) {
            var e = format_tooltip_data(d.aggregate.count(league), t);
            $('.l' + league + "-n", o.tooltip).text(e.n);
            $('.l' + league + "-p", o.tooltip).text(e.p);
        });
        $('.pop-n', o.tooltip).text(format_int(t));

        return 210;
    };

    //
    // Init functions.
    //

    o.init = _.wrap(o.init, function(wrapped) {
        Radio(o.container.find("ul[ctrl-name='v']"), default_version, o.controls_change);
        Radio(o.container.find("ul[ctrl-name='r']"), '-2', o.controls_change);
        Radio(o.container.find("ul[ctrl-name='sx']"), 'a', o.controls_change);

        wrapped();
    });

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id)
    ).done(function() { o.init(); });

    return o;
};

//
// Population table.
//
export let PopulationTable = function(mode_id) {

    var o = {};

    o.settings = {v: undefined};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        var stat = Mode(mode_id).get_last();

        var filters = {versions: [parseInt(o.settings.v)]};

        var regions = stat.filter_aggregate(filters, ['region']);

        _.each(regions.regions, function(region) {
            $("#r" + region + " .number").text(format_int(regions.count(region)));
        });
        $("#r-2 .number").text(format_int(regions.count()));
    };

    o.init = function() {
        Radio($("#pop-table-container ul[ctrl-name='v']"), default_version, o.controls_change);
        $("#pop-table-container.wait").removeClass("wait");
    };

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id)
    ).done(function() { o.init(); });

    return o;
};

//
// Population graph.
//
export let PopulationGraph = function(mode_id) {

    var o = GraphBase('#pop-graph-container');

    var data = [];     // Filtered and aggregated data.
    var max_y = 0.001;     // Max y value.

    // Update units based on resize or new settings.
    o.update_units = function() {
        o.y_ax.top_value = max_y;
        o.y_ax.bottom_value = 0;
        o.y_per_unit = o.height / (o.y_ax.bottom_value - o.y_ax.top_value);

        o.x_ax.left_value = data[0].data_time;
        o.x_ax.right_value = data[data.length - 1].data_time;
        o.x_per_unit = o.width / (o.x_ax.right_value - o.x_ax.left_value);
    };

    // Update points based on new data or resize.
    o.update_points = function() {

        o.update_units();

        var new_points = [];

        for (var i = 0; i < data.length; ++i) {
            new_points.push({x: o.epoch_to_pixels(data[i].data_time),
                             y: o.height + o.y_per_unit * data[i].y_value,
                             m: i});
        }

        o.points = new_points;
    };

    //
    // Graph callbacks.
    //

    o.new_settings = function() {

        // Get new data.

        var version = parseInt(o.settings.v);
        var filters = {versions: [version]};

        if (parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        data = [];
        max_y = 0.001;
        var last_season = -1;
        var stats = Mode(mode_id);
        stats.each_reverse(function(stat) {
            var aggregate = stat.filter_aggregate(filters, []);
            var season = seasons.by_id[stat.season_id];
            var point = {
                season_id: season.id,
                season_age: (stat.data_time - season.start) / (24 * 3600),
                data_time: stat.data_time,
                count: aggregate.count(),
                games: aggregate.wins() + aggregate.losses(),
            };
            if (o.settings.sx == 'a' || (o.settings.sx == 'sl' && last_season != point.season_id)) {
                data.push(point);
                last_season = point.season_id;
            }
        }, version);
        data.reverse();
        var first_season = last_season;

        last_season = -1;
        for (var i = 0; i < data.length; ++i) {
            var point = data[i];
            if (first_season != last_season) {
                point.d_games = point.games;
                point.d_age = point.season_age;
            }
            else {
                point.d_games = point.games - data[i - 1].games;
                point.d_age = point.season_age - data[i - 1].season_age;
            }
            point.games_per_day = point.d_games / point.d_age;

            if (o.settings.sy == 'c') {
                point.y_value = point.count;
            }
            else if (o.settings.sy == 'g') {
                point.y_value = point.games_per_day;
            }

            max_y = Math.max(max_y, point.y_value);
        }

        // Update points.

        o.update_points();
    };

    o.new_size = function() {
        o.update_points();
    };

    o.redraw = function() {
        o.clear();
        o.setup_league_styles();
        o.gline("#ffffaa", 2, o.points);
        o.y_axis("int");
        o.time_x_axis("year");
        o.draw_crosshair();
    };

    o.update_tooltip = function(m) {
        var d = data[m];
        var season = seasons.by_id[d.season_id];
        $('.date', o.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        $('.season-age', o.tooltip).text(Math.round(d.season_age) + " days");
        $('.pop-n', o.tooltip).text(format_int(d.count));
        $('.gpd', o.tooltip).text(format_int(Math.round(d.games_per_day)));
        $('.games', o.tooltip).text(format_int(Math.round(d.games)));

        return 188;
    };

    //
    // Init functions.
    //

    o.init = _.wrap(o.init, function(wrapped) {
        Radio(o.container.find("ul[ctrl-name='v']"), default_version, o.controls_change);
        Radio(o.container.find("ul[ctrl-name='r']"), '-2', o.controls_change);
        Radio(o.container.find("ul[ctrl-name='sx']"), 'a', o.controls_change);
        Radio(o.container.find("ul[ctrl-name='sy']"), 'c', o.controls_change);

        wrapped();
    });

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id)
    ).done(function() { o.init(); });

    return o;
};


//
// Rrace distribution graph.
//
export let RaceDistributionGraph = function(mode_id) {

    var o = GraphBase('#races-graph-container');

    var data = [];   // Filtered and aggregated data.

    var lines = {};  // Lines by race key between races.

    var max_value = 1;

    // Update units based on resize or new settings.
    o.update_units = function() {
        o.y_ax.top_value = max_value;
        o.y_ax.bottom_value = 0;
        o.y_per_unit = o.height / (o.y_ax.bottom_value - o.y_ax.top_value);

        o.x_ax.left_value = data[0].data_time;
        o.x_ax.right_value = data[data.length - 1].data_time;
        o.x_per_unit = o.width / (o.x_ax.right_value - o.x_ax.left_value);
    };

    // Update points based on new data or resize.
    o.update_points = function() {

        o.update_units();

        lines = {};
        var new_points = [];

        for (var i = 0; i < data.length; ++i) {
            var x = o.epoch_to_pixels(data[i].data_time);
            _.each(enums_info.race_ranking_ids, function(race_id) {
                var y = o.y_per_unit * (data[i].aggregate.count(race_id) / data[i].aggregate.count() * 100 - max_value);
                lines[race_id] = lines[race_id] || [];
                lines[race_id].push({x: x, y: y, m: i});
            });
        }

        _.each(enums_info.race_ranking_ids, function(race_id) {
            $.merge(new_points, lines[race_id]);
        });

        // Update points.

        o.points = new_points;
    };

    //
    // Graph callbacks.
    //

    o.new_settings = function() {

        // Get new data.
        var v = parseInt(o.settings.v);
        var r = parseInt(o.settings.r);
        var l = parseInt(o.settings.l);

        var filters = {versions: [v]};

        if (r !== TOT) {
            filters.regions = [r];
        }

        if (l !== TOT) {
            filters.leagues = [l];
        }

        if (l == 6 && v == 0) {
            // GM WoL data is totally broken, let's just not show it.
            filters.leagues = [];
        }

        max_value = 1;

        var all = [];
        var stats = Mode(mode_id);
        stats.each(function(stat) {
            var aggregate = stat.filter_aggregate(filters, ['race']);
            var point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: aggregate,
            };
            all.push(point);
            var t = point.aggregate.count();
            if (t) {
                _.each(aggregate.races, function(race) {
                    max_value = Math.max(max_value, point.aggregate.count(race) / t * 100);
                });
            }
        }, v);
        data = all;

        // Update points.

        o.update_points();
    };

    o.new_size = function() {
        o.update_points();
    };

    o.redraw = function() {
        o.clear();

        _.each(enums_info.race_ranking_ids, function(race) {
            o.gline(o.race_colors[race], 2, lines[race]);
        });

        _.each(enums_info.race_ranking_ids, function(race) {
            o.ctx.drawImage(document.getElementById('race' + race),
                            lines[race][0].x - 8 + o.edges.left,
                            lines[race][0].y - 8 + o.edges.top);
        });
        o.y_axis("percent");
        o.time_x_axis("year");
        o.draw_crosshair();
    };

    o.update_tooltip = function(m) {
        function format_tooltip_data(c, t) {
            return {n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"};
        }

        var d = data[m];
        var season = seasons.by_id[d.season_id];
        $('.date', o.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        var t = d.aggregate.count();
        _.each(enums_info.race_ranking_ids, function(race) {
            var e = format_tooltip_data(d.aggregate.count(race), t);
            $('.r' + race + '-n', o.tooltip).text(e.n);
            $('.r' + race + '-p', o.tooltip).text(e.p);
        });
        $('.pop-n', o.tooltip).text(format_int(t));
        return 210;
    };

    //
    // Init functions.
    //

    o.init = _.wrap(o.init, function(wrapped) {
        Radio(o.container.find("ul[ctrl-name='v']"), default_version, o.controls_change);
        Radio(o.container.find("ul[ctrl-name='r']"), '-2', o.controls_change);
        Radio(o.container.find("ul[ctrl-name='l']"), '-2', o.controls_change);

        wrapped();
    });

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id)
    ).done(function() { o.init(); });

    return o;
};

//
// Race distribution table.
//
export let RaceDistributionTable = function(mode_id) {

    var o = {};

    o.settings = {};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        var stat = Mode(mode_id).get_last();

        var filters = {versions: [parseInt(o.settings.v)]};

        if (!_.isUndefined(o.settings.r) && parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        var races_by_league = stat.filter_aggregate(filters, ['league', 'race']);

        _.each(races_by_league.leagues, function(league) {
            var t = races_by_league.count(league);
            _.each(races_by_league.races, function(race) {
                var c = races_by_league.count(league, race);
                $("#l" + league + "-r" + race + " .number").text(format_int(c));
                $("#l" + league + "-r" + race + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
            });
        });
    };

    o.init = function() {
        Radio($("#races-table-container ul[ctrl-name='v']"), default_version, o.controls_change);
        Radio($("#races-table-container ul[ctrl-name='r']"), '-2', o.controls_change);
        $("#races-table-container.wait").removeClass("wait");
    };

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id),
        images.deferred_load_races()
    ).done(function() { o.init(); });

    return o;
};
