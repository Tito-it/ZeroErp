# Brief DB — Righe e componenti di documento: i tre debiti rimasti

> **Chi chiede:** team DB (`dev/db-tid`), 2026-10-08. **A chi:** team DB; il §3 tocca anche il
> dominio approvazioni (BE).
> **Origine:** il §5 di `brief-db-righe-e-componenti-le-altre-famiglie` (archiviato in `work-done/`
> il 2026-10-08). Quel giro ha chiuso i quattro punti di D19 e ha trovato questi tre, che non
> erano nel suo perimetro. Un brief solo per tutti e tre, per decisione di Tid.
> **Stato:** ✅ **lato DB chiuso il 2026-10-09** — changeSet `20261008-80` … `-94` e
> `20261009-03` applicati su dev, pgTAP verdi col runner di Tid, anche su `zeroerp_ci` (§4.8).
> D-1, D-2 e D-3 decisi da Tid il 2026-10-08 (in fondo a ciascun paragrafo); i tre test non più
> costruibili sono skip motivati (§4.5). ⏳ **Resta aperto per il BE** (§4.4): il brief si
> archivia quando il team BE le ha chiuse.
> **Nel registro dei difetti DB:** voce **D20** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. 🟡 Righe d'ordine e di preventivo: la quantità cambia fuori bozza

Sulle righe d'ordine il building block `vendite.trgfn_doc_righe_lock_fuori_bozza` è montato **solo
sul DELETE**: INSERT e UPDATE restano aperti di proposito, perché `data_consegna_confermata` cambia
dopo la conferma (decisione di Tid del 14 settembre). Le righe del preventivo non hanno nessun lock
(il flusso di approvazione dei prezzi scrive `stato_approvazione_prezzo` sulle righe anche fuori
bozza). A livello DB quindi la quantità di una riga d'ordine confermato o di un preventivo emesso si
può cambiare, e a un ordine confermato si può aggiungere una riga. Il BE lo impedisce già
(`richiedi_righe_in_bozza`): la regola esiste, ma solo da un lato.

Dal `20261008-34` i **componenti** delle tre famiglie sono chiusi fuori bozza. Su una riga **kit**
quel cambio lo respinge quindi il lock del componente, attraverso la propagazione della quantità o
l'init dei componenti; su una riga **semplice** passa. È la forma che il `20261005-17` aveva corretto
sul contratto («un effetto, non una regola»), un livello più in alto.

**Direzione proposta:** un lock per **colonna** sulle due tabelle di righe, che lasci aperto solo
ciò che il dominio cambia dopo la conferma (`data_consegna_confermata` sull'ordine; sul preventivo
le marche di approvazione, se il censimento del flusso lo conferma).

⏳ **D-1 (Tid):** quali colonne restano scrivibili fuori bozza, per ordine e per preventivo.

**Istruttoria (2026-10-08, sulla struttura).**

* Nessuna funzione DB modifica `ordini_righe` o `preventivi_righe` dopo averle create: zero `UPDATE`
  nei corpi della doc auto-generata. Chi le crea per copia scrive in un documento in bozza
  (`fn_push_preventivo_a_ordine` crea l'ordine `DRAFT`, `fn_crea_revisione_preventivo` la rev
  `DRAFT`). Il lock a tre porte non ferma nessun percorso DB.
* Preventivo: le marche di approvazione **non** chiedono colonne aperte. Una riga `PENDING` è
  congelata da `script.trgfn_righe_guard_pending` (anche `attivo`: non si spegne), e un
  `PENDING`/`REJECTED` su una riga attiva ferma emissione, accettazione e revisione
  (`fn_check_prezzi_autorizzati`, `fn_check_prezzi_in_attesa`). L'esito arriva quindi sempre in
  bozza. Resta fuori solo il preventivo **annullato** con una riga in attesa: lì l'esito sarà
  respinto dal lock, ed è il ciclo di vita della pratica (`refactor-prezzi.md` §4.7, BE).
* Ordine: l'unica colonna del dominio dopo la conferma è `data_consegna_confermata`. Oggi nemmeno
  il BE la lascia cambiare dopo la conferma (`richiedi_righe_in_bozza` chiude tutto): la decisione
  del 14 settembre non ha ancora un verbo.

✅ **Deciso da Tid il 2026-10-08.**

* **Preventivo:** righe chiuse fuori bozza sulle tre porte, **nessuna colonna aperta**.
* **Ordine:** righe chiuse fuori bozza sulle tre porte; resta scrivibile la sola
  `data_consegna_confermata`, e **solo negli stati da evadere** (`CONFERMATO`,
  `PARZIALMENTE_EVASO`). In `EVASO`, `ANNULLATO` e negli altri stati è chiusa anche lei.
* **Forma:** non un trigger nuovo accanto al building block, ma un argomento in più a
  `vendite.trgfn_doc_righe_lock_fuori_bozza` — l'elenco delle colonne ammesse fuori bozza, valido
  solo sull'UPDATE, col confronto a allowlist già usato da `trgfn_righe_guard_pending`
  (`to_jsonb(OLD) - ammesse` contro `to_jsonb(NEW) - ammesse`, più le colonne di audit e `tx_id`).
  ⚠️ Da risolvere in sviluppo: «stati da evadere» si legge da un **flag** dello stato se il
  catalogo `config.stati_doc_ordini` ne ha uno, non da due codici cablati nel montaggio.
* **Ricaduta BE (richiesta al team):** il verbo che cambia `data_consegna_confermata` dopo la
  conferma, sopra la porta che il DB lascia aperta.

## 2. 🟡 `user_update` nullable ben oltre le righe di documento

Letto dal catalogo il 2026-10-08: `user_update` è nullable su circa 140 tabelle, in tutti gli schemi
applicativi (`acquisti`, `anagrafiche`, `catalogo`, `config`, `magazzino`, `ui`, `vendite`…).
`linee-guida-sql.md` §7 lo vuole `NOT NULL` ovunque. Il `20261008-31` ha chiuso soltanto la famiglia
delle righe e dei componenti di documento.

Il numero è una fotografia: la regola vale a una tabella come a cento. Quello che manca davvero è
un **presidio**: oggi niente ferma una tabella nuova che nasce con la colonna nullable.

**Direzione proposta:** prima il presidio (un pgTAP che elenca le tabelle con `user_update`
nullable e accetta solo quelle dichiarate come debito), poi la bonifica per schema, ogni volta con
la preCondition «zero NULL» del `20261008-31`.

⏳ **D-2 (Tid):** presidio con registro del debito che cala, oppure bonifica in un giro solo.

**Istruttoria (2026-10-08, sulla struttura).** `script.trgfn_audit_data_user_generic` scrive
`user_update` su ogni INSERT e UPDATE (`COALESCE` con fallback `CURRENT_USER`): dove è montato,
il `NOT NULL` non può rompere chi scrive per copia. L'unico ostacolo sono le righe NULL già
presenti. Il registro che cala serve quando ogni chiusura chiede una decisione; qui la chiusura è
meccanica.

✅ **Deciso da Tid il 2026-10-08: un giro solo, presidio compreso.** Presidio pgTAP e bonifica
nello stesso giro, un changeSet per schema con l'elenco delle tabelle scritto per esteso e la
preCondition «zero NULL» del `20261008-31`. Nel registro del debito entrano solo le tabelle
**senza** trigger di audit, se ce ne sono: quelle sono un trovato a parte, non una bonifica.

## 3. 🟡 Un componente spento IN ATTESA passa nella revisione

Il guard di testa della revisione (`fn_check_prezzi_in_attesa`, «prima l'esito, poi la revisione»,
`20260924-34`) guarda solo i componenti **attivi**. Uno spento in `PENDING` non blocca, ed è giusto,
perché un componente spento non deve bloccare per sempre. Con D-1 del brief precedente però ora si
**copia**, con la sua marca e la pratica della rev N. Se nella rev N+1 qualcuno lo riaccende, torna
un prezzo in attesa legato alla pratica della revisione vecchia: è lo stesso caso che il
`20260924-34` ha chiuso per le righe. Vale identico per l'offerta, dal `20261005-19`.

Non è solo del DB: tocca il ciclo di vita della pratica su una revisione superata
(`refactor-prezzi.md` §4.7, dominio approvazioni).

⏳ **D-3 (Tid):** quale delle tre strade.
* la revisione rifiuta anche con uno spento in attesa;
* lo spento in attesa si copia senza marca e torna a chiedere l'approvazione quando si riaccende;
* riaccenderlo nella rev N+1 è rifiutato finché la pratica della rev N non ha un esito.

**Istruttoria (2026-10-08, sulla struttura).** Sui componenti il ciclo di approvazione **non
esiste**: nessun verbo li mette in `PENDING` né dà loro un esito (`approvazioni_prezzo_service`
lavora solo su righe di preventivo, contratto e offerta; il contratto dell'operatore rifiuta
`stato_approvazione_prezzo` sul componente; le funzioni DB la marca la **copiano** soltanto), e
non c'è nemmeno il controllo L2 (`update_componente`: «riservato a L1/L2/L3 futuro»). In più dal
`20261008-34` i componenti della rev N emessa sono chiusi. Quindi:

* la **terza strada** blocca per sempre: l'esito non si può scrivere sul componente chiuso della
  rev N;
* la **prima** pure: lo spento della rev N non si può più correggere (chiuso e congelato), e il
  documento non si revisionerebbe più;
* la **seconda** non apre un buco nuovo: oggi qualunque prezzo di componente passa senza
  controllo, perché la policy sui componenti non c'è.

✅ **Deciso da Tid il 2026-10-08: seconda strada.** Nella revisione di preventivo e offerta
(`fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`) un componente **spento** in
`PENDING` si copia con `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` a NULL.
Approvato e rifiutato continuano a copiarsi 1:1; un componente **attivo** in `PENDING` continua a
fermare la revisione (`fn_check_prezzi_in_attesa`). ⚠️ **Debito dichiarato:** la nuova richiesta
di approvazione alla riaccensione appartiene all'L3 dei componenti, che oggi non esiste. Va in un
brief suo quando quel ciclo si costruisce, non qui.

## 4. Il giro DB (2026-10-08 / -09) — applicato, test verdi

### 4.1 ChangeSet

| ChangeSet | Cosa | Decisione |
| --- | --- | --- |
| `00_schema/*/20261008-80` … `-86` | `user_update` `NOT NULL`, uno per schema (acquisti, anagrafiche, catalogo, config, magazzino, pagamenti, vendite); `DEFAULT CURRENT_USER` dove mancava (5 tabelle di config, 2 di magazzino, `vendite.listini_righe_componenti`); le madri partizionate `*.note` portano il vincolo alle partizioni; preCondition «zero NULL» | D-2 |
| `20_code/vendite/20261008-87` | `fn_crea_revisione_preventivo`: lo spento `PENDING` si copia senza marca né pratica | D-3 |
| `20_code/vendite/20261008-88` | `fn_crea_revisione_offerta`: idem | D-3 |
| `20_code/vendite/20261008-89` | building block `trgfn_doc_righe_lock_fuori_bozza`: argomenti `[4]` colonne ammesse fuori bozza (solo UPDATE) e `[5]` stati in cui lo sono; allowlist, colonne tecniche ignorate; montaggio a metà = `E_DOC_RIGHE_LOCK_MONTAGGIO` | D-1 |
| `20_code/vendite/20261008-90` | `ordini_righe`: tre porte, aperta la sola `data_consegna_confermata` in `CONFERMATO`, `PARZIALMENTE_EVASO` (tolto il trigger del solo DELETE) | D-1 |
| `20_code/vendite/20261008-91` | `preventivi_righe`: tre porte, nessuna eccezione | D-1 |
| `20_code/vendite/20261008-92` | `trgfn_ddt_righe_prelievi_guard`: tolto il ramo dello stato della bolla (resta la regola del kit) | regola del 2 |
| `20_code/vendite/20261008-93` | `ddt_righe_prelievi`: il building block a livello RIGA, aperta la sola `ubicazione_arrivo_id` in `EMESSO`, `SPEDITO` | regola del 2 |
| `20_code/dbops/20261008-94` | helper di fixture `dbops.fn_pgtap_porta_a_stato(testata, id, stato)`: percorso più corto della matrice, un UPDATE per passo, guard veri | fixture D-1 |

⭐ **Regola del 2 (§1).** «Fuori bozza tutto chiuso, salvo queste colonne in questi stati» esisteva
già, scritto a mano, nel guard dei prelievi della bolla; con le righe d'ordine è comparso la seconda
volta. Il building block l'ha imparato e la copia dei prelievi è ritirata nello stesso giro. ⚠️ Due
differenze dichiarate nel `-92`: l'allowlist chiude anche `meta` e `storicizza` sui prelievi fuori
bozza (il vecchio confronto non le guardava), e il contesto dell'errore ha le chiavi del building
block. Nessuno scrive i prelievi fuori bozza (zero UPDATE nei corpi DB, il BE non scrive
`ubicazione_arrivo_id`), e nessuno legge quel contesto.

⚠️ **«Stati da evadere» per codice, non per flag.** `config.stati_doc_ordini` ha `fase`, ma `IN_CORSO`
comprende anche `SPEDITO` e `CONSEGNATO` (oggi non raggiungibili dalla matrice), che la decisione non
nomina. Gli stati si dicono per `codice_interno` negli argomenti, come lo stato bozza.

### 4.2 pgTAP

* **Nuovi:** `vendite/test-righe-e-componenti-debiti-residui-v1.sql` (24: helper, D-1 su ordine e
  preventivo, montaggio e livello RIGA su tabella temporanea, prelievi, D-3 su preventivo e offerta,
  tutto costruito); `dbops/test-user-update-not-null-v1.sql` (4: invariante, registro del debito vero,
  registro solo per tabelle senza audit, lente).
* **Building block:** `test-trgfn-doc-righe-lock-fuori-bozza-v1` (test 2: tredici adottanti; test 14
  rovesciato — pinnava la porta aperta e prevedeva il proprio rosso); `test-righe-gemelle-secondo-giro-v1`
  (test 9: sette adottanti a livello RIGA).
* **Fixture:** circa 55 file creavano la testata già fuori bozza e poi ci scrivevano le righe. Ora:
  `DRAFT` → righe → `dbops.fn_pgtap_porta_a_stato`. Dove la conferma vera chiedeva l'aliquota, le righe
  l'hanno presa (nessun guard aggirato). Tre file avevano scritture fuori bozza vere, spostate in bozza
  senza cambiare l'intento (`test-situazione-merce-ritardo-v1`, `test-fn-situazione-merce-ordine-chiusura-v1`,
  e le natura in `test-vw-preventivi-smistamento-v1` / `…-natura-aware-v1`).

### 4.3 Prova pre-apply (2026-10-08, dev, come owner, transazione annullata)

SQL **estratto** dagli YAML (preCondition comprese), mai riscritto.

* D-2: i sette changeSet passano; dopo, restano nullable solo le 9 tabelle del registro e
  `public.v_src`. Fatto datato: zero NULL su tutte le tabelle con audit.
* D-1/D-3: `plpgsql_check` a zero errori sulle tre funzioni toccate; il pgTAP nuovo 24/24; i due del
  building block 21/21 e 31/31.
* **Mutazioni:** senza `-90`/`-91` diventano rossi i test 4, 6, 7, 9, 11-15 (l'8 resta verde: il DELETE
  era già chiuso); senza `-87`/`-88` i test 21 e 23 (`G:false:PENDING:pratica_in_attesa`).
* Fixture: ogni file con lo stesso esito di prima (`--senza`), salvo i tre del §4.5. I rossi che restano
  erano già rossi prima ed erano test di scope (RLS), attesi da owner.
* ⚠️ Da owner la RLS non c'è: la corsa col runner app resta di Tid.

### 4.4 Ricadute fuori dal DB (richieste al team BE)

* **Il verbo di `data_consegna_confermata` dopo la conferma.** Il DB ora lascia aperta quella sola
  colonna in `CONFERMATO`/`PARZIALMENTE_EVASO`; `richiedi_righe_in_bozza` la chiude ancora: serve il
  verbo (stampo: gli override di prezzo) o il dialog di conferma.
* **Test e smoke che scrivono righe fuori bozza:** `backend/apps/vendite/tests/db/test_resi_create_db.py`
  (58-72, ordine `CONFERMATO` poi INSERT di righe) e `backend/scripts/tests/smoke-push-termine-documento-commessa.py`
  (108-140, `clona_ordine` CONFERMATO poi `clona_riga`): stessa correzione delle fixture, bozza → righe →
  transizione.
* **Ciclo di vita della pratica** (`refactor-prezzi.md` §4.7): l'esito di una pratica su un preventivo
  annullato con una riga in attesa ora è respinto dal lock; la pratica resta aperta in coda.

### 4.5 ✅ Tre test che il modello non sa più costruire — skip motivato (Tid, 2026-10-08)

Il lock delle righe rende irraggiungibili, dalle porte del modello, casi che questi test costruivano
scrivendo una riga fuori bozza. I guard che provavano restano (difesa in profondità); è il test che
non ha più una strada. Le prove li lasciano rossi, ed è voluto finché non si decide.

1. **`vendite/test-ordini-guard-conferma-iva.sql` test 7** — la Regola 4 (riga senza aliquota) sul
   rientro `EVASO → CONFERMATO`. Costruiva il caso togliendo l'aliquota a una riga di un ordine EVASO:
   ora rifiutato. In bozza non si può preparare (la riga senza aliquota non si conferma, test 5-6).
2. **`script/test-fn-check-prezzi-autorizzati-v1.sql` test 39-42** — un preventivo EMESSO con una
   riga PENDING (revisione rifiutata) o REJECTED (revisione che ricopia il REJECTED). Un PENDING/REJECTED
   su una riga attiva ferma l'emissione, e fuori bozza la riga non si scrive: il caso non nasce più.
   ⚠️ Nello stesso file i test 13-15 sono stati trasformati dall'agente (l'UPDATE del REJECTED su EMESSO
   ora è il rifiuto del lock, poi «Accetta» acceso e l'annullamento): da confermare.
3. **`vendite/test-fn-crea-revisione-preventivo-riga-completa-v1.sql` test 5 e 8** — la revisione che
   ricopia il REJECTED di una riga, e la rev N+1 che non si emette per quel REJECTED. Stessa ragione.
   I test 1-4, 6, 7 reggono con le righe APPROVED e senza marca (fixture da riscrivere insieme).

Le strade erano tre: (a) `skip()` motivato, (b) trasformare l'asserzione nel rifiuto del lock
(cambia il soggetto del test), (c) ritirarli. ✅ **Decisione di Tid: (a).** Applicata a tutti e tre i
file, compresi i test 13-15 di `test-fn-check-prezzi-autorizzati-v1` (che l'agente aveva trasformati
nella forma (b), quella usata il 2026-10-04 per offerta e ordine nello stesso file: per il preventivo
la scelta è lo skip). Nel file della revisione la riga REJECTED della fixture è diventata una riga
senza marca e il preventivo nasce in bozza ed è emesso per le transizioni: i test 1-4, 6, 7 girano.
Prova (dev, già migrato, come owner): 9/9, 44/44, 8/8, con gli skip dichiarati.

### 4.6 Altro, per Tid

* ✅ **`public.v_src`** esisteva solo su dev (nessun changelog la creava; colonne catastali, owner
  `titodb`): era un residuo, tolto a mano da Tid il 2026-10-09.
* Il registro del debito `user_update` (9 tabelle, tutte senza audit: `dbops.fk_index_policy`,
  `dbops.transaction_ids`, sette di `ui`) chiede di decidere chi scrive la colonna: è un debito, non una
  bonifica, e sta nel presidio a vista.

### 4.7 Il rosso di zeroerp_ci (2026-10-09): la tabella che dbdev non mostrava

Il presidio `dbops/test-user-update-not-null-v1` (test 1) è rosso in CI: `config.tipi_doc_fiscale`
ha `user_update` nullable (e il trigger di audit). Il modello lo dice: il v1
`migrations/00_bootstrap/20250912-01` (changeSet `20250912-02`) le dà le quattro colonne di audit, con
`user_update` nullable. Su **dbdev** la tabella quelle colonne **non le ha**, anche se il suo
`databasechangelog` segna `20250912-02` come eseguito il 2025-09-15: è una deriva di dev, che nessun
changelog spiega. La bonifica `-80…-86` era stata costruita leggendo il catalogo di dev, e per questo
la tabella le era sfuggita. Il presidio, che è un invariante sul catalogo e non un elenco preso da dev,
l'ha trovata alla prima corsa da zero.

✅ **`00_schema/config/20261009-03`**: `ADD COLUMN IF NOT EXISTS` delle quattro colonne di audit con la
forma del v1 (su CI non fa niente, su dev riporta la tabella al modello), poi `user_update SET NOT NULL`.
Niente preCondition: su dev la colonna prima non esiste, e una riga NULL farebbe fallire il migrate
con `23502`, cioè con un errore che si vede. Il seed (`sql/config/tipi_doc_fiscale.csv`) non porta la colonna,
quindi prende il default. Prova su dev in transazione annullata: colonne al loro posto, presidio 4/4.

### 4.8 Esito (2026-10-09)

Tid ha applicato su dev `20261008-80` … `-94` (2026-10-08, 23:46) e `20261009-03` (2026-10-09,
00:18), e ha lanciato i pgTAP col runner: **verdi**, compreso il presidio
`dbops/test-user-update-not-null-v1` su `zeroerp_ci` dopo il `-03` (§4.7).

Nello stesso giro, due rossi di presidio emersi dal cantiere parallelo `brief-db-istanza-nasce-col-ba`
sono stati chiusi lì (§6.15 di quel brief): `20261008-95` (`search_path` di tre DEFINER) e
`20261009-01`/`-02` (modo `COPPIA` dello scope di storico).

⏳ **Resta aperto, non del DB:** le richieste al team BE del §4.4 (il verbo di
`data_consegna_confermata` dopo la conferma; `test_resi_create_db.py` e lo smoke
`smoke-push-termine-documento-commessa.py` in forma bozza → righe → transizione; il ciclo di vita
della pratica su un preventivo annullato). Debiti dichiarati, da portare in brief propri
all'archiviazione: l'L3 dei componenti (§3) e il registro `user_update` delle nove tabelle senza
audit (§2, presidio a vista).

