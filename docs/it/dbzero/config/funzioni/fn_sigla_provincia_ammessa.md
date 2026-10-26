# ⚙️ Funzione `fn_sigla_provincia_ammessa`

```sql
CREATE FUNCTION fn_sigla_provincia_ammessa(p_sigla character varying, p_stato_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_sigla_provincia_ammessa(p_sigla character varying, p_stato_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   La sigla di una provincia e' ammessa? Per una provincia
  --   italiana (stato con codice_iso2 = 'IT') due lettere
  --   maiuscole; per ogni altra maiuscole e cifre, da 1 a 10
  --   (la stessa forma di chk_province_sigla_forma).
  --   Stato NULL (provincia senza regione, o regione senza
  --   stato): non si sa se e' italiana, vale la forma generale.
  --   Pura sul risultato: non solleva, la usano i guard.
  -- =========================================================
  IF p_sigla IS NULL THEN
    RETURN false;
  END IF;

  IF EXISTS (SELECT 1 FROM config.stati s
              WHERE s.id = p_stato_id AND s.codice_iso2 = 'IT') THEN
    RETURN p_sigla ~ '^[A-Z]{2}$';
  END IF;

  RETURN p_sigla ~ '^[A-Z0-9]{1,10}$';
END;
$function$

COMMENT ON FUNCTION config.fn_sigla_provincia_ammessa(p_sigla character varying, p_stato_id integer)
IS 'La sigla di una provincia e'' ammessa? Italia (codice_iso2 = IT): due lettere maiuscole; altrimenti maiuscole e cifre, da 1 a 10 (come chk_province_sigla_forma). Stato NULL: forma generale. Non solleva: la leggono trgfn_province_guard_sigla e trgfn_regioni_guard_sigla_province. Brief: brief-db-character-n-spazi-di-riempimento D-2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
