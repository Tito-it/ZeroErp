{% include-markdown "it/dbzero/script/manual/trgfn_guard_sorgente_polimorfa_testuale.md" %}
# ⚙️ Funzione `trgfn_guard_sorgente_polimorfa_testuale`

```sql
CREATE FUNCTION trgfn_guard_sorgente_polimorfa_testuale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- =========================================================
  -- Scopo:
  --   Validare la sorgente polimorfa delle tabelle di
  --   collegamento a chiave unica TESTUALE (MODELLO B:
  --   pratiche_sorgenti, commesse_sorgenti): NEW.sorgente_uid
  --   TEXT deve rispettare il formato dettato da
  --   config.sorgenti.key_selector (id::text per 'id', uuid
  --   testuale per 'uid') ed esistere nella target_table.
  --   NEW.sorgente_riga qui NON e' una chiave documento e non
  --   viene validata (grana di riga del link; D4 fase 2).
  -- =========================================================
  -- ⭐ rev 2026-10-05 (20261005-25): il formato si controlla sulla FORMA
  --   CANONICA della chiave, con i building block script.fn_sorgente_chiave_*
  --   — la stessa regola con cui la chiave si cerca (fn_stato_sorgente,
  --   vw_pratica_doc_sorgente). Prima: regex permissiva (maiuscole, zeri
  --   davanti) e controllo su btrim(NEW.sorgente_uid) mentre la riga salvava
  --   il valore NON ripulito. Passavano '007', ' 42 ', un uuid maiuscolo:
  --   chiavi che esistono ma che nessun lettore risolve mai.
  v_tbl       regclass;
  v_selector  text;
  v_uid       text;
  v_exists    boolean;
  v_chiave_id   script.vw_stato_sorgente.sorgente_chiave_id%TYPE;
  v_chiave_uuid script.vw_stato_sorgente.sorgente_chiave_uuid%TYPE;
BEGIN
  -- Se non e' valorizzata la sorgente, nessuna verifica
  IF NEW.sorgente_tipo_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Recupero configurazione sorgente attiva
  SELECT s.target_table, s.key_selector
    INTO v_tbl, v_selector
    FROM config.sorgenti s
   WHERE s.id = NEW.sorgente_tipo_id
     AND s.attivo = true;

  IF v_tbl IS NULL OR v_selector IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_testuale',
      'E_SORG_CONF',
      jsonb_build_object(
        'detail','Configurazione sorgente mancante/errata',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'target_table', COALESCE(v_tbl::text,'<NULL>'),
        'key_selector', COALESCE(v_selector,'<NULL>')
      ),
      NULL::uuid,
      concat(NEW.sorgente_tipo_id::text,
        ' target_table:', COALESCE(v_tbl::text,'<NULL>'),
        ' key_selector:', COALESCE(v_selector,'<NULL>'))
    );
  END IF;

  -- Chiave testuale obbligatoria
  v_uid := btrim(NEW.sorgente_uid);
  IF v_uid IS NULL OR v_uid = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_testuale',
      'E_SORG_KEY_MISSING',
      jsonb_build_object(
        'detail','Chiave sorgente mancante: atteso sorgente_uid (text)',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'key_selector', v_selector
      ),
      NULL::uuid,
      -- ⚠️ ARITA' (2026-08-18): il concat() componeva UN valore solo, ma
      --   E_SORG_KEY_MISSING ha due segnaposto -> format() alzava 22023.
      --   Gli altri tre punti di questa funzione passano un valore a messaggi
      --   con un segnaposto e stanno bene: era solo questo.
      NEW.sorgente_tipo_id::text, v_selector
    );
  END IF;

  -- Formato + esistenza secondo key_selector.
  -- ⚠️ Si controlla NEW.sorgente_uid, cioe' il valore che verra' SALVATO, non
  --   la sua copia ripulita: e' quello che i lettori confronteranno.
  IF v_selector = 'id' THEN
    v_chiave_id := script.fn_sorgente_chiave_id(NEW.sorgente_uid);
    IF v_chiave_id IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'script.trgfn_guard_sorgente_polimorfa_testuale',
        'E_SORG_FORMATO',
        jsonb_build_object(
          'detail','Atteso id numerico in forma canonica (id::text: niente zeri davanti, spazi, segno)',
          'sorgente_tipo_id', NEW.sorgente_tipo_id,
          'key_selector', v_selector,
          'sorgente_uid', NEW.sorgente_uid
        ),
        NULL::uuid,
        concat('atteso id::text, ricevuto «', NEW.sorgente_uid, '»')
      );
    END IF;

    EXECUTE format('SELECT true FROM %s WHERE id = $1', v_tbl::text)
      INTO v_exists
      USING v_chiave_id;

  ELSIF v_selector = 'uid' THEN
    v_chiave_uuid := script.fn_sorgente_chiave_uuid(NEW.sorgente_uid);
    IF v_chiave_uuid IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'script.trgfn_guard_sorgente_polimorfa_testuale',
        'E_SORG_FORMATO',
        jsonb_build_object(
          'detail','Atteso uuid testuale in forma canonica (uuid::text: minuscolo, con i trattini)',
          'sorgente_tipo_id', NEW.sorgente_tipo_id,
          'key_selector', v_selector,
          'sorgente_uid', NEW.sorgente_uid
        ),
        NULL::uuid,
        concat('atteso uuid, ricevuto «', NEW.sorgente_uid, '»')
      );
    END IF;

    EXECUTE format('SELECT true FROM %s WHERE uid = $1', v_tbl::text)
      INTO v_exists
      USING v_chiave_uuid;

  ELSE
    -- Valore non consentito: config.sorgenti dovrebbe impedirlo con CHECK
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_testuale',
      'E_SORG_KEYSEL',
      jsonb_build_object(
        'detail','key_selector non supportato',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'key_selector', v_selector
      ),
      NULL::uuid,
      concat(NEW.sorgente_tipo_id::text, ' key_selector:', v_selector)
    );
  END IF;

  IF NOT COALESCE(v_exists, false) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_testuale',
      'E_SORG_NOT_FOUND',
      jsonb_build_object(
        'detail','Riferimento sorgente non trovato nella tabella target',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'target_table', v_tbl::text,
        'key_selector', v_selector,
        'sorgente_uid', v_uid
      ),
      NULL::uuid,
      concat(NEW.sorgente_tipo_id::text,
        ' target_table ', v_tbl::text,
        ' key_selector ', v_selector,
        ' sorgente_uid ', v_uid)
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()
IS 'Guard polimorfo MODELLO B (tabelle di collegamento a chiave unica testuale: pratiche.pratiche_sorgenti, vendite.commesse_sorgenti): valida che NEW.sorgente_uid TEXT rispetti il formato dettato da config.sorgenti.key_selector (id::text per i tipi id, uuid testuale per i tipi uid — E_SORG_FORMATO) e che la riga esista nella target_table (E_SORG_NOT_FOUND). NON valida sorgente_riga (grana di riga del link, non chiave documento; D4 rinviata). Sorella di trgfn_guard_sorgente_polimorfa_tipizzata (modello A). Brief-db-guard-sorgente-polimorfa, 2026-07-18. ⭐ rev 2026-10-05 (20261005-25): il formato si controlla sulla FORMA CANONICA con i building block script.fn_sorgente_chiave_id / script.fn_sorgente_chiave_uuid — la stessa regola con cui la chiave si cerca (fn_stato_sorgente, vw_pratica_doc_sorgente) — e sul valore che verra'' SALVATO (NEW.sorgente_uid), non sulla sua copia ripulita. Prima: regex larghe su btrim(sorgente_uid), e la riga salvava il valore non ripulito; passavano ''007'', '' 42 '', un uuid maiuscolo, chiavi che esistono ma che nessun lettore ritrova. Ora E_SORG_FORMATO. La verifica di esistenza usa la chiave gia'' convertita.';
```

</div>

---
{% include-markdown "signature-core.md" %}
