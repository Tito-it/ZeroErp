-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i cinque trigger z90_propaga_qta_componenti scattano anche quando la
--   quantita' del padre la ricalcola un trigger BEFORE (qta_operativa -> quantita).
--   ChangeSet 20261004-85 (commento), -86 (trigger con WHEN).
-- Brief: brief-db-esclusioni-implicite (UPDATE OF).
--
-- Elenco test (plan 5):
--  Struttura
--   1) i cinque trigger su script.trgfn_componenti_propaga_qta sono AFTER
--      UPDATE senza colonne (niente OF) e con WHEN sul valore di quantita
--  Comportamento, su un preventivo con un kit
--   2) PRECONDIZIONE: riga padre quantita 1, componente coeff 2 -> quantita 2
--   3) ⭐ UPDATE del SOLO qta_operativa (come il backend sui preventivi): la
--      quantita' del padre cambia e il componente la segue (2 x 3 = 6)
--   4) ... e la propagazione ha davvero riscritto il componente (ctid nuovo):
--      il controllo che rende il 5 significativo
--   5) un UPDATE del padre che NON cambia la quantita' non propaga: il
--      componente non viene riscritto (ctid invariato)
--
-- Scopo:
--  - ⭐ il difetto: con AFTER UPDATE OF quantita il trigger non scattava,
--    perche' quantita la scrive trgfn_qta_from_operativa (BEFORE) e non sta
--    nel SET. linee-guida-trigger.md descriveva UPDATE OF al contrario, e il
--    commento della funzione ripeteva la frase;
--  - il caso si COSTRUISCE: articolo kit, componente e distinta nascono qui
--    (stampo: script/test-fn-check-prezzi-autorizzati-v1);
--  - il preventivo basta per il comportamento: le cinque tabelle montano la
--    stessa funzione con la stessa forma, e il test 1 le guarda tutte;
--  - ⚠️ la quantita' di un componente NON si sceglie a mano:
--    trgfn_componenti_calcola_quantita (BEFORE INSERT OR UPDATE sul
--    componente) la impone sempre = coeff x quantita' del padre. Quindi una
--    propagazione spuria non cambierebbe nessun valore: si vede solo dal fatto
--    che la riga viene RISCRITTA. Il controllo 4-5 guarda il ctid, che cambia a
--    ogni UPDATE (anche HOT) e resta uguale se nessuno tocca la riga.
--    Rev 2026-10-04: la prima versione scriveva 7 a mano sul componente e
--    aspettava che restasse — falso, lo riscriveva quel trigger.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (zeroerp_app, RLS
-- attiva). Su un database vuoto questa riga costruisce azienda + operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti: scattano a fine istruzione, non al COMMIT che qui non
-- arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture: mondo, kit con distinta, preventivo con la riga del kit
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP propaga qta');

-- Il kit nasce composito: il flag serve PRIMA della distinta
-- (la check della distinta, script.fn_articolo_riga_contesto).
CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PQO-KIT', false, p_is_composito => true) AS kit_id,
       dbops.fn_pgtap_crea_articolo('PGT-PQO-CMP', false) AS cmp_id;

-- obbligatorio = false: il test 4 riscrive a mano la quantita' del componente.
INSERT INTO catalogo.articoli_componenti
    (prodotto_id, componente_id, coeff_qta, valido_dal, esposizione_in_fattura, obbligatorio)
SELECT a.kit_id, a.cmp_id, 2, script.fn_data_operativa() - 30, 'DESCRITTIVO', false FROM _a a;

CREATE TEMP TABLE _k AS
SELECT a.kit_id, a.cmp_id,
       (SELECT ac.id FROM catalogo.articoli_componenti ac
         WHERE ac.prodotto_id = a.kit_id) AS bom_id,
       (SELECT ar.uom_id FROM catalogo.articoli ar WHERE ar.id = a.kit_id) AS uom_kit,
       (SELECT ar.uom_id FROM catalogo.articoli ar WHERE ar.id = a.cmp_id) AS uom_cmp,
       -- ⚠️ ORDER BY: un'aliquota qualunque del catalogo, ma sempre la stessa.
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1) AS iva_id
  FROM _a a;

-- Padre e figli in istruzioni separate: la policy della riga risolve il
-- perimetro passando dalla testata.
CREATE TEMP TABLE _p (prev_id bigint, riga_id bigint, comp_id bigint);

DO $fixture$
DECLARE
    c      record;
    k      record;
    v_prev vendite.preventivi.id%TYPE;
    v_riga vendite.preventivi_righe.id%TYPE;
    v_comp vendite.preventivi_righe_componenti.id%TYPE;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id)
    VALUES
        -- numero e' varchar(30): prefisso di 8 + 20 esadecimali (largo, non 2).
        ('PGT-PQO-' || substring(md5(clock_timestamp()::text) FOR 20),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id)
    RETURNING id INTO v_prev;

    -- UdM operativa = UdM del kit: fattore 1, quantita = qta_operativa.
    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
         prezzo_unitario, iva_id)
    VALUES
        (v_prev, k.kit_id, 1, 1, k.uom_kit, 100, k.iva_id)
    RETURNING id INTO v_riga;

    INSERT INTO vendite.preventivi_righe_componenti
        (riga_preventivo_id, articolo_componente_id, componente_id,
         coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo,
         uom_operativa_id)
    VALUES
        (v_riga, k.bom_id, k.cmp_id, 2, 2, 10, 'MANUALE', k.uom_cmp)
    RETURNING id INTO v_comp;

    INSERT INTO _p VALUES (v_prev, v_riga, v_comp);
END
$fixture$;

-- ============================================================
-- 1) Struttura, sulle cinque tabelle
-- ============================================================
-- Criterio, non elenco di nomi: ogni trigger che monta la funzione.
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'trgfn_componenti_propaga_qta'
        AND NOT t.tgisinternal
        AND (t.tgtype & 2)  = 0                      -- AFTER
        AND (t.tgtype & 16) <> 0                     -- UPDATE
        AND cardinality(t.tgattr::int2[]) = 0        -- niente OF
        AND pg_get_triggerdef(t.oid) LIKE '%WHEN%old.quantita IS DISTINCT FROM new.quantita%'),
    5,
    '1) i cinque trigger di propagazione: AFTER UPDATE senza OF, WHEN sul valore di quantita'
);

-- ============================================================
-- 2-5) Comportamento
-- ============================================================
SELECT is(
    (SELECT c.quantita FROM vendite.preventivi_righe_componenti c
      WHERE c.id = (SELECT comp_id FROM _p)),
    2::numeric,
    '2) PRECONDIZIONE: componente coeff 2 su padre 1 -> quantita 2'
);

-- La versione della riga componente prima del cambio di quantita'.
CREATE TEMP TABLE _ct AS
SELECT c.ctid AS prima
  FROM vendite.preventivi_righe_componenti c
 WHERE c.id = (SELECT comp_id FROM _p);

-- ⭐ Il caso del backend: fra le colonne aggiornabili della riga c'e'
--   qta_operativa, non quantita. quantita la ricalcola trgfn_qta_from_operativa.
UPDATE vendite.preventivi_righe
   SET qta_operativa = 3
 WHERE id = (SELECT riga_id FROM _p);

SELECT is(
    (SELECT c.quantita FROM vendite.preventivi_righe_componenti c
      WHERE c.id = (SELECT comp_id FROM _p)),
    6::numeric,
    '3) * UPDATE del solo qta_operativa: il componente segue il padre (2 x 3 = 6)'
);

-- 4) Il controllo: la propagazione ha RISCRITTO il componente. Senza questo,
--    un 5 verde potrebbe venire da un ctid che non cambia mai.
ALTER TABLE _ct ADD COLUMN dopo_qta tid;
UPDATE _ct SET dopo_qta = (SELECT c.ctid FROM vendite.preventivi_righe_componenti c
                            WHERE c.id = (SELECT comp_id FROM _p));

SELECT isnt(
    (SELECT dopo_qta FROM _ct),
    (SELECT prima FROM _ct),
    '4) la propagazione ha riscritto il componente (ctid nuovo)'
);

-- 5) Un UPDATE del padre che non cambia la quantita': il WHEN lo lascia fuori,
--    il componente non viene toccato.
UPDATE vendite.preventivi_righe
   SET descrizione = 'pgTAP propaga qta: descrizione cambiata'
 WHERE id = (SELECT riga_id FROM _p);

SELECT is(
    (SELECT c.ctid FROM vendite.preventivi_righe_componenti c
      WHERE c.id = (SELECT comp_id FROM _p)),
    (SELECT dopo_qta FROM _ct),
    '5) un UPDATE del padre che non cambia quantita non propaga: componente non riscritto'
);

-- ============================================================
-- Chiusura: niente cleanup, ci pensa il ROLLBACK
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
