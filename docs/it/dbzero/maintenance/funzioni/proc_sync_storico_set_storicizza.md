{% include-markdown "it/dbzero/maintenance/manual/proc_sync_storico_set_storicizza.md" %}
# ⚙️ Procedura `proc_sync_storico_set_storicizza`

```sql
CREATE PROCEDURE proc_sync_storico_set_storicizza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_sync_storico_set_storicizza()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    v_aggiunte integer := 0;
    v_potate   integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Tenere `config.storico_set_storicizza` allineato alla sua
    --   DERIVAZIONE: le tabelle ordinarie che hanno la colonna
    --   `storicizza` con DEFAULT true.
    --
    -- ⭐ Una sincronizzazione ha due meta'. Prima ne aveva una:
    --   aggiungeva e non toglieva mai, quindi una tabella ritirata
    --   lasciava una riga che puntava a niente — e il consumatore
    --   (apply_storicizza_weekly) ci moriva sopra, in silenzio.
    -- =========================================================

    -- ── 1. Aggiungi cio' che la derivazione produce ──────────
    -- ⚠️ Nome QUALIFICATO esplicitamente: `regclass::text` lo
    --   ometterebbe per gli schemi nel search_path del chiamante,
    --   e una chiave che dipende dal search_path e' una chiave che
    --   un giorno non ritrova la propria riga.
    INSERT INTO config.storico_set_storicizza (table_name, insert_manuale)
    SELECT n.nspname || '.' || c.relname, false
      FROM pg_attribute a
      JOIN pg_class c ON c.oid = a.attrelid AND c.relkind = 'r'
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
     WHERE a.attname = 'storicizza'
       AND NOT a.attisdropped
       -- Si confronta il TESTO dell'espressione, senza cast:
       -- forma invariata dalla versione precedente.
       AND pg_get_expr(ad.adbin, ad.adrelid) = 'true'
    ON CONFLICT (table_name) DO NOTHING;

    GET DIAGNOSTICS v_aggiunte = ROW_COUNT;

    -- ── 2. La meta' che mancava: pota cio' che non ha piu' un
    --      referente ─────────────────────────────────────────
    -- ⛔ SOLO le righe derivate, e SOLO quelle il cui nome non
    --   risolve piu' a nessun oggetto. Una tabella che esiste ma
    --   ha perso il DEFAULT non si pota: e' il caso transitorio
    --   che `apply_storicizza_weekly` ripara, e potarlo qui
    --   spegnerebbe la storicizzazione di una tabella viva.
    -- ⛔ `insert_manuale = true` non si tocca mai: e' una
    --   decisione di una persona, e se il suo bersaglio sparisce
    --   va detto a qualcuno, non cancellato di nascosto.
    DELETE FROM config.storico_set_storicizza s
     WHERE NOT s.insert_manuale
       AND to_regclass(s.table_name) IS NULL;

    GET DIAGNOSTICS v_potate = ROW_COUNT;

    -- ⚠️ Il riepilogo finisce nel log del server: chi chiama e' un
    --   job pgAgent e non ha dove leggere un valore di ritorno.
    RAISE NOTICE 'storico_set_storicizza: % aggiunte, % potate',
                 v_aggiunte, v_potate;
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_sync_storico_set_storicizza()
IS 'Tiene config.storico_set_storicizza allineato alla sua DERIVAZIONE (le tabelle ordinarie con la colonna `storicizza` a DEFAULT true): aggiunge cio'' che la derivazione produce e POTA le righe derivate che non hanno piu'' un referente. ⭐ La potatura e'' la meta'' che mancava (rev 2026-09-05, R-12): il set si popolava da solo e non si potava da solo, quindi ogni tabella ritirata lasciava una riga che puntava a niente — ed e'' cosi'' che apply_storicizza_weekly e'' morto ogni settimana per SEI MESI senza che nessuno lo sapesse. ⛔ Si pota SOLO il caso «il nome non risolve piu'' a nessun oggetto»: una tabella che esiste ma ha perso il DEFAULT NON si pota, perche'' e'' il caso transitorio che apply_storicizza_weekly ripara e le due meta'' si combatterebbero. ⛔ Le righe insert_manuale = true non si toccano mai: sono una decisione di una persona, e se il loro bersaglio sparisce va detto a qualcuno invece che cancellato di nascosto. ⚠️ Il nome si scrive schema-qualificato esplicitamente: regclass::text lo omette per gli schemi nel search_path del chiamante, e una chiave che dipende dal search_path un giorno non ritrova la propria riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
