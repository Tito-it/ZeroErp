-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_prezzi_autorizzati — «un prezzo che nessuno ha
--   autorizzato non esce dalla bozza», e i suoi consumatori nei cinque
--   documenti di vendita. Riferimenti: 20260924-20 … -32.
-- Brief: docs/it/dev/work-in-progress/brief-db-preventivi-congelamento-pricing.md
--
-- Elenco test (plan 44):
--  Il building block
--   1) una testata che non conosce e' un errore, non un «niente da dire»
--   2) un id nullo e' un errore
--   3) preventivo con prezzi autorizzati (riga senza stato, componente
--      APPROVED): nessun motivo
--   4) riga PENDING: un motivo, E_DOC_PREZZO_PENDENTE
--   5) ... col conteggio nel dettaglio e la riga giusta
--   6) riga REJECTED + componente PENDING: due motivi, PRIMA il PENDING
--   7) ... e il conteggio va nei `valori` (la frase resa)
--   8) riga REJECTED DISATTIVATA e componente REJECTED SPENTO: non contano
--  Preventivo (D-1, D-2)
--   9) «Emetti» spento col motivo del prezzo in attesa
--  10) «Annulla» resta ACCESO (via d'uscita)
--  11) DRAFT -> EMESSO con un prezzo in attesa: BLOCCA
--  12) DRAFT -> EMESSO con prezzi autorizzati: PASSA (controllo del 11)
--  13) EMESSO con un prezzo rifiutato dopo l'emissione: «Accetta» spento
--  14) EMESSO -> ACCETTATO con un prezzo rifiutato: BLOCCA
--  15) EMESSO -> ANNULLATO con un prezzo rifiutato: PASSA
--      ⚠️ 13-15 SKIP motivato dal 2026-10-08: caso non costruibile (20261008-91)
--  16) il vecchio trigger a10 non c'e' piu'
--  Contratto (D-4)
--  17) una RIGA con prezzo in attesa (prima non contava): un motivo
--  18) «Attiva» spento col motivo, e le azioni portano `reasons`
--  19) DRAFT -> ATTIVO con una riga REJECTED: BLOCCA
--  20) DRAFT -> ATTIVO con prezzi autorizzati: PASSA
--  Offerta (D-4)
--  21) eccezione con prezzo in attesa: un motivo
--  22) «Emetti» spento col motivo del prezzo (il listino c'e')
--  23) BOZZA -> EMESSA con un prezzo in attesa: BLOCCA
--  24) BOZZA -> EMESSA con prezzi autorizzati: PASSA
--  25) EMESSA: il prezzo di un componente non cambia piu' (righe fuori bozza)
--  26) EMESSA coi prezzi autorizzati: «Accetta» acceso
--      (rev 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende R5a: prima
--      «componente rifiutato dopo l'emissione: Accetta spento / BLOCCA», un
--      caso che il lock delle righe dell'offerta ora rende impossibile)
--  Ordine (D-6)
--  27) componente REJECTED: un motivo
--  28) «Conferma» spento col motivo, dalla bozza
--  29) DRAFT -> CONFERMATO con un componente rifiutato: BLOCCA
--  30) DRAFT -> CONFERMATO con prezzi autorizzati: PASSA
--  31) EVASO: un componente non diventa rifiutato (componenti fuori bozza)
--      (rev 2026-10-08, brief-db-righe-e-componenti-le-altre-famiglie §2.2:
--      prima «il RIENTRO EVASO -> CONFERMATO con un componente rifiutato
--      passa», un caso che il lock dei componenti dell'ordine ora rende
--      impossibile)
--  DDT (D-6)
--  32) causale che vende + componente PENDING: il motivo nuovo in
--      fn_check_ddt_emittibile, non piu' E_COMPONENTE_PREZZO_PENDENTE
--  33) ... e «Emetti» e' spento con quel motivo fra i reasons
--  34) causale che NON vende: il prezzo non si chiede (politica del DDT)
--  35) DRAFT -> EMESSO del DDT che vende: il guard solleva il codice nuovo
--  Presidi
--  36) i due codici sono registrati, vivi, CONFLITTO_STATO
--  37) E_PREVENTIVO_RIGHE_PRICING_PENDENTI e' ritirato
--  38) le reason_key nuove stanno nel namespace trasversale
--  Revisioni (§10 del brief: prima l'esito, poi la revisione)
--  39) preventivo EMESSO con un prezzo in attesa: «Crea revisione» spento
--  40) ... e la madre fn_crea_revisione_preventivo rifiuta
--  41) col prezzo RIFIUTATO la revisione si crea (il rifiutato non blocca)
--  42) ... e la riga della revisione porta il REJECTED: la copia resta
--      ⚠️ 39-42 SKIP motivato dal 2026-10-08: caso non costruibile (20261008-91)
--  43) offerta EMESSA: un componente non torna in attesa (righe fuori bozza)
--  44) ... e «Crea revisione» e' acceso: i prezzi sono quelli dell'emissione
--      (rev 2026-10-04, R5a: prima «componente tornato in attesa: Crea
--      revisione spento / la madre rifiuta», ora impossibile per costruzione)
--
-- Scopo:
--  - ⭐ i casi si COSTRUISCONO: mondo, articoli, distinta base e documenti
--    nascono qui. Il test non chiede ai dati di oggi di contenere un prezzo
--    in attesa (i test vecchi saltavano quando non lo trovavano).
--  - ⭐ per ogni guard c'e' il suo controllo: lo stesso passaggio, coi prezzi
--    autorizzati, PASSA. Senza, un rosso potrebbe venire dalla fixture.
--  - ⚠️ gli errori si asseriscono sulla FRASE (throws_like), non su P0001:
--    i guard di transizione sanno sollevare anche altro, e P0001 direbbe solo
--    «errore di dominio», non quale.
-- ------------------------------------------------------------

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   contratto e offerta stanno nel PERIMETRO dell'articolo. L'articolo del builder e' MERCE
--   senza tipologia, che ammette UNA_TANTUM: l'erogazione, scritta CANONE per caso, ora e'
--   UNA_TANTUM (stessa fonte FISSA, la quantita' si comporta uguale).

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (zeroerp_app, RLS
-- attiva). Su un database vuoto questa riga costruisce azienda + operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti: scattano a fine istruzione, non al COMMIT che qui non
-- arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(44);

-- =========================================================
-- Il mondo: azienda di chi agisce + cliente fatturabile legato a lei.
-- ⚠️ Con il contesto gia' aperto il builder RIUSA l'azienda di chi agisce.
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP prezzi autorizzati');

-- Due articoli costruiti: un KIT composito e il suo COMPONENTE, con una
-- distinta base valida oggi. Il KIT nasce composito:
-- catalogo.trgfn_articoli_componenti_guard_is_composito rifiuta la distinta
-- di un articolo semplice.
CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PZA-KIT', false, p_is_composito => true) AS kit_id,
       dbops.fn_pgtap_crea_articolo('PGT-PZA-CMP', false)                         AS cmp_id;

-- ⚠️ obbligatorio = false: un componente obbligatorio non si spegne dalla riga
--   documento (script.trgfn_componenti_guard_obbligatorio), e il caso 8 — un
--   componente rifiutato e poi TOLTO — esiste solo per i facoltativi.
INSERT INTO catalogo.articoli_componenti
    (prodotto_id, componente_id, coeff_qta, valido_dal, esposizione_in_fattura, obbligatorio)
SELECT a.kit_id, a.cmp_id, 1, script.fn_data_operativa() - 30, 'DESCRITTIVO', false FROM _a a;

CREATE TEMP TABLE _k AS
SELECT a.kit_id, a.cmp_id,
       (SELECT ac.id FROM catalogo.articoli_componenti ac
         WHERE ac.prodotto_id = a.kit_id) AS bom_id,
       (SELECT ar.uom_id FROM catalogo.articoli ar WHERE ar.id = a.kit_id) AS uom_id,
       -- ⚠️ ORDER BY: un'aliquota qualunque del catalogo, ma sempre la stessa.
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1) AS iva_id
  FROM _a a;

-- =========================================================
-- 1-2) Il building block, da solo
-- =========================================================
SELECT throws_like(
    $$SELECT script.fn_check_prezzi_autorizzati('vendite.fatture'::regclass, 1)$$,
    '%Parametro non valido%',
    '1) una testata che la funzione non conosce e'' un errore, non un «niente da dire»'
);

SELECT throws_like(
    $$SELECT script.fn_check_prezzi_autorizzati('vendite.preventivi'::regclass, NULL)$$,
    '%Parametro non valido%',
    '2) un id nullo e'' un errore'
);

-- =========================================================
-- Preventivi: uno per scenario, padre e figli in istruzioni separate
-- (la policy della riga risolve il perimetro passando dalla testata).
-- =========================================================
CREATE TEMP TABLE _p (tag text PRIMARY KEY, prev_id bigint, riga_id bigint, comp_id bigint);

DO $fixture$
DECLARE
    c        record;
    k        record;
    v_caso   record;
    v_prev   vendite.preventivi.id%TYPE;
    v_riga   vendite.preventivi_righe.id%TYPE;
    v_comp   vendite.preventivi_righe_componenti.id%TYPE;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    FOR v_caso IN
        SELECT * FROM (VALUES
            -- tag,        stato riga,  stato comp,  riga attiva, comp attivo
            ('pulito',     NULL,        'APPROVED',  true,        true),
            ('pendente',   'PENDING',   NULL,        true,        true),
            ('misto',      'REJECTED',  'PENDING',   true,        true),
            ('spenti',     'REJECTED',  'REJECTED',  false,       false),
            ('emesso',     NULL,        NULL,        true,        true),
            ('rev',        NULL,        NULL,        true,        true)
        ) AS v(tag, st_riga, st_comp, riga_attiva, comp_attivo)
    LOOP
        INSERT INTO vendite.preventivi
            (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
             billing_account_id, data, emittente_fiscale_id)
        VALUES
            ('PGT-PZA-' || v_caso.tag || '-' || substring(md5(clock_timestamp()::text) FOR 6),
             (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
             c.utility_id, c.istanza_utility_id, c.billing_account_id,
             script.fn_data_operativa(), c.emittente_fiscale_id)
        RETURNING id INTO v_prev;

        INSERT INTO vendite.preventivi_righe
            (preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
             prezzo_unitario, iva_id)
        VALUES
            (v_prev, k.kit_id, 1, 1, k.uom_id, 100, k.iva_id)
        RETURNING id INTO v_riga;

        INSERT INTO vendite.preventivi_righe_componenti
            (riga_preventivo_id, articolo_componente_id, componente_id,
             coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo,
             stato_approvazione_prezzo, uom_operativa_id)
        VALUES
            (v_riga, k.bom_id, k.cmp_id, 1, 1, 10, 'MANUALE',
             v_caso.st_comp::config.stato_approvazione_prezzo, (SELECT uom_id FROM catalogo.articoli WHERE id = k.cmp_id))
        RETURNING id INTO v_comp;

        -- ⚠️ Lo stato della RIGA si scrive DOPO il componente, non alla
        --   nascita: il componente ricalcola il prezzo della riga padre
        --   (script.trgfn_componenti_ricalcola_padre), e su una riga gia'
        --   PENDING il guard per riga (trgfn_righe_guard_pending) lo rifiuta.
        UPDATE vendite.preventivi_righe
           SET stato_approvazione_prezzo = v_caso.st_riga::config.stato_approvazione_prezzo
         WHERE id = v_riga;

        -- Lo spegnimento DOPO la nascita: e' cosi' che l'applicazione toglie
        -- un componente (attivo = false) — e il suo stato resta REJECTED.
        IF NOT v_caso.comp_attivo THEN
            UPDATE vendite.preventivi_righe_componenti SET attivo = false WHERE id = v_comp;
        END IF;
        IF NOT v_caso.riga_attiva THEN
            UPDATE vendite.preventivi_righe SET attivo = false WHERE id = v_riga;
        END IF;

        INSERT INTO _p VALUES (v_caso.tag, v_prev, v_riga, v_comp);
    END LOOP;
END
$fixture$;

-- =========================================================
-- 3-8) Il building block sui preventivi costruiti
-- =========================================================
SELECT is(
    script.fn_check_prezzi_autorizzati('vendite.preventivi'::regclass,
                                       (SELECT prev_id FROM _p WHERE tag = 'pulito')),
    '[]'::jsonb,
    '3) prezzi autorizzati (riga senza stato, componente APPROVED): nessun motivo'
);

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice')
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.preventivi'::regclass,
              (SELECT prev_id FROM _p WHERE tag = 'pendente'))) m),
    '["E_DOC_PREZZO_PENDENTE"]'::jsonb,
    '4) riga PENDING: un motivo, E_DOC_PREZZO_PENDENTE'
);

SELECT is(
    (SELECT (m -> 'dettaglio') - 'componente_id'
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.preventivi'::regclass,
              (SELECT prev_id FROM _p WHERE tag = 'pendente'))) m),
    jsonb_build_object('n_prezzi', 1, 'riga_id', (SELECT riga_id FROM _p WHERE tag = 'pendente')),
    '5) ... col conteggio nel dettaglio e la riga giusta'
);

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice' ORDER BY o)
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.preventivi'::regclass,
              (SELECT prev_id FROM _p WHERE tag = 'misto'))) WITH ORDINALITY AS x(m, o)),
    '["E_DOC_PREZZO_PENDENTE", "E_DOC_PREZZO_RIFIUTATO"]'::jsonb,
    '6) riga REJECTED + componente PENDING: due motivi, PRIMA il PENDING'
);

-- ⚠️ La frase si rende come la renderebbe fn_raise_primo_motivo_se_presente:
--   il messaggio del catalogo coi `valori` del motivo.
SELECT is(
    (SELECT format(me.messaggio,
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(m -> 'valori')))
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.preventivi'::regclass,
              (SELECT prev_id FROM _p WHERE tag = 'misto'))) m
       JOIN config.messaggi_errore me ON me.codice = m ->> 'codice' AND me.lingua = 'it'
      WHERE m ->> 'codice' = 'E_DOC_PREZZO_RIFIUTATO'),
    'Non si può procedere: ci sono prezzi rifiutati dal responsabile (1).',
    '7) ... e il conteggio va nei `valori`: la frase resa lo porta'
);

SELECT is(
    script.fn_check_prezzi_autorizzati('vendite.preventivi'::regclass,
                                       (SELECT prev_id FROM _p WHERE tag = 'spenti')),
    '[]'::jsonb,
    '8) riga REJECTED DISATTIVATA e componente REJECTED SPENTO: non contano (non bloccano per sempre)'
);

-- =========================================================
-- 9-16) Preventivo: capability e guard di transizione
-- =========================================================
SELECT is(
    (SELECT a ->> 'reason_key'
       FROM jsonb_array_elements(script.fn_available_actions_preventivo(
              (SELECT prev_id FROM _p WHERE tag = 'pendente')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO' AND (a ->> 'enabled')::boolean IS FALSE),
    'common.azione_reason.prezzo_pendente',
    '9) «Emetti» spento col motivo del prezzo in attesa'
);

SELECT is(
    (SELECT (a ->> 'enabled')::boolean
       FROM jsonb_array_elements(script.fn_available_actions_preventivo(
              (SELECT prev_id FROM _p WHERE tag = 'pendente')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'ANNULLATO'),
    true,
    '10) «Annulla» resta ACCESO: e'' la via d''uscita (D-2)'
);

SELECT throws_like(
    format('UPDATE vendite.preventivi SET stato_doc_preventivo_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EMESSO'),
           (SELECT prev_id FROM _p WHERE tag = 'pendente')),
    '%prezzi ancora in attesa di approvazione%',
    '11) DRAFT -> EMESSO con un prezzo in attesa: BLOCCA'
);

SELECT lives_ok(
    format('UPDATE vendite.preventivi SET stato_doc_preventivo_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EMESSO'),
           (SELECT prev_id FROM _p WHERE tag = 'emesso')),
    '12) DRAFT -> EMESSO con prezzi autorizzati: PASSA (controllo dell''11)'
);

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui §4.5, decisione
--   di Tid): SKIP MOTIVATO dei test 13-15. Il caso si costruiva scrivendo
--   REJECTED sulla riga del preventivo gia' EMESSO («il modello lo ammette»):
--   da 20261008-91 le righe del preventivo fuori bozza non si scrivono, e dalla
--   bozza si esce solo coi prezzi autorizzati (11-12). «EMESSO con un prezzo
--   rifiutato» non nasce piu' da nessuna porta. Il blocco verso ACCETTATO
--   (Regola 3 del guard di transizione) e la reason della capability RESTANO
--   come difesa in profondita'. ⚠️ Non e' la forma dei test 25-26 (offerta) e
--   31 (ordine), che il 2026-10-04 erano stati riscritti nel rifiuto del lock:
--   per il preventivo Tid ha scelto lo skip, che non cambia il soggetto del test.
SELECT skip(
    'preventivo EMESSO con un prezzo rifiutato dopo l''emissione («Accetta» spento, '
    'ACCETTATO bloccato, ANNULLATO ammesso): caso non costruibile dalle porte del '
    'modello da 20261008-91 (righe del preventivo solo in bozza); i controlli '
    'restano come difesa in profondita''',
    3);

SELECT hasnt_trigger('vendite', 'preventivi',
    'trg_preventivi_a10_guard_transizione_approvazione_upd',
    '16) il vecchio trigger a10 non c''e'' piu'': la regola ha una sede sola');

-- =========================================================
-- 17-20) Contratto: le RIGHE ora contano, e il REJECTED pure
-- =========================================================
CREATE TEMP TABLE _c (tag text PRIMARY KEY, contratto_id bigint, riga_id bigint);

DO $fixture$
DECLARE
    c        record;
    k        record;
    v_tag    text;
    v_ctr    vendite.contratti.id%TYPE;
    v_riga   vendite.contratti_righe.id%TYPE;
    v_ef     vendite.contratti.emittente_fiscale_id%TYPE;
BEGIN
    SELECT m.emittente_fiscale_id INTO v_ef FROM _m m;
    SELECT * INTO k FROM _k;

    FOREACH v_tag IN ARRAY ARRAY['pendente', 'rifiutato', 'pulito'] LOOP
        -- ⚠️ Un cliente per contratto: ex_contratti_no_overlap ammette un solo
        --   contratto per (billing account, istanza, utility, ambito,
        --   periodo). Con il contesto aperto il builder lega il BA all'azienda
        --   di chi agisce.
        SELECT * INTO c FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP prezzi contratto ' || v_tag);

        INSERT INTO vendite.contratti
            (numero, billing_account_id, istanza_utility_id, utility_id,
             stato_doc_contratto_id, emittente_fiscale_id)
        VALUES
            ('PGT-PZA-C-' || v_tag || '-' || substring(md5(clock_timestamp()::text) FOR 6),
             c.billing_account_id, c.istanza_utility_id, c.utility_id,
             (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno = 'DRAFT'),
             v_ef)
        RETURNING id INTO v_ctr;

        -- Negoziato puro: la riga AGGIUNTA con un prezzo e' cio' che rende il
        -- contratto «non vuoto» (DOCUMENTO_SENZA_RIGHE non deve coprire il
        -- motivo che si vuole vedere).
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        INSERT INTO vendite.contratti_righe
            (contratto_id, articolo_id, fonte_quantita_attesa, tipo_eccezione,
             prezzo_unitario, qta_operativa, tipo_erogazione)
        VALUES
            (v_ctr, k.cmp_id, 'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto, 100, 1, 'UNA_TANTUM')
        RETURNING id INTO v_riga;

        UPDATE vendite.contratti_righe
           SET stato_approvazione_prezzo = CASE v_tag
                   WHEN 'pendente'  THEN 'PENDING'::config.stato_approvazione_prezzo
                   WHEN 'rifiutato' THEN 'REJECTED'::config.stato_approvazione_prezzo
               END
         WHERE id = v_riga;

        INSERT INTO _c VALUES (v_tag, v_ctr, v_riga);
    END LOOP;
END
$fixture$;

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice')
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.contratti'::regclass,
              (SELECT contratto_id FROM _c WHERE tag = 'pendente'))) m),
    '["E_DOC_PREZZO_PENDENTE"]'::jsonb,
    '17) contratto: una RIGA con prezzo in attesa (prima contavano solo i componenti) da'' un motivo'
);

SELECT is(
    (SELECT (a ->> 'reason_key') || ' / reasons=' || jsonb_typeof(a -> 'reasons')
       FROM jsonb_array_elements(script.fn_available_actions_contratto(
              (SELECT contratto_id FROM _c WHERE tag = 'pendente')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'ATTIVO' AND (a ->> 'enabled')::boolean IS FALSE),
    'common.azione_reason.prezzo_pendente / reasons=array',
    '18) «Attiva» spento col motivo del prezzo, e l''azione porta l''array `reasons`'
);

SELECT throws_like(
    format('UPDATE vendite.contratti SET stato_doc_contratto_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno = 'ATTIVO'),
           (SELECT contratto_id FROM _c WHERE tag = 'rifiutato')),
    '%prezzi rifiutati dal responsabile%',
    '19) DRAFT -> ATTIVO con una riga REJECTED: BLOCCA (prima passava)'
);

SELECT lives_ok(
    format('UPDATE vendite.contratti SET stato_doc_contratto_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno = 'ATTIVO'),
           (SELECT contratto_id FROM _c WHERE tag = 'pulito')),
    '20) DRAFT -> ATTIVO con prezzi autorizzati: PASSA (controllo del 19)'
);

-- =========================================================
-- 21-26) Offerta: prima non guardava il prezzo per niente
-- =========================================================
-- Il listino con una versione ATTIVA: senza, «Emetti» sarebbe spento dal
-- motivo del listino e il guard solleverebbe quello, coprendo il prezzo.
CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _m), 'pgTAP prezzi offerta');

CREATE TEMP TABLE _o (tag text PRIMARY KEY, offerta_id bigint, eccezione_id bigint, comp_id bigint);

DO $fixture$
DECLARE
    c        record;
    k        record;
    l        record;
    v_tag    text;
    v_off    vendite.offerte_commerciali.id%TYPE;
    v_ecc    vendite.offerte_commerciali_eccezioni.id%TYPE;
    v_comp   vendite.offerte_commerciali_eccezioni_componenti.id%TYPE;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;
    SELECT * INTO l FROM _l;

    -- 'pendente': un'eccezione semplice col prezzo in attesa.
    -- 'kit':      un'eccezione sul kit col suo componente, prezzi autorizzati
    --             alla nascita (il rifiuto arriva DOPO l'emissione, test 25).
    FOREACH v_tag IN ARRAY ARRAY['pendente', 'kit'] LOOP
        INSERT INTO vendite.offerte_commerciali
            (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
             utility_id, listino_id, listino_versione_id, validita_dal,
             stato_doc_offerta_id)
        VALUES
            ('PGT-PZA-O-' || v_tag || '-' || substring(md5(clock_timestamp()::text) FOR 6),
             c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id,
             c.utility_id, l.listino_id, l.listino_versione_id, script.fn_data_operativa(),
             (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA'))
        RETURNING id INTO v_off;

        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        INSERT INTO vendite.offerte_commerciali_eccezioni
            (offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
             prezzo_unitario, qta_operativa, tipo_erogazione)
        VALUES
            (v_off, CASE v_tag WHEN 'kit' THEN k.kit_id ELSE k.cmp_id END,
             'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'FISSA', 100, 1, 'UNA_TANTUM')
        RETURNING id INTO v_ecc;

        v_comp := NULL;
        IF v_tag = 'kit' THEN
            INSERT INTO vendite.offerte_commerciali_eccezioni_componenti
                (eccezione_offerta_id, articolo_componente_id, componente_id,
                 coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
            VALUES
                (v_ecc, k.bom_id, k.cmp_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = k.cmp_id))
            RETURNING id INTO v_comp;
        ELSE
            UPDATE vendite.offerte_commerciali_eccezioni
               SET stato_approvazione_prezzo = 'PENDING'
             WHERE id = v_ecc;
        END IF;

        INSERT INTO _o VALUES (v_tag, v_off, v_ecc, v_comp);
    END LOOP;
END
$fixture$;

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice')
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.offerte_commerciali'::regclass,
              (SELECT offerta_id FROM _o WHERE tag = 'pendente'))) m),
    '["E_DOC_PREZZO_PENDENTE"]'::jsonb,
    '21) offerta: un''eccezione col prezzo in attesa da'' un motivo'
);

SELECT is(
    (SELECT a ->> 'reason_key'
       FROM jsonb_array_elements(script.fn_available_actions_offerta(
              (SELECT offerta_id FROM _o WHERE tag = 'pendente')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSA' AND (a ->> 'enabled')::boolean IS FALSE),
    'common.azione_reason.prezzo_pendente',
    '22) «Emetti» spento col motivo del prezzo (il listino c''e'', non e'' lui a spegnerlo)'
);

SELECT throws_like(
    format('UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'EMESSA'),
           (SELECT offerta_id FROM _o WHERE tag = 'pendente')),
    '%prezzi ancora in attesa di approvazione%',
    '23) BOZZA -> EMESSA con un prezzo in attesa: BLOCCA (prima passava)'
);

SELECT lives_ok(
    format('UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'EMESSA'),
           (SELECT offerta_id FROM _o WHERE tag = 'kit')),
    '24) BOZZA -> EMESSA con prezzi autorizzati: PASSA (controllo del 23)'
);

-- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a; decisione
--   di Tid, «lock pieno»): le righe di un'offerta si toccano solo in BOZZA, come
--   quelle del contratto. Lo stato di approvazione di un componente non cambia
--   piu' dopo l'emissione: la sua modifica ricalcola il prezzo della riga madre
--   (trg_oce_comp_z90_ricalcola_padre), e quell'UPDATE e' fuori bozza. Il caso
--   «componente rifiutato dopo l'emissione», che qui si costruiva con un UPDATE,
--   non ha piu' una strada: il controllo verso ACCETTATA resta come rete.
SELECT throws_like(
    format($$UPDATE vendite.offerte_commerciali_eccezioni_componenti
                SET stato_approvazione_prezzo = 'REJECTED' WHERE id = %s$$,
           (SELECT comp_id FROM _o WHERE tag = 'kit')),
    '%non e'' piu'' in bozza%',
    '25) EMESSA: il prezzo di un componente non cambia piu'' (righe fuori bozza)'
);

SELECT is(
    (SELECT (a ->> 'enabled')::boolean
       FROM jsonb_array_elements(script.fn_available_actions_offerta(
              (SELECT offerta_id FROM _o WHERE tag = 'kit')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'ACCETTATA'),
    true,
    '26) EMESSA coi prezzi autorizzati all''emissione: «Accetta» acceso'
);

-- =========================================================
-- 27-31) Ordine: solo dalla bozza, mai sul rientro
-- =========================================================
CREATE TEMP TABLE _or (tag text PRIMARY KEY, ordine_id bigint, riga_id bigint, comp_id bigint);

DO $fixture$
DECLARE
    c        record;
    k        record;
    v_tag    text;
    v_ord    vendite.ordini.id%TYPE;
    v_riga   vendite.ordini_righe.id%TYPE;
    v_comp   vendite.ordini_righe_componenti.id%TYPE;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    FOREACH v_tag IN ARRAY ARRAY['rifiutato', 'pulito'] LOOP
        INSERT INTO vendite.ordini
            (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
             fatturazione_trigger, emittente_fiscale_id, data)
        VALUES
            (c.cliente_soggetto_ruolo_id, c.billing_account_id,
             (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT'),
             'SPEDITO', c.emittente_fiscale_id, script.fn_data_operativa())
        RETURNING id INTO v_ord;

        INSERT INTO vendite.ordini_righe
            (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
             prezzo_unitario, iva_id)
        VALUES
            (v_ord, 1, k.kit_id, 'Kit pgTAP prezzi', 1, 1, 100, k.iva_id)
        RETURNING id INTO v_riga;

        INSERT INTO vendite.ordini_righe_componenti
            (riga_ordine_id, articolo_componente_id, componente_id,
             coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
        VALUES
            (v_riga, k.bom_id, k.cmp_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = k.cmp_id))
        RETURNING id INTO v_comp;

        IF v_tag = 'rifiutato' THEN
            UPDATE vendite.ordini_righe_componenti
               SET stato_approvazione_prezzo = 'REJECTED'
             WHERE id = v_comp;
        END IF;

        INSERT INTO _or VALUES (v_tag, v_ord, v_riga, v_comp);
    END LOOP;
END
$fixture$;

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice')
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.ordini'::regclass,
              (SELECT ordine_id FROM _or WHERE tag = 'rifiutato'))) m),
    '["E_DOC_PREZZO_RIFIUTATO"]'::jsonb,
    '27) ordine: un componente rifiutato da'' un motivo'
);

SELECT is(
    (SELECT a ->> 'reason_key'
       FROM jsonb_array_elements(script.fn_available_actions_ordine(
              (SELECT ordine_id FROM _or WHERE tag = 'rifiutato')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO' AND (a ->> 'enabled')::boolean IS FALSE),
    'common.azione_reason.prezzo_rifiutato',
    '28) «Conferma» spento col motivo del prezzo, dalla bozza'
);

SELECT throws_like(
    format('UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'CONFERMATO'),
           (SELECT ordine_id FROM _or WHERE tag = 'rifiutato')),
    '%prezzi rifiutati dal responsabile%',
    '29) DRAFT -> CONFERMATO con un componente rifiutato: BLOCCA (prima passava)'
);

SELECT lives_ok(
    format('UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'CONFERMATO'),
           (SELECT ordine_id FROM _or WHERE tag = 'pulito')),
    '30) DRAFT -> CONFERMATO con prezzi autorizzati: PASSA (controllo del 29)'
);

-- ⭐ Il RIENTRO. La matrice riporta l'ordine da EVASO a CONFERMATO in
--   automatico quando l'evasione torna indietro, e un prezzo non autorizzato
--   non deve fermarlo: e' una via d'uscita (D-2). Il guard lo dice ancora.
-- 🔄 rev 2026-10-08 (20261008-34, brief-db-righe-e-componenti-le-altre-famiglie
--   §2.2): il caso non si costruisce piu'. Sull'ordine la marca di approvazione
--   ce l'hanno solo i componenti; l'ordine si conferma solo coi prezzi
--   autorizzati (29), e dopo la conferma i componenti si toccano solo in bozza.
--   Quindi un prezzo non diventa rifiutato su un ordine EVASO: il test prova
--   questo. Stessa riscrittura dei test 26 e 44 sull'offerta (rev 2026-10-04).
UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'EVASO')
 WHERE id = (SELECT ordine_id FROM _or WHERE tag = 'pulito');

SELECT throws_like(
    format($$UPDATE vendite.ordini_righe_componenti
                SET stato_approvazione_prezzo = 'REJECTED'
              WHERE id = %s$$,
           (SELECT comp_id FROM _or WHERE tag = 'pulito')),
    '%non e'' piu'' in bozza%',
    '31) EVASO: un componente non diventa rifiutato dopo la conferma (componenti fuori bozza)'
);

-- =========================================================
-- 32-35) DDT: il predicato dal building block, la politica resta sua
-- =========================================================
CREATE TEMP TABLE _d (tag text PRIMARY KEY, ddt_id bigint, comp_id bigint);

DO $fixture$
DECLARE
    c        record;
    k        record;
    v_tag    text;
    v_ddt    vendite.ddt.id%TYPE;
    v_riga   vendite.ddt_righe.id%TYPE;
    v_comp   vendite.ddt_righe_componenti.id%TYPE;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    -- 'vende':  causale fatturabile — il prezzo si chiede;
    -- 'visione': conto visione — il documento non vende, il prezzo no.
    FOREACH v_tag IN ARRAY ARRAY['vende', 'visione'] LOOP
        -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): col BA del cliente — la
        --   causale vuole un cliente (D-2) e la utility senza BA viola
        --   chk_ddt_ba_utility_insieme.
        INSERT INTO vendite.ddt
            (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id,
             utility_id, billing_account_id, causale_trasporto_id)
        VALUES
            (c.cliente_soggetto_ruolo_id,
             (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT'),
             c.emittente_fiscale_id, c.utility_id, c.billing_account_id,
             (SELECT ct.id FROM config.causali_trasporto ct
               WHERE ct.codice = CASE v_tag WHEN 'vende' THEN 'VENDITA' ELSE 'CONTO_VISIONE' END))
        RETURNING id INTO v_ddt;

        INSERT INTO vendite.ddt_righe
            (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
             prezzo_unitario, iva_id)
        VALUES
            (v_ddt, 1, k.kit_id, 'Kit pgTAP prezzi', 1, 1, 100, k.iva_id)
        RETURNING id INTO v_riga;

        INSERT INTO vendite.ddt_righe_componenti
            (riga_ddt_id, articolo_componente_id, componente_id,
             coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
        VALUES
            (v_riga, k.bom_id, k.cmp_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = k.cmp_id))
        RETURNING id INTO v_comp;

        UPDATE vendite.ddt_righe_componenti
           SET stato_approvazione_prezzo = 'PENDING'
         WHERE id = v_comp;

        -- Gli indirizzi che l'emissione pretende: senza, il guard solleverebbe
        -- quelli e coprirebbe il motivo del prezzo (test 35).
        INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
        SELECT v_ddt, ti.id, '{"pgtap": true}'::jsonb
          FROM config.tipi_indirizzi ti
         WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti('DDT', ARRAY[]::integer[]));

        INSERT INTO _d VALUES (v_tag, v_ddt, v_comp);
    END LOOP;
END
$fixture$;

SELECT is(
    (SELECT jsonb_agg(m ->> 'codice' ORDER BY m ->> 'codice')
       FROM vendite.ddt d,
            jsonb_array_elements(script.fn_check_ddt_emittibile(d)) m
      WHERE d.id = (SELECT ddt_id FROM _d WHERE tag = 'vende')),
    '["E_DOC_PREZZO_PENDENTE"]'::jsonb,
    '32) DDT che vende, componente PENDING: il motivo e'' E_DOC_PREZZO_PENDENTE (non piu'' E_COMPONENTE_PREZZO_PENDENTE)'
);

SELECT ok(
    (SELECT a -> 'reasons' @> '[{"reason": "PREZZO_PENDENTE"}]'::jsonb
            AND (a ->> 'enabled')::boolean IS FALSE
       FROM jsonb_array_elements(script.fn_available_actions_ddt(
              (SELECT ddt_id FROM _d WHERE tag = 'vende')) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    '33) ... e «Emetti» e'' spento con quel motivo fra i reasons'
);

SELECT is(
    (SELECT count(*)::int
       FROM vendite.ddt d,
            jsonb_array_elements(script.fn_check_ddt_emittibile(d)) m
      WHERE d.id = (SELECT ddt_id FROM _d WHERE tag = 'visione')
        AND m ->> 'codice' LIKE 'E_DOC_PREZZO_%'),
    0,
    '34) causale che NON vende: il prezzo non si chiede (la politica resta del DDT)'
);

SELECT throws_like(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s',
           (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'EMESSO'),
           (SELECT ddt_id FROM _d WHERE tag = 'vende')),
    '%prezzi ancora in attesa di approvazione%',
    '35) DRAFT -> EMESSO del DDT che vende con un prezzo in attesa: il guard solleva il codice nuovo'
);

-- =========================================================
-- 36-38) Presidi sul catalogo dei codici
-- =========================================================
SELECT is(
    (SELECT jsonb_agg(ce.codice || ':' || ce.classe ORDER BY ce.codice)
       FROM config.codici_errore ce
      WHERE ce.codice IN ('E_DOC_PREZZO_PENDENTE', 'E_DOC_PREZZO_RIFIUTATO')
        AND ce.obsoleto_dal IS NULL),
    '["E_DOC_PREZZO_PENDENTE:CONFLITTO_STATO", "E_DOC_PREZZO_RIFIUTATO:CONFLITTO_STATO"]'::jsonb,
    '36) i due codici sono registrati, vivi, CONFLITTO_STATO'
);

SELECT isnt(
    (SELECT ce.obsoleto_dal FROM config.codici_errore ce
      WHERE ce.codice = 'E_PREVENTIVO_RIGHE_PRICING_PENDENTI'),
    NULL,
    '37) E_PREVENTIVO_RIGHE_PRICING_PENDENTI e'' ritirato: non lo solleva piu'' nessuno'
);

SELECT is(
    (SELECT jsonb_agg(m ->> 'reason_key' ORDER BY o)
       FROM jsonb_array_elements(script.fn_check_prezzi_autorizzati(
              'vendite.preventivi'::regclass,
              (SELECT prev_id FROM _p WHERE tag = 'misto'))) WITH ORDINALITY AS x(m, o)),
    '["common.azione_reason.prezzo_pendente", "common.azione_reason.prezzo_rifiutato"]'::jsonb,
    '38) le reason_key stanno nel namespace trasversale common.azione_reason'
);

-- =========================================================
-- 39-44) Revisioni: non si creano con un prezzo IN ATTESA (§10 del brief)
-- ⭐ La revisione ricopia stato e pratica di approvazione 1:1. Una riga in
--   attesa ricopiata restava legata alla pratica della versione vecchia, e
--   sulla nuova l'attesa non finiva piu'. Decisione di Tid del 2026-09-24:
--   prima l'esito, poi la revisione. Approvato e rifiutato si ricopiano.
-- =========================================================
UPDATE vendite.preventivi
   SET stato_doc_preventivo_id = (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EMESSO')
 WHERE id = (SELECT prev_id FROM _p WHERE tag = 'rev');

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui §4.5, decisione
--   di Tid): SKIP MOTIVATO dei test 39-42. Il caso si costruiva scrivendo
--   PENDING, poi REJECTED, sulla riga del preventivo gia' EMESSO («il modello lo
--   ammette»). Da 20261008-91 le righe del preventivo fuori bozza non si
--   scrivono, e dalla bozza si esce solo coi prezzi autorizzati (test 11-12):
--   un preventivo EMESSO con una riga attiva in attesa o rifiutata non nasce
--   piu' da nessuna porta. Il gate «prima l'esito, poi la revisione»
--   (script.fn_check_prezzi_in_attesa nella madre e nella capability) e la
--   copia 1:1 del rifiutato RESTANO nel codice come difesa in profondita'.
--   Della copia resta provato il ramo raggiungibile: il componente SPENTO
--   rifiutato, in vendite/test-righe-e-componenti-debiti-residui-v1 (22, 24).
SELECT skip(
    'revisione di un preventivo EMESSO con una riga in attesa o rifiutata: caso non '
    'costruibile dalle porte del modello da 20261008-91 (righe del preventivo solo in '
    'bozza, uscita dalla bozza solo coi prezzi autorizzati); gate e copia restano '
    'come difesa in profondita''',
    4);

-- Offerta: l'eccezione-kit e' EMESSA (test 24).
-- ⚠️ rev 2026-10-04 (R5a, «lock pieno»): un componente non torna in attesa dopo
--   l'emissione — la nuova richiesta passa da una revisione, che nasce in BOZZA.
--   Il caso che qui si costruiva con un UPDATE non ha piu' una strada; il gate
--   «prezzo in attesa» di fn_crea_revisione_offerta resta come rete (lo provava sul
--   preventivo il test 40, stesso building block: dal 2026-10-08 nemmeno li' il
--   caso si costruisce, e il 40 e' uno skip motivato).
SELECT throws_like(
    format($$UPDATE vendite.offerte_commerciali_eccezioni_componenti
                SET stato_approvazione_prezzo = 'PENDING' WHERE id = %s$$,
           (SELECT comp_id FROM _o WHERE tag = 'kit')),
    '%non e'' piu'' in bozza%',
    '43) offerta EMESSA: un componente non torna in attesa (righe fuori bozza)'
);

SELECT is(
    (SELECT (a ->> 'enabled')::boolean
       FROM jsonb_array_elements(script.fn_available_actions_offerta(
              (SELECT offerta_id FROM _o WHERE tag = 'kit')) -> 'available_actions') a
      WHERE a ->> 'key' = 'crea_revisione'),
    true,
    '44) ... e «Crea revisione» e'' acceso: i prezzi sono quelli dell''emissione'
);

SELECT * FROM finish();
ROLLBACK;
