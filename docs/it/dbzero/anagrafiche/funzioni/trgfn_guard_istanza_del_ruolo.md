{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_guard_istanza_del_ruolo.md" %}
# ⚙️ Funzione `trgfn_guard_istanza_del_ruolo`

```sql
CREATE FUNCTION trgfn_guard_istanza_del_ruolo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_guard_istanza_del_ruolo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi              text := 'anagrafiche.trgfn_guard_istanza_del_ruolo';
    v_soggetto_ruolo   anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
    v_codice_istanza   anagrafiche.istanze_utilities.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'istanza della riga (istanza_utility_id) e' del
    --   soggetto del suo ruolo (soggetto_ruolo_id). Un corpo
    --   per anagrafiche.indirizzi e
    --   anagrafiche.soggetti_ruoli_conti_bancari.
    --
    -- Regole:
    --   - nessuna istanza: niente da giudicare;
    --   - UPDATE che non tocca ruolo e istanza: niente da
    --     giudicare (le righe di prima restano valide finche'
    --     non si toccano);
    --   - il confronto dal BB fn_istanza_di_altro_soggetto.
    -- =========================================================
    IF NEW.istanza_utility_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (OLD.soggetto_ruolo_id, OLD.istanza_utility_id)
           IS NOT DISTINCT FROM
           (NEW.soggetto_ruolo_id, NEW.istanza_utility_id)
    THEN
        RETURN NEW;
    END IF;

    SELECT sr.soggetto_id
      INTO v_soggetto_ruolo
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = NEW.soggetto_ruolo_id;

    v_soggetto_istanza := anagrafiche.fn_istanza_di_altro_soggetto(
        NEW.istanza_utility_id, v_soggetto_ruolo);

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
                               'soggetto_id', v_soggetto_ruolo,
                               'soggetto_id_istanza', v_soggetto_istanza),
            NEW.tx_id,
            COALESCE(v_codice_istanza::text, NEW.istanza_utility_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_guard_istanza_del_ruolo()
IS 'Guard (2026-10-19), un corpo per anagrafiche.indirizzi e anagrafiche.soggetti_ruoli_conti_bancari: l''istanza della riga (istanza_utility_id) e'' del soggetto del suo ruolo (soggetto_ruolo_id). BEFORE INSERT OR UPDATE in fascia a10, per ogni scrittore (madri e UPDATE del backend). Esce senza istanza, e in UPDATE se ruolo e istanza non cambiano. Rifiuto E_ISTANZA_ALTRO_SOGGETTO (DATO_ERRATO), contesto campo = istanza_utility_id e la tabella; nella frase il codice dell''istanza. Il confronto dal BB anagrafiche.fn_istanza_di_altro_soggetto. L''altra porta (il soggetto dell''istanza o del ruolo che cambia) la chiudono i lock E_ISTANZA_SOGGETTO_IMMUTABILE ed E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE. R-BE-15, D-17a e D-17c di Tid, brief-db-processi-accensione-per-ambiente §6.17.1.';
```

---
{% include-markdown "signature-core.md" %}
