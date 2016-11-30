
//
// Graph related code.
//

// The ranking graph object.
sc2.graph.RankingGraph = function(container_id, team_id, region_id, league_id, mode_id) {
    
    //
    // Set up html for container canvas and controls.
    //

    var container = $('#' + container_id);
    
    sc2.html.conf_container(container);
    
    var controls = sc2.html.add_controls_div(container);

    sc2.html.add_control(
        controls, 'td', 'Data:', [
            {'value': 'world',
             'heading': 'World',
             'tooltip': 'Show world ranking for team.',
             'src': sc2.static_url + 'img/regions/world-16x16.png'},
            {'value': 'region',
             'heading': 'Region',
             'tooltip': 'Show region ranking for team.',
             'src': sc2.static_url + 'img/regions/' + sc2.enums_info.region_key_by_ids[region_id] + '-16x16.png'},
            {'value': 'league',
             'heading': 'League',
             'tooltip': 'Show league ranking (in region) for team.',
             'src': sc2.static_url + 'img/leagues/' + sc2.enums_info.league_key_by_ids[league_id] + '-16x16.png'},
        ]);

    sc2.html.add_control(
        controls, 'ty', 'Y-Axis:', [
            {'value': 'c',
             'heading': 'Percent',
             'tooltip': 'Percent on y-axis, % of teams ranked above team.'},
            {'value': 'p',
             'heading': 'Points',
             'tooltip': 'Points on y-axis, 0 at the bottom. Note that this graph does not change for different types of data since the points are always the same.'},
            {'value': 'r',
             'heading': 'Rank',
             'tooltip': 'Absolute rank on y-axis, no 1 at the top. The grey area (or league distribution area) indicates all ranked teams from the top to the bottom at that point in time.'},
        ]);

    sc2.html.add_control(
        controls, 'tyz', 'Y-Zoom:', [
            {'value': '0',
             'heading': 'Off',
             'tooltip': 'No zoom, show full scale to see teams position relative to everyone.'},
            {'value': '1',
             'heading': 'On',
             'tooltip': 'This will cause the graph to zoom in to make the graph line fill the y-space.'},
        ]);

    sc2.html.add_control(
        controls, 'tx', 'X-Axis:', [
            {'value': 'a',
             'heading': 'All',
             'tooltip': 'Show all data.'},
            {'value': 's',
             'heading': 'Season',
             'tooltip': 'Show current/last available season for this player.'},
            {'value': '60',
             'heading': '60-Days',
             'tooltip': 'Show last 60 days.'},
        ]);

    sc2.html.add_control(
        controls, 'tl', 'Leagues:', [
            {'value': '0',
             'heading': 'Off',
             'tooltip': 'League distribution background off.'},
            {'value': '1',
             'heading': 'On',
             'tooltip': 'League distribution background on, there will be no league background for "league" graph or if "points" is selected since that would not make any sense.'},
        ]);

    sc2.html.add_canvas(container);

    sc2.html.add_tooltip(container, [
        ['Date:',   'date'],
        ['Version', 'version'],
        ['World:',  'world_rank'],
        ['Region:', 'region_rank'],
        ['League:', 'league_rank'],
        ['Ladder:', 'ladder_rank'],
        ['Season:', 'season'],
        ['Points:', 'points'],
        ['Wins:',   'wins'],
        ['Losses:', 'losses'],
    ]);

    //
    // Init graph base.
    //
    
    var o = sc2.graph.GraphBase('#' + container_id);

    //
    // Calculated units by settings and size.
    //

    var start_ranking_index;
    var end_ranking_index;
    
    var start_season_index;
    var end_season_index;
    
    var max_rank_all; // One value per settings.data.
    var min_rank_all; // One value per settings.data.
    var max_rank; // One value per settings.data.
    var min_rank; // One value per settings.data.
    var max_percent; // One value per settings.data.
    var min_percent; // One value per settings.data.
    var min_points;
    var max_points;
    
    //
    // Data for the graph.
    //

    o.points = [];          // Points {x, y, m} calcualted from rankings (m is the index in rankings).
    var leagues = [];       // List of point plus league data in a map.
    var floor = [];         // Points {x, y} used when there is an absolute floor.
    var league_areas = {};  // Map from leagues to lists of league area points, league areas should be drawn in
                            // backwards order since they overlap (from gm to bronze)

    //
    // Functions.
    //
    
    // Updating on units needs to be done after a resize or after settings changed.
    o.update_units = function() {
        
        end_ranking_index = o.rankings.length - 1;
        o.x_ax.right_value = o.rankings[end_ranking_index].data_time;
        
        if (o.settings.tx == 'a') {
            start_ranking_index = 0;
        }
        else if (o.settings.tx == 's') {
            var season_id = o.rankings[end_ranking_index].season_id;
            for (var i = end_ranking_index; i >= 0; --i) {
                if (season_id == o.rankings[i].season_id) {
                    start_ranking_index = i;
                }
            }
        }
        else if (o.settings.tx == '60') {
            for (var i = end_ranking_index; i >= 0; --i) {
                if (o.x_ax.right_value - o.rankings[i].data_time < 3600 * 24 * 60) {
                    start_ranking_index = i;
                }
            }
        }
        o.x_ax.left_value = o.rankings[start_ranking_index].data_time;
        
        start_season_index = -1;
        end_season_index = -1;
        for (var i = 0; i < sc2.seasons.sorted.length; ++i) {
            if (sc2.seasons.sorted[i].start <= o.x_ax.left_value && o.x_ax.left_value <= sc2.seasons.sorted[i].end) {
                start_season_index = i;
            }
            if (sc2.seasons.sorted[i].start <= o.x_ax.right_value && o.x_ax.right_value <= sc2.seasons.sorted[i].end) {
                end_season_index = i;
            }
        }
        
        max_rank_all = {world: 0, region: 0, league: 0};
        min_rank_all = {world: 1, region: 1, league: 1};
        max_rank = {world: 0, region: 0, league: 0};
        min_rank = {world: 1e9, region: 1e9, league: 1e9};
        max_percent = {world: 0, region: 0, league: 0};
        min_percent = {world: 1e9, region: 1e9, league: 1e9};
        min_points = 1e9;
        max_points = 0;
        
        for (var i = start_ranking_index; i <= end_ranking_index; ++i) {
            $.each(['world', 'region', 'league'], function(j, key) {
                var count = o.rankings[i][key + "_count"];
                var rank =  o.rankings[i][key + "_rank"];

                max_rank_all[key] = Math.max(max_rank_all[key], count);
                
                min_rank[key] = Math.min(min_rank[key], rank);
                max_rank[key] = Math.max(max_rank[key], rank + 0.1);
                
                min_percent[key] = Math.max(Math.min(min_percent[key], 100 * rank / count - 0.001), 0);
                max_percent[key] = Math.min(Math.max(max_percent[key], 100 * rank / count + 0.001), 100);
            });
            min_points = Math.min(min_points, o.rankings[i].points);
            max_points = Math.max(max_points, o.rankings[i].points + 0.1);
        }
        
        o.x_per_unit = o.width / (o.x_ax.right_value - o.x_ax.left_value + 0.01);

        if (o.settings.tyz == "1") {
            if (o.settings.ty == "c") {
                o.y_ax.top_value = min_percent[o.settings.td];
                o.y_ax.bottom_value = Math.min(100, max_percent[o.settings.td] * 1.02);
            }
            else if (o.settings.ty == "p") {
                o.y_ax.top_value = max_points;
                o.y_ax.bottom_value = Math.max(0, min_points - o.y_ax.top_value * 0.02);                
            }
            else if (o.settings.ty == "r") {
                o.y_ax.top_value = min_rank[o.settings.td];
                o.y_ax.bottom_value = max_rank[o.settings.td] * 1.02;
            }
        }
        else {
            if (o.settings.ty == "c") {
                o.y_ax.top_value = 0;
                o.y_ax.bottom_value = 100;
            }
            else if (o.settings.ty == "p") {
                o.y_ax.top_value = max_points;
                o.y_ax.bottom_value = 0;
            }
            else if (o.settings.ty == "r") {
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
        wrapped({'c': 'percent', 'r': 'int', 'p': 'int'}[o.settings.ty]);
    });

    // Print the x axis.
    o.time_x_axis = _.wrap(o.time_x_axis, function(wrapped) {
        wrapped({"s": "season", "a": "year", "60": "month"}[o.settings.tx]);
    });

    // Get y value for ranking based on settings.
    o.ranking_y_value = function(ranking) {
        if (o.settings.ty == 'c') {
            return o.y_value(ranking[o.settings.td + "_rank"], ranking[o.settings.td + "_count"]);
        }
        else if (o.settings.ty == 'r') {
            return o.y_value(ranking[o.settings.td + "_rank"]);
        }
        else if (o.settings.ty == 'p') {
            return o.y_value(ranking.points);
        }
    };

    // Calculate y-value based on settings and ranking value and count.
    o.y_value = function(value, count) {
        if (o.settings.ty == 'c') {
            return (100 * value / count - o.y_ax.top_value) * o.y_per_unit;
        }
        else if (o.settings.ty == 'r') {
            return (value - o.y_ax.top_value) * o.y_per_unit;
        }
        else if (o.settings.ty == 'p') {
            return (value - o.y_ax.top_value) * o.y_per_unit;
        }
    };    
    
    //
    // Callbacks to implement for graphs.
    //

    o.new_settings = function() {

        o.update_units();

        // Calculate if floor or leagues background should be drawn.

        if (o.settings.tl == '1' && o.settings.td != 'league' && o.settings.ty != 'p') {
            o.settings.bg = 'leagues';
        }
        else if (o.settings.ty == 'r') {
            o.settings.bg = 'floor';
        }
        else {
            o.settings.bg = undefined;
        }

        // Set up filter for leagues background (version is different for each point).

        var filters;
        if (o.settings.bg == 'leagues') {
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

        var league = -1;
        for (var i = start_ranking_index; i <= end_ranking_index; ++i) {
            var ranking = o.rankings[i];
            var x = o.epoch_to_pixels(ranking.data_time);
            var y = o.ranking_y_value(ranking);
            var count = ranking[o.settings.td + "_count"];
            o.points.push({x: x, y: y, m: i});
            
            if (o.settings.bg) {
                floor.push({x: x, y: o.y_value(count, count)});
            }
            if (o.settings.bg == 'leagues') {
                var stat = sc2.stats.Mode(mode_id).get(ranking.id);
                filters.versions = [ranking.version];
                var agg = stat.filter_aggregate(filters, ['league']);
                var ly = 0;
                sc2.utils.rev_each(sc2.enums_info.league_ranking_ids, function(league_id) {
                    league_areas[league_id] = league_areas[league_id] || [];
                    league_areas[league_id].push({x: x, y: o.y_value(ly, count)});
                    ly += agg.count(league_id);
                });
            }
            
            if (league != ranking.league) {
                league = ranking.league;
                leagues.push({x: o.edges.left + x, y: o.edges.top + y, league: league});
            }
        }

        // Make the areas areas.
        if (o.settings.bg == 'floor') {
            $.merge(floor, [{x: o.width, y: 0}, {x: 0, y: 0}]);
        }
        else if (o.settings.bg == 'leagues') {
            floor.reverse();
                sc2.utils.rev_each(sc2.enums_info.league_ranking_ids, function(league_id) {
                    $.merge(league_areas[league_id], floor);
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
            if (o.settings.bg == 'floor') {
                o.garea("#242424", floor);
            }
            if (o.settings.bg == 'leagues') {
                o.setup_league_styles();
                sc2.utils.rev_each(sc2.enums_info.league_ranking_ids, function(league_id, i) {
                    o.garea(o.league_styles[i], league_areas[league_id]);
                });
                o.garea('#000000', floor);
                o.clear(0.3);
            }
            var c_width = o.canvas.width();
            var c_height = o.canvas.height();
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

        // Leagues.
        
        for (var i = 0; i < leagues.length; ++i) {
            o.ctx.drawImage(document.getElementById('league' + leagues[i].league), leagues[i].x - 8, leagues[i].y - 8);
        }
    };

    o.update_tooltip = function(m) {
        function format_rank(rank, count) {
            return sc2.utils.format_int(rank) + " / " + sc2.utils.format_int(count)
                + " (" + (rank / count * 100).toFixed(2) + "%)";
        };
        
        var r = o.rankings[m];
        var season = sc2.seasons.by_id[r.season_id];
        $('.date', o.tooltip).text(new Date(r.data_time * 1000).toLocaleDateString());
        $('.version', o.tooltip).text(sc2.enums_info.version_name_by_ids[r.version]);
        $('.world_rank', o.tooltip).text(format_rank(r.world_rank, r.world_count));
        $('.region_rank', o.tooltip).text(format_rank(r.region_rank, r.region_count));
        $('.league_rank', o.tooltip).text(format_rank(r.league_rank, r.league_count));
        $('.ladder_rank', o.tooltip).text(format_rank(r.ladder_rank, r.ladder_count));
        $('.season', o.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        $('.points', o.tooltip).text(r.points + " (season " + season.id + ")");
        $('.wins', o.tooltip).text(r.wins +  " (season " + season.id + ")");
        $('.losses', o.tooltip).text(r.losses + " (season " + season.id + ")");

        return 218;
    };

    //
    // Major control functions.
    //
    
    // Init everything.
    o.init = _.wrap(o.init, function(wrapped) {

        sc2.controls.Radio(o.container.find("ul[ctrl-name='td']"), 'region', o.controls_change);
        sc2.controls.Radio(o.container.find("ul[ctrl-name='ty']"), 'c', o.controls_change);
        sc2.controls.Radio(o.container.find("ul[ctrl-name='tyz']"), '0', o.controls_change);
        sc2.controls.Radio(o.container.find("ul[ctrl-name='tx']"), 'a', o.controls_change);
        sc2.controls.Radio(o.container.find("ul[ctrl-name='tl']"), '1', o.controls_change);
        
        wrapped();
    });

    //
    // Load resources and add init trigger when complete.
    //

    $.when(sc2.utils.doc_ready(),
           $.ajax({dataType: "json",
                   url: sc2.dynamic_url + 'team/' + team_id + '/rankings/',
                   success: function(data) {
                       o.rankings = data;
                       if (o.rankings.length == 0) {
                           o.init = function() { o.container.removeClass('wait'); }
                       }
                   }}),
           sc2.seasons.load(),
           sc2.stats.load_all_for_mode(mode_id),
           sc2.images.load_leagues())
        .done(function() { o.init(); });
            
    return o;
};
