## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_titolo_iva_ammesso`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_titolo_iva_tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_titolo_iva_tipi_soggetto_dettaglio) — la matrice che legge
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_tipo_soggetto) — il guard sul titolo
> * [anagrafiche.fn_titoli_iva_non_ammessi](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi) — il lettore del cambio di natura
> * [config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro](/dbzero/config/funzioni/trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro) — il guard del ritiro di matrice

---

### 🎯 Scopo Principale

`anagrafiche.fn_titolo_iva_ammesso` dice se una natura di dettaglio ammette un tipo di titolo IVA: sì se la matrice
ha una riga attiva per la coppia. È la sede unica della domanda, e la fanno tutti e tre i controlli della regola.

---

### Nessuna riga è un no

Una coppia senza riga, o con la riga spenta, non è ammessa; una natura assente non ammette niente. La funzione non
è `STRICT` apposta: una natura assente deve rispondere «no», non «nessuna risposta», perché il lettore del cambio di natura
la usa in una negazione, e lì un valore vuoto lascerebbe fuori il titolo come se fosse ammesso.

Anche il guard del ritiro di matrice la chiama, dopo la modifica: una riga che smette di ammettere fa problema solo
se nessun'altra riga ammette ancora la stessa coppia.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
