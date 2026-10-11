# Brief DB — Gli indirizzi del documento seguono il cliente

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10. **A chi:** team DB; poi BE/FE (§6).
> **Origine:** §12.3 di [brief-db-esecutivi-ba-coppia](../work-done/brief-db-esecutivi-ba-coppia.md).
> Dal giro di quel brief il cliente di un DDT si sceglie, si cambia e si toglie **in bozza**. Gli
> indirizzi del documento gia' scritti non lo seguono.
> **Stato:** ✅ **lato DB applicato e verde il 2026-10-11** (§7): `20261011-43` … `-61` e i tre CSV, pgTAP
> verdi nella corsa di Tid (§7.4). D-4 decisa e fatta nello stesso giro (§7.5). ⏳ **Tocca a BE/FE** (§6):
> il brief si chiude con la loro consegna.
> **Nel registro dei difetti DB:** voce **D27** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La regola

Un indirizzo del documento preso dall'anagrafica e' **del cliente del documento**. Se il cliente
cambia, quell'indirizzo non e' piu' valido. Restano validi solo gli indirizzi **una-tantum**, scritti
a mano: per D-4 del brief d'origine, la consegna a terzi passa da li'.

Oggi la regola la tiene solo il backend, e solo quando l'indirizzo viene scritto. Dopo non la
ricontrolla nessuno.

## 2. Che cosa c'e' oggi

**Gli snapshot.** Ci sono sei tabelle: `vendite.{ddt,ordini,preventivi,offerte_commerciali,contratti,fatture}_indirizzi`,
con uno slot per tipo (`uq_*_uno_per_tipo`). Ogni riga dice da dove viene:

| `origine_indirizzo_id` | `origine_soggetto_ruolo_id` | Che cos'e' |
| --- | --- | --- |
| valorizzato | valorizzato | layer RUOLO: una riga di `anagrafiche.indirizzi` (eventualmente di un'istanza) |
| NULL | valorizzato | layer SOGGETTO: dall'anagrafica del soggetto |
| NULL | NULL | una-tantum, scritto a mano |

**L'auto-assegnazione alla creazione la fa solo il backend.**
`auto_assegna_indirizzo_default` (`backend/apps/vendite/services/_indirizzi_documento_helpers.py`)
sceglie lo slot di default: CON, se manca FATT, se manca il primo tipo ammesso. Poi risolve
l'indirizzo con `script.fn_resolve_indirizzo_documento(ruolo, istanza, tipo)`, prima RUOLO e poi
SOGGETTO, con l'istanza che ha la precedenza. E' best-effort: se fallisce scrive un warning e il
documento nasce senza indirizzo. Se lo slot e' gia' pieno, per esempio per la cascata dal documento
sorgente (`fn_genera_ddt_da_ordine` sez. 4-bis, `fn_genera_ddt_riconsegna`), non lo tocca. La
chiamano DDT, ordine, preventivo, offerta e contratto.

**Il controllo che l'indirizzo sia del cliente lo fa solo il backend, e solo in scrittura**
(`upsert_indirizzo_documento`, stesso file): `origine_soggetto_ruolo_id` deve essere il ruolo del
documento. Lato DB su `*_indirizzi` c'e' soltanto la whitelist dei tipi
(`vendite.trgfn_tipi_indirizzi_only_allowed`).

**Il gate d'emissione guarda solo che l'indirizzo ci sia.** `script.fn_check_ddt_emittibile`
(punto 4) confronta i tipi presenti con quelli obbligatori (`script.fn_indirizzi_obbligatori_mancanti`).
Non controlla l'origine.

## 3. Perche' e' un difetto, sul modello

* **Il DDT si emette con la Consegna del cliente di prima.** Si crea la bozza col cliente A e lo
  slot CON viene preso dal ruolo di A. Poi il cliente diventa B, e la bolla si emette, si stampa e si
  consegna all'indirizzo di A. Lo stesso vale per una bolla senza cliente di cui cambia il
  destinatario.
* **Preventivo e offerta hanno lo stesso buco.** Il cliente, cioe' la coppia BA/istanza, si cambia
  in bozza: `preventivi_service.aggiorna_preventivo` e `offerte_service.aggiorna_offerta`. Nessuno dei
  due tocca gli indirizzi. Sul preventivo cambia anche l'**istanza** dello stesso cliente: un
  indirizzo di un'istanza (layer RUOLO con `anagrafiche.indirizzi.istanza_utility_id` valorizzato)
  resta attaccato a una fornitura che il documento non ha piu'.
* **L'ordine no**: BA e ruolo sono bloccati sempre (`E_ORD_CLIENTE_IMMUTABILE`).
* **La regola sta in un posto che non vede tutto.** Chi scrive senza passare dal service salta il
  controllo, e l'emissione non lo recupera.

⚠️ Nessuna di queste ragioni dipende da quante righe ci sono oggi in quello stato.

## 4. Decisioni di Tid (2026-10-10)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | La regola «un indirizzo d'anagrafica e' del cliente del documento» vale su tutti i documenti in cui il cliente si cambia in bozza? | ✅ **Si'**: DDT (BA o destinatario), preventivo, offerta. Gli una-tantum restano |
| **D-2** | Lo slot di default dopo un cambio di cliente lo riempie il backend o il DB? | ✅ **Il DB.** Ne segue che l'auto-assegnazione passa intera nel DB, anche alla creazione: due sedi per la stessa regola sono la copia che la regola del 2 vieta |
| **D-3** | L'emissione controlla l'origine? | ✅ **Si'**: e' un motivo del gate d'emissione, cosi' vale anche per chi scrive saltando il backend |
| **D-2-bis** (2026-10-11) | Alla **creazione**, chi fa scattare il riempimento dello slot di default? | ✅ **Chi crea chiama il building block DB** (`vendite.fn_doc_indirizzo_default`): il backend negli stessi punti dell'helper Python, `fn_create_contratto` dentro di se'. La regola resta tutta nel DB; il cambio di cliente in bozza e' un trigger. Le alternative e il perche' nel §7.2 b |

## 5. Forma proposta (la sceglie il team DB)

1. **Un BB di risoluzione dello slot di default.** Prende documento e cliente (ruolo, istanza) e
   scrive lo slot se e' vuoto, con `script.fn_resolve_indirizzo_documento`. ⚠️ La priorita' fra i tipi
   (CON → FATT → primo ammesso) oggi e' scritta in Python come «regola di UX». Nel DB diventa regola
   di dominio: va dichiarata in `config.tipi_indirizzi_allowed` (per esempio un ordine di default per
   ambito), non cablata per codice.
2. **Alla creazione**, il BB lo chiamano i verbi e/o i trigger. ⚠️ La cascata dal documento sorgente
   deve restare prioritaria: oggi il backend arriva **dopo** il verbo e trova lo slot gia' pieno.
   Bisogna scegliere il «quando» (trigger AFTER INSERT sulla testata, o chiamata esplicita dai verbi
   dopo la cascata) in modo da non scrivere uno slot che la cascata scriverebbe subito dopo.
3. **Al cambio di cliente in bozza** (un `UPDATE` che cambia `billing_account_id`/`istanza_utility_id`
   sul preventivo e sull'offerta, `billing_account_id` o `destinatario_soggetto_ruolo_id` sul DDT):
   * si tolgono le righe d'anagrafica non piu' valide per il cliente nuovo, cioe' con
     `origine_soggetto_ruolo_id` diverso dal ruolo nuovo, oppure del layer RUOLO legate a un'istanza
     diversa da quella nuova. Gli una-tantum restano;
   * si richiama il BB del punto 1 sullo slot di default rimasto vuoto.
4. **Il guard sulla scrittura di `*_indirizzi`**, che sostituisce quello Python: una riga d'anagrafica
   deve avere il ruolo del documento, e se viene da un'istanza, l'istanza del documento. Un
   documento senza ruolo risolvibile lascia passare, come oggi. Un BB parametrico per le sei
   tabelle, come la whitelist dei tipi.
5. **Il motivo d'emissione nuovo**, sul DDT in `script.fn_check_ddt_emittibile` (sede unica di guard
   e capability). Sui gate d'emissione di preventivo e offerta si fa lo stesso censimento.
6. **Codici**: uno per «indirizzo non del cliente del documento» (guard di scrittura e motivo
   d'emissione), registrato con policy e frase di ripiego. Il campo e' `tipo_indirizzo_id` o lo slot.

### 5.1 Da censire nel giro

* Contratto e fattura: il loro cliente si cambia in bozza **a DB**? Lato BE il BA del contratto e'
  vietato in update (`contratti_service._FORBIDDEN_TESTATA_UPDATE`). Se il DB non lo blocca, la regola
  del §5.3 li riguarda anche loro.
* Il reso non ha `*_indirizzi`: la riconsegna li eredita per cascata (`fn_genera_ddt_riconsegna`). Va
  confermato che non serve altro.
* I verbi con cascata degli indirizzi (`fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`, push
  preventivo → ordine, offerta → contratto): con il punto 2 non devono trovarsi uno slot gia' scritto
  dal default.
* La testata del pgTAP `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` (riga 7) punta ancora a
  `work-in-progress/brief-db-esecutivi-ba-coppia.md`. Il brief e' in `work-done/` dal 2026-10-10.

### 5.2 pgTAP (fixture fabbricati)

* DDT in bozza col cliente A e la CON di A; il cliente diventa B: la CON di A non c'e' piu', c'e'
  quella di B (se B ne ha una); un una-tantum resta.
* Preventivo: stesso cliente, istanza cambiata, con un indirizzo legato all'istanza vecchia.
* Scrittura diretta su `ddt_indirizzi` di un indirizzo d'un altro ruolo: rifiutata col codice.
* Emissione di una bolla con una riga d'anagrafica d'un altro ruolo (scritta prima del guard, o a
  guard spento): motivo nuovo.
* Creazione da ordine: lo slot lo scrive la cascata, non il default.

## 6. Ricaduta BE/FE (dopo la consegna DB)

> Riscritto dal team DB il 2026-10-11 sulla forma consegnata (§7). ⛔ Le righe R-FE-1 e R-BE-2 vanno
> fatte **nello stesso giro dell'apply**: senza, la CI e' rossa sul lato altrui (`check_i18n_keys.py`
> controllo 4, guardrail delle policy dei codici).

| # | Lato | Che cosa |
| --- | --- | --- |
| **R-BE-1** | BE | Al posto di `auto_assegna_indirizzo_default` il BE chiama **`SELECT vendite.fn_doc_indirizzo_default(<documento>, <id>)`** negli stessi punti: dopo la creazione di DDT, ordine, preventivo e offerta (`ddt_service:365`, `ordini_service:457`, `preventivi_service:557`, `offerte_service:572`) e dopo i verbi con cascata (`crea_ddt_da_ordine`, push preventivo → ordine, push offerta → contratto). Selettori: `DDT`, `ORDINE`, `PREVENTIVO`, `OFFERTA`, `CONTRATTO`. Dopo `create_contratto_atomico` **non** serve: `vendite.fn_create_contratto` lo fa da sé. Si ritirano `auto_assegna_indirizzo_default`, `_tipo_default` e `auto_assegna_indirizzo_default_contratto`: la priorita' fra i tipi e' ora un dato (§7.2 a). ⚠️ Non e' piu' best-effort: un errore del DB (non uno slot vuoto, che torna `false`) sale come gli altri |
| **R-BE-2** | BE | Codice nuovo **`E_INDIRIZZO_DOC_NON_DEL_CLIENTE`** (`DATO_ERRATO`, campo `tipo_indirizzo_id`): policy rigenerata e frase di ripiego. Si ritira il guard d'origine di `upsert_indirizzo_documento` (i due `ErrorManager.require` sull'ownership, picker e una-tantum dichiarato): decide il guard DB e il BE mappa il codice |
| **R-BE-3** | BE | La fotografia del Python era la sola ancora del guard: `get_soggetto_ruolo_documento` resta solo se serve ad altro (il picker del FE) |
| **R-FE-1** | FE | `reason_key` nuova **`common.azione_reason.indirizzo_non_del_cliente`** nei locales (it, en): la emettono la check della bolla, quella del preventivo e le capability di offerta e contratto |
| **R-FE-2** | FE | Dopo il salvataggio del cliente in bozza (DDT: BA o destinatario; preventivo, offerta, contratto: BA/istanza) il pannello indirizzi si **ricarica**: il DB toglie gli indirizzi del cliente di prima e riempie lo slot di default dal nuovo |

## 7. Disegno DB (team DB, 2026-10-11)

### 7.1 Il censimento del §5.1, chiuso

| Voce | Esito |
| --- | --- |
| Contratto | ✅ **Nel perimetro.** A DB `billing_account_id`, `istanza_utility_id` e `utility_id` del contratto sono fermi solo **fuori** bozza (`trg_contratti_a05_lock_fuori_bozza_upd`): in DRAFT si cambiano, e il divieto del BE (`_FORBIDDEN_TESTATA_UPDATE`) non vale per chi scrive senza passarci. Cambio di cliente e motivo all'attivazione come preventivo e offerta |
| Fattura | Il cliente non si cambia in bozza da un verbo dell'operatore, e gli indirizzi li scrive solo `vendite.fn_snapshot_indirizzi_fattura`, dal BA di testata: validi per costruzione. Entra nel **guard di scrittura** (le sei tabelle, §5.4), non nel cambio di cliente né nel motivo |
| Ordine | Cliente fermo sempre (`E_ORD_CLIENTE_IMMUTABILE`): guard di scrittura sì, cambio di cliente no |
| Reso | Nessun `*_indirizzi`. La riconsegna li copia da un DDT con lo stesso BA (un BA lungo la catena, D21): la copia passa dal guard come ogni altra scrittura. Non serve altro |
| Verbi con cascata | Il default lo fa scattare chi crea **dopo** la cascata (§7.2 b): lo slot scritto dalla sorgente vince, e i verbi non si toccano |
| `acquisti.ddt_indirizzi` | ⛔ **Non è una copia.** In un DDT d'acquisto la Consegna è il **nostro** magazzino, non un indirizzo del fornitore: la regola «l'indirizzo è della controparte» lì non vale. Fuori perimetro, si decide col comportamento degli acquisti |
| Testata del pgTAP `test-esecutivi-ba-coppia-v1` | corretta in questo giro (`work-done/`) |
| ⚠️ **Trovato:** la revisione dell'offerta | `vendite.fn_crea_revisione_offerta` **non copia gli indirizzi** (quella del preventivo sì, `fn_crea_revisione_preventivo`). ✅ **D-4 di Tid (2026-10-11): la copia si fa in questo giro** (`20261011-61`), come la gemella |

### 7.2 La forma

**a) Lo slot di default è un dato, in `config.tipi_indirizzi_allowed`.** Due colonne:

* `slot_default boolean NOT NULL DEFAULT false`, uno per ambito (indice unico parziale): il tipo che il
  database riempie da solo. Seme: **CON** per DDT, ORDINI, PREVENTIVI, OFFERTE, CONTRATTI; nessuno per
  FATTURE (ha la sua funzione) e ACQUISTI_DDT (§7.1).
* `ripiego_tipo_indirizzo_id`, facoltativo e solo sullo slot di default: il tipo d'anagrafica da cui
  prenderlo se il cliente non ha quello dello slot. Seme: **FATT** sulle cinque righe CON. È la regola di
  oggi («la merce va all'indirizzo di fatturazione se manca la consegna»), scritta come dato.

⚠️ **Una differenza dichiarata col Python.** `_tipo_default` sceglieva lo slot (CON → FATT → primo ammesso)
e poi riempiva lo slot con la catena **fissa** CON → FATT, qualunque fosse lo slot: su un ambito senza CON
lo slot FATT avrebbe preso un indirizzo di Consegna. Qui lo slot si riempie dal **suo** tipo e poi dal suo
ripiego. Su tutti gli ambiti di oggi il risultato è lo stesso (lo slot è CON); sul modello la regola nuova
è quella giusta.

**b) Quando.** Due momenti, un building block:

* **Nascita: chi crea chiama il building block** (decisione di Tid del 2026-10-11). Il backend dopo le
  sue INSERT e dopo i verbi con cascata, negli stessi punti in cui chiamava l'helper Python (R-BE-1);
  `vendite.fn_create_contratto` dentro di sé (`20261011-60`). Lo slot si riempie solo se è vuoto, quindi
  la cascata dalla sorgente vince sempre. ⚠️ Limite dichiarato: un documento creato senza passare dal
  backend (o un verbo chiamato da fuori) non riceve il default, come oggi; l'obbligo lo dice l'emissione.
  ⛔ **Perché non un trigger alla nascita**, provato sul codice e non supposto: quasi tutti i pgTAP girano
  con `SET CONSTRAINTS ALL IMMEDIATE` (è nel template), quindi anche un trigger `DEFERRABLE INITIALLY
  DEFERRED` scatta a fine istruzione; ogni cliente di fixture ha un indirizzo FATT di ruolo (il ruolo
  cliente lo vuole), quindi lo slot CON si riempirebbe subito e la fixture che scrive poi la sua CON
  (47 file, più `dbops.fn_pgtap_crea_ddt`) collide sulla UNIQUE dello slot; e un evento differito in
  sospeso fa fallire l'`ALTER TABLE … FORCE ROW LEVEL SECURITY` dei dieci pgTAP RLS sulle testate. Le
  alternative erano riscrivere sei verbi con la cascata «la sorgente vince», o una colonna «automatico»
  sulle cinque tabelle con uno slot che cede (§ domanda a Tid del 2026-10-11).
* **Cambio di cliente in bozza:** `AFTER UPDATE` (`trg_<t>_m50_indirizzi_seguono_cliente_upd`), con il
  `WHEN` sulle colonne del cliente: DDT `billing_account_id`, `destinatario_soggetto_ruolo_id`;
  preventivo, offerta, contratto `billing_account_id`, `istanza_utility_id`. Toglie le righe d'anagrafica
  che non sono più del cliente (le una-tantum restano) e richiama il building block sullo slot rimasto vuoto.

**c) I building block.**

| Oggetto | Che cosa fa |
| --- | --- |
| `script.fn_doc_indirizzi_sede(documento)` | per DDT, ORDINE, PREVENTIVO, OFFERTA, CONTRATTO, FATTURA: tabella degli indirizzi, colonna verso la testata, ambito. Una mappa sola |
| `script.fn_get_cliente_testata_documento(documento, id)` | il cliente del documento, `(soggetto_ruolo_id, istanza_utility_id)`: la colonna nativa se c'è, altrimenti dal BA (la stessa ancora di `get_ancora_indirizzi_documento` del BE). `SECURITY DEFINER` come il lettore dello stato: testate e BA hanno la RLS. Zero righe = la testata non c'è |
| `script.fn_indirizzo_documento_fuori_cliente(origine_indirizzo, origine_ruolo, ruolo, istanza)` | **il predicato**, sui valori: `NULL` se la riga è del cliente (o è una-tantum, o il documento non ha un ruolo), altrimenti il motivo `ALTRO_CLIENTE` / `ALTRA_FORNITURA`. Lo usano guard, cambio di cliente e motivo d'emissione |
| `vendite.fn_doc_indirizzo_default(documento, id)` | riempie lo slot di default se è vuoto: `script.fn_resolve_indirizzo_documento` sul tipo dello slot, poi sul ripiego. Torna se ha scritto |
| `vendite.trgfn_doc_indirizzi_guard_cliente()` | guard `_a10_` sulle sei `*_indirizzi`, `BEFORE INSERT OR UPDATE OF` origine e FK: rifiuta una riga d'anagrafica non del cliente. Sostituisce il guard del Python |
| `script.fn_check_indirizzi_documento_cliente(documento, id)` | il motivo d'emissione, `[]` o un motivo; lo leggono i gate (§7.2 d) |

**Il predicato, per intero.** Una riga con le due origini `NULL` è una-tantum: sempre valida. Altrimenti
è d'anagrafica, e il suo ruolo è `origine_soggetto_ruolo_id` (o quello dell'indirizzo d'anagrafica, se
l'origine del ruolo manca). È del cliente se quel ruolo è il ruolo del documento, se l'indirizzo
d'anagrafica (quando c'è) è dello stesso ruolo, e se il suo `istanza_utility_id` è `NULL` o è l'istanza
del documento. ⚠️ Un indirizzo d'anagrafica legato a una fornitura, su un documento senza fornitura (un
DDT senza BA), **non** è del cliente: è la stessa scelta del risolutore, che con l'istanza `NULL` prende
solo gli indirizzi generici. ⚠️ L'istanza dell'indirizzo d'anagrafica si legge **viva** (la riga del
documento non la registra): se in anagrafica l'indirizzo passa a un'altra fornitura, il motivo d'emissione
lo vede.

**d) I gate d'emissione.**

| Documento | Dove entra il motivo | Chi solleva |
| --- | --- | --- |
| DDT | `script.fn_check_ddt_emittibile`, punto 4-bis (dopo gli indirizzi mancanti) | `vendite.trgfn_ddt_guard_indirizzi_obbligatori`, che diventa il guard degli **indirizzi** all'emissione |
| Preventivo | `script.fn_check_preventivo_emettibile`, motivo 3 | il guard di transizione, col primo motivo (invariato) |
| Offerta | la capability e il guard `BOZZA → EMESSA` | `vendite.trgfn_offerte_commerciali_guard_transizione` |
| Contratto | la capability e il guard `DRAFT → ATTIVO` | `vendite.trgfn_contratti_guard_transizione_stato` |
| Ordine | — | il cliente non cambia: una riga d'altri ce la metterebbe solo una scrittura che il guard ora rifiuta |

**e) Il codice.** `E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, classe `DATO_ERRATO` (l'operatore lo corregge cambiando
l'indirizzo), campo `tipo_indirizzo_id`, un valore: il tipo d'indirizzo leggibile. Stesso codice dal guard
di scrittura e dal motivo. Motivo: `reason INDIRIZZO_NON_DEL_CLIENTE`, `reason_key
common.azione_reason.indirizzo_non_del_cliente` (trasversale, come `indirizzi_mancanti`).

### 7.3 changeSet

| changeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261011-43` | `config.tipi_indirizzi_allowed` + `slot_default`, `ripiego_tipo_indirizzo_id` (FK, due CHECK, unico parziale per ambito) |
| `80_data/sql/config/tipi_indirizzi_allowed.csv` | le due colonne nel CSV del mirror `20260711-18` (`nullValue: "NULL"`, CSV allineato al DB prima della modifica): CON slot di default con ripiego FATT su DDT, ORDINI, PREVENTIVI, OFFERTE, CONTRATTI |
| `20_code/script/20261011-44` | BB `script.fn_doc_indirizzi_sede` |
| `20_code/script/20261011-45` | lettore DEFINER `script.fn_get_cliente_testata_documento` (+ GRANT all'app) |
| `20_code/script/20261011-46` | predicato `script.fn_indirizzo_documento_fuori_cliente` |
| `20_code/vendite/20261011-47` / `-48` | guard `vendite.trgfn_doc_indirizzi_guard_cliente` e i sei montaggi `trg_<t>_indirizzi_a10_guard_origine_ins_upd` |
| `20_code/vendite/20261011-49` | BB `vendite.fn_doc_indirizzo_default` |
| `20_code/vendite/20261011-50` / `-51` | `vendite.trgfn_doc_indirizzi_seguono_cliente` e i quattro montaggi `trg_<t>_m50_indirizzi_seguono_cliente_upd` (DDT, preventivo, offerta, contratto) |
| `20_code/script/20261011-52` | check `script.fn_check_indirizzi_documento_cliente` |
| `20_code/script/20261011-53` | `script.fn_check_ddt_emittibile`, punto 4-bis |
| `20_code/vendite/20261011-54` | `vendite.trgfn_ddt_guard_indirizzi_obbligatori` solleva anche il codice nuovo |
| `20_code/script/20261011-55` | `script.fn_check_preventivo_emettibile`, motivo 3 |
| `20_code/vendite/20261011-56` / `script/-57` | offerta: guard `BOZZA → EMESSA` e capability (firma ancorata a `%TYPE`) |
| `20_code/vendite/20261011-58` / `script/-59` | contratto: guard verso `ATTIVO` e capability (firma ancorata a `%TYPE`) |
| `20_code/vendite/20261011-60` | `vendite.fn_create_contratto` chiama il BB in coda (`RETURNS TABLE` ancorato) |
| `20_code/vendite/20261011-61` | `vendite.fn_crea_revisione_offerta` copia gli indirizzi della rev.N, come la revisione del preventivo (D-4) |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` (`DATO_ERRATO`, messaggio 1288) |
| `db/pgtap/vendite/test-indirizzi-documento-seguono-cliente-v1.sql` | nuovo, 18 test |
| `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` | solo la testata (il brief e' in `work-done/`) |

Il `20261011-42` resta libero (Tid). Le funzioni copiate (`-53` … `-61`) partono dal corpo della doc
auto-generata o dall'ultimo changeSet allineato, con le sole righe nuove.

### 7.4 Prove (pre-apply, 2026-10-11)

Su `zeroerp_ci` (allineato fino a `20261011-41`), **come owner**, in transazione annullata: l'SQL
**estratto** dagli YAML `-43` … `-61` (i `changes`, non le `preConditions`), poi il pgTAP senza il suo
`BEGIN`. ⚠️ Cosa non copre: il seed del CSV e' **simulato** con `UPDATE` (il loader del mirror non e'
provato), il codice errore e' inserito a mano; da owner la RLS non c'e'. L'apply e la corsa come app
restano di Tid.

| Prova | Esito |
| --- | --- |
| `test-indirizzi-documento-seguono-cliente-v1` | 18/18 |
| Mutazioni, una alla volta | senza il trigger del cambio sul DDT: rossi 2 e 9; senza il guard sul preventivo: 2, 12, 13; check che torna sempre `[]`: 13-16; senza ripiego: 1, 5, 7, 9, 11, 13-17; senza il `-61`: 18 |
| Corpi di partenza (`-53` … `-61`) | i nove `pg_get_functiondef` del vivo su dbdev coincidono con la doc auto-generata |
| Regressione: 246 pgTAP che toccano indirizzi, gate, capability, contratti/offerte, piu' i presidi trasversali (`riferimenti-morti`, `rubinetto-primo-motivo`, `catalogo-messaggi-errore-completo`, `vw-codici-errore-motivo-nominato`, `storico-scope-policy`), ciascuno prima e dopo l'SQL estratto | **0 differenze**. I rossi presenti lo sono in tutte e due le corse (dati di macchina assenti su `zeroerp_ci`, o rosso da owner dichiarato) |
| **Post-apply (Tid, 2026-10-11)** | migrazione applicata su dbdev (`-43` … `-61` EXECUTED, mirror `20260711-18` RERAN col CSV nuovo), **pgTAP verdi** nella corsa come app: la RLS e il loader del CSV, che la prova pre-apply non copriva, sono provati qui |
| Col `-61`: i 13 pgTAP che usano la revisione dell'offerta o i suoi indirizzi (revisione, radice, emissione, end-to-end, gemelle, debiti residui, prezzi autorizzati, RLS dei satelliti, simmetria, lock, testata dopo l'emissione, rubinetto), prima e dopo | **0 differenze**, tutti verdi |

⚠️ Fra i rossi «di prima» ci sono anche `test-fn-genera-ddt-da-ordine-v1` (test 2), `test-fn-crea-revisione-preventivo`
(2) e `test-snapshot-indirizzi-fattura-v1` (1, 2): le loro altre asserzioni, che passano dalla cascata
degli indirizzi e quindi dal guard d'origine, sono verdi prima e dopo. La conferma piena e' la corsa di Tid.

### 7.5 Decisioni per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D-4** | La revisione dell'offerta copia gli indirizzi della madre, come quella del preventivo? | ✅ **Si', in questo giro** (Tid, 2026-10-11): `20261011-61`, test 18 |
