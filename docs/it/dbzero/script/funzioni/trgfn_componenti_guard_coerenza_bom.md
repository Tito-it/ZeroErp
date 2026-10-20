{% include-markdown "it/dbzero/script/manual/trgfn_componenti_guard_coerenza_bom.md" %}
# ⚙️ Funzione `trgfn_componenti_guard_coerenza_bom`

```sql
CREATE FUNCTION trgfn_componenti_guard_coerenza_bom()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_guard_coerenza_bom()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INS/UPD su *_righe_componenti — 4 guard BoM modello unificato.
--   TG_ARGV[0]: schema padre       (es. 'vendite')
--   TG_ARGV[1]: tabella padre      (es. 'preventivi_righe')
--   TG_ARGV[2]: col FK figli->padre (es. 'riga_preventivo_id')
--   TG_ARGV[3]: tabella testata    (es. 'preventivi')
--   TG_ARGV[4]: col FK padre->testata (es. 'preventivo_id')
--   TG_ARGV[5]: col data riferimento su testata (es. 'data')
DECLARE
    v_riga_padre_id     BIGINT;
    v_articolo_id_padre catalogo.articoli.id%TYPE;
    v_is_composito      catalogo.articoli.is_composito%TYPE;
    v_data_rif          date;
    v_sql               text;
    v_bom               record;
BEGIN
    -- Legge id riga padre da NEW tramite nome colonna FK in TG_ARGV[2]
    EXECUTE format('SELECT ($1).%I', TG_ARGV[2])
      INTO v_riga_padre_id USING NEW;

    -- Legge articolo_id, is_composito e data documento in unica query
    v_sql := format(
        $q$SELECT pr.articolo_id, a.is_composito, d.%5$I
             FROM %1$I.%2$I  pr
             JOIN catalogo.articoli a  ON a.id  = pr.articolo_id
             JOIN %1$I.%4$I  d  ON d.id  = pr.%3$I
            WHERE pr.id = $1$q$,
        TG_ARGV[0],   -- 1: schema
        TG_ARGV[1],   -- 2: tab_padre
        TG_ARGV[4],   -- 3: col FK padre->testata
        TG_ARGV[3],   -- 4: tab_testata
        TG_ARGV[5]    -- 5: col data testata
    );
    EXECUTE v_sql INTO v_articolo_id_padre, v_is_composito, v_data_rif
      USING v_riga_padre_id;

    -- Guard 1: l'articolo della riga padre deve essere composito
    IF NOT COALESCE(v_is_composito, FALSE) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_DOC_RIGA_NON_COMPOSITO',
            jsonb_build_object(
                'riga_padre_id', v_riga_padre_id,
                'articolo_id',   v_articolo_id_padre
            ),
            NULL::uuid,
            v_riga_padre_id::text
        );
    END IF;

    -- Guard 2+3+4: legge la riga BoM e verifica i vincoli strutturali
    SELECT ac.componente_id,
           ac.validita
      INTO v_bom
      FROM catalogo.articoli_componenti ac
     WHERE ac.id          = NEW.articolo_componente_id
       AND ac.prodotto_id = v_articolo_id_padre;

    -- Guard 2: articolo_componente_id deve appartenere alla BoM del padre
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_DOC_COMPONENTE_NON_BOM',
            jsonb_build_object(
                'articolo_componente_id', NEW.articolo_componente_id,
                'articolo_id_padre',      v_articolo_id_padre
            ),
            NULL::uuid,
            NEW.articolo_componente_id::text,
            v_articolo_id_padre::text
        );
    END IF;

    -- Guard 3: componente_id deve coincidere con BoM.componente_id
    IF v_bom.componente_id IS DISTINCT FROM NEW.componente_id THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_DOC_COMPONENTE_ID_INCOERENTE',
            jsonb_build_object(
                'componente_id_ricevuto', NEW.componente_id,
                'componente_id_atteso',   v_bom.componente_id,
                'articolo_componente_id', NEW.articolo_componente_id
            ),
            NULL::uuid,
            NEW.componente_id::text,
            v_bom.componente_id::text,
            NEW.articolo_componente_id::text
        );
    END IF;

    -- Guard 4: BoM deve essere valida alla data documento
    -- (skip se data non disponibile: v_data_rif IS NULL)
    IF v_data_rif IS NOT NULL AND NOT (v_bom.validita @> v_data_rif) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_DOC_COMPONENTE_BOM_NON_VALIDA',
            jsonb_build_object(
                'articolo_componente_id', NEW.articolo_componente_id,
                'validita_bom',           v_bom.validita::text,
                'data_riferimento',       v_data_rif
            ),
            NULL::uuid,
            NEW.articolo_componente_id::text,
            v_data_rif::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_guard_coerenza_bom()
IS 'Trigger BEFORE INS/UPD su *_righe_componenti: 4 guard BoM modello unificato. (1) padre is_composito, (2) articolo_componente_id in BoM padre, (3) componente_id coerente, (4) validita BoM @> data documento. TG_ARGV[0..5]: schema, tab_padre, col_fk_figli_padre, tab_testata, col_fk_padre_testata, col_data_testata. Rimosso guard esposto_in_fattura (rev 2026-05-13, modello unificato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
