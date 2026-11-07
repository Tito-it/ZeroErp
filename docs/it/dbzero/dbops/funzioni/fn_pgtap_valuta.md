{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_valuta.md" %}
# ⚙️ Funzione `fn_pgtap_valuta`

```sql
CREATE FUNCTION fn_pgtap_valuta()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_valuta()
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la valuta di una fixture pgTAP che non ha una catena da cui
--   risolverla: le radici della risoluzione del dominio (billing account,
--   emittente, gestore), che la valuta la danno agli altri. I documenti
--   la chiedono invece alla catena (vendite.fn_get_valuta_id).
-- Uso:
--   'valuta_id', dbops.fn_pgtap_valuta()
DECLARE
    v_valuta config.valute.id%TYPE;
BEGIN
    -- La prima del catalogo, per id: config.valute e' seed, e la scelta
    -- non cambia fra un'esecuzione e l'altra.
    SELECT v.id INTO v_valuta
      FROM config.valute v
     ORDER BY v.id
     LIMIT 1;
    IF v_valuta IS NULL THEN
        RAISE EXCEPTION 'dbops.fn_pgtap_valuta: config.valute e'' vuota — e'' un seed di 80_data, non un dato di macchina';
    END IF;
    RETURN v_valuta;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_valuta()
IS 'Fixture pgTAP (building block): la valuta per una fixture che non ha una catena da cui risolverla, cioe'' le radici della risoluzione del dominio (vendite.fn_get_valuta_id: billing account, poi emittente, poi gestore): la usano dbops.fn_pgtap_crea_cliente_ba, dbops.fn_pgtap_crea_emittente e dbops.fn_pgtap_crea_gestore. La prima di config.valute per id, che e'' seed: la scelta non cambia fra un''esecuzione e l''altra. I builder di documento non la usano: chiedono la valuta alla catena, come i trigger di default. Catalogo vuoto: RAISE EXCEPTION. STABLE: non scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
