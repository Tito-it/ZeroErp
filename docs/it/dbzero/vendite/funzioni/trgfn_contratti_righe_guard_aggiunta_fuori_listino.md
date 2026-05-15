{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_righe_guard_aggiunta_fuori_listino.md" %}
# ⚙️ Funzione `trgfn_contratti_righe_guard_aggiunta_fuori_listino`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_aggiunta_fuori_listino()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca INSERT/UPDATE su contratti_righe con tipo_eccezione='AGGIUNTA'
--   se l'articolo è già presente nel listino del contratto.
-- Branch 1: listino_id IS NULL -> nessun check, AGGIUNTA sempre valida.
-- Branch 2: DRAFT (listino_versione_id IS NULL) -> verifica versione
--   attiva a CURRENT_DATE (listini_versioni WHERE validita @> CURRENT_DATE).
-- Branch 3: ATTIVO (listino_versione_id IS NOT NULL) -> verifica versione
--   fissata all'attivazione.
-- Errore se articolo trovato: E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO (450).
DECLARE
    v_listino_id          vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    v_in_listino          boolean := false;
BEGIN
    SELECT c.listino_id, c.listino_versione_id
      INTO v_listino_id, v_listino_versione_id
      FROM vendite.contratti c
     WHERE c.id = NEW.contratto_id;

    -- Branch 1: nessun listino -> AGGIUNTA sempre valida
    IF v_listino_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF v_listino_versione_id IS NULL THEN
        -- Branch 2: DRAFT -> versione attiva a CURRENT_DATE
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_versioni lv
              JOIN vendite.listini_righe lr
                ON lr.listino_versione_id = lv.id
             WHERE lv.listino_id = v_listino_id
               AND lv.validita @> CURRENT_DATE
               AND lv.attivo = TRUE
               AND lr.articolo_id = NEW.articolo_id
               AND lr.attivo = TRUE
        ) INTO v_in_listino;
    ELSE
        -- Branch 3: ATTIVO -> versione fissata
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_righe lr
             WHERE lr.listino_versione_id = v_listino_versione_id
               AND lr.articolo_id = NEW.articolo_id
               AND lr.attivo = TRUE
        ) INTO v_in_listino;
    END IF;

    IF v_in_listino THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO',
            jsonb_build_object(
                'contratto_id',        NEW.contratto_id,
                'articolo_id',         NEW.articolo_id,
                'listino_id',          v_listino_id,
                'listino_versione_id', v_listino_versione_id
            ),
            NULL::uuid,
            NEW.articolo_id::text,
            NEW.contratto_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino()
IS 'Guard AGGIUNTA fuori listino: blocca contratti_righe.tipo_eccezione=AGGIUNTA se l''articolo è già presente nel listino del contratto. DRAFT: verifica versione attiva a CURRENT_DATE. ATTIVO: verifica versione fissata (listino_versione_id). Nessun check se listino_id IS NULL. Errore: E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO (450). Step 2.2.';
```

---
{% include-markdown "signature-core.md" %}
