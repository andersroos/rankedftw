
import {format_int} from "./utils";
import {Mode, stats_data, TOT} from "./stats";
import {GraphBase, GraphUnits} from "./graph";
import {seasons} from "./seasons";
import {create_region_control, create_version_control, create_x_axis_control, create_y_axis_control, SX_ALL, SX_SEASON_LAST, SY_GAMES_PER_DAY, SY_TEAMS} from "./controls";
import {TableBase} from "./table";


export class PopulationTable extends TableBase {
    
    constructor(mode_id) {
        super("#pop-table-container");
        this.mode_id = mode_id;
        this.settings = {v: null};
        
        create_version_control(this);
    
        stats_data.fetch_mode(mode_id).then(() => this.init());
    }
    
    update() {
        const stat = new Mode(this.mode_id).get_last();
    
        const filters = {versions: [parseInt(this.settings.v)]};
    
        const region_aggregate = stat.filter_aggregate(filters, ['regions']);
    
        region_aggregate.regions.forEach(region => {
            document.querySelector(`#r${region} .number`).textContent = format_int(region_aggregate.count(region));
        });
        document.querySelector("#r-2 .number").textContent = format_int(region_aggregate.count());
    }
}

export class PopulationGraph extends GraphBase {
    constructor(mode_id) {
        super("#pop-graph-container");
    
        create_version_control(this);
        create_region_control(this);
        create_y_axis_control(this);
        create_x_axis_control(this);
    
        stats_data.fetch_mode(mode_id).then(() => {
            this.mode_stats = new Mode(mode_id);
            this.init();
        });
    }
    
    // Update points based on new data or resize.
    update_points() {
        
        this.update_units();
            
    }
        
    draw_graph() {
    
        // Stats filter based on settings.
    
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
            const aggregate = stat.filter_aggregate(filters, []);
            const season = seasons.by_id[stat.season_id];
            const point = {
                season_id: season.id,
                season_age: (stat.data_time - season.start) / (24 * 3600),
                data_time: stat.data_time,
                count: aggregate.count(),
                games: aggregate.wins() + aggregate.losses(),
            };
            if (this.settings.sx === SX_ALL || (this.settings.sx === SX_SEASON_LAST && last_season !== point.season_id)) {
                stat_points.push(point);
                last_season = point.season_id;
            }
        }, version);
        stat_points.reverse();
    
        let max_y_value = 0.001;

        stat_points.forEach(stat_point => {
            // This code is wrong, see: https://github.com/andersroos/rankedftw/issues/12
            stat_point.delta_games = stat_point.games
            stat_point.delta_age = stat_point.season_age
            
            stat_point.games_per_day = stat_point.delta_games / stat_point.delta_age;
    
            if (this.settings.sy === SY_TEAMS) {
                stat_point.y_value = stat_point.count;
            }
            else if (this.settings.sy === SY_GAMES_PER_DAY) {
                stat_point.y_value = stat_point.games_per_day;
            }
            
            max_y_value = Math.max(max_y_value, stat_point.y_value);
        });
    
        // Create graph units.
    
        const units = new GraphUnits({
            width: this.width,
            height: this.height,
            x_start_value: stat_points[0].data_time,
            x_end_value: stat_points[stat_points.length - 1].data_time,
            y_top_value: max_y_value,
            y_bottom_value: 0,
        });

        // Draw population stats line.
        
        const points = stat_points.map(stat_point => ({
            x: units.x_value_to_pixel(stat_point.data_time),
            y: units.y_value_to_pixel(stat_point.y_value),
            m: stat_point,
        }));
        this.gline("#ffffaa", 2, points);
    
        // Draw axis and crosshair.
        
        this.y_axis(units, "int");
        this.x_axis(units, "year");
        this.draw_crosshair();
    
        // Return points to use for mouse over.
        
        return points;
    }
    
    update_tooltip(stat_point) {
        const season = seasons.by_id[stat_point.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(stat_point.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        this.tooltip.querySelector(".season-age").textContent = Math.round(stat_point.season_age) + " days";
        this.tooltip.querySelector(".pop-n").textContent = format_int(stat_point.count);
        this.tooltip.querySelector(".gpd").textContent = format_int(Math.round(stat_point.games_per_day));
        this.tooltip.querySelector(".games").textContent = format_int(Math.round(stat_point.games));
            
        return 188;
    }
}

