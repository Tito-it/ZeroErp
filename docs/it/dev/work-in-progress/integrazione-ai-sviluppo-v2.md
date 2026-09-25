# Piano di Sviluppo v2 — Integrazione AI in ZeroERP (Evoluzione)

**Stato:** WIP
**Data:** 2026-03-31 · **riletto sul codice il 2026-09-25**
**Autore:** Michele Carlo / Claude Code
**Prerequisito:** [integrazione-ai-sviluppo.md](../work-done/integrazione-ai-sviluppo.md) (v1 completato)

---

## Contesto

Questo documento raccoglie le attività di evoluzione dell'assistente AI rimaste
fuori dalla v1. Com'è fatto oggi l'assistente (architettura, sicurezza, catalogo
dei tool, configurazione) lo dice la
[guida integrazione AI](../../guide/integrazione-ai.md): qui non si ripete.

Due cantieri successivi hanno cambiato le regole con cui si aggiunge un tool:

* ✅ **Permessi di un tool = permessi del suo endpoint gemello** (2026-09-24,
  [brief-db-area-funzionale-assistente-ai.md](brief-db-area-funzionale-assistente-ai.md)
  §5.2). Un tool non dichiara più area, livello o azione: dichiara l'endpoint
  della UI che fa la stessa cosa (`endpoint=EndpointGemello(view, metodo)`), e
  il permesso si deriva da lì. Un tool **senza** gemello è un'eccezione da
  decidere e scrivere per nome in `_SENZA_GEMELLO`
  (`test_tool_endpoint_gemello.py`).
* ✅ **Area `ai_assistant` a catalogo** (2026-09-25, stesso brief §4): l'uso
  dell'assistente si concede agli operatori dal pannello dei profili. Il
  significato dei tre livelli sull'area (§5.3 di quel brief) è ancora da fare
  lato backend.

---

## Fase 2.5b — RAG con pgvector (ricerca documentazione)

> Obiettivo: ricerca semantica nella documentazione ZeroERP. L'AI risponde a
> domande sulle procedure con frammenti reali dai docs.

Al 2026-09-25 non c'è niente: le cartelle `indexing/` e `management/commands/`
sono vuote. Esiste solo il segnaposto `generate_embedding()` nell'interfaccia
dei provider (`providers/base.py`).

### DB

* [ ] Migrazione Liquibase: abilitazione estensione `pgvector`
* [ ] Migrazione Liquibase: tabella `doc_embeddings` con colonne, indice, unique constraint
* [ ] Decisione dello schema che ospita la tabella (`dbops` o uno schema dedicato).
  ⚠️ `ai_assistant` oggi è la chiave di un'**area funzionale**, non uno schema:
  le due cose non vanno confuse

### Backend

* [ ] Aggiungere dipendenza `pgvector` a `requirements.in`
* [ ] Decisione provider embedding: stesso AI provider, Voyage AI, o sentence-transformers locale
* [ ] Implementazione `generate_embedding()` nel provider scelto
* [ ] `indexing/chunker.py`: splitting markdown per heading + fallback per paragrafi
* [ ] `indexing/embedder.py`: generazione embedding via provider con gestione batch
* [ ] `indexing/doc_repository.py`: accesso tabella `doc_embeddings` (upsert, delete, query coseno)
* [ ] `management/commands/index_docs.py`: command con `--path`, `--exclude`, `--rebuild`, `--dry-run`
* [ ] `management/commands/index_docs.py`: logica hash SHA-256 per skip chunk invariati
* [ ] `management/commands/index_docs.py`: pulizia chunk orfani (file rimossi)
* [ ] `management/commands/index_docs.py`: report stdout (nuovi, aggiornati, invariati, rimossi)
* [ ] `tools/doc_tools.py`: tool `cerca_documentazione` con handler query pgvector + filtro soglia
* [ ] Registrazione del tool. ⚠️ Non ha un endpoint gemello nella UI: va
  deciso chi lo può usare e scritto come eccezione in `_SENZA_GEMELLO`, con il
  motivo accanto

### Test

* [ ] Unit test `chunker`: splitting per heading, fallback paragrafi, limiti token
* [ ] Unit test `index_docs`: chunking, hashing, skip invariati (filesystem mock)
* [ ] Unit test handler `cerca_documentazione`: formato output, filtro soglia (repository mock)
* [ ] Unit test embedding: vettore dimensione attesa (provider mock)
* [ ] Test integrazione locale: indicizzazione reale + query reale su docs di test

### Quando farla

Quando gli operatori chiedono regolarmente "come funziona X?" e il contesto
statico non basta. Non prima.

---

## Tool estensioni — Nuovi strumenti

> Obiettivo: ampliare il catalogo tool con dati più dettagliati. Al 2026-09-25
> nessuno dei tool qui sotto esiste.

Ogni tool nuovo si scrive **sul suo endpoint gemello**: prima c'è l'endpoint
della UI, poi il tool che lo rispecchia. Chi lo può usare non si dichiara nel
tool.

### Anagrafiche

* [ ] `cerca_indirizzi_soggetto` — gemello: GET indirizzi soggetto
* [ ] `cerca_contatti_soggetto` — gemello: GET contatti soggetto

### Pratiche

* [ ] `cerca_note_pratica` — gemello: GET note pratica
* [ ] `crea_flusso_pratica` — tool di scrittura con conferma, gemello: POST flusso

### Vendite

* [ ] `cerca_fatture` — gemello: lista fatture
* [ ] `cerca_lotti` — gemello: lista lotti fatturazione

### Analisi (opzionali)

* [ ] `statistiche_pratiche` — query aggregata per stato/priorità/periodo
* [ ] `pratiche_in_scadenza` — filtro scadenza prossimi N giorni

⚠️ Le due voci di analisi non hanno oggi un endpoint gemello: o nasce prima
l'endpoint, o diventano eccezioni dichiarate in `_SENZA_GEMELLO`.

### Quando farli

Incrementalmente, quando l'endpoint gemello del dominio è stabile e testato.

---

## Miglioramenti frontend widget

> Obiettivo: rendering più ricco e interazioni avanzate. Al 2026-09-25 nessuna
> voce è fatta.

### Rendering

* ✅ **Regola di sicurezza fissata il 2026-06-26, prima di scrivere il codice.**
  Il rendering arricchito resta su **testo strutturato e azioni interne** (rotte
  Vue). **Mai** immagini o risorse esterne caricate a partire dall'output del
  modello: sarebbe una via di **esfiltrazione**. Vedi
  [analisi-sicurezza-aggiornata.md](../work-done/analisi-sicurezza-aggiornata.md)
  §3 e guida AI §4.5.

* [ ] Rendering risultati lista come mini-tabella nel widget (righe cliccabili)
* [ ] Rendering dettaglio singolo come card informativa
* [ ] Troncamento risultati > 5 con link "e altri N risultati" → lista dominio con filtri

### Interazioni avanzate

* [ ] Azione `prefill`: pre-compilazione form via aiAssistantStore + router.push()
* [ ] Coordinamento aiAssistantStore ↔ drawer di dominio per dati pre-fill

### Quando farli

Dopo le prime prove con operatori reali: le priorità emergono dall'uso.

---

## Durabilità conversazioni (multi-worker)

> Emerso durante l'hardening sicurezza 2026-06-26 (vedi
> [analisi-sicurezza-aggiornata.md](../work-done/analisi-sicurezza-aggiornata.md)).

* ✅ Le **conferme pendenti** sono in `django.core.cache` (Redis in produzione),
  con la chiave che include conversazione e proprietario.
* [ ] Le **conversazioni** sono ancora un dict **in memoria per processo**
  (`_conversations` in `ai_assistant_service.py`): con gunicorn multi-worker un
  follow-up che colpisce un altro worker **non** ritrova il contesto. Vanno
  portate allo stesso meccanismo delle conferme (cache con TTL
  `AI_CONVERSATION_TTL`, chiave per conversazione + proprietario), mantenendo
  l'isolamento di sicurezza che c'è già. Degrada la continuità multi-turno, non
  la sicurezza, ma serve prima della produzione.

---

## Audit e tracciabilità

* ✅ Le interazioni con l'assistente sono registrate in `dbops.ai_query_log`
  (input, tool invocati, risposta, token, durata, provider), append-only con
  retention.
* [ ] Campo `ai_initiated` nelle tabelle `storico.*`, per marcare le **scritture**
  originate dall'AI. Rilevante anche per
  [analisi-diagnostica-produzione-senza-accesso-db.md](../work-done/analisi-diagnostica-produzione-senza-accesso-db.md)
  §7.3. Valutare dopo le prime settimane di uso.

---

## Test con provider reale

> Richiedono `AI_PROVIDER=anthropic` e credito API attivo.

⚠️ **Da verificare per primo: thinking blocks e storia della conversazione.**
Il modello di default è `claude-opus-5` (`AI_MODEL`), dove il thinking è attivo
per default. `_run_tool_loop` **ricostruisce** il turno assistant dai campi
normalizzati (`{"type": "text"}` + `{"type": "tool_use"}`), e `ProviderResponse`
scarta ogni content block diverso da quei due: gli eventuali blocchi `thinking`
**non vengono ri-inviati** nella storia. Con thinking + tool use l'API può
chiedere che siano riproposti invariati nel turno che contiene i `tool_use`.
Con `AI_PROVIDER=mock` non si vede: **il primo smoke con provider reale deve
fare un giro multi-tool**. Se l'API rifiuta, la correzione è propagare i blocchi
grezzi invece di ricostruirli.

* ✅ Default del modello e `AI_MAX_TOKENS` (16000) allineati a Opus 5
* [ ] Smoke test: query che esercitano ciascun tool
* [ ] Smoke test: flusso completo preview → conferma → esecuzione
* [ ] Test multi-tool: query che richiede 2-3 tool in sequenza
* [ ] Test wizard: conversazione multi-turno con estrazione parametri

---

## Priorità

⛔ **Prima di qualunque installazione con un provider esterno** c'è una
decisione che non è un'evoluzione: il perimetro dei dati inviati al fornitore.
Sta nella guida AI §9 (requisito R7 di
[analisi-diagnostica-produzione-senza-accesso-db.md](../work-done/analisi-diagnostica-produzione-senza-accesso-db.md)).

| Priorità | Attività | Perché |
|---|---|---|
| Alta | Livelli dell'area `ai_assistant` (brief-db-area-funzionale-assistente-ai §5.3) | Senza, `LETTURA` sull'assistente non ha un significato |
| Alta | Test con provider reale, a partire dai thinking blocks | Il tool loop può rompersi al primo giro multi-tool reale, e con il mock non si vede |
| Alta | Conversazioni in cache | Con più worker il multi-turno si perde |
| Media | Tool estensioni | Incrementali, sul gemello del dominio |
| Media | Rendering arricchito widget | Dopo le prime prove con gli operatori |
| Media | Audit `ai_initiated` | Dopo le prime settimane d'uso |
| Bassa | RAG con pgvector | Quando il contesto statico non basta |
| Bassa | Prefill form da AI | Dopo validazione UX con operatori |

---

## Registro

| Data | Cosa |
|---|---|
| 2026-03-31 | Documento scritto alla chiusura della v1 |
| 2026-06-26 | Regola di sicurezza sul rendering; conferme pendenti in cache; follow-up conversazioni |
| 2026-07-26 | Nota sui thinking blocks dopo il passaggio a Opus 5 |
| 2026-09-25 | Riletto sul codice: tolti i numeri della v1 e la ricetta vecchia per aggiungere un tool (area/livello dichiarati), riscritti tool e RAG sulla regola del gemello, segnate ✅ le voci fatte, priorità riordinate |

---

*Documento WIP — evoluzione dell'integrazione AI v1 completata.*
