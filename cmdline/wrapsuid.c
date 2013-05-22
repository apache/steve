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
 /* Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <sys/types.h>
#include <unistd.h>
#include <stdlib.h>

int main(int argc, char **argv, char **envp) {

    setuid((uid_t )TARGET_UID);
    setgid((gid_t )TARGET_GID);
    execve(PROGNAME, argv, envp);
}
