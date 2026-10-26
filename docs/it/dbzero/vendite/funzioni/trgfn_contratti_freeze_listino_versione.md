{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_freeze_listino_versione.md" %}
# ⚙️ Funzione `trgfn_contratti_freeze_listino_versione`

```sql
CREATE FUNCTION trgfn_contratti_freeze_listino_versione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_freeze_listino_versione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- Scopo: al momento dell'attivazione (DRAFT→ATTIVO), fissa la versione
--   listino e verifica la coerenza del negoziato puro.
-- A) listino_id IS NULL: verifica almeno una AGGIUNTA con prezzo.
--    Errore: E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE (451).
-- B) listino_id NOT NULL: congela la versione operativa,
--    vendite.fn_listino_versione_operativa (la fissata, altrimenti quella
--    in vigore oggi). Se non ce n'e' una il contratto NON si attiva
--    (rev 2026-10-07, decisione A-D2 di Tid, brief-db-offerta-emissione-
--    ed-erogazione §C.1.2): primo motivo di
--    script.fn_check_listino_congelabile, lo stesso della capability.
--    Prima si attivava con la versione NULL (§4.4 del 2026-05-18) e da li'
--    il risolutore delle righe lo faceva galleggiare sulla versione in
--    vigore di ogni giorno: l'opposto di «congela all'attivazione».
-- C) listino_versione_id gia' valorizzato (dal push dell'offerta): resta.
-- Esce senza effetti su qualsiasi transizione diversa da DRAFT→ATTIVO.
DECLARE
    v_codice_da   config.stati_doc_contratti.codice_interno%TYPE;
    v_codice_a    config.stati_doc_contratti.codice_interno%TYPE;
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

    -- Con listino: prima il predicato, poi il congelamento (rev 2026-10-07).
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        script.fn_check_listino_congelabile('CONTRATTO', NEW.listino_id, NEW.listino_versione_id),
        NULL,
        NEW.tx_id,
        jsonb_build_object('contratto_id', NEW.id, 'numero', NEW.numero));

    NEW.listino_versione_id := vendite.fn_listino_versione_operativa(
        NEW.listino_id, NEW.listino_versione_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_freeze_listino_versione()
IS 'Trigger BEFORE UPDATE su vendite.contratti, solo su DRAFT->ATTIVO. Negoziato puro (listino_id NULL): richiede almeno una AGGIUNTA attiva con prezzo (E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE). Con listino: solleva il primo motivo di script.fn_check_listino_congelabile(''CONTRATTO'', ...) — nessuna versione in vigore oggi, E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO — e congela listino_versione_id := vendite.fn_listino_versione_operativa (la fissata, altrimenti quella in vigore oggi). Una versione già fissata (dal push dell''offerta) resta anche se nel frattempo si è chiusa: è quella che il cliente ha accettato. Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, decisione A-D2 di Tid): prima il contratto si attivava con la versione NULL (§4.4 del 2026-05-18) e il risolutore delle righe lo faceva galleggiare sulla versione in vigore di ogni giorno. La capability script.fn_available_actions_contratto legge la stessa check e spegne «Attiva» col motivo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
