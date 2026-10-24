# Brief DB — Un prezzo non autorizzato non esce dalla bozza: una sede sola, a DB

> **Destinatari:** team DB (`dev/db-tid`); richieste al BE/FE in §6.
>
> **Tipo:** brief di dominio, nato dal §5 di
> [brief-be-fe-capability-annidata.md](brief-be-fe-capability-annidata.md)
> («il predicato duplicato di preventivi, brief DB suo»).
>
> **Stato (2026-09-24):** ✅ **CHIUSO**, archiviato in `work-done/`.
> * ✅ **DB chiuso, due giri applicati, pgTAP verdi** (Tid: «migrazione
>   applicata test verdi»). Giro 1: tredici changeSet `20260924-20…-32`, §8 — la
>   regola nei cinque documenti di vendita. Giro 2: cinque changeSet
>   `20260924-33…-37`, §10 — nessuna revisione con un prezzo in attesa.
> * ✅ **BE + FE del §6 consegnati e committati** (dettaglio §6, storia §11):
>   * **BE** — il blob del preventivo arriva **intatto**: tolti la riscrittura
>     Python e i quattro riepiloghi `frozen_for_*` / `*_pricing_count`; codici
>     rigenerati, ripiego allineato (anche ai messaggi generici del giro 2),
>     doc API corretta;
>   * **FE** — il perché di un pulsante spento sta **solo nel tooltip**, uguale
>     per i cinque documenti e per ogni motivo, **col numero**
>     (*«Ci sono prezzi in attesa di approvazione (2).»*): banner del preventivo
>     ritirato invece che copiato sugli altri quattro (decisione di Tid), i
>     `valori` del motivo passano alla frase, la resa dei motivi ha una sede
>     sola (`testoMotivi`, regola del 2, ok Tid). Il giro 2 non chiede niente
>     al FE: «Crea revisione» arriva da `available_actions` e passa dallo
>     stesso tooltip.
>
> ⏳ **Fuori dal brief, con una sede loro:**
> 1. il **collaudo a video** (§6.3, anche le revisioni) →
>    [collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md](collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md) §2;
> 2. la riga di `test-preventivi-approvazione-prezzo.sql` in
>    `baseline-rossi-ci.tsv` (`ERRORE_FIXTURE`), da togliere con
>    `scripts/pgtap-baseline-ci-rientrati.sh` dopo la corsa CI su `Tito-dev`
>    (team DB; lo ricorda anche il copione, §3).
>
> 🔢 **Progressivi riservati: `20260924-20` … `-39`.** `-01…-19` restano al
> §13 di [brief-db-guard-date-validita.md](brief-db-guard-date-validita.md)
> (due copie da ritirare, ancora da numerare). Il numero si riverifica con
> `find` prima di salvare ogni file.
>
> **In una riga:** un prezzo in attesa di approvazione o rifiutato dal
> responsabile non lascia uscire il documento dalla bozza e non lo lascia
> accettare — preventivi, contratti, offerte, ordini e DDT — e la regola sta in
> **un** building block, `script.fn_check_prezzi_autorizzati`, letto dai guard
> e dai pulsanti. Prima era scritta in cinque sedi che non dicevano la stessa
> cosa, più una sesta nel backend.

---

## 1. Il problema, in parole semplici

Una riga di preventivo con un prezzo fuori listino chiede un'approvazione: la
riga diventa `PENDING`. Il responsabile approva (`APPROVED`) o rifiuta
(`REJECTED`). Un prezzo rifiutato non vale: l'operatore lo corregge o toglie
la riga, e correggendolo lo stato torna vuoto.

Finché un prezzo è in attesa o rifiutato, **nessuno lo ha autorizzato**. Il
preventivo non deve arrivare al cliente, né diventare un impegno accettato.

Oggi questa regola sta in due sedi:

* il **database** — `vendite.trgfn_preventivi_guard_transizione_approvazione`
  (trigger `trg_preventivi_a10_guard_transizione_approvazione_upd`) e
  `script.trgfn_righe_guard_pending`;
* il **backend** — `preventivi_service.get_preventivo`, che riscrive
  `available_actions`, `can_edit_testata` e `can_edit_righe` dentro il blob
  (🔴 DEBITO DICHIARATO nel codice).

## 2. Le due sedi dissentono

Il confronto è fatto sul **corpo** delle funzioni (doc auto-gen) e del service,
al 2026-09-24:

| Caso | Database | Backend (`get_preventivo`) |
| --- | --- | --- |
| Riga `PENDING` | blocca **solo** → `ACCETTATO` | spegne **tutte** le azioni, anche Annulla ed Emetti |
| Riga `REJECTED` | **nessuna regola** | spegne tutte le azioni e la modifica della testata |
| Componente BoM `PENDING` | conta (Check 2) | **non conta**: Accetta resta acceso, poi il trigger lo rifiuta |
| Componente BoM `REJECTED` | nessuna regola | non conta |
| Testata e altre righe con una riga `PENDING` | modificabili (blocca la sola riga `PENDING`) | spente |

⛔ Nessuna delle due è «la regola»: il database è stretto dove il backend è
largo e viceversa. Il backend **non replica** il trigger, come dice il suo
commento («defense-in-depth replica trgfn DB»): ne scrive un altro.

⚠️ E una parte — il `REJECTED` — **esiste solo a video**: una chiamata API
diretta, l'assistente AI, un import o una schermata futura emettono un
preventivo con dentro un prezzo rifiutato, e il database lo accetta.

## 3. Le decisioni (Tid, 2026-09-24)

| | Decisione |
| --- | --- |
| **D-1** | Il `REJECTED` è una **regola di dominio**, non un promemoria: un preventivo con un prezzo rifiutato non si emette e non si accetta, **da nessuna strada**. Va a DB. *Motivo:* un prezzo rifiutato e uno in attesa sono entrambi prezzi che nessuno ha autorizzato; bloccarne uno e lasciar passare l'altro non ha senso |
| **D-2** | Un prezzo `PENDING` blocca → `EMESSO` **e** → `ACCETTATO`. **Annulla resta sempre acceso**: è la via d'uscita dell'operatore (brief vie-d'uscita, R1) |
| **D-3** | Il blocco resta sulla **sola riga** `PENDING` (`trgfn_righe_guard_pending`, invariato): la testata e le altre righe restano modificabili in `DRAFT` come dice la capability del database |
| **D-4** | Contratti e offerte nello stesso cantiere (§7) |
| **D-5** | **Un building block solo** per i cinque documenti: il predicato in un posto, la politica (verso quale stato, e se il documento la chiede) nel documento (§7-bis) |
| **D-6** | Anche **ordini e DDT**, nello stesso giro (§7-bis) |

Ne segue la regola, scritta una volta:

> Un preventivo con **almeno un prezzo non autorizzato** — riga o componente
> BoM in `PENDING` o `REJECTED` — non può andare verso `EMESSO` né verso
> `ACCETTATO`. Nient'altro si spegne.

## 4. La forma (com'è stata costruita)

> ⚠️ Questa sezione descrive **ciò che è stato scritto** (§8). La prima stesura
> parlava di una `fn_check_preventivo_prezzi_autorizzati` del solo preventivo:
> il censimento del §7-bis e D-5/D-6 l'hanno fatta diventare un building block.

### 4.1 Il building block

`script.fn_check_prezzi_autorizzati(p_testata regclass, p_documento_id bigint)
RETURNS jsonb` — `STABLE`, `SECURITY INVOKER`, non solleva sul contenuto, non
scrive. `[]` oppure un array **ordinato** di motivi nella forma di casa
`{codice, reason, reason_key, dettaglio, valori}`: prima l'in attesa, poi il
rifiutato.

* **Il documento si indica con la tabella di testata** (`regclass`):
  `vendite.preventivi`, `vendite.contratti`, `vendite.offerte_commerciali` (le
  righe con prezzo sono le eccezioni), `vendite.ordini` e `vendite.ddt` (solo i
  componenti portano lo stato). Un nome sbagliato fallisce alla conversione;
  una testata non gestita solleva `E_PARAMETRO_INVALIDO` — un `[]` farebbe
  passare tutto in silenzio. ⚠️ `config.tipi_entita` non si usa: non ha offerte
  né DDT.
* **Solo righe e componenti ATTIVI.** Le righe si cancellano, i componenti si
  spengono: un componente rifiutato e poi tolto resta `REJECTED` per sempre, e
  contarlo bloccherebbe il documento senza rimedio. ⚠️ Il trigger a10 contava
  anche le righe disattivate: differenza voluta.
* **Nella frase il conteggio** (`valori`), nel `dettaglio` `n_prezzi` e la prima
  riga/componente a video. Le tabelle non hanno tutte un numero di riga.
* **Codici e `reason_key` letterali**, un motivo per blocco, non in un `CASE`:
  `dbops.vw_funzioni_check_codici` e `scripts/check_i18n_keys.py` li
  riconoscono solo nella forma `'codice', 'E_…'` / `'reason_key', '…'`.
* Tipi della firma **espliciti, con il motivo scritto**: l'id è la chiave di
  cinque tabelle diverse, la testata non è una colonna, l'array dell'enum non si
  scrive con `%TYPE[]`.

### 4.2 La politica, documento per documento

| Documento | Quando lo chiede | Dove | Pulsante spento |
| --- | --- | --- | --- |
| Preventivo | verso `EMESSO` | dentro `fn_check_preventivo_emettibile` (motivo 2, dopo l'aliquota) → Regola 2 del guard | «Emetti» (già legge la check) |
| Preventivo | verso `ACCETTATO` | Regola 3 di `trgfn_preventivi_guard_transizione` | «Accetta» |
| Contratto | verso `ATTIVO` | `trgfn_contratti_guard_transizione_stato` (sostituisce il controllo sui soli componenti) | «Attiva» |
| Offerta | verso `EMESSA` e `ACCETTATA`, **non** sul rientro da `SUPERATA` | `trgfn_offerte_commerciali_guard_transizione` | «Emetti» (dopo il motivo del listino), «Accetta» |
| Ordine | **solo `DRAFT → CONFERMATO`** | Regola 5 di `trgfn_ordini_guard_transizione` — ⛔ non in `fn_check_ordine_confermabile` | «Conferma», solo dalla bozza |
| DDT | verso `EMESSO`, **solo se la causale vende** | punto 5 di `fn_check_ddt_emittibile` → `trgfn_ddt_guard_transizione_approvazione` | «Emetti» (già legge la check) |

⛔ **I rientri automatici non si bloccano.** La matrice fa rientrare l'ordine in
`CONFERMATO` da `EVASO`/`PARZIALMENTE_EVASO` quando l'evasione torna indietro,
e l'offerta in `EMESSA` da `SUPERATA` quando si annulla la sua revisione. Quei
rientri non mandano niente al cliente e non confermano niente di nuovo: un
prezzo rimasto non autorizzato li fermerebbe, e con loro l'**annullamento** che
li provoca — cioè una via d'uscita (D-2). Per l'ordine è la ragione per cui la
regola non sta in `fn_check_ordine_confermabile` (che vale per ogni ingresso in
`CONFERMATO`, perché l'aliquota protegge un riepilogo che non sa da dove si
arriva). Per l'offerta si legge il flag `is_superato`, non un codice.

⭐ Contratto e offerta avevano funzioni dei pulsanti nella forma vecchia (un
motivo solo): passano alla forma dell'**array dei motivi** (linee-guida-sql
§12.2), come preventivo e ordine, con la chiave `reasons` sulle azioni. Nessuna
chiave tolta.

### 4.3 La copia che si ritira, nello stesso giro

Il trigger a10 `trg_preventivi_a10_guard_transizione_approvazione_upd` e la sua
funzione: `DROP` in `20260924-24`, pagina `manual/` cancellata, la sua storia
spostata nella pagina di `trgfn_preventivi_guard_transizione`. Il controllo sui
soli componenti del contratto e il punto 5 del DDT sono sostituiti nel corpo
delle loro funzioni. Nessun changeSet di `80_data` o `90_end` nominava il
trigger (censimento prima del `DROP`).

## 5. Codici e chiavi

| Codice | Stato | Note |
| --- | --- | --- |
| `E_DOC_PREZZO_PENDENTE` | 🆕 `CONFLITTO_STATO`, messaggio id 1119 | «Non si può procedere: ci sono prezzi ancora in attesa di approvazione (%s).» |
| `E_DOC_PREZZO_RIFIUTATO` | 🆕 `CONFLITTO_STATO`, messaggio id 1120 | «Non si può procedere: ci sono prezzi rifiutati dal responsabile (%s).» |
| `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` | ⛔ **ritirato**, `obsoleto_dal` 2026-09-24 | lo sollevava solo il trigger a10; la riga resta per `dbops.error_log` |
| `E_COMPONENTE_PREZZO_PENDENTE` | vivo, nota riscritta | resta il codice del guard **per riga** dei componenti; non è più il codice del blocco di emissione (DDT) o di attivazione (contratto) |

`reason_key` nuove, nel namespace trasversale (linee-guida-sql §12.3):
`common.azione_reason.prezzo_pendente`, `common.azione_reason.prezzo_rifiutato`.
⚠️ La `reason_key` `vendite.ddt.azione_reason.componenti_prezzo_pendente` non la
emette più nessuno.

## 6. Richieste al BE / FE (dopo l'apply) — ✅ consegnate il 2026-09-24

> Ogni voce porta la richiesta e l'esito. Dove l'esito si discosta dalla
> richiesta c'è il perché; la cronaca sta nel registro (§11).

### 6.1 BE

| Richiesta | Esito |
| --- | --- |
| `preventivi_service.get_preventivo`: togliere la riscrittura di `available_actions` / `can_edit_*` e il 🔴 DEBITO DICHIARATO | ✅ Il blob si consegna com'è |
| I quattro riepiloghi (`frozen_for_*`, `*_pricing_count`) restano sulla testata — «da decidere col BE» se contare anche i componenti attivi | ⭐ **Ritirati**, non estesi. Contare righe **e** componenti attivi in Python sarebbe stata una seconda copia del predicato di `fn_check_prezzi_autorizzati`; il motivo, col conteggio (`dettaglio.n_prezzi`, `valori`), è già nelle `reasons` delle azioni che il prezzo spegne. Il repository conta ora solo le righe attive (`count_righe_attive`, per `righe_count`) |
| Test BE che pinnano il congelamento Python: riscriverli sul comportamento del DB | ✅ Blob intatto: «Emetti» spento col motivo, «Annulla» acceso, testata e righe modificabili in `DRAFT`; nessun riepilogo sulla testata |
| `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` fuori da ripiego e commenti; policy rigenerate | ✅ Rigenerate dal catalogo (DB allineato al CSV committato; il diff porta anche il ritiro di `E_BOM_VALIDO_AL_INVALIDO`, del cantiere date di validità). Ripiego: dentro `E_DOC_PREZZO_PENDENTE` / `_RIFIUTATO` senza `%s` (testo riallineato dopo il giro 2: «Non si può procedere: …»), fuori il ritirato. Commento stantio anche in `ddt_service.cambia_stato` |
| Forma del blob: `reasons` nuove su contratto e offerta | ✅ `guard:capability` verde, nessun intervento |
| Doc BE diventata falsa | ✅ `api_preventivi.md`, `api_approvazioni_prezzo.md`, `api_ordini.md` |

### 6.2 FE

| Richiesta | Esito |
| --- | --- |
| `common.azione_reason.prezzo_pendente` / `prezzo_rifiutato` in it/en (bloccante CI) | ✅ Col conteggio: *«Ci sono prezzi in attesa di approvazione ({0}).»* / *«Ci sono prezzi rifiutati dal responsabile ({0}): correggili o togli le righe.»* |
| Togliere `vendite.ddt.azione_reason.componenti_prezzo_pendente` | ✅ Tolta (la emettevano solo YAML superati) |
| *(non chiesto)* Il banner del `PreventiviDrawer` diceva «transizioni ed edit bloccati», falso dopo D-2/D-3, e leggeva i riepiloghi ritirati | ⭐ **Ritirato, non copiato sugli altri quattro documenti** (decisione di Tid). L'asimmetria vera era fra **motivi**, non fra documenti: «IVA mancante», «senza righe», «listino mancante» bloccano come un prezzo e nessuno ha un banner. Il perché di un pulsante spento ha un canale solo — il tooltip, con **tutti** i motivi — come già deciso nella Decisione D di `work-done/brief-db-ddt-reason-push-catch-all.md`. Il tag di stato sulla riga resta: è dove l'operatore agisce |
| *(conseguenza)* Il numero dei prezzi, che il banner mostrava | ✅ Recuperato **per tutti i motivi**: i `valori` del motivo passano alla traduzione come `{0}` (`labelOrCode` con `params` opzionale). Un testo senza `{0}` non cambia |
| *(regola del 2, ok Tid)* `useLottoAzioni.motiviTesto` era una seconda copia della resa dei motivi, senza `valori` | ✅ Estratta `testoMotivi(t, te, azione)` in `useDrawerActions.js`, usata dal mapper e dal lotto; copia ritirata. Sul lotto, un'azione spenta col solo motivo singolo ora mostra quel motivo invece dell'avviso generico |
| Presidi | `useDrawerActions.spec.js` 11 → 15 test (12 provato rosso per mutazione); catalogo BB FE aggiornato |

### 6.3 Collaudo a video — ➡️ nel copione [collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md](collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md) §2

Per ciascun documento: il pulsante che fa avanzare è **spento** e il tooltip
dice il motivo **col numero**; «Annulla» resta **acceso**; testata e righe non
bloccate restano modificabili in bozza.

- [ ] **Preventivo** in bozza con una riga in attesa → «Emetti» spento; in emesso → «Accetta» spento
- [ ] **Preventivo** con una riga rifiutata e una in attesa → il tooltip porta **due** righe
- [ ] **Contratto** con una riga rifiutata → «Attiva» spento
- [ ] **Offerta** con un'eccezione in attesa → «Emetti» e «Accetta» spenti
- [ ] **Ordine** in bozza con un componente rifiutato → «Conferma» spento
- [ ] **DDT** di vendita con un componente in attesa → «Emetti» spento; con causale che non vende → acceso
- [ ] **Lotto**: un'azione spenta dal kebab di lista mostra il suo motivo
- [ ] **Revisione** (giro 2, §10): preventivo e offerta EMESSI con un prezzo in attesa → «Crea revisione» spento col motivo; con un prezzo solo rifiutato → acceso

⚠️ Sul DB di sviluppo, al 2026-09-24, nessun preventivo in bozza o emesso ha un
prezzo in approvazione: il caso va **costruito** (una richiesta di approvazione
da una riga fuori listino), non cercato.

## 7. Domande aperte

| | Domanda | Raccomandazione |
| --- | --- | --- |
| ✅ **D-4** | Contratti e offerte hanno lo stesso modello di approvazione, e a DB la stessa lacuna: `trgfn_contratti_guard_transizione_stato` blocca `DRAFT → ATTIVO` solo sui **componenti** `PENDING` (non sulle righe, non sul `REJECTED`); sulle offerte nessun guard di transizione sul prezzo è stato trovato. La regola di D-1 («un prezzo non autorizzato non esce») vale anche lì? | **Sì, nello stesso cantiere** ma in un passo a sé dopo i preventivi: il motivo di D-1 non è specifico del preventivo, e PROJECT_CONTEXT chiede di chiudere le asimmetrie **subito**. Prima un censimento (P-0) dei guard di transizione di contratti e offerte e della riga di `offerte_commerciali_eccezioni` |
| | **Decisa da Tid il 2026-09-24: sì, contratti e offerte nello stesso cantiere.** | |

## 7-bis. Il censimento (P-0, 2026-09-24) — e le due domande che apre

Letto sul **corpo** delle funzioni (doc auto-gen), non sui dati.

**Dove vive lo stato di approvazione del prezzo** — otto tabelle, cinque
documenti:

| Documento | Righe | Componenti BoM | Chi lo guarda oggi, e cosa |
| --- | --- | --- | --- |
| Preventivo | `preventivi_righe` | `preventivi_righe_componenti` | trigger `a10`: righe **e** componenti, solo `PENDING`, solo → `ACCETTATO` |
| Contratto | `contratti_righe` | `contratti_righe_componenti` | `trgfn_contratti_guard_transizione_stato`: **solo componenti**, solo `PENDING`, `DRAFT → ATTIVO`. Le righe non contano |
| Offerta | `offerte_commerciali_eccezioni` | `offerte_commerciali_eccezioni_componenti` | **nessuno**: `trgfn_offerte_commerciali_guard_transizione` non guarda il prezzo, `BOZZA → EMESSA` passa con un prezzo in attesa o rifiutato |
| Ordine | — | `ordini_righe_componenti` | nessun guard di transizione trovato; solo il guard per-riga |
| DDT | — | `ddt_righe_componenti` | `fn_check_ddt_emittibile` punto 5: solo componenti `PENDING`, solo se la causale **vende** |

⭐ **Nessuna delle cinque sedi dice la stessa cosa delle altre.** È la forma
classica della divergenza che la regola del 2 esiste per impedire: lo stesso
significato — *«questo documento contiene un prezzo che nessuno ha
autorizzato»* — scritto cinque volte, e ogni copia ne ha tenuto un pezzo
diverso.

Il `REJECTED` non lo guarda **nessuno**, in nessun documento.

✅ **D-5 — un building block solo, o una funzione per documento?** *Decisa da
Tid il 2026-09-24: un building block solo.* La proposta:
un BB in `script` che risponde a una domanda sola — *«quali prezzi non
autorizzati contiene questo documento?»* — e restituisce i motivi nella forma
delle `fn_check_*`. Ogni `fn_check_*` / guard di dominio lo chiama e decide
**quando** chiederlo (lo stato di destinazione, la causale che vende per il
DDT). Il predicato sta in un posto; la politica resta nel dominio. Tocca cinque
domini, quindi vuole l'ok di Tid (AGENTS.md, regola del 2).

✅ **D-6 — ordini e DDT dentro?** *Decisa da Tid il 2026-09-24: sì.* Hanno solo i componenti, ma la ragione di D-1
vale identica. La proposta: sì, nello stesso giro, perché il BB li copre senza
lavoro in più e lasciarli fuori terrebbe viva la copia del DDT accanto al BB
(regola del 2: le copie si ritirano nello stesso giro).

## 8. Cosa è stato scritto

### 8.1 I changeSet (`20260924-20 … -32`, fascia riservata `-20…-39`)

| # | File | Cosa |
| --- | --- | --- |
| -20 | `20_code/script/…-create-fn-check-prezzi-autorizzati` | il building block (§4.1) |
| -21 | `20_code/script/…-update-fn-check-preventivo-emettibile-prezzi-autorizzati` | motivo 2: i prezzi verso `EMESSO` |
| -22 | `20_code/vendite/…-update-trgfn-preventivi-guard-transizione-prezzi-accettato` | Regola 3: verso `ACCETTATO` |
| -23 | `20_code/script/…-update-fn-available-actions-preventivo-prezzi-accettato` | «Accetta» spento col motivo |
| -24 | `20_code/vendite/…-drop-trgfn-preventivi-guard-transizione-approvazione` | ritiro del trigger a10 |
| -25 | `20_code/vendite/…-update-trgfn-contratti-guard-transizione-stato-prezzi` | contratto verso `ATTIVO` |
| -26 | `20_code/script/…-update-fn-available-actions-contratto-prezzi-attivo` | array dei motivi, «Attiva» |
| -27 | `20_code/vendite/…-update-trgfn-offerte-guard-transizione-prezzi` | offerta verso `EMESSA`/`ACCETTATA` |
| -28 | `20_code/script/…-update-fn-available-actions-offerta-prezzi` | array dei motivi, «Emetti»/«Accetta» |
| -29 | `20_code/vendite/…-update-trgfn-ordini-guard-transizione-prezzi` | Regola 5: `DRAFT → CONFERMATO` |
| -30 | `20_code/script/…-update-fn-available-actions-ordine-prezzi-conferma` | «Conferma» dalla bozza |
| -31 | `20_code/script/…-update-fn-check-ddt-emittibile-prezzi-autorizzati` | punto 5 dal building block |
| -32 | `20_code/vendite/…-update-trgfn-ddt-guard-transizione-approvazione-prezzi` | il LOOP solleva i codici nuovi |

⚠️ **Il corpo viene dalla doc auto-gen** (identica al vivo sullo scratch il
24-09, verificato funzione per funzione); **la dichiarazione no**: firme e
`COMMENT ON FUNCTION` ancorati con `%TYPE`, `SECURITY INVOKER` esplicito sulle
funzioni non-trigger — l'auto-gen li perde entrambi (correzione di Tid in
corso d'opera).

### 8.2 Catalogo, pgTAP, documentazione

* `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv`: §5. ⚠️ Gli
  stessi due file hanno modifiche non committate del cantiere delle date di
  validità, su righe diverse.
* 🆕 `db/pgtap/script/test-fn-check-prezzi-autorizzati-v1.sql` — 38 test, il
  mondo si **costruisce** (mondo cliente, un kit con la sua distinta, i
  documenti). Per ogni blocco c'è il suo controllo (il caso pulito passa).
* `db/pgtap/vendite/test-preventivi-approvazione-prezzo.sql` — i test 1, 3 e 10
  fissavano la regola vecchia (il 3 affermava «ad ACCETTATO con riga REJECTED →
  OK», cioè il buco): riscritti. E il fixture ora **costruisce** il mondo invece
  di pescare un billing account e `ART_TEST_BASE`: sullo scratch passa 10/10,
  dove prima moriva nel fixture. ⇒ la sua riga in `baseline-rossi-ci.tsv`
  (`ERRORE_FIXTURE`) andrà tolta dopo la corsa di Tid.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` test 5: da 21 a 23
  (contratti e offerte, siti nuovi dell'helper).
* Doc: `manual/` nuova per il building block; la pagina del trigger a10
  cancellata e la sua storia nella pagina di `trgfn_preventivi_guard_transizione`;
  sezioni «rev 2026-09-24» e riferimenti corretti nelle pagine degli oggetti
  toccati e nelle guide `gestione-preventivi` e `gestione-listini`.

## 9. Le prove (2026-09-24, prima dell'apply)

Tutte sullo scratch `zeroerp_ci`, come owner, in `BEGIN … ROLLBACK`, con l'SQL
**estratto** dagli YAML (niente runner, niente migrate). I due codici nuovi e il
ritiro caricati a mano nella stessa transazione, come farebbe il caricatore del
CSV.

* **Compilazione**: i tredici changeSet in ordine, `plpgsql_check` a zero errori
  sulle dodici funzioni toccate (sette funzioni e cinque trigger con la loro
  tabella).
* **Il pgTAP nuovo: 38/38.**
* **Controprova per mutazione**: con la funzione comune sostituita da uno stub
  che risponde sempre `[]`, diventano rossi tutti i test che affermano la regola
  (1-2, 4-7, 9, 11, 13-14, 17-19, 21-23, 25-29, 32-33, 35, 38) e restano verdi
  solo i controlli. Con il guard dell'ordine allargato a ogni ingresso in
  `CONFERMATO`, diventa rosso **solo** il 31 (il rientro): il test morde sulla
  scelta del §4.2.
* **`test-preventivi-approvazione-prezzo`**: 10/10. **`test-rubinetto-primo-motivo-v1`**:
  7/7. **`dbops/test-riferimenti-morti-v1`**: 9/9.
* **pgTAP esistenti che toccano gli oggetti cambiati**, ciascuno senza e con i
  changeSet: stessi rossi prima e dopo, nessuno nuovo. I rossi presenti sono
  file che misurano i dati di oggi e sullo scratch vuoto non trovano niente
  (`test-preventivi-guard-transizione-v1` 3-5,
  `test-capability-annulla-aspetto-e-stato-leggibile-v1` 2 e 8,
  `test-ddt-componenti-senza-prezzo-v1` 1,
  `test-offerte-rientro-padre-revisione-annullata` 3). ⚠️ Tre file muoiono nel
  fixture sullo scratch (IVA del preventivo, IVA dell'ordine, push offerta →
  contratto): il loro verdetto arriva **solo** dalla corsa di Tid su dbdev.
* ⚠️ Gli avvisi `fk_error_log_messaggio_errore_id` nella prova sono attesi: il
  log passa da una connessione separata, che non vede i codici caricati dentro
  la transazione. Dopo l'apply non ci sono.

✅ **Dopo l'apply (Tid, 2026-09-24 sera)**: migrazione applicata, corsa pgTAP
senza regressioni.

## 10. Le revisioni che ricopiano un «in attesa» — il giro 2

### 10.1 Il problema e la decisione

`fn_crea_revisione_preventivo` e `fn_crea_revisione_offerta` ricopiano sulla
revisione **stato e pratica** di approvazione, 1:1 (`20260914-14`,
`20260601-05`: «prezzo fuori policy sempre marcato»). Una riga **in attesa**
ricopiata resta legata alla pratica della revisione vecchia: l'esito arriva
lì, e sulla nuova l'attesa non finisce più. Non si modifica (guard per riga) e,
dal giro 1, il documento non si emette: resta solo l'annullamento. È il debito
di PROJECT_CONTEXT «Pratica di approvazione prezzo su revisione superata».

Tid ha proposto di non copiare lo stato e ripartire dal primo stato valido
(che è il **vuoto**, «nessuna approvazione chiesta»). ⚠️ Azzerare riapriva il
difetto sanato il 14-09 — la revisione nasceva con lo stesso prezzo e senza
marca — e con D-1 avrebbe fatto **passare un prezzo rifiutato**. La sua
seconda regola («se la precedente è in attesa non si fa una nuova versione»)
bastava da sola a chiudere il caso. ✅ **Decisione di Tid del 2026-09-24:
proposta 1+2.**

1. **Non si crea una revisione** (preventivo e offerta) se il documento ha
   righe o componenti attivi **in attesa**. «Crea revisione» resta a video,
   spento con il motivo.
2. **La copia resta** per approvato e rifiutato.

### 10.2 Cosa è stato scritto

| # | File | Cosa |
| --- | --- | --- |
| -33 | `20_code/script/…-create-fn-check-prezzi-in-attesa` | `script.fn_check_prezzi_in_attesa(regclass, bigint)`: dei motivi del building block, il solo `E_DOC_PREZZO_PENDENTE`. Quattro consumatori, scritto una volta |
| -34 | `20_code/vendite/…-update-fn-crea-revisione-preventivo-guard-prezzi-in-attesa` | la madre rifiuta col primo motivo (sito nuovo dell'helper) |
| -35 | `20_code/vendite/…-update-fn-crea-revisione-offerta-guard-prezzi-in-attesa` | idem; in più firma/`RETURNS` ancorati con `%TYPE` e `SECURITY INVOKER` esplicito, che mancavano |
| -36 | `20_code/script/…-update-fn-available-actions-preventivo-revisione-prezzi` | «Crea revisione» spento col motivo; `can_create_revisione` **veritiero** |
| -37 | `20_code/script/…-update-fn-available-actions-offerta-revisione-prezzi` | idem |

* **Messaggi**: `E_DOC_PREZZO_PENDENTE` / `_RIFIUTATO` diventano «Non si può
  procedere: ci sono prezzi … (N).» — «il documento non può avanzare» era falso
  per una revisione. Causa e soluzione dell'«in attesa» nominano la revisione.
  Stesso CSV (`runOnChange`), nessuna chiave FE nuova.
* **Dichiarazione dallo YAML**, non dall'auto-gen: le due madri partono dai loro
  ultimi YAML (`20260915-41`, `20260601-05`), verificati identici al vivo
  (`prosrc` e `COMMENT`); le capability dai miei `-23` e `-28`.
* **pgTAP**: `test-fn-check-prezzi-autorizzati-v1` da 38 a 44 test (39-44 sulle
  revisioni: pulsante spento, madre che rifiuta, rifiutato che non blocca e si
  ricopia, offerta); `test-rubinetto-primo-motivo-v1` test 5 da 23 a 25.
* **Doc**: `manual/` nuova per `fn_check_prezzi_in_attesa`, sezioni «rev
  2026-09-24» sulle due madri e sui due pulsanti, riga nella guida dei
  preventivi (§4.1).
* ⚠️ **Al FE**: nessuna chiave nuova; il frontend legge già l'azione
  `crea_revisione` da `available_actions` e ne rispetta `enabled` — basta il
  collaudo a video (preventivo e offerta EMESSI con un prezzo in attesa).

### 10.3 Le prove (prima dell'apply)

Sullo scratch, che ha il giro 1 applicato, in `BEGIN … ROLLBACK`:
`test-fn-check-prezzi-autorizzati-v1` **44/44**, `test-rubinetto-primo-motivo-v1`
7/7, `test-preventivi-approvazione-prezzo` 10/10; `plpgsql_check` a zero sulle
cinque funzioni. **Controprova**: senza `-33…-37` diventano rossi 39-44. I
pgTAP esistenti che creano revisioni (sette file) hanno gli stessi rossi prima
e dopo. Guardrail statici verdi.

### 10.4 La corsa della notte: due rossi attesi

La corsa pgTAP di Tid ha dato, fra i «rossi QUI che la CI non conosce»:

| File | Esito |
| --- | --- |
| `script/test-fn-check-prezzi-autorizzati-v1.sql` | ASSERZIONE |
| `script/test-rubinetto-primo-motivo-v1.sql` | ASSERZIONE |

**Causa**: il giro 2 non è applicato su quel database (su `zeroerp_ci` il
`databasechangelog` si ferma a `20260924-32`, letto il 2026-09-24). I due file
però sono già quelli del giro 2: il primo verifica le revisioni (test 39-44),
il secondo conta 25 siti dell'helper del primo motivo, e senza `-33…-35` sono
23. È la controprova del §10.3 vista dall'altra parte: senza i changeSet
diventano rossi proprio 39-44 e il test 5. Con `-33…-37` in testa alla stessa
transazione i due file danno 44/44 e 7/7.

⇒ **Non è debito e non entra in baseline**: si applica il giro 2 e si rilancia.
✅ **Fatto** (Tid, 2026-09-24 notte): giro 2 applicato, test verdi.
Un pgTAP che usa un oggetto nuovo si misura solo su un database che quel
changeSet ce l'ha.

## 11. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-24 | **Nascita**, dal §5 del brief capability annidata dopo la consegna BE/FE. Confronto delle due sedi sul corpo delle funzioni (§2). Decisioni di Tid: D-1 (strada A: il `REJECTED` è regola, a DB), D-2 e D-3 sulla raccomandazione. D-4 aperta |
| 2026-09-24 (sera) | **DB scritto.** D-4 (contratti e offerte), D-5 (un building block solo) e D-6 (ordini e DDT) decise da Tid. Tredici changeSet `20260924-20…-32` (fascia `-20…-39`, per non incrociare il §13 del brief delle date di validità), catalogo dei codici, un pgTAP nuovo e due aggiornati, doc. ⚠️ Scelta nuova rispetto alla prima stesura: i **rientri automatici** (ordine da `EVASO`, offerta da `SUPERATA`) non chiedono il prezzo, o un prezzo rimasto non autorizzato fermerebbe un annullamento (§4.2). Correzione di Tid in corso d'opera: firme ancorate con `%TYPE` (l'auto-gen le perde). Prove in transazione ritirata: §9. Aperta la domanda del §10 |
| 2026-09-24 (sera, dopo) | **Applicato** da Tid, corsa pgTAP senza regressioni. Restano le richieste FE (bloccante per la CI) e BE del §6, la riga in `baseline-rossi-ci.tsv` e la domanda del §10 |
| 2026-09-24 (notte) | **Giro 2, le revisioni** (§10): decisione di Tid «proposta 1+2» — nessuna revisione con un prezzo in attesa, la copia di approvato e rifiutato resta. `20260924-33…-37`, messaggi resi generici, pgTAP da 38 a 44, rubinetto a 25. Da applicare |
| 2026-09-24 (notte, dopo) | Corsa pgTAP di Tid: due rossi «che la CI non conosce», `test-fn-check-prezzi-autorizzati-v1` e `test-rubinetto-primo-motivo-v1`. Causa: giro 2 non applicato su `zeroerp_ci` (`databasechangelog` fermo a `-32`). Attesi, non in baseline: §10.4. Resta l'apply del giro 2 |
| 2026-09-24 (notte, chiusura DB) | **Giro 2 applicato, test verdi** (Tid). Il lato DB è chiuso; restano FE (bloccante per la CI), BE e la riga di baseline — §6 e testata |
| 2026-09-24 (BE/FE) | **§6 consegnato** su `dev/backend-tid`. **BE**: `get_preventivo` consegna il blob **com'è** — tolti la riscrittura di `available_actions`/`can_edit_*` e il 🔴 DEBITO DICHIARATO. ⭐ **Decisione sui quattro riepiloghi** (lasciata al BE dal §6.1): **ritirati anch'essi**, non estesi ai componenti. Contare righe **e** componenti attivi in Python sarebbe stata una seconda copia del predicato di `fn_check_prezzi_autorizzati`; il motivo, col conteggio (`dettaglio.n_prezzi`), è già nelle `reasons` delle azioni che il prezzo spegne. Il repository conta ora solo le righe attive (`count_righe_attive`, per `righe_count`); `count_righe_per_stato_approvazione` tolto, senza altri lettori. Test riscritti sul contratto del DB (blob intatto: «Emetti» spento col motivo, «Annulla» acceso, testata e righe modificabili; nessun riepilogo sulla testata). Policy rigenerate (i due `E_DOC_PREZZO_*` e il ritiro di `E_PREVENTIVO_RIGHE_PRICING_PENDENTI`; il diff porta anche il ritiro di `E_BOM_VALIDO_AL_INVALIDO` del cantiere date di validità, già nel CSV committato); ripiego: dentro i due codici nuovi senza `%s`, fuori il ritirato. Commento stantio in `ddt_service.cambia_stato`. Doc: `api_preventivi.md`, `api_approvazioni_prezzo.md`, `api_ordini.md`. **FE**: `common.azione_reason.prezzo_pendente` / `prezzo_rifiutato` in it/en; tolta `vendite.ddt.azione_reason.componenti_prezzo_pendente`; il banner del `PreventiviDrawer` legge i motivi `PREZZO_PENDENTE`/`PREZZO_RIFIUTATO` dalle `reasons` delle azioni (compare solo quando il prezzo blocca davvero un'azione) e il suo testo dice la regola nuova (chiavi `banner_prezzi_pendenti`/`_rifiutati`: la vecchia prometteva «transizioni ed edit bloccati», falso dopo D-2/D-3). **Verifica**: BE `apps.vendite` + `apps.core` verdi (3323 test, 43 skip); FE `npm run verify` verde; `check_i18n_keys.py` pulito; `guard:capability` verde. Sul DB di sviluppo nessuna bozza o emesso ha oggi un prezzo in approvazione: il caso si è **costruito** in una transazione annullata (una riga della bozza 32865 portata a `REJECTED`) → «Emetti» `enabled: false`, `reason_key` `common.azione_reason.prezzo_rifiutato`, `n_prezzi = 1`; «Annulla» acceso; `can_edit_*` veri; nessun campo extra. **Resta**: collaudo a video (§6.3); la riga di `baseline-rossi-ci.tsv` (team DB); la domanda del §10. ⚠️ Banner solo sul preventivo: asimmetria dichiarata, chiusa nella riga sotto |
| 2026-09-24 (FE, simmetria) | **Il banner del preventivo ritirato, non copiato** (decisione di Tid). L'asimmetria vera non era fra documenti ma fra **motivi**: il perché di un pulsante spento ha un canale solo, il tooltip di `mapAvailableActionsToDrawerActions` (tutti i motivi, non solo il primo), uguale in ogni drawer; «IVA mancante», «senza righe», «listino mancante» sono temporanei e azionabili come un prezzo in attesa, e nessuno ha un banner. Un banner su cinque documenti avrebbe lasciato i prezzi l'unico motivo col canale suo — ed è la stessa scelta della Decisione D di `work-done/brief-db-ddt-reason-push-catch-all.md` («tooltip discreto, non banner»). L'unica perdita, il **numero**, si recupera per tutti: il mapper passa i `valori` del motivo alla traduzione come `{0}` (`labelOrCode` con `params` opzionale), e le due chiavi dicono *«Ci sono prezzi in attesa di approvazione (2).»*. Un testo senza `{0}` non cambia. Presidi: `useDrawerActions.spec.js` 11 → 13 test (il 12 provato rosso per mutazione). Tolte le chiavi `banner_prezzi_*`. Il tag di stato sulla riga (preventivo, pannello componenti) resta: è dove l'operatore agisce. ⚠️ `useLottoAzioni.motiviTesto` era una seconda copia della resa dei motivi e **non** passava i `valori` → ✅ **regola del 2 applicata lo stesso giorno (ok Tid)**: `testoMotivi(t, te, azione)` in `useDrawerActions.js`, usata dal mapper e dal lotto, copia ritirata. Unica differenza di comportamento, voluta: sul lotto, un'azione spenta senza `reasons` ma col motivo singolo ora mostra quel motivo invece dell'avviso generico. Spec 15 test, FE `npm run verify` verde (322) |
| 2026-09-24 (merge) | I due lati sono stati uniti nello stesso documento (merge `21c59a174`): testata riscritta in **un** blocco di stato (prima ce n'erano due, DB-notte e BE/FE-sera, che si contraddicevano sui «restano»). Il giro 2 ha chiuso la domanda del §10 che il blocco BE/FE dava ancora aperta. ⚠️ **Ricaduta BE del giro 2**: i messaggi di `E_DOC_PREZZO_*` sono diventati «Non si può procedere: …», ma il ripiego del backend diceva ancora «Il documento non può avanzare», proprio la frase che il giro 2 aveva tolto perché falsa per una revisione → allineato. Policy generate già allineate alle note del CSV. Collaudo §6.3 esteso alle revisioni |
| 2026-09-24 (chiusura) | **Chiuso e archiviato in `work-done/`**, insieme a [brief-be-fe-capability-annidata.md](brief-be-fe-capability-annidata.md). Il collaudo a video passa nel copione [collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md](collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md). ⚠️ Scrivendolo: un documento **emesso** con un prezzo non autorizzato **dall'app non nasce più** (la richiesta si apre in bozza, e in bozza blocca l'emissione) — il §6.3 «in emesso → Accetta spento» e il collaudo delle revisioni del §10.2 si vedono solo costruendo il caso a DB; li coprono i pgTAP (13-15, 25-26, 39-44). La riga di baseline resta al team DB dopo la corsa CI |
