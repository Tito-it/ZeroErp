{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_commesse_guard_transizione`

```sql
CREATE FUNCTION trgfn_commesse_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato commessa.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in vendite.transizioni_stati_commessa. In piu',
--   ->PRONTA_FATTURAZIONE richiede almeno una riga commesse_attivita
--   APPROVATA e NON_EMESSA (ingresso), e ->CHIUSA / ->ANNULLATA
--   richiedono che non resti niente di vivo (uscita, rev 2026-07-24).
--   Letto dalla matrice (no grafo hardcodato).
DECLARE
    v_codice_da vendite.stati_commessa.codice_interno%TYPE;
    v_codice_a  vendite.stati_commessa.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_motivi    jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_commessa_id IS NOT DISTINCT FROM OLD.stato_commessa_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_commessa_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_commessa_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM vendite.stati_commessa
     WHERE id IN (OLD.stato_commessa_id, NEW.stato_commessa_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.transizioni_stati_commessa t
         WHERE t.stato_da_id = OLD.stato_commessa_id
           AND t.stato_a_id  = NEW.stato_commessa_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_COMMESSA_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'commessa_id', NEW.id,
                'codice',      NEW.codice,
                'stato_da',    v_codice_da,
                'stato_a',     v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: ->PRONTA_FATTURAZIONE richiede almeno una riga
    -- approvata e non ancora emessa. Tiene allineati i due livelli
    -- (testata emittibile <-> esiste qualcosa da emettere).
    IF v_codice_a = 'PRONTA_FATTURAZIONE' THEN
        IF NOT EXISTS (
            SELECT 1 FROM vendite.commesse_attivita ca
             WHERE ca.commessa_id = NEW.id
               AND ca.stato_approvazione = 'APPROVATA'
               AND ca.stato_emissione    = 'NON_EMESSA'
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_COMMESSA_NESSUNA_RIGA_APPROVATA',
                jsonb_build_object(
                    'commessa_id', NEW.id,
                    'codice',      NEW.codice
                ),
                NEW.tx_id,
                NEW.id::text,
                coalesce(NEW.codice, 'NULL')
            );
        END IF;
    END IF;

    -- Regola 3 (rev 2026-07-24): guard di USCITA, speculare alla
    -- Regola 2. CHIUSA e ANNULLATA sono TERMINALI (nessun arco
    -- uscente in matrice) e non emittibili: un errore qui non e'
    -- recuperabile per via applicativa, quindi fail-fast.
    -- La regola vera vive nelle fn_check_* (sorgente UNICA,
    -- condivisa con script.fn_available_actions_commessa): qui si
    -- solleva soltanto, col codice del PRIMO motivo.
    -- Arita' fissa (codice commessa, dettaglio): vale per tutti i
    -- codici di questa famiglia (brief §3.1).
    IF v_codice_a IN ('CHIUSA', 'ANNULLATA') THEN
        v_motivi := CASE v_codice_a
                      WHEN 'CHIUSA' THEN script.fn_check_commessa_chiudibile(NEW.id)
                      ELSE               script.fn_check_commessa_annullabile(NEW.id)
                    END;

        IF jsonb_array_length(v_motivi) > 0 THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                v_motivi -> 0 ->> 'codice',
                jsonb_build_object(
                    'commessa_id', NEW.id,
                    'codice',      NEW.codice,
                    'stato_da',    v_codice_da,
                    'stato_a',     v_codice_a,
                    'motivi',      v_motivi
                ),
                NEW.tx_id,
                coalesce(NEW.codice, NEW.id::text),
                coalesce(v_motivi -> 0 ->> 'dettaglio', '0')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato commessa letto da vendite.transizioni_stati_commessa (E_COMMESSA_STATO_TRANSIZIONE_INVALIDA). Precondizione INGRESSO ->PRONTA_FATTURAZIONE: almeno una riga APPROVATA+NON_EMESSA (E_COMMESSA_NESSUNA_RIGA_APPROVATA). Precondizione USCITA ->CHIUSA/->ANNULLATA (rev 2026-07-24, brief-db-guard-uscita-commessa-e-capabilities): delegata alle funzioni pure script.fn_check_commessa_chiudibile / _annullabile — sorgente UNICA condivisa con script.fn_available_actions_commessa — che producono i motivi; qui si solleva il codice del primo (558 righe emesse / 559 righe approvate non emesse) con arita'' fissa (codice commessa, dettaglio). Motivo: CHIUSA e ANNULLATA sono terminali e non emittibili, un errore non e'' recuperabile. rev 2026-07-24.';
```

---
{% include-markdown "signature-core.md" %}
