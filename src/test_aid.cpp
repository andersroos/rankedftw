#include <boost/python/object.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/extract.hpp>
#include <jsoncpp/json/json.h>

#include "test_aid.hpp"
#include "db.hpp"
#include "log.hpp"
#include "ladder_handler.hpp"
#include "compare.hpp"

using namespace boost::python;
using namespace std;

void
test_aid::save_ranking_data_raw(const string& db_name,
                                id_t ranking_id, float now,
                                const boost::python::list& p_trs,
                                bool sort)
{
   db db(db_name);

   team_ranks_t trs;
    
   for (uint32_t i = 0; i < len(p_trs); ++i) {
      object p_tr = p_trs[i];
      team_rank_t tr;
      
      tr.team_id               = extract<id_t    >(p_tr["team_id"]);
      tr.data_time             = extract<double  >(p_tr["data_time"]);
      tr.version               = extract<enum_t  >(p_tr["version"]);
      tr.region                = extract<enum_t  >(p_tr["region"]);
      tr.mode                  = extract<enum_t  >(p_tr["mode"]);
      tr.league                = extract<enum_t  >(p_tr["league"]);
      tr.tier                  = extract<enum_t  >(p_tr["tier"]);
      tr.ladder_id             = extract<id_t    >(p_tr["ladder_id"]);
      tr.join_time             = extract<float   >(p_tr["join_time"]);
      tr.mmr                   = extract<int16_t >(p_tr["mmr"]);
      tr.source_id             = extract<id_t    >(p_tr["source_id"]);
      tr.points                = extract<float   >(p_tr["points"]);
      tr.wins                  = extract<uint32_t>(p_tr["wins"]);
      tr.losses                = extract<uint32_t>(p_tr["losses"]);
      tr.race0                 = extract<enum_t  >(p_tr["race0"]);
      tr.race1                 = extract<enum_t  >(p_tr["race1"]);
      tr.race2                 = extract<enum_t  >(p_tr["race2"]);
      tr.race3                 = extract<enum_t  >(p_tr["race3"]);
      tr.ladder_rank           = extract<uint32_t>(p_tr["ladder_rank"]);
      tr.ladder_count          = extract<uint32_t>(p_tr["ladder_count"]);
      tr.league_rank           = extract<uint32_t>(p_tr["league_rank"]);
      tr.league_count          = extract<uint32_t>(p_tr["league_count"]);
      tr.region_rank           = extract<uint32_t>(p_tr["region_rank"]);
      tr.region_count          = extract<uint32_t>(p_tr["region_count"]);
      tr.world_rank            = extract<uint32_t>(p_tr["world_rank"]);
      tr.world_count           = extract<uint32_t>(p_tr["world_count"]);
      trs.push_back(tr);
   }
   if (sort)
      stable_sort(trs.begin(), trs.end(), compare_team_id_version_race);
   
   db.save_team_ranks(ranking_id, now, trs);
}


void
test_aid::log_test()
{
   LOG_INFO("info %d", 123);
   LOG_WARNING("warning %d", 1236);
   LOG_ERROR("error %d", 123123);
}



string
test_aid::direct_ladder_handler_request_ladder(const string& db_name, const string& request)
{
   ladder_handler ladder_handler(db_name, 14);

   Json::Reader reader;
   Json::FastWriter writer;
   Json::Value value;
   reader.parse(request, value);
   
   return writer.write(ladder_handler.ladder(value));
}

string
test_aid::direct_ladder_handler_request_clan(const string& db_name, const string& request)
{
   ladder_handler ladder_handler(db_name, 14);

   Json::Reader reader;
   Json::FastWriter writer;
   Json::Value value;
   reader.parse(request, value);
   
   return writer.write(ladder_handler.clan(value));
}

boost::python::list
test_aid::get_team_ranks(const std::string& db_name, id_t ranking_id, bool sort)
{
   db db(db_name);
   team_ranks_t team_ranks;
   db.load_team_ranks(ranking_id, team_ranks);
   if (sort) {
      stable_sort(team_ranks.begin(), team_ranks.end(), compare_version_mode_world_rank);
   }
   
   boost::python::list ranks;

   for (team_ranks_t::iterator i = team_ranks.begin(); i != team_ranks.end(); ++i) {
      boost::python::dict tr;
      tr["team_id"] = i->team_id;
      tr["data_time"] = i->data_time;
      tr["version"] = i->version;
      tr["region"] = i->region;
      tr["mode"] = i->mode;
      tr["league"] = i->league;
      tr["tier"] = i->tier;
      tr["ladder_id"] = i->ladder_id;
      tr["join_time"] = i->join_time;
      tr["source_id"] = i->source_id;
      tr["mmr"] = i->mmr;
      tr["points"] = i->points;
      tr["wins"] = i->wins;
      tr["losses"] = i->losses;
      tr["race0"] = i->race0;
      tr["race1"] = i->race1;
      tr["race2"] = i->race2;
      tr["race3"] = i->race3;
      tr["ladder_rank"] = i->ladder_rank;
      tr["ladder_count"] = i->ladder_count;
      tr["league_rank"] = i->league_rank;
      tr["league_count"] = i->league_count;
      tr["region_rank"] = i->region_rank;
      tr["region_count"] = i->region_count;
      tr["world_rank"] = i->world_rank ;
      tr["world_count"] = i->world_count;
      
      ranks.append(tr);
   }

   return ranks;
}

