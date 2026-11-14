{% include-markdown "it/dbzero/script/manual/fn_doc_lock_regola.md" %}
# ⚙️ Funzione `fn_doc_lock_regola`

```sql
CREATE FUNCTION fn_doc_lock_regola(p_building_block text, p_argomenti text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_lock_regola(p_building_block text, p_argomenti text[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
-- ⚠️ Tipi nudi DICHIARATI: p_building_block e' un selettore
--   (RIGHE | TESTATA) senza colonna di vocabolario; p_argomenti
--   sono gli argomenti di un trigger, text per costruzione.
DECLARE
  -- Gli argomenti contati da 1, qualunque sia il primo indice
  -- dell'array ricevuto (TG_ARGV parte da 0).
  a          text[];
  n          integer;
  v_ammesse  text[];
  v_stati    text[];
  v_colonne  jsonb := '[]'::jsonb;
  -- La bozza del documento: dalla sua testata (config.sorgenti) al
  -- vocabolario (script.fn_doc_stato_modello), allo stato iniziale.
  v_testata     config.sorgenti.target_table%TYPE;
  v_vocabolario regclass;  -- nudo: un vocabolario qualunque della mappa
  v_iniziale_id bigint;    -- nudo: l'id di uno stato di sei vocabolari
  v_bozza       text;      -- nudo: il codice_interno di sei vocabolari
BEGIN
  -- =========================================================
  -- Scopo:
  --   Dagli argomenti di un montaggio alla regola che dicono.
  --   E' la grammatica dei due building block «si tocca solo
  --   in bozza»: la leggono il trigger (da TG_ARGV) e il
  --   lettore del montaggio (da pg_trigger.tgargs), cosi' i due
  --   non possono capire gli argomenti in due modi.
  --   La decisione («questa colonna, in questo stato?») sta in
  --   script.fn_doc_lock_colonna_bloccata.
  -- ⭐ La bozza la dice il vocabolario del documento: stato_bozza e'
  --   il codice dello stato iniziale (colonna iniziale), non un
  --   argomento. L'argomento dello stato bozza resta nella grammatica,
  --   nella sua posizione, e non si legge: i montaggi non cambiano.
  -- =========================================================
  a := ARRAY(SELECT x
               FROM unnest(p_argomenti) WITH ORDINALITY AS u(x, k)
              ORDER BY k);
  n := COALESCE(cardinality(a), 0);

  -- Il primo argomento di tutti e due i building block e' il tipo
  -- documento. Un documento senza testata, senza vocabolario o senza
  -- stato iniziale lascia v_bozza NULL: e' un montaggio sbagliato.
  SELECT so.target_table
    INTO v_testata
    FROM config.sorgenti so
   WHERE so.codice_interno = NULLIF(a[1], '');
  IF v_testata IS NOT NULL THEN
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(v_testata) AS m;
  END IF;
  IF v_vocabolario IS NOT NULL THEN
    v_iniziale_id := script.fn_stato_iniziale_id(v_vocabolario);
    EXECUTE format('SELECT s.codice_interno::text FROM %s s WHERE s.id = $1', v_vocabolario)
       INTO v_bozza
      USING v_iniziale_id;
  END IF;

  IF p_building_block = 'RIGHE' THEN
    -- [0] tipo documento, [1] colonna FK verso il padre,
    -- [2] (opz., non letto: la bozza la dice il vocabolario),
    -- [3] (opz.) livello TESTATA | RIGA,
    -- [4] (opz.) colonne che un UPDATE cambia fuori bozza,
    -- [5] (opz., con [4]) gli stati in cui le cambia,
    -- [6] (opz.) il codice errore da sollevare, default
    --     E_RIGA_DOC_NON_BOZZA (rev 2026-10-11: i satelliti
    --     del documento, indirizzi e fornitura, montano il loro,
    --     D-12 di brief-db-testata-dopo-emissione).
    v_ammesse := ARRAY(SELECT btrim(x)
                         FROM unnest(string_to_array(COALESCE(a[5], ''), ',')) AS x
                        WHERE btrim(x) <> '');
    v_stati   := ARRAY(SELECT btrim(x)
                         FROM unnest(string_to_array(COALESCE(a[6], ''), ',')) AS x
                        WHERE btrim(x) <> '');

    RETURN jsonb_build_object(
      'building_block',   'RIGHE',
      'documento',        NULLIF(a[1], ''),
      'colonna_fk',       NULLIF(a[2], ''),
      'stato_bozza',      v_bozza,
      'livello',          COALESCE(NULLIF(a[4], ''), 'TESTATA'),
      'colonne_ammesse',  to_jsonb(v_ammesse),
      'stati_ammessi',    to_jsonb(v_stati),
      'codice',           COALESCE(NULLIF(btrim(a[7]), ''), 'E_RIGA_DOC_NON_BOZZA'),
      -- Le scrive l'audit, non chi modifica la riga: fuori dal
      -- confronto dell'eccezione.
      'colonne_tecniche', jsonb_build_array('data_update', 'user_update', 'tx_id'),
      'errore',
        CASE WHEN n < 2
               OR n > 7
               OR NULLIF(a[1], '') IS NULL
               OR NULLIF(a[2], '') IS NULL
               OR COALESCE(NULLIF(a[4], ''), 'TESTATA') NOT IN ('TESTATA', 'RIGA')
               -- [4] e [5] vanno insieme: colonne senza stati, o
               -- stati senza colonne, sono un montaggio a meta'.
               OR (cardinality(v_ammesse) = 0) <> (cardinality(v_stati) = 0)
             THEN 'attesi: tipo documento, colonna FK della riga [, codice stato bozza [, livello TESTATA | RIGA [, colonne ammesse fuori bozza, stati in cui sono ammesse [, codice errore]]]]'
             WHEN v_bozza IS NULL
             THEN format('il tipo documento %s non porta a uno stato iniziale: serve la testata in config.sorgenti, il vocabolario in script.fn_doc_stato_modello e uno stato con iniziale = true', COALESCE(NULLIF(a[1], ''), 'NULL'))
        END);
  END IF;

  IF p_building_block = 'TESTATA' THEN
    -- [0] tipo documento, [1] stato bozza (obbligatorio nella
    -- grammatica, non letto: la bozza la dice il vocabolario), [2..]
    -- terne (colonna,
    -- codice errore, stati in cui resta aperta fuori bozza). Stati
    -- vuoti: bloccata fuori bozza. Una lista (codice_interno separati
    -- da virgola): aperta solo in quegli stati, chiusa negli altri
    -- (D-8 e D-10, rev 2026-10-10). Le colonne che il montaggio non
    -- nomina sono libere: le scrive il database (totali, istantanee,
    -- date dei cambi di stato, lo stato stesso).
    -- rev 2026-10-18: '-' al posto degli stati = la colonna e' ferma
    -- sempre, anche in bozza (ferma_sempre): si sceglie alla nascita
    -- e non si cambia piu'. Il '-' sta da solo: mescolato a degli
    -- stati e' un montaggio sbagliato.
    IF n < 5
       OR (n - 2) % 3 <> 0
       OR NULLIF(a[1], '') IS NULL
       OR NULLIF(a[2], '') IS NULL
       OR EXISTS (SELECT 1
                    FROM generate_series(3, n, 3) AS g(k)
                   WHERE NULLIF(btrim(a[k]), '') IS NULL
                      OR NULLIF(btrim(a[k + 1]), '') IS NULL
                      OR (SELECT bool_or(btrim(x) = '-') AND count(*) > 1
                            FROM unnest(string_to_array(COALESCE(a[k + 2], ''), ',')) AS x
                           WHERE btrim(x) <> '')) THEN
      RETURN jsonb_build_object(
        'building_block', 'TESTATA',
        'documento',      NULLIF(a[1], ''),
        'stato_bozza',    v_bozza,
        'colonne',        '[]'::jsonb,
        'errore',         'attesi: tipo documento, codice dello stato bozza, e terne (colonna, codice errore, stati in cui resta aperta fuori bozza, vuoto, o - se e'' ferma anche in bozza)');
    END IF;

    IF v_bozza IS NULL THEN
      RETURN jsonb_build_object(
        'building_block', 'TESTATA',
        'documento',      a[1],
        'stato_bozza',    NULL,
        'colonne',        '[]'::jsonb,
        'errore',         format('il tipo documento %s non porta a uno stato iniziale: serve la testata in config.sorgenti, il vocabolario in script.fn_doc_stato_modello e uno stato con iniziale = true', a[1]));
    END IF;

    FOR i IN 3 .. n BY 3 LOOP
      v_stati := ARRAY(SELECT btrim(x)
                         FROM unnest(string_to_array(COALESCE(a[i + 2], ''), ',')) AS x
                        WHERE btrim(x) <> '');
      v_colonne := v_colonne || jsonb_build_array(jsonb_build_object(
        'colonna',       btrim(a[i]),
        'codice',        btrim(a[i + 1]),
        'ferma_sempre',  v_stati = ARRAY['-'],
        'stati_ammessi', CASE WHEN v_stati = ARRAY['-'] THEN '[]'::jsonb
                              ELSE to_jsonb(v_stati) END));
    END LOOP;

    RETURN jsonb_build_object(
      'building_block', 'TESTATA',
      'documento',      a[1],
      'stato_bozza',    v_bozza,
      'colonne',        v_colonne,
      'errore',         NULL);
  END IF;

  -- Un building block che la grammatica non conosce: nessuna
  -- regola da leggere, e chi la usa deve fermarsi.
  RETURN jsonb_build_object(
    'building_block', p_building_block,
    'errore',         format('building block sconosciuto: %s', COALESCE(p_building_block, 'NULL')));
END;
$function$

COMMENT ON FUNCTION script.fn_doc_lock_regola(p_building_block text, p_argomenti text[])
IS 'La grammatica dei montaggi dei due building block «si tocca solo in bozza»: dagli argomenti di un trigger (TG_ARGV, o pg_trigger.tgargs letto da dbops.fn_trigger_argomenti; qualunque primo indice) alla regola che dicono, in jsonb. stato_bozza e'' il codice dello stato iniziale del vocabolario del documento: dal tipo documento (primo argomento) alla testata (config.sorgenti.target_table), al vocabolario (script.fn_doc_stato_modello), allo stato con iniziale = true (script.fn_stato_iniziale_id). L''argomento dello stato bozza resta nella grammatica, nella sua posizione, e non si legge. p_building_block = RIGHE (vendite.trgfn_doc_righe_lock_fuori_bozza): documento, colonna_fk, stato_bozza, livello (default TESTATA), colonne_ammesse e stati_ammessi (argomenti [4] e [5], liste separate da virgola), codice (argomento [6], default E_RIGA_DOC_NON_BOZZA; i satelliti del documento, indirizzi e fornitura, montano un codice la cui frase non parla di righe), colonne_tecniche. TESTATA (vendite.trgfn_doc_testata_lock_fuori_bozza): documento, stato_bozza, colonne = [{colonna, codice, ferma_sempre, stati_ammessi}] dalle terne degli argomenti (colonna, codice, stati in cui resta aperta fuori bozza: vuoto = bloccata fuori bozza, ''-'' = ferma anche in bozza). errore: NULL, o la frase di un montaggio sbagliato (argomenti mancanti o in eccesso, una terna incompleta, un ''-'' mescolato a degli stati, un tipo documento che non porta a uno stato iniziale), che il chiamante solleva con E_DOC_RIGHE_LOCK_MONTAGGIO. La chiamano i due building block e il lettore script.fn_doc_lock_montaggi: trigger e capability non possono capire gli argomenti in due modi. La decisione per colonna e stato e'' script.fn_doc_lock_colonna_bloccata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
