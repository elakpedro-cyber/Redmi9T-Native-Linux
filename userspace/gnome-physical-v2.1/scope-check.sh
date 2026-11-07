#!/bin/sh
set -eu
base=$1
test -d "$base"
mount_ns= pid_ns= net_ns=
if [ -f "$base/namespaces" ]; then
    { IFS= read -r mount_ns; IFS= read -r pid_ns; IFS= read -r net_ns; } <"$base/namespaces"
fi
if grep -F " $base/" /proc/self/mountinfo; then
    echo SCOPE_BUSY_PARENT_MOUNT
    exit 1
fi
for process in /proc/[0-9]*; do
    [ "${process##*/}" != "$$" ] || continue
    for kind in root exe cwd; do
        target=$(readlink "$process/$kind" 2>/dev/null || :)
        case "$target" in "$base"|"$base"/*)
            echo "SCOPE_BUSY path=$process/$kind target=$target"; exit 1;; esac
    done
    for file in "$process"/fd/*; do
        target=$(readlink "$file" 2>/dev/null || :)
        # The outer shell still reads its own launcher while invoking this check.
        [ "${process##*/}" != "$PPID" ] || [ "$target" != "$base/session.sh" ] || continue
        case "$target" in "$base"|"$base"/*)
            echo "SCOPE_BUSY_FD path=$file target=$target"; exit 1;; esac
    done
    [ -n "$mount_ns" ] || continue
    for file in "$process/ns/mnt" "$process/ns/pid" "$process/ns/net" "$process"/fd/*; do
        target=$(readlink "$file" 2>/dev/null || :)
        case "$target" in "$mount_ns"|"$pid_ns"|"$net_ns")
            echo "SCOPE_BUSY_NAMESPACE path=$file target=$target"; exit 1;; esac
    done
done
echo SCOPE_CLEAR
