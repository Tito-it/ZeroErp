# ---- Liquibase local runner ---------------------------------------------------
LIQUIBASE ?= liquibase

DB_HOST   ?= localhost
DB_PORT   ?= 5432
DB_NAME   ?= zeroerp
DB_USER   ?= zeroerp
DB_PASS   ?= secret

CHANGELOG ?= db/changelog/changelog-master.yaml

# JDBC base e opzioni (disabilita dblink-log; nella seconda chiamiamo anche app.env=ci)
JDBC_BASE := jdbc:postgresql://$(DB_HOST):$(DB_PORT)/$(DB_NAME)
OPTS_NODBLINK := ?options=-c%20myapp.log_with_dblink%3Doff
OPTS_CI      := $(OPTS_NODBLINK)%20-c%20myapp.env%3Dci

.PHONY: db-migrate db-ci-apply db-setup

db-migrate:
	@echo "==> Liquibase base update (no test contexts)…"
	$(LIQUIBASE) \
	  --url="$(JDBC_BASE)$(OPTS_NODBLINK)" \
	  --username="$(DB_USER)" \
	  --password="$(DB_PASS)" \
	  --changeLogFile="$(CHANGELOG)" \
	  update --contexts="!test"

db-ci-apply:
	@echo "==> Liquibase CI apply (runner/automations)…"
	$(LIQUIBASE) \
	  --url="$(JDBC_BASE)$(OPTS_CI)" \
	  --username="$(DB_USER)" \
	  --password="$(DB_PASS)" \
	  --changeLogFile="$(CHANGELOG)" \
	  update --contexts="ci_apply"

# One-shot: schema + automazioni come in CI
db-setup: db-migrate db-ci-apply
	@echo "==> Done."
