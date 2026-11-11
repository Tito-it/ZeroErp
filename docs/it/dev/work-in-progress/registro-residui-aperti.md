# Registro dei residui aperti

> Il **dettaglio** di ciò che i brief chiusi hanno lasciato aperto: decisioni rimandate, debiti dichiarati,
> collaudi da fare. L'**indice**, una riga per voce, sta in `.codex/PROJECT_CONTEXT.md` § «Aperto — Media
> priorità», che ogni sessione legge all'avvio; questo file si apre quando il lavoro tocca una voce.
>
> **Come si tiene.** Alla chiusura di un brief i suoi residui si scrivono **qui**, col rimando al documento in
> `work-done/` e al paragrafo, e in PROJECT_CONTEXT si aggiunge **una riga** con lo stesso titolo in grassetto.
> Quando un residuo si chiude, la voce si **toglie** da tutti e due i posti (non si marca ✅). I percorsi
> `work-done/…` e `work-in-progress/…` sono relativi a `docs/it/dev/`.

- **Briciole lasciate aperte da brief chiusi** (raccolte il 2026-11-11, quando le voci dei cantieri chiusi sono
  uscite da § «Altri cantieri aperti»; il dettaglio è nel documento citato):
  - **D31 resta aperta per ORARIO e CONSUMO** (G-4 di `work-done/brief-db-contratto-righe-periodiche-in-commessa.md`):
    aspettano timesheet e letture;
  - **collaudo a video dei form di DDT e ordine** (`work-done/brief-db-esecutivi-ba-coppia.md`, D21). Di Tid;
  - **il «perché» nel tooltip di `RIGA_NON_AMMESSA`** (`work-done/brief-db-offerta-emissione-ed-erogazione.md` §J.4):
    proposta aperta, non bloccante;
  - **D24, il presidio C2 non vede i BB trigger col codice in `TG_ARGV`** (registro DB
    `migliorie-generali-da-test-valutazione.md`, seguito di `work-done/brief-db-guard-emittente-ba-unico.md`): il BE
    tiene un'esenzione su `E_DOC_EMITTENTE_BA_INCOERENTE` finché la vista non li vede;
  - **la sorgente sugli acquisti** (`work-done/brief-db-sorgente-documento-e-riga.md`): le quattro tabelle restano
    nella grammatica precedente, elenco dichiarato del presidio; si allineano col cantiere `acquisti`;
  - **i residui del cliente manuale** (§7 di `work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility.md`, D33):
    fanno parte dello sviluppo delle utility (Tid, 2026-10-15).
- **Residui di `work-done/brief-db-contratto-righe-periodiche-in-commessa.md`** (ereditati il 2026-11-01
  dalla chiusura, §7.14), nessuno bloccante:
  - **il collaudo a video** del form della riga a canone (contratto e offerta) e della colonna «Periodicità»
    della lista 37 (anche sul composito, e nell'export). Di Tid;
  - **la colonna «Periodicità» della lista 37**: codice o descrizione (proposta: la descrizione, col JOIN
    nella proiezione del repository), e se ordinabile (sul ritmo `config.periodicita.mesi`, con la voce in
    `RIGHE_ORDER_COLUMNS` e `ordinabile = t` insieme). Di Tid; poi team DB e BE;
  - gli smoke di `backend/scripts/tests/` non lanciati nel giro BE del §7.13.6.
- **Residui di `work-done/brief-db-scadenza-preventivi.md`** (ereditati il 2026-11-01 dalla chiusura, §8.10),
  nessuno bloccante:
  - **`validita_al` dice due cose**: la scadenza dell'offerta e, come ripiego dietro `competenza_mese`, il periodo
    di competenza (`fn_list_preventivi_da_pushare`, `vw_dash_fatturazione_preventivi`). Se la competenza debba
    avere una sede sua lo decide Tid; poi team DB;
  - **il verbo di chiusura del listino** (`vendite.fn_chiudi_versioni_listino_scadute`) legge ancora i letterali
    `'ATTIVA'`/`'CHIUSA'`, mentre il gemello del preventivo legge il vocabolario. Team DB.
- **Residui di `work-done/brief-modello-documento-vendita.md`** (ereditati il 2026-10-31 dalla chiusura, §18.6),
  nessuno bloccante:
  - **i permessi `emetti_offerta`, `emetti_contratto`, `emetti_ordine`, `attiva_listino` ai profili** su dbdev:
    al 2026-10-26 nessun profilo li aveva, e senza nessuno emette, attiva o cessa quei documenti. Di Tid;
  - **due rami del preventivo senza strada dall'interfaccia** (§18.4): la riaccettazione di un preventivo già
    accettato (aggiorna la sola modalità di fatturazione) e «Genera pratica» (`genera_pratica`). Ritirarli o dar
    loro un accesso. Di Tid;
  - **`DocumentoDrawerHost` tace sul drawer che non si carica** (`catch { return }`): il click su una tappa dei
    «Passaggi» non fa niente, senza avviso né console (visto a video il 2026-10-31). Proposto un avviso. FE, con
    l'ok di Tid.
- **Residui di `work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md`** (ereditati il
  2026-10-24 dal collaudo passato, §3):
  - **il reset del rifiuto sta solo nel BE del preventivo** (`preventivi_service.py` `aggiorna_riga`,
    «Auto-reset stato approvazione»), nessun trigger a DB: una correzione del prezzo che non passa da lì
    lascia la riga `REJECTED` e il documento bloccato. Su contratto e offerta un reset equivalente non
    risulta: asimmetria del modello. Da decidere, di Tid, se la regola vada a DB, simmetrica su tutti i
    documenti; brief DB nuovo;
  - **la riga `test-preventivi-approvazione-prezzo.sql`** è ancora in `db/pgtap/baseline-rossi-ci.tsv`
    (`ERRORE_FIXTURE`): si toglie dopo la corsa CI su `Tito-dev` (`scripts/pgtap-baseline-ci-rientrati.sh`).
    Team DB.
- **Residui di `work-done/brief-db-modelli-documento-standard.md`** (ereditati il 2026-10-21 dalla
  chiusura, §11.5.4 e riga 10):
  - **il giro degli smoke su `dev.smoke`** (§7, B-11): DEVA emette con lo standard e chiude una
    fattura. Non fatto: il brief si è chiuso col collaudo a video. BE;
  - **B-8, la matrice utility dell'emittente**: mostra solo l'override grezzo. Mettere nei suoi campi
    i parametri di sistema li farebbe leggere come override; la forma proposta sono due campi
    «effettivo» da `anagrafiche.fn_parametri_importo_utility` e una colonna FE accanto. Da decidere,
    di Tid;
  - **la numerazione della versione nuova** di un template: la versione scritta da zero la numera il
    BE (`next_versione_num`, MAX+1), la copia la numera il DB (`fn_crea_bozza_da_versione`). Due sedi
    dello stesso numero; si chiude con un verbo DB per la versione nuova. Brief nuovo se Tid vuole;
  - **`vendite.fatture.utility_id NOT NULL`** (§10.9, facoltativa): l'unico creatore applicativo la
    pretende già, molte fixture pgTAP inseriscono fatture senza. Di Tid.
- **Residui di `work-done/brief-db-presidio-job-run-a-chi-tocca.md`** (ereditati il 2026-10-18 dalla chiusura),
  nessuno bloccante:
  - **errori lato client senza SQLSTATE** (§12): una connessione che cade dentro un command arriva come
    `OperationalError` senza SQLSTATE e va a `PROGRAMMA`. Se servirà, la strada è riconoscere la classe Python
    (`OSError`, `ConnectionError`), che è la tassonomia lasciata al BE dal §4.2. BE;
  - **`SMOKE_GIRO_FALLITO`** copre sia il tetto di tempo sia lo script uscito con 2 (§12): si separa quando lo
    smoke avrà un caso reale da instradare diversamente. BE;
  - **`error_detail` con la riga `CONTEXT:`** (§5, visto nel collaudo del 2026-10-18): per un errore PL/pgSQL
    `registered_job` scrive `str(exc)`, che porta il `CONTEXT` del driver su una riga nuova, e il digest stampa la
    voce spezzata. BE;
  - **il `%TYPE` mancato del giro 1** (§10.1-bis): debito noto, deciso di non riscrivere (Tid, 2026-10-16). DB.
- **Residui di `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`** (ereditati il 2026-10-14 dalla
  chiusura):
  - **D-4, che cosa registra il titolo IVA `COOPERATIVA`** (§4): l'aliquota agevolata delle cooperative sociali
    riguarda di solito le prestazioni rese **dalla** cooperativa, ma il titolo sta sul cliente. Finché non è
    chiarito, `COOPERATIVA` non ha righe nella matrice `config.tipi_titolo_iva_tipi_soggetto_dettaglio`, e quindi
    non è ammesso su nessun soggetto. Se la risposta è «titolare il cliente», basta una riga nel CSV. Altrimenti il
    titolo è nella tabella sbagliata. Da decidere, di Tid;
  - **censimento dei titoli IVA fuori regola** (§8.2, query pronta): la deve lanciare Tid **come owner**, perché
    come app la RLS non mostra nessun titolo. I titoli fuori regola non bloccano niente, ma alla prossima
    modifica il guard li rifiuta;
  - **`SGT-0000121` con `cliente_pa = 'S'`** (§8.1): un privato, il caso della segnalazione. Il guard lo rifiuterà
    alla prossima modifica dei flag o della natura. Da riportare a `N` a mano (Tid);
  - **`anagrafiche.fornitori.split_payment`** (§7): nullable, senza regola sulla natura, senza lettori oltre
    `vw_fornitori_dettaglio`. Sul passivo la scissione dipende dall'emittente, non dal fornitore: forse è nella
    sede sbagliata. Da verificare; se confermato, brief suo.
- **La commessa vuota lasciata dal push batch** (DB + BE, ereditata il 2026-10-13 dalla chiusura di
  `work-done/brief-db-annullo-a-valle-riapre-a-monte.md` §10.8): nel push batch (`pr_run_commesse_push`,
  best-effort per riga) la commessa nasce prima che il batch delle righe le accetti; se una riga e'
  rifiutata, per qualunque causa, la commessa resta vuota e aperta e il ponte di emittibilita' scrive un
  errore nel report. Strade di modello: (a) il fan-out chiede al DB la commessa aperta del documento prima di
  crearne una; (b) le righe di un documento si scrivono dentro il suo savepoint; (c) il DB non crea la
  commessa vuota. Da decidere, di Tid con il team DB.
- **Residui di `work-done/brief-db-istanza-nasce-col-ba.md`** (ereditati il 2026-10-10 dalla chiusura):
  - ⏭️ **collaudo a video delle pratiche** (§7.4): la tendina della fornitura (una riga per fornitura, con la
    utility), nessun campo fornitura su chi non è cliente, offerta e contratto col cliente ereditato dalla
    pratica. Rimandato da Tid: si fa alla ripresa del cantiere pratiche;
- **La coerenza tra codice fiscale e sesso ha una sede sola, e parziale** (DB + BE, ereditata il 2026-10-10
  dalla chiusura di `work-done/brief-db-sesso-senza-default.md`, D5, rimandata da Tid il 2026-10-09): la
  controlla solo `SoggettiService._valida_cf_congruenza`, e solo nella **creazione** di una persona fisica.
  Una modifica (`PATCH`) di sesso o CF, o chi scrive senza passare dal BE, può mettere un CF da donna con
  sesso `M`. `X` e i CF esteri non si possono confrontare. Da decidere, di Tid: se la regola scende nel
  guard del DB, o resta nel BE estesa alla modifica.
- **La corsa appesa non è «in corso» nella liveness del BE** (BE/FE, ereditata il 2026-10-10 dalla chiusura
  di `work-done/brief-db-corsa-saltata-non-e-una-corsa.md` §8.7): una corsa col processo vivo che tiene il
  lock, seguita da skip, ha come riga più recente la skip, chiusa; `job_liveness`/`list_job_summary` dicono
  `in_corso = false`, e badge e digest non la mostrano. Il caso lo vede `maintenance.vw_job_run_da_guardare`
  («presa e mai chiusa»), coerente con D3 di quel brief. Se la si vuole anche nel BE: `in_corso` dall'ultima
  corsa **vera**, con la sua data di avvio — un campo in più nella forma condivisa con la coda lavori. Da
  decidere, di Tid.
- **La lista dei processi non dice se un processo gira adesso** (ereditato il 2026-10-10 dalla chiusura di
  `work-done/brief-db-presidio-processi-testo-per-causa.md` §6.6): «Attivo» è il flag del catalogo, «Esito»
  quello dell'ultima corsa registrata (per un servizio `SESSIONE`, l'avvio). Lo stato vivo (`OK`, `MUTO`,
  `JOB_SPENTO`…) lo calcola già `dbops.vw_processi_programmazione`: una colonna «Stato» in `amm.processi`
  vuole la riga nel seed della lista (DB) e la lettura nel repository. Proposta, da decidere di Tid.
- **Presidi, i residui del brief dei testi per chi agisce** (ereditati il 2026-10-06 dalla chiusura di
  `work-done/brief-db-presidi-cosa-significa-cosa-fare.md`):
  - **D-4**, le quattro misure larghe per costruzione (`vw_codici_errore_forme_condizione`,
    `vw_codici_errore_da_dichiarare`, `vw_punti_primo_motivo`, `vw_punti_canale_campo`): il pannello le mostra
    come un numero da guardare. O diventano `INVENTARIO`, o la natura del pannello si separa da quella del
    cancello (§7, decisione del team DB e di Tid);
  - la **postura in sola lettura** di `dbops.presidi` e `dbops.presidi_testi` per l'app (§8.1): oggi il loop
    dei grant di `ci_apply` dà anche la scrittura. Non chiesta, da decidere.
- **`HTML_MARKDOWN_BLOCKS` si sceglie ma non fa niente** (BE `documenti`, ereditato il 2026-10-04
  dalla chiusura di `work-done/brief-db-vocabolari-versione-template.md` §5.6): il valore sta nel
  vocabolario `documenti.formati_template` (la Decisione 4, «markdown solo per blocchi controllati»),
  ma il render tratta ogni versione come HTML e non legge `markdown_template`. Da decidere se
  implementarlo o ritirarlo, quando si tocca il trattamento del markdown.
- **Le versioni pubblicate stampano coi margini delle colonne (15 mm), non coi 18/16 mm del loro
  CSS** (dal 2026-10-04, R-BE-V2a di Tid: la pagina la decidono le colonne). Per tornare ai 18/16 mm
  servono versioni nuove con i margini nelle colonne; l'`@page` di formato e margini nel loro CSS
  non ha più effetto (restano i piè di pagina). Le ristampe dei documenti già emessi escono coi 15 mm.
- 🟡 **L'editor dei workflow perde le righe in compilazione senza chiedere** (FE, ereditato il
  2026-10-03 dalla chiusura di `work-done/analisi-fe-chrome-drawer.md`, D-13): `DefinizioneEditorView`
  e i pannelli di passi e archi (`useEditableCollection`) non tengono la fotografia del form di riga,
  quindi cambiare riga o uscire butta cio' che si e' scritto. Il rimedio esiste ed e' provato sui
  documenti: fotografia nel form (`useDrawerFormPreserve`) + `confermaCambio` di `useFormInline`.
  Non fatto con il resto perche' non e' un drawer documento e ha form propri: un giro a se'.
- **`E_ATTIVO_REQUIRE` è TECNICO anche quando il dato l'ha scelto una persona**
  (DB, `dbops`; residuo di `work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md`): il
  codice del require generato dal framework ATTIVO è candidato allo split, per **tutte** le coppie
  ATTIVO: oggi un riferimento a un dato disattivato scelto dall'operatore esce come 500, lo
  stesso codice di un trigger montato male. Cantiere `dbops`, non di dominio; intanto il BE
  pre-verifica «attivo» e risponde 400 col campo (§5.5 nota 2 e tabella dei residui, voce 4).
- 🟡 **IVA per cassa: i residui del cantiere** (DB, ereditati il 2026-10-03 dalla chiusura
  di `work-done/brief-db-esigibilita-iva-per-cassa-emittente.md` §12):
  **R-DB-1** — i riepiloghi IVA **memorizzati** dei preventivi non si ricalcolano
  quando cambia la regola che li produce (rimandato da Tid, SQL a mano nel §9.5;
  si riapre al prossimo cambio della regola: ricalcolo del pregresso o riepilogo
  derivato come ordini e DDT); **storicità del regime** dell'emittente (D-8,
  oggi senza validità nel tempo); **domande al consulente** (§9.4: RF16, catalogo
  RF, DDT senza cliente); **annotazioni future** (scissione, inversione
  contabile, RF19) come righe di `vendite.fn_annotazioni_fattura`.
- 🟡 **Le variabili di una versione di template non si validano alla pubblicazione**
  (DB + BE, ereditata il 2026-10-01 dalla chiusura di
  `work-done/brief-db-documenti-versione-contesto-template.md`, D-C3 §7 e §14): le
  decisioni 35-36 del 2026-04-29 (`work-done/sviluppo-documenti.md`) volevano
  `context_schema` «contratto leggero delle variabili attese», validato prima di
  pubblicare; il campo è ancora `'{}'` ovunque e nessuno lo legge. Il caso grave
  (pezzi mancanti in silenzio per un cambio di forma) lo chiude già
  `versione_contesto`; questo è il raffinamento per variabile. Sede naturale: la
  pubblicazione, la stessa della verifica degli asset citati
  (`work-done/brief-be-documenti-risorse-esterne-render-pdf.md` §5.3). Con la stessa
  chiusura, facoltativa al team DB: la colonna «Forma dei dati»
  (`versione_contesto`) nella lista configurabile `documenti.template_versioni`
  (88) — il campo viaggia già nelle righe (§12.1 del brief).
- ⏳ **«Annulla» e «Porta a Bozza» sulle distinte non manuali: spenti col motivo**
  (DB poi BE/FE, ereditata il 2026-09-30 dalla chiusura di
  `work-done/brief-db-righe-distinta-annullata-fuori-dalle-code.md`, R-3 + D-6 §11.3-§11.4,
  D-6 approvata da Tid). Oggi le due voci si propongono accese su una GENERATA
  e finiscono in 409 (`E_CONTABILE_ANNULLO_NON_MANUALE`,
  `E_CONTABILE_RIAPERTURA_NON_MANUALE`): le regole vivono solo nel corpo del
  guard `trgfn_vendite_contabili_guard_validazione` e non c'è una check da
  leggere. ⏳ Al team DB: `script.fn_check_contabile_transizione` + il guard che
  la chiama (P-9 … P-12). Poi il BE espone `transizioni_blocco` e il drawer spegne
  le voci col motivo.
- 🟡 **Colori PrimeVue ancora scritti nei componenti** (FE, registrato il
  2026-09-26 alla chiusura di `work-done/analisi-fe-regole-standard-violate-dal-codice.md`
  R-3): circa 60 `var(--p-*)` — `primary-700/500/50`, `yellow-*`, `blue-*`,
  `surface-200/400`, `border-radius-sm`… — che non hanno ancora un token
  `--app-*` perché il loro **significato** non è nominato. Si decide caso per
  caso cosa dicono (il nome è il significato, non la tinta), poi un guard che
  tenga lo zero. Regola: frontend-standards § «Stili CSS».
- 🟡 **`djangorestframework-simplejwt` senza un manutentore certo** (BE, sicurezza;
  registrato il 2026-10-03): siamo alla 5.5.1 (21-07-2025), ultima release;
  PyPI dichiara il supporto solo fino a Django 5.2 (noi siamo su 6.1). Il
  repo sta ancora su `jazzband/`, ma Jazzband ha annunciato la chiusura il
  14-03-2026, coi progetti da trasferire. Oggi va bene così: la crittografia è
  di PyJWT (mantenuto a parte) e la configurazione è prudente (access token da
  10 minuti, rotazione e blacklist del refresh). Le condizioni: i test su login,
  refresh, rotazione e blacklist vanno fatti girare a ogni salto di Django o DRF;
  poi va seguito dove finisce il repo, l'eventuale nuova release con Django 6 e
  gli advisory. **Da decidere prima della produzione**, se il manutentore non si
  è chiarito: sostituirlo con un nostro strato sopra PyJWT, cioè una dipendenza
  in meno e del codice nostro in più. È una scelta di Tid.
- ❓ **Le FK verso `django.auth_user` non nascono su un'installazione nuova**
  (DB, domanda di forma per Tid, ereditata il 2026-09-27 dalla chiusura di
  `work-done/brief-db-blocco-login-per-credenziale.md`, §11.5): con
  `onFail: MARK_RAN` il changeSet del «ponte django» si segna quando Liquibase
  gira prima di `manage.py migrate` (la tabella non esiste ancora) e non si
  riprova più. In CI nessuna FK del ponte esiste e
  `config/test-fk-auth-user-ponte-django-v1` salta. L'indice sull'email (D-B5 di
  quel brief) usa invece `onFail: CONTINUE`, che salta senza segnare e riprova al
  migrate successivo. Da decidere se portare a `CONTINUE` tutte le FK del ponte
  (le 18 storiche e `20260925-22`/`-23`): è un cambio della forma di casa, del
  team DB. ⚠️ Dal 2026-10-06 ha un effetto visibile: senza il ponte
  `script.fn_elimina_credenziale` rifiuta sempre (fail-closed,
  `E_CREDENZIALE_STORIA_NON_VERIFICABILE`, D-4 del brief elimina-credenziale),
  quindi su un'installazione nuova nessuna credenziale si elimina (brief archiviato in `work-done/`).
- 🟡 **Tetto d'area dei permessi — due decisioni residue di Tid**, non
  bloccanti (brief §9.6). Il cantiere è ✅ **chiuso il 2026-10-06** (DB
  `20261004-50 → -59`, BE/FE in `b8ac544fe`, collaudo a video verde):
  `work-done/brief-db-permessi-tetto-area.md`. Restano: ritiro del parametro
  morto `p_area_schema_db` da `fn_resolve_livello_oggetto` (raccomandato:
  tenerlo finché un cantiere non tocca quella firma) e raggruppamento
  «Trasversali» delle aree (servirebbe una colonna su `aree_funzionali`, brief
  al team DB)
- **Il `codice` delle sei famiglie di documento di seed si perde al migrate**
  (DB, ereditata il 2026-09-24 dalla chiusura di
  `work-done/brief-be-ricerca-full-liste-residue.md`, §13.5): dal 24-09 il
  `codice` dell'operatore si modifica dal CRUD, ma il mirror del CSV
  `vendite.famiglie_documento` lo riscrive a ogni migrate, come già la
  `descrizione`. Una modifica dal CRUD dura fino al migrate successivo. Da
  decidere col team DB se il mirror debba smettere di riscrivere le colonne che
  l'operatore può cambiare
- **Righe di listino: la gamba dei compositi bundle non è provata sul DB**
  (BE, stessa origine, §13.3 g): la ricerca libera di `vendite.listini_righe`
  è una condizione sola sulla CTE `unione`, ma
  `vendite/tests/db/test_ricerca_liste_db` costruisce solo la riga standalone
  (la fixture di una BoM con prezzo bundle è pesante). Su quella gamba la
  ricerca non ha un rosso che la presidi
- **La matrice di `stato_lotto` in due sedi che dissentono** (BE + DB,
  ereditata il 2026-09-23 dalla chiusura di
  `work-done/brief-db-annullamento-chiude-la-vita.md`, §9.3): il BE ammette
  `COMPLETATO → ERRORE`, `vendite.fn_set_fatturazione_lotto_stato` no — e
  quella funzione è di fatto **morta**, il runner scrive `stato_lotto` con un
  `UPDATE` diretto (è per questo che la guardia su `COMPLETATO` sta su un
  trigger della colonna). Da decidere quale sia la sede unica della matrice e
  ritirare l'altra. Cantiere a sé
- **La porta dell'esito ancora aperta** (DB, stessa origine, §9.9): un
  documento marcato `ERRORE` su un lotto **già** `COMPLETATO` produce la
  contraddizione «COMPLETATO con documenti in errore» senza toccare
  `stato_lotto`, quindi la guardia del trigger non la vede. Oggi la sorveglia
  il presidio a catalogo `dbops.vw_lotti_chiusi_con_errori_da_guardare` (deve
  restare vuoto); chiuderla a DB è una decisione a sé, di Tid
- **`zeroerp_log` in CI non ha `USAGE` su `dbops`: ogni test Django lavora con
  `tx_id = uuid_nil`** (DB+CI, ereditata il 2026-09-19 dalla chiusura di
  `work-done/brief-db-privilegio-app-job-run-log.md`, §5). La sede del
  privilegio esiste — `scripts/sql/provision_dblink_log_channel.sql` — ma la CI
  non la esegue (il vecchio changeSet `90_end/20260205-42`, `context:
  disabled`, è stato ritirato il 2026-10-15), il bootstrap di `ci-validate.yaml` crea il ruolo e il
  DSN senza concedergli niente su `dbops`, e `90_end/20260905-38` gli dà
  `maintenance`, non `dbops`. Su dev il grant c'è, a mano (§11.9, stessa
  forma). Effetto: `fn_get_or_create_session_tx_id` ripiega su `uuid_nil`
  (progettato apposta, non fa fallire nulla), quindi ogni asserzione sul
  `tx_id` reale in CI è verde per sottrazione e l'audit non correla. Fatto
  datato: 16 114 righe `permission denied for schema dbops` nel log Postgres
  della corsa verde `35451924195`. Due strade, **decisione a Tid**: un passo
  in `ci-validate.yaml` che lancia `provision_dblink_log_channel.sql` dopo il
  bootstrap, oppure un changeSet `90_end` gemello di `20260905-38` per
  `dbops`. Tocca il workflow, condiviso BE/DB. In coda allo stesso brief due
  code minori: `maintenance.test_pgagent_log` con `zeroerp_app=r` a mano su
  dev e senza lettore (§3.3, `REVOKE` + pin nel pgTAP, o un lettore da
  trovare) e `check_db_role_access.sql` che esclude `maintenance` per intero
  (§3.4, da verificare)
- **La distinta del fondo fattura fuori lotto** (DB, ereditata il 2026-09-17
  dalla chiusura di `work-done/brief-db-distinta-numerata-sul-registro.md`,
  §4-bis.19): `fn_sync_contabili_fondo_fattura` passa `p_lotto_id = NULL` se la
  fattura non è in nessun lotto, e la distinta del fondo cade al **livello 3**
  di `fn_get_emittente_distinta` (l'emittente di chi agisce) invece che a
  quello della fattura — per l'admin globale in «tutti» è un
  `E_CONTABILE_EMITTENTE_OBBLIGATORIO` in mezzo alla pipeline. La strada è che
  la madre dei fondi passi `p_emittente_fiscale_id` dall'emittente della
  **fattura**. Da decidere con Tid, un changeSet
- **`runOnChange` + `dbms:` in `80_data`/`90_end`: la ri-esecuzione una-tantum**
  (DB, ereditata il 2026-09-17 dalla chiusura di
  `work-done/brief-db-distinta-numerata-sul-registro.md`, §9 riga del 17-09
  pomeriggio): in Liquibase 5.0.4 un `runOnChange` con un change `dbms:` viene
  ri-eseguito **una volta** all'update successivo alla prima esecuzione — il
  filtro ricalcola il checksum senza `Database` nello `Scope` e salta il
  change, quindi il checksum salvato non torna (`exectype = RERAN`, poi
  stabile). In CI cade nella **seconda** invocazione (`ci_apply`), **fuori
  ordine** rispetto a `80_data`: è così che `20260831-03` è morto dopo il
  merge di PR #1598 (corretto: cancello per nome, `237ea2939`). Sono 28
  changeSet in `80_data`/`90_end`, tolleranti tranne quel cancello. Da
  decidere: togliere `dbms:` dai 28 (checksum deterministico, niente
  ri-esecuzione) o accettare la ri-esecuzione e censire ogni `sqlCheck` con
  `HALT` sul **contenuto**; e riscrivere la nota del guardrail `runOnChange`
  in `ci-validate.yaml`, che nomina `runOnChange` come causa quando la causa è
  `runOnChange` **+ `dbms:`**. Cantiere `dbops`, non di dominio
- **La scala di `vendite_contabili_righe.importo`** (DB, **P-8**, ereditata il
  2026-09-18 dalla chiusura di `work-done/brief-db-distinta-ricerca-rate.md`,
  §4-bis.10): la colonna è `numeric` **senza scala** (`20260213-10`), quindi una
  riga con quattordici decimali — la sottrazione in virgola mobile di un client —
  entra com'è, e il guard di capienza la rifiuta su un importo che *era* lo
  spazio. Il FE arrotonda ai centesimi dal 17-09, ma la regola vale per
  **qualunque** client. Raccomandazione scritta nel brief: un
  `CHECK (importo = round(importo, 2))` che **rifiuta** (AGENTS.md: «non
  normalizzare silenziosamente»), non un typmod `numeric(18,2)` che arrotonda
  in silenzio; `fatture_scadenze.importo` resta `numeric(18,6)` come i totali di
  documento. Un changeSet `00_schema` con `expectedResult: 0` sulle righe che
  non passerebbero. ✅ **DECISA da Tid il 2026-09-18 sera: strada A, il
  `CHECK` che rifiuta.** Da domanda a lavoro del team DB (`pagamenti`,
  un changeSet); nessun impatto BE/FE — il FE arrotonda già ai centesimi
- **Su quale documento si può registrare un incasso** (DB, **Q-4**, ereditata
  il 2026-09-18 dallo stesso brief, registro del 18-09): Tid vuole nel picker
  delle rate «solo le definitive, inviate a SDI — ma faremo poi». È un
  predicato di **dominio** e la sede è **una**, a DB, letta dalla lista **e**
  dal guard della riga: oggi `trgfn_vendite_contabili_righe_guard_rata` non
  chiede lo stato del documento (la rata di una bozza si abbina) e il filtro
  `solo_numerate` di `GET /pagamenti/rate/` è presentazione, non cancello. Si
  apre con la **persistenza dell'esito SDI** (voce sotto), che è ciò che
  «inviata» significa; nessun changeSet chiesto prima. ✅ **DECISA da Tid il
  2026-09-18 sera: si aspetta SDI** («a breve farò lo sviluppo SDI») — niente
  passo intermedio «solo numerati» a DB; il filtro BE sulle bozze resta
  presentazione, e il buco (la rata di una bozza è abbinabile per vie diverse
  dal picker) è **dichiarato**, non dimenticato: si chiude nel cantiere SDI
  con la regola intera «definitiva e inviata», in una sede, letta da lista e
  guard. ⚠️ **Aggiornamento 2026-09-23 (Tid), che NON cambia la decisione**:
  `solo_numerate` era scritto nel **frontend** (nei `filterDefaults` del picker)
  e da quel giorno il suo default vive nel **backend**
  (`saldi_service.list_rate` / `list_rate_paginata`, `= True`; l'assenza del
  parametro significa «applica la regola»). ⭐ Resta **presentazione, non
  cancello** — il guard della riga non chiede ancora lo stato del documento e il
  buco dichiarato è intatto: cambia solo che la regola non dipende più dal client
  che si ricorda di mandarla. Regola generale in
  [api.md §«Un PERIMETRO non è un filtro»](../../dev/api.md)
- **«Riavvia» un servizio dall'interfaccia** (DB + deploy + BE, **decisione
  D1 di Tid**; ereditata il 2026-09-18 dalla chiusura di
  `work-done/analisi-riavvio-processi-da-interfaccia.md`): «Esegui ora» è in
  esercizio dal 15-09 e non aveva bisogno di sapere su quale macchina gira —
  un timer è un comando che parla col DB. `systemctl restart` di un servizio
  (oggi il solo `listen_permessi`) **sì**: senza un *host* nel modello
  il pulsante riavvia «un host a caso» alla seconda macchina, in silenzio.
  Cancello: **D1** — forma A (`ZEROERP_HOST` dichiarato in `env.sh`, `host`
  obbligatorio nella richiesta, claim del drenatore filtrato) o B (registro
  `dbops.host` + `abilita` per host); l'analisi raccomanda **A subito, con
  `host` obbligatorio dal primo giorno**. Poi D2…D8 (§7) e la sequenza §9:
  colonna sul claim, tipo `RIAVVIA_UNIT` (`attivo = false`), azione
  `unit_riavvia`, `sudoers` **reso** da `sveglie.json` in `install-timers.sh`,
  handler a lista senza shell, run **non** contato come segno di vita del
  processo riavviato (D6). Zero righe scritte al 18-09, per scelta. Sta anche
  fra le «Decisioni aperte» della mappa concentrica
- **Il Giornale eventi non è multi-emittente** (DB, **non urgente**, ereditata
  il 2026-09-19 dalla chiusura di `work-done/piano-be-fe-osservabilita-pallino-e-superfici.md`,
  §10 pezzo G): `vendite.giornale` è `multi_emittente = false` perché
  `script.vw_giornale_entita` non proietta l'emittente della riga — su «Tutti
  gli emittenti» la lista chiede di sceglierne uno (422), come `Fatture`. Per
  certificarla serve `emittente_soggetto_ruolo_id` nei **quattro rami** della
  vista (le tabelle lo hanno o lo raggiungono) + la colonna a catalogo. Il
  collaudo in-app dell'osservabilità (`work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md`,
  chiuso il 2026-10-06) lo dichiara al §3.15
- **Tendine del lookup generico senza `page_size`** (FE, residuo di
  `work-done/brief-db-registri-giornale-catalogo.md` §5.1): i siti che chiamano
  `lookupCodici(rel)` senza `page_size` ricevono la pagina di default (50) e la
  tendina si tronca in silenzio — da rivedere uno per uno, o da far passare da
  `useLookupCodici`
- **Registry runtime Python multi-dominio**: modello DB pronto, ma la mappa Python per tutti i domini non è completa
- **Builder XML SDI**: payload pronto, ma generazione file FatturaPA non ancora implementata. ⚠️ Sospeso per decisione (Tid, 2026-08-05); raccoglie anche `EsigibilitaIVA`, `DatiContratto` e le righe spezzate dal plafond (`vw_fattura_righe_esposte`, `PARTE_PLAFOND`) — dettagli in `work-done/fatturazione-roadmap.md` §9
- **Persistenza esito SDI**: `vendite.fatture_sdi` e `vendite.fatture_sdi_eventi` da popolare
- **Pratica di approvazione prezzo su revisione superata** (BE,
  `work-done/refactor-prezzi.md` §4.7, residuo differito dal 2026-06-01): dal
  2026-09-14 (`20260914-14`) riguarda anche i **preventivi** — la rev N+1
  ricopia `stato_approvazione_prezzo` e la pratica 1:1, e una riga `PENDING`
  può trovarsi con la pratica già chiusa sulla rev N. ⚠️ **Dal 2026-09-24 il
  debito morde prima**: un prezzo non autorizzato blocca già l'**emissione**
  (building block `script.fn_check_prezzi_autorizzati`, cinque documenti di
  vendita), non più la sola accettazione — la revisione con quella riga non si
  emette, e resta solo l'annullamento. ✅ **Deciso da Tid lo stesso giorno**
  (§10 di `work-done/brief-db-preventivi-congelamento-pricing.md`,
  `20260924-33…-37`, applicati il 24-09 con test verdi; collaudo a video
  passato il 2026-10-24, `work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md`):
  una revisione **non si crea** finché un
  prezzo è in attesa, quindi la riga in attesa ricopiata non può più nascere;
  approvato e rifiutato si ricopiano come prima. Resta del BE il ciclo di vita
  della pratica su una rev superata (il suo `meta` nomina la riga della rev N)
  ⚠️ **Dal 2026-10-08 anche sul preventivo annullato** (`work-done/brief-db-righe-e-componenti-debiti-residui.md`
  §4.4, §5): con le righe chiuse fuori bozza l'esito di una pratica su un preventivo annullato con una riga in
  attesa è respinto dal lock (`E_RIGA_DOC_NON_BOZZA`), e la pratica resta `APERTA` in coda. Debito dichiarato da
  Tid il 2026-10-09: si chiude con il resto del ciclo di vita della pratica
- **L'L3 dei componenti non esiste** (DB + BE, ereditata il 2026-10-09 dalla chiusura di
  `work-done/brief-db-righe-e-componenti-debiti-residui.md` §3): nessun verbo mette un componente in attesa
  né gli dà un esito, e non c'è il controllo L2. Dal `20261008-87`/`-88` uno spento in attesa si copia nella
  revisione senza marca: la nuova richiesta alla riaccensione è di quel ciclo. Un brief suo quando si costruisce
- **`user_update` nullable su nove tabelle senza audit** (DB, stessa origine, §2 e §4.6): `dbops.fk_index_policy`,
  `dbops.transaction_ids` e sette di `ui`. Il presidio `dbops/test-user-update-not-null-v1` le tiene a vista nel
  registro del debito; da decidere chi scrive la colonna

**Residui della roadmap fatturazione** (archiviata il 2026-09-12 in
`docs/it/dev/work-done/fatturazione-roadmap.md`, dove sta il *perché* di
ciascuna; qui solo la riga, perché un promemoria di stato lungo marcisce —
lezione della §Nota di metodo di quel file):

- **Esercizio fiscale come entità** (roadmap #3): zero occorrenze di `esercizio`/`anno_fiscale` in `migrations_v2` e nel backend; l'esercizio è l'anno solare derivato da `fatture.data`. Serve al primo **bilancio**, non al primo ciclo — la numerazione con reset annuale è coperta
- **Vista push** (roadmap #5): `vendite.commesse_push_log` non ha una UI di lista/ultimo run per sorgente; i contatori `created/updated/skipped/errors` esistono nel payload e nessuno li rende — l'operatore riceve un `push_log_id` in un toast e non ha modo di aprirlo
- **Alerting sui dati** (roadmap #6): la vitalità dei **processi** è coperta (sveglia, `dbops.processi`, digest) e dal 19-09 anche il **lotto fermo** (presidio a catalogo → digest e pallino) e la consultazione **a video** (`vendite/giornale`, «Giornale eventi»); manca ancora un **canale d'uscita** (email) per la query generica su `vendite.event_log` per severità/finestra. ⚠️ Non ha più una casa: `analisi-osservabilita-log.md` è **chiusa e archiviata** il 2026-09-19 (`work-done/`), e questa voce è uno dei residui dichiarati nel suo riquadro
- **Diagrammi di stato** (roadmap #8): zero `stateDiagram-v2` nel repo per lotto e task_run; la sostanza è già in prosa in `guide/fatturazione.md` — è trasposizione, non analisi
- **Preview di fatturazione del contratto** (roadmap #10): non esiste il punto in cui l'operatore veda *«su questa competenza fatturerà queste righe, per X»*; il dato lo produce `fn_list_contratti_da_pushare`. ⚠️ Non è `/contratti/<id>/righe-preview/`, che è la preview di **pricing**
