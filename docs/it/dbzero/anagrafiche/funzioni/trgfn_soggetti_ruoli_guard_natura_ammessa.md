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
-- Guard: la natura (macro-tipologia) del soggetto e' ammessa per il
-- ruolo che nasce, secondo la matrice config.tipi_ruoli_nature_ammesse.
-- «Matrice assente = libero»: senza righe per il tipo di ruolo, nessun
-- vincolo. Solo all'INSERT: il tipo del ruolo non si cambia (lucchetto
-- E_SOGGETTO_RUOLO_TIPO_IMMUTABILE), il soggetto nemmeno.
DECLARE
    v_tipo_soggetto_dettaglio_id  config.tipi_soggetto_dettaglio.id%TYPE;
    v_tipo_soggetto_id            config.tipi_soggetto.id%TYPE;
    v_ruolo                       config.tipi_ruoli.descrizione%TYPE;
    v_natura                      config.tipi_soggetto.descrizione%TYPE;
    v_today                       date := script.fn_data_operativa();  -- il giorno aziendale: nessuna colonna
BEGIN
    -- Caso A: nessuna matrice per il ruolo -> nature libere
    IF NOT EXISTS (
        SELECT 1
          FROM config.tipi_ruoli_nature_ammesse m
         WHERE m.tipo_ruolo_id = NEW.tipo_ruolo_id
    ) THEN
        RETURN NEW;
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_tipo_soggetto_dettaglio_id
      FROM anagrafiche.soggetti s
     WHERE s.id = NEW.soggetto_id;

    SELECT COALESCE(tr.descrizione, tr.codice_interno)
      INTO v_ruolo
      FROM config.tipi_ruoli tr
     WHERE tr.id = NEW.tipo_ruolo_id;

    -- Caso B: matrice definita, soggetto senza natura
    IF v_tipo_soggetto_dettaglio_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_ruoli_guard_natura_ammessa',
            'E_RUOLO_NATURA_TIPO_DET_NULL',
            jsonb_build_object(
                'campo',         'tipo_soggetto_dettaglio_id',
                'soggetto_id',   NEW.soggetto_id,
                'tipo_ruolo_id', NEW.tipo_ruolo_id),
            NEW.tx_id,
            v_ruolo);
    END IF;

    SELECT tsd.tipo_soggetto_id, COALESCE(ts.descrizione, ts.id)
      INTO v_tipo_soggetto_id, v_natura
      FROM config.tipi_soggetto_dettaglio tsd
      LEFT JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
     WHERE tsd.id = v_tipo_soggetto_dettaglio_id;

    -- Caso C: la natura e' ammessa, attiva e valida oggi
    IF NOT EXISTS (
        SELECT 1
          FROM config.tipi_ruoli_nature_ammesse m
         WHERE m.tipo_ruolo_id    = NEW.tipo_ruolo_id
           AND m.tipo_soggetto_id = v_tipo_soggetto_id
           AND m.attivo           = TRUE
           AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
           AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_ruoli_guard_natura_ammessa',
            'E_RUOLO_NATURA_NON_AMMESSA',
            jsonb_build_object(
                'campo',            'tipo_ruolo_id',
                'soggetto_id',      NEW.soggetto_id,
                'tipo_ruolo_id',    NEW.tipo_ruolo_id,
                'tipo_soggetto_id', v_tipo_soggetto_id),
            NEW.tx_id,
            v_ruolo,
            v_natura);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()
IS 'Guard di anagrafiche.soggetti_ruoli (BEFORE INSERT): la macro-tipologia del soggetto e'' ammessa per il ruolo che nasce, secondo config.tipi_ruoli_nature_ammesse (righe attive e valide alla data operativa); matrice assente per il ruolo = libero. Rifiuti: E_RUOLO_NATURA_NON_AMMESSA (campo tipo_ruolo_id) ed E_RUOLO_NATURA_TIPO_DET_NULL (soggetto senza natura, campo tipo_soggetto_dettaglio_id), con le descrizioni di ruolo e natura nella frase, senza id (S42). Solo all''INSERT dal 2026-11-24: il tipo del ruolo non si cambia (lucchetto E_SOGGETTO_RUOLO_TIPO_IMMUTABILE, D-T5-4 a) e il soggetto nemmeno (E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE). Una riga di matrice spenta non tocca i ruoli che esistono: la configurazione vale alla scrittura. Brief: brief-db-revisione-anagrafiche §20.';
```

</div>

---
{% include-markdown "signature-core.md" %}
