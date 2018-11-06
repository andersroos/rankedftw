#pragma once

#include <jsoncpp/json/json.h>
#include <unistd.h>
#include <arpa/inet.h>


struct tcp_handler;


struct request {

   request() : _server(-1) {}
   
   // blocks until full request is read then returns json
   Json::Value recv();

   // send reply
   void reply(const Json::Value response);   
                
   virtual ~request() { close(_server); };

private:
   
   friend tcp_handler;
   int _server;
};


struct tcp_handler {

   tcp_handler(in_port_t port);

   // block until a client connects and set server in request
   void accept(request& request);

   virtual ~tcp_handler() { close(_socket); }

private:

   int _socket;
};
