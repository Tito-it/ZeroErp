{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_indirizzi_obbligatori.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_indirizzi_obbligatori`

```sql
CREATE FUNCTION trgfn_ddt_guard_indirizzi_obbligatori()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-60, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della
--   sorgente.
-- Scopo: bloccare l'emissione (EMESSO) di un DDT privo degli
--   indirizzi marcati obbligatori per l'ambito DDT, o con un
--   indirizzo d'anagrafica che non e' del suo cliente.
--   rev 2026-07-19: valutazione delegata a
--   script.fn_check_ddt_emittibile — single source con la capability.
--   rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente,
--   D-3): + E_INDIRIZZO_DOC_NON_DEL_CLIENTE (punto 4-bis della check).
-- ⚠️ v_motivi e v_motivo nudi: l'array dei motivi di una check e un
--   suo elemento, jsonb senza colonna da ancorare.
DECLARE
    v_stato_codice config.stati_doc_ddt.codice_interno%TYPE;
    v_motivi       jsonb;
    v_motivo       jsonb;
    v_mancanti     text[];
BEGIN
    SELECT sdd.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    IF v_stato_codice IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_ddt_emittibile(NEW);

    -- 1. Indirizzi obbligatori mancanti.
    SELECT m INTO v_motivo
      FROM jsonb_array_elements(v_motivi) AS m
     WHERE m->>'codice' = 'E_INDIRIZZO_DOC_OBBLIGATORIO'
     LIMIT 1;

    IF v_motivo IS NOT NULL THEN
        SELECT array_agg(x) INTO v_mancanti
          FROM jsonb_array_elements_text(v_motivo->'dettaglio'->'mancanti') AS x;

        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_INDIRIZZO_DOC_OBBLIGATORIO',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'ambito',   'DDT_VENDITA',
                'mancanti', v_mancanti),
            NEW.tx_id,
            'DDT',
            NEW.id::text,
            array_to_string(v_mancanti, ', ')
        );
    END IF;

    -- 2. Un indirizzo d'anagrafica che non e' del cliente della bolla
    --    (rev 2026-10-11). La frase: il tipo leggibile, dal motivo.
    v_motivo := NULL;
    SELECT m INTO v_motivo
      FROM jsonb_array_elements(v_motivi) AS m
     WHERE m->>'codice' = 'E_INDIRIZZO_DOC_NON_DEL_CLIENTE'
     LIMIT 1;

    IF v_motivo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_INDIRIZZO_DOC_NON_DEL_CLIENTE',
            jsonb_build_object(
                'campo',  'tipo_indirizzo_id',
                'ddt_id', NEW.id,
                'numero', NEW.numero,
                'tipi',   v_motivo->'dettaglio'->'tipi'),
            NEW.tx_id,
            v_motivo->'valori'->>0
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()
IS 'Blocca l''emissione (EMESSO) di un DDT privo degli indirizzi marcati obbligatori per l''ambito DDT (E_INDIRIZZO_DOC_OBBLIGATORIO). rev 2026-07-19: valutazione delegata a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt); codice errore e argomenti invariati. rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-3 di Tid): e'' il guard degli INDIRIZZI all''emissione, e solleva anche il punto 4-bis della check, E_INDIRIZZO_DOC_NON_DEL_CLIENTE (campo tipo_indirizzo_id, valore: il tipo leggibile dal motivo), dopo i mancanti come nella check. La check si chiama una volta per i due rami. Rev 2026-10-20 (20261020-60, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
