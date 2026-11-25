## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_lotto_da_draft`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) · [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) — il lotto e le sue fatture
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) · [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) · [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva) — le fatture che si cancellano
> * [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log) · [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture) — log e note della fattura
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività che tornano libere
> * [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti) — gli esiti, che diventano `ESCLUSO`
>
> Approfondimento funzioni:
>
> * [vendite.fn_guard_passaggio_lotto](/dbzero/vendite/funzioni/fn_guard_passaggio_lotto) — il permesso del passaggio verso l'annullo
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — la pulizia, riservata
> * [vendite.fn_cambia_stato_lotto](/dbzero/vendite/funzioni/fn_cambia_stato_lotto) — il verbo che scrive lo stato del lotto, dopo la pulizia
> * [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili) — chi aveva bloccato le attività
> * [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) — l'uscita di un documento solo
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — le vie d'uscita da un lotto, e chi le può prendere

---
### 🎯 Scopo Principale

La funzione **`vendite.fn_annulla_lotto_da_draft()`** effettua il **rollback tecnico**
di un lotto in stato **DRAFT**, eliminando i documenti generati dal draft,
ripristinando le righe di `attivita_fatturabili` e **chiudendo** il lotto
portandolo ad **ANNULLATA**.

⭐ **Un lotto annullato è vuoto** (decisione di Tid, 23-09-2026). Tutto ciò che il
giro aveva in corso viene risolto o riportato allo stato di prima: le fatture
cancellate, le attività liberate, le corse dei task chiuse, e ogni documento
**esce dal giro**. Da lì nessun controllo ha bisogno di escludere un lotto
annullato: non c'è più niente da segnalare.

> ⚠️ **Da non confondere con la sorella.**
> [`fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft)
> fa la stessa pulizia ma **lascia il lotto vivo** e lo rimette in bozza perché
> riparta. Questa invece lo **chiude**: il lotto non lavorerà più.

---

### Chi la chiama, con quale permesso e su quale lotto

È il verbo dell'endpoint «annulla lotto». Gira come proprietario (`SECURITY DEFINER`), fuori dalla
row security, quindi perimetro e permesso li controlla lei, all'ingresso e in quest'ordine:

1. **il perimetro**, sul lotto **e** su tutte le sue fatture, con una lettura sola: devono essere di
   un'azienda di chi agisce. Il controllo è doppio perché il modello non lega la fattura all'azienda
   del lotto. Fuori dal perimetro il lotto «non c'è» (`E_LOTTO_NON_TROVATO`, la stessa risposta di
   un lotto inesistente), anche se fuori è una fattura sola, e prima di dire qualunque cosa sul suo
   stato;
2. **il permesso** del passaggio verso lo stato d'annullo
   ([`vendite.fn_guard_passaggio_lotto`](/dbzero/vendite/funzioni/fn_guard_passaggio_lotto)). Viene
   dopo la lettura del lotto perché dipende dal suo stato. La riga `DRAFT → ANNULLATA` non dichiara
   un'azione, quindi conta il livello `TUTTO` sull'area `vendite`, lo stesso controllo
   dell'endpoint. Sotto il livello: `E_PERMESSO_NEGATO`.

Il permesso arriva **prima** della pulizia: un rifiuto non lascia lavoro fatto e poi annullato.

**Le porte.** Il verbo spegne all'ingresso la GUC del reset del lotto e quella delle righe
contabili. La porta del reset la riapre solo la pulizia, mentre lavora, e la richiude prima di
uscire. Lo stato d'annullo che il verbo scrive dopo, con
[`vendite.fn_cambia_stato_lotto`](/dbzero/vendite/funzioni/fn_cambia_stato_lotto), lo giudica il
guard di transizione del lotto.

---

### Regole principali

* Ammesso per `tipo_lotto` **MASSIVO** e **GIORNALIERO** (dal 02-08-2026: un giro
  giornaliero interrotto deve poter tornare indietro come uno massivo).
* Ammesso **solo** se `stato_doc_fiscale = DRAFT`.
* Tutte le fatture del lotto devono essere **pre-fiscali**, cioè in **DRAFT** o
  **EMESSA** (dal 02-08-2026): pre-fiscale significa non numerata, quindi
  cancellabile. Restringerlo alle sole DRAFT renderebbe non annullabile un lotto
  tornato in bozza con dentro una fattura marcata critica, che resta EMESSA.
* Aggiorna il lotto:  
  * `stato_doc_fiscale = ANNULLATA`  
  * `stato_operativo = CHIUSO`  
  * ⛔ **`stato_lotto` non si tocca** (dal 07-09-2026). Fino a quel giorno
    l'annullo ci scriveva `COMPLETATO`, e un lotto fallito smetteva di dire di
    esserlo. `stato_lotto` racconta com'è andata l'elaborazione; che il lotto
    sia chiuso lo dicono le due colonne sopra.
* **Chiude le corse dei task** del lotto con esito `ANNULLATO` (dal 04-09-2026),
  così un lotto annullato non resta fra gli errori vivi del cruscotto.
* ⭐ **Fa uscire dal giro ogni documento** (dal 23-09-2026): ogni esito di
  `fatturazione_lotti_esiti` non ancora `ESCLUSO` diventa `ESCLUSO`, con il
  motivo *«Annullo del lotto &lt;codice&gt;»*. Chi e quando li scrive il
  database. Vale per **tutti** gli esiti, anche quelli andati bene: senza più
  fatture, un documento «completato» direbbe il falso. Il giornale del lotto
  riceve una riga informativa (`ANNULLO_LOTTO`) col numero di documenti usciti.
  * ⚠️ La sorella `fn_riporta_lotto_a_draft` **non** lo fa, ed è giusto: il
    suo lotto resta vivo, e il giro successivo riscrive gli esiti da sé.
* Elimina:  
  * note fatture e note righe  
  * `fatture_riepiloghi_iva`  
  * `fatture_righe`  
  * `fatture_log`  
  * link `fatturazione_lotti_fatture`  
  * testate `fatture`
* Ripristina `attivita_fatturabili` (unlock + reset flags).
* Cleanup centralizzato tramite `vendite.fn_cleanup_fatture_by_ids`.
* La pulizia apre la porta del reset del lotto solo mentre lavora, e solo perché gira come
  proprietario (sezione «Chi la chiama»).
* I log di lotto (`fatturazione_lotti_log`) **non** vengono eliminati.

---

### Output

Ritorna una riga con:

* `updated_lotti`
* `updated_attivita`
* `deleted_fatture`
* `deleted_righe`
* `annullati_task_run`

Il numero di documenti usciti dal giro **non** è in questa riga: il backend la
legge per posizione, e una colonna in più sarebbe un cambio di contratto. Lo
dice la riga `ANNULLO_LOTTO` del giornale.

---

### Codici errore

* `E_LOTTO_NON_TROVATO` — il lotto non esiste, oppure il lotto o una sua fattura sono fuori dal
  perimetro di chi agisce.
* `E_PERMESSO_NEGATO` — manca il livello `TUTTO` sull'area `vendite`.
* I motivi di `script.fn_check_lotto_annullabile`, se il lotto non si può annullare.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: il verbo è
  `SECURITY DEFINER`; con l'area a `LETTURA` risponde `E_PERMESSO_NEGATO`; il lotto di un'altra
  azienda risponde `E_LOTTO_NON_TROVATO` e resta com'era; col permesso l'annullo riesce anche con la
  GUC accesa davanti, e dopo il verbo la GUC è vuota.
* `db/pgtap/vendite/test-annulla-lotto-non-riscrive-stato-v1.sql`,
  `db/pgtap/vendite/test-annulla-lotto-task-runs-v1.sql`,
  `db/pgtap/vendite/test-annulla-lotto-vuoto-v1.sql` — che cosa fa l'annullo.

---

### Note di migrazione

* 2026-11-25 — `SECURITY DEFINER`: il perimetro su lotto e fatture all'ingresso (prima lo dava la
  row security), il permesso del passaggio prima della pulizia e con la ricaduta sull'area (prima
  arrivava dopo, da `fn_cambia_stato_lotto`), le porte spente all'ingresso
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7, D-X a, D-Y a).

---

{% include-markdown "signature-core.md" %}
