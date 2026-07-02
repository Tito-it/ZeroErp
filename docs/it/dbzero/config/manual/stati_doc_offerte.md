## 📘 Documentazione Concettuale – Tabella `config.stati_doc_offerte`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)
>
### 🎯 Scopo Principale
(latest review 2026-07-02)
`config.stati_doc_offerte` definisce gli **stati documento** del ciclo di vita
delle offerte commerciali, dalla bozza fino all'accettazione, al rifiuto o al
superamento.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per la progressione logica degli stati.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.
* **Proiezione stato di dominio** (D1, brief `brief-db-proiezione-stato-dominio`):
  `fase`, `esito`, `terminale` — la **mappa dichiarata dal dominio** che normalizza il
  ciclo di vita per il motore pratiche (consumata via
  `vendite.vw_stato_sorgente_offerta` → `script.vw_stato_sorgente`).

---

### Proiezione stato di dominio (mappa dichiarata)

| `codice_interno` | `fase` | `esito` | `terminale` |
|------------------|--------|---------|-------------|
| `BOZZA` | `APERTO` | — | no |
| `EMESSA` | `IN_ATTESA` | — | no |
| `ACCETTATA` | `IN_CORSO` | `POSITIVO` | no |
| `RIFIUTATA` | `CHIUSO` | `NEGATIVO` | sì |
| `SUPERATA` | `CHIUSO` | `NEGATIVO` | sì |
| `ANNULLATA` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` e` NOT NULL con CHECK sui 4 valori del vocabolario di motore: **ogni nuovo
  stato deve dichiarare la propria fase** (niente default silenziosi).
* `esito` referenzia `config.esiti_flussi_pratiche.codice_interno` (FK) e deve essere un
  **verdetto** (`is_verdetto=true`, guard
  `trg_stati_doc_offerte_a10_guard_esito_verdetto_ins_upd`); NULL = nessun verdetto.
* `terminale` implica `fase='CHIUSO'` (CHECK `chk_stati_doc_offerte_terminale_chiuso`).

---

### Regole operative

* Lo stato e` usato da `vendite.offerte_commerciali.stato_doc_offerta_id`.
* `codice` e `codice_interno` devono restare **stabili** per workflow, query e integrazioni.
* La disattivazione di uno stato gia` in uso su offerte esistenti e` bloccata a livello DB.

---

{% include-markdown "signature-core.md" %}
