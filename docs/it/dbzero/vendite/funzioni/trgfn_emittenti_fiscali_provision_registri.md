# ⚙️ Funzione `trgfn_emittenti_fiscali_provision_registri`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_provision_registri()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_emittenti_fiscali_provision_registri()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un emittente nuovo — o appena riattivato — nasce gia'
    --   capace di emettere DDT, ordini, resi e commesse.
    --
    -- ⚠️ Anche sulla RIATTIVAZIONE: un emittente puo' nascere
    --   spento ed essere acceso dopo, e con un trigger di solo
    --   INSERT resterebbe senza registri proprio nel momento in
    --   cui comincia a servire.
    -- ⭐ La composizione non sta qui: sta in
    --   vendite.fn_provision_registri_emittente, che e' la sede
    --   unica. Qui c'e' solo il QUANDO.
    -- =========================================================
    IF NEW.attivo IS NOT TRUE THEN
        RETURN NULL;
    END IF;

    PERFORM vendite.fn_provision_registri_emittente(NEW.soggetto_ruolo_id);
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_emittenti_fiscali_provision_registri()
IS 'Trigger AFTER INSERT OR UPDATE OF attivo su anagrafiche.emittenti_fiscali: quando un emittente nasce attivo — o viene riattivato — gli provvede i registri delle famiglie non fiscali chiamando vendite.fn_provision_registri_emittente. ⭐ Chiude la lacuna dichiarata dal C2-12, che aveva provveduto ai soli emittenti gia'' esistenti: quello FUTURO sarebbe rimasto senza registri, e i suoi DDT non sarebbero nati finche'' qualcuno non li configurava — fail-closed e rumoroso, ma attrito nuovo su un''operazione che prima bastava a se stessa. Decisione di Tid, 2026-08-31: la lacuna va chiusa anche se formalmente fuori dal perimetro del cantiere, perche'' una lacuna dichiarata e non chiusa e'' un difetto con una nota sopra. ⚠️ Scatta anche sulla RIATTIVAZIONE e non solo sull''INSERT: un emittente puo'' nascere attivo = false ed essere acceso dopo, e un trigger di solo INSERT lo lascerebbe senza registri proprio quando comincia a servire. ⭐ Qui c''e'' solo il QUANDO: la composizione (codice, descrizione, meta) sta tutta nella funzione, che e'' la sede unica. ℹ️ AFTER e non BEFORE: la riga dell''emittente deve esistere, perche'' la FK del registro ci punta. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-12.';
```

</div>

---
{% include-markdown "signature-core.md" %}
