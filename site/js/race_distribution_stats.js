//
// Race distribution graph.
//
import {NewGraphBase} from "./graph";
import {create_league_control, create_region_control, create_version_control} from "./stats_graph";
import {settings} from "./settings";
import {Mode, stats_data, TOT} from "./stats";
import {deferred_doc_ready, format_int} from "./utils";
import {seasons} from "./seasons";
import {images} from "./images";

//
// Race distribution table.
//
// TODO JQ PROMISE
export class RaceDistributionTable {
    constructor(mode_id) {
        this.settings = {};
        this.mode_id = mode_id;
        this.container = document.querySelector("#races-table-container");
        this.version_control = create_version_control(this.container, this.controls_change.bind(this));
        this.region_control = create_region_control(this.container, this.controls_change.bind(this));
    
        $.when(
            deferred_doc_ready(),
            stats_data.deferred_fetch_mode(mode_id),
            images.deferred_load_races()
        ).done(() => this.init());
    }
    
    controls_change(name, value) {
        this.settings[name] = value;
        
        const stat = Mode(this.mode_id).get_last();
        
        const filters = {versions: [parseInt(this.settings.v)]};
        
        if (this.settings.r != null && parseInt(this.settings.r) !== TOT) {
            filters.regions = [parseInt(this.settings.r)];
        }
        
        const races_by_league = stat.filter_aggregate(filters, ['league', 'race']);
        
        races_by_league.leagues.forEach(league => {
            const t = races_by_league.count(league);
            races_by_league.races.forEach(race => {
                let c = races_by_league.count(league, race);
                document.querySelector(`#l${league}-r${race} .number`).textContent = format_int(c);
                document.querySelector(`#l${league}-r${race} .percent`).textContent = "(" + (c * 100 / t).toFixed(2) + "%)";
            });
        });
    }
    
    init() {
        this.version_control.init();
        this.region_control.init();
        this.container.classList.remove("wait");
    }
}

// TODO JQ SELECT, JQ PROMISE
export class RaceDistributionGraph extends NewGraphBase {
    
    // Create a race distribution graph for mode_id.
    constructor(mode_id) {
        super("#races-graph-container");
        this.mode_id = mode_id;
    
        this.data = [];   // Filtered and aggregated data for the graph.
    
        this.lines = {};  // Lines between races by race key (bronze to gm).
    
        this.max_value = 1;
    
        this.version_control = create_version_control(this.container, this.controls_change.bind(this));
        this.region_control = create_region_control(this.container, this.controls_change.bind(this));
        this.league_control = create_league_control(this.container, this.controls_change.bind(this));
    
        $.when(
            deferred_doc_ready(),
            stats_data.deferred_fetch_mode(mode_id)
        ).done(this.init.bind(this));
        
    }
    
    // Update units based on resize or new settings.
    // TODO Too integrated, make a better interface to base class.
    update_units() {
        this.y_ax.top_value = this.max_value;
        this.y_ax.bottom_value = 0;
        this.y_per_unit = this.height / (this.y_ax.bottom_value - this.y_ax.top_value);
        
        this.x_ax.left_value = this.data[0].data_time;
        this.x_ax.right_value = this.data[this.data.length - 1].data_time;
        this.x_per_unit = this.width / (this.x_ax.right_value - this.x_ax.left_value);
    }
    
    // Update points based on new data or resize.
    update_points() {
        
        this.update_units();
        
        this.lines = {};
        const new_points = [];
        
        for (let i = 0; i < this.data.length; ++i) {
            let x = this.epoch_to_pixels(this.data[i].data_time);
            settings.enums_info.race_ranking_ids.forEach(race_id => {
                let y = this.y_per_unit * (this.data[i].aggregate.count(race_id) / this.data[i].aggregate.count() * 100 - this.max_value);
                this.lines[race_id] = this.lines[race_id] || [];
                this.lines[race_id].push({x: x, y: y, m: i});
            });
        }
        
        settings.enums_info.race_ranking_ids.forEach(race_id => {
            $.merge(new_points, this.lines[race_id]);
        });
        
        // Update points.
        
        // TODO Just set points in base class like this???
        this.points = new_points;
    }
    
    //
    // Graph callbacks.
    //
    
    new_settings() {
        // Get new data.
        const v = parseInt(this.settings.v);
        const r = parseInt(this.settings.r);
        const l = parseInt(this.settings.l);
        
        const filters = {versions: [v]};
        
        if (r !== TOT) {
            filters.regions = [r];
        }
        
        if (l !== TOT) {
            filters.leagues = [l];
        }
        
        if (l === 6 && v === 0) {
            // GM WoL data is totally broken, let's just not show it.
            filters.leagues = [];
        }
        
        this.max_value = 1;
        
        const all = [];
        const stats = Mode(this.mode_id);
        stats.each(stat => {
            const aggregate = stat.filter_aggregate(filters, ['race']);
            const point = {
                season_id: stat.season_id,
                data_time: stat.data_time,
                aggregate: aggregate,
            };
            all.push(point);
            const t = point.aggregate.count();
            if (t) {
                aggregate.races.forEach(race => {
                    this.max_value = Math.max(this.max_value, point.aggregate.count(race) / t * 100);
                });
            }
        }, v);
        this.data = all;
        
        // Update points.
        
        this.update_points();
    }
    
    new_size() {
        this.update_points();
    }
    
    redraw() {
        this.clear();
        
        settings.enums_info.race_ranking_ids.forEach(race => {
            this.gline(settings.race_colors[race], 2, this.lines[race]);
        });
        
        settings.enums_info.race_ranking_ids.forEach(race => {
            this.ctx.drawImage(document.getElementById('race' + race),
                this.lines[race][0].x - 8 + this.edges.left,
                this.lines[race][0].y - 8 + this.edges.top);
        });
        this.y_axis("percent");
        this.time_x_axis("year");
        this.draw_crosshair();
    }
    
    update_tooltip(m) {
        const format_tooltip_data = (c, t) => ({n: format_int(c), p: "(" + (c * 100 / t).toFixed(2) + "%)"});
        
        const d = this.data[m];
        const season = seasons.by_id[d.season_id];
        $('.date', this.tooltip).text(new Date(d.data_time * 1000).toLocaleDateString());
        $('.season', this.tooltip).text(season.id + " (" + season.number + " - " + season.year + ")");
        const t = d.aggregate.count();
        settings.enums_info.race_ranking_ids.forEach(race => {
            const e = format_tooltip_data(d.aggregate.count(race), t);
            $('.r' + race + '-n', this.tooltip).text(e.n);
            $('.r' + race + '-p', this.tooltip).text(e.p);
        });
        $('.pop-n', this.tooltip).text(format_int(t));
        return 210;
    }
    
    //
    // Init functions.
    //
    
    init() {
        this.version_control.init();
        this.region_control.init();
        this.league_control.init();
        super.init();
    }
}
