#!/bin/sh
# Silent guard: skip the hook entirely if uv is not installed.
command -v uv >/dev/null 2>&1 || exit 0
exec uv "$@"
