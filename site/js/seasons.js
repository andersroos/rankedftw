//
// Information about seasons in singleton, either deferred load or populated in page.
//
class Seasons {

    init(seasons) {
        this.sorted = seasons;
        this.by_id = {};
        for (let i = 0; i < seasons.length; ++i) {
            this.by_id[seasons[i].id] = seasons[i];
        }
    }
}
export let seasons = new Seasons();
