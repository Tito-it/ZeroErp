{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_contatti_guard_contesto_soggetto.md" %}
# ⚙️ Funzione `trgfn_contatti_guard_contesto_soggetto`

```sql
CREATE FUNCTION trgfn_contatti_guard_contesto_soggetto()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_contatti_guard_contesto_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi              text := 'anagrafiche.trgfn_contatti_guard_contesto_soggetto';
    v_soggetto_ruolo   anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
    v_codice_istanza   anagrafiche.istanze_utilities.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il ruolo e l'istanza del contatto sono del soggetto
    --   del contatto (soggetto_id).
    --
    -- Regole:
    --   - UPDATE che non tocca soggetto, ruolo e istanza:
    --     niente da giudicare;
    --   1. il ruolo e' del soggetto (fn_ruolo_di_altro_soggetto);
    --   2. l'istanza e' del soggetto (fn_istanza_di_altro_soggetto).
    -- =========================================================
    IF NEW.soggetto_ruolo_id IS NULL AND NEW.istanza_utility_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (OLD.soggetto_id, OLD.soggetto_ruolo_id, OLD.istanza_utility_id)
           IS NOT DISTINCT FROM
           (NEW.soggetto_id, NEW.soggetto_ruolo_id, NEW.istanza_utility_id)
    THEN
        RETURN NEW;
    END IF;

    -- 1) Il ruolo.
    v_soggetto_ruolo := anagrafiche.fn_ruolo_di_altro_soggetto(
        NEW.soggetto_ruolo_id, NEW.soggetto_id);

    IF v_soggetto_ruolo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_RUOLO_ALTRO_SOGGETTO',
            jsonb_build_object('campo', 'soggetto_ruolo_id',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                               'soggetto_id', NEW.soggetto_id,
                               'soggetto_id_ruolo', v_soggetto_ruolo),
            NEW.tx_id,
            NEW.soggetto_ruolo_id::text);
    END IF;

    -- 2) L'istanza.
    v_soggetto_istanza := anagrafiche.fn_istanza_di_altro_soggetto(
        NEW.istanza_utility_id, NEW.soggetto_id);

    IF v_soggetto_istanza IS NOT NULL THEN
        SELECT iu.codice
          INTO v_codice_istanza
          FROM anagrafiche.istanze_utilities iu
         WHERE iu.id = NEW.istanza_utility_id;

        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_ISTANZA_ALTRO_SOGGETTO',
            jsonb_build_object('campo', 'istanza_utility_id',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'istanza_utility_id', NEW.istanza_utility_id,
                               'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                               'soggetto_id', NEW.soggetto_id,
                               'soggetto_id_istanza', v_soggetto_istanza),
            NEW.tx_id,
            COALESCE(v_codice_istanza::text, NEW.istanza_utility_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_contatti_guard_contesto_soggetto()
IS 'Guard (2026-10-19) di anagrafiche.contatti: il ruolo (soggetto_ruolo_id) e l''istanza (istanza_utility_id) del contatto sono del suo soggetto (soggetto_id). BEFORE INSERT OR UPDATE in fascia a10; in UPDATE esce se soggetto, ruolo e istanza non cambiano. Rifiuti DATO_ERRATO col campo: E_RUOLO_ALTRO_SOGGETTO (soggetto_ruolo_id, dal BB anagrafiche.fn_ruolo_di_altro_soggetto), poi E_ISTANZA_ALTRO_SOGGETTO (istanza_utility_id, dal BB anagrafiche.fn_istanza_di_altro_soggetto). R-BE-15, D-17a e D-17c di Tid, brief-db-processi-accensione-per-ambiente §6.17.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
