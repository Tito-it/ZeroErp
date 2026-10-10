# Brief DB — Dati fiscali e societari del soggetto: chi li scrive, e per quali nature

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10, su segnalazioni di Tid e su quanto
> trovato chiudendo `work-done/brief-db-character-n-spazi-di-riempimento.md`.
> **A chi:** team DB; poi BE/FE (§5).
> **Stato:** 📝 bozza, in attesa delle decisioni di Tid (§4). BE/FE attendono il DB.
>
> Tre difetti, sullo stesso oggetto: i dati fiscali e societari di un soggetto.
>
> | Parte | Difetto | Da dove |
> | --- | --- | --- |
> | **A** | «Cliente PA» e «Split payment» valgono per ogni natura, anche per un privato | segnalazione di Tid, 2026-10-10 |
> | **B** | In modifica i dati societari non si salvano: manca il verbo di scrittura | brief character-n §6.2, decisione di Tid (ex D-7) |
> | **C** | La forma giuridica non è legata alla natura del soggetto | collaudo R-2 del brief character-n: «la forma giuridica è vuota» |

## 1. Parte A — PA e split payment: quali nature li ammettono

### 1.1 Il difetto, sul modello

`anagrafiche.soggetti.cliente_pa` e `split_payment` (`character(1)`, NOT NULL, default `'N'`, CHECK
`'S'`/`'N'`) esistono su **ogni** soggetto, qualunque sia la natura. Nessuna regola dice per quali
nature hanno senso:

- in `config.tipi_soggetto_dettaglio` non c'è una colonna su PA o split. Le altre domande della
  natura ce l'hanno: `sesso_policy`, `dati_societari_policy`, `cf_obbligatorio`,
  `piva_obbligatoria`;
- nessun guard su `soggetti` lega i due flag alla natura;
- il drawer (`SoggettoDrawer.vue`) mostra la sezione «Dati fiscali» per **ogni** soggetto in
  modifica (`v-if="isEdit"`). Il BE (`_normalizza_flag_fiscali`) controlla solo che il valore sia
  `S`/`N`.

Quindi un privato può essere salvato come `cliente_pa = 'S'` o `split_payment = 'S'`. Lo split
cambia **chi versa l'IVA** in fattura (l'`EsigibilitaIVA`): l'errore è fiscale e non si vede.

⛔ **Nascondere la sezione nel frontend per le persone fisiche non chiude il difetto**: sarebbe una
regola di dominio scritta in Vue, e il DB continuerebbe ad accettare il valore da qualunque altro
chiamante. Il FE deve leggere la regola, non scriverla.

### 1.2 Le nature (contratto: seed `80_data/sql/config/tipi_soggetto_dettaglio.csv`)

| Natura | `tipo_soggetto_id` | `dati_societari_policy` | `sesso_policy` |
| --- | --- | --- | --- |
| PR — Persona Fisica - Privato | PF | NONE | REQUIRED |
| DI — Persona Fisica - Ditta Individuale | PF | OPTIONAL | OPTIONAL |
| SP — Società di Persone | PG | OPTIONAL | NONE |
| SC — Società di Capitali | PG | REQUIRED | NONE |
| ENC — Ente non Commerciale | ENC | OPTIONAL | NONE |

Nel seed non c'è una natura «Pubblica Amministrazione»: oggi una PA può essere solo un ENC (la
matrice delle forme dà all'ENC la forma «Ente pubblico»).

## 2. Parte B — Il verbo di scrittura dei dati societari

### 2.1 Il difetto, sul modello

I dati societari (forma giuridica, REA, capitale, socio unico, liquidazione, canale FE con PEC e
codice SDI, data di costituzione) **nascono** con il soggetto, dentro
`anagrafiche.fn_crea_soggetto_pg`, e poi **non si cambiano più** da nessuna parte. Nessuna funzione
del DB fa `UPDATE` di `anagrafiche.dati_societari`, a parte l'helper di fixture
`dbops.fn_pgtap_crea_soggetto_pg`. Lato BE `SOGGETTO_UPDATE_COLS` non ha quelle colonne.
`SoggettoDrawer` mostra il form modificabile anche in modifica, ma il ramo di modifica di
`handleSave` non mette `dati_societari` nel payload. L'operatore cambia canale, PEC o codice SDI,
legge «salvato», e alla riapertura trova i valori vecchi.

Sono dati che cambiano nella vita di un'azienda: trasloco della sede REA, aumento di capitale,
messa in liquidazione, cambio di PEC o di codice destinatario. Il codice destinatario va dritto
nello snapshot della fattura (`vendite.fn_snapshot_intestazione_fattura`): se non si può correggere,
la fattura elettronica parte verso un recapito vecchio.

✅ **Strada decisa da Tid il 2026-10-10**: un verbo di scrittura a DB, con BE e FE dietro (non il form
in sola lettura).

### 2.2 Che cosa dice oggi il DB (contratto, catalogo vivo di dbdev, 2026-10-10)

⚠️ La doc auto-gen di `dati_societari` è ferma a prima del `20261010-37`: mostra ancora
`uq_ds_codice_sdi`, `uq_ds_pec_fatt` e `destinatario_fe varchar(10) NOT NULL`. Quanto segue viene
dal catalogo.

- Una riga per soggetto (`uq_ds_soggetto`). Colonne scrivibili: `forma_giuridica_id` (nullable),
  `id_prov_iscri_rea` e `iscrizione_rea` (**NOT NULL**, `uq_ds_prov_cea`), `capitale_sociale`
  (**NOT NULL**), `socio_unico`, `liquidazione` (enum NOT NULL), `destinatario_fe` (`varchar(1)`
  nullable, `P`/`C`), `pec_fatturazione`, `codice_sdi` (`varchar(7)`), `data_costituzione`.
- Guard presenti: `…_guard_tipo_soggetto` (la natura ammette i dati societari),
  `…_guard_forma_giuridica` (solo il paese, §3), `…_a10_guard_canale_fe`, i due «parent attivo» su
  soggetto e forma giuridica, storico `z90` su UPDATE e DELETE.
- `zeroerp_app` ha `INSERT`, `UPDATE`, `DELETE` diretti sulla tabella.
- Sul soggetto, `trgfn_soggetti_guard_dati_societari_required` presidia la `dati_societari_policy`.

## 3. Parte C — La forma giuridica non è legata alla natura

### 3.1 Il difetto, sul modello

`config.forme_giuridiche_tipi_soggetto_dettaglio` dichiara quali forme ammette ogni natura (SC:
SRL, SRLS, SPA, SAPA, cooperativa, consorzio, impresa sociale; SP: SNC, SAS; DI: ditta individuale;
ENC: associazione, fondazione, ente pubblico, ONLUS). Ma **nessuno la fa rispettare in scrittura**:

- `trgfn_dati_societari_guard_forma_giuridica` controlla solo che il **paese** della forma sia quello
  del soggetto, non la matrice;
- la matrice la legge solo il **lookup** del form (`LookupRepository.list_forme_giuridiche`, filtro
  sul tipo e su `attivo`).

L'effetto a video è quello del collaudo: se la forma salvata non è fra quelle ammesse dalla natura,
il `Select` del drawer non la trova fra le opzioni e **la mostra vuota**. Il dato non è vuoto, è
illegale per la natura, e nessuno lo dice. Al salvataggio successivo l'operatore non saprebbe
nemmeno di doverla correggere.

Secondo buco, sulla stessa colonna: `forma_giuridica_id` è **nullable** anche quando la natura
dichiara i dati societari `REQUIRED`, e il form la considera obbligatoria (`validate()` di
`useDatiSocietariForm`). La regola «se c'è la riga dei dati societari, c'è la forma» sta solo nel
frontend.

### 3.2 Controesempio (fatto datato, dbdev, 2026-10-10)

Sulle 161 righe di `dati_societari`: 152 Società di Capitali con forma «Ditta individuale», 6
righe senza forma (fra cui «Azienda SC REQUIRED con dati»). Sono quasi certamente residui di
fixture, e non decidono niente: dicono solo che il DB le accetta. Vanno corrette o cancellate a mano
prima del guard (§4, C-3).

## 4. Decisioni attese da Tid

| # | Domanda | Proposta della sessione BE |
| --- | --- | --- |
| **A-1** | **Dove sta la regola PA/split.** | Due colonne su `config.tipi_soggetto_dettaglio`, sul modello delle altre domande della natura: `cliente_pa_ammesso boolean NOT NULL DEFAULT false` e `split_payment_ammesso boolean NOT NULL DEFAULT false`. Booleani e non `presenza_policy_enum`: i flag sono `S`/`N` NOT NULL, quindi «obbligatorio» non ha significato. «Non ammesso» vuol dire che il valore resta `N`. |
| **A-2** | **Quali nature li ammettono** (seed). | PR e DI: nessuno dei due. SP, SC: split sì (società controllate dalla PA o quotate), PA no. ENC: tutti e due. È una regola fiscale: **la decide Tid**, se serve col consulente. |
| **A-3** | **Il guard.** | Su `anagrafiche.soggetti` (BEFORE INSERT OR UPDATE OF `cliente_pa`, `split_payment`, `tipo_soggetto_dettaglio_id`): un flag a `S` su una natura che non lo ammette → codice nuovo `DATO_ERRATO` con `COLUMN` = il campo, e una frase che nomina natura e campo. Copre anche il cambio di natura. |
| **B-1** | **Il verbo.** | `anagrafiche.fn_scrivi_dati_societari(p_soggetto_id uuid, …)` che **crea o aggiorna** la riga. Crea, perché con policy `OPTIONAL` un soggetto può nascere senza dati societari e riceverli dopo. Nella prima riga `script.fn_guard_livello(…, 'anagrafiche', 'soggetti', 'TUTTO')` («una scrittura = un verbo»). Firma ancorata con `%TYPE` (§7e di `linee-guida-sql.md`), parametri nominati. |
| **B-2** | **Stato intero o parziale?** | Il form manda tutta la sezione: un verbo che riceve **lo stato intero** è il più semplice (`NULL` scrive `NULL` dove la colonna lo ammette). «Solo i campi passati» si distingue male da «passato NULL apposta». Decide il team DB, il BE si adegua. |
| **B-3** | **Le regole restano nei guard.** | Il verbo aggiunge solo il permesso e il «soggetto non trovato» (`E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`, esiste già). Forma giuridica, natura, canale FE e REA restano ai trigger. |
| **B-4** | **`fn_crea_soggetto_pg` chiama il verbo.** | Sì: la scrittura dei dati societari ha una sede sola (regola del 2). |
| **B-5** | **La scrittura diretta dell'app.** | Col verbo, all'app si tolgono `INSERT`/`UPDATE`/`DELETE` su `dati_societari`. Oggi scrivono solo `fn_crea_soggetto_pg` e l'helper pgTAP. |
| **B-6** | ❓ **REA e capitale obbligatori sempre.** | `id_prov_iscri_rea`, `iscrizione_rea` e `capitale_sociale` sono NOT NULL, e `fn_crea_soggetto_pg` li pretende tutti e tre (`E_ADMIN_VALIDAZIONE`). Ma la forma giuridica dichiara `capitale_sociale_policy = NONE` per DI, associazione, fondazione, ente pubblico e ONLUS, e `rea_policy = OPTIONAL` per le stesse (seed, letto il 2026-10-10). ⇒ **Un ente o una ditta individuale con dati societari oggi non si può creare**: il form nasconde il capitale, e dal 2026-10-10 non lo manda (`toPayload`, §5), quindi la creazione si ferma sempre sul capitale mancante. Proposta: le tre colonne nullable, la regola nel guard della forma, che legge le due policy (`REQUIRED` ⇒ presente, `NONE` ⇒ assente). |
| **B-7** | ❓ **Il canale FE è facoltativo o no?** | D-6 del brief character-n ha reso `destinatario_fe` **nullable** (decisione di Tid), e il form permette di lasciarlo vuoto. Ma `fn_crea_soggetto_pg` lo pretende ancora («Destinatario FE obbligatorio per dati societari», `E_ADMIN_VALIDAZIONE`, corpo vivo del 2026-10-10). Le due sedi dicono due cose diverse. Proposta: vale la colonna (nullable, decisione già presa), e il controllo esce dalla creazione. Con B-4 la creazione passa dal verbo e i controlli stanno nei guard, quindi la contraddizione sparisce insieme alla copia. |
| **C-1** | **La matrice si fa rispettare.** | Il guard della forma giuridica controlla anche che la forma sia nella matrice della natura del soggetto, valida e attiva → codice nuovo `DATO_ERRATO`, `COLUMN = forma_giuridica_id`. Un soggetto che cambia natura con una forma non ammessa dalla nuova va rifiutato allo stesso modo (guard su `soggetti`, `UPDATE OF tipo_soggetto_dettaglio_id`). |
| **C-2** | **La forma è obbligatoria?** | `forma_giuridica_id NOT NULL`: la riga dei dati societari senza forma non ha senso (REA e capitale dipendono dalla forma). La regola esce dal frontend. |
| **C-3** | **Le righe fuori regola** (§3.2). | Correggerle o cancellarle **a mano** prima del guard, come la provincia `TEST` del brief character-n. Se sono residui di fixture, anche l'helper che le scrive va corretto. |

## 5. Che cosa farà il BE/FE quando il DB è pronto

- **A, BE:** la query dei tipi soggetto che porta `tsd.sesso_policy` e `tsd.dati_societari_policy`
  (`soggetti_repository.py`) porta anche i due flag. Codice nuovo: `genera_error_policies` + ripiego.
- **A, FE:** `useSoggettoForm` espone `showClientePa` / `showSplitPayment` dalla natura, come
  `showSesso`. La sezione si mostra solo se resta almeno un campo; i `Select` si accendono da
  `campiErrati`. Via il `.trim()` in lettura su `split_payment`/`cliente_pa`: sono `character(1)` a
  lunghezza esatta, il padding non c'è (brief character-n §2.2).
- **B, BE:** `SoggettiService.update_soggetto` accetta la chiave `dati_societari` (contratto della
  PATCH validato nel service) e la passa al verbo con parametri nominati. Test Django sul DB vero
  per il percorso intero, compreso un errore col campo (`codice_sdi`).
- **B, FE:** il ramo di modifica di `SoggettoDrawer.handleSave` manda `dati_societari` con
  `useDatiSocietariForm().toPayload()`, come la creazione. `toPayload` (2026-10-10, con la sua spec)
  manda solo ciò che il form mostra: il recapito del canale non scelto, e REA e capitale quando la
  forma non li prevede, restano nel form ma non partono. Il form accende già i campi da
  `campiErrati`.
- **C, BE/FE:** nessuna regola nuova; i codici nuovi col loro ripiego. `forma_giuridica_id` si
  accende da `campiErrati`.
- ⛔ **Finché il DB non è pronto** BE/FE non toccano niente: niente `v-if` sulla natura scritto in Vue,
  niente `UPDATE` di `dati_societari` scritto nel repository.

## 6. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-10 | Aperto come `brief-db-regime-pa-split-per-natura` (sezione PA/split visibile su un privato). |
| 2026-10-10 | Su indicazione di Tid diventa il brief unico dei dati fiscali e societari: entra il verbo di scrittura (ex D-7 del brief character-n, deciso da Tid) e la forma giuridica non legata alla natura (dal collaudo R-2). Rinominato. In attesa delle decisioni del §4. |
| 2026-10-10 | Aggiunte B-6 (riscritta: con capitale `NONE` la creazione oggi fallisce sempre) e B-7 (il canale FE nullable per la colonna, obbligatorio per `fn_crea_soggetto_pg`), lette dal corpo vivo. Lato FE c'è già `toPayload()` (§5). |
