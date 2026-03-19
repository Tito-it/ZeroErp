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

### Vincoli e trigger rilevanti

* **FK principali**: contratto, articolo, UoM operativa.
* **Trigger**:
  * `trg_contratti_righe_a10_qta_from_operativa_ins_upd` → calcolo quantita base da operativa.
  * `trg_contratti_righe_a10_note_contratto_block_deact_upd` → blocca disattivazioni se presenti note figlie.
  * `trg_contratti_righe_a10_articoli_require_attivo_ins_upd` → articolo attivo obbligatorio.

---

### Best practice

* Impostare `tipo_erogazione` e `fonte_quantita_attesa` in modo coerente con la logica di calcolo.
* Usare `quantita_fissa` **solo** per righe a canone o una‑tantum.
* Inserire in `meta` i soli parametri non coperti da colonne core.
* Disattivare una riga (`attivo = false`) solo dopo aver gestito le note collegate.

---

### Ruolo nel sistema

`vendite.contratti_righe` e` il **dettaglio contrattuale operativo**: traduce il contratto in voci fatturabili, collegando catalogo, regole di erogazione e parametri tecnici. E` il ponte tra **accordo commerciale** e **processo di fatturazione**.

{% include-markdown "signature-core.md" %}

---
