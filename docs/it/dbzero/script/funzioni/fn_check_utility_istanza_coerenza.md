{% include-markdown "it/dbzero/script/manual/fn_check_utility_istanza_coerenza.md" %}
# ⚙️ Funzione `fn_check_utility_istanza_coerenza`

```sql
CREATE FUNCTION fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Guard input: un valore mancante e' incoerente.
    IF p_istanza_utility_id IS NULL OR p_utility_id IS NULL THEN
        RETURN false;
    END IF;

    -- Una sola fonte: il billing account della coppia
    -- (uq_billing_instance_utility). Dati precontrattuali e
    -- cliente lo implicano per FK (regola per coppia, D-2).
    RETURN EXISTS (
        SELECT 1
          FROM anagrafiche.billing_account ba
         WHERE ba.istanza_utility_id = p_istanza_utility_id
           AND ba.utility_id         = p_utility_id
    );
END
$function$

COMMENT ON FUNCTION script.fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
IS 'Pure check (no raise): true se la coppia (istanza_utility_id, utility_id) ha il suo billing account. ⚠️ rev 2026-10-08: fino a quel giorno le fonti erano tre (billing_account, istanze_dati_precontrattuali, clienti); con la regola di Tid «istanza e BA nascono insieme, per coppia» (D-2) le altre due implicano il BA per FK, e la fonte e'' una. Non e'' la regola del constraint trigger dell''istanza (almeno un BA): questa guarda la coppia. Chiamanti: vendite.trgfn_preventivi_guard_utility_istanza_coerenza e il backend (lookup istanze per utility, pre-validazione del preventivo). Brief: brief-db-istanza-nasce-col-ba (R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
