#!/bin/sh
set -eu
umask 077
test -c /dev/dri/renderD128 || { echo 'Adreno render node is required' >&2; exit 1; }
export MESA_SHADER_CACHE_DISABLE=true
/usr/local/bin/gpu-render-v7 /dev/dri/renderD128 > /tmp/freedreno-test.log 2>&1
cat /tmp/freedreno-test.log
grep -F 'DRM=msm' /tmp/freedreno-test.log
grep -Eq 'renderer=(FD610|Adreno [(]TM[)] 610)([^0-9]|$)' /tmp/freedreno-test.log
grep -F '256 RGBA pixels verified' /tmp/freedreno-test.log
printf '%s  %s\n' ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb /tmp/gpu-render-v7.rgba | sha256sum -c -
