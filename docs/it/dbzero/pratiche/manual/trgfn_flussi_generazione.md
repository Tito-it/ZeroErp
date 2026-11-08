## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_generazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui è montata
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — le regole che dicono che cosa generare
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — lo stato `COMPLETATO`
>
> Approfondimento funzioni:
>
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — genera la pratica di una regola

---

### 🎯 Scopo Principale

`pratiche.trgfn_flussi_generazione` fa la generazione automatica fra pratiche: quando un flusso
transita a `COMPLETATO`, applica le regole di generazione automatica del suo template e genera, per
ciascuna, la pratica a valle con `pratiche.fn_genera_pratica_da_flusso`.

---

### Quando genera

È montata `AFTER UPDATE OF stato_id`, riga per riga, su `pratiche.flussi`, nella fase `_z90_`.

* ⭐ Solo alla **transizione** di stato: un aggiornamento che non cambia lo stato (per esempio la
  correzione delle note di esito su un flusso già completato) non genera niente. Il controllo è dentro
  la funzione, così copre anche un aggiornamento che riscrive lo stesso stato.
* Solo se il nuovo stato è `COMPLETATO`.
* Solo per un flusso nato da un template: un flusso manuale non ha regole.

---

### Quali regole

Le regole di `pratiche.regole_generazione` che hanno come origine il template del flusso, attive e
automatiche, e il cui esito richiesto è vuoto (qualsiasi esito) o uguale all'esito del flusso. Le
regole non automatiche il trigger non le guarda: le invoca il backend in modo esplicito.

---

### ⭐ Tre difese contro la doppia generazione

1. Il trigger genera solo alla transizione di stato.
2. `pratiche.fn_genera_pratica_da_flusso` non rigenera una pratica che esiste già.
3. Un indice unico sulle pratiche impedisce due pratiche dello stesso tipo di prestazione generate dallo
   stesso flusso di origine.

---

### Test

* `pratiche/test-generazione-cross-pratica` — la generazione alla transizione e la sua idempotenza.

---

### Note di migrazione

* 2026-06-11 — il trigger diventa idempotente: prima scattava a ogni aggiornamento, senza controllo di
  transizione, e ogni aggiornamento di un flusso già completato generava una nuova pratica figlia.

---

{% include-markdown "signature-core.md" %}
