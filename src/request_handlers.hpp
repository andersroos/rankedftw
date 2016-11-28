#pragma once

#include <jsoncpp/json/json.h>

#include "data_handler.hpp"
#include "udp_handler.hpp"


struct request_handler
{
   request_handler(udp_handler& udp_handler, data_handler& data_handler) :
      _udp_handler(udp_handler),
      _data_handler(data_handler)
   {}

   virtual void operator()() {}
      
   
   virtual void start()
   {
      try {
         boost::thread(boost::ref(*this));
      }
      catch (std::exception& e) {
         LOG_ERROR("got exception in thread: %s", e.what());
      }
   }

   void reply_json(request& r, Json::Value& data)
   {
      r.json(data);
      _udp_handler.reply(r);
   }
      
   void reply_error(request& r, uint32_t code, const std::string& message)
   {
      Json::Value data;
      data["code"] = code;
      data["message"] = message;
      reply_json(r, data);
   }

   virtual ~request_handler() {}

protected:
   udp_handler& _udp_handler;
   data_handler& _data_handler;
};


// The cached version, not implemented yet because it is not really needed. ;-)
struct team_history_request_handler : public request_handler
{
   team_history_request_handler(udp_handler& udp_handler, data_handler& data_handler) :
      request_handler(udp_handler, data_handler)
   {}
   
   virtual void operator()();

   virtual ~team_history_request_handler() {}
   
};
