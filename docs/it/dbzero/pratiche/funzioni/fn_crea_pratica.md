{% include-markdown "it/dbzero/pratiche/manual/fn_crea_pratica.md" %}
# ⚙️ Funzione `fn_crea_pratica`

```sql
CREATE FUNCTION fn_crea_pratica(p_emittente_fiscale_id bigint, p_tipo_prestazione_id integer, p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_priorita_id integer, p_descrizione text, p_meta jsonb, p_billing_account_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_crea_pratica(p_emittente_fiscale_id bigint, p_tipo_prestazione_id integer, p_soggetto_id uuid DEFAULT NULL::uuid, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_priorita_id integer DEFAULT NULL::integer, p_descrizione text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb, p_billing_account_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_id    pratiche.pratiche.stato_id%TYPE;
    v_priorita_id pratiche.pratiche.priorita_id%TYPE := p_priorita_id;
    v_pratica_id  pratiche.pratiche.id%TYPE;
BEGIN
    -- Stato iniziale APERTA.
    SELECT sp.id INTO v_stato_id
      FROM config.stati_pratiche sp
     WHERE sp.codice_interno = 'APERTA';
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pratiche.fn_crea_pratica', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_pratiche.APERTA'),
            NULL::uuid,
            VARIADIC ARRAY['stato iniziale APERTA (config.stati_pratiche)']);
    END IF;

    -- Priorita' default NORMALE se non fornita.
    IF v_priorita_id IS NULL THEN
        SELECT pp.id INTO v_priorita_id
          FROM config.priorita_pratiche pp
         WHERE pp.codice_interno = 'NORMALE';
        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pratiche.fn_crea_pratica', 'E_CONFIG_MANCANTE',
                jsonb_build_object('config', 'config.priorita_pratiche.NORMALE'),
                NULL::uuid,
                VARIADIC ARRAY['priorita default NORMALE (config.priorita_pratiche)']);
        END IF;
    END IF;

    INSERT INTO pratiche.pratiche (
        emittente_fiscale_id, tipo_prestazione_id, soggetto_id,
        soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id,
        descrizione, meta,
        billing_account_id
    ) VALUES (
        p_emittente_fiscale_id, p_tipo_prestazione_id, p_soggetto_id,
        p_soggetto_ruolo_id, p_istanza_utility_id, v_stato_id, v_priorita_id,
        p_descrizione, COALESCE(p_meta, '{}'::jsonb),
        p_billing_account_id
    )
    RETURNING id INTO v_pratica_id;

    RETURN v_pratica_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_crea_pratica(p_emittente_fiscale_id bigint, p_tipo_prestazione_id integer, p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_priorita_id integer, p_descrizione text, p_meta jsonb, p_billing_account_id bigint)
IS 'Building block condiviso: crea una pratica (stato APERTA, priorita'' default NORMALE) con INSERT guardato dai trigger di pratiche.pratiche. NON include il guard pre/post-attivazione (solo Python). SECURITY INVOKER. Riusata dai madre di dominio (preventivo/ordine/...). Piano: analisi-fix-transazioni Classe A. rev 2026-10-08 (20261008-67): parametro p_billing_account_id in CODA (DEFAULT NULL) — il cliente di cui parla la pratica, a grana fine; i chiamanti per nome non cambiano. Brief: brief-db-istanza-nasce-col-ba (R-8, D-9).';
```

</div>

---
{% include-markdown "signature-core.md" %}
