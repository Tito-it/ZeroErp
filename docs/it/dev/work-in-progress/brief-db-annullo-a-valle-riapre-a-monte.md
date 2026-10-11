# Brief DB — Tornare indietro: annullare a valle riapre a monte, con la segnalazione

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11, dal collaudo a video di Tid. **A chi:**
> team DB; poi BE/FE (§6).
> **Stato:** 📝 **aperto.** Decisioni D-1…D-4 prese da Tid il 2026-10-11 (§4). Tocca al team DB.
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

## 1. Il principio (Tid, 2026-10-11)

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

## 2. Il caso che manca: annullare la commessa

La commessa e' a valle di preventivo, ordine, contratto e bolla (le righe spinte, `commesse_attivita`
con `sorgente_tipo_id` / `sorgente_uid`). Annullarla oggi (`vendite.fn_cambia_stato_commessa(…,
'ANNULLATA')`) non riapre niente e non segnala niente.

**Il caso misurato** (collaudo di Tid, dbdev, 2026-10-11): PRV0000398 (rev. 0, id 50012) smistato per
intero nella commessa `CMM-PGTAPEF202-2026-000000008` (id 55666), poi la commessa annullata.

| Cosa | Oggi | Atteso |
| --- | --- | --- |
| finestra di conferma | nessuna | l'elenco di cio' che si riapre |
| la riga di commessa del preventivo | NON_EMESSA, dentro una commessa ANNULLATA | ritirata (ANNULLATA) con la commessa |
| PRV0000398 | EVASO, nessuna azione | **ACCETTATO**, riga di nuovo da smistare (D-1) |
| `vendite.fn_preventivo_ha_residuo_commessa(50012)` | `false` | `true` |
| `vendite.fn_documento_legami('PREVENTIVO', 50012)` | 1 legame COMMESSA verso la commessa annullata | 0 |

Il lineage e' corretto nei due versi (dal preventivo si vede la commessa e viceversa): il difetto e' nel
modello, non nella lettura.

⚠️ **Ordine → commessa, da verificare nello stesso giro** (Tid): l'ordine passa a `EVASO` quando il push
a commessa e' completo (guida `gestione-ordini` §4.2). Annullando la commessa l'ordine deve tornare
`CONFERMATO`, con le righe di nuovo da spingere. Stessa domanda per contratto e bolla, dove il push ha
effetti sul documento a monte: il team DB la legge sul modello, documento per documento.

## 3. La verifica dell'«in avanti»

Il principio vale solo se e' vero su **tutti** gli archi. Il team DB verifica, sul catalogo e sulle
`fn_check_*_annullabile`, che il documento a monte non si annulli con un documento a valle vivo, per
ciascuno: preventivo (ordine vivo, commessa), offerta (contratto e ordine vivi), ordine (bolla viva,
commessa), contratto (commessa), commessa (fattura: righe emesse). Dove manca, lo segnala qui prima di
scrivere: e' una decisione di Tid, non un'aggiunta automatica.

⚠️ Un punto da guardare insieme: oggi un preventivo **ACCETTATO** con righe in commessa non ancora emesse
si annulla CON CONFERMA ritirando quelle righe (D-5 di brief-db-annullo-documento-con-legami, collaudo
a video ancora da fare su PRV0000144). Se l'«in avanti bloccato» deve valere anche per la commessa, quel
caso diventa un blocco. Il team DB lo mette davanti a Tid, non lo cambia da solo.

## 4. Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Annullare la commessa ritira le sue righe NON_EMESSA e riapre i documenti che le hanno spinte (preventivo EVASO → ACCETTATO con residuo commessa riaperto; ordine EVASO → CONFERMATO; contratto e bolla dove si applica)? | ✅ **si'**: «deve tornare accettato, la logica all'indietro e' la stessa che da ordini verso DDT» |
| **D-2** | Con la forma comune: avviso `E_DOC_ANNULLO_CON_LEGAMI`, `vendite.fn_documento_legami('COMMESSA', id)`, verbo `vendite.fn_annulla_commessa(id, legami_confermati)`? | ✅ **si'**: un unico meccanismo |
| **D-3** | Le righe gia' EMESSE bloccano l'annullo della commessa? | ✅ **gia' cosi'** (verificato il 2026-10-11): `script.fn_check_commessa_annullabile`, motivo `RIGHE_EMESSE`, codice `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`, sede unica di guard e capability. Il verbo nuovo la lascia parlare **prima** della conferma (prima cio' che vieta, poi cio' che chiede conferma) |
| **D-4** | I dati gia' rimasti indietro (commesse annullate con righe NON_EMESSA, es. 55666 e 113)? | ✅ **non serve**: sono dati di test. Nessun ritiro una tantum |

## 5. Cosa si chiede al team DB

| # | Cosa | Note |
| --- | --- | --- |
| **R-1** | `vendite.fn_documento_legami('COMMESSA', id)`: i documenti che si riaprono (preventivo, ordine, contratto, bolla), uno per legame, natura CONSUMO | lo stesso lettore di avviso, conferma e finestra |
| **R-2** | L'avviso `E_DOC_ANNULLO_CON_LEGAMI` montato anche sulla commessa (BB `vendite.trgfn_doc_guard_annullo_con_legami`, fascia `_m10_`, dopo `trgfn_commesse_guard_transizione`) | in avanti parla prima `fn_check_commessa_annullabile` |
| **R-3** | Verbo `vendite.fn_annulla_commessa(p_commessa_id, p_legami_confermati)`: perimetro, conferma e ritiro (BB `vendite.fn_documento_ritira_legami`), cambio di stato, riproiezione dello stato dei documenti a monte | preventivo EVASO → ACCETTATO (l'arco esiste, `manuale = false`); ordine EVASO → CONFERMATO (arco da verificare in matrice) |
| **R-4** | ⚠️ Il lettore ignora le commesse abortite | oggi `fn_documento_legami('PREVENTIVO', 50012)` conta un legame verso una commessa ANNULLATA. Con R-3 non succede piu' per questa strada, ma il lettore deve dirlo da se', o due sedi risponderanno in modo diverso al primo caso che ci arriva per un'altra strada |
| **R-5** | La verifica dell'«in avanti» (§3), con l'elenco degli archi e cosa li blocca | prima di scrivere |
| **R-6** | pgTAP fabbricati: commessa da preventivo (EVASO → ACCETTATO), da ordine (EVASO → CONFERMATO), con righe emesse (bloccata), senza legami (passa senza conferma), conferma sbagliata | i dati di dbdev non bastano: si costruiscono |

## 6. Ricaduta BE/FE (dopo la consegna DB)

* Backend: `GET /vendite/commesse/<id>/legami/` dalla factory `build_legami_view`; l'annullo della
  commessa (`/stato/` verso ANNULLATA) dal verbo, con `legami_confermati` (BB `_annullo_con_legami`).
* Frontend: `CommessaGestioneDrawer` passa il cambio di stato verso ANNULLATA da `useForzaturaConfermata`
  e mostra `DocumentoAnnulloLegamiDialog` (`base-path="/vendite/commesse"`), come bolla, ordine,
  preventivo e contratto. Lo store avvisa i tab con `avvisaDocumentiCollegati`.
* Guide: `gestione-commesse` «Annullare una commessa», e il rimando da ordini e preventivi.
* Collaudo a video: PRV0000398 (o un preventivo nuovo) smistato in commessa, commessa annullata con la
  finestra, preventivo di nuovo ACCETTATO; lo stesso da un ordine.
