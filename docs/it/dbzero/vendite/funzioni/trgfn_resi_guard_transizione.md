{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_resi_guard_transizione`

```sql
CREATE FUNCTION trgfn_resi_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato reso.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_reso (no grafo
--   hardcodato). Mirror di trgfn_ddt_guard_transizione.
DECLARE
    v_codice_da config.stati_doc_reso.codice_interno%TYPE;
    v_codice_a  config.stati_doc_reso.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_guc          text;      -- valore di una GUC: nessuna colonna
    v_dentro_verbo boolean;   -- calcolato
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_reso_id IS NOT DISTINCT FROM OLD.stato_doc_reso_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_reso_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_reso_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_reso
     WHERE id IN (OLD.stato_doc_reso_id, NEW.stato_doc_reso_id);

    -- La transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_reso t
         WHERE t.stato_da_id = OLD.stato_doc_reso_id
           AND t.stato_a_id  = NEW.stato_doc_reso_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_RESO_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'reso_id',  NEW.id,
                'numero',   NEW.numero,
                'stato_da', v_codice_da,
                'stato_a',  v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2 — LA PORTA DEL REGISTRO (rev 2026-09-28,
    --   brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f). I passaggi che
    --   toccano il registro di magazzino — la conferma (carico) e l'annullo di
    --   un reso confermato (storno) — di un reso che fa rientrare merce
    --   (vendite.fn_reso_muove_merce, sulla riga NUOVA) si fanno solo dai verbi
    --   vendite.fn_conferma_reso / vendite.fn_annulla_reso, che nella stessa
    --   transazione scrivono i movimenti. Due condizioni, come la porta della
    --   bolla (Regola 3 di trgfn_ddt_guard_transizione): la GUC transazionale
    --   porta NEW.id E chi esegue e' il proprietario della tabella (un verbo
    --   DEFINER, non l'app che accende la GUC da se').
    --   ⚠️ DRAFT -> ANNULLATO non tocca il registro: resta fuori.
    IF ((v_codice_da = 'DRAFT'      AND v_codice_a = 'CONFERMATO')
        OR (v_codice_da = 'CONFERMATO' AND v_codice_a = 'ANNULLATO'))
       AND vendite.fn_reso_muove_merce(NEW) THEN
        v_guc          := current_setting('zeroerp.reso_cambio_stato', true);
        v_dentro_verbo := script.fn_is_proprietario_tabella(TG_RELID);
        IF v_guc IS DISTINCT FROM NEW.id::text OR NOT v_dentro_verbo THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_RESO_STATO_SOLO_DA_VERBO',
                jsonb_build_object(
                    'reso_id',      NEW.id,
                    'numero',       NEW.numero,
                    'stato_da',     v_codice_da,
                    'stato_a',      v_codice_a,
                    'guc_valore',   v_guc,
                    'dentro_verbo', v_dentro_verbo,
                    'db_user',      current_user
                ),
                NEW.tx_id,
                coalesce(NEW.numero, NEW.id::text),
                coalesce(v_codice_a, 'NULL')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato reso letto da config.transizioni_stati_reso (E_STATO_RESO_TRANSIZIONE_NON_VALIDA). Mirror di trgfn_ddt_guard_transizione. rev 2026-07-13. rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f): Regola 2, la PORTA DEL REGISTRO. DRAFT->CONFERMATO e CONFERMATO->ANNULLATO di un reso che fa rientrare merce (vendite.fn_reso_muove_merce sulla riga NUOVA) passano solo dai verbi vendite.fn_conferma_reso / vendite.fn_annulla_reso: GUC transazionale zeroerp.reso_cambio_stato = NEW.id E chi esegue e'' il proprietario della tabella (script.fn_is_proprietario_tabella), altrimenti E_RESO_STATO_SOLO_DA_VERBO. I resi che non muovono merce, e DRAFT->ANNULLATO, restano all''UPDATE diretto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
