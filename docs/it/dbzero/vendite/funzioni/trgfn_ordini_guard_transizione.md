{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ordini_guard_transizione`

```sql
CREATE FUNCTION trgfn_ordini_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato ordine.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_ordini. In piu',
--   DRAFT->CONFERMATO richiede almeno una riga ordine ATTIVA, e
--   ->ANNULLATO passa da script.fn_check_ordine_annullabile.
--   Letto dalla matrice (no grafo hardcodato): SSOT col lato
--   lettura fn_available_actions_ordine.
--   rev 2026-07-16: Regola 2 filtra attivo IS TRUE.
--   rev 2026-08-04: Regola 3, l'annullamento riattivato ha i suoi
--   controlli (brief-db-vie-uscita-operatore).
DECLARE
    v_codice_da config.stati_doc_ordini.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ordini.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_motivi    jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ordine_id IS NOT DISTINCT FROM OLD.stato_doc_ordine_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ordine_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ordine_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_ordini
     WHERE id IN (OLD.stato_doc_ordine_id, NEW.stato_doc_ordine_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_ordini t
         WHERE t.stato_da_id = OLD.stato_doc_ordine_id
           AND t.stato_a_id  = NEW.stato_doc_ordine_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_ORDINE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'ordine_id', NEW.id,
                'numero',    NEW.numero,
                'stato_da',  v_codice_da,
                'stato_a',   v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: DRAFT->CONFERMATO richiede almeno una riga ATTIVA.
    -- Spostata da ordini_service.py (E_ORD_NESSUNA_RIGA inline) per
    -- DB-first: vale per ogni chiamante, non solo conferma().
    -- Una riga disattivata e' logicamente cancellata: un ordine con
    -- sole righe inattive e' vuoto e non va confermato.
    -- Nessun vincolo su quantita/prezzo/totale: conta la sola
    -- presenza (un ordine a totale zero deve poter avanzare).
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'CONFERMATO' THEN
        IF NOT EXISTS (
            SELECT 1 FROM vendite.ordini_righe r
             WHERE r.ordine_id = NEW.id
               AND r.attivo IS TRUE
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_ORDINE_CONFERMA_SENZA_RIGHE',
                jsonb_build_object(
                    'ordine_id', NEW.id,
                    'numero',    NEW.numero
                ),
                NEW.tx_id,
                NEW.id::text,
                coalesce(NEW.numero, 'NULL')
            );
        END IF;
    END IF;

    -- Regola 3 (rev 2026-08-04): l'annullamento non deve poter
    -- cancellare un documento che ha gia' prodotto qualcosa a
    -- valle. La regola vive nella funzione pura, la STESSA che
    -- fn_available_actions_ordine usa per accendere il bottone:
    -- qui si solleva soltanto, col codice del PRIMO motivo.
    IF v_codice_a = 'ANNULLATO' THEN
        v_motivi := script.fn_check_ordine_annullabile(NEW.id);

        IF jsonb_array_length(v_motivi) > 0 THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                v_motivi -> 0 ->> 'codice',
                jsonb_build_object(
                    'ordine_id', NEW.id,
                    'numero',    NEW.numero,
                    'stato_da',  v_codice_da,
                    'stato_a',   v_codice_a,
                    'motivi',    v_motivi
                ),
                NEW.tx_id,
                coalesce(NEW.numero, NEW.id::text),
                coalesce(v_motivi -> 0 ->> 'dettaglio', '0')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_guard_transizione()
IS 'Trigger function: enforcement del grafo transizioni stato ordine (matrice config.transizioni_stati_ordini), riga attiva obbligatoria su DRAFT->CONFERMATO, e dal 2026-08-04 controlli sull''annullamento delegati a script.fn_check_ordine_annullabile — la stessa funzione letta da fn_available_actions_ordine, cosi'' bottone e guard non divergono.';
```

---
{% include-markdown "signature-core.md" %}
