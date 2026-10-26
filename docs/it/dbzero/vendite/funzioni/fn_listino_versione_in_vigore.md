{% include-markdown "it/dbzero/vendite/manual/fn_listino_versione_in_vigore.md" %}
# ⚙️ Funzione `fn_listino_versione_in_vigore`

```sql
CREATE FUNCTION fn_listino_versione_in_vigore(p_listino_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listino_versione_in_vigore(p_listino_id bigint, p_data date)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la versione del listino in vigore alla data: ATTIVA o CHIUSA
--   (la BOZZA non e' operativa), attiva, la cui validita' contiene la
--   data. NULL se non ce n'e' una.
-- ⭐ Al piu' UNA per costruzione: ex_listini_versioni_no_overlap vale
--   per ATTIVA e CHIUSA, e le date di una CHIUSA sono bloccate
--   (trgfn_listini_versioni_guard_date_chiusa). Per questo qui non si
--   ordina ne' si limita.
DECLARE
    v_versione_id vendite.listini_versioni.id%TYPE;
BEGIN
    SELECT lv.id
      INTO v_versione_id
      FROM vendite.listini_versioni lv
     WHERE lv.listino_id = p_listino_id
       AND lv.attivo IS TRUE
       AND lv.stato IN ('ATTIVA', 'CHIUSA')
       AND lv.validita @> p_data;

    RETURN v_versione_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_listino_versione_in_vigore(p_listino_id bigint, p_data date)
IS 'La versione di un listino in vigore a una data: ATTIVA o CHIUSA (la BOZZA non e'' operativa), attiva, la cui validita'' contiene la data; NULL se non ce n''e''. Sede UNICA dal 2026-09-28 (brief-db-liste-righe-documento §8.15): la regola era scritta sette volte in sei funzioni, cinque che ne sceglievano una e due che le guardavano tutte. Decisione di Tid: «le versioni valide oggi», e il buco chiuso — ex_listini_versioni_no_overlap vale per ATTIVA e CHIUSA, e le date di una CHIUSA non si modificano (trgfn_listini_versioni_guard_date_chiusa) — quindi la versione valida e'' al piu'' una per costruzione e la funzione non ordina ne'' limita. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
