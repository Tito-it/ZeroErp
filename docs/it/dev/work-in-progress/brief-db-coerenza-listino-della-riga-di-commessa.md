# Brief DB — Il listino citato da una riga di commessa: stesso emittente, versione giusta, in vigore

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-09. **A chi:** team DB.
> **Origine:** debito emerso lavorando
> [brief-db-riga-listino-propagata-dalla-commessa](../work-done/brief-db-riga-listino-propagata-dalla-commessa.md)
> (§6, D-3). Quel brief fa scrivere `listino_riga_id`; questo dice che cosa la
> colonna può contenere.
> **Stato:** 🟡 aperto. La metà «riga di listino ↔ versione, articolo, unità di misura» è
> **fatta e applicata** il 2026-10-15 (§5); secondo (§6, §7) e terzo giro (§8, la matrice
> categoria → listino) applicati il 2026-10-16, pgTAP verdi. **Lato DB chiuso**; resta il BE (§9).

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: Tid, con l'archiviazione.** Lato DB chiuso (tre giri applicati su dbdev, pgTAP verdi); ✅ i due passi BE del §9 fatti e committati il 2026-10-16 (§9.1).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ BE | Rigenerato `error_policies_generated.py`: i sette codici, più i loro ripieghi | §9.1 | — |
| 2 | ✅ BE | Fixture di `test_prezzo_riga_commessa_db` sul builder `dbops.fn_pgtap_crea_commessa_attivita`, tolta la copia della chiamata alla madre | §9.1 | — |
| 3 | **Tid** | Archiviazione in `work-done/` | — | 1, 2 |

**Decisioni aperte di Tid: nessuna.** Prese: D-1 (2026-10-15); D-2…D-4 e D-5 = opzione B sulla matrice (2026-10-16).
✅ **Committato** su `dev/db-tid` il 2026-10-16: i tre giri (§5, §7, §8) e questo documento. ✅ **Committato** su `dev/backend-tid` il 2026-10-16: il giro BE del §9.1. Niente da committare.

## 1. Il problema

Su `vendite.commesse_attivita` (e su `vendite.attivita_fatturabili`, che la copia)
nessuna regola lega la provenienza del prezzo alla commessa:

| Colonna | Cosa garantisce oggi | Cosa manca |
| --- | --- | --- |
| `listino_versione_id` | la FK: la versione esiste | che il listino sia dell'**emittente della commessa** |
| `listino_riga_id` | la FK: la riga esiste | che la riga appartenga a **`listino_versione_id`** (e quindi allo stesso listino) |

Contratto letto il 2026-10-09: nessun trigger su queste due tabelle legge
`listino_versione_id` o `listino_riga_id`, e nessun `CHECK` li confronta. Il
resolver (`fn_resolve_prezzo_listino_v2[_esito]`) sceglie i listini
dell'emittente che gli si passa, ma la madre del push e l'`UPDATE` diretto del BE
(riallinea, sblocca) scrivono quello che ricevono.

⚠️ **E nemmeno lo stato della versione.** I rami del resolver che cercano la
versione da soli la prendono solo `ATTIVA`/`CHIUSA` («Bug A fix: esclude BOZZA»).
Il **percorso rapido** (`p_listino_versione_id_preferito`, usato dal BE in
`pricing_repository`) legge invece la versione che gli si passa **senza guardarne
lo stato**: un prezzo può venire da una versione in `BOZZA`. Su una versione in
`BOZZA` sia `trgfn_listini_righe_guard_stato` sia il guard dei componenti
(`trgfn_listini_righe_comp_guard_immutabilita_v5`) lasciano modificare tutto, per
scelta. Una riga di commessa che cita una riga di una versione in `BOZZA` ha quindi
un prezzo **non riproducibile**, qualunque cosa dica il legame.

## 2. Perché conta: il guard dei listini diventa cieco

`vendite.trgfn_listini_righe_guard_stato` decide se una riga di listino è
«propagata» con un `EXISTS` su `commesse_attivita` e `attivita_fatturabili`. È
`SECURITY INVOKER`, e le due tabelle hanno la RLS per emittente
(`rls_*_ef_whitelist`, attraverso la commessa). Il listino ha
`emittente_soggetto_ruolo_id NOT NULL`, con RLS anch'essa per emittente.

* Se la riga di commessa cita **sempre** un listino del **proprio** emittente, chi
  vede il listino vede anche tutte le commesse che lo citano: il guard vede tutto.
* Se il modello ammette una riga di commessa dell'emittente Y che cita un listino
  dell'emittente X, chi lavora solo su X **non vede** quella commessa. Il guard
  trova zero righe, giudica la riga «non propagata» e la lascia modificare.
  È la forma «il guard giudica su un'assenza»: rifiuta solo per chi vede tutti e
  due gli emittenti.

Oggi il modello lo ammette, perché manca la regola del §1.

## 3. Proposta (da decidere)

**A — la regola sulla riga (raccomandata).** Un guard `BEFORE INSERT OR UPDATE OF
listino_versione_id, listino_riga_id` su `commesse_attivita` e
`attivita_fatturabili`:
1. se `listino_riga_id` è valorizzato, la riga appartiene a `listino_versione_id`,
   e quest'ultimo è valorizzato;
2. se `listino_versione_id` è valorizzato, il listino è dell'emittente della
   commessa;
3. se `listino_versione_id` è valorizzato, la versione **non è in `BOZZA`**: una
   riga di commessa non prende il prezzo da un listino che non è in vigore.
   (Da decidere a parte se anche il percorso rapido del resolver debba rifiutare
   una `BOZZA`, o se lì serva a un'anteprima legittima del contratto in bozza:
   la regola 3 vale comunque sulla riga di commessa.)

Chiude tutti e due i problemi **per costruzione**: con la regola, la cecità del §2
non ha un caso da cui partire. Copre ogni percorso (push, batch, riallinea, sblocca,
emissione), non solo la madre.
⚠️ Va letto sotto RLS: la lettura del listino dentro il guard deve rispondere
anche quando il chiamante non lo vede (`SECURITY DEFINER` di lettura, decisione
sul **valore**). Un listino invisibile non può valere come «coerente».

**B — solo il guard dei listini in `SECURITY DEFINER`.** L'`EXISTS` vedrebbe tutte
le righe. Chiude il §2 ma lascia la provenienza incoerente del §1. Insieme ad A è
difesa in profondità; da solo non basta.

## 4. Da censire prima di scrivere

* i percorsi che scrivono `listino_versione_id`/`listino_riga_id` (madre del push,
  `fn_accredita_riga_reso`, `fn_aggiungi_onere_commessa`, emissione, `UPDATE` del BE
  in `commesse_repository`);
* le righe di commessa esistenti che violerebbero la regola. Il progetto non è in
  produzione, ma un guard nuovo su `UPDATE` rifiuterebbe anche un riallineamento di
  una riga già incoerente;
* i pgTAP che costruiscono righe di commessa con un listino di un altro emittente,
  se ce ne sono.

## 5. Primo giro — fatto il 2026-10-15

Nato da una richiesta del team BE sul builder pgTAP (§5.3). Nell'analisi è emersa la regola
del §3.A punto 1, e Tid l'ha voluta nello stesso giro. ⚠️ Il giro è stato scritto **senza**
aver letto questo brief: lo si è ritrovato dopo l'apply. Le differenze rispetto al §3 sono
dichiarate al §5.2.

**Applicato su dbdev** (`databasechangelog`, 2026-10-15) e trigger di blocco generato. pgTAP
verdi, nessuna regressione (corsa di Tid).

### 5.1 La decisione

**D-1 (Tid, 2026-10-15).** Domanda: versione e riga di listino di una riga di commessa possono
divergere di proposito? Risposta: **no**. Una riga di listino è *il prezzo di un articolo, in
un'unità di misura, dentro una versione*: chi la cita deve avere lo stesso articolo, la stessa
unità di misura e, se porta la versione, quella versione.

Verificato prima di scrivere, sul contratto:
* il **risolutore** cerca la riga sempre con `listino_versione_id`, `articolo_id` e `uom_id` della
  riga: è coerente per costruzione;
* il **kit** (`LISTINO_BUNDLE`) non restituisce una riga di listino, quindi non fa eccezione;
* chi scrive le colonne a mano: la madre del push e l'`UPDATE` diretto del riallineamento nel
  backend (`commesse_repository`, che scrive anche `attivita_fatturabili`). Per questo la regola
  sta sulla **tabella** e non nella madre;
* su dbdev, il 2026-10-15, nessuna riga cita una riga di listino. È un fatto datato, non un motivo.

### 5.2 Che cosa c'è

| changeSet / file | Cosa |
| --- | --- |
| `20261015-20` | `vendite.fn_listino_riga_coerente(riga, articolo, uom, versione)`: predicato `SECURITY DEFINER`, `search_path` da `pg_catalog`. Legge `listini_righe` senza la RLS di chi scrive (il §3.A «decisione sul valore»). Riga NULL → `true`; versione NULL → non confrontata |
| `20261015-21` | `vendite.trgfn_attivita_guard_listino_riga`: solleva `E_ATTIVITA_LISTINO_RIGA_INCOERENTE` (TECNICO, nessun bersaglio: la riga di listino la scrive il programma). La versione si legge per nome da `to_jsonb(NEW)`: `attivita_fatturabili` non ce l'ha |
| `20261015-22` | Montato su `commesse_attivita` e `attivita_fatturabili`, **AFTER** `INSERT OR UPDATE`, per riga |
| `automation_lock_columns.csv` | `listini_righe.articolo_id`, `uom_id` e `listino_versione_id` immutabili **sempre** (`E_LISTINO_RIGA_IDENTITA_IMMUTABILE`). È il lato del padre: una riga citata in `BOZZA` poteva cambiare articolo e rendere incoerenti le righe che la citano. Il backend li trattava già così (`RIGA_UPDATE_COLUMNS`) |
| `codici_errore.csv`, `messaggi_errore.csv` | i due codici (id messaggio 1321, 1322) |
| `db/pgtap/vendite/test-guard-listino-riga-coerente-v1.sql` | 10 casi: forma, coerente, articolo, versione e unità di misura diversi, versione tolta, attività fatturabile, blocco di colonna |
| `manual/` | pagine nuove per il predicato e per il guard; aggiornate quelle di `listini_righe`, `commesse_attivita` e `attivita_fatturabili` |

**Differenze rispetto al §3.A:**
* oltre all'appartenenza alla versione si controllano anche **articolo e unità di misura**;
* **AFTER senza `OF`** al posto di `BEFORE … OF`: giudica la riga finale, anche quando una
  colonna la cambia un altro trigger (linee-guida-trigger, «UPDATE OF»). In `UPDATE` il corpo
  esce subito se nessuna delle quattro colonne cambia;
* la riga di listino **senza versione è oggi lecita**, mentre il punto 1 del §3.A la voleva
  vietata: vedi D-2.

### 5.3 Il builder pgTAP (richiesta del team BE)

`dbops.fn_pgtap_crea_commessa_attivita` (`20261015-23`, DROP + CREATE) accetta `p_articolo_id`,
`p_listino_versione_id` e `p_listino_riga_id`, tutti in coda e facoltativi. Dal guard A-10 un
articolo usato non cambia più i flag, e quello costruito dal builder era già usato quando il
test lo riceveva. Due fixture avevano ricopiato la chiamata alla madre.
* Confine scritto nel COMMENT: il builder decide il contesto, il chiamante l'articolo e la
  provenienza del prezzo, tutto il resto passa dalla madre.
* La pgTAP gemella `test-riga-listino-propagata-dalla-commessa-v1` usa ora il builder.
* La pgTAP del builder passa da 6 a 11 casi.
* **Resta al BE**: la copia in `test_prezzo_riga_commessa_db` (passo 2 del blocco in cima).

## 6. Secondo giro — deciso il 2026-10-16 (scritto: §7)

**D-2 e D-3 non sono scelte (Tid, 2026-10-16): discendono da D-1.** Se la provenienza del prezzo
non può contraddire la riga, non può nemmeno essere incompleta (D-2) né venire da un listino
che la commessa non può usare (D-3). Vanno solo fatte.

* **D-2. Una riga di listino porta la sua versione** (sulla commessa).
  `CHECK (listino_riga_id IS NULL OR listino_versione_id IS NOT NULL)` su `commesse_attivita`.
  Il risolutore le dà sempre insieme. Su `attivita_fatturabili` non si applica, perché la
  tabella non porta la versione. ⚠️ Il predicato del §5 oggi non confronta una versione NULL: col
  CHECK quel ramo resta solo per `attivita_fatturabili`.
* **D-3. Il listino è dell'emittente della commessa** (§3.A punto 2). Nello stesso predicato
  `SECURITY DEFINER` (`vendite.fn_listino_riga_coerente`) o in uno gemello. Chiude per
  costruzione la cecità del §2.
* **D-4. Mai un prezzo da una versione in `BOZZA`** (Tid, 2026-10-16). Due punti:
  1. **il risolutore** (`fn_resolve_prezzo_listino_v2[_esito]`): il percorso rapido
     (`p_listino_versione_id_preferito`) non deve più accettare una versione in `BOZZA`. Oggi la
     legge senza guardarne lo stato. Da decidere scrivendo: un esito d'errore che dice il
     perché, non un ripiego silenzioso allo stadio 2, che nasconderebbe il chiamante sbagliato;
  2. **la riga di commessa**: `listino_versione_id` non punta a una versione in `BOZZA`. Conta
     soprattutto per le righe scritte direttamente sulla commessa (oneri, righe a mano); quelle
     che arrivano da preventivi, ordini e altri documenti hanno il prezzo del documento. La
     regola sulla tabella vale comunque per tutte.

  **L'opzione «anche bozza»** (un parametro esplicito del risolutore) **non si aggiunge ora**.
  Censito il 2026-10-16: dal backend il percorso rapido lo chiamano contratti e offerte, che
  prendono la versione da `vendite.fn_documento_listino_operativo`. È la versione fissata in
  testata oppure quella in vigore, e la `BOZZA` è già esclusa («non è operativa»). Nessun
  chiamante oggi ha bisogno di una bozza. L'opzione nasce col primo che la chiede davvero, per
  esempio un'anteprima mentre si scrive il listino, e con il suo caso d'uso scritto.
* **B del §3** (guard dei listini in `SECURITY DEFINER`): resta difesa in profondità. Con D-3
  diventa superflua per la cecità del §2, ma non la contraddice. Si valuta scrivendo.

## 7. Secondo giro — scritto il 2026-10-16

### 7.1 Che cosa c'è

| changeSet / file | Cosa |
| --- | --- |
| `20261016-01` (`00_schema`) | D-2: `CHECK chk_commesse_attivita_listino_riga_con_versione` su `commesse_attivita`. preCondition HALT sulle righe che lo violerebbero |
| `20261016-02` | `vendite.fn_check_listino_provenienza(commessa, articolo, uom, versione, riga)` → codice del primo motivo o NULL: riga incoerente (D-1), listino di un altro emittente (D-3), versione in `BOZZA` (D-4). `SECURITY DEFINER`, `search_path` da `pg_catalog`. Firma, RETURNS e DECLARE con `%TYPE` |
| `20261016-03` | il guard `trgfn_attivita_guard_listino_riga` legge la check e solleva il codice; giudica anche la riga con la **sola versione** (emittente e bozza); ritira `vendite.fn_listino_riga_coerente` del primo giro (un solo lettore) e la sua pagina `manual/` |
| `20261016-04` | D-4 nel risolutore: il percorso rapido con una versione in `BOZZA` dà l'esito `E_PREZZO_LISTINO_VERSIONE_BOZZA` (NON_ESEGUIBILE). Corpo dal `20260928-41`, verificato uguale al vivo (md5 di `prosrc`) |
| `20261016-05` | builder pgTAP: le tre colonne della riga di listino in variabili `%TYPE` invece di un `record` (regola di casa; nessun cambio di comportamento) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`, `E_ATTIVITA_LISTINO_VERSIONE_BOZZA` (TECNICO, frasi chiuse), `E_PREZZO_LISTINO_VERSIONE_BOZZA` (NON_ESEGUIBILE); id messaggio 1323–1325. Nota di `E_ATTIVITA_LISTINO_RIGA_INCOERENTE` aggiornata |
| `test-guard-listino-riga-coerente-v1.sql` | da 10 a 15 casi: CHECK D-2, emittente diverso (con la riga e con la sola versione), versione in bozza, risolutore con versione preferita in bozza e attiva. L'altra azienda si costruisce coi builder atomici prima del contesto |
| `manual/` | nuova `fn_check_listino_provenienza`; aggiornate guard, risolutore (esito), `commesse_attivita`, `attivita_fatturabili` |

### 7.2 Verificato prima di scrivere

* **Chi scrive versione e riga di listino** (D-2): il risolutore le restituisce insieme; il
  riallineamento del backend le scrive insieme dal risolutore (`provenienza_da_resolver`); il
  prezzo manuale le azzera entrambe; il push scrive la sola versione; oneri e rettifiche
  nessuna delle due.
* **Il percorso rapido** (D-4): lo chiamano solo `contratti_service` e `offerte_service`, con la
  versione di `vendite.fn_documento_listino_operativo`, che esclude già la bozza; nessuna
  funzione DB lo usa; l'endpoint pubblico dei prezzi non lo espone. Nessun chiamante cambia
  comportamento.
* **Dati** (dbdev, 2026-10-16, fatti datati): nessuna riga di commessa porta una versione di
  listino; nessuna violerebbe le tre regole.

### 7.2-bis Prova pre-apply (2026-10-16)

SQL estratto dei cinque changeSet e righe dei CSV in una transazione annullata sullo scratch
`zeroerp_ruoli` (che ha già il primo giro), fuso orario ostile, come proprietario:
* `plpgsql_check` sulle quattro funzioni: nessun errore. Tre avvisi del risolutore, già
  presenti prima (`PERFORM` in una `STABLE`, una variabile mai letta);
* `test-guard-listino-riga-coerente-v1` 15/15, builder 11/11, gemella 9/9; presidi
  trasversali verdi (riferimenti morti, DEFINER e `search_path`, catalogo dei messaggi,
  codici di errore, rubinetto del primo motivo, convergenza dei lock);
* corsa larga su `vendite`, `dbops`, `script`, `rls` (522 file): 359 verdi, 163 rossi, **tutti
  identici senza il giro** (stessi ok, non ok e piano). Sono fixture che pescano dati che lo
  scratch da zero non ha. ⚠️ Fra questi tre pgTAP del risolutore
  (`test-fn-resolve-prezzo-listino-esito-v1`, `…-v2-v1`, `…-v2-classe-da-contratto-v1`): sullo
  scratch non provano niente, vanno guardati nella corsa su dbdev.

### 7.3 Ricaduta sul BE

`backend/apps/core/services/error_policies_generated.py` si rigenera dal catalogo dei codici
(`manage.py genera_error_policies`). Mancano i sei codici dei due giri:
`E_ATTIVITA_LISTINO_RIGA_INCOERENTE`, `E_LISTINO_RIGA_IDENTITA_IMMUTABILE` (15-10),
`E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`, `E_ATTIVITA_LISTINO_VERSIONE_BOZZA`,
`E_PREZZO_LISTINO_VERSIONE_BOZZA` (16-10). ⚠️ Il primo giro non l'aveva segnalato.

### 7.5 Dopo l'apply: il test 11 rosso come app, e il builder (2026-10-16)

Corsa di Tid su dbdev dopo l'apply: `vendite/test-guard-listino-riga-coerente-v1` test 11 rosso,
`have:` vuoto. Il guard non c'entra: il builder `dbops.fn_pgtap_crea_commessa_attivita` legge la
riga di listino per ricavarne l'unità di misura, e **come app** la riga di un listino di un'altra
azienda è invisibile sotto la RLS di chi agisce. Il builder si fermava su «nessuna riga di listino»
(un `P0001` senza nome di vincolo, quindi il codice vuoto) e il guard non veniva raggiunto. La prova
pre-apply (§7.2-bis) girava da owner, senza RLS: lì il test era verde.

Corretto da `20_code/dbops/20261016-33` (sessione DB, su decisione di Tid dello stesso giorno): se la
riga non si vede e il chiamante dà articolo e versione, come fa il backend, l'unità di misura viene
dall'articolo e giudica il guard. Senza articolo e versione il builder resta fermo, con una frase che
dice che cosa passare (la frase pinnata da `dbops/test-fn-pgtap-crea-commessa-attivita-v1` resta).
Il test 11 passa articolo e versione del listino altrui.

Provato **come app** sullo scratch (`zeroerp_app`, il builder nuovo creato in `pg_temp`): col builder
vecchio il test 11 rosso con `have:` vuoto, lo stesso di dbdev; col nuovo 15/15. Gli altri pgTAP che
usano il builder, identici prima e dopo: `dbops/test-fn-pgtap-crea-commessa-attivita-v1` 11/11,
`vendite/test-riga-listino-propagata-dalla-commessa-v1` 9/9, `vendite/test-push-contratto-dalla-madre-v1`
12/12, `rls/test-rls-commesse-ef-whitelist-write` 6/6 (da owner, come il suo runner).

### 7.4 Trovato nel giro: la matrice categoria → listino non guarda l'emittente (→ D-5, §8)

Contratti e offerte rifiutano già un listino di un'altra azienda
(`script.fn_check_listino_documento`, `E_DOC_LISTINO_EMITTENTE_DIVERSO`, decisione F-2 del
2026-10-08). La matrice `anagrafiche.categorie_clienti_listini` no: una riga dell'emittente X
può puntare a un listino di Y. Il risolutore lo sceglierebbe, e il push di una commessa di X
verrebbe rifiutato da D-3 con un errore TECNICO, invece di fermare la configurazione sbagliata
dove nasce. Su dbdev, il 2026-10-16, nessuna riga della matrice è in questo stato (fatto
datato).

**Proposta:** un guard sulla matrice che riusa `script.fn_check_listino_documento` (utility ed
emittente, traducendo `emittente_soggetto_ruolo_id` nel suo emittente fiscale). I messaggi di
quei due codici parlano di «documento», quindi vanno resi neutri o affiancati da due codici
della matrice. Tocca `anagrafiche`: si decide prima di scrivere.

## 8. Terzo giro — la matrice categoria → listino (2026-10-16)

**D-5 (Tid, 2026-10-16): opzione B.** La regola non è una scelta: è F-2 (contratti e offerte)
e D-3 (commessa) applicata alla matrice. La scelta era sui messaggi: **B** = codici propri della
matrice, senza toccare quelli dei documenti (la loro frase dice «il documento»).

### 8.1 Che cosa c'è

| changeSet / file | Cosa |
| --- | --- |
| `20261016-06` | `anagrafiche.trgfn_categorie_clienti_listini_guard_listino`: legge `script.fn_check_listino_documento` (regola del 2: lo stesso predicato dei documenti), con l'emittente fiscale tradotto dal ruolo (`uq_emittenti_fiscali_ruolo`); sceglie il codice della matrice dalla `reason` del primo motivo e lo solleva come letterale. Una `reason` senza codice della matrice fallisce forte |
| `20261016-07` | montato `BEFORE INSERT` (senza WHEN) e `BEFORE UPDATE` con la WHEN su listino, utility, emittente: la forma del gemello dei documenti |
| CSV | `E_CATEGORIA_LISTINO_UTILITY_DIVERSA`, `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO` (DATO_ERRATO, campo `listino_id`, frasi chiuse); id messaggio 1326, 1327 |
| `anagrafiche/test-categorie-clienti-listini-guard-listino-v1.sql` | nuovo, 6 casi: i due trigger, listino giusto, altra utility, altra azienda, UPDATE verso altra azienda, UPDATE della sola variazione |
| `anagrafiche/test-categorie-clienti-listini-v1.sql` | **fixture rifatta**: pescava «la prima utility», «il primo emittente», «il primo listino» e la categoria `SILVER`. Su dbdev (2026-10-16) il primo listino era dell'utility 5 e la prima utility la 1: una riga che il guard nuovo rifiuta, verde fino a oggi per coincidenza, e i test 2-3 (CHECK) sarebbero stati oscurati dal guard BEFORE. Ora categoria propria, listino dal builder, utility ed emittente letti dal listino |
| `manual/` | nuova pagina del guard; regola e trigger nella pagina della matrice |

### 8.2 Prova pre-apply

Scratch `zeroerp_ruoli` (con `-01…-05` e `-33` già applicati), SQL estratto in transazione
annullata, fuso ostile, come proprietario:
* `plpgsql_check` sul guard: nessun avviso;
* pgTAP nuova 6/6; `test-categorie-clienti-listini-v1` **10/10** (prima 4/10 sullo scratch,
  per la categoria `SILVER` assente); le altre otto pgTAP che scrivono nella matrice: esito
  identico con e senza il giro; presidi trasversali verdi; `vendite/test-doc-listino-documento-v1`
  (il gemello dei documenti) 12/12;
* dbdev, lettura: nessuna delle 54 righe della matrice viene rifiutata (fatto datato).

⚠️ Come applicazione (con la RLS) si prova solo dopo l'apply: il listino di un'altra azienda,
invisibile, dà lo stesso codice (emittente diverso), per costruzione della check.

**Applicato su dbdev il 2026-10-16** (`20261016-06`, `-07` e i CSV; prima `-33`), pgTAP verdi,
nessuna regressione (corsa di Tid).

## 9. Richiesta al team BE (2026-10-16)

Testo da passare al BE così com'è:

> **Dal DB — brief `brief-db-coerenza-listino-della-riga-di-commessa`** (tutto applicato su dbdev)
>
> 1. **Rigenerare `backend/apps/core/services/error_policies_generated.py`**
>    (`manage.py genera_error_policies`). Mancano sette codici nuovi:
>    * `E_ATTIVITA_LISTINO_RIGA_INCOERENTE`, `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`,
>      `E_ATTIVITA_LISTINO_VERSIONE_BOZZA` (TECNICO): la provenienza del prezzo scritta su una riga
>      di commessa o su un'attività fatturabile non è ammessa (riga di listino incoerente con
>      articolo, unità di misura o versione; listino di un'altra azienda; versione in bozza);
>    * `E_LISTINO_RIGA_IDENTITA_IMMUTABILE` (CONFLITTO_STATO): una riga di listino non cambia
>      articolo, unità di misura o versione. Il backend già non li accetta in modifica;
>    * `E_PREZZO_LISTINO_VERSIONE_BOZZA` (NON_ESEGUIBILE): il calcolo del prezzo non dà prezzi
>      da una versione di listino in bozza passata come preferita. Contratti e offerte non
>      cambiano comportamento: passano già la versione operativa, che esclude la bozza;
>    * `E_CATEGORIA_LISTINO_UTILITY_DIVERSA`, `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO`
>      (DATO_ERRATO, campo `listino_id`): nella matrice categoria → listino il listino dev'essere
>      della utility e dell'azienda della riga. Il form della matrice li riceve come errore di
>      campo, come già succede per contratti e offerte.
> 2. **Riportare la fixture di `test_prezzo_riga_commessa_db` sul builder**
>    `dbops.fn_pgtap_crea_commessa_attivita`, che ora accetta tre parametri nominali in coda:
>    `p_articolo_id` (l'articolo costruito prima, coi flag giusti), `p_listino_versione_id`
>    (la versione sotto cui la riga è registrata) e `p_listino_riga_id` (la riga di listino del
>    prezzo; da lei l'unità di misura e, se non li passate, articolo e versione). La chiamata
>    diretta alla madre `vendite.fn_upsert_commessa_attivita` nella fixture si toglie: la
>    gemella pgTAP lo ha già fatto.
>
> Nessun'altra modifica richiesta: il riallineamento del prezzo scrive già versione e riga di
> listino insieme dal risolutore, e le regole nuove lo lasciano passare.

### 9.1 Fatto dal BE (sessione BE, `dev/backend-tid`, 2026-10-16)

* **Policy**: `error_policies_generated.py` rigenerato (git e DB allineati: ogni codice nuovo è
  nel CSV in git). Entrano i sette codici con le classi del catalogo, nessuna classe esistente
  cambiata. Il rigenero porta anche i quattro codici di
  brief-db-processi-accensione-per-ambiente (`E_AMBIENTE_IMMUTABILE`, `E_PROCESSO_NON_SPEGNIBILE`,
  `E_PROCESSO_SENZA_SVEGLIA`, `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO`), già in git: il modulo è
  uno solo. Per tutti e undici il ripiego senza segnaposto in `error_messages_fallback.py`.
* **Matrice categoria → listino**: provato con una scrittura vera annullata su dbdev, come
  operatore: un listino che l'operatore non vede dà `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO` col campo
  `listino_id` strutturato. Il P0001 non è un `IntegrityError`: lo traduce il middleware, come per
  contratti e offerte, e il form accende il campo. Nessun codice BE da cambiare. Il ramo «altra
  utility» non si è potuto provare a mano: su dbdev l'operatore vede listini di una sola utility
  (fatto datato); lo prova la pgTAP nuova.
* **Fixture**: `test_prezzo_riga_commessa_db` scrive la riga col builder (articolo e versione dal
  chiamante); la copia della chiamata alla madre è tolta. 5/5 verdi.
