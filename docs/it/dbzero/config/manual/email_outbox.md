## Documentazione Concettuale -- Tabella `config.email_outbox`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_log](/dbzero/config/tabelle/email_log)
> [config.email_template](/dbzero/config/tabelle/email_template)
> [config.email_account](/dbzero/config/tabelle/email_account)
> [config.email_allegato](/dbzero/config/tabelle/email_allegato)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---

### 🎯 Scopo Principale

La tabella `config.email_outbox` contiene le **bozze email** preparate dal sistema e modificabili dall'operatore prima dell'invio. Rappresenta il passaggio intermedio tra la generazione automatica dal template e l'invio effettivo.

---

### Flusso operativo

```
Template renderizzato
  → Bozza DRAFT (oggetto e corpo pre-compilati, editabili)
  → Operatore modifica testo, aggiunge CC, allega file
  → Conferma → stato READY → invio effettivo → stato SENT
  → (oppure) invio NON tentato, di proposito → stato SIMULATA
  → (oppure) invio fallito → torna a DRAFT, perche' l'operatore riprovi
  → (oppure) Annullamento → stato CANCELLED
```

Il dialog "Componi email" nel frontend mostra la bozza con editor HTML, permette modifiche e upload allegati.

#### ⭐ Questa colonna parla di CONSEGNA, non di redazione

Sembra il ciclo di vita di una bozza — e i nomi lo suggeriscono — ma **non lo e'**: lo dice il ramo che su fallimento dell'invio riporta la bozza a `DRAFT`. Una colonna che retrocede quando la consegna fallisce sta descrivendo la consegna.

⇒ Da qui `SIMULATA` (changeSet `20260911-07`, 2026-09-11): quando la mail viene mostrata invece che spedita, la bozza **non e' stata consegnata**, e scrivere `SENT` direbbe il contrario. E' il gemello del valore omonimo su [config.email_log](/dbzero/config/tabelle/email_log), dove sta la spiegazione per esteso.

⚠️ Le due righe sono legate da `email_log_id`: allargare il vocabolario di una sola delle due le avrebbe fatte dissentire sulla **stessa** spedizione, in modo leggibile a occhio nudo.

---

### Ambito di visibilita'

Come per `email_log`, ogni bozza ha un `ambito` (SISTEMA, REPARTO, OPERATORE) che determina chi puo' vederla e modificarla:

* **SISTEMA**: solo admin -- per email di infrastruttura
* **REPARTO**: operatori dell'unita' organizzativa -- per comunicazioni del reparto. Richiede `unita_organizzativa_id` NOT NULL (CHECK constraint)
* **OPERATORE**: solo chi l'ha creata -- per comunicazioni personali

---

### Collegamento a pratica

Il campo `pratica_id` collega la bozza a una pratica. Quando l'operatore clicca "Nuova comunicazione" dalla scheda pratica, la bozza viene creata con `pratica_id` pre-impostato e il template risolto per tipo prestazione + reparto.

---

### Cross-reference con email_log

Dopo l'invio effettivo:

* `email_outbox.email_log_id` punta al record di log creato
* `email_log.email_outbox_id` punta alla bozza di origine

Questa relazione bidirezionale permette di navigare in entrambe le direzioni: dalla bozza al log e viceversa.

---

### Vincoli e regole

* CHECK: `stato IN ('DRAFT', 'READY', 'SENT', 'CANCELLED', 'SIMULATA')` -- `SIMULATA` dal 2026-09-11
* CHECK: `ambito IN ('SISTEMA', 'REPARTO', 'OPERATORE')`
* CHECK: se `ambito = 'REPARTO'` allora `unita_organizzativa_id IS NOT NULL`
* FK NO ACTION su account, template, reparto, pratica
* FK SET NULL su `email_log_id` (cross-reference)
