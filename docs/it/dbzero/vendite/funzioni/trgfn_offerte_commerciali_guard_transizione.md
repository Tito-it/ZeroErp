# ⚙️ Funzione `trgfn_offerte_commerciali_guard_transizione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare transizioni stato non ammesse sul workflow offerta
-- commerciale (config-driven via stati_doc_offerte_transizioni).
-- Valorizza i timestamp di passaggio stato e applica guard listino
-- al momento dell'emissione (BOZZA->EMESSA).
DECLARE
    v_codice_da config.stati_doc_offerte.codice_interno%TYPE;
    v_codice_a  config.stati_doc_offerte.codice_interno%TYPE;
    v_stato_versione vendite.listini_versioni.stato%TYPE;
BEGIN
    -- Nessuna transizione effettiva: niente da validare.
    IF OLD.stato_doc_offerta_id = NEW.stato_doc_offerta_id THEN
        RETURN NEW;
    END IF;

    -- Risolve i codici interni degli stati per messaggi leggibili.
    SELECT
        max(CASE WHEN id = OLD.stato_doc_offerta_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_offerta_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_offerte
     WHERE id IN (OLD.stato_doc_offerta_id, NEW.stato_doc_offerta_id);

    -- Verifica transizione ammessa (config-driven, solo righe attive).
    IF NOT EXISTS (
        SELECT 1
          FROM config.stati_doc_offerte_transizioni
         WHERE stato_da_id = OLD.stato_doc_offerta_id
           AND stato_a_id  = NEW.stato_doc_offerta_id
           AND attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_OFFERTA_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'offerta_id', NEW.id,
                'stato_da',   coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
                'stato_a',    coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text)
            ),
            NEW.tx_id,
            coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
            coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text)
        );
    END IF;

    -- Guard specifica BOZZA -> EMESSA: listino_versione_id obbligatorio + ATTIVA.
    IF v_codice_da = 'BOZZA' AND v_codice_a = 'EMESSA' THEN

        -- listino_versione_id deve essere valorizzato.
        IF NEW.listino_versione_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO',
                jsonb_build_object('offerta_id', NEW.id),
                NEW.tx_id
            );
        END IF;

        -- La versione listino deve essere in stato ATTIVA.
        SELECT stato INTO v_stato_versione
          FROM vendite.listini_versioni
         WHERE id = NEW.listino_versione_id;

        IF v_stato_versione IS DISTINCT FROM 'ATTIVA' THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA',
                jsonb_build_object(
                    'offerta_id',          NEW.id,
                    'listino_versione_id', NEW.listino_versione_id,
                    'stato_versione',      v_stato_versione
                ),
                NEW.tx_id,
                coalesce(v_stato_versione, 'NULL')
            );
        END IF;

    END IF;

    -- Valorizza il timestamp corrispondente al passaggio stato.
    CASE v_codice_a
        WHEN 'EMESSA'    THEN NEW.data_emissione    := now();
        WHEN 'ACCETTATA' THEN NEW.data_accettazione := now();
        WHEN 'RIFIUTATA' THEN NEW.data_rifiuto      := now();
        WHEN 'ANNULLATA' THEN NEW.data_annullamento  := now();
        ELSE NULL;
    END CASE;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
IS 'BEFORE UPDATE OF stato_doc_offerta_id: blocca transizioni non ammesse (config-driven via config.stati_doc_offerte_transizioni). Guard BOZZA->EMESSA: listino_versione_id NOT NULL + stato ATTIVA. Valorizza data_emissione|data_accettazione|data_rifiuto|data_annullamento. rev 2026-05-24.';
```

---
{% include-markdown "signature-core.md" %}
