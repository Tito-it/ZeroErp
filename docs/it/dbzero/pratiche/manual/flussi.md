## 📘 Documentazione Concettuale – Tabella `pratiche.flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica a cui il flusso appartiene
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il template da cui il flusso nasce
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — che cosa deve essere completato prima
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — che cosa genera il completamento
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — gli stati e le transizioni
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario degli esiti
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — la storia di dominio del flusso
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_guard_definizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_definizione) — il template sta nell'edizione della pratica
> * [pratiche.trgfn_flussi_guard_prerequisiti](/dbzero/pratiche/funzioni/trgfn_flussi_guard_prerequisiti) · [pratiche.trgfn_flussi_guard_ripetibilita](/dbzero/pratiche/funzioni/trgfn_flussi_guard_ripetibilita) — se il flusso può nascere
> * [pratiche.trgfn_flussi_guard_transizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_transizione) — i cambi di stato ammessi
> * [pratiche.trgfn_flussi_guard_esito_completato](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_completato) · [pratiche.trgfn_flussi_guard_esito_classe](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_classe) — l'esito al completamento
> * [pratiche.trgfn_flussi_guard_pratica_terminale](/dbzero/pratiche/funzioni/trgfn_flussi_guard_pratica_terminale) · [pratiche.trgfn_flussi_guard_chiusura_prematura](/dbzero/pratiche/funzioni/trgfn_flussi_guard_chiusura_prematura) — i limiti posti dalla pratica
> * [pratiche.trgfn_flussi_generazione](/dbzero/pratiche/funzioni/trgfn_flussi_generazione) · [pratiche.trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica) · [pratiche.trgfn_flussi_calcolo_tempo_completamento](/dbzero/pratiche/funzioni/trgfn_flussi_calcolo_tempo_completamento) — che cosa segue un completamento
> * [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/funzioni/fn_prendi_in_carico_flusso) · [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/funzioni/fn_coda_lavoro_operatore) — l'assegnazione e la coda
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — il completamento dei milestone dal documento
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.flussi` contiene le istanze operative degli step di una pratica: ogni flusso nasce
da un template dell'edizione di workflow della pratica, e ha un suo stato, un suo esito e una sua
assegnazione.

---

### ⭐ Ogni flusso nasce da un template

`template_flusso_id` è obbligatorio: un flusso nasce dal percorso del template o dalla generazione a
valle di un altro flusso, e il flusso «generico» senza template non esiste più. Il template deve
appartenere all'edizione di workflow fissata dalla pratica (`trgfn_flussi_guard_definizione`), deve
essere attivo e non obsoleto.

---

### Quando un flusso può nascere

Prima dell'inserimento, i guard controllano che:

* la pratica non sia in uno stato terminale (`trgfn_flussi_guard_pratica_terminale`, che vale anche per
  le modifiche);
* i prerequisiti del template siano completati, con l'esito richiesto quando la regola lo indica
  (`trgfn_flussi_guard_prerequisiti`): è anche il meccanismo dei bivi condizionali;
* la ripetibilità del template ammetta un'altra istanza nella stessa pratica
  (`trgfn_flussi_guard_ripetibilita`).

---

### Lo stato e l'esito

* Ogni cambio di stato deve essere una transizione ammessa (`trgfn_flussi_guard_transizione`), e il flusso
  di chiusura (il cui template chiude la pratica) non si completa finché la pratica non è chiudibile
  (`trgfn_flussi_guard_chiusura_prematura`).
* `esito` è un codice di `config.esiti_flussi_pratiche`. Al completamento è richiesto
  (`trgfn_flussi_guard_esito_completato`), e la sua classe, verdetto o esito di ramo, deve essere quella
  che la modalità di esito del template ammette (`trgfn_flussi_guard_esito_classe`). `note_esito` lo
  accompagna con testo libero.
* `data_fine` è l'istante di completamento, vuoto finché il flusso non è completato. ⚠️ Nessuna
  funzione del database la valorizza al completamento, nemmeno il completamento automatico di
  `pratiche.fn_reconcile_sorgente`: la scrive chi completa il flusso. Ne dipendono i conteggi di
  `pratiche.calcoli_tempo` e i calcoli di tempo al volo.

---

### Che cosa segue un completamento

Dopo il cambio di stato:

* `trgfn_flussi_generazione` applica le regole di generazione automatiche che corrispondono a template
  ed esito, e genera le pratiche o i flussi a valle;
* `trgfn_flussi_autochiusura_pratica` chiude la pratica quando il lavoro è finito;
* `trgfn_flussi_calcolo_tempo_completamento` apre o chiude i conteggi di tempo;
* il giornale registra il cambio di stato.

---

### Assegnazione e gerarchia

* `risorsa_umana_id` e `unita_organizzativa_id` dicono chi ha in carico il flusso e in quale reparto;
  devono essere attivi. Ogni cambio di assegnazione va nel giornale.
* `flusso_padre_id` lega un sotto-flusso al suo flusso padre; cancellando il padre il legame si svuota.
* `sequenza` è l'ordine dello step nel workflow della pratica.
* `data_scadenza` è la scadenza prevista dello step.

---

### Storia e visibilità

La tabella è storicizzata (`storico.flussi`) e porta `tx_id`. Il giornale registra la nascita, i cambi
di stato e di assegnazione. La regola RLS limita i flussi al perimetro di emittente della pratica.

---

### Test

* `pratiche/test-trigger-guard-flussi` — i guard di nascita e di stato.
* `pratiche/test-guard-pratica-terminale-flussi` — nessun flusso su una pratica terminale.
* `pratiche/test-transizioni-stati`, `pratiche/test-guard-esito-classe`,
  `pratiche/test-ripetibilita-flussi`, `pratiche/test-prerequisiti-esito-aware`,
  `pratiche/test-bivi-condizionali` — transizioni, esiti, ripetibilità e prerequisiti.
* `pratiche/test-trigger-giornale-flussi` — il giornale del flusso.

---

### Note di migrazione

* 2026-06-14 — `template_flusso_id` diventa obbligatorio: il flusso manuale senza template è ritirato.
* 2026-07-01 — l'esito passa da un vincolo di valori a una chiave verso `config.esiti_flussi_pratiche`.

---

{% include-markdown "signature-core.md" %}
