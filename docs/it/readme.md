# ZeroERP

**ERP open-source per aziende italiane, progettato con approccio DB-first e sviluppo concentrico.**

ZeroERP nasce da esperienza diretta su sistemi gestionali in contesti utilities e PMI.
L'obiettivo e` ridurre la complessita` superflua mantenendo rigore su dati, regole e tracciabilita`.

---

## Stato progetto

> **Sviluppo attivo — DB, backend e frontend operativi su core, anagrafiche, catalogo, ciclo attivo completo (preventivi, offerte, contratti, ordini, DDT, resi, fatture, commesse), pratiche, documenti e presentazione configurabile. Non ancora rilasciato per produzione.**
>
> *Ultimo aggiornamento dello stato: **10 settembre 2026**.*
>
> La fotografia dettagliata, lo stato per componente e la roadmap sono mantenuti in
> un'unica fonte: la [Mappa Concentrica](./mappa-concentrica.md) (stato per anello +
> sezione Roadmap), con la storia datata nel suo
> [changelog](./dev/mappa-concentrica-changelog.md). Qui sotto solo uno snapshot.

---

## Indice

- [ZeroERP](#zeroerp)
  - [Stato progetto](#stato-progetto)
  - [Indice](#indice)
  - [Filosofia](#filosofia)
  - [Sviluppo Concentrico](#sviluppo-concentrico)
  - [Architettura](#architettura)
  - [Stack Tecnologico](#stack-tecnologico)
  - [Struttura del Database](#struttura-del-database)
  - [Motore Pratiche](#motore-pratiche)
  - [Stato dello Sviluppo](#stato-dello-sviluppo)
  - [Installazione](#installazione)
  - [Struttura Repository](#struttura-repository)
  - [Roadmap](#roadmap)
  - [Documentazione](#documentazione)
  - [Licenza](#licenza)
  - [Autore](#autore)

---

## Filosofia

ZeroERP adotta un modello **DB-first**:

- le regole critiche vivono nel database (vincoli, funzioni, trigger);
- Django orchestra i processi e espone API;
- la UI e` uno strato esterno, non il punto dove si decide la coerenza del dominio.

Principi guida:

- tracciabilita` operativa end-to-end;
- linguaggio dati coerente tra domini;
- crescita incrementale senza duplicare regole tra strati.

---

## Sviluppo Concentrico

Lo sviluppo concentrico e` una proposta progettuale: si consolida un nucleo comune e si cresce per anelli successivi.

Punti chiave:

- il nucleo e` stabile ma evolvibile quando emergono limiti reali;
- gli strati esterni dipendono da quelli interni, non il contrario;
- le integrazioni sono ridotte e semplificate tramite protocollo condiviso.

Approfondimento:

- [Manifesto (IT)](./sviluppo-concentrico.md)
- [Manifesto (EN)](../en/sviluppo-concentrico.md)
- [Vocabolario](./sviluppo-concentrico-vocabolario.md)

---

## Architettura

```
Frontend Vue 3 (presentazione, zero logica business)
    |
API REST Django (orchestrazione, permessi, endpoint)
    |
PostgreSQL (nucleo dominio: regole, workflow, audit)
```

Scelte architetturali:

- business logic critica nel DB;
- orchestrazione applicativa nel backend;
- isolamento per istanza organizzativa (non multi-tenant condiviso).

---

## Stack Tecnologico

| Componente         | Tecnologia                      |
| ------------------ | ------------------------------- |
| Database           | PostgreSQL 18                   |
| Versioning DB      | Liquibase 5                     |
| Backend            | Django 6.01 + DRF               |
| Linguaggio backend | Python 3.14                     |
| Frontend           | Vue 3.5, Vite 7, PrimeVue 4.5, Pinia 3 |
| Tooling docs/dev   | Zensical + preprocess docs, pre-commit, Docker |

---

## Struttura del Database

Il database e` organizzato per schemi funzionali principali:

- `anagrafiche`
- `catalogo`
- `acquisti`
- `vendite`
- `magazzino`
- `pagamenti`
- `contabilita` (⛔ nome di schema, vuoto — vedi nota sotto)
- `config`
- `storico`
- `documenti`
- `script`, `dbops`, `maintenance`, `internal`

Le migrazioni correnti sono mantenute in `db/changelog/migrations_v2/`.

---

## Motore Pratiche

Il motore pratiche e` il nucleo di workflow operativo:

- modella processi e stati;
- gestisce prerequisiti e avanzamenti;
- mantiene audit trail e tracciabilita`.

Il modello e` pensato per supportare processi non lineari e gestione multi-reparto.

---

## Stato dello Sviluppo

Snapshot (**30 agosto 2026**). Per il dettaglio per componente, lo stato per anello e
la roadmap aggiornata fa fede la [Mappa Concentrica](./mappa-concentrica.md); la
storia datata è nel suo [changelog](./dev/mappa-concentrica-changelog.md).

**Fondamenta**

- **Database**: operativo — 20 schemi, `daterange` nativo, PostgreSQL 18, automazioni parametriche (audit, storicizzazione, chiusure a scadenza, anti-overlap)
- **Coda lavori generica**: operativa — job queue DB-native transazionale, senza broker: la fondazione asincrona dell'ERP
- **Errori come contratto**: il significato di un errore è **a catalogo** (10 classi, 831 codici nel seed); status HTTP e reazione della UI si **derivano**, e l'errore porta un **bersaglio** che la UI trasforma in un gesto
- **Test DB**: 551 file pgTAP, in CI, eseguiti **come l'applicazione** — quindi con le policy RLS attive a ogni corsa; il debito noto è sceso da 86 rossi a 19

**Accessi e dati di base**

- **Autenticazione**: completa (JWT, multi-veste, email, token monouso, reset/invito/cambio password)
- **Permessi**: tre livelli — area funzionale, oggetto, azione di processo — con **RLS operatori attiva** a scope emittente fiscale
- **Anagrafiche**: soggetti e ruoli, indirizzi, contatti, conti bancari, risorse umane, emittenti fiscali, billing account, **titoli IVA del soggetto** con registro movimenti append-only
- **Catalogo**: articoli, unità di misura e conversioni, distinte base, note
- **Presentazione configurabile**: liste personalizzabili per profilo/emittente/utente e **dashboard home** a card KPI

**Processi**

- **Ciclo attivo completo**: preventivi, offerte commerciali, contratti, ordini, DDT, **resi**, fatture e **note di credito** — DB + backend + frontend, con la numerazione governata dal registro e l'IVA di riga decisa da un risolutore
- **Fatturazione**: pipeline batch a corsie, lotti, **cockpit da cui si agisce** (fattura adesso, rendi definitive, stampa massiva), tre lenti di lettura
- **Commesse**: multi-sorgente, quantità immutabili dopo la fatturazione, oneri manuali con la propria IVA
- **Motore pratiche**: operativo e **validato dal primo consumatore reale** (pratica PREVENTIVI); il secondo è ciò che ne promuoverà le astrazioni a contratti
- **Motore documentale**: template versionati, asset per emittente, PDF — **6 domini consumatori**, con tre percorsi di stampa distinti
- **Genealogia dei documenti**: da dove viene e dove è andato ogni documento del ciclo

**Aperto**

- **Incassi e contabili di pagamento**: il **posting è scritto** (contabile, saldo rata, sistemazioni) — ⛔ ma lo schema ha zero righe: di questo dominio è provato il *percorso*, mai l'*esito*, e il collaudo in-app è aperto
- **Fatturazione elettronica SDI**: payload pronto, builder XML e persistenza esito da fare
- **Acquisti, magazzino**: DB presente, backend ancora stub
- ⛔ **Contabilità: fuori perimetro, e lo schema è vuoto.** `contabilita` non ha
  tabelle, funzioni né viste: non è un modulo a metà, non c'è niente da finire.
  Se un giorno servirà, sarà un **aggancio a una contabilità esterna**, e la
  forma del piano dei conti la detta il **sistema di destinazione**
- **Integrazione AI v2**: contesto dinamico e nuovi tool (v1 operativa: 11 tool + widget conversazionale)

> Lavori in corso e previsti: vedi la [Roadmap nella Mappa Concentrica](./mappa-concentrica.md#3-roadmap).

---

## Installazione

ZeroERP non ha ancora un rilascio stabile per produzione.
Per setup ambiente di sviluppo, seguire:

- [Installazione](./installazione.md)
- [Liquibase Setup & Workflow](./liquibase-setup-workflow.md)

Nota: prima di applicare migrazioni DB in locale, verificare il workflow del team.

---

## Struttura Repository

Struttura essenziale:

- `backend/` -> progetto Django e app dominio
- `db/changelog/migrations_v2/` -> changelog Liquibase correnti
- `docs/` -> documentazione tecnica (IT/EN)
- `frontend/` -> area frontend
- `scripts/` -> utility di supporto sviluppo/CI

---

## Roadmap

La roadmap è mantenuta in un'unica fonte nella
[Mappa Concentrica §3](./mappa-concentrica.md#3-roadmap), organizzata in **lavori
in corso** (ciascuno con il suo documento vivo), **previsti**, **decisioni
aperte** — che non sono lavori — e **debito dichiarato**. Lì le voci sono solo
quelle aperte; la storia di ciò che è stato completato vive nel
[changelog della mappa](./dev/mappa-concentrica-changelog.md).

---

## Documentazione

La documentazione di ZeroERP non è un allegato al codice: è **dove le decisioni
sono scritte con il loro perché**. Chi arriva dopo — un collega, un agente AI, o
noi stessi fra sei mesi — deve poter capire *perché* una cosa è fatta così senza
ricostruirlo dal codice.

È divisa in **cinque famiglie**, che rispondono a domande diverse.

### 📘 Guide — «come funziona questa area, e perché»

Il livello concettuale: cosa fa un dominio, quali regole lo governano, quali
sono le sue trappole. **44 guide**, raggruppate per area:

- **Ciclo attivo** — [preventivi](./guide/gestione-preventivi.md) ·
  [offerte commerciali](./guide/gestione-offerte-commerciali.md) ·
  [contratti](./guide/gestione-contratti.md) · [ordini](./guide/gestione-ordini.md) ·
  [DDT](./guide/gestione-ddt.md) · [fatturazione](./guide/fatturazione.md) ·
  [cruscotti fatturazione](./guide/cruscotti-fatturazione.md) ·
  [commesse](./guide/gestione-commesse.md) · [listini](./guide/gestione-listini.md)
- **Regole trasversali ai documenti** — [numerazione: come nasce un numero o un
  codice](./guide/numerazione-documenti-e-codici.md) ·
  [il risolutore IVA di riga](./guide/iva-risolutore-di-riga.md) — ⭐ **meccanismi
  unici** condivisi da tutta la famiglia vendite (e domani dagli acquisti): le
  guide dei singoli documenti ci **rimandano** invece di rispiegarli, così non
  nascono tre versioni della stessa regola
- **Ciclo passivo** — 🔴 **nessuna guida, ed è un buco dichiarato** (2026-09-02).
  Le decisioni architetturali di fondo (emittente fiscale, motore di stato,
  numerazione, indirizzi) sono state chiuse il 01-09-2026, ma il primo lotto del
  cantiere non è atterrato: finché non lo è, una guida racconterebbe
  un'intenzione. ⚠️ **Dove la documentazione acquisti c'è già, e dove no**: lo
  schema è disegnato e documentato — [`dbzero/acquisti/`](./dbzero/acquisti/index.md)
  ha ordini, DDT, note e le loro schede concettuali; l'area
  [`backend/acquisti/`](./backend/acquisti/index.md) invece è **vuota di
  proposito**, perché l'app Django è ancora uno scheletro senza endpoint.
  Materiale di lavoro in `dev/work-in-progress/`:
  `analisi-simmetria-ordini-acquisto.md`, `sviluppo-preventivi-acquisti.md`.
- **Anagrafiche e dati di base** — [soggetti e ruoli](./guide/soggetti-e-ruoli-anagrafici.md) ·
  [indirizzi](./guide/gestione-degli-indirizzi.md) · [contatti](./guide/gestione-dei-contatti.md) ·
  [conti bancari](./guide/gestione-conti-bancari.md) ·
  [istanze utility](./guide/gestione-delle-istanze-utility.md)
- **Incassi e pagamenti** — [modello contabile dei pagamenti](./guide/gestione-dei-pagamenti.md)
  (centri di riscossione, contabili, movimenti, compensazioni, fondi fattura)
- **Processi e orchestrazione** — [pratiche](./guide/gestione-pratiche.md) e la sua
  [configurazione](./guide/gestione-pratiche-configurazione.md) ·
  [code di lavoro](./guide/gestione-code-di-lavoro.md) ·
  [tracciamento processi e job](./guide/analisi-tracciamento-processi-e-job.md) ·
  [job pgAgent](./guide/processi-pgagent-funzionali.md) ·
  [statistiche del planner](./guide/statistiche-del-planner.md) ·
  [un database che resta veloce](./guide/database-che-resta-veloce.md)
- **Documenti e comunicazioni** — [documenti e stampe](./guide/documenti-e-stampe.md) ·
  [gestione mail](./guide/gestione-mail.md)
- **Accessi e sicurezza** — [multi-face auth](./guide/architettura-multi-face-auth.md) ·
  [permessi e autorizzazioni](./guide/architettura-permessi-e-autorizzazioni.md) ·
  [risorse umane e accessi](./guide/risorse-umane-e-accessi.md) ·
  [contratto GUC](./guide/contratto-guc-app.md)
- **Dati, audit e storicizzazione** — [audit e tracciabilità](./guide/audit-e-tracciabilita.md) ·
  [storicizzazione tabelle](./guide/storicizzazione-tabelle.md) ·
  [`tx_id`](./guide/tx_id_implementation_guide.md) ·
  [sorgente polimorfa](./guide/sorgente-polimorfa.md) ·
  [uso di `obsoleto`](./guide/uso-di-obsoleto.md)
- **Configurazione** — [parametri multi-scope](./guide/configurazione-e-gestione-parametri.md) ·
  [liste configurabili](./guide/configurazione-liste.md) ·
  [automazioni DB](./guide/automazione-db.md)
- **Qualità e presidi** — [messaggi di errore e log](./guide/Messaggi-di-Errore-e-Generazione-Log.md) ·
  [presidi e registri del debito](./guide/presidi-e-registri-del-debito.md) ·
  [come si scrive un test pgTAP](./guide/pgtap-come-si-scrive-un-test.md)
- **AI** — [integrazione AI](./guide/integrazione-ai.md)

### 🗄️ `dbzero/` — «com'è fatto davvero il database, adesso»

Documentazione **auto-generata** dall'oggetto vivo, per **20 schemi**: una scheda
per ogni tabella, vista e funzione, con colonne, vincoli, indici e trigger.

- ⛔ Le schede auto-generate **non si modificano a mano**: si rigenerano
- ✅ Accanto a ognuna c'è una cartella `manual/` — lì vive la **semantica**: a
  cosa serve quell'oggetto, quali regole lo governano, cosa **non** è
- ⭐ Per capire o modificare un oggetto esistente, **la fonte è questa**, non gli
  YAML di migrazione (che sono quasi sempre superati da revisioni successive)

### 🔧 `backend/` — «il contratto di ogni endpoint»

Manuali per **15 domini** applicativi: scopo, input, output, regole, dipendenze
DB. Struttura standard, così due manuali si confrontano a colpo d'occhio.

### 🛠️ `dev/` — «come si lavora qui»

Le regole operative e il cantiere aperto:

- [Linee guida API](./dev/api.md) e
  [policy di ricerca e paginazione](./dev/Policy-ricerca-e-paginazione(API-DB).md)
- [Linee guida SQL](./linee-guida-sql.md) e [trigger](./linee-guida-trigger.md)
- [Workflow Liquibase](./liquibase-setup-workflow.md)
- **Cataloghi dei building block** [backend](./dev/backend/catalogo-building-block-backend.md)
  e [frontend](./dev/frontend/catalogo-building-block-frontend.md) — la prima
  difesa contro le duplicazioni: prima di scrivere qualcosa di nuovo, si guarda lì
- [Ricette: dove intervenire](./dev/ricette-dove-intervenire.md) e
  [trappole](./dev/trappole.md)
- `work-in-progress/` — i **brief dei cantieri aperti**, con le decisioni prese e
  il loro perché; `work-done/` — gli stessi, chiusi

### 🧭 Fondamenta — «perché il progetto è fatto così»

- [Manifesto dello sviluppo concentrico](./sviluppo-concentrico.md) e il suo
  [vocabolario](./sviluppo-concentrico-vocabolario.md)
- [Mappa Concentrica](./mappa-concentrica.md) — stato per anello, roadmap e
  lezioni metodologiche
- [Architettura](./architettura.md) · [schemi DB](./schemidb.md) · [API](./API.md)
- [Perché ZeroERP](./perche-zeroerp.md) · [Introduzione](./introduzione.md)
- [PostgreSQL](./postgresql/intro.md) — estensioni, GUC, pgAgent, dblink, upgrade
- [Glossario](./glossario/glossario-utility.md) ·
  [Versioni supportate](./versioni-supportate.md)

> **Indice completo**: [indice documentazione IT](./index.md).

---

## Licenza

ZeroERP e` distribuito con licenza **GNU GPL v3 o successiva**.

Riferimenti:

- [LICENSE (IT)](./LICENSE.md)
- [LICENSE (EN)](../en/LICENSE.md)

---

## Autore

**Michele Carlo**

Sviluppatore con oltre 30 anni di esperienza nel software gestionale.

> Zero complessita` superflua. Crescita concentrica. Coerenza operativa.

---

{% include-markdown "signature-core.md" %}
