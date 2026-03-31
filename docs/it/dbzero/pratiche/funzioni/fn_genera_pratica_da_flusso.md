{% include-markdown "it/dbzero/pratiche/manual/fn_genera_pratica_da_flusso.md" %}
# ⚙️ Funzione `fn_genera_pratica_da_flusso`

```sql
CREATE FUNCTION fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_pratica_sorgente_id  pratiche.pratiche.id%TYPE;
    v_emittente_id         pratiche.pratiche.emittente_fiscale_id%TYPE;
    v_soggetto_id          pratiche.pratiche.soggetto_id%TYPE;
    v_priorita_id          pratiche.pratiche.priorita_id%TYPE;
    v_tipo_prest_dest_id   pratiche.regole_generazione.tipo_prestazione_dest_id%TYPE;
    v_stato_iniziale_id    config.stati_pratiche.id%TYPE;
    v_nuova_pratica_id     pratiche.pratiche.id%TYPE;
BEGIN
    -- Guard: parametri obbligatori
    IF p_flusso_id IS NULL OR p_flusso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_flusso_id', 'valore', p_flusso_id),
            NULL::uuid,
            'p_flusso_id obbligatorio e > 0'
        );
    END IF;

    IF p_regola_id IS NULL OR p_regola_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_regola_id', 'valore', p_regola_id),
            NULL::uuid,
            'p_regola_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera pratica_id dal flusso
    SELECT f.pratica_id
      INTO v_pratica_sorgente_id
      FROM pratiche.flussi f
     WHERE f.id = p_flusso_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_VALORE_MANCANTE',
            jsonb_build_object('flusso_id', p_flusso_id),
            NULL::uuid,
            concat('flusso_id ', p_flusso_id)
        );
    END IF;

    -- Recupera dati pratica sorgente
    SELECT p.emittente_fiscale_id, p.soggetto_id, p.priorita_id
      INTO v_emittente_id, v_soggetto_id, v_priorita_id
      FROM pratiche.pratiche p
     WHERE p.id = v_pratica_sorgente_id;

    -- Recupera regola di generazione
    SELECT rg.tipo_prestazione_dest_id
      INTO v_tipo_prest_dest_id
      FROM pratiche.regole_generazione rg
     WHERE rg.id = p_regola_id
       AND rg.attivo = true;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_CODICE',
            jsonb_build_object('regola_id', p_regola_id),
            NULL::uuid,
            p_regola_id::text, 'pratiche.regole_generazione'
        );
    END IF;

    -- Determina stato iniziale (BOZZA)
    SELECT sp.id
      INTO v_stato_iniziale_id
      FROM config.stati_pratiche sp
     WHERE sp.codice_interno = 'BOZZA'
       AND sp.attivo = true
     LIMIT 1;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_CODICE',
            jsonb_build_object('codice_interno', 'BOZZA'),
            NULL::uuid,
            'BOZZA', 'config.stati_pratiche'
        );
    END IF;

    -- Crea pratica target
    INSERT INTO pratiche.pratiche (
        emittente_fiscale_id,
        tipo_prestazione_id,
        soggetto_id,
        stato_id,
        priorita_id,
        flusso_origine_id
    ) VALUES (
        v_emittente_id,
        v_tipo_prest_dest_id,
        v_soggetto_id,
        v_stato_iniziale_id,
        v_priorita_id,
        p_flusso_id
    )
    RETURNING id INTO v_nuova_pratica_id;

    RETURN v_nuova_pratica_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
IS 'Genera nuova pratica da flusso completato secondo regola di generazione. Copia emittente/soggetto/priorita. Stato iniziale BOZZA.';
```

---
{% include-markdown "signature-core.md" %}
