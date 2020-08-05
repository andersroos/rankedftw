#pragma once

#include <boost/thread/mutex.hpp>    
#include <jsoncpp/json/json.h>

#include "db.hpp"
#include "log.hpp"
#include "types.hpp"

// Holds a ladder sorted on version and mode. Can the sort sub portions of ladder for each request depending on what the
// user wants.
struct ladder_handler
{
   ladder_handler(const std::string& db_name, uint32_t keep_api_data_days) :
      _db_name(db_name), _keep_api_data_days(keep_api_data_days), _last_checked(), _ranking(0, 0, 0, 0, 0) {}

   // Get a ladder slice of the ladder offseted by team_id or offset in the request. Return the teams in that
   // slice. Sorting and filtering possible.
   Json::Value ladder(const Json::Value& request);

   // Get rankings for a clan (set of team ids in the request). Sorting and filtering possible.
   Json::Value clan(const Json::Value& request);

   // Reload ranking will reload the ranking for db.
   Json::Value refresh(const Json::Value& request);
   
   virtual ~ladder_handler() {}
   
private:

   // Get ranking from db if new ranking is available.
   void refresh_ranking(bool force=false);

   std::string _db_name;
   uint32_t _keep_api_data_days;
   uint64_t _last_checked;
   ranking_t _ranking;
   mutable boost::mutex _mutex;
   team_ranks_t _team_ranks;
};
