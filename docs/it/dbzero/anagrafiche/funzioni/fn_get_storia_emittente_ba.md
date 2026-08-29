{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba.md" %}
# ⚙️ Funzione `fn_get_storia_emittente_ba`

```sql
CREATE FUNCTION fn_get_storia_emittente_ba(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
 RETURNS TABLE(n_fatture bigint, n_commesse bigint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Quanti documenti hanno gia' CONGELATO l'emittente di
    --   questo billing account. E' la definizione operativa di
    --   «storia» (decisione D-2): non «quanto e' grave», ma
    --   «chi porta una copia che nessuno riscrivera' piu'».
    --
    -- ⚠️ SECURITY DEFINER: fatture e commesse hanno la RLS. Da
    --   SECURITY INVOKER la storia di un altro emittente sarebbe
    --   invisibile e il chiamante concluderebbe «non c'e'
    --   storia» proprio nel caso da bloccare.
    --
    -- ⛔ Ordini e DDT non si contano: il loro emittente ha un
    --   guard che lo ricontrolla col BA a ogni scrittura, quindi
    --   non e' una copia stantia.
    -- =========================================================
    IF p_billing_account_id IS NULL THEN
        -- Nessun BA = nessuna storia da proteggere. La riga senza
        -- billing account e' quella del gestore globale, e la
        -- guarda fn_guard_ba_gestore_globale_storia.
        RETURN QUERY SELECT 0::bigint, 0::bigint;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        (SELECT count(*) FROM vendite.fatture f
          WHERE f.billing_account_id = p_billing_account_id),
        (SELECT count(*) FROM vendite.commesse c
          WHERE c.billing_account_id = p_billing_account_id);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
IS 'Quanti documenti hanno gia'' CONGELATO l''emittente di un billing account: (n_fatture, n_commesse). E'' la definizione operativa di «storia» del cantiere brief-db-billing-account-cambio-emittente (decisione D-2), e il criterio non e'' la gravita'' ma una proprieta'' del modello — si conta cio'' che porta una COPIA dell''emittente che nessuno riscrivera'' piu''. ⭐ Sono due cose e si compilano da sole: vendite.fatture, dove emittente_soggetto_ruolo_id e'' NOT NULL e accanto c''e'' emittente_snapshot (il documento fiscale porta con se'' chi lo ha emesso); e vendite.commesse, dove dal 20260826-41 la colonna e'' NOT NULL e vincolata al billing account — con un guard montato UPDATE OF, quindi un mapping spostato NON riscrive quella riga e la lascia falsa in silenzio. ⛔ Ordini e DDT NON si contano, e non per clemenza: hanno un trgfn_*_guard_emittente_ba che ricontrolla la coerenza col BA a ogni scrittura, quindi la loro copia non invecchia — metterli nella lista bloccherebbe piu'' casi senza chiudere nessun buco in piu'', e «blocca di piu''» non e'' un argomento. ⚠️ SECURITY DEFINER: entrambe le tabelle hanno la RLS accesa, e da SECURITY INVOKER la storia di un ALTRO emittente sarebbe invisibile — il guard direbbe «nessuna storia, si puo'' spostare» proprio nel caso che deve bloccare. E'' la stessa ragione per cui anagrafiche.fn_guard_albero_ba_emittente e'' DEFINER. ⭐ Restituisce i CONTEGGI e non un booleano perche'' il messaggio che legge l''operatore deve dire QUANTE fatture e QUANTE commesse: un «non si puo''» senza numeri manda a cercare a mano cosa c''e'' sotto. ⚠️ Entrambi i conteggi sono serviti da un indice (ix_fatture_ba_data, ix_commesse_ba_utility). Input NULL -> (0, 0): la riga senza billing account e'' quella del gestore globale, e la guarda anagrafiche.fn_guard_ba_gestore_globale_storia.';
```

---
{% include-markdown "signature-core.md" %}
