# Brief DB — Commessa multi-sorgente: aggregazione `ROOT` + `COLLEGATO`

> **Tipo**: brief operativo **per il team commesse** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL/SQL** (lo scrive il team DB).
>
> **Stato**: 🟢 **CHIUSO (2026-06-09)** — DB opzione B consegnato+pushato (commit
> `806fe749c`, migrations `20260609-10` schema + `20260609-11`
> `fn_link_commessa_sorgente`) **+ fix BE §4.2 fatto** (idempotenza transizione
> PRONTA nell'handler, NON ancora committato). Vedi §7 (log).
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

> ✅ **CONSEGNATO 2026-06-09** (commit `806fe749c`, migrations `20260609-10/11`).
> §2.1 (CHECK `{ROOT, COLLEGATO}`), §2.2 (UNIQUE ROOT parziale) e §2.4 (fn_link
> auto-ruolo) implementati come da brief. **§2.3 adottato nella forma rigida**:
> unicità `(sorgente_tipo_id, sorgente_uid)` senza `ruolo_link` → una sorgente sta
> in **una sola** commessa; il tentativo di agganciarla a un'altra solleva il
> **nuovo** errore `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` (non più
> `E_COMMESSA_ROOT_CONFLITTO`, che resta solo per la 2ª-ROOT esplicita).

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

## 4. Lato BE (1 fix DA FARE — la consegna B la rende ora raggiungibile)

Il *delega-e-basta* è confermato **invariato**: i percorsi che spingono in
commessa delegano a `fn_link_commessa_sorgente` (ora auto-ruolo) → l'aggancio di
una 2ª sorgente non fallisce più (diventa `COLLEGATO`). Nessun guard applicativo
assume «1 sorgente = 1 commessa».

### 4.1 Chi sblocca la fix B
Sull'aggancio sorgente: **tutti** i percorsi push-commessa
(`ordini_service.push_a_commessa`, `preventivi_service.push_a_commessa`,
orchestratore `CONFERMA_VENDITA`) — la collisione dimensionale ora produce un
`COLLEGATO` invece di `E_COMMESSA_ROOT_CONFLITTO`. ✅ Nessuna modifica BE per
questo.

### 4.2 Fix BE — `cambia_stato_commessa(PRONTA)` idempotente (1 SOLO call-site) — ✅ FATTO

> ✅ **Implementato 2026-06-09** (NON committato). Handler `CONFERMA_VENDITA`,
> ramo servizi: `approva_commessa_attivita` resta incondizionato (idempotente);
> la transizione a `PRONTA_FATTURAZIONE` parte **solo se** `get_commessa_stato_codice`
> ≠ `PRONTA_FATTURAZIONE` (nuovo getter repo). **Scelta di merito**: gli stati
> "oltre" anomali (`CHIUSA`/`ANNULLATA`) **non** sono silenziati — la transizione
> viene tentata e fallisce forte (non si evade un preventivo su commessa
> chiusa/annullata). Test: `test_commessa_gia_pronta_skip_transizione`.

**Correzione vs prima stesura**: verificato sul codice — l'unico percorso che
porta la commessa a `PRONTA_FATTURAZIONE` è l'orchestratore **`CONFERMA_VENDITA`**
([`push_preventivo_handler.py`](../../../backend/apps/vendite/handlers/push_preventivo_handler.py),
ramo servizi: `approva_commessa_attivita` + `cambia_stato_commessa(PRONTA)`). I
due `push_a_commessa` standalone (preventivi **e** ordini) **non** transitano la
commessa (pushano righe + evadono il documento sorgente). → il fix riguarda **solo
l'handler**.

**Regressione resa raggiungibile da B** (prima mascherata: la 2ª sorgente era
bloccata *prima*, sull'aggancio). Scenario: due preventivi con stesse dimensioni
(BA/utility/periodo/policy) confermati in sequenza → il 2° handler trova la
commessa **già `PRONTA_FATTURAZIONE`** (portata lì dal 1°) e
`cambia_stato_commessa(PRONTA)` fallisce su `PRONTA→PRONTA` (matrice senza
`da=a`). `fn_cambia_stato_commessa` **non** è idempotente (fa l'UPDATE, il trigger
`trgfn_commesse_guard_transizione` blocca).

**Specifica fix** (handler, ramo servizi): leggere lo stato corrente della
commessa e transitare a `PRONTA_FATTURAZIONE` **solo se non già** PRONTA/oltre
(skip idempotente); l'`approva_commessa_attivita` resta (approva le nuove righe
COLLEGATO). In alternativa, gemella a DB (`fn_cambia_stato_commessa` no-op su
stato-uguale) — da decidere col team; preferenza guard BE (blast radius minimo).

### 4.3 Verifica residua
Nessun altro guard applicativo deve assumere «1 sorgente = 1 commessa». ✅ Verificato.

## 5. pgTAP (suggeriti) — ✅ coperti dalla consegna
- ROOT presente + **seconda sorgente diversa** → INSERT `COLLEGATO`, **niente**
  `E_COMMESSA_ROOT_CONFLITTO`.
- **N COLLEGATO** sulla stessa commessa ammessi (≥2).
- Re-push della stessa sorgente (ROOT o COLLEGATO) → idempotente (no duplicati).
- Tentata **seconda ROOT** esplicita → ancora bloccata.
- Attività delle due sorgenti **entrambe presenti** nella commessa (segment_key
  distinti).
- §2.3 adottato: stessa sorgente su due commesse → `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`.

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

## 7. Log implementazione

| Quando | Cosa |
| --- | --- |
| 2026-06-09 (DB) | **Consegnato** (`806fe749c`). `20260609-10`: `chk_commesse_sorgenti_ruolo` → `{ROOT, COLLEGATO}`, UNIQUE ROOT **parziale**, UNIQUE sorgente `(sorgente_tipo_id, sorgente_uid)` senza ruolo (§2.3). `20260609-11`: `fn_link_commessa_sorgente` **auto-ruolo** (lock commessa, idempotente, `COLLEGATO` se ROOT già presente) + nuovo errore `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`. pgTAP §5 coperti. |
| 2026-06-09 (BE) | ✅ **FATTO** §4.2 (NON committato): skip idempotente di `cambia_stato_commessa(PRONTA)` nell'handler `CONFERMA_VENDITA` quando la commessa è già `PRONTA_FATTURAZIONE` (nuovo `CommesseRepository.get_commessa_stato_codice`). `CHIUSA`/`ANNULLATA` falliscono forte (deliberato). Test `test_commessa_gia_pronta_skip_transizione`. Brief ora **chiuso**. |

---

*Brief DB — commessa multi-sorgente (ROOT + COLLEGATO). Specchio di
`pratiche_sorgenti`. **DB consegnato 2026-06-09** (`806fe749c`); resta il fix BE
§4.2 (idempotenza transizione PRONTA nell'handler).*
