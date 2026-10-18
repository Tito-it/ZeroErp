-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce fornitori, vettori e clienti di
--   soggetti nuovi, e prova il guard di config.tipi_ruoli con un UPDATE del
--   catalogo: come `zeroerp_app` il catalogo non si scrive. Il perimetro
--   dell'emittente (RLS di anagrafiche.clienti) NON e' il soggetto di questo
--   file: lo prova script/test-search-scope-interno-v1 con FORCE ROW LEVEL
--   SECURITY. Qui si prova la REGOLA su quale tabella fa esistere un ruolo.
-- pgTAP test per Zero ERP
--
-- La regola unica della ricerca universale: chi si vede.
-- Brief: brief-db-codici-non-trovato-email-e-permessi (R-6, Q-1, Q-2, Q-3, Q-5)
--
-- Elenco test (plan 17):
--   il catalogo (Q-1)
--    1) ogni entita_esistenza valorizzata e' una TABELLA viva con soggetto_ruolo_id
--    2) CL -> anagrafiche.clienti, FO -> anagrafiche.fornitori: le tabelle che
--       leggono i rami del dettaglio
--    3) * guard: una vista come entita_esistenza -> E_TIPI_RUOLI_ENTITA_INVALIDA
--    4) * guard: una tabella senza soggetto_ruolo_id -> E_TIPI_RUOLI_ENTITA_INVALIDA
--    5) * CHECK di forma: un nome che il guard risolve ma fuori forma -> 23514
--   la regola sui ruoli (R-6)
--    6) * FO senza la riga in fornitori: dettaglio NULL (era righe: [])
--    7) * ...e assente dalla lista (prima compariva)
--    8)   FO con il fornitore: dettaglio con la sua riga
--    9)   ...e presente nella lista
--   10) * VT senza la riga in vettori: dettaglio NULL
--   11)   ruolo senza entita_esistenza (RE): dettaglio con una riga (ramo ELSE)
--   12)   ...e presente nella lista
--   lo stato dell'entita' non conta (Q-3)
--   13)   fornitore disattivato: il dettaglio lo mostra, attivo = false
--   14)   cliente CHIUSO: il dettaglio lo mostra, con lo stato CH
--   15)   ...e la lista lo trova
--   il ruolo (Q-2)
--   16) * lista su un ruolo non ricercabile (EF) -> E_TIPO_RUOLO_NON_RICERCABILE
--   17) * lista su un tipo ruolo inesistente -> E_TIPO_RUOLO_NON_TROVATO
--       (prima la lista rispondeva zero righe)
--
-- Scopo:
--  - fino al 2026-10-10 la check scriveva 'CL' come letterale: un CL senza
--    clienti spariva, un FO senza fornitore compariva. I test 6-12 provano
--    che la regola ora legge il catalogo (config.tipi_ruoli.entita_esistenza)
--    per OGNI ruolo, con soggetti costruiti nel test;
--  - 1-5 presidiano il catalogo: il guard vale in scrittura, una tabella
--    cancellata dopo la vede solo il test 1;
--  - 13-15: un rapporto finito si ritrova (decisione di Tid, Q-3).
--
-- ⚠️ soggetti.attivo NON e' nella regola (Q-5), e qui non c'e' un test che lo
--   provi: il modello non ammette un soggetto-ruolo col soggetto spento
--   (trg_soggetti_a10_soggetti_ruoli_block_deact_upd,
--   trg_soggetti_ruoli_a10_soggetti_require_attivo_ins_upd), quindi il caso
--   non si puo' costruire.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: soggetti PG nuovi
--   (dbops.fn_pgtap_crea_soggetto_pg) con una ragione sociale che porta un
--   termine che nessun altro soggetto ha, ruoli con
--   dbops.fn_pgtap_crea_soggetto_ruolo, il cliente chiuso con
--   dbops.fn_pgtap_crea_cliente. Nessun confronto con i dati presenti.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- Contesto applicativo: un'azienda col suo operatore, costruita (su un
-- database ricostruito dai changelog non ce n'e' nessuna da pescare), e il
-- contesto aperto su di lui. Da owner, senza FORCE ROW LEVEL SECURITY, la RLS
-- di clienti non filtra: il perimetro non e' il soggetto di questo file (vedi
-- l'intestazione). Il cliente chiuso, costruito dopo, si lega a quest'azienda
-- (trigger z90 del billing account).
CREATE TEMP TABLE _op ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op));
END $ctx$;

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): si pinna il codice, non la frase.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE TEMP TABLE _ruoli ON COMMIT DROP AS
SELECT tr.codice_interno, tr.id FROM config.tipi_ruoli tr;

-- ============================================================
-- 1-5) Il catalogo
-- ============================================================

-- 1) Sul catalogo VIVO: il guard vale in scrittura, e una tabella cancellata
--    o sostituita da una vista dopo non passa di li'.
SELECT is(
    (SELECT count(*)
       FROM config.tipi_ruoli tr
       LEFT JOIN pg_class c ON c.oid = to_regclass(tr.entita_esistenza)
      WHERE tr.entita_esistenza IS NOT NULL
        AND (c.oid IS NULL
             OR c.relkind NOT IN ('r', 'p')
             OR NOT EXISTS (SELECT 1 FROM pg_attribute a
                             WHERE a.attrelid = c.oid
                               AND a.attname = 'soggetto_ruolo_id'
                               AND a.attnum > 0 AND NOT a.attisdropped))),
    0::bigint,
    '1. ogni entita_esistenza valorizzata e'' una tabella viva con soggetto_ruolo_id'
);

-- 2) I rami CL e FO di fn_get_search_detail leggono anagrafiche.clienti e
--    anagrafiche.fornitori: se il catalogo dicesse un'altra tabella, verifica
--    d'esistenza e righe del dettaglio leggerebbero due cose diverse.
SELECT is(
    (SELECT string_agg(tr.codice_interno || '=' || tr.entita_esistenza, ',' ORDER BY tr.codice_interno)
       FROM config.tipi_ruoli tr
      WHERE tr.codice_interno IN ('CL', 'FO')),
    'CL=anagrafiche.clienti,FO=anagrafiche.fornitori',
    '2. CL e FO esistono per le tabelle che leggono i rami del dettaglio'
);

-- 3) Una vista non e' ammessa: la RLS e' della tabella.
SELECT is(
    pg_temp.codice_errore($q$
        UPDATE config.tipi_ruoli
           SET entita_esistenza = 'anagrafiche.vw_clienti_codice_ba'
         WHERE codice_interno = 'CL'$q$),
    'E_TIPI_RUOLI_ENTITA_INVALIDA',
    '3. * guard: una vista come entita_esistenza -> E_TIPI_RUOLI_ENTITA_INVALIDA'
);

-- 4) Una tabella senza soggetto_ruolo_id non sa a chi appartiene.
SELECT is(
    pg_temp.codice_errore($q$
        UPDATE config.tipi_ruoli
           SET entita_esistenza = 'config.utilities'
         WHERE codice_interno = 'RE'$q$),
    'E_TIPI_RUOLI_ENTITA_INVALIDA',
    '4. * guard: una tabella senza soggetto_ruolo_id -> E_TIPI_RUOLI_ENTITA_INVALIDA'
);

-- 5) La forma schema.tabella (minuscola) la pretende il CHECK.
--    ⚠️ Il guard e' BEFORE ROW e parla PRIMA del CHECK: un nome che il guard
--    rifiuta (senza schema, tabella inesistente) non arriva mai al CHECK. Per
--    provare il CHECK serve un nome che il guard RISOLVE e che la forma
--    rifiuta: 'anagrafiche.Clienti' e' la tabella vera (to_regclass piega le
--    maiuscole), ma non e' la forma che il seed e il predicato si aspettano.
--    Il CHECK resta la rete per le strade che non passano dai trigger.
SELECT throws_ok(
    $q$UPDATE config.tipi_ruoli SET entita_esistenza = 'anagrafiche.Clienti' WHERE codice_interno = 'RE'$q$,
    '23514',
    NULL,
    '5. * CHECK di forma: un nome che il guard risolve ma fuori forma -> 23514'
);

-- ============================================================
-- Fixture: i soggetti
-- ============================================================
CREATE TEMP TABLE _sr ON COMMIT DROP AS
SELECT 'FO_NUDO'  AS caso, 'ZQRUVFONUDO'  AS termine, 'FO'::varchar AS ruolo UNION ALL
SELECT 'FO_PIENO',          'ZQRUVFOPIENO',           'FO'          UNION ALL
SELECT 'VT_NUDO',           'ZQRUVVTNUDO',            'VT'          UNION ALL
SELECT 'RE',                'ZQRUVRESELL',            'RE';

ALTER TABLE _sr ADD COLUMN soggetto_id uuid, ADD COLUMN sr_id bigint;

UPDATE _sr
   SET soggetto_id = dbops.fn_pgtap_crea_soggetto_pg(termine || ' pgTAP regola unica');

UPDATE _sr
   SET sr_id = dbops.fn_pgtap_crea_soggetto_ruolo(soggetto_id, ruolo);

-- Il fornitore del soggetto FO_PIENO, dalla madre (rev 2026-10-18, 2b-1 lotto
-- 4 di brief-db-processi-accensione-per-ambiente): riusa il ruolo del builder,
-- codice dal trigger, nasce VE. Poi lo stato AT, con un UPDATE come ogni
-- passaggio di stato.
DO $fo$
BEGIN
    PERFORM anagrafiche.fn_crea_fornitore(s.soggetto_id) FROM _sr s WHERE s.caso = 'FO_PIENO';
END
$fo$;

UPDATE anagrafiche.fornitori f
   SET stato_fornitore_id = (SELECT sf.id FROM config.stati_fornitore sf WHERE sf.codice_interno = 'AT')
  FROM _sr s
 WHERE s.caso = 'FO_PIENO'
   AND f.soggetto_ruolo_id = s.sr_id;

-- Il cliente CHIUSO (Q-3): stato CH, attivazione e chiusura dal builder.
CREATE TEMP TABLE _cl_chiuso ON COMMIT DROP AS
SELECT c.*, 'ZQRUVCLCHIUSO'::text AS termine
  FROM dbops.fn_pgtap_crea_cliente(
           'ZQRUVCLCHIUSO',
           (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'),
           NULL,
           'CH') c;

-- ============================================================
-- 6-12) La regola sui ruoli
-- ============================================================

-- 6) FO senza fornitore: il modello lo ammette (uq_fornitori_soggetto_ruolo_id
--    dice 0..1, nessun trigger pretende la riga). Ora e' un «non c'e'».
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _sr WHERE caso = 'FO_NUDO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'FO')),
    NULL::jsonb,
    '6. * FO senza la riga in fornitori: dettaglio NULL (era righe: [])'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _sr WHERE caso = 'FO_NUDO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'FO'))),
    0::bigint,
    '7. * FO senza fornitore: assente dalla lista, come un CL senza clienti'
);

SELECT is(
    jsonb_array_length(script.fn_get_search_detail(
        (SELECT soggetto_id FROM _sr WHERE caso = 'FO_PIENO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'FO')) -> 'righe'),
    1,
    '8. FO con il fornitore: dettaglio con la sua riga'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _sr WHERE caso = 'FO_PIENO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'FO'))),
    1::bigint,
    '9. FO con il fornitore: presente nella lista'
);

-- 10) VT: stessa regola, altra tabella (anagrafiche.vettori). Nessun ramo del
--     dettaglio nomina VT: lo dice il catalogo.
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _sr WHERE caso = 'VT_NUDO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'VT')),
    NULL::jsonb,
    '10. * VT senza la riga in vettori: dettaglio NULL'
);

-- 11-12) RE non ha entita_esistenza: il soggetto-ruolo si mostra se esiste.
SELECT is(
    jsonb_array_length(script.fn_get_search_detail(
        (SELECT soggetto_id FROM _sr WHERE caso = 'RE'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'RE')) -> 'righe'),
    1,
    '11. ruolo senza entita_esistenza (RE): dettaglio con una riga (ramo ELSE)'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _sr WHERE caso = 'RE'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'RE'))),
    1::bigint,
    '12. ruolo senza entita_esistenza (RE): presente nella lista'
);

-- ============================================================
-- 13-15) Lo stato dell'entita' non conta (Q-3)
-- ============================================================

UPDATE anagrafiche.fornitori f
   SET attivo = false
  FROM _sr s
 WHERE s.caso = 'FO_PIENO'
   AND f.soggetto_ruolo_id = s.sr_id;

SELECT is(
    (script.fn_get_search_detail(
        (SELECT soggetto_id FROM _sr WHERE caso = 'FO_PIENO'),
        (SELECT id FROM _ruoli WHERE codice_interno = 'FO')) -> 'righe' -> 0 ->> 'attivo'),
    'false',
    '13. fornitore disattivato: il dettaglio lo mostra, con attivo = false'
);

SELECT is(
    (script.fn_get_search_detail(
        (SELECT soggetto_id FROM _cl_chiuso),
        (SELECT id FROM _ruoli WHERE codice_interno = 'CL')) -> 'righe' -> 0 ->> 'stato_codice_interno'),
    'CH',
    '14. cliente chiuso: il dettaglio lo mostra, con lo stato CH'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _cl_chiuso),
        (SELECT id FROM _ruoli WHERE codice_interno = 'CL'))),
    1::bigint,
    '15. cliente chiuso: la lista lo trova'
);

-- ============================================================
-- 16-17) Il ruolo (Q-2)
-- ============================================================

SELECT is(
    pg_temp.codice_errore(format(
        $q$SELECT * FROM script.fn_search_soggetti_universale('ZQRUV', %s)$q$,
        (SELECT id FROM _ruoli WHERE codice_interno = 'EF'))),
    'E_TIPO_RUOLO_NON_RICERCABILE',
    '16. * lista su un ruolo non ricercabile (EF) -> E_TIPO_RUOLO_NON_RICERCABILE'
);

SELECT is(
    pg_temp.codice_errore(format(
        $q$SELECT * FROM script.fn_search_soggetti_universale('ZQRUV', %s)$q$,
        (SELECT COALESCE(max(id), 0) + 1000 FROM _ruoli))),
    'E_TIPO_RUOLO_NON_TROVATO',
    '17. * lista su un tipo ruolo inesistente -> E_TIPO_RUOLO_NON_TROVATO (prima zero righe)'
);

SELECT * FROM finish();
ROLLBACK;
