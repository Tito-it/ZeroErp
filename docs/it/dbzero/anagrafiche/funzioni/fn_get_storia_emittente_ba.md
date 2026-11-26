{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba.md" %}
# ⚙️ Funzione `fn_get_storia_emittente_ba`

```sql
CREATE FUNCTION fn_get_storia_emittente_ba(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
 RETURNS TABLE(famiglia_documento character varying, famiglia_descrizione character varying, n_documenti bigint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la tabella dei documenti di ogni famiglia e' la target_table della
--   sua sorgente (config.fn_sorgente_tabella); famiglia_documento e'
--   il codice della sorgente; firma e RETURNS TABLE ancorati.
DECLARE
    -- la riga di una SELECT statica sul catalogo delle famiglie (§5e)
    v_famiglia record;
    -- un conteggio: nessuna colonna dietro
    -- un conteggio: nessuna colonna dietro
    v_n        bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire QUANTI documenti e DI CHE SPECIE hanno gia'
    --   congelato l'emittente di questo billing account. Una
    --   riga per famiglia che ha almeno un documento, in
    --   qualunque stato (anche in bozza);
    --   nessuna riga = nessuna storia.
    --
    -- ⭐ rev 2026-08-31: prima tornava (n_fatture, n_commesse) —
    --   due colonne fisse, cioe' un elenco travestito da firma.
    --   Ora la forma segue il catalogo, e il messaggio che legge
    --   l'operatore puo' dire QUALE documento blocca: senza,
    --   «non si puo'» manda a cercare a mano in cinque tabelle.
    --
    -- ⚠️ Si chiama SOLO nel ramo d'errore. Il si'/no del guard
    --   lo da' anagrafiche.fn_ba_ha_storia_emittente.
    -- =========================================================
    IF p_billing_account_id IS NULL THEN
        RETURN;
    END IF;

    FOR v_famiglia IN
        SELECT fd.codice_interno,
               fd.descrizione,
               t.schema_tabella,
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
        EXECUTE format(
            'SELECT count(*) FROM %I.%I d'
            || ' WHERE d.%I = $1',
            v_famiglia.schema_tabella,
            v_famiglia.nome_tabella,
            v_famiglia.colonna_billing_account)
          INTO v_n
         USING p_billing_account_id;

        -- ⚠️ Le famiglie a zero NON escono: «nessuna riga» e'
        --   la risposta «nessuna storia», e chi compone la frase
        --   non deve filtrare gli zeri.
        IF v_n > 0 THEN
            famiglia_documento   := v_famiglia.codice_interno;
            famiglia_descrizione := v_famiglia.descrizione;
            n_documenti          := v_n;
            RETURN NEXT;
        END IF;
    END LOOP;

    RETURN;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
IS 'La storia del billing account per famiglia: una riga per ogni famiglia attiva di vendite.famiglie_documento con almeno un documento del billing account, in qualunque stato, col numero dei documenti. Nessuna riga = nessuna storia. Compone la frase di E_BA_EMITTENTE_CON_STORIA (script.fn_check_ba_cambio_emittente). SECURITY DEFINER: i documenti hanno la RLS.';
```

</div>

---
{% include-markdown "signature-core.md" %}
