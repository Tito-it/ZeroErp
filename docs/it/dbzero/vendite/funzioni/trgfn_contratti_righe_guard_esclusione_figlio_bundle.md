{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_righe_guard_esclusione_figlio_bundle.md" %}
# ⚙️ Funzione `trgfn_contratti_righe_guard_esclusione_figlio_bundle`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_esclusione_figlio_bundle()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca INSERT/UPDATE su contratti_righe con tipo_eccezione='ESCLUSIONE'
--   se l'articolo è un componente figlio di un bundle nel listino del contratto.
--   L'ESCLUSIONE si applica al padre bundle o a un articolo standalone,
--   mai al singolo figlio (il bundle è un prodotto venduto come unità).
-- Branch 1: listino_id IS NULL → nessun bundle, RETURN NEW.
-- Branch 2: DRAFT (listino_versione_id IS NULL) → verifica versione operativa
--   stato IN ('ATTIVA','CHIUSA') a CURRENT_DATE. Bug A fix applicato.
-- Branch 3: ATTIVO (listino_versione_id IS NOT NULL) → verifica versione fissata.
-- Errore: E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA (455).
DECLARE
    v_listino_id          vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    v_e_figlio_bundle     boolean := FALSE;
BEGIN
    SELECT c.listino_id, c.listino_versione_id
      INTO v_listino_id, v_listino_versione_id
      FROM vendite.contratti c
     WHERE c.id = NEW.contratto_id;

    -- Branch 1: nessun listino → nessun bundle da cui escludere
    IF v_listino_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF v_listino_versione_id IS NULL THEN
        -- Branch 2: DRAFT → versione operativa a CURRENT_DATE
        -- articolo_figlio_id: colonna corretta (UUID articolo).
        -- articolo_componente_id referenzia articoli_componenti.id, non articoli.id.
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_versioni lv
              JOIN vendite.listini_righe_componenti lrc
                ON lrc.listino_versione_id = lv.id
             WHERE lv.listino_id = v_listino_id
               AND lv.attivo      = TRUE
               AND lv.stato       IN ('ATTIVA', 'CHIUSA')
               AND lv.validita   @> CURRENT_DATE
               AND lrc.articolo_figlio_id = NEW.articolo_id
               AND lrc.attivo             = TRUE
               AND lrc.validita          @> CURRENT_DATE
        ) INTO v_e_figlio_bundle;
    ELSE
        -- Branch 3: ATTIVO → versione fissata all'attivazione
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_righe_componenti lrc
             WHERE lrc.listino_versione_id  = v_listino_versione_id
               AND lrc.articolo_figlio_id   = NEW.articolo_id
               AND lrc.attivo               = TRUE
               AND lrc.validita            @> CURRENT_DATE
        ) INTO v_e_figlio_bundle;
    END IF;

    IF v_e_figlio_bundle THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA',
            jsonb_build_object(
                'contratto_id', NEW.contratto_id,
                'articolo_id',  NEW.articolo_id
            ),
            NEW.tx_id,
            NEW.articolo_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle()
IS 'Guard ESCLUSIONE figlio bundle: blocca contratti_righe.tipo_eccezione=ESCLUSIONE se l''articolo è componente figlio (articolo_figlio_id) di un bundle nel listino del contratto. DRAFT (Branch 2): versione operativa ATTIVA/CHIUSA a CURRENT_DATE. ATTIVO (Branch 3): versione fissata. Nessun check se listino_id IS NULL (Branch 1). Errore: E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA (455). §6.1 2026-05-16.';
```

---
{% include-markdown "signature-core.md" %}
