## 📘 Documentazione Concettuale – Funzione trigger `documenti.trgfn_documenti_generati_guard_versione_contesto()`

> 👀 **Vedi anche**
>
> [documenti.fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto)
> [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)

### 🎯 Scopo

(30-09-2026 — brief `brief-db-documenti-versione-contesto-template`)

**Una stampa incoerente non si registra, qualunque strada l'abbia prodotta.** All'INSERT di una
riga di `documenti.documenti_generati` legge la forma dichiarata dal contesto congelato e la
confronta con quella della versione di template usata, delegando a
`documenti.fn_guard_versione_contesto`. È la rete dietro al controllo che il backend fa prima del
render: protegge da una strada di stampa che lo dimentica.

### Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_a10_guard_versione_contesto_ins
    BEFORE INSERT ON documenti.documenti_generati
    FOR EACH ROW
    EXECUTE FUNCTION documenti.trgfn_documenti_generati_guard_versione_contesto();
```

* **Fase** `a10`. In ordine alfabetico parla **dopo** `check_coerenza` e `guard_emittente_scope`:
  su una riga incoerente la frase giusta è quella della coerenza, non quella della forma.
* **Solo INSERT**: `context_json` e `template_versione_id` non cambiano dopo (guard A7).

### La forma dei dati

`context_json -> '_meta' -> 'context_version'`, **un intero JSON** come lo scrive il builder
(`"context_version": 2`). Qualunque altra cosa — chiave assente, stringa `"2"`, `2.5`, `null` —
vale «forma non dichiarata»: la funzione passa `NULL` e il guard risponde
`E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE`. Niente cast diretto: un `"2a"::integer`
darebbe un `22P02` al posto del codice di catalogo.

---

{% include-markdown "signature-core.md" %}
