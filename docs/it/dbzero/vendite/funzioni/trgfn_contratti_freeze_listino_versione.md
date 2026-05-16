{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_freeze_listino_versione.md" %}
# ⚙️ Funzione `trgfn_contratti_freeze_listino_versione`

```sql
CREATE FUNCTION trgfn_contratti_freeze_listino_versione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_freeze_listino_versione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: al momento dell'attivazione (DRAFT→ATTIVO), fissa la versione
--   listino e verifica la coerenza del negoziato puro.
-- A) listino_id IS NULL: verifica almeno una AGGIUNTA con prezzo.
--    Errore: E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE (451).
-- B) listino_id NOT NULL + listino_versione_id IS NULL: fissa versione
--    operativa (stato IN ('ATTIVA','CHIUSA')) a CURRENT_DATE.
--    FIX Bug A: BOZZA esclusa dal lookup — non viene mai congelata.
--    Se non trovata: attivazione consentita con versione NULL (warning UI, §4.4).
-- C) listino_versione_id già valorizzato: nessuna azione.
-- Esce senza effetti su qualsiasi transizione diversa da DRAFT→ATTIVO.
DECLARE
    v_codice_da   config.stati_doc_contratti.codice_interno%TYPE;
    v_codice_a    config.stati_doc_contratti.codice_interno%TYPE;
    v_versione_id vendite.listini_versioni.id%TYPE;
BEGIN
    SELECT
        max(CASE WHEN id = OLD.stato_doc_contratto_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_contratto_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_contratti
     WHERE id IN (OLD.stato_doc_contratto_id, NEW.stato_doc_contratto_id);

    -- Attivo solo su DRAFT→ATTIVO
    IF v_codice_da <> 'DRAFT' OR v_codice_a <> 'ATTIVO' THEN
        RETURN NEW;
    END IF;

    IF NEW.listino_id IS NULL THEN
        -- Negoziato puro: almeno una AGGIUNTA con prezzo valorizzato
        IF NOT EXISTS (
            SELECT 1
              FROM vendite.contratti_righe cr
             WHERE cr.contratto_id = NEW.id
               AND cr.tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
               AND cr.prezzo_unitario IS NOT NULL
               AND cr.attivo = TRUE
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                TG_NAME::text,
                'E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE',
                jsonb_build_object('contratto_id', NEW.id, 'numero', NEW.numero),
                NEW.tx_id,
                NEW.id::text
            );
        END IF;
        RETURN NEW;
    END IF;

    -- Con listino: fissa versione operativa snapshot se non già valorizzata.
    -- stato IN ('ATTIVA','CHIUSA'): BOZZA non è operativa, mai snapshot.
    IF NEW.listino_versione_id IS NULL THEN
        SELECT lv.id
          INTO v_versione_id
          FROM vendite.listini_versioni lv
         WHERE lv.listino_id = NEW.listino_id
           AND lv.attivo     = TRUE
           AND lv.stato      IN ('ATTIVA', 'CHIUSA')
           AND lv.validita  @> CURRENT_DATE
         ORDER BY (lv.stato = 'ATTIVA') DESC
         LIMIT 1;

        -- Se trovata: fissa snapshot. Se non trovata (§4.4): attivazione
        -- consentita con listino_versione_id NULL (UI mostrerà warning).
        IF v_versione_id IS NOT NULL THEN
            NEW.listino_versione_id := v_versione_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_freeze_listino_versione()
IS 'Freeze versione listino su DRAFT→ATTIVO. Negoziato puro (listino_id NULL): richiede almeno una AGGIUNTA con prezzo. Con listino: fissa versione operativa (stato IN (''ATTIVA'',''CHIUSA'')) a CURRENT_DATE in listino_versione_id. BOZZA non viene mai congelata (Bug A fix 2026-05-16). Versione non trovata: attivazione consentita, listino_versione_id resta NULL. Errore negoziato puro senza righe: E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE (451).';
```

---
{% include-markdown "signature-core.md" %}
