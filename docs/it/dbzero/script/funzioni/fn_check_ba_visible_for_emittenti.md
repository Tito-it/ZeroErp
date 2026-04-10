# ⚙️ Funzione `fn_check_ba_visible_for_emittenti`

```sql
CREATE FUNCTION fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
BEGIN
    -- Convenzione fn_check_*: pure boolean, nessun raise.
    -- Il chiamante gestisce il NULL di p_emittente_ids (= nessuna
    -- restrizione) PRIMA di invocare questa funzione.

    -- BA NULL = non visibile (no BA = no mapping possibile)
    IF p_billing_account_id IS NULL THEN
        RETURN false;
    END IF;

    -- Array vuoto o NULL = nessun emittente autorizzato = non visibile
    IF p_emittente_ids IS NULL OR array_length(p_emittente_ids, 1) IS NULL THEN
        RETURN false;
    END IF;

    -- 1) Mapping specifico: il BA ha una riga in
    --    emittenti_fiscali_billing_account collegata a uno degli
    --    emittenti autorizzati.
    IF EXISTS (
        SELECT 1
          FROM anagrafiche.emittenti_fiscali_billing_account efba
         WHERE efba.emittente_soggetto_ruolo_id = ANY(p_emittente_ids)
           AND efba.billing_account_id = p_billing_account_id
    ) THEN
        RETURN true;
    END IF;

    -- 2) Fallback default: un emittente autorizzato ha is_default=true
    --    (gestore globale) E il BA non ha nessun mapping specifico
    --    su nessun emittente. Il gestore globale "copre" i BA non
    --    ancora mappati esplicitamente.
    IF EXISTS (
        SELECT 1
          FROM anagrafiche.emittenti_fiscali_billing_account efba
         WHERE efba.emittente_soggetto_ruolo_id = ANY(p_emittente_ids)
           AND efba.is_default = true
    )
    AND NOT EXISTS (
        SELECT 1
          FROM anagrafiche.emittenti_fiscali_billing_account efba2
         WHERE efba2.billing_account_id = p_billing_account_id
    ) THEN
        RETURN true;
    END IF;

    -- 3) Ne' mapping specifico ne' fallback default: non visibile
    RETURN false;
END
$function$

COMMENT ON FUNCTION script.fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
IS 'Pure check (fn_check_*, boolean, no raise): un billing_account e'' visibile per un set di emittenti autorizzati? Logica a 3 livelli: 1) mapping specifico BA->emittente, 2) fallback default (is_default=true) se BA non ha mapping, 3) non visibile. Usata da fn_search_soggetti_universale e fn_get_search_detail per il filtro scope emittente ramo CL.';
```

---
{% include-markdown "signature-core.md" %}
