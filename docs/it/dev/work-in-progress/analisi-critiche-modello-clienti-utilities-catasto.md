# Analisi Critiche – Modello Clienti, Utilities, Catasto e Subentro

Data analisi: 01-03-2026
Ambito: revisione critica su catena trigger subentro, billing_account gerarchico, vincoli istanze,
flusso disdetta, relazione soggetti-istanze, sequenza temporale creazione entita, catasto.

## 1. Scopo e perimetro

Questo documento raccoglie e analizza le criticita emerse dalla revisione della guida
[Generazione di un cliente](/guide/generazione-cliente), della guida
[Gestione delle Istanze Utility](/guide/gestione-delle-istanze-utility) e della documentazione
tecnica correlata (tabelle, funzioni, trigger manuali).

Per ciascun punto viene indicato:

- **Tipo**: `DESIGN` (scelta progettuale da riconsiderare), `DOC` (solo correzione documentale),
  `GAP` (funzionalita mancante da sviluppare)
- **Gravita**: ALTA / MEDIA / BASSA
- **Stato**: APERTO / IN ANALISI / CHIUSO / RISOLTO
- **Azione**: cosa serve (solo doc, sviluppo, o entrambi)

Riferimenti trasversali:

- [Guida Generazione Cliente](/guide/generazione-cliente)
- [Guida Gestione Istanze Utility](/guide/gestione-delle-istanze-utility)
- [Guida Soggetti e Ruoli](/guide/soggetti-e-ruoli-anagrafici)
- [anagrafiche.istanze_utilities – doc auto](/dbzero/anagrafiche/tabelle/istanze_utilities)
- [anagrafiche.billing_account – doc auto](/dbzero/anagrafiche/tabelle/billing_account)
- [anagrafiche.clienti – doc auto](/dbzero/anagrafiche/tabelle/clienti)
- [script.fn_subentro_cliente – doc auto](/dbzero/script/funzioni/fn_subentro_cliente)
- [Analisi gravita precedente](/dev/work-in-progress/analisi-gravita-anagrafiche-indirizzi-soggetti-istanze)
- [Modello fatturazione utilities](/dev/work-in-progress/fatturazione-modello-utilities-gas-ee-idrico)

---

## 2. Findings

### 2.1 Catena trigger subentro: atomicita e gestione fallimenti

**Tipo**: DOC + DESIGN (verifica)
**Gravita**: ALTA
**Stato**: RISOLTO

#### Problema

La catena di trigger che scatta durante un subentro coinvolge almeno 4-5 trigger in cascata:

1. `trgfn_clienti_set_parent_istanza` (BEFORE INSERT su `clienti`) → UPDATE su `istanze_utilities.parent_istanza_id`
2. `trg_iu_z50_clone_catasto_from_parent_aft_upd` (AFTER UPDATE su `istanze_utilities`) → INSERT su `catasto_unita_immobiliari` + UPDATE su `istanze_utilities.catasto_unita_immobiliare_id`
3. `trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd` (AFTER INSERT/UPDATE su `istanze_utilities`) → INSERT su `catasto_unita_immobiliari_indirizzi`
4. `trgfn_clienti_sync_stato_pdp` (AFTER INSERT/UPDATE su `clienti`) → UPDATE su `pdp.stato_pdp_id`
5. Trigger di storicizzazione, audit, tx_id su ciascuna tabella toccata

Ogni trigger presuppone che il precedente abbia completato correttamente.

#### Analisi

**Aspetto positivo non documentato**: PostgreSQL esegue tutti questi trigger all'interno della stessa transazione. Se un trigger intermedio fallisce (es. `clone_catasto_from_parent` non trova il catasto sorgente), l'intera transazione fa **rollback atomico**. Non esistono stati parziali.

**Problema reale**: la documentazione della guida generazione-cliente (appendice subentro) e la nota finale dicono:

> "Questo flusso e progettato per essere deterministico, idempotente e auditabile"

Ma **non spiega mai esplicitamente** che il subentro e atomico a livello transazionale. Questo e un punto critico per chi non conosce il comportamento di PostgreSQL con trigger in cascata.

Inoltre:

- La funzione `fn_subentro_cliente` nella sua implementazione reale (`script.fn_subentro_cliente`) fa **solo la chiusura** del cliente precedente (return id del cliente chiuso). La creazione di istanza, billing_account e nuovo cliente e delegata al chiamante (frontend/servizio). Questo e documentato nella doc manuale della funzione ma **non e chiaro nella guida principale**, che presenta il flusso come se fosse tutto automatico.
- La doc manuale di `fn_subentro_cliente` descrive una firma concettuale con 4 parametri (`p_pdp_id, p_soggetto_id_new, p_data_attivazione, p_opzioni`), ma l'implementazione reale ha solo 2 parametri (`p_pdp_id, p_data_attivazione`). C'e un **disallineamento** tra documentazione concettuale e implementazione.

#### Azione richiesta

1. **DOC** – Aggiungere nella guida generazione-cliente (appendice subentro) una nota esplicita:
   - "L'intero flusso di subentro avviene all'interno di una singola transazione PostgreSQL. Se un qualsiasi trigger della catena fallisce, tutte le operazioni vengono annullate (rollback atomico). Non esistono stati parziali."
   - Chiarire che `fn_subentro_cliente` copre **solo** la chiusura del precedente, e che la creazione del nuovo ciclo (istanza + BA + cliente) e a carico del chiamante.

2. **DOC** – Riallineare la doc manuale `script/manual/fn_subentro_cliente.md`:
   - La firma concettuale (4 parametri) non corrisponde all'implementazione (2 parametri).
   - Decidere: la doc descrive lo stato futuro (funzione completa) o lo stato attuale (solo chiusura)?
   - Aggiungere una nota chiara sulla discrepanza.

3. **DESIGN (verifica)** – Valutare se consolidare l'intera operazione di subentro in una singola funzione DB (come descritto nella doc concettuale) per evitare che il chiamante debba orchestrare correttamente 4-5 step. Questo ridurrebbe la superficie di errore applicativo.
   - **Decisione**: l'orchestrazione complessa va in Django (come `LottoPipelineRunner`), le guard atomiche e la logica pura restano nel DB. Vedi sezione 5 (Orchestrator Django).

---

### 2.2 billing_account gerarchico (parent_account_id): analisi completata

**Tipo**: DOC + DESIGN (chiarimento)
**Gravita**: ALTA
**Stato**: RISOLTO (analisi) — resta DOC da aggiornare

#### Problema originale

Il modello `billing_account` supporta una gerarchia padre/figlio tramite `parent_account_id`,
ma la documentazione non chiariva ne la semantica, ne l'impatto sulla pipeline fatturazione,
ne la tracciabilita del BA figlio nelle tabelle di vendita.

#### Analisi completata

**Tracciabilita BA nella catena di fatturazione** — il modello e gia corretto:

| Tabella                | Colonna                   | Contiene                                                  | Sempre valorizzata? |
| ---------------------- | ------------------------- | --------------------------------------------------------- | ------------------- |
| `attivita_fatturabili` | `billing_account_id`      | **CHILD BA** (originale, mai risolto al padre)            | Si                  |
| `fatture`              | `billing_account_id`      | **PARENT BA** (risolto da `fn_build_fattura_key` riga 54) | Si                  |
| `fatture_righe`        | `dest_billing_account_id` | **CHILD BA** (preservato per tracciabilita)               | Si                  |

Flusso dettagliato:

1. `fn_build_fattura_key` riga 54: `COALESCE(ba.parent_account_id, a.billing_account_id)` → risolve al padre (se esiste) per la testata fattura
2. `fn_group_attivita_fatturabili` → estrae `a.billing_account_id` (child) come `dest_billing_account_id` — commento nel codice: *"dest_billing_account = BA reale (mai parent)"*
3. `fn_generate_fatture_righe` → inserisce `dest_billing_account_id` nelle righe fattura dal valore del punto 2
4. `trgfn_fatture_righe_guard_normalize` → fallback: se `dest_billing_account_id` e NULL, eredita da `fatture.billing_account_id` (non dovrebbe mai succedere nel flusso normale)

**Risalita padre → figlio**: `fatture.billing_account_id` (padre) → `fatture_righe.dest_billing_account_id` (figlio) → `attivita_fatturabili.fattura_riga_id` (back-link alla riga). **Non serve una colonna `ba_child` aggiuntiva.**

**Flag `fattura_aggregata` non necessario**: la semantica e gia chiara:

- `parent_account_id IS NULL` → BA stand-alone o padre, fattura per se stesso
- `parent_account_id IS NOT NULL` → BA figlio, il COALESCE risolve al padre automaticamente
- Se non si vuole aggregare un figlio al padre, **basta non impostare `parent_account_id`**
- Aggiungere un flag separato creerebbe ridondanza e uno stato incoerente (`parent_account_id` impostato ma aggregazione disabilitata)

**Guard dissociazione parent**: una volta che un BA ha `parent_account_id` impostato e ci sono attivita/fatture collegate, la rimozione di `parent_account_id` va protetta con una guard nel trigger `trgfn_billing_account_guard_normalize`. Vedi sezione 5 per lo sviluppo.

#### Azione richiesta

1. **DOC** – Aggiornare `anagrafiche/manual/billing_account.md`:
   - Sezione "Tracciabilita BA nella pipeline fatturazione" con la tabella sopra
   - Nota: "Il BA figlio e sempre preservato in `fatture_righe.dest_billing_account_id`"
   - Nota: "La risoluzione al padre e incondizionata: se `parent_account_id` e valorizzato, la fattura va al padre"

2. **DOC** – Aggiornare guida generazione-cliente con una nota sulla gerarchia BA

3. **GAP (sviluppo)** – Guard dissociazione parent (vedi sezione 5.1.1)

---

### 2.3 Vincolo "nessuna istanza attiva sullo stesso indirizzo_dettaglio_id": ambiguita multi-utility

**Tipo**: DOC (chiarimento urgente)
**Gravita**: MEDIA
**Stato**: RISOLTO

#### Problema

La guida generazione-cliente afferma:

> "Nessuna istanza puo essere attiva contemporaneamente sullo stesso `indirizzo_dettaglio_id`."

Questo vincolo, preso alla lettera, impedirebbe di avere sullo stesso civico un'istanza GAS e un'istanza ENERGIA attive contemporaneamente — scenario normale in una multi-utility.

#### Analisi

Esaminando il modello reale:

- La tabella `istanze_utilities` **non ha** un vincolo UNIQUE su `indirizzo_dettaglio_id` da solo.
- Il vincolo di unicita effettivo e sulla tabella `clienti` con l'indice di esclusione `ex_clienti_no_overlap_stesso_pdp` che opera su `(pdp_id, periodo)` — cioe **per PDP**, non per indirizzo.
- Il PDP ha vincolo `UNIQUE (indirizzo_dettaglio_id, utility_id)` — un solo PDP per utility per indirizzo.

Quindi il vincolo reale e: **un solo cliente attivo per PDP** (e quindi per combinazione indirizzo + utility), **non** un solo cliente per indirizzo in assoluto.

La frase nella guida e **fuorviante** e va corretta.

#### Azione richiesta

1. **DOC** – Correggere nella guida generazione-cliente la frase:
   - Da: "Nessuna istanza puo essere attiva contemporaneamente sullo stesso `indirizzo_dettaglio_id`."
   - A: "Per ciascun PDP (combinazione indirizzo + utility), puo esistere al massimo un cliente attivo. Sullo stesso indirizzo possono coesistere istanze attive di utility diverse (es. GAS e ENERGIA)."

2. **DOC** – Aggiungere nella guida gestione istanze utility un esempio esplicito multi-utility:
   - Civico X ha PDP_GAS e PDP_ENERGIA
   - Ciascuno ha la propria istanza e il proprio cliente attivo
   - Nessun conflitto: il vincolo opera per PDP, non per indirizzo

---

### 2.4 Flusso inverso mancante: disdetta senza subentro

**Tipo**: GAP
**Gravita**: ALTA
**Stato**: RISOLTO — `script.fn_disdetta_cliente` implementata + pgTAP test (DB-04..09)

#### Problema

La documentazione copre in dettaglio il subentro (cliente esce, cliente entra sullo stesso PDP).
Ma non documenta ne implementa il flusso di **disdetta senza subentro** (cessazione):

- Il cliente disdice il servizio
- Nessun nuovo intestatario subentra
- Cosa succede all'istanza? Al billing_account? Al PDP?

In un'azienda utility questo e un flusso frequente quanto il subentro.

#### Analisi

Elementi gia presenti nel modello che supportano la disdetta:

- `config.stati_cliente`: esiste lo stato `CH` (chiuso) usato gia nel subentro
- `config.stati_pdp`: esiste lo stato `DISP` (disponibile) — il PDP torna disponibile quando il cliente viene chiuso
- Il trigger `trgfn_clienti_sync_stato_pdp` gia gestisce: `CH → PDP DISPONIBILE`
- Il modello di `fn_subentro_cliente` gia gestisce il caso "nessun cliente attivo" come prima attivazione

Cosa **manca**:

1. **Nessuna funzione dedicata** `fn_disdetta_cliente(p_cliente_id, p_data_cessazione)` che incapsuli:
   - chiusura del cliente con data cessazione
   - transizione stato cliente → CH
   - (automatico via trigger) PDP torna DISPONIBILE
   - (opzionale) chiusura billing_account (`valido_al`)

2. **Nessuna documentazione** del flusso di cessazione nella guida generazione-cliente ne nella guida istanze utility.

3. **Nessuna chiarezza** su cosa succede al billing_account dopo la disdetta:
   - Resta attivo (per eventuali fatture finali / conguagli)?
   - Va chiuso con `valido_al`?
   - Puo essere riutilizzato da un futuro subentro dello stesso soggetto?

4. **Nessuna chiarezza** sullo stato dell'istanza dopo la disdetta:
   - L'istanza non ha un campo `stato` proprio
   - La "chiusura" dell'istanza e implicita (il suo cliente e chiuso)
   - Va documentato che l'istanza resta nel DB come record storico

#### Azione richiesta

Sviluppo pianificato nella sezione 5.1.2 (`script.fn_disdetta_cliente`) + documentazione.

---

### 2.5 Relazione soggetti → istanze_utilities: incoerenza con modello soggetto/ruolo

**Tipo**: DESIGN (chiarimento) + DOC
**Gravita**: MEDIA
**Stato**: RISOLTO

#### Problema

Il diagramma ER nella guida generazione-cliente mostra:

```
soggetti ||--o{ istanze_utilities : has
```

L'istanza e collegata direttamente al `soggetto_id` (UUID), non al ruolo. Ma il modello soggetto/ruolo e costruito per separare l'identita dal ruolo funzionale. Se un soggetto e cliente gas e cliente energia, le istanze di entrambi i servizi sono appese allo stesso soggetto senza distinzione di ruolo.

#### Analisi

Esaminando il modello:

- `istanze_utilities.soggetto_id` → FK diretta a `anagrafiche.soggetti(id)`
- `clienti.soggetto_ruolo_id` → FK a `anagrafiche.soggetti_ruoli(id)` (ruolo CLIENTE)
- `billing_account.soggetto_ruolo_id` → FK a `anagrafiche.soggetti_ruoli(id)`

La scelta progettuale ha una **ragione specifica**: l'istanza rappresenta un punto di erogazione fisico e un ciclo tecnico-commerciale. Essa **precede** il ruolo:

1. L'istanza nasce in fase pre-contrattuale, quando il soggetto potrebbe non avere ancora il ruolo CLIENTE
2. L'istanza identifica il "chi" solo come soggetto fisico/giuridico (chi abita/possiede al civico)
3. Il ruolo CLIENTE viene assegnato dopo, quando il soggetto firma il contratto

Inoltre, l'istanza non e "del cliente" ma "del servizio al civico per quel soggetto". Il ruolo arriva con la specializzazione in `clienti`.

Questa logica e corretta ma **non documentata**.

#### Azione richiesta

1. **DOC** – Aggiungere nella guida gestione istanze utility (e nella guida generazione-cliente) una nota progettuale che spieghi:
   - Perche l'istanza e legata al soggetto e non al ruolo
   - L'istanza precede il ruolo: esiste in fase pre-contrattuale
   - Il ruolo CLIENTE e la specializzazione commerciale dell'istanza, non l'ownership
   - La distinzione per utility avviene tramite il PDP e il billing_account, non tramite il soggetto

2. **DOC** – Aggiungere un esempio esplicito:
   - Soggetto "Mario Rossi" ha istanza GAS e istanza ENERGIA
   - Entrambe puntano a `soggetti.id` di Mario Rossi
   - Il ruolo CLIENTE e unico (un solo record in `soggetti_ruoli` con tipo_ruolo=CL)
   - I due record `clienti` (uno per istanza) puntano allo stesso `soggetto_ruolo_id`

---

### 2.6 Sequenza temporale creazione entita: ordine obbligatorio non esplicitato

**Tipo**: DOC + GAP
**Gravita**: MEDIA
**Stato**: DOC RISOLTO — orchestrator Django pianificato (vedi sezione 5.2)

#### Problema

La documentazione dice che si puo creare il billing_account prima del cliente (fase precontrattuale) e che le colonne `istanza_utilities_id` su clienti e billing_account devono essere NOT NULL. Ma la **sequenza obbligatoria** di creazione non e esplicitata step-by-step.

#### Analisi

Dalla struttura dei vincoli e delle FK:

**Ordine obbligatorio**:

1. `anagrafiche.soggetti` — deve esistere il soggetto
2. `anagrafiche.soggetti_ruoli` — deve esistere il ruolo CLIENTE (puo essere creato contestualmente tramite `fn_get_or_create_soggetto_ruolo`)
3. `anagrafiche.istanze_utilities` — necessita `soggetto_id` (NOT NULL)
4. `anagrafiche.billing_account` — necessita `istanza_utility_id` (NOT NULL) e `soggetto_ruolo_id` (NOT NULL)
5. `anagrafiche.clienti` — necessita `istanza_utility_id` (NOT NULL), `billing_account_id` (NOT NULL), `soggetto_ruolo_id` (NOT NULL)

**Vincoli che confermano l'ordine**:

- Non si puo creare un BA senza istanza (`istanza_utility_id NOT NULL`)
- Non si puo creare un cliente senza BA e istanza
- La FK composita `(billing_account_id, istanza_utility_id)` su clienti garantisce che il BA appartenga alla stessa istanza
- Non si puo creare un'istanza senza soggetto

**Flusso pre-contrattuale**:

1. Soggetto → 2. Istanza → 3. Billing Account → (pausa contrattuale) → 4. Ruolo CLIENTE → 5. Cliente

**Flusso attivazione diretta**:

1. Soggetto + Ruolo CLIENTE → 2. Istanza → 3. Billing Account → 4. Cliente

**Cosa non si puo fare**:

- Creare un cliente senza billing_account: `billing_account_id NOT NULL`
- Creare un billing_account senza istanza: `istanza_utility_id NOT NULL`
- Creare un'istanza senza soggetto: `soggetto_id NOT NULL`

#### Azione richiesta

1. **DOC** – Aggiungere nella guida generazione-cliente una sezione "Sequenza obbligatoria di creazione" con:
   - Diagramma sequenziale step-by-step
   - Distinzione tra flusso pre-contrattuale e attivazione diretta
   - Elenco esplicito di "cosa non si puo fare" (violazioni di sequenza)
   - Nota sulla transazionalita: tutti gli step possono avvenire nella stessa transazione (trigger deferred)

2. **GAP (sviluppo)** – Orchestrator Django `ClienteService` che incapsula la sequenza completa. Vedi sezione 5.2.

---

### 2.7 Catasto: sotto-sistema da documentare separatamente

**Tipo**: DOC
**Gravita**: MEDIA
**Stato**: RISOLTO

#### Problema

I dati catastali sono distribuiti tra:

- `anagrafiche.catasto_unita_immobiliari` — record catastale
- `anagrafiche.catasto_unita_immobiliari_indirizzi` — tabella ponte catasto ↔ indirizzo
- `anagrafiche.istanze_utilities.catasto_unita_immobiliare_id` — FK dall'istanza al catasto
- Trigger `trgfn_iu_clone_catasto_from_parent` — clonazione catasto nel subentro
- Trigger `trgfn_iu_sync_catasto_unita_indirizzo` — sync tabella ponte
- Funzione `fn_get_catasto_source_by_istanza` — lookup sorgente catasto
- Funzione `fn_clone_catasto_from_parent_by_istanza` — logica di clonazione

Uno sviluppatore che deve fare manutenzione sul catasto deve leggere la guida generazione-cliente (appendice subentro), la guida istanze utility, e ricostruire il puzzle tra 4 documenti di funzioni/trigger.

#### Analisi

Il catasto e un sotto-sistema con la propria logica, le proprie regole e i propri trigger. Meriterebbe almeno una sezione strutturata dedicata che unisca tutti i pezzi.

Il modello catastale segue questa architettura:

- Il catasto e un'entita autonoma (non dipende dal cliente)
- Il legame con l'istanza e 1:1 (FK su `istanze_utilities`)
- Il legame con l'indirizzo e N:M (tabella ponte)
- Nel subentro, il catasto viene **clonato** (non condiviso) per mantenere indipendenza storica
- La sorgente per la clonazione e la parent istanza (e solo quella)

#### Azione richiesta

1. **DOC** – Creare un documento dedicato `docs/it/dbzero/anagrafiche/manual/catasto-architettura.md` (o sezione nella guida generazione-cliente) che riunisca:
   - Modello dati catastale (tabelle, relazioni, vincoli)
   - Ciclo di vita del catasto (creazione, clonazione, versioning)
   - Flusso subentro catasto con diagramma sequenziale dei trigger
   - Regole: il catasto non e mai condiviso, sempre clonato
   - Riferimenti a tutte le funzioni/trigger coinvolti

---

### 2.8 Glossario dominio utility mancante

**Tipo**: DOC
**Gravita**: BASSA
**Stato**: RISOLTO

#### Problema

La documentazione assume conoscenza del dominio utility italiano. Termini come PDP, PDR, POD, istanza, billing_account, subentro, voltura non sono mai definiti formalmente.

Per i destinatari dichiarati (sviluppatori e analisti da altri settori), un glossario minimo all'inizio della guida farebbe una differenza enorme nell'onboarding.

#### Azione richiesta

1. **DOC** – Aggiungere un glossario minimo in testa alla guida generazione-cliente (o come documento separato `docs/it/guide/glossario-utility.md`):

Termini minimi da includere:

| Termine               | Significato nel contesto ZeroErp                                                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| PDP                   | Punto Di Prelievo – entita fisica che identifica il contatore/allaccio. Equivalente a POD (energia) o PDR (gas)                                    |
| POD                   | Point Of Delivery – codice identificativo del punto di prelievo per energia elettrica                                                              |
| PDR                   | Punto Di Riconsegna – codice identificativo del punto di prelievo per gas naturale                                                                 |
| Istanza (utility)     | Ciclo tecnico-commerciale di un servizio su un indirizzo/PDP per un soggetto. Non e il cliente: precede e sopravvive al contratto                  |
| Billing Account (BA)  | Account di fatturazione collegato a un'istanza. Identifica "a chi fatturare" e puo esistere in fase pre-contrattuale                               |
| Subentro              | Passaggio di titolarita su un PDP da un cliente a un altro. Implica chiusura del precedente e creazione di un nuovo ciclo (istanza + BA + cliente) |
| Voltura               | Sinonimo di subentro nel contesto utility italiano                                                                                                 |
| Disdetta / Cessazione | Chiusura del servizio senza subentro. Il PDP torna disponibile                                                                                     |
| Parent istanza        | Istanza precedente nella catena di subentri sullo stesso PDP. Usata per tracciabilita storica e clonazione catasto                                 |

---

## 3. Riepilogo azioni

### Solo correzione documentale (DOC)

| ID   | Descrizione                                                       | Dove                                          | Stato  |
| ---- | ----------------------------------------------------------------- | --------------------------------------------- | ------ |
| 2.1a | Esplicitare atomicita transazionale della catena trigger          | Guida generazione-cliente, appendice subentro | RISOLTO |
| 2.1b | Chiarire che `fn_subentro_cliente` fa solo la chiusura            | Guida generazione-cliente                     | RISOLTO |
| 2.1c | Riallineare firma concettuale vs reale di `fn_subentro_cliente`   | `script/manual/fn_subentro_cliente.md`        | RISOLTO |
| 2.2a | Tracciabilita BA pipeline + casi d'uso gerarchia                  | `anagrafiche/manual/billing_account.md`       | RISOLTO |
| 2.3  | Correggere vincolo istanze da "per indirizzo" a "per PDP+utility" | Guida generazione-cliente                     | RISOLTO |
| 2.5  | Spiegare perche istanza → soggetto e non → ruolo                  | Guide generazione-cliente e istanze utility   | RISOLTO |
| 2.6  | Documentare sequenza obbligatoria di creazione                    | Guida generazione-cliente                     | RISOLTO |
| 2.7  | Creare documento/sezione dedicata al catasto                      | `anagrafiche/manual/catasto-architettura.md`  | RISOLTO |
| 2.8  | Glossario termini dominio utility                                 | `guide/glossario/glossario-utility.md`        | RISOLTO |

### Sviluppo richiesto (GAP)

| ID   | Descrizione                                                          | Priorita | Stato  |
| ---- | -------------------------------------------------------------------- | -------- | ------ |
| 2.2b | Guard dissociazione parent_account_id                                | ALTA     | RISOLTO (DB-01..03) |
| 2.4  | Funzione `fn_disdetta_cliente` + policy BA post-cessazione           | ALTA     | RISOLTO (DB-04..09) |
| 2.6b | Orchestrator Django `ClienteService` (creazione, subentro, disdetta) | ALTA     | APERTO |

### Design risolti

| ID   | Descrizione                                    | Decisione                                                                                                                         |
| ---- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 2.2c | Flag `fattura_aggregata` su billing_account    | **NON NECESSARIO** — la semantica e gia coperta da `parent_account_id`. Se non si vuole aggregare, basta non impostare il parent. |
| 2.2d | Colonna `ba_child` aggiuntiva su fatture_righe | **NON NECESSARIA** — `dest_billing_account_id` fa gia il lavoro. Sempre valorizzata con il child BA.                              |
| 2.1e | Orchestrazione subentro: DB o Django?          | **Django** — l'orchestrazione complessa va in Django (come `LottoPipelineRunner`), le guard atomiche restano nel DB.              |

---

## 4. Priorita di intervento suggerita

### Fase 1 – Sviluppo DB (guard + disdetta)

1. **2.2b** Guard dissociazione parent_account_id
2. **2.4** Funzione `fn_disdetta_cliente`
3. pgTAP test per entrambi

### Fase 2 – Sviluppo Django (orchestrator)

1. **2.6b** Repository + Service + Types + API + Test

### Fase 3 – Correzioni documentali

1. **2.3** Correzione vincolo istanze (fuorviante)
2. **2.1a/b/c** Atomicita e chiarimento `fn_subentro_cliente`
3. **2.2a** Tracciabilita BA pipeline
4. **2.6** Sequenza obbligatoria creazione
5. **2.5** Motivazione relazione soggetto-istanza
6. **2.8** Glossario dominio utility
7. **2.7** Documento architettura catasto

---

## 5. Piano di sviluppo

**Decisione architetturale**: l'orchestrazione complessa va in Django (come `LottoPipelineRunner`), le guard atomiche e la logica pura restano nel DB (trigger + funzioni).

### 5.1 Fase DB

#### 5.1.1 Guard dissociazione parent_account_id

**File**: `db/changelog/migrations_v2/20_code/anagrafiche/20260301-14-update-trgfn-billing-account-guard-normalize-mctit.yaml`

Aggiornare `trgfn_billing_account_guard_normalize` per bloccare la rimozione di `parent_account_id` quando esistono:

- `vendite.attivita_fatturabili` non fatturate (`fatturato = FALSE`) collegate al BA figlio
- `vendite.fatture_righe` con `dest_billing_account_id` che punta al BA figlio

Logica:

```sql
-- Se parent_account_id viene rimosso (era NOT NULL, diventa NULL)
IF OLD.parent_account_id IS NOT NULL AND NEW.parent_account_id IS NULL THEN
  -- Blocco se ci sono attivita non fatturate
  IF EXISTS (
    SELECT 1 FROM vendite.attivita_fatturabili
    WHERE billing_account_id = NEW.id AND fatturato IS FALSE
  ) THEN
    RAISE EXCEPTION 'Impossibile rimuovere parent: attivita non fatturate collegate';
  END IF;
END IF;
```

Il frontend dovra mostrare un warning prima di tentare la dissociazione, ma la guard DB e obbligatoria.

- [x] **DB-01** Aggiornare trigger `trgfn_billing_account_guard_normalize` con guard dissociazione parent
- [x] **DB-02** pgTAP test guard dissociazione: rimozione parent con attivita pendenti → errore
- [x] **DB-03** pgTAP test guard dissociazione: rimozione parent senza attivita → OK

#### 5.1.2 Funzione `script.fn_disdetta_cliente`

**File**: `db/changelog/migrations_v2/20_code/script/20260301-17-create-fn-disdetta-cliente-mctit.yaml`

Firma:

```sql
CREATE OR REPLACE FUNCTION script.fn_disdetta_cliente(
  p_cliente_id    BIGINT,
  p_data_cessazione DATE
) RETURNS BIGINT
LANGUAGE plpgsql
```

Logica:

1. Guard: `p_cliente_id` e `p_data_cessazione` NOT NULL
2. Legge cliente + stato → verifica stato = `AT` (attivo, codice_interno)
3. Verifica `p_data_cessazione >= data_attivazione`
4. UPDATE clienti: `data_chiusura = p_data_cessazione`, `stato_cliente_id = CH`
5. I trigger cascata fanno il resto:
   - `trgfn_clienti_set_periodo` → aggiorna `periodo` (daterange)
   - `trgfn_clienti_sync_stato_pdp` → PDP torna `DISPONIBILE`
   - `trgfn_storico_generic` → storicizzazione
   - `trgfn_audit_data_user_generic` → audit
6. RETURN `p_cliente_id`

**Policy BA post-disdetta**: il billing_account **non viene toccato**. Resta attivo per consentire fatture finali, conguagli e riconciliazioni. La chiusura del BA e un'operazione separata, da gestire quando tutti i documenti fiscali sono stati emessi.

- [x] **DB-04** Creare funzione `script.fn_disdetta_cliente`
- [x] **DB-05** pgTAP test: cliente attivo → disdetta → stato CH, periodo chiuso, PDP DISPONIBILE
- [x] **DB-06** pgTAP test: cliente non attivo → errore
- [x] **DB-07** pgTAP test: data cessazione < data attivazione → errore
- [x] **DB-08** pgTAP test: parametri NULL → errore
- [x] **DB-09** pgTAP test: BA resta attivo dopo disdetta (policy)

---

### 5.2 Fase Django: Orchestrator Cliente Unificato

#### 5.2.1 Repository: `backend/apps/anagrafiche/db/anagrafiche_repository.py`

Pattern: segue `vendite/db/pipeline_repository.py` (cursor.execute, guard fetchone, return typed).

Metodi:

| Metodo                                                                                                               | SQL                                                              |
| -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `get_soggetto(soggetto_id)`                                                                                          | SELECT da `anagrafiche.soggetti`                                 |
| `get_or_create_soggetto_ruolo(soggetto_id, codice_ruolo)`                                                            | `SELECT script.fn_get_or_create_soggetto_ruolo(...)`             |
| `create_istanza_utilities(soggetto_id, indirizzo_dettaglio_id, pdp_id, fittizia)`                                    | `INSERT INTO anagrafiche.istanze_utilities ... RETURNING id`     |
| `create_billing_account(istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id)`                       | `INSERT INTO anagrafiche.billing_account ... RETURNING id`       |
| `create_cliente(istanza_utility_id, billing_account_id, soggetto_ruolo_id, stato_cliente_id, data_attivazione, ...)` | `INSERT INTO anagrafiche.clienti ... RETURNING id`               |
| `close_previous_client(pdp_id, data_attivazione)`                                                                    | `SELECT script.fn_subentro_cliente(...)`                         |
| `disdetta_cliente(cliente_id, data_cessazione)`                                                                      | `SELECT script.fn_disdetta_cliente(...)`                         |
| `get_stato_cliente_by_codice(codice_interno)`                                                                        | `SELECT id FROM config.stati_cliente WHERE codice_interno = ...` |
| `get_utility(utility_id)`                                                                                            | `SELECT FROM config.utilities WHERE id = ...`                    |

- [ ] **DJ-01** Creare `backend/apps/anagrafiche/db/anagrafiche_repository.py` con tutti i metodi

#### 5.2.2 Types: `backend/apps/anagrafiche/types.py`

```python
@dataclass(frozen=True)
class CreaClienteParams:
    soggetto_id: str          # UUID
    indirizzo_dettaglio_id: int | None
    pdp_id: int | None
    utility_id: int
    data_attivazione: date
    fittizia: bool = False
    parent_ba_id: int | None = None
    # ... altri campi opzionali (iva_id, modalita_pagamento_id, ...)
```

- [ ] **DJ-02** Creare `backend/apps/anagrafiche/types.py` con `CreaClienteParams`

#### 5.2.3 Service: `backend/apps/anagrafiche/services/cliente_service.py`

```python
class ClienteService:
    def __init__(self, repository=None):
        self.repository = repository or AnagraficheRepository()

    def crea_cliente(self, params: CreaClienteParams) -> int:
        """
        Orchestrazione completa creazione cliente.
        Sequenza: soggetto → ruolo → [subentro] → istanza → BA → cliente.
        Atomico: tutti gli step nella stessa transazione.
        """
        with transaction.atomic():
            # 1. Validazione soggetto
            soggetto = self.repository.get_soggetto(params.soggetto_id)
            ErrorManager.require(soggetto is not None, "E_SOGGETTO_NOT_FOUND", ...)

            # 2. Get/create ruolo CLIENTE
            soggetto_ruolo_id = self.repository.get_or_create_soggetto_ruolo(
                params.soggetto_id, 'CL')

            # 3. Chiusura precedente (se PDP fornito)
            if params.pdp_id:
                self.repository.close_previous_client(
                    params.pdp_id, params.data_attivazione)

            # 4. Crea istanza
            istanza_id = self.repository.create_istanza_utilities(
                soggetto_id=params.soggetto_id,
                indirizzo_dettaglio_id=params.indirizzo_dettaglio_id,
                pdp_id=params.pdp_id,
                fittizia=params.fittizia)

            # 5. Crea billing account
            ba_id = self.repository.create_billing_account(
                istanza_utility_id=istanza_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=params.utility_id,
                parent_account_id=params.parent_ba_id)

            # 6. Crea cliente
            stato_at = self.repository.get_stato_cliente_by_codice('AT')
            cliente_id = self.repository.create_cliente(
                istanza_utility_id=istanza_id,
                billing_account_id=ba_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                stato_cliente_id=stato_at,
                data_attivazione=params.data_attivazione,
                ...)

            return cliente_id

    def disdetta_cliente(self, cliente_id: int, data_cessazione: date) -> int:
        """Cessazione senza subentro. BA resta attivo per fatture finali."""
        with transaction.atomic():
            return self.repository.disdetta_cliente(cliente_id, data_cessazione)

    def subentro_cliente(self, params: CreaClienteParams) -> int:
        """Alias: crea_cliente con pdp_id obbligatorio."""
        ErrorManager.require(params.pdp_id is not None, "E_PDP_REQUIRED", ...)
        return self.crea_cliente(params)
```

- [ ] **DJ-03** Creare `backend/apps/anagrafiche/services/cliente_service.py` con `ClienteService`

#### 5.2.4 API: `backend/apps/anagrafiche/api/views.py` + `urls.py`

| Endpoint                                         | Metodo             | Descrizione                          |
| ------------------------------------------------ | ------------------ | ------------------------------------ |
| `POST /api/v1/anagrafiche/clienti/`              | `crea_cliente`     | Creazione completa (con o senza PDP) |
| `POST /api/v1/anagrafiche/clienti/{id}/disdetta` | `disdetta_cliente` | Cessazione senza subentro            |
| `POST /api/v1/anagrafiche/clienti/subentro`      | `subentro_cliente` | Subentro (PDP obbligatorio)          |

Pattern: `handle_post_json` + `@extend_schema` per drf-spectacular.

- [ ] **DJ-04** Creare view + url per endpoint `crea_cliente`
- [ ] **DJ-05** Creare view + url per endpoint `disdetta_cliente`
- [ ] **DJ-06** Creare view + url per endpoint `subentro_cliente`

#### 5.2.5 Test Django

**File**: `backend/apps/anagrafiche/tests/services/test_cliente_service.py`

- Test con mock del repository (nessun DB reale in CI)
- Happy path: crea_cliente, subentro, disdetta
- Error path: soggetto non trovato, parametri mancanti, PDP obbligatorio per subentro

**File**: `backend/apps/anagrafiche/tests/api/test_cliente_api.py`

- Smoke test endpoint (mock service)

- [ ] **DJ-07** Test service: happy path crea_cliente
- [ ] **DJ-08** Test service: happy path subentro_cliente (con chiusura precedente)
- [ ] **DJ-09** Test service: happy path disdetta_cliente
- [ ] **DJ-10** Test service: error path soggetto non trovato
- [ ] **DJ-11** Test service: error path PDP obbligatorio per subentro
- [ ] **DJ-12** Test API: smoke test tutti gli endpoint

---

### 5.3 Ordine di esecuzione

| Step | Fase  | Cosa                          | Checkpoint          |
| ---- | ----- | ----------------------------- | ------------------- |
| 1    | 5.1.1 | Guard dissociazione parent BA | DB-01, DB-02, DB-03 |
| 2    | 5.1.2 | fn_disdetta_cliente           | DB-04..DB-09        |
| 3    | 5.2.1 | Repository anagrafiche        | DJ-01               |
| 4    | 5.2.2 | Types                         | DJ-02               |
| 5    | 5.2.3 | Service ClienteService        | DJ-03               |
| 6    | 5.2.4 | API views + urls              | DJ-04..DJ-06        |
| 7    | 5.2.5 | Test Django                   | DJ-07..DJ-12        |

### 5.4 Verifica

1. **pgTAP**: `scripts/testpgtap.sh db/pgtap/anagrafiche/test-billing-account-guard-parent.sql`
2. **pgTAP**: `scripts/testpgtap.sh db/pgtap/script/test-fn-disdetta-cliente.sql`
3. **Django tests**: `./manage-test.sh apps.anagrafiche.tests.services -v 2`
4. **Django tests**: `./manage-test.sh apps.anagrafiche.tests.api -v 2`
5. **CI**: tutti i test devono passare senza DB reale (mock per Django)

### 5.5 File di riferimento (pattern da seguire)

- Repository: `backend/apps/vendite/db/pipeline_repository.py`
- Service: `backend/apps/vendite/services/pipeline_runner.py`
- Error handling: `backend/apps/core/services/error_manager.py`
- API helper: `backend/apps/core/api/endpoint_helpers.py`
- DB function template: `docs/it/dbzero/script/funzioni/fn_subentro_cliente.md`
- pgTAP example: `db/pgtap/anagrafiche/` (existing tests)

---

*Documento WIP — aggiornare man mano che i punti vengono chiusi.*
