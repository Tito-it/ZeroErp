## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_copia_indirizzo_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — la sorgente e le righe nuove
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_copie_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_copie_indirizzo_ruolo) — le righe sulla destinazione
> * [anagrafiche.fn_indirizzo_elemento_da_riga](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_da_riga) — l'indirizzo della sorgente
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — i tipi che la destinazione ammette
> * [anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto_su_ruolo) — il gemello, dalla riga del soggetto
> * [anagrafiche.fn_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto) — la copia sul soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_copia_indirizzo_ruolo` copia un indirizzo del ruolo in uno o più tipi sulla chiave di destinazione,
il ruolo stesso o una sua istanza, tutto o niente, e restituisce gli id delle righe nuove nell'ordine dei tipi. È il
verbo di «Copia come…» sulle righe del ruolo, nel drawer aperto su un ruolo o su un suo servizio.

Che cosa vuol dire copiare un indirizzo, verso quale chiave e con quali rifiuti, lo dice la sezione «La copia di un
indirizzo» in fondo alla pagina.

---

### Da qualunque chiave del ruolo, verso la chiave aperta

La sorgente può stare sul ruolo o su una qualunque sua istanza; la riga nuova nasce sulla destinazione indicata. Così
l'indirizzo di un servizio si copia sul ruolo, quello del ruolo su un servizio, e quello di un servizio su un altro
servizio dello stesso soggetto. Il tipo si giudica **sulla destinazione**: un tipo che la sorgente ha già sulla sua
chiave si copia, se manca dove la riga nasce.

La destinazione è un parametro obbligatorio senza valore predefinito: un'istanza, o niente per il ruolo.

---

### Che cosa fa questo verbo

1. **Il ruolo** deve esistere, e **la sorgente** dev'essere un suo indirizzo, in qualunque sua chiave.
2. **Le righe** le scrive `anagrafiche.fn_crea_copie_indirizzo_ruolo`, il building block che condivide col gemello dal
   soggetto: una per tipo, dalla singolare del ruolo.

Non c'è un motivo di riga: se la destinazione non ammette nessun tipo, il drawer spegne la copia dal picker della
destinazione, e una copia che arriva lo stesso la rifiuta la singolare col motivo del tipo chiesto.

---

### Codici errore

* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — manca l'indirizzo, o l'elenco dei tipi è vuoto.
* `E_INDIRIZZO_RUOLO_NON_TROVATO` — l'indirizzo non è di quel ruolo.
* Dalla singolare, sulla destinazione: `E_TIPO_INDIRIZZO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE` (anche per
  un tipo ripetuto nell'elenco), `E_TIPO_INDIRIZZO_NON_PERMESSO`, `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`.
* Dal guard della tabella: `E_ISTANZA_ALTRO_SOGGETTO`, per un'istanza di un altro soggetto.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` — dal ruolo a un'istanza, da un'istanza al ruolo, da
  un'istanza a un'altra con tutte le colonne della forma; il tipo presente sulla destinazione e non sulla sorgente; tutto
  o niente su due tipi; l'istanza di un altro soggetto; la sorgente di un altro ruolo; il ruolo che non c'è; l'elenco
  vuoto; gli id nell'ordine dei tipi; la destinazione piena, rifiutata col motivo del tipo; la firma senza destinazione,
  la check e la vista di riga del ruolo che non esistono più.

---

### Note di migrazione

* 2026-11-15 — nasce, con la copia sulla chiave della sorgente e un motivo di riga, calcolato da una check e mostrato da
  una vista di riga gemelle di quelle del soggetto.
* 2026-11-20 — la riga nuova nasce sulla chiave di destinazione, che diventa un parametro obbligatorio: la firma a tre
  argomenti si ritira. La check e la vista di riga si ritirano, perché un motivo uguale per tutte le righe è un motivo
  del drawer, e l'azione `COPIA_INDIRIZZO_RUOLO` si spegne nel registro.

---

{% include-markdown "it/dbzero/anagrafiche/_copia-indirizzo.md" %}

---

{% include-markdown "signature-core.md" %}
