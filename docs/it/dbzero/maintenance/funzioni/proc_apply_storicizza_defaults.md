{% include-markdown "it/dbzero/maintenance/manual/proc_apply_storicizza_defaults.md" %}
# ⚙️ Procedura `proc_apply_storicizza_defaults`

```sql
CREATE PROCEDURE proc_apply_storicizza_defaults()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_storicizza_defaults()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    rec         record;
    v_applicate integer := 0;
    v_saltate   integer := 0;
    v_fallite   integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rimettere `DEFAULT true` sulla colonna `storicizza` di
    --   ogni tabella del set. E' il consumatore di un insieme
    --   DERIVATO, popolato e potato da
    --   maintenance.proc_sync_storico_set_storicizza.
    --
    -- ⭐ I due girano su schedulazioni diverse: se l'apply arriva
    --   prima del sync, una riga stantia c'e'. Morirci sopra
    --   ferma il lavoro per tutte le altre — ed e' cosi' che
    --   questo job e' rimasto morto per sei mesi (R-12).
    -- =========================================================

    -- ⚠️ Ordine stabile: due corse devono essere confrontabili
    --   leggendo il log del server.
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
            -- Nessun referente: si salta e si dice — non si muore.
            -- ⚠️ Il messaggio distingue i due casi, perche' hanno
            --   due rimedi opposti: una riga DERIVATA la togliera'
            --   il sync da sola; una riga MANUALE il sync non la
            --   tocca mai, quindi promettere una potatura che non
            --   arrivera' sarebbe peggio di non dire niente.
            v_saltate := v_saltate + 1;
            IF rec.insert_manuale THEN
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
            CONTINUE;
        END IF;

        BEGIN
            EXECUTE format(
                'ALTER TABLE %s ALTER COLUMN storicizza SET DEFAULT true',
                rec.rel::regclass);
            v_applicate := v_applicate + 1;
        EXCEPTION WHEN OTHERS THEN
            -- ⭐ Isolamento per riga: un permesso mancante o una
            --   colonna che non c'e' piu' riguarda QUELLA tabella,
            --   non le altre cento.
            v_fallite := v_fallite + 1;
            RAISE WARNING 'storicizza: % non applicata: %',
                          rec.table_name, SQLERRM;
        END;
    END LOOP;

    RAISE NOTICE 'storicizza: % applicate, % saltate, % fallite',
                 v_applicate, v_saltate, v_fallite;
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_apply_storicizza_defaults()
IS 'Rimette DEFAULT true sulla colonna `storicizza` di ogni tabella di config.storico_set_storicizza. ⭐ Rev 2026-09-05 (R-12): salta le righe che non risolvono a nessun oggetto e ISOLA il fallimento di una riga dalle altre. Prima una sola riga stantia sollevava undefined_table e fermava il giro per tutte — ed e'' cosi'' che questo job e'' morto ogni settimana per SEI MESI senza che nessuno lo sapesse. ⛔ Non e'' una conseguenza delle tre righe morte trovate quel giorno: produttore (proc_sync_storico_set_storicizza) e consumatore girano su due job pgAgent con schedulazioni diverse, quindi una riga non ancora potata e'' una possibilita'' STRUTTURALE. ⚠️ Non «ingoia gli errori»: cambia il posto dove si raccontano — un WARNING nel log del server invece di un''eccezione che nessuno vede, e un''eccezione qui cancellava anche il proprio verbale (fn_run_and_log scrive la riga ok=false e poi rilancia: il RAISE fa rollback anche di quella). ⭐ Il nome della tabella si risolve una volta con to_regclass e non si smonta mai: split_part sul punto sbaglia su un nome con piu'' punti o su un identificatore quotato. ⚠️ Il WARNING distingue una riga derivata da una manuale: la prima la potera'' il sync, la seconda no — e'' una decisione che ha perso il suo bersaglio e va guardata da una persona.';
```

</div>

---
{% include-markdown "signature-core.md" %}
