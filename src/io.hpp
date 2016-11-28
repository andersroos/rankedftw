#pragma once

#include "types.hpp"


std::string to_string(const team_rank_t& tr);

std::string to_string(const player_t& p);

std::string to_string(const team_t& p);


void read_tr(std::istream& is, uint16_t tr_version, team_rank_t& tr);

std::ostream& operator<<(std::ostream& os, const team_rank_t& tr);


std::ostream& operator<<(std::ostream& os, const team_ranks_header& tr);

std::istream& operator>>(std::istream& is, team_ranks_header& tr);


std::ostream& operator<<(std::ostream& os, const ranking_stats_t& ranking_stats);

std::istream& operator>>(std::istream& is, ranking_stats_t& ranking_stats);
