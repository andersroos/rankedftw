#pragma once

#include <libpq-fe.h>
#include <string>
#include <vector>
#include <set>
#include <array>

#include "types.hpp"


// Class to handle a database connection and doing custom sc2 stuff.
struct db
{
   struct transaction_block
   {
      transaction_block(db& db) : _db(db) { _db.start_transaction(); }
      virtual ~transaction_block() { _db.end_transaction(); }
   private:
      db& _db;
   };
   
   db(const std::string& db_name);

   // For each player in players get existing player of <region, realm, bid> or create one. Insert the player with id
   // into store. The players set is consumed.
   uint32_t get_or_insert_players(player_set_t& store, player_set_t& players);

   // Update players in players in database.
   void update_players(const player_set_t& players);

   // For each team in teams get existing team of <id0, id1, id2, id3, mode> or create one. Insert the team with id
   // into store. The teams set is consumed.
   uint32_t  get_or_insert_teams(team_set_t& store, team_set_t& teams, uint32_t team_size);

   // Update teams in teams in database.
   void update_teams(const team_set_t& teams);

   // Save team ranks and set updated time. NOTE Only use ranking.id, not ranking_data.id or ranking_stats.id.
   void save_team_ranks(id_t id, float now, team_ranks_t& team_ranks);
   
   // Get the complete list of available rankings (but without data). Use from_season to exclude seasons lower.
   rankings_t get_available_rankings(uint32_t from_season);

   // Get the lastest ranking (but without data).
   ranking_t get_latest_ranking();
   
   // Load an array of team ranks from ranking, index points to the start of the sequence to get, if index or any of the
   // team ranks is is out of range the team_id is set to 0 for that team rank. If used on non unpacked team_ranks the
   // behaviour is undefined. Set window_size to the requested number of team ranks to get. Returns number of team ranks
   // actually loaded.
   uint32_t load_team_rank_window(id_t ranking_id, uint16_t tr_version, uint32_t index,
                                  team_rank_window_t& trs, uint32_t window_size);

   // Load the team ranks header from the database, it will check the version and the magic number. NOTE Only use
   // ranking.id, not ranking_data.id or ranking_stats.id.
   void load_team_ranks_header(id_t ranking_id, team_ranks_header& trh);
   
   // Load team ranks saved in the unpacked format. NOTE Only use ranking.id, not ranking_data.id or ranking_stats.id.
   // Use data_time_low_limit (unix time in seconds) to only get entries with data_time >= data_time_low_limit_s.
   void load_team_ranks(id_t id, team_ranks_t& team_ranks, double data_time_low_limit_s=0);

   // Update or create ranking stats with id. NOTE Only use ranking.id, not ranking_data.id or ranking_stats.id.
   void update_or_create_ranking_stats(ranking_stats_t& ranking_stats, id_t id);

   // Load ranking_stats with ranking id.
   void load_ranking_stats(ranking_stats_t& ranking_stats, id_t ranking_id);
   
   // Load all ranking stats in data_time_order (oldest first).
   void load_all_ranking_stats(ranking_stats_list_t& ranking_stats_list, uint32_t filter_season);

   // Reconnect to the db.
   void reconnect();
   
   // Explicitly disconnect from the db.
   void disconnect();

   virtual ~db();

   //
   // Private methods, but we are all grown ups. :-)
   //
   
   // Excute one query and throw exception on any error, save res as state.
   void exec(const std::stringstream& sql);
   void exec(const std::string& sql);
   void exec(const std::string& sql,
             std::vector<char*> args,
             std::vector<int> arg_sizes,
             std::vector<int> arg_formats,
             int return_format=1);
   
   // Clear result, if not done it will be done automatically at next exec.
   void clear_res();
   
   // Get int from result.
   int32_t res_int(uint32_t row, uint32_t col);

   // Get float from result.
   float res_float(uint32_t row, uint32_t col);

   // Get double from result.
   double res_double(uint32_t row, uint32_t col);
   
   // Is null for field in result.
   bool res_isnull(uint32_t row, uint32_t col);

   // Get string from result.
   std::string res_str(uint32_t row, uint32_t col);

   // Get the size of the value.
   uint32_t res_value_size(uint32_t row, uint32_t col);

   // Get the value raw.
   char* res_value(uint32_t row, uint32_t col);
   
   // Get number of rows in result set.
   uint32_t res_size();

   // Return the number of rows affected by the last UPDATE, INSERT, DELETE, etc statement.
   int32_t affected_rows();

   // Use this method via transaction_block.
   void start_transaction();

   // Use this method via transaction_block.
   void end_transaction();

   // Helper for get_or_insert_players.
   void read_player_result(player_set_t& store, player_set_t& players);

   // Helper for get_or_insert_teams.
   void read_team_result(team_set_t& store, team_set_t& teams);
   
   std::string _db_name;
   PGconn* _conn;
   PGresult* _res;
};
