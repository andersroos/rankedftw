import {doc_ready, format_int} from "./utils";
import {Mode, stats_data, TOT} from "./stats";
import {GraphBase} from "./graph";
import {settings} from "./settings";
import {seasons} from "./seasons";
import {create_region_control, create_version_control, create_x_axis_control} from "./controls";


//
// League distribution table.
//
// TODO Very simliar to RaceDistributionTable, maybe reuse something?
export class LeagueDistributionTable {
    constructor(mode_id) {
        this.container = document.querySelector("#leagues-table-container");
        this.mode_id = mode_id;
        this.settings = {};
        this.version_control = create_version_control(this);
    
        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
        ]).then(() => this.init());
    }
    
    on_control_change(name, value) {
        this.settings[name] = value;
        
        const stats = new Mode(this.mode_id).get_last();
        
        const filters = {versions: [parseInt(this.settings.v)]};
        
        const region_league_aggreage = stats.filter_aggregate(filters, ['region', 'league']);
        const league_aggregate = stats.filter_aggregate(filters, ['league']);
        
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

    init() {
        this.version_control.init();
        this.container.classList.remove("wait");
    }
}

//
// League distribution graph.
//
export class LeagueDistributionGraph extends GraphBase {
    constructor(mode_id) {
        super("#leagues-graph-container");

        this.mode_id = mode_id;
        this.version_control = create_version_control(this);
        this.region_control = create_region_control(this);
        this.x_axis_control = create_x_axis_control(this);
    
        this.data = [];   // Filtered and aggregated data.
    
        this.lines = {};  // Lines between races by race key (bronze to gm).
    
        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
        ]).then(() => this.init());
    }
    
    // Update units based on resize or new settings.
    update_units() {
        this.y_ax.top_value = 0;
        this.y_ax.bottom_value = 100;
        this.y_per_unit = this.height / 100;
        
        this.x_ax.left_value = this.data[0].data_time;
        this.x_ax.right_value = this.data[this.data.length - 1].data_time;
        this.x_per_unit = this.width / (this.x_ax.right_value - this.x_ax.left_value);
    }
        
    // Update points based on new data or resize.
    update_points() {
        this.update_units();
        
        const new_points = [];
        
        let line = [];
        let last_line;
        
        // Baseline.
        
        for (let i = 0; i < this.data.length; ++i) {
            line.push({x: this.epoch_to_pixels(this.data[i].data_time), y: this.height});
        }
            
        // Add up for each league.
        
        settings.enums_info.league_ranking_ids.forEach(league => {
            last_line = line;
            line = [];
            for (let i = 0; i < this.data.length; ++i) {
                // Push the line and use data index as mouse over key.
                line.push({x: last_line[i].x,
                    y: last_line[i].y - this.y_per_unit * this.data[i].aggregate.count(league) / this.data[i].aggregate.count() * 100,
                    m: i});
            }
            new_points.push(...line);
            this.lines[league] = line;
        });
        
        // Update points.
        
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
            
        const all = [];
        let last_season = -1;
        const stats = new Mode(this.mode_id);
        stats.each_reverse(stat => {
            const point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: stat.filter_aggregate(filters, ['league']),
            };
            if (this.settings.sx === 'a' || (this.settings.sx === 'sl' && last_season !== point.season_id)) {
                all.push(point);
                last_season = point.season_id;
            }
        }, version);
        all.reverse();
        this.data = all;
        
        // Update points.
            
        this.update_points();
    }
        
    new_size() {
        this.update_points();
    }
        
    redraw() {
        this.clear();
        this.setup_league_styles();
            
        for (let li = settings.enums_info.league_ranking_ids.length - 1; li >= 0; --li) {
            this.garea(this.league_styles[li], [{x: this.width, y: this.height}, {x: 0, y: this.height}].concat(this.lines[settings.enums_info.league_ranking_ids[li]]));
        }
            
        this.y_axis("percent");
        this.time_x_axis("year");
        this.draw_crosshair();
    }
        
    update_tooltip(m) {
        const format_tooltip_data = (c, t) => ({n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"});
        
        const d = this.data[m];
        const season = seasons.by_id[d.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(d.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        const t = d.aggregate.count();
        d.aggregate.leagues.forEach(league => {
            const e = format_tooltip_data(d.aggregate.count(league), t);
            this.tooltip.querySelector(`.l${league}-n`).textContent = e.n;
            this.tooltip.querySelector(`.l${league}-p`).textContent = e.p;
        });
        this.tooltip.querySelector(`.pop-n`).textContent = format_int(t);
        
        return 210;
    }
        
    //
    // Init functions.
    //
    
    init() {
        this.version_control.init();
        this.region_control.init();
        this.x_axis_control.init();
        super.init();
    }
}
