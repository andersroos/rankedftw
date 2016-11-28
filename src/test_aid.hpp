#pragma once

#include <types.hpp>
#include <iostream>
#include <boost/python/list.hpp>


namespace test_aid
{

   void save_ranking_data_raw(const std::string& db_name,
                              id_t ranking_id,
                              float now,
                              const boost::python::list& p_trs,
                              bool sort);
   
   void log_test();

   std::string direct_ladder_handler_request_ladder(const std::string& db_name, const std::string& request);
   
   std::string direct_ladder_handler_request_clan(const std::string& db_name, const std::string& request);

   boost::python::list get_team_ranks(const std::string& db_name, id_t team_rank_id, bool sort);
};
