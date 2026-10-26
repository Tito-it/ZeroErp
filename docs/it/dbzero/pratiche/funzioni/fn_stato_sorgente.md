{% include-markdown "it/dbzero/pratiche/manual/fn_stato_sorgente.md" %}
# ⚙️ Funzione `fn_stato_sorgente`

```sql
CREATE FUNCTION fn_stato_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
DECLARE
    v_chiave_uuid script.vw_stato_sorgente.sorgente_chiave_uuid%TYPE;
    v_chiave_id   script.vw_stato_sorgente.sorgente_chiave_id%TYPE;
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

    -- ⭐ La chiave si cerca nel suo TIPO, non come testo (rev 2026-10-05,
    --   20261005-23). Il confronto sulla colonna testuale sorgente_uid
    --   (uid::text, id::text) sotto RLS non arriva mai all'indice — uuid_out e
    --   int8out non sono leakproof — e cercare UN documento scandiva per intero
    --   tutte le tabelle-documento. uuid_eq e int8eq sono leakproof: Index Cond
    --   sulla chiave del ramo, e il ramo dell'altro tipo ha la colonna a NULL
    --   costante e il planner lo scarta.
    --   La conversione — solo forma CANONICA, NULL e non un errore su una chiave
    --   malformata — sta dal 20261005-24 nei building block
    --   script.fn_sorgente_chiave_uuid / _id, gli stessi che usa
    --   script.vw_pratica_doc_sorgente: qui c'era la prima copia, ritirata.
    v_chiave_uuid := script.fn_sorgente_chiave_uuid(p_sorgente_uid);
    IF v_chiave_uuid IS NULL THEN
        v_chiave_id := script.fn_sorgente_chiave_id(p_sorgente_uid);
    END IF;

    -- Due letture statiche, una per specie di chiave: una stringa non e'
    -- mai insieme un uuid e un intero, quindi al piu' una delle due gira.
    -- Una chiave in nessuna delle due forme non puo' coincidere con nessun
    -- ramo: si va diritti alla sentinella.
    IF v_chiave_uuid IS NOT NULL THEN
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
         WHERE v.sorgente_tipo_id     = p_sorgente_tipo_id
           AND v.sorgente_chiave_uuid = v_chiave_uuid;
    ELSIF v_chiave_id IS NOT NULL THEN
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
         WHERE v.sorgente_tipo_id   = p_sorgente_tipo_id
           AND v.sorgente_chiave_id = v_chiave_id;
    END IF;

    -- Degrado con grazia: tipo senza resolver o documento non
    -- trovato -> sentinella UNKNOWN (risolto=false). fase=APERTO
    -- e' il default di routing; il consumer usa `risolto` per il
    -- fallback UI (milestone manuale come oggi).
    -- ⚠️ FOUND riflette l'ultimo RETURN QUERY eseguito; se non ne e' girato
    --   nessuno e' ancora false dall'ingresso nella funzione.
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
IS 'API di motore per il descrittore normalizzato dello stato del documento sorgente (D3, brief-db-proiezione-stato-dominio). Sempre esattamente 1 riga: proiezione da script.vw_stato_sorgente (risolto=true) oppure sentinella UNKNOWN (risolto=false, fase APERTO, esito NULL, terminale false) senza errore — un tipo senza resolver degrada al comportamento manuale odierno. Guard parametri: E_STATO_SORGENTE_PARAM_INVALIDO su tipo NULL/<=0 o uid vuoto. Per le liste joinare direttamente script.vw_stato_sorgente (niente N+1). rev 2026-07-01. ⭐ rev 2026-10-05 (20261005-23): cerca la chiave nel suo TIPO (sorgente_chiave_uuid / sorgente_chiave_id della union), non come testo. Il confronto testuale sotto RLS non arriva all''indice e per un documento solo leggeva per intero tutte le tabelle-documento (dbdev come applicazione, 2026-10-05: 391 chiamate 3,6 s -> 0,05 s). Stessi risultati del confronto testuale: si accetta solo la forma CANONICA (quella che uid::text / id::text producono — un uid maiuscolo o un id con zeri davanti restano UNKNOWN come prima), e una chiave che non e'' ne'' un uuid ne'' un intero da'' la sentinella senza errore (pg_input_is_valid prima del cast). ⭐ rev 2026-10-05 (20261005-24): la conversione della chiave nel suo tipo non e'' piu'' scritta qui ma nei building block script.fn_sorgente_chiave_uuid / script.fn_sorgente_chiave_id, gli stessi che usa script.vw_pratica_doc_sorgente (regola del 2: la copia di qui e'' ritirata nello stesso giro). Nessun cambio di comportamento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
