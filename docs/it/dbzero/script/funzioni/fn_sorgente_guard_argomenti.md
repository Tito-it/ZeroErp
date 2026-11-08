# ⚙️ Funzione `fn_sorgente_guard_argomenti`

```sql
CREATE FUNCTION fn_sorgente_guard_argomenti(p_argomenti text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_guard_argomenti(p_argomenti text[])
 RETURNS TABLE(livello_minimo text, azione_cancellazione text, valido boolean)
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE ROWS 1
BEGIN ATOMIC
 SELECT a.livello,
     a.azione,
     ((a.livello = ANY (ARRAY['DOCUMENTO'::text, 'RIGA'::text, 'DETTAGLIO'::text])) AND (a.azione = ANY (ARRAY['BLOCCA'::text, 'CANCELLA'::text])) AND (COALESCE(cardinality(fn_sorgente_guard_argomenti.p_argomenti), 0) <= 2))
    FROM ( SELECT COALESCE(upper(btrim((fn_sorgente_guard_argomenti.p_argomenti)[array_lower(fn_sorgente_guard_argomenti.p_argomenti, 1)])), 'DOCUMENTO'::text) AS livello,
             COALESCE(upper(btrim((fn_sorgente_guard_argomenti.p_argomenti)[(array_lower(fn_sorgente_guard_argomenti.p_argomenti, 1) + 1)])), 'BLOCCA'::text) AS azione) a;
END

COMMENT ON FUNCTION script.fn_sorgente_guard_argomenti(p_argomenti text[])
IS 'La grammatica degli argomenti del guard della provenienza (script.trgfn_guard_sorgente): il primo e'' il livello minimo che la tabella chiede (DOCUMENTO, il default, RIGA o DETTAGLIO), il secondo l''azione quando il documento, la riga o il dettaglio di origine si cancella (BLOCCA, il default, o CANCELLA). Maiuscole e spazi non contano. valido = false su un valore fuori elenco o su piu'' di due argomenti. Legge l''array dal suo primo indice, quindi vale per TG_ARGV (da 0) e per dbops.fn_trigger_argomenti (da 1): il trigger e chi legge pg_trigger.tgargs usano questa, non una copia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
