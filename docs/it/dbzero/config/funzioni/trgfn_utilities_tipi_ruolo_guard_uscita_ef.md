# ⚙️ Funzione `trgfn_utilities_tipi_ruolo_guard_uscita_ef`

```sql
CREATE FUNCTION trgfn_utilities_tipi_ruolo_guard_uscita_ef()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi      CONSTANT dbops.error_log.function_name%TYPE := 'config.trgfn_utilities_tipi_ruolo_guard_uscita_ef';
    v_ef       config.tipi_ruoli.id%TYPE;
    v_oggi     config.utilities_tipi_ruolo.valido_dal%TYPE := script.fn_data_operativa();
    -- un conteggio: nessuna colonna dietro
    v_aziende  integer;
    v_codice   config.utilities.codice%TYPE;
    -- il nome di una colonna, per il contesto dell'errore: nessuna colonna dietro
    v_campo    text;
BEGIN
    -- =========================================================
    -- Scopo: la riga dell'emittente fiscale (EF) di un'utility
    --   non ha data di fine, e non smette di ammettere l'utility
    --   finche' un'azienda la gestisce (una riga in
    --   anagrafiche.emittenti_fiscali_utilities). Montata BEFORE
    --   INSERT OR UPDATE OR DELETE, fase a12.
    -- =========================================================
    SELECT t.id INTO v_ef
      FROM config.tipi_ruoli t
     WHERE t.codice_interno = 'EF';
    -- Senza il tipo EF a catalogo non c'e' niente da presidiare.
    IF v_ef IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- 1) la riga EF non ha data di fine
    IF TG_OP IN ('INSERT', 'UPDATE')
       AND NEW.tipo_ruolo_id = v_ef
       AND NEW.valido_al IS NOT NULL THEN
        SELECT u.codice INTO v_codice FROM config.utilities u WHERE u.id = NEW.utility_id;
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_UTILITY_EF_SENZA_SCADENZA',
            jsonb_build_object('campo', 'valido_al',
                               'tabella', 'config.utilities_tipi_ruolo',
                               'utility_id', NEW.utility_id,
                               'valido_al', NEW.valido_al),
            NULL::uuid,
            COALESCE(v_codice::text, NEW.utility_id::text));
    END IF;

    -- 2) la riga EF che oggi ammette l'utility smette di farlo
    IF TG_OP IN ('UPDATE', 'DELETE')
       AND OLD.tipo_ruolo_id = v_ef
       AND OLD.attivo IS TRUE
       AND (OLD.valido_dal IS NULL OR OLD.valido_dal <= v_oggi)
       AND OLD.valido_al IS NULL
       AND NOT (TG_OP = 'UPDATE'
                AND NEW.tipo_ruolo_id = v_ef
                AND NEW.utility_id = OLD.utility_id
                AND NEW.attivo IS TRUE
                AND (NEW.valido_dal IS NULL OR NEW.valido_dal <= v_oggi)) THEN

        SELECT count(*)::integer INTO v_aziende
          FROM anagrafiche.emittenti_fiscali_utilities e
         WHERE e.utility_id = OLD.utility_id;

        IF v_aziende > 0 THEN
            v_campo := CASE
                WHEN TG_OP = 'DELETE' THEN NULL
                WHEN NEW.utility_id IS DISTINCT FROM OLD.utility_id THEN 'utility_id'
                WHEN NEW.tipo_ruolo_id IS DISTINCT FROM OLD.tipo_ruolo_id THEN 'tipo_ruolo_id'
                WHEN NEW.attivo IS NOT TRUE THEN 'attivo'
                ELSE 'valido_dal'
            END;
            SELECT u.codice INTO v_codice FROM config.utilities u WHERE u.id = OLD.utility_id;
            PERFORM script.fn_log_and_raise_error(
                'database', v_chi, 'E_UTILITY_EF_GESTITA',
                jsonb_strip_nulls(jsonb_build_object(
                    'campo', v_campo,
                    'tabella', 'config.utilities_tipi_ruolo',
                    'operazione', TG_OP,
                    'utility_id', OLD.utility_id,
                    'aziende', v_aziende)),
                NULL::uuid,
                COALESCE(v_codice::text, OLD.utility_id::text),
                v_aziende::text);
        END IF;
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END
$function$

COMMENT ON FUNCTION config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()
IS 'BEFORE INSERT OR UPDATE OR DELETE su config.utilities_tipi_ruolo, fase a12. La riga dell''emittente fiscale (tipo di ruolo EF) non ha data di fine: E_UTILITY_EF_SENZA_SCADENZA, campo valido_al. Finche'' un''azienda gestisce l''utility (una riga in anagrafiche.emittenti_fiscali_utilities), la riga EF che oggi la ammette non si spegne, non prende una data d''inizio futura, non si cancella e non si sposta: E_UTILITY_EF_GESTITA, con il codice dell''utility e il numero delle aziende. Le altre righe della matrice non sono giudicate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
