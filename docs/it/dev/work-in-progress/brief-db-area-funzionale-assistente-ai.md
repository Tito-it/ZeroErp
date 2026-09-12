# Brief DB — L'area funzionale dell'assistente AI

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-11. **A chi:** team DB.
> **Origine:** `migliorie-generali-BE-FE-da-test-valutazione.md` §3 D5.
> **Decisione di Tid, 2026-09-11:** l'assistente AI **lo devono poter usare anche
> gli operatori**, non solo gli amministratori. È questa risposta che sceglie la
> strada del §3.
>
> **In una riga:** `AIQueryView` dichiara `area_funzionale = "ai_assistant"`, e
> quel codice **non esiste** in `config.aree_funzionali`. La catena dei permessi
> si comporta esattamente come deve — e proprio per questo l'endpoint è
> raggiungibile **solo da un `SUPER_ADMIN`**, e a nessun altro operatore il
> permesso si può concedere: non esiste la riga a cui appenderlo.
>
> ⇒ **Serve una riga di catalogo** (§4). Una sola, e con un precedente già in
> servizio.
>
> ⛔ **Il backend si ferma qui e aspetta**, come da regola: BE/FE solo con
> prerequisiti DB pronti. Ciò che il backend fa appena arriva è al §5.

---

## 1. Il fatto, letto dalla struttura

`backend/apps/ai_assistant/api/views.py:77`

```python
class AIQueryView(DomainAPIView):
    area_funzionale = "ai_assistant"
```

Il catalogo è `config.aree_funzionali`, **tredici righe** (mirror
`80_data/sql/config/aree_funzionali.csv`, changeSet `20260228-17`):
`anagrafiche`, `vendite`, `acquisti`, `catalogo`, `contabilita`, `magazzino`,
`pagamenti`, `storico`, `config`, `core`, `pratiche`, `documenti`, `strumenti`.

⛔ **`ai_assistant` non c'è.**

Letta la catena dalla doc auto-generata (`script.fn_resolve_livello_area`), il
percorso per un'area che il catalogo non nomina è: nessun `user_override_aree`
(il `JOIN` su `config.aree_funzionali` non trova nulla), nessun profilo per la
stessa ragione ⇒ **passo 5, `RETURN 'BLOCCATO'`**.

⚠️ **Non è un buco: è il suo opposto**, ed è ciò che lo rende difficile da
trovare. La catena è fail-closed e fa il suo mestiere. Il difetto è che il 403
che ne esce è **indistinguibile** da «non hai il permesso», mentre la verità è
«il permesso non esiste e nessuno può dartelo». Chi indaga andrà a cercare nei
profili di accesso, e lì non troverà niente da sistemare.

⭐ Fra le nove aree che il backend dichiara nelle sue view, **è l'unica fuori
catalogo**: le altre otto combaciano.

---

## 2. Perché adesso, se la funzione è spenta

Le rotte sono montate solo con `AI_ENABLED=1`, che di default vale `0`: a flag
spento l'app non è nemmeno in `INSTALLED_APPS`.

⛔ **«Oggi non capita mai» è uno degli argomenti che la Regola zero rifiuta per
nome.** Il giorno in cui la funzione si accende, si accende **rotta per tutti
tranne uno** — e in quel momento la diagnosi costa molto più di adesso, perché
il sintomo (un 403) punta nella direzione sbagliata.

⭐ E c'è una seconda ragione, più forte: la riga di catalogo **non cambia niente
finché il flag è spento**. È esattamente il lavoro che conviene fare prima.

---

## 3. La decisione già presa, e quale strada esclude

Le strade erano due, e sono alternative:

| Strada | Cosa comporta |
| --- | --- |
| **Riga a catalogo** ⇐ **scelta** | L'assistente diventa concedibile per area come ogni altro dominio, coi livelli `TUTTO` / `LETTURA` / `BLOCCATO`. Passa dal team DB |
| `AdminAPIView` | Zero passaggi dal DB, ma l'assistente resta riservato a `SUPER_ADMIN` **per sempre**, salvo un cambio successivo |

⇒ Tid ha scelto **anche gli operatori**, quindi serve la riga. La seconda strada
è qui perché un brief che non dice cosa è stato escluso lascia credere che non ci
fosse altro.

---

## 4. Cosa si chiede — una riga

Nel mirror `80_data/sql/config/aree_funzionali.csv`:

```csv
14,ai_assistant,ai_assistant,Assistente AI,ai_assistant,t,140,{},...
```

| Colonna | Valore proposto | Perché |
| --- | --- | --- |
| `id` | **14** | primo libero: gli id in uso arrivano a 13 |
| `codice` · `codice_interno` | `ai_assistant` | ⛔ **deve combaciare con la stringa nella view**, che è il valore su cui `fn_resolve_livello_area` fa il `JOIN`. Non è un'etichetta: è la chiave |
| `descrizione` | `Assistente AI` | è ciò che l'amministratore legge nel pannello dei profili |
| `schema_db` | `ai_assistant` | vedi §4.1 — **non** esiste uno schema con questo nome, ed è già il caso di altre due righe |
| `attivo` | `t` | |
| `ordinamento` | **140** | dopo `strumenti` (130), che è l'ultima |

### 4.1 ⭐ `schema_db` senza uno schema: non è un'eccezione, è la terza volta

La colonna è `NOT NULL` e `UNIQUE`, e il `COMMENT` della tabella dice:

> *«Ogni area corrisponde a uno schema DB; il mapping area→schema è automatico
> (Django risolve l'area dal `db_table` del model).»*

⛔ **Quella frase è già falsa per due righe su tredici.** Verificato il
2026-09-11 con un `LEFT JOIN` su `pg_namespace`:

| Area | `schema_db` | Lo schema esiste? |
| --- | --- | --- |
| `core` | `core` | ⛔ **no** |
| `strumenti` | `strumenti` | ⛔ **no** |
| le altre undici | — | ✓ sì |

`strumenti` è il precedente più vicino e il più recente (2026-07-21, area creata
per la gestione delle code di lavoro): un'area funzionale che nomina un
**dominio applicativo**, non uno schema fisico.

⇒ `ai_assistant` sarebbe la **terza** riga della stessa specie, non un caso
nuovo. Non si chiede un'eccezione: si chiede la ripetizione di una forma già in
servizio.

⚠️ **Richiesta accessoria, e la lasciamo decidere a voi**: il `COMMENT` della
tabella descrive una regola che il catalogo non applica più da luglio. Se lo
aggiornate, la frase giusta è *«ogni area ha un `schema_db` che la identifica; per
le aree che non corrispondono a uno schema fisico (`core`, `strumenti`,
`ai_assistant`) il valore è il nome del dominio applicativo»*. ⭐ Non è pedanteria
documentale: è la riga che qualcuno leggerà **prima di rifiutare** la prossima
area senza schema, credendo di applicare un vincolo che non c'è.

### 4.2 Cosa NON si chiede

* ⛔ **Nessuna azione di processo.** I tool dell'assistente dichiarano ciascuno la
  propria azione, speculare al `<action>_permission` dell'endpoint di dominio
  corrispondente, e quelle azioni **esistono già** — sono le stesse dei domini
  che i tool interrogano. Non serve un vocabolario nuovo.
* ⛔ **Nessun override, nessun profilo seminato.** Chi può usare l'assistente lo
  decide l'amministratore in-app, dopo. La riga di catalogo è la *possibilità* di
  decidere, non la decisione.
* ⛔ **Nessuna policy RLS.** I tool leggono con la connessione dell'utente, quindi
  la RLS che già presidia le tabelle di dominio vale anche per loro.

---

## 5. Cosa fa il backend appena la riga è applicata

1. **Niente nel codice.** `AIQueryView` dichiara già `area_funzionale =
   "ai_assistant"`: la stringa è quella giusta, era il catalogo a non conoscerla.
   ⭐ È la prova che la scelta del §3 è quella che costa meno: l'altra strada
   avrebbe voluto un cambio di base class.
2. **Il presidio**, che oggi non esiste: un test su DB provvisto
   (`richiedi_db_provvisto`) che confronta le `area_funzionale` dichiarate dalle
   view con i `codice` a catalogo, e **fallisce su una dichiarata e non
   catalogata**. ⛔ Senza, la prossima area nuova ripete questo difetto identico
   e nessuno se ne accorge — che è esattamente come è nato questo.
   ⚠️ Il test deriva l'elenco **dalle view**, non da una lista scritta a mano:
   una terza sede dello stesso fatto è quella che nessuno aggiorna.
3. **Registrare la chiusura** in `api.md` §Endpoint attivi, dove oggi l'app è
   nominata **con questo difetto scritto accanto**, e in §3 D5 della valutazione.

---

## 6. Come si verifica che è arrivata

```sql
-- deve tornare una riga
SELECT id, codice, schema_db, attivo, ordinamento
  FROM config.aree_funzionali WHERE codice_interno = 'ai_assistant';

-- e il livello per un operatore qualsiasi non deve più essere BLOCCATO
-- per assenza di catalogo (resta BLOCCATO se nessuno gli ha dato il permesso,
-- che è il caso normale e corretto)
SELECT script.fn_resolve_livello_area(<auth_user_id>, 'ai_assistant');
```

⚠️ **La seconda query non prova la chiusura da sola**: `BLOCCATO` è la risposta
giusta anche dopo, finché l'amministratore non concede il livello. Ciò che cambia
è che **adesso si può concedere**. La prova vera è la prima query più il pannello
dei profili, dove l'area deve comparire fra quelle assegnabili.

---

## 7. Perimetro e rischio

| | |
| --- | --- |
| **Righe toccate** | 1 (un append al CSV) |
| **Oggetti DDL** | nessuno |
| **Rischio di regressione** | ⭐ **nullo per costruzione**: nessuna riga esistente cambia, e l'unica funzione che legge il catalogo (`fn_resolve_livello_area`) oggi su `ai_assistant` cade sul default. Con la riga, cade sul default **della riga** — che per chi non ha permessi è lo stesso `BLOCCATO` |
| **Effetto a flag spento** | nessuno: le rotte non sono montate |
| **Reversibile** | sì, `attivo = false` |

---

*Brief backend → team DB, 2026-09-11. Perimetro: una riga in
`config.aree_funzionali`. La decisione di merito («anche gli operatori») è di
Tid, stessa data. Lo stato applicativo del difetto è in
`migliorie-generali-BE-FE-da-test-valutazione.md` §3 D5.*
