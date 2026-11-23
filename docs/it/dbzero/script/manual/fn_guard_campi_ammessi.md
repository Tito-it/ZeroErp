## 📘 Documentazione Concettuale – Funzione `script.fn_guard_campi_ammessi`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_prima_chiave_estranea](/dbzero/script/funzioni/fn_prima_chiave_estranea) — trova la prima chiave fuori lista
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto, a nome della funzione che lo chiama
> * [magazzino.fn_crea_magazzino](/dbzero/magazzino/funzioni/fn_crea_magazzino) — una delle porte che lo usano
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il controllo dei **campi facoltativi** che una porta di scrittura riceve tutti insieme: devono essere un oggetto, e ogni campo deve stare nella lista che la porta ammette.

È la sede unica di una regola che quindici porte, in tre domini, ripetevano uguale: i building block di nascita, i verbi di modifica di magazzino, la scrittura dei profili d'accesso e degli override, l'elemento di un indirizzo.

---

### ⭐ Il rifiuto nomina il campo

Un campo fuori lista è rifiutato col suo nome, nella frase e nel contesto dell'errore: il backend lo legge e accende proprio quel campo del form. Se i campi estranei sono più di uno, si nomina il primo in ordine alfabetico, così la risposta è sempre la stessa.

---

### Il rifiuto è della porta, non del guard

Chi lo chiama gli passa il proprio dominio, il proprio nome e il proprio contesto (l'id, il codice, il soggetto): nel log l'errore resta della porta che ha rifiutato, e il guard aggiunge al contesto solo la sua chiave.

---

### Che cosa non fa

Non sceglie la lista: la riceve dalla porta, che la legge dalla sede della sua tabella. Una lista vuota non ammette niente.

Non controlla il permesso e non legge tabelle. Il pannello di configurazione non lo usa: rifiuta con un codice suo, che il frontend conosce (`E_PANNELLO_CAMPO_NON_AMMESSO`).

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — i campi non sono un oggetto: chi chiama è rotto. Chi non ha campi da passare manda un oggetto vuoto.
* `E_CAMPO_NON_AMMESSO` — un campo non è nella lista della porta; il codice lo nomina.

---

### Test

`db/pgtap/script/test-fn-guard-campi-ammessi-v1.sql`: la forma, la regola, il contesto nel log, le porte che lo chiamano e il fatto che nessun'altra funzione sollevi da sé `E_CAMPO_NON_AMMESSO`.

---

### Note di migrazione

* 2026-11-23 — nasce dalle copie dello stesso controllo nei `fn_crea_*` di magazzino e anagrafiche, nei verbi di modifica di magazzino e in tre porte di config, che si ritirano nello stesso giro (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "signature-core.md" %}
