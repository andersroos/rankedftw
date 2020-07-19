import {settings} from "./settings";

//
// Image bank.
//

class Images {

    constructor(bank_id) {
        this.league_deferred = $.Deferred();
        this.races_deferred = $.Deferred();
        this.bank = $('#' + bank_id);
        if (this.bank.length === 0) {
            this.bank = $("<div id=bank_id style='display: none;'>");
            this.bank.appendTo('body');
        }
    }

    deferred_load_leagues() {
        _.each(settings.enums_info.league_ranking_ids, (league_id) => {
            var league_tag = settings.enums_info.league_key_by_ids[league_id];
            var img = $("<img id='league" + league_id + "' src='" + settings.static_url + "img/leagues/" + league_tag + ".svg' height='16px' width='16px'/>");
            img.one("load", () => {
                if (_.every(_.map(settings.enums_info.league_ranking_ids,
                                  (lid) => $('#league' + lid)[0].complete))) {
                    this.league_deferred.resolve();
                }
            });
            img.appendTo(this.bank);
        });
        return this.league_deffered;
    }

    deferred_load_races() {
        _.each(settings.enums_info.race_ranking_ids, (race_id) => {
            var race_tag = settings.enums_info.race_key_by_ids[race_id];
            var img = $("<img id='race" + race_id + "' src='" + settings.static_url + "img/races/" + race_tag + ".svg' height='16px' width='16px'/>");
            img.one("load", () => {
                if (_.every(_.map(settings.enums_info.race_ranking_ids, (rid) => $('#race' + rid)[0].complete))) {
                    this.races_deferred.resolve();
                }
                this.races_deferred.resolve();
            });
            img.appendTo(this.bank);
        });

        return this.races_deferred;
    }
}

export let images = new Images('sc2-image-bank');
