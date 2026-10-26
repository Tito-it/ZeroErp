{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_ambiti_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_ambiti_guard`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_ambiti_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga di ambito che rende incoerente il
--   titolo. Non riscrive il predicato: CHIAMA
--   anagrafiche.fn_check_titolo_iva_ambito e solleva il PRIMO
--   motivo. ⚠️ L'ordine dell'array e' il contratto: se cambiasse,
--   il codice sollevato e il motivo mostrato direbbero cose diverse.
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi jsonb;
BEGIN
    v_motivi := anagrafiche.fn_check_titolo_iva_ambito(NEW.titolo_iva_id);

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⚠️ `NEW.tx_id` e' giusto e non per l'ordine dei nomi: questo guard sta su
    --   un trigger `_z90_` **AFTER**, quindi TUTTI i BEFORE — gen_tx_id
    --   compreso — sono gia' passati.
    -- ⚠️ L'ordine di fusione del contesto lo decide ora l'helper, e `campo`
    --   VINCE sul `dettaglio`. Qui era il contrario; misurato il 2026-09-08,
    --   nessuna fn_check_* del database mette `campo` dentro `dettaglio`,
    --   quindi a video non cambia niente e la regola smette di essere doppia.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', 'trgfn_soggetti_titoli_iva_ambiti_guard',
        v_motivi,
        'ambito',
        NEW.tx_id);

    -- ⭐ Ora RAGGIUNGIBILE, ed e' il ramo «passa»: l'helper tace quando la
    --   check non ha trovato nessun motivo.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()
IS 'Guard sulle righe di anagrafiche.soggetti_titoli_iva_ambiti. ⭐ Non contiene il predicato: CHIAMA anagrafiche.fn_check_titolo_iva_ambito e solleva il codice del PRIMO motivo. Il presidio da scrivere non e'' «gli esiti coincidono» ma «il guard non contiene piu'' il predicato» (linee-guida-sql §12.5.2). ⚠️ L''ordine dell''array e'' il contratto: se divergesse, il codice sollevato e il motivo mostrato direbbero cose diverse. ⚠️ AFTER e non BEFORE: la riga nuova deve essere gia'' visibile perche'' la fn_check la conti — un BEFORE valuterebbe il titolo senza di essa e lascerebbe passare proprio la riga che crea il conflitto. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
