## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzi_con_obbligatori`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — la plurale del ruolo, che le passa gli obbligatori del ruolo
> * [anagrafiche.fn_crea_indirizzi_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_soggetto) — la plurale del soggetto, che le passa quelli della natura
> * [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento) — la normalizzazione di un elemento, che viene prima
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — gli obbligatori del ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzi_con_obbligatori` completa un elenco di indirizzi coi tipi obbligatori che non ha: per
ognuno aggiunge una copia del primo indirizzo dell'elenco, col tipo sostituito. È la copia automatica degli
obbligatori delle due plurali.

---

### Una regola sola, due matrici

Chi inserisce un soggetto o un ruolo scrive di solito un indirizzo, e il database ne ricava gli altri che il
requisito pretende: la sede legale uguale alla fatturazione, per esempio. La funzione non legge tabelle: riceve
l'elenco, già normalizzato elemento per elemento, e i tipi obbligatori, che ogni chiamante legge dalla sua
matrice (la plurale del ruolo dal requisito del ruolo, quella del soggetto dalla matrice della natura). Così la
regola della copia è la stessa per tutti e due i livelli.

* Una copia per tipo mancante, in ordine di tipo, anche se il tipo compare più volte fra gli obbligatori.
* Un elenco vuoto resta vuoto: senza un indirizzo da copiare non si inventa niente, e sarà il guard a
  rifiutare.
* Un elenco assente vale come vuoto; un tipo obbligatorio assente si ignora.

Chi scrive le righe salta i tipi che il titolare ha già: la funzione guarda solo l'elenco.

---

### ⚠️ Che cosa oggi non copre

* **Il ripiego non ferma la copia.** Si confronta l'elenco col solo tipo richiesto: un elenco che porta già il
  ripiego, che al guard basterebbe, riceve lo stesso la copia del tipo, e il titolare nasce con tutti e due.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` — una copia del primo per ogni tipo che manca,
  in ordine e una per tipo; l'elenco vuoto senza copie; la plurale del soggetto che scrive l'indirizzo e la sua
  copia, e con la copia spenta solo l'indirizzo chiesto.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — la copia sul ruolo di un fornitore privato,
  che segue la natura.

---

### Note di migrazione

* 2026-10-19 — nasce per tenere in un posto solo la copia degli obbligatori, che stava nella plurale del ruolo e
  nell'applicazione.

---

{% include-markdown "signature-core.md" %}
