# Brief DB — Un indirizzo nuovo partendo da uno esistente

## ⏭️ Chi riparte — aggiornato al 2026-11-15

**Riparte: il team DB**, col giro 1 del §5. Le decisioni D-1 … D-4 le ha prese Tid il
2026-11-15 (§6): tutte come da proposta.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | giro 1: le check e il motivo «tipo già presente», chiamate dalle singolari, sui due layer; gli obbligatori delle plurali sulla finestra di validità (D-4) | §4.1, §4.2, §4.6 | — |
| 2 | team DB | giro 2: i picker dei tipi, sui due layer | §4.3, §4.6 | 1 |
| 3 | team DB | giro 3: i verbi della copia e il loro motivo di riga, sui due layer | §4.4, §4.5, §4.6 | 1 |
| 4 | BE/FE | richiesta R-1 … R-5 | §7 | 2, 3 |
| 5 | chi chiude | archiviazione in `work-done/` | — | 4 |

Decisioni aperte di Tid: nessuna. Lavoro fatto da committare: questo file.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-15.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE al §7.
> **Origine:** richiesta di Tid del 2026-11-15: nel drawer del soggetto, in modifica, non c'è
> modo di creare un indirizzo partendo da uno che il soggetto ha già, per esempio duplicare la
> sede legale come indirizzo di spedizione cambiando solo il tipo.
> **Brief vicini verificati:**
> [brief-db-fornitore-privato-indirizzi](brief-db-fornitore-privato-indirizzi.md): tratta gli
> indirizzi del **ruolo** (`config.tipi_ruolo_tipi_indirizzo`) e la sede legale del privato;
> oggetti diversi, nessuna sovrapposizione. `work-done/brief-db-cambio-natura-soggetto-conferma-e-pulizia`
> (chiuso il 2026-11-14) ha dato a `fn_tipo_indirizzo_ammesso_per_natura` la forma di sede unica del
> predicato: questo brief la **legge**, non la cambia. Nessuna decisione precedente sulla copia di un
> indirizzo d'anagrafica (cercato in `work-done/` e nella guida *Gestione degli indirizzi*).

## 1. Il caso

Un soggetto ha un indirizzo per tipo (`uq_indirizzi_soggetti_soggetto_tipo`). Spesso la spedizione,
la fatturazione o la posta stanno allo stesso indirizzo della sede legale o della residenza.
L'operatore oggi ha una sola strada: «Aggiungi», scegliere il tipo e **ricompilare** l'indirizzo da
capo. Serve il gesto «questo stesso indirizzo, anche come…».

Il gesto ha un significato preciso: **la copia di una riga di `anagrafiche.indirizzi_soggetti` col
tipo sostituito**. È esattamente ciò che `anagrafiche.fn_indirizzi_con_obbligatori` fa già alla
creazione del soggetto (la copia del primo indirizzo per i tipi obbligatori mancanti), ma su un
indirizzo **già scritto** e su un tipo **scelto dall'operatore**.

## 2. Che cosa c'è già (contratto, dalla doc auto-generata, 2026-11-15)

| Pezzo | Che cosa dice | Serve qui? |
| --- | --- | --- |
| `fn_crea_indirizzo_soggetto(soggetto, jsonb)` | la madre singolare: un indirizzo nella grammatica di `fn_indirizzo_elemento`, tre forme | ✅ è la sola scrittura: la copia passa da lei |
| `fn_crea_indirizzi_soggetto(soggetto, jsonb, copia_obbligatori)` | la plurale della creazione; un tipo che il soggetto ha già **si salta** | ⚠️ non adatta: alla copia esplicita un salto silenzioso è un rifiuto taciuto |
| `fn_indirizzi_con_obbligatori` | BB puro: copia del primo elemento col tipo sostituito | ⚠️ lavora su elementi in ingresso, non su una riga salvata |
| `fn_tipo_indirizzo_ammesso_per_natura(natura, tipo, giorno)` | sede unica del predicato: natura NULL o senza matrice = tutti i tipi; altrimenti riga attiva **e valida il giorno** | ✅ la check lo chiama |
| `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` | il guard della scrittura, sullo stesso predicato, giorno `fn_data_operativa()` | ✅ resta la fonte di verità |
| `uq_indirizzi_soggetti_soggetto_tipo` | un tipo per soggetto | ⚠️ **rifiuta senza codice** (§3.2) |
| `trgfn_child_requires_active_parent` su dettaglio e soggetto | la riga vuole il dettaglio attivo e il soggetto attivo | ✅ la copia di un indirizzo dal dettaglio spento si rifiuta, giustamente |

**Che cosa si copia.** Le colonne della grammatica dell'elemento, e nient'altro: o
`indirizzo_dettaglio_id` (il dettaglio è condiviso, non si duplica), o la forma libera
(`indirizzo_libero`, `stato_id`, `comune_id`, `codice_postale_id`, `administrative_area`,
`locality`, `sublocality`, `postal_code`). `geoloc` la rimette il trigger di sync come per ogni
scrittura; `tx_id`, audit e `storicizza` sono quelli di una riga nuova.

## 3. Due difetti trovati analizzando (fatti, non misure)

### 3.1 Il FE propone i tipi da una copia della regola, e la copia è già divergente

Il drawer degli indirizzi del soggetto sceglie i tipi da proporre in «Aggiungi» dal lookup BE
`LookupRepository.list_matrice_indirizzi` (`backend/apps/core/db/lookup_repository.py`), che legge
la matrice con il solo `attivo = true`. Il guard invece usa `fn_tipo_indirizzo_ammesso_per_natura`.
I due rispondono diversamente in due casi che il **modello ammette**:

| Caso | Il guard | Il lookup, e quindi il FE |
| --- | --- | --- |
| riga di matrice attiva ma fuori dalla sua finestra (`valido_dal` futuro, `valido_al` passato) | rifiuta `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` | **propone** il tipo: l'operatore compila e prende il rifiuto |
| natura senza nessuna riga di matrice (fallback permissivo) | ammette **ogni** tipo | **non propone niente**: il pulsante «Aggiungi» sparisce (`matriceDisponibile.length > 0`) |

È il caso del §12.6 delle linee guida («un picker propone ciò che il guard accetta, leggendo la
stessa check»). Il picker del §4.3 lo chiude per «Aggiungi» e per la copia insieme.

⚠️ Lo stesso scarto sta nella plurale `fn_crea_indirizzi_soggetto`: i tipi **obbligatori** li legge
dalle righe attive «senza guardare la finestra di validità» (lo dice la sua pagina `manual/`). Una
riga obbligatoria scaduta fa nascere una copia che il guard poi rifiuta. Si corregge nel giro 1
(D-4), e vale anche per la plurale del ruolo (§4.6).

### 3.2 La singolare rifiuta il tipo già presente senza saper dire perché

`fn_crea_indirizzo_soggetto` affida il «tipo già presente» a `uq_indirizzi_soggetti_soggetto_tipo`.
Al BE arriva un `IntegrityError`, che `create_with_dedup` traduce nel testo fisso «Indirizzo
duplicato per questo soggetto.», senza codice a catalogo e senza il tipo. Per il §12.5.2 è il
difetto a monte: una check ha bisogno di un codice nuovo perché la madre rifiutava senza motivo.
Il vincolo resta, come presidio contro la corsa; il rifiuto educato lo dà la check.

## 4. La proposta

### 4.1 La check: «questo tipo, per questo soggetto?»

`anagrafiche.fn_check_tipo_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer) RETURNS jsonb`,
nella forma del §12.5.1 (`[]` se ammesso, altrimenti i motivi in ordine):

| Ordine | `reason` | `codice` | Condizione |
| --- | --- | --- | --- |
| 1 | `TIPO_GIA_PRESENTE` | **nuovo** (§4.2) | il soggetto ha già una riga di quel tipo |
| 2 | `TIPO_NON_AMMESSO_DALLA_NATURA` | `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` (a catalogo) | `NOT fn_tipo_indirizzo_ammesso_per_natura(natura del soggetto, tipo, fn_data_operativa())` |

L'ordine (proposta, il team DB lo può rivedere scrivendo il perché): «già presente» è il fatto più
specifico del soggetto e quello che l'operatore risolve da solo, togliendo o cambiando la riga che
c'è; la natura è una regola di configurazione.

⭐ Il predicato della natura **non si riscrive**: la check chiama `fn_tipo_indirizzo_ammesso_per_natura`,
come il guard. Per il §12.6 (molti candidati, un soggetto) la check si può dividere in contesto
(la natura e i tipi presenti, letti una volta) e motivi di un candidato; la firma sopra le compone.

### 4.2 Il codice nuovo, e la singolare che chiama la check

* Codice nuovo, proposta `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE` (`DATO_ERRATO`), coi valori il
  tipo (descrizione) e il soggetto. Il nome dice il layer, come il codice del guard: il ruolo ha un
  vincolo suo (`uq_indirizzi_ruolo_*`) e, con D-1, un codice suo.
* `fn_crea_indirizzo_soggetto` **chiama** la check (§12.5.2, D-3) e solleva il primo motivo prima
  dell'`INSERT`. Il guard della natura resta sul trigger; la check lo anticipa con lo stesso
  predicato, e il presidio da scrivere è «la singolare non contiene il predicato».
* La plurale `fn_crea_indirizzi_soggetto` **non cambia comportamento** sui tipi presenti: li salta
  prima di chiamare la singolare (la sua regola 3), quindi non incontra il motivo nuovo. Cambia
  invece la lettura dei suoi **obbligatori** (D-4): righe attive **e valide** il giorno
  `fn_data_operativa()`, come il guard. La cosa più semplice è leggerli col predicato stesso
  (`fn_tipo_indirizzo_ammesso_per_natura` sulla coppia, più `obbligatorio`), così le due letture non
  possono divergere; la pagina `manual/` della plurale perde il suo ⚠️ sulla finestra.

### 4.3 Il picker dei tipi

`anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(p_soggetto_id uuid)`, gemella di
`fn_nature_proponibili_soggetto`: una riga per tipo di `config.tipi_indirizzi`, con
`tipo_indirizzo_id`, `obbligatorio` (dalla matrice, sulla stessa finestra di validità), `ammesso`,
il `reason` / `reason_key` del primo motivo e i motivi. Prima gli ammessi, poi gli altri. Legge la
check del §4.1: propone ciò che la singolare e il verbo della copia accettano.

Serve due gesti: «Aggiungi» (il tipo del nuovo indirizzo) e «Copia come…» (i tipi di destinazione).

⚠️ Alla **creazione** del soggetto il soggetto non esiste, e il form usa oggi lo stesso lookup
divergente (`useIndirizzoSoggettoForm.loadMatriceTipo`). Per il §12.6 lì il contesto sono i valori
del form, cioè la natura scelta: serve la sorella sulla natura (proposta
`fn_tipi_indirizzo_proponibili_natura(p_tipo_soggetto_dettaglio_id bigint)`, senza il motivo «già
presente»), e la funzione sul soggetto la compone. ⛔ Non un parametro facoltativo sulla stessa
firma: la natura arriverebbe da due fonti, e le firme con `DEFAULT` si sovrappongono.

### 4.4 Il verbo della copia

`anagrafiche.fn_copia_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[]) RETURNS bigint[]`
(più tipi in un gesto, tutto o niente: D-2):

1. la riga sorgente dev'essere **di quel soggetto**: altrimenti un codice `NON_TROVATO` (proposta
   `E_INDIRIZZO_SOGGETTO_NON_TROVATO`, nuovo). Soggetto o elenco mancanti:
   `E_SCRIPT_CHIAMATA_NON_VALIDA`. Un tipo che il catalogo non ha: `E_TIPO_INDIRIZZO_NON_TROVATO`
   del BB dell'elemento;
2. per ogni tipo, la check del §4.1, che solleva il **primo** motivo; un tipo ripetuto nell'elenco
   è un tipo già presente al secondo giro, e si rifiuta allo stesso modo;
3. l'elemento si costruisce dalla riga sorgente con le sole colonne del §2 e il tipo sostituito, e
   lo scrive la **singolare** `fn_crea_indirizzo_soggetto`: nessuna seconda `INSERT`, tutti i guard
   della tabella valgono;
4. tutto o niente: un rifiuto su un tipo non lascia scritti gli altri;
5. ritorna gli id delle righe nuove, nell'ordine dei tipi.

Il permesso: come le madri sorelle dell'anagrafica, oggi il verbo non chiama un guard (lo controlla
la view del BE, `DomainAPIView`). Se Tid vuole il permesso nel verbo, è il passaggio del dominio
`anagrafiche` al modello «una scrittura = un verbo», che non si apre qui.

### 4.5 Il motivo di riga: «Copia come…» spento col motivo

L'azione vive sulla card di ogni indirizzo del drawer (§12.5.3: da lì si preme). È spenta quando la
riga non si può copiare **in nessun tipo**, per §12.1:

| `reason` | Condizione |
| --- | --- |
| `DETTAGLIO_NON_ATTIVO` | la riga punta a un dettaglio spento: la riga nuova lo rifiuterebbe (`trgfn_child_requires_active_parent`) |
| `NESSUN_TIPO_PROPONIBILE` | il picker del §4.3 non ha un tipo ammesso |

Proposta: `anagrafiche.fn_check_copia_indirizzo_soggetto(p_indirizzo_soggetto_id bigint) RETURNS jsonb`,
chiamata anche dal verbo; il motivo arriva in **una vista di riga** degli indirizzi del soggetto
(`copia_blocco_reason`, `copia_blocco_reason_key`), iscritta in `config.azioni_riga` (§12.5.7).

⚠️ Oggi la lista degli indirizzi del soggetto è SQL scritto nel BE
(`SoggettiRepository.get_soggetto_indirizzi`), e una colonna di blocco composta dal BE non si
iscrive. La vista è quindi parte del lavoro; se `vw_indirizzi_resolved_soggetto` è la sede giusta
(oggi la legge `views_indirizzi_ruolo.py` per la cascata) o ne serve una nuova lo decide il team DB.
La vista deve portare tutte le colonne che la lista BE legge oggi, così il BE la sostituisce senza
perdere niente (oggi mancano, fra l'altro, i campi della forma estera).

### 4.6 Il layer ruolo, nello stesso lavoro (D-1)

Gli indirizzi del ruolo (`anagrafiche.indirizzi`) hanno lo stesso bisogno e gli stessi due difetti:
un tipo già presente lo rifiutano solo i due vincoli `uq_indirizzi_ruolo_tipo_no_istanza` e
`uq_indirizzi_ruolo_istanza_tipo`; i tipi del drawer arrivano dal lookup
`lookupMatriceIndirizziRuolo`, una lettura della matrice che il guard non legge. I pezzi sono i
gemelli del soggetto, con tre differenze di modello:

1. **Il predicato del ruolo oggi non ha una sede.** `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`
   lo scrive dentro il corpo del trigger (matrice `config.tipi_ruolo_tipi_indirizzo`, fallback
   permissivo se il tipo di ruolo non ha righe, riga attiva e valida il giorno). Va estratto,
   gemello di quello della natura, in `fn_tipo_indirizzo_ammesso_per_ruolo(tipo_ruolo, tipo, giorno)`,
   e il trigger lo legge: la check del ruolo lo chiama, non lo ricopia. Il codice resta quello del
   guard, `E_TIPO_INDIRIZZO_NON_PERMESSO`.
2. **«Già presente» ha la chiave con l'istanza**: lo stesso tipo è ammesso una volta sul ruolo senza
   istanza e una volta per ogni istanza. La check prende l'istanza (`NULL` = il ruolo) e guarda la
   chiave giusta; il codice nuovo è quello del ruolo (proposta
   `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`), distinto da quello del soggetto per la stessa ragione per
   cui lo sono i due codici del tipo non ammesso.
3. **La copia resta nello stesso layer e nella stessa istanza**: la riga nuova prende ruolo e
   `istanza_utility_id` della sorgente. La copia **fra layer** (un indirizzo del soggetto copiato sul
   ruolo, o il contrario) è un gesto diverso e resta fuori da questo brief.

| Soggetto | Ruolo (gemello) |
| --- | --- |
| `fn_check_tipo_indirizzo_soggetto(soggetto, tipo)` | `fn_check_tipo_indirizzo_ruolo(ruolo, istanza, tipo)` |
| `fn_crea_indirizzo_soggetto` chiama la check | `fn_crea_indirizzo_ruolo` chiama la check |
| `fn_tipi_indirizzo_proponibili_soggetto(soggetto)` / `_natura(natura)` | `fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza)` / `_tipo_ruolo(tipo_ruolo)` per il ruolo in assegnazione |
| `fn_copia_indirizzo_soggetto(soggetto, indirizzo, tipi[])` | `fn_copia_indirizzo_ruolo(ruolo, indirizzo, tipi[])` |
| `fn_check_copia_indirizzo_soggetto(indirizzo)` + vista di riga | `fn_check_copia_indirizzo_ruolo(indirizzo)` + vista di riga |
| la plurale legge gli obbligatori col predicato (D-4) | `fn_crea_indirizzi_ruolo` idem: oggi legge le righe attive senza finestra |

Rifiuti del verbo del ruolo: la sorgente dev'essere di quel ruolo (proposta
`E_INDIRIZZO_RUOLO_NON_TROVATO`); un ruolo inesistente è il già catalogato
`E_SOGGETTO_RUOLO_NON_TROVATO`.

⚠️ Nel drawer, in contesto ruolo, la lista mostra anche gli indirizzi del **soggetto** (la cascata,
`fonte = 'soggetto'`): su quelle righe l'azione è la copia del soggetto, non quella del ruolo, e la
vista di riga del ruolo non le porta.

## 5. I giri

Ogni giro copre i due layer, soggetto e ruolo (D-1).

| Giro | Che cosa | Prova |
| --- | --- | --- |
| 1 | §4.1 check, §4.2 codice nuovo + singolare che la chiama; estrazione del predicato del ruolo (§4.6.1); obbligatori delle due plurali sul predicato (D-4) | pgTAP: ogni motivo **costruito** (un soggetto o un ruolo col tipo già scritto, anche su un'istanza; una matrice con la riga scaduta; una natura e un tipo di ruolo senza matrice; un obbligatorio scaduto che la plurale non copia più); presidi «la singolare non contiene il predicato» e «il trigger del ruolo legge la funzione» |
| 2 | §4.3 picker (soggetto, natura, ruolo, tipo di ruolo) | pgTAP: ogni picker e la sua singolare dicono la stessa cosa sui casi del §3.1 |
| 3 | §4.4 verbi, §4.5 check di riga + viste + registro | pgTAP: copia dal dettaglio, copia libera nazionale ed estera (tutte le colonne del §2 arrivano), sorgente di un altro soggetto o ruolo, copia sul ruolo che resta nella sua istanza, tutto-o-niente su due tipi col secondo rifiutato, dettaglio spento; `test-azioni-riga-registro-v1.sql` verde con le righe nuove |

Ogni codice nuovo entra in `codici_errore.csv` con la sua policy: il BE rigenera
`error_policies_generated.py` e aggiunge il ripiego (§7, R-5).

## 6. Decisioni di Tid (prese il 2026-11-15, tutte come da proposta)

* **D-1 — Il ruolo nello stesso lavoro: sì.** La check, il picker e il verbo gemelli sul ruolo
  (§4.6), con la copia **nello stesso layer e nella stessa istanza**. La copia **fra layer** resta
  fuori. Perché: gli indirizzi del ruolo hanno lo stesso bisogno e gli stessi due difetti, e
  un'asimmetria del modello si chiude subito, non in una seconda fase.
* **D-2 — Più tipi per gesto, tutto o niente** (`text[]`). Perché: «la sede legale è anche
  spedizione, fatturazione e posta» è un gesto solo; con un tipo per chiamata il FE farebbe N
  chiamate non atomiche. È il difetto che il drawer ha già nel salvataggio multi-tipo di «Aggiungi»,
  dove si fa un `POST` per tipo e un fallimento a metà lascia scritti i primi.
* **D-3 — Il motivo «tipo già presente» anche nelle singolari: sì** (§4.2, §4.6). Perché: senza, la
  copia avrebbe un rifiuto col motivo e «Aggiungi» il testo fisso del BE, cioè due risposte per la
  stessa regola.
* **D-4 — Gli obbligatori delle plurali sulla finestra di validità: sì, nel giro 1** (§3.1, §4.2),
  per il soggetto e per il ruolo.

## 7. Richieste a BE/FE (dopo i giri DB)

* **R-1 (BE)** — `POST soggetti/<id>/indirizzi/<indirizzo_soggetto_id>/copia/` e
  `POST ruoli/<soggetto_ruolo_id>/indirizzi/<indirizzo_id>/copia/`, con
  `{"tipi_indirizzo_codice_interno": [...]}` → i verbi del §4.4 e §4.6; rispondono con gli id.
* **R-2 (BE)** — il lookup dei tipi del drawer e dei form di creazione (soggetto e assegnazione del
  ruolo) legge i picker del §4.3 e §4.6; si ritirano `LookupRepository.list_matrice_indirizzi` e la
  lettura gemella della matrice del ruolo (regola del 2: la copia divergente si toglie nello stesso
  giro), dopo aver cercato ogni altro chiamante.
* **R-3 (BE)** — le liste `GET soggetti/<id>/indirizzi/` e `GET ruoli/<id>/indirizzi/` leggono le
  viste del §4.5 e §4.6 e portano `copia_blocco_reason` / `copia_blocco_reason_key`.
* **R-4 (FE)** — `IndirizziSoggettoDrawer`: le azioni della card passano al kebab `RowActionsMenu`
  («Cambia», «Copia come…» spenta col motivo); «Copia come…» apre la scelta dei tipi dal picker, gli
  esclusi visibili col loro motivo; dopo il salvataggio si ricarica la lista. «Aggiungi» legge lo
  stesso picker, e il pulsante resta quando la natura non ha matrice. In contesto ruolo la stessa
  azione, col verbo del ruolo sulle righe del ruolo e quello del soggetto sulle righe della cascata
  (§4.6, ultimo punto). Il drawer è riusato da
  `DocumentoIndirizziDrawer` in modalità selezione: lì l'azione vale uguale, il gesto è sull'anagrafica.
* **R-5 (BE)** — i codici nuovi (§4.2, §4.4, §4.6): `error_policies_generated.py` rigenerato col DB
  allineato a git, il ripiego in `error_messages_fallback.py`; le `reason_key` nei locales FE.
