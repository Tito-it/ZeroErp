## 📘 Documentazione Concettuale – Funzione `documenti.fn_template_motivo_non_stampabile`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello, che deve essere acceso
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa, che nasce dalla versione in uso
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — la sede di «può stampare», che la funzione legge
>
> Approfondimento funzioni:
>
> * [documenti.fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente) — la domanda gemella: il modello va bene per il documento?
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la chiede per il modello indicato, prima del render
> * [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza) — la chiede alla nascita della stampa
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3.3, il modello indicato

---

### 🎯 Scopo Principale

Risponde a una domanda: questo modello oggi può stampare, e, se si indica una versione, proprio con
quella? Restituisce niente se sì, altrimenti il motivo per cui no. Non solleva errori: il codice lo
sceglie chi la chiama.

---

### I motivi, nell'ordine in cui si controllano

| Motivo | Quando |
| --- | --- |
| `MODELLO_INESISTENTE` | l'id non è un modello |
| `MODELLO_SPENTO` | il modello è disattivato |
| `NESSUNA_VERSIONE_VALIDA` | il modello è acceso, ma oggi non ha una versione in vigore: solo bozze, versioni spente, versioni scadute o che valgono da una data futura |
| `VERSIONE_NON_IN_USO` | solo con la versione indicata: il modello stampa, ma con un'altra versione, per esempio perché quella indicata è stata superata |

Vale il primo motivo che si verifica. «Può stampare» non è scritto qui: la funzione legge
`vw_template_versioni_stampabili`, che ne è la sede unica, e aggiunge solo il motivo.

---

### ⭐ La stessa regola nei due momenti

La regola serve prima del render, quando chi stampa indica un modello, e alla nascita della stampa,
come difesa finale: una stampa non tiene accesi i suoi padri, e senza questa domanda potrebbe nascere
da un modello spento o da una versione superata. Sta in un punto solo perché le due risposte non
possano divergere.

---

### Test

* `db/pgtap/documenti/test-documenti-risoluzione-scarto-asset-v1.sql` — i quattro motivi e la
  risposta vuota, costruiti; gli stessi casi visti dalla nascita della stampa e dalla risoluzione del
  modello indicato.

---

### Note di migrazione

* 2026-11-16 — nasce, per dare alla risoluzione del modello indicato e alla nascita della stampa una
  regola sola.

---

{% include-markdown "signature-core.md" %}
