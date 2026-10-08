{% include-markdown "it/dbzero/script/manual/fn_get_billing_account_by_istanza.md" %}
# ⚙️ Funzione `fn_get_billing_account_by_istanza`

```sql
CREATE FUNCTION fn_get_billing_account_by_istanza(p_istanza_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_billing_account_by_istanza(p_istanza_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_billing_account_id anagrafiche.billing_account.id%TYPE;
BEGIN
    IF p_istanza_id IS NULL OR p_istanza_id <= 0 THEN
        RETURN NULL;
    END IF;

    -- Il BA dell'istanza, se e' UNO. Un'istanza puo' avere piu' utility,
    -- ognuna col suo BA: con piu' di uno la domanda non ha una risposta,
    -- e la funzione non ne sceglie uno (niente LIMIT 1).
    SELECT min(ba.id)
      INTO v_billing_account_id
      FROM anagrafiche.billing_account ba
     WHERE ba.istanza_utility_id = p_istanza_id
    HAVING count(*) = 1;

    RETURN v_billing_account_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_billing_account_by_istanza(p_istanza_id bigint)
IS 'Resolver di lettura: il billing account dell''istanza, SE l''istanza ne ha uno solo; NULL se ne ha piu'' d''uno (istanza con piu'' utility) o input NULL/<=0. Mai un LIMIT 1. ⚠️ IN RITIRO (2026-10-08): il suo consumatore, il dettaglio pratica del backend, deve leggere pratiche.billing_account_id (20261008-63, D-9); quando non lo chiama piu'' nessuno si cancella. Fino al 2026-10-08 leggeva il BA del cliente dell''istanza con ORDER BY id DESC LIMIT 1, contando su «un cliente per istanza» (non piu'' vero: un cliente per BA, 20261008-64). Brief: brief-db-istanza-nasce-col-ba (R-8).';
```

---
{% include-markdown "signature-core.md" %}
