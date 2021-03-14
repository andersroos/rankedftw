#pragma once

#include <boost/python/dict.hpp>
#include <boost/python/list.hpp>

#include "types.hpp"
#include "db.hpp"


struct get
{
   get(const std::string& db_name, const boost::python::dict& enums_info, uint32_t from_season) :
      _db(db_name), _enums_info(enums_info), _from_season(from_season)
   {}
   
   // Get all team rankings for a team. Uint32_t or strange errors in python call.
   boost::python::list rankings_for_team(id_t team_id);

   // Get all rankings stats for one mode. Returs a string json. Uint32_t or strange errors in python call.
   std::string ranking_stats(uint32_t mode_id);

   // Returns game played count by region for ranking.
   boost::python::dict games_played(id_t id);

   virtual ~get() {}
   
private:

   db _db;
   const boost::python::dict _enums_info;
   uint32_t _from_season;
};
