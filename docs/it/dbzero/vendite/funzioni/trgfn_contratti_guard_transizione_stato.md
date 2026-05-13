{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_guard_transizione_stato.md" %}
# ⚙️ Funzione `trgfn_contratti_guard_transizione_stato`

```sql
CREATE FUNCTION trgfn_contratti_guard_transizione_stato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_guard_transizione_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca transizioni stato non ammesse sul workflow contratti
--   (DRAFT -> ATTIVO -> CESSATO).
-- ATTIVO->CESSATO: distingue job automatico da cessazione manuale.
--   Job (GUC app.cessazione_automatica='true'): valido_al < CURRENT_DATE.
--   Manuale: valido_al >= CURRENT_DATE (oggi o futura, no riscrittura storica).
--   Manuale retroattiva: E_CONTRATTO_VALIDO_AL_RETROATTIVO (449).
-- Aggiornato 2026-05-12: blocca DRAFT->ATTIVO se componente BoM PENDING.
-- Aggiornato 2026-05-14: no-retroattiva su cessazione manuale.
DECLARE
    v_codice_da config.stati_doc_contratti.codice_interno%TYPE;
    v_codice_a  config.stati_doc_contratti.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    SELECT
        max(CASE WHEN id = OLD.stato_doc_contratto_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_contratto_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_contratti
     WHERE id IN (OLD.stato_doc_contratto_id, NEW.stato_doc_contratto_id);

    IF v_codice_da = 'DRAFT' AND v_codice_a = 'ATTIVO' THEN
        v_ammessa := true;

    ELSIF v_codice_da = 'ATTIVO' AND v_codice_a = 'CESSATO' THEN
        IF current_setting('app.cessazione_automatica', true) = 'true' THEN
            -- Job notturno (fn_apply_chiusura_scadenze): contratto gia' scaduto.
            -- Ammette valido_al < CURRENT_DATE (comportamento invariato pre-fix).
            v_ammessa := (NEW.valido_al IS NOT NULL
                          AND NEW.valido_al < CURRENT_DATE);
        ELSE
            -- Cessazione manuale da UI: vietata la riscrittura storica.
            -- Retroattiva (valido_al < oggi): raise codice specifico e esci.
            IF NEW.valido_al IS NOT NULL AND NEW.valido_al < CURRENT_DATE THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME::text,
                    'E_CONTRATTO_VALIDO_AL_RETROATTIVO',
                    jsonb_build_object(
                        'contratto_id', NEW.id,
                        'numero',       NEW.numero,
                        'valido_al',    NEW.valido_al,
                        'today',        CURRENT_DATE
                    ),
                    NEW.tx_id,
                    NEW.valido_al::text,
                    CURRENT_DATE::text
                );
            END IF;
            -- Ammessa se valido_al IS NOT NULL AND valido_al >= CURRENT_DATE.
            -- NULL: v_ammessa resta false -> raise E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA.
            v_ammessa := (NEW.valido_al IS NOT NULL);
        END IF;
    END IF;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object('contratto_id', NEW.id, 'numero', NEW.numero,
                'stato_da', v_codice_da, 'stato_a', v_codice_a,
                'valido_al', NEW.valido_al),
            NEW.tx_id, NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL'),
            coalesce(NEW.valido_al::text, 'NULL')
        );
    END IF;

    -- Check componenti BoM CASO A con prezzo PENDING (solo su DRAFT->ATTIVO).
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'ATTIVO' THEN
        IF EXISTS (
            SELECT 1 FROM vendite.contratti_righe cr
              JOIN vendite.contratti_righe_componenti crc
                ON crc.riga_contratto_id = cr.id
             WHERE cr.contratto_id = NEW.id
               AND crc.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME::text, 'E_COMPONENTE_PREZZO_PENDENTE',
                jsonb_build_object('contratto_id', NEW.id,
                    'hint', 'Componente BoM CASO A in attesa di approvazione prezzo. '
                         || 'Attendi esito su tutti i componenti prima di attivare il contratto.'),
                NEW.tx_id, NEW.id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_guard_transizione_stato()
IS 'Trigger function: controlla transizioni stato contratto (DRAFT->ATTIVO->CESSATO). ATTIVO->CESSATO: job automatico (GUC app.cessazione_automatica=true) ammette valido_al<oggi; cessazione manuale ammette valido_al>=oggi (no retroattiva). Retroattiva raise E_CONTRATTO_VALIDO_AL_RETROATTIVO (449); NULL raise E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA. Blocca DRAFT->ATTIVO se componenti PENDING (E_COMPONENTE_PREZZO_PENDENTE). rev 2026-05-14.';
```

---
{% include-markdown "signature-core.md" %}
