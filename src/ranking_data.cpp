#include <boost/python/object.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/stl_iterator.hpp>
#include <boost/python/extract.hpp>
#include <algorithm>

#include "log.hpp"
#include "ranking_data.hpp"
#include "exception.hpp"
#include "util.hpp"
#include "compare.hpp"
#include "io.hpp"

using namespace boost::python;
using namespace std;


inline enum_t get_sort_key(id_t season_id)
{
   return season_id >= MMR_SEASON ? MMR : LEAGUE_POINTS;
}

void ranking_data::load(id_t id)
{
   boost::lock_guard<boost::mutex> lock(_team_ranks_mutex);
   db::transaction_block tb(_db);   
   _db.load_team_ranks(id, _team_ranks);
}

void ranking_data::save_data(id_t id, id_t season_id, float now)
{
   boost::lock_guard<boost::mutex> lock(_team_ranks_mutex);

   // Fix order here later, mostly used for team page.
   
   // Sort the team ranks in global order within version and mode to be able to calculate the rest of the rankings.

   enum_t sort_key = get_sort_key(season_id);
   
   cmp_tr cmp_inner(NOT_REVERSED, NOT_SET, NOT_SET, NOT_SET, sort_key, STRICT);
   stable_sort(_team_ranks.begin(), _team_ranks.end(), cmp_tr_version_mode(cmp_inner));

   // Calcualte ranks, possible to do this smarter, but who cares, saving this in database
   // will take infinite more time anyways.

   uint32_t world_count;
   uint32_t region_count;
   uint32_t league_count;
   uint32_t pos;
   uint32_t rank;

   vector<enum_t> versions = extract_enum(_enums_info, "version_ranking_ids");
   vector<enum_t> modes = extract_enum(_enums_info, "mode_ranking_ids");
   vector<enum_t> regions = extract_enum(_enums_info, "region_ranking_ids");
   vector<enum_t> leagues = extract_enum(_enums_info, "league_ranking_ids");

   // Loop over game versions.
   for (vector<enum_t>::iterator version_i = versions.begin(); version_i != versions.end(); ++version_i) {
      enum_t version = *version_i;
      
      // Loop over modes.

      for (vector<enum_t>::iterator mode_i = modes.begin(); mode_i != modes.end(); ++mode_i) {
         enum_t mode = *mode_i;
         
         world_count = 0;

         // Loop over all regions.
         for (vector<enum_t>::iterator region_i = regions.begin(); region_i != regions.end(); ++region_i) {
            enum_t region = *region_i;
            
            region_count = 0;
            
            // Loop over all leagues in the region.
            for (vector<enum_t>::iterator league_i = leagues.begin(); league_i != leagues.end(); ++league_i) {
               enum_t league = *league_i;
            
               // Count league size.
               league_count = 0;
               for (auto tr = _team_ranks.begin(); tr != _team_ranks.end(); ++tr) {
                  if (tr->mode == mode and tr->version == version
                      and tr->region == region and tr->league == league) {
                     ++league_count;
                  }
               }
               
               // Set league ranks.
               auto last_tr = _team_ranks.end();
               cmp_tr cmp(NOT_REVERSED, region, league, NOT_SET, sort_key, STRICT);
               pos = 1;
               rank = 1;
               for (auto tr = _team_ranks.begin(); tr != _team_ranks.end(); ++tr) {
                  if (tr->mode == mode and tr->version == version and cmp.use(*tr)) {
                     if (last_tr == _team_ranks.end() or cmp(*last_tr, *tr) or cmp(*tr, *last_tr)) {
                        rank = pos;
                        last_tr = tr;
                     }
                     tr->league_rank = rank;
                     tr->league_count = league_count;
                     ++pos;
                  }
               }
               region_count += league_count;
            }
               
            // Set region ranks.
            auto last_tr = _team_ranks.end();
            cmp_tr cmp(NOT_REVERSED, region, NOT_SET, NOT_SET, sort_key, STRICT);
            pos = 1;
            rank = 1;
            for (auto tr = _team_ranks.begin(); tr != _team_ranks.end(); ++tr) {
               if (tr->mode == mode and tr->version == version and cmp.use(*tr)) {
                  if (last_tr == _team_ranks.end() or cmp(*last_tr, *tr) or cmp(*tr, *last_tr)) {
                     rank = pos;
                     last_tr = tr;
                  }
                  tr->region_rank = rank;
                  tr->region_count = region_count;
                  ++pos;
               }
            }
            world_count += region_count;
         }
         
         // Set world ranks.
         auto last_tr = _team_ranks.end();
         cmp_tr cmp(NOT_REVERSED, NOT_SET, NOT_SET, NOT_SET, sort_key, STRICT);
         pos = 1;
         rank = 1;
         for (auto tr = _team_ranks.begin(); tr != _team_ranks.end(); ++tr) {
            if (tr->mode == mode and tr->version == version and cmp.use(*tr)) {
               if (last_tr == _team_ranks.end() or cmp(*last_tr, *tr) or cmp(*tr, *last_tr)) {
                  rank = pos;
                  last_tr = tr;
               }
               tr->world_rank = rank;
               tr->world_count = world_count;
               ++pos;
            }
         }

         // Set best rank for 1v1 where different ranks per race is possible.
         std::set<id_t> team_ids;
         if (mode == TEAM_1V1) {
            for (auto& tr : _team_ranks) {
               if (team_ids.find(tr.team_id) == team_ids.end()) {
                  tr.race3 = RACE_BEST;
                  team_ids.insert(tr.team_id);
               }
               else {
                  tr.race3 = RACE_ANY;
               }
            }
         }
      }
   }
   
   // Write new team_ranks to database.
   
   stable_sort(_team_ranks.begin(), _team_ranks.end(), compare_team_id_version_race);

   db::transaction_block tb(_db);   
   _db.save_team_ranks(id, now, _team_ranks);
}

void ranking_data::save_stats(id_t id, float now)
{
   boost::lock_guard<boost::mutex> lock(_team_ranks_mutex);
   
   stable_sort(_team_ranks.begin(), _team_ranks.end(), compare_for_ranking_stats_v1);

   ranking_stats_t stats;
   stats.ranking_id = id;
   rs_datas_t& datas = stats.datas;

   // It is very important that all those enums are sorted as ints because the sorted team_ranks will have to be
   // processed in order or the code won't work, enum info stat ids arrays are sorted because of this.
   object enums_stat = _enums_info["stat"][RANKING_STATS_VERSION_1];
   vector<enum_t> modes = extract_enum(enums_stat, "mode_ids");
   vector<enum_t> versions = extract_enum(enums_stat, "version_ids");
   vector<enum_t> regions = extract_enum(enums_stat, "region_ids");
   vector<enum_t> leagues = extract_enum(enums_stat, "league_ids");
   vector<enum_t> races = extract_enum(enums_stat, "race_ids");
   
   uint32_t index = 0;

   for (uint32_t mode_i = 0; mode_i < modes.size(); ++mode_i) {
      for (uint32_t version_i = 0; version_i < versions.size(); ++version_i) {
         for (uint32_t region_i = 0; region_i < regions.size(); ++region_i) {
            for (uint32_t league_i = 0; league_i < leagues.size(); ++league_i) {
               for (uint32_t race_i = 0; race_i < races.size(); ++race_i) {
                  rs_data_t data;
                  while (index < _team_ranks.size()
                         and _team_ranks[index].mode == modes[mode_i]
                         and _team_ranks[index].version == versions[version_i]
                         and _team_ranks[index].region == regions[region_i]
                         and _team_ranks[index].league == leagues[league_i]
                         and _team_ranks[index].race0 == races[race_i]) {
                     data.count += 1;
                     data.wins += _team_ranks[index].wins;
                     data.losses += _team_ranks[index].losses;
                     data.points += _team_ranks[index].points;
                     ++index;
                  }
                  datas.push_back(data);
               }
            }
         }
      }
   }
   
   stats.version = RANKING_STATS_VERSION_1;

   {
      db::transaction_block tb(_db);
      _db.update_or_create_ranking_stats(stats, id);
   }

   // Sort it back for more inserts.
   stable_sort(_team_ranks.begin(), _team_ranks.end(), compare_team_id_version_race);
}

boost::python::list ranking_data::min_max_data_time()
{
   boost::python::list res;
   if (not _team_ranks.size()) {
      res.append(0);
      res.append(0);
      return res;
   }
   
   double min_data_time = 1e32;
   double max_data_time = 0;
   for (auto& team_rank : _team_ranks) {
      min_data_time = min(team_rank.data_time, min_data_time);
      max_data_time = max(team_rank.data_time, max_data_time);
   }
   res.append(min_data_time);
   res.append(max_data_time);
   return res;
}

// Update old player with new player info, return true if anything was updated.
bool update_player(player_t& old_player, const player_t& new_player)
{
   bool updated = false;
   
   if (old_player.season_id <= new_player.season_id
       and (new_player.name != old_player.name
            or new_player.tag != old_player.tag
            or new_player.clan != old_player.clan)) {
      // Due to bug in battle net api names are sometimes not available, never update to an empty name.
      if (new_player.name.length()) {
         old_player.name = new_player.name;
         old_player.tag = new_player.tag;
         old_player.clan = new_player.clan;
         updated = true;
      }
   }

   if (old_player.season_id < new_player.season_id) {
      // Always update if new data is later season.
      old_player.season_id = new_player.season_id;
      old_player.race = new_player.race;
      old_player.league = new_player.league;
      old_player.mode = new_player.mode;
      updated = true;
   }
   else if (new_player.season_id < old_player.season_id) {
      // Never update if new data is previous season.
   }
   else if (old_player.mode == TEAM_1V1 or new_player.mode == TEAM_1V1) {
      // Handle 1v1 as a special case that will always be displayed if played.
      
      if (new_player.mode != TEAM_1V1) {
         // Never change from 1v1.
      }
      else if (old_player.mode != TEAM_1V1) {
         // Always update this.
         old_player.mode = new_player.mode;
         old_player.race = new_player.race;
         old_player.league = new_player.league;
         updated = true;
      }
      else if (old_player.league < new_player.league) {
         // Only update on better league, don't update on race since a player can have several races in same league.
         old_player.race = new_player.race;
         old_player.league = new_player.league;
         updated = true;
      }
   }
   else if (old_player.league < new_player.league) {
      // Display mode with best league.
      old_player.mode = new_player.mode;
      old_player.race = new_player.race;
      old_player.league = new_player.league;
      updated = true;
   }
   else if (old_player.mode == new_player.mode
            and (old_player.league != new_player.league or old_player.race != new_player.race)) {
      // If something changed within mode, update it (this may cause consecutive updates because another mode may now
      // have a better league, but the other option is to not update league canges within mode).
      old_player.race = new_player.race;
      old_player.league = new_player.league;
      updated = true;
   }

   return updated;
}

// Update old team with new team info, return true if anything was updated.
bool update_team(team_t& old_team, const team_t& new_team)
{
   bool updated = false;

   if (old_team.season_id < new_team.season_id) {
      // Always update if new data is later season.
      old_team.season_id = new_team.season_id;
      old_team.version = new_team.version;
      old_team.league = new_team.league;
      old_team.r0 = new_team.r0;
      old_team.r1 = new_team.r1;
      old_team.r2 = new_team.r2;
      old_team.r3 = new_team.r3;
      updated = true;
   }
   else if (old_team.season_id == new_team.season_id and old_team.version < new_team.version) {
      // Always update if later version.
      old_team.version = new_team.version;
      old_team.league = new_team.league;
      old_team.r0 = new_team.r0;
      old_team.r1 = new_team.r1;
      old_team.r2 = new_team.r2;
      old_team.r3 = new_team.r3;
      updated = true;
   }
   else if (old_team.season_id == new_team.season_id and old_team.version == new_team.version and
            new_team.mode == TEAM_1V1) {
      // Handle 1v1 separatly to avoid excessive updates form separate race mmr, only update if better league.
      if (old_team.league < new_team.league) {
         old_team.league = new_team.league;
         old_team.r0 = new_team.r0;
         updated = true;
      }      
   }
   else if (old_team.season_id == new_team.season_id and old_team.version == new_team.version and
            (old_team.league != new_team.league or old_team.r0 != new_team.r0 or old_team.r1 != new_team.r1
             or old_team.r2 != new_team.r2 or old_team.r3 != new_team.r3)) {
      // Update if something changed.
      old_team.league = new_team.league;
      old_team.r0 = new_team.r0;
      old_team.r1 = new_team.r1;
      old_team.r2 = new_team.r2;
      old_team.r3 = new_team.r3;
      updated = true;
   }

   return updated;
}

boost::python::dict
ranking_data::update_with_ladder(id_t ladder_id,
                                 id_t source_id,
                                 enum_t region,
                                 enum_t mode,
                                 enum_t league,
                                 enum_t tier,
                                 enum_t version,
                                 id_t season_id,
                                 double data_time,
                                 uint32_t team_size,
                                 boost::python::list members)
{
   boost::lock_guard<boost::mutex> lock(_team_ranks_mutex);

   uint32_t updated_player_count = 0;
   uint32_t inserted_player_count = 0;
   uint32_t updated_team_count = 0;
   uint32_t inserted_team_count = 0;

   // This comparator is used to find out what display race and league players and teams should have.
   cmp_tr cmp(NOT_REVERSED, NOT_SET, NOT_SET, NOT_SET, get_sort_key(season_id), STRICT);
   
   team_ranks_t ladder;
   {
      db::transaction_block transaction(_db);
   
      //
      // Get or create player ids.
      //

      players_t players;
      player_set_t unknown_players;
      for (uint32_t i = 0; i < len(members); ++i) {
         object member = members[i];
         player_t p;
         p.id = 0;
         p.region = region;
         p.bid = extract<bid_t>(member["bid"]);
         p.realm = extract<bid_t>(member["realm"]);
         p.name = extract<string>(member["name"]);
         p.tag = extract<string>(member["tag"]);
         p.clan = extract<string>(member["clan"]);
         p.season_id = season_id;
         p.mode = mode;
         p.league = league;
         p.race = extract<enum_t>(member["race"]);
         
         auto pc = _player_cache.find(p);
         if (pc == _player_cache.end()) {
            unknown_players.insert(p);
         }
         else {
            p.id = pc->id;
         }

         players.push_back(p);
      }

      // Get/insert players in db and make sure all ids are set.

      if (unknown_players.size()) {
         inserted_player_count = _db.get_or_insert_players(_player_cache, unknown_players);
      
         for (auto& p : players) {
            if (not p.id) {
               auto pc = _player_cache.find(p);
               p.id = pc->id;
            }
         }
      }
            
      //
      // Get or create team ids.
      //

      id_t member_ids[] = {0, 0, 0, 0};
      enum_t member_races[] = {-1, -1, -1, -1};
      teams_t teams;
      team_set_t unknown_teams;
      for (uint32_t i = 0; i < len(members); ++i) {
         
         member_ids[i % team_size] = players[i].id;
         member_races[i % team_size] = players[i].race;

         if (i % team_size == team_size - 1) {
            // Last member in the team, handle team.
            team_t team;
            team.id = 0;
            team.region = region;
            team.mode = mode;
            team.season_id = season_id;
            team.version = version;
            team.league = league;
            team.m0 = member_ids[0];
            team.m1 = member_ids[1];
            team.m2 = member_ids[2];
            team.m3 = member_ids[3];
            team.r0 = member_races[0];
            team.r1 = member_races[1];
            team.r2 = member_races[2];
            team.r3 = member_races[3];
            team.normalize(team_size);

            auto tc = _team_cache.find(team);
            if (tc == _team_cache.end()) {
               unknown_teams.insert(team);
            }
            else {
               team.id = tc->id;
            }
            teams.push_back(team);
         }
      }

      // Get/insert teams in db and make sure all ids are set.

      if (unknown_teams.size()) {
         inserted_team_count = _db.get_or_insert_teams(_team_cache, unknown_teams, team_size);

         for (auto& team : teams) {
            if (not team.id) {
               auto tc = _team_cache.find(team);
               team.id = tc->id;
            }
         }
      }
      
      //
      // Extract ladder from members, but skip duplicates when inserting in ladder.
      //
    
      uint32_t rank = 0;
      team_map_t team_map;
      player_map_t player_map;

      for (uint32_t i = 0; i < len(members); ++i) {

         player_map.insert(make_pair(players[i].id, players[i]));
         
         if (i % team_size == team_size - 1) {
            // Last member in the team, handle team.
            
            object member = members[i];
            auto& team = teams[i / team_size];

            if (not team_map.insert(make_pair(team.id, team)).second) {
               // No insert, skip duplicates for race mmr (first occurance will be the higher ranked).
               continue;
            }
            
            team_rank_t team_rank;
            team_rank.team_id = team.id;
            team_rank.region = region;
            team_rank.league = league;
            team_rank.tier = tier;
            team_rank.mode = mode;
            team_rank.version = version;
            team_rank.ladder_id = ladder_id;
            team_rank.source_id = source_id;
            team_rank.data_time = data_time;
            team_rank.mmr = extract<int16_t>(member["mmr"]);
            team_rank.points = extract<float>(member["points"]);
            team_rank.wins = extract<uint32_t>(member["wins"]);
            team_rank.losses = extract<uint32_t>(member["losses"]);
            team_rank.join_time = extract<uint32_t>(member["join_time"]);
            team_rank.race0 = team.r0;
            team_rank.race1 = team.r1;
            team_rank.race2 = team.r2;
            team_rank.race3 = team.r3;
            
            ladder.push_back(team_rank);
         }
      }

      //
      // Sort ladder and assign ranks.
      //
      
      stable_sort(ladder.begin(), ladder.end(), cmp);
      auto last_tr = ladder.end();
      rank = 1;
      uint32_t pos = 1;
      for (auto tr = ladder.begin(); tr != ladder.end(); ++tr, ++pos) {
         if (last_tr == ladder.end() or cmp(*last_tr, *tr) or cmp(*tr, *last_tr)) {
            rank = pos;
            last_tr = tr;
         }

         tr->ladder_rank = rank;
         tr->ladder_count = ladder.size();
         last_tr = tr;
      }
      
      //
      // Merge/replace/add team data. We should not need to check anything just rely on the later data is the correct
      // one.
      //

      {
         team_ranks_t new_team_ranks;
         stable_sort(ladder.begin(), ladder.end(), compare_team_id_version_race);

         auto source = ladder.begin();
         for (auto target = _team_ranks.begin(); target != _team_ranks.end() and source != ladder.end();) {

            if (compare_team_id_version(*source, *target)) {
               // We passed source's place in target, adding later.
               new_team_ranks.push_back(*source);
               ++source;
            }
            else if (not compare_team_id_version(*target, *source)) {
               // Equal, replace target with source. One mmr per race for 1v1 is handled here. Always replace if same
               // race. Otherwise only replace if better ladder position effectivly making a ladder using only the best
               // race for each team. If not using for update, mark the team by zeroing the id. Mode and version is
               // always the same for source and target here.
               if (season_id < 29
                   or mode != TEAM_1V1
                   or target->race0 == source->race0
                   or cmp(*source, *target)) {
                  *target = *source;
               }
               else {
                  source->team_id = 0;
               }
               ++target;
               ++source;
            }
            else {
               ++target;
            }
         }

         // Put teams on _team_ranks and sort it if needed.

         // Adding in order to the end.
         _team_ranks.insert(_team_ranks.end(), source, ladder.end());

         if (new_team_ranks.size()) {
            // Adding out of order teams.
            _team_ranks.insert(_team_ranks.end(), new_team_ranks.begin(), new_team_ranks.end());
            stable_sort(_team_ranks.begin(), _team_ranks.end(), compare_team_id_version_race);
         }
      }
      
      // Handle teams and players that should be updated in db. This will also make the caches up to date.

      player_set_t updated_players;
      team_set_t updated_teams;

      for (auto& tr : ladder) {
         if (tr.team_id) {
            auto& team = team_map[tr.team_id];
            team_t cached = *_team_cache.find(team);
            if (update_team(cached, team)) {
               _team_cache.erase(cached);
               _team_cache.insert(cached);
               updated_teams.insert(cached);
            }

            vector<id_t> player_ids;
            player_ids.push_back(team.m0);
            if (team.m1) player_ids.push_back(team.m1);
            if (team.m2) player_ids.push_back(team.m2);
            if (team.m3) player_ids.push_back(team.m3);
            
            for (auto id : player_ids) {
               auto& player = player_map[id];
               player_t cached = *_player_cache.find(player);
               if (update_player(cached, player)) {
                  _player_cache.erase(cached);
                  _player_cache.insert(cached);
                  updated_players.insert(cached);
               }
            }
         }
      }

       // Update players in the database.
       
       if (updated_players.size()) {
          updated_player_count = updated_players.size();
          _db.update_players(updated_players);
       }
       // Update teams in the database.
       
       if (updated_teams.size()) {
          updated_team_count = updated_teams.size();
          _db.update_teams(updated_teams);
       }
   }

   boost::python::dict stats;
   stats["updated_player_count"] = updated_player_count;
   stats["inserted_player_count"] = inserted_player_count;
   stats["updated_team_count"] = updated_team_count;
   stats["inserted_team_count"] = inserted_team_count;
   stats["player_cache_size"] = _player_cache.size();
   stats["team_cache_size"] = _team_cache.size();
   return stats;
}

