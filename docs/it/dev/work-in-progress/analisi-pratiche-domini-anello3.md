# Analisi — Pratiche come container di processo: integrazione domini Anello 3

> **Stato**: ANALISI infrastrutturale, nessuna decisione operativa, nessun brief DB
> ancora scritto. Documento di consolidamento delle convenzioni di aggancio fra
> motore `pratiche` (Anello 2) e processi di Anello 3 (`vendite`, `acquisti`,
> `magazzino`, ...).
>
> **Data**: 2026-05-18
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

| Capacità | Componente | Stato |
| --- | --- | --- |
| Catalogo workflow | `pratiche.tipi_prestazione` + `pratiche.template_flussi` (+ prerequisiti, canali, handler) | Operativo |
| Istanza operativa | `pratiche.pratiche` + `pratiche.flussi` | Operativo |
| Macchina a stati | `config.transizioni_stati_pratiche` + `config.transizioni_stati_flussi_pratiche` (config-driven, trigger DB) | Operativo |
| Giornale di bordo | `pratiche.giornale` (append-only, alimentato da trigger) | Operativo |
| Generazione cross-pratica | `pratiche.regole_generazione` + `fn_genera_pratica_da_flusso` | Operativo |
| Dispatch handler | `pratiche.handler_flussi` (registry DB) + `HANDLER_MAP` Python | Predisposto, registry vuoto |
| Sospensioni / SLA | `pratiche.sospensioni` + `formule_tempo` + `calcoli_tempo` | Operativo |
| Coda lavoro 3 livelli | `competenze_flussi` + `fn_coda_lavoro_operatore` + `fn_prendi_in_carico_flusso` | Operativo (dashboard) |
| Ponte verso sorgenti | `pratiche.pratiche_sorgenti` (M:N generico via `config.sorgenti`) | Operativo |
| Note / allegati | `note_pratiche` / `allegati_pratiche` + analoghi per flussi | Operativo |

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
   pratica".
3. **Stabilire come il giornale di bordo registra eventi cross-dominio** in
   modo uniforme, così che diventi la *vista unificata sulle attività
   dell'azienda* prevista nella mappa concentrica §Lungo termine.
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

| Livello | Dove | Quando si setta | Esempio |
| --- | --- | --- | --- |
| Statico | `template_flussi.handler_params` (JSONB) | Configurazione del template | `{"crea_ordine": true, "fatturazione_trigger": "CONFERMATO"}` |
| Dinamico | `flussi.meta` (JSONB) | Runtime, da operatore o da flusso precedente | `{"preventivo_id": 4711, "modalita_consegna": "SPEDIZIONE"}` |

L'handler riceve entrambi e decide cosa fare. Cambiando solo
`handler_params` del template si ottengono varianti del processo **senza
toccare il codice**.

**Quando usarlo**:

- Un flusso deve produrre un effetto **lato dominio** (creare un preventivo,
  pushare un ordine in commessa, inviare un'email, scrivere su una tabella
  esterna).
- L'effetto è ripetibile, idempotente, e configurabile per template.

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

**Tabella**: futura `pratiche.ext_<dominio>` (oggi solo design, vedi guida
pratiche §"Estensioni future"). Esempi citati: `ext_appuntamento`,
`ext_preventivo`, `ext_sopralluogo`, `ext_comunicazione`, `ext_spedizione`.

**Semantica**: una specializzazione 1:1 (o 1:1 con flusso) di una pratica per
un dominio specifico, che porta colonne strutturate proprie del legame, non
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

**Quando NON usarlo**:

- Se i dati appartengono a un documento esterno già esistente (preventivo,
  ordine): vivono lì, pratica li cita con pattern A.
- Se i dati sono pochi e occasionali: stanno in `meta JSONB` finché non
  emerge un secondo caso identico.

**Stato**: nessuna tabella `ext_*` esiste oggi. Andranno introdotte una alla
volta, **trainate** da casi concreti del dominio chiamante.

### 2.4 Risposta diretta al punto 3 del dialogo

Tid aveva chiesto: "non ho capito cosa intendi per `pratiche_sorgenti` vs
`ext_preventivo`".

In sintesi:

| Aspetto | `pratiche_sorgenti` (pattern A) | `ext_preventivo` (pattern C, futuro) |
| --- | --- | --- |
| Cosa lega | Pratica ↔ documento esterno (preventivo, ordine, contratto) | Pratica ↔ dati specifici della pratica nel contesto preventivo |
| Cardinalità | M:N | 1:1 (o 1:1 con flusso) |
| Dove vivono i dati | Nello schema del documento (vendite.preventivi, ecc.) | In `pratiche.ext_preventivo` |
| Cosa registra | "Questa pratica si riferisce al preventivo PRV-0042" | Eventuali dati propri della pratica nel contesto preventivo: es. nota negoziazione, fascicolo trattativa, stato accettazione interno |
| Modifica al motore | Nessuna (tabella già esiste) | Aggiunta di una nuova tabella in `pratiche` |

**Per il caso vendite (preventivi+ordini) basta il pattern A.** Il preventivo
vive in `vendite.preventivi` con tutti i suoi dati. La pratica ci punta tramite
`pratiche_sorgenti`. Non c'è bisogno di `ext_preventivo` finché non emerge un
dato proprio della pratica-nel-contesto-preventivo che non sta bene nel
preventivo stesso né in un flusso pratica.

Se in futuro vorrai memorizzare, su una pratica `VENDITA`, qualcosa del tipo
"appuntamento di firma del preventivo presso il cliente" con data, sede, esito
firma, **quello** sarà candidato per `ext_appuntamento` legato al flusso —
non al preventivo, perché non è un dato del preventivo.

---

## 3. Giornale di bordo come backbone trasversale

Il giornale è la **vista unificata sulle attività dell'azienda** annunciata
nella mappa concentrica (§Lungo termine). Oggi è già operativo come audit
trail interno di pratiche/flussi; questa analisi formalizza come diventa il
canale unico cross-dominio.

### 3.1 Cosa è già coperto

`pratiche.giornale` registra automaticamente, via trigger DB:

| Evento | Origine |
| --- | --- |
| `PRATICA_CREATA` | trigger `trgfn_pratiche_giornale_ins` |
| `STATO_CAMBIATO` (pratica) | `trgfn_pratiche_giornale_stato` |
| `ASSEGNAZIONE_CAMBIATA` | `trgfn_pratiche_giornale_assegnazione` |
| `PRIORITA_CAMBIATA` | `trgfn_pratiche_giornale_priorita` |
| `FLUSSO_CREATO` / `FLUSSO_STATO_CAMBIATO` | `trgfn_flussi_giornale_*` |
| `NOTA_AGGIUNTA` / `ALLEGATO_AGGIUNTO` | `trgfn_note_*` / `trgfn_allegati_*` |
| `SOSPENSIONE_REGISTRATA` / `SOSPENSIONE_CHIUSA` | `trgfn_sospensioni_giornale_*` |

Tutti immutabili (append-only), correlati con `tx_id`, con `meta JSONB` libero
per dettagli specifici dell'evento.

### 3.2 Cosa serve per integrazione cross-dominio

Quando un handler (pattern B) compie un'azione lato dominio, l'evento *del
dominio* va riflesso nel giornale **della pratica** in modo standardizzato.
Esempio: l'handler `PushPreventivoOrdineHandler` crea l'ordine e deve
lasciare nel giornale un evento `DOMINIO_ORDINE_CREATO` con
`meta = {"ordine_id": ..., "preventivo_id": ..., "anno_serie_numero": ...}`.

Due opzioni di design considerate:

| Opzione | Come | Pro | Contro |
| --- | --- | --- | --- |
| Estendere tipi evento giornale | Aggiungere voci a `config.tipi_eventi_giornale` (se esiste) o enum equivalente | Tutto in `pratiche.giornale`, una sola query temporale | I tipi crescono per dominio (proliferazione) |
| Helper service `pratiche_service.log_evento_dominio()` | Wrapper applicativo che fa INSERT in giornale con tipo `DOMINIO_<EVENTO>` libero e meta strutturato | Nessun seed nuovo per ogni evento | I tipi non sono whitelist, validazione solo applicativa |

**Decisione presa** (2026-05-18, default conservativo): il primo brief
operativo (Fase B) userà l'**helper applicativo libero**
`pratiche_service.log_evento_dominio(pratica_id, flusso_id, tipo_evento,
meta)`, con tipo evento testuale convenzionato (`DOMINIO_ORDINE_CREATO`,
`DOMINIO_PREVENTIVO_ACCETTATO`, ...). Nessuna whitelist DB iniziale. Se dopo
i primi 3-4 eventi reali emerge il bisogno di vincoli a schema (raise su
tipo sconosciuto, dropdown filtri, ecc.) si promuove a tabella di
configurazione `config.tipi_eventi_giornale` come secondo passo non
breaking.

### 3.3 Eventi cross-dominio: convenzione di scrittura

Indipendentemente dall'opzione tecnica scelta, la convenzione semantica è:

- **L'evento si registra sul giornale della pratica**, non in un giornale di
  dominio separato. Il giornale di pratica è il backbone.
- **Il record contiene `pratica_id` + `flusso_id` (se applicabile) + `tx_id`**,
  così la correlazione è completa.
- **`meta` JSONB include i riferimenti incrociati**: `ordine_id`,
  `preventivo_id`, `fattura_id`, `commessa_id`, ecc. — sempre con la stessa
  chiave per lo stesso concetto.

Risultato: un operatore che apre la pratica vede in giornale tutta la storia
end-to-end. Un report cross-pratica può cercare per `meta->>'ordine_id'`
ovunque, perché la chiave è la stessa.

### 3.4 Cosa il giornale NON è

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
configurabilità". I quattro livelli di configurabilità del motore:

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

### 4.5 Conseguenza per Tid

Tutti i bivi tipici che hai descritto ("preventivo diventa ordine se richiesto,
altrimenti va in commessa", "fatturazione immediata sì/no") sono casi
configurabili tramite combinazioni dei 4 livelli sopra. Il codice degli
handler resta uno solo per ciascuna azione (es. `PushPreventivoHandler`); le
varianti sono dati.

Esempio concreto applicato al caso vendite (sezione 5 lo dettaglia):

```text
template_flusso "CONFERMA_VENDITA" del tipo "VENDITA_STANDARD"
  handler_id = vendita.push_preventivo
  handler_params = {
    "crea_ordine_se": "BENI_FISICI",         // chiave decisionale
    "fatturazione_trigger_default": "CONFERMATO"
  }

flussi.meta dell'istanza (popolato runtime)
  {
    "natura_vendita": "BENI_FISICI",         // letto dal preventivo o
                                              // settato dall'operatore in
                                              // PREVENTIVAZIONE
    "preventivo_id": 4711
  }

Handler PushPreventivoHandler:
  legge handler_params + flussi.meta
  decide: crea_ordine = (handler_params.crea_ordine_se == meta.natura_vendita)
  ramifica:
    - crea_ordine=true  → fn_push_preventivo_a_ordine(...)
    - crea_ordine=false → push_a_commessa(...) classico
  scrive in giornale: DOMINIO_ORDINE_CREATO o DOMINIO_COMMESSA_CREATA
```

Aggiungere domani un terzo binario (es. "→ offerta commerciale → contratto",
asse dell'analisi-offerta-commerciale) significa:

- aggiungere un terzo branch nell'handler **o** registrare un secondo
  handler `vendita.push_a_contratto` collegato a un template
  `CONFERMA_VENDITA_RICORRENTE` distinto.

Quale dei due dipende dall'esito della validazione vendite: si decide alla
luce dei dati, non a priori.

---

## 5. Caso di validazione: vendite (preventivi + ordini)

Questa sezione descrive il **primo consumatore reale** che valida i pattern
§2-§4. Non è il piano operativo definitivo — è la lettura del caso d'uso che
permetterà di scrivere un brief DB sensato. La descrizione si tiene
volutamente sopra il livello "DDL pronto".

### 5.1 Il tipo_prestazione di partenza

Una sola riga in `pratiche.tipi_prestazione` per cominciare:

| Campo | Valore proposto |
| --- | --- |
| `codice` | `VENDITA_STANDARD` |
| `categoria` | `COMMERCIALE` |
| `descrizione` | Processo commerciale standard: dalla richiesta cliente all'esecuzione (ordine o commessa diretta) |
| `pre_attivazione` | `false` |
| `post_attivazione` | `false` (vendita può avvenire pre o post attivazione BA) |

**Perché un solo template all'inizio**: principio §7 del manifesto. Il
secondo tipo (`VENDITA_RICORRENTE`, `VENDITA_PORTALE_B2B`, ...) si seeda solo
quando emerge dal dominio reale un caso diverso, non a priori.

### 5.2 I template_flussi del processo

Sequenza minimale, prerequisiti lineari (configurabili per varianti future):

| Sequenza | Codice | Direzione | Obbligatorio | Handler | Descrizione |
| --- | --- | --- | --- | --- | --- |
| 10 | `RICHIESTA_CLIENTE` | ENTRATA | true | NULL (manuale) | Registrazione richiesta iniziale: contesto cliente, esigenza. Non crea ancora preventivo |
| 20 | `PREVENTIVAZIONE` | INTERNA | true | NULL (manuale) | Creazione/editing preventivo in `vendite.preventivi` (rimane PreventivoDrawer come UI). Chiusura del flusso = preventivo EMESSO |
| 30 | `APPROVAZIONE_CLIENTE` | ENTRATA | true | NULL (manuale) | Registrazione esito (ACCETTATO/RIFIUTATO). Esito flusso → POSITIVO/NEGATIVO |
| 40 | `CONFERMA_VENDITA` | INTERNA | true | `vendita.push_preventivo` | Bivio configurabile: crea ordine o pusha direttamente in commessa. Vedi §5.3 |

**Note**:

- Il flusso 10 (`RICHIESTA_CLIENTE`) è il punto in cui la pratica registra il
  contesto **prima** che il preventivo esista. Risponde alla richiesta di Tid
  "tutto deve poter avvenire nella pratica": l'inizio del processo è
  registrato nella pratica, non come preventivo BOZZA orfano.
- Il flusso 20 chiude solo quando il preventivo passa a EMESSO. Lo stato del
  preventivo non viene duplicato in pratica: la pratica registra "preventivo
  emesso = ✓" come esito del flusso, il preventivo resta sorgente di verità per
  i propri dati.
- Il flusso 40 è l'unico con handler. Tutto il resto è manuale (in v2 della
  dashboard, gli operatori avanzano i flussi cliccando "Completa").

### 5.3 Conversione preventivo→ordine come azione configurabile

Il bivio del flusso 40 si risolve con la combinazione descritta in §4.5. Il
risultato lato dominio:

- **Ramo "ordine"**: l'handler chiama una funzione DB (da scrivere)
  `vendite.fn_push_preventivo_a_ordine(p_preventivo_id, p_pratica_id,
  p_fatturazione_trigger)`. La funzione:
  - crea una nuova `vendite.ordini` con `sorgente_tipo_id` = PREVENTIVO e
    `sorgente_uid` = `preventivi.uid`;
  - copia righe e componenti BoM dal preventivo all'ordine, mantenendo lo
    snapshot prezzi (modello già usato dai contratti);
  - registra il legame anche in `pratiche_sorgenti` (la pratica ora ha 2
    sorgenti: preventivo ROOT, ordine COLLEGATO);
  - transiziona il preventivo a EVASO con `meta = {"via": "ORDINE",
    "ordine_id": ...}` (estensione del campo `meta` già presente per la
    transizione automatica del 2026-05-10).

- **Ramo "commessa diretta"**: l'handler chiama `push_a_commessa` esistente
  (preventivo→EVASO→commessa). Comportamento odierno, preservato.

Nessuno dei due rami è "speciale": entrambi sono casi normali. L'handler
sceglie in base a `handler_params + meta`.

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
operativo.

### 5.5 Cosa il giornale registrerà end-to-end (per una pratica VENDITA)

| Tempo | Evento giornale | Note |
| --- | --- | --- |
| t0 | `PRATICA_CREATA` (`VENDITA_STANDARD`) | Operatore avvia |
| t0+ε | `FLUSSO_CREATO` x4 | Tutti i flussi 10-40 instanziati alla creazione |
| t1 | `FLUSSO_STATO_CAMBIATO` su RICHIESTA_CLIENTE → COMPLETATO | Esito POSITIVO |
| t2 | `DOMINIO_PREVENTIVO_CREATO` (in `meta`: `preventivo_id`, `numero PRV-...`) | Handler manuale o trigger derivato |
| t3 | `FLUSSO_STATO_CAMBIATO` su PREVENTIVAZIONE → COMPLETATO | Esito POSITIVO (preventivo EMESSO) |
| t4 | `DOMINIO_PREVENTIVO_ACCETTATO` | Registrato dall'operatore via flusso 30 |
| t5 | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → IN_CORSO | Handler dispatch |
| t6 | `DOMINIO_ORDINE_CREATO` (in `meta`: `ordine_id`, `anno_serie_numero`) | Effetto handler ramo "ordine" |
| t7 | `FLUSSO_STATO_CAMBIATO` su CONFERMA_VENDITA → COMPLETATO | Esito POSITIVO |
| t8 | `STATO_CAMBIATO` su pratica → CHIUSA | Trigger su tutti i flussi obbligatori completati |

Un secondo processo (assistenza, ticketing, CRM) seguirà lo stesso pattern,
con eventi `DOMINIO_*` propri.

### 5.6 Cosa NON cambia con questa integrazione

Per evitare ambiguità, lascio esplicito cosa **non** si tocca alla prima
integrazione:

- I cicli di vita `vendite.preventivi` e `vendite.ordini` restano invariati.
- Il PreventivoDrawer esistente resta. Cambia solo che, quando si entra nel
  drawer dal flusso PREVENTIVAZIONE di una pratica, la pratica viene
  agganciata come sorgente automaticamente.
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

Eventuali propagazioni esplicite (es. dialog "annullando la pratica vuoi
annullare anche il preventivo?") sono **passi UX** del frontend, non trigger
DB. Si valutano caso per caso quando emergono. Il principio: il DB protegge
l'integrità, l'operatore decide la propagazione di processo.

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

- `vendita.push_preventivo` — push verso ordine o commessa
- `vendita.invio_documento` — invio PDF preventivo/ordine al cliente
- `assistenza.notifica_tecnico` — dispatch notifica
- `pratiche.notifica_responsabile` — handler trasversale (interno al motore)

### 6.5 Naming `ext_<dominio>` (quando emergerà)

Convenzione: `pratiche.ext_<concetto>`. Esempio: `ext_appuntamento`,
`ext_sopralluogo`. Mai `ext_<entita_di_dominio>` (es. `ext_preventivo` è
sconsigliato — il preventivo è già `vendite.preventivi`, non duplicarlo).

**Criterio quantitativo di promozione da `meta JSONB` a `ext_*`** (decisione
2026-05-18):

| Dati propri della pratica nel contesto del legame | Soluzione |
| --- | --- |
| 0-1 colonne | `pratiche_sorgenti.meta` o `flussi.meta` JSONB |
| 2-3 colonne occasionali | Ancora `meta`, ma con commento esplicito sulla struttura attesa |
| 4+ colonne con vincoli a schema (UNIQUE, CHECK, FK, indici di ricerca) | Promozione a `pratiche.ext_<concetto>` (tabella nuova) |

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

- `E_VENDITA_ORDINE_GIA_GENERATO` (push preventivo che ha già un ordine)
- `E_PRATICHE_SORGENTE_INCOMPATIBILE` (tentativo di link sorgente non
  ammessa per quel tipo_prestazione)

I codici si registrano in `config.messaggi_errore.csv` come da convenzione
esistente. Errori del motore pratiche stanno con prefisso `E_PRATICHE_*` o
`E_FLUSSI_*`, errori del dominio chiamante con prefisso del dominio.

### 6.8 Convenzione `meta` JSONB cross-record

Quando lo stesso concetto compare in `meta` JSONB di tabelle diverse, usare
la stessa chiave:

| Concetto | Chiave |
| --- | --- |
| ID preventivo | `preventivo_id` |
| UID preventivo | `preventivo_uid` |
| ID ordine | `ordine_id` |
| UID ordine | `ordine_uid` |
| ID commessa | `commessa_id` |
| ID fattura | `fattura_id` |
| Numero documento testuale | `documento_numero` |
| Naturalità (BENI_FISICI / SERVIZIO / RICORRENTE) | `natura_vendita` |

Permette query trasversali tipo `SELECT pratica_id FROM pratiche.giornale
WHERE meta->>'ordine_id' = '...'`.

---

## 7. Decisioni prese (sintesi 2026-05-18)

Tutte le decisioni di modello sono chiuse a default conservativo, ognuna
documentata nella sezione operativa di pertinenza. Tabella riassuntiva per
navigazione veloce:

| Tema | Decisione | Rif. |
| --- | --- | --- |
| Push commessa | Sorgente più a valle: da ordine se esiste, altrimenti da preventivo. `fn_list_preventivi_da_pushare` esclude i preventivi con ordine collegato | §5.4 |
| Scope pratica | Tutto il processo avviene nella pratica (`RICHIESTA_CLIENTE` prima del preventivo + `CONFERMA_VENDITA` come bivio) | §5.2 |
| Conversione preventivo→ordine | Azione configurabile via `handler_params` del template `CONFERMA_VENDITA` | §5.3 |
| Lifecycle congiunto pratica↔preventivo | Nessuna propagazione automatica di stati. Propagazioni esplicite restano in UX, non in trigger DB | §5.7 |
| Soglia `ext_*` | `meta JSONB` per 0-3 colonne; promozione a `pratiche.ext_<concetto>` solo a 4+ colonne con vincoli a schema e secondo caso d'uso identico | §6.5 |
| Competenze flussi | Seed manuale via admin/CRUD. Derivazione automatica da ruolo non in v1, valutata al secondo consumatore | §6.6 |
| Eventi di dominio nel giornale | Helper applicativo `pratiche_service.log_evento_dominio(...)` con tipo testuale convenzionato. Promozione a whitelist `config.tipi_eventi_giornale` solo dopo 3-4 eventi reali | §3.2 |
| Aggancio pratica↔preventivo | `pratiche_sorgenti` (M:N esistente), non `ext_preventivo` | §2.4 |
| Secondo consumatore validante motore | Da scegliere tra assistenza, acquisti, CRM in base alle priorità di business. Non bloccante per Fase B | §8.6 |

Tutte le decisioni sono **revedibili** alla fase di validazione (Fase E,
§8.5) se l'uso reale mostra divergenza dai default.

---

## 8. Roadmap incrementale di validazione

Quattro fasi successive. Ogni fase chiude prima di iniziare la successiva.

### 8.1 Fase A — Chiusura decisioni di modello (questa analisi)

- ✅ Analisi pubblicata (questo documento)
- ⏳ Tid review + decisioni su §7.1, §7.4 (almeno indirizzo, non firma)
- ⏳ Eventuale aggiornamento di `gestione-pratiche-v2.md` con riferimento a
  questo documento come "Fase 8 — Integrazione cross-dominio" (rinviato a OK
  Tid)

### 8.2 Fase B — Primo brief DB operativo (vendite, MVP)

Documento separato (es. `brief-db-vendite-integrazione-pratiche.md`) che
contiene:

- seed `config.sorgenti` (verifica + eventuali aggiunte: ORDINE,
  COMMESSA, ...)
- seed `pratiche.tipi_prestazione` (`VENDITA_STANDARD`)
- seed `pratiche.template_flussi` x4 + prerequisiti + canali
- seed `pratiche.handler_flussi` (`vendita.push_preventivo`)
- DDL `vendite.fn_push_preventivo_a_ordine` (funzione PL/pgSQL nuova)
- ALTER `fn_list_preventivi_da_pushare` (escludere preventivi con ordine
  collegato)
- 3-5 codici errore in `config.messaggi_errore.csv`
- pgTAP minimo: creazione pratica VENDITA + push preventivo→ordine + legame
  in `pratiche_sorgenti` corretto

### 8.3 Fase C — BE + handler Python + integrazione PreventivoDrawer

- App Django `apps/vendite/handlers/push_preventivo_handler.py`
- Registrazione in `HANDLER_MAP`
- Service `vendite_service.crea_ordine_da_preventivo()` (wrapper della fn DB)
- API: estensione `PreventivoDrawer` per agganciare/sganciare a pratica
- Test Django + smoke test bash

### 8.4 Fase D — FE (dashboard + drawer)

- Estensione `PraticheDashboard` per il tipo VENDITA_STANDARD (probabilmente
  nessuna modifica: la dashboard è generica per tipo_prestazione)
- `FlussoDrawer` esteso: per `CONFERMA_VENDITA`, dialog con scelta "Crea
  ordine" vs "Push diretto commessa"
- Aggiunta tab "Pratiche collegate" nel PreventivoDrawer (lista pratiche da
  `pratiche_sorgenti`)
- Smoke UI

### 8.5 Fase E — Validazione e decanto

- Esecuzione end-to-end del processo: richiesta cliente → preventivo →
  ordine → commessa → fattura, tutto sotto una pratica
- Estrazione del *vocabolario* che è effettivamente servito (cosa va
  promosso al nucleo pratiche, cosa resta dominio vendite)
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
- `vendite.preventivi`, `vendite.ordini` (+ righe + componenti),
  `vendite.commesse_sorgenti`,
  `vendite.fn_list_preventivi_da_pushare`, `vendite.fn_list_ordini_da_pushare`

### 9.3 Backend chiave

- `apps/pratiche/services/handler_registry.py` (`HANDLER_MAP` da
  popolare al primo handler reale)
- `apps/pratiche/services/pratiche_service.py` (facade cross-dominio)
- `apps/vendite/services/preventivi_service.py` (push_a_commessa già esistente)

---

## 10. Stato del documento

| Sezione | Stato | Prossima azione |
| --- | --- | --- |
| §1 Inquadramento | Stabile | — |
| §2 Tre pattern | Stabile (pattern A e B operativi, C in attesa di caso reale) | — |
| §3 Giornale backbone | Chiusa a default (helper applicativo) | Validazione Fase E |
| §4 Configurabilità | Stabile | — |
| §5 Caso vendite | Decisioni 2026-05-18 chiuse a default | Fase B brief DB |
| §6 Convenzioni | Decisioni 2026-05-18 chiuse a default | Si consolida dopo §8.5 |
| §7 Decisioni prese | Sintesi 2026-05-18 | Revisione a Fase E |
| §8 Roadmap | Approvata | Avvio Fase B su OK Tid |

---

*Analisi integrazione domini Anello 3 con motore pratiche — ZeroErp
(2026-05-18). Documento vivo, da aggiornare ad ogni Fase chiusa.*
