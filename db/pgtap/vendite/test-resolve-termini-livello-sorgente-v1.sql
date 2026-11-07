-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10):
--   la commessa del caso 7 nasce APERTA con l'attivita' del builder (p_con_attivita
--   => true, prima false): BOZZA -> APERTA e' spenta, APERTA si raggiunge solo da
--   PRONTA_FATTURAZIONE («riapri»), che vuole una riga APPROVATA e non emessa.
--   La prova legge solo l'attivita' fatturabile della riga DDT (_af7 filtra per
--   commessa_attivita_id). Attese invariate.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): le righe e la conferma dei due
--   ordini da dbops.fn_pgtap_crea_ordine_con_righe (p_ordine_id, 2 x 10): la testata col suo
--   termine resta a mano, e' la premessa del caso. Il test 7 non pesca piu' «un'attivita' nata
--   da un DDT, se il database ne ha una»: la COSTRUISCE (dbops.fn_pgtap_crea_ddt_senza_ordine,
--   dbops.fn_pgtap_crea_commessa con la sorgente ROOT, dbops.fn_pgtap_crea_commessa_attivita
--   con la sorgente DDT_VENDITA, emissione dalla madre): da SKIP diventa una prova vera.
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: T.2 — il livello 1 di vendite.fn_resolve_termini_pagamento
--       risolve la SORGENTE EFFETTIVA e torna raggiungibile.
--       (brief-db-termine-dal-documento-alla-commessa.md §3.2 · changeSet
--        20260803-03) + T.1 (20260803-02, le due colonne del contratto push).
--
-- 🔴 PERCHE' QUESTO FILE ESISTE, ed e' la parte da leggere prima del codice.
--    Il livello 1 sembrava vivo leggendo la funzione, e un primo test in
--    rollback lo aveva CONFERMATO — perche' costruiva l'attivita' a mano con
--    `sorgente_tipo_id = ORDINE_VENDITA`, cioe' con una forma che il pull vero
--    non produce MAI. Il pull scrive `sorgente = COMMESSA`.
--    Un livello si verifica **dal percorso che lo attraversa**, non dal codice
--    che lo dichiara.
--
-- ⭐ rev 2026-10-10 (brief-db-testata-dopo-emissione, fase 2, D-3): il
--    PERCORSO si COSTRUISCE, non si pesca.
--    Fino a quel giorno il file prendeva attivita' reali gia' prodotte dal pull
--    e poi CAMBIAVA il termine sul loro ordine o preventivo — documenti gia'
--    spinti in commessa, quindi fuori bozza. D-3 ha chiuso le condizioni
--    commerciali fuori bozza (E_DOC_CONDIZIONI_FUORI_BOZZA): quella scrittura
--    il modello non la ammette piu' da nessun percorso, e il test la usava per
--    costruirsi il caso. Ora i documenti nascono in bozza COL LORO termine,
--    escono dalla bozza con le transizioni vere, e passano da push
--    (fn_list_*_da_pushare -> fn_get_or_create_commessa ->
--    fn_upsert_commessa_attivita, come il backend) e pull
--    (fn_emit_attivita_fatturabili_da_commessa). La forma della sorgente e'
--    quella del pull vero (COMMESSA), e il test non dipende piu' dai dati del
--    database su cui gira.
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1)  ⭐ invariante di forma: il pull ha prodotto le attivita' costruite qui, e
--       l'attivita' non ha colonne sorgente_* (la provenienza e' la riga di commessa)
--   2)  ⭐ livello 1 dal PERCORSO REALE: il termine dell'ORDINE vince sul cliente
--   3)  livello 1 porta anche la MODALITA' quando la sorgente e' un ordine
--   4)  PREVENTIVO: porta il termine ma NON la modalita' (discesa indipendente)
--   5)  livello 2: la commessa batte il cliente, ma non il documento
--   6)  livello 4: senza nulla lungo la catena, default TP_1RATA
--   7)  ⚠️ sorgente polimorfa: un tipo non gestito NON esplode e non vince
--   8)  T.1: le 5 fn_list_*_da_pushare espongono le due colonne
--   9)  T.1: la colonna porta il valore del documento, non un NULL fisso
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

SELECT plan(9);

-- ============================================================
-- Il mondo: un cliente, un articolo, il contesto dell'operatore.
--   Gira come l'applicazione (ruolo OPERATORE + RLS): il mondo apre il
--   contesto sull'operatore che lo costruisce.
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP termini dalla sorgente');

DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m));
END $ctx$;

CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('PGT-TRM-S') AS id;
-- Al preventivo un SERVIZIO (non gestito a magazzino): la merce del preventivo
-- va all'ordine (fn_push_preventivo_a_ordine), in commessa ci va il resto.
-- La natura la riga la eredita dall'articolo (trg_preventivi_righe_a10_set_natura_vendita):
-- un servizio una tantum ha destinazione COMMESSA. Si sceglie alla nascita.
CREATE TEMP TABLE _srv AS SELECT dbops.fn_pgtap_crea_articolo('PGT-TRM-SRV', p_gestito => false,
    p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                             WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM')) AS id;

-- I termini per CODICE (chiave stabile), le modalita' per codice.
CREATE TEMP TABLE _k AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
       (SELECT t.id FROM config.termini_pagamento t WHERE t.codice_interno = 'TP_30_60_EOM_2R') AS tp_ordine,
       (SELECT t.id FROM config.termini_pagamento t WHERE t.codice_interno = 'TP_30G_EOM_1R')   AS tp_preventivo,
       (SELECT t.id FROM config.termini_pagamento t WHERE t.codice_interno = 'TP_60G_1R')       AS tp_commessa,
       (SELECT t.id FROM config.termini_pagamento t WHERE t.codice_interno = 'TP_30G_1R')       AS tp_cliente,
       (SELECT mp.id FROM config.modalita_pagamento mp WHERE mp.codice = 'MP05')               AS mp_ordine,
       (SELECT mp.id FROM config.modalita_pagamento mp WHERE mp.codice = 'MP01')               AS mp_cliente;

-- Il cliente ha un SUO termine e una SUA modalita': e' il livello che il
-- documento deve battere (il difetto della fattura 2263).
UPDATE anagrafiche.clienti
   SET termine_pagamento_id = (SELECT tp_cliente FROM _k),
       modalita_pagamento_id = (SELECT mp_cliente FROM _k)
 WHERE istanza_utility_id = (SELECT istanza_utility_id FROM _m);

-- ============================================================
-- Push e pull come il backend: le righe della lista da pushare diventano
-- attivita' di commessa, il pull le emette in attivita' fatturabili.
-- Restituisce l'attivita' fatturabile nata dal documento.
-- ============================================================
CREATE FUNCTION pg_temp.spingi_e_tira(p_righe jsonb) RETURNS bigint
LANGUAGE plpgsql AS $f$
DECLARE
    r          jsonb;
    v_commessa bigint;
BEGIN
    IF jsonb_array_length(p_righe) = 0 THEN
        RAISE EXCEPTION 'spingi_e_tira: la lista da pushare e'' vuota';
    END IF;

    -- Come commesse_source_handlers del backend: la commessa con le
    -- dimensioni della riga (compresi termine e modalita' del documento),
    -- poi il collegamento della sorgente ROOT, che il pull pretende.
    r := p_righe -> 0;
    v_commessa := vendite.fn_get_or_create_commessa(
        p_billing_account_id     => (r ->> 'billing_account_id')::bigint,
        p_utility_id             => (r ->> 'utility_id')::integer,
        p_fatturazione_immediata => (r ->> 'fatturazione_immediata')::boolean,
        p_competenza_dal         => (r ->> 'competenza_dal')::date,
        p_competenza_al          => (r ->> 'competenza_al')::date,
        p_meta                   => jsonb_build_object('test_scope', 'pgtap_resolve_termini'),
        p_termine_pagamento_id   => (r ->> 'termine_pagamento_id')::bigint,
        p_modalita_pagamento_id  => (r ->> 'modalita_pagamento_id')::integer);

    PERFORM vendite.fn_link_commessa_sorgente(
        p_commessa_id      => v_commessa,
        p_sorgente_tipo_id => (r ->> 'sorgente_tipo_id')::bigint,
        p_sorgente_chiave  => r ->> 'sorgente_uid');

    FOR r IN SELECT * FROM jsonb_array_elements(p_righe) LOOP
        PERFORM vendite.fn_upsert_commessa_attivita(
            p_commessa_id                   => v_commessa,
            p_segment_key                   => r ->> 'segment_key',
            p_articolo_id                   => (r ->> 'articolo_id')::uuid,
            p_istanza_utility_id            => (r ->> 'istanza_utility_id')::bigint,
            p_data_attivita                 => (r ->> 'data_attivita')::date,
            p_uom_id                        => (r ->> 'uom_id')::bigint,
            p_quantita                      => (r ->> 'quantita')::numeric,
            p_competenza_mese               => (r ->> 'competenza_mese')::date,
            p_competenza_dal                => (r ->> 'competenza_dal')::date,
            p_competenza_al                 => (r ->> 'competenza_al')::date,
            p_prezzo_snapshot               => (r ->> 'prezzo_snapshot')::numeric,
            p_prezzo_base_snapshot          => NULL,
            p_origine_prezzo                => NULL,
            p_tipo_variazione_applicata     => NULL,
            p_valore_variazione_applicata   => NULL,
            p_promo_id                      => NULL,
            p_contratto_id                  => NULL,
            p_categoria_cliente_id_snapshot => NULL,
            p_classe_utenza_id_snapshot     => NULL,
            p_qta_operativa                 => (r ->> 'qta_operativa')::numeric,
            p_uom_operativa_id              => (r ->> 'uom_operativa_id')::bigint,
            p_factor_to_base                => (r ->> 'factor_to_base')::numeric,
            p_tipo_doc_fiscale_id           => (r ->> 'tipo_doc_fiscale_id')::bigint,
            p_valuta_id                     => (r ->> 'valuta_id')::integer,
            p_prezzo_bloccato               => (r ->> 'prezzo_bloccato')::boolean,
            p_pricing_mode                  => r ->> 'pricing_mode',
            p_sorgente_tipo_id              => (r ->> 'sorgente_tipo_id')::bigint,
            p_sorgente_chiave               => r ->> 'sorgente_uid',
            -- La riga del documento, dal lister (come la passa il backend).
            p_sorgente_riga => (r ->> 'riga_id')::bigint,
            p_meta                          => r -> 'meta');
    END LOOP;

    PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
        p_commessa_id   => v_commessa,
        p_only_approved => false);

    RETURN (SELECT min(a.id)
              FROM vendite.attivita_fatturabili a
              JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id
             WHERE a.commessa_id = v_commessa
               AND vendite.fn_documento_uid_di_attivita(ca.sorgente_tipo_id, ca.segment_key) = p_righe -> 0 ->> 'sorgente_uid');
END
$f$;

-- ============================================================
-- I documenti: nascono in bozza COL LORO termine, poi escono dalla bozza.
--   ORD     termine e modalita' propri (livelli 1-3, 5, 9)
--   ORD0    nessun termine e nessuna modalita' (livello 4)
--   PREV    termine proprio, nessuna modalita' (livello 1 sul preventivo)
-- ============================================================
CREATE TEMP TABLE _doc (chiave text PRIMARY KEY, id bigint);

DO $fixture$
DECLARE
    c    record;
    k    record;
    v_id bigint;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    FOR i IN 1..2 LOOP
        -- La testata nasce in bozza COL SUO termine: e' la premessa del caso.
        INSERT INTO vendite.ordini
            (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
             fatturazione_trigger, emittente_fiscale_id, valuta_id, data,
             termine_pagamento_id, modalita_pagamento_id)
        VALUES
            (c.cliente_soggetto_ruolo_id, c.billing_account_id,
             (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT'),
             'CONFERMATO', c.emittente_fiscale_id, k.valuta_id, script.fn_data_operativa(),
             CASE i WHEN 1 THEN k.tp_ordine END, CASE i WHEN 1 THEN k.mp_ordine END)
        RETURNING id INTO v_id;

        -- La riga e la conferma: la strada dell'ordine, dal builder.
        PERFORM dbops.fn_pgtap_crea_ordine_con_righe('termini dalla sorgente', 'CONFERMATO',
            p_quantita => 2, p_prezzo => 10, p_articolo_id => (SELECT id FROM _art),
            p_ordine_id => v_id);
        INSERT INTO _doc VALUES (CASE i WHEN 1 THEN 'ORD' ELSE 'ORD0' END, v_id);
    END LOOP;

    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id, valuta_id, termine_pagamento_id)
    VALUES
        ('PGT-TRM-' || substring(md5(clock_timestamp()::text) FOR 6),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id, k.valuta_id, k.tp_preventivo)
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
    VALUES (v_id, (SELECT id FROM _srv), 2, 2, 10, k.iva_id, 1);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_id, 'EMESSO');
    -- L'accettazione come la fa il backend: le condizioni di fatturazione si
    -- scelgono accettando (D-9), poi la transizione.
    UPDATE vendite.preventivi
       SET fatturazione_immediata = false,
           competenza_mese = date_trunc('month', script.fn_data_operativa())::date
     WHERE id = v_id;
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_id, 'ACCETTATO');
    INSERT INTO _doc VALUES ('PREV', v_id);
END
$fixture$;

CREATE FUNCTION pg_temp.doc(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT id FROM _doc WHERE chiave = p $f$;

-- ============================================================
-- 9) T.1 PRIMA del push: la lista da pushare porta il termine del documento.
--    Un ordine ANCORA DA PUSHARE: dopo il push la funzione lo esclude.
--    ⚠️ DISTINCT e non LIMIT 1: la funzione ritorna una riga per riga
--    d'ordine, ma il termine e' di TESTATA. Con DISTINCT la sotto-select
--    esplode se le righe dello stesso ordine portassero valori diversi:
--    asserisce anche l'invarianza.
-- ============================================================
CREATE TEMP TABLE _t9 AS
SELECT (SELECT DISTINCT termine_pagamento_id
          FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, pg_temp.doc('ORD'))) AS termine;

-- Il percorso: push e pull dei tre documenti.
CREATE TEMP TABLE _af AS
SELECT 'ORD' AS chiave,
       pg_temp.spingi_e_tira((SELECT jsonb_agg(to_jsonb(l))
                                FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, pg_temp.doc('ORD')) l)) AS attivita_id
UNION ALL
SELECT 'ORD0',
       pg_temp.spingi_e_tira((SELECT jsonb_agg(to_jsonb(l))
                                FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, pg_temp.doc('ORD0')) l))
UNION ALL
SELECT 'PREV',
       pg_temp.spingi_e_tira((SELECT jsonb_agg(to_jsonb(l))
                                FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, pg_temp.doc('PREV'), NULL) l));

CREATE FUNCTION pg_temp.af(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT attivita_id FROM _af WHERE chiave = p $f$;

-- ============================================================
-- 1) ⭐ L'invariante di forma che ha ingannato tutti.
--    Se questo test diventa rosso, il pull ha cambiato comportamento e il
--    livello 1 va riletto: e' il primo campanello, non un dettaglio.
--    Sulle attivita' costruite qui (devono esserci tutte e tre) e su tutte
--    quelle del database.
-- ============================================================
-- rev 2026-11-07 (lotto C, giro C.1 di brief-db-sorgente-documento-e-riga): le
--   colonne sorgente_* dell'attivita' non ci sono piu'. L'invariante si riscrive
--   sulla forma che resta: l'attivita' non ha una provenienza sua, la sua
--   provenienza e' la riga di commessa, e il livello 1 parte da li'.
SELECT is(
    (SELECT count(*)::int FROM _af WHERE attivita_id IS NULL)
    + (SELECT count(*)::int FROM pg_attribute a
        WHERE a.attrelid = 'vendite.attivita_fatturabili'::regclass
          AND a.attnum > 0 AND NOT a.attisdropped AND a.attname LIKE 'sorgente%'),
    0,
    '1) invariante: il pull ha prodotto le tre attivita'', e l''attivita'' non ha colonne sorgente_*: la provenienza e'' la riga di commessa');

-- ============================================================
-- 2) ⭐ IL TEST CHE CONTA — livello 1 dal percorso reale.
--    L'ordine porta un termine DIVERSO da quello del cliente: vince l'ordine.
--    Prima di T.2 qui usciva il termine del cliente: e' il difetto della
--    fattura 2263.
-- ============================================================
SELECT is(
    (SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('ORD'))),
    (SELECT tp_ordine FROM _k),
    '2) livello 1 dal percorso reale: vince il termine dell''ORDINE, non del cliente');

-- ============================================================
-- 3) La modalita' viaggia con lo stesso livello.
-- ============================================================
SELECT is(
    (SELECT modalita_pagamento_id FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('ORD'))),
    (SELECT mp_ordine FROM _k),
    '3) livello 1: l''ordine porta anche la modalita'' di pagamento');

-- ============================================================
-- 4) PREVENTIVO: porta il termine, NON la modalita'.
--    I due campi scendono la catena in modo indipendente, e il default
--    esiste solo per il termine: config.modalita_pagamento non ha una riga
--    «predefinita» e sceglierne una finirebbe sulla fattura elettronica.
--    Il cliente non deve poter coprire il buco della modalita'.
-- ============================================================
UPDATE anagrafiche.clienti SET modalita_pagamento_id = NULL
 WHERE istanza_utility_id = (SELECT istanza_utility_id FROM _m);

SELECT is(
    (SELECT termine_pagamento_id::text || '/' || COALESCE(modalita_pagamento_id::text, 'NULL')
       FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('PREV'))),
    (SELECT tp_preventivo FROM _k)::text || '/NULL',
    '4) PREVENTIVO: porta il termine ma non la modalita'' (discesa indipendente)');

-- ============================================================
-- 5) Livello 2: la commessa e' piu' specifica del cliente, ma il documento
--    (livello 1) resta davanti.
--    ⚠️ Il guard di immutabilita' della chiave scatta se la commessa ha gia'
--    attivita' collegate: si usa la GUC di manutenzione, che e' il canale
--    previsto e non un aggiramento. La commessa non e' un documento col lock
--    «fuori bozza».
-- ============================================================
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
UPDATE vendite.commesse SET termine_pagamento_id = (SELECT tp_commessa FROM _k)
 WHERE id IN (SELECT a.commessa_id FROM vendite.attivita_fatturabili a
               WHERE a.id IN (pg_temp.af('ORD'), pg_temp.af('ORD0')));
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'off';

SELECT is(
    (SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('ORD')))::text
    || '|' ||
    (SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('ORD0')))::text,
    (SELECT tp_ordine FROM _k)::text || '|' || (SELECT tp_commessa FROM _k)::text,
    '5) il documento (livello 1) precede la commessa (livello 2); senza termine sul documento vince la commessa');

-- ============================================================
-- 6) Livello 4: tolto tutto, resta il default. Nessuna fattura senza rate.
--    ORD0 e' nato senza termine: si tolgono quello della commessa e del
--    cliente.
-- ============================================================
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
UPDATE vendite.commesse SET termine_pagamento_id = NULL
 WHERE id = (SELECT a.commessa_id FROM vendite.attivita_fatturabili a WHERE a.id = pg_temp.af('ORD0'));
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'off';
UPDATE anagrafiche.clienti SET termine_pagamento_id = NULL
 WHERE istanza_utility_id = (SELECT istanza_utility_id FROM _m);

SELECT is(
    (SELECT tp.codice_interno FROM vendite.fn_resolve_termini_pagamento(pg_temp.af('ORD0')) r
       JOIN config.termini_pagamento tp ON tp.id = r.termine_pagamento_id),
    'TP_1RATA',
    '6) senza nulla lungo la catena resta il default TP_1RATA (D-J)');

-- ============================================================
-- 7) ⚠️ Sorgente POLIMORFA: il tipo non gestito non deve esplodere.
--    `commesse_attivita.sorgente_uid` e' TEXT e per convenzione contratti e
--    consumi vi mettono `id::text`, non un uuid; `attivita_fatturabili.
--    sorgente_uid` e' invece UUID. Assegnare senza filtrare farebbe fallire
--    il cast. Il DDT e' il tipo non gestito: l'attivita' nata da una bolla si
--    COSTRUISCE (bolla senza ordine consegnata, commessa con la sorgente ROOT,
--    attivita' sul segmento della bolla con la sorgente DDT_VENDITA, emissione
--    dalla madre), non si pesca dal database.
-- ============================================================
CREATE TEMP TABLE _ddt7 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('termini ddt',
    p_billing_account_id => (SELECT billing_account_id FROM _m));
CREATE TEMP TABLE _com7 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('termini ddt', 'APERTA',
    (SELECT billing_account_id FROM _m), true, p_con_sorgente_root => true);
CREATE TEMP TABLE _ca7 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id      => (SELECT commessa_id FROM _com7),
    p_sorgente_codice  => 'DDT_VENDITA',
    p_sorgente_uid     => (SELECT ddt_uid::text FROM _ddt7),
    p_sorgente_riga_id => (SELECT ddt_riga_id FROM _ddt7),
    p_quantita         => (SELECT quantita FROM _ddt7));
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id   => (SELECT commessa_id FROM _com7),
    p_only_approved => false);
CREATE TEMP TABLE _af7 AS
SELECT a.id
  FROM vendite.attivita_fatturabili a
 WHERE a.commessa_attivita_id = (SELECT attivita_id FROM _ca7);

SELECT lives_ok(
    format($$ SELECT * FROM vendite.fn_resolve_termini_pagamento(%s) $$,
           (SELECT a.id FROM _af7 a WHERE (SELECT count(*) FROM _af7) = 1)),
    '7) sorgente non gestita dal livello 1: risolve senza errore di cast');

-- ============================================================
-- 8-9) T.1 — il contratto delle fn di push.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname LIKE 'fn\_list\_%\_da\_pushare'
        AND pg_get_function_result(p.oid) LIKE '%termine_pagamento_id%'
        AND pg_get_function_result(p.oid) LIKE '%modalita_pagamento_id%'),
    5,
    '8) tutte e cinque le fn_list_*_da_pushare espongono le due colonne');

SELECT is(
    (SELECT termine FROM _t9),
    (SELECT tp_ordine FROM _k),
    '9) la colonna porta il valore del documento, non un NULL fisso');

SELECT * FROM finish();
ROLLBACK;