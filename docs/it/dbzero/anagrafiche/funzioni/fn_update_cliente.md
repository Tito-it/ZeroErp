{% include-markdown "it/dbzero/anagrafiche/manual/fn_update_cliente.md" %}
# ⚙️ Funzione `fn_update_cliente`

```sql
CREATE FUNCTION fn_update_cliente(p_cliente_id bigint, p_ba_categoria_cliente_id smallint, p_cliente_fields jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
    --    ⚠️ rev 2026-07-31 (D-I): via `tipo_gg_scadenza_ft` e
    --    `nr_giorni_scadenza`. Le condizioni di pagamento hanno
    --    un solo meccanismo — il termine di catalogo — e le due
    --    colonne cadono con la 3a.5.
    -- ----------------------------------------------------
    SELECT count(*) > 0
      INTO v_has_fields
      FROM jsonb_object_keys(v_fields) AS k
     WHERE k IN (
               -- ⚠️ rev 2026-08-29 (brief IVA, I0-B / I8-B): via SEI chiavi.
               --   `iva_id` non aveva piu' un lavoro (D7-bis); `cliente_pa` e
               --   `split_payment` sono saliti su anagrafiche.soggetti (D8);
               --   `codice_cig`/`codice_cup`/`codice_commessa` sono andati su
               --   vendite.contratti (D9). Le colonne non esistono piu'.
               'modalita_pagamento_id', 'termine_pagamento_id',
               'servizio_da_fatturare',
               'garanzia_tipo', 'garanzia_importo'
           );

    IF v_has_fields THEN
        UPDATE anagrafiche.clienti c
           SET modalita_pagamento_id = CASE WHEN jsonb_exists(v_fields, 'modalita_pagamento_id')
                             THEN (v_fields->>'modalita_pagamento_id')::integer
                             ELSE c.modalita_pagamento_id END,
               termine_pagamento_id = CASE WHEN jsonb_exists(v_fields, 'termine_pagamento_id')
                             THEN (v_fields->>'termine_pagamento_id')::bigint
                             ELSE c.termine_pagamento_id END,
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
IS 'Funzione madre atomica: aggiorna la categoria cliente sul billing_account e/o i campi editabili del cliente in un''unica statement (o tutto o rollback). SECURITY INVOKER: RLS e scope emittente restano applicati. Ritorna (cliente_id, categoria_aggiornata, campi_aggiornati). Cliente inesistente => E_CLIENTE_NON_TROVATO. rev 2026-07-31 (D-I): rimossi dalla whitelist e dalle assegnazioni `tipo_gg_scadenza_ft` e `nr_giorni_scadenza` — le condizioni di pagamento hanno un solo meccanismo, il termine di catalogo, e le due colonne cadono con la 3a.5. La firma non cambia: i campi editabili viaggiano nel payload jsonb. Piano: analisi-fix-transazioni Classe A #1 + piano-db-satelliti-fattura 3a.5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
