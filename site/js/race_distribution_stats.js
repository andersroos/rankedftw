//
// Race distribution graph.
//
import {GraphBase, GraphUnits} from "./graph";
import {settings} from "./settings";
import {Mode, stats_data, TOT} from "./stats";
import {format_int} from "./utils";
import {seasons} from "./seasons";
import {images} from "./images";
import {create_league_control, create_region_control, create_version_control} from "./controls";
import {TableBase} from "./table";


export class RaceDistributionTable extends TableBase {
    
    constructor(mode_id) {
        super("#races-table-container");
        this.mode_id = mode_id;
        create_version_control(this);
        create_region_control(this);
    
        stats_data.fetch_mode(mode_id).then(() => this.init());
    }
    
    update() {
        const stat = new Mode(this.mode_id).get_last();
        
        const filters = {versions: [parseInt(this.settings.v)]};
        
        if (this.settings.r != null && parseInt(this.settings.r) !== TOT) {
            filters.regions = [parseInt(this.settings.r)];
        }
        
        const league_race_aggregate = stat.filter_aggregate(filters, ['leagues', 'races']);
        
        league_race_aggregate.leagues.forEach(league => {
            const t = league_race_aggregate.count(league);
            league_race_aggregate.races.forEach(race => {
                let c = league_race_aggregate.count(league, race);
                document.querySelector(`#l${league}-r${race} .number`).textContent = format_int(c);
                document.querySelector(`#l${league}-r${race} .percent`).textContent = "(" + (c * 100 / t).toFixed(2) + "%)";
            });
        });
    }
}


export class RaceDistributionGraph extends GraphBase {
    
    // Create a race distribution graph for mode_id.
    constructor(mode_id) {
        super("#races-graph-container");
    
        create_version_control(this);
        create_region_control(this);
        create_league_control(this);
    
        Promise.all([
            stats_data.fetch_mode(mode_id),
            images.fetch_races()
        ]).then(() => {
            this.mode_stats = new Mode(mode_id);
            this.init();
        });
    }
    
    draw_graph() {
        
        // Stats filter based on settings.
    
        const version = parseInt(this.settings.v);
        const region = parseInt(this.settings.r);
        const league = parseInt(this.settings.l);
    
        const filters = {versions: [version]};
    
        if (region !== TOT) {
            filters.regions = [region];
        }
    
        if (league !== TOT) {
            filters.leagues = [league];
        }
    
        if (league === 6 && version === 0) {
            // GM WoL data is totally broken, let's just not show it.
            filters.leagues = [];
        }
        
        // Gather stats data and max_percentage.
    
        const stat_points = [];
        let max_percentage = 0;

        this.mode_stats.each(stat => {
            const race_aggregate = stat.filter_aggregate(filters, ['races']);
            const point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: race_aggregate,
            };
            stat_points.push(point);
            const total_count = point.aggregate.count();
            if (total_count) {
                race_aggregate.races.forEach(race => {
                    max_percentage = Math.max(max_percentage, point.aggregate.count(race) / total_count * 100);
                });
            }
        }, version);

        // Create graph units.
        
        const units = new GraphUnits({
            width: this.width,
            height: this.height,
            x_start_value: stat_points[0].data_time,
            x_end_value: stat_points[stat_points.length - 1].data_time,
            y_top_value: max_percentage,
            y_bottom_value: 0,
        });

        // Calculate line for each race id.
        
        const lines = {};
        stat_points.forEach(stat_point => {
            const x = units.x_value_to_pixel(stat_point.data_time);
            settings.enums_info.race_ranking_ids.forEach(race_id => {
                const y = units.y_value_to_pixel(stat_point.aggregate.count(race_id) / stat_point.aggregate.count() * 100);
                lines[race_id] = lines[race_id] || [];
                lines[race_id].push({x, y, m: stat_point});
            });
        });
    
        // Draw graph.
    
        settings.enums_info.race_ranking_ids.forEach(race_id => {
            // Line.
            this.gline(settings.race_colors[race_id], 2, lines[race_id]);

            // Race icon.
            const elem = document.getElementById('race' + race_id);
            const x_offset = elem.width / 2;
            const y_offset = elem.height / 2;
            this.ctx.drawImage(elem, lines[race_id][0].x - x_offset + this.edges.left, lines[race_id][0].y - y_offset + this.edges.top, elem.width, elem.height);
        });
        
        // Draw axis and crosshair.
        
        this.y_axis(units, "percent");
        this.x_axis(units, "year");
        this.draw_crosshair();
    
        // Build points for mouse over.
        
        const points = [];
        settings.enums_info.race_ranking_ids.forEach(race_id => {
            points.push(...lines[race_id]);
        });
    
        return points;
    }
    
    update_tooltip(stat_point) {
        const format_tooltip_data = (c, t) => ({n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"});
        
        const season = seasons.by_id[stat_point.season_id];
        this.tooltip.querySelector(".date").textContent = new Date(stat_point.data_time * 1000).toLocaleDateString();
        this.tooltip.querySelector(".season").textContent = season.id + " (" + season.number + " - " + season.year + ")";
        const t = stat_point.aggregate.count();
        settings.enums_info.race_ranking_ids.forEach(race => {
            const e = format_tooltip_data(stat_point.aggregate.count(race), t);
            this.tooltip.querySelector(`.r${race}-n`).textContent = e.n;
            this.tooltip.querySelector(`.r${race}-p`).textContent = e.p;
        });
        this.tooltip.querySelector(`.pop-n`).textContent = format_int(t);
        return 210;
    }
}
