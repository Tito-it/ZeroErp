## 📘 Documentazione Concettuale – Funzione `documenti.fn_template_motivo_non_coerente`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — sorgente, tipo e azienda del modello
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa registrata, che deve essere coerente col suo modello
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la chiede per il modello indicato, prima del render
> * [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza) — la chiede alla scrittura del documento generato
> * [documenti.fn_template_motivo_non_stampabile](/dbzero/documenti/funzioni/fn_template_motivo_non_stampabile) — la domanda gemella: il modello oggi stampa?
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3.3, il modello indicato

---

### 🎯 Scopo Principale

Risponde a una domanda: questo modello va bene per questo documento? Restituisce niente se sì,
altrimenti il motivo per cui no. Non solleva errori: il codice lo sceglie chi la chiama.

---

### I motivi, nell'ordine in cui si controllano

| Motivo | Quando |
| --- | --- |
| `MODELLO_INESISTENTE` | l'id non è un modello |
| `SORGENTE` | il modello è per un'altra sorgente |
| `TIPO` | il modello produce un altro tipo di documento; si controlla solo se il tipo è indicato |
| `EMITTENTE` | il modello è di un'altra azienda e non è standard |

Vale il primo motivo che si verifica. Lo standard vale per tutte le aziende: non ha un'azienda, e per
questo è escluso dal controllo dell'azienda invece di confrontarlo.

---

### ⭐ La stessa regola nei due momenti

La regola serve prima del render (il modello indicato da chi stampa) e alla scrittura del documento
generato (la difesa finale). Sta in un punto solo perché le due risposte non possano divergere: un
modello che la porta della stampa accetta non viene poi rifiutato alla registrazione, e viceversa.

---

### Test

* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — i tre motivi attraverso la porta
  della stampa, l'id che non è un modello, e lo stesso motivo letto dal trigger di coerenza.
* `db/pgtap/documenti/test-documenti-risoluzione-scarto-asset-v1.sql` — `SORGENTE` e `TIPO` chiesti
  direttamente.

---

### Note di migrazione

* 2026-10-21 — nasce, per dare alla porta della stampa e al trigger di coerenza una regola sola.

---

{% include-markdown "signature-core.md" %}
