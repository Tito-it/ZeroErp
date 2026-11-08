{% include-markdown "it/dbzero/pratiche/manual/fn_stato_sorgente.md" %}
# ⚙️ Funzione `fn_stato_sorgente`

```sql
CREATE FUNCTION fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS TABLE(sorgente_tipo_id bigint, sorgente_id bigint, sorgente_uid uuid, risolto boolean, stato_codice_interno text, stato_codice text, stato_descrizione text, fase text, esito text, terminale boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Descrittore normalizzato dello stato del documento sorgente.
-- Dispatch: lookup sulla union script.vw_stato_sorgente (unica
-- superficie); nessuna riga -> sentinella UNKNOWN, mai errore
-- (un dominio senza resolver degrada al comportamento manuale).
BEGIN
    -- Guard fail-fast sui parametri: tipo NULL o <= 0, nessuna chiave.
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0
       OR num_nonnulls(p_sorgente_id, p_sorgente_uid) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_stato_sorgente',
            'E_STATO_SORGENTE_PARAM_INVALIDO',
            jsonb_build_object(
                'sorgente_tipo_id', p_sorgente_tipo_id,
                'sorgente_id',      p_sorgente_id,
                'sorgente_uid',     p_sorgente_uid
            ),
            NULL,
            COALESCE(p_sorgente_tipo_id::text, 'NULL'),
            COALESCE(p_sorgente_id::text, p_sorgente_uid::text, 'NULL')
        );
    END IF;

    -- Una lettura statica per chiave, sulle colonne native della union:
    -- ogni ramo espone una sola delle due chiavi (l'altra e' NULL), quindi
    -- il documento si trova senza leggere il key_selector. Due letture e
    -- non un OR: un OR sulle due chiavi non scende nella union e la legge
    -- per intero. uuid_eq e int8eq sono leakproof: sotto RLS la chiave
    -- arriva all'Index Cond del ramo.
    IF p_sorgente_uid IS NOT NULL THEN
        RETURN QUERY
        SELECT
            v.sorgente_tipo_id,
            v.sorgente_chiave_id,
            v.sorgente_chiave_uuid,
            v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
          FROM script.vw_stato_sorgente v
         WHERE v.sorgente_tipo_id     = p_sorgente_tipo_id
           AND v.sorgente_chiave_uuid = p_sorgente_uid;
    END IF;

    -- ⚠️ FOUND riflette l'ultimo RETURN QUERY eseguito; se non ne e' girato
    --   nessuno e' ancora false dall'ingresso nella funzione.
    IF NOT FOUND AND p_sorgente_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            v.sorgente_tipo_id,
            v.sorgente_chiave_id,
            v.sorgente_chiave_uuid,
            v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
          FROM script.vw_stato_sorgente v
         WHERE v.sorgente_tipo_id   = p_sorgente_tipo_id
           AND v.sorgente_chiave_id = p_sorgente_id;
    END IF;

    -- Degrado con grazia: tipo senza resolver o documento non
    -- trovato -> sentinella UNKNOWN (risolto=false). fase=APERTO
    -- e' il default di routing; il consumer usa `risolto` per il
    -- fallback UI (milestone manuale).
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            p_sorgente_tipo_id,
            p_sorgente_id,
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

COMMENT ON FUNCTION pratiche.fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'API di motore per il descrittore normalizzato dello stato del documento sorgente. Il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid) e si cerca in script.vw_stato_sorgente sulle sue colonne native, una lettura per chiave (prima sorgente_chiave_uuid = p_sorgente_uid, poi sorgente_chiave_id = p_sorgente_id): chi ha il documento passa il suo id e il suo uid, chi ha la chiave del modello passa quella e NULL nell''altra. Due letture e non un OR: un OR sulle due chiavi non scende nella union. Sempre esattamente 1 riga: la proiezione della vista (risolto=true) oppure la sentinella UNKNOWN (risolto=false, fase APERTO, esito NULL, terminale false, la chiave ricevuta) senza errore: un tipo senza resolver degrada al comportamento manuale. Il risultato porta la chiave nelle colonne del modello (sorgente_id, sorgente_uid). Guard parametri: E_STATO_SORGENTE_PARAM_INVALIDO su tipo NULL o <= 0, o senza chiave. uuid_eq e int8eq sono leakproof: sotto RLS la chiave arriva all''indice del ramo. Lettore: pratiche.fn_reconcile_sorgente. Per le liste si legge direttamente script.vw_stato_sorgente (niente N+1). STABLE, INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
