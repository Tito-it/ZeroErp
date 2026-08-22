## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_sistemazioni_guard_dati`

### 🎯 Scopo Principale

(rev 2026-08-22)

Che l'atto sia **coerente con se stesso** e con i documenti che nomina.
⛔ Non decide chi può scriverlo: quello è `script.trgfn_guard_emittente_scope`,
montato accanto su **entrambe** le colonne di fattura.

---

### Quattro regole, tre lettori diversi

| | Regola | Chi sbaglia | Codice |
| --- | --- | --- | --- |
| 1 | la **destinazione** vuole i documenti che le servono | l'operatore | `E_SISTEMAZIONE_DOCUMENTI_INCOERENTI` |
| 2 | i documenti sono **dello stesso cliente e della stessa azienda** | l'operatore | `E_SISTEMAZIONE_DOCUMENTI_NON_ABBINABILI` |
| 3 | cliente ed emittente **dichiarati** corrispondono alla fattura | chi ha scritto la chiamata | `E_PAGAMENTI_CHIAMATA_NON_VALIDA` |
| 4 | il **motivo** c'è dove serve | l'operatore | `E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO` |

⭐ La terza ha un codice **tecnico** apposta: l'emittente e il cliente non li
sceglie una persona in un modulo, li **deriva** chi costruisce l'atto. Il lettore
del messaggio è `dbops.error_log`, non l'operatore — *il codice si sceglie da CHI
PUÒ RIMEDIARE.*

### 🔴 Le fatture si leggono FUORI dalla row security

`vendite.fatture` ha la RLS. Un guard è `SECURITY INVOKER`: leggendola
direttamente direbbe *«è di un altro cliente»* **anche quando il cliente è lo
stesso**, solo perché una delle due fatture non si vede.

> ⚠️ È il difetto trovato nel lotto 6, e qui è **prevenuto invece che trovato**:
> la domanda di fatto passa da
> [fn_get_fattura_intestazione](/dbzero/script/funzioni/fn_get_fattura_intestazione),
> che è `SECURITY DEFINER`.

### ⚠️ Ospita anche la regola del centro di compensazione

*«Una contabile di compensazione sta sul centro dedicato»* viveva su
`vendite_contabili`, appesa a `compensazione_id`. Girato il verso (D15-e) quella
colonna è sparita, e con lei il momento in cui la regola poteva scattare: alla
nascita della contabile **non esiste ancora** nessun atto che la citi.

⭐ Si è spostata qui, ed è il posto giusto: la regola dipende dalla
**destinazione**, che è un dato dell'atto. Codice invariato
(`E_CENTRO_NON_ABILITATO_COMPENSAZIONE`): stessa regola, stesso rimedio.

### Regole principali

* Gira in fase **`a20`** e non `a10`: i `BEFORE ROW` vanno in ordine alfabetico, e
  devono parlare prima i due guard di scope (`a10`) e quello di transizione
  (`a15`). ⭐ *«Puoi toccarlo?» → «è ancora aperto?» → «il contenuto sta in piedi?»*
* Si guarda anche in `UPDATE`: l'atto vive, e un guard che parlasse solo
  all'`INSERT` lascerebbe correggere la destinazione senza rileggerne i documenti.
* I due `CHECK` compositi della tabella sono la **rete**, non il presidio: un
  `23514` non dice quale regola è caduta.

---

{% include-markdown "signature-core.md" %}
