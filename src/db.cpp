#include <sys/time.h>
#include <stdlib.h>
#include <libpq-fe.h>

#include <boost/iostreams/device/file.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filtering_stream.hpp>   
#include <boost/interprocess/interprocess_fwd.hpp>
#include <boost/lexical_cast.hpp>

#include "db.hpp"
#include "log.hpp"
#include "exception.hpp"
#include "util.hpp"
#include "timer.hpp"
#include "io.hpp"

using namespace std;

//
// Postgresql string escaper, RAII style.
//
struct pg_escape
{
   pg_escape(PGconn* conn, const string& unescaped)
   {
      _str = PQescapeLiteral(conn, unescaped.c_str(), unescaped.size());
      c = _str;
   }

   char* str() const
   {
      return _str;
   }

   operator const char* () const {
      return _str;
   }
   
   virtual ~pg_escape()
   {
      PQfreemem(_str);
   }

   const char* c;
private:
   friend ostream& operator<<(ostream &os, const pg_escape& e);
   char* _str;
};
ostream & operator<<(ostream &os, const pg_escape& e) { return os << e.str(); }

//
// NULL if 0.
//
struct null_if_0
{
   null_if_0(int32_t value)
   {
      if (value == 0) {
         _val = "NULL";
         _equal_val = " is NULL";
      }
      else {
         _val = boost::lexical_cast<string>(value);
         _equal_val = string(" =") + _val;
      }
      c = _val.c_str();
      e = _equal_val.c_str();
   }

   const char* c;
   const char* e;
private:
   string _val;
   string _equal_val;
};

//
// Implementation of db class.
// 

db::db(const string& db_name) : _conn(NULL), _res(NULL)
{
   _db_name = string("dbname = ") + db_name;
   _conn = PQconnectdb(_db_name.c_str());

   if (PQstatus(_conn) != CONNECTION_OK) {
      THROW(base_exception, fmt("failed to connect to database %s, %s", db_name.c_str(), PQerrorMessage(_conn)));
   }
}

void
db::exec(const stringstream& sql)
{
   exec(sql.str());
}
   
void
db::exec(const string& sql)
{
   clear_res();
   _res = PQexec(_conn, sql.c_str());
   
   ExecStatusType status = PQresultStatus(_res);
   if (status != PGRES_COMMAND_OK and status != PGRES_TUPLES_OK) {
      THROW(db_exception, fmt("db statement '%s' failed, status '%s', message '%s'",
                              sql.c_str(), PQresStatus(status), PQresultErrorMessage(_res)));
   }
}

void
db::exec(const std::string& sql,
         std::vector<char*> args,
         std::vector<int> arg_sizes,
         std::vector<int> arg_formats,
         int return_format)
{
   clear_res();
   _res = PQexecParams(_conn,
                       sql.c_str(),
                       args.size(),
                       NULL, // Types of parameters, unused as casts will define types.
                       args.data(),
                       arg_sizes.data(),
                       arg_formats.data(),
                       1); // Binary.

   ExecStatusType status = PQresultStatus(_res);
   if (status != PGRES_COMMAND_OK and status != PGRES_TUPLES_OK) {
      THROW(db_exception, fmt("db statement '%s' failed, status '%s', message '%s'",
                              sql.c_str(), PQresStatus(status), PQresultErrorMessage(_res)));
   }
}

void
db::clear_res()
{
   if (_res != NULL) {
      PQclear(_res);
      _res = NULL;
   }
}    

uint32_t
db::res_size()
{
   return PQntuples(_res);
}

int32_t
db::res_int(uint32_t row, uint32_t col)
{
   return atoi(PQgetvalue(_res, row, col));
}

float
db::res_float(uint32_t row, uint32_t col)
{
   return atof(PQgetvalue(_res, row, col));
}

double
db::res_double(uint32_t row, uint32_t col)
{
   return strtod(PQgetvalue(_res, row, col), NULL);
}

string
db::res_str(uint32_t row, uint32_t col)
{
   return string(PQgetvalue(_res, row, col));
}

bool
db::res_isnull(uint32_t row, uint32_t col)
{
   return PQgetisnull(_res, row, col);
}

char*
db::res_value(uint32_t row, uint32_t col)
{
   return PQgetvalue(_res, row, col);
}

uint32_t
db::res_value_size(uint32_t row, uint32_t col)
{
   return PQgetlength(_res, row, col);
}

int32_t
db::affected_rows()
{
   return atoi(PQcmdTuples(_res));
}

void
db::start_transaction()
{
   exec("BEGIN;");
}

void
db::end_transaction()
{
   exec("COMMIT;");
}

void
db::read_player_result(player_set_t& store, player_set_t& players)
{
   for (uint32_t i = 0; i < res_size(); ++i) {
      player_t p;
      p.id =        res_int(i,  0);
      p.region =    res_int(i,  1);
      p.bid =       res_int(i,  2);
      p.realm =     res_int(i,  3);
      p.name =      res_str(i,  4);
      p.tag =       res_str(i,  5);
      p.clan =      res_str(i,  6);
      p.season_id = res_int(i,  7);
      p.race =      res_int(i,  8);
      p.league =    res_int(i,  9);
      p.mode =      res_int(i, 10);
      p.last_seen = res_str(i, 11);
      store.insert(p);
      players.erase(p);
   }
} 

uint32_t
db::get_or_insert_players(player_set_t& store, player_set_t& players)
{
   uint32_t count = 0;
   
   // Get current players.

   if (players.size()) {
      stringstream sql;
      sql << "SELECT id, region, bid, realm, name, tag, clan, season_id, race, league, mode, last_seen"
          << " FROM player WHERE (region, bid, realm) IN (VALUES ";
      char delimiter = ' ';
      for (auto& p : players) {
         sql << delimiter << "(" << int(p.region) << "," << p.bid << "," << int(p.realm) << ")";
         delimiter = ',';
      }
      sql << ");";
      exec(sql);

      read_player_result(store, players);
   }

   // Insert what is left.

   if (players.size()) {
      stringstream sql;
      sql << "INSERT INTO player (region, bid, realm, name, tag, clan, "
          << "season_id, mode, league, race, last_seen) VALUES ";
      char delimiter = ' ';
      for (auto& p : players) {
         pg_escape e_name(_conn, p.name);
         pg_escape e_tag(_conn, p.tag);
         pg_escape e_clan(_conn, p.clan);
         pg_escape e_last_seen(_conn, p.last_seen);
         sql << delimiter << "(" << int(p.region) << "," << p.bid << ","
             << int(p.realm) << "," << e_name << "," << e_tag << "," << e_clan << ","
             << p.season_id << "," << int(p.mode) << "," << int(p.league) << "," << int(p.race)
             << "," << e_last_seen << ")";
         delimiter = ',';
      }
      sql << " RETURNING id, region, bid, realm, name, tag, clan, season_id, race, league, mode, last_seen;";
      exec(sql);

      count = players.size();
      
      read_player_result(store, players);
   }
   return count;
}

void
db::update_players(const player_set_t& players)
{
   // Create temp table.
   exec("CREATE TEMP TABLE updated_player (LIKE player) ON COMMIT DROP;");

   // Insert data.
   stringstream sql;
   sql << "INSERT INTO updated_player (id, region, bid, realm, name, tag, clan, "
       << "season_id, mode, league, race, last_seen) VALUES ";
   char delimiter = ' ';
   for (auto& p : players) {
      pg_escape e_name(_conn, p.name);
      pg_escape e_tag(_conn, p.tag);
      pg_escape e_clan(_conn, p.clan);
      pg_escape e_last_seen(_conn, p.last_seen);
      sql << delimiter << "(" << p.id << "," << int(p.region) << "," << p.bid << ","
          << int(p.realm) << "," << e_name << "," << e_tag << "," << e_clan << ","
          << p.season_id << "," << int(p.mode) << "," << int(p.league) << "," << int(p.race)
          << "," << e_last_seen << ")";
      delimiter = ',';
   }
   sql << ";";
   exec(sql);

   // Update from temp table.
   exec("UPDATE player t"
        " SET"
        "   name = s.name,"
        "   tag = s.tag,"
        "   clan = s.clan,"
        "   race = s.race,"
        "   league = s.league,"
        "   mode = s.mode,"
        "   season_id = s.season_id,"
        "   last_seen = s.last_seen"
        " FROM updated_player s"
        " WHERE"
        " t.id = s.id"
        " ;");
}

void
db::read_team_result(team_set_t& store, team_set_t& teams)
{
   for (uint32_t i = 0; i < res_size(); ++i) {
      team_t t;
      t.id =        res_int(i, 0);
      t.region =    res_int(i, 1);
      t.mode =      res_int(i, 2);
      t.season_id = res_int(i, 3);
      t.version =   res_int(i, 4);
      t.league =    res_int(i, 5);
      t.m0 =        res_isnull(i, 6) ? 0 : res_int(i, 6);
      t.m1 =        res_isnull(i, 7) ? 0 : res_int(i, 7);
      t.m2 =        res_isnull(i, 8) ? 0 : res_int(i, 8);
      t.m3 =        res_isnull(i, 9) ? 0 : res_int(i, 9);
      t.r0 =        res_int(i, 10);
      t.r1 =        res_int(i, 11);
      t.r2 =        res_int(i, 12);
      t.r3 =        res_int(i, 13);
      t.last_seen = res_str(i, 14);
      store.insert(t);
      teams.erase(t);
   }
} 

uint32_t
db::get_or_insert_teams(team_set_t& store, team_set_t& teams, uint32_t team_size)
{
   uint32_t count = 0;
   
   // Get current teams.

   if (teams.size()) {

      const char* values = "";
      switch (team_size) {
         case 1: values = "mode, member0_id";                                     break;
         case 2: values = "mode, member0_id, member1_id";                         break;
         case 3: values = "mode, member0_id, member1_id, member2_id";             break;
         case 4: values = "mode, member0_id, member1_id, member2_id, member3_id"; break;
      }
      
      stringstream sql;
      sql << "SELECT id, region, mode, season_id, version, league"
          << "  , member0_id, member1_id, member2_id, member3_id, race0, race1, race2, race3, last_seen"
          << " FROM team WHERE (" << values << ") IN (VALUES ";
      char delimiter = ' ';
      for (auto& t : teams) {
         null_if_0 m0(t.m0);
         null_if_0 m1(t.m1);
         null_if_0 m2(t.m2);
         null_if_0 m3(t.m3);
         sql << delimiter << "(" << int(t.mode) << "," ;
         switch (team_size) {
            case 1: sql << m0.c;                                              break;
            case 2: sql << m0.c << "," << m1.c;                               break;
            case 3: sql << m0.c << "," << m1.c << "," << m2.c;                break;
            case 4: sql << m0.c << "," << m1.c << "," << m2.c << "," << m3.c; break;
         }
         sql << ")";
         delimiter = ',';
      }
      sql << ");";
      exec(sql);

      read_team_result(store, teams);
   }

   // Insert what is left.

   if (teams.size()) {
      stringstream sql;
      sql << "INSERT INTO team (region, mode,season_id, version, league"
          << " , member0_id, member1_id, member2_id, member3_id, race0, race1, race2, race3, last_seen) VALUES ";
      char delimiter = ' ';
      for (auto& t : teams) {
         null_if_0 m0(t.m0);
         null_if_0 m1(t.m1);
         null_if_0 m2(t.m2);
         null_if_0 m3(t.m3);

         pg_escape e_last_seen(_conn, t.last_seen);

         sql << delimiter << "(" << int(t.region) << "," << int(t.mode)
             << "," << t.season_id << "," << int(t.version) << "," << int(t.league)
             << "," << m0.c << "," << m1.c << "," << m2.c << "," << m3.c
             << "," << int(t.r0) << "," << int(t.r1) << "," << int(t.r2) << "," << int(t.r3)
             << "," << e_last_seen << ")";
         delimiter = ',';
      }
      sql << " RETURNING id, region, mode, season_id, version, league"
          << "  , member0_id, member1_id, member2_id, member3_id, race0, race1, race2, race3, last_seen;";
      exec(sql);

      count = teams.size();
      
      read_team_result(store, teams);
   }

   return count;
}

void
db::update_teams(const team_set_t& teams)
{
   // Create temp table.
   exec("CREATE TEMP TABLE updated_team (LIKE team) ON COMMIT DROP;");

   // Insert data.
   stringstream sql;
   sql << "INSERT INTO updated_team (id, region, mode,season_id, version, league"
       << " , member0_id, member1_id, member2_id, member3_id, race0, race1, race2, race3, last_seen) VALUES ";
   char delimiter = ' ';
   for (auto& t : teams) {
      null_if_0 m0(t.m0);
      null_if_0 m1(t.m1);
      null_if_0 m2(t.m2);
      null_if_0 m3(t.m3);

      pg_escape e_last_seen(_conn, t.last_seen);

      sql << delimiter << "(" << t.id << "," << int(t.region) << "," << int(t.mode)
          << "," << t.season_id << "," << int(t.version) << "," << int(t.league)
          << "," << m0.c << "," << m1.c << "," << m2.c << "," << m3.c
          << "," << int(t.r0) << "," << int(t.r1) << "," << int(t.r2) << "," << int(t.r3)
          << "," << e_last_seen << ")";
      delimiter = ',';
   }
   exec(sql);

   // Update from temp table.
   exec("UPDATE team t"
        " SET"
           "   race0 = s.race0"
           "  ,race1 = s.race1"
           "  ,race2 = s.race2"
           "  ,race3 = s.race3"
           "  ,season_id = s.season_id"
           "  ,version = s.version"
           "  ,league = s.league"
           "  ,last_seen = s.last_seen"
        " FROM updated_team s"
        " WHERE"
        " t.id = s.id"
        " ;");
}

rankings_t
db::get_available_rankings(uint32_t from_season)
{
   // Ranking.COMPLETE_WITH_DATA and Ranking.COMPLETE_WITOUT_DATA used here.
   exec(fmt("SELECT r.id, s.id, s.version, EXTRACT(epoch FROM r.data_time), EXTRACT(epoch FROM rd.updated)"
            " FROM ranking_data rd"
            " JOIN ranking r ON rd.ranking_id = r.id"
            " JOIN season s ON s.id = r.season_id"
            " WHERE r.status IN (1, 2) AND r.season_id >= %d ORDER BY r.data_time", from_season));
   rankings_t res;
   for (uint32_t i = 0; i < res_size(); ++i) {
      ranking_t r(res_int(i, 0), res_int(i, 1), res_int(i, 2), res_float(i, 3), res_float(i, 4));
      res.push_back(r);
   }
   return res;
}

ranking_t
db::get_latest_ranking()
{
   // Ranking.COMPLETE_WITH_DATA and Ranking.COMPLETE_WITOUT_DATA used here.
   exec("SELECT r.id, s.id, s.version, EXTRACT(epoch FROM r.data_time), EXTRACT(epoch FROM rd.updated)"
        " FROM ranking_data rd"
        " JOIN ranking r ON rd.ranking_id = r.id"
        " JOIN season s ON s.id = r.season_id"
        " WHERE r.status IN (1, 2) ORDER BY r.data_time DESC LIMIT 1");
   ranking_t res(res_int(0, 0), res_int(0, 1), res_int(0, 2), res_float(0, 3), res_float(0, 4));
   return res;
}

uint32_t
db::load_team_rank_window(id_t ranking_id, uint16_t tr_version, uint32_t index,
                          team_rank_window_t& trs, uint32_t window_size)
{
   uint32_t tr_size;
   if (tr_version == 2) 
      tr_size = TEAM_RANK_V2_SIZE;
   else if (tr_version == 1)
      tr_size = TEAM_RANK_V1_SIZE;
   else
      THROW(db_exception, fmt("Unsupported team rank version %d.", tr_version));

   if (trs.size() < window_size) {
      THROW(db_exception, fmt("Window size %d does not fit array %s when getting from ranking %d.",
                              window_size, trs.size(), ranking_id));
   }
   
   exec(fmt("SELECT substring(data from %u for %u) FROM ranking_data WHERE ranking_id = %d;",
            TEAM_RANKS_HEADER_SIZE + tr_size * index + 1, tr_size * window_size, ranking_id),
        {}, {}, {});

   for (auto& tr : trs) tr.team_id = 0;
   
   size_t size = res_value_size(0, 0);
   if (size == 0) {
      return 0;
   }

   string s(res_value(0, 0), size);
   stringstream ss(s);

   uint32_t i = 0;
   for (; i < window_size and (i + 1) * tr_size <= size; ++i) {
      read_tr(ss, tr_version, trs[i]);
   }
   return i;
}

void
db::load_team_ranks_header(id_t ranking_id, team_ranks_header& trh)
{
   exec(fmt("SELECT substring(data from 1 for 12) FROM ranking_data WHERE ranking_id = %d;", ranking_id),
        {}, {}, {});
   
   if (res_value_size(0, 0) == 0) {
      THROW(db_exception, fmt("Got size 0 from ranking %d.", ranking_id));
   }

   string s(res_value(0, 0), res_value_size(0, 0));
   stringstream ss(s);
   try {
      ss >> trh;
   }
   catch (io_exception &e) {
      THROW(db_exception, fmt("Failed to load header from ranking_data with ranking_id %d.", ranking_id)) << NEST(e);
   }
}

void
db::load_team_ranks(id_t id, team_ranks_t& team_ranks, double data_time_low_limit_s)
{
   clear_res();
   team_ranks.clear();
   timer_us timer;

   {
      exec(fmt("SELECT data FROM ranking_data WHERE ranking_id = %d;", id), {}, {}, {});
   }

   if (res_value_size(0, 0) == 0) {
      THROW(db_exception, fmt("Got size 0 from ranking %d.", id));
   }

   team_ranks_header trh;
   team_rank_t tr;
   
   string s(res_value(0, 0), res_value_size(0, 0));
   stringstream ss(s);
   try {
      ss >> trh;
   }
   catch (io_exception &e) {
      THROW(db_exception, fmt("Failed to load header from ranking_data with ranking_id %d.", id)) << NEST(e);
   }

   uint32_t skip_count = 0;
   for (uint32_t i = 0; i < trh.count; ++i) {
      read_tr(ss, trh.version, tr);
      if (data_time_low_limit_s <= tr.data_time) {
         team_ranks.push_back(tr);
      }
      else {
         ++skip_count;
      }
   }
   
   LOG_INFO("loaded %d team ranks from ranking_data ranking_id %d (%d bytes) in %fs, skipped %d due to data_time",
            team_ranks.size(), id, res_value_size(0, 0), float(timer.end()) / 1e6, skip_count);
   clear_res();
}

void
db::save_team_ranks(id_t id, float now, team_ranks_t& team_ranks)
{
   // data_time for ranking us updated in python.

   team_ranks_header trh(team_ranks.size());
   timer_us timer;
   stringstream ss;
   ss << trh;

   for (uint32_t i = 0; i < team_ranks.size(); ++i) {
      ss << team_ranks[i];
   }
   
   string data = ss.str();
   
   if (data.size() >= (1L << 31)) {
      THROW(db_exception, fmt("fatal, can not handle blob this big (%d bytes)", data.size()));
   }

   exec(fmt("SELECT count(1) FROM ranking_data WHERE ranking_id = %d", id));
   if (res_int(0, 0) == 0) {
      exec(fmt("INSERT INTO ranking_data (id, ranking_id, updated)"
               " VALUES (%d, %d, to_timestamp(%f))",
               id, id, now));
   }
   
   {
      if (now < 1) {
         exec(fmt("UPDATE ranking_data SET data = $1::bytea WHERE ranking_id = %d", id),
              { (char*) data.c_str() },
              { static_cast<int>(data.size()) },
              { 1 }); // Binary arg.
      }
      else {
         exec(fmt("UPDATE ranking_data SET updated = to_timestamp(%f), data = $1::bytea WHERE ranking_id = %d",
                  now, id),
              { (char*) data.c_str() },
              { static_cast<int>(data.size()) },
              { 1 }); // Binary arg.
      }
   }
   clear_res();
   
   LOG_INFO("saved %d team ranks to ranking_data ranking_id %d (%d bytes) in %fs",
            team_ranks.size(), id, data.size(), float(timer.end()) / 1e6);
}

void
db::update_or_create_ranking_stats(ranking_stats_t& ranking_stats, id_t id)
{
   stringstream ss;
   ss << ranking_stats;
   string data = ss.str();

   float now = float(now_us()) / 1e6;
   
   if (data.size() >= (1L << 31)) {
      THROW(db_exception, fmt("fatal, can not handle blob this big (%d bytes)", data.size()));
   }

   timer_us timer;

   exec(fmt("SELECT count(1) FROM ranking_stats WHERE ranking_id = %d", id));
   if (res_int(0, 0) == 0) {
      exec(fmt("INSERT INTO ranking_stats (id, ranking_id, updated) VALUES"
               " (%d, %d, to_timestamp(%f))",
               id, id, now));
   }
   
   exec(fmt("UPDATE ranking_stats SET updated = to_timestamp(%f), data = $1::text WHERE ranking_id = %d",
            now, id),
        { (char*) data.c_str() },
        { static_cast<int>(data.size()) },
        { 0 }, // Text arg.
        0);  // Text return format.
   
   LOG_INFO("updated/created ranking_stats ranking_id %d (%d bytes) in %fs",
            id, data.size(), float(timer.end()) / 1e6);
}

void
db::load_ranking_stats(ranking_stats_t& ranking_stats, id_t ranking_id)
{
   clear_res();

   exec(fmt("SELECT rs.data, EXTRACT(epoch FROM r.data_time), r.season_id FROM ranking_stats rs JOIN ranking r"
            " ON r.id = rs.ranking_id"
            " WHERE rs.ranking_id = %d", ranking_id));
   
   if (res_size() == 0) {
      THROW(db_exception, fmt("Fatal, did not find ranking_stats with ranking_id %d.", ranking_id));
   }
   
   string s(res_value(0, 0), res_value_size(0, 0));
   stringstream ss(s);
   
   ss >> ranking_stats;

   ranking_stats.ranking_id = ranking_id;
   ranking_stats.data_time = res_double(0, 1);
   ranking_stats.season_id = res_int(0, 2);
}
   
void
db::load_all_ranking_stats(ranking_stats_list_t& ranking_stats_list, uint32_t filter_season)
{
   ranking_stats_list.clear();
   clear_res();
   
   // Ranking.COMPLETE_WITH_DATA and Ranking.COMPLETE_WITOUT_DATA used here.
   exec(fmt("SELECT rs.data, r.id, EXTRACT(epoch FROM r.data_time) as data_time, s.id, s.version FROM ranking_stats rs"
            " JOIN ranking r ON r.id = rs.ranking_id"
            " JOIN season s ON r.season_id = s.id"
            " WHERE r.status IN (1, 2) AND r.season_id > %d ORDER BY data_time", filter_season));

   uint32_t size = res_size();
   for (uint32_t i = 0; i < size; ++i) {
      string s(res_value(i, 0), res_value_size(i, 0));
      stringstream ss(s);
      ranking_stats_t stats;
      ss >> stats;
      
      stats.ranking_id = res_int(i, 1);
      stats.data_time = res_float(i, 2);
      stats.season_id = res_int(i, 3);
      stats.season_version = res_int(i, 4);
      
      ranking_stats_list.push_back(stats);
   }
}

void
db::load_seen_team_ids(unordered_set<id_t>& team_ids, string threshold_date)
{
   team_ids.clear();

   pg_escape e_date(_conn, threshold_date);

   stringstream sql;
   sql << "SELECT id FROM team WHERE last_seen >= " << e_date;
   exec(sql);

   uint32_t size = res_size();
   for (uint32_t i = 0; i < size; ++i) {
      team_ids.insert(res_int(i, 0));
   }
   LOG_INFO("loaded %d team_ids that was seen since %s (inclusive)", team_ids.size(), threshold_date.c_str());
}


void
db::reconnect()
{
   disconnect();

   _conn = PQconnectdb(_db_name.c_str());
   if (PQstatus(_conn) != CONNECTION_OK) {
      THROW(base_exception, fmt("failed to connect to database %s, %s", _db_name.c_str(), PQerrorMessage(_conn)));
   }
}

void
db::disconnect()
{
   if (_res != NULL) {
      PQclear(_res);
      _res = NULL;
   }
   if (_conn != NULL) {
      PQfinish(_conn);
      _conn = NULL;
   }
}

db::~db()
{
   if (_res != NULL) {
      PQclear(_res);
      _res = NULL;
   }
   if (_conn != NULL) {
      PQfinish(_conn);
      _conn = NULL;
   }
}

