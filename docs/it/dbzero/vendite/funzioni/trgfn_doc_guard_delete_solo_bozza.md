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
--   colonna da ancorare; v_stato, v_iniziale e v_etichetta sono
--   POLIMORFI, il codice_interno di sette vocabolari diversi (e lo
--   stato di una mail) e una frase composta; v_ha_righe e' una
--   risposta, e v_successivi un CONTEGGIO: nessuno dei due e' il
--   riflesso di una colonna.
DECLARE
  v_documento  text;
  v_stato      text;
  v_iniziale   text;
  v_etichetta  text;
  v_ha_righe   boolean;
  v_successivi bigint := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Un documento si cancella SOLO se e' una bozza vuota: nello
  --   stato iniziale del suo vocabolario (Tid, 2026-08-26; dal
  --   vocabolario dal 2026-11-08, Z2-a) e senza contenuto (Tid,
  --   2026-11-06, giro T.4; 2026-11-08, giro Z.2 di brief-db-
  --   sorgente-documento-e-riga). Montato su preventivi,
  --   offerte, contratti, ordini, bolle, resi, commesse e sulla
  --   bozza email, che non ha righe.
  --
  -- ⭐ «Vuota» = nessuna riga ATTIVA fra quelle che il catalogo
  --    dichiara (config.sorgenti.righe_table), lo stesso predicato
  --    del BE (count_righe) e delle capability (senza_righe). Le
  --    righe disattivate seguono la testata nella cascata. La
  --    commessa: nessuna attivita' (non hanno attivo) e nessun
  --    documento collegato.
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

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'preventivi' THEN
    v_documento := 'PREVENTIVO';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.preventivi_righe r
                            WHERE r.preventivo_id = OLD.id AND r.attivo IS TRUE);

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'offerte_commerciali' THEN
    -- L'offerta non ha righe proprie (il contenuto viene dal
    -- listino): le sue righe sono le eccezioni (Z2-b).
    v_documento := 'OFFERTA_COMMERCIALE';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.offerte_commerciali_eccezioni e
                            WHERE e.offerta_id = OLD.id AND e.attivo IS TRUE);

  ELSIF TG_TABLE_SCHEMA = 'vendite' AND TG_TABLE_NAME = 'commesse' THEN
    -- Le attivita' non hanno attivo: ognuna conta. Il documento
    -- collegato e' contenuto della commessa quanto un'attivita'
    -- (Z2-c). Le due FK (NO ACTION) rifiuterebbero con un 23503:
    -- qui si dice perche'. Le fatturabili presuppongono
    -- un'attivita'.
    v_documento := 'COMMESSA';
    v_ha_righe  := EXISTS (SELECT 1 FROM vendite.commesse_attivita a
                            WHERE a.commessa_id = OLD.id)
                OR EXISTS (SELECT 1 FROM vendite.commesse_sorgenti s
                            WHERE s.commessa_id = OLD.id);

  ELSIF TG_TABLE_SCHEMA = 'config' AND TG_TABLE_NAME = 'email_outbox' THEN
    -- La bozza email non ha righe: vale la sola regola di stato.
    -- Non ha un vocabolario (lo stato e' la colonna): la bozza e'
    -- DRAFT, scritta qui perche' non c'e' un'altra sede.
    v_documento := 'EMAIL';
    v_iniziale  := 'DRAFT';
    v_ha_righe  := false;

  ELSE
    -- Errore di MONTAGGIO, non di dato.
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, 'id', OLD.id),
      NULL::uuid,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME);
  END IF;

  -- Lo stato in cui la testata nasce, dal suo vocabolario (Z2-a).
  IF v_iniziale IS NULL THEN
    v_iniziale := script.fn_doc_stato_codice(
                    TG_RELID,
                    script.fn_doc_stato_iniziale_id(TG_RELID));
  END IF;

  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, OLD.id) AS t;

  v_etichetta := COALESCE(v_etichetta, concat(v_documento, ' #', OLD.id::text));

  -- ⚠️ IS DISTINCT FROM e non <>: se il lettore non restituisse lo
  --    stato, o il vocabolario non dichiarasse l'iniziale, il guard
  --    RIFIUTA. Su un verbo distruttivo il default e' il no.
  IF v_iniziale IS NULL OR v_stato IS DISTINCT FROM v_iniziale THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DELETE_DOC_NON_BOZZA',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'stato', v_stato,
                         'stato_iniziale', v_iniziale),
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
IS 'Un documento si cancella SOLO se e'' una bozza vuota: nello stato iniziale del suo vocabolario e senza contenuto. Montato BEFORE DELETE FOR EACH ROW, fascia _a10_, su vendite.preventivi, vendite.offerte_commerciali, vendite.contratti, vendite.ordini, vendite.ddt, vendite.resi, vendite.commesse e config.email_outbox (la bozza email non ha righe: vale la sola regola di stato). La regola e'' di Tid (2026-08-26 la bozza; 2026-11-06 la bozza vuota e il contratto, giro T.4; 2026-11-08 preventivo, offerta e commessa, giro Z.2 di brief-db-sorgente-documento-e-riga) e sta solo qui: il BE non la ripete (Tid, 2026-11-08). ⭐ Lo stato iniziale si legge dal vocabolario della testata (script.fn_doc_stato_iniziale_id, script.fn_doc_stato_codice su TG_RELID), non da un letterale: offerta e commessa nascono in BOZZA, le altre in DRAFT. La mail, che non ha un vocabolario, ha la bozza DRAFT nel suo ramo. ⭐ «Vuota» = nessuna riga attiva (attivo IS TRUE) fra quelle che il catalogo dichiara (config.sorgenti.righe_table), lo stesso predicato del BE e delle capability (senza_righe): per l''offerta le eccezioni, che sono le sue righe; per la commessa nessuna attivita'' (non hanno attivo) e nessun documento collegato (commesse_sorgenti), che le FK NO ACTION rifiuterebbero comunque con un 23503. Una bozza con sole righe disattivate si cancella, e quelle righe seguono la testata nella cascata. ⛔ E'' la meta'' di una coppia con i guard di riga (vendite.trgfn_doc_righe_lock_fuori_bozza, vendite.trgfn_dlt_block_ordrig_ddtrig): le righe sono in ON DELETE CASCADE dalla testata, e in un BEFORE DELETE di riga innescato dalla cascata la testata risulta gia'' cancellata, quindi il guard di riga passa. La regola della cancellazione sta qui, dove la cascata parte. ⭐ SECURITY DEFINER (search_path pg_catalog, pg_temp): legge le righe, che hanno RLS, e la cascata che segue non passa dalla RLS; come una FK, vede anche cio'' che il chiamante non vede. Lo stato e l''etichetta li da'' il lettore condiviso script.fn_get_stato_testata_documento. ⚠️ IS DISTINCT FROM: se il lettore non restituisse lo stato, o il vocabolario non dichiarasse l''iniziale, il guard rifiuta; su un verbo distruttivo il default e'' il no. Lo stato si controlla prima del contenuto, perche'' i due rimedi sono diversi: fuori bozza si annulla (E_DELETE_DOC_NON_BOZZA), in bozza si toglie il contenuto o si annulla (E_DELETE_DOC_CON_RIGHE, generico per tutti i documenti, Tid 2026-11-08). Il contratto che e'' il precedente di altri contratti (parent_contratto_id) non si cancella: lo rifiuta la FK fk_contratti_parent (NO ACTION dal 2026-11-07), e il guard lo dice prima con E_DELETE_CONTRATTO_CON_SUCCESSIVI, con lo stesso predicato. Un montaggio su una tabella che la funzione non conosce e'' E_DOC_TIPO_NON_GESTITO. Fascia _a10_: i BEFORE ROW girano in ordine alfabetico, e il rifiuto precede trg_*_z90_storico_upd_dlt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
