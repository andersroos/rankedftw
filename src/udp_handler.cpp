
#include <arpa/inet.h>

#include "udp_handler.hpp"
#include "exception.hpp"
#include "util.hpp"
#include "log.hpp"

void
request::json(Json::Value value)
{
   Json::FastWriter writer;
   response_data = writer.write(value);
}

Json::Value
request::json()
{
   Json::Value value;
   Json::Reader reader;
   if (!reader.parse(request_data, value)) {
      THROW(json_exception, fmt("Failed to parse json '%s': %s",
                                request_data.c_str(),
                                reader.getFormattedErrorMessages().c_str()));
   }
   return value;
}

udp_handler::udp_handler(in_port_t port)
{
   _socket = socket(AF_INET, SOCK_DGRAM, 0);
   if (_socket == -1) {
      THROW_E(net_exception, "Could not create socket.") << boost::errinfo_errno(errno);
   }
   
   sockaddr_in addr;
   memset(&addr, 0, sizeof(sockaddr_in));
   addr.sin_family = AF_INET;
   addr.sin_port = htons(port);
   addr.sin_addr.s_addr = inet_addr("127.0.0.1");
   if (bind(_socket, (sockaddr*) & addr, sizeof(sockaddr_in)) == -1) {
      THROW_E(net_exception, fmt("Failed to bind socket to port %d and ip 127.0.0.1.", port));
   }
   LOG_INFO("listenting to udp port %d", port);
}

void
udp_handler::reply(const request& request)
{
   socklen_t addrlen = sizeof(sockaddr_in);
   
   ssize_t sent = sendto(_socket, request.response_data.c_str(), request.response_data.length(), 0,
                         (sockaddr*) &request.request_src, addrlen);
   if (sent == -1) {
      THROW_E(net_exception, "Failed to send data.");
   }
   
   if (sent != int32_t(request.response_data.length())) {
      THROW(net_exception, fmt("Failed to send all the data, size was %d, sent %d.",
                               request.response_data.length(), sent));
   }
   
}

request
udp_handler::recv()
{
   char buf[1<<16];
   socklen_t addrlen = sizeof(sockaddr_in);
   
   request request;
   
   ssize_t received = recvfrom(_socket, buf, 1<<16, 0, (sockaddr*) &request.request_src, &addrlen);
   if (received == -1) {
      THROW_E(net_exception, "Failed to receive data.");
   }

   request.request_data = std::string(buf, received);

   return request;
}

udp_handler::~udp_handler()
{
   close(_socket);
}
