## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto) — la check sul soggetto salvato, che la compone
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — il picker sul soggetto salvato
> * [anagrafiche.fn_tipi_indirizzo_proponibili_natura](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_natura) — il picker sulla natura scelta nel form
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato della natura
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo_su_contesto) — la gemella sullo strato del ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto` dice perché un tipo d'indirizzo non si può scrivere
su un soggetto con un dato contesto: restituisce l'elenco ordinato dei motivi, vuoto se il tipo è ammesso. È la
metà pura della check del soggetto, che la madre e i picker leggono allo stesso modo.

---

### Il contesto, invece del soggetto

Non legge il soggetto: riceve la **natura**, i **tipi** che il soggetto ha già e il **giorno**. Così la stessa
regola serve al soggetto salvato, dove il contesto lo legge la check sul salvato, e al soggetto che non esiste
ancora, dove il picker della natura passa la natura scelta nel form e nessun tipo presente. Il soggetto, quando
c'è, entra solo nel dettaglio dei motivi.

I motivi sono due, nell'ordine: il tipo già presente, poi il tipo che la natura non ammette, col predicato
della natura. Possono esserci tutti e due; chi solleva prende il primo. La natura vuota non dà motivi.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il tipo d'indirizzo o il giorno non sono passati.

I codici dei motivi la funzione non li solleva: li restituisce.

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — su una matrice della natura costruita: il tipo
  ammesso, il tipo già presente, la riga scaduta, i due motivi nell'ordine coi codici a catalogo, la natura
  vuota; i valori del motivo per descrizione.
* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — i picker del soggetto e della natura la
  leggono, e dicono ciò che la madre solleva.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi: la madre del soggetto smette di affidare il tipo già presente
  all'indice unico, e la regola diventa leggibile anche dal picker.

---

{% include-markdown "signature-core.md" %}
