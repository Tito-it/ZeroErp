# ⚙️ Funzione `fn_provenienza_prezzo_coerente`

```sql
CREATE FUNCTION fn_provenienza_prezzo_coerente(p_origine character varying, p_prezzo numeric, p_listino_versione_id bigint, p_listino_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provenienza_prezzo_coerente(p_origine character varying, p_prezzo numeric, p_listino_versione_id bigint, p_listino_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN NOT vendite.fn_origine_prezzo_ammessa(p_origine) THEN false
        WHEN p_prezzo IS NULL THEN
             p_origine IS NULL
         AND p_listino_versione_id IS NULL
         AND p_listino_riga_id IS NULL
        WHEN p_origine IS NULL THEN false
        WHEN p_listino_riga_id IS NOT NULL
         AND p_listino_versione_id IS NULL THEN false
        WHEN p_origine IN ('MANUALE', 'COMPONENTI') THEN
             p_listino_versione_id IS NULL
         AND p_listino_riga_id IS NULL
        ELSE true
    END;
$function$

COMMENT ON FUNCTION vendite.fn_provenienza_prezzo_coerente(p_origine character varying, p_prezzo numeric, p_listino_versione_id bigint, p_listino_riga_id bigint)
IS 'Vero se la provenienza del prezzo di una riga di documento e'' coerente col prezzo: l''origine e'' ammessa (vendite.fn_origine_prezzo_ammessa); senza prezzo non c''e'' provenienza (origine, versione e riga di listino NULL); con un prezzo c''e'' un''origine; una riga di listino porta la sua versione; MANUALE e COMPONENTI non citano listino. Mai NULL. La leggono i CHECK chk_<tabella>_provenienza_prezzo delle righe principali e dei componenti di preventivi, ordini, contratti, DDT e offerte. Che la riga di listino sia dell''articolo, dell''emittente e di una versione non in bozza lo giudica il trigger vendite.trgfn_riga_documento_guard_listino_provenienza, che legge altre tabelle.';
```

</div>

---
{% include-markdown "signature-core.md" %}
