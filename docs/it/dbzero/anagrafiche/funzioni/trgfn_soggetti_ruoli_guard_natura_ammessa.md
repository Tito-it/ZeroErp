{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_guard_natura_ammessa.md" %}
# ⚙️ Funzione `trgfn_soggetti_ruoli_guard_natura_ammessa`

```sql
CREATE FUNCTION trgfn_soggetti_ruoli_guard_natura_ammessa()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard: verifica che la natura (tipo_soggetto) del soggetto sia ammessa
-- per il ruolo che si sta assegnando, secondo la matrice
-- config.tipi_ruoli_nature_ammesse.
-- Logica "matrice assente = libero": se non esistono righe per il
-- tipo_ruolo, nessun vincolo viene applicato.
DECLARE
    v_tipo_soggetto_dettaglio_id  config.tipi_soggetto_dettaglio.id%TYPE;
    v_tipo_soggetto_id            config.tipi_soggetto.id%TYPE;
    v_has_matrix                  boolean;
    v_today                       date := script.fn_data_operativa();
    v_error_ctx                   jsonb;
BEGIN
    -- DELETE: nessun controllo
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    -- Recupero tipo_soggetto_dettaglio_id dal soggetto
    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_tipo_soggetto_dettaglio_id
      FROM anagrafiche.soggetti s
     WHERE s.id = NEW.soggetto_id;

    -- Verifico se esiste almeno una riga di matrice per questo tipo_ruolo
    SELECT EXISTS (
        SELECT 1
          FROM config.tipi_ruoli_nature_ammesse m
         WHERE m.tipo_ruolo_id = NEW.tipo_ruolo_id
    ) INTO v_has_matrix;

    -- Caso A: nessuna matrice definita per il ruolo → nature libere
    IF NOT v_has_matrix THEN
        RETURN NEW;
    END IF;

    -- Caso B: matrice definita MA soggetto senza tipo_soggetto_dettaglio configurato
    IF v_tipo_soggetto_dettaglio_id IS NULL THEN
        v_error_ctx := jsonb_build_object(
            'soggetto_id', NEW.soggetto_id,
            'tipo_ruolo_id', NEW.tipo_ruolo_id
        );
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_ruoli_guard_natura_ammessa',
            'E_RUOLO_NATURA_TIPO_DET_NULL',
            v_error_ctx,
            NEW.tx_id,
            NEW.tipo_ruolo_id::text,
            NEW.soggetto_id::text
        );
    END IF;

    -- Risalgo a tipo_soggetto_id via tipi_soggetto_dettaglio
    SELECT tsd.tipo_soggetto_id
      INTO v_tipo_soggetto_id
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = v_tipo_soggetto_dettaglio_id;

    -- Caso C: matrice definita → verifico che la natura sia ammessa, attiva e valida
    IF NOT EXISTS (
        SELECT 1
          FROM config.tipi_ruoli_nature_ammesse m
         WHERE m.tipo_ruolo_id    = NEW.tipo_ruolo_id
           AND m.tipo_soggetto_id = v_tipo_soggetto_id
           AND m.attivo           = TRUE
           AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
           AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
    ) THEN
        v_error_ctx := jsonb_build_object(
            'soggetto_id', NEW.soggetto_id,
            'tipo_ruolo_id', NEW.tipo_ruolo_id,
            'tipo_soggetto_id', v_tipo_soggetto_id
        );
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_ruoli_guard_natura_ammessa',
            'E_RUOLO_NATURA_NON_AMMESSA',
            v_error_ctx,
            NEW.tx_id,
            v_tipo_soggetto_id::text,
            NEW.tipo_ruolo_id::text,
            NEW.soggetto_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()
IS 'Guard trigger: verifica che il tipo_soggetto (natura) del soggetto sia ammesso
per il ruolo che si sta assegnando, secondo la matrice config.tipi_ruoli_nature_ammesse.
Se la matrice non ha righe per il tipo_ruolo, nessun vincolo viene applicato (natura libera).
Segue lo stesso pattern di trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
