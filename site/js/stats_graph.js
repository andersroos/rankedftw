import {deferred_doc_ready, format_int} from "./utils";
import {stats_data, Mode, TOT} from "./stats";
import {GraphBase} from "./graph";
import {Radio} from "./controls";
import {seasons} from "./seasons";
import {images} from "./images";
import {settings} from "./settings";


let create_version_control = (graph_jq, cb) => {
    return new Radio(graph_jq.find(".controls").find(".content"), 'v', 'Version:',
        settings.enums_info.version_ranking_ids
                  .map(vid => ({value: vid, heading: settings.enums_info.version_name_by_ids[vid]}))
                  .reverse(),
        settings.default_version, cb);
};


let create_region_control = (graph_jq, cb) => {
    let regions = [settings.ALL].concat(settings.enums_info.region_ranking_ids);
    return new Radio(graph_jq.find(".controls").find(".content"), 'r', 'Regions:',
        regions
            .map(rid => ({
                value: rid,
                heading: settings.enums_info.region_name_by_ids[rid],
                src: settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[rid] + '-16x16.png'
            })),
        settings.ALL, cb)
};


let create_league_control = (graph_jq, cb) => {
    let leagues = [settings.ALL].concat(settings.enums_info.league_ranking_ids.reverse());
    return new Radio(graph_jq.find(".controls").find(".content"), 'l', 'League:',
        leagues
            .map(lid => ({
                value: lid,
                heading: lid === settings.ALL ? settings.enums_info.league_name_by_ids[lid] : null,
                src: lid === settings.ALL ? null : settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[lid] + '-16x16.png',
                tooltip: settings.enums_info.league_name_by_ids[lid],
            })),
        settings.ALL, cb);
};


let create_x_axis_control = (graph_jq, cb) => {
    return new Radio(graph_jq.find(".controls").find(".content"), 'sx', 'X-Axis:', [
            {value: 'a', heading: 'All', tooltip: 'Show all data'},
            {value: 'sl', heading: 'Season Last', tooltip: 'Show only one point in graph for each season.'},
    ], 'a', cb)
};


//
// League distribution table.
//
export let LeagueDistributionTable = function(mode_id) {

    let o = {};

    let container = $("#leagues-table-container");

    o.settings = {};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        let stats = Mode(mode_id).get_last();

        let filters = {versions: [parseInt(o.settings.v)]};

        let leagues_by_region = stats.filter_aggregate(filters, ['region', 'league']);
        let leagues = stats.filter_aggregate(filters, ['league']);

        _.each(leagues_by_region.regions, function(region) {
            let t = leagues_by_region.count(region);
            $("#r" + region + "-pop .number").text(format_int(t));
            _.each(leagues_by_region.leagues, function(league) {
                let c = leagues_by_region.count(region, league);
                $("#r" + region + "-l" + league + " .number").text(format_int(c));
                $("#r" + region + "-l" + league + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
            });
        });

        let t = leagues.count();
        $("#r-2-pop").find(".number").text(format_int(t));
        _.each(leagues.leagues, function(league) {
            let c = leagues.count(league);
            $("#r-2-l" + league + " .number").text(format_int(c));
            $("#r-2-l" + league + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
        });
    };

    o.version_control = create_version_control(container, o.controls_change);

    o.init = function() {
        o.version_control.init();
        container.removeClass("wait");
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

    let o = GraphBase('#leagues-graph-container');

    o.version_control = create_version_control(o.container, o.controls_change);
    o.region_control = create_region_control(o.container, o.controls_change);
    o.x_axis_control = create_x_axis_control(o.container, o.controls_change);

    let data = [];   // Filtered and aggregated data.

    let lines = {};  // Lines by league key between leagues.

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

        let new_points = [];

        let line = [];
        let last_line;

        // Baseline.

        for (let i = 0; i < data.length; ++i) {
            line.push({x: o.epoch_to_pixels(data[i].data_time), y: o.height});
        }

        // Add up for each league.

        _.each(settings.enums_info.league_ranking_ids, function(league) {
            last_line = line;
            line = [];
            for (let i = 0; i < data.length; ++i) {
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

        let version = parseInt(o.settings.v);
        let filters = {versions: [version]};

        if (parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        let all = [];
        let last_season = -1;
        let stats = Mode(mode_id);
        stats.each_reverse(function(stat) {
            let point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: stat.filter_aggregate(filters, ['league']),
            };
            if (o.settings.sx === 'a' || (o.settings.sx === 'sl' && last_season !== point.season_id)) {
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

        for (let li = settings.enums_info.league_ranking_ids.length - 1; li >= 0; --li) {
            o
                .garea(o.league_styles[li], [{x: o.width, y: o.height}, {x: 0, y: o.height}]
                .concat(lines[settings.enums_info.league_ranking_ids[li]]));
        }

        o.y_axis("percent");
        o.time_x_axis("year");
        o.draw_crosshair();
    };

    o.update_tooltip = function(m) {
        function format_tooltip_data(c, t) {
            return {n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"};
        }

        let d = data[m];
        let season = seasons.by_id[d.season_id];
        $('.date', o.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        let t = d.aggregate.count();
        _.each(d.aggregate.leagues, function(league) {
            let e = format_tooltip_data(d.aggregate.count(league), t);
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
        o.version_control.init();
        o.region_control.init();
        o.x_axis_control.init();
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

    let o = {};

    let container = $("#pop-table-container");

    o.settings = {v: null};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        let stat = Mode(mode_id).get_last();

        let filters = {versions: [parseInt(o.settings.v)]};

        let regions = stat.filter_aggregate(filters, ['region']);

        _.each(regions.regions, function(region) {
            $("#r" + region + " .number").text(format_int(regions.count(region)));
        });
        $("#r-2 .number").text(format_int(regions.count()));
    };

    o.version_control = create_version_control(container, o.controls_change);

    o.init = function() {
        o.version_control.init();
        container.removeClass("wait");
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

    let o = GraphBase('#pop-graph-container');

    o.version_control = create_version_control(o.container, o.controls_change);
    o.region_control = create_region_control(o.container, o.controls_change);
    o.y_axis_control = new Radio(o.container.find(".controls").find(".content"), 'sy', 'Y-Axis:', [
        {value: 'c', heading: 'Teams', tooltip: 'Number of ranked teams in the season.'},
        {value: 'g', heading: 'Games/Day', tooltip: 'Average number of played games per day.'},
    ], 'c', o.controls_change);
    o.x_axis_control = create_x_axis_control(o.container, o.controls_change);

    let data = [];     // Filtered and aggregated data.
    let max_y = 0.001;     // Max y value.

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

        let new_points = [];

        for (let i = 0; i < data.length; ++i) {
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

        let version = parseInt(o.settings.v);
        let filters = {versions: [version]};

        if (parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        data = [];
        max_y = 0.001;
        let last_season = -1;
        let stats = Mode(mode_id);
        stats.each_reverse(function(stat) {
            let aggregate = stat.filter_aggregate(filters, []);
            let season = seasons.by_id[stat.season_id];
            let point = {
                season_id: season.id,
                season_age: (stat.data_time - season.start) / (24 * 3600),
                data_time: stat.data_time,
                count: aggregate.count(),
                games: aggregate.wins() + aggregate.losses(),
            };
            if (o.settings.sx === 'a' || (o.settings.sx === 'sl' && last_season !== point.season_id)) {
                data.push(point);
                last_season = point.season_id;
            }
        }, version);
        data.reverse();
        let first_season = last_season;

        last_season = -1;
        for (let i = 0; i < data.length; ++i) {
            let point = data[i];
            if (first_season !== last_season) {
                point.d_games = point.games;
                point.d_age = point.season_age;
            }
            else {
                point.d_games = point.games - data[i - 1].games;
                point.d_age = point.season_age - data[i - 1].season_age;
            }
            point.games_per_day = point.d_games / point.d_age;

            if (o.settings.sy === 'c') {
                point.y_value = point.count;
            }
            else if (o.settings.sy === 'g') {
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
        let d = data[m];
        let season = seasons.by_id[d.season_id];
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
        o.version_control.init();
        o.region_control.init();
        o.y_axis_control.init();
        o.x_axis_control.init();

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

    let o = GraphBase('#races-graph-container');

    let data = [];   // Filtered and aggregated data.

    let lines = {};  // Lines by race key between races.

    let max_value = 1;

    o.version_control = create_version_control(o.container, o.controls_change);
    o.region_control = create_region_control(o.container, o.controls_change);
    o.league_control = create_league_control(o.container, o.controls_change);

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
        let new_points = [];

        for (let i = 0; i < data.length; ++i) {
            let x = o.epoch_to_pixels(data[i].data_time);
            _.each(settings.enums_info.race_ranking_ids, function(race_id) {
                let y = o.y_per_unit * (data[i].aggregate.count(race_id) / data[i].aggregate.count() * 100 - max_value);
                lines[race_id] = lines[race_id] || [];
                lines[race_id].push({x: x, y: y, m: i});
            });
        }

        _.each(settings.enums_info.race_ranking_ids, function(race_id) {
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
        let v = parseInt(o.settings.v);
        let r = parseInt(o.settings.r);
        let l = parseInt(o.settings.l);

        let filters = {versions: [v]};

        if (r !== TOT) {
            filters.regions = [r];
        }

        if (l !== TOT) {
            filters.leagues = [l];
        }

        if (l === 6 && v === 0) {
            // GM WoL data is totally broken, let's just not show it.
            filters.leagues = [];
        }

        max_value = 1;

        let all = [];
        let stats = Mode(mode_id);
        stats.each(function(stat) {
            let aggregate = stat.filter_aggregate(filters, ['race']);
            let point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: aggregate,
            };
            all.push(point);
            let t = point.aggregate.count();
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

        _.each(settings.enums_info.race_ranking_ids, function(race) {
            o.gline(o.race_colors[race], 2, lines[race]);
        });

        _.each(settings.enums_info.race_ranking_ids, function(race) {
            const elem = document.getElementById('race' + race);
            const x_offset = elem.width / 2;
            const y_offset = elem.height / 2;
            o.ctx.drawImage(elem,
                            lines[race][0].x - x_offset + o.edges.left,
                            lines[race][0].y - y_offset + o.edges.top,
                            elem.width, elem.height);
        });
        o.y_axis("percent");
        o.time_x_axis("year");
        o.draw_crosshair();
    };

    o.update_tooltip = function(m) {
        function format_tooltip_data(c, t) {
            return {n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"};
        }

        let d = data[m];
        let season = seasons.by_id[d.season_id];
        $('.date', o.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        let t = d.aggregate.count();
        _.each(settings.enums_info.race_ranking_ids, function(race) {
            let e = format_tooltip_data(d.aggregate.count(race), t);
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
        o.version_control.init();
        o.region_control.init();
        o.league_control.init();
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

    let o = {};

    o.settings = {};

    let container = $("#races-table-container");

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        let stat = Mode(mode_id).get_last();

        let filters = {versions: [parseInt(o.settings.v)]};

        if (!_.isUndefined(o.settings.r) && parseInt(o.settings.r) !== TOT) {
            filters.regions = [parseInt(o.settings.r)];
        }

        let races_by_league = stat.filter_aggregate(filters, ['league', 'race']);

        _.each(races_by_league.leagues, function(league) {
            let t = races_by_league.count(league);
            _.each(races_by_league.races, function(race) {
                let c = races_by_league.count(league, race);
                $("#l" + league + "-r" + race + " .number").text(format_int(c));
                $("#l" + league + "-r" + race + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
            });
        });
    };

    o.version_control = create_version_control(container, o.controls_change);
    o.region_control = create_region_control(container, o.controls_change);

    o.init = function() {
        o.version_control.init();
        o.region_control.init();
        container.removeClass("wait");
    };

    $.when(
        deferred_doc_ready(),
        stats_data.deferred_fetch_mode(mode_id),
        images.deferred_load_races()
    ).done(function() { o.init(); });

    return o;
};
