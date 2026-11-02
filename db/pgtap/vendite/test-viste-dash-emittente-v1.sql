-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Fase E del cantiere «perimetro emittente», R-3 + R-4: l'emittente nella
-- riga delle cinque liste che restano.
-- Brief: brief-db-perimetro-emittente-fase-e-e-ricerca.md
--
-- Elenco test (plan 12):
--   0) PRECONDIZIONE: le sei liste esistono in catalogo
--   1) vw_dash_fatturazione_documenti ha emittente_ragione_sociale
--   2) vw_dash_aperto_documenti           idem
--   3) vw_dash_backlog_documenti          idem
--   4) vw_dash_competenza_errori          idem
--   5) vw_dash_competenza_attivita        idem
--   (security_invoker: presidiato da rls/test-rls-viste-security-invoker.sql)
--   7) sei righe di catalogo, una per lista
--   8) ...e sono nella forma giusta (sorgente, attiva, non sensibile, i18n)
--   9) * coerenza catalogo <-> vista: il campo dichiarato ESISTE nella vista
--  10) il flag multi_emittente e' acceso SOLO sulle liste dichiarate qui
--      (rev 2026-08-18: tutte e sei, per decisione di Tid)
--  11) dbops.vw_liste_multi_emittente_non_certificate resta a zero righe
--
-- Scopo, e perche' i due test con l'asterisco sono quelli che guadagnano il
-- pane:
--
--  ⭐ IL PEZZO PIU' IMPORTANTE DI QUESTO RAGIONAMENTO NON VIVE PIU' QUI
--     (rev 2026-09-07): sta in db/pgtap/rls/test-rls-viste-security-invoker.sql,
--     che lo fa per TUTTE le viste che toccano dati in RLS — non per le cinque
--     di questo file, e senza elencarne nessuna. Il
--     perche' resta scritto qui sotto, perche' e' la ragione per cui esiste.
--     `security_invoker = on` NON e' visibile in pg_get_viewdef: chi ricrea
--     una vista partendo dalla definizione stampata la perde senza nessun
--     avviso. Su queste cinque viste ci si appoggia lo scope emittente —
--     perderla significa che la RLS smette di filtrare per chi legge, cioe'
--     che ognuno vede i documenti di tutti. E' esattamente il difetto che
--     nessun test funzionale trova: la vista continua a rispondere, risponde
--     solo di piu'. Cinque CREATE OR REPLACE in un colpo solo sono cinque
--     occasioni di sbagliarlo, e questo test le copre tutte.
--
--  ⭐ IL 9 E' IL PONTE FRA LE DUE META'. Il catalogo dice al frontend quale
--     campo leggere; la vista lo produce. Sono due file diversi, aggiornati da
--     due changeSet diversi, e nessuno dei due sa dell'altro: se il seed
--     arriva e la vista no, la migrazione e' verde, il catalogo e' verde, e la
--     colonna a video e' vuota. Senza errori da nessuna parte. Il test lega le
--     due meta' e rende quel disallineamento rumoroso.
--
--  ⚠️ LA LISTA 12 (lotti) NON ENTRA NEL TEST 9, ed e' voluto: non ha nessuna
--     vista: il repository del backend costruisce l'SQL direttamente su
--     vendite.fatturazione_lotti. Metterla nella mappa vorrebbe dire inventare
--     una vista che non esiste; lasciarla fuori in silenzio vorrebbe dire
--     fingere che sia coperta. E' fuori, ed e' scritto perche'.
--
--  ⚠️ IL 10 NON E' UN DETTAGLIO BUROCRATICO. Il flag multi_emittente si
--     GUADAGNA: si accende lista per lista quando la colonna mostra un nome su
--     dati veri, mai insieme al seed della colonna (§7, decisione 3 del brief
--     madre). Se un giorno questo test diventa rosso senza che nessuno abbia
--     fatto quel lavoro, e' il segnale che serve.
--
--  🔵 La lista 42 (gruppi fatturabili) e' la PILOTA, arrivata il 2026-08-17 con
--     il changeSet 20260818-15: qui entra solo come sesta riga di catalogo e
--     nella mappa del test 9. Il suo test dedicato e'
--     db/pgtap/ui/test-lista-competenza-gruppi-colonna-emittente-v1.sql.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
-- Le cinque viste toccate da R-4. La pilota (vw_dash_competenza_gruppi) non
-- c'e': era gia' a posto e ha il suo file.
CREATE TEMP TABLE _t_viste (vista text) ON COMMIT DROP;
INSERT INTO _t_viste (vista) VALUES
    ('vw_dash_fatturazione_documenti'),
    ('vw_dash_aperto_documenti'),
    ('vw_dash_backlog_documenti'),
    ('vw_dash_competenza_errori'),
    ('vw_dash_competenza_attivita');

-- Le liste che devono portare l'emittente, e la vista da cui la riga nasce.
-- ⚠️ La 12 (lotti) NON e' qui: non ha vista, il repository legge la tabella.
CREATE TEMP TABLE _t_liste_vista (lista_id integer, vista text) ON COMMIT DROP;
INSERT INTO _t_liste_vista (lista_id, vista) VALUES
    (39, 'vw_dash_aperto_documenti'),
    (40, 'vw_dash_backlog_documenti'),
    (41, 'vw_dash_competenza_errori'),
    (42, 'vw_dash_competenza_gruppi'),
    (43, 'vw_dash_competenza_attivita');

-- Tutte e sei le liste, lotti compresa: il catalogo le vuole tutte.
CREATE TEMP TABLE _t_liste (lista_id integer) ON COMMIT DROP;
INSERT INTO _t_liste (lista_id) VALUES (12), (39), (40), (41), (42), (43);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 0) Senza le liste in catalogo i test 7-10 sarebbero verdi per sottrazione.
SELECT is(
    (SELECT count(*) FROM ui.lista_definizione ld
      WHERE ld.id IN (SELECT lista_id FROM _t_liste)),
    6::bigint,
    '0. PRECONDIZIONE: le sei liste della Fase E esistono in catalogo'
);

SELECT has_column(
    'vendite', 'vw_dash_fatturazione_documenti', 'emittente_ragione_sociale',
    '1. vw_dash_fatturazione_documenti espone emittente_ragione_sociale'
);

SELECT has_column(
    'vendite', 'vw_dash_aperto_documenti', 'emittente_ragione_sociale',
    '2. vw_dash_aperto_documenti espone emittente_ragione_sociale (NON ereditata: elencata)'
);

SELECT has_column(
    'vendite', 'vw_dash_backlog_documenti', 'emittente_ragione_sociale',
    '3. vw_dash_backlog_documenti espone emittente_ragione_sociale (anche sui rami resi)'
);

SELECT has_column(
    'vendite', 'vw_dash_competenza_errori', 'emittente_ragione_sociale',
    '4. vw_dash_competenza_errori espone emittente_ragione_sociale'
);

SELECT has_column(
    'vendite', 'vw_dash_competenza_attivita', 'emittente_ragione_sociale',
    '5. vw_dash_competenza_attivita espone emittente_ragione_sociale'
);

-- ⛔ QUI `security_invoker` NON SI PRESIDIA PIU' (rev 2026-09-07), e non e' una
--   rinuncia: lo fa gia' db/pgtap/rls/test-rls-viste-security-invoker.sql, su
--   TUTTE le viste che toccano dati in RLS — anche attraverso altre viste — e
--   leggendo la PROPRIETA' invece della parola. Nessun elenco di nomi.
--   ⚠️ Il doppione locale non aggiungeva copertura, e ne ha tolta: era scritto
--   come confronto di GRAFIA (`security_invoker=on`) ed e' diventato ROSSO su
--   una vista perfettamente sana, riscritta con `= true` — che significa la
--   stessa identica cosa. Due falsi allarmi il 2026-09-07, e una bisezione fra
--   due cantieri per scoprire che non era rotto niente.
--   ⭐ Una seconda sede diverge sempre; questa e' divergiata verso il FALSO
--   ALLARME, che e' il verso che fa spegnere i presidi.


-- 7) Il catalogo: una riga emittente per ciascuna delle sei liste.
SELECT is(
    (SELECT count(*)
       FROM ui.lista_colonna lc
      WHERE lc.lista_id IN (SELECT lista_id FROM _t_liste)
        AND lc.codice = 'emittente_fiscale'),
    6::bigint,
    '7. sei righe di catalogo «emittente_fiscale», una per lista (R-3 + pilota)'
);

-- 8) ...e nella forma giusta. `sensibile = f` non e' un dettaglio: `t` senza
--    grant renderebbe la colonna invisibile a TUTTI, che e' il contrario di
--    quel che serve qui.
SELECT is(
    (SELECT count(*)
       FROM ui.lista_colonna lc
      WHERE lc.lista_id IN (SELECT lista_id FROM _t_liste)
        AND lc.codice = 'emittente_fiscale'
        AND lc.campo_sorgente = 'emittente_ragione_sociale'
        AND lc.attivo
        AND lc.sensibile IS FALSE
        AND COALESCE(btrim(lc.etichetta_i18n_key), '') <> ''),
    6::bigint,
    '8. le sei righe: sorgente emittente_ragione_sociale, attive, NON sensibili, con chiave i18n'
);

-- 9) * Il ponte fra catalogo e vista. Zero righe = nessun campo dichiarato che
--    la vista non produca.
SELECT is(
    (SELECT count(*)
       FROM _t_liste_vista lv
       JOIN ui.lista_colonna lc
         ON lc.lista_id = lv.lista_id
        AND lc.codice = 'emittente_fiscale'
      WHERE NOT EXISTS (
              SELECT 1
                FROM pg_attribute a
                JOIN pg_class c2 ON c2.oid = a.attrelid
                JOIN pg_namespace n2 ON n2.oid = c2.relnamespace
               WHERE n2.nspname = 'vendite'
                 AND c2.relname = lv.vista
                 AND a.attname = lc.campo_sorgente
                 AND a.attnum > 0
                 AND NOT a.attisdropped
            )),
    0::bigint,
    '9. * coerenza catalogo<->vista: ogni campo dichiarato ESISTE nella vista che lo alimenta'
);

-- 10) Il flag si guadagna dopo, mai insieme al seed della colonna.
--
--     ⭐ Rev 2026-08-18: acceso su TUTTE E SEI, per decisione di Tid
--     (brief perimetro-emittente §13-ter.5 e §13-ter.7).
--     ⚠️ Sulla sola PILOTA il flag ha dietro il giro completo; sulle altre
--     cinque e' stato acceso prima che il backend selezioni la colonna
--     (BE-5), e su `vendite.lotti` il campo non esiste nemmeno in una vista
--     (BE-4). Scritto qui perche' e' qui che qualcuno verra' a chiedersi
--     perche' la colonna e' vuota.
--
--     ⚠️ Si asserisce l'ELENCO e non il conteggio, per la stessa ragione per
--     cui il conteggio non bastava: «una accesa» sarebbe verde anche se
--     l'accesa fosse un'altra. Chi certifica una lista deve venire QUI a
--     scriverne il codice — e' il «prezzo del biglietto» in forma di test.
SELECT is(
    (SELECT COALESCE(array_agg(ld.codice::text ORDER BY ld.codice), '{}'::text[])
       FROM ui.lista_definizione ld
      WHERE ld.id IN (SELECT lista_id FROM _t_liste)
        AND ld.multi_emittente),
    ARRAY['vendite.dash_aperto_documenti',
          'vendite.dash_backlog_documenti',
          'vendite.dash_competenza_commesse',
          'vendite.dash_competenza_errori',
          'vendite.dash_competenza_gruppi',
          'vendite.lotti']::text[],
    '10. multi_emittente acceso solo sulle liste certificate e dichiarate qui'
);

-- 11) Il controllo automatico di P-2b non deve avere niente da dire.
SELECT is(
    (SELECT count(*) FROM dbops.vw_liste_multi_emittente_non_certificate),
    0::bigint,
    '11. vw_liste_multi_emittente_non_certificate a zero righe'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
