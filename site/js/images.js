import {settings} from "./settings";


export const get_region_image_srcset = region_id => {
    const static_url = settings.static_url;
    const region_key = settings.enums_info.region_key_by_ids[region_id];
    return `${static_url}img/regions/${region_key}-16x16.webp 1.2x, ${static_url}img/regions/${region_key}-128x128.webp 2x`;
};


export const get_world_image_srcset = () => {
    const static_url = settings.static_url;
    return `${static_url}img/regions/world-16x16.webp 1.2x, ${static_url}img/regions/world-128x128.webp 2x`;
};


export const get_league_image_src = league_id => {
    return settings.static_url + 'img/leagues/' + settings.enums_info.league_key_by_ids[league_id] + '-128x128.webp';
}


export const get_race_image_src = race_id => {
    return settings.static_url + 'img/races/' + settings.enums_info.race_key_by_ids[race_id] + '.svg';
}


//
// Image bank.
//

class Images {
    
    constructor() {
        this.bank = document.getElementById("sc2-image-bank");
    }
    
    // Load league images and return a promise resolved when done.
    fetch_leagues() {
        return new Promise(resolve => {
            settings.enums_info.league_ranking_ids.forEach(league_id => {
                const league_image_src = get_league_image_src(league_id);
                const id = `league${league_id}`;
                this.bank.insertAdjacentHTML("beforeend", `<img id="${id}" src="${league_image_src}" height="16px" width="16px"/>`);
                const checkComplete = () => {
                    if (settings.enums_info.league_ranking_ids.every(lid => (document.getElementById(`league${lid}`) || {}).complete)) {
                        resolve();
                    }
                };
                this.bank.lastElementChild.onload = checkComplete;
                checkComplete();
            });
        });
    }
    
    // Load race images and return a promise resolved when done.
    fetch_races() {
        return new Promise(resolve => {
            settings.enums_info.race_ranking_ids.forEach(race_id => {
                const race_image_src = get_race_image_src(race_id);
                
                const id = `race${race_id}`;
                this.bank.insertAdjacentHTML("beforeend", `<img id="${id}" src="${race_image_src}" height="16px" width="16px"/>`);
                const checkComplete = () => {
                    if (settings.enums_info.race_ranking_ids.every(rid => (document.getElementById(`race${rid}`) || {}).complete)) {
                        resolve();
                    }
                };
                this.bank.lastElementChild.onload = checkComplete;
                checkComplete();
            });
        });
    }
}

export const images = new Images();


