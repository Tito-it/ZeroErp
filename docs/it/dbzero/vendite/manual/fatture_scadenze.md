## 📘 Documentazione Concettuale – Tabella `vendite.fatture_scadenze`

> 👀 **Vedi anche**
>
> **Tabelle collegate:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la testata, che porta il termine e il suo snapshot
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — la regola da cui nascono le rate
>
> **Funzioni che la scrivono:**
>
> • [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura) — per una fattura
> • [vendite.fn_genera_scadenze_lotto](/dbzero/vendite/funzioni/fn_genera_scadenze_lotto) — wrapper di lotto

---
### 🎯 Scopo Principale
(latest review 02-08-26)

`vendite.fatture_scadenze` contiene il **piano rate** di una fattura: una riga per
rata, con la sua data e il suo importo. È uno **snapshot**, non un calcolo vivo —
una volta scritto non si ricalcola da solo se il catalogo dei termini cambia.

Serve a tre cose: rendere deterministiche stampe e flussi contabili, reggere sia
la rata unica sia i piani rateali, e conservare la storicità del documento emesso.

---

### 🔁 Chi la scrive, e quando

Le rate **non** si scrivono a mano né con una `INSERT` di dominio. L'unico
scrittore è `vendite.fn_genera_scadenze_fattura`, invocata per lotto dal task
`genera_scadenze_lotto` nello step **EMESSA** della pipeline, in coda a
`ricalcola_iva_lotto`.

L'ordine conta e non è negoziabile: la base di ripartizione è
`fatture.totale_a_pagare`, che prima del ricalcolo IVA non esiste.

**La generazione è idempotente per costruzione**: `DELETE` di tutte le rate della
fattura, poi `INSERT` del piano ricalcolato. Rieseguire ricostruisce lo stesso
piano invece di sommarcisi. La `DELETE` precede i casi a base non positiva, e
questo è voluto: una fattura diventata **interamente coperta da acconti** deve
*perdere* le rate che aveva, non tenersele senza che nessuno lo dica.

---

### 🧮 Come nascono le righe

```text
data_scadenza della rata n = fatture.data + primo_offset_giorni + (n − 1) × intervallo
se il termine ha fine_mese → la data slitta all'ultimo giorno del proprio mese

importo = totale_a_pagare ÷ numero_rate, arrotondato
importo dell'ULTIMA rata = totale_a_pagare − somma delle precedenti
```

La quadratura sull'ultima rata è ciò che rende `Σ importo` **esattamente** uguale a
`totale_a_pagare`, e non una sua approssimazione.

⚠️ **«L'ultima assorbe la differenza» non significa «l'ultima è la più alta».**
La direzione dipende da come arrotonda la divisione, ed è controintuitiva proprio
nei casi che si incontrano oggi:

| Base | Rate | Piano | L'ultima riceve |
| --- | ---: | --- | --- |
| 10,03 | 2 | 5,02 · **5,01** | **meno** — 5,015 arrotonda per eccesso |
| 0,03 | 2 | 0,02 · **0,01** | **meno** |
| 100,00 | 3 | 33,33 · 33,33 · **33,34** | più — 33,3333 arrotonda per difetto |

Con **2 rate** `base/2` finisce sempre per 0 o 5 al terzo decimale: `HALF_UP`
arrotonda quindi sempre per eccesso e la prima rata è **sempre ≥** dell'ultima.
Il verso opposto si vede solo da 3 rate in su — e il catalogo di oggi arriva al
massimo a **2**, quindi la riga con 100,00 illustra la formula ma **non è
riproducibile** senza aggiungere un termine.

Un solo invariante vale in ogni caso: **Σ rate = `totale_a_pagare`, al centesimo.**
Chi scrive un test asserisca quello e i **valori attesi rata per rata**; «le prime
uguali fra loro e l'ultima diversa» con due rate è una frase **vacua** — un insieme
di un elemento è sempre omogeneo — e non distingue «resto sull'ultima» da «resto
sulla prima».

> ⚠️ La formula ha **un ramo solo**, tutto in giorni, dopo la riforma di
> `config.termini_pagamento` del 31-07-2026. Documentazione o codice che nomini
> `tipo_offset` (`G`/`M`/`F`/`N`) o `unita_intervallo` è anteriore a quella data:
> entrambe le colonne non esistono più.

---

### ⚖️ Tre casi in cui zero rate è la risposta giusta

Una fattura **senza rate non è una fattura difettosa**. Su questi casi non va
costruito nessun allarme:

| Base (`totale_a_pagare`) | Esito | Perché |
| --- | --- | --- |
| `= 0` | zero rate, **nessun log** | documento interamente coperto da acconti: è normale |
| `< 0` | zero rate, **log non critico** | saldo a favore del cliente. Il `CHECK (importo >= 0)` aveva già deciso che un documento a credito non si rateizza; il log c'è perché a volte è un fondo configurato male, e la differenza la vede una persona |
| `IS NULL` | **errore** `E_SCADENZE_BASE_NON_PRONTA` | non è un documento particolare: sono i passi eseguiti fuori ordine |

---

### Campi chiave (semantica)

* `fattura_id` → FK alla testata, `ON DELETE CASCADE`.
* `numero_rata` → progressivo da 1, **univoco per fattura**.
* `data_scadenza` → data di esigibilità della rata.
* `importo` → quanto si paga a quella data (`>= 0`).
* `meta` → estensioni JSONB; oggi la generazione vi scrive `modalita_codice` e
  `termine_codice_interno`, cioè con che cosa e in base a quale regola è nata.

---

### 🔒 Vincoli e congelamento

* **PK** `id`; **FK** `fattura_id` con `ON DELETE CASCADE`;
  **UNIQUE** `(fattura_id, numero_rata)`; **CHECK** `importo >= 0`;
  indice su `data_scadenza`.
* **Congelamento oltre la soglia fiscale.** Un trigger di guard impedisce
  `INSERT`/`UPDATE`/`DELETE` sulle rate di una fattura che ha superato
  DRAFT/EMESSA: da lì in poi il documento è uno snapshot fiscale e il suo piano
  rate è quello. La cancellazione in **CASCADE** dalla testata resta però
  ammessa — senza quel ramo una fattura congelata non sarebbe più cancellabile.
  Il generatore intercetta il caso prima, con `E_SCADENZE_FATTURA_BLOCCATA`, così
  l'errore dice la ragione invece di presentarsi come una violazione di trigger a
  metà giro.

---

### 📸 Il piano si spiega da sé

Insieme alle rate, la generazione scrive in testata
`vendite.fatture.termine_pagamento_snapshot`: i **valori** del termine usato —
rate, offset, intervallo, fine mese, arrotondamento — con l'`id` accanto come sola
provenienza.

È la ragione per cui non serve risalire al catalogo per capire un documento
emesso: se domani il termine cambia, quella fattura continua a spiegare le rate
che ha.

---

### Query utili

```sql
-- Piano rate di una fattura
SELECT numero_rata, data_scadenza, importo
  FROM vendite.fatture_scadenze
 WHERE fattura_id = :fattura_id
 ORDER BY numero_rata;

-- Controllo di quadratura (deve dare zero righe)
SELECT f.id, f.totale_a_pagare, sum(s.importo) AS somma_rate
  FROM vendite.fatture f
  JOIN vendite.fatture_scadenze s ON s.fattura_id = f.id
 WHERE f.totale_a_pagare > 0
 GROUP BY f.id, f.totale_a_pagare
HAVING sum(s.importo) <> f.totale_a_pagare;
```

⚠️ Il filtro `totale_a_pagare > 0` nella seconda query **non è un dettaglio**:
senza, le fatture a base zero o negativa — che per progetto hanno zero rate —
comparirebbero come squadrature.

---

### ⚠️ Quello che questa tabella NON è

**Non è uno scadenzario.** Non esiste uno stato di pagamento della rata: la
tabella non ha una colonna di stato, e gli incassi (`pagamenti.vendite_movimenti`)
sono legati alla **fattura**, non alla singola rata — nessuna FK incasso → rata.

Ne consegue che oggi **non sono derivabili** «rata scaduta», «insoluta» o «da
incassare»: su una fattura già incassata sarebbero tutti falsi. Si può elencare il
**piano rate**; uno scadenzario è un'altra cosa, e il modello non può ancora
sostenerlo. Quando la riconciliazione rata ↔ incasso esisterà, il limite cade.

**«Prossima rata» è un concetto temporale, non di pagamento**: la prossima per
data, e se sono tutte passate l'ultima. La regola vive già nel frontend
(`useScadenzeSintesi`) ed è una per tutto il prodotto — chi la ricalcolasse per
conto proprio farebbe dire a due schermate cose diverse sullo stesso documento.

---

### Ruolo nel sistema

`vendite.fatture_scadenze` è la fonte unica della pianificazione di pagamento
della fattura: minimale, congelata insieme al documento, e sempre coerente col
termine che l'ha prodotta perché quel termine viaggia con lei.
