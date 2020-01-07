#pragma once

#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/thread/mutex.hpp>
#include <boost/thread.hpp>    

#include "log.hpp"
#include "types.hpp"
#include "db.hpp"
#include "timer.hpp"

// Keep a full ranking data in memory to be able to continously update it with new ladders.
struct ranking_data {

   ranking_data(const std::string& db_name, const boost::python::dict enums_info) :
      _db(db_name),
      _enums_info(enums_info)
   {}

   ranking_data(const ranking_data& other) = delete;
   
   // Load ranking (data) to use as base for updating, if not loading, an empty team rank will be used.
   void load(id_t id);

   // Save to the ranking data of the ranking and set now as updated time.
   void save_data(id_t id, id_t season_id, float now);

   // Save to the ranking stats of the ranking and set now as updated time.
   void save_stats(id_t id, float now);

   // Return the <min, max> data_time for the rankings.
   boost::python::list min_max_data_time();

   // Update ranking in memory with a ladder, new/updates teams/users will be saved directly to the database.
   boost::python::dict update_with_ladder(id_t ladder_id,
                                          id_t source_id,
                                          enum_t region,
                                          enum_t mode,
                                          enum_t league,
                                          enum_t tier,
                                          enum_t version,
                                          id_t season_id,
                                          double data_time,
                                          std::string date_date,
                                          uint32_t team_size,
                                          boost::python::list members);

   // Clear team ranks, but keep caches and db connection.
   void clear_team_ranks()
   {
      boost::lock_guard<boost::mutex> lock(_team_ranks_mutex);
      _team_ranks.clear();
   }

   // Reconnect db (adding method to desperatly try to resolv failing BEGIN situation).
   void reconnect_db()
   {
      _db.reconnect();
   }
   
   // Release resources.
   void release()
   {
      _db.disconnect();
      _team_ranks.clear();
      _player_cache.clear();
      _team_cache.clear();
   }      

   virtual ~ranking_data() {}

private:

   // The ranking data.
   team_ranks_t _team_ranks;

   // Guard for _team_ranks, make sure to lock mutex before starting transaction_block to maipulate rankings in db or we
   // may have deadlocks.
   boost::mutex _team_ranks_mutex;

   // Player cache.
   player_set_t _player_cache;

   // Team cache.
   team_set_t _team_cache;
   
   db _db;
   
   const boost::python::dict _enums_info;
};
