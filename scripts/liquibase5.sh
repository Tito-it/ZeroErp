#!/usr/bin/env bash
# Wrapper per Liquibase 5 in sandbox

LB5_HOME="/opt/liquibase5"

"${LB5_HOME}/liquibase" "$@"