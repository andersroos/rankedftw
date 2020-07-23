import {to_jq_element} from "./utils";
import {Radio} from "./controls";
import {settings} from "./settings";


export const create_version_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    return new Radio(graph_jq.find(".controls").find(".content"), 'v', 'Version:',
        settings.enums_info.version_ranking_ids
                  .map(vid => ({value: vid, heading: settings.enums_info.version_name_by_ids[vid]}))
                  .reverse(),
        settings.default_version, cb);
};


export const create_region_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    let regions = [settings.ALL].concat(settings.enums_info.region_ranking_ids);
    return new Radio(graph_jq.find(".controls").find(".content"), 'r', 'Regions:',
        regions
            .map(rid => ({
                value: rid,
                heading: settings.enums_info.region_name_by_ids[rid],
                src: settings.static_url + 'img/regions/' + settings.enums_info.region_key_by_ids[rid] + '-16x16.png'
            })),
        settings.ALL, cb)
};


export const create_league_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    let leagues = [settings.ALL].concat(settings.enums_info.league_ranking_ids.reverse());
    return new Radio(graph_jq.find(".controls").find(".content"), 'l', 'League:',
        leagues
            .map(lid => ({
                value: lid,
                heading: lid === settings.ALL ? settings.enums_info.league_name_by_ids[lid] : null,
                src: lid === settings.ALL ? null : settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[lid] + '-16x16.png',
                tooltip: settings.enums_info.league_name_by_ids[lid],
            })),
        settings.ALL, cb);
};


export const create_x_axis_control = (graph, cb) => {
    const graph_jq = to_jq_element(graph);
    return new Radio(graph_jq.find(".controls").find(".content"), 'sx', 'X-Axis:', [
            {value: 'a', heading: 'All', tooltip: 'Show all data'},
            {value: 'sl', heading: 'Season Last', tooltip: 'Show only one point in graph for each season.'},
    ], 'a', cb)
};
