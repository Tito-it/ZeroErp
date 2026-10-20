{% include-markdown "it/dbzero/config/manual/trgfn_stati_doc_guard_esito_verdetto.md" %}
# ⚙️ Funzione `trgfn_stati_doc_guard_esito_verdetto`

```sql
CREATE FUNCTION trgfn_stati_doc_guard_esito_verdetto()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard (fase a10): la proiezione `esito` di una config.stati_doc_*
-- deve essere un verdetto (esiti_flussi_pratiche.is_verdetto=true).
-- NULL = nessun verdetto: ammesso. Codice inesistente: bloccato qui
-- (prima della FK) con lo stesso errore parlante.
DECLARE
    v_is_verdetto boolean;
BEGIN
    IF NEW.esito IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT e.is_verdetto
      INTO v_is_verdetto
      FROM config.esiti_flussi_pratiche e
     WHERE e.codice_interno = NEW.esito;

    IF v_is_verdetto IS DISTINCT FROM true THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'config.trgfn_stati_doc_guard_esito_verdetto',
            'E_STATO_DOC_ESITO_NON_VERDETTO',
            jsonb_build_object(
                'campo', 'esito',
                'tabella',        TG_TABLE_NAME,
                'codice_interno', NEW.codice_interno,
                'esito',          NEW.esito
            ),
            NULL,
            NEW.esito::text,
            TG_TABLE_NAME::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()
IS 'Guard generico per le config.stati_doc_*: la proiezione `esito` (D1, brief-db-proiezione-stato-dominio) deve referenziare un esito con is_verdetto=true in config.esiti_flussi_pratiche; NULL ammesso (nessun verdetto). Blocca gli esiti di instradamento di dominio e i codici inesistenti con E_STATO_DOC_ESITO_NON_VERDETTO. Riusabile su ogni dominio del roll-out (legge solo NEW.esito/NEW.codice_interno).';
```

</div>

---
{% include-markdown "signature-core.md" %}
