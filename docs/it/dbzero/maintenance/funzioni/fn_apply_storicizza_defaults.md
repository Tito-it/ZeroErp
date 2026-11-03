{% include-markdown "it/dbzero/maintenance/manual/fn_apply_storicizza_defaults.md" %}
# ⚙️ Funzione `fn_apply_storicizza_defaults`

```sql
CREATE FUNCTION fn_apply_storicizza_defaults()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_apply_storicizza_defaults()
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: rimettere DEFAULT true sulla colonna storicizza di ogni
--   tabella di config.storico_set_storicizza, una riga alla volta,
--   e RESTITUIRE il riepilogo: chi la lancia (il job, via
--   maintenance.fn_run_and_log) legge _falliti e sa se la corsa e'
--   riuscita a meta'. Brief: brief-db-revisione-maintenance D11.
--
-- ⭐ E' il consumatore di un insieme DERIVATO, popolato e potato da
--   maintenance.proc_sync_storico_set_storicizza, che gira prima.
--   Una riga stantia puo' comunque esserci (un sync fallito o
--   spento, una tabella ritirata fra le due corse, una riga
--   manuale): morirci sopra fermerebbe il lavoro per tutte le altre.
DECLARE
    rec               record;
    v_applicate       integer := 0;
    v_saltate         integer := 0;
    v_saltate_manuali integer := 0;
    v_falliti         integer := 0;
    v_dettaglio       jsonb   := '[]'::jsonb;
BEGIN
    -- Ordine stabile: due corse devono essere confrontabili.
    FOR rec IN
        SELECT s.table_name,
               s.insert_manuale,
               -- ⭐ Il nome si risolve UNA volta e non si smonta
               --   mai: `split_part` sul punto sbaglia su un nome
               --   con piu' punti o su un identificatore quotato.
               to_regclass(s.table_name) AS rel
          FROM config.storico_set_storicizza s
         ORDER BY s.table_name
    LOOP
        IF rec.rel IS NULL THEN
            -- Nessun referente: si salta e si dice, non si muore.
            -- ⚠️ I due casi hanno due rimedi opposti: una riga
            --   DERIVATA la togliera' il sync da sola; una MANUALE
            --   il sync non la tocca mai, e va guardata.
            v_saltate := v_saltate + 1;
            IF rec.insert_manuale THEN
                v_saltate_manuali := v_saltate_manuali + 1;
                RAISE WARNING
                    'storicizza: % e'' una riga MANUALE che non risolve a '
                    'nessun oggetto: una decisione che ha perso il suo '
                    'bersaglio, e il sync non la potera'' — va guardata da '
                    'una persona', rec.table_name;
            ELSE
                RAISE WARNING
                    'storicizza: % non risolve a nessun oggetto, riga '
                    'saltata (la potera'' il prossimo sync)', rec.table_name;
            END IF;
            v_dettaglio := v_dettaglio || jsonb_build_object(
                'tabella', rec.table_name,
                'esito',   CASE WHEN rec.insert_manuale
                                THEN 'SALTATA_MANUALE'
                                ELSE 'SALTATA_DERIVATA' END);
            CONTINUE;
        END IF;

        BEGIN
            EXECUTE format(
                'ALTER TABLE %s ALTER COLUMN storicizza SET DEFAULT true',
                rec.rel);
            v_applicate := v_applicate + 1;
        EXCEPTION WHEN OTHERS THEN
            -- ⭐ Isolamento per riga: un permesso mancante o una
            --   colonna che non c'e' piu' riguarda QUELLA tabella,
            --   non le altre cento. Ma si CONTA: e' cio' che rende
            --   rossa la corsa.
            v_falliti := v_falliti + 1;
            RAISE WARNING 'storicizza: % non applicata: %',
                          rec.table_name, SQLERRM;
            v_dettaglio := v_dettaglio || jsonb_build_object(
                'tabella', rec.table_name,
                'esito',   'FALLITA',
                'errore',  left(SQLERRM, 200),
                'sqlstate', SQLSTATE);
        END;
    END LOOP;

    RETURN jsonb_build_object(
        '_applicate',       v_applicate,
        '_saltate',         v_saltate,
        '_saltate_manuali', v_saltate_manuali,
        '_falliti',         v_falliti,
        '_dettaglio',       v_dettaglio);
END
$function$

COMMENT ON FUNCTION maintenance.fn_apply_storicizza_defaults()
IS 'Rimette DEFAULT true sulla colonna storicizza di ogni tabella di config.storico_set_storicizza, una riga alla volta in ordine di nome, e restituisce il riepilogo: _applicate, _saltate (righe che non risolvono a nessun oggetto), _saltate_manuali (quante di quelle sono manuali: decisioni che hanno perso il bersaglio), _falliti (DEFAULT che non si applicano), _dettaglio (le righe saltate o fallite, col motivo). Una riga che fallisce non ferma le altre e lascia un WARNING. Chiamata dal job via maintenance.fn_run_and_log, _falliti maggiore di zero rende la corsa rossa con E_JOB_ESITO_CON_SCARTI senza annullare le tabelle applicate. Il nome si risolve una volta con to_regclass e non si smonta mai.';
```

</div>

---
{% include-markdown "signature-core.md" %}
