# Analisi Gravita Progettuale - Anagrafiche (Indirizzi, Soggetti/Ruoli, Istanze Utility)

Data analisi: 15-02-2026
Ambito: revisione di gravita su incongruenze strutturali e miglioramenti ad alto impatto.

## 1. Scopo e perimetro

Questo documento sintetizza i punti critici emersi su:

- gestione indirizzi
- soggetti e ruoli anagrafici
- gestione istanze utility

L'analisi esclude volutamente dettagli minori e si concentra su rischi progettuali con impatto architetturale/operativo.

## 2. Findings ad alta gravita

### 2.1 Ownership della utility non deterministico tra istanza/PDP/cliente (CHIUSO)

Problema:

- la guida funzionale tratta la utility come attributo proprio dell'istanza;
- il modello tabellare di `anagrafiche.istanze_utilities` non espone `utility_id`;
- in pratica la utility viene derivata da `pdp.utilities_id` (quando presente) oppure sincronizzata su cliente da billing account.

Rischio (iniziale):

- disallineamento tra dominio tecnico (PDP) e dominio commerciale (billing account/clienti);
- difficolta a garantire coerenza in assenza PDP o in flussi pre-contrattuali.

Riferimenti:

- `docs/it/guide/gestione-delle-istanze-utility.md`
- `docs/it/dbzero/anagrafiche/tabelle/istanze_utilities.md`
- `docs/it/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio.md`
- `docs/it/dbzero/anagrafiche/manual/trgfn_clienti_sync_utility_from_ba.md`

#### Stato implementativo (aggiornato 15-02-2026)

- la derivazione della utility senza persistenza su `istanze_utilities` e una scelta tecnica accettata;
- il `billing_account` e la fonte prevalente nella maggior parte dei flussi;
- per utility come **gas, energia, idrico** il PDP e parte del modello tecnico e deve restare coerente con la utility del billing account;
- quando non si tratta di **gas, energia, idrico**, il PDP puo non essere richiesto e la utility puo essere risolta dal billing account.

Implementazioni applicate:

- aggiunto `config.utilities.richiede_pdp` con valorizzazione dominio (`GAS/ENERGIA/IDRICO=true`, altri `false`);
- rafforzata `anagrafiche.trgfn_clienti_sync_utility_from_ba()`:
  - se `richiede_pdp=true` e `pdp_id` assente -> errore bloccante;
  - se `pdp_id` presente e `pdp.utilities_id <> billing_account.utility_id` -> errore bloccante;
  - mantenuto sync `clienti.utility_id` da `billing_account.utility_id`;
- aggiunti test `pgTAP` dedicati alla policy utility/PDP;
- allineata documentazione funzionale/tecnica sulla policy con e senza PDP.

Correzioni correlate emerse durante i test:

- fix storico su `clienti`: trigger storico riallineato a `cliente_id` (non `clienti_id`);
- aggiunto override `STORICO_FK` su `dbops.automation_overrides_cols` per evitare regressioni da automazioni.

Follow-up residui (non bloccanti per il punto 2.1):

- mantenere monitoraggio regressione sui trigger storico `anagrafiche.clienti`;
- consolidare nel backend API la validazione pre-run (stessi vincoli dei guard DB) come ulteriore rete di sicurezza.

---

### 2.2 Drift documentale su `soggetti_ruoli` (naming e semantica)

Problema (CHIUSO):

- documentazione concettuale con naming storico (`ruolo_id`, `extra`);
- modello reale con naming aggiornato (`tipo_ruolo_id`, `meta`).

Rischio:

- implementazioni future su colonne non piu coerenti;
- query/API di nuova scrittura non allineate al modello reale.

Riferimenti:

- `docs/it/dbzero/anagrafiche/manual/soggetti_ruoli.md`
- `docs/it/dbzero/anagrafiche/tabelle/soggetti_ruoli.md`
- `docs/it/guide/soggetti-e-ruoli-anagrafici.md`

Stato:

- aggiornamento documentazione applicato il 15-02-2026 su `manual/soggetti_ruoli.md` per usare naming corrente (`tipo_ruolo_id`, `meta`).

---

### 2.3 Semantica trigger guard indirizzi obbligatori non chiarita (immediata vs deferita)   **CHIUSO**

Problema:

- documentazione funzione mostra uso tipico come controllo immediato;
- tabella mostra trigger operativo in forma `AFTER`/deferrable.

Rischio:

- differenza tra aspettativa applicativa (fail-fast) e comportamento transazionale reale (errore a fine transazione);
- gestione errori lato API non uniforme.

Riferimenti:

- `docs/it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_guard_indirizzi_required.md`
- `docs/it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_indirizzi_required.md`
- `docs/it/dbzero/anagrafiche/tabelle/soggetti_ruoli.md`
- `docs/it/dbzero/anagrafiche/tabelle/soggetti.md`
- `docs/it/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required.md`
- `docs/it/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required.md`

Stato:

- RISOLTO (15-02-2026).
- Allineata la documentazione `manual` e `funzioni` alla semantica reale:
  - trigger di tipo `CONSTRAINT`,
  - `DEFERRABLE INITIALLY DEFERRED`,
  - enforcement a `COMMIT` o via `SET CONSTRAINTS ... IMMEDIATE`.
- Aggiornate anche le pagine tabellari (`soggetti`, `soggetti_ruoli`) con nota esplicita sui trigger deferred.
- Copertura test confermata:
  - `db/pgtap/anagrafiche/test-soggetti-indirizzi-required.sql` (layer soggetto),
  - `db/pgtap/anagrafiche/test-soggetti-ruoli-indirizzi-required.sql` (layer ruolo, aggiunto).
- Correzione strutturale emersa durante i test e già inclusa:
  - fix trigger storico `anagrafiche.soggetti` su FK logica `soggetto_id`,
  - override automazione `dbops.automation_overrides_cols` per evitare rigenerazioni errate.

---

### 2.4 Doppio layer indirizzi (ruolo/soggetto) corretto ma con governance incompleta    **CHIUSO**

Problema:

- il modello separa bene `indirizzi` (ruolo) e `indirizzi_soggetti` (identitario);
- restano differenze operative rilevanti (storicizzazione di default diversa, policy non sempre esplicitata nei flussi).

Rischio:

- usi non uniformi per dominio;
- audit/storico incoerente tra indirizzo identitario e indirizzo operativo.

Regole operative formalizzate (decisione):

1. Master per processo/ruolo:
   - l'indirizzo master e sempre quello del layer `indirizzi` (indirizzo del ruolo).

2. Fallback consentito:
   - il fallback a `indirizzi_soggetti` e consentito solo quando non esiste un indirizzo ruolo valido
     per il tipo indirizzo richiesto dal processo.

3. Selezione deterministica:
   - non e richiesto un solo indirizzo assoluto per ruolo, ma per ogni chiave funzionale
     (ruolo + tipo indirizzo richiesto) deve esistere al massimo un candidato risolvibile;
   - in presenza di candidati multipli per la stessa chiave funzionale, il processo deve:
     - applicare una priorita esplicita e documentata, oppure
     - fallire con errore di guard (comportamento preferito).

4. Processi critici fail-closed:
   - se manca sia l'indirizzo ruolo (master) sia il fallback su `indirizzi_soggetti`,
     i processi critici devono terminare con errore bloccante (no fail-open silenzioso).

Note di implementazione:

- non e richiesto introdurre un campo `source` nelle tabelle base;
- la provenienza risolta (`ROLE` o `SOGGETTO`) va esposta come campo derivato in viste/API
  di risoluzione indirizzo per audit funzionale e debug.

Stato implementativo (aggiornato 15-02-2026):

- introdotto campo derivato `source` nelle viste resolved indirizzi
  (`anagrafiche.vw_indirizzi_resolved_base` e derivate);
- aggiornata `script.fn_get_indirizzo(...)` con policy operativa:
  - master su layer ruolo (inclusa catena fallback per tipo su matrice ruolo/tipo),
  - fallback su layer soggetto solo se nessun indirizzo ruolo risolto.
- RISOLTO (15-02-2026):
  - policy formalizzata in documentazione;
  - viste/funzioni allineate alla governance ruolo-master + soggetto-fallback;
  - copertura test aggiornata in `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` (14 assert).

Riferimenti:

- `docs/it/guide/gestione-degli-indirizzi.md`
- `docs/it/dbzero/anagrafiche/tabelle/indirizzi.md`
- `docs/it/dbzero/anagrafiche/tabelle/indirizzi_soggetti.md`
- `docs/it/dbzero/script/manual/trgfn_storico_generic.md`

---

### 2.5 Gap intenzionale ma rilevante: dominio anagrafiche DB-first, backend non ancora avviato

Contesto (esplicito):

- il backend anagrafiche non e stato avviato appositamente.

Osservazione:

- ad oggi il dominio e molto ricco nel DB;
- lato Django l'area `apps/anagrafiche` e sostanzialmente placeholder.

Rischio (se non pianificato):

- crescita di logica operativa solo SQL senza orchestrazione applicativa;
- difficolta di test end-to-end e contratti API nel momento in cui parte lo sviluppo.

Riferimenti:

- `backend/apps/anagrafiche/models.py`
- `backend/apps/anagrafiche/api/views.py`
- `backend/apps/anagrafiche/api/urls.py`
- `docs/it/backend/anagrafiche/index.md`

## 3. Findings a media gravita

### 3.1 Residui documentali obsoleti su `istanze_utilities`  **(CHIUSO)**

Problema:

- nella manualistica sono presenti riferimenti storici non piu coerenti con lo schema reale (es. `codice_istanza`, `trgfn_istanze_utilities_clean_fields`, indici non piu presenti con quei nomi).

Rischio:

- onboarding piu lento;
- errori di implementazione nelle prime fasi backend per uso di nomi non aggiornati.

Riferimenti:

- `docs/it/dbzero/anagrafiche/manual/istanze_utilities.md`
- `docs/it/dbzero/anagrafiche/tabelle/istanze_utilities.md`

Stato:

- RISOLTO (15-02-2026).
- Allineata la manualistica di `istanze_utilities`:
  - naming corrente `codice` (non `codice_istanza`),
  - trigger correnti (`..._normalize`, `..._gen_codice`, `..._gen_tx_id`, audit),
  - riferimenti funzione aggiornati.

---

### 3.2 Naming eterogeneo `utility_id` vs `utilities_id`  **(CHIUSO)**

Problema:

- nel dominio convivono naming diversi (`utility_id` in molte tabelle, `utilities_id` in PDP e viste collegate).

Rischio:

- maggiore probabilita di bug in query/join, mapping DTO e serializzazione API;
- maggiore costo cognitivo nel backend.

Riferimenti:

- `docs/it/dbzero/anagrafiche/tabelle/pdp.md`
- `docs/it/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio.md`
- `docs/it/dbzero/anagrafiche/tabelle/clienti.md`
- `docs/it/dbzero/anagrafiche/tabelle/billing_account.md`

Stato:

- RISOLTO (15-02-2026) lato documentale.
- Inserita nota esplicita di mapping naming:
  - `utilities_id` nel perimetro PDP/vista dettaglio istanza,
  - `utility_id` in `clienti` e `billing_account`.
- Corrette anche alcune tipizzazioni descrittive errate nella vista `vw_istanze_utilities_dettaglio`.

---

### 3.3 Matrice configurativa: stato reale, gap e azioni

Cosa e stato verificato:

- la matrice indirizzi per ruolo esiste: `config.tipi_ruolo_tipi_indirizzo`;
- la matrice indirizzi per tipo soggetto dettaglio esiste: `config.tipi_soggetto_dettaglio_tipi_indirizzo`;
- i guard su indirizzi e required si appoggiano gia a queste matrici;
- e presente la policy utility `richiede_pdp` su `config.utilities`.

Cosa manca (gap reale):

- non esiste una matrice generale `utility -> tipo_soggetto` e `utility -> tipo_ruolo` per governare ammissibilita cross-dominio;
- quindi la regola "quali ruoli/soggetti sono ammessi per una utility" non e configurata in modo esplicito e centralizzato;
- il comportamento fail-open delle matrici indirizzi (se assenti: nessuna restrizione) resta un rischio operativo in ambienti non completamente configurati.

Impatto:

- possibile disallineamento tra aspettative funzionali e comportamento effettivo;
- maggiore dipendenza da convenzioni applicative implicite;
- maggiore rischio di data quality non uniforme tra ambienti.

Cosa aggiornare in documentazione (esiste ma non era esplicitato):

1. esplicitare in modo univoco che le matrici indirizzi gia presenti sono:
   - `config.tipi_ruolo_tipi_indirizzo`
   - `config.tipi_soggetto_dettaglio_tipi_indirizzo`
2. esplicitare che la policy utility oggi copre solo `richiede_pdp` (non copre ammissibilita ruoli/soggetti);
3. esplicitare il comportamento fail-open attuale e quando puo essere accettabile;
4. aggiungere una nota architetturale che separi:
   - governance indirizzi (coperta),
   - governance utility->ruolo/soggetto (non ancora coperta).

Cosa sviluppare:

1. introdurre una nuova matrice configurativa per ammissibilita utility:
   - opzione A: `config.utilities_tipi_ruolo`
   - opzione B: `config.utilities_tipi_soggetto_dettaglio`
   - opzione C: entrambe (consigliata per chiarezza semantica)
2. aggiungere guard DB che validino la coerenza utility con ruolo/soggetto nei punti di ingresso principali (es. clienti/istanze/billing account secondo ownership);
3. aggiungere pgtap dedicati:
   - caso ammesso,
   - caso non ammesso,
   - caso matrice assente (comportamento esplicito: fail-open o fail-closed);
4. dopo introduzione matrice utility, rivalutare policy default:
   - mantenere fail-open solo dove serve per bootstrap,
   - portare fail-closed negli ambienti operativi stabili.

Riferimenti:

- `db/changelog/migrations_v2/00_schema/config/20251129-01-ruoli-tipi-indirizzo-mctit.yaml`
- `db/changelog/migrations_v2/00_schema/config/20251218-06-create-tipi-soggetto-dettaglio-tipi-indirizzo-mctit.yaml`
- `db/changelog/migrations_v2/00_schema/config/20260215-01-add-richiede-pdp-utilities-mctit.yaml`
- `docs/it/dbzero/config/manual/tipi_ruolo_tipi_indirizzo.md`
- `docs/it/dbzero/config/manual/tipi_soggetto_dettaglio_tipi_indirizzo.md`
- `docs/it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_guard_indirizzi_required.md`
- `docs/it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_indirizzi_required.md`

---

### 3.4 Incoerenza narrativa tra guide su indirizzi per ruolo vs soggetto

Problema:

- la guida soggetti/ruoli enfatizza l'appoggio indirizzi sul ruolo;
- la guida indirizzi formalizza anche il layer identitario su soggetto.

Rischio:

- ambiguita nelle scelte di modellazione dei nuovi processi;
- possibili duplicazioni evitabili tra indirizzo identitario e operativo.

Riferimenti:

- `docs/it/guide/soggetti-e-ruoli-anagrafici.md`
- `docs/it/guide/gestione-degli-indirizzi.md`

---

### 3.5 Punto da verificare: indice geoloc documentato come GIST ma definito BTREE

Problema:

- in documentazione tabellare l'indice `ix_indirizzi_geoloc_gist` e riportato con definizione BTREE.

Rischio:

- possibile mismatch tra naming e implementazione effettiva;
- rischio performance su query spaziali se l'indice reale non e coerente al tipo dati/uso.

Riferimenti:

- `docs/it/dbzero/anagrafiche/tabelle/indirizzi.md`
- `docs/it/dbzero/anagrafiche/tabelle/indirizzi_dettaglio.md`

## 4. Migliorie architetturali raccomandate

1. Definire una source-of-truth unica per utility istanza (non implicita).
2. Riallineare documentazione core con naming e trigger reali.
3. Esplicitare formalmente la semantica dei guard (deferred/immediate) nei contratti applicativi.
4. Formalizzare la policy "indirizzo master" (soggetto vs ruolo) per ciascun processo.
5. Avviare backend anagrafiche con perimetro minimo ma completo (service + API + test).

## 5. Backend anagrafiche: cosa serve per iniziare (piano di avvio)

Questa sezione e pensata per l'avvio imminente del backend, mantenendo il DB come source-of-truth di regole e vincoli.

### 5.1 Obiettivi del primo avvio

- non duplicare nel backend le regole gia garantite da trigger/vincoli DB;
- introdurre orchestrazione applicativa e contratti API stabili;
- rendere osservabili gli errori dominio in modo uniforme.

### 5.2 Struttura minima consigliata

- `backend/apps/anagrafiche/db/`:
  - repository SQL espliciti per use case principali
  - funzioni helper per read model (liste, dettaglio, search)
- `backend/apps/anagrafiche/services/`:
  - orchestrazione transazionale (create/update soggetto, assegna ruolo, collega indirizzi, crea istanza)
  - mapping errori DB -> `ServiceError` (senza `try/except Exception` generici)
- `backend/apps/anagrafiche/api/`:
  - endpoint versionati `/api/v1/anagrafiche/...`
  - payload validati via helper core e response envelope uniforme

### 5.3 Use case MVP (ordine consigliato)

1. create/update soggetto
2. assegna ruolo a soggetto
3. aggiungi/aggiorna indirizzo soggetto
4. aggiungi/aggiorna indirizzo ruolo
5. create istanza utility
6. create cliente su istanza con billing account coerente

### 5.4 Contratti ed error handling

- standardizzare codici errore dominio per:
  - ruolo non coerente
  - indirizzo obbligatorio mancante
  - utility mismatch cliente/billing account
  - incoerenza PDP/indirizzo/fittizia
- mappare gli errori con policy centrale (`error_policies`) per coerenza API/UI.

### 5.5 Test minimi necessari all'avvio

- test service per ciascun use case MVP
- test API happy path + casi guard principali
- test integrazione DB per casi deferred (commit-time failure)
- smoke test di regressione su funzioni trigger critiche

## 6. Roadmap di remediation (3 sprint)

### Sprint 1 - Allineamento modello/documentazione e decisioni architetturali

Obiettivi:

- decidere ownership ufficiale della utility istanza;
- riallineare documenti core (`soggetti_ruoli`, `istanze_utilities`, guida istanze);
- formalizzare semantica guard deferred/immediate.
- definire policy su matrici fail-open/fail-closed e allineare le guide.
- normalizzare nomenclatura (`utility_id` vs `utilities_id`) a livello di contract documentale.

Deliverable:

- ADR breve su utility ownership;
- documentazione aggiornata e coerente;
- checklist di coerenza transazionale pubblicata.
- decisione formale su fail-open/fail-closed per matrici indirizzi.

### Sprint 2 - Avvio backend anagrafiche (MVP operativo)

Obiettivi:

- implementare repository + service + API per use case MVP prioritari;
- integrare error mapping uniforme;
- coprire i casi principali con test service/API.
- introdurre test specifici sui casi "matrice assente" per evitare regressioni silenti.

Deliverable:

- primi endpoint `/api/v1/anagrafiche/...` attivi;
- suite test iniziale su soggetti/ruoli/indirizzi/istanze;
- linee guida backend anagrafiche aggiornate.

### Sprint 3 - Hardening cross-dominio e controllo qualita

Obiettivi:

- completare i casi su cliente-istanza-billing-PDP;
- introdurre validazioni pre-run/consistency checks trasversali;
- consolidare osservabilita e regressione.
- verificare e correggere eventuali mismatch indici geoloc (naming/engine/uso query).

Deliverable:

- test end-to-end su catena istanza -> cliente -> PDP;
- report coerenza periodico (query diagnostiche + test automatici);
- readiness per estensione funzionale successiva.
- verifica prestazionale su query geografiche e piano di ottimizzazione indici.

## 7. Decisione operativa proposta

Procedere con:

1. allineamento documentale + decisione utility ownership (Sprint 1),
2. avvio backend MVP anagrafiche con use case essenziali (Sprint 2),
3. hardening cross-dominio e stabilizzazione (Sprint 3).

Questo ordine riduce il rischio di implementare API su concetti non ancora stabilizzati e permette di partire subito con uno sviluppo backend ordinato, come previsto.
