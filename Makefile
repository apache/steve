CC = gcc
INSTALLBIN = /home/voter/bin
SUIDS = -DTARGET_UID=508 -DTARGET_GID=508

all: votegroup make_issue vote close_issue reminder check_quorum

votegroup: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/votegroup.pl\" $(SUIDS) \
	      -o votegroup wrapsuid.c

make_issue: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/make_issue.pl\" $(SUIDS) \
	      -o make_issue wrapsuid.c

vote: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/vote.pl\" $(SUIDS) \
	      -o vote wrapsuid.c

close_issue: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/close_issue.pl\" $(SUIDS) \
	      -o close_issue wrapsuid.c

reminder: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/reminder.pl\" $(SUIDS) \
	      -o reminder wrapsuid.c

check_quorum: wrapsuid.c
	$(CC) -DPROGNAME=\"$(INSTALLBIN)/check_quorum.pl\" $(SUIDS) \
	      -o check_quorum wrapsuid.c

install: install-votegroup install-make_issue install-vote install-close_issue install-reminder install-check_quorum

install-votegroup: votegroup
	rm -f $(INSTALLBIN)/votegroup $(INSTALLBIN)/votegroup.pl
	cp -p votegroup.pl $(INSTALLBIN)/votegroup.pl
	cp -p votegroup $(INSTALLBIN)/votegroup
	chmod 700 $(INSTALLBIN)/votegroup.pl
	chmod 6755 $(INSTALLBIN)/votegroup

install-make_issue: make_issue
	rm -f $(INSTALLBIN)/make_issue $(INSTALLBIN)/make_issue.pl
	cp -p make_issue.pl $(INSTALLBIN)/make_issue.pl
	cp -p make_issue $(INSTALLBIN)/make_issue
	chmod 700 $(INSTALLBIN)/make_issue.pl
	chmod 6755 $(INSTALLBIN)/make_issue

install-vote: vote
	rm -f $(INSTALLBIN)/vote $(INSTALLBIN)/vote.pl
	cp -p vote.pl $(INSTALLBIN)/vote.pl
	cp -p vote $(INSTALLBIN)/vote
	chmod 700 $(INSTALLBIN)/vote.pl
	chmod 6755 $(INSTALLBIN)/vote

install-close_issue: close_issue
	rm -f $(INSTALLBIN)/close_issue $(INSTALLBIN)/close_issue.pl
	cp -p close_issue.pl $(INSTALLBIN)/close_issue.pl
	cp -p close_issue $(INSTALLBIN)/close_issue
	chmod 700 $(INSTALLBIN)/close_issue.pl
	chmod 6755 $(INSTALLBIN)/close_issue

install-reminder: reminder
	rm -f $(INSTALLBIN)/reminder $(INSTALLBIN)/reminder.pl
	cp -p reminder.pl $(INSTALLBIN)/reminder.pl
	cp -p reminder $(INSTALLBIN)/reminder
	chmod 700 $(INSTALLBIN)/reminder.pl
	chmod 6755 $(INSTALLBIN)/reminder

install-check_quorum: check_quorum
	rm -f $(INSTALLBIN)/check_quorum $(INSTALLBIN)/check_quorum.pl
	cp -p check_quorum.pl $(INSTALLBIN)/check_quorum.pl
	cp -p check_quorum $(INSTALLBIN)/check_quorum
	chmod 700 $(INSTALLBIN)/check_quorum.pl
	chmod 6755 $(INSTALLBIN)/check_quorum

