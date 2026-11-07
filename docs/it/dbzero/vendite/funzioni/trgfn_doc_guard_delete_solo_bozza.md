{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_guard_delete_solo_bozza.md" %}
# ⚙️ Funzione `trgfn_doc_guard_delete_solo_bozza`

```sql
CREATE FUNCTION trgfn_doc_guard_delete_solo_bozza()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: v_documento e' un selettore (il codice
--   che script.fn_get_stato_testata_documento riconosce) senza una
--   colonna da ancorare; v_stato e v_etichetta sono POLIMORFI,
--   il codice_interno di quattro vocabolari diversi (e lo stato di
--   una mail) e una frase composta; v_ha_righe e' una risposta,
--   e v_successivi un CONTEGGIO: nessuno dei due e' il riflesso di
--   una colonna.
DECLARE
  v_documento  text;
  v_stato      text;
  v_etichetta  text;
  v_ha_righe   boolean;
  v_successivi bigint := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Un documento si cancella SOLO se e' una bozza vuota: in
  --   bozza (Tid, 2026-08-26) e senza righe attive (Tid,
  --   2026-11-06, giro T.4 di brief-db-sorgente-documento-e-
  --   riga). Montato su ordini, bolle, resi, contratti e sulla
  --   bozza email, che non ha righe.
  --
  -- ⭐ «Vuota» = nessuna riga ATTIVA, lo stesso predicato del BE
  --    (count_righe) e delle capability (senza_righe). Le righe
  --    disattivate seguono la testata nella cascata.
  -- ⭐ SECURITY DEFINER: la regola legge le righe, che hanno RLS,
  --    e la cascata che segue non passa dalla RLS. Come una FK,
  --    il guard vede anche cio' che il chiamante non vede.
  -- ⚠️ Lo stato e l'etichetta li da' il lettore condiviso: la
  --    testata c'e' ancora (BEFORE ROW), quindi risponde.
  -- =========================================================
  IF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'ddt' THEN
    v_documento := 'DDT_VENDITA';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.ddt_righe r
                            WHERE r.ddt_id = OLD.id AND r.attivo IS TRUE);

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'ordini' THEN
    v_documento := 'ORDINE_VENDITA';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.ordini_righe r
                            WHERE r.ordine_id = OLD.id AND r.attivo IS TRUE);

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'resi' THEN
    v_documento := 'RESO_VENDITA';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.resi_righe r
                            WHERE r.reso_id = OLD.id AND r.attivo IS TRUE);

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'contratti' THEN
    v_documento := 'CONTRATTO';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.contratti_righe r
                            WHERE r.contratto_id = OLD.id AND r.attivo IS TRUE);
    -- I contratti che dichiarano questo come precedente: lo stesso
    -- predicato della FK fk_contratti_parent (NO ACTION). Il
    -- riferimento a se stesso si esclude, come fa la FK, che lo
    -- controlla a riga gia' cancellata.
    SELECT count(*)
      INTO v_successivi
      FROM vendite.contratti c
     WHERE c.parent_contratto_id = OLD.id
       AND c.id <> OLD.id;

  ELSIF TG_TABLE_SCHEMA = 'config' AND TG_TABLE_NAME = 'email_outbox' THEN
    -- La bozza email non ha righe: vale la sola regola di stato.
    v_documento := 'EMAIL';
    v_ha_righe  := false;

  ELSE
    -- Errore di MONTAGGIO, non di dato.
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, 'id', OLD.id),
      NULL::uuid,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME);
  END IF;

  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, OLD.id) AS t;

  v_etichetta := COALESCE(v_etichetta, concat(v_documento, ' #', OLD.id::text));

  -- ⚠️ IS DISTINCT FROM e non <>: se il lettore non restituisse lo
  --    stato il guard RIFIUTA. Su un verbo distruttivo il default
  --    e' il no.
  IF v_stato IS DISTINCT FROM 'DRAFT' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DELETE_DOC_NON_BOZZA',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'stato', v_stato),
      NULL::uuid,
      v_etichetta,
      COALESCE(v_stato, '<sconosciuto>'));
  END IF;

  -- La seconda meta': la bozza dev'essere vuota. Lo stato si dice
  -- prima, perche' fuori bozza il rimedio e' un altro (annullare).
  IF v_ha_righe THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DELETE_DOC_CON_RIGHE',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento),
      NULL::uuid,
      v_etichetta);
  END IF;

  -- Il contratto precedente di altri contratti: la FK rifiuterebbe
  -- con un 23503; qui si dice perche', e quanti sono.
  IF v_successivi > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DELETE_CONTRATTO_CON_SUCCESSIVI',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'successivi', v_successivi),
      NULL::uuid,
      v_etichetta,
      v_successivi::text);
  END IF;

  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()
IS 'Un documento si cancella SOLO se e'' una bozza vuota: in bozza (stato DRAFT) e senza righe attive. Montato BEFORE DELETE FOR EACH ROW, fascia _a10_, su vendite.ordini, vendite.ddt, vendite.resi, vendite.contratti e config.email_outbox (la bozza email non ha righe: vale la sola regola di stato). La regola e'' di Tid (2026-08-26 la bozza; 2026-11-06 la bozza vuota e il contratto, brief-db-sorgente-documento-e-riga giro T.4); il BE la controlla prima, come controllo preventivo. ⭐ «Vuota» = nessuna riga attiva (attivo IS TRUE), lo stesso predicato del BE e delle capability (senza_righe): una bozza con sole righe disattivate si cancella, e quelle righe seguono la testata nella cascata. ⛔ E'' la meta'' di una coppia con i guard di riga (vendite.trgfn_doc_righe_lock_fuori_bozza, vendite.trgfn_dlt_block_ordrig_ddtrig): le righe sono in ON DELETE CASCADE dalla testata, e in un BEFORE DELETE di riga innescato dalla cascata la testata risulta gia'' cancellata, quindi il guard di riga passa. La regola della cancellazione sta qui, dove la cascata parte. ⭐ SECURITY DEFINER (search_path pg_catalog, pg_temp): legge le righe, che hanno RLS, e la cascata che segue non passa dalla RLS; come una FK, vede anche cio'' che il chiamante non vede. Lo stato e l''etichetta li da'' il lettore condiviso script.fn_get_stato_testata_documento. ⚠️ IS DISTINCT FROM ''DRAFT'': se il lettore non restituisse lo stato il guard rifiuta, su un verbo distruttivo il default e'' il no. Lo stato si controlla prima delle righe, perche'' i due rimedi sono diversi: fuori bozza si annulla (E_DELETE_DOC_NON_BOZZA), in bozza si tolgono le righe o si annulla (E_DELETE_DOC_CON_RIGHE). Il contratto che e'' il precedente di altri contratti (parent_contratto_id) non si cancella: lo rifiuta la FK fk_contratti_parent (NO ACTION dal 2026-11-07; prima SET NULL staccava i successori in silenzio), e il guard lo dice prima con E_DELETE_CONTRATTO_CON_SUCCESSIVI, con lo stesso predicato. Un montaggio su una tabella che la funzione non conosce e'' E_DOC_TIPO_NON_GESTITO. Fascia _a10_: i BEFORE ROW girano in ordine alfabetico, e il rifiuto precede trg_*_z90_storico_upd_dlt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
