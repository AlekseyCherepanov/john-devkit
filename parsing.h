/* Copyright © 2015 Alexander Cherepanov <ch3root@openwall.com>
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 */

int proc_valid(const char *s, const char *format, ...);
void proc_extract(const char *s, const char *format, ...);

#define IGNORE_NUM ((uint32_t *)0)
