-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--
-- Test: righe e componenti di preventivo, ordine e DDT allineati a contratto
--   e offerta. ChangeSet 20261008-30 … -35.
-- Brief: docs/it/dev/work-done/brief-db-righe-e-componenti-le-altre-famiglie.md
--
-- Elenco test (plan 26):
--  I lettori DEFINER (§2.2)
--   1) fn_get_testata_id_di_riga: PREVENTIVO, ORDINE, DDT danno la testata della riga
--   2) ... e NULL per una riga che non c'e'
--   3) fn_get_stato_testata_documento: PREVENTIVO -> stato ed etichetta con la revisione
--  Il lock dei componenti (§2.2): per ogni famiglia, in bozza si tocca, fuori no
--   4) preventivo DRAFT: un componente si modifica
--   5) ordine DRAFT: un componente si modifica
--   6) DDT DRAFT: un componente si modifica
--   7) preventivo EMESSO: modificare un componente e' rifiutato DAL COMPONENTE (frase)
--   8) preventivo EMESSO: aggiungere un componente e' rifiutato dal componente
--   9) preventivo EMESSO: togliere un componente e' rifiutato dal componente
--  10) ordine CONFERMATO: modificare un componente e' rifiutato dal componente (frase)
--  11) ordine CONFERMATO: aggiungere un componente e' rifiutato dal componente
--  12) ordine CONFERMATO: togliere un componente e' rifiutato dal componente
--  13) DDT EMESSO: modificare un componente e' rifiutato dal componente (frase)
--  14) DDT EMESSO: aggiungere un componente e' rifiutato dal componente
--  15) DDT EMESSO: togliere un componente e' rifiutato dal componente
--  16) il rifiuto parla PRIMA dei guard del componente: spegnere l'obbligatorio
--      su un ordine confermato dice «non piu' in bozza», non «obbligatorio»
--  La revisione del preventivo (§2.1, D-1)
--  17) la rev N+1 ha gli stessi componenti della rev N, ANCHE lo spento
--  18) ogni componente della rev N+1 sta sotto la riga del suo kit (identita')
--  19) ... e sotto una riga della rev N+1, non della rev N
--  20) la rev N conserva i suoi componenti: la revisione copia, non sposta
--  21) il prezzo delle righe kit e' lo stesso della rev N (dai componenti attivi)
--  22) nella rev N+1 lo spento si riaccende: e' il punto di D-1
--  Il DDL (§2.3, §2.4)
--  23) user_update NOT NULL sulle undici tabelle di righe e componenti
--  24) i quattro CHECK dei componenti si chiamano _quantita_nz, nessuno _pos
--  25) ... e dicono quantita <> 0
--  26) i tre lock nuovi sono BEFORE ROW su INSERT, UPDATE e DELETE
--
-- Scopo:
--  - ⭐ i casi si COSTRUISCONO: mondo, due kit con la loro distinta, i
--    documenti nei loro stati. Niente pescato dal DB.
--  - ⭐ per ogni rifiuto c'e' il suo controllo: lo stesso componente in
--    bozza si modifica. Senza, un rosso potrebbe venire dalla fixture.
--  - ⭐ la revisione e' provata col caso che il ROW_NUMBER non distingueva
--    da solo: due righe kit con l'ORDINE ROVESCIATO rispetto agli id. Il
--    vecchio corpo reggeva comunque (la SELECT ordinava e gli id nascevano in
--    quell'ordine); il test prova il risultato — ogni componente sotto il suo
--    kit — qualunque sia la strada.
--  - ⚠️ gli errori si asseriscono sulla FRASE: il lock e i guard del
--    componente sollevano tutti P0001.
--  - ⭐ e su CHI la dice (pg_temp.chi_rifiuta). Sul DDT, dove anche le righe
--    sono chiuse fuori bozza, un componente fuori bozza lo fermava gia' il
--    lock della RIGA, raggiunto dal ricalcolo del prezzo della madre
--    (trgfn_componenti_ricalcola_padre, AFTER): stessa frase, ma un effetto e
--    non la regola. La controprova senza 20261008-34 (2026-10-08) ha dato
--    verdi i test 13 e 15 per questa strada. Il rifiuto giusto e' quello che
--    non passa dal ricalcolo della madre.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): l'ambito degli indirizzi della bolla e' DDT_VENDITA (le etichette ORDINE/DDT della tabella _doc sono del test e restano).
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (zeroerp_app, RLS
-- attiva). Su un database vuoto questa riga costruisce azienda + operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti: scattano a fine istruzione, non al COMMIT che qui non
-- arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- Chi rifiuta: 'componente | <frase>' se l'errore nasce sul componente,
-- 'madre | <frase>' se nasce dal ricalcolo della riga madre, 'NESSUN ERRORE'.
CREATE FUNCTION pg_temp.chi_rifiuta(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_msg text;
    v_ctx text;
BEGIN
    EXECUTE p_sql;
    RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_ctx = PG_EXCEPTION_CONTEXT;
    RETURN CASE WHEN v_ctx LIKE '%trgfn_componenti_ricalcola_padre%' THEN 'madre' ELSE 'componente' END
           || ' | ' || v_msg;
END
$f$;

-- =========================================================
-- Il mondo e due kit.
--   KIT A: un componente OBBLIGATORIO e uno FACOLTATIVO (che si spegne);
--   KIT B: un componente obbligatorio.
-- I due kit nascono compositi dal builder:
-- catalogo.trgfn_articoli_componenti_guard_is_composito rifiuta la distinta
-- di un articolo semplice.
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP righe altre famiglie');

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-RAF-KA',   false, p_is_composito => true) AS kit_a,
       dbops.fn_pgtap_crea_articolo('PGT-RAF-KA-O', false) AS cmp_a_obb,
       dbops.fn_pgtap_crea_articolo('PGT-RAF-KA-F', false) AS cmp_a_fac,
       dbops.fn_pgtap_crea_articolo('PGT-RAF-KB',   false, p_is_composito => true) AS kit_b,
       dbops.fn_pgtap_crea_articolo('PGT-RAF-KB-O', false) AS cmp_b_obb;

INSERT INTO catalogo.articoli_componenti
    (prodotto_id, componente_id, coeff_qta, valido_dal, esposizione_in_fattura, obbligatorio)
SELECT a.kit_a, a.cmp_a_obb, 1, script.fn_data_operativa() - 30, 'DESCRITTIVO', true  FROM _a a UNION ALL
SELECT a.kit_a, a.cmp_a_fac, 2, script.fn_data_operativa() - 30, 'DESCRITTIVO', false FROM _a a UNION ALL
SELECT a.kit_b, a.cmp_b_obb, 1, script.fn_data_operativa() - 30, 'DESCRITTIVO', true  FROM _a a;

-- Una riga per componente della distinta: kit, componente, riga BoM, UoM.
CREATE TEMP TABLE _bom AS
SELECT ac.prodotto_id AS kit_id, ac.componente_id AS cmp_id, ac.id AS bom_id,
       ac.obbligatorio, ar.uom_id AS cmp_uom_id
  FROM catalogo.articoli_componenti ac
  JOIN catalogo.articoli ar ON ar.id = ac.componente_id
 WHERE ac.prodotto_id IN (SELECT kit_a FROM _a UNION ALL SELECT kit_b FROM _a);

CREATE TEMP TABLE _k AS
SELECT a.*,
       (SELECT ar.uom_id FROM catalogo.articoli ar WHERE ar.id = a.kit_a) AS uom_id,
       -- ⚠️ ORDER BY: un'aliquota qualunque del catalogo, ma sempre la stessa.
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1) AS iva_id
  FROM _a a;

-- =========================================================
-- I documenti, tutti in DRAFT, con una riga KIT A e i suoi due componenti.
-- Il preventivo ha anche una riga KIT B, con l'ORDINE rovesciato rispetto
-- agli id (la riga A nasce prima ma viene dopo): serve alla revisione.
-- Padre e figli in istruzioni separate: la policy della riga risolve il
-- perimetro passando dalla testata.
-- =========================================================
CREATE TEMP TABLE _doc (famiglia text PRIMARY KEY, testata_id bigint, riga_id bigint,
                        comp_obb_id bigint, comp_fac_id bigint, riga_b_id bigint);

DO $fixture$
DECLARE
    c       record;
    k       record;
    v_id    bigint;
    v_riga  bigint;
    v_rigab bigint;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    -- PREVENTIVO
    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id)
    VALUES
        ('PGT-RAF-' || substring(md5(clock_timestamp()::text) FOR 6),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id)
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
         prezzo_unitario, iva_id, ordine)
    VALUES (v_id, k.kit_a, 1, 1, k.uom_id, 100, k.iva_id, 2)
    RETURNING id INTO v_riga;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
         prezzo_unitario, iva_id, ordine)
    VALUES (v_id, k.kit_b, 1, 1,
            (SELECT ar.uom_id FROM catalogo.articoli ar WHERE ar.id = k.kit_b),
            100, k.iva_id, 1)
    RETURNING id INTO v_rigab;

    INSERT INTO vendite.preventivi_righe_componenti
        (riga_preventivo_id, articolo_componente_id, componente_id,
         coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id, ordine)
    SELECT CASE WHEN b.kit_id = k.kit_a THEN v_riga ELSE v_rigab END,
           b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id,
           CASE WHEN b.obbligatorio THEN 1 ELSE 2 END
      FROM _bom b;

    INSERT INTO _doc
    SELECT 'PREVENTIVO', v_id, v_riga,
           (SELECT x.id FROM vendite.preventivi_righe_componenti x WHERE x.riga_preventivo_id = v_riga AND x.componente_id = k.cmp_a_obb),
           (SELECT x.id FROM vendite.preventivi_righe_componenti x WHERE x.riga_preventivo_id = v_riga AND x.componente_id = k.cmp_a_fac),
           v_rigab;

    -- ORDINE
    INSERT INTO vendite.ordini
        (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
         fatturazione_trigger, emittente_fiscale_id, data)
    VALUES
        (c.cliente_soggetto_ruolo_id, c.billing_account_id,
         (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT'),
         'SPEDITO', c.emittente_fiscale_id, script.fn_data_operativa())
    RETURNING id INTO v_id;

    INSERT INTO vendite.ordini_righe
        (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
         prezzo_unitario, iva_id)
    VALUES (v_id, 1, k.kit_a, 'Kit pgTAP', 1, 1, 100, k.iva_id)
    RETURNING id INTO v_riga;

    INSERT INTO vendite.ordini_righe_componenti
        (riga_ordine_id, articolo_componente_id, componente_id,
         coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
    SELECT v_riga, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id
      FROM _bom b WHERE b.kit_id = k.kit_a;

    INSERT INTO _doc
    SELECT 'ORDINE', v_id, v_riga,
           (SELECT x.id FROM vendite.ordini_righe_componenti x WHERE x.riga_ordine_id = v_riga AND x.componente_id = k.cmp_a_obb),
           (SELECT x.id FROM vendite.ordini_righe_componenti x WHERE x.riga_ordine_id = v_riga AND x.componente_id = k.cmp_a_fac),
           NULL;

    -- DDT: causale CONTO_VISIONE, che non vende — il prezzo non si chiede
    --   all'emissione (test 34 di test-fn-check-prezzi-autorizzati-v1).
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
         (SELECT ct.id FROM config.causali_trasporto ct WHERE ct.codice = 'CONTO_VISIONE'))
    RETURNING id INTO v_id;

    INSERT INTO vendite.ddt_righe
        (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
         prezzo_unitario, iva_id)
    VALUES (v_id, 1, k.kit_a, 'Kit pgTAP', 1, 1, 100, k.iva_id)
    RETURNING id INTO v_riga;

    INSERT INTO vendite.ddt_righe_componenti
        (riga_ddt_id, articolo_componente_id, componente_id,
         coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
    SELECT v_riga, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id
      FROM _bom b WHERE b.kit_id = k.kit_a;

    -- Gli indirizzi che l'emissione pretende.
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_id, ti.id, '{"pgtap": true}'::jsonb
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA', ARRAY[]::integer[]));

    INSERT INTO _doc
    SELECT 'DDT', v_id, v_riga,
           (SELECT x.id FROM vendite.ddt_righe_componenti x WHERE x.riga_ddt_id = v_riga AND x.componente_id = k.cmp_a_obb),
           (SELECT x.id FROM vendite.ddt_righe_componenti x WHERE x.riga_ddt_id = v_riga AND x.componente_id = k.cmp_a_fac),
           NULL;
END
$fixture$;

-- =========================================================
-- 1-3) I lettori DEFINER
-- =========================================================
SELECT is(
    concat_ws(',',
        script.fn_get_testata_id_di_riga('PREVENTIVO', (SELECT riga_id FROM _doc WHERE famiglia = 'PREVENTIVO'))
            = (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO'),
        script.fn_get_testata_id_di_riga('ORDINE_VENDITA', (SELECT riga_id FROM _doc WHERE famiglia = 'ORDINE'))
            = (SELECT testata_id FROM _doc WHERE famiglia = 'ORDINE'),
        script.fn_get_testata_id_di_riga('DDT_VENDITA', (SELECT riga_id FROM _doc WHERE famiglia = 'DDT'))
            = (SELECT testata_id FROM _doc WHERE famiglia = 'DDT')),
    't,t,t',
    '1) fn_get_testata_id_di_riga: PREVENTIVO, ORDINE e DDT danno la testata della riga'
);

SELECT is(
    concat_ws(',',
        script.fn_get_testata_id_di_riga('PREVENTIVO', 9223372036854775806) IS NULL,
        script.fn_get_testata_id_di_riga('ORDINE_VENDITA', 9223372036854775806) IS NULL,
        script.fn_get_testata_id_di_riga('DDT_VENDITA', 9223372036854775806) IS NULL),
    't,t,t',
    '2) fn_get_testata_id_di_riga: NULL per una riga che non c''e'' (il lock la legge come cascade)'
);

SELECT is(
    (SELECT t.stato || ' | ' || t.etichetta
       FROM script.fn_get_stato_testata_documento(
              'PREVENTIVO', (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO')) t),
    (SELECT 'DRAFT | Preventivo ' || p.numero || ' rev. ' || p.rev
       FROM vendite.preventivi p
      WHERE p.id = (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO')),
    '3) fn_get_stato_testata_documento: PREVENTIVO -> stato ed etichetta con la revisione'
);

-- =========================================================
-- 4-6) In bozza un componente si modifica (il controllo dei rifiuti)
-- =========================================================
SELECT lives_ok(
    format('UPDATE vendite.preventivi_righe_componenti SET attivo = false WHERE id = %s',
           (SELECT comp_fac_id FROM _doc WHERE famiglia = 'PREVENTIVO')),
    '4) preventivo DRAFT: un componente si modifica (il facoltativo si spegne)'
);

SELECT lives_ok(
    format('UPDATE vendite.ordini_righe_componenti SET meta = ''{"pgtap": 1}''::jsonb WHERE id = %s',
           (SELECT comp_fac_id FROM _doc WHERE famiglia = 'ORDINE')),
    '5) ordine DRAFT: un componente si modifica'
);

SELECT lives_ok(
    format('UPDATE vendite.ddt_righe_componenti SET meta = ''{"pgtap": 1}''::jsonb WHERE id = %s',
           (SELECT comp_fac_id FROM _doc WHERE famiglia = 'DDT')),
    '6) DDT DRAFT: un componente si modifica'
);

-- =========================================================
-- Fuori dalla bozza: preventivo EMESSO, ordine CONFERMATO, DDT EMESSO.
-- La revisione (17-22) parte da questo preventivo EMESSO.
-- =========================================================
UPDATE vendite.preventivi
   SET stato_doc_preventivo_id = (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EMESSO')
 WHERE id = (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO');

UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'CONFERMATO')
 WHERE id = (SELECT testata_id FROM _doc WHERE famiglia = 'ORDINE');

UPDATE vendite.ddt
   SET stato_doc_ddt_id = (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'EMESSO')
 WHERE id = (SELECT testata_id FROM _doc WHERE famiglia = 'DDT');

-- =========================================================
-- 7-15) Fuori bozza: modificare, aggiungere, togliere
-- ⚠️ «Aggiungere» rimette lo stesso componente su una riga che ne e' gia'
--   piena: e' il lock a parlare per primo (fascia _a05_), prima ancora della
--   UNIQUE (riga, riga BoM), che controlla dopo i trigger BEFORE.
-- =========================================================
SELECT alike(
    pg_temp.chi_rifiuta(
        format('UPDATE vendite.preventivi_righe_componenti SET attivo = true WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'PREVENTIVO'))),
    'componente | %Preventivo % rev. % non e'' piu'' in bozza (stato EMESSO)%',
    '7) preventivo EMESSO: modificare un componente e'' rifiutato dal componente, e la frase nomina la revisione'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format($$INSERT INTO vendite.preventivi_righe_componenti
                   (riga_preventivo_id, articolo_componente_id, componente_id,
                    coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
                 SELECT %s, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id
                   FROM _bom b WHERE b.cmp_id = (SELECT cmp_a_fac FROM _k)$$,
               (SELECT riga_id FROM _doc WHERE famiglia = 'PREVENTIVO'))),
    'componente | %non e'' piu'' in bozza%',
    '8) preventivo EMESSO: aggiungere un componente e'' rifiutato dal componente'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format('DELETE FROM vendite.preventivi_righe_componenti WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'PREVENTIVO'))),
    'componente | %non e'' piu'' in bozza%',
    '9) preventivo EMESSO: togliere un componente e'' rifiutato dal componente'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format('UPDATE vendite.ordini_righe_componenti SET meta = ''{"pgtap": 2}''::jsonb WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'ORDINE'))),
    'componente | %Ordine % non e'' piu'' in bozza (stato CONFERMATO)%',
    '10) ordine CONFERMATO: modificare un componente e'' rifiutato dal componente (frase)'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format($$INSERT INTO vendite.ordini_righe_componenti
                   (riga_ordine_id, articolo_componente_id, componente_id,
                    coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
                 SELECT %s, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id
                   FROM _bom b WHERE b.cmp_id = (SELECT cmp_a_fac FROM _k)$$,
               (SELECT riga_id FROM _doc WHERE famiglia = 'ORDINE'))),
    'componente | %non e'' piu'' in bozza%',
    '11) ordine CONFERMATO: aggiungere un componente e'' rifiutato dal componente'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format('DELETE FROM vendite.ordini_righe_componenti WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'ORDINE'))),
    'componente | %non e'' piu'' in bozza%',
    '12) ordine CONFERMATO: togliere un componente e'' rifiutato dal componente'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format('UPDATE vendite.ddt_righe_componenti SET meta = ''{"pgtap": 2}''::jsonb WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'DDT'))),
    'componente | %DDT % non e'' piu'' in bozza (stato EMESSO)%',
    '13) DDT EMESSO: modificare un componente e'' rifiutato dal componente (frase)'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format($$INSERT INTO vendite.ddt_righe_componenti
                   (riga_ddt_id, articolo_componente_id, componente_id,
                    coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
                 SELECT %s, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.cmp_uom_id
                   FROM _bom b WHERE b.cmp_id = (SELECT cmp_a_fac FROM _k)$$,
               (SELECT riga_id FROM _doc WHERE famiglia = 'DDT'))),
    'componente | %non e'' piu'' in bozza%',
    '14) DDT EMESSO: aggiungere un componente e'' rifiutato dal componente'
);

SELECT alike(
    pg_temp.chi_rifiuta(
        format('DELETE FROM vendite.ddt_righe_componenti WHERE id = %s',
               (SELECT comp_fac_id FROM _doc WHERE famiglia = 'DDT'))),
    'componente | %non e'' piu'' in bozza%',
    '15) DDT EMESSO: togliere un componente e'' rifiutato dal componente'
);

-- Spegnere l'obbligatorio lo rifiuta anche trgfn_componenti_guard_obbligatorio
-- (_a10_): fuori bozza deve parlare il lock, che viene prima.
SELECT alike(
    pg_temp.chi_rifiuta(
        format('UPDATE vendite.ordini_righe_componenti SET attivo = false WHERE id = %s',
               (SELECT comp_obb_id FROM _doc WHERE famiglia = 'ORDINE'))),
    'componente | %non e'' piu'' in bozza%',
    '16) ordine CONFERMATO: spegnere l''obbligatorio -> parla il lock, non il guard dell''obbligatorio'
);

-- =========================================================
-- 17-22) La revisione del preventivo (D-1: lo spento si porta)
-- Rev N (EMESSA): riga KIT A (ordine 2) con l'obbligatorio acceso e il
-- facoltativo SPENTO (test 4); riga KIT B (ordine 1) col suo obbligatorio.
-- =========================================================
CREATE TEMP TABLE _rev AS
SELECT r.nuovo_preventivo_id
  FROM vendite.fn_crea_revisione_preventivo(
         (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO'), 'pgtap') r;

-- I componenti di una revisione, con la riga e il kit a cui stanno sotto.
CREATE TEMP TABLE _comp_rev AS
SELECT pr.preventivo_id, pr.id AS riga_id, pr.articolo_id AS kit_riga,
       ac.prodotto_id AS kit_bom, prc.componente_id, prc.attivo, prc.id AS comp_id
  FROM vendite.preventivi_righe_componenti prc
  JOIN vendite.preventivi_righe pr ON pr.id = prc.riga_preventivo_id
  JOIN catalogo.articoli_componenti ac ON ac.id = prc.articolo_componente_id
 WHERE pr.preventivo_id IN ((SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO'),
                            (SELECT nuovo_preventivo_id FROM _rev));

SELECT set_eq(
    $$SELECT componente_id, attivo FROM _comp_rev
       WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)$$,
    $$SELECT componente_id, attivo FROM _comp_rev
       WHERE preventivo_id = (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO')$$,
    '17) la rev N+1 ha gli stessi componenti della rev N, ANCHE lo spento (e spento)'
);

SELECT is(
    (SELECT count(*)::int FROM _comp_rev
      WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)
        AND kit_riga IS DISTINCT FROM kit_bom),
    0,
    '18) ogni componente della rev N+1 sta sotto la riga del suo kit (legame per identita'')'
);

SELECT is(
    (SELECT count(DISTINCT riga_id)::int FROM _comp_rev
      WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)),
    2,
    '19) ... e sotto le due righe della rev N+1'
);

SELECT is(
    (SELECT count(*)::int FROM _comp_rev
      WHERE preventivo_id = (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO')),
    3,
    '20) la rev N conserva i suoi tre componenti: la revisione copia, non sposta'
);

SELECT set_eq(
    format($$SELECT articolo_id, prezzo_unitario FROM vendite.preventivi_righe WHERE preventivo_id = %s$$,
           (SELECT nuovo_preventivo_id FROM _rev)),
    format($$SELECT articolo_id, prezzo_unitario FROM vendite.preventivi_righe WHERE preventivo_id = %s$$,
           (SELECT testata_id FROM _doc WHERE famiglia = 'PREVENTIVO')),
    '21) il prezzo delle righe kit e'' lo stesso della rev N (calcolato dai componenti attivi)'
);

SELECT lives_ok(
    format('UPDATE vendite.preventivi_righe_componenti SET attivo = true WHERE id = %s',
           (SELECT comp_id FROM _comp_rev
             WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)
               AND componente_id = (SELECT cmp_a_fac FROM _k))),
    '22) nella rev N+1 (DRAFT) il facoltativo spento si riaccende: e'' il punto di D-1'
);

-- =========================================================
-- 23-26) Il DDL
-- =========================================================
SELECT is(
    (SELECT COALESCE(string_agg(c.relname::text, ', ' ORDER BY c.relname), '')
       FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
      WHERE a.attname = 'user_update' AND NOT a.attnotnull
        AND a.attrelid IN ('vendite.preventivi_righe'::regclass,
                           'vendite.preventivi_righe_componenti'::regclass,
                           'vendite.ordini_righe'::regclass,
                           'vendite.ordini_righe_componenti'::regclass,
                           'vendite.ddt_righe'::regclass,
                           'vendite.ddt_righe_componenti'::regclass,
                           'vendite.contratti_righe'::regclass,
                           'vendite.contratti_righe_componenti'::regclass,
                           'vendite.offerte_commerciali_eccezioni'::regclass,
                           'vendite.offerte_commerciali_eccezioni_componenti'::regclass,
                           'vendite.resi_righe'::regclass,
                           'vendite.fatture_righe'::regclass)),
    '',
    '23) user_update NOT NULL su righe e componenti dei documenti di vendita (linee-guida-sql §7)'
);

SELECT is(
    (SELECT string_agg(c.conname::text, ', ' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.contype = 'c'
        AND c.conrelid IN ('vendite.preventivi_righe_componenti'::regclass,
                           'vendite.ordini_righe_componenti'::regclass,
                           'vendite.ddt_righe_componenti'::regclass,
                           'vendite.contratti_righe_componenti'::regclass)
        AND c.conname LIKE 'chk\_%\_comp\_quantita\_%'),
    'chk_contrighe_comp_quantita_nz, chk_ddtrighe_comp_quantita_nz, chk_ordrighe_comp_quantita_nz, chk_prevrighe_comp_quantita_nz',
    '24) i quattro CHECK della quantita'' dei componenti si chiamano _nz, nessuno _pos'
);

SELECT is(
    (SELECT string_agg(DISTINCT pg_get_constraintdef(c.oid), ' | ')
       FROM pg_constraint c
      WHERE c.contype = 'c'
        AND c.conname IN ('chk_contrighe_comp_quantita_nz', 'chk_ddtrighe_comp_quantita_nz',
                          'chk_ordrighe_comp_quantita_nz', 'chk_prevrighe_comp_quantita_nz')),
    'CHECK ((quantita <> (0)::numeric))',
    '25) ... e dicono tutti quantita <> 0, come il gemello dell''offerta'
);

-- tgtype: 1 ROW, 2 BEFORE, 4 INSERT, 8 DELETE, 16 UPDATE -> 31.
SELECT is(
    (SELECT string_agg(c.relname || '=' || t.tgtype, ' ' ORDER BY c.relname)
       FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
      WHERE t.tgname IN ('trg_preventivi_righe_componenti_a05_doc_bozza_ins_upd_dlt',
                         'trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt',
                         'trg_ddt_righe_componenti_a05_doc_bozza_ins_upd_dlt')),
    'ddt_righe_componenti=31 ordini_righe_componenti=31 preventivi_righe_componenti=31',
    '26) i tre lock nuovi sono BEFORE ROW su INSERT, UPDATE e DELETE'
);

SELECT * FROM finish();
ROLLBACK;
