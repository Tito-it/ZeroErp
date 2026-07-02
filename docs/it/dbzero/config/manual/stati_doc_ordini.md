## 📘 Documentazione Concettuale – Tabella `config.stati_doc_ordini`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.ordini](/dbzero/vendite/tabelle/ordini)    
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_ordini` definisce gli **stati documento** del ciclo ordine di
vendita. Raccoglie in un catalogo unico le fasi di avanzamento commerciale e
operativo dell'ordine, dalla bozza fino all'evasione o chiusura.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per rappresentare la progressione del flusso ordine.
* **Governance**: `attivo`, `meta`.
* **Proiezione stato di dominio** (D1, brief `brief-db-proiezione-stato-dominio`):
  `fase`, `esito`, `terminale` — mappa dichiarata dal dominio, consumata via
  `vendite.vw_stato_sorgente_ordine` → `script.vw_stato_sorgente`.

---

### Proiezione stato di dominio (mappa dichiarata)

| `codice_interno` | `fase` | `esito` | `terminale` |
|------------------|--------|---------|-------------|
| `DRAFT` | `APERTO` | — | no |
| `CONFERMATO` | `IN_CORSO` | — | no |
| `ALLOCATO` | `IN_CORSO` | — | no |
| `SPEDITO` | `IN_CORSO` | — | no |
| `CONSEGNATO` | `IN_CORSO` | — | no |
| `EVASO` | `CHIUSO` | `POSITIVO` | sì |
| `FATTURATO` | `CHIUSO` | `POSITIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` NOT NULL con CHECK sui 4 valori; `esito` = verdetto (`is_verdetto=true`, guard
  `trg_stati_doc_ordini_a10_guard_esito_verdetto_ins_upd`) o NULL; `terminale ⇒ CHIUSO`.
* ⚠️ **Mappa centrata sul ciclo di VENDITA.** La tabella e` **condivisa** con
  `acquisti.ordini` (trigger di deattivazione su entrambi), ma il resolver della
  proiezione legge solo `vendite.ordini` (sorgente `ORDINE_VENDITA`). Un eventuale futuro
  resolver per l'ordine di **acquisto** dovra` validare che questa mappa calzi la sua
  semantica (es. `FATTURATO` come terminale/positivo puo` non valere per un acquisto) o
  valutare lo split della tabella.

---

### Regole operative

* Lo stato e` usato come riferimento da `vendite.ordini.stato_doc_ordine_id`.
* Lo stesso catalogo e` richiamato anche dalle righe ordine per allineare la fase documentale del dettaglio.
* `codice` e `codice_interno` devono restare **immutabili** dal punto di vista funzionale.
* La disattivazione di stati gia` usati in ordini o righe esistenti e` bloccata da trigger DB.

---

### Uso tipico nel processo

* **Preparazione**: stati iniziali per ordine in bozza o inserimento.
* **Conferma**: stati che rendono l'ordine valido per evasione o passaggi successivi.
* **Evasione/chiusura**: stati finali o avanzati per spedizione, completamento, annullo.

---

{% include-markdown "signature-core.md" %}
