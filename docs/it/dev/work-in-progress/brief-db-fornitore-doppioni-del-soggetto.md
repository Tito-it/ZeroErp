# Brief DB — i doppioni del soggetto sul fornitore

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), revisione `/verifica` del 2026-11-21. **A chi:** team DB
> (`dev/db-tid`); Tid per le decisioni aperte.

## ⏭️ Chi riparte — aggiornato al 2026-11-21

**Riparte: il team BE/FE** col §4, dopo `/arrivi-db`: da adesso lista e dettaglio dei fornitori leggono colonne che
la vista non ha più, finché il BE non passa (accettato da Tid). I giri A e B (`20261121-01` … `-07`, §5.5 e §5.6) sono
applicati su dbdev con i pgTAP verdi (Tid, 2026-11-21, §5.7). Alla sessione DB restano il `/verifica-db` e,
con Tid, la doc auto-generata rigenerata e il commit. D-3, D-4 e D-5 sono decise (Tid, 2026-11-21, §5.4). Il lato BE/FE
del primo passaggio è fatto (§1) e committato (`56c7fee9f6`, PR #182).

| # | Chi | Che cosa | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ team BE/FE | Form, dettaglio, PATCH e creazione del fornitore senza i sei campi (2026-11-21) | — |
| 2 | ✅ Tid | D-1 «a», D-2 «non serve» (2026-11-21) | — |
| 2-bis | ✅ sessione DB | Ricognizione dei lettori DB e dei presidi (§5) | 2 |
| 2-ter | ✅ Tid | D-3, D-4, D-5 come raccomandate, e il via al giro A (2026-11-21) | 2-bis |
| 3 | ✅ sessione DB e Tid | Giro A: via le tre colonne dal catalogo della lista (§3), nella forma del §5.2. Scritto e provato (§5.5); applicato su dbdev, pgTAP verdi (2026-11-21) | 2-ter |
| 4 | sessione DB e Tid | Giro B: via i sei campi da tabella, vista, madre e guard (§3); il regime su `config.regimi_fiscali` e `acquisti.ordini` sul termine (§5.3, D-3, D-4); il residuo del registro chiuso (D-5). ✅ Scritto e provato (§5.6), anticipato prima del BE (Tid); ✅ applicato su dbdev, pgTAP verdi (2026-11-21, §5.7); ⏳ `/verifica-db` in una sessione nuova; ⏳ doc auto-generata rigenerata e commit (Tid) | 3 |
| 5 | **team BE/FE** ⏭️ | Il §4 intero, dopo `/arrivi-db` | 4 |
| 6 | team DB | Chiusura: archiviazione | 5 |

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
* il commit, che tiene fuori i file della sessione `ui` presenti nello stesso albero (§5.6);
* il §4, del team BE/FE: fino al suo passaggio lista e dettaglio dei fornitori sono in errore.
