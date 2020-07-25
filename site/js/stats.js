import {settings} from "./settings";

export const TOT = -2;
export const COUNT = 0;
export const WINS = 1;
export const LOSSES = 2;


//
// Singleton for handling fetching of stats data.
//
class StatsData {
    
    constructor() {
        this.deferred = {};
        this.raw_by_mode = {};
    }
    
    // Return deferred for when mode data is available.
    deferred_fetch_mode(mode_id) {
        if (typeof this.deferred[mode_id] === "undefined") {
            // TODO JQ AJAX
            this.deferred[mode_id] = $.ajax({
                dataType: "json",
                url: settings.dynamic_url + 'stats/raw/' + mode_id + '/',
                success: (data) => { this.raw_by_mode[mode_id] = data; }
            });
        }
        return this.deferred[mode_id];
    }

    get_raws(mode_id) {
        return this.raw_by_mode[mode_id];
    }
}
export let stats_data = new StatsData();

//
// Wrapper object for a filtered and aggregated object.
//
// TODO OLD OBJECT
export let Aggregate = function(mode_id, filters, group_by, raw) {
    const object = Object.assign({}, filters);
    
    function create_accessor(type) {
        return function() {
            let data = raw.data;
            for (let i = 0; i < arguments.length; ++i) {
                data = data[arguments[i]];
            }
            if (group_by.length !== arguments.length) {
                data = data[TOT];
            }
            return data[type];
        };
    }

    // Get the count at the id sub path of group_by enums.
    object.count = create_accessor(COUNT);

    // Get the wins at the id sub path of group_by enums.
    object.wins = create_accessor(WINS);

    // Get the losses at the id sub path of group_by enums.
    object.losses = create_accessor(LOSSES);

    return object;
};

//
// Wrapper object for single raw stat to help with filtering and aggregation.
//
export class Stat {
    
    constructor(mode_id, raw) {
        this.mode_id = mode_id;
        this.raw = raw;
        this.stat = settings.enums_info.stat[raw.stat_version];
    }
    
    get season_id() {
        return this.raw.season_id;
    }
    
    get data_time() {
        return this.raw.data_time;
    }
    
    get(version, region, league, race) {
        // Get data at index.

        const index = this.stat.data_size
                      * (  this.stat.version_indices[version] * this.stat.region_count * this.stat.league_count * this.stat.race_count
                           + this.stat.region_indices[region] * this.stat.league_count * this.stat.race_count
                           + this.stat.league_indices[league] * this.stat.race_count
                           + this.stat.race_indices[race]);
        return this.raw.data.slice(index, index + this.stat.data_size);
    }

    filter_sum(filters) {
        // Calculate a sum based on filters, one filter per type (version, region, league, races),
        // each filter maps to a list of type ids. An undefined type list will be regarded as a list with all ids.
        let sum = [0, 0, 0, 0];
    
        filters.versions.forEach(version => {
            filters.regions.forEach(region => {
                filters.leagues.forEach(league => {
                    filters.races.forEach(race => {
                        const data = this.get(version, region, league, race);
                        for (let i = 0; i < this.stat.data_size; ++i) {
                            sum[i] += data[i];
                        }
                    });
                });
            });
        });

        return sum;
    }

    filter_aggregate_internal(filters, group_by) {
        // Calculate a generic filtered map [of maps ..]  of sums. The
        // aggregate will only consist of data points that is in the filter
        // for each dimension (making it possible to aggregate EU + AM but not
        // include SEA). Filters is a map with index lists into the type
        // arrays. The group_by list is the type names of lists that should be
        // included (with sum) in the result. The order of group_by is
        // important. For example group_by = ['regions', 'races'] will return a
        // map of region_ids => map of race_ids => sums. The race_ids map will also
        // include a TOT which is the total in that region. The region_ids map
        // will also include a TOT which is a total of everything.

        if (group_by.length === 0) {
            return this.filter_sum(filters);
        }
    
        // TODO Try to make this core understandable.
        const result = {};
        const group_by__head = group_by[0];
        const group_by__head_s = group_by__head + 's';
        const group_by__rest = group_by.slice(1, group_by.length);
        const tot = [0, 0, 0, 0];
    
        for (let fi in filters[group_by__head_s]) {
            const next_filter = Object.assign({}, filters);
            next_filter[group_by__head_s] = [filters[group_by__head_s][fi]];
            const next_res = this.filter_aggregate_internal(next_filter, group_by__rest);
            result[filters[group_by__head_s][fi]] = next_res;
            let sum;
            if (next_res[TOT]) {
                sum = next_res[TOT];
            }
            else {
                sum = next_res;
            }
            for (let i = 0; i < this.stat.data_size; ++i) {
                tot[i] += sum[i];
            }
        }
        result[TOT] = tot;

        return result;
    }

    // Return an Aggregate object with count, wins and losses aggregated on group_by entities. And filtered by filters.
    filter_aggregate(filters, group_by) {
        filters.versions = filters.versions || this.stat.version_ids;
        filters.regions = filters.regions   || this.stat.region_ids;
        filters.leagues = filters.leagues   || this.stat.league_ids;
        filters.races = filters.races       || this.stat.race_ids;

        // TODO Check usage.
        const {id, data_time, mode_id, season_id, season_version, stat_version} = this.raw;
        const aggregated = {id, data_time, mode_id, season_id, season_version, stat_version};
        aggregated.data = this.filter_aggregate_internal(filters, group_by);
        return Aggregate(this.mode_id, filters, group_by, aggregated);
    }
}


//
// Create a stats object to handle all stats for a mode.
//
export class Mode {

    constructor(mode_id) {
        this.mode_id = mode_id;
        this.raws = stats_data.get_raws(mode_id);
    }
    
    // Get stat by ranking id, return another one close to it if not present.
    get(ranking_id) {
        let raw;
        for (let i = 0; i < this.raws.length; ++i) {
            raw = this.raws[i];  // Will cause a missing raws to get another raw.
            if (raw.id === ranking_id) {
                break;
            }
        }
        return new Stat(this.mode_id, raw);
    }

    // Get last stat.
    get_last() {
        return new Stat(this.mode_id, this.raws[this.raws.length - 1])
    }

    // Iterate over raws in order. Skip raws that are of season version lower than min.
    each(fun, min_version) {
        for (let i = 0; i < this.raws.length; ++i) {
            if (min_version == null || min_version <= this.raws[i].season_version) {
                fun(new Stat(this.mode_id, this.raws[i]), i);
            }
        }
    }

    // Iterate over raws in reverse order. Skip raws that are of season version lower than min.
    each_reverse(fun, min_version) {
        for (let i = this.raws.length - 1; i >= 0; --i) {
            if (min_version == null || min_version <= this.raws[i].season_version) {
                fun(new Stat(this.mode_id, this.raws[i]), i);
            }
        }
    }
}

