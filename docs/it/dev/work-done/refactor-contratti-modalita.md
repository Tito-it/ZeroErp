# Refactor contratti — Ripensare la "modalità" pricing

> **Stato**: DECISIONI CHIUSE — pronto per brief DB.
>
> **Scope**: rivedere il modello UX/dominio della scelta "modalità A/B/C" sui
> contratti. Non riguarda i bug puntuali — quelli stanno in
> [`recap-contratti-post-componenti.md`](recap-contratti-post-componenti.md)
> e possono essere fixati prima di o dopo questo refactor.
>
> **Premessa**: l'osservazione di Tid (2026-05-15) — "scegliere la modalità è
> confusionario, l'operatore non dovrebbe scegliere il tipo di pricing" — ha
> aperto una rivalutazione di fondo. Dopo verifica del pattern già adottato nei
> preventivi (cfr. doc preventivi: contesto risolto + azioni di processo +
> parametri soglia + workflow escalation), le decisioni sono state prese e sono
> riportate in §3 e §3-bis. Le sezioni 1–2 e §4–5 restano come analisi e piano
> operativo.

---

## 1. Come funziona oggi end-to-end

### 1.1 Il modello dati

`vendite.contratti` ha (semplificando) 3 campi che determinano la "modalità":

| Campo                       | Tipo                               | NULL? | Significato                                    |
| --------------------------- | ---------------------------------- | ----- | ---------------------------------------------- |
| `listino_id`                | int                                | sì    | Listino di riferimento, se esiste              |
| `tipo_variazione_globale`   | varchar (PERCENTUALE/VALORE_FISSO) | sì    | Tipo della variazione applicata al listino     |
| `valore_variazione_globale` | numeric                            | sì    | Valore della variazione (es. -10 → sconto 10%) |

La combinazione ammessa è (CHECK DB + service guard):

| Combinazione                                | "Modalità" | Intent commerciale                                                         |
| ------------------------------------------- | ---------- | -------------------------------------------------------------------------- |
| `listino_id` NULL, tipo+valore NULL         | C          | "Niente listino di base — tutto negoziato puntualmente con questo cliente" |
| `listino_id` NOT NULL, tipo+valore NULL     | B          | "Parto dal listino X, ma su alcuni articoli applico prezzi miei"           |
| `listino_id` NOT NULL, tipo+valore NOT NULL | A          | "Parto dal listino X e applico uno sconto/maggiorazione globale"           |

Sono **invarianti DB**: trigger `trgfn_contratti_*` enforcano queste combinazioni
e bloccano l'attivazione di una modalità C senza righe complete.

Sotto la testata vivono:

- `contratti_righe` — righe con prezzo override (manuale o automatico per compositi)
- `contratti_righe_componenti` — figli BoM (auto-init quando articolo padre è composito)
- `contratti_utilities` — 1:1 utility (tipo/classe utenza, parametri PDP, ecc.)

### 1.2 Il flusso utente attuale

**Step 1 — Click "Nuovo contratto" su ContrattiSearchTable**

`ContrattoDrawer` si apre in CREATE. Il form ha:

- Sezione "Anagrafica": BA, istanza utility, utility, ambito (COMMODITY/COMMERCIO)
- Sezione "Validità": data, valido_dal, valido_al
- Sezione "Pricing": **SelectButton A/B/C** con default da parameter `VENDITE_CONTRATTO_DEFAULT_MODALITA`
  - Se A: campo listino + campo tipo_variazione + campo valore_variazione
  - Se B: campo listino (no variazione)
  - Se C: nessun campo (le righe verranno dopo)

L'operatore **sceglie la modalità prima di salvare la testata**.

**Step 2 — Save testata**

Crea contratto in stato DRAFT. Numero auto-generato (CNT*). Sostanzialmente
salva la testata e (se valorizzato) il sub-payload utility.

**Step 3 — Click "Righe" sul contratto creato**

Si apre `ContrattoRigheDrawer`. La logica delle righe **diverge per modalità**:

- **A**: la lista righe è una **preview combinata** = righe listino con variazione globale
  applicata; possono esistere righe `contratti_righe` di override per articoli specifici
  (l'operatore può "puntare" un articolo e dare un prezzo diverso). Le righe di pura preview
  sono read-only (origine `DA_LISTINO`); quelle override sono editabili (origine `OVERRIDE`).
- **B**: identico ad A ma senza variazione globale. Listino + override mirati.
- **C**: nessun listino → la lista è puramente `contratti_righe`, tutte editabili.

**Step 4 — Eventualmente: aggiunta articoli compositi**

Se l'operatore aggiunge una riga con articolo `is_composito=TRUE`, scatta l'auto-init
componenti BoM: viene scritto un record in `contratti_righe` (riga padre) + N record
in `contratti_righe_componenti` (figli). Il prezzo padre è SUM(figli).

**Conseguenza non ovvia**: in modalità A/B, il composito genera necessariamente un
`contratti_righe` (per ancorare i figli), quindi appare sempre come `OVERRIDE` nella
preview. È implementativamente un override, ma logicamente non lo è — l'operatore non
ha negoziato un prezzo, è solo l'agganciamento dei figli BoM al listino bundle.

**Step 5 — Attivazione contratto (DRAFT → ATTIVO)**

Trigger DB blocca l'attivazione se:

- Modalità C e nessuna riga in `contratti_righe`, oppure righe con `prezzo_unitario NULL`
- Tipo/classe utenza incoerenti per utility con dimensione
- Overlap temporale con altro contratto attivo stessa (BA, istanza, utility, ambito)

Se passa: stato → ATTIVO, post-DRAFT le righe/utility diventano **congelate** (Profilo A).
Per modificarle servirebbe un nuovo contratto.

### 1.3 Riassunto della scelta operatore

L'operatore fa 3 scelte indipendenti:

1. Quale BA + utility (mondo del cliente)
2. Quale modalità tecnica A/B/C
3. Quali articoli/prezzi (riempimento righe)

La (2) è la più astratta delle tre e quella che richiede maggior conoscenza del modello.

---

## 2. Perché la scelta esplicita di modalità è problematica

### 2.1 È una scelta tecnica esposta a uno scopo commerciale

Le 3 modalità sono nate per descrivere combinazioni di campi DB. L'operatore non pensa
in termini di "modalità A": pensa "questo cliente ha un listino con sconto del 5%" oppure
"questo cliente è VIP e abbiamo trattato 3 articoli su 50 ad personam" oppure "qui non
c'è un listino, abbiamo concordato 12 articoli specifici".

Le label "A/B/C" sono codici interni che non comunicano l'intent. Anche tradotte ("Listino
+ variazione", "Listino + override", "Tutto negoziato") restano scelte di **modello**, non
di **dominio commerciale**.

### 2.2 La modalità è **derivabile** dai dati

Se l'operatore compila listino + variazione, è A. Se compila solo listino, è B. Se non
compila listino, è C. La modalità non aggiunge informazione rispetto ai dati — è
**ridondante**.

Far scegliere prima la modalità è anche un'**inversione di causalità**: oggi il SelectButton
modalità nasconde/mostra i campi listino/variazione. Cioè la modalità decide quali dati si
possono inserire. Ma logicamente è il contrario: i dati che servono determinano la modalità.

### 2.3 La modalità può cambiare durante l'editing

Se l'operatore in modalità A toglie la variazione → diventa B. Se aggiunge una riga override
in A → la preview comincia a mostrare un OVERRIDE → il BE oggi (bug) inizia a chiamarla B.
La modalità non è un attributo stabile della testata: è uno stato derivato che oscilla.

### 2.4 Manca un livello di governo

Oggi qualsiasi operatore può creare un contratto in qualsiasi modalità. Non c'è gating:

- Per emittente fiscale (es. emittente X non fa contratti negoziati puro)
- Per categoria cliente (es. cliente STANDARD può essere solo A)
- Per operatore (es. junior può solo applicare listini esistenti, senza override)
- Per azione di processo (es. "negoziare prezzi" è un permesso a sé)

Questo significa che le politiche commerciali dell'azienda non hanno nessun appoggio nel
modello: dipendono dall'autodisciplina e dalla formazione dell'operatore.

### 2.5 Le righe non rispettano la modalità

Anche post-fix del bug BE (modalità derivata da `tipo_variazione_globale`), resta che
in **modalità A** l'operatore può oggi creare override su singoli articoli del listino.
Ma la semantica di A è "listino + variazione **globale**" — l'override singolo è semanticamente
una contraddizione (è B). Eppure il modello DB lo permette.

Quindi A e B oggi sono distinguibili solo dalla presenza/assenza di `tipo_variazione_globale`,
non dalla presenza di override puntuali. Un contratto può essere "A con override singoli" —
ammesso dal modello, ma è una zona grigia logica.

---

## 3. Decisioni prese — modello e UX (primo giro)

> Questa sezione contiene le decisioni del primo giro di analisi. La sezione successiva
> (§3-bis) integra i raffinamenti del secondo giro.

### 3.1 Distinzione "modalità contratto" vs "reperimento prezzo"

Premessa metodologica: nelle vecchie ipotesi le due cose erano mescolate. Vanno separate
perché sono assi indipendenti.

- **Reperimento prezzo**: dato (BA, utility, articolo, data), da dove arriva il prezzo
  proposto? Cascata già esistente nei preventivi: contratto attivo → listino di categoria
  cliente → niente (manuale). **Non si tocca**. Funziona indipendentemente dalla forma del
  contratto.
- **Forma del contratto** (ex "modalità"): quali campi della testata sono valorizzati, cosa
  contengono le righe. È UX di costruzione, non logica di pricing. Su questa interviene il
  refactor.

Conseguenza: tutto ciò che riguarda la modalità A/B/C riguarda **solo** l'UX di costruzione
del contratto. Il pricing runtime non cambia (a parte l'estensione cascata parametri di §3.5).

### 3.2 Modello unificato — sparisce la scelta A/B/C

Le tre modalità A/B/C **non sono più una scelta dell'operatore**.

Il contratto diventa concettualmente **uno solo**, con due "forme" derivate automaticamente
in base a cosa l'operatore compila:

| Forma derivata      | Trigger                  | Corrispondenza vecchia modalità |
| ------------------- | ------------------------ | ------------------------------- |
| **"Con listino"**   | `listino_id` valorizzato | A + B (fuse)                    |
| **"Senza listino"** | `listino_id` NULL        | C                               |

La differenza A/B (ex: "listino + variazione globale" vs "listino + override singoli") sparisce
come distinzione di modello: entrambe diventano semplicemente "contratto con listino", dove
la variazione globale è un campo opzionale della testata e gli override sulle righe sono
azioni opzionali — **compatibili tra loro**.

In altre parole: un contratto con listino può avere variazione globale, override singoli,
entrambi, o nessuno dei due. Tutte e quattro le combinazioni sono valide e indistinguibili
dal modello.

**Conseguenza sul modello dati**: nessuna modifica strutturale ai campi (`listino_id`,
`tipo_variazione_globale`, `valore_variazione_globale` restano). Va però **rilassato il
CHECK constraint** che oggi vieta la coesistenza di "listino + variazione globale + righe
override" in modo strict. Tecnicamente è già ammesso oggi a livello CHECK; va verificato e
documentato.

### 3.3 Le righe come delta del listino

Decisione chiave sull'UX righe (era il punto §4.1 del recap e la "scelta 3" della sessione).

Il contratto **non importa** le righe del listino. Il listino resta riferimento esterno
(letto in preview/runtime via il resolver). Nella tabella `contratti_righe` vivono solo le
**eccezioni** rispetto al listino. Vedi §3-bis-A-schema per il dettaglio dello schema.

> **Importante**: la semantica del "delta vivo" del listino è ora qualificata dalla decisione
> §3-bis-A (snapshot del `listino_versione_id` all'attivazione). In DRAFT il contratto
> segue la versione corrente del listino; all'attivazione la versione viene fissata. Il
> testo originale di questa sezione che parlava di "delta vivo" anche dopo l'attivazione
> non è più valido — vedi §3-bis-A.

**Comportamento al runtime del resolver prezzo**: quando si chiede un prezzo per (cliente,
articolo) sul contratto attivo:

1. C'è una OVERRIDE per quell'articolo? → usa quel prezzo (la variazione globale **non** si
   applica, l'override è prezzo finale)
2. C'è una ESCLUSIONE? → articolo non disponibile per questo cliente, segnalalo
3. C'è una AGGIUNTA? → usa quel prezzo
4. Nessuna eccezione? → leggi il prezzo dalla **versione del listino fissata sul contratto**
   e applica eventuale variazione globale dalla testata

**Conseguenza pratica**: il flusso "importa righe selezionate" inizialmente ipotizzato è
scartato. Non c'è una fase di importazione. Il contratto vive come delta del listino fin
dal momento zero. In DRAFT segue il listino corrente; all'attivazione si snapshot la
versione listino. Le righe in eccezione sono blindate contro variazioni del listino in
ogni fase.

### 3.4 Permessi sulle righe — un unico permesso "variare prezzi"

L'operatore può modificare/escludere righe del listino **se e solo se** ha un permesso unico,
nominalmente "variare prezzi" (nome esatto da decidere, allineato al naming già usato per i
preventivi — vedi §3.5). Lo stesso permesso governa **sia** la variazione globale **sia** gli
override/esclusioni sulle righe.

Non c'è distinzione fra "permesso variazione globale" e "permesso override riga": un solo
toggle.

| Senza permesso                                                                         | Con permesso                                        |
| -------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Testata: campo variazione globale **readonly**                                         | Testata: campo variazione globale **editabile**     |
| Righe: tutte readonly (listino così com'è + AGGIUNTE già presenti ma non modificabili) | Righe: override/esclusioni/aggiunte tutte possibili |

Nota: il permesso "variare prezzi" governa la **possibilità di toccare**. Quanto si possa
spingere oltre è materia delle soglie (§3.5).

### 3.5 Gate prezzo — stesso pattern dei preventivi, esteso a categoria cliente

Quando l'operatore tenta di mettere un prezzo override (manuale) diverso dal suggerito dal
resolver, scattano i 3 gate identici al pattern preventivi:

- **Gate 1 — Permesso**: l'utente ha l'azione di processo "variare prezzi"? Se no → 403
  non retryable.
- **Gate 2 — Soglia**: `delta_pct = (manuale - suggerito) / suggerito × 100`. Soglia letta
  via cascata parametri. Se entro soglia → riga salvata. Se eccede → 403 retryable con
  dettagli.
- **Gate 3 — Escalation**: se 403 retryable, frontend mostra "Richiedi approvazione". Su
  click, BE crea pratica `APPROVAZIONE_PREZZO` collegata, riga con
  `stato_approvazione_prezzo='PENDING'`, blocco modifiche/attivazione finché non risolta.

**Estensione della cascata parametri**: oggi nei preventivi la cascata è
`user → group → emittente → default`. Viene **estesa** per includere la categoria cliente
del BA destinatario. Per l'ordine esatto vedi §3-bis-C.

L'estensione viene fatta **una sola volta**, e vale anche per i preventivi (uniformità
desiderata, evita di avere due cascate parametri diverse). Per l'impatto sui preventivi e
la strategia di rilascio in due PR DB separate vedi §3-bis-D.

### 3.6 UX del form contratto

Conseguenza diretta delle decisioni precedenti, lato `ContrattoDrawer.vue`:

- **Niente SelectButton modalità A/B/C** (rimosso)
- **Parametro `VENDITE_CONTRATTO_DEFAULT_MODALITA`** → diventa obsoleto, da rimuovere
- Sezione "Pricing" diventa:
  - Campo "Listino di partenza" (opzionale)
  - Campo "Variazione globale" (opzionale, gated su permesso "variare prezzi")
- Computed `derivedModalita` produce un badge informativo readonly post-save:
  "Contratto con listino LST-001, sconto globale 5%" / "Contratto senza listino di
  riferimento" / etc. — informativo, non decisivo
- Logica enable/disable dei campi: in base al permesso "variare prezzi" dell'utente, la
  variazione globale è editabile o readonly

Lato `ContrattoRigheDrawer.vue`:

- Banner contesto pricing (mutuato dai preventivi) mostra il riferimento corrente: "Listino
  LST-001 versione 5 attivo per questo contratto"
- Lista righe = preview combinata: righe listino (lette dalla versione fissata via resolver)
  + eccezioni in `contratti_righe` (OVERRIDE/ESCLUSIONE/AGGIUNTA)
- Su ogni riga del listino: azioni "Modifica prezzo" (crea/aggiorna OVERRIDE), "Escludi"
  (crea ESCLUSIONE) — entrambe gated sul permesso "variare prezzi"
- Aggiunta articolo fuori-listino: crea AGGIUNTA, gated sullo stesso permesso
- I 3 gate scattano al save della singola riga override (non al save del contratto intero)

### 3.7 Compositi — copertura parziale

Decisione (era §4.2 del doc originale): con il modello unificato la **classificazione** dei
compositi si chiude (sparisce la "zona grigia A pura con righe implicite"). Restano però
tre sotto-problemi che dipendono dalla decisione sul versioning del listino — vedi §3-bis-B
per il dettaglio.

### 3.8 Backward compatibility — non si pone

Decisione (era §6 punto 5 del doc originale): ZeroERP non ha produzione, i contratti
esistenti sono solo dati di sviluppo. Si scarta la backward compatibility, si parte da
schema pulito.

Nessuna migrazione dati da progettare. La migration DB del refactor può ricreare struttura
ed eventualmente svuotare le tabelle contratti.

---

## 3-bis. Decisioni del secondo giro — raffinamenti

> Questa sezione integra le decisioni emerse dopo la review critica delle ipotesi §3.
> Ogni punto qui chiude o qualifica un'ambiguità della sezione precedente. Quando §3 e
> §3-bis dicono cose diverse, **vince §3-bis**.

### 3-bis-A. Snapshot della versione listino all'attivazione

**Tensione risolta**: §3.3 originale ("delta vivo del listino") era in conflitto con §1.2
step 5 ("Profilo A: righe congelate post-attivazione"). Le opzioni considerate erano:

- (a) Delta vivo sempre — contratto attivo segue il listino corrente
- (b) Delta vivo in DRAFT, snapshot di tutte le righe DA_LISTINO in `contratti_righe`
  all'attivazione
- (c) Delta vivo in DRAFT, snapshot del `listino_versione_id` all'attivazione (senza
  duplicare righe)

**Decisione: (c)**. Il contratto referenzia `listino_id + listino_versione_id`. I listini
sono già versionati (`valido_dal/valido_al`), quindi una versione fissata è immutabile.

**Conseguenze**:

- Aggiungere campo `listino_versione_id` (nullable) alla tabella `vendite.contratti`
- In DRAFT: `listino_versione_id` può essere NULL → il contratto segue la versione corrente
  del listino (utile per costruzione)
- All'attivazione: trigger riempie `listino_versione_id` con la versione attiva al momento
  dell'attivazione, e da quel momento è immutabile
- Profilo A (congelamento) si traduce in: post-attivazione non si possono più modificare
  `listino_id`, `listino_versione_id`, `tipo_variazione_globale`, `valore_variazione_globale`,
  né le eccezioni
- Il resolver prezzo legge sempre la versione listino fissata sul contratto (se contratto
  attivo) o la versione corrente (se contratto DRAFT)
- Se domani esce LST-001 v6, il contratto di Mario continua a leggere v5 — comportamento
  prevedibile, niente sorprese in fattura

**Nessuna duplicazione di righe `contratti_righe`** per articoli non in eccezione: vivono
solo gli OVERRIDE/ESCLUSIONI/AGGIUNTE.

#### Drift del listino mentre il contratto è in DRAFT

Finché il contratto è in DRAFT, `listino_versione_id` può essere NULL e il contratto segue
la versione corrente del listino. Se durante il lavoro in DRAFT esce una nuova versione del
listino (es. cambia un prezzo articolo), la preview del contratto si aggiorna automaticamente
al nuovo prezzo per le righe non in eccezione. Gli OVERRIDE/ESCLUSIONE/AGGIUNTA già inseriti
**non vengono invalidati** (puntano all'articolo, non alla versione listino), ma il loro
"delta% rispetto al base" può essere cambiato perché il base è cambiato.

Regole di comportamento in DRAFT:

- **Gate L2 valutato al save dell'override, non al read**: se Mario salva un OVERRIDE -10%
  vs versione listino v5 e poi esce v6 che renderebbe quel delta -25%, il gate L2 non si
  rivaluta automaticamente. L'OVERRIDE resta valido; sarà ri-validato solo se Mario lo
  modifica esplicitamente.
- **Segnalazione operatore in UI**: quando il contratto in DRAFT è aperto in drawer e il
  resolver rileva che `listino_versione_id` corrente differisce da quella usata per gli
  OVERRIDE esistenti, il banner contesto mostra un avviso ("Il listino è stato aggiornato
  alla versione v6. Le tue eccezioni sono ancora valide ma riferite alla versione v5 —
  rivedi prima di attivare"). L'operatore può lasciar correre o rivedere.
- **All'attivazione**: il trigger fissa `listino_versione_id` alla versione corrente al
  momento dell'attivazione, non a quella vista al momento dell'inserimento delle eccezioni.
  Da quel momento il banner di drift sparisce e il contratto è blindato.

### 3-bis-A-schema. Schema delle eccezioni — `tipo_eccezione` esplicito

**Decisione**: niente "magia su NULL". Aggiungere a `contratti_righe` un campo
`tipo_eccezione` enum NOT NULL con valori `OVERRIDE` / `ESCLUSIONE` / `AGGIUNTA`.

| `tipo_eccezione` | Significato                                              | `prezzo_unitario` | Note                                    |
| ---------------- | -------------------------------------------------------- | ----------------- | --------------------------------------- |
| `OVERRIDE`       | Prezzo personalizzato per articolo presente nel listino  | NOT NULL          | La variazione globale non si applica    |
| `ESCLUSIONE`     | Articolo del listino non disponibile per questo cliente  | NULL              | Marker di esclusione, nessun prezzo     |
| `AGGIUNTA`       | Articolo non presente nel listino, aggiunto al contratto | NOT NULL          | Valido anche su contratti senza listino |

**Constraint**:

- Unique parziale (o trigger) su `(contratto_id, articolo_id)` quando il record è OVERRIDE
  o ESCLUSIONE → al massimo un'eccezione per articolo del listino
- AGGIUNTA può duplicare il vincolo solo se l'articolo non è nel listino di riferimento
  (caso normale); se il listino lo contenesse, si dovrebbe usare OVERRIDE — da gestire con
  validazione service
- `prezzo_unitario` NOT NULL se `tipo_eccezione IN ('OVERRIDE', 'AGGIUNTA')`, NULL se
  `tipo_eccezione = 'ESCLUSIONE'` (CHECK)

Motivazione: NULL su `prezzo_unitario` ha già un suo significato semantico (campo non
valorizzato durante DRAFT). Sovraccaricarlo come marker di esclusione era overload semantico
e una "pezza" da evitare per filosofia.

### 3-bis-B. Compositi — applicazione della §3-bis-A

I tre sotto-problemi sui compositi si risolvono coerentemente con la decisione (c):

**B1. Composito come AGGIUNTA**: padre + figli sono entrambi roba del contratto (record in
`contratti_righe` per il padre + record in `contratti_righe_componenti` per i figli).
Nessun conflitto col listino. Già risolto.

**B2. Composito come OVERRIDE su listino bundle**: il padre ha prezzo override (dichiarato
dall'operatore). I figli replicano la BoM del bundle del listino. Coerentemente con §3-bis-A,
**i figli leggono la BoM dalla versione listino fissata sul contratto** (non dinamicamente
dal listino corrente). Nessuna duplicazione strutturale dei componenti se non quando servono
override sui figli stessi (caso raro).

**B3. Univocità (contratto, articolo)**: il constraint di unicità (vedi §3-bis-A-schema)
vale **solo sul padre** in `contratti_righe`. I `contratti_righe_componenti` hanno la loro
chiave (`contratto_riga_padre_id` + `componente_id`) e non concorrono al constraint del
padre.

### 3-bis-C. Cascata parametri — 5 livelli, categoria prima di group

**Decisione**: la cascata di risoluzione di un parametro soglia diventa:

```
user → categoria_cliente → group → emittente → default
```

**Motivazione**: categoria cliente vince su group. La regola commerciale (categoria PREMIUM
ha max sconto 5%) prevale sul seniority dell'operatore (Mario SENIOR ha max 20%). Se Mario
serve un cliente PREMIUM, la sua soglia è 5%. Eccezioni per singoli senior si configurano
come override a livello `user` (primo livello, sovrascrive tutto).

**Esempio**:

- Default sistema: 10%
- Emittente fiscale FATT001: 12%
- Group SENIOR: 20%
- Categoria PREMIUM: 5%
- User Mario.Junior: nessun override
- User Maria.Senior: nessun override (ma è nel group SENIOR)

Casi risolti:

- Mario.Junior su cliente PREMIUM → 5% (categoria_cliente vince)
- Mario.Junior su cliente STANDARD → 10% (default, niente categoria, niente group, niente
  emittente specifici applicabili)
- Maria.Senior su cliente PREMIUM → 5% (categoria_cliente vince ancora, group SENIOR è
  secondario)
- Maria.Senior su cliente STANDARD → 20% (group SENIOR vince, niente categoria applicabile)

**Classe_utenza**: presente in altre tabelle pricing (`categorie_clienti_listini.classe_utenza_id`)
ma **fuori dalla cascata** in questa prima versione. Da rivalutare se emerge necessità reale.

**Conseguenza sul modello dati**:

- Estensione `config.parameters_overrides` (o tabella equivalente) con colonna
  `categoria_cliente_id` nullable
- Funzione `fn_resolve_parameter` (o equivalente) → nuovo argomento `categoria_cliente_id`
- Chiamanti del gate 2 → devono recuperare la `categoria_cliente_id` dal BA del contratto/
  preventivo e passarla al risolutore

### 3-bis-D. Split in due PR DB indipendenti

**Decisione**: il refactor viene rilasciato in due PR DB sequenziali, non in un unico drop.

**PR DB-1 — Estensione cascata parametri** (trasversale, abilita preventivi e contratti):

- Schema: nuova colonna `categoria_cliente_id` in `config.parameters_overrides`
- Funzione: nuovo signature di `fn_resolve_parameter` con `categoria_cliente_id`
- Migrazione dati: nessuna (colonna nullable, semantica retro-compatibile)
- Impatto BE preventivi:
  - `preventivi_service` gate 2 → recupera `categoria_cliente_id` dal BA e passa al
    risolutore
  - `PricingLimitiUtenteView` (endpoint hint UI) → nuovo signature che accetta
    `billing_account_id` per recuperare la categoria
  - Tutti i test L2 esistenti dei preventivi → aggiornati al nuovo signature
- Valore di per sé: dopo PR DB-1, le soglie sui preventivi tengono già conto della categoria
  cliente

**PR DB-2 — Refactor contratti unificato** (dipende da PR DB-1):

- Schema:
  - Rilassamento CHECK constraint su `vendite.contratti` (ammessa coesistenza listino +
    variazione globale + eccezioni)
  - Nuovo campo `listino_versione_id` in `vendite.contratti` (nullable, fissato
    all'attivazione)
  - Nuovo campo `tipo_eccezione` enum in `contratti_righe` + constraint correlati
- Funzioni:
  - Aggiornamento `fn_resolve_prezzo_listino_v2` (o equivalente del resolver contratti) per
    gestire OVERRIDE/ESCLUSIONE/AGGIUNTA + lettura dalla versione listino fissata
  - Trigger attivazione: fissa `listino_versione_id` se NULL e contratto sta passando da
    DRAFT a ATTIVO
  - Drop trigger / CHECK obsoleti su "modalità"
- Drop parameter `VENDITE_CONTRATTO_DEFAULT_MODALITA`
- Migrazione dati: nessuna (decisione §3.8: schema pulito, no backward compat)

**Vantaggi della separazione**:

- Blast radius del PR contratti ridotta (la cascata parametri è già stabilizzata)
- Valore intermedio rilasciabile (preventivi con soglia per categoria)
- Più facile testare e revisionare in due review separate

### 3-bis-E. Gate L2 si applica anche alla variazione globale

**Decisione**: i 3 gate prezzo (§3.5) scattano **anche** sulla variazione globale del
contratto, non solo sugli override di singola riga.

**Comportamento**:

- Quando l'operatore salva la testata del contratto con `valore_variazione_globale`
  diverso da zero, i 3 gate vengono valutati prima del save
- **Gate 1** (permesso): se l'utente non ha "variare prezzi", la variazione globale non è
  nemmeno editabile (UI readonly, BE rifiuta in PATCH se valore presente)
- **Gate 2** (soglia): la variazione globale è essa stessa un delta percentuale (se
  `tipo_variazione_globale = PERCENTUALE`). Il valore viene confrontato con:
  - `VENDITE_MAX_SCONTO_PCT` se la variazione è negativa (sconto)
  - `VENDITE_MAX_MAGGIORAZIONE_PCT` se positiva (maggiorazione)
  - Stessa logica usata oggi da `_check_limite_variazione_prezzo` nei preventivi
- **Gate 3** (escalation): se gate 2 fallisce, frontend mostra "Richiedi approvazione" sulla
  testata. Backend crea pratica `APPROVAZIONE_PREZZO` legata al contratto, contratto in
  stato bloccato finché non risolta

**Caso `VALORE_FISSO`**: se la variazione globale è un valore assoluto e non percentuale,
il gate 2 non è applicabile per confronto soglia%. Da valutare in implementazione se
introdurre un secondo set di parametri (`VENDITE_MAX_SCONTO_ABS`, ecc.) o vietare
`VALORE_FISSO` come variazione globale (lasciandolo solo per override su righe specifiche).
Decisione operativa da prendere in fase brief DB.

**Decisione chiusa (2026-05-18)**: ✅ `VALORE_FISSO` **vietato come variazione globale**
sulla testata contratto. Resta ammesso unicamente per OVERRIDE su singola riga
(semantica "prezzo fisso sostitutivo per quell'articolo"). Implementazione:

- `_TIPI_VARIAZIONE_GLOBALE_AMMESSI` in `contratti_service.py` ridotto a
  `frozenset({"PERCENTUALE"})` — validatore `_apply_variazione_globale`
  solleva `E_VENDITE_VALIDATION` con messaggio parlante se l'operatore
  invia `VALORE_FISSO`.
- Lookup FE `tipi_variazione_contratto` (`vendite_lookups_service._TIPI_VARIAZIONE_CONTRATTO`)
  ritorna solo `PERCENTUALE` → il SelectButton FE (FE 2.1 quando atterrerà)
  non esporrà nemmeno l'opzione `VALORE_FISSO` sulla testata.
- Test: `test_update_contratto_variazione_valore_fisso_rifiutata` +
  aggiornamento `test_tipi_variazione_contratto_ok` API.

### 3-bis-F. Togliere `listino_id` con eccezioni esistenti — blocco esplicito

**Decisione**: se l'operatore tenta di rimuovere il `listino_id` da un contratto che ha
eccezioni di tipo OVERRIDE o ESCLUSIONE, l'API risponde con **422** e messaggio chiaro.

**Logica**:

- OVERRIDE e ESCLUSIONE perdono significato senza un listino di riferimento → blocco
- AGGIUNTA resta valida (è un articolo fuori-listino, vale anche senza listino) → no blocco
  solo per AGGIUNTE

**Messaggio API esempio** (422):

```json
{
  "detail": "Impossibile rimuovere il listino: 5 eccezioni (3 OVERRIDE, 2 ESCLUSIONE) sono ancora associate. Rimuovi prima le eccezioni o sostituiscile con AGGIUNTE.",
  "code": "E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI"
}
```

**Motivazione**: trasformazioni automatiche (es. OVERRIDE → AGGIUNTA, cancellazione
automatica ESCLUSIONI) sono modifiche semantiche nascoste. L'operatore deve **vedere** che
sta perdendo dati o cambiandone il significato. Il blocco con messaggio chiaro porta più
consapevolezza, meno sorprese.

---

## 4. Tensioni nel modello attuale — esito post-decisioni

### 4.1 Modalità A "con override" — è A o B? → Risolta

Risolta da §3.2: A e B fuse in "contratto con listino". La domanda non si pone più.

### 4.2 Compositi in qualsiasi modalità → Risolta

Risolta da §3.7 + §3-bis-B (con dipendenza da §3-bis-A).

### 4.3 Editabilità delle righe DA_LISTINO → Risolta

Risolta da §3.3 + §3.4 + §3-bis-A-schema: le righe del listino sono readonly per default;
chi ha il permesso "variare prezzi" può fare OVERRIDE, ESCLUSIONE o AGGIUNTA. Niente
importazione iniziale, modello delta con `tipo_eccezione` esplicito.

### 4.4 Listino senza versione attiva → Risolta (decisione 2026-05-18)

**Decisione chiusa**: ✅ un listino **senza versione ATTIVA non è selezionabile**
come riferimento contrattuale. Implementazione:

- BE guard pre-save: `ContrattiService._guard_listino_ha_versione_attiva` invocato in
  `_build_create_data_testata` e `_build_update_data_testata` quando `listino_id`
  è valorizzato. Helper repo: `ListiniRepository.has_versione_attiva(listino_id)`
  (single round-trip EXISTS su `vendite.listini_versioni` con `stato='ATTIVA'` +
  `attivo IS TRUE`).
- Nuovo codice errore `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (422) registrato
  in `error_policies.py` con messaggio parlante per il banner FE.
- Test: `test_create_contratto_listino_senza_versione_attiva_rifiutato`.

**Conseguenza sul flag `listino_senza_versione_oggi`** del payload `list_righe_preview`:
non più necessario come "warning UX", perché il caso non si crea più (il guard pre-save
lo intercetta). Il flag resta nel payload come safety net per contratti pre-esistenti
(prima della decisione 2026-05-18) che potrebbero avere `listino_id` con versione
poi disattivata. Da rimuovere quando confermiamo che il DB non ha più contratti
in tale stato.

**FE downstream (FE 2.1)**: il lookup listini per il drawer contratto dovrebbe
filtrare solo listini con versione attiva, per non mostrare opzioni che il save
rifiuterebbe. Il lookup attualmente vive in `dbops.fn_get_lookup_codici`
(whitelist DB-side `vendite.listini` senza JOIN su versioni). Soluzione richiede
**brief DB**: estendere il lookup `vendite.listini` con filtro `WHERE EXISTS (SELECT
1 FROM vendite.listini_versioni v WHERE v.listino_id = l.id AND v.stato='ATTIVA'
AND v.attivo IS TRUE)`. Alternative: endpoint dedicato `/api/v1/vendite/contratti/lookup/listini-selezionabili/`
(pattern API.md "lookup dedicato"). **Open task**, basso costo (1h DB + 30 min FE
swap dell'endpoint).

### 4.5 Transizione modalità in editing → Non si pone più (con riserva §3-bis-F)

Con il modello unificato non esiste più la "transizione di modalità". Cambiare i campi
della testata (mettere/togliere listino, mettere/togliere variazione globale) è una
semplice PATCH che lascia intatte le righe `contratti_righe`. Le righe restano valide; il
resolver in preview interpreterà diversamente la combinazione finale.

**Eccezione bloccata**: togliere `listino_id` con eccezioni OVERRIDE/ESCLUSIONE → blocco
422 come da §3-bis-F.

---

## 5. Piano operativo BE / FE — step con prerequisiti DB

> Il dettaglio completo delle modifiche DB (DDL, funzioni, trigger, pgTAP) vive nel brief
> dedicato [`brief-db-refactor-contratti-completo.md`](brief-db-refactor-contratti-completo.md).
> Questa sezione elenca i workstream BE/FE che il backend agent prenderà in carico,
> indicando per ognuno il **prerequisito DB** (step del brief che deve essere chiuso e con
> pgTAP verde) e il **prerequisito BE** (per gli step FE).
>
> Pattern operativo: appena il team DB notifica la chiusura di uno step, il backend agent
> avvia in parallelo tutti i workstream che hanno solo quello come prerequisito.

### 5.1 FASE 1 — Workstream BE/FE preventivi (cascata parametri estesa)

Trigger di avvio: chiusura step DB 1.2 (`fn_get_parameter_full` con
`categoria_cliente_id`).

| Step | Stato | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- | --- |
| **BE 1.1** | ✅ | Gate L2 propaga `categoria_cliente_id` recuperato dal BA. Lookup spostato post-early-return (superuser bypass non spreca query) | service | DB 1.2 chiuso | `preventivi_service.py` (`_check_limite_variazione_prezzo`, `_resolve_or_check_override_prezzo`) |
| **BE 1.2** | ✅ | `PricingLimitiUtenteView` accetta `billing_account_id` opzionale; deriva categoria via `BillingAccountRepository.get_categoria_cliente_id` (nuovo BB) | api | DB 1.2 chiuso | `views_pricing.py`, `parameter_service.py`, `parameter_repository.py`, `billing_account_repository.py` |
| **BE 1.3** | ✅ | +6 test mirati: `test_get_parameter_passes_categoria_cliente`, `test_get_defaults_passes_categoria_cliente`, `test_limiti_utente_senza_ba_categoria_none`, `test_limiti_utente_con_ba_propaga_categoria`, `test_limiti_utente_ba_malformato_ignorato`, `test_gestisci_riga_L2_propaga_categoria_cliente` + assert "no lookup BA su superuser bypass". 2393/2393 verdi. | test | BE 1.1 + BE 1.2 | `tests/services/test_parameter_service.py`, `tests/api/test_pricing_api.py`, `tests/services/test_preventivi_service.py` |
| **FE 1.1** | ✅ | Chiamata `PricingLimitiUtenteView` con `billing_account_id` (composable `useLimitiPricing` cache per-BA) + banner soglia con copy condizionale "su questo cliente" se BA presente (2026-05-18) | UI preventivi | BE 1.2 | `useLimitiPricing.js`, `PreventiviRigaForm.vue` |
| **DOC 1.1** | ✅ | `api_preventivi.md` sezione L2 con cascata estesa + `api_pricing.md` query param `billing_account_id` + catalogo BB aggiornato (ParameterService + nuovo `get_categoria_cliente_id`) | doc | BE 1.1 + BE 1.2 | `docs/it/backend/vendite/manual/api_preventivi.md`, `api_pricing.md`, `docs/it/dev/backend/catalogo-building-block-backend.md` |

**Note di completamento BE (2026-05-15)**:

- Cascata estesa propagata: `parameter_repository.py` (`_SQL_RESOLVE` con 7 segnaposto), `parameter_service.py` (4 fn pubbliche), `preventivi_service.py` (`_check_limite_variazione_prezzo`)
- Nuovo BB `BillingAccountRepository.get_categoria_cliente_id` simmetrico a `get_istanza_utility_id`
- Optimization: lookup BA→categoria avviene dentro `_check_limite_variazione_prezzo` dopo gli early-return (superuser, delta=0, resolver nullo) per non sprecare round-trip DB su gate inattivi
- `list_parameters_for_user` (admin UI overview parametri) **non esteso** in questa fase: la fn DB `script.fn_list_parameters_for_user` non riceve `categoria_cliente_id`. Estendere quando emergerà necessità admin di filtrare per categoria

Stima Fase 1 (BE+FE+DOC): 1-2 sessioni. **Tutto chiuso 2026-05-18** (FE 1.1
implementato + raffinamento copy condizionale BA).

### 5.2 FASE 2 — Workstream BE/FE contratti (refactor unificato)

I trigger di avvio sono differenziati per step DB di Fase 2 perché ogni step DB abilita
un sottoinsieme di workstream BE/FE (vedi tabella dipendenze in fondo al brief DB).

#### 5.2.1 Indipendenti — possono partire subito

| Step | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- |
| **FE 2.0** | Cleanup default prop del bug recap §3.1 (FE) | UI contratti | Nessuno | `ContrattoRigheDrawer.vue` (vedi `recap-contratti-post-componenti.md` §3.2) |

#### 5.2.2 Dipendenti da DB Fase 1 (cascata parametri)

Possono partire alla chiusura della Fase 1 DB, indipendenti dalla Fase 2 DB.

| Step | Stato | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- | --- |
| **BE 2.0** | ✅ | Orchestratore 3 gate (L1+L2+L3) per riga `contratti_service`, mutuati da `preventivi_service`. **Estratto BB condiviso** `resolve_or_check_override_prezzo` in `_pricing_gate_helpers.py` parametrizzato su `resolver_fn` + `error_code_validazione`. Aggiunti `contratti_suggerisci_prezzo_riga` (resolver wrapper) e `resolve_or_check_override_prezzo_riga_contratto` (thin wrapper sul BB). Preventivi refactor a thin wrapper (zero regressioni). 11 nuovi test mirati. **Non ancora cablato** in `create_riga`/`update_riga`: wiring in BE 2.2 quando arrivano le operazioni eccezione OVERRIDE/AGGIUNTA. | service | DB 1.2 chiuso | `_pricing_gate_helpers.py`, `preventivi_service.py`, `contratti_service.py`, `test_contratti_service.py` |

#### 5.2.3 Dipendenti da DB step 2.1 (cleanup modalità su contratti)

| Step | Stato | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- | --- |
| **BE 2.1** | ✅ | Rimozione logica gating modalità: `_validate_modalita_coerente` eliminato; `list_righe_preview` non deriva più A/B/C ma restituisce forma `con_listino` / `senza_listino`. Cleanup docstring obsolete + rimozione duplicazione `categoria_cliente_id_snapshot` (apply chiamato 2 volte in `_build_create_data_testata`). | service | DB 2.1 | `contratti_service.py` |
| **FE 2.1** | ✅ | SelectButton A/B/C rimosso; sezione "Pricing" semplificata (Listino opzionale + Variazione globale solo PERCENTUALE post 2026-05-18 §3-bis-E); badge `forma_derivata` readonly post-save; lookup Listino sostituito da endpoint dedicato filtrato su versione ATTIVA | UI contratti | BE 2.1 | `ContrattoDrawer.vue` |

#### 5.2.4 Dipendenti da DB step 2.2 (tipo_eccezione su contratti_righe)

| Step | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- |
| **BE 2.2** | Service di gestione eccezioni: `aggiungi_eccezione`, `aggiorna_eccezione`, `rimuovi_eccezione` con dispatch sui 3 tipi OVERRIDE/ESCLUSIONE/AGGIUNTA; `list_righe_preview` JOIN listino + eccezioni | service | DB 2.2 | `contratti_service.py`, `contratti_repository.py` |
| **BE 2.3** | Endpoint REST aggiornati per i 3 tipi eccezione (serializzatori, payload validation) | api | BE 2.2 | `views_contratti.py` |
| **BE 2.4** | Blocco rimozione listino con eccezioni OVERRIDE/ESCLUSIONE (422 `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`) | service | DB 2.2 | `contratti_service.py` (in `aggiorna_contratto` / `patch_testata`) |
| **FE 2.2** | Azioni di riga "Modifica prezzo", "Escludi", "Aggiungi articolo" su `ContrattoRigheDrawer.vue`, tutte gated sul permesso "variare prezzi" | UI contratti | BE 2.3 | `ContrattoRigheDrawer.vue` |

#### 5.2.5 Dipendenti da DB step 2.3 (trigger attivazione + lock post-attivazione)

| Step | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- |
| **BE 2.5** | Mapping dei nuovi errori DB attivazione (`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`, `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`) in `error_policies.py`; gestione transizione DRAFT→ATTIVO | service + policy | DB 2.3 | `contratti_service.py`, `error_policies.py` |
| **FE 2.3** | Handling 403 retryable per "richiedi approvazione" su testata (variazione globale gate L3) + 422 blocco rimozione listino | UI contratti | BE 2.5 + BE 2.4 | `ContrattoDrawer.vue`, `ContrattoRigheDrawer.vue` |

#### 5.2.6 Dipendenti da DB step 2.4 (resolver aggiornato)

| Step | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- |
| **BE 2.6** | Endpoint contesto pricing contratti `GET /api/v1/vendite/contratti/<id>/contesto-pricing/` (mutuato da preventivi) | api | DB 2.4 | `contratti_repository.py` (`resolve_contesto_pricing_contratto`), `views_contratti.py` |
| **FE 2.4** | Banner contesto pricing in `ContrattoRigheDrawer.vue` (mostra `listino` + `versione fissata` se ATTIVO, o "versione corrente" se DRAFT); banner drift listino in DRAFT (§3-bis-A) | UI contratti | BE 2.6 | `ContrattoRigheDrawer.vue` |

#### 5.2.7 Documentazione (a chiusura del refactor)

| Step | Lavoro | Area | Prerequisito | File principali |
| --- | --- | --- | --- | --- |
| **DOC 2.1** | `api_contratti.md` reworked completo: nuovo modello unificato, 3 tipi eccezione, listino_versione_id, 3 gate, errori nuovi | doc | Tutti BE Fase 2 | `docs/it/backend/vendite/manual/api_contratti.md` |
| **DOC 2.2** | Nuovo `modello-contratti.md`: reference del modello contratto + relazioni con listino (snapshot versione, eccezioni, simmetria/asimmetria con preventivi) | doc | Tutti BE Fase 2 | `docs/it/backend/vendite/manual/modello-contratti.md` |
| **DOC 2.3** | Aggiornamento glossario: rimuovere "modalità A/B/C", aggiungere "forma derivata", "eccezione", "versione listino fissata", "drift listino" | doc | DOC 2.1 + DOC 2.2 | `docs/it/glossario.md` o equivalente |

### 5.3 Ordine di esecuzione consigliato

1. **DB Fase 1** (team DB) → Step 1.1 → 1.2 → 1.3
2. Chiusura DB 1.2 → **BE 1.1 + BE 1.2 + BE 2.0** in parallelo (3 workstream)
3. Chiusura DB 1.3 → **BE 1.3 + FE 1.1 + DOC 1.1** in parallelo
4. **FE 2.0** (cleanup default prop) può partire in qualsiasi momento, indipendente
5. **DB Fase 2** (team DB) → Step 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7
6. Chiusura DB 2.1 → **BE 2.1** → **FE 2.1**
7. Chiusura DB 2.2 → **BE 2.2 + BE 2.4** in parallelo → **BE 2.3** → **FE 2.2**
8. Chiusura DB 2.3 → **BE 2.5** → **FE 2.3**
9. Chiusura DB 2.4 → **BE 2.6** → **FE 2.4**
10. Chiusura DB 2.7 → **DOC 2.1 + DOC 2.2** → **DOC 2.3**

### 5.4 Stima complessiva

5-7 sessioni di sviluppo BE/FE distribuite su 2 PR DB. Il piano sopra è ottimizzato per
massimizzare la parallelizzazione: i workstream non in catena di dipendenza vengono
avviati appena il loro prerequisito DB è chiuso.

**Consuntivo (2026-05-19): chiuso end-to-end in 5 sessioni** (15-16, 17, 18, 19 maggio,
+1 sessione DB simmetria L3). Tutti gli step BE/FE/DOC ✅ — vedi §7.1–§7.9 per il
dettaglio cronologico.

---

## 6. Stato di questo documento

- ✅ **REFACTOR COMPLETATO end-to-end (2026-05-19)** — DB + BE + FE + DOC tutti
  chiusi. Vedi §7.1–§7.8 per il riepilogo cronologico delle attività svolte.
- ✅ **CHIUSE le decisioni di modello, UX e schema**: §3 e §3-bis contengono tutte le scelte
  definitive.
- ✅ **CHIUSI dettagli implementativi minori (2026-05-18)**:
  - §3-bis-E: `VALORE_FISSO` **vietato come variazione globale** (solo OVERRIDE riga).
    Implementato + test.
  - §4.4: listino **senza versione ATTIVA non selezionabile** — guard pre-save BE
    e codice errore parlante. Filtro FE lookup chiuso 2026-05-18 con endpoint dedicato
    `GET /api/v1/vendite/lookup/listini-selezionabili-contratto/` (no brief DB
    necessario: la logica e' BE+FE pura sopra `EXISTS listini_versioni`).
  - Nome permesso: **"variare prezzi"** (label UX/doc). Il codename DB resta
    `prezzo_override_manuale` per stabilità del binding.
- ✅ **CHIUSO debito tecnico §7.6 (2026-05-19)**: porting gate L1+L2+L3 sulle
  righe contratto in `create_riga`/`update_riga` + workflow L3 (richiesta
  approvazione, pratica APPROVAZIONE_PREZZO, endpoint approva/rifiuta dedicati
  righe contratto, CTA FE "Richiedi approvazione" su ContrattoRigheDrawer).
  Service `approvazioni_prezzo_service` reso sorgente-agnostico via
  `_SORGENTE_CONFIG`. Vedi §7.8 + §7.9.
- Il recap [`recap-contratti-post-componenti.md`](recap-contratti-post-componenti.md)
  e' **obsoleto post-refactor**: le 3 modalità A/B/C non esistono piu' come
  scelta utente (sostituite da forma derivata `con_listino`/`senza_listino`).
  I bug logici §3.1–§3.4 del recap sono stati assorbiti dal refactor (BE
  derivazione naturale via `c.listino_id`, FE row actions non piu' bloccate
  su DA_LISTINO grazie a Opzione C, default prop rimosso). Le decisioni di
  dominio §4 del recap sono state chiuse in §3-bis di questo doc.
- **Out-of-scope di questo refactor**: relazione preventivo↔contratto e dominio offerta
  commerciale. Il flusso `push_a_commessa` per i preventivi resta intatto; il contratto
  continua a nascere direttamente dall'operatore. Il modello §3-bis-A (snapshot della
  versione listino) è preparato per ricevere in futuro un push da un'eventuale entità
  `offerta_commerciale`, ma non la richiede oggi. Per il ragionamento di dominio e le
  opzioni considerate vedi [`analisi-offerta-commerciale.md`](analisi-offerta-commerciale.md).
- Documenti prodotti:
  - ✅ [`brief-db-refactor-contratti-completo.md`](brief-db-refactor-contratti-completo.md)
    — brief DB completo Fase 1 + Fase 2 a step incrementali, per passaggio al team DB su
    `dev/db-tid`
  - ✅ §5 di questo doc — piano operativo BE/FE step-per-step con prerequisiti DB
- Building block estratti per il refactor (oltre a quelli censiti nei file):
  - ✅ `apps/vendite/services/_pricing_gate_helpers.py` — BB condiviso che centralizza
    i 3 gate "autorizzazioni prezzi": `check_permesso_override_prezzo` (L1),
    `check_limite_variazione_prezzo` (L2 riga, sconto/maggiorazione vs resolver),
    `check_limite_variazione_globale` (L2 testata contratto, valore % gia' delta).
    Cascata user→categoria_cliente→group→emittente→default, workflow L3
    `accept_for_approval` per pratica APPROVAZIONE_PREZZO. Prima il codice era duplicato
    ~80% fra `preventivi_service` e `contratti_service`; ora entrambi i service
    importano dal BB. Censito in [catalogo BB](../backend/catalogo-building-block-backend.md)
    sezione "Vendite — Gate autorizzazioni prezzi"
- ✅ **Debito tecnico §7.6 CHIUSO (2026-05-19)**: i 3 gate (L1 + L2 + L3) sulle
  righe contratto sono invocati in `contratti_service.create_riga` /
  `update_riga` via helper `_apply_pricing_gate_riga` (refactor + estrazione
  duplicazione). Decisione di dominio applicata: **Alternativa B**
  (OVERRIDE → L1+L2+L3 sempre; AGGIUNTA → L1 sempre, L2/L3 condizionali al
  resolver; ESCLUSIONE → skip totale). Workflow L3 simmetrico ai preventivi
  via `approvazioni_prezzo_service` sorgente-agnostico (`_SORGENTE_CONFIG`).
  Endpoint approva/rifiuta dedicati `/righe-contratto/<id>/...`. Dettagli §7.8.
- Da produrre durante l'esecuzione:
  - ✅ **`modello-contratti.md`** prodotto in `docs/it/backend/vendite/manual/` — reference
    del modello unificato + glossario (§9)

---

## 7. Attività svolte (2026-05-15)

Refactor chiuso end-to-end. Le sessioni hanno seguito il piano operativo §5 con
parallelizzazione massima sui prerequisiti DB.

### 7.1 DB (team DB su `dev/db-tid`)

- **Fase 1**: estensione cascata parametri con `categoria_cliente_id` (`config.parameter_overrides`
  + `script.fn_get_parameter_full` 7 parametri; cascata
  `user → categoria_cliente → group → emittente → session → function → default`)
- **Fase 2**: schema `vendite.contratti` con `listino_versione_id`; enum `tipo_eccezione`
  su `vendite.contratti_righe` (OVERRIDE/ESCLUSIONE/AGGIUNTA) + CHECK coerenza prezzo +
  UNIQUE parziali; trigger freeze versione listino al passaggio DRAFT→ATTIVO;
  trigger lock post-attivazione su testata e righe; trigger guard AGGIUNTA fuori-listino;
  riscrittura `fn_resolve_prezzo_listino_v2` per 3 tipi eccezione + lettura versione fissata;
  drop trigger/CHECK/parameter modalità legacy
- pgTAP: 70+ test su tutti gli step, 100% verdi
- Migrations: `20260515-06..16`

### 7.2 BE (`dev/backend-tid`)

- **`ParameterService` + repo** estesi con `categoria_cliente_id` (4 metodi pubblici)
- **`BillingAccountRepository.get_categoria_cliente_id`** nuovo BB
- **`preventivi_service`**: gate L2 propaga categoria; lookup BA post-early-return per
  evitare round-trip su superuser/delta=0
- **`PricingLimitiUtenteView`**: accetta query param `billing_account_id`
- **`contratti_service`**: rimozione `_validate_modalita_coerente` (→ `_validate_variazione_globale_coppia_coerente`);
  `list_righe_preview` ritorna `forma`; gestione 3 tipi eccezione con coerenza prezzo/tipo;
  blocco rimozione listino con eccezioni OVERRIDE/ESCLUSIONE (422); gate L2 sulla
  variazione globale al PATCH testata (PERCENTUALE only)
- **`contratti_repository`**: query `list_righe_preview` riscritta per versione listino
  fissata + 3 tipi eccezione; nuovo `resolve_contesto_pricing_contratto`; nuovo
  `count_eccezioni_bloccanti`; schema SELECT con `listino_versione_id`/`tipo_eccezione`
- **`views_contratti`**: nuovo endpoint `GET /api/v1/vendite/contratti/<id>/contesto-pricing/`
  con schema OpenAPI completo; `tipo_eccezione` come `ChoiceField` nello schema riga
- **`error_policies.py`**: 5 nuovi codici (`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`,
  `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`, `E_ARTICOLO_ESCLUSO_DA_CONTRATTO`,
  `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`, `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`);
  marker substring DB aggiornati; vecchi codici `MODALITA_C_*` rimossi
- **Cleanup**: drop lookup `modalita-pricing-contratto` (endpoint + service + URL + test)
- **BB estratto**: `apps/vendite/services/_pricing_gate_helpers.py` con 3 fn pubbliche
  (`check_permesso_override_prezzo`, `check_limite_variazione_prezzo`,
  `check_limite_variazione_globale`); preventivi+contratti importano dal BB; test mock
  path aggiornati

### 7.3 FE (`dev/backend-tid`)

- **`ContrattoDrawer.vue`**: SelectButton modalità A/B/C rimosso; sezione "Pricing"
  semplificata (Listino opzionale + Variazione globale opzionale); badge
  `forma_<derivata>` readonly post-save; `lookupModalitaPricingContratto` droppato
- **`ContrattoRigheDrawer.vue`**: prop `contrattoForma` (fix recap §3.2: default 'B'→null);
  banner contesto pricing nell'header (forma + listino + versione fissata + categoria);
  Select `tipo_eccezione` in CREATE + Tag readonly in EDIT (immutabile); coerenza
  prezzo/tipo nel form e nel `canSave`; `previewMeta.modalita`→`previewMeta.forma`;
  `isModalitaC`→`isSenzaListino`
- **`getContrattoContestoPricing`** nuovo client API
- **`useLimitiPricing`**: cache per-BA (no leak cross-BA); `getLimitiPricingUtente`
  accetta `billing_account_id`; `PreventiviRigaForm` propaga BA del preventivo
  (fix doppio fetch in review critica)
- **i18n**: +14 key (`forma_*_descrizione`, `contesto_*`, `tipo_eccezione_*`,
  `field_tipo_eccezione`, `prezzo_esclusione_n_a`, azioni); rimosse legacy
  `modalita_*` e `field_modalita`
- **Handling 5 nuovi codici errore**: gestito dal middleware `error_policies` →
  toast automatici via `useApiHandler` (zero codice FE specifico)

### 7.4 DOC

- ✅ `api_contratti.md` reworked: modello unificato, snapshot versione, 3 tipi eccezione,
  contesto-pricing, 5 nuovi codici, regole Profilo A + coerenza
- ✅ `modello-contratti.md` nuovo: doc di riferimento del modello + cascata parametri +
  glossario (§9)
- ✅ `api_preventivi.md` (Fase 1): sezione L2 con cascata estesa categoria
- ✅ `api_pricing.md` (Fase 1): query param `billing_account_id`
- ✅ `ai-context.md`: voce "Contratto" aggiornata + transizione DRAFT→ATTIVO con nuovo guard
- ✅ Catalogo BB backend: `ParameterService` cascata estesa + `BillingAccountRepository.get_categoria_cliente_id`
  + nuova sezione "Vendite — Gate autorizzazioni prezzi" (3 fn BB); drop lookup modalità
- ✅ Catalogo BB frontend: aggiunto `getContrattoContestoPricing`; drop `lookupModalitaPricingContratto`
- ✅ Brief DB completo aggiornato a fine corsa con note BE+FE chiuse

### 7.5 Risultati test

- **BE**: 2400/2400 verdi (suite completa)
- **FE**: build vite verde (1.14s, zero errori)
- **DB**: pgTAP 70+ test verdi (tutti gli step DB)
- **+9 nuovi test mirati** sui flussi contratto post-refactor

### 7.6 Debito tecnico residuo — CHIUSO 2026-05-19

> **Stato: chiuso 2026-05-19.** Wiring gate riga contratti completato dopo
> consegna DB simmetria L3 (migrations `20260518-01` schema +
> `20260518-02` trigger guard_pending). Vedi §7.8 sotto.

I 3 gate prezzo (L1 + L2 + L3) sulle **righe** contratto sono ora invocati
in `contratti_service.create_riga` e `contratti_service.update_riga`.

### 7.7 Attività svolte (2026-05-18) — chiusura decisioni minori

Dopo la chiusura del refactor maggiore (sezioni 7.1–7.6), 3 decisioni rimanenti
sono state prese e implementate end-to-end nella stessa sessione (BE+test+doc):

- **§3-bis-E — `VALORE_FISSO` vietato come variazione globale**:
  - `_TIPI_VARIAZIONE_GLOBALE_AMMESSI = frozenset({"PERCENTUALE"})` in `contratti_service.py`
  - `_apply_variazione_globale` rifiuta VALORE_FISSO con messaggio parlante
    (cita il caso d'uso "OVERRIDE su riga" come alternativa)
  - Lookup FE `tipi_variazione_contratto` aggiornato a solo PERCENTUALE
  - Test BE: `test_update_contratto_variazione_valore_fisso_rifiutata` +
    `test_update_contratto_ok_variazione` aggiornato a PERCENTUALE
  - Test API: `test_tipi_variazione_contratto_ok` aggiornato

- **§4.4 — listino senza versione ATTIVA non selezionabile**:
  - `ListiniRepository.has_versione_attiva(listino_id) -> bool` (EXISTS single
    round-trip su `vendite.listini_versioni` stato='ATTIVA' + attivo IS TRUE)
  - `ContrattiService._guard_listino_ha_versione_attiva` invocato in
    `_build_create_data_testata` e `_build_update_data_testata` quando
    `listino_id` è valorizzato (skip in PATCH quando `listino_id` non è nel patch
    per non invalidare contratti esistenti)
  - Nuovo codice errore `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (422) registrato
    in `error_policies.py` con messaggio parlante per banner FE
  - Test: `test_create_contratto_listino_senza_versione_attiva_rifiutato`
  - **Open task** (separato da questo refactor): filtro lookup FE
    `vendite.listini` per mostrare solo listini con versione attiva. Richiede
    brief DB (modifica whitelist `dbops.fn_get_lookup_codici` o nuovo endpoint
    dedicato). Stima: 1h DB + 30 min FE swap dell'endpoint.

- **Nome permesso "variare prezzi"**:
  - Label UX e doc aggiornata in `refactor-contratti-modalita.md` +
    `gestione-contratti.md`
  - Codename DB del permesso resta `prezzo_override_manuale` (stabile, niente
    rename DB invasivo). Il binding tecnico è invariato; solo la presentazione
    cambia.

**Test BE post-decisioni**: 711/711 verdi. Diff netto rispetto alla suite
precedente: 1 nuovo test rifiuto VALORE_FISSO, 1 nuovo test rifiuto listino
senza versione attiva, 1 duplicato di
`test_create_contratto_variazione_coppia_incompleta_fallisce` rimosso.

### 7.8 Attività svolte (2026-05-19) — chiusura debito tecnico §7.6

Dopo la consegna del DB con la simmetria L3 su `vendite.contratti_righe`
(brief `brief-db-contratti-righe-approvazione-prezzo-simmetria-l3.md`,
migrations `20260518-01` schema + `20260518-02` trigger guard_pending),
il backend ha chiuso il debito tecnico cablando i 3 gate prezzo (L1+L2+L3)
in `ContrattiService.create_riga` e `update_riga`. Decisione di dominio
applicata: **Alternativa B** confermata 2026-05-18 (OVERRIDE → gate sempre;
AGGIUNTA → L1 sempre, L2/L3 condizionali al resolver; ESCLUSIONE → skip).

- **BE — refactor sorgente-agnostico** `approvazioni_prezzo_service`:
  - Costanti: `META_KEY_RIGA_CONTRATTO_ID`, `META_KEY_SORGENTE`,
    `SORGENTE_PREVENTIVO`, `SORGENTE_CONTRATTO` in `_approvazioni_prezzo_constants.py`
  - `_SORGENTE_CONFIG` whitelist `{preventivo, contratto}` con `table`,
    `doc_fk_column`, `meta_key_riga/doc`, error codes; `_require_sorgente`
    validate + `_update_riga_workflow` dispatch fra firme repo diverse
    (`PreventiviRepository.update_riga(**kwargs)` vs
    `ContrattiRepository.update_riga(dict)`)
  - `_crea_richiesta_approvazione_impl` privato parametrizzato; wrapper
    pubblici `crea_richiesta_approvazione` (preventivi, back-compat firma
    Sprint E) + `crea_richiesta_approvazione_contratto` (nuovo)
  - `approva`/`rifiuta`/`_get_riga_pending`/`link_riga_a_pratica` con
    parametro keyword `sorgente` (default preventivo per back-compat)
  - `_capabilities_per_pratica` legge `META_KEY_SORGENTE` dal meta della
    pratica; espone `sorgente` nel payload coda per routing FE endpoint

- **BE — `ContrattiService`**:
  - `create_riga` invoca `resolve_or_check_override_prezzo_riga_contratto`
    PRIMA della transazione DB per tipi OVERRIDE/AGGIUNTA. Skip totale
    per ESCLUSIONE. Workflow L3: se `richiesta_approvazione=true` nel
    payload e gate L2 viola, crea pratica via
    `_orchestrate_l3_request_contratto`, popola
    `stato_approvazione_prezzo='PENDING'` + `pratica_approvazione_prezzo_id`
    nel data riga, salva, e fa `link_riga_a_pratica` post-INSERT
  - `update_riga` con parametro `auth_user_id`: gate scatta solo se PATCH
    tocca `prezzo_unitario` su riga OVERRIDE/AGGIUNTA. `existing_riga`
    riusato fra coerenza prezzo/tipo e gate (no double-fetch)
  - `_orchestrate_l3_request_contratto` module-level simmetrico al pattern
    `preventivi_service._orchestrate_l3_request`

- **BE — `ContrattiRepository`**: whitelist `create_riga`/`update_riga`
  esposta a `stato_approvazione_prezzo`+`pratica_approvazione_prezzo_id`;
  `_SELECT_COLS_RIGA` proietta le 2 colonne; nuovo
  `resolve_contesto_pratica` simmetrico al pattern preventivi

- **API — nuovi endpoint dedicati righe contratto**:
  - `POST /api/v1/vendite/righe-contratto/<riga_id>/approva-prezzo/`
  - `POST /api/v1/vendite/righe-contratto/<riga_id>/rifiuta-prezzo/`
  - View `ApprovaPrezzoContrattoView` / `RifiutaPrezzoContrattoView` thin
    wrapper sul service con `sorgente=SORGENTE_CONTRATTO`. Path distinti
    per evitare ambiguita' su riga_id (preventivi e contratti hanno
    sequence indipendenti)
  - `PATCH /api/v1/vendite/contratti/<id>/righe/<riga_id>/` ora passa
    `auth_user_id` al service per il gate L1

- **Test**: 721/721 vendite verdi (+8 nuovi mirati). Suite globale BE
  2423/2423 verdi.
  - `test_create_riga_override_invoca_gate`
  - `test_create_riga_esclusione_skip_gate`
  - `test_create_riga_l3_richiesta_approvazione_pending`
  - `test_create_riga_aggiunta_senza_base_resolver_skip_l2`
  - `test_update_riga_override_invoca_gate`
  - `test_update_riga_skip_gate_se_prezzo_non_in_patch`
  - `test_approva_riga_contratto_dispatch_contratti_repo`
  - `test_rifiuta_riga_contratto_dispatch_meta_motivazione`

- **Doc**: `api_contratti.md` §"Workflow autorizzazioni prezzo L1+L2+L3"
  con matrice tipo_eccezione → gate + endpoint approva/rifiuta contratto;
  `catalogo-building-block-backend.md` con nuove fn sorgente-agnostiche +
  `_SORGENTE_CONFIG` / `_update_riga_workflow`.

### 7.9 Attività svolte (2026-05-19) — chiusura FE 2.3 CTA Richiedi approvazione

Chiusura UX simmetrica al pattern preventivi (`PreventiviRigaForm.vue`).
Lo schema FE è ora completo end-to-end: un OVERRIDE/AGGIUNTA che viola L2
mostra banner inline con bottone "Richiedi approvazione" che retry il save
con `richiesta_approvazione=true` (BE crea pratica + riga PENDING).

- **`ContrattoRigheDrawer.vue`**:
  - `buildRigaPayload({extra}={})` centralizza la build del payload (usata
    da onSave e da onRichiediApprovazione)
  - `onSave` intercetta i codici L2 (`E_PRICING_SCONTO_ECCESSIVO`,
    `E_PRICING_MAGGIORAZIONE_ECCESSIVA`) via `extractApiErrorCode` e
    setta `l2Error.value` invece del toast standard (gli altri errori
    restano sul toast generico)
  - `onRichiediApprovazione` rilancia il save con `richiesta_approvazione=true`
    e mostra toast esplicito sulla riuscita
  - Watch reset di `l2Error` su cambio prezzo/articolo
  - Template: `<Message v-if="l2Error">` con CTA `<Button>` "Richiedi
    approvazione" + spinner durante il retry
  - Import nuovi: `useNotify`, `useLimitiPricing` (riusa `L2_ERROR_CODES`),
    `extractApiError`/`extractApiErrorCode`

- **i18n** (it + en): 5 chiavi `contratti.*` mutuate da `preventivi.*`:
  `richiedi_approvazione`, `richiedi_approvazione_in_corso`,
  `richiedi_approvazione_tooltip`, `richiesta_approvazione_inviata`,
  `errore_generico`.

Test/Build: BE 2423/2423 verdi, build vite verde 1.03s. Refactor di
deduplicazione fra preventivi e contratti possibile in futuro (oggi
i due Vue replicano lo stesso pattern; quando emergera' un terzo
caller, valutare l'estrazione in composable `useL2RetryWorkflow`).
