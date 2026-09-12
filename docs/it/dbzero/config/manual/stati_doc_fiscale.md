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
    ⚠️ **Ha una seconda sede che deve dire la stessa cosa**: la matrice
    `config.stati_doc_fiscale_transizioni` (`ammesso`, `solo_fattura`,
    `meta->>'tipo_lotto'`). Il guard `vendite.trgfn_fatturazione_lotti_guard_stato`
    legge il flag **solo alla prima assegnazione** dello stato; ogni transizione
    successiva passa dalla matrice e il flag non viene riletto. ⇒ Uno stato in cui
    la matrice porta un lotto **deve** avere il flag a `true`, altrimenti il
    catalogo dice il falso senza che niente si fermi. È successo: fino al
    12-09-2026 `ANNULLATA` aveva `applica_lotto = false` mentre `DRAFT → ANNULLATA`
    è ammessa ai lotti (segnalazione del BE; corretto nel CSV, riga 7). Presidio:
    `db/pgtap/config/test-stati-doc-fiscale-applica-lotto-vs-matrice-v1.sql`
    (regola a un verso solo: raggiungibile ⇒ flag; non il contrario — `REGISTRATA`
    ha il flag e nessuna transizione la raggiunge ancora).
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

> ### ✅ ~~E la ricopiano ANCORA~~ → **CHIUSO il 2026-08-30** (`D33`)
>
> Per un giorno la colonna e` esistita con **un solo lettore**: le altre sette
> funzioni tenevano la lista `NOT IN ('DRAFT','EMESSA')` nel proprio corpo. Otto
> copie della stessa frase, e sette non danno errore se ci si dimentica di
> aggiornarle.
>
> ⛔ **Le due copie peggiori erano le guardie di congelamento stesse**
> (~~`trgfn_fatture_righe_guard_congelamento`~~,
> `trgfn_fattura_satellite_guard_congelamento`). ⭐ Dal 2026-08-30 sono **una
> sola**: la prima e` stata riassorbita dalla seconda (`D34`), perche` erano la
> stessa funzione. Una guardia che usa una
> definizione di «congelato» diversa da quella di chi ricalcola lascia il
> documento **congelato per meta` sistema e scrivibile per l'altra** — senza un
> errore e senza una riga di log.
>
> ✅ **Tutte e sette portate a leggere la colonna** con i changeSet
> `20260830-01`…`-07`. ⚠️ Il comportamento **non e` cambiato**: verificato che
> sui sei stati esistenti colonna e lista dicevano la stessa cosa. E` cambiata la
> **sede**, cioe` quante cose vanno toccate il giorno che il confine si sposta —
> da otto a una.
>
> ⚠️ **Il trattamento dello STATO MANCANTE e` rimasto identico funzione per
> funzione**, e non e` lo stesso per tutte: alcune lasciano passare, altre
> bloccano. Uniformarlo sarebbe stato giusto in se`, ma sarebbe stato un
> cambiamento di comportamento **nascosto** dentro un lavoro di sede.
>
> ### ⭐ E il confine e` `DEFINITIVA`, non `EMESSA` (rilievo di Tid)
>
> Da `EMESSA` si **torna indietro**: `EMESSA -> DRAFT` e` una transizione
> **ammessa** su `config.stati_doc_fiscale_transizioni`. `DEFINITIVA` non ha
> ritorno. La colonna lo diceva gia` correttamente; la lista di codici anche —
> ma in otto posti.
>
> ### 🔒 Il presidio
>
> `db/pgtap/config/test-soglia-congelamento-sede-unica.sql`. Quattro casi: che
> **nessuna** funzione porti piu` la lista (e se lo fa, la **nomina**); che le
> otto la leggano davvero; e — i due che contano — che il guard **segua** la
> colonna, in entrambi i versi. Provato per mutazione: sul database di ieri e`
> rosso e nomina tutte e sette.

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
