
#include <iostream>
#include <fstream>
#include <algorithm>
#include <time.h>

#include "exception.hpp"
#include "types.hpp"
#include "db.hpp"
#include "util.hpp"
#include "log.hpp"
#include "timer.hpp"
#include "get.hpp"
#include "io.hpp"
#include "compare.hpp"

using namespace std;

void write_read_team_rank_header()
{
   {
      cerr << "writing team rank header to /tmp/trh" << endl;
      team_ranks_header trh(123);
      std::ofstream ofs("/tmp/trh");
      ofs << trh;
   }

   {
      cerr << "reading team rank header from /tmp/trh" << endl;
      team_ranks_header trh;
      std::ifstream ifs("/tmp/trh");
      ifs >> trh;
      cerr << "read count: " << trh.count << endl;
   }
}

void print_teams_that_played_both_versions() {
   db db(DEFAULT_DB);

   // vector<uint32_t> ids({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 24, 31, 39, 47,
   //                       54, 62, 69, 77, 80, 88, 96, 103, 191, 192, 199, 207, 214, 221, 228, 235,
   //                       242, 249, 256, 261, 270, 271, 279, 285, 286, 287, 288, 289, 290, 291});

   vector<uint32_t> ids({291});
   
   team_ranks_t team_ranks;

   for (uint32_t j = 0; j < ids.size(); j++) {
   
      db.load_team_ranks(ids[j], team_ranks);
      
      map<uint32_t, uint32_t> counts;
      
      for (uint32_t i = 0; i < team_ranks.size(); ++i) {
         counts[team_ranks[i].team_id]++;
      }
      
      uint32_t count = 0;
      for (map<uint32_t, uint32_t>::iterator i = counts.begin(); i != counts.end(); ++i) {
         if (i->second > 1) {
            count++;
         }
      }

      for (uint32_t i = 0; i < team_ranks.size(); ++i) {
         if (counts[team_ranks[i].team_id] > 1 && team_ranks[i].mode == 11) {
            cerr << to_string(team_ranks[i]) << endl;
         }
      }
            
      cerr << ids[j] << ": " << count << "/" << team_ranks.size() << "  "
           << (float(count) / team_ranks.size() * 100) << " %" << endl;
   }
}

void find_teams_without_rankings_fast() {
   db db(DEFAULT_DB);

   std::set<uint32_t> team_ids;
   
   rankings_t rankings = db.get_available_rankings(0);

   cerr << "loading all team ranks" << endl;

   team_ranks_t team_ranks;
   for (uint32_t i = 0; i < rankings.size(); ++i) {
      db.load_team_ranks(rankings[i].id, team_ranks);
      cerr << "loaded rankings " << rankings[i].id << endl;
      for (uint32_t j = 0; j < team_ranks.size(); ++j) {
         team_ids.insert(team_ranks[j].team_id);
         if (team_ranks[j].source_id == 0) {
            cerr << " team " << team_ranks[j].team_id
                 << " from ranking " << rankings[i].id
                 << " has source_id 0" << endl;
         }
      }
   }
   
   db.exec("SELECT max(id) FROM team");
   uint32_t max_id = db.res_int(0, 0);
   db.clear_res();

   cerr << "checking all teams from 1 to " << max_id << endl;
   
   for (uint32_t team_id = 1; team_id <= max_id; ++team_id) {
      db.exec(fmt("SELECT id, mode, member0_id, member1_id, member2_id, member3_id FROM team WHERE id = %d", team_id));
      uint32_t size = db.res_size();
      if (size == 0) {
         cerr << " skipping " << team_id << " non existing team" << endl;
      }
      else {
         if (team_ids.find(team_id) != team_ids.end()) {
            cerr << " found " << team_id << endl;
         }
         else {
            cout << team_id
                 << " mode " << db.res_value(0, 1)
                 << " m0 " << db.res_value(0, 2)
                 << " m1 " << db.res_value(0, 3)
                 << " m2 " << db.res_value(0, 4)
                 << " m3 " << db.res_value(0, 5)
                 << endl;
         }
      }
   }
}

void print_all_team_ids_in_ranking() {
   db db(DEFAULT_DB);

   team_ranks_t team_ranks;
   
   db.load_team_ranks(334, team_ranks);

   for (uint32_t i = 0; i < team_ranks.size(); ++i) {
      cout << team_ranks[i].team_id << endl;
   }
}   

void sort_one_ranking() {
   db db(DEFAULT_DB);

   team_ranks_t team_ranks;

   //db.load_team_ranks(191, team_ranks);
   db.load_team_ranks(425, team_ranks);

   for (int i = 0; i < 20; ++i) {
      {
         timer_us timer;
         stable_sort(team_ranks.begin(), team_ranks.end(), compare_version_mode_world_rank);
         cerr << "compare_version_mode_world_rank " << (double(timer.end()) / 1e6) << endl;
      }
      
      {
         timer_us timer;
         stable_sort(team_ranks.begin(), team_ranks.end(), compare_team_id_version);
         cerr << "compare_team_id_version         " << (double(timer.end()) / 1e6) << endl;
      }
   }
   
}

void print_all_ranks_for_one_team() {
   db db(DEFAULT_DB);

   uint32_t team_id = 878892;
   team_ranks_t all_ranks;
      
   rankings_t rankings = db.get_available_rankings(0);

   cerr << "loading all team ranks to find all ranks for team " << team_id << endl;

   team_ranks_t team_ranks;
   for (uint32_t j = 0; j < rankings.size(); ++j) {
      db.load_team_ranks(rankings[j].id, team_ranks);

      for (uint32_t i = 0; i < team_ranks.size(); ++i) {
         if (team_ranks[i].team_id == team_id) {
            team_ranks[i].losses = rankings[j].id;
            all_ranks.push_back(team_ranks[i]);
         }
      }
   }

   cerr << endl << "all rankings for team " << team_id << endl;
   for (uint32_t i = 0; i < all_ranks.size(); ++i) {
      team_rank_t& tr = all_ranks[i];
      cerr << fmt("id=%u, ranking_id=%u, version=%u, league=%u, mode=%u, region=%u, source_id=%u, ladder_id=%u\n",
                  tr.team_id, tr.losses, tr.version, tr.league, tr.mode, tr.region, tr.source_id, tr.ladder_id);
   }
}

typedef pair<uint32_t, uint32_t> team_id_version_t;
void find_duplicate_rankings()
{
   db db(DEFAULT_DB);

   std::set<uint32_t> team_ids;
   
   rankings_t rankings = db.get_available_rankings(0);

   team_ranks_t team_ranks;
   for (auto& ranking : rankings) {
      if (ranking.season_id < 24) continue;         
      db.load_team_ranks(ranking.id, team_ranks);
      cerr << "loaded rankings " << ranking.id << endl;

      set<team_id_version_t> seen;
      
      for (auto& tr : team_ranks) {
         team_id_version_t tv(tr.version, tr.team_id);
         if (seen.find(tv) != seen.end()) {
            cerr << "ranking " << ranking.id << " dup " << uint32_t(tr.version) << " " << tr.team_id << endl;
         }
         seen.insert(tv);
      }
   }
}

void dump_ranking(uint32_t id)
{
   db db(DEFAULT_DB);

   team_ranks_header trh;

   db.load_team_ranks_header(id, trh);
   cout << "version " << trh.version << endl;
   cout << "count " << trh.count << endl;
   cout << "magic " << trh.magic_number << endl;
   
   team_ranks_t team_ranks;
   db.load_team_ranks(id, team_ranks);
   for (uint32_t i = 0; i < team_ranks.size(); ++i) {
      auto& tr = team_ranks[i];
      cout << "==== TEAM RANK " << i << " ====" << endl;
      cout << to_string(tr) << endl;
   }
}

void count_no_mmr()
{
   db db(DEFAULT_DB);
   rankings_t rankings = db.get_available_rankings(27);

   team_ranks_header trh;

   for (auto ranking : rankings) {
      team_ranks_t team_ranks;
      db.load_team_ranks(ranking.id, team_ranks);
      uint32_t count = 0;
      for (uint32_t i = 0; i < team_ranks.size(); ++i) {
         if (team_ranks[i].mmr == NO_MMR) {
            ++count;
         };
      }
      cerr << "ranking " << ranking.id << " " << count << "/" << team_ranks.size() << endl;
   }
}

void dump_multi_race_teams()
{
   db db(DEFAULT_DB);
   
   team_ranks_t team_ranks;
   db.load_team_ranks(1076, team_ranks);

   set<pair<id_t, enum_t> > have_rank;
   for (auto& tr : team_ranks) {
      if (tr.mode == TEAM_1V1) {
         auto team_id_version = make_pair(tr.team_id, tr.version);
         if (have_rank.find(team_id_version) == have_rank.end()) {
            have_rank.insert(team_id_version);
         }
         else {
            cout << tr.team_id << endl;
         }
      }
   }
}

int main()
{
   dump_multi_race_teams();
   
   return 0;
}
