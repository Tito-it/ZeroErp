## 📘 Documentazione Concettuale – Tabella `config.stati_doc_contratti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)    
>
### 🎯 Scopo Principale
(latest review 2026-05-21)
`config.stati_doc_contratti` definisce gli **stati documento** del ciclo di vita
dei contratti commerciali. Fornisce un catalogo centralizzato per rappresentare
le fasi operative del contratto, dalla bozza fino alla chiusura o all'annullamento.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per esprimere una progressione logica degli stati.
* **Governance**: `attivo`, `meta`, `is_abortito`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

#### Campo `is_abortito`

`is_abortito BOOLEAN NOT NULL DEFAULT false` — aggiunto in migration `20260520-07`.

Indica che lo stato rappresenta un contratto **abortito** (annullato prima
dell'attivazione). Gli stati con `is_abortito = true` hanno effetti speciali:

* Il constraint di overlap `ex_contratti_no_overlap` su `vendite.contratti`
  usa un predicato parziale `WHERE NOT is_abortito_snapshot`: i contratti in
  stato abortito sono esclusi dal check di sovrapposizione temporale.
* `is_abortito` viene denormalizzato su `vendite.contratti.is_abortito_snapshot`
  tramite il trigger `trg_contratti_z90_snapshot_da_stato_ins_upd` (BB
  `vendite.trgfn_doc_snapshot_da_stato`, dal 2026-10-11) a ogni scrittura.

#### Campo `meta`

**La sede e` il CSV** `80_data/sql/config/stati_doc_contratti.csv`, letto dal
mirror `20260806-14` (`loadUpdateData`, `runOnChange`). Si modifica editando il
CSV: nessun `UPDATE` SQL nuovo su questa colonna.

Contenuto oggi: `meta.nessuna_azione_key`, la chiave i18n che spiega
all'operatore cosa sta succedendo quando il contratto e` in uno stato chiuso
(`CESSATO`, `ANNULLATO`). La legge `script.fn_available_actions_contratto` e la
espone nel blob come **`stato_info_key`** — il nome del campo e quello della
proprieta` sono diversi di proposito, vedi `20260811-01`.

> 🔴 **Correzione del 2026-08-11 — questo paragrafo diceva l'opposto, ed era
> stale di due generazioni.** Diceva: «popolato da `20260430-61` + `20260520-10`
> tramite UPDATE SQL (non da `loadUpdateData` — il meta e` gestito solo da SQL
> dedicato per evitare sovrascritture)». Non e` piu` vero **e non va rimesso**.
> Il testo resta qui perche` il dubbio che ha generato e` legittimo e tornera` a
> qualcun altro.
>
> **Cosa e` cambiato, in due passaggi:**
>
> 1. **2026-05-28** — `meta.outgoing_action` era un ripiego: i contratti non
>    avevano una tabella di transizioni, quindi il bottone si descriveva nel
>    `meta` dello stato sorgente. Quel giorno la tabella e` nata
>    (`20260528-04-create-transizioni-stati-contratti`) e la funzione e` passata
>    a leggere quella (`20260528-05`). Da allora `outgoing_action` e` un **campo
>    morto**: verificato sulla funzione viva, non lo legge piu`, e nel CSV non
>    compare.
> 2. **2026-08-06** — `20260806-14` ha **ri-ancorato il mirror** dopo i due
>    `UPDATE`, che sono stati spenti (`runOnChange: false`). Il motivo e` la
>    trappola descritta in `.codex/AGENTS.md`: quei due SQL scrivevano `meta`
>    *dopo* il mirror originale `20260520-08`, quindi su sviluppo vinceva il CSV
>    (il mirror ri-esegue a ogni migrate) e su un database **ricostruito da zero**
>    vincevano loro, riportando in vita `outgoing_action` con le chiavi i18n
>    vecchie. Due macchine su due versioni della stessa tabella.
>
> **Verificato l'11-08 su tre piani**, perche` sul solo DB di sviluppo si misura
> una macchina e non la riproducibilita`: il valore vivo (le due
> `nessuna_azione_key` sono in tabella), la funzione (non legge piu`
> `outgoing_action`), e l'ordine in timeline (`20260806-14` e` l'ultimo dei
> quattro e ha `runOnChange: true`, quindi vince anche su un DB da zero).

---

### Stati registrati

| `codice_interno` | `ordine` | `is_abortito` | Significato |
| --- | --- | --- | --- |
| `DRAFT` | 10 | false | Bozza in costruzione — modificabile |
| `ATTIVO` | 20 | false | Contratto in vigore — usato dal resolver pricing |
| `CESSATO` | 50 | false | Contratto scaduto o terminato — terminale |
| `ANNULLATO` | 70 | **true** | Bozza annullata prima dell'attivazione — terminale |

---

### Regole operative

* Lo stato e` usato da `vendite.contratti.stato_doc_contratto_id` come riferimento funzionale univoco.
* `codice` e `codice_interno` devono restare **stabili** per non rompere query, mapping applicativi e integrazioni (protetti da `script.trgfn_lock_columns`).
* La disattivazione di uno stato gia` usato da contratti esistenti e` bloccata da trigger DB.
* `ordine` va mantenuto coerente con la sequenza attesa del processo contrattuale.
* Nuovi stati con `is_abortito = true` richiedono verifica del constraint `ex_contratti_no_overlap` su `vendite.contratti` (il predicato `WHERE NOT is_abortito_snapshot` li esclude automaticamente).

---

### Uso tipico nel processo

* **Apertura**: `DRAFT` — bozza in costruzione, tutto modificabile.
* **Attivazione**: `ATTIVO` — contratto operativo, resolver pricing attivo, lock post-attivazione.
* **Chiusura ordinaria**: `CESSATO` — scadenza automatica (job notturno) o cessazione manuale.
* **Annullamento bozza**: `ANNULLATO` — bozza non ancora attivata; non blocca nuovi contratti sulla stessa quadrupla.

---

### Proiezione stato di dominio (mappa dichiarata)

Mappa D1 (brief `brief-db-proiezione-stato-dominio`) consumata via
`vendite.vw_stato_sorgente_contratto` → `script.vw_stato_sorgente`:

| `codice_interno` | `fase` | `esito` | `terminale` |
|------------------|--------|---------|-------------|
| `DRAFT` | `APERTO` | — | no |
| `ATTIVO` | `IN_CORSO` | — | no |
| `CESSATO` | `CHIUSO` | `POSITIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` NOT NULL con CHECK sui 4 valori; `esito` = verdetto (`is_verdetto=true`, guard
  `trg_stati_doc_contratti_a10_guard_esito_verdetto_ins_upd`) o NULL; `terminale ⇒ CHIUSO`.
* `terminale` **non sostituisce** `is_abortito`: `CESSATO` è terminale ma non abortito;
  `ANNULLATO` è entrambi. Sono assi distinti (§decisione E del brief).

---

{% include-markdown "signature-core.md" %}
