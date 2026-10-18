# Brief DB — Gli indirizzi del documento seguono il cliente

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: Tid (apply del §8.7 e pgTAP; collaudo §8.5 e §8.6.4). Il lato DB del §8.7 e' scritto e provato (§8.7.4).**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | **Tid** | Apply di `20261018-65` … `-68` e dei due codici (mirror di `codici_errore` e `messaggi_errore`), poi i pgTAP come app | §8.7.4 | niente |
| 2 | **BE** | R-BE-8 (policy e ripiego dei due codici) **nello stesso giro dell'apply**; poi R-BE-9 e R-BE-10 | §8.7.3 | 1 |
| 3 | **Tid** | Collaudo in-app: slot di default e cambio di cliente in bozza su DDT, preventivo e offerta (§8.5); scheda precompilata e cambio di cliente del contratto (§8.6.4); emittente e utility spenti in modifica su preventivo, offerta e contratto (R-FE-5) | §8.5, §8.6.4, §8.7.3 | 1, 2 |
| 4 | **Tid** | Archiviazione in `work-done/` | — | 3 |

**Decisioni aperte di Tid: nessuna.** La forma del §8.7 (la colonna «ferma sempre» nel montaggio
del lock di testata, due codici nuovi) era scelta del team DB: e' motivata nel §8.7.4, se Tid la
vuole diversa lo dice prima dell'apply.
✅ **Committato** su `dev/db-tid` il 2026-10-18 (i quattro changeSet, le righe dei due codici, il
pgTAP nuovo e i tre adeguati, le pagine `manual/`, la guida dei contratti, questo documento).
Corsa di Tid su `zeroerp_ruoli` dopo l'apply (2026-10-18): nessuna regressione del giro; i quattro
rossi segnalati erano rossi di fixture della baseline dello scratch (§8.7.4 non c'entra), sistemati
a parte.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10. **A chi:** team DB; poi BE/FE (§6).
> **Origine:** §12.3 di [brief-db-esecutivi-ba-coppia](../work-done/brief-db-esecutivi-ba-coppia.md).
> Dal giro di quel brief il cliente di un DDT si sceglie, si cambia e si toglie **in bozza**. Gli
> indirizzi del documento gia' scritti non lo seguono.
> **Stato:** ✅ **lato DB applicato e verde il 2026-10-11** (§7): `20261011-43` … `-61` e i tre CSV, pgTAP
> verdi nella corsa di Tid (§7.4). D-4 decisa e fatta nello stesso giro (§7.5). ✅ **BE/FE scritti e verdi**
> (2026-10-12, §8): R-BE-1 … R-FE-2. ✅ **La scheda di fornitura segue il cliente** (§8.4): lato DB
> applicato e verde il 2026-10-12 (`20261012-34` … `-42`, pgTAP verdi nella corsa di Tid). ⏳ Restano il
> collaudo in-app di Tid (§8.5), la ricaduta BE/FE del §8.4.6 e il cambio di cliente del **contratto** in
> bozza (§8.3). ✅ **§8.3 e §8.4.6 fatti il 2026-10-14** (§8.6). ⏳ Restano il collaudo e la richiesta DB
> del §8.7. ✅ **§8.7 lato DB scritto e provato il 2026-10-18** (§8.7.4): da applicare.
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
| **R-BE-1** | BE | Al posto di `auto_assegna_indirizzo_default` il BE chiama **`SELECT vendite.fn_doc_indirizzo_default(<documento>, <id>)`** negli stessi punti: dopo la creazione di DDT, ordine, preventivo e offerta (`ddt_service:365`, `ordini_service:457`, `preventivi_service:557`, `offerte_service:572`) e dopo i verbi con cascata (`crea_ddt_da_ordine`, push preventivo → ordine, push offerta → contratto). Selettori: `DDT`, `ORDINE`, `PREVENTIVO`, `OFFERTA`, `CONTRATTO`. Dopo `create_contratto_atomico` **non** serve: `vendite.fn_create_contratto` lo fa da sé. Si ritirano `auto_assegna_indirizzo_default`, `_tipo_default` e `auto_assegna_indirizzo_default_contratto`: la priorita' fra i tipi e' ora un dato (§7.2 a). ⚠️ Non e' piu' best-effort: un errore del DB (non uno slot vuoto, che torna `false`) sale come gli altri. 📌 I selettori si usano **come sono**: questo giro si chiude coi codici corti, e li migra il lotto 2 di [brief-db-grammatica-unica-documenti](brief-db-grammatica-unica-documenti.md) (§5 G-4, Tid 2026-10-18) |
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

## 8. Sviluppo BE/FE (sessione BE, `dev/backend-tid`, 2026-10-12)

### 8.1 Decisioni di Tid (2026-10-12)

| # | Domanda | Decisione |
| --- | --- | --- |
| **B-1** | Il cliente del contratto si cambia in bozza? Il DB lo ammette (lock solo fuori DRAFT, §7.1), il backend lo vietava sempre (`contratti_service._FORBIDDEN_TESTATA_UPDATE`) | ✅ **Si'**, come preventivo e offerta. Lavoro in §8.3 |
| **B-2** | Chi crea un documento con una cascata, oltre ai tre di R-BE-1, chiama il building block? | ✅ **La riconsegna dal reso si'** (un DDT nuovo con cascata, gemello del DDT da ordine). **Le revisioni** di preventivo e offerta **no**: copiano la versione precedente com'e', slot vuoto compreso |
| **B-3** | Al cambio di cliente si chiede conferma? | ✅ **No**, cambio in silenzio: gli indirizzi tolti sono copie dell'anagrafica, lo slot di default si riempie dal cliente nuovo, gli una-tantum restano. Il pannello si ricarica |
| **B-4** | Sul contratto, l'emittente si cambia in modifica? | ✅ **No, come il preventivo**: si cambiano solo BA e istanza, in coppia (§8.3) |

### 8.2 Cosa e' stato fatto

| # | Che cosa |
| --- | --- |
| **R-BE-1** | Il mixin `IndirizziDocumentoRepositoryMixin` ha `riempi_indirizzo_default(id)` → `vendite.fn_doc_indirizzo_default(<documento>, id)`; ogni repository dichiara il selettore (`_indirizzi_documento`). Chiamato **nella transazione della creazione** (non e' piu' best-effort: un errore annulla anche la testata; `ATOMIC_REQUESTS` e' spento) in `crea_ddt`, `crea_ddt_da_ordine`, `genera_ddt_riconsegna` (B-2), `crea_ordine` (copre la conversione da offerta), `crea_ordine_da_preventivo`, `crea_preventivo`, `crea_offerta`, `push_a_contratto` dell'offerta (il verbo scrive la testata da se', non passa da `fn_create_contratto`). Tolta la chiamata dopo `create_contratto_atomico`. Ritirati `auto_assegna_indirizzo_default`, `_tipo_default`, `auto_assegna_indirizzo_default_contratto` |
| **R-BE-2** | Tolti da `upsert_indirizzo_documento` i due `require` sull'ownership (picker e origine soggetto dichiarata). Il codice e' gia' mappato dalla policy generata: arriva `E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, 400, campo `tipo_indirizzo_id` (provato sul DB vero, §8.5). ⚠️ Una differenza col Python, voluta: su un documento **senza cliente** il DB lascia passare una riga che dichiara un'origine soggetto (il predicato torna NULL), il Python la rifiutava; quando il cliente arriva, il trigger del cambio la toglie se non e' sua |
| **R-BE-3** | `get_soggetto_ruolo_documento`, `get_ancora_indirizzi_documento` e `resolve_indirizzo_documento` non avevano altri utilizzatori: ritirati, con gli attributi `_indirizzi_documento_table`, `_indirizzi_doc_sr_column`, `_indirizzi_doc_istanza_column`. Il cliente del documento lo legge il DB (`script.fn_get_cliente_testata_documento`). Lo smoke `smoke-indirizzi-documento-catena.py` interroga la catena con l'SQL |
| **R-FE-2** | `DocumentoIndirizziSection` osserva l'identita' del cliente che il drawer le passa dal `detail` salvato (`soggettoRuoloId`, `istanzaUtilityId`): se un cliente c'era e cambia, ricarica. Da vuota a valorizzata (apertura, cambio di documento) no: carica gia' il watch su `docId`. Vale per i cinque drawer senza toccarli |

### 8.3 ✅ Il cambio di cliente del contratto in bozza (B-1) — fatto il 2026-10-14 (§8.6)

* **Regola del 2 — ✅ ok di Tid (2026-10-12).** Il preventivo risolve il
  cliente per coppia BA/istanza in `preventivi_service._risolvi_cliente_preventivo`
  (dal lato che il payload porta, BA della coppia `(istanza, utility)`, codici
  `E_PREV_*`). Il contratto ne sarebbe la seconda copia: si estrae un BB in
  `apps/vendite`, con i codici per dominio, e si ritira la copia del preventivo
  nello stesso giro. ⚠️ L'estrazione si fa **insieme** al contratto, non prima:
  un BB con il solo preventivo come consumatore sposterebbe il codice senza
  centralizzare niente (AGENTS.md, regola del 2).
* ✅ **Era bloccante il difetto del §8.4, consegnato il 2026-10-12** (§8.4.5): al
  cambio di coppia la scheda di fornitura la rifa' il DB. Vedi R-BE-6: la scheda
  del form non si riapplica sopra.
* **Emittente — ✅ deciso da Tid (2026-10-12): come il preventivo.**
  `emittente_fiscale_id` resta fuori dall'aggiornamento del contratto (in
  `_FORBIDDEN_TESTATA_UPDATE`), come `utility_id`. Escono dal divieto ed entrano
  in `UPDATE_KEYS_TESTATA` i soli `billing_account_id` e `istanza_utility_id`,
  risolti in coppia dal BB. Se il BA nuovo non e' dell'emittente del contratto
  lo dice il guard DB (`script.trgfn_doc_guard_emittente_ba`,
  `E_DOC_EMITTENTE_BA_INCOERENTE`); il commento sul divieto dell'emittente va
  riscritto, perche' la sua premessa («il BA e' immutabile») cade.

Ordine: il team DB consegna il §8.4 → BE (BB + contratto + ritiro della copia del
preventivo) e FE nello stesso giro.

Lato BE: `billing_account_id` e `istanza_utility_id` escono da
`_FORBIDDEN_TESTATA_UPDATE` ed entrano in `UPDATE_KEYS_TESTATA`, risolti dal
BB; `utility_id` ed `emittente_fiscale_id` restano immutabili come sul
preventivo (B-4). Lato FE: il BA
del `ContrattoDrawer` in modifica oggi e' un `InputText` disabilitato, e dopo il
salvataggio in modifica il drawer **non** ricarica `detail`, che e' la fonte del
R-FE-2: va ricaricato come fanno DDT, preventivo e offerta.

### 8.4 ✅ Richiesta al team DB — la fornitura del documento non segue il cliente

> Per decisione di Tid (2026-10-12) la richiesta sta **in questo brief**. ✅ Consegnata
> e applicata il 2026-10-12 (§8.4.5); ricaduta BE/FE nel §8.4.6.

#### 8.4.1 Il difetto (sessione BE, 2026-10-12)

Trovato scrivendo il §8.3, sul contratto (la struttura):
`vendite.offerte_commerciali_utilities` e `vendite.contratti_utilities` hanno
una loro **copia** di `istanza_utility_id` e `utility_id` (NOT NULL), e
`istanza_dati_precontrattuali_id`. Nessun vincolo e nessun trigger le lega alla
testata: la FK composta `fk_<doc>_ba_coppia` e' sulla testata, i satelliti hanno
FK semplici, e nessuna funzione le riallinea.

* **Offerta, oggi**: il cliente si cambia in bozza
  (`UPDATE_KEYS_OFFERTA` ha BA e istanza) e il BE toglie `istanza_utility_id` /
  `utility_id` dall'aggiornamento della fornitura (immutabili). Un'offerta che
  cambia istanza tiene la fornitura sull'istanza di prima, e la cascata la porta
  sul contratto (`fn_push_offerta_a_contratto`).
* **Contratto**: il DB ammette il cambio in DRAFT (§7.1), con lo stesso esito.

E' lo stesso difetto di questo brief, sulla fornitura invece che sugli
indirizzi: un dato del documento preso dal cliente che non lo segue quando il
cliente cambia.

#### 8.4.2 Il perimetro vero: e' la riga intera, non la coppia (team DB, 2026-10-12)

Sul contratto la fornitura la scrive `vendite.trgfn_contratti_snapshot_precontrattuali`
(`trg_contratti_z90_snapshot_precontrattuali_ins`, **solo** `AFTER INSERT`), e la
prende **tutta** da `anagrafiche.istanze_dati_precontrattuali` di `(istanza, utility)`:
`istanza_dati_precontrattuali_id`, `classe_utenza_id`, `tipo_utenza_id` (dalla classe),
`param_1_num`, `param_2_txt`, `meta`. Quando l'istanza cambia, e' stantia l'intera
riga, non solo la coppia `istanza_utility_id` / `utility_id`.

Chi la legge rende il difetto un errore di prezzo e d'imposta, non solo di
anagrafica:

* `vendite.fn_resolve_prezzo_listino_v2_esito` prende da `contratti_utilities` la
  `classe_utenza_id` della fornitura del contratto (stadio di contratto del pricing);
* `vendite.fn_get_tipo_utenza_fornitura` (ripiego dello stadio A del risolutore IVA)
  raggiunge il tipo d'uso solo da `contratti_utilities`.

Sull'**offerta** la riga ha un'altra natura: la scrive il backend dal payload
(`CREATE_KEYS_UTILITY`: coppia, `istanza_dati_precontrattuali_id`, tipo e classe,
parametri, `meta`), e l'operatore ne cambia in bozza tutto tranne la coppia
(`UPDATE_KEYS_UTILITY`). Il push al contratto la copia 1:1 sopra quella appena
fotografata dal trigger (`INSERT … ON CONFLICT … DO UPDATE`): l'offerta vince.

#### 8.4.3 Le forme scartate, e perche'

| Forma proposta in §8.4.1 | Esito | Perche' |
| --- | --- | --- |
| Togliere la copia (la fornitura legge istanza e utility dalla testata) | ⛔ non basta | Riallinea la coppia e lascia classe, tipo, parametri e `istanza_dati_precontrattuali_id` della fornitura di prima |
| FK composta verso la testata con `ON UPDATE CASCADE` | ⛔ non basta, ed e' peggio | Stesso risultato: la riga **sembra** coerente con la testata e descrive un'altra fornitura, e il pricing e l'IVA la leggono |
| Il trigger del cambio di cliente la riallinea | ✅ la direzione | Sul contratto: la riga si **rifa'** dai dati precontrattuali del cliente nuovo, con lo stesso building block della nascita (la regola del 2: oggi il corpo vive nel trigger d'`INSERT`). Un vincolo sulla coppia testata/fornitura la rende non divergibile (un guard, D-6). Consegna nel §8.4.5 |

✅ **D-5 di Tid (2026-10-12) — la fornitura dell'offerta al cambio di cliente: strada a.**
Rifarla dall'anagrafica, come sul contratto, cancella quello che l'operatore ha
scritto; tenerla com'e' lascia `istanza_dati_precontrattuali_id` e la coppia sul
cliente di prima, e il push la porta sul contratto. Le strade:

| # | Strada | Che cosa comporta |
| --- | --- | --- |
| **a** ✅ | **Si rifa'** dall'anagrafica del cliente nuovo, come sul contratto | Una sola regola per i due documenti; l'operatore riscrive classe e parametri se li aveva cambiati |
| b | Si riallineano coppia e `istanza_dati_precontrattuali_id`, i dati dell'operatore restano | La riga mescola una fornitura nuova con classe e parametri pensati per la vecchia |
| c | Il cambio d'istanza e' **rifiutato** su un'offerta che ha gia' la fornitura | Niente da riallineare; per cambiare cliente si toglie prima la fornitura |

Il perche', sul modello: classe, tipo d'uso e parametri descrivono la **fornitura**, non
una scelta commerciale; se la fornitura cambia, cambiano con lei. E' la stessa regola di
B-3 sugli indirizzi: le copie dell'anagrafica seguono il cliente, in silenzio. Una
correzione fatta a mano sulla fornitura di prima valeva per quella, e non si porta su
un'altra. La b e' scartata: e' la sola strada che lascia una riga incoerente senza che
nessuno lo veda.

#### 8.4.4 Decisioni di Tid sul disegno (2026-10-12)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-5-bis** | Un'offerta **senza** scheda di fornitura, quando cambia il contatore, la riceve dall'anagrafica? | ✅ **Si'**: regola unica, la scheda si rifa' dall'anagrafica sia sul contratto sia sull'offerta, c'era o no |
| **D-6** | Il presidio «la coppia della scheda e' quella della testata»: FK composta o guard? | ✅ **Guard** sulle due `*_utilities` col codice nuovo `E_DOC_FORNITURA_FUORI_TESTATA`; il BE interviene dopo (§8.4.6). ⛔ La FK `ON UPDATE CASCADE` delle linee qui sotto non regge: la cascata aggiorna la coppia della scheda **prima** del trigger che la rifa', e `trgfn_contratti_utilities_guard_tipo_classe` giudica la classe vecchia contro la utility nuova (utility con tipi d'uso ↔ senza: `E_CONTRATTO_UTILITY_*`). Una FK senza cascata scatta prima del trigger (i trigger RI precedono `trg_` in ordine di nome), una differita torna immediata nei pgTAP |
| **D-7** | Alla **nascita** del contratto ci sono la scheda dall'anagrafica (trigger) e quella dell'operatore (`p_utility` di `fn_create_contratto`): oggi collidono su `uq_contratti_utilities_contratto_id` e il contratto non si crea | ✅ **Vince l'operatore**, come nel push dall'offerta: l'anagrafica fa da base, le chiavi dell'operatore la correggono. ⚠️ **A patto che l'operatore veda i dati dell'anagrafica e li possa modificare**: il DB espone la scheda che scriverebbe (`vendite.fn_get_fornitura_da_anagrafica`) e il drawer la precompila (§8.4.6) |

#### 8.4.5 ✅ Consegna DB (team DB, 2026-10-12) — applicata e verde

**La forma.** Una regola, tre punti d'ingresso:

* **la lettura** `vendite.fn_get_fornitura_da_anagrafica(istanza, utility)`: la scheda
  che l'anagrafica da' alla coppia (record precontrattuale + tipo d'uso dalla classe).
  Sede unica: la scrive il building block, e il drawer la mostra (D-7);
* **il building block** `vendite.fn_doc_fornitura_da_anagrafica(documento, id)`: toglie
  la scheda e la riscrive da quella lettura. Lo chiamano la nascita del contratto
  (`trgfn_contratti_snapshot_precontrattuali`, ora un guscio) e il cambio di coppia in
  bozza (`trg_<t>_m50_fornitura_segue_cliente_upd` su contratto e offerta, `AFTER UPDATE`
  col `WHEN` su `istanza_utility_id`/`utility_id`: un cambio del solo BA a coppia ferma
  non la tocca);
* **il guard** `vendite.trgfn_doc_fornitura_guard_coppia` (`_a10_`, `BEFORE INSERT OR
  UPDATE OF` coppia e FK) sulle due schede: la coppia e' quella della testata (D-6).

Alla nascita del contratto `fn_create_contratto` applica la scheda dell'operatore con un
`UPDATE` sopra quella dell'anagrafica (D-7); `UPDATE` e non `ON CONFLICT`, perche' i
`BEFORE INSERT` giudicherebbero la riga proposta, parziale. Il `LIMIT 1` del vecchio
trigger e' sparito: un record precontrattuale per coppia
(`uq_istanze_dati_precontrattuali_id_utility_id`).

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261012-34` | mappa `vendite.fn_doc_fornitura_sede` (testata e scheda di CONTRATTO, OFFERTA) |
| `20_code/vendite/20261012-35` | lettore `vendite.fn_get_fornitura_da_anagrafica` |
| `20_code/vendite/20261012-36` | BB `vendite.fn_doc_fornitura_da_anagrafica` |
| `20_code/vendite/20261012-37` | `trgfn_contratti_snapshot_precontrattuali` chiama il BB (la copia della regola si ritira) |
| `20_code/vendite/20261012-38` / `-39` | guard `trgfn_doc_fornitura_guard_coppia` e i due montaggi |
| `20_code/vendite/20261012-40` / `-41` | `trgfn_doc_fornitura_segue_cliente` e i due montaggi `_m50_` |
| `20_code/vendite/20261012-42` | `fn_create_contratto`: la scheda dell'operatore corregge quella dell'anagrafica |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_DOC_FORNITURA_FUORI_TESTATA` (1291) e `E_DOC_FORNITURA_PARAMETRO_MANCANTE` (1292), entrambi `TECNICO` |
| `db/pgtap/vendite/test-fornitura-documento-segue-cliente-v1.sql` | nuovo, 17 test |
| `docs/it/dbzero/vendite/manual/` | `trgfn_contratti_snapshot_precontrattuali.md` (diceva «la scheda non si aggiorna mai») e `fn_create_contratto.md` |

**Prove (2026-10-12).**

| Prova | Esito |
| --- | --- |
| Pre-apply su `zeroerp_ci`, da owner, fuso ostile (Kiritimati): SQL **estratto** dagli YAML `-34` … `-42` + le righe dei due codici, poi il pgTAP | 17/17 |
| Mutazioni | senza `-41`: rossi 9-12, 15-17; senza `-39`: 13, 14; senza `-37` (la regola ricopiata nel trigger): 2; senza `-42`: torna la collisione su `uq_contratti_utilities_contratto_id` |
| Regressione: 59 pgTAP che toccano schede, contratti, offerte, revisione, push, precontrattuali, RLS dei satelliti, piu' i presidi trasversali (`riferimenti-morti`, `rubinetto-primo-motivo`, `catalogo-messaggi-errore-completo`, `vw-codici-errore-motivo-nominato`, `storico-scope-policy`, `stati-check-scrittori`), prima e dopo | **0 differenze** |
| Corpo di partenza del `-42` | il `-60` coincide con la doc auto-generata, salvo l'ancoraggio `%TYPE` del `RETURNS TABLE` |
| Apply (Tid) | `-34` … `-42` EXECUTED su dbdev il 2026-10-12 alle 17:29, codici caricati |
| Schede gia' fuori coppia su dbdev (Tid, query da owner) | zero righe: niente da bonificare |
| **Post-apply (Tid, 2026-10-12)** | migrazione applicata, **pgTAP verdi** nella corsa come app: la RLS, che la prova pre-apply da owner non copriva, e' provata qui |

#### 8.4.6 Ricaduta BE/FE

| # | Lato | Che cosa |
| --- | --- | --- |
| **R-BE-4** | BE | Codici nuovi `E_DOC_FORNITURA_FUORI_TESTATA` e `E_DOC_FORNITURA_PARAMETRO_MANCANTE` (`TECNICO`, 500, niente `campo`): policy rigenerata e frase di ripiego. ⛔ Nello stesso giro dell'apply, o la CI e' rossa sul lato BE (guardrail delle policy) |
| **R-BE-5** | BE | Lettura della scheda dall'anagrafica per il drawer: un endpoint che, data la coppia (istanza, utility), chiama `vendite.fn_get_fornitura_da_anagrafica` (zero o una riga). Nessuna copia della derivazione in Python |
| **R-FE-3** | FE | Condizione di Tid su D-7: in **creazione** di contratto e offerta, scelti BA/istanza, il drawer **precompila** la scheda di fornitura da R-BE-5 e l'operatore la vede e la corregge. Il contratto ora si crea anche su un contatore con dati precontrattuali e la scheda compilata (prima: «Questo contratto ha gia' una riga utility associata») |
| **R-BE-6** | BE | ⚠️ `offerte_service.aggiorna_offerta` aggiorna la testata e **poi** fa l'upsert della scheda (`_upsert_utility_inline`) nella stessa richiesta. Se la richiesta cambia la coppia, il trigger ha appena rifatto la scheda dal contatore nuovo e l'upsert ci scriverebbe sopra i valori del form, cioe' quelli del contatore di prima: D-5 svanirebbe in silenzio. Con un cambio di coppia la scheda del payload non si applica (o il FE non la manda). Lo stesso vale per il contratto quando il §8.3 apre il cambio di cliente |
| **R-FE-4** | FE | Dopo il salvataggio di un cambio di cliente in bozza (offerta; contratto col §8.3) la sezione della scheda di fornitura si **ricarica**, come gli indirizzi (R-FE-2) |
| ↳ *stato* | — | ✅ **Offerta, R-BE-6 e R-FE-4 fatti il 2026-10-13** (sessione BE, giro C2 di [piano-be-fe-magazzino-lotto-3](piano-be-fe-magazzino-lotto-3.md)): il cliente dell'offerta si cambia in bozza, `aggiorna_offerta` non applica la scheda del payload quando la coppia cambia, il form non la manda e rilegge il dettaglio. ✅ **R-BE-4 c'era gia'** (policy e ripiego dei due codici). ✅ **R-BE-5, R-FE-3 e R-BE-7 fatti il 2026-10-14** (§8.6) |
| **R-BE-7** | BE | Il §8.3 non e' piu' bloccato: il cambio di cliente del contratto lascia al DB la scheda di fornitura (la rifa' il trigger) |

### 8.5 Prove

* `apps/vendite/tests/db/test_indirizzi_seguono_cliente_db.py` (DB vero, 6 test,
  mondo fabbricato): la creazione riempie lo slot CON dal ripiego FATT; a slot
  pieno il building block torna `False`; il cliente cambiato in bozza porta lo
  slot sul cliente nuovo; picker e origine soggetto di un altro cliente
  rifiutati con `E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, 400, campo
  `tipo_indirizzo_id`; l'una-tantum si scrive.
* Unitari: `test_indirizzi_documento_helpers.py` riscritto (6 test, repository
  con `spec`: un ritorno al controllo Python fallirebbe; gli id del payload
  passano da `PayloadValidator`, un id non intero e' `E_<DOM>_VALIDAZIONE` e non
  un 500 da `int()` grezzo); un test per punto di
  chiamata (DDT, DDT da ordine, riconsegna, ordine, ordine da preventivo,
  preventivo, offerta, push al contratto; il contratto **non** lo richiama);
  gli errori del building block salgono.
* ⚠️ Trovato: `test_offerte_service.py` usa `unittest.TestCase`, che **non**
  vieta il DB (api.md §Test). I due test del push al contratto hanno chiamato
  `fn_doc_indirizzo_default` sul DB configurato prima che `ContrattiRepository`
  fosse patchato. Verificato in lettura col contesto operatore: il contratto
  101 non esiste, nessuna riga di `contratti_indirizzi` nata nella finestra
  delle corse. Ora e' patchato; la classe resta un debito (`SimpleTestCase`).
* Suite BE con `ZEROERP_TEST_DB_E2E=1`: 6549, verdi tranne i due guardrail
  delle policy, rossi per `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`
  (brief-db-date-consegna-righe-in-blocco): il codice e' a DB ma il suo seed
  non e' ancora in git, quindi non si rigenera (DB avanti a git). ruff e mypy
  puliti. Smoke `smoke-indirizzi-documento-catena.py` verde.
* FE: vitest 813 verdi (spec della sezione 7-8 nuovi), lint, guard e build verdi.
  Poi la sezione ha preso anche una guardia contro le risposte stantie
  (`useFetchVersion`) e la ricarica solo a parita' di documento: spec 9 verdi.
  Rilettura critica dello stesso giorno: il watch sul cliente ricaricava anche al
  **cambio di documento** (doppia `list` in gara con quella del watch su `docId`)
  e `load()` non scartava le risposte stantie. Ora ricarica solo sullo stesso
  documento, con `useFetchVersion`; spec 9, provato per mutazione.
* ⏳ **Collaudo in-app (Tid)**: un DDT nuovo nasce con la Consegna del cliente;
  cambiato il cliente in bozza, il pannello mostra quella del cliente nuovo e
  una consegna scritta a mano resta; un preventivo e un'offerta che cambiano
  cliente fanno lo stesso; il DDT da ordine e la riconsegna tengono la consegna
  della sorgente.

### 8.6 Giro BE/FE del 2026-10-14 (sessione BE, `dev/backend-tid`)

#### 8.6.1 Decisioni di Tid (2026-10-14)

| # | Domanda | Decisione |
| --- | --- | --- |
| **E-1** | R-BE-5: un endpoint nuovo, o i form-defaults di contratto e offerta, che dal BA ricavano gia' istanza e utility e che il drawer chiama al cambio di BA (`useBaFormDefaults`)? | ✅ **I form-defaults**: la scheda e' un default che dipende dal cliente. Nessun endpoint e nessun watcher nuovi |
| **E-2** | Il drawer del contratto mostrava solo tipo e classe; i due parametri della scheda no (l'offerta si'). La condizione di D-7 vuole che l'operatore veda cio' che l'anagrafica scrive | ✅ **I due parametri anche sul contratto**, come sull'offerta |
| **E-3** | L'offerta cambiava cliente senza risolutore (la coppia andava al DB com'era, e la fermava la FK composta), e in modifica lasciava cambiare emittente e utility, che preventivo e contratto fermano (B-4) | ✅ **Terzo consumatore del BB**; emittente e utility fermi anche sull'offerta. ⚠️ Quest'ultima e' una regola di dominio: la scrive il DB (§8.7), il BE/FE la legge dopo |

#### 8.6.2 Cosa e' stato fatto

| # | Che cosa |
| --- | --- |
| **BB** | `apps/vendite/services/_cliente_coppia_documento.py` (regola del 2): `risolvi_cliente_coppia` — il cliente letto dal lato che il payload porta, codici e frase del dominio chiamante — e `coppia_cambiata`. Consumatori: preventivo (la copia `_risolvi_cliente_preventivo` e' ora un adattatore dei suoi codici), contratto, offerta. Ritirata la copia locale dell'offerta (`_COPPIA_FORNITURA`, `_come_testo`). Catalogo BB backend aggiornato |
| **R-BE-7** | `ContrattiService.update_contratto`: `billing_account_id` e `istanza_utility_id` escono da `_FORBIDDEN_TESTATA_UPDATE` ed entrano in `UPDATE_KEYS_TESTATA` e in `TESTATA_UPDATE_COLUMNS`, risolti dal BB sulla utility della testata; `utility_id` ed emittente restano fermi (B-4), col commento riscritto. La frase della FK composta e del BB e' una sola |
| **Difetto** | ⛔ **Trovato**: in modifica il drawer del contratto mostrava tipo e classe utenza modificabili in bozza, ma la PATCH non li portava e il backend non li accettava: «contratto salvato», niente scritto. Ora la PATCH porta la scheda inline (`UPDATE_KEYS_CONTRATTO` = testata + `utility`, come l'offerta), nella stessa transazione; con un cambio di coppia non si applica (R-BE-6 sul contratto) |
| **R-BE-5** | `fornitura_da_anagrafica` in `_documento_eccezioni_repo.py` (le letture comuni di contratto e offerta) su `vendite.fn_get_fornitura_da_anagrafica`; i form-defaults di contratto e offerta portano `fornitura` (E-1). Manual `api_vendite_form_defaults.md` aggiornato |
| **R-FE-3** | BB `vendite/_shared/fornitura/schedaFornitura.js` (regola del 2: le due copie della scheda nei drawer erano gia' divergenti). In creazione la scheda segue il cliente scelto (callback `apply` di `useBaFormDefaults`), e un cliente senza dati precontrattuali la svuota. Il contratto spedisce in creazione la scheda com'e' a video (D-7: quello che si vede e' quello che si scrive) |
| **§8.3 FE** | `ContrattoDrawer`: il BA si sceglie anche in modifica (spento da `isLocked('billing_account_id')`, cioe' dal lock di testata del DB); la PATCH in bozza porta BA e istanza; la scheda parte se `can_edit_utility` e il cliente non cambia; dopo il salvataggio il dettaglio si rilegge (prima no), cosi' la scheda e gli indirizzi rifatti dal DB arrivano nel form (R-FE-4). I due parametri della scheda nel form (E-2) |
| **Offerta** | `aggiorna_offerta` risolve il cliente col BB; `OffertaDrawer` usa il BB della scheda e riceve la scheda precompilata in creazione |

#### 8.6.3 Prove

* Unitari: `test_contratti_cambio_cliente.py` (nuovo, `SimpleTestCase`, 10 test: la coppia dal BB sulla
  utility della testata, utility ed emittente rifiutati, la scheda inline creata o aggiornata, il cambio di
  cliente che non la applica, l'id in testo, la coppia nella scheda rifiutata, il BB vero con un BA
  d'altri); i guardrail della catena della PATCH del contratto con i due campi nuovi; i due test
  dell'offerta col BB; i form-defaults con la scheda (4 test). Provati per mutazione (la guardia sul
  cambio di cliente, il calcolo della coppia, la chiamata della lettura).
* DB vero: `vendite/tests/db/test_contratto_cliente_e_fornitura_db.py` (nuovo, 5 test, mondo fabbricato
  come il pgTAP del team DB): la lettura della scheda, i form-defaults, il cambio di cliente con la scheda
  rifatta dal DB e non dal form, la scheda del form scritta a cliente fermo, il BA d'altri rifiutato sul
  BA. La guardia del cambio di cliente provata per mutazione anche qui.
* Suite `apps.vendite` + `apps.core`: 4019 verdi. mypy a cricchetto: nessun rilievo nuovo. ruff pulito.
* FE: vitest 879 verdi (`schedaFornitura.spec.js` nuovo, 5 test, provato per mutazione), lint, guard,
  build e `check_i18n_keys` verdi. Due chiavi nuove: `vendite.contratti.field_param_1_num` /
  `field_param_2_txt` (it, en).

#### 8.6.4 Collaudo in-app (Tid)

* Contratto nuovo su un cliente con dati precontrattuali: scelto il BA, la scheda (tipo, classe, i due
  parametri) si riempie dall'anagrafica; corretta e salvata, il contratto la porta com'e' a video.
  Cambiato il BA prima di salvare, la scheda passa al cliente nuovo (vuota se non ne ha).
* Contratto in bozza: cambiato il cliente e salvato, la testata, la scheda e gli indirizzi sono del
  cliente nuovo. A cliente fermo, cambiati classe o parametri e salvato, restano (prima si perdevano).
* Offerta nuova: la scheda si precompila allo stesso modo.
* Contratto attivo: il BA e la scheda sono spenti.

### 8.7 Richiesta al team DB — emittente e utility fermi in modifica

> Per decisione di Tid (2026-10-14, E-3) la richiesta sta in questo brief, come quella del §8.4.

#### 8.7.1 Il difetto

«Emittente e utility di un documento non si cambiano in modifica: si cambia il cliente, dentro la
stessa utility» (B-4 di Tid, 2026-10-12, per contratto e preventivo; esteso all'offerta il 2026-10-14)
e' una regola di dominio, e oggi la scrive solo il backend, in tre modi diversi:

| Documento | `utility_id` | `emittente_fiscale_id` | Lo dice il DB? |
| --- | --- | --- | --- |
| Preventivo | fuori dalla whitelist di modifica | fuori dalla whitelist di modifica | ✅ la utility, nella capability (`c_sempre_non_edit` di `script.fn_available_actions_preventivo`); l'emittente no |
| Contratto | rifiutato (`_FORBIDDEN_TESTATA_UPDATE`) | rifiutato | ❌ |
| Offerta | **ammesso** (`UPDATE_KEYS_OFFERTA`) | **ammesso** | ❌ — e il drawer accende l'emittente in bozza, perche' la capability non lo ferma (la utility la spegne il BA scelto) |

Il guard `script.trgfn_doc_guard_emittente_ba` impedisce un emittente incoerente col BA, e la FK
composta un BA fuori coppia; nessuno dei due impedisce di **cambiare** emittente o utility insieme al
cliente.

#### 8.7.2 La richiesta

* le due colonne fra quelle «sempre» ferme nella capability di offerta, contratto e preventivo
  (`c_sempre_non_edit`), perche' il form le legga da `non_editable_fields` (la stessa forma di
  `utility_id` sul preventivo);
* un presidio in scrittura sulle tre testate (il lock di testata o un guard), col suo codice, perche' la
  regola valga anche fuori dal backend.

Forma, codice e nome sono scelte del team DB.

#### 8.7.3 Ricaduta BE/FE (dopo la consegna)

> Riscritta dal team DB il 2026-10-18 sulla forma consegnata (§8.7.4). ⛔ R-BE-8 va fatta **nello
> stesso giro dell'apply**: senza, la CI e' rossa sul lato BE (guardrail delle policy).

| # | Lato | Che cosa |
| --- | --- | --- |
| **R-BE-8** | BE | Codici nuovi **`E_DOC_UTILITY_IMMUTABILE`** ed **`E_DOC_EMITTENTE_IMMUTABILE`** (`CONFLITTO_STATO`, 409, **niente `campo`**, come la famiglia dei lock; VARIADIC lo stato): policy rigenerata e frase di ripiego |
| **R-BE-9** | BE | `offerte_service`: `utility_id` ed `emittente_fiscale_id` escono da `UPDATE_KEYS_OFFERTA`; il BB della coppia prende la utility dalla testata. Finche' non escono non si rompe niente: un `UPDATE` allo stesso valore passa (il lock guarda il cambio), uno diverso prende il codice nuovo |
| **R-BE-10** | BE | Contratto e preventivo: il divieto Python (`_FORBIDDEN_TESTATA_UPDATE`, la whitelist del preventivo) si puo' ritirare. Il codice del DB **non** porta il campo (`CONFLITTO_STATO`): se il BE vuole l'errore sul campo lo tiene come errore anticipato, altrimenti si ritira. Scelta del BE |
| **R-FE-5** | FE | Niente da scrivere: in modifica i due campi si spengono da soli, perche' le capability di preventivo, offerta e contratto ora li mettono in `non_editable_fields` **anche in bozza**. Da verificare nel collaudo sull'offerta (prima l'emittente si accendeva in bozza) |

#### 8.7.4 ✅ Consegna DB (team DB, 2026-10-18) — da applicare

**La forma: una colonna «ferma sempre» nel montaggio del lock di testata.** Il terzo elemento di
una terna di `vendite.trgfn_doc_testata_lock_fuori_bozza` puo' essere `-`: la colonna non si
cambia in nessuno stato, bozza compresa. Sui montaggi di preventivo, offerta e contratto
`utility_id` ed `emittente_fiscale_id` passano a `-`.

Perche' qui e non nel registro dei lock di colonna (`dbops.automation_lock_columns`, la forma
dell'ordine e del billing account):

* **la capability la legge gia'**: `non_editable_fields` esce dal montaggio del lock di testata
  (`script.fn_doc_testata_in_stato`). Col registro serviva la lista `c_sempre_non_edit` in tre
  capability, cioe' una seconda copia della regola; cosi' la copia del preventivo si **ritira**;
* **parla per prima**: il lock e' in fascia `_a05_`. Il trigger generato dal registro
  (`trg_*_a10_lock_columns_upd`) verrebbe dopo `trg_*_a10_guard_emittente_ba` e
  `_guard_emittente_scope`, e un cambio di emittente si sarebbe sentito rispondere «emittente
  incoerente col billing account», cioe' un rimedio che non e' il rimedio;
* niente convergenza dei trigger generati su dbdev (il job notturno o un `CALL` a mano).

**I codici sono nuovi**: la frase di `E_DOC_CLIENTE_FUORI_BOZZA` e di `E_DOC_EMITTENTE_FUORI_BOZZA`
dice «si sceglie solo in bozza», che qui sarebbe falso. DDT, reso e ordine tengono i loro.

| changeSet | Che cosa |
| --- | --- |
| `20_code/script/20261018-65` | grammatica `script.fn_doc_lock_regola`: la terna con `-`, la chiave `ferma_sempre`; `-` insieme a degli stati e' un montaggio sbagliato |
| `20_code/script/20261018-66` | decisione `script.fn_doc_lock_colonna_bloccata`: una colonna ferma sempre si ferma anche in bozza; per le righe niente cambia |
| `20_code/vendite/20261018-67` | i tre montaggi rimontati (utility → `E_DOC_UTILITY_IMMUTABILE`, emittente → `E_DOC_EMITTENTE_IMMUTABILE`, terna `-`), COMMENT della funzione del trigger |
| `20_code/script/20261018-68` | `script.fn_available_actions_preventivo`: via `c_sempre_non_edit` (la sola `utility_id`), firma ancorata a `%TYPE` |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | i due codici, `CONFLITTO_STATO`, messaggi 1359 e 1360 |
| `db/pgtap/vendite/test-doc-emittente-utility-fermi-v1.sql` | nuovo, 18 test |
| `db/pgtap/vendite/test-fornitura-documento-segue-cliente-v1.sql` | test 12: il contratto portato su un'altra utility ora e' **rifiutato** e la scheda resta quella di prima (era «la scheda dell'altra utility»: il caso non e' piu' raggiungibile dalla testata) |
| `db/pgtap/vendite/test-testata-dopo-emissione-v1.sql` | la matrice dice `-` per le sei colonne (test 3), i codici nuovi fra quelli di lock (21), in testa a `non_editable_fields` del preventivo c'e' la data (25) |
| `db/pgtap/script/test-doc-lock-montaggio-v1.sql` | test 4: la regola porta `ferma_sempre` |
| `docs/it/dbzero/*/manual/` | `fn_doc_lock_regola`, `fn_doc_lock_colonna_bloccata`, `fn_doc_testata_in_stato`, `trgfn_doc_testata_lock_fuori_bozza`, `fn_available_actions_preventivo`, `trgfn_doc_guard_emittente_ba`; la guida `gestione-contratti.md` §6.1 |

⚠️ **Censito il 2026-10-18, chi scrive le due colonne in `UPDATE`**: nessun verbo e nessun trigger
del DB (l'emittente lo scrive solo `trgfn_default_emittente_fiscale`, in `INSERT`); fra i pgTAP solo
il test 12 della fornitura. Lato BE l'offerta (R-BE-9).

⚠️ Il caso che aveva deciso D-6 (§8.4.4: un contratto che passa da una utility senza tipi d'uso a
una con) **non e' piu' raggiungibile** dalla testata. Il guard della coppia sulla scheda resta:
protegge la scheda da chi la scrive con un'altra coppia (test 13 e 14 della fornitura).

**Prove (2026-10-18), su `zeroerp_ruoli` allineato fino a `20261018-64`, da owner, in transazione
annullata**: l'SQL **estratto** dagli YAML `-65` … `-68`, i due codici inseriti a mano come li
caricherebbe il mirror, poi il pgTAP senza il suo `BEGIN`. ⚠️ Non coperto: il loader dei CSV, e
la RLS (da owner non c'e'). L'apply e la corsa come app restano di Tid.

| Prova | Esito |
| --- | --- |
| `test-doc-emittente-utility-fermi-v1` | 18/18 |
| Mutazioni, un changeSet tolto alla volta | senza `-66`: rossi 3, 5-10, 14-16; senza `-67`: 4, 5-10, 14-16; senza `-68`: 17 |
| I tre pgTAP adeguati (fornitura, testata dopo l'emissione, montaggio del lock) | 17/17, 26/26, 30/30 |
| Regressione: 64 pgTAP che toccano le tre testate, le loro capability, il lock di testata, la nascita e la revisione di contratto, offerta e preventivo; «prima» (versione di `HEAD`, senza l'SQL) e «dopo» (versione di lavoro, con l'SQL) | **0 differenze**. 12 file hanno rossi o errori, **uguali** nelle due corse (ambiente: scratch da owner) |
| Corpi di partenza | `pg_get_functiondef` su dbdev il 2026-10-18, uguali alla doc auto-generata |

Fuori perimetro, detto per completezza: sull'**ordine** la utility e' ferma solo fuori bozza nel
montaggio, ma il billing account ha il lock assoluto e la utility la deriva il DB dal BA; su
**DDT e reso** l'emittente in bozza si cambia ancora (B-4 riguardava contratto e preventivo, E-3
l'offerta).
