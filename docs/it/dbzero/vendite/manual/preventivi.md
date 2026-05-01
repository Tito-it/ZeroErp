## 📘 Documentazione Concettuale – Tabella `vendite.preventivi` (testata)

> ⚠️ **Modifiche importanti 2026-05-01** (sessione brief preventivi rev2):
>
> * `istanza_utility_id` ora **obbligatoria** (NOT NULL) — pattern allineato a `commesse_attivita` / `attivita_fatturabili`
> * Aggiunta colonna `emittente_fiscale_id` (NOT NULL, FK `anagrafiche.emittenti_fiscali`) — snapshot user-derived dell'operatore creatore, **immutabile** post-create
> * `billing_account_id` esplicitamente **opzionale** — supporto preventivi prospect (cliente non ancora BA)
> * Vista `vw_preventivi_list.emittente_fiscale_id` ora legge la colonna persistita (era fn dinamica che esplodeva su BA NULL)
> * Nuovi trigger di guardia: `default_emittente`, `guard_utility_istanza_coerenza`
>
> Brief completo: [risposta-db-brief-preventivi-rev2](/it/dev/work-in-progress/risposta-db-brief-preventivi-rev2).

👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)  
> • [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)  
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)  
> • [config.valute](/dbzero/config/tabelle/valute)  
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)  
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)  

**Trigger e funzioni associate (rev 2026-05-01):**

> • [vendite.trgfn_preventivi_default_emittente](/dbzero/vendite/funzioni/trgfn_preventivi_default_emittente) — set emittente da operatore  
> • [vendite.trgfn_preventivi_guard_utility_istanza_coerenza](/dbzero/vendite/funzioni/trgfn_preventivi_guard_utility_istanza_coerenza) — guard coerenza coppia istanza/utility  
> • [script.fn_check_utility_istanza_coerenza](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza) — pure check riusabile (BA + IDP + clienti)  
> • [anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — Strategia C su istanze  

**Guide concettuali:**

> • [Gestione delle istanze utility — sezione "Strategia C"](/it/guide/gestione-delle-istanze-utility#strategia-c--ogni-istanza-dichiara-la-utility-tramite-un-satellite-2026-05-01)  
> • [Risorse umane e accessi (multi-face auth, GUC `app.current_user_id`)](/it/guide/risorse-umane-e-accessi)  

---
### 🎯 Scopo Principale
La tabella **`vendite.preventivi`** rappresenta la **testata del preventivo commerciale**:
raccoglie cliente/BA/utility, condizioni economiche, validita` e stato documento.

E` il punto di ingresso del ramo commerciale che, dopo accettazione, alimenta la pipeline
`attivita_fatturabili` prima della fase di fatturazione fiscale.

---

### Flusso documentale (allineato pipeline attuale)

1. **Creazione preventivo** (bozza/emesso).  
2. **Gestione righe** su `vendite.preventivi_righe` (articoli, qta, prezzi, IVA).  
3. **Accettazione commerciale** (`stato_doc_preventivo_id -> ACCETTATO`).  
4. **Acquisizione in attività fatturabili** (branch `PREVENTIVI`) con creazione/aggiornamento
   record in `vendite.attivita_fatturabili`.  
5. **Fatturazione**: le attività fatturabili entrano nel flusso lotto/fatture.

Nota:

* il passaggio standard non è diretto `preventivo -> fattura`, ma mediato da
  `attivita_fatturabili`.

---

### Revisione preventivi

`vendite.preventivi` supporta revisioni multiple dello stesso numero documento:

* `numero` + `rev` identifica univocamente la revisione (`uq_preventivi_numero_rev`);
* è ammessa **una sola revisione attiva per numero** tramite indice univoco parziale
  `ux_preventivi_numero_attiva` (`is_revision_attiva = true`).

Regola operativa:
* le pipeline downstream devono considerare la revisione attiva, evitando doppio carico
  di revisioni storiche non attive.

---

### Fatturazione immediata (`fatturazione_immediata`)

Il flag `fatturazione_immediata` identifica preventivi che devono avere priorita` di
esecuzione nel ciclo attivo:

1. generazione attività in `attivita_fatturabili` (come gli altri preventivi eleggibili);
2. instradamento operativo verso **lotto giornaliero** per fatturazione.

Stato implementativo:
* la semantica funzionale e` definita;
* l’orchestrazione completa del ramo `PREVENTIVI` con comportamento immediato
  è tracciata nel documento `ripresa-lavori-attivita-fatturabili` (superato, vedi `gestione-commesse-v2.md`).

---

### Campi chiave funzionali

* **Identificazione/revisione**: `numero`, `rev`, `is_revision_attiva`
* **Perimetro operativo (obbligatorio)**: `istanza_utility_id`, `utility_id`
* **Perimetro fiscale (obbligatorio, snapshot)**: `emittente_fiscale_id`
* **Controparte (opzionale, prospect ammesso)**: `billing_account_id`
* **Validita`**: `validita_dal`, `validita_al`
* **Economici**: `totale_imponibile`, `totale_iva`, `totale_documento`, `valuta_id`
* **Stato**: `stato_doc_preventivo_id`
* **Competenza**: `competenza_mese`
* **Comportamento processo**: `fatturazione_immediata`
* **Pagamento**: `termine_pagamento_id`

#### Modello `istanza_utility_id` / `billing_account_id` / `emittente_fiscale_id`

* `istanza_utility_id` è **obbligatoria** (NOT NULL): allinea preventivi al pattern
  di `commesse_attivita` / `attivita_fatturabili`. In contesti utility (gas/EE/idrico)
  l'istanza esiste prima del BA (preventivo prospect); in contesti non-utility
  l'istanza viene generata in automatico come "contenitore tecnico"
  (vedi [Gestione delle istanze utility](/it/guide/gestione-delle-istanze-utility)).
* `billing_account_id` è **opzionale**: i preventivi prospect (cliente non ancora
  trasformato in BA) sono ammessi.
* `emittente_fiscale_id` è **obbligatoria** (NOT NULL): snapshot dell'emittente
  fiscale dell'**operatore loggato** che ha creato la riga (modello user-derived).
  Valorizzata a INSERT-time dal trigger `trgfn_preventivi_default_emittente`
  via GUC `app.current_user_id` (popolata da `JwtAuditAuthentication`) e
  `script.fn_resolve_emittente_for_user`. **Immutabile** post-create
  (`automation_lock_columns` + `script.trgfn_lock_columns`).

#### Coerenza utility/istanza

Il trigger `trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd` garantisce
che la coppia `(istanza_utility_id, utility_id)` sia coerente con almeno una
fonte satellite (`billing_account`, `istanze_dati_precontrattuali`, `clienti`)
tramite `script.fn_check_utility_istanza_coerenza`. La lista delle 3 fonti è
allineata al constraint trigger su `istanze_utilities`
(`trg_istanze_utilities_z90_require_utility_dichiarata_ins`).

---

### Audit e metadati

* `meta jsonb` per estensioni dominio/canale;
* colonne audit standard (`data_insert`, `user_insert`, `data_update`, `user_update`).

---

### Regole di coerenza principali

1. `chk_preventivi_validita`: intervallo validita` coerente.
2. `chk_preventivi_competenza_mese_primo`: competenza allineata al primo giorno del mese.
3. FK attive su stato documento, termini, utility, valuta, BA, emittente fiscale.
4. **Istanza obbligatoria** (NOT NULL): regola dominio.
5. **Emittente fiscale obbligatorio** (NOT NULL): snapshot user-derived,
   sollevato `E_PREV_EMITTENTE_NON_RISOLTO` se contesto non risolvibile.
6. **Coerenza utility/istanza**: `E_PREV_UTILITY_ISTANZA_INCOERENTE` se la coppia
   non e` dichiarata da nessuna fonte satellite.
7. **Emittente immutabile post-create**: `EMITTENTE_NON_MODIFICABILE` su UPDATE.

---

### Ruolo nel sistema

`vendite.preventivi` è la base del ciclo commerciale “offerta -> fatturabile”:
governa la proposta al cliente, la sua revisione controllata e il passaggio strutturato
verso il dominio `attivita_fatturabili`, inclusi i casi a fatturazione immediata.

