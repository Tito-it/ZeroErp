# Modello dominio Contratti

> Doc di riferimento del modello unificato `vendite.contratti` post refactor
> 2026-05-15 (drop modalita' A/B/C). Documento "vivo" — descrive lo stato
> attuale del modello, non lo storico delle decisioni.
>
> Per il razionale del refactor e le decisioni di modello vedi
> [`refactor-contratti-modalita.md`](/dev/work-done/refactor-contratti-modalita).
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

- in **DRAFT**: `c.listino_versione_id` e' `NULL`. Righe, pricing e
  capability leggono la versione **in vigore oggi**
  (`vendite.fn_documento_listino_operativo`, una sede per le tre). Cambi del
  listino durante DRAFT si propagano (utile per costruzione: il banner FE
  segnala il drift).
- alla **transizione DRAFT → ATTIVO**: il trigger
  `trgfn_contratti_freeze_listino_versione` fissa quella versione, dopo
  averla verificata con `script.fn_check_listino_congelabile` (la stessa
  check che spegne «Attiva»). Una eventuale BOZZA con date sovrapposte viene
  ignorata — non e' mai snapshot (fix Bug A 2026-05-16). Da quel momento la
  versione e' **immutabile** (lock di testata
  `trgfn_doc_testata_lock_fuori_bozza`, dal 2026-10-10: assorbe il vecchio
  `trgfn_contratti_lock_post_attivazione`).
- in **ATTIVO**: il pricing legge la versione fissata. Cambi futuri del
  listino non toccano il contratto.

⛔ **Un contratto con listino senza una versione in vigore oggi non si
attiva** (decisione A-D2 di Tid, 2026-10-07,
brief-db-offerta-emissione-ed-erogazione): `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`.
Fino a quel giorno si attivava con `listino_versione_id` NULL e poi seguiva la
versione in vigore di ogni giorno, cioe' cambiava prezzi in silenzio: l'opposto
di «congela all'attivazione». Resta il caso del DRAFT, in cui la preview e'
vuota e il drawer delle righe lo dice con un avviso.

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
- `script.trgfn_righe_guard_articolo_ammesso` (BEFORE INSERT/UPDATE OF `articolo_id`, lo stesso
  su contratto e offerta; dal Lotto 3b di brief-db-articoli-ammessi-per-documento, 2026-10-13):
  rifiuta l'articolo col primo motivo di `script.fn_check_articolo_riga`, la stessa check del
  picker. Fra i motivi: AGGIUNTA di un articolo gia' nel listino (`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`,
  si usa OVERRIDE), OVERRIDE o ESCLUSIONE senza listino o fuori listino, ESCLUSIONE di un figlio di
  bundle. Ha ritirato `trgfn_righe_guard_aggiunta_fuori_listino` e
  `trgfn_righe_guard_esclusione_figlio_bundle`.

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
[`analisi-offerta-commerciale.md`](/dev/work-done/analisi-offerta-commerciale)
discute la simmetria mancante (predecessore "offerta commerciale" non ancora
modellato).

## 7. Profilo A — congelamento post-attivazione

Il contratto ATTIVO e' **blindato** per garantire stabilita' contrattuale.
⭐ Dal 2026-10-10 la regola ha **una sede sola**, il lock di testata del DB
(`vendite.trgfn_doc_testata_lock_fuori_bozza`, montato colonna per colonna e per
stato: [brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)).
Il backend non ha piu' la sua tabella per stato (`_CONTRATTO_PATCH_ALLOWED_BY_STATE`,
ritirata): passa la scrittura e il 409 del lock arriva com'e'. Il form spegne i
campi prima, leggendo `can_edit_testata` e `non_editable_fields` dalla capability,
che leggono lo stesso montaggio.

| Campo | In ATTIVO | Codice del rifiuto |
| --- | --- | --- |
| `data`, `valuta_id` | ❌ | `E_DOC_IDENTITA_FUORI_BOZZA` |
| `listino_id`, `listino_versione_id`, `tipo_variazione_globale`, `valore_variazione_globale`, `categoria_cliente_id_snapshot`, `ambito`, `valido_dal`, `parent_contratto_id` | ❌ | `E_DOC_CONDIZIONI_FUORI_BOZZA` |
| `billing_account_id`, `istanza_utility_id`, `utility_id` | ❌ | `E_DOC_CLIENTE_FUORI_BOZZA` |
| `offerta_id`, `sorgente_tipo_id`, `sorgente_uid` | ❌ | `E_DOC_SORGENTE_FUORI_BOZZA` |
| Eccezioni in `contratti_righe` (INSERT/UPDATE/DELETE) | ❌ | `E_RIGA_DOC_NON_BOZZA` (building block `trgfn_doc_righe_lock_fuori_bozza`) |
| `valido_al` | ✅ (cessazione programmata) | — |
| `codice_cig`, `codice_cup`, `codice_commessa` | ✅ (riferimenti dell'atto) | — |
| `meta` | ✅ (note interne) | — |

In **CESSATO** e **ANNULLATO** il documento e' chiuso: si fermano anche le
colonne aperte in ATTIVO (`E_DOC_CHIUSO`). `fatturazione_immediata` non e'
nominata dal lock: la governa il suo guard di commessa.
`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` e' **ritirato** (2026-10-10). Per
cambi sostanziali serve un nuovo contratto.

### 7.1 Invariante no-overlap (esclusivita' all'attivazione)

Un solo contratto **partecipante** per `(billing_account, istanza_utility,
utility, ambito)` puo' insistere su un periodo di `validita` sovrapposto.
"Partecipante" = colonna generata `partecipa_overlap_snapshot = NOT abortito
AND NOT draft` (refactor overlap 2026-06-02, migration `20260602-17..22`):

- i contratti **DRAFT** e quelli **abortiti** NON partecipano → due bozze
  sovrapposte sono ammesse, e una bozza puo' essere preparata sovrapposta a un
  contratto attivo (flusso di **successione**);
- l'esclusivita' scatta **solo all'attivazione** (`POST .../emetti/`): per
  attivare il nuovo contratto della successione va prima chiusa la `valido_al`
  dell'incumbent, nella stessa transazione (close-before-activate).

Difesa a due livelli: il backstop duro e' l'EXCLUDE gist parziale
`ex_contratti_no_overlap` (`WHERE partecipa_overlap_snapshot`); davanti, il DB
(`script.fn_check_contratto_sovrapposto`) spegne «Attiva» nella capability col
motivo che **nomina** il contratto in conflitto, e il guard della transizione
rifiuta con `E_CONTRATTO_OVERLAP_ESISTENTE` (409). L'EXCLUDE, sulla corsa,
risponde con lo stesso codice (senza il numero, che il vincolo non da'). `ambito` resta nella chiave: forniture di
ambiti diversi (es. COMMERCIO vs COMMODITY) sullo stesso punto coesistono
legittimamente.

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

## 8-bis. Come si eroga una riga: dall'articolo (2026-10-07)

Ogni riga che si fattura (OVERRIDE, AGGIUNTA) dice **come si eroga**
(`tipo_erogazione`: CANONE, UNA_TANTUM, CONSUMO; ORARIO modellato e non ancora
ammesso) e **da dove arriva la quantita'** (`fonte_quantita_attesa`). Dal
2026-10-07 (brief-db-offerta-emissione-ed-erogazione, decisioni di Tid B-D1…B-D6)
non lo sceglie l'operatore da zero: **lo dice l'articolo**.

- **La tipologia di listino dell'articolo** dichiara le combinazioni ammesse e
  quella di default (`config.listini_tipologie_erogazioni`): per esempio
  QUOTA_FISSA solo CANONE/FISSA, CONSUMO a letture o manuale, PRODOTTI una
  tantum. **Senza tipologia** (solo un'AGGIUNTA puo' averlo: un OVERRIDE sta nel
  listino, che la tipologia la pretende) decide la **natura di vendita**
  (`config.nature_vendita_erogazioni`). Vince la tipologia. Il composito ammette
  in piu' DERIVATA_COMPONENTI. Sede unica: `vendite.fn_articolo_erogazioni`.
- **La riga eredita** erogazione e fonte che non indica (solo all'INSERT);
  CANONE porta con se' la sua `generazione_canone`. La scelta dell'operatore
  vince, dentro il perimetro.
- **Il perimetro** e' la tipologia dell'articolo, e la tipologia dev'essere fra
  quelle della utility del documento: una combinazione fuori →
  `E_RIGA_EROGAZIONE_FUORI_PERIMETRO`; un articolo di una tipologia che la
  utility non prevede → `E_RIGA_TIPOLOGIA_FUORI_UTILITY`. Le righe gia' scritte
  restano come sono (B-D6).
- **Il form** propone le sole combinazioni ammesse e preseleziona il default
  (`GET …/righe/erogazioni/`). Il push offerta → contratto ricopia i valori
  della riga, quindi quelli ereditati.

- **La quantita' segue la fonte** (2026-10-08, F-1): solo FISSA e
  DERIVATA_COMPONENTI portano una quantita' sulla riga
  (`script.fn_fonte_porta_quantita`). Con una fonte a valle `quantita` la svuota
  il DB (`trgfn_qta_from_operativa`) e una `qta_operativa` valorizzata e'
  rifiutata (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`, campo `qta_operativa`).

Stesse regole sull'offerta: le due tabelle di riga hanno gli stessi trigger.

## 9. Glossario refactor 2026-05-15 (aggiornato 2026-05-18)

| Termine | Definizione |
| --- | --- |
| **Modalita' A/B/C** (deprecato) | Vecchia classificazione del contratto come scelta utente. Rimossa: ora la forma e' derivata dai dati. |
| **Forma derivata** | Stato del contratto rispetto al listino: `con_listino` o `senza_listino`. Calcolata da `c.listino_id`. |
| **Eccezione** | Riga in `contratti_righe` con `tipo_eccezione` esplicito. Sostituisce le "righe modalita' C" e gli "override modalita' B". |
| **OVERRIDE** | Eccezione che cambia il prezzo di un articolo del listino. Soggetto a L1 (permesso `prezzo_override_manuale`) + L2 (soglia % vs prezzo resolver) + L3 (richiesta approvazione, vedi sotto). |
| **ESCLUSIONE** | Eccezione che rende un articolo del listino non disponibile per il cliente. Non porta dati di fatturazione: prezzo, quantita', UdM, erogazione e fonte restano NULL (`E_RIGA_ESCLUSIONE_CON_DATI`, 2026-10-04), e non si modifica. Ammessa su articoli standalone o su padri bundle. **Vietata su figli bundle** (trigger su `script.trgfn_righe_guard_esclusione_figlio_bundle`, errore 455) — l'esclusione si applica al bundle padre, non al singolo componente. Nessun gate (no prezzo = no L1/L2/L3). |
| **AGGIUNTA** | Eccezione che aggiunge un articolo fuori-listino al contratto. L1 sempre (permesso override richiesto). L2/L3 condizionali: si applicano solo se il resolver bundle-aware trova comunque un prezzo di riferimento (matrice categoria_cliente_listino stadio 3 o promo stadio 0). Senza base, prezzo manuale puro (Alternativa B confermata 2026-05-18). |
| **Versione operativa** | Versione listino con `stato IN ('ATTIVA','CHIUSA')` e `validita @> data`. La BOZZA e' uno stato di preparazione, esclusa dai lookup operativi. |
| **Versione fissata** | `c.listino_versione_id` valorizzato post-attivazione: snapshot della versione operativa al momento dell'attivazione. Il contratto e' blindato da cambi del listino. |
| **Drift del listino** | Disallineamento fra la `listino_versione_id` fissata sul contratto e la versione ATTIVA corrente del listino. Si verifica quando il listino pubblica una nuova versione operativa dopo l'attivazione del contratto: il contratto resta sulla fissata (i prezzi non cambiano), ma l'operatore vede nel banner contesto pricing un Tag drift con la versione corrente. Informativo, non bloccante. Esposto dal payload `/contesto-pricing/` come `drift_versione_listino: bool` + `listino_versione_corrente_codice`. |
| **Gate L2 variazione globale** | Check sulla variazione globale al PATCH testata: se eccede la soglia → 403 retryable. **Solo PERCENTUALE** ammesso lato testata (decisione 2026-05-18 §3-bis-E): VALORE_FISSO globale vietato perche' opacizza la natura della variazione (sconto secco € insensibile alla magnitudine del listino). VALORE_FISSO resta ammesso per OVERRIDE su singola riga. |
| **VALORE_FISSO globale (vietato)** | Tipo variazione testata non ammesso dal 2026-05-18. Whitelist `_TIPI_VARIAZIONE_GLOBALE_AMMESSI = frozenset({"PERCENTUALE"})` in `contratti_service`; lookup FE `tipi-variazione-contratto` ritorna solo PERCENTUALE. |
| **Contesto pricing** | Endpoint readonly `/contratti/<id>/contesto-pricing/` che ritorna forma + listino + versione fissata + versione corrente (drift detection) + variazione globale + categoria cliente. Alimenta il banner header del drawer righe. Mutuato dal pattern preventivi. |
| **Permesso "variare prezzi"** | Label UX della azione di processo. Codename DB stabile: `prezzo_override_manuale` (decisione 2026-05-18: rename solo della label, codename invariato per non rompere il binding). Richiesto da L1 per qualunque OVERRIDE/AGGIUNTA su riga contratto, dalla creazione preventivi con prezzo manuale, e dalle azioni componenti BoM con override prezzo. |
| **Listino selezionabile** | Dal 2026-10-08 (F-2 di brief-db-offerta-emissione-ed-erogazione): il listino di un contratto o di un'offerta è della **stessa utility e dello stesso emittente** del documento. La regola sta in `script.fn_check_listino_documento`, letta dal guard della testata (`E_DOC_LISTINO_UTILITY_DIVERSA`, `E_DOC_LISTINO_EMITTENTE_DIVERSO`, campo `listino_id`) e dalla tendina del form (`vendite.fn_listini_selezionabili`, `GET /vendite/lookup/listini-selezionabili/`). ⛔ La versione non c'entra più: la decisione 2026-05-18 §4.4 («senza versione ATTIVA non si seleziona», guard Python `_guard_listino_ha_versione_attiva`, codice `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA`) è ritirata col D.4.3 del 2026-10-07: in DRAFT un listino senza versione in vigore si sceglie, lo rifiuta l'attivazione (`E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`). |
| **Richiesta approvazione (L3)** | Workflow di escalation Sprint E quando un OVERRIDE/AGGIUNTA viola L2: il payload riga puo' includere `richiesta_approvazione=true` e il service crea una pratica APPROVAZIONE_PREZZO + salva la riga con `stato_approvazione_prezzo='PENDING'` + FK alla pratica. Trigger DB blocca modifiche struttura sulle righe PENDING (allowlist: workflow + meta + audit). **Cablato sia su preventivi che su contratti dal 2026-05-19** (migrations DB `20260518-01/02` per simmetria contratti_righe + cablaggio BE in `ContrattiService.create_riga`/`update_riga` + endpoint `/righe-contratto/<id>/approva-prezzo/` e `/rifiuta-prezzo/`). Il service di esito (`approvazioni_prezzo_service.approva/rifiuta`) e' sorgente-agnostico con parametro `sorgente='preventivo'` o `'contratto'` che fa dispatch su tabella e repository corretti via `_SORGENTE_CONFIG`. |

## Riferimenti

- [api_contratti.md](api_contratti.md) — contratto HTTP completo
- [api_preventivi.md](api_preventivi.md) — pattern simmetrico (snapshot riga)
- [fn_resolve_prezzo_listino_v2](../../../dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver DB
- [refactor-contratti-modalita](/dev/work-done/refactor-contratti-modalita) — decisioni di modello
- [catalogo-building-block-backend](../../../dev/backend/catalogo-building-block-backend) — sezione "Vendite — Gate autorizzazioni prezzi" per il BB `_pricing_gate_helpers`
