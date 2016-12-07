#include <iostream>
#include <sstream>
#include <boost/python/extract.hpp>

#include "get.hpp"
#include "db.hpp"
#include "log.hpp"
#include "exception.hpp"

using namespace boost::python;
using namespace std;


uint32_t find_team_rank(db& db, uint32_t ranking_id, id_t team_id, team_rank_window_t& trs)
{
   // Binary search getting four team ranks at a time because that will be enough for the common case. Results will be
   // filled in trs from pos 0 for non 1v1 there will only be one result.
   
   team_ranks_header trh;
   db.load_team_ranks_header(ranking_id, trh);

   int32_t imin = 0;             // Min index of possible hits (response is within this).
   int32_t imax = trh.count - 1; // Max index of possible hits (response is within this).
   uint32_t count = 0;
   uint32_t window_size = 4;
  
   while (trh.count > 0 && imax >= imin) {
  
      int32_t imid = imin + ((imax - imin) / 2); // This is the index getted from the db.
     
      uint32_t size = db.load_team_rank_window(ranking_id, trh.version, imid, trs, window_size);
  
      if (trs[0].team_id > team_id) {
         // Search lower.
         imax = imid - 1;
      }
      else if (trs[size - 1].team_id < team_id) {
         // Search higher.
         imin = imid + count;
      }
      else {
         // Range should have a hit or none exists, find it or calculate a window that will contain the answer.

         // Find hits in window.
         int32_t hit_lo = -1;
         int32_t hit_hi = -1;
         for (uint32_t i = 0; i < window_size; ++i) {
            if (trs[i].team_id == team_id) {
               if (hit_lo == -1) {
                  hit_lo = i;
               }
               hit_hi = i;
            }
         }
  
         // Return if nothing was found.
         if (hit_lo == -1) {
            return 0;
         }

         // Set ..
         if (hit_hi != int32_t(window_size) - 1) {
            // High limit found.
            imax = imid + hit_hi;
         }
  
         if (hit_lo > 0) {
            // Low limit found.
            imin = imin + hit_lo;
         }
         
         
         
      }
   }
   return 0;
   
   // while (trh.count > 0 && imax >= imin) {
   // 
   //    int32_t imid = imin + ((imax - imin) / 2);
   //    
   //    db.load_team_rank(ranking_id, trh.version, imid, trs);
   //    if (trs[0].team_id == team_id) {
   // 
   //       if (trs[2].team_id == team_id) {
   //          if (trs[2].version <= tr.version) {
   //             THROW(bug_exception, fmt("fatal, bad version (2) for team_id %d.", team_id));
   //          }
   //          
   //          // Return plus 2 this is a later version.
   //          tr = trs[2];
   //          return;
   //       }
   //       
   //       if (trs[1].team_id == team_id) {
   //          if (trs[1].version <= tr.version) {
   //             THROW(bug_exception, fmt("fatal, bad version (1) for team_id %d.", team_id));
   //          }
   //          
   //          // Return plus 1 this is a later version.
   //          tr = trs[1];
   //          return;
   //       }
   // 
   //       // Return the version we got.
   //       tr = trs[0];
   //       return;
   //    }
   //    else if (trs[0].team_id < team_id) {
   //       imin = imid + 1;
   //    }
   //    else {
   //       imax = imid - 1;
   //    }
   // }
   // tr.team_id = 0;
}

// TODO Remove mode again, maybe it is not needed?
boost::python::list
get::rankings_for_team(id_t team_id, uint32_t mode)
{
   boost::python::list res;
   
   db::transaction_block transaction(_db);

   rankings_t rankings = _db.get_available_rankings(_season_filter);

   team_rank_window_t trs;
   
   for (uint32_t i = 0; i < rankings.size(); ++i) {
      uint32_t found = find_team_rank(_db, rankings[i].id, team_id, trs);
      
      if (not found) continue;
      
      auto& team_rank = trs[0];
      if (rankings[i].season_id < MMR_SEASON or team_rank.mmr != NO_MMR) {
         boost::python::dict tr;
         
         tr["league"] = team_rank.league;
         tr["tier"] = team_rank.tier;
         tr["version"] = team_rank.version;
         tr["data_time"] = rankings[i].data_time;
         tr["season_id"] = rankings[i].season_id;
         tr["race0"] = team_rank.race0;

         tr["best_race"] = mode != TEAM_1V1 or team_rank.race3 == RACE_BEST;
         
         if (team_rank.mmr != NO_MMR) {
            tr["mmr"] = team_rank.mmr;
         }
         tr["points"] = team_rank.points;
         tr["wins"] = team_rank.wins;
         tr["losses"] = team_rank.losses;
         
         tr["world_rank"] = team_rank.world_rank;
         tr["world_count"] = team_rank.world_count;
         
         tr["region_rank"] = team_rank.region_rank;
         tr["region_count"] = team_rank.region_count;
         
         tr["league_rank"] = team_rank.league_rank;
         tr["league_count"] = team_rank.league_count;

         tr["ladder_rank"] = team_rank.ladder_rank;
         tr["ladder_count"] = team_rank.ladder_count;
         
         tr["id"] = rankings[i].id;
         
         res.attr("append")(tr);
      }
   }
   
   return res;
}

bool raw_mode_to_stringstream(stringstream& ss,
                              uint32_t mode_id,
                              uint32_t mode_i,
                              uint32_t data_count,
                              const ranking_stats_t& stats)
{
   const rs_datas_t& datas = stats.datas;

   ss << "{\"stat_version\":" << stats.version
      << ",\"id\":" << stats.ranking_id
      << ",\"mode_id\":" << mode_id
      << ",\"data_time\":" << stats.data_time
      << ",\"season_id\":" << stats.season_id
      << ",\"season_version\":" << stats.season_version
      << ",\"data\":[";
   
   char del = ' ';
   for (uint32_t i = data_count * mode_i; i < datas.size() && i < data_count * (mode_i + 1); ++i) {
      ss << del << datas[i].count
         << ',' << datas[i].wins
         << ',' << datas[i].losses
         << ',' << datas[i].points;
      del = ',';
   }
   ss << "]}";

   return true;
}

string
get::ranking_stats(uint32_t mode_id)
{
   db::transaction_block transaction(_db);

   stringstream ss;

   ranking_stats_list_t list;
   _db.load_all_ranking_stats(list, _season_filter);
   
   char del = ' ';
   ss << "[";
   for (uint32_t i = 0; i < list.size(); ++i) {
      const ranking_stats_t& stats = list[i];
      
      // Find mode index for this stats version, skip if it does not exist.
      
      object enums_stat = _enums_info["stat"][stats.version];
      vector<enum_t> modes = extract_enum(enums_stat, "mode_ids");
      
      uint32_t mode_i = 0;
      for (; mode_i < modes.size(); ++mode_i) {
         if (modes[mode_i] == enum_t(mode_id)) {
            break;
         }
      }

      // Get extract the data to the stringstream.
      
      if (mode_i != modes.size()) {
         ss << del;
         raw_mode_to_stringstream(ss, mode_id, mode_i, extract<uint32_t>(enums_stat["data_count"]), stats);
         del = ',';
      }
   }
   ss << "]";
   
   return ss.str();
}

