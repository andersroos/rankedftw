import {doc_ready, format_int} from "./utils";
import {Mode, stats_data, TOT} from "./stats";
import {GraphBase, GraphUnits} from "./graph";
import {settings} from "./settings";
import {seasons} from "./seasons";
import {create_region_control, create_version_control, create_x_axis_control} from "./controls";
import {TableBase} from "./table";


//
// League distribution table.
//
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
}

//
// League distribution graph.
//
export class LeagueDistributionGraph extends GraphBase {
    constructor(mode_id) {
        super("#leagues-graph-container");

        this.mode_id = mode_id;
        create_version_control(this);
        create_region_control(this);
        create_x_axis_control(this);
    
        this.data = [];   // Filtered and aggregated data.
    
        Promise.all([
            doc_ready(),
            stats_data.fetch_mode(mode_id),
        ]).then(() => this.init());
    }
    
    // Calculate new graph data based on settings.
    calculate_data() {
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
        return all;
    }
    
    // Update points based on new data or resize.
    calculate_points(units) {
        const points = [];
        const lines = {};  // Lines between races by race key (bronze to gm).
    
        let line = [];
        let last_line;
        
        // Baseline.
        
        for (let i = 0; i < this.data.length; ++i) {
            line.push({x: units.x_value_to_pixel(this.data[i].data_time), y: units.y_value_to_pixel(100)});
        }
        
        // Add up for each league.
        
        settings.enums_info.league_ranking_ids.forEach(league => {
            last_line = line;
            line = [];
            for (let i = 0; i < this.data.length; ++i) {
                // Push the line and use data index as mouse over key.
                line.push({
                    x: last_line[i].x,
                    y: last_line[i].y + units.y_per_unit * this.data[i].aggregate.count(league) / this.data[i].aggregate.count() * 100,
                    m: i
                });
            }
            points.push(...line);
            lines[league] = line;
        });
        
        return {points, lines};
    }
    
    draw_graph() {
        this.data = this.calculate_data();
    
        const units = new GraphUnits({
            width: this.width,
            height: this.height,
            x_start_value: this.data[0].data_time,
            x_end_value: this.data[this.data.length - 1].data_time,
            y_top_value: 0,
            y_bottom_value: 100,
        });
        
        const {points, lines} = this.calculate_points(units);
        
        for (let li = settings.enums_info.league_ranking_ids.length - 1; li >= 0; --li) {
            this.league_garea(li, [{x: this.width, y: this.height}, {x: 0, y: this.height}].concat(lines[settings.enums_info.league_ranking_ids[li]]));
        }
        this.y_axis(units, "percent");
        this.x_axis(units, "year");
        
        return points;
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
}
