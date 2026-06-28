# Piano di Sviluppo v2 — Integrazione AI in ZeroERP (Evoluzione)

**Stato:** WIP
**Data:** 2026-03-31
**Autore:** Michele Carlo / Claude Code
**Prerequisito:** [integrazione-ai-sviluppo.md](../work-done/integrazione-ai-sviluppo.md) (v1 completato)

---

## Contesto

La v1 dell'integrazione AI e' completata con:

- 9 tool (6 lettura + 3 scrittura con conferma)
- Widget flottante non modale con conversazione multi-turno
- Contesto statico documentale (`ai-context.md`)
- Multi-tool chaining con timeout 30s
- 61 test unitari, 951 suite completa OK
- Shortcut `Ctrl+.`, tema scuro, responsive

Questo documento raccoglie le attivita' di evoluzione rimandate dalla v1.

---

## Fase 2.5b — RAG con pgvector (ricerca documentazione)

> Obiettivo: ricerca semantica nella documentazione ZeroERP. L'AI risponde a domande sulle procedure con frammenti reali dai docs.

### DB

- [ ] Migrazione Liquibase: abilitazione estensione `pgvector`
- [ ] Migrazione Liquibase: tabella `doc_embeddings` con colonne, indice ivfflat, unique constraint
- [ ] Decisione schema: `ai_assistant` dedicato oppure `dbops`

### Backend

- [ ] Aggiungere dipendenza `pgvector` a `requirements.in`
- [ ] Decisione provider embedding: stesso AI provider, Voyage AI, o sentence-transformers locale
- [ ] Implementazione `generate_embedding()` nel provider scelto
- [ ] `indexing/chunker.py`: splitting markdown per heading + fallback per paragrafi
- [ ] `indexing/embedder.py`: generazione embedding via provider con gestione batch
- [ ] `indexing/doc_repository.py`: accesso tabella `doc_embeddings` (upsert, delete, query coseno)
- [ ] `management/commands/index_docs.py`: command con `--path`, `--exclude`, `--rebuild`, `--dry-run`
- [ ] `management/commands/index_docs.py`: logica hash SHA-256 per skip chunk invariati
- [ ] `management/commands/index_docs.py`: pulizia chunk orfani (file rimossi)
- [ ] `management/commands/index_docs.py`: report stdout (nuovi, aggiornati, invariati, rimossi)
- [ ] `tools/doc_tools.py`: tool `cerca_documentazione` con handler query pgvector + filtro soglia
- [ ] Registrazione tool in `register_tools()` (disponibile a tutti, nessun filtro area)

### Test

- [ ] Unit test `chunker`: splitting per heading, fallback paragrafi, limiti token
- [ ] Unit test `index_docs`: chunking, hashing, skip invariati (filesystem mock)
- [ ] Unit test handler `cerca_documentazione`: formato output, filtro soglia (repository mock)
- [ ] Unit test embedding: vettore dimensione attesa (provider mock)
- [ ] Test integrazione locale: indicizzazione reale + query reale su docs di test

### Quando farla

Quando gli operatori in produzione chiedono regolarmente "come funziona X?" e il contesto statico non basta. Non prima.

---

## Tool estensioni — Nuovi strumenti read-only

> Obiettivo: ampliare il catalogo tool con dati piu' dettagliati.

### Anagrafiche

- [ ] `cerca_indirizzi_soggetto` — handler wrappa GET indirizzi soggetto
- [ ] `cerca_contatti_soggetto` — handler wrappa GET contatti soggetto

### Pratiche

- [ ] `cerca_note_pratica` — handler wrappa GET note pratica
- [ ] `crea_flusso_pratica` — tool scrittura con conferma (wrappa POST flusso)

### Vendite (quando API pronte)

- [ ] `cerca_fatture` — handler wrappa endpoint fatture
- [ ] `cerca_lotti` — handler wrappa endpoint lotti fatturazione

### Analisi (opzionali)

- [ ] `statistiche_pratiche` — query aggregata per stato/priorita'/periodo
- [ ] `pratiche_in_scadenza` — filtro scadenza prossimi N giorni

### Quando farli

Aggiungere incrementalmente quando le API del dominio sono stabili e testate. Ogni tool richiede: file in `tools/`, classe con `_FIELD_MAP`, registrazione in `populate_registry()`.

---

## Miglioramenti frontend widget

> Obiettivo: rendering piu' ricco e interazioni avanzate.

### Rendering

> ⚠️ **Regola di sicurezza (fissata 2026-06-26, prima di scrivere il codice)**: il rendering
> arricchito resta su **testo strutturato e azioni interne** (rotte Vue). **Mai** abilitare
> immagini o risorse esterne caricate a partire dall'output del modello: sarebbe una via di
> **esfiltrazione** (un'injection può costruire un URL-immagine che fa uscire dati riservati
> nell'indirizzo). Così si conserva la proprietà "il widget non ha vie di esfiltrazione".
> Vedi [analisi-sicurezza-aggiornata.md](../work-done/analisi-sicurezza-aggiornata.md) §3 e guida AI §4.5.

- [ ] Rendering risultati lista come mini-tabella nel widget (righe cliccabili)
- [ ] Rendering dettaglio singolo come card informativa
- [ ] Troncamento risultati > 5 con link "e altri N risultati" → lista dominio con filtri

### Interazioni avanzate

- [ ] Azione `prefill`: pre-compilazione form via aiAssistantStore + router.push()
- [ ] Coordinamento aiAssistantStore ↔ drawer di dominio per dati pre-fill

### Quando farli

Dopo test in produzione con operatori reali — le priorita' emergono dall'uso.

---

## Durabilità conversazioni (multi-worker)

> Emerso durante l'hardening sicurezza 2026-06-26 (vedi [analisi-sicurezza-aggiornata.md](../work-done/analisi-sicurezza-aggiornata.md)).

- [ ] Le **conversazioni** AI sono oggi un dict **in-memory per processo** (`_conversations` in `ai_assistant_service.py`): con gunicorn multi-worker un follow-up che colpisce un altro worker **non** ricostruisce il contesto. Le **conferme pendenti** sono già state migrate a `django.core.cache` (Redis); migrare le conversazioni **allo stesso meccanismo** (cache con TTL `AI_CONVERSATION_TTL`, chiave per scope conv+owner, mantenendo l'isolamento sicurezza già presente). Non urgente (degrada la continuità multi-turno, non la sicurezza), ma necessario per coerenza in produzione.

---

## Audit e tracciabilita'

- [ ] Campo `ai_initiated BOOLEAN DEFAULT FALSE` nelle tabelle audit `storico.*` — per marcare operazioni originate dall'AI. Valutare utilita' reale dopo le prime settimane di uso.

---

## Test con provider reale

> Richiedono `AI_PROVIDER=anthropic` e credito API attivo.

- [ ] Smoke test: query che esercitano ciascun tool
- [ ] Smoke test: flusso completo preview → conferma → esecuzione
- [ ] Test multi-tool: query che richiede 2-3 tool in sequenza
- [ ] Test wizard: conversazione multi-turno con estrazione parametri

---

## Priorita' suggerite

| Priorita' | Attivita' | Quando |
|---|---|---|
| Alta | Test con provider reale | Appena credito API disponibile |
| Alta | Tool estensioni (note pratica, contatti) | Sprint successivo |
| Media | Rendering arricchito widget | Dopo feedback operatori |
| Media | Audit `ai_initiated` | Dopo prime settimane produzione |
| Bassa | RAG con pgvector | Quando contesto statico non basta |
| Bassa | Prefill form da AI | Dopo validazione UX con operatori |

---

*Documento WIP — evoluzione dell'integrazione AI v1 completata.*
