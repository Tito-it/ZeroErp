# Brief DB — Righe e componenti di documento: allineare preventivo, ordine e DDT a contratto e offerta

> **Chi chiede:** team DB (`dev/db-tid`), 2026-10-08. **A chi:** team DB; poi BE/FE solo se il §3
> lo fa emergere.
> **Origine:** i trovati del §10.8 di `brief-db-righe-esclusione-solo-non-si-vende` (archiviato in
> `work-done/` il 2026-10-08, §14). Quel brief ha messo contratto e offerta sotto le stesse regole e,
> per perimetro, ha lasciato fuori le altre famiglie. Questo brief esiste perché quei quattro punti
> non si perdano con l'archiviazione.
> **Stato:** ✅ **APPLICATO, pgTAP verdi, nessuna regressione (Tid, 2026-10-08).** D-1 decisa da
> Tid: il componente spento **si porta**. Censimento del §3 chiuso (BE e DB). Sei changeSet e i
> pgTAP nel §4; la prova pre-apply nel §4.1, l'esito su dbdev nel §4.2.
> ✅ **Archiviato il 2026-10-08** (decisione di Tid): `test-ddt-gate-emissione-bom-pending-v1`
> ritirato (§4); i tre trovati del §5 sono **un** brief, `brief-db-righe-e-componenti-debiti-residui`
> (in `work-in-progress/`, voce D20 del registro). D19 chiusa.
> **Nel registro dei difetti DB:** voce **D19** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui. Lo stato vive in questo brief: alla chiusura si spunta D19 e la si sposta nel §7.

## 1. Da dove si parte

Il giro di contratto e offerta ha dato alle due famiglie una forma comune:

* la revisione dell'offerta (`vendite.fn_crea_revisione_offerta`, `20261005-19`) porta con sé
  **tutti** i componenti, e rimappa le righe per identità, non per ordine;
* i componenti di contratto e offerta sono chiusi «solo in bozza» dal livello RIGA del building
  block `trgfn_doc_righe_lock_fuori_bozza` (`20261005-16`, `-17`).

Le famiglie vicine (preventivo, ordine, DDT) sono rimaste come erano.

## 2. I quattro punti

### 2.1 ✅ La revisione del preventivo

`fn_crea_revisione_preventivo` copia **solo i componenti attivi** e rimappa le righe con un
`ROW_NUMBER` che si affida all'ordine di assegnazione degli id. La revisione dell'offerta fa
diversamente su entrambi i punti.

✅ **D-1 (Tid, 2026-10-08): il componente spento si porta, spento.** La revisione è lo stesso
documento (lo stesso principio che copia l'emittente, D3 del 20260915-41, e le marche di
approvazione, 20260914-14). Spegnere un opzionale è una scelta reversibile: non portarlo la
cancella, e nella rev N+1 non si potrebbe più riaccendere. È la regola di `fn_crea_revisione_offerta`
dal `20261005-19` (regola del 2). Non cambia cosa si vende: il push preventivo → ordine filtra già i
componenti attivi (`20260914-12`). Revisione e push restano diversi di proposito: la prima copia lo
stesso documento, il secondo ne fa nascere un altro.

La rimappatura per identità non chiede decisioni: è un difetto. Si passa alla forma dell'offerta,
una riga alla volta con `RETURNING`.

### 2.2 ✅ Il lock «solo in bozza» sui componenti di preventivo, ordine e DDT

Mancano. Col livello RIGA del building block è un `CREATE TRIGGER` per tabella, nella forma di
`20261005-17`. ⚠️ Sul preventivo vale la cautela già scritta per le sue righe: prima si censisce il
flusso di approvazione dei prezzi, che scrive anche fuori bozza.

➕ **Non è solo un `CREATE TRIGGER`** (letto il 2026-10-08): i due lettori SECURITY DEFINER del
building block non conoscono tutte e tre le famiglie.

* `script.fn_get_testata_id_di_riga` conosce CONTRATTO, OFFERTA, RESO → si aggiungono PREVENTIVO,
  ORDINE, DDT;
* `script.fn_get_stato_testata_documento` conosce già DDT e ORDINE, non PREVENTIVO → si aggiunge.
  Etichetta «Preventivo <numero> rev. <rev>»: le revisioni hanno lo stesso numero, e senza la
  revisione la frase non dice quale documento è fermo.

Il commento dei due lettori lo dice già: «un tipo nuovo entra col suo primo adottante».

### 2.3 ✅ `user_update` può essere NULL

Su tutte le righe e i componenti di documento, tranne il componente dell'offerta.
`linee-guida-sql.md` §7 lo vuole `NOT NULL`. Il test 4 di
`vendite/test-righe-gemelle-secondo-giro-v1` fissa oggi l'asimmetria come dichiarata: chi chiude
questo punto aggiorna anche quel test.

**Perimetro: le righe e i componenti dei documenti di vendita**, undici tabelle:
`preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe`, `offerte_commerciali_eccezioni`,
`resi_righe`, `fatture_righe` e i quattro `*_righe_componenti` di preventivo, ordine, DDT e contratto.
Tutte hanno `script.trgfn_audit_data_user_generic`, che scrive `user_update` a ogni INSERT e UPDATE:
dopo il vincolo nessuna scrittura cambia. La preCondition pretende zero NULL (precedente
`20261005-14`): se ce ne sono, il migrate si ferma e si guardano a mano.

⚠️ Il debito vero è più largo, vedi §5.2.

### 2.4 ✅ Il nome di `chk_contrighe_comp_quantita_pos`

Il nome dice «positiva», ma il vincolo vieta solo lo zero, come il gemello
`chk_oce_comp_quantita_nz`. Si rinomina in `…_nz`: nessun dato toccato. Lo nomina il test 8 di
`vendite/test-contratti-righe-componenti-v1`.

➕ **Perimetro allargato (letto dal catalogo il 2026-10-08):** il nome sbagliato ce l'hanno **tutti e
quattro** i gemelli: `chk_prevrighe_comp_quantita_pos`, `chk_ordrighe_comp_quantita_pos`,
`chk_ddtrighe_comp_quantita_pos`, `chk_contrighe_comp_quantita_pos`. Tutti `CHECK (quantita <> 0)`.
Stesso difetto, si rinominano insieme.

## 3. Ricadute BE/FE

Da verificare quando si scrive il §2.2: un lock nuovo sui componenti di ordine e DDT può
respingere una scrittura che il backend oggi fa fuori bozza. Il censimento delle scritture si fa
prima del changeSet.

### 3.1 ✅ Il censimento (2026-10-08): nessuna scrittura legittima fuori bozza

È un **fatto datato**, non il motivo del lock: il lock lo chiede il modello, e il censimento dice
solo che nessuno ci va contro.

**Lato BE** (risposta del team BE, 2026-10-08):

* modifica ed eliminazione di un componente da parte dell'operatore: preventivo, ordine e DDT
  passano già da `richiedi_righe_in_bozza` (`ordini_service.py:1063`, `ddt_service.py:761`,
  `preventivi_service.py:1728`). Il trigger DB ripete la stessa regola nel posto giusto;
* componenti creati alla nascita di una riga (`fn_*_riga_componenti_init`, l'UPDATE delle
  attivazioni in `preventivi_repository.py:956`): dentro la creazione della riga, quindi in bozza;
* la cautela sul flusso di approvazione dei prezzi del preventivo: `approvazioni_prezzo_service.py`
  scrive **solo sulle righe** (`preventivi_righe`, `contratti_righe`, le eccezioni dell'offerta),
  mai sui componenti. Per il lock dei componenti non è un ostacolo. Resta valida per un eventuale
  lock sulle **righe** del preventivo, che questo brief non tocca.

**Lato DB** (doc auto-generata, corpi vivi):

* `fn_preventivo/ordine/ddt_riga_componenti_init`: alla nascita della riga, in bozza;
* `fn_push_preventivo_a_ordine`, `fn_genera_ddt_da_ordine`, `fn_crea_revisione_preventivo`: sul
  documento che nasce in DRAFT;
* `script.trgfn_componenti_propaga_qta`: dall'UPDATE della quantità della riga. Su DDT la riga è già
  chiusa fuori bozza; su ordine e preventivo no, vedi §5.1.

**Lato pgTAP**: due test scrivevano fuori bozza per costruire il loro caso (§4).

**Ricadute BE/FE: nessuna.** Il codice d'errore è quello che esiste (`E_RIGA_DOC_NON_BOZZA`), e
il BE lo intercetta già prima.

## 4. Il piano (2026-10-08)

| # | ChangeSet | Cosa |
| --- | --- | --- |
| §2.4 | `00_schema/vendite/20261008-30-rename-componenti-chk-quantita-nz` | i quattro `…_quantita_pos` → `…_quantita_nz` |
| §2.3 | `00_schema/vendite/20261008-31-alter-righe-componenti-user-update-not-null` | `user_update SET NOT NULL` sulle undici tabelle |
| §2.2 | `20_code/script/20261008-32-update-fn-get-stato-testata-documento-preventivo` | + PREVENTIVO |
| §2.2 | `20_code/script/20261008-33-update-fn-get-testata-id-di-riga-tre-famiglie` | + PREVENTIVO, ORDINE, DDT |
| §2.2 | `20_code/vendite/20261008-34-create-trigger-componenti-lock-fuori-bozza-tre-famiglie` | i tre `CREATE TRIGGER`, forma del `20261005-17` |
| §2.1 | `20_code/vendite/20261008-35-update-fn-crea-revisione-preventivo-componenti-per-identita` | tutti i componenti, rimappati per identità |

**pgTAP.** Un file nuovo, `vendite/test-righe-e-componenti-le-altre-famiglie-v1`, che si costruisce
i casi (preventivo, ordine e DDT con un kit, nei loro stati). Più i test esistenti che il cambio
tocca:

* `vendite/test-righe-gemelle-secondo-giro-v1`: il 4 (nessuna differenza di nullabilità), il 5 (il
  proprietario delle tabelle di righe lette dal lettore), il 7 (`DDT` non è più un tipo
  sconosciuto), il 9 e il 10 (sei adottanti a livello RIGA, non tre);
* `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1`: l'elenco degli adottanti;
* `vendite/test-contratti-righe-componenti-v1` (test 8) e i gemelli di preventivo, ordine e DDT: il
  nome del CHECK;
* `script/test-fn-check-prezzi-autorizzati-v1`, test 31: scriveva `REJECTED` su un componente di un
  ordine EVASO. Col lock non si può più, ed è il modello: l'ordine si conferma solo coi prezzi
  autorizzati, quindi un esito non arriva dopo la conferma. Stessa riscrittura dei test 26 e 44
  sull'offerta (rev 2026-10-04);
* `vendite/test-ddt-gate-emissione-bom-pending-v1`: costruiva un ordine **nato CONFERMATO** e gli
  attaccava i componenti. Col lock l'errore finirebbe nel suo `EXCEPTION WHEN OTHERS` e il test
  passerebbe in `skip()` senza dirlo, verde per sottrazione;
* i test sui componenti che pescano dal DB con `LIMIT 1` e si aspettano un errore qualunque
  (`'%'`): su dbdev, dopo il lock, risponderebbe il lock invece della regola che vogliono provare.
  Si portano su documenti in bozza: `test-preventivi/ordini/ddt-righe-componenti-v1` (19-20,
  20-22), `script/test-componenti-helpers-v1` (4-6). Restano test che pescano dal DB (debito già
  noto di quei file), ma ora pescano dove la regola in esame è la prima a parlare;
* ⚠️ `has_check(schema, tabella, descrizione)` nel test 8 di ordine, DDT e contratto verificava
  che esistesse **un** CHECK qualunque: il nome stava solo nella descrizione. Ora si leggono nome
  e definizione dal catalogo;
* `test-trgfn-doc-righe-lock-fuori-bozza-v1` e i conteggi dei trigger (ordine 13 → 14, DDT 14 → 15,
  e il presidio 12a del preventivo per funzione).

✅ **Ritirato (Tid, 2026-10-08): `vendite/test-ddt-gate-emissione-bom-pending-v1`.** Il suo caso
(un ordine porta un componente in attesa fino al DDT) non si costruisce più: ordine confermato
solo coi prezzi autorizzati (D-6) e componenti solo in DRAFT. Il gate del DDT lo prova
`script/test-fn-check-prezzi-autorizzati-v1` (32-35); la strada chiusa la prova
`vendite/test-righe-e-componenti-le-altre-famiglie-v1` (10-12).

### 4.1 La prova (2026-10-08): su un clone, e cosa non copre

Senza una connessione da owner su dbdev, la prova si è fatta su un **cluster PG18 usa-e-getta**
nello scratchpad: schema di dbdev copiato con `pg_dump -s` come app (solo catalogo), dati dei
cataloghi (`config`, `catalogo`, `dbops`, `ui`, `documenti`, `pratiche`, i cataloghi di `vendite`,
`magazzino.causali`), utenti orfani tolti. Nessuna scrittura su dbdev.

* i sei changeSet si applicano dall'**SQL estratto** dagli YAML, preCondition comprese, come owner;
* **85 pgTAP** toccati dal cambio (chi nomina le tabelle dei componenti, i lettori, il BB, la
  revisione, push e genera-DDT, più i presidi trasversali `riferimenti-morti`, `rubinetto`,
  `catalogo-messaggi`): **stesso esito prima e dopo** su tutti, salvo il file nuovo (26/26).
  49 verdi; **35 rossi già prima, per il clone** (fixture che pescano utenti, istanze o scope che
  solo dbdev ha). Quei 35 qui **non dicono niente**: li dice solo la corsa di Tid;
* **controprova**: il file nuovo contro il clone senza un pezzo alla volta. Senza `-35` rossi il
  17 e il 22 (lo spento non si porta); senza `-34` rossi i dieci test del lock e il 26; senza
  `-30`/`-31` rossi 23-25. Il 18 (legame per identità) è verde anche col corpo vecchio: il
  `ROW_NUMBER` nei fatti reggeva, il difetto era di contratto, e il test lo dice;
* ⚠️ la controprova ha trovato un difetto **del test**: sul DDT un componente fuori bozza lo
  fermava già il lock della **riga**, raggiunto dal ricalcolo del prezzo della madre. Stessa
  frase, ma un effetto. Ora il test guarda anche **chi** rifiuta (`pg_temp.chi_rifiuta`).

Non coperto qui: i dati di dbdev (la preCondition del `-31` conta i `user_update` NULL veri: se
ce ne sono, il migrate si ferma, ed è voluto), `plpgsql_check` come owner, la CI da zero.

### 4.2 ✅ L'esito su dbdev (Tid, 2026-10-08)

Migrazione applicata (`20261008-30` … `-35`), pgTAP verdi, **nessuna regressione**. La
preCondition del `-31` è passata: nessun `user_update` NULL sulle undici tabelle. I 35 file che
il clone non sapeva far girare (§4.1) li ha coperti questa corsa.

### 4.3 Documentazione

Aggiornate le pagine `manual/` scritte a mano: `fn_get_testata_id_di_riga`,
`fn_get_stato_testata_documento`, `trgfn_doc_righe_lock_fuori_bozza`, `fn_crea_revisione_preventivo`.
La doc auto-generata si rigenera dall'apply.

## 5. Trovato nel giro, non corretto qui

> ➡️ **Passato il 2026-10-08 al brief `brief-db-righe-e-componenti-debiti-residui`** (un brief solo
> per i tre punti, decisione di Tid): lo stato si legge lì, non qui.

### 5.1 🟡 Righe d'ordine e di preventivo: la quantità cambia fuori bozza

Sulle righe d'ordine il building block è montato **solo sul DELETE**: INSERT e UPDATE restano
aperti di proposito, perché `data_consegna_confermata` cambia dopo la conferma. Le righe del
preventivo non hanno nessun lock (la cautela sull'approvazione dei prezzi). A livello DB quindi la
quantità di una riga d'ordine confermato o di un preventivo emesso si può cambiare, e si può
aggiungere una riga a un ordine confermato. Il BE lo impedisce già (`richiedi_righe_in_bozza`).

Col lock sui componenti succede questo: su una riga **kit** quel cambio viene respinto dal lock del
componente, attraverso la propagazione della quantità o l'init dei componenti. Su una riga
**semplice** passa. È la stessa forma che il `20261005-17` ha corretto sul contratto («un effetto,
non una regola»), solo un livello più in alto. Il lock sui componenti è giusto lo stesso. Il debito
è sulle righe: un lock per colonna, che lasci aperto solo ciò che il dominio cambia dopo la
conferma.

### 5.2 🟡 `user_update` nullable ben oltre le righe di documento

Letto dal catalogo il 2026-10-08: `user_update` è nullable su circa 140 tabelle, in tutti gli schemi
applicativi (`acquisti`, `anagrafiche`, `catalogo`, `config`, `magazzino`, `ui`, `vendite`…).
`linee-guida-sql.md` §7 lo vuole `NOT NULL` ovunque. Non c'è un presidio che lo fermi su una tabella
nuova. Il §2.3 chiude soltanto la famiglia delle righe e dei componenti di documento.

### 5.3 🟡 Un componente spento IN ATTESA passa nella revisione

Il guard di testa della revisione (`fn_check_prezzi_in_attesa`, «prima l'esito, poi la
revisione») guarda solo i componenti **attivi**: uno spento in `PENDING` non blocca, ed è giusto
(uno spento non deve bloccare per sempre). Con D-1 però ora si **copia**, con la sua marca e la
pratica della rev N. Se nella rev N+1 qualcuno lo riaccende, torna un prezzo in attesa legato
alla pratica della revisione vecchia: lo stesso caso che il 20260924-34 ha chiuso per le righe.
Vale identico per l'offerta dal `20261005-19`. Non si decide qui: è del ciclo di vita della
pratica su una revisione superata (`refactor-prezzi.md` §4.7, dominio approvazioni).
