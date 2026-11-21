# Brief DB — i doppioni del soggetto sul fornitore

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), revisione `/verifica` del 2026-11-21. **A chi:** team DB
> (`dev/db-tid`); Tid per le decisioni aperte.

## ⏭️ Chi riparte — aggiornato al 2026-11-21

**Riparte: Tid**, col commit del lavoro BE/FE non committato (il §4, §6; il test e2e del regime spento, §7.2 «Dopo il
push») e il collaudo a video del drawer; poi **la sessione DB** con la nota sul motivo del pgTAP (§7.2, punto 4 di
«Dopo il push») e l'archiviazione. La D-6 nella forma della D-7 «2» è applicata e pushata (`20261121-10` … `-15`,
`790fc0432`, PR #185), e la sessione BE/FE l'ha provata sui due drawer. Il `/verifica-db` dei giri
A e B è fatto (§7) e la doc auto-generata è rigenerata (`eaed059e6`).
Lista e dettaglio dei fornitori tornano a funzionare sul DB vero (§6). I giri A e B (`20261121-01` … `-07`, §5.5 e §5.6)
sono applicati su dbdev con i pgTAP verdi (§5.7) e committati in `4ea18ba7d1`. D-1 … D-5 decise. Il primo passaggio
BE/FE è committato (`56c7fee9f6`, PR #182). D-6 «a» e D-7 «2» decise (Tid, 2026-11-21, §7.2: la «1» è stata rivista da Tid nella sessione DB); nessuna decisione aperta.

| # | Chi | Che cosa | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ team BE/FE | Form, dettaglio, PATCH e creazione del fornitore senza i sei campi (2026-11-21) | — |
| 2 | ✅ Tid | D-1 «a», D-2 «non serve» (2026-11-21) | — |
| 2-bis | ✅ sessione DB | Ricognizione dei lettori DB e dei presidi (§5) | 2 |
| 2-ter | ✅ Tid | D-3, D-4, D-5 come raccomandate, e il via al giro A (2026-11-21) | 2-bis |
| 3 | ✅ sessione DB e Tid | Giro A: via le tre colonne dal catalogo della lista (§3), nella forma del §5.2. Scritto e provato (§5.5); applicato su dbdev, pgTAP verdi (2026-11-21) | 2-ter |
| 4 | sessione DB e Tid | Giro B: via i sei campi da tabella, vista, madre e guard (§3); il regime su `config.regimi_fiscali` e `acquisti.ordini` sul termine (§5.3, D-3, D-4); il residuo del registro chiuso (D-5). ✅ Scritto e provato (§5.6), anticipato prima del BE (Tid); ✅ applicato su dbdev, pgTAP verdi (2026-11-21, §5.7); ✅ committato (`4ea18ba7d1`); ✅ doc auto-generata rigenerata (`eaed059e6`); ✅ `/verifica-db` (§7, 2026-11-21) | 3 |
| 5 | ✅ team BE/FE | Il §4 intero, col censimento (§6, 2026-11-21); ⏳ commit di Tid; ⏳ collaudo a video del drawer (Tid) | 4 |
| 5-bis | ✅ Tid | D-6 «a»: il regime spento non si assegna (2026-11-21, §7.2) | 4 |
| 5-ter | ✅ sessione DB | La D-6 nella forma della D-7 «2»: REQUIRE sulle due FK del regime e BLOCK su `config.regimi_fiscali` (§7.2). Applicato su dbdev e pushato (`20261121-10` … `-15`, `790fc0432`, PR #185); i due pgTAP del §7.3 corretti nello stesso giro | 5-bis |
| 5-quater | ✅ team BE/FE | La prova del rifiuto `E_ATTIVO_PADRE_NON_ATTIVO` sul campo `regime_fiscale_rf` dei due drawer: nessun codice nuovo, un test e2e (§7.2, «Dopo il push», 2026-11-21); ⏳ commit di Tid | 5-ter |
| 6 | team DB | Chiusura: archiviazione | 5, 5-ter, 5-quater |

## 1. Che cosa ha fatto il BE/FE (2026-11-21)

`anagrafiche.fornitori` porta sei campi che hanno la loro sede altrove, o nessuna:

| Campo | Sede |
| --- | --- |
| `giorni_pagamento`, `fine_mese` | il termine (`config.termini_pagamento`, via `termine_pagamento_id`) |
| `split_payment` | il soggetto (`anagrafiche.soggetti.split_payment`, `character(1)`) |
| `canale_fe`, `pec_email` | i dati societari del soggetto (`anagrafiche.dati_societari`) |
| `bollo_esente` | **nessuna**, e sul fornitore non serve (D-2) |

Sono usciti da: il form di `FornitoreDrawer.vue`; il dettaglio (`FornitoriRepository.get_fornitore`); la whitelist
della PATCH (`FORNITORE_UPDATE_ALLOWED`: un PATCH che li porta ora è un 400, test
`test_update_fornitore_campi_del_soggetto_sono_400`); i campi della creazione
(`FornitoriService._extract_fornitore_data`); lo schema OpenAPI delle due view; la lettura del fornitore del portale
(`PortaleRepository`, `pec_email`, senza lettori). Come sul cliente, che non li ha.

**Restano, e sono il motivo di questo brief:**

* la **lista** `anagrafiche.fornitori` mostra ancora tre colonne di `ui.lista_colonna` (codici `pec_email`,
  `canale_fe`, `split_payment`), lette da `vw_fornitori_dettaglio`, cioè da `f.*`. Mostrano il valore **del
  fornitore**, che nessuno può più modificare, e non quello del soggetto: il dato a video diverge in silenzio dal
  dato vero. Il BE le tiene nella SELECT di `list_fornitori` solo perché il catalogo le espone;
* le **colonne** della tabella, la vista, l'allowlist di `anagrafiche.fn_crea_fornitore` (`p_campi` accetta ancora le
  sei chiavi) e `trgfn_fornitori_guard_normalize` (normalizza `canale_fe`).

## 2. Decisioni di Tid (2026-11-21)

* **D-1 — le tre colonne della lista. ✅ Decisa: «a», si ritirano.** (a) si ritirano dal catalogo; (b) si rifanno dalla sede vera (split payment
  dal soggetto, canale e PEC da `dati_societari`), come colonne nuove. **Raccomandata (a)**: né `clienti` né
  `billing_account` portano questi campi, e la lista clienti non ha colonne equivalenti (verificato su
  `lista_colonna.csv` il 2026-11-21); se servono su tutte e due le liste, è uno sviluppo delle colonne di soggetto,
  simmetrico. Una colonna che legge il doppione è peggio di nessuna colonna.
* **D-2 — `bollo_esente`. ✅ Decisa: non serve sul fornitore, si ritira con gli altri cinque.** A differenza degli altri cinque non ha un'altra sede (sta solo su `emittenti_fiscali` e
  sulle fatture): il form l'ha tolto per simmetria col cliente, che non lo ha. Da confermare che sul fornitore non
  serve (il bollo della fattura passiva lo porta il documento del fornitore); se serve, torna nel form e non si
  ritira.

## 3. Richiesta al team DB

**Giro A — il catalogo (prima del BE).**

1. `ui.lista_colonna`, lista `anagrafiche.fornitori`: via le colonne di codice `pec_email`, `canale_fe`,
   `split_payment` (D-1 «a»), con le loro tracce nelle preferenze e nei preset della lista, se ne hanno.

**Giro B — i campi (dopo il passo 4, il BE).**

2. `anagrafiche.fornitori`: via `giorni_pagamento`, `fine_mese`, `split_payment`, `bollo_esente`, `canale_fe`,
   `pec_email`, coi loro CHECK (`char_length(canale_fe) = 7`) e la normalizzazione di `canale_fe` in
   `trgfn_fornitori_guard_normalize`.
3. `vw_fornitori_dettaglio`: via le stesse sei colonne.
4. `anagrafiche.fn_crea_fornitore`: via le sei chiavi dall'allowlist di `p_campi` (diventano `E_CAMPO_NON_AMMESSO`)
   e dal `COMMENT`.
5. Manuale `docs/it/dbzero/anagrafiche/manual/fornitori.md`: le righe dei campi e il consiglio «compila uno tra
   `canale_fe` e `pec_email`».

⚠️ **Superato il 2026-11-21:** i due giri vanno insieme e il BE passa per ultimo (Tid); vedi §4 e §5.6.

**Chi cambia per primo, e perché in due giri.** Il BE ha già smesso di scrivere e leggere i campi, tranne le tre
colonne della lista, che legge dalla vista (`v.split_payment`, `v.canale_fe`, `v.pec_email` in
`FornitoriRepository.list_fornitori`). ⛔ Se la vista le perdesse nello stesso giro del catalogo, la lista fornitori
uscirebbe 500 fino al commit del BE. Quindi: giro A (il catalogo non le chiede più) → il BE le toglie dalla SELECT →
giro B (vista e tabella).

## 4. Dopo l'apply, al team BE

✅ **Fatto il 2026-11-21 (sessione BE/FE), §6.**

⚠️ **Rivisto il 2026-11-21 (sessione DB):** i giri A e B vanno sul DB insieme, e il BE passa **dopo** tutti e due
(Tid). La richiesta è una sola, ed è questa. Dal momento dell'apply fino al passaggio del BE la lista e il dettaglio
dei fornitori leggono colonne che la vista non ha più.

1. `FornitoriRepository.list_fornitori`: via `v.split_payment`, `v.canale_fe`, `v.pec_email` dalla SELECT, col
   commento che le spiega; via le chiavi i18n `anagrafiche.fornitori.col_pec_email`, `col_canale_fe`,
   `col_split_payment` (le citava solo il catalogo).
2. **Il regime cambia nome**: `anagrafiche.fornitori.regime_fiscale` è ora `regime_fiscale_rf`, e
   `vw_fornitori_dettaglio` espone `regime_fiscale_rf` e `regime_fiscale_descrizione` (§5.6). Da adeguare:
   - la SELECT della lista e del dettaglio (`v.regime_fiscale` non esiste più);
   - la whitelist della PATCH e i campi della creazione: la chiave è `regime_fiscale_rf`.
     `fn_crea_fornitore` rifiuta `regime_fiscale` con `E_CAMPO_NON_AMMESSO`;
   - un codice fuori catalogo esce da `fk_fornitori_regimi_fiscali`: tradurlo in 400 sul campo, come per
     l'emittente (`fk_emittenti_fiscali_regimi_fiscali`);
   - FE: il campo di testo diventa un lookup su `config.regimi_fiscali` (valore `codice_interno`), come nel drawer
     dell'emittente.
3. La colonna `regime_fiscale` della lista fornitori mantiene il suo **codice** (e quindi la chiave i18n
   `col_regime_fiscale`); cambia il campo, che ora è `regime_fiscale_rf`.
4. **Censimento richiesto al BE/FE**: cercare tutti i lettori di `regime_fiscale` sul fornitore e delle sei colonne
   ritirate, compresi quelli fuori dai file nominati qui (serializer, OpenAPI, portale, export, test). L'elenco qui
   sopra è quello che si vede dal DB, e non è detto che sia completo.
5. `acquisti.ordini`: niente da fare, il BE/FE degli acquisti non esiste ancora. Quando nascerà, l'ordine porta
   `termine_pagamento_id`, come l'ordine di vendita.

## 5. Ricognizione DB (sessione DB, 2026-11-21)

La struttura è letta sullo scratch `zeroerp_ruoli` (catalogo, `pg_depend`, `prosrc`) e sulla doc auto-generata.

### 5.1 I lettori DB dei sei campi

| Lettore | Che cosa legge | Esito |
| --- | --- | --- |
| `anagrafiche.vw_fornitori_dettaglio` | i sei campi | giro B, §3 punto 3 |
| `anagrafiche.fn_crea_fornitore` | i sei campi in `c_ammesse` e nel `COMMENT` | giro B, §3 punto 4 |
| `anagrafiche.trgfn_fornitori_guard_normalize` | `canale_fe` e `pec_email`, regole 1-2 | giro B: si tolgono le regole 1-2, restano 3-4 sulla ritenuta; il `COMMENT` va riscritto |
| `chk_fornitori_canale_fe_len` | `canale_fe` | cade con la colonna |
| `storico.fornitori` | niente: tiene la riga in `snapshot jsonb` | ⚠️ **non va allineato**. Le foto già scritte conservano le chiavi, ed è corretto: sono la storia della riga |
| `config.messaggi_errore` | nessun codice dedicato a questi campi | — |

Nessun'altra funzione, vista o job legge le sei colonne.

**pgTAP da adeguare.** `ui/test-lista-fornitori-seed.sql`: il test 4 passa da 13 a 10 colonne attive, il test 6 da 2 a 1
colonna booleana `yesno` (resta `ritenuta_acconto`). `anagrafiche/test-fornitore-privato-indirizzi-v1.sql` nomina
`split_payment`, ma quello del soggetto: non si tocca.

### 5.2 La forma del giro A: le righe si tolgono, non si spengono

Le tre righe di `ui.lista_colonna` (lista 3, id 30 `pec_email`, 31 `canale_fe`, 32 `split_payment`) non si possono
lasciare spente con `attivo=f`. Al giro B la vista perde le colonne, e allora una riga spenta si rompe in due modi:

* il test 2 di `ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` controlla il `campo_sorgente` di **tutte** le
  colonne delle liste attive, comprese quelle spente: va rosso;
* il CSV diventa una **mina irriscrivibile** (linee-guida-sql §11.2): al prossimo risveglio del mirror,
  `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` rifiuta una riga che nomina una colonna che non esiste più.

Quindi al giro A le tre righe escono dal CSV e dal database con il `DELETE` forward-only di §11.2, passando per il
blocco per riga del seed di primo impianto (`trgfn_seed_primo_impianto`).

**Non è una revoca di QU3.** QU3 (Tid, 2026-11-20, `work-done/2026/brief-db-seed-primo-impianto-non-si-riscrive.md`,
«La cancellazione») dice che una riga nata dal seed non si cancella e si spegne. È la regola per le cancellazioni
dell'**installazione**: l'admin dall'interfaccia riceve `E_SEED_RIGA_NON_CANCELLABILE`. Lo stesso giro ha lasciato al
**migratore** la porta `zeroerp.allow_seed_primo_impianto_override`, «per la bonifica voluta e il `DELETE`
forward-only» (guida `automazione-db`, «La porta di manutenzione»). Il giro A usa quella porta. Spegnere qui vorrebbe dire
lasciare la mina del punto sopra. Sullo scratch nessun `lista_preset_colonna` e
nessun `lista_colonna_permesso` nomina le tre righe: è un fatto datato, non un motivo. Il giro guarda comunque le figlie
per struttura, e anche le preferenze per codice.

⚠️ **Coordinamento.** `brief-db-revisione-ui.md` sta scrivendo il suo giro 2 sui CSV di `ui`. Il giro A tocca
`lista_colonna.csv` per riga, con l'albero allineato subito prima, e non deve incrociarsi con quel giro.

### 5.3 Due punti della richiesta che questo brief non porta

La richiesta del BE arrivata in chat il 2026-11-21 aveva altri due punti, che qui non ci sono:

* **Il regime fiscale.** `fornitori.regime_fiscale` è un `varchar(8)` libero, senza FK. Va portato su
  `config.regimi_fiscali`. Il precedente è la D-9 del 2026-10-01
  (`work-done/2026/brief-db-esigibilita-iva-per-cassa-emittente.md`): `emittenti_fiscali.regime_fiscale_rf` ha la FK su
  `codice_interno` (RF01…), la chiave del tracciato FatturaPA, non sull'`id`. Ricaduta che la richiesta non nomina: la
  riga 34 della lista 3 ha `campo_sorgente = regime_fiscale`, e cambia insieme alla vista.
* **`acquisti.ordini`.** Ha ancora `giorni_pagamento` e `fine_mese` e non ha `termine_pagamento_id`. Il modello da copiare
  è `vendite.ordini`: FK `fk_ordini_termini_pagamento`, `ON UPDATE CASCADE ON DELETE SET NULL`; il trigger che pretende un
  termine attivo lo crea `ci_apply` (§11.5), e la snapshot del termine esiste solo in fattura. Nessun lettore DB delle due
  colonne. Il BE/FE acquisti non esiste ancora. Il tema sta anche in `analisi-simmetria-ordini-acquisto.md`.

### 5.4 Decisioni di Tid (2026-11-21: tutte e tre come raccomandate)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-3 | I due punti del §5.3 entrano in questo brief? | **Sì, al giro B**: toccano la stessa tabella e la stessa vista (il regime), oppure lo stesso tema, il termine al posto della coppia giorni + fine mese (`acquisti.ordini`). L'analisi della simmetria riceve una riga che rimanda qui |
| D-4 | Nome e chiave del regime del fornitore | `regime_fiscale_rf`, FK su `config.regimi_fiscali.codice_interno`, nullable (un fornitore privato non ha regime): la forma della D-9. La vista espone anche la descrizione, per la riga 34 e per il lookup del FE |
| D-5 | Il residuo «`anagrafiche.fornitori.split_payment`» del registro dei residui (e la sua riga in PROJECT_CONTEXT) | **Si chiude con il giro B**: il campo esce dalla tabella, e la domanda del residuo («forse è nella sede sbagliata») ha la risposta |

**Ricadute BE di D-3 e D-4** (dopo il giro B): la chiave `regime_fiscale_rf` in creazione e PATCH del fornitore,
al posto di `regime_fiscale`, che `fn_crea_fornitore` rifiuterà con `E_CAMPO_NON_AMMESSO`; la FK tradotta in 400 sul
campo; il FE dal campo di testo al lookup sui regimi; la colonna della lista, se legge la descrizione.

### 5.5 Il giro A, scritto (2026-11-21)

| File | Che cosa |
| --- | --- |
| `80_data/changelog/20261121-01-delete-ui-lista-fornitori-colonne-doppioni-soggetto` | Con la porta `zeroerp.allow_seed_primo_impianto_override` (`SET LOCAL`), nell'ordine: via le voci di `ui.lista_preset_colonna` sulle tre colonne (la FK non ha `CASCADE`); via le voci sui tre codici dall'`ordinamento_default` dei preset della lista, tenendo l'ordine delle altre; il `DELETE` forward-only delle tre righe, con i permessi di colonna che escono in cascata. preCondition: la lista esiste |
| `80_data/sql/ui/lista_colonna.csv` | Via le righe 30, 31, 32 (`git diff --numstat`: 0 aggiunte, 3 tolte, nessun ritorno carrello) |
| `db/pgtap/ui/test-lista-fornitori-seed.sql` | Test 4: da 13 a 10 colonne attive; test 6: da 2 a 1 booleana `yesno`; test 13 nuovo, le tre colonne non sono nel catalogo, nemmeno spente (plan 13) |

**La prova** (`scripts/prova_changeset.py --pgtap`, scratch `zeroerp_ruoli`, 2026-11-21): estratto eseguito per intero
e annullato; pgTAP senza l'estratto 10 ok e 3 rossi (i tre test che vogliono lo stato nuovo), con l'estratto 13 ok e 0
rossi; catalogo identico prima e dopo. Il `DELETE` delle righe nate dal seed passa dalla porta: senza, il trigger del
seed lo rifiuterebbe con `E_SEED_RIGA_NON_CANCELLABILE`. Guardrail forme, `runOnChange`, preCondition e letterali
verdi.

⚠️ **Non provati su un caso costruito:** la bonifica dell'`ordinamento_default` e quella delle voci di preset
dell'installazione. Il seed non ne ha nessuna sulle tre colonne, quindi sullo scratch le due istruzioni non toccano
niente: il verde non le prova. Le due istruzioni sono scritte per struttura (la FK senza `CASCADE`, il guard
dell'ordinamento che rifiuta un codice che non c'è più).

**Il mirror.** Togliere tre righe risveglia `20260806-15-riancora-mirror-ui-lista-colonna` (`runOnChange`), che rilegge
tutto il file. Non scrive le tre righe tolte e non le cancella: quello lo fa il `-01`, che viene dopo nell'ordine dei
nomi. Le altre righe del file non cambiano. L'ultima riscrittura completa è passata su dbdev il 2026-11-21, col residuo di
BE22 della revisione `ui`.

⚠️ **Lavoro parallelo nello stesso albero:** la sessione del giro 2 di `brief-db-revisione-ui.md` ha file `ui` non
committati (`20261120-21` … `-33`, `lista_preset.csv`). Il giro A non tocca quei file, e il commit li deve tenere
separati.

### 5.6 Il giro B, scritto (2026-11-21)

Anticipato prima del BE per decisione di Tid (2026-11-21, «il BE interverrà per ultimo»). L'ordine dei file è quello
dell'apply su dev: fase, poi numero.

| File | Che cosa |
| --- | --- |
| `00_schema/anagrafiche/20261121-02-update-fornitori-normalizza-regime-fiscale` | `regime_fiscale`: spazi tolti, maiuscolo, il vuoto a `NULL`. In un changeSet suo perché l'`UPDATE` lascia eventi trigger in sospeso, e l'`ALTER` nella stessa transazione morirebbe |
| `00_schema/anagrafiche/20261121-03-alter-fornitori-ritira-doppioni-regime-fk` | Via la vista (DROP COLUMN non passa finché esiste), via le sei colonne (il CHECK di `canale_fe` cade con la sua), `regime_fiscale` → `regime_fiscale_rf`, FK `fk_fornitori_regimi_fiscali` su `config.regimi_fiscali(codice_interno)` `RESTRICT`, COMMENT della colonna e di `termine_pagamento_id` |
| `00_schema/acquisti/20261121-04-alter-acquisti-ordini-termine-pagamento` | Nasce `termine_pagamento_id` con FK `fk_ordini_ao_termini_pagamento` (`ON UPDATE CASCADE ON DELETE SET NULL`, come `vendite.ordini`), escono `giorni_pagamento` e `fine_mese` |
| `20_code/anagrafiche/20261121-05-recreate-vw-fornitori-dettaglio-senza-doppioni` | La vista ricreata, presa dal catalogo, senza le sei colonne; `regime_fiscale_rf` e `regime_fiscale_descrizione` (join sul catalogo dei regimi) |
| `20_code/anagrafiche/20261121-06-update-fn-crea-fornitore-senza-doppioni` | `c_ammesse` senza le sei chiavi, con `regime_fiscale_rf` al posto di `regime_fiscale`; COMMENT riscritto. Corpo dal catalogo; la firma e il `RETURNS TABLE` con i `%TYPE` di `20261018-30`, che il catalogo scioglie (il guardrail delle forme lo ha preso alla prima stesura) |
| `20_code/anagrafiche/20261121-07-update-trgfn-fornitori-guard-normalize-senza-canale-fe` | Via la normalizzazione di `canale_fe` e `pec_email`: con le colonne fuori sarebbe un errore a runtime alla prima scrittura. Restano le regole sulla ritenuta, invariate |
| `80_data/sql/ui/lista_colonna.csv` | La riga 34 (`regime_fiscale`): `campo_sorgente` = `regime_fiscale_rf`. Codice ed etichetta restano. `campo_sorgente` è una colonna del software per il seed di primo impianto: il mirror la riscrive anche su una riga personalizzata |
| pgTAP `anagrafiche/test-fn-crea-fornitore-v1.sql` | Esteso, plan da 16 a 21: le sette chiavi ritirate (sei doppioni più `regime_fiscale`) rifiutate con `E_CAMPO_NON_AMMESSO`; il regime ammesso e scritto; la vista che lo espone con la descrizione; un regime fuori catalogo rifiutato da `fk_fornitori_regimi_fiscali`; tabella e vista senza le colonne ritirate |
| pgTAP `acquisti/test-ordini-termine-pagamento-v1.sql` | Nuovo, primo della cartella: niente coppia giorni + fine mese; la FK sul termine, con azioni e tipo confrontati con quelli di `vendite.ordini`, non scritti a mano |
| pgTAP `ui/test-lista-fornitori-seed.sql` | Test 14: la colonna `regime_fiscale` legge `regime_fiscale_rf` |
| doc `manual/` | `fornitori` (corretto anche `stato_operativo`, che non esiste: è `stato_fornitore_id`), `vw_fornitori_dettaglio`, `fn_crea_fornitore`, `trgfn_fornitori_guard_normalize` |
| D-5 | Residuo «`anagrafiche.fornitori.split_payment`» tolto dal registro e dalla riga di PROJECT_CONTEXT |
| D-3 | Riga di rimando in `analisi-simmetria-ordini-acquisto.md` |

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, 2026-11-21). I sette changeSet nell'ordine
dell'apply, con in mezzo un file di sola prova, fuori dal repo, che fa sulla riga 34 quello che farà il mirror del CSV
(la prova non simula i mirror). Esito, prima e dopo l'estratto:

| pgTAP | Senza | Con |
| --- | --- | --- |
| `anagrafiche/test-fn-crea-fornitore-v1` | 16 ok, si ferma al 17 | 21/21 |
| `ui/test-lista-fornitori-seed` | 10 ok, 4 rossi (gli attesi nuovi) | 14/14 |
| `acquisti/test-ordini-termine-pagamento-v1` | 0 ok, 4 rossi | 4/4 |
| `ui/test-lista-colonna-campo-sorgente-in-vista-v1` | 6/6 | 6/6 |
| `anagrafiche/test-fornitore-privato-indirizzi-v1` | 24/24 | 24/24 |
| `script/test-search-regola-unica-visibile-v1` | 17/17 | 17/17 |
| `anagrafiche/test-indirizzi-obbligatori-mancanti-v1` | 11/11 | 11/11 |
| `anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1` | 10/10 | 10/10 |
| `anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1` | 27/27 | 27/27 |

Catalogo identico prima e dopo ogni prova. I guardrail delle forme, `runOnChange`, preCondition/seed, letterali,
DDL su trigger di `ci_apply` e GRANT ai ruoli batch sono verdi sui sette file.

⚠️ **Da sapere prima dell'apply:**

* **Un regime fuori catalogo su dbdev fa fallire il `-03`** al suo posto. Un cancello non c'è, perché una
  preCondition di `00_schema` non può leggere il contenuto di `80_data` (§11.4). Sullo scratch non c'è nessun
  fornitore. La query da lanciare prima su dbdev:
  `SELECT id, regime_fiscale FROM anagrafiche.fornitori WHERE regime_fiscale IS NOT NULL AND NULLIF(upper(btrim(regime_fiscale)), '') NOT IN (SELECT codice_interno FROM config.regimi_fiscali);`.
  Se esce qualcosa, si corregge a mano.
* **Il trigger «termine attivo» su `acquisti.ordini` e la coppia ATTIVO sul regime** nascono da `ci_apply`. La prova
  non li ha visti, e nessun pgTAP di questo giro li cita.
  ⚠️ **Smentito per il regime il 2026-11-21 (§7.1):** il motore ATTIVO salta la FK, perché `regime_fiscale_rf` non
  finisce in `_id`. Il «termine attivo» su `acquisti.ordini` invece c'è.
* **I valori delle sei colonne si perdono.** Le loro sedi vere (soggetto, dati societari, termine) esistono già, e
  nessuno le scriveva più. Lo stesso vale per i giorni e il fine mese degli ordini di acquisto: non dicono quale
  termine del catalogo sia.
* **La vista resta senza `security_invoker`**, come prima. Il rischio è già descritto nella sua pagina `manual/`,
  e questo giro non lo cambia.
* **Doc auto-generata**: va rigenerata dopo l'apply. Toccano: `fornitori`, `vw_fornitori_dettaglio`,
  `fn_crea_fornitore`, `trgfn_fornitori_guard_normalize`, `acquisti.ordini`.

### 5.7 L'apply (2026-11-21)

Tid ha applicato i giri A e B su dbdev, nell'ordine di fase (`00_schema` `-02` … `-04`, `20_code` `-05` … `-07`,
`80_data`: il mirror di `lista_colonna`, poi il `-01`), con i pgTAP verdi. La query di controllo sui regimi fuori
catalogo del §5.6 non ha fermato il `-03`.

Restano aperti:

* il `/verifica-db` del lavoro, in una sessione nuova: l'apply è venuto prima della verifica;
* la doc auto-generata, da rigenerare: `anagrafiche.fornitori`, `vw_fornitori_dettaglio`, `fn_crea_fornitore`,
  `trgfn_fornitori_guard_normalize`, `acquisti.ordini`. Finché non c'è, il contratto degli oggetti toccati si legge dal
  catalogo, non dal markdown;
* ✅ il commit: `4ea18ba7d1` (2026-11-21), coi soli file di questo cantiere. Da PROJECT_CONTEXT è entrata la sola
  riga del residuo (D-5); le altre modifiche presenti nell'albero sono di altre sessioni e restano fuori;
* ✅ il §4, del team BE/FE: fatto il 2026-11-21 (§6).

## 6. Il passaggio BE/FE (sessione BE/FE, 2026-11-21)

Fatto il §4 per intero. Lista e dettaglio provati sul DB vero; PATCH e creazione provate con chiamate reali al service, in
transazione annullata: RF99 → 400 sul campo `regime_fiscale_rf`, RF01 e RF19 scritti, il vuoto della PATCH a `NULL`.

| Punto del §4 | Che cosa |
| --- | --- |
| 1 | `FornitoriRepository.list_fornitori`: via `v.split_payment`, `v.canale_fe`, `v.pec_email` e il commento che le teneva; via le chiavi i18n `anagrafiche.fornitori.col_pec_email`, `col_canale_fe`, `col_split_payment` (it, en) |
| 2 | `regime_fiscale_rf` nella SELECT della lista e del dettaglio; il dettaglio porta anche `regime_fiscale_descrizione` (join su `config.regimi_fiscali`), per la voce della combo quando il regime è stato disattivato dopo la scelta; la chiave nella whitelist della PATCH (`FORNITORE_UPDATE_ALLOWED`), nei nullable, nei campi della creazione e nello schema OpenAPI delle due view. FE: `FornitoreDrawer.vue` passa dal campo di testo a `LookupSelect` su `config.regimi_fiscali` (`codice_interno`, `show-clear`, campo acceso dal 400), come nel drawer dell'emittente; via la chiave `placeholder_regime` |
| 2, la FK | `fk_fornitori_regimi_fiscali` → 400 `E_ANAG_VALIDAZIONE` sul campo, in creazione e in PATCH. **Regola del 2 (ok Tid, 2026-11-21):** la traduzione era una copia privata del service dell'emittente (`_regime_nel_catalogo`); ora è il BB `regime_nel_catalogo(fk)` in `anagrafiche/services/_validators.py`, usato dai due service. La copia è ritirata nello stesso giro, la voce è nel catalogo BB backend e l'indice è rigenerato. Resta fuori, ed è voluto, la regola sul vuoto: sull'emittente il regime è NOT NULL, sul fornitore è nullable |
| 3 | La colonna `regime_fiscale` della lista mantiene codice e chiave i18n; legge `regime_fiscale_rf` dalla SELECT |
| 4 | Censimento, sotto |
| 5 | `acquisti.ordini`: niente, come scritto |

**Il censimento (punto 4).** Lettori di `regime_fiscale` sul fornitore e delle sei colonne ritirate, cercati in tutto
`backend/` e `frontend/src`. Esito:

* da adeguare, e adeguati: repository, service e view dei fornitori, `FornitoreDrawer.vue`, le chiavi i18n, i test del
  service (`test_fornitori_service`), la doc API `docs/it/backend/anagrafiche/manual/api_fornitori.md`. La doc portava
  ancora i sei campi anche nel contratto di creazione e PATCH, rimasta indietro già dal primo passaggio (§1);
* non ne dipendono: `soggetti_repository`, `soggetti_service`, `views_soggetti` e `lookup_repository` leggono
  `split_payment` del **soggetto**, che è la sede vera; `clienti_repository` cita i fornitori solo in un commento; il
  portale non legge più `pec_email` dal §1; export (`test_fornitori_export_api`) e store/view FE della lista non nominano
  le colonne, perché le prendono dal catalogo `ui.lista_colonna`.

**Un difetto trovato lavorando, chiuso nello stesso giro.** La creazione del fornitore non controllava le chiavi del
payload, unica fra le creazioni dell'anagrafica (il cliente ha `_CREATE_KEYS_CLIENTE`, l'emittente
`_CREA_EMITTENTE_KEYS`), e `extract_optional_fields` scarta in silenzio quelle che non conosce. Col regime rinominato,
un payload con `regime_fiscale` creava un fornitore **senza regime** e rispondeva 200: provato con una chiamata reale
prima della correzione. Ora `_CREA_FORNITORE_KEYS` lo rende un 400 che nomina la chiave, e lo stesso vale per i sei
campi ritirati. Le chiavi sono quelle che il drawer manda, e un test lo tiene fermo.

**Test.** `apps.anagrafiche` 649 verdi, `apps.amm_software` compreso 859 (i test su DB reale sono spenti di default).
Con `ZEROERP_TEST_DB_E2E=1` sono verdi anche `test_regime_fiscale_conferma_db` (la FK dell'emittente, dopo l'estrazione),
`test_clienti_fornitori_scrittura_db`, `test_creazioni_dalle_madri_db`, `test_scritture_bb_db`, `test_ricerca_liste_db`:
36 su 36. I test nuovi: il regime che arriva alla madre col suo nome; il fuori catalogo in creazione e in PATCH; un'altra
FK rilanciata; le chiavi ignote della creazione a 400; il payload del drawer ammesso; `RegimeNelCatalogoTest` per il BB.
Verdi anche ruff, la baseline di mypy, eslint, oxlint e il guard i18n. Gunicorn ricaricato (HUP).

⚠️ **Non provati:** il drawer a video (combo dei regimi, voce di un regime disattivato, campo acceso dal 400). Questo è
il collaudo di Tid del passo 5.

**La revisione `/verifica` del 2026-11-21/22 (sessione BE/FE).** Corretti nello stesso giro:

* lo smoke notturno `backend/scripts/tests/smoke-test-fornitori.sh` mandava ancora `pec_email` e `regime_fiscale`
  (creazione e PATCH), che col contratto nuovo sono 400: ora manda `regime_fiscale_rf` e `note`;
* il nome `fk_fornitori_regimi_fiscali`, che il service nomina per testo, era provato solo coi mock: ora lo provano sul
  DB vero i casi 6 e 7 di `test_regime_fiscale_spento_db` (rosso provato con un nome sbagliato);
* il 409 `E_ATTIVO_PADRE_NON_ATTIVO` del regime spento (D-6) entra nelle tabelle d'errore di `api_fornitori.md` e
  `api_emittenti_fiscali.md`;
* **regola del 2 (ok Tid, 2026-11-22):** la voce del regime corrente della combo era ricopiata identica nei drawer
  dell'emittente e del fornitore, e tutte e due mettevano il `codice_interno` al posto del `codice` a video. Ora è il BB
  FE `voceRegimeFiscale` (`src/core/utils/`, catalogo BB frontend, indice rigenerato), e i due dettagli BE portano
  `regime_fiscale_codice` (`rf.codice`). Prova sul DB vero: il caso 8 di `test_regime_fiscale_spento_db`, su un regime
  costruito con `codice` diverso da `codice_interno` (rosso provato).

## 7. La verifica DB dei giri A e B (2026-11-21)

Fatta da una sessione che non ha scritto i giri A e B. È la sessione BE/FE del §6, quindi non ha corretto file `db/`:
le correzioni stanno al §7.3 come richiesta.

**Pulito:**

* nessun numero di changeSet doppio, nessun changelog pushato modificato;
* `-06` rispetto a `20261018-30`: cambiano solo l'elenco delle chiavi e il COMMENT;
* `-07` rispetto a `20260808-08`: cambia solo la rimozione delle due normalizzazioni; il trigger non ha `UPDATE OF`;
* `-05`: le colonne giuste, il GRANT a `zeroerp_app` c'è;
* nessuna funzione né vista del catalogo vivo nomina le colonne ritirate, `fn_provisiona_dati_di_sviluppo` compresa;
  nessun CSV di seed le scrive;
* doc auto-generata rigenerata (`eaed059e6`); il trigger «termine attivo» su `acquisti.ordini` c'è.

### 7.1 La coppia ATTIVO sul regime non c'è

Il `-03` (commento in testata) e il §5.6 dicevano che a `ci_apply` nasce la coppia ATTIVO fra fornitore e regime.
`ci_apply` è girato su dbdev il 2026-11-21 alle 19:46, dopo l'apply, e su `anagrafiche.fornitori` non c'è nessun
trigger sul regime. `dbops.fn_run_automations_attivo` lanciato in prova a vuoto, in transazione annullata, dice
perché: `ATTIVO_SKIP_FK_NO_ID`, «FK column has no _id suffix», per `fornitori.regime_fiscale_rf` **e** per
`emittenti_fiscali.regime_fiscale_rf`. Il motore lega solo le FK la cui colonna finisce in `_id`. Il `-03` è pushato e
non si corregge: la correzione è questa sezione.

### 7.2 D-6 — un regime spento si può scegliere? ✅ Decisa: «a» (Tid, 2026-11-21)

Oggi il database **accetta** che a un fornitore, o a un emittente, si assegni un regime spento. La combo del drawer
propone solo i regimi attivi, ma la regola non sta a DB. Lo spegnimento di un regime già in uso resta libero, ed è
voluto: un regime spento dopo la scelta resta di chi l'aveva (Tid, 2026-10-01, sull'emittente).

| Strada | Che cosa |
| --- | --- |
| a | Un guard a DB che rifiuta la **scrittura** di un regime spento, sull'emittente e sul fornitore. ⚠️ La forma «scritto a mano» è superata dalla D-7, sotto |
| b | Si lascia così, e si scrive nella pagina `manual/` del regime che la regola la fa la combo |

#### La risposta della sessione DB (in chat, 2026-11-21)

* La regola dichiarata dalla pagina `docs/it/dbzero/config/manual/regimi_fiscali.md` («un regime spento non si assegna,
  e uno usato non si spegne: la coppia ATTIVO nasce a `ci_apply`») non la applica il database, né su dbdev né su uno
  scratch costruito da zero. Il motivo è il filtro `ATTIVO_SKIP_FK_NO_ID` del runner, presente da gennaio. Le
  funzioni generiche seguono già una FK su `codice_interno`: le ferma solo quel filtro.
* Il filtro esclude oggi circa 90 FK monocolonna (fatto datato, 2026-11-21): toglierlo è un cambio su tutte quelle
  tabelle, non una correzione.
* Contro la «a» scritta a mano: sarebbe una seconda copia della regola ATTIVO, contro la regola del 2.
* La proposta: un registro delle FK da **includere** nel runner, simmetrico a `dbops.automazione_attivo_eccezioni`,
  con le due righe del regime e il loro motivo.

⚠️ **La proposta generava anche il BLOCK sul padre** (un regime in uso non si spegne), e il BLOCK **revoca** una
decisione presa: *«un emittente può TENERE un regime che il catalogo disattiva (la FK non guarda `attivo`, e va bene
così)»* (Tid, 2026-10-01, `work-done/2026/brief-db-esigibilita-iva-per-cassa-emittente.md` §R-1). È la pagina
`regimi_fiscali.md`, scritta il 2026-10-02, a dire il contrario della decisione: sbaglia la pagina.

#### D-7 — un regime in uso si spegne? ✅ Decisa: «2» (Tid, 2026-11-21, rivista)

> ⚠️ **Prima decisa «1», poi rivista da Tid in «2»** nella sessione DB, lo stesso giorno. Valgono la tabella e il
> paragrafo «D-7 rivista» qui sotto; la richiesta in forma «1» resta come storia, marcata superata.


| Strada | Che cosa |
| --- | --- |
| 1 ⚠️ superata | Sì, si spegne anche se in uso (la decisione del 2026-10-01 resta): chi lo ha lo tiene, un nuovo non lo sceglie. Serve la sola parte REQUIRE |
| **2** ✅ | **No, finché un emittente o un fornitore acceso lo usa**: REQUIRE e BLOCK, la «b» piena della sessione DB, con la revoca della decisione del 2026-10-01 |

**D-7 rivista — la regola applicata (sessione DB, `20261121-10` … `-15`, applicati su dbdev, push in arrivo).**

* Un regime spento **non si assegna**, né a un emittente né a un fornitore.
* Un regime usato da un emittente o da un fornitore **acceso** **non si spegne**. È revocata la decisione del
  2026-10-01 (`work-done/2026/brief-db-esigibilita-iva-per-cassa-emittente.md` §R-1) per cui un emittente poteva
  tenere un regime spento: per i ruoli accesi quella proprietà non vale più.

| Caso | Codice | Classe | Contesto |
| --- | --- | --- | --- |
| Regime spento assegnato a un emittente o fornitore acceso: in creazione, in PATCH o alla riaccensione | `E_ATTIVO_PADRE_NON_ATTIVO` | `CONFLITTO_STATO` | `campo = "regime_fiscale_rf"`, `ref_val` = il codice RF |
| Riaccendere un emittente o fornitore che tiene un regime spento | lo stesso | lo stesso | lo stesso; il rimedio è scegliere un regime acceso |
| Spegnere un regime in uso | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` | `CONFLITTO_STATO` | — il catalogo dei regimi non è nel pannello: oggi l'operatore non lo incontra |

Garanzie ritirate: nessuna; il giro ne aggiunge due.

**Dopo il push, al team BE/FE.** ✅ Fatto il 2026-11-21 (sessione BE/FE): esito sotto, dopo i tre punti.

1. La tendina del regime resta filtrata sui soli regimi accesi: il DB fa da rete, non sostituisce il filtro.
2. Il campo: se il DB lo manda nel canale strutturato `COLUMN`, il BE lo porta già nel `field` della risposta
   (`backend/apps/core/services/db_error_fields.py`) e i due drawer accendono il regime senza codice nuovo. Si prova
   con una chiamata vera, in transazione annullata: regime spento su fornitore ed emittente, in creazione, in PATCH e
   alla riaccensione. Codice nuovo solo se il campo non si accende.
3. Il censimento dei lettori di `regime_fiscale_rf` che contano su «si può tenere un regime spento» (sessione BE/FE,
   2026-11-21): `backend/`, `frontend/` e i manuali BE non ne hanno. Il `:voce-corrente` del drawer del fornitore
   resta: un fornitore **spento** può ancora tenere un regime spento, e il drawer lo deve mostrare.

**Esito (sessione BE/FE, 2026-11-21, dopo `/arrivi-db` di `790fc0432`).**

1. **Nessun codice BE/FE nuovo.** Il DB manda il campo nel canale strutturato: il traduttore generale
   (`ErrorTranslator._from_database_error`, via middleware) lo porta nei `fields` dell'envelope, e i due drawer
   accendono già il regime da `campiErrati` (`frontend/src/anagrafiche/components/FornitoreDrawer.vue`,
   `frontend/src/amministrazione/components/EmittenteFiscaleDrawer.vue`). `regime_nel_catalogo` rilancia l'errore
   (non è la FK) senza tradurlo in «fuori catalogo»; lo stesso fa `create_with_constraint_mapping` in creazione.
   I due codici erano già nella policy generata e nel ripiego.

   | Caso, dal service vero | Codice | HTTP | `fields` |
   | --- | --- | --- | --- |
   | PATCH del fornitore con un regime spento | `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` |
   | Creazione del fornitore con un regime spento | `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` |
   | Riaccensione di un fornitore che tiene un regime spento | `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` |
   | PATCH dell'emittente con un regime spento | `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` |
   | Spegnimento di un regime in uso (SQL) | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` | 409 | `attivo` |

2. **Il presidio:** `backend/apps/anagrafiche/tests/db/test_regime_fiscale_spento_db.py` (e2e, cinque test: i primi
   quattro casi sopra più il controcampione «un regime acceso si assegna»). I due regimi li costruisce il test. ⚠️ I
   require sono `DEFERRABLE INITIALLY DEFERRED`: nella richiesta vera (autocommit) giudicano alla fine
   dell'istruzione; nel test, che non fa COMMIT, si rendono `IMMEDIATE` i **soli** due require del regime, cercati per
   funzione e argomenti, e il test è rosso se non sono due.
3. **Garanzie ritirate:** nessuna. Da sapere: dal giro, il ritiro del motore toglie anche i trigger ATTIVO di una FK
   senza `_id` fuori dal registro. Censiti su dbdev: gli unici trigger ATTIVO su FK senza `_id` sono i quattro nuovi del
   regime, tutti nel registro; oggi non se ne perde nessuno.
4. **Alla sessione DB, una nota (nessuna urgenza).** Il motivo di `db/pgtap/dbops/test-automazione-attivo-inclusioni-v1.sql`
   (`pgtap-runner-motivo`) dice che spegnere un regime «lo può solo il migratore». Su dbdev il ruolo applicativo
   `zeroerp_app` ha INSERT e UPDATE su `config.regimi_fiscali`: il test e2e sopra costruisce e spegne regimi con quel
   ruolo. O il privilegio è di troppo (e va tolto, allora il test e2e cambia strada), o il motivo va riscritto. Il
   catalogo dei regimi non è nel pannello, quindi a video l'operatore non ci arriva.

⚠️ **Superata dalla D-7 «2» (sopra): resta come storia della prima forma.**


**Richiesta alla sessione DB (sostituisce quella della D-6 sotto).**

1. Il registro delle FK da includere nel runner ATTIVO, come ha proposto la sessione DB, con in più **quale parte** si
   genera per ogni riga (REQUIRE, BLOCK, o tutte e due). Le due righe: `anagrafiche.emittenti_fiscali.regime_fiscale_rf`
   e `anagrafiche.fornitori.regime_fiscale_rf`, **solo REQUIRE**, col motivo (D-6 e D-7). Nessuna logica di controllo
   nuova: il trigger è quello generico.
2. Sul padre `config.regimi_fiscali` **nessun BLOCK**: un regime in uso si spegne. ⚠️ Rovesciato dalla D-7 «2»: il BLOCK c'è.
3. La pagina `docs/it/dbzero/config/manual/regimi_fiscali.md` corretta: un regime spento non si assegna, e uno in uso
   si spegne, e resta di chi l'aveva (D-7).
4. Da sapere, detto dalla sessione DB: il REQUIRE generico scatta anche quando si **riaccende** un emittente o un
   fornitore. Riaccendere un fornitore che ha un regime spento diventa un rifiuto, finché non gli si dà un regime
   acceso. Se questo non va, lo si dice prima di scrivere il registro.
5. Un pgTAP che costruisce i due casi: il regime spento assegnato è rifiutato, e il regime in uso si spegne.

**Ricaduta BE/FE, da scrivere quando il registro c'è:** il codice d'errore del REQUIRE (`E_ATTIVO_PADRE_NON_ATTIVO`)
sul campo `regime_fiscale_rf` dei due drawer. Il drawer propone già i soli regimi attivi, quindi a video il rifiuto si
vede solo riaccendendo un fornitore o un emittente col regime spento.

### 7.3 Richiesta alla sessione DB: due pgTAP che possono passare a vuoto

✅ **Fatto** nel giro `790fc0432` (PR #185): il `COALESCE` sull'atteso nei test 18 e 19 di
`test-fn-crea-fornitore-v1.sql` e nei test 3 e 4 di `test-ordini-termine-pagamento-v1.sql`, `plan` invariati.

* `db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql`, test 18 e 19: l'atteso è il primo regime attivo del catalogo
  (`t_rf`). Con il catalogo vuoto `t_rf` non ha righe, `t_f3` resta vuota e il test confronta `NULL` con `NULL`: passa.
  Correzione: l'atteso con `COALESCE((SELECT rf FROM t_rf), '<catalogo regimi vuoto>')`, e lo stesso nel 19. Il
  `plan` resta 21.
* `db/pgtap/acquisti/test-ordini-termine-pagamento-v1.sql`, test 3 e 4: l'atteso viene da `vendite.ordini`. Se quella
  FK o quella colonna mancassero, `NULL` contro `NULL`: passa. Correzione: il `COALESCE` sull'atteso. Il `plan` resta 4.

⚠️ **Superata dalla D-7 (§7.2, sotto): la forma è il registro di inclusione del motore, non un guard a mano.**

**Richiesta alla sessione DB per la D-6 «a».** Un guard su `anagrafiche.fornitori` e uno su
`anagrafiche.emittenti_fiscali` che rifiutano la scrittura di un `regime_fiscale_rf` con `attivo = false` in
`config.regimi_fiscali`, all'INSERT e all'UPDATE che **cambia** il regime: un regime spento dopo la scelta resta di
chi l'aveva, e la riga si salva lo stesso. Il predicato è uno solo per le due tabelle (regola del 2), e si cerca prima
se `dbops.trgfn_child_requires_active_parent` lo può già fare passando `codice_interno` come colonna del padre. Il
codice d'errore va fatto col campo `regime_fiscale_rf`, perché il BE lo accenda. Ricaduta BE, da scrivere quando il
guard c'è: il codice nuovo nella policy generata e nel ripiego; il drawer non cambia, propone già i soli attivi.

