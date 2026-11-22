## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi del ruolo che soddisfano il requisito
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo, col suo tipo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — il requisito
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il guard, che la legge sulla natura del soggetto
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli) — la lettura del form, sulla natura proposta
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto) — la gemella del livello soggetto

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo` restituisce gli indirizzi obbligatori che mancano a un
ruolo su una natura data, in un giorno dato: i tipi che il requisito chiede e che nessun indirizzo del ruolo
soddisfa, ognuno col ripiego che lo sostituirebbe.

---

### La natura è un parametro

Il requisito si calcola sul tipo del ruolo e sulla natura **passata**, non su quella che il soggetto ha: il
guard le passa la natura del soggetto, la lettura del form quella che un cambio di natura propone. Così la
stessa domanda serve al controllo e a chi prepara il salvataggio, e le due risposte non si separano. Senza
natura, la natura non conta.

Un requisito è soddisfatto da un indirizzo del ruolo del tipo richiesto o del suo ripiego, anche se l'indirizzo
è legato a un'istanza. Un ruolo che non esiste non ha mancanti. Le righe sono ordinate per tipo richiesto: la
prima è quella che il guard solleva.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il guard che legge questa funzione; la
  natura di oggi sul ruolo completo (niente), la natura proposta che chiede un tipo nuovo, il ripiego riportato,
  la natura assente che non conta.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il ruolo a cui la
  cancellazione o il cambio di tipo tolgono un obbligatorio.

---

### Note di migrazione

* 2026-11-17 — nasce estraendo dal guard la domanda «che cosa manca», per darla anche al form del cambio di
  natura.

---

{% include-markdown "signature-core.md" %}
