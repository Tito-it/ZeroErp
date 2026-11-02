-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test NOTIFY cambio reparto:
--
--   Precondizioni:
--     1. Qualifica DIPENDENTE esiste
--     2. Un operatore umano costruito, con la sua risorsa umana
--     3. Almeno due unita' organizzative attive
--
--   Funzione fn_notify_cambio_reparto:
--     4. Setup: risorsa con unita' organizzativa
--     5. fn_notify con uo valide -> esegue senza errore
--     6. fn_notify con uo NULL -> esegue senza errore
--     7. fn_notify risorsa senza bridge -> esegue senza errore
--
--   Trigger trg_risorse_umane_z90_notify_cambio_reparto_upd:
--     8. Trigger presente su risorse_umane
--     9. UPDATE unita_organizzativa_id -> trigger esegue senza errore
--    10. UPDATE senza cambio uo -> trigger non interviene (no-op)
--
-- Nota: NOTIFY e' consegnato solo al COMMIT. Poiche' pgTAP
--   esegue in transazione con ROLLBACK, non possiamo verificare
--   la ricezione del messaggio. Verifichiamo che la catena
--   funzione-trigger esegue correttamente senza errore.
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- =========================================================
-- 1) Precondizione: qualifica DIPENDENTE
-- =========================================================
CREATE TEMP TABLE _t_qualifica AS
SELECT id AS qualifica_id
  FROM config.qualifiche
 WHERE codice_interno = 'DIPENDENTE'
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_qualifica) = 1,
    '1. Esiste la qualifica DIPENDENTE'
);

-- =========================================================
-- 2) Precondizione: un operatore UMANO, con la sua risorsa umana
-- =========================================================
-- ⛔ 2026-09-23: il file PESCAVA il soggetto del gestore e gli dava a mano il
--   ruolo RIS_UMANA. Su un database ricostruito dai changelog il gestore non
--   c'e' (dato di macchina), e la fixture moriva su «soggetto_id mancante per
--   il ruolo RIS_UMANA». Ed era anche il soggetto sbagliato: una persona
--   giuridica come risorsa umana, senza utente — mentre il NOTIFY porta
--   proprio l'auth_user_id del «ponte». Ora la risorsa umana e' quella di un
--   operatore costruito dal percorso di produzione, ponte compreso.
CREATE TEMP TABLE _t_operatore AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('cambio reparto');

SELECT ok(
    (SELECT risorsa_umana_id IS NOT NULL AND auth_user_id IS NOT NULL FROM _t_operatore),
    '2. Costruito un operatore umano con la sua risorsa umana'
);

-- =========================================================
-- 3) Precondizione: almeno 2 unita' organizzative attive
-- =========================================================
CREATE TEMP TABLE _t_uo AS
SELECT id AS uo_id
  FROM config.unita_organizzative
 WHERE attivo = true
 ORDER BY id
 LIMIT 2;

SELECT ok(
    (SELECT count(*) FROM _t_uo) = 2,
    '3. Trovate almeno 2 unita'' organizzative attive'
);

-- =========================================================
-- 4) Setup: risorsa con unita' organizzativa
-- =========================================================
CREATE TEMP TABLE _t_risorsa AS
SELECT o.risorsa_umana_id AS id FROM _t_operatore o;

-- Assicura stato pulito: attiva, prima uo
UPDATE anagrafiche.risorse_umane
   SET attivo = true,
       valido_dal = script.fn_data_operativa(),
       valido_al = NULL,
       unita_organizzativa_id = (SELECT uo_id FROM _t_uo LIMIT 1)
 WHERE id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT count(*) FROM _t_risorsa) = 1,
    '4. Setup: risorsa umana con unita'' organizzativa'
);

-- =========================================================
-- 5) fn_notify: cambio uo valido -> esegue senza errore
-- =========================================================
SELECT lives_ok(
    format(
        'SELECT anagrafiche.fn_notify_cambio_reparto(%s, %s, %s)',
        (SELECT id FROM _t_risorsa),
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1),
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1 OFFSET 1)
    ),
    '5. fn_notify: cambio uo valido -> esegue senza errore'
);

-- =========================================================
-- 6) fn_notify: uo NULL -> esegue senza errore
-- =========================================================
SELECT lives_ok(
    format(
        'SELECT anagrafiche.fn_notify_cambio_reparto(%s, NULL::integer, %s)',
        (SELECT id FROM _t_risorsa),
        (SELECT uo_id FROM _t_uo LIMIT 1)
    ),
    '6. fn_notify: uo NULL -> esegue senza errore'
);

-- =========================================================
-- 7) fn_notify: risorsa senza bridge -> esegue senza errore
--    (auth_user_id sara' NULL nel payload)
-- =========================================================
-- Usa un ID fittizio senza bridge
SELECT lives_ok(
    format(
        'SELECT anagrafiche.fn_notify_cambio_reparto(%s, %s, %s)',
        (SELECT COALESCE(MAX(id), 0) + 99999 FROM anagrafiche.risorse_umane),
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1),
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1 OFFSET 1)
    ),
    '7. fn_notify: risorsa senza bridge -> esegue senza errore'
);

-- =========================================================
-- 8) Trigger presente su risorse_umane
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'anagrafiche'
           AND c.relname = 'risorse_umane'
           AND t.tgname = 'trg_risorse_umane_z90_notify_cambio_reparto_upd'
           AND NOT t.tgisinternal
    ),
    '8. Trigger notify_cambio_reparto presente su risorse_umane'
);

-- =========================================================
-- 9) UPDATE unita_organizzativa_id -> trigger esegue senza errore
-- =========================================================
SELECT lives_ok(
    format(
        'UPDATE anagrafiche.risorse_umane SET unita_organizzativa_id = %s WHERE id = %s',
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1 OFFSET 1),
        (SELECT id FROM _t_risorsa)
    ),
    '9. Trigger: UPDATE unita_organizzativa_id -> esegue senza errore'
);

-- =========================================================
-- 10) UPDATE senza cambio uo -> trigger non interviene
-- =========================================================
-- Ripetiamo lo stesso valore: il WHEN clause (IS DISTINCT FROM) non scatta
SELECT lives_ok(
    format(
        'UPDATE anagrafiche.risorse_umane SET unita_organizzativa_id = %s WHERE id = %s',
        (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1 OFFSET 1),
        (SELECT id FROM _t_risorsa)
    ),
    '10. Trigger: UPDATE stesso uo_id -> nessun errore (WHEN non scatta)'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
