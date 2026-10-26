{% include-markdown "it/dbzero/pratiche/manual/fn_prendi_in_carico_flusso.md" %}
# ⚙️ Funzione `fn_prendi_in_carico_flusso`

```sql
CREATE FUNCTION fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
-- Scopo: assegnare un flusso DA_ESEGUIRE all'operatore corrente,
--        applicando la policy di eligibilita' reparto-first +
--        competenza opzionale (design assegnazione-flusso §2.2).
-- Regole:
--   1. Il flusso deve esistere
--   2. Stato DA_ESEGUIRE
--   3. Non gia' assegnato ad altro operatore
--   4. Eligibilita' (casi A/B/C/D, vedi sotto)
-- Risultato: true se assegnato, false se gia' assegnato allo stesso operatore.
-- Nota: SELECT ... FOR UPDATE per evitare race condition.
DECLARE
    v_stato_id          pratiche.flussi.stato_id%TYPE;
    v_risorsa_attuale   pratiche.flussi.risorsa_umana_id%TYPE;
    v_template_id       pratiche.flussi.template_flusso_id%TYPE;
    v_unita_org         pratiche.flussi.unita_organizzativa_id%TYPE;
    v_da_eseguire_id    config.stati_flussi_pratiche.id%TYPE;
    -- Il BERSAGLIO dei due rifiuti. ⚠️ `jsonb` esplicito: e' un frammento del
    -- context, non il valore di una colonna.
    v_bersagli          jsonb;
    v_has_skill_lock    BOOLEAN;
    v_competente        BOOLEAN;
    v_reparto_operatore anagrafiche.risorse_umane.unita_organizzativa_id%TYPE;
    v_righe_aggiornate  INTEGER;
BEGIN
    -- Guard: parametri obbligatori
    IF p_flusso_id IS NULL OR p_flusso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('p_flusso_id', p_flusso_id),
            NULL::uuid, 'p_flusso_id'
        );
    END IF;

    IF p_risorsa_umana_id IS NULL OR p_risorsa_umana_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('p_risorsa_umana_id', p_risorsa_umana_id),
            NULL::uuid, 'p_risorsa_umana_id'
        );
    END IF;

    -- Recupera stato + routing del flusso CON LOCK (FOR UPDATE)
    SELECT f.stato_id, f.risorsa_umana_id, f.template_flusso_id, f.unita_organizzativa_id
      INTO v_stato_id, v_risorsa_attuale, v_template_id, v_unita_org
      FROM pratiche.flussi f
     WHERE f.id = p_flusso_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_VALORE_MANCANTE',
            jsonb_build_object('flusso_id', p_flusso_id),
            NULL::uuid, concat('flusso_id ', p_flusso_id)
        );
    END IF;

    -- ⭐ IL BERSAGLIO, composto una volta e riusato dai due rifiuti sotto.
    --    Chi prende in carico un flusso arriva da una LISTA: la frase gli dice
    --    quale flusso ha rifiutato, e senza bersaglio deve ritrovarselo.
    --    ⚠️ Il flusso e' gia' stato letto (SELECT ... FOR UPDATE): esiste ed e'
    --    visibile, quindi nessuna query in piu' e nessun ramo condizionale.
    v_bersagli := jsonb_build_array(
        jsonb_build_object('tipo', 'FLUSSO', 'id', p_flusso_id::text));

    -- Verifica stato DA_ESEGUIRE
    SELECT id INTO v_da_eseguire_id
      FROM config.stati_flussi_pratiche
     WHERE codice_interno = 'DA_ESEGUIRE';

    IF v_stato_id <> v_da_eseguire_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_FLUSSI_PRESA_CARICO_STATO_ERRATO',
            jsonb_build_object('flusso_id', p_flusso_id, 'stato_id', v_stato_id,
                               'stato_richiesto', v_da_eseguire_id,
                               'bersaglio', v_bersagli),
            NULL::uuid, p_flusso_id::text
        );
    END IF;

    -- Gia' assegnato allo stesso operatore: noop
    IF v_risorsa_attuale = p_risorsa_umana_id THEN
        RETURN FALSE;
    END IF;

    -- Gia' assegnato ad altro operatore: errore
    IF v_risorsa_attuale IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_FLUSSI_GIA_ASSEGNATO',
            jsonb_build_object('flusso_id', p_flusso_id, 'risorsa_attuale', v_risorsa_attuale,
                               'risorsa_richiedente', p_risorsa_umana_id,
                               'bersaglio', v_bersagli),
            NULL::uuid, p_flusso_id::text, v_risorsa_attuale::text
        );
    END IF;

    -- ============================================================
    -- Eligibilita' (policy reparto-first + competenza opzionale)
    -- ============================================================
    -- skill-lock: la matrice competenze e' configurata (attiva) per il template
    v_has_skill_lock := (v_template_id IS NOT NULL) AND EXISTS (
        SELECT 1 FROM pratiche.competenze_flussi cf
         WHERE cf.template_flusso_id = v_template_id
           AND cf.attivo = true
    );

    IF v_has_skill_lock THEN
        -- Casi A/D: serve competenza ATTIVA dell'operatore
        SELECT EXISTS (
            SELECT 1 FROM pratiche.competenze_flussi cf
             WHERE cf.template_flusso_id = v_template_id
               AND cf.risorsa_umana_id = p_risorsa_umana_id
               AND cf.attivo = true
        ) INTO v_competente;

        IF NOT v_competente THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
                'E_FLUSSI_COMPETENZA_MANCANTE',
                jsonb_build_object('flusso_id', p_flusso_id, 'template_flusso_id', v_template_id, 'risorsa_umana_id', p_risorsa_umana_id),
                NULL::uuid, p_flusso_id::text, p_risorsa_umana_id::text
            );
        END IF;

    ELSIF v_unita_org IS NOT NULL THEN
        -- Caso B: niente skill-lock ma reparto valorizzato -> serve
        -- appartenenza al reparto ANAGRAFICO dell'operatore
        SELECT unita_organizzativa_id INTO v_reparto_operatore
          FROM anagrafiche.risorse_umane
         WHERE id = p_risorsa_umana_id;

        IF v_reparto_operatore IS NULL OR v_reparto_operatore <> v_unita_org THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
                'E_FLUSSI_PRESA_NON_ELIGIBILE',
                jsonb_build_object(
                    'flusso_id', p_flusso_id,
                    'unita_organizzativa_flusso', v_unita_org,
                    'unita_organizzativa_operatore', v_reparto_operatore,
                    'risorsa_umana_id', p_risorsa_umana_id
                ),
                NULL::uuid, p_flusso_id::text, p_risorsa_umana_id::text
            );
        END IF;

    -- ELSE: Caso C (niente reparto, niente skill-lock) -> presa libera
    END IF;

    -- Assegna il flusso e verifica risultato
    UPDATE pratiche.flussi
       SET risorsa_umana_id = p_risorsa_umana_id
     WHERE id = p_flusso_id;

    GET DIAGNOSTICS v_righe_aggiornate = ROW_COUNT;

    IF v_righe_aggiornate <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', 'pratiche.fn_prendi_in_carico_flusso',
            'E_QUERY_FAILED',
            jsonb_build_object('flusso_id', p_flusso_id),
            NULL::uuid, 'pratiche', 'flussi', 'UPDATE'
        );
    END IF;

    RETURN TRUE;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_prendi_in_carico_flusso(p_flusso_id bigint, p_risorsa_umana_id bigint)
IS 'Assegna un flusso DA_ESEGUIRE all''operatore con policy eligibilita'' reparto-first + competenza opzionale (casi A/B/C/D). FOR UPDATE anti-race. ⭐ rev 2026-08-24: i due rifiuti della presa in carico portano il BERSAGLIO sul flusso. Chi prende in carico arriva da una LISTA: la frase dice quale flusso ha rifiutato, e senza bersaglio deve ritrovarselo. Il flusso e'' gia'' letto (SELECT ... FOR UPDATE), quindi esiste ed e'' visibile: nessuna query in piu''. Brief: brief-db-bersaglio-errore.md §6 L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
