# Analisi — Pratiche come container di processo: integrazione domini Anello 3

> **Stato**: ANALISI infrastrutturale, nessuna decisione operativa, nessun brief DB
> ancora scritto. Documento di consolidamento delle convenzioni di aggancio fra
> motore `pratiche` (Anello 2) e processi di Anello 3 (`vendite`, `acquisti`,
> `magazzino`, ...).
>
> **Data**: 2026-05-18 (rev. 2026-05-19 — integrazione critica e decisioni
> aggiuntive)
>
> **Owner concettuale**: Tid (Michele Carlo Titini). L'analisi nasce dalla domanda
> "come iniziamo a integrare preventivi e ordini nelle pratiche?" e risponde con
> una **base generale**: tutto ciò che vale per preventivi+ordini deve valere
> domani per CRM, assistenza, acquisti, magazzino — senza riscrivere il motore.
>
> **Cosa NON è questo documento**:
>
> - non è un brief DB (nessun DDL, nessun seed pronto da applicare)
> - non è il piano operativo della prima integrazione (quello viene dopo, sulla
>   base di questa analisi)
> - non è una modifica di `pratiche-v2`: estende v2 con il piano di integrazione
>   cross-dominio e indica come v2 stessa diventa pienamente validata
>
> **Riferimenti incrociati obbligatori**:
>
> - [sviluppo-concentrico.md](../../sviluppo-concentrico.md) — §III bis: dipendenza
>   non è ordine di costruzione, anelli di servizio si decantano sui consumatori
> - [mappa-concentrica.md](../../mappa-concentrica.md) — §Anello 2: pratiche è
>   *predisposta, in attesa di validazione*. §Caso di studio: pratiche prima di
>   vendite
> - [gestione-pratiche-v2.md](gestione-pratiche-v2.md) — modello operativo
>   pratiche v2 (fasi 1-7 DB+BE+FE)
> - [Guida Gestione Pratiche](../../guide/gestione-pratiche.md) — semantica
>   tipi_prestazione, template_flussi, handler, generazione cross-pratica
> - [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md) — pattern già aperto
>   per assistenza/CRM, qui generalizzato
> - [Analisi-iniziale-offerta-commerciale.md](Analisi-iniziale-offerta-commerciale.md)
>   — futuro asse `offerta_commerciale → contratto`, distinto da preventivo→ordine
> - [pratiche_sorgenti](../../dbzero/pratiche/manual/pratiche_sorgenti.md) — tabella
>   ponte M:N esistente

---

## 1. Inquadramento

### 1.1 Cosa esiste già

Il motore `pratiche` v2 (mappa concentrica 4 maggio 2026) ha:

| Capacità                  | Componente                                                                                                   | Stato                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------- |
| Catalogo workflow         | `pratiche.tipi_prestazione` + `pratiche.template_flussi` (+ prerequisiti, canali, handler)                   | Operativo                   |
| Istanza operativa         | `pratiche.pratiche` + `pratiche.flussi`                                                                      | Operativo                   |
| Macchina a stati          | `config.transizioni_stati_pratiche` + `config.transizioni_stati_flussi_pratiche` (config-driven, trigger DB) | Operativo                   |
| Giornale di bordo         | `pratiche.giornale` (append-only, alimentato da trigger)                                                     | Operativo                   |
| Generazione cross-pratica | `pratiche.regole_generazione` + `fn_genera_pratica_da_flusso`                                                | Operativo                   |
| Dispatch handler          | `pratiche.handler_flussi` (registry DB) + `HANDLER_MAP` Python                                               | Predisposto, registry vuoto |
| Sospensioni / SLA         | `pratiche.sospensioni` + `formule_tempo` + `calcoli_tempo`                                                   | Operativo                   |
| Coda lavoro 3 livelli     | `competenze_flussi` + `fn_coda_lavoro_operatore` + `fn_prendi_in_carico_flusso`                              | Operativo (dashboard)       |
| Ponte verso sorgenti      | `pratiche.pratiche_sorgenti` (M:N generico via `config.sorgenti`)                                            | Operativo                   |
| Note / allegati           | `note_pratiche` / `allegati_pratiche` + analoghi per flussi                                                  | Operativo                   |

Il motore è **completamente predisposto** per ricevere il primo consumatore di
Anello 3, ma nessun processo lo consuma ancora end-to-end. Il manifesto
§III bis e la mappa lo segnano esplicitamente come anello di servizio in attesa
di validazione.

### 1.2 Cosa cambia con questa analisi

Il rischio identificato nel caso di studio "pratiche prima di vendite": se
agganciamo vendite a pratiche con una soluzione ad hoc (es. solo per
preventivi), creiamo un debito immediato perché la stessa decisione andrà
ripresa al secondo consumatore. Quest'analisi mira a:

1. **Definire una sola volta** i tre pattern di aggancio dominio↔pratica
   (sorgente, handler, ext_*), in modo che siano riusabili senza modifiche per:
   vendite, assistenza (già pianificata in `crm-ticketing-pratiche.md`), CRM
   (futuro), acquisti, magazzino.
2. **Stabilire come la pratica diventa "container configurabile" di tutte le
   attività di un processo** — risposta diretta alla richiesta di Tid: "per
   tutte le attività dovremo abilitare la possibilità che tutto avvenga nella
   pratica". Vedi §5.8 per il principio generale di configurabilità che
   risolve questa richiesta.
3. **Stabilire come il giornale di bordo registra eventi cross-dominio** in
   modo uniforme, così che diventi la *vista unificata sulle attività
   dell'azienda* prevista nella mappa concentrica §Lungo termine, con
   l'onestà di dichiarare che questa proprietà è **condizionata al modello
   operativo configurato dall'azienda installatrice** (vedi §3.4).
4. **Identificare il caso di validazione**: vendite (preventivi + ordini) come
   primo consumatore reale, con criteri espliciti per riconoscere quando il
   motore si può promuovere a "contratto stabile" (manifesto §1) anziché
   "proposta in attesa" (§7).

### 1.3 Sviluppo concentrico: il vincolo metodologico

Il manifesto §III bis e la lezione "pratiche prima di vendite" impongono due
regole operative su questa analisi:

- **Non disegnare astrazioni che il dominio reale non ha ancora chiesto.** Se
  questa analisi propone un pattern (es. `ext_*`), deve emergere da almeno una
  necessità concreta del primo consumatore (vendite). Quello che oggi è
  ipotesi va marcato come tale, non come decisione presa.
- **L'astrazione si promuove al nucleo dopo due consumatori, non dopo uno.**
  Concretamente: i pattern in §2 saranno *predisposti* dopo l'integrazione
  vendite e *consolidati* solo quando il secondo consumatore (probabilmente
  acquisti o assistenza, in base alle priorità di business) li ri-eserciterà
  con requisiti identici.

Questa analisi è quindi una **mappa dei pattern candidati**, non una
specifica di contratto. La specifica nasce da brief DB successivi, uno per
ciascun pattern, dopo validazione su almeno un caso reale.

---

## 2. Tre pattern di aggancio dominio↔pratica

Quando un dominio di Anello 3 (vendite, acquisti, ecc.) deve essere "dentro"
una pratica, ha tre modi tecnicamente distinti — non in alternativa, ma in
combinazione, a seconda del legame semantico desiderato.

### 2.1 Pattern A — Sorgente (legame ponte M:N, legge i documenti esterni)

**Tabella**: `pratiche.pratiche_sorgenti` (già esistente, vedi
[manuale](../../dbzero/pratiche/manual/pratiche_sorgenti.md)).

**Semantica**: la pratica *cita* uno o più documenti esterni come fonte di
contesto. I documenti esterni vivono autonomi nel loro schema (vendite,
acquisti, ...) e mantengono il proprio ciclo di vita. La pratica li referenzia
tramite la coppia `(sorgente_tipo_id, sorgente_uid)` — la stessa coppia
generica già usata da `vendite.ordini` e `vendite.commesse_sorgenti` per
l'idempotenza import.

**Cardinalità**: M:N. Una pratica può puntare a più documenti di tipi diversi
(ROOT + COLLEGATI); un documento può apparire in più pratiche (es. lo stesso
preventivo come ROOT per una pratica vendita e come COLLEGATO per una pratica
post-vendita).

**Quando usarlo**:

- Il documento esterno esiste già in autonomia (preventivo creato dal
  PreventivoDrawer, ordine importato dal CRM esterno).
- Il legame è **referenziale informativo**: la pratica usa il documento per
  contesto/navigazione, ma non aggiunge dati specifici a quel documento dentro
  pratiche.
- Vale per più documenti di tipi diversi (es. una pratica VENDITA cita 1
  preventivo ROOT + 0..N ordini collegati).

**Pro**: pattern già implementato, generalizzato cross-dominio, nessuna
modifica al motore. Le sorgenti si seedano nella tabella `config.sorgenti` man
mano che nuovi tipi di documento entrano in scena.

**Contro / limiti**:

- È un puntatore: i metadati specifici del legame (es. "ho già spinto questo
  preventivo in ordine sì/no?", "qual è stato l'esito della negoziazione?") non
  hanno casa naturale qui — finiscono nel `meta JSONB` se servono, ma il JSONB
  non è indicizzabile né validabile a schema.

**Conseguenza pratica**: questo è il pattern di default per **ogni**
integrazione. Si sale di livello (al pattern C `ext_*`) solo quando il legame
ha dati propri abbastanza strutturati da meritare colonne dedicate.

### 2.2 Pattern B — Handler (automazione step dentro la pratica)

**Tabella + Python**: `pratiche.handler_flussi` (registry DB con `handler_key`
discriminatore) + `pratiche.template_flussi.handler_id` (campo opzionale sul
template) + `apps/pratiche/services/handler_registry.py` con `HANDLER_MAP:
dict[str, BaseFlussoHandler]`.

**Semantica**: un template_flusso può dichiarare un `handler_id`. Quando il
flusso istanziato passa in IN_CORSO, il service `pratiche.dispatch_handler`
chiama il metodo `execute(flusso_id, pratica_id, meta, handler_params)`
dell'handler corrispondente. L'handler vive nel **dominio chiamante** (es.
`apps/vendite/handlers/...`) ma è registrato nel registry pratiche per il
dispatch.

**Configurabilità**: due livelli (già richiamati nella guida pratiche §6.2):

| Livello  | Dove                                     | Quando si setta                              | Esempio                                                      |
| -------- | ---------------------------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| Statico  | `template_flussi.handler_params` (JSONB) | Configurazione del template                  | `{"fatturazione_trigger": "CONFERMATO"}`                     |
| Dinamico | `flussi.meta` (JSONB)                    | Runtime, da operatore o da flusso precedente | `{"preventivo_id": 4711, "modalita_consegna": "SPEDIZIONE"}` |

L'handler riceve entrambi e decide cosa fare. Cambiando solo
`handler_params` del template si ottengono varianti del processo **senza
toccare il codice**.

**Quando usarlo**:

- Un flusso deve produrre un effetto **lato dominio** (creare un preventivo,
  pushare un ordine in commessa, inviare un'email, scrivere su una tabella
  esterna).
- L'effetto è ripetibile, idempotente (vedi §6.9), e configurabile per
  template.

**Pro**: vocabolario condiviso (chi conosce pratiche conosce il pattern handler
ovunque); l'automazione cresce per registrazione, non per modifica del motore.

**Contro / limiti**:

- Il registry oggi è **vuoto**: la prima integrazione (vendite) deve
  registrare i primi handler reali e validare la firma di
  `BaseFlussoHandler`. Solo dopo il secondo handler in produzione il
  protocollo si stabilizza (manifesto §7).
- Gli handler **non sostituiscono** il dominio: un `PushPreventivoOrdineHandler`
  deve delegare a `vendite_service.crea_ordine_da_preventivo(...)`, non
  reimplementare la logica.

### 2.3 Pattern C — Estensione di pratica (`ext_<dominio>`, dati specifici 1:1)

**Tabella**: futura `pratiche.ext_<concetto>` (oggi solo design, vedi guida
pratiche §"Estensioni future"). Esempi candidati: `ext_appuntamento`,
`ext_sopralluogo`, `ext_comunicazione`, `ext_spedizione`.

**Semantica**: una specializzazione 1:1 (o 1:1 con flusso) di una pratica per
un concetto specifico, che porta colonne strutturate proprie del legame, non
del documento esterno. Tipico esempio: una pratica `ASSISTENZA_TECNICA` con
flusso `SOPRALLUOGO` ha un `ext_sopralluogo` con `data_pianificata`,
`tecnico_id`, `esito_dettagliato`, `coordinate_gps`. Questi dati non
appartengono a `pratiche.flussi.meta` (sarebbero schema-less e non
referenziabili) né a un dominio esterno (perché non sono *del* dominio, sono
*della pratica*).

**Quando usarlo**:

- Esiste un sottoinsieme di pratiche (per `tipo_prestazione` specifico) con
  dati strutturati propri che NON appartengono né al documento esterno (non è
  un preventivo) né al motore (non è un workflow primitivo).
- I dati hanno ricerche/filtri/vincoli a schema (es. `data_pianificata BETWEEN
  ...`, `UNIQUE(tecnico_id, slot)`).

**Quando NON usarlo (principio architetturale)**:

- **`ext_*` non duplica entità di dominio che vivono già in altri schemi.**
  Esempio sbagliato: `ext_preventivo`. Il preventivo è già `vendite.preventivi`
  con il suo ciclo di vita, le sue righe, i suoi vincoli. Creare un
  `pratiche.ext_preventivo` significherebbe avere una seconda casa per dati che
  hanno già una casa — anti-pattern classico, due verità parallele che prima
  o poi divergono.
- Se i dati appartengono a un documento esterno già esistente (preventivo,
  ordine, contratto): vivono lì, la pratica li cita con pattern A
  (`pratiche_sorgenti`).
- Se i dati sono pochi e occasionali: stanno in `meta JSONB` finché non
  emerge un secondo caso identico (criterio quantitativo di promozione in
  §6.5).

**Stato**: nessuna tabella `ext_*` esiste oggi. Andranno introdotte una alla
volta, **trainate** da casi concreti del dominio chiamante.

### 2.4 Risposta diretta al punto 3 del dialogo

Tid aveva chiesto: "non ho capito cosa intendi per `pratiche_sorgenti` vs
estensione di pratica".

In sintesi:

| Aspetto              | `pratiche_sorgenti` (pattern A)                             | `ext_<concetto>` (pattern C, futuro)                                                       |
| -------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Cosa lega            | Pratica ↔ documento esterno (preventivo, ordine, contratto) | Pratica ↔ dati specifici della pratica nel contesto di un concetto                         |
| Cardinalità          | M:N                                                         | 1:1 (o 1:1 con flusso)                                                                     |
| Dove vivono i dati   | Nello schema del documento (vendite.preventivi, ecc.)       | In `pratiche.ext_<concetto>`                                                               |
| Cosa registra        | "Questa pratica si riferisce al preventivo PRV-0042"        | Dati propri della pratica in un contesto specifico (appuntamento, sopralluogo, spedizione) |
| Modifica al motore   | Nessuna (tabella già esiste)                                | Aggiunta di una nuova tabella in `pratiche`                                                |
| Esempio legittimo    | Aggancio pratica VENDITA → preventivo + ordine              | `ext_appuntamento` con `data_pianificata`, `sede`, `esito_firma` per flusso di firma       |
| Esempio anti-pattern | —                                                           | `ext_preventivo`: duplicherebbe `vendite.preventivi`                                       |

**Per il caso vendite (preventivi+ordini) basta il pattern A.** Il preventivo
vive in `vendite.preventivi` con tutti i suoi dati. La pratica ci punta tramite
`pratiche_sorgenti`. Non c'è bisogno di alcun `ext_*` per il caso preventivo.

Se in futuro vorrai memorizzare, su una pratica `VENDITA`, qualcosa del tipo
"appuntamento di firma del preventivo presso il cliente" con data, sede, esito
firma, **quello** sarà candidato per `ext_appuntamento` legato al flusso —
non al preventivo, perché non è un dato del preventivo ma dell'appuntamento.

---

## 3. Giornale di bordo come backbone trasversale

Il giornale è candidato a essere la **vista unificata sulle attività
dell'azienda** annunciata nella mappa concentrica (§Lungo termine). Oggi è
già operativo come audit trail interno di pratiche/flussi; questa analisi
formalizza come diventa il canale unico cross-dominio, con un'importante
nota di onestà sulla qualità di questa proprietà (§3.4).

### 3.1 Cosa è già coperto

`pratiche.giornale` registra automaticamente, via trigger DB:

| Evento                                          | Origine                                |
| ----------------------------------------------- | -------------------------------------- |
| `PRATICA_CREATA`                                | trigger `trgfn_pratiche_giornale_ins`  |
| `STATO_CAMBIATO` (pratica)                      | `trgfn_pratiche_giornale_stato`        |
| `ASSEGNAZIONE_CAMBIATA`                         | `trgfn_pratiche_giornale_assegnazione` |
| `PRIORITA_CAMBIATA`                             | `trgfn_pratiche_giornale_priorita`     |
| `FLUSSO_CREATO` / `FLUSSO_STATO_CAMBIATO`       | `trgfn_flussi_giornale_*`              |
| `NOTA_AGGIUNTA` / `ALLEGATO_AGGIUNTO`           | `trgfn_note_*` / `trgfn_allegati_*`    |
| `SOSPENSIONE_REGISTRATA` / `SOSPENSIONE_CHIUSA` | `trgfn_sospensioni_giornale_*`         |

Tutti immutabili (append-only), correlati con `tx_id`, con `meta JSONB` libero
per dettagli specifici dell'evento.

### 3.2 Cosa serve per integrazione cross-dominio

Quando un handler (pattern B) compie un'azione lato dominio, l'evento *del
dominio* va riflesso nel giornale **della pratica** in modo standardizzato.
Esempio: l'handler `PushPreventivoOrdineHandler` crea l'ordine e deve
lasciare nel giornale un evento `DOMINIO_ORDINE_CREATO` con
`meta = {"ordine_id": ..., "preventivo_id": ..., "anno_serie_numero": ...}`.

Due opzioni di design considerate:

| Opzione                                                | Come                                                                                                | Pro                                                    | Contro                                                  |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------- |
| Estendere tipi evento giornale                         | Aggiungere voci a `config.tipi_eventi_giornale` (se esiste) o enum equivalente                      | Tutto in `pratiche.giornale`, una sola query temporale | I tipi crescono per dominio (proliferazione)            |
| Helper service `pratiche_service.log_evento_dominio()` | Wrapper applicativo che fa INSERT in giornale con tipo `DOMINIO_<EVENTO>` libero e meta strutturato | Nessun seed nuovo per ogni evento                      | I tipi non sono whitelist, validazione solo applicativa |

**Implementazione provvisoria** (2026-05-18, senza pretesa di stabilità
protocollare): il primo brief operativo (Fase B) userà l'**helper applicativo
libero** `pratiche_service.log_evento_dominio(pratica_id, flusso_id,
tipo_evento, meta)`, con tipo evento testuale convenzionato
(`DOMINIO_ORDINE_CREATO`, `DOMINIO_PREVENTIVO_ACCETTATO`, ...). Nessuna
whitelist DB iniziale.

Questa scelta è **esplicitamente provvisoria**: dopo i primi 3-4 eventi reali
registrati nell'uso effettivo si rivaluta se promuovere a tabella di
configurazione `config.tipi_eventi_giornale` (in coerenza con manifesto §7,
l'astrazione si decanta dal dominio reale, non si decide a priori). Nessuna
firma protocollare è considerata stabile prima di questa fase.

### 3.3 Eventi cross-dominio: convenzione di scrittura

Indipendentemente dall'opzione tecnica scelta, la convenzione semantica è:

- **L'evento si registra sul giornale della pratica**, non in un giornale di
  dominio separato. Il giornale di pratica è il backbone (con la riserva di
  §3.4).
- **Il record contiene `pratica_id` + `flusso_id` (se applicabile) + `tx_id`**,
  così la correlazione è completa.
- **`meta` JSONB include i riferimenti incrociati**: `ordine_id`,
  `preventivo_id`, `fattura_id`, `commessa_id`, ecc. — sempre con la stessa
  chiave per lo stesso concetto (vedi §6.8).

Risultato: un operatore che apre la pratica vede in giornale tutta la storia
end-to-end della pratica. Un report cross-pratica può cercare per
`meta->>'ordine_id'` ovunque, perché la chiave è la stessa.

### 3.4 Onestà sulla qualità del giornale come backbone

Il giornale è backbone **delle attività che sono nate dentro pratica**.
Questa è una proprietà condizionata, non intrinseca del software:

- Se l'azienda installatrice configura il proprio menù in modo che **tutte**
  le attività cross-dominio (preventivi, ordini, richieste assistenza, ecc.)
  nascano dentro pratiche (vedi §5.8), allora il giornale è effettivamente la
  vista unificata dell'attività aziendale.
- Se l'azienda lascia abilitati i punti di ingresso autonomi delle attività,
  i preventivi/ordini/ecc. nati fuori da pratica **non lasciano traccia nel
  giornale**. Il giornale rimane backbone delle sole attività strutturate.

Inoltre, in coerenza con §5.8.3, **un'attività nata fuori pratica non viene
mai retrofittata dentro una pratica successiva**: la sua storia resta fuori
dal giornale per sempre. Eventuali recuperi sono attività di consulenza
one-shot a carico del cliente, fuori dallo scope di ZeroERP come prodotto.

La qualità del giornale come "vista unificata sull'attività aziendale" è
quindi una **proprietà dipendente dalla configurazione operativa scelta**.
Va dichiarata onestamente nella documentazione utente: "configura le attività
per nascere dentro pratiche se vuoi un giornale completo".

### 3.5 Cosa il giornale NON è

Non è il sostituto della pipeline fatturazione (`vendite.fatture_log`,
`fatturazione_lotti_task_runs`). La distinzione è esplicita nella mappa §A3
("processi massivi mantengono la propria infrastruttura di tracking"):

- `pratiche.giornale` = eventi di **una** pratica singola.
- Pipeline fatturazione = eventi di **batch** (lotto, parallelismo,
  resume).

L'integrazione vendite deve rispettarla: un push commessa è un evento del
giornale-pratica (singolo); l'esecuzione del lotto fattura è evento della
pipeline (batch).

---

## 4. Configurabilità della pratica

Risposta diretta alla richiesta "pratiche devono avere massima
configurabilità". I quattro livelli di configurabilità del motore (questa
sezione tratta la configurabilità *interna* alla pratica; la configurabilità
*esterna* — esposizione delle attività nei menù aziendali — è in §5.8).

### 4.1 Livello catalogo — `tipi_prestazione` + `template_flussi`

Il dominio chiamante seeda i propri `tipi_prestazione` (es. `VENDITA_STANDARD`,
`ASSISTENZA_TECNICA`, `RICHIESTA_OFFERTA_CRM`) e i loro `template_flussi`
ordinati con prerequisiti. Niente codice, solo dati. Questo è il primo strato:
se vuoi un secondo processo simile ma diverso, copi/adatti la riga seed.

### 4.2 Livello template — `handler_params` JSONB

Su ogni `template_flusso` esiste `handler_params JSONB` (statico). È la
*configurazione del template*: se il flusso ha un handler associato, qui si
parametrizza il suo comportamento. Cambiando `handler_params` su un template
si ottiene una variante del processo senza scrivere codice.

### 4.3 Livello istanza — `flussi.meta` + `pratiche.meta` JSONB

`flussi.meta` è dato di istanza: viene popolato runtime dall'operatore o da un
flusso precedente. È il modo in cui il flusso N+1 riceve informazioni dal
flusso N. `pratiche.meta` è equivalente sulla testata.

### 4.4 Livello dispatch — `regole_generazione` cross-pratica

Quando un flusso completato deve generare automaticamente una nuova pratica
(es. "diagnosi tecnica negativa → apri pratica preventivazione"), si seeda
`pratiche.regole_generazione`. La generazione cross-pratica è già operativa
(`fn_genera_pratica_da_flusso`). Permette di **comporre processi** senza
hardcoding: ogni dominio dichiara i suoi "trigger di generazione" come dati.

### 4.5 Esempio didattico (provvisorio)

> **Nota**: l'esempio sotto è **didattico**, non un template implementativo.
> Il bivio reale del flusso `CONFERMA_VENDITA` deve gestire **preventivi
> misti** (righe con nature diverse: beni fisici + servizi + ricorrenti
> nello stesso preventivo), che il modello a `natura_vendita` di testata
> sotto rappresentato non regge. Vedi §5.3.2 per il modello corretto.

```text
template_flusso "CONFERMA_VENDITA" del tipo "VENDITA_STANDARD"
  handler_id = vendita.push_preventivo
  handler_params = {
    "fatturazione_trigger_default": "CONFERMATO"
  }

flussi.meta dell'istanza (popolato runtime)
  {
    "preventivo_id": 4711
  }

Handler PushPreventivoHandler:
  legge handler_params + flussi.meta
  determina lo split del preventivo per natura di riga (vedi §5.3.2)
  per ciascun sottoinsieme di righe genera la destinazione appropriata
  (ordine, commessa diretta, contratto)
  scrive in giornale gli eventi di dominio relativi
```

Tutti i bivi tipici del processo vendita sono casi configurabili tramite
combinazioni dei 4 livelli sopra. Il codice degli handler resta uno solo per
ciascuna azione; le varianti sono dati.

---

## 5. Caso di validazione: vendite (preventivi + ordini)

Questa sezione descrive il **primo consumatore reale** che valida i pattern
§2-§4. Non è il piano operativo definitivo — è la lettura del caso d'uso che
permetterà di scrivere un brief DB sensato. La descrizione si tiene
volutamente sopra il livello "DDL pronto".

### 5.1 Il tipo_prestazione di partenza

Una sola riga in `pratiche.tipi_prestazione` per cominciare:

| Campo              | Valore proposto                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `codice`           | `VENDITA_STANDARD`                                                                                |
| `categoria`        | `COMMERCIALE`                                                                                     |
| `descrizione`      | Processo commerciale standard: dalla richiesta cliente all'esecuzione (ordine o commessa diretta) |
| `pre_attivazione`  | `false`                                                                                           |
| `post_attivazione` | `false` (vendita può avvenire pre o post attivazione BA)                                          |

**Perché un solo template all'inizio**: principio §7 del manifesto. Il
secondo tipo (`VENDITA_RICORRENTE`, `VENDITA_PORTALE_B2B`, ...) si seeda solo
quando emerge dal dominio reale un caso diverso, non a priori.

### 5.2 I template_flussi del processo

Sequenza minimale, prerequisiti lineari (configurabili per varianti future):

| Sequenza | Codice                 | Direzione | Obbligatorio | Handler                   | Descrizione                                                                                                                     |
| -------- | ---------------------- | --------- | ------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 10       | `RICHIESTA_CLIENTE`    | ENTRATA   | true         | NULL (manuale)            | Registrazione richiesta iniziale: contesto cliente, esigenza. Non crea ancora preventivo                                        |
| 20       | `PREVENTIVAZIONE`      | INTERNA   | true         | NULL (manuale)            | Creazione/editing preventivo in `vendite.preventivi` (rimane PreventivoDrawer come UI). Chiusura del flusso = preventivo EMESSO |
| 30       | `APPROVAZIONE_CLIENTE` | ENTRATA   | true         | NULL (manuale)            | Registrazione esito (ACCETTATO/RIFIUTATO). Esito flusso → POSITIVO/NEGATIVO                                                     |
| 40       | `CONFERMA_VENDITA`     | INTERNA   | true         | `vendita.push_preventivo` | Split del preventivo per natura di riga, generazione 0..N destinazioni (ordine, commessa, contratto). Vedi §5.3                 |

**Note**:

- Il flusso 10 (`RICHIESTA_CLIENTE`) è il punto in cui la pratica registra il
  contesto **prima** che il preventivo esista. È obbligatorio **all'interno
  di questo template**, ma il template stesso è opzionale per l'azienda
  installatrice (vedi §5.8): un'azienda che vuole il modello strutturato
  completo lo accetta come parte del flusso; un'azienda che vuole vendite
  rapide può seedare un secondo template `VENDITA_RAPIDA` senza questo
  flusso, o non usare affatto le pratiche per le vendite.
- Il flusso 20 chiude solo quando il preventivo passa a EMESSO. Lo stato del
  preventivo non viene duplicato in pratica: la pratica registra "preventivo
  emesso = ✓" come esito del flusso, il preventivo resta sorgente di verità per
  i propri dati.
- Il flusso 40 è l'unico con handler. Tutto il resto è manuale (in v2 della
  dashboard, gli operatori avanzano i flussi cliccando "Completa").

### 5.3 Il flusso `CONFERMA_VENDITA`: split e idempotenza

Questa sezione è divisa in tre sottosezioni che descrivono i tre aspetti
critici del flusso 40:

- §5.3.1 — Struttura concettuale del bivio
- §5.3.2 — Preventivi misti: natura come proprietà di riga (**decisione
  aperta**, prerequisito Fase B)
- §5.3.3 — Idempotenza dell'azione push preventivo→ordine

#### 5.3.1 Struttura concettuale del bivio

Una volta che il preventivo è stato accettato dal cliente (flusso 30), il
flusso 40 si occupa di tradurre questa accettazione in **destinazioni
operative interne**: ordini per la merce da evadere, commesse dirette per i
servizi una tantum, contratti per i servizi ricorrenti.

Il modello concettuale è: una sorgente (il preventivo), N destinazioni
(0..N tra ordini, commesse, contratti), ciascuna corrispondente al
sottoinsieme di righe del preventivo con natura corrispondente.

Per le righe destinate ad **ordine**: la funzione DB (da scrivere)
`vendite.fn_push_preventivo_a_ordine(p_preventivo_id, p_righe_ids,
p_pratica_id, p_fatturazione_trigger)`:

- crea una nuova `vendite.ordini` con `sorgente_tipo_id` = PREVENTIVO e
  `sorgente_uid` = `preventivi.uid`;
- copia il sottoinsieme di righe e componenti BoM dal preventivo all'ordine,
  mantenendo lo snapshot prezzi (modello già usato dai contratti);
- registra il legame anche in `pratiche_sorgenti` (la pratica ora ha 2
  sorgenti: preventivo ROOT, ordine COLLEGATO);
- la transizione del preventivo a EVASO avviene **solo se tutte le righe
  sono state smistate** verso destinazioni operative. Se ne resta anche una
  sola non smistata, il preventivo resta in ACCETTATO.

Per le righe destinate a **commessa diretta**: l'handler chiama
`push_a_commessa` esistente (preventivo→commessa con sottoinsieme di
righe).

Per le righe destinate a **contratto** (ricorrenza): handler dedicato da
definire quando il caso emergerà concretamente (asse offerta commerciale →
contratto, vedi documento di analisi separato). In v1 dell'integrazione,
righe di natura ricorrente possono essere marcate come "non smistate
automaticamente" e gestite manualmente dall'operatore.

Nessuna delle destinazioni è "speciale": tutte sono casi normali. L'handler
le produce in base allo split delle righe.

#### 5.3.2 Preventivi misti: natura come proprietà di riga (**decisione aperta**)

**Riconoscimento del problema**: nella realtà commerciale, i preventivi
sono spesso **misti**. Esempio reale:

| Riga | Descrizione                          | Natura              |
| ---- | ------------------------------------ | ------------------- |
| 1    | Server fisico Dell PowerEdge         | BENE_FISICO         |
| 2    | Switch di rete Cisco                 | BENE_FISICO         |
| 3    | UPS APC                              | BENE_FISICO         |
| 4    | Installazione e configurazione       | SERVIZIO_UNA_TANTUM |
| 5    | Manutenzione annuale + supporto 24/7 | SERVIZIO_RICORRENTE |

Un singolo preventivo accettato deve generare:

- un **ordine** per le righe 1-3 (beni fisici, magazzino, evasione, DDT)
- una **commessa diretta** per la riga 4 (servizio una tantum, esecuzione
  progettuale)
- un **contratto** per la riga 5 (ricorrenza, ciclo di fatturazione
  periodico)

**Decisione architetturale (presa, irreversibile per v1)**: la natura è
una **proprietà di riga**, non di testata. L'handler `CONFERMA_VENDITA`
divide il preventivo per natura e genera 0..N destinazioni, ciascuna per il
sottoinsieme di righe corrispondente. Il modello a `natura_vendita` di
testata (esempio didattico in §4.5) è **insufficiente** e non viene
adottato.

**Fallback per righe non auto-classificabili (Opzione 3)**: se alcune righe
non hanno una natura derivabile automaticamente (es. articolo senza
classificazione, riga ambigua), il flusso si sospende e chiede
all'operatore di smistare manualmente quelle righe verso una destinazione.
Il sistema non blocca il processo, lo delega all'umano nei casi limite.
Questo è documentato come comportamento previsto, non come errore.

**Decisione aperta — prerequisito di Fase B**: dove vive la natura?

Va verificato **in apertura di Fase B**, prima di scrivere qualunque DDL:

> **Esiste già nello schema ZeroERP** (in `articoli`, `config`, `listini`,
> `vendite`, `fatturazione` o altri) **un'entità che rappresenta in tutti i
> termini il concetto di "natura commerciale ai fini del routing
> post-accettazione"?**
>
> "In tutti i termini" significa: l'entità deve essere nata per
> rappresentare *esattamente questo concetto*, non un concetto vicino o
> affine usato per altri scopi.
>
> **Regola: nessun riuso opportunistico.** Se esiste un'entità che *sembra*
> calzante ma è stata creata per un'altra ragione (es. un campo
> `tipo_articolo` usato per discriminare cosa va in magazzino), **non si
> riusa**. Si introduce una nuova `config.nature_vendita` (o nome
> equivalente) dedicata al routing. Il prezzo di una tassonomia in più è
> accettato come costo della pulizia semantica. Niente overload, niente
> patch, niente adapter (coerente con manifesto §III bis e §7).

L'esito di questa verifica (entità esistente identificata, oppure
introduzione nuova tassonomia) è il **primo deliverable di Fase B**, prima
del brief DB dell'handler.

**Granularità della natura**: vincolata a livello di riga di preventivo.
Può essere derivata automaticamente dall'articolo associato alla riga (se
l'articolo ha natura definita), oppure sovrascritta manualmente
dall'operatore in casi specifici. La derivazione vs override è una
decisione operativa che si chiude in Fase B sulla base di come l'entità
natura verrà strutturata.

#### 5.3.3 Idempotenza dell'azione push preventivo→ordine

L'azione "creo un ordine da un preventivo" deve essere **idempotente per
costruzione**: invocarla due volte sullo stesso preventivo (per qualunque
motivo: errore operatore, crash applicativo, doppio click, retry
automatico) **non deve mai produrre due ordini**. Questo è coerente con il
principio trasversale §6.9 sull'idempotenza delle azioni cross-dominio,
amplificato dal fatto che ZeroERP è DB-centrico: la garanzia vive nel DB,
non nell'applicativo.

**Difesa in profondità a tre strati**:

**Strato 1 — Vincolo DB (partial unique index)**:

```sql
CREATE UNIQUE INDEX uq_ordini_da_preventivo
  ON vendite.ordini (sorgente_uid)
  WHERE sorgente_tipo_id = (SELECT id FROM config.sorgenti
                            WHERE codice = 'PREVENTIVO');
```

Garantisce a livello DB che lo stesso preventivo non possa mai generare due
ordini. Vale per qualunque strada arrivi a `INSERT INTO vendite.ordini`
(UI, API, retry, script manuale, errore). È **l'ultima linea di difesa**,
inviolabile.

**Strato 2 — Check applicativo nella funzione**:

Dentro `fn_push_preventivo_a_ordine`, prima dell'INSERT:

```sql
IF EXISTS (SELECT 1 FROM vendite.ordini
           WHERE sorgente_tipo_id = (SELECT id FROM config.sorgenti
                                     WHERE codice = 'PREVENTIVO')
             AND sorgente_uid = (SELECT uid FROM vendite.preventivi
                                 WHERE id = p_preventivo_id))
THEN
  RAISE EXCEPTION USING ERRCODE = 'P0001',
    MESSAGE = 'E_VENDITA_ORDINE_GIA_GENERATO',
    DETAIL = format('Preventivo % già evaso con ordine', p_preventivo_id);
END IF;
```

Fornisce un **errore semantico esplicito** con codice
`E_VENDITA_ORDINE_GIA_GENERATO` (registrato in
`config.messaggi_errore.csv` per Fase B), interpretabile dal frontend.
Senza questo strato, il caller riceverebbe solo una unique violation
generica difficile da gestire in UX.

**Strato 3 — Idempotenza lato handler**:

L'handler `PushPreventivoOrdineHandler`, prima di chiamare la funzione DB,
può controllare nel `meta` del flusso o nel giornale se l'evento
`DOMINIO_ORDINE_CREATO` è già stato registrato. Se sì, riconosce
l'esecuzione precedente e non riprova. È il livello più alto, riduce
rumore in UX.

**Gestione errore in v1 — Opzione 1 (errore propagato)**:

Se l'azione viene riproposta su un preventivo già evaso, l'handler
**propaga l'errore all'operatore** con dialog esplicito: "Questo preventivo
ha già un ordine collegato (ID 4711). Apri l'ordine esistente". Nessun
recovery automatico, nessuna creazione silenziosa di un secondo ordine.

Le opzioni di recovery automatico (Opzione 2: handler riconosce l'ordine
esistente e completa il flusso senza errore) e di decisione operatore
contestuale (Opzione 3: dialog con scelte multiple) si valuteranno dopo
aver visto il comportamento del sistema in mano agli operatori reali. In
v1 il comportamento è esplicito e conservativo.

**Test di accettazione Fase B**: pgTAP test obbligatorio sul caso "doppia
invocazione di `fn_push_preventivo_a_ordine` sullo stesso preventivo →
seconda invocazione fallisce con errore semantico `E_VENDITA_ORDINE_GIA_
GENERATO`, nessun ordine duplicato in DB".

### 5.4 Push commessa: scelta automatica (sorgente più a valle)

Conferma decisione Tid (2026-05-18, risposta 2): quando esiste l'ordine, il
push commessa parte da `fn_list_ordini_da_pushare`; altrimenti da
`fn_list_preventivi_da_pushare`. Le due funzioni sono già scritte e
parallele. La regola "sorgente più a valle" è dichiarativa: nessun flag
"push_via_ordine" necessario, basta guardare l'esistenza di un ordine con
`sorgente_uid = preventivo.uid`.

Implicazione: `fn_list_preventivi_da_pushare` deve **escludere** i preventivi
che hanno già un ordine collegato (NOT EXISTS su
`vendite.ordini.sorgente_uid`). Modifica chirurgica, da fare nel brief DB
operativo. Questa è una protezione **lato lista** (filtro UX) che si somma
alla protezione di idempotenza **lato execute** descritta in §5.3.3.

### 5.5 Cosa il giornale registrerà end-to-end (per una pratica VENDITA)

Esempio per un preventivo composto interamente da beni fisici (caso
omogeneo, scelto per chiarezza didattica; il caso misto produce eventi
multipli analoghi per ciascuna destinazione):

| Tempo | Evento giornale                                                                    | Note                                             |
| ----- | ---------------------------------------------------------------------------------- | ------------------------------------------------ |
| t0    | `PRATICA_CREATA` (`VENDITA_STANDARD`)                                              | Operatore avvia                                  |
| t0+ε  | `FLUSSO_CREATO` x4                                                                 | Tutti i flussi 10-40 instanziati alla creazione  |
| t1    | `FLUSSO_STATO_CAMBIATO` su RICHIESTA_CLIENTE → COMPLETATO                          | Esito POSITIVO                                   |
| t2    | `DOMINIO_PREVENTIVO_CREATO` (in `meta`: `preventivo_id`, `numero PRV-...`)         | Handler manuale o trigger derivato               |
| t3    | `FLUSSO_STATO_CAMBIATO` su PREVENTIVAZIONE → COMPLETATO                            | Esito POSITIVO (preventivo EMESSO)               |
| t4    | `DOMINIO_PREVENTIVO_ACCETTATO`                                                     | Registrato dall'operatore via flusso 30          |
| t5    | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → IN_CORSO                             | Handler dispatch                                 |
| t6    | `DOMINIO_ORDINE_CREATO` (in `meta`: `ordine_id`, `anno_serie_numero`, `righe_ids`) | Effetto handler ramo "ordine"                    |
| t7    | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → COMPLETATO                           | Esito POSITIVO                                   |
| t8    | `STATO_CAMBIATO` su pratica → CHIUSA                                               | Trigger su tutti i flussi obbligatori completati |

In un caso misto (preventivo 3+1+1 di §5.3.2), tra t5 e t7 compaiono
multipli eventi di dominio:

- `DOMINIO_ORDINE_CREATO` (con `righe_ids` = sottoinsieme beni fisici)
- `DOMINIO_COMMESSA_CREATA` (con `righe_ids` = sottoinsieme servizi una
  tantum)
- `DOMINIO_CONTRATTO_CREATO` (con `righe_ids` = sottoinsieme ricorrenti),
  se contratti supportati in v1; altrimenti evento manuale dall'operatore.

Un secondo processo (assistenza, ticketing, CRM) seguirà lo stesso pattern,
con eventi `DOMINIO_*` propri.

### 5.6 Cosa NON cambia con questa integrazione

Per evitare ambiguità, lascio esplicito cosa **non** si tocca alla prima
integrazione:

- I cicli di vita `vendite.preventivi` e `vendite.ordini` restano invariati.
- Il PreventivoDrawer esistente resta. Cambia solo che, quando si entra nel
  drawer dal flusso PREVENTIVAZIONE di una pratica, la pratica viene
  agganciata come sorgente automaticamente. Quando si entra dal menù
  autonomo (se l'azienda lo lascia abilitato, vedi §5.8), il drawer
  funziona esattamente come oggi.
- Il push commessa resta operativo come oggi per i preventivi non agganciati
  a una pratica (compatibilità retroattiva interna — non con la "produzione",
  che non esiste).
- Il motore pratiche v2 non subisce modifiche infrastrutturali. Le aggiunte
  sono solo dati (seed `tipi_prestazione`, `template_flussi`,
  `handler_flussi`, `regole_generazione`), handler Python in `apps/vendite/`
  e funzioni DB nuove in `vendite.*`.

### 5.7 Lifecycle congiunto pratica ↔ preventivo (decisione 2026-05-18)

**Default conservativo**: nessuna propagazione automatica fra stati di
pratica e stati di preventivo/ordine.

Concretamente:

- Se la pratica VENDITA viene annullata mentre il preventivo è EMESSO o
  ACCETTATO, il preventivo **non viene annullato in cascata**. La pratica
  va in ANNULLATA, il preventivo conserva il suo stato. Il legame in
  `pratiche_sorgenti` resta come storico (giornale visibile da entrambi i
  lati).
- Se il preventivo viene annullato dal PreventivoDrawer mentre la pratica è
  ancora APERTA, il flusso `PREVENTIVAZIONE` non si chiude in automatico:
  l'operatore vede in dashboard il flusso aperto con il preventivo
  ANNULLATO e decide come procedere (es. nuova rev, oppure annullamento
  pratica manuale).

**Consistenza visualizzabile (decisione 2026-05-19)**: a livello di
dashboard, i flussi che puntano a sorgenti annullate sono **marcati
visivamente** (badge "sorgente annullata" o simile). Questo non è
propagazione di stato (il flusso resta APERTO), è solo segnalazione UI
perché l'operatore non navighi a vuoto. Implementazione lato frontend,
basata su join in lettura tra `flussi` e `pratiche_sorgenti` →
`vendite.preventivi.stato`.

Eventuali propagazioni esplicite (es. dialog "annullando la pratica vuoi
annullare anche il preventivo?") sono **passi UX** del frontend, non trigger
DB. Si valutano caso per caso quando emergono. Il principio: il DB protegge
l'integrità, l'operatore decide la propagazione di processo.

### 5.8 Configurabilità delle attività cross-dominio (principio generale)

> **Sezione introdotta in revisione 2026-05-19** per rispondere in modo
> generale alla richiesta "pratiche devono essere container configurabili di
> tutte le attività". Il principio qui descritto si applica a vendite (caso
> validatore) ma **vale identicamente** per ogni futuro dominio cross-pratica:
> ordini autonomi, richieste di assistenza, CRM, acquisti, ecc.

#### 5.8.1 Il principio

ZeroERP offre per ogni attività che può essere oggetto di pratica
(preventivi, ordini, richieste di assistenza, acquisti, ecc.) **due punti
di ingresso indipendenti**:

1. **Punto di ingresso autonomo dal menù** (es. "Nuovo preventivo",
   "Nuovo ordine", "Nuova richiesta assistenza")
2. **Punto di ingresso dentro un flusso di pratica** (es. flusso
   `PREVENTIVAZIONE` che apre il drawer relativo)

**L'azienda installatrice decide via configurazione menù** quali ingressi
esporre per ciascuna attività, usando l'area di configurazione menù **già
esistente** in ZeroERP. La scelta non è del software, è di chi adotta il
software.

Esempi:

- **Azienda Alfa** decide "tutti i preventivi devono nascere da una pratica
  VENDITA_STANDARD". Configura il menù disabilitando la voce autonoma
  "Nuovo preventivo". I loro operatori possono aprire PreventivoDrawer
  solo dal flusso `PREVENTIVAZIONE` di una pratica.
- **Azienda Beta** decide "preventivi veloci diretti, pratiche solo per
  progetti complessi". Lascia abilitata la voce autonoma. Gli operatori
  scelgono caso per caso.
- **Azienda Gamma** mescola: preventivi sempre da pratica, ordini autonomi
  liberi, assistenza sempre da pratica. Configurazione granulare per
  attività.

Entrambi i modi (e tutte le combinazioni) sono **legittimi, supportati
ufficialmente, end-to-end**. Non c'è uno "scenario corretto" e uno "scenario
di compatibilità".

#### 5.8.2 Conseguenze sul modello dati

Da questo principio discendono regole vincolanti su tutto lo schema:

- I campi di aggancio a pratica nelle entità di dominio (es. eventuale
  `vendite.preventivi.pratica_id`, o equivalenti per altre attività) sono
  **sempre opzionali a livello DB** (`NULL`-able). Nessun `NOT NULL`,
  perché spezzerebbe l'azienda Beta. La presenza/assenza dell'aggancio
  riflette il modello operativo scelto.
- Il PreventivoDrawer (e ogni drawer analogo per altre attività) deve
  funzionare **standalone**, perché il software offre la capacità. Se
  un'azienda non vuole esporlo, lo disabilita dal menù. Ma il codice del
  drawer non assume mai "esisto solo dentro una pratica".
- Le funzioni DB di azione cross-dominio (es.
  `fn_push_preventivo_a_ordine`) accettano `p_pratica_id` come parametro
  **opzionale**. Se presente, l'aggancio viene registrato in
  `pratiche_sorgenti`; se assente, l'azione viene comunque eseguita ma
  senza traccia in pratiche.

#### 5.8.3 No retroattività (decisione architetturale)

Un'attività nata fuori pratica **resta fuori per sempre**. Non esiste
nell'API di ZeroERP un'operazione "promuovi questo preventivo orfano dentro
una pratica esistente o nuova".

Se un'azienda passa nel tempo da una configurazione "preventivi autonomi" a
"preventivi sempre da pratica", **il software non offre strumenti per
recuperare la storia**. I preventivi orfani precedenti restano orfani; i
nuovi preventivi nascono dentro pratica. Le due popolazioni convivono nello
schema senza commistione.

**La retroattività esce dallo scope di ZeroERP come prodotto.** Eventuali
recuperi storici da parte di un'azienda specifica sono **attività di
consulenza/migrazione one-shot**, a carico del cliente, con script ad hoc
scritti per la specifica esigenza, e compromessi (eventi giornale datati
nel passato, flussi sintetizzati, ecc.) accettati consapevolmente. Non
sono funzionalità di prodotto, e non vengono pianificati come tali.

Conseguenza pratica per i casi di attività successive a un'attività
orfana: se un preventivo orfano genera in seguito un ordine, e l'azienda
nel frattempo ha attivato il modello "ordini sempre da pratica", la nuova
pratica sull'ordine **cita l'ordine** come `pratiche_sorgenti`, **non il
preventivo originario**. La storia commerciale del preventivo resta fuori;
la storia esecutiva dell'ordine è dentro. Asimmetria voluta e dichiarata.

#### 5.8.4 Limite del modello: il giornale come backbone è proprietà condizionata

Coerentemente con §5.8.3, il giornale è backbone effettivo dell'attività
aziendale **solo nella misura in cui l'azienda configura le attività per
nascere dentro pratica**. Le attività autonome non lasciano traccia nel
giornale, mai. Questo è un fatto da dichiarare onestamente nella
documentazione utente, non un limite da nascondere (vedi §3.4).

---

## 6. Convenzioni riusabili (proposte, da validare alla prima integrazione)

### 6.1 Naming `tipi_prestazione`

Codice: `<DOMINIO>_<PROCESSO>` in maiuscolo, separatore `_`. Esempi:

- vendite: `VENDITA_STANDARD`, `VENDITA_RICORRENTE` (futuro)
- assistenza: `ASSISTENZA_TECNICA`, `INTERVENTO_PROGRAMMATO`
- acquisti: `ACQUISTO_STANDARD`, `RICHIESTA_OFFERTA` (futuro)

### 6.2 Naming `template_flussi`

Codice: `<VERBO_O_FASE>` in maiuscolo, nome del passo, non del dominio.
Esempio: `PREVENTIVAZIONE` non `VENDITA_PREVENTIVAZIONE` — il dominio è già
nel `tipo_prestazione`. I template sono "stack" del processo, non duplicati
per dominio.

### 6.3 Naming sorgenti (`config.sorgenti`)

Codice: nome del tipo di documento al singolare, maiuscolo: `PREVENTIVO`,
`ORDINE`, `CONTRATTO`, `DDT`, `FATTURA`. Una sola riga per tipo,
condivisa fra tutti i moduli che la consumano. Il pattern è già attivo
(`vendite.commesse_sorgenti` la usa).

### 6.4 Naming handler_key

Convenzione `<dominio>.<azione>`, lowercase con `.`, riusabile per più
template. Esempi:

- `vendita.push_preventivo` — push verso ordine, commessa, contratto (split)
- `vendita.invio_documento` — invio PDF preventivo/ordine al cliente
- `assistenza.notifica_tecnico` — dispatch notifica
- `pratiche.notifica_responsabile` — handler trasversale (interno al motore)

### 6.5 Naming `ext_<concetto>` (quando emergerà)

Convenzione di forma: `pratiche.ext_<concetto>`, snake_case, singolare.
Esempi attesi: `ext_appuntamento`, `ext_sopralluogo`, `ext_comunicazione`,
`ext_spedizione`.

> Per il **principio architetturale** (cosa rappresenta `ext_*` e cosa NON
> rappresenta) il riferimento è §2.3 sottosezione "Quando NON usarlo". Qui
> stiamo solo dichiarando la convenzione di naming.

**Criterio quantitativo di promozione da `meta JSONB` a `ext_<concetto>`**
(decisione 2026-05-18):

| Dati propri della pratica nel contesto del legame                      | Soluzione                                                       |
| ---------------------------------------------------------------------- | --------------------------------------------------------------- |
| 0-1 colonne                                                            | `pratiche_sorgenti.meta` o `flussi.meta` JSONB                  |
| 2-3 colonne occasionali                                                | Ancora `meta`, ma con commento esplicito sulla struttura attesa |
| 4+ colonne con vincoli a schema (UNIQUE, CHECK, FK, indici di ricerca) | Promozione a `pratiche.ext_<concetto>` (tabella nuova)          |

La promozione richiede sempre un secondo caso d'uso identico (manifesto §7).
Per il caso vendite (preventivi+ordini) **non si introduce alcun `ext_*`**:
i dati specifici stanno in `meta` finché un secondo dominio non chiede la
stessa struttura.

### 6.6 Granularità competenze flussi (decisione 2026-05-18)

`pratiche.competenze_flussi` (matrice operatore × template_flusso × reparto,
già operativa nella dashboard v2) si **seeda manualmente** dall'admin via
endpoint CRUD esistente. Niente derivazione automatica da ruolo operatore
nella prima integrazione.

Motivazione: il modello "competenza derivata da ruolo" introduce un secondo
livello di astrazione (ruolo → set di template) che oggi non ha un secondo
caso d'uso identico oltre vendite. Si valuta dopo aver visto il secondo
consumatore di pratiche, in coerenza con manifesto §7.

### 6.7 Codici errore `E_*`

Convenzione: `E_<DOMINIO>_<CONDIZIONE>`. Esempi:

- `E_VENDITA_ORDINE_GIA_GENERATO` (push preventivo che ha già un ordine,
  vedi §5.3.3)
- `E_PRATICHE_SORGENTE_INCOMPATIBILE` (tentativo di link sorgente non
  ammessa per quel tipo_prestazione)

I codici si registrano in `config.messaggi_errore.csv` come da convenzione
esistente. Errori del motore pratiche stanno con prefisso `E_PRATICHE_*` o
`E_FLUSSI_*`, errori del dominio chiamante con prefisso del dominio.

### 6.8 Convenzione `meta` JSONB cross-record

Quando lo stesso concetto compare in `meta` JSONB di tabelle diverse, usare
la stessa chiave:

| Concetto                         | Chiave                        |
| -------------------------------- | ----------------------------- |
| ID preventivo                    | `preventivo_id`               |
| UID preventivo                   | `preventivo_uid`              |
| ID ordine                        | `ordine_id`                   |
| UID ordine                       | `ordine_uid`                  |
| ID commessa                      | `commessa_id`                 |
| ID fattura                       | `fattura_id`                  |
| ID contratto                     | `contratto_id`                |
| Numero documento testuale        | `documento_numero`            |
| IDs righe coinvolte in un'azione | `righe_ids` (array di interi) |

Permette query trasversali tipo `SELECT pratica_id FROM pratiche.giornale
WHERE meta->>'ordine_id' = '...'`.

### 6.9 Idempotenza delle azioni cross-dominio (convenzione trasversale)

> **Convenzione introdotta in revisione 2026-05-19**, generalizzazione del
> caso `vendita.push_preventivo` (§5.3.3) a tutte le azioni cross-dominio.
> Discende direttamente dalla natura DB-centrica di ZeroERP: l'integrità è
> business logic, e quindi vive nel DB.

#### 6.9.1 Il principio

**Ogni azione cross-dominio che produce un'entità a partire da un'altra
deve essere idempotente per costruzione. L'idempotenza si garantisce con
vincoli a livello DB, non con controlli applicativi.**

Concretamente: chiamare due volte la stessa azione con la stessa coppia
sorgente non deve mai produrre due destinazioni. Il livello applicativo
può sbagliare (errore operatore, doppio click, retry, crash). Il DB è
l'ultima linea di difesa, e deve esserlo per davvero.

#### 6.9.2 Ambito di applicazione

La convenzione si applica a tutte le azioni del tipo "una sorgente produce
una destinazione" in ZeroERP. Esempi attuali e attesi:

- preventivo → ordine
- preventivo → commessa diretta
- ordine → commessa
- pratica → pratica generata (`fn_genera_pratica_da_flusso`)
- ordine acquisto → DDT ingresso
- DDT → fattura
- ogni futuro handler cross-dominio che produce un'entità

#### 6.9.3 Pattern di implementazione

Per ciascuna coppia sorgente→destinazione la garanzia di idempotenza si
implementa **a livello DB** con uno dei due pattern seguenti, a seconda
della cardinalità del legame:

**Pattern A — Una destinazione per sorgente** (cardinalità 0..1):

```sql
CREATE UNIQUE INDEX uq_<dest>_da_<src>
  ON <schema>.<destinazione> (sorgente_uid)
  WHERE sorgente_tipo_id = (SELECT id FROM config.sorgenti
                            WHERE codice = '<SORGENTE>');
```

Esempio: un preventivo genera al massimo un ordine.

**Pattern B — Molte destinazioni distinte per sorgente** (cardinalità
0..N, dove le N destinazioni sono distinguibili da una chiave aggiuntiva):

```sql
CREATE UNIQUE INDEX uq_<dest>_da_<src>
  ON <schema>.<destinazione> (sorgente_uid, <chiave_disambiguazione>)
  WHERE sorgente_tipo_id = ...;
```

Esempio: un ordine genera N DDT, ciascuno per un sottoinsieme di righe →
`UNIQUE(sorgente_uid, riga_ordine_id)` o equivalente.

In entrambi i casi, oltre al vincolo DB, la funzione PL/pgSQL chiamante
deve aggiungere il check applicativo con `RAISE EXCEPTION` e codice errore
semantico (`E_<DOMINIO>_<CONDIZIONE>_GIA_GENERATO`), per fornire un
messaggio comprensibile al chiamante invece della unique violation
generica.

#### 6.9.4 Differenza tra idempotenza e replay

La convenzione richiede **idempotenza** (la seconda invocazione non
duplica), **non replay** (la seconda invocazione finge "ok, fatto"). La
seconda invocazione deve **fallire con errore esplicito**, riferendo
all'esistente. Il chiamante (handler, UI, script) decide cosa fare con
l'errore. Il replay silenzioso è considerato pericoloso perché nasconde
problemi reali (es. l'operatore credeva che la prima invocazione fosse
fallita, e invece era riuscita).

#### 6.9.5 Conseguenza sui brief DB

Ogni brief DB futuro che introduce una nuova azione cross-dominio
**deve includere obbligatoriamente**:

1. Il vincolo DB (Pattern A o B di §6.9.3).
2. Il check applicativo nella funzione con codice errore registrato in
   `config.messaggi_errore.csv`.
3. Un pgTAP test sul caso "doppia invocazione → seconda invocazione
   fallisce con errore semantico, nessun dato duplicato".

Senza questi tre elementi, il brief è considerato incompleto e non
applicabile.

---

## 7. Decisioni prese (sintesi 2026-05-18 + revisione 2026-05-19)

Tabella riassuntiva per navigazione veloce. Le decisioni del 18 maggio sono
state chiuse a default conservativo; la revisione del 19 maggio ha aggiunto
decisioni nuove (configurabilità attività, idempotenza trasversale,
preventivi misti) e mantenuto aperti i prerequisiti tecnici per Fase B.

### 7.1 Decisioni chiuse

| Tema                                              | Decisione                                                                                                                                                                                                                                              | Rif.   |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| Push commessa                                     | Sorgente più a valle: da ordine se esiste, altrimenti da preventivo. `fn_list_preventivi_da_pushare` esclude i preventivi con ordine collegato                                                                                                         | §5.4   |
| Scope pratica                                     | Tutto il processo avviene nella pratica (`RICHIESTA_CLIENTE` prima del preventivo + `CONFERMA_VENDITA` come split). Il flusso `RICHIESTA_CLIENTE` è obbligatorio nel template `VENDITA_STANDARD`; aziende che vogliono varianti seedano altri template | §5.2   |
| Modello del bivio CONFERMA_VENDITA                | Split del preventivo per natura di riga, 0..N destinazioni (ordine, commessa, contratto). Modello a `natura_vendita` di testata rigettato                                                                                                              | §5.3.2 |
| Configurabilità attività cross-dominio            | Doppio punto di ingresso (autonomo da menù + dentro flusso pratica) per ogni attività; l'azienda installatrice configura via menù quali esporre; principio generale valido per preventivi/ordini/assistenza/CRM/acquisti                               | §5.8   |
| Retroattività                                     | Fuori scope di ZeroERP come prodotto. Un'attività nata fuori pratica resta fuori per sempre. Recuperi storici = consulenza one-shot a carico del cliente                                                                                               | §5.8.3 |
| Consistenza visualizzabile sorgenti annullate     | Marcatura UI in dashboard sui flussi che puntano a sorgenti annullate; nessuna propagazione di stato lato DB                                                                                                                                           | §5.7   |
| Idempotenza cross-dominio (principio trasversale) | Ogni azione produttiva è idempotente per costruzione, garantita da vincoli DB (UNIQUE su sorgente o chiave composita); check applicativo + codice errore semantico in aggiunta; pgTAP obbligatorio                                                     | §6.9   |
| Idempotenza preventivo→ordine (caso specifico)    | Partial UNIQUE index su `vendite.ordini(sorgente_uid) WHERE sorgente_tipo_id = PREVENTIVO`; check con `E_VENDITA_ORDINE_GIA_GENERATO`; gestione errore = Opzione 1 (errore propagato all'operatore, no recovery automatico v1)                         | §5.3.3 |
| Lifecycle congiunto pratica↔preventivo            | Nessuna propagazione automatica di stati. Propagazioni esplicite restano in UX, non in trigger DB                                                                                                                                                      | §5.7   |
| Soglia `ext_*`                                    | `meta JSONB` per 0-3 colonne; promozione a `pratiche.ext_<concetto>` solo a 4+ colonne con vincoli a schema e secondo caso d'uso identico                                                                                                              | §6.5   |
| Principio `ext_*` non duplica entità di dominio   | `ext_preventivo` rigettato come anti-pattern: il preventivo vive in `vendite.preventivi`, l'aggancio si fa con `pratiche_sorgenti`                                                                                                                     | §2.3   |
| Competenze flussi                                 | Seed manuale via admin/CRUD. Derivazione automatica da ruolo non in v1, valutata al secondo consumatore                                                                                                                                                | §6.6   |
| Eventi di dominio nel giornale                    | Helper applicativo `pratiche_service.log_evento_dominio(...)` come **implementazione provvisoria**, senza pretesa di stabilità protocollare. Rivalutazione dopo 3-4 eventi reali                                                                       | §3.2   |
| Aggancio pratica↔preventivo                       | `pratiche_sorgenti` (M:N esistente), non `ext_preventivo`                                                                                                                                                                                              | §2.4   |
| Secondo consumatore validante motore              | Da scegliere tra assistenza, acquisti, CRM in base alle priorità di business. Non bloccante per Fase B                                                                                                                                                 | §8.6   |

### 7.2 Decisioni aperte (prerequisiti di Fase B)

| Tema                                                      | Stato                                                | Decisione richiesta in apertura di | Rif.   |
| --------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------- | ------ |
| Identificazione/introduzione entità `natura` (di riga)    | **APERTA**                                           | Fase B, primo deliverable          | §5.3.2 |
| No riuso opportunistico di entità esistenti per la natura | Chiusa come **vincolo** della decisione sopra        | Fase B applica il vincolo          | §5.3.2 |
| Derivazione natura da articolo vs override su riga        | **APERTA**, dipende dall'esito della verifica entità | Fase B, secondo deliverable        | §5.3.2 |

Tutte le decisioni chiuse sono **revedibili** alla fase di validazione (Fase
E, §8.5) se l'uso reale mostra divergenza dai default.

---

## 8. Roadmap incrementale di validazione

Quattro fasi successive. Ogni fase chiude prima di iniziare la successiva.

### 8.1 Fase A — Chiusura decisioni di modello (questa analisi)

- ✅ Analisi pubblicata (questo documento)
- ✅ Revisione critica 2026-05-19 (correzioni punti 1, 4, 5, 10)
- ⏳ Eventuale aggiornamento di `gestione-pratiche-v2.md` con riferimento a
  questo documento come "Fase 8 — Integrazione cross-dominio" (rinviato a OK
  Tid)

### 8.2 Fase B — Primo brief DB operativo (vendite, MVP)

Documento separato (es. `brief-db-vendite-integrazione-pratiche.md`) che
contiene, nell'ordine:

**Deliverable preliminari (decisioni aperte di §7.2)**:

- **D0 — Verifica entità natura**: indagine sullo schema esistente per
  identificare se una tassonomia "natura commerciale ai fini del routing
  post-accettazione" esiste già nei termini esatti del concetto. Esito:
  entità identificata (con motivazione) oppure introduzione nuova
  `config.nature_vendita` (o nome equivalente). Vincolo: no riuso
  opportunistico di entità nate per altri scopi.
- **D1 — Derivazione natura**: decisione su come la natura arriva alla
  riga di preventivo (derivata da articolo, override manuale, entrambi).

**Deliverable DDL e seed**:

- seed `config.sorgenti` (verifica + eventuali aggiunte: ORDINE,
  COMMESSA, CONTRATTO, ...)
- seed `pratiche.tipi_prestazione` (`VENDITA_STANDARD`)
- seed `pratiche.template_flussi` x4 + prerequisiti + canali
- seed `pratiche.handler_flussi` (`vendita.push_preventivo`)
- DDL `vendite.fn_push_preventivo_a_ordine` (funzione PL/pgSQL nuova) con
  parametro `p_righe_ids` per lo split
- DDL `vendite.fn_push_preventivo_a_commessa` (o estensione esistente con
  parametro `p_righe_ids` per lo split)
- DDL partial unique index `uq_ordini_da_preventivo` (idempotenza, §5.3.3)
- ALTER `fn_list_preventivi_da_pushare` (escludere preventivi con ordine
  collegato)
- Eventuale ALTER su `vendite.preventivi_righe` per il campo natura (se la
  decisione D0 richiede una colonna nuova)
- 3-5 codici errore in `config.messaggi_errore.csv` inclusi
  `E_VENDITA_ORDINE_GIA_GENERATO`

**Deliverable pgTAP**:

- creazione pratica VENDITA + push preventivo→ordine + legame in
  `pratiche_sorgenti` corretto
- **caso di accettazione obbligatorio**: preventivo misto 3 beni fisici + 1
  servizio una tantum + 1 servizio ricorrente → 1 ordine (con righe 1-3) +
  1 commessa (con riga 4) + 1 contratto o segnalazione manuale (con riga
  5)
- **caso di idempotenza obbligatorio**: doppia invocazione di
  `fn_push_preventivo_a_ordine` sullo stesso preventivo → seconda
  invocazione fallisce con `E_VENDITA_ORDINE_GIA_GENERATO`, nessun ordine
  duplicato

### 8.3 Fase C — BE + handler Python + integrazione PreventivoDrawer

- App Django `apps/vendite/handlers/push_preventivo_handler.py`
- Registrazione in `HANDLER_MAP`
- Service `vendite_service.crea_ordine_da_preventivo()` (wrapper della fn DB)
- Service di split per natura di riga
- API: estensione `PreventivoDrawer` per agganciare/sganciare a pratica
- Test Django + smoke test bash

### 8.4 Fase D — FE (dashboard + drawer)

- Estensione `PraticheDashboard` per il tipo VENDITA_STANDARD (probabilmente
  nessuna modifica: la dashboard è generica per tipo_prestazione)
- `FlussoDrawer` esteso: per `CONFERMA_VENDITA`, anteprima dello split per
  natura + dialog di smistamento manuale (Opzione 3 fallback) per righe non
  auto-classificabili
- Aggiunta tab "Pratiche collegate" nel PreventivoDrawer (lista pratiche da
  `pratiche_sorgenti`)
- Marcatura UI sui flussi con sorgenti annullate (§5.7)
- Smoke UI

> **Nota architetturale (rev. 2026-05-19)**: le fasi B, C, D possono essere
> svolte in **parallelo** dopo la chiusura dei deliverable preliminari D0/D1
> di Fase B, anziché in sequenza rigida. La sequenza B→C→D era proposta
> originariamente ma rischia di accumulare lavoro DB+BE senza feedback FE
> reale, contro lo spirito concentrico. La validazione (Fase E) richiede UI
> funzionante per essere significativa.

### 8.5 Fase E — Validazione e decanto

- Esecuzione end-to-end del processo: richiesta cliente → preventivo →
  (split) → ordine + commessa + contratto → fatture, tutto sotto una
  pratica
- Test del caso misto 3+1+1 con operatori reali
- Test del caso "azienda Beta": preventivi/ordini autonomi senza pratica
- Estrazione del *vocabolario* che è effettivamente servito (cosa va
  promosso al nucleo pratiche, cosa resta dominio vendite)
- Rivalutazione decisioni provvisorie (es. `log_evento_dominio` helper vs
  promozione a `config.tipi_eventi_giornale`)
- Aggiornamento `mappa-concentrica.md`: `pratiche` da "predisposta, in
  attesa di validazione" → "validata con primo consumatore (vendite),
  pronto per secondo (assistenza/CRM/acquisti)"

### 8.6 Fase F — Secondo consumatore (manifesto §7)

A scelta in base alle priorità di business: assistenza (pattern già
pianificato in `crm-ticketing-pratiche.md`), acquisti, o CRM. Solo dopo la
fase F il motore si può promuovere a contratto stabile.

---

## 9. Riferimenti e dipendenze

### 9.1 Documenti chiave

- [sviluppo-concentrico.md](../../sviluppo-concentrico.md) §III bis, §7
- [mappa-concentrica.md](../../mappa-concentrica.md) §Anello 2, §Caso di
  studio pratiche prima di vendite
- [Guida Gestione Pratiche](../../guide/gestione-pratiche.md)
- [Guida Gestione Preventivi](../../guide/gestione-preventivi.md)
- [Manuale vendite.ordini](../../dbzero/vendite/manual/ordini.md)
- [gestione-pratiche-v2.md](gestione-pratiche-v2.md)
- [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md)
- [Analisi-iniziale-offerta-commerciale.md](Analisi-iniziale-offerta-commerciale.md)
- [pratiche_sorgenti manual](../../dbzero/pratiche/manual/pratiche_sorgenti.md)

### 9.2 Tabelle/funzioni DB di interesse

- `pratiche.pratiche`, `pratiche.flussi`, `pratiche.giornale`,
  `pratiche.pratiche_sorgenti`, `pratiche.handler_flussi`,
  `pratiche.regole_generazione`, `pratiche.competenze_flussi`
- `config.sorgenti`, `config.canali_pratiche`, `config.stati_pratiche`,
  `config.stati_flussi_pratiche`, `config.messaggi_errore`
- Eventuale futura `config.nature_vendita` (esito Fase B D0)
- `vendite.preventivi`, `vendite.preventivi_righe`, `vendite.ordini` (+
  righe + componenti), `vendite.commesse_sorgenti`,
  `vendite.fn_list_preventivi_da_pushare`, `vendite.fn_list_ordini_da_pushare`

### 9.3 Backend chiave

- `apps/pratiche/services/handler_registry.py` (`HANDLER_MAP` da
  popolare al primo handler reale)
- `apps/pratiche/services/pratiche_service.py` (facade cross-dominio,
  include `log_evento_dominio` helper provvisorio)
- `apps/vendite/services/preventivi_service.py` (push_a_commessa già
  esistente, da estendere con split per natura di riga)

---

## 10. Stato del documento

| Sezione                            | Stato                                                                                                                                                           | Prossima azione                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| §1 Inquadramento                   | Stabile                                                                                                                                                         | —                                                 |
| §2 Tre pattern                     | Stabile, contraddizione `ext_preventivo` risolta (rev. 19 maggio)                                                                                               | —                                                 |
| §3 Giornale backbone               | Chiusa a default (helper applicativo provvisorio) + onestà sulla qualità condizionata                                                                           | Validazione Fase E                                |
| §4 Configurabilità interna pratica | Stabile, esempio §4.5 marcato come didattico                                                                                                                    | —                                                 |
| §5 Caso vendite                    | Decisioni 18 maggio chiuse + revisione 19 maggio: introdotti §5.3.2 (preventivi misti, decisione aperta), §5.3.3 (idempotenza), §5.8 (configurabilità attività) | Fase B brief DB con deliverable preliminari D0/D1 |
| §6 Convenzioni                     | Stabile + nuova §6.9 (idempotenza trasversale)                                                                                                                  | Si consolida dopo §8.5                            |
| §7 Decisioni prese                 | Sintesi 18 maggio + integrazione 19 maggio, distinzione chiuse vs aperte                                                                                        | Revisione a Fase E                                |
| §8 Roadmap                         | Approvata + nota su parallelismo B/C/D                                                                                                                          | Avvio Fase B su OK Tid                            |

---

*Analisi integrazione domini Anello 3 con motore pratiche — ZeroErp
(2026-05-18, revisione critica 2026-05-19). Documento vivo, da aggiornare ad
ogni Fase chiusa.*