# Brief DB — i doppioni del soggetto sul fornitore

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), revisione `/verifica` del 2026-11-21. **A chi:** team DB
> (`dev/db-tid`); Tid per le decisioni aperte.

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Brief chiuso e archiviato (sessione DB, 2026-11-22, §7.6). Non riparte nessuno**: l'ultimo passo, la riga 1356
di `messaggi_errore.csv` (5-novies), è applicato su dbdev (Tid, 2026-11-22) e committato con l'archiviazione. Il giro D-8/D-9 è committato (`e00a3c7279`, PR #188), il test e2e e il ripiego del BE pure
(`e9d5cde2a8`, PR #189); la doc auto-generata del giro è rigenerata (§7.6). Il lavoro BE/FE dei giri precedenti è
committato (`ae2336fcfd`, PR #187); il collaudo a video del drawer è fatto (Tid, 2026-11-22). La D-6 nella forma della D-7 «2» è applicata e pushata (`20261121-10` … `-15`,
`790fc0432`, PR #185), e la sessione BE/FE l'ha provata sui due drawer. Il `/verifica-db` dei giri
A e B è fatto (§7) e la doc auto-generata è rigenerata (`eaed059e6`).
Lista e dettaglio dei fornitori tornano a funzionare sul DB vero (§6). I giri A e B (`20261121-01` … `-07`, §5.5 e §5.6)
sono applicati su dbdev con i pgTAP verdi (§5.7) e committati in `4ea18ba7d1`. D-1 … D-5 decise. Il primo passaggio
BE/FE è committato (`56c7fee9f6`, PR #182). D-6 «a» e D-7 «2» decise (Tid, 2026-11-21, §7.2: la «1» è stata rivista da Tid nella sessione DB). D-8 «a» e D-9 «a» decise (Tid, 2026-11-22, §7.4); nessuna decisione aperta.

| # | Chi | Che cosa | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ team BE/FE | Form, dettaglio, PATCH e creazione del fornitore senza i sei campi (2026-11-21) | — |
| 2 | ✅ Tid | D-1 «a», D-2 «non serve» (2026-11-21) | — |
| 2-bis | ✅ sessione DB | Ricognizione dei lettori DB e dei presidi (§5) | 2 |
| 2-ter | ✅ Tid | D-3, D-4, D-5 come raccomandate, e il via al giro A (2026-11-21) | 2-bis |
| 3 | ✅ sessione DB e Tid | Giro A: via le tre colonne dal catalogo della lista (§3), nella forma del §5.2. Scritto e provato (§5.5); applicato su dbdev, pgTAP verdi (2026-11-21) | 2-ter |
| 4 | sessione DB e Tid | Giro B: via i sei campi da tabella, vista, madre e guard (§3); il regime su `config.regimi_fiscali` e `acquisti.ordini` sul termine (§5.3, D-3, D-4); il residuo del registro chiuso (D-5). ✅ Scritto e provato (§5.6), anticipato prima del BE (Tid); ✅ applicato su dbdev, pgTAP verdi (2026-11-21, §5.7); ✅ committato (`4ea18ba7d1`); ✅ doc auto-generata rigenerata (`eaed059e6`); ✅ `/verifica-db` (§7, 2026-11-21) | 3 |
| 5 | ✅ team BE/FE | Il §4 intero, col censimento (§6, 2026-11-21); ✅ commit di Tid (`ae2336fcfd`, PR #187); ✅ collaudo a video del drawer (Tid, 2026-11-22) | 4 |
| 5-bis | ✅ Tid | D-6 «a»: il regime spento non si assegna (2026-11-21, §7.2) | 4 |
| 5-ter | ✅ sessione DB | La D-6 nella forma della D-7 «2»: REQUIRE sulle due FK del regime e BLOCK su `config.regimi_fiscali` (§7.2). Applicato su dbdev e pushato (`20261121-10` … `-15`, `790fc0432`, PR #185); i due pgTAP del §7.3 corretti nello stesso giro | 5-bis |
| 5-quater | ✅ team BE/FE | La prova del rifiuto `E_ATTIVO_PADRE_NON_ATTIVO` sul campo `regime_fiscale_rf` dei due drawer: nessun codice nuovo, un test e2e (§7.2, «Dopo il push», 2026-11-21); ✅ commit di Tid (`ae2336fcfd`) | 5-ter |
| 5-quinquies | ✅ Tid | D-8 «a»: `config.regimi_fiscali` in sola lettura per l'app (2026-11-22, §7.4) | 5-quater |
| 5-sexies | ✅ sessione DB | Il giro D-8: `20261121-16`, loop dei grant, provisioning, pgTAP nuovo, pagina `manual/` (§7.4). Scritto e provato, non applicato, da committare | 5-quinquies |
| 5-septies-bis | ✅ Tid e sessione DB | D-9 «a»: il builder dei regimi di prova, nel giro del `-16` (Tid, 2026-11-22). Scritto e provato: `20261121-17`, `-18` (§7.4) | 5-sexies |
| 5-septies | ✅ team BE/FE | Il test e2e del regime spento costruisce i regimi col builder; il censimento di chi scrive la tabella (§7.4). Fatto il 2026-11-22: 8/8 verdi su dbdev con `ZEROERP_TEST_DB_E2E=1`, nessun regime di prova rimasto; censimento: l'unico scrittore era questo test. ✅ commit di Tid (`e9d5cde2a8`, PR #189) | 5-septies-bis |
| 5-octies | Tid | ✅ Apply di `20261121-16` … `-18` su dbdev, pgTAP verdi (2026-11-22, prima del BE); ✅ commit del giro DB (`e00a3c7279`, PR #188); ✅ doc auto-generata (sessione DB, 2026-11-22, §7.6) | 5-septies-bis |
| 5-novies | ✅ sessione DB | Il messaggio a catalogo di `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` nomina anche i regimi fiscali di prova (§7.5, §7.6). Scritto il 2026-11-22; ✅ applicato su dbdev (Tid, 2026-11-22); ✅ committato con l'archiviazione | 5-septies-bis |
| 6 | ✅ sessione DB | Chiusura: archiviazione (2026-11-22, §7.6) | 5-septies, 5-octies, 5-novies |

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
   catalogo dei regimi non è nel pannello, quindi a video l'operatore non ci arriva. → Risposta della sessione DB
   (2026-11-22): §7.4, D-8.

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

### 7.4 D-8 — chi scrive `config.regimi_fiscali`? ✅ Decisa: «a» (Tid, 2026-11-22)

È il punto 4 di «Dopo il push» (§7.2). Il motivo del pgTAP `dbops/test-automazione-attivo-inclusioni-v1.sql` dice
che spegnere un regime «lo può solo il migratore», ma il loop dei grant (`90_end/ci_apply/20260205-41`) dà a
`zeroerp_app` `SELECT, INSERT, UPDATE, DELETE` su `config.regimi_fiscali`, perché la tabella non è in
`v_tabelle_sola_lettura_app`. Il motivo dice il vero sul modello e il falso sui privilegi.

Struttura letta (non popolazione): `config.regimi_fiscali` è un vocabolario posseduto dal CSV (mirror
`loadUpdateData` `runOnChange` di `20261001-15`), e in `config.tabelle_gestibili` ha `lookup` sì e `pannello` no.
Nel `backend/` fuori dai test nessuno lo scrive. È la stessa forma dei vocabolari di `documenti` e di
`config.formati_file`, chiusi il 2026-11-14 con la Q10 di Tid (`90_end/20261115-98`): «un valore è ciò che il codice
sa usare: una riga scritta dall'applicazione sarebbe un valore che nessun codice onora». Il codice RF è quello del
tracciato FatturaPA.

| Strada | Che cosa | Ricadute |
| --- | --- | --- |
| **a** (raccomandata) | `config.regimi_fiscali` in sola lettura per l'app, nelle tre sedi di linee-guida-sql §11.8 (changeSet forward in `90_end`, `v_tabelle_sola_lettura_app` del loop, blocco «POSTURA DICHIARATA» di `provision_zeroerp.sql`), con il suo pgTAP di postura. Applica la Q10 a un vocabolario che ha la stessa forma: completa una decisione, non ne prende una nuova. Il motivo del pgTAP diventa vero com'è scritto | BE/FE: `backend/apps/anagrafiche/tests/db/test_regime_fiscale_spento_db.py` costruisce e spegne i regimi come `zeroerp_app` e diventa rosso (`42501`): deve costruirli per un'altra strada. Da chiedere al BE il censimento di chi scrive la tabella (test, smoke, fixture) |
| b | Il privilegio resta; si riscrive il motivo del pgTAP: il BLOCK lo fa scattare chi scrive la tabella, oggi il migratore e i test e2e, e nessun entry point dell'applicazione | Nessuna. Resta un vocabolario che l'app può scrivere, unico fra quelli posseduti dal CSV |

Con la «a» il lavoro è un giro DB piccolo e la richiesta al BE va **prima** dell'apply (il test e2e si rompe al
momento della revoca). Il brief si archivia dopo il giro: resta in `work-in-progress/` finché la richiesta al BE è
aperta, perché `/arrivi-db` legge solo lì.

#### Il giro D-8, scritto (sessione DB, 2026-11-22)

| File | Che cosa |
| --- | --- |
| `90_end/20261121-16-revoke-app-scrittura-regimi-fiscali` | Il forward su dev: a `zeroerp_app` `SELECT`, via `INSERT, UPDATE, DELETE`. Lo stampo di `90_end/20261115-98` |
| `90_end/ci_apply/20260205-41-apply-runtime-grants-ci` | `config.regimi_fiscali` in `v_tabelle_sola_lettura_app` (il loop è `runOnChange` in `ci_apply`, §11.1) |
| `scripts/sql/provision_zeroerp.sql` | Il blocco «POSTURA DICHIARATA» col `REVOKE`, la terza sede di §11.8 |
| pgTAP `config/test-regimi-fiscali-sola-lettura-v1.sql` | Nuovo, plan 3, runner di default (l'app): solo `SELECT` per l'app; `UPDATE` e `INSERT` come app rispondono `42501` |
| pgTAP `dbops/test-automazione-attivo-inclusioni-v1.sql` | Il motivo del runner owner rimanda alla porta: ora è vero com'è scritto |
| `manual/` `config/regimi_fiscali.md` | «L'applicazione lo legge e basta», con la regola e il perché |

Nessuna funzione del catalogo scrive `config.regimi_fiscali` (`prosrc`, scratch `zeroerp_ruoli`, 2026-11-22): lo
scrive solo il mirror del CSV, come migratore.

**La prova** (2026-11-22, scratch `zeroerp_ruoli`). `scripts/prova_changeset.py --pgtap`, come owner: estratto eseguito
per intero e annullato, test 1 da rosso a verde, catalogo identico prima e dopo. I test 2 e 3 da owner sono rossi
per costruzione, perché l'owner scrive. Il pgTAP come app, senza l'estratto: 3 rossi attesi, perché oggi l'app scrive.
Le due istruzioni si leggono senza errore (`caught: no exception`, nessun `42703`), quindi dopo l'apply il `42501`
arriva per il motivo giusto. ⚠️ **Il verde pieno come app non è provato**: si vede solo dopo l'apply. Verdi i guardrail
delle forme, `runOnChange`, preCondition, letterali, GRANT ai ruoli batch e preambolo pgTAP.

**Garanzie ritirate:** nessuna. Il giro toglie un privilegio all'app e non allenta nessun vincolo.

#### Prima dell'apply, al team BE/FE

⚠️ **Riscritta dalla D-9 (sotto, «La richiesta al BE/FE, con il builder»)**: i tre punti qui restano come storia.

1. `backend/apps/anagrafiche/tests/db/test_regime_fiscale_spento_db.py` crea e spegne regimi come `zeroerp_app`
   (§7.2, «Dopo il push», punto 2; casi 6-8 del §6). Dopo l'apply ogni scrittura su `config.regimi_fiscali` risponde
   `42501`, e il test diventa rosso. Serve un'altra strada per costruire i due regimi (acceso e spento) e il regime con
   `codice` diverso da `codice_interno`. La scelta è del BE.
2. **Censimento richiesto**: chi scrive `config.regimi_fiscali` come applicazione in `backend/` e `frontend/`. Vanno
   compresi test, smoke, fixture, management command e seed di sviluppo, anche fuori dal file del punto 1. Il DB
   vede solo questo file, che viene dal §7.2, e non è detto che sia l'unico.
3. Il contratto applicativo non cambia: lookup e dettagli leggono la tabella come prima.

#### D-9 — la proposta del BE: un builder dei regimi di prova ✅ Decisa: «a» (Tid, 2026-11-22)

**La proposta (sessione BE/FE, in chat).** Nello stesso giro del `-16` il DB aggiunge un builder `SECURITY DEFINER`,
per esempio `dbops.fn_pgtap_crea_regime_fiscale(codice_interno, codice, descrizione, attivo)`, che scrive solo regimi
di prova riconoscibili (`PGTAP-…`, `E2E-…`). Il test lo chiama al posto dell'`INSERT` e dell'`UPDATE`, e gli otto
casi restano. Il caso 3 non spegne più un regime: il fornitore spento prende il regime spento, poi si riaccende. Il
BE stesso nota il rischio: è una porta di scrittura che resta anche fuori dai test.

**La risposta della sessione DB, sulla struttura:**

* ⛔ **Un regime riconoscibile dal codice non si può fare.** `codice_interno` ha il CHECK `^RF[0-9]{2}$`: `PGTAP-…` e
  `E2E-…` non nascono. Il segno «di prova» deve stare altrove.
* ⚠️ **Nessuno dei 56 builder `dbops.fn_pgtap_*` è `SECURITY DEFINER`** (scratch, 2026-11-22). Scrivono coi
  privilegi di chi li chiama, e quindi non aprono porte. Un builder DEFINER con quel prefisso sarebbe il primo, e
  riaprirebbe proprio la porta che la D-8 chiude. Il nome non deve farlo sembrare uno di loro.
* ⭐ **Il precedente giusto è la porta dei dati di sviluppo**: `anagrafiche.fn_provisiona_dati_di_sviluppo`, una
  DEFINER che apre solo in `SVILUPPO` (`script.fn_ambiente_installazione()` e
  `dbops.fn_dati_di_sviluppo_ammessi_su_valori`, altrimenti `E_DATI_DI_SVILUPPO_IN_PRODUZIONE`). La CI è `SVILUPPO`
  (provisioning `ambiente=SVILUPPO`), quindi l'e2e lì gira.

**La forma che il DB propone (strada «a» della D-9):** una DEFINER `dbops.fn_crea_regime_fiscale_di_prova(codice_interno,
codice, descrizione, attivo)`, eseguibile dall'app, con tre limiti nel corpo:

1. si apre solo in `SVILUPPO`, col BB dell'ambiente, nella stessa forma della porta dei dati di sviluppo;
2. scrive un regime con il segno di prova in `meta` (per esempio `{"di_prova": true}`) e rifiuta un `codice_interno`
   che esiste già: una riga del catalogo non la tocca mai;
3. solo inserimento: niente `UPDATE` e niente spegnimento. Il regime spento nasce spento, come propone il BE per il
   caso 3.

Ricadute:

* il caso «spegnimento di un regime in uso» (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, §7.2, esito, riga 5) **esce dall'e2e**:
  dopo la D-8 l'app non lo raggiunge per nessuna strada, e la regola la prova il pgTAP
  `dbops/test-automazione-attivo-inclusioni-v1.sql`, come owner. Restano gli altri casi;
* un regime di prova scritto in una transazione **confermata** su dbdev resta, e compare nelle tendine. Il test non fa
  COMMIT (§7.2), e il segno in `meta` lo rende riconoscibile e cancellabile a mano;
* il giro DB cresce: un codice d'errore nuovo per «il codice esiste già», un pgTAP del builder (si apre solo in
  `SVILUPPO`, rifiuta un codice del catalogo, il segno c'è) e la pagina `manual/`.

| Strada | Che cosa |
| --- | --- |
| **a** (raccomandata dal DB) | Il builder DEFINER nella forma sopra, nello stesso giro del `-16` |
| b | Nessuna porta: l'e2e costruisce i regimi con una seconda connessione come migratore, e solo nell'arrange. Lato DB non cambia niente; servono le credenziali del migratore nei test, in CI e su dev |
| c | Nessuna porta: il caso del regime spento esce dall'e2e del BE. La regola la provano i pgTAP; il BE prova la traduzione del campo con un errore costruito. Si perde la prova sul DB vero del canale `COLUMN`

#### Il giro D-9, scritto (sessione DB, 2026-11-22)

Si aggiunge al giro D-8: stessi commit e apply.

| File | Che cosa |
| --- | --- |
| `20_code/dbops/20261121-17-create-fn-crea-regime-fiscale-di-prova` | Il builder, `SECURITY DEFINER`, nei tre limiti: solo in `SVILUPPO` (`E_DATI_DI_SVILUPPO_IN_PRODUZIONE`, la stessa regola della porta dei dati di sviluppo, nessun codice nuovo); solo righe nuove con `meta` = `{"di_prova": true}`, mentre un codice esistente lo rifiutano `uq_regimi_fiscali_codice_interno` e `uq_regimi_fiscali_codice`; solo `INSERT`. Firma coi `%TYPE`, restituisce l'id |
| `20_code/dbops/20261121-18-update-vw-radici-di-prova-in-produzione-regimi` | Il presidio delle radici di prova ha un terzo ramo, `REGIME`: un regime col segno, in un database `PRODUZIONE`. Un dato di prova ha un presidio solo. Corpo dal catalogo, i due rami di prima invariati |
| `80_data/sql/config/codici_errore.csv` | La descrizione di `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` nomina anche il builder |
| `80_data/sql/dbops/presidi.csv`, `presidi_testi.csv` | La nota e il testo del presidio dicono anche «regimi fiscali di prova» |
| pgTAP `config/test-regimi-fiscali-sola-lettura-v1.sql` | Plan da 3 a 6: come app, in `SVILUPPO`, il builder crea un regime spento col segno; RF01 e il suo `codice` rifiutati dai due UNIQUE |
| pgTAP `dbops/test-etichette-di-prova-v1.sql` | Plan da 16 a 17: un regime di prova nato in `SVILUPPO` lo vede il presidio in `PRODUZIONE` (test 13); in `PRODUZIONE` il builder non parte (15 nuovo; i vecchi 15 e 16 sono ora 16 e 17) |
| `manual/` | Nuova `dbops/fn_crea_regime_fiscale_di_prova.md`; `dbops/vw_radici_di_prova_in_produzione.md`; `config/regimi_fiscali.md` |

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, 2026-11-22: `-17`, `-18`, `-16`, nell'ordine di fase).

| pgTAP | Senza | Con |
| --- | --- | --- |
| `dbops/test-etichette-di-prova-v1` (owner) | 7 ok, si ferma (il builder non c'è) | 17/17 |
| `config/test-regimi-fiscali-sola-lettura-v1`, da owner | 1 ok, si ferma | 4 ok; il 2 e il 3 rossi per costruzione (l'owner scrive) |
| `dbops/test-catalogo-presidi-v1` | 11/11 | 11/11 |
| `dbops/test-automazione-attivo-inclusioni-v1` | 12/12 | 12/12 |
| `anagrafiche/test-fn-crea-fornitore-v1` | 21/21 | 21/21 |
| `config/test-pannello-porta-v1`, da owner | 8 ok, 3 rossi per costruzione | uguale |

Il catalogo è identico prima e dopo ogni prova. I guardrail sono verdi: forme, `runOnChange`, preCondition, letterali,
GRANT ai ruoli batch, COMMENT al presente (alla prima stesura i due COMMENT nominavano il brief, ora tolto) e preambolo
pgTAP. ⚠️ **Come app il test della sola lettura non è provato verde**: senza i changeSet il builder non esiste, e la
prova non sa girare l'estratto come app. Si vede dopo l'apply. Un difetto trovato e corretto provando: `format('%s')`
su un booleano scrive `f`, non `false`.

**Garanzie ritirate:** nessuna. Il catalogo dei regimi resta in sola lettura per l'app fuori dal builder, e il builder
non tocca le righe che esistono.

#### L'apply (2026-11-22)

Tid ha applicato `20261121-16` … `-18` su dbdev, con i pgTAP verdi. È il verde come app del test della sola lettura
che la prova non sapeva dare. L'apply è venuto **prima** del BE: alla stessa data il test e2e
`backend/apps/anagrafiche/tests/db/test_regime_fiscale_spento_db.py` scrive ancora la tabella direttamente (l'`INSERT`
dei regimi e l'`UPDATE` che spegne), quindi con `ZEROERP_TEST_DB_E2E=1` è rosso con `42501`, finché non passa al builder.
L'e2e è spento di default e acceso in `ci-validate.yaml`, che ricostruisce il DB dal branch: la CI diventa rossa quando
il giro DB entra in `Tito-dev` senza il punto 1 qui sotto. Conviene che le due PR arrivino insieme.

Restano:

* il commit del giro DB, coi soli file di questo cantiere: `brief-db-attivo-fk-senza-suffisso-id.md` è di un'altra
  sessione e resta fuori;
* la doc auto-generata, da rigenerare: `config.regimi_fiscali` (privilegi), `dbops.fn_crea_regime_fiscale_di_prova`,
  `dbops.vw_radici_di_prova_in_produzione`. Finché non c'è, il contratto si legge dal catalogo.

#### La richiesta al BE/FE, con il builder (⚠️ arriva dopo l'apply: l'e2e è rosso finché non c'è)

1. `backend/apps/anagrafiche/tests/db/test_regime_fiscale_spento_db.py`: i regimi di prova si costruiscono con
   `SELECT dbops.fn_crea_regime_fiscale_di_prova(codice_interno, codice, descrizione, attivo)`, che restituisce l'id,
   al posto dell'`INSERT` e dell'`UPDATE`. `codice_interno` deve essere `RF` più due cifre e libero (l'e2e ne sceglie
   uno che il catalogo non ha); `codice` libero anche lui, e per il caso 8 diverso da `codice_interno`. Il regime
   spento nasce spento: il caso 3 diventa «il fornitore spento prende il regime spento, poi si riaccende».
2. Il caso «spegnimento di un regime in uso» (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, §7.2, esito, riga 5) **esce
   dall'e2e**: dopo la D-8 l'app non lo raggiunge per nessuna strada, e il builder non spegne. La regola la prova il
   pgTAP `dbops/test-automazione-attivo-inclusioni-v1.sql`, come owner.
3. Il test non fa COMMIT: un regime di prova confermato su dbdev resterebbe nelle tendine. Il segno è
   `meta ->> 'di_prova' = 'true'`.
4. **Censimento richiesto**: chi scrive `config.regimi_fiscali` come applicazione in `backend/` e `frontend/`, compresi
   test, smoke, fixture, management command e seed di sviluppo, anche fuori dal file del punto 1. Ogni scrittura
   diretta, dopo l'apply, è un `42501`.
5. Il codice `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` non è nuovo, ed è già nella policy: in CI l'ambiente è `SVILUPPO`, e
   il builder lì si apre.

### 7.5 Dopo il giro D-9, dal BE/FE (2026-11-22)

**Fatto.** Il test e2e `test_regime_fiscale_spento_db.py` costruisce i regimi con `dbops.fn_crea_regime_fiscale_di_prova`
ed è verde sul DB vero (8/8, `ZEROERP_TEST_DB_E2E=1`); il caso 3 è nella forma del §7.4 (il fornitore spento prende il
regime nato spento, poi si riaccende). Nessun regime di prova rimasto su dbdev. Il caso «spegnimento di un regime in
uso» nel file non c'era: niente da togliere. **Censimento** di chi scrive `config.regimi_fiscali` in `backend/`,
`frontend/`, script, smoke e CI: l'unico era questo test. Gli altri (il test della conferma, lo smoke dei fornitori,
service, repository, drawer, `voceRegimeFiscale.js`) leggono e basta. Il lookup dei regimi non filtra il segno
`meta.di_prova`: va bene, perché il test non fa COMMIT e in produzione c'è il presidio.

**Richiesta alla sessione DB.** Il giro D-9 ha esteso la nota di `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` in
`codici_errore.csv`, ma il messaggio in `80_data/sql/config/messaggi_errore.csv` (riga `it`, id 1356) dice ancora
«utenti e soggetti di prova», e la causa «Gli utenti e i dati di prova». Proposta di testo:

* messaggio: «I dati di sviluppo (utenti, soggetti e regimi fiscali di prova) non si creano in un'installazione di %s.»
* causa: «Utenti, soggetti e regimi fiscali di prova esistono solo nei database di sviluppo: in produzione resterebbero
  mescolati ai dati veri.»

Il ripiego del BE (`error_messages_fallback.py`) ha già il messaggio senza segnaposto, nella stessa forma. Nessun
codice nuovo e nessuna policy da rigenerare.

### 7.6 La chiusura (sessione DB, 2026-11-22)

* **Il messaggio (passo 5-novies).** La riga `it` di `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` in
  `80_data/sql/config/messaggi_errore.csv` (id 1356) porta i due testi proposti nel §7.5, senza ritocchi: il messaggio
  tiene il suo `%s`, che il VARIADIC riempie con l'ambiente. Il loader `20260614-08` è un `loadUpdateData` con
  `runOnChange: true` sulla chiave `id`: niente changeSet nuovo. Applicato su dbdev da Tid il 2026-11-22. Nessun pgTAP,
  test o guida citava il testo vecchio.
* **La doc auto-generata** del giro D-8/D-9 è rigenerata da dbdev: nasce la pagina di
  `dbops.fn_crea_regime_fiscale_di_prova`, si aggiornano `dbops.vw_radici_di_prova_in_produzione` e gli indici di
  `config` e `dbops`. `check_i18n_keys.py` pulito.
* **Il giro D-8/D-9 non chiede un `/verifica-db` a parte** (Tid, 2026-11-22): `20261121-16` … `-18` sono stati
  scritti e provati prima dell'apply, applicati su dbdev coi pgTAP verdi e committati (`e00a3c7279`, PR #188). Non si
  ripropone alla prossima chiusura.
* **Niente debito.** Il solo punto lasciato a dopo, `acquisti.ordini` sul termine lato BE/FE (§4, punto 5), è parte
  dello sviluppo del BE/FE degli acquisti, che non esiste ancora: resta qui come promemoria e non apre un brief.
* **Archiviato** in `work-done/2026/`; i due rimandi per percorso (`brief-db-attivo-fk-senza-suffisso-id`,
  `analisi-simmetria-ordini-acquisto`) puntano alla sede nuova.
