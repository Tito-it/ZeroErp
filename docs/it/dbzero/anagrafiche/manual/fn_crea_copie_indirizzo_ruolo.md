## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_copie_indirizzo_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — le righe che il building block scrive
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_copia_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_ruolo) — il verbo dalla riga del ruolo
> * [anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto_su_ruolo) — il verbo dalla riga del soggetto
> * [anagrafiche.fn_indirizzo_elemento_da_riga](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_da_riga) — l'elemento che riceve
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la singolare, che scrive ogni riga
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_copie_indirizzo_ruolo` scrive un indirizzo in uno o più tipi su una chiave del ruolo, il ruolo
stesso o una sua istanza, tutto o niente, e restituisce gli id delle righe nuove nell'ordine dei tipi. È la metà comune
dei due verbi della copia verso il ruolo.

---

### ⭐ Perché esiste

I due verbi della copia verso il ruolo cambiano solo la sorgente: una riga del ruolo, o una riga del soggetto del ruolo.
La scrittura sulla destinazione è la stessa, e sta qui una volta: ognuno dei due verbi legge la sua sorgente, ne
ricostruisce l'elemento con `anagrafiche.fn_indirizzo_elemento_da_riga` e lo passa a questa funzione.

---

### Che cosa fa

* **Aggiunge l'istanza** di destinazione all'elemento; senza istanza la riga è del ruolo, e la chiave non si scrive.
* **Scrive una riga per tipo**, nell'ordine dato, con la singolare `anagrafiche.fn_crea_indirizzo_ruolo`: il tipo si
  giudica sulla destinazione. Un tipo ripetuto nell'elenco è già presente al secondo giro, e si rifiuta.
* **Tutto o niente**: un tipo rifiutato non lascia scritti quelli prima di lui.

Non valida i parametri: lo fanno i verbi, prima di chiamarla.

---

### Codici errore

Non solleva codici suoi. Arrivano dalla singolare (`E_TIPO_INDIRIZZO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`,
`E_TIPO_INDIRIZZO_NON_PERMESSO`, `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`) e dal guard della tabella
(`E_ISTANZA_ALTRO_SOGGETTO`).

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` — i due verbi che scrivono da qui, e questa funzione
  che scrive dalla singolare, senza un inserimento suo; tutti i casi dei due verbi.

---

### Note di migrazione

* 2026-11-20 — nasce, con la copia sulla chiave di destinazione e il verbo dal soggetto al ruolo.

---

{% include-markdown "signature-core.md" %}
