import {GraphBase, GraphUnits} from "./graph";
import {settings} from "./settings";
import {seasons} from "./seasons";
import {images} from "./images";
import {Radio} from "./controls";
import {doc_ready, rev_each, format_int, fetch_json} from "./utils";
import {stats_data, Mode} from "./stats";


const TY_MMR = "m";
const TY_PERCENT = "c";
const TY_RANK = "r";

const TX_ALL = "a";
const TX_SEASON = "s";
const TX_60 = "60";

const TYZ_ZOOM_OFF = "0";
const TYZ_ZOOM_ON = "1";

const TD_WORLD = "world";
const TD_REGION = "region";
const TD_LEAGUE = "league";

const TL_LEAGUES_OFF = "0";
const TL_LEAGUES_ON = "1";

const BACKGROUND_LEAGUES = "leagues";
const BACKGROUND_FLOOR = "floor";
const BACKGROUND_NONE = null;


const filter_race = (rankings, selected_race) => {
    if (selected_race == null || selected_race === 'best') {
        return rankings.filter(r => r.best_race);
    }
    const race = parseInt(selected_race);
    return rankings.filter(r => r.race0 === race);
}


const filter_time_selection = (rankings, ty, tx) => {
    
    if (ty === TY_MMR) {
        // Remove rankings without mmr since y axis shows mmr.
        rankings = rankings.filter(r => r.mmr != null);
    }
    
    if (tx === TX_ALL || rankings.length === 0) {
        return rankings;
    }
    
    if (tx === TX_SEASON) {
        const season_id = rankings[rankings.length - 1].season_id;
        return rankings.filter(r => r.season_id === season_id);
    }
    
    if (tx === TX_60) {
        const cutoff = rankings[rankings.length - 1].data_time - 3600 * 24 * 60;
        return rankings.filter(r => r.data_time >= cutoff);
    }
    
    throw new Error(`unknown setttings ty ${ty} tx ${tx}, this is a bug`);
    
};


const calculate_units = (width, height, rankings, ty, tyz, td) => {
    let y_top_value;
    let y_bottom_value;
    
    if (tyz === TYZ_ZOOM_ON) {
        if (ty === TY_PERCENT) {
            y_top_value = Math.max(0, rankings.reduce((acc, ranking) => Math.min(acc, 100 * ranking[td + "_rank"] / ranking[td + "_count"] - 0.001), 1e9));
            y_bottom_value = Math.min(100, rankings.reduce((acc, ranking) => Math.max(acc, 100 * ranking[td + "_rank"] / ranking[td + "_count"] + 0.001), 0));
        }
        else if (ty === TY_MMR) {
            y_top_value = rankings.reduce((acc, ranking) => Math.max(acc, ranking.mmr), 0);
            y_bottom_value = Math.max(0, rankings.reduce((acc, ranking) => Math.min(acc, ranking.mmr), 1e9) - y_top_value * 0.02);
        }
        else if (ty === TY_RANK) {
            y_top_value = rankings.reduce((acc, ranking) => Math.min(acc, ranking[td + "_rank"]), 1e9);
            y_bottom_value = rankings.reduce((acc, ranking) => Math.max(acc, ranking[td + "_rank"]), 0) * 1.02;
        }
    }
    else {
        if (ty === TY_PERCENT) {
            y_top_value = 0;
            y_bottom_value = 100;
        }
        else if (ty === TY_MMR) {
            y_top_value = rankings.reduce((acc, ranking) => Math.max(acc, ranking.mmr), 0);
            y_bottom_value = 0;
        }
        else if (ty === TY_RANK) {
            y_top_value = 1;
            y_bottom_value = rankings.reduce((acc, ranking) => Math.max(acc, ranking[td + "_count"]), 0);
        }
    }
    
    return new GraphUnits({
        width,
        height,
        x_start_value: rankings[0].data_time,
        x_end_value: rankings[rankings.length - 1].data_time,
        y_top_value,
        y_bottom_value,
    });
};


const calculate_background_type = (tl, td, ty) => {
    if (tl === TL_LEAGUES_ON && td !== TD_LEAGUE && ty !== TY_MMR) {
        return BACKGROUND_LEAGUES;
    }
    
    if (ty === TY_RANK) {
        return BACKGROUND_FLOOR;
    }
    
    return BACKGROUND_NONE;
};


// Return a function to get y value from (value, count).
const y_value_fun = (units, ty) => {
    if (ty === TY_PERCENT) {
        return (value, count) => units.y_value_to_pixel(100 * value / count);
    }
    
    if (ty === TY_RANK || ty === TY_MMR) {
        return value => units.y_value_to_pixel(value);
    }
    
    return null;
};


// Return a function to get y value from ranking.
const ranking_y_value_fun = (units, ty, td) => {
    const y_value = y_value_fun(units, ty);
    
    if (ty === TY_PERCENT) {
        return ranking => y_value(ranking[td + "_rank"], ranking[td + "_count"]);
    }
    
    if (ty === TY_RANK) {
        return ranking => y_value(ranking[td + "_rank"]);
    }
    
    if (ty === TY_MMR) {
        return ranking => y_value(ranking.mmr);
    }
    
    return null;
}


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
                value: TD_WORLD,
                heading: 'World',
                srcset: [settings.static_url + 'img/regions/world-16x16.png 1x', settings.static_url + 'img/regions/world.svg 2x',].join(", "),
                tooltip: 'Show world ranking for team.'
            },
            {
                value: TD_REGION,
                heading: 'Region',
                srcset: [
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[region_id] + '-16x16.png 1x',
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[region_id] + '.svg 2x'
                ].join(", "),
                tooltip: 'Show region ranking for team.'
            },
            {value: TD_LEAGUE, heading: 'League', src: settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[league_id] + '-128x128.png', tooltip: 'Show league ranking (in region) for team.'},
        ], 'world', this.on_control_change.bind(this));
        
        this.y_axis_control = new Radio(this.controls, 'ty', 'Y-Axis:', [
            {value: TY_PERCENT, heading: 'Percent', tooltip: 'Percent on y-axis, % of teams ranked above team.'},
            {value: TY_MMR, heading: 'MMR', tooltip: 'MMR on y-axis, 0 at the bottom. Note that this graph does not change for different types of data since the points are always the same. This will hide all parts of the graph where mmr was not avaiable.'},
            {value: TY_RANK, heading: 'Rank', tooltip: 'Absolute rank on y-axis, no 1 at the top. The grey area (or league distribution area) indicates all ranked teams from the top to the bottom at that point in time.'},
        ], 'c', this.on_control_change.bind(this));
        
        if (settings.enums_info.mode_key_by_ids[this.mode_id] === '1v1') {
            this.race_control = new Radio(this.controls, 'ra', 'Race:', this.get_race_options([]), 'best', this.on_control_change.bind(this));
        }

        this.y_zoom_control = new Radio(this.controls, 'tyz', 'Y-Zoom:', [
            {value: TYZ_ZOOM_OFF, heading: 'Off', tooltip: 'No zoom, show full scale to see teams position relative to everyone.'},
            {value: TYZ_ZOOM_ON, heading: 'On', tooltip: 'This will cause the graph to zoom in to make the graph line fill the y-space.'},
        ], 0, this.on_control_change.bind(this));

        this.x_axis_control = new Radio(this.controls, 'tx', 'X-Axis:', [
            {value: TX_ALL, heading: 'All', tooltip: 'Show all data.'},
            {value: TX_SEASON, heading: 'Season', tooltip: 'Show current/last available season for this player.'},
            {value: TX_60, heading: '60-Days', tooltip: 'Show last 60 days.'},
        ], 'a', this.on_control_change.bind(this));

        this.background_control = new Radio(this.controls, 'tl', 'Leagues:', [
            {value: TL_LEAGUES_OFF, heading: 'Off', tooltip: 'League distribution background off.'},
            {value: TL_LEAGUES_ON, heading: 'On', tooltip: 'League distribution background on, there will be no league background for "league" graph.'},
        ], 1, this.on_control_change.bind(this));
    
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
    
    draw_graph() {
        let rankings = this.rankings;

        // Filter rankings based on settings.
        rankings = filter_race(rankings, this.settings.ra);
        rankings = filter_time_selection(rankings, this.settings.ty, this.settings.tx);
        
        // Abort if rankings is empty.
        if (rankings.length === 0) return [];
        
        // Calculate units based on filtered rankings and settings.
        const units = calculate_units(this.width, this.height, rankings, this.settings.ty, this.settings.tyz, this.settings.td);
    
        // Set up functions to use based on settings.
        const y_value = y_value_fun(units, this.settings.ty);
        const ranking_y_value = ranking_y_value_fun(units, this.settings.ty, this.settings.td);
        
        // Points for the graph line, also with ranking for mouse over.
        const points = rankings.map(ranking => ({
            x: units.x_value_to_pixel(ranking.data_time),
            y: ranking_y_value(ranking),
            m: ranking,
            ranking,
        }));
        
        // Calculate and draw background.
    
        const background = calculate_background_type(this.settings.tl, this.settings.td, this.settings.ty);
        if (background) {
            
            // Prepare a floor line to be used as floor area or lower edge for league areas.
            const floor = points.map(({x, ranking}) => {
                const count = ranking[this.settings.td + "_count"];
                return {x, y: y_value(count, count)};
            });
            
            if (background === BACKGROUND_FLOOR) {
                // Make floor into an area, then draw it.
                floor.push({x: this.width, y: 0}, {x: 0, y: 0});
                this.garea("#242424", floor);
            }
            else if (background === BACKGROUND_LEAGUES) {
                const filters = {};
                if (this.settings.td !== TD_WORLD) {
                    // Set up filter for leagues background (version is different for each point so it is applied for each ranking below).
                    filters.regions = [this.region_id];
                }
    
                // Areas by league id for background.
                const league_areas = {};
                points.forEach(({x, ranking}) => {
                    const count = ranking[this.settings.td + "_count"];
                    const stat = new Mode(this.mode_id).get(ranking.id);
                    filters.versions = [ranking.version];
                    const league_aggreate = stat.filter_aggregate(filters, ['leagues']);
                    let ly = 0;
                    rev_each(settings.enums_info.league_ranking_ids, lid => {
                        league_areas[lid] = league_areas[lid] || [];
                        league_areas[lid].push({x: x, y: y_value(ly, count)});
                        ly += league_aggreate.count(lid);
                    });
                });
    
                floor.reverse();
    
                rev_each(settings.enums_info.league_ranking_ids, lid => {
                    league_areas[lid].push(...floor);
                });

                // Complete the floor.
                floor.push({x: 0, y: this.height}, {x: this.width, y: this.height});
                
                rev_each(settings.enums_info.league_ranking_ids, lid =>{
                    this.league_garea(lid, league_areas[lid]);
                });
                this.garea('#000000', floor);
                this.clear(0.3);
            }
            
            // Clear the area outside the graph.
            let c_width = this.canvas.width;
            let c_height = this.canvas.height;
            this.area('#000000', [{x: 0, y: 0}, {x: c_width, y: 0}, {x: c_width, y: this.edges.top}, {x: 0, y: this.edges.top}]);
            this.area('#000000', [{x: 0, y: this.edges.top + this.height}, {x: c_width, y: this.edges.top + this.height}, {x: c_width, y: c_height}, {x: 0, y: c_height}]);
        }
    
        // Draw axis.
    
        this.y_axis(units, {[TY_PERCENT]: 'percent', [TY_RANK]: 'int', [TY_MMR]: 'int'}[this.settings.ty]);
        this.x_axis(units, {[TX_SEASON]: "season", [TX_ALL]: "year", [TX_60]: "month"}[this.settings.tx]);
    
        // Draw graph line.
    
        this.gline("#ffffaa", 2, points);
        
        // Draw the crosshair before icons to prevent overwriting.
        
        this.draw_crosshair();
        
        // Draw league icons when player changes league.
        let league = -64;
        points.forEach(({x, y, ranking}) => {
            if (league !== ranking.league) {
                league = ranking.league;
                const elem = document.getElementById('league' + league);
                const x_offset = elem.width / 2;
                const y_offset = elem.height / 2;
                this.ctx.drawImage(elem, this.edges.left + x - x_offset, this.edges.top + y - y_offset, elem.width, elem.height);
            }
        });

        // Return points for mouse over.
        return points;
    }
    
    update_tooltip(r) {
        function format_rank(rank, count) {
            return format_int(rank) + " / " + format_int(count)
                + " (" + (rank / count * 100).toFixed(2) + "%)";
        }
        
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
}
