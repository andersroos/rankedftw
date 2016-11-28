#include <string.h>
#include <stdarg.h>
#include <sstream>
#include <iostream>
#include <sys/time.h>
#include <boost/python/object.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/stl_iterator.hpp>
#include <boost/python/extract.hpp>

#include "util.hpp"
#include "exception.hpp"

using namespace boost::python;
using namespace std;

std::string fmt(const char* format, ...)
{
   va_list args;
   va_start(args, format);

   size_t len = strlen(format);
   
   char message[len + (1<<16)];

   int res = vsnprintf(message, sizeof(message), format, args);
   message[sizeof(message) - 1] = 0;

   if (res < 0 or uint32_t(res) >= sizeof(message) - 1) {
      THROW(base_exception, "fmt failed, total mesage too large or other error");
   }

   va_end(args);

   return std::string(message);
}

uint64_t now_us() {
   timeval now;
   gettimeofday(&now, 0);
   return now.tv_sec * 1000000 + now.tv_usec;
}

vector<enum_t> extract_enum(const object enums_info, const string& key) {
   vector<enum_t> res;

   object list = enums_info[key];
   
   for (uint32_t i = 0; i < len(list); ++i) {
      res.push_back(extract<enum_t>(list[i]));
   }
   return res;
}

