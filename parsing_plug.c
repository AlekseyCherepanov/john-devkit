/* -*- c-basic-offset: 2 -*- */
/* Copyright © 2015 Alexander Cherepanov <ch3root@openwall.com>
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 */

/* for size_t */
#include <stddef.h>
/* for uint32_t */
#include <stdint.h>
/* for isdigit etc. */
#include <ctype.h>
/* for va_list etc. */
#include <stdarg.h>
/* for strlen */
#include <string.h>

#include "parsing.h"

#pragma GCC diagnostic ignored "-Wdeclaration-after-statement"

static int initialized = 0;
static unsigned char dec[256], hex[256];

static void init()
{
  int i;

  for (i = 0; i < 10; i++) {
    dec['0' + i] = i;
    hex['0' + i] = i;
  }
  for (i = 10; i < 16; i++) {
    hex['A' + (i - 10)] = i;
    hex['a' + (i - 10)] = i;
  }
}

/**********************************************************************/

/*
  decimal number, positive, without leading zeroes (except for zero itself)
  (uint32_t only)
  empty string is not allowed
  gobbles all digits
*/
static const unsigned char *num_valid(const unsigned char *s, uint32_t min, uint32_t max, uint32_t *number)
{
  if (!s)
    return 0;

  /* convert */
  /* leading zeroes */
  const unsigned char *s0 = s;  /* start of the string */
  while (*s == '0')
    s++;
  /* further digits */
  const unsigned char *s1 = s;  /* after leading zeroes */
  uint32_t n = 0;
  while (isdigit(*s))
    n = n * 10 + dec[*s++];

  /* check */
  /* only two good cases: one 0 and no other digits or no 0 and there are other digits*/
  if (!((s1 == s0 + 1 && s == s1) || (s1 == s0 && s > s1)))
    return 0;
  if (s - s1 > 10)              /* too many digits for uint32_t */
    return 0;
  if (s - s1 == 10 && (*s1 > '4' || n < 1000000000u)) /* overflow in exactly 10 digits */
    return 0;
  if (n < min || n > max)
    return 0;

  /* results */
  if (number)
    *number = n;
  return s;
}

static const unsigned char *num_extract(const unsigned char *s, uint32_t *number)
{
  /* convert */
  uint32_t n = 0;
  while (isdigit(*s))
    n = n * 10 + dec[*s++];

  /* results */
  if (number)
    *number = n;
  return s;
}

/**********************************************************************/

/*
  binary data of variable length in hex
  empty string is allowed
  gobbles all hex digits
  stores length and data

  size should be <= SIZE_MAX / 2
*/
static const unsigned char *hex_var_valid(const unsigned char *s, size_t size, size_t *length)
{
  if (!s)
    return 0;

  /* convert */
  const unsigned char *s0 = s;
  while (isxdigit(*s))
    s++;

  /* check */
  size_t len = s - s0;           /* casted from ptrdiff_t to size_t */
  if (len % 2 != 0 || len > size * 2)
    return 0;

  /* results */
  if (length)
    *length = len / 2;
  return s;
}

static const unsigned char *hex_var_extract(const unsigned char *s, size_t *length, unsigned char *buffer)
{
  /* convert */
  unsigned char *p = buffer;
  while (isxdigit(s[0])) {
    *p++ = hex[s[0]] * 16 + hex[s[1]];
    s += 2;
  }

  /* results */
  *length = p - buffer;         /* casted from ptrdiff_t to size_t */
  return s;
}

/**********************************************************************/

/*
  generic parsing function -- validation
*/
int proc_valid(const char *s0, const char *format0, ...)
{
  if (!initialized)
    init();

  va_list ap;
  const unsigned char *s = (const unsigned char *)s0;
  const unsigned char *format = (const unsigned char *)format0;

  va_start(ap, format0);

  /* for %l */
  int have_length = 0;
  uint32_t length = 0;          /* silence -Wmaybe-uninitialized */

  const unsigned char *p = format;
  while (*p && s) {
    if (*p == ' ') {
      /* ignore spaces */
      p++;
    } else if (*p != '%') {
      /* fixed */
      /* printf(" %c", *p); */
      if (*s == *p)
        s++;
      else
        s = 0;
      p++;
    } else {
      p++;                      /* skip % */

      /* numbers like in %40h or %1-64d */
      size_t size1, size2 = UINT32_MAX;
      if (*p == '*') {
        size1 = va_arg(ap, int);
        p++;
      } else {
        size1 = 0;
        while (isdigit(*p))
          size1 = size1 * 10 + dec[*p++];
      }
      if (*p == '-') {          /* range */
        p++;
        if (*p == '*') {
          size2 = va_arg(ap, int);
          p++;
        } else {
          size2 = 0;
          while (isdigit(*p))
            size2 = size2 * 10 + dec[*p++];
        }
      }

      /* specifiers */
      switch (*p) {
      case 'd':                 /* number */
        /* printf(" %%(%zu-%zu)d", size1, size2); */
        s = num_valid(s, size1, size2, 0);
        break;
      case 'l':                 /* length of the next data field of variable length*/
        /* printf(" %%l"); */
        have_length = 1;
        s = num_valid(s, 0, (uint32_t)-1, &length);
        break;
      case 'h':                 /* hex data */
        /* printf(" %%(%zu)h", size1); */
        {
          size_t len = 0;
          /* printf("hi there 1\n"); */
          /* printf("hi there 4\n"); */
          /* printf("%p %d\n", s, size1); */
          /* printf("%s\n", s); */
          /* printf("hi there 3\n"); */
          s = hex_var_valid(s, size1, &len);
          /* printf("hi there 2\n"); */
          if (have_length &&  len != length)
            s = 0;
          else
            have_length = 0;
        }
        break;
      }
      p++;
    }
  }
  /* puts(""); */

  va_end(ap);
  return *p == 0 && s && *s == 0;
}

/*
  generic parsing function -- extraction
*/
void proc_extract(const char *s0, const char *format0, ...)
{
  if (!initialized)
    init();

  va_list ap;
  const unsigned char *s = (const unsigned char *)s0;
  const unsigned char *format = (const unsigned char *)format0;

  va_start(ap, format0);

  const unsigned char *p = format;
  while (*p) {
    if (*p == ' ') {
      /* ignore spaces */
      p++;
    } else if (*p != '%') {
      /* fixed */
      /* printf(" %c", *p); */
      s++;
      p++;
    } else {
      p++;                      /* skip % */

      if (*p == '*') {
        p++;
      } else {
        while (isdigit(*p))
          p++;
      }
      if (*p == '-') {          /* range */
        p++;
        if (*p == '*') {
          p++;
        } else {
          while (isdigit(*p))
            p++;
        }
      }

      /* specifiers */
      switch (*p) {
      case 'd':                 /* number */
        /* printf(" %%(*-*)d"); */
        s = num_extract(s, va_arg(ap, uint32_t *));
        break;
      case 'l':                 /* length of the next data field of variable length*/
        /* printf(" %%l"); */
        s = num_extract(s, 0);
        break;
      case 'h':                 /* hex data */
        /* printf(" %%(*)h"); */
        {
          size_t *t1 = va_arg(ap, size_t *);
          unsigned char *t2 = va_arg(ap, unsigned char *);
          /* printf("11\n"); */
          s = hex_var_extract(s, t1, t2);
          /* printf("12\n"); */
        }
        break;
      }
      p++;
    }
  }
  /* puts(""); */

  va_end(ap);
}
