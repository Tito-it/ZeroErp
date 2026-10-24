# ---- Liquibase local runner ---------------------------------------------------
# Il wrapper, mai il binario nudo: aggancia il driver JDBC versionato nel repo e
# rigenera changelog-autogen.yaml. Dal 02-09-2026 nel PATH non c'e' piu' alcun
# liquibase, quindi qui un nome nudo non funzionerebbe affatto.
LIQUIBASE ?= scripts/liquibase5.sh

DB_HOST   ?= localhost
DB_PORT   ?= 5432
DB_NAME   ?= zeroerp
# Il migratore e' zeroerp_owner, proprietario di tutti gli oggetti (ruoli di
#   sistema, brief-db-ruoli-di-sistema, 2026-10-15). ⛔ Nessuna password nel
#   file: si passa da DB_PASS o, come per gli altri script, da DB_PASSWORD.
#   Su dbdev chi lavora come un altro utente lo dice sulla riga di comando: DB_USER=…
DB_USER   ?= zeroerp_owner
DB_PASS   ?= $(DB_PASSWORD)

# ⚠️ master-v2, non v1. Il v1 copre solo baseline+migrations (488 changeSet) ed
#   esclude tutto migrations_v2 (3210): con il v1 il target ci-apply non trovava
#   nemmeno un changeSet in contesto ci_apply e usciva con successo, e la
#   timeline autogen non veniva mai rigenerata (verificato il 02-09-2026).
CHANGELOG ?= db/changelog/changelog-master-v2.yaml

# JDBC base e opzioni (disabilita dblink-log; nella seconda chiamiamo anche app.env=ci)
JDBC_BASE := jdbc:postgresql://$(DB_HOST):$(DB_PORT)/$(DB_NAME)
OPTS_NODBLINK := ?options=-c%20myapp.log_with_dblink%3Doff
OPTS_CI      := $(OPTS_NODBLINK)%20-c%20myapp.env%3Dci

.PHONY: db-migrate db-ci-apply db-setup db-credenziali

# Si ferma PRIMA di Liquibase se manca la password: con un --password vuoto
#   l'errore arriverebbe dal driver JDBC, e non direbbe che cosa manca.
db-credenziali:
	@test -n "$(DB_PASS)" || { echo "⛔ DB_PASS (o DB_PASSWORD) non impostata per l'utente $(DB_USER)."; exit 1; }

db-migrate: db-credenziali
	@echo "==> Liquibase base update (esclusi i contesti test e provision)…"
	$(LIQUIBASE) \
	  --url="$(JDBC_BASE)$(OPTS_NODBLINK)" \
	  --username="$(DB_USER)" \
	  --password="$(DB_PASS)" \
	  --changeLogFile="$(CHANGELOG)" \
	  update --contexts="!test AND !provision"

db-ci-apply: db-credenziali
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
