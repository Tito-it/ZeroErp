# Gestione commesse — Architettura e decisioni operative (v2 — 24-02-2026)

Questo documento consolida tutte le decisioni architetturali prese nelle sessioni di analisi
del 23-24/02/2026. Sostituisce la preanalisi `gestione-commesse.md` (v1).
Da consegnare al team DB come base per DB-0 → DB-5.

Riferimenti correlati:

- `docs/it/dev/work-in-progress/ripresa-lavori-attivita-fatturabili.md`
- `docs/it/dev/work-in-progress/gestione-commesse.md` (v1 — superato)

---

## 1) Obiettivo

Definire un modello scalabile per la gestione commesse che:

1. Supporti preventivi, ordini, consumi e sorgenti future (ticket, DDT, integrazioni CRM).
2. Supporti utilities (energia, gas, idrico) con fatturazione periodica e immediata.
3. Faccia transitare ogni emissione fatturabile attraverso la commessa — nessun bypass.
4. Semplifichi la pipeline attività fatturabili esistente (il pull diventa step 0 della pipeline
   di fatturazione, non una pipeline separata).
5. Sia estendibile senza refactor strutturale all'aggiunta di nuove sorgenti.

---

## 2) Flusso generale (decisione finale)

```
SORGENTI (preventivi / ordini / consumi / future)
        |
        | regole assegnazione (vedi §6)
        v
    COMMESSA
    (REALE o AUTO — sempre presente)
        |
        | pull (standalone o come step 0 della pipeline fatturazione)
        v
ATTIVITÀ FATTURABILI
    (materializzate dalla commessa, non più acquisite dalle sorgenti)
        |
        | pipeline fatturazione (step 1+)
        v
    FATTURA
```

**Cosa cambia rispetto al modello precedente:**

- La pipeline attività fatturabili (acquisizione da sorgenti sparse) **non esiste più**.
- Le sorgenti non scrivono direttamente in `attivita_fatturabili` — passano tutte per la commessa.
- Il pull commessa → attività fatturabili diventa lo **step 0** della pipeline di fatturazione,
  eseguibile anche in standalone per review/reportistica.
- La pipeline di fatturazione (lotti, documenti fiscali) **non cambia**.

---

## 3) Principi architetturali (invarianti)

1. **Commessa sempre presente** — ogni sorgente genera sempre una commessa (REALE o AUTO).
2. **Una sola sorgente root per commessa** — una commessa ha esattamente una sorgente primaria.
3. **Nessun bypass** — nessuna scrittura diretta in `attivita_fatturabili` senza `commessa_id`.
4. **Idempotenza by design** — stessa sorgente + stesso `segment_key` non produce doppioni.
5. **Pull sempre rieseguibile** — il passaggio commessa → attività fatturabili è idempotente.
6. **Prezzi con ownership su commessa, validazione in fatturazione** — la commessa salva
   `prezzo_snapshot`/`prezzo_bloccato`; la verifica finale avviene nello step prezzi della pipeline.
7. **Estendibile senza refactor** — aggiungere una nuova sorgente = registrare un nuovo handler,
   non toccare il modello core.

---

## 4) Tipi di commessa

### 4.1 Commessa AUTO

Generata automaticamente dal sistema quando la sorgente non richiede gestione operativa.

Casi d'uso:
- Preventivo con `fatturazione_immediata = TRUE` → commessa AUTO + chiusura immediata alla fattura.
- Preventivo con `fatturazione_immediata = FALSE` → commessa AUTO + ciclo periodico standard.
- Ordine semplice (monoprestazione evasa) → commessa AUTO.
- Consumi utility → commessa AUTO per accumulo mensile.

Lifecycle:

```
BOZZA → PRONTA_FATTURAZIONE → CHIUSA
```

- `CHIUSA` avviene automaticamente dopo emissione in `attivita_fatturabili` e conferma COMPLETED.
- Riapertura non prevista salvo correzione tecnica esplicita.
- Non ha gate operativi — emissione immediata appena le condizioni sono soddisfatte.

### 4.2 Commessa REALE

Richiede gestione operativa (task, worklog, milestone, approvazioni).

Casi d'uso:
- Progetto con SAL e milestone.
- Contratto con consuntivo approvabile.
- Servizi con gate operativo prima della fatturazione.

Lifecycle:

```
BOZZA → APERTA → [IN_ESECUZIONE] → PRONTA_FATTURAZIONE → CHIUSA
```

- Emissione in `attivita_fatturabili` subordinata ai gate operativi (approvazione/milestone/consuntivo).
- Priorità operativa (`ALTA` / `NORMALE` / `BASSA`) per ordinare la lavorazione — non bypassa i gate.

### 4.3 Fatturazione immediata — breaking change dichiarato

**Prima**: `fatturazione_immediata = TRUE` significava "documento direttamente fatturabile" senza
commessa.

**Da questa revisione**: `fatturazione_immediata = TRUE` significa:
1. Creazione commessa AUTO.
2. Creazione `commessa_attivita` tecnica.
3. Emissione immediata verso lotto giornaliero.

Il campo resta sul preventivo. Su ordini non previsto per ora (lasciato aperto per futuro).

---

## 5) Policy di fatturazione

Ogni commessa ha una policy che determina come si calcola l'importo fatturabile:

| Policy | Significato |
|---|---|
| `DA_DOCUMENTO` | Usa i valori del documento commerciale come base |
| `DA_CONSUNTIVO` | Usa solo le attività operative approvate |
| `MISTA` | Base documento + conguaglio da consuntivo |

**Specifica MISTA:**

1. Fase 1: emissione baseline da documento (quota iniziale deterministica).
2. Fase 2: conguaglio da consuntivo su `commesse_attivita` approvate.
3. Delta positivo → nuova `attivita_fatturabile` di conguaglio.
4. Delta negativo → nota di credito / attività negativa secondo policy fiscale.
5. Stessa finestra temporale + stesso `segment_key` non genera doppio conguaglio (idempotenza).

---

## 6) Gerarchia sorgenti e regole di assegnazione alla commessa

### 6.1 Gerarchia documenti

Ogni tipo di documento è classificato come **sorgente terminale** (può andare direttamente
sulla commessa) o **sorgente intermedia** (deve passare per un documento superiore).

```
Ticket (futuro)
  └→ Preventivo          ← sorgente terminale (se non convertito)
       └→ Ordine          ← sorgente terminale (sempre)
            └→ Commessa

Consumo utility           ← sorgente terminale (sempre)
  └→ Commessa

DDT                       ← sorgente terminale solo per beni fisici
                            NON sorgente per utilities
```

**Regola fissa**: solo le sorgenti terminali possono essere `ROOT` di una commessa.

### 6.2 Preventivo convertito in ordine — flag stato_commessa

Quando un preventivo viene accettato e genera un ordine, il sistema setta automaticamente:

```
preventivo.stato_commessa = CONVERTITO
```

Valori ammessi su `stato_commessa`:
- `LIBERO` — può andare su commessa come ROOT.
- `CONVERTITO` — è stato promosso a ordine, non può essere ROOT di una commessa.
- `ESCLUSO` — escluso manualmente.

**Conseguenza**: preventivo CONVERTITO + ordine nato da esso non possono mai produrre
doppia fatturazione sulla stessa commessa. L'ordine è l'unico ROOT.

### 6.3 Come una sorgente arriva sulla commessa — processore batch

Non una pipeline pesante — un **processore batch leggero** con handler registrati per tipo
sorgente:

```
HandlerPreventivi   — legge preventivi LIBERI, valida, assegna/crea commessa
HandlerOrdini       — legge ordini, valida, assegna/crea commessa
HandlerConsumi      — legge consumi utility, assegna/crea commessa AUTO mensile
HandlerFuturoXYZ    — aggiunto senza toccare il modello core
```

Caratteristiche:
- Eseguibile a piacimento (manuale o schedulato) — nessun vincolo di timing.
- Supporta `dry_run` — mostra cosa verrebbe assegnato senza scrivere.
- Segnala anomalie ma non blocca le altre sorgenti.
- Idempotente — rieseguibile senza duplicazioni.

---

## 7) Gestione prezzi e listini

### 7.1 Cosa salva la commessa per riga

Ogni riga commessa salva:

| Campo | Significato |
|---|---|
| `quantita` | Quantità della prestazione |
| `listino_versione_id` | Riferimento alla versione listino al momento del push |
| `data_competenza` | Periodo di riferimento |
| `prezzo_snapshot` | Prezzo al momento del push (per audit) |
| `prezzo_bloccato` | Se TRUE il prezzo non viene mai ricalcolato |
| `prezzo_da_riallineare` | Flag tecnico: TRUE se il documento sorgente `LIBERO` cambia prezzo dopo il push |

### 7.2 Policy prezzo per tipo sorgente

| Tipo sorgente | Policy prezzo |
|---|---|
| Preventivo `fatturazione_immediata` | Bloccato al push — non serve ricalcolo |
| Preventivo periodico | Ricalcolato alla fatturazione se listino è cambiato |
| Ordine | Bloccato alla conferma ordine |
| Consumo utility | Sempre calcolato dal listino del periodo di competenza |

### 7.3 Allineamento quando il listino cambia

Quando una versione listino viene aggiornata, il sistema individua le righe commessa
potenzialmente stantie:

```
righe con listino_versione_id = versione aggiornata
AND data_competenza >= data_validita_nuova versione
AND prezzo_bloccato = FALSE
AND non ancora fatturate
→ segnalate come "da verificare"
```

**Non ricalcolo automatico silenzioso** — le righe vengono segnalate.
Il ricalcolo definitivo avviene nello **step 1 della pipeline fatturazione**
con `dry_run` disponibile:

```
dry_run pipeline fatturazione →
  - righe con listino aggiornato (prezzo cambierebbe da X a Y)
  - righe con prezzo bloccato (invariate)
  - totale fattura attuale vs totale con prezzi aggiornati
  - anomalie bloccanti
→ operatore decide: conferma o aggiusta → poi esecuzione reale
```

**Per piccole realtà**: conferma manuale sempre.
**Per utility su grandi volumi**: ricalcolo automatico con log audit.
Configurabile per commessa/policy.

### 7.4 Override prezzo documento e riallineamento

Regole:

1. se il documento applica override manuale:
   - `prezzo_snapshot = prezzo_documento`,
   - `prezzo_bloccato = TRUE`,
   - `listino_versione_id` valorizzato alla versione risolta alla data (se disponibile) per audit comparativo.
2. se il preventivo e` ancora `LIBERO` e il prezzo cambia dopo push:
   - non si introduce nuovo stato business commessa,
   - si imposta `commesse_attivita.prezzo_da_riallineare = TRUE`,
   - riallineamento solo su conferma esplicita.
3. se il documento non e` piu` `LIBERO` (es. convertito/confermato), la modifica prezzo non altera la commessa consolidata.

---

## 8) Pull commessa → attività fatturabili

### 8.1 Posizione nel flusso

Il pull è lo **step 0** della pipeline fatturazione. È anche eseguibile standalone.

```
esecuzione standalone:   pull → review anomalie → stop
                                                        ↓
esecuzione pipeline:    pull → step 1 verifica prezzi → step 2 genera fatture → ...
```

### 8.2 Caratteristiche

- Eseguibile a piacimento — nessun vincolo di timing rispetto alla commessa.
- Idempotente — rieseguibile, non produce duplicazioni grazie a `segment_key`.
- Segnala anomalie strutturali (righe mancanti, gap, duplicati potenziali).
- Supporta `dry_run` (vedi §7.3).

### 8.3 Cosa fa

Per ogni commessa PRONTA_FATTURAZIONE nel perimetro del lotto:
1. Legge le righe dalla commessa (già validate al momento dell'assegnazione sorgente).
2. Applica `segment_key` per idempotenza.
3. Verifica listino (segnala righe stantie).
4. Scrive in `attivita_fatturabili` con `commessa_id` e `commessa_attivita_id` sempre valorizzati.
5. Segna righe commessa come `emesse`.

---

## 9) Modello DB — tabelle necessarie

Da consegnare al team DB. Qui le definizioni principali, i dettagli tecnici (tipi, indici,
FK esatte) sono delegati al team.

### 9.1 Tabelle nuove

**`vendite.commesse`**
```
id                      PK
tipo_commessa           REALE | AUTO
stato_commessa          BOZZA | APERTA | IN_ESECUZIONE |
                        PRONTA_FATTURAZIONE | CHIUSA | ANNULLATA
policy_fatturazione     DA_DOCUMENTO | DA_CONSUNTIVO | MISTA
fatturazione_immediata  boolean
priorita_operativa      ALTA | NORMALE | BASSA
utility_id              FK
billing_account_id      FK
emittente_soggetto_ruolo_id  FK
competenza_dal          date
competenza_al           date
meta                    jsonb
created_at / updated_at
```

**`vendite.commesse_sorgenti`** (bridge sorgente root)
```
id                  PK
commessa_id         FK → commesse
sorgente_tipo_id    FK → config.sorgenti
sorgente_uid        identificativo documento sorgente
sorgente_riga       riga specifica (opzionale)
ruolo_link          ROOT (unico valore in questa fase)
created_at
```

Vincoli:
- `UNIQUE (commessa_id, ruolo_link)` dove `ruolo_link = 'ROOT'` → una sola root per commessa.
- `UNIQUE (sorgente_tipo_id, sorgente_uid, ruolo_link)` → stessa sorgente non duplicabile.

**`vendite.commesse_attivita`** (righe operative/fatturabili della commessa)
```
id                      PK
commessa_id             FK → commesse
tipo_attivita           TASK | ORE | MILESTONE | CONSUMO | TECNICA
descrizione
quantita
listino_versione_id     FK → listini_versioni
prezzo_snapshot         numeric — prezzo al momento del push
prezzo_bloccato         boolean
prezzo_da_riallineare   boolean — flag tecnico di riallineamento post-push
pricing_mode            FIXED | FORMULA | SCAGLIONI
data_competenza         date
segment_key             varchar — chiave idempotenza (vedi §9.3)
sorgente_tipo_id        FK → config.sorgenti (nullable — valorizzato solo per import da sistemi esterni)
sorgente_uid            varchar (nullable — valorizzato solo per import da sistemi esterni)
stato_approvazione      BOZZA | APPROVATA | RIFIUTATA
stato_emissione         NON_EMESSA | EMESSA | ANNULLATA
meta                    jsonb
created_at / updated_at
```

**`vendite.commesse_attivita_log`** (audit — consigliato)
```
id
commessa_attivita_id    FK
evento                  varchar
dettaglio               jsonb
created_at
```

### 9.2 Estensioni a tabelle esistenti

**`vendite.attivita_fatturabili`** — aggiungere:
```
commessa_id             FK → commesse   (NOT NULL dopo backfill)
commessa_attivita_id    FK → commesse_attivita   (NOT NULL dopo backfill)
```

Nota ownership:

1. `attivita_fatturabili.prezzo_bloccato` e` requisito del dominio pricing/listini;
2. viene introdotto nella roadmap `gestione-listini.md` (DB-L3), non in DB-1 core commesse.

I campi `sorgente_tipo_id / sorgente_uid / sorgente_riga` restano su AF come contratto
idempotenza del pull e vengono valorizzati come `COMMESSA + segment_key`.
La sorgente esterna originale resta su `commesse_attivita.sorgente_*`.

**`vendite.preventivi`** (o tabella equivalente) — aggiungere:
```
stato_commessa          LIBERO | CONVERTITO | ESCLUSO   (default LIBERO)
```

### 9.3 Definizione segment_key

La `segment_key` identifica il segmento economico-fiscale atomico emettibile.
Deve essere:

1. **Deterministica** rispetto a:
   - `commessa_attivita_id`
   - periodo/competenza (`competenza_dal` / `competenza_al` o mese)
   - tipo quota (`BASE` / `SAL` / `CONGUAGLIO`)
   - progressivo di split tecnico se presente
2. **Stabile su rerun** — stesso evento, stessa `segment_key`, sempre.
3. **Obbligatoria** su tutte le righe emesse da commessa.

Formato suggerito (da validare col team DB):
```
{commessa_attivita_id}_{YYYY-MM}_{tipo_quota}[_{split_n}]
esempio: 42_2026-02_BASE
esempio: 42_2026-02_SAL_1
```

### 9.4 Vincoli di unicità (da implementare in DB-2)

Unicità operativa primaria:
```sql
UNIQUE (commessa_id, segment_key)
```

Unicità di sicurezza su root source:
```sql
UNIQUE (sorgente_tipo_id, sorgente_uid, ruolo_link)
```

Regola anti-doppio canale: impossibile avere due record attivi con stesso `segment_key`
e stessa root source su commesse diverse (salvo split esplicito con `segment_key` diversa).

Da rimuovere in DB-2:
```
uq_attivita_fatturabili_v_sorgente_fk (sorgente_tipo_id, sorgente_uid)
```
Troppo restrittivo — impedisce la parzializzazione controllata della stessa sorgente.

---

## 10) Funzioni DB necessarie

Funzioni dominio commessa (core DB-3) + riferimenti a funzioni pricing. Definizioni principali, dettagli tecnici al team DB.

| Funzione | Scopo |
|---|---|
| `fn_get_or_create_commessa(...)` | Risolve o crea commessa per la sorgente in ingresso |
| `fn_link_commessa_sorgente(...)` | Collega la sorgente ROOT alla commessa |
| `fn_upsert_commessa_attivita(...)` | Inserisce/aggiorna riga operativa con idempotenza su `segment_key` |
| `fn_emit_attivita_fatturabili_da_commessa(...)` | Pull commessa → `attivita_fatturabili` (step 0 pipeline) |
| `fn_resolve_commessa_prezzi(lotto_id)` | Individua righe con listino stantio nel perimetro lotto (ownership: roadmap pricing `gestione-listini.md`, step DB-L2) |
| `fn_get_commessa_stato(commessa_id)` | Stato + info commessa in un round-trip |

Note per `fn_emit_attivita_fatturabili_da_commessa`:
- Legge sempre la ROOT da `commesse_sorgenti`.
- Se ROOT mancante → errore bloccante.
- Scrive `commessa_id` e `commessa_attivita_id` su ogni riga emessa.
- Propaga `prezzo_bloccato` da `commesse_attivita` a `attivita_fatturabili`.
- I campi `sorgente_*` in `attivita_fatturabili` riflettono la sorgente commessa:
  `sorgente_tipo_id = 'COMMESSA'`, `sorgente_uid = commesse_attivita.segment_key`.
  Il `segment_key` è deterministico → il pull è idempotente senza query preventiva.
  Se la `commesse_attivita` ha propria sorgente esterna, viene tracciata su `commesse_attivita.sorgente_*`
  (vedi §21), non su AF.
- Idempotente su `segment_key`.

Nota ownership funzioni pricing:

1. `fn_resolve_prezzo_listino(...)` e `fn_resolve_commessa_prezzi(lotto_id)` sono governate dalla roadmap pricing in `gestione-listini.md`.

---

## 11) Guardrail anti-bypass (DB-3)

Il team DB deve implementare un meccanismo che impedisca inserimenti diretti in
`attivita_fatturabili` senza `commessa_id`:

- Trigger o check constraint su `attivita_fatturabili`.
- Blocco attivabile per flag (per gestire la fase di transizione).
- Attivazione piena dopo completamento del backfill storico.

---

## 12) Migrazione e backfill

### Fase A — Fondazione (DB-0 + DB-1)

1. Inventario oggetti legacy su `attivita_fatturabili` (vincoli, funzioni, trigger).
2. Creare le tabelle commesse core.
3. Aggiungere `commessa_id` e `commessa_attivita_id` su `attivita_fatturabili` (nullable).
4. **Backfill storico** — per ogni record esistente senza commessa:
   - Creare commessa AUTO.
   - Creare `commessa_attivita` tecnica 1:1.
   - Valorizzare `commessa_id`, `commessa_attivita_id`, `segment_key`.
5. Dopo backfill completo: attivare `NOT NULL` e unique nuove.

### Fase B — Percorso unico (DB-3 + DB-4)

1. Commessa AUTO come default per tutte le sorgenti attive.
2. Flag `stato_commessa` su preventivi.
3. Guardrail anti-bypass attivo.
4. Seed policy per tipo sorgente (nessuna logica hardcoded nel backend).

### Fase C — Gate fatturazione (post Fase B)

1. Gate operativo attivo per commesse REALE.
2. Nessuna emissione fatturabile senza prerequisiti operativi.

### Fase D — Estensione ticket (futuro)

1. Aggiungere TICKET in `config.sorgenti` / policy.
2. Il ticket non è sorgente diretta di commessa — passa da preventivo o ordine.
3. Nessuna modifica al modello core.

---

## 13) Bloccanti da chiudere prima di DB-1

Da validare col team DB prima di partire con lo schema:

1. Formato `segment_key` approvato (vedi §9.3).
2. Formato `stato_commessa` su preventivi approvato (vedi §6.2).
3. Conferma: una commessa = una sola ROOT.
4. Conferma: unique da rimuovere (`uq_attivita_fatturabili_v_sorgente_fk`).
5. Piano backfill storico validato (stima volume record da backfillare).
6. Conferma: guardrail anti-bypass come trigger o check constraint.

---

## 14) Roadmap DB

| Step | Contenuto |
|---|---|
| DB-0 | Inventario baseline — oggetti legacy, dipendenze, unique da rimuovere |
| DB-1 | Schema commessa core (tabelle, FK, nullable per transizione) |
| DB-2 | Unicità e idempotenza (rimozione unique legacy, nuove unique commessa-centriche) |
| DB-3 | Funzioni core + guardrail anti-bypass |
| DB-4 | Seed policy e configurazione operativa |
| DB-5 | pgTAP DDL, funzioni, anti-bypass, unicità, backfill |

Gate di uscita DB (il backend parte solo dopo):
- Schema commessa completo e vincoli attivi.
- Unique legacy rimosse.
- Nuove unique attive e validate.
- Funzioni core operative e testate.
- pgTAP verde.

---

## 15) Cosa NON cambia

- **Pipeline di fatturazione** (lotti, documenti fiscali, SDI) — invariata.
- **Campi `sorgente_*` su `attivita_fatturabili`** — restano con semantica idempotenza pull (`COMMESSA + segment_key`).
- **Logica `Idempotency-Key` sulle API** — invariata.
- **Branch policy BRANCH/GLOBAL** — invariata.

---

## 16) Nota futura — Utilities su commessa AUTO (senza bypass)

Decisione di indirizzo (da implementare in fase successiva, non ora):

1. per fatturazioni extra ad alto volume (energia/gas/idrico) non si introduce bypass diretto a `attivita_fatturabili`;
2. si usa il percorso standard tramite `commessa AUTO`, come per i preventivi con `fatturazione_immediata`;
3. in `AUTO` il codice commessa business puo` essere nullo (se previsto dal modello DB), mantenendo comunque `commessa_id` e `commessa_attivita_id` valorizzati sulle righe emesse;
4. i campi `sorgente_*` su AF restano valorizzati per idempotenza, con convenzione
   `COMMESSA + segment_key`; la provenienza originaria vive su `commesse_attivita.sorgente_*`.

Scopo della nota:

1. preservare il modello v2 come riferimento unico;
2. evitare future deviazioni architetturali quando si aprira` il cantiere utilities.

---

## 17) Analisi integrativa tabelle `commesse_*` e refactor `attivita_fatturabili`

### 17.1 Obiettivo

Definire in modo esplicito:

1. struttura target delle tabelle `commesse_*`,
2. ownership dei campi oggi presenti su `attivita_fatturabili`,
3. percorso di refactor progressivo senza rotture runtime.

### 17.2 Struttura target (v1 operativa)

**`vendite.commesse`** (testata)
```
id
codice
tipo_commessa                 REALE | AUTO
stato_commessa                BOZZA | APERTA | IN_ESECUZIONE | PRONTA_FATTURAZIONE | CHIUSA | ANNULLATA
billing_account_id
utility_id
emittente_soggetto_ruolo_id
competenza_dal
competenza_al
meta
data_insert / user_insert / data_update / user_update / tx_id
```

**`vendite.commesse_sorgenti`** (root source commessa)
```
id
commessa_id
sorgente_tipo_id
sorgente_uid
sorgente_riga
is_root                       boolean (una sola root attiva)
meta
data_insert / user_insert / data_update / user_update / tx_id
```

**`vendite.commesse_attivita`** (righe operative)
```
id
commessa_id
segment_key
articolo_id
istanza_utility_id          FK → anagrafiche.istanze_utilities (sempre valorizzata)
uom_id
quantita
competenza_dal
competenza_al
competenza_mese               mese fatturazione (YYYY-MM-01)
posticipa_al
tipo_doc_fiscale_id
valuta_id
listino_versione_id
prezzo_snapshot               numeric(22,10)
prezzo_bloccato               boolean
pricing_mode                  FIXED (v1), FORMULA/SCAGLIONI (v2)
prezzo_da_riallineare         boolean
stato_approvazione
stato_emissione
sorgente_tipo_id              FK → config.sorgenti (nullable — solo import da sistemi esterni)
sorgente_uid                  varchar (nullable — solo import da sistemi esterni)
meta
data_insert / user_insert / data_update / user_update / tx_id
```

**`vendite.commesse_attivita_log`** (audit eventi)
```
id
commessa_attivita_id
evento
dettaglio jsonb
data_insert / user_insert
```

### 17.3 Mapping campi: owner vs snapshot

| Campo dominio | Owner target | Su `attivita_fatturabili` |
|---|---|---|
| `competenza_dal`, `competenza_al` | `commesse_attivita` | snapshot copiato |
| `competenza_mese` (mese fatturazione) | `commesse_attivita` | snapshot copiato (obbligatorio) |
| `posticipa_al` | `commesse_attivita` | snapshot copiato |
| `tipo_doc_fiscale_id`, `valuta_id` | `commesse_attivita` | snapshot copiato |
| `uom_id`, `quantita` | `commesse_attivita` | snapshot copiato |
| `prezzo_snapshot`/`prezzo_unitario` | `commesse_attivita` | snapshot copiato su `prezzo_unitario` |
| `prezzo_bloccato` | `commesse_attivita` | snapshot operativo (gia` presente) |
| `listino_versione_id` | `commesse_attivita` | non obbligatorio in AF v1, consigliato in v2 |
| `sorgente_*` root | `commesse_attivita` + `commesse_sorgenti` | su AF valorizzati come `COMMESSA + segment_key` |

Regola di governo:

1. calcolo e decisione business in `commesse_attivita`;
2. `attivita_fatturabili` resta layer esecutivo per pipeline/fatturazione.

### 17.4 Fatturazione immediata e competenza

Per commesse `AUTO` (incluso caso "immediata/giornaliera"):

1. `competenza_mese` resta sempre valorizzata (mese della data conferma/esecuzione);
2. il lotto giornaliero governa il run operativo, non sostituisce la semantica della competenza;
3. `posticipa_al` resta il gate di differimento anche su percorso AUTO.

### 17.5 Refactor `attivita_fatturabili` (progressivo)

Fase R1:

1. aggiungere FK `commessa_id`, `commessa_attivita_id` (nullable in transizione),
2. propagare sempre i campi snapshot da commessa in `fn_emit_attivita_fatturabili_da_commessa`.

Fase R2:

1. attivare guardrail anti-bypass (no insert diretto senza commessa),
2. backfill completo storico e successivo `NOT NULL` su FK commessa.

Fase R3:

1. eliminare logica duplicata di calcolo prezzi/competenza su `attivita_fatturabili`,
2. mantenere in AF solo snapshot e filtri runtime.

Fase R4 (cleanup schema, opzionale):

1. valutare deprecazione colonne ridondanti su AF solo dopo stabilizzazione,
2. eventuali drop colonne in changeset dedicati e reversibili.

### 17.6 Decisione operativa

Il modello v2 resta confermato:

1. nessun bypass `sorgente -> attivita_fatturabili`,
2. percorso unico `sorgente -> commessa -> attivita_fatturabili`,
3. `sorgente_*` su AF mantenuti come contratto idempotenza (`COMMESSA + segment_key`).

---

## 18) Checklist tecnica DB-L3 (esecutiva)

### 18.1 Schema `commesse_*`

- [x] creare `vendite.commesse` con stati, tipo (`REALE/AUTO`), contesto BA/utility/emittente, audit
- [x] creare `vendite.commesse_sorgenti` con vincolo una sola root attiva per commessa
- [x] creare `vendite.commesse_attivita` con:
  - [x] `segment_key`
  - [x] `istanza_utility_id` (NOT NULL, anche fittizia)
  - [x] `competenza_dal`, `competenza_al`, `competenza_mese`
  - [x] `posticipa_al`
  - [x] `tipo_doc_fiscale_id`, `valuta_id`
  - [x] `listino_versione_id`, `prezzo_snapshot numeric(22,10)`, `prezzo_bloccato`
  - [x] `pricing_mode`, `prezzo_da_riallineare`
  - [x] `sorgente_tipo_id` nullable, `sorgente_uid` nullable (per import da sistemi esterni)
  - [x] unique parziale `(sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL`
- [x] creare `vendite.commesse_attivita_log`

### 18.2 Estensioni `attivita_fatturabili`

- [x] aggiungere `commessa_id` (finalizzato `NOT NULL`)
- [x] aggiungere `commessa_attivita_id` (finalizzato `NOT NULL`)
- [x] aggiungere `prezzo_bloccato` (completato: `20260224-04`)
- [ ] valutare introduzione `segment_key` su AF (snapshot tecnico) se richiesta idempotenza runtime

### 18.3 Vincoli e indici

- [x] FK `attivita_fatturabili.commessa_id -> commesse.id`
- [x] FK `attivita_fatturabili.commessa_attivita_id -> commesse_attivita.id`
- [x] unique operativa su `commesse_attivita (commessa_id, segment_key)` (o equivalente approvato)
- [x] vincolo `competenza_mese` primo giorno mese su `commesse_attivita`
- [x] strategia per rimozione/sostituzione `uq_attivita_fatturabili_v_sorgente_fk`
- [x] unique parziale su `commesse_attivita (sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL`

### 18.4 Funzioni DB (core commessa)

- [x] `fn_get_or_create_commessa(...)`
- [x] `fn_link_commessa_sorgente(...)`
- [x] `fn_upsert_commessa_attivita(...)`
- [x] `fn_emit_attivita_fatturabili_da_commessa(...)`
  - [x] propaga `commessa_id`, `commessa_attivita_id`
  - [x] propaga `prezzo_bloccato`
  - [x] copia `competenza_mese` da commessa (no ricalcolo in AF)
  - [x] copia `posticipa_al` e altri snapshot dominio
- [x] `fn_get_commessa_stato(commessa_id)`

### 18.5 Backfill e guardrail

- [x] backfill storico AF -> commesse AUTO (1:1 tecnico) *(N/A ambiente v0 senza dati storici)*
- [x] popolamento `commessa_id`, `commessa_attivita_id` su storico *(N/A ambiente v0 senza dati storici)*
- [x] implementazione guardrail anti-bypass su insert/update AF senza commessa (toggle via `config.parameters`)
- [x] passaggio finale FK a `NOT NULL` dopo backfill validato

### 18.6 Test pgTAP minimi

- [x] DDL `commesse_*` (vincoli/FK/unique/check)
- [x] funzioni core create ed eseguibili
- [x] `fn_emit_attivita_fatturabili_da_commessa` idempotente
- [x] propagazione snapshot (`competenza_mese`, `posticipa_al`, `prezzo_bloccato`)
- [x] guardrail anti-bypass attivo (switch parametro a `true` in go-live transizione, changeset `20260224-41`)
- [x] regressione su pipeline esistente non rotta (verifica con `test-attivita-guardrail-commessa-v1.sql`)
  - Evidenza prevista: `db/pgtap/vendite/test-attivita-guardrail-commessa-v1.sql`
    (caso guard ON + emit commessa operativo).

### 18.8 Orchestratore push commessa (vedi §23)

- [x] Creare `vendite.commesse_push_log` (schema §23.4)
- [x] Indice su `commesse_push_log.run_at`
- [x] Documentare uso di `pg_try_advisory_lock` come anti-concorrenza (nessuna tabella lock)

### 18.9 Gate uscita DB-L3

- [x] test pgTAP DB-L3 verdi
- [x] WIP `gestione-listini.md` e `gestione-commesse-v2.md` allineati
- [x] checklist 13.3 (`gestione-listini.md`) portata a completamento coerente

### 18.10 Stato transizione pipeline (COMMESSA_ONLY)

- [x] decisione architetturale: pipeline legacy `attivita-da-fatturare` deprecata
- [x] applicare switch operativo `20260224-41-switch-attivita-to-commessa-only-mctit.yaml`
- [x] validare switch con `db/pgtap/vendite/test-attivita-commessa-only-switch-v1.sql`

### 18.11 Readiness backfill (analisi volumi pre-NOT-NULL)

Obiettivo: misurare il perimetro reale del backfill prima di forzare
`attivita_fatturabili.commessa_id/commessa_attivita_id` a `NOT NULL`.

Query operative (solo analisi):

```sql
-- 1) Volume totale AF e quota senza link commessa
SELECT
  count(*) AS total_af,
  count(*) FILTER (WHERE commessa_id IS NULL OR commessa_attivita_id IS NULL) AS af_missing_commessa_link
FROM vendite.attivita_fatturabili;

-- 2) Distribuzione missing per sorgente (diagnostica priorita backfill)
SELECT
  COALESCE(s.codice, 'N/D') AS sorgente_codice,
  count(*) AS righe_missing
FROM vendite.attivita_fatturabili af
LEFT JOIN config.sorgenti s
  ON s.id = af.sorgente_tipo_id
WHERE af.commessa_id IS NULL
   OR af.commessa_attivita_id IS NULL
GROUP BY COALESCE(s.codice, 'N/D')
ORDER BY righe_missing DESC, sorgente_codice;

-- 3) Controllo coerenza link presenti (FK logica commessa_attivita -> commessa)
SELECT
  count(*) AS incoerenti
FROM vendite.attivita_fatturabili af
JOIN vendite.commesse_attivita ca
  ON ca.id = af.commessa_attivita_id
WHERE af.commessa_id IS NOT NULL
  AND ca.commessa_id <> af.commessa_id;
```

Criterio go/no-go per fase `NOT NULL`:
- `af_missing_commessa_link = 0`
- `incoerenti = 0`

---

## 19) Analisi struttura `commesse_attivita` vs `attivita_fatturabili` — gap e rischi

### 19.1 Obiettivo

Verificare se la struttura `commesse_attivita` proposta in §17.2 copre tutti i campi
business di `attivita_fatturabili` necessari prima del refactor/deprecazione della
pipeline attività.

Riferimento schema AF reale: `docs/it/dbzero/vendite/manual/attivita_fatturabili.md`

---

### 19.2 Campi mancanti in `commesse_attivita` (gap da colmare)

Confronto tra schema AF reale e schema `commesse_attivita` proposto in §17.2.

**Gap 1 — `data_attivita`**

Presente in AF, assente in `commesse_attivita`.
Rappresenta la data in cui l'attività è avvenuta (es. lettura consumo, esecuzione
prestazione). Importante per traceability e per utility billing.

Decisione da prendere:

- Aggiungere `data_attivita` a `commesse_attivita` (consigliato), oppure
- Lasciarlo solo in AF come dato di dettaglio (accettabile se non serve a monte).

### Gap 2 — `istanza_utility_id`

Presente in AF come FK a `anagrafiche.istanze_utilities` (il punto tecnico specifico
— contatore, POD, PDR). Su `commesse` esiste `utility_id` che è il tipo di
utility/fornitore — NON la stessa cosa.

Decisione chiusa:

1. `istanza_utility_id` vive su `commesse_attivita`;
2. nel dominio attuale e` **sempre valorizzata** (anche con istanza fittizia);
3. `commesse` puo` mantenerla come snapshot/testata opzionale solo se utile per query aggregate.

Motivazione:

1. `anagrafiche.billing_account.istanza_utility_id` e` `NOT NULL`;
2. `attivita_fatturabili.istanza_utility_id` e` `NOT NULL`;
3. la presenza di istanza fittizia standardizza il modello anche fuori da gas/energia legate a PDP.

### Gap 3 — campi misura operativa

Presenti in AF, assenti in `commesse_attivita`:

- `qta_operativa` — quantità nella UoM operativa (es. mc gas, kWh)
- `uom_operativa_id` — UoM operativa
- `factor_to_base` — fattore di conversione verso UoM base

Sono essenziali per utility billing (la quantità fatturata in kWh ≠ quantità
in UoM base). Da aggiungere a `commesse_attivita` o portare come snapshot in AF.

### Gap 4 — `area_geografica_id`

Presente in AF come dimensione di billing opzionale. Non menzionato in
`commesse_attivita` né in `commesse`. Da decidere se va sulla testata commessa
o sulla riga attività.

### Mapping `stato_approvazione` → `approvato`

AF usa `approvato boolean`. `commesse_attivita` usa `stato_approvazione` enum.
La funzione pull deve mappare:

- `stato_approvazione = APPROVATA` → `approvato = TRUE` in AF
- `stato_approvazione = BOZZA / RIFIUTATA` → non emettibile (pull bloccato)

---

### 19.3 Inconsistenza stati commessa tra §4 e §17.2

§4.1 (AUTO lifecycle): `BOZZA → PRONTA_FATTURAZIONE → CHIUSA`
§4.2 (REALE lifecycle): `BOZZA → APERTA → IN_ESECUZIONE → PRONTA_FATTURAZIONE → CHIUSA`

Set canonico approvato per `commesse.stato_commessa`:

`BOZZA | APERTA | IN_ESECUZIONE | PRONTA_FATTURAZIONE | CHIUSA | ANNULLATA`

Nota:

- `COMPLETATA` e` sostituito da `CHIUSA`.
- `BLOCCATA` non e` stato business; eventuale blocco e` gestito via eventi/log/meta.

---

### 19.4 Rischi trigger su `attivita_fatturabili`

Con il pull da commessa, AF riceve campi già valorizzati da `commesse_attivita`.
I trigger esistenti su AF potrebbero interferire.

**Trigger a rischio:**

`trg_attivita_fatturabili_normalize_ins_upd`

- Normalizza `competenza_mese` al 1° del mese (deriva da `posticipa_al` se assente)
- Risolve `tipo_doc_fiscale_id`/`valuta_id` quando mancanti
- Con pull da commessa, questi campi arrivano già valorizzati come snapshot

Rischio: il trigger sovrascrive i valori snapshot provenienti dalla commessa.

Mitigazione: rendere il trigger "commessa-aware" — se `commessa_attivita_id IS NOT NULL`,
saltare la normalizzazione e la risoluzione (i valori vengono dalla commessa e sono
già corretti).

`trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd`

- Valida coerenza BA/istanza/articolo
- Con commessa, BA e utility vengono dalla testata commessa via FK

Rischio: le regole di coerenza potrebbero non essere aggiornate per leggere
i valori dal join commessa invece che dai campi diretti su AF.

---

### 19.5 Campi AF che diventano obsoleti con il modello commessa

| Campo AF | Stato post-commessa | Note |
|---|---|---|
| `lotto_attivita_id` | Nullable → deprecato in R4 | Il link al lotto attività non serve più |
| `approvato` | Ridondante con `commesse_attivita.stato_approvazione` | Snapshot derivato al pull, mantenuto per compatibilità filtri pipeline fatturazione |
| `billing_account_id` su AF | Snapshot ridondante da `commesse.billing_account_id` | Mantenuto per performance indici esistenti |
| `istanza_utility_id` su AF | Resta se aggiunto a `commesse_attivita`, snapshot | Ownership da chiarire (vedi §19.2 Gap 2) |

---

### 19.6 Schema `commesse_attivita` corretto (integrazione gap)

Rispetto a §17.2, aggiungere:

```text
data_attivita               date — data evento/attività (consigliato)
istanza_utility_id          FK → anagrafiche.istanze_utilities (per utilities)
qta_operativa               numeric — quantità in UoM operativa
uom_operativa_id            FK → catalogo.uom (UoM operativa)
factor_to_base              numeric — fattore conversione UoM operativa → base
area_geografica_id          FK → config.aree_geografiche (opzionale)
```

Nota aggiornata:

1. `istanza_utility_id` e` da considerare sempre valorizzata anche per casi non-PDP
   tramite istanza fittizia;
2. i campi misura operativa restano opzionali e si valorizzano nei branch utility.

---

### 19.7 Checklist integrativa (da aggiungere a §18)

- [x] Ownership `istanza_utility_id`: su `commesse_attivita` (sempre valorizzata, anche con istanza fittizia)
- [ ] Aggiungere `data_attivita` a `commesse_attivita` (o documentare esclusione)
- [ ] Aggiungere campi misura operativa a `commesse_attivita` (o documentare esclusione)
- [x] Allineare stati `commesse.stato_commessa` con set canonico (`BOZZA|APERTA|IN_ESECUZIONE|PRONTA_FATTURAZIONE|CHIUSA|ANNULLATA`)
- [ ] Aggiornare trigger `trg_attivita_fatturabili_normalize_ins_upd` per essere commessa-aware
- [ ] Aggiornare trigger `trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd` per leggere BA da commessa
- [ ] Documentare mapping esplicito `stato_approvazione → approvato` nel pull

---

## 20) Piano deprecazione pipeline attività fatturabili

### 20.1 Stato attuale della pipeline

La pipeline attività (`AttivitaPipelineRunner`, `AttivitaPipelineStepExecutor`,
`AttivitaPipelineRepository`) è strutturalmente completa ma **tutti i task di
acquisizione sono placeholder non implementati** (`pass`):

```python
_handle_acquisisci_preventivi()     → pass
_handle_acquisisci_ordini()         → pass
_handle_acquisisci_contratti()      → pass
_handle_acquisisci_attivita_consumi() → pass
_handle_normalizza_attivita()       → pass
_handle_valida_attivita()           → pass
_handle_deduplica_attivita()        → pass
```

Non c'è logica business da salvare nei task — sono gusci vuoti.

### 20.2 Cosa rimane utile (da NON eliminare)

| Componente | File | Perché resta |
|---|---|---|
| Lotto management (`get_or_create_lotto_attivita`, `set_lotto_attivita_stato`, ecc.) | `attivita_pipeline_repository.py` | Serve per il tracing del pull (step 0 pipeline fatturazione) |
| Task run tracing (`start/complete/fail_attivita_task_run`, `get_attivita_branch_summary`) | `attivita_pipeline_repository.py` | Serve per monitoring step 0 |
| `_decode_jsonb` / `_to_jsonb_param` | `attivita_pipeline_repository.py` | Già estratti in §11 refactor |
| Error logger pattern | `attivita_pipeline_error_logger.py` | Pattern riusato su step 0 e commessa |

### 20.3 Cosa NON serve più (candidato eliminazione)

| Componente | File | Motivo |
|---|---|---|
| `AttivitaPipelineRunner` | `attivita_pipeline_runner.py` | Il pull da commessa è una funzione semplice, non un runner multi-branch |
| `AttivitaPipelineStepExecutor` | `attivita_pipeline_step_executor.py` | I 7 handler sono stub — nessuna logica da preservare |
| Tutti i `_handle_acquisisci_*` | `attivita_pipeline_step_executor.py` | Placeholder — mai implementati |
| Endpoint API `run` pipeline attività | `api/views.py` | Sostituito da step 0 pipeline fatturazione |
| Endpoint API `status` pipeline attività | `api/views.py` | Sostituito da stato commessa |

### 20.4 Cosa diventa lo step 0

Il pull commessa → attività fatturabili non richiede la complessità di un runner/executor.
Diventa una chiamata diretta alla funzione DB:

```python
# step 0 della pipeline fatturazione — non è una pipeline separata
def pull_commessa_step(lotto_id: int, dry_run: bool = False) -> dict:
    return repo.fn_emit_attivita_fatturabili_da_commessa(lotto_id, dry_run)
```

L'orchestrazione è già nel runner della pipeline fatturazione esistente.

### 20.5 Timing deprecazione

**Ora — nessuna modifica**: la pipeline attività non causa danni, il DB commesse
non esiste ancora. Congela lo sviluppo su questi file (nessun nuovo handler).

Dopo DB-L3 (schema commessa attivo):

- Marca i file come `# DEPRECATED — sostituiti da modello commessa`
- Disabilita gli endpoint API attività pipeline (o flag `deprecated` nella doc)

Dopo DB-L5 (suite pgTAP verde):

- Elimina `attivita_pipeline_runner.py`
- Elimina `attivita_pipeline_step_executor.py`
- Elimina `attivita_pipeline_error_logger.py`
- Riduce `attivita_pipeline_repository.py` ai soli metodi ancora usati (lotto + task run)
- Rimuove i 2 endpoint API pipeline attività (run + status)
- Mantiene endpoint task-runs (riusato per il monitoring dello step 0)

### 20.6 Endpoint API — impatto

| Endpoint | Stato post-commessa |
|---|---|
| `POST /attivita_fatturabili/pipeline/run/` | Eliminato — il run è step 0 del lotto fatturazione |
| `GET /attivita_fatturabili/pipeline/<id>/status/` | Eliminato — sostituito da status commessa |
| `GET /attivita_fatturabili/pipeline/<id>/task-runs/` | Mantenuto o reindirizzato — il tracing task run resta utile |

---

## 21) Catena sorgente a due livelli — decisione (24-02-2026)

### 21.1 Problema

Nel modello v2, `attivita_fatturabili` (AF) ha `sorgente_tipo_id`/`sorgente_uid` per garantire
idempotenza degli import. Con l'introduzione di `commesse_attivita` come livello intermedio,
la catena sorgente si allunga:

```text
[Sistema esterno] → commesse_attivita → attivita_fatturabili → fattura
```

La domanda è: chi garantisce l'idempotenza del passaggio sistema esterno → commesse_attivita?

### 21.2 Decisione

La coppia sorgente si duplica su due livelli con semantiche distinte:

**Livello 1 — `commesse_attivita.sorgente_tipo_id / sorgente_uid`**

- Nullable — valorizzato **solo** quando la riga arriva da un sistema esterno (import batch,
  API terze parti, letture utility automatiche).
- Per flussi manuali (preventivo → ordine → commessa) la FK al documento sorgente è sufficiente
  — non serve la coppia sorgente.
- Vincolo: unique parziale `(sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL`.
- Garantisce idempotenza del passaggio sistema esterno → `commesse_attivita`.

**Livello 2 — `attivita_fatturabili.sorgente_tipo_id / sorgente_uid`**

- Sempre valorizzato. Quando la sorgente è una commessa:
  - `sorgente_tipo_id = 'COMMESSA'`
  - `sorgente_uid = commesse_attivita.segment_key`
- Il `segment_key` è deterministico → il pull commessa → AF è idempotente by design
  senza query preventiva.
- La sorgente originale esterna (es. lettura utility) è tracciata su `commesse_attivita.sorgente_*`
  — non viene ri-propagata su AF.

### 21.3 Catena completa per flusso concreto

| Flusso | Sorgente su `commesse_attivita` | Sorgente su AF |
|---|---|---|
| Preventivo → ordine → commessa | Nessuna (FK al documento) | `COMMESSA` + `segment_key` |
| Import utility batch → commessa | `LETTURE` + uid lettura | `COMMESSA` + `segment_key` |
| API terza parte → commessa | `API_XYZ` + uid esterno | `COMMESSA` + `segment_key` |
| Consumo automatico → commessa AUTO | `CONSUMI` + uid consumo | `COMMESSA` + `segment_key` |

### 21.4 Perché non propagare la sorgente originale su AF

Due ragioni:

1. **`segment_key` è sufficiente** — identifica univocamente la riga in ogni contesto; la sorgente
   originale è rintracciabile via join `AF → commesse_attivita → sorgente_*`.
2. **Semplificazione vincoli** — il vincolo unique su AF (`sorgente_tipo_id, sorgente_uid`) rimane
   omogeneo: punta sempre a `COMMESSA + segment_key`, non a sorgenti eterogenee.
   Questo evita collisioni tra sorgenti di tipo diverso sullo stesso AF.

### 21.5 Impatto su §9 e §18

- **§9.1**: `commesse_attivita` aggiornato con `sorgente_tipo_id` e `sorgente_uid` nullable.
- **§17.2**: idem.
- **§18.1 / §18.3**: checklist aggiornata con unique parziale sorgente su `commesse_attivita`.
- **§15 "Cosa NON cambia"**: la semantica dei campi `sorgente_*` su AF resta — cambia solo il
  valore (`COMMESSA + segment_key` invece di sorgente diretta).

---

## 22) Decisioni definitive su `attivita_fatturabili` post-commessa (24-02-2026)

### 22.1 Campi che restano — layer esecutivo billing

Questi campi appartengono al **motore di fatturazione** e sono indipendenti dalla sorgente.
Non vengono mai spostati su `commesse_attivita`.

| Campo | Ruolo |
|---|---|
| `approvato`, `fatturato` | Flag di stato ciclo billing |
| `lock_in_fatturazione`, `lock_batch_id` | Isolamento corsa fatturazione |
| `fattura_riga_id` | Link al documento emesso |
| `sospesa`, `posticipa_al` | Gating — quando fatturare |
| `competenza_mese`, `competenza_dal/al` | Regola competenza — snapshot da commessa |
| `tipo_doc_fiscale_id`, `valuta_id` | Tipo documento — snapshot da commessa |
| `articolo_id` | Servizio fatturato — snapshot da commessa |
| `billing_account_id` | Intestazione — snapshot + indice performance |
| `prezzo_unitario`, `prezzo_bloccato` | Snapshot economico da `commesse_attivita` |
| `uom_id`, `quantita` | Quantità fatturata — snapshot da commessa |
| `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` | Idempotenza pull (`COMMESSA` + `segment_key`) |

### 22.2 Campi che diventano snapshot (copiati al pull)

Al momento del pull `fn_emit_attivita_fatturabili_da_commessa`, i campi seguenti vengono
copiati da `commesse_attivita` e non ricalcolati da AF:

| Campo su AF | Fonte snapshot |
|---|---|
| `prezzo_unitario` | `commesse_attivita.prezzo_snapshot` |
| `prezzo_bloccato` | `commesse_attivita.prezzo_bloccato` |
| `competenza_mese` | `commesse_attivita.competenza_mese` |
| `competenza_dal`, `competenza_al` | `commesse_attivita.competenza_dal/al` |
| `posticipa_al` | `commesse_attivita.posticipa_al` |
| `tipo_doc_fiscale_id`, `valuta_id` | `commesse_attivita.tipo_doc_fiscale_id/valuta_id` |
| `billing_account_id` | `commesse.billing_account_id` |
| `area_geografica_id` | `commesse_attivita.area_geografica_id` (se presente) |
| `istanza_utility_id` | `commesse_attivita.istanza_utility_id` (per utilities) |
| `qta_operativa`, `uom_operativa_id`, `factor_to_base` | `commesse_attivita.*` (per utilities) |

### 22.3 Campi da deprecare (lungo termine)

| Campo | Timing | Motivo |
| --- | --- | --- |
| `lotto_attivita_id` | R4 post-deprecazione pipeline | Link al vecchio batch attività. Con il pull come step 0, non serve più. Nullable ora → rimosso in R4. |
| `attivita_consumi_id` | R5 o dopo migrazione utilities | Link al modulo consumi standalone. Diventa orfano se utilities migrano a commesse. |

### 22.4 Trigger da modificare (non eliminare)

**`trg_attivita_fatturabili_normalize_ins_upd`**

Attuale comportamento: normalizza `competenza_mese`, risolve `tipo_doc_fiscale_id`/`valuta_id`
quando mancanti.

Rischio: con il pull da commessa questi campi arrivano già valorizzati come snapshot. Il trigger
potrebbe sovrascriverli con valori ricalcolati.

Mitigazione obbligatoria: rendere il trigger commessa-aware.

```sql
-- logica da aggiungere al trigger
IF NEW.commessa_attivita_id IS NOT NULL THEN
    -- valori snapshot già corretti — non ricalcolare
    RETURN NEW;
END IF;
-- logica normalizzazione esistente per righe non da commessa
```

**`trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd`**

Attuale comportamento: valida coerenza BA/istanza/articolo sui campi diretti di AF.

Rischio: le regole potrebbero rifiutare righe valide dove BA e utility vengono dalla commessa
via FK e non dai campi diretti di AF.

Mitigazione: aggiornare le regole di coerenza per leggere BA/utility dal join commessa
quando `commessa_id IS NOT NULL`.

### 22.5 Riepilogo scelte chiave

1. `attivita_fatturabili` **non perde quasi nulla strutturalmente** — diventa layer di esecuzione
   billing puro.
2. `commesse_attivita` è la nuova **sorgente di verità** per cosa e quanto fatturare.
3. AF gestisce solo **quando** (competenza, gating) e **come** (documento, lock, stato).
4. I campi `sorgente_*` su AF sono il contratto di idempotenza del pull:
   sempre `COMMESSA + segment_key`, mai la sorgente originale esterna.
5. La sorgente originale esterna vive su `commesse_attivita.sorgente_*` e si raggiunge via join.

---

## 23) Push commessa — orchestratore vs pipeline (24-02-2026)

### 23.1 Analisi

Il push commessa è il processo che prende le sorgenti (preventivi, ordini, consumi, future)
e le assegna a una commessa creando/aggiornando `commesse_attivita`.

La domanda è se questo processo richiede una **pipeline** (come quella inizialmente progettata
per attività fatturabili) o basta un **orchestratore**.

**Pattern a confronto:**

```text
Pipeline AF (deprecata):         step1 → step2 → step3 → ...   (catena sequenziale)

Orchestratore push commessa:     HandlerPreventivi ─┐
                                 HandlerOrdini     ─┼→ PushReport
                                 HandlerConsumi    ─┘   (fan-out indipendente)
```

La pipeline AF aveva step sequenziali con dipendenze:
`acquisisci → normalizza → valida → deduplica → scrivi`

Il push commessa NON ha step sequenziali cross-handler. I singoli handler:

- Sono **indipendenti tra loro** — `HandlerPreventivi` non dipende da `HandlerConsumi`.
- Internamente eseguono solo: `read → validate → fn_db() → commit`.
- La logica business (normalizza, valida, upsert idempotente) vive nelle **funzioni DB**,
  non nel runner Python.
- L'isolamento errori è semplice (`try/except` per handler) — non serve error scope
  BRANCH/GLOBAL come nella pipeline AF.

**Differenza strutturale determinante:**

| Aspetto | Pipeline AF | Orchestratore push |
| --- | --- | --- |
| Stato interno | Lotto + task run tracing | Nessuno (stateless) |
| Step sequenziali | Sì, con dipendenze | No — handler indipendenti |
| Idempotenza | Gestita dal runner | Garantita dal DB (`sorgente_uid` unique) |
| Concorrenza | Lock di lotto | `pg_try_advisory_lock` — nessuna tabella |
| Errore in un branch | Blocca o continua per scope | Un handler fallisce, gli altri girano |
| Estendibilità | Nuovo handler-code nel registry | Idem — identico pattern |

### 23.2 Motivazione della scelta: orchestratore

**1. Nessuna dipendenza sequenziale cross-handler.**
I tre handler (preventivi, ordini, consumi) possono girare in qualsiasi ordine o in parallelo.
Non c'è un output di HandlerA che serve come input di HandlerB.

**2. La logica business è nel DB, non nel runner.**
Le funzioni `fn_get_or_create_commessa`, `fn_upsert_commessa_attivita` gestiscono
normalizzazione, validazione e idempotenza. Il Python chiama e riceve il risultato.
Un runner multi-step non aggiungerebbe logica, solo overhead.

**3. Lo stato vive nelle tabelle commessa.**
"Cosa è già stato processato?" → risponde `commesse_sorgenti.sorgente_uid` con il vincolo
unique. L'orchestratore non ha bisogno di ricordarlo — è il DB che impedisce i doppioni.

**4. Estendibilità identica a una pipeline.**
Aggiungere `HandlerTicket` in futuro = registrare un handler nel registry.
Non serve toccare la struttura dell'orchestratore — esattamente come per una pipeline.

**5. Evita il debito tecnico della pipeline AF.**
La pipeline AF aveva complessità (lotto, branch, task run, error scope) che non è mai
stata implementata perché eccessiva per il problema reale. Non si ripete lo stesso errore.

### 23.3 Struttura orchestratore (Python)

```python
class CommessaPushOrchestrator:
    handlers: dict[str, BaseSourceHandler]  # registry estendibile per tipo sorgente

    def run(
        self,
        source_types: list[str] | None = None,  # None = tutti i tipi registrati
        dry_run: bool = False,
    ) -> PushReport:
        report = PushReport(dry_run=dry_run)
        for handler in self._resolve_handlers(source_types):
            try:
                result = handler.run(dry_run=dry_run)
                report.add_success(handler.source_type, result)
            except Exception as e:
                report.add_error(handler.source_type, e)
                # continua con gli altri handler — isolamento garantito
        return report
```

Caratteristiche:

- **Stateless**: nessun lotto, nessun task run, nessuna branch state machine.
- **Dry-run** integrato — ogni handler riceve il flag e non scrive.
- **Isolamento per handler** — un fallimento non blocca gli altri.
- **Registry estendibile** — nuova sorgente = nuovo handler registrato.
- **Concorrenza**: `pg_try_advisory_lock` a livello DB — nessuna tabella di lock applicativa.

### 23.4 Decisione DB — tabella da implementare

**Motivazione:**
L'orchestratore è stateless, ma per un processo schedulato business-critical serve
audit trail minimo. Le tabelle commessa rispondono a "cosa è stato creato" ma non a:

- "Il push schedulato delle 3:00 è andato a buon fine?"
- "HandlerConsumi ha avuto errori la notte scorsa?"
- "Qual era il `sorgente_uid` fallito nell'ultimo run?"

**Una sola tabella — `vendite.commesse_push_log`:**

```sql
vendite.commesse_push_log (
    id              bigserial PRIMARY KEY,
    run_at          timestamptz NOT NULL DEFAULT now(),
    dry_run         boolean NOT NULL DEFAULT false,
    source_types    text[],          -- handler eseguiti (NULL = tutti)
    risultato       jsonb,           -- dettaglio per handler (vedi sotto)
    stato           text NOT NULL,   -- COMPLETATO | PARZIALE | ERRORE
    durata_ms       int,
    user_run        text,            -- 'scheduler' | user applicativo
    data_insert     timestamptz DEFAULT now(),
    user_insert     text DEFAULT current_user
)
```

Esempio `risultato` jsonb:

```json
{
  "HandlerPreventivi": {"created": 12, "updated": 0, "skipped": 138, "errors": []},
  "HandlerOrdini":     {"created": 3,  "updated": 1, "skipped": 22,  "errors": []},
  "HandlerConsumi":    {"created": 45, "updated": 3, "skipped": 0,
                        "errors": ["uid_xyz: billing_account non trovato"]}
}
```

- `stato = PARZIALE` se almeno un handler ha completato ma almeno uno ha avuto errori.
- `stato = ERRORE` se tutti gli handler hanno fallito o errore critico pre-esecuzione.
- `stato = COMPLETATO` se tutti i handler hanno girato senza errori (dry_run o reale).

**Cosa NON va in questa tabella:**

- Dettaglio per singola riga sorgente (troppo granulare — non serve).
- Stato inter-run (ogni run è indipendente — append-only).
- Lock o flag `is_running` (gestito da `pg_try_advisory_lock`).

### 23.5 Checklist DB da aggiungere a §18

- [x] Creare `vendite.commesse_push_log` con schema §23.4
- [x] Indice su `run_at` per query audit (`WHERE run_at >= ...`)
- [x] `pg_try_advisory_lock` documentato come meccanismo anti-concorrenza (nessuna tabella)
- [x] Inserimento in `commesse_push_log` eseguito via funzione DB `vendite.fn_log_commessa_push_run(...)`;
      il layer Python la invoca al termine di ogni `CommessaPushOrchestrator.run()`

---

## 24) Uniformazione canali fatturabili per sorgente (contratti/preventivi/ordini/ddt)

### 24.1 Decisione modello

Per uniformita` cross-dominio, il controllo canali non usa `documento_tipo` hardcoded.
Usa invece il pattern standard gia` adottato nel progetto:

- `sorgente_tipo_id` (`config.sorgenti.id`)
- `sorgente_uid` (`text`)

Questa scelta e` allineata a:

- `vendite.commesse_sorgenti` (`sorgente_uid text`)
- `vendite.commesse_attivita` (`sorgente_uid text`)

e consente di estendere la logica a nuove sorgenti senza alterazioni strutturali.

### 24.2 Perche` `sorgente_uid text` (e non UUID obbligatorio)

Motivazioni:

1. Alcune sorgenti sono naturalmente non-UUID (chiavi esterne, codici tecnici, composite key serializzate).
2. Evita conversioni forzate `text -> uuid` e collisioni applicative inutili.
3. Mantiene coerenza con `commesse_*` dove l'identificazione sorgente e` gia` testuale.
4. Riduce coupling tra domini diversi (vendite, utility, future integrazioni ticket/API).

Nota:
nelle tabelle che oggi hanno `uuid` (es. `attivita_fatturabili.sorgente_uid`) la mappatura
deterministica resta possibile per compatibilita` runtime, ma il modello canonico
di tracciamento sorgente resta `text`.

### 24.3 Struttura tabella proposta

Tabella tecnica unica (nome da confermare in DB design):
`vendite.documenti_fatturazione_canali`

Campi minimi:

- `id bigserial`
- `sorgente_tipo_id bigint not null`
- `sorgente_uid text not null`
- `canale_codice varchar(32) not null` (`COMMESSA|PREVENTIVO|ORDINE|DDT|DIRETTO`)
- `stato_canale varchar(16) not null` (`APERTO|CONSUMATO|BLOCCATO`)
- `target_sorgente_tipo_id bigint null` (es. sorgente target creata)
- `target_sorgente_uid text null`
- `motivo_blocco text null`
- `meta jsonb not null default '{}'::jsonb`
- audit standard (`data_insert`, `user_insert`, `data_update`, `user_update`)

Vincoli minimi:

- unique parziale: un solo `stato_canale='APERTO'` per (`sorgente_tipo_id`,`sorgente_uid`)
- check su domini `canale_codice` / `stato_canale`
- FK su `config.sorgenti` per `sorgente_tipo_id` e `target_sorgente_tipo_id`

### 24.4 Regola funzionale uniforme

Regola generale:

- quando un documento viene instradato su un canale, quel canale viene `CONSUMATO`;
- i canali alternativi diventano `BLOCCATO` (se policy esclusiva attiva).

Applicazioni immediate:

- `PREVENTIVO -> ORDINE`: canale preventivo bloccato per fatturazione diretta
- `ORDINE -> DDT`: in base alla policy, blocco fatturazione diretta ordine oppure coesistenza controllata
- `CONTRATTO`: routing esplicito (`DIRETTO_COMMESSA` / `VIA_PREVENTIVO` / `VIA_ORDINE`)

Policy esclusivita` v0 (definitiva in sviluppo):

- **PREVENTIVO (root)**:
  - `PREVENTIVO` APERTO finche` non nasce `ORDINE_VENDITA` da quel preventivo;
  - alla conversione: `PREVENTIVO -> CONSUMATO` con target ordine.
- **ORDINE_VENDITA (root)**:
  - `ORDINE_VENDITA` APERTO finche` non nasce `DDT_VENDITA` collegato;
  - alla conversione: `ORDINE_VENDITA -> CONSUMATO` con target ddt.
- **DDT_VENDITA (root)**:
  - `DDT_VENDITA` APERTO come canale corrente;
  - eventuali canali alternativi APERTI sulla stessa sorgente vengono auto-bloccati dalla funzione canali.
- **CONTRATTO (root)**:
  - apertura `DIRETTO` su inserimento contratto;
  - eventuali altri canali APERTI sulla stessa sorgente vengono auto-bloccati dalla funzione canali.

Implementazione DB di riferimento:
- `vendite.fn_set_documento_canale_stato(...)`
- `vendite.trgfn_documenti_sync_canali()`
- pgTAP: `db/pgtap/vendite/test-documenti-fatturazione-canali-v1.sql`,
  `db/pgtap/vendite/test-documenti-canali-sync-v1.sql`

### 24.5 Checklist aggiuntiva (analisi)

- [x] Definire la tabella canali sorgente-based (`sorgente_tipo_id` + `sorgente_uid text`)
- [x] Definire policy esclusivita` per ciascuna sorgente primaria (contratto/preventivo/ordine/ddt)
- [x] Introdurre funzione DB unica di transizione stato canale (set/open/consume/block)
- [x] Copertura pgTAP tabella/funzione canali (`test-documenti-fatturazione-canali-v1.sql`)
- [x] Allineare i trigger/flow di conversione (`preventivo->ordine`, `ordine->ddt`) al nuovo registro canali

---

## 25) Piano implementazione backend — definitivo (24-02-2026)

### 25.0 Premessa e stato baseline

**DB completato dal team (non va rifatto):**

- [x] DB-L0/L1/L2/L3/L4/L5 commesse — schema, funzioni, test pgTAP
- [x] DB-L1/L2/L3 listini — schema, resolver, integrazione commessa
- [x] §11 backend refactor — `_decode_jsonb`, `get_attivita_branch_summary`,
      `get_lotto_attivita_info`, `fn_list_attivita_sorgenti_abilitate`

**Stato pipeline attività (Python):**

- [x] `AttivitaPipelineRunner` — esiste ma da deprecare
- [x] `AttivitaPipelineStepExecutor` — esiste, 7 handler tutti `pass`, da eliminare
- [x] `AttivitaPipelineRepository` — esiste, metodi lotto/task-run da tenere
- [x] Nessun endpoint API esposto (nessun breaking change)

**Ordine esecuzione fasi:**

```text
FASE 1 → FASE 2 → FASE 4 → FASE 4.5 → FASE 3 → FASE 5 → FASE 6 → FASE 7
```

La FASE 4 (deprecazione) precede FASE 3 (step 0) per non costruire su codice da eliminare.
La FASE 4.5 (rettifiche) precede le API per non esporre un ciclo prezzi incompleto.

---

### 25.1 FASE 1 — Repository commesse

**Obiettivo:** layer Python che wrappa le funzioni DB commesse.

**File da creare:** `backend/apps/vendite/db/commesse_repository.py`

- [x] Struttura classe `CommesseRepository` con `_to_jsonb_param` e `_decode_jsonb`
- [x] `get_or_create_commessa(...)` — wrappa `fn_get_or_create_commessa`
- [x] `link_sorgente(...)` — wrappa `fn_link_commessa_sorgente`
- [x] `upsert_attivita(CommessaAttivitaInput)` — wrappa `fn_upsert_commessa_attivita`
- [x] `get_commessa_stato(commessa_id)` — wrappa `fn_get_commessa_stato`
- [x] `emit_attivita_fatturabili(commessa_id, lotto_attivita_id, only_approved, dry_run)` — wrappa `fn_emit_attivita_fatturabili_da_commessa`
- [x] `log_push_run(...)` — wrappa `fn_log_commessa_push_run` → `vendite.commesse_push_log`
- [x] `get_push_log(push_log_id)` — SELECT `vendite.commesse_push_log`
- [x] TypedDict `CommessaEmitResult`, `CommessaStatoResult`, `CommessaPushLogRow` in `types.py`
- [x] Dataclass `CommessaAttivitaInput` (28 campi, opzionali con default `None`)
- [x] Test `test_commesse_repository.py` — 10 test verdi (mock DB, verifica SQL e mapping)

---

### 25.2 FASE 2 — Orchestratore push + handler sorgenti

**Obiettivo:** `CommessaPushOrchestrator` stateless con handler per tipo sorgente.

**File creati:**

- `backend/apps/vendite/services/commesse_push_orchestrator.py`
- `backend/apps/vendite/services/commesse_source_handlers.py`

#### 25.2.1 Orchestratore

- [x] Struttura `CommessaPushOrchestrator` con handler registry e DI repository
- [x] `run(source_types=None, dry_run=False) → PushReport` — fan-out indipendente
- [x] Isolamento errori per handler (`try/except`, continua sugli altri)
- [x] Scrittura `commesse_push_log` al completamento (successo, parziale e dry_run)
- [x] `PushReport` dataclass: `stato`, `risultato` per handler, `dry_run`, `durata_ms`, `push_log_id`
- [ ] Supporto `pg_try_advisory_lock` anti-concorrenza (da definire in sviluppo)

**Note implementazione:**

- dry_run=True: il log viene comunque scritto con `dry_run=True` per audit
- `_compute_stato`: COMPLETATO / PARZIALE / ERRORE (nessun handler = ERRORE)
- `HandlerResult.as_dict()` serializza per JSONB risultato per handler

#### 25.2.2 Handler sorgenti

- [x] `BaseSourceHandler` — classe astratta con interfaccia `run(dry_run) → HandlerResult`
- [x] `HandlerResult` — dataclass: `handler_name`, `created`, `updated`, `skipped`, `errors`
- [x] `HandlerPreventivi` — stub, richiede DB: `fn_list_preventivi_da_pushare`
  - [ ] Query selezione preventivi eleggibili — **richiede fn_list_preventivi_da_pushare (team DB)**
  - [ ] Mapping preventivo → `CommessaAttivitaInput` — da implementare dopo fn DB
  - [ ] Gestione `stato_commessa = CONVERTITO` (skippa senza errore)
- [x] `HandlerOrdini` — stub, richiede DB: `fn_list_ordini_da_pushare`
  - [ ] Query selezione ordini eleggibili — **richiede fn_list_ordini_da_pushare (team DB)**
  - [ ] Mapping ordine → `CommessaAttivitaInput` — da implementare dopo fn DB
- [x] `HandlerConsumi` — stub, richiede DB: `fn_list_consumi_da_pushare`
  - [ ] Query selezione consumi eleggibili — **richiede fn_list_consumi_da_pushare (team DB)**
  - [ ] Mapping consumo → `CommessaAttivitaInput` — da implementare dopo fn DB
- [x] Test `test_commesse_push_orchestrator.py` — 9 test verdi (isolamento, dry_run, filtro, log, stato)

---

### 25.3 FASE 3 — Step 0 pull nella pipeline fatturazione

**Obiettivo:** aggiungere handler `pull_attivita_da_commessa` come primo step
della pipeline di fatturazione, che chiama `fn_emit_attivita_fatturabili_da_commessa`.

**File da modificare:** `backend/apps/vendite/services/pipeline_step_executor.py`

- [ ] Aggiungere al handler registry: `"pull_attivita_da_commessa": self._handle_pull_attivita_da_commessa`
- [ ] Implementare `_handle_pull_attivita_da_commessa(...)`:
  - [ ] Chiama `commesse_repo.emit_attivita_fatturabili(lotto_id, dry_run)`
  - [ ] Legge anomalie dal result e le logga come segnalazioni (da definire in sviluppo)
  - [ ] Propaga dry_run al DB
- [ ] Aggiungere `CommesseRepository` come dipendenza iniettabile in `PipelineStepExecutor`
- [ ] Configurazione DB: registrare step `PULL_COMMESSA` come step 0 della pipeline
  fatturazione in `vendite.attivita_fatturabili_pipeline` — da concordare col team DB
- [ ] Test: aggiornare `test_pipeline_step_executor.py` con test per nuovo handler

---

### 25.4 FASE 4 — Deprecazione pipeline attività

**Obiettivo:** eliminare il codice mai implementato, ridurre il repository.

#### 25.4.1 File da eliminare

- [ ] `backend/apps/vendite/services/attivita_pipeline_step_executor.py`
      (7 handler tutti `pass` — zero logica da preservare)
- [ ] `backend/apps/vendite/services/attivita_pipeline_runner.py`
      (sostituito da step 0 FASE 3)

#### 25.4.2 `attivita_pipeline_repository.py` — metodi da rimuovere

- [ ] Gruppo 2 — pipeline steps: `list_attivita_pipeline_steps`,
      `get_attivita_step_processes`, `get_attivita_pipeline_id_for_step`
- [ ] Gruppo 3 — sorgenti: `list_sorgenti_abilitate`
- [ ] Gruppo 4 — task registry: `get_dominio_id`, `get_task_handler_code`
- [ ] Gruppo 5 — task policy: `get_attivita_task_policy`, `task_policy_exists`

#### 25.4.3 File da tenere invariati

- [ ] `attivita_pipeline_repository.py` — gruppi 1 (lotto) e 6 (task runs) e helpers
- [ ] `attivita_pipeline_error_logger.py` — riusato dallo step 0
- [ ] `pipeline_repository.py` — pipeline fatturazione, invariato
- [ ] `lotto_segnalazioni_service.py` — invariato

#### 25.4.4 Test da aggiornare

- [ ] `test_attivita_pipeline_repository.py` — rimuovere test per gruppi eliminati 2/3/4/5
- [ ] Verificare nessun import orfano dopo eliminazione file

---

### 25.5 FASE 4.5 — Rettifiche listino (layer Python)

**Obiettivo:** completare il ciclo prezzi — senza questo i flag `prezzo_da_riallineare = TRUE`
si accumulano senza auto-correzione (gap funzionale identificato in §23).

Le funzioni DB di L4 sono già presenti (team DB). Serve il layer Python.

**File da creare:**

- `backend/apps/vendite/db/commesse_rettifiche_repository.py`
- `backend/apps/vendite/services/commesse_rettifiche_service.py`

#### 25.5.1 Repository rettifiche

- [ ] Struttura `CommesseRettificheRepository`
- [ ] `apply_rettifica(commessa_attivita_id, delta_prezzo, motivo, tipo)` — wrappa `fn_apply_rettifica`
- [ ] `list_righe_da_riallineare(...)` — legge righe con `prezzo_da_riallineare = TRUE`
- [ ] Mapping output → dataclass (da definire in sviluppo)

#### 25.5.2 Service rettifiche

- [ ] Struttura `CommesseRettificheService`
- [ ] Canale manuale: `applica_rettifica_manuale(commessa_attivita_id, delta, motivo)` con validazione
- [ ] Canale automatico: `processa_righe_da_riallineare(lotto_id)` — consuma flag
      `prezzo_da_riallineare`, calcola delta, applica rettifica
  - [ ] Logica calcolo delta (da definire in sviluppo — dipende da struttura `fn_apply_rettifica`)
  - [ ] Gestione caso delta = 0 (skip senza errore)
  - [ ] Integrazione con `LottoSegnalazioniService` per segnalare rettifiche applicate
- [ ] Test `test_commesse_rettifiche_service.py` — da definire in sviluppo

---

### 25.6 FASE 5 — API endpoints

**Obiettivo:** esporre orchestratore push e commesse al frontend.

**File da modificare/creare:** `backend/apps/vendite/api/views.py`, `urls.py`

#### 25.6.1 Endpoint push orchestratore

- [ ] `POST /api/v1/commesse/push/` — lancia `CommessaPushOrchestrator.run()`
  - [ ] Parametri: `source_types[]`, `dry_run` — da definire in sviluppo
  - [ ] Response: `PushReport` serializzato
- [ ] `GET /api/v1/commesse/push/<log_id>/` — restituisce `commesse_push_log`
  - [ ] Serializer `PushLogSerializer` — da definire in sviluppo

#### 25.6.2 Endpoint commesse

- [ ] `GET /api/v1/commesse/<id>/` — dettaglio commessa + stato
  - [ ] Serializer da definire in sviluppo
- [ ] `GET /api/v1/commesse/<id>/attivita/` — lista `commesse_attivita`
  - [ ] Serializer da definire in sviluppo
- [ ] Eventuali altri endpoint (da definire in sviluppo in base a esigenze frontend)

#### 25.6.3 Endpoint da rimuovere (pipeline attività)

- [ ] Rimuovere `POST /attivita-pipeline/run/`
      (o marcare deprecated con flag configurabile per transizione)
- [ ] Rimuovere `GET /attivita-pipeline/<id>/status/`
- [ ] Valutare `GET /attivita-pipeline/<id>/task-runs/` — reindirizzare o mantenere

---

### 25.7 FASE 6 — Test suite

**Obiettivo:** suite completa verde prima del go-live.

- [ ] `test_commesse_repository.py` — FASE 1
- [ ] `test_commesse_push_orchestrator.py` — FASE 2
- [ ] `test_commesse_source_handlers.py` — FASE 2
- [ ] `test_commesse_rettifiche_service.py` — FASE 4.5
- [ ] `test_pipeline_step_executor.py` aggiornato — FASE 3
- [ ] `test_attivita_pipeline_repository.py` aggiornato — FASE 4
- [ ] Run suite completa: `./manage-test.sh apps.vendite.tests -v 2`
  - [ ] Zero regressioni sulla pipeline fatturazione esistente
  - [ ] Nuovi test verdi

---

### 25.8 FASE 7 — Cleanup finale

- [ ] Aggiornare header `attivita_pipeline_repository.py` ridotto (rimuovere riferimenti a gruppi eliminati)
- [ ] Verificare nessun import orfano nei file modificati
- [ ] Marcare `ripresa-lavori-attivita-fatturabili.md` come superato (nota in testa al file)
- [ ] Aggiornare §20.5 (timing deprecazione) con data completamento effettiva
- [ ] Allineare `gestione-listini.md` §13 se FASE 4.5 ha prodotto variazioni al modello rettifiche

---

### 25.9 Gate di uscita — go-live backend

- [ ] FASE 1 completata e test verdi
- [ ] FASE 2 completata e test verdi
- [ ] FASE 3 step 0 integrato e testato
- [ ] FASE 4 deprecazione eseguita — zero riferimenti a file eliminati
- [ ] FASE 4.5 rettifiche operative — ciclo prezzi chiuso
- [ ] FASE 5 endpoint esposti e documentati
- [ ] FASE 6 suite completa verde (zero regressioni)
- [ ] FASE 7 cleanup completato
- [ ] Revisione finale con team DB: nessuna funzione DB referenziata da codice eliminato
