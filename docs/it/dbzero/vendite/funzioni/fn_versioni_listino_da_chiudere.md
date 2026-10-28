{% include-markdown "it/dbzero/vendite/manual/fn_versioni_listino_da_chiudere.md" %}
# ⚙️ Funzione `fn_versioni_listino_da_chiudere`

```sql
CREATE FUNCTION fn_versioni_listino_da_chiudere(p_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_versioni_listino_da_chiudere(p_versione_id bigint)
 RETURNS TABLE(versione_id bigint, codice_versione character varying, valido_dal date, valido_al_prima date, valido_al_dopo date)
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: le versioni che l'attivazione di p_versione_id chiude,
    --   con la data di fine che prenderebbero. Vedi l'intestazione
    --   del changeSet 20261028-11.
    SELECT p.id, p.codice_versione, p.valido_dal, p.valido_al,
           n.valido_dal - 1
      FROM vendite.listini_versioni n
      JOIN vendite.listini_versioni p
        ON p.listino_id = n.listino_id
       AND p.id <> n.id
      JOIN config.stati_doc_listino_versioni s
        ON s.id = p.stato_doc_listino_versione_id
     WHERE n.id = p_versione_id
       AND p.attivo IS TRUE
       AND s.codice_interno = 'ATTIVA'
       AND p.valido_dal < n.valido_dal
       AND p.validita && daterange(n.valido_dal, NULL, '[)')
     ORDER BY p.valido_dal, p.id;
$function$

COMMENT ON FUNCTION vendite.fn_versioni_listino_da_chiudere(p_versione_id bigint)
IS 'Le versioni che l''attivazione di p_versione_id chiude (decisione D3 di sviluppo-listini-v2): attive, in stato ATTIVA, dello stesso listino, con decorrenza precedente e periodo che tocca la decorrenza nuova; valido_al_dopo = decorrenza nuova - 1. Ordinate per decorrenza. Lo chiama il verbo vendite.fn_attiva_versione_listino per chiuderle e il backend per l''anteprima del dialogo (dry_run): quello che si mostra e'' quello che si fa. Prima stava nel backend (listini_repository.find_versioni_per_autoclose). SECURITY INVOKER, STABLE. Brief: brief-modello-documento-vendita §16 (L-4, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
