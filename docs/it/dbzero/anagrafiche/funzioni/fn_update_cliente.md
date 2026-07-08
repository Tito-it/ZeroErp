{% include-markdown "it/dbzero/anagrafiche/manual/fn_update_cliente.md" %}
# ⚙️ Funzione `fn_update_cliente`

```sql
CREATE FUNCTION fn_update_cliente(p_cliente_id bigint, p_ba_categoria_cliente_id smallint, p_cliente_fields jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_update_cliente(p_cliente_id bigint, p_ba_categoria_cliente_id smallint DEFAULT NULL::smallint, p_cliente_fields jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(cliente_id bigint, categoria_aggiornata boolean, campi_aggiornati boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_id           anagrafiche.clienti.billing_account_id%TYPE;
    v_fields          jsonb   := COALESCE(p_cliente_fields, '{}'::jsonb);
    v_has_fields      boolean;
    v_ba_changed      boolean := false;
    v_cliente_changed boolean := false;
BEGIN
    -- ----------------------------------------------------
    -- 1) Esistenza cliente + risoluzione del suo BA.
    --    (La FK clienti.billing_account_id garantisce che il
    --     BA esista; lo risolviamo per la scrittura categoria.)
    -- ----------------------------------------------------
    SELECT c.billing_account_id
      INTO v_ba_id
      FROM anagrafiche.clienti c
     WHERE c.id = p_cliente_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_update_cliente',
            'E_CLIENTE_NON_TROVATO',
            jsonb_build_object('cliente_id', p_cliente_id),
            NULL::uuid,
            VARIADIC ARRAY[p_cliente_id::text]
        );
    END IF;

    -- ----------------------------------------------------
    -- 2) Categoria sul BA (solo se fornita; mai a NULL).
    -- ----------------------------------------------------
    IF p_ba_categoria_cliente_id IS NOT NULL THEN
        UPDATE anagrafiche.billing_account ba
           SET categoria_cliente_id = p_ba_categoria_cliente_id
         WHERE ba.id = v_ba_id;
        v_ba_changed := true;
    END IF;

    -- ----------------------------------------------------
    -- 3) Campi editabili del cliente (delta whitelisted).
    --    Aggiorniamo solo se almeno una chiave whitelisted
    --    e' presente, per non generare UPDATE/storico a vuoto.
    -- ----------------------------------------------------
    SELECT count(*) > 0
      INTO v_has_fields
      FROM jsonb_object_keys(v_fields) AS k
     WHERE k IN (
               'iva_id', 'modalita_pagamento_id', 'termine_pagamento_id',
               'tipo_gg_scadenza_ft', 'nr_giorni_scadenza',
               'cliente_pa', 'split_payment',
               'codice_cig', 'codice_cup', 'codice_commessa',
               'servizio_da_fatturare',
               'garanzia_tipo', 'garanzia_importo'
           );

    IF v_has_fields THEN
        UPDATE anagrafiche.clienti c
           SET iva_id = CASE WHEN jsonb_exists(v_fields, 'iva_id')
                             THEN (v_fields->>'iva_id')::integer
                             ELSE c.iva_id END,
               modalita_pagamento_id = CASE WHEN jsonb_exists(v_fields, 'modalita_pagamento_id')
                             THEN (v_fields->>'modalita_pagamento_id')::integer
                             ELSE c.modalita_pagamento_id END,
               termine_pagamento_id = CASE WHEN jsonb_exists(v_fields, 'termine_pagamento_id')
                             THEN (v_fields->>'termine_pagamento_id')::bigint
                             ELSE c.termine_pagamento_id END,
               tipo_gg_scadenza_ft = CASE WHEN jsonb_exists(v_fields, 'tipo_gg_scadenza_ft')
                             THEN (v_fields->>'tipo_gg_scadenza_ft')
                             ELSE c.tipo_gg_scadenza_ft END,
               nr_giorni_scadenza = CASE WHEN jsonb_exists(v_fields, 'nr_giorni_scadenza')
                             THEN (v_fields->>'nr_giorni_scadenza')::integer
                             ELSE c.nr_giorni_scadenza END,
               cliente_pa = CASE WHEN jsonb_exists(v_fields, 'cliente_pa')
                             THEN (v_fields->>'cliente_pa')
                             ELSE c.cliente_pa END,
               split_payment = CASE WHEN jsonb_exists(v_fields, 'split_payment')
                             THEN (v_fields->>'split_payment')
                             ELSE c.split_payment END,
               codice_cig = CASE WHEN jsonb_exists(v_fields, 'codice_cig')
                             THEN (v_fields->>'codice_cig')
                             ELSE c.codice_cig END,
               codice_cup = CASE WHEN jsonb_exists(v_fields, 'codice_cup')
                             THEN (v_fields->>'codice_cup')
                             ELSE c.codice_cup END,
               codice_commessa = CASE WHEN jsonb_exists(v_fields, 'codice_commessa')
                             THEN (v_fields->>'codice_commessa')
                             ELSE c.codice_commessa END,
               servizio_da_fatturare = CASE WHEN jsonb_exists(v_fields, 'servizio_da_fatturare')
                             THEN (v_fields->>'servizio_da_fatturare')::boolean
                             ELSE c.servizio_da_fatturare END,
               garanzia_tipo = CASE WHEN jsonb_exists(v_fields, 'garanzia_tipo')
                             THEN (v_fields->>'garanzia_tipo')
                             ELSE c.garanzia_tipo END,
               garanzia_importo = CASE WHEN jsonb_exists(v_fields, 'garanzia_importo')
                             THEN (v_fields->>'garanzia_importo')::numeric
                             ELSE c.garanzia_importo END
         WHERE c.id = p_cliente_id;

        v_cliente_changed := true;
    END IF;

    RETURN QUERY
    SELECT p_cliente_id, v_ba_changed, v_cliente_changed;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_update_cliente(p_cliente_id bigint, p_ba_categoria_cliente_id smallint, p_cliente_fields jsonb)
IS 'Funzione madre atomica: aggiorna la categoria cliente sul billing_account e/o i campi editabili del cliente in un''unica statement (o tutto o rollback). SECURITY INVOKER: RLS e scope emittente restano applicati. Ritorna (cliente_id, categoria_aggiornata, campi_aggiornati). Cliente inesistente => E_CLIENTE_NON_TROVATO. Piano: analisi-fix-transazioni Classe A #1.';
```

---
{% include-markdown "signature-core.md" %}
