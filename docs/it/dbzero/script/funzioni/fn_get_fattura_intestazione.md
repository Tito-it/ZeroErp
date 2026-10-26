{% include-markdown "it/dbzero/script/manual/fn_get_fattura_intestazione.md" %}
# ⚙️ Funzione `fn_get_fattura_intestazione`

```sql
CREATE FUNCTION fn_get_fattura_intestazione(p_fattura_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_fattura_intestazione(p_fattura_id bigint)
 RETURNS TABLE(emittente_soggetto_ruolo_id bigint, cliente_soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire DI CHI E' e A CHI E' una fattura, e nient'altro.
    --
    -- ⭐ Perche' SECURITY DEFINER: vendite.fatture ha la row
    --   security. Un guard SECURITY INVOKER che confrontasse i
    --   clienti leggendola direttamente direbbe «non sono dello
    --   stesso cliente» anche quando LO SONO — perche' una delle
    --   due non si vede. La domanda di FATTO va risposta per
    --   intero; il permesso lo decide il guard di scope.
    --
    -- ⚠️ Non allarga niente: due id su una fattura che il
    --   chiamante ha gia' nominato, e due id da soli non dicono
    --   niente di usabile — non un numero, non un importo.
    --
    -- ⚠️ Dipende dalla RLS abilitata e NON forzata (il
    --   proprietario la salta). Con un FORCE va rivista, come
    --   fn_resolve_emittente_fiscale_id.
    --
    -- Nessuna riga se la fattura non esiste: chi chiama decide
    -- che farne, ed e' l'unico che sa quale messaggio dare.
    -- =========================================================
    RETURN QUERY
    SELECT f.emittente_soggetto_ruolo_id,
           ba.soggetto_ruolo_id
      FROM vendite.fatture f
      JOIN anagrafiche.billing_account ba
        ON ba.id = f.billing_account_id
     WHERE f.id = p_fattura_id;
END
$function$

COMMENT ON FUNCTION script.fn_get_fattura_intestazione(p_fattura_id bigint)
IS 'Risponde l''emittente e il cliente di una fattura, FUORI dalla row security. ⭐ Serve ai guard che devono confrontare due documenti: vendite.fatture ha la RLS, e un guard SECURITY INVOKER che la leggesse direttamente non distinguerebbe «e'' di un altro cliente» da «non lo vedo» — direbbe la prima frase anche nel secondo caso. La domanda di FATTO va risposta per intero; il PERMESSO lo decide il guard di scope, che e'' un''altra cosa. ⚠️ Non allarga nessun perimetro: due id su una fattura che il chiamante ha gia'' nominato, e due id da soli non raccontano niente. ⚠️ Dipende dalla RLS abilitata e NON forzata: con un FORCE va rivista, come fn_resolve_emittente_fiscale_id e fn_check_scadenza_di_fattura. Nessuna riga se la fattura non esiste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
