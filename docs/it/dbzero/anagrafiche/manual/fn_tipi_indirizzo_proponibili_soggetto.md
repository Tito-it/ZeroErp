## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipi_indirizzo_proponibili_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il catalogo dei tipi, una riga per tipo
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura, da cui l'obbligatorio
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto_su_contesto) — la check che legge per ogni tipo
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la madre che accetta ciò che il picker propone
> * [anagrafiche.fn_check_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_copia_indirizzo_soggetto) — la copia, che si spegne quando non resta nessun tipo
> * [anagrafiche.fn_tipi_indirizzo_proponibili_natura](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_natura) — il gemello per il soggetto da creare
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — il gemello sul ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipi_indirizzo_proponibili_soggetto` dice quali tipi d'indirizzo si possono ancora aggiungere a
un soggetto salvato: una riga per tipo, ammessa oppure spenta col suo motivo. Propone ciò che la madre del
soggetto accetta, perché legge la stessa check.

---

### Il contesto letto una volta

Legge dal soggetto la natura e i tipi che ha già, una volta sola, e per ogni tipo del catalogo chiama la check su
contesto col giorno operativo. I motivi possibili sono i due del soggetto: il tipo già presente e il tipo che la
natura non ammette. Un soggetto che non esiste non dà nessuna riga.

Lo leggono il form dell'aggiunta e la check della copia di un indirizzo del soggetto, che si spegne quando
nessun tipo resta ammesso. Gira coi permessi di chi la chiama.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### ⚠️ Che cosa oggi non copre

* **«Obbligatorio per la natura» non ha una sede unica.** La colonna `obbligatorio` la calcola il picker dalla
  matrice (riga obbligatoria che il predicato ammette), con lo stesso criterio scritto anche nel picker della
  natura, negli obbligatori mancanti del soggetto e nella creazione degli obbligatori del soggetto. Sul ruolo lo
  stesso giudizio sta in una funzione sola. Oggi le quattro copie dicono la stessa cosa; una modifica a una
  sola le separerebbe.

---

### Test

* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — legge la check della madre; prima di
  scriverlo un tipo è ammesso, scritto si spegne col codice che la madre solleva; il tipo con la riga scaduta
  spento con lo stesso codice della madre, coi valori natura e tipo; il soggetto che non c'è.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi: i tipi che il form propone li dice il database, sulla regola
  del salvataggio.

---

{% include-markdown "signature-core.md" %}
