## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il catalogo dei tipi, una riga per tipo
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice del tipo di ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo_su_contesto) — la check che legge per ogni tipo
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — da cui la colonna obbligatorio
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — il gemello sul ruolo salvato
> * [anagrafiche.fn_tipi_indirizzo_proponibili_natura](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_natura) — il gemello per il soggetto da creare
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo` dice quali tipi d'indirizzo può avere un ruolo che non
esiste ancora, sul tipo di ruolo dell'assegnazione e sul soggetto a cui si assegna: una riga per tipo, ammessa
oppure spenta col suo motivo, e quali sono obbligatori.

---

### Il tipo di ruolo e, se c'è, il soggetto

Senza ruolo non ci sono tipi presenti: i motivi possibili sono il tipo che il tipo di ruolo non ammette e il tipo
che la natura del soggetto non ammette. La check è quella della madre del ruolo, chiamata senza ruolo e senza
tipi presenti, col giorno operativo.

* Il **soggetto** non ha un valore di default: vuoto vuol dire soggetto non ancora scelto, e la natura non
  conta. Scelto, la sua natura entra nei motivi e nell'obbligatorio: un privato fornitore vede la sede legale
  spenta.
* Il **tipo di ruolo** vuoto o senza matrice non dà motivi del ruolo, come il guard.
* Un tipo di ruolo o un soggetto passati che non esistono non danno nessuna riga.

Gira coi permessi di chi la chiama.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — legge la check della madre; su una matrice
  costruita il tipo ammesso, il tipo spento col motivo del ruolo, l'obbligatorio; il tipo di ruolo senza
  matrice, vuoto, inesistente.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — col privato la sede legale spenta e la
  fatturazione obbligatoria; col soggetto non ancora scelto la sede legale ammessa; il soggetto che non c'è.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi, sul solo tipo di ruolo.
* 2026-11-16 — prende il soggetto in coda, col fornitore privato: la natura entra nei motivi e nell'obbligatorio.

---

{% include-markdown "signature-core.md" %}
