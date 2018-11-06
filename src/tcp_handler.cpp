#include "log.hpp"
#include <sstream>
#include "tcp_handler.hpp"
#include "exception.hpp"


Json::Value request::recv()
{
   char buf[2048];
   std::stringstream data;
   while (true) {
      auto received = ::recv(_server, buf, sizeof(buf), 0);
      if (received == -1) {
         THROW_E(net_exception, "failed to recv data");
      }
      data.write(buf, received);
      data.seekg(-1, data.end);
      data.read(buf, 1);
      if (buf[0] == '\n') {
         // We have the end of the request, read is complete.
         break;
      }
   }
   
   Json::Value value;
   Json::Reader reader;
   if (!reader.parse(data.str(), value)) {
      THROW(json_exception, fmt("Failed to parse json '%s': %s",
                                data.str().c_str(),
                                reader.getFormattedErrorMessages().c_str()));
   }
   return value;
}

void request::reply(const Json::Value response)
{
   Json::FastWriter writer;
   auto data = writer.write(response);

   while (data.size()) {
      auto sent = send(_server, data.c_str(), data.size(), 0);
      if (sent == -1) {
         THROW_E(net_exception, "failed to send data");
      }
      data.erase(0, sent);
   }
}

tcp_handler::tcp_handler(in_port_t port)
{
   _socket = socket(AF_INET6, SOCK_STREAM, 0);
   if (_socket == -1) {
      THROW_E(net_exception, "failed to create socket");
   }

   int opt = 1;
   if (setsockopt(_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1) {
      THROW_E(net_exception, "failed to set socket options");
   }

   struct sockaddr_in6 addr;
   memset(&addr, 0, sizeof(sockaddr_in6));
   addr.sin6_family = AF_INET6;
   addr.sin6_port = htons(port);
   
   if (bind(_socket, (sockaddr*) & addr, sizeof(sockaddr_in6)) == -1) {
      THROW_E(net_exception, fmt("failed to bind to port %d", port));
   }

   if (listen(_socket, 64) == -1) {
      THROW_E(net_exception, "could not listen to socket");
   }

   LOG_INFO("listenting to tcp port %d", port);   
}

void tcp_handler::accept(request& request)
{
   int server = ::accept(_socket, NULL, NULL);
   if (server == -1) {
      THROW_E(net_exception, "failed to accept connection");
   }

   request._server = server;
}
