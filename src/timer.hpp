#pragma once

#include <stdint.h>

#include <util.hpp>

//
// Execution timing.
//

typedef uint64_t duration_us_t;

struct conv_us
{
   // Convert to seconds.
   static float s(duration_us_t duration) {
      return float(duration) / 1000000;
   }

   // Convert to miliseconds.
   static float ms(duration_us_t duration) {
      return float(duration) / 1000;
   }
};

// Time execution in micro seconds.
struct timer_us
{
   // Create a timer and start it unless start is false.
   timer_us(bool start = true) : _start(-1), _last(-1), _end(-1)
   {
      if (start) {
         _start = now_us();
      }
   }

   // Start the timer, in most cases the constructor starts the timer.  Start will only have effect the first time it is
   // called.
   void start()
   {
      if (_start < 0) {
         _start = now_us();
      }
   }

   // Take a mid timing. Will return the duration since start or last call to mid, whichever is latest. If the timer was
   // not started the behaviour is undefined.
   duration_us_t mid()
   {
      int64_t last = _last;
      _last = now_us();
      
      if (last > 0) {
         return _last - last;
      }
      
      return _last - _start;
   }

   // Return the duration from start but do not save any state.
   duration_us_t from_start()
   {
      return now_us() - _start;
   }

   // Return the duration from last mig but do not save any state.
   duration_us_t from_mid()
   {
      return now_us() - _last;
   }
   
   // Does same as mid, but adds the mid timing to duration.
   void add_mid(duration_us_t& duration)
   {
      duration += mid();
   }

   // Take an end timing. Will return the durationn from start to end. If the timer was not started
   // the behaviour is undefined. If already taken, end will return.
   duration_us_t end()
   {
      if (_end < 0) {
         _end = now_us();
      }
      return _end - _start;
   }
   
   // Does the same as end, but adds the end timing to duration.
   void add_end(duration_us_t& duration)
   {
      duration += end();
   }

   // Resets the timer. Will also start the timer unless told not to.
   void reset(bool start = true) {
      _start = _last = _end = -1;
      if (start) {
         this->start();
      }
   }

private:

   int64_t _start;
   int64_t _last;
   int64_t _end;
};

//
// Will count time from construction to destruction and then add that time to duration.
//
struct add_duration_us
{
   add_duration_us(duration_us_t& duration) : timer(), _duration(duration) {}

   ~add_duration_us()
   {
      timer.add_end(_duration);
   }
   
   timer_us timer;
   
private:
   
   duration_us_t& _duration;
};   
