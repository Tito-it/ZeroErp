## 📘 Documentazione Concettuale – Tabella `pratiche.competenze_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il tipo di step a cui la competenza si riferisce
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — il reparto della competenza
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — l'operatore abilitato
>
> Approfondimento funzioni:
>
> * [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/funzioni/fn_coda_lavoro_operatore) — la coda di lavoro, che ne ricava il livello competenza
> * [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/funzioni/fn_prendi_in_carico_flusso) — la presa in carico, che ne ricava l'eleggibilità
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — blocca le modifiche quando la definizione è congelata

---

### 🎯 Scopo Principale

La tabella `pratiche.competenze_flussi` è la matrice delle competenze: dice quali operatori, in quale
reparto, sono abilitati a eseguire un tipo di step (template).

È configurazione, gestita dall'amministratore: non contiene dati operativi.

---

### Il modello

Una riga dice: «l'operatore X, nel reparto Y, è abilitato a eseguire gli step del tipo Z». La terna
template, reparto e operatore è unica: la stessa competenza non si duplica.

`attivo` sospende una competenza senza cancellarla (un operatore in ferie, per esempio). Una competenza
può nascere solo verso un template, un reparto e un operatore attivi.

---

### ⭐ La competenza è un lucchetto opzionale

Un template è **sotto competenza** quando ha almeno una competenza attiva: da quel momento lo prendono in
carico solo gli operatori competenti. Un template senza competenze attive non è sotto competenza, e
decide il reparto del flusso, o la presa è libera. Spegnere tutte le competenze di un template lo
libera: non resta un flusso che nessuno può prendere.

⚠️ Il reparto della riga è configurazione e non entra nella decisione: la coda di lavoro e la presa in
carico guardano la coppia template e operatore.

---

### Chi la legge

* `pratiche.fn_coda_lavoro_operatore`, per il livello competenza (i flussi non assegnati che l'operatore
  può prendere) e per sapere quando un flusso del reparto è libero dal lucchetto.
* `pratiche.fn_prendi_in_carico_flusso`, per verificare che l'operatore abbia una competenza attiva
  prima di assegnargli un flusso sotto competenza.

---

### Automazioni

La tabella ha l'audit, il `tx_id` e lo storico delle modifiche. Come gli altri figli di
`pratiche.template_flussi`, non si modifica quando la definizione del template è pubblicata o
congelata: lo impedisce `pratiche.trgfn_template_flussi_figli_guard_immutabile`.

---

{% include-markdown "signature-core.md" %}
