# Brief DB — Dati fiscali e societari del soggetto: chi li scrive, e per quali nature

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10, su segnalazioni di Tid e su quanto
> trovato chiudendo `work-done/brief-db-character-n-spazi-di-riempimento.md`.
> **A chi:** team DB; poi BE/FE (§5).
> **Stato:** 🔵 pronto per il team DB: decisioni di Tid prese il 2026-10-10 (§4), resta aperta solo
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
| **A-3** | **Il guard.** | Su `anagrafiche.soggetti` (BEFORE INSERT OR UPDATE OF `cliente_pa`, `split_payment`, `tipo_soggetto_dettaglio_id`): un flag a `S` su una natura che non lo ammette → codice nuovo di classe `DATO_ERRATO` (proposta: `E_REGIME_PA_NON_AMMESSO`, uno solo per i due flag) con `campo` = il flag, e una frase che nomina natura e campo. Copre anche il cambio di natura: chi cambia natura porta il flag a `N` nella stessa scrittura, il DB non lo azzera da sé. |
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

## 7. Fuori perimetro, da verificare

`anagrafiche.fornitori.split_payment` (`boolean`, **nullable**, scritto dal BE come
`bools=(…)`) non ha lettori nel DB oltre a `vw_fornitori_dettaglio` (verificato il 2026-10-10). Sul
lato passivo la scissione dipende da chi **compra**, cioè dall'emittente, non dal fornitore: il flag
potrebbe essere nella sede sbagliata, oltre che senza regola sulla natura. È un difetto diverso da
A, e se confermato va in un **brief suo**.
