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
  v_stato      text;
  v_etichetta  text;
  v_cnt        bigint := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Decidere se una riga di documento (DDT o ordine) si puo'
  --   cancellare. TRE esiti, e il terzo e' quello che fino al
  --   2026-08-26 non esisteva.
  --
  -- Regole, nell'ordine:
  --   1. il documento non e' piu' in bozza -> rifiuto;
  --   2. la riga ha legami a valle (fulfillment, resi,
  --      riconsegne)                       -> rifiuto;
  --   3. altrimenti                        -> si cancella.
  --
  -- ⚠️ L'ordine e' dominio, non stile: «il documento e' chiuso»
  --    e' l'identita' della situazione e va detto per primo.
  --    Dire «esiste un fulfillment» su un DDT gia' consegnato
  --    manderebbe a togliere il fulfillment, che non e' il
  --    rimedio.
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

  -- ── 1. Lo stato del documento ───────────────────────────
  -- ⛔ SECURITY DEFINER, e non e' un dettaglio: vendite.ddt e
  --    vendite.ordini hanno RLS, vendite.ddt_righe e
  --    vendite.ordini_righe no. Sotto RLS un chiamante fuori
  --    perimetro vedrebbe zero righe e questo guard leggerebbe
  --    «testata assente», cioe' passerebbe. Fail-open proprio
  --    per chi sta fuori.
  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, v_testata_id) AS t;

  -- ⚠️ Testata assente = CASCADE partito dalla testata (provato
  --    con tabelle temporanee il 2026-08-26). La regola di stato
  --    l'ha gia' applicata trgfn_doc_guard_delete_solo_bozza
  --    sulla testata: qui non si ricontrolla, si prosegue ai
  --    legami a valle, che valgono comunque.
  --    ⚠️ Non e' un buco: ddt_id e ordine_id sono NOT NULL con
  --    FK, quindi una riga orfana non esiste e «assente» non
  --    puo' voler dire altro.
  IF v_stato IS NOT NULL AND v_stato <> 'DRAFT' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_dlt_block_ordrig_ddtrig', 'E_DELETE_RIGA_DOC_NON_BOZZA',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'testata_id', v_testata_id,
                         'stato', v_stato),
      NULL::uuid,
      v_etichetta,
      v_stato);
  END IF;

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
  -- ⭐ Nessuna di queste tre tabelle ha RLS (verificato sul
  --    catalogo il 2026-08-26), quindi il conteggio e' un dato e
  --    non una fotografia del perimetro di chi chiama.
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

  -- ── 3. Il ramo che non esisteva ─────────────────────────
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()
IS 'Guard di cancellazione delle righe di documento (vendite.ddt_righe, vendite.ordini_righe). ⭐ Rev 2026-08-26: da DIVIETO ASSOLUTO a guard con TRE esiti. Fino a quella data ogni ramo sollevava e il RETURN OLD era irraggiungibile: nessun DELETE poteva riuscire, su nessuna delle due tabelle. ⛔ E il perimetro era doppio — le righe sono in ON DELETE CASCADE dalla loro testata, e un cascade fa scattare i trigger di riga: fallivano anche «elimina DDT» ed «elimina ordine» su qualunque documento con almeno una riga. Quattro verbi del backend, tutti scritti sull''assunzione opposta. ⭐ Che fosse un difetto e non una scelta lo dice il modello, non una preferenza: delle sette vendite.*_righe solo queste due avevano un divieto assoluto (preventivi_righe, resi_righe e contratti_righe non hanno guard; fatture_righe e listini_righe ne hanno uno condizionale); la protezione c''e'' gia'' nelle FK (ordini_righe_fulfillment in RESTRICT, resi_righe e resi_righe_riconsegne in NO ACTION, componenti e note in CASCADE perche'' devono morire con la riga); la tracciabilita'' la garantisce gia'' trg_*_z90_storico_upd_dlt; e accanto viveva un secondo ramo morto, trg_ordini_righe_z90_ricalcola_totali_dlt, che esiste per ricalcolare i totali dopo una cancellazione che non poteva avvenire. ⭐ ORDINE DEI RAMI, ed e'' dominio: (1) documento non in bozza -> E_DELETE_RIGA_DOC_NON_BOZZA; (2) legami a valle -> E_DELETE_BLOCKED_FUL (fulfillment) o E_DELETE_RIGA_DOC_REFERENZIATA (resi, riconsegne); (3) altrimenti si cancella. Lo stato viene per primo perche'' e'' l''identita'' della situazione: dire «esiste un fulfillment» su un DDT gia'' consegnato manderebbe a togliere il fulfillment, che non e'' il rimedio. ⭐ Il ramo 2 non e'' un presidio ma un TRADUTTORE: la FK bloccherebbe comunque, con un 23503 grezzo. ⭐ E_DELETE_NOT_ALLOWED resta solo sul ramo «tabella non prevista» (errore di montaggio), cosi'' il suo testo non va toccato e i tre guard che lo condividono restano intatti. ⚠️ Lo stato si legge da script.fn_get_stato_testata_documento, SECURITY DEFINER: le testate hanno RLS e le righe no, e una lettura invoker non distinguerebbe «non c''e''» da «non la vedo». ⚠️ Testata assente significa CASCADE dalla testata, e li'' la regola di stato l''ha gia'' applicata vendite.trgfn_doc_guard_delete_solo_bozza: i due guard sono una coppia, e togliendone uno l''altro diventa fail-open. Decisioni di Tid del 2026-08-26: la regola «solo bozza» scende nel DB, e i verbi di cancellazione devono funzionare.';
```

---
{% include-markdown "signature-core.md" %}
