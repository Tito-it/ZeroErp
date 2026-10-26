# ⚙️ Funzione `fn_listino_versione_operativa`

```sql
CREATE FUNCTION fn_listino_versione_operativa(p_listino_id bigint, p_listino_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listino_versione_operativa(p_listino_id bigint, p_listino_versione_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la versione di listino che governa un documento con eccezioni
--   (contratto, offerta), dai VALORI della sua testata: la versione
--   fissata se c'e'; altrimenti quella in vigore oggi
--   (vendite.fn_listino_versione_in_vigore); NULL senza listino o
--   senza una versione in vigore.
-- ⭐ Sui valori e non sull'id del documento: la chiamano anche i
--   guard BEFORE ROW di emissione e attivazione, che hanno in mano NEW
--   e congelano QUESTA versione nella stessa scrittura. Una funzione
--   per id leggerebbe la riga di prima.
-- ⛔ Non STRICT: un listino senza versione fissata (NULL) e' il caso
--   normale di un documento in bozza.
BEGIN
    IF p_listino_versione_id IS NOT NULL THEN
        RETURN p_listino_versione_id;
    END IF;

    IF p_listino_id IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN vendite.fn_listino_versione_in_vigore(p_listino_id, script.fn_data_operativa());
END;
$function$

COMMENT ON FUNCTION vendite.fn_listino_versione_operativa(p_listino_id bigint, p_listino_versione_id bigint)
IS 'Sede unica della regola «l''offerta e il contratto vivono sulla versione di listino in vigore e la congelano»: dai valori della testata restituisce la versione fissata se c''è, altrimenti quella in vigore oggi (vendite.fn_listino_versione_in_vigore), NULL senza listino o senza versione in vigore. Sui valori e non sull''id: la chiamano anche i guard BEFORE ROW di emissione dell''offerta e di attivazione del contratto, che congelano questa versione nella stessa scrittura del cambio stato. Consumatori: vendite.fn_documento_listino_operativo (le righe), script.fn_check_listino_congelabile (pulsanti e guard), vendite.trgfn_offerte_commerciali_guard_transizione e vendite.trgfn_contratti_freeze_listino_versione (il congelamento). STABLE, SECURITY INVOKER, non STRICT. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.1.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
