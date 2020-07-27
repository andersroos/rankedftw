
import {create_region_control, create_version_control, create_x_axis_control} from "./stats_graph";
import {doc_ready, format_int} from "./utils";
import {Mode, stats_data, TOT} from "./stats";
import {GraphBase} from "./graph";
import {seasons} from "./seasons";
import {Radio} from "./controls";

//
// Population table.
//
export class PopulationTable {
    constructor(mode_id) {
        this.mode_id = mode_id;
        this.container = document.querySelector("#pop-table-container");
        this.settings = {v: null};
        this.version_control = create_version_control(this.container, this.controls_change.bind(this));
    
        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
        ]).then(() => this.init());
    }
    
    controls_change(name, value) {
        this.settings[name] = value;
    
        const stat = new Mode(this.mode_id).get_last();
    
        const filters = {versions: [parseInt(this.settings.v)]};
    
        const region_aggregate = stat.filter_aggregate(filters, ['region']);
    
        region_aggregate.regions.forEach(region => {
            document.querySelector(`#r${region} .number`).textContent = format_int(region_aggregate.count(region));
        });
        document.querySelector("#r-2 .number").textContent = format_int(region_aggregate.count());
    }
    
    init() {
        this.version_control.init();
        this.container.classList.remove("wait");
    }
}

//
// Population graph.
//
export class PopulationGraph extends GraphBase {
    constructor(mode_id) {
        super("#pop-graph-container");
    
        this.mode_id = mode_id;
        this.version_control = create_version_control(this.container, this.controls_change.bind(this));
        this.region_control = create_region_control(this.container, this.controls_change.bind(this));
        // TODO Why is helper not used here?
        this.y_axis_control = new Radio(this.container.querySelector(".controls .content"), 'sy', 'Y-Axis:', [
            {value: 'c', heading: 'Teams', tooltip: 'Number of ranked teams in the season.'},
            {value: 'g', heading: 'Games/Day', tooltip: 'Average number of played games per day.'},
        ], 'c', this.controls_change.bind(this));
        this.x_axis_control = create_x_axis_control(this.container, this.controls_change.bind(this));
    
        this.data = [];     // Filtered and aggregated data.
        
        this.max_y = 0.001;     // Max y value.

        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
        ]).then(() => this.init());
    }
    
    // Update units based on resize or new settings.
    update_units() {
        this.y_ax.top_value = this.max_y;
        this.y_ax.bottom_value = 0;
        this.y_per_unit = this.height / (this.y_ax.bottom_value - this.y_ax.top_value);
        
        this.x_ax.left_value = this.data[0].data_time;
        this.x_ax.right_value = this.data[this.data.length - 1].data_time;
        this.x_per_unit = this.width / (this.x_ax.right_value - this.x_ax.left_value);
    }
        
    // Update points based on new data or resize.
    update_points() {
        
        this.update_units();
            
        const new_points = [];
            
        for (let i = 0; i < this.data.length; ++i) {
            new_points.push({
                x: this.epoch_to_pixels(this.data[i].data_time),
                y: this.height + this.y_per_unit * this.data[i].y_value,
                m: i
            });
        }
            
        this.points = new_points;
    }
        
    //
    // Graph callbacks.
    //
    
    new_settings() {

        // Get new data.
            
        const version = parseInt(this.settings.v);
        const filters = {versions: [version]};
            
        if (parseInt(this.settings.r) !== TOT) {
            filters.regions = [parseInt(this.settings.r)];
        }
            
        this.data = [];
        
        this.max_y = 0.001;
        let last_season = -1;
        const stats = new Mode(this.mode_id);
        stats.each_reverse(stat => {
            const aggregate = stat.filter_aggregate(filters, []);
            const season = seasons.by_id[stat.season_id];
            const point = {
                season_id: season.id,
                season_age: (stat.data_time - season.start) / (24 * 3600),
                data_time: stat.data_time,
                count: aggregate.count(),
                games: aggregate.wins() + aggregate.losses(),
            };
            if (this.settings.sx === 'a' || (this.settings.sx === 'sl' && last_season !== point.season_id)) {
                this.data.push(point);
                last_season = point.season_id;
            }
        }, version);
        this.data.reverse();
        const first_season = last_season;
        
        last_season = -1;
        for (let i = 0; i < this.data.length; ++i) {
            let point = this.data[i];
            if (first_season !== last_season) {
                point.d_games = point.games;
                point.d_age = point.season_age;
            }
            else {
                point.d_games = point.games - this.data[i - 1].games;
                point.d_age = point.season_age - this.data[i - 1].season_age;
            }
            point.games_per_day = point.d_games / point.d_age;
                
            if (this.settings.sy === 'c') {
                point.y_value = point.count;
            }
            else if (this.settings.sy === 'g') {
                point.y_value = point.games_per_day;
            }
                
            this.max_y = Math.max(this.max_y, point.y_value);
        }
        
        // Update points.
        
        this.update_points();
    }
        
    new_size() {
        this.update_points();
    }
        
    redraw() {
        this.clear();
        this.setup_league_styles();
        this.gline("#ffffaa", 2, this.points);
        this.y_axis("int");
        this.time_x_axis("year");
        this.draw_crosshair();
    }
    
    update_tooltip(m) {
        const d = this.data[m];
        const season = seasons.by_id[d.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(d.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        this.tooltip.querySelector(".season-age").textContent = Math.round(d.season_age) + " days";
        this.tooltip.querySelector(".pop-n").textContent = format_int(d.count);
        this.tooltip.querySelector(".gpd").textContent = format_int(Math.round(d.games_per_day));
        this.tooltip.querySelector(".games").textContent = format_int(Math.round(d.games));
            
        return 188;
    }
        
    //
    // Init functions.
    //
    
    init() {
        this.version_control.init();
        this.region_control.init();
        this.y_axis_control.init();
        this.x_axis_control.init();
        super.init();
    }
}

