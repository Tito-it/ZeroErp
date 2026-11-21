# Brief DB — Annullare un documento con legami: si riapre l'origine, con conferma

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-11. **A chi:** Tid; poi BE/FE (§6, che sostituisce il §3.4).
> **Origine:** il caso bolla → ordine trovato nel giro di
> [brief-db-ddt-righe-evase-dall-ordine](brief-db-ddt-righe-evase-dall-ordine.md) (§7.6, decisione D-8),
> e la domanda di Tid del 2026-10-11: *«quando esiste un legame, ci sia la conferma: abbiamo altri
> legami simili per cui segnalare "attenzione, si riapre qualcosa"?»*
> **Stato (2026-10-11):** ✅ **caso 1 (bolla) applicato e verde** (§3, changeSet del giro D28, applicati
> da Tid il 2026-10-11, pgTAP senza regressioni). ✅ **Casi 2-5 applicati e verdi** (§8: `20261011-68 … -91`
> + tre CSV, applicati da Tid il 2026-10-11, pgTAP verdi; decisioni D-1…D-6 di Tid, §5), con la forma
> comune (D-4) che riallinea anche la bolla. **Lato DB chiuso.** ✅ **Lato BE/FE fatto il 2026-10-11**
> (§9, R-1…R-6), provato sul DB vero. ✅ **Collaudo di Tid superato. Chiuso e archiviato il 2026-10-11**
> (§11). Il caso 6, l'annullo della commessa, e' diventato il brief D30 (§10).
> **Nel registro dei difetti DB:** voce **D29** di `migliorie-generali-da-test-valutazione.md`, che rimanda
> qui.

## 1. Il principio (Tid, 2026-10-11)

Un documento «a valle» nasce consumando qualcosa di un documento «a monte»: la bolla una quantita'
dell'ordine, l'ordine le righe del preventivo, il contratto l'offerta. Se il documento a valle si
**annulla**, quella cosa deve **tornare disponibile** a monte, altrimenti resta consumata per merce mai
partita o per un contratto mai nato. E non in silenzio: chi annulla vede **che cosa si riapre** e
**conferma**.

## 2. Il censimento (sugli archi del lineage, `vendite.vw_documento_lineage_archi`)

| # | Legame (monte → valle) | Dove sta | Se il documento a valle si annulla, oggi | Esito |
| --- | --- | --- | --- | --- |
| 1 | **Ordine → bolla**, **reso → bolla di ri-consegna** | `ordini_righe_fulfillment`, `resi_righe_riconsegne` | ritiro dei legami **con conferma** (§3) | ✅ caso 1, scritto |
| 2 | **Preventivo → ordine** | `ordini_righe.preventivo_riga_id` | l'ordine si annulla (DRAFT o CONFERMATO → ANNULLATO), ma le sue righe continuano a «occupare» le righe del preventivo (`vw_preventivi_righe_smistabili_ordine` non guarda lo stato dell'ordine). Il preventivo resta EVASO, e la matrice non ha EVASO → ACCETTATO | 🔴 consumato per sempre |
| 3 | **Offerta → contratto** | `contratti.offerta_id` | il contratto si annulla (DRAFT → ANNULLATO), ma `fn_push_offerta_a_contratto` rifiuta se esiste **un qualunque** contratto dell'offerta, anche annullato | 🔴 consumata per sempre |
| 4 | **Offerta → ordine** | `ordini.documento_origine_tipo/_id` | idem: il push rifiuta se esiste un ordine dell'offerta, anche annullato | 🔴 consumata per sempre |
| 5 | **Preventivo / ordine / contratto / bolla → commessa** | `commesse_attivita` (`segment_key`), `commesse_sorgenti` | gia' regolato (strada A): alla chiusura le righe NON_EMESSA si **ritirano** (`trgfn_doc_ritira_commessa_attivita`), le EMESSA **bloccano** con una via d'uscita (`script.fn_check_sorgente_chiudibile`, «Riporta da emettere») | 🟡 corretto ma **silenzioso** |
| 6 | **Commessa ← preventivo / ordine / contratto / bolla** (si annulla la COMMESSA) | `commesse_attivita` (`sorgente_tipo_id`, `sorgente_uid`) | la commessa va ad ANNULLATA (`fn_cambia_stato_commessa`), ma le sue righe NON_EMESSA restano tali, il documento che le ha spinte resta consumato (preventivo EVASO, residuo commessa `false`) e `fn_documento_legami` continua a contare il legame verso la commessa morta. Trovato nel collaudo di Tid del 2026-10-11 (§10) | 🔴 consumato per sempre |
| — | Bolla → reso; reso → fattura (accrediti) | `resi`, `resi_righe_accrediti` | l'annullo del reso e' **bloccato** se ci sono ri-consegne o accrediti (`fn_annulla_reso`) | ✅ niente si riapre in silenzio |
| — | Commessa → fattura; fattura → nota di credito | fatturazione | si corregge con la nota di credito, non annullando | ⚪ fuori dal principio |

Le revisioni di offerta e preventivo sono successioni dello stesso documento, non legami fra documenti:
fuori. ⚠️ I casi 2-4 sono letti dal contratto (viste, verbi, matrici), non ancora fabbricati in un pgTAP:
il primo passo di ciascuno e' il test che li costruisce.

## 3. Caso 1 — La bolla con legami (D-8 di brief-db-ddt-righe-evase-dall-ordine): fatto

> ⚠️ **Riallineato il 2026-10-11 dalla forma comune (D-4, §7-§8).** Restano: il BB del ritiro di una
> riga, il guard e il lock dei legami, il verbo `fn_annulla_ddt`. Cambiano: il lettore
> (`vendite.fn_ddt_legami` → `vendite.fn_documento_legami('DDT', id)`), il codice
> (`E_DDT_ANNULLO_CON_LEGAMI` → `E_DOC_ANNULLO_CON_LEGAMI`), l'avviso (la Regola 4 → il guard comune
> `_m10_`), la porta (GUC `zeroerp.ddt_annullo` → `zeroerp.doc_ritira_legami`), la conferma (le righe
> legate → i legami visti). Le tabelle qui sotto raccontano il giro D28 com'era.


### 3.1 Il caso, in semplice

Ordine 10 pippo, bolla generata con 10: l'ordine e' EVASO. La bolla si annulla (era sbagliata, il
camion non e' partito). Prima: il legame restava, l'ordine restava EVASO per 10, e una bolla nuova
dall'ordine veniva rifiutata (niente da evadere). Con la bolla emessa, il magazzino aveva gia' stornato
l'uscita: il magazzino diceva «la merce e' qui», l'ordine «la merce e' partita».

### 3.2 La regola (D-8)

* Annullare una bolla **ritira i suoi legami** (fulfillment e ponte di ri-consegna), come la
  cancellazione in bozza (D-3 di brief-db-ddt-righe-evase-dall-ordine): l'ordine si riproietta, il reso torna da ri-consegnare.
* ⚠️ **Mai in silenzio.** Se la bolla ha legami, l'annullo diretto e' **rifiutato** con un codice che
  dice quante righe sono legate (E_DDT_ANNULLO_CON_LEGAMI): e' l'avviso. L'annullo vero passa da un verbo
  in cui chi conferma **dichiara** quante righe legate ha visto (stampo di E_CREDENZIALE_DA_CONFERMARE:
  «chi conferma dichiara cio' che ha visto»). Se nel frattempo il numero e' cambiato, il verbo rifiuta
  con lo stesso codice, e la finestra si ripresenta aggiornata.
* Una bolla **senza** legami si annulla come oggi, senza finestra.

### 3.3 La forma

| Oggetto | Cosa |
| --- | --- |
| `vendite.fn_ddt_legami(p_ddt_id)` | ⭐ i legami della bolla, riga per riga (origine ordine/reso, riga d'origine, quantita'; il nome del documento lo da' il lineage). Sede unica: lo legge il guard (per contare), il verbo (per contare e ritirare) e il backend (per la finestra di conferma) |
| BB `vendite.fn_ddt_riga_ritira_legami(p_ddt_riga_id)` | ⭐ il ritiro dei legami di UNA riga, con la porta e la riproiezione dell'ordine. Regola del 2: lo chiamano la cancellazione in bozza (`trgfn_dlt_block_ordrig_ddtrig`, D-3) e l'annullo (D-8) |
| `vendite.trgfn_ddt_guard_transizione`, Regola 4 | `→ ANNULLATO` con legami ancora presenti → **E_DDT_ANNULLO_CON_LEGAMI** (CONFLITTO_STATO; valori: etichetta, numero di righe legate). E' l'avviso, per ogni strada (UPDATE diretto del backend o verbo di stato) |
| verbo `vendite.fn_annulla_ddt(p_ddt_id, p_righe_legate_confermate)` | SECURITY DEFINER. Conferma che non corrisponde → E_DDT_ANNULLO_CON_LEGAMI. Poi ritira i legami di ogni riga (porta dell'annullo: GUC `zeroerp.ddt_annullo` = id della bolla E proprietario) e chiama `vendite.fn_cambia_stato_ddt(…, 'ANNULLATO')`, che fa il resto come oggi (permesso `emetti_ddt` sull'annullo di una emessa, storno del magazzino) |
| guard del legame (`20261011-14`) | il DELETE di un legame passa per la porta del ritiro (GUC sulla riga) **solo se la bolla e' in bozza** (o e' stata appena cancellata); fuori bozza solo con la porta dell'annullo, dal proprietario |
| lock dei legami (`20261011-15`) | resta su INSERT e UPDATE; il DELETE lo governa il guard del legame, che sa distinguere le due madri |

### 3.4 Ricaduta BE/FE

✅ **Fatta il 2026-10-11**: il dettaglio sta in brief-db-ddt-righe-evase-dall-ordine §10 (endpoint
`GET …/ddt/<id>/legami/`, `cambia-stato` verso ANNULLATO sempre da `fn_annulla_ddt`, `confirm_and_retry`,
finestra `DdtAnnulloLegamiDialog`, guida §4.3). ✅ Collaudo di Tid superato il 2026-10-11: il caso 1 è chiuso.

* Il cambio di stato verso ANNULLATO, se riceve **E_DDT_ANNULLO_CON_LEGAMI**, apre una finestra di
  conferma che elenca le righe legate (da `vendite.fn_ddt_legami`: «riga 1, ordine 12, 10 pz»). Alla
  conferma: `SELECT * FROM vendite.fn_annulla_ddt(ddt_id, <righe viste>)`.
* Codice nuovo con policy (409, `ui_action` di conferma) e frase di ripiego.
* Guida `gestione-ddt`: «Annullare una bolla da ordine o da reso» (le quantita' tornano da spedire).

### 3.5 Consegna DB (2026-10-11)

| NN | Oggetto | Cosa |
| --- | --- | --- |
| `20261011-20` | `vendite.fn_ddt_legami(p_ddt_id)` | i legami riga per riga: `ddt_riga_id`, `riga_nr`, `origine` (ORDINE/RESO), `origine_riga_id`, `qta`. Niente etichette: il nome del documento d'origine lo da' il lineage (decisione di Tid: il lineage risponde a «da quali documenti viene la bolla», a livello di testata; qui serve la riga) |
| `20261011-16` | BB `vendite.fn_ddt_riga_ritira_legami(p_ddt_riga_id)` | il ritiro di una riga (porta, DELETE dei due legami, riproiezione degli ordini), condiviso da cancellazione in bozza e annullo |
| `20261011-14` | guard del legame | sul DELETE la porta del ritiro vale solo con la bolla in bozza (o appena cancellata); fuori bozza serve anche la porta dell'annullo (`zeroerp.ddt_annullo` = id della bolla) dal proprietario |
| `20261011-15` | lock dei legami | INSERT e UPDATE: il DELETE lo governa il guard, che sa distinguere le due madri |
| `20261011-34` | `vendite.trgfn_ddt_guard_transizione`, Regola 4 | l'avviso: verso ANNULLATO con righe legate → E_DDT_ANNULLO_CON_LEGAMI (valori: etichetta, righe legate). Corpo dal vivo, `SECURITY INVOKER` esplicito |
| `20261011-35` | verbo `vendite.fn_annulla_ddt(p_ddt_id, p_righe_legate_confermate)` | SECURITY DEFINER: testata nel perimetro, conferma (dichiarazione del numero di righe legate), ritiro con la porta dell'annullo, poi `vendite.fn_cambia_stato_ddt(…, 'ANNULLATO')` (matrice, permesso `emetti_ddt`, storno del magazzino), di cui restituisce i movimenti |
| CSV | E_DDT_ANNULLO_CON_LEGAMI (CONFLITTO_STATO, id 1287) | frase: «%s ha %s righe che vengono da un ordine o da un reso: annullandola, quelle quantita' tornano da spedire. Serve una conferma.» |

**La prova** (su `zeroerp_ci`, transazione ritirata, da owner): il pgTAP nuovo e' **42/43** (il 43 e' il
rosso «da owner» dichiarato). Scenario H: annullo diretto rifiutato; conferma sbagliata rifiutata; conferma
giusta in bozza e da emessa (ordine di nuovo CONFERMATO); la porta del ritiro accesa a mano non toglie un
legame fuori bozza; una bolla senza legami si annulla come prima.

**Fixture rifatte per D-8** (annullavano con un UPDATE diretto una bolla nata da un ordine): ora passano da
`vendite.fn_annulla_ddt`, dichiarando le righe lette da `vendite.fn_ddt_legami`, e si concedono
`emetti_ddt`. `script/test-fn-available-actions-ddt-reason-catch-all-v1` gira tutto sullo scratch (16/1
come prima, il caso della bolla annullata passa dal verbo); `vendite/test-vw-stato-sorgente-ddt-reso-v1` e
`vendite/test-fn-list-ddt-da-pushare-orfano-v1` sullo scratch si fermano prima, come prima, per i dati: li
prova la corsa su dbdev.

**Regressione** (62 pgTAP, «prima» = il file in HEAD): nessuna regressione mia. Oltre ai file aggiornati per
contratto (§7.4 di brief-db-ddt-righe-evase-dall-ordine), due differenze che **non** vengono da questo giro: `script/test-doc-lock-montaggio-v1`
test 1 aspetta la chiave `codice` del `20261011-21` dell'altra sessione, e il rubinetto aspetta 37 (il mio
sito piu' il loro). Con tutti e due i giri applicati tornano.

## 4. I casi aperti (2026-10-11: chiusi dal disegno del §7, scritti nel §8)

### 4.1 Caso 2 — Preventivo → ordine

Annullare un ordine nato da un preventivo dovrebbe liberare le righe del preventivo che occupava, e
riportare il preventivo da EVASO ad ACCETTATO. Domande: le righe d'ordine annullate si **scollegano**
(`preventivo_riga_id` a NULL, il legame si ritira come in D-8) oppure lo **smistamento ignora** le righe di
un ordine annullato? E la matrice dei preventivi prende EVASO → ACCETTATO.

### 4.2 Casi 3 e 4 — Offerta → contratto, offerta → ordine

Un contratto (o un ordine) annullato non deve impedire una nuova trasformazione dell'offerta. Domanda: il
push guarda solo i documenti **vivi** (`is_abortito` dal vocabolario, come `fn_check_ordine_annullabile` e
il freno della commessa), e lo stato dell'offerta cambia all'annullo del documento nato da lei?

### 4.3 Caso 5 — Il ritiro dalla commessa, oggi silenzioso

La regola e' gia' giusta (strada A): manca solo la conferma. `script.fn_check_sorgente_chiudibile` sa gia'
quali righe si ritirano: l'avviso e la conferma si appoggiano li'.

## 5. Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | I casi 2-5 seguono il principio del §1 (si riapre, con conferma)? | ✅ **si'**, tutti e quattro |
| **D-2** | Caso 2: il legame si ritira (riga d'ordine scollegata) o lo smistamento ignora gli ordini annullati? | ✅ **strada A, il legame si ritira** (§5.1) |
| **D-3** | Casi 3-4: il push guarda solo i documenti vivi? L'offerta torna da trasformare? | ✅ **si'**, con `is_abortito` dal vocabolario |
| **D-4** | Una forma comune: un **lettore unico dei legami** per documento (il generale di `vendite.fn_ddt_legami`), un **codice unico di avviso** («annullandolo si riapre…») e un **verbo di annullo con conferma** per documento | ✅ **si'**: regola del 2, alla seconda finestra di conferma la prima diventa il building block (e la forma della bolla, §3, vi si riallinea nello stesso giro: niente copie accanto al BB) |
| **D-5** | Caso 5 (commessa): la regola c'e' gia', manca l'avviso. Stesso stampo degli altri o un avviso senza rifiuto? | ✅ **stesso stampo**: rifiuto con l'avviso, **conferma dichiarata** e **verbo** di annullo, come gli altri casi |
| **D-6** | Casi 3-4: `uq_contratti_offerta_id` (UNIQUE su `offerta_id`) e `uq_ordini_v_documento_origine_offerta` (UNIQUE sull'ordine da offerta) non vedono lo stato: col solo push filtrato (D-3) il secondo documento dalla stessa offerta sbatte sull'indice. Ritiro del legame o UNIQUE sui vivi? | ✅ **UNIQUE sui soli vivi** (§7.1): la provenienza resta sul documento annullato; sull'ordine nasce `is_abortito_snapshot`, come sul contratto |

### 5.1 D-2 in chiaro: perche' il ritiro

Annullando un ordine nato da un preventivo, le sue righe perdono `preventivo_riga_id` (torna NULL), come
la bolla perde i suoi legami in D-8; il preventivo torna da EVASO ad ACCETTATO (arco nuovo della matrice).

* **Il dato dice la verita'**: una riga di preventivo e' occupata solo se un ordine **vivo** la usa. Chi
  legge (oggi `vw_preventivi_righe_smistabili_ordine`, domani altri) non deve ricordarsi di escludere gli
  ordini annullati.
* **La struttura lo pretende**: `uq_ordini_righe_v_preventivo_riga` (UNIQUE parziale su
  `preventivo_riga_id IS NOT NULL`) dice «una riga di preventivo sta in una sola riga d'ordine». Con
  l'aggancio lasciato sull'ordine annullato, il secondo ordine dallo stesso preventivo sbatterebbe sul
  UNIQUE; per tenerlo servirebbe un guard scritto a mano «una sola riga d'ordine **viva**» (un indice non
  vede lo stato, che sta sulla testata). Col ritiro il UNIQUE resta com'e' e garantisce la regola giusta.
* **Il prezzo, accettato**: la riga dell'ordine annullato non dice piu' da quale riga del preventivo
  veniva. La testata lo dice ancora (`documento_origine_*`, e il lineage), quindi si perde il solo
  dettaglio riga per riga, su un documento morto.

### 5.2 Prossimo passo

Via di Tid il 2026-10-11 («puoi partire»), numeri dal `20261011-68`. Il disegno e' il §7.

## 7. Casi 2-5: il disegno (2026-10-11)

### 7.1 Consumo e provenienza

Il criterio che tiene insieme D-2 e D-6: **il consumo si ritira, la provenienza resta**.

| Legame | Natura | All'annullo |
| --- | --- | --- |
| fulfillment e ponte di ri-consegna della bolla | consumo (quantita' evasa) | si ritira (D-8) |
| `ordini_righe.preventivo_riga_id` | consumo (la riga di preventivo e' occupata) | si ritira (D-2); lo storico della riga ne tiene il valore |
| righe di commessa NON_EMESSA spinte dal documento | consumo | si ritirano (ANNULLATA, col registro: la primitiva di sempre) |
| `contratti.offerta_id`, `ordini.documento_origine_*` | **provenienza**: dice da dove viene il documento | resta; gli indici UNIQUE valgono sui soli vivi (D-6) |

Una provenienza non si ritira, ma **si conferma lo stesso** (D-1): annullando il contratto, l'offerta torna
trasformabile, e chi annulla lo vede.

### 7.2 La forma comune (D-4)

| Oggetto | Cosa |
| --- | --- |
| ⭐ `vendite.fn_documento_legami(p_documento, p_id)` | il lettore unico: una riga per legame (bolla, ordine, preventivo, contratto), con la natura (consumo o provenienza). Prende il posto di `vendite.fn_ddt_legami` |
| ⭐ BB `vendite.fn_documento_ritira_legami(p_documento, p_id, p_legami_confermati)` | la conferma (chi conferma dichiara quanti legami ha visto) e il ritiro di tutti i consumi; apre la porta del ritiro (`zeroerp.doc_ritira_legami` = `DOCUMENTO:id`) |
| BB `vendite.fn_doc_porta_ritiro_ammette(…)` | la porta, letta da chi blocca: il lock delle righe (per staccare `preventivo_riga_id` da un ordine confermato), il guard del legame della bolla, il guard dell'annullo. Vale solo per il proprietario della tabella (i verbi DEFINER) |
| guard `vendite.trgfn_doc_guard_annullo_con_legami`, fascia `_m10_` | l'avviso, su bolla, ordine, preventivo e contratto: entrare in uno stato `is_abortito` con legami → **E_DOC_ANNULLO_CON_LEGAMI**. Dopo i guard `_a10_` (matrice, righe di commessa EMESSA): prima parla cio' che vieta, poi cio' che chiede conferma. Prende il posto della Regola 4 della bolla |
| verbi `vendite.fn_annulla_ddt`, `fn_annulla_ordine`, `fn_annulla_preventivo`, `fn_annulla_contratto` | perimetro, BB, cambio di stato. Quello della bolla si riallinea al BB |
| `vendite.fn_offerta_documenti_vivi(p_offerta_id)` | i contratti e gli ordini **vivi** nati dall'offerta: lo leggono il push, la capability dell'offerta (e il backend, che oggi ne tiene uno specchio) |
| `E_DOC_ANNULLO_CON_LEGAMI` | il codice unico; `E_DDT_ANNULLO_CON_LEGAMI` si ritira (`obsoleto_dal`) |

Si ritirano anche: il ritiro automatico dalla commessa (`vendite.trgfn_doc_ritira_commessa_attivita` e i
suoi quattro trigger `_z90_`), che col guard non scatterebbe piu' (il ritiro lo fa il verbo, dopo la
conferma); `vendite.trgfn_contratti_sync_is_abortito_snapshot`, che diventa il BB
`vendite.trgfn_doc_snapshot_da_stato` montato su contratto e ordine (regola del 2).

### 7.3 Il preventivo torna ACCETTATO

Staccate le righe dell'ordine, un preventivo EVASO che ha di nuovo un residuo torna ACCETTATO: arco nuovo
EVASO → ACCETTATO (`manuale = false`) in `transizioni_stati_preventivi`, eseguito dal BB.

## 6. Ricaduta BE/FE (2026-10-11, dopo l'apply del §8; sostituisce il §3.4)

| # | Cosa | Dove | Note |
| --- | --- | --- | --- |
| **R-1** | **Una finestra di conferma sola**, per bolla, ordine, preventivo e contratto | il cambio di stato verso ANNULLATO (UPDATE diretto per ordine e contratto, `fn_cambia_stato_preventivo` per il preventivo, quello della bolla) | se il DB risponde **E_DOC_ANNULLO_CON_LEGAMI** (409, contesto `documento`, `id`, `legami`), la finestra legge `SELECT * FROM vendite.fn_documento_legami(<documento>, <id>)` ed elenca che cosa si riapre e dove («riga 1, preventivo 12, 4 pz»; «offerta 7 torna trasformabile»; «2 righe di commessa da emettere tornano annullate»). Il nome dei documenti per il gesto «vai al documento» dal lineage. La colonna `natura` distingue CONSUMO (si riapre) da PROVENIENZA (l'offerta torna trasformabile) |
| **R-2** | **Alla conferma, il verbo del documento** | `SELECT * FROM vendite.fn_annulla_ddt(id, n)` (movimenti), `SELECT vendite.fn_annulla_ordine(id, n)`, `fn_annulla_preventivo(id, n)`, `fn_annulla_contratto(id, n)` (i legami confermati) | `n` = quante righe la finestra ha mostrato. Se non corrisponde (legami cambiati nel frattempo) risponde lo stesso codice: la finestra si ripresenta aggiornata. Il permesso di annullare resta quello del BE (come per l'UPDATE diretto); la bolla emessa chiede `emetti_ddt` al verbo di stato |
| **R-3** | **Codice nuovo** `E_DOC_ANNULLO_CON_LEGAMI` | policy (409, `ui_action` di conferma) e frase di ripiego | `E_DDT_ANNULLO_CON_LEGAMI` si ritira (`obsoleto_dal` 2026-10-11) prima di essere arrivato al BE: non va mappato |
| **R-4** | **L'offerta non e' consumata da un documento annullato** | `ordini_service.crea_ordine_da_offerta` (guard specchio), `views_offerte` (dialog «gia' generato») | il controllo «l'offerta ha gia' generato un contratto/ordine» guarda i soli documenti VIVI: legga `vendite.fn_offerta_documenti_vivi(offerta_id)` invece di tenere uno specchio (regola del 2). La violazione di `uq_ordini_v_documento_origine_offerta` resta la rete sulla corsa, ora sui soli vivi |
| **R-5** | ⚠️ **`offerte_repository._FROM_JOINS_OFFERTA`: il LEFT JOIN sul contratto dava per scontato «0 o 1»** | `LEFT JOIN vendite.contratti c ON c.offerta_id = o.id` | con l'unicita' sui vivi un'offerta puo' avere un contratto annullato e uno vivo: la riga dell'offerta si DUPLICA. Va filtrato `AND NOT c.is_abortito_snapshot` (il contratto che il dialog mostra e' quello vivo). Da fare nello stesso rilascio dell'apply |
| **R-6** | Guide | `gestione-ddt` e le guide di ordini, preventivi, contratti | «Annullare un documento nato da un altro»: che cosa si riapre (quantita' da spedire, righe da ordinare, offerta da trasformare, righe di commessa), e che la finestra lo chiede. Il preventivo torna ACCETTATO quando un suo ordine si annulla |

## 8. Consegna DB dei casi 2-5 (2026-10-11): ✅ applicata da Tid e verde

### 8.1 I changeSet

| NN | Oggetto | Cosa |
| --- | --- | --- |
| `-68` | `uq_contratti_offerta_id` | da UNIQUE (offerta_id) a indice unico parziale sui contratti vivi (D-6); stesso nome |
| `-69` | `vendite.ordini.is_abortito_snapshot` | colonna nuova + allineamento delle righe, coi trigger della tabella spenti per il solo UPDATE (i trigger «padre attivo» controllano a ogni UPDATE: un ordine annullato su un termine di pagamento poi disattivato e' uno stato ammesso) |
| `-70` | `uq_ordini_v_documento_origine_offerta` | unico sui soli ordini vivi (D-6); stesso nome |
| `-71` | BB `vendite.trgfn_doc_snapshot_da_stato` | le bandiere dello stato copiate sulla riga, a ogni scrittura (regola del 2: prima copia sul contratto) |
| `-72` | trigger | montato su ordine e contratto; ritirata `vendite.trgfn_contratti_sync_is_abortito_snapshot` |
| `-73` | `vendite.fn_offerta_documenti_vivi` | i contratti e gli ordini vivi nati dall'offerta: sede unica (push, capability, backend) |
| `-74` | `vendite.fn_push_offerta_a_contratto` | i due guard «gia' generato» sui soli vivi (D-3) |
| `-75` | `script.fn_available_actions_offerta` | `can_push_contratto` / `can_genera_ordine` sui soli vivi |
| `-76` | `vendite.vw_dash_fatturazione_offerte` | il lettore che l'unicita' sui vivi rompeva: i figli dell'offerta in una riga per lato (esiste, vivo), niente duplicati ne' `LIMIT 1` arbitrario |
| `-77` | ⭐ `vendite.fn_documento_legami` | il lettore unico dei legami (D-4), SECURITY DEFINER perche' avviso, conferma e finestra contino la stessa cosa sotto la RLS |
| `-78` | BB `vendite.fn_doc_porta_ritiro_ammette` | la porta del ritiro (GUC `zeroerp.doc_ritira_legami` + proprietario + cosa il ritiro tocca) |
| `-79` | `vendite.trgfn_doc_righe_lock_fuori_bozza` | la porta prima del rifiuto: la riga d'ordine si stacca dal preventivo anche fuori bozza, solo dal verbo |
| `-80` | `vendite.trgfn_ddt_riga_legame_guard` | il DELETE fuori bozza dalla porta comune (via `zeroerp.ddt_annullo`) |
| `-81` | BB `vendite.trgfn_doc_guard_annullo_con_legami` | l'avviso: consumo presente → rifiuto sempre; sola provenienza → passa con la porta |
| `-82` | trigger `_m10_` | l'avviso su bolla, ordine, preventivo, contratto (dopo i guard `_a10_`) |
| `-83` | `vendite.trgfn_ddt_guard_transizione` | ritirata la Regola 4 |
| `-84` | ⭐ BB `vendite.fn_documento_ritira_legami` | conferma e ritiro dei consumi (bolla, ordine → preventivo con EVASO → ACCETTATO, commessa); lascia la porta aperta |
| `-85` | `vendite.fn_annulla_ddt` | riallineato al BB; il parametro diventa `p_legami_confermati` (DROP/CREATE: il BE non lo chiamava ancora) |
| `-86` `-87` `-88` | `vendite.fn_annulla_ordine` / `_preventivo` / `_contratto` | i tre verbi nuovi, SECURITY DEFINER: perimetro, BB, cambio di stato, porta chiusa |
| `-89` | `vendite.trgfn_doc_guard_chiusura_sorgente` | solo testo: non nomina piu' il motore che si ritira |
| `-90` | DROP `vendite.trgfn_doc_ritira_commessa_attivita` + 4 trigger `_z90_` | il ritiro automatico e silenzioso (D-5): col guard non scatterebbe piu' |
| `-91` | DROP `vendite.fn_ddt_legami` | il lettore della sola bolla (regola del 2) |
| CSV | `transizioni_stati_preventivi` | arco 9: EVASO → ACCETTATO, `manuale = false` |
| CSV | `codici_errore`, `messaggi_errore` | `E_DOC_ANNULLO_CON_LEGAMI` (CONFLITTO_STATO, id 1289); `E_DDT_ANNULLO_CON_LEGAMI` `obsoleto_dal` 2026-10-11 |

### 8.2 La prova (sullo scratch `zeroerp_ci`, da owner, transazione ritirata)

* **SQL estratto** dei 24 changeSet, in ordine, con le **preCondition** valutate ciascuna al suo punto:
  tutte vere. I CSV sono simulati con INSERT/UPDATE (il loader non e' provato qui).
* **pgTAP nuovo** `vendite/test-annullo-documento-con-legami-v1.sql`: **29/30**; il 30 e' il rosso
  «da owner» dichiarato (la GUC accesa a mano: da proprietario la porta si apre per costruzione, come il
  test 43 del caso 1). Costruisce i casi 2, 3, 4 e 5 dai builder e dai push veri.
* **Regressione** (stesso file prima e dopo, stesso scratch): 80 pgTAP che toccano annulli, legami,
  offerte, push e commessa, piu' 137 presidi trasversali (`dbops/`, `config/`, presidi di `script/`, fra
  cui riferimenti morti, rubinetto, catalogo dei messaggi, DEFINER): **nessuna regressione**. Le
  differenze sono i file aggiornati per contratto:
  * `vendite/test-ritiro-alla-chiusura-documento-v1` riscritto per D-5 (l'UPDATE nudo ora chiede conferma,
    il ritiro e' del verbo) e passato ai builder: **8/8**, e ora gira anche da zero (prima si fermava sui
    dati);
  * `config/test-costanti-catalogo-citate-dal-codice-v1` (test 5-6: i freni rimasti sono tre) 6/6;
  * `vendite/test-ddt-righe-evase-dall-ordine-v1` 42/43 (il 43 rosso da owner, come prima), e i tre file
    con le fixture della bolla annullata (`reason-catch-all` 16/1 come prima; `stato-sorgente-ddt-reso` e
    `list-ddt-orfano` sullo scratch si fermano prima per i dati, come prima) dichiarano ora i legami da
    `fn_documento_legami`.
* ⚠️ **Non provato qui**: l'esito come app (la RLS; il test 30) e i file che sullo scratch si fermano per i
  dati: li prova la corsa di Tid su dbdev. Ho riletto a mano quelli che annullano un documento
  (`fn-list-ordini-da-pushare-v3`, `vw-dash-backlog`, `vw-dash-fatturazione`, `fn-cambia-stato-preventivo`,
  `vw-situazione-merce-ordine`): annullano documenti senza legami, o inseriscono contratti gia'
  annullati, quindi l'avviso non li tocca.
* **Dopo l'apply (Tid, 2026-10-11, dbdev):** `script/test-capability-motivi-e-nessuna-azione-v1` si fermava
  al test 12 con E_DOC_ANNULLO_CON_LEGAMI. La fixture prende dai dati il primo ordine DRAFT annullabile e lo
  annullava con un UPDATE diretto: su dbdev quell'ordine ha un legame, e l'avviso l'ha fermato, com'e' giusto.
  Sullo scratch il ramo va in SKIP (nessun ordine), per questo la regressione non l'aveva visto. Fixture
  riallineata: passa da `vendite.fn_annulla_ordine` dichiarando i legami letti da `fn_documento_legami`,
  come gia' la gemella della bolla nello stesso file. Riletti gli altri file che annullano con un UPDATE
  diretto (`ordini-guard-transizione`, `testata-dopo-emissione`, `preventivi-approvazione-prezzo`,
  `seed-stati-doc-ordini-evaso`, `contratti-step23`, `fn-check-prezzi-autorizzati`): costruiscono
  documenti propri senza legami, l'avviso non li tocca.
* **Dopo l'apply (2):** `vendite/test-seed-stati-doc-preventivi-evaso-v1` test 4 fissava «da EVASO nessuna
  transizione»: e' la regola che D-2 cambia. Riscritto sul significato: da EVASO nessuna uscita MANUALE,
  una sola automatica verso ACCETTATO. 4/4 sullo scratch. ⚠️ Il gemello degli ordini
  (`script/test-seed-stati-doc-ordini-evaso-v1`, test 4 e 6) e' rosso da PRIMA di questo giro (5/2 sullo
  scratch prima e dopo): fissa la stessa regola, ma gli ordini hanno uscite automatiche da EVASO dal
  2026-07-09 (proiezione dell'evasione). Non e' di questo cantiere: riallineato a parte il 2026-10-11 (test 4:
  nessuna uscita manuale; test 6: `ORDINE_GIA_EVASO` tolto il 2026-07-10 da `20260710-02`): ✅ verde su dbdev (Tid, 2026-10-11).

### 8.3 Fatti da sapere prima dell'apply

* La FK `fk_contratti_offerta` perde la copertura per prefisso (l'indice sui vivi e' parziale su
  `is_abortito_snapshot`): la policy FK e' opt-in e la FK non e' a registro, come le altre del contratto.
* Il backend ha **due** lettori che davano per scontato «un'offerta, al piu' un contratto» (R-4, R-5 del
  §6): vanno nello stesso rilascio, o una seconda trasformazione duplica la riga dell'offerta.
* Le pagine `manual/` dei due oggetti ritirati si cancellano, e il loro contenuto passa in
  `trgfn_doc_snapshot_da_stato.md` e `trgfn_doc_guard_annullo_con_legami.md` (nuove, con
  `fn_documento_legami.md`).

## 9. Lato BE/FE (sessione backend, 2026-10-11)

> Non committato. Prove: suite `apps.core` + `apps.vendite` 3951 verdi; presidi sul DB vero
> (`test_error_codes_db_policy_guardrail`, `test_error_policies_divergenza_db`) verdi; ruff e mypy a
> cricchetto puliti; FE 608 test (`vendite` + `core`), `npm run guards`, lint e build verdi.

| # | Fatto |
| --- | --- |
| **R-1** | BB backend `services/_annullo_con_legami.py` (`legami_del_documento`, `legami_confermati`): legge `vendite.fn_documento_legami` e mette a ogni legame il nome del documento dall'altra parte, dal lineage nelle due direzioni. Factory `api/legami_views.build_legami_view`: `GET …/ddt|ordini|preventivi|contratti/<id>/legami/` → `{documento, id, legami, righe}`. Il service legge prima la testata (il lettore e' DEFINER). Finestra FE comune `vendite/_shared/annullo/DocumentoAnnulloLegamiDialog.vue` (+ `legamiApi.getLegami`, + spec), cablata con `useForzaturaConfermata` in `DdtDrawer`, `OrdiniDrawer`, `PreventiviDrawer` e `ContrattoDrawer` (negli ultimi due solo l'annullo: le altre transizioni restano su `execute`). ⭐ Regola del 2: `DdtAnnulloLegamiDialog`, `getDdtLegami` e `DdtRepository.list_legami` ritirati nello stesso giro |
| **R-2** | `cambia_stato` di bolla, ordine, preventivo e contratto: verso ANNULLATO chiama SEMPRE il verbo (`fn_annulla_ddt` / `_ordine` / `_preventivo` / `_contratto`) con `legami_confermati` dal corpo (assente al primo tentativo; non intero → 400 col campo). Il preventivo risponde con la forma di `fn_cambia_stato_preventivo`. La dichiarazione della bolla si chiamava `righe_legate_confermate` e contava le righe distinte: ora `legami_confermati`, il `count(*)` del lettore come il verbo. Dopo l'annullo gli store avvisano i tab di ordini, resi, preventivi, offerte (`avvisaDocumentiCollegati`) |
| **R-3** | Policy rigenerate dal catalogo (`E_DOC_ANNULLO_CON_LEGAMI`, e `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` di D27 arrivato nello stesso merge), override `confirm_and_retry` spostato sul codice nuovo, ripieghi per i due codici. Il ripiego di `E_DDT_ANNULLO_CON_LEGAMI` resta per il diario |
| **R-4** | `crea_ordine_da_offerta`: i due controlli specchio (ordine gia' nato, contratto gia' nato) diventano una lettura di `vendite.fn_offerta_documenti_vivi` (`OfferteRepository.list_documenti_vivi`). Il dialog «gia' generato» legge `contratto_id` del dettaglio, ora sui soli vivi (R-5) |
| **R-5** | `offerte_repository._FROM_JOINS_OFFERTA`: `LEFT JOIN vendite.contratti c ON c.offerta_id = o.id AND NOT c.is_abortito_snapshot` |
| **R-6** | Guide: `gestione-ddt` §4.3 (generalizzata), `gestione-ordini` §4.3 nuova, `gestione-preventivi` §3.2 nuova, `gestione-contratti` §3.1. Corretti nello stesso giro due archi stantii: CONFERMATO → ANNULLATO dell'ordine e EMESSO/ACCETTATO → ANNULLATO del preventivo erano dati «disabilitati», la matrice li ha attivi e manuali. Manuali API dei quattro documenti. Cataloghi BB backend e frontend |

**Prova sul DB vero** (dbdev, ruolo `zeroerp_app`, transazione ritirata), per bolla (generata da un
ordine), ordine (con righe di preventivo), preventivo (con righe di commessa da emettere) e contratto (da
offerta): legami letti coi nomi dal lineage; annullo senza conferma e con conferma sbagliata →
`E_DOC_ANNULLO_CON_LEGAMI`; con conferma giusta → ANNULLATO. Dopo l'annullo del contratto
`fn_offerta_documenti_vivi` non lo conta piu', l'offerta resta una riga sola e il suo dettaglio non mostra
il contratto annullato.

### 9.1 Trovato nel giro

* ⭐ **Difetto corretto, conseguenza di D-2:** `OrdiniRepository.get_ordine_by_documento_origine` (l'ordine
  nato dal preventivo, per l'esito dello smistamento `MERCE_PRESENTE` e per l'handler che aggancia l'ordine
  alla pratica) leggeva anche gli ordini annullati: con un preventivo il cui ordine e' stato annullato e poi
  rigenerato avrebbe preso quello morto (il primo per id). Ora legge i soli vivi (`NOT is_abortito_snapshot`).
* Il service del preventivo lascia arrivare l'errore del DB grezzo (lo traduce il middleware in HTTP), come
  prima per `fn_cambia_stato_preventivo`: in HTTP il codice e' quello giusto.
* Fuori da questo brief: `check_i18n_keys.py` e' rosso su `common.azione_reason.indirizzo_non_del_cliente`,
  emessa da `script.fn_check_indirizzi_documento_cliente` (D27, arrivato col merge): e' del lato BE/FE di
  brief-db-indirizzi-documento-seguono-il-cliente.

## 10. Caso 6 — Annullare la commessa: spostato

Trovato nel collaudo di Tid del 2026-10-11 (PRV0000398 smistato in commessa, commessa annullata: nessuna
finestra, il preventivo resta EVASO). Per decisione di Tid lo stesso giorno diventa un brief suo, che
generalizza il verso all'indietro («annullare a valle riapre a monte, con la segnalazione; in avanti
bloccato; un unico meccanismo»):
[brief-db-annullo-a-valle-riapre-a-monte](brief-db-annullo-a-valle-riapre-a-monte.md)
(D30). Le decisioni prese qui (D-7…D-10) sono passate la' come D-1…D-4. La forma di questo brief
(lettore, avviso, verbo, finestra) si riusa.

## 11. Chiusura (2026-10-11)

* **Lato DB**: casi 1-5 applicati e verdi (§3.5, §8).
* **Lato BE/FE**: R-1…R-6 fatti (§9), provati sul DB vero per bolla, ordine, preventivo e contratto.
* **Collaudo a video di Tid**: superato per bolla, ordine, contratto e documento senza legami. Il caso
  del preventivo ACCETTATO con righe in commessa non ancora emesse (PRV0000144) non e' stato provato a
  video: passa al collaudo del brief D30 (§3 la', dove la decisione «in avanti bloccato» puo' cambiarlo).
* **Il caso 6** (annullo della commessa) e' il brief D30 (§10).
* Registro dei difetti: **D29** chiusa (§7 di `migliorie-generali-da-test-valutazione.md`).
