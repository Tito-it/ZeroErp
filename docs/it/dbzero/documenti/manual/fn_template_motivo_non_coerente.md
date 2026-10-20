## 📘 Documentazione Concettuale – Funzione `documenti.fn_template_motivo_non_coerente()`

> 👀 **Vedi anche**
>
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)
> [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-4)

Risponde a una domanda: **questo modello va bene per questo documento?** `NULL` se sì, altrimenti
il motivo.

### I motivi, nell'ordine in cui si controllano

| Motivo | Quando |
|---|---|
| `MODELLO_INESISTENTE` | l'id non è un modello |
| `SORGENTE` | il modello è per un'altra sorgente |
| `TIPO` | il modello produce un altro tipo di documento (solo se il tipo è indicato) |
| `EMITTENTE` | il modello è di un'altra azienda e non è standard |

Lo standard vale per tutte le aziende: si esclude per nome, e i confronti sono in
`IS DISTINCT FROM`, perché l'azienda di uno standard è `NULL`.

### Chi la legge

* `fn_risolvi_template_applicabile`, per il modello indicato, **prima** del render;
* `trgfn_documenti_generati_check_coerenza`, alla scrittura del documento generato.

È la stessa regola nei due momenti: per questo sta in un punto solo.

### Firma

`LANGUAGE sql` (`BEGIN ATOMIC`), `STABLE`, `SECURITY INVOKER`. Il contratto è nella doc
auto-generata.
