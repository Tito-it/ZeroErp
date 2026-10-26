{% include-markdown "it/dbzero/script/manual/trgfn_guard_sorgente_polimorfa_tipizzata.md" %}
# ⚙️ Funzione `trgfn_guard_sorgente_polimorfa_tipizzata`

```sql
CREATE FUNCTION trgfn_guard_sorgente_polimorfa_tipizzata()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_area          text := TG_TABLE_SCHEMA;
  v_tbl           regclass;
  v_selector      text;
  v_exists        boolean;
  v_src_id        bigint;
  v_src_uid       uuid;
  v_target_id     text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Validare la sorgente polimorfa (sorgente_tipo_id) usando
  --   config.sorgenti, verificando la presenza del record target
  --   su tabella/chiave configurata (id oppure uid).
  --   MODELLO A (colonne tipizzate alternative): la chiave sta in
  --   NEW.sorgente_riga (BIGINT) per selector 'id' e in
  --   NEW.sorgente_uid (UUID) per selector 'uid'.
  --   Per le tabelle a chiave unica testuale (pratiche_sorgenti,
  --   commesse_sorgenti) usare la sorella _testuale.
  -- =========================================================
  -- Se non è valorizzata la sorgente, nessuna verifica
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
  -- Configurazione mancante o errata
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_tipizzata',
      'E_SORG_CONF',
      jsonb_build_object(
        'detail','Configurazione sorgente mancante/errata',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'target_table', COALESCE(v_tbl::text,'<NULL>'),
        'key_selector', COALESCE(v_selector,'<NULL>')
      ),
      NULL::uuid,
      concat( NEW.sorgente_tipo_id::text,
      ' target_table:', COALESCE(v_tbl::text,'<NULL>'),
       ' key_selector:', COALESCE(v_selector,'<NULL>'))
    );
  END IF;

  -- Selezione per tipo chiave
  IF v_selector = 'id' THEN
    v_src_id := NEW.sorgente_riga;
    IF v_src_id IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'script.trgfn_guard_sorgente_polimorfa_tipizzata',
        'E_SORG_KEY_MISSING',
        jsonb_build_object(
          'detail','Chiave sorgente mancante: atteso sorgente_riga (id)',
          'sorgente_tipo_id', NEW.sorgente_tipo_id,
          'key_selector', v_selector
        ),
        NULL::uuid,
        -- ⚠️ ARITA' (2026-08-18): concat() = un valore, E_SORG_KEY_MISSING ne
        --   chiede due -> 22023 al posto del P0001. Vale per entrambi i rami
        --   (id e uid) di questa funzione.
        NEW.sorgente_tipo_id::text, v_selector
      );
    END IF;

    EXECUTE format('SELECT true FROM %s WHERE id = $1', v_tbl::text)
      INTO v_exists
      USING v_src_id;

  ELSIF v_selector = 'uid' THEN
    v_src_uid := NEW.sorgente_uid;
    IF v_src_uid IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'script.trgfn_guard_sorgente_polimorfa_tipizzata',
        'E_SORG_KEY_MISSING',

        jsonb_build_object(
          'detail','Chiave sorgente mancante: atteso sorgente_uid (uuid)',
          'sorgente_tipo_id', NEW.sorgente_tipo_id,
          'key_selector', v_selector
        ),
        NULL::uuid,
        -- ⚠️ ARITA' (2026-08-18): secondo dei due rami, stesso difetto.
        NEW.sorgente_tipo_id::text, v_selector
      );
    END IF;

    EXECUTE format('SELECT true FROM %s WHERE uid = $1', v_tbl::text)
      INTO v_exists
      USING v_src_uid;

  ELSE
    -- Valore non consentito: la tabella config.sorgenti dovrebbe impedirlo con CHECK
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_tipizzata',
      'E_SORG_KEYSEL',

      jsonb_build_object(
        'detail','key_selector non supportato',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'key_selector', v_selector
      ),
      NULL::uuid,
      concat(NEW.sorgente_tipo_id::text , ' key_selector:', v_selector)
    );
  END IF;

  IF v_selector = 'id' THEN
    v_target_id := v_src_id::text;
  ELSE
    v_target_id := v_src_uid::text;
  END IF;

  IF NOT COALESCE(v_exists,false) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_sorgente_polimorfa_tipizzata',
      'E_SORG_NOT_FOUND',
      jsonb_build_object(
        'detail','Riferimento sorgente non trovato nella tabella target',
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'target_table', v_tbl::text,
        'key_selector', v_selector,
        'sorgente_riga', NEW.sorgente_riga,
        'sorgente_uid', NEW.sorgente_uid
      ),
      NULL::uuid,
      concat(NEW.sorgente_tipo_id::text ,
      ' target_table ', v_tbl::text,
        ' key_selector ', v_selector,
        ' sorgente_riga ', NEW.sorgente_riga,
        ' sorgente_uid ', NEW.sorgente_uid
      )
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()
IS 'Guard polimorfo MODELLO A (colonne tipizzate alternative): valida che la sorgente esista nella target_table di config.sorgenti leggendo NEW.sorgente_riga (BIGINT) per key_selector=id e NEW.sorgente_uid (UUID) per key_selector=uid. Ex trgfn_guard_sorgente_polimorfa (rinominata 2026-07-18, brief-db-guard-sorgente-polimorfa: nasce la sorella _testuale per il modello B a chiave unica testuale). NON agganciata ad alcuna tabella: il trigger su attivita_fatturabili fu rimosso con 20260225-45 (ridondante con FK commessa_attivita_id nel flusso commessa-only); riaggancio da ri-decidere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
