# ⚙️ Funzione `fn_sorgente_documento`

```sql
CREATE FUNCTION fn_sorgente_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS TABLE(documento_id bigint, documento_uid uuid, documento_numero text)
 LANGUAGE plpgsql
 STABLE ROWS 1
AS $function$
DECLARE
    v_schema    pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella   pg_catalog.pg_class.relname%TYPE;
    v_ha_uid    boolean;
    v_label     config.sorgenti.label_selector%TYPE;
    v_ha_label  boolean;
    -- Frammenti della SELECT: colonne costruite con %I, mai testo
    -- del chiamante dentro il format.
    v_uid_expr   text;
    v_label_expr text;
BEGIN
    -- =========================================================
    -- Scopo: da tipo + chiave (id o uid), l'id, l'uid e il numero
    --   leggibile del documento di origine, in una lettura.
    -- Ritorna: UNA riga sempre; tutta NULL se la provenienza non
    --   si risolve (tipo assente, nessuna chiave, documento che
    --   non c'e' o non e' visibile, catalogo incoerente).
    -- ⚠️ Non solleva: e' la domanda di una lista. Chi scrive e il
    --   guard sollevano loro.
    -- =========================================================
    documento_id     := NULL;
    documento_uid    := NULL;
    documento_numero := NULL;

    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0
       OR (p_sorgente_id IS NULL AND p_sorgente_uid IS NULL) THEN
        RETURN NEXT;
        RETURN;
    END IF;

    SELECT l.documento_schema, l.documento_tabella, l.documento_ha_uid,
           l.label_selector, l.documento_ha_label
      INTO v_schema, v_tabella, v_ha_uid, v_label, v_ha_label
      FROM config.fn_sorgente_livelli(p_sorgente_tipo_id) l;

    -- Tipo assente o senza tabella del documento.
    IF v_tabella IS NULL THEN
        RETURN NEXT;
        RETURN;
    END IF;

    -- L'etichetta e' dichiarata ma la colonna non c'e': un difetto
    -- di CATALOGO. Cade tutto, id compreso, perche' si veda.
    IF v_label IS NOT NULL AND NOT v_ha_label THEN
        RETURN NEXT;
        RETURN;
    END IF;

    -- Una chiave che la tabella non ha non si risolve.
    IF p_sorgente_uid IS NOT NULL AND NOT v_ha_uid THEN
        RETURN NEXT;
        RETURN;
    END IF;

    v_uid_expr := CASE WHEN v_ha_uid THEN 't.uid' ELSE 'NULL::uuid' END;
    v_label_expr := CASE
        WHEN v_label IS NULL THEN 'NULL::text'
        ELSE format('t.%I::text', v_label)
    END;

    IF p_sorgente_id IS NOT NULL THEN
        -- Con tutte e due le chiavi, devono indicare lo stesso documento.
        EXECUTE format(
            'SELECT t.id::bigint, %s, %s FROM %I.%I t WHERE t.id = $1%s',
            v_uid_expr, v_label_expr, v_schema, v_tabella,
            CASE WHEN p_sorgente_uid IS NOT NULL THEN ' AND t.uid = $2' ELSE '' END)
          INTO documento_id, documento_uid, documento_numero
          USING p_sorgente_id, p_sorgente_uid;
    ELSE
        EXECUTE format(
            'SELECT t.id::bigint, t.uid, %s FROM %I.%I t WHERE t.uid = $1',
            v_label_expr, v_schema, v_tabella)
          INTO documento_id, documento_uid, documento_numero
          USING p_sorgente_uid;
    END IF;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_sorgente_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'Il BB che risolve la provenienza: da tipo (config.sorgenti) e chiave del documento, l''id, l''uid e il numero leggibile del documento, in una lettura della sua tabella (config.fn_sorgente_livelli). Legge la chiave che riceve, sorgente_id o sorgente_uid, qualunque sia il key_selector del tipo; con tutte e due le vuole coerenti; una chiave che la tabella non ha (l''uid di una commessa) non si risolve. Il numero viene dalla colonna che il catalogo dichiara (label_selector); NULL se non la dichiara. Se la dichiara e la colonna non esiste cade tutta la riga, id compreso: un refuso di catalogo deve vedersi. Restituisce SEMPRE una riga, anche tutta NULL, e non solleva: una provenienza che non si risolve fa sparire l''azione, non rompe la lista. INVOKER: sotto la RLS dei documenti NULL vuol dire anche «non visibile a chi chiede». Per una chiave in forma di testo c''e'' script.fn_sorgente_documento_da_chiave.';
```

</div>

---
{% include-markdown "signature-core.md" %}
