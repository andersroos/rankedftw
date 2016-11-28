#include <iostream>
#include <sstream>
#include <boost/python/extract.hpp>

#include "get.hpp"
#include "db.hpp"
#include "log.hpp"
#include "exception.hpp"

using namespace boost::python;
using namespace std;

void find_team_rank(db& db, uint32_t ranking_id, id_t team_id, team_rank_t& tr)
{
   team_ranks_header trh;
   db.load_team_ranks_header(ranking_id, trh);

   int32_t imin = 0;
   int32_t imax = trh.count - 1;
   team_rank_t tr_plus_1;
   team_rank_t tr_plus_2;

   while (trh.count > 0 && imax >= imin) {

      int32_t imid = imin + ((imax - imin) / 2);
      
      db.load_team_rank(ranking_id, trh.version, imid, tr, tr_plus_1, tr_plus_2);
      if (tr.team_id == team_id) {

         if (tr_plus_2.team_id == team_id) {
            if (tr_plus_2.version <= tr.version) {
               THROW(bug_exception, fmt("fatal, bad version (2) for team_id %d.", team_id));
            }
            
            // Return plus 2 this is a later version.
            tr = tr_plus_2;
            return;
         }
         
         if (tr_plus_1.team_id == team_id) {
            if (tr_plus_1.version <= tr.version) {
               THROW(bug_exception, fmt("fatal, bad version (1) for team_id %d.", team_id));
            }
            
            // Return plus 1 this is a later version.
            tr = tr_plus_1;
            return;
         }

         // Return the version we got.
         return;
      }
      else if (tr.team_id < team_id) {
         imin = imid + 1;
      }
      else {
         imax = imid - 1;
      }
   }
   tr.team_id = 0;
}

boost::python::list
get::rankings_for_team(id_t team_id)
{
   boost::python::list res;
   
   db::transaction_block transaction(_db);

   rankings_t rankings = _db.get_available_rankings(_season_filter);
   
   for (uint32_t i = 0; i < rankings.size(); ++i) {
      team_rank_t team_rank;
      find_team_rank(_db, rankings[i].id, team_id, team_rank);

      if (team_rank.team_id != 0) {
         boost::python::dict tr;

         tr["league"] = team_rank.league;
         tr["tier"] = team_rank.tier;
         tr["version"] = team_rank.version;
         tr["data_time"] = rankings[i].data_time;
         tr["season_id"] = rankings[i].season_id;
         tr["race0"] = team_rank.race0;
         
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

