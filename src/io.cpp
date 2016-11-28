#include "types.hpp"
#include "exception.hpp"


#define WRITE( OS, FIELD ) ( OS ).write((char*) & FIELD , sizeof( FIELD ))

#define READ( IS, FIELD ) ( IS ).read((char*) & FIELD , sizeof( FIELD ))

std::ostream& operator<<(std::ostream& os, const team_rank_v2_t& tr)
{
   WRITE(os, tr.team_id);
   WRITE(os, tr.data_time);
   WRITE(os, tr.version);
   WRITE(os, tr.region);
   WRITE(os, tr.mode);
   WRITE(os, tr.league);
   WRITE(os, tr.tier);
   WRITE(os, tr.ladder_id);
   WRITE(os, tr.join_time);
   WRITE(os, tr.source_id);
   WRITE(os, tr.mmr);
   WRITE(os, tr.points);
   WRITE(os, tr.wins);
   WRITE(os, tr.losses);
   WRITE(os, tr.race0);
   WRITE(os, tr.race1);
   WRITE(os, tr.race2);
   WRITE(os, tr.race3);
   WRITE(os, tr.ladder_rank);
   WRITE(os, tr.ladder_count);
   WRITE(os, tr.league_rank);
   WRITE(os, tr.league_count);
   WRITE(os, tr.region_rank);
   WRITE(os, tr.region_count);  
   WRITE(os, tr.world_rank);
   WRITE(os, tr.world_count);  
   
   return os;
}

// Read team rank of any version into team rank of latest version.
void read_tr(std::istream& is, uint16_t version, team_rank_v2_t& tr)
{
   READ(is, tr.team_id);
   READ(is, tr.data_time);
   READ(is, tr.version);
   READ(is, tr.region);
   READ(is, tr.mode);
   READ(is, tr.league);
   READ(is, tr.tier);
   READ(is, tr.ladder_id);
   READ(is, tr.join_time);
   READ(is, tr.source_id);
   
   if (version >= 2)
      READ(is, tr.mmr);
   else
      tr.mmr = NO_MMR;
   
   READ(is, tr.points);
   READ(is, tr.wins);
   READ(is, tr.losses);
   READ(is, tr.race0);
   READ(is, tr.race1);
   READ(is, tr.race2);
   READ(is, tr.race3);
   READ(is, tr.ladder_rank);
   READ(is, tr.ladder_count);
   READ(is, tr.league_rank);
   READ(is, tr.league_count);
   READ(is, tr.region_rank);
   READ(is, tr.region_count);
   READ(is, tr.world_rank);
   READ(is, tr.world_count);
   if (version == 0) {
      uint32_t ignore;
      READ(is, ignore); // active_rank
      READ(is, ignore); // active_count
   }
}

std::ostream& operator<<(std::ostream& os, const team_ranks_header& trh)
{
   WRITE(os, trh.magic_number);
   WRITE(os, trh.version);
   WRITE(os, trh.count);
   
   return os;
}

std::istream& operator>>(std::istream& is, team_ranks_header& trh)
{
   READ(is, trh.magic_number);
   READ(is, trh.version);
   READ(is, trh.count);
   
   if (trh.magic_number != TEAM_RANK_MAGIC_NUMBER) {
      THROW(io_exception, fmt("Bad magic number, expected %X, was %X.", TEAM_RANK_MAGIC_NUMBER, trh.magic_number));
   }
   
   if (trh.version != TEAM_RANK_VERSION_1 and trh.version != TEAM_RANK_VERSION_2) {
      THROW(io_exception, fmt("Bad version, can not handle %d.", trh.version));
   }
   
   return is;
}

std::ostream& operator<<(std::ostream& os, const ranking_stats_t& ranking_stats)
{
   const rs_datas_t& datas = ranking_stats.datas;
   
   os << ranking_stats.version << ' ' << datas.size();
   
   for (uint32_t i = 0; i < datas.size(); ++i) {
      os << ' ' << datas[i].count << ' ' << datas[i].wins << ' '<< datas[i].losses << ' ' << datas[i].points;
   }
   return os;
}

std::istream& operator>>(std::istream& is, ranking_stats_t& ranking_stats)
{ 
   rs_datas_t& datas = ranking_stats.datas;
   datas.clear();
   
   is >> ranking_stats.version;

   if (ranking_stats.version != RANKING_STATS_VERSION_1) {
      THROW(io_exception, fmt("Can not handle ranking stats version %d.", ranking_stats.version));
   }

   uint32_t size;
   is >> size;

   for (uint32_t i = 0; i < size; ++i) {
      rs_data_t d;
      is >> d.count >> d.wins >> d.losses >> d.points;
      datas.push_back(d);
   }
   
   return is;
}

//
// For debugging.
//

std::string to_string(const team_rank_t& tr)
{
   std::stringstream ss;
   ss << "<team_rank"
      << " team_id: " << tr.team_id
      << " data_time: " << tr.data_time
      << " version: " << int(tr.version)
      << " region: " << int(tr.region)
      << " mode: " << int(tr.mode)
      << " league: " << int(tr.league)
      << " tier: " << int(tr.tier)
      << " ladder_id: " << tr.ladder_id
      << " join_time: " << tr.join_time
      << " source_id: " << tr.source_id
      << " mmr: " << tr.mmr
      << " points: " << tr.points
      << " wins: " << tr.wins
      << " losses: " << tr.losses
      << " race0: " << int(tr.race0)
      << " race1: " << int(tr.race1)
      << " race2: " << int(tr.race2)
      << " race3: " << int(tr.race3)
      << " ladder_rank: " << tr.ladder_rank
      << " ladder_count: " << tr.ladder_count
      << " league_rank: " << tr.league_rank
      << " league_count: " << tr.league_count
      << " region_rank: " << tr.region_rank
      << " region_count: " << tr.region_count
      << " world_rank: " << tr.world_rank
      << " world_count: " << tr.world_count
      << ">";
   return ss.str();
}

std::string to_string(const player_t& p)
{
   std::stringstream ss;
   ss << "<player"
      << " id: " << p.id
      << " bid: " << p.bid
      << " region: " << int(p.region)
      << " realm: " << int(p.realm)
      << " name: " << p.name
      << " tag: " << p.tag
      << " clan: " << p.clan
      << " season_id: " << int(p.season_id)
      << " race: " << int(p.race)
      << " league: " << int(p.league)
      << " mode: " << int(p.mode)
      << ">";
   return ss.str();
}

std::string to_string(const team_t& t)
{
   std::stringstream ss;
   ss << "<team"
      << " id: " << t.id
      << " region: " << int(t.region)
      << " mode: " << int(t.mode)
      << " season_id: " << int(t.season_id)
      << " version: " << int(t.version)
      << " league: " << int(t.league)
      << " m0: " << int(t.m0)
      << " m1: " << int(t.m1)
      << " m2: " << int(t.m2)
      << " m3: " << int(t.m3)
      << " r0: " << int(t.r0)
      << " r1: " << int(t.r1)
      << " r2: " << int(t.r2)
      << " r3: " << int(t.r3)
      << ">";
   return ss.str();
}

