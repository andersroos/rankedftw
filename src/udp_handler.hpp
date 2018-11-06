#pragma once

#include <string.h>
#include <string>
#include <jsoncpp/json/json.h>
#include <netinet/in.h>
#include <sys/socket.h>

struct request
{
   request() :
      response_data(),
      request_data()
   {
      memset(&request_src, 0, sizeof(sockaddr_in));
   }

   // Set response as json value.
   void json(Json::Value value);

   // Get request as json value.
   Json::Value json();
   
   std::string response_data;
   std::string request_data;
   sockaddr_in request_src;
};

struct udp_handler {

   udp_handler(in_port_t port);

   // Sends a reply message to dest_addr, see sendto system call.
   void reply(const request& request);   

   // Block until a message is available and then returns it.
   request recv();

   virtual ~udp_handler();

private:

   int _socket;
};
