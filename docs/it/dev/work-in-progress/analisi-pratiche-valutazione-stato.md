# Analisi — Valutazione dello stato della Gestione Pratiche

> **Tipo**: analisi strategica / di stato (non implementativa) · **Data**: 2026-07-01
> **Owner**: Tid · **Stato**: 🟢 aperta — documento **padre** da cui derivare i brief.
>
> **Origine**: sessione di *ragionamento libero* sullo stato del motore pratiche
> mentre si cerca di portare a termine la **pratica PREVENTIVI**. La sensazione di
> partenza dell'autore: «tutto si basa su un'ottima idea ma come la sto approcciando
> non mi convince — graficamente resta difficile da far capire a un operatore, e la
> configurazione dovrebbe essere più gestibile perché società diverse (persino gas
> vs idrico vs energia) gestiscono la stessa attività in modi diversi».
>
> **Natura del documento**: qui si raccolgono le **opinioni generali** e le **cose da
> valutare/rivalutare**. Non decide nulla: è la *lista degli spunti* da cui nascono i
> brief operativi (BE/FE/DB). Il primo brief generato da questa analisi è già pronto:
> [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md).
>
> **Documenti collegati**: [Guida Gestione Pratiche](../../guide/gestione-pratiche.md),
> [Gestione Pratiche — Configurazione](../../guide/gestione-pratiche-configurazione.md),
> [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md),
> [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md),
> [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md).

---

## 0. In una frase

Il **motore** pratiche non è il problema: è la parte più forte del sistema. Il dubbio
che si prova è il fenomeno normale che colpisce *ogni* piattaforma di processo — lo
**scarto fra un motore corretto e un prodotto comprensibile**. La cura non è rifare il
motore: è **costruire i due strati che gli mancano sopra** (l'esperienza dell'operatore
e gli strumenti di configurazione), e smettere — per un po' — di aggiungergli manopole.

---

## 1. Lettura umana dello stato (prima di ogni tecnicismo)

Va detto con chiarezza, perché conta per decidere bene: quello che è stato costruito
**non è un'idea buona approcciata male**. È un workflow engine serio. Macchina a stati
guidata da configurazione (una nuova transizione è un `INSERT`, non un deploy), giornale
immutabile alimentato dai trigger, sospensioni con propagazione, calcolo automatico dei
tempi/SLA, generazione di pratiche a cascata, dispatch verso handler di dominio con
registry, esito dello step configurabile con guard che spiegano l'errore, binding
evento→handler, aggancio parametrico ai documenti versionati. È tanto, ed è fatto bene.

Quindi la sensazione di «non sto facendo un buon lavoro» **non nasce da un difetto del
motore**. Nasce da un fatto strutturale: il motore è ormai abbastanza completo da far
vedere che *sopra* di lui manca qualcosa. Il dubbio è un **segnale di maturità del
progetto**, non di fallimento. Arriva sempre nel momento in cui l'infrastruttura è
pronta e ci si accorge che tradurla in uno strumento che una persona capisce, e che una
seconda azienda può configurare a modo suo, è un lavoro **diverso** — non un'estensione
del motore, ma due strati nuovi.

Una diagnosi onesta, da tenere presente in tutte le valutazioni che seguono: **il motore
è oggi sovra-costruito rispetto ai due strati che gli stanno sopra.** Guardando gli
ultimi mesi, quasi tutta l'energia è andata nel motore (esito configurabile, esiti
data-driven, prerequisiti esito-aware, handler-eventi, assegnazione, binding
smistamento…): ognuno giusto, ma tutti *dentro* il motore. Il rischio è che la prossima
manopola *sembri* progresso senza spostare di un millimetro le due cose che fanno davvero
dubitare: **un operatore lo capisce?** e **un non-sviluppatore lo sa configurare?**

---

## 2. La nebbia sono tre problemi distinti

Il malessere è vissuto come uno solo, ma sono **tre problemi di tre livelli diversi**.
Separarli è già metà della cura, perché due dei tre **non si toccano nemmeno col motore**.

### 2.1 Problema 1 — L'operatore non deve *mai* vedere «il flusso» (presentazione)

È un problema di **presentazione**, non di motore. La risposta è già stata scritta
dall'autore stesso in [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md):
*«la pratica non deve divergere dal programma standalone»*. Portato fino in fondo:
parole come *flusso, template, prerequisito, modalità esito, direzione, handler* sono
**vocabolario da idraulico**; l'operatore non deve incontrarle mai. Lui pensa «mi è
arrivata una richiesta, cosa faccio adesso?». La pratica, in UI, non è una macchina a
stati: è **un racconto con un solo pulsante attivo**, che apre *le stesse schermate che
l'operatore già conosce*.

Questo problema è stato **misurato** (sessione 2026-07-01, superfici FE reali) e il
risultato è più preciso e più economico del temuto: il vocabolario da motore trapela
davvero, **peggiora con la profondità** (l'ingresso "Le mie attività" è quasi pulito, la
vista *Percorso* — che dovrebbe essere il racconto — è la più leaky), ed è **economico
da chiudere** perché le etichette umane (`descrizione`) esistono già nel dato e non
vengono renderizzate. Dettaglio, evidenze e piano nel brief:
[brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md).

### 2.2 Problema 2 — La variazione fra aziende non ha un asse su cui appoggiarsi (architettura)

È il **vero buco architetturale**, ed è concreto. Verificato sul modello vivo:
[`pratiche.template_flussi`](../../dbzero/pratiche/tabelle/template_flussi.md) pende da
`tipo_prestazione_id` e **non ha `emittente_fiscale_id`**;
[`pratiche.tipi_prestazione`](../../dbzero/pratiche/tabelle/tipi_prestazione.md) è
condiviso fra tutti gli emittenti. Solo l'**istanza**
([`pratiche.pratiche`](../../dbzero/pratiche/tabelle/pratiche.md)) è segregata per
azienda. Tradotto: **oggi la società A e la società B non possono avere due workflow
"preventivi" diversi per lo stesso tipo prestazione.** L'unica via è clonare l'intero
tipo (`PREVENTIVI_A`, `PREVENTIVI_B`), che è il pattern brutto.

Ecco perché lo scenario utilities (gas/idrico/energia che fanno *la stessa attività in
modo leggermente diverso*) fa sentire che qualcosa non torna: **è corretto tecnicamente,
non è insicurezza.** La variazione fra aziende **è dato, non codice** — e *questa* è la
parte giusta del design — ma **manca l'asse** su cui appoggiare quel dato. Le
sotto-decisioni vere (da valutare, non da decidere qui):

- **come compone l'override**: un override per-azienda *sostituisce* l'intero set di step
  o fa *patch* di singoli step/parametri sul default globale?
- **cosa succede alle istanze in volo** quando la definizione cambia mentre ci sono
  pratiche aperte (versionamento del template)?
- **il default (globale) È il preset**: il preset non è un concetto nuovo, è il template
  con `emittente = NULL`.

Nota di layering: l'asse va progettato **rispettando l'agnosticità dell'Anello 2**
(il motore fornisce il *meccanismo* di scoping; non conosce la semantica dei domini).
Non è greenfield: esiste già l'infrastruttura di scope multi-company
(`script.trgfn_guard_emittente_scope`, RLS operatori).

### 2.3 Problema 3 — Gli strumenti di configurazione, e l'analogia con l'AI da correggere (governo)

Oggi *ogni* modifica al workflow è un changeset Liquibase (guida configurazione §6):
non si può chiedere all'admin della società A di scrivere SQL. Servono davvero (a) uno
strumento per **capire le opzioni** e (b) un modo per **crescere senza rompere**.

Sull'idea «l'AI ha milioni di parametri, qui parliamo di migliaia, sarà più facile»: è
giusta sulla direzione (parametrizzare come **dato** è la strada scalabile, e il *numero*
non è il muro) ma fuorviante su *dove* sta la difficoltà. Nell'AI i parametri sono
**appresi automaticamente e nessun umano ne capisce uno**. In un sistema di
configurazione **ogni parametro deve essere capito, scelto e mantenuto da una persona**
— l'admin dell'azienda. Quindi il limite di scala non è lo storage né il conteggio: **è
la comprensione umana.** Un workflow con 40 manopole che nessuno capisce è *peggiore* di
uno con 6 scelte bene. L'obiettivo di design si ribalta: non «più parametri», ma
**rendere lo spazio delle opzioni leggibile e sicuro** — default sensati + opzioni
avanzate nascoste (progressive disclosure), guard rail (che *già ci sono*: `esito_default`
obbligatorio, `AUTOMATICO` solo `INTERNA`, FK verso i vocabolari) e **preset** da cui
partire invece del foglio bianco.

E *qui* l'AI serve davvero — non come architettura, ma come **copilota di
configurazione**: «descrivi a parole come la tua azienda gestisce i preventivi» → l'AI
propone un seed di `template_flussi` + prerequisiti → lo mostra come diagramma → l'admin
corregge. Il modello è **dichiarativo e con guard rail**: è il substrato *perfetto*
perché un LLM generi la configurazione e il DB scarti da solo le combinazioni illegali.

---

## 3. La strategia di prodotto proposta: convenzione con vie di fuga

La risposta alla domanda «gas ≠ idrico ≠ altri settori, sto chiedendo l'impossibile?» è
**no** — ma c'è una trappola e una disciplina.

- **La trappola**: rendere *un* workflow configurabile abbastanza da coprire ogni azienda
  a forza di manopole → esplosione combinatoria, ingestibile, UX incomprensibile (il
  Problema 1 e il 3 si avvitano a vicenda).
- **La disciplina**: **preset opinionati per settore** («preventivi utilities»,
  «preventivi generico») — ognuno un *punto curato* nello spazio di configurazione, cioè
  le "scelte comuni" verso cui si vuole veicolare — più **fork guard-railed** per
  l'azienda che deve discostarsi. Il preset **è** il vincolo; il fork è la valvola che
  impedisce al vincolo di rompersi contro la realtà. È come ServiceNow/Salesforce/Odoo
  sopravvivono allo *stesso* problema: motore piccolo e stabile + catalogo di template
  opinionati + personalizzazione con paletti + UI a scoperta progressiva.

Si ha già il motore e i guard rail. Mancano **l'asse preset/override** (Problema 2) e
**la UI** (Problema 3).

---

## 4. Cose da valutare / rivalutare (la lista degli spunti → futuri brief)

Ogni voce è un candidato brief. Priorità = *dove conviene mettere la prossima unità di
sforzo*, non urgenza assoluta.

| # | Tema | Cosa valutare | Tipo | Priorità | Brief |
|---|---|---|---|---|---|
| **V1** | **Comprensibilità operatore** | Il *Percorso* è un debugger della macchina a stati, non un racconto; il lessico da motore trapela. Trasformarlo in "sei qui / prossimo passo / un pulsante". | FE (+ display fields BE) | 🔴 alta | ✅ [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md) |
| **V2** | **Variazione per azienda** | Asse `emittente`/override sui workflow (oggi i template sono globali). Le tre sotto-decisioni §2.2. La decisione a più alta leva. | Design → DB | 🔴 alta (strategica) | da generare |
| **V3** | **Preset per settore + fork** | Formalizzare "convenzione con vie di fuga" (§3): cosa è preset, cosa è fork, quali paletti. Inquadra V2 e V4. | Design | 🟠 media-alta | da generare |
| **V4** | **UI di amministrazione workflow** | Oggi solo seed Liquibase. Serve editor/ispettore (anche solo read-only all'inizio) che renda visibili gli step, i prerequisiti, gli esiti. | FE + BE | 🟠 media | da generare |
| **V5** | **Discoverability delle opzioni** | "Capire le opzioni possibili": il §5 della guida configurazione è già la specifica di questa vista. Può nascere gemella di V4 (ispettore read-only). | FE | 🟡 media | da generare |
| **V6** | **Estensibilità senza rotture** | Versionamento delle definizioni: cosa accade alle pratiche aperte quando un template cambia. Emerge inevitabilmente con V2. | DB + design | 🟡 media | da generare |
| **V7** | **AI copilota di configurazione** | L'AI genera/valida il seed dei workflow dal linguaggio naturale, sopra il modello dichiarativo + guard. Visione, non ora. | Visione | 🟢 futura | nota |
| **V8** | **Bilanciamento dello sforzo** | Regola di metodo: *fermarsi ad aggiungere manopole al motore* finché lo strato-prodotto (V1/V4) non recupera. Trasversale a tutto. | Metodo | — | (principio) |
| **V9** | **Uniformità pratica ⇄ standalone** | Già in corso ([analisi-uniformita](analisi-uniformita-pratica-preventivi.md)). Confermarlo come principio guida **anche per la UX** (V1 ne è un corollario). | Design | (in corso) | esistente |

---

## 5. Metodo e sequenza consigliata

1. **V1 prima di tutto.** È già misurato, costa poco nel 70% (lessico + fonte-dato) e
   affronta il 30% strutturale (la vista-racconto) su *un* workflow che già gira
   end-to-end (PREVENTIVI). O dissolve il dubbio, o mostra *esattamente* quale assunzione
   del motore è sbagliata — a costo molto più basso che indovinarlo a tavolino.
2. **Poi V3 (strategia) prima di V2 (implementazione).** Decidere "preset + fork" come
   forma prima di committare l'asse per-azienda al buio.
3. **V2 e V4/V5** a seguire; **V6** emerge insieme a V2; **V7** resta visione.
4. **V8 come guardrail continuo**: ogni proposta di nuova manopola di motore passa prima
   la domanda «questo aiuta l'operatore o l'admin, o solo il motore?».

> Nota sul lavoro in corso (2026-07-01): il cantiere `config.esiti_flussi_pratiche`
> (esiti data-driven per il bivio SMISTAMENTO) è **architetturalmente corretto** — «il
> motore fornisce il meccanismo, i domini seedano i valori» — e va finito. È citato qui
> solo come esempio del *pattern* §1 (energia nel motore): giusto in sé, ma da bilanciare
> con lo strato-prodotto. Bonus: la sua colonna `descrizione` è **esattamente** ciò che il
> FE dovrà renderizzare per gli esiti (vedi brief V1).

---

## 6. Come nascono i brief da questo documento

Questo file è la **sorgente**. Per ogni voce §4 che si decide di affrontare:

1. si apre un brief in `work-in-progress/` (`brief-fe-*`, `brief-be-*`, `brief-db-*`,
   `brief-design-*` secondo il perimetro);
2. il brief eredita da qui **problema + principio**, e aggiunge **evidenze, deliverable e
   piano**;
3. a chiusura, il brief si sposta in `work-done/` e la riga §4 corrispondente si aggiorna.

*Documento vivo: aggiornare la tabella §4 a ogni brief generato o chiuso.*
