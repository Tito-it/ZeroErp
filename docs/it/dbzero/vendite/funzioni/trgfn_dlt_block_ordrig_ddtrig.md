{% include-markdown "it/dbzero/vendite/manual/trgfn_dlt_block_ordrig_ddtrig.md" %}
# ⚙️ Funzione `trgfn_dlt_block_ordrig_ddtrig`

```sql
CREATE FUNCTION trgfn_dlt_block_ordrig_ddtrig()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
  --   Sul DELETE di una riga di documento (DDT o ordine) che ha
  --   LEGAMI A VALLE: tradurre il 23503 della FK in una frase, o
  --   ritirare il legame quando il modello lo ammette.
  --
  -- Rami:
  --   riga d'ordine:
  --     2a. ha un fulfillment               -> E_DELETE_BLOCKED_FUL
  --     2b. e' usata da resi                -> E_DELETE_RIGA_DOC_REFERENZIATA
  --   riga di DDT:
  --     2b. e' l'origine di un reso         -> E_DELETE_RIGA_DOC_REFERENZIATA
  --     2a. ha legami con l'origine (fulfillment, ponte di
  --         ri-consegna)                    -> si RITIRANO con la riga, e
  --         l'ordine si riproietta (rev 2026-10-11, D-3, D-7)
  --   3.  altrimenti                        -> si cancella
  --
  -- ⭐ rev 2026-09-22: il ramo «il documento non e' piu' in bozza» NON
  --    sta qui: lo dice il building block
  --    vendite.trgfn_doc_righe_lock_fuori_bozza in fascia _a05_, PRIMA
  --    di questo trigger. Quindi una riga arriva qui solo col documento
  --    in bozza, o per un cascade partito dalla testata (che si elimina
  --    solo in bozza: trgfn_doc_guard_delete_solo_bozza).
  -- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-3): la
  --    riga di DDT evasa si toglie in bozza, e il suo fulfillment se ne
  --    va con lei. Ritira QUESTA madre, aprendo la porta del guard del
  --    legame (GUC zeroerp.ddt_riga_ritira_legame = id della riga) e
  --    richiudendola; la FK resta ON DELETE RESTRICT, di proposito.
  --    Dal D-7 anche il ponte di ri-consegna (riga di reso) si ritira
  --    con la riga. Il 2b parla PRIMA del ritiro, e sulla riga di DDT
  --    guarda solo i resi che la hanno come ORIGINE.
  -- =========================================================

  -- ── Dispatch: quale documento, e qual e' la sua testata ──
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    v_documento  := 'ORDINE_VENDITA';
    v_testata_id := OLD.ordine_id;
  ELSIF TG_TABLE_NAME = 'ddt_righe' THEN
    v_documento  := 'DDT_VENDITA';
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

  -- ── 2a. Fulfillment della riga d'ordine ─────────────────
  -- La FK e' in ON DELETE RESTRICT: bloccherebbe comunque. Qui
  -- si traduce il 23503 in una frase.
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    SELECT count(*) INTO v_cnt
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ordine_riga_id = OLD.id;

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
  END IF;

  -- ── 2b. Resi e riconsegne ───────────────────────────────
  -- FK in NO ACTION: stesso ragionamento del 2a. Sulla riga di DDT
  -- parla PRIMA del ritiro del legame.
  IF TG_TABLE_NAME = 'ordini_righe' THEN
    SELECT count(*) INTO v_cnt
      FROM vendite.resi_righe r
     WHERE r.ordine_riga_id = OLD.id;
  ELSE
    -- Solo i resi che hanno la riga come ORIGINE: il ponte di
    -- ri-consegna e' un legame che si ritira (D-7), qui sotto.
    SELECT count(*) INTO v_cnt
      FROM vendite.resi_righe r
     WHERE r.ddt_riga_id = OLD.id;
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

  -- ── 2a. I legami della riga di DDT: si ritirano ─────────
  -- (rev 2026-10-11, D-3, D-7). Il ritiro e' il building block
  -- vendite.fn_ddt_riga_ritira_legami (porta, DELETE dei due legami,
  -- riproiezione degli ordini), condiviso con l'annullo (D-8).
  IF TG_TABLE_NAME = 'ddt_righe' THEN
    PERFORM vendite.fn_ddt_riga_ritira_legami(OLD.id);
  END IF;

  -- ── 3. Si cancella ──────────────────────────────────────
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()
IS 'Sul DELETE di una riga di DDT o ordine con legami a valle. Riga d''ordine: fulfillment -> E_DELETE_BLOCKED_FUL, resi -> E_DELETE_RIGA_DOC_REFERENZIATA (il 23503 della FK diventa una frase). Riga di DDT: origine di un reso (vendite.resi_righe.ddt_riga_id) -> E_DELETE_RIGA_DOC_REFERENZIATA, PRIMA di tutto; poi, ⭐ dal 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-3, D-7), i legami con l''origine — fulfillment e ponte di ri-consegna — si RITIRANO con la riga: il ritiro e'' il building block vendite.fn_ddt_riga_ritira_legami (porta del guard del legame, DELETE dei legami, riproiezione degli ordini con vendite.fn_ordine_proietta_stato_evasione), condiviso con l''annullo della bolla (D-8). La riga arriva qui solo in bozza: il ramo «documento non piu'' in bozza» sta nel building block vendite.trgfn_doc_righe_lock_fuori_bozza, fascia _a05_, che parla prima (rev 2026-09-22); oppure per il cascade dalla testata, che si elimina solo in bozza (trgfn_doc_guard_delete_solo_bozza). ⛔ La FK fk_ordini_r_ful_v_ddt_riga resta ON DELETE RESTRICT di proposito: il ritiro e'' di questa madre, non di una cascata. Testata assente = cascade dalla testata: i legami a valle si controllano comunque, con l''etichetta che ripiega sul tipo di documento (script.fn_get_stato_testata_documento, SECURITY DEFINER). E_DELETE_NOT_ALLOWED resta solo sul ramo «tabella non prevista» (errore di montaggio). ⭐ rev 2026-10-19 (20261019-66, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
