## 📘 Documentazione Concettuale – Funzione `ui.fn_intero_da_jsonb`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — ordine, larghezza e misura scritti nella configurazione
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — ordine dei widget e numero di card
>
> Approfondimento funzioni:
>
> * [ui.fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione) — la usa per giudicare ordine e larghezza alla scrittura
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — la usa per la misura «righe per pagina»
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la usa in lettura, sulle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la usa in lettura, sulle dashboard

---

### 🎯 Scopo Principale

`ui.fn_intero_da_jsonb` risponde alla domanda «questo valore scritto in una configurazione è un
numero intero?»: restituisce il numero, oppure niente. Non solleva mai un errore.

---

### Una domanda, una sede

Le configurazioni di `ui` (le preferenze delle liste e delle dashboard) portano numeri dentro un
campo libero: l'ordine di una colonna, la sua larghezza, le righe per pagina, il numero di card. La
domanda «è un intero?» la fanno sia chi rifiuta una scrittura sbagliata sia chi legge la
preferenza per mostrare la lista o la home. Questa funzione è la sola risposta: il guard di forma,
il guard della misura e i due resolver la chiedono qui, così un valore che la scrittura rifiuta non
può essere onorato dalla lettura, e viceversa.

---

### Che cosa vale come intero

* Vale un numero senza segno scritto con sole cifre, al più nove: resta sempre dentro un intero.
* Non vale una stringa, nemmeno se contiene solo cifre: il testo «25» non è il numero 25.
* Non valgono un numero negativo, un numero con decimali, uno scritto in notazione esponenziale, il
  valore nullo, un oggetto o un elenco: per tutti la risposta è «niente».

Lo zero è un intero: dire se un valore è **ammesso** (positivo, una misura del catalogo, un tetto
fra 1 e 100) resta a chi chiama.

---

### ⭐ Perché non solleva

In lettura un errore di conversione fermerebbe la lista o la home di un utente per una riga scritta
male, magari prima che esistesse il guard. Con «niente» al posto dell'errore il resolver ripiega
sul default del catalogo e la schermata si apre; in scrittura chi chiama trasforma il «niente» nel
proprio rifiuto, con un codice parlante.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — un ordine scritto come stringa rifiutato dal
  guard di forma; i resolver che, su una riga scritta senza il guard, danno all'ordine non intero il
  default del catalogo.
* `db/pgtap/ui/test-misure-pagina-v1.sql` — la misura scritta come stringa rifiutata.

---

### Note di migrazione

* 2026-11-21 — nasce: la stessa domanda aveva tre risposte diverse (il guard della misura voleva un
  numero di sole cifre, il resolver delle liste accettava anche la stringa «25», quello delle
  dashboard un testo di cifre), e le letture dei resolver si fermavano con un errore di conversione su
  una riga malformata.

---

{% include-markdown "signature-core.md" %}
