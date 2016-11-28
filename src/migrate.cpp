
#include <iostream>
#include <fstream>
#include <algorithm>
#include <time.h>

#include "exception.hpp"
#include "types.hpp"
#include "db.hpp"
#include "log.hpp"
#include "timer.hpp"
#include "get.hpp"

using namespace std;

int main()
{
   // Migrating from team_rank_v0 or v1 to team_rank_v2 by loading and resaving all rankings. Later rankings
   // from season >= 28 may want patched mmr, we will see, but for now they get patched mmr.

   return 0; // Don't do it, better to keep old versions.
   
   db db("sc2");

   std::set<uint32_t> team_ids;
   
   rankings_t rankings = db.get_available_rankings(0);

   team_ranks_t team_ranks;
   for (auto& ranking : rankings) {
      
      cerr << "ranking " << ranking.id << endl;
      
      db.load_team_ranks(ranking.id, team_ranks);
      
      cerr << "loaded ranking " << ranking.id << endl;
      
      db.save_team_ranks(ranking.id, float(now_us()) / 1e6, team_ranks);
      
      cerr << "saved ranking " << ranking.id << endl;
   }
   
   return 0;
}
