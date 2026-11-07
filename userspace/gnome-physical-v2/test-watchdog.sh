#!/bin/busybox sh
set -eu
trap 'rc=$?; if [ "$rc" != 0 ]; then for log in /tmp/*.log; do busybox cat "$log"; done; fi' EXIT
export PATH=/bin
for app in sleep mount cat grep mkdir rm; do busybox ln -s /bin/busybox /bin/$app; done
mkdir -p /tmp /probe
cat >/child.sh <<'EOF'
#!/bin/busybox sh
set -eu
mount -t proc proc /proc
mount -t tmpfs tmpfs /probe
echo private >/probe/private
sleep 120 &
echo $! >/tmp/child.pid
trap 'echo GRACEFUL_CHILD_STOP; exit 0' TERM
while :; do sleep 1; done
EOF
read start _ </proc/uptime
/watchdog 7 /bin/busybox sh /child.sh >/tmp/soft.log 2>&1
test ! -e /probe/private
! busybox kill -0 "$(cat /tmp/child.pid)" 2>/dev/null
grep GRACEFUL_CHILD_STOP /tmp/soft.log
echo PASS_WATCHDOG_SOFT_DEADLINE
/watchdog 20 /bin/busybox sh /child.sh >/tmp/stop.log 2>&1 &
p=$!
sleep 1
busybox kill -TERM "$p"
wait "$p"
grep GRACEFUL_CHILD_STOP /tmp/stop.log
test ! -e /probe/private
echo PASS_WATCHDOG_MANUAL_STOP
cat >/stubborn.sh <<'EOF'
#!/bin/busybox sh
mount -t proc proc /proc
trap '' TERM
sleep 120 &
echo $! >/tmp/stubborn.pid
while :; do sleep 1; done
EOF
set +e
/watchdog 2 /bin/busybox sh /stubborn.sh >/tmp/hard.log 2>&1
rc=$?
set -e
test "$rc" = 124
! busybox kill -0 "$(cat /tmp/stubborn.pid)" 2>/dev/null
grep 'WATCHDOG deadline' /tmp/hard.log
read end _ </proc/uptime
echo ALL_WATCHDOG_TESTS_PASS start=$start end=$end
