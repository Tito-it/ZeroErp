{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_id(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_emittente_id anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  
  SELECT m.emittente_soggetto_ruolo_id
    INTO v_emittente_id
    FROM anagrafiche.emittenti_fiscali_billing_account m
   WHERE m.billing_account_id = p_billing_account_id;

  IF v_emittente_id IS NOT NULL THEN
    RETURN v_emittente_id;
  END IF;

  
  SELECT m.emittente_soggetto_ruolo_id
    INTO v_emittente_id
    FROM anagrafiche.emittenti_fiscali_billing_account m
   WHERE m.is_default = true;

  IF v_emittente_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'fn_get_emittente_fiscale_id',
      'E_EMITTENTE_DEFAULT_MISSING',
      jsonb_build_object(
        'detail', 'Emittente fiscale di default mancante',
        'billing_account_id', p_billing_account_id
      ),
      NULL::uuid,
      concat('Emittente fiscale di default mancante ',
        'billing_account_id ', p_billing_account_id::text)
      
    );
  END IF;

  RETURN v_emittente_id;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id bigint)
IS 'ATTENZIONE: nonostante il nome, restituisce soggetto_ruolo_id (anagrafiche.soggetti_ruoli.id), NON emittenti_fiscali.id. Catena: 1) mapping specifico per billing_account, 2) fallback al gestore globale (is_default=true). Non filtra per attivo. Per ottenere la PK numerica reale di emittenti_fiscali usare fn_get_emittente_fiscale_pk. Usata da ~33 funzioni del dominio vendite che ragionano su soggetto_ruolo_id.';
```

---
{% include-markdown "signature-core.md" %}
