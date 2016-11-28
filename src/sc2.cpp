
#include <boost/python/module.hpp>
#include <boost/python/class.hpp>
#include <boost/python/def.hpp>

#include "log.hpp"
#include "db.hpp"
#include "get.hpp"
#include "test_aid.hpp"
#include "ranking_data.hpp"

using namespace boost::python;

extern object py_logger;

void set_logger(object python_logger)
{
   py_logger = python_logger;
}


BOOST_PYTHON_MODULE(sc2)
{
   // Set the python logger for the process.
   def("set_logger", set_logger);

   class_<get, boost::noncopyable>("Get", init<std::string, dict, uint32_t>())
      .def("rankings_for_team", &get::rankings_for_team)
      .def("ranking_stats", &get::ranking_stats)
      ;

   class_<ranking_data, boost::noncopyable>("RankingData", init<std::string, dict>())
      .def("load", &ranking_data::load)
      .def("save_data", &ranking_data::save_data)
      .def("save_stats", &ranking_data::save_stats)
      .def("update_with_ladder", &ranking_data::update_with_ladder)
      .def("min_max_data_time", &ranking_data::min_max_data_time)
      .def("clear_team_ranks", &ranking_data::clear_team_ranks)
      .def("reconnect_db", &ranking_data::reconnect_db)
      .def("release", &ranking_data::release)
      ;
   
   //
   // Test Aid
   //
   
   // Log some test messages.
   def("log_test", test_aid::log_test);

   // Save ranking data in ranking_data for testing, teams and players should be created before.
   def("save_ranking_data_raw", test_aid::save_ranking_data_raw);

   // Do not use the server but simulate a request to the ladder handler.   
   def("direct_ladder_handler_request_ladder", test_aid::direct_ladder_handler_request_ladder);
   def("direct_ladder_handler_request_clan", test_aid::direct_ladder_handler_request_clan);

   // Get ranking data as a python object, sorted in version, mode, world rank - order.
   def("get_team_ranks", test_aid::get_team_ranks);
   
}
