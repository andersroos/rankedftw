#pragma once

#include "log.hpp"
#include "types.hpp"
#include "db.hpp"

// Filter team_ranks from ranking data, keep a cache of all team ids in object.
struct purger {

   purger(const std::string& db_name) :
      _db(db_name)
   {}

   purger(const ranking_data& other) = delete;

   void purge_removed_teams_from_ranking(id_t ranking_id, float now, std::string threshold_date) {
      if (_team_ids.size() == 0) {
         LOG_INFO("loading team ids");
         _db.load_seen_team_ids(_team_ids, threshold_date);
      }
      _db.load_team_ranks(ranking_id, _team_ranks);
      team_ranks_t filtered_team_ranks;
      std::copy_if(_team_ranks.begin(), 
                   _team_ranks.end(),
                   std::back_inserter(filtered_team_ranks),
                   [&](const team_rank_t& tr){return _team_ids.find(tr.team_id) != _team_ids.end();}
         );
      _db.save_team_ranks(ranking_id, now, filtered_team_ranks);
   }
   
   virtual ~purger() {}

private:

   // The ranking data.
   team_ranks_t _team_ranks;

   // Player cache.
   std::unordered_set<id_t> _team_ids;
   
   db _db;
};
