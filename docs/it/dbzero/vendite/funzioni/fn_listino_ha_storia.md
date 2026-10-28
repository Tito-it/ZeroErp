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
    --   BOZZA (oggi ATTIVA o CHIUSA), anche spenta. Una BOZZA non
    --   conta. Listino NULL: false.
    -- ⚠️ Non e' la regola «in vigore a una data»
    --   (vendite.fn_listino_versione_in_vigore): qui non c'e'
    --   data ne' filtro su attivo.
    -- =========================================================
    RETURN EXISTS (
        SELECT 1
          FROM vendite.listini_versioni v
          JOIN config.stati_doc_listino_versioni s ON s.id = v.stato_doc_listino_versione_id
         WHERE v.listino_id = p_listino_id
           AND s.codice_interno <> 'BOZZA');
END;
$function$

COMMENT ON FUNCTION vendite.fn_listino_ha_storia(p_listino_id bigint)
IS 'True se il listino ha STORIA: almeno una versione uscita dalla bozza (stato <> BOZZA: oggi ATTIVA o CHIUSA), anche spenta (D-1 di Tid, 2026-10-22). Non e'' la regola «in vigore a una data» di vendite.fn_listino_versione_in_vigore: qui non c''e'' data ne'' filtro su attivo. Una BOZZA non conta: nessuno ci ha mai preso un prezzo. Gli stati di una versione non tornano indietro, quindi «ha oggi ATTIVA o CHIUSA» = «ha avuto una versione attiva». Un listino con storia non si spegne con l''interruttore: si chiude con la fine validita'' della versione (vendite.trgfn_listini_guard_spegnimento_storia). Sede unica della regola: la legge anche il backend per mostrare il toggle «Attivo» solo a un listino senza storia. SECURITY INVOKER, STABLE. Richiesta BE §9.8 di brief-be-utenti-di-sviluppo. Rev 2026-10-28 (20261028-19, brief-modello-documento-vendita §16, L-1): lo stato della versione di listino si legge dal vocabolario config.stati_doc_listino_versioni (codice_interno), non piu'' dalla colonna testo stato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
