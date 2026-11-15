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
-- Scopo: la versione del listino in vigore alla data: fuori dalla
--   bozza (non nello stato iniziale del vocabolario: la bozza non e'
--   operativa), attiva, la cui validita' contiene la data. NULL se non
--   ce n'e' una.
-- ⭐ Al piu' UNA per costruzione: ex_listini_versioni_no_overlap vale
--   per le versioni fuori dalla bozza (gli id del seed nel predicato),
--   e le date di una CHIUSA sono bloccate
--   (trgfn_listini_versioni_guard_per_stato). Per questo qui non si
--   ordina ne' si limita.
DECLARE
    v_versione_id vendite.listini_versioni.id%TYPE;
BEGIN
    SELECT lv.id
      INTO v_versione_id
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.listino_id = p_listino_id
       AND lv.attivo IS TRUE
       AND NOT s.iniziale
       AND lv.validita @> p_data;

    RETURN v_versione_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_listino_versione_in_vigore(p_listino_id bigint, p_data date)
IS 'La versione di un listino in vigore a una data: fuori dalla bozza (non nello stato iniziale del vocabolario config.stati_doc_listino_versioni: la bozza non e'' operativa), attiva, la cui validita'' contiene la data; NULL se non ce n''e''. Sede unica della regola. La versione valida e'' al piu'' una per costruzione: ex_listini_versioni_no_overlap vale per le versioni fuori dalla bozza (gli id del seed stanno nel suo predicato, e vendite/test-listino-versione-al-modello-v1 li confronta coi codici), e le date di una versione chiusa non si modificano (vendite.trgfn_listini_versioni_guard_per_stato); per questo la funzione non ordina ne'' limita. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
