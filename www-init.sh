#!/bin/sh

PREFIX=/usr/local/apache2-install/people.apache.org/current
CFG=/home/voter/www/conf/httpd.conf

case "$1" in
    start)
        [ -x ${PREFIX}/bin/httpd ] && ${PREFIX}/bin/httpd -f ${CFG} -k start > /dev/null && echo -n ' apache'
        ;;
    stop)
        [ -r /var/run/httpd-vote.apache.org.pid ] && ${PREFIX}/bin/httpd -f ${CFG} -k stop > /dev/null && echo -n ' apache'
        ;;
    *)
        echo "Usage: `basename $0` {start|stop}" >&2
        ;;
esac

exit 0
