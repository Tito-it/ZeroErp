# Brief DB — Commessa multi-sorgente: aggregazione `ROOT` + `COLLEGATO`

> **Tipo**: brief operativo **per il team commesse** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL/SQL** (lo scrive il team DB).
>
> **Stato**: 🟡 **APERTO** — decisione di modello ratificata, implementazione DB
> da avviare.
>
> **Owner concettuale**: Tid (Michele Carlo Titini). **Data brief**: 2026-06-09.
>
> **Origine (bug reale)**: l'invio a commessa di un ordine fallisce con
> `E_COMMESSA_ROOT_CONFLITTO` → `E_COMMESSA_PUSH_PARZIALE_VIETATO`. Diagnosi:
> l'ordine si risolve **dimensionalmente** (BA + utility + tipo + policy +
> competenza) sulla **stessa commessa** di un altro ordine già pushato (caso
> reale: commessa 66, ROOT = ordine 53 `ORD0000045`, BA 173 / utility 5; il nuovo
> ordine ha le stesse dimensioni). In v1 `commesse_sorgenti.ruolo_link` ammette
> **solo `ROOT`** e una commessa ha **una sola ROOT** → la seconda sorgente è
> rifiutata. **Non è dato sporco**: due ordini legittimi dello stesso
> cliente/utility/periodo collidono **sempre**.
>
> **Decisione di modello ratificata (Tid, 2026-06-09)**: **opzione B —
> aggregazione multi-sorgente**. Una commessa può contenere **N sorgenti**: una
> `ROOT` (primaria) + N `COLLEGATO` (contributori). Il resolver dimensionale
> resta com'è (è *corretto*: la commessa **è** l'unità di aggregazione del
> fatturabile per cliente/utility/periodo → più ordini convergono in una
> commessa → una fatturazione aggregata). Recupero/azione non distruttiva.
>
> **Precedente già implementato (da specchiare)**: `pratiche.pratiche_sorgenti`
> ha **già** `ruolo_link ∈ {ROOT, COLLEGATO}` e l'aggregazione ROOT + N
> COLLEGATO è in uso sul percorso pratica. Nel modello split preventivo→(ordine
> + commessa) i legami `pratiche_sorgenti` sono:
>
>   - **preventivo ROOT + ordine `COLLEGATO`** → li scrive ora la fn DB
>     [`fn_push_preventivo_a_ordine`](../../../db/changelog/migrations_v2/20_code/vendite/20260609-06-create-fn-push-preventivo-a-ordine-mctit.yaml)
>     (quando riceve `p_pratica_id`), **non più** l'handler;
>   - **commessa `COLLEGATO`** → la aggancia l'handler
>     [`push_preventivo_handler.py`](../../../backend/apps/vendite/handlers/push_preventivo_handler.py)
>     nel ramo servizi.
>
> Stesso pattern ROOT/COLLEGATO, un livello sotto (commessa): è ciò che questo
> brief porta su `commesse_sorgenti`.

---

## 1. Stato di fatto verificato (doc DB)

Da [`vendite/tabelle/commesse_sorgenti.md`](../../dbzero/vendite/tabelle/commesse_sorgenti.md):

| Vincolo | Definizione | Ruolo nel bug |
|---|---|---|
| `chk_commesse_sorgenti_ruolo` | CHECK su `ruolo_link` — **solo `ROOT`** in v1 (manual: *"in v1 ruolo_link ammesso solo ROOT"*) | impedisce di marcare la 2ª sorgente come contributore |
| `uq_commesse_sorgenti_commessa_ruolo` | UNIQUE `(commessa_id, ruolo_link)` | **vincolo chiave del blocco**: una sola riga per ruolo per commessa → con sola `ROOT` = una sola sorgente per commessa |
| `uq_commesse_sorgenti_src_uid_ruolo` | UNIQUE `(sorgente_tipo_id, sorgente_uid, ruolo_link)` | una sorgente non duplicabile nello stesso ruolo |

Confronto con il precedente che **funziona** già multi-sorgente
([`pratiche/tabelle/pratiche_sorgenti.md`](../../dbzero/pratiche/tabelle/pratiche_sorgenti.md)):

| Vincolo | `pratiche_sorgenti` |
|---|---|
| CHECK ruolo | `{ROOT, COLLEGATO}` |
| UNIQUE idempotenza | `(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` |
| UNIQUE "una riga per ruolo" | **NON esiste** → molti `COLLEGATO` ammessi |

→ La differenza che blocca le commesse è esattamente `uq_commesse_sorgenti_commessa_ruolo`.

Comportamento attuale di `vendite.fn_link_commessa_sorgente(p_commessa_id, …)`:
cerca la `ROOT` della commessa; se assente → INSERT `ROOT`; se presente con
**stessa** chiave → idempotente (merge `meta`); se presente con **chiave
diversa** → solleva `E_COMMESSA_ROOT_CONFLITTO`. **È quest'ultimo ramo il
problema.**

## 2. Cosa serve a DB (logica, opzione B)

### 2.1 CHECK ruolo → `{ROOT, COLLEGATO}`
Estendere `chk_commesse_sorgenti_ruolo` per ammettere anche `COLLEGATO`
(specchio di `chk_pratiche_sorgenti_ruolo`).

### 2.2 «Una sola ROOT per commessa» → vincolo **parziale**
`uq_commesse_sorgenti_commessa_ruolo (commessa_id, ruolo_link)` deve diventare
**parziale**: unicità su `commessa_id` **solo** per `ruolo_link = 'ROOT'`. Così
resta **una sola ROOT** per commessa, ma si ammettono **N `COLLEGATO`**. (Stesso
idioma del vincolo parziale già usato per offerta→ordine
`uq_ordini_v_documento_origine_offerta`.)

### 2.3 «Una sorgente sta in una sola commessa» (da decidere)
`uq_commesse_sorgenti_src_uid_ruolo (sorgente_tipo_id, sorgente_uid,
ruolo_link)`: con due ruoli, la stessa sorgente potrebbe essere `ROOT` di una
commessa **e** `COLLEGATO` di un'altra — incoerente (un ordine deve stare in
**una** commessa). Valutare di rendere l'unicità `(sorgente_tipo_id,
sorgente_uid)` **senza** `ruolo_link` → una sorgente = un solo link, un solo
ruolo. (Decisione del team: scegliere se questa rigidità è desiderata o se
basta l'enforcement applicativo.)

### 2.4 `fn_link_commessa_sorgente` — nuova logica
Sostituire il ramo che oggi solleva `E_COMMESSA_ROOT_CONFLITTO` quando esiste già
una ROOT con chiave diversa. Comportamento target (la fn **decide il ruolo**, il
chiamante non cambia):

1. **Lookup per sorgente** sulla commessa: cerca una riga `(commessa_id,
   sorgente_tipo_id, sorgente_uid)` qualunque sia il ruolo.
   - **Esiste** → idempotente (merge `meta`), ritorna il link. *(copre il
     re-push della stessa sorgente, ROOT o COLLEGATO che sia)*
2. **Non esiste** → assegna il ruolo:
   - se la commessa **non ha ancora una ROOT** → INSERT come **`ROOT`**;
   - se la commessa **ha già una ROOT** (di altra sorgente) → INSERT come
     **`COLLEGATO`** (idempotente sul vincolo sorgente).
3. `E_COMMESSA_ROOT_CONFLITTO` resta **solo** per i casi davvero incoerenti
   (es. tentativo esplicito di una seconda `ROOT`), non più per «altra sorgente
   sulla stessa commessa», che è ora il flusso **normale**.

> Nota: in alternativa il ruolo lo passa il chiamante (handler) — ma far decidere
> la fn mantiene `BaseSourceHandler`/orchestratore **invariati** (blast radius
> minimo, come la scelta c7-2 del brief pratica-preventivi).

## 3. Cosa NON cambia
- **Resolver dimensionale** `fn_get_or_create_commessa`: resta com'è. Far
  convergere più ordini su una commessa è **voluto** (è l'aggregazione del
  fatturabile), non un bug.
- **Idempotenza righe**: `commesse_attivita` UPSERT su `(commessa_id,
  segment_key)`. Il `segment_key` include il `sorgente_uid` → ordini diversi =
  attività distinte che **coesistono** nella stessa commessa (nessuna
  sovrascrittura).
- **EVASO ordine** (cablato 2026-06-08): il secondo ordine ora **passa** (push
  COMPLETATO come COLLEGATO) → transita anch'esso a `EVASO`. Coerente.

## 4. Lato BE (verifica + 1 fix da fare A CONSEGNA, competenza agente BE)

Atteso **nessun cambio strutturale** sul *delega-e-basta*: gli orchestratori
delegano a `fn_link_commessa_sorgente` (che ora auto-assegna il ruolo) e l'esito
non è più `E_COMMESSA_ROOT_CONFLITTO` → il push non fallisce più `PARZIALE`. Il
pattern `COLLEGATO` è già in uso (`pratiche_sorgenti`).

### 4.1 Chi è soggetto a questo bug (oggi)
Tutti i percorsi che spingono in commessa passano da `fn_link_commessa_sorgente`,
quindi **tutti** oggi sono soggetti a `E_COMMESSA_ROOT_CONFLITTO` su collisione
dimensionale, **non solo l'ordine**:

- `vendite.ordini_service.push_a_commessa` (ordine→commessa) — il caso del bug
  originale;
- `vendite.preventivi_service.push_a_commessa` (preventivo→commessa, servizi);
- l'orchestratore **`CONFERMA_VENDITA`** (`push_preventivo_handler`, ramo
  servizi) — anche due preventivi stesso BA/utility/periodo collidono.

→ La fix B sblocca **tutti** questi, non serve toccarli per il *delega*.

### 4.2 Fix BE da fare INSIEME alla consegna B — `cambia_stato_commessa(PRONTA)` idempotente
**Regressione resa raggiungibile dalla multi-sorgente** (oggi mascherata: la 2ª
sorgente viene bloccata *prima* da `E_COMMESSA_ROOT_CONFLITTO`). Con B, una
sorgente può agganciarsi a una commessa **già `PRONTA_FATTURAZIONE`** (portata lì
da una sorgente precedente). I percorsi che dopo il push fanno, incondizionato:

```
approva_commessa_attivita(...) ; cambia_stato_commessa(PRONTA_FATTURAZIONE)
```

falliscono sulla transizione `PRONTA→PRONTA` (matrice senza `PRONTA→PRONTA`,
CHECK `da≠a`) — stesso tipo di problema di §8.2 del brief pratica-preventivi.

**Specifica**: rendere la transizione a `PRONTA_FATTURAZIONE` **idempotente**
(skip se la commessa è già `PRONTA_FATTURAZIONE`/oltre) nei punti che la invocano:

- `apps/vendite/handlers/push_preventivo_handler.py` (ramo servizi);
- `apps/vendite/services/preventivi_service.py::push_a_commessa`;
- `apps/vendite/services/ordini_service.py::push_a_commessa`.

Equivalente lato DB: `fn_cambia_stato_commessa` no-op (o ammessa) su
`PRONTA→PRONTA` — da decidere col team se la guardia vive a DB o BE (preferenza:
guard applicativo a monte, BE, blast radius minimo). **Non urgente prima della
consegna B**: oggi il caso non è raggiungibile (il conflitto ROOT lo previene).

### 4.3 Verifica residua
Nessun altro guard applicativo deve assumere «1 sorgente = 1 commessa».

## 5. pgTAP (suggeriti)
- ROOT presente + **seconda sorgente diversa** → INSERT `COLLEGATO`, **niente**
  `E_COMMESSA_ROOT_CONFLITTO`.
- **N COLLEGATO** sulla stessa commessa ammessi (≥2).
- Re-push della stessa sorgente (ROOT o COLLEGATO) → idempotente (no duplicati).
- Tentata **seconda ROOT** esplicita → ancora bloccata.
- Attività delle due sorgenti **entrambe presenti** nella commessa (segment_key
  distinti).
- (Se adottato §2.3) stessa sorgente su due commesse → bloccata.

## 6. Note / fuori scope
- **Fatturazione**: B abilita l'aggregazione *N ordini → 1 commessa → 1
  fatturazione*. La **cardinalità esatta della fattura** (una per commessa per
  periodo di competenza) è decisa dalla pipeline **lotto→fattura** a valle:
  **invariata**, fuori scope di questo brief. Se serve certezza sul
  raggruppamento per competenza, va verificata a parte.
- **Dato corrente**: con B, l'ordine che oggi fallisce su commessa 66 si
  aggancerebbe come `COLLEGATO` senza pulizia manuale.
- Questo brief è **solo `commesse_sorgenti`** + `fn_link_commessa_sorgente`. Non
  tocca il resolver, né il modello pratiche (già a posto), né la pipeline fattura.

---

*Brief DB — commessa multi-sorgente (ROOT + COLLEGATO). Specchio di
`pratiche_sorgenti`. Pronto per il team commesse su `dev/db-tid`. A consegna,
l'agente BE verifica il cablaggio (atteso no-op) e rieseguibilità push.*
