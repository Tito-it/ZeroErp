{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_ba_gestore_globale_storia.md" %}
# ⚙️ Funzione `fn_guard_ba_gestore_globale_storia`

```sql
CREATE FUNCTION fn_guard_ba_gestore_globale_storia(p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_ba_gestore_globale_storia(p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_ba_id anagrafiche.billing_account.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   ⚠️ E' l'unica operazione del cantiere con RAGGIO N:
    --   cambiare il gestore globale sposta in blocco l'emittente
    --   di TUTTI i billing account che non hanno un mapping
    --   specifico. Una riga sola puo' ri-attribuire
    --   retroattivamente l'emittente di un numero arbitrario di
    --   documenti gia' emessi.
    --
    -- ⚠️ SECURITY DEFINER: il semi-join legge billing_account,
    --   fatture e commesse, che hanno tutte la RLS.
    -- =========================================================
    IF p_emittente_sr_prima IS NOT DISTINCT FROM p_emittente_sr_dopo THEN
        RETURN;
    END IF;

    -- ⭐ Il PRIMO billing account non mappato che abbia storia.
    --   Basta lui: la risposta a «esiste storia» non cambia con
    --   il secondo, e delegargli il messaggio significa nominare
    --   un cliente vero invece di dire «da qualche parte».
    -- ⚠️ ORDER BY esplicito: un LIMIT 1 senza non verifica,
    --   scommette — e qui deciderebbe QUALE cliente compare
    --   nell'errore.
    SELECT ba.id
      INTO v_ba_id
      FROM anagrafiche.billing_account ba
     WHERE NOT EXISTS (
               SELECT 1
                 FROM anagrafiche.emittenti_fiscali_billing_account e
                WHERE e.billing_account_id = ba.id)
       AND (
             EXISTS (SELECT 1 FROM vendite.fatture f
                      WHERE f.billing_account_id = ba.id)
          OR EXISTS (SELECT 1 FROM vendite.commesse c
                      WHERE c.billing_account_id = ba.id)
           )
     ORDER BY ba.id
     LIMIT 1;

    IF v_ba_id IS NULL THEN
        RETURN;
    END IF;

    -- Il messaggio lo compone il guard del singolo billing
    -- account: una implementazione, due superfici.
    PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
        v_ba_id, p_emittente_sr_prima, p_emittente_sr_dopo);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_ba_gestore_globale_storia(p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
IS 'Guard fail-fast per lo spostamento del GESTORE GLOBALE (la riga di anagrafiche.emittenti_fiscali_billing_account con billing_account_id IS NULL e is_default = true), l''unica operazione del cantiere con RAGGIO N: quella riga decide l''emittente di TUTTI i billing account che non hanno un mapping specifico, quindi cambiarla li sposta in blocco e puo'' ri-attribuire retroattivamente l''emittente di un numero arbitrario di documenti gia'' emessi. E'' il gemello esatto di anagrafiche.fn_guard_albero_ba_gestore_globale, che lo stesso movimento lo presidia gia'' per l''omogeneita'' dell''albero. ⭐ Un SEMI-JOIN e non un ciclo, e la differenza col gemello e'' motivata: a quello serve visitare ogni BA perche'' deve dire QUALE coppia e'' mista, qui la domanda e'' «esiste storia» e la risposta non cambia dopo il primo che la trova. Si cerca il primo (ORDER BY ba.id + LIMIT 1, deterministico — un LIMIT 1 senza ORDER BY deciderebbe a caso quale cliente compare nell''errore) e si delega ad anagrafiche.fn_guard_ba_cambio_emittente, che compone il messaggio nominando un cliente vero invece di dire «da qualche parte»: una implementazione, due superfici. ⭐ Esce subito se l''emittente non cambia davvero. ⚠️ SECURITY DEFINER: il semi-join legge billing_account, fatture e commesse, che hanno tutte la RLS. ⚠️ In pratica questo cancello chiude quasi sempre, ed e'' corretto: spostare il gestore globale su un''installazione che ha gia'' fatturato non e'' una configurazione, e'' una riscrittura della storia. Piano: brief-db-billing-account-cambio-emittente, M2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
