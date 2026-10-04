## 📘 Documentazione Concettuale – Tabella `vendite.contratti_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**   
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)   
> • [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto)  
> • [vendite.regole_fatturazione_articolo](/dbzero/vendite/tabelle/articolo_regole_fatturazione)    
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
* **Tipo erogazione** (`tipo_erogazione`) → natura della riga: `CANONE`, `UNA_TANTUM`, `ORARIO`, `CONSUMO`.
* **Fonte quantita attesa** (`fonte_quantita_attesa`) → origine della quantita attesa (vedi sezione dedicata).
* **Periodicita** (`periodicita`) → intervallo di fatturazione (mensile, bimestrale, ecc.).
* **Generazione/competenza canone** (`generazione_canone`, `competenza_canone`) → canone anticipato/posticipato e competenza.
* **Prezzo unitario** (`prezzo_unitario`) e **quantita** (`quantita`) → base per righe a canone o una‑tantum.
* **Meta** (`meta`) → estensioni specifiche (parametri di tariffa, flag tecnici, mapping esterni).

---

### Matrice `tipo_erogazione` × `fonte_quantita_attesa` (dal 2026-05-19)

> **Migrations**: `20260519-05` (backfill + NOT NULL + CHECK), `20260519-06` (trigger normalize).

`fonte_quantita_attesa` e’ **NOT NULL** e deve essere coerente con `tipo_erogazione`.
Il trigger `script.trgfn_righe_default_fonte_qta` (funzione **generica**, condivisa
con `offerte_commerciali_eccezioni` dal refactor 2026-05-31; sostituisce la vecchia
`vendite.trgfn_contratti_righe_default_fonte_qta`) imposta il default automaticamente
su INSERT e resetta la fonte se il cambio di `tipo_erogazione` rende la combinazione vietata.

#### Valori ammessi per `fonte_quantita_attesa`

| Valore | Significato | `quantita` mostrata in UI? |
| --- | --- | --- |
| `FISSA` | Quantita contrattualizzata a corpo | Si’, obbligatoria |
| `MANUALE` | Quantita definita sul documento al momento dell’emissione | No — tag "Definita sul documento" |
| `TIMESHEET` | Quantita da rendicontazione ore (modulo futuro) | No — tag "Da rendicontazione ore" |
| `LETTURE` | Quantita da letture utility | No — tag "Da letture utility" |
| `DERIVATA_COMPONENTI` | Quantita calcolata dai componenti BoM del padre composito | No — tag "Derivata dai componenti" |

Per `DERIVATA_COMPONENTI`: la colonna `quantita` viene **scritta automaticamente** dal trigger
`trg_contratti_righe_z90_propaga_qta_componenti_upd` a partire dai componenti — non e’ editabile dall’utente
ma non e’ vuota nel DB.

#### Matrice coerenza (legenda: ✅ default · 🟢 secondaria · 🟡 rara/edge · ❌ vietata)

| tipo_erogazione | FISSA | MANUALE | TIMESHEET | LETTURE | DERIVATA_COMPONENTI |
| --- | --- | --- | --- | --- | --- |
| **CANONE** | ✅ | 🟡 | ❌ | ❌ | 🟢 |
| **UNA_TANTUM** | ✅ | 🟢 | ❌ | ❌ | 🟢 |
| **ORARIO** | 🟡 | 🟢 | ✅ (futuro) | ❌ | 🟡 |
| **CONSUMO** | ❌ | 🟢 | ❌ | ✅ | 🟢 |

Le 7 combinazioni ❌ sono bloccate dal CHECK `chk_contrighe_coerenza_fonte_erogazione`.
Le combinazioni 🟡 rare sono ammesse e segnalate in UI con tooltip "uso atipico".

#### Default per `tipo_erogazione`

| tipo_erogazione | fonte default |
| --- | --- |
| `CANONE` | `FISSA` |
| `UNA_TANTUM` | `FISSA` |
| `ORARIO` | `MANUALE` (sara’ `TIMESHEET` quando il modulo esistera’) |
| `CONSUMO` | `LETTURE` |
| `NULL` o non riconosciuto | `FISSA` (fallback difensivo) |

---

### 📏 Quantita operative e unita di misura

Per righe che richiedono una UoM operativa:

* **`uom_operativa_id`** identifica la UoM usata in riga.
* **`qta_operativa`** indica la quantita nella UoM operativa (**sorgente**).
* **`factor_to_base`** salva lo snapshot del fattore di conversione verso la UoM base.
  **Nullable** dal refactor 2026-05-31 (prima `NOT NULL DEFAULT 1`): se NULL il trigger
  lo deriva dal mapping `catalogo.articoli_uom_operativa` e lo salva.
* Il trigger `script.trgfn_qta_from_operativa(...)` garantisce la **coerenza della quantita base** (`quantita`, derivata) a partire dalla quantita operativa.
* Vincolo `chk_contrighe_qta_operativa_nonzero` (`qta_operativa IS NULL OR qta_operativa <> 0`): negativi ammessi, zero vietato.

---

### Collegamento con dati precontrattuali

Quando l’istanza e` di tipo utility, i dati di `anagrafiche.istanze_dati_precontrattuali` possono:

* fornire **parametri tecnici** per la valorizzazione di `meta`;
* determinare **regole di fatturazione** (es. tariffe, scaglioni, soglie);
* influenzare `quantita` o la **fonte di quantita**.

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

#### Righe solo in bozza (era «lock post-attivazione», Step 2.3)

Le righe si aggiungono, modificano e tolgono solo finché il contratto è in
DRAFT: il trigger `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt`
— il building block
[`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
lo stesso di `ddt_righe` e `ordini_righe` — blocca **qualsiasi**
INSERT/UPDATE/DELETE in ATTIVO, CESSATO e ANNULLATO → `E_RIGA_DOC_NON_BOZZA`.
La copia dedicata ai contratti (che bloccava il solo ATTIVO) è stata ritirata il
2026-09-22; il codice 452 resta al lock della testata.

#### Un'esclusione non si modifica (2026-10-04)

Una riga `ESCLUSIONE` dice una cosa sola: il contratto non vende quell'articolo
del listino. Si crea (Escludi) e si cancella (Ripristina articolo, `DELETE`), e
basta: prezzo, quantità, UoM, erogazione e fonte non la riguardano. Il trigger
`trg_contratti_righe_a05_guard_esclusione_immutabile_upd`
(→ [`trgfn_contratti_righe_guard_esclusione_immutabile`](/dbzero/vendite/funzioni/trgfn_contratti_righe_guard_esclusione_immutabile))
rifiuta ogni `UPDATE` che cambi qualcosa di diverso dalle colonne tecniche →
`E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`. Anche `attivo`: un'esclusione spenta
terrebbe occupato il posto dell'articolo in `uq_contrighe_one_eccezione_per_articolo`.

#### Il tipo di una riga non si cambia (2026-10-04)

`tipo_eccezione` è bloccato da un lock di colonna (registro
`dbops.automation_lock_columns`) → `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`.
Ogni tipo ha i suoi dati e i suoi controlli, che valgono quando la riga nasce:
un `OVERRIDE` portato a `ESCLUSIONE` sul posto creerebbe un'esclusione senza
passare da Escludi. Per cambiare tipo si elimina la riga e se ne crea una nuova.

---

### Vincoli e trigger rilevanti

* **FK principali**: contratto, articolo, UoM operativa.
* **Trigger**:
  * `trg_contratti_righe_a05_guard_esclusione_immutabile_upd` — una riga ESCLUSIONE non si modifica (2026-10-04).
  * lock di colonna su `tipo_eccezione` (generato dal registro `dbops.automation_lock_columns`, 2026-10-04).
  * `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd` — blocca AGGIUNTA per articoli già in listino (Step 2.2).
  * `trg_contratti_righe_a10_default_fonte_qta_ins_upd` — normalizza `fonte_quantita_attesa` al default su INSERT e su UPDATE con tipo cambiato (20260519-06; ri-bindato alla funzione generica `script.trgfn_righe_default_fonte_qta` in 20260531-10).
  * `trg_contratti_righe_a10_qta_from_operativa_ins_upd` — calcolo quantita base da operativa.
  * `trg_contratti_righe_a10_note_contratto_block_deact_upd` — blocca disattivazioni se presenti note figlie.
  * `trg_contratti_righe_a10_articoli_require_attivo_ins_upd` — articolo attivo obbligatorio.

---

### Best practice

* Impostare `tipo_eccezione` esplicitamente in base all'intento commerciale: **mai** usare AGGIUNTA per articoli già nel listino.
* Impostare `tipo_erogazione` e `fonte_quantita_attesa` in modo coerente con la logica di calcolo.
* Inserire in `meta` i soli parametri non coperti da colonne core.
* Disattivare una riga (`attivo = false`) solo dopo aver gestito le note collegate.
* Un'esclusione non si disattiva e non si modifica: si cancella («Ripristina articolo»).

---

### Ruolo nel sistema

`vendite.contratti_righe` e` il **dettaglio contrattuale operativo**: traduce il contratto in voci fatturabili, collegando catalogo, regole di erogazione e parametri tecnici. E` il ponte tra **accordo commerciale** e **processo di fatturazione**.

{% include-markdown "signature-core.md" %}

---
