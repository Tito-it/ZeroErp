{% include-markdown "it/dbzero/pratiche/manual/fn_stato_sorgente.md" %}
# ⚙️ Funzione `fn_stato_sorgente`

```sql
CREATE FUNCTION fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS TABLE(sorgente_tipo_id bigint, sorgente_uid text, risolto boolean, stato_codice_interno text, stato_codice text, stato_descrizione text, fase text, esito text, terminale boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Descrittore normalizzato dello stato del documento sorgente
-- (contratto §4 brief design V10). Dispatch: lookup sulla union
-- script.vw_stato_sorgente (unica superficie, decisione A);
-- nessuna riga -> sentinella UNKNOWN, mai errore (additivita':
-- dominio senza resolver = comportamento di oggi).
BEGIN
    -- Guard fail-fast sui parametri (id NULL/<=0, uid vuoto).
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0
       OR p_sorgente_uid IS NULL OR btrim(p_sorgente_uid) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_stato_sorgente',
            'E_STATO_SORGENTE_PARAM_INVALIDO',
            jsonb_build_object(
                'sorgente_tipo_id', p_sorgente_tipo_id,
                'sorgente_uid',     p_sorgente_uid
            ),
            NULL,
            COALESCE(p_sorgente_tipo_id::text, 'NULL'),
            COALESCE(p_sorgente_uid, 'NULL')
        );
    END IF;

    RETURN QUERY
    SELECT
        v.sorgente_tipo_id,
        v.sorgente_uid,
        v.risolto,
        v.stato_codice_interno,
        v.stato_codice,
        v.stato_descrizione,
        v.fase,
        v.esito,
        v.terminale
      FROM script.vw_stato_sorgente v
     WHERE v.sorgente_tipo_id = p_sorgente_tipo_id
       AND v.sorgente_uid     = p_sorgente_uid;

    -- Degrado con grazia: tipo senza resolver o documento non
    -- trovato -> sentinella UNKNOWN (risolto=false). fase=APERTO
    -- e' il default di routing; il consumer usa `risolto` per il
    -- fallback UI (milestone manuale come oggi).
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            p_sorgente_tipo_id,
            p_sorgente_uid,
            false,
            'UNKNOWN'::text,
            'UNKNOWN'::text,
            'n/d'::text,
            'APERTO'::text,
            NULL::text,
            false;
    END IF;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'API di motore per il descrittore normalizzato dello stato del documento sorgente (D3, brief-db-proiezione-stato-dominio). Sempre esattamente 1 riga: proiezione da script.vw_stato_sorgente (risolto=true) oppure sentinella UNKNOWN (risolto=false, fase APERTO, esito NULL, terminale false) senza errore — un tipo senza resolver degrada al comportamento manuale odierno. Guard parametri: E_STATO_SORGENTE_PARAM_INVALIDO su tipo NULL/<=0 o uid vuoto. Per le liste joinare direttamente script.vw_stato_sorgente (niente N+1). rev 2026-07-01.';
```

---
{% include-markdown "signature-core.md" %}
