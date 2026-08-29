## 📘 Documentazione Concettuale – Tabella `config.stati_doc_fiscale`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)     
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)     
>
### 🎯 Scopo Principale
(latest review 23-01-2026)
`config.stati_doc_fiscale` definisce gli **stati documento** utilizzati dal ciclo
fatturazione. Gli stessi stati possono essere applicati sia alle **fatture** sia
ai **lotti**, tramite flag di applicabilita`.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` (progressione di stato).
* **Applicabilita`**:
  * `applica_fattura` → stato valido per `vendite.fatture`.
  * `applica_lotto` → stato valido per `vendite.fatturazione_lotti`.
  * `chiude_lotto` → se `true`, al termine dello step pipeline il lotto viene chiuso operativamente (`stato_operativo=CHIUSO`) tramite processo dedicato.
* **Congelamento fiscale** (dal 2026-08-29):
  * `congela_fiscale` → se `true`, da questo stato in poi il documento e` uno **snapshot
    fiscale**: i valori calcolati non si ricalcolano piu`, si rileggono. `false` = ricalcolo
    ammesso (bozza e lavorazione). Seed: `false` su `DRAFT` ed `EMESSA`, `true` sugli altri
    quattro.
* **Governance**: `attivo`, `meta`.

---

### ⭐ `congela_fiscale`: la soglia era gia` in vigore, ma non era scritta da nessuna parte

Fino al 2026-08-29 il confine viveva come **lista di codici dentro una funzione**:
`vendite.fn_ricalcola_riepilogo_iva_fattura` rifiutava il ricalcolo con
`codice_interno NOT IN ('DRAFT','EMESSA')`.

⛔ **Il problema non era il comportamento, era la sede.** Chiunque scriva un secondo
consumatore della stessa soglia — il risolutore IVA, una stampa, un ricalcolo totali — la
**ricopia**, e due finestre di congelamento sullo stesso documento sono due verita` che
divergono in silenzio.

⚠️ **`DEFAULT true`, e la direzione e` una decisione.** Uno stato futuro che nessuno
classifica **rifiuta** il ricalcolo con un errore parlante, invece di lasciar riscrivere in
silenzio uno snapshot fiscale. E` la stessa direzione che aveva il vecchio `NOT IN`, che per
esclusione congelava d'ufficio ogni stato nuovo: l'unica parte di quella forma che meritava
di sopravvivere.

⛔ **Tre scorciatoie disponibili, tutte e tre sbagliate** — verificate sul seed:

1. **`fase`** non separa niente: `EMESSA` (ricalcolo ammesso) e `DEFINITIVA` (congelata)
   hanno la **stessa** `fase = 'IN_CORSO'`;
2. **`ordine`** (DRAFT 10, EMESSA 20, DEFINITIVA 30) e` la trappola piu` invitante, ma quella
   colonna e` **ordinamento di presentazione**, non un ciclo di vita;
3. ⛔ **`chiude_lotto` non si riusa**, benche` oggi sia `true` esattamente su `DEFINITIVA`:
   risponde a **un'altra domanda**, e il giorno che le due divergono non si separano piu`.

⚠️ La sede del dato e` il CSV `80_data/sql/config/stati_doc_fiscale.csv`: **cambiare la
soglia e` una cella**. Perche` la frase sia vera e` stato ri-ancorato il mirror
(`20260829-05`), che ne dichiarava dieci colonne su tredici — `fase`, `is_abortito` e
`congela_fiscale` non erano governate dal CSV, e nessuno se ne sarebbe accorto.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, D15 / I10.

---

### Regole operative

* Gli stati **possono essere condivisi** tra lotto e fattura, ma vanno marcati con i flag.
* Le **transizioni ammesse** sono definite in `config.stati_doc_fiscale_transizioni`.
* `chiude_lotto` deve avere cardinalita` **esattamente 1** (una sola riga `true`).

---

{% include-markdown "signature-core.md" %}
