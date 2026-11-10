{% include-markdown "it/dbzero/script/manual/trgfn_qta_from_operativa.md" %}
# ⚙️ Funzione `trgfn_qta_from_operativa`

```sql
CREATE FUNCTION trgfn_qta_from_operativa()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_qta_from_operativa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- Parametri. Tipi nudi DICHIARATI: un interruttore del trigger e i NOMI di
  -- colonne e tabelle, nessuna colonna di cui siano il riflesso.
  v_fill_factor_to_base boolean := false;
  v_fonte_col           text    := NULL;
  -- Il valore della fonte: la colonna fonte_quantita_attesa (gemella su
  -- offerte_commerciali_eccezioni, stesso tipo).
  v_fonte_val           vendite.contratti_righe.fonte_quantita_attesa%TYPE := NULL;

  -- La data del documento, letta dalla testata.
  v_data_doc     date;

  -- Le regole della quantita' della mappatura alla data.
  v_qty_step     catalogo.articoli_uom_operativa.qty_step%TYPE;
  v_max_dec      catalogo.articoli_uom_operativa.max_decimals%TYPE;
  v_forbid_frac  catalogo.articoli_uom_operativa.forbid_fraction%TYPE;

  -- Il fattore usato. numeric nudo DICHIARATO: arriva dal factor_to_base della
  -- riga, che su sei tabelle ha scale diverse (resi_righe e' numeric senza
  -- scala), o dall'inversa di una conversione: un ancoraggio a numeric(18,6)
  -- lo arrotonderebbe in silenzio.
  v_factor_used  numeric;

  -- Per le frasi degli errori.
  v_art_codice   catalogo.articoli.codice%TYPE;
  v_uom_codice   catalogo.unita_misura.codice%TYPE;
  v_base_codice  catalogo.unita_misura.codice%TYPE;
BEGIN
  -- ------------------------------------------------------------
  -- script.trgfn_qta_from_operativa()
  -- quantita (unita' base) = qta_operativa x fattore. La scrive solo lui.
  --
  -- TG_ARGV:
  --   [0] fill_factor_to_base :: boolean (default FALSE): se la riga non ha
  --       il fattore, ci scrive quello usato (la fotografia).
  --   [1] la colonna della fonte della quantita' (fonte_quantita_attesa, su
  --       contratti_righe e offerte_commerciali_eccezioni), letta via
  --       to_jsonb(NEW); vuota sulle altre tabelle. Con una fonte a valle
  --       (script.fn_fonte_porta_quantita = false) quantita := NULL.
  --   [2] la tabella della testata (stesso schema della riga),
  --   [3] la colonna della riga che la punta,
  --   [4] la colonna data della testata: la data del documento, a cui si
  --       leggono il fattore e le regole della mappatura.
  -- ------------------------------------------------------------

  -- 0) Parametri. Letti PRIMA del short-circuit: la fonte serve anche su un
  --    UPDATE che non tocca gli input operativi.
  IF TG_NARGS >= 1 THEN
    v_fill_factor_to_base := lower(coalesce(TG_ARGV[0],'')) IN ('1','t','true','y','yes');
  END IF;
  IF TG_NARGS >= 2 AND TG_ARGV[1] IS NOT NULL AND TG_ARGV[1] <> '' THEN
    v_fonte_col := TG_ARGV[1];
    v_fonte_val := to_jsonb(NEW) ->> v_fonte_col;
  END IF;

  --------------------------------------------------------------------
  -- Fonte a valle: quantita e' calcolata, e qui vale NULL.
  -- Con una fonte che non porta la quantita' (script.fn_fonte_porta_quantita:
  -- MANUALE, LETTURE, TIMESHEET) la quantita' arriva a valle: il DB porta
  -- quantita a NULL a ogni INSERT e a ogni UPDATE, anche quando gli input
  -- operativi non cambiano. qta_operativa valorizzata la rifiuta il guard
  -- trgfn_righe_guard_quantita_per_fonte, che gira prima di questo trigger.
  --------------------------------------------------------------------
  IF v_fonte_val IS NOT NULL
     AND NOT script.fn_fonte_porta_quantita(v_fonte_val) THEN
    NEW.quantita := NULL;
    RETURN NEW;
  END IF;

  --------------------------------------------------------------------
  -- short-circuit: solo su UPDATE dove nessun input operativo e' cambiato.
  --------------------------------------------------------------------
  IF TG_OP = 'UPDATE'
     AND NEW.qta_operativa    IS NOT DISTINCT FROM OLD.qta_operativa
     AND NEW.uom_operativa_id IS NOT DISTINCT FROM OLD.uom_operativa_id
     AND NEW.factor_to_base   IS NOT DISTINCT FROM OLD.factor_to_base THEN
    RETURN NEW;
  END IF;

  -- Verifica qta_operativa: obbligatoria. Le fonti a valle sono gia' uscite
  -- sopra; qui arrivano la FISSA e le tabelle senza fonte.
  IF NEW.qta_operativa IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'application',
      'script.trgfn_qta_from_operativa',
      'E_QTA_MISSING',
      jsonb_build_object(
        'campo', 'qta_operativa',
        'schema', TG_TABLE_SCHEMA,
        'table',  TG_TABLE_NAME,
        'qualified_table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'articolo_id', NEW.articolo_id,
        'uom_operativa_id', NEW.uom_operativa_id
      ),
      NULL::uuid,
      'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'column', 'qta_operativa'
    );
  END IF;

  --------------------------------------------------------------------
  -- 1) Unita' operativa: se manca, l'unita' base dell'articolo.
  --    articolo_id e catalogo.articoli.uom_id sono NOT NULL: c'e' sempre.
  --------------------------------------------------------------------
  IF NEW.uom_operativa_id IS NULL THEN
    NEW.uom_operativa_id := catalogo.fn_get_uom_base(NEW.articolo_id);
  END IF;

  --------------------------------------------------------------------
  -- 2) La data del documento, dalla testata (argomenti [2]-[4]).
  --------------------------------------------------------------------
  IF TG_NARGS < 5
     OR coalesce(TG_ARGV[2], '') = ''
     OR coalesce(TG_ARGV[3], '') = ''
     OR coalesce(TG_ARGV[4], '') = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.trgfn_qta_from_operativa',
      'E_SCRIPT_CHIAMATA_NON_VALIDA',
      jsonb_build_object('tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, 'trigger', TG_NAME),
      NULL::uuid,
      'script.trgfn_qta_from_operativa',
      'montaggio senza la testata e la sua data (argomenti 3-5)');
  END IF;

  EXECUTE format('SELECT t.%I FROM %I.%I t WHERE t.id = $1',
                 TG_ARGV[4], TG_TABLE_SCHEMA, TG_ARGV[2])
     INTO v_data_doc
    USING (to_jsonb(NEW) ->> TG_ARGV[3])::bigint;

  -- La data e' NOT NULL su tutte le testate: se manca, la testata non c'e' o
  -- chi scrive non la vede. Qui non si decide niente: parlano la FK o la RLS,
  -- che girano dopo questo trigger. Un errore sul fattore sarebbe falso.
  IF v_data_doc IS NULL THEN
    RETURN NEW;
  END IF;

  --------------------------------------------------------------------
  -- 3) Il fattore.
  --    Un UPDATE che cambia l'unita' e non il fattore: il fattore di prima
  --    era dell'altra unita', e non vale piu'.
  --    Il fattore scritto sulla riga e' la fotografia (anche quella copiata
  --    da un documento sorgente) e si rispetta; altrimenti
  --    catalogo.fn_get_uom_factor alla data del documento, e senza fattore
  --    la riga si rifiuta: una quantita' base inventata e' peggio di nessuna.
  --------------------------------------------------------------------
  IF TG_OP = 'UPDATE'
     AND NEW.uom_operativa_id IS DISTINCT FROM OLD.uom_operativa_id
     AND NEW.factor_to_base   IS NOT DISTINCT FROM OLD.factor_to_base THEN
    NEW.factor_to_base := NULL;
  END IF;

  v_factor_used := COALESCE(
      NEW.factor_to_base,
      catalogo.fn_get_uom_factor(NEW.articolo_id, NEW.uom_operativa_id, v_data_doc));

  IF v_factor_used IS NULL THEN
    SELECT a.codice, ub.codice INTO v_art_codice, v_base_codice
      FROM catalogo.articoli a
      LEFT JOIN catalogo.unita_misura ub ON ub.id = a.uom_id
     WHERE a.id = NEW.articolo_id;
    SELECT u.codice INTO v_uom_codice
      FROM catalogo.unita_misura u
     WHERE u.id = NEW.uom_operativa_id;
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.trgfn_qta_from_operativa',
      'E_UOM_MISSING',
      jsonb_build_object(
        'campo', 'uom_operativa_id',
        'articolo_id', NEW.articolo_id,
        'uom_operativa_id', NEW.uom_operativa_id,
        'data_documento', v_data_doc,
        'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
      NULL::uuid,
      COALESCE(v_uom_codice, '—'), COALESCE(v_base_codice, '—'),
      COALESCE(v_art_codice, '—'), COALESCE(to_char(v_data_doc, 'DD/MM/YYYY'), '—'));
  END IF;

  IF v_fill_factor_to_base AND NEW.factor_to_base IS NULL THEN
    NEW.factor_to_base := v_factor_used;
  END IF;

  --------------------------------------------------------------------
  -- 4) Le regole della quantita': quelle della mappatura alla data.
  --    Un'unita' senza mappatura (convertita dalle conversioni generali)
  --    non ne ha.
  --------------------------------------------------------------------
  SELECT m.qty_step, m.max_decimals, m.forbid_fraction
    INTO v_qty_step, v_max_dec, v_forbid_frac
    FROM catalogo.fn_uom_operativa_alla_data(NEW.articolo_id, NEW.uom_operativa_id, v_data_doc) m;

  IF v_forbid_frac IS TRUE AND NEW.qta_operativa <> TRUNC(NEW.qta_operativa) THEN
    PERFORM script.fn_log_and_raise_error(
      'database','script.trgfn_qta_from_operativa',
      'E_QTA_OPERATIVA_NON_INTERA',
      jsonb_build_object(
        'campo', 'qta_operativa',
        'articolo_id', NEW.articolo_id,
        'uom_operativa_id', NEW.uom_operativa_id,
        'qta_operativa', NEW.qta_operativa
      ),
      NULL::uuid,
      'articolo_id', NEW.articolo_id::text,
      'uom_operativa_id', NEW.uom_operativa_id::text
    );
  END IF;

  -- I decimali che contano: trim_scale toglie gli zeri in coda (2,50 ha un
  -- decimale, non due).
  IF v_max_dec IS NOT NULL AND scale(trim_scale(NEW.qta_operativa)) > v_max_dec THEN
    SELECT a.codice INTO v_art_codice FROM catalogo.articoli a WHERE a.id = NEW.articolo_id;
    SELECT u.codice INTO v_uom_codice FROM catalogo.unita_misura u WHERE u.id = NEW.uom_operativa_id;
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.trgfn_qta_from_operativa',
      'E_QTA_OPERATIVA_DECIMALI',
      jsonb_build_object(
        'campo', 'qta_operativa',
        'articolo_id', NEW.articolo_id,
        'uom_operativa_id', NEW.uom_operativa_id,
        'qta_operativa', NEW.qta_operativa,
        'max_decimals', v_max_dec),
      NULL::uuid,
      NEW.qta_operativa::text, COALESCE(v_uom_codice, '—'),
      COALESCE(v_art_codice, '—'), v_max_dec::text);
  END IF;

  IF v_qty_step IS NOT NULL AND v_qty_step > 0 THEN
    IF abs(NEW.qta_operativa / v_qty_step - ROUND(NEW.qta_operativa / v_qty_step)) > 1e-9 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','script.trgfn_qta_from_operativa',
        'E_QTA_OPER_STEP_INVALIDO',
        jsonb_build_object(
          'campo', 'qta_operativa',
          'articolo_id', NEW.articolo_id,
          'uom_operativa_id', NEW.uom_operativa_id,
          'qta_operativa', NEW.qta_operativa,
          'qty_step', v_qty_step
        ),
        NULL::uuid,
        'articolo_id',NEW.articolo_id::text,
        'uom_operativa_id',NEW.uom_operativa_id::text
      );
    END IF;
  END IF;

  --------------------------------------------------------------------
  -- 5) La quantita' base.
  --------------------------------------------------------------------
  NEW.quantita := ROUND(NEW.qta_operativa * v_factor_used, 6);

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_qta_from_operativa()
IS 'Calcola quantita (unita'' base) da qta_operativa per il fattore: quantita e'' una colonna calcolata, la scrive solo questo trigger. Il fattore e'' quello scritto sulla riga (factor_to_base: la fotografia, anche quella copiata da un documento sorgente), altrimenti catalogo.fn_get_uom_factor alla data del documento; senza fattore la riga e'' rifiutata (E_UOM_MISSING). Se un UPDATE cambia l''unita'' e non il fattore, il fattore si rilegge. Le regole della quantita'' della mappatura alla data (catalogo.fn_uom_operativa_alla_data): intera (E_QTA_OPERATIVA_NON_INTERA), al massimo max_decimals decimali (E_QTA_OPERATIVA_DECIMALI), a passi di qty_step (E_QTA_OPER_STEP_INVALIDO). Unita'' operativa NULL = l''unita'' base dell''articolo. Con qta_operativa NULL: E_QTA_MISSING. TG_ARGV: [0] fill_factor_to_base (scrive il fattore usato se la riga non l''ha); [1] la colonna della fonte della quantita'' (vuota se la tabella non ce l''ha): con una fonte a valle (script.fn_fonte_porta_quantita = false) quantita vale NULL; [2] la tabella della testata, [3] la colonna della riga che la punta, [4] la colonna data della testata (la data del documento). Senza [2]-[4]: E_SCRIPT_CHIAMATA_NON_VALIDA. Se la testata non si vede (o non c''e'') non calcola niente: parlano la RLS o la FK. Su UPDATE non fa niente se qta_operativa, unita'' e fattore non cambiano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
