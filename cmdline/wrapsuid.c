/*
 * wrapsuid.c: simple setuid wrapper for perl scripts
 * Copyright (C) 2002  The Apache Software Foundation.  All rights reserved.
 *
 * You need to compile this with a command like
 *
 *    CC = gcc
 *    INSTALLBIN = /home/voter/bin
 *    SUIDS = -DTARGET_UID=508 -DTARGET_GID=508
 *
 *    $(CC) -DPROGNAME=\"$(INSTALLBIN)/vote.pl\" $(SUIDS) -o vote wrapsuid.c
 *
 * Note that the perl script must be careful about using the arguments.
 *
 * Originally created by Roy Fielding
 */

#include <sys/types.h>
#include <unistd.h>
#include <stdlib.h>

int main(int argc, char **argv, char **envp) {

    setuid((uid_t )TARGET_UID);
    setgid((gid_t )TARGET_GID);
    execve(PROGNAME, argv, envp);
}
