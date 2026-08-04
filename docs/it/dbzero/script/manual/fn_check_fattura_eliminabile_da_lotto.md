## 📘 Documentazione Concettuale – Funzione `script.fn_check_fattura_eliminabile_da_lotto`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Elenca i **motivi che impediscono di togliere una fattura da un lotto**. Funzione **pura**
(`fn_check_*`): non solleva errori di dominio e non scrive. Ritorna `[]` quando la fattura
si può togliere.

Sede unica della regola. La legge `vendite.fn_elimina_fattura_da_lotto`, che solleva il
codice del **primo** motivo; il backend può leggerla per **spiegare** invece di far
fallire la chiamata.

---

### I quattro motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `STATO_LOTTO_NON_PRE_FISCALE` | `E_LOTTO_NON_PRE_FISCALE` (831) | il lotto non è in `DRAFT` né `EMESSA` |
| 2 | `FATTURA_NON_COLLEGATA` | `E_FATTURA_NON_COLLEGATA_AL_LOTTO` (832) | la fattura non appartiene a quel lotto |
| 3 | `FATTURA_NON_PRE_FISCALE` | `E_FATTURA_GIA_FISCALE` (833) | la fattura non è in `DRAFT` né `EMESSA` |
| 4 | `FATTURA_NUMERATA` | `E_FATTURA_GIA_NUMERATA` (834) | la fattura ha già un numero |

---

### ⚠️ Il motivo 1 è l'allargamento, non un controllo nuovo

Fino al 2026-08-04 la funzione di mutazione pretendeva il lotto in **bozza**. Il confine
giusto è quello delle due sorelle che lavorano sul lotto intero — **non ancora numerato** —
ed era anche quello che il frontend applicava già: il drawer proponeva la voce di riga su
qualunque lotto con una fattura pre-fiscale, quindi anche sui lotti emessi, dove la
chiamata falliva. Il motivo 1 codifica il confine corretto e chiude quel disallineamento.

### ⚠️ Il motivo 4 è ridondante di proposito: non semplificarlo via

Una fattura in `EMESSA` non è ancora numerata (C-19), quindi il motivo 3 basterebbe a
garantire il 4. Resta lo stesso: cancellare una fattura già numerata aprirebbe un **buco
irreversibile** nella numerazione fiscale, e su un danno irreversibile si guarda il
**fatto** — il numero — non lo stato che dovrebbe implicarlo. Stesso principio di
`script.fn_check_lotto_riportabile_a_draft`.

---

### 🔴 Non è una capability per riga

Il drawer **non** deve chiamarla per ogni riga della lista fatture: ha già in mano lo stato
del lotto e lo stato di ogni fattura, che sono i due campi su cui costruire il gate. Questa
funzione è l'**autorità al momento dell'esecuzione** e la fonte del messaggio, non un
servizio di lista.

---

### Errori sollevati (non di dominio)

* `E_PARAMETRO_INVALIDO` — `lotto_id` o `fattura_id` assenti o `<= 0`.
* `E_LOTTO_NON_TROVATO` / `E_FATTURA_NON_TROVATA` — identificativi inesistenti.

---

### Output (jsonb)

Array (eventualmente vuoto) di `{ codice, reason, reason_key, dettaglio }`.

---

{% include-markdown "signature-core.md" %}
