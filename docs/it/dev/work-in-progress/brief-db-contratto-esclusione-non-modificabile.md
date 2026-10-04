# Brief DB — Un'esclusione del contratto non si modifica

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§5), che **attende** la consegna DB.
> **Origine:** verifica critica del codice non committato del
> `brief-db-liste-righe-documento` (§9.15-9.16), 2026-10-04.
> **Decisione:** di Tid, 2026-10-04: «una esclusione non si modifica».
> **Stato:** ✅ **DB chiuso** il 2026-10-04: applicato (`20261004-12…-14` + CSV), lock generato su dev,
> pgTAP senza regressioni (§6.6). ✅ **BE/FE scritto** il 2026-10-04 (§7), non committato.

## 1. La regola

Una riga `ESCLUSIONE` di `vendite.contratti_righe` dice una cosa sola: «questo articolo del listino
non è disponibile per questo contratto». Non ha prezzo (CHECK
`chk_contrighe_prezzo_per_tipo_eccezione`), e quantità, UdM, erogazione e fonte non hanno senso su un
articolo che il contratto non vende. **Si crea (Escludi) e si cancella (Ripristina articolo), e
basta.** Cambiare idea è cancellarla e, se serve, creare un'altra eccezione.

## 2. Il difetto di oggi

La regola non è scritta da nessuna parte, e il modello dice il contrario:

* `vendite.fn_contratto_righe_preview` dà alla riga `ESCLUSIONE` i verbi
  `ARRAY['MODIFICA', 'RIPRISTINA_ARTICOLO']` (D-8.4 del brief liste-righe);
* nessun guard rifiuta un `UPDATE` su una riga `ESCLUSIONE`: il solo vincolo è il CHECK sul prezzo;
* il drawer, che **rende** i verbi del DB, apre quindi il form di modifica sull'esclusione. Il form
  ripiega su `tipo_erogazione = CANONE` e sulla fonte di default (`FISSA`, quantità 1) perché la
  riga, creata con `tipo_erogazione` NULL, non li ha: il primo «Salva» scrive sull'esclusione valori
  che nessuno ha scelto. È la stessa classe di difetto del §9.11 del brief liste-righe (il form che
  riscrive in silenzio).

⛔ Il frontend **non** deve togliere da sé il click sulle esclusioni: i verbi della riga li decide il
DB (capability di riga, linee-guida-sql §12.5), e una seconda sede della regola è la divergenza che
D-8.4 ha ritirato.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| R1 | `vendite.fn_contratto_righe_preview`: sulla riga `ESCLUSIONE` i verbi diventano `ARRAY['RIPRISTINA_ARTICOLO']`. Aggiornare il `COMMENT` (oggi elenca `ESCLUSIONE -> MODIFICA, RIPRISTINA_ARTICOLO`). |
| R2 | Un guard `BEFORE UPDATE` su `vendite.contratti_righe` che rifiuta l'`UPDATE` di una riga con `OLD.tipo_eccezione = 'ESCLUSIONE'`, con codice ed errore propri (forma §12.5: un `script.fn_check_*` che rende i motivi, letto anche dal guard, come `fn_check_esclusione_articolo_contratto`). ⚠️ Da decidere sul modello quali colonne restano ammesse: le tecniche (`data_update`, `user_update`, `tx_id`) le scrivono i trigger della stessa riga; resta da vedere `attivo` (la cancellazione è un `DELETE` fisico nel repository, ma i trigger `prevent_deactivate_if_children` dicono che una disattivazione esiste nel modello). |
| R3 | ⭐ **Simmetria, da valutare insieme**: `tipo_eccezione` è immutabile per il modello (il service lo dice nei messaggi: «per cambiare tipo, eliminare la riga e crearne una nuova»), ma a DB nessun guard lo impedisce. Senza, un `UPDATE` che porta `OVERRIDE → ESCLUSIONE` crea un'esclusione per un'altra via. Se il team DB conferma, lo stesso guard rifiuta `NEW.tipo_eccezione IS DISTINCT FROM OLD.tipo_eccezione`. |
| R4 | Elencare **tutti** gli scrittori di `contratti_righe` (funzioni, trigger, job) e verificare che nessuno aggiorni per percorso legittimo una riga `ESCLUSIONE` (per esempio una propagazione al cambio di versione del listino): un guard nuovo non deve rompere in silenzio un flusso esistente. |
| R5 | pgTAP **costruiti**: un'esclusione fabbricata nel test, l'`UPDATE` rifiutato col codice atteso, i verbi della riga senza `MODIFICA`; per R3 il cambio di tipo rifiutato. Non su righe esistenti. |

Codice di errore nuovo: va registrato con la sua policy **e** il ripiego senza `%s` (regola del
progetto, Messaggi-di-Errore-e-Generazione-Log).

## 4. Fuori perimetro

* Le righe `OVERRIDE` e `AGGIUNTA` restano modificabili come oggi.
* «Escludi» (creazione) e «Ripristina articolo» (`DELETE`) non cambiano.

## 5. Lato BE/FE, a consegna DB fatta

* **BE** (`contratti_service.update_riga`): il ramo che pre-valida il prezzo di una `ESCLUSIONE` diventa
  irraggiungibile e va tolto; il codice nuovo del guard va tradotto (policy). Test: un PATCH su
  un'esclusione risponde l'errore del guard.
* **BE, i due codici nuovi** (§6.3): `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` (guard, senza valori) e
  `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` (lock, un valore: il nome della colonna) vanno in
  `error_policies_generated.py` e in `error_messages_fallback.py` (il ripiego **senza** `%s`). Tutti e
  due `CONFLITTO_STATO`. Il guardrail `test_error_codes_db_policy_guardrail` li trova nel corpo del
  guard e nel registro dei lock, e resta rosso finché non ci sono.
* **BE, cambio di tipo**: il service rifiutava già il cambio di `tipo_eccezione` («eliminare la riga e
  crearne una nuova»). Da oggi lo rifiuta anche il DB: il messaggio del service resta (parla prima, col
  campo), il codice del lock è la rete per chi passa da un'altra strada.
* **FE** (`ContrattoRigheDrawer`): nessun cambio di comportamento (il click segue i verbi). Diventano
  morti i rami del form di **modifica** che trattano l'`ESCLUSIONE` (Tag «prezzo n/a», prezzo
  disabilitato, ripieghi `tipo_erogazione`/fonte per le righe senza): da togliere nello stesso giro.
* **Doc:** `api_contratti.md` (PATCH riga), `analisi-contratti-v1.md` se ne parla.

## 6. Consegna DB (2026-10-04)

### 6.1 I changeSet

| changeSet | Cosa | Richiesta |
| --- | --- | --- |
| `20_code/vendite/20261004-12` | nasce `vendite.trgfn_contratti_righe_guard_esclusione_immutabile` | R2 |
| `20_code/vendite/20261004-13` | trigger `trg_contratti_righe_a05_guard_esclusione_immutabile_upd`, `BEFORE UPDATE`, per riga, `WHEN (OLD.tipo_eccezione = 'ESCLUSIONE')` | R2 |
| `20_code/vendite/20261004-14` | `fn_contratto_righe_preview`: l'ESCLUSIONE ha il solo `RIPRISTINA_ARTICOLO`; `RETURNS TABLE` invariato, `CREATE OR REPLACE` | R1 |
| CSV `dbops/automation_lock_columns` | riga `vendite.contratti_righe.tipo_eccezione` → `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` | R3 |
| CSV `config/codici_errore` + `config/messaggi_errore` | i due codici nuovi (id messaggio 1192, 1193) | R2, R3 |

Il corpo della preview viene da `20261004-01`, verificato identico riga per riga al corpo vivo della doc
auto-gen.

### 6.2 Decisioni prese sul modello

* **R2, quali colonne restano ammesse: solo le tecniche** (`data_update`, `user_update`, `tx_id`). Il
  guard confronta la riga intera tolte quelle tre. L'elenco è delle colonne **ammesse**, non di quelle
  vietate: una colonna aggiunta domani nasce bloccata.
* **`attivo` è vietata.** Disattivare un'esclusione non la toglie:
  `uq_contrighe_one_eccezione_per_articolo` non è parziale su `attivo`, quindi la riga spenta tiene
  occupato il posto dell'articolo, e sull'articolo non si possono più creare né un'altra esclusione né
  un OVERRIDE. L'uscita è una sola, il `DELETE`. Vale per il modello, non per le righe di oggi: i
  trigger `prevent_deactivate_if_children` dicono che la disattivazione esiste per la tabella, non che
  serva a un'esclusione.
* **Anche le FK sono vietate** (`contratto_id`, `articolo_id`, `uom_operativa_id`): spostare
  un'esclusione è crearne un'altra. ⚠️ Le tre FK sono `ON UPDATE CASCADE`, quindi la rinumerazione
  della chiave di un padre che ha un'esclusione verrebbe rifiutata. È la scelta già in servizio per i
  lock di colonna su FK (`magazzino.ubicazioni.magazzino_id`), e nessun verbo del modello rinumera la
  chiave di un articolo, di un contratto o di un'UdM.
* **Fascia `_a05_`**: il rifiuto «questa riga non si tocca» parla prima dei guard `_a10_` e del CHECK
  sul prezzo. Un prezzo scritto su un'esclusione dice «l'esclusione non si modifica», non «un'esclusione
  non ha prezzo» (che inviterebbe a togliere il prezzo e riprovare). Nella stessa fascia viene dopo il
  rifiuto «fuori bozza» del documento.
* **Niente `fn_check_*`** (scostamento dal testo di R2). La forma §12.5 serve quando la regola spegne un
  pulsante **con un motivo**. Qui il pulsante non c'è: l'origine `ESCLUSIONE` non ha il verbo
  `MODIFICA`, come le altre origini non hanno i verbi delle altre (D-8.4). Non c'è un `reason` da
  rendere a video, quindi il guard solleva il codice diretto (linee-guida-sql §5, «la domanda che viene
  PRIMA»).
* **R3 confermato, ma nel registro dei lock e non nel guard.** Dal 2026-09-26 il registro
  `dbops.automation_lock_columns` è l'unica sede di un lock di colonna
  (`brief-db-lock-di-colonna-fuori-registro`). Il lock vale per **tutte** le righe: il cambio di tipo
  è rifiutato anche fra OVERRIDE e AGGIUNTA. Su un'ESCLUSIONE parla prima il guard `_a05_`.
  ⚠️ Il trigger generato si chiama `trg_contratti_righe_a10_lock_columns_upd`, e il nome lo fissa il
  generatore: su un `OVERRIDE → AGGIUNTA` di un articolo del listino parla prima
  `…_a10_guard_aggiunta_fuori_listino_ins_upd` («g» < «l»). Rifiutano tutti e due, cambia solo la
  frase. Non lo correggo qui: la fascia del lock è del generatore, per tutte le tabelle.

### 6.3 Codici nuovi

| Codice | Classe | Messaggio | Valori |
| --- | --- | --- | --- |
| `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` | `CONFLITTO_STATO` | «Un articolo escluso dal contratto non si modifica: l'esclusione si può solo togliere.» | nessuno |
| `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` | `CONFLITTO_STATO` | «Il tipo di una riga del contratto non si cambia (colonna %s): …» | la colonna |

Contesto del guard: `riga_id`, `contratto_id`, `articolo_id`, `colonne` (quelle cambiate). Nessun
`bersaglio`: l'operatore è già sulla riga.

### 6.4 R4 — chi scrive `contratti_righe` (censito il 2026-10-04)

| Scrittore | Cosa fa | Tocca un'ESCLUSIONE? |
| --- | --- | --- |
| `vendite.fn_push_offerta_a_contratto` | solo `INSERT` | no |
| BE `ContrattiRepository.create_riga` / `update_riga` / `delete_riga` | i verbi del drawer | solo `update_riga`, che è il caso che il guard chiude |
| BE `approvazioni_prezzo_service` (workflow L3) | `update_riga` su `stato_approvazione_prezzo` | no: lavora sulle righe con prezzo, e un'esclusione non ne ha (CHECK) |
| trigger della tabella (`default_fonte_qta`, `qta_from_operativa`, audit, `tx_id`) | riscrivono `NEW` | girano **dopo** il guard `_a05_`, che vede il valore chiesto |
| automazioni (`cleanup_at`, chiusura scadenze, pannello, storico) | — | nessuna nomina la tabella |
| FK `ON UPDATE CASCADE` | rinumerazione della chiave del padre | sì, e viene rifiutata: §6.2 |

Nessun percorso legittimo aggiorna un'esclusione.

### 6.5 Verifica

* `db/pgtap/vendite/test-contratto-esclusione-non-modificabile-v1.sql` (nuovo, 15 test, tutto
  costruito): verbi della riga (R1); quantità, prezzo, articolo, `attivo` e cambio di tipo rifiutati col
  messaggio del guard (R2); `UPDATE` senza cambi, `UPDATE` delle sole tecniche, `DELETE` e modifica
  dell'OVERRIDE passano; il registro dichiara il lock e il lock generato rifiuta `OVERRIDE → ESCLUSIONE`
  (R3; `skip` dichiarato finché l'automazione non lo genera).
* `db/pgtap/vendite/test-contratto-righe-lista-v1.sql` test 5: ora fissa `ARRAY['RIPRISTINA_ARTICOLO']`.
* **Prova prima dell'apply** (SQL estratto dai changeSet + righe nuove dei CSV + corpo del pgTAP, in
  una transazione ritirata, da owner su dbdev): 15/15, e con la generazione del lock dentro la stessa
  transazione il test 15 gira davvero. Mutazione: senza il guard sono rossi esattamente i test 2 e 5-9.
  Il pgTAP della lista: 12/12 con le modifiche, solo il 5 rosso senza. `plpgsql_check` a zero sulle due
  funzioni. Guardrail statici verdi. Lo stato vivo è rimasto intatto (md5 della preview invariato).
  `check_i18n_keys` ha un rosso che c'era già e non è di questo giro
  (`vendite.lotti.azione_reason.plafond_consumato`, cantiere plafond).
* **Presidi trasversali da guardare nella corsa di Tid**: `dbops/test-riferimenti-morti-v1` (compila
  ogni funzione plpgsql: qui verde in prova); `config/test-catalogo-messaggi-errore-completo` e i test
  sui codici (due codici nuovi, coi loro messaggi).

### 6.6 Esito (2026-10-04)

1. ✅ Applicato da Tid: `20261004-12`, `-13`, `-14` (`EXECUTED`, 17:29) e i tre CSV.
2. ✅ Lock generato su dev: `trg_contratti_righe_a10_lock_columns_upd` presente accanto a
   `trg_contratti_righe_a05_guard_esclusione_immutabile_upd`, quindi il test 15 gira davvero.
3. ✅ pgTAP lanciati da Tid: nessuna regressione.
4. ✅ BE/FE (§5): scritto il 2026-10-04, vedi §7.

## 7. Consegna BE/FE (2026-10-04)

| Pezzo | Cosa |
| --- | --- |
| Codici | `genera_error_policies`: le sole due voci nuove, entrambe `CONFLITTO_STATO`, zero classi mosse. Ripieghi senza `%s` in `error_messages_fallback.py` |
| `contratti_service.update_riga` | tolto il ramo che pre-validava il prezzo di un'`ESCLUSIONE` (400 `E_VENDITE_VALIDATION`). Il PATCH arriva al DB e il codice strutturato del guard vince in `raise_from_database_error`: nessun marker da aggiungere. Il messaggio del service sul cambio di tipo resta (§5) |
| Test BE | `vendite/tests/db/test_contratto_esclusione_non_modificabile_db` (nuovo, DB vero, mondo costruito come nel pgTAP): PATCH della quantità e PATCH del prezzo rispondono `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`. Il secondo va rosso col ramo vecchio (che rispondeva `E_VENDITE_VALIDATION`). Ritirato il test mock `test_update_riga_esclusione_prezzo_non_null_fallisce`, che provava il ramo tolto |
| `ContrattoRigheDrawer` | tolti i rami del form morti per l'`ESCLUSIONE`: condizioni su `useComponentiDialog`, eccezione in `canSave`, forzatura del prezzo a NULL nel payload, Tag «prezzo n/a» e prezzo disabilitato. Tolti anche i ripieghi di `tipo_eccezione` e `fonte_quantita_attesa` in modifica: tutte e due NOT NULL, i ripieghi erano morti per contratto. Chiave i18n `prezzo_esclusione_n_a` ritirata (it, en). Il click continua a seguire i verbi del DB |
| Doc | `api_contratti.md`: vincoli delle righe, PATCH riga, regola 7, i due codici nella tassonomia. `analisi-contratti-v1.md` non ne parla |

Verifica: test core (1653) e vendite (2267) con `ZEROERP_TEST_DB_E2E=1` verdi; vitest 662/662; eslint
e `check_i18n_keys` puliti.

### 7.1 Aperto — il ripiego di `tipo_erogazione` resta vivo, ma non sull'esclusione

Il §5 chiedeva di togliere «i ripieghi `tipo_erogazione`/fonte per le righe senza». Quello di
`tipo_erogazione` (`r.tipo_erogazione || CANONE` in `_onEditRigaPersistita`) **non è morto**:
`contratti_righe.tipo_erogazione` è nullable per **ogni** tipo di riga (doc auto-gen), quindi un
OVERRIDE o un'AGGIUNTA senza erogazione, che il modello ammette, apre il form con `CANONE` e il
primo «Salva» lo scrive senza che nessuno l'abbia scelto. È la classe del §9.11 del brief
liste-righe, sulle righe che restano modificabili. Non toccato qui: togliere il ripiego chiede di
decidere come il form presenta un'erogazione assente (le fonti ammesse si filtrano per tipo, e con
il tipo NULL la tendina resta vuota). Da decidere con Tid.

