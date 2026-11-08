## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_pratica_terminale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella sorvegliata
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica padre, di cui si legge lo stato
> * [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche) — la matrice da cui si deriva «terminale»
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_guard_transizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_transizione) — la legalità delle transizioni del flusso
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — che cosa deve essere finito perché la pratica chiuda
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_pratica_terminale` congela i flussi di una pratica
conclusa: quando la pratica padre è in uno stato terminale, non si creano nuovi flussi e non si
modificano quelli esistenti.

La scheda in sola lettura dell'interfaccia è la prima linea; questo guard garantisce che una chiamata
diretta o un batch non aggirino la regola.

---

### «Terminale» si deriva dalla matrice

Uno stato della pratica è terminale quando non ha nessuna transizione attiva in uscita in
`config.transizioni_stati_pratiche`. Nel catalogo di oggi lo sono `CHIUSA` e `ANNULLATA`. La funzione
non conosce nessun codice né id: se si aggiunge uno stato terminale o una transizione, la regola segue
la matrice da sé.

---

### Le regole

* Scatta `BEFORE INSERT OR UPDATE`, riga per riga, su `pratiche.flussi`, nella fase dei guard, su
  tutte le colonne: il congelamento riguarda l'intera riga, anche una modifica del solo esito o delle
  sue note senza cambio di stato.
* Si legge lo stato della pratica padre; se ha almeno un'uscita attiva la pratica è operabile e non
  si blocca niente.
* Se è terminale, l'errore dipende dall'operazione: creazione o modifica, e porta il codice dello stato.
* ⚠️ L'atto di rendere terminale la pratica è un aggiornamento di `pratiche.pratiche` e non passa di
  qui: resta permesso anche con flussi ancora attivi.
* ⚠️ Non c'è cascata dalla pratica ai flussi: chiudendo o annullando una pratica, i flussi attivi
  restano nel loro stato, congelati. Una futura cascata di sistema andrebbe resa esente da questo guard.

---

### Codici errore

* `E_PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO` — inserimento di un flusso su una pratica terminale.
* `E_PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE` — modifica di un flusso su una pratica terminale.

---

### Test

* `pratiche/test-guard-pratica-terminale-flussi` — creazione e modifica bloccate su pratica terminale,
  libere su pratica operabile, chiusura della pratica permessa.

---

{% include-markdown "signature-core.md" %}
