-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_user_profile - top-level ruolo_applicativo
-- GUC-aware (post migration 20260421-05).
--
-- Contesto:
--   Fix bug §13.7 pr-b-shop-b2c: utente multi-veste
--   (OPERATORE + CLIENTE_PORTALE) loggato su canale portale
--   riceveva top-level='OPERATORE' invece di 'CLIENTE_PORTALE'
--   perche' il campo veniva popolato dall'identita OPERATORE
--   caricata dalla query iniziale, ignorando il contesto di sessione.
--   Post-fix il top-level legge app.ruolo_applicativo con fallback
--   all'identita OPERATORE (tool/cron/psql).
--
-- Semantica attesa:
--   - GUC app.ruolo_applicativo popolata -> top-level = GUC
--   - GUC vuota/assente -> top-level = ruolo_applicativo dell'identita
--     OPERATORE caricata (fallback legacy)
--   - User senza identita OPERATORE -> raise E_ADMIN_VALIDAZIONE
--     (comportamento pre-fix preservato)
--
-- Indice test (1..4):
--    1. Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE
--    2. GUC vuota + user con identita OPERATORE -> top-level=OPERATORE
--    3. Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE
--    4. Regressione: GUC vuota + user senza OPERATORE -> raise
--       E_ADMIN_VALIDAZIONE
--
-- Fixture (rev 2026-09-23): un operatore UMANO costruito
-- (dbops.fn_pgtap_crea_operatore_umano) e due clienti costruiti, i cui
-- ruoli CL non hanno nessuna identita' per costruzione. Per il caso
-- multi-veste aggiungo all'operatore un'identita' CLIENTE_PORTALE sul
-- primo; per il caso 4 creo un fresh auth_user + identita'
-- CLIENTE_PORTALE (senza OPERATORE) sul secondo.
-- ⛔ Prima: l'utente 1 («tid», che in CI non esiste) e «un SR-CL libero»
--   pescato fra i clienti, con due rami `skip` se non ce n'erano.
--
-- BEGIN + ROLLBACK isolamento completo.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- =========================================================
-- Setup: l'operatore e i due ruoli CL si COSTRUISCONO.
-- =========================================================
-- ⛔ 2026-09-23: il file usava l'utente 1 — «tid, che ha identita' OPERATORE
--   via seed» — e su un database ricostruito quell'utente non c'e': la
--   fixture moriva su «auth_user con id=1 non trovato». Ora l'operatore e'
--   UMANO e costruito dal percorso di produzione.
CREATE TEMP TABLE _t_tid AS
SELECT ou.auth_user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('profilo GUC') ou;

-- Due clienti: i loro ruoli CL non hanno identita' per costruzione, e sono
-- quelli su cui nascono le vesti CLIENTE_PORTALE dei casi 1 e 4. Il contesto
-- e' aperto dalla riga sopra: il primo lo da' il mondo (ramo B), il secondo il
-- builder atomico.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('profilo GUC 1');

CREATE TEMP TABLE _t_cli_2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('profilo GUC 2');

CREATE TEMP TABLE _t_sr_cl_libero AS
SELECT m.cliente_soggetto_ruolo_id AS sr_id FROM _t_mondo m;

-- Aggiungo all'operatore un'identita' CLIENTE_PORTALE (setup multi-veste).
-- L'insert scatta il guard coerenza: il ruolo CL e' di un cliente vero.
-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale(t.auth_user_id, (SELECT sr_id FROM _t_sr_cl_libero), 'CLIENTE_PORTALE', true) FROM _t_tid t
    ) AS v;
END
$veste$;

-- =========================================================
-- 1) Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE
-- =========================================================
SET LOCAL app.ruolo_applicativo = 'CLIENTE_PORTALE';

SELECT is(
    (script.fn_get_user_profile((SELECT auth_user_id FROM _t_tid)) ->> 'ruolo_applicativo'),
    'CLIENTE_PORTALE',
    '1. Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE'
);

-- =========================================================
-- 2) GUC vuota + user con identita OPERATORE -> top-level=OPERATORE
-- =========================================================
-- SET LOCAL a '' simula GUC non settata (NULLIF('','')=NULL).
SET LOCAL app.ruolo_applicativo = '';

SELECT is(
    (script.fn_get_user_profile((SELECT auth_user_id FROM _t_tid)) ->> 'ruolo_applicativo'),
    'OPERATORE',
    '2. GUC vuota + user con identita OPERATORE -> top-level=OPERATORE (fallback)'
);

-- =========================================================
-- 3) Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE
-- =========================================================
-- Rimuovo l'identita CLIENTE_PORTALE aggiunta dal setup per simulare
-- single-veste (solo OPERATORE). DELETE perche' UPDATE attivo=false
-- scatenerebbe altro trigger; in transazione BEGIN il DELETE e'
-- rollbackato.
DELETE FROM anagrafiche.identita_digitali
 WHERE auth_user_id = (SELECT auth_user_id FROM _t_tid)
   AND ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo;

SET LOCAL app.ruolo_applicativo = 'OPERATORE';

SELECT is(
    (script.fn_get_user_profile((SELECT auth_user_id FROM _t_tid)) ->> 'ruolo_applicativo'),
    'OPERATORE',
    '3. Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE'
);

-- =========================================================
-- 4) Regressione: GUC vuota + user senza identita OPERATORE
--    -> raise E_ADMIN_VALIDAZIONE (guard invariato).
-- =========================================================
-- Creo fresh auth_user + identita CLIENTE_PORTALE (senza OPERATORE),
-- sul ruolo CL del secondo cliente costruito.
CREATE TEMP TABLE _t_sr_cl_libero_2 AS
SELECT c.soggetto_ruolo_id AS sr_id FROM _t_cli_2 c;

CREATE TEMP TABLE _t_au_portale_only (auth_user_id int);
DO $pgtap$
DECLARE
    v_au     int;
    v_sr_cl  bigint;
BEGIN
    SELECT sr_id INTO v_sr_cl FROM _t_sr_cl_libero_2;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_profile_portale_only_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    PERFORM anagrafiche.fn_crea_veste_portale(v_au, v_sr_cl, 'CLIENTE_PORTALE', true);

    INSERT INTO _t_au_portale_only (auth_user_id) VALUES (v_au);
END
$pgtap$;

SET LOCAL app.ruolo_applicativo = '';

-- ⚠️ Il discriminante e' il frammento stabile della frase (2026-09-23): il
--   throws_ok(sql, NULL, NULL) di prima accettava anche un permesso negato o
--   il crash del guard, e lo stesso codice E_ADMIN_VALIDAZIONE esce anche per
--   «auth_user non trovato».
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_get_user_profile(%L::int) $sql$,
        (SELECT auth_user_id FROM _t_au_portale_only)
    ),
    '%Nessuna identita OPERATORE%',
    '4. Regressione: user senza identita OPERATORE -> raise E_ADMIN_VALIDAZIONE'
);

SELECT * FROM finish();
ROLLBACK;
