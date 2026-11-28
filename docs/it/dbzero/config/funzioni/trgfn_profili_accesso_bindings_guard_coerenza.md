{% include-markdown "it/dbzero/config/manual/trgfn_profili_accesso_bindings_guard_coerenza.md" %}
# ⚙️ Funzione `trgfn_profili_accesso_bindings_guard_coerenza`

```sql
CREATE FUNCTION trgfn_profili_accesso_bindings_guard_coerenza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_profili_accesso_bindings_guard_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE sulle colonne sorgente (policy ZeroErp).
    v_tipo_profilo config.profili_accesso.tipo%TYPE;
    v_ruolo_veste  anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger function: guard coerenza tipo_profilo <-> tipo_binding
    -- su config.profili_accesso_bindings (fase a10, BEFORE INSERT/UPDATE).
    --
    -- ⚠️ IL COMMENTO PRECEDENTE QUI DICEVA IL FALSO, e va corretto
    --   perche' ha gia' ingannato un test. Diceva: «il CHECK
    --   chk_profili_accesso_bindings_xor garantisce che esattamente
    --   una tra (uo, identita, ruolo) sia NOT NULL PRIMA che il
    --   trigger venga eseguito». In PostgreSQL e' il contrario: i
    --   trigger BEFORE ROW girano PRIMA che i vincoli CHECK siano
    --   valutati. Quindi con zero colonne valorizzate e' QUESTO
    --   guard a intercettare, e il CHECK non viene mai raggiunto.
    --   Il guard non puo' dare per acquisito l'xor: se ne accorge da
    --   solo, ed e' quello che fa.
    --
    -- Logica:
    --   1. Recupera tipo del profilo referenziato.
    --   2. Verifica che la colonna valorizzata corrisponda al tipo:
    --      REPARTO      => unita_organizzativa_id
    --      PORTALE      => ruolo_applicativo
    --      AD_HOC       => identita_digitale_id
    --      SUPER_ADMIN  => identita_digitale_id (§4.6.A.3)
    --
    -- ⚠️ I VALORI VARIADICI DEVONO ESSERE TANTI QUANTI I SEGNAPOSTO.
    --   Il messaggio di E_PROFILO_ACCESSO_BINDING_INCOERENTE e'
    --   «Profilo %s (tipo %s): …»: servono DUE valori. Passandone uno
    --   solo, fn_log_and_raise_error esplodeva in format() e il guard
    --   non arrivava mai a dire la ragione.
    --   Brief: brief-db-pgtap-runner-rls-baseline §13.
    -- ------------------------------------------------------------

    -- 1) Recupero tipo del profilo header.
    SELECT pa.tipo
      INTO v_tipo_profilo
      FROM config.profili_accesso pa
     WHERE pa.id = NEW.profilo_accesso_id;

    IF NOT FOUND THEN
        -- Caso limite: la FK lo impedirebbe, fail-fast esplicito.
        -- ⚠️ rev 2026-08-06: qui c'era E_PARAMETRO_INVALIDO, e il commento
        --   diceva il perche': «ha UN segnaposto, un valore basta». Il codice
        --   era stato scelto per la FORMA della stringa di formato, non per
        --   cosa significa — e quella scelta era arrivata fino allo status
        --   HTTP (400 «hai sbagliato a compilare» su una riga che non esiste).
        --   E_PROFILO_ACCESSO_NON_TROVATO ha anch'esso un solo segnaposto, e
        --   in piu' dice la verita'. Brief terzo lato §18.2/§18.5a.
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_PROFILO_ACCESSO_NON_TROVATO',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'profilo_accesso_id', NEW.profilo_accesso_id,
                'nota', 'profilo_accesso_id non trovato in config.profili_accesso'
            ),
            NULL::uuid,
            NEW.profilo_accesso_id::text
        );
    END IF;

    -- 2) Dispatch per tipo profilo.
    CASE v_tipo_profilo
        WHEN 'REPARTO' THEN
            IF NEW.unita_organizzativa_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_PROFILO_ACCESSO_BINDING_INCOERENTE',
                    jsonb_build_object(
                        'campo', 'unita_organizzativa_id',
                        'table', TG_TABLE_NAME,
                        'profilo_accesso_id', NEW.profilo_accesso_id,
                        'tipo_profilo', v_tipo_profilo,
                        'nota', 'Profilo REPARTO richiede unita_organizzativa_id'
                    ),
                    NULL::uuid,
                    NEW.profilo_accesso_id::text,
                    v_tipo_profilo::text
                );
            END IF;

        WHEN 'PORTALE' THEN
            IF NEW.ruolo_applicativo IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_PROFILO_ACCESSO_BINDING_INCOERENTE',
                    jsonb_build_object(
                        'campo', 'ruolo_applicativo',
                        'table', TG_TABLE_NAME,
                        'profilo_accesso_id', NEW.profilo_accesso_id,
                        'tipo_profilo', v_tipo_profilo,
                        'nota', 'Profilo PORTALE richiede ruolo_applicativo'
                    ),
                    NULL::uuid,
                    NEW.profilo_accesso_id::text,
                    v_tipo_profilo::text
                );
            END IF;

        WHEN 'AD_HOC' THEN
            IF NEW.identita_digitale_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_PROFILO_ACCESSO_BINDING_INCOERENTE',
                    jsonb_build_object(
                        'campo', 'identita_digitale_id',
                        'table', TG_TABLE_NAME,
                        'profilo_accesso_id', NEW.profilo_accesso_id,
                        'tipo_profilo', v_tipo_profilo,
                        'nota', 'Profilo AD_HOC richiede identita_digitale_id'
                    ),
                    NULL::uuid,
                    NEW.profilo_accesso_id::text,
                    v_tipo_profilo::text
                );
            END IF;

        WHEN 'SUPER_ADMIN' THEN
            -- SUPER_ADMIN e' un privilegio personale: sempre
            -- bindato a una singola identita, mai a reparto
            -- ne' a ruolo applicativo. Questo garantisce
            -- tracciabilita' individuale del bypass permessi.
            IF NEW.identita_digitale_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_PROFILO_ACCESSO_BINDING_INCOERENTE',
                    jsonb_build_object(
                        'campo', 'identita_digitale_id',
                        'table', TG_TABLE_NAME,
                        'profilo_accesso_id', NEW.profilo_accesso_id,
                        'tipo_profilo', v_tipo_profilo,
                        'nota', 'Profilo SUPER_ADMIN richiede identita_digitale_id (privilegio personale)'
                    ),
                    NULL::uuid,
                    NEW.profilo_accesso_id::text,
                    v_tipo_profilo::text
                );
            END IF;

            -- ⛔ Mai su un'identita' tecnica: un processo automatico
            --   passerebbe sopra ogni permesso. La veste che diventa
            --   tecnica col binding gia' addosso la ferma il guard di
            --   coerenza di anagrafiche.identita_digitali.
            IF EXISTS (SELECT 1
                         FROM anagrafiche.identita_digitali idg
                        WHERE idg.id = NEW.identita_digitale_id
                          AND idg.tecnica)
            THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_SUPER_ADMIN_SU_VESTE_TECNICA',
                    jsonb_build_object(
                        'campo', 'identita_digitale_id',
                        'table', TG_TABLE_NAME,
                        'profilo_accesso_id', NEW.profilo_accesso_id,
                        'identita_id', NEW.identita_digitale_id
                    ),
                    NULL::uuid,
                    NEW.identita_digitale_id::text
                );
            END IF;

        ELSE
            -- Nuovo valore dell'enum tipo_profilo_accesso senza
            -- regola qui: fail-fast esplicito (anti-bypass).
            -- E_PROFILO_ACCESSO_TIPO_NON_GESTITO ha UN segnaposto.
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_PROFILO_ACCESSO_TIPO_NON_GESTITO',
                jsonb_build_object(
                    'table', TG_TABLE_NAME,
                    'profilo_accesso_id', NEW.profilo_accesso_id,
                    'tipo_profilo', v_tipo_profilo,
                    'nota', 'Tipo profilo sconosciuto al guard di coerenza bindings'
                ),
                NULL::uuid,
                v_tipo_profilo::text
            );
    END CASE;

    -- 3) ⛔ Un profilo personale (AD_HOC, SUPER_ADMIN) si lega solo a
    --    una veste OPERATORE. I profili si raccolgono per credenziale
    --    e tipo di veste (script.fn_get_profili_accesso_applicabili), e
    --    sui portali una persona ha piu' vesti dello stesso tipo, una
    --    per soggetto: un profilo personale su una di loro varrebbe per
    --    tutte. Anche per un legame spento: riaccenderlo non ripassa
    --    di qui (il trigger non scatta su `attivo`).
    IF v_tipo_profilo IN ('AD_HOC', 'SUPER_ADMIN') THEN
        SELECT idg.ruolo_applicativo
          INTO v_ruolo_veste
          FROM anagrafiche.identita_digitali idg
         WHERE idg.id = NEW.identita_digitale_id;

        IF FOUND AND v_ruolo_veste <> 'OPERATORE' THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_PROFILO_PERSONALE_SOLO_OPERATORE',
                jsonb_build_object(
                    'campo', 'identita_digitale_id',
                    'table', TG_TABLE_NAME,
                    'profilo_accesso_id', NEW.profilo_accesso_id,
                    'tipo_profilo', v_tipo_profilo,
                    'identita_id', NEW.identita_digitale_id,
                    'ruolo_applicativo', v_ruolo_veste
                ),
                NULL::uuid,
                v_tipo_profilo::text,
                v_ruolo_veste::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_profili_accesso_bindings_guard_coerenza()
IS 'Guard a10 BEFORE INSERT/UPDATE su config.profili_accesso_bindings: il tipo del profilo e la colonna del binding sono coerenti (REPARTO -> unita_organizzativa_id, PORTALE -> ruolo_applicativo, AD_HOC e SUPER_ADMIN -> identita_digitale_id), il SUPER_ADMIN non si lega mai a un''identita'' tecnica (E_SUPER_ADMIN_SU_VESTE_TECNICA), e un profilo personale (AD_HOC, SUPER_ADMIN) si lega solo a una veste OPERATORE, anche spento (E_PROFILO_PERSONALE_SOLO_OPERATORE): i profili si raccolgono per credenziale e tipo di veste, e sui portali una persona ha una veste per soggetto. Incoerenza: E_PROFILO_ACCESSO_BINDING_INCOERENTE, con id e tipo del profilo; profilo assente: E_PROFILO_ACCESSO_NON_TROVATO; tipo sconosciuto: E_PROFILO_ACCESSO_TIPO_NON_GESTITO. Si somma al CHECK chk_profili_accesso_bindings_xor (una sola colonna valorizzata), e parla prima di lui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
