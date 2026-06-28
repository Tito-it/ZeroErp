# Integrazione AI in ZeroERP

**Stato:** WIP  
**Data:** 2026-03-30  
**Autore:** Michele Carlo  

---

## Visione generale

ZeroERP ha il suo cuore nel database: logica di business in PostgreSQL, integrità transazionale garantita, audit trail immutabile, workflow eseguiti — non simulati. Questo è esattamente ciò che un modello AI non può essere, e non deve essere.

L'integrazione AI non tocca questo cuore. Si posiziona come **strato di interazione intelligente** sopra le API esistenti: interpreta il linguaggio naturale dell'utente, seleziona gli strumenti giusti, chiama le API reali, restituisce una risposta contestuale.

```
┌─────────────────────────────────────┐
│         Utente (linguaggio nat.)    │
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
│   PostgreSQL  — fonte di verità     │
│  trigger · funzioni · audit trail   │
└─────────────────────────────────────┘
```

L'AI non ha percorsi privilegiati. Non scrive mai direttamente nel database. Non bypassa validazioni né trigger. Chiama le API esattamente come fa il frontend Vue.

---

## Meccanismo tecnico: Function Calling

L'API Anthropic supporta il **tool use** (function calling): al modello viene fornito un catalogo di "strumenti" disponibili. Invece di rispondere in prosa, il modello risponde con una chiamata strutturata allo strumento più appropriato.

### Flusso di una richiesta

```
1. Utente scrive nel drawer di ricerca universale
2. Il testo viene inviato all'endpoint Django /api/ai/query/
3. Django costruisce il messaggio e lo invia all'API Anthropic
   includendo il catalogo degli strumenti disponibili
4. L'LLM risponde con una o più tool_call
5. Django esegue le chiamate alle API interne corrispondenti
6. I risultati vengono restituiti all'LLM come tool_result
7. L'LLM formula la risposta finale in linguaggio naturale
8. La risposta viene mostrata all'utente nel drawer
```

### Esempio di definizione strumento (Python)

```python
tools = [
    {
        "name": "cerca_pratiche",
        "description": (
            "Cerca pratiche nel sistema. Usare quando l'utente vuole trovare "
            "pratiche per cliente, stato, tipo, scadenza o operatore assegnato."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente": {
                    "type": "string",
                    "description": "Nome o parte del nome del cliente"
                },
                "stato": {
                    "type": "string",
                    "enum": ["aperta", "sospesa", "chiusa", "annullata"],
                    "description": "Stato corrente della pratica"
                },
                "tipo_prestazione": {
                    "type": "string",
                    "description": "Codice o nome del tipo di prestazione"
                },
                "scadenza_da": {
                    "type": "string",
                    "format": "date",
                    "description": "Data scadenza da (YYYY-MM-DD)"
                },
                "scadenza_a": {
                    "type": "string",
                    "format": "date",
                    "description": "Data scadenza a (YYYY-MM-DD)"
                },
                "operatore": {
                    "type": "string",
                    "description": "Username o nome dell'operatore assegnato"
                }
            },
            "required": []
        }
    },
    {
        "name": "cerca_fornitori",
        "description": (
            "Cerca fornitori in anagrafica. Usare per trovare fornitori per nome, "
            "partita IVA, stato documenti di compliance, o regime fiscale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ragione_sociale": {"type": "string"},
                "partita_iva": {"type": "string"},
                "documenti_scaduti": {
                    "type": "boolean",
                    "description": "Se true, restituisce solo fornitori con documenti scaduti o mancanti"
                },
                "regime_fiscale": {"type": "string"}
            },
            "required": []
        }
    },
    {
        "name": "cerca_fatture",
        "description": (
            "Cerca fatture passive o attive. Usare per trovare fatture per fornitore, "
            "cliente, stato SDI, importo o periodo di emissione."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "controparte": {"type": "string"},
                "stato_sdi": {
                    "type": "string",
                    "enum": ["inviata", "consegnata", "rifiutata", "in_attesa"]
                },
                "importo_min": {"type": "number"},
                "importo_max": {"type": "number"},
                "data_emissione_da": {"type": "string", "format": "date"},
                "data_emissione_a": {"type": "string", "format": "date"}
            },
            "required": []
        }
    }
]
```

---

## Esempi d'uso concreti

### 1. Query in linguaggio naturale

L'utente non sa navigare fino alla schermata pratiche, oppure vuole combinare filtri che normalmente richiederebbero più passaggi.

**Input utente:**
> "mostrami le pratiche aperte di Acea scadute questa settimana"

**L'LLM chiama:**
```json
{
  "name": "cerca_pratiche",
  "input": {
    "cliente": "Acea",
    "stato": "aperta",
    "scadenza_da": "2026-03-30",
    "scadenza_a": "2026-04-05"
  }
}
```

**Risposta all'utente:**
> Ho trovato 4 pratiche aperte di Acea in scadenza questa settimana. La più urgente è la pratica #2341 (Allaccio gas — Via Roma 12) scaduta ieri. Vuoi aprirla direttamente?

---

**Input utente:**
> "fornitori senza DURC valido"

**L'LLM chiama:**
```json
{
  "name": "cerca_fornitori",
  "input": {
    "documenti_scaduti": true
  }
}
```

**Risposta all'utente:**
> 3 fornitori hanno il DURC scaduto o mancante: Edilco Srl (scaduto il 15/03), Manutenzioni Rossi (mai caricato), Impianti Sud Spa (scade domani). Vuoi che ti mostri i dettagli o apra le schede?

---

### 2. Navigazione contestuale

L'utente descrive cosa vuole fare. Il sistema lo porta direttamente lì.

**Input utente:**
> "devo registrare una nuova fattura di Edilco"

**Risposta:**
> Edilco Srl — trovata in anagrafica (P.IVA 01234567890). Attenzione: il DURC risulta scaduto dal 15 marzo. Vuoi comunque procedere con la registrazione della fattura passiva?

Il drawer propone il link diretto al form di inserimento fattura con il fornitore già preselezionato, e un avviso visibile sul DURC.

---

### 3. Assistente operativo guidato

Per operazioni complesse, l'AI guida passo-passo verificando i prerequisiti.

**Input utente:**
> "devo aprire una pratica di allaccio gas per un nuovo cliente"

**Risposta:**
> Per creare una pratica di allaccio gas ho bisogno di alcune informazioni:
> 
> 1. **Cliente** — è già in anagrafica o devo crearlo?  
> 2. **Indirizzo fornitura** — via, comune, CAP  
> 3. **Tipo contatore** — G4, G6, G10...  
> 4. **Operatore assegnato** — o assegno a te automaticamente?
> 
> Dimmi pure in formato libero, ci penso io a strutturare i dati.

L'utente risponde in prosa, l'LLM estrae i campi, pre-compila il form e lo apre già popolato — o chiede esplicitamente solo i dati mancanti.

---

### 4. Rilevamento anomalie

**Input utente:**
> "c'è qualcosa di strano nelle fatture di questo mese?"

L'LLM chiama più strumenti in sequenza:
1. `cerca_fatture` con `data_emissione_da: 2026-03-01` e `data_emissione_a: 2026-03-30`
2. Analizza i risultati cercando outlier (importi fuori dalla norma, fornitori insoliti, fatture duplicate per importo e fornitore)

**Risposta:**
> Ho analizzato 47 fatture di marzo. Segnalo:
> - 2 fatture di importo identico (€ 3.200) dallo stesso fornitore a 3 giorni di distanza — possibile duplicato
> - 1 fattura da un fornitore mai usato prima (Servizi Tecnici Roma Srl) per € 8.400
> - 3 fatture in stato SDI "in_attesa" da più di 10 giorni
> 
> Vuoi che apra i dettagli di uno di questi casi?

---

## Punto di ingresso architetturale: il drawer universale

Il posto più naturale dove innestare questa funzionalità è la **universal search drawer** già prevista nel design di ZeroERP.

Attualmente progettata come ricerca full-text, diventa una **ricerca con intento**:

- L'utente apre il drawer (shortcut globale, es. `Ctrl+K`)
- Scrive in linguaggio libero
- Il drawer mostra risultati classici (entità trovate) **e** suggerimenti d'azione contestuali generati dall'AI

Architetturalmente è un'evoluzione, non una rottura: il drawer esiste, le API esistono. Si aggiunge un endpoint `/api/ai/query/` che fa da orchestratore.

---

## Cosa l'AI non fa mai

Queste garanzie devono essere esplicite nel prompt di sistema inviato all'LLM ad ogni chiamata:

- **Non scrive direttamente nel database** — ogni operazione passa dalle API con le relative validazioni
- **Non bypassa trigger né funzioni PostgreSQL** — la logica di business rimane nel DB
- **Non è la fonte di verità** — in caso di discrepanza tra la risposta AI e i dati a schermo, i dati vincono
- **Non esegue operazioni irreversibili senza conferma esplicita** — cancellazioni, chiusure di pratiche, emissione fatture richiedono sempre un secondo step di conferma dall'utente
- **Non ha memoria tra sessioni** — ogni conversazione riparte da zero (il contesto è fornito dalle API, non dall'LLM)

---

## Considerazioni di sicurezza

> **Principio**: la prompt injection **non è eliminabile**; la difesa è il **blast radius**
> (limitare i danni se accade), non il system prompt. Versione estesa e autorevole nella
> [guida AI §4](../../guide/integrazione-ai.md). Sintesi qui sotto.

### Pilastri (le difese vere)
- **Permessi**: il catalogo strumenti è filtrato per area/livello — un'operazione vietata all'utente **non è nemmeno offerta** all'AI (lo strumento non esiste nel suo catalogo).
- **RLS**: le tabelle sensibili (`vendite.fatture`, `vendite.fatturazione_lotti`, ...) filtrano le righe per contesto operatore — un tool di lettura restituisce **solo** ciò che l'utente vedrebbe nella UI.
- **Conferma umana** sulle scritture: preview + confirm, parametri ripresi dallo stato server, permessi **da ri-verificare a execution-time** (vedi [analisi-sicurezza-aggiornata.md](analisi-sicurezza-aggiornata.md) §2).
- **Nessuna esfiltrazione**: il widget mostra solo testo + link interni. Da preservare in v2: **mai** immagini/risorse esterne caricate dall'output AI.

### Igiene (NON difesa principale)
Mettere i dati nel `tool_result` **non** protegge dalla prompt injection: per il modello è lo stesso flusso del system prompt. È igiene contro injection *diretta* e *invenzioni* (CF/PIVA/importi). La protezione vera resta il blast radius (pilastri sopra).

### Audit
Ogni chiamata è loggata in `dbops.ai_query_log` (`request_id` correla con `request_log` HTTP). Oltre alla tracciabilità è il **sistema di rilevamento anomalie**: per le scritture confermate il logging va reso **affidabile** (alert se fallisce), non best-effort.

---

## Stack tecnico suggerito

| Componente                         | Scelta                                                                            |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| LLM                                | Anthropic Claude (API) — `claude-sonnet-4`                                        |
| Integrazione backend               | Endpoint Django `/api/ai/query/`                                                  |
| Autenticazione verso API Anthropic | Chiave API lato server, mai esposta al client                                     |
| Frontend                           | Estensione del drawer universale in Vue 3                                         |
| Logging chiamate AI                | Tabella `ai_query_log` con `request_id`, `user_id`, `input`, `tools_called`, `ts` |

---

## Fasi di implementazione (bozza)

**Fase 1 — Fondamenta**
- Endpoint `/api/ai/query/` con autenticazione JWT
- Catalogo iniziale di 3-5 strumenti (pratiche, fornitori, fatture)
- Integrazione drawer universale in Vue
- Logging base

**Fase 2 — Ampliamento strumenti**
- Aggiungere strumenti per anagrafica clienti, operatori, documenti compliance
- Risposta con link diretti alle entità trovate (navigazione contestuale)

**Fase 3 — Operazioni guidate**
- Strumenti in scrittura (con conferma obbligatoria)
- Assistente per creazione pratiche e registrazione fatture

**Fase 4 — Analisi e anomalie**
- Query multi-strumento in sequenza
- Report anomalie su richiesta

---

---

## Nota finale: GDPR e architettura multi-provider

ZeroERP tratta dati fiscali e aziendali reali: partite IVA, fatture, DURC, dati di fornitori e clienti. Prima di scegliere un provider AI esterno, la domanda da porsi è semplice: **questi dati possono uscire dall'infrastruttura europea?**

La risposta dipende dal cliente. Per questo motivo l'endpoint `/api/ai/query/` va progettato fin dall'inizio con un'**astrazione del provider**, non come chiamata diretta a un vendor specifico:

```python
# settings.py
AI_PROVIDER = env("AI_PROVIDER", default="anthropic")  # anthropic | openai | mistral | local

# services/ai_provider.py
def get_ai_client():
    if settings.AI_PROVIDER == "anthropic":
        return AnthropicClient()
    elif settings.AI_PROVIDER == "mistral":
        return MistralClient()
    elif settings.AI_PROVIDER == "local":
        return OllamaClient(base_url=settings.OLLAMA_URL)  # self-hosted su nodo Proxmox
```

In questo modo:

- **PMI standard** — API esterna (Anthropic, OpenAI, Mistral EU), semplice e immediata
- **Utilities e grandi aziende** — modello self-hosted su infrastruttura propria, zero dati fuori perimetro
- **Il cliente sceglie**, ZeroERP supporta entrambi nativamente

Questa flessibilità è essa stessa un argomento commerciale: *"l'intelligenza artificiale ce l'hai, ma decidi tu dove girano i tuoi dati."* In Italia, con il Garante della Privacy particolarmente attivo, non è un dettaglio da poco.

---

*Un ringraziamento speciale a **Dario Amodei**, CEO di Anthropic — italoamericano, quindi in qualche modo di famiglia — le cui ricerche sulla sicurezza dell'AI e sulla costruzione di modelli affidabili hanno reso possibile immaginare integrazioni come questa anche in contesti enterprise seri come quello delle utilities italiane. Se mai leggesse queste note: ZeroERP è open source, GPL3, fatto da un artigiano del software con 30 anni di AS/400 alle spalle. C'è tutto il rispetto del mondo per chi costruisce le cose per bene. I saluti più cordiali da Michele Carlo, Civitanova Marche.*

---

*Documento WIP — idee e struttura soggette a revisione.*