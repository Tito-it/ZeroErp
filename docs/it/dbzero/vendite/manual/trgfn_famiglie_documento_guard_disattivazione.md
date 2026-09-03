## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_famiglie_documento_guard_disattivazione`

> 👀 **Vedi anche**
>
> **Il predicato NON è qui, sta in:**
>
> • [script.fn_check_famiglia_documento_disattivabile](/dbzero/script/manual/fn_check_famiglia_documento_disattivabile)
>
> **Approfondimenti tabelle:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
>
> **Che cosa difende:**
>
> • [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)
> • [anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — trigger nato il 2026-09-01)*

**Impedisce di spegnere una famiglia di documento che è ancora la regola di
qualcuno**: che ha registri accesi, o documenti che portano già un numero.

Trigger `trg_famiglie_documento_a10_guard_disattivazione_upd`, `BEFORE UPDATE OF
attivo`.

---

### ⛔ Non difende un catalogo: difende un presidio

Le due funzioni che rispondono *«questo cliente ha già documenti numerati?»*
scorrono le famiglie **attive**. Spegnere una famiglia la fa uscire dal giro, e i
suoi documenti smettono di trattenere il cliente presso l'emittente che li ha
numerati.

⚠️ Nessun errore e nessun diario: il controllo guarda in un posto in meno. È la
ragione per cui questo guard esiste, e non è la coerenza di un elenco.

---

### ⛔ Solo la transizione verso spento

Il predicato è `OLD.attivo AND NOT NEW.attivo`, non `NOT NEW.attivo`.

⭐ **Riaccendere è sempre lecito**: rimette in gioco un presidio, non lo toglie.

---

### ⭐ L'uscita sul no-op, ed è la riga che tiene in piedi la migrazione

`UPDATE OF` scatta quando l'istruzione **nomina** la colonna, anche a valore
invariato — e il mirror CSV delle famiglie riscrive `attivo` **a ogni
migrazione**, con lo stesso valore.

⇒ Senza il confronto fra vecchio e nuovo, **ogni migrazione fallirebbe**. È lo
stesso accorgimento già scritto in
`vendite.trgfn_registri_fatturazione_guard_serie_ammessa`, e qui non è una
raffinatezza: è la condizione per cui la decisione di lasciare i mirror accesi
sta in piedi.

---

### ⭐ Perché chiama la verifica invece di riscriverla

È la regola delle [linee guida SQL §12.5.2](/linee-guida-sql): il guard non
contiene il predicato, lo **chiama**, e solleva il codice del **primo** motivo.

⇒ Il rifiuto del database e il cestino spento nell'elenco non «coincidono oggi»:
**non possono** divergere, perché la regola sta scritta in un posto solo.

---

### ⚠️ Note operative

* **Niente `campo` nel contesto**: l'operatore ha premuto un interruttore, non
  compilato un campo. Quello che non va è la situazione, e il frontend spegne il
  pulsante col motivo invece di accendere un input.
* **Solo `UPDATE`, mai `INSERT`**: una famiglia che **nasce** spenta è legittima
  — si prepara prima, si accende dopo — e non ha figli per definizione. Un guard
  `BEFORE ROW` montato anche in inserimento avrebbe in più il difetto noto di
  **oscurare i `CHECK`** della tabella.
* **`tx_id` NULL e non `NEW.tx_id`**: la fase `_a10_` scatta **prima** del
  trigger che genera il `tx_id`, quindi lì il valore è ancora quello vecchio.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.4.*
