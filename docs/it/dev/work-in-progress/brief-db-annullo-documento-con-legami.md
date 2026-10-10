# Brief DB — Annullare un documento con legami: si riapre l'origine, con conferma

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-11. **A chi:** Tid; poi BE/FE (§3.4, §6).
> **Origine:** il caso bolla → ordine trovato nel giro di
> [brief-db-ddt-righe-evase-dall-ordine](brief-db-ddt-righe-evase-dall-ordine.md) (§7.6, decisione D-8),
> e la domanda di Tid del 2026-10-11: *«quando esiste un legame, ci sia la conferma: abbiamo altri
> legami simili per cui segnalare "attenzione, si riapre qualcosa"?»*
> **Stato (2026-10-11):** ✅ **caso 1 (bolla) applicato e verde** (§3, changeSet del giro D28, applicati
> da Tid il 2026-10-11, pgTAP senza regressioni). ⬜ **Casi 2-5 aperti** (§4): decisioni attese da Tid (§5).
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
| — | Bolla → reso; reso → fattura (accrediti) | `resi`, `resi_righe_accrediti` | l'annullo del reso e' **bloccato** se ci sono ri-consegne o accrediti (`fn_annulla_reso`) | ✅ niente si riapre in silenzio |
| — | Commessa → fattura; fattura → nota di credito | fatturazione | si corregge con la nota di credito, non annullando | ⚪ fuori dal principio |

Le revisioni di offerta e preventivo sono successioni dello stesso documento, non legami fra documenti:
fuori. ⚠️ I casi 2-4 sono letti dal contratto (viste, verbi, matrici), non ancora fabbricati in un pgTAP:
il primo passo di ciascuno e' il test che li costruisce.

## 3. Caso 1 — La bolla con legami (D-8 di brief-db-ddt-righe-evase-dall-ordine): fatto


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

## 4. I casi aperti

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

## 5. Decisioni attese da Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | I casi 2-5 seguono il principio del §1 (si riapre, con conferma)? | ✅ si' |
| **D-2** | Caso 2: il legame si ritira (riga d'ordine scollegata) o lo smistamento ignora gli ordini annullati? | ritiro, come D-8: il dato dice la verita' senza che ogni lettore debba filtrare |
| **D-3** | Casi 3-4: il push guarda solo i documenti vivi? L'offerta torna da trasformare? | si', con `is_abortito` dal vocabolario |
| **D-4** | Una forma comune: un **lettore unico dei legami** per documento (il generale di `vendite.fn_ddt_legami`), un **codice unico di avviso** («annullandolo si riapre…») e un **verbo di annullo con conferma** per documento | si': regola del 2, alla seconda finestra di conferma la prima diventa il building block; senza, cinque finestre scritte in cinque modi |

## 6. Ricaduta BE/FE (quando i casi 2-5 sono fatti)

* Una finestra di conferma sola, guidata dal codice di avviso e dal lettore dei legami: elenca che cosa si
  riapre e dove («riga 1, ordine 12, 10 pz»), col gesto «vai al documento» dal lineage.
* Per la bolla (caso 1) vale gia' il §3.4.
