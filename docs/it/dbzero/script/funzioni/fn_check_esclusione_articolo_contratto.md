{% include-markdown "it/dbzero/script/manual/fn_check_esclusione_articolo_contratto.md" %}
# ⚙️ Funzione `fn_check_esclusione_articolo_contratto`

```sql
CREATE FUNCTION fn_check_esclusione_articolo_contratto(p_contratto_id bigint, p_articolo_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_esclusione_articolo_contratto(p_contratto_id bigint, p_articolo_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: elencare i motivi per cui un articolo NON si puo' escludere
--   da un contratto. Funzione PURA (fn_check_*): nessun raise di
--   dominio, nessuna scrittura.
-- Consumatori: il guard
--   vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle
--   (solleva il PRIMO motivo) e vendite.fn_contratto_righe_preview
--   (spegne «Escludi» sulla riga e dice perche').
-- Ritorna: [] se ammesso; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio, valori}.
DECLARE
    v_motivi              jsonb := '[]'::jsonb;
    v_listino_id          vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    v_e_figlio_bundle     boolean := false;
BEGIN
    SELECT c.listino_id, c.listino_versione_id
      INTO v_listino_id, v_listino_versione_id
      FROM vendite.contratti c
     WHERE c.id = p_contratto_id;

    -- Ramo 1: nessun listino -> nessun bundle da cui escludere.
    -- ⚠️ Vale anche per un contratto che non si vede o non esiste: la
    --    check non ha niente da nominare, e chi scrive passa comunque
    --    dalla policy e dalle FK.
    IF v_listino_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    IF v_listino_versione_id IS NULL THEN
        -- Ramo 2: bozza -> la versione in vigore OGGI (ATTIVA o CHIUSA;
        -- BOZZA esclusa, «Bug A»). Era un EXISTS su tutte le valide: dal
        -- 2026-09-28 sono al piu' una per costruzione (§8.15).
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_righe_componenti lrc
             -- rev 2026-09-28: la versione in vigore oggi, dalla sede
             -- unica (al piu' una per costruzione, §8.15).
             WHERE lrc.listino_versione_id =
                   vendite.fn_listino_versione_in_vigore(v_listino_id, CURRENT_DATE)
               AND lrc.articolo_figlio_id = p_articolo_id
               AND lrc.attivo             = TRUE
               AND lrc.validita          @> CURRENT_DATE
        ) INTO v_e_figlio_bundle;
    ELSE
        -- Ramo 3: contratto attivo -> la versione fissata.
        SELECT EXISTS (
            SELECT 1
              FROM vendite.listini_righe_componenti lrc
             WHERE lrc.listino_versione_id = v_listino_versione_id
               AND lrc.articolo_figlio_id  = p_articolo_id
               AND lrc.attivo              = TRUE
               AND lrc.validita           @> CURRENT_DATE
        ) INTO v_e_figlio_bundle;
    END IF;

    -- ---- MOTIVO 1 — e' un componente di un bundle ------------------
    -- Il bundle si vende come unita': si esclude il padre, mai il
    -- singolo figlio. `valori` e' il VARIADIC che il guard passava
    -- gia' (l'articolo): la frase non si ricompone in due posti.
    IF v_e_figlio_bundle THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA',
            'reason',     'FIGLIO_DI_BUNDLE',
            'reason_key', 'vendite.contratti.escludi_blocco.figlio_di_bundle',
            'dettaglio',  jsonb_build_object(
                              'contratto_id',        p_contratto_id,
                              'articolo_id',         p_articolo_id,
                              'listino_id',          v_listino_id,
                              'listino_versione_id', v_listino_versione_id),
            'valori',     jsonb_build_array(p_articolo_id::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_esclusione_articolo_contratto(p_contratto_id bigint, p_articolo_id uuid)
IS 'I motivi per cui un articolo NON si puo'' escludere da un contratto: [] se ammesso, altrimenti un array ordinato di {codice, reason, reason_key, dettaglio, valori} (linee-guida-sql §12.5). Unico motivo oggi: FIGLIO_DI_BUNDLE — l''articolo e'' un componente di un bundle del listino del contratto, e il bundle si vende come unita'' (si esclude il padre, mai il figlio); codice E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA, reason_key vendite.contratti.escludi_blocco.figlio_di_bundle. Il predicato era nel guard vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle, che da 20260928-31 chiama questa funzione e solleva il primo motivo; la legge anche vendite.fn_contratto_righe_preview per spegnere «Escludi» sulla riga con il motivo (brief-db-liste-righe-documento, 2026-09-28). Prende i VALORI (contratto, articolo) e non l''id di una riga: una riga dal listino non esiste in contratti_righe finche'' non la si esclude. Versione del listino: in bozza tutte le ATTIVA/CHIUSA valide oggi, da attivo quella fissata — la semantica del guard. SECURITY INVOKER: legge il contratto coi diritti di chi agisce.';
```

---
{% include-markdown "signature-core.md" %}
