# ---- Liquibase local runner ---------------------------------------------------
# Il wrapper, mai il binario nudo: aggancia il driver JDBC versionato nel repo e
# rigenera changelog-autogen.yaml. Dal 02-09-2026 nel PATH non c'e' piu' alcun
# liquibase, quindi qui un nome nudo non funzionerebbe affatto.
LIQUIBASE ?= scripts/liquibase5.sh

DB_HOST   ?= localhost
DB_PORT   ?= 5432
DB_NAME   ?= zeroerp
DB_USER   ?= zeroerp
DB_PASS   ?= secret

# ⚠️ master-v2, non v1. Il v1 copre solo baseline+migrations (488 changeSet) ed
#   esclude tutto migrations_v2 (3210): con il v1 il target ci-apply non trovava
#   nemmeno un changeSet in contesto ci_apply e usciva con successo, e la
#   timeline autogen non veniva mai rigenerata (verificato il 02-09-2026).
CHANGELOG ?= db/changelog/changelog-master-v2.yaml

# JDBC base e opzioni (disabilita dblink-log; nella seconda chiamiamo anche app.env=ci)
JDBC_BASE := jdbc:postgresql://$(DB_HOST):$(DB_PORT)/$(DB_NAME)
OPTS_NODBLINK := ?options=-c%20myapp.log_with_dblink%3Doff
OPTS_CI      := $(OPTS_NODBLINK)%20-c%20myapp.env%3Dci

.PHONY: db-migrate db-ci-apply db-setup

db-migrate:
	@echo "==> Liquibase base update (esclusi i contesti test e provision)…"
	$(LIQUIBASE) \
	  --url="$(JDBC_BASE)$(OPTS_NODBLINK)" \
	  --username="$(DB_USER)" \
	  --password="$(DB_PASS)" \
	  --changeLogFile="$(CHANGELOG)" \
	  update --contexts="!test AND !provision"

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
