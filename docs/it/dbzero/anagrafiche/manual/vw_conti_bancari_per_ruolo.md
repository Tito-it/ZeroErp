## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_conti_bancari_per_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — i legami del ruolo, candidate di fonte `RUOLO`
> * [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari) — i legami del soggetto, candidate di fonte `SOGGETTO`
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli su cui le candidate si proiettano
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — il registro, da cui la vista tiene solo i conti attivi
>
> Approfondimento funzioni:
>
> * [script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito) — la scelta di un conto solo, che legge questa vista
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno su cui si misura la validità
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i due legami e la scelta del conto

---

### 🎯 Scopo Principale

`anagrafiche.vw_conti_bancari_per_ruolo` elenca, per ogni ruolo e uso, tutti i conti che oggi si possono usare: quelli
legati al ruolo e quelli legati al suo soggetto. Non sceglie: la scelta di un conto solo la fa
`script.fn_get_conto_bancario_predefinito`.

---

### Una riga per ogni candidata

La vista unisce i due legami e dice da dove viene ogni riga:

* **fonte `RUOLO`** — un legame del ruolo, con la sua istanza di servizio se ce l'ha; `soggetto_ruolo_conto_id` è il
  legame;
* **fonte `SOGGETTO`** — un legame del soggetto, ripetuto per **ogni** ruolo del soggetto; l'istanza è vuota, e
  `soggetto_conto_id` è il legame.

Un ruolo ha quindi tante righe quante sono le sue candidate, per ogni uso: la vista è piatta, non ne tiene una sola.

---

### Che cosa è una candidata

Un legame entra se, nel giorno operativo (la data di oggi nel fuso dell'azienda, da `script.fn_data_operativa`), la
sua validità lo copre (un estremo assente non limita), se non è bloccato, e se il suo conto è attivo. Il resto non
filtra: un legame scaduto, futuro o bloccato resta nelle tabelle, fuori dalla vista.

---

### L'ordine di priorità

Le righe escono ordinate per ruolo e uso, poi su tre gradini: il legame del ruolo con un'istanza, il legame del ruolo
senza istanza, il legame del soggetto. A parità di gradino viene prima il predefinito, poi il legame modificato più di
recente.

L'ordine serve a chi guarda il ventaglio delle candidate e vuole capire perché ha vinto un conto. La funzione di
scelta non si appoggia a questo ordine: filtra per gradino e per uso e ordina da sé, e solo lei passa all'uso
`GENERICO` quando l'uso chiesto non ha candidate.

---

### ⚠️ Che cosa oggi non copre

* **L'ordine non è garantito a chi filtra.** Una query che legge la vista con un suo filtro o un suo join non riceve
  per forza le righe nell'ordine della vista: chi vuole un ordine lo chiede.
* **Il soggetto e il ruolo non sono guardati.** Le candidate non dipendono dallo stato del soggetto, e i legami del
  soggetto si proiettano su ogni suo ruolo, anche su quelli che con un conto non hanno a che fare.
* **I permessi di scrittura.** L'applicazione ha sulla vista anche i permessi di inserire, modificare e cancellare,
  che una vista di unione non può eseguire.

---

### Test

* `db/pgtap/anagrafiche/test_vw_conti_bancari_per_ruolo_gestore.sql` — il legame d'incasso del soggetto di un gestore,
  predefinito, che esce come prima candidata del ruolo, di fonte `SOGGETTO`.
* `db/pgtap/anagrafiche/test-conti-bancari-istanza-cascata.sql` — la vista espone l'istanza dei legami del ruolo.

---

### Note di migrazione

* 2026-03-24 — la vista diventa piatta: prima teneva una riga sola per ruolo e uso, e la scelta di un conto solo
  passa alla funzione.
* 2026-03-25 — la vista espone l'istanza di servizio del legame del ruolo, al posto della utility.
* 2026-10-09 — la validità si misura sul giorno operativo, non sulla data della sessione.

---

{% include-markdown "signature-core.md" %}
