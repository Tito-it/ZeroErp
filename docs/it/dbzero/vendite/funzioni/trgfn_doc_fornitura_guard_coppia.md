# ⚙️ Funzione `trgfn_doc_fornitura_guard_coppia`

```sql
CREATE FUNCTION trgfn_doc_fornitura_guard_coppia()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_fornitura_guard_coppia()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: e' il selettore del montaggio (TG_ARGV), senza
    --   colonna di vocabolario. v_testata_id e' POLIMORFO: l'id di due
    --   testate diverse. v_numero e v_etichetta sono testo da leggere.
    v_documento   text := TG_ARGV[0];
    v_schema      pg_catalog.pg_namespace.nspname%TYPE;
    v_testata     pg_catalog.pg_class.relname%TYPE;
    v_col_numero  pg_catalog.pg_attribute.attname%TYPE;
    v_fk_col      pg_catalog.pg_attribute.attname%TYPE;
    v_etichetta   text;
    v_testata_id  bigint;
    v_istanza     anagrafiche.istanze_dati_precontrattuali.istanza_utility_id%TYPE;
    v_utility     anagrafiche.istanze_dati_precontrattuali.utility_id%TYPE;
    v_numero      text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La scheda di fornitura descrive la fornitura del suo
    --   documento: la coppia (istanza, utility) e' quella della
    --   testata.
    -- =========================================================
    SELECT s.schema_tabella, s.testata, s.colonna_etichetta, s.colonna_fk, s.etichetta
      INTO v_schema, v_testata, v_col_numero, v_fk_col, v_etichetta
      FROM vendite.fn_doc_fornitura_sede(v_documento) AS s;

    -- Montaggio errato: errore di chiamante, non di dato.
    IF v_fk_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('trigger',   TG_NAME,
                               'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'documento', v_documento),
            NULL::uuid,
            COALESCE(v_documento, '<null>'));
    END IF;

    v_testata_id := (to_jsonb(NEW) ->> v_fk_col)::bigint;

    EXECUTE format(
        'SELECT t.istanza_utility_id, t.utility_id, t.%I::text FROM %I.%I t WHERE t.id = $1',
        v_col_numero, v_schema, v_testata)
       INTO v_istanza, v_utility, v_numero
      USING v_testata_id;

    -- Testata assente o fuori dalla RLS di chi scrive: parlano la FK
    -- e la policy della scheda.
    IF v_istanza IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.istanza_utility_id IS DISTINCT FROM v_istanza
       OR NEW.utility_id IS DISTINCT FROM v_utility THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_FORNITURA_FUORI_TESTATA',
            jsonb_build_object(
                'table',                      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'documento',                  v_documento,
                'testata_id',                 v_testata_id,
                'istanza_utility_id',         NEW.istanza_utility_id,
                'utility_id',                 NEW.utility_id,
                'istanza_utility_id_testata', v_istanza,
                'utility_id_testata',         v_utility),
            NULL::uuid,
            v_etichetta || ' ' || COALESCE(v_numero, v_testata_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_fornitura_guard_coppia()
IS 'Guard BB BEFORE INSERT OR UPDATE OF istanza_utility_id, utility_id, <colonna verso la testata> sulle schede di fornitura (vendite.contratti_utilities, vendite.offerte_commerciali_utilities), TG_ARGV[0] = documento (CONTRATTO | OFFERTA, vendite.fn_doc_fornitura_sede). La coppia (istanza, utility) della scheda e'' quella della testata, altrimenti E_DOC_FORNITURA_FUORI_TESTATA (TECNICO: la coppia la deriva dalla testata chi scrive, non la sceglie una persona). Testata assente o fuori dalla RLS di chi scrive: passa, parlano la FK e la policy della scheda. Un guard e non una FK composta con ON UPDATE CASCADE (D-6 di Tid, 2026-10-12): la cascata cambierebbe la coppia della scheda prima che vendite.trgfn_doc_fornitura_segue_cliente la rifaccia, e il guard tipo/classe del contratto giudicherebbe la classe vecchia contro la utility nuova. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§8.4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
