{% include-markdown "it/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente.md" %}
# ⚙️ Funzione `fn_ba_ha_storia_emittente`

```sql
CREATE FUNCTION fn_ba_ha_storia_emittente(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_ba_ha_storia_emittente(p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la tabella dei documenti di ogni famiglia e' la target_table della
--   sua sorgente (config.fn_sorgente_tabella), non piu'
--   schema_tabella/nome_tabella; firma ancorata.
DECLARE
    v_famiglia record;
    -- l'esito di un EXISTS: nessuna colonna dietro
    v_trovato  boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rispondere alla SOLA domanda che serve al guard: questo
    --   billing account ha gia' un documento numerato su un
    --   registro? Si esce al PRIMO che si trova.
    --
    -- ⭐ Esiste separata dal conteggio perche' il guard gira su
    --   OGNI movimento di un mapping, e li' cinque count(*)
    --   sarebbero il prezzo di un'informazione che non si usa:
    --   quanto grande sia la storia interessa solo alla frase
    --   del rifiuto, cioe' quando si e' gia' deciso di rifiutare.
    --
    -- ⚠️ SECURITY DEFINER: fatture e commesse hanno la RLS. Da
    --   INVOKER la storia di un ALTRO emittente sarebbe
    --   invisibile e la risposta sarebbe «nessuna storia» proprio
    --   nel caso da bloccare.
    -- =========================================================
    IF p_billing_account_id IS NULL THEN
        -- La riga senza billing account e' quella del gestore
        -- globale: non e' un cliente, e la guarda
        -- anagrafiche.fn_guard_ba_gestore_globale_storia.
        RETURN false;
    END IF;

    FOR v_famiglia IN
        SELECT t.schema_tabella,
               t.nome_tabella,
               fd.colonna_numero,
               fd.colonna_billing_account
          FROM vendite.famiglie_documento fd
          -- ⭐ rev 2026-10-20: la tabella e' quella della sorgente (G-5).
          -- ⚠️ LEFT e non CROSS: una famiglia attiva senza tabella (il
          --   guard dei riferimenti non la lascia nascere) non deve
          --   SPARIRE dal presidio: il format() con NULL fallisce
          --   rumoroso, come prima una tabella che non c'era.
          LEFT JOIN LATERAL config.fn_sorgente_tabella(fd.codice_interno) t ON true
         WHERE fd.attivo
           -- ⭐ Solo le famiglie che HANNO un billing account (dal
           --   20260914-07 la colonna e' opzionale): una famiglia senza
           --   BA non puo' contribuire alla storia di nessun BA. Il
           --   salto sta QUI, nella query che sceglie, e non dentro il
           --   format(): %I con NULL solleva un errore di PostgreSQL
           --   senza codice di dominio, e %s con NULL tace.
           AND COALESCE(btrim(fd.colonna_billing_account), '') <> ''
         ORDER BY fd.id
    LOOP
        -- ⚠️ Identificatori da %I, valori da USING: il catalogo
        --   e' dato, non codice.
        EXECUTE format(
            'SELECT EXISTS (SELECT 1 FROM %I.%I d'
            || ' WHERE d.%I = $1'
            || '   AND d.%I IS NOT NULL'
            || '   AND btrim(d.%I::text) <> $2)',
            v_famiglia.schema_tabella,
            v_famiglia.nome_tabella,
            v_famiglia.colonna_billing_account,
            v_famiglia.colonna_numero,
            v_famiglia.colonna_numero)
          INTO v_trovato
         USING p_billing_account_id, ''::text;

        IF v_trovato THEN
            RETURN true;
        END IF;
    END LOOP;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_ba_ha_storia_emittente(p_billing_account_id bigint)
IS 'Questo billing account ha gia'' un documento NUMERATO su un registro? E'' il percorso felice del presidio sul cambio emittente del BA: si esce al PRIMO documento trovato, e le famiglie da guardare si leggono da vendite.famiglie_documento. ⭐ Esiste separata da anagrafiche.fn_get_storia_emittente_ba, e non e'' duplicazione: il guard gira su OGNI movimento di un mapping emittente-BA, e li'' cinque count(*) sarebbero il prezzo di un''informazione che non si usa — quanto grande sia la storia interessa solo alla frase del rifiuto, cioe'' quando si e'' gia'' deciso di rifiutare. E'' lo stesso schema di vendite.fn_get_next_progressivo, dove il bersaglio si compone dopo il no. ⭐ Il predicato e'' DERIVATO e non elencato: la regola decisa il 2026-08-30 e'' che ogni famiglia con un registro e'' per costruzione per-emittente, quindi e'' candidata a bloccare lo spostamento — e il sesto documento entra nella regola il giorno in cui si registra la sua famiglia, senza nessun elenco parallelo da tenere allineato. ⚠️ «Numerato» e non «esistente»: una bozza non ha congelato niente. Ne discende che una FATTURA IN BOZZA non blocca piu'' — prima si contava, perche'' il conteggio non guardava il numero — ed e'' voluto: e'' esattamente il caso per cui la finestra di correzione esiste, il cliente nato sotto l''emittente sbagliato prima che ci passi del lavoro vero. ⚠️ SQL DINAMICO: gli identificatori vengono dal catalogo e passano da %I, i valori da USING. Una riga di catalogo sbagliata romperebbe qui a runtime, ed e'' la ragione del guard vendite.trgfn_famiglie_documento_guard_riferimenti. ⚠️ SECURITY DEFINER: fatture e commesse hanno la RLS accesa, e da SECURITY INVOKER la storia di un ALTRO emittente sarebbe invisibile — la risposta sarebbe «nessuna storia, si puo'' spostare» proprio nel caso che deve bloccare. ℹ️ Input NULL -> false: la riga senza billing account e'' quella del gestore globale, e la guarda anagrafiche.fn_guard_ba_gestore_globale_storia. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-16. ⭐ rev 2026-09-14 (P-9, brief-db-modifiche-certe-ciclo-vendita-e-articolo sezione 3-bis): famiglie_documento.colonna_billing_account e'' opzionale, e una famiglia senza billing account (l''ordine di acquisto) NON entra nel giro: il salto sta nella query che SCEGLIE le famiglie, non dentro il format() — un %I con NULL solleverebbe un errore di PostgreSQL senza codice di dominio, e un %s con NULL produrrebbe stringa vuota senza fiatare. Il predicato resta derivato dal catalogo. Rev 2026-10-20 (20261020-40, brief-db-grammatica-unica-documenti 2c, G-5): la tabella dei documenti di ogni famiglia e'' la target_table della sua sorgente (config.fn_sorgente_tabella).';
```

</div>

---
{% include-markdown "signature-core.md" %}
