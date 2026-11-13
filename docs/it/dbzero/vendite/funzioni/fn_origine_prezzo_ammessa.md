# ⚙️ Funzione `fn_origine_prezzo_ammessa`

```sql
CREATE FUNCTION fn_origine_prezzo_ammessa(p_origine character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_origine_prezzo_ammessa(p_origine character varying)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT p_origine IS NULL
        OR p_origine IN ('PROMO', 'CONTRATTO_OVERRIDE', 'CONTRATTO_LISTINO',
                         'CATEGORIA', 'MANUALE', 'LISTINO_BUNDLE', 'COMPONENTI');
$function$

COMMENT ON FUNCTION vendite.fn_origine_prezzo_ammessa(p_origine character varying)
IS 'L''elenco unico delle origini del prezzo: vero se l''origine e'' ammessa o NULL. PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA e LISTINO_BUNDLE vengono dal resolver dei prezzi; MANUALE e'' un prezzo scritto da una persona o di cui nessuno ha dichiarato la provenienza; COMPONENTI e'' un prezzo che e'' la somma dei componenti della riga, ciascuno con la sua provenienza. La leggono i CHECK di ogni tabella con origine_prezzo e vendite.fn_provenienza_prezzo_coerente. Se l''origine e'' dovuta lo dice chi la pretende, non questa funzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
