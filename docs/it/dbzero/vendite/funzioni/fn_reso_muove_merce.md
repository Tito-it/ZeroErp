# ⚙️ Funzione `fn_reso_muove_merce`

```sql
CREATE FUNCTION fn_reso_muove_merce(p_reso vendite.resi)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reso_muove_merce(p_reso vendite.resi)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: «questo reso fa rientrare merce?» — ha almeno una voce (vedi
--   vendite.fn_reso_merce_da_rientrare, la sede della regola).
BEGIN
    RETURN EXISTS (SELECT 1 FROM vendite.fn_reso_merce_da_rientrare(p_reso));
END;
$function$

COMMENT ON FUNCTION vendite.fn_reso_muove_merce(p_reso vendite.resi)
IS 'True se il reso fa rientrare merce: ha almeno una voce in vendite.fn_reso_merce_da_rientrare (una riga attiva la cui riga di bolla d''origine ha prelievi). Decide la porta del registro sul cambio di stato del reso (vendite.trgfn_resi_guard_transizione), la check della merce e il presidio dbops.vw_resi_confermati_senza_carico. Prende la RIGA del reso. Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
