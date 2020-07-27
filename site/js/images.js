import {settings} from "./settings";

//
// Image bank.
//

// TODO JQ PROMISE
class Images {

    constructor() {
        this.league_deferred = $.Deferred();
        this.races_deferred = $.Deferred();
        this.bank = document.getElementById("sc2-image-bank");
    }

    deferred_load_leagues() {
        settings.enums_info.league_ranking_ids.forEach(league_id => {
            const league_tag = settings.enums_info.league_key_by_ids[league_id];
            const id = `league${league_id}`;
            this.bank.insertAdjacentHTML("beforeend", `<img id="${id}" src="${settings.static_url}img/leagues/${league_tag}-16x16.png"/>`);
            const checkComplete = () => {
                if (settings.enums_info.league_ranking_ids.every(lid => (document.getElementById(`league${lid}`) || {}).complete)) {
                    this.league_deferred.resolve();
                }
            };
            this.bank.lastElementChild.onload = checkComplete;
            checkComplete();
        });
        return this.league_deffered;
    }

    deferred_load_races() {
        settings.enums_info.race_ranking_ids.forEach(race_id => {
            const race_tag = settings.enums_info.race_key_by_ids[race_id];
    
            const id = `race${race_id}`;
            this.bank.insertAdjacentHTML("beforeend", `<img id="${id}" src="${settings.static_url}img/races/${race_tag}-16x16.png"/>`);
            const checkComplete = () => {
                if (settings.enums_info.race_ranking_ids.every(rid => (document.getElementById(`race${rid}`) || {}).complete)) {
                    this.races_deferred.resolve();
                }
            };
            this.bank.lastElementChild.onload = checkComplete;
            checkComplete();
        });

        return this.races_deferred;
    }
}

export let images = new Images();
