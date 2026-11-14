{% include-markdown "it/dbzero/vendite/manual/fn_offerta_scaduta.md" %}
# ⚙️ Funzione `fn_offerta_scaduta`

```sql
CREATE FUNCTION fn_offerta_scaduta(p_esito character varying, p_validita_al date, p_data_riferimento date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_scaduta(p_esito character varying, p_validita_al date, p_data_riferimento date)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Scaduta = il cliente non ha ancora risposto (lo stato non ha un
    -- esito) e la validita' e' passata. Senza validita' non scade.
    SELECT p_esito IS NULL
       AND p_validita_al IS NOT NULL
       AND p_validita_al < p_data_riferimento;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_scaduta(p_esito character varying, p_validita_al date, p_data_riferimento date)
IS 'true = l''offerta e'' scaduta: il cliente non ha ancora risposto (p_esito, la colonna esito dello stato corrente in config.stati_doc_offerte, e'' NULL) e la validita'' (p_validita_al) e'' passata rispetto a p_data_riferimento. Senza validita'' l''offerta non scade; un''offerta accettata, rifiutata, superata o annullata ha un esito e non e'' scaduta. Il chiamante passa la data operativa dell''azienda, script.fn_data_operativa(). Pura sui valori (IMMUTABLE, LANGUAGE sql): vendite.vw_offerte_commerciali_lista la incorpora per is_scaduta, il dettaglio dell''offerta la chiama sulla sua riga. Non e'' STRICT: esito NULL e'' il caso normale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
