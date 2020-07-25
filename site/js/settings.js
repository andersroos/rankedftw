//
// Global settings and constants. Most are set in page.
//

const settings = {
    enums_info: {
        league_ranking_ids: [],  // Ids for the leagues from bronze to gm.
        race_ranking_ids: [],    // Ids for the races from unknown to random.
        stat: {},                // Information about where data is located in the raw stat format for each version of the format.
    },
    default_version: 2,          // LotV
    static_url: 'https://www.rankedftw.com/static/latest/',
    dynamic_url: 'https://www.rankedftw.com/',
    UNKWNON: -1,
    ALL: -2,
    race_colors: {
        [-1]: "#666666", // Unknown
        [0]:  "#704898", // Zerg
        [1]:  "#fff080", // Protoss
        [2]:  "#c94118", // Terran
        [3]:  "#a0ebff", // Random
    },
};

export {settings};
