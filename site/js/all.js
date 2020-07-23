
import {settings} from './settings.js';
import {seasons} from './seasons.js';
import * as team from './team.js';
import * as stats from './stats_graph.js';
import {RaceDistributionGraph, RaceDistributionTable} from "./race_distribution_stats";
import {LeagueDistributionGraph, LeagueDistributionTable} from "./league_distribution_stats";
import {PopulationGraph, PopulationTable} from "./population_stats";

window.sc2 = {
    settings,
    seasons,
    team,
    stats,
    RaceDistributionTable,
    RaceDistributionGraph,
    LeagueDistributionTable,
    LeagueDistributionGraph,
    PopulationTable,
    PopulationGraph,
};
