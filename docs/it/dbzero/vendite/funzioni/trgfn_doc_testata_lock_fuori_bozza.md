{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_testata_lock_fuori_bozza.md" %}
# ⚙️ Funzione `trgfn_doc_testata_lock_fuori_bozza`

```sql
CREATE FUNCTION trgfn_doc_testata_lock_fuori_bozza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- La regola del montaggio, letta dalla grammatica condivisa
  -- (script.fn_doc_lock_regola): [0] tipo documento, [1] stato
  -- bozza, [2..] terne (colonna, codice errore, stati in cui resta aperta fuori bozza; vuoto = bloccata).
  v_regola       jsonb;
  v_documento    text;

  v_old          jsonb;
  v_new          jsonb;
  v_cambiate     text[];
  v_colonna      text;
  v_codice       text;
  v_stato        text;
  v_etichetta    text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Una colonna della testata si sceglie solo finche' il
  --   documento e' in bozza: fuori, e' stampata su un foglio
  --   consegnato o ha gia' prodotto un fatto (merce uscita o
  --   rientrata, un cliente a cui si fattura). Decide lo stato
  --   VECCHIO: l'UPDATE che esce dalla bozza scegliendo la
  --   colonna e' legittimo.
  --
  -- Building block, montato BEFORE UPDATE con:
  --   [0] tipo documento (lettore
  --       script.fn_get_stato_testata_documento);
  --   [1] codice_interno dello stato bozza;
  --   [2..] terne (colonna, codice errore, stati in cui resta aperta fuori bozza; vuoto = bloccata).
  -- Gemello di testata di vendite.trgfn_doc_righe_lock_fuori_bozza.
  -- ⭐ La grammatica degli argomenti e la decisione non stanno
  --    qui (rev 2026-10-10): script.fn_doc_lock_regola legge il
  --    montaggio, script.fn_doc_lock_colonna_bloccata decide. Le
  --    stesse due le usa il lettore del montaggio
  --    (script.fn_doc_lock_montaggi).
  -- ⛔ Stato letto dal lettore SECURITY DEFINER: le testate
  --    hanno RLS.
  -- =========================================================

  -- ── Argomenti ed evento: errore di MONTAGGIO, non di dato ─
  v_regola := script.fn_doc_lock_regola('TESTATA', TG_ARGV);

  IF TG_OP <> 'UPDATE' OR v_regola ->> 'errore' IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'evento',  TG_OP,
                         'tg_argv', TG_ARGV),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      COALESCE(v_regola ->> 'errore', 'si monta BEFORE UPDATE'));
  END IF;

  v_documento := v_regola ->> 'documento';
  v_old       := to_jsonb(OLD);
  v_new       := to_jsonb(NEW);

  -- Una colonna che la testata non ha e' un refuso del
  -- montaggio: il lock non scatterebbe mai, e nessuno se ne
  -- accorgerebbe.
  SELECT e ->> 'colonna'
    INTO v_colonna
    FROM jsonb_array_elements(v_regola -> 'colonne') AS e
   WHERE NOT (v_new ? (e ->> 'colonna'))
   LIMIT 1;

  IF v_colonna IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'colonna', v_colonna),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      format('la colonna %s non esiste sulla testata', v_colonna));
  END IF;

  -- ── Le colonne che cambiano ──────────────────────────────
  v_cambiate := ARRAY(SELECT n.key
                        FROM jsonb_each(v_new) AS n
                       WHERE n.value IS DISTINCT FROM (v_old -> n.key));

  -- Nessuna colonna nominata cambia: niente da guardare, e lo
  -- stato non si legge. Con lo stato NULL la decisione ferma
  -- ogni colonna nominata che cambia.
  IF script.fn_doc_lock_colonna_bloccata(v_regola, NULL, v_cambiate) IS NULL THEN
    RETURN NEW;
  END IF;

  -- ── Lo stato VECCHIO ─────────────────────────────────────
  -- Dentro il BEFORE ROW il lettore vede la versione che
  -- l'UPDATE sta sostituendo.
  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, (v_old ->> 'id')::bigint) AS t;

  -- La prima colonna, nell'ordine del montaggio, che in questo
  -- stato non si cambia. Decide la funzione che usa anche la
  -- capability.
  v_colonna := script.fn_doc_lock_colonna_bloccata(v_regola, v_stato, v_cambiate);

  IF v_colonna IS NOT NULL THEN
    SELECT e ->> 'codice'
      INTO v_codice
      FROM jsonb_array_elements(v_regola -> 'colonne') AS e
     WHERE e ->> 'colonna' = v_colonna
     LIMIT 1;

    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, v_codice,
      jsonb_build_object('table',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'id',         v_old ->> 'id',
                         'documento',  v_documento,
                         'etichetta',  v_etichetta,
                         'stato',      v_stato,
                         'colonna',    v_colonna,
                         'valore_da',  v_old -> v_colonna,
                         'valore_a',   v_new -> v_colonna),
      (v_new ->> 'tx_id')::uuid,
      COALESCE(v_stato, 'NULL'));
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza()
IS 'Building block (2026-10-09, brief-db-esecutivi-ba-coppia): una colonna della TESTATA di un documento si sceglie solo finche'' il documento e'' in bozza. BEFORE UPDATE FOR EACH ROW, TG_ARGV = [0] tipo documento per script.fn_get_stato_testata_documento, [1] codice_interno dello stato bozza, [2..] coppie (colonna, codice errore) come script.trgfn_lock_columns. Decide lo stato VECCHIO, letto dal lettore SECURITY DEFINER dentro il BEFORE ROW: l''UPDATE che esce dalla bozza scegliendo la colonna e'' legittimo. Si legge lo stato solo se una colonna bloccata cambia (confronto to_jsonb). Solleva il codice della PRIMA colonna che cambia, nell''ordine degli argomenti; VARIADIC: lo stato; nel contesto etichetta, colonna, valore_da, valore_a. Montaggio errato (evento diverso da UPDATE, argomenti spaiati, colonna che la testata non ha): E_DOC_RIGHE_LOCK_MONTAGGIO, come il gemello delle righe vendite.trgfn_doc_righe_lock_fuori_bozza. Si monta in fascia _a05_: l''immutabilita'' parla prima dei guard sul valore nuovo. Regola del 2: ritira vendite.trgfn_ddt_guard_causale_immutabile e il punto 1 di vendite.trgfn_ddt_guard_magazzino e di vendite.trgfn_resi_guard_magazzino. Adottanti: vendite.ddt (causale, cliente, magazzino), vendite.resi (magazzino). Dal 2026-10-09 (20261009-86…-92, brief-db-esecutivi-ba-coppia) anche l''emittente (emittente_fiscale_id, E_DOC_EMITTENTE_FUORI_BOZZA) su ddt, resi, ordini, offerte_commerciali, contratti e preventivi: adottanti vendite.ddt, vendite.resi, vendite.ordini, vendite.offerte_commerciali, vendite.contratti, vendite.preventivi. rev 2026-10-10 (brief-db-testata-dopo-emissione fase 1, R-1): la grammatica degli argomenti e la decisione escono dal corpo in due building block condivisi col lettore del montaggio. script.fn_doc_lock_regola legge TG_ARGV (le coppie diventano colonne con il loro codice e gli stati in cui restano aperte fuori bozza: per le coppie nessuno); script.fn_doc_lock_colonna_bloccata decide quale colonna nominata, fra quelle che cambiano, lo stato vecchio non lascia cambiare (la prima nell''ordine del montaggio). Se nessuna colonna nominata cambia lo stato non si legge (la decisione con lo stato NULL). Le stesse due le usa script.fn_doc_lock_montaggi: lock e capability leggono lo stesso montaggio con la stessa grammatica. La forma per stato della testata (D-8, fase 2) si aggiunge alla grammatica, e trigger e lettore la seguono insieme. Codici, contesto e valori invariati; la frase del montaggio sbagliato dice l''evento (si monta BEFORE UPDATE) o gli argomenti attesi. rev 2026-10-10 (fase 2): le coppie diventano terne (colonna, codice, stati in cui resta aperta fuori bozza); la colonna nominata si ferma se lo stato vecchio non e'' la bozza ne'' uno dei suoi stati. Famiglie del brief: identita'' (E_DOC_IDENTITA_FUORI_BOZZA), condizioni (E_DOC_CONDIZIONI_FUORI_BOZZA), cliente (E_DOC_CLIENTE_FUORI_BOZZA, e i codici di bolla e reso), sorgente (E_DOC_SORGENTE_FUORI_BOZZA), emittente, e le colonne aperte che si fermano a documento chiuso (E_DOC_CHIUSO). Sul contratto assorbe vendite.trgfn_contratti_lock_post_attivazione (ritirato). rev 2026-10-18 (brief-db-indirizzi-documento-seguono-il-cliente §8.7, B-4 ed E-3 di Tid): una terna puo'' dire ''-'' al posto degli stati, la colonna e'' ferma sempre, bozza compresa (script.fn_doc_lock_regola, script.fn_doc_lock_colonna_bloccata). Il corpo non cambia: lo stato si legge solo se una colonna nominata cambia, e con lo stato NULL la decisione ferma ogni colonna nominata che cambia, ferma sempre o no. Prime colonne ferme sempre: emittente_fiscale_id (E_DOC_EMITTENTE_IMMUTABILE) e utility_id (E_DOC_UTILITY_IMMUTABILE) di preventivo, offerta e contratto: in bozza si cambia il cliente, dentro la stessa utility e dello stesso emittente. VARIADIC: lo stato, come per le altre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
