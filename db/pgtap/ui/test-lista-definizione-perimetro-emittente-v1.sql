-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il TERZO CASO del perimetro emittente di una lista
--       ui.lista_definizione.perimetro_emittente   (20260902-01)
--       seed: colonna `perimetro_emittente` del CSV   (20260507-06, dal 18-09;
--             il CSV laterale 20260902-02 e' RITIRATO: una tabella, un CSV)
--       ui.fn_resolve_lista_config                 (20260902-03)
--       Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.16
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 1) ⭐ Il risolutore porta la chiave `perimetro_emittente`
-- 2) ⭐ La lista delle famiglie dichiara di NON avere perimetro
-- 3) ⭐ ...e resta `multi_emittente = false`, che e' la verita'
-- 4) ⛔ Dall'APPLICAZIONE quel flag non si scrive affatto: parla il guard
-- 5) ⛔ ...e dietro il guard c'e' il CHECK, per chi il guard lo attraversa
-- 6) ⭐ Le liste globali sono ESATTAMENTE quelle dichiarate qui (elenco, non conteggio)
-- 7) ⛔⛔ La vista di certificazione resta a ZERO righe
-- 8) ⭐ Chi dichiara di non avere emittenti non ne mostra uno per riga (derivato)
--
-- Scopo:
--   ⭐ IL TEST CHE CONTA E' IL 7, ed e' il motivo per cui questa colonna
--   esiste. La strada breve era dichiarare la lista famiglie
--   `multi_emittente = true` — cioe' vantare una capacita' che non ha — e la
--   vista di certificazione l'avrebbe intercettata. Il 7 verifica che la
--   strada lunga NON abbia pagato quel prezzo.
--
--   ⛔ E il 3 e' il suo gemello dal lato opposto: se un domani qualcuno
--   «semplificasse» mettendo `t` al posto della colonna nuova, il 3 diventa
--   rosso prima del 7, e dice perche'.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che il frontend entri davvero senza chiedere
--   l'emittente. La chiave viaggia nella configurazione risolta; chi la legge
--   e' fuori dal database (§11.16, richiesta BE-F9/FE-F7).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1/2/3) La chiave, e cosa dice sulla lista famiglie
-- ============================================================
SELECT ok(
    ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ? 'perimetro_emittente',
    '1) La configurazione risolta porta la chiave `perimetro_emittente`');

SELECT is(
    (ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ->> 'perimetro_emittente'),
    'false',
    '2) La lista delle famiglie dichiara di NON avere un perimetro emittente');

-- ⭐ Il gemello: la strada breve sarebbe stata mettere `t` qui. Se qualcuno la
--   prendesse, questo test lo dice prima che lo dica la vista del test 7.
SELECT is(
    (ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ->> 'multi_emittente'),
    'false',
    '3) ...e resta multi_emittente = false, che e'' la verita'': non ha emittenti da dire');

-- ============================================================
-- 4/5) ⛔ «Non ho emittenti, e so dirti quale sono» — DUE muri
-- ============================================================
-- 🔴 DAVANTI A `multi_emittente` CI SONO DUE PRESIDI, E NON DICONO LA STESSA
--   COSA. Il primo e' il guard trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd:
--   quel flag non si scrive DALL'APPLICAZIONE, punto — si dichiara nel seed.
--   Il secondo e' il CHECK di coerenza, che vale per tutti, migrate compreso.
--
-- ⚠️ Questa distinzione si e' vista SOLO lanciando il test come applicazione:
--   girando da owner il guard esce subito (pg_has_role) e a rifiutare e' il
--   CHECK, quindi un test scritto in quella condizione chiede il 23514 e lo
--   ottiene. In esercizio arriva un P0001, e il test diventa rosso su un
--   database sano. ⛔ Un presidio che passa solo nella veste sbagliata non
--   presidia: prova la veste.
PREPARE incoerente AS
UPDATE ui.lista_definizione SET multi_emittente = TRUE
 WHERE codice = 'vendite.famiglie_documento';

SELECT throws_ok(
    'incoerente', 'P0001',
    NULL,
    '4) Dall''applicazione il flag non si scrive affatto: a rifiutare e'' il guard');

-- ⭐ Il secondo muro si prova sulla STRUTTURA e non sul comportamento: per
--   vederlo agire servirebbe la veste dell'owner, che questo file non ha e non
--   deve avere. Se qualcuno togliesse il CHECK, questo test diventa rosso.
SELECT is(
    (SELECT pg_get_constraintdef(oid)
       FROM pg_constraint
      WHERE conname = 'chk_ui_lista_definizione_perimetro_coerente'),
    'CHECK ((perimetro_emittente OR (NOT multi_emittente)))',
    '5) ...e dietro il guard c''e'' il CHECK, che vale anche per il migrate');

-- ============================================================
-- 6) ⭐ Le liste globali sono esattamente quelle dichiarate qui
-- ============================================================
-- ⚠️ Fino al 2026-09-18 questo test diceva «nessun'altra oltre le famiglie»,
--   ed era un conteggio a zero: verde finche' il CSV aveva una riga, rosso
--   sulla prima riga giusta. Dal 18-09 il CSV ne ha SETTE
--   (brief-db-perimetro-emittente-cataloghi-globali, §3 e D-1), OTTO dal
--   19-09 con `dbops.error_log` (analisi-osservabilita-log), e il test
--   prende la forma del gemello `test-lista-definizione-multi-emittente-v1`
--   test 5: si asserisce l'ELENCO, non il conteggio. Un numero dice «sono
--   sette» e lascia credere che siano le sette giuste; l'elenco dice QUALI, e
--   chi dichiara globale una lista deve venire qui a scriverlo. Il default
--   resta «con perimetro»: una lista nuova che non compare qui nasce come
--   nascevano tutte prima del 2026-09-02, e se qualcuno la dichiarasse
--   globale senza passare di qui il test lo dice per nome.
SELECT is(
    (SELECT COALESCE(array_agg(codice::text ORDER BY codice), '{}'::text[])
       FROM ui.lista_definizione
      WHERE NOT perimetro_emittente),
    ARRAY['amm.processi',
          -- ⭐ 2026-09-27 (brief-db-liste-datatable-grezze, riga 5): i reparti
          --   sono `config.unita_organizzative`, catalogo senza emittente.
          'amm.reparti',
          -- ⭐ 2026-10-02 (brief-db-be-fe-area-accessi, R-DB-A3): una
          --   CREDENZIALE non appartiene a un'azienda — e' una password per
          --   tutte le porte, e un cliente del portale lo e' di chi lo serve.
          --   La lista non ha colonne d'emittente (test 8).
          'anagrafiche.accessi_altri',
          -- ⭐ D-1 (Tid, 2026-09-18): la riga non APPARTIENE a un emittente,
          --   la riga E' l'emittente. Scegliere un emittente per vedere
          --   l'elenco degli emittenti era una domanda senza risposta.
          'anagrafiche.emittenti_fiscali',
          -- ⭐ 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro §2,
          --   righe 3 e 4): le note e le unita' di misura di un ARTICOLO.
          --   L'articolo e' catalogo unico per tutte le aziende, e le note
          --   di catalogo non hanno emittente (le note di un documento di
          --   vendita, `vendite.note`, il perimetro ce l'hanno: D-2).
          'catalogo.articolo_uom',
          'catalogo.note',
          -- ⭐ 2026-09-27 (brief-db-liste-datatable-grezze, riga 9): le sei
          --   liste geografiche leggono cataloghi di `config` senza emittente
          --   ne' RLS — la geografia e' la stessa per tutte le aziende.
          'config.codici_postali',
          'config.comuni',
          'config.province',
          'config.regioni',
          'config.stati',
          'config.toponomastica',
          -- ⭐ 2026-09-27 (Tid, stesso brief §8 punto 7): la matrice utility /
          --   tipi ruolo e' un vocabolario uguale per tutte le aziende. Gli
          --   override per emittente stanno nella lista del suo tab «Utilizzo»
          --   (`config.utilities_tipi_ruolo_usage`, con perimetro).
          'config.utilities_tipi_ruolo',
          -- ⭐ 2026-09-27 (stesso brief, riga 1): una sessione e' di un
          --   UTENTE (`dbops.sessioni_utente`), non di un'azienda.
          'core.sessioni_attive',
          -- ⭐ Diario tecnico di sistema (analisi-osservabilita-log, pezzo E,
          --   2026-09-19): come `storico.audit_log`, la riga non ha nessuna
          --   dimensione emittente. Arrivata nel CSV da un cantiere BE senza
          --   passare di qui: e' il rosso che questo elenco esiste per dare.
          'dbops.error_log',
          -- ⭐ Il lotto APPARTIENE ALL'ARTICOLO, che e' catalogo globale: la
          --   tabella non ha ne' emittente ne' magazzino (D-L2, brief del Lotto
          --   2; piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config,
          --   2026-09-21). Arrivata nel CSV dal cantiere BE con il residuo
          --   «il nome nell'elenco: team DB» — questo e' il nome.
          'magazzino.lotti',
          'storico.audit_log',
          'ui.lista_colonna',
          'ui.lista_colonna_permesso',
          'ui.lista_definizione',
          'vendite.famiglie_documento']::text[],
    '6) Le liste globali sono esattamente quelle dichiarate qui: il default non si eredita');

-- ============================================================
-- 7) ⛔⛔ Il prezzo che NON si e' pagato
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_liste_multi_emittente_non_certificate),
    0,
    '7) La vista di certificazione resta a zero righe: nessun adesivo senza collaudo');

-- ============================================================
-- 8) ⭐ Chi dichiara di non avere emittenti non ne mostra uno per riga
-- ============================================================
-- ⭐ E' il test 7 letto dal lato opposto, e a differenza del 6 e' DERIVATO:
--   non nomina nessuna lista. `perimetro_emittente = false` dice «nessuna
--   riga appartiene a un emittente»; una colonna attiva a catalogo che espone
--   l'emittente della riga (`campo_sorgente ~ '^emittent'`, lo stesso
--   criterio con cui `vw_liste_multi_emittente_non_certificate` riconosce una
--   certificazione) dice il contrario. Le due dichiarazioni non possono stare
--   sulla stessa lista: o la lista e' globale, o sa dire da quale emittente
--   arriva ogni riga — e allora la strada e' `multi_emittente`, non `false`.
--   ⚠️ E' la trappola che il brief del 18-09 ha scansato due volte
--   (`config.email_log`, `ui.lista_preset`: hanno l'emittente, quindi NON
--   sono in questo CSV). Se un giorno qualcuno la imboccasse «per far
--   entrare», questo test lo dice.
SELECT is(
    (SELECT COALESCE(array_agg(ld.codice::text ORDER BY ld.codice), '{}'::text[])
       FROM ui.lista_definizione ld
      WHERE NOT ld.perimetro_emittente
        AND EXISTS (SELECT 1
                      FROM ui.lista_colonna lc
                     WHERE lc.lista_id = ld.id
                       AND lc.attivo
                       AND lc.campo_sorgente ~ '^emittent')),
    '{}'::text[],
    '8) Nessuna lista globale espone un emittente per riga: le due dichiarazioni si escludono');

SELECT * FROM finish();
ROLLBACK;
