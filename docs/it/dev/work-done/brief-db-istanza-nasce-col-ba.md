# Brief DB — L'istanza nasce col BA, sempre

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-08; risposta e analisi del team DB
> (`dev/db-tid`) nello stesso giorno, §6. **A chi:** team DB; poi BE/FE (§5), che **attende** la
> consegna DB.
> **Origine:** D10-bis di
> [migliorie-generali-BE-FE-da-test-valutazione.md](migliorie-generali-BE-FE-da-test-valutazione.md):
> chiudendo il restore per id del lookup istanze, che leggeva istanze di qualunque emittente,
> è emerso che la regola di scope «un'istanza è dell'emittente del suo BA» ha un buco
> **solo** se un'istanza può esistere senza BA. Il DB oggi lo ammette.
> **Decisione:** di Tid, 2026-10-08 — *«la regola giusta è che nascono insieme e deve essere
> sempre così»*. Decisioni D-1…D-4 di Tid del 2026-10-08 (§6.1).
> **Stato:** ✅ DB **chiuso** il 2026-10-08: R-1/R-2/R-7 (`20261008-50…-62`, §6.10), R-8/R-9
> (`-63…-73`, §6.12) e la RLS dei dati precontrattuali (`-74…-76`, §6.13) **applicati da Tid**,
> pgTAP senza regressioni. ✅ BE/FE fatti il 2026-10-08 (§7). ✅ **Chiuso e archiviato il
> 2026-10-10**, su decisione di Tid. Del collaudo a video (§7.4) è superato il punto del preventivo;
> i punti sulle pratiche sono **rimandati** alla ripresa di quel cantiere, oggi fermo. I debiti
> del §7.5 ancora aperti sono passati in PROJECT_CONTEXT § «Aperto — Media priorità».
> ➡️ Il 2026-10-10 il resolver per istanza, il ramo morto della capability (§6.10.3, §6.12.3) e i
> debiti rimasti senza sede (`uq_gestori_singleton`, il pgTAP del gestore globale) sono passati a
> [brief-db-istanza-nasce-col-ba-residui.md](brief-db-istanza-nasce-col-ba-residui.md) (D25).
> Decisioni D-1…D-9 prese (§6.1), D-10 (§7.1). R-3 non si fa.

## 1. La regola

**Istanza e billing account nascono insieme, nella stessa transazione, sempre.** Un'istanza
senza BA non è uno stato del ciclo di vita (non c'è una «fase prospect» con la sola istanza):
è un dato fuori regola.

La regola vale **per coppia (istanza, utility)** (D-2): ogni utility dichiarata su un'istanza ha
il suo BA. Tutti i BA di un'istanza sono dello **stesso emittente** (D-4).

Il soggetto prende il ruolo CLIENTE con la prima istanza (D-3): il BA lo pretende. Un soggetto
può non avere mai un BA — un soggetto che è solo fornitore — ma allora non ha nemmeno istanze.

Il codice del BA resta generato **alla nascita**, com'è oggi (D-1 rivista, §6.1).

## 2. Che cosa dice oggi il DB (contratto, letto dalla doc auto-generata)

| Sede | Che cosa ammette | Con la regola |
| --- | --- | --- |
| `anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata` (constraint trigger, al COMMIT) | basta **uno** fra tre satelliti: `billing_account`, `istanze_dati_precontrattuali`, `clienti`. Con la sola riga precontrattuale l'istanza nasce **senza BA** | 🔴 il BA deve esserci sempre |
| `vendite.preventivi.billing_account_id` | **nullable** (l'istanza è NOT NULL) | 🔴 asimmetria: su `offerte_commerciali` e `contratti` è **NOT NULL** |
| `anagrafiche.billing_account.codice` | NOT NULL, generato **all'INSERT** (`trgfn_billing_account_gen_codice`) e bloccato (`trgfn_lock_columns`) | ✅ resta così (D-1 rivista) |
| Guida [generazione-cliente.md](../../guide/generazione-cliente.md) §«Pre-contrattuale» | «Soggetto → Istanza → [pausa, **anche indefinita**] → Ruolo CLIENTE + BA»; «un'istanza può legittimamente restare in pausa per sempre» | 🔴 da riscrivere |

Le righe che il team DB aggiunge, dalla stessa lettura (§6):

| Sede | Che cosa ammette | Con la regola |
| --- | --- | --- |
| `anagrafiche.billing_account`: DELETE, `UPDATE OF istanza_utility_id` | il trigger dell'istanza è solo `AFTER INSERT` su `istanze_utilities`; il BA si cancella (nessun guard, solo lo storico) e si sposta su un'altra istanza (`lock_columns` copre solo `codice`) | 🔴 l'istanza resta senza BA dopo la nascita |
| `vendite.preventivi`, `offerte_commerciali`, `contratti`: FK **semplice** su `billing_account_id` | nessun vincolo né trigger di tabella lega il BA del documento alla sua `(istanza_utility_id, utility_id)` | 🔴 un documento può puntare al BA di un'altra istanza |
| `anagrafiche.istanze_dati_precontrattuali` | la riga per la coppia `(istanza, utility)` nasce anche senza il BA di quella coppia | 🔴 con D-2 è fuori regola |
| `anagrafiche.emittenti_fiscali_billing_account` | ogni BA prende l'emittente dell'operatore all'INSERT (`trgfn_billing_account_link_ef`) e il legame si corregge finché non c'è storia (`trgfn_efba_guard_storia_emittente`); `fn_guard_albero_ba_emittente` controlla l'albero padre/figlio, **non** i BA della stessa istanza | 🔴 con D-4 due BA della stessa istanza possono avere emittenti diversi |

⭐ L'applicazione rispetta già la regola: l'unico punto del backend che crea un'istanza è
l'orchestratore cliente (`ClienteService`, `apps/anagrafiche/services/clienti_service.py`), che
crea ruolo CLIENTE → istanza → BA → cliente nella stessa transazione. Il buco è nel **contratto**
del DB, non nell'uso di oggi: un'importazione, uno script o una schermata futura potrebbero
creare l'istanza da sola, e il DB non direbbe niente.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **Il trigger pretende il BA.** `trgfn_istanze_utilities_require_utility_dichiarata` (o il guard che il team DB ritiene giusto) rifiuta al COMMIT un'istanza senza almeno un `billing_account`. `istanze_dati_precontrattuali` e `clienti` restano satelliti di **dati**, non sostituti del BA. Il codice d'errore: riusare `E_ISTANZA_UTILITY_SENZA_UTILITY` solo se il significato tiene, altrimenti codice nuovo (e allora policy generata **e** frase di ripiego lato BE). Allineare anche `script.fn_check_utility_istanza_coerenza`, che dichiara la stessa lista di satelliti. **Forma del team DB: §6.2** |
| **R-2** | **Simmetria dei precontrattuali.** Con la regola ogni istanza ha il suo BA (1:1 per utility, `uq (istanza_utility_id, utility_id)`): `vendite.preventivi.billing_account_id` diventa NOT NULL come su offerte e contratti, oppure si **deriva** dall'istanza. La forma la sceglie il team DB. **Forma del team DB: §6.3** |
| **R-3** | ~~Il codice del BA prima della prima fattura~~ — **non si fa** (D-1 rivista da Tid, §6.1): il codice resta generato alla nascita del BA. Gli elementi raccolti restano nel §6.5, se la questione si riaprisse |
| **R-4** | **La guida** `generazione-cliente.md` §«Pre-contrattuale» va riscritta sulla regola (niente pausa con la sola istanza). Le pagine `manual/` di `istanze_utilities` e `billing_account` se ne parlano. **Perimetro completo: §6.6** |
| **R-5** | **Le righe che oggi sono fuori regola** (istanze senza BA, preventivi senza BA): prima del vincolo, decidere con Tid se si correggono a mano o con un changeSet. ⛔ Il loro numero non decide la regola: entra solo come fatto datato. **Nota del team DB: §6.7** |
| **R-6** | pgTAP: istanza con il solo satellite precontrattuale → rifiutata al COMMIT; istanza + BA nella stessa transazione → ammessa; preventivo senza BA → secondo la forma di R-2. **Casi aggiunti dal team DB: §6.8** |
| **R-8** | *(da D-6, risposta di Tid del 2026-10-08)* **Un BA, un cliente.** Un'istanza ha tanti clienti quanti BA. Analisi e forma nel §6.11; attende D-7 e D-8 |
| **R-7** | *(team DB, da D-4)* **Un'istanza, un emittente.** Tutti i BA di un'istanza risolvono allo stesso emittente: rifiuto all'aggancio del BA all'emittente e alla correzione del legame. Forma nel §6.4 |

**D-1 — risposta di Tid (2026-10-08), rivista lo stesso giorno:** la prima risposta era il
codice del BA generato alla prima fattura. Ripensandoci, Tid osserva che **non è un vincolo**
e che si può lasciare com'è: il codice nasce col BA. Nelle guide (`generazione-cliente.md`,
`gestione-delle-istanze-utility.md`, `soggetti-e-ruoli-anagrafici.md`) e nelle pagine `manual/`
di `billing_account`, `istanze_utilities` e `clienti` non c'era nessuna decisione precedente sul
codice differito: dicono solo che il codice si genera in automatico all'inserimento.

## 4. Fuori da questo brief

* Lo **scope** del lookup istanze resta «un'istanza è dell'emittente del suo BA»
  (`script.fn_check_ba_visible_for_emittenti`): con la regola è completo, e non serve una
  funzione di scope nuova. Il BE l'ha già applicata anche al restore per id (2026-10-08,
  D10-bis): con R-1 il caso «istanza senza BA invisibile a un operatore» smette di esistere.
  ⚠️ *(team DB)* La regola di scope è **univoca** solo con R-7: senza, un'istanza con due BA
  di emittenti diversi sarebbe «dell'emittente del suo BA» in due modi.

## 5. Ricaduta BE/FE (dopo la consegna DB)

* Commenti da riscrivere sulla regola: `apps/anagrafiche/services/istanze_utility_service.py` e
  `apps/anagrafiche/db/istanze_utility_repository.py` («preventivi prospect senza BA», «istanze
  totalmente orfane»), `apps/anagrafiche/db/soggetti_repository.py` («prospect puri: hanno solo
  istanze, il ruolo CL nasce col BA»).
* FE: il badge «Solo istanza» di `core/components/IstanzaUtilityLookup.vue` (istanza orfana) e la
  chiave `solo_istanza_badge` perdono il caso: si tolgono.
* Se R-1 porta un codice d'errore nuovo: policy generata **e** frase di ripiego. *(team DB)* Sì,
  porta codici nuovi: §6.2 e §6.4.
* *(team DB)* Un soggetto con il solo preventivo ha il ruolo CLIENTE (D-3): le liste e i filtri
  che leggono «clienti» dal ruolo lo mostrano come cliente. È la regola, non un difetto; il BE
  verifichi che nessuna schermata dia per scontato il contrario.
* *(team DB)* Con R-2 il preventivo ha sempre il BA: i rami BE che trattano `billing_account_id`
  NULL sul preventivo diventano codice morto e si ritirano.

## 6. Risposta del team DB (2026-10-08)

### 6.1 Decisioni di Tid (2026-10-08)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Il codice differito è quello del BA, generato alla prima fattura? | **Rivista: no.** Non è un vincolo, e i documenti che precedono la fattura (contratti, offerte, ordini, DDT) portano già il BA: il codice resta generato alla nascita del BA. R-3 non si fa (§6.5) |
| **D-2** | La regola vale per istanza («almeno un BA») o per coppia (istanza, utility)? | **Per coppia**: ogni utility dichiarata su un'istanza ha il suo BA |
| **D-3** | Il ruolo CLIENTE nasce con la prima istanza? | **Sì.** Precisazione di Tid: la frase della guida «il soggetto potrebbe non acquisire mai il ruolo CLIENTE» resta vera, ma per un soggetto **senza istanze** (per esempio un soggetto che è solo fornitore). Falsa è l'istanza «in pausa» senza ruolo |
| **D-4** | Un'istanza con BA su utility diverse può avere BA di emittenti diversi? | **No**: un'istanza ha solo BA dello stesso emittente. Il DB oggi non lo impone (§2) → R-7 |
| **D-5** | L'istanza e' mono-utility? | **No**: un'istanza puo' avere piu' utility, ognuna col suo BA (§6.10.4). Guida corretta |
| **D-6** | Un solo cliente per istanza anche con piu' utility? | **No**: un BA ha un solo cliente, un'istanza ha tanti clienti quanti BA → **R-8** (§6.11) |
| **D-7** | Una pratica di quale BA parla? | La pratica porta l'aggancio a grana fine del cliente, **nullable** (pratiche di fornitori e altri ruoli). Superata dalla forma di D-9 |
| **D-8** | `fn_get_stato_cliente_by_istanza` e `view_clienti_istanza_states`? | **Si ritirano** (nessun consumatore applicativo) |
| **D-9** | Sulla pratica utility o BA? | **`billing_account_id`** nullable al posto di `utility_id` (§6.11.7-8): per gli altri ruoli basta `soggetto_ruolo_id`, che individua gia' il record specializzato |
| **R-9** | `gestori` senza `UNIQUE (soggetto_ruolo_id)` | **Si mette** il vincolo, come le altre specializzazioni (§6.11.8) |
| **Giro** | Un giro o due? | **Un giro unico**: R-8 e R-9 numerati dopo i `-62`, si applicano insieme a R-1, R-2, R-7. Via di Tid il 2026-10-08: scritti (§6.12) |

### 6.2 R-1 — la forma

* **Il satellite `clienti` era già un ramo morto.** `clienti.billing_account_id` è NOT NULL, con
  FK composta `(billing_account_id, istanza_utility_id)`: una riga cliente non esiste senza un BA
  sulla stessa istanza. Il cambio vero è togliere i precontrattuali dalla lista.
* **Con D-2 la regola diventa in gran parte strutturale:**
  * `istanze_dati_precontrattuali`: FK composta `(istanza_utility_id, utility_id)` →
    `billing_account (istanza_utility_id, utility_id)`. L'indice unico di destinazione esiste già
    (`uq_billing_instance_utility`). La riga precontrattuale di una coppia senza BA diventa
    impossibile: non serve un trigger;
  * `script.fn_check_utility_istanza_coerenza` si riduce al solo BA: le altre due fonti lo
    implicano. ⚠️ Non è la stessa regola del trigger (controlla la **coppia**, non l'esistenza di
    un BA): «allinearla» significa ridurla, non ricopiarle la lista;
  * il constraint trigger sull'istanza resta per la sola cosa che una FK non sa dire: «l'istanza
    ha almeno un BA».
* **Il trigger guarda solo la nascita, la regola dice «sempre».** Due porte da chiudere:
  * `billing_account.istanza_utility_id` e `utility_id` si **bloccano** (`lock_columns`): sono
    l'identità del BA, e spostarlo su un'altra istanza lascia orfana quella di partenza;
  * il **DELETE dell'ultimo BA** di un'istanza si rifiuta al COMMIT (constraint trigger deferred su
    `billing_account`, `AFTER DELETE`). Deferred perché la cancellazione dell'istanza intera, BA
    compreso, nella stessa transazione resta lecita.
* **Il codice d'errore è nuovo.** Il messaggio di `E_ISTANZA_UTILITY_SENZA_UTILITY` dice «serve
  almeno un riferimento (billing_account, dati precontrattuali, cliente)», che con la regola è
  falso. Codice nuovo (nome di lavoro `E_ISTANZA_SENZA_BA`), registrato con policy e messaggio;
  il vecchio si ritira se nessun altro lo solleva (censire dal nome).

### 6.3 R-2 — la forma

* Il BA del preventivo è **derivabile** da `(istanza_utility_id, utility_id)` grazie a
  `uq_billing_instance_utility`. Ritirare la colonna costerebbe tutti i suoi lettori (liste,
  push, capability, IVA, termini di pagamento): la si tiene, e la si **lega**.
* **Lo stesso difetto sta su offerte e contratti**, oltre che sul preventivo: la FK è semplice e
  nessun vincolo o trigger di tabella verifica che il BA sia quello della coppia
  `(istanza, utility)` del documento. Eventuali controlli nei verbi (`fn_create_contratto`,
  `fn_push_offerta_a_contratto`) non proteggono una scrittura diretta; da verificare quando si
  scrive il changeSet. Per il principio «vendite = acquisti, le asimmetrie si chiudono subito»
  si chiude su tutti e tre.
* **Forma:** sui tre documenti `billing_account_id` NOT NULL e FK composta
  `(billing_account_id, istanza_utility_id, utility_id)` → un indice unico nuovo su
  `billing_account (id, istanza_utility_id, utility_id)`. La coerenza BA↔istanza↔utility diventa
  struttura, e il guard di coerenza del preventivo (`trgfn_preventivi_guard_utility_istanza_coerenza`)
  diventa ridondante: si ritira nello stesso giro.
* **Lettori del NULL** — esito del censimento (2026-10-08, §6.10.3):
  * l'uscita anticipata su NULL di `vendite.trgfn_preventivi_guard_emittente_ba` **resta, ed e'
    voluta**: il guard e' BEFORE ROW e il NOT NULL si controlla DOPO i trigger BEFORE. Senza
    l'uscita, un preventivo senza BA passerebbe NULL a `fn_get_emittente_fiscale_pk` e
    risponderebbe con un errore tecnico invece che col vincolo (23502). Il changeSet che la
    toglieva e' stato scritto e ritirato prima della consegna;
  * il ramo `v_ba_id IS NULL` di `script.fn_available_actions_preventivo` (motivo
    `PREVENTIVO_SENZA_BILLING_ACCOUNT`, chiave i18n `…push_commessa_reason.senza_billing_account`)
    e il predicato «testata completa» di `vendite.fn_preventivo_ha_residuo_commessa` diventano
    irraggiungibili: **debito dichiarato**, si ritirano al prossimo giro su quelle funzioni (la
    prima e' di ~350 righe e il ritiro tocca anche il frontend).

### 6.4 R-7 — un'istanza, un emittente

* L'emittente di un BA nasce dal mapping `emittenti_fiscali_billing_account` creato **dopo**
  l'INSERT (`trgfn_billing_account_link_ef`, AFTER) e si può correggere finché il cliente non ha
  storia (`trgfn_efba_guard_storia_emittente`). Il guard va quindi dove nasce o cambia
  l'emittente: AFTER INSERT/UPDATE/DELETE su `emittenti_fiscali_billing_account` (e AFTER INSERT
  su `billing_account`, per il BA che cade sul mapping di default), come già fa
  `fn_guard_albero_ba_emittente` per l'albero padre/figlio.
* La regola si misura con l'emittente **risolto** del BA (`anagrafiche.fn_get_emittente_fiscale_pk`),
  non con la sola riga di mapping, così che il default conti come gli altri.
* ⭐ Regola del 2: «l'albero non attraversa due emittenti» e «l'istanza non attraversa due
  emittenti» sono la stessa domanda su due insiemi di BA. Prima di scrivere il guard nuovo, il
  team DB valuta se estrarre da `fn_guard_albero_ba_emittente` il pezzo comune. Codice d'errore
  nuovo (nome di lavoro `E_ISTANZA_EMITTENTI_DIVERSI`).

### 6.5 Elementi su R-3, se si riaprisse

R-3 non si fa (D-1 rivista), confermato da Tid il 2026-10-08 col motivo **di modello**:
contratti, offerte, ordini e DDT vengono prima della fattura e portano già il BA, con il suo
codice. Un codice che nasce alla prima fattura lascerebbe quei documenti senza il riferimento
che stampano, e costringerebbe a scegliere un sostituto (codice dell'istanza o un provvisorio).
Il solo guadagno sarebbe non consumare codici per chi riceve un preventivo e non compra, e non
è un vincolo.

Stima di sviluppo fatta il 2026-10-08, per chi riaprisse la questione: il cuore DB è piccolo,
ma tutti i lettori del codice del BA andrebbero censiti (funzioni e viste DB, colonne `ba_codice`
delle liste configurabili, repository e context builder del BE, lookup e liste del FE, pgTAP) e
vanno decise le stampe dei documenti precedenti alla fattura.

Si annotano gli elementi raccolti, perché non vadano ricercati:

* `trgfn_lock_columns` confronta con `IS DISTINCT FROM`: blocca anche il passaggio NULL → valore.
  Fra le funzioni di `script` non c'è un blocco «scrivibile una volta sola»;
* `trgfn_billing_account_gen_codice` scatta su INSERT **e** UPDATE quando `codice` è NULL: con il
  codice nullable, il codice nascerebbe alla prima modifica qualsiasi del BA, non alla fattura;
* `uq_billing_account_codice` ammette più NULL: lì nessun ostacolo.

### 6.6 R-4 — perimetro della documentazione

* `guide/generazione-cliente.md`: §«Pre-contrattuale» (la pausa); §«Istanza», righe sul ruolo
  CLIENTE che «arriva dopo» (con la precisazione di D-3: senza istanze, nessun ruolo CLIENTE);
  §«Billing account» («viene creato dopo l'istanza»); il riquadro dell'invariante («i
  precontrattuali scelgono l'istanza prima che esista un BA»).
* `guide/gestione-delle-istanze-utility.md` §«Ogni istanza dichiara la utility (strategia C)»: le
  tre fonti satellite e la «nota sul retroattivo».
* Pagine `manual/`: `trgfn_istanze_utilities_require_utility_dichiarata`,
  `fn_check_utility_istanza_coerenza`, `trgfn_preventivi_guard_utility_istanza_coerenza` (se
  ritirato si cancella), `istanze_dati_precontrattuali`, `billing_account`,
  `emittenti_fiscali_billing_account` (R-7).

### 6.7 R-5 — prima dei vincoli

Diversamente dal trigger `AFTER INSERT`, le FK composte e i NOT NULL verificano **anche le righe
esistenti** al momento del changeSet. La correzione delle righe fuori regola (istanze senza BA,
precontrattuali di coppie senza BA, preventivi senza BA o col BA di un'altra coppia, istanze con
BA di emittenti diversi) va quindi fatta **prima**, ed è una condizione del changeSet, non una
scelta. Ogni changeSet porta la sua `preCondition` sul conteggio delle righe che non
passerebbero. Il modo della correzione (a mano o con un changeSet) si decide con Tid.

**Decisione di Tid (2026-10-08):** sono dati di test, si correggono a mano; serve solo una
verifica che li mostri prima di applicare i changeSet. Fatto datato, dbdev 2026-10-08:
nessuna istanza senza BA, nessun documento col BA di un'altra coppia, nessuna istanza su due
emittenti; 18 righe precontrattuali su una coppia senza BA (istanze che hanno il BA su
un'altra utility: il caso che D-2 rende fuori regola) e 11 preventivi senza BA.

✅ **Corretti a mano da Tid il 2026-10-08**: le 18 righe precontrattuali cancellate (nessun
riferimento da `contratti_utilities` / `offerte_commerciali_utilities`, nessun documento sulle
loro coppie); gli 11 preventivi, tutti ANNULLATI su (istanza 182, utility 5), collegati al BA
già esistente di quella coppia. La verifica rilanciata subito dopo restituisce zero righe. La
query di verifica va rilanciata **subito prima** di applicare i changeSet: i dati di dbdev
cambiano nel frattempo.

### 6.8 R-6 — casi aggiunti

* cancellazione dell'ultimo BA di un'istanza → rifiutata al COMMIT; cancellazione di istanza e BA
  insieme → ammessa;
* spostamento del BA su un'altra istanza (`UPDATE` di `istanza_utility_id`) → rifiutato;
* riga precontrattuale su una coppia `(istanza, utility)` senza BA → rifiutata;
* preventivo, offerta e contratto col BA di un'altra istanza o di un'altra utility → rifiutati;
* secondo BA della stessa istanza su un emittente diverso → rifiutato; correzione del legame
  emittente che lascia l'istanza su due emittenti → rifiutata.

### 6.9 Fuori da questo brief — il BA di un documento chiuso si riscrive

Emerso dalla correzione del §6.7 (2026-10-08): l'`UPDATE` di `billing_account_id` è passato
su preventivi **ANNULLATI**. Nessun guard di `vendite.preventivi` (`lock_columns`,
`guard_annullamento`, `guard_transizione`, `guard_emittente_ba`…) impedisce di cambiare il BA
di un documento chiuso. Con R-2 il BA non potrà più puntare a un'altra coppia (FK composta), e
siccome la coppia ha un solo BA il valore è di fatto univoco; resta la domanda di modello
generale: **quali colonne di testata si riscrivono su un documento in fase chiusa**, per tutte
le famiglie (preventivo, offerta, contratto, ordine, DDT). Non fa parte di questo lavoro.
⏳ All'archiviazione di questo brief, al più tardi, diventa un brief nuovo `brief-db-*` in
`work-in-progress/` (con la voce-rimando nel registro delle migliorie): non va in archivio
come nota.

### 6.10 Consegna DB (2026-10-08) — applicata

#### 6.10.1 ChangeSet

| # | File | Cosa |
| --- | --- | --- |
| -50 | `00_schema/anagrafiche/…-add-uq-billing-account-id-coppia` | UNIQUE (id, istanza_utility_id, utility_id) sul BA: destinazione delle FK composte |
| -51 | `00_schema/anagrafiche/…-add-fk-idp-billing-account-coppia` | FK dei dati precontrattuali verso il BA della coppia (preCondition: zero righe fuori regola) |
| -52 | `00_schema/vendite/…-alter-preventivi-billing-account-coppia` | `preventivi.billing_account_id` NOT NULL + FK composta `fk_preventivi_ba_coppia` |
| -53 | `00_schema/vendite/…-add-fk-offerte-commerciali-ba-coppia` | FK composta `fk_offerte_commerciali_ba_coppia` |
| -54 | `00_schema/vendite/…-add-fk-contratti-ba-coppia` | FK composta `fk_contratti_ba_coppia` |
| -55 | `20_code/anagrafiche/…-create-fn-guard-istanza-ha-ba` | il guard «l'istanza ha il suo BA» (DEFINER), `E_ISTANZA_SENZA_BA` |
| -56 | `20_code/anagrafiche/…-update-trgfn-istanze-utilities-require-ba` | il constraint trigger della nascita delega al guard |
| -57 | `20_code/anagrafiche/…-create-trigger-billing-account-require-istanza-ha-ba` | constraint trigger al COMMIT sulla cancellazione del BA |
| -58 | `20_code/script/…-update-fn-check-utility-istanza-coerenza-solo-ba` | la check della coppia legge il solo BA (firma invariata) |
| -59 | `20_code/anagrafiche/…-create-fn-guard-istanza-ba-emittente` | R-7, gemello del guard dell'albero, stessa check |
| -60 | `20_code/anagrafiche/…-create-fn-guard-istanza-ba-gestore-globale` | R-7 sullo spostamento dell'azienda predefinita (raggio N) |
| -61 | `20_code/anagrafiche/…-create-trigger-billing-account-guard-istanza-emittente` | R-7 alla nascita del BA (AFTER INSERT, z95) |
| -62 | `20_code/anagrafiche/…-create-trigger-efba-guard-istanza-emittente` | R-7 sul collegamento BA → azienda (AFTER, z95) |

`80_data` (CSV, nessun changeSet nuovo): `config/codici_errore.csv` e `config/messaggi_errore.csv`
— `E_ISTANZA_SENZA_BA` (1224), `E_ISTANZA_EMITTENTI_DIVERSI` (1225), `E_BA_ISTANZA_IMMUTABILE` (1226),
tutti `CONFLITTO_STATO`; `E_ISTANZA_UTILITY_SENZA_UTILITY` `obsoleto_dal 2026-10-08`; causa e
soluzione di `E_PREV_UTILITY_ISTANZA_INCOERENTE` riscritte sulla fonte unica.
`dbops/automation_lock_columns.csv`: `billing_account.istanza_utility_id` e `.utility_id` →
`E_BA_ISTANZA_IMMUTABILE`. ⚠️ Il trigger di lock lo **genera l'automazione** (`ci_apply`, o il job
notturno su dev): finche' non gira, il test 13 del pgTAP nuovo fa `skip()` dichiarato.

#### 6.10.2 Come e' stato provato

Tutto con l'SQL **estratto** dagli YAML, come owner, in transazioni annullate (nessuna scrittura
rimasta su dbdev):

* preCondition dei -51…-54: zero righe su dbdev (dopo la correzione a mano del §6.7);
* undici casi della regola (nascita senza BA, cancellazione dell'ultimo BA, istanza cancellata
  intera, dati precontrattuali con e senza BA, secondo BA, preventivo col BA di un'altra coppia,
  preventivo senza BA, BA su un altro emittente, check della coppia): tutti con l'esito atteso;
* `plpgsql_check` sulle otto funzioni nuove o cambiate: zero segnalazioni.

pgTAP — corpo concatenato all'SQL estratto, stessa transazione, come owner:

| File | Esito | Che cosa e' cambiato |
| --- | --- | --- |
| `anagrafiche/test-istanza-nasce-col-ba-v1.sql` (**nuovo**) | 13/13 (il 13 in `skip` finche' il lock non e' generato) | R-6 |
| `anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` | 4/4 | istanza + BA al posto di istanza + riga precontrattuale; soggetto costruito |
| `anagrafiche/test-create-istanza-from-pdp.sql` | 9/9 | il satellite dell'istanza e' il BA GAS |
| `anagrafiche/test-billing-account-auto-link-ef.sql` | 4/4 | finestra differita aperta fino ai BA dei test; slot 4 sull'istanza dello slot 3 |
| `rls/test-rls-billing-account-returning-secondo-emittente.sql` | 9/10 | finestra aperta fino al BA del test 1. Il rosso (test 6) e' **preesistente e da owner**: identico sull'originale, l'owner salta la RLS |
| `anagrafiche/test-istanze-dati-precontrattuali.sql` | si ferma alla pulizia iniziale | cliente costruito sul BA GAS. Il fermo e' **preesistente**, identico sull'originale: la pulizia tocca righe di dbdev gia' fotografate in un contratto (dato di macchina, non del modello) |
| `pratiche/test-proiezione-stato-sorgente.sql` | 31/31 | cliente costruito, il preventivo nasce col BA |
| `script/test-fn-available-actions-preventivo-v1.sql` | 8/8 | il preventivo nasce col BA; test 5 atteso su `PREVENTIVO_NESSUNA_RIGA_COMMESSA` |
| `vendite/test-fn-preventivo-ha-residuo-commessa-v1.sql` | 12/12 (piano 13 → 12) | test 3 = la regola (23502); test 7 ritirato; corretta una chiave i18n rimasta senza il prefisso `vendite.` (rossa da prima) |
| `anagrafiche/test-billing-account-guard-parent.sql` | 7/7 | la pulizia in coda apre la finestra differita (istanza e BA se ne vanno insieme) |
| `script/test-fn-disdetta-cliente.sql` | 12/12 | idem |
| `script/test-fn-check-utility-istanza-coerenza.sql` | 6/6 | solo l'intestazione |

⏳ **A Tid**: l'apply e la corsa dei pgTAP come applicazione (la RLS la prova solo quella).

#### 6.10.3 Debiti e limiti dichiarati

* **Ramo morto nelle capability del preventivo** (§6.3): `PREVENTIVO_SENZA_BILLING_ACCOUNT` e la
  sua chiave i18n non si raggiungono piu'; si ritirano al prossimo giro su
  `script.fn_available_actions_preventivo`, insieme al frontend. ➡️ Scritto il 2026-10-10 in
  `brief-db-istanza-nasce-col-ba-residui` (R-1, con i due filtri gemelli R-2 e R-3).
* **Lo spostamento dell'azienda predefinita** (`fn_guard_istanza_ba_gestore_globale`) non ha un
  pgTAP: con un operatore in sessione un BA senza collegamento risolve all'azienda di chi agisce,
  e il caso «uno collegato, uno no» non si costruisce senza smontare il contesto del mondo. La
  funzione e' provata solo da `plpgsql_check`. ➡️ D-4 di `brief-db-istanza-nasce-col-ba-residui`.
* **Ordine dei rifiuti sul BA**: cambiare `istanza_utility_id` verso l'istanza di un **altro
  soggetto** lo intercetta prima `trg_billing_account_a10_guard_soggetto_coerenza_istanza_ins_upd`
  (`E_BA_SOGGETTO_INCOERENTE_ISTANZA`), che in ordine alfabetico precede il lock. E' comunque un
  rifiuto; il lock parla per il cambio verso un'istanza dello stesso soggetto e per `utility_id`.
* Le FK semplici `fk_preventivi_billing_account`, `fk_offerte_commerciali_billing_account`,
  `fk_contratti_billing_account` restano accanto alle composte (il backend ne mappa i nomi).

#### 6.10.4 D-5: l'istanza e' mono-utility? — ✅ risposta di Tid (2026-10-08): **no, un'istanza puo' avere piu' utility**

Nessun vincolo nuovo: D-2 («per coppia») e R-7 erano gia' scritti per il caso multi-utility. La
guida delle istanze e' corretta (sezione «Utility» e invariante: la relazione 1:1 vale **per
utility**). ⚠️ **Resta da guardare, D-6 per Tid**: `clienti` ha `UNIQUE (istanza_utility_id)`,
quindi su un'istanza con piu' utility i BA sono piu' d'uno ma il **cliente e' uno solo** — una sola
utility dell'istanza arriva al contratto. E' voluto, o il vincolo dovrebbe essere
`(istanza_utility_id, utility_id)` come sugli altri satelliti? Non toccato in questo brief.

Testo della domanda, com'era posta:

La guida delle istanze dice «una istanza corrisponde a una sola utility» e «1 istanza = 1
utility», e l'appoggia sui vincoli UNIQUE dei satelliti. **Il DB non lo impone**: `billing_account`
e `istanze_dati_precontrattuali` hanno `UNIQUE (istanza_utility_id, utility_id)`, che ammette piu'
utility sulla stessa istanza (lo dimostra il test 7 del pgTAP nuovo: secondo BA, altra utility,
stessa istanza, ammesso). D-2 («per coppia») e R-7 sono scritti per il caso multi-utility e
valgono in entrambe le risposte.

* **Se l'istanza e' mono-utility**: manca un vincolo — `UNIQUE (istanza_utility_id)` su
  `billing_account` — e R-7 diventa automatico (un BA per istanza). Un changeSet in piu'.
* **Se e' multi-utility**: va corretta la guida (sezione «Utility» e l'invariante 1:1).

(Le frasi della guida sono state corrette dopo la risposta.)

#### 6.10.5 Al BE/FE (aggiunge al §5)

* **Codici nuovi**: `E_ISTANZA_SENZA_BA`, `E_ISTANZA_EMITTENTI_DIVERSI`, `E_BA_ISTANZA_IMMUTABILE`
  (`CONFLITTO_STATO`, nessun campo): policy generata e frase di ripiego.
  `E_ISTANZA_UTILITY_SENZA_UTILITY` e' obsoleto: il BE lo ha in `error_policies_generated.py` e
  `error_messages_fallback.py`.
* **FK nuove** che il BE mappa per nome: `fk_offerte_commerciali_ba_coppia` (offerte_service),
  `fk_contratti_ba_coppia` (contratti_service), `fk_preventivi_ba_coppia`: «il billing account non
  e' quello dell'istanza e della utility del documento».
* Il commento di `preventivi_service.crea_preventivo` sulla pre-validazione («no billing account,
  dati precontrattuali o cliente matching») parla delle tre fonti: ora e' il solo BA.
* Il ramo morto delle capability (§6.10.3) quando il DB lo ritira: la chiave
  `vendite.preventivi.push_commessa_reason.senza_billing_account` esce dai locales.

### 6.11 R-8 — un BA, un cliente (D-6, 2026-10-08)

**Risposta di Tid a D-6:** *«un BA ha solo un cliente, quindi un'istanza ha piu' BA e tanti clienti
quanti i BA»*.

#### 6.11.1 Che cosa dice oggi il DB

* `uq_clienti_istanza_utility` = `UNIQUE (istanza_utility_id)`: **un cliente per istanza**, il
  contrario della regola;
* nessun vincolo limita i clienti per BA: oggi lo stesso BA potrebbe avere due clienti su due
  righe, purche' su istanze diverse — ma la FK composta `(billing_account_id, istanza_utility_id)`
  lo impedisce gia' (un BA ha una sola istanza), quindi oggi la cardinalita' BA → cliente e'
  limitata **solo per caso** dal vincolo sull'istanza.

#### 6.11.2 La forma

* `UNIQUE (billing_account_id)` su `anagrafiche.clienti` al posto di `uq_clienti_istanza_utility`.
  Con la FK composta verso il BA, un cliente per BA implica al massimo un cliente per coppia
  (istanza, utility). La protezione «un solo cliente attivo per PDP»
  (`ex_clienti_no_overlap_stesso_pdp`) non cambia.
* ⚠️ Il backend mappa il nome `uq_clienti_istanza_utility` a una frase
  (`clienti_service.py`, «Esiste gia' un cliente per questa istanza»): con il vincolo nuovo la
  frase diventa «… per questo billing account» e il nome cambia.

#### 6.11.3 I lettori che oggi danno per scontato «un cliente per istanza»

Censimento del 2026-10-08 (funzioni, viste, backend). Con piu' clienti per istanza diventano
**ambigui in silenzio** (`LIMIT 1` o una JOIN che moltiplica le righe), quindi vanno sistemati
**prima** o **insieme** al cambio di vincolo, non dopo.

| Lettore | Che cosa fa | Con la regola nuova | Proposta |
| --- | --- | --- | --- |
| `vendite.fn_resolve_termini_pagamento` (livello 3) | prende termine e modalita' di pagamento dal cliente agganciandolo **per istanza** (`cl.istanza_utility_id = ba.istanza_utility_id`); il commento dice «deterministico grazie a uq_clienti_istanza_utility» | la fattura prenderebbe il termine di pagamento di **un cliente qualunque** dell'istanza | agganciare per BA (`cl.billing_account_id = ba.id`): e' il cliente del BA della fattura. Nessuna decisione serve |
| `script.fn_get_billing_account_by_istanza` | «il BA del cliente dell'istanza», `ORDER BY id DESC LIMIT 1`; la usa il backend per il **dettaglio pratica** (`pratiche_repository`, due punti) | con piu' BA sceglie l'ultimo cliente creato, non quello della pratica | **D-7** |
| `script.fn_get_stato_cliente_by_istanza` + vista `script.view_clienti_istanza_states` | «lo stato del cliente dell'istanza», `LIMIT 1` | ambiguo come sopra | nessun consumatore applicativo (solo la doc): **D-8** |

#### 6.11.4 Decisioni per Tid

* **D-7 — una pratica di quale BA parla?** `pratiche.pratiche` porta l'istanza ma **non** la
  utility ne' il BA: su un'istanza con piu' utility, «il cliente della pratica» non si ricava.
  Proposta del team DB: la pratica porta la **utility** (o il BA) e il resolver diventa
  `fn_get_billing_account_by_istanza(istanza, utility)` — la coppia individua un BA solo. Se una
  pratica e' per natura di una sola utility (un allaccio GAS), e' un dato che oggi manca.
* **D-8 — `fn_get_stato_cliente_by_istanza` e `view_clienti_istanza_states`**: nessun consumatore
  nel backend ne' nel frontend. Proposta: ritirarle (lo «stato del cliente» e' del cliente, cioe'
  del BA, non dell'istanza); in alternativa riscriverle per coppia.

#### 6.11.5 Ricaduta su guide e test

* Guida istanze: «L'istanza ospita **al massimo un cliente**», «la relazione istanza → cliente e'
  sempre 1:1», «il vincolo UNIQUE su `istanza_utility_id` garantisce un solo cliente per
  istanza» → un cliente **per BA**.
* pgTAP che asseriscono il vincolo vecchio o lo usano: da censire nel giro dei changeSet
  (`grep uq_clienti_istanza_utility`, piu' i test di `fn_resolve_termini_pagamento` e
  `test-fn-get-billing-account-by-istanza.sql`).

#### 6.11.6 Risposte di Tid (2026-10-08) e forma risultante

* **D-7: la pratica porta la utility, nullable.** Precisazione di Tid: una pratica non e' sempre di
  un cliente — `soggetto_ruolo_id` (sulla testata, nullable) la lega a qualunque ruolo (cliente,
  fornitore, …), e per un fornitore istanza e utility non esistono. Tid ricorda anche la
  **sorgente**: verificato, sta nella tabella ponte `pratiche.pratiche_sorgenti` (preventivo,
  ordine, contratto; ROOT o COLLEGATO, anche piu' d'una), non sulla testata.
  * Il ruolo dice **chi**, non **quale BA**: un ruolo CLIENTE ha un BA per ogni coppia
    (istanza, utility).
  * La sorgente porta il suo BA e quindi la sua coppia: e' da li' che la pratica **prende** la
    utility quando nasce da un documento. Non diventa una seconda strada di lettura del BA (una
    pratica puo' avere piu' sorgenti o nessuna, e due strade per lo stesso dato prima o poi
    dissentono).
* **D-8: si ritirano** `script.fn_get_stato_cliente_by_istanza` e `script.view_clienti_istanza_states`.

Forma (proposta del team DB, in attesa del via):

| # | Cosa |
| --- | --- |
| a | `pratiche.pratiche.utility_id` nullable + FK `config.utilities`; CHECK «utility solo con istanza»; FK composta `(istanza_utility_id, utility_id)` verso il BA della coppia (con un NULL non scatta). Le pratiche gia' scritte con un'istanza si valorizzano solo se l'istanza ha **un** BA: altrimenti restano NULL (si deriva solo cio' che e' univoco) |
| b | Chi crea le pratiche passa la utility: `pratiche.fn_crea_pratica` (parametro nuovo **in coda**), `vendite.fn_genera_pratica_da_preventivo` (la utility del preventivo: e' la sorgente), `pratiche.fn_genera_pratica_da_flusso` (la copia dalla pratica madre); il backend (`create_pratica`, form della pratica) e' richiesta al BE |
| c | `script.fn_get_billing_account_by_istanza(istanza, utility DEFAULT NULL)`: legge il **BA della coppia** da `billing_account` (non piu' dal cliente: il BA esiste dalla nascita dell'istanza, il «prospect senza BA» non c'e' piu'). Utility NULL: il BA solo se l'istanza ne ha **uno**, altrimenti NULL — mai un `LIMIT 1` |
| d | `anagrafiche.clienti`: `UNIQUE (billing_account_id)` al posto di `uq_clienti_istanza_utility`, piu' un indice semplice su `istanza_utility_id` (la FK verso le istanze perde l'indice che aveva) |
| e | `vendite.fn_resolve_termini_pagamento` livello 3: il cliente si aggancia **per BA** |
| f | D-8: `DROP` della vista e della funzione; pagine `manual/` cancellate |
| g | pgTAP: censimento di `uq_clienti_istanza_utility`, test del resolver e dei termini di pagamento; casi nuovi (due clienti sulla stessa istanza su due BA; secondo cliente sullo stesso BA rifiutato; pratica con utility senza istanza rifiutata) |

#### 6.11.7 Domanda di Tid: le pratiche reggono fornitori e altri ruoli? Serve una «sorgente del ruolo»?

Verifica sulla struttura (2026-10-08):

* le specializzazioni dei ruoli hanno `UNIQUE (soggetto_ruolo_id)` — `fornitori`, `vettori`,
  `psp`, `risorse_umane`, `emittenti_fiscali`: per questi ruoli il `soggetto_ruolo_id` della
  pratica individua **gia'** il record specializzato, senza ambiguita'. Le pratiche reggono;
* l'unico ruolo **a grana fine** e' il CLIENTE: un ruolo CL ha un BA (e, con R-8, un cliente)
  per ogni coppia (istanza, utility). E' l'unico caso in cui il ruolo non basta;
* ⚠️ `gestori` **non** ha `UNIQUE (soggetto_ruolo_id)`, mentre la guida «Soggetti & Ruoli» dice
  che tutte le specializzazioni ce l'hanno. Fuori da questo brief: o manca il vincolo, o la guida
  sbaglia. Da decidere;
* ⚠️ la stessa frase della guida e' falsa anche per `clienti` (oggi unico per istanza, con R-8
  per BA).

Proposta del team DB — **D-9**: invece di una «sorgente del ruolo» polimorfa (tipo + id, che una
FK non sa verificare e che per i ruoli non-cliente ripeterebbe il `soggetto_ruolo_id`), la pratica
porta **`billing_account_id`** nullable al posto di `utility_id`:

* e' l'aggancio a grana fine del cliente, tipizzato: una FK lo verifica;
* istanza e utility ne discendono: FK composta `(billing_account_id, istanza_utility_id)` verso
  il BA (l'indice unico esiste gia'), e il guard che il ruolo del BA sia il `soggetto_ruolo_id`
  della pratica;
* il backend lo legge dalla colonna: il resolver `fn_get_billing_account_by_istanza` non serve
  piu' alla pratica (D-8 si allarga a lui, se non ha altri consumatori);
* chi crea la pratica da un documento (la sorgente) passa il BA del documento;
* NULL per le pratiche di fornitori e altri ruoli, e per quelle che nascono prima dell'istanza
  (allaccio da pratica). Se un giorno un altro ruolo diventa a grana fine, prende la sua colonna
  tipizzata.

#### 6.11.8 Risposte di Tid (2026-10-08)

* **D-9 accettata:** la pratica porta `billing_account_id` nullable al posto di `utility_id`. La
  forma del §6.11.6 cambia nei punti a-c: colonna `billing_account_id` (FK composta
  `(billing_account_id, istanza_utility_id)` verso il BA, guard «il ruolo del BA e' il
  `soggetto_ruolo_id` della pratica»), i creatori passano il BA della sorgente, il backend legge la
  colonna. `script.fn_get_billing_account_by_istanza` perde il consumatore della pratica: se non
  ne restano altri si ritira con D-8.
* **R-9 — `gestori`: `UNIQUE (soggetto_ruolo_id)`**, come le altre specializzazioni. Fatto datato
  (dbdev, 2026-10-08): nessun ruolo con piu' di un gestore; il changeSet porta comunque la sua
  preCondition.
* **La frase della guida «Soggetti & Ruoli»** («tutte le tabelle specializzate … UNIQUE: un solo
  record specializzato per ruolo») si corregge: vale per tutte **tranne `clienti`**, che e' per
  costruzione a grana fine — un ruolo CLIENTE ha un cliente per ogni BA (R-8). Su `clienti` non
  c'e' e non ci deve essere un `UNIQUE (soggetto_ruolo_id)`.
* **Guida «Soggetti & Ruoli» corretta il 2026-10-08**: «un solo record specializzato per ruolo»
  vale per tutti tranne il CLIENTE (un cliente per BA); per i gestori il vincolo arriva con R-9.

### 6.12 Consegna DB di R-8 e R-9 (2026-10-08) — applicata

#### 6.12.1 ChangeSet

| # | File | Cosa |
| --- | --- | --- |
| -63 | `00_schema/pratiche/…-add-pratiche-billing-account` | `pratiche.billing_account_id` nullable; CHECK «solo con l'istanza»; FK composta `(billing_account_id, istanza_utility_id)` verso il BA. Le pratiche gia' scritte si valorizzano solo dove l'istanza ha UN BA ed e' del ruolo della pratica |
| -64 | `00_schema/anagrafiche/…-alter-clienti-uno-per-billing-account` | `uq_clienti_billing_account` al posto di `uq_clienti_istanza_utility` (preCondition: nessun BA con due clienti) |
| -65 | `00_schema/anagrafiche/…-add-uq-gestori-soggetto-ruolo` | R-9: `uq_gestori_soggetto_ruolo` |
| -66 | `20_code/pratiche/…-update-trgfn-pratiche-guard-contesto-ba` | regola 5 del guard di contesto: il BA e' del ruolo della pratica (`E_PRATICHE_BA_NON_COERENTE`); il trigger scatta anche su `billing_account_id` |
| -67 | `20_code/pratiche/…-update-fn-crea-pratica-billing-account` | `p_billing_account_id` in coda (firma vecchia tolta: niente overload) |
| -68 | `20_code/vendite/…-update-fn-genera-pratica-da-preventivo-billing-account` | la pratica nasce col BA del preventivo (la sorgente); via il ramo «preventivo senza BA» |
| -69 | `20_code/pratiche/…-update-fn-genera-pratica-da-flusso-billing-account` | la figlia copia il BA dalla madre |
| -70 | `20_code/vendite/…-update-fn-resolve-termini-pagamento-cliente-per-ba` | livello 3: il cliente si aggancia per BA, non per istanza |
| -71 | `20_code/script/…-update-fn-get-billing-account-by-istanza-solo-se-univoco` | il BA dell'istanza solo se e' uno (letto da `billing_account`); **in ritiro** |
| -72 | `20_code/script/…-drop-view-clienti-istanza-states` | D-8: ritirate vista e `fn_get_stato_cliente_by_istanza` |
| -73 | `80_data/changelog/…-upsert-fk-index-policy-istanza-nasce-col-ba` | CSV dedicato della policy indici FK: indice sulla FK clienti → istanze (persa la copertura del vincolo vecchio), indice parziale sulla FK pratica → BA, indice dedicato dei gestori sul ruolo a `false` (lo copre il UNIQUE) |

Registri: `E_PRATICHE_BA_NON_COERENTE` (1227, `DATO_ERRATO`, campo `billing_account_id`). Le
funzioni lunghe (-66, -69, -70) partono dal corpo **vivo** del DB (`pg_get_functiondef`,
verificato che l'ultimo changeSet di ciascuna fosse applicato), con le sole modifiche dichiarate e
la firma ancorata dove l'originale l'aveva.

#### 6.12.2 Come e' stato provato

SQL estratto da `-50…-72`, come owner, in transazioni annullate; preCondition `-64` e `-65` a zero
su dbdev; `plpgsql_check` sulle sei funzioni cambiate: nessuna segnalazione nuova (due avvisi
STABLE/VOLATILE su `fn_resolve_termini_pagamento`, righe 33 e 55, **gia' presenti** sulla funzione
viva); le righe della policy passano `chk_fk_index_policy_dll_command_forma`.

pgTAP — 71 file (i 62 che nominano gli oggetti toccati, piu' quelli del primo giro), corpo
concatenato all'SQL estratto: **69 verdi**. I due rossi sono **preesistenti**, identici sugli
originali: `rls/test-rls-billing-account-returning-secondo-emittente` test 6 (l'owner salta la
RLS) e `anagrafiche/test-indirizzi-fallback` test 8 e 10 (tipo di ritorno di
`vw_indirizzi_resolved_soggetto`, fuori da questo brief).

| File | Che cosa e' cambiato |
| --- | --- |
| `anagrafiche/test-un-ba-un-cliente-v1.sql` (**nuovo**, 13/13) | R-8 e R-9: due clienti sulla stessa istanza su due BA (su due utility senza PDP del catalogo); secondo cliente sullo stesso BA rifiutato; pratica col BA del preventivo; regola 5, CHECK, FK composta della pratica; resolver per istanza; ritiri D-8; vincolo dei gestori; forma del join dei termini |
| `script/test-fn-get-billing-account-by-istanza.sql` | test 7: istanza senza cliente → il suo BA se e' uno (il «prospect senza BA» non esiste piu') |
| `pratiche/test-guida-avanza-esito-proiettato.sql`, `pratiche/test-reconcile-tie-break-flusso-origine.sql`, `rls/test-rls-preventivi-satelliti.sql` | ⚠️ **buco del censimento del primo giro**, trovato qui: creavano preventivi senza BA (il grep di allora non li vedeva). Ora il cliente e' costruito col BA legato all'emittente del preventivo |

⚠️ Non provato da un pgTAP: la copia del BA nella pratica generata da un flusso (-69) — serve un
flusso completato con una regola di generazione. Provato solo da `plpgsql_check`.

#### 6.12.3 Debiti e osservazioni

* `script.fn_get_billing_account_by_istanza` e' **in ritiro**: resta finche' il backend la chiama
  (dettaglio pratica), poi si cancella con la sua pagina `manual/`. ➡️ Ritiro scritto il 2026-10-10
  in `brief-db-istanza-nasce-col-ba-residui` (R-4); li' anche `uq_gestori_singleton` (D-3).
* `uq_gestori_singleton`, nonostante il nome, e' un indice **GiST non unico** su `id`: non vincola
  niente. Fuori da questo brief: o va ritirato, o doveva essere un vincolo (un solo gestore nel
  sistema?). Da decidere.

#### 6.12.4 Al BE/FE (aggiunge al §5 e al §6.10.5)

* **Dettaglio pratica** (`pratiche_repository`, due punti): leggere `p.billing_account_id` al posto
  di `script.fn_get_billing_account_by_istanza(p.istanza_utility_id)`. Il «prospect» (BA NULL perche'
  manca il cliente) non esiste piu': il BA NULL ora significa pratica di un altro ruolo o senza
  istanza.
* **Creazione della pratica** (`create_pratica` e il suo form): passare `billing_account_id` quando la
  pratica parla di un cliente; nuovo codice `E_PRATICHE_BA_NON_COERENTE` (policy e frase).
* **Clienti**: il nome del vincolo cambia (`uq_clienti_billing_account`): la frase mappata in
  `clienti_service` diventa «Esiste gia' un cliente per questo billing account». Un'istanza ora
  ammette piu' clienti: le schermate che danno per scontato «il cliente dell'istanza» vanno
  riviste.

### 6.13 La RLS dei dati precontrattuali (2026-10-08) — applicata

**Il trovato.** Dopo l'apply del giro `-50…-73`, la corsa di Tid ha dato rosso
`rls/test-rls-perimetro-scoperto` test 2: `NON_DICHIARATO FIGLIA_DI_TABELLA_PROTETTA
anagrafiche.istanze_dati_precontrattuali`. La FK `fk_idp_billing_account_coppia` (-51) l'aveva resa
figlia del BA, che ha la RLS per azienda, e il presidio chiede una decisione.

**Decisione di Tid: opzione A, la RLS segue il BA della coppia** (l'alternativa era una riga nel
registro `rls_perimetro_debito`). I dati precontrattuali sono di un cliente di un'azienda.

| # | File | Cosa |
| --- | --- | --- |
| -74 | `20_code/script/…-create-fn-scope-ef-whitelist-via-coppia` | scope «vedo la riga se vedo il BA della sua coppia», delega a `fn_scope_ef_whitelist_via_efba`; BA invisibile o assente: false |
| -75 | `00_schema/anagrafiche/…-create-policy-istanze-dati-precontrattuali` | `rls_istanze_dati_precontrattuali_ef_whitelist`, veste OPERATORE, FOR ALL con WITH CHECK, come i satelliti delle testate. Inerte |
| -76 | `00_schema/anagrafiche/…-arm-rls-istanze-dati-precontrattuali` | `ENABLE ROW LEVEL SECURITY` (niente FORCE) e `vw_istanze_dati_precontrattuali_dettaglio` resa `security_invoker`: non lo era, e con la RLS accesa sarebbe stata una porta laterale (nessun consumatore oggi) |

`istanze_utilities` resta senza RLS: l'istanza e' il luogo, i dati precontrattuali sono del cliente.

**Prove** (SQL estratto di `-74…-76` sul DB vivo, transazioni annullate):

* `rls/test-rls-istanze-dati-precontrattuali-v1.sql` (**nuovo**, 8/8): struttura (policy, RLS
  accesa, vista invoker), l'operatore A vede i suoi e non quelli di B, non scrive sulla coppia di
  un cliente di B, senza veste niente, e il presidio non elenca piu' la tabella;
* `rls/test-rls-perimetro-scoperto` 8/8;
* 64 pgTAP che toccano la tabella o creano contratti e offerte: 62 verdi. Restano rossi
  `anagrafiche/test-istanze-dati-precontrattuali` (la pulizia iniziale tocca righe di dbdev gia'
  fotografate in un contratto) e — fino alla correzione sotto — tre file dei contratti.

**⚠️ Tre fixture dei contratti, trovate qui** (il censimento di R-2 aveva guardato i preventivi,
non i contratti). Erano gia' nel registro dei rossi di CI (`baseline-rossi-ci.tsv`):

| File | Che cosa era | Ora |
| --- | --- | --- |
| `vendite/test-fn-create-contratto-v1.sql` | dal 2026-07-27 (42/42 BA con dati precontrattuali) sceglieva una utility «libera» **diversa** da quella del BA: un contratto col BA di un'altra coppia, che `fk_contratti_ba_coppia` ora rifiuta | cliente costruito, verde |
| `vendite/test-fatture-atti-v1.sql` | idem per i due contratti della fixture | cliente costruito, verde |
| `vendite/test-contratti-utilities-snapshot.sql` | pescava un BA senza dati precontrattuali: non ce n'e' piu' nessuno su dbdev | cliente costruito sulla utility della classe d'utenza scelta, 12/12 |

⚠️ I tre file, verdi, restano elencati in `baseline-rossi-ci.tsv`: il registro si riallinea alla
prossima corsa di riferimento.

### 6.14 Esito dell'apply (2026-10-08)

Tid ha applicato l'intero giro `20261008-50…-76` e lanciato i pgTAP: **nessuna regressione**
(dopo la correzione del §6.13, il presidio `rls/test-rls-perimetro-scoperto` e' verde).

Restano aperti, e non sono del lato DB:

* il lato **BE/FE**: §5, §6.10.5 e §6.12.4 (codici nuovi da mappare, FK nuove da tradurre, dettaglio e
  creazione della pratica sul `billing_account_id`, piu' clienti per istanza, commenti sul
  «prospect»);
* `baseline-rossi-ci.tsv` elenca ancora come rossi `test-fn-create-contratto-v1`,
  `test-fatture-atti-v1` e `test-contratti-utilities-snapshot`, ora verdi: si riallinea alla
  prossima corsa di riferimento.

Debiti dichiarati, da portare in brief propri all'archiviazione (§6.9, §6.10.3, §6.12.3): il BA di un
documento chiuso si riscrive; il ramo morto `PREVENTIVO_SENZA_BILLING_ACCOUNT` nelle capability del
preventivo; `fn_get_billing_account_by_istanza` in ritiro (quando il BE legge la colonna della
pratica); `uq_gestori_singleton` che non vincola niente; la copia del BA nella pratica da flusso e lo
spostamento del gestore globale senza un pgTAP.

## 7. Consegna BE/FE (2026-10-08, `dev/backend-tid`)

### 7.1 La decisione presa nel giro — D-10 (Tid, 2026-10-08)

**La pratica sceglie la fornitura, cioe' il BA.** Il lookup istanze
(`/anagrafiche/istanze-utility/lookup/`) da' **una riga per billing account**, cioe' per coppia
(istanza, utility), e il drawer della pratica manda il `billing_account_id` della riga; l'istanza la
ricava il backend dal BA. Ruolo e forniture si legano dal BA (`ba.soggetto_ruolo_id`), non da
`clienti`. Le alternative scartate: istanza + scelta della utility nel form (un campo in piu', e la
riga del lookup avrebbe continuato a mostrare un BA solo), o solo BE col FE in un giro a se'.

### 7.2 Che cosa e' cambiato

| Richiesta | Dove | Che cosa |
| --- | --- | --- |
| §6.10.5 codici | `error_policies_generated.py` (rigenerato), `error_messages_fallback.py` | `E_ISTANZA_SENZA_BA`, `E_ISTANZA_EMITTENTI_DIVERSI`, `E_BA_ISTANZA_IMMUTABILE`, `E_PRATICHE_BA_NON_COERENTE` con la frase di ripiego; `E_ISTANZA_UTILITY_SENZA_UTILITY` ritirato (resta, come ogni codice ritirato, per leggere `dbops.error_log`) |
| §6.10.5 FK | `offerte_service`, `contratti_service` | `fk_offerte_commerciali_ba_coppia`, `fk_contratti_ba_coppia` → `E_VENDITE_FK` sul campo `billing_account_id` |
| R-2 preventivo | `preventivi_service._risolvi_cliente_preventivo` | il cliente e' la coppia col suo BA, letto dal lato che il payload porta: col BA l'istanza e' la sua, con la sola istanza il BA della coppia (`BillingAccountRepository.get_id_by_coppia`, una chiave, non una scelta). Vale in creazione **e** in modifica. `fk_preventivi_ba_coppia` → `E_VENDITE_FK`. Il wrapper `check_utility_istanza_coerenza` e' ritirato (nessun chiamante) |
| §6.12.4 pratica | `pratiche_repository`, `pratiche_service.crea_pratica`, view, approvazioni prezzo | dettaglio e flussi leggono `p.billing_account_id` (zero consumatori di `script.fn_get_billing_account_by_istanza`); la creazione accetta `billing_account_id` (col solo BA l'istanza e' la sua; BA e istanza discordi → `E_PRATICA_VALIDATION` sul campo); la pratica di approvazione prezzo nasce col BA del documento |
| D-10 lookup | `istanze_utility_repository`, `soggetti_repository` | una riga per BA; il restore per id resta l'istanza, coi campi del BA solo se e' uno; il lookup soggetto+ruolo conta i BA del ruolo (`n_billing_account`, `billing_account_unico_id/_codice` al posto di `n_istanze`, `istanza_unica_*`) |
| §6.12.4 clienti | `clienti_service` | `uq_clienti_billing_account` → «Esiste gia' un cliente per questo billing account» |
| §5 FE | `IstanzaUtilityLookup`, `SoggettoRuoloLookup`, `PraticaDrawer`, `PreventiviDrawer`/`Form` | via il badge «Solo istanza» e la chiave; il drawer della pratica sceglie la «Fornitura»; via il restore del preventivo «prospect senza BA»; commenti riscritti sulla regola |

### 7.3 Trovato nel giro, corretto

**Creare un cliente su un'istanza esistente era un 500.** `ClientiRepository.get_istanza` chiedeva
`istanze_utilities.utility_id`, che non esiste, e il service confrontava la utility dell'istanza.
I test mockavano il repository con quella colonna: verdi per costruzione. Ora la utility si
controlla sul BA indicato (la coppia e' la sua identita'), e su un'istanza la cui utility ha gia' il
BA la creazione risponde `E_ANAG_DUPLICATO` (`uq_billing_instance_utility`) invece di un 500. E' la
strada che R-8 apre: un secondo cliente sulla stessa istanza.

**Prove:** suite BE intera verde (5996); sul DB vero (opt-in E2E) i nuovi
`anagrafiche/tests/db/test_lookup_forniture_per_ba_db.py` (4: un'istanza con due utility da' due
righe, il filtro utility tiene la coppia, il ruolo conta i suoi BA, il restore non sceglie fra due
BA), `pratiche/tests/db/test_pratica_billing_account_db.py` (2) e
`anagrafiche/tests/db/test_clienti_repository_db.py` (2); FE: eslint, guard e vitest verdi.

### 7.4 Collaudo a video (Tid)

* ⏭️ Pratica nuova su un cliente con un BA solo: «Fornitura … derivata»; con piu' BA (anche
  un'istanza con due utility): la tendina mostra una riga per fornitura, con la utility nel testo.
* ⏭️ Pratica su un soggetto senza ruoli o con un ruolo non cliente: nessun campo fornitura.
* ✅ Preventivo nuovo scegliendo l'istanza invece del BA: al salvataggio il BA compare, bloccato.
* ⏭️ Dal flusso di una pratica col BA: offerta e contratto si aprono col cliente ereditato.

✅ Superato il 2026-10-10 il punto del preventivo. ⏭️ I tre punti sulle pratiche sono rimandati
(Tid, 2026-10-10): il cantiere pratiche è fermo e sarà ripreso per intero. Si rifanno alla sua
ripresa; il promemoria sta in PROJECT_CONTEXT § «Aperto — Media priorità».

### 7.5 Debiti e segnalazioni, aperti

> **Aggiornamento 2026-10-10, all'archiviazione:** il primo punto è preso in carico da
> [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md). Il secondo
> e il terzo sono ancora aperti e passano in PROJECT_CONTEXT § «Aperto — Media priorità». Il
> quarto è chiuso: `test_resi_create_db` è verde sul DB di sviluppo (con `ZEROERP_TEST_DB_E2E=1`).

* **Ordini e DDT hanno ancora `billing_account_id` nullable**, senza FK di coppia: e' la stessa
  asimmetria che R-2 ha chiuso su preventivo, offerta e contratto (il BE ha ancora i commenti
  «ordine prospect con BA NULL», `ordini_repository`, `_indirizzi_repo_mixin`, `ddt_repository`,
  `ordine_document_context_builder`). → Brief aperto il 2026-10-09 su richiesta di Tid:
  [brief-db-esecutivi-ba-coppia.md](brief-db-esecutivi-ba-coppia.md) (D21 del registro DB).
* `script.fn_get_billing_account_by_istanza` non ha piu' consumatori nel BE: il team DB puo'
  ritirarla (§6.12.3).
* Il ramo morto `PREVENTIVO_SENZA_BILLING_ACCOUNT`: la chiave
  `vendite.preventivi.push_commessa_reason.senza_billing_account` esce dai locales quando il DB
  ritira il ramo (§6.10.3).
* ⚠️ Fuori da questo brief: su dbdev `vendite/tests/db/test_resi_create_db` e' rosso perche' la
  sua fixture aggiunge righe a un ordine CONFERMATO, che il lock di D-1 di
  `brief-db-righe-e-componenti-debiti-residui` ora rifiuta. Quel giro e' **applicato su dbdev ma
  non ancora pushato** (2026-10-08); il test va rivisto con quel giro.
### 6.15 Trovato dopo il merge (2026-10-09): lo scope di storico dei dati precontrattuali

Il runner di Tid ha dato due rossi fuori dai pgTAP del giro, tutti e due conseguenza del giro:

* **`dbops/test-security-definer-search-path-v1` test 4** (20 contro la soglia 17, «può solo
  calare»): le tre DEFINER nuove `fn_guard_istanza_ha_ba` (`-55`), `fn_guard_istanza_ba_emittente`
  (`-59`) e `fn_guard_istanza_ba_gestore_globale` (`-60`) erano nate col `search_path` senza `pg_temp`,
  per copia dalle gemelle del gestore globale. Sanate da **`20261008-95`** (`ALTER FUNCTION … SET
  search_path`, corpo invariato, forma del `20261005-27`).
* **`dbops/test-storico-scope-policy-v1` test 4 e 29**: la RLS accesa su
  `anagrafiche.istanze_dati_precontrattuali` (§6.13) ha reso «protetta» una madre che la mappa dello
  storico dichiarava `NESSUNO` — la sua ragione diceva proprio «quando entrerà in RLS il presidio
  segnalerà questa riga». Nessun modo sapeva dirla: la policy la vede attraverso il BA della COPPIA
  (istanza, utility), una chiave composta, e i modi leggevano una colonna sola.
  ✅ **Decisione di Tid (2026-10-09): un modo nuovo, `COPPIA`** — `colonna` dichiara i due nomi,
  il resolver trova il BA della coppia e ne prende l'emittente come nel modo `BA`, la strada della
  policy `via_coppia`. ChangeSet **`20261009-01`** (i due CHECK della mappa), **`20261009-02`** (il
  ramo nel resolver), la riga 19 del CSV della mappa (`80_data`, da `NESSUNO` a `COPPIA`). Il nome è
  senza trattino basso: il test 10 del presidio legge i modi dal CHECK con `'([A-Z]+)'`.
  pgTAP: `test-storico-scope-policy-v1` +3 (6-bis coerenza della FK composta col catalogo, 28-ter e
  28-quater il resolver sui valori, con un mondo costruito), test 9 conta `COPPIA` fra i terminali.
  Prova (dev, owner, transazione annullata, seed simulato con un UPDATE: il loader vero lo prova il
  migrate): 36/36, `plpgsql_check` a zero, la shadow `storico.istanze_dati_precontrattuali` armata
  dalla convergenza di `90_end`; mutazione senza il ramo: rosso il test 10 e il file si ferma al 28-ter.
  ⚠️ Le versioni già archiviate della madre hanno `origine_schema` valorizzata e scope `NULL`: il
  backfill non le riprende e, con la shadow armata, restano invisibili. È il fail-closed del modello
  («versione precedente non attribuibile»), dichiarato.
  ✅ **Applicato il 2026-10-09** (`20261008-95` alle 00:01, `20261009-01`/`-02` alle 00:08), pgTAP
  verdi col runner di Tid.

