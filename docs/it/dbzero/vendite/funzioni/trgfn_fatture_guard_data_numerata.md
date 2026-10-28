{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_data_numerata.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_data_numerata`

```sql
CREATE FUNCTION trgfn_fatture_guard_data_numerata()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_data_numerata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da quando una fattura ha un numero fiscale, la sua data
    --   non si tocca piu'.
    --
    -- Regola:
    --   il discriminante e' OLD.numero, NON lo stato: la fattura
    --   viene numerata mentre e' in EMESSA, e una soglia per
    --   stato lascerebbe una finestra scrivibile su un documento
    --   gia' numerato.
    -- =========================================================

    -- ⚠️ IS DISTINCT FROM e non `<>`: la data e' NOT NULL oggi, ma
    --    un confronto che non regge il NULL e' un difetto che
    --    aspetta solo un ALTER COLUMN.
    IF OLD.numero IS NOT NULL
       AND NEW.data IS DISTINCT FROM OLD.data THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text,
            'E_FATTURA_DATA_NON_MODIFICABILE',
            jsonb_build_object(
                'fattura_id',   OLD.id,
                'numero',       OLD.numero,
                'anno',         OLD.anno,
                'serie',        OLD.serie,
                'data_attuale', OLD.data,
                'data_richiesta', NEW.data,
                -- ⭐ Il bersaglio: il documento su cui l'errore e'
                --    successo. Sempre visibile a chi opera — se non
                --    lo fosse, la RLS avrebbe gia' impedito l'UPDATE.
                'bersaglio', jsonb_build_array(
                    jsonb_build_object('tipo', 'FATTURA',
                                       'id', OLD.id::text))),
            NEW.tx_id,
            -- ⭐ Nel messaggio va il NUMERO, non l'id: e' quello che
            --    compare sul documento e che una persona riconosce.
            OLD.numero::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_data_numerata()
IS 'Rende immutabile vendite.fatture.data da quando la fattura ha un numero. ⭐ Nasce il 2026-08-25 da una MISURA, non dal piano: trgfn_fattura_satellite_guard_congelamento — che il brief dava per «congela tutto oltre EMESSA» — e'' agganciata alla TESTATA con BEFORE UPDATE OF emittente_snapshot, cliente_snapshot e basta (su fatture_indirizzi e fatture_scadenze copre tutti gli eventi, sulla testata no). Fino a oggi un UPDATE della data su una fattura numerata e DEFINITIVA passava, e la data e'' il dato da cui dipendono l''anno del sezionale, la chiave del contatore e il piano rate: il cantiere costruiva un cancello sull''ingresso principale lasciando aperto il retro. ⛔ IL DISCRIMINANTE E'' OLD.numero, NON LO STATO, e non e'' un dettaglio: fn_numera_fattura_opz_emessa assegna il numero MENTRE la fattura e'' in EMESSA — lo stato passa a DEFINITIVA dopo, nella finalizzazione dello step — quindi una soglia scritta sugli stati DRAFT|EMESSA lascerebbe una finestra reale in cui il documento ha un numero fiscale e la data e'' ancora scrivibile. ℹ️ Il codice e'' nuovo e non riusa E_COLONNA_NON_MODIFICABILE, che pure esiste sulla stessa tabella: quel messaggio dice «Colonna non modificabile: %s» e non dice PERCHE'', mentre il perche'' e'' tutto. Gemello per forma di E_FATTURA_NON_ANNULLABILE. Nel segnaposto va il NUMERO e non l''id: e'' quello che compare sul documento. ℹ️ Nessun `campo` nel contesto: su un CONFLITTO_STATO non c''e'' niente da accendere, ed e'' la situazione a non consentirlo. Brief: brief-db-numerazione-data-documento-e-sequenza.md §4 DB-14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
