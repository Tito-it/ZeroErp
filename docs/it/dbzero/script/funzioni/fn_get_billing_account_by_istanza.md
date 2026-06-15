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
    -- Tipo ancorato alla colonna sorgente (%TYPE): segue
    -- automaticamente eventuali cambi di tipo del BA.
    v_billing_account_id anagrafiche.clienti.billing_account_id%TYPE;
BEGIN
    -- =====================================================
    -- Scopo:
    --   Dato l'id di una istanza utility, restituire il
    --   billing account del cliente attivo su quell'istanza.
    --   NULL se l'istanza non ha cliente (prospect puro):
    --   il preventivo ammette BA nullo, offerta/contratto
    --   sono gated lato FE (requiresActiveClient).
    -- =====================================================

    -- Guard input esplicito (resolver di lettura): NULL o
    -- valore non valido -> NULL, niente raise. Allineato al
    -- comportamento di fn_get_stato_cliente_by_istanza.
    IF p_istanza_id IS NULL OR p_istanza_id <= 0 THEN
        RETURN NULL;
    END IF;

    -- anagrafiche.clienti ha UNIQUE(istanza_utility_id) ->
    -- al piu' 1 riga per istanza. ORDER BY id DESC + LIMIT 1
    -- e' difensivo (idempotente rispetto all'unicita').
    SELECT c.billing_account_id
      INTO v_billing_account_id
      FROM anagrafiche.clienti c
     WHERE c.istanza_utility_id = p_istanza_id
     ORDER BY c.id DESC
     LIMIT 1;

    RETURN v_billing_account_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_billing_account_by_istanza(p_istanza_id bigint)
IS 'Resolver di lettura: billing_account_id del cliente attivo per l''istanza utility, NULL se prospect (nessun cliente) o input NULL/<=0. Specchio di fn_get_stato_cliente_by_istanza. Coerenza (istanza,BA) garantita dalla FK fk_clienti_billing_account. Consumata dal dettaglio pratica (contesto cliente per i documenti aperti dal flusso).';
```

---
{% include-markdown "signature-core.md" %}
