## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_dati_societari_guard_tipo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che il trigger ammette o rifiuta
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura e la sua policy dei dati societari
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_guard_dati_societari_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_dati_societari_required) — l'altra metà: la riga pretesa, al COMMIT
> * [anagrafiche.trgfn_dati_societari_guard_forma_giuridica](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_forma_giuridica) — il guard della forma, che parla prima di questo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_dati_societari_guard_tipo_soggetto` rifiuta i dati societari di un soggetto la cui natura
non li ammette (il privato) o che non ha una natura. Scatta a ogni scrittura della riga, subito.

---

### Che cosa controlla, e che cosa no

* **Il soggetto esiste**: altrimenti `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`, prima che parli la chiave esterna.
* **La natura ha una policy**: un soggetto senza natura non sa se la riga gli spetta, e la riga è rifiutata
  (`E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO`).
* **La policy non è `NONE`**: altrimenti `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`.

Con `OPTIONAL` e `REQUIRED` la riga passa. Che una natura `REQUIRED` abbia davvero la riga non lo controlla
questo trigger, che vede solo le righe scritte: lo controlla
`anagrafiche.trgfn_soggetti_guard_dati_societari_required`, al COMMIT, su `anagrafiche.soggetti`.

Il trigger non rilegge la riga quando cambia la natura del soggetto: il passaggio verso una natura che non
ammette la riga lo ferma il cambio di natura (`E_CAMBIO_NATURA_CON_DATI_SOCIETARI`).

---

### ⚠️ Che cosa oggi non copre

* **Parla per ultimo fra i guard della riga.** Il suo trigger (`trg_dati_societari_guard_tipo_soggetto_ins_upd`)
  non ha la fascia nel nome, e per ordine alfabetico viene dopo quelli del canale e della forma. Per un privato
  con una forma o un canale senza recapito risponde prima uno di quelli, e il rifiuto più radicale, «questa
  natura non ha dati societari», arriva solo per una sezione senza forma.

---

### Codici errore

* `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` — il soggetto della riga non esiste.
* `E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO` — il soggetto non ha una natura, o la natura non ha una
  policy.
* `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO` — la natura non ammette i dati societari.

---

### Test

* `db/pgtap/anagrafiche/test-dati-societari-policy.sql` — il privato rifiutato, la società di persone con e
  senza riga, la società di capitali che la pretende.
* `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` — il privato con la sola data di costituzione,
  rifiutato e non scartato.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
