# Modello dominio Contratti

> Doc di riferimento del modello unificato `vendite.contratti` post refactor
> 2026-05-15 (drop modalita' A/B/C). Documento "vivo" — descrive lo stato
> attuale del modello, non lo storico delle decisioni.
>
> Per il razionale del refactor e le decisioni di modello vedi
> [`refactor-contratti-modalita.md`](/dev/work-in-progress/refactor-contratti-modalita).
> Per il contratto HTTP delle API vedi [`api_contratti.md`](api_contratti.md).

## 1. Cos'e' un contratto

Un contratto e' un accordo cliente-fornitore che fissa **come si prezza** un
articolo per un cliente specifico, su una specifica utility, per un periodo
di validita'. E' il ponte tra:

- il **cliente** (`billing_account` + `istanza_utility`), che identifica
  *chi paga* e *quale punto di erogazione*;
- il **listino di riferimento** (`listino_id` + `listino_versione_id`,
  opzionale), che identifica *da dove arrivano i prezzi base*;
- la **variazione globale** (opzionale), che modifica uniformemente tutti
  i prezzi del listino;
- le **eccezioni** (`contratti_righe`), che derogano puntualmente al listino
  per articoli specifici.

Il contratto **non** materializza le righe del listino. Resta un "delta" del
listino: solo le eccezioni vivono nella sua tabella righe. Il resto e' letto
dinamicamente dal listino (in DRAFT: versione corrente; in ATTIVO: versione
fissata, vedi §3).

## 2. Forma derivata: "con_listino" / "senza_listino"

Le vecchie modalita' A/B/C sono state rimosse come scelta utente. La forma
del contratto e' derivata dai dati di testata:

| Forma | `listino_id` | Significato |
| --- | --- | --- |
| **`con_listino`** | NOT NULL | C'e' un listino di riferimento. Variazione globale opzionale. Eccezioni puntuali (OVERRIDE/ESCLUSIONE/AGGIUNTA) opzionali. |
| **`senza_listino`** | NULL | Contratto interamente negoziato (ex-modalita' C). Tutte le righe sono AGGIUNTA con prezzo NOT NULL. |

In forma "con_listino" sono ammesse tutte le combinazioni:

- listino + nessuna variazione + nessuna eccezione → prezzi listino tal quali
- listino + variazione globale + nessuna eccezione → ex-modalita' A
- listino + nessuna variazione + eccezioni mirate → ex-modalita' B
- listino + variazione globale + eccezioni mirate → ex "A con override singoli"
  (era zona grigia nel vecchio modello, ora pienamente ammesso)

L'unico vincolo strutturale e' la **coppia variazione coerente**:
`tipo_variazione_globale` e `valore_variazione_globale` devono essere
entrambi NULL o entrambi NOT NULL. Validato in
`_validate_variazione_globale_coppia_coerente` (service) + check DB
(`chk_contratti_tipo_variazione_globale`).

## 3. Snapshot della versione listino all'attivazione

Il listino e' versionato (`listini_versioni.validita`): nel tempo escono
versioni nuove. Il contratto deve essere blindato dai cambi di listino
post-attivazione (Profilo A). La soluzione:

- in **DRAFT**: `c.listino_versione_id` e' `NULL`. Il pricing legge la
  versione corrente del listino alla data. Cambi del listino durante DRAFT
  si propagano (utile per costruzione: il banner FE segnala il drift).
- alla **transizione DRAFT → ATTIVO**: il trigger
  `trgfn_contratti_freeze_listino_versione` fissa
  `c.listino_versione_id = lv.id` della versione **operativa** (stato
  `IN ('ATTIVA','CHIUSA')`) alla data del contratto. Una eventuale BOZZA
  con date sovrapposte viene ignorata — non e' mai snapshot (fix Bug A
  2026-05-16). Da quel momento la versione e' **immutabile** (lock dal
  trigger `trgfn_contratti_lock_post_attivazione`).
- in **ATTIVO**: il pricing legge la versione fissata. Cambi futuri del
  listino non toccano il contratto.

Caso limite: contratto attivato con listino senza versione attiva alla data
(`lv.validita @> data` non matcha). `c.listino_versione_id` resta NULL, la
preview ritorna vuota, il FE mostra un warning. Quando una versione viene
attivata in futuro, il pricing inizia a usarla. Edge case raro ma ammesso
dal modello.

## 4. Eccezioni: i 3 tipi

Le righe in `contratti_righe` sono **eccezioni tipizzate** del listino di
riferimento, non "il contenuto del contratto". Il campo `tipo_eccezione`
(enum/varchar + CHECK DB) e' NOT NULL.

| `tipo_eccezione` | Significato | `prezzo_unitario` | Valido in forma |
| --- | --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per un articolo presente nel listino. La variazione globale **non si applica** (l'override e' prezzo finale). | NOT NULL | `con_listino` |
| `ESCLUSIONE` | L'articolo del listino non e' disponibile per questo cliente. Il resolver pricing solleva `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` se viene richiesto. | NULL | `con_listino` |
| `AGGIUNTA` | Articolo non presente nel listino, aggiunto al contratto. Prezzo esplicito. | NOT NULL | `con_listino` e `senza_listino` |

Vincoli DB:

- `chk_contrighe_prezzo_per_tipo_eccezione`: coerenza prezzo/tipo (vedi
  tabella).
- `uq_contrighe_one_eccezione_per_articolo` (UNIQUE parziale): max 1
  eccezione OVERRIDE/ESCLUSIONE per coppia `(contratto_id, articolo_id)`.
- `uq_contrighe_one_aggiunta_per_articolo` (UNIQUE parziale): max 1
  AGGIUNTA per coppia `(contratto_id, articolo_id)`.
- `trgfn_contratti_righe_guard_aggiunta_fuori_listino` (BEFORE INSERT/UPDATE):
  blocca AGGIUNTA per articolo gia' presente nel listino di riferimento del
  contratto. L'operatore avrebbe dovuto usare OVERRIDE.

`tipo_eccezione` e' **immutabile in UPDATE**. Per cambiare tipo serve
DELETE + INSERT (evita cambi di semantica silenti). Validato in
`_FORBIDDEN_RIGA_UPDATE` (service).

## 5. Resolver pricing: come arriva il prezzo

Quando si richiede un prezzo per `(BA, utility, articolo, data)`, la fn
`vendite.fn_resolve_prezzo_listino_v2` segue questa cascata (STADIO 1 e 2):

```
STADIO 1 — c'e' un contratto attivo per (BA, utility, data)?
  ├── Si' (c.listino_id, c.listino_versione_id puo' essere NULL o NOT NULL)
  │   ├── Esiste eccezione OVERRIDE su (contratto, articolo)?
  │   │   └── Si' -> prezzo = cr.prezzo_unitario, origine='CONTRATTO_OVERRIDE'
  │   ├── Esiste eccezione ESCLUSIONE su (contratto, articolo)?
  │   │   └── Si' -> raise E_ARTICOLO_ESCLUSO_DA_CONTRATTO
  │   ├── Esiste eccezione AGGIUNTA su (contratto, articolo)?
  │   │   └── Si' -> prezzo = cr.prezzo_unitario, origine='CONTRATTO_AGGIUNTA'
  │   └── Nessuna eccezione:
  │       ├── c.listino_id NULL (forma senza_listino) -> raise (articolo non
  │       │   negoziato sul contratto)
  │       └── c.listino_id NOT NULL:
  │           ├── leggi riga listino dalla versione FISSATA
  │           │   (c.listino_versione_id) o CORRENTE (se NULL)
  │           ├── applica c.tipo_variazione_globale (se valorizzato)
  │           └── prezzo = listino * (1 + variazione_pct) o + variazione_fissa
  │
  └── No -> fallback STADIO 2 (categoria cliente) o STADIO 3 (promo overlay)
```

Il dettaglio della fn (formula variazione, gestione tipi, promo) e' in
[fn_resolve_prezzo_listino_v2.md](../../../dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2).

## 6. Differenza chiave preventivo ↔ contratto

I due artefatti modellano momenti diversi del processo commerciale:

| Aspetto | Preventivo | Contratto |
| --- | --- | --- |
| Cosa fissa | Il **prezzo della singola riga** | La **versione del listino** + le eccezioni |
| Tipo snapshot | Riga-per-riga (`preventivi_righe.prezzo_unitario` materializzato) | Versione listino (`c.listino_versione_id` fisso, righe non duplicate) |
| Scope | Una transazione puntuale | Una relazione duratura |
| Cosa diventa accettato | Commessa → fattura una-tantum | Pipeline fatturazione ricorrente |

Quando il prezzo del listino cambia dopo la creazione:

- nel **preventivo** le righe sono fisse (prezzo materializzato): non cambiano;
- nel **contratto DRAFT** la preview riflette il nuovo listino (drift visibile
  via banner FE);
- nel **contratto ATTIVO** la versione e' fissata: il pricing resta blindato.

Approfondimento dominio:
[`Analisi-iniziale-offerta-commerciale.md`](/dev/work-in-progress/Analisi-iniziale-offerta-commerciale)
discute la simmetria mancante (predecessore "offerta commerciale" non ancora
modellato).

## 7. Profilo A — congelamento post-attivazione

Il contratto ATTIVO e' **blindato** per garantire stabilita' contrattuale:

| Campo | Modificabilita' in ATTIVO |
| --- | --- |
| `listino_id` | ❌ trigger `trgfn_contratti_lock_post_attivazione` |
| `listino_versione_id` | ❌ trigger lock |
| `tipo_variazione_globale` | ❌ trigger lock |
| `valore_variazione_globale` | ❌ trigger lock |
| Eccezioni in `contratti_righe` (INSERT/UPDATE/DELETE) | ❌ trigger `trgfn_contratti_righe_lock_post_attivazione` |
| `categoria_cliente_id_snapshot` | ❌ rifiutato dal service (DRAFT-only) |
| `valido_al` | ✅ ammesso (cessazione programmata) |
| `meta` | ✅ ammesso (note interne) |

Tentativi di modifica sui campi bloccati sollevano
`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (409). Per cambi sostanziali
serve un nuovo contratto.

## 8. Cascata parametri estesa (per gate L2)

Il sistema "autorizzazioni prezzi" (L1 permesso + L2 soglia variazione + L3
escalation) usa parametri di sistema risolti con cascata multi-livello.
Refactor 2026-05-15: la cascata e' stata estesa con il livello
**categoria_cliente** del BA destinatario:

```
user → categoria_cliente → group → emittente → session → function → default
```

Esempio: parametro `VENDITE_MAX_SCONTO_PCT`:

- Default sistema: 10%
- Group SENIOR: 20%
- Categoria PREMIUM: 5%
- User Mario (junior): nessun override

Risoluzione "Mario su cliente PREMIUM" → 5% (categoria vince su group).

Il livello categoria viene alimentato dai service di dominio passando
`categoria_cliente_id` (derivato dal BA via
`BillingAccountRepository.get_categoria_cliente_id`) alla fn DB
`script.fn_get_parameter_full`. Implementato nel BB condiviso
`apps.vendite.services._pricing_gate_helpers` (vedi catalogo BB
"Vendite — Gate autorizzazioni prezzi").

## 9. Glossario refactor 2026-05-15

| Termine | Definizione |
| --- | --- |
| **Modalita' A/B/C** (deprecato) | Vecchia classificazione del contratto come scelta utente. Rimossa: ora la forma e' derivata dai dati. |
| **Forma derivata** | Stato del contratto rispetto al listino: `con_listino` o `senza_listino`. Calcolata da `c.listino_id`. |
| **Eccezione** | Riga in `contratti_righe` con `tipo_eccezione` esplicito. Sostituisce le "righe modalita' C" e gli "override modalita' B". |
| **OVERRIDE** | Eccezione che cambia il prezzo di un articolo del listino. |
| **ESCLUSIONE** | Eccezione che rende un articolo del listino non disponibile per il cliente. Ammessa su articoli standalone o su padri bundle. **Vietata su figli bundle** (trigger `trgfn_contratti_righe_guard_esclusione_figlio_bundle`, errore 455) — l'esclusione si applica al bundle padre, non al singolo componente. |
| **AGGIUNTA** | Eccezione che aggiunge un articolo fuori-listino al contratto. |
| **Versione operativa** | Versione listino con `stato IN ('ATTIVA','CHIUSA')` e `validita @> data`. La BOZZA e' uno stato di preparazione, esclusa dai lookup operativi. |
| **Versione fissata** | `c.listino_versione_id` valorizzato post-attivazione: snapshot della versione operativa al momento dell'attivazione. Il contratto e' blindato da cambi del listino. |
| **Drift del listino** | Stato in DRAFT in cui esce una nuova versione del listino: il banner FE lo segnala all'operatore. |
| **Gate L2 variazione globale** | Check sulla variazione globale (PERCENTUALE) al PATCH testata: se eccede la soglia → 403 retryable. Solo PERCENTUALE; VALORE_FISSO skip. |
| **Contesto pricing** | Endpoint readonly che ritorna forma + listino + versione fissata + variazione + categoria cliente per il banner FE. Mutuato dal pattern preventivi. |

## Riferimenti

- [api_contratti.md](api_contratti.md) — contratto HTTP completo
- [api_preventivi.md](api_preventivi.md) — pattern simmetrico (snapshot riga)
- [fn_resolve_prezzo_listino_v2](../../../dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver DB
- [refactor-contratti-modalita](/dev/work-in-progress/refactor-contratti-modalita) — decisioni di modello
- [catalogo-building-block-backend](../../../dev/backend/catalogo-building-block-backend) — sezione "Vendite — Gate autorizzazioni prezzi" per il BB `_pricing_gate_helpers`
