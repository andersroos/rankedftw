
#include "log.hpp"

#include <cstdarg>
#include <stdint.h>
#include <boost/python/object.hpp>
#include <boost/python/dict.hpp>

using namespace boost::python;

object py_logger;

void log_test()
{
   LOG_INFO("info %d", 123);
   LOG_WARNING("warning %d", 1236);
   LOG_ERROR("error %d", 123123);
}

void log(const uint32_t& level, const char* file, int line, const char* format, ...)
{
   va_list va_args;
   va_start(va_args, format);
   char message[2048];
   vsnprintf(message, sizeof(message), format, va_args);

   // va_args

   object log_method;

   switch (level) {
      case LEVEL_INFO: log_method = py_logger.attr("info"); break;
      case LEVEL_WARNING: log_method = py_logger.attr("warning"); break;
      case LEVEL_ERROR: log_method = py_logger.attr("error"); break;
   }
   
   list args;
   args.append(message);
   
   dict extra;
   extra["cpp_file"] = file;
   extra["cpp_line"] = line;
   
   dict kwargs;
   kwargs["extra"] = extra;
   
   log_method(*tuple(args), **kwargs);

   // va_args
   
   va_end(va_args);
}

