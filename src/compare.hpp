#pragma once

#include "types.hpp"
#include "exception.hpp"

// x before y -> res -1
// x equal to y -> res 0
// x after y -> res 1
#define EQUAL 0
#define BEFORE -1
#define AFTER 1

// After quick fix LADDER_RANK == LEAGUE_POINTS here, but in url LADDER_RANK == MMR, this should be fixed after
// descision to keep league-tier-points as a sort order.
#define LADDER_RANK   0
#define PLAYED        1
#define WINS          2
#define LOSSES        3
#define WIN_RATE      4
#define MMR           5

#define REVERSED true
#define NOT_REVERSED false

#define STRICT true
#define NON_STRICT false

#define NOT_SET -64


int32_t inline cmp_league_tier_points(const team_rank_t& x, const team_rank_t& y) {

   if (x.league == y.league and x.tier == y.tier and x.points == y.points)
      return EQUAL;

   if (x.league > y.league
       or (x.league == y.league and x.tier < y.tier)
       or (x.league == y.league and x.tier == y.tier and x.points > y.points))
      return BEFORE;

   return AFTER;
}

//
// Class used to compare team ranks with same version and mode.
//
struct cmp_tr
{
   //
   // Create comparator with filter and sorting properties below.
   //
   // If strict is true the comparator will stick to the ordering and filtering strict. If strict is false it will use
   // additional values for comparison to make a more appealing sort order for displaying (like played is a secondary
   // sort to win sort order). For calculating ranks strict sorting is needed.
   //
   // Enum types (region, league and race) can be set to a value or NOT_SET. This setting is primary used to filter
   // team_ranks, see use method. If set to a value it will alwasy be used as primary sort order (in region, league,
   // race order). If set to NOT_SET it may or may not be used in sort, depending on the sort order key.
   //
   cmp_tr(bool reverse, enum_t region, enum_t league, enum_t race, enum_t key, bool strict=false) :
      _reverse(reverse), _region(region), _league(league), _race(race), _key(key), _strict(strict) {}

   cmp_tr() : _reverse(false), _region(NOT_SET), _league(NOT_SET), _race(NOT_SET),
              _key(LADDER_RANK), _strict(false) {}
   
   // Is x < y? (x before y)
   bool operator()(const team_rank_t& x, const team_rank_t& y) const {

      if (_region != NOT_SET and x.region != y.region) {
         return x.region < y.region;
      }

      if (_league != NOT_SET and x.league != y.league) {
         return x.league > y.league;
      }

      if (_race != NOT_SET and x.race0 != y.race0) {
         return x.race0 < y.race0;
      }

      int32_t x_played = x.wins + x.losses;
      int32_t y_played = y.wins + y.losses;
      int32_t res;
         
      switch (_key) {

         case MMR:
            if (x.mmr == y.mmr) 
               res = EQUAL;
            else if (x.mmr > y.mmr)
               res = BEFORE;
            else
               res = AFTER;
            
            if (res != EQUAL)
               return _reverse != (res == BEFORE);

            if (_strict)
               return false;
            return _reverse != (x.wins > y.wins
                                or (x.wins == y.wins and x.losses < y.losses)
                                or (x.wins == y.wins and x.losses == y.losses and x.team_id < y.team_id));
            
         case LADDER_RANK:
            res = cmp_league_tier_points(x, y);
            if (res != EQUAL)
               return _reverse != (res == BEFORE);
            if (_strict)
               return false;
            if (x.wins == y.wins and x.losses == y.losses and x.team_id == y.team_id)
               return false;
            return _reverse != (x.wins > y.wins
                                or (x.wins == y.wins and x.losses < y.losses)
                                or (x.wins == y.wins and x.losses == y.losses and x.team_id < y.team_id));
            
         case PLAYED:
            if (x_played == y_played)
               res = 0;
            else if (x_played > y_played)
               res = -1;
            else
               res = 1;
            if (res != EQUAL)
               return _reverse != (res == BEFORE);
            if (_strict)
               return false;
            if (x.mmr == y.mmr and x.wins == y.wins and x.team_id == y.team_id)
               return false;
            return _reverse != (x.mmr > y.mmr
                                or (x.mmr == y.mmr and x.wins > y.wins)
                                or (x.mmr == y.mmr and x.wins == y.wins and x.team_id < y.team_id));
            
         case WINS:
            if (x.wins == y.wins)
               res = 0;
            else if (x.wins > y.wins)
               res = -1;
            else
               res = 1;
            if (res != EQUAL)
               return _reverse != (res == BEFORE);
            if (_strict)
               return false;
            if (x.mmr == y.mmr and x.losses == y.losses and x.team_id == y.team_id)
               return false;
            return _reverse != (x.mmr > y.mmr
                                or (x.mmr == y.mmr and x.losses < y.losses)
                                or (x.mmr == y.mmr and x.losses == y.losses and x.team_id < y.team_id));

         case LOSSES:
            if (x.losses == y.losses)
               res = 0;
            else if (x.losses > y.losses)
               res = -1;
            else
               res = 1;
            if (res != EQUAL)
               return _reverse != (res == BEFORE);
            if (_strict)
               return false;
            if (x.wins == y.wins and x.team_id == y.team_id)
               return false;
            return _reverse != (x.wins < y.wins
                                or (x.wins == y.wins and x.team_id < y.team_id));
            
         case WIN_RATE:
            {
               double x_rate = double(x.wins) / (x.wins + x.losses);
               double y_rate = double(y.wins) / (y.wins + y.losses);

               if (x_rate == y_rate)
                  res = 0;
               else if (x_rate > y_rate)
                  res = -1;
               else
                  res = 1;
                  
               if (res != EQUAL)
                  return _reverse != (res == BEFORE);
               if (_strict)
                  return false;
               if (x_played == y_played and x.mmr == y.mmr and x.team_id == y.team_id)
                  return false;
               return _reverse != (x.wins > y.wins
                                   or (x.wins == y.wins and x.losses < y.losses)
                                   or (x.wins == y.wins and x.losses == y.losses and x.mmr > y.mmr)
                                   or (x.wins == y.wins and x.losses == y.losses and x.mmr == y.mmr and
                                       x.team_id < y.team_id));
             }
         default:
            THROW(bug_exception, fmt("Can't sort with key %d.", _key));
      }
   }

   // Return true if this team rank mathces enum values not set as NOT_SET (in practice returns true if it is a good
   // idea to compare it with this comparator).
   bool use(const team_rank_t& x) const {

      // This is a hack to make NO_MMR not appear in ladder, remove when blizzard bug is fixed.
      if (_key == MMR and x.mmr == NO_MMR) {
         return false;
      }
      
      if (_region != NOT_SET and x.region != _region) {
         return false;
      }

      if (_league != NOT_SET and x.league != _league) {
         return false;
      }

      if (_race != NOT_SET and x.race0 != _race) {
         return false;
      }

      return true;
   }

   bool   _reverse;
   enum_t _region;
   enum_t _league;
   enum_t _race;
   enum_t _key;
   bool   _strict;
};

//
// Compare team ranks version and mode, used in combination with cmp_tr to make a full sort.
//
struct cmp_tr_version_mode
{
   // Make a comparator that can be used to sort all team ranks gloablly. Will use cmp_tr instance to sort team_ranks
   // with same version and mode.
   cmp_tr_version_mode(cmp_tr cmp) : _cmp(cmp) {}

   // Is x < y? (x before y)
   bool operator()(const team_rank_t& x, const team_rank_t& y) const {
      if (x.version < y.version
          or (x.version == y.version and x.mode < y.mode))
         return true;

      if  (x.version == y.version and x.mode == y.mode) {
         return _cmp(x, y);
      }

      return false;
   }

   cmp_tr _cmp;
};

//
// This will restore the original ranking order after loading from database.
//
inline bool compare_version_mode_world_rank(const team_rank_t& x, const team_rank_t& y)
{
   return (x.version < y.version
           or (x.version == y.version and x.mode < y.mode)
           or (x.version == y.version and x.mode == y.mode and x.world_rank < y.world_rank));
}

//
// Comparator for team version order that is used before storing in the db or team history won't work.
//
inline bool compare_team_id_version(const team_rank_t& x, const team_rank_t& y)
{
   return (x.team_id < y.team_id
           or (x.team_id == y.team_id and x.version < y.version));
}

//
// This is used before summarizing stats version 1.
//
inline bool compare_for_ranking_stats_v1(const team_rank_t& x, const team_rank_t& y)
{
   return (x.mode < y.mode
           or (x.mode == y.mode and x.version < y.version)
           or (x.mode == y.mode and x.version == y.version and x.region < y.region)
           or (x.mode == y.mode and x.version == y.version and x.region == y.region and x.league < y.league)
           or (x.mode == y.mode and x.version == y.version and x.region == y.region and x.league == y.league
               and x.race0 < y.race0)
      );
}

