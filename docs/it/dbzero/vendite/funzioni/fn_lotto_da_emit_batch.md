{% include-markdown "it/dbzero/vendite/manual/fn_lotto_da_emit_batch.md" %}
# ⚙️ Funzione `fn_lotto_da_emit_batch`

```sql
CREATE FUNCTION fn_lotto_da_emit_batch(p_emit_batch_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_lotto_da_emit_batch(p_emit_batch_id uuid)
 RETURNS bigint
 LANGUAGE sql
 STABLE
RETURN (SELECT l.id FROM vendite.fatturazione_lotti l WHERE (l.lock_batch_id = fn_lotto_da_emit_batch.p_emit_batch_id))

COMMENT ON FUNCTION vendite.fn_lotto_da_emit_batch(p_emit_batch_id uuid)
IS 'Il lotto che sta girando, risolto dal marchio del giro (p_emit_batch_id = fatturazione_lotti.lock_batch_id, UNIQUE: al piu'' una riga). NULL in ingresso, marchio sconosciuto o lotto fuori dal perimetro RLS di chi esegue → NULL, cioe'' NESSUNA auto-esclusione del proprio lotto (la risposta prudente). Sede unica della risoluzione: prima stava inline nell''emit e mancava nella discovery — due copie, una gia'' sfilata. La leggono fn_list_commesse_emittibili e fn_emit_attivita_fatturabili_da_commessa, che passano il risultato a fn_classe_emittibilita_per_giro. SECURITY INVOKER, STABLE. Brief: brief-db-rilancio-step-non-rivede-le-proprie-commesse (D1), 2026-09-12.';
```

</div>

---
{% include-markdown "signature-core.md" %}
