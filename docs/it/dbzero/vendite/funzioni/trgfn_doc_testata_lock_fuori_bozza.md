# ⚙️ Funzione `trgfn_doc_testata_lock_fuori_bozza`

```sql
CREATE FUNCTION trgfn_doc_testata_lock_fuori_bozza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- TG_ARGV[0]: tipo documento per script.fn_get_stato_testata_documento
  v_documento    text;
  -- TG_ARGV[1]: codice_interno dello stato «bozza»
  v_stato_bozza  text;

  n_args         integer := COALESCE(array_length(TG_ARGV, 1), 0);
  i              integer;
  v_old          jsonb;
  v_new          jsonb;
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
  --   [2..] coppie (colonna, codice errore).
  -- Gemello di testata di vendite.trgfn_doc_righe_lock_fuori_bozza.
  -- ⛔ Stato letto dal lettore SECURITY DEFINER: le testate
  --    hanno RLS.
  -- =========================================================

  -- ── Argomenti: errore di MONTAGGIO, non di dato ───────────
  IF TG_OP <> 'UPDATE'
     OR n_args < 4
     OR (n_args - 2) % 2 <> 0
     OR NULLIF(TG_ARGV[0], '') IS NULL
     OR NULLIF(TG_ARGV[1], '') IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'evento',  TG_OP,
                         'tg_argv', TG_ARGV),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'attesi: BEFORE UPDATE con tipo documento, codice dello stato bozza, e coppie (colonna, codice errore)');
  END IF;

  v_documento   := TG_ARGV[0];
  v_stato_bozza := TG_ARGV[1];
  v_old         := to_jsonb(OLD);
  v_new         := to_jsonb(NEW);

  -- ── La prima colonna bloccata che cambia ─────────────────
  FOR i IN 2 .. n_args - 1 BY 2 LOOP
    -- Una colonna che la testata non ha e' un refuso del
    -- montaggio: il lock non scatterebbe mai, e nessuno se ne
    -- accorgerebbe.
    IF NOT (v_new ? TG_ARGV[i]) THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
        jsonb_build_object('trigger', TG_NAME,
                           'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                           'colonna', TG_ARGV[i]),
        NULL::uuid,
        TG_NAME::text,
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        format('la colonna %s non esiste sulla testata', TG_ARGV[i]));
    END IF;

    IF v_colonna IS NULL
       AND (v_old -> TG_ARGV[i]) IS DISTINCT FROM (v_new -> TG_ARGV[i]) THEN
      v_colonna := TG_ARGV[i];
      v_codice  := TG_ARGV[i + 1];
    END IF;
  END LOOP;

  -- Nessuna colonna bloccata cambia: niente da guardare.
  IF v_colonna IS NULL THEN
    RETURN NEW;
  END IF;

  -- ── Lo stato VECCHIO ─────────────────────────────────────
  -- Dentro il BEFORE ROW il lettore vede la versione che
  -- l'UPDATE sta sostituendo.
  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento(v_documento, (v_old ->> 'id')::bigint) AS t;

  IF v_stato IS DISTINCT FROM v_stato_bozza THEN
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
IS 'Building block (2026-10-09, brief-db-esecutivi-ba-coppia): una colonna della TESTATA di un documento si sceglie solo finche'' il documento e'' in bozza. BEFORE UPDATE FOR EACH ROW, TG_ARGV = [0] tipo documento per script.fn_get_stato_testata_documento, [1] codice_interno dello stato bozza, [2..] coppie (colonna, codice errore) come script.trgfn_lock_columns. Decide lo stato VECCHIO, letto dal lettore SECURITY DEFINER dentro il BEFORE ROW: l''UPDATE che esce dalla bozza scegliendo la colonna e'' legittimo. Si legge lo stato solo se una colonna bloccata cambia (confronto to_jsonb). Solleva il codice della PRIMA colonna che cambia, nell''ordine degli argomenti; VARIADIC: lo stato; nel contesto etichetta, colonna, valore_da, valore_a. Montaggio errato (evento diverso da UPDATE, argomenti spaiati, colonna che la testata non ha): E_DOC_RIGHE_LOCK_MONTAGGIO, come il gemello delle righe vendite.trgfn_doc_righe_lock_fuori_bozza. Si monta in fascia _a05_: l''immutabilita'' parla prima dei guard sul valore nuovo. Regola del 2: ritira vendite.trgfn_ddt_guard_causale_immutabile e il punto 1 di vendite.trgfn_ddt_guard_magazzino e di vendite.trgfn_resi_guard_magazzino. Adottanti: vendite.ddt (causale, cliente, magazzino), vendite.resi (magazzino).';
```

---
{% include-markdown "signature-core.md" %}
