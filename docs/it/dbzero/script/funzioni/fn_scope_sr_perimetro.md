# ⚙️ Funzione `fn_scope_sr_perimetro`

```sql
CREATE FUNCTION fn_scope_sr_perimetro(p_perimetro bigint, p_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_sr_perimetro(p_perimetro bigint, p_soggetto_ruolo_id bigint)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: il soggetto della riga e' quello di chi guarda? La funzione di
    --   scope delle policy di controparte (linee-guida-sql §10.3). Il
    --   perimetro glielo passa la policy, gia' calcolato da
    --   script.fn_get_identita_sr_perimetro.
    -- COALESCE: perimetro NULL (nessuno) o soggetto NULL -> false, non NULL.
    SELECT coalesce(p_soggetto_ruolo_id = p_perimetro, false)
$function$

COMMENT ON FUNCTION script.fn_scope_sr_perimetro(p_perimetro bigint, p_soggetto_ruolo_id bigint)
IS 'Funzione di scope delle policy di controparte (linee-guida-sql §10.3): il soggetto_ruolo della riga e'' quello di chi guarda? Il perimetro lo passa la policy, calcolato una volta per istruzione da script.fn_get_identita_sr_perimetro in una sottoquery non correlata. Pura e incorporata dal pianificatore: per riga resta COALESCE(soggetto = perimetro, false). Perimetro NULL (nessuno) o soggetto NULL -> false. Rev 2026-10-21 (20261021-29, giro 2 di brief-db-perimetro-una-volta-famiglie-residue).';
```

</div>

---
{% include-markdown "signature-core.md" %}
