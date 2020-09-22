import {get_hash} from "./utils";
import {get_cookie} from "./utils";
import {set_cookie} from "./utils";
import {set_hash} from "./utils";
import {settings} from "./settings";
import {get_league_image_src, get_region_image_srcset} from "./images";

//
// Set persistent value of control (no checking).
//
let set_persistent_value = function(name, value) {
    set_cookie(name, value);
    set_hash(name, value);
};

//
// Get value initial value from persistent storage (will also set
// value to default if not present). The list allowed_values is mostly
// to prevent cookie manipulation all settings with the same name
// should have the same allowed_values.
//
let get_persistent_initial_value = function(name, allowed_values, default_value) {

    let value = get_hash(name);

    if (!value) {
        value = get_cookie(name);
    }

    for (let i = 0; i < allowed_values.length; ++i) {
        if (value === allowed_values[i]) {
            set_persistent_value(name, value, true);
            return value;
        }
    }
    set_persistent_value(name, default_value, true);
    return default_value;
};


//
// Controls registry, singleton for handling page global settings (like version and region).
//
class Registry {

    constructor() {
        this.by_name = {};  // Controls with the same name will be linked.
    }

    //
    // During init of a control, the control should register itself. The control will be called with initial the
    // value.
    //
    register(control) {
        let controls = this.by_name[control.key] = this.by_name[control.key] || [];
        if (!controls.includes(control)) {
            this.by_name[control.key].push(control);
        }
        control.set_value(get_persistent_initial_value(control.key, control.allowed_values, control.default_value))
    }

    //
    // Will be when something is selected in a control (like a click event).
    //
    set_value(key, value) {
        set_persistent_value(key, value);
        this.by_name[key].forEach(control => { control.set_value(value) });
    }
}
let registry = new Registry();


//
// Create a Radio control. It will render itself inside jq_container. Options is a list of
// {value, heading (optional), tooltip, src (optional, for images)}. After creation it will
// add itself to the registry to be linked with other controls of the same key. Option values will be
// converted to strings and on_select will be called with a string.
//
export class Radio {

    // Render and register.
    constructor(container, key, heading, options, default_value, on_select) {
        this.key = key;
        this.heading = heading;
        this.on_select = on_select;

        container.insertAdjacentHTML("beforeend", `<ul class="${key}"/>`);
        this.ul = container.lastElementChild;

        this.update(options, default_value);
    }

    // Update with new options.
    update(options, default_value) {
        this.default_value = typeof default_value === "undefined" ? this.default_value : String(default_value);
        this.allowed_values = options.map(o => String(o.value));

        this.ul.innerHTML = null;
        this.ul.insertAdjacentHTML("beforeend", `<span class="icon-align">${this.heading}</span>`);
        options.forEach(option => {
            let html = `<a data-ctrl-value="${option.value}" title="${option.tooltip || ''}">`;
            if (option.heading) {
                html += `<span class="icon-align ${option.class || ""}">${option.heading}</span>`;
            }
            if (option.src) {
                html += `<img class="${option.class || ""}" src="${option.src}" height="16px" width="16px"/>`;
            }
            else if (option.srcset) {
                html += `<img class="${option.class || ""}" srcset="${option.srcset}" height="16px" width="16px"/>`;
            }
            html += "</a>";
            this.ul.insertAdjacentHTML("beforeend", html);
        });

        // Setup click callback.
        Array.from(this.ul.getElementsByTagName('a')).forEach(e => {
            e.onclick = () => registry.set_value(this.key, e.dataset.ctrlValue);
        });
        registry.register(this);
    }

    // On change callback from registry.
    set_value(new_value) {
        this.value = new_value;

        // Highlight selected.
        Array.from(this.ul.getElementsByTagName('a')).forEach(e => {
            if (e.dataset.ctrlValue === this.value) {
                e.classList.add('selected');
            }
            else {
                e.classList.remove('selected');
            }
        });

        // Callback to change graph etc.
        this.on_select(this.key, this.value)
    }
}


export const create_version_control = graph => {
    return new Radio(graph.container.querySelector(".controls .content"), 'v', 'Version:',
        settings.enums_info.version_ranking_ids
            .map(vid => ({value: vid, heading: settings.enums_info.version_name_by_ids[vid]}))
            .reverse(),
        settings.default_version, graph.on_control_change.bind(graph));
};


export const create_region_control = graph => {
    let regions = [settings.ALL].concat(settings.enums_info.region_ranking_ids);
    return new Radio(graph.container.querySelector(".controls .content"), 'r', 'Regions:',
        regions
            .map(rid => ({
                value: rid,
                class: "region",
                heading: settings.enums_info.region_name_by_ids[rid],
                srcset: get_region_image_srcset(rid),
            })),
        settings.ALL, graph.on_control_change.bind(graph))
};


export const create_league_control = graph => {
    let leagues = [settings.ALL].concat(settings.enums_info.league_ranking_ids.reverse());
    return new Radio(graph.container.querySelector(".controls .content"), 'l', 'League:',
        leagues
            .map(lid => ({
                value: lid,
                class: "league",
                heading: lid === settings.ALL ? settings.enums_info.league_name_by_ids[lid] : null,
                src: lid === settings.ALL ? null : get_league_image_src(lid),
                tooltip: settings.enums_info.league_name_by_ids[lid],
            })),
        settings.ALL, graph.on_control_change.bind(graph));
};


export const SY_TEAMS = "c";
export const SY_GAMES_PER_DAY = "g";
export const create_y_axis_control = graph => {
    return new Radio(graph.container.querySelector(".controls .content"), 'sy', 'Y-Axis:', [
        {value: SY_TEAMS, heading: 'Teams', tooltip: 'Number of ranked teams in the season.'},
        {value: SY_GAMES_PER_DAY, heading: 'Games/Day', tooltip: 'Average number of played games per day.'},
    ], 'c', graph.on_control_change.bind(graph));
};


export const SX_ALL = "a";
export const SX_SEASON_LAST = "sl";
export const create_x_axis_control = graph => {
    return new Radio(graph.container.querySelector(".controls .content"), 'sx', 'X-Axis:', [
        {value: SX_ALL, heading: 'All', tooltip: 'Show all data'},
        {value: SX_SEASON_LAST, heading: 'Season Last', tooltip: 'Show only one point in graph for each season.'},
    ], 'a', graph.on_control_change.bind(graph))
};
