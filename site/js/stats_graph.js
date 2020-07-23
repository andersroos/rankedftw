import {deferred_doc_ready, format_int, to_jq_element} from "./utils";
import {stats_data, Mode, TOT} from "./stats";
import {GraphBase} from "./graph";
import {Radio} from "./controls";
import {seasons} from "./seasons";
import {images} from "./images";
import {settings} from "./settings";


export const create_version_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    return new Radio(graph_jq.find(".controls").find(".content"), 'v', 'Version:',
        settings.enums_info.version_ranking_ids
                  .map(vid => ({value: vid, heading: settings.enums_info.version_name_by_ids[vid]}))
                  .reverse(),
        settings.default_version, cb);
};


export const create_region_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
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


export const create_league_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
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


export const create_x_axis_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    return new Radio(graph_jq.find(".controls").find(".content"), 'sx', 'X-Axis:', [
            {value: 'a', heading: 'All', tooltip: 'Show all data'},
            {value: 'sl', heading: 'Season Last', tooltip: 'Show only one point in graph for each season.'},
    ], 'a', cb)
};


//
// League distribution table.
//
// TODO OLD OBJECT, JQ SELECT, JQ PROMISE
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

        // TODO UNDERSCORE
        leagues_by_region.regions.forEach(region => {
            const t = leagues_by_region.count(region);
            $("#r" + region + "-pop .number").text(format_int(t));
            leagues_by_region.leagues.forEach(league => {
                const c = leagues_by_region.count(region, league);
                $("#r" + region + "-l" + league + " .number").text(format_int(c));
                $("#r" + region + "-l" + league + " .percent").text("(" + (c * 100 / t).toFixed(2) + "%)");
            });
        });

        const t = leagues.count();
        $("#r-2-pop").find(".number").text(format_int(t));
        leagues.leagues.forEach(league => {
            const c = leagues.count(league);
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
// TODO OLD OBJECT, JQ MERGE ARRAY, UNDERSCORE, JQ SELECT, JQ PROMISE
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

        settings.enums_info.league_ranking_ids.forEach(league => {
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
        const t = d.aggregate.count();
        d.aggregate.leagues.forEach(league => {
            const e = format_tooltip_data(d.aggregate.count(league), t);
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
// TODO OLD OBJECT, UNDERSCORE, JQ SELECT, JQ PROMISE
export let PopulationTable = function(mode_id) {

    let o = {};

    let container = $("#pop-table-container");

    o.settings = {v: null};

    o.controls_change = function(name, value) {
        o.settings[name] = value;

        let stat = Mode(mode_id).get_last();

        let filters = {versions: [parseInt(o.settings.v)]};

        let regions = stat.filter_aggregate(filters, ['region']);

        regions.regions.forEach(region => {
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
// TODO OLD OBJECT, UNDERSCORE, JQ SELECT, JQ PROMISE
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
