import {format_int, rev_each} from "./utils";
import {Mode, stats_data, TOT} from "./stats";
import {GraphBase, GraphUnits} from "./graph";
import {settings} from "./settings";
import {seasons} from "./seasons";
import {create_region_control, create_version_control, create_x_axis_control, SX_ALL, SX_SEASON_LAST} from "./controls";
import {TableBase} from "./table";


export class LeagueDistributionTable extends TableBase {
    constructor(mode_id) {
        super("#leagues-table-container");
        this.mode_id = mode_id;
        create_version_control(this);
        stats_data.fetch_mode(mode_id).then(() => this.init());
    }
    
    update() {
        const stats = new Mode(this.mode_id).get_last();
        
        const filters = {versions: [parseInt(this.settings.v)]};
        
        const region_league_aggreage = stats.filter_aggregate(filters, ['regions', 'leagues']);
        const league_aggregate = stats.filter_aggregate(filters, ['leagues']);
        
        region_league_aggreage.regions.forEach(region => {
            const t = region_league_aggreage.count(region);
            document.querySelector(`#r${region}-pop .number`).textContent = format_int(t);
            region_league_aggreage.leagues.forEach(league => {
                const c = region_league_aggreage.count(region, league);
                document.querySelector(`#r${region}-l${league} .number`).textContent = format_int(c);
                document.querySelector(`#r${region}-l${league} .percent`).textContent = "(" + (c * 100 / t).toFixed(2) + "%)";
            });
        });
        
        const t = league_aggregate.count();
        document.querySelector("#r-2-pop .number").textContent = format_int(t);
        league_aggregate.leagues.forEach(league => {
            const c = league_aggregate.count(league);
            document.querySelector(`#r-2-l${league} .number`).textContent = format_int(c);
            document.querySelector(`#r-2-l${league} .percent`).textContent = "(" + (c * 100 / t).toFixed(2) + "%)";
        });
    }
}


export class LeagueDistributionGraph extends GraphBase {
    constructor(mode_id) {
        super("#leagues-graph-container");

        create_version_control(this);
        create_region_control(this);
        create_x_axis_control(this);
    
        stats_data.fetch_mode(mode_id).then(() => {
            this.mode_stats = new Mode(mode_id);
            this.init();
        });
    }
    
    draw_graph() {

        // Create stat filter based on settings.
        
        const version = parseInt(this.settings.v);
        const region = parseInt(this.settings.r);
        
        const filters = {versions: [version]};
    
        if (region !== TOT) {
            filters.regions = [region];
        }
    
        // Gather stats data.
        
        const stat_points = [];
        let last_season = -1;

        this.mode_stats.each_reverse(stat => {
            const point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: stat.filter_aggregate(filters, ['leagues']),
            };
            if (this.settings.sx === SX_ALL || (this.settings.sx === SX_SEASON_LAST && last_season !== point.season_id)) {
                stat_points.push(point);
                last_season = point.season_id;
            }
        }, version);
        stat_points.reverse();
    
        // Create graph units.

        const units = new GraphUnits({
            width: this.width,
            height: this.height,
            x_start_value: stat_points[0].data_time,
            x_end_value: stat_points[stat_points.length - 1].data_time,
            y_top_value: 0,
            y_bottom_value: 100,
        });
        
        // Calculate line for each league id (bronze to gm).
    
        const lines = {};
        let max_x = 0;
        stat_points.forEach(stat_point => {
            let percentage_offset = 0;
            const count = stat_point.aggregate.count();
            if (count) {
                rev_each(settings.enums_info.league_ranking_ids, league_id => {
                    lines[league_id] = lines[league_id] || [];
                    const percentage = percentage_offset + stat_point.aggregate.count(league_id) / count * 100;
                    const x = units.x_value_to_pixel(stat_point.data_time);
                    const y = units.y_value_to_pixel(percentage);
                    lines[league_id].push({x, y, m: stat_point});
                    percentage_offset = percentage;
                    max_x = Math.max(x, max_x);
                });
            }
        });
        
        // Draw league lines as areas on top of each other.
        
        settings.enums_info.league_ranking_ids.forEach(league_id => {
            this.league_garea(league_id, [{x: max_x, y: 0}, {x: 0, y: 0}].concat(lines[league_id]));
        });
        
        // Draw axis and crosshair.
        
        this.y_axis(units, "percent");
        this.x_axis(units, "year");
        this.draw_crosshair();
    
        // Build points for mouse over.
    
        let points = [];
        settings.enums_info.league_ranking_ids.forEach(league_id => {
            points.push(...lines[league_id]);
        });
        
        return points;
    }
        
    update_tooltip(stat_point) {
        const format_tooltip_data = (c, t) => ({n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"});
        
        const season = seasons.by_id[stat_point.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(stat_point.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        const t = stat_point.aggregate.count();
        stat_point.aggregate.leagues.forEach(league => {
            const e = format_tooltip_data(stat_point.aggregate.count(league), t);
            this.tooltip.querySelector(`.l${league}-n`).textContent = e.n;
            this.tooltip.querySelector(`.l${league}-p`).textContent = e.p;
        });
        this.tooltip.querySelector(`.pop-n`).textContent = format_int(t);
        
        return 210;
    }
}
