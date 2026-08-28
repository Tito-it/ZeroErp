{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_guard_transizione.md" %}
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
-- rev 2026-08-28: + regola del rientro da uno stato di superamento;
-- data_emissione non si riscrive su un secondo ingresso in EMESSA.
DECLARE
    v_codice_da config.stati_doc_offerte.codice_interno%TYPE;
    v_codice_a  config.stati_doc_offerte.codice_interno%TYPE;
    v_superato_da boolean;
    v_superato_a  boolean;
    v_figlia_viva_codice vendite.offerte_commerciali.codice%TYPE;
    v_stato_versione vendite.listini_versioni.stato%TYPE;
BEGIN
    -- Nessuna transizione effettiva: niente da validare.
    IF OLD.stato_doc_offerta_id = NEW.stato_doc_offerta_id THEN
        RETURN NEW;
    END IF;

    -- Risolve i codici interni degli stati per messaggi leggibili,
    -- e la dichiarazione di superamento dei due estremi.
    SELECT
        max(CASE WHEN id = OLD.stato_doc_offerta_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_offerta_id THEN codice_interno END),
        bool_or(id = OLD.stato_doc_offerta_id AND is_superato IS TRUE),
        bool_or(id = NEW.stato_doc_offerta_id AND is_superato IS TRUE)
      INTO v_codice_da, v_codice_a, v_superato_da, v_superato_a
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

    -- ⭐ RIENTRO da uno stato di superamento. La transizione SUPERATA->EMESSA
    -- esiste per l'automatismo «annullo la revisione, il padre torna vivo»
    -- (trg_offerte_commerciali_z90_rientro_padre_upd). Ma una transizione
    -- ammessa e' una porta aperta a chiunque scriva, quindi la condizione va
    -- detta qui, dove vale per tutti: si esce dal superamento SOLO se non c'e'
    -- piu' una revisione figlia viva. Altrimenti il lineage avrebbe due
    -- revisioni vive insieme, che e' l'invariante che il dominio non ammette.
    IF COALESCE(v_superato_da, false) AND NOT COALESCE(v_superato_a, false) THEN

        -- Una figlia "viva" e' una revisione il cui stato non e' di
        -- annullamento: una revisione abortita non rimpiazza nessuno.
        -- ⚠️ Legge sotto RLS, e regge perche' le figlie ereditano
        -- l'emittente del padre (fn_crea_revisione_offerta) e la policy
        -- scopa per emittente: chi aggiorna il padre vede le figlie.
        SELECT f.codice
          INTO v_figlia_viva_codice
          FROM vendite.offerte_commerciali f
          JOIN config.stati_doc_offerte sf
            ON sf.id = f.stato_doc_offerta_id
         WHERE f.revisione_padre_id = NEW.id
           AND sf.is_abortito IS FALSE
         ORDER BY f.revisione_numero DESC, f.id DESC
         LIMIT 1;

        IF v_figlia_viva_codice IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA',
                jsonb_build_object(
                    'offerta_id',   NEW.id,
                    'stato_da',     coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
                    'stato_a',      coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text),
                    'revisione_viva_codice', v_figlia_viva_codice
                ),
                NEW.tx_id,
                coalesce(NEW.codice, NEW.id::text),
                v_figlia_viva_codice
            );
        END IF;

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
                NEW.tx_id,
                NEW.id::text
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
    -- ⚠️ data_emissione con COALESCE: un rientro SUPERATA->EMESSA e' un
    -- SECONDO ingresso in EMESSA, e riscrivere la data cancellerebbe il
    -- giorno in cui l'offerta e' stata davvero mandata al cliente. Sul primo
    -- ingresso (BOZZA->EMESSA) la colonna e' NULL: valore identico a prima.
    CASE v_codice_a
        WHEN 'EMESSA'    THEN NEW.data_emissione    := COALESCE(NEW.data_emissione, now());
        WHEN 'ACCETTATA' THEN NEW.data_accettazione := now();
        WHEN 'RIFIUTATA' THEN NEW.data_rifiuto      := now();
        WHEN 'ANNULLATA' THEN NEW.data_annullamento  := now();
        ELSE NULL;
    END CASE;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
IS 'BEFORE UPDATE OF stato_doc_offerta_id: blocca transizioni non ammesse (config-driven via config.stati_doc_offerte_transizioni). Guard BOZZA->EMESSA: listino_versione_id NOT NULL + stato ATTIVA. Regola del RIENTRO (rev 2026-08-28): si esce da uno stato con is_superato solo se non esiste piu'' una revisione figlia non abortita, altrimenti E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA — la condizione vale per chiunque scriva, non solo per il trigger di rientro. Valorizza data_accettazione|data_rifiuto|data_annullamento, e data_emissione solo se ancora NULL (un rientro non riscrive la data di emissione reale).';
```

---
{% include-markdown "signature-core.md" %}
