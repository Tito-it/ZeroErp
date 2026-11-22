## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzi_obbligatori_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — le righe obbligatorie del tipo di ruolo, col ripiego
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_ruolo) — il tipo ammesso dal ruolo
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il tipo ammesso dalla natura
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_ruolo) — il requisito confrontato con gli indirizzi del ruolo
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — la domanda su un tipo solo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzi_obbligatori_ruolo` calcola il requisito degli indirizzi obbligatori di un tipo di
ruolo su una natura di soggetto, in un giorno dato: una riga per ogni tipo richiesto, col ripiego che lo
sostituisce quando vale.

---

### Che cosa restituisce

* **`tipo_indirizzo_id`** è il tipo che il ruolo deve avere: quello della riga di matrice se la natura lo
  ammette, altrimenti il ripiego della riga, che ne prende il posto.
* **`ripiego_tipo_indirizzo_id`** è il tipo che basta al posto del richiesto: il ripiego della riga, quando la
  natura ammette il tipo e il ruolo e la natura ammettono anche il ripiego; vuoto quando il ripiego è già il
  tipo richiesto o non vale.

Le righe sono ordinate per tipo richiesto. La funzione non legge né soggetti né indirizzi: dice che cosa un
ruolo di quel tipo, su quella natura, deve avere, e chi la chiama lo confronta con ciò che c'è. Il giorno è
un parametro, perché chi chiama sceglie quello del suo controllo (i guard usano il giorno aziendale).

---

### ⭐ La sede unica del requisito del ruolo

Nessun altro oggetto legge le righe obbligatorie della matrice del ruolo: la leggono attraverso questa
funzione i mancanti (e quindi il guard e il form del cambio di natura), la domanda su un tipo solo (e quindi la
copia degli obbligatori e i picker) e la fixture dei pgTAP che crea un ruolo completo
([dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo)). Il presidio
pgTAP verifica che nessun lettore ne abbia una copia.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — i lettori che non leggono
  la matrice; su una matrice costruita, il tipo col ripiego sulla società, il ripiego da solo sul privato, la
  natura assente, la riga che non chiede niente quando la natura vieta anche il ripiego.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il requisito letto dai mancanti sulla
  natura proposta.

---

### Note di migrazione

* 2026-11-17 — nasce come sede unica del requisito del ruolo, che passa a dipendere dalla natura del soggetto
  («vale il ripiego»).

---

{% include-markdown "signature-core.md" %}
