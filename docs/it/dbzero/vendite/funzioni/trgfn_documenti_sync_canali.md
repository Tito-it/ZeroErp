{% include-markdown "it/dbzero/vendite/manual/trgfn_documenti_sync_canali.md" %}
# ⚙️ Funzione `trgfn_documenti_sync_canali`

```sql
CREATE FUNCTION trgfn_documenti_sync_canali()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_documenti_sync_canali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_source_code config.sorgenti.codice_interno%TYPE;
  v_prev_src_id config.sorgenti.id%TYPE;
  v_ord_src_id config.sorgenti.id%TYPE;
  v_ddt_src_id config.sorgenti.id%TYPE;
  v_ctr_src_id config.sorgenti.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Sincronizzare il registro canali fatturabili su eventi
  --   documento principali del dominio vendite.
  --
  -- Regole:
  --   - preventivi: apre canale PREVENTIVO su INSERT o cambio uid
  --   - ordini: apre canale ORDINE_VENDITA; se da PREVENTIVO,
  --     consuma canale PREVENTIVO
  --   - ddt: apre canale DDT_VENDITA; se da ORDINE_VENDITA,
  --     consuma canale ordine
  --   - contratti: apre canale DIRETTO su sorgente CONTRATTO
  --   Tutte le sorgenti aprono il proprio canale alla creazione
  --   per simmetria e completezza della storia documento.
  --
  -- rev 2026-08-04 (bonifica riferimenti morti, F5): tolto il ramo
  --   `TG_TABLE_NAME = 'ddt_ordini'` (safety net consumo ordine->ddt).
  --   `vendite.ddt_ordini` non esiste piu': era la sola lettrice di
  --   NEW.ordine_id / NEW.ddt_id, campi che nessuna delle quattro tabelle
  --   agganciate possiede. Con la tabella se n'e' andato anche il trigger,
  --   e il ramo era irraggiungibile. Il consumo ordine->ddt resta
  --   presidiato dal ramo `ddt` qui sotto.
  --
  -- NOTE codice_interno (rev 2026-06-28, analisi-hardcoded-codice §3a #13):
  --   le sorgenti sono risolte per codice_interno (immutabile), non per
  --   codice (mutabile). I canale_codice passati restano i medesimi
  --   literali (= codice_interno della sorgente). 'DIRETTO' = sentinel.
  -- =========================================================

  IF TG_TABLE_SCHEMA <> 'vendite' THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- Lookup unico per tutti i codici sorgente usati dalla funzione.
  SELECT
    max(CASE WHEN s.codice_interno = 'PREVENTIVO'      THEN s.id END),
    max(CASE WHEN s.codice_interno = 'ORDINE_VENDITA'  THEN s.id END),
    max(CASE WHEN s.codice_interno = 'DDT_VENDITA'     THEN s.id END),
    max(CASE WHEN s.codice_interno = 'CONTRATTO'       THEN s.id END)
  INTO
    v_prev_src_id,
    v_ord_src_id,
    v_ddt_src_id,
    v_ctr_src_id
  FROM config.sorgenti s
  WHERE s.attivo IS TRUE
    AND s.codice_interno IN ('PREVENTIVO', 'ORDINE_VENDITA', 'DDT_VENDITA', 'CONTRATTO');

  -- ---------------------------------------------------------
  -- PREVENTIVI
  -- ---------------------------------------------------------
  IF TG_TABLE_NAME = 'preventivi' THEN
    IF TG_OP = 'INSERT'
       OR (TG_OP = 'UPDATE' AND NEW.uid IS DISTINCT FROM OLD.uid) THEN
      IF v_prev_src_id IS NOT NULL THEN
        PERFORM vendite.fn_set_documento_canale_stato(
          p_sorgente_tipo_id => v_prev_src_id,
          p_sorgente_uid     => NEW.uid::text,
          p_canale_codice    => 'PREVENTIVO',
          p_stato_canale     => 'APERTO',
          p_meta             => jsonb_build_object('event', 'PREVENTIVO_UPSERT', 'table', TG_TABLE_NAME)
        );
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  -- ---------------------------------------------------------
  -- ORDINI
  -- ---------------------------------------------------------
  IF TG_TABLE_NAME = 'ordini' THEN
    IF TG_OP = 'INSERT'
       OR (TG_OP = 'UPDATE'
           AND (
             NEW.sorgente_tipo_id IS DISTINCT FROM OLD.sorgente_tipo_id
             OR NEW.sorgente_uid IS DISTINCT FROM OLD.sorgente_uid
           )) THEN

      IF v_ord_src_id IS NOT NULL THEN
        PERFORM vendite.fn_set_documento_canale_stato(
          p_sorgente_tipo_id => v_ord_src_id,
          p_sorgente_uid     => NEW.uid::text,
          p_canale_codice    => 'ORDINE_VENDITA',
          p_stato_canale     => 'APERTO',
          p_meta             => jsonb_build_object('event', 'ORDINI_UPSERT', 'table', TG_TABLE_NAME)
        );
      END IF;

      IF NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_uid IS NOT NULL THEN
        SELECT s.codice_interno INTO v_source_code
        FROM config.sorgenti s
        WHERE s.id = NEW.sorgente_tipo_id
        LIMIT 1;

        IF v_source_code = 'PREVENTIVO' THEN
          PERFORM vendite.fn_set_documento_canale_stato(
            p_sorgente_tipo_id     => NEW.sorgente_tipo_id,
            p_sorgente_uid         => NEW.sorgente_uid::text,
            p_canale_codice        => 'PREVENTIVO',
            p_stato_canale         => 'CONSUMATO',
            p_target_sorgente_tipo_id => v_ord_src_id,
            p_target_sorgente_uid  => NEW.uid::text,
            p_meta                 => jsonb_build_object('event', 'PREVENTIVO_TO_ORDINE', 'ordine_id', NEW.id)
          );
        END IF;
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  -- ---------------------------------------------------------
  -- DDT
  -- ---------------------------------------------------------
  IF TG_TABLE_NAME = 'ddt' THEN
    IF TG_OP = 'INSERT'
       OR (TG_OP = 'UPDATE'
           AND (
             NEW.sorgente_tipo_id IS DISTINCT FROM OLD.sorgente_tipo_id
             OR NEW.sorgente_uid IS DISTINCT FROM OLD.sorgente_uid
           )) THEN

      IF v_ddt_src_id IS NOT NULL THEN
        PERFORM vendite.fn_set_documento_canale_stato(
          p_sorgente_tipo_id => v_ddt_src_id,
          p_sorgente_uid     => NEW.uid::text,
          p_canale_codice    => 'DDT_VENDITA',
          p_stato_canale     => 'APERTO',
          p_meta             => jsonb_build_object('event', 'DDT_UPSERT', 'table', TG_TABLE_NAME)
        );
      END IF;

      IF NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_uid IS NOT NULL THEN
        SELECT s.codice_interno INTO v_source_code
        FROM config.sorgenti s
        WHERE s.id = NEW.sorgente_tipo_id
        LIMIT 1;

        IF v_source_code = 'ORDINE_VENDITA' THEN
          IF v_ord_src_id IS NOT NULL AND v_ddt_src_id IS NOT NULL THEN
            PERFORM vendite.fn_set_documento_canale_stato(
              p_sorgente_tipo_id     => v_ord_src_id,
              p_sorgente_uid         => NEW.sorgente_uid::text,
              p_canale_codice        => 'ORDINE_VENDITA',
              p_stato_canale         => 'CONSUMATO',
              p_target_sorgente_tipo_id => v_ddt_src_id,
              p_target_sorgente_uid  => NEW.uid::text,
              p_meta                 => jsonb_build_object('event', 'ORDINE_TO_DDT', 'ddt_id', NEW.id)
            );
          END IF;
        END IF;
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  -- ---------------------------------------------------------
  -- CONTRATTI
  -- ---------------------------------------------------------
  IF TG_TABLE_NAME = 'contratti' AND TG_OP = 'INSERT' THEN
    IF v_ctr_src_id IS NOT NULL THEN
      PERFORM vendite.fn_set_documento_canale_stato(
        p_sorgente_tipo_id => v_ctr_src_id,
        p_sorgente_uid     => NEW.uid::text,
        p_canale_codice    => 'DIRETTO',
        p_stato_canale     => 'APERTO',
        p_meta             => jsonb_build_object('event', 'CONTRATTO_UPSERT', 'contratto_id', NEW.id)
      );
    END IF;

    RETURN NEW;
  END IF;

  RETURN COALESCE(NEW, OLD);
END
$function$

COMMENT ON FUNCTION vendite.trgfn_documenti_sync_canali()
IS 'Sincronizza documenti_fatturazione_canali su eventi preventivi/ordini/ddt/ddt_ordini/contratti. Tutte le sorgenti aprono il proprio canale alla creazione per simmetria. Transizioni: PREVENTIVO->ORDINE, ORDINE->DDT. rev 2026-06-28: sorgenti risolte per codice_interno (analisi-hardcoded-codice §3a #13).';
```

</div>

---
{% include-markdown "signature-core.md" %}
