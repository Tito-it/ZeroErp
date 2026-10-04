# Brief DB — Una riga che si fattura dice come si eroga

> **Chi chiede:** sessione BE/FE (`dev/backend-tid`), 2026-10-04: richiesta arrivata **senza brief**,
> scritto qui dal team DB. **A chi:** team DB (`dev/db-tid`); poi BE/FE (§6).
> **Decisione:** di Tid, 2026-10-04: «contratti e offerte: l'erogazione è obbligatoria sulle righe che
> si fatturano».
> **Origine:** il seguito di `brief-db-contratto-esclusione-non-modificabile` (stessa giornata): chiusa
> l'esclusione, restava la riga che si fattura senza dire come.
> **Stato:** ✅ **DB chiuso** il 2026-10-04: applicato (`20261004-30…-33` + due CSV), pgTAP verdi
> nella corsa di Tid (§7). ⏳ Resta BE/FE (§6).

## 1. La regola

`vendite.contratti_righe` e `vendite.offerte_commerciali_eccezioni` hanno tre tipi di riga:

| Tipo | Che cosa dice | Si fattura? | `tipo_erogazione` |
| --- | --- | --- | --- |
| `OVERRIDE` | un articolo del listino a un prezzo diverso | sì | **obbligatoria** |
| `AGGIUNTA` | un articolo fuori listino | sì | **obbligatoria** |
| `ESCLUSIONE` | il contratto non vende quell'articolo | no | libera (resta vuota) |

Una riga che finisce in fattura deve dire come si conteggia: canone, una tantum, a ore o a consumo.
L'esclusione non si fattura e non si modifica (guard `_a05_` del brief precedente).

## 2. Il difetto

`tipo_erogazione` era nullable su tutte e due le tabelle, e chi la legge **ripiegava in silenzio**:

* `vendite.fn_list_contratti_da_pushare` proiettava `COALESCE(cr.tipo_erogazione, 'CANONE')`: una
  riga senza erogazione andava in fattura come canone, senza che nessuno l'avesse scelto;
* il form del drawer fa lo stesso (`ContrattoRigheDrawer.vue`, `r.tipo_erogazione || CANONE`).

⭐ **Trovato nel censimento dei lettori, e corretto nello stesso giro (R4).** Lo stesso lister
listava **ogni** riga del contratto, `ESCLUSIONE` comprese. Un'esclusione non ha prezzo (CHECK),
quindi arrivava in commessa con `prezzo_bloccato = FALSE`, cioè col prezzo da risolvere a valle; e il
resolver (`fn_resolve_prezzo_listino_v2_esito`, stadio 1a), per quell'articolo su quel contratto,
risponde `E_ARTICOLO_ESCLUSO_DA_CONTRATTO`. Un articolo che il contratto dichiara di non vendere
veniva proposto alla fatturazione.

## 3. Richiesta

| # | Cosa | Sede |
| --- | --- | --- |
| R1 | `contratti_righe`: `tipo_erogazione` obbligatoria su ogni riga che non è `ESCLUSIONE` | CHECK + guard |
| R2 | La stessa regola su `offerte_commerciali_eccezioni`. `fn_push_offerta_a_contratto` ricopia l'erogazione: con la regola solo sul contratto, il push di un'offerta farebbe nascere un contratto rifiutato dal suo stesso CHECK | CHECK + guard |
| R3 | Codice di errore proprio, classe `DATO_ERRATO`, campo `tipo_erogazione`, con la policy e il ripiego senza `%s`. Meglio un guard che solleva il codice che un CHECK nudo, così il backend riceve il campo da correggere | guard |
| R4 | *(trovato dal team DB)* il lister del push non propone le esclusioni e legge l'erogazione senza ripiego | `fn_list_contratti_da_pushare` |
| R5 | pgTAP **costruiti**: OVERRIDE e AGGIUNTA senza erogazione rifiutati col codice, ESCLUSIONE senza erogazione accettata, su contratto e su offerta | pgTAP |
| R6 | Le righe esistenti fuori regola: il team DB sceglie come sistemarle. Il changeSet non deve fallire in CI su un DB ricostruito da zero | §5.2 |
| R7 | Elencare chi scrive le due tabelle e verificare che nessuno crei un OVERRIDE o un'AGGIUNTA senza erogazione | §5.4 |

## 4. Fuori perimetro

* L'erogazione sull'`ESCLUSIONE` non viene **vietata**: la richiesta la vuole solo non obbligatoria.
  Vietarla sarebbe un'altra regola, da decidere a parte. Oggi un'esclusione nasce anche con
  un'erogazione (il drawer la manda) e non si modifica più, quindi nessuno la legge.
* La matrice erogazione × fonte (`chk_*_coerenza_fonte_erogazione`) e il CHECK sul prezzo non
  cambiano.

## 5. Consegna DB (2026-10-04)

### 5.1 I changeSet

| changeSet | Cosa | Richiesta |
| --- | --- | --- |
| `00_schema/vendite/20261004-30` | `chk_contrighe_erogazione_per_tipo_eccezione` e `chk_offerte_eccezioni_erogazione_per_tipo_eccezione`: `tipo_eccezione = 'ESCLUSIONE' OR tipo_erogazione IS NOT NULL` | R1, R2, R6 |
| `20_code/script/20261004-31` | nasce `script.trgfn_righe_guard_erogazione_obbligatoria()` | R3 |
| `20_code/vendite/20261004-32` | `trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd` e `trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd`, `BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione`, per riga | R1, R2 |
| `20_code/vendite/20261004-33` | `fn_list_contratti_da_pushare`: niente `ESCLUSIONE`, niente `COALESCE(…, 'CANONE')`. Firma invariata | R4 |
| CSV `config/codici_errore` + `config/messaggi_errore` | `E_RIGA_EROGAZIONE_OBBLIGATORIA` (id messaggio 1194) | R3 |

Il corpo del lister viene dalla doc auto-gen, verificato identico a `pg_get_functiondef` sullo scratch
prima di toccarlo.

### 5.2 Decisioni prese sul modello

* **«Tutto tranne `ESCLUSIONE`», non «`OVERRIDE` o `AGGIUNTA`».** Un tipo di riga aggiunto domani
  all'enum nasce vincolato, non aperto: la stessa scelta dell'elenco delle colonne ammesse nel guard
  dell'esclusione.
* **CHECK e guard, tutti e due.** Il guard (`BEFORE ROW`) parla prima e manda codice e campo; il
  CHECK è la regola leggibile nella struttura della tabella e copre le strade che il trigger non
  percorre (trigger spenti, `COPY`). È la forma già in servizio per il prezzo. Il pgTAP asserisce il
  CHECK per conto suo: a fermare un `INSERT` basterebbe il guard, e un CHECK tolto passerebbe
  inosservato.
* **Una funzione per le due tabelle**, in `script` accanto a `trgfn_righe_default_fonte_qta` e
  `trgfn_righe_guard_pending`, che servono le stesse due tabelle gemelle. Due copie della stessa
  regola un giorno risponderebbero in due modi diversi (regola del 2). L'argomento del trigger è la
  colonna del documento padre, usata solo nel contesto.
* **Fascia `_a10_`**: è un giudizio sul valore nuovo, non un «questa riga non si tocca». Prima
  parlano il rifiuto «fuori bozza» del documento (`_a05_`) e, sul contratto,
  `guard_aggiunta_fuori_listino` («a» < «e»): un'AGGIUNTA su un articolo del listino è sbagliata
  comunque. `default_fonte_qta` gira prima e con l'erogazione vuota lascia vuota anche la fonte, ma il
  `NOT NULL` della fonte si valuta dopo tutti i `BEFORE ROW`: parla questo guard.
* **`UPDATE OF tipo_erogazione, tipo_eccezione`** (linee-guida-trigger): solo quelle due colonne
  possono rompere la regola, e il CHECK garantisce che nessuna riga ferma la violi già.
* **Niente `fn_check_*`**: la regola non spegne un pulsante, segnala un campo mancante in un form
  (linee-guida-sql §5, «la domanda che viene PRIMA»). Si solleva il codice diretto.
* **R6, le righe esistenti: si correggono a mano, prima dell'apply.** Una bonifica scritta in un
  changeSet dovrebbe scegliere un'erogazione al posto di chi ha creato la riga, cioè ripetere il
  difetto che il brief chiude; e passerebbe dal rifiuto «fuori bozza» sui contratti attivi. Il
  `20261004-30` ha una `preCondition` `HALT` che conta le righe fuori regola e, nel messaggio, dà la
  query per trovarle (precedente: `20261002-43`). Su un DB da zero le tabelle sono vuote e la
  `preCondition` passa. ⚠️ È una `preCondition` su dati di esercizio, non su un seed di `80_data`:
  non è il divieto di linee-guida-sql §11.4.
* **R4, il ripiego si toglie, non si lascia «per sicurezza».** Dopo il filtro, ogni riga listata
  è una riga che il CHECK obbliga ad avere l'erogazione: il `COALESCE` è irraggiungibile, e lasciarlo
  nasconderebbe in silenzio un vincolo che un giorno mancasse.

### 5.3 Il codice nuovo

| Codice | Classe | Messaggio | Valori |
| --- | --- | --- | --- |
| `E_RIGA_EROGAZIONE_OBBLIGATORIA` | `DATO_ERRATO` | «Manca il tipo di erogazione: una riga che si fattura deve dire se è un canone, una tantum, a ore o a consumo.» | nessuno |

Contesto: `campo` = `tipo_erogazione` (esce nel canale `COLUMN`), `riga_id`, `contratto_id` o
`offerta_id`, `articolo_id`, `tipo_eccezione`. Nessun `bersaglio`: l'operatore è già sulla riga.

### 5.4 R7 — chi scrive le due tabelle (censito il 2026-10-04)

| Scrittore | Cosa fa | Crea OVERRIDE/AGGIUNTA senza erogazione? |
| --- | --- | --- |
| `vendite.fn_push_offerta_a_contratto` | `INSERT` nel contratto, copia 1:1 dall'offerta | no: l'offerta ha la stessa regola (R2) |
| `vendite.fn_crea_revisione_offerta` | `INSERT` nell'offerta nuova, copia 1:1 dalla revisione | no: copia righe che hanno già passato la regola |
| BE `ContrattiRepository.create_riga` / `update_riga` | i verbi del drawer del contratto | **sì, oggi**: `tipo_erogazione` è facoltativa nel service. Da oggi la rifiuta il DB col codice; vedi §6 |
| BE `OfferteRepository` (create/update eccezione) | i verbi del drawer dell'offerta | **sì, oggi**, come sopra |
| BE `approvazioni_prezzo_service` (workflow L3) | `UPDATE` di `stato_approvazione_prezzo` | no: non tocca le due colonne, il guard non scatta |
| trigger delle tabelle (`default_fonte_qta`, `qta_from_operativa`, audit, `tx_id`) | riscrivono `NEW` | nessuno scrive `tipo_erogazione` |
| automazioni (`cleanup_at`, chiusura scadenze, pannello, storico) | — | nessuna nomina le due tabelle |

Lettori di `tipo_erogazione` nel DB: `trgfn_righe_default_fonte_qta`, `fn_contratto_righe_preview`,
`fn_push_offerta_a_contratto`, `fn_crea_revisione_offerta`, `fn_list_contratti_da_pushare`. Solo
l'ultimo ripiegava (R4).

### 5.5 pgTAP

* **Nuovo** `db/pgtap/vendite/test-righe-erogazione-obbligatoria-v1.sql`, 21 test, tutto costruito:
  i due CHECK (forma esatta) e i due trigger montati; su contratto e su offerta, OVERRIDE e AGGIUNTA
  senza erogazione rifiutati con la frase, un `UPDATE` che la toglie rifiutato, l'ESCLUSIONE senza
  erogazione accettata, e i due canali strutturati (`CONSTRAINT` = il codice, `COLUMN` =
  `tipo_erogazione`); per R4, il contratto attivato si lista con l'OVERRIDE, l'ESCLUSIONE no, e
  `tipo_consumo` è `UNA_TANTUM`, cioè quello della riga. Non `CANONE`, che era il vecchio ripiego: il
  test passerebbe per coincidenza.
* **`test-fn-list-contratti-da-pushare-v1.sql`**: il test 3 pinnava il ripiego («CANONE quando
  tipo_erogazione NULL»), ora vuole l'erogazione della riga. ⭐ E la fixture **ora si costruisce**
  (`fn_pgtap_crea_cliente_ba`, `fn_pgtap_crea_articolo`, stati per `codice_interno`): prima leggeva
  il primo billing account del DB e su un DB da zero finiva in `ERRORE_FIXTURE`
  (`baseline-rossi-ci.tsv`). Sullo scratch: 8/8. ⏳ La riga del registro la aggiorna la corsa di Tid.
* **Fixture di altri 14 file**: le loro righe OVERRIDE/AGGIUNTA nascevano senza erogazione, e il guard
  le avrebbe rifiutate. Aggiunta l'erogazione coerente con la fonte (`CANONE`; `CONSUMO` dove la fonte
  è `LETTURE`), con una riga di commento a ogni `INSERT`. Dove il test voleva provare un **altro**
  rifiuto (il CHECK sul prezzo, la UNIQUE, `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`,
  `E_RIGA_DOC_NON_BOZZA`, i blocchi RLS che catturano solo `insufficient_privilege` /
  `check_violation`), l'erogazione serve proprio perché il guard nuovo non parli al suo posto:
  `rls/test-rls-contratti-satelliti`, `rls/test-rls-offerte-satelliti`,
  `script/test-fn-check-prezzi-autorizzati-v1`, `offerte_commerciali/test_offerte_eccezioni_componenti`,
  `offerte_commerciali/test_offerte_eccezioni_guard_pending`,
  `vendite/test-bozza-non-operativa-e-preview-contratto-v1`, `test-contratti-overlap-draft-escluso-v1`,
  `test-contratti-righe-guard-pending-v1`, `test-contratti-schema-step22-v1`, `test-contratti-step23-v1`,
  `test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1`, `test-fn-resolve-prezzo-listino-v2-step24-v1`,
  `test-fn-resolve-prezzo-listino-v2-v1`, `test-trgfn-doc-righe-lock-fuori-bozza-v1`.
* 🟠 **Trovato e non corretto qui**: `test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1.sql`
  (riga ~361) inserisce una riga di contratto **senza `tipo_eccezione`** (NOT NULL, senza default) su
  un contratto creato già ATTIVO, che il rifiuto «fuori bozza» respingerebbe. Oggi non gira: la
  fixture va in `skip` (7 skip). Va ricostruita (OVERRIDE, contratto prima in bozza); è debito di
  quel file, non di questo giro.

### 5.6 Verifica

Tid ha applicato i quattro changeSet mentre la prova pre-apply stava partendo
(`databasechangelog` di `zeroerp_ci`: `EXECUTED` alle 18:27; la doc auto-gen rigenerata mostra
CHECK e trigger anche su dbdev). La prova si è fatta quindi **dopo l'apply**, sullo scratch, che è
il DB ricostruito da zero:

* il pgTAP nuovo: **21/21**. **Mutazione**, in transazione ritirata: rimesso il lister vecchio e
  tolto il guard del contratto, sono rossi esattamente il 3 (montaggio), il 5, 6 e 9 (parla il CHECK,
  23514, con un'altra frase), il 10 e 11 (canali vuoti) e il 20 (l'esclusione si lista). Il CHECK da
  solo ferma comunque la riga: è la rete;
* `test-fn-list-contratti-da-pushare-v1`: 8/8 (era `ERRORE_FIXTURE`);
* i 14 file con le fixture sistemate: stessi conteggi di prima della regola, file per file. I rossi
  che restano (`overlap-draft-escluso` 2, `schema-step22` 4, `step23` 6, `resolve-v2-step24` e
  `resolve-v2-v1` in errore di fixture) sono tutti già in `baseline-rossi-ci.tsv`. ⚠️ Per step22 e
  step23 sullo scratch le fixture non nascono, quindi i loro `INSERT` li esercita solo la corsa su
  dbdev;
* `plpgsql_check` a zero sulle due funzioni (il guard provato su tutte e due le tabelle); guardrail
  statici verdi (`run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
  `grant_ruolo_batch`, `pgtap_preambolo`, `sql_letterali`, `timestamp_senza_fuso`).
* **Presidi trasversali da guardare nella corsa di Tid**: `dbops/test-riferimenti-morti-v1` (funzione
  plpgsql nuova); `config/test-catalogo-messaggi-errore-completo` e i test sui codici (un codice
  nuovo); i presidi che guardano il canale del campo (`dbops.vw_punti_canale_campo`: un punto nuovo
  che passa `campo`).

## 6. Lato BE/FE, a consegna DB fatta

* **BE, il codice nuovo**: `E_RIGA_EROGAZIONE_OBBLIGATORIA` in `error_policies_generated.py` (classe
  `DATO_ERRATO`; il campo `tipo_erogazione` arriva nel canale `COLUMN`, da evidenziare nel form) e in
  `error_messages_fallback.py` (il ripiego, frase chiusa). Il guardrail
  `test_error_codes_db_policy_guardrail` lo trova nel corpo del guard e resta rosso finché non c'è.
* **BE, create**: `contratti_service` e `offerte_service` accettano oggi `tipo_erogazione` facoltativa
  in `CREATE_KEYS_*`. Da oggi il DB la rifiuta su OVERRIDE/AGGIUNTA col campo: la pre-validazione nel
  service si può aggiungere solo se **dice la stessa cosa** del guard (stesso codice, stesso campo),
  altrimenti è una seconda sede della regola. Lasciare che parli il DB è sufficiente.
* **BE, update**: un PATCH che porta `tipo_erogazione` a `null` su OVERRIDE/AGGIUNTA ora è rifiutato.
  Test: una create senza erogazione e un PATCH a `null` rispondono il codice nuovo, col campo.
* **FE** (`ContrattoRigheDrawer.vue`, `OffertaEccezioniDrawer.vue`): il campo diventa obbligatorio
  nella creazione di OVERRIDE e AGGIUNTA. I ripieghi `r.tipo_erogazione || CANONE`
  (`ContrattoRigheDrawer.vue` ~410, ~588-593) diventano irraggiungibili sulle righe che si
  modificano (l'esclusione non si modifica più, le altre hanno l'erogazione): vanno tolti, perché sono
  la stessa classe di difetto che il brief chiude (un valore che nessuno ha scelto).
* **Commesse / fatturazione**: il lister non propone più le righe `ESCLUSIONE`. Se il BE contava su
  quelle righe per qualcosa (non risulta dal censimento: `commesse_repository` chiama il lister e
  basta), da verificare.
* **Doc:** `api_contratti.md` e la doc API delle offerte (create/PATCH riga: erogazione obbligatoria
  su OVERRIDE/AGGIUNTA).

## 7. Esito

1. ✅ Scritti e applicati da Tid `20261004-30…-33` e i due CSV (scratch: `EXECUTED` 18:27).
2. ✅ Prova sullo scratch dopo l'apply (§5.6).
3. ✅ Migrazione applicata e pgTAP verdi nella corsa di Tid (2026-10-04).
4. ⏳ BE/FE (§6).
