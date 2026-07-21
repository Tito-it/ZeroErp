# Brief DB — Quantità immutabili sulla commessa + porta oneri (il libro giornale)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-17 · **Owner**: Tid
> **Stato**: 🟢 **step 3 + step 1 + PORTA ONERI (step 4/5/6/7) FATTI** — porta oneri
> **applicata su dev + pgTAP verde (2026-07-21)**. Step 3 (`tipo_movimento` colonna+CHECK incl.
> `ONERE`, `20260717-01..04`) e **step 1 (guard immutabilità CA+AF, `20260721-01..02`,
> codici 550/551, pgTAP `plan(16)` verde)** applicati e testati. **Porta oneri** (changeset
> `20260721-03..09` **APPLICATI** + pgTAP `test-porta-oneri-v1` **`plan(19)` verde**): vocabolario `config.causali_onere`
> (5 voci, mono-lingua), colonna FK `causale_onere_id`+CHECK biconditional su `commesse_attivita`,
> **modello articolo↔causale**: `catalogo.articoli.causale_onere_id` (1:1) → **5 articoli-onere**
> (uno per causale, **IVA propria**), `fn_upsert` esteso con `p_causale_onere_id`, madre
> `fn_aggiungi_onere_commessa(…, p_articolo_onere_id, …)` (riga SOURCELESS qta=1 APPROVATA +
> writer `commesse_attivita_log`), codici 552/553/554. **pgTAP tutti verdi** (porta base
> `plan(19)`, contatore cieco `plan(5)`, giro completo onere→fattura `plan(12)` 12/12 dopo il
> fix `fn_group` — vedi §7 step 9). **Restano solo BE**: ponte approvazione (step 2, hardening),
> permessi prezzo N5/N7 (step 8). Verificato sul codice vivo **2026-07-21**.
>
> **✅ Decisioni ratificate con Tid (2026-07-21)**: (a) causali **mono-lingua `descrizione`**
> come i vocabolari gemelli (`tipi_reso`…), NON `label_key` (§4c.3 rivisto); (b) causale su
> **colonna FK dedicata** `causale_onere_id`, non in `meta`; (c) **modello articolo↔causale 1:1**
> — un articolo È un onere collegandogli una causale (`catalogo.articoli.causale_onere_id`), così
> **ogni onere porta la SUA IVA** (l'IVA sta sull'articolo, non è più unica): risolve il vincolo
> «l'IVA non può essere solo 22%» — penale fuori campo art.15, resto 22% (§4c.8 riscritto);
> (d) riga onere **SOURCELESS** (il CHECK `sorgente_pair` impone tipo+uid entrambi-o-nessuno e un
> inserimento diretto non ha documento → sorgente NULL; discriminatore portante
> `tipo_movimento='ONERE'`) → la sorgente `DIRECT_ENTRY` NON serve a questa slice.
> **Validità confermata (2026-07-21)**: nessun brief successivo (coda-lavori, be-fe
> processi-fatturazione) tocca quantità/immutabilità/oneri/prezzo → design intatto. Anzi lo
> **step 1 è più urgente**: il contatore merce (viste `20260717-11/12`, live) poggia
> sull'invariante `AF.quantita = CA.quantita` immutabile, oggi presidiata **solo de-facto**
> (nessun writer) + post-fattura (`guard_fatturato`) — il guard è la rete mancante.
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
   > ⚠️ **i18n (nota 2026-07-21, frontend-standards §Multilingua)**: se le causali vanno a
   > video in multilingua, la tabella deve **emettere un `label_key`** (contratto a 3 livelli
   > DB→BE→FE), radice **`vendite.commesse.*`** (mai `oneri.*` piatto), chiavi in **it.json E
   > en.json**, guardrail `scripts/check_i18n_keys.py` **verde** (valida le chiavi emesse dal
   > DB). Valutare `label_key` vs `descrizione` per-lingua sul modello dei vocabolari esistenti
   > (`tipi_reso`/`motivi_fermo`/`causali_trasporto`). Vale anche per gli eventuali `reason_key`
   > di capability/transizioni introdotte dalla porta.
   >
   > ✅ **RISOLTO (2026-07-21) — MONO-LINGUA `descrizione`, niente `label_key`.** Verificato
   > sul codice vivo: i tre vocabolari gemelli (`tipi_reso`/`motivi_fermo`/`causali_trasporto`)
   > sono **tutti mono-lingua** (una sola colonna `descrizione`, resa a video via `LookupSelect`),
   > NON usano `label_key`. Il pattern `label_key` vive solo in `config.transizioni_stati_*`
   > (i **bottoni-azione** di una macchina a stati, ruolo UI diverso). Una causale onere è una
   > voce di **tendina**, gemella di `tipi_reso` → si segue quel pattern: `config.causali_onere`
   > con `descrizione` (IT). Conseguenza: **non** passa da `scripts/check_i18n_keys.py` (nessuna
   > `label_key` emessa). Il percorso `label_key` `vendite.commesse.*` resta disponibile solo se
   > in futuro queste voci dovranno comparire tradotte — eccezione rispetto agli altri vocabolari.
   >
   > **Voci seedate (Tid 2026-07-21)**: `ONERE_SENZA_CONTRATTO`, `SPESE_TRASFERTA`,
   > `MAGGIORAZIONE_URGENZA`, `SPESE_AMMINISTRATIVE`, `PENALE` (`20260721-05`, CSV append per
   > aggiungerne). Discriminatore = **colonna FK** `commesse_attivita.causale_onere_id`
   > (`20260721-04`) + CHECK biconditional `(tipo_movimento='ONERE') ⇔ (causale IS NOT NULL)`,
   > NON `meta` (stessa critica del §3 al jsonb). `fn_upsert` esteso con `p_causale_onere_id`
   > (`20260721-06`).
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

### 4c.8. Le colonne obbligatorie di `commesse_attivita` — il problema veicolo (scoperto 2026-07-21)

Il brief assumeva «riga di puro valore, qta=1». La realtà del codice vivo: `commesse_attivita`
ha **NOT NULL + FK + trigger `require_attivo`** su `articolo_id`, `istanza_utility_id`, `uom_id`
(oltre a `data_attivita`, `competenza_*`, `prezzo_snapshot`). Un onere non ne ha di naturali →
servono dei **veicoli**. Decisioni (Tid 2026-07-21):

- **articolo_id** → **modello articolo↔causale (Tid 2026-07-21)**: «un articolo È un onere
  collegandogli una causale». Nuova colonna `catalogo.articoli.causale_onere_id` (FK, **1:1**,
  `20260721-05`): un articolo è un onere ⟺ causale valorizzata. Seed di **5 articoli-onere**
  (`20260721-09`, natura `SERVIZIO_UNA_TANTUM`, uom `NR`), uno per causale. La madre riceve
  l'**articolo-onere** (`p_articolo_onere_id`) e **deriva** causale + uom (e a valle l'IVA) da esso.
  > ✅ **IVA RISOLTA (Tid 2026-07-21)**: l'IVA vive sull'articolo → **ogni onere porta la SUA
  > aliquota** (non più unica). Mappa seedata: `ONERE_SENZA_CONTRATTO`/`_TRASFERTA`/`_MAGG_URGENZA`/
  > `_SPESE_AMM` = **22%** (iva 16); `ONERE_PENALE` = **Escluso art.15** (iva 1, ES — le penali non
  > sono corrispettivo, fuori campo). Aggiungere/variare = una riga di `articoli_onere.csv`.
- **istanza_utility_id** + **tipo_doc_fiscale_id** → **forniti dal chiamante**: nessun default
  sensato; l'onere si aggancia al servizio/documento reale che l'operatore conosce. `tipo_doc`
  obbligatorio perché la riga nasce APPROVATA+NON_EMESSA = emittibile (guard `tipo_doc_emittibile`).
- **uom** = `NR`, **qta=1**, **competenza/data** = oggi (default), override opzionale.
- **Riga SOURCELESS**: `chk_commesse_attivita_sorgente_pair` impone `sorgente_tipo_id` e
  `sorgente_uid` **entrambi-o-nessuno**; un inserimento diretto non ha documento sorgente e non
  ha un `uid` naturale → **sorgente NULL**. Il discriminatore portante resta `tipo_movimento='ONERE'`
  (+ causale + segment `MAN:`). **Conseguenza sul §4c.1**: la sorgente `DIRECT_ENTRY` **non serve**
  a questa slice (resta disponibile per un futuro inserimento diretto *con* chiave esterna).

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
| 1 | Guard immutabilità su `commesse_attivita.quantita` **e** `attivita_fatturabili.quantita`, bypass GUC di percorso (§4a, deciso) | ✅ **FATTO (2026-07-21)** — `20260721-01` guard CA (blocca `UPDATE OF quantita` su EMESSA), `20260721-02` guard AF **mirror-enforcement** (blocca se `quantita ≠ CA madre`; scelta 2026-07-21 perché l'emit fa UPSERT `SET quantita` → un "blocca-sempre" lo romperebbe). Bypass GUC riusato: `zeroerp.maintenance_reset_lotto_draft`. Codici `E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE` (550) / `E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE` (551). pgTAP `test-guard-quantita-immutabile-v1` **plan(16) verde** (senza emit: CA sourceless + flip EMESSA + AF INSERT diretto, per aggirare il guard esistenza-sorgente 2026-07-18). |
| 2 | Fix ponte approvazione: il push approva le proprie righe (`p_righe_ids`) (§4b) — **hardening raccomandato**, non più prerequisito | ☐ |
| 3 | `tipo_movimento` a colonna + CHECK + backfill NORMALE (CA e AF) (§4c.2) | ✅ **FATTO E APPLICATO** (committato) — **anticipato nella slice DDT/resi** (step 0b del piano di ripartenza): changeset `20260717-01..04` + pgTAP `test-tipo-movimento-colonna-v1`. Motivo dell'anticipo: il contatore filtra `tipo_movimento = 'NORMALE'` (§5) e deve nascere sulla colonna vera, non riaprirsi dopo. Dettaglio in §4c.2 |
| 4 | Vocabolario causali config + seed (§4c.3) | ✅ **SCRITTO (2026-07-21)** — `config.causali_onere` (`20260721-03`) mono-lingua + seed 5 voci (`20260721-08`); colonna FK `causale_onere_id`+CHECK biconditional (`20260721-04`); `fn_upsert`+`p_causale_onere_id` (`20260721-06`). **Applicato dev + pgTAP verde.** |
| 5 | Sorgente `DIRECT_ENTRY` accesa + convenzione `segment_key` manuale (§4c.1/.6) | ➖ **RIVISTO (2026-07-21)** — riga **SOURCELESS** (§4c.8: `sorgente_pair` entrambi-o-nessuno, nessun documento) → `DIRECT_ENTRY` non serve a questa slice. Convenzione `segment_key` = `MAN:<commessa>:<progressivo>` implementata nella madre. |
| 6 | Madre/endpoint «aggiungi onere» (qta=1, causale, `post_permission`, riga nasce **APPROVATA** — niente endpoint approvazione, deciso §4c.5) | ✅ **SCRITTO (2026-07-21)** — **modello articolo↔causale 1:1**: colonna `catalogo.articoli.causale_onere_id` (`20260721-05`, UNIQUE) + 5 articoli-onere (`20260721-09`, IVA propria: 22% + penale fuori campo). Madre DB `fn_aggiungi_onere_commessa(…, p_articolo_onere_id, …)` (`20260721-07`): riga ONERE qta=1 APPROVATA sourceless, causale+uom+IVA derivate dall'articolo; codici 552/554. `post_permission` = BE (fuori perimetro DB). **Applicato dev + pgTAP verde.** |
| 7 | Writer `commesse_attivita_log` (primo evento: la voce manuale) — **dopo** riscrittura del suo manuale (§4c.7) | ✅ **SCRITTO (2026-07-21)** — writer dentro la madre (evento `ONERE_AGGIUNTO`); manuale `commesse_attivita_log` riscritto sul comportamento reale (rimosso il «push/pull» inesistente). |
| 8 | `post_permission` su N5/N7 prezzo (§4d) — indipendente, può andare per primo | ☐ |
| 9 | pgTAP: UPDATE quantita su EMESSA bloccato (CA **e** AF) · re-push su NON_EMESSA passa (via GUC) · riga onere nasce APPROVATA e fa il giro completo fino in fattura · porta rifiuta qta ≠ 1 e negative · contatore cieco alle righe MAN (§5) · se fatto lo step 2: riga BOZZA di terzi non approvata dal push | ✅ **VERDE (2026-07-21, migrate applicato)** — immutabilità: `test-guard-quantita-immutabile-v1` `plan(16)`. Porta base: `test-porta-oneri-v1` `plan(19)`. Contatore cieco alle MAN: `test-porta-oneri-contatore-cieco-v1` `plan(5)` (tripla cintura §5 sulla porta reale: `tipo_movimento`≠NORMALE + segment MAN:∉ORD/DDT + no `:R:`). **Giro completo**: `test-porta-oneri-giro-completo-v1` **`plan(12)` 12/12** — onere→emissione→AF→**fattura**, con **IVA per-onere fino in fattura** (penale fuori campo). Ha richiesto: fix `20260721-11` del bug **pre-esistente** `fn_group_attivita_fatturabili` (`SELECT INTO v_regole` senza alias + senza fallback no-row → `fn_generate_fatture_righe` rotto per QUALUNQUE articolo; la pipeline reale genera via BE, la fn DB non era mai stata esercitata così) + seed regole onere `20260721-10`. **Manca solo**: step 2 (BE). |
| 10 | Apply dev + comunicazione BE/FE (endpoint nuovi, permessi, vocabolari i18n) | ☐ |

> **Decisioni — stato (2026-07-17)**: perimetro guard ✅ (CA+AF, bypass GUC) · valore
> discriminatore ✅ (`ONERE`, dominio esteso) · vocabolario causali ✅ (approccio; **voci
> concrete da Tid in fase di seed**) · approvazione oneri ✅ (**nessuna**: responsabilità del
> caricatore autorizzato, riga nasce APPROVATA, porta usabile anche da processo) · negativi in
> catena ✅ (restano ammessi, §3-T3) · drift storico ✅ (**query eseguita da Tid, zero righe** —
> §6, nessuna bonifica). **Il brief è deciso in ogni sua parte: pronto per la realizzazione.**
