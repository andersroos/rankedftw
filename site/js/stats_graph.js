import {Radio} from "./controls";
import {settings} from "./settings";


export const create_version_control = (graph, cb) => {
    return new Radio(graph.querySelector(".controls .content"), 'v', 'Version:',
        settings.enums_info.version_ranking_ids
                  .map(vid => ({value: vid, heading: settings.enums_info.version_name_by_ids[vid]}))
                  .reverse(),
        settings.default_version, cb);
};


export const create_region_control = (graph, cb) => {
    let regions = [settings.ALL].concat(settings.enums_info.region_ranking_ids);
    return new Radio(graph.querySelector(".controls .content"), 'r', 'Regions:',
        regions
            .map(rid => ({
                value: rid,
                heading: settings.enums_info.region_name_by_ids[rid],
                srcset: [
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[rid] + '-16x16.png 1x',
                    settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[rid] + '.svg 2x',
                ].join(", "),
            })),
        settings.ALL, cb)
};


export const create_league_control = (graph, cb) => {
    let leagues = [settings.ALL].concat(settings.enums_info.league_ranking_ids.reverse());
    return new Radio(graph.querySelector(".controls .content"), 'l', 'League:',
        leagues
            .map(lid => ({
                value: lid,
                heading: lid === settings.ALL ? settings.enums_info.league_name_by_ids[lid] : null,
                src: lid === settings.ALL ? null : settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[lid] + '-128x128.png',
                tooltip: settings.enums_info.league_name_by_ids[lid],
            })),
        settings.ALL, cb);
};


export const create_x_axis_control = (graph, cb) => {
    return new Radio(graph.querySelector(".controls .content"), 'sx', 'X-Axis:', [
            {value: 'a', heading: 'All', tooltip: 'Show all data'},
            {value: 'sl', heading: 'Season Last', tooltip: 'Show only one point in graph for each season.'},
    ], 'a', cb)
};
