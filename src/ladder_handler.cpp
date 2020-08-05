#include <boost/thread.hpp>    
#include <algorithm>
#include <unordered_set>
#include <tuple>

#include "compare.hpp"
#include "ladder_handler.hpp"
#include "exception.hpp"

using namespace std;

void
ladder_handler::refresh_ranking(bool force)
{
   uint64_t now = now_us();
   double data_time_low_limit = (now / 1e6) - _keep_api_data_days * 24 * 3600;
   
   boost::lock_guard<boost::mutex> lock(_mutex);
   // Check for new data every 1 minutes.
   if (_last_checked == 0 or now > _last_checked + 1e6 * 60 * 1 or force) {
      _last_checked = now;
      db db(_db_name);
      ranking_t ranking = db.get_latest_ranking();
      
      // Reload if new data.
      if (ranking.id != _ranking.id or ranking.updated > _ranking.updated) {
         LOG_INFO("loading ranking %d", ranking.id);
         db.load_team_ranks(ranking.id, _team_ranks, data_time_low_limit);
         // Make sure new data is sorted on version and mode since request will filter on version and mode before
         // sorting (or sorting will take too long time).
         sort(_team_ranks.begin(), _team_ranks.end(), compare_version_mode_world_rank);
         LOG_INFO("ranking loaded and sorted");
         _ranking = ranking;
      }
      else {
         LOG_INFO("no new ranking available");
      }
   }
}

Json::Value
ladder_handler::refresh(const Json::Value& request)
   
{
   Json::Value response;
   response["code"] = "ok";
   LOG_INFO("got refresh ping");
   refresh_ranking(true);
   return response;
}

// Set start and end iterators to start and end of version and mode in team_ranks.
tuple<team_ranks_t::iterator, team_ranks_t::iterator>
find_span(team_ranks_t& team_ranks, enum_t version, enum_t mode)
{
   team_ranks_t::iterator start = team_ranks.begin();
   for (; start != team_ranks.end() and not (start->version == version and start->mode == mode); ++start) {}
   team_ranks_t::iterator end = start;
   for (; end != team_ranks.end() and (end->version == version and end->mode == mode); ++end) {}
   return make_tuple(start, end);
}

// Return teams json array, offset is offset for start and is used to calculate rank, rank is used for start rank since
// that is dependend on data before start.
Json::Value build_teams_array(const cmp_tr& cmp_op,
                              const team_ranks_t::const_iterator& start,
                              const team_ranks_t::const_iterator& end,
                              uint32_t rank,
                              uint32_t offset)
{
   Json::Value teams(Json::arrayValue);
   team_ranks_t::const_iterator curr = start;
   team_rank_t last = *curr;  // Last rank, to be able to detect which team_ranks that are the same rank.

   for (uint32_t i = 0; curr < end; ++i, ++curr) {
      if (cmp_op(last, *curr) or cmp_op(*curr, last)) {
         rank = i + offset;
         last = *curr;
      }
      Json::Value team;
      team["rank"] = rank;
      team["team_id"] = curr->team_id;
      team["region"] = curr->region;
      team["league"] = curr->league;
      team["tier"] = curr->tier;
      team["mmr"] = curr->mmr;
      team["points"] = curr->points;
      team["wins"] = curr->wins;
      team["losses"] = curr->losses;
      team["win_rate"] = (curr->wins or curr->losses) ? float(100 * curr->wins) / (curr->wins + curr->losses) : 0;
      team["data_time"] = uint32_t(curr->data_time);
      team["m0_race"] = curr->race0;
      team["m1_race"] = curr->race1;
      team["m2_race"] = curr->race2;
      team["m3_race"] = curr->race3;
      teams.append(team);
   }
   return teams;
}


// Based on filter in request, sort and narrow span based off that.
cmp_tr sort_and_filter_span(team_ranks_t::iterator& start, team_ranks_t::iterator& end, const Json::Value& request)
{
   // Optional filters (-64 means not set). Race always filters on race0 (only relevant for 1 person teams).

   enum_t region = request.get("region", NOT_SET).asInt();
   enum_t race =   request.get("race", NOT_SET).asInt();
   enum_t league = request.get("league", NOT_SET).asInt();
   
   // Sort key and order to use.
   
   enum_t key = request["key"].asInt();
   bool reverse = request["reverse"].asBool();

   // Create sorts and sort.
   
   stable_sort(start, end, cmp_tr(reverse, region, league, race, key));

   // Find filter span and return it.
   
   cmp_tr cmp_strict(reverse, region, league, race, key, true);
   
   for (; start != end and !cmp_strict.use(*start); ++start) {}
   team_ranks_t::iterator mode_end = end;
   
   for (end = start; end != mode_end and cmp_strict.use(*end); ++end) {}
   
   return cmp_strict;
}


Json::Value
ladder_handler::clan(const Json::Value& request)
{
   refresh_ranking();

   boost::lock_guard<boost::mutex> lock(_mutex);

   // Read team ids from request.
   
   std::unordered_set<id_t> team_ids;
   auto& val = request["team_ids"];
   for (uint32_t i = 0; i < val.size(); ++i) {
      team_ids.insert(val[i].asUInt());
   }

   // Find mode, version span then pick out ids, then apply filters.
   Json::Value response;
   response["code"] = "ok";

   team_ranks_t::iterator start;
   team_ranks_t::iterator end;
   tie(start, end) = find_span(_team_ranks, LOTV, TEAM_1V1);

   // Get ladder members and work with them.

   team_ranks_t team_ranks;
   for (team_ranks_t::iterator tr = start; tr < end; ++tr) {
      if (team_ids.find(tr->team_id) != team_ids.end()) {
         team_ranks.push_back(*tr);
      }
   }

   // Find start and end based in filter.

   start = team_ranks.begin();
   end = team_ranks.end();
   cmp_tr cmp_strict = sort_and_filter_span(start, end, request);

   if (end <= start) {
      // Return here, code below will fail if there is no data.
      response["teams"] = Json::Value(Json::arrayValue);
      return response;
   }

   // Sort it and build response.
   
   response["teams"] = build_teams_array(cmp_strict, start, end, 0, 0);
   return response;
}

Json::Value
ladder_handler::ladder(const Json::Value& request)
{
   refresh_ranking();
   
   boost::lock_guard<boost::mutex> lock(_mutex);   

   // Required filters.
   
   enum_t version = request.get("version", LOTV).asInt();
   enum_t mode =    request.get("mode", TEAM_1V1).asInt();

   // Position and order. See view for description about team_id and offset, it is pretty complicated.

   int32_t offset = request.get("offset", -1).asInt(); // None offset is represented by -1 here.

   uint32_t team_id = request["team_id"].asInt();
   uint32_t limit = request["limit"].asInt();
   
   // Get start and end position of sort (based on mode and version), then sort it using filters.

   team_ranks_t::iterator start;
   team_ranks_t::iterator end;
   tie(start, end) = find_span(_team_ranks, version, mode);
   
   // Find start and end based in filter.

   cmp_tr cmp_strict = sort_and_filter_span(start, end, request);
   uint32_t count = end - start;
   
   // Start on response.
   
   Json::Value response = request;
   response["code"] = "ok";
   response["count"] = count;

   if (offset == -1 and team_id != 0) {
      // Use team based offset.

      team_ranks_t::iterator team_i = start;
      for (uint32_t o = 0; team_i != end; ++o, ++team_i) {
         if (team_i->team_id == team_id) {
            offset = max(int32_t(o) - 10, 0);
            break;
         }
      }
   }
   offset = max(offset, 0);
   offset = std::min(uint32_t(offset), count);

   if (not count) {
      // Return here, code below will fail if there is no data.
      response["teams"] = Json::Value(Json::arrayValue);
      response["offset"] = offset;
      return response;
   }
   
   // Go back, find the actual start of the first rank of the page to calculate correct rank to start with.
   
   team_ranks_t::iterator rank_start = start + offset;  // Set to first rank on page, check similar to this backwards.
   team_rank_t last = *rank_start;                      // Save rank start to be able to compare.
   uint32_t rank;                                       // Actual rank to set for team, 0 indexed, just as offset.
   
   while (true) {
      if (cmp_strict(last, *rank_start) or cmp_strict(*rank_start, last)) {
         // This is the first not the same, rank start is this offset + 1.
         rank = rank_start - start + 1;
         break;
      }
      else if (start == rank_start) {
         // If start is the same rank as rank_start we are at firts rank, which is rank 0.
         rank = 0;
         break;
      }
            
      --rank_start;
   }

   team_ranks_t::iterator curr = start + offset;

   response["teams"] = build_teams_array(cmp_strict, curr, min(end, curr + limit), rank, offset);
   response["offset"] = offset;
   
   return response;
}

