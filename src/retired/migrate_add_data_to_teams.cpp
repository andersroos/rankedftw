
#include <iostream>
#include <fstream>
#include <algorithm>
#include <time.h>

#include "exception.hpp"
#include "types.hpp"
#include "db.hpp"
#include "log.hpp"
#include "timer.hpp"
#include "rankings.hpp"

using namespace std;

struct update_t {
   id_t team_id;
   enum_t version;
   enum_t league;
};

typedef std::map<id_t, update_t> updates_t;
   

// Migrating of teams, adding season and version to teams. All inforamtion is in the team ranks, so we will loop through
// the latest ranking per season backwards. Then update all teams in that ranking. Also adding team ids to a map to be
// able to filter those teams from earlier rankings.
int main()
{
   db db("sc2");

   db.exec("SELECT id, season_id FROM ranking WHERE status = 1 "
           " ORDER BY season_id DESC, data_time DESC");

   rankings_t rankings;
   for (uint32_t i = 0; i < db.res_size(); ++i) {
      ranking ranking(db.res_int(i, 0), db.res_int(i, 1), 0, 0);
      rankings.push_back(ranking);
   }

   LOG_INFO("loaded %d rankings to process", rankings.size());

   std::set<id_t> processed;
   
   for (rankings_t::iterator ri = rankings.begin(); ri != rankings.end(); ++ri) {
      LOG_INFO("===");
      LOG_INFO("loading team ranks %d from season %d", ri->id, ri->season_id);
      uint32_t updated_rows = 0;
      updates_t updates;
      {
         team_rank_db_stats stats;
         team_ranks_t team_ranks;
         db.load_team_ranks(stats, ri->id, team_ranks);
      
         LOG_INFO("processing team ranks");
         for (team_ranks_t::iterator i = team_ranks.begin(); i != team_ranks.end(); ++i) {

            // Filter first, then add to processed, need to allow multiple instances of team within rank.
            if (processed.find(i->team_id) == processed.end()) {
               update_t update;
               update.team_id = i->team_id;
               update.version = i->version;
               update.league = i->league;

               updates_t::iterator ud = updates.find(i->team_id);
               if (ud == updates.end() or ud->second.version < update.version) {
                  updates[i->team_id] = update;
               }
               else if (ud->second.version == update.version) {
                  THROW(bug_exception, fmt("same version twice, for team %d", i->team_id));
               }
            }
         }
      }

      LOG_INFO("%d teams to update", updates.size());

      // Do the actual updating in batches.
      updates_t::iterator ud = updates.begin();
      while (ud != updates.end()) {
         // Batch.
         
         db::transaction_block transaction(db);
      
         db.exec("CREATE TEMP TABLE updated_team ("
                 "  id integer,"
                 "  season_id integer,"
                 "  version integer,"
                 "  league integer"
                 ") ON COMMIT DROP");
         db.exec("CREATE INDEX updated_team_id ON updated_team USING btree (id)");
         
         stringstream sql;
         sql << "INSERT INTO updated_team (id, season_id, version, league) VALUES ";
         char delimiter = ' ';
         for (uint32_t i = 0; i < 800 and ud != updates.end(); ++i, ++ud) {
            sql << delimiter << "(" << ud->second.team_id << "," << ri->season_id
                << "," << int(ud->second.version) << "," << int(ud->second.league) << ")";
            delimiter = ',';
         }
         sql << ";";
         db.exec(sql);
         
         db.exec("UPDATE team t"
                 " SET"
                 "   season_id = s.season_id,"
                 "   version = s.version,"
                 "   league = s.league"
                 " FROM updated_team s"
                 " WHERE"
                 " t.id = s.id;");
         updated_rows += db.affected_rows();
      }
      
      for (updates_t::iterator i = updates.begin(); i != updates.end(); ++i) {
         processed.insert(i->first);
      }
      
      LOG_INFO("processing complete, %d team ranks done, %d updated teams", updates.size(), updated_rows);
   }
   
   return 0;
}
