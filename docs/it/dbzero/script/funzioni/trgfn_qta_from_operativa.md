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
  -- Parametri. Tipi nudi DICHIARATI: un interruttore del trigger e il NOME
  -- di una colonna, nessuna colonna di cui siano il riflesso.
  v_fill_factor_to_base boolean := false;
  v_fonte_col           text    := NULL;
  -- Il valore della fonte: la colonna fonte_quantita_attesa (gemella su
  -- offerte_commerciali_eccezioni, stesso tipo).
  v_fonte_val           vendite.contratti_righe.fonte_quantita_attesa%TYPE := NULL;

  -- Mapping/policy
  v_factor_map   catalogo.articoli_uom_operativa.factor_to_base%TYPE;
  v_qty_step     catalogo.articoli_uom_operativa.qty_step%TYPE;
  v_max_dec      catalogo.articoli_uom_operativa.max_decimals%TYPE;
  v_forbid_frac  catalogo.articoli_uom_operativa.forbid_fraction%TYPE;

  -- Fattore effettivo usato per i calcoli (rispetta snapshot se presente).
  -- numeric nudo DICHIARATO: arriva dal factor_to_base della riga, che su
  -- sei tabelle ha scale diverse (resi_righe e' numeric senza scala): un
  -- ancoraggio a numeric(18,6) lo arrotonderebbe in silenzio.
  v_factor_used  numeric := 1;

  BEGIN

  -- ------------------------------------------------------------
  -- script.trgfn_qta_from_operativa()
  -- Sorgente unica: UoM/quantità OPERATIVA.
  -- Su INSERT: calcola sempre quantita da qta_operativa.
  -- Su UPDATE: short-circuit se nessun input operativo è cambiato.
  --
  -- TG_ARGV (opzionali):
  --   [0] fill_factor_to_base :: boolean  (default FALSE)
  --       Se TRUE e NEW.factor_to_base è NULL, salva lo snapshot del fattore usato.
  --   [1] fonte_nullability_col :: text   (default NULL)
  --       Nome colonna della fonte della quantita' (fonte_quantita_attesa,
  --       su contratti_righe e offerte_commerciali_eccezioni), letta via
  --       to_jsonb(NEW). Con una fonte a valle (fn_fonte_porta_quantita =
  --       false) quantita := NULL, sempre. Con la fonte che la porta
  --       (FISSA) qta_operativa e' obbligatoria (E_QTA_MISSING).
  --
  -- rev 2026-08-04 (bonifica riferimenti morti, F5) — tolti due rami morti
  --   e i due parametri che li governavano:
  --     · [1] fill_uom_id_base -> scriveva NEW.uom_id. Nessuna delle sei
  --       tabelle agganciate ha una colonna `uom_id`, e tutti e sei i
  --       trigger passavano 'false': il ramo non era raggiungibile, e se
  --       lo si fosse acceso avrebbe fatto fallire ogni riga.
  --     · [2] target_col = 'quantita_fissa' -> `quantita_fissa` non
  --       esiste in **nessuna** tabella del database, e tutti e sei i
  --       trigger passavano 'quantita'. Un parametro con un solo valore
  --       lecito e' una bugia nella firma.
  --   Gli argomenti scalano: fonte_nullability_col era [3], ora e' [1].
  --   Precedente: 20260804-29 (stesso ragionamento su p_scope).
  -- ------------------------------------------------------------

  -- 0) Parametri. Letti PRIMA del short-circuit (rev 2026-10-08): la fonte
  --    serve anche su un UPDATE che non tocca gli input operativi.
  IF TG_NARGS >= 1 THEN
    v_fill_factor_to_base := lower(coalesce(TG_ARGV[0],'')) IN ('1','t','true','y','yes');
  END IF;
  IF TG_NARGS >= 2 AND TG_ARGV[1] IS NOT NULL AND TG_ARGV[1] <> '' THEN
    v_fonte_col := TG_ARGV[1];
    v_fonte_val := to_jsonb(NEW) ->> v_fonte_col;
  END IF;

  --------------------------------------------------------------------
  -- Fonte a valle: quantita e' calcolata, e qui vale NULL (rev 2026-10-08,
  -- brief-db-offerta-emissione-ed-erogazione §F.1, F-1.1).
  -- Con una fonte che non porta la quantita' (script.fn_fonte_porta_quantita:
  -- MANUALE, LETTURE, TIMESHEET) la quantita' arriva a valle: il DB porta
  -- quantita a NULL a ogni INSERT e a ogni UPDATE, anche quando gli input
  -- operativi non cambiano (un cambio di sola fonte con qta_operativa gia'
  -- vuota: il short-circuit qui sotto la lascerebbe). qta_operativa e'
  -- l'input: se e' valorizzata la rifiuta il guard
  -- trgfn_righe_guard_quantita_per_fonte, che gira prima di questo trigger.
  --------------------------------------------------------------------
  IF v_fonte_val IS NOT NULL
     AND NOT script.fn_fonte_porta_quantita(v_fonte_val) THEN
    NEW.quantita := NULL;
    RETURN NEW;
  END IF;

  --------------------------------------------------------------------
  -- short-circuit: solo su UPDATE dove nessun input operativo è cambiato.
  -- Su INSERT: calcola sempre (qta_operativa + uom → quantita).
  --------------------------------------------------------------------
  IF TG_OP = 'UPDATE'
     AND NEW.qta_operativa    IS NOT DISTINCT FROM OLD.qta_operativa
     AND NEW.uom_operativa_id IS NOT DISTINCT FROM OLD.uom_operativa_id
     AND NEW.factor_to_base   IS NOT DISTINCT FROM OLD.factor_to_base THEN
    RETURN NEW;
  END IF;

  -- Verifica qta_operativa: obbligatoria. Le fonti a valle sono gia' uscite
  -- sopra; qui arrivano la FISSA e le tabelle senza fonte.
  -- Rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.1, I-D1):
  -- tolta l'eccezione per DERIVATA_COMPONENTI, ritirata. Era la sola fonte
  -- che portava la quantita' senza che la scrivesse l'operatore, e nessuno
  -- la calcolava: i componenti seguono la quantita' del padre.
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
  -- 1) UoM operativa: se manca, fallback a UoM base articolo
  --------------------------------------------------------------------
  IF NEW.uom_operativa_id IS NULL THEN
    SELECT a.uom_id
      INTO NEW.uom_operativa_id
    FROM catalogo.articoli a
    WHERE a.id = NEW.articolo_id;
  END IF;

  IF NEW.uom_operativa_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'application','script.trgfn_qta_from_operativa',
      'E_UOM_MISSING',
      jsonb_build_object('campo', 'uom_operativa_id', 'articolo_id', NEW.articolo_id),
      NULL::uuid,
      'articolo_id', COALESCE(NEW.articolo_id::text, 'NULL')
    );
  END IF;

  --------------------------------------------------------------------
  -- 2) Mapping factor/policy
  --------------------------------------------------------------------
  SELECT aum.factor_to_base,
        aum.qty_step,
        COALESCE(aum.max_decimals,6),
        aum.forbid_fraction
    INTO v_factor_map, v_qty_step, v_max_dec, v_forbid_frac
  FROM catalogo.articoli_uom_operativa aum
  WHERE aum.articolo_id = NEW.articolo_id
    AND aum.uom_id      = NEW.uom_operativa_id
    AND aum.attivo      = TRUE
    AND (aum.valido_dal IS NULL OR aum.valido_dal <= (SELECT script.fn_data_operativa()))
    AND (aum.valido_al  IS NULL OR aum.valido_al  >= (SELECT script.fn_data_operativa()))
  LIMIT 1;

  v_factor_map := COALESCE(v_factor_map, 1);

  v_factor_used := COALESCE(NEW.factor_to_base, v_factor_map, 1);

  IF v_fill_factor_to_base THEN
    IF NEW.factor_to_base IS NULL THEN
      NEW.factor_to_base := v_factor_used;
    END IF;
  END IF;

  --------------------------------------------------------------------
  -- 3) Policy su quantità operativa
  --------------------------------------------------------------------
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
  -- 4) Calcolo finale della quantita' base
  --------------------------------------------------------------------
  NEW.quantita := ROUND(NEW.qta_operativa * v_factor_used, 6);

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_qta_from_operativa()
IS 'Calcola quantita (UoM base) da qta_operativa * fattore: quantita è una colonna CALCOLATA, la scrive solo questo trigger. TG_ARGV[0] = fill_factor_to_base (snapshot del fattore in factor_to_base se NULL); TG_ARGV[1] = colonna della fonte della quantità (fonte_quantita_attesa, su vendite.contratti_righe e vendite.offerte_commerciali_eccezioni). Con una fonte a valle (script.fn_fonte_porta_quantita = false: MANUALE, LETTURE, TIMESHEET) porta quantita a NULL a ogni INSERT e UPDATE, anche se gli input operativi non cambiano; qta_operativa valorizzata la rifiuta prima il guard script.trgfn_righe_guard_quantita_per_fonte. Con qta_operativa NULL: E_QTA_MISSING. Short-circuit su UPDATE senza variazioni agli input operativi; su INSERT calcola sempre. Rev 2026-05-27 (short-circuit), 2026-08-04 (rami morti), 2026-10-08 (fonte a valle: brief-db-offerta-emissione-ed-erogazione §F.1, F-1.1), 2026-10-21 (20261021-46, §I.1: ritirata DERIVATA_COMPONENTI, che era l''eccezione a E_QTA_MISSING).';
```

</div>

---
{% include-markdown "signature-core.md" %}
