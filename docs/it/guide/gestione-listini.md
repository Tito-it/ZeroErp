# Guida — Gestione Listini e Pricing (v5)

> **Ultima revisione**: 23 aprile 2026 — chiusura end-to-end Sprint E+F
> (workflow L3 approvazione + cleanup + doc API estesa). Il modello v5
> è feature-complete (resolver a 3 stadi: promo → contratto → categoria
> + L1+L2+L3 autorizzazioni prezzi + BoM versionata immutabile).
>
> La versione pre-v5 è archiviata in [gestione-listini-pre-v5](archive/gestione-listini-pre-v5.md)
> per riferimento storico.
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.listini](/dbzero/vendite/tabelle/listini) / [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) / [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) + [categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini)
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) + [contratti_righe](/dbzero/vendite/tabelle/contratti_righe) + [contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> * [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) (BoM versionata immutabile)
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> * [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito)
>
> **Vedi anche** — API e service backend:
>
> * [PricingService (backend)](/backend/vendite/manual/pricing_service)
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Approvazioni prezzo (workflow L3)](/backend/vendite/manual/api_approvazioni_prezzo)
> * [API Preventivi](/backend/vendite/manual/api_preventivi) (con flag `richiesta_approvazione` per L3)
> * [API Contratti](/backend/vendite/manual/api_contratti) / [API Promo articoli](/backend/vendite/manual/api_promo_articoli) / [API Matrice categorie/listini](/backend/anagrafiche/manual/api_categorie_clienti_listini)
>
> **Vedi anche** — piani sprint:
>
> * [Storico piano sprint v5 (work-done)](/dev/work-done/sviluppo-listini-v5) — tutti gli sprint chiusi end-to-end
> * [Piano test UI v5 (WIP attivo)](/dev/work-in-progress/sviluppo-listini-v5-test-ui) — 7 scenari per validazione UI

---

## 1. Cosa risponde il sistema pricing

> *"Quanto costa questo articolo, per questo cliente, in questa data, per questa utility?"*

Il sistema pricing v5 risponde deterministicamente attraverso **3 stadi** valutati in sequenza:

1. **STADIO 0 — PROMO**: esiste una promozione temporanea attiva su quella coppia (articolo, uom)? Se sì, vince.
2. **STADIO 1 — CONTRATTO**: il cliente ha un contratto individuale attivo? Se sì, il prezzo viene dal contratto (modalità A/B/C).
3. **STADIO 2 — CATEGORIA**: in assenza di contratto, il cliente ha una categoria commerciale? Se sì, la matrice categoria→listino determina il prezzo base.

Non ci sono tie-break: la struttura dati **garantisce** che ogni stadio produca al massimo una risposta.

---

## 2. Le entità in gioco

### 2.1 Listino

È un **contenitore di prezzi** identificato dalla combinazione:

- `utility_id` — il servizio (Gas, Energia, Idrico, "Base" per commercio)
- `tipologia_id` — la categoria di voce (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA, PRODOTTI, SERVIZI)
- `emittente_soggetto_ruolo_id` — chi emette la fattura (dimensione interna)

**Un solo listino** per ogni quadrupla (utility, tipologia, emittente, codice). Non esistono "listini derivati": le variazioni commerciali vivono altrove.

Un listino contiene:

- **Versioni** (`listini_versioni`) — finestre temporali con stato BOZZA → ATTIVA → CHIUSA. Solo una versione ATTIVA per listino nel periodo (vincolo `EXCLUDE`).
- **Righe** (`listini_righe`) — per ogni versione: (articolo, uom) → prezzo. Forma pura, senza dimensioni di scope.

### 2.2 Categoria cliente

Rappresenta la **politica commerciale trasversale** (STANDARD, BASE, SILVER, GOLD, PLATINUM).

Caratteristiche:

- ogni `billing_account` ha esattamente una `categoria_cliente_id` (default STANDARD)
- la categoria decide se il cliente **partecipa alle promo** (flag `partecipa_promo`)
- la categoria indirizza al listino corretto via la **matrice**

### 2.3 Matrice categoria → listino

Tabella `anagrafiche.categorie_clienti_listini`. Per ogni quadrupla:

```
(categoria_cliente, utility, emittente, classe_utenza opz.) → listino + variazione opz.
```

La variazione è opzionale (`tipo_variazione` + `valore_variazione`, coppia coerente):

- `PERCENTUALE` — firmata (negativo = sconto, positivo = maggiorazione)
- `VALORE_FISSO` — firmato
- Nessuna variazione → prezzo base del listino tal quale

`classe_utenza_id` è opzionale: la ricerca prova prima il match esatto poi il fallback a NULL (dimensione pricing per utility con gradazione, es. DOM-BTA su energia).

Vincolo `EXCLUDE`: non possono esistere due righe attive sovrapposte per la stessa quadrupla → il resolver STADIO 2 non ha ambiguità.

### 2.4 Contratto

È l'**accordo individuale** tra cliente ed emittente. Tre modalità possibili:

| Modalità | Listino | Variazione globale | Righe override | Quando usarla |
|---|---|---|---|---|
| **A** — listino + variazione | sì | sì | vuote o parziali | "Listino standard 2026 scontato 10%" |
| **B** — listino con override mirati | sì | sì o no | alcune righe con prezzo forzato | "Listino standard, ma art X a €50 fisso" |
| **C** — interamente negoziato | no | no | tutte le righe con prezzo | Grande cliente con condizioni 100% custom |

Un trigger DB blocca la transizione DRAFT → ATTIVO se la modalità C ha righe vuote (errore `E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE`).

### 2.5 Promo

Tabella `vendite.promo_articoli`. È un **overlay temporale** indipendente:

- (articolo, uom, validità) → tipo e valore variazione
- batte qualsiasi altro stadio se il cliente appartiene a una categoria con `partecipa_promo = true`
- ammette `PREZZO_FISSO` (prezzo assoluto sostitutivo) — vietato negli altri stadi

---

## 3. Resolver — i 3 stadi in dettaglio

La funzione `vendite.fn_resolve_prezzo_listino_v2` riceve:

- articolo, uom, data, billing_account
- utility, emittente (derivato dal JWT dell'operatore, 1-a-1)
- classe_utenza (opzionale, derivata da contratto o istanza)

### STADIO 0 — Promo overlay

```
Esiste riga in promo_articoli (articolo, uom, data) attiva?
  E la categoria del BA ha partecipa_promo = true?
    → SÌ: prezzo_base = STADIO 1/2, applica variazione promo → STOP
           origine = PROMO
    → NO: vai allo STADIO 1
```

### STADIO 1 — Contratto

```
Esiste contratto ATTIVO per (ba, utility, data)?
  → SÌ:
      Esiste riga override per (articolo, uom) con prezzo_unitario NOT NULL?
        → SÌ: prezzo = prezzo_unitario; origine = CONTRATTO_OVERRIDE
        → NO: se contratto ha listino_id (modalità A o B senza override):
               prezzo_base = riga listino
               applica variazione_globale se presente
               origine = CONTRATTO_LISTINO
             altrimenti (modalità C senza riga):
               ERRORE E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
  → NO: vai allo STADIO 2
```

### STADIO 2 — Categoria cliente

```
BA ha categoria_cliente_id (sempre sì: default STANDARD)?
  → SÌ:
      Cerca in matrice (categoria, utility, emittente, data):
        - prima: classe_utenza_id = <derivato>
        - fallback: classe_utenza_id IS NULL
      Se nessun match: ERRORE E_CATEGORIA_LISTINO_NON_MAPPATA
      Altrimenti:
        prezzo_base = riga listino
        applica variazione matrice se presente
        origine = CATEGORIA
```

### Output

Il resolver ritorna sempre:

- `prezzo` (persistito su `commesse_attivita.prezzo_snapshot`) e `prezzo_base_snapshot`
- `origine_prezzo` ∈ `{PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA, MANUALE}`
- `tipo_variazione_applicata` ∈ `{PERCENTUALE, VALORE_FISSO, PREZZO_FISSO, NESSUNA}`, `valore_variazione_applicata`
- FK popolate del caso: `listino_versione_id` + `listino_riga_id`, `contratto_id`, `promo_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`

Su ogni riga `vendite.commesse_attivita` vengono persistite **8 nuove dimensioni snapshot v5** (`prezzo_base_snapshot`, `origine_prezzo`, `tipo_variazione_applicata`, `valore_variazione_applicata`, `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`), che si aggiungono ai campi pricing già presenti nel modello operativo (`prezzo_snapshot`, `prezzo_bloccato`, `listino_versione_id`, `listino_riga_id`, `pricing_mode`, `prezzo_da_riallineare`). Il ciclo di vita di questi ultimi è descritto nel §7.

Le stesse 8 dimensioni sono propagate su `vendite.attivita_fatturabili` all'emissione, preservando la tracciabilità fino alle righe fattura.

---

## 4. Convenzione segno delle variazioni

Le variazioni di tipo `PERCENTUALE` e `VALORE_FISSO` sono **firmate**:

| Valore | Effetto |
|---|---|
| **Negativo** (es. -10) | Sconto (10%  di riduzione o -10€ di correzione) |
| **Positivo** (es. +5) | Maggiorazione |
| **Zero** | Vietato dal service (no-op inutile) |

`PREZZO_FISSO` (ammesso solo in promo) è un prezzo assoluto ≥ 0 che **sostituisce** il prezzo base.

Formule applicate dal resolver:

```
PERCENTUALE:  prezzo_finale = prezzo_base × (1 + valore / 100)
VALORE_FISSO: prezzo_finale = prezzo_base + valore
PREZZO_FISSO: prezzo_finale = valore
```

---

## 5. Articoli, tipologia e BoM

### 5.1 Tipologia articolo

Ogni articolo ha `listino_tipologia_id` (FK a `config.listini_tipologie`). Un articolo può essere inserito solo in listini con la **stessa tipologia** (guard DB trigger `trgfn_listini_righe_guard_tipologia`).

Esempi:

- articolo di tipologia `PRODOTTI` → inseribile solo in listini PRODOTTI
- articolo di tipologia `CONSUMO` (voce utility) → solo in listini CONSUMO per quella utility

### 5.2 Distinta base (BoM) — componenti esposti

Un articolo composito (`is_composito = true`) ha una distinta base in `articoli_componenti`. Il flag `esposto_in_fattura` decide il comportamento:

- **Nessun componente esposto** (CASO B / B1 / B2): il composito ha un prezzo unico (riga listino sul composito, o somma componenti a fallback). Resolver al push, status quo.
- **Almeno un componente esposto** (CASO A): il resolver ritorna N righe (una per componente). Ogni componente esposto diventa una **riga negoziabile a se' stante** dentro il documento sorgente — vedi §5.2.1 sotto. Al push, la pipeline espande l'articolo composito in N righe `commesse_attivita` separate.

Logica completa in [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito).

#### 5.2.1 Componenti CASO A nel ciclo preventivo → commessa

> **Decisione di dominio 2026-05-11**: il prezzo della riga padre di un
> composito CASO A non e' negoziabile direttamente — e' un valore
> derivato dalla somma dei componenti. Ogni componente esposto vive
> come riga propria, con prezzo proprio risolto dal resolver e
> override manuale ammesso (L1).

**Razionale.** Prima del 2026-05-11 la riga preventivo di un composito
CASO A salvava un `prezzo_unitario` sul padre che pero' veniva
**ignorato silenziosamente al push**: il resolver risolveva N prezzi
per i componenti dal listino e quelli finivano in fattura. Cliente
vedeva X nel preventivo e Y nella fattura. Inoltre, se anche solo un
componente non aveva mappa listino, il push esplodeva **dopo** che
l'utente aveva accettato il preventivo. Bug logico del modello:
asimmetria fra preventivo (prezzo manuale ammesso sul padre) e push
(prezzo manuale ignorato, resolver obbligatorio per ogni componente).

**Modello nuovo**: per ogni documento sorgente che genera commesse
(preventivi, ordini, contratti, DDT, attivita consumi) esiste una
tabella `<sorgente>_righe_componenti` parallela a `<sorgente>_righe`.
Quando l'operatore inserisce una riga su articolo composito CASO A:

1. Il backend chiama `fn_<sorgente>_riga_componenti_init` che invoca
   il resolver e popola un record per ogni componente esposto, con
   `prezzo_unitario` = prezzo suggerito + `origine_prezzo` (PROMO /
   CONTRATTO_OVERRIDE / CONTRATTO_LISTINO / CATEGORIA — vedi §3).
2. Se il resolver fallisce su un componente (es. listino mancante),
   il componente viene comunque creato con `prezzo_unitario = 0` e
   `origine_prezzo = 'MANUALE'`. L'UI mostra un warning e l'operatore
   digita il prezzo a mano (richiede L1, vedi §6).
3. Il `prezzo_unitario` della riga padre e' **readonly** lato UI e
   ricalcolato automaticamente da un trigger DB come
   `SUM(prezzo_componente × coeff_qta_snapshot)`. Cambia ad ogni
   modifica di componenti.
4. Al push commessa, il `BoMComponentExpander` legge direttamente i
   prezzi gia' fissati su `<sorgente>_righe_componenti` — **senza
   ri-chiamare il resolver**. Snapshot pricing immutabile
   post-accettazione, simmetrico al pattern `prezzo_bloccato`.

**Componenti vs riga padre**: la riga padre composita CASO A esiste
sul documento sorgente come "ricetta" + totale calcolato. I componenti
vivono nella tabella parallela. In fattura ogni componente esposto
genera 1 riga `commesse_attivita` con `articolo_id = componente_id`,
`quantita = quantita_componente × quantita_padre`, `prezzo_unitario =
quello fissato sul componente preventivo`.

**Cascade quantita padre**: se l'operatore cambia la `quantita` della
riga padre, un trigger DB propaga il ricalcolo della `quantita` di
tutti i componenti come `coeff_qta_snapshot × quantita_padre`. Il
prezzo unitario dei componenti resta invariato.

**Cosa NON entra nella tabella componenti**: componenti con
`esposto_in_fattura = FALSE`. Restano interni al composito, vivono
solo nella BoM `articoli_componenti` e non sono mai negoziabili —
contribuiscono al prezzo via fallback "somma componenti" del resolver
nel CASO B.

**Workflow L1/L2/L3 sui componenti**: vedi §6.2.

### 5.3 Immutabilità della BoM — pattern "chiudi + nuova versione"

La distinta base è **immutabile nel tempo**: una volta inserita una riga in `articoli_componenti`, i campi di struttura (componente, `coeff_qta`, `esposto_in_fattura`, `obbligatorio`, `partecipa_qta`, `determina_qta_padre`, `valido_dal`) non possono essere modificati in place. Il trigger DB `trgfn_articoli_componenti_block_modifica_struttura` blocca gli UPDATE con errore `E_BOM_MODIFICA_VIETATA` e le DELETE (una riga BoM non si elimina mai: si chiude).

**Perché**: le commesse e le fatturazioni che hanno già consumato quella BoM restano ancorate alla struttura del momento, e lo snapshot `prezzo_bloccato` sulle righe commessa preserva il calcolo fatto all'epoca. Modificare la BoM "sotto" a una commessa emessa romperebbe la ricostruzione storica.

**Come si correggono errori o si evolve una distinta base**:

1. **Chiudi la riga corrente**: imposta `valido_al = oggi` (l'unico campo editabile in place). Dalla UI: menu kebab della riga → "Chiudi riga", oppure click sulla cella `valido_al` inline.
2. **Inserisci una nuova versione**: dalla UI → menu kebab → "Duplica come nuova versione". Il form si pre-compila con i valori della riga sorgente, `valido_dal = oggi`, `valido_al` vuoto. Modifica i campi desiderati e salva.

L'exclusion constraint daterange `ex_articoli_componenti_no_overlap` sull'indice GiST `(prodotto_id, componente_id, validita)` garantisce che non ci siano sovrapposizioni temporali tra versioni dello stesso componente.

**Campi ancora modificabili in place**: `note`, `meta`, `attivo`, `valido_al` (chiusura). Non sono campi di struttura.

---

## 6. Autorizzazioni override prezzo (L1)

Nel preventivo, il prezzo suggerito dal resolver può essere **sovrascritto manualmente** dall'operatore. L1 è attivo:

- Se il payload riga ha `prezzo_unitario` uguale al suggerito → passa sempre
- Se è diverso → il service verifica l'azione processo `prezzo_override_manuale`
  - Autorizzato: salva con origine `MANUALE`, traccia in `meta` il resolver originale
  - Non autorizzato: `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` (403)

Il badge UI mostra l'origine del prezzo (`PROMO` / `CONTRATTO_OVERRIDE` /
`CONTRATTO_LISTINO` / `CATEGORIA` / `MANUALE`) e il delta eventuale.

L2 (limite sconto/maggiorazione %) è in produzione (Sprint D 22-04-2026): vedi `VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT` in `config.parameters` e l'endpoint diagnostico `GET /vendite/pricing/limiti-utente/`.

### 6.2 L1/L2/L3 sui componenti BoM CASO A

> **Eccezione al §6**: su articoli compositi CASO A (vedi §5.2.1)
> l'override L1 si applica **sui singoli componenti esposti**, non sul
> prezzo padre. Il prezzo padre e' un valore calcolato readonly. Solo
> i componenti sono righe negoziabili.

Stesso flusso L1 della riga normale, applicato alla riga componente:

- Se `prezzo_unitario` del componente = suggerito dal resolver → passa
- Se diverso → service verifica `prezzo_override_manuale`
  - Autorizzato: salva con `origine_prezzo = 'MANUALE'`, traccia in
    `prezzo_resolver_context` JSONB il suggerito originale + delta
  - Non autorizzato: `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` (403)

**Listino mancante sul componente**: caso speciale del L1. Quando il
resolver fallisce su un componente al popolamento iniziale (es.
`E_CATEGORIA_LISTINO_NON_MAPPATA`), il componente viene creato con
`prezzo_unitario = 0`, `origine_prezzo = 'MANUALE'`,
`prezzo_resolver_context.error = '<codice_errore>'`. L'UI mostra
warning inline "listino mancante" e l'operatore digita il prezzo a
mano. Se ha `prezzo_override_manuale` passa, altrimenti errore L1
classico (e deve far aggiungere il listino prima di proseguire).

**L2 sui componenti**: stessi parametri di sistema della riga padre
(`VENDITE_MAX_SCONTO_PCT`, `VENDITE_MAX_MAGGIORAZIONE_PCT`). Il delta %
e' calcolato componente per componente vs il suo suggerito.

**L3 sui componenti**: workflow approvazione PENDING/APPROVED/REJECTED
opera anche su `<sorgente>_righe_componenti.stato_approvazione_prezzo`.
Il guard `trgfn_<sorgente>_guard_transizione_approvazione` blocca la
transizione del documento sorgente verso lo stato terminale (es.
preventivo → ACCETTATO) se esiste anche un solo componente PENDING. La
modifica della struttura del componente PENDING e' bloccata da
`trgfn_<sorgente>_righe_componenti_guard_pending` (simmetrico al guard
della riga padre).

### 6.1 L3 — Workflow approvazione out-of-policy (Sprint E)

Quando l'operatore richiede un prezzo che viola i limiti L2, può **richiedere approvazione al responsabile** invece di rinunciare. Il flusso:

1. **Riga oltre L2 + flag `richiesta_approvazione=true`**: il backend NON solleva errore. Crea una pratica `APPROVAZIONE_PREZZO` (stato APERTA, priorità NORMALE) e salva la riga con `stato_approvazione_prezzo='PENDING'` collegata alla pratica via `pratica_approvazione_prezzo_id`.
2. **Email best-effort al recipient configurato** in `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` (parameter scope user/group/emittente). Se il parameter non è configurato, la pratica resta visibile in coda senza notifica push.
3. **L'approver** (utente con azione `approva_prezzo_override` abilitata) vede la coda in `/vendite/approvazioni-prezzo/` filtrata per scope emittente. Per ogni pratica può:
   - **Approvare** → riga `stato_approvazione_prezzo='APPROVED'`, pratica CHIUSA con nota interna OK
   - **Rifiutare** → riga `stato_approvazione_prezzo='REJECTED'`, pratica CHIUSA con nota interna KO + motivazione

**Trigger DB di guardia**:
- `trgfn_preventivi_guard_transizione_approvazione`: blocca passaggio preventivo→ACCETTATO se esistono righe `stato_approvazione_prezzo='PENDING'` (`E_PREVENTIVO_RIGHE_PRICING_PENDENTI`)
- `trgfn_preventivi_righe_guard_pending`: blocca modifica struttura riga PENDING; permette solo transizione di stato approvazione (`E_RIGA_PREZZO_PENDENTE`)

**Endpoint API**:
- `POST /api/v1/vendite/righe/<riga_id>/approva-prezzo/` (body `{nota?}`)
- `POST /api/v1/vendite/righe/<riga_id>/rifiuta-prezzo/` (body `{motivazione?}`)
- `GET /api/v1/vendite/approvazioni-prezzo/?limit=&offset=`

**Riavvio richiesta**: se l'approver rifiuta, l'utente può modificare il prezzo (riga REJECTED non è bloccata) e ri-tentare. Una nuova violazione L2 con `richiesta_approvazione=true` crea una nuova pratica.

---

## 7. Ciclo di vita del prezzo sulla riga commessa

Il resolver calcola il prezzo al **momento del push sorgente → commessa**. Da quel momento il prezzo vive sulla riga `commesse_attivita` con un piccolo set di stati operativi che ne governano riallineamento, blocco manuale e segnalazioni di revisione. Questo layer è distinto dal resolver (non lo invoca più) e opera esclusivamente su commesse in stato `modificabile` e righe **non ancora fatturate**.

### 7.1 Flag di stato pricing su `commesse_attivita`

| Campo                   | Tipo    | Default   | Ruolo operativo                                                                                         |
| ----------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------- |
| `prezzo_snapshot`       | numeric | —         | Prezzo corrente della riga (output del resolver o override manuale)                                     |
| `prezzo_bloccato`       | boolean | `FALSE`   | Se `TRUE`, il prezzo è "congelato" da override manuale: il riallineamento automatico/massivo lo salta   |
| `prezzo_da_riallineare` | boolean | `FALSE`   | Segnalazione: il prezzo di listino è cambiato rispetto allo snapshot e la riga è candidata a revisione  |
| `pricing_mode`          | varchar | `'FIXED'` | Predisposizione per modalità di calcolo future (`FORMULA`, `SCAGLIONI`). Oggi solo `FIXED` è operativo  |
| `listino_versione_id`   | bigint  | —         | Versione listino risolta al momento dello snapshot (serve al guard di riallineamento — vedi §7.3)       |

### 7.2 Variazione prezzo eccezionale — blocco manuale (N7)

**Scopo**: permettere all'operatore di forzare un prezzo fuori dalle regole di listino/contratto/promo per una singola riga, con motivo obbligatorio.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/variazione-prezzo-eccezionale/`
Service: `fn_variazione_prezzo_eccezionale` ([commesse_service.py](/backend/vendite/manual/commesse_service))

Effetti:

- aggiorna `prezzo_snapshot = nuovo_prezzo`
- imposta `prezzo_bloccato = TRUE` (d'ora in poi il riallineamento salta la riga)
- appende una entry a `meta.variazioni_eccezionali` con `data`, `prezzo_precedente`, `prezzo_nuovo`, `motivo`, `stato_commessa`, `listino_versione_id_riferimento`

Precondizioni: commessa `modificabile`, riga non fatturata. Il servizio non invoca il resolver: il prezzo è deciso dall'operatore.

### 7.3 Riallineamento dal listino

**Scopo**: ricalcolare il prezzo di una riga quando il listino è cambiato rispetto allo snapshot originale.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/riallinea-prezzo/`
Service: `fn_riallinea_prezzo`

Flusso:

1. Guard: se `prezzo_bloccato = TRUE` → errore `E_COMMESSA_VALIDATION` (per ricalcolare bisogna prima sbloccare — §7.4).
2. Invoca il resolver sul contesto originale della riga (articolo, uom, data, BA, utility, emittente).
3. Se la **versione listino** è cambiata rispetto allo snapshot e il payload non contiene `conferma_versione_diversa=true`, ritorna un body di pre-conferma con `versione_originale_id`, `versione_attuale_id`, `prezzo_attuale`, `prezzo_ricalcolato`, `richiede_conferma=true`: l'UI chiede conferma all'operatore prima di procedere.
4. In caso di conferma (o versione invariata): aggiorna `prezzo_snapshot` con il nuovo valore, tiene `prezzo_bloccato = FALSE`, appende a `meta.riallineamenti` la storia del cambio (`data`, `prezzo_precedente`, `prezzo_nuovo`, `listino_versione_id_precedente`, `listino_versione_id_nuovo`).

Il flag `prezzo_da_riallineare` viene azzerato come side-effect: la riga è allineata.

### 7.4 Sblocco prezzo bloccato (N7-sblocco)

**Scopo**: rimuovere un blocco da variazione eccezionale e tornare al prezzo di listino corrente.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/sblocca-prezzo/`
Service: `fn_sblocca_prezzo`

Effetti:

- guard: errore `E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO` se la riga non è bloccata
- ricalcola dal resolver (come §7.3 ma senza guard versione)
- imposta `prezzo_snapshot = ricalcolato`, `prezzo_bloccato = FALSE`
- appende a `meta.sblocchi_prezzo` (`data`, `prezzo_bloccato_precedente`, `prezzo_ricalcolato`, `motivo`)

Motivo obbligatorio come per il blocco.

### 7.5 Dashboard "prezzi da riallineare"

La funzione [`vendite.fn_get_commessa_stato`](/dbzero/vendite/funzioni/fn_get_commessa_stato) espone il contatore `total_prezzo_da_riallineare` per ogni commessa: conta le righe con `prezzo_da_riallineare = TRUE` e alimenta la coda di revisione prezzi nella dashboard commesse.

### 7.6 Propagazione a `attivita_fatturabili`

All'emissione (`fn_emit_attivita_fatturabili_da_commessa`) il flag `prezzo_bloccato` e lo snapshot pricing vengono **propagati** sulla riga AF. Questo garantisce che:

- gli step della pipeline fatturazione non sovrascrivano un prezzo manualmente bloccato;
- lo snapshot resolver (8 dimensioni v5) resti tracciabile fino alla riga fattura.

Vedi [guida fatturazione §"Snapshot pricing su commessa"](fatturazione.md#snapshot-pricing-su-commessa-e-propagazione-ad-af).

### 7.7 Su `pricing_mode`

Il campo ha dominio CHECK `FIXED | FORMULA | SCAGLIONI` ed è predisposto per estensioni future del motore pricing (calcolo a formula su variabili di commessa, tariffe a scaglioni). **Oggi tutte le funzioni sorgente → commessa producono esclusivamente `FIXED`**: non esiste implementazione operativa per le altre due modalità. Le righe nate da `FIXED` sono quelle descritte nei §§3–6 (resolver v5 deterministico).

---

## 8. Ciclo di vita operativo

### 8.1 Nuovo listino

1. Admin: crea listino (codice, descrizione, utility, tipologia) — emittente derivato dall'operatore
2. Crea versione BOZZA con `valido_dal`
3. Popola righe prezzo (articoli coerenti con tipologia)
4. Attiva versione → BOZZA passa ad ATTIVA; eventuali versioni precedenti autoclose

### 8.2 Assegnare un listino a un cliente (scope categoria)

1. Definisci la categoria cliente (STANDARD, SILVER, GOLD…)
2. Imposta sul `billing_account` la `categoria_cliente_id`
3. Admin: crea riga matrice per (categoria, utility, emittente, classe_utenza opz.) → listino + variazione

Tutti i clienti della stessa categoria, utility, emittente condivideranno la regola senza duplicare listini.

### 8.3 Contratto individuale

1. Commerciale: stipula contratto con BA, scegliendo modalità A/B/C
2. Inserisce righe (se C: obbligatorie per ogni articolo preventivabile)
3. Transizione DRAFT → ATTIVO → il resolver STADIO 1 userà il contratto

### 8.4 Promo

1. Admin vendite: crea riga in `promo_articoli` (articolo, uom, periodo, tipo+valore variazione, codice)
2. La promo vale per tutti i BA con categoria che partecipa promo
3. A scadenza periodo (`valido_al`), la promo smette di applicarsi automaticamente

---

## 9. Garanzie DB

Il database rafforza la determinismo con vincoli espliciti (non è "responsabilità del client"):

| Vincolo | Tabella | Cosa garantisce |
|---|---|---|
| `ex_contratti_no_overlap` | `contratti` | Un solo contratto attivo per (BA, istanza, utility, ambito) nel periodo |
| `ex_categ_cli_listini_no_overlap` | `categorie_clienti_listini` | Una sola riga matrice per (categoria, utility, emittente, classe) nel periodo |
| `ex_promo_articoli_no_overlap` | `promo_articoli` | Una sola promo attiva per (articolo, uom) nel periodo |
| `ex_listini_versioni_no_overlap` | `listini_versioni` | Una sola versione ATTIVA per listino nel periodo |
| `uq_listini_righe_key_attiva` | `listini_righe` | Una sola riga attiva per (versione, articolo, uom) |
| `trgfn_listini_righe_guard_tipologia` | trigger | Articolo e listino devono avere la stessa tipologia |
| `trgfn_contratti_modalita_c_righe_complete` | trigger | Modalità C: attivazione blocca se righe incomplete |
| `trgfn_contratti_utilities_guard_tipo_classe` | trigger | Tipo/classe utenza coerenti con ambito (NULL per COMMERCIO) |

Il resolver poggia su queste invarianti — il codice Python non deve duplicarle.

---

## 10. Errori espliciti

Nessun fallback silenzioso. Ogni scenario non risolvibile produce un errore strutturato:

| Codice | Quando |
|---|---|
| `E_PREZZO_LISTINO_NON_TROVATO` | BA senza contratto e senza categoria mappata |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` | Categoria esistente ma nessuna riga in matrice per la quadrupla |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | Listino risolto ma nessuna riga prezzo per (articolo, uom) |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | Contratto modalità C senza riga per l'articolo richiesto |
| `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE` | Articolo in listino di tipologia diversa |
| `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` | L1: override prezzo non autorizzato |
| `E_VENDITE_PRICING_FAILED` | Errore generico pricing (envelope, dettaglio in `detail`) |
| `E_BOM_MODIFICA_VIETATA` | Tentata modifica/eliminazione campo struttura BoM. Risolvere con pattern chiudi+inserisci nuova versione (vedi §5.3) |
| `E_BOM_VALIDO_AL_INVALIDO` | Tentata chiusura riga BoM con `valido_al < valido_dal` |
| `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` | Tentata accettazione preventivo con righe in attesa di approvazione (L3) |
| `E_RIGA_PREZZO_PENDENTE` | Tentata modifica struttura riga in stato `stato_approvazione_prezzo='PENDING'` |
| `E_APPROVAZIONE_PREZZO_NON_AMMESSA` | Tentata approva/rifiuta su riga non PENDING o senza pratica collegata; oppure coda approvazioni richiesta da admin globale senza emittente |

Tutti gestiti dal frontend con messaggi user-friendly (vedi `error_policies.py` backend).

---

## 11. Cosa NON c'è più (modello pre-v5)

Per chi arrivava dal vecchio modello:

- ❌ `vendite.listini_associazioni` — **droppata** (F1-DB-26). Il suo ruolo è coperto da categoria cliente + contratto + dimensione emittente interna al listino.
- ❌ "Listini derivati" con `listino_base_id` e variazione — mai implementati. La variazione vive nella matrice (per categoria) o nel contratto (individuale).
- ❌ `catalogo.articoli.voce_utility` — droppata. L'equivalente v5 è `listino_tipologia_id`.
- ❌ Resolver a 7 livelli con `match_rank` — sostituito dal resolver deterministico a 3 stadi senza tie-break.
- ❌ Campo `priorita` su versioni/associazioni — rimosso. Le invarianti `EXCLUDE` garantiscono univocità, niente tie-break.

---

*Gestione Listini e Pricing — ZeroERP v5 (23 aprile 2026, chiusura end-to-end)*
