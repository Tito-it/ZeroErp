## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — il requisito che interroga
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — la copia degli obbligatori
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — il picker di un ruolo salvato
> * [anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_tipo_ruolo) — il picker di un ruolo da assegnare
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo` dice se un tipo d'indirizzo è obbligatorio per un tipo
di ruolo, su un soggetto di una natura data, in un giorno dato: vero quando è uno dei tipi che il requisito del
ruolo chiede.

---

### Obbligatorio vuol dire «richiesto», non «presente in una riga obbligatoria»

La risposta viene dal requisito (`anagrafiche.fn_indirizzi_obbligatori_ruolo`), non dalla matrice: il tipo di
una riga obbligatoria che la natura vieta **non** è obbligatorio, mentre lo diventa il ripiego della riga,
quando il ruolo e la natura lo ammettono. Un ripiego che basta al posto del tipo, quando la natura ammette tutti
e due, non è obbligatorio: è un'alternativa. Senza natura, la natura non conta.

La leggono la copia degli obbligatori di `anagrafiche.fn_crea_indirizzi_ruolo` e la colonna «obbligatorio» dei
due picker del ruolo: ciò che si copia e ciò che il form segna obbligatorio è ciò che il guard pretende.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — i tre lettori che leggono questa funzione;
  su una riga costruita, la natura che ammette il tipo (obbligatorio), quella che non lo ammette (non
  obbligatorio), la natura assente (obbligatorio); i picker e la copia sul fornitore privato.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — sul privato è obbligatorio
  il ripiego e non il tipo; il picker del ruolo da assegnare segna il ripiego.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la plurale del ruolo che legge gli obbligatori
  attraverso il building block.

---

### Note di migrazione

* 2026-11-17 — legge il requisito di `anagrafiche.fn_indirizzi_obbligatori_ruolo` e prende la natura del soggetto
  fra i parametri: prima guardava la sola matrice del ruolo.

---

{% include-markdown "signature-core.md" %}
