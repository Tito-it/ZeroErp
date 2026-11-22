## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipi_indirizzo_proponibili_natura`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il catalogo dei tipi, una riga per tipo
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto_su_contesto) — la check che legge per ogni tipo
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — il gemello sul soggetto salvato
> * [anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_tipo_ruolo) — il gemello per il ruolo da creare
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipi_indirizzo_proponibili_natura` dice quali tipi d'indirizzo può avere un soggetto che non
esiste ancora, sulla natura di dettaglio scelta nel form: una riga per tipo, ammessa oppure spenta col suo
motivo, e quali sono obbligatori.

---

### Solo la natura

Senza soggetto non ci sono tipi presenti: il solo motivo possibile è il tipo che la natura non ammette. La
check è quella della madre del soggetto, chiamata senza soggetto e senza tipi presenti, col giorno operativo:
il soggetto, una volta creato, accetta i tipi che qui risultano ammessi.

La natura vuota (nessuna natura scelta) o senza matrice propone tutti i tipi, come il guard; una natura che
non esiste non dà nessuna riga.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### ⚠️ Che cosa oggi non copre

* **«Obbligatorio per la natura» non ha una sede unica.** La colonna `obbligatorio` la calcola il picker dalla
  matrice, con lo stesso criterio scritto anche nel picker del soggetto, negli obbligatori mancanti del
  soggetto e nella creazione degli obbligatori del soggetto. Oggi le copie dicono la stessa cosa; una modifica
  a una sola le separerebbe.

---

### Test

* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — su una matrice costruita: una riga per tipo,
  la riga scaduta spenta col motivo, l'obbligatorio (una riga obbligatoria scaduta non lo è), l'ordine; la
  natura senza matrice, la natura vuota, la natura che non c'è.

---

### Note di migrazione

* 2026-11-15 — nasce con il picker del soggetto, per il form di creazione.

---

{% include-markdown "signature-core.md" %}
