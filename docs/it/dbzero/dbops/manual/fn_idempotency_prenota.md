## 📘 Documentazione Concettuale – Funzione `dbops.fn_idempotency_prenota`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.idempotency_keys](/dbzero/dbops/tabelle/idempotency_keys) — le key che la funzione prenota e riprende
>
> Approfondimento funzioni:
>
> * [dbops.fn_idempotency_soglia_secondi](/dbzero/dbops/funzioni/fn_idempotency_soglia_secondi) — la soglia oltre cui una key in corso è abbandonata
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — da dove passano i rifiuti
>
> Guide:
>
> * [Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono) — il meccanismo intero, dal gesto alla scadenza

---

### 🎯 Scopo Principale

Prenota una Idempotency-Key per una richiesta e dice al backend che cosa fare: `ESEGUI` (la key è
sua, esegua l'operazione), `REPLAY` (l'operazione è già fatta: rimandi la risposta salvata),
`IN_CORSO` (la sta eseguendo un'altra richiesta). È la sede unica della decisione; il backend la
chiama in autocommit, prima dell'operazione.

---

### Le regole

| La key… | Risposta |
| --- | --- |
| non c'è | `ESEGUI`, e la key nasce `in_progress`, legata a utente ed endpoint |
| è di un altro utente o su un altro endpoint | rifiuto, `E_IDEMPOTENCY_KEY_RIUSATA` |
| è `completed` | `REPLAY` con la risposta salvata |
| è `failed` | `ESEGUI`: ripresa |
| è `in_progress` entro la soglia | `IN_CORSO` |
| è `in_progress` oltre la soglia, ripresa ammessa | `ESEGUI`: ripresa |
| è `in_progress` oltre la soglia, ripresa non ammessa | `IN_CORSO` |

`IN_CORSO` non è un errore della funzione: è il backend che risponde 409
`E_IDEMPOTENCY_IN_PROGRESS`.

Una ripresa riporta la key a `in_progress` con la nuova richiesta, svuota transazione e risposta e
rinnova `prenotata_at`; utente ed endpoint restano, perché si è appena verificato che sono gli
stessi.

---

### ⭐ La key è di chi l'ha prenotata

Una key arrivata da un altro utente, o su un altro endpoint, non rimanda niente: la risposta salvata
è dell'operazione di qualcun altro. Una richiesta anonima conta come un utente diverso da tutti, non
come un jolly. Nel contesto dell'errore non entrano utente ed endpoint dell'altro: sono proprio ciò
che non va rivelato.

---

### ⛔ La ripresa di una key in corso si dichiara sempre

Una key `in_progress` oltre la soglia vuol dire che chi lavorava è morto senza finire. Riprenderla è
sicuro solo se l'operazione scrive `completed` **nella stessa transazione** del proprio lavoro:
allora una key orfana vuol dire «nessun commit». Il chiamante lo dichiara con
`p_ripresa_ammessa`:

* `true`, operazione in un passo solo: oltre la soglia si riprende;
* `false`, operazione a passi (per esempio una pipeline che salva ogni passo per conto suo): la key
  può coprire un lavoro già salvato in parte, e resta `IN_CORSO` finché scade;
* vuoto: rifiuto. Né sì né no sono un default del modello.

Una key `failed` si riprende sempre, con o senza ripresa ammessa: l'esito l'ha scritto il backend,
e si sa che cosa è successo.

La soglia si legge da `dbops.fn_idempotency_soglia_secondi`, la stessa lettura del presidio del
backend all'avvio; si misura da `prenotata_at`.

---

### Le corse fra due richieste

* La prenotazione di una key nuova è una sola scrittura con conflitto assorbito: di due richieste
  insieme, una scrive e l'altra trova la key.
* Una key già presente si legge bloccandola: due riprese concorrenti non eseguono entrambe, e
  un'operazione che sta scrivendo `completed` si aspetta per l'istante del suo commit.
* Una key cancellata dalla pulizia fra i due passi è di nuovo una key nuova; se intanto un'altra
  richiesta l'ha riscritta, è sua e la risposta è `IN_CORSO`.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — key o endpoint vuoti, oppure `p_ripresa_ammessa` non dichiarato.
* `E_IDEMPOTENCY_KEY_RIUSATA` — la key è stata prenotata da un altro utente o su un altro endpoint.
* `E_CONFIG_MANCANTE` — la soglia di ripresa manca o non è un intero positivo (da
  `dbops.fn_idempotency_soglia_secondi`, solo quando serve leggerla).

---

### Test

* `db/pgtap/dbops/test-idempotency-prenota-v1.sql` — key nuova, key appena prenotata, key di un
  altro utente, di un altro endpoint, di una richiesta anonima; in corso sotto e sopra la soglia,
  con e senza ripresa ammessa; `completed` in `REPLAY`; `failed` ripresa; i rifiuti per key vuota e
  ripresa non dichiarata.
* `db/pgtap/script/test-intero-positivo-da-testo-v1.sql` — la funzione legge la soglia attraverso il
  building block, non con una sua copia della regola.

---

### Note di migrazione

* 2026-10-23 — nasce: la decisione passa dal backend a questa funzione, con il legame della key a
  utente ed endpoint; lo stesso giorno arriva `p_ripresa_ammessa` (`brief-be-verifica-documentazione-api`).
* 2026-10-24 — l'endpoint diventa obbligatorio e la soglia si legge da
  `dbops.fn_idempotency_soglia_secondi`.

---

{% include-markdown "signature-core.md" %}
