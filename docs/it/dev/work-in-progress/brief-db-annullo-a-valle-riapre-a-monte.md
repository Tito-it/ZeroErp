# Brief DB — Tornare indietro: annullare a valle riapre a monte, con la segnalazione

## ⏭️ Chi riparte — aggiornato al 2026-10-12

**Riparte: Tid con il team DB**, sul §10 (trovato nel collaudo: una commessa annullata non lascia
libero il documento, che non si puo' piu' rimandare in commessa), a partire dalla domanda del §10.5.
Il collaudo a video del giro di ritorno aspetta il §10.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | changeSet `20261012-08 … -24`, `-27 … -29`, CSV, pgTAP | §8 | — |
| 2 | ✅ BE/FE | ritiro delle copie del verso in avanti, annullo della commessa con la finestra, smoke | §9 | — |
| 3a | **Tid + team DB** | la domanda: la commessa si annulla anche con righe vive da documento? | §10.5 | — |
| 3 | **team DB** | il link documento → commessa (`vendite.commesse_sorgenti`) dopo l'annullo: R-13…R-15, nella forma che esce dal 3a | §10.3 | 3a |
| 4 | sessione BE | ricaduta del §10 (lettore del link nel backend, smoke) | §10.4 | 3 |
| 5 | Tid | lo smoke HTTP `smoke-test-ordini-giro-commessa.sh` (vuole la password degli smoke); il passo 14 fallisce finche' manca il §10 | §9.3 | 3 |
| 6 | Tid | collaudo a video: preventivo, ordine, misto, PRV0000144 | §6.4 | 3 |
| 7 | Tid | eseguire su dbdev l'SQL del §9.4 (deciso il 2026-10-12: si riportano a CONFERMATO) | §9.4 | — |
| 8 | sessione BE | archiviare in `work-done/`, riga di PROJECT_CONTEXT | — | 6, 7 |

**Decisioni aperte di Tid:** ❓ **§10.5**, da vedere con il team DB: la commessa si annulla anche con
righe vive spinte da un documento, o solo senza? Da li' la forma di R-13 (§10.3).
**Da committare:** il lavoro BE/FE del §9 (non committato).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11, dal collaudo a video di Tid; lettura critica e
> seconda tornata di decisioni del team DB (`dev/db-tid`), 2026-10-12 (§7). **A chi:** team DB; poi BE/FE (§6).
> **Stato:** 📝 **aperto.** Decisioni D-1…D-4 prese da Tid il 2026-10-11, **D-5…D-10 il 2026-10-12** (§4),
> dopo la lettura del team DB (§7). Il perimetro si e' allargato per decisione di Tid: anche il verso **in
> avanti** verso la commessa passa al DB (D-10), qui e non in un brief nuovo. ✅ **Lato DB scritto e provato
> il 2026-10-12** (§8: `20261012-08 … -24` + due righe di CSV, due pgTAP nuovi, tre aggiornati per
> contratto): applicato da Tid il 2026-10-12. Dalla corsa su dbdev: ⭐ **§8.5**, una riga senza documento
> d'origine e' un onere o una rettifica, per vincolo (`20261012-27 … -29` + 36 pgTAP corretti, piu' 17 nel
> secondo giro e `test-vw-dash-competenza-v1`): ✅ **applicato da Tid il 2026-10-12, corsa pgTAP tutta verde,
> nessuna regressione.** ✅ **Lato DB chiuso**; l'SQL dell'appendice D-9 eseguito da Tid il 2026-10-12. Resta da
> tenere d'occhio il costo del trigger (§8.4, non un lavoro). ✅ **BE/FE fatto il 2026-10-12** (§9):
> restano il collaudo a video (§6.4) e lo smoke HTTP, di Tid. ⚠️ **Riaperto lato DB il 2026-10-12** dal
> collaudo: una commessa annullata non lascia libero il documento, che non si rimanda in commessa (§10).
> **Origine:** il caso 6 di [brief-db-annullo-documento-con-legami](../work-done/brief-db-annullo-documento-con-legami.md)
> (§10), trovato nel collaudo e spostato qui per decisione di Tid: *«quando si torna indietro ci devono
> essere le segnalazioni di quello che si sta facendo; in avanti le abbiamo bloccate. Un unico
> meccanismo.»*
> **Non e' un doppione di quel brief:** la forma (lettore unico dei legami, avviso
> `E_DOC_ANNULLO_CON_LEGAMI`, verbo di annullo con la dichiarazione, finestra di conferma comune) e'
> nata li' e si RIUSA. Qui si aggiunge il documento che mancava, la **commessa**, e si verifica che il
> meccanismo sia lo stesso su ogni arco.
> **Nel registro dei difetti DB:** voce **D30** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. Il principio (Tid, 2026-10-11; eccezione del 2026-10-12)

Fra due documenti collegati c'e' un verso **in avanti** (a monte → a valle: preventivo → commessa,
ordine → bolla, ordine → commessa) e un verso **all'indietro**.

* **In avanti e' bloccato.** Il documento a monte non si annulla finche' un documento a valle vivo lo
  sta usando (es. il preventivo con un ordine vivo: motivo `ORDINE_GIA_GENERATO`; la commessa con righe
  gia' emesse: `RIGHE_EMESSE`). Ci si ferma e si sistema prima il documento a valle.
* **All'indietro riapre, con la segnalazione.** Annullare il documento a valle restituisce al documento
  a monte cio' che aveva consumato, e chi annulla vede **che cosa si riapre e dove** prima di
  confermare. E' gia' cosi' da bolla a ordine e reso, da ordine a preventivo e offerta, da contratto a
  offerta (brief-db-annullo-documento-con-legami).
* **Un meccanismo solo.** Stesso lettore, stesso avviso, stessa conferma, stessa finestra su tutti gli
  archi: un arco che fa a modo suo e' il punto in cui il principio si perde.
* **Un livello solo** (D-10). Andata e ritorno di uno stesso arco stanno nello stesso posto, il DB: una
  regola scritta per meta' nel backend e per meta' nel database e' due regole.

### 1.1 ⭐ L'eccezione: la commessa a valle (D-8)

Un documento che ha righe in una commessa **viva**, **non ancora emesse**, **si annulla con la conferma**:
le sue righe escono dalla commessa (ANNULLATA, col registro), le righe degli altri documenti restano.
Non e' un blocco, ed e' voluto.

**Il motivo, sul modello.** La commessa non e' figlia di un documento solo come l'ordine lo e' del
preventivo o la bolla dell'ordine: **raccoglie righe di piu' documenti** dello stesso cliente. Se valesse
il blocco, per annullare un preventivo la via d'uscita sarebbe una delle due:

* annullare **l'intera commessa**, cioe' anche le righe degli altri documenti, che non c'entrano;
* togliere dalla commessa **una riga alla volta**, che il modello vieta di proposito:
  `vendite.fn_annulla_commessa_attivita` rifiuta le righe con sorgente, perche' «per una riga da push il
  rimedio e' sempre a monte, sul documento».

Il blocco resta dove la riga e' gia' **emessa** (in volo verso una fattura): `script.fn_check_sorgente_chiudibile`,
con la via d'uscita «Riporta da emettere». E' la regola gia' in vigore dal D-5 di
brief-db-annullo-documento-con-legami (§3 qui sotto), ora scritta come principio.

## 2. Il caso che manca: annullare la commessa

La commessa e' a valle di preventivo, ordine, contratto e bolla (le righe spinte, `commesse_attivita`
con `sorgente_tipo_id` / `sorgente_uid`), e anche delle rettifiche del reso, dei consumi e degli oneri
(§7.3). Annullarla oggi (`vendite.fn_cambia_stato_commessa(…, 'ANNULLATA')`) non riapre niente e non
segnala niente.

**Il caso misurato** (collaudo di Tid, dbdev, 2026-10-11): PRV0000398 (rev. 0, id 50012) smistato per
intero nella commessa `CMM-PGTAPEF202-2026-000000008` (id 55666), poi la commessa annullata.

| Cosa | Oggi | Atteso |
| --- | --- | --- |
| finestra di conferma | nessuna | l'elenco di cio' che si riapre |
| la riga di commessa del preventivo | NON_EMESSA, dentro una commessa ANNULLATA | ritirata (ANNULLATA) con la commessa |
| PRV0000398 | EVASO, nessuna azione | **ACCETTATO**, riga di nuovo da smistare (D-1) |
| `vendite.fn_preventivo_ha_residuo_commessa(50012)` | `false` | `true` (vuole anche D-5: §7.1) |
| `vendite.fn_documento_legami('PREVENTIVO', 50012)` | 1 legame COMMESSA verso la commessa annullata | 0 |

Il lineage e' corretto nei due versi (dal preventivo si vede la commessa e viceversa): il difetto e' nel
modello, non nella lettura.

⚠️ **Ordine → commessa**: la domanda «l'ordine torna CONFERMATO?» e' chiusa da **D-6**: lo stato
dell'ordine lo dicono solo le bolle, quindi ne' l'invio in commessa ne' il suo annullo lo cambiano.
L'ordine torna «da mandare in commessa» perche' le sue righe tornano libere (D-5).

## 3. La verifica dell'«in avanti» (R-5, fatta dal team DB il 2026-10-12)

Letta sulle matrici (`80_data`) e sulle `fn_check_*_annullabile`, non sui dati.

| Arco (monte → valle) | Cosa lo regge oggi | In avanti bloccato? |
| --- | --- | --- |
| preventivo → ordine vivo | `script.fn_check_preventivo_annullabile`, `E_PREV_ORDINE_GIA_GENERATO` (anche con l'ordine in bozza) | ✅ |
| offerta → contratto / ordine | la matrice ammette solo BOZZA → ANNULLATA, e un'offerta in bozza non genera niente | ✅ per costruzione (nessuna check: la regge la matrice) |
| ordine → bolla viva | `script.fn_check_ordine_annullabile`, `E_ORD_ANNULLA_CON_DDT` | ✅ |
| ordine → (annullo da EVASO / PARZIALMENTE_EVASO) | la matrice ammette solo DRAFT e CONFERMATO → ANNULLATO | ✅ per costruzione |
| contratto → commessa | si annulla solo da DRAFT, il push vuole ATTIVO | ✅ per costruzione |
| commessa → fattura | `script.fn_check_commessa_annullabile`, `RIGHE_EMESSE` (D-3) | ✅ |
| preventivo, ordine, bolla → commessa, righe **EMESSA** | `script.fn_check_sorgente_chiudibile`, `E_SORGENTE_CON_RIGHE_EMESSE` | ✅ |
| preventivo, ordine, bolla → commessa, righe **NON_EMESSA** | conferma e ritiro (D-5 di brief-db-annullo-documento-con-legami) | ⭐ **eccezione voluta** (§1.1, D-8) |

Il caso del §3 originale (preventivo ACCETTATO con righe in commessa non emesse, PRV0000144) **resta
com'e'**: si annulla con la finestra. Il suo collaudo a video passa qui (§6.4).

**Debito documentale trovato nella lettura** (nessun effetto sul comportamento): i COMMENT di
`script.fn_check_ordine_annullabile` e `script.fn_check_preventivo_annullabile` citano un motivo «riga in
`vendite.commesse_sorgenti`» che nei corpi non c'e' piu'. Si riallineano nello stesso giro (R-12).

## 4. Decisioni di Tid

### 4.1 Prima tornata (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Annullare la commessa ritira le sue righe NON_EMESSA e riapre i documenti che le hanno spinte (preventivo EVASO → ACCETTATO con residuo commessa riaperto; ordine EVASO → CONFERMATO; contratto e bolla dove si applica)? | ✅ **si'**: «deve tornare accettato, la logica all'indietro e' la stessa che da ordini verso DDT». ⚠️ La parte sull'ordine e' **precisata da D-6**: l'ordine non cambia stato |
| **D-2** | Con la forma comune: avviso `E_DOC_ANNULLO_CON_LEGAMI`, `vendite.fn_documento_legami('COMMESSA', id)`, verbo `vendite.fn_annulla_commessa(id, legami_confermati)`? | ✅ **si'**: un unico meccanismo |
| **D-3** | Le righe gia' EMESSE bloccano l'annullo della commessa? | ✅ **gia' cosi'** (verificato il 2026-10-11): `script.fn_check_commessa_annullabile`, motivo `RIGHE_EMESSE`, codice `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`, sede unica di guard e capability. Il verbo nuovo la lascia parlare **prima** della conferma (prima cio' che vieta, poi cio' che chiede conferma) |
| **D-4** | I dati gia' rimasti indietro (commesse annullate con righe NON_EMESSA, es. 55666 e 113)? | ✅ **non serve** un ritiro una tantum nei changeSet: sono dati di test. Li sistema Tid a mano (D-9, SQL in appendice) |

### 4.2 Seconda tornata (2026-10-12, dalla lettura del §7)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-5** | Una riga di commessa ANNULLATA deve ancora «occupare» il documento da cui viene? | ✅ **no**: una riga ritirata non occupa il segmento, e il documento torna spingibile. La regola sta **in un posto solo** (`script.fn_get_stato_push_segment`); le altre due copie la leggono da li' (§7.1) |
| **D-6** | Che cosa vuol dire «Evaso» per l'ordine? | ✅ **solo «la merce e' partita»**: lo stato dell'ordine lo dicono le bolle (`vendite.fn_ordine_proietta_stato_evasione`: nessuna bolla → CONFERMATO, in parte → PARZIALMENTE_EVASO, tutta → EVASO; «partita» = bolla generata). L'invio in commessa **non** cambia lo stato dell'ordine, e nemmeno l'annullo della commessa. Che l'ordine sia gia' in commessa lo dicono la lista «da mandare» e le capability (§7.2) |
| **D-7** | Le righe di commessa che non vengono da preventivo, ordine, contratto o bolla? | ✅ **rettifica da reso**: il reso torna da accreditare, e la finestra lo dice (precisazione del 2026-10-12, §8.3: l'accredito si annulla e la quota non risulta piu' accreditata; la coda accrediti la ripropone quando la merce torna in fattura). **Consumo**: la misura torna da mandare in commessa, in finestra come gli altri. **Onere**: non riapre niente; si annulla con la commessa ed e' elencato in finestra («2 oneri vengono annullati») (§7.3) |
| **D-8** | Un documento con righe in una commessa viva, non emesse: blocco o conferma? | ✅ **conferma**, ed e' un'eccezione **scritta e motivata** nel principio (§1.1) |
| **D-9** | Le commesse annullate con righe NON_EMESSA rimaste indietro (R-4)? | ✅ **niente presidio e niente filtro nel lettore**: nessun vincolo del DB le ferma, e dal giro di questo brief non se ne creano piu' (§7.5). Le sistema Tid a mano su dbdev con l'SQL dell'appendice |
| **D-10** | Il verso in avanti verso la commessa (preventivo → EVASO, ordine → EVASO, commessa → PRONTA_FATTURAZIONE) oggi lo fa il backend: dove deve stare? | ✅ **tutto nel DB, in questo brief** (niente brief nuovi: *«o tutto DB o tutto BE»*, e la meta' che c'e' gia' e il ritorno stanno nel DB). Il backend ritira le sue copie nello stesso giro (§6). Per l'ordine, con D-6, il passaggio non si sposta: si **ritira** |

## 5. Cosa si chiede al team DB (riveduto il 2026-10-12)

| # | Cosa | Note |
| --- | --- | --- |
| **R-1** | `vendite.fn_documento_legami('COMMESSA', id)`: una riga per legame, le righe NON_EMESSA della commessa: dal documento che le ha spinte (preventivo, ordine, contratto, bolla), dalla rettifica del reso (il reso torna da accreditare), dal consumo (torna da mandare), e gli oneri (si annullano, non riaprono niente) | lo stesso lettore di avviso, conferma e finestra. La `natura` dell'onere (oggi esistono CONSUMO e PROVENIENZA) si decide nel disegno: la finestra deve poter dire «si annulla» invece di «si riapre» |
| **R-2** | L'avviso `E_DOC_ANNULLO_CON_LEGAMI` montato anche sulla commessa (BB `vendite.trgfn_doc_guard_annullo_con_legami`, fascia `_m10_`, dopo `trgfn_commesse_guard_transizione`) | in avanti parla prima `fn_check_commessa_annullabile` |
| **R-3** | Verbo `vendite.fn_annulla_commessa(p_commessa_id, p_legami_confermati)`: perimetro, conferma e ritiro (BB `vendite.fn_documento_ritira_legami`), cambio di stato, riproiezione a monte | ⚠️ il perimetro va scritto: `vendite.fn_cambia_stato_commessa` e' INVOKER e non ha il controllo che hanno i verbi di D29. Riproiezione: preventivo EVASO → ACCETTATO con la stessa regola del ramo ordine di `fn_documento_ritira_legami` (residuo ordine **o** commessa); ordine **nessun cambio** (D-6); reso di nuovo da accreditare (D-7); oneri ANNULLATA (D-7) |
| **R-4** | ~~Il lettore ignora le commesse abortite~~ | ❌ **ritirata da D-9**: con R-2 e R-3 una commessa annullata non ha piu' righe NON_EMESSA (§7.5) |
| **R-5** | La verifica dell'«in avanti» | ✅ **fatta** (§3) |
| **R-6** | pgTAP fabbricati: commessa da preventivo (EVASO → ACCETTATO e di nuovo smistabile), da ordine (stato invariato, di nuovo da mandare), preventivo **misto** (ordine vivo + commessa annullata: §7.4), rettifica (reso di nuovo da accreditare), consumo, onere, con righe emesse (bloccata), senza legami (passa senza conferma), conferma sbagliata; per D-10 l'andata (preventivo EVASO e commessa PRONTA_FATTURAZIONE dal DB; ordine Parzialmente evaso che resta tale dopo l'invio in commessa) | i dati di dbdev non bastano: si costruiscono |
| **R-7** | **D-5**: in `script.fn_get_stato_push_segment` una riga ANNULLATA non conta. `vendite.vw_preventivi_righe_smistabili_commessa` e `vendite.fn_list_consumi_da_pushare` smettono di avere un predicato proprio e leggono la funzione | regola del 2, copie ritirate nello stesso giro. ⚠️ Costo da misurare: la funzione e' `BEGIN ATOMIC` (non si inlinea) e verrebbe chiamata per riga sotto RLS. Censire gli altri lettori di `commesse_attivita.segment_key` (§7.1) |
| **R-8** | **D-10, preventivo**: il passaggio ACCETTATO → EVASO dopo l'invio in commessa, nel DB, con la regola che `vendite.fn_push_preventivo_a_ordine` usa gia' (nessun residuo su nessuna delle due strade) | regola del 2: la seconda sede della regola diventa un BB condiviso dai due invii e dal ritorno. Il punto di aggancio (fine del giro di push, `vendite.fn_close_commessa_push_run`, o altro) lo sceglie il team DB sul codice |
| **R-9** | **D-10, commessa**: il passaggio a PRONTA_FATTURAZIONE dopo l'invio, nel DB (oggi `commesse_service`, dopo l'approvazione delle righe) | stesso aggancio di R-8. Da decidere nel disegno se l'approvazione delle righe del push (`approva_commessa_attivita`) segue: e' la stessa operazione |
| **R-10** | **D-6, ordine**: nessun oggetto DB cambia; l'arco CONFERMATO → EVASO resta per la proiezione dalle bolle | la sola ricaduta e' nel backend e nella guida (§6) |
| **R-11** | I cinque elenchi del «documento» polimorfo da estendere con COMMESSA: `vendite.fn_documento_legami`, `vendite.fn_documento_ritira_legami`, `vendite.trgfn_doc_guard_annullo_con_legami`, `vendite.fn_doc_porta_ritiro_ammette`, e **`script.fn_get_stato_testata_documento`, che oggi non conosce la COMMESSA** (senza, l'avviso esce con «COMMESSA #id») | verificare sui guard di `commesse_attivita` se la porta del ritiro serve anche li' o solo sulla testata |
| **R-12** | COMMENT di `script.fn_check_ordine_annullabile` e `script.fn_check_preventivo_annullabile` riallineati ai corpi (§3) | solo testo |

✅ **Esito (2026-10-12): tutte fatte**, nel §8. Le tre scelte tecniche lasciate aperte qui le ha prese il
team DB, scritte nel §8.1: l'aggancio del verso in avanti (R-8: un trigger sulle righe di commessa, perche'
l'invio nel DB non ha una madre; R-9: una funzione madre chiamata dal backend, perche' «le righe di questo
invio» le conosce solo chi orchestra), la natura dell'onere (R-1: `ANNULLO`) e il costo della regola unica
(R-7: il classificatore resta una funzione, chiamata per riga come gia' fa il lister dell'ordine). R-11: la
porta del ritiro non serve sulla commessa (nessun legame di provenienza), basta l'avviso.

## 6. Ricaduta BE/FE (dopo la consegna DB; allargata da D-6 e D-10)

### 6.1 L'annullo della commessa (come prima)

* Backend: `GET /vendite/commesse/<id>/legami/` dalla factory `build_legami_view`; l'annullo della
  commessa (`/stato/` verso ANNULLATA) dal verbo, con `legami_confermati` (BB `_annullo_con_legami`).
* Frontend: `CommessaGestioneDrawer` passa il cambio di stato verso ANNULLATA da `useForzaturaConfermata`
  e mostra `DocumentoAnnulloLegamiDialog` (`base-path="/vendite/commesse"`), come bolla, ordine,
  preventivo e contratto. Lo store avvisa i tab con `avvisaDocumentiCollegati` (anche resi, per D-7).
* La finestra deve distinguere «si riapre» (documenti, reso, consumi) da «si annulla» (oneri): R-1.
* ⚠️ Cosa il lettore porta di nuovo per la commessa (`vendite.fn_documento_legami('COMMESSA', id)`, §8.1):
  `origine` in `PREVENTIVO`, `ORDINE`, `CONTRATTO`, `DDT`, `CONSUMI`, `RESO`, `ONERE` (il ramo `MANUALE` del
  `-19` e' uscito col vincolo del §8.5); `natura`
  `CONSUMO` o, per l'onere, `ANNULLO` (nuova); `riga_id` = la riga di commessa. In `_annullo_con_legami.py`
  `_TIPO_LINEAGE_DELL_ORIGINE` oggi conosce ORDINE, RESO, PREVENTIVO, OFFERTA, COMMESSA: servono CONTRATTO e
  DDT (e la commessa fra i documenti, `_TIPO_LINEAGE_DEL_DOCUMENTO`). ⚠️ Lo stato abortito della commessa e'
  `ANNULLATA` (femminile), non `ANNULLATO` come gli altri quattro.
* Il verbo e' `SELECT vendite.fn_annulla_commessa(id, legami_confermati)` (ritorna i legami confermati);
  le righe EMESSE rispondono `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE` **prima** della conferma.

### 6.2 Il verso in avanti esce dal backend (D-10)

| Cosa si ritira | Dove | Perche' |
| --- | --- | --- |
| `transiziona_a_evaso_se_smistato` (e il modulo `_smistamento_gate_helpers.py`, se resta senza consumatori) | `services/_smistamento_gate_helpers.py`, chiamato da `preventivi_service.py` (push a commessa) | il passaggio ACCETTATO → EVASO lo fa il DB (R-8) |
| il passaggio dell'ordine a EVASO dopo il push a commessa | `ordini_service.push_a_commessa` (savepoint «best-effort») | D-6: l'invio in commessa non cambia lo stato dell'ordine. ⭐ Corregge un difetto di oggi: un ordine PARZIALMENTE_EVASO mandato in commessa diventava EVASO con meta' merce in magazzino |
| il passaggio della commessa a PRONTA_FATTURAZIONE dopo il push | `commesse_service._rendi_commessa_emittibile` (invio singolo e batch) | lo fa il DB: il backend chiama `SELECT vendite.fn_rendi_commessa_emittibile(commessa_id, righe_ids, user)` al posto dei suoi due passi (approvazione + cambio di stato), stessa semantica di `righe_ids` (R-9) |

⭐ **L'ordine di rilascio non rompe niente** (letto sul codice il 2026-10-12): con il DB applicato prima del
backend, il preventivo diventa EVASO dal trigger, e il gate del servizio (`preventivi_service`, gia' dentro un
savepoint che cattura l'errore) tenta EVASO → EVASO, la matrice rifiuta e il servizio scrive un avviso nel log:
rumore, non un errore. L'orchestratore CONFERMA_VENDITA, che lo chiamava senza rete, e' progettato ma non
cablato. L'ordine continua a diventare EVASO dall'invio finche' il backend non ritira la sua copia (il difetto
di oggi, D-6). ⚠️ Invece l'annullo di una commessa con righe NON_EMESSA, dal giorno dell'apply, risponde
`E_DOC_ANNULLO_CON_LEGAMI` finche' il drawer non ha la finestra (§6.1): e' il blocco voluto, ma va rilasciato
insieme.

⚠️ Da controllare nel giro BE: i messaggi, i pannelli e i test che si aspettano «ordine EVASO a push
completato» (es. lo smistamento del preventivo, l'esito `MERCE_PRESENTE`, la chiusura dello step pratica
`INVIO_COMMESSA`, che oggi sta nello stesso blocco del passaggio a EVASO e resta).

### 6.3 Guide

* `gestione-commesse`: «Annullare una commessa» (che cosa si riapre, che cosa si annulla, la finestra).
* `gestione-ordini`: §4.1-§4.2 e glossario dicono oggi «EVASO = righe inviate a commessa (push
  completato)»: con D-6 **EVASO vuol dire merce partita** (bolle), e l'invio in commessa non cambia lo
  stato. Il rimando all'annullo della commessa.
* `gestione-preventivi`: il preventivo misto (§7.4) e il rimando all'annullo della commessa.
* `gestione-resi`: il reso torna da accreditare se si annulla la commessa della sua rettifica.

### 6.4 Collaudo a video

PRV0000398 (o un preventivo nuovo) smistato in commessa, commessa annullata con la finestra, preventivo
di nuovo ACCETTATO e di nuovo smistabile; lo stesso da un ordine (stato invariato, di nuovo da mandare);
un preventivo misto; PRV0000144 (preventivo ACCETTATO con righe in commessa non emesse, annullato con la
finestra: l'eccezione del §1.1).

## 7. Lettura critica del team DB (2026-10-12)

> Letta sul contratto (doc auto-generata, seed `80_data`, servizi del backend), non sui dati. E' cio' da
> cui sono nate le domande D-5…D-10.

### 7.1 Una riga ritirata contava ancora come «gia' spinta» (→ D-5, R-7)

Con il solo verbo (R-1…R-3) le righe della commessa sarebbero passate ad ANNULLATA, e **non si sarebbe
riaperto niente**: chi decide «questo documento e' gia' in commessa» conta anche le righe ANNULLATA.

| Lettore | Predicato | Dopo il ritiro |
| --- | --- | --- |
| `script.fn_get_stato_push_segment` (dichiarata «fonte unica del gia' inviato»: lister di ordine, contratto e bolla, diagnosi della bolla, capability) | `count(*) = 0` → LIBERA, qualunque `stato_emissione` | restava ALLOCATA |
| `vendite.vw_preventivi_righe_smistabili_commessa` (e da li' `fn_preventivo_ha_residuo_commessa`, `fn_list_preventivi_da_pushare`) | `NOT EXISTS` su qualunque riga del segmento, «qualsiasi stato_emissione» per scelta dichiarata; non vede `#RET:` | il residuo restava `false` |
| `vendite.fn_list_consumi_da_pushare` | `NOT EXISTS` senza filtro di stato (rev 2026-07-19) | restava consumato |

Tre copie dello stesso significato, due delle quali gia' diverse fra loro. La regola nuova («una riga
ANNULLATA non occupa») e' sicura sul modello: una riga ANNULLATA con sorgente nasce solo dal ritiro
all'annullo del documento a monte (morto, e i lister lo escludono per stato) o, da qui, dall'annullo
della commessa; le sourceless non hanno segmento di sorgente.

⚠️ Effetto da sapere: su un accredito annullato (`#RET:` ANNULLATA) nella corsia ORD (nota N11 del COMMENT
di `fn_get_stato_push_segment`) il segmento della bolla torna LIBERA, cioe' com'era prima
dell'accredito; contro la ri-spinta resta la cintura XOR sullo stato dell'ordine, come prima.

Lettori di `commesse_attivita.segment_key` da censire nel giro (elenco dalla doc auto-generata, da
leggere uno per uno): `fn_af_merce_per_riga`, `vw_af_merce_per_riga`, `vw_dash_fatturazione_ddt`,
`vw_dash_fatturazione_ordini`, `vw_lotto_documento_righe`, `vw_preventivi_smistamento_righe`,
`fn_build_gruppo_fatturabile_key`, `fn_gruppi_di_commessa_nel_lotto`, oltre a quelli della tabella.

### 7.2 «Evaso» dell'ordine aveva due scrittori (→ D-6)

* il **DB**, `vendite.fn_ordine_proietta_stato_evasione`, dalle bolle (chiamato da
  `fn_genera_ddt_da_ordine`, dai verbi del reso, dalla correzione della quantita' evasa, dal ritiro di una
  riga di bolla in bozza);
* il **backend**, `ordini_service.push_a_commessa`, dopo un push a commessa completo.

Nessuno dei due sapeva dell'altro, e la matrice ammette PARZIALMENTE_EVASO → EVASO: un ordine con meta'
merce spedita, mandato in commessa, diventava EVASO. Annullando la commessa il DB non avrebbe potuto
sapere quale dei due aveva scritto quell'EVASO. D-6 tiene il solo significato delle bolle.

### 7.3 La commessa ha legami che il brief non elencava (→ D-7)

Oltre a preventivo, ordine, contratto e bolla, in una commessa stanno: le **rettifiche del reso**
(`#RET:`, da `vendite.fn_accredita_riga_reso`; il rimedio inverso esiste, `fn_annulla_accredito_riga_reso`),
i **consumi** (sorgente con lister proprio) e gli **oneri** (sourceless, `vendite.fn_aggiungi_onere_commessa`).
Senza D-7, annullando la commessa una rettifica sarebbe rimasta viva in una commessa morta, o morta con il
reso ancora «accreditato».

### 7.4 Il preventivo misto (domanda di Tid, 2026-10-12)

Ogni riga del preventivo va da una parte sola: la merce nell'ordine, i servizi in commessa. Il preventivo
e' EVASO quando **nessuna** delle due strade ha un residuo; torna ACCETTATO appena **una** delle due ne ha
di nuovo.

| Cosa si annulla | Il preventivo |
| --- | --- |
| l'ordine (D29, gia' cosi') | le righe di merce tornano da ordinare, torna ACCETTATO; le righe in commessa restano |
| la commessa (questo brief) | le righe di servizio tornano da mandare, torna ACCETTATO; l'ordine resta vivo |
| tutti e due, uno dopo l'altro | ognuno riapre la sua parte; ACCETTATO una volta sola |
| il preventivo, con un ordine vivo | bloccato: prima l'ordine |
| il preventivo, senza ordine, con righe in commessa non emesse | con la finestra; le righe escono dalla commessa (§1.1) |

**La catena lunga** (preventivo → ordine → commessa): annullando la commessa si riapre **solo l'anello
subito prima**. Le righe dell'ordine tornano da mandare, lo stato dell'ordine non cambia (D-6), il
preventivo non si muove: le sue righe le usa ancora l'ordine. Si torna indietro di un passo alla volta,
come si va avanti.

### 7.5 L'invariante che sostituisce R-4 (→ D-9)

Con l'avviso montato sulla commessa (R-2) e il verbo che ritira prima di cambiare stato (R-3), una
commessa annullata **non ha righe NON_EMESSA**: ogni strada che cambia lo stato passa dal guard, e il guard
rifiuta finche' resta un consumo. Filtrare le commesse abortite nel lettore (R-4) avrebbe aggiunto un
caso che dalla struttura non nasce piu', e lo avrebbe filtrato in una sede sola: l'altra,
`fn_get_stato_push_segment`, e' la funzione piu' calda del push e una join in piu' sotto RLS li' costa.
Le righe di prima (55666, 113) non violano nessun vincolo: le sistema Tid (appendice).

### 7.6 Il passaggio in avanti, chi lo faceva (→ D-10)

| Passaggio | Chi, fino a questo brief |
| --- | --- |
| preventivo → ordine, preventivo ACCETTATO → EVASO | DB (`vendite.fn_push_preventivo_a_ordine`, atomico) |
| preventivo → commessa, preventivo ACCETTATO → EVASO | backend (`transiziona_a_evaso_se_smistato`, «best-effort») |
| ordine → bolla, CONFERMATO → PARZIALMENTE_EVASO / EVASO | DB (`vendite.fn_ordine_proietta_stato_evasione`) |
| ordine → commessa, → EVASO | backend (`ordini_service.push_a_commessa`, «best-effort») |
| commessa → PRONTA_FATTURAZIONE dopo l'invio | backend (`commesse_service`) |
| offerta → contratto / ordine; contratto, bolla → commessa | nessun cambio di stato |

Dove porta a un documento lo faceva il DB; dove porta in commessa, il backend, e «se riesce» (un
fallimento finiva in un avviso nel log e lo stato restava indietro). D-10 porta tutto nel DB.

### 7.7 Il costo della forma comune alla quinta copia

Montare la COMMESSA vuol dire estendere cinque elenchi scritti a mano (R-11). Non blocca D30, ma e' il
segnale che il «documento» polimorfo meriterebbe un vocabolario unico invece di cinque `IN (...)`: da
valutare al prossimo documento che entra nella forma, non qui.

## 8. Consegna DB (2026-10-12): scritta, provata, applicata

### 8.1 I changeSet

| NN | Oggetto | Cosa | D / R |
| --- | --- | --- | --- |
| `-08` | `script.fn_get_stato_push_segment` | una riga ANNULLATA non occupa il segmento (scritto «<> ANNULLATA»: uno stato nuovo occupa) | D-5, R-7 |
| `-09` | `vendite.vw_preventivi_righe_smistabili_commessa` | «gia' mandata» dal classificatore invece del `NOT EXISTS` proprio | D-5, R-7 |
| `-10` | `vendite.fn_list_consumi_da_pushare` | idem; il predicato di prima non escludeva niente (§8.3) | D-5, D-7, R-7 |
| `-11` | `vendite.vw_preventivi_smistamento_righe` | IN_COMMESSA = segmento non LIBERO (prima: solo EMESSA, §8.3) | D-5, R-7 |
| `-12` | ⭐ BB `vendite.fn_preventivo_proietta_stato_smistamento` | ACCETTATO <-> EVASO dal residuo sulle due strade: la sede unica | D-1, D-10, R-8 |
| `-13` | `vendite.fn_push_preventivo_a_ordine` | la sezione 8 chiama il BB | D-10 |
| `-14` `-15` | `vendite.trgfn_commesse_attivita_proietta_stato_preventivo` + due trigger `_z90_` | una riga di commessa di un preventivo che nasce, cambia `stato_emissione` o sparisce riproietta il preventivo: l'invio (singolo e batch), il ritiro, l'annullo | D-10, R-8 |
| `-16` | madre `vendite.fn_rendi_commessa_emittibile` | dopo l'invio: approva le righe dell'invio, commessa a PRONTA_FATTURAZIONE (prima nel backend) | D-10, R-9 |
| `-17` | `script.fn_get_stato_testata_documento` | + COMMESSA («Commessa <codice>») | R-11 |
| `-18` | `vendite.fn_ritira_commessa_attivita_da_sorgente` | quarto parametro `p_commessa_id` (NULL = tutte, com'era): DROP + CREATE | D-1, R-3 |
| `-19` | `vendite.fn_documento_legami` | + COMMESSA: una riga per riga NON_EMESSA; natura nuova ANNULLO (l'onere) | D-2, D-7, R-1 |
| `-20` | `vendite.trgfn_doc_guard_annullo_con_legami` | + COMMESSA; «da ritirare» = ogni legame che non e' PROVENIENZA | D-2, R-2 |
| `-21` | `trg_commesse_m10_guard_annullo_con_legami_upd` | l'avviso montato sulla commessa, dopo il guard di transizione | D-2, D-3, R-2 |
| `-22` | `vendite.fn_documento_ritira_legami` | + COMMESSA (ogni riga dal verbo del suo genere); **prima cio' che vieta**, per tutti i documenti (§8.3); §4b dal BB; §4a solo per la bolla | D-1, D-3, D-7, D-10, R-3 |
| `-23` | verbo `vendite.fn_annulla_commessa` | stampo dei verbi di D29: perimetro, BB, stato, porta chiusa. SECURITY DEFINER | D-1, D-2, R-3 |
| `-24` | COMMENT delle due check | riallineati ai corpi | R-12 |
| CSV | `messaggi_errore`, `codici_errore` | il testo di `E_DOC_ANNULLO_CON_LEGAMI` nomina anche la commessa (i due `%s` invariati) | D-2 |

Nessun codice nuovo. R-4 ritirata (D-9), R-5 nel §3, R-10 nessun oggetto DB.

### 8.2 La prova (sullo scratch `zeroerp_ci`, da owner, transazioni ritirate)

* **SQL estratto** dei 17 changeSet, in ordine, con le **preCondition** valutate ciascuna al suo punto: tutte
  vere. I **rollback**, eseguiti all'indietro dopo l'apply: tutti passano. `plpgsql_check` sulle undici
  funzioni nuove o cambiate (i due trigger con la loro tabella): zero errori.
* **pgTAP nuovo** `vendite/test-annullo-commessa-v1.sql`: **31/31**. Costruisce tutto (cliente, articoli,
  preventivi, ordini, commesse); l'invio in commessa passa dai lister veri e dalla madre delle righe, come fa
  l'orchestratore. Casi: preventivo andata e ritorno (EVASO dal DB, PRONTA_FATTURAZIONE dal DB, rifiuto
  diretto, conferma sbagliata, conferma, ACCETTATO e di nuovo smistabile, secondo invio), ordine (stato
  invariato, torna da mandare), preventivo misto, una sorgente in due commesse, oneri, righe EMESSE prima della
  conferma, preventivo con ordine vivo prima della conferma, commessa senza legami, classificatore, trigger
  solo sui preventivi.
  **Mutazione**: tolto il `-08` (D-5), il file da' sette rossi (11, 12, 14, 16, 17, 25, 26): morde.
* **pgTAP nuovo** `vendite/test-annullo-commessa-rettifica-v1.sql`: **6/6**. La catena intera (ordine ->
  bolla consegnata -> riga di commessa con la sua sorgente -> emissione -> fattura -> reso a credito ->
  accredito -> reset della riga fatturata -> annullo della commessa).
* **Aggiornati per contratto** (la regola che fissavano e' quella che D-5 cambia):
  `script/test-fn-get-stato-push-segment-v1` test 9 (ANNULLATA -> LIBERA, 11/12 prima e dopo: il 12 e' il
  rosso «da owner» dichiarato); `vendite/test-vw-preventivi-smistamento-v1` test 6 in due (NON_EMESSA ->
  IN_COMMESSA, ritirata -> RESIDUA), piano 10; `script/test-rubinetto-primo-motivo-v1` test 5 da 38 a 39 (un
  sito nuovo sull'helper, il §1-bis del `-22`); `vendite/test-fn-preventivo-ha-residuo-commessa-v1` test 12
  (ANNULLATA -> residuo `true`: fissava la decisione del 2026-06-28 che D-5 sostituisce). ⚠️ Quest'ultimo
  l'ha trovato la corsa di Tid su dbdev il 2026-10-12: sullo scratch il file si ferma prima per i dati,
  quindi la regressione non lo vedeva. Cercati gli altri pgTAP che fissano «ANNULLATA occupa»: nessuno.
* **Regressione** (145 pgTAP che nominano gli oggetti toccati, piu' i presidi trasversali: riferimenti morti,
  catalogo dei messaggi, rubinetto; «prima» = il file in HEAD senza l'SQL estratto): **nessuna differenza**
  fuori dal file nuovo. 56 file interi verdi; 11 con gli stessi rossi prima e dopo (i rossi «da owner»
  dichiarati nei file, fra cui il 30 di `test-annullo-documento-con-legami-v1`); 78 si fermano sullo scratch
  per i dati, prima e dopo allo stesso punto.

### 8.3 Trovati nel giro

* ⭐ **Il lister dei consumi non escludeva niente** (`-10`). Cercava `'CONS:<uid>:%'`, ma il segmento che
  scrive e' `'CONS:<uid>'`, senza i due punti: vedeva solo le righe del fan-out per componente (`':COMP:<x>'`,
  `HandlerConsumi._expand_rows`), che e' uno stub rimandato (Tid, 2026-06-16). Un consumo gia' mandato restava
  in lista; all'idempotenza pensava solo l'`ON CONFLICT` dell'upsert nella stessa commessa. ⚠️ Il giorno in cui
  il fan-out si accende deve usare il suffisso `#CMP:` che il classificatore vede, non `:COMP:`.
* ⭐ **Il pannello di smistamento era una copia rimasta indietro** (`-11`). IN_COMMESSA contava solo le righe
  EMESSA, allineato al predicato che la vista smistabili aveva fino al 2026-06-28; da quel giorno una riga
  mandata e non emessa risultava RESIDUA mentre il push la dava gia' inviata. Il test che lo fissava diceva
  «predicato allineato a EMESSA».
* ⭐ **Prima cio' che vieta, per tutti i documenti** (`-22`, D-3). I verbi di D29 chiedevano la conferma e solo
  dopo il cambio di stato rifiutava: un preventivo con un ordine vivo e righe in commessa chiedeva di
  confermare il ritiro, poi diceva ORDINE_GIA_GENERATO. Ora il BB solleva subito il primo motivo della stessa
  check del guard (test 21 e 23 del file nuovo). Vale anche per bolla, ordine e contratto. La matrice resta ai
  guard.
* ⭐ **La decisione del 2026-06-28** «ANNULLATA conta come allocata; il ri-push e' un flusso da progettare a
  parte» (pagina manual del classificatore): il flusso e' questo, e D-5 la sostituisce. La pagina lo dice.
* **D-7, la rettifica, in pratica.** La rettifica nasce nella stessa commessa della riga fatturata che
  corregge, che e' EMESSA: finche' lo resta, la commessa non si annulla (D-3). Il ramo si raggiunge dopo il
  reset del lotto (la riga torna NON_EMESSA). Annullando la commessa l'accredito si annulla e la quota non
  risulta piu' accreditata (test 5: da 3 a 0); la coda accrediti la riproporra' quando la merce tornera' in
  fattura, perche' dopo il reset non lo e'. ⚠️ Se l'accredito ha un'altra rettifica gia' emessa in un'altra
  commessa, il verbo dell'accredito rifiuta (RETTIFICA_EMESSA) dopo la conferma: caso non anticipato dal §1-bis.
* Il BB del ritiro chiamava il ritiro dei legami di bolla per ogni legame di origine ORDINE o RESO, senza
  guardare il documento: la commessa ha legami con quelle origini. Ora solo per la bolla (`-22` §4a).

### 8.4 Cosa resta a Tid, e cosa non e' provato qui

* ✅ **Apply** di `20261012-08 … -24` e dei due CSV, poi di `-27 … -29` (§8.5): fatto da Tid il 2026-10-12;
  la corsa pgTAP su dbdev, dopo il secondo giro sulle fixture e la correzione di `test-vw-dash-competenza-v1`
  (§8.5), e' **tutta verde, senza regressioni**. I punti che restavano da guardare, chiusi da quella corsa:
  * `vendite/test-vw-preventivi-smistamento-v1` e `vendite/test-ritiro-commessa-attivita-da-sorgente-v1`
    sullo scratch si fermano per i dati (prima e dopo): li prova la corsa su dbdev. Il primo e' aggiornato per
    contratto (test 6a/6b, piano 10); il secondo chiama la primitiva a tre argomenti, che resta valida;
  * l'esito come app (la RLS): la prova e' da owner; il trigger e la proiezione sono INVOKER, il verbo DEFINER
    come i fratelli;
  * il rubinetto a 39: se l'altra sessione di oggi aggiunge un sito sull'helper, il numero va sommato.
* ✅ **Le commesse annullate rimaste indietro** su dbdev (55666, 113): l'SQL dell'appendice (D-9), eseguito da
  Tid il 2026-10-12; la SELECT di controllo ora non torna righe. Dopo l'apply
  del `-08` i loro documenti tornano spingibili, e i preventivi EVASO tornano ACCETTATO dal trigger delle righe,
  perche' l'UPDATE dell'appendice passa da li'.
* **Il costo del trigger** sull'invio batch non e' misurato qui (lo scratch non ha dati): per ogni riga di un
  preventivo la proiezione rilegge il residuo delle righe del preventivo.

### 8.5 Una riga senza documento d'origine e' un onere o una rettifica (decisione di Tid, 2026-10-12)

**Da dove nasce.** La corsa di Tid su dbdev di `vendite/test-guard-uscita-commessa-v1` (test 15: annullo di una
commessa con una riga NON_EMESSA senza sorgente). Il lettore del `-19` chiamava quella riga MANUALE e l'avviso
la rifiutava sempre: nessun verbo la sa ritirare, quindi una commessa cosi' non si annullava mai.

**Sul modello.** Le righe di commessa nascono da tre strade sole: l'invio (con la sorgente, sempre: il lister la
proietta, l'handler del backend la esige), `vendite.fn_aggiungi_onere_commessa` (ONERE) e
`vendite.fn_accredita_riga_reso` (RETTIFICA), queste due senza sorgente. Una NORMALE senza sorgente non la
scriveva nessuno: la costruivano solo le fixture dei pgTAP. Ma il DB non lo imponeva (lo diceva il guard 4 di
`vendite.fn_annulla_commessa_attivita`: «garantito dalla disciplina di chi chiama e non dalla struttura»).
**Decisione di Tid: la regola va nel DB, e si corregge tutto cio' che ne consegue, test compresi.**

| NN | Oggetto | Cosa |
| --- | --- | --- |
| `-27` | `chk_commesse_attivita_senza_sorgente_onere_rettifica` (00_schema) | `sorgente_tipo_id IS NOT NULL OR tipo_movimento IN ('ONERE', 'RETTIFICA')`. preCondition HALT se esiste gia' una riga che lo viola (la query e' nel messaggio) |
| `-28` | `vendite.fn_documento_legami` | via il ramo MANUALE: senza sorgente, RETTIFICA -> RESO, altrimenti ONERE |
| `-29` | `vendite.fn_documento_ritira_legami` | solo il commento del §4d |

⚠️ Numeri: l'altra sessione di oggi ha scritto il suo `20261012-26` mentre scrivevo; i tre di questo giro sono
stati rinumerati a `-27…-29` prima della consegna.

**I test, corretti** (36 file, 47 scritture censite con uno script sui sorgenti dei pgTAP): ogni fixture che
scriveva una riga NORMALE senza sorgente ora le da' la sorgente COMMESSA con l'id della commessa (la forma del
builder `dbops.fn_pgtap_crea_commessa_attivita`); dove il movimento e' un parametro (`test-fn-af-merce-per-
riga-chiusura`, `test-vw-af-merce-per-riga`, `test-fn-partite-merce-chiusura`) solo le righe NORMALE, perche'
onere e rettifica nascono senza. Casi a mano:

* `vendite/test-commesse-schema-v1`: le tre scritture prendono la sorgente, cosi' i due `throws_ok` (unicita',
  `pricing_mode`) continuano a fallire per il loro motivo e non per il vincolo nuovo; **asserzione nuova 10-bis**:
  una NORMALE senza sorgente e' rifiutata dal vincolo, per nome (piano 17);
* `vendite/test-commessa-pronta-fatturazione-v1`: la copia di una riga reale prende la sorgente della commessa
  di test, non quella della riga reale, che punterebbe a un documento vero e ne riproietterebbe lo stato;
* `vendite/test-tipo-movimento-colonna-v1` test 7 e il batch (`test-fn-batch-upsert-commessa-attivita-v1`):
  invariati (il primo e' rifiutato prima di scrivere; il secondo passava gia' la sorgente);
* `vendite/test-guard-uscita-commessa-v1` **test 15**: l'annullo passa dal verbo,
  `vendite.fn_annulla_commessa(id, 1)`: la riga NON_EMESSA e' un legame, e dal verbo di stato l'avviso lo
  rifiuterebbe. Il test 13 (righe EMESSE, rifiutato) resta com'era.

**Secondo giro sui test (2026-10-12, dopo la corsa di Tid su dbdev).** Il censimento cercava le fixture che
la sorgente la *omettevano*, e non ha visto quelle che la scrivevano **esplicitamente a NULL**: `…, NULL, NULL`
in coda a un `INSERT` (forme `SELECT` e `VALUES`) e `p_sorgente_tipo_id => NULL` nella madre. Sono 17 file in
`ERRORE_FIXTURE` sul vincolo. Corretti allo stesso modo (sorgente COMMESSA con l'id della commessa), con due
casi a mano:

* dove il test si costruisce la chiave del gruppo come «senza sorgente»
  (`fn_build_gruppo_fatturabile_key(NULL, NULL, v_comm)`: `test-pull-non-prende-trattenuti`,
  `test-specchio-lane-diagnostica`, `test-vw-commesse-attivita-emittibilita`, `test-diagnostica-gruppi-
  fatturabili`), la chiave la chiede con la sorgente della riga, altrimenti punterebbe a un gruppo `MAN:` che
  non esiste piu';
* `vendite/test-fn-list-commessa-attivita-provenienza-v1`: la riga senza sorgente **e'** il soggetto (15–17),
  quindi resta senza sorgente e diventa una RETTIFICA (l'ONERE vorrebbe la causale); i filtri 24/25/27 seguono
  (RETTIFICA presente, NORMALE assente, `'  rettifica  '`);
* `vendite/test-vw-dash-competenza-v1` (rimasto rosso alla corsa dopo il secondo giro, test 15): stesso caso,
  il gruppo DA_EMETTERE senza sorgente e' il soggetto (`documento_id` NULL, riferimento sulla commessa). La sua
  riga A2 torna senza sorgente come RETTIFICA; le altre righe della fixture tengono la sorgente COMMESSA.

⚠️ **Richiesta al backend**: `backend/scripts/tests/smoke-ritorno-lotto-a-draft.py` chiama
`vendite.fn_upsert_commessa_attivita` con una NORMALE senza sorgente: dopo il `-27` il vincolo la rifiuta. Va
passata la sorgente (COMMESSA, uid = id della commessa, come `dbops.fn_pgtap_crea_commessa_attivita`).

**La prova** (scratch, transazioni ritirate): `-27…-29` con le preCondition, in sequenza: verdi. I 41 pgTAP
toccati oggi, lo stesso file prima e dopo i tre changeSet: **esiti identici** (31/31 e 6/6 i due nuovi; 16/16
satelliti RLS, 21/21 lock fuori bozza, 7/7 guard del BA, 6/6 segment_base, gli altri invariati). ⚠️ 27 di
questi file sullo scratch si fermano per i dati prima di arrivare alle righe corrette (BA presi dal database):
li prova la corsa su dbdev.

**All'apply** (Tid, 2026-10-12): la preCondition del `-27` (ferma il migrate se esiste gia' una riga NORMALE
senza sorgente, e il messaggio porta la query per trovarla) e' passata; il vincolo e' in tabella. La corsa pgTAP
che ne e' seguita ha portato al secondo giro sulle fixture (sopra) e alla correzione del test 15 di
`test-vw-dash-competenza-v1`; dopo, ✅ **tutta verde, nessuna regressione** (Tid, 2026-10-12).

## Appendice — D-9: le commesse annullate rimaste indietro (SQL per Tid, dbdev)

✅ Eseguito da Tid su dbdev il 2026-10-12 (dopo l'apply di `-08 … -24`): la SELECT del passo 1 ora non torna
righe. Non eseguito dal team DB. Porta le righe ad ANNULLATA invece di cancellarle: una riga di commessa ha
storico e registro collegati.

```sql
BEGIN;

-- 1. Guarda prima cosa c'e'
SELECT ca.id, ca.commessa_id, c.codice, ca.segment_key, ca.sorgente_uid
  FROM vendite.commesse_attivita ca
  JOIN vendite.commesse c        ON c.id  = ca.commessa_id
  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
 WHERE sc.is_abortito
   AND ca.stato_emissione = 'NON_EMESSA'
 ORDER BY ca.commessa_id, ca.id;

-- 2. Le porta ad ANNULLATA
UPDATE vendite.commesse_attivita ca
   SET stato_emissione = 'ANNULLATA'
  FROM vendite.commesse c
  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
 WHERE c.id = ca.commessa_id
   AND sc.is_abortito
   AND ca.stato_emissione = 'NON_EMESSA';

-- 3. Se il conteggio torna con la SELECT: COMMIT; altrimenti ROLLBACK;
```

Da lanciare **dopo** l'apply di `20261012-08 … -24`: allora i documenti da cui venivano le righe tornano
spingibili (D-5), e i preventivi EVASO tornano ACCETTATO da soli, perche' l'UPDATE passa dal trigger delle
righe di commessa (`20261012-15`). Lanciato prima, le righe si ritirano ma i preventivi restano EVASO.

## 9. Consegna BE/FE (2026-10-12)

### 9.1 Backend

| Cosa | Dove |
| --- | --- |
| L'annullo della commessa dal verbo: verso `ANNULLATA` `cambia_stato_commessa` chiama `vendite.fn_annulla_commessa(id, legami_confermati)` (dopo la difesa applicativa delle capability, che resta); risposta nella forma del cambio di stato | `commesse_service.cambia_stato_commessa`, `CommesseRepository.annulla` |
| `GET /vendite/commesse/<id>/legami/`: prima la testata (404 `E_COMMESSA_NOT_FOUND`), poi il BB | `commesse_service.get_legami`, `legami_views.ApiCommessaLegami` (factory con `model_permission=None`, come i passaggi della commessa), `urls_v1.py` |
| Il BB dei legami conosce la commessa: `DOCUMENTO_COMMESSA`, `STATO_ANNULLATA`, lineage della commessa; origini `CONTRATTO` e `DDT` | `_annullo_con_legami.py` |
| Il `POST …/stato/` trasporta `legami_confermati` | `views.ApiCommessaStato` |
| R-9: il ponte di emittibilita' chiama la madre `vendite.fn_rendi_commessa_emittibile` al posto dei suoi due passi (stessa semantica di `righe_ids`: None, vuota, piena) | `commesse_service._rendi_commessa_emittibile`, `CommesseRepository.rendi_commessa_emittibile` |
| R-8: ritirato il passaggio ACCETTATO → EVASO del push del preventivo; ritirato il modulo `_smistamento_gate_helpers.py` (senza consumatori) | `preventivi_service.push_a_commessa` |
| D-6: ritirato il passaggio dell'ordine a EVASO dopo l'invio in commessa; la chiusura dello step pratica `INVIO_COMMESSA` resta | `ordini_service.push_a_commessa` |

Controllato il §6.2 «da controllare»: lo smistamento del preventivo e l'esito `MERCE_PRESENTE` non
dipendono dallo stato EVASO dell'ordine (l'esito guarda se un ordine e' nato dal preventivo); la chiusura
dello step `INVIO_COMMESSA` resta nel blocco del push completato. Nessun messaggio del frontend promette
«ordine EVASO a push completato».

### 9.2 Frontend

* `CommessaGestioneDrawer`: l'annullo passa da `useForzaturaConfermata` e apre
  `DocumentoAnnulloLegamiDialog` (`base-path="/vendite/commesse"`); le altre azioni di stato restano
  com'erano.
* Store minimo `useCommesseStore` (`vendite/stores/commesse.js`): il cambio di stato, e dopo l'annullo
  l'avviso ai tab (`avvisaDocumentiCollegati`). Esiste perche' lo standard vuole il produttore dell'avviso
  nello store, mai nel drawer; la commessa non ne aveva uno.
* `avvisaDocumentiCollegati` avvisa anche contratti e bolle (tornano da mandare in commessa).
* `DocumentoAnnulloLegamiDialog`, forma della commessa (la decide `documento` della risposta): le righe che
  si riaprono **contate per documento d'origine** («torna da mandare in commessa · righe: n», per il reso
  «torna da accreditare»), gli oneri in un secondo elenco «Che cosa si annulla» (R-1 §6.1). Il numero
  dichiarato resta `legami` del lettore, oneri compresi.
* Chiavi i18n (it/en) sotto `vendite.annullo_legami.*`; costante `STATO_COMMESSA.ANNULLATA`.

### 9.3 Le prove

* Django: `apps.vendite.tests` 2359 verdi, `apps.core` 1624 verdi; mypy a cricchetto a zero; ruff pulito.
  Nuovi: annullo dal verbo, dichiarazione non numerica, codice del DB con `confirm_and_retry`, legami dopo
  la testata, lineage della commessa nel BB; riscritti i test del ponte (la madre DB), del push dell'ordine
  (lo stato non cambia, anche da `PARZIALMENTE_EVASO`) e del push del preventivo (lo stato non lo tocca
  il backend). Ritirati quelli che fissavano le copie (skip «gia' pronta», gate EVASO Python, transizione
  soft): le regole sono del DB e le prova il pgTAP.
* Frontend: vitest 839 verdi (nuovi: lo store, il caso commessa del dialog, provato per mutazione su
  due punti), lint, guard, build.
* **Binding vero sul DB di sviluppo** (prova in-process, transazione ritirata): `get_legami` col nome
  dal lineage; senza conferma e con la conferma sbagliata `E_DOC_ANNULLO_CON_LEGAMI`; con la conferma
  la commessa e' `ANNULLATA` senza righe `NON_EMESSA`; la madre dell'emittibilita' risponde con `[]` e con
  `None`, e su una commessa annullata la matrice rifiuta.
* **Smoke Python** (`scripts/smoke-baseline.sh`, dbdev): `ritorno-lotto-a-draft` (§8.5) e altri cinque
  verdi. ⚠️ **Trovato nel giro**: il §8.5 nominava uno smoke, ma la stessa scrittura — una riga NORMALE
  senza sorgente da `vendite.fn_upsert_commessa_attivita` — stava in altri cinque
  (`fattura-indirizzi-snapshot`, `fattura-scadenze`, `fattura-aggregazione-termini`,
  `fatturazione-aggregazione-righe`, `push-termine-documento-commessa`). Corretti tutti allo stesso modo
  (sorgente COMMESSA, uid = id della commessa). ⭐ Regola del 2 (ok Tid, 2026-10-12): la chiamata,
  copiata nei sei, e' diventata un BB degli smoke, `crea_riga_commessa` in
  `scripts/tests/_smoke_commessa.py` (catalogo BB backend); i sei di nuovo verdi su dbdev.
* **Smoke HTTP** `smoke-test-ordini-giro-commessa.sh`: riallineato a D-6 (il passo 7 si aspettava EVASO
  dopo l'invio) e allungato col ritorno (passi 11-14: domanda 409, legami, annullo confermato, ordine
  CONFERMATO e di nuovo da mandare). ⏳ **Non eseguito**: vuole la password degli smoke. Gunicorn
  ricaricato il 2026-10-12.

### 9.4 Per Tid: gli ordini EVASO senza bolle (dati di test)

Fatto datato (dbdev, 2026-10-12, nel perimetro di un utente): **30 ordini `EVASO` senza nessuna riga
evasa da una bolla**. Sono il residuo del vecchio invio in commessa, che portava l'ordine a EVASO (D-6):
nessun vincolo del DB li ferma, e da questo giro non se ne creano piu'. Come per D-9, sono dati di test, e
nessun lavoro di codice.

✅ **Decisione di Tid (2026-10-12): si riportano a CONFERMATO**, a mano su dbdev. Lo fa il BB che
proietta lo stato dalle bolle (`vendite.fn_ordine_proietta_stato_evasione`: nessuna bolla →
`CONFERMATO`), e la matrice ammette l'arco `EVASO → CONFERMATO` (letto su dbdev il 2026-10-12). Non
eseguito dalla sessione BE.

```sql
BEGIN;

-- 1. Guarda prima cosa c'e': ordini EVASO senza nessuna riga evasa da una bolla
SELECT o.id, o.numero
  FROM vendite.ordini o
  JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
 WHERE s.codice_interno = 'EVASO'
   AND NOT EXISTS (SELECT 1
                     FROM vendite.ordini_righe r
                     JOIN vendite.ordini_righe_fulfillment f ON f.ordine_riga_id = r.id
                    WHERE r.ordine_id = o.id)
 ORDER BY o.id;

-- 2. Riproietta lo stato dalle bolle (senza bolle: CONFERMATO)
SELECT o.id, vendite.fn_ordine_proietta_stato_evasione(o.id)
  FROM vendite.ordini o
  JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
 WHERE s.codice_interno = 'EVASO'
   AND NOT EXISTS (SELECT 1
                     FROM vendite.ordini_righe r
                     JOIN vendite.ordini_righe_fulfillment f ON f.ordine_riga_id = r.id
                    WHERE r.ordine_id = o.id);

-- 3. Rilancia la SELECT del passo 1: deve tornare zero righe. Poi COMMIT; altrimenti ROLLBACK;
```

### 9.5 Guide e documentazione

* `gestione-commesse`: «Annullare una commessa» (verso in avanti e all'indietro, che cosa si riapre e
  che cosa si annulla, l'eccezione del §1.1) e il passo 5 dell'invio (la madre DB).
* `gestione-ordini`: stati riscritti su D-6 (EVASO = merce partita, cinque stati in uso), push che non
  cambia lo stato, rimando all'annullo della commessa, glossario.
* `gestione-preventivi`: ACCETTATO ↔ EVASO dal DB nei due versi, la commessa annullata, il preventivo
  misto (§7.4) e la catena lunga.
* ⚠️ `gestione-resi` **non esiste**: il reso e' raccontato in `gestione-ddt` §11-bis, e il «torna da
  accreditare» sta li'.
* `api_commessa_stato.md` (l'annullo con la conferma, `GET …/legami/`), `api_ordini.md`,
  `api_preventivi.md`, api.md (inventario), i due cataloghi BB.

## 10. Trovato nel collaudo (2026-10-12): la commessa annullata non lascia libero il documento

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-12, dal collaudo a video di Tid. **A chi:** team
> DB. Letto sulla doc auto-generata e sul codice, non sui dati: il caso di dbdev e' il controesempio, non
> il motivo (§10.1).

### 10.1 Il controesempio

Tid, collaudo del §6.4: PRV0000398 (id 50012), di nuovo ACCETTATO dopo l'annullo della commessa 55666,
si rimanda in commessa. `POST /api/v1/vendite/preventivi/50012/push-commessa/` risponde 422
`E_COMMESSA_PUSH_PARZIALE_VIETATO` («nessuna riga inviata»); sotto, nel log di Gunicorn, il DB:

```text
vendite.fn_link_commessa_sorgente  E_COMMESSA_SORGENTE_ALTRA_COMMESSA
La sorgente e' gia' collegata a un'altra commessa (id 55666): una sorgente puo' appartenere a una sola commessa.
```

Fatto datato (dbdev, 2026-10-12, letto nel perimetro dell'utente che vede la commessa): 55666 e'
`ANNULLATA`, ha una riga sola, `ANNULLATA`; `vendite.fn_preventivo_ha_residuo_commessa(50012)` e' `true`;
in `vendite.commesse_sorgenti` resta il link `PREVENTIVO 01a12b84-… → 55666`, ruolo `ROOT`.

⚠️ 55666 e' stata annullata il 2026-10-11, **prima** del verbo, e sistemata a mano col D-9. Ma il difetto
non e' del dato: il verbo nuovo lascerebbe lo stesso link (§10.2).

⭐ **Lo stesso con l'ordine** (Tid, collaudo del 2026-10-12): ordine mandato in commessa, commessa annullata
dal verbo nuovo con la finestra, secondo invio dell'ordine: stesso errore. E' il caso costruito, non un
residuo: conferma che il difetto e' della forma, per ogni sorgente.

### 10.2 Il difetto, sul modello

* `vendite.commesse_sorgenti` ha `uq_commesse_sorgenti_src_uid (sorgente_tipo_id, sorgente_uid)`: un
  documento sta in **una** commessa, **per sempre**. `fn_link_commessa_sorgente` lo fa valere con un
  lookup globale, senza guardare lo stato della commessa del link che trova.
* Nella doc auto-generata l'**unico** scrittore della tabella e' `fn_link_commessa_sorgente`, e solo in
  inserimento (con l'`UPDATE` del `meta` nel ramo idempotente). Nessuna funzione la libera:
  ne' `vendite.fn_annulla_commessa`, ne' `vendite.fn_documento_ritira_legami`, ne'
  `vendite.fn_ritira_commessa_attivita_da_sorgente` (che ritira le righe di `commesse_attivita`, non il
  link).
* Il link lo scrive l'handler **base** del push (`BaseSourceHandler`, `commesse_source_handlers.py`),
  quindi vale per **tutte** le sorgenti: preventivo, ordine, contratto, bolla, consumi.
* **Da dove viene la rigidita'**: [brief-db-commesse-multi-sorgente](../work-done/brief-db-commesse-multi-sorgente.md)
  §2.3 lasciava al team DB «una sorgente sta in una sola commessa», e il `20260609-10` l'ha fatta vincolo
  (UNIQUE senza ruolo). Era scritta per impedire che un documento stesse in **due commesse vive**; l'annullo
  della commessa (questo brief) non c'era ancora. La regola resta giusta per le commesse vive: e' il
  vincolo che non distingue una commessa morta.
* ⚠️ **Non e' l'eccezione del §1.1.** Il D-8 dice che il documento a **monte** si annulla con la conferma
  anche se ha righe in una commessa viva, proprio perche' l'alternativa sarebbe annullare l'**intera**
  commessa (righe di altri documenti comprese). Non dice che la commessa non si annulla: l'annullo della
  commessa e' D-1/D-2, e il suo solo limite sono le righe EMESSE (D-3).

**Effetto:** dopo l'annullo della commessa il documento risulta «da mandare» per tutti i lettori del
residuo (D-5 ha liberato i segmenti: e' giusto), ma il push lo rifiuta, perche' il documento e' ancora
agganciato alla commessa morta. Il D-1 («di nuovo smistabile») e il D-5 sono veri a meta'; per l'ordine
il §7.4 («le righe dell'ordine tornano da mandare») anche.

⛔ **Perche' i pgTAP del §8 erano verdi:** provano il residuo (`fn_preventivo_ha_residuo_commessa`, le
`fn_list_*_da_pushare`) dopo l'annullo, non un **secondo invio vero**. E' il «verde per sottrazione»
di AGENTS.md: la prova si ferma un passo prima del punto in cui il caso si distingue.

### 10.3 Cosa si chiede al team DB

| # | Cosa | Note |
| --- | --- | --- |
| **R-13** | Dopo l'annullo di una commessa, un documento che vi aveva spinto righe si deve poter rimandare in commessa (una commessa nuova, o un'altra viva). La forma la sceglie il team DB sul codice | due strade viste dalla sessione BE, nessuna decisa: (a) il verbo di annullo **libera** il link (lo cancella); (b) il link **resta** come storia, e l'unicita' e il lookup di `fn_link_commessa_sorgente` contano solo i link verso commesse non abortite. ⚠️ Con (b) l'indice unico com'e' non basta (non puo' leggere lo stato della commessa): serve uno stato sul link, o un'altra chiave. ⚠️ Con (a) si perde l'arco storico che leggono lineage e passaggi (`fn_documento_lineage_archi`, `vw_documento_lineage_archi`): va deciso se il lineage di un documento deve ancora mostrare la commessa annullata |
| **R-14** | Censire i lettori di `commesse_sorgenti` e dire per ognuno se un link verso una commessa annullata deve contare | dalla doc auto-generata: `fn_build_gruppo_fatturabile_key`, `fn_get_sorgente_documento_ref`, `fn_genera_ddt_riconsegna`, `fn_emit_attivita_fatturabili_da_commessa`, `trgfn_commesse_sorgenti_guard_emittente`, `fn_documento_lineage_archi` / `vw_documento_lineage_archi`, `trgfn_guard_fatturazione_immediata_immutabile`, `script.trgfn_guard_sorgente_polimorfa_tipizzata` / `_testuale`, `script.fn_check_sorgente_chiudibile`, `script.fn_check_preventivo_annullabile`, `script.fn_check_ordine_annullabile` (gli ultimi due col COMMENT gia' stantio, R-12). Lato backend: §10.4 |
| **R-15** | pgTAP fabbricati del **giro completo**: invio, annullo della commessa con la conferma, **secondo invio riuscito** (in una commessa nuova), per preventivo e ordine almeno; e il preventivo misto (§7.4) | la prova che il §8 non faceva. Anche: il secondo invio nella **stessa** commessa, se viva (un altro documento l'ha tenuta aperta?), dove il ramo idempotente di `fn_link_commessa_sorgente` oggi riaggancerebbe senza errore |

**I dati di dbdev** (55666 e le altre commesse annullate col link ancora attaccato): li decide Tid, come
D-9, a forma scelta. Con la strada (a) e' una `DELETE` dei link verso commesse `ANNULLATA`; con la (b)
nessun intervento.

### 10.4 Ricaduta BE (dopo la consegna DB)

* `CommesseRepository.get_commessa_id_by_sorgente` legge `commesse_sorgenti` senza filtro di stato e con
  `LIMIT 1`: lo usa `preventivi_service._aggancia_commessa_servizi_a_pratica` dopo l'invio. Con la strada
  (b) potrebbe agganciare alla pratica la commessa **annullata** invece della nuova: va allineato alla
  regola del DB (meglio, letto da una funzione DB, non da una `SELECT` del backend).
* Lo smoke `smoke-test-ordini-giro-commessa.sh` ha gia' il passo 14 (secondo invio dopo l'annullo, atteso
  `COMPLETATO`): oggi deve fallire, ed e' il presidio HTTP del §10.

### 10.5 ❓ Domanda aperta, da vedere con il team DB (Tid, 2026-10-12)

Nata dalla lettura del §10 nella sessione BE. **Non e' una decisione**: Tid la porta al team DB, e la
forma di R-13 dipende dalla risposta.

**La domanda:** la commessa si deve poter annullare quando ha righe **vive** (NON_EMESSA) spinte da un
documento, o solo quando non ne ha (oneri, o nessuna riga viva)?

**Gli elementi, distinti per natura:**

* ✅ **Scritto nel modello, per la riga.** Il guard 4 di `vendite.fn_annulla_commessa_attivita` («per una
  riga da push il rimedio e' SEMPRE a monte, sul documento, sia essa emessa o no») rifiuta l'annullo di
  **una** riga che viene da un documento. Riguarda la riga singola, non la commessa intera.
* ✅ **Scritto nel modello, per la commessa.** La commessa e' un contenitore trovato o creato dal push
  (`fn_get_or_create_commessa`, per cliente, utility e competenza) che raccoglie righe di N documenti
  diversi, piu' oneri e rettifiche (§7.3). Il suo annullo oggi e' D-1/D-2, con il solo limite delle righe
  EMESSE (D-3).
* ✅ **Scritto, per il documento.** Il D-8 (§1.1): il documento a monte si annulla con la conferma anche
  con righe in una commessa viva, perche' l'alternativa sarebbe annullare l'intera commessa.
* ✅ **Storia.** La decisione del 2026-06-28 di
  [brief-db-push-commessa-gia-inviato](../work-done/brief-db-push-commessa-gia-inviato.md) §5: «instradata
  = esclusa»; il flusso «annulla attivita' e ri-pusha» e' «da progettare a parte». Il D-5 di qui l'ha
  sostituita in parte (le righe, non il link: §10.2).
* ⚠️ **Deduzione della sessione BE, non scritta da nessuna parte:** annullare la commessa porta ad
  ANNULLATA, in un colpo solo, proprio le righe da push che il guard 4 non lascia togliere una alla volta,
  quindi cambia lo stato di N documenti con un gesto solo a valle. Se vale, la commessa si annulla solo
  senza righe vive da documento, e il «rimandare in un'altra commessa» diventa un verbo sul **documento**
  («ritira dalla commessa»: righe ANNULLATA, link libero, documento di nuovo da mandare).
* ⚠️ Tid ricorda un'indicazione del team DB (10-12 ottobre) contraria all'annullo della commessa, per lo
  stesso motivo (righe di piu' documenti). **Non trovata** nei brief, nei commit di `dev/db-tid` ne' nei
  file non committati di questa copia: da ritrovare con il team DB.

**Se la risposta e' «solo senza righe vive da documento»**, si rivedono (lato BE/FE niente e' committato):
D-1, il ramo `COMMESSA` di `vendite.fn_documento_legami` e del verbo, la finestra del drawer della
commessa, la parte rettifica e consumi di D-7. Il D-5 resta: serve anche al verbo sul documento. R-13 si
restringe al verbo sul documento.

**Se resta l'annullo della commessa com'e'**, R-13…R-15 restano come scritti.
