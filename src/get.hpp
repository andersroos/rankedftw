#pragma once

#include <boost/python/dict.hpp>
#include <boost/python/list.hpp>

#include "types.hpp"
#include "db.hpp"


struct get
{
   get(const std::string& db_name, const boost::python::dict& enums_info, uint32_t season_filter) :
      _db(db_name), _enums_info(enums_info), _season_filter(season_filter)
   {}
   
   // Get all team rankings for a team.
   boost::python::list rankings_for_team(id_t team_id, uint32_t mode);

   // Get all rankings stats for one mode. Returs a string json.
   std::string ranking_stats(uint32_t mode_id);
   
   virtual ~get() {}   
   
private:

   db _db;
   const boost::python::dict _enums_info;
   uint32_t _season_filter;
};
