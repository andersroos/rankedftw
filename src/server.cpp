#include <stdlib.h>
#include <signal.h>
#include <stdio.h>
#include <atomic>
#include <iostream>
#include <boost/thread.hpp>
#include <boost/program_options.hpp>
#include <jsoncpp/json/json.h>
#include <fstream>
#include <glo.hpp>

#include "tcp_handler.hpp"
#include "exception.hpp"
#include "log.hpp"
#include "ladder_handler.hpp"

using namespace std;
using namespace glo;
namespace po = boost::program_options;

struct signal_handler
{
   signal_handler()
   { 
      sigset_t all;
      sigfillset(&all);
      if (pthread_sigmask(SIG_BLOCK, &all,  NULL) != 0) {
         THROW_E(signal_exception, "Failed to block all signals.");
      }
   }
   
   void operator()()
   {
      sigset_t mask;
      sigemptyset(&mask);
      sigaddset(&mask, SIGINT);
      sigaddset(&mask, SIGTERM);
      sigaddset(&mask, SIGQUIT);
      
      if (pthread_sigmask(SIG_BLOCK, &mask, NULL) != 0) {
         THROW_E(signal_exception, "Failed to block signals in mask.");
      }

      try {
         while (true) {
            boost::this_thread::interruption_point();

            LOG_INFO("signal handler ready");
            
            int signal = 0;
            sigwait(&mask, &signal);

            LOG_INFO("got signal %d, exiting", signal);
            exit(0);
         }
      }
      catch (const boost::thread_interrupted& e) {
         LOG_WARNING("signal listening thread got interrupted, it will now die");
      }
   }
};

int main(int argc, char *argv[])
{
   try {
      po::variables_map vm;
      
      po::options_description desc("Usage");
      desc.add_options()
         ("db,d", po::value<string>()->default_value(DEFAULT_DB), "Database name to use.")
         ("log,l", po::value<string>(), "Output log to file.")
         ("help,h", "Print help.")
         ;
      po::store(po::parse_command_line(argc, argv, desc), vm);
      po::notify(vm);    
      
      if (vm.count("help")) {
         cerr << desc << endl;
         return 1;
      }
         
      ofstream log_os;
      if (vm.count("log")) {
         string log_filename(vm["log"].as<string>());
         log_os.open(log_filename, ios::out | ios::app);
         set_log_output(&log_os);
         LOG_INFO("logging to file %s", log_filename.c_str());
      }
      
      signal_handler signal_handler;
      boost::thread signal_handler_thread(signal_handler);
      
      tcp_handler tcp_handler(4747);
      ladder_handler ladder_handler(vm["db"].as<string>());

      glo::status_server status_server("/server", 22200);
      
      atomic<uint32_t> request_count(0);
      status_server.add(cref(request_count), "/request", {tag::COUNT}, level::MEDIUM, "Number of requests to the server.");
 
      status_server.start();
      LOG_INFO("started status server on port %d", status_server.port());
    
      // Dispatcher loop.
      while (true) {
         request request;
         tcp_handler.accept(request);
         boost::this_thread::interruption_point();
         
         Json::Value request_data = request.recv();
         string command = request_data["cmd"].asString();
         
         ++request_count;
         
         Json::Value response_data;
         if (command == "ladder") {
            response_data = ladder_handler.ladder(request_data);
         }
         else if (command == "clan") {
            response_data = ladder_handler.clan(request_data);
         }
         else if (command == "refresh") {
            response_data = ladder_handler.refresh(request_data);
         }
         else {
            LOG_WARNING("don't know what to do with command '%s'", command.c_str());
            response_data["code"] = 400;
            response_data["message"] = fmt("unknown command, '%s'", command.c_str());
         }

         request.reply(response_data);
      }
   }
   catch (std::exception& e) {
      // This is buggy, when threads above go out of scope the process will terminate.
      std::cerr << e.what() << std::endl;
      return 1;
   }
   
   return 0;
}
