#pragma once

#include <stdint.h>
#include <set>
#include <map>
#include <vector>
#include <iostream>
#include <algorithm>

#include <boost/shared_ptr.hpp>

//
// Basic types.
//

typedef uint32_t id_t;
typedef int8_t enum_t;
typedef uint32_t bid_t;

#define TEAM_1V1 11
#define LOTV 2
#define GRANDMASTER 6
#define KR 2
#define NO_MMR -32768
#define MMR_SEASON 28
#define SEPARATE_RACE_MMR_SEASON 29

#define RACE_ANY  8
#define RACE_BEST 9

//
// Team rank data.
//

// Size of team_rank in db or on disk.
#define TEAM_RANKS_HEADER_SIZE ( 3 * sizeof(uint32_t) )
#define TEAM_RANK_V1_SIZE ( 3 * sizeof(id_t) + 2 * sizeof(float) + 1 * sizeof(double)\
                            + 9 * sizeof(enum_t) + 10 * sizeof(uint32_t) )
#define TEAM_RANK_V2_SIZE ( 3 * sizeof(id_t) + 2 * sizeof(float) + 1 * sizeof(double)\
                            + sizeof(int16_t) + 9 * sizeof(enum_t) + 10 * sizeof(uint32_t) )
#define TEAM_RANK_MAGIC_NUMBER 0xD00D6A3E

// First version
#define TEAM_RANK_VERSION_0 0

// Added tier and removed active ranking.
#define TEAM_RANK_VERSION_1 1

// Fast mmr implementation.
#define TEAM_RANK_VERSION_2 2

// Header for team ranks data in db and file.
struct team_ranks_header {
   team_ranks_header()
      : magic_number(TEAM_RANK_MAGIC_NUMBER), version(TEAM_RANK_VERSION_2), count(0) {}
   
   team_ranks_header(uint32_t _count)
      : magic_number(TEAM_RANK_MAGIC_NUMBER), version(TEAM_RANK_VERSION_2), count(_count) {}

   uint32_t magic_number;  // Magic number, should be TEAM_RANK_MAGIC_NUMBER or byte order is wrong.
   uint32_t version;       // Version of data, 2 is current version.
   uint32_t count;         // Number of entries in db or file.
};

// Representation of one ranking in time of one team.
struct team_rank_v0_t {

   team_rank_v0_t() {}
   
   id_t team_id;

   // The timestamp of the ladder data for presenting data points on site. Ideally this
   // should be the last time the ladder was updated. This data can not be retrieved
   // easily at all times. For already closed ladders it will be the season end date
   // (season <= 14 don't have sufficient meta data). For current season ladders it will
   // be the cache update time.
   double data_time;
   
   enum_t version;
   enum_t region;
   enum_t mode;
   enum_t league;
   
   id_t ladder_id;
   float join_time;
   id_t source_id;  // Cache id where this ranking origins.

   float points;
   uint32_t wins;
   uint32_t losses;

   enum_t race0;
   enum_t race1;
   enum_t race2;
   enum_t race3;
   
   uint32_t ladder_rank;
   uint32_t ladder_count;
   uint32_t league_rank;
   uint32_t league_count;
   uint32_t region_rank;
   uint32_t region_count;
   uint32_t world_rank;
   uint32_t world_count;
   uint32_t active_rank;
   uint32_t active_count;
};

// Representation of one ranking in time of one team.
struct team_rank_v1_t {

   team_rank_v1_t() {}
   
   id_t team_id;

   // The timestamp of the ladder data for presenting data points on site. Ideally this
   // should be the last time the ladder was updated. This data can not be retrieved
   // easily at all times. For already closed ladders it will be the season end date
   // (season <= 14 don't have sufficient meta data). For current season ladders it will
   // be the cache update time.
   double data_time;
   
   enum_t version;
   enum_t region;
   enum_t mode;
   enum_t league;
   enum_t tier;
   
   id_t ladder_id;
   float join_time;
   id_t source_id;  // Cache id where this ranking origins.

   float points;
   uint32_t wins;
   uint32_t losses;

   enum_t race0;
   enum_t race1;
   enum_t race2;
   enum_t race3;

   uint32_t ladder_rank;
   uint32_t ladder_count;
   uint32_t league_rank;
   uint32_t league_count;
   uint32_t region_rank;
   uint32_t region_count;
   uint32_t world_rank;
   uint32_t world_count;
};

// Representation of one ranking in time of one team.
struct team_rank_v2_t {

   team_rank_v2_t() {}
   
   id_t team_id;

   // The timestamp of the ladder data for presenting data points on site. Ideally this
   // should be the last time the ladder was updated. This data can not be retrieved
   // easily at all times. For already closed ladders it will be the season end date
   // (season <= 14 don't have sufficient meta data). For current season ladders it will
   // be the cache update time.
   double data_time;
   
   enum_t version;
   enum_t region;
   enum_t mode;
   enum_t league;
   enum_t tier;
   
   id_t ladder_id;
   float join_time;
   id_t source_id;  // Cache id where this ranking origins.

   int16_t mmr;
   float points;
   uint32_t wins;
   uint32_t losses;

   enum_t race0;
   enum_t race1;
   enum_t race2;
   enum_t race3; // Best race for 1v1 is coded here, only in c++.
   
   uint32_t ladder_rank;
   uint32_t ladder_count;
   uint32_t league_rank;
   uint32_t league_count;
   uint32_t region_rank;
   uint32_t region_count;
   uint32_t world_rank;
   uint32_t world_count;
};

using team_rank_t =  team_rank_v2_t;
using team_ranks_t = std::vector<team_rank_t>;

//
// Player.
//

struct player_t {
   id_t id;
   enum_t region;
   bid_t bid;
   enum_t realm;
   std::string name;
   std::string tag;
   std::string clan;
   id_t season_id;
   enum_t race;
   enum_t league;
   enum_t mode;
};

struct pr {
   pr(id_t p, enum_t r) : p(p), r(r) {}
   id_t p;
   enum_t r;
};

inline bool compare_pr(const pr& x, const pr& y)
{
   return x.p < y.p;
}

struct player_set_cmp {  // Is x before y?
   bool operator()(const player_t& x, const player_t& y) const {
      if (x.region < y.region) return true;
      if (y.region < x.region) return false;
      if (x.bid < y.bid)       return true;
      if (y.bid < x.bid)       return false;
      if (x.realm < y.realm)   return true;
      if (y.realm < x.realm)   return false;
      return false;
   }
};

using players_t =    std::vector<player_t>;
using player_set_t = std::set<player_t, player_set_cmp>;
using player_map_t = std::map<id_t, player_t>;

//
// Team.
//

struct team_t {
   id_t id;
   enum_t region;
   enum_t mode;
   id_t season_id;
   enum_t version;
   enum_t league;
   id_t m0;
   id_t m1;
   id_t m2;
   id_t m3;
   enum_t r0;
   enum_t r1;
   enum_t r2;
   enum_t r3;

   // Sort members (and races to have the first one with the lowest id.
   void normalize(uint32_t team_size) {
      if (team_size == 1) {
         return;
      }
      
      std::vector<pr> l;
      l.push_back(pr(m0, r0));
      l.push_back(pr(m1, r1));
      if (team_size > 2) l.push_back(pr(m2, r2));
      if (team_size > 3) l.push_back(pr(m3, r3));
      
      std::sort(l.begin(), l.end(), compare_pr);
      l.push_back(pr(0, -1));
      l.push_back(pr(0, -1));

      m0 = l[0].p; r0 = l[0].r;
      m1 = l[1].p; r1 = l[1].r;
      m2 = l[2].p; r2 = l[2].r;
      m3 = l[3].p; r3 = l[3].r;
   }

};

struct team_set_cmp {  // Is x before y?
   bool operator()(const team_t& x, const team_t& y) const {
      if (x.mode < y.mode) return true;
      if (y.mode < x.mode) return false;
      if (x.m0 < y.m0)     return true;
      if (y.m0 < x.m0)     return false;
      if (x.m1 < y.m1)     return true;
      if (y.m1 < x.m1)     return false;
      if (x.m2 < y.m2)     return true;
      if (y.m2 < x.m2)     return false;
      if (x.m3 < y.m3)     return true;
      if (y.m3 < x.m3)     return false;
      return false;
   }
};

using teams_t =    std::vector<team_t>;
using team_set_t = std::set<team_t, team_set_cmp>;
using team_map_t = std::map<id_t, team_t>;

//
// Ranking.
//

struct ranking
{
   ranking(id_t id, id_t season_id, float data_time, float updated) :
      id(id), season_id(season_id), data_time(data_time), updated(updated)
   {}

   id_t id;          // From ranking never ever use ranking_data.id or ranking_stats.id.
   id_t season_id;   // From ranking.
   float data_time;  // From ranking.
   float updated;    // From ranking_data.
};

using rankings_t = std::vector<ranking>;

//
// Ranking statistics.
//

// Note that the premade > 1v1 team and race stats is totally pointless, but that will be filtered when getting from db
// for page or in js.

// Stat version 0 is no longer used.

// Stat version 1 is a series of numbers (sums) where the index is based off the following:
// modes (8) -> version (3) -> region (5) -> league (7) -> races (5, including unknown)
// -> data (4, count, wins, losses, points)
// Ranking stats before lotv will contain zeroes for all that data. When fetching data a mapping to season version has
// to be done through ranking to determine of those zeroes should be ignored or not.
#define RANKING_STATS_VERSION_1 1

struct rs_data_t
{
   rs_data_t() : count(), wins(), losses(), points() {}
   
   uint64_t count;
   uint64_t wins;
   uint64_t losses;
   double points;
};

using rs_datas_t = std::vector<rs_data_t>;

struct ranking_stats_t
{
   uint32_t version;
   id_t ranking_id;     // Not saved in db data.
   double  data_time;   // Not saved in db data.
   id_t season_id;      // Not saved in db data.
   id_t season_version; // Not saved in db data.
   rs_datas_t datas;
};

using ranking_stats_list_t = std::vector<ranking_stats_t>;
