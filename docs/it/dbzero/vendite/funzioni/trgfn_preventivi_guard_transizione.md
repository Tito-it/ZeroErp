# ⚙️ Funzione `trgfn_preventivi_guard_transizione`

```sql
CREATE FUNCTION trgfn_preventivi_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni del preventivo.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e ATTIVA in config.transizioni_stati_preventivi.
--   Letto dalla matrice, nessun grafo hardcodato: stessa sorgente
--   di fn_available_actions_preventivo, quindi la UI non puo'
--   proporre cio' che il database rifiuta, ne' viceversa.
--   Mirror di vendite.trgfn_ordini_guard_transizione (Regola 1).
--   Brief: brief-db-vie-uscita-operatore §6.2, §7.4 punto 3.
--
-- Cosa NON fa, per scelta:
--   - l'annullamento ha il suo guard dedicato
--     (trgfn_preventivi_guard_annullamento, 20260804-35): qui si
--     verifica solo che la strada esista, non che sia percorribile;
--   - la regola "documento senza righe" vive ancora nella porta
--     vendite.fn_cambia_stato_preventivo e un UPDATE diretto la
--     aggira: e' un'asimmetria dichiarata, non una dimenticanza.
DECLARE
    v_codice_da config.stati_doc_preventivi.codice_interno%TYPE;
    v_codice_a  config.stati_doc_preventivi.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_preventivo_id IS NOT DISTINCT FROM OLD.stato_doc_preventivo_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_preventivo_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_preventivo_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_preventivi
     WHERE id IN (OLD.stato_doc_preventivo_id, NEW.stato_doc_preventivo_id);

    -- Regola unica: la transizione deve esistere ed essere attiva.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_preventivi t
         WHERE t.stato_da_id = OLD.stato_doc_preventivo_id
           AND t.stato_a_id  = NEW.stato_doc_preventivo_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_PREV_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'numero',        NEW.numero,
                'stato_da',      v_codice_da,
                'stato_a',       v_codice_a
            ),
            NEW.tx_id,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_transizione()
IS 'Trigger function: rende vincolante per il database la matrice config.transizioni_stati_preventivi, come gia'' avviene per ordine, DDT, commessa, reso, contratto e offerta. Legge la matrice (nessun grafo hardcodato), quindi condivide la sorgente con fn_available_actions_preventivo: la UI non puo'' proporre cio'' che il database rifiuta. Non valuta l''ammissibilita'' dell''annullamento, che ha il guard dedicato trgfn_preventivi_guard_annullamento. Creata 2026-08-05 (brief-db-vie-uscita-operatore §6.2, §7.4 punto 3).';
```

---
{% include-markdown "signature-core.md" %}
