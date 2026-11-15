# Brief DB — Un indirizzo nuovo partendo da uno esistente

## ⏭️ Chi riparte — aggiornato al 2026-11-15

**Nessuno: brief chiuso e archiviato il 2026-11-15.** Q-2 è applicata, pgTAP verde (2026-11-15, §8.1); il caso «natura inesistente → `[]`» è nel test Django (§8.2). Fatte il 2026-11-15 tutte le richieste del §7: R-0, R-0 bis e R-5 (commit
`940a4e6b6`); R-6, R-2, R-1, R-3, R-4 (commit `82fe126890`). Il DB dei giri 1, 2, 3 e Q-1 è
applicato, verde e committato (`42a8fa7847`). Le decisioni D-1 … D-4 le ha prese Tid il 2026-11-15
(§6): tutte come da proposta.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | ✅ giro 1 scritto e provato in `ROLLBACK` (2026-11-15) | §5.1 | — |
| 1-bis | Tid | ✅ giro 1 applicato, pgTAP verdi (2026-11-15) | §5.1 | — |
| 1-quater | team DB | ✅ Q-1 scritta e provata in `ROLLBACK` (2026-11-15): le due frasi, i due guard e le due check sulle descrizioni | §5.2 | — |
| 1-quinquies | Tid | ✅ Q-1 applicata, pgTAP verdi (2026-11-15) | §5.2 | — |
| 1-ter | BE/FE | ✅ R-0 (le chiavi i18n, che sbloccano il commit DB) e R-6 (il test Django sul duplicato, le policy dei codici nuovi) (2026-11-15). R-6: `create_with_dedup` resta intorno alle singolari, per FK, CHECK e la corsa fra due scritture | §7 | — |
| 2 | team DB | ✅ giro 2 scritto e provato in `ROLLBACK` (2026-11-15): i quattro picker | §5.3 | — |
| 2-bis | Tid | ✅ giro 2 applicato, pgTAP verdi coi presidi 1-2 riscritti (2026-11-15) | §5.3 | — |
| 2-ter | BE/FE | ✅ R-2 (2026-11-15): i quattro picker in una lettura sola (`LookupRepository.list_tipi_indirizzo_proponibili`), rotte nuove `soggetti/<id>/indirizzi/tipi/` e `ruoli/<id>/indirizzi/tipi/`; ritirate le due letture della matrice, nel BE e nel FE | §7 | — |
| 3 | team DB | ✅ giro 3 scritto e provato in `ROLLBACK` (2026-11-15): verbi, check di riga, viste, registro | §5.4 | — |
| 3-bis | Tid | ✅ giro 3 applicato, pgTAP verdi (2026-11-15) | §5.4 | — |
| 4 | BE/FE | ✅ R-1 (le due rotte `…/copia/`), R-3 (le liste dalle viste di azioni, BB `COLONNE_INDIRIZZO_RESOLVED`: la lista del soggetto legge la vista risolta e porta la forma estera), R-4 (kebab, «Copia come…» col motivo del registro, `CopiaIndirizzoDialog`), R-5 e R-0 bis (2026-11-15) | §7 | — |
| 4-bis | team DB | ✅ Q-2 scritta e provata in `ROLLBACK` (2026-11-15): `20261115-60`, `-61`, asserzioni 22-25 del pgTAP del giro 2 | §8.1 | — |
| 4-ter | Tid | ✅ Q-2 applicata (`20261115-60`, `-61`), pgTAP `anagrafiche/test-tipi-indirizzo-proponibili-v1` verde (2026-11-15) | §8.1 | — |
| 4-quater | BE/FE | ✅ il caso «natura inesistente → `[]`» in `test_tipi_indirizzo_proponibili_db`, col gemello sul tipo di ruolo per id (2026-11-15) | §8.2 | — |
| 5 | chi chiude | ✅ archiviato in `work-done/` (2026-11-15) | — | — |

Decisioni aperte di Tid: nessuna (Q-2: `NULL` resta «tutti ammessi», ok di Tid del
2026-11-15). Lavoro fatto da committare: il test del §8.2 e l'archiviazione (sessione BE, 2026-11-15).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-15.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE al §7.
> **Origine:** richiesta di Tid del 2026-11-15: nel drawer del soggetto, in modifica, non c'è
> modo di creare un indirizzo partendo da uno che il soggetto ha già, per esempio duplicare la
> sede legale come indirizzo di spedizione cambiando solo il tipo.
> **Brief vicini verificati:**
> [brief-db-fornitore-privato-indirizzi](../work-in-progress/brief-db-fornitore-privato-indirizzi.md): tratta gli
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
| ~~`DETTAGLIO_NON_ATTIVO`~~ | ⚠️ superato (§5.4): lo stato non esiste nel modello, il motivo non si scrive. ~~la riga punta a un dettaglio spento: la riga nuova lo rifiuterebbe (`trgfn_child_requires_active_parent`)~~ |
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

### 5.1 Giro 1, fatto (team DB, 2026-11-15)

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| `fn_tipo_indirizzo_ammesso_per_ruolo(tipo ruolo, tipo, giorno)`: il predicato del ruolo, gemello di quello della natura, `BEGIN ATOMIC` | `20261114-84-create-fn-tipo-indirizzo-ammesso-per-ruolo` |
| `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` legge il predicato: stesse risposte, stesso codice, stessi valori | `20261114-85-update-trgfn-indirizzi-guard-tipo-ruolo-dal-predicato` |
| `fn_check_tipo_indirizzo_soggetto_su_contesto(natura, tipi presenti, tipo, giorno, soggetto)` e `fn_check_tipo_indirizzo_soggetto(soggetto, tipo)` | `20261114-86-create-fn-check-tipo-indirizzo-soggetto` |
| `fn_check_tipo_indirizzo_ruolo_su_contesto(tipo ruolo, tipi presenti, tipo, giorno, ruolo)` e `fn_check_tipo_indirizzo_ruolo(ruolo, istanza, tipo)` | `20261114-87-create-fn-check-tipo-indirizzo-ruolo` |
| `fn_crea_indirizzo_soggetto` chiama la check e solleva il primo motivo (campo `tipo_indirizzo_codice_interno`) | `20261114-88-update-fn-crea-indirizzo-soggetto-chiama-la-check` |
| `fn_crea_indirizzo_ruolo` idem, sulla chiave (ruolo, istanza) | `20261114-89-update-fn-crea-indirizzo-ruolo-chiama-la-check` |
| `fn_crea_indirizzi_soggetto` e `fn_crea_indirizzi_ruolo`: gli obbligatori col predicato (D-4) | `20261114-90-…-soggetto-obbligatori-dal-predicato`, `20261114-91-…-ruolo-obbligatori-dal-predicato` |
| `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE` e `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE` (`DATO_ERRATO`), frasi id 1492 e 1493 | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` |
| Il pgTAP del giro (30 asserzioni) | `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` |
| Due test riscritti sul contratto nuovo: il duplicato ora è il codice, non il 23505 | `test-fn-crea-indirizzo-soggetto.sql` (5), `test-indirizzi-singolare-e-plurale-v1.sql` (4) |
| Pagine `manual/` delle quattro madri e del guard del ruolo; guida *Gestione degli indirizzi* (R2, R5) | `docs/it/dbzero/anagrafiche/manual/`, `docs/it/guide/` |

**Le scelte fatte scrivendo:**

* **La check è divisa in due metà** (§12.6) già nel giro 1: il **contesto** (natura o tipo di
  ruolo, e i tipi presenti) lo legge la firma completa; i **motivi** di un tipo sono la metà
  `_su_contesto`, che non legge né il soggetto né il ruolo. Così i picker del giro 2 sulla natura e
  sul tipo di ruolo (soggetto e ruolo non ancora nati) la chiamano con i tipi presenti vuoti.
* **«Già presente» sul ruolo** si legge sulla chiave dei due indici: istanza
  `IS NOT DISTINCT FROM` quella data. Un tipo del ruolo non blocca la stessa istanza, e viceversa.
* **La delega fra le due metà è un'assegnazione** (`v_motivi := …_su_contesto(…)`), non un
  `RETURN …(…)`: `dbops.vw_funzioni_check_codici` riconosce solo `:=` e `||`. Con il `RETURN` il
  presidio `test-punti-canale-campo-v1` (2) vedeva le due singolari come siti ciechi (vicolo
  cieco provato e corretto).
* La reason_key del «già presente» è la stessa sui due layer
  (`anagrafiche.indirizzi.tipo_blocco.gia_presente`), i codici no: la frase dice «il soggetto» o
  «il ruolo».
* Un soggetto inesistente, dalla singolare, ora esce con `E_SOGGETTO_NOT_FOUND` (dalla check)
  invece della violazione di FK.
* Le plurali **non** incontrano il motivo nuovo: saltano i tipi presenti prima della singolare,
  come prima.

**Prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, 2026-11-15): estratto degli otto
changeSet eseguito per intero, catalogo identico dopo il `ROLLBACK`.

| pgTAP | Senza l'estratto | Con l'estratto |
| --- | --- | --- |
| `test-check-tipo-indirizzo-v1` (nuovo) | interrotto (le funzioni non ci sono) | 30 ok / 0 |
| `test-fn-crea-indirizzo-soggetto`, `test-indirizzi-singolare-e-plurale-v1` (riscritti) | 1 rosso ciascuno (il contratto nuovo) | tutti verdi |
| `test-fn-crea-indirizzi-ruolo-v1`, `test-istanza-dello-stesso-soggetto-v1`, `test-indirizzi-fallback`, `test-emittenti-fiscali`, `test-indirizzo-libero-due-forme-v1`, `test-cambio-natura-soggetto-v1` | verdi | verdi, invariati |
| presidi `dbops`: canale del campo, motivo nominato, valore atteso, check sotto JIT, riferimenti morti, corpo senza commenti, corpo leggibile; `script`: rubinetto, catalogo messaggi | verdi (il rubinetto ha il suo rosso dichiarato) | invariati |

**Mutazione**: senza `-90` e `-91` (le plurali di prima) diventano rossi il 20, il 21, il 28 e il
presidio 4: il pgTAP distingue davvero la finestra di validità degli obbligatori.
I due CSV: upsert di **tutte** le righe in una transazione annullata, verde; nessun `\r`, diff di
due righe per file.

⛔ **Non provati prima dell'apply:** le frasi dei due codici nuovi (i CSV non sono nell'estratto: il
pgTAP asserisce i codici, non le frasi, apposta) e il `rollback` dei changeSet (la prova estrae
solo i `changes`).

**Debito trovato (Q-1, decisa da Tid il 2026-11-15: si fa subito, §5.2).** Le frasi dei due codici del tipo non ammesso sono scritte sugli
id: `E_TIPO_INDIRIZZO_NON_PERMESSO` «Tipo indirizzo %s non permesso per tipo_ruolo_id %s
(soggetto_ruolo_id=%s)», `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` «… per il tipo soggetto %s
(soggetto_id=%s)». I due guard passano gli id; le check nuove passano le descrizioni (il tipo, il
tipo di ruolo o la natura) e l'id del ruolo o del soggetto, perché da qui in avanti la frase la
legge l'operatore. Proposta: riscrivere le due frasi senza nomi di colonna e coi due guard sulle
descrizioni, in un giro del brief (due righe di CSV, due corpi di guard). Da decidere: se e quando.

**Doc auto-generata**: va rigenerata dopo l'apply; le pagine `manual/` e la guida rimandano già
alle quattro funzioni nuove.

**Apply**: giro 1 applicato da Tid il 2026-11-15, pgTAP verdi.

### 5.2 Q-1, le due frasi del tipo non ammesso (team DB, 2026-11-15)

Decisa da Tid il 2026-11-15 («le riscriviamo subito»). Le due frasi perdono i nomi di colonna e
gli id, e passano a due valori, per descrizione, nell'ordine «chi non ammette», «quale
indirizzo». La stessa forma di `E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI`:

| Codice | Frase (id) | Valori |
| --- | --- | --- |
| `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` | «Il tipo soggetto %s non prevede l'indirizzo «%s».» (930) | la natura, il tipo |
| `E_TIPO_INDIRIZZO_NON_PERMESSO` | «Il ruolo %s non prevede l'indirizzo «%s».» (108) | il tipo di ruolo, il tipo |

Causa e soluzione riscritte per chi le legge: non nominano più le tabelle di configurazione.

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| Il guard del soggetto passa le due descrizioni; il contesto guadagna `campo` = `tipo_indirizzo_id` | `20261114-92-update-trgfn-indirizzi-soggetti-guard-tipo-indirizzo-frase` |
| Il guard del ruolo passa le due descrizioni (il `campo` c'era già) | `20261114-93-update-trgfn-indirizzi-guard-tipo-ruolo-frase` |
| Le due metà `_su_contesto` delle check: il motivo del tipo non ammesso porta gli stessi due valori | `20261114-94-…-soggetto-su-contesto-frase`, `20261114-95-…-ruolo-su-contesto-frase` |
| Le due righe di frase | `80_data/sql/config/messaggi_errore.csv` (id 108, 930) |
| Quattro asserzioni nuove (30-33: i valori dei due motivi, la frase intera dei due guard da un `UPDATE` che salta la madre); plan 34 | `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` |

Le descrizioni i guard le leggono solo nel ramo che rifiuta. Gli id restano nel contesto, per chi
diagnostica.

**Prova** (`scripts/prova_changeset.py`, scratch col giro 1 applicato, 2026-11-15), con
l'aggiornamento delle due frasi anteposto al pgTAP (i CSV non sono nell'estratto):

| pgTAP | Senza l'estratto | Con l'estratto |
| --- | --- | --- |
| `test-check-tipo-indirizzo-v1` | 30 ok / 4 rossi: le quattro asserzioni nuove | 34 ok / 0 |
| `test-catalogo-messaggi-errore-completo` | 1 rosso: frasi nuove con i guard vecchi (tre valori su due segnaposto) | verde |
| valore atteso, canale del campo, motivo nominato, `test-indirizzi-fallback`, `test-cambio-natura-soggetto-v1`, i due test delle singolari | verdi | verdi |

⭐ Il rosso del catalogo dei messaggi senza l'estratto dice che **frasi e corpi entrano
insieme**: un apply delle sole righe di CSV darebbe a quei guard una frase con un valore di
troppo. Upsert di tutte le righe del CSV in `ROLLBACK`: verde; nessun `\r`.

⛔ **Non provato:** il `rollback` dei changeSet.

**Apply**: Q-1 applicata da Tid il 2026-11-15, pgTAP verdi.

Il ripiego del BE (`error_messages_fallback.py`) ha già una frase generica, senza segnaposto, per i
due codici: non cambia.

### 5.3 Giro 2, fatto (team DB, 2026-11-15)

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| `fn_tipi_indirizzo_proponibili_natura(natura)` e `fn_tipi_indirizzo_proponibili_soggetto(soggetto)` | `20261114-96-create-fn-tipi-indirizzo-proponibili-soggetto` |
| `fn_tipi_indirizzo_proponibili_tipo_ruolo(tipo ruolo)` e `fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza)` | `20261114-97-create-fn-tipi-indirizzo-proponibili-ruolo` |
| Il pgTAP del giro (21 asserzioni) | `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` |
| La guida *Gestione degli indirizzi* (R6): da dove il form prende i tipi | `docs/it/guide/` |

**La forma.** `RETURNS TABLE (tipo_indirizzo_id, obbligatorio, ammesso, motivo_codice, reason,
reason_key, reason_valori, motivi)`, una riga per tipo di `config.tipi_indirizzi`, prima gli
ammessi e poi gli altri, per codice interno. `BEGIN ATOMIC`, `STABLE`, INVOKER.

* `ammesso` e il primo motivo vengono dalla metà `_su_contesto` della check della madre
  singolare (§5.1): il picker non scrive nessuna regola. Il contesto (natura o tipo di ruolo, tipi
  presenti) si legge una volta per chiamata (§12.6).
* `obbligatorio` è la lettura della plurale: riga obbligatoria della matrice che il predicato del
  guard ammette oggi. Una riga obbligatoria scaduta non è obbligatoria.
* Il primo motivo è appiattito come vuole il §12.2 (`reason`, `reason_key`, `reason_valori`), e in
  più `motivo_codice`, come `fn_nature_proponibili_soggetto`.
* Sulla **natura** e sul **tipo di ruolo** i tipi presenti sono nessuno: il soggetto o il ruolo non
  esistono ancora, e «già presente» non può comparire. Sono firme diverse, non un parametro
  facoltativo (§4.3).
* Sul **ruolo** l'istanza non ha `DEFAULT`: `NULL` vuol dire il ruolo, ed è un valore legittimo.
* Soggetto o ruolo inesistenti: nessuna riga.
* Nessuna `reason_key` nuova: sono quelle delle check (R-0).

**Prova** (`scripts/prova_changeset.py`, scratch con giro 1 e Q-1 applicati, 2026-11-15): estratto
eseguito per intero, catalogo identico dopo il `ROLLBACK`; `test-tipi-indirizzo-proponibili-v1`
interrotto senza l'estratto (le funzioni non ci sono), 21 ok / 0 con l'estratto. Ognuno dei due casi
del §3.1 è costruito su entrambe le matrici, e su ciascuno il codice del picker è confrontato con
quello che la madre singolare solleva (9, 10, 17), o la madre accetta ciò che il picker propone
(14, 21). Invariati e verdi: `test-check-tipo-indirizzo-v1`, i presidi `dbops` (check sotto JIT,
canale del campo, motivo nominato, riferimenti morti, corpo senza commenti, corpo leggibile) e il
rubinetto. Guardrail statici verdi.

⛔ **Non provati:** il `rollback` dei changeSet; il piano come applicazione (§13.1): il pgTAP lo
esercita da `zeroerp_app` quando lo lancia Tid; il picker legge nove tipi per chiamata.

**Prima corsa di Tid (dbdev, 2026-11-15, giro 2 applicato):** 19 ok, 2 rossi, i presidi 1 e 2.
Causa: per una `BEGIN ATOMIC` `pg_get_functiondef` stampa i nomi relativi al `search_path` della
sessione (§5c); da `zeroerp_app`, che ha `anagrafiche` nel path, la chiamata alla check esce senza
schema e il `LIKE '%anagrafiche.fn_check_…'` non la trova. Nella prova, da owner, il path era un
altro e i due presidi passavano: **vicolo cieco della prova da owner**. Corretti: il legame si
asserisce su `pg_depend` (la funzione dipende dalla check), indipendente dal path; le quattro
dipendenze lette su dbdev ci sono.

**Apply**: giro 2 applicato da Tid il 2026-11-15; pgTAP verdi alla seconda corsa, coi presidi 1-2
riscritti.

### 5.4 Giro 3, fatto (team DB, 2026-11-15)

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| `fn_check_copia_indirizzo_soggetto(indirizzo)`: il motivo di riga | `20261115-34-create-fn-check-copia-indirizzo-soggetto` |
| `fn_check_copia_indirizzo_ruolo(indirizzo)`: la gemella | `20261115-35-create-fn-check-copia-indirizzo-ruolo` |
| `fn_indirizzo_elemento_da_riga(…)`: l'elemento ricostruito dalla riga, BB dei due verbi | `20261115-36-create-fn-indirizzo-elemento-da-riga` |
| `fn_copia_indirizzo_soggetto(soggetto, indirizzo, tipi[]) → bigint[]` | `20261115-37-create-fn-copia-indirizzo-soggetto` |
| `fn_copia_indirizzo_ruolo(ruolo, indirizzo, tipi[]) → bigint[]` | `20261115-38-create-fn-copia-indirizzo-ruolo` |
| `vw_indirizzi_soggetti_azioni`: la superficie di `COPIA_INDIRIZZO_SOGGETTO` | `20261115-39-create-vw-indirizzi-soggetti-azioni` |
| `vw_indirizzi_ruolo_azioni`: la superficie di `COPIA_INDIRIZZO_RUOLO` | `20261115-40-create-vw-indirizzi-ruolo-azioni` |
| `E_INDIRIZZO_SOGGETTO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_NON_TROVATO` (`NON_TROVATO`), `E_INDIRIZZO_COPIA_NESSUN_TIPO` (`CONFLITTO_STATO`); frasi 1494-1496, senza segnaposto | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` |
| Le due azioni nel registro (id 5, 6) | `80_data/sql/config/azioni_riga.csv` |
| Il pgTAP del giro (26 asserzioni) | `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` |
| La soglia del rubinetto, da 56 a 58 (i due verbi sono siti nuovi dell'helper) | `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` |
| La guida *Gestione degli indirizzi* (R2): la copia | `docs/it/guide/` |

**Le scelte fatte scrivendo:**

* ⚠️ **Il motivo `DETTAGLIO_NON_ATTIVO` del §4.5 non c'è.** Il modello non ammette una riga che
  punta a un dettaglio spento: la rifiuta `trgfn_child_requires_active_parent`, e lo spegnimento di
  un dettaglio che ha indirizzi lo rifiuta `trgfn_prevent_deactivate_if_children` (le due tabelle
  degli indirizzi non hanno `attivo`: ogni figlia blocca). Un motivo per uno stato che non esiste
  non si scrive. Resta un motivo solo, `NESSUN_TIPO_PROPONIBILE`, letto dal **picker** del giro 2
  (nessun tipo ammesso): la regola non si riscrive.
* **Il codice di quel motivo è nuovo** (`E_INDIRIZZO_COPIA_NESSUN_TIPO`, lo stesso sui due layer:
  la frase non nomina il layer). Il §12.5.2 vuole i motivi su codici a catalogo; qui la madre che
  lo solleva è nuova, e nessuna strada rifiutava già quello stato.
* **Le viste di riga sono viste di azioni** (`vw_indirizzi_soggetti_azioni`,
  `vw_indirizzi_ruolo_azioni`), come `vendite.vw_listini_versioni_azioni`: l'id della riga, le
  chiavi del padre e le due colonne del motivo. La domanda del §4.5 («`vw_indirizzi_resolved_soggetto`
  o una nuova?») ha la risposta «una nuova»: la catena `vw_indirizzi_resolved_*` la leggono altri,
  unisce i due layer e non è `security_invoker`, mentre il registro vuole la superficie
  `security_invoker`. Le colonne dell'indirizzo (anche quelle della forma estera) il BE le prende
  dalla catena, per id: nessuna join si ricopia (R-3).
* **L'elemento dalla riga è un BB** (`fn_indirizzo_elemento_da_riga`): i due verbi lo costruiscono
  allo stesso modo, seconda occorrenza. Dal dettaglio solo l'id; dalla forma libera le otto colonne
  valorizzate. Le copie nazionale ed estera arrivano con tutte le colonne uguali alla sorgente (3, 4).
* **Il controllo del tipo lo fa la singolare**, non il verbo: il verbo costruisce l'elemento col
  tipo e chiama `fn_crea_indirizzo_*`, che risolve il codice, chiama la check del tipo e passa dai
  guard. Un tipo ripetuto nell'elenco è un tipo già presente al secondo giro. Tutto o niente: una
  funzione, un'istruzione.

**Prova** (`scripts/prova_changeset.py` col `search_path` del runner, scratch, 2026-11-15): estratto
dei sette changeSet eseguito per intero, catalogo identico dopo il `ROLLBACK`;
`test-copia-indirizzo-v1` 26 ok / 0. Con le righe nuove dei tre CSV anteposte al pgTAP (l'estratto
non le porta): `config/test-azioni-riga-registro-v1` da 4 rossi (le due righe puntano a oggetti che
senza l'estratto non ci sono) a 8 ok; verdi i presidi `dbops` (canale del campo, motivo nominato,
valore atteso, riferimenti morti, corpo senza commenti, corpo leggibile, check sotto JIT),
`rls/test-rls-viste-security-invoker`, il catalogo dei messaggi, i pgTAP dei giri 1 e 2. Il
rubinetto era rosso (56 attese, 58 trovate): soglia portata a 58, verde. Upsert di tutte le righe
dei tre CSV in `ROLLBACK`, verde; nessun `\r`. Guardrail statici verdi.

Due difetti del pgTAP trovati nella prova e corretti prima della consegna: la rilettura delle righe
nuove nella stessa istruzione che le scrive (non le vede: ora in due istruzioni), e un rifiuto
provato dopo che il soggetto aveva già tutti i tipi (parlava prima `E_INDIRIZZO_COPIA_NESSUN_TIPO`:
riordinato).

⛔ **Non provati:** il `rollback` dei changeSet; le frasi dei tre codici nuovi a video.

**Apply**: giro 3 applicato da Tid il 2026-11-15, pgTAP verdi.

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
  Dopo l'apply del giro 3 (§5.4) le firme sono:
  `SELECT anagrafiche.fn_copia_indirizzo_soggetto(%s::uuid, %s, %s::text[])` e
  `SELECT anagrafiche.fn_copia_indirizzo_ruolo(%s, %s, %s::text[])`, ritorno `bigint[]` (gli id
  nell'ordine dei tipi). Una sola `SELECT`: è già tutto o niente. Codici da mappare:
  `E_INDIRIZZO_SOGGETTO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_NON_TROVATO` (404),
  `E_INDIRIZZO_COPIA_NESSUN_TIPO` (409), e quelli della singolare (§5.1). Il permesso lo controlla
  la view, come per «Aggiungi».
* **R-2 (BE)** — ⏭️ si può fare dopo l'apply del giro 2 (§5.3), senza aspettare il giro 3. Il lookup dei tipi del drawer e dei form di creazione (soggetto e assegnazione del
  ruolo) legge i picker del §4.3 e §4.6; si ritirano `LookupRepository.list_matrice_indirizzi` e la
  lettura gemella della matrice del ruolo (regola del 2: la copia divergente si toglie nello stesso
  giro), dopo aver cercato ogni altro chiamante. Le quattro funzioni, tutte
  `SELECT … FROM fn(…)` (sono `RETURNS TABLE`):

  | Dove | Funzione |
  | --- | --- |
  | drawer del soggetto, «Aggiungi» e i tipi di «Copia come…» | `anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(soggetto_id uuid)` |
  | form di creazione del soggetto (la natura scelta nel form) | `anagrafiche.fn_tipi_indirizzo_proponibili_natura(tipo_soggetto_dettaglio_id bigint)` |
  | drawer in contesto ruolo (istanza `NULL` = il ruolo) | `anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(soggetto_ruolo_id bigint, istanza_utility_id bigint)` |
  | assegnazione del ruolo (il tipo di ruolo scelto) | `anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(tipo_ruolo_id integer)` |

  Colonne: `tipo_indirizzo_id`, `obbligatorio`, `ammesso`, `motivo_codice`, `reason`,
  `reason_key`, `reason_valori`, `motivi`. Il codice del tipo (`codice`, `codice_interno`) e la
  descrizione si prendono da `config.tipi_indirizzi` con un join su `tipo_indirizzo_id`. Un tipo non
  ammesso resta nell'elenco, spento col tooltip dalla `reason_key` e dai `reason_valori` (R-4).
  Con una natura o un tipo di ruolo senza matrice il picker ammette tutti i tipi: il pulsante
  «Aggiungi» resta.
* **R-3 (BE)** — le liste `GET soggetti/<id>/indirizzi/` e `GET ruoli/<id>/indirizzi/` leggono le
  viste del §4.5 e §4.6 e portano `copia_blocco_reason` / `copia_blocco_reason_key`. Dopo l'apply
  del giro 3 (§5.4) le superfici sono viste di azioni, da unire per id alla catena che porta le
  colonne dell'indirizzo:
  * soggetto: `anagrafiche.vw_indirizzi_resolved_soggetto v LEFT JOIN
    anagrafiche.vw_indirizzi_soggetti_azioni a ON a.indirizzo_soggetto_id = v.indirizzo_id`. Così
    `SoggettiRepository.get_soggetto_indirizzi` smette di essere SQL scritto nel BE, e la lista
    guadagna i campi della forma estera;
  * ruolo, sui livelli istanza e ruolo della cascata: `vw_indirizzi_resolved_ruolo v LEFT JOIN
    anagrafiche.vw_indirizzi_ruolo_azioni a ON a.indirizzo_id = v.indirizzo_id`; sul livello
    soggetto della cascata la vista del soggetto, come sopra (l'azione di quelle righe è la copia
    del soggetto).
  I nomi delle due azioni e delle colonne stanno in `config.azioni_riga`
  (`COPIA_INDIRIZZO_SOGGETTO`, `COPIA_INDIRIZZO_RUOLO`).
* **R-4 (FE)** — `IndirizziSoggettoDrawer`: le azioni della card passano al kebab `RowActionsMenu`
  («Cambia», «Copia come…» spenta col motivo); «Copia come…» apre la scelta dei tipi dal picker, gli
  esclusi visibili col loro motivo; dopo il salvataggio si ricarica la lista. «Aggiungi» legge lo
  stesso picker, e il pulsante resta quando la natura non ha matrice. In contesto ruolo la stessa
  azione, col verbo del ruolo sulle righe del ruolo e quello del soggetto sulle righe della cascata
  (§4.6, ultimo punto). Il drawer è riusato da
  `DocumentoIndirizziDrawer` in modalità selezione: lì l'azione vale uguale, il gesto è sull'anagrafica.
* **R-5 (BE)** — i codici nuovi (§4.2, §4.4, §4.6): `error_policies_generated.py` rigenerato col DB
  allineato a git, il ripiego in `error_messages_fallback.py`; le `reason_key` nei locales FE.

**Richieste del giro 1, subito dopo l'apply** (non aspettano i giri 2 e 3; scritte dal team DB il
2026-11-15):

* **R-0 bis (FE, giro 3)** — una chiave i18n in più, il tooltip di «Copia come…» spenta:
  `anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile` — «Non c'è un altro tipo di
  indirizzo in cui copiarlo»; senza valori.
* **R-0 (FE)** — tre chiavi i18n in `it.json` ed `en.json`, emesse dalle check del §5.1 e lette
  dai picker e dal tooltip di «Copia come…»; `check-i18n-keys` rifiuta il commit DB finché
  mancano:
  * `anagrafiche.indirizzi.tipo_blocco.gia_presente` — «Il soggetto (o il ruolo) ha già un
    indirizzo di questo tipo»; valore `{0}`: il tipo;
  * `anagrafiche.indirizzi.tipo_blocco.non_ammesso_dalla_natura` — «Il tipo soggetto {0} non
    prevede l'indirizzo «{1}»»; valori, in quest'ordine: la natura, il tipo (§5.2);
  * `anagrafiche.indirizzi.tipo_blocco.non_ammesso_dal_ruolo` — «Il ruolo {0} non prevede
    l'indirizzo «{1}»»; valori, in quest'ordine: il tipo di ruolo, il tipo (§5.2).
* **R-6 (BE)** — il contratto del «tipo già presente» cambia dall'apply del giro 1, ed è il DB a
  cambiare per primo:
  * `backend/apps/core/services/error_policies_generated.py`: rigenerato col DB allineato, con
    `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE` ed `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`
    (`DATO_ERRATO`, campo `tipo_indirizzo_codice_interno`); il ripiego in
    `error_messages_fallback.py`. Fino ad allora il guardrail
    `apps/core/tests/test_error_codes_db_policy_guardrail.py` è rosso per due codici senza policy;
  * `backend/apps/anagrafiche/tests/db/test_creazioni_dalle_madri_db.py`, riga 250
    (`test_un_indirizzo_singolo_dalla_madre`): si aspetta `E_ANAG_DUPLICATO` sul secondo indirizzo
    dello stesso tipo, ora riceve `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`;
  * `backend/apps/anagrafiche/services/soggetti_service.py` (righe 306-310 e 1080-1082): il
    `create_with_dedup` con «Indirizzo duplicato per questo soggetto.» intorno alle due singolari
    non scatta più per il tipo già presente (arriva un `P0001` col codice, non un `23505`). Resta
    solo per la corsa fra due scritture: il team BE decide se tenerlo o ritirarlo, dopo aver
    cercato gli altri chiamanti.

## 8. Q-2, richiesta al team DB dalla verifica BE (2026-11-15)

> **Chi scrive:** sessione di verifica BE/FE (`dev/backend-tid`), 2026-11-15.

**Il difetto.** `anagrafiche.fn_tipi_indirizzo_proponibili_natura` e
`anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo` non distinguono un id che **non esiste** da
una natura (o un tipo di ruolo) **senza matrice**: tutte e due le forme danno ogni tipo ammesso.
Le gemelle sul salvato non lo fanno: soggetto o ruolo inesistenti, nessuna riga. Fatto datato,
DB di sviluppo del 2026-11-15: `fn_tipi_indirizzo_proponibili_natura(987654321)` → 9 righe, 9
ammesse; `fn_tipi_indirizzo_proponibili_tipo_ruolo(987654)` → 9 su 9; `NULL` → 9 su 9;
`fn_tipi_indirizzo_proponibili_ruolo(987654321, NULL)` → 0 righe.

**Dove si vede.** `GET /core/lookup/tipi-soggetto-dettaglio/<id>/indirizzi/` con un id
inesistente risponde «tutti i tipi ammessi»; fino al 2026-11-15 (lettura della matrice) rispondeva
`[]`. Il gemello per codice del tipo di ruolo non ne soffre solo perché il BE, che deve comunque
risolvere il codice in id, dà `[]` a un codice ignoto (`list_tipi_indirizzo_proponibili_tipo_ruolo`).
Il BE **non** aggiunge un controllo di esistenza della natura: la regola «inesistente = nessuna
riga» è del picker, come lo è già per soggetto e ruolo.

**La richiesta.** Un id non `NULL` che non esiste in `config.tipi_soggetto_dettaglio` (o in
`config.tipi_ruoli`): nessuna riga, come le gemelle; `NULL` resta «nessuna matrice, tutti
ammessi» se il team DB lo vuole tenere per il form senza natura scelta. Con il pgTAP del caso.
Ricaduta BE: nessuna modifica di codice; il controllo di `list_tipi_indirizzo_proponibili_tipo_ruolo`
resta (serve a risolvere il codice), e il test DB `test_tipi_indirizzo_proponibili_db` prende un
caso «natura inesistente → `[]`» quando il DB è applicato.

### 8.1 Q-2, fatta (team DB, 2026-11-15)

Decisione di Tid (2026-11-15): `NULL` resta «nessuna matrice, tutti ammessi», come il guard della
singolare: è il form senza natura (o senza tipo di ruolo) scelto.

* `20261115-60` riscrive `anagrafiche.fn_tipi_indirizzo_proponibili_natura` e `20261115-61`
  riscrive `anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo`: un id non `NULL` che non c'è in
  `config.tipi_soggetto_dettaglio` (o in `config.tipi_ruoli`) non dà righe. Il corpo è quello di
  `20261114-96` / `-97`, uguale al vivo, con in più la sola `WHERE`; i COMMENT dicono il caso
  nuovo. Attributi invariati (default; nessun `COST`, `ROWS` o `SET` da ripetere).
* Il filtro sta nel **picker**, non nella check: la check giudica un tipo su un contesto, e il
  guard la chiama con una natura che esiste per FK. La regola «inesistente = nessuna riga» è del
  picker, come per le gemelle sul salvato.
* pgTAP `anagrafiche/test-tipi-indirizzo-proponibili-v1`, plan 25: 22 e 24 l'id inesistente
  (costruito come `max(id) + 1`, non supposto), 23 e 25 il `NULL` che resta «tutti ammessi».
* Prova (`scripts/prova_changeset.py`, scratch, 2026-11-15): con l'estratto 25 ok su 25. Senza,
  un solo rosso, il 24: il `-60` era già applicato sullo scratch alle 16:21, quindi il 22 era già
  verde. Catalogo identico prima e dopo.
* Guida *Gestione degli indirizzi*: invariata, rimanda alla doc auto-generata dei picker.
* Applicata da Tid il 2026-11-15, pgTAP del giro verde.

### 8.2 La ricaduta BE, fatta (sessione BE, 2026-11-15)

`apps/anagrafiche/tests/db/test_tipi_indirizzo_proponibili_db.py` prende due casi, sulla porta
del BE (`LookupRepository.list_tipi_indirizzo_proponibili`): `test_natura_inesistente` (`"natura"`)
e `test_tipo_di_ruolo_inesistente` (`"tipo_ruolo"` per id, il gemello del `-61`). L'id si
costruisce come `max(id) + 1`, come nel pgTAP. Nessuna modifica di codice. Con
`ZEROERP_TEST_DB_E2E=1` sul DB di sviluppo: 9 test, verdi.
