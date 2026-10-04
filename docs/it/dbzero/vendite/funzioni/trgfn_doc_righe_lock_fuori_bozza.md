{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_righe_lock_fuori_bozza.md" %}
# ⚙️ Funzione `trgfn_doc_righe_lock_fuori_bozza`

```sql
CREATE FUNCTION trgfn_doc_righe_lock_fuori_bozza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- TG_ARGV[0]: tipo documento per script.fn_get_stato_testata_documento
  v_documento    text;
  -- TG_ARGV[1]: colonna della riga che porta l'id della testata
  v_fk_col       text;
  -- TG_ARGV[2] (opz.): codice_interno dello stato «bozza», default DRAFT
  v_stato_bozza  text;

  v_riga         jsonb;          -- la riga che sta cambiando (NEW, o OLD sul DELETE)
  v_testate      bigint[];       -- le testate coinvolte: una, due se la riga cambia padre
  v_testata_id   bigint;
  v_stato        text;
  v_etichetta    text;
  v_verbo        text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Le righe di un documento si aggiungono, modificano e
  --   tolgono SOLO finche' il documento e' in bozza. Fuori dalla
  --   bozza il contenuto non e' piu' una proposta ma un fatto
  --   (una spedizione, una merce instradata a fatturazione, un
  --   pricing attivo): le correzioni passano da documenti di
  --   rettifica, non da una riga che cambia.
  --
  -- Building block, montato per documento con tre argomenti:
  --   [0] tipo documento (DDT | ORDINE | CONTRATTO — decide il
  --       lettore script.fn_get_stato_testata_documento);
  --   [1] colonna FK della riga verso la testata;
  --   [2] (opz.) codice dello stato bozza, default 'DRAFT'.
  --
  -- ⛔ Lo stato si legge da un lettore SECURITY DEFINER: testate e
  --    righe hanno RLS, e un guard invoker non distinguerebbe
  --    «la testata non c'e'» da «non la vedo».
  -- ⚠️ Testata assente = cascade partito dalla testata (DELETE),
  --    o FK che parlera' (INSERT/UPDATE): il guard PASSA. La
  --    regola di stato sulla testata l'ha gia' applicata il guard
  --    di testata (trgfn_doc_guard_delete_solo_bozza), e ddt_id /
  --    ordine_id / contratto_id sono NOT NULL con FK: una riga
  --    orfana non esiste, quindi «assente» non puo' voler dire
  --    altro.
  -- ⭐ Fascia _a05_: il rifiuto di stato deve parlare PRIMA dei
  --    guard _a10_ sui legami (fulfillment, figli), o l'operatore
  --    legge un rimedio che non e' il rimedio.
  -- =========================================================

  -- ── Argomenti: errore di MONTAGGIO, non di dato ───────────
  IF COALESCE(array_length(TG_ARGV, 1), 0) < 2
     OR NULLIF(TG_ARGV[0], '') IS NULL
     OR NULLIF(TG_ARGV[1], '') IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'tg_argv', TG_ARGV),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'attesi: tipo documento, colonna FK della riga [, codice stato bozza]');
  END IF;

  v_documento   := TG_ARGV[0];
  v_fk_col      := TG_ARGV[1];
  v_stato_bozza := COALESCE(NULLIF(TG_ARGV[2], ''), 'DRAFT');

  -- ── La riga, letta una volta (niente SQL dinamico per riga) ─
  v_riga := CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;

  IF NOT (v_riga ? v_fk_col) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'fk_col',  v_fk_col),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      format('la colonna %s non esiste sulla riga', v_fk_col));
  END IF;

  -- ── Le testate da guardare ────────────────────────────────
  -- Su UPDATE anche quella di provenienza: spostare una riga da
  -- un documento emesso a una bozza e' comunque una modifica del
  -- documento emesso.
  v_testate := ARRAY[(v_riga ->> v_fk_col)::bigint];
  IF TG_OP = 'UPDATE'
     AND (to_jsonb(OLD) ->> v_fk_col) IS DISTINCT FROM (v_riga ->> v_fk_col) THEN
    v_testate := ARRAY[(to_jsonb(OLD) ->> v_fk_col)::bigint] || v_testate;
  END IF;

  v_verbo := CASE TG_OP
               WHEN 'INSERT' THEN 'aggiungere'
               WHEN 'UPDATE' THEN 'modificare'
               ELSE               'togliere'
             END;

  FOREACH v_testata_id IN ARRAY v_testate LOOP
    v_stato := NULL;
    v_etichetta := NULL;

    SELECT t.stato, t.etichetta
      INTO v_stato, v_etichetta
      FROM script.fn_get_stato_testata_documento(v_documento, v_testata_id) AS t;

    -- Assente: cascade dalla testata, o FK che parlera'. Si passa.
    CONTINUE WHEN v_stato IS NULL;

    IF v_stato <> v_stato_bozza THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME::text, 'E_RIGA_DOC_NON_BOZZA',
        jsonb_build_object('table',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                           'id',         v_riga ->> 'id',
                           'documento',  v_documento,
                           'testata_id', v_testata_id,
                           'stato',      v_stato,
                           'operazione', TG_OP),
        (v_riga ->> 'tx_id')::uuid,
        v_etichetta,
        v_stato,
        v_verbo);
    END IF;
  END LOOP;

  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza()
IS 'Building block (2026-09-22): le righe di un documento si aggiungono, modificano e tolgono SOLO finche'' il documento e'' in bozza. BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW, TG_ARGV = [0] tipo documento per script.fn_get_stato_testata_documento (DDT | ORDINE | CONTRATTO | OFFERTA | RESO), [1] colonna FK della riga verso la testata, [2] (opz.) codice_interno dello stato bozza, default DRAFT. Rifiuta con E_RIGA_DOC_NON_BOZZA (CONFLITTO_STATO; valori: etichetta, stato, verbo). ⛔ Lo stato si legge dal lettore SECURITY DEFINER perche'' testate e righe hanno RLS: un guard invoker non distinguerebbe «non c''e''» da «non la vedo». Testata assente = cascade dalla testata o FK che parlera'': passa. Su UPDATE guarda anche la testata di provenienza se la riga cambia padre. ⭐ Fascia _a05_: il rifiuto di stato parla PRIMA dei guard _a10_ sui legami (fulfillment, figli), o l''operatore legge un rimedio che non e'' il rimedio. Nasce da D7 di brief-db-partita-merce-per-documento (una riga di DDT gia'' instradata a fatturazione poteva essere disattivata) e ritira nello stesso giro le due copie che la regola aveva a DB: vendite.trgfn_contratti_righe_lock_post_attivazione (droppata) e il ramo 1 di vendite.trgfn_dlt_block_ordrig_ddtrig. Adottanti: vendite.ddt_righe (tre porte), vendite.ordini_righe (solo DELETE: INSERT/UPDATE restano aperti di proposito, data_consegna_confermata cambia dopo la conferma), vendite.contratti_righe (tre porte). Montaggio errato: E_DOC_RIGHE_LOCK_MONTAGGIO (TECNICO). rev 2026-09-29 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-h): quarto adottante, vendite.resi_righe (tre porte, tipo RESO, colonna reso_id): dal Lotto 3-bis la conferma del reso carica la merce, e una riga cambiata dopo farebbe divergere reso e registro. rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a): quinto adottante, vendite.offerte_commerciali_eccezioni (tre porte, tipo OFFERTA, colonna offerta_id, stato bozza BOZZA come terzo argomento): fn_push_offerta_a_contratto copia le righe 1:1 nel contratto, e la regola che il backend diceva da solo ora sta ai due capi.';
```

---
{% include-markdown "signature-core.md" %}
