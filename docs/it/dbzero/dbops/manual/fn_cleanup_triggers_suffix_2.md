## 📘 Documentazione Concettuale – Funzione `dbops.fn_cleanup_triggers_suffix_2`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_rename_triggers_by_order](/dbzero/dbops/funzioni/fn_rename_triggers_by_order) — la rinomina che lasciava i suffissi in caso di collisione
> * [dbops.fn_fix_triggers_events_noorder](/dbzero/dbops/funzioni/fn_fix_triggers_events_noorder) — l'altra rinomina della stessa campagna
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger#il-nome-del-trigger) — la regola dei nomi di oggi

---

### 🎯 Scopo Principale

Utility **una tantum** della campagna di rinomina dei trigger del settembre 2025: per ogni
trigger il cui nome finisce in `_2`, doveva togliere il doppione se il trigger col nome base
esiste già, o riprendersi il nome base se è libero. Oggi non la chiama nessun runner, job o
backend: è una **candidata al ritiro**.

Esiste ancora perché il changeSet che la crea, nel primo albero (`db/changelog/migrations/50_dbops`),
gira su ogni database nuovo. Non è mai stata eseguita da un changeSet: quattro doppioni li
toglie a mano, per nome, il changeSet che la segue.

---

### Che cosa fa

* Cerca i trigger utente il cui nome finisce in `_2`, in tutti gli schemi o in quello indicato.
  Il commento del changeSet parla di «tutti gli schemi tranne `public`/`topology`», ma la
  funzione non li esclude.
* Se sulla stessa tabella c'è il trigger col nome base, confronta le due definizioni: se sono
  uguali toglie il doppione, se no lo lascia e lo segnala come conflitto.
* Se il nome base è libero, rinomina il trigger col nome base.
* In anteprima (il default) restituisce quello che farebbe; altrimenti esegue e restituisce
  l'esito di ogni passo, con l'errore nelle note se un passo non riesce.

---

### ⚠️ Il ramo che toglie il doppione non scatta mai

Le due definizioni si confrontano come testo intero, e la definizione di un trigger contiene il
suo **nome**. Il doppione e il trigger base hanno nomi diversi per costruzione, quindi le
definizioni non sono mai uguali: ogni doppione finisce fra i conflitti, e niente si toglie. È
coerente con il changeSet successivo, che i quattro doppioni li toglie a mano.

Anche il controllo sui 63 caratteri del nome base non scatta mai: il nome base è più corto del
nome con il suffisso, che PostgreSQL ha già contenuto nei 63.

---

### ⛔ Perché non si rilancia

* Un nome che finisce in `_2` per una ragione sua (una colonna `…_2`, una seconda variante) viene
  rinominato lo stesso, se il nome base è libero.
* Rinomina anche i `CONSTRAINT TRIGGER` con `ALTER TRIGGER`. Le
  [linee guida dei trigger](/linee-guida-trigger#trigger-differiti-constraint-trigger) avvertono
  che una rinomina così aggiorna uno solo dei due cataloghi.

---

### Note di migrazione

* 2025-09-22 — nasce nel primo albero dei changeSet, dopo le due rinomine della campagna.

---

{% include-markdown "signature-core.md" %}
