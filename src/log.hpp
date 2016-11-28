#pragma once

#include <stdint.h>
#include <iostream>

#define LEVEL_INFO 0
#define LEVEL_WARNING 1
#define LEVEL_ERROR 2

#define LOG_INFO(FORMAT, ...)    log(LEVEL_INFO, __FILE__, __LINE__, FORMAT, ##__VA_ARGS__)
#define LOG_WARNING(FORMAT, ...) log(LEVEL_WARNING, __FILE__, __LINE__, FORMAT, ##__VA_ARGS__)
#define LOG_ERROR(FORMAT, ...)   log(LEVEL_ERROR, __FILE__, __LINE__, FORMAT, ##__VA_ARGS__)

// Log, but use the macro instead.
void log(const uint32_t& level, const char* file, int line, const char* format, ...);

// Set the output stream for the log.
void set_log_output(std::ostream* out);
