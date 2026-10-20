{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_categorie_clienti_listini_guard_listino.md" %}
# ⚙️ Funzione `trgfn_categorie_clienti_listini_guard_listino`

```sql
CREATE FUNCTION trgfn_categorie_clienti_listini_guard_listino()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_categorie_clienti_listini_guard_listino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ef_id  anagrafiche.emittenti_fiscali.id%TYPE;
    v_motivi jsonb;
    -- La reason del primo motivo: il vocabolario della check.
    v_reason text;
    v_codice config.codici_errore.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   BEFORE INSERT, e BEFORE UPDATE quando cambiano listino,
    --   utility o emittente, su
    --   anagrafiche.categorie_clienti_listini: il listino e' della
    --   utility e dell'emittente della riga
    --   (script.fn_check_listino_documento).
    -- =========================================================

    -- Il ruolo dell'emittente -> il suo emittente fiscale.
    SELECT ef.id INTO v_ef_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = NEW.emittente_soggetto_ruolo_id;

    v_motivi := script.fn_check_listino_documento(
        NEW.listino_id, NEW.utility_id, v_ef_id);

    IF jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    v_reason := v_motivi -> 0 ->> 'reason';
    v_codice := CASE v_reason
        WHEN 'LISTINO_UTILITY_DIVERSA'   THEN 'E_CATEGORIA_LISTINO_UTILITY_DIVERSA'
        WHEN 'LISTINO_EMITTENTE_DIVERSO' THEN 'E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO'
    END;

    -- Un motivo nuovo nella check non passa in silenzio.
    IF v_codice IS NULL THEN
        RAISE EXCEPTION
            'trgfn_categorie_clienti_listini_guard_listino: motivo % di script.fn_check_listino_documento senza codice della matrice',
            v_reason;
    END IF;

    IF v_codice = 'E_CATEGORIA_LISTINO_UTILITY_DIVERSA' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', TG_NAME::text, 'E_CATEGORIA_LISTINO_UTILITY_DIVERSA',
            jsonb_build_object(
                'campo',                       'listino_id',
                'categoria_cliente_listino_id', NEW.id,
                'listino_id',                  NEW.listino_id,
                'utility_id',                  NEW.utility_id,
                'emittente_soggetto_ruolo_id', NEW.emittente_soggetto_ruolo_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    ELSE
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', TG_NAME::text, 'E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO',
            jsonb_build_object(
                'campo',                       'listino_id',
                'categoria_cliente_listino_id', NEW.id,
                'listino_id',                  NEW.listino_id,
                'utility_id',                  NEW.utility_id,
                'emittente_soggetto_ruolo_id', NEW.emittente_soggetto_ruolo_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_categorie_clienti_listini_guard_listino()
IS 'Guard BEFORE INSERT, e BEFORE UPDATE quando cambiano listino_id, utility_id o emittente_soggetto_ruolo_id, su anagrafiche.categorie_clienti_listini (brief-db-coerenza-listino-della-riga-di-commessa §7.4, opzione B di Tid del 2026-10-16): il listino della riga e'' della sua utility e del suo emittente. Predicato: script.fn_check_listino_documento, lo stesso di contratti e offerte (F-2 del 2026-10-08), con l''emittente fiscale tradotto dal ruolo (uq_emittenti_fiscali_ruolo). Codici della matrice, scelti dalla reason del primo motivo: E_CATEGORIA_LISTINO_UTILITY_DIVERSA, E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO (DATO_ERRATO, campo listino_id, frasi chiuse; un listino illeggibile sotto RLS e'' di un''altra azienda). Una reason senza codice della matrice fallisce forte. Ferma dove nasce lo sbaglio che altrimenti arriverebbe al push in commessa come E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
