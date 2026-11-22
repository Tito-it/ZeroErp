## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_forma_giuridica_ammessa`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.forme_giuridiche_tipi_soggetto_dettaglio](/dbzero/config/tabelle/forme_giuridiche_tipi_soggetto_dettaglio) — la matrice delle forme ammesse per natura
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la forma che si giudica
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_dati_societari_guard_forma_giuridica](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_forma_giuridica) — chi la chiama quando si scrive la forma
> * [anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_forma_giuridica_natura) — chi la chiama quando cambia la natura
> * [script.fn_giorno_operativo](/dbzero/script/funzioni/fn_giorno_operativo) — il giorno che i due chiamanti le passano

---

### 🎯 Scopo Principale

`anagrafiche.fn_forma_giuridica_ammessa` dice se una natura di soggetto ammette una forma giuridica in un
giorno dato: vero se la matrice delle forme per natura ha una riga attiva e valida quel giorno per la coppia.

È la sede unica della domanda: la fanno il guard della forma, quando si scrivono i dati societari, e il guard
al COMMIT, quando cambia la natura del soggetto. Con due letture, prima o poi le due strade direbbero cose
diverse.

---

### Che cosa vuol dire «ammessa»

* **Una riga attiva** della matrice per la forma e la natura, con il giorno dentro la sua validità (un estremo
  vuoto è aperto): ammessa.
* **Nessuna riga**, oppure una riga spenta o fuori validità: non ammessa. La matrice elenca ciò che si può,
  non ciò che non si può.
* **Forma o natura assenti**: non ammessa. La funzione non decide che cosa fare di un soggetto senza natura:
  i chiamanti la saltano in quel caso.

Il giorno lo passa chi chiama: i due guard passano il giorno operativo, non la data di calendario.

---

### Test

* `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` — la forma rifiutata su una natura che non
  l'ammette (un ente con la forma SRL), il cambio di natura con la forma vecchia rifiutato al COMMIT e quello
  con la forma nuova che passa.

---

### Note di migrazione

* 2026-10-10 — nasce, come lettura comune ai due guard della forma.

---

{% include-markdown "signature-core.md" %}
