# Brief DB — Quantità immutabili sulla commessa + porta oneri (il libro giornale)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-17 · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE — **priorità sotto** [brief-db-fatturazione-ddt-resi.md](../work-done/brief-db-fatturazione-ddt-resi.md)
> (il contatore non ne dipende: procede in parallelo).
> **Sostituisce**: `brief-db-correzione-quantita-commessa-af.md` (ritirato in fase di design,
> mai realizzato: proponeva un percorso di UPDATE della quantità — esattamente ciò che questo
> brief vieta).
> **Origine**: design 2026-07-17 con Tid, a valle dell'analisi CA↔AF. Decisione Tid: *«le
> quantità di una riga esistente non possono essere modificate; al massimo si caricano righe
> manuali per correggere/aggiungere valori; il prezzo si aggiusta ma con autorizzazioni
> speciali»* — raffinata insieme fino alla forma «nessuna porta generica» (§1).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> secchi ammessi.

---

## 0. Il principio — la commessa è un libro giornale

Una riga di commessa nata dal push è un **fatto**: lo specchio del documento d'origine al
momento del push (`segment_key` la àncora alla riga di quel documento). I fatti **non si
modificano**: si correggono **con altri fatti** — righe nuove, mai UPDATE. È lo stesso
principio già vivo in `ordini_righe_fulfillment` (*«ogni evasione aggiunge, non sottrae»*).

Modificare la quantità di una riga esistente **romperebbe lo specchio con l'origine** — e in
ambiente utility lo romperebbe anche una riga manuale con quantità *positiva*, perché lì le
quantità sono consumi da misuratore: qualunque quantità non nata dal push inquina la
riconciliazione.

**Questo scioglie anche la confusione storica CA↔AF.** La domanda *«dove correggo, commessa o
AF?»* nasceva dal fatto che l'AF è nata **prima** delle commesse ed era il fulcro (Tid). La
risposta del libro giornale è che la domanda **sparisce**: non si corregge da nessuna parte —
si **aggiunge**, e si aggiunge dove nascono tutte le righe: **in commessa**. L'AF è puro
transito, mai toccata a mano.

## 1. Il problema semantico — e la risposta di design

Una «riga manuale» generica è **semanticamente opaca**: il sistema vede una riga, ma quella
riga può *essere* tre cose diverse — un onere legittimo, una nota di credito travestita
(quantità negativa), una correzione di merce travestita. L'intento sta **nella testa
dell'operatore** (Tid), e nessun consumatore a valle (contatore, riconciliazione utility,
dashboard) può leggerlo.

Non si prova a *indovinare* l'intento. Si applica il pattern che il progetto usa già ovunque
(`tipi_reso`, `motivi_fermo` — «nessun IF hardcoded: si legge il flag») portato alle
conseguenze:

> **Ogni intento ha esattamente una porta. La porta che si presta all'abuso non esiste.**

## 2. Le tre porte

| Intento | Porta | Governo |
|---|---|---|
| **Onere / voce di valore** senza contratto specifico (caso Tid) | azione dedicata «aggiungi onere»: riga in commessa, **quantità fissa = 1, solo positiva**, il prezzo È l'importo, causale obbligatoria da vocabolario config | approvazione umana + `post_permission` dedicato |
| **Correzione merce** (resa, in più/in meno) | il percorso dei **fatti**: reso → contatore → sottrazione/NC ([brief DDT/resi](../work-done/brief-db-fatturazione-ddt-resi.md) §3) | i fatti, non l'operatore |
| **Aggiustamento prezzo** | `fn_riallinea_prezzo` / `fn_variazione_prezzo_eccezionale` — esistono già | `post_permission` da **cablare** (oggi manca, §3-T2) |

La chiave di volta: **la riga manuale non porta quantità, porta valore** (`quantita = 1`
fissa). Conseguenze per costruzione, non per disciplina:

- la **NC travestita è impossibile** — niente quantità negative sulla porta, nulla da vigilare;
- l'**origine non si rompe mai**, nemmeno in utility — la riga manuale non parla la lingua
  delle quantità di merce/consumo; vive su un registro diverso (`tipo_movimento`, §4c);
- le **correzioni di merce non passano di qui** → niente segment compositi di rettifica,
  niente rischio di doppia correzione col contatore (§5).

**Residuo onesto** (dichiarato, non risolto): l'onere positivo usato per compensare
informalmente qualcosa è indistinguibile da un onere vero *per definizione*. Il presidio scelto
(Tid, §4c.5) è l'**autorizzazione all'ingresso** — la porta è riservata, chi carica è
responsabile — più l'audit pieno (causale + motivo + la riga stessa + log). Nessuna
approvazione a due passi.

## 3. Stato dei fatti (verificato sul DB vivo, 2026-07-17)

**Il principio è già legge de facto — per accidente, non per regola:**

- **Nessun percorso aggiorna `commesse_attivita.quantita`**: né endpoint, né repository, né
  funzione DB. Unico writer: il re-push su riga **non ancora emessa** (`fn_upsert…`, ramo
  `ON CONFLICT`, bloccato dopo dal guard `E_COMMESSA_ATTIVITA_GIA_EMESSA`). Il riallineamento
  prezzo (`update_attivita_prezzo`) tocca solo prezzo — pattern «CA fulcro → propaga su AF con
  finestra `fattura_riga_id IS NULL`» — ed è il modello di riferimento anche per questa slice.
- **Gli slot per la porta esistono già, dormienti**: `tipo_movimento ∈ {NORMALE, RETTIFICA}` e
  `tipo_consumo ∈ {ACCONTO, CONGUAGLIO, STORNO}` (dominio validato in `fn_upsert…`, salvati in
  `meta`; **nessun chiamante li usa** — tutti passano NORMALE/CONGUAGLIO); scope
  **`DIRECT_ENTRY`** = *«inserimento diretto (futuro)»* nel CHECK di `config.sorgenti`, **zero
  sorgenti lo usano**; `fn_upsert_commessa_attivita` **accetta già** righe senza sorgente
  documento (`p_sorgente_tipo_id`/`p_sorgente_uid` opzionali, `segment_key` libera).

**Le tre trappole** (tutte verificate — sono i prerequisiti del §4):

- **T1 — Il ponte di approvazione travolge tutto.** L'approvazione attività **non ha
  endpoint**: è automatica nel push, che chiama `approva_commessa_attivita` **senza filtro
  righe** → approva *tutte* le BOZZA/NON_EMESSA della commessa (docstring: *«il push è esso
  stesso l'autorizzazione delle attività generate»* — vero per le righe del push, falso per le
  altre). Un onere in BOZZA in attesa di approvazione verrebbe **spazzato ad APPROVATA dal
  primo push successivo**. La fn supporta già `p_righe_ids`: il service passa NULL.
- **T2 — L'autorizzazione sul prezzo oggi non esiste.** Gli endpoint N5/N7 di commessa
  (riallinea / variazione eccezionale / sblocca) **non hanno `post_permission`**: basta il
  permesso generico di scrittura sull'area vendite. I codename dedicati esistono
  (`prezzo_override_manuale`, `approva_prezzo_override`) e presidiano i gate di
  preventivi/contratti/DDT — ma **non sono cablati sugli endpoint di commessa**.
- **T3 — Nessun CHECK di segno su tutta la catena.** `commesse_attivita.quantita`,
  `attivita_fatturabili.quantita`, `fatture_righe.qta`: quantità negative tecnicamente ammesse
  ovunque (unico blocco: `≠ 0` dentro `fn_upsert…`). Oggi regge *solo perché* l'unico scrittore
  è il push e i documenti a monte hanno i loro CHECK positivi. La porta manuale è il **primo
  scrittore non-documentale**: deve portarsi la propria disciplina, sotto non c'è rete.

  **✅ DECISO (Tid, 2026-07-17) — si lascia così: i valori negativi restano ammessi sulla
  catena.** Nessun CHECK di segno generale: è **predisposizione deliberata** ai modelli futuri
  che potranno averne bisogno (conguagli utility a favore del cliente, storni — il dominio
  `tipo_consumo {ACCONTO, CONGUAGLIO, STORNO}` li anticipa già). Conseguenze:
  - la disciplina di segno vive **solo sulla porta onere** (`quantita = 1` positiva, guard
    della porta — §4c.4): è la porta a essere vincolata, non la catena;
  - `fatture_righe.qta` resta libera e la slice NC ne deciderà il segno **consapevolmente**
    (§6) — qui si registra che è una decisione sua, non una svista;
  - ⚠️ il **contatore** (brief DDT/resi §3a) legge quantità dalla catena assumendole positive:
    i suoi filtri (`tipo_movimento = 'NORMALE'`, segmenti di partita) sono la sua protezione —
    se un modello futuro introdurrà righe negative NORMALE, dovrà farsi carico dell'impatto
    sul segno del contatore.

Più un rilievo di modello: **`tipo_movimento` non è una colonna** — la fn lo valida e lo salva
in `meta` (jsonb). Come discriminatore portante (contatore, utility, dashboard filtrano su di
esso) sepolto in un jsonb senza vincolo è fragile: un INSERT diretto lo bypassa.

> ✅ **Chiuso (scritto 2026-07-17, non applicato)** — step 3 del §7, anticipato nella slice
> DDT/resi: `20260717-01..04`. Ora è colonna su CA **e** AF con CHECK
> (`NORMALE|RETTIFICA|ONERE`), scritta da `fn_upsert_commessa_attivita` e propagata dall'emit.
> Il jsonb non ospita più il valore: **una casa sola**. Verificato prima di spostarlo che
> nessuno leggesse `meta->>'tipo_movimento'` (solo writer) → nessun consumer rotto. Residuo
> dichiarato: la chiave storica resta sulle righe già scritte, inerte e sempre `'NORMALE'`
> (provato da un guard fail-fast nel changeset), perché ripulirla con un UPDATE di massa
> costerebbe uno snapshot storico per riga e farebbe scattare i guard `require_attivo`.

## 4. Cosa serve

### 4a. Il guard di immutabilità — da accidente a regola

Trigger guard su `UPDATE OF quantita` di `commesse_attivita`: vietato su righe **EMESSA**
(oggi lo garantisce solo l'assenza di chiamanti — un UPDATE a mano in SQL passa). Codice
errore dedicato, messaggio parlante ([[feedback_error_codes_messaggi_errore]]).

**✅ DECISO (Tid, 2026-07-17) — guard su ENTRAMBE, CA e AF, con bypass GUC di percorso.**

- Il re-push su riga NON_EMESSA resta l'unico writer legittimo di `commesse_attivita.quantita`
  (aggiorna lo specchio dell'origine prima che diventi fatto fatturabile): il guard lo ammette
  via **GUC di percorso** (pattern `zeroerp.maintenance_reset_lotto_draft`); la forma esatta
  (nome GUC, dove si arma) al team.
- **Anche `attivita_fatturabili.quantita`**: l'AF specchia la CA (l'emit copia), i suoi writer
  legittimi (emit, reset-lotto) non toccano la quantità → guard con lo stesso bypass GUC. Si
  chiude per sempre la finestra «correggo l'AF a mano dopo il reset», che il principio dichiara
  illegittima.

### 4b. Fix del ponte di approvazione (T1) — **declassato a hardening raccomandato**

> ⚠️ **Rev 2026-07-17**: con la decisione del §4c.5 (le righe della porta **nascono
> APPROVATA**, niente passaggio in BOZZA) il ponte **non le travolge più** → questo fix non è
> più un prerequisito della porta. Resta **raccomandato**: il push che approva righe non sue è
> concettualmente sbagliato e colpirà il **prossimo** creatore di righe BOZZA (chiunque sia).

Il push approva **le proprie righe**: il service passa a `approva_commessa_attivita` gli id
delle righe appena upsertate (`p_righe_ids`), non NULL. Grep dei pgTAP esistenti prima
([[feedback_guard_breaks_existing_tests]]).

### 4c. La porta onere

1. **Sorgente**: si accende `DIRECT_ENTRY` — nuova riga in `config.sorgenti` (es.
   `VOCE_MANUALE`, `target_table` = la commessa stessa o nessuna — forma al team). Il
   vocabolario era predisposto per questo.
2. **Discriminatore**: `tipo_movimento` **promosso a colonna** con CHECK su
   `commesse_attivita` (e propagato su AF), backfill `NORMALE` dalle righe esistenti.
   **✅ DECISO (Tid, 2026-07-17)**: dominio **esteso** con **`ONERE`** — un onere non è una
   rettifica; `RETTIFICA` resta libero per i conguagli/rettifiche vere di domani.
3. **Causale obbligatoria**: vocabolario `config` (nuova tabella codice/descrizione standard,
   seed CSV [[feedback_seed_80_data_csv]]). **✅ DECISO (Tid, 2026-07-17)**: si parte con 3-4
   voci reali — l'elenco concreto lo fornisce Tid **in fase di seed** (prima voce nota dal caso
   d'origine: onere senza contratto specifico); aggiungere dopo costa una riga di CSV.
4. **Disciplina quantità**: `quantita = 1` fissa e positiva per le righe della porta —
   enforced dal guard (T3), non dalla UI.
5. **Autorizzazione — ✅ DECISO (Tid, 2026-07-17): NESSUNA approvazione a due passi.** *«Chi
   carica oneri è responsabile di quello che fa»*: il presidio è **all'ingresso**, non a valle —
   `post_permission` dedicato (codename nuovo, es. `carica_voce_manuale`) riservato agli
   autorizzati. Conseguenze:
   - la riga della porta **nasce `APPROVATA`** (la madre passa `p_stato_approvazione =>
     'APPROVATA'` a `fn_upsert…`, che già lo supporta): niente endpoint di approvazione,
     niente riga BOZZA in attesa;
   - la porta è una **madre DB** → utilizzabile anche da un **processo automatico** autorizzato
     (previsto da Tid: *«o potrebbe essere un processo»*), non solo dall'endpoint interattivo;
   - l'audit resta pieno: causale + motivo + la riga stessa + `commesse_attivita_log` (punto 7).
6. **segment_key**: convenzione dedicata (es. `MAN:<commessa>:<progressivo>` — forma al team;
   oggi non esiste alcun prefisso manuale, verificato).
7. La riga fa il **giro normale da APPROVATA in poi**: nasce `APPROVATA` (punto 5) →
   emissione → AF → fattura. La riga stessa è l'audit; in più è il primo **evento vero** per
   `commesse_attivita_log` (writer da costruire — il suo manuale va prima riscritto: metà
   descrive operazioni inesistenti, il «pull» che toglie dalla commessa non esiste).

### 4d. Prezzo — cablare l'autorizzazione (T2)

`post_permission` sugli endpoint N5/N7 di commessa, riusando i codename esistenti
(`prezzo_override_manuale` per l'override, coerente con i gate già vivi su
preventivi/contratti/DDT). Nessuna funzione DB nuova: è il requisito «autorizzazioni speciali»
di Tid, oggi disatteso solo sul punto dove il prezzo conta di più.

## 5. Interazione col contatore (brief DDT/resi)

Doppia cintura, entrambe per costruzione:

1. i «fatturati» del contatore si misurano sui **segmenti della partita** (`ORD:`/`DDT:`) — le
   righe della porta hanno segmenti propri (`MAN:`) e non vi entrano mai;
2. il contatore filtra `tipo_movimento = 'NORMALE'` — anche un errore di segment non
   inquinerebbe il libro mastro della merce.

Le correzioni di **merce** restano interamente sul percorso dei fatti (reso → contatore →
NC): la porta onere non le tocca, e con l'immutabilità (§4a) **AF.quantita = CA.quantita
sempre** → la misura del contatore su AF è stabile per costruzione.

## 6. Fuori perimetro

- **Slice NC**: le righe negative in fattura (tecnicamente ammesse: `fatture_righe.qta` è
  senza CHECK di segno — appunto utile a quella slice) e la rettifica documento↔documento
  (`fatture_rettifiche`, tabella-ponte esistente). Vincolo già posto dal brief DDT/resi §7: la
  NC dovrà essere **attribuibile alla merce e portare una quantità**.
- **Movimenti di magazzino.**
- **✅ CHIUSA — Drift storico: NESSUNO** (query eseguita da Tid sul DB dev, 2026-07-17:
  **zero righe**). CA e AF coincidono ovunque: nessuna bonifica necessaria, il guard può
  atterrare senza backfill. Per riferimento, la query usata (utile da ripetere prima
  dell'apply del guard, come cintura):

  ```sql
  SELECT ca.id, ca.segment_key, ca.quantita AS qta_commessa, af.quantita AS qta_af
  FROM vendite.commesse_attivita ca
  JOIN vendite.attivita_fatturabili af ON af.commessa_attivita_id = ca.id
  WHERE ca.quantita IS DISTINCT FROM af.quantita;
  ```

## 7. Avanzamento

| # | Step | Stato |
|---|---|---|
| 0 | Decisioni: **TUTTE CHIUSE** (2026-07-17) — drift storico verificato: **zero righe** (query §6 eseguita da Tid). Unica coda operativa: le **voci concrete** del vocabolario causali (Tid, in fase di seed) | ✅ |
| 1 | Guard immutabilità su `commesse_attivita.quantita` **e** `attivita_fatturabili.quantita`, bypass GUC di percorso (§4a, deciso) | ☐ |
| 2 | Fix ponte approvazione: il push approva le proprie righe (`p_righe_ids`) (§4b) — **hardening raccomandato**, non più prerequisito | ☐ |
| 3 | `tipo_movimento` a colonna + CHECK + backfill NORMALE (CA e AF) (§4c.2) | ✅ **SCRITTO, non applicato** — **anticipato nella slice DDT/resi** (step 0b del piano di ripartenza): changeset `20260717-01..04` + pgTAP `test-tipo-movimento-colonna-v1`. Motivo dell'anticipo: il contatore filtra `tipo_movimento = 'NORMALE'` (§5) e deve nascere sulla colonna vera, non riaprirsi dopo. Dettaglio in §4c.2 |
| 4 | Vocabolario causali config + seed (§4c.3) | ☐ |
| 5 | Sorgente `DIRECT_ENTRY` accesa + convenzione `segment_key` manuale (§4c.1/.6) | ☐ |
| 6 | Madre/endpoint «aggiungi onere» (qta=1, causale, `post_permission`, riga nasce **APPROVATA** — niente endpoint approvazione, deciso §4c.5) | ☐ |
| 7 | Writer `commesse_attivita_log` (primo evento: la voce manuale) — **dopo** riscrittura del suo manuale (§4c.7) | ☐ |
| 8 | `post_permission` su N5/N7 prezzo (§4d) — indipendente, può andare per primo | ☐ |
| 9 | pgTAP: UPDATE quantita su EMESSA bloccato (CA **e** AF) · re-push su NON_EMESSA passa (via GUC) · riga onere nasce APPROVATA e fa il giro completo fino in fattura · porta rifiuta qta ≠ 1 e negative · contatore cieco alle righe MAN (§5) · se fatto lo step 2: riga BOZZA di terzi non approvata dal push | ☐ |
| 10 | Apply dev + comunicazione BE/FE (endpoint nuovi, permessi, vocabolari i18n) | ☐ |

> **Decisioni — stato (2026-07-17)**: perimetro guard ✅ (CA+AF, bypass GUC) · valore
> discriminatore ✅ (`ONERE`, dominio esteso) · vocabolario causali ✅ (approccio; **voci
> concrete da Tid in fase di seed**) · approvazione oneri ✅ (**nessuna**: responsabilità del
> caricatore autorizzato, riga nasce APPROVATA, porta usabile anche da processo) · negativi in
> catena ✅ (restano ammessi, §3-T3) · drift storico ✅ (**query eseguita da Tid, zero righe** —
> §6, nessuna bonifica). **Il brief è deciso in ogni sua parte: pronto per la realizzazione.**
