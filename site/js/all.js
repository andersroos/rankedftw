
import {settings} from './settings.js';
import {seasons} from './seasons.js';
import * as team from './team.js';
import * as stats from './stats_graph.js';
import {NewRaceDistributionGraph} from "./race_distribution_stats";

window.sc2 = {
    settings,
    seasons,
    team,
    stats,
    RaceDistributionGraph: NewRaceDistributionGraph,
};
