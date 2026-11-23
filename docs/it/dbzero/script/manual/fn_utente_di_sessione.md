## 📘 Documentazione Concettuale – Funzione `script.fn_utente_di_sessione`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_current_identita_context](/dbzero/script/funzioni/fn_current_identita_context) — gli altri tre valori di sessione dell'identità
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto, a nome della funzione che legge
>
> Guide:
>
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — chi scrive e chi legge i valori di sessione

---

### 🎯 Scopo Principale

Dà l'utente della richiesta: l'id che il backend scrive nella sessione (`app.current_user_id`) a ogni
chiamata autenticata. Ogni funzione e ogni vista del database che ha bisogno di sapere chi sta agendo
lo legge da qui, invece di convertire il valore da sé.

---

### Che cosa risponde

* **L'id dell'utente**, se la sessione ne porta uno.
* **Niente** (`NULL`) se la sessione non ha un utente: un comando, un job, una corsa senza
  autenticazione. Che cosa voglia dire, lo decide chi legge: un verbo di scrittura rifiuta, una
  ricerca toglie le colonne sensibili.
* **Un errore** se la sessione porta qualcosa che non è l'id di un utente: lettere, segni, spazi, zero,
  zeri in testa, un numero oltre il massimo. Nessuna interfaccia lo scrive così: è rotto il chiamante,
  e l'operatore non ha niente da correggere.

---

### Il rifiuto nomina chi leggeva

Chi la chiama passa il proprio nome. Il messaggio e il log dicono quale funzione ha trovato il valore
sbagliato, e il contesto del log riporta il valore com'era scritto.

---

### Una sede sola

Prima ogni funzione convertiva il valore per conto suo: un valore sbagliato dava un errore grezzo di
PostgreSQL senza codice, e una sola funzione di `ui` aveva un controllo suo, con un codice diverso. Ora
la regola sta qui, e un test del catalogo diventa rosso se una funzione o una vista torna a leggere il
valore da sé.

Le policy RLS leggono ancora il valore da sé, con la conversione descritta nel
[contratto delle GUC](/guide/contratto-guc-app).

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — la sessione porta un valore che non è l'id di un utente.

---

### Test

`db/pgtap/script/test-fn-utente-di-sessione-v1.sql`: la forma, le risposte (sessione senza utente,
un id, il massimo), i valori rifiutati, il nome di chi legge nel messaggio, e il presidio del catalogo:
nessuna funzione e nessuna vista legge il valore da sé, salvo un elenco chiuso di eccezioni, ciascuna
col suo motivo.

---

### Note di migrazione

* 2026-11-23 — nasce dalle copie della stessa conversione in una sessantina di funzioni e quattro viste
  di `script`, `ui`, `anagrafiche`, `catalogo`, `config`, `dbops`, `pagamenti` e `vendite`, che passano
  qui nello stesso giro; `magazzino` subito dopo (`brief-db-revisione-ui`, giro 8).

---

{% include-markdown "signature-core.md" %}
