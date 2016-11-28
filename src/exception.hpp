#pragma once

#include <string.h>
#include <errno.h>
#include <stdexcept>

#include <boost/exception/exception.hpp>
#include <boost/exception/error_info.hpp>
#include <boost/exception/errinfo_at_line.hpp>
#include <boost/exception/errinfo_errno.hpp>
#include <boost/exception/errinfo_file_name.hpp>
#include <boost/exception/errinfo_nested_exception.hpp>
#include <boost/exception/get_error_info.hpp>
#include <boost/exception_ptr.hpp>

#include "util.hpp"

typedef boost::errinfo_file_name                                  ex_file;
typedef boost::errinfo_at_line                                    ex_line;
typedef boost::errinfo_errno                                      ex_errno;
typedef boost::errinfo_nested_exception                           ex_cause;
typedef boost::error_info<struct tag_ex_message, std::string>     ex_message;

#define THROW( EXCEPTION, MESSAGE )                                     \
   throw EXCEPTION()                                                    \
      << ex_file( __FILE__ )                                            \
      << ex_line( __LINE__ )                                            \
      << ex_message( MESSAGE )

#define THROW_E( EXCEPTION, MESSAGE )                                   \
   throw  EXCEPTION()                                                   \
      << ex_file( __FILE__ )                                            \
      << ex_line( __LINE__ )                                            \
      << ex_message( MESSAGE )                                          \
      << ex_errno( errno )

#define NEST( CAUSE ) ex_cause(boost::copy_exception( CAUSE ))

//
// Base class exceptions.
//
// This class is based on boost::exception, all data should be added
// with the operator<< and boost::error_info.
//
class base_exception : public virtual std::exception, public virtual boost::exception
{
public:
   
   virtual const char* what() const throw();

   virtual ~base_exception() throw();

private:
   
   mutable std::string what_;

protected:
   
   //
   // Format the error message.
   // 
   virtual const std::string format() const;
};

struct io_exception : public base_exception {};
struct db_exception : public base_exception {};
struct bug_exception : public base_exception {};
struct net_exception : public base_exception {};
struct signal_exception : public base_exception {};
struct json_exception : public base_exception {};
