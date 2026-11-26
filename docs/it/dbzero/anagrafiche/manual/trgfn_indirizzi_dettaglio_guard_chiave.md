## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico di cui giudica la chiave
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — gira prima, e prepara i valori che si giudicano
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea», che cerca il doppione prima di creare
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e dello stradario

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave` dice che cosa non va nella chiave di un civico, con un
codice e il nome del campo da correggere, invece dell'errore tecnico di un `CHECK` o dell'indice unico.

---

### Le regole

| Regola | Quando | Codice | Campo |
| --- | --- | --- | --- |
| la via si risolve | nascita e modifica | `E_INDIRIZZO_VIA_NON_RISOLTA` | `stradario_id` |
| il civico, se c'è, è maggiore di zero | nascita e modifica | `E_INDIRIZZO_CIVICO_NON_POSITIVO` | `civico` |
| estensione, palazzina, scala, piano e interno hanno almeno una lettera o una cifra | nascita e modifica | `E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE` | la colonna |
| la riga non finisce sulla chiave di un'altra | solo modifica | `E_INDIRIZZO_DETTAGLIO_DUPLICATO` | l'indirizzo intero, che la frase nomina |

* **Una via che non si risolve si rifiuta su ogni strada.** Se la normalizzazione non trova la via nella catena
  comune → provincia → CAP (per esempio un comune senza provincia), la riga non si scrive: lo stesso codice e lo
  stesso campo del «trova o crea», che si ferma prima di cercare, arrivano anche a un inserimento diretto o alla
  modifica di un civico. La regola è la stessa: cambia solo la strada da cui arriva.
* **«Senza numero civico» si dice lasciando vuoto il civico.** Lo zero o un negativo non sono un modo di dirlo:
  sarebbero due chiavi diverse per lo stesso indirizzo.
* **I soli segni non distinguono niente.** `/A`, `-1` (un piano interrato) e `BIS` passano; un valore di soli
  spazi è già diventato nessun valore nella normalizzazione.
* **Il doppione si controlla solo in modifica.** La modifica sul posto vuol dire «correggo l'indirizzo per tutti
  quelli che lo usano», e la frase nomina l'indirizzo che esiste già. Alla nascita il doppione lo cerca il
  «trova o crea», e la corsa fra due sessioni la chiude l'indice: un errore qui, in quella finestra, gli
  toglierebbe la rilettura.

---

### Quando giudica

* In fascia `z10`, dopo la normalizzazione: giudica i valori come si salvano (maiuscolo, vuoto uguale a nessun
  valore, estensione col `/`).
* Una modifica che non tocca la chiave (via, civico e i cinque valori del dettaglio) non si giudica: le righe di
  prima restano valide finché nessuno le tocca, e la riattivazione del «trova o crea» passa senza giudizio.

I `CHECK` `chk_indirizzi_dettaglio_civico_positivo` e `chk_indirizzi_dettaglio_dettaglio_leggibile` e l'indice
`uq_indirizzi_dettaglio_norm_v2` restano come rete per le scritture che non passano dai trigger: il guard è la
sede che parla.

---

### Codici errore

* `E_INDIRIZZO_VIA_NON_RISOLTA` — la via non si risolve nella catena comune → provincia → CAP.
* `E_INDIRIZZO_CIVICO_NON_POSITIVO` — civico zero o negativo.
* `E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE` — un valore del dettaglio fatto di soli segni.
* `E_INDIRIZZO_DETTAGLIO_DUPLICATO` — una modifica che porta la riga sulla chiave di un'altra.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — il guard montato prima di ogni scrittura, il
  civico zero e negativo, i valori di soli segni, piano `-1` ed estensione `/B` accettati, la modifica sulla
  chiave di un'altra riga e quelle che passano.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (9, 10) — l'inserimento diretto di un civico su
  una via di un comune senza provincia, rifiutato con `E_INDIRIZZO_VIA_NON_RISOLTA`, e il «trova o crea» sulla stessa
  via, con lo stesso codice.

---

### Note di migrazione

* 2026-10-25 — nasce insieme alla chiave sulle sette colonne nude e ai due `CHECK` di rete.
* 2026-11-24 — prende la via che non si risolve: prima il codice lo dava solo il «trova o crea», e un inserimento
  diretto o la modifica di un civico cadevano sul vincolo di colonna di `via_norm`.

---

{% include-markdown "signature-core.md" %}
