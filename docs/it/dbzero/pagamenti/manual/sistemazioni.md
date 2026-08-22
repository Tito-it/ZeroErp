## 📘 Documentazione Concettuale – Tabella `pagamenti.sistemazioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)
> • [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare)
>

### 🎯 Scopo Principale

(rev 2026-08-22 — nasce rinominando `pagamenti.compensazioni`)

Il **registro** delle sistemazioni: *che cosa si è deciso di fare di
un'eccedenza, e che cosa ne è venuto fuori.*

⭐ Si legge insieme alla sua vista, e la coppia è il senso di tutto il processo:

```text
vw_eccedenze_da_sistemare   →  che cosa c'è DA FARE
sistemazioni                →  che cosa è STATO FATTO
```

---

### ⭐ Tre destinazioni, e nessuna macchina nuova sotto

| `destinazione` | Che cosa significa | Che cosa genera |
| --- | --- | --- |
| `RIPORTO` | il credito va su un'**altra fattura** del cliente | un **fondo fattura** `origine = MANUALE` |
| `RIMBORSO` | il denaro **esce**, al cliente | una **distinta a importi negativi** |
| `COMPENSAZIONE` | si mette insieme il credito di un documento col debito di un altro | una **distinta sul centro dedicato**, con **due righe che sommano a zero** |

⭐ Il punto di D15-a: **i meccanismi esistevano già tutti e tre**. Mancavano
l'elenco e il registro — *prima di dimensionare un lavoro, contare quanto ne è
già costruito da altri cantieri.*

---

### Il percorso, che è cortissimo

```text
BOZZA ──► CONFERMATA    (l'atto diventa un FATTO: genera il documento)
  └────► ANNULLATA      (la decisione si scarta, e resta scritta)
```

⚠️ Entrambi gli esiti sono **terminali**, e da `CONFERMATA` non si torna perché
**il denaro si è già mosso**: la correzione è una sistemazione **nuova**. È la
stessa regola della distinta contabile chiusa.

⛔ **Non c'è una tabella-matrice** come per le contabili, e non è una
dimenticanza: tre stati e due passaggi sarebbero due righe che nessuno
interroga, e le azioni del frontend **sono i due verbi**. La regola vive in
`trgfn_sistemazioni_guard_transizione`, e il codice errore la nomina per esteso
perché chi la cerca nei dati non la trova.

---

### Campi chiave (semantica)

* `destinazione` · `stato` — vocabolari chiusi, entrambi con `CHECK`.
* `importo` — quanto si sistema. ⚠️ **Non** necessariamente tutta l'eccedenza: si
  può rimborsare una parte e riportare il resto, ed è il motivo per cui su una
  fattura possono esistere più sistemazioni.
* `fattura_origine_id` — il documento **che ha l'eccedenza**.
* `fattura_destinazione_id` — dove va il denaro. ⚠️ Obbligatoria su `RIPORTO` e
  `COMPENSAZIONE`, **vietata** su `RIMBORSO`: in un rimborso il denaro esce dal
  sistema e un secondo documento non esiste. E non può coincidere con l'origine.
* `cliente_soggetto_ruolo_id` — ⭐ sta qui perché la decisione si prende
  **guardando il cliente** (D15-b): compensare significa mettere insieme due
  documenti **suoi**.
* `emittente_soggetto_ruolo_id` — è il **perimetro**, e la policy RLS lo legge
  direttamente (mirror di `vendite.fatture`). Non è una denormalizzazione comoda:
  una sistemazione sta dentro un solo emittente **per natura**.
* `contabile_id` / `fondo_source_id` — **l'esito**, e sono **due** colonne.
* `data_esecuzione` / `user_esecuzione` — quando l'atto è diventato un fatto.
* `motivo` — ⚠️ obbligatorio su `ANNULLATA` e su `RIPORTO`.

---

### ⭐ Perché due colonne di esito e non una polimorfa

Le tre destinazioni producono **due specie diverse** di oggetto: un fondo, oppure
una distinta. Una colonna sola avrebbe richiesto un «tipo» accanto per sapere
dove guardare — cioè `destinazione` scritta due volte. Così invece ciascuna porta
la **sua** chiave esterna vera, e un `CHECK` le lega alla destinazione.

### 🔴 Il legame con la contabile sta QUI, ed è la decisione D15-e

Fino al 2026-08-22 il legame andava **dalla contabile all'atto**
(`vendite_contabili.compensazione_id`). Ma nel giro reale è l'**atto a generare**
la contabile:

```text
la vista mostra un'eccedenza
   → una PERSONA sceglie la destinazione
   → l'atto si registra qui
   → alla conferma GENERA una contabile (o un fondo)
   → la contabile registrata genera i MOVIMENTI
```

Girandolo, su `vendite_contabili` sono spariti **la colonna, la sua FK e il suo
unico**, e da `fn_get_or_create_vendite_contabile` il parametro
`p_compensazione_id`. ⭐ **Meno pezzi, non di più** — e l'unicità *«una contabile
per atto»* non si è persa: ha cambiato lato (`uq_sistemazioni_contabile`).

⚠️ Costo zero: **zero righe** ovunque, e nessuna riga di codice in `backend/` o
`frontend/` nominava la tabella o la colonna.

### ⚠️ Il nome, e perché non è `compensazioni` né `regolazioni`

Chiamare «compensazione» un bonifico di rimborso sarebbe **falso**: se la tabella
copre tre azioni, il nome deve dirlo. ⛔ E non `regolazioni`, che in contabilità
sarebbe la parola più esatta: in un ERP per le **utilities** «regolazione»
significa un'altra cosa, e *un nome che in un dominio vuol dire due cose è un
nome che confonde.*

### 🔒 Chi la vede

Policy `rls_sistemazioni_ef_whitelist`, `FOR ALL`, gate `OPERATORE` fail-closed —
il mirror esatto di `rls_fatture_ef_whitelist`. ⭐ È il pezzo più semplice del
perimetro incassi: l'emittente è **sulla riga** e non va cercato, perché qui
l'atto nasce da una **decisione** e chi decide sa già per chi.

---

{% include-markdown "signature-core.md" %}
