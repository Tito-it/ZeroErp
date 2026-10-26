{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_guard_ambito.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_guard_ambito`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_guard_ambito()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la stessa regola dell'ambito, applicata quando a cambiare
--   e' il TITOLO e non le sue righe. Due titoli diventano
--   sovrapposti anche allargando `valido_al`, riattivando un
--   titolo spento o cambiandone il tipo: in nessuno di quei casi
--   la tabella figlia viene toccata, quindi il guard sulle figlie
--   non scatta. Chiama la stessa fn_check.
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi jsonb;
BEGIN
    v_motivi := anagrafiche.fn_check_titolo_iva_ambito(NEW.id);

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⚠️ `NEW.tx_id`: trigger `_z90_` **AFTER**, i BEFORE sono gia' passati.
    -- ⚠️ Anche qui l'ordine di fusione si inverte e `campo` vince: nessuna
    --   check del database mette `campo` dentro `dettaglio` (misurato
    --   2026-09-08), quindi e' una regola che si unifica senza cambiare nulla.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', 'trgfn_soggetti_titoli_iva_guard_ambito',
        v_motivi,
        'valido_al',
        NEW.tx_id);

    -- ⭐ Ora raggiungibile: l'helper tace se non c'e' nessun motivo.
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito()
IS 'La stessa regola dell''ambito, applicata quando a cambiare e'' il TITOLO invece delle sue righe. ⭐ Non e'' un doppione del guard sulle figlie: due titoli diventano sovrapposti anche allargando valido_al, riattivando un titolo spento o cambiandone il tipo — e in nessuno di quei casi la tabella figlia viene toccata, quindi quel guard non scatta. Chiama la stessa anagrafiche.fn_check_titolo_iva_ambito: la regola e'' scritta in un posto solo. ⚠️ AFTER UPDATE, perche'' la fn_check legge la riga com''e'' DOPO la modifica. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
