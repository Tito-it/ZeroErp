# Brief DB — Esigibilità IVA: il regime dell'emittente (IVA per cassa) non entra nella decisione

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`); Tid
> per le decisioni di §6.
> **Origine:** controllo dell'esigibilità sulle fatture del cliente Titini Michele Carlo (2026-10-01):
> lì «Immediata» è **corretta** (privato con codice fiscale, fuori dalla scissione). Il controllo ha
> però mostrato che la decisione guarda **solo il cliente** e mai l'emittente.
> **Stato:** ✅ **D-1 → D-6 decise da Tid il 2026-10-01** (§6). ✅ **D-7 → D-11 (analisi critica del
> team DB, §8) accettate da Tid il 2026-10-01, come proposte.** ✅ **Lato DB SCRITTO il 2026-10-01**
> (`20261001-01 → -17`, §9), **non applicato**: ⏳ l'apply e la corsa pgTAP sono di Tid. Poi le
> richieste a BE/FE (§9.5), bloccanti dopo l'apply per due punti (R-1, R-2).
>
> **In una riga:** un emittente in regime di **IVA per cassa** (art. 32-bis, codice RF17) deve
> emettere fatture con esigibilità **D** (differita); il sistema oggi scrive **I** (immediata) e non
> lo sa, senza nessun errore.

---

## 1. Il problema

L'esigibilità IVA di una riga di fattura (`I` immediata, `D` differita, `S` scissione dei pagamenti)
oggi la decide il trigger `vendite.trgfn_fatture_righe_guard_normalize`, guardando **il cliente**:

* cliente in scissione (`soggetti.split_payment = 'S'`) → `S`, imposta;
* altrimenti → `I`, ma **solo se la riga è vuota**: una `D` scritta da qualcuno sopravvive.

Il **regime fiscale dell'emittente** esiste nel modello (`anagrafiche.emittenti_fiscali.regime_fiscale_rf`,
il codice RF del tracciato FatturaPA), finisce nello snapshot dell'intestazione
(`fn_snapshot_intestazione_fattura`), ma **nessuna regola lo legge per l'esigibilità**.

⇒ Un emittente in IVA per cassa emetterebbe **tutte** le sue fatture con `I`. A meno di una
correzione a mano riga per riga, che nessuna schermata offre, il documento fiscale dichiara un
regime sbagliato. È un difetto **del modello**: non dipende da quali emittenti ci sono oggi.

## 2. Cosa c'è oggi — letto dalla struttura (2026-10-01)

| Oggetto | Cosa dice |
| --- | --- |
| `emittenti_fiscali.regime_fiscale_rf` | `varchar`, **nullable**, nessun `CHECK`, nessuna tabella di vocabolario: un testo libero |
| `vendite.trgfn_fatture_righe_guard_normalize` | `split_payment` dal cliente (riscritto sempre); `esigibilita` = `S` con la scissione, altrimenti `I` sul vuoto |
| `vendite.fn_resolve_iva_riga_it` (risolutore, anteprima del form riga) | ricalcola **la stessa coppia** dal soggetto cliente, con la sua copia della regola (`v_esigibilita := CASE …`) |
| `vendite.fatture_riepiloghi_iva` | raggruppa per `(iva, natura, esigibilita, split)`; unique con `COALESCE(esigibilita, 'I')` |
| `vendite.preventivi_riepiloghi_iva` | ha la colonna, ma `fn_ricalcola_riepilogo_iva_preventivo` la scrive sempre `NULL` |
| `anagrafiche.soggetti` | `split_payment`, `partita_iva`, `id_fiscale_univoco_cf_piva`, `tipo_soggetto_dettaglio_id` |

⚠️ **La regola sta in due sedi**: il trigger e il risolutore la ricalcolano ognuno per conto suo. Oggi
coincidono, ma la modifica di §4 va fatta in **una** sede letta da tutti e due (regola del 2), o
l'anteprima del form e la riga salvata diranno due cose diverse.

Fatto datato, non motivo: al 2026-10-01 i due emittenti di dbdev hanno `regime_fiscale_rf` vuoto,
quindi nessun documento esistente è sbagliato. Il difetto resta: il modello ammette RF17 e non lo
gestisce.

## 3. La regola fiscale (da far confermare al consulente)

> ⚠️ Riassunto di chi scrive, **non** un parere fiscale: va verificato prima del changeSet.

* **Art. 32-bis DL 83/2012**: chi opta per l'IVA per cassa versa l'imposta all'**incasso** (comunque
  entro un anno dall'operazione). In fattura elettronica: `RegimeFiscale = RF17` ed
  `EsigibilitaIVA = D`.
* **Esclusioni** — l'operazione resta a esigibilità ordinaria anche per un emittente in cassa:
  * verso un cliente che **non agisce nell'esercizio d'impresa, arte o professione** (il privato:
    il caso di Titini Michele resterebbe `I` anche con un emittente in cassa);
  * operazioni in **inversione contabile** (reverse charge, nature `N6.x`);
  * operazioni in **scissione dei pagamenti** (`S` prevale);
  * operazioni dei regimi speciali.
* **Annotazione obbligatoria** in fattura: «operazione con IVA per cassa ai sensi dell'art. 32-bis
  del DL 83/2012».

⇒ La decisione dipende da **tre** cose, non da una: regime dell'emittente, natura del cliente
(privato o soggetto IVA), natura della riga (reverse charge). La seconda e la terza rendono
l'esigibilità **per riga** e non per documento, ed è compatibile col raggruppamento dei riepiloghi.

## 4. Proposta (team DB)

1. **Il vocabolario del regime**: `regime_fiscale_rf` da testo libero a codice di un catalogo
   (`config.regimi_fiscali`, RF01…RF19 del tracciato, CSV in `80_data`) con FK. Una regola che decide
   su `= 'RF17'` non può appoggiarsi a un testo che accetta `'rf17 '`.
   **D-1**: la colonna prende il **default RF01** (ordinario), e gli emittenti esistenti col regime
   vuoto passano a RF01 nello stesso giro; un presidio elenca gli emittenti a RF01 **non confermati**
   da una persona, perché un default resta una forma che nessuno ha dichiarato.
2. **Una sede per la regola**: una funzione (`vendite.fn_esigibilita_riga(...)` o simile) che riceve
   il regime dell'emittente, il cliente e la natura della riga e risponde `S` / `D` / `I` / `NULL`
   («non determinato»). La chiamano il trigger e il risolutore. Ordine:
   1. cliente non risolto → `NULL` (com'è oggi);
   2. scissione → `S`;
   3. emittente RF17, cliente soggetto IVA, riga non in reverse charge → `D`;
   4. altrimenti → `I`, sul vuoto (la `D` scelta a mano sopravvive, come oggi).
3. **Il cliente soggetto IVA** (D-2): si legge dalla `partita_iva` del soggetto cliente
   valorizzata, come regola scritta nella funzione del punto 2.
4. **L'annotazione in fattura**: un riferimento normativo legato al regime, letto dal contesto di
   stampa (il BE lo porta nel contesto e la versione del template lo stampa). Va con la forma dei
   dati: **nuova forma** del builder fattura e nuova versione del template, secondo il patto di
   `brief-db-documenti-versione-contesto-template`.
5. **Preventivi, ordini e DDT** (D-4, D-6): i loro riepiloghi IVA calcolano esigibilità e scissione con la
   **stessa** funzione del punto 2, al posto dei `NULL` di oggi (`fn_ricalcola_riepilogo_iva_preventivo`
   scrive sempre `NULL`; `vw_ordini_riepilogo_iva_dettaglio` proietta `NULL::character(1)` e
   `NULL::boolean`). Il raggruppamento segue quello della fattura, `(iva, natura, esigibilita, split)`.
   Il DDT si allinea nello stesso giro (D-6): `vw_ddt_riepilogo_iva_dettaglio` ha la stessa forma
   della vista degli ordini.
6. **pgTAP** costruendo i casi: emittente RF17 × (soggetto IVA, privato, PA in scissione) × (riga
   ordinaria, riga N6), più emittente ordinario e regime vuoto. Nessun confronto con la popolazione.

## 5. Ricadute fuori dal DB (da chiedere a BE/FE quando il DB è fatto)

* **BE**: il contesto di stampa fattura porta l'annotazione del regime (forma nuova); il payload SDI
  (sospeso per decisione, PROJECT_CONTEXT) dovrà leggere `EsigibilitaIVA` dalle righe, già giuste.
* **FE**: il campo del regime fiscale nel form emittente diventa una scelta dal catalogo; il
  riepilogo IVA del drawer fattura mostra già la `D` (decodifica esistente).
* **Preventivi, ordini e DDT** (D-4, D-6): il riepilogo IVA del drawer mostra l'esigibilità anche
  lì — `RiepilogoIvaTable` ha già `show-esigibilita`, da accendere sui tre drawer; l'annotazione in
  stampa, se si vuole anche sui loro PDF, è una forma nuova dei loro builder.

## 6. Decisioni per Tid

✅ **Tutte decise da Tid il 2026-10-01.**

| # | Domanda | Esito |
| --- | --- | --- |
| D-1 | `regime_fiscale_rf` **vuoto**: come si tratta? | ✅ **Ordinario, con un default RF01** sulla colonna; gli esistenti vuoti passano a RF01. Il presidio sugli emittenti a RF01 non confermati resta (§4.1) |
| D-2 | «Il cliente è un soggetto IVA»: da dove si legge? | ✅ Dalla **`partita_iva`** del soggetto cliente |
| D-3 | L'annotazione art. 32-bis in fattura | ✅ **Sì**, nello stesso giro: forma nuova del contesto fattura + versione nuova del template |
| D-4 | I preventivi | ✅ **Si allineano, e con loro gli ordini**: riepilogo IVA con esigibilità e scissione dalla stessa funzione (§4.5) |
| D-5 | Le fatture già emesse | ✅ **Nessun riallineamento**: su dbdev sono fatture di test |
| D-6 | Il **DDT** | ✅ **Sì, insieme** agli ordini: il suo riepilogo ha la stessa forma (`NULL` fissi in `vw_ddt_riepilogo_iva_dettaglio`), e lasciarlo fuori sarebbe un'asimmetria fra documenti fratelli |

## 7. Fuori perimetro, dichiarato

* La **liquidazione** all'incasso (quando l'IVA diventa dovuta, la scadenza di un anno): è
  contabilità, e lo schema `contabilita` è fuori perimetro per decisione.
* Gli altri regimi speciali (forfettario RF19 e simili): stesso catalogo di §4.1, regole proprie da
  decidere a parte.

## 8. Analisi critica del team DB (2026-10-01)

> **Chi scrive:** team DB (`dev/db-tid`). Letta la struttura dalla documentazione generata
> (`trgfn_fatture_righe_guard_normalize`, `fn_resolve_iva_riga_it`, `fn_snapshot_intestazione_fattura`,
> `fn_ricalcola_riepilogo_iva_preventivo`, le viste dei riepiloghi di ordini e DDT, `config.iva_natura`,
> `anagrafiche.emittenti_fiscali`, `anagrafiche.soggetti`). Nessun changeSet scritto.
>
> **In breve:** la diagnosi del §1 è giusta, e anche la sede unica del §4.2. Il punto debole è
> «**`I` sul vuoto, la `D` scelta a mano sopravvive**»: con una `D` che il sistema stesso deriva,
> quella regola non regge più (§8.1). Ci sono poi tre imprecisioni sulla struttura (§8.3, §8.4,
> §8.5) e due pezzi che le decisioni presuppongono ma che il §4 non descrive (§8.6, §8.7). Le
> domande nuove sono D-7 → D-11 (§8.9).

### 8.1 🔴 «Riempire solo il vuoto» non distingue una `D` derivata da una `D` scelta

Oggi il trigger riscrive sempre `split_payment` e scrive l'esigibilità **solo se è vuota**. La
regola reggeva perché l'unico valore che il sistema deduceva fuori dalla scissione era `I`, e una
`D` poteva arrivare solo da una persona.

Con il §4.2 anche la `D` diventa un valore che il sistema deduce, e una colonna non sa dire chi
l'ha scritta. Alla prima scrittura la riga riceve un valore, e da lì in poi ogni `UPDATE` lo trova
non vuoto e lo lascia com'è:

* emittente che passa a RF17 mentre una fattura è in bozza: le righe già scritte restano `I`;
* cliente a cui si aggiunge la partita IVA: le righe restano `I`;
* al contrario, una `D` dedotta resta `D` anche quando il cliente torna privato o la riga passa a
  un codice IVA in reverse charge.

È lo stesso difetto che il §1 denuncia, cioè un regime sbagliato senza nessun errore, che rientra
dall'aggiornamento invece che dall'inserimento.

**Che cosa dice il modello.** L'IVA per cassa è un'**opzione** che vale per **tutte** le
operazioni dell'emittente non escluse: per un emittente RF17 la `D` è **imposta**, come la `S` della
scissione, non scelta. La `D` scelta a mano resta concepibile solo per un emittente ordinario
(esigibilità differita dell'art. 6 c. 5 DPR 633/72). Oggi però nessuna schermata la offre, come
dice lo stesso §1.

**Proposta (D-7):** l'esigibilità diventa una **derivazione pura**, riscritta a ogni scrittura
della riga, come `split_payment`. Se un giorno servirà una differita scelta a mano, avrà una sede
**dichiarata**, per esempio una colonna di scelta con il suo motivo, e non il «non vuoto» di una
colonna che ospita anche i valori dedotti. Lo stesso principio del brief `versione_contesto`: una
scelta si dichiara, non si deduce dalla presenza di un valore.

### 8.2 🔴 Le righe e la testata leggono il regime in due momenti diversi

* L'esigibilità delle righe si calcola **quando si scrive la riga**.
* Il regime stampato in testata (`RegimeFiscale`) lo fotografa `fn_snapshot_intestazione_fattura`
  **all'uscita dalla bozza** (`trgfn_fatture_guard_uscita_draft`) o nel giro del lotto.

Se il regime dell'emittente cambia mentre la fattura è in bozza, la testata dirà RF01 e le righe
`D`, o il contrario. Lo stesso difetto esiste già oggi per la scissione del cliente, ma con il
regime pesa di più, perché l'opzione per cassa **cambia nel tempo** per sua natura: si esercita per
anno.

**Proposta (D-8):** all'uscita dalla bozza, nello stesso punto in cui nasce lo snapshot della
testata, si **ricalcola** l'esigibilità delle righe. Con la derivazione pura di D-7 basta toccarle.
In alternativa, un guard che rifiuta l'uscita se righe e testata non coincidono. La storicità del
regime (quale regime valeva a una certa data) è una domanda più grande, ed è solo **dichiarata**:
oggi `regime_fiscale_rf` è un valore senza validità nel tempo.

### 8.3 ⚠️ Il reverse charge non si riconosce da `N6.x`: c'è già un flag

Il §4.2 e il §4.6 parlano di «natura `N6.x`». In `config.iva_natura` esiste già
`is_reverse_charge boolean NOT NULL`, ed è il flag che il risolutore restituisce. Un confronto
`LIKE 'N6%'` sul `codice` sarebbe proprio l'antipattern di linee-guida-sql §6d (un letterale su una
colonna che non è la chiave stabile). La regola legge il **flag**.

### 8.4 ⚠️ Nemmeno `= 'RF17'` va scritto nella regola: serve un attributo del catalogo

Per lo stesso motivo il catalogo `config.regimi_fiscali` dovrebbe portare un **attributo**, per
esempio `iva_per_cassa boolean`, e la regola dovrebbe leggere quello, non il letterale `'RF17'`.
È lo stampo di `is_reverse_charge`: il codice è del tracciato, il **significato** è una colonna.
Tre conseguenze:

* il codice (`RF17`) resta la chiave naturale esterna, stabile come un codice ISO (§6b punto 2);
* il catalogo segue il tracciato **di oggi**, da verificare sulle specifiche FatturaPA in vigore:
  «RF01…RF19» va riletto, perché RF03 risulta soppresso e un RF20 è stato aggiunto di recente.
  Chi esce dal tracciato si deprezza con `obsoleto_dal`, non si cancella;
* la FK: oggi `regime_fiscale_rf` è un `varchar` che **due lettori** usano come testo,
  `fn_snapshot_intestazione_fattura` e `script.fn_get_user_profile`. Se la colonna resta col suo
  nome e diventa una FK sul codice, i lettori non cambiano. Se invece diventa
  `regime_fiscale_id`, vanno censiti e riscritti (D-9).

### 8.5 ⚠️ Nel risolutore l'esigibilità non può più essere calcolata una volta sola

`fn_resolve_iva_riga_it` calcola `v_esigibilita` **una volta**, prima della ripartizione del
plafond, e la ricopia su tutte le parti. Fino a oggi andava bene, perché dipendeva solo dal
cliente. Con il §4.2 dipende anche dalla **natura**, e le due parti di una riga spezzata dal
plafond hanno codici IVA, e quindi nature, diverse. La chiamata alla funzione unica va fatta **per
parte**, nella `SELECT` finale, accanto a `n.is_reverse_charge`.

### 8.6 ⚠️ Il presidio di D-1 ha bisogno di un dato che il §4 non prevede

D-1 vuole un presidio sugli emittenti a RF01 «**non confermati** da una persona». Con un default,
però, una riga a RF01 dichiarata e una a RF01 di default sono identiche: per distinguerle serve
una colonna, per esempio la data e l'utente della conferma, scritta dal form dell'emittente. Senza,
il presidio non può essere scritto. Quindi la colonna va aggiunta allo stesso giro, e il BE e il FE
devono scriverla.

⚠️ Il passaggio a FK ha bisogno di un cancello: un `expectedResult: 0` sui valori di
`regime_fiscale_rf` che non sono nel catalogo (`'rf17 '`, testo libero), con `HALT`. È sbagliato
pensare che «oggi sono vuoti» basti: la colonna li ammette.

### 8.7 ⚠️ L'annotazione dipende dalle righe, non dal regime

Il §4.4 lega l'annotazione art. 32-bis «al regime». Ma una fattura di un emittente RF17 verso un
privato, o tutta in reverse charge, ha tutte le righe `I`: nessuna operazione è per cassa, e
l'annotazione sarebbe un'affermazione falsa. La condizione è che **almeno una riga** sia `D` per
effetto del regime. Il testo dell'annotazione può stare nel catalogo dei regimi; la decisione di
stamparla si legge dalle righe.

### 8.8 Punti minori

* **Regime vuoto o riga senza codice IVA.** Se `iva_id` è vuoto (in bozza è legittimo, D3) la
  natura non è nota e il reverse charge non si sa. Per un emittente in cassa e un cliente soggetto
  IVA la risposta giusta è `NULL` («non determinato»), non `D`. È la stessa disciplina di D32.
* **Partita IVA «valorizzata» (D-2).** `soggetti.partita_iva` è un `text` nullable: «valorizzata»
  si scrive `NULLIF(btrim(partita_iva), '') IS NOT NULL`, altrimenti una stringa vuota diventa un
  soggetto IVA.
* ~~**`fatture_righe.esigibilita` non ha un `CHECK`**~~ — ⚠️ **sbagliato, corretto il 2026-10-01**:
  il `CHECK` c'è (`chk_fatture_righe_esigibilita` e `chk_fatture_r_iva_esigibilita`,
  `esigibilita IS NULL OR esigibilita IN ('I','D','S')`). L'avevo preso dal commento di
  `fn_resolve_iva_riga_it` (D32), che lo dava per assente, invece che dal catalogo: la stessa
  trappola che quel commento racconta. Nessun lavoro da fare.
* **La funzione unica lavora sui valori, non sugli id.** Riceve il regime (o il suo attributo
  «per cassa»), la scissione del cliente, «cliente soggetto IVA» e «reverse charge», ed è
  `IMMUTABLE`. Ogni chiamante risolve da sé i propri dati: trigger e risolutore li hanno già in
  mano, i tre riepiloghi li leggono da testata e codice IVA. La sede: `vendite` è giusta oggi, ma la
  stessa domanda la farà `acquisti` sul passivo. `script` evita uno spostamento più avanti.
* **I riepiloghi di preventivi, ordini e DDT (D-4, D-6)** sono fattibili senza colonne nuove sulle
  righe: raggruppano per `iva_id`, e la natura viene dal codice IVA. Sono valori **calcolati al
  momento**, non fotografati, e per documenti non fiscali va bene. Per il preventivo, con
  `billing_account_id` nullable, la risposta è `NULL` finché il cliente non c'è (regola 1 del §4.2).
* **Gli altri «regimi speciali»** esclusi dal 32-bis non sono nel modello: il §7 li mette fuori, e
  la funzione li tratta come «non per cassa» solo perché l'attributo del catalogo è `false`.

### 8.9 Decisioni nuove per Tid

✅ **Tutte e cinque accettate da Tid il 2026-10-01, come proposte.**

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| D-7 | L'esigibilità resta «`I` sul vuoto, la `D` manuale sopravvive» o diventa una derivazione pura? | **Derivazione pura**, riscritta a ogni scrittura come `split_payment` (§8.1). Una differita scelta a mano, se mai servirà, avrà una colonna sua |
| D-8 | Regime che cambia mentre la fattura è in bozza | **Ricalcolo all'uscita dalla bozza**, accanto allo snapshot della testata (§8.2). Storicità del regime dichiarata, fuori da questo giro |
| D-9 | Forma della FK sul regime | La colonna `regime_fiscale_rf` **resta** e diventa FK sul **codice** del catalogo (chiave esterna del tracciato), così i due lettori non cambiano (§8.4) |
| D-10 | Il significato «per cassa» | Un **attributo** del catalogo (`iva_per_cassa`), non il letterale `'RF17'` nella regola (§8.4) |
| D-11 | La conferma del regime per il presidio di D-1 | Una colonna di conferma (data, utente) scritta dal form dell'emittente; senza, il presidio non si può scrivere (§8.6) |

## 9. Che cosa è stato scritto (2026-10-01, team DB)

### 9.1 I changeSet

| changeSet | cosa |
| --- | --- |
| `00_schema/config/20261001-01` | `config.regimi_fiscali`: `codice_interno` = codice RF (CHECK `^RF[0-9]{2}$`), `iva_per_cassa`, `annotazione_documento`, la forma dei vocabolari di `config` (D-9, D-10) |
| `00_schema/anagrafiche/20261001-02` | `emittenti_fiscali.regime_fiscale_confermato_il` / `_da`, nullabili, in coppia (CHECK) (D-11) |
| `20_code/script/20261001-03` | `script.fn_esigibilita_iva(p_iva_per_cassa, p_cliente_split_payment, p_cliente_partita_iva, p_iva_id)` → `TABLE(esigibilita, split_payment)`: **la regola**, sui valori (§4.2, D-2, D-7, D-10, §8.3) |
| `20_code/script/20261001-04` | `script.fn_esigibilita_iva_documento(p_emittente_fiscale_id, p_billing_account_id, p_iva_id, p_regime_fiscale_rf DEFAULT NULL)`: le parti di un documento, una catena sola |
| `20_code/vendite/20261001-05` | `vendite.fn_esigibilita_iva_fattura(p_fattura_id, p_iva_id)`: regime dallo **snapshot** dell'intestazione, se c'è (D-8) |
| `20_code/vendite/20261001-06` | `trgfn_fatture_righe_guard_normalize`: il blocco 2-bis diventa una derivazione pura (D-7) |
| `20_code/vendite/20261001-07` | `fn_resolve_iva_riga_it`: la coppia esce dalla regola, **per parte** (§8.5); firma invariata |
| `20_code/vendite/20261001-08` | `fn_ricalcola_riepilogo_iva_fattura`: riallinea esigibilità e scissione delle righe prima di aggregare (D-8) |
| `20_code/vendite/20261001-09` | `fn_ricalcola_riepilogo_iva_preventivo`: la coppia dalla regola invece dei `NULL` (D-4) |
| `20_code/vendite/20261001-10`, `-11` | `vw_ordini_riepilogo_iva_dettaglio`, `vw_ddt_riepilogo_iva_dettaglio`: idem (D-4, D-6); colonne e `security_invoker` invariate |
| `20_code/anagrafiche/20261001-12`, `-13` | `trgfn_emittenti_fiscali_regime_conferma` + `trg_emittenti_fiscali_a20_regime_conferma_upd`: se il regime cambia senza conferma, la conferma si azzera (D-11) |
| `20_code/dbops/20261001-14` | il presidio `dbops.vw_emittenti_regime_non_confermato` (D-1, D-11) + la sua riga in `presidi.csv` (ZERO, SETTIMANALE, LIBERO) |
| `80_data/changelog/20261001-15` | seed `regimi_fiscali.csv` (19 codici; `iva_per_cassa` e annotazione sul solo RF17) |
| `80_data/changelog/20261001-16` | backfill regime vuoto → RF01, dietro un cancello HALT sui valori non vuoti fuori catalogo (D-1) |
| `80_data/changelog/20261001-17` | `SET DEFAULT 'RF01'`, `SET NOT NULL`, FK `fk_emittenti_fiscali_regimi_fiscali` su `codice_interno` (D-1, D-9) |
| `80_data/sql/config/tabelle_gestibili.csv` | riga 88: `config.regimi_fiscali`, lookup sì, pannello no (vocabolario di sistema) |
| `20_code/script/20261001-40` | **D-12** (dopo l'apply del `-03`): `script.fn_esigibilita_iva`, `D` solo sulle righe con imposta (codice senza Natura, aliquota > 0); ogni Natura N1-N7 va a `I`. In coda il `COMMENT` di `regimi_fiscali.iva_per_cassa` allineato. Numero `-40` perché `-18 … -26` sono di un altro cantiere aperto lo stesso giorno |

I corpi vengono dalla doc auto-generata (regola di AGENTS); il rollback è il corpo vivo di prima.
Pagine `manual/` nuove o aggiornate per tutti gli oggetti toccati.

### 9.2 Dove si discosta da §4 e §8, e perché

* **D-8 sta nel ricalcolo del riepilogo, non in un trigger di uscita dalla bozza.** La fattura
  congela il regime nello snapshot (passo DRAFT della pipeline). Le righe ora leggono il regime
  **dallo snapshot**, se c'è, e `fn_ricalcola_riepilogo_iva_fattura` le riallinea prima di
  aggregare, come già faceva per l'aliquota (D30). Nella pipeline è il passo `ricalcola_iva_lotto`
  della fase EMESSA, l'ultimo prima del congelamento. Un `UPDATE` delle righe dentro il trigger
  `BEFORE UPDATE` della testata avrebbe lasciato stantio il riepilogo, e ricalcolarlo da lì
  avrebbe scritto sulla testata che si sta aggiornando.
* **Il presidio guarda tutti i regimi non confermati, non solo RF01.** La conferma si azzera
  anche su un cambio di regime senza conferma: un RF17 non confermato è lo stesso fatto. Filtrare
  su RF01 sarebbe un letterale di codice in un presidio.
* **Tre funzioni, non una.** La regola è una (`fn_esigibilita_iva`); le altre due risolvono le
  parti, con chiavi diverse (la testata dei documenti fratelli; la testata e lo snapshot della
  fattura). Il risolutore risolve le sue (emittente e soggetto passati come parametri) e chiama
  la regola.
* **Cliente non noto: il trigger ora scrive `NULL`/`NULL`.** Prima lasciava i valori che c'erano.
  È la conseguenza di D-7, ed è la disciplina D32.
* **Senza emittente il risolutore dà esigibilità `NULL`** fuori dalla scissione (regime non
  noto), non più `'I'`.
* **I riepiloghi dei documenti fratelli usano `LEFT JOIN LATERAL ... ON true`**: la regola rende
  sempre una riga, ma un totale non deve poter perdere un gruppo per un join.
* Il §8.8 sul `CHECK` era sbagliato (corretto lì): il vincolo c'è già.

### 9.3 La prova (2026-10-01): cluster PG18 usa-e-getta, NON dbdev

dbdev non era raggiungibile dalla sessione (autenticazione). La prova è su un cluster locale con
**tabelle minime** (solo le colonne che i corpi nominano), in `BEGIN … ROLLBACK`, con l'SQL
**estratto** dagli YAML `-01 → -17` (il seed simulato con `COPY` dal CSV, token `NULL`).

* Tutto il blocco applica; anche i rollback, in ordine inverso.
* `plpgsql_check` sulle sei funzioni plpgsql nuove o riscritte e sui due trigger: nessun errore
  (solo avvisi di volatilità sugli stub del cluster).
* La matrice della regola dà il risultato atteso negli undici casi. Sulla fattura: RF17 → `D`,
  inversione contabile → `I`, `D` scritta a mano su RF01 → `I`, righe stantie riallineate dal
  ricalcolo, snapshot RF17 che prevale sul vivo RF01. Preventivo con cliente IVA, privato, PA e
  senza cliente. Viste di ordini e DDT con il tipo `character(1)` e `security_invoker`
  conservati. FK, NOT NULL, CHECK della coppia e della forma. Un emittente nuovo nasce RF01.
* ⚠️ **Non provato**: lo schema vero (trigger, RLS e guard degli altri cantieri), il loader di
  Liquibase sul CSV, i pgTAP col runner, i presidi trasversali. Da far girare nella corsa di Tid:
  `vendite/test-esigibilita-iva-per-cassa-v1.sql` (nuovo, 26 test con il 9-bis di D-12),
  `vendite/test-fatture-righe-esigibilita-split.sql` (caso 4 riscritto per D-7, fixture a RF01),
  `vendite/test-fn-resolve-iva-riga.sql`, `dbops/test-riferimenti-morti-v1.sql`,
  `dbops/test-catalogo-presidi-v1.sql` (vista nuova a catalogo), `config/test-pannello-porta-v1.sql`
  (riga nuova in `tabelle_gestibili`).

### 9.4 Domande aperte (per il consulente, non bloccano)

* ✅ **DECISA da Tid il 2026-10-01 (D-12): ogni Natura va a `I`.** La regola resta quella del
  §4.2, precisata: `D` solo sulle righe **con imposta** (codice IVA senza Natura, quindi imposta
  maggiore di zero), emittente per cassa, cliente soggetto passivo IVA, niente scissione.
  Qualsiasi riga con una Natura, dalla N1 alla N7 (inversione contabile compresa), va a `I`.
  Il `-03` mandava a `I` la sola inversione contabile ed era già applicato: la correzione è il
  changeSet nuovo `20261001-40`. Provata sul cluster usa-e-getta (N3 → `I`, N6.3 → `I`, imponibile
  → `D`; `plpgsql_check` pulito); pgTAP: caso 9-bis nel test nuovo (`plan(26)`).
* **RF16** («IVA per cassa P.A.», art. 6 c. 5): `iva_per_cassa = false`. Oggi la differita verso
  la PA è assorbita dalla scissione dei pagamenti.
* **Il catalogo dei codici RF**: RF03 escluso (soppresso), RF20 incluso (franchigia
  transfrontaliera, 2025). Da verificare sulle specifiche FatturaPA in vigore.
* **DDT senza `billing_account_id`**: il cliente non è noto e la coppia è `NULL`. Il DDT ha anche
  un destinatario: se serve, è una scelta di forma da fare a parte.

### 9.5 Richieste al BE e al FE

| # | Cosa | Perché si rompe senza |
| --- | --- | --- |
| **R-1** | Il form dell'emittente (anagrafiche **e** `amm_software`): `regime_fiscale_rf` diventa una scelta dal catalogo `config.regimi_fiscali` (lookup generico, riga 88 di `tabelle_gestibili`). Mai `""` né `NULL` esplicito: in creazione si omette, e vale il default RF01 | dopo l'apply: `23503` su un codice fuori catalogo, `23502` su un `NULL` esplicito |
| **R-2** | Quando l'operatore salva il regime, il form scrive anche `regime_fiscale_confermato_il = now()` e `regime_fiscale_confermato_da = <utente>`, **nella stessa scrittura** | senza, ogni cambio di regime azzera la conferma (trigger) e l'emittente resta nel presidio |
| **R-3** | Stampa della fattura (D-3): l'annotazione `config.regimi_fiscali.annotazione_documento` del regime **dello snapshot**, solo se il documento ha almeno una riga con `esigibilita = 'D'` (§8.7). È una **forma nuova** del contesto fattura e una **versione nuova** del template, secondo il patto di `brief-db-documenti-versione-contesto-template` | senza, la fattura RF17 esce senza l'annotazione obbligatoria |
| **R-4** | `RiepilogoIvaTable` con `show-esigibilita` sui drawer di preventivo, ordine e DDT (§5) | le colonne ci sono, ma a video no |
| **R-5** | Nessun codice errore nuovo. I test Django che creano emittenti con `regime_fiscale_rf` libero vanno allineati a un codice del catalogo | rossi su `23503` |
| **R-6** | Il payload SDI (sospeso) legge l'esigibilità dalle righe, che sono già giuste | — |
