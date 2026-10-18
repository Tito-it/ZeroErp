{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzi_soggetto.md" %}
# ⚙️ Funzione `fn_crea_indirizzi_soggetto`

```sql
CREATE FUNCTION fn_crea_indirizzi_soggetto(p_soggetto_id uuid, p_indirizzi jsonb, p_copia_obbligatori boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzi_soggetto(p_soggetto_id uuid, p_indirizzi jsonb, p_copia_obbligatori boolean DEFAULT true)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi       CONSTANT text := 'anagrafiche.fn_crea_indirizzi_soggetto';
    v_lista     jsonb := COALESCE(p_indirizzi, '[]'::jsonb);
    v_norm      jsonb := '[]'::jsonb;  -- elementi col tipo risolto
    v_el        jsonb;
    v_tipo_sd   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_tipo_id   anagrafiche.indirizzi_soggetti.tipo_indirizzo_id%TYPE;
    v_n         integer := 0;   -- un conteggio: niente da ancorare
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere gli indirizzi di un soggetto. p_indirizzi e' un
    --   array di oggetti con la grammatica di
    --   anagrafiche.fn_indirizzo_elemento. Ritorna quanti
    --   indirizzi ha scritto.
    --
    -- Regole (quelle della gemella fn_crea_indirizzi_ruolo):
    --   1. ogni elemento si normalizza col BB dell'elemento;
    --   2. se p_copia_obbligatori, i tipi obbligatori del TIPO
    --      DI SOGGETTO che mancano ricevono una copia del primo
    --      (anagrafiche.fn_indirizzi_con_obbligatori);
    --   3. un tipo che il soggetto ha gia' si salta; le righe le
    --      scrive la singolare fn_crea_indirizzo_soggetto.
    -- =========================================================
    IF jsonb_typeof(v_lista) <> 'array' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_indirizzi', jsonb_typeof(v_lista)),
            NULL::uuid,
            c_chi,
            'gli indirizzi non sono un elenco');
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_tipo_sd
      FROM anagrafiche.soggetti s
     WHERE s.id = p_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_NOT_FOUND',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            COALESCE(p_soggetto_id::text, '-'));
    END IF;

    IF jsonb_array_length(v_lista) = 0 THEN
        RETURN 0;
    END IF;

    -- 1. La grammatica dell'elemento.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        v_norm := v_norm || jsonb_build_array(
                    anagrafiche.fn_indirizzo_elemento(
                        v_el, c_chi,
                        jsonb_build_object('soggetto_id', p_soggetto_id)));
    END LOOP;

    -- 2. La copia degli obbligatori, con la matrice del tipo di soggetto.
    IF p_copia_obbligatori THEN
        v_norm := anagrafiche.fn_indirizzi_con_obbligatori(
            v_norm,
            ARRAY(SELECT m.tipo_indirizzo_id
                    FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
                   WHERE m.tipo_soggetto_dettaglio_id = v_tipo_sd
                     AND m.attivo
                     AND m.obbligatorio));
    END IF;

    -- 3. La scrittura: un tipo che il soggetto ha gia' si salta.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_norm) AS e LOOP
        v_tipo_id := (v_el ->> 'tipo_indirizzo_id')::integer;

        CONTINUE WHEN EXISTS (
            SELECT 1
              FROM anagrafiche.indirizzi_soggetti i
             WHERE i.soggetto_id = p_soggetto_id
               AND i.tipo_indirizzo_id = v_tipo_id);

        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(p_soggetto_id, v_el);
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzi_soggetto(p_soggetto_id uuid, p_indirizzi jsonb, p_copia_obbligatori boolean)
IS 'MADRE PLURALE (2026-10-19): scrive gli indirizzi di un soggetto e ritorna quanti ne ha scritti. Elementi con la grammatica di anagrafiche.fn_indirizzo_elemento; se p_copia_obbligatori (il flag auto_clone del backend, vero di default) i tipi obbligatori della matrice del TIPO DI SOGGETTO (config.tipi_soggetto_dettaglio_tipi_indirizzo, righe attive) che mancano ricevono una copia del primo (anagrafiche.fn_indirizzi_con_obbligatori); un tipo che il soggetto ha gia'' si salta; ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_soggetto. Soggetto inesistente E_SOGGETTO_NOT_FOUND, elenco non array E_SCRIPT_CHIAMATA_NON_VALIDA, elenco vuoto 0. Gemella di anagrafiche.fn_crea_indirizzi_ruolo (D-16a). Ritira la saga del backend SoggettiService._apply_auto_clone + _create_indirizzi_batch. R-BE-12, D-16a di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

---
{% include-markdown "signature-core.md" %}
