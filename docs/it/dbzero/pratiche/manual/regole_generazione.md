## 📘 Documentazione Concettuale – Tabella `pratiche.regole_generazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il passo che attiva la regola e il passo iniziale della figlia
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il tipo di pratica da generare
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica generata, con la sua genealogia
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso il cui completamento attiva la regola
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_generazione](/dbzero/pratiche/funzioni/trgfn_flussi_generazione) — la generazione automatica
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — il motore, anche per la generazione manuale

---

### 🎯 Scopo Principale

La tabella `pratiche.regole_generazione` configura la generazione di una pratica da un'altra: quando
un flusso di un dato passo si completa con un dato esito, il sistema genera (o propone di generare)
una nuova pratica di un dato tipo.

---

### Come si usa una regola

* **Automatica** (`auto` vero): alla transizione di un flusso a `COMPLETATO`,
  `pratiche.trgfn_flussi_generazione` cerca le regole attive di quel passo che ammettono l'esito del
  flusso, e genera la pratica di ognuna.
* **Manuale** (`auto` falso): la generazione la chiede l'operatore, attraverso il backend, con la
  stessa funzione.
* In entrambi i casi la figlia è una sola per coppia (flusso, tipo di destinazione): la funzione
  ritorna quella che c'è già, e un indice unico su `pratiche.pratiche` lo garantisce anche per
  scritture fuori dal motore.
* La figlia porta la genealogia (`pratica_padre_id`, `flusso_origine_id`) ed eredita dalla madre
  emittente, soggetto, contesto, cliente e priorità.
* Se la regola dichiara il passo iniziale, la figlia nasce con quel flusso già creato in
  `DA_ESEGUIRE`.

---

### Le colonne che non si capiscono dal nome

* `template_flusso_origine_id` — il passo che, al completamento, attiva la regola.
* `tipo_prestazione_dest_id` — il tipo di pratica da generare.
* `template_flusso_dest_id` — il passo iniziale della figlia; vuoto, nessun flusso iniziale. Il passo
  indicato deve essere senza prerequisiti, perché la figlia nasce senza flussi: altrimenti la
  generazione fallisce subito. La regola lo indica nel preset, e la generazione lo ritrova per codice
  nella definizione della figlia. Se il passo viene cancellato, la regola resta, senza passo iniziale.
* `esito_richiesto` — l'esito del flusso che attiva la regola: `POSITIVO`, `NEGATIVO` o vuoto, che vale
  per qualsiasi esito.

⚠️ Il vincolo ammette anche `QUALSIASI`, ma la generazione automatica confronta l'esito richiesto con
quello del flusso, e nessun flusso ha esito `QUALSIASI`: una regola automatica con quel valore non
scatta mai. «Qualsiasi esito» si scrive lasciando la colonna vuota. Per la stessa ragione una regola
non può chiedere gli altri esiti del vocabolario dei flussi (`PARZIALE`, `NON_APPLICABILE`…).

---

### Una regola per combinazione

Per ogni (passo di origine, tipo di destinazione, esito) c'è una sola regola. Un secondo indice unico
copre il caso con l'esito vuoto, che il vincolo unico ordinario non vede perché due valori vuoti non
sono uguali fra loro.

Il passo di origine, il passo iniziale e il tipo di destinazione devono essere attivi.

---

### Esempi

* Passo «Sopralluogo» con esito `POSITIVO` → tipo «Allacciamento», automatica: al completamento
  positivo del sopralluogo nasce la pratica di allacciamento.
* Passo «Verifica» con esito `NEGATIVO` → tipo «Reclamo», manuale: se la verifica fallisce, l'operatore
  può scegliere di aprire un reclamo.

---

{% include-markdown "signature-core.md" %}
