#pragma once

#include <string.h>
#include <boost/python/object.hpp>

#include "types.hpp"

std::string fmt(const char* format, ...);

uint64_t now_us();

// Extract a cpp vector from an enum list with key key.
std::vector<enum_t> extract_enum(const boost::python::object enums_info, const std::string& key);
