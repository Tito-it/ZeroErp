## 📘 Documentazione Concettuale – Tabella `config.stati_doc_preventivi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)    
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_preventivi` definisce gli **stati documento** del ciclo dei
preventivi commerciali. Serve a governare il passaggio dalla proposta iniziale
alla sua accettazione, revisione o chiusura operativa.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per descrivere la progressione del preventivo nel processo commerciale.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.
* **Revisioni**: `is_abortito` — la revisione con questo stato e` stata abbandonata
  (solo ANNULLATO). Diverso da `terminale` (vedi sotto).
* **Proiezione stato di dominio** (D1, brief `brief-db-proiezione-stato-dominio`):
  `fase`, `esito`, `terminale` — la **mappa dichiarata dal dominio** che normalizza il
  ciclo di vita per il motore pratiche (consumata via
  `vendite.vw_stato_sorgente_preventivo` → `script.vw_stato_sorgente`).

---

### Proiezione stato di dominio (mappa dichiarata)

| `codice_interno` | `fase` | `esito` | `terminale` |
|------------------|--------|---------|-------------|
| `DRAFT` | `APERTO` | — | no |
| `EMESSO` | `IN_ATTESA` | — | no |
| `ACCETTATO` | `IN_CORSO` | `POSITIVO` | no |
| `RIFIUTATO` | `CHIUSO` | `NEGATIVO` | sì |
| `SCADUTO` | `CHIUSO` | `NEGATIVO` | sì |
| `EVASO` | `CHIUSO` | `POSITIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` e` NOT NULL con CHECK sui 4 valori del vocabolario di motore: **ogni nuovo
  stato deve dichiarare la propria fase** (niente default silenziosi).
* `esito` referenzia `config.esiti_flussi_pratiche.codice_interno` (FK) e deve essere un
  **verdetto** (`is_verdetto=true`, guard
  `trg_stati_doc_preventivi_a10_guard_esito_verdetto_ins_upd`); NULL = nessun verdetto.
* `terminale` implica `fase='CHIUSO'` (CHECK `chk_stati_doc_preventivi_terminale_chiuso`).
* `terminale` **non sostituisce** `is_abortito`: RIFIUTATO/SCADUTO sono terminali ma non
  abortiti (chiudono la negoziazione, non la singola revisione).
* La proiezione fotografa lo **stato memorizzato**: `EMESSO → SCADUTO` e` transizione
  asincrona (job notturno) — il lag e` accettato e documentato nel manuale del resolver.

---

### Regole operative

* Lo stato e` usato da `vendite.preventivi.stato_doc_preventivo_id` come riferimento funzionale del documento.
* `codice` e `codice_interno` devono restare **stabili** per workflow, query e integrazioni.
* La disattivazione di uno stato gia` in uso su preventivi esistenti e` bloccata a livello DB.
* `ordine` va mantenuto coerente con la sequenza attesa del flusso commerciale, in particolare per stati come bozza, emesso, accettato, annullato.

---

### Uso tipico nel processo

* **Preparazione**: stati di lavoro per preventivi in costruzione o revisione.
* **Proposta/accettazione**: stati che qualificano il preventivo come presentato o accettato dal cliente.
* **Chiusura**: stati finali per annullo, superamento o completamento del ciclo.

---

{% include-markdown "signature-core.md" %}
