-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'azienda che emette un documento e' quella del suo cliente — un
--   building block (script.trgfn_doc_guard_emittente_ba) al posto di sette
--   copie, un codice per i sei documenti, una frase con i nomi.
--   Brief: docs/it/dev/work-done/brief-db-guard-emittente-ba-unico.md
--   ChangeSet 20261010-17 ... -19.
--
-- ⭐ I soggetti li FABBRICA (dbops.fn_pgtap_crea_emittente_operatore due
--   volte, fn_pgtap_crea_cliente_ba): gira uguale su un database ricostruito
--   da zero. Il cliente e' dell'emittente E1; E2 e' «l'altra azienda».
-- ⚠️ Il codice si legge dal canale CONSTRAINT dell'eccezione (il contratto
--   DB -> backend), non dalla frase.
--
-- ⚠️ DDT e reso NON sono provati sul comportamento, e non per svista: con
--   l'emittente di un'altra azienda sul DDT parlava prima il guard di
--   perimetro (allora trg_ddt_a10_guard_emittente_scope, E_SCOPE_EMITTENTE;
--   dal 20261013-53 e' _z10_ e viene dopo questo guard, come sull'ordine), e
--   il BA di un cliente dell'altra azienda l'operatore non lo vede (lo ferma
--   prima script.fn_cliente_dal_billing_account). La funzione e' la stessa
--   dell'ordine (test 4, 5); il montaggio su DDT e reso lo prova il test 1.
--
-- Indice test (1..10):
--   STRUTTURA
--    1) i sette trigger sono montati sul BB, con colonna e codice attesi
--    2) le sette funzioni di prima non ci sono piu'
--    3) i sei codici di prima sono ritirati, e nessuna funzione li solleva
--   DOCUMENTI
--    4) ordine col BA del cliente di E1 ed emittente E2: E_DOC_EMITTENTE_BA_INCOERENTE
--    5) la frase dice il documento, le due aziende e il billing account, senza nomi di colonna
--    6) DDT senza billing account: niente da confrontare, nasce
--    7) col BA e l'emittente giusti l'ordine nasce
--   COMMESSA
--    8) commessa con l'emittente di E2: E_COMMESSA_EMITTENTE_BA_INCOERENTE (TECNICO)
--    9) la frase della commessa ha la stessa forma
--   MONTAGGIO
--   10) il BB montato senza i quattro argomenti: E_DOC_RIGHE_LOCK_MONTAGGIO
-- ------------------------------------------------------------
BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _e1 AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
CREATE TEMP TABLE _e2 AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Si agisce come l'operatore di E1: il BA del cliente lo lega a E1 il
-- trigger z90.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e1)); END $ctx$;

CREATE TEMP TABLE _c AS SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('emittente unico');

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _k AS
SELECT (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT') AS ord_draft,
       (SELECT id FROM config.stati_doc_ddt    WHERE codice_interno = 'DRAFT') AS ddt_draft,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                AS valuta,
       (SELECT ba.codice FROM anagrafiche.billing_account ba
         WHERE ba.id = (SELECT billing_account_id FROM _c))                    AS ba_codice;

-- Il codice d'errore (canale CONSTRAINT) e la frase di un'istruzione che
-- deve fallire; NULL se passa.
CREATE FUNCTION pg_temp.errore_di(p_sql text, OUT codice text, OUT frase text)
LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS codice = CONSTRAINT_NAME, frase = MESSAGE_TEXT;
END $f$;

CREATE TEMP TABLE _sql AS
SELECT format($q$INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, emittente_fiscale_id, valuta_id)
                 VALUES (%s, %s, %s, %s, %s)$q$,
              c.soggetto_ruolo_id, c.billing_account_id, k.ord_draft, e2.emittente_fiscale_id, k.valuta) AS ordine_e2,
       format($q$INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, emittente_soggetto_ruolo_id)
                 VALUES ('PGTAP-EMIT-UNICO', %s, %s, %s)$q$,
              c.billing_account_id, c.utility_id, e2.soggetto_ruolo_id) AS commessa_e2
  FROM _c c, _k k, _e2 e2;

CREATE TEMP TABLE _err AS
SELECT (pg_temp.errore_di(s.ordine_e2)).*   , 'ordine'   AS caso FROM _sql s
UNION ALL
SELECT (pg_temp.errore_di(s.commessa_e2)).* , 'commessa' FROM _sql s;

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
    (SELECT string_agg(c.relname || ':' || a[3] || ':' || a[4], ', ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_proc p ON p.oid = t.tgfoid
       CROSS JOIN LATERAL (SELECT dbops.fn_trigger_argomenti(t.tgargs) AS a) x
      WHERE p.proname = 'trgfn_doc_guard_emittente_ba'
        AND NOT t.tgisinternal),
    'commesse:emittente_soggetto_ruolo_id:E_COMMESSA_EMITTENTE_BA_INCOERENTE, '
    || 'contratti:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE, '
    || 'ddt:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE, '
    || 'offerte_commerciali:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE, '
    || 'ordini:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE, '
    || 'preventivi:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE, '
    || 'resi:emittente_fiscale_id:E_DOC_EMITTENTE_BA_INCOERENTE',
    '1) i sette trigger guard emittente <-> BA sono montati sul BB, con la colonna e il codice di ciascuno');

SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname ~ '^trgfn_(preventivi|offerte_commerciali|contratti|ordini|ddt|resi|commesse)_guard_emittente_ba$'),
    0,
    '2) le sette funzioni di prima sono ritirate (regola del 2: nello stesso giro)');

SELECT is(
    (SELECT count(*)::int FROM config.codici_errore
      WHERE codice IN ('E_PREV_EMITTENTE_BA_INCOERENTE', 'E_OFFERTA_EMITTENTE_BA_INCOERENTE',
                       'E_CONTRATTO_EMITTENTE_BA_INCOERENTE', 'E_ORDINE_EMITTENTE_BA_INCOERENTE',
                       'E_DDT_EMITTENTE_BA_INCOERENTE', 'E_RESO_EMITTENTE_BA_INCOERENTE')
        AND obsoleto_dal IS NOT NULL)
    + (SELECT count(*)::int FROM pg_proc p
        WHERE p.prosrc ~ 'E_(PREV|OFFERTA|CONTRATTO|ORDINE|DDT|RESO)_EMITTENTE_BA_INCOERENTE'),
    6,
    '3) i sei codici per documento sono ritirati (obsoleto_dal) e nessuna funzione li solleva');

-- ============================================================
-- DOCUMENTI
-- ============================================================
SELECT is(
    (SELECT codice FROM _err WHERE caso = 'ordine'),
    'E_DOC_EMITTENTE_BA_INCOERENTE',
    '4) ordine col BA del cliente di E1 ed emittente E2: E_DOC_EMITTENTE_BA_INCOERENTE (D-1)');

-- ⚠️ Il nome di un'azienda che l'operatore non vede sotto RLS esce come
--   #id: si accetta l'uno o l'altro, e si pretende la forma della frase.
SELECT ok(
    (SELECT e.frase LIKE 'Ordine %: l''azienda che emette (%) non e'' quella del cliente (%, billing account '
                         || k.ba_codice || ').'
            AND e.frase NOT LIKE '%emittente_fiscale_id%'
            AND e.frase NOT LIKE '%billing_account_id%'
       FROM _err e, _k k WHERE e.caso = 'ordine'),
    '5) la frase dice il documento, le due aziende e il billing account, senza nomi di colonna (D-2)');

SELECT lives_ok(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id)
              VALUES (%s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c), (SELECT ddt_draft FROM _k),
           (SELECT emittente_fiscale_id FROM _e1)),
    '6) DDT senza billing account: non c''e'' un cliente con cui confrontare, nasce');

SELECT lives_ok(
    format($q$INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, emittente_fiscale_id, valuta_id)
              VALUES (%s, %s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c), (SELECT billing_account_id FROM _c),
           (SELECT ord_draft FROM _k), (SELECT emittente_fiscale_id FROM _e1), (SELECT valuta FROM _k)),
    '7) col BA del cliente e l''emittente E1 l''ordine nasce');

-- ============================================================
-- COMMESSA
-- ============================================================
SELECT is(
    (SELECT codice FROM _err WHERE caso = 'commessa'),
    'E_COMMESSA_EMITTENTE_BA_INCOERENTE',
    '8) commessa con l''emittente di E2: E_COMMESSA_EMITTENTE_BA_INCOERENTE, il suo codice TECNICO (D-1, D-3)');

SELECT ok(
    (SELECT e.frase LIKE 'Commessa PGTAP-EMIT-UNICO: l''azienda indicata (%) non e'' quella del cliente (%, billing account '
                         || k.ba_codice || ').'
       FROM _err e, _k k WHERE e.caso = 'commessa'),
    '9) la frase della commessa ha la stessa forma: documento, due aziende, billing account');

-- ============================================================
-- MONTAGGIO
-- ============================================================
CREATE TEMP TABLE _montaggio (id int, numero text, billing_account_id bigint, emittente_fiscale_id bigint);
CREATE TRIGGER trg_montaggio_sbagliato
    BEFORE INSERT ON _montaggio FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Prova', 'numero', 'emittente_fiscale_id');

SELECT throws_like(
    'INSERT INTO _montaggio VALUES (1, ''X'', 1, 1)',
    '%montato male%',
    '10) il BB montato con tre argomenti invece di quattro: errore di configurazione (E_DOC_RIGHE_LOCK_MONTAGGIO)');

SELECT * FROM finish();
ROLLBACK;
