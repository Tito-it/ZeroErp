{% include-markdown "it/dbzero/script/manual/fn_check_utility_istanza_coerenza.md" %}
# ⚙️ Funzione `fn_check_utility_istanza_coerenza`

```sql
CREATE FUNCTION fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Guard input: NULL su entrambi -> incoerente per default
    IF p_istanza_utility_id IS NULL OR p_utility_id IS NULL THEN
        RETURN false;
    END IF;

    -- Fonte 1: billing_account
    -- UNIQUE (istanza_utility_id, utility_id) tramite uq_billing_instance_utility
    IF EXISTS (
        SELECT 1 FROM anagrafiche.billing_account
         WHERE istanza_utility_id = p_istanza_utility_id
           AND utility_id         = p_utility_id
    ) THEN
        RETURN true;
    END IF;

    -- Fonte 2: istanze_dati_precontrattuali
    -- UNIQUE (istanza_utility_id, utility_id)
    IF EXISTS (
        SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali
         WHERE istanza_utility_id = p_istanza_utility_id
           AND utility_id         = p_utility_id
    ) THEN
        RETURN true;
    END IF;

    -- Fonte 3: clienti
    -- (istanza_utility_id, utility_id) entrambi presenti, no UNIQUE esplicito
    -- ma per costruzione 1:1 cliente <-> istanza
    IF EXISTS (
        SELECT 1 FROM anagrafiche.clienti
         WHERE istanza_utility_id = p_istanza_utility_id
           AND utility_id         = p_utility_id
    ) THEN
        RETURN true;
    END IF;

    RETURN false;
END
$function$

COMMENT ON FUNCTION script.fn_check_utility_istanza_coerenza(p_istanza_utility_id bigint, p_utility_id integer)
IS 'Pure check (no raise): true se la coppia (istanza_utility_id, utility_id) e'' coerente con almeno 1 fonte satellite (billing_account, istanze_dati_precontrattuali, clienti). Lista fonti allineata a anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata. Riusabile cross-tabella (preventivi, attivita_fatturabili, ...).';
```

---
{% include-markdown "signature-core.md" %}
