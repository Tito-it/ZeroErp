{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera.md" %}
# ⚙️ Funzione `trgfn_indirizzi_guard_forma_libera`

```sql
CREATE FUNCTION trgfn_indirizzi_guard_forma_libera()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_guard_forma_libera()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi        text := 'anagrafiche.trgfn_indirizzi_guard_forma_libera';
    v_stato      config.stati%ROWTYPE;
    v_catalogo   boolean;   -- la forma del catalogo vale per questa riga
    v_campo      text;      -- la colonna che si rifiuta
    v_cosa       text;      -- la stessa, come la legge una persona
    v_comune     config.comuni.descrizione%TYPE;
    v_stato_com  config.stati.id%TYPE;
    v_cap        config.codici_postali.codice%TYPE;
    v_cap_comune config.codici_postali.comune_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La forma dell'indirizzo libero (tabelle indirizzi e
    --   indirizzi_soggetti). Rifiuta col codice e col campo.
    --
    -- Regole:
    --   - indirizzo normalizzato: niente da giudicare;
    --   - UPDATE che non tocca l'indirizzo: niente da giudicare
    --     (le righe di prima restano valide finche' non si
    --     toccano);
    --   - testo e stato, poi la forma decisa dallo stato:
    --     catalogo (comune e CAP coerenti) o estera (localita').
    -- =========================================================
    IF NEW.indirizzo_dettaglio_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (OLD.indirizzo_dettaglio_id, OLD.indirizzo_libero, OLD.stato_id,
            OLD.comune_id, OLD.codice_postale_id, OLD.locality,
            OLD.postal_code, OLD.administrative_area, OLD.sublocality)
           IS NOT DISTINCT FROM
           (NEW.indirizzo_dettaglio_id, NEW.indirizzo_libero, NEW.stato_id,
            NEW.comune_id, NEW.codice_postale_id, NEW.locality,
            NEW.postal_code, NEW.administrative_area, NEW.sublocality)
    THEN
        RETURN NEW;
    END IF;

    -- 1) Il testo e lo stato, in ogni forma. Il normalize ha
    --    gia' portato a NULL i testi vuoti e scritto lo stato
    --    proposto: qui il NULL e' davvero «manca».
    IF NEW.indirizzo_libero IS NULL THEN
        v_campo := 'indirizzo_libero';
        v_cosa  := 'l''indirizzo (via e numero)';
    ELSIF NEW.stato_id IS NULL THEN
        v_campo := 'stato_id';
        v_cosa  := 'lo stato';
    END IF;

    IF v_campo IS NULL THEN
        SELECT s.* INTO v_stato FROM config.stati s WHERE s.id = NEW.stato_id;
        v_catalogo := v_stato.catalogo_comuni_completo
                      OR NEW.comune_id IS NOT NULL
                      OR NEW.codice_postale_id IS NOT NULL;

        IF v_catalogo THEN
            IF NEW.comune_id IS NULL THEN
                v_campo := 'comune_id';
                v_cosa  := 'il comune';
            ELSIF NEW.codice_postale_id IS NULL THEN
                v_campo := 'codice_postale_id';
                v_cosa  := 'il CAP';
            END IF;
        ELSIF NEW.locality IS NULL THEN
            v_campo := 'locality';
            v_cosa  := 'la localita''';
        END IF;
    END IF;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_LIBERO_INCOMPLETO',
            jsonb_build_object('campo', v_campo,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'stato_id', NEW.stato_id),
            NULL::uuid,
            v_cosa);
    END IF;

    IF NOT v_catalogo THEN
        RETURN NEW;   -- forma estera: comune e CAP sono NULL
    END IF;

    -- 2) La forma del catalogo: niente campi della forma estera.
    --    La sotto-localita' (frazione) resta ammessa.
    IF NEW.locality IS NOT NULL THEN
        v_campo := 'locality';
        v_cosa  := 'la localita''';
    ELSIF NEW.postal_code IS NOT NULL THEN
        v_campo := 'postal_code';
        v_cosa  := 'il codice postale';
    ELSIF NEW.administrative_area IS NOT NULL THEN
        v_campo := 'administrative_area';
        v_cosa  := 'la regione o provincia';
    END IF;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_CAMPO_ALTRA_FORMA',
            jsonb_build_object('campo', v_campo,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'stato_id', NEW.stato_id),
            NULL::uuid,
            v_cosa);
    END IF;

    -- 3) Il comune e' dello stato. Catena interrotta (provincia
    --    senza regione, o comune senza provincia): non lo si puo'
    --    dire, e si rifiuta.
    SELECT c.descrizione, r.stato_id
      INTO v_comune, v_stato_com
      FROM config.comuni c
      LEFT JOIN config.province p ON p.id = c.provincia_id
      LEFT JOIN config.regioni  r ON r.id = p.regione_id
     WHERE c.id = NEW.comune_id;

    IF v_stato_com IS DISTINCT FROM NEW.stato_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_COMUNE_ALTRO_STATO',
            jsonb_build_object('campo', 'comune_id',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'comune_id', NEW.comune_id,
                               'stato_id', NEW.stato_id,
                               'stato_del_comune', v_stato_com),
            NULL::uuid,
            COALESCE(v_comune, '-'), COALESCE(v_stato.descrizione, '-'));
    END IF;

    -- 4) Il CAP e' del comune.
    SELECT cp.codice, cp.comune_id
      INTO v_cap, v_cap_comune
      FROM config.codici_postali cp
     WHERE cp.id = NEW.codice_postale_id;

    IF v_cap_comune IS DISTINCT FROM NEW.comune_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_CAP_ALTRO_COMUNE',
            jsonb_build_object('campo', 'codice_postale_id',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'codice_postale_id', NEW.codice_postale_id,
                               'comune_id', NEW.comune_id),
            NULL::uuid,
            COALESCE(v_cap, '-'), COALESCE(v_comune, '-'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_guard_forma_libera()
IS 'Guard (2026-10-18) della forma dell''indirizzo libero, un corpo per anagrafiche.indirizzi e indirizzi_soggetti, in fascia z10: dopo il normalize, che scrive lo stato proposto e porta a NULL i testi vuoti. Testo e stato sempre; poi la forma la decide lo stato (config.stati.catalogo_comuni_completo): catalogo = comune e CAP del catalogo, coerenti fra loro e con lo stato, senza localita'', codice postale libero e regione (la sotto-localita'' e'' ammessa); estera = la localita'', il resto facoltativo, senza comune e CAP. Uno stato senza catalogo completo accetta anche la forma del catalogo se il chiamante sceglie comune o CAP. Rifiuti DATO_ERRATO col nome della colonna in contesto campo: E_INDIRIZZO_LIBERO_INCOMPLETO (il primo campo che manca), E_INDIRIZZO_CAMPO_ALTRA_FORMA, E_INDIRIZZO_COMUNE_ALTRO_STATO (anche a catena del catalogo interrotta), E_INDIRIZZO_CAP_ALTRO_COMUNE. Indirizzo normalizzato, o UPDATE che non tocca le colonne dell''indirizzo: esce (le righe di prima restano valide finche'' non si toccano). Il CHECK chk_*_free_requirements resta la rete; le madri non ripetono la completezza. Richiesta BE in brief-db-processi-accensione-per-ambiente §6.11, D-2 e D-3 di Tid.';
```

</div>

---
{% include-markdown "signature-core.md" %}
