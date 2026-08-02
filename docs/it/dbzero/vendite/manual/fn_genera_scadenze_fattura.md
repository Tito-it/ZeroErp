## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_scadenze_fattura`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le righe che produce
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — da cui **legge** il termine, e dove scrive lo snapshot
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — la regola applicata
>
> **Funzioni:**
>
> • [vendite.fn_resolve_termini_pagamento](/dbzero/vendite/funzioni/fn_resolve_termini_pagamento) — chi **risolve** il termine (non è questa)
> • [vendite.fn_genera_scadenze_lotto](/dbzero/vendite/funzioni/fn_genera_scadenze_lotto) — il wrapper che la invoca per lotto
> • [script.fn_arrotonda_importo](/dbzero/script/funzioni/fn_arrotonda_importo) — l'unico arrotondatore del modello

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_genera_scadenze_fattura(p_fattura_id)` genera — o **ri**genera — il
**piano rate** di una fattura in `vendite.fatture_scadenze`. Restituisce
`(deleted_rows, inserted_rows)`.

È il **produttore unico** di quella tabella: le rate non si scrivono a mano.

---

### 🔴 Legge il termine, non lo risolve

Prende `termine_pagamento_id` **dalla testata**, dove è arrivato passando dalla
chiave di aggregazione. Non risale a nessuna anagrafica.

Non è pigrizia: se lo facesse, esisterebbero **due risolutori** delle condizioni
di pagamento e due risolutori divergono in silenzio. La catena è una sola e vive
in `fn_resolve_termini_pagamento`. Qui un termine mancante è un **difetto a
monte**, non un caso da compensare — e infatti solleva.

---

### 🧮 La formula

```text
data_scadenza rata n = fatture.data + primo_offset_giorni + (n − 1) × intervallo
se il termine ha fine_mese → la data slitta all'ultimo giorno del proprio mese

importo = totale_a_pagare ÷ numero_rate, arrotondato
importo dell'ULTIMA rata = totale_a_pagare − somma delle precedenti
```

**Un ramo solo, tutto in giorni.** Dopo la riforma di `config.termini_pagamento`
(31-07-2026) non esistono più unità diverse: «due mesi» si scrive
`intervallo = 60`. Una formula sola non può divergere da sé stessa.

**Il cavallo d'anno non ha codice dedicato**: `20/12/2026 + 30` dà `19/01/2027`
perché il calendario lo fa PostgreSQL. Nessuna aritmetica a mano, nessun caso
limite da ricordare.

**L'arrotondamento passa da `script.fn_arrotonda_importo`**, il building block
unico, invece di essere la terza copia della stessa tabella di `CASE`.

⚠️ **La quadratura sull'ultima rata non significa «l'ultima è la più alta».** La
direzione dipende da come arrotonda la divisione: con **2 rate** `base/2` finisce
sempre per 0 o 5 al terzo decimale, quindi `HALF_UP` arrotonda per eccesso e
**l'ultima riceve meno** (10,03 → 5,02 · **5,01**). Il verso opposto si vede solo
da 3 rate in su — e il catalogo di oggi arriva **al massimo a 2**. L'unico
invariante sempre vero è **Σ rate = `totale_a_pagare`, al centesimo**.

---

### ♻️ Idempotenza, e perché la DELETE viene prima

`DELETE` + `INSERT`: rieseguire **ricostruisce** lo stesso piano invece di
sommarcisi.

La `DELETE` sta **prima** dei casi a base non positiva, e questo è voluto: una
fattura diventata **interamente coperta da acconti** deve *perdere* le rate che
aveva, non tenersele senza che nessuno lo dica.

---

### ⚖️ I tre casi della base — due non sono errori

| `totale_a_pagare` | Esito | Perché |
|---|---|---|
| `IS NULL` | **errore 571** | passi eseguiti fuori ordine: i totali si calcolano prima |
| `= 0` | zero rate, **nessun log** | documento coperto da acconti: è normale |
| `< 0` | zero rate, **log NON critico** | saldo a favore del cliente. Il `CHECK (importo >= 0)` aveva già deciso che un documento a credito non si rateizza; il log c'è perché a volte è un fondo configurato male, e **la differenza la vede una persona** |

**Una fattura senza rate non è una fattura difettosa.** Su questi due casi non va
costruito nessun allarme.

---

### 📸 Scrive anche lo snapshot del termine

In testata, `fatture.termine_pagamento_snapshot`: i **valori** del termine — rate,
offset, intervallo, fine mese, arrotondamento — con l'`id` accanto come sola
provenienza.

Uno snapshot di soli id non è uno snapshot: se domani il catalogo cambia, la
fattura emessa deve continuare a spiegare le rate che ha.

---

### Errori

| Codice | Quando | Cosa dice davvero |
|---|---|---|
| **570** `E_SCADENZE_TERMINE_MANCANTE` | testata senza termine | difetto a monte: la catena ha un default, non dovrebbe accadere |
| **571** `E_SCADENZE_BASE_NON_PRONTA` | `totale_a_pagare` NULL | i totali si calcolano prima |
| **572** `E_SCADENZE_TERMINE_INVALIDO` | ripartizione non gestita, **o** ultima rata negativa | è il **termine** a essere inconciliabile con quella base, non la fattura |
| **573** `E_SCADENZE_FATTURA_BLOCCATA` | fattura oltre DRAFT/EMESSA | è uno snapshot fiscale: il suo piano rate è quello |

⚠️ Il **572 sull'ultima rata negativa** è una seconda linea che vale la pena
capire: se l'arrotondamento delle prime rate sovra-alloca (metodo `UP` su basi
minuscole), l'ultima diventerebbe negativa e violerebbe
`chk_fatture_scadenze_importo_pos` **a metà giro**, con un errore di vincolo
illeggibile. Intercettarlo prima dà la diagnosi vera. I 9 termini di oggi sono
tutti `HALF_UP`/`UGUALI`, quindi non scatta.

⚠️ Il **573** esiste per lo stesso motivo: oltre soglia la `DELETE` fallirebbe
comunque sul guard dei satelliti, ma con un messaggio che parla di trigger invece
che di documento fiscale.

---
{% include-markdown "signature-core.md" %}
