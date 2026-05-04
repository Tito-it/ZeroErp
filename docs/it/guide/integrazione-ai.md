# Guida Tecnica — Integrazione AI

> **Destinatari:** sviluppatori backend, frontend, analisti funzionali
>
> **Prerequisiti:** [Guida Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni), [API](/dev/api)
>
> **Stato:** Implementato — Anello 4 (interazione)
>
> **Riferimenti sorgente:**
> `backend/apps/ai_assistant/` —
> `frontend/src/core/components/AiAssistantDrawer.vue` —
> `frontend/src/core/composables/useAiAssistant.js` —
> `docs/it/ai/ai-context.md`
>
> **Piano di sviluppo:**
> [integrazione-ai-sviluppo.md](/dev/work-done/integrazione-ai-sviluppo) (v1, completato) —
> [integrazione-ai-sviluppo-v2.md](/dev/work-in-progress/integrazione-ai-sviluppo-v2) (evoluzione)

---

## Nota per gli sviluppatori

L'assistente AI e' un Anello 4: consuma le API degli anelli interni senza che questi lo conoscano. Tuttavia, ogni volta che si aggiunge o modifica un endpoint REST nei domini esistenti (pratiche, anagrafiche, vendite, ecc.), e' opportuno verificare se:

- **Esiste un tool AI che wrappa quell'endpoint** — se si', aggiornare il tool per riflettere i nuovi campi o parametri
- **Il nuovo endpoint espone dati utili all'operatore** — valutare se creare un nuovo tool (un file, una classe, una registrazione)
- **Gli stati o le transizioni sono cambiati** — aggiornare `docs/it/ai/ai-context.md` che alimenta il system prompt
- **I permessi dell'area funzionale sono cambiati** — il filtro tool usa `PermissionResolver`, nessuna azione necessaria se i permessi sono gestiti centralmente

Non e' obbligatorio — l'ERP funziona identicamente senza AI. Ma un tool non aggiornato restituisce dati incompleti, e un contesto statico non allineato produce risposte imprecise.

---

## 1. Filosofia

ZeroERP ha il suo cuore nel database: logica di business in PostgreSQL, integrita' transazionale garantita, audit trail immutabile. L'integrazione AI non tocca questo cuore.

Si posiziona come **strato di interazione intelligente** sopra le API esistenti: interpreta il linguaggio naturale dell'operatore, seleziona gli strumenti giusti, chiama le API reali, restituisce una risposta contestuale.

```
┌─────────────────────────────────────┐
│      Operatore (linguaggio nat.)    │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         Layer AI  (LLM)            │
│  - comprende l'intento              │
│  - seleziona gli strumenti          │
│  - formula la risposta finale       │
└────────────────┬────────────────────┘
                 │ chiama
┌────────────────▼────────────────────┐
│      API Django REST Framework      │
│  (le stesse usate dal frontend Vue) │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   PostgreSQL  — fonte di verita'    │
└─────────────────────────────────────┘
```

L'AI non ha percorsi privilegiati. Non scrive mai direttamente nel database. Non bypassa validazioni ne' trigger. Chiama i service e i repository esattamente come fa il frontend Vue.

---

## 2. Posizionamento nel modello concentrico

L'integrazione AI e' un **Anello 4 — Interazione**:

- **Dipende** da tutti gli anelli interni (0-3) tramite le loro API
- **Nessun anello interno** lo conosce o dipende da lui
- **Disattivabile** con `AI_ENABLED=false` senza effetti sul sistema
- **Le tabelle** di logging sono in `dbops` (Anello 0, infrastruttura operativa)

Questa collocazione garantisce che l'ERP funziona identicamente con o senza AI. L'assistente e' un'aggiunta, non una dipendenza.

---

## 3. Scelte architetturali

### 3.1 Stesse API del frontend

L'AI usa gli stessi service e repository usati dalle view Django. Non esistono endpoint "per l'AI" ne' query SQL dedicate. Questo significa:

- Le validazioni sono le stesse
- I trigger DB si attivano normalmente
- I permessi utente si applicano allo stesso modo
- L'audit trail registra le operazioni identicamente

Se l'AI ha bisogno di dati che le API non espongono, si arricchisce l'API del dominio — non si crea un percorso alternativo.

### 3.2 Function calling (tool use)

Il meccanismo tecnico e' il **function calling** dell'API Anthropic: al modello viene fornito un catalogo di "strumenti" disponibili. Invece di rispondere in prosa, il modello risponde con una chiamata strutturata allo strumento piu' appropriato.

Il flusso di una richiesta:

1. L'operatore scrive nel widget AI
2. Il testo viene inviato all'endpoint Django `POST /api/v1/ai-assistant/query/`
3. Django costruisce il system prompt e lo invia al provider AI con il catalogo strumenti
4. Il provider risponde con una o piu' `tool_call`
5. Django esegue le chiamate ai service interni corrispondenti
6. I risultati vengono restituiti al provider come `tool_result`
7. Il provider formula la risposta finale in linguaggio naturale
8. La risposta viene mostrata all'operatore nel widget

### 3.3 Astrazione provider

L'endpoint non chiama direttamente un vendor specifico. Un'interfaccia astratta (`AIProvider`) definisce il contratto, e una factory istanzia il provider configurato:

- **Anthropic** — provider principale (Claude)
- **Mistral** — opzione EU per residenza dati GDPR
- **Mock** — per test CI e sviluppo locale senza API esterna

Il provider e' configurabile via variabile d'ambiente `AI_PROVIDER`. In questo modo:

- Le PMI usano API esterna (Anthropic o Mistral), semplice e immediata
- Le grandi aziende possono usare modelli self-hosted, zero dati fuori perimetro
- Il cliente sceglie dove girano i suoi dati

### 3.4 Registro strumenti con filtro permessi

Il catalogo degli strumenti AI non e' un elenco statico inviato all'LLM. Viene filtrato ad ogni richiesta in base a:

1. **Blacklist installazione** — parametro `AI_DISABLED_TOOLS` in `config.parameters`, per disabilitare tool specifici per installazione senza toccare codice
2. **Permessi area funzionale** — usa `PermissionResolver` (Anello 0), lo stesso componente di `ZeroERPPermission`. Se l'operatore non ha accesso all'area `pratiche`, il tool `cerca_pratiche` non viene nemmeno inviato all'LLM
3. **Livello accesso** — i tool in scrittura richiedono `TUTTO`; un operatore con `LETTURA` non li vede

Questo garantisce che l'LLM non puo' mai chiamare un'operazione per cui l'utente non ha permesso — perche' lo strumento non esiste nel suo catalogo.

### 3.5 Conferma operazioni in scrittura

Le operazioni che modificano dati (creazione pratica, cambio stato, aggiunta nota) seguono un protocollo a due step:

1. **Preview** — il tool valida i parametri e restituisce un sommario dell'operazione senza eseguirla. Il widget mostra i bottoni Conferma/Annulla.
2. **Esecuzione** — solo dopo conferma esplicita dell'operatore, il tool esegue l'operazione reale chiamando il service di dominio.

Se l'operatore non conferma entro 5 minuti, la conferma pendente viene scartata automaticamente.

### 3.6 Contesto statico documentale

Il system prompt inviato all'LLM include un contesto statico (`docs/it/ai/ai-context.md`) con il vocabolario di dominio, gli stati e le transizioni, la struttura anagrafica e le regole operative fondamentali di ZeroERP.

Questo file e' scritto **per l'LLM**, non per l'operatore umano. Non contiene mai dati dal database — solo definizioni e regole. I dati reali arrivano come `tool_result` e sono trattati dall'LLM come dati, non come istruzioni (protezione prompt injection).

### 3.7 Nessuna tabella di configurazione tool

I tool sono oggetti Python con handler — una tabella DB puo' solo disabilitare, non abilitare tool che non esistono nel codice. La disabilitazione per installazione usa `config.parameters` (chiave `AI_DISABLED_TOOLS`), coerente con il pattern configurazione gia' consolidato in ZeroERP.

---

## 4. Sicurezza

### 4.1 Autorizzazioni

L'endpoint `/api/v1/ai-assistant/query/` e' soggetto alle stesse autorizzazioni JWT del resto delle API. L'LLM opera con i permessi dell'operatore autenticato: se un operatore non puo' vedere le pratiche, l'AI non gliele mostrera'.

### 4.2 Dati sacri

I dati restituiti dai tool sono trattati come **sacri** dal system prompt: l'LLM ha istruzione tassativa di copiarli esattamente (codici fiscali, partite IVA, codici pratica, date, importi) senza modificarli o inventarli. Un prefisso nel tool_result rinforza questa regola.

### 4.3 Prompt injection

Il testo proveniente dal database (nomi clienti, note libere, descrizioni) non viene mai inserito nel prompt di sistema. Arriva come `tool_result` — dato, non istruzione. Il frontend applica un ulteriore filtro (`cleanResponse`) per rimuovere eventuali residui tecnici dalla risposta.

### 4.4 Dominio chiuso

L'assistente e' istruito a rispondere **solo** a domande relative a ZeroERP. Richieste fuori dominio (meteo, ricette, programmazione) ricevono una risposta standard che reindirizza verso le funzionalita' del sistema.

### 4.5 Audit trail

Ogni interazione AI viene loggata in `dbops.ai_query_log` con: input utente, strumenti chiamati con parametri, risposta, provider, modello, token consumati, durata. Il `request_id` correla il log AI con il `request_log` HTTP. Le operazioni confermate sono marcate con flag `confirmed: true`.

---

## 5. Interfaccia utente

L'assistente AI si presenta come un **widget flottante** ancorato in basso a destra dello schermo:

- **Non modale** — l'operatore continua a lavorare normalmente con il widget aperto
- **Minimizzabile** — si riduce alla barra header con un click
- **Shortcut** — `Ctrl+.` per aprire/chiudere rapidamente
- **Conversazionale** — mantiene il contesto intra-sessione (TTL 15 minuti)
- **Tema coerente** — sfondo scuro, bordi e colori allineati al tema ZeroERP
- **Responsive** — full-width su mobile

L'icona AI nella topbar appare solo se `AI_ENABLED=true` (verifica via `GET /api/v1/ai-assistant/status/` al mount).

Le risposte includono **azioni di navigazione** cliccabili che portano l'operatore direttamente alla lista del dominio con il filtro search pre-impostato.

---

## 6. Catalogo strumenti

### 6.1 Lettura

| Strumento | Dominio | Descrizione |
|---|---|---|
| `cerca_pratiche` | pratiche | Ricerca pratiche per stato, cliente, scadenza |
| `dettaglio_pratica` | pratiche | Dati completi di una pratica |
| `cerca_flussi_pratica` | pratiche | Flussi operativi di una pratica |
| `cerca_soggetti` | anagrafiche | Ricerca soggetti con ruoli (cliente, fornitore) |
| `dettaglio_soggetto` | anagrafiche | Dati completi, contatti, indirizzi, ruoli |
| `cerca_operatori` | amm_software | Ricerca operatori per nome, reparto, ruolo |
| `cerca_billing_account` | anagrafiche | Ricerca clienti (billing account) per ragione sociale, codice fiscale, partita IVA |
| `cerca_articoli` | catalogo | Ricerca articoli del catalogo per codice o descrizione |
| `cerca_contratti` | vendite | Ricerca contratti commerciali per stato, utility, ambito, cliente, scadenza |
| `dettaglio_contratto` | vendite | Dati completi di un contratto: testata, utility 1:1, righe con prezzi |
| `cerca_preventivi` | vendite | Ricerca preventivi per stato (DRAFT/EMESSO/ACCETTATO/...), cliente, utility, periodo |
| `dettaglio_preventivo` | vendite | Dati completi di un preventivo: testata, totali, validita', capabilities, count righe |
| `cerca_promo_articoli` | vendite | Ricerca promo articolo per articolo, tipo variazione (PERCENTUALE/VALORE_FISSO/PREZZO_FISSO), validita' |
| `cerca_listini` | vendite | Ricerca listini di pricing per utility, tipologia, attivo |
| `cerca_documenti_generati` | documenti | Lista versioni PDF archiviate per un record sorgente (oggi: PREVENTIVO; estendibile a CONTRATTO/ORDINE) |

### 6.2 Scrittura (con conferma)

| Strumento | Dominio | Descrizione |
|---|---|---|
| `crea_pratica` | pratiche | Crea nuova pratica con tipo prestazione e priorita' |
| `cambia_stato_pratica` | pratiche | Attiva, sospendi, chiudi o annulla una pratica |
| `aggiungi_nota_pratica` | pratiche | Aggiunge nota con tipo (generale, interna, tecnica) |

Tutti i tool in scrittura richiedono livello accesso `TUTTO` e conferma esplicita dell'operatore.

### 6.3 Aggiungere un nuovo tool

Per aggiungere uno strumento:

1. Creare un file in `backend/apps/ai_assistant/tools/` con una classe che estende `AITool`
2. Definire `name`, `description`, `input_schema`, `required_area`, `required_level`
3. Implementare `execute()` che chiama il service/repository esistente
4. Per tool in scrittura, impostare `requires_confirmation=True` e implementare `preview()`
5. Registrare nella funzione `populate_registry()` in `tool_registry.py`

I metodi helper `simplify_results()` e `safe_page_size()` nella classe base eliminano il codice ripetitivo.

---

## 7. Configurazione

Tutte le configurazioni sono via variabili d'ambiente:

| Variabile | Default | Descrizione |
|---|---|---|
| `AI_ENABLED` | `0` | Feature flag globale. Se `0`, l'app non viene caricata |
| `AI_PROVIDER` | `mock` | Provider: `anthropic`, `mistral`, `mock` |
| `AI_API_KEY` | — | Chiave API del provider (mai in codice) |
| `AI_MODEL` | `claude-sonnet-4-20250514` | Modello LLM da usare |
| `AI_MAX_TOKENS` | `4096` | Limite token risposta |
| `AI_CONVERSATION_TTL` | `900` | TTL conversazione in secondi (15 min) |
| `AI_CONTEXT_FILE` | `docs/it/ai/ai-context.md` | Contesto statico per system prompt |

La disabilitazione di tool specifici avviene via `config.parameters` con chiave `AI_DISABLED_TOOLS` (lista separata da virgola).

---

## 8. Cosa l'AI non fa mai

Queste garanzie sono esplicite nel system prompt e nell'architettura:

- **Non scrive direttamente nel database** — ogni operazione passa dai service con le relative validazioni
- **Non bypassa trigger ne' funzioni PostgreSQL** — la logica di business rimane nel DB
- **Non e' la fonte di verita'** — in caso di discrepanza tra la risposta AI e i dati a schermo, i dati vincono
- **Non esegue operazioni irreversibili senza conferma** — cancellazioni, chiusure, cambi stato richiedono sempre il secondo step
- **Non ha memoria tra sessioni** — ogni conversazione riparte da zero (il contesto viene dalle API, non dall'LLM)
- **Non risponde a domande fuori dominio** — e' un assistente ZeroERP, non un assistente generico

---

## 9. Evoluzione prevista

Le attivita' di evoluzione sono tracciate in [integrazione-ai-sviluppo-v2.md](/dev/work-in-progress/integrazione-ai-sviluppo-v2):

- **RAG con pgvector** — ricerca semantica nella documentazione operativa (quando il contesto statico non basta)
- **Tool estensioni** — indirizzi, contatti, note, fatture (incrementali con le API di dominio)
- **Rendering arricchito** — mini-tabelle e card nel widget (dopo feedback operatori)
- **Pre-compilazione form** — l'AI apre un drawer con campi pre-compilati (da validare UX)

---

*Guida tecnica — Integrazione AI in ZeroERP (31 marzo 2026)*
