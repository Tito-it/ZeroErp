{% include-markdown "it/dbzero/pratiche/manual/fn_prendi_in_carico_flusso.md" %}
# ⚙️ Funzione `fn_prendi_in_carico_flusso`

```sql
CREATE FUNCTION fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
-- Scopo: assegnare un flusso DA_ESEGUIRE all'operatore corrente,
--        verificando che abbia competenza attiva per quel tipo di flusso.
-- Regole:
--   1. Il flusso deve esistere
--   2. Il flusso deve essere in stato DA_ESEGUIRE
--   3. Il flusso non deve essere gia' assegnato ad altro operatore
--   4. L'operatore deve avere competenza attiva per il template_flusso_id
-- Risultato: true se assegnato, false se gia' assegnato allo stesso operatore.
-- Errori: raise se il flusso non esiste, stato errato, o competenza mancante.
-- Nota: usa SELECT ... FOR UPDATE per evitare race condition
--       tra lettura stato e assegnazione.
DECLARE
    v_stato_id          pratiche.flussi.stato_id%TYPE;
    v_risorsa_attuale   pratiche.flussi.risorsa_umana_id%TYPE;
    v_template_id       pratiche.flussi.template_flusso_id%TYPE;
    v_da_eseguire_id    config.stati_flussi_pratiche.id%TYPE;
    v_ha_competenza     BOOLEAN;
    v_righe_aggiornate  INTEGER;
BEGIN
    -- Guard: parametri obbligatori
    IF p_flusso_id IS NULL OR p_flusso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('p_flusso_id', p_flusso_id),
            NULL::uuid,
            'p_flusso_id'
        );
    END IF;

    IF p_risorsa_umana_id IS NULL OR p_risorsa_umana_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('p_risorsa_umana_id', p_risorsa_umana_id),
            NULL::uuid,
            'p_risorsa_umana_id'
        );
    END IF;

    -- Recupera stato corrente del flusso CON LOCK (FOR UPDATE)
    -- per evitare race condition: due operatori non possono
    -- prendere in carico lo stesso flusso contemporaneamente
    SELECT f.stato_id, f.risorsa_umana_id, f.template_flusso_id
      INTO v_stato_id, v_risorsa_attuale, v_template_id
      FROM pratiche.flussi f
     WHERE f.id = p_flusso_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'E_VALORE_MANCANTE',
            jsonb_build_object('flusso_id', p_flusso_id),
            NULL::uuid,
            concat('flusso_id ', p_flusso_id)
        );
    END IF;

    -- Verifica stato DA_ESEGUIRE
    SELECT id INTO v_da_eseguire_id
      FROM config.stati_flussi_pratiche
     WHERE codice_interno = 'DA_ESEGUIRE';

    IF v_stato_id <> v_da_eseguire_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'FLUSSI_PRESA_CARICO_STATO_ERRATO',
            jsonb_build_object(
                'flusso_id', p_flusso_id,
                'stato_id', v_stato_id,
                'stato_richiesto', v_da_eseguire_id
            ),
            NULL::uuid,
            p_flusso_id::text
        );
    END IF;

    -- Gia' assegnato allo stesso operatore: noop
    IF v_risorsa_attuale = p_risorsa_umana_id THEN
        RETURN FALSE;
    END IF;

    -- Gia' assegnato ad altro operatore: errore
    IF v_risorsa_attuale IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'FLUSSI_GIA_ASSEGNATO',
            jsonb_build_object(
                'flusso_id', p_flusso_id,
                'risorsa_attuale', v_risorsa_attuale,
                'risorsa_richiedente', p_risorsa_umana_id
            ),
            NULL::uuid,
            p_flusso_id::text,
            v_risorsa_attuale::text
        );
    END IF;

    -- Verifica competenza (solo per flussi template-based)
    IF v_template_id IS NOT NULL THEN
        SELECT EXISTS (
            SELECT 1 FROM pratiche.competenze_flussi cf
             WHERE cf.template_flusso_id = v_template_id
               AND cf.risorsa_umana_id = p_risorsa_umana_id
               AND cf.attivo = true
        ) INTO v_ha_competenza;

        IF NOT v_ha_competenza THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche',
                'pratiche.fn_prendi_in_carico_flusso',
                'FLUSSI_COMPETENZA_MANCANTE',
                jsonb_build_object(
                    'flusso_id', p_flusso_id,
                    'template_flusso_id', v_template_id,
                    'risorsa_umana_id', p_risorsa_umana_id
                ),
                NULL::uuid,
                p_flusso_id::text,
                p_risorsa_umana_id::text
            );
        END IF;
    END IF;

    -- Assegna il flusso e verifica risultato
    UPDATE pratiche.flussi
       SET risorsa_umana_id = p_risorsa_umana_id
     WHERE id = p_flusso_id;

    GET DIAGNOSTICS v_righe_aggiornate = ROW_COUNT;

    IF v_righe_aggiornate <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.fn_prendi_in_carico_flusso',
            'E_QUERY_FAILED',
            jsonb_build_object('flusso_id', p_flusso_id),
            NULL::uuid,
            'pratiche', 'flussi', 'UPDATE'
        );
    END IF;

    RETURN TRUE;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
IS 'Assegna un flusso DA_ESEGUIRE all''operatore, verificando competenza attiva. Usa FOR UPDATE per evitare race condition.';
```

---
{% include-markdown "signature-core.md" %}
