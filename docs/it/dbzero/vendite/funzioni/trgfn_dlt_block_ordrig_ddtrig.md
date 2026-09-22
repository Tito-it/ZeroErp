{% include-markdown "it/dbzero/vendite/manual/trgfn_dlt_block_ordrig_ddtrig.md" %}
# ⚙️ Funzione `trgfn_dlt_block_ordrig_ddtrig`

```sql
CREATE FUNCTION trgfn_dlt_block_ordrig_ddtrig()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_documento  text;
  v_testata_id bigint;
  v_etichetta  text;
  v_cnt        bigint := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Tradurre in una frase il rifiuto di cancellare una riga di
  --   documento (DDT o ordine) che ha LEGAMI A VALLE: la FK
  --   bloccherebbe comunque, ma con un 23503 grezzo.
  --
  -- Rami:
  --   2a. la riga ha un fulfillment           -> E_DELETE_BLOCKED_FUL
  --   2b. la riga e' usata da resi/riconsegne -> E_DELETE_RIGA_DOC_REFERENZIATA
  --   3.  altrimenti                          -> si cancella
  --
  -- ⭐ rev 2026-09-22: il ramo 1 («il documento non e' piu' in
  --    bozza») NON sta piu' qui. La regola vive nel building
  --    block vendite.trgfn_doc_righe_lock_fuori_bozza, montato in
  --    fascia _a05_ su ddt_righe (tre porte) e ordini_righe
  --    (DELETE): parla PRIMA di questo trigger, quindi qui una
  --    riga arriva solo se il documento e' in bozza, oppure per
  --    un cascade partito dalla testata. Tenere il ramo anche
  --    qui sarebbe una seconda implementazione mai raggiunta.
  -- =========================================================

  -- ── Dispatch: quale documento, e qual e' la sua testata ──
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    v_documento  := 'ORDINE';
    v_testata_id := OLD.ordine_id;
  ELSIF TG_TABLE_NAME = 'ddt_righe' THEN
    v_documento  := 'DDT';
    v_testata_id := OLD.ddt_id;
  ELSE
    -- Errore di MONTAGGIO: il trigger e' stato agganciato a una
    -- tabella che questa funzione non conosce. E' l'unico ramo
    -- che resta su E_DELETE_NOT_ALLOWED, ed e' l'uso corretto di
    -- quel codice: un diritto che manca, non uno stato.
    PERFORM script.fn_log_and_raise_error(
      'database', 'trgfn_dlt_block_ordrig_ddtrig', 'E_DELETE_NOT_ALLOWED',
      jsonb_build_object('table', TG_TABLE_NAME, 'id', OLD.id),
      NULL::uuid,
      TG_TABLE_NAME,
      OLD.id::text);
  END IF;

  -- ── L'etichetta per le frasi ─────────────────────────────
  -- Dal lettore SECURITY DEFINER (testate e righe hanno RLS).
  -- ⚠️ Testata assente = CASCADE partito dalla testata: la regola
  --    di stato l'ha gia' applicata trgfn_doc_guard_delete_solo_bozza
  --    sulla testata, e i legami a valle valgono comunque —
  --    l'etichetta ripiega sul tipo di documento.
  SELECT t.etichetta
    INTO v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, v_testata_id) AS t;

  -- ── 2a. Fulfillment ─────────────────────────────────────
  -- La FK e' in ON DELETE RESTRICT: bloccherebbe comunque. Qui
  -- si traduce il 23503 in una frase.
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    SELECT count(*) INTO v_cnt
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ordine_riga_id = OLD.id;
  ELSE
    SELECT count(*) INTO v_cnt
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ddt_riga_id = OLD.id;
  END IF;

  IF v_cnt > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_dlt_block_ordrig_ddtrig', 'E_DELETE_BLOCKED_FUL',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'testata_id', v_testata_id,
                         'legami', v_cnt),
      NULL::uuid,
      COALESCE(v_etichetta, v_documento));
  END IF;

  -- ── 2b. Resi e riconsegne ───────────────────────────────
  -- FK in NO ACTION: stesso ragionamento del 2a.
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    SELECT count(*) INTO v_cnt
      FROM vendite.resi_righe r
     WHERE r.ordine_riga_id = OLD.id;
  ELSE
    SELECT count(*) INTO v_cnt
      FROM (SELECT 1 FROM vendite.resi_righe r
             WHERE r.ddt_riga_id = OLD.id
            UNION ALL
            SELECT 1 FROM vendite.resi_righe_riconsegne rr
             WHERE rr.ddt_riga_id = OLD.id) AS legami;
  END IF;

  IF v_cnt > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_dlt_block_ordrig_ddtrig', 'E_DELETE_RIGA_DOC_REFERENZIATA',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'testata_id', v_testata_id,
                         'legami', v_cnt),
      NULL::uuid,
      COALESCE(v_etichetta, v_documento));
  END IF;

  -- ── 3. Si cancella ──────────────────────────────────────
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()
IS 'Traduttore sul DELETE di una riga di DDT o ordine: se la riga ha legami a valle (fulfillment -> E_DELETE_BLOCKED_FUL; resi o riconsegne -> E_DELETE_RIGA_DOC_REFERENZIATA) il 23503 della FK diventa una frase; altrimenti la riga si cancella. ⭐ rev 2026-09-22: il ramo «documento non piu'' in bozza» (E_DELETE_RIGA_DOC_NON_BOZZA, dal 20260826-21) NON sta piu'' qui — la regola «le righe si toccano solo in bozza» vive nel building block vendite.trgfn_doc_righe_lock_fuori_bozza, montato in fascia _a05_ su ddt_righe (INSERT/UPDATE/DELETE) e ordini_righe (DELETE), che parla PRIMA di questo trigger; tenerlo anche qui sarebbe una seconda implementazione mai raggiunta. Testata assente = cascade partito dalla testata (la regola di stato l''ha applicata trgfn_doc_guard_delete_solo_bozza): i legami a valle si controllano comunque, con l''etichetta che ripiega sul tipo di documento. L''etichetta si legge da script.fn_get_stato_testata_documento (SECURITY DEFINER: testate e righe hanno RLS). E_DELETE_NOT_ALLOWED resta solo sul ramo «tabella non prevista» (errore di montaggio).';
```

---
{% include-markdown "signature-core.md" %}
