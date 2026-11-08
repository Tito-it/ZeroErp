-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum — la natura di EVENTO_ASSET su dbdev e scratch (Z-b / D-12 di Tid, 2026-11-08)
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto Z, giro Z.1.
--
-- Che cosa: config.sorgenti.categoria dice la natura del tipo, DOCUMENTO o EVENTO
-- (decisione Z-b). EVENTO_ASSET ha ancora RIGA, il valore dei tipi di riga
-- ritirati. sorgenti.csv porta EVENTO, ma il mirror (80_data/20251002-21) non lo
-- puo' scrivere: categoria e' sotto lucchetto (trg_sorgenti_a10_lock_columns_upd,
-- E_CODICE_NON_MODIFICABILE), e un mirror di 80_data gira prima di ogni changeSet
-- datato oggi, quindi la correzione non puo' stare in un changeSet.
-- Da zero (CI) non serve: la riga nasce dal mirror con un INSERT, gia' EVENTO.
--
-- Come: in UNA transazione, con la porta del lucchetto aperta solo qui
-- (SET LOCAL zeroerp.allow_lock_columns_override = 'on'). Si aggiorna SOLO
-- EVENTO_ASSET, e solo se e' ancora RIGA; poi si verifica che nessun tipo abbia
-- RIGA: altrimenti si ferma e non scrive niente. Idempotente: rilanciato aggiorna
-- zero righe.
-- Quando: PRIMA del migrate del giro Z.1, su ciascun database.
-- Chi: Tid, come zeroerp_owner. Solo sviluppo.
--
-- Uso:
--   set -a; . db/internal.env; set +a          (dbdev)
--   psql -v ON_ERROR_STOP=1 -f docs/it/dev/work-done/sql-una-tantum-sorgenti-categoria-evento.sql
--   set -a; . db/internal.ruoli.env; set +a    (scratch zeroerp_ruoli)
--   psql -v ON_ERROR_STOP=1 -f docs/it/dev/work-done/sql-una-tantum-sorgenti-categoria-evento.sql
-- ------------------------------------------------------------
\set ON_ERROR_STOP on

BEGIN;

SET LOCAL ROLE zeroerp_owner;
SET LOCAL zeroerp.allow_lock_columns_override = 'on';

UPDATE config.sorgenti
   SET categoria = 'EVENTO'
 WHERE codice_interno = 'EVENTO_ASSET'
   AND categoria = 'RIGA';

DO $chk$
DECLARE
    v_restano bigint;
BEGIN
    SELECT count(*) INTO v_restano FROM config.sorgenti WHERE categoria = 'RIGA';
    IF v_restano > 0 THEN
        RAISE EXCEPTION 'config.sorgenti: % tipi hanno ancora categoria RIGA: niente e'' stato scritto', v_restano;
    END IF;
END
$chk$;

SELECT codice_interno, categoria FROM config.sorgenti WHERE codice_interno = 'EVENTO_ASSET';

COMMIT;
