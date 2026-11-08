# Analisi — Pratiche come container di processo: integrazione domini Anello 3

> ⚠️ **Allineamento al modello della provenienza (2026-11-08).** Dove questa analisi lega la pratica e i documenti
> derivati con la coppia `(sorgente_tipo_id, sorgente_uid)` testuale, e propone indici unici su `sorgente_uid`, oggi
> vale il modello unico di `brief-db-sorgente-documento-e-riga`: la chiave del documento sta in `sorgente_id` o
> `sorgente_uid` (tipizzate, secondo il tipo), la riga in `sorgente_riga`; `pratiche.pratiche_sorgenti` ha le colonne
> tipizzate; un'unicità esiste solo dove il dominio ha una regola, sulla chiave del modello (l'ordine e il contratto
> dall'offerta: `uq_ordini_v_sorgente_offerta`, `uq_contratti_sorgente_offerta`). Gli esempi SQL con `sorgente_uid`
> qui sotto vanno riletti su quella struttura. Il meccanismo è nella guida
> [Sorgente polimorfa](../../guide/sorgente-polimorfa.md).
>
> **Stato**: ANALISI infrastrutturale + **Fase E chiusa** (primo consumatore
> PREVENTIVI validato runtime, §8.5). Documento di consolidamento delle convenzioni
> di aggancio fra motore `pratiche` (Anello 2) e processi di Anello 3 (`vendite`,
> `acquisti`, `magazzino`, ...).
>
> **➡️ Per i prossimi passi operativi** (urgenze, item aperti, pratiche
> offerta/contratto/ordine) il riferimento autorevole è
> [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md). Questa
> analisi resta la **visione** dell'integrazione domini.
>
> **Data**: 2026-05-18 (rev. 2026-05-19 — integrazione critica; aggiornamento
> 2026-06-20 — allineamento §8 al codice reale)
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
> - [gestione-pratiche-v2.md](../work-done/gestione-pratiche-v2.md) — modello operativo
>   pratiche v2 (fasi 1-7 DB+BE+FE)
> - [Guida Gestione Pratiche](../../guide/gestione-pratiche.md) — semantica
>   tipi_prestazione, template_flussi, handler, generazione cross-pratica
> - [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md) — pattern già aperto
>   per assistenza/CRM, qui generalizzato
> - [analisi-offerta-commerciale.md](../work-done/analisi-offerta-commerciale.md)
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

> ⚠️ **AGGIORNAMENTO — decisioni ratificate (Tid, 2026-06-08/09), prevalgono su questa prosa.**
> Fonte autorevole: [brief-preventivi-ordini.md §0](../work-done/brief-preventivi-ordini.md).
>
> 1. **Natura ricorrente (MODALITÀ A — blocco vero):** un articolo con
>    `destinazione_tipo = 'CONTRATTO'` (oggi `SERVIZIO_RICORRENTE`) **non può stare
>    su un preventivo**. La ricorrenza si avvia solo da **offerta→contratto**. Il
>    preventivo ha quindi **solo due destinazioni: ORDINE e COMMESSA**. Decade la
>    parte di §5.3.1 secondo cui le righe ricorrenti «possono essere marcate come
>    non smistate automaticamente e gestite manualmente»: sono **bloccate
>    all'inserimento riga** (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`), non gestite a valle.
> 2. **Nessun override operatore sulla natura:** la natura è proprietà intrinseca
>    dell'articolo, ereditata e **congelata** sulla riga. Decade la parte di §5.3.2
>    su «oppure sovrascritta manualmente dall'operatore».
> 3. **Riga senza natura:** prevenuta a monte da `catalogo.articoli.natura_vendita_id`
>    NOT NULL (+ backfill), non dalla «sospensione/Opzione 3» di §5.3.2.
> 4. **Idempotenza:** a livello **riga** (link `ordini_righe.preventivo_riga_id` +
>    UNIQUE parziale), non di testata: §5.3.3 (UNIQUE su `sorgente_uid`) è **deprecata**.

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

Per le righe destinate a **contratto** (ricorrenza): ~~handler dedicato da
definire... righe marcate come non smistate e gestite manualmente~~.
**SUPERATO (MODALITÀ A, vedi banner §5.3):** le righe ricorrenti **non entrano
nel preventivo** — sono bloccate all'inserimento (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`).
La ricorrenza si avvia da **offerta→contratto**, non dal preventivo.

Le destinazioni del preventivo sono quindi **due** (ORDINE, COMMESSA): nessuna è
"speciale", l'handler le produce in base allo split delle righe.

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
**CHIUSA (vedi banner §5.3):** è **derivata e congelata** dall'articolo
(snapshot all'inserimento, come i prezzi), **senza override operatore** — la riga
non può discostarsi dalla classificazione dell'articolo. L'articolo senza natura
è prevenuto a monte da `catalogo.articoli.natura_vendita_id` NOT NULL (+ backfill),
quindi non esiste la riga «non auto-classificabile» dell'Opzione 3 qui sopra.

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
| t0+ε  | `FLUSSO_CREATO` x4                                                                 | Flussi 10-40 instanziati (vedi nota ⚠ sotto)     |
| t1    | `FLUSSO_STATO_CAMBIATO` su RICHIESTA_CLIENTE → COMPLETATO                          | Esito POSITIVO                                   |
| t2    | `DOMINIO_PREVENTIVO_CREATO` (in `meta`: `preventivo_id`, `numero PRV-...`)         | Handler manuale o trigger derivato               |
| t3    | `FLUSSO_STATO_CAMBIATO` su PREVENTIVAZIONE → COMPLETATO                            | Esito POSITIVO (preventivo EMESSO)               |
| t4    | `DOMINIO_PREVENTIVO_ACCETTATO`                                                     | Registrato dall'operatore via flusso 30          |
| t5    | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → IN_CORSO                             | Handler dispatch                                 |
| t6    | `DOMINIO_ORDINE_CREATO` (in `meta`: `ordine_id`, `anno_serie_numero`, `righe_ids`) | Effetto handler ramo "ordine"                    |
| t7    | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → COMPLETATO                           | Esito POSITIVO                                   |
| t8    | `STATO_CAMBIATO` su pratica → CHIUSA                                               | Trigger su tutti i flussi obbligatori completati |

> **⚠ Nota correttiva (2026-06-07)** — Il passo `t0+ε` (`FLUSSO_CREATO ×4` —
> "tutti i flussi instanziati alla creazione") è **errato**, e per un motivo di
> modello, non solo di implementazione. Materializzare tutti i flussi alla
> creazione **non è il comportamento voluto**: un flusso può dipendere da una
> scelta fatta (o no) in un flusso precedente → i percorsi sono **condizionali**,
> quindi pre-crearli tutti confonderebbe l'operatore e sarebbe scorretto.
>
> **Modello corretto**: `template_flussi` descrive il **percorso suggerito** (gli
> N step in ordine di esecuzione). All'operatore si mostra **visivamente quel
> percorso** (roadmap/stepper ordinato), anche per gli step futuri; i flussi
> concreti si **eseguono/istanziano progressivamente**, e le **regole di
> prerequisito — già esistenti** (`trgfn_flussi_guard_prerequisiti` /
> `fn_check_prerequisiti_flusso`, da `template_flussi_prerequisiti`) — bloccano
> con errore il tentativo di eseguire uno step non ancora abilitato. La testata
> pratica porta solo stati-contenitore (`BOZZA/APERTA → SOSPESA/CHIUSA/ANNULLATA`);
> l'avanzamento reale lo raccontano i flussi e i loro stati. Coerente: il codice
> attuale (`crea_pratica`) **non** materializza i flussi alla creazione, ed è
> giusto così. Vedi stessa correzione in §11.1.7.
>
> Stessa cautela per il passo `t8` ("`pratica → CHIUSA` per trigger su tutti i
> flussi obbligatori completati"): la guida (`gestione-pratiche.md`) descrive
> `CHIUSA` come **transizione esplicita** da `APERTA`, e non risulta un trigger
> di auto-chiusura su completamento dei flussi. Da verificare/realizzare se si
> vuole la chiusura automatica.

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

> **⚠ Stato di avanzamento (2026-06-08) — primo consumatore consegnato in
> sottoinsieme focalizzato.** La roadmap §8.2-§8.4 descrive la **visione ampia**
> (`VENDITA_STANDARD` con split per `natura_vendita` → ordine + commessa +
> contratto). Il **primo giro implementato** è un **sottoinsieme deliberato e più
> stretto**: pratica **`PREVENTIVI`** (immediata/differita) → **commessa diretta**
> (nessuno split natura, niente ordine/contratto). Tracciato in tre brief
> dedicati:
> [brief-db-pratica-preventivi.md](../work-done/brief-db-pratica-preventivi.md),
> [brief-be-pratica-preventivi.md](../work-done/brief-be-pratica-preventivi.md),
> [brief-fe-pratica-preventivi.md](../work-done/brief-fe-pratica-preventivi.md).
>
> - **Fase B (DB)** — ✅ **CONSEGNATA** (2026-06-08): seed `PREVENTIVI_IMMEDIATA/_DIFFERITA`
>   + 8 `template_flussi` + handler_flussi `vendita.push_preventivo`, motore
>   prerequisiti **esito-aware** (guard `COMPLETATO⇒esito`), `fn_log_evento_dominio`
>   (`DOMINIO_*`), macchina transizioni commesse, codici errore, GRANT. **Più**
>   `config.nature_vendita` come groundwork. *(Aggiornamento 2026-06-20: lo split
>   per natura — `fn_push_preventivo_a_ordine`, routing MERCE→ordine/SERVIZIO→commessa,
>   `uq_ordini_da_preventivo` — è stato **poi consegnato e attivato** (handoff
>   2026-06-09); la frase "non consegnati/rinviati" era vera solo al 2026-06-08.)*
> - **Fase C (BE)** — ✅ **CONSEGNATA** (2026-06-08): handler `vendita.push_preventivo`
>   (atomico, idempotente, policy via c7-2), registrazione `HANDLER_MAP` lazy,
>   dispatch su `IN_CORSO` in transazione unica, accoppiamento accettazione↔flusso.
>   9 test unitari verdi + 837 regressione verde. *(Aggiornamento 2026-06-20:
>   l'accoppiamento accettazione↔flusso **M2** — `completa_approvazione_da_flusso` +
>   endpoint `approvazione-flusso` — è stato **poi rimosso** e sostituito
>   dall'handler event-driven `vendita.accetta_preventivo` su COMPLETATO+POSITIVO via
>   `template_flussi_handler_eventi`; vedi brief BE §8.3.)*
> - **Fase D (FE)** — ✅ **CONSEGNATA** (2026-06-08, build+lint verdi): roadmap
>   percorso da `template_flussi` (`PraticaPercorso.vue` + endpoint
>   `GET /pratiche/<id>/percorso/`, creazione flussi **template-bound**);
>   PREVENTIVAZIONE (apri+collega preventivo ROOT); F1 routing
>   `APPROVAZIONE_CLIENTE`→M2; accept dialog nascosto sul percorso pratica.
>   Revisione critica + cleanup dead code applicati. **Residuo**: smoke UI E2E
>   runtime. Vedi brief FE.
>
> Le voci §8.2/§8.3 sotto restano la **specifica della visione ampia** (split
> natura): si riprenderanno in un secondo giro, dopo la validazione del
> sottoinsieme PREVENTIVI.

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

### 8.5 Fase E — Validazione e decanto — ✅ COMPLETATA (2026-06-10 → 2026-06-12)

> **Esito**: validazione runtime end-to-end eseguita con smoke contro DB+API
> reali (`smoke-test-pratica-preventivi-conferma.sh`,
> `smoke-test-preventivi-smistamento-ordine.sh`,
> `smoke-test-ordini-giro-commessa.sh`), sia da super admin (36 OK) sia da
> **operatore reale** (33 OK, con seed delle azioni di processo pratiche —
> prima mancanti — vedi `work-done/brief-db-azioni-processo-pratiche.md`).
> La validazione ha scovato e chiuso bug reali a ogni livello (competenza
> NOT NULL + policy `competenza_mese` ignorata nella fn di push; jsonb-as-str
> su `handler_params`/`meta`; resolver commessa cieco al multi-sorgente; 4
> buchi della generazione cross-pratica). In corsa la Fase E si è estesa col
> cantiere **workflow v2** (ripetibilità, bivi, lenti contesto, guard
> chiusura): vedi
> [analisi-pratiche-workflow-v2](../work-done/analisi-pratiche-workflow-v2.md).

- ✅ Esecuzione end-to-end sotto pratica: richiesta → preventivo misto →
  (split per natura) → ordine + commessa emittibile; preventivo EVASO,
  giornale `DOMINIO_*`, pratica chiudibile. (La fatturazione a valle —
  pipeline lotto sulla commessa PRONTA — era già collaudata; il ramo
  contratto resta fuori dal preventivo per modello: ricorrente → offerta.)
- ✅ Caso misto merce+servizio validato (incluso multi-sorgente: 2 preventivi
  → stessa commessa).
- ✅ Caso "azienda Beta" (autonomi senza pratica): coperto dagli smoke di
  smistamento standalone (genera-ordine + push-commessa con gate EVASO).
- ✅ Operatori reali: giro completo con permessi da operatore (faccia
  OPERATORE, azioni di processo seedate, abilitazioni come dato di
  installazione).
- ✅ Rivalutazione `log_evento_dominio`: helper **confermato** — i 3 tipi
  evento `DOMINIO_*` in uso reale funzionano; la promozione a
  `config.tipi_eventi_giornale` si rivaluta in Fase F quando un secondo
  consumatore porterà nuovi tipi evento.
- ✅ Aggiornamento `mappa-concentrica.md`: `pratiche` → "validata con primo
  consumatore (vendite), pronta per il secondo".

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
- [gestione-pratiche-v2.md](../work-done/gestione-pratiche-v2.md)
- [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md)
- [analisi-offerta-commerciale.md](../work-done/analisi-offerta-commerciale.md)
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

## 11. Esempio operativo di configurazione: `VENDITA_STANDARD`

> **Stato**: redatto 2026-05-22 come continuazione concreta di §5.
> Questo capitolo **non è un brief DB** (resta livello modello: nomi, semantica,
> esempi runtime). I DDL pronti restano in Fase B (§8.2).
>
> **Cosa contiene**:
>
> - §11.0 chiude le decisioni aperte §7.2 (D0 = entità natura; D1 = derivazione
>   natura su riga) con esito **decisivo, irreversibile per v1**.
> - §11.1 mostra la **configurazione completa** del processo preventivo
>   (`VENDITA_STANDARD`): seed + handler + esempio runtime end-to-end.
> - §11.2 (in scrittura successiva) farà l'analogo per il **contratto**.
> - §11.3 (in scrittura successiva) descrive il **percorso fatturazione immediata
>   → commessa** come ramo dell'handler `vendita.push_preventivo`.

### 11.0 Chiusura decisioni aperte D0 / D1

#### 11.0.1 Verdetto D0 — entità "natura ai fini del routing post-accettazione"

**Audit dello schema esistente** (2026-05-22) ha verificato in
`catalogo.articoli`, `vendite.articoli_tipologie`, `vendite.articoli_gruppi`,
`vendite.articoli_spesa`, `vendite.preventivi_righe`, `config.*`:

| Candidata                              | Nata per                                                                          | Vale per il routing?                       |
| -------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------ |
| `vendite.articoli_tipologie`           | Raggruppamenti merceologici / analisi statistiche                                 | NO — concetto vicino ma diverso            |
| `vendite.articoli_gruppi`              | Raggruppamenti commerciali per reportistica                                       | NO — non discrimina BENE / SERVIZIO        |
| `catalogo.articoli.is_composito`       | Composizione BoM (presenza componenti)                                            | NO — ortogonale alla natura                |
| `catalogo.articoli.voce_utility`       | Mapping verso utility (energia, idrico, ...)                                      | NO — concetto del dominio utility, non BoM |
| Nessun campo su `vendite.preventivi_righe` esistente classifica la riga come routing-target. |                                                                                   | —                                          |

**Esito**: nessuna entità nasce per "natura ai fini del routing post-accettazione".
Le candidate più vicine (`articoli_tipologie`) sono raggruppamenti merceologici
nati per altri scopi — il loro riuso ricadrebbe nel **riuso opportunistico vietato**
da §5.3.2.

**Decisione D0 — chiusa**: si introduce in Fase B la nuova tassonomia
`config.nature_vendita`, dedicata e con un solo scopo.

**Valori semantici per v1** (3 righe seed, di cui solo 2 ammesse in preventivo):

| Codice                | Descrizione                                                                                                                                                          | Ammessa nel routing preventivo                                  | Destinazione                                |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| `BENE_FISICO`         | Merce fisica da evadere via magazzino + DDT                                                                                                                          | Sì                                                              | `vendite.ordini`                            |
| `SERVIZIO_UNA_TANTUM` | Servizio una-tantum esecutivo (installazione, consulenza, intervento progettuale)                                                                                    | Sì                                                              | `vendite.commesse` (commessa diretta)       |
| `SERVIZIO_RICORRENTE` | Servizio ricorrente con ciclo di fatturazione periodico (canone manutenzione, supporto, abbonamento)                                                                 | **NO** (vedi nota sotto)                                        | `vendite.contratti` via offerta commerciale |

**Nota architetturale critica — perché 3 valori ma solo 2 ammessi**:

Il modello commerciale di ZeroErp (vedi
[analisi-offerta-commerciale.md](../work-done/analisi-offerta-commerciale.md)
§2) tiene **strutturalmente separati** due assi:

- **Preventivo → Ordine / Commessa** = proposta di transazione puntuale,
  snapshot prezzo riga-per-riga
- **Offerta commerciale → Contratto** = proposta di condizioni quadro
  durature, snapshot versione listino

Il dominio `offerta_commerciale` **non esiste ancora** in ZeroErp (è in
analisi iniziale, stato APERTO). Ma il modello già lo presuppone: la
ricorrenza non passa per il preventivo, per costruzione.

La natura `SERVIZIO_RICORRENTE` esiste a livello `config.nature_vendita` e su
`catalogo.articoli` perché è un dato del **catalogo articolo** (la
"manutenzione annuale" è ricorrente per natura sua, indipendentemente da
dove venga venduta). Ma in `vendite.preventivi_righe` una riga con
`natura_vendita_id = SERVIZIO_RICORRENTE` è **un errore commerciale**: il
preventivo è lo strumento sbagliato per proporre ricorrenza.

**Regola in CONFERMA_VENDITA**: se l'handler trova una riga con natura
`SERVIZIO_RICORRENTE`, **non procede con lo split** e solleva
`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` con messaggio operativo del tipo
"La riga N è di natura ricorrente: non può essere venduta via preventivo.
Emettere un'offerta commerciale separata per le condizioni quadro." Il
flusso si sospende, l'operatore corregge (cambia natura riga, oppure
rimuove la riga dal preventivo e apre una pratica `OFFERTA_QUADRO`
parallela — vedi §11.2 in scrittura).

**Cardinalità (3) giustificata**: pur essendo `SERVIZIO_RICORRENTE` non
ammesso nel routing del preventivo, la tabella `config.nature_vendita`
deve poterlo rappresentare perché:

- Il catalogo articolo lo richiede (un articolo nasce ricorrente nel
  catalogo, anche se viene poi venduto solo via offerta commerciale).
- L'handler usa quel valore per riconoscere e bloccare correttamente
  l'errore (senza il valore, non distinguerebbe "ricorrente" da "natura
  ignota").
- L'offerta commerciale (futura) leggerà la stessa tassonomia per il
  proprio routing verso contratto.

Suddivisioni più fini (es. `BENE_FISICO_SU_COMMESSA` per beni venduti dentro
progetto, `SERVIZIO_RICORRENTE_USAGE` per ricorrenze a consumo) non vengono
introdotte a priori: si valutano al secondo caso reale (manifesto §7).

**Mapping natura → sorgente di destinazione** (per l'handler): tabella
dichiarativa, non hardcoded. In Fase B la mappa vive come colonna su
`config.nature_vendita` (es. `sorgente_codice_destinazione VARCHAR`, FK virtuale
verso `config.sorgenti.codice`) — così aggiungere una natura nuova non richiede
modifica codice handler. Per `SERVIZIO_RICORRENTE` la destinazione è
`CONTRATTO` ma viene letta dal flusso `OFFERTA_QUADRO`, **non** dal flusso
`VENDITA_STANDARD`.

#### 11.0.2 Verdetto D1 — derivazione natura su riga

**Decisione D1 — chiusa**: la natura su `vendite.preventivi_righe` è
**derivata + sovrascrivibile**, con la regola operativa seguente:

1. **Catalogo articolo** (`catalogo.articoli.natura_vendita_id`, FK opzionale a
   `config.nature_vendita`): il catalogista, in fase di seed articolo, dichiara
   la natura "tipica" dell'articolo. È un dato opzionale: articoli generici
   senza natura tipica restano con `NULL`.
2. **Riga preventivo** (`vendite.preventivi_righe.natura_vendita_id`, FK opzionale):
   alla creazione della riga, default = `catalogo.articoli.natura_vendita_id`
   se valorizzata; altrimenti `NULL`. L'operatore può **sempre** sovrascrivere
   il default in fase di editing del preventivo (drawer riga).
3. **Vincolo CHECK su riga** in apertura del flusso `CONFERMA_VENDITA`:
   `natura_vendita_id IS NOT NULL` per **tutte** le righe del preventivo,
   altrimenti il flusso si sospende con errore parlante
   `E_VENDITA_RIGA_SENZA_NATURA` e l'operatore deve smistare manualmente
   (Opzione 3 fallback §5.3.2).

**Perché derivata + sovrascrivibile**:

- Riusare il dato del catalogo riduce l'overhead operatore al 95% dei casi
  (articolo "Server Dell PowerEdge" → BENE_FISICO una sola volta a livello
  catalogo, mai più toccato).
- L'override è necessario perché casi limite esistono (es. "vendiamo lo stesso
  modem come bene a un cliente e come servizio incluso a un altro" — stesso
  articolo, righe con natura diversa).
- Il vincolo a `CONFERMA_VENDITA` (non all'INSERT) lascia all'operatore la
  libertà di compilare un preventivo "bozza" senza natura su tutte le righe,
  e di smistare al momento opportuno. Coerente con §5.3.2 (sospensione del
  flusso).

**Quello che NON facciamo**:

- Non rendiamo `natura_vendita_id` `NOT NULL` su `preventivi_righe` (spezzerebbe
  preventivi in BOZZA / preventivi importati storici).
- Non derivazione "intelligente" da altri campi (es. "se prezzo è canone
  mensile allora SERVIZIO_RICORRENTE") — il dato è dichiarativo, non inferito.

#### 11.0.3 Conseguenza per l'esempio §11.1

Da questo punto in poi, l'esempio assume:

- esiste `config.nature_vendita` con le 3 righe di §11.0.1;
- esiste `catalogo.articoli.natura_vendita_id` (FK opzionale);
- esiste `vendite.preventivi_righe.natura_vendita_id` (FK opzionale, derivato +
  sovrascrivibile);
- esiste `config.messaggi_errore` con `E_VENDITA_RIGA_SENZA_NATURA`.

Le ALTER DDL relative sono **deliverable di Fase B**; qui si tratta il
modello come dato.

### 11.1 Configurazione completa del processo preventivo

#### 11.1.1 Seed `config.sorgenti` (verifica + completamento)

`config.sorgenti` è la tabella dei tipi di documento citabili da
`pratiche_sorgenti` e `commesse_sorgenti`. Già esistente, con `PREVENTIVO` e
`CONTRATTO` seedati. Per il caso `VENDITA_STANDARD` servono inoltre:

| Codice      | Descrizione                          | Stato                                          |
| ----------- | ------------------------------------ | ---------------------------------------------- |
| `PREVENTIVO` | Preventivo di vendita               | Già seedato                                    |
| `CONTRATTO` | Contratto di vendita ricorrente     | Già seedato                                    |
| `ORDINE`    | Ordine di vendita beni fisici       | **Da verificare in Fase B**: se assente, seed |
| `COMMESSA`  | Commessa di esecuzione              | **Da verificare in Fase B**: se assente, seed |

Convenzione di naming §6.3 rispettata (singolare maiuscolo).

#### 11.1.2 Seed `config.nature_vendita` (nuova tabella, §11.0.1)

```text
codice                 descrizione                            sorgente_codice_destinazione
─────────────────────  ─────────────────────────────────────  ────────────────────────────
BENE_FISICO            Bene fisico da evadere via magazzino    ORDINE
SERVIZIO_UNA_TANTUM    Servizio una-tantum esecutivo           COMMESSA
SERVIZIO_RICORRENTE    Servizio ricorrente con canone          CONTRATTO
```

#### 11.1.3 Seed `pratiche.tipi_prestazione`

Una sola riga per cominciare (manifesto §7 — secondo template `VENDITA_RAPIDA`
o `VENDITA_RICORRENTE_PURA` solo quando un caso reale lo chiederà):

| Campo              | Valore                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `codice`           | `VENDITA_STANDARD`                                                                                |
| `categoria`        | `COMMERCIALE`                                                                                     |
| `descrizione`      | Processo commerciale standard: dalla richiesta cliente all'esecuzione (ordine, commessa, contratto) |
| `pre_attivazione`  | `false`                                                                                           |
| `post_attivazione` | `false`                                                                                           |

Note:

- `pre_attivazione = false` e `post_attivazione = false` insieme significano
  "ammessa indipendentemente dallo stato BA del cliente" (un preventivo si
  può fare a un prospect senza BA attivo, oppure a un cliente già attivo per
  ampliamento fornitura).
- La validazione contesto anagrafico (soggetto / soggetto_ruolo / istanza
  utility) è già garantita dal trigger v2 `trgfn_pratiche_guard_contesto`
  (vedi `gestione-pratiche-v2.md` §1.2): per `VENDITA_STANDARD` ci si aspetta
  `soggetto_id` + `soggetto_ruolo_id` (ruolo cliente), `istanza_utility_id`
  generalmente `NULL`.

#### 11.1.4 Seed `pratiche.template_flussi` + prerequisiti + canali

| Seq | Codice                 | Direzione | Obbligatorio          | Esito atteso                                                           | Handler                   |
| --- | ---------------------- | --------- | --------------------- | ---------------------------------------------------------------------- | ------------------------- |
| 10  | `RICHIESTA_CLIENTE`    | ENTRATA   | true                  | POSITIVO (richiesta accettata) o NEGATIVO (richiesta non perseguibile) | NULL (manuale)            |
| 20  | `PREVENTIVAZIONE`      | INTERNA   | true                  | POSITIVO (preventivo EMESSO)                                           | NULL (manuale, drawer)    |
| 30  | `APPROVAZIONE_CLIENTE` | ENTRATA   | true                  | POSITIVO (ACCETTATO) / NEGATIVO (RIFIUTATO)                            | NULL (manuale)            |
| 40  | `CONFERMA_VENDITA`     | INTERNA   | true (se 30 positivo) | POSITIVO (split eseguito su ordine e/o commessa)                       | `vendita.push_preventivo` |

Il flusso 40 **non** può generare contratti: la ricorrenza viaggia su un
asse separato (vedi §11.0.1 nota architetturale e §11.2).

**Prerequisiti** (`pratiche.template_flussi_prerequisiti`):

- `PREVENTIVAZIONE` richiede `RICHIESTA_CLIENTE` POSITIVO
- `APPROVAZIONE_CLIENTE` richiede `PREVENTIVAZIONE` POSITIVO
- `CONFERMA_VENDITA` richiede `APPROVAZIONE_CLIENTE` POSITIVO

**Canali ammessi** (`pratiche.template_flussi_canali`): tutti i flussi ENTRATA
accettano i canali standard di `config.canali_pratiche` (email, telefono,
sportello, portale). I flussi INTERNA non hanno canale (sono operazioni
back-office).

#### 11.1.5 Seed `pratiche.handler_flussi`

Una sola riga per `VENDITA_STANDARD` v1 (il flusso `CONFERMA_VENDITA` è
l'unico con handler):

| Campo            | Valore                                                                |
| ---------------- | --------------------------------------------------------------------- |
| `handler_key`    | `vendita.push_preventivo`                                             |
| `descrizione`    | Split del preventivo per natura di riga e generazione 0..N destinazioni |
| `attivo`         | `true`                                                                |

`pratiche.template_flussi.handler_id` per `CONFERMA_VENDITA` punta a questa
riga.

**`handler_params` (statico, sul template `CONFERMA_VENDITA`)** — JSONB di
default:

```json
{
  "natura_obbligatoria_su_tutte_le_righe": true,
  "comportamento_riga_senza_natura": "SOSPENDI_FLUSSO",
  "comportamento_riga_ricorrente": "SOSPENDI_FLUSSO",
  "fatturazione_immediata_default": false
}
```

Quattro parametri configurabili per template senza toccare codice:

- `natura_obbligatoria_su_tutte_le_righe`: se `true` il flusso fallisce con
  `E_VENDITA_RIGA_SENZA_NATURA` quando esiste una riga con
  `natura_vendita_id IS NULL`. Se `false` (variante per processi
  sperimentali), le righe senza natura vengono raccolte in un report e
  l'operatore decide manualmente.
- `comportamento_riga_senza_natura`: `SOSPENDI_FLUSSO` (default v1) vs
  `IGNORA_RIGA` (variante futura, non implementata).
- `comportamento_riga_ricorrente`: `SOSPENDI_FLUSSO` (default v1, vedi
  §11.0.1: la riga ricorrente in un preventivo è un errore commerciale → il
  flusso si sospende con `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`). Variante
  futura `IGNORA_E_SCARTA` (la riga viene espunta dallo split, lo split
  procede sulle altre nature, operatore avvisato). Non in v1.
- `fatturazione_immediata_default`: vedi §11.3 (in scrittura successiva).

**`flussi.meta` (dinamico, popolato dall'operatore al lancio del flusso)** —
JSONB del singolo flusso istanziato:

```json
{
  "preventivo_id": 4711,
  "preventivo_uid": "P/2026/0042",
  "fatturazione_immediata": false,
  "note_operatore": "Cliente conferma via email del 15/5"
}
```

#### 11.1.6 Seed `pratiche.competenze_flussi` (esempio per un'installazione)

Matrice operatore × template_flusso × unità organizzativa (vedi
`gestione-pratiche-v2.md` §6.2). Esempio per un'azienda con reparto
commerciale e back-office:

| `template_flusso`      | `unita_organizzativa` | `risorsa_umana` | `attivo` |
| ---------------------- | --------------------- | --------------- | -------- |
| `RICHIESTA_CLIENTE`    | COMMERCIALE           | Alice           | true     |
| `RICHIESTA_CLIENTE`    | COMMERCIALE           | Bob             | true     |
| `PREVENTIVAZIONE`      | COMMERCIALE           | Alice           | true     |
| `PREVENTIVAZIONE`      | COMMERCIALE           | Bob             | true     |
| `APPROVAZIONE_CLIENTE` | COMMERCIALE           | Alice           | true     |
| `APPROVAZIONE_CLIENTE` | COMMERCIALE           | Bob             | true     |
| `CONFERMA_VENDITA`     | BACK_OFFICE           | Carla           | true     |

Lettura: Alice e Bob (commerciale) prendono in carico tutto il front (10/20/30);
Carla (back-office) si occupa del flusso 40 dove avviene lo split tecnico.

Il seed è **operativo**: lo cura l'admin dell'azienda installatrice via UI
admin (CRUD competenze esistente, vedi `gestione-pratiche-v2.md` §6.5). Non
viene scritto nel brief DB iniziale — il brief seeda solo un esempio per i
test pgTAP. La popolazione reale è atto di setup operativo del cliente.

#### 11.1.7 Esempio runtime end-to-end (caso misto 3+1)

Scenario: cliente "Rossi SRL" (già attivo come cliente per emittente fiscale
`EF-001`) chiama il commerciale Alice per fornitura datacenter:

- 3 server fisici (BENE_FISICO)
- installazione e configurazione (SERVIZIO_UNA_TANTUM)

Il cliente ha anche bisogno di manutenzione annuale + supporto 24/7
(`SERVIZIO_RICORRENTE`), ma Alice **non** la mette nel preventivo perché la
ricorrenza viaggia su un asse separato (offerta commerciale → contratto, vedi
§11.0.1). In una sessione successiva Alice apre una pratica `OFFERTA_QUADRO`
parallela per la parte ricorrente (vedi §11.2). Le due pratiche restano
distinte ma collegabili a livello cliente.

**t0 — Alice crea la pratica** dalla dashboard pratiche, scegliendo:

| Campo                     | Valore                                                           |
| ------------------------- | ---------------------------------------------------------------- |
| `emittente_fiscale_id`    | EF-001                                                           |
| `tipo_prestazione_id`     | VENDITA_STANDARD                                                 |
| `soggetto_id`             | (UUID di Rossi SRL)                                              |
| `soggetto_ruolo_id`       | (ruolo CLIENTE di Rossi SRL)                                     |
| `istanza_utility_id`      | NULL (vendita non legata a utility)                              |
| `priorita_id`             | NORMALE                                                          |
| `risorsa_umana_id`        | Alice (auto, dall'utente loggato)                                |
| `unita_organizzativa_id`  | COMMERCIALE                                                      |
| `descrizione`             | "Fornitura datacenter Rossi SRL"                                 |
| `canale_origine_id`       | TELEFONO                                                         |

Trigger: codice pratica `PRA-0001234` assegnato; stato `BOZZA`; giornale registra
`PRATICA_CREATA`. Il **percorso suggerito** dei 4 flussi (da `template_flussi`)
viene mostrato all'operatore in ordine di esecuzione; i flussi concreti si
istanziano/eseguono **progressivamente**, non tutti in blocco alla creazione.

> **⚠ Nota correttiva (2026-06-07)** — "istanziati automaticamente alla
> creazione" sarebbe **inesatto e indesiderato**: pre-creare tutti i flussi è
> sbagliato perché un flusso può dipendere da scelte fatte nei flussi precedenti
> (percorsi condizionali). Modello corretto: il `template_flussi` è la **mappa**
> mostrata come roadmap; l'esecuzione è **progressiva**, governata dalle regole
> di prerequisito già esistenti (`trgfn_flussi_guard_prerequisiti`). Il codice
> attuale (`crea_pratica`) non materializza i flussi alla creazione, ed è
> coerente con questo modello. Vedi §5.5.

**t1 — Alice avanza alla stato APERTA**, e completa `RICHIESTA_CLIENTE`
inserendo nota "richiesta perseguibile, prepariamo preventivo entro venerdì" →
esito POSITIVO.

Giornale: `STATO_CAMBIATO BOZZA→APERTA`, `data_apertura` valorizzata,
`FLUSSO_STATO_CAMBIATO RICHIESTA_CLIENTE → COMPLETATO`.

**t2 — Alice apre il flusso `PREVENTIVAZIONE`**. Il flusso espone un bottone
"Apri preventivo collegato" che apre `PreventivoDrawer` in CREATE mode con
`pratica_id` pre-impostato in `flussi.meta`. Alice compila il preventivo:

| Riga | Articolo                 | Qta | Prezzo unit. | Natura (derivata)                 |
| ---- | ------------------------ | --- | ------------ | --------------------------------- |
| 1    | Dell PowerEdge R750      | 3   | 8.500        | BENE_FISICO (da articolo)         |
| 2    | Installazione DataCenter | 1   | 4.500        | SERVIZIO_UNA_TANTUM (da articolo) |

Il preventivo viene salvato come BOZZA, poi EMESSO. Al salvataggio della prima
versione, il backend popola `pratiche.pratiche_sorgenti(pratica_id, sorgente_tipo=PREVENTIVO, sorgente_uid=P/2026/0042, ruolo=ROOT)`.

Alice completa il flusso `PREVENTIVAZIONE` con esito POSITIVO. Giornale:
`DOMINIO_PREVENTIVO_CREATO`, `FLUSSO_STATO_CAMBIATO PREVENTIVAZIONE → COMPLETATO`.

**t3 — Cliente accetta via email**. Alice apre il flusso
`APPROVAZIONE_CLIENTE`, registra l'esito POSITIVO con allegato (PDF
dell'accettazione via email). Internamente questo aggiorna anche lo stato del
preventivo a ACCETTATO via dialog dedicato (decisione `fatturazione_immediata`
+ `competenza` — pattern `feedback_dialog_cambio_stato_dati_processo`).

Giornale: `DOMINIO_PREVENTIVO_ACCETTATO` (con `fatturazione_immediata: false`),
`FLUSSO_STATO_CAMBIATO APPROVAZIONE_CLIENTE → COMPLETATO`.

**t4 — Carla (back-office) apre `CONFERMA_VENDITA`** dalla coda lavoro
(competenza). Il flusso parte in `IN_CORSO`, l'handler `vendita.push_preventivo`
si attiva:

1. Verifica `natura_obbligatoria_su_tutte_le_righe = true` → entrambe le righe
   hanno natura: OK.
2. Verifica `comportamento_riga_ricorrente`: nessuna riga ha natura
   `SERVIZIO_RICORRENTE` → nessun blocco.
3. Raggruppa per natura:
   - BENE_FISICO: riga 1 (3×PowerEdge)
   - SERVIZIO_UNA_TANTUM: riga 2 (installazione)
4. Per ciascun raggruppamento chiama la fn DB corrispondente (mapping
   `config.nature_vendita.sorgente_codice_destinazione`):
   - `vendite.fn_push_preventivo_a_ordine(p_preventivo_id=4711, p_righe_ids=[1], p_pratica_id=...)` → idempotenza §5.3.3
   - `vendite.fn_push_preventivo_a_commessa(... p_righe_ids=[2] ...)` (estensione della esistente)
5. Per ciascuna destinazione creata, registra `pratiche_sorgenti(ruolo=COLLEGATO)`
   e scrive nel giornale `DOMINIO_<ENTITA>_CREATA` con `meta` strutturato
   (§6.8).
6. Verifica che tutte le righe del preventivo siano smistate → transizione
   preventivo `ACCETTATO → EVASO` (§5.3.1).

Giornale finale del flusso 40:

| Evento                     | meta                                                               |
| -------------------------- | ------------------------------------------------------------------ |
| `FLUSSO_STATO_CAMBIATO`    | `CONFERMA_VENDITA: DA_ESEGUIRE → IN_CORSO`                         |
| `DOMINIO_ORDINE_CREATO`    | `{ordine_id: 8801, righe_ids: [1], preventivo_id: 4711}`           |
| `DOMINIO_COMMESSA_CREATA`  | `{commessa_id: 7701, righe_ids: [2], preventivo_id: 4711}`         |
| `DOMINIO_PREVENTIVO_EVASO` | `{preventivo_id: 4711}`                                            |
| `FLUSSO_STATO_CAMBIATO`    | `CONFERMA_VENDITA: IN_CORSO → COMPLETATO (POSITIVO)`               |
| `STATO_CAMBIATO`           | `pratica: APERTA → CHIUSA` (tutti i flussi obbligatori completati) |

A questo punto la pratica `PRA-0001234` è chiusa. Aprendo il drawer, l'operatore
vede il giornale completo end-to-end, le 3 sorgenti in `pratiche_sorgenti`
(1 preventivo ROOT + 1 ordine + 1 commessa COLLEGATI), e da ciascuna sorgente
può navigare al documento di dominio. La parte ricorrente (manutenzione
annuale) verrà gestita in una pratica `OFFERTA_QUADRO` separata, eventualmente
collegabile per cliente via report cross-pratica (`soggetto_id` comune).

#### 11.1.8 Esempio runtime in caso anomalo (riga senza natura)

Scenario: stesso preventivo ma la riga 2 (Installazione DataCenter) è un articolo
generico senza natura tipica nel catalogo; Alice non ha compilato manualmente.

**t4 — Carla apre `CONFERMA_VENDITA`**. L'handler trova `righe[2].natura_vendita_id IS NULL`. Con `comportamento_riga_senza_natura = SOSPENDI_FLUSSO`:

1. L'handler **non** procede con lo split.
2. Solleva `E_VENDITA_RIGA_SENZA_NATURA` con `meta = {righe_senza_natura: [2]}`.
3. Il flusso transita in stato `SOSPESO` (non `FALLITO`, perché è risolvibile).
4. Giornale: `FLUSSO_STATO_CAMBIATO CONFERMA_VENDITA → SOSPESO`, evento
   `DOMINIO_RICHIESTA_SMISTAMENTO_RIGHE` con elenco righe.

**t5 — Carla apre il PreventivoDrawer dalla pratica**, va sulla riga 2, sceglie
manualmente la natura `SERVIZIO_UNA_TANTUM`, salva. Il preventivo non cambia
stato (resta EVASO_PARZIALE o ACCETTATO se non era stato evaso ancora; vedi
modello stati preventivi).

**t6 — Carla rilancia `CONFERMA_VENDITA`** (azione "Riprendi" sul flusso
sospeso). L'handler ripete il check: ora tutte le righe hanno natura → split
procede normalmente come §11.1.7.

#### 11.1.9 Cosa rimane in v1 e cosa è già confinato

**In v1 dell'esempio**:

- Catalogo articolo con `natura_vendita_id` opzionale e derivazione automatica
  su nuova riga preventivo (DDL + trigger di default in Fase B).
- Handler `vendita.push_preventivo` con split per natura, idempotente per
  costruzione (§5.3.3), errore parlante su riga senza natura e su riga
  ricorrente.
- 2 funzioni DB di push (preventivo → ordine, preventivo → commessa):
  `fn_push_preventivo_a_ordine` (nuova) e `fn_push_preventivo_a_commessa`
  (estensione dell'esistente con `p_righe_ids`). Nessuna
  `fn_push_preventivo_a_contratto`: la ricorrenza non passa dal preventivo.
- Filtro `fn_list_preventivi_da_pushare`: esclude preventivi già pushati per
  natura (preventivo è EVASO solo quando tutte le nature ammesse sono
  smistate).

**Già confinato fuori v1** (in coerenza con manifesto §7):

- Variante `IGNORA_RIGA` di `comportamento_riga_senza_natura` e
  `IGNORA_E_SCARTA` di `comportamento_riga_ricorrente`.
- Derivazione natura "intelligente" da altri campi del preventivo.
- Cancellazione di una destinazione e ripush (es. ordine creato per errore →
  delete + ripush). Si valuta dopo casi reali.
- UI dashboard di "righe da smistare" globale (oggi è solo sospensione di un
  flusso pratica per volta).
- Collegamento automatico tra pratica `VENDITA_STANDARD` e pratica
  `OFFERTA_QUADRO` per lo stesso cliente nella stessa trattativa: oggi le due
  pratiche sono indipendenti, eventuali ponti si valutano dopo §11.2 e
  l'introduzione del dominio offerta commerciale.

### 11.2 Ossatura del processo offerta commerciale: `OFFERTA_QUADRO`

> **AVVERTENZA — dominio non ancora introdotto**
>
> Questa sezione descrive **solo l'ossatura** della configurazione pratica per
> l'asse "offerta commerciale → contratto". Il dominio
> `vendite.offerte_commerciali` (tabelle, service, view, drawer) **non esiste
> oggi in ZeroErp**: è in stato di analisi iniziale APERTA, vedi
> [analisi-offerta-commerciale.md](../work-done/analisi-offerta-commerciale.md)
> §7.
>
> Per coerenza con il manifesto §III bis (non disegnare astrazioni che il
> dominio reale non ha ancora chiesto), §11.2 si ferma a:
>
> - il `tipo_prestazione`
> - i `template_flussi` paralleli a `VENDITA_STANDARD`
> - l'`handler_flussi` di push
>
> **Nessun esempio runtime**: scriverlo senza l'entità sottostante sarebbe
> fantasia. Il runtime end-to-end (con eventi giornale, stati, transizioni
> preventivo-like) si scriverà solo dopo la chiusura delle decisioni §5 di
> `analisi-offerta-commerciale.md` e l'esistenza effettiva di
> `vendite.offerte_commerciali` come tabella popolabile.
>
> Lo scopo di §11.2 è **mostrare che il motore pratiche regge senza
> riscrittura** il secondo asse commerciale (simmetria con §11.1), non
> proporre brief operativi.

#### 11.2.1 Seed `pratiche.tipi_prestazione`

| Campo              | Valore                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| `codice`           | `OFFERTA_QUADRO`                                                                                        |
| `categoria`        | `COMMERCIALE`                                                                                           |
| `descrizione`      | Processo offerta commerciale: dalla richiesta di condizioni quadro all'attivazione del contratto         |
| `pre_attivazione`  | `false`                                                                                                 |
| `post_attivazione` | `false` (un'offerta si può fare a prospect senza BA o a cliente già attivo per nuovo contratto)         |

Stessa logica `VENDITA_STANDARD` sul contesto anagrafico: ci si aspetta
`soggetto_id` + `soggetto_ruolo_id` (ruolo cliente o prospect), `istanza_utility_id`
opzionale (rilevante per offerte legate a una specifica utility, es. fornitura
elettrica per un punto di consegna).

#### 11.2.2 Seed `pratiche.template_flussi`

Specchio simmetrico di §11.1.4, riformulato per la semantica offerta/contratto:

| Seq | Codice                  | Direzione | Obbligatorio          | Esito atteso                                                                | Handler                  |
| --- | ----------------------- | --------- | --------------------- | --------------------------------------------------------------------------- | ------------------------ |
| 10  | `RICHIESTA_QUADRO`      | ENTRATA   | true                  | POSITIVO (richiesta di condizioni quadro accettata)                         | NULL (manuale)           |
| 20  | `EMISSIONE_OFFERTA`     | INTERNA   | true                  | POSITIVO (offerta commerciale EMESSA in `vendite.offerte_commerciali`)      | NULL (manuale, drawer)   |
| 30  | `APPROVAZIONE_CLIENTE`  | ENTRATA   | true                  | POSITIVO (ACCETTATA) / NEGATIVO (RIFIUTATA) / SCADUTA                       | NULL (manuale)           |
| 40  | `ATTIVAZIONE_CONTRATTO` | INTERNA   | true (se 30 positivo) | POSITIVO (contratto creato in DRAFT o ATTIVO secondo configurazione)        | `offerta.push_a_contratto` |

**Parallelismo con §11.1.4** (mantenuto per scelta architetturale):

- `RICHIESTA_QUADRO` ↔ `RICHIESTA_CLIENTE` (entrambi registrano la
  domanda iniziale)
- `EMISSIONE_OFFERTA` ↔ `PREVENTIVAZIONE` (entrambi producono il documento di
  proposta nel rispettivo dominio)
- `APPROVAZIONE_CLIENTE` identico in entrambi i template — i due processi
  condividono il concetto di "esito esplicito del cliente" e in futuro
  potranno condividere il template, oppure restare separati a seconda di
  scelte di canale (es. firma digitale obbligatoria per offerte quadro)
- `ATTIVAZIONE_CONTRATTO` ↔ `CONFERMA_VENDITA` (entrambi eseguono il push
  verso le destinazioni operative del rispettivo asse)

**Prerequisiti** identici al pattern §11.1.4 (10→20→30→40, con POSITIVO).

**Canali ammessi**: gli stessi di `VENDITA_STANDARD` per i flussi ENTRATA
(email, telefono, sportello, portale).

#### 11.2.3 Seed `pratiche.handler_flussi`

| Campo         | Valore                                                                                |
| ------------- | ------------------------------------------------------------------------------------- |
| `handler_key` | `offerta.push_a_contratto`                                                            |
| `descrizione` | Crea un contratto a partire da un'offerta commerciale ACCETTATA (snapshot versione listino + eccezioni proposte) |
| `attivo`      | `true`                                                                                |

`pratiche.template_flussi.handler_id` per `ATTIVAZIONE_CONTRATTO` punta a
questa riga.

**`handler_params` (statico, sul template `ATTIVAZIONE_CONTRATTO`)** — JSONB di
default (proposta, da chiudere insieme alle decisioni §5 dell'analisi offerta):

```json
{
  "stato_contratto_creato": "DRAFT",
  "richiede_versione_listino_attiva": true,
  "comportamento_listino_aggiornato_post_emissione": "RIEMETTI_OFFERTA"
}
```

Tre parametri:

- `stato_contratto_creato`: `DRAFT` (default v1, contratto creato e
  l'operatore lo attiva esplicitamente) vs `ATTIVO` (creazione e attivazione
  in un colpo solo — variante per processi B2B con accordo già fermo).
  Mappato sulle decisioni §5.4 dell'analisi offerta commerciale.
- `richiede_versione_listino_attiva`: se `true`, il push fallisce se la
  versione listino citata dall'offerta non è più ATTIVA al momento
  dell'`ATTIVAZIONE_CONTRATTO`. Mappato sulla decisione §5.3 dell'analisi
  offerta.
- `comportamento_listino_aggiornato_post_emissione`: `RIEMETTI_OFFERTA`
  (default conservativo, vedi §5.3 dell'analisi: l'offerta è fissata
  all'emissione, se cambia il listino prima dell'accettazione si forza una
  revisione) vs `AGGIORNA_AUTOMATICAMENTE`.

#### 11.2.4 Idempotenza `offerta.push_a_contratto`

In coerenza con §6.9 (convenzione trasversale di idempotenza cross-dominio),
il push offerta → contratto **deve** essere idempotente per costruzione. La
proposta di implementazione (DDL pronto solo in Fase B post-introduzione del
dominio):

```sql
CREATE UNIQUE INDEX uq_contratti_da_offerta
  ON vendite.contratti (sorgente_uid)
  WHERE sorgente_tipo_id = (SELECT id FROM config.sorgenti
                            WHERE codice = 'OFFERTA_COMMERCIALE');
```

Più check applicativo con `E_OFFERTA_CONTRATTO_GIA_GENERATO` (errore da
registrare in `config.messaggi_errore.csv`).

**Sorgente nuova in `config.sorgenti`**: `OFFERTA_COMMERCIALE` (singolare
maiuscolo come da §6.3). Da seedare contestualmente all'introduzione del
dominio.

#### 11.2.5 Cosa serve per scrivere il runtime di §11.2

Per poter scrivere un esempio runtime end-to-end equivalente a §11.1.7 servono,
nell'ordine, deliverable **fuori scope di questo documento**:

1. Chiusura decisioni §5 di `analisi-offerta-commerciale.md`
   (granularità, eccezioni, listino mobile, workflow accettazione,
   numerazione).
2. Brief DB del dominio `vendite.offerte_commerciali` (testata + eccezioni +
   stati + fn `crea_revisione_*` + fn `push_a_contratto`).
3. Backend `apps/vendite/services/offerte_service.py` + drawer FE
   `OffertaDrawer.vue` (scaffolding su pattern preventivo).
4. Solo allora §11.2 si completa con runtime end-to-end e §11.0 può
   eventualmente promuovere la natura `SERVIZIO_RICORRENTE` da "errore in
   preventivo" a "ammessa in offerta".

Fino ad allora, §11.2 resta a livello di **ossatura del template**, e l'unico
deliverable di Fase B che la tocca è la riserva di sorgente
`OFFERTA_COMMERCIALE` in `config.sorgenti` (se conveniente seedarla in
anticipo per evitare migrazioni successive).

---

## 10. Stato del documento

| Sezione                            | Stato                                                                                                                                                           | Prossima azione                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| §1 Inquadramento                   | Stabile                                                                                                                                                         | —                                                 |
| §2 Tre pattern                     | Stabile, contraddizione `ext_preventivo` risolta (rev. 19 maggio)                                                                                               | —                                                 |
| §3 Giornale backbone               | Chiusa: helper validato in Fase E (3 tipi `DOMINIO_*` in uso reale); promozione a config rivalutata in Fase F                                                   | —                                                 |
| §4 Configurabilità interna pratica | Stabile, esempio §4.5 marcato come didattico                                                                                                                    | —                                                 |
| §5 Caso vendite                    | Chiusa: D0/D1 risolte (§11.0), split per natura consegnato e validato runtime (Fasi B/C/D + E)                                                                  | —                                                 |
| §6 Convenzioni                     | Stabile + §6.9 (idempotenza trasversale); consolidata post-Fase E                                                                                               | —                                                 |
| §7 Decisioni prese                 | Revisione Fase E fatta: decisioni confermate; estese da D1..D4 workflow v2 (ripetibilità, bivi, lenti contesto, guard chiusura)                                 | —                                                 |
| §8 Roadmap                         | Fasi A→E **chiuse** (E completata 2026-06-12, vedi §8.5); motore esteso dal cantiere workflow v2                                                                | **Avvio Fase F** (secondo consumatore, su OK Tid) |

---

*Analisi integrazione domini Anello 3 con motore pratiche — ZeroErp
(2026-05-18, revisione critica 2026-05-19; **Fase E chiusa 2026-06-12**, vedi
§8.5 e [analisi-pratiche-workflow-v2](../work-done/analisi-pratiche-workflow-v2.md)).
Documento vivo, da aggiornare ad ogni Fase chiusa. Prossimo passo: Fase F —
secondo consumatore (candidata: assistenza/ticketing,
[crm-ticketing-pratiche](crm-ticketing-pratiche.md)).*