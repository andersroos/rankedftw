import {GraphBase} from "./graph";
import {settings} from "./settings";
import {seasons} from "./seasons";
import {images} from "./images";
import {Radio} from "./controls";
import {doc_ready, rev_each, format_int, fetch_json} from "./utils";
import {stats_data, Mode} from "./stats";

//
// The ranking graph object.
//
export class RankingGraph extends GraphBase {
    constructor(container_selector, team_id, region_id, league_id, mode_id) {
        super(container_selector);
        this.team_id = team_id;
        this.region_id = region_id;
        this.league_id = league_id;
        this.mode_id = mode_id;
        
        //
        // Add controls.
        //
        
        this.controls = this.container.querySelector(".controls .content");
        
        // Return race options depending on what is available in rankings.
        this.get_race_options = rankings => {
            let options = [{value: 'best', heading: 'Best', tooltip: 'Show ranking for best race in each data point.'}];
            let races_present = rankings.map(r => r.race0);
            options.push(...settings.enums_info.race_ranking_ids.filter(rid => rid >= 0 && races_present.includes(rid)).map(rid => ({
                value: rid,
                src: settings.static_url + 'img/races/' + settings.enums_info.race_key_by_ids[rid] + '.svg',
                tooltip:'Show only ' + settings.enums_info.race_name_by_ids[rid] + ' data points.',
            })));
            return options;
        };
        
        this.data_control = new Radio(this.controls, 'td', 'Data:', [
            {
                value: 'world',
                heading: 'World',
                srcset: [settings.static_url + 'img/regions/world-16x16.png 1x', settings.static_url + 'img/regions/world.svg 2x',].join(", "),
                tooltip: 'Show world ranking for team.'
            },
            {
                value: 'region',
                heading: 'Region',
                srcset: [
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[region_id] + '-16x16.png 1x',
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[region_id] + '.svg 2x'
                ].join(", "),
                tooltip: 'Show region ranking for team.'
            },
            {value: 'league', heading: 'League', src: settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[league_id] + '-128x128.png', tooltip: 'Show league ranking (in region) for team.'},
        ], 'world', this.controls_change.bind(this));
        
        this.y_axis_control = new Radio(this.controls, 'ty', 'Y-Axis:', [
            {value: 'c', heading: 'Percent', tooltip: 'Percent on y-axis, % of teams ranked above team.'},
            {value: 'm', heading: 'MMR', tooltip: 'MMR on y-axis, 0 at the bottom. Note that this graph does not change for different types of data since the points are always the same. This will hide all parts of the graph where mmr was not avaiable.'},
            {value: 'r', heading: 'Rank', tooltip: 'Absolute rank on y-axis, no 1 at the top. The grey area (or league distribution area) indicates all ranked teams from the top to the bottom at that point in time.'},
        ], 'c', this.controls_change.bind(this));
        
        if (settings.enums_info.mode_key_by_ids[this.mode_id] === '1v1') {
            this.race_control = new Radio(this.controls, 'ra', 'Race:', this.get_race_options([]), 'best', this.controls_change.bind(this));
        }

        this.y_zoom_control = new Radio(this.controls, 'tyz', 'Y-Zoom:', [
            {value: '0', heading: 'Off', tooltip: 'No zoom, show full scale to see teams position relative to everyone.'},
            {value: '1', heading: 'On', tooltip: 'This will cause the graph to zoom in to make the graph line fill the y-space.'},
        ], 0, this.controls_change.bind(this));

        this.x_axis_control = new Radio(this.controls, 'tx', 'X-Axis:', [
            {value: 'a', heading: 'All', tooltip: 'Show all data.'},
            {value: 's', heading: 'Season', tooltip: 'Show current/last available season for this player.'},
            {value: '60', heading: '60-Days', tooltip: 'Show last 60 days.'},
        ], 'a', this.controls_change.bind(this));

        this.background_control = new Radio(this.controls, 'tl', 'Leagues:', [
            {value: '0', heading: 'Off', tooltip: 'League distribution background off.'},
            {value: '1', heading: 'On', tooltip: 'League distribution background on, there will be no league background for "league" graph.'},
        ], 1, this.controls_change.bind(this));
    
        //
        // Calculated units by settings and size.
        //
        
        this.start_ranking_index = null; // Start ranking for time selection, index among f_rankings.
        this.end_ranking_index = null; // End ranking for time selection, index among f_rankings.
        
        this.f_rankings = null; // Rankings filtered on race setting.
        
        this.max_rank_all = null; // One value per settings.data.
        
        this.max_rank = null; // One value per settings.data.
        this.min_rank = null; // One value per settings.data.
        
        this.max_percent = null; // One value per settings.data.
        this.min_percent = null; // One value per settings.data.

        this.min_mmr = null; // Min among points.
        this.max_mmr = null; // Max among points.
    
        //
        // Data for the graph.
        //
        
        this.points = [];         // Points {x, y, m} calculated from rankings (m is the index in this.rankings).
        this.leagues = [];        // List of {x, y, league} for when league changes.
        this.floor = [];          // Points {x, y} used when there is an absolute floor.
        this.league_areas = {};   // Map from leagues to lists of league area points, league areas should be drawn in
                                  // backwards order since they overlap (from gm to bronze)
    
        //
        // Load resources and add init trigger when complete.
        //
    
        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
            fetch_json(`${settings.dynamic_url}team/${team_id}/rankings/`).then(data => {
                this.rankings = data;
    
                // Add index to each ranking to be able to find it in global list after filtering.
                this.rankings.forEach((r, i) => r.index = i);
    
                // Update race control based on actual data.
                if (this.race_control) this.race_control.update(this.get_race_options(this.rankings));
                
                return null;
            }),
            images.fetch_leagues(),
            images.fetch_races()
        ]).then(() => this.init());
    }
    
    // Updating of units needs to be done after a resize or after settings changed.
    update_units() {
        
        let start = 0;
        this.end_ranking_index = this.f_rankings.length - 1;
        this.x_ax.right_value = this.f_rankings[this.end_ranking_index].data_time;

        if (this.settings.ty === 'm') {
            for (let i = this.end_ranking_index; i >= 0; --i) {
                if  (typeof this.f_rankings[i].mmr !== 'undefined') {
                    start = i;
                }
            }
        }

        if (this.settings.tx === 'a') {
            this.start_ranking_index = start;
        }
        else if (this.settings.tx === 's') {
            let season_id = this.f_rankings[this.end_ranking_index].season_id;
            for (let i = this.end_ranking_index; i >= start; --i) {
                if (season_id === this.f_rankings[i].season_id) {
                    this.start_ranking_index = i;
                }
            }
        }
        else if (this.settings.tx === '60') {
            for (let i = this.end_ranking_index; i >= start; --i) {
                if (this.x_ax.right_value - this.f_rankings[i].data_time < 3600 * 24 * 60) {
                    this.start_ranking_index = i;
                }
            }
        }
        this.x_ax.left_value = this.f_rankings[this.start_ranking_index].data_time;
        
        this.max_rank_all = {world: 0, region: 0, league: 0};
        this.max_rank = {world: 0, region: 0, league: 0};
        this.min_rank = {world: 1e9, region: 1e9, league: 1e9};
        this.max_percent = {world: 0, region: 0, league: 0};
        this.min_percent = {world: 1e9, region: 1e9, league: 1e9};
        this.min_mmr = 1e9;
        this.max_mmr = 0;
        
        for (let ranking_id = this.start_ranking_index; ranking_id <= this.end_ranking_index; ++ranking_id) {
            ['world', 'region', 'league'].forEach(key => {
                let count = this.f_rankings[ranking_id][key + "_count"];
                let rank =  this.f_rankings[ranking_id][key + "_rank"];

                this.max_rank_all[key] = Math.max(this.max_rank_all[key], count);
                
                this.min_rank[key] = Math.min(this.min_rank[key], rank);
                this.max_rank[key] = Math.max(this.max_rank[key], rank + 0.1);
                
                this.min_percent[key] = Math.max(Math.min(this.min_percent[key], 100 * rank / count - 0.001), 0);
                this.max_percent[key] = Math.min(Math.max(this.max_percent[key], 100 * rank / count + 0.001), 100);
            });
            this.min_mmr = Math.min(this.min_mmr, this.f_rankings[ranking_id].mmr);
            this.max_mmr = Math.max(this.max_mmr, this.f_rankings[ranking_id].mmr);
        }
        
        this.x_per_unit = this.width / (this.x_ax.right_value - this.x_ax.left_value + 0.01);

        if (this.settings.tyz === "1") {
            if (this.settings.ty === "c") {
                this.y_ax.top_value = this.min_percent[this.settings.td];
                this.y_ax.bottom_value = Math.min(100, this.max_percent[this.settings.td] * 1.02);
            }
            else if (this.settings.ty === "m") {
                this.y_ax.top_value = this.max_mmr;
                this.y_ax.bottom_value = Math.max(0, this.in_mmr - this.y_ax.top_value * 0.02);
            }
            else if (this.settings.ty === "r") {
                this.y_ax.top_value = this.min_rank[this.settings.td];
                this.y_ax.bottom_value = this.max_rank[this.settings.td] * 1.02;
            }
        }
        else {
            if (this.settings.ty === "c") {
                this.y_ax.top_value = 0;
                this.y_ax.bottom_value = 100;
            }
            else if (this.settings.ty === "m") {
                this.y_ax.top_value = this.max_mmr;
                this.y_ax.bottom_value = 0;
            }
            else if (this.settings.ty === "r") {
                this.y_ax.top_value = 1;
                this.y_ax.bottom_value = this.max_rank_all[this.settings.td];
            }
        }
        this.y_per_unit = this.height / (this.y_ax.bottom_value - this.y_ax.top_value);
    }

    //
    // Drawing methods.
    //
        
    // Print the y axis.
    y_axis() {
        super.y_axis({'c': 'percent', 'r': 'int', 'm': 'int'}[this.settings.ty]);
    }

    // Print the x axis.
    time_x_axis() {
        super.time_x_axis({"s": "season", "a": "year", "60": "month"}[this.settings.tx]);
    }

    // Get y value for ranking based on settings.
    ranking_y_value(ranking) {
        if (this.settings.ty === 'c') {
            return this.y_value(ranking[this.settings.td + "_rank"], ranking[this.settings.td + "_count"]);
        }
        else if (this.settings.ty === 'r') {
            return this.y_value(ranking[this.settings.td + "_rank"]);
        }
        else if (this.settings.ty === 'm') {
            return this.y_value(ranking.mmr);
        }
        return null;
    }

    // Calculate y-value based on settings and ranking value and count.
    y_value(value, count) {
        if (this.settings.ty === 'c') {
            return (100 * value / count - this.y_ax.top_value) * this.y_per_unit;
        }
        else if (this.settings.ty === 'r') {
            return (value - this.y_ax.top_value) * this.y_per_unit;
        }
        else if (this.settings.ty === 'm') {
            return (value - this.y_ax.top_value) * this.y_per_unit;
        }
        return null;
    }
    
    //
    // Callbacks to implement for graphs.
    //

    new_settings() {

        // Start by filtering rankings on race settings, then.
        if (typeof this.settings.ra === 'undefined' || this.settings.ra === 'best') {
            this.f_rankings = this.rankings.filter(r => r.best_race);
        }
        else {
            let race = parseInt(this.settings.ra);
            this.f_rankings = this.rankings.filter(r => r.race0 === race);
        }

        this.update_units();

        // Calculate if floor or leagues background should be drawn.

        if (this.settings.tl === '1' && this.settings.td !== 'league' && this.settings.ty !== 'm') {
            this.settings.bg = 'leagues';
        }
        else if (this.settings.ty === 'r') {
            this.settings.bg = 'floor';
        }
        else {
            this.settings.bg = null;
        }

        // Set up filter for leagues background (version is different for each point).

        let filters;
        if (this.settings.bg === 'leagues') {
            filters = {};
            if (this.settings.td !== 'world') {
                filters.regions = [this.region_id];
            }
        }
        
        // Calculate new points and background.

        this.points = [];
        this.floor = [];
        this.leagues = [];
        this.league_areas = {};

        let league = -64;
        for (let i = this.start_ranking_index; i <= this.end_ranking_index; ++i) {
            let ranking = this.f_rankings[i];
            let x = this.epoch_to_pixels(ranking.data_time);
            let y = this.ranking_y_value(ranking);
            let count = ranking[this.settings.td + "_count"];
            this.points.push({x: x, y: y, m: ranking.index});
            
            if (this.settings.bg) {
                this.floor.push({x: x, y: this.y_value(count, count)});
            }
            if (this.settings.bg === 'leagues') {
                const stat = new Mode(this.mode_id).get(ranking.id);
                filters.versions = [ranking.version];
                const league_aggreate = stat.filter_aggregate(filters, ['league']);
                let ly = 0;
                rev_each(settings.enums_info.league_ranking_ids, lid => {
                    this.league_areas[lid] = this.league_areas[lid] || [];
                    this.league_areas[lid].push({x: x, y: this.y_value(ly, count)});
                    ly += league_aggreate.count(lid);
                });
            }
            
            if (league !== ranking.league) {
                league = ranking.league;
                this.leagues.push({x: this.edges.left + x, y: this.edges.top + y, league: league});
            }
        }

        // Make the areas areas.
        if (this.settings.bg === 'floor') {
            this.floor.push({x: this.width, y: 0}, {x: 0, y: 0});
        }
        else if (this.settings.bg === 'leagues') {
            this.floor.reverse();
                rev_each(settings.enums_info.league_ranking_ids, lid => {
                    this.league_areas[lid].push(...this.floor);
            });
            this.floor.push({x: 0, y: this.height}, {x: this.width, y: this.height});
        }
    }

    new_size() {
        this.new_settings();
    }
        
    redraw() {

        // Basis.
        
        this.clear();

        // Background.

        if (this.settings.bg) {
            if (this.settings.bg === 'floor') {
                this.garea("#242424", this.floor);
            }
            if (this.settings.bg === 'leagues') {
                this.setup_league_styles();
                rev_each(settings.enums_info.league_ranking_ids, (lid, i) =>{
                    this.garea(this.league_styles[i], this.league_areas[lid]);
                });
                this.garea('#000000', this.floor);
                this.clear(0.3);
            }
            let c_width = this.canvas.width;
            let c_height = this.canvas.height;
            this.area('#000000', [{x: 0, y: 0}, {x: c_width, y: 0},
                               {x: c_width, y: this.edges.top}, {x: 0, y: this.edges.top}]);
            this.area('#000000', [{x: 0, y: this.edges.top + this.height}, {x: c_width, y: this.edges.top + this.height},
                               {x: c_width, y: c_height}, {x: 0, y: c_height}]);
        }

        // Axis.
        
        this.y_axis();
        this.time_x_axis();

        // Graph.
        
        this.gline("#ffffaa", 2, this.points);

        // Tooltip crosshair.

        this.draw_crosshair();

        // League icons.
        
        for (let i = 0; i < this.leagues.length; ++i) {
            const elem = document.getElementById('league' + this.leagues[i].league);
            const x_offset = elem.width / 2;
            const y_offset = elem.height / 2;
            this.ctx.drawImage(elem, this.leagues[i].x - x_offset, this.leagues[i].y - y_offset, elem.width, elem.height);
        }
    }

    update_tooltip(m) {
        function format_rank(rank, count) {
            return format_int(rank) + " / " + format_int(count)
                + " (" + (rank / count * 100).toFixed(2) + "%)";
        }
        
        let r = this.rankings[m];
        let season = seasons.by_id[r.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(r.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".version").textContent = settings.enums_info.version_name_by_ids[r.version];
        this.tooltip.querySelector(".world_rank").textContent = format_rank(r.world_rank, r.world_count);
        this.tooltip.querySelector(".region_rank").textContent = format_rank(r.region_rank, r.region_count);
        this.tooltip.querySelector(".league_rank").textContent = format_rank(r.league_rank, r.league_count);
        this.tooltip.querySelector(".ladder_rank").textContent = format_rank(r.ladder_rank, r.ladder_count);
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        this.tooltip.querySelector(".mmr").textContent = typeof r.mmr === 'undefined' ? 'N/A': r.mmr;
        this.tooltip.querySelector(".points").textContent = r.points;
        this.tooltip.querySelector(".wins").textContent = r.wins;
        this.tooltip.querySelector(".losses").textContent = r.losses;
        this.tooltip.querySelector(".race").innerHTML = '<img src="'+ settings.static_url + 'img/races/' + settings.enums_info.race_key_by_ids[r.race0] + '.svg" height="16px" width="16px"/>';
        this.tooltip.querySelector(".league").innerHTML = '<img style="margin-bottom: -3px" src="'+ settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[r.league] + '-128x128.png" height="16px" width="16px"/><span style="margin-bottom: 2px; padding-left: 3px;"> ' + (r.tier + 1) + '</span>';
        return 218;
    }

    //
    // Major control functions.
    //
    
    // Init everything.
    init() {
        // Handle empty ranking.
        if (this.rankings.length === 0) {
            this.container.classList.remove('wait');
            return;
        }
        this.data_control.init();
        this.y_axis_control.init();
        if (this.race_control) this.race_control.init();
        this.y_zoom_control.init();
        this.x_axis_control.init();
        this.background_control.init();
        super.init();
    }
}
