{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_reso.md" %}
# ⚙️ Funzione `fn_pgtap_crea_reso`

```sql
CREATE FUNCTION fn_pgtap_crea_reso(p_etichetta text, p_ddt_id bigint, p_quantita numeric, p_tipo_reso_codice character varying, p_stato_codice_interno character varying, p_ddt_riga_id bigint, p_ordine_riga_id bigint, p_reso_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_reso(p_etichetta text DEFAULT 'pgTAP'::text, p_ddt_id bigint DEFAULT NULL::bigint, p_quantita numeric DEFAULT NULL::numeric, p_tipo_reso_codice character varying DEFAULT 'RESO_A_CREDITO'::character varying, p_stato_codice_interno character varying DEFAULT 'CONFERMATO'::character varying, p_ddt_riga_id bigint DEFAULT NULL::bigint, p_ordine_riga_id bigint DEFAULT NULL::bigint, p_reso_id bigint DEFAULT NULL::bigint, p_data date DEFAULT NULL::date)
 RETURNS TABLE(reso_id bigint, reso_uid uuid, resi_riga_id bigint, ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint, ordine_riga_id bigint, quantita numeric, tipo_reso_id bigint, stato_doc_reso_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un RESO su una bolla, nello
--   stato chiesto (default CONFERMATO), per la strada vera del
--   dominio.
-- Uso:
--   -- un reso a credito di 3 sulla bolla del test, confermato:
--   CREATE TEMP TABLE tmp_r AS
--   SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti',
--              (SELECT ddt_id FROM tmp_b), 3);
--   -- un reso per ri-consegna a due righe: la prima in bozza,
--   -- la seconda aggiunta allo stesso reso, poi la conferma:
--   CREATE TEMP TABLE tmp_r1 AS
--   SELECT * FROM dbops.fn_pgtap_crea_reso('due righe', v_ddt, 3,
--              'RESO_PER_RICONSEGNA', 'DRAFT', p_ddt_riga_id => v_r1);
--   SELECT * FROM dbops.fn_pgtap_crea_reso('due righe', NULL, 2,
--              'RESO_PER_RICONSEGNA', p_ddt_riga_id => v_r2,
--              p_reso_id => (SELECT reso_id FROM tmp_r1));
-- ⛔ L'annullo non lo fa: e' del verbo vendite.fn_annulla_reso.
-- rev 2026-10-25 (20261025-36, brief-db-pgtap-reso-costruito §7.7): lo
--   stato da dbops.fn_pgtap_porta_a_stato, che sul reso passa dal verbo e
--   concede l'azione che la matrice chiede per il passaggio (giro 5 di
--   brief-modello-documento-vendita): il builder non nomina piu' l'azione.
-- rev 2026-11-03 (20261103-35, brief-db-addebito-trasporto-ordine §8.1):
--   senza p_ddt_riga_id la riga e' la prima di MERCE della bolla, non
--   la prima: un onere (trasporto, spese) non si rende, e con l'onere
--   al numero 1 il builder sbaglierebbe bersaglio. Una riga chiesta
--   esplicitamente si prende com'e' (il test del rifiuto la chiede).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_stato_id    config.stati_doc_reso.id%TYPE;
    v_iniziale    config.stati_doc_reso.iniziale%TYPE;
    v_abortito    config.stati_doc_reso.is_abortito%TYPE;
    v_tipo_id     config.tipi_reso.id%TYPE;
    v_sorgente_id config.sorgenti.id%TYPE;
    v_ddt         vendite.ddt.id%TYPE;
    v_ddt_uid     vendite.ddt.uid%TYPE;
    v_prov_id     vendite.resi.sorgente_id%TYPE;
    v_prov_uid    vendite.resi.sorgente_uid%TYPE;
    v_reso        vendite.resi.id%TYPE;
    v_reso_stato  config.stati_doc_reso.codice_interno%TYPE;
    v_ddt_riga    vendite.ddt_righe.id%TYPE;
    v_ord_riga    vendite.resi_righe.ordine_riga_id%TYPE;
    v_qta_riga    vendite.ddt_righe.qta_operativa%TYPE;
    v_riga_nr     vendite.resi_righe.riga_nr%TYPE;
    v_resi_riga   vendite.resi_righe.id%TYPE;
BEGIN
    -- 0. I parametri si giudicano PRIMA di costruire.
    -- Lo stato dalla sede della traduzione codice -> id
    -- (script.fn_doc_stato_id: solo uno stato attivo).
    v_stato_id := script.fn_doc_stato_id('vendite.resi'::regclass, p_stato_codice_interno);
    SELECT s.iniziale, s.is_abortito
      INTO v_iniziale, v_abortito
      FROM config.stati_doc_reso s
     WHERE s.id = v_stato_id;
    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_reso: nessuno stato attivo del reso con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;
    IF v_abortito THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_reso: % e'' uno stato abortito — il reso si annulla col verbo vendite.fn_annulla_reso: chiederlo DRAFT o CONFERMATO e annullare dal test',
            p_stato_codice_interno;
    END IF;

    SELECT t.id INTO v_tipo_id
      FROM config.tipi_reso t
     WHERE t.codice_interno = p_tipo_reso_codice
       AND t.attivo IS TRUE;
    IF v_tipo_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_reso: nessun tipo di reso attivo con codice_interno = %',
            coalesce(p_tipo_reso_codice::text, 'NULL');
    END IF;

    IF p_quantita IS NOT NULL AND p_quantita <= 0 THEN
        RAISE EXCEPTION 'fn_pgtap_crea_reso: quantita'' non positiva: %', p_quantita;
    END IF;

    -- 1. La testata: quella del test, o una nuova sulla bolla.
    IF p_reso_id IS NOT NULL THEN
        IF p_data IS NOT NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_reso: con p_reso_id la data e'' quella del reso — non si passa';
        END IF;
        SELECT r.id, d.id, d.uid, s.codice_interno
          INTO v_reso, v_ddt, v_ddt_uid, v_reso_stato
          FROM vendite.resi r
          JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
          LEFT JOIN vendite.ddt d ON d.id = r.sorgente_id
         WHERE r.id = p_reso_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_reso: reso id = % non esiste o non e'' visibile', p_reso_id;
        END IF;
        IF p_ddt_id IS NOT NULL AND p_ddt_id IS DISTINCT FROM v_ddt THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_reso: il reso % e'' della bolla %, non della bolla %',
                p_reso_id, v_ddt, p_ddt_id;
        END IF;
    ELSE
        IF p_ddt_id IS NULL THEN
            -- Nessuna bolla dal test: quella consegnata del dominio.
            SELECT b.ddt_id INTO v_ddt
              FROM dbops.fn_pgtap_crea_ddt_da_ordine(p_etichetta) b;
        ELSE
            v_ddt := p_ddt_id;
        END IF;
        SELECT d.uid INTO v_ddt_uid FROM vendite.ddt d WHERE d.id = v_ddt;
        IF v_ddt_uid IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_reso: bolla id = % non esiste o non e'' visibile', v_ddt;
        END IF;

        -- La provenienza: la bolla, con la chiave del key_selector (il BB che scrive).
        SELECT p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid
          INTO v_sorgente_id, v_prov_id, v_prov_uid
          FROM script.fn_sorgente_provenienza('DDT_VENDITA', v_ddt::text) p;

        -- ⚠️ data e' NOT NULL con un DEFAULT di tabella: due rami,
        --   la sede del default resta il DDL.
        IF p_data IS NULL THEN
            INSERT INTO vendite.resi (sorgente_tipo_id, sorgente_id, sorgente_uid, meta)
            VALUES (v_sorgente_id, v_prov_id, v_prov_uid,
                    jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
            RETURNING id INTO v_reso;
        ELSE
            INSERT INTO vendite.resi (sorgente_tipo_id, sorgente_id, sorgente_uid, data, meta)
            VALUES (v_sorgente_id, v_prov_id, v_prov_uid, p_data,
                    jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
            RETURNING id INTO v_reso;
        END IF;
    END IF;

    -- 2. La riga della bolla: quella chiesta, che deve essere
    --    della bolla, o la prima di MERCE (rev 2026-11-03).
    SELECT dr.id, COALESCE(dr.qta_operativa, dr.quantita) INTO v_ddt_riga, v_qta_riga
      FROM vendite.ddt_righe dr
     WHERE dr.ddt_id = v_ddt
       AND dr.attivo IS TRUE
       AND (p_ddt_riga_id IS NULL OR dr.id = p_ddt_riga_id)
       AND (p_ddt_riga_id IS NOT NULL OR script.fn_natura_e_merce(dr.natura_vendita_id))
     ORDER BY dr.riga_nr, dr.id
     LIMIT 1;
    IF v_ddt_riga IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_reso: nessuna riga attiva % nella bolla %',
            coalesce('id = ' || p_ddt_riga_id::text, 'di merce'), v_ddt;
    END IF;

    -- La riga d'ordine: quella chiesta, o la prima del legame.
    v_ord_riga := p_ordine_riga_id;
    IF v_ord_riga IS NULL THEN
        SELECT f.ordine_riga_id INTO v_ord_riga
          FROM vendite.ordini_righe_fulfillment f
         WHERE f.ddt_riga_id = v_ddt_riga
         ORDER BY f.id
         LIMIT 1;
    END IF;

    SELECT COALESCE(max(rr.riga_nr), 0) + 1 INTO v_riga_nr
      FROM vendite.resi_righe rr
     WHERE rr.reso_id = v_reso;

    INSERT INTO vendite.resi_righe (
        reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
        articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
        tipo_reso_id, meta)
    SELECT v_reso, v_riga_nr, dr.id, v_ord_riga,
           dr.articolo_id, dr.descrizione,
           COALESCE(p_quantita, ceil(v_qta_riga / 2)),
           dr.uom_operativa_id, dr.factor_to_base,
           v_tipo_id, jsonb_build_object('test_scope', 'pgtap_' || p_etichetta)
      FROM vendite.ddt_righe dr
     WHERE dr.id = v_ddt_riga
    RETURNING id INTO v_resi_riga;

    -- 3. Lo stato: il reso e' nato nello stato iniziale; avanti lo porta
    --    la matrice, dal verbo, con l'azione del passaggio concessa.
    IF NOT v_iniziale THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.resi'::regclass, v_reso, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT r.id, r.uid, rr.id, v_ddt, v_ddt_uid, rr.ddt_riga_id, rr.ordine_riga_id,
           rr.quantita, rr.tipo_reso_id, r.stato_doc_reso_id
      FROM vendite.resi r
      JOIN vendite.resi_righe rr ON rr.reso_id = r.id
     WHERE rr.id = v_resi_riga;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_reso(p_etichetta text, p_ddt_id bigint, p_quantita numeric, p_tipo_reso_codice character varying, p_stato_codice_interno character varying, p_ddt_riga_id bigint, p_ordine_riga_id bigint, p_reso_id bigint, p_data date)
IS 'Fixture pgTAP: un reso su una bolla, nello stato chiesto (quinto parametro, default CONFERMATO), per la strada vera del dominio: testata legata alla bolla, riga legata alla riga della bolla e alla riga d''ordine che essa evade, azione conferma_reso concessa, verbo di conferma. La bolla: p_ddt_id, quella del reso p_reso_id (a cui si aggiunge una riga, finche'' e'' in bozza; la bolla si legge da sorgente_id del reso), o una bolla consegnata costruita da dbops.fn_pgtap_crea_ddt_da_ordine. La testata porta la provenienza dal BB che scrive (script.fn_sorgente_provenienza: DDT_VENDITA con la chiave della bolla per il key_selector del tipo) e la data (p_data; NULL = il default della colonna); cliente, emittente, stato iniziale, numero e magazzino li mettono i trigger del dominio. Del reso il database non ha una madre di creazione (testata e righe le scrive il backend), quindi il builder fa gli INSERT. La riga: p_ddt_riga_id (deve essere della bolla) o la prima riga attiva di merce della bolla (script.fn_natura_e_merce sulla natura congelata; un onere non si rende, una riga chiesta con p_ddt_riga_id si prende com''e''); p_ordine_riga_id o la prima riga d''ordine del legame (ORDER BY id; NULL se la riga della bolla non nasce da un ordine); quantita'' operativa p_quantita (default: la meta'' della riga della bolla, arrotondata in su); tipo per codice (p_tipo_reso_codice, default RESO_A_CREDITO); articolo, descrizione, unita'' e fattore dalla riga della bolla. La coerenza (quantita'', origine, bolla consegnata, cliente) la giudicano i guard veri. Uno stato non iniziale si raggiunge con dbops.fn_pgtap_porta_a_stato, che sul reso passa dal verbo (vendite.fn_conferma_reso) e concede all''operatore in sessione l''azione che la matrice chiede; lo stato chiesto lo traduce script.fn_doc_stato_id (solo uno stato attivo): uno stato spento, inesistente o abortito si rifiuta prima di costruire (l''annullo e'' del verbo vendite.fn_annulla_reso, caso del test). Restituisce reso, la riga scritta, bolla, riga della bolla, riga d''ordine, quantita'' base, tipo e stato. Uno stato, un tipo, una bolla, una riga o un reso inesistenti sollevano. Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
