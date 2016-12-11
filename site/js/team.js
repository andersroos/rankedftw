import {GraphBase} from "./graph";
import {static_url, enums_info, dynamic_url} from "./settings";
import {seasons} from "./seasons";
import {images} from "./images";
import {Radio} from "./controls";
import {deferred_doc_ready, rev_each, format_int} from "./utils";
import {stats_data, Mode} from "./stats";

//
// Add classes to container.
//
let conf_container = function(jq_container) {
    jq_container.addClass('data-container wait');
};

//
// Add controls to container and returns of controls container.
//
let add_controls_div = function(jq_container) {
    let controls = $('<div class="controls">');
    let content = $('<div class="content">');
    controls.append(content);
    jq_container.append(controls);
    return content;
};

//
// Add canvas element to container.
//
let add_canvas = function(jq_container) {
    jq_container.append('<canvas class="graph">');
};

//
// Add tooltip element to container. Table is a list of <heading, data-class>.
//
let add_tooltip = function(jq_container, data) {
    let tooltip = $('<div class="tooltip">');
    let table = $('<table>');
    for (let i = 0; i < data.length; ++i) {
        let tr = $('<tr>');
        tr.append("<th>" + data[i][0] + "</th>");
        tr.append("<td class='" + data[i][1] + "'></td>");
        table.append(tr);
    }
    tooltip.append(table);
    jq_container.append(tooltip);
};

//
// The ranking graph object.
//
export let RankingGraph = function(container_id, team_id, region_id, league_id, mode_id) {
    
    //
    // Set up basic html for container canvas and controls.
    //

    let container = $('#' + container_id);
    
    conf_container(container);

    let controls = add_controls_div(container);

    //
    // Add tooltip.
    //

    add_tooltip(container, [
        ['Date:',   'date'],
        ['Version', 'version'],
        ['World:',  'world_rank'],
        ['Region:', 'region_rank'],
        ['League:', 'league_rank'],
        ['Ladder:', 'ladder_rank'],
        ['Season:', 'season'],
        ['MMR:', 'mmr'],
        ['Points:', 'points'],
        ['Wins:',   'wins'],
        ['Losses:', 'losses'],
        ['Race:', 'race'],
        ['League:', 'league'],
    ]);

    //
    // Init graph base.
    //

    add_canvas(container);
    let o = GraphBase('#' + container_id);

    //
    // Add controls.
    //

    // Return race options depending on what is available in rankings.
    o.get_race_options = (rankings) => {
        let options = [{value: 'best', heading: 'Best', tooltip: 'Show ranking for best race in each data point.'}];
        let races_present = rankings.map(r => r.race0);
        options.push(...enums_info.race_ranking_ids.filter(rid => rid >= 0 && races_present.includes(rid)).map(rid => ({
            value: rid,
            src: static_url + 'img/races/' + enums_info.race_key_by_ids[rid] + '-16x16.png',
            tooltip:'Show only ' + enums_info.race_name_by_ids[rid] + ' data points.',
        })));
        return options;
    };

    o.data_control = new Radio(controls, 'td', 'Data:', [
            {value: 'world', heading: 'World', src: static_url + 'img/regions/world-16x16.png', tooltip: 'Show world ranking for team.'},
            {value: 'region', heading: 'Region', src: static_url + 'img/regions/' + enums_info.region_key_by_ids[region_id] + '-16x16.png', tooltip: 'Show region ranking for team.'},
            {value: 'league', heading: 'League', src: static_url + 'img/leagues/' + enums_info.league_key_by_ids[league_id] + '-16x16.png', tooltip: 'Show league ranking (in region) for team.'},
        ], 'world', o.controls_change);

    o.y_axis_control = new Radio(controls, 'ty', 'Y-Axis:', [
        {value: 'c', heading: 'Percent', tooltip: 'Percent on y-axis, % of teams ranked above team.'},
        {value: 'm', heading: 'MMR', tooltip: 'MMR on y-axis, 0 at the bottom. Note that this graph does not change for different types of data since the points are always the same. This will hide all parts of the graph where mmr was not avaiable.'},
        {value: 'r', heading: 'Rank', tooltip: 'Absolute rank on y-axis, no 1 at the top. The grey area (or league distribution area) indicates all ranked teams from the top to the bottom at that point in time.'},
    ], 'c', o.controls_change);

    if (enums_info.mode_key_by_ids[mode_id] === '1v1') {
        o.race_control = new Radio(controls, 'ra', 'Race:', o.get_race_options([]), 'best', o.controls_change);
    }

    o.y_zoom_control = new Radio(controls, 'tyz', 'Y-Zoom:', [
        {value: '0', heading: 'Off', tooltip: 'No zoom, show full scale to see teams position relative to everyone.'},
        {value: '1', heading: 'On', tooltip: 'This will cause the graph to zoom in to make the graph line fill the y-space.'},
    ], 0, o.controls_change);

    o.x_axis_control = new Radio(controls, 'tx', 'X-Axis:', [
        {value: 'a', heading: 'All', tooltip: 'Show all data.'},
        {value: 's', heading: 'Season', tooltip: 'Show current/last available season for this player.'},
        {value: '60', heading: '60-Days', tooltip: 'Show last 60 days.'},
    ], 'a', o.controls_change);

    o.background_control = new Radio(controls, 'tl', 'Leagues:', [
        {value: '0', heading: 'Off', tooltip: 'League distribution background off.'},
        {value: '1', heading: 'On', tooltip: 'League distribution background on, there will be no league background for "league" graph.'},
    ], 1, o.controls_change);

    //
    // Calculated units by settings and size.
    //

    let start_ranking_index; // Start ranking for time selection, index among f_rankings.
    let end_ranking_index; // End ranking for time selection, index among f_rankings.

    let f_rankings; // Rankings filtered on race setting.

    let max_rank_all; // One value per settings.data.

    let max_rank; // One value per settings.data.
    let min_rank; // One value per settings.data.

    let max_percent; // One value per settings.data.
    let min_percent; // One value per settings.data.

    let min_mmr; // Min among points.
    let max_mmr; // Max among points.
    
    //
    // Data for the graph.
    //

    o.points = [];          // Points {x, y, m} calcualted from rankings (m is the index in o.rankings).
    let leagues = [];       // List of {x, y, league} for when league changes.
    let floor = [];         // Points {x, y} used when there is an absolute floor.
    let league_areas = {};  // Map from leagues to lists of league area points, league areas should be drawn in
                            // backwards order since they overlap (from gm to bronze)

    //
    // Functions.
    //
    
    // Updating of units needs to be done after a resize or after settings changed.
    o.update_units = function() {
        
        let start = 0;
        end_ranking_index = f_rankings.length - 1;
        o.x_ax.right_value = f_rankings[end_ranking_index].data_time;

        if (o.settings.ty === 'm') {
            for (let i = end_ranking_index; i >= 0; --i) {
                if  (typeof f_rankings[i].mmr !== 'undefined') {
                    start = i;
                }
            }
        }

        if (o.settings.tx === 'a') {
            start_ranking_index = start;
        }
        else if (o.settings.tx === 's') {
            let season_id = f_rankings[end_ranking_index].season_id;
            for (let i = end_ranking_index; i >= start; --i) {
                if (season_id === f_rankings[i].season_id) {
                    start_ranking_index = i;
                }
            }
        }
        else if (o.settings.tx === '60') {
            for (let i = end_ranking_index; i >= start; --i) {
                if (o.x_ax.right_value - f_rankings[i].data_time < 3600 * 24 * 60) {
                    start_ranking_index = i;
                }
            }
        }
        o.x_ax.left_value = f_rankings[start_ranking_index].data_time;
        
        max_rank_all = {world: 0, region: 0, league: 0};
        max_rank = {world: 0, region: 0, league: 0};
        min_rank = {world: 1e9, region: 1e9, league: 1e9};
        max_percent = {world: 0, region: 0, league: 0};
        min_percent = {world: 1e9, region: 1e9, league: 1e9};
        min_mmr = 1e9;
        max_mmr = 0;
        
        for (let i = start_ranking_index; i <= end_ranking_index; ++i) {
            $.each(['world', 'region', 'league'], function(j, key) {
                let count = f_rankings[i][key + "_count"];
                let rank =  f_rankings[i][key + "_rank"];

                max_rank_all[key] = Math.max(max_rank_all[key], count);
                
                min_rank[key] = Math.min(min_rank[key], rank);
                max_rank[key] = Math.max(max_rank[key], rank + 0.1);
                
                min_percent[key] = Math.max(Math.min(min_percent[key], 100 * rank / count - 0.001), 0);
                max_percent[key] = Math.min(Math.max(max_percent[key], 100 * rank / count + 0.001), 100);
            });
            min_mmr = Math.min(min_mmr, f_rankings[i].mmr);
            max_mmr = Math.max(max_mmr, f_rankings[i].mmr);
        }
        
        o.x_per_unit = o.width / (o.x_ax.right_value - o.x_ax.left_value + 0.01);

        if (o.settings.tyz === "1") {
            if (o.settings.ty === "c") {
                o.y_ax.top_value = min_percent[o.settings.td];
                o.y_ax.bottom_value = Math.min(100, max_percent[o.settings.td] * 1.02);
            }
            else if (o.settings.ty === "m") {
                o.y_ax.top_value = max_mmr;
                o.y_ax.bottom_value = Math.max(0, min_mmr - o.y_ax.top_value * 0.02);
            }
            else if (o.settings.ty === "r") {
                o.y_ax.top_value = min_rank[o.settings.td];
                o.y_ax.bottom_value = max_rank[o.settings.td] * 1.02;
            }
        }
        else {
            if (o.settings.ty === "c") {
                o.y_ax.top_value = 0;
                o.y_ax.bottom_value = 100;
            }
            else if (o.settings.ty === "m") {
                o.y_ax.top_value = max_mmr;
                o.y_ax.bottom_value = 0;
            }
            else if (o.settings.ty === "r") {
                o.y_ax.top_value = 1;
                o.y_ax.bottom_value = max_rank_all[o.settings.td];
            }
        }
        o.y_per_unit = o.height / (o.y_ax.bottom_value - o.y_ax.top_value);
    };

    //
    // Drawing functions.
    //
        
    // Print the y axis.
    o.y_axis = _.wrap(o.y_axis, function(wrapped) {
        wrapped({'c': 'percent', 'r': 'int', 'm': 'int'}[o.settings.ty]);
    });

    // Print the x axis.
    o.time_x_axis = _.wrap(o.time_x_axis, function(wrapped) {
        wrapped({"s": "season", "a": "year", "60": "month"}[o.settings.tx]);
    });

    // Get y value for ranking based on settings.
    o.ranking_y_value = function(ranking) {
        if (o.settings.ty === 'c') {
            return o.y_value(ranking[o.settings.td + "_rank"], ranking[o.settings.td + "_count"]);
        }
        else if (o.settings.ty === 'r') {
            return o.y_value(ranking[o.settings.td + "_rank"]);
        }
        else if (o.settings.ty === 'm') {
            return o.y_value(ranking.mmr);
        }
        return null;
    };

    // Calculate y-value based on settings and ranking value and count.
    o.y_value = function(value, count) {
        if (o.settings.ty === 'c') {
            return (100 * value / count - o.y_ax.top_value) * o.y_per_unit;
        }
        else if (o.settings.ty === 'r') {
            return (value - o.y_ax.top_value) * o.y_per_unit;
        }
        else if (o.settings.ty === 'm') {
            return (value - o.y_ax.top_value) * o.y_per_unit;
        }
        return null;
    };    
    
    //
    // Callbacks to implement for graphs.
    //

    o.new_settings = function() {

        // Start by filtering rankings on race settings, then.
        if (typeof o.settings.ra === 'undefined' || o.settings.ra === 'best') {
            f_rankings = o.rankings.filter(r => r.best_race);
        }
        else {
            let race = parseInt(o.settings.ra);
            f_rankings = o.rankings.filter(r => r.race0 === race);
        }

        o.update_units();

        // Calculate if floor or leagues background should be drawn.

        if (o.settings.tl === '1' && o.settings.td !== 'league' && o.settings.ty !== 'm') {
            o.settings.bg = 'leagues';
        }
        else if (o.settings.ty === 'r') {
            o.settings.bg = 'floor';
        }
        else {
            o.settings.bg = null;
        }

        // Set up filter for leagues background (version is different for each point).

        let filters;
        if (o.settings.bg === 'leagues') {
            filters = {};
            if (o.settings.td !== 'world') {
                filters.regions = [region_id];
            }
        }
        
        // Calculate new points and background.

        o.points = [];
        floor = [];
        leagues = [];
        league_areas = {};

        let league = -64;
        for (let i = start_ranking_index; i <= end_ranking_index; ++i) {
            let ranking = f_rankings[i];
            let x = o.epoch_to_pixels(ranking.data_time);
            let y = o.ranking_y_value(ranking);
            let count = ranking[o.settings.td + "_count"];
            o.points.push({x: x, y: y, m: ranking.index});
            
            if (o.settings.bg) {
                floor.push({x: x, y: o.y_value(count, count)});
            }
            if (o.settings.bg === 'leagues') {
                let stat = Mode(mode_id).get(ranking.id);
                filters.versions = [ranking.version];
                let agg = stat.filter_aggregate(filters, ['league']);
                let ly = 0;
                rev_each(enums_info.league_ranking_ids, function(lid) {
                    league_areas[lid] = league_areas[lid] || [];
                    league_areas[lid].push({x: x, y: o.y_value(ly, count)});
                    ly += agg.count(lid);
                });
            }
            
            if (league !== ranking.league) {
                league = ranking.league;
                leagues.push({x: o.edges.left + x, y: o.edges.top + y, league: league});
            }
        }

        // Make the areas areas.
        if (o.settings.bg === 'floor') {
            $.merge(floor, [{x: o.width, y: 0}, {x: 0, y: 0}]);
        }
        else if (o.settings.bg === 'leagues') {
            floor.reverse();
                rev_each(enums_info.league_ranking_ids, function(lid) {
                    $.merge(league_areas[lid], floor);
            });
            $.merge(floor, [{x: 0, y: o.height}, {x: o.width, y: o.height}]);
        }
    };

    o.new_size = function() {
        o.new_settings();
    };
        
    o.redraw = function() {

        // Basis.
        
        o.clear();

        // Background.

        if (o.settings.bg) {
            if (o.settings.bg === 'floor') {
                o.garea("#242424", floor);
            }
            if (o.settings.bg === 'leagues') {
                o.setup_league_styles();
                rev_each(enums_info.league_ranking_ids, function(lid, i) {
                    o.garea(o.league_styles[i], league_areas[lid]);
                });
                o.garea('#000000', floor);
                o.clear(0.3);
            }
            let c_width = o.canvas.width();
            let c_height = o.canvas.height();
            o.area('#000000', [{x: 0, y: 0}, {x: c_width, y: 0},
                               {x: c_width, y: o.edges.top}, {x: 0, y: o.edges.top}]);
            o.area('#000000', [{x: 0, y: o.edges.top + o.height}, {x: c_width, y: o.edges.top + o.height},
                               {x: c_width, y: c_height}, {x: 0, y: c_height}]);
        }

        // Axis.
        
        o.y_axis();
        o.time_x_axis();

        // Graph.
        
        o.gline("#ffffaa", 2, o.points);

        // Tooltip crosshair.

        o.draw_crosshair();

        // League icons.
        
        for (let i = 0; i < leagues.length; ++i) {
            o.ctx.drawImage(document.getElementById('league' + leagues[i].league), leagues[i].x - 8, leagues[i].y - 8);
        }
    };

    o.update_tooltip = function(m) {
        function format_rank(rank, count) {
            return format_int(rank) + " / " + format_int(count)
                + " (" + (rank / count * 100).toFixed(2) + "%)";
        }
        
        let r = o.rankings[m];
        let season = seasons.by_id[r.season_id];
        $('.date', o.tooltip).text(new Date(r.data_time * 1000).toLocaleDateString());
        $('.version', o.tooltip).text(enums_info.version_name_by_ids[r.version]);
        $('.world_rank', o.tooltip).text(format_rank(r.world_rank, r.world_count));
        $('.region_rank', o.tooltip).text(format_rank(r.region_rank, r.region_count));
        $('.league_rank', o.tooltip).text(format_rank(r.league_rank, r.league_count));
        $('.ladder_rank', o.tooltip).text(format_rank(r.ladder_rank, r.ladder_count));
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        $('.mmr', o.tooltip).text(typeof r.mmr === 'undefined' ? 'N/A': r.mmr);
        $('.points', o.tooltip).text(r.points);
        $('.wins', o.tooltip).text(r.wins);
        $('.losses', o.tooltip).text(r.losses);
        $('.race', o.tooltip).empty().append('<img src="'+ static_url + 'img/races/' + enums_info.race_key_by_ids[r.race0] + '-16x16.png"/>');
        $('.league', o.tooltip).empty().append('<img src="'+ static_url + 'img/leagues/' + enums_info.league_key_by_ids[r.league] + '-16x16.png"/>');

        return 218;
    };

    //
    // Major control functions.
    //
    
    // Init everything.
    o.init = _.wrap(o.init, function(wrapped) {

        o.data_control.init();
        o.y_axis_control.init();
        if (o.race_control) o.race_control.init();
        o.y_zoom_control.init();
        o.x_axis_control.init();
        o.background_control.init();

        wrapped();
    });

    //
    // Load resources and add init trigger when complete.
    //

    $.when(deferred_doc_ready(),
           $.ajax({dataType: "json",
                   url: dynamic_url + 'team/' + team_id + '/rankings/',
                   success: function(data) {
                       o.rankings = data;

                       // Add index to each ranking to be able to find it in global list after filtering.
                       o.rankings.forEach((r, i) => r.index = i);

                       // Update race control based on actual data.
                       if (o.race_control) o.race_control.update(o.get_race_options(o.rankings));

                       // Handle empty ranking.
                       if (o.rankings.length === 0) {
                           o.init = function() { o.container.removeClass('wait'); }
                       }
                   }}),
           stats_data.deferred_fetch_mode(mode_id),
           images.deferred_load_leagues(),
           images.deferred_load_races())
        .done(function() { o.init(); });
            
    return o;
};
