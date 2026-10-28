## 📘 Documentazione Concettuale – Funzione `vendite.fn_listino_versione_in_vigore`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [vendite.fn_resolve_prezzo_listino_v2_esito](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito) — il risolutore del prezzo, alla data del documento
> • [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo) — la versione che governa le righe di un contratto o di un'offerta (dal 2026-10-04 la chiedono a lei la lista delle righe, le righe espanse dell'offerta e i guard delle eccezioni)
> • [vendite.trgfn_contratti_freeze_listino_versione](/dbzero/vendite/funzioni/trgfn_contratti_freeze_listino_versione) — la versione fissata all'attivazione del contratto
>
> **Ciò che la rende univoca:**
>
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — vincolo `ex_listini_versioni_no_overlap`
> • [vendite.trgfn_listini_versioni_guard_per_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_per_stato)
>
> **Verifica:** `db/pgtap/vendite/test-listino-versione-in-vigore-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-09-28, `20260928-35`)

**La versione di un listino in vigore a una data**: quella ATTIVA o CHIUSA,
attiva, la cui validità contiene la data. `NULL` se non ce n'è una. La BOZZA non
è mai in vigore («Bug A»: una bozza non è operativa).

---

### ⭐ Perché esiste

La stessa domanda era scritta **sette volte in sei funzioni** e non sempre con
la stessa risposta: cinque ne sceglievano **una** (`ORDER BY stato = 'ATTIVA'
DESC LIMIT 1`), due guardavano **tutte** quelle valide (`EXISTS`). Decisione di
Tid del 2026-09-28: «le versioni valide oggi» — e il buco che rendeva ambigue le
due risposte **si chiude**. Le sette copie sono state ritirate nello stesso giro
(`20260928-36 → -41`, brief-db-liste-righe-documento §8.15).

---

### ⭐ Al più UNA versione, per costruzione

| Regola | Dove |
| --- | --- |
| una versione passa ad ATTIVA → CHIUSA solo a fine validità già passata | `trgfn_listini_versioni_guard_transizione_stato` |
| due versioni **ATTIVE o CHIUSE** dello stesso listino non si sovrappongono | `ex_listini_versioni_no_overlap` (esteso a CHIUSA il 2026-09-28) |
| di una versione **CHIUSA** non si modifica niente, date comprese (rev 2026-10-28) | `trgfn_listini_versioni_guard_per_stato` |

Per questo la funzione **non ordina né limita**: se un giorno le righe fossero
due, il difetto sarebbe il vincolo, e va corretto lì. «Una» e «tutte le valide»
sono la stessa cosa.

⭐ **Risponde anche per il passato**: una versione CHIUSA è in vigore per il suo
periodo. È ciò che serve al risolutore del prezzo, che lavora sulla data del
documento, non su oggi.

---

### Forma

- `STABLE`, `SECURITY INVOKER`: legge con i diritti di chi chiama.
- `plpgsql`, non `LANGUAGE sql`: il presidio dei riferimenti morti compila solo
  il plpgsql.
- `p_data` è `date` esplicito: la data di riferimento del chiamante (oggi o la
  data del documento), non il riflesso di una colonna.

---

{% include-markdown "signature-core.md" %}
