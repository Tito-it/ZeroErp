{% include-markdown "it/dbzero/vendite/manual/fn_listino_ha_storia.md" %}
# ⚙️ Funzione `fn_listino_ha_storia`

```sql
CREATE FUNCTION fn_listino_ha_storia(p_listino_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listino_ha_storia(p_listino_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   true se il listino ha almeno una versione USCITA DALLA
    --   BOZZA (non nello stato iniziale del vocabolario), anche
    --   spenta. Una bozza non conta. Listino NULL: false.
    -- ⚠️ Non e' la regola «in vigore a una data»
    --   (vendite.fn_listino_versione_in_vigore): qui non c'e'
    --   data ne' filtro su attivo.
    -- =========================================================
    RETURN EXISTS (
        SELECT 1
          FROM vendite.listini_versioni v
          JOIN config.stati_doc_listino_versioni s ON s.id = v.stato_doc_listino_versione_id
         WHERE v.listino_id = p_listino_id
           AND NOT s.iniziale);
END;
$function$

COMMENT ON FUNCTION vendite.fn_listino_ha_storia(p_listino_id bigint)
IS 'True se il listino ha storia: almeno una versione uscita dalla bozza (non nello stato iniziale del vocabolario config.stati_doc_listino_versioni), anche spenta. Non e'' la regola «in vigore a una data» di vendite.fn_listino_versione_in_vigore: qui non c''e'' data ne'' filtro su attivo. Una bozza non conta: nessuno ci ha mai preso un prezzo. Nessun passaggio della matrice config.transizioni_stati_listino_versioni riporta una versione nello stato iniziale, quindi «ha oggi una versione fuori dalla bozza» = «ha avuto una versione attiva». Un listino con storia non si spegne con l''interruttore: si chiude con la fine validita'' della versione (vendite.trgfn_listini_guard_spegnimento_storia). Sede unica della regola: la legge anche il backend per mostrare il toggle «Attivo» solo a un listino senza storia. SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
