## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_handler_eventi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — lo step a cui si lega l'azione
> * [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi) — il registro degli handler
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario di `esito_richiesto`
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — l'alternativa all'handler: lo step avanza sul verdetto del documento
> * [pratiche.azioni_ui](/dbzero/pratiche/tabelle/azioni_ui) — le azioni interattive, un asse ortogonale
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_tfhe_guard_no_proiezione](/dbzero/pratiche/funzioni/trgfn_tfhe_guard_no_proiezione) — uno step non ha insieme handler di completamento e proiezione
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — protegge i collegamenti di un'edizione emessa
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — la copia di un'edizione, che porta con sé i collegamenti

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi_handler_eventi` lega uno step di workflow agli handler da eseguire
quando un suo flusso raggiunge un evento, eventualmente solo con un certo esito: il template dichiara,
il motore esegue per dati.

---

### Evento ed esito

* `evento` è `IN_CORSO` (esecuzione dello step) o `COMPLETATO` (azione di dominio al completamento).
* `esito_richiesto` condiziona l'azione all'esito del flusso: vuoto vale per qualsiasi esito. Il
  vocabolario è quello di `config.esiti_flussi_pratiche`, lo stesso dei prerequisiti e dell'esito dei
  flussi.
* Più azioni sullo stesso evento si eseguono nell'ordine di `sequenza`; `handler_params` sono i
  parametri di quel collegamento.
* Lo stesso collegamento (template, evento, esito, handler) non si ripete, ed esito vuoto conta come un
  valore.
* Una famiglia di documenti nuova, o un evento nuovo, entra come riga di configurazione, non come
  modifica di schema.

⚠️ L'esecuzione dello step all'avvio la dice ancora `template_flussi.handler_id`: questa tabella porta
le azioni degli altri eventi, e i due registri non si sovrappongono.

---

### Chi esegue

L'esecutore è un handler del backend, risolto per chiave dal registro `HANDLER_MAP`: il database tiene
il collegamento, il backend lo esegue al completamento generico del flusso. Il frontend chiama solo il
completamento: l'azione è lato server. È un asse diverso da `pratiche.azioni_ui`, che apre
un'attività interattiva su richiesta dell'operatore.

⛔ **Handler o proiezione, non entrambi.** Uno step che avanza sul verdetto proiettato di un documento non
ha anche un handler di completamento: lo impedisce `trgfn_tfhe_guard_no_proiezione`, e il controllo
gemello sul lato della proiezione.

---

### ⛔ I due registri degli handler devono dire la stessa cosa

Un collegamento attivo cerca la chiave dell'handler in `HANDLER_MAP`. Se la chiave non è registrata, il
completamento dello step fallisce e il flusso non si chiude più.

Il database presidia il suo lato: un collegamento attivo vuole un handler e un template attivi, e un
handler con collegamenti attivi non si spegne. Non può vedere `HANDLER_MAP`. Per questo un handler si
ritira in quest'ordine:

1. si spengono i collegamenti che lo usano, in ogni edizione di workflow;
2. si spegne l'handler in `pratiche.handler_flussi`;
3. solo allora il backend lo toglie da `HANDLER_MAP`.

---

### ⛔ Un cambio sul preset non raggiunge le edizioni già copiate

I collegamenti appartengono, con il loro template, a un'edizione di workflow. La copia di
un'edizione li porta con sé, e una modifica fatta dopo sul preset non arriva alle copie esistenti.

Su un'edizione di un emittente già pubblicata o ritirata i collegamenti non si inseriscono né si
modificano, e su una pubblicata non si cancellano: l'unica strada è una nuova versione, corretta in bozza
e pubblicata. Un cambio di comportamento (per esempio da handler a proiezione) si scrive quindi sul
modello, cioè su tutte le edizioni che hanno quello step, e non sull'id di un template del preset.

---

### Codici errore

* `E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER` — handler di completamento su uno step che avanza per
  proiezione.
* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — modifica di un collegamento di un'edizione emessa.

---

### Test

* `pratiche/test-template-flussi-handler-eventi` — chiavi esterne, vocabolario di evento ed esito, e
  l'handler ritirato senza collegamenti attivi.
* ⚠️ Il divieto di handler e proiezione sullo stesso step non ha un test che lo faccia scattare.

---

### Note di migrazione

* 2026-06-15 — nasce la tabella, per le azioni al completamento; l'esecuzione all'avvio resta su
  `template_flussi.handler_id`.
* 2026-07-01 — il vocabolario di `esito_richiesto` passa da un `CHECK` a una chiave esterna verso
  `config.esiti_flussi_pratiche`.
* 2026-07-06 — l'handler di accettazione del preventivo è ritirato: l'accettazione fa avanzare lo step per
  proiezione, e i suoi collegamenti restano a configurazione spenti.

---

{% include-markdown "signature-core.md" %}
