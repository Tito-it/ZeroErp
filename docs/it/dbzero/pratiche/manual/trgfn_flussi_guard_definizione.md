## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui è montata
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il template del flusso e la sua edizione
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni del workflow
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_pratiche_guard_pin_immutabile](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_pin_immutabile) — tiene fermo il pin della pratica
> * [pratiche.trgfn_workflow_definizioni_guard](/dbzero/pratiche/funzioni/trgfn_workflow_definizioni_guard) — il ciclo di vita delle edizioni
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — la generazione fra pratiche, che rimappa il template

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_definizione` garantisce che il template di un flusso
appartenga alla stessa edizione di workflow che la pratica ha fissato alla nascita
(`pratiche.definizione_id`).

Una pratica non può accogliere un passo di un'altra definizione: né di un altro tipo, né di un'altra
edizione o di un fork dello stesso tipo.

---

### La regola

Scatta `BEFORE INSERT` su `pratiche.flussi`, riga per riga, ed è il primo dei guard d'inserimento
della tabella. Confronta l'edizione del template con quella della pratica: se differiscono, il flusso
non nasce. Entrambe le colonne sono obbligatorie, quindi il confronto è netto.

Il guard guarda solo l'inserimento: la pratica e il template di un flusso non cambiano dopo la sua
creazione, come per i guard sorella dei prerequisiti e della ripetibilità.

---

### È compatibile per costruzione con chi scrive flussi

* Template e pratica dello stesso tipo, senza fork, stanno nella stessa edizione preset.
* Un seed di flussi coerente passa; uno incoerente è un errore di dato e va rifiutato.
* La generazione fra pratiche (`pratiche.fn_genera_pratica_da_flusso`) rimappa il template di
  destinazione per codice nell'edizione fissata dalla pratica figlia, così il flusso inserito soddisfa
  il guard.

---

### Codici errore

* `E_FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` — il template sta in un'edizione diversa da quella della
  pratica; il messaggio porta il codice del template, l'edizione della pratica e la pratica.

---

### Test

* `pratiche/test-workflow-definizioni-fase1` — un flusso coerente passa, uno incoerente è rifiutato.

---

### Note di migrazione

* 2026-07-03 — nasce con il versionamento delle definizioni di workflow
  (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}
