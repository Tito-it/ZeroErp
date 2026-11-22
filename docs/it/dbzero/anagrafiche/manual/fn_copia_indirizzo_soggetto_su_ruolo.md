## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — la sorgente, del soggetto del ruolo
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — le righe nuove, del ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_copie_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_copie_indirizzo_ruolo) — le righe sulla destinazione
> * [anagrafiche.fn_indirizzo_elemento_da_riga](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_da_riga) — l'indirizzo della sorgente
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — i tipi che la destinazione ammette
> * [anagrafiche.fn_copia_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_ruolo) — il gemello, dalla riga del ruolo
> * [anagrafiche.fn_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto) — la copia sul soggetto, nel drawer del soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo` copia un indirizzo del soggetto del ruolo in uno o più tipi del
ruolo, sul ruolo stesso o su una sua istanza, tutto o niente, e restituisce gli id delle righe nuove nell'ordine dei
tipi. È il verbo di «Copia come…» sulle righe del soggetto nel drawer aperto su un ruolo.

Che cosa vuol dire copiare un indirizzo, verso quale chiave e con quali rifiuti, lo dice la sezione «La copia di un
indirizzo» in fondo alla pagina.

---

### ⭐ Nel drawer del ruolo la copia va sul ruolo

Il drawer aperto su un ruolo mostra, in cascata, anche gli indirizzi del soggetto. Copiarne uno è lo stesso gesto della
copia di una riga del ruolo, e va nello stesso posto, la chiave aperta: la riga nuova è un indirizzo del ruolo, non del
soggetto. La sorgente del soggetto resta com'è. Nel drawer aperto sul soggetto, la stessa riga si copia invece con
`anagrafiche.fn_copia_indirizzo_soggetto`.

---

### Che cosa fa questo verbo

1. **Il ruolo** deve esistere, e **la sorgente** dev'essere un indirizzo del soggetto del ruolo.
2. **Le righe** le scrive `anagrafiche.fn_crea_copie_indirizzo_ruolo`, lo stesso building block del gemello dal ruolo:
   una per tipo sulla destinazione, dalla singolare del ruolo. I tipi si giudicano quindi con le regole del ruolo (il
   tipo di ruolo e la natura), non con quelle del soggetto.

Come il gemello, non ha un motivo di riga: se la destinazione non ammette nessun tipo, lo dice il picker della
destinazione.

---

### Codici errore

* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — manca l'indirizzo, o l'elenco dei tipi è vuoto.
* `E_INDIRIZZO_SOGGETTO_NON_TROVATO` — l'indirizzo non è del soggetto del ruolo.
* Dalla singolare del ruolo, sulla destinazione: `E_TIPO_INDIRIZZO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`
  (anche per un tipo ripetuto nell'elenco), `E_TIPO_INDIRIZZO_NON_PERMESSO`, `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`.
* Dal guard della tabella: `E_ISTANZA_ALTRO_SOGGETTO`, per un'istanza di un altro soggetto.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` — dal soggetto al ruolo con lo stesso dettaglio, dal
  soggetto a un'istanza del ruolo, il tipo già presente sulla destinazione, la riga di un altro soggetto, l'istanza di
  un altro soggetto, il ruolo che non c'è, l'elenco vuoto.

---

### Note di migrazione

* 2026-11-20 — nasce. Fino ad allora, nel drawer del ruolo, la copia di una riga del soggetto restava sul soggetto.

---

{% include-markdown "it/dbzero/anagrafiche/_copia-indirizzo.md" %}

---

{% include-markdown "signature-core.md" %}
