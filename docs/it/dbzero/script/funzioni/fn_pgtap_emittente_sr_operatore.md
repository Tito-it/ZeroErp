{% include-markdown "it/dbzero/script/manual/fn_pgtap_emittente_sr_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_emittente_sr_operatore`

```sql
CREATE FUNCTION fn_pgtap_emittente_sr_operatore()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_pgtap_emittente_sr_operatore()
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dare a una fixture pgTAP il soggetto_ruolo
    --   dell'emittente su cui l'operatore corrente puo'
    --   davvero scrivere, per le tabelle che usano la
    --   convenzione SR invece di emittente_fiscale_id.
    --   Brief: brief-db-pgtap-runner-rls-baseline §26.
    -- Uso, al posto di lasciare la colonna a NULL:
    --   emittente_soggetto_ruolo_id =
    --     script.fn_pgtap_emittente_sr_operatore()
    --
    -- Si appoggia alla compagna invece di riscriverne la
    -- scelta: la logica di «quale emittente» sta in un posto
    -- solo, qui c'e' solo la traduzione 1:1 verso il
    -- soggetto_ruolo, la stessa che fa
    -- script.fn_scope_ef_whitelist_via_sr in senso inverso.
    SELECT ef.soggetto_ruolo_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = script.fn_pgtap_emittente_operatore();
$function$

COMMENT ON FUNCTION script.fn_pgtap_emittente_sr_operatore()
IS 'Helper pgTAP: soggetto_ruolo dell''emittente dell''operatore di contesto, per le tabelle a convenzione SR (vendite.commesse, vendite.fatture). Compagna di script.fn_pgtap_emittente_operatore, che risponde per la convenzione emittente_fiscale_id. Rende scrivibile cio'' che l''applicazione scriverebbe: NON e'' una scorciatoia per aggirare la RLS, e una fixture che ha bisogno di un emittente diverso deve cambiare contesto operatore. Brief: brief-db-pgtap-runner-rls-baseline.';
```

</div>

---
{% include-markdown "signature-core.md" %}
