## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_nature_proponibili_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — le nature, una riga ciascuna
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la riga salvata da cui si parte
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — la regola dei motivi
> * [anagrafiche.trgfn_soggetti_guard_cambio_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cambio_natura) — il guard, che legge la stessa regola

---

### 🎯 Scopo Principale

`anagrafiche.fn_nature_proponibili_soggetto` è il picker delle nature di un soggetto: per ogni natura di
dettaglio dice se il soggetto ci può passare e, se no, perché. È la lettura che il form usa per accendere e
spegnere le nature.

---

### Che cosa risponde

Una riga per ogni natura del catalogo, compresa quella attuale (che è sempre ammessa: la natura che non
cambia non ha motivi). Per ciascuna:

* **ammessa** — vero quando la regola del cambio non ha motivi;
* **il codice del primo motivo** — quello che il guard solleverebbe, e che il form mostra accanto alla natura
  spenta;
* **tutti i motivi** — l'elenco intero della regola, per chi vuole spiegarli tutti.

Prima le nature ammesse, poi le altre; dentro ciascun gruppo, per codice. Un soggetto che non esiste non ha
righe.

---

### ⭐ Il picker propone ciò che il guard accetta

Non c'è una lista delle nature «modificabili» calcolata altrove: il picker chiama, natura per natura, la
stessa `anagrafiche.fn_check_cambio_natura_soggetto` che il guard chiama al salvataggio. Una natura accesa
qui passa il guard; una natura spenta qui ha lo stesso primo motivo che il guard solleverebbe.

La regola gira coi permessi di chi chiede: i titoli IVA che nomina sono quelli che chi agisce vede.

---

### La riga salvata, non quella in modifica

Partita IVA e flag del regime PA sono quelli **salvati**. Una natura spenta solo da quei campi (la partita
IVA che la natura nuova non ha, un flag a `S` che non ammette) si accende correggendoli nello stesso
salvataggio: il guard giudica i valori proposti, e lì il motivo non c'è più. Il form lo sa dal codice del
motivo, che è un campo della riga.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il passaggio per la natura vuota.** A un soggetto senza natura il picker propone ogni natura senza i due
  motivi definitivi (la macro-tipologia e i documenti), perché la regola non ha una natura di partenza. Vale
  anche per il soggetto che una natura l'aveva e ci è arrivato svuotandola: con i suoi documenti, gli si
  accendono le nature di un'altra famiglia.

---

### Test

* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — su una società con un documento: la natura
  attuale ammessa, il privato spento col motivo della macro-tipologia.

---

### Note di migrazione

* 2026-11-14 — prende il posto, per il backend, delle nature modificabili calcolate nel servizio dei
  soggetti (la stessa macro-tipologia).

---

{% include-markdown "signature-core.md" %}
