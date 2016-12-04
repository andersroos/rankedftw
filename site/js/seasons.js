import {dynamic_url} from "./settings";


//
// Information about seasons in singleton, either deferred load or populated in page.
//
class Seasons {

    constructor() {
        this.deferred = $.Deferred();
    }

    deferred_init(seasons) {
        this.sorted = seasons;
        this.by_id = {};
        for (var i = 0; i < seasons.length; ++i) {
            this.by_id[seasons[i].id] = seasons[i];
        }
        this.deferred.resolve();
    }

    deferred_load() {
        if (typeof this.sorted == 'undefined') {
            $.ajax({
                       dataType: "json",
                       url: dynamic_url + 'team/seasons/',
                       success: function(data) {
                           this.deferred_init(data);
                       }
                   });
        }
        return this.deferred;
    };

}
export let seasons = new Seasons();
