
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

#include <sstream>
#include <iostream>

#include "exception.hpp"

const char*
base_exception::what() const throw()
{
   try {
      what_ = format();
      return what_.c_str();
   }
   catch (...) {
      return "What string creation threw exception, this is a fallback message.";
   }
}

const std::string
base_exception::format() const
{
   std::stringstream ss;
   
   const std::string* msg = boost::get_error_info<ex_message>(*this);
   if (msg != NULL) {
      ss << *msg;
   }
   
   const int* line = boost::get_error_info<ex_line>(*this);
   
   const std::string* file = boost::get_error_info<ex_file>(*this);
   
   const int* errno_ = boost::get_error_info<ex_errno>(*this);
   
   if (file != NULL || line != NULL || errno_ != NULL) {
      ss << " (";
      if (errno_ != NULL) {
         ss << "errno " << *errno_ << " '" << strerror(*errno_) << "' ";
      }
      if (file != NULL && line != NULL) {
         ss << "at " << *file << ":" << *line;
      }
      ss << ")";
   }
   
   const boost::exception_ptr* cause = boost::get_error_info<ex_cause>(*this);
   
   if (NULL != cause) {
      try {
         boost::rethrow_exception(*cause);
      }
      catch (const base_exception& e) {
         ss << ": " << e.format();
      }
      catch (const std::exception& e) {
         ss << ": " << e.what();
      }
      catch (...) {
         ss << ": <unknown cause>";
      }
   }
   
   return ss.str();
}

base_exception::~base_exception() throw()
{
}
