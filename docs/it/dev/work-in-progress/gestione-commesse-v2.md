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
6. **Prezzi gestiti a livello di fatturazione** — la commessa non blocca i prezzi, li segnala
   se stantii; la verifica definitiva avviene alla pipeline di fatturazione.
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
CREATA → PRONTA_FATTURAZIONE → CHIUSA
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
stato                   BOZZA | CREATA | APERTA | IN_ESECUZIONE |
                        PRONTA_FATTURAZIONE | CHIUSA
stato_operativo         APERTO | CHIUSO | ANNULLATO
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

I campi `sorgente_tipo_id / sorgente_uid / sorgente_riga` restano invariati
e continuano a rappresentare la root source originale.

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
UNIQUE (commessa_attivita_id, segment_key) WHERE attivo = TRUE
```

Unicità di sicurezza su root source:
```sql
UNIQUE (sorgente_tipo_id, COALESCE(sorgente_uid::text, sorgente_riga::text), segment_key)
WHERE attivo = TRUE
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

Da implementare in DB-3. Definizioni principali, dettagli tecnici al team DB.

| Funzione | Scopo |
|---|---|
| `fn_get_or_create_commessa(...)` | Risolve o crea commessa per la sorgente in ingresso |
| `fn_link_commessa_sorgente(...)` | Collega la sorgente ROOT alla commessa |
| `fn_upsert_commessa_attivita(...)` | Inserisce/aggiorna riga operativa con idempotenza su `segment_key` |
| `fn_emit_attivita_fatturabili_da_commessa(...)` | Pull commessa → `attivita_fatturabili` (step 0 pipeline) |
| `fn_resolve_commessa_prezzi(lotto_id)` | Individua righe con listino stantio nel perimetro lotto |
| `fn_get_commessa_stato(commessa_id)` | Stato + info commessa in un round-trip |

Note per `fn_emit_attivita_fatturabili_da_commessa`:
- Legge sempre la ROOT da `commesse_sorgenti`.
- Se ROOT mancante → errore bloccante.
- Scrive `commessa_id` e `commessa_attivita_id` su ogni riga emessa.
- Propaga `prezzo_bloccato` da `commesse_attivita` a `attivita_fatturabili`.
- I campi `sorgente_*` in `attivita_fatturabili` prendono i valori dalla ROOT.
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
- **Campi `sorgente_*` su `attivita_fatturabili`** — restano e rappresentano la root source.
- **Logica `Idempotency-Key` sulle API** — invariata.
- **Branch policy BRANCH/GLOBAL** — invariata.

---

## 16) Nota futura — Utilities su commessa AUTO (senza bypass)

Decisione di indirizzo (da implementare in fase successiva, non ora):

1. per fatturazioni extra ad alto volume (energia/gas/idrico) non si introduce bypass diretto a `attivita_fatturabili`;
2. si usa il percorso standard tramite `commessa AUTO`, come per i preventivi con `fatturazione_immediata`;
3. in `AUTO` il codice commessa business puo` essere nullo (se previsto dal modello DB), mantenendo comunque `commessa_id` e `commessa_attivita_id` valorizzati sulle righe emesse;
4. i campi `sorgente_*` restano sempre valorizzati con la provenienza originaria.

Scopo della nota:

1. preservare il modello v2 come riferimento unico;
2. evitare future deviazioni architetturali quando si aprira` il cantiere utilities.
- **`fatturazione_immediata` come flag** — resta sul preventivo, cambia solo il significato
  (vedi §4.3).
