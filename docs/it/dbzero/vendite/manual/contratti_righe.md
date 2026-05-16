## 📘 Documentazione Concettuale – Tabella `vendite.contratti_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**   
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)   
> • [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto)  
> • [vendite.regole_fatturazione_articolo](/dbzero/vendite/tabelle/regole_fatturazione_articolo)    
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)   
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)   
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)     

---
### 🎯 Scopo Principale
(Initial version - 19-01-26)
`vendite.contratti_righe` contiene il **dettaglio economico e operativo** del contratto: ogni riga rappresenta un **articolo/servizio** con le proprie regole di erogazione (canone, consumo, una‑tantum), periodicita e parametri di quantita/prezzo.

Obiettivi principali:

* Definire **cosa** viene erogato (articolo) e **come** viene fatturato.
* Gestire **canoni** e **quantita attese** secondo regole flessibili.
* Supportare servizi **utilities** e servizi **non‑standard** con logiche specifiche per riga.

---

### Collocazione nel flusso

1. **Creazione contratto** → testata in `vendite.contratti`.
2. **Inserimento righe** → articoli e regole di erogazione in `vendite.contratti_righe`.
3. **Generazione attivita fatturabili** → le righe alimentano il motore di fatturazione (direttamente o tramite regole articolo).

---

### Campi chiave e logiche operative

* **Articolo** (`articolo_id`) → servizio/voce di catalogo.
* **Tipo erogazione** (`tipo_erogazione`) → indica la natura della riga (es. canone, consumo, una‑tantum).
* **Fonte quantita attesa** (`fonte_quantita_attesa`) → stabilisce se la quantita e` fissa, derivata da letture o calcolata.
* **Periodicita** (`periodicita`) → definisce l’intervallo di fatturazione (mensile, bimestrale, ecc.).
* **Generazione/competenza canone** (`generazione_canone`, `competenza_canone`) → governano se il canone e` anticipato/posticipato e con quale competenza.
* **Prezzo unitario** (`prezzo_unitario`) e **quantita fissa** (`quantita_fissa`) → base per righe a canone o una‑tantum.
* **Meta** (`meta`) → estensioni specifiche (parametri di tariffa, flag tecnici, mapping esterni).

---

### 📏 Quantita operative e unita di misura

Per righe che richiedono una UoM operativa:

* **`uom_operativa_id`** identifica la UoM usata in riga.
* **`qta_operativa`** indica la quantita nella UoM operativa.
* **`factor_to_base`** salva lo snapshot del fattore di conversione verso la UoM base.
* Il trigger `script.trgfn_qta_from_operativa(...)` garantisce la **coerenza della quantita base** a partire dalla quantita operativa.

---

### Collegamento con dati precontrattuali

Quando l’istanza e` di tipo utility, i dati di `anagrafiche.istanze_dati_precontrattuali` possono:

* fornire **parametri tecnici** per la valorizzazione di `meta`;
* determinare **regole di fatturazione** (es. tariffe, scaglioni, soglie);
* influenzare `quantita_fissa` o la **fonte di quantita**.

Per servizi non‑utility, la riga rimane il punto di verita delle condizioni economiche.

---

### Righe come eccezioni del listino — `tipo_eccezione` (dal 2026-05-15)

> **Refactor Step 2.2** — migration `20260515-11`, `20260515-12`.
> Il modello "modalità A/B/C" è eliminato. Le righe sono ora **eccezioni tipizzate**
> rispetto al listino del contratto padre.

Ogni riga porta un campo `tipo_eccezione vendite.tipo_eccezione_contratto NOT NULL`:

| Valore | Significato | `prezzo_unitario` |
| --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per articolo già nel listino | NOT NULL |
| `ESCLUSIONE` | Articolo del listino escluso per questo cliente | NULL |
| `AGGIUNTA` | Articolo non presente nel listino, aggiunto al contratto | NOT NULL |

#### CHECK `chk_contrighe_prezzo_per_tipo_eccezione`

Coerenza strutturale dichiarativa:

```text
ESCLUSIONE  → prezzo_unitario IS NULL
OVERRIDE    → prezzo_unitario IS NOT NULL
AGGIUNTA    → prezzo_unitario IS NOT NULL
```

#### Vincoli di unicità parziale

| Indice | Predicato | Semantica |
| --- | --- | --- |
| `uq_contrighe_one_eccezione_per_articolo` | `WHERE tipo_eccezione IN ('OVERRIDE','ESCLUSIONE')` | OVERRIDE e ESCLUSIONE sono mutualmente esclusivi per la stessa coppia `(contratto, articolo)` |
| `uq_contrighe_one_aggiunta_per_articolo` | `WHERE tipo_eccezione = 'AGGIUNTA'` | Al più una AGGIUNTA per coppia `(contratto, articolo)` |

#### Guard AGGIUNTA fuori listino

Il trigger `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd`
(→ [`trgfn_contratti_righe_guard_aggiunta_fuori_listino`](/dbzero/vendite/funzioni/trgfn_contratti_righe_guard_aggiunta_fuori_listino))
impedisce di usare `tipo_eccezione='AGGIUNTA'` per articoli **già presenti nel listino**:

* **Contratto senza listino** (`listino_id IS NULL`): nessun check, AGGIUNTA sempre valida.
* **Contratto DRAFT** (`listino_versione_id IS NULL`): verifica nella versione attiva del listino a `CURRENT_DATE`.
* **Contratto ATTIVO** (`listino_versione_id IS NOT NULL`): verifica nella versione fissata all'attivazione.

Se l'articolo è già nel listino → `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` (id 450). L'operatore deve usare `OVERRIDE` invece di `AGGIUNTA`.

#### Lock post-attivazione (Step 2.3)

Una volta che il contratto diventa ATTIVO, il trigger
`trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt`
blocca **qualsiasi** INSERT/UPDATE/DELETE su `contratti_righe` →
`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (id 452).

---

### Vincoli e trigger rilevanti

* **FK principali**: contratto, articolo, UoM operativa.
* **Trigger**:
  * `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd` — blocca AGGIUNTA per articoli già in listino (Step 2.2).
  * `trg_contratti_righe_a10_qta_from_operativa_ins_upd` — calcolo quantita base da operativa.
  * `trg_contratti_righe_a10_note_contratto_block_deact_upd` — blocca disattivazioni se presenti note figlie.
  * `trg_contratti_righe_a10_articoli_require_attivo_ins_upd` — articolo attivo obbligatorio.

---

### Best practice

* Impostare `tipo_eccezione` esplicitamente in base all'intento commerciale: **mai** usare AGGIUNTA per articoli già nel listino.
* Impostare `tipo_erogazione` e `fonte_quantita_attesa` in modo coerente con la logica di calcolo.
* Inserire in `meta` i soli parametri non coperti da colonne core.
* Disattivare una riga (`attivo = false`) solo dopo aver gestito le note collegate.

---

### Ruolo nel sistema

`vendite.contratti_righe` e` il **dettaglio contrattuale operativo**: traduce il contratto in voci fatturabili, collegando catalogo, regole di erogazione e parametri tecnici. E` il ponte tra **accordo commerciale** e **processo di fatturazione**.

{% include-markdown "signature-core.md" %}

---
