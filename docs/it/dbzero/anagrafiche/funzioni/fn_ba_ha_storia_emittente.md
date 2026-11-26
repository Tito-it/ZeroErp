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
    -- la riga di una SELECT statica sul catalogo delle famiglie (§5e)
    v_famiglia record;
    -- l'esito di un EXISTS: nessuna colonna dietro
    v_trovato  boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rispondere alla SOLA domanda che serve al guard: questo
    --   billing account ha gia' un documento, di qualunque
    --   famiglia e in qualunque stato (anche in bozza)? Si
    --   esce al PRIMO che si trova.
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
        -- La riga senza billing account e' quella dell'azienda
        -- predefinita: non e' un cliente, e non ha storia.
        RETURN false;
    END IF;

    FOR v_famiglia IN
        SELECT t.schema_tabella,
               t.nome_tabella,
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
            || ' WHERE d.%I = $1)',
            v_famiglia.schema_tabella,
            v_famiglia.nome_tabella,
            v_famiglia.colonna_billing_account)
          INTO v_trovato
         USING p_billing_account_id;

        IF v_trovato THEN
            RETURN true;
        END IF;
    END LOOP;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_ba_ha_storia_emittente(p_billing_account_id bigint)
IS 'Il billing account ha gia'' un documento: di qualunque famiglia attiva di vendite.famiglie_documento che dichiara la colonna del billing account, e in qualunque stato, anche in bozza. E'' la storia che chiude il cambio d''azienda del billing account (script.fn_check_ba_cambio_emittente). Si esce al primo documento trovato. NULL: false. SECURITY DEFINER: i documenti hanno la RLS, e la storia di un''altra azienda deve contare.';
```

</div>

---
{% include-markdown "signature-core.md" %}
