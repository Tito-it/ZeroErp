{% include-markdown "it/dbzero/pratiche/manual/fn_genera_pratica_da_flusso.md" %}
# ⚙️ Funzione `fn_genera_pratica_da_flusso`

```sql
CREATE FUNCTION fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_pratica_sorgente_id   pratiche.pratiche.id%TYPE;
    v_emittente_id          pratiche.pratiche.emittente_fiscale_id%TYPE;
    v_soggetto_id           pratiche.pratiche.soggetto_id%TYPE;
    v_soggetto_ruolo_id     pratiche.pratiche.soggetto_ruolo_id%TYPE;
    v_istanza_utility_id    pratiche.pratiche.istanza_utility_id%TYPE;
    v_billing_account_id    pratiche.pratiche.billing_account_id%TYPE;
    v_priorita_id           pratiche.pratiche.priorita_id%TYPE;
    v_tipo_prest_dest_id    pratiche.regole_generazione.tipo_prestazione_dest_id%TYPE;
    v_template_dest_id      pratiche.regole_generazione.template_flusso_dest_id%TYPE;
    v_stato_iniziale_id     config.stati_pratiche.id%TYPE;
    v_stato_flusso_id       config.stati_flussi_pratiche.id%TYPE;
    v_dest_sequenza         pratiche.template_flussi.sequenza%TYPE;
    v_nuova_pratica_id      pratiche.pratiche.id%TYPE;
    -- D2-8 (Fase 1): remap del template destinazione per codice
    -- dentro la definizione pinnata della figlia.
    v_nuova_definizione_id       pratiche.pratiche.definizione_id%TYPE;
    v_dest_codice                pratiche.template_flussi.codice%TYPE;
    v_template_dest_effettivo_id pratiche.template_flussi.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Genera la pratica figlia da un flusso completato secondo
    --   una regola di generazione. Idempotente: per la stessa
    --   coppia (flusso, tipo destinazione) esiste al massimo una
    --   figlia; le chiamate successive ritornano l'id esistente.
    --   Copia emittente/soggetto/contesto/priorita, valorizza
    --   pratica_padre_id + flusso_origine_id e, se la regola lo
    --   dichiara, crea il flusso iniziale della figlia (template
    --   destinazione rimappato per codice nella definizione della
    --   figlia, D2-8 definizione-aware).
    -- =========================================================

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

    -- Recupera dati pratica sorgente (incluso contesto, fix-4)
    -- rev 2026-10-08: anche il BA (il cliente di cui parla la madre).
    SELECT p.emittente_fiscale_id, p.soggetto_id,
           p.soggetto_ruolo_id, p.istanza_utility_id, p.priorita_id,
           p.billing_account_id
      INTO v_emittente_id, v_soggetto_id,
           v_soggetto_ruolo_id, v_istanza_utility_id, v_priorita_id,
           v_billing_account_id
      FROM pratiche.pratiche p
     WHERE p.id = v_pratica_sorgente_id;

    -- Recupera regola di generazione (incluso flusso iniziale, fix-3)
    SELECT rg.tipo_prestazione_dest_id, rg.template_flusso_dest_id
      INTO v_tipo_prest_dest_id, v_template_dest_id
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

    -- Idempotenza (fix-1): figlia gia' esistente per
    -- (flusso, tipo destinazione) -> ritorna l'id esistente.
    -- Vale per trigger auto, API /genera/ e doppi eventi.
    SELECT p.id
      INTO v_nuova_pratica_id
      FROM pratiche.pratiche p
     WHERE p.flusso_origine_id  = p_flusso_id
       AND p.tipo_prestazione_id = v_tipo_prest_dest_id
     LIMIT 1;

    IF FOUND THEN
        RETURN v_nuova_pratica_id;
    END IF;

    -- Determina stato iniziale (APERTA): la figlia auto-generata
    -- e' un lavoro gia' avviato, nasce operativa (coerente con il
    -- modello "la pratica nasce APERTA"). data_apertura viene
    -- valorizzata dal trigger trg_pratiche_m50_set_data_apertura_ins.
    SELECT sp.id
      INTO v_stato_iniziale_id
      FROM config.stati_pratiche sp
     WHERE sp.codice_interno = 'APERTA'
       AND sp.attivo = true
     LIMIT 1;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_genera_pratica_da_flusso',
            'E_CODICE',
            jsonb_build_object('codice_interno', 'APERTA'),
            NULL::uuid,
            'APERTA', 'config.stati_pratiche'
        );
    END IF;

    -- Crea pratica target: genealogia completa (fix-2) e
    -- contesto propagato (fix-4, coerente col soggetto copiato).
    -- definizione_id NON passata: l'auto-pin (BEFORE INSERT) la
    -- risolve per l'emittente della figlia; RETURNING la rilegge.
    INSERT INTO pratiche.pratiche (
        emittente_fiscale_id,
        tipo_prestazione_id,
        soggetto_id,
        soggetto_ruolo_id,
        istanza_utility_id,
        billing_account_id,
        stato_id,
        priorita_id,
        pratica_padre_id,
        flusso_origine_id
    ) VALUES (
        v_emittente_id,
        v_tipo_prest_dest_id,
        v_soggetto_id,
        v_soggetto_ruolo_id,
        v_istanza_utility_id,
        v_billing_account_id,
        v_stato_iniziale_id,
        v_priorita_id,
        v_pratica_sorgente_id,
        p_flusso_id
    )
    RETURNING id, definizione_id
         INTO v_nuova_pratica_id, v_nuova_definizione_id;

    -- Flusso iniziale della figlia (fix-3): solo se la regola
    -- lo dichiara. Il template deve essere senza prerequisiti
    -- (la figlia nasce senza flussi): in caso contrario il
    -- guard prerequisiti blocca — errore di seed, fail-fast.
    IF v_template_dest_id IS NOT NULL THEN
        SELECT sfp.id
          INTO v_stato_flusso_id
          FROM config.stati_flussi_pratiche sfp
         WHERE sfp.codice_interno = 'DA_ESEGUIRE'
           AND sfp.attivo = true
         LIMIT 1;

        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'fn_genera_pratica_da_flusso',
                'E_CODICE',
                jsonb_build_object('codice_interno', 'DA_ESEGUIRE'),
                NULL::uuid,
                'DA_ESEGUIRE', 'config.stati_flussi_pratiche'
            );
        END IF;

        -- D2-8: la regola dichiara il template destinazione per id
        -- (nel preset). Rimappa per CODICE nella definizione PINNATA
        -- della figlia: con un fork l'id del preset non vi appartiene
        -- e il guard D2-7 lo bloccherebbe. In Fase 1 (no fork) e' lo
        -- stesso template. La sequenza viene dal template rimappato.
        SELECT tf.codice
          INTO v_dest_codice
          FROM pratiche.template_flussi tf
         WHERE tf.id = v_template_dest_id;

        SELECT tf2.id, tf2.sequenza
          INTO v_template_dest_effettivo_id, v_dest_sequenza
          FROM pratiche.template_flussi tf2
         WHERE tf2.definizione_id = v_nuova_definizione_id
           AND tf2.codice = v_dest_codice;

        IF NOT FOUND THEN
            -- La definizione pinnata della figlia non contiene lo
            -- step dichiarato dalla regola (es. fork che l'ha rimosso).
            PERFORM script.fn_log_and_raise_error(
                'database',
                'fn_genera_pratica_da_flusso',
                'E_GENERAZIONE_TEMPLATE_NON_IN_DEFINIZIONE',
                jsonb_build_object(
                    'regola_id',              p_regola_id,
                    'template_dest_codice',   v_dest_codice,
                    'definizione_figlia_id',  v_nuova_definizione_id,
                    'pratica_figlia_id',      v_nuova_pratica_id
                ),
                NULL::uuid,
                COALESCE(v_dest_codice, v_template_dest_id::text),
                v_nuova_definizione_id::text
            );
        END IF;

        INSERT INTO pratiche.flussi (
            pratica_id,
            template_flusso_id,
            stato_id,
            sequenza
        ) VALUES (
            v_nuova_pratica_id,
            v_template_dest_effettivo_id,
            v_stato_flusso_id,
            COALESCE(v_dest_sequenza, 0)
        );
    END IF;

    RETURN v_nuova_pratica_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_genera_pratica_da_flusso(p_flusso_id bigint, p_regola_id bigint)
IS 'Genera pratica figlia da flusso completato secondo regola di generazione. Idempotente per (flusso, tipo dest): ritorna la figlia esistente. Copia emittente/soggetto/contesto/priorita; valorizza pratica_padre_id e flusso_origine_id; crea il flusso iniziale se la regola dichiara template_flusso_dest_id, RIMAPPANDOLO per codice nella definizione pinnata della figlia (D2-8 definizione-aware; fail-fast 512 se assente). Stato iniziale APERTA. rev 2026-10-08 (20261008-69): copia dalla madre anche billing_account_id (il cliente di cui parla la pratica). Brief: brief-db-istanza-nasce-col-ba (R-8, D-9).';
```

</div>

---
{% include-markdown "signature-core.md" %}
