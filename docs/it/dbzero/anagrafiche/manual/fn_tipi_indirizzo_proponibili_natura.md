## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipi_indirizzo_proponibili_natura`

> **Ultimo aggiornamento**: 24 novembre 2026
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
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_natura) — la colonna obbligatorio
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

### La colonna «obbligatorio» viene dalla sede unica

Se un tipo è obbligatorio lo dice `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura`, nel giorno
operativo: la stessa risposta che leggono i mancanti del soggetto, la copia degli obbligatori e il guard. Una
riga obbligatoria scaduta o spenta non segna il tipo obbligatorio.

---

### Test

* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — su una matrice costruita: una riga per tipo,
  la riga scaduta spenta col motivo, l'obbligatorio (una riga obbligatoria scaduta non lo è), l'ordine; la
  natura senza matrice, la natura vuota, la natura che non c'è.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (2) — nessun picker legge più
  «obbligatorio» dalla matrice da sé: la sede unica è la sola a leggerla.

---

### Note di migrazione

* 2026-11-15 — nasce con il picker del soggetto, per il form di creazione.
* 2026-11-24 — la colonna `obbligatorio` la legge da `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura`:
  prima il picker la calcolava da sé dalla matrice. Il valore non cambia.

---

{% include-markdown "signature-core.md" %}
