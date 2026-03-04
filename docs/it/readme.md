# 🪵 ZeroERP

**L'ERP open-source per le aziende italiane, costruito con lo sviluppo concentrico.**

ZeroERP nasce dall'esperienza trentennale nel mondo gestionale italiano — utilities, multi-servizi, PMI — con un obiettivo chiaro: eliminare la complessita superflua mantenendo tutto cio che serve davvero. Il nome "Zero" non è un numero: è una filosofia. Zero complessita inutile, zero sovrastrutture, zero compromessi sulla sostanza.

---

> **Stato del progetto: sviluppo attivo — fase nucleo**
>
> ZeroERP è in costruzione attiva. Il database (anello centrale) è in fase avanzata
> con schema multi-funzionale, fatturazione elettronica e motore pratiche progettati.
> Le API REST Django sono in sviluppo. Non esiste ancora un'interfaccia frontend
> ne un rilascio utilizzabile. Chi arriva ora trova un cantiere aperto:
> le fondamenta sono solide, i muri si stanno alzando.

---

## Indice

- [🪵 ZeroERP](#-zeroerp)
  - [Indice](#indice)
  - [Filosofia](#filosofia)
  - [Sviluppo Concentrico](#sviluppo-concentrico)
  - [Architettura](#architettura)
  - [Stack Tecnologico](#stack-tecnologico)
  - [Struttura del Database](#struttura-del-database)
  - [Il Motore Pratiche](#il-motore-pratiche)
    - [Come funziona](#come-funziona)
    - [Struttura (13 tabelle nucleo)](#struttura-13-tabelle-nucleo)
    - [Funzionalita chiave](#funzionalita-chiave)
    - [Esempio: Ticket tecnico con preventivo](#esempio-ticket-tecnico-con-preventivo)
  - [Stato dello Sviluppo](#stato-dello-sviluppo)
  - [Installazione](#installazione)
    - [Prerequisiti](#prerequisiti)
    - [Setup rapido](#setup-rapido)
  - [Struttura del Repository](#struttura-del-repository)
  - [Roadmap](#roadmap)
    - [Fase 1 — Nucleo (in corso)](#fase-1--nucleo-in-corso)
    - [Fase 2 — Operativita](#fase-2--operativita)
    - [Fase 3 — Specializzazione](#fase-3--specializzazione)
    - [Fase 4 — Crescita](#fase-4--crescita)
  - [Documentazione](#documentazione)
  - [Licenza](#licenza)
  - [Autore](#autore)

---

## Filosofia

Gli ERP tradizionali crescono per accumulo: moduli aggiunti nel tempo, integrazioni forzate, strati di complessita che nessuno osa piu toccare. ZeroERP ribalta questo approccio.

Ogni funzionalita nasce da un nucleo centrale stabile e si espande in modo organico, come gli anelli di un tronco d'albero. Il cuore è il piu denso e il piu solido. Ogni nuovo anello si appoggia su quelli interni rafforzandoli. Il risultato è un sistema che cresce senza perdere coerenza.

**Principi fondamentali:**

- La business logic vive nel database, non sparpagliata nel codice applicativo
- Ogni operazione è tracciabile: il sistema è un giornale di bordo permanente
- La configurazione prevale sulla personalizzazione: si adatta senza riscrivere
- Multi-azienda nativo per gruppi societari: un gruppo, piu emittenti fiscali, un unico sistema. Non multi-tenant per scelta: ogni organizzazione la propria istanza, i propri dati, il proprio perimetro di sicurezza
- Pensato per l'Italia: fatturazione elettronica SDI, normative ARERA, fiscalita italiana

---

## Sviluppo Concentrico

> *Concentric Development — una metodologia nata dalla pratica, non dalla teoria.*

Lo sviluppo concentrico è il modello con cui ZeroERP viene progettato e costruito. Non è agile, non è waterfall, non è sviluppo modulare tradizionale.

**Come funziona:**

Il nucleo si progetta con rigore assoluto. Ogni nuova funzionalita si aggiunge come un anello esterno che si appoggia sugli anelli interni. Non esistono integrazioni tra moduli perchè tutto parla gia attraverso il centro. La crescita è incrementale ma la struttura è coerente dal primo giorno.

Quando un anello esterno rivela che il nucleo non è abbastanza forte, si torna al centro e si corregge li — non con un adapter, non con un connettore, non con una scorciatoia. Si riscrive l'anello interno e si propaga il cambiamento attraverso ogni strato soprastante. E' doloroso, è lento, ma è onesto. Nella sezione di un tronco reale, gli anelli piu scuri sono quelli che hanno lavorato di piu, che sono stati compressi dal peso della crescita. Non sono errori: sono il legno piu forte.

**Perche è diverso:**

- L'**agile** lavora a sprint ma non garantisce coerenza strutturale
- Il **waterfall** pianifica tutto prima ma non regge i cambiamenti
- Lo **sviluppo modulare** costruisce pezzi separati e poi li integra con connettori
- Lo **sviluppo concentrico** parte dal cuore e cresce mantenendo l'integrita ad ogni passaggio. Quando il centro cambia, tutto cambia insieme, fino in fondo

**La metafora:**

Come un tronco d'albero. Il cuore del legno è il piu antico e il piu duro. Ogni anello è un anno di crescita. Se tagli il tronco puoi leggere tutta la storia — esattamente come il giornale di bordo del sistema. Gli anelli scuri non sono cicatrici: sono la prova del lavoro dell'artigiano che è tornato al centro per renderlo migliore.

```
        ╭─────────────────────────╮
       │    portale / API ext.     │
      │  ╭─────────────────────╮  │
      │ │    fatturazione SDI   │  │
      │ │  ╭─────────────────╮ │  │
      │ │ │   anagrafiche     │ │  │
      │ │ │  ╭─────────────╮ │ │  │
      │ │ │ │   PRATICHE    │ │ │  │
      │ │ │ │   (nucleo)    │ │ │  │
      │ │ │  ╰─────────────╯ │ │  │
      │ │  ╰─────────────────╯ │  │
      │  ╰─────────────────────╯  │
       ╰─────────────────────────╯
```

*Il concetto di Sviluppo Concentrico è nato il 2 marzo 2026 durante la progettazione di ZeroERP.*
*Leggi il [Manifesto completo](docs/concentric_development_manifesto.md) — disponibile in [italiano](docs/manifesto_sviluppo_concentrico.md) e [inglese](docs/concentric_development_manifesto.md).*

---

## Architettura

ZeroERP segue un'architettura a tre livelli con la business logic centralizzata nel database:

```
┌──────────────────────────────────┐
│          Frontend (SPA)          │
│     Vue.js / React (TBD)        │
├──────────────────────────────────┤
│        Backend (API REST)        │
│      Django REST Framework       │
│   Autenticazione / Permessi /    │
│   Handler flussi / Orchestrator  │
├──────────────────────────────────┤
│         Database (nucleo)        │
│          PostgreSQL              │
│  Funzioni / Trigger / Vincoli /  │
│  Validazioni / Controllo flussi  │
└──────────────────────────────────┘
```

**Scelte architetturali chiave:**

- **Business logic nel DB**: le validazioni, i controlli di sequenza, il giornale di bordo sono gestiti da funzioni e trigger PostgreSQL. Nessun bypass possibile, ne da interfaccia ne da API esterna
- **Orchestrator pattern**: le operazioni complesse (es. push commessa, avanzamento flussi) sono coordinate da un orchestrator che invoca le funzioni DB nella sequenza corretta
- **Handler per tipo flusso**: ogni tipo di flusso ha un handler Django che implementa la logica specifica. Il nucleo DB resta agnostico rispetto all'implementazione
- **Multi-azienda per gruppi societari**: il campo `azienda_id` distingue gli emittenti fiscali all'interno dello stesso gruppo (es. multi-utility con societa gas, idrica, servizi). Non è multi-tenant: ogni organizzazione ha la propria istanza, per scelta deliberata di sicurezza e isolamento dei dati

---

## Stack Tecnologico

| Componente         | Tecnologia              | Note                                             |
| ------------------ | ----------------------- | ------------------------------------------------ |
| Database           | PostgreSQL 16+          | Nucleo del sistema, business logic centralizzata |
| Versioning DB      | Liquibase               | Changelog XML per tutte le migrazioni            |
| Backend            | Django 5+ / DRF         | API REST, autenticazione, handler flussi         |
| Frontend           | TBD (Vue.js / React)    | SPA con interfaccia operatore/dashboard          |
| Linguaggio         | Python 3.12+ / SQL      |                                                  |
| Containerizzazione | Docker / Docker Compose | Ambiente di sviluppo e deploy                    |

---

## Struttura del Database

Il database è organizzato per schema funzionali PostgreSQL, ognuno con responsabilita chiare:

| Schema        | Responsabilita                                                   |
| ------------- | ---------------------------------------------------------------- |
| `pratiche`    | **Nucleo centrale** — motore pratiche, flussi, giornale di bordo |
| `anagrafiche` | Soggetti, ruoli, indirizzi, contatti                             |
| `vendite`     | Ciclo attivo, ordini, contratti                                  |
| `acquisti`    | Ciclo passivo, ordini fornitori                                  |
| `catalogo`    | Prodotti, servizi, listini                                       |
| `config`      | Configurazione di sistema, parametri                             |
| `contabilita` | Piano conti, registrazioni, partitario                           |
| `magazzino`   | Giacenze, movimenti, lotti                                       |
| `pagamenti`   | Incassi, pagamenti, scadenzario                                  |
| `storico`     | Archiviazione dati storici                                       |
| `core`        | Funzioni trasversali, utilities, permessi                        |

---

## Il Motore Pratiche

Il cuore di ZeroERP. **Tutto è una pratica.** Ogni operazione transita dal motore pratiche, che funziona come un workflow engine leggero ma rigoroso.

### Come funziona

Chi configura prestazioni e flussi ottiene un workflow con controllo di sequenza, prerequisiti, assegnazioni a reparti diversi e tempi monitorati. Chi non configura ottiene comunque un giornale di bordo completo con tracciabilita totale.

### Struttura (13 tabelle nucleo)

**Catalogo (configurazione):**
- `tipo_prestazione` — categorie di pratica (es. Attivazione, Ordine, Reclamo)
- `template_flusso` — sequenza prevista di step per ogni tipo
- `template_flusso_prerequisito` — dipendenze tra flussi (paralleli e convergenze)
- `template_flusso_azione` — regole automatiche: "flusso X con esito Y genera flusso Z"

**Esecuzione (istanze operative):**
- `pratica` — testata della pratica con stato, priorita, soggetto, date
- `flusso` — singolo step con stato, esito, operatore assegnato, reparto

**Documentale:**
- `nota_pratica` / `nota_flusso` — note tipizzate (generale, interna, cliente, tecnica, legale)
- `allegato_pratica` / `allegato_flusso` — documenti e immagini con versionamento e hash SHA-256

**Tracciabilita:**
- `giornale` — audit trail immutabile alimentato automaticamente via trigger
- `sospensione` — periodi di sospensione con calcolo automatico impatto sulla timeline
- `formula_tempo` — definizione KPI e SLA tra flussi, al netto delle sospensioni

### Funzionalita chiave

- **Flussi non lineari**: supporto a rami paralleli, convergenze e flussi opzionali tramite prerequisiti espliciti
- **Flussi che generano flussi**: un flusso completato puo generare automaticamente sotto-flussi assegnati ad altri reparti
- **Controllo sequenza**: prerequisiti minimi (non puoi farlo troppo presto) e massimi (non puoi farlo troppo tardi)
- **Handler configurabili**: ogni tipo di flusso puo avere un handler Django specifico
- **Apertura verso l'esterno**: un sistema esterno o un portale cliente interagisce con due operazioni: "apri pratica" e "avanza flusso"
- **Processi batch separati**: le operazioni massive (fatturazione, letture) hanno registri dedicati. Solo le anomalie generano pratiche per intervento umano

### Esempio: Ticket tecnico con preventivo

```
Ricezione ticket (reparto Tecnico)
    |
    v
Valutazione tecnica (reparto Tecnico)
    |-- esito: serve preventivo
    |
    v (azione automatica)
Predisposizione preventivo (reparto Commerciale)
    |
    v
Invio al cliente (reparto Commerciale)
    |
    v
Attesa accettazione
    |-- esito positivo
    |
    v (azione automatica)
Schedulazione intervento (reparto Tecnico)
    |
    v
Esecuzione e chiusura
```

Tutto tracciato nel giornale. Ogni passaggio tra reparti registrato. Il cliente vede lo stato dal portale.

---

## Stato dello Sviluppo

ZeroERP è un progetto in costruzione attiva. Questa è la fotografia attuale:

| Componente              | Stato              | Note                                            |
| ----------------------- | ------------------ | ----------------------------------------------- |
| Architettura database   | 🟢 Avanzato         | Schema multi-funzionale, struttura stabile      |
| Fatturazione SDI        | 🟢 Avanzato         | Modello dati completo                           |
| Motore pratiche         | 🟡 In progettazione | 13 tabelle nucleo definite, da implementare     |
| Sistema permessi        | 🟢 Avanzato         | Modello tre livelli per area funzionale         |
| API REST (fatturazione) | 🟡 In sviluppo      | Django REST Framework, endpoint in costruzione  |
| API REST (anagrafiche)  | 🔴 Da avviare       | Dipende dal completamento modello pratiche      |
| API REST (pratiche)     | 🔴 Da avviare       | In attesa implementazione schema DB             |
| Frontend                | 🔴 Da avviare       | Scelta tecnologica Vue.js / React ancora aperta |
| Dashboard operatore     | 🔴 Da avviare       | Richiede frontend e API pratiche                |
| Portale cliente         | 🔴 Da avviare       | Fase 3 della roadmap                            |
| Documentazione          | 🟡 In corso         | Guide tecniche in costruzione                   |

**Legenda**: 🟢 Avanzato / stabile — 🟡 In corso / in sviluppo — 🔴 Da avviare

---

## Installazione

> ⚠️ ZeroERP non ha ancora un rilascio utilizzabile. Le istruzioni seguenti sono per chi vuole esplorare il codice sorgenteècontribuire allo sviluppo.

### Prerequisiti

- PostgreSQL 16+
- Python 3.12+
- Liquibase 4.x
- Docker e Docker Compose (opzionale ma consigliato)

### Setup rapido

```bash
# Clona il repository
git clone https://github.com/[username]/zeroerp.git
cd zeroerp

# Avvia i servizi con Docker Compose
docker-compose up -d

# Applica le migrazioni database
liquibase update

# Avvia il backend Django
cd backend
pip install -r requirements.txt
python manage.py runserver
```

*Istruzioni dettagliate nella documentazione completa.*

---

## Struttura del Repository

```
zeroerp/

├── docker-compose.yml
├── db/
│   ├── changelog/              # Liquibase changelog files
│   │   ├── pratiche/           # Schema pratiche
│   │   ├── anagrafiche/        # Schema anagrafiche
│   │   ├── vendite/            # Schema vendite
│   │   ├── ...                 # Altri schema
│   │   └── master-changelog.xml
│   └── functions/              # Funzioni PostgreSQL
├── backend/
│   ├── manage.py
│   ├── zeroerp/                # Django project
│   ├── pratiche/               # App pratiche
│   ├── anagrafiche/            # App anagrafiche
│   └── ...                     # Altre app
├── frontend/                   # SPA (TBD)
└── docs/                       # Documentazione 
tecnica
├   ├──README.md
├   ├──LICENSE
```

---

## Roadmap

### Fase 1 — Nucleo (in corso)
- Schema database completo per tutti i moduli
- Motore pratiche operativo con tutte le 13 tabelle
- API REST per pratiche e anagrafiche

### Fase 2 — Operativita
- Dashboard operatore con gestione attivita per reparto
- Ciclo attivo: ordini, fatturazione, incassi
- Ciclo passivo: fornitori, acquisti, pagamenti

### Fase 3 — Specializzazione
- Moduli specifici utilities (letture, consumi, tariffe)
- Portale cliente/fornitore
- Integrazioni esterne (flussi distributori, ARERA)

### Fase 4 — Crescita
- Business intelligence e reportistica
- App mobile per operatori sul campo
- Marketplace estensioni

---

## Documentazione

- **ZeroERP Docs**: [github.com/[username]/zeroerp-docs](https://github.com/[username]/zeroerp-docs) — documentazione funzionale e tecnica
- **ZeroERP Logo**: [github.com/[username]/zeroerp-logo](https://github.com/[username]/zeroerp-logo) — risorse grafiche e linee guida brand

---

## Licenza

Questo progetto e distribuito con licenza [DA DEFINIRE].

Vedi il file [LICENSE](LICENSE) per i dettagli completi.

---

## Autore

**Michele Carlo**

Sviluppatore con oltre 30 anni di esperienza nel mondo gestionale, specializzato in sistemi ERP per utilities e PMI italiane. ZeroERP nasce dalla convinzione che la complessita non è una caratteristica, è un difetto.

> *"Zero complessita superflua. Crescita concentrica. Tutto tracciato negli anelli."*

---

<p align="center">
  <strong>ZeroERP</strong> — Sviluppo Concentrico / Concentric Development<br>
  <em>Ogni anello racconta la storia</em><br><br>
  🪵
</p>