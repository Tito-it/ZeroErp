# Zero ERP – Vendite: Preventivi, Ordini, DDT, Fatture, Contratti

**Sintesi architetturale e stato lavori** — aggiornato al 16/09/2025
  
---

## 1) Panoramica

Questo documento raccoglie quanto implementato e definito in chat per l’area **Vendite**:

* **Preventivi**, **Ordini**, **DDT**, **Fatture**, **Contratti** (linee guida) + domini trasversali.
* Decisioni architetturali, trigger e funzioni chiave, indici, partizionamenti.
* Backlog mirato (urgente vs non urgente).

> Convenzioni: tabelle in *corsivo* = previste/da completare. I riferimenti a changeSet indicano gli ID discussi/forniti in chat.

---

## 2) Domini e standard trasversali

### 2.1 Stati documento (fiscale / ordini / DDT)

* **`config.tipi_doc_fiscale`**

  * Aggiunte colonne: `codice_interno` (immutabile) e `codice_fe` (es. **TD01**, **TD04**), con vincoli `NN`, `UNIQUE`, `CHECK` sul formato FE.
  * Trigger di immutabilità su `codice_interno` (tramite `script.trgfn_lock_columns`).
  * Seed di **FATTURA** / **NOTA\_CREDITO** sistemato (fix sul campo `ordine` → `NULL`, non stringa vuota).
* **`config.stati_doc_fiscale`**

  * Colonna **`codice_interno`** (immutabile, univoca) introdotta per logica di trigger e riferimenti stabili.
  * Stati bloccanti (es. **EMESSA/INVIATA/CONSEGNATA/SCARTATA/REGISTRATA/ANNULLATA**) determinano vincoli di immutabilità numerazione.
* **`config.stati_doc_ordini`**

  * Usata da `vendite.ordini_righe.stato_doc_ordine_id`.
* **`config.stati_doc_ddt`** (proposta)

  * Stati: `DRAFT, EMESSO, SPEDITO, CONSEGNATO, RESO, ANNULLATO` (logistic oriented). Domanda aperta: introdurre tabella dedicata con `codice_interno`.

### 2.2 Sorgenti e idempotenza

* Dominio **`config.sorgenti`** (id numerico) usato da molte tabelle via campi `sorgente_*`.
* Indici unici **parziali** su tripletta (`sorgente_tipo_id`, `sorgente_id`, `sorgente_riga`) per garantire idempotenza di import.

### 2.3 Progressivi e numerazione fatture

* **Tabella** `vendite.registri_fatturazione_progressivi` **normalizzata**:

  * `mese` **DEFAULT 0 NOT NULL** (0 = non mensile), `serie` **DEFAULT '' NOT NULL**.
  * Vincolo **UNIQUE** su `(registro_id, anno, mese, serie)`.
* **Funzione** `vendite.fn_assign_numero_fattura(p_fattura_id)`

  * Assegnazione **atomica** e **idempotente**; loop `UPDATE … RETURNING` / `INSERT …` per concorrenza.
  * Chiavi progressivo basate su `reset_policy` del registro (annuale/mensile).
* **Finalizer** `vendite.fn_emetti_e_numera(p_fattura_id, p_set_emessa=true, 'EMESSA')`

  * Minimizza la finestra critica: numerazione come **ultimo step** → commit immediato. Idempotente.

### 2.4 Trigger “hard” comuni

* **A10** `vendite.trgfn_a10_fat_protect_num` → dopo stati bloccanti impedisce modifiche a **numero/serie/anno/data/registro/tipo\_doc\_fiscale**.
* **A11** `vendite.trgfn_a11_block_cancel_if_numbered` → **vietato** passare a `ANNULLATA` se la fattura è **numerata**.

### 2.5 Indirizzi & stradario

* **`anagrafiche.indirizzi`**

  * Unicità semplificata: **`(soggetto_ruolo_id, tipo_indirizzo_id)`** (rimossi i 2 UNIQUE che includevano l’indirizzo).
  * Opzionale: indice parziale `UNIQUE` per **un solo “primario”** per (ruolo,tipo) nello **stato corrente**.
* **`storico.indirizzi`** (separato) — esclusione temporale proposta (`btree_gist`) per evitare overlap dei periodi (da fare dove serve).
* **Stradario**

  * Modello confermato **via-per-CAP per Comune** (`config.stradario` ↔ `config.stradario_generale`).
  * Aggiunta colonna **`config.stradario_generale.indirizzo_normalizzato`** + funzioni `util.fn_norm_testo` / `util.fn_norm_via` e trigger di mantenimento; indice **GIN trigram** per ricerche veloci.

### 2.6 Altri domini

* **`config.modalita_addebito_trasporto`** (porto franco/assegnato/terzi)

  * Colonne: `codice_interno`, `codice`, `descrizione`, `attivo`, `ordine`, `meta` + trigger di lock su `codice_interno`.

---

## 3) Fatture

**Tabella** `vendite.fatture` (testata). Punti chiave decisi/implementati:

* **Neutralità fiscale**: *no* colonna `tipo_sdi` in fatture; mapping FE gestito nel dominio `config.tipi_doc_fiscale.codice_fe`.
* **Rettifiche**: link a fatture rettificate **esterno** (tabella separata N\:N) — *da implementare*.
* **Indirizzi**: snapshot spostati in tabella dedicata **`vendite.fatture_indirizzi`** (FATTURAZIONE/SPEDIZIONE/FORNITURA/RESIDENZA + `email_spedizione` vincolata al tipo SPEDIZIONE tramite trigger `trgfn_fatindir_email_rule`).
* **Totali/arrotondamenti**: previsti campi per **arrotondamento attuale e precedente**, **totale escluso base imponibile**, **flag fattura di minimo**, **data contabilizzazione** — *da completare nel DDL*.
* **Idempotenza**: `uid` unico e (opz.) `sorgente_*` per import.
* **Trigger**: A10, A11 (vedi §2.4).
* **Numerazione**: `fn_assign_numero_fattura` + finalizer `fn_emetti_e_numera` (§2.3).

### 3.1 Indici principali

* `(billing_account_id, data)`, `(emittente_soggetto_ruolo_id, data)`, `stato_doc_fiscale_id`, `uq_fatture_uid`, `uq_fatture_source` (parziale).

---

## 4) Ordini

**Testata** `vendite.ordini` (esistente).
**Righe** `vendite.ordini_righe` (changeSet **20250907-02**):

* Colonne chiave: `ordine_id`, `riga_nr`, `articolo_id`, `descrizione` (snapshot), `uom_id`, `qta`, `prezzo_unitario`, `sconto_perc`, `iva_id`, `iva_perc`.
* **Sorgente/idempotenza**: `sorgente_tipo_id`, `sorgente_id`, `sorgente_riga` + indice unico parziale `uq_ordrig_sorgente_fk`.
* **Stati**: `stato_doc_ordine_id` (FK `config.stati_doc_ordini`).
* **Vincoli**: CHECK su quantità/prezzo non negativi e percentuali ∈ \[0,100].
* **Unicità**: `(ordine_id, riga_nr)`.
* **Indici**: su testata, articolo, stato.

**Note per ordini**: partizione `vendite.note_ordini` (LIST `'ordine'`) con FK forti a testata/righe + **check di ancoraggio** e indice di rendering.

---

## 5) DDT

* **Domini stati DDT**: proposta `config.stati_doc_ddt` con `codice_interno` e possibili flag logistici.
* **Note per DDT**: partizione `vendite.note_ddt` (LIST `'ddt'`) con FK a testata/righe DDT + check ancoraggio + indice rendering.
* **Trigger futuri**: blocchi mirati per stati logistici (es. dopo `SPEDITO` solo campi tracking/POD; dopo `CONSEGNATO` blocco totale salvo stato/audit).

---

## 6) Preventivi

* *Struttura analoga* ad ordini/fatture, con dominio `config.stati_doc_preventivi` (DRAFT/EMESSO/SCADUTO/ANNULLATO…).
* Da consolidare DDL di **testata**/**righe**: snapshot descrizioni/UoM/IVA, idempotenza sorgente, regole di validità (scadenza/prezzi).

---

## 7) Contratti

* **Payer**: `anagrafiche.billing_account` usato come **payer** (FK in fattura). Principio: BA **immutabile** sulla fattura.
* **Legami**: in futuro, **contratto → BA** con validità; eventuale legame **punto di fornitura** per settori *acqua/gas*.
* **Rettifiche multiple**: previsione di tabella N\:N per collegare più documenti rettificati (rilevante nei servizi).

---

## 8) Note (partizionamento)

* Tabella parent: `vendite.note` (LIST sul tipo target: `'ordine'`, `'ddt'`, …).
* Partizioni: `vendite.note_ordini`, `vendite.note_ddt` create con changeSet dedicati; **evitare** `runOnChange` su partizioni; usare preconditions `not: tableExists`.
* **Check ancoraggio**: coerenza tra `anchor_tipo`, `target_riga_id` e `posizione` per rendering.

---

## 9) Osservazioni chiave emerse in chat

* **Uniformità naming**: `pk_*/fk_*/uq_*/ix_*`; rimozione prefissi eterogenei (`cod_*` vs `codice_*`).
* **COALESCE negli indici**: da evitare su chiavi logiche → **normalizzare i dati** (es. `mese=0`, `serie=''`).
* **RunOnChange/ANY**: limitarne l’uso (auditabilità). Ogni migrazione **immutabile** con preconditions idempotenti.
* **Meta JSONB**: utile, ma promuovere a colonne i campi che diventano core (tipi/indici/controlli).
* **Stradario**: scelta **via-per-CAP** confermata; ricerche rapide via `indirizzo_normalizzato` su `stradario_generale` e su `indirizzo_dettaglio` per full-address.
* **Indirizzi per ruolo**: pivot corretto su `soggetto_ruolo_id` (non serve `soggetto_id`). Unique aggiornata a `(ruolo,tipo)`.
* **Stati come policy**: idea di **`consente_modifiche`** (o livello `EDIT_*`) rimandata a fase successiva.

---

## 10) Prossimi passi – urgenti

1. **Fatture – DDL finale**: aggiungere in `vendite.fatture` i campi concordati (arrotondamento\_precedente/attuale, totale\_escluso\_imponibile, flag\_fattura\_minimo, data\_contabilizzazione) + commenti.
2. **Rettifiche**: creare tabella **`vendite.fatture_rettifiche`** (N\:N) con vincoli coerenti e regole su `tipo_doc_fiscale`.
3. **Partizioni `vendite.note`**: consolidare changeSet per `note_ordini`/`note_ddt` **senza** `runOnChange` + preconditions idempotenti.

## 11) Prossimi passi – non urgenti

* **State machine tabellare** (transizioni per ogni dominio stati + validazioni opzionali).
* **Test suite DB** per trigger/funzioni (pgTAP o `DO $$` di verifica) + **grants idempotenti**.
* **Partizionamento** per volumi (fatture/righe per anno) + viste/materializzate per reporting.
* **i18n** domini: tabella `_traduzioni` per entità (vista con `current_setting('app.lang')`).
* **Incoterms** (`config.incoterms`) e mapping con logistica/fatturazione.

---

## 12) Riferimenti changeSet principali citati

* Numerazione fatture (funzioni, trigger A10/A11): **20250904-09**, **20250904-11**, **20250904-12**, **20250904-13**.
* Progressivi normalizzati (mese/serie, UNIQUE): **20250904-14**.
* Ordini righe (creazione completa): **20250907-02**.
* Note per Ordini / DDT (partizioni): **20250915-02** (fix ordini), **20250915-01** (ddt).
* Tipi doc fiscali – `codice_interno`, `codice_fe`: **20250907-01**.
* Stradario generale – `indirizzo_normalizzato` + trigram: **20250905-stradgen-add-indirizzo-normalizzato**.
* Indirizzi (unique per ruolo/tipo): **20250905-indirizzi-unique-ruolo-tipo**.

---

### Appendice A — Trigger chiave (descrizione)

* **`vendite.trgfn_a10_fat_protect_num`**: impedisce modifiche a numerazione/data/registro/tipo\_doc\_fiscale quando lo stato (letto via `stato_doc_fiscale_id → config.stati_doc_fiscale.codice_interno`) è in elenco bloccante.
* **`vendite.trgfn_a11_block_cancel_if_numbered`**: vieta transizione a `ANNULLATA` se `numero` non è NULL (già numerata).
* **`vendite.trgfn_fatindir_email_rule`**: consente `email_spedizione` **solo** per tipo indirizzo `SPEDIZIONE` (FK `config.tipi_indirizzi`).

### Appendice B — Funzioni chiave (descrizione)

* **`vendite.fn_assign_numero_fattura(p_id)`**: serializza la numerazione per chiave `(registro, anno, [mese], [serie])` e aggiorna la testata; idempotente se già numerata.
* **`vendite.fn_emetti_e_numera(p_id, p_set_emessa, p_codice)`**: finalizer per assegnare numero come ultimo step, opzionalmente imposta lo stato `EMESSA`.
* **`util.fn_norm_testo` / `util.fn_norm_via`**: normalizzazione (lower, unaccent, rimozione punteggiatura, spazi compressi) coerente tra stradario/indirizzi.

---

> **Nota**: questo documento è una fotografia dello stato discusso/implementato. Per dettagli puntuali dei DDL, fare riferimento ai singoli changeSet nel repository.
