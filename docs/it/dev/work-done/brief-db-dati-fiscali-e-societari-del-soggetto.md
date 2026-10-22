# Brief DB — Dati fiscali e societari del soggetto: chi li scrive, e per quali nature

## ✅ Chiuso il 2026-10-14

Lato DB applicato e verde (§8.4), BE/FE scritti e verdi (§9), collaudo in-app di Tid superato il
2026-10-11. Decisione di Tid del 2026-10-14: si chiude, e i residui escono di qui.

| # | Chi | Che cosa | Dove |
| --- | --- | --- | --- |
| 1 | ✅ team DB | A, D, B, C: `20261010-85 … -99`, `20261011-01 … -04`, 12 codici, pgTAP | §8 |
| 2 | ✅ Tid | 6 righe senza forma corrette a mano, apply, test verdi | §8.4 |
| 3 | ✅ sessione BE/FE | A, B, C, D; lookup delle forme e natura in modifica corretti | §9 |
| 4 | ✅ Tid | collaudo in-app | §9.4 |
| 5 | ✅ team DB | `20261012-02`: soggetto NULL nel verbo → `E_PARAMETRO_INVALIDO` | §6 |
| 6 | ✅ sessione DB | archiviato in `work-done/`, residui sistemati (sotto) | — |

**Dove sono andati i residui:**

- `data_costituzione` in creazione (§9.5) → brief
  [brief-db-dati-societari-in-creazione](brief-db-dati-societari-in-creazione.md)
  (D34 del registro DB). Rileggendo la creazione è emerso anche il caso più grave: la ditta individuale
  perde **tutta** la sezione;
- cambio di natura con dati non congrui → già nel suo brief,
  [brief-db-cambio-natura-soggetto-conferma-e-pulizia](../work-in-progress/brief-db-cambio-natura-soggetto-conferma-e-pulizia.md);
- D-4 (`COOPERATIVA`), il censimento dei titoli IVA fuori regola (§8.2), `cliente_pa` di
  `SGT-0000121` (§8.1) e `fornitori.split_payment` (§7) → `.codex/PROJECT_CONTEXT.md`
  § «Aperto — Media priorità».

⚠️ `20261012-02` era dato «da applicare» al 2026-10-11: lo stato dell'apply non è stato riletto da
`databasechangelog` alla chiusura.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10, su segnalazioni di Tid e su quanto
> trovato chiudendo `work-done/brief-db-character-n-spazi-di-riempimento.md`.
> **A chi:** team DB; poi BE/FE (§5).
> **Stato:** ✅ chiuso e archiviato il 2026-10-14 (vedi in cima). Lato DB applicato e verde (2026-10-10, §8.4); ✅ BE/FE scritti e verdi (2026-10-10,
> §9), collaudati in-app da Tid il 2026-10-11. Storia: pronto per il team DB: decisioni di Tid prese il 2026-10-10 (§4), resta aperta solo
> D-4 (`COOPERATIVA`, Tid verifica; non blocca: senza righe di matrice). B-2, D-5, D-6 sono scelte
> tecniche del team DB. BE/FE attendono il DB.
>
> Quattro difetti, sullo stesso oggetto: i dati fiscali e societari di un soggetto.
>
> | Parte | Difetto | Da dove |
> | --- | --- | --- |
> | **A** | «Cliente PA» e «Split payment» valgono per ogni natura, anche per un privato | segnalazione di Tid, 2026-10-10 |
> | **B** | In modifica i dati societari non si salvano: manca il verbo di scrittura | brief character-n §6.2, decisione di Tid (ex D-7) |
> | **C** | La forma giuridica non è legata alla natura del soggetto | collaudo R-2 del brief character-n: «la forma giuridica è vuota» |
> | **D** | Un titolo IVA si registra su qualunque soggetto, anche su chi non può esserne titolare | ex `brief-db-regime-fiscale-per-natura-soggetto` (§3.2, §4.2), assorbito qui il 2026-10-10 |

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

⚠️ I due flag **non pesano allo stesso modo**, e il manuale di `soggetti` li accomuna a torto:

- `split_payment` lo legge `script.fn_esigibilita_iva` (EsigibilitaIVA `S`), attraverso
  `vendite.trgfn_fatture_righe_guard_normalize` e i riepiloghi: un valore sbagliato **è** una
  fattura sbagliata;
- `cliente_pa` oggi **non ha lettori** fuori dal CRUD del soggetto (né funzioni DB né servizi BE,
  verificato il 2026-10-10): un valore sbagliato è un dato sbagliato, che diventerà un errore
  quando nascerà il suo lettore (formato FatturaPA, CIG/CUP). La regola si mette **adesso** perché
  è una regola del modello, non perché oggi faccia danno.

Da correggere nello stesso giro il manuale `anagrafiche/manual/soggetti.md` (§«Regime fiscale
della controparte») e `soggetti_titoli_iva.md` (§«Due cose che sembrano IVA»): dicono che
**entrambi** i flag sono l'`EsigibilitaIVA`.

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

### 1.3 Una parte della regola è della natura, non della configurazione

«Una persona fisica, privato o ditta individuale, non è mai una PA e non è mai in scissione dei
pagamenti» (art. 17-ter DPR 633/1972) è un fatto di legge sulla natura **base**, non una scelta di
chi configura. Due booleani liberi per dettaglio la lascerebbero riaccendere da una riga di CSV.
Il modello ha già il presidio di questa forma:
`chk_tipi_soggetto_dettaglio_sesso_policy_natura` (`(tipo_soggetto_id = 'PF') = (sesso_policy <>
'NONE')`, in `90_end` perché i valori arrivano dal CSV). Qui serve il gemello, a senso unico:
`tipo_soggetto_id = 'PF'` ⇒ i due flag `ammesso` a `false` (A-4).

Il resto — quali PG e quali enti — **resta configurazione**, ed è una condizione **necessaria**,
non sufficiente: «la natura lo ammette» non vuol dire «il soggetto lo è». Per lo split sui PG non
può essere altrimenti: società controllate dalla PA e quotate nel FTSE MIB non si distinguono da
nessuna colonna, e il flag lo mette l'operatore. ⚠️ L'asse più fine per «è una PA» è la forma
giuridica (`ENTE_PUBBLICO` sotto `ENC`, accanto ad associazione, fondazione, ONLUS): un affinamento
sulla forma diventa possibile solo dopo la Parte C, e solo dove la forma c'è (sull'ENC i dati
societari sono `OPTIONAL`). Non entra in questo brief.

### 1.4 Soggetto senza natura

`anagrafiche.soggetti.tipo_soggetto_dettaglio_id` è **nullable**. I guard gemelli (sesso, CF/P.IVA)
in quel caso tacciono, ed è un limite dichiarato. Per un flag che cambia l'esigibilità della
fattura la stessa scelta va presa **esplicitamente** (A-5), non ereditata per copia.

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

## 3bis. Parte D — Chi può essere titolare di un titolo IVA

### 3bis.1 Il difetto, sul modello

`config.tipi_titolo_iva` (INTENTO, USO_INDUSTRIALE, AGEVOLATA_104, COOPERATIVA) e
`anagrafiche.soggetti_titoli_iva` non hanno nessun legame con la natura del soggetto: i guard
presidiano sovrapposizione, ambito, plafond e date, non **chi** può essere titolare. Una
dichiarazione d'intento su un privato entra nel risolutore (`vendite.fn_resolve_iva_riga`, stadio
B) e **cambia l'aliquota** delle sue righe. Ogni titolo ha invece un destinatario preciso:

- `INTENTO`: lo presenta un esportatore abituale, cioè un soggetto IVA, mai un privato;
- `USO_INDUSTRIALE`: presuppone un'attività d'impresa o agricola;
- `AGEVOLATA_104`: spetta a una persona fisica (il disabile, o il familiare che lo ha a carico);
- `COOPERATIVA`: ⚠️ **da chiarire prima del seed** (D-4). L'aliquota agevolata delle cooperative
  sociali riguarda in genere le prestazioni rese **da** loro, cioè l'emittente, non il cliente. Se
  il titolo sta sul cliente, va detto che cosa registra davvero chi lo scrive.

### 3bis.2 Che cosa si propone

- una matrice `config.tipi_titolo_iva_tipi_soggetto_dettaglio`, sullo stampo di
  `tipi_soggetto_dettaglio_tipi_indirizzo`, seed da CSV in `80_data`;
- un guard su `soggetti_titoli_iva` (INSERT, UPDATE OF `tipo_titolo_iva_id`, `soggetto_id`): il tipo
  deve essere ammesso per il dettaglio del soggetto;
- l'altro lato: un soggetto che **cambia dettaglio** non può lasciare titoli **vigenti** che il
  nuovo dettaglio non ammette (guard su `soggetti`, UPDATE OF `tipo_soggetto_dettaglio_id`);
- il terzo lato: una riga **tolta dalla matrice** mentre ci sono titoli vigenti che la usano.

Codice nuovo proposto: `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO` (classe `DATO_ERRATO`,
`campo` = `tipo_titolo_iva_id` dal lato titolo, `tipo_soggetto_dettaglio_id` dal lato soggetto).

Seed (D-2 e D-3 decisi, D-4 aperta):

| Titolo | Dettagli ammessi |
| --- | --- |
| `INTENTO` | `DI`, `SP`, `SC`, `ENC` |
| `USO_INDUSTRIALE` | `DI`, `SP`, `SC`, `ENC` |
| `AGEVOLATA_104` | `PR` (D-3) |
| `COOPERATIVA` | nessuna riga finché D-4 è aperta (ipotesi: `SC`, `ENC`) |

### 3bis.3 Tre trappole del modello che il disegno deve evitare

1. ⛔ **La RLS acceca il guard sul cambio di dettaglio.** `soggetti_titoli_iva` ha row security per
   emittente (`20260829-27`): un guard su `soggetti` che cerca i titoli vigenti del soggetto vede
   solo quelli del perimetro di chi scrive. Un operatore dell'emittente A cambia il dettaglio
   mentre l'emittente B ha un `INTENTO` vigente, e passa. La lettura va fatta da un helper
   `SECURITY DEFINER` stretto, che risponde solo «esiste / non esiste».
2. ⛔ **«Attivo» non è il criterio giusto.** `soggetti_titoli_iva` ha il blocco di disattivazione
   sui `soggetti_titoli_iva_movimenti`, e i movimenti non hanno una colonna `attivo`: un intento
   che ha consumato plafond **non si disattiva mai**. Con il criterio «titoli attivi» quel soggetto
   non potrebbe più cambiare dettaglio. E un titolo scaduto ma rimasto `attivo = true` bloccherebbe
   senza motivo. Il criterio proposto è la **validità**: titolo `attivo` **e** `validita &&
   daterange(current_date, NULL)`. Si esce chiudendo `valido_al`, che è anche la cosa vera da fare
   (D-5).
3. ⚠️ **La matrice viene da un CSV.** Un guard che impedisce di togliere una riga in uso ferma il
   mirror di `80_data` su un DB che ha titoli: va disegnato insieme al modo in cui la riga si
   ritira (`attivo = false` nel CSV, non DELETE), e il guard scatta su quella transizione.

⚠️ **Matrice senza righe per un dettaglio**: la proposta è il **rifiuto** (nessuna riga = nessun
titolo ammesso), e non il ripiego permissivo di `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`. Là
il ripiego è innocuo, qui un titolo cambia l'aliquota. I dettagli sono per paese (`stato_iso2`): un
dettaglio estero che nasce domani non deve nascere libero. Stesso discorso per il soggetto senza
dettaglio (A-5).

### 3bis.4 Le righe che già violano

Prima dei guard si **censiscono** i titoli vigenti non ammessi. Non si correggono d'ufficio: cosa
farne lo decide Tid, guardandoli (come C-3).

### 3bis.5 pgTAP (A e D)

- `PR` con `cliente_pa = 'S'` → rifiuto, `campo = cliente_pa`; `DI` con `split_payment = 'S'` →
  rifiuto, `campo = split_payment`;
- `SC` con split → accettato; `SC` con split che passa a `PR` → rifiuto;
- CSV con `cliente_pa_ammesso = true` su un dettaglio `PF` → il CHECK di A-4 lo rifiuta;
- soggetto senza dettaglio con un flag a `S` → rifiuto (A-5); con un titolo IVA → rifiuto (D-1);
- `PR` con `INTENTO` → rifiuto; `PR` con `AGEVOLATA_104` → accettato;
- soggetto con `INTENTO` vigente che passa a `PR` → rifiuto; con `INTENTO` **scaduto** → accettato;
- soggetto con `INTENTO` vigente **con movimenti** che passa a `PR` → rifiuto finché non si chiude
  `valido_al`, poi accettato;
- **due emittenti sotto RLS**: l'operatore di A cambia il dettaglio di un soggetto con titolo
  vigente presso B → rifiuto;
- riga di matrice ritirata con titoli vigenti → rifiuto; dettaglio senza righe di matrice → rifiuto.

## 4. Decisioni attese da Tid

| # | Domanda | Proposta della sessione BE |
| --- | --- | --- |
| **A-1** | **Dove sta la regola PA/split.** | Due colonne su `config.tipi_soggetto_dettaglio`, sul modello delle altre domande della natura: `cliente_pa_ammesso boolean NOT NULL DEFAULT false` e `split_payment_ammesso boolean NOT NULL DEFAULT false`. Booleani e non `presenza_policy_enum`: i flag sono `S`/`N` NOT NULL, quindi «obbligatorio» non ha significato. «Non ammesso» vuol dire che il valore resta `N`. |
| **A-2** | **Quali nature li ammettono** (seed). | PR e DI: nessuno dei due (lo impone A-4). SP, SC: split sì (società controllate dalla PA o quotate), PA no. ENC: tutti e due. ⚠️ Il «PA no» su SC va confermato: le controllate sono in **split** (art. 17-ter c. 1-bis) ma ricevono fatture B2B, non FatturaPA; restano fuori gli enti dell'elenco ISTAT S13 costituiti in forma societaria, che sono PA. ✅ **Deciso da Tid il 2026-10-10**: SP e SC split sì, PA no; ENC tutti e due; un ente S13 in forma di società si censisce come ENC con forma «Ente pubblico». |
| **A-3** | **Il guard.** | Su `anagrafiche.soggetti` (BEFORE INSERT OR UPDATE OF `cliente_pa`, `split_payment`, `tipo_soggetto_dettaglio_id`): un flag a `S` su una natura che non lo ammette → codice nuovo di classe `DATO_ERRATO` (✏️ scritti **due**, `E_CLIENTE_PA_NON_AMMESSO` e `E_SPLIT_PAYMENT_NON_AMMESSO`, §8.1) con `campo` = il flag, e una frase che nomina natura e campo. Copre anche il cambio di natura: chi cambia natura porta il flag a `N` nella stessa scrittura, il DB non lo azzera da sé. |
| **A-4** | **Il CHECK sulla natura base** (§1.3). | `CHECK (tipo_soggetto_id <> 'PF' OR (NOT cliente_pa_ammesso AND NOT split_payment_ammesso))` su `config.tipi_soggetto_dettaglio`, in `90_end` come il gemello del sesso. La legge sulla persona fisica non dipende dal CSV. |
| **A-5** | **Soggetto senza natura** (§1.4). | ✅ **Deciso da Tid il 2026-10-10: rifiuto** di un flag a `S` quando `tipo_soggetto_dettaglio_id` è NULL. Un flag che cambia l'esigibilità non si accende su un soggetto di cui non si sa che cosa sia. Diverge dal limite dichiarato dei guard sesso e CF/P.IVA, e va scritto nel commento del guard. Stessa scelta per i titoli (D-1). |
| **A-6** | **Legame fra i due flag.** | ✅ **Deciso da Tid il 2026-10-10: nessun vincolo** `cliente_pa ⇒ split_payment`. Verso la PA ci sono operazioni escluse dallo split, ma l'esclusione dipende dall'operazione, non dal cliente: se servirà, sarà una regola di riga con un brief suo. |
| **B-1** | **Il verbo.** | `anagrafiche.fn_scrivi_dati_societari(p_soggetto_id uuid, …)` che **crea o aggiorna** la riga. Crea, perché con policy `OPTIONAL` un soggetto può nascere senza dati societari e riceverli dopo. Nella prima riga `script.fn_guard_livello(…, 'anagrafiche', 'soggetti', 'TUTTO')` («una scrittura = un verbo»). Firma ancorata con `%TYPE` (§7e di `linee-guida-sql.md`), parametri nominati. |
| **B-2** | **Stato intero o parziale?** | Il form manda tutta la sezione: un verbo che riceve **lo stato intero** è il più semplice (`NULL` scrive `NULL` dove la colonna lo ammette). «Solo i campi passati» si distingue male da «passato NULL apposta». Decide il team DB, il BE si adegua. |
| **B-3** | **Le regole restano nei guard.** | Il verbo aggiunge solo il permesso e il «soggetto non trovato» (`E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`, esiste già). Forma giuridica, natura, canale FE e REA restano ai trigger. |
| **B-4** | **`fn_crea_soggetto_pg` chiama il verbo.** | Sì: la scrittura dei dati societari ha una sede sola (regola del 2). |
| **B-5** | **La scrittura diretta dell'app.** | Col verbo, all'app si tolgono `INSERT`/`UPDATE`/`DELETE` su `dati_societari`. Oggi scrivono solo `fn_crea_soggetto_pg` e l'helper pgTAP. |
| **B-6** | **REA e capitale obbligatori sempre.** | `id_prov_iscri_rea`, `iscrizione_rea` e `capitale_sociale` sono NOT NULL, e `fn_crea_soggetto_pg` li pretende tutti e tre (`E_ADMIN_VALIDAZIONE`). Ma la forma giuridica dichiara `capitale_sociale_policy = NONE` per DI, associazione, fondazione, ente pubblico e ONLUS, e `rea_policy = OPTIONAL` per le stesse (seed, letto il 2026-10-10). ⇒ **Un ente o una ditta individuale con dati societari oggi non si può creare**: il form nasconde il capitale, e dal 2026-10-10 non lo manda (`toPayload`, §5), quindi la creazione si ferma sempre sul capitale mancante. ✅ **Deciso da Tid il 2026-10-10**: le tre colonne nullable, la regola nel guard della forma, che legge le due policy (`REQUIRED` ⇒ presente, `NONE` ⇒ assente). ⚠️ Per il team DB: provincia e numero REA sono una coppia (o tutti e due o nessuno, CHECK di tabella); `uq_ds_prov_cea` con i NULL non collide più, ed è il comportamento voluto. |
| **B-7** | **Il canale FE è facoltativo o no?** | D-6 del brief character-n ha reso `destinatario_fe` **nullable** (decisione di Tid), e il form permette di lasciarlo vuoto. Ma `fn_crea_soggetto_pg` lo pretende ancora («Destinatario FE obbligatorio per dati societari», `E_ADMIN_VALIDAZIONE`, corpo vivo del 2026-10-10). Le due sedi dicono due cose diverse. ✅ **Deciso da Tid il 2026-10-10: vale la colonna** (facoltativo), e il controllo esce dalla creazione. Con B-4 la creazione passa dal verbo e i controlli stanno nei guard, quindi la contraddizione sparisce insieme alla copia. |
| **C-1** | **La matrice si fa rispettare.** | Il guard della forma giuridica controlla anche che la forma sia nella matrice della natura del soggetto, valida e attiva → codice nuovo di classe `DATO_ERRATO`, `campo = forma_giuridica_id`. Un soggetto che cambia natura con una forma non ammessa dalla nuova va rifiutato allo stesso modo (guard su `soggetti`, `UPDATE OF tipo_soggetto_dettaglio_id`). |
| **C-2** | **La forma è obbligatoria?** | ✅ **Deciso da Tid il 2026-10-10**: `forma_giuridica_id NOT NULL`. La riga dei dati societari senza forma non ha senso (REA e capitale dipendono dalla forma, B-6), e la regola esce dal frontend. ⚠️ Per il team DB: `fn_crea_soggetto_pg` e l'helper `dbops.fn_pgtap_crea_soggetto_pg` devono passare una forma ammessa dalla natura (C-1); i pgTAP che li chiamano (28 file al 2026-10-10) vanno censiti. |
| **C-3** | **Le righe fuori regola** (§3.2, §3bis.4). | ✅ **Deciso da Tid il 2026-10-10**: il team DB prepara le query di censimento (forme, flag A, titoli D) e le mostra a Tid, che decide riga per riga; niente changeSet di bonifica. Correggerle o cancellarle **a mano** prima del guard, come la provincia `TEST` del brief character-n. Se sono residui di fixture, anche l'helper che le scrive va corretto. |
| **D-1** | **Matrice senza righe, soggetto senza dettaglio** (§3bis.3). | **Rifiuto** in entrambi i casi (soggetto senza dettaglio: ✅ deciso da Tid con A-5): nessuna riga = nessun titolo ammesso. Dichiarato nel commento del guard. |
| **D-2** | **Seed della matrice** (§3bis.2). | ✅ **Deciso da Tid il 2026-10-10**: INTENTO e USO_INDUSTRIALE su DI, SP, SC, ENC (chiunque abbia partita IVA); AGEVOLATA_104 su PR (D-3); COOPERATIVA in attesa di D-4. |
| **D-3** | **`AGEVOLATA_104` sulla ditta individuale.** | ✅ **Deciso da Tid il 2026-10-10: solo `PR`.** L'agevolazione riguarda acquisti per uso personale: si fattura alla persona come privato, non all'impresa. |
| **D-4** | ❓ **Che cosa registra `COOPERATIVA`.** | Il titolo sta sul cliente, ma l'aliquota agevolata delle cooperative sociali riguarda di solito le prestazioni rese **dalla** cooperativa. Va chiarito il caso d'uso prima del seed: se il titolare non è il cliente, il titolo è nella tabella sbagliata. ⏳ **2026-10-10: Tid lo verifica.** Intanto `COOPERATIVA` resta **senza righe di matrice**: con D-1 non è ammesso su nessun soggetto; i titoli `COOPERATIVA` vigenti entrano nel censimento (§3bis.4). |
| **D-5** | **Criterio «vigente»** (§3bis.3 punto 2). | `attivo AND validita && daterange(current_date, NULL)`, non il solo `attivo`: un titolo con movimenti non si disattiva mai. |
| **D-6** | **Ritiro di una riga di matrice** (§3bis.3 punto 3). | Ritiro con `attivo = false` nel CSV, mai DELETE; il guard scatta sulla transizione `true → false` se esistono titoli vigenti, letti da DEFINER. |

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
- **D, BE:** il lookup dei tipi titolo si filtra per il dettaglio del soggetto (endpoint e parametro
  li decide il BE): è solo comodità, la regola resta nel guard. Codice nuovo con policy e ripiego.
- **D, FE:** la sezione «Titoli IVA» del drawer resta visibile anche sul privato (`AGEVOLATA_104` è
  suo); il `Select` del tipo legge il lookup filtrato.
- ⛔ **Finché il DB non è pronto** BE/FE non toccano niente: niente `v-if` sulla natura scritto in Vue,
  niente `UPDATE` di `dati_societari` scritto nel repository.

## 6. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-10 | Aperto come `brief-db-regime-pa-split-per-natura` (sezione PA/split visibile su un privato). |
| 2026-10-10 | Su indicazione di Tid diventa il brief unico dei dati fiscali e societari: entra il verbo di scrittura (ex D-7 del brief character-n, deciso da Tid) e la forma giuridica non legata alla natura (dal collaudo R-2). Rinominato. In attesa delle decisioni del §4. |
| 2026-10-10 | Aggiunte B-6 (riscritta: con capitale `NONE` la creazione oggi fallisce sempre) e B-7 (il canale FE nullable per la colonna, obbligatorio per `fn_crea_soggetto_pg`), lette dal corpo vivo. Lato FE c'è già `toPayload()` (§5). |
| 2026-10-10 | Analisi critica (sessione DB). Assorbito `brief-db-regime-fiscale-per-natura-soggetto` (stesso difetto A, proposte divergenti su SC e sul codice): entra la **Parte D** (titoli IVA), corretta su RLS, criterio «vigente» e matrice senza righe. A: `cliente_pa` oggi senza lettori (§1.1), CHECK sulla natura base (A-4), soggetto senza natura (A-5), «PA no» su SC motivato (A-2). Verificato che nessun changeset né commit successivo tocca il tema. |
| 2026-10-10 | Decisioni di Tid: A-2 (SP/SC split, PA solo ENC), A-5/D-1 (senza natura = rifiuto), A-6 (nessun legame PA ⇒ split), D-2, D-3 (104 solo PR), B-6 (REA/capitale nullable + guard della forma), B-7 (canale FE facoltativo), C-2 (forma NOT NULL), C-3 (censimento, decide Tid). D-4 aperta. |
| 2026-10-10 | Sviluppo DB (§8): A, D, B, C scritte e provate sullo scratch (`20261010-85…-99`, `20261011-01…-04`, 12 codici, 3 pgTAP nuovi, 9 adattati). Decisioni di Tid durante lo sviluppo: numerazione, B-5 (solo il verbo scrive, **senza** guard di livello), C-3 (le 6 righe senza forma le corregge Tid). Apply di Tid fino al `-87`; fermo, come previsto, sul `20261011-03`. |
| 2026-10-10 | Tid: corrette a mano le 6 righe senza forma, migrate completo (`20261011-03`, `-04`), test verdi. Lato DB chiuso; restano BE/FE e D-4. |
| 2026-10-10 | Sviluppo BE/FE (§9): A, B, C, D. Trovati due difetti fuori dal perimetro del brief e corretti: il lookup delle forme falliva sempre (colonna inesistente, §9.2) e la natura offerta in modifica non arrivava mai al DB (§9.3). |
| 2026-10-11 | Collaudo in-app di Tid: superato. |
| 2026-10-11 | CI rossa sul rubinetto degli accumulatori (`scripts/codici-errore-baseline.sh`): `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` aveva acquistato la famiglia PARAMETRO, perché il verbo `20261010-99` rifiutava `p_soggetto_id IS NULL OR NOT EXISTS` con un solo codice. Un soggetto non passato è un chiamante rotto, non un 404. `20261012-02`: NULL → `E_PARAMETRO_INVALIDO`, inesistente → `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` come prima; COMMENT con la firma in `%TYPE`. pgTAP `test-fn-scrivi-dati-societari-v1` con l'8-bis (plan 23), rosso sul corpo vecchio per il motivo giusto. Prova sullo scratch, SQL estratto: 22/23, rosso solo il 22 (da owner per costruzione); fotografia delle famiglie col changeSet dentro: nessun accumulo. Baseline `db/baseline-codici-errore-famiglie.tsv` stretta da quella fotografia (gli stessi 1 ristretto e 4 rientrati della CI, più i codici nati dopo con una sola famiglia). BE invariato: nessun chiamante passa NULL. ⏳ Da applicare (Tid). |
| 2026-10-14 | Chiuso su decisione di Tid. `data_costituzione` in creazione va in `brief-db-dati-societari-in-creazione` (D34), che prende anche la ditta individuale, che in creazione perde tutta la sezione. D-4, censimento dei titoli, `SGT-0000121` e `fornitori.split_payment` vanno in PROJECT_CONTEXT. Archiviato in `work-done/`. |

## 7. Fuori perimetro, da verificare

`anagrafiche.fornitori.split_payment` (`boolean`, **nullable**, scritto dal BE come
`bools=(…)`) non ha lettori nel DB oltre a `vw_fornitori_dettaglio` (verificato il 2026-10-10). Sul
lato passivo la scissione dipende da chi **compra**, cioè dall'emittente, non dal fornitore: il flag
potrebbe essere nella sede sbagliata, oltre che senza regola sulla natura. È un difetto diverso da
A, e se confermato va in un **brief suo**.

## 8. Sviluppo DB (sessione DB, dal 2026-10-10)

Numerazione decisa da Tid: in sequenza da `20261010-85`; dopo il `-99` si passa a `20261011-01`.
⛔ Niente è applicato: apply e corsa pgTAP restano di Tid.

### 8.1 Parte A — scritta e provata, da applicare

| changeSet / file | Cosa |
| --- | --- |
| `00_schema/config/20261010-85-alter-tipi-soggetto-dettaglio-add-regime-pa-ammesso` | colonne `cliente_pa_ammesso`, `split_payment_ammesso` (`boolean NOT NULL DEFAULT false`) |
| `20_code/anagrafiche/20261010-86-create-trgfn-soggetti-guard-regime-pa` | guard `trgfn_soggetti_guard_regime_pa`, trigger `trg_soggetti_a10_guard_regime_pa_ins_upd` (BEFORE INSERT OR UPDATE OF `cliente_pa`, `split_payment`, `tipo_soggetto_dettaglio_id`) |
| `90_end/20261010-87-check-tipi-soggetto-dettaglio-regime-pa-natura` | CHECK `chk_tipi_soggetto_dettaglio_regime_pa_natura` (A-4) |
| `80_data/sql/config/tipi_soggetto_dettaglio.csv` + mirror `20250717-12` | i valori di A-2 (due colonne nuove nel mirror, `BOOLEAN`) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_CLIENTE_PA_NON_AMMESSO`, `E_SPLIT_PAYMENT_NON_AMMESSO`, `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` (id 1254-1256) |
| `db/pgtap/anagrafiche/test-soggetti-regime-pa-v1.sql` | nuovo, plan 15 |
| `db/pgtap/anagrafiche/test-soggetti-split-payment-cliente-pa.sql` | fixture: un ente (`ENC`) invece di un soggetto senza natura, che il guard ora rifiuta |
| `db/pgtap/vendite/test-fatture-righe-esigibilita-split.sql` | fixture: solo billing account con un cliente la cui natura ammette lo split (il primo per id, su dbdev, era di un privato) |
| manuali `soggetti`, `tipi_soggetto_dettaglio`, `soggetti_titoli_iva` | la regola per natura; `cliente_pa` non è l'`EsigibilitaIVA` |

**Una scelta presa scrivendo (A-3).** Due codici invece di `E_REGIME_PA_NON_AMMESSO`: il flag
sbagliato lo dice il **codice**. Con un codice solo, il flag sarebbe finito nel `VARIADIC` come
etichetta italiana («Cliente PA»), che non si traduce. Il codice «senza natura» ha una frase chiusa
e lo riusa la Parte D.

**Prova pre-apply** (scratch `zeroerp_ci`, owner `zeroerp`, transazione annullata). L'SQL è
estratto dagli YAML, e i due mirror (`20250717-12`, `20260614-08`) sono resi offline con
`updateSQL`, non riscritti:

| File | Esito |
| --- | --- |
| `anagrafiche/test-soggetti-regime-pa-v1` | 15/15 |
| `anagrafiche/test-soggetti-split-payment-cliente-pa` | 5/5 |
| `anagrafiche/test-soggetti-sesso-policy-v1` (fratello sulla stessa tabella) | 20/20 |
| mutazione: estratto **senza** il `-86` | 9 rossi, tutti sui casi del guard |
| `vendite/test-fatture-righe-esigibilita-split` | rosso in fixture **come la versione di HEAD** (scratch senza dati: `ERRORE_FIXTURE` già in `baseline-rossi-ci.tsv`/`-scratch.tsv`). Su dbdev lo misura Tid |
| `plpgsql_check_function` sul guard | nessun errore |
| `sqlCheck` delle preCondition, su `zeroerp_ci` e dbdev | tutte `0` come atteso |

Non coperto dalla prova: RLS come app, dati di dbdev, presidi trasversali.

**Censimento (fatto datato, dbdev, 2026-10-10, C-3).** Un solo soggetto viola la Parte A:
`SGT-0000121` (Titini Michele Carlo, PR) con `cliente_pa = 'S'`, cioè il caso della segnalazione.
Il guard **non** blocca l'apply, perché giudica solo chi scrive. Ma qualunque modifica futura di
quel soggetto che tocchi i flag o la natura verrà rifiutata finché `cliente_pa` non torna a `N`.
⏳ Decide Tid: riportarlo a `N` a mano.

**Ricadute BE/FE**: invariate (§5, voce A). I codici sono tre e non uno: `genera_error_policies`
e ripiego per tutti e tre.

### 8.2 Parte D — scritta e provata, da applicare

| changeSet / file | Cosa |
| --- | --- |
| `00_schema/config/20261010-88-create-tipi-titolo-iva-tipi-soggetto-dettaglio` | la matrice: chiave (tipo, natura), `attivo`, audit, `tx_id`. Niente validità né storico (stampo: la matrice delle forme) |
| `80_data/changelog/20261010-89-upsert-tipi-titolo-iva-tipi-soggetto-dettaglio` + CSV | il seed di D-2/D-3 (9 righe); `COOPERATIVA` senza righe (D-4) |
| `20_code/anagrafiche/20261010-90-create-fn-titolo-iva-ammesso-e-vigente` | i due predicati condivisi: `fn_titolo_iva_ammesso` (STABLE, nessuna riga = false) e `fn_titolo_iva_vigente` (IMMUTABLE, sui valori, con «oggi» passato da chi chiama) |
| `20_code/anagrafiche/20261010-91-create-fn-titoli-iva-vigenti-lettori-definer` | i due lettori `SECURITY DEFINER` sopra la RLS: `fn_titolo_iva_non_ammesso_del_soggetto`, `fn_titolo_iva_vigente_su_natura_esiste` |
| `20_code/anagrafiche/20261010-92-create-trgfn-soggetti-titoli-iva-guard-tipo-soggetto` | guard sul titolo (BEFORE INSERT OR UPDATE OF `tipo_titolo_iva_id`, `soggetto_id`, `attivo`, `valido_al`; giudica solo un titolo vigente) |
| `20_code/anagrafiche/20261010-93-create-trgfn-soggetti-guard-titoli-iva-ammessi` | guard sul cambio di natura (BEFORE UPDATE OF `tipo_soggetto_dettaglio_id`) |
| `20_code/config/20261010-94-create-trgfn-tipi-titolo-iva-tsd-guard-ritiro` | guard sul ritiro di una riga di matrice (AFTER UPDATE OR DELETE; il mirror che riscrive la stessa riga tace) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO` (DATO_ERRATO), `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI` e `E_TITOLO_IVA_AMMISSIONE_IN_USO` (CONFLITTO_STATO), id 1257-1259 |
| `db/pgtap/anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql` | nuovo, plan 21 |
| `test-soggetti-titoli-iva`, `test-consuma-plafond-titolo-iva-righe-v1` | il «tipo senza plafond» della fixture passa da `AGEVOLATA_104` a `USO_INDUSTRIALE`. Sul cliente `SC` l'agevolazione sarebbe rifiutata, e i rifiuti attesi dal guard di coerenza (`P0001`) passerebbero per il motivo sbagliato |
| `vendite/test-fn-resolve-iva-riga` | il soggetto della fixture deve avere una natura; dentro la transazione la sua natura ammette i quattro tipi che il test mette sullo stesso soggetto (misura il risolutore, non la matrice) |
| manuali `soggetti_titoli_iva`, `config/manual/tipi_titolo_iva_tipi_soggetto_dettaglio` (nuovo) | la regola per natura e i suoi tre lati |

**Scelte prese scrivendo:**
- tre codici invece di uno. Il cambio di natura e il ritiro di matrice sono **conflitti di
  stato**, non dati sbagliati: la natura nuova può essere giusta, è il titolo in vigore che non lo
  consente;
- la natura tolta (NULL) a chi ha titoli vigenti riusa `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO`;
- un titolo che **comincia domani** è vigente: è già stato presentato;
- `valido_dal` resta fuori dall'aggancio del guard: anticiparlo non cambia se il titolo arriva a oggi.

**Prova pre-apply** (scratch `zeroerp_ci`, owner, transazione annullata, estratto A+D con i tre
mirror resi offline):

| File | Esito |
| --- | --- |
| `test-soggetti-titoli-iva-tipo-soggetto-v1` | 20/21. ⚠️ Il **14** (gemello RLS: «per l'altro operatore il titolo è invisibile») è **rosso da owner per costruzione** e verde come app. Con `FORCE ROW LEVEL SECURITY` il 14 diventa verde ma cade il 15, perché sullo scratch anche il lettore `DEFINER` ha lo stesso proprietario e subisce la policy. Il verdetto sui due insieme lo dà solo la corsa come app di Tid |
| mutazioni: senza `-92` / `-93` / `-94` | 8 / 4 / 2 rossi, sui casi di quel guard (più il 14 da owner, e il 9 a cascata senza `-92`) |
| fuso ostile (`PGTZ` Kiritimati, Pago Pago) | come sopra, stabile |
| `test-soggetti-titoli-iva` 23/23, `-due-emittenti` 5/5, `test-consuma-plafond-…` 22/22, `test-stiva-movimenti-annullo-v1` 12/12, `test-reset-fattura-plafond-consumato-v1` 11/11, `test-dati-societari-policy` 13/13, `regime-pa` 15/15, `sesso` 20/20, `split-payment` 5/5 | verdi, uguali a prima |
| `vendite/test-fn-resolve-iva-riga`, `vendite/test-fatture-righe-esigibilita-split` | rossi in fixture **uguali alla versione di HEAD** (scratch senza dati). Su dbdev li misura Tid |
| presidi trasversali: `riferimenti-morti`, `security-definer-search-path`, `storico-scope-policy`, `codici-errore-valore-atteso`, `catalogo-messaggi-errore-completo`, `policy-funzioni-cost`, `sec-functions-owner-migratore-passa` | verdi prima e dopo |
| `plpgsql_check` sui quattro guard | zero errori |
| `sqlCheck` delle preCondition, in sequenza | tutte come atteso; su dbdev nessun oggetto nuovo esiste |

**⏳ Censimento dei titoli (C-3): lo deve lanciare Tid come owner.** Come app la RLS lascia vedere
zero titoli, quindi questa sessione non può contarli. Prima dell'apply va guardato che cosa
diventerebbe «fuori regola»: il guard non blocca l'apply, ma rifiuterà la prossima modifica di
quei titoli o del loro soggetto.

```sql
SELECT t.id, s.codice, tt.codice_interno AS titolo, tsd.codice_interno AS natura,
       t.emittente_fiscale_id, t.valido_dal, t.valido_al
  FROM anagrafiche.soggetti_titoli_iva t
  JOIN anagrafiche.soggetti s       ON s.id  = t.soggetto_id
  JOIN config.tipi_titolo_iva tt    ON tt.id = t.tipo_titolo_iva_id
  LEFT JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
 WHERE t.attivo
   AND (t.valido_al IS NULL OR t.valido_al >= script.fn_giorno_operativo(now()))
   AND (tsd.codice_interno IS NULL
        OR NOT (   (tt.codice_interno IN ('INTENTO', 'USO_INDUSTRIALE') AND tsd.codice_interno IN ('DI', 'SP', 'SC', 'ENC'))
                OR (tt.codice_interno = 'AGEVOLATA_104' AND tsd.codice_interno = 'PR')));
```

**Ricadute BE/FE**: §5, voce D. I codici nuovi sono tre: policy generata e ripiego per tutti.

### 8.3 Parti B e C — scritte e provate, da applicare

**Decisioni prese durante lo sviluppo** (Tid, 2026-10-10):
- **B-5**: solo il verbo scrive `dati_societari`, quindi l'app perde `INSERT`/`UPDATE`/`DELETE`.
  ✏️ Ma il verbo **non** ha `script.fn_guard_livello`. L'operatore pgTAP di default è `BLOCCATO`
  su `anagrafiche.soggetti` (dbdev e scratch), e con il guard ogni fixture che crea una società
  sarebbe rifiutata, mentre una fixture deve scrivere dove scrive l'app. Il permesso resta al
  backend, come per `anagrafiche.soggetti`. Il permesso a DB per l'anagrafica è un cantiere suo;
- **B-2** (team DB): stato intero.

| changeSet / file | Cosa |
| --- | --- |
| `00_schema/anagrafiche/20261010-95-alter-dati-societari-rea-capitale-dalla-forma` | REA (provincia, numero) e capitale nullable; CHECK `chk_dati_societari_rea_coppia` (B-6) |
| `20_code/anagrafiche/20261010-96-create-fn-forma-giuridica-ammessa` | predicato condiviso: riga attiva **e valida oggi** della matrice delle forme |
| `20_code/anagrafiche/20261010-97-update-trgfn-dati-societari-guard-forma-giuridica` | il guard della forma: paese, matrice (C-1), REA e capitale per policy (B-6); riagganciato anche alle colonne REA e capitale |
| `20_code/anagrafiche/20261010-98-create-trgfn-soggetti-guard-forma-giuridica-natura` | guard **al COMMIT** sul cambio di natura (constraint trigger differito): natura e forma si cambiano nella stessa transazione, prima la natura e poi la forma |
| `20_code/anagrafiche/20261010-99-create-fn-scrivi-dati-societari` | il verbo: crea o aggiorna, stato intero, `SECURITY DEFINER`, nessuna regola propria (B-1..B-3) |
| `20_code/anagrafiche/20261011-01-update-fn-crea-soggetto-pg-dal-verbo-dati-societari` | `fn_crea_soggetto_pg` scrive col verbo (B-4); via i controlli doppi su REA, capitale, canale FE (B-6, B-7) e la risoluzione dei default |
| `20_code/dbops/20261011-02-update-fn-pgtap-crea-soggetto-pg-dal-verbo` | la fixture delle società passa dal verbo: forma = la prima ammessa dalla natura, REA e capitale solo se la forma li prevede. Resta `INVOKER` |
| `90_end/20261011-03-alter-dati-societari-forma-giuridica-not-null` | `forma_giuridica_id NOT NULL` (C-2). ⛔ La preCondition **ferma il migrate** finché ci sono righe senza forma (vedi censimento) |
| `90_end/20261011-04-revoke-app-scrittura-dati-societari` + loop `ci_apply/20260205-41` + `scripts/sql/provision_db_roles.sql` | la porta (B-5), nelle tre sedi |
| `codici_errore.csv`, `messaggi_errore.csv` | 6 codici, id 1260-1265: `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO`, `E_REA_OBBLIGATORIO`, `E_REA_NON_AMMESSO`, `E_CAPITALE_SOCIALE_OBBLIGATORIO`, `E_CAPITALE_SOCIALE_NON_AMMESSO`, `E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA` (tutti `DATO_ERRATO`) |
| `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` | nuovo, plan 22 |
| `test-dati-societari-policy`, `test-dati-societari-canale-fe-v1`, `test-soggetti-indirizzi-required`, `create-soggetto-bank-branches` | le scritture dirette su `dati_societari` passano dal verbo, con una forma ammessa. Nel test del canale una funzione temporanea `ds_cambia` sovrappone i campi e chiama il verbo, e i casi restano identici. Nel test della policy l'asserzione sul privato è diventata `throws_like` sulla frase della policy: prima accettava qualunque errore |
| manuali `dati_societari`, `trgfn_dati_societari_guard_forma_giuridica` | la porta, la forma che decide, l'ordine al cambio di natura |

**Prova pre-apply** (scratch, owner, estratto A+B+C+D, i tre mirror resi offline):
- `test-fn-scrivi-dati-societari-v1`: 21/22. Il **22** (UPDATE diretto → `42501`) è **rosso da
  owner per costruzione** e verde come app. Il **3** (privilegi dell'app) è verde anche da owner,
  perché legge il catalogo;
- mutazioni: senza `-97` cadono 6 casi (9-13, 18); senza `-98` cadono 16 e 17; senza
  `20261011-04` cadono 3 e 22;
- i quattro file portati sul verbo: verdi come prima, tranne `test-soggetti-indirizzi-required`,
  che muore **allo stesso punto della versione di HEAD** (`uq_soggetto_idstato_id_fiscale_univoc…`,
  rosso che c'era già);
- regressione larga: §8.4.

**⏳ Censimento dei dati societari (C-3): da guardare prima dell'apply.** Al 2026-10-10, da §3.2:
152 righe SC con forma «Ditta individuale» e 6 senza forma. Le righe **senza forma fermano il
`20261011-03`**; le altre non fermano niente, ma verranno rifiutate alla prossima modifica. Query
(da owner):

```sql
-- 1. senza forma: fermano il 20261011-03
SELECT ds.id, s.codice, s.ragione_sociale FROM anagrafiche.dati_societari ds
  JOIN anagrafiche.soggetti s ON s.id = ds.soggetto_id WHERE ds.forma_giuridica_id IS NULL;
-- 2. forma non ammessa dalla natura
SELECT ds.id, s.codice, tsd.codice_interno AS natura, fg.codice AS forma
  FROM anagrafiche.dati_societari ds
  JOIN anagrafiche.soggetti s ON s.id = ds.soggetto_id
  JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
  JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id
 WHERE NOT anagrafiche.fn_forma_giuridica_ammessa(ds.forma_giuridica_id, s.tipo_soggetto_dettaglio_id,
                                                  script.fn_giorno_operativo(now()));
-- 3. REA o capitale contro la policy della forma
SELECT ds.id, s.codice, fg.codice AS forma, fg.rea_policy, ds.iscrizione_rea,
       fg.capitale_sociale_policy, ds.capitale_sociale
  FROM anagrafiche.dati_societari ds
  JOIN anagrafiche.soggetti s ON s.id = ds.soggetto_id
  JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id
 WHERE (fg.rea_policy = 'REQUIRED' AND ds.iscrizione_rea IS NULL)
    OR (fg.rea_policy = 'NONE' AND ds.iscrizione_rea IS NOT NULL)
    OR (fg.capitale_sociale_policy = 'REQUIRED' AND ds.capitale_sociale IS NULL)
    OR (fg.capitale_sociale_policy = 'NONE' AND ds.capitale_sociale IS NOT NULL);
```

La 2 e la 3 usano le funzioni nuove, quindi si lanciano **dopo** l'apply fino al `-99`, oppure
sostituendo il predicato con la join sulla matrice.

**Ricadute BE/FE** (aggiornano il §5):
- **il verbo**: `anagrafiche.fn_scrivi_dati_societari(p_soggetto_id, p_forma_giuridica_id,
  p_id_prov_iscri_rea, p_iscrizione_rea, p_capitale_sociale, p_socio_unico, p_liquidazione,
  p_destinatario_fe, p_pec_fatturazione, p_codice_sdi, p_data_costituzione)`, parametri nominati,
  **stato intero**;
- **l'ordine**: se nella stessa PATCH cambia la natura, prima l'UPDATE del soggetto e poi il
  verbo, nella stessa transazione. Il controllo che le lega scatta al COMMIT;
- `fn_crea_soggetto_pg` non pretende più canale FE, REA e capitale: le regole arrivano dalla forma;
- 12 codici nuovi in tutto il cantiere (A 3, D 3, B/C 6): `genera_error_policies` e ripiego;
- il lookup delle forme (`LookupRepository.list_forme_giuridiche`) filtra per natura e `attivo`,
  ma non per la **validità** (`valido_dal`/`valido_al`), che il guard invece guarda. Va allineato,
  o il form offrirà una forma che il DB rifiuta.

### 8.4 Regressione larga e stato dell'apply

**Regressione pre-apply** (scratch, 2026-10-10): 301 pgTAP, cioè tutti quelli che toccano gli
helper delle fixture, la creazione di società, dati societari, titoli, flag o natura. Lanciati
prima (file di HEAD, senza estratto) e dopo (file attuali con l'estratto A+B+C+D): cambiano
**solo i tre file nuovi**. Nessun file esistente cambia esito. Lo scratch non ha dati di
macchina, quindi i test che pescano dai dati falliscono uguali prima e dopo: quelli li misura la
corsa di Tid su dbdev.

**Apply su dbdev (Tid, 2026-10-10 21:27):** entrati dal `20261010-85` al `-99`, `20261011-01`,
`-02`, i tre mirror (`20250717-12`, `20260614-08`, `-89`) e il `-87`. Il migrate si è **fermato,
come previsto, sul `20261011-03`**: ci sono 6 righe senza forma, tutte residui di pgTAP rimasti
committati. Restano da applicare `20261011-03` e `-04`. ⛔ Da qui ogni correzione ai file
applicati va in un changeSet nuovo.

| ds | soggetto | natura | REA / capitale |
| --- | --- | --- | --- |
| 15 | SGT-0000119 Gestore Test pgTAP | SC | sì / sì |
| 16 | SGT-0000123 Banca Zero Test pgTAP | SC | sì / sì |
| 36 | TST-DSP-SP-001 Azienda SP OPTIONAL | SP | sì / sì |
| 37 | TST-DSP-SC-OK Azienda SC REQUIRED con dati | SC | sì / sì |
| 506, 508 | TST-IND-SC-OK-… Societa Test OK | SC | sì / sì |

⏳ **Tid le corregge a mano** (decisione del 2026-10-10). Proposta, che regge il guard della forma
(SRL: REA e capitale obbligatori; SNC: REA obbligatorio, capitale facoltativo):

```sql
UPDATE anagrafiche.dati_societari
   SET forma_giuridica_id = CASE id
           WHEN 36 THEN (SELECT id FROM config.forme_giuridiche WHERE codice = 'SNC')
           ELSE         (SELECT id FROM config.forme_giuridiche WHERE codice = 'SRL') END
 WHERE id IN (15, 16, 36, 37, 506, 508) AND forma_giuridica_id IS NULL;
```

Poi si rilancia il migrate, che applica `20261011-03` e `-04`. Dopo la corsa pgTAP vanno
guardati come app i due rossi da owner dichiarati: test 14 di
`test-soggetti-titoli-iva-tipo-soggetto-v1` e test 22 di `test-fn-scrivi-dati-societari-v1`.

✅ **Chiuso il 2026-10-10 (Tid):** righe corrette a mano, migrate rilanciato (`20261011-03` e
`-04` applicati), **test verdi**: compresi i due rossi da owner, che come app passano.

**Cosa resta:**
- **BE/FE**: §5 e ricadute del §8.3. Ci sono 12 codici nuovi da mettere in policy e ripiego, il
  verbo da chiamare in modifica (prima la natura, poi il verbo), e il lookup delle forme da
  allineare alla validità della matrice;
- **D-4** (`COOPERATIVA`): finché è aperta, nessuna riga di matrice. Se si chiude con «titolare il
  cliente», basta una riga nel CSV;
- **censimento dei titoli IVA** fuori regola (query in §8.2): da guardare se ce ne sono; il guard
  non li tocca finché nessuno li modifica;
- `fornitori.split_payment` (§7): da verificare, eventualmente brief suo;
- il permesso a DB per l'anagrafica (`fn_guard_livello` nei verbi): fuori da questo brief, cantiere suo.

## 9. Sviluppo BE/FE (sessione BE, 2026-10-10)

### 9.1 Cosa e' stato fatto, per parte

| Parte | BE | FE |
| --- | --- | --- |
| **A** | `LookupRepository.list_tipi_soggetto_dettaglio` e `get_config_resolver` portano `cliente_pa_ammesso` / `split_payment_ammesso` | `useSoggettoForm` espone `showClientePa` / `showSplitPayment`; la sezione «Dati fiscali» c'e' solo se resta un campo; `:invalid` da `campiErrati`; via il `.trim()`. Un flag nascosto parte `N` (A-3) |
| **B** | `SoggettiService.update_soggetto` accetta `dati_societari` (contratto validato: un oggetto, le sole chiavi del verbo) e chiama `SoggettiRepository.scrivi_dati_societari` → `fn_scrivi_dati_societari`, parametri nominati, stato intero. **Prima il soggetto, poi il verbo**, in un solo `transaction.atomic()`. `get_dati_societari` legge anche `data_costituzione` | `handleSave` in modifica manda `dati_societari` con `toPayload()` se la riga c'e' o se e' stata scelta una forma (con la natura `OPTIONAL` e la sezione vuota non c'e' niente da creare). Campo nuovo «Data di costituzione»: lo stato intero lo azzererebbe |
| **C** | `list_forme_giuridiche` filtra col predicato del guard, `fn_forma_giuridica_ammessa(…, fn_giorno_operativo(now()))`: matrice attiva **e valida** | Forma, REA e capitale si accendono da `campiErrati`. La forma salvata fuori elenco resta visibile, marcata «non ammessa per il tipo soggetto» |
| **D** | Lookup nuovo `GET soggetti/{id}/titoli-iva/tipi/lookup/` (`fn_titolo_iva_ammesso`), con `ha_plafond` | `TitoloIvaDrawer`: `LookupSelect` col fetcher del lookup, chiave per soggetto invalidata a ogni apertura (la natura puo' cambiare), voce corrente per un tipo non piu' ammesso, `:invalid` sul tipo |
| Codici | `genera_error_policies` (12 codici, zero classi cambiate) + 12 ripieghi in `error_messages_fallback.py` | etichette del pannello config per le due colonne nuove (`config_panel.campi.*`) |

### 9.2 ⛔ Trovato: il lookup delle forme giuridiche falliva sempre

`list_forme_giuridiche` leggeva `COALESCE(fg.codice_interno, fg.codice)`, ma
`config.forme_giuridiche` una colonna `codice_interno` non l'ha mai avuta. Dal 2026-03-28 la
query falliva **sempre**: l'endpoint rispondeva 500, il drawer ingoiava l'errore e la tendina
restava vuota. E' con ogni probabilita' la causa vera del «la forma giuridica e' vuota» del
collaudo R-2 (§3.1), che si sommava al difetto del modello. I test unitari, col cursore mockato,
non potevano vederlo; lo ha visto il primo test sul DB vero. Corretto (`fg.codice`).

### 9.3 ⛔ Trovato: la natura cambiata in modifica non arrivava al DB

Il drawer offre in modifica le nature della stessa natura base (`tipi_modificabili_ids`), ma
`tipo_soggetto_dettaglio_id` non era nel contratto della PATCH, e il drawer non lo mandava:
l'operatore cambiava SP in SC, leggeva «salvato» e non cambiava niente. Il §8.3 presuppone che
il cambio passi dalla PATCH («prima la natura, poi il verbo»). Ora la chiave e' nel contratto
(`SOGGETTO_UPDATE_COLS`) e il drawer la manda **solo se cambiata**; cosa la natura nuova ammette
lo dicono i guard.

### 9.4 Prove

- `apps/anagrafiche/tests/db/test_dati_fiscali_societari_db.py` (DB vero, 12 test): flag per
  natura, verbo con stato intero, campo acceso (`codice_sdi`, `forma_giuridica_id`, `cliente_pa`),
  «non trovato» del verbo, **natura e forma nella stessa PATCH**, natura senza forma rifiutata al
  COMMIT, i due lookup. Mutazione: invertendo l'ordine soggetto/verbo il test 8 va rosso.
- 3 test unitari nuovi su `update_soggetto` (contratto della sezione, stato intero, niente
  UPDATE vuoto).
- Suite BE intera con `ZEROERP_TEST_DB_E2E=1`: 6495 verdi. mypy a registro, ruff pulito.
- FE: vitest 795 verdi (spec di `useSoggettoForm` e `useDatiSocietariForm` estesi), lint, guard
  e build verdi.
- ✅ Collaudo in-app: fatto da Tid il 2026-10-11 (modifica di una SC con canale, SDI e data di
  costituzione; cambio SP↔SC con la forma; privato senza sezione «Dati fiscali»; titolo IVA su
  un privato, solo 104).

### 9.5 Cosa resta

- ⚠️ **Richiesta al team DB — `data_costituzione` in creazione.** `fn_crea_soggetto_pg` chiama il
  verbo con `p_data_costituzione := NULL` e non ha un parametro per riceverla: la creazione non
  la può scrivere. Il FE la offre quindi **solo in modifica** (`DatiSocietariForm`, prop
  `showDataCostituzione`): in creazione si sarebbe persa in silenzio. Proposta: un parametro
  `p_data_costituzione date DEFAULT NULL` passato al verbo; poi BE (`crea_soggetto_pg`,
  `_create_pg`) e FE (togliere la prop) si allineano. ➡️ 2026-10-14: in
  [brief-db-dati-societari-in-creazione](brief-db-dati-societari-in-creazione.md),
  insieme alla ditta individuale, che in creazione perde tutta la sezione;
- il rifiuto di un REA gia' usato (`uq_ds_prov_cea`) accende `iscrizione_rea`, in modifica e in
  creazione (`create_with_constraint_mapping`, test 13 e 15 sul DB vero). In creazione fino al
  2026-10-11 usciva «CF/PIVA duplicata»: difetto del solo BE, il DB nominava gia' il vincolo;
- ⚠️ **Cambio di natura con dati non congrui** (dati societari su una natura `NONE`, titoli IVA
  non ammessi, flag PA/split): oggi o vicolo cieco o perdita silenziosa. Decisione di Tid
  (2026-10-11): conferma esplicita, poi pulizia → brief proprio,
  [brief-db-cambio-natura-soggetto-conferma-e-pulizia](../work-in-progress/brief-db-cambio-natura-soggetto-conferma-e-pulizia.md);
- ⛔ Trovato e corretto (solo BE): `get_config_resolver` leggeva il default di natura per ruolo con
  `get_parameter`, che su un parametro non dichiarato solleva; il seed lo dichiara per CL e FO, e
  per RIS_UMANA ed EF il risolutore andava in errore (il FE lo ingoiava: cercatore senza filtro di
  natura). BB `get_parameter_se_dichiarato` (regola del 2, ok Tid 2026-10-11), usato anche da
  `get_parameters`, che prometteva di escludere i codici non trovati e invece falliva (test 16);
- BB `SQL_TIPI_SOGGETTO_DETTAGLIO` (regola del 2, ok Tid 2026-10-11): lookup e risolutore per
  ruolo leggono la stessa riga. Divergevano: per l'ente `natura_soggetto` era `ENC` (il codice)
  nel lookup, in lista e nel dettaglio, `ENTE` (l'enum) nel risolutore — e `SoggettoResolver`,
  che confronta i due, marcava ogni ente «natura bloccata». Ora e' l'enum ovunque (test 14);
- **D-4** (`COOPERATIVA`) e il censimento dei titoli fuori regola (§8.2), invariati;
- `fornitori.split_payment` (§7), invariato.

➡️ 2026-10-14: gli ultimi due punti, con il `cliente_pa` di `SGT-0000121` (§8.1), sono in
`.codex/PROJECT_CONTEXT.md` § «Aperto — Media priorità».
