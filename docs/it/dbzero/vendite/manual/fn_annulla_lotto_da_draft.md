## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_lotto_da_draft`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)  
> • [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) — *l'uscita di un documento solo*  

---
### 🎯 Scopo Principale
(latest review 23-09-2026)  
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
* Usa una **GUC di manutenzione** per bypassare il guard di fatturato durante il reset.
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

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_annulla_lotto_da_draft(
  p_lotto_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
