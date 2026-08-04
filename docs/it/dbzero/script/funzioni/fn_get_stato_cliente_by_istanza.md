{% include-markdown "it/dbzero/script/manual/fn_get_stato_cliente_by_istanza.md" %}
# ⚙️ Funzione `fn_get_stato_cliente_by_istanza`

```sql
CREATE FUNCTION fn_get_stato_cliente_by_istanza(p_istanza_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stato_cliente_by_istanza(p_istanza_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
-- 1. Funzione di recupero stato_cliente per un'istanza
--
-- rev 2026-08-04 (bonifica riferimenti morti, F6): la SELECT era nuda —
--   senza INTO e senza RETURN. In plpgsql una query senza destinazione e'
--   un errore (42601), e anche superandolo la funzione sarebbe uscita
--   senza valore (2F005). Non ha mai potuto restituire niente.
RETURN COALESCE(
    (SELECT c.stato_cliente_id
    FROM anagrafiche.clienti c
    WHERE c.istanza_utility_id = p_istanza_id 
    ORDER BY c.id DESC
    LIMIT 1),
    (SELECT id
    FROM config.stati_cliente
    WHERE codice_interno = 'IS'
    LIMIT 1)
);
END
$function$

COMMENT ON FUNCTION script.fn_get_stato_cliente_by_istanza(p_istanza_id bigint)
IS ' Restituisce lo stato di un cliente in base alla istanza. ';
```

---
{% include-markdown "signature-core.md" %}
