# Brief DB — Revisione dello schema `dbops`: i difetti di codice e i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-11 (brief chiuso e archiviato)

**Giro 1 chiuso e committato** (blocco 1d in `8c75d5682a`). **Decisioni di §4 prese** (Tid, 2026-11-05/06):
tutte, Q1-Q15 (la Q7 non è mai esistita), con la Q14 punto per punto. **Ordine dei giri deciso** (2026-11-06):
si fa tutto lo sviluppo DB, per gravità, e i lavori sugli stessi oggetti vanno insieme (Tid ha delegato
l'ordine alla sessione DB). Il piano è riscritto in §8, giri 2-14. **Giro 2 chiuso** (2026-11-07, §14):
blocchi 2a e 2b (Q16), `20261107-01` … `-19`, applicati su dbdev e sullo scratch, pgTAP verdi, committato
(`93b650e517`). **Giro 3 chiuso** (2026-11-07, §15): i guard ATTIVO, D5, D18, D46, D47, D49, D51,
`20261107-20` … `-27` e i due CSV dei codici, applicati, pgTAP verdi, committato. **Baseline B-7 aggiornata**
(2026-11-07, §16.6): le sole righe di §14.4 e §15.5. **Giro 4 applicato** (2026-11-07, §16): D6 e D53,
`20261107-28` … `-30`, `-33`, `-34`, su dbdev e sullo scratch, pgTAP verdi. **D21 + M18 passa al blocco 4b** (decisione
di Tid, §16.9): registro dei modi e risolutore generato, dopo l'apply del giro 4.
**Blocco 4b scritto** (2026-11-07, §17): D21 + M18, il registro dei modi e i due risolutori generati,
`20261107-31`, `-32`, `-35` … `-40`, due CSV nuovi o cambiati e due codici (1453, 1454); provato sullo scratch e su dbdev.
**Blocco 4b applicato** (Tid, 2026-11-07): pgTAP di §17.5 verdi. **Giro 4 chiuso**: giro 4, blocco 4b e baseline B-7
committati insieme.
**Giro 5, blocco 5a applicato e committato** (2026-11-07, §18): la coda lavori pronta per la RLS, D9;
`20261107-51` … `-56`, sei CSV; quattro decisioni di Tid nel giro (§18.1). Applicato su scratch e dbdev (sul dbdev dopo
la correzione dei 137 lavori senza azienda, §18.6), pgTAP verdi.
Il team BE ha chiuso BE3 e BE6 fino al blocco 4b (§5, 2026-11-07, merge di `Tito-dev`); al team DB resta la
segnalazione S-BE-1 (§5: la frase di due codici nomina le tabelle).
**Giro 5 chiuso** (2026-11-07): blocco 5b applicato da Tid su dbdev e scratch, pgTAP verdi, committato (§18.9).
`dbops.coda_lavori` è sotto RLS. BE10 (a), (b), (c) e BE6 del giro 5 ✅ e **mergiati** (team BE, PR #40, §5); gli utenti
tecnici di `draina_coda_lavori` ci sono tutti, EMITEST compresa. Scelte 1 e 3 di §18.4 ok (Tid). S-BE-2 fatta, con la
regola canale/`run_as` ristretta ai `CODA` di `DOMINIO` (§18.9).
**Giro 6 chiuso** (2026-11-07, §19): Q14 ④ e ⑦, le viste dei lotti rinominate in «congelati» (decisione di Tid),
`20261108-10` … `-13`; applicato da Tid su dbdev e scratch, pgTAP verdi, committato (§19.5).
**Giro 7 applicato** (2026-11-07, §20): D35, D36, D37, D57, `20261108-25` … `-31`, con due decisioni di Tid nel giro
(§20.1: il perimetro del presidio, il tetto dei lookup che cade); applicato da Tid, pgTAP di §20.5 verdi, convergenza
su `shop.ricevute` letta sul catalogo dei due database (§20.9), **committato** (`11203bab2e`). **Giro 7 chiuso.**
**Giro 8 preparato** (§21): i difetti riverificati sulla scheda di oggi; D68 è già chiuso dall'altro cantiere.
**Via al giro 8 dato** (Tid, 2026-11-07, §21.3): dal **`20261108-41`** (dato da Tid), D68 fuori, D63 come da proposta.
**Giro 8 chiuso** (Tid, 2026-11-08, §21.10): `20261108-41` … `-60` applicati su dbdev e scratch, pgTAP verdi,
**committato** (`8bbae0df7b`, in `Tito-dev` con la PR #51).
**Seguito del giro 7 su `shop` scritto** (2026-11-08, §22): `20261108-88` (il presidio della mappa di storico sul catalogo), `-89` (`shop` fra gli schemi dell'app), applicati su dbdev e scratch e committati (`42fd9eefa0`); il §22 resta nel working tree per scelta di Tid.
**Via al giro 7-bis** (Tid, 2026-11-08, dal `20261108-90`): diviso in tre blocchi (§23.3). **Blocco 7-bis-a applicato**
(Tid, 2026-11-08, §23.10): `20261108-90` … `-93` e il CSV del registro su dbdev e scratch, pgTAP di §23.7 verdi.
Blocco a **committato** (`f7ce9855c5`). **Via al blocco 7-bis-b** (Tid, 2026-11-08, §23.11): dal `20261109-31`,
test 14 esteso; il `fk_index_policy.csv` orfano passa al blocco 10d. **Blocco 7-bis-b applicato** (Tid, 2026-11-08,
§23.11.4): `20261109-31` su dbdev e scratch, pgTAP verdi, committato (`286117c2f6`). **Blocco 7-bis-c censito**
(2026-11-08, §23.12), decisioni di Tid prese, **scritto e provato** sullo scratch e su dbdev (§23.12.2-23.12.3). **Blocco c applicato** (Tid, 2026-11-08, §23.12.5): migrazione, convergenza, pgTAP verdi. **Il giro 7-bis è chiuso** e committato. **Giro 9 preparato** (2026-11-08, §24): difetti riverificati, sei nodi. **Via di Tid** (2026-11-08): N1-N6 come da
proposta, dal primo libero. **Giro 9 scritto e provato** sullo scratch (§24.5-24.7): `20261109-40` … `-57`, quattro CSV,
il guardrail dei codici, sei pgTAP nuovi e cinque riscritti.
**Giro 9 applicato** (Tid, 2026-11-08, §24.11): migrazione su dbdev e scratch, pgTAP verdi; **committato**.
**D12-bis deciso** (Tid, 2026-11-08: strada (a)) e **via al giro 10a** dato lo stesso giorno. I numeri `20261109-58` … `-79`
sono concordati con le altre sessioni DB. **Giro 10a preparato** (§25): difetti riverificati, quattro nodi.
**Via sui nodi** (Tid, 2026-11-08: «ok inizia», N1-N4 come da proposta). **Giro 10a scritto e provato** sullo scratch e su
dbdev (§25.6-25.9): `20261109-58` … `-64`, `presidi.csv`, due pgTAP nuovi e due estesi; un nodo nuovo, **N5** (§25.8).
**Giro 10a applicato** (Tid, 2026-11-08): pgTAP verdi; il presidio su tutto il database era lento, curato da `-65` (§25.12).
**`-65` applicato** (Tid, 2026-11-08). **N5 deciso**: A, trigger a mano, nella forma di §25.8, nel giro 10b. Scelte di §25.7 ok.
**Il giro 10a è chiuso.** **Giro 10b preparato** (§26): difetti riverificati, sei nodi, quattro blocchi.
**Via** (Tid, 2026-11-08: N1-N6 come da proposta). **Blocchi 10b-1 e 10b-2 scritti e provati** su scratch e dbdev (§26.5-26.7):
`20261109-66` … `-75`, il CSV e il mirror del registro; 28 BLOCK e 7 REQUIRE ATTIVO mancanti nascono al giro delle automazioni.
**Applicati** da Tid (2026-11-08). Il pgTAP `test-attivo-due-fk-stessa-coppia-v1` era lento: curato da `20261109-76` (§26.10).
**`-76` applicato** (Tid, 2026-11-08): migrazione su dbdev e scratch, pgTAP verdi. **Blocchi 10b-1 e 10b-2 chiusi**, committati e pushati (`cdc563dedb`).
**Via ai blocchi 10b-3 e 10b-4** (Tid, 2026-11-08, §27.1), con due nodi nuovi decisi nel giro (§27.2: la colonna della
scadenza è `cleanup_at`, nome fisso; base vuota = nessuna scadenza). **Scritti e provati** su scratch e dbdev
(§27.3-27.5): `20261109-84` … `-94` e il CSV del registro.
**Applicati** da Tid (2026-11-08): migrazione su dbdev e scratch, pgTAP di §27.6 verdi; scelte di §26.6 ok (il via era su
tutto). **Il giro 10b è chiuso** (§27.9).
**Committato** (`148ec4eb20`). **Giro 10c preparato** (§28): difetti riverificati, sette nodi, tre blocchi; un difetto nuovo
(il registro overlap senza CSV, N7).
**Via al giro 10c** (Tid, 2026-11-08: N1-N7 come da proposta). **Scritto e provato** su scratch e dbdev (§28.5-28.7):
`20261109-95` … `-99`, `20261110-01` … `-06`, tre CSV, R3. Il CSV dell'overlap (N7) si ferma su un fatto tecnico: nodo N7-bis (§28.9).
**Applicato** da Tid (2026-11-08): migrazione su dbdev e scratch, pgTAP verdi (§28.10). ⚠️ Su dbdev `zeroerp_job` non ha
ancora l'EXECUTE sulla procedura nuova: manca la fase post del provisioning.
**Decisioni di Tid** (2026-11-08, §28.11): N7-bis (a), le colonne dell'overlap diventano `jsonb`; le scelte di §27.4 e
§28.6 tutte ok, tranne due che aprono lavoro: `p_cleanup_column` esce dalla firma, `fn_name_from_template` si corregge ora.
Fase post del provisioning su dbdev **fatta** (Tid, 2026-11-08): `zeroerp_job` ha l'EXECUTE sulla procedura nuova.
Giro 10c **committato** (2026-11-08, su richiesta di Tid; non pushato).
**Via al blocco 10c-4** (Tid, 2026-11-08: «ok procedi, l'altro cantiere è fermo»). **Scritto e provato** su scratch e
dbdev (§28.12): `20261110-34` … `-41`, il CSV dell'overlap, un pgTAP nuovo e sei riscritti; trovato e curato un difetto
del riconciliatore ATTIVO sulle partizioni (`-41`).
**Applicato** da Tid (2026-11-09): migrazione su dbdev e scratch, pgTAP verdi. Le dieci righe dell'overlap solo di dbdev
**cancellate** (decisione di Tid, §28.12 punto 2).
Blocco 10c-4 **committato** (`48b5d39354`, 2026-11-09): **il giro 10c è chiuso.** **Giro 10d preparato** (§29, 2026-11-09):
riverifica sulla struttura, nove nodi (N1-N9), tre blocchi; il residuo di §14.8 era una diagnosi sbagliata (§29.1 punto 9).
**Decisioni di Tid** (2026-11-09, §29.4): proposte accettate; numeri `20261110-42` … `-61` riservati, l'altro cantiere dal `-62`.
**Via** (Tid, 2026-11-09). **Giro 10d scritto e provato** su scratch e dbdev (§29.5-29.7): `20261110-42` … `-54`, il CSV unico
(34 laterali cancellati), un pgTAP nuovo; su dbdev nessun indice cambia.
**Applicato** da Tid (2026-11-09): migrazione su dbdev e scratch, pgTAP verdi (§29.10).
**Decisioni di Tid** sulle scelte di §29.6 (2026-11-09, §29.11): le quattro righe delle note delle offerte erano di prova ed
escono; le tre FK di N2 `CON_INDICE`; il resto ok. **Seguito scritto e provato** su scratch e dbdev: il CSV unico e
`20261110-55`.
**Giro 10d chiuso**: committato da Tid (`2050435065`). **Giro 11 preparato** (§30), numeri `20261110-56` … `-61` riservati.
**N1 deciso** (Tid, 2026-11-09: strada (b)). **Giro 11 scritto e provato** su scratch e dbdev (§30.4): `20261110-56` … `-58`,
un pgTAP nuovo. **Giro 11 applicato** (Tid, 2026-11-09): migrazione su dbdev e scratch, pgTAP di §30.4 verdi (§30.5).
**Via al giro 12** (Tid, 2026-11-09: «procedi prossimo step»): Q15, §31. Censimento fatto, nodi N1-N3 decisi e numeri dati
(Tid, 2026-11-09, §31.2): `20261110-59` … `-61`, `-80` … `-84`, e `-94` (rinumerato da Tid) al posto del `-85` preso da `catalogo`.
**Giro 12 scritto e provato** su scratch e dbdev (§31.3-31.4): nove changeSet, i due CSV dei codici, un pgTAP nuovo.
**Giri 11 e 12 applicati e committati** da Tid (`df2fc72b53`, PR #75). **S-BE-2 e S-BE-3 scritti e provati**
(§32, `20261110-95` … `-98`). N4 deciso (strada a). **Giro 13 scritto e provato** (§33, `20261111-14` … `-17`).
**Applicati** da Tid (2026-11-09): S-BE-2, S-BE-3 e giro 13 su dbdev e scratch, pgTAP di §32.4 e §33.5 verdi (§33.6).
**Giro 13 committato** (`aaa12df0ef`, PR #79).
Rosso dopo il merge, `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1` (`E_UOM_MISSING`): non è di questo cantiere,
viene dal giro 2 di `brief-db-revisione-catalogo` (§13.4), dove è registrato; corretta la fixture, verde (Tid, 2026-11-09).
**Giro BE di §33.7 fatto** dal team BE (BE8, S-BE-2 e S-BE-3 lato BE, BE6 dei due codici nuovi; `2af6d986f5`, PR #81):
al team BE non resta niente dei giri applicati.
**Giro 14 censito** (§34), nodi N1-N5 decisi come da proposta, numeri `20261111-18` … `-24` (Tid, 2026-11-09). **Giro 14 scritto e provato** su dbdev (§34.6): sette changeSet, il presidio pgTAP, il guardrail in CI, i CSV e le intestazioni. **Giro 14 applicato** da Tid su dbdev e scratch, pgTAP verdi (2026-11-10, §34.6.6). Doc auto-generata e **commit** (Tid, `fe388dbfdf`): **giro 14 chiuso**, e con lui i giri di §8. Le scelte di §34.6.3 sono applicate così. **S-BE-1 censito** (§35), nodi N1-N6 come da proposta (Tid, 2026-11-10), **scritto e provato** su dbdev (§35.6): `20261111-40` … `-46`, due CSV, un loader esteso, il pgTAP nuovo e sette pgTAP riallineati. **S-BE-1 applicato** da Tid su dbdev e scratch, pgTAP di §35.6.5 verdi, doc auto-generata, **committato** (`67df18ad8d`, 2026-11-11, §35.7): **S-BE-1 è chiuso**, e con lui lo sviluppo DB del brief. Il `-18` corretto per il migrate da zero (§34.6.7, `53e14938ef`).
**N5 chiuso dal team FE** (2026-11-11, passo 9-nonagies-quater): nessun tipo da aggiungere al CSV; il FE apre ora anche ARTICOLO e PROMO_ARTICOLO.
**Doc BE di §35.6.4 riscritta** (team BE, 2026-11-11, passo 9-nonagies-quinquies).
**`key_selector` deciso** (Tid, 2026-11-11, §35.8): le due colonne restano diverse, si corregge il solo COMMENT.
**COMMENT corretto** dalla sessione DB in `20261111-67`, applicato da Tid su dbdev e scratch (2026-11-11, §35.6.4): ⚠️ corregge il primo dei due difetti di §35.8, **non il secondo**: il testo dice ancora «'id' (la PK numerica)», e per ARTICOLO la PK è un uuid.
**Residuo del COMMENT scritto e provato** (sessione DB, 2026-11-11, via di Tid): `20261111-81`, §35.8. **`-81` applicato** da Tid su dbdev e scratch (2026-11-11), riscontrato sul `databasechangelog`. **Brief chiuso e archiviato** (2026-11-11): non riparte nessuno.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Revisione delle 239 pagine `dbops/manual/` allo standard (201 riscritte, 38 nuove); doc fuori schema corretta | §7 | — |
| 2 | ✅ Tid | Si parte dalla classe C; ritiri solo se certi; D17-bis e D74 rimandati (2026-11-04) | §10 | 1 |
| 3 | ✅ sessione DB | Giro C1 scritto e provato sullo scratch; doc riallineata | §10 | 2 |
| 4 | ✅ Tid | Apply del giro C1 su dbdev e scratch (`-09` … `-19`); pgTAP di §10.2 verdi (2026-11-04) | §10.2 | 3 |
| 5 | ✅ Tid | Commit del giro C1; si parte dal giro 1, nei difetti senza decisioni (2026-11-04) | §8 | — |
| 6 | ✅ sessione DB | Giro 1, blocco 1a (D14, D15, D54, D56): scritto e provato sullo scratch | §12 | 5 |
| 7 | ✅ Tid | Apply del blocco 1a; pgTAP di §12.3 verdi (2026-11-04). Un test lento: §12.6 | §12.3 | 6 |
| 7-bis | ✅ Tid | Apply di `20261104-43` e `20261104-45`; i pgTAP di §12.6 e §12.7 verdi (2026-11-04) | §12.6, §12.7 | 7 |
| 7-ter | ✅ sessione DB | Giro 1, blocco 1b (D1 + D26): scritto e provato sullo scratch | §12.8 | 7-bis |
| 7-quater | ✅ Tid | Apply del blocco 1b (`-46` … `-50`); pgTAP di §12.8.3 verdi (2026-11-04) | §12.8.3 | 7-ter |
| 7-quinquies | ✅ sessione DB | Giro 1, blocco 1c (D40, D41): scritto e provato sullo scratch | §12.9 | 7-quater |
| 7-sexies | ✅ Tid | Apply del blocco 1c (`-51`, `-52`); pgTAP di §12.9.3 verdi (2026-11-04) | §12.9.3 | 7-quinquies |
| 8 | ✅ sessione DB | Giro 1, blocco 1d (D43, D7): scritto e provato sullo scratch | §12.10 | 7-sexies |
| 8-bis | ✅ Tid | Apply del blocco 1d; pgTAP di §12.10.3 verdi (2026-11-04). Il giro 1 è chiuso | §12.10.3 | 8 |
| 9 | ✅ Tid | Le decisioni di §4 (2026-11-05/06; la Q6 il 2026-11-04); regola dei COMMENT scritta in `linee-guida-sql.md` §5d | §4 | — |
| 9-bis | sessione DB ✅ | Decisioni registrate in §4, giri riassegnati in §8, richieste BE8 e BE9 in §5 | §4, §5, §8 | 9 |
| 9-ter | ✅ Tid → sessione DB | L'ordine dei giri: tutto lo sviluppo DB, per gravità, lavori collegati insieme (2026-11-06) | §8 | 9-bis |
| 9-quater | ✅ sessione DB | Rosso da zero del blocco 1b curato con `20261103-29`, committato in `206fa0f65f` | §13 | — |
| 9-quinquies | ✅ Tid | Le viste di magazzino (D58, D29, ⑧) confluiscono nel lotto M di `brief-db-sorgente-documento-e-riga` (2026-11-06) | §8.1 | 9-ter |
| 9-sexies | ✅ Tid | Il via al giro 2, con la sequenza `20261107-01` (2026-11-07) | §8 | 9-ter |
| 9-septies | ✅ sessione DB | Giro 2 (D3, D4, D44, D45, D60, R6, R7, Q14 ①): scritto e provato sullo scratch | §14 | 9-sexies |
| 9-octies | ✅ Tid | Apply del giro 2 fino al `-17` (il `-05` rinumerato, §14.7.5); pgTAP come app: tre rossi (2026-11-07) | §14.3 | 9-decies |
| 9-undecies | ✅ sessione DB | I tre rossi: nomi delle tabelle senza schema per l'app, l'indice della FK tolto dalla politica; `-18`, `-19`, CSV | §14.8 | 9-octies |
| 9-duodecies | ✅ Tid | Apply di `-18`, `-19` e di `fk_index_policy_bonifica_ridondanze.csv`; pgTAP di §14.3 verdi (2026-11-07). Il giro 2 è chiuso | §14.3, §14.8 | 9-undecies |
| 9-terdecies | ✅ sessione DB, su richiesta di Tid | Baseline B-7: le sette righe di §14.4 e §15.5, a mano, senza `--update` (le altre differenze sono di altri cantieri) | §16.6 | 9-septdecies |
| 9-quaterdecies | ✅ Tid | Commit del giro 2 (`93b650e517`) e via al giro 3, con i numeri dal primo libero e `%TYPE` (2026-11-07) | §8 | — |
| 9-quindecies | ✅ sessione DB | Giro 3 (D5, D18, D46, D47, D49, D51 con Q8): scritto e provato sullo scratch | §15 | 9-quaterdecies |
| 9-sexdecies | ✅ Tid | Apply del giro 3 (`20261107-20` … `-27`, i due CSV dei codici); pgTAP come app di §15.6 verdi (2026-11-07) | §15.6 | 9-quindecies |
| 9-septdecies | ✅ sessione DB, su richiesta di Tid | Commit del giro 3 (2026-11-07). Il giro 3 è chiuso | §8 | 9-sexdecies |
| 9-octodecies | ✅ Tid | Via al giro 4, dal `20261107-28` e con `%TYPE` (2026-11-07) | §8 | 9-septdecies |
| 9-vicies | ✅ sessione DB | Giro 4 (D6, D53): scritto e provato sullo scratch e su dbdev | §16 | 9-octodecies |
| 9-vicies-semel | ✅ Tid | Apply del giro 4 (`20261107-28`, `-29`, `-30`, `-33`, `-34`) su dbdev e scratch; pgTAP come app di §16.5 verdi (2026-11-07) | §16.5 | 9-vicies |
| 9-vicies-semel-bis | ✅ sessione DB, su richiesta di Tid | Commit del giro 4 e della baseline B-7, insieme al blocco 4b (2026-11-07) | §16, §16.6 | 9-vicies-sexies |
| 9-vicies-bis | ✅ Tid | D21: sede unica col registro dei modi e il risolutore generato, nel blocco 4b dopo l'apply del giro 4 (2026-11-07) | §16.9 | 9-vicies |
| 9-vicies-ter | ✅ Tid | Il perimetro del registro: il gemello SR dentro (generato), i 36 adattatori fuori, con un pgTAP che controlla che nominino un modo del registro (2026-11-07) | §16.9 | 9-vicies-bis |
| 9-vicies-quater | ✅ Tid | Via al blocco 4b (2026-11-07) | §16.9 | 9-vicies-semel |
| 9-vicies-quinquies | ✅ sessione DB | Blocco 4b: registro dei modi, risolutore fiscale e gemello SR generati, FK delle vie; scritto e provato sullo scratch e su dbdev | §17 | 9-vicies-quater |
| 9-vicies-sexies | ✅ Tid | Apply del blocco 4b (`20261107-31`, `-32`, `-35` … `-40`, `emittente_modi.csv`, `processi_bersagli.csv`, i due CSV dei codici) su dbdev e scratch; pgTAP come app di §17.5 verdi (2026-11-07). Il giro 4 è chiuso | §17.5 | 9-vicies-quinquies |
| 9-vicies-septies | ✅ Tid | Via al giro 5, coi numeri `20261107-51` … `-58` e `%TYPE`; decisioni del giro: drenatore per azienda, porta DEFINER, `draina_coda_lavori` di DOMINIO, un lavoro un'azienda (2026-11-07) | §18.1 | 9-vicies-semel-bis |
| 9-vicies-octies | ✅ sessione DB | Giro 5, blocco 5a (Q14 ③, D9): scritto e provato sullo scratch, prima e dopo l'apply | §18 | 9-vicies-septies |
| 9-vicies-nonies | ✅ Tid | Correzione dei dati su dbdev (§18.6 punto 1), apply del 5a su dbdev e scratch, pgTAP di §18.6 verdi (2026-11-07); commit del 5a dalla sessione DB | §18.6 | 9-vicies-octies |
| 9-tricies | team BE ✅, Tid ✅ (EMITEST servita, 2026-11-07, §18.9) | BE10 ✅: (a) un lavoro per azienda dal cockpit, con ownership per azienda (anticipo di BE9), (b) drenatore per azienda, (c) chi accoda, «Esegui ora» SISTEMA; BE6 per i tre codici nuovi ✅ (2026-11-07, mergiati con la PR #40). Utenti tecnici creati da Tid, **manca EMITEST** | §5 | 9-vicies-nonies |
| 9-tricies-semel | ✅ sessione DB | Blocco 5b: l'`ENABLE` della RLS, il debito tolto, la decisione dell'indice della FK, S-BE-2, la guida; scritto e provato sullo scratch (2026-11-07) | §18.9 | 9-tricies |
| 9-tricies-bis | ✅ Tid | Apply del 5b (`20261107-57`, `-58`, `20261108-08`, quattro CSV) su dbdev e scratch; pgTAP di §18.9.2 verdi (2026-11-07); commit dalla sessione DB. Il giro 5 è chiuso | §18.9.2 | 9-tricies-semel |
| 9-tricies-ter | **team BE** ✅ (2026-11-07, committato su `dev/backend-tid`) | Il test di S-BE-2 a SISTEMA (`test_avvio_manuale_catalogo`), BE9 (il filtro di perimetro si ritira, lo fa la RLS) | §18.9.2, §5 | 9-tricies-bis |
| 9-tricies-quater | ✅ Tid | Il via al giro 6, coi numeri dal `20261108-10`; le viste dei lotti rinominate in «congelati» (2026-11-07) | §19 | 9-tricies-bis |
| 9-tricies-quinquies | ✅ sessione DB | Giro 6 (Q14 ④, ⑦): scritto e provato sullo scratch | §19 | 9-tricies-quater |
| 9-tricies-sexies | ✅ Tid | Apply del giro 6 (`20261108-10` … `-13`, `presidi.csv`, `presidi_testi.csv`) su dbdev e scratch; pgTAP di §19.3 verdi (2026-11-07); commit dalla sessione DB. Il giro 6 è chiuso | §19.5 | 9-tricies-quinquies |
| 9-tricies-septies | ✅ Tid | Il via al giro 7, coi numeri dal `20261108-25` e `%TYPE`; nel giro il perimetro del presidio (`tx_id`, `storicizza`, `cleanup_at`) e il tetto dei lookup che cade, con lo spareggio (2026-11-07) | §20.1 | 9-tricies-sexies |
| 9-tricies-octies | ✅ sessione DB | Giro 7 (D35, D36, D37, D57): scritto e provato sullo scratch | §20 | 9-tricies-septies |
| 9-tricies-nonies | ✅ Tid | Apply del giro 7 (`20261108-25` … `-31`, sette CSV e il loader `20260429-08`) e convergenza; pgTAP di §20.5 verdi (2026-11-07) | §20.9 | 9-tricies-octies |
| 9-tricies-decies | **team BE** ✅ (2026-11-07, `aeb59a08e6`) | BE4: il tetto `LOOKUP_MAX_SOURCE_ROWS` cade (`p_limit` NULL), ricerca e paginazione restano — fatto, §5 | §5 | — |
| 9-tricies-undecies | ✅ Tid | Commit del giro 7 (`11203bab2e`). Il giro 7 è chiuso | §20.9 | 9-tricies-nonies |
| 9-tricies-duodecies | ✅ sessione DB | Giro 8 preparato: difetti riverificati sulla scheda del 2026-11-07, D68 passato all'altro cantiere | §21 | 9-tricies-undecies |
| 9-tricies-terdecies | ✅ Tid | Via al giro 8: dal `20261108-41` (dato da Tid), D68 fuori, D63 come da proposta (2026-11-07) | §21.3 | 9-tricies-duodecies |
| 9-tricies-quaterdecies | ✅ sessione DB | Giro 8 (D63, D64, D66, D67, D69, D70, D71, D73, D74): scritto e provato sullo scratch (2026-11-08), `-41` … `-60` | §21 | 9-tricies-terdecies |
| 9-tricies-quindecies | ✅ Tid | Apply del giro 8 (`20261108-41` … `-60`) su dbdev e scratch; pgTAP di §21.7 verdi (2026-11-08) | §21.10 | 9-tricies-quaterdecies |
| 9-tricies-septdecies | ✅ Tid | Commit del giro 8 (`8bbae0df7b`, PR #51 in `Tito-dev`) | §21.10 | 9-tricies-quindecies |
| 9-tricies-sexdecies | ✅ Tid → sessione DB | Via al giro 7-bis dal `20261108-90` (2026-11-08); censimento e tre blocchi | §23.1-23.3 | 9-tricies-quindecies |
| 9-tricies-septdecies-bis | ✅ sessione DB | Blocco 7-bis-a: i sedici cataloghi di `dbops` scritti dal solo seed perdono i marcatori, il registro si svuota, la vista legge l'override; scritto e provato sullo scratch (2026-11-08) | §23.4-23.6 | 9-tricies-sexdecies |
| 9-tricies-octodecies | ✅ Tid | Apply del blocco 7-bis-a (`20261108-90` … `-93`, `marcatori_automazione_debito.csv`) su dbdev e scratch; pgTAP di §23.7 verdi (2026-11-08) | §23.10 | 9-tricies-septdecies-bis |
| 9-tricies-octodecies-bis | ✅ Tid | Commit del blocco 7-bis-a (`f7ce9855c5`) e via al blocco 7-bis-b, dal `20261109-31` (2026-11-08) | §23.10, §23.11 | 9-tricies-octodecies |
| 9-tricies-novemdecies | ✅ sessione DB | Blocco 7-bis-b (`data_update`/`user_update` della classe B, coi CSV e i loader): scritto e provato sullo scratch (2026-11-08), `20261109-31` | §23.11 | 9-tricies-octodecies-bis |
| 9-quadragies | ✅ Tid | Apply del blocco 7-bis-b (`20261109-31`, i cinque loader) su dbdev e scratch; pgTAP di §23.11.3 verdi (2026-11-08) | §23.11.4 | 9-tricies-novemdecies |
| 9-quadragies-semel | ✅ Tid | Commit del blocco 7-bis-b (`286117c2f6`) e via al blocco 7-bis-c | §23.11.4 | 9-quadragies |
| 9-quadragies-bis | ✅ sessione DB | Blocco 7-bis-c: censimento dei montaggi e degli scrittori; quattro nodi (2026-11-08) | §23.12 | 9-quadragies-semel |
| 9-quadragies-ter | ✅ Tid | Le quattro decisioni del 7-bis-c: tutte come da proposta (2026-11-08) | §23.12 | 9-quadragies-bis |
| 9-quadragies-quater | ✅ sessione DB | Blocco 7-bis-c scritto e provato (`20261109-32` … `-39`, due CSV, quattro pgTAP); N2 precisato sulle righe di composizione | §23.12.1-23.12.3 | 9-quadragies-ter |
| 9-quadragies-quinquies | ✅ Tid | Apply del blocco 7-bis-c, convergenza, pgTAP come app verdi (2026-11-08); commit e push dalla sessione DB. Il giro 7-bis è chiuso | §23.12.5 | 9-quadragies-quater |
| 9-quadragies-sexies | **team BE** ✅ (2026-11-08, committato su `dev/backend-tid`) | BE11: lo snapshot rinominato, la data del contenuto, l'audit a mano che si ritira, i rifiuti nuovi del guard | §5 | 9-quadragies-quinquies |
| 9-quadragies-septies | ✅ sessione DB | Giro 9 preparato: riverifica sulla struttura, sei nodi, due blocchi (2026-11-08) | §24 | 9-quadragies-quinquies |
| 9-quadragies-octies | ✅ Tid | Decisioni N1-N6 come da proposta, via al giro 9 dal primo libero (2026-11-08) | §24.4 | 9-quadragies-septies |
| 9-quadragies-nonies | ✅ sessione DB | Giro 9, blocchi 9a e 9b: scritti e provati sullo scratch (`20261109-40` … `-57`) | §24.5-24.7 | 9-quadragies-octies |
| 9-quinquagies | ✅ Tid | Apply del giro 9 su dbdev e scratch, pgTAP di §24.8 verdi (2026-11-08); commit dalla sessione DB. Il giro 9 è chiuso | §24.11 | 9-quadragies-nonies |
| 9-quinquagies-bis | ✅ Tid | D12-bis: strada (a), entra nel giro 10a (2026-11-08) | §24.6, §25 | 9-quinquagies |
| 9-quinquagies-ter | ✅ Tid → sessione DB | Via al giro 10a; numeri `20261109-58` … `-79`, concordati con le altre sessioni DB (2026-11-08) | §25 | 9-quinquagies |
| 9-quinquagies-quater | ✅ sessione DB | Giro 10a preparato: riverifica, quattro nodi, changeSet previsti | §25 | 9-quinquagies-ter |
| 9-quinquagies-quinquies | ✅ Tid | Nodi N1-N4 del giro 10a, come da proposta (2026-11-08) | §25.2, §25.5 | 9-quinquagies-quater |
| 9-quinquagies-sexies | ✅ sessione DB | Giro 10a scritto e provato su scratch e dbdev (`20261109-58` … `-64`) | §25.6-25.9 | 9-quinquagies-quinquies |
| 9-quinquagies-septies | ✅ Tid | Apply del giro 10a (`-58` … `-64`, `presidi.csv`) e pgTAP come app verdi (2026-11-08); il test 4 della convergenza lento | §25.11, §25.12 | 9-quinquagies-sexies |
| 9-quinquagies-nonies | ✅ sessione DB | `20261109-65`: il controllo di `codice_interno` una volta per tabella; 9,2 s → 0,36 s | §25.12 | 9-quinquagies-septies |
| 9-sexagies | ✅ Tid | Apply di `-65` e pgTAP della convergenza (2026-11-08); commit del giro dalla sessione DB (`d8492eeb77`) | §25.12 | 9-quinquagies-nonies |
| 9-sexagies-semel | ✅ Tid | N5: A, il codice di `domini_task` è bloccato, col trigger montato a mano; la forma in quattro punti confermata; le scelte di §25.7 ok (2026-11-08) | §25.7, §25.8 | 9-sexagies |
| 9-sexagies-bis | ✅ Tid → sessione DB | Via alla preparazione del giro 10b (2026-11-08) | §8, §26 | 9-sexagies-semel |
| 9-sexagies-ter | ✅ sessione DB | Giro 10b preparato: riverifica, sei nodi, quattro blocchi | §26 | 9-sexagies-bis |
| 9-sexagies-quater | ✅ Tid | Nodi N1-N6 come da proposta, via ai blocchi 10b-1 e 10b-2 (2026-11-08) | §26.2, §26.4 | 9-sexagies-ter |
| 9-sexagies-quinquies | ✅ sessione DB | Blocchi 10b-1 e 10b-2 scritti e provati (`20261109-66` … `-75`) | §26.5-26.7 | 9-sexagies-quater |
| 9-sexagies-sexies | ✅ Tid | Apply di `-66` … `-75`, pgTAP come app verdi (2026-11-08); le scelte di §26.6 da guardare | §26.8 | 9-sexagies-quinquies |
| 9-sexagies-octies | ✅ sessione DB | `20261109-76`: la grammatica ATTIVO in PL/pgSQL; il test 7,2 s → 0,7 s | §26.10 | 9-sexagies-sexies |
| 9-sexagies-nonies | ✅ Tid | Apply di `-76` su dbdev e scratch, pgTAP di §26.10 verdi (2026-11-08) | §26.10 | 9-sexagies-octies |
| 9-sexagies-decies | ✅ sessione DB, su richiesta di Tid | Commit e push dei blocchi 10b-1 e 10b-2 (`cdc563dedb`, 2026-11-08) | §26 | 9-sexagies-nonies |
| 9-sexagies-septies | ✅ Tid | Via ai blocchi 10b-3 e 10b-4, numeri dal primo libero (2026-11-08); N7 e N8 decisi nel giro | §27.1, §27.2 | 9-sexagies-decies |
| 9-sexagies-undecies | ✅ sessione DB | Blocchi 10b-3 e 10b-4 scritti e provati (`20261109-84` … `-94`, il CSV del registro) | §27.3-27.5 | 9-sexagies-septies |
| 9-sexagies-duodecies | ✅ Tid | Apply di `-84` … `-94` e del CSV su dbdev e scratch; pgTAP come app di §27.6 verdi; scelte di §26.6 ok (2026-11-08). Il giro 10b è chiuso | §27.9 | 9-sexagies-undecies |
| 9-sexagies-terdecies | ✅ sessione DB, su richiesta di Tid | Commit dei blocchi 10b-3 e 10b-4 (`148ec4eb20`, 2026-11-08) | §27 | 9-sexagies-duodecies |
| 9-sexagies-quaterdecies | ✅ sessione DB | Giro 10c preparato: riverifica, sette nodi, tre blocchi | §28 | 9-sexagies-terdecies |
| 9-sexagies-quindecies | ✅ Tid | Nodi N1-N7 come da proposta, via al giro 10c (2026-11-08) | §28.4 | 9-sexagies-quaterdecies |
| 9-sexagies-sexdecies | ✅ sessione DB | Giro 10c scritto e provato (tre blocchi; N7 fermo, N7-bis) | §28.5-28.7 | 9-sexagies-quindecies |
| 9-sexagies-septdecies | ✅ Tid | Apply del giro 10c su dbdev e scratch, pgTAP verdi (2026-11-08) | §28.10 | 9-sexagies-sexdecies |
| 9-sexagies-novodecies | ✅ Tid | Fase post del provisioning su dbdev: `zeroerp_job` ha l'EXECUTE sulla procedura nuova (2026-11-08) | §28.11 | 9-sexagies-septdecies |
| 9-sexagies-vicies-semel | ✅ Tid | N7-bis (a); le scelte di §27.4 e §28.6 (2026-11-08) | §28.11 | 9-sexagies-septdecies |
| 9-sexagies-vicies-bis | ✅ sessione DB | Blocco 10c-4 scritto e provato (`20261110-34` … `-41`): overlap in `jsonb` con il CSV; via `p_cleanup_column` dalla firma; `fn_name_from_template` idempotente, col censimento dei nomi vivi | §28.11 | 9-sexagies-vicies-semel |
| 9-sexagies-vicies-ter | ✅ Tid | Apply del blocco 10c-4, pgTAP come app verdi (2026-11-09); le dieci righe dell'overlap solo di dbdev cancellate dalla sessione DB su decisione di Tid | §28.12 | 9-sexagies-vicies-bis |
| 9-sexagies-vicies | ✅ sessione DB, su richiesta di Tid | Commit del giro 10c (2026-11-08, non pushato) | §28 | 9-sexagies-septdecies |
| 9-sexagies-vicies-quater | ✅ Tid | Commit del blocco 10c-4 (`48b5d39354`, 2026-11-09). Il giro 10c è chiuso | §28.12 | 9-sexagies-vicies-ter |
| 9-sexagies-vicies-quinquies | ✅ sessione DB | Giro 10d preparato: riverifica, nove nodi, tre blocchi (2026-11-09) | §29 | 9-sexagies-vicies-quater |
| 9-sexagies-vicies-sexies | ✅ Tid | Decisioni N1-N9 ✅ e numeri `20261110-42` … `-61` ✅ (2026-11-09); le tre FK di N2 `CON_INDICE` (§29.6) e il via ✅ | §29.4 | 9-sexagies-vicies-quinquies |
| 9-sexagies-vicies-septies | ✅ sessione DB | Giro 10d, blocchi 10d-1 … 10d-3: scritti e provati (`20261110-42` … `-54`) | §29.5-29.7 | 9-sexagies-vicies-sexies |
| 9-sexagies-vicies-octies | ✅ Tid | Apply del giro 10d su dbdev e scratch, pgTAP come app verdi (2026-11-09) | §29.10 | 9-sexagies-vicies-septies |
| 9-sexagies-vicies-nonies | ✅ Tid | Le scelte di §29.6: righe di prova fuori, tre FK `CON_INDICE`, il resto ok (2026-11-09) | §29.11 | 9-sexagies-vicies-octies |
| 9-septuagies | ✅ sessione DB | Il seguito: CSV unico e `20261110-55`, scritti e provati su scratch e dbdev | §29.11 | 9-sexagies-vicies-nonies |
| 9-septuagies-semel | ✅ Tid | Apply del CSV e del `20261110-55` (dbdev), commit del giro 10d (`2050435065`, 2026-11-09). Il giro 10d è chiuso | §29.11 | 9-septuagies |
| 9-septuagies-bis | ✅ sessione DB | Giro 11 preparato: riverifica, un nodo, numeri `20261110-56` … | §30 | 9-septuagies-semel |
| 9-septuagies-ter | ✅ Tid | N1 del giro 11: strada (b), l'etichetta va con la credenziale (2026-11-09) | §30.2 | 9-septuagies-bis |
| 9-septuagies-quater | ✅ sessione DB | Giro 11 scritto e provato (`20261110-56` … `-58`) | §30.4 | 9-septuagies-ter |
| 9-septuagies-quinquies | ✅ Tid | Apply del giro 11, pgTAP come app verdi (2026-11-09) | §30.5 | 9-septuagies-quater |
| 9-septuagies-sexies | ✅ Tid | Commit del giro 11 (`df2fc72b53`) | §30.5 | 9-septuagies-quinquies |
| 9-septuagies-septies | ✅ sessione DB | Giro 12 (Q15): censimento, nodi N1-N3 decisi da Tid, scritto e provato | §31 | 9-septuagies-quinquies |
| 9-septuagies-octies | ✅ Tid | Apply del giro 12, pgTAP di §31.6 verdi, commit (`df2fc72b53`) | §31.6 | 9-septuagies-septies |
| 9-septuagies-nonies | ✅ team BE (`2af6d986f5`, PR #81, con 9-octogies-ter) | BE6 del giro 12: `E_CONTATTI_SOGGETTO_OBBLIGATORIO` nelle politiche d'errore, dopo l'apply | §31.5 | 9-septuagies-octies |
| 9-octogies | ✅ sessione DB | S-BE-2 e S-BE-3 verificati, N4 deciso (a), scritti e provati (`20261110-95` … `-98`) | §32 | 9-septuagies-octies |
| 9-octogies-semel | ✅ sessione DB | Giro 13 (Q10) scritto e provato (`20261111-14` … `-17`) | §33 | 9-octogies |
| 9-octogies-bis | ✅ Tid | Apply di S-BE-2, S-BE-3 e giro 13, pgTAP verdi (2026-11-09) | §33.6 | 9-octogies-semel |
| 9-octogies-ter | **team BE** ✅ (`2af6d986f5`, PR #81, §33.7) | BE8 (giro 13), S-BE-2 e S-BE-3 lato BE, BE6 dei codici `E_CONTATTI_SOGGETTO_OBBLIGATORIO` e `E_SOGGETTO_ID_FISCALE_IMMUTABILE` | §32.4, §33.4 | 9-octogies-bis |
| 9-octogies-quater | ✅ Tid | Commit di §32 e §33 (`aaa12df0ef`, PR #79) | §8 | 9-octogies-bis |
| 9-octogies-quinquies | **team BE** ✅ (`2af6d986f5`, PR #81) | BE8: `session_key` esce da `parameter_repository.py` (non fatto nella PR #77; fatto con la PR #81) | §5, §33.4 | 9-octogies-bis |
| 9-octogies-sexies | ✅ Tid | Via al censimento del giro 14 (2026-11-09) | §8 | 9-octogies-quater |
| 9-octogies-septies | ✅ sessione DB | Giro 14 censito: marche per schema, §3.2 e §3.1 riverificate, cinque nodi | §34 | 9-octogies-sexies |
| 9-octogies-octies | ✅ Tid | Nodi N1-N5 come da proposta; numeri dal primo libero: `20261111-18` … `-24`, le altre sessioni dal `-25` (2026-11-09) | §34.5 | 9-octogies-septies |
| 9-octogies-nonies | ✅ sessione DB | Giro 14 scritto e provato su dbdev (`20261111-18` … `-24`) | §34.6 | 9-octogies-octies |
| 9-octogies-decies | ✅ Tid | Apply del giro 14 su dbdev e scratch, pgTAP di §34.6.5 verdi (2026-11-10) | §34.6.6 | 9-octogies-nonies |
| 9-octogies-undecies | ✅ Tid | Doc auto-generata e commit del giro 14 (`fe388dbfdf`, 2026-11-10) | §34.6.6 | 9-octogies-decies |
| 9-nonagies | ✅ sessione DB | S-BE-1 censito: montaggi, padri, tipi, storia del bersaglio, sei nodi | §35 | 9-octogies-undecies |
| 9-nonagies-semel | ✅ Tid | Nodi N1-N6 di S-BE-1 come da proposta, e il via (2026-11-10) | §35.5 | 9-nonagies |
| 9-nonagies-bis | ✅ sessione DB | S-BE-1 scritto e provato su dbdev (`20261111-40` … `-46`) | §35.6 | 9-nonagies-semel |
| 9-nonagies-ter | ✅ Tid | Apply di S-BE-1 su dbdev e scratch, pgTAP di §35.6.5 verdi, doc auto-generata, commit (`67df18ad8d`, 2026-11-11) | §35.7 | 9-nonagies-bis |
| 9-nonagies-quater | ✅ team FE (2026-11-11) | N5 confermato: dal solo id il FE apre FATTURA, COMMESSA, LOTTO, CONTRATTO, ORDINE_VENDITA, PREVENTIVO, FLUSSO, DEFINIZIONE_WORKFLOW e, **dal 2026-11-11**, ARTICOLO e PROMO_ARTICOLO (deep-link `?open=` delle due liste, BB `useIngressoDaQuery`; l'id dell'articolo è un uuid, BB `idNellaForma`). ASSET, ARTICOLO_COMPONENTE, LISTINO_VERSIONE e le righe **no**: in `tipi_entita.csv` non si aggiungono. Il pulsante apre e basta: riattivare resta dei permessi e del DB. Decisione di Tid: il pulsante sì (2026-11-11) | §35.6.3 | 9-nonagies-ter |
| 9-nonagies-quinquies | ✅ team BE (2026-11-11) | `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md`: la riga del guard di disattivazione dice che il messaggio «nomina la tabella che sta bloccando»; dopo S-BE-1 non è più vero. Riscritta: la frase non nomina tabelle, la figlia che blocca sta nel contesto del registro errori | §35.6.4 | 9-nonagies-ter |
| 9-nonagies-sexies | ✅ Tid (2026-11-11) | `key_selector` di PREVENTIVO e OFFERTA_COMMERCIALE: **dicono il vero tutti e due**. Le due colonne rispondono a domande diverse e **non si unificano**: `config.sorgenti` (con che chiave il lineage collega il documento: `uid`), `config.tipi_entita` (con che chiave lo si raggiunge a video: `id`). Nessun dato cambia; sbagliato è il solo COMMENT della colonna | §35.8 | — |
| 9-nonagies-septies | ✅ sessione DB, Tid | changeSet del COMMENT di `config.tipi_entita.key_selector` come da §35.8. Punto 1 ✅ (`20261111-67`, applicato da Tid su dbdev e scratch il 2026-11-11: non dice più «stessi valori di config.sorgenti»). Punto 2 scritto e provato su dbdev in `20261111-81` (2026-11-11): «'id' (la chiave primaria, numerica o uuid secondo la tabella)»; applicato da Tid su dbdev e scratch il 2026-11-11 | §35.6.4, §35.8 | 9-nonagies-sexies |
| 9-sexagies-octodecies | team BE ✅ (2026-11-09) | `E_GUARD_UTILITY` nella rigenerazione delle politiche d'errore: già in policy, `genera_error_policies --check` pulito | §28.8 | 9-sexagies-septdecies |
| 9-quinquagies-octies | **team BE** ✅ (2026-11-09, `9f540bea72`) | BE2: i due gap che ripetevano un lock del DB ritirati, `DISTINCT`, commenti riscritti | §5 | 9-quinquagies-septies |
| 9-quinquagies-semel | **team BE** ✅ (2026-11-09, `9f540bea72`) | BE12 (il filtro «vivo» dei processi) ✅; BE6 (`W_TXID_BYPASS_PARAMETRO_ASSENTE`) già in policy | §5, §24.9 | 9-quinquagies |
| 9-nonies | ✅ Tid | Q16: la via fusa resta, marcata come soppressa (b, 2026-11-07) | §4 | 9-septies |
| 9-decies | ✅ sessione DB | Giro 2, blocco 2b (Q16): la via soppressa; lettori censiti, scritto e provato sullo scratch | §14.7 | 9-nonies |
| 10 | sessione DB ✅ | Giri 5-14 nell'ordine di §8, uno alla volta, ognuno col suo via e il suo apply: tutti chiusi (giro 14, `fe388dbfdf`) | §8 | 9-vicies-septies |
| 11 | team BE ✅ | Le ricadute di §5, quando il giro DB corrispondente è applicato. BE3, BE6, BE9, BE10, BE11 ✅ (mergiati o committati); BE4 ✅; BE2, BE5, BE7, BE12 ✅ (committati, `9f540bea7`); BE8, S-BE-2 e S-BE-3 lato BE ✅ (`2af6d986f5`, PR #81). S-BE-1 non ha ricadute BE obbligatorie (§35.6.5); resta la doc, passo 9-nonagies-quinquies | §5, §33.7 | 10 |
| 11-bis | ✅ sessione DB, Tid (`67df18ad8d`, 2026-11-11) | S-BE-1 (censito, deciso, scritto, provato, applicato e committato: §35, passo 9-nonagies-ter): la frase di `E_ATTIVO_PADRE_NON_ATTIVO` ed `E_PADRE_INESISTENTE` nomina `schema.tabella` all'operatore. ✅ Modello deciso da Tid (2026-11-07): frase senza tabelle, il padre come bersaglio `config.tipi_entita` nel `DATATYPE`; da dove il trigger sa il tipo resta al DB. Blocco a parte, dopo il 5b | §5 | — |
| 12 | ✅ sessione DB | Pagine `manual/` e guide riallineate a ogni difetto chiuso, insieme al COMMENT ✅ (verificato il 2026-11-11: i `manual/` dei tre trigger, `fn_bersaglio_di_riga`, `fn_check_famiglia_documento_disattivabile`, `fn_riattiva_articolo` e la guida `automazione-db.md` dicono la frase senza tabelle e il bersaglio); brief in `work-done/` (2026-11-11) | §1, §8 | 9-nonagies-septies |

**Decisioni aperte di Tid:** nessuna (il `key_selector` è deciso, §35.8). Le scelte dentro il giro 12 sono in §31.3, da guardare. Nessuna sul giro 10c.
**Da committare:** il `20261111-81` e questo brief, spostato in `work-done/` (2026-11-11). Del resto dello sviluppo nulla: S-BE-1 è committato (`67df18ad8d`), il giro BE di §33.7 è nella PR #81 (`2af6d986f5`). S-BE-2, S-BE-3 (§32) e il giro 13 (§33) sono committati
(`aaa12df0ef`).
I giri 11 e 12 sono committati (`df2fc72b53`). Il giro 10d è committato (`2050435065`). ⚠️ Nel working tree ci sono anche i file del cantiere `catalogo` (`20261110-62` …): non entrano nel commit di questo giro. Il blocco 10c-4 è committato (`48b5d39354`). Il giro 10c (blocchi 1-3) è committato (`6a9fec9a44`). I blocchi 10b-3 e 10b-4 sono committati (`148ec4eb20`). Nulla dei blocchi 10b-1 e 10b-2: committati e pushati
(`cdc563dedb`, 2026-11-08). Sul giro 10a nessuna: le scelte di §25.7 e la forma di N5 (§25.8) sono confermate (2026-11-08). **Da committare:** nulla del giro 10a:
è committato (`d8492eeb77`, 2026-11-08), `-65` compreso, che è ancora da applicare. Del giro 9 nulla: è committato dal 2026-11-08. ⚠️ Nel working tree restano
file dell'altro cantiere (`20261109-25` … `-27`, i suoi pgTAP, il suo brief e le sue righe di `codici_errore.csv` e
`messaggi_errore.csv`): non sono entrati nel commit. Nessuna sul giro 7-bis: il criterio dello scrittore (§20.8.2, punto 2) è confermato
(Tid, 2026-11-07); le scelte del blocco a sono in §23.5, da guardare. **Da committare:** nulla del giro 7-bis: i blocchi a, b e c sono
committati (`f7ce9855c5`, `286117c2f6` e il commit del blocco c, 2026-11-08). ⚠️ Nel working tree
ci sono anche file dell'altro cantiere (`codici_errore.csv`, `presidi.csv`, `presidi_testi.csv`, il suo brief e i suoi
changeSet): non entrano nel commit del blocco. Lato BE, BE4 nel working tree di `dev/backend-tid`.
L'indice della FK della coda: **false confermato** (Tid, 2026-11-07, §18.9).
**Da verificare:** se lo scratch è stato ricostruito con `ci-local.sh --fresh` dopo il `20261103-29` (§13).
⚠️ **Numerazione:** questo cantiere ha preso `20261107-01` … `-27`; il prossimo numero libero del giorno è il
`-28`; il giro 4 ha preso `-28` … `-30`, `-33`, `-34`, il blocco 4b `-31`, `-32`, `-35` … `-40`; il prossimo libero è il
`-41`. Il giro 5 ha preso `-51` … `-58` (il 5b `-57`, `-58`) e `20261108-08` (dato da Tid; `-41` … `-50` e `-59` … `-69`
sono dell'altro cantiere). Il giro 6 ha preso `20261108-10` … `-13` (dato da Tid). Il giro 8 ha preso `20261108-41` … `-60` (dato da Tid). Il giro 7-bis, blocco a, ha preso `20261108-90` … `-93` (dato da Tid; `-86` … `-89` sono dell'altro cantiere e di §22). Il blocco b parte dal `20261109-31` (`20261108-94` … `-99` e `20261109-01` … `-30` sono del lotto M dell'altro cantiere, che li tiene riservati; 2026-11-08). Il giro 7 ha preso `20261108-25` … `-31` (dato da Tid), la
regola 28 di `automation_rules_tbl`, la riga 126 di `storico_scope_policy`, gli id 1-10 del registro nuovo; nessun
codice errore. Gli id dei messaggi presi qui: 1442-1450, 1453-1454 e 1455-1457 (1451 e 1452 li ha presi l'altro
cantiere, giro T.4); 1458 l'ha preso l'altro cantiere, il giro 9 ha preso 1459; il prossimo libero è 1460. Il giro 9 ha
preso `20261109-40` … `-57`. L'altro cantiere aperto
(`brief-db-sorgente-documento-e-riga`) numera oggi nel blocco `20261106-74` … `-87`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-04; decisioni registrate il 2026-11-06. **A chi:** Tid e team DB; §5 al team BE.
> **Origine:** verifica delle pagine `docs/it/dbzero/dbops/manual/` contro lo standard e contro il
> codice, chiesta da Tid il 2026-11-03: «per la doc procedi, per le anomalie di sviluppo un brief».
> Stessa forma del precedente sullo schema `maintenance`
> ([brief-db-revisione-maintenance](../work-done/brief-db-revisione-maintenance.md), chiuso il 2026-11-03),
> di cui qui non si ri-segnala nessun punto chiuso.
> **Brief vicini verificati:**
> [framework-automazione-db-migliorie](framework-automazione-db-migliorie.md) (2026-03) tocca gli stessi
> runner delle automazioni, ma come elenco di migliorie: recupero da esecuzione parziale, naming del
> populate, trigger manuali contro generati, validazione dell'ambito. Si sovrappone solo a D41 (la parte
> fuori ambito) e a D17-bis (vocabolari chiusi, §2.4 di quel brief): lì vanno annotati, non rifatti. Se i
> due vanno fusi lo decide Tid.
> [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md) §8.1 censisce le fixture
> della bolla e il predicato «natura è merce»: D71 e D72 completano quel censimento.
> [brief-db-sorgente-documento-e-riga](../work-done/brief-db-sorgente-documento-e-riga.md) (aggiunto il 2026-11-06): il suo
> lotto M riscrive le tre viste di magazzino, e porta anche D58, D29 e Q14 ⑧ (decisione di Tid, §8.1). Nessun altro brief aperto tratta i
> difetti qui sotto.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata
(`docs/it/dbzero/<schema>/funzioni/…`), non dagli YAML citati qui: i riferimenti `file:riga` servono a
trovare il punto. Le righe `funzioni/…md:N` sono della scheda auto-generata al 2026-11-03.

⚠️ Ogni difetto è stato ricontrollato sul corpo dalla sessione che ha rivisto il lotto; D1, D3, D5 e D6
anche da chi scrive il brief (✔︎). Prima di scrivere il changeSet si riverifica sulla scheda del giorno.

## 1. Il perimetro

I difetti del **codice** e dei **metadati** dello schema `dbops`, più quelli di altri schemi trovati
leggendo i suoi chiamanti (§6). La documentazione è già allineata: le pagine `manual/` descrivono il
comportamento di oggi, difetti compresi, e vanno aggiornate quando un difetto si chiude.

Ogni difetto si regge sul modello, non su un conteggio: dove compare un numero è un fatto datato.

## 2. I difetti di codice

Forma compatta: **fatto** (dove e perché il modello non lo ammette) · **correzione** · **presidio**.

### 2.0 Le tre classi

I difetti sono esposti per tema (§2.1-§2.9); qui sono pesati. Per la regola zero tutti e tre i tipi
sono difetti: il peso dice l'ordine dei giri, non se si fanno.

* **A — contraddice un contratto deciso, o è sbagliato ogni volta che il ramo si percorre** con la
  configurazione e i seed di oggi (un presidio che dice il falso, una porta che fallisce appena la si
  usa, una fixture che produce una forma che l'applicazione non produce).
* **B — latente**: il modello ammette il caso, ma oggi nessun seed né configurazione lo produce (una
  regola scritta male, due FK corte verso lo stesso padre, un canale che cade, una corsa concorrente).
* **C — pulizia**: copie senza divergenza, oggetti senza chiamanti, etichette sbagliate senza effetto.

| Classe | Difetti |
| --- | --- |
| **A** — D14, D15, D54, D56 ✅ scritti nel giro 1a (§12); D1 ✅ nel blocco 1b (§12.8); D40, D41 ✅ nel blocco 1c (§12.9); D43 ✅ nel blocco 1d (§12.10); D3, D4, D44 ✅ nel giro 2 (§14); D46, D47, D51 ✅ nel giro 3 (§15); D6, D53 ✅ nel giro 4 (§16), D21 ✅ nel blocco 4b (§17); D35, D36, D37, D57 ✅ nel giro 7 (§20) | D1 (contratto del 2026-07-22: un dblink fallito restituisce la sentinella), D3, D4, D6, D14, D15, D21, D25, D30 (cinque righe del seed senza prefisso), D35, D36, D37, D40, D41, D43, D44, D46, D47, D51, D53, D54, D56, D57, D58, D59, D63, D64, D66, D67, D68, D70 |
| **B** — D26 ✅ nel blocco 1b (§12.8); D7 ✅ nel blocco 1d (§12.10); D45, D60 ✅ nel giro 2 (§14); D5, D18, D49 ✅ nel giro 3 (§15) | D2, D5, D7, D8, D9, D10, D11, D12, D13, D16, D17, D18, D19, D20, D22, D23, D24, D26, D27, D28, D29, D32, D33, D34, D38, D39, D45, D49, D52, D60, D69, D71, D73 |
| **C** | D17-bis, D42, D48, D50, D55, D61, D62, D65, D72, D74 — ✅ scritti nel giro C1 (§10) tutti tranne D17-bis e D74; di D61 restano i quattro strumenti DBA (Q9) |

⚠️ D31 non c'è: il ramo del `tx_id` non registrato l'ha già giudicato il brief chiuso
`brief-db-coerenza-tx-id-non-registrato` (2026-07-22), e resta solo il COMMENT falso (M11).

### 2.1 I difetti puntuali del modello

#### D1 ✔︎ — `fn_get_or_create_session_tx_id`: un canale di log irraggiungibile blocca ogni scrittura tracciata

* **Fatto.** `PERFORM script.fn_ensure_logconn()` (`funzioni/fn_get_or_create_session_tx_id.md:43`) sta
  fuori dal blocco protetto (`:83`). `fn_ensure_logconn` assorbe solo `duplicate_object` e `53300`: un
  errore di connessione di classe 08 risale a `trgfn_tx_id_managed`, che lo trasforma in
  `E_TXID_GENERATION` e solleva. Con `myapp.dblink_log_connection` impostato e il canale giù, fallisce
  ogni INSERT/UPDATE senza `tx_id` su ogni tabella tracciata, e `script.fn_log_error_only` smette di
  registrare e comincia a sollevare. Il commento dice «non blocca mai il chiamante».
* **Correzione.** La chiamata dentro il blocco protetto, o `fn_ensure_logconn` che assorbe ogni errore
  di connessione con un WARNING; commento corretto.
* **Presidio.** pgTAP con una stringa di connessione che non si connette e `logconn` assente: la
  funzione restituisce `uuid_nil` senza sollevare, un INSERT su una tabella tracciata riesce.

#### D2 — Parametri `CLEANUP` non validati: un termine malformato ferma il giro e gli INSERT dei registri

* **Fatto.** `ttl_days`, `apply_on_update`, `batch_limit` si convertono fuori dalla rete degli errori
  (`funzioni/fn_run_automations_cleanup.md:126-127,244`) e, per `ttl_days`, in un `BEFORE INSERT`
  (`funzioni/trgfn_cleanup_at_alla_nascita.md:53`). `automation_rules_tbl.params` non ha CHECK. Un
  `ttl_days` non numerico rende impossibile scrivere su `event_log`, `request_log`, `idempotency_keys` e
  sui registri dei login (il login fallisce); uno negativo fa nascere righe già scadute.
* **Correzione.** Validare i `params` quando la regola entra (CHECK o guard: intero ≥ 0, booleano,
  > 0), oppure conversioni dentro la rete con un salto `INVALID_PARAMS`.
* **Presidio.** pgTAP: una regola con `ttl_days` testuale è respinta; il runner in simulazione la salta.

#### D3 ✔︎ — `fn_admin_merge_stradario`: la fusione fallisce appena la via ha un indirizzo

* **Fatto.** L'UPDATE di `anagrafiche.indirizzi_dettaglio.stradario_id` (`funzioni/fn_admin_merge_stradario.md:63-64`)
  non accende `zeroerp.maintenance_indirizzi_dettaglio`: `trgfn_indirizzi_dettaglio_protect_update`
  rifiuta con `E_COLONNA_NON_MODIFICABILE` e la fusione si annulla. Due indirizzi identici sulle due vie
  collidono su `uq_indirizzi_dettaglio_norm_v2`. D8 del brief maintenance dice che «nessun verbo» sposta
  gli indirizzi su un'altra via: il verbo c'è, ed è questo, ma non apre la porta.
* **Correzione.** Se è la riclassificazione delle vie (decisione §4): flag acceso con `set_config(…, true)`
  solo attorno all'UPDATE, spento all'uscita e nel gestore; regola sui doppioni (rifiuto con codice o
  unione). Altrimenti ritiro.
* **Presidio.** pgTAP con due vie e un indirizzo: la fusione lo ripunta, e subito dopo il cambio a mano è
  ancora rifiutato; più un caso col doppione.

#### D4 — `fn_admin_merge_comune` ripunta solo lo stradario

* **Fatto.** L'unico UPDATE è su `config.stradario.comune_id`. Restano sul comune soppresso
  `config.codici_postali`, `anagrafiche.indirizzi`, `anagrafiche.soggetti`,
  `anagrafiche.indirizzi_soggetti`, `vendite.area_geografica_fatturazione_comuni` (tutte FK `comune_id`);
  `uq_stradario_comune_stradario_gen_cp` può respingere l'UPDATE. Il COMMENT dice «chi riferiva l'origine».
* **Correzione.** Figlie derivate da `pg_constraint`, regola sulle collisioni; oppure COMMENT ristretto.
* **Presidio.** pgTAP: dopo la fusione nessuna figlia (da `pg_constraint`) nomina l'origine.

#### D5 ✔︎ — `trgfn_child_requires_active_parent`, `trgfn_child_requires_non_obsolete_parent`: il ramo «padre non trovato» non scatta mai

* **Fatto.** `IF NOT FOUND` dopo `EXECUTE … INTO` (`funzioni/trgfn_child_requires_non_obsolete_parent.md:128-130`):
  `EXECUTE` non aggiorna `FOUND`, che resta quello della `SELECT INTO` precedente. Su un require
  polimorfo senza FK, un padre assente risponde «padre non attivo» nel primo e lascia passare la scrittura
  nel secondo.
* **Correzione.** `GET DIAGNOSTICS … ROW_COUNT`, o `INTO STRICT` con `NO_DATA_FOUND`.
* **Presidio.** pgTAP su TEMP: require polimorfo verso un id inesistente, per entrambe.

#### D6 ✔︎ — Il riconoscimento dei trigger ATTIVO per argomenti non riconosce niente

* **Fatto.** `fn_trigger_exists_block_by_args` e `…_require_by_args` cercano gli argomenti separati da
  `','` (`funzioni/fn_trigger_exists_block_by_args.md:32`), ma `pg_get_triggerdef` li scrive separati da
  `', '`: rispondono sempre falso. Tutte e tre, con `fn_drop_triggers_by_function_args`, cercano
  `dbops.<funzione>(`: PostgreSQL scrive lo schema solo se non è nel `search_path`, e `dbops` è nel default
  di `zeroerp_app` (`scripts/sql/provision_zeroerp.sql:312`). `ILIKE` tratta `_` come jolly. Le strategie
  `BY_FUNCTION`/`BOTH` per ATTIVO sono quindi finte: con `BOTH` (il seed) decide il solo nome, con
  `BY_FUNCTION` ogni giro toglie e ricrea, e la riconciliazione dipende da chi lancia il runner.
* **Correzione.** `t.tgfoid` contro la funzione risolta per schema e nome, e
  `dbops.fn_trigger_argomenti(t.tgargs)` uguale all'array atteso, nelle tre.
* **Presidio.** pgTAP su TEMP: block/require montati dal generatore riconosciuti; un argomento diverso no;
  stesso esito con `dbops` nel `search_path`.

#### D7 — `vw_riferimenti_morti_rientrati`: con la misura fallita dà per rientrate le voci del registro

* **Fatto.** Cerca per ogni voce un difetto `REALE`/`ORFANA` (`views/vw_riferimenti_morti_rientrati.md:24-27`):
  se `plpgsql_check` non ha misurato la funzione esentata (`NON_MISURATO`), la voce esce «da togliere».
  Il guardrail CI conosce il caso e si ferma prima (`scripts/sql/guardrail_riferimenti_morti.sql:84-114`),
  la vista e il digest no. Le anti-join sono scritte due volte, nelle viste e nel guardrail.
* **Correzione.** Escludere le voci con `NON_MISURATO`, o niente righe se la misura ne ha; valutare un
  guardrail che legge le viste.
* **Presidio.** pgTAP con una voce su una funzione costruita perché `plpgsql_check` sollevi.

#### D8 — `vw_duplicate_indexes` propone di togliere l'indice che regge un vincolo

* **Fatto.** Esclude solo la chiave primaria e ordina per `indisunique DESC, indexrelid`
  (`views/vw_duplicate_indexes.md:30,42`): fra due UNIQUE identici può proporre il DROP di quello del
  vincolo, o della replica identity. La sorella per prefisso li esclude.
* **Correzione.** Indici di vincolo (`conindid`) e di replica identity prima nell'ordinamento, ed esclusi
  da `indici_da_droppare`.
* **Presidio.** pgTAP con due UNIQUE identici, uno di vincolo.

#### D9 — `fn_accoda_lavoro` può restituire un id vuoto senza aver accodato

* **Fatto.** Dopo `INSERT … ON CONFLICT DO NOTHING RETURNING id` vuoto, la rilettura
  `stato IN ('PENDING','IN_CORSO')` prende uno snapshot nuovo: se il drenatore ha chiuso il lavoro vivo
  nel frattempo, la funzione restituisce NULL. `fn_accoda_chiusura_scadenze` conterebbe l'azienda come
  accodata, e la sua chiusura slitterebbe alla sveglia dopo.
* **Correzione.** Ripetere l'INSERT se la rilettura non trova il vivo (ciclo dell'upsert), o sollevare.
* **Presidio.** pgTAP a due sessioni (dblink).

#### D10 — `fn_run_automations_attivo`: due FK dalla stessa figlia allo stesso padre, la seconda resta scoperta

* **Fatto.** Template `trg_{child}_a10_{parent}_require_attivo_ins_upd_{fkhash6_if_long}`
  (`80_data/sql/dbops/automation_rules_tbl.csv:4`): l'hash entra solo oltre 63 caratteri, due FK corte
  della stessa coppia danno lo stesso nome e con `BOTH` il runner salta la seconda.
* **Correzione.** `{fkhash6}` sempre, dopo il censimento dei nomi condivisi su dbdev.
* **Presidio.** pgTAP su TEMP con una figlia a due FK: due require e due block.

#### D11 — `dbops.processi`: il ritiro ha due colonne, e i lettori ne leggono una ciascuno

* **Fatto.** Regola di accensione, guard della scelta a mano e sveglia guardano solo `obsoleto_dal`
  (`funzioni/fn_processo_acceso_su_valori.md:23`, `trgfn_processi_accensione_guard.md:57`,
  `maintenance/funzioni/fn_sveglia_accesa.md:51`, `chk_processi_accensione`); panorama, presidi e roster
  `attivo AND obsoleto_dal IS NULL` (`views/vw_processi_programmazione.md:69`, `vw_processi_roster.md:29`).
  Un processo `attivo = false` senza data ha la sveglia accesa, gira, e il panorama non lo mostra.
* **Correzione.** Un CHECK che vieta `attivo = false` senza `obsoleto_dal` (una sede sola del ritiro),
  oppure la regola che legge anche `attivo` (decisione §4).
* **Presidio.** pgTAP costruito sul ramo scelto.

#### D12 — `trgfn_tx_id_managed`: senza il parametro del bypass, l'override di sessione è ignorato

* **Fatto.** Senza riga `tx_id_bypass_enabled` (o con `default_value` NULL) `v_bypass_enabled` resta NULL
  (`funzioni/trgfn_tx_id_managed.md:53`), `IF NOT v_bypass_enabled` (`:93`) non entra e
  `myapp.bypass_tx_id_check` non si legge. `E_ERRORE_PARAMETRI_TABELLA` qui non blocca, contro la
  convenzione E_/W_.
* **Correzione.** `COALESCE(v_bypass_enabled, false)`; un `W_` dedicato, registrato.
* **Presidio.** pgTAP senza la riga del parametro e con il bypass di sessione: sentinella, nessuna generazione.

### 2.2 La stessa regola scritta più volte, già divergente (regola del 2)

| # | Regola | Dove sono le copie | Correzione | Presidio |
| --- | --- | --- | --- | --- |
| D13 | **L'ambito di una corsa** | `fn_run_automations` (`:31-50`) ricalcola invece di chiamare `fn_resolve_scope` (`:22-55`); `fn_resolve_scope` non fa DISTINCT sul registro né `btrim` sull'elenco del chiamante; `fn_seed_fk_index_policy` (`:36`) guarda solo lo schema e ignora `table_like`, e da zero gira prima del seed dell'ambito (`20_code/dbops/20260116-06…:12`), quindi non registra niente | Tutti passano da `fn_resolve_scope` + `fn_table_in_scope`; `array_agg(DISTINCT btrim(…))` | pgTAP su `fn_resolve_scope` (spazi, `*all`, vuoto, schema su più righe); presidio sul testo: nessun runner legge `automation_scope` direttamente |
| D14 | **Il corpo di una funzione senza commenti** | `vw_codici_errore_da_dichiarare`, `vw_bersagli_non_dichiarati`, `vw_magazzino_dipendenze_inverse` tolgono solo `--`; `vw_funzioni_check_codici`, `vw_punti_canale_campo` anche `/* */`; `vw_codici_errore_forme_condizione` solo le righe che iniziano con `--`; `vw_punti_primo_motivo` niente; anche `vw_audit_log_scrittori_fuori_perimetro`, `vw_stati_check_scrittori`. Nessuna rispetta un `--` dentro un letterale: un codice dopo `'--'` sfugge a un cancello, un nome in un commento a blocco accende un cancello | Un BB `fn_prosrc_senza_commenti(text)` IMMUTABLE che rispetta i letterali; censimento con grep `regexp_replace(p.prosrc` | pgTAP con una funzione in `pg_temp` (codice in commento a blocco, codice dopo `'--'`) + presidio sul testo che le viste chiamano il BB |
| D15 | **Il corpo di una funzione `BEGIN ATOMIC`** | `vw_audit_log_scrittori_fuori_perimetro` (`:23`), `vw_stati_check_scrittori` (`:42`, include `lanname = 'sql'`), `fn_find_function_usage` (`:27`), `fn_search_column_usage` (`:62`) leggono `prosrc`, vuoto per `BEGIN ATOMIC` (linee guida SQL §5c): un cancello non vede lo scrittore, un `ESENTE` non diventa mai `DEBITO_ESTINTO` | `prosrc` + `pg_get_functiondef` dove `prosqlbody IS NOT NULL`; si fonde con D14 nello stesso BB | Una `BEGIN ATOMIC` costruita in `test-audit-log-perimetro-scrittori-v1.sql` e `test-stati-check-scrittori-v1.sql` |
| D16 | **La scadenza `CLEANUP_AT`** | `fn_cleanup_at_params` (`:55-64`) prende una regola, senza `exec_mode` né esclusioni; il runner (`fn_run_automations_cleanup.md:66-101`) tutte, con i filtri; senza `base_ts_column` il trigger alla nascita usa `now()` (`:68`), il runner la catena `data_insert` → `executed_at` → `occurred_at` → `created_at` (`:130-140`); il trigger scrive sempre `cleanup_at`. Una tabella esclusa col trigger riceve scadenze mai purgate | Un risolutore unico usato da trigger e job, con filtro, esclusioni e catena; il trigger scrive la colonna dichiarata | pgTAP: due regole sulla stessa tabella, una esclusa, una con solo `executed_at` → stessa scadenza da trigger e job |
| D17 | **La strategia di esistenza** | Ricopiata in `fn_run_automations_tx_id` (`:120-123`), `_audit_update` (`:89-92`), `_storico` (`:130-133`), `_date_validita` (`:90-93`), `_attivo`; un valore diverso da `BY_NAME`/`BY_FUNCTION`/`BOTH` vale «c'è già», in silenzio | `dbops.fn_trigger_esiste(rel, strategia, nome, schema_fn, nome_fn)` che rifiuta una strategia sconosciuta | pgTAP con una strategia sconosciuta: errore o `WARN`, non silenzio |
| D17-bis | **I vocabolari del registro delle regole** | `rule_type`, `exec_mode`, `existence_strategy`, `col_role` sono `text` senza CHECK; `exec_mode` non si normalizza (anche `fn_run_automations_storico_provision` confronta letterale, `_storico` con `upper(btrim)`) | CHECK sui valori, con bonifica — da annotare in `framework-automazione-db-migliorie` §2.4 | INSERT fuori vocabolario che fallisce |
| D18 | **La grammatica degli argomenti dei trigger ATTIVO** | Minimi (3 e 4) e default (`id`, `attivo`) in `fn_trigger_attivo_orfani` e nelle due trgfn; `fn_ritira_attivo_eccezioni` indicizza le posizioni | Una funzione che restituisce gli argomenti normalizzati per nome (linee guida trigger, lettori di `tgargs`) | pgTAP di confronto su trigger di fixture |
| D19 | **Il nome del trigger DELETE_BLOCK** | Composto nel runner (`fn_run_automations_delete_block.md:59-62`) e in `fn_apply_delete_block_trigger.md:39-42`, senza `fn_name_from_template` e il primo senza `NULLIF`: `trigger_name = ''` annuncia «would be created» a ogni giro; una tabella oltre 38 caratteri fa troncare il nome, il controllo per nome non lo trova e il giro dopo prende 42710 (`E_DELETE_BLOCK`) | Nome composto in un posto, con `fn_name_from_template` e `NULLIF` | pgTAP su una tabella di 50 caratteri: due giri, un trigger |
| D20 | **Il nome del trigger di storico** | Ripiego `trg_z90_{table}_storico_upd_dlt` (`fn_run_automations_storico.md:115`) contro il seed `trg_{table}_z90_storico_upd_dlt` (`automation_rules_tbl.csv:6`): una regola `STORICO` senza template monterebbe un secondo trigger | Default uguale al seed, o `name_template` obbligatorio per `STORICO` | CHECK o pgTAP |
| D21 | **Le vie dell'emittente** | `chk_processi_bersagli_via` (`00_schema/dbops/20260904-08…:84`): fiscale, soggetto_ruolo, fattura, contabile, padre; `script.trgfn_guard_emittente_scope` e il risolutore: soggetto_ruolo, fattura, fiscale, contabile, listino, magazzino. Il COMMENT (`:99`) dice «stesso vocabolario» | Una sede del vocabolario, con listino e magazzino, `padre` ricondotto alla via vera | pgTAP che confronta il CHECK con i modi del risolutore letti dalla definizione |
| D22 | **La convenzione dei codici errore** | CHECK `chk_messaggi_errore_codici_legacy_non_conforme` (`00_schema/dbops/20260805-28…:84-85`) e `c_convenzione` in `scripts/sql/guardrail_codice_errore_strutturato.sql:65-77`, che dice «deve restare IDENTICO … nessuno se ne accorge» | Una funzione IMMUTABLE usata da entrambi, o il guardrail che legge `pg_constraint` | pgTAP |
| D23 | **Il nome dell'indice di una riga di policy** | `vw_indici_ridondanti_prefisso` (`:56`) con un LIKE sul nome dell'indice seguito da «ON» (suffissi e `_` jolly → falso `AUTOMAZIONE_FK`); `apply_fk_index_policy` con la sesta parola | Una funzione unica | pgTAP con un nome suffisso di un altro |
| D24 | **Il pattern di un parametro FK surrogato** | `vw_parameter_fk_surrogate_dangling` (`:22,34`) unisce tutti i pattern; `script.fn_check_parameter_fk_surrogate` (`:58`) ne sceglie uno (EXACT, poi il più lungo) | Un risolutore unico, la vista con `LATERAL … LIMIT 1` | pgTAP con EXACT e LIKE sullo stesso codice |
| D25 | **Il lock implicito di `codice_interno`** | `fn_lock_columns_divergenze` (`:79`) lo mette nel lock atteso di ogni tabella che ha la colonna; `vw_non_editable_fields` (`:20-21`) legge solo il registro e non filtra `exec_mode`; il BE compensa a mano (§5) | Un risolutore unico del lock atteso letto da vista e runner | pgTAP: tabella con `codice_interno` e senza riga → `fn_non_editable_fields` lo elenca |
| D26 | **L'interruttore `myapp.log_with_dblink`** | Assente = spento in `fn_audit_*`, acceso in `script.fn_ensure_logconn` (`:23`); `fn_get_or_create_session_tx_id` lo aggira se c'è la stringa di connessione (`:98-123`) | Un BB «il canale è acceso?» con un default solo | pgTAP con `off` e la stringa impostata: sentinella, GUC non pubblicato |
| D27 | **I nomi delle colonne di audit** | `fn_run_automations_audit_update` usa gli override `AUDIT_TS`/`AUDIT_USER` (`:78-79`) solo per decidere se montare; il trigger nasce senza argomenti (`:114-118`) e `script.trgfn_audit_data_user_generic` scrive nomi fissi: con l'override il trigger fallisce alla prima scrittura | Argomenti al trigger, o ritiro della manopola | pgTAP con colonne rinominate e override |
| D28 | **Le condizioni strutturali della distinta** | Le `condition_expr` di `lock_columns_conditional` su `is_composito`, `requires_serial`, `is_solo_componente` (`80_data/changelog/20260522-04…`, `20261013-04…:57`) ricopiano l'`EXISTS` di `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva` (già divergite: `CURRENT_DATE` contro `fn_data_operativa`) | Predicati in funzioni `catalogo.fn_*`, come `fn_articolo_usato` | pgTAP: guard e `fn_non_editable_fields` rispondono uguale |
| D29 | **«Il reso ha fatto rientrare la merce»** | `vw_resi_confermati_senza_carico` con il letterale `'CONFERMATO'`; la gemella della bolla legge `script.vw_stati_doc_ddt_merce_partita` dal 2026-10-12 | BB gemello `script.vw_stati_doc_reso_merce_rientrata` | Test sul viewdef, come il test 8 di `test-vw-stati-doc-ddt-merce-partita-v1.sql` |
| D30 | **Le colonne del guard utility/tipo ruolo** | `fn_apply_automazione_guard_utility_tipo_ruolo` filtra `LIKE '%_soggetto_ruolo_id'` e scarta `soggetto_ruolo_id` (cinque righe del CSV); colonne inesistenti saltate senza traccia, nessun audit, dry run vuoto; lo stesso filtro nel ripiego del seed | Decidere se la forma senza prefisso è ammessa (CHECK sul catalogo o filtro tolto); salti `WARN`, dry run `DRYRUN` | pgTAP con una riga senza prefisso e una con colonna inesistente |

### 2.3 Registri che aggiungono e non tolgono

Tre registri delle automazioni montano oggetti ma non li smontano: il registro dice una cosa e il
database un'altra. Per i lock di colonna il framework ha già adottato la convergenza; conviene
decidere la regola una volta per tutti e tre (§4).

| # | Registro | Fatto | Presidio |
| --- | --- | --- | --- |
| D32 | Lock di colonna | `fn_lock_columns_divergenze` parte da `JOIN regola` (`:145`): un lock montato su una tabella senza regola attiva è invisibile, e spegnendo la regola i lock restano vivi. `test-lock-columns-convergenza.sql` test 4 si dice presidio «su tutto il database» | Un lock montato a mano su una tabella senza regola fa rosso |
| D33 | DELETE_BLOCK | Il trigger si crea se il nome manca e non si toglie mai: `enabled = false`, riga cancellata, `guc_key` cambiato non arrivano al trigger; un `trigger_name` cambiato ne monta un secondo | Spegnere una riga toglie il trigger |
| D34 | Guard utility/tipo ruolo | L'apply legge solo `enabled = true`, e `DROP TRIGGER IF EXISTS` colpisce solo il nome di oggi | Accesa → spenta → rinominata |

### 2.4 Promesse senza esecutore

| # | Che cosa promette | Che cosa succede | Correzione / presidio |
| --- | --- | --- | --- |
| D35 | `shop.ricevute` ha `storicizza DEFAULT true` e `tx_id` | `shop` non è in `automation_scope.csv`: nessun trigger generato, nessuna `storico.ricevute` | Decidere per `shop` (§4); in generale una tabella con colonna-marcatore di automazione sta nell'ambito o è esclusa dichiarata. Presidio: censimento delle colonne-marcatore fuori ambito |
| D36 | `dbops.ai_query_log` ha `cleanup_at`, il COMMENT dice «retention via cleanup_at» | Fuori ambito, nessuna regola `CLEANUP_AT`, nessun trigger alla nascita: le righe (testo digitato dagli utenti) non scadono mai | Scope + regola (termine: §4) + trigger alla nascita; estendere `test-registri-dbops-scadenza-v1.sql` |
| D37 | `dbops.audit_sources` ha `data_update`, `user_update`, `tx_id`, `storicizza` | Fuori ambito: nessuno le scrive, `storicizza = true` non produce storico | Ambito o colonne tolte (§4). Presidio: ogni tabella con `tx_id` ha `trgfn_tx_id_managed`, salvo registro del debito |
| D38 | `automazione_chiusura_scadenze.classe` separa le nature dei bersagli | L'unico chiamante, l'handler della coda, non passa `p_classe` (`backend/apps/core/services/coda_lavori/chiusura_scadenze_handler.py:60`): un bersaglio `MANUTENZIONE`/`AMMINISTRAZIONE`, che il CHECK ammette, verrebbe lavorato con l'identità e la RLS di ogni azienda | (a) solo `DOMINIO` sulle righe attive + handler che passa `'DOMINIO'` (§5), o (b) un esecutore `SISTEMA` |
| D39 | `automazione_chiusura_scadenze.verbo_chiusura` | Porta e verbo si guardano solo nel ramo `FK`: nel ramo `VARCHAR` l'UPDATE è sempre dinamico (sotto la porta fallisce con `E_DOC_STATO_SOLO_DAL_VERBO` invece dell'errore di configurazione), nel ramo `FK` senza porta un verbo dichiarato è ignorato | Porta e verbo valutati prima del dispatch; verbo senza porta → `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` con un motivo nuovo, o verbo usato sempre. Presidio in `test-fn-apply-chiusura-scadenze-v1` |
| D40 | `fn_run_automations_cleanup`: «un rifiuto non ferma il giro» | `RETURNS void`: le tabelle bloccate vanno solo in `audit_log` (`BLOCKED_BY_TABLE`), la corsa resta verde in `vw_job_run_da_guardare` (D5 del brief maintenance non esteso qui) | Un riepilogo jsonb con `_falliti`; estendere `test-cleanup-framework.sql` |
| D41 | `fn_run_automations_delete_block` | Nel giro vero non scrive audit (`:82-104`); la tabella sparita solo nel dry run (`:39-56`); una riga fuori ambito ignorata senza traccia (`:31-33`, da annotare in `framework-automazione-db-migliorie` §2.4) | Audit `OK` e `WARN TABLE_NOT_FOUND` sempre |
| D42 | `vw_run_senza_attore` misura un debito | Dal CHECK `chk_job_run_log_processo_dichiarato` (`90_end/20260905-16…:85`) il debito non può più nascere: in vista restano per sempre i job la cui ultima corsa è anteriore | Ritiro del presidio (`obsoleto_dal` in `presidi.csv`) o filtro sui processi vivi (§4) |
| D43 | `vw_processi_che_bypassano` | Classifica `DEBITO_DICHIARATO` il ruolo `zeroerp_batch_fatturazione`, ritirato il 2026-10-15, e scrive su ogni riga la nota fissa «ritiro previsto alla fase 6-bis» (`views/vw_processi_che_bypassano.md:16,19`): se il ruolo tornasse con BYPASSRLS il presidio tacerebbe | Nome e nota tolti. Presidio in `test-processi-registro.sql` |

### 2.5 Codici errore

| # | Dove | Fatto | Correzione |
| --- | --- | --- | --- |
| D44 | `fn_check_pipeline_task_registered` (`:33,42,62`), `fn_get_pipeline_task_implementation` (`:33,42,87`) | `E_GENERICO` con nomi di parametro nel VARIADIC (linee guida §5); «task non registrato» arriva come 500 | `E_PIPELINE_TASK_HANDLER_NOT_FOUND` / `E_PIPELINE_TASK` (già registrati); `throws_ok` nei test 7-8 di `test-pipeline-task-registry.sql` |
| D45 | `fn_admin_merge_comune`, `fn_admin_merge_stradario` | Tre `RAISE EXCEPTION` in chiaro ciascuna; il debito sta solo in un brief chiuso | `E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`, `E_COMUNE_NON_TROVATO`, `E_STRADARIO_NON_TROVATO`, nel giro di D3/D4 |
| D46 | `trgfn_child_requires_active_parent` | Ogni rifiuto, anche «padre non attivo», esce con `E_ATTIVO_REQUIRE`, classe `TECNICO` (`codici_errore.csv:64`); il BE lo aggira con controlli preventivi (§5) | Un codice `CONFLITTO_STATO` sul modello del block; `E_ATTIVO_REQUIRE` resta per il montaggio |
| D47 | `trgfn_child_requires_non_obsolete_parent` | Argomenti insufficienti e colonne mancanti escono con `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (un 409 per l'operatore) | `E_TRIGGER_ARGOMENTI_INVALIDI` (`codici_errore.csv:699`) nei rami di configurazione |
| D48 | `dbops.automation_lock_columns.error_code` | DEFAULT `'CODICE_NON_MODIFICABILE'` (`00_schema/dbops/20260110-11…:42`), ritirato il 2026-08-05 (`codici_errore.csv:3`); il `COALESCE` di `fn_lock_columns_divergenze` (`:85`) è morto perché la colonna è NOT NULL | `DROP DEFAULT` o `E_CODICE_NON_MODIFICABILE`; `COALESCE` tolto |
| D49 | `trgfn_prevent_deactivate_if_children`, `trgfn_child_requires_active_parent` | Con un argomento facoltativo mancante il ripiego scrive in `error_log` a ogni scatto (lo stesso difetto chiuso il 2026-08-05 per `E_ATTIVO_BLOCK_REF_NULL`) | Argomenti obbligatori, dopo il censimento dei montaggi |
| D50 | `fn_run_automations_tx_id` (`:130`) | La riga `DRYRUN` ha `rule_type = 'E_TX_ID'` | `'TX_ID'` |

### 2.6 Chi legge e con quali occhi

* **D51 — I guard ATTIVO leggono figli e padre sotto la RLS di chi scrive.** `trgfn_prevent_deactivate_if_children`
  e `trgfn_child_requires_active_parent` sono `INVOKER` con `EXECUTE` dinamici sulle tabelle di dominio
  (`db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql:157-166` lo documenta): il block lascia spegnere
  un padre con figli attivi fuori perimetro; il require, differito, conta il contesto al commit.
  Correzione: le due letture in una funzione `SECURITY DEFINER` del migratore con `search_path` stretto.
  ⚠️ Cambia il comportamento delle fixture che chiudono i differiti «nei panni di chi ha scritto»: §4.
* **D52 — Il proprietario della shadow si controlla per nome.** `fn_storico_arma_scope` (`:47-59`) e
  `fn_storico_backfill_scope` (`:115-118`) procedono solo se `v_owner = current_user`;
  `fn_ensure_storico_table` (`:203-204`) usa `pg_has_role(…, 'MEMBER')`. Un membro di `zeroerp_owner`
  senza `SET ROLE` prende un falso `SKIP_OWNER`. Correzione: membership nei due punti. Presidio: un ruolo
  membro arma una shadow di prova e ottiene `ALLINEATA`.

### 2.7 Strumenti che rispondono in modo sbagliato

| # | Oggetto | Fatto | Correzione |
| --- | --- | --- | --- |
| D53 | `fn_find_file_usage` (`:34,37`), `fn_foreign_keys_info` (`:35,39,56`) | Prodotto cartesiano sulle FK composite; la seconda unisce i vincoli per nome senza tabella, filtra senza schema, dipende da `information_schema`. Stessa domanda in due funzioni, nessun chiamante | Una funzione su `pg_constraint` con `unnest(conkey, confkey) WITH ORDINALITY`; l'altra si ritira (o entrambe: §2.8) |
| D54 | `fn_search_column_usage` (`:73`) | Il ramo dei vincoli cerca in `conbin`, dove le colonne sono `:varattno N`: risponde sempre vuoto | `pg_get_constraintdef` o `conkey` |
| D55 | `vw_function_list` (`:23,27`) | `num_args` conta le virgole (sbaglia con `numeric(p,s)`, NULL a zero argomenti); `pg_description` senza `classoid`/`objsubid` | `pronargs`, `obj_description(oid, 'pg_proc')` |
| D56 | `vw_codici_errore_forme_condizione` | `(regexp_match(riga, …))[1]`: un solo codice per riga, il secondo si perde | `dbops.fn_regexp_occorrenze`; baseline B-7 rigenerata, con la ragione nel commit |
| D57 | `fn_get_lookup_codici` e il suo unico consumatore | La paginazione del BE è corretta: chiama con offset 0, ordina col BB `sql_order_clause` con spareggio `id` e ricalcola il totale con `fetch_paged_with_total` (`backend/apps/core/db/dbops_repository.py:415-470`, dal 2026-09-26). Ma passa `p_limit = LOOKUP_MAX_SOURCE_ROWS` (10 000, `:55`) e applica la ricerca **dopo** il taglio: su una tabella più lunga del tetto la ricerca non vede le righe oltre, e quali restano fuori lo decide l'`ORDER BY` della funzione, che non ha spareggio. `p_offset` e l'ordinamento della funzione non li usa nessuno | Il filtro di ricerca dentro la funzione (parametro `p_search`, prima del `LIMIT`), oppure nessun tetto interno; ritirare `p_offset`. Ricaduta BE (§5, BE4) |
| D58 | `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico` | `NOT EXISTS` su tutto il documento, mentre il contratto del posting è un movimento per prelievo e un carico per rientro: lo scarico parziale non accende niente | Domanda alla grana di prelievo/rientro |
| D59 | `fn_apply_automazione_overlap` | Una colonna di chiave inesistente si salta in silenzio: il vincolo nasce con una chiave più corta (più severo), e l'audit `OK` riporta la chiave registrata | Tutte le colonne devono esistere, altrimenti `WARN KEY_COLUMN_MISSING` |
| D60 | `fn_audit_begin`, `fn_audit_end`, `fn_audit_log_once` — ramo dblink | Il ruolo del canale ha diritti solo su `error_log` e `job_run_log` (`scripts/sql/provision_dblink_log_channel.sql:45-51`); `p_parts` NULL diventa `'null'::text[]`; `p_params` NULL il JSON `null`; `fn_audit_end` senza `COALESCE` (`:42-48` contro `:61-67`); il `tx_id` è quello della sessione remota. Acceso, fa fallire la transazione del chiamante | Ritiro del ramo (`begin`/`end` non hanno chiamanti), o grant + `tx_id` esplicito + costruzione unica (§4) |

### 2.8 D61 — Oggetti da ritirare in un changeSet solo

Senza chiamanti in `db/`, `backend/`, `scripts/`, `db/pgtap/`, e con risposte sbagliate o copie di regole
vive. Con il ritiro si cancellano le pagine `manual/` (non si lasciano monconi). Presidio: `hasnt_function`
o `dbops.vw_riferimenti_morti_da_sanare`.

| Oggetto | Perché | Decisione |
| --- | --- | --- |
| `fn_rename_triggers_by_order`, `fn_fix_triggers_events_noorder`, `fn_cleanup_triggers_suffix_2`, `fn_fix_lock_codice_interno_triggers` | Utility una tantum del primo albero (`migrations/50_dbops/20250921-01…`, `20250922-05/-06/-07…`), tre eseguite davvero. Rinominano anche i `CONSTRAINT TRIGGER` con `ALTER TRIGGER` (nome morto in `pg_constraint`), producono nomi fuori dalla regola di oggi, montano lucchetti fuori registro; il DROP di `suffix_2` è irraggiungibile | Ritiro (`DROP FUNCTION IF EXISTS` in `migrations_v2/20_code/dbops`: il primo albero è congelato ma `v2` gira dopo) |
| `fn_fix_triggers_event_tokens` | Nessun changeSet la crea (`git log -S` vuoto): esiste solo su dbdev; il default `'a10'` è rifiutato dal suo controllo; `RAISE` nudo | Stesso `DROP … IF EXISTS` |
| `fn_trigger_exists_cascade_by_args` | Cerca `dbops.trgfn_soft_delete_cascade`, ritirata (`20260101-01-drop-attivo-legacy-objects.yaml:30`) | Ritiro |
| `fn_seed_automazione_overlap` | Seconda sorgente del registro (lo scrivono i changeSet di `80_data`); lanciata, l'upsert sovrascrive le righe curate; la regex del ramo GiST non estrae mai la chiave (`20_code/dbops/20260412-03…:134`) | Ritiro, o diagnosi con NOTICE |
| `fn_set_gucs_conn` | Scrive `app.user_id`/`app.group_ids` che nessuno legge; `app.session_key` lo legge `script.fn_get_parameter_di_sessione` ma senza questa funzione non lo scrive nessuno: il livello «sessione» degli override è sempre spento | Ritiro; per `app.session_key` decisione §4 |
| `fn_normalize_indirizzo` | `indirizzo_dettaglio_id` porta l'id della via; `civico_norm` sempre vuoto; col civico nel testo non trova la via; sede vera `anagrafiche.fn_build_indirizzo_normalizzato` | Ritiro |
| `fn_migrate_add_indirizzo_normalizzato` | Crea una colonna `GENERATED` con una formula sua, divergente da `fn_build_indirizzo_normalizzato`; su una tabella senza colonna entrerebbe in conflitto col trigger | Ritiro |
| `fn_run_automations` | Nessun chiamante; ordine e parti diversi dal giro vero (`dbops.processi.ci_ordine`): niente `STORICO_PROVISION`, delete_block, overlap (`:56-84`) | Ritiro, o ordine letto da `dbops.processi` |
| `fn_find_file_usage`, `fn_foreign_keys_info`, `fn_find_function_usage`, `fn_search_column_usage`, `fn_get_child_fk_col`, `fn_list_indices` | Strumenti DBA senza chiamanti; i primi quattro rispondono in modo sbagliato (D15, D53, D54; il COMMENT di `fn_find_function_usage` è copiato da `fn_find_file_usage`) | **Restano tutti** (Q9). `fn_find_function_usage` e `fn_search_column_usage` riparati nel giro 1a; i due di D53 si riparano nel giro 4 |
| `fn_audit_begin`, `fn_audit_end` | Nessun chiamante; ramo dblink rotto (D60) | ✅ Ritirati nel giro C1 (`90_end/20261104-18`) |

### 2.9 Le fixture pgTAP

Le fixture devono produrre i dati nella forma in cui li produce l'applicazione: dove scrivono a mano
accanto a una porta di dominio, un guard nuovo sulla porta non arriva al test.

| # | Fixture | Fatto | Correzione |
| --- | --- | --- | --- |
| D62 | `fn_pgtap_piva_libera` | Le due firme ripetono lo stesso ciclo | La firma senza argomenti delega a quella con salto zero |
| D63 | `fn_pgtap_crea_soggetto_pg` | INSERT diretti su `anagrafiche.soggetti` e `indirizzi_soggetti`, accanto alle madri `fn_crea_soggetto_pg` e `fn_crea_indirizzi_soggetto`; divergono già su dati societari e indirizzi | Chiamare le madri; il ripiego «almeno un indirizzo» da ridecidere |
| D64 | `fn_pgtap_crea_indirizzo_dettaglio` | `ON CONFLICT DO UPDATE` (`:43-45`) al posto di `anagrafiche.fn_get_or_create_indirizzo_dettaglio`: su una riga disattivata restituisce un indirizzo spento e salta i controlli sulla via | Chiamare il BB; presidio in `test-indirizzi-dettaglio-unicita-v1.sql` |
| D65 | `fn_pgtap_crea_mondo_cliente` | Ricopia la verifica del legame di `fn_pgtap_cliente_ba_del_mondo` (`:104-112` contro `:31-39`) | Chiamare la seconda |
| D66 | `script.fn_pgtap_emittente_operatore` / `dbops.fn_pgtap_azienda_di_chi_agisce` | Senza azienda per chi agisce, dbops solleva, script ripiega sul primo emittente (`script/funzioni/fn_pgtap_emittente_operatore.md:48-60`): un'azienda su cui chi agisce non può né leggere né scrivere | L'helper di script solleva, o delega (§4) |
| D67 | `fn_pgtap_crea_lotto` | L'esito del gruppo trattenuto è un INSERT su `vendite.fatturazione_lotti_esiti`, accanto a `vendite.fn_segna_esito_gruppo_lotto`: un `ERRORE` senza `errore_quando` | Chiamare la porta; test 8 di `test-fn-pgtap-crea-lotto-v1.sql` |
| D68 | `fn_pgtap_crea_commessa_attivita` | Senza sorgente la chiave è `PGT-SEG-<md5>`, fuori dalla grammatica di `script.fn_segment_key`: i lettori vedono un documento che non esiste | Chiave composta dal dominio (forma: §4) |
| D69 | `fn_pgtap_crea_listino`, `fn_pgtap_listino_aggiungi_articoli` | Righe senza periodicità anche su versione ATTIVA; tipologia di default che può essere quota fissa: dal 2026-10-31 il motivo 3 di `script.fn_check_versione_listino_attivabile` ferma l'attivazione | Periodicità facoltativa; quota fissa esclusa dal default |
| D70 | `fn_pgtap_porta_a_stato` | Verso `CHIUSA` chiama `vendite.fn_chiudi_versioni_listino_scadute()`, globale e muta: restituisce `ATTIVA` senza errore (verde per sottrazione) | Sollevare se lo stato raggiunto ≠ `p_stato`, per ogni testata |
| D71 | `fn_pgtap_crea_ddt_da_ordine` | «La prima riga» per `riga_nr` può essere l'onere (dal `20261103-36` la madre porta l'onere nella prima bolla); il conteggio di `p_qta_da_evadere` conta gli oneri | Filtro `script.fn_natura_e_merce` — censito «lieve» in `brief-db-addebito-trasporto-ordine` §8.1, corretto lì solo per il reso |
| D72 | `fn_pgtap_crea_preventivo_con_righe` | `nv.destinazione_tipo = 'ORDINE_VENDITA'` in linea, mentre `script.fn_natura_e_merce` è la sede del predicato (copia non censita in §8.1 di quel brief; un'altra in `vendite.vw_preventivi_smistamento`) | Usare il BB |
| D73 | Builder di documento | Lo stato si cerca in tre forme: senza `attivo` (`_crea_ordine`, `_crea_preventivo`), in linea con `attivo IS TRUE`, con `script.fn_doc_stato_id`. Uno stato disattivato non solleva prima di costruire | Tutti con `script.fn_doc_stato_id` |
| D74 | Builder di fixture | «La prima valuta del catalogo» in sette copie (`_crea_ddt`, `_crea_ordine`, `_crea_preventivo`, `_crea_fattura`, `_crea_cliente_ba`, `_crea_emittente`, `_crea_gestore`) | Un BB di fixture, copie ritirate nello stesso giro |

## 3. I metadati

Nessuno cambia il comportamento, ma ognuno dice una cosa falsa a chi legge. ⚠️ Quelli in changeSet già
applicati si correggono con un changeSet nuovo.

### 3.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `dbops.automation_scope` | «Scope opzionale per rollout filtrato»: è l'allow-list che decide l'ambito di ogni automazione; colonne senza COMMENT |
| M2 | COMMENT `storico_scope_policy`, colonne `modo`/`colonna` (`00_schema/dbops/20260911-21…:137-142`), COMMENT `fn_storico_risolvi_scope` | «Cinque modi»: manca `COPPIA` |
| M3 | COMMENT `fn_storico_arma_scope` | Comincia con un marcatore di revisione e poi cita l'adapter `script.fn_scope_ef_whitelist`: si contraddice |
| M4 | COMMENT `fn_grant_storico_shadows` (e corpo) | Cita il test 19 di `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` e il ruolo batch, ritirati il 2026-10-15; «audit SKIP», ma scrive `WARN`; «le shadow ereditano il proprietario da chi esegue», superato dalla cessione al proprietario della madre |
| M5 | COMMENT `fn_run_automations_storico_provision` (e corpo) | Apici raddoppiati (`''STORICO_PROVISION''`); «crea/aggiorna», ma crea soltanto; `MANUAL` come `exec_mode`. Idem COMMENT `maintenance.proc_automations_storico_provision_job` |
| M6 | COMMENT `fn_storico_backfill_scope`; intestazione `90_end/20260911-31…:28-29` | «Il pgTAP le conta come debito»: nessun pgTAP conta le versioni senza origine delle shadow vere |
| M7 | Commento nel corpo di `fn_run_automations_storico` | «duplicate_object: logga SKIP_EXISTS»: lo status è `WARN` |
| M8 | COMMENT `audit_sources.storico_table` (`00_schema/dbops/20260429-05…:19,69`) | «Non esposto dalla vista»: lo è dal 2026-09-02 |
| M9 | COMMENT `ai_query_log`; remark di `user_id` (`00_schema/dbops/20260331-21…:47`) | «Retention via cleanup_at» (D36); «FK auth_user.id» senza vincolo |
| M10 | COMMENT `fn_get_or_create_session_tx_id` e commento nel corpo | «Rispetta myapp.log_with_dblink … non blocca mai»: falso (D1, D26) |
| M11 | COMMENT `trgfn_tx_id_managed` | «Assegna script.uuid_nil()»: nel ramo dell'id non registrato vince il GUC (`:169-173`) e la riga `:163` è irraggiungibile. Il comportamento l'ha giudicato innocuo `brief-db-coerenza-tx-id-non-registrato` (2026-07-22): si corregge il COMMENT, non il corpo |
| M12 | COMMENT `fn_set_gucs_conn` | «Per audit, RLS e override»: nessuno la chiama |
| M13 | COMMENT `script.fn_ensure_logconn` | Dice di leggere `dblink.log_connection`, il corpo legge `myapp.dblink_log_connection` |
| M14 | COMMENT `vw_processi_che_bypassano` e nota in `presidi.csv` | «Fase 6-bis: a regime vuota», «ritiro alla fase 6-bis»: avvenuto (D43) |
| M15 | COMMENT `vw_processi_roster` | «Roster_processo può diventare un SELECT su questa vista»: il repository la legge già (`backend/apps/core/db/processi_repository.py:152-176`) |
| M16 | COMMENT `vw_processi_dominio_su_pgagent` | «DEVE arrivare a VUOTA … oggi fallirebbe il migrate»: vuota dal 2026-09-05 |
| M17 | COMMENT `vw_processi_programmazione_da_guardare`, `vw_processi_programmazione` | Elenco degli esclusi incompleto (anche OK, IN_ATTESA, SPENTO); conteggi usati come argomento; cronaca |
| M18 | COMMENT colonna `processi_bersagli.emittente_via` (`00_schema/dbops/20260904-08…:99`) | «Stesso vocabolario del guard»: falso (D21) |
| M19 | `db/pgtap/anagrafiche/test-identita-tecnica.sql:28-30` | «Il presidio guarda nei DUE sensi»: sono tre, e il secondo non lo costruisce nessun file |
| M20 | `presidi.csv` — `vw_riferimenti_morti_da_sanare` (`:15`), `vw_bersagli_non_dichiarati` (`:25`), `vw_codici_errore_forme_condizione` (`:23`) | Nota stantia (CHECK-KO → REALE, superata da `NON_MISURATO`); `presidiato_da` «ci-validate.yaml», ma la build la ferma `test-vw-bersagli-non-dichiarati.sql`; «lente da rilanciare a mano», ma la legge lo scatto B-7 |
| M21 | `presidi.csv` — `vw_af_senza_giro`; `test-catalogo-presidi-v1.sql:52-61` | «`attivita_fatturabili` non ha la RLS (debito)»: armata dal 2026-09-10, non è nel debito; «tre viste DEFINER, ne copre due»: superato |
| M22 | `presidi.csv` — `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico`; COMMENT `vendite.fn_ddt_muove_merce`, `vendite.fn_reso_muove_merce` | Citano la Regola 3 di `trgfn_ddt_guard_transizione` e la Regola 2 di `trgfn_resi_guard_transizione`, ritirate il 2026-10-25: la porta è `script.trgfn_doc_stato_solo_dal_verbo` |
| M23 | `presidi.csv` — `vw_magazzino_valore_giacenza_divergente`; COMMENT e nota di `vw_magazzino_movimenti_senza_costo` | Scrittori incompleti (anche `fn_posta_trasferimento`, `fn_storna_movimenti_sorgente`, `vendite.fn_posta_ddt`, `vendite.fn_posta_reso`); manca il carico da reso senza costo |
| M24 | `presidi.csv:21` e COMMENT `vw_run_senza_attore` | «Dodici job», «quando è vuota → NOT NULL»: superati dal CHECK (D42); cita `script.fn_run_and_log` (è `maintenance.`) |
| M25 | COMMENT `fn_guardiano_digest` | «Finché NOTIFICA_DIGEST_MUTO è attivo = false»: acceso dal 2026-09-11 |
| M26 | COMMENT `fn_conta_presidio_per_variante`; `codici_errore.csv:856`, `messaggi_errore.csv:853` | «Stessa ragione di fn_conta_presidio» (INVOKER dal 2026-10-10); `E_PRESIDIO_NON_A_CATALOGO` lo solleva `fn_conta_presidio_per_variante` |
| M27 | COMMENT `fn_check_funzioni_riferimenti_morti`; `codici_errore_senza_policy` | Consumatori incompleti, «test 7» è il 6; «voce in error_policies.py», la mappa è `error_policies_generated.py` |
| M28 | COMMENT `fn_apply_chiusura_scadenze` (e del filtro), `automazione_chiusura_scadenze`; riga `CHIUSURA_SCADENZE` di `coda_lavori_tipi.csv`; intestazione e test 4-6 di `test-chiusura-scadenze-classe.sql` | «Il job pgAgent chiama senza argomenti», «chiamata dal job notturno», «quando migreranno sulla coda»: la chiama l'handler della coda dal 2026-09-05; manca il preventivo fra i bersagli; «due bersagli» (tre) |
| M29 | COMMENT `fn_sessione_del_migratore`, `fn_idempotency_prenota`, `sessioni_utente` | Manca il chiamante `script.fn_blocca_credenziale`; «committa da sola» (è il backend in autocommit); manca `TOTP_DISABILITATO`, `SCADENZA` non ha scrittori |
| M30 | COMMENT `fn_admin_merge_comune`, `fn_admin_merge_stradario` | «Ripunta chi riferiva l'origine» (D3, D4); il commento su `fn_get_vie_discendenti` è falso |
| M31 | COMMENT `fn_get_lookup_codici`, `trgfn_child_requires_non_obsolete_parent`; `messaggi_errore.csv:292` | «obsoleto_dal <= CURRENT_DATE»: dal 2026-10-09 è `fn_data_operativa()` |
| M32 | COMMENT `vw_emittenti_regime_non_confermato` | «O di un cambio senza conferma»: stantio dal 2026-10-02 |
| M33 | COMMENT `fn_find_function_usage`, `fn_get_override_col`, `fn_get_child_fk_col` | Copiato da `fn_find_file_usage`; rimanda a `dbops._col_exists` (è `fn_col_exists`); «di fatto STABLE» (è VOLATILE) e «utility delle automazioni» senza chiamanti |
| M34 | COMMENT `lock_columns_conditional`, `fn_cleanup_at_params`, `trgfn_cleanup_at_alla_nascita`, `fn_apply_delete_block_trigger`, `fn_seed_automazione_guard_utility_tipo_ruolo`, `fn_seed_automazione_overlap`, `automazione_overlap`, `automazione_attivo_eccezioni`, `fn_trigger_exists_block_by_args`/`…_require_by_args`, tabella `automation_delete_block` | «Colonne immutabili» (segnala al form); «stesso criterio» (D16); «event_log e i quattro registri» (dieci tabelle); non dice `AFTER DELETE` né il controllo per nome; «Popola» (non scrive); non dice che sovrascrive né che non ha chiamanti; manca `range_col`; «prima riga» (sono due); «la signature a 5 args» (non riconoscono niente, D6); «tabelle sensibili (ruoli)» (generico) |
| M35 | `automation_rules_tbl.csv:12`, nota della regola di `vendite.event_log`; `codici_errore.csv:64`; intestazioni `80_data/changelog/20260602-10…:16-19`, `20260626-04…:21` | «Trigger a10 all'INSERT» (è `trgfn_cleanup_at_alla_nascita` in m50); «meno di 4 argomenti» (copre ogni rifiuto, D46); «oggi NON è schedulato» (ha job e convergenza) |
| M36 | COMMENT di fixture | `fn_pgtap_piva_libera()` «due chiamate danno valori diversi» (falso senza scrittura fra le due); `_crea_operatore_umano` «lo stesso UPDATE di identita_digitali.attivo» (è `fn_accendi_veste`); `_cliente_ba_del_mondo` «BB di fattura, contratto, ordine» (solo `_cliente_del_builder`); `_cliente_del_builder` cinque builder (sei); `_crea_mondo_cliente` `uq_emittenti_fiscali_ba` (stantio); `_crea_commessa`, `_contratto`, `_fattura`, `_ordine` «il cliente da `_crea_mondo_cliente`» (da `_cliente_del_builder` dal 2026-10-24); `_crea_commessa_attivita` (D68); `_crea_reso` si contraddice; `_porta_a_stato` «testate senza la porta» (oggi tutte l'hanno) |
| M37 | Intestazioni pgTAP | `test-fn-pgtap-crea-fattura-v1.sql` («coppia», «quattro anelli»); `test-fn-pgtap-crea-preventivo-v1.sql` («stato alla nascita»); `test-audit-sources-seed.sql:16,54,168` («3 colonne», «almeno 9»); `test-cleanup-framework.sql:31` («tre tabelle», sono sei); `test-storico-scope-congelato-v1.sql:4-8,20-23` («titodb non può fare SET ROLE», superato dai ruoli di sistema); `test-automazione-attivo-eccezioni-v1.sql` (presidia solo la prima eccezione) |
| M38 | `scripts/sql/provision_storico_scope.sql:6` | Rimanda a `work-in-progress/brief-db-rls-storico-scope-congelato.md`, oggi in `work-done/` |
| M39 | `script.fn_check_versione_listino_attivabile`; `script.fn_crea_utente_tecnico` | COMMENT con i motivi 1 e 2, il corpo ha anche il 3; commento del Guard 1 «canale CODA no», la condizione ammette `CODA_AUTOMATICA` |

### 3.2 Senza COMMENT

`dbops.audit_log`; `fn_audit_begin`, `fn_audit_end`, `fn_audit_log_once`; `fn_schema_match`,
`fn_schema_in_scope`, `fn_table_in_scope`, `fn_resolve_scope` (il doppio significato di `*all` —
«qualunque schema» qui, «usa il default» in `fn_resolve_scope` — non è scritto nel database);
`fn_find_file_usage`, `fn_foreign_keys_info`, `fn_search_column_usage`, `fn_list_indices`;
`fn_drop_triggers_by_function_args`; `fn_normalize_indirizzo`, `fn_migrate_add_indirizzo_normalizzato`
e le utility di D61 (si chiudono col ritiro).

### 3.3 Marcatori di revisione, nomi di brief, id di changeSet e conteggi nei COMMENT

Lo stesso residuo che lo standard toglie dalle pagine `manual/` sta nei COMMENT di quasi tutti gli
oggetti rivisti: `Rev …`, `⭐ rev …`, «Brief: …», sigle di cantiere, id di changeSet, un hash di commit
(`28d9beeb6` in `fn_storico_risolvi_scope`), misure usate come argomento («168 su 349» in
`trgfn_prevent_deactivate_if_children`, «12 righe OK», «su 102 dei 185 file»). Il COMMENT è il primo
paragrafo della scheda auto-generata, quindi chi legge lo trova come descrizione. Oggetti più colpiti:
`fn_storico_*`, `fn_ensure_storico_table`, `fn_run_automations_*`, `trgfn_tx_id_managed`,
`fn_get_or_create_session_tx_id`, `fn_generate_tx_id`, tutte le `vw_processi_*`, `processi*`,
`installazione`, `vw_codici_errore_*`, `vw_funzioni_check_codici`, `fn_regexp_occorrenze`,
`messaggi_errore_codici_legacy`, `coda_lavori*`, `fn_accoda_*`, `fn_idempotency_*`,
`fn_sync_functions_owner`, `vw_stati_check_*`, `vw_trigger_functions`, le viste delle FK, quasi tutte
le `fn_pgtap_*` e le etichette di prova.

Proposta: una regola sul COMMENT uguale a quella del primo paragrafo dello Scopo (il significato
dell'oggetto, al presente, niente provenienza), un changeSet di riscrittura per famiglia quando la
famiglia si tocca per un difetto, e un presidio di testo
(`obj_description` che contiene `brief-`, `rev 20`, un id `20\d{6}-\d\d`). Se vale anche per i COMMENT
la R3 del brief maintenance (nomi di brief fuori dalle note dei CSV) lo decide Tid (§4).

## 4. Le decisioni di Tid

| # | Domanda | Raccomandazione della sessione DB |
| --- | --- | --- |
| Q1 | D3/D4: `fn_admin_merge_*` si riparano (sono la riclassificazione delle vie) o si ritirano? | Riparare lo stradario (la guida riclassificazione-vie ne ha bisogno), restringere o riparare il comune nello stesso giro. **✅ Deciso (Tid, 2026-11-05): si riparano tutte e due**; le figlie del comune si derivano da `pg_constraint`; un indirizzo doppio sulle due vie **ferma la fusione con un codice** e l'elenco dei doppi (nessuna unione automatica); D45 nello stesso giro |
| Q2 | D11: che cosa vuol dire `attivo = false` per un processo? | CHECK: il ritiro si scrive con la data, una sede sola. **✅ Deciso (Tid, 2026-11-05): la data è l'unica sede del ritiro**; CHECK che vieta `attivo = false` senza `obsoleto_dal`; un BB «processo vivo» (data vuota o non ancora arrivata) letto da sveglia, accensione, guard, panorama, roster e dalle sette viste che oggi leggono `obsoleto_dal IS NULL` (chiude anche quel dubbio della Q14) |
| Q3 | §2.3: una regola di convergenza per i registri che aggiungono e non tolgono | Sì, una volta per tutti e tre: riconoscimento per funzione, rimozione con `enabled = false`. **✅ Deciso (Tid, 2026-11-05): sì**, una regola per i tre registri (trigger riconosciuto dalla funzione; riga spenta o cancellata = trigger tolto; presidio di convergenza per ciascuno) |
| Q4 | D35-D37: `shop` nell'ambito? `ai_query_log`: che termine? `audit_sources`: ambito o colonne tolte? | `shop` nell'ambito; `ai_query_log` a 90 giorni come gli altri registri, o meno per il testo sensibile; `audit_sources` nell'ambito. **✅ Deciso (Tid, 2026-11-05): `shop` nell'ambito; `ai_query_log` nell'ambito, scadenza 90 giorni come gli altri registri; `audit_sources` resta fuori e perde `tx_id`, `storicizza`, `data_update` e `user_update`** |
| Q5 | D38: classe dei bersagli — solo `DOMINIO` o un esecutore `SISTEMA`? | Solo `DOMINIO` finché non c'è un bersaglio di altra natura. **✅ Deciso (Tid, 2026-11-05): (a) nel DB** — il CHECK su `classe` ammette solo `DOMINIO`, il motore rifiuta con un codice un bersaglio di altra classe; **BE1 si ritira** (l'handler rifiuta già `p_classe`, a ragione); **`p_classe` si ritira** dal motore nello stesso giro. Un bersaglio di altra natura chiederà un giro suo: CHECK riaperto, esecutore che lavora una volta con identità tecnica, chi lo lancia. Doc da correggere nel giro (dicono che il registro ammette tre classi): `dbops/manual/automazione_chiusura_scadenze.md` §«La classe sta sul bersaglio», `dbops/manual/fn_apply_chiusura_scadenze.md` §`p_classe`, `guide/processi-pgagent-funzionali.md` §`chiusura_scadenze_daily` (passo «aggiungere una riga»): solo `DOMINIO`, le altre classi chiedono un esecutore da sviluppare |
| Q6 | D42: `vw_run_senza_attore` ritirata o filtrata? | Ritirata (`obsoleto_dal`): il debito non può più nascere. **✅ Deciso (Tid, 2026-11-04): si ritira**; fatto nel giro C1 (§10, DROP in `20_code/dbops/20261104-11`) |
| Q8 | D51: lettura `DEFINER` dei guard ATTIVO, con l'effetto sulle fixture | Sì, con il censimento delle fixture che chiudono i differiti. **✅ Deciso (Tid, 2026-11-05): sì** |
| Q9 | D60 e §2.8: ramo dblink di `fn_audit_*`; `fn_audit_begin/end`; i sei strumenti DBA senza chiamanti | Ritirare il ramo dblink e `begin/end`; riparare `fn_find_function_usage` e `fn_search_column_usage` (servono ai censimenti), ritirare gli altri quattro **✅ Deciso (Tid, 2026-11-05): il ramo dblink di `fn_audit_log_once` si ritira** (giro 2; la riga si scrive sempre nella transazione del chiamante; il fallimento lo registra `error_log`). `begin/end` già ritirati (C1), `fn_find_function_usage` e `fn_search_column_usage` già riparati (1a). I quattro strumenti DBA restano (C1): **i due del D53 si riparano** (Tid, 2026-11-05): una funzione sola su `pg_constraint` con `unnest(conkey, confkey) WITH ORDINALITY`, l'altra la chiama |
| Q10 | `app.session_key` (D61, `fn_set_gucs_conn`): lo imposta il BE all'autenticazione, o il livello sessione esce da `fn_get_parameter_di_sessione`? | ~~Esce: nessuno lo usa~~ (una misura, non un motivo). **✅ Deciso (Tid, 2026-11-05): il livello «sessione» esce dal modello, da tutte e due le catene** — colonna `config.parameter_overrides.session_key`, livello in `script.fn_get_parameter_full` e `script.fn_get_parameter_di_sessione`, dimensione `session_key` nel repository BE. Motivo di modello: un override è configurazione che resta, una sessione di login scade; nessuna porta lo crea né lo pulisce. Fuori dal perimetro `dbops`: un giro suo, con la richiesta BE8 |
| Q11 | D66: `script.fn_pgtap_emittente_operatore` senza azienda — solleva o delega? | Delega a quella di dbops (una sede). **✅ Deciso (Tid, 2026-11-05): delega.** Censimento del 2026-11-05 (scratch, da owner, helper con un `WARNING` su chiamata e ripiego, dentro la transazione di ogni file): 103 file la nominano, 94 la chiamano, nessuno cade sul ripiego; i 6 file con `not ok` lo sono uguali senza lo strumento |
| Q12 | D68: chiave di default del segmento senza sorgente — `COMMESSA:<id>…` o `MAN:`? | `MAN:`, che è la forma di una riga senza documento. **✅ Deciso (Tid, 2026-11-05): `MAN:<commessa>:<n>`**, con la regola del progressivo della porta degli oneri; nel giro si verifica anche la sorgente che la fixture scrive sulla riga. **Superata (2026-11-07)** da una decisione di Tid in `brief-db-sorgente-documento-e-riga` (§«Le fixture dei pgTAP»): senza sorgente il builder crea un consumo vero e la chiave la compone `script.fn_segment_key`; la sorgente della riga, che la Q12 chiedeva di verificare, era la commessa stessa ed è corretta lì (§21.1) |
| Q13 | §3.3: la regola sui COMMENT, e se vale per loro la R3 del brief maintenance | Sì, con il presidio di testo. **✅ Deciso (Tid, 2026-11-05): il COMMENT descrive l'oggetto, al presente; nessun brief, mai (né percorso né nome), nessun marcatore di revisione, id di changeSet o misura.** Scritto come standard in `linee-guida-sql.md` §5d. Riscrittura per famiglia quando la famiglia si riapre, in ogni giro; il residuo e il presidio di testo su `obj_description` nel giro 14 |
| Q14 | Altri dubbi dei lotti, da confermare o girare in difetto: `fn_get_pipeline_task_implementation` ripiega in silenzio sul default per una variante inesistente; una FK registrata a `false` sparisce da ogni presidio; `vw_coda_lavori_da_guardare` è definer su tabella senza RLS e catalogata `LIBERO`; `vw_codici_errore_forme_condizione` è catalogata `LAVORAZIONE` ma la usa lo scatto B-7 come cancello; `vw_processi_dominio_senza_difesa` riconosce il guard dal solo `proname`; `obsoleto_dal IS NULL` fa uscire dai presidi un processo a ritiro programmato che gira ancora (sette viste); un lotto congelato con `stato_lotto` IN_ESECUZIONE/ERRORE ed esiti in ERRORE non lo guarda né `vw_lotti_fermi_da_guardare` né `vw_lotti_chiusi_con_errori_da_guardare`; uno storno di un'uscita senza costo entra in `vw_magazzino_movimenti_senza_costo`; `sessioni_utente.evento = 'SCADENZA'` ammesso e mai scritto; `credenziali_di_prova` senza FK verso la credenziale (un'etichetta che sopravvive alla credenziale); il trigger DELETE_BLOCK è `AFTER DELETE` in fase `a10`; un `ADD CONSTRAINT` overlap su dati già sovrapposti (23P01) ferma il giro; il guard utility gira solo in `ci_apply`, senza processo | Da decidere uno per uno; la sessione DB li apre come difetti solo su conferma. **Decisi (Tid, 2026-11-05/06):** ① variante inesistente → **difetto**, giro 2 (stessa funzione di D44): con una variante chiesta e assente la funzione non restituisce righe (il BE solleva già `E_PIPELINE_TASK_HANDLER_NOT_FOUND`), il default vale solo senza variante; ② FK a `false` che sparisce da `vw_fk_senza_indice` → **difetto**, giro 10, blocco 10d: in `dbops.fk_index_policy` `consentito` lascia il posto a `decisione` (NOT NULL, `DA_DECIDERE` / `CON_INDICE` / `SENZA_INDICE`, default `DA_DECIDERE`) e a `motivo` (facoltativo); la scoperta scrive solo `DA_DECIDERE` e solo sulle FK nuove, la decisione la scrive solo un seed; il presidio mostra le `DA_DECIDERE`; righe di oggi: quelle scritte da un seed diventano decisioni, quelle scritte solo dall'automazione `DA_DECIDERE` (censimento dei seed nel giro); censiti e riscritti nello stesso giro lettori e scrittori di `consentito` (apply, populate, vista, CSV di `80_data`, pgTAP); ③ `vw_coda_lavori_da_guardare` `LIBERO` → **non è un difetto** della vista (è il presidio di sistema, vede tutte le aziende di proposito); la nota del presidio dice perché è `LIBERO`. **Ma la coda si corregge:** `dbops.coda_lavori` va sotto RLS come `vendite.fatture_stampa_coda` — la separazione fra aziende sta nel DB, non nel BE (oggi la fa solo `core/services/coda_lavori/gestione_service.py` con lo `scope_key`); poi il BE si ripulisce (BE9). Il giro 5, con D9 (stessa tabella). Vincoli da tenere: il drenatore deve vedere e prendere i lavori di tutte le aziende (ramo della policy per l'identità di processo), un lavoro `SISTEMA` non ha emittente; dopo la RLS si rivaluta il `perimetro` della vista. La RLS sulla coda era stata rinviata come «ondata futura» in `brief-be-fe-gestione-code-lavori-stampa`, non scartata; ④ `vw_codici_errore_forme_condizione` → **difetto di metadato**: in `presidi.csv` natura `CANCELLO`, `presidiato_da` = passo B-7 di `ci-validate.yaml` (via `scripts/sql/codici_errore_famiglie_snapshot.sql` e la baseline), nota riscritta; nel giro 6; ⑤ `vw_processi_dominio_senza_difesa` riconosce il guard dal solo `proname` → **difetto**: la vista conta come difesa anche un'omonima in un altro schema e un trigger disattivato; il guard si riconosce dalla funzione esatta per OID (`'script.trgfn_guard_emittente_scope'::regproc`, il criterio della Q3), conta solo un trigger acceso (`tgenabled <> 'D'`) su INSERT e UPDATE, e il processo vivo si legge con il BB della Q2; pgTAP con un'omonima in un altro schema e con il guard disattivato, in tutti e due i casi la tabella compare; si corregge nel giro 9, quello delle sette viste della Q2, così la vista si apre una volta sola; ⑥ ritiro programmato → chiuso con la Q2; ⑦ lotto congelato con esiti in ERRORE e job non COMPLETATO → **difetto**, giro 6: i due presidi si spartiscono l'asse su criteri diversi (`vw_lotti_fermi_da_guardare` sullo stato fiscale, `vendite.vw_lotti_chiusi_con_gruppi_in_errore` sullo stato del job), e ne nascono un buco (congelato + IN_ESECUZIONE/ERRORE, ammesso dalla matrice dei job, non lo vede nessuno: è il caso della R-1) e un doppione (COMPLETATO in bozza con esito ERRORE lo vedono tutti e due); l'asse diventa uno solo, lo stato fiscale: non congelato → presidio dei lotti fermi, invariato; congelato con un esito ERRORE → l'altro, qualunque `stato_lotto` (`stato_lotto = 'COMPLETATO'` lascia il posto a `NOT pre_fiscale` di `vw_lotti_fase`; lo stato fiscale ignoto cade qui); gli annullati restano fuori perché l'annullo chiude gli esiti, non per un filtro; censiti i lettori della vista di `vendite`, valutato il nome («chiusi» → «congelati»); pgTAP: congelato + job ERRORE + esito ERRORE solo nel secondo, COMPLETATO in bozza + errore solo nel primo. **Non solo i COMMENT:** nello stesso giro si riscrive la documentazione che descrive la spartizione — `dbops/manual/vw_lotti_fermi_da_guardare.md`, `dbops/manual/vw_lotti_chiusi_con_errori_da_guardare.md`, `vendite/manual/vw_lotti_segnalazioni_summary.md`, `vendite/manual/fn_get_lotto_segnalazioni_summary.md`, le note in `presidi.csv` e `presidi_testi.csv`, la guida `processi-automatici-classe-e-identita.md` e `Messaggi-di-Errore-e-Generazione-Log.md` dove ne parlano; `backend/vendite/manual/api_lotto_segnalazioni_summary.md` va al team BE se descrive la spartizione; ⑧ storno di un'uscita senza costo in `vw_magazzino_movimenti_senza_costo` → **difetto**, nel lotto M di `brief-db-sorgente-documento-e-riga`, con D58 e D29 (§8.1): lo storno è lo specchio dell'originale e ne prende il costo (`fn_scrivi_movimento` rifiuta un costo passato), quindi lo storno di un'uscita senza costo è un'entrata senza costo, conseguenza di una conseguenza, mentre la causa (il carico senza valore) è già nella vista; la vista aggiunge `storno_di_movimento_id IS NULL`; pgTAP: uscita senza costo stornata, lo storno non compare e il carico che l'ha causata sì; documentazione nello stesso giro: `dbops/manual/vw_magazzino_movimenti_senza_costo.md`, note di `presidi.csv` e `presidi_testi.csv`, `magazzino/manual/fn_scrivi_movimento.md` e `magazzino/manual/inventari_righe.md` dove parlano del presidio, `dbops/manual/vw_magazzino_valore_giacenza_divergente.md` se cita la regola; ⑨ `sessioni_utente.evento = 'SCADENZA'` → **difetto**, `SCADENZA` si ritira dal vincolo `chk_sessioni_utente_evento` (giro 9): la scadenza di un token non è un gesto, nessuno la compie, e scriverla vorrebbe dire inventare un evento da un'assenza; chi vuole le sessioni scadute le legge dalla scadenza del token; nello stesso changeSet, prima del vincolo stretto, il conteggio delle righe `SCADENZA` (se ce n'è una il vincolo si ferma); censiti i lettori (valore ritirato = filtro nascosto: oggi nessuno in BE e FE); documentazione nello stesso giro: `dbops/manual/sessioni_utente.md` e il COMMENT della tabella («traccia … scadenza»); pgTAP: un INSERT con `SCADENZA` è respinto; si valuta se `test-stati-check-scrittori-v1` va esteso ai vincoli sugli eventi; ⑩ `credenziali_di_prova` senza FK → **difetto**, giro 11: il motivo del COMMENT («in CI `django.auth_user` nasce dopo Liquibase») è un fatto, non una ragione — le FK verso `django.auth_user` stanno nel ponte `90_end` con la loro preCondition (più di venti), e la gemella `soggetti_di_prova` ha la sua; si aggiunge `credenziali_di_prova.auth_user_id → django.auth_user` in `90_end`, `NO ACTION` come la gemella (una cascata la respingerebbe il guard dell'etichetta); da decidere nel giro come si comporta `script.fn_elimina_credenziale` su un utente etichettato (rifiuto con codice, oppure unica porta che toglie etichetta e utente insieme — proposta: la seconda); censimento degli orfani prima dell'`ADD CONSTRAINT`; pgTAP sui due mondi (FK presente su dbdev, assente in CI fino al ponte); documentazione nello stesso giro: COMMENT della tabella (motivo e brief citato), `dbops/manual/credenziali_di_prova.md`, `dbops/manual/trgfn_etichette_di_prova_guard.md`, `dbops/manual/vw_radici_di_prova_in_produzione.md`, `dbops/manual/soggetti_di_prova.md` se confronta le due, la doc di `fn_elimina_credenziale`; `backend/amm-software/manual/api_amm_software.md` al team BE se ne parla; ⑪ DELETE_BLOCK `AFTER DELETE` in fase `a10` → **difetto**, nel giro della Q3 (stesso registro, stesso apply): `dbops.fn_apply_delete_block_trigger` crea il trigger `AFTER`, quindi le cascate delle FK (trigger interni, prima in ordine di nome) cancellano i figli prima del rifiuto, un guard o una FK di un figlio può parlare al posto di `E_DELETE_NOT_ALLOWED`, cascate e storico girano per poi annullarsi, e il nome `a10` (zona dei guard `BEFORE`) mente; i due blocchi scritti a mano (eventi dei documenti generati, versioni dei template) sono già `BEFORE`; il generatore crea `BEFORE DELETE … FOR EACH ROW`, i nove trigger di oggi si ricreano con l'apply, il presidio di convergenza della Q3 controlla anche il momento (un `AFTER` è difforme); pgTAP: trigger generato `BEFORE`, cliente con figli in cascata rifiutato con `E_DELETE_NOT_ALLOWED` e figli intatti; documentazione nello stesso giro: `dbops/manual/automation_delete_block.md`, `fn_apply_delete_block_trigger.md`, `fn_run_automations_delete_block.md`, `proc_automations_delete_block_job.md`, `script/manual/trgfn_delete_block_by_guc.md`, la guida `automazione-db.md`; ⑫ `ADD CONSTRAINT` overlap su dati già sovrapposti → **difetto**, nel giro della Q3 insieme alla D59 (stessa funzione): `dbops.fn_apply_automazione_overlap` non gestisce il `23P01`, quindi ferma la corsa intera (e la catena di `ci_apply`) con l'errore generico, senza dire regola né righe e senza riga d'audit; i dati sovrapposti sono un difetto dei dati, da rendere visibile senza fermare le regole che non c'entrano: un blocco `EXCEPTION WHEN exclusion_violation` per ogni `ADD CONSTRAINT` (variabili a `%TYPE`), audit `WARN` con motivo `DATI_SOVRAPPOSTI`, la tabella e le coppie di id sovrapposte, poi la regola successiva; presidio di convergenza (lo schema della Q3): regola overlap attiva senza il suo vincolo; e la regola si dà per applicata solo col **suo** vincolo, non con un qualsiasi `EXCLUDE` della tabella (`v_any_exclusion`, riconoscimento per presenza); pgTAP: due righe sovrapposte → corsa non ferma, vincolo non nato, audit con le coppie, presidio con la regola, e una seconda regola su un'altra tabella applicata lo stesso; documentazione nello stesso giro: `dbops/manual/automazione_overlap.md`, `dbops/manual/fn_apply_automazione_overlap.md`, `maintenance/manual/proc_automations_overlap_job.md`, guida `automazione-db.md` §4.3, il COMMENT della funzione; ⑬ guard utility solo in `ci_apply`, senza processo → **difetto**, nel giro della Q3 insieme alla D30 (stessa funzione): `ci_apply` chiama a mano seed e apply, quindi la famiglia è invisibile a panorama, roster e presidi dei processi, non converge fra un `ci_apply` e l'altro, non ha runner, e il seed a ogni corsa è una seconda sorgente del registro (come il seed overlap ritirato); nasce il processo `automations_guard_utility` in `dbops.processi` con `ci_ordine` fra delete_block (70) e overlap (80), per esempio 75; nasce il runner `dbops.fn_run_automations_guard_utility` sul modello degli altri, e `ci_apply` chiama quello al posto delle due righe; il seed esce da `ci_apply` (il registro lo scrive il suo CSV di `80_data`; seed come diagnosi o ritiro, con la D30); processo vivo col BB della Q2, registro con la regola unica della Q3; pgTAP: processo in catena al suo posto, `ci_apply` senza l'apply diretto, il runner applica una riga nuova; documentazione nello stesso giro: `dbops/manual/automazione_guard_utility_tipo_ruolo.md`, `fn_apply_automazione_guard_utility_tipo_ruolo.md`, `fn_seed_automazione_guard_utility_tipo_ruolo.md`, una pagina per il runner nuovo, guida `automazione-db.md` (§4.6 e l'elenco dei processi), le guide sui processi che elencano la catena. **La Q14 è chiusa.** |
| Q15 | Giro 1a: `vw_codici_errore_da_dichiarare` e `vw_punti_canale_campo` guardano il solo plpgsql. Una funzione `LANGUAGE sql` può chiamare `fn_log_and_raise_error` con un codice letterale: entrano nel perimetro? | Sì: il corpo ora lo legge il BB anche per le `BEGIN ATOMIC`, e il perimetro di un presidio sui codici è il modello (chi può sollevare), non il linguaggio. Un giro a sé, perché può far comparire righe nuove nei due presidi. **✅ Deciso (Tid, 2026-11-06): sì, in un giro suo**; un codice nuovo che emerge porta la rigenerazione BE (come BE6) |
| Q16 | Giro 2 (D3, D4): dopo la fusione di due vie la via d'origine **resta** in `config.stradario`, sul suo comune e senza più nessuno che la riferisca. Se poi si fondono i due comuni e la stessa via (via generale e codice postale) c'è in tutti e due, la via rimasta collide con quella della destinazione su `uq_stradario_comune_stradario_gen_cp`, e la fusione dei comuni si ferma. «Fondere prima le vie» non basta. Che cosa ne è di una via fusa? | Sul modello le strade sono tre: (a) la fusione delle vie **cancella** la via d'origine, se non la riferisce più nessuno (il registro delle trasformazioni conserva gli id, e `script.fn_get_vie_discendenti` risale per id); (b) la via fusa resta ma è **marcata** come soppressa (una colonna, o il registro), e la fusione dei comuni la lascia sul comune d'origine invece di spostarla; (c) resta com'è, e il doppio lo corregge a mano chi fonde. Raccomandazione: (b), perché la via d'origine è la radice della catena delle trasformazioni e un indirizzo storico può ancora nominarla nelle shadow. Oggi il codice fa (c), in sicurezza: la fusione si ferma con l'elenco invece di scegliere. **✅ Deciso (Tid, 2026-11-07): (b), la via fusa resta ed è marcata come soppressa.** Forma proposta dalla sessione DB, sul modello del ritiro di una voce di catalogo (`obsoleto_dal`, non `attivo = false`, che vuol dire «riferimento valido» e romperebbe chi la nomina nello storico): ① `config.stradario.obsoleto_dal date NULL`, la scrive la fusione delle vie con la data dell'evento; ② `uq_stradario_comune_stradario_gen_cp` diventa parziale sulle vie vive (`WHERE obsoleto_dal IS NULL`): una via soppressa non collide più, e la fusione dei comuni la sposta con le altre (il controllo dei doppi legge già il predicato di un indice parziale); ③ un indirizzo nuovo, o spostato, non può puntare a una via soppressa: il require `dbops.trgfn_child_requires_non_obsolete_parent` su `anagrafiche.indirizzi_dettaglio → config.stradario` (il guard generico del ritiro, nessun guard nuovo); ④ censiti e riallineati i lettori che scelgono una via per il nuovo (lookup, ricerche, normalizzazione), che devono escludere le soppresse; ⑤ una via soppressa non si fonde più (né come origine né come destinazione: codice nuovo). Si fa nel giro 2, blocco 2b, prima dell'apply: stessi oggetti |

ℹ️ La Q7 non c'è: la numerazione l'ha saltata la prima stesura (nessuna versione del brief in git la contiene).
Non manca una decisione.

## 5. Ricadute su BE e FE

Si chiedono quando il giro DB corrispondente è applicato.

| # | Che cosa | Dove | Legata a |
| --- | --- | --- | --- |
| ~~BE1~~ | ~~L'handler della chiusura per scadenza passa `p_classe = 'DOMINIO'`~~ — ritirata (Q5, 2026-11-05): il cancello è il CHECK nel DB | `backend/apps/core/services/coda_lavori/chiusura_scadenze_handler.py:51-60` | D38 (Q5) |
| BE2 ✅ (2026-11-09) | `dbops.vw_non_editable_fields` legge il lock **vivo** (§25.4): elenca ogni colonna che un trigger di lock blocca, `codice_interno` compreso, e non piu' le righe del registro che nessun trigger applica. ① I `gaps` che ripetono una colonna gia' bloccata dal DB si ritirano: al 2026-11-08 `("catalogo", "articoli"): ("codice",)` in `catalogo_service.py` e `codice` di `_EMITTENTE_NON_EDITABLE_GAPS` in `emittenti_fiscali_service.py` (tutte e due bloccate da `automation_lock_columns`); gli altri restano finche' il DB non li dichiara. Il controllo si fa colonna per colonna sulla vista dopo l'apply. ② Le colonne della vista cambiano: escono `exec_mode` e `note`, entra `trigger_name`. `LockColumnsRepository` legge solo `column_name`: nessuna rottura, ma il commento di testata del repository («alias semantico su `automation_lock_columns`») e quello di `non_editable_fields_helper.py` vanno riscritti. ③ Una colonna bloccata da due trigger compare due volte: `list_non_editable` restituisce una tupla, e un `DISTINCT` (o un `set`) evita il doppio | `backend/apps/catalogo/services/catalogo_service.py:126-140`, `backend/apps/anagrafiche/services/emittenti_fiscali_service.py:47-50`, `backend/apps/core/db/lock_columns_repository.py:8-50`, `backend/apps/core/services/non_editable_fields_helper.py` | D25 |
| BE3 ✅ | I controlli preventivi «padre non attivo» si ritirano e si mappa il codice nuovo (`E_ATTIVO_PADRE_NON_ATTIVO`, CONFLITTO_STATO; `E_PADRE_INESISTENTE`, DATO_ERRATO; tutti e due con la colonna FK in `campo`). I commenti che dicono «`E_ATTIVO_REQUIRE`, TECNICO, 500» diventano falsi | `backend/apps/vendite/services/commesse_service.py:552`, `backend/apps/anagrafiche/db/anagrafiche_repository.py:98`; commenti in `backend/apps/magazzino/services/anagrafiche_magazzino_service.py:13-18`, `backend/apps/magazzino/services/magazzino_service.py:208`, `backend/apps/vendite/tests/services/test_commesse_service.py:2035` | D46 (giro 3) |
| BE4 ✅ (2026-11-07) | **Decisione di Tid (2026-11-07): cade il tetto.** `list_lookup_codici` chiama `dbops.fn_get_lookup_codici` con `p_limit` NULL al posto di `LOOKUP_MAX_SOURCE_ROWS` (la costante e il commento «il limit interno è una guardia» si ritirano); la ricerca `ILIKE` e la paginazione con `sql_order_clause` e `fetch_paged_with_total` restano come sono. Da riscrivere la docstring («chiama con limit ampio…, obiettivo: evitare di modificare la funzione DB»). Non dipende dall'apply: lo spareggio DB del giro 7 non cambia il risultato per il backend, che riordina fuori | `backend/apps/core/db/dbops_repository.py:52-55, 378-470` | D57 |
| BE5 ✅ (2026-11-09) | Docstring stantie: «tre viste … SECURITY DEFINER» (`fn_conta_presidio` è INVOKER) e «registro non vuoto» (il corpo ammette vuoto) | `backend/apps/core/db/presidi_repository.py:16-22`, `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py:66-67` | — |
| BE6 ✅ fino al giro 5 | Codici nuovi → rigenerare `error_policies_generated.py`, e le voci di `error_messages_fallback.py`: dal giro 2 `E_DBOPS_CHIAMATA_NON_VALIDA`, `E_MERGE_RIGHE_DOPPIE`, `E_MERGE_FIGLIA_SOTTO_RLS`, `E_STRADARIO_SOPPRESSO` e gli altri di §14.1; dal giro 3 `E_ATTIVO_PADRE_NON_ATTIVO`, `E_PADRE_INESISTENTE`; dal blocco 4b `E_EMITTENTE_MODI_INVALIDO`, `E_EMITTENTE_MODI_NON_SCRIVIBILE` (li vede chi migra, non l'operatore: basta la policy generata); dal giro 5 (✅ 2026-11-07: policy rigenerata, solo i tre codici, nessuna classe mossa; tre ripieghi) `E_CODA_LAVORO_SENZA_EMITTENTE` (TECNICO), `E_CODA_SCOPE_ALTRUI` (NON_PERMESSO), `E_CODA_CHIAVE_ALTRUI` (TECNICO). Poi D12 (giro 9) **Giro 12 ✅ (2026-11-09):** `E_CONTATTI_SOGGETTO_OBBLIGATORIO` (§31.5): policy rigenerata, ripiego scritto. **S-BE-3 ✅ (2026-11-09, §33.7):** `E_SOGGETTO_ID_FISCALE_IMMUTABILE`, policy e ripiego. | `backend/apps/core/services/error_messages_fallback.py:113-123` (la voce di `E_ATTIVO_REQUIRE` dice «trigger configurato male», ora è solo il generatore) | §2.5, §14.1, §15.2, §17.1 |
| BE7 ✅ (2026-11-09) | Commento stantio: il test nomina il presidio `dbops.vw_run_senza_attore`, ritirato | `backend/apps/core/tests/services/test_job_run.py:136-138` | D42 |
| BE8 ✅ (2026-11-09, §33.7) | Il livello «sessione» degli override esce: via `session_key` da `_DIMENSIONI_OVERRIDE` e dalle firme di `ParameterRepository.get_parameter` e affini | `backend/apps/core/db/parameter_repository.py:97-140` | Q10 |
| BE9 ✅ (2026-11-07) | Dopo la RLS su `dbops.coda_lavori` (blocco 5b): il filtro per `scope_key` scritto a mano negli elenchi e nei conteggi della coda lavori si ritira, la separazione la fa il DB (come per la coda di stampa). ⚠️ Cambia che cosa vede un operatore: oggi i lavori con la sua stessa `scope_key`, dopo quelli della sua azienda; i lavori SISTEMA solo il super admin | `backend/apps/core/services/coda_lavori/gestione_service.py:83-320`, `CodaLavoriRepository` | Q14.3 |
| BE11 ✅ (2026-11-08) | **Insieme all'apply del blocco 7-bis-c (§23.12); prima si rompe il salvataggio delle preferenze.** (a) Lo snapshot della preferenza si rinomina: `preset_base_data_update` → `preset_base_contenuto_aggiornato_il` in `ui.lista_preferenza_utente` e `ui.dashboard_preferenza_utente` (le SELECT e gli upsert dei due repository, i kwargs dei due service e dei test). (b) `get_preset_base_snapshot` legge `contenuto_aggiornato_il` del preset, non `data_update`: oggi `data_update` è l'audit. (c) ⛔ Gli UPDATE di `ui_admin_repository.py` (`update_definizione`, `update_colonna`, `update_preset` e gli upsert dei permessi) non scrivono più `user_update` né `data_update = now()` (`extra_set`): lo fa il trigger di audit dal JWT (`app.jwt_user`). È la stessa regola su due livelli; sui preset l'`extra_set` spostava anche la data del contenuto quando l'admin cambiava solo `attivo`. (d) Rifiuti nuovi dal guard ATTIVO, da mappare se il BE li fa scattare: non si spegne una lista che ha colonne o preset attivi, né una dashboard che ha preset attivi (BLOCK); non nasce né si riattiva una colonna o un preset su una lista spenta, né un widget su un'area o un'azione spenta (REQUIRE). I codici sono `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (BLOCK) ed `E_ATTIVO_PADRE_NON_ATTIVO` (REQUIRE), già in policy. Il commento di `ListaConfigurabile.vue:743` («`preset.data_update` corrente») va riscritto | `backend/apps/ui/db/ui_repository.py:285-360`, `backend/apps/ui/db/dashboard_repository.py:85-150`, `backend/apps/ui/services/lista_preferenza_service.py`, `dashboard_preferenza_service.py`, `backend/apps/ui/db/ui_admin_repository.py:232-260, 469-510, 662-700, 843-880`, i test in `backend/apps/ui/tests/` | §23.12 |
| BE12 ✅ (2026-11-09) | Dopo l'apply del giro 9: il filtro `attivo` della lista dei processi non dice piu' se un processo e' vivo (la data del ritiro e' l'unica sede). Il filtro «vivo» si chiede al DB (`NOT script.fn_e_obsoleto(p.obsoleto_dal)`), non si ricalcola; `attivo` resta una colonna del catalogo. Con BE6 per `W_TXID_BYPASS_PARAMETRO_ASSENTE` | `backend/apps/core/db/processi_repository.py:75, 238-240` | D11 (Q2) |
| BE10 ✅ (2026-11-07) | **Prima della RLS (blocco 5b), dal 5a.** (a) ⛔ Un lavoro OPERATORE nasce dentro un'azienda: in modalità globale si accoda un lavoro per azienda, o si chiede di sceglierla. Dall'apply del 5a la porta rifiuta un lavoro senza emittente attivo nello scope (`E_CODA_LAVORO_SENZA_EMITTENTE`): oggi lo accodano il giro di fatturazione dal cockpit in modalità globale (FATTURAZIONE_GIRO/NUMERA, dbdev, ultimo 2026-10-26) e chiunque catturi uno scope senza emittente attivo. (b) Il drenatore della coda lavori prende, recupera e chiude i lavori **un'azienda alla volta**, con l'utente tecnico di `draina_coda_lavori` di quell'azienda (`dbops.vw_processi_roster`), come `draina_coda_stampa`; i lavori SISTEMA li vede ogni utente tecnico del drenatore (`claim` con `SKIP LOCKED`). Claim, reaper, `mark_done`/`mark_error` sotto quell'identità; l'esecuzione del lavoro resta con l'identità dello scope. Un'azienda senza utente tecnico non viene drenata, e lo dice `vw_processi_dominio_senza_identita`. (c) La porta, da una sessione dell'applicazione, accoda un lavoro OPERATORE solo a nome di chi è in sessione e nel suo perimetro (`E_CODA_SCOPE_ALTRUI`), e la chiave di un lavoro OPERATORE deve contenere la sua azienda (`E_CODA_CHIAVE_ALTRUI`): da censire i punti che accodano a nome d'altri | `backend/apps/core/services/coda_lavori/drainer_service.py`, `repository.py` (`claim`, `reap_stale`, `mark_*`), `scope.py`, i chiamanti di `CodaLavoriRepository.accoda` | Q14.3, §18 |

Nessuna ricaduta FE diretta: D25 si vede nel form quando BE2 è fatto.

**Stato al 2026-11-06** (giro C1 e giro 1 applicati): **nessuna ricaduta chiede lavoro al BE.** BE2-BE4,
BE6, BE8 e BE9 aspettano giri non ancora scritti (in che giro: §8); BE1 è ritirata. BE6 si chiede una volta
alla fine del giro 3, per i codici dei giri 2 e 3; i codici dei giri successivi (D12 nel giro 9, quelli che emergono dal giro 12)
la richiedono nel loro giro. BE5 e BE7 sono commenti, si fanno quando capita.
Censiti nel backend (`.py`) gli oggetti ritirati o cambiati da quei giri: nessun chiamante. Restano due mock
in `test_tracciamento_repositories.py`, che usano `fn_run_automations` come nome qualunque in una riga di
`audit_log` finta: non si rompono e non vanno toccati. Le tre viste del blocco 1a che il BE legge nei suoi
test (`vw_punti_canale_campo`, `vw_stati_check_scrittori`, `vw_codici_errore_da_dichiarare`) non hanno
perso né rinominato colonne: sono cambiate con `CREATE OR REPLACE VIEW`, che non lo permette.

**Stato al 2026-11-07** (giro 2 applicato, giro 3 scritto): dopo l'apply del giro 3 si chiedono **BE3** e
**BE6**, una volta sola per i codici dei giri 2 e 3. Il giro 3 non cambia firme né colonne di oggetti che il
backend legga; cambia i codici che i guard ATTIVO sollevano (un 500 che diventa 409 o 400) e la frase.
Censiti nel backend: i due controlli preventivi di BE3 e i tre commenti che li motivano.

**Stato al 2026-11-07, dopo il giro BE** (team BE, da committare): **BE3 e BE6 fatte.**

* **BE6.** `error_policies_generated.py` rigenerato (venti codici nuovi dei giri 2, 3, 4b e del lotto T di
  `brief-db-sorgente-documento-e-riga`; nessuna classe esistente cambiata, `--check` pulito), venti
  ripieghi in `error_messages_fallback.py`. La frase di ripiego di `E_ATTIVO_REQUIRE` ora dice solo il
  generatore.
* **BE3.** Ritirato il controllo preventivo del responsabile in `commesse_service.aggiorna_commessa_testata`,
  e con lui `get_risorsa_umana_lookup` (repository e service), che serviva solo a quello: il rifiuto è il
  409 `E_ATTIVO_PADRE_NON_ATTIVO` del require, col campo. La persona inesistente resta la FK (`E_VENDITE_FK`
  col campo). Prova sul DB vero: `vendite/tests/db/test_commessa_testata_db.py`. Il controllo del magazzino
  (`magazzino_service._magazzino_o_400`) resta: legge il magazzino sotto la RLS e risponde anche «fuori dal
  tuo perimetro», che il require non dice; corretto il solo commento.
  Nessun override `highlight_form_fields` sui due codici: sono guard generici, e la colonna FK non è sempre
  un input della pagina (`api.md` §la promessa e il canale). Resta il banner di classe.

**⏭️ Segnalazione al team DB (S-BE-1, 2026-11-07): la frase dei due codici nomina le tabelle.**
`E_ATTIVO_PADRE_NON_ATTIVO` ed `E_PADRE_INESISTENTE` sono dichiarati «per l'operatore» (§15, pagina
`manual/trgfn_child_requires_active_parent.md` §Codici errore), ma i valori della frase sono `v_padre` e
`v_figlia`, cioè `schema.tabella`: sulla commessa l'operatore legge *«anagrafiche.risorse_umane (id = 5) non
è attivo: non vi si può collegare una riga attiva di vendite.commesse»*. Fino a BE3 il backend la copriva con
una frase sua; ritirato il controllo (decisione di Tid, 2026-11-07), è questa la frase che arriva a video.
Non sono parole dell'operatore, e il catalogo serve anche portale e shop, dove un nome di tabella è
ricognizione regalata (la stessa ragione per cui `targets` porta un codice di `config.tipi_entita`, mai
una tabella: `api.md` §`targets`). Si chiede al team DB di decidere la forma: il nome della cosa al posto
della tabella (da dove leggerlo è una scelta del modello), i nomi tecnici nel solo contesto del diario.
Il backend non ha niente da cambiare quando la frase cambia: la legge dal catalogo.

**✅ Decisione di Tid (2026-11-07) su S-BE-1: il nome viene da `config.tipi_entita`, non dalla tabella.**
Proposta del team BE, accettata. Si chiede al team DB:

1. **La frase non nomina più né il padre né la figlia.** Diventa la frase della cosa, senza valori di
   tabella: per esempio *«La riga a cui si collega non è attiva: non vi si può collegare una riga
   attiva.»* (`E_ATTIVO_PADRE_NON_ATTIVO`) e *«La riga a cui si collega non esiste.»*
   (`E_PADRE_INESISTENTE`), cioè le frasi che il backend ha già come ripiego.
2. **QUALE cosa lo dice il bersaglio, non la frase.** Il trigger mette il padre nel campo strutturato
   `DATATYPE` come bersaglio — il codice di `config.tipi_entita` e l'id della riga — come ogni altro
   bersaglio del catalogo (`brief-db-bersaglio-errore` §4.4). Il backend lo legge già
   (`db_error_fields.bersagli_envelope` → `targets` dell'envelope), e il frontend lo mostra con
   l'`etichetta_key` di quel tipo: il nome è tradotto, e un portale o uno shop non vedono una tabella.
   ⚠️ Niente nome nella frase anche quando il tipo c'è: `etichetta_key` è una chiave di traduzione,
   e una frase del DB che la ricopiasse in chiaro sarebbe un secondo vocabolario.
3. **Da dove il trigger sa il tipo: è la scelta del modello che resta al team DB.** `config.tipi_entita`
   non ha una colonna con la tabella; `sorgente_codice_interno` porta a `config.sorgenti` solo per i
   tipi che sono sorgenti, e il padre di un require spesso non lo è (`anagrafiche.risorse_umane`). La
   forma che il backend suggerisce, perché resta dichiarativa: il codice del tipo come **argomento del
   trigger**, scritto da chi lo monta (`dbops.fn_run_automations_attivo` lo legge dalla FK), con
   `E_TRIGGER_ARGOMENTI_INVALIDI` se non è un codice del catalogo.
   ⛔ Un padre senza un tipo nel catalogo **non** è un caso da coprire con la tabella: il bersaglio
   manca, la frase regge da sola (`api.md` §`targets`: il bersaglio è facoltativo).
4. **I nomi tecnici restano nel contesto del diario** (`dbops.error_log`), padre, figlia e id: chi
   legge il diario è chi ripara il dato.

Ricaduta BE: **nessuna obbligatoria** — frase e bersaglio arrivano dai canali che il backend legge già.
All'apply va solo provato un rifiuto vero (un pgTAP o un test sul DB) che porti `targets` fino
all'envelope.

**Stato al 2026-11-07, BE10 (team BE, da committare): (a), (b) e (c) fatte.**

* **(b) Il drenatore per azienda.** `draina_coda_lavori_per_roster` (nuovo, in `drainer_service.py`) gira un'azienda
  alla volta con l'utente tecnico di `draina_coda_lavori`; il command lo chiama, e chiude rosso (D9) se il giro di
  un'azienda non parte. ⛔ **Il difetto trovato per strada, che non dava errore**: `operator_identity_context`,
  uscendo, **azzerava** i GUC invece di rimettere quelli di prima. Dentro il giro del badge, la `mark_done` dopo un
  lavoro OPERATORE sarebbe girata senza identità: sotto la RLS del 5b zero righe aggiornate, il lavoro IN_CORSO fino
  al reaper. Ora rimette l'identità esterna; i lavori SISTEMA girano in `senza_identita_context` (col badge addosso
  avrebbero il perimetro di quell'azienda). Provato sul DB vero (`core/tests/db/test_identita_annidata_db.py`, rosso
  per mutazione).
  ⚠️ **Roster vuoto = niente drenato**, nemmeno i lavori SISTEMA, e il command lo scrive per primo. Gli utenti tecnici
  si possono creare **già ora** (`draina_coda_lavori` è DOMINIO dal 5a): conviene farlo prima del deploy di questo
  giro BE, o la coda si ferma finché non ci sono.
* **(c) Chi accoda a nome d'altri.** Censiti i chiamanti di `accoda`. Il produttore del giro notturno
  (`accoda_giri_fatturazione`, command `run_fatturazione_batch`, anche da «Esegui ora») accodava fuori da ogni
  identità: dal 5a **ogni azienda tornava `E_CODA_SCOPE_ALTRUI`** (ricavato dal codice, non osservato sul dbdev).
  Ora accoda dentro l'identità del badge. Le chiavi: quella del giro contiene la `scope_key` (l'azienda, quando è
  una); quella di «Esegui ora» (`esegui:<unit>`) no, ed è risolta col punto sotto.
* **«Esegui ora» è un lavoro SISTEMA** (decisione di Tid, 2026-11-07). `avvio_manuale` è di MANUTENZIONE, quindi il
  guard di classe lo ammette già; chi preme viaggia nel payload (`richiesto_da`) come attore del comando. Un lavoro
  per azienda sarebbe stato falso (il comando serve da sé tutto il suo roster) e la chiave senza azienda avrebbe dato
  `E_CODA_CHIAVE_ALTRUI`. ⚠️ Dopo il 5b un lavoro SISTEMA lo vedono solo super admin e drenatore: oggi «Esegui ora» è
  solo `SUPER_ADMIN` (`AdminAPIView`), quindi chi preme continua a vederlo.
* **Regola del 2 (ok Tid, 2026-11-07).** Il giro sul roster era scritto tre volte (stampa, email, produttore della
  fatturazione), con nomi già divergenti; BE10 sarebbe stata la quarta. Estratto il BB
  `apps/core/services/giro_per_azienda.py`, ritirate le tre copie nello stesso giro, voce nel catalogo BB.
* **(a) Il cockpit accoda un lavoro per azienda** (scelta A di Tid, 2026-11-07). `POST fatturazione/run/` e
  `fatturazione/numera/` rispondono `{lavori: [...]}`: uno con un'azienda scelta, uno per ciascuna azienda della combo
  di topbar dalla modalità globale (`aziende_della_richiesta`, `scope_in_azienda` in `coda_lavori/scope.py`; il ciclo in
  `vendite/services/fatturazione_accodamento_service.py`). Lo scope di ogni lavoro è quello che avrebbe catturato chi
  sceglie l'azienda, e quello del giro notturno: la chiave di dedup è una per (atto, azienda) qualunque strada arrivi.
  **Le selezioni si dividono per azienda** (decisione di Tid): i gruppi dalla `vw_dash_competenza_gruppi` della
  competenza, i lotti dalla loro azienda; una riga senza azienda è un 400 e non si accoda niente (tutto o niente, il
  gesto è uno). FE: `useJobPolling().seguiLavori` (regola del 2, ok Tid) in cockpit e lista Lotti; il verbo di mese
  resta a un gesto per volta, tenuto dal pulsante.
  ⭐ **Anticipato BE9 per l'ownership** (decisione di Tid): col lavoro per azienda la `scope_key` del lavoro è quella
  dell'azienda («3»), e chi l'aveva accodato in modalità globale («3,4») non l'avrebbe più visto — polling a 404, UI
  code vuota. Ora un lavoro è di chi ha la sua `emittente_fiscale_id` nel perimetro, la regola della policy, in due
  frammenti del repository (`_filtro_perimetro`, `_espr_nel_perimetro`) usati da polling, elenchi, conteggi, azioni,
  `is_mio` e lo split miei/altri del cockpit. ⚠️ Cambia cosa vede un operatore già da ora: i lavori delle sue aziende,
  i SISTEMA solo chi non ha filtro. **A BE9, dopo il 5b, resta solo ritirare il filtro**: lo fa la RLS. Presidio sul DB
  vero: `core/tests/db/test_coda_perimetro_db.py`, rosso per mutazione.
* **Utenti tecnici** (creati da Tid, 2026-11-07, letti da `vw_processi_roster`): `draina_coda_lavori` serve DEVA, DEVB,
  PGTAPEF202; ⚠️ **EMITEST non è servita** (gli altri tre processi del roster sì). Finché manca, la coda lavori di
  EMITEST non si drena, e il command lo scrive a ogni corsa: va creato prima del 5b
  (`script.fn_crea_utente_tecnico('draina_coda_lavori', 'EMITEST')`).

**Stato al 2026-11-07, BE9 e il test di S-BE-2 (team BE, committato su `dev/backend-tid`): fatti.**

* **S-BE-2**: `test_avvio_manuale_catalogo` vuole SISTEMA; il suo accodamento reale gira come **super admin**
  (`apri_contesto_operatore(cur, super_admin=True)`, nuovo parametro del BB), perché sotto la RLS una riga SISTEMA la
  vedono solo il super admin e il drenatore — senza, la rilettura tornava `{}`.
* **BE9, il filtro si ritira.** `_filtro_perimetro` e i parametri `owner_emittenti`/`caller_emittenti` del
  repository non ci sono più: elenco, conteggi del badge, dettaglio, stato e polling leggono ciò che la RLS mostra.
* ⭐ **Decisione di Tid nel giro: «mio» è per PERSONA.** Con la RLS accesa «mio = della mia azienda» (BE10 a) sarebbe
  stato vero per ogni lavoro visibile. Ora `ambito=miei` = i lavori **accodati da me**, `tutti` = tutti quelli **delle
  mie aziende**: la semantica della coda stampa (una per le due code, decisione del 2026-07-23). Una regola sola in SQL,
  `_espr_accodato_da` — `scope.auth_user_id` per un OPERATORE, `payload.richiesto_da` per il SISTEMA di «Esegui ora» —
  usata dal filtro «miei», da `is_mio` e dallo split miei/altri del cockpit (`operatore_coda`). Dettaglio e azioni sui
  lavori dei colleghi restano dietro `code_manage`; il polling dei giri non restringe ai miei (dedup condivisa).
* **Lo stato vero** dopo l'accodamento anche per «Esegui ora» (`stati_dopo_accodamento`, regola del 2 con la
  fatturazione): il super admin vede il SISTEMA che ha accodato.
* **Fixture dei test sul DB vero** rotte dal 5b o dal giro C.3 (di `brief-db-sorgente-documento-e-riga`):
  `test_coda_lavori_summary_corse` e `test_coda_lavori_vivi_per_chiave` scrivono come super admin;
  `test_ricerca_liste_db` compone la chiave del push con `script.fn_segment_key`; `test_prezzo_riga_commessa_db`
  rilegge la chiave del documento dalla colonna del suo tipo. `test_coda_perimetro_db` era il presidio del filtro
  ritirato: ora prova `_espr_accodato_da` su righe **costruite** e l'SQL di ogni lettura, non la popolazione.
* **Analisi critica del giro** (2026-11-07): nessun bug di logica; corretto ciò che attorno al diff raccontava
  ancora la semantica vecchia. Il parametro OpenAPI `ambito` (condiviso dalle due code) diceva «`tutti` richiede
  `code_manage`», falso già dal 2026-07-23: ora `miei` = accodate/innescate da me, `tutti` = il perimetro d'azienda
  della RLS, `code_manage` solo per dettaglio e azioni altrui. Riallineate le docstring di lista, dettaglio e annullo
  in `views_tracciamento.py` (erano sulla `scope_key`) e due righe del catalogo BB (`owner_emittenti` in `requeue` e
  `count_per_stato`, `scope_key_da_emittenti`). In `test_prezzo_riga_commessa_db` la variabile locale è
  `sorgente_chiave`: porta la chiave del documento (id o uid), non un uid.
* ⚠️ **Residuo, fuori da questo cantiere**: il nome `sorgente_uid` per «la chiave del documento, id o uid» vive nel
  contratto DB (`p_sorgente_uid` della madre `fn_upsert_commessa_attivita` e della porta del link, la chiave JSON
  del batch) e in molti service BE che vi passano un id (`ordini_service`, `ddt_service`, `commesse_service`, push
  orchestrator, source handlers). Il rinomina lo sta facendo il team DB (Tid, 2026-11-07), nel tema di
  `brief-db-sorgente-documento-e-riga`; il BE si allinea all'apply, con una prova a chiamata reale (binding per
  nome). Restano `sorgente_uid` i lister `fn_list_*_da_pushare` e `PushableRow`: lì è davvero l'uid.
* Aperto, da decidere: `conteggi_code(user, *, auth_user_id)` non usa più `user` dopo BE9. Resta per la firma dei
  contatori dashboard-home; se non serve, si toglie con la view e due test.

**✅ Richiesta al team DB (S-BE-2, 2026-11-07): il tipo `ESEGUI_PROCESSO` dice ancora OPERATORE.** Fatta nel blocco 5b
(§18.9), con la regola canale/`run_as` ristretta ai `CODA` di `DOMINIO` (decisione di Tid); all'apply si avvisa il BE. In
`80_data/sql/dbops/coda_lavori_tipi.csv` la riga ha `run_as_default = OPERATORE` e la descrizione «con l'identità di chi
preme (run_as OPERATORE)». Il backend passa `SISTEMA` esplicito, quindi non è un blocco; ma il default è il
suggerimento che chiunque altro accodi leggerebbe, e la pagina `manual/coda_lavori_tipi` lo ripete. Si chiede di
portarli a `SISTEMA`, con la ragione. ⚠️ Nello stesso giro il backend gira una riga di
`core/tests/db/test_avvio_manuale_catalogo.py` (`test_tipo_esegui_processo`, che oggi pretende OPERATORE): va detto al
team BE all'apply.

**Stato al 2026-11-08, BE11 (team BE, da committare su `dev/backend-tid`): (a), (b), (c) e (d) fatte.**

* **(a) Lo snapshot rinominato.** `preset_base_contenuto_aggiornato_il` nelle SELECT e negli upsert di
  `UiRepository` e `DashboardRepository`, nei kwargs dei due service delle preferenze e nei loro test. Prima del giro
  il salvataggio di una preferenza dava `E_DATABASE` sul DB vero (`ui/tests/db/test_misure_pagina_db`, rosso con la
  suite unitaria verde: i mock non vedono il nome di una colonna).
* **(b) La data del contenuto.** Il BB `fetch_preset_base_snapshot` legge `contenuto_aggiornato_il` sui tre livelli
  della cascata; il ripiego `COALESCE(data_update, data_insert)` (DEF-2, 2026-05-11) si ritira, perché la colonna è
  `NOT NULL`.
* **(c) L'audit a mano si ritira, per intero.** Gli UPDATE di `UiAdminRepository` (`update_definizione`,
  `update_colonna`, `update_preset`) non nominano più `user_update` né `data_update` (via l'`extra_set` e la voce
  nelle whitelist); l'upsert dei permessi non scrive più `data_update`/`user_update` nel ramo `DO UPDATE`. Nello
  stesso giro, sullo stesso argomento, anche **gli INSERT** (`create_definizione`, `create_colonna`, `create_preset`,
  `upsert_permesso`) non passano più `user_insert`: il trigger generico lo scrive sull'INSERT dal JWT e sovrascriveva
  quello del BE, quindi era la stessa regola su due livelli. I quattro service admin non chiamano più `user_label`; la
  testata della classe `UiAdminRepository` dice perché. `apps/ui/services/_audit.py` (`user_label`), rimasto senza
  consumatori, è ritirato (ok di Tid, 2026-11-08).
* **(d) I rifiuti del guard.** Nessun service admin li anticipa con un controllo preventivo: spegnere una lista con
  colonne attive arriva all'operatore come `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, 409, non come il fallback di validazione
  del service. Nessun mapping da aggiungere.
* **Il presidio** è `ui/tests/db/test_audit_ui_dal_trigger_db` (DB vero, sei test, i soggetti costruiti nel test):
  INSERT e UPDATE admin con l'audit dal trigger (`app.jwt_user`), la data del contenuto ferma su `descrizione` e
  `attivo` e mossa su `filtri_default`, lo snapshot e l'upsert della preferenza col nome nuovo, i due rami dell'upsert
  dei permessi, il 409 del BLOCK. Allineati `test_update_colonna_repository` e i test SQL di
  `test_lista_preset_admin_service` / `test_lista_definizione_admin_service` (l'SQL senza audit); il commento di
  `ListaConfigurabile.vue` (lo snapshot è la data del contenuto).
* **Esteso a tutto il backend** (decisione di Tid, 2026-11-08: «correggi dove data update/insert vengono aggiornate
  ed esiste il trigger»). Censite le scritture a mano di `data_update`/`user_update`/`user_insert` e incrociate con la
  scheda auto-generata di ogni tabella: **24 punti** su tabelle col trigger, tutti ritirati — `core/db/email_repository`
  (5: account, test dell'account, template, bozza e stato dell'outbox), `core/db/auth_repository` (invito),
  `core/db/parameter_repository` (upsert dell'override), `core/services/idempotency_store` (2), `portale/db/
  portale_repository` (disattivazione dell'identità), `vendite/db/commesse_repository` (2), `vendite/db/
  listini_repository` (2), `vendite/db/pipeline_repository` (10: lotti, log, coda di stampa, attività fatturabili).
  Il commento della coda di stampa diceva «la tabella non ha trigger audit»: falso, il trigger c'è e scrive anche il
  `data_update` che il reaper legge come istante del claim (stesso valore, `CURRENT_TIMESTAMP` della transazione). Il
  comportamento non cambia in nessun punto: il trigger sovrascriveva già. **Restano**, giusti, i quattro `data_update`
  delle due `*_preferenza_utente`, che il trigger non ce l'hanno. La regola è scritta in [api.md](../api.md)
  §«Propagazione identita' al DB (GUC)», e la doc del BB `execute_dynamic_update` (codice e catalogo) non porta più
  l'audit come esempio di `extra_set`. Un test era verde a vuoto e dichiarava una prova che non poteva fare:
  `core/tests/db/test_scritture_email_note_db` portava indietro `data_update` con un UPDATE (che il trigger rimetteva
  a `now()`) e poi lo trovava «aggiornato»; il controllo esce, col motivo nel commento.


**Stato al 2026-11-09, BE2, BE5, BE7, BE12 (team BE, da committare su `dev/backend-tid`): fatte.** BE6 per i codici
dei giri 9 e 10c era già in policy (`W_TXID_BYPASS_PARAMETRO_ASSENTE`, `E_GUARD_UTILITY`, con i ripieghi):
`genera_error_policies --check` pulito sul dbdev.

* **BE12.** Il filtro della lista dei processi si chiama **`vivo`** (query param, service, repository, store FE)
  e chiede al DB `NOT script.fn_e_obsoleto(p.obsoleto_dal)` (`false` = ritirato); `attivo` resta colonna e
  ordinamento. Il nome cambia perché un filtro `attivo` che risponde «vivo» direbbe il falso. (Il filtro ha
  un comando a video dalla rilettura critica, sotto.) Controesempio datato, non motivo
  (dbdev, 2026-11-09): `sync_auth_user_active` ha `attivo = true` e il ritiro raggiunto, e col filtro vecchio
  usciva fra i vivi. Presidio sul DB vero, coi tre casi costruiti su un processo del seed (data vuota, futura,
  raggiunta con `attivo` true): `core/tests/db/test_processi_filtro_vivo_db`, rosso per mutazione.
  ⚠️ Fuori dal BE: la pagina auto-generata di `script.fn_e_obsoleto` ha ancora il COMMENT del 2026-11-06
  («⛔ Non è la regola dei processi»), smentito dal giro 9 (N2): va rigenerata con le altre schede di §24.8 punto 4.
* **BE2.** Ritirati i gap `catalogo.articoli.codice` (`catalogo_service._NON_EDITABLE_DB_GAPS`) e `codice`
  dell'emittente (`_EMITTENTE_NON_EDITABLE_GAPS`): la vista li dichiara (letto su dbdev, anche dal ramo per
  record `fn_non_editable_fields`). Gli altri gap restano, controllati colonna per colonna: il DB non li blocca
  (`articoli_uom_operativa.uom_id`, `unita_misura_conversioni.uom_from_id/uom_to_id`, `emittenti_fiscali.soggetto_id`,
  le dimensioni delle due matrici). `LockColumnsRepository.list_non_editable` legge `DISTINCT`; riscritti i
  commenti del repository, dell'helper e dei due service. I due test unitari che pretendevano `codice` dal gap
  con la vista mockata vuota ora provano il contrario; presidio sul DB vero che le colonne uscite dai gap le
  dichiari la vista: `core/tests/db/test_lock_columns_vivo_db`.
  ✅ ~~Segnalazione: `soggetti_service._compute_non_editable_fields` non legge la vista~~ — chiusa il 2026-11-09
  con S-BE-3 (sotto): la lista del soggetto passa dal BB e porta `codice` dalla vista.
* **BE5, BE7.** Commenti riallineati: in `presidi_repository.py` a attraversare la RLS è
  `fn_conta_presidio_per_variante` (DEFINER), non `fn_conta_presidio` (INVOKER dal 2026-10-10); la docstring del
  guardrail dei codici ammette il registro vuoto; il test del giornale non nomina più il presidio ritirato come scopo.

**Rilettura critica del giro BE (2026-11-09, team BE, da committare su `dev/backend-tid`).**

* **BE12, la proiezione.** Il filtro chiedeva il DB ma lista e drawer mostravano `attivo`: un processo col ritiro
  raggiunto e `attivo = true` usciva dal filtro «vivi» e il drawer non diceva che era ritirato. L'espressione è
  ora una sola, `_SQL_VIVO` in `processi_repository.py`, usata dal filtro e proiettata come `vivo` da lista e
  dettaglio; il drawer legge `vivo` («Ritirato dal …», o «Ritiro programmato al …» con la data futura). Il
  filtro ha la sua tendina (vivi / ritirati / tutti). Presidio esteso: `test_processi_filtro_vivo_db` prova anche
  la colonna proiettata.
* **Classi e canali del pannello.** La tendina dei canali era una copia a mano senza presidio, e le mancava
  `CODA_AUTOMATICA`. Ora le tendine leggono `GET /amm-software/processi/vocabolari/`, che consegna le costanti di
  validazione del service (`_CLASSI`, `_CANALI`, già confrontate coi CHECK dal loro guardrail).
* **Lock di colonna.** La cache di `LockColumnsRepository.list_non_editable` conservava anche il fallback vuoto
  di un errore DB, fino al riavvio del worker: col BE2 il form avrebbe lasciato modificare `codice`. Ora in cache
  va solo la lettura riuscita. Il ramo per record (`record_id`) è entrato nel BB `compute_non_editable_fields`,
  e la copia privata di catalogo è ritirata (regola del 2, ok Tid). `test_lock_columns_vivo_db` non legge più
  una riga con `LIMIT 1` (passava saltando su un DB vuoto) e fallisce se il ramo per record ripiega sugli statici.
* **Ordinamento dei processi.** `_ORDER_AMMESSI` del service era una copia a mano delle chiavi del repository:
  ora il service legge `PROCESSI_SORT_COLUMNS`.

**⏭️ Segnalazione al team DB (S-BE-2, 2026-11-09): la colonna `vivo` nel catalogo della lista `amm.processi`.**
Il backend la proietta già (booleano, `NOT script.fn_e_obsoleto(p.obsoleto_dal)`), ma il catalogo della lista ha
solo `attivo`, che non dice se un processo è ritirato. Serve la colonna `vivo` nel seed della lista (ordinabile).
Dopo l'apply il team BE aggiunge `"vivo": _SQL_VIVO` a `PROCESSI_SORT_COLUMNS` (il presidio
`test_liste_configurabili_seed` lo chiede nei due versi) e la cella col tag nella tab. Se `attivo` debba restare a
video accanto a `vivo` lo decide Tid.

**⏭️ Segnalazione al team DB (S-BE-3, 2026-11-09): CF e P.IVA valorizzati sono immutabili, e oggi non lo
impone nessuno.**

*Il difetto.* La regola «CF e P.IVA bloccati se valorizzati» esisteva solo come metadato del form
(`soggetti_service._compute_non_editable_fields`, più una copia nel FE). La PATCH del soggetto accetta
`codice_fiscale` e `partita_iva` (sono in `SOGGETTO_UPDATE_COLS`), e il DB non ha né un trigger di lock né una
riga in `dbops.lock_columns_conditional` su quelle colonne: una PATCH diretta cambia un CF valorizzato con un 200.
Una promessa senza esecutore.

*Decisione di Tid (2026-11-09).* CF e P.IVA sono immutabili: si blocca ciò che fa l'unicità. La chiave è la
colonna generata `id_fiscale_univoco_cf_piva` (`uq_soggetto_idstato_id_fiscale_univoco`, con `stato_id`), che
contiene **tutti e due** quando ci sono entrambi e diversi, altrimenti quello presente. Quindi:
* un CF o una P.IVA **valorizzati** non si cambiano e non si svuotano;
* un campo **vuoto** resta riempibile (il privato che apre la partita IVA, la società senza CF distinto): la
  chiave cambia, ma da un'identità incompleta a una completa, non da un soggetto a un altro. *(Lettura della
  sessione BE da confermare con Tid nel giro.)*

*Cosa serve al DB.*
1. Il guard: un trigger `BEFORE UPDATE OF codice_fiscale, partita_iva` su `anagrafiche.soggetti` che rifiuta
   `OLD.x IS NOT NULL AND NEW.x IS DISTINCT FROM OLD.x`, con un codice a catalogo (campo strutturato per il
   form). Se il meccanismo giusto è il trigger di lock generico esteso ai condizionali, lo decide il team DB.
2. La dichiarazione: le due righe in `dbops.lock_columns_conditional` (condizione «valorizzato sul record
   `$1::uuid`»), così `fn_non_editable_fields` le restituisce. ⚠️ Oggi il registro lo **applica** solo il guard
   degli articoli: una riga senza il guard del punto 1 rifarebbe lo stesso difetto, in un altro posto.
3. pgTAP: cambio e svuotamento rifiutati, riempimento di un vuoto ammesso, per CF e per P.IVA.

*Fatto lato BE e FE (2026-11-09, da committare).* La lista del soggetto passa dal BB
`compute_non_editable_fields`: porta `codice` dalla vista (il DB lo blocca, la lista non lo diceva), e CF e P.IVA
valorizzati restano come **gap** dichiarato. Il FE non rifà più la regola: disabilita solo ciò che la lista dice.
Presidio sul DB vero: `codice` del soggetto in `test_lock_columns_vivo_db`.
*Dopo l'apply.* Il team BE toglie il gap e passa `record_id` al BB (la lista arriva da `fn_non_editable_fields`),
e mappa il codice nuovo sul campo nella PATCH.

## 6. Difetti fuori schema trovati leggendo i chiamanti

* `vendite.trgfn_listini_righe_guard_periodicita_quota_fissa` scatta solo su `UPDATE OF periodicita`:
  l'INSERT di una riga a quota fissa senza periodicità su una versione già ATTIVA passa, e la regola del
  dominio è chiusa a metà. Da portare al cantiere dei listini.
* `vendite.vw_preventivi_smistamento`: copia in linea del predicato «natura è merce» (vedi D72).
* `db/changelog/migrations/50_dbops/20250922-05…` e `-06…`: stessi id di changeSet; il primo albero è
  congelato, solo annotazione.

## 7. La documentazione già corretta (2026-11-03/04)

* Le 239 pagine `docs/it/dbzero/dbops/manual/`: 201 riscritte allo standard, 38 create per gli oggetti
  che non l'avevano. Tutte passano la verifica di `standard-guide.md` §«Verifica di una pagina
  `manual/`». Le correzioni di contenuto (codici errore mancanti, colonne inesistenti, chiamanti,
  comportamenti cambiati) sono nella pagina di ciascun oggetto.
* Il blocco comune `dbops/_fixture-pgtap.md`, le guide e le pagine fuori schema che dicevano il falso
  su oggetti `dbops`, e i link da guide, tutorial e `dev/` verso `/dbzero/dbops/manual/` ripuntati alle
  schede. L'elenco è in §7.1.

### 7.1 Doc fuori schema

Tutte con la data al 2026-11-04.

| File | Correzione |
| --- | --- |
| `guide/storicizzazione-tabelle.md` | Sei modi (con `COPPIA`); `p_exec_mode` è `CI` o `SCHEDULED`, valgono le regole `AUTO` o uguali |
| `linee-guida-sql.md` §9 | Il trigger generato è `trg_{table}_gen_tx_id_ins_upd` |
| `guide/tx_id_implementation_guide.md` | Un canale irraggiungibile blocca la scrittura (D1); l'interruttore lo rispetta solo `fn_ensure_logconn` (D26); senza parametro il bypass di sessione è ignorato (D12) |
| `guide/Messaggi-di-Errore-e-Generazione-Log.md` | `error_log` non è immutabile (scade a 90 giorni); senza canale la riga non nasce |
| `guide/messaggi-audit.md` | Tolto il consiglio di accendere `log_with_dblink` per l'audit (D60) |
| `guide/automazione-db.md` | §4.2 (azione FK, require differito, figli attivi, due eccezioni, nomi uguali per due FK — D10), §4.3 (seed overlap senza chiamanti), §4.6 (forma `<prefisso>_soggetto_ruolo_id`, il seed è una diagnosi), §5.4 (hash solo oltre 63 caratteri) |
| `guide/processi-pgagent-funzionali.md` | Chiusura per scadenza: sveglia oraria, `DOMINIO` su `CODA_AUTOMATICA`, audit, verbo e `fn_data_operativa()`, job e link |
| `guide/riclassificazione-vie.md` | Esiste `fn_admin_merge_stradario`, che oggi fallisce (D3) |
| `guide/pgtap-come-si-scrive-un-test.md` | Riga d'onere da `crea_ddt_da_ordine`, `conferma_reso` da `porta_a_stato`, «solo dal verbo» per tutte le testate, fattura a tre anelli, motivo dell'ordine obbligato |
| `dbzero/dbops/_fixture-pgtap.md` | Data, eccezione `pgtap-runner: owner`, link a guida e template |
| `dbzero/vendite/manual/contratti.md`, `dbzero/maintenance/manual/proc_automations_overlap_job.md` | Il chiamante della chiusura è il lavoro di coda; il seed overlap non gira |
| `dev/work-in-progress/sviluppo-multi-face-da-completare.md` | Nota: `zeroerp_batch_fatturazione` è ritirato |
| 19 file in `guide/`, `tutorial/`, `dev/` | 79 link da `/dbzero/{dbops,maintenance,script}/manual/` ripuntati alle schede; in `dev/manual/modello-componenti-bom.md` la riga di data ridotta alla data (la cronaca sta già in `changelog-decisioni-componenti.md`) |

Restano fuori, non richiesti: un link morto preesistente in `guide/gestione-ddt.md`
(`/dbzero/vendite/funzioni/fn_ddt_legami`); marcatori di revisione rimasti nelle guide toccate; i link
`/dbzero/*/manual/` dentro le pagine `manual/` degli **altri** schemi, che si ripuntano quando quegli
schemi vengono rivisti.

## 8. I giri, nell'ordine in cui si fanno

**Decisione di Tid (2026-11-06):** si fa tutto lo sviluppo DB di questo brief. L'ordine è per gravità (§2.0:
prima la A, poi la B, infine la C), e i lavori che toccano gli stessi oggetti vanno nello stesso giro, anche
se sono di classi diverse, così ogni oggetto si apre una volta sola. L'ordine l'ha scritto la sessione DB, su
delega di Tid. Ogni giro: changeSet, pgTAP del presidio, COMMENT e pagine `manual/` riallineati, poi apply e
via al giro dopo.

I numeri sono quelli dell'ordine. Rispetto al piano del 2026-11-05 i difetti sono gli stessi, ma sono raggruppati
in un altro modo: i giri vecchi 8 e 9 (pulizia) sono vuoti, perché ciò che restava è stato fatto nel giro C1 o
entra nel giro che apre lo stesso oggetto.

| Giro | Classe | Contenuto | Perché insieme, e perché a questo punto |
| --- | --- | --- | --- |
| 1 ✅ | A | D1 (+ D26), D14 + D15, D40, D41, D43, D54, D56 (+ D7) | Applicato e verde (§12) |
| 2 ✅ | A | **Le fusioni e la pipeline.** D3, D4, D45 (Q1); D60 con R6 e R7 (Q9: il ramo dblink di `fn_audit_log_once` esce, nasce il parametro della durata); D44 con Q14 ① | Le porte che falliscono appena le si usa vengono prima di tutto. D60 entra qui (prima era nel giro 7) perché le fusioni devono scrivere la durata nella colonna, e il parametro per farlo lo porta D60. ① è la stessa funzione di D44 |
| 3 ✅ | A | **I guard ATTIVO.** D46, D47, D49, D5, D51 (Q8, con il censimento delle fixture che chiudono i differiti), D18 — applicato e verde (§15) | Sono le stesse due o tre funzioni trigger (`trgfn_child_requires_active_parent`, `…_non_obsolete_parent`, `trgfn_prevent_deactivate_if_children`): prima erano divise fra i giri 2, 4, 6 e 7. Codice sbagliato e lettura sotto la RLS sbagliata sono errori che l'operatore vede. Alla fine del giro, una sola rigenerazione BE (BE6) per i codici dei giri 2 e 3; BE3 |
| 4 ✅ | A | **Riconoscimento e strumenti.** D6, D53 (Q9) — applicato e verde (§16). D21 (+ M18) nel blocco 4b: registro dei modi e risolutori generati, applicato e verde (§17) | D6 dà il riconoscimento del trigger dalla funzione (`tgfoid`): il giro 10 lo riusa, quindi viene prima |
| 5 ✅ | A | **La coda lavori sotto RLS.** Q14 ③, D9 — blocco 5a (§18): azienda del lavoro, policy inerte, porta DEFINER, D9; blocco 5b (§18.9): l'`ENABLE`, S-BE-2. Applicato e verde | Separare le aziende nel DB è un contratto deciso (Q14 ③). D9 (`fn_accoda_lavoro`) è la stessa tabella. Poi BE9 e la revisione del `perimetro` di `vw_coda_lavori_da_guardare` |
| 6 ✅ | A | **Presidi che guardano il campo sbagliato.** Q14 ④, ⑦ — chiuso (§19): applicato, pgTAP verdi, committato | Un presidio che non vede un caso che il modello ammette (il buco dei lotti congelati) dice il falso. Tutti e due riaprono il catalogo `presidi.csv` / `presidi_testi.csv`. ⑧ va nell'altro brief (§8.1) |
| 7 ✅ | A | **Promesse senza esecutore, ricerca dei lookup.** D35, D36, D37 (Q4), D57 — applicato e verde (§20) | Tutti riaprono l'ambito delle automazioni o un lettore che non vede tutto. BE4. D25 è passato al giro 10a (stessa funzione di D32) |
| 8 | A | **Le fixture.** D63, D64, D66 (Q11), D67, D70; + D69, D71, D73 (B) e D74 (C). D68 chiuso dall'altro cantiere (§21.1) | Fixture che producono una forma che l'applicazione non produce. Le B e la C usano gli stessi builder: un giro solo |
| 9 ✅ | B | **Il processo vivo, e correzioni locali.** D11 (Q2): il BB «processo vivo» con sveglia, accensione, guard, panorama, roster e le sette viste, fra cui Q14 ⑤; D38, D39 (Q5); D8, D12, D22, D24, D52; Q14 ⑨ | Il BB deve nascere **prima** del giro 10, che lo usa (⑬). D38 e D39 sono lo stesso motore. Gli altri sono correzioni locali, ognuna su un oggetto suo |
| 10 | B | **Il framework delle automazioni e la convergenza dei registri (Q3).** Quattro blocchi, ognuno provato prima del successivo, come il giro 1: | Le copie del framework e i registri che aggiungono e non tolgono. Le A di questo giro (D25, D30, D59) entrano qui perché aprono le stesse funzioni |
| 10a | | Lock di colonna: D25 (A), D28, D32, R2; BE2 | `fn_lock_columns_divergenze` si apre una volta |
| 10b | | Runner e registro delle regole: D2, D10, D13, D16, D17, D17-bis, D20, D27, R1 | La strategia d'esistenza, l'ambito, la scadenza, i nomi; il vocabolario del registro (D17-bis) con il registro |
| 10c | | DELETE_BLOCK, guard utility, overlap: D19, D33, D34, D30 (A), D59 (A), Q14 ⑪, ⑫, ⑬, R3 | Ogni apply si apre una volta. ⑬ usa il BB del giro 9 |
| 10d | | La politica degli indici delle FK: Q14 ②, D23; e il `fk_index_policy.csv` che nessuno carica, unica sede di decisioni `true` che da zero non nascono (§23.11) | `fk_index_policy` e il nome dell'indice di una sua riga |
| 11 | B | **Le etichette di prova.** Q14 ⑩ | La FK verso `django.auth_user` e il comportamento di `fn_elimina_credenziale` |
| 12 | B | **I presidi dei codici anche sulle funzioni SQL.** Q15 | Viene dopo i giri che portano codici nuovi (2, 3, 9), così le righe nuove che compaiono nei due presidi si leggono una volta sola. Un codice nuovo che emerge porta la rigenerazione BE |
| 13 | — | **Il livello «sessione» esce dagli override.** Q10 | Cambia il modello, ma non c'è un difetto attivo: oggi quel livello non lo scrive nessuno. Fuori dal perimetro `dbops`; BE8 |
| 14 | — | **I COMMENT rimasti, e il presidio di testo.** M1-M39, §3.2, §3.3 (Q13) | Ogni giro riscrive i COMMENT della famiglia che apre. Qui si fa ciò che resta, poi si accende il presidio su `obj_description`, che sarebbe rosso se lo si accendesse prima |

In ogni giro la documentazione si riscrive insieme al COMMENT: pagine `manual/`, guide e note dei presidi che
descrivono la regola cambiata (gli elenchi sono nelle decisioni di §4).

### 8.1 Le tre viste di magazzino: si fanno nel lotto M dell'altro brief

**Decisione di Tid (2026-11-06):** D58, D29 (+ M22) e Q14 ⑧ (+ M23) confluiscono nel lotto M di
[brief-db-sorgente-documento-e-riga](../work-done/brief-db-sorgente-documento-e-riga.md) (§7.2 «Lotto M»), che riscrive
comunque `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico` e `vw_magazzino_movimenti_senza_costo`:
le viste si aprono una volta sola, alla grana di prelievo e rientro. Qui resta solo questo rimando, e l'analisi
(fatto, correzione, presidio, documentazione) nelle loro sezioni, da cui il lotto M la legge. Prima del via al
lotto M si riverifica l'analisi: il promemoria sta in quel brief. I tre punti non tengono aperto questo brief:
se va in `work-done/` prima del lotto M, il blocco in testa li dichiara passati all'altro.

## 9. Alla chiusura

* Ogni difetto chiuso aggiorna la pagina `manual/` dell'oggetto, che oggi descrive il difetto.
* Il brief va in `work-done/` quando tutti i giri sono applicati e verdi, con le richieste BE ancora
  aperte dichiarate nel blocco in testa.

## 10. Giro C1 — la pulizia, 2026-11-04

**Decisioni di Tid (2026-11-04):** si parte dalla classe C. I ritiri si fanno solo per gli oggetti di cui
è certo che nessuno li usa: i quattro strumenti DBA di Q9 restano. `vw_run_senza_attore` si ritira (Q6).
D17-bis e D74 si rimandano.

### 10.1 Che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261104-09` | D48 | `automation_lock_columns.error_code` senza DEFAULT (era un codice ritirato); COMMENT di colonna |
| `20_code/dbops/20261104-10` | D61 | DROP di undici funzioni senza chiamanti: le cinque utility dei trigger, `fn_trigger_exists_cascade_by_args`, `fn_normalize_indirizzo`, `fn_migrate_add_indirizzo_normalizzato`, `fn_set_gucs_conn`, `fn_seed_automazione_overlap`, `fn_run_automations` |
| `20_code/dbops/20261104-11` | D42 | DROP di `dbops.vw_run_senza_attore` |
| `20_code/dbops/20261104-12` | D50 | `fn_run_automations_tx_id`: il dry run scrive `rule_type = TX_ID` e si firma col proprio nome (l'orchestratore che firmava è ritirato); COMMENT riscritto |
| `20_code/dbops/20261104-13` | D55 | `vw_function_list`: `num_args` da `pronargs`, `comment` da `obj_description` |
| `20_code/dbops/20261104-14` | D62 | `fn_pgtap_piva_libera()` delega a `fn_pgtap_piva_libera(0)`; COMMENT corretto (M36) |
| `20_code/dbops/20261104-15` | D65 | `fn_pgtap_crea_mondo_cliente` verifica il legame con `fn_pgtap_cliente_ba_del_mondo`; COMMENT dei due (M36) |
| `20_code/dbops/20261104-16` | D72 | `fn_pgtap_crea_preventivo_con_righe` sceglie la natura con `script.fn_natura_e_merce`; COMMENT riscritto |
| `80_data/changelog/20261104-17` | D42 | DELETE delle righe di `vw_run_senza_attore` da `dbops.presidi_testi` e `dbops.presidi`, già tolte dai due CSV (i mirror non cancellano) |
| `90_end/20261104-18` | D61 | DROP di `fn_audit_begin`, `fn_audit_end`: in `90_end` perché il REVOKE di `20260911-09` le pretende con una preCondition HALT |
| `00_schema/dbops/20261104-19` | D61 | `chk_audit_status` senza `START`: lo scriveva solo `fn_audit_begin`, e una corsa «aperta» non è più uno stato del modello. Senza, il presidio C1 è rosso (`dbops/test-stati-check-scrittori-v1` test 2, `audit_log.status = START` NON_DICHIARATO: visto da Tid dopo l'apply). Nessun lettore del valore; zero righe `START` su dbdev; una riga `START` farebbe fallire l'`ADD CONSTRAINT`, e va bene così |

pgTAP riallineati: `dbops/test-registri-append-only-postura-v1.sql` (plan 22: i test 14-15 provano che le
due porte non esistono più, i 22-23 escono) e `maintenance/test-job-run-attore.sql` (plan 11: esce il test
della vista).

**Il censimento dei ritiri** (prima di scrivere i DROP): nessun chiamante nel repository (tutti gli alberi
dei changelog, pgTAP, backend, frontend, scripts) fuori dai changeSet che li creano; sul database di
sviluppo nessun riferimento nei corpi delle funzioni (comprese le `BEGIN ATOMIC`), nelle viste, negli step
pgAgent, nei trigger. Tutte di `zeroerp_owner`, `INVOKER`. Chi li nomina ancora come testo, e regge
l'assenza: la lista dei grant di `ci_apply/20260205-41` (scorre solo le funzioni che esistono),
l'elenco delle porte di `vw_audit_log_scrittori_fuori_perimetro`, un filtro di
`scripts/sql/provision_zeroerp.sql`, il GRANT di `90_end/20260904-20` (protetto da `to_regclass`).

### 10.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* L'estratto dei dieci changeSet gira intero (`ON_ERROR_STOP`); `fn_fix_triggers_event_tokens` sullo scratch
  non esiste e l'`IF EXISTS` la salta, come previsto.
* Quindici pgTAP senza e con l'estratto in testa: nessun rosso nuovo. `test-catalogo-presidi-v1` (test 3,
  ogni riga punta a una vista viva) e `test-presidi-testi-v1` verdi senza la vista; `test-lock-columns-convergenza`,
  le fixture del mondo e del preventivo, `test-riferimenti-morti-v1`, `test-audit-log-perimetro-scrittori-v1`
  verdi. Da owner restano rossi per costruzione i test 16-19 della postura (UPDATE/DELETE sul registro:
  da owner riescono) e un rosso preesistente di `test-soggetti-titoli-iva-tipo-soggetto-v1`, uguali senza e con.
* D50 su un caso costruito (tabella di `vendite` con `tx_id` e senza trigger): la riga DRYRUN è
  `dbops.fn_run_automations_tx_id` / `TX_ID`. D55: `num_args` 0 e 1 sulle due firme di
  `fn_pgtap_piva_libera`, nessuna riga doppia. D62: le due firme danno la stessa partita IVA.
  `plpgsql_check` pulito sulle quattro funzioni riscritte.
* Lo scratch dopo le prove è intatto (impronta delle funzioni di `dbops`, righe di `dbops.presidi`, vista,
  default della colonna).

* `20261104-19`, provato dopo l'apply del C1 sullo scratch: `dbops/test-stati-check-scrittori-v1` passa da
  14/15 a 15/15; `test-chiusura-scadenze-audit-v1`, `test-storico-salto-trigger-presente-v1` e la postura
  invariati senza e con.

**✅ Applicato da Tid il 2026-11-04** su dbdev e sullo scratch, `20261104-09` … `-19`. Verdi come app
`dbops/test-registri-append-only-postura-v1.sql`, `maintenance/test-job-run-attore.sql`,
`dbops/test-catalogo-presidi-v1.sql`, `dbops/test-presidi-testi-v1.sql`; verde da owner
`dbops/test-stati-check-scrittori-v1.sql` (era rosso al test 2 dopo il `-18`, chiuso dal `-19`).

### 10.3 Doc

Cancellate le pagine `manual/` dei quattordici oggetti ritirati; riallineate le pagine che li nominavano e
quelle degli oggetti cambiati (§7.1 resta per la revisione).

### 10.4 Residuo della classe C

| # | Che cosa | Perché resta |
| --- | --- | --- |
| R1 | I dry run di `fn_run_automations_lock_columns`, `_audit_update`, `_date_validita` firmano ancora `dbops.fn_run_automations`, ritirata | Tre funzioni grandi: si chiude quando ciascuna si riapre (giro 10b) |
| R2 | Il `COALESCE` morto in `fn_lock_columns_divergenze` | Con D32 (giro 10a) |
| R3 | I nomi `fn_audit_begin`/`fn_audit_end` nella lista di `ci_apply/20260205-41`. ✅ Dalle porte di `vw_audit_log_scrittori_fuori_perimetro` li toglie il `20261104-21` (giro 1a) | Testo senza effetto; si toglie quando `ci_apply/20260205-41` si riapre (giro 10c, che riscrive le chiamate di `ci_apply` per la ⑬) |
| R4 | D17-bis, D74 | Rimandati da Tid nel C1; ora nei giri 10b e 8 (§8) |
| R5 | I quattro strumenti DBA (`fn_find_file_usage`, `fn_foreign_keys_info`, `fn_get_child_fk_col`, `fn_list_indices`) | Restano (Q9, decisa il 2026-11-05); i due di D53 si riparano nel giro 4 |
| R6 | `dbops.audit_log.duration_ms` non la scrive più nessuno: la scriveva solo `fn_audit_end`, e `fn_audit_log_once` non ha un parametro per la durata. ⚠️ Corretto il 2026-11-05: su dbdev nessuna riga porta la durata, né in colonna né in `result`/`params`; solo le due fusioni della Q1 (che oggi falliscono) la mettono nei `params`. ✅ La metà su `START` è chiusa da `00_schema/dbops/20261104-19` (vedi §10.1) | **✅ Deciso (Tid, 2026-11-05): parametro della durata in `fn_audit_log_once`** (in coda, facoltativo, `dbops.audit_log.duration_ms%TYPE`), nello stesso changeSet del ritiro del ramo dblink; la durata ha una sede sola, la colonna (le fusioni della Q1 smettono di metterla nei `params`); la misurano **tutte** le automazioni che scrivono un riepilogo di fine giro, ciascuna quando si riapre nel suo giro |
| R7 | `docs/it/postgresql/dblink.md` dice ancora che `fn_audit_log_once` scrive fuori transazione con `myapp.log_with_dblink = on`: oggi quel ramo non scrive (D60) | ✅ Corretto nel giro 2 (§14.5) |
| R8 | ✅ `dbops/manual/fn_run_automations_codice_maiuscolo.md` (cantiere parallelo) diceva «non è una parte di `dbops.fn_run_automations`, che non ha chiamanti» | Corretto dal suo cantiere il 2026-11-04, con il commento di testata di `20_code/dbops/20261104-04` |

## 11. Il cantiere parallelo CODICE_MAIUSCOLO (2026-11-04, applicato)

Nota per i giri 1 e 10, non un difetto. Il cantiere CODICE_MAIUSCOLO (`20261104-01` … `-08`, nessun
brief: il perché sta nelle intestazioni e nelle pagine `manual/`) ha aggiunto un runner nuovo,
`dbops.fn_run_automations_codice_maiuscolo`, applicato da Tid su dbdev con i pgTAP verdi. È nato già
allineato ai difetti che qui si segnalano sugli altri runner, e può servire da forma quando si riaprono:

| Difetto | Come lo evita |
| --- | --- |
| D17 | Il trigger vivo si riconosce dalla funzione (`tgfoid`); la `existence_strategy` della regola non si legge |
| D32-D34 | Stato atteso e vivo in una funzione sola, `dbops.fn_codice_maiuscolo_perimetro`, che converge nei due sensi (`CREA`, `RIGENERA`, `TOGLIE`); la convergenza in `90_end` (`20261104-08`, `runAlways`) ferma il migrate se resta un'azione |
| D41 | Audit `OK` anche nel giro vero, `DRYRUN` nel dry run, `WARN NO_RULE` quando manca la regola |
| R1 | Il dry run si firma col proprio nome |
| D61 | Nessun aggancio all'orchestratore ritirato: la chiamano la convergenza e `maintenance.proc_automations_lock_columns_job` (`20261104-05`) |

⚠️ `20261104-05` ha riscritto `proc_automations_lock_columns_job`: chi la riapre parte da quel corpo.

## 12. Giro 1 — i giornali e i presidi che dicono il falso, 2026-11-04

**Decisione di Tid (2026-11-04):** si parte dal giro 1, che non aspetta nessuna domanda di §4. Si fa per
blocchi, ognuno scritto e provato prima del successivo: **1a** il building block del corpo (D14 + D15) con
i suoi lettori e gli strumenti (D54, D56); **1b** il canale dblink (D1 + D26); **1c** i runner cleanup e
delete_block (D40, D41); **1d** le viste puntuali (D43, D7).

### 12.1 Blocco 1a — che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `20_code/dbops/20261104-20` | D14, D15 | Il building block: `dbops.fn_testo_senza_commenti(text)` (toglie `--` e `/* */`, lascia intatti `'…'`, `E'…'`, `"…"`) e `dbops.fn_corpo_funzione(pg_proc.oid%TYPE)` (il corpo da `prosrc`, o da `pg_get_function_sqlbody` per una `BEGIN ATOMIC`, con `search_path = pg_catalog` perché esca qualificato) |
| `-21` | D14, D15, R3 | `vw_audit_log_scrittori_fuori_perimetro`: corpo dal BB; la porta è la sola `fn_audit_log_once` |
| `-22` | D14 | `vw_bersagli_non_dichiarati` |
| `-23` | D14 | `vw_codici_errore_da_dichiarare` |
| `-24` | D14 | `vw_punti_primo_motivo`: il marcatore gira anche sul corpo senza commenti; il prefiltro su `prosrc` resta davanti |
| `-25` | D14 | `vw_magazzino_dipendenze_inverse`, lente CORPO |
| `-26` | D14 | `vw_funzioni_check_codici`: i tre corpi e `emette_valori` (che leggeva `prosrc` commenti compresi); prefiltro del JIT invariato |
| `-27` | D14 | `vw_punti_canale_campo` |
| `-28` | D14, D15 | `vw_stati_check_scrittori`: vede gli scrittori `BEGIN ATOMIC` |
| `-29` | D56, D14 | `vw_codici_errore_forme_condizione`: ogni codice distinto di una riga è un punto; righe tagliate dal corpo senza commenti |
| `-30` | D15, M33 | `fn_find_function_usage`: corpo dal BB; firma ancorata (`pg_proc.proname%TYPE`, `pg_namespace.nspname%TYPE`), quindi DROP + CREATE; COMMENT riscritto |
| `-31` | D54, D15, §3.2 | `fn_search_column_usage`: i vincoli da `pg_get_constraintdef`; corpo dal BB; firma ancorata (`pg_attribute.attname%TYPE`), DROP + CREATE; COMMENT nuovo |

**Le scelte che non si vedono dal titolo:**

* **La regex del BB** è un'alternativa sola: il primo carattere decide se comincia un letterale (rimesso
  con `\1`) o un commento (tolto). ⚠️ In PostgreSQL un'alternativa al primo livello è sempre greedy: un
  `/\*.*?\*/` lì dentro si mangerebbe tutto fino all'ultimo `*/`. Il commento a blocco è scritto in
  modo da non poter contenere `*/`. Limiti dichiarati nel COMMENT: niente dollar-quoting interno, niente
  commenti annidati.
* **La collation.** `prosrc` ha la collation del catalogo (`"C"`), il risultato del BB quella di default:
  il primo apply sullo scratch è fallito su `vw_bersagli_non_dichiarati` (`CREATE OR REPLACE VIEW`
  rifiuta il cambio di collation di una colonna). Nelle viste il corpo si legge
  `dbops.fn_corpo_funzione(p.oid) COLLATE "C"`: colonne, `\w` e `~*` restano quelli di prima. La regola
  è nel COMMENT del BB.
* **I prefiltri su `prosrc` restano** dove c'erano (`vw_funzioni_check_codici`, `vw_bersagli_non_dichiarati`)
  e uno si aggiunge (`vw_punti_primo_motivo`): sono sovrainsiemi economici, e tengono la stima sotto il
  JIT (`test-vw-funzioni-check-codici-sotto-jit-v1` verde, invariato).
* **Il perimetro delle viste non cambia.** Quelle limitate al plpgsql restano limitate; solo
  `vw_audit_log_scrittori_fuori_perimetro` e `vw_stati_check_scrittori`, che già guardavano anche le
  funzioni SQL, ora le vedono davvero. ⚠️ Se `vw_codici_errore_da_dichiarare` e
  `vw_punti_canale_campo` debbano guardare anche le funzioni SQL (una `LANGUAGE sql` può chiamare
  `fn_log_and_raise_error`) è una domanda nuova: **Q15** per Tid.
* **`%TYPE`.** `fn_corpo_funzione` è ancorata a `pg_proc` (parametro e risultato); i due strumenti al
  catalogo (`name`). Il cambio da `text` a `name` cambia l'identità: DROP + CREATE, possibile perché non
  hanno chiamanti (censimento del giro C1). `fn_testo_senza_commenti` resta `text`/`text`, con la ragione
  accanto.

### 12.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto, `BEGIN … ROLLBACK`)

* **Base uguale al vivo**: lo YAML di partenza di ognuna delle nove viste, eseguito, lascia definizione,
  COMMENT e opzioni identici al vivo. `vw_stati_check_scrittori` non è `security_invoker`, né nel vivo né
  nella base: il `-28` lo lascia così.
* **L'estratto dei dodici changeSet gira intero.** Firme: una per nome;
  `fn_find_function_usage(name)` e `fn_search_column_usage(name)` restituiscono
  `TABLE(object_type text, schema_name name, object_name text)`.
* **Fatto datato, non motivo:** al 2026-11-04 le nove viste danno, sul codice vivo, le stesse righe di
  prima, identiche nei due versi (775, 716, 734, 1836, 22, 107 righe; tre vuote). Quindi la baseline B-7
  (`db/baseline-codici-errore-famiglie.tsv`) non si muove. La correzione si prova solo **costruendo i
  casi**, e i casi sono nei pgTAP.
* **pgTAP senza e con l'estratto:**
  * nuovo `dbops/test-corpo-funzione-senza-commenti-v1.sql` (15): con, 15/15;
  * `dbops/test-stati-check-scrittori-v1.sql` (15 → 17): senza, rossi il 14, il 16 e il 17, perché la
    vista vecchia non vede lo scrittore `BEGIN ATOMIC` né il valore dopo il `'--'`; con, 17/17;
  * `dbops/test-audit-log-perimetro-scrittori-v1.sql` (6 → 8): con, 8/8;
  * `dbops/test-vw-codici-errore-motivo-nominato.sql` (8 → 10): senza, rossi il 9 e il 10; con, 10/10;
  * invariati senza e con: `test-vw-codici-errore-valore-atteso`, `test-vw-funzioni-check-codici-sotto-jit-v1`,
    `test-punti-canale-campo-v1`, `test-vw-bersagli-non-dichiarati`,
    `config/test-costanti-catalogo-citate-dal-codice-v1`, `pagamenti/test-righe-contabili-eliminazione-v1`,
    `magazzino/test-registro-non-nomina-i-consumatori-v1`, `script/test-rubinetto-primo-motivo-v1`,
    `script/test-catalogo-messaggi-errore-completo`, `test-catalogo-presidi-v1`, `test-riferimenti-morti-v1`,
    `test-registri-append-only-postura-v1` (da owner restano rossi i 16-19, uguali senza e con).
* **Guardrail** dei changelog e dei pgTAP verdi; header di licenza a posto.

### 12.3 Per Tid

Apply su dbdev (`cd db && ../scripts/liquibase5.sh update`) e sullo scratch (`scripts/ci-local.sh --ci-apply`).
Poi **come app** (sullo scratch la prova come app nella stessa transazione della DDL non si può fare):
`dbops/test-corpo-funzione-senza-commenti-v1.sql`, `dbops/test-audit-log-perimetro-scrittori-v1.sql`,
`dbops/test-vw-codici-errore-motivo-nominato.sql`, `dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql`;
da owner `dbops/test-stati-check-scrittori-v1.sql`. Il controllo B-7 (`scripts/codici-errore-baseline.sh`)
deve restare verde senza `--update`.

### 12.4 Doc

Pagine `manual/` dei dodici oggetti riallineate (il difetto descritto diventa il comportamento), due
pagine nuove per il building block.

### 12.5 Prossimi blocchi

| Blocco | Difetti | Stato |
| --- | --- | --- |
| 1b | D1 (un canale di log irraggiungibile blocca ogni scrittura tracciata), D26 (l'interruttore `myapp.log_with_dblink` letto in quattro modi) | ⭐ Decisione di Tid (2026-11-04): un default solo, **assente = acceso** (il canale c'è se c'è una stringa e l'interruttore non è `off`), come `fn_ensure_logconn`, il `makefile` e la CI. `fn_audit_log_once` restava fuori finché Q9 non decideva il suo ramo dblink (D60): deciso, si ritira nel giro 2. ✅ Scritto e provato: §12.8 |
| 1c | D40 (`fn_run_automations_cleanup`: un rifiuto non ferma il giro e non si vede), D41 (`fn_run_automations_delete_block` senza audit nel giro vero) | ✅ Scritto e provato: §12.9 |
| 1d | D43 (`vw_processi_che_bypassano` col ruolo ritirato), D7 (`vw_riferimenti_morti_rientrati` con la misura fallita) | ✅ Scritto e provato: §12.10 |

### 12.6 Dopo l'apply: un test lento, e la stima che lo spiegava

**Il fatto (Tid, 2026-11-04):** applicato il blocco 1a e verdi i test, `dbops/test-vw-codici-errore-motivo-nominato`
era lento. Misura sullo scratch:

* una lettura di `vw_codici_errore_forme_condizione` era passata da ~730 ms a ~1.170 ms, e ~300 ms erano
  **compilazione JIT**. La causa è la stima, non il lavoro: il `-29` portava i codici di una riga in un
  array e lo espandeva con `unnest`, che dichiara 10 righe (vere: 0,15). Il costo stimato saliva da
  ~297.000 a ~789.000, sopra `jit_optimize_above_cost` (500.000): oltre quella soglia PostgreSQL
  inlinea e ottimizza a ogni lettura. È la trappola per cui esiste `dbops.fn_regexp_occorrenze`,
  rimessa da me con un'altra funzione;
* il test legge la vista dieci volte, e il gemello `test-vw-codici-errore-valore-atteso` sette.

**La cura, in due pezzi:**

| Dove | Che cosa | Effetto (scratch) |
| --- | --- | --- |
| `20_code/dbops/20261104-43` | le occorrenze si estraggono in `classificato` con `fn_regexp_occorrenze` (ROWS 1), solo sulle righe con un codice; `n_punti` conta le coppie distinte (riga, codice) | stima ~289.000, JIT 16 ms, una lettura ~760 ms; output identico al `-29` nei due versi |
| i due pgTAP | la vista si fotografa una volta, in una tabella temporanea, dopo i testimoni; le asserzioni leggono la fotografia | `motivo-nominato` da 10,2 s a 1,2 s (10/10), `valore-atteso` da 7,3 s a 0,9 s (7/7) |

⚠️ La lezione vale per ogni vista dei presidi: un'espansione dentro la vista si scrive con una funzione
che dichiara la cardinalità vera, e la prova di un cambio guarda anche il piano (`EXPLAIN ANALYZE`, la
riga `JIT`), non solo le righe. Il presidio sotto JIT esiste solo per `vw_funzioni_check_codici` e i suoi
due lettori: per questa vista no, e la regressione l'ha vista Tid a occhio.

### 12.7 Il secondo test lento: il building block su ogni funzione

**Il fatto (Tid, 2026-11-04):** lento anche `dbops/test-audit-log-perimetro-scrittori-v1`. Qui il JIT non
c'entra: il `-21` chiede a `fn_corpo_funzione` il corpo senza commenti di **ogni** funzione del database
(sullo scratch 3.656), a ogni lettura, per poi tenere quelle che nominano il registro. Una lettura costava
~465 ms, e il test legge la vista sei volte.

| Dove | Che cosa | Effetto (scratch) |
| --- | --- | --- |
| `20_code/dbops/20261104-45` | in `sorgenti`, prima del building block, `prosqlbody IS NOT NULL OR prosrc ILIKE '%audit\_log%'` | una lettura ~105 ms; il test da 2,4 s a 0,65 s, 8/8 |

⭐ Il prefiltro è un **sovrainsieme esatto**, non una stima: togliere i commenti può solo levare testo, e
le due regex della vista contengono entrambe `audit_log`. Le `BEGIN ATOMIC` passano tutte, perché il loro
`prosrc` è vuoto. Verificato sullo scratch senza il filtro di perimetro: 20 scrittori in tutto il
database, nessuno perso. Il prefiltro su `prosrc` con `LIKE` è ammesso dal test 11 di
`test-corpo-funzione-senza-commenti-v1`, perché non è una lettura del corpo.

Fatto datato, stesso giorno: le altre viste del blocco 1a leggono fra 28 e 640 ms, e i loro test durano al
più 1,7 s. `vw_punti_canale_campo` e `vw_stati_check_scrittori` cercano valori diversi per ogni riga e
non hanno un prefiltro unico: restano come sono.

⚠️ La lezione si aggiunge a quella di §12.6: una vista che cerca un nome fisso nei corpi filtra sul testo
grezzo **prima** di chiedere il corpo senza commenti.

### 12.8 Blocco 1b — il canale di log: una regola sola, e mai un errore (D1 + D26)

⭐ **La regola** (decisione di Tid, 2026-11-04): il canale è acceso se c'è una stringa di connessione non
vuota **e** `myapp.log_with_dblink` non vale `off` (maiuscole e spazi non contano). L'interruttore assente
vale acceso. La stringa è `myapp.logconn` se valorizzata, altrimenti `myapp.dblink_log_connection`: è la
precedenza già scritta in `guide/configurazione-e-gestione-parametri.md`, che prima rispettavano solo due
lettori su quattro.

Le letture erano **cinque**, non quattro. Rileggendo il corpo, `fn_ensure_logconn` confrontava con `'on'`:
l'interruttore **assente** (NULL) valeva acceso, quello **vuoto** (`''`, cioè una GUC impostata e poi
azzerata in sessione) valeva spento. Il building block li tratta allo stesso modo: acceso. La prima stesura
del pgTAP costruiva l'assente con `''`, e con le funzioni vecchie il D1 non si vedeva.

#### 12.8.1 Che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `20_code/script/20261104-46` | D26 | Nuovo `script.fn_canale_log_stringa()`: la stringa del canale se è acceso, NULL se è spento o non configurato. Restituisce la stringa e non un booleano perché chi chiede «è acceso?» la usa subito dopo: due letture separate tornerebbero a divergere. SQL, `STABLE`, INVOKER, del migratore |
| `20_code/script/20261104-47` | D1, D26 | `fn_ensure_logconn`: il canale dal building block; **ogni** errore di connessione diventa un WARNING (prima solo `duplicate_object` e `53300`); COMMENT riscritto (nominava una GUC inesistente, `dblink.log_connection`); search_path nella forma di casa, stessa semantica |
| `20_code/dbops/20261104-48` | D26, D1 | `fn_get_or_create_session_tx_id`: il canale si chiede **prima** di aprire qualunque cosa. Prima, con `off` e la stringa impostata, `fn_ensure_logconn` taceva ma il passo dopo generava l'id con una connessione nuova. COMMENT riscritto per intero (era una revisione datata davanti al testo vecchio, §3.3) |
| `20_code/script/20261104-49` | D26 | `fn_log_error_only`: la stringa dal building block; con `off` un WARNING e nessuna scrittura (prima ignorava l'interruttore). Firma, DECLARE e COMMENT con `%TYPE` |
| `20_code/maintenance/20261104-50` | D26 | `fn_job_run_log_failure`: come sopra; firma e COMMENT con `%TYPE` |

Tutte e quattro le funzioni sono di postgres: la proprietà si prende in prestito, si verifica con
`$guard$` e si restituisce, nella forma di `20261103-05`. Con `%TYPE` i tipi risolti sono quelli di oggi:
le firme non cambiano, e il test 6 di `test-job-run-sqlstate-e-codice-v1` (firma testuale di
`fn_job_run_log_failure`) resta verde. `fn_audit_log_once` resta fuori finché non si decide Q9: legge
ancora «assente = spento», e il pgTAP la esclude per nome.

⚠️ **Effetto voluto, da sapere.** Con l'interruttore a `off` (la migrazione col `makefile` e in CI) le
scritture tracciate prendono la sentinella `uuid_nil` come `tx_id` invece di un id registrato, e i due
verbali fuori transazione non scrivono. `trgfn_tx_id_managed` accetta la sentinella, e nessuna FK punta a
`dbops.transaction_ids`. È ciò che `off` ha sempre promesso.

#### 12.8.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto, `BEGIN … ROLLBACK`)

* **Definizioni prima e dopo, a confronto:** cambiano solo le righe previste; una firma per nome; le
  quattro funzioni tornano di postgres con gli stessi permessi.
* **pgTAP nuovo `db/pgtap/script/test-canale-log-v1.sql` (16 test).** Sullo scratch il canale non c'è:
  per i test 13-15 la sessione di prova ha avuto una stringa verso lo scratch stesso (`PGOPTIONS`), così
  non si saltano.

  | Versione | Esito |
  | --- | --- |
  | `-46` … `-50` | 16/16 |
  | solo `-46` (i lettori vecchi) | rossi 7 e 8 (`could not establish connection`: il D1), poi la transazione si interrompe |
  | solo `-46`, senza la sezione D1 | rossi 13, 14 (`have: 1`), 15 (`have: 1`) e 16: il D26 |

  Il giro rosso ha lasciato sullo scratch una riga in `dbops.error_log` e una in `maintenance.job_run_log`
  (`pgtap.canale_log.spento`): è la prova che prima si scriveva con `off`.
* **Undici pgTAP che toccano queste funzioni**, senza e con: invariati.
  `test-registri-append-only-postura-v1` ha 4 rossi (16-19) **identici** nei due versi: vengono dal
  runner owner, che ha UPDATE e DELETE sui registri; il test li vuole come app.
* Guardrail pre-commit verdi.

#### 12.8.3 Per Tid — ✅ 1 e 2 fatti (Tid, 2026-11-04: migrazione applicata, test verdi)

1. Apply su dbdev e sullo scratch di `20261104-46` … `-50`.
2. pgTAP:
   * `script/test-canale-log-v1` (nuovo; su dbdev il canale c'è, quindi i test 13-15 girano: il gemello
     del 13 registra un `tx_id` che sopravvive al ROLLBACK, come lo scenario D di
     `test-tx-id-coerenza-non-registrato`);
   * `dbops/test-tx-id-coerenza-non-registrato`, `dbops/test-registri-append-only-postura-v1`,
     `dbops/test-security-definer-search-path-v1`, `maintenance/test-job-run-log-failure-out-of-tx`,
     `maintenance/test-job-run-sqlstate-e-codice-v1`, `script/test-bersaglio-canale-strutturato`.
3. Commit.

#### 12.8.4 Doc

* Nuova `script/manual/fn_canale_log_stringa.md`.
* Pagine `manual/` delle quattro funzioni: `fn_ensure_logconn` riscritta per intero (nominava
  `dblink.log_connection`, che non esiste); `fn_log_error_only` col flusso nel suo ordine vero;
  `fn_get_or_create_session_tx_id` senza i due avvisi diventati falsi; `fn_job_run_log_failure`.
  Ritoccate anche `fn_audit_log_once` (è l'unica fuori dalla regola) e `fn_log_and_raise_error` (diceva
  che `fn_log_error_only` scrive solo su `logconn`).
* Guide: `configurazione-e-gestione-parametri`, `messaggi-audit`, `tx_id_implementation_guide` (anche il
  diagramma, che mostrava ancora l'`uuidv7` locale ritirato il 2026-07-22), `automazione-db`,
  `Messaggi-di-Errore-e-Generazione-Log`; `postgresql/parametri-personalizzati-(GUC)` e `postgresql/dblink`.
* I link a `/dbzero/script/funzioni/fn_canale_log_stringa` puntano alla pagina generata, che nasce con la
  rigenerazione dopo l'apply. `script/index.md` riprende lo «Scopo» delle pagine `manual/` e si riallinea
  da sola.

### 12.9 Blocco 1c — il cleanup e il delete_block dicono che cosa è successo (D40 + D41)

#### 12.9.1 Che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `20_code/dbops/20261104-51` | D40 | `fn_run_automations_cleanup` restituisce un riepilogo jsonb invece di `void`, nella forma di `maintenance.fn_apply_storicizza_defaults` (20261103-67): `_applicate`, `_saltate`, `_saltate_motivi`, `_falliti` (i `BLOCKED_BY_TABLE`), `_righe`, `_dettaglio` (i rifiuti, con tabella, regola, SQLSTATE e messaggio). Il job la chiama già con una SELECT: `fn_run_and_log` legge l'esito, e `_falliti > 0` rende la corsa rossa con `E_JOB_ESITO_CON_SCARTI`. Il wrapper non cambia; le righe di audit sono le stesse. `void` → `jsonb` vuole DROP e CREATE; firma e DECLARE con `%TYPE` |
| `20_code/dbops/20261104-52` | D41 | `fn_run_automations_delete_block`: nel giro vero una riga `OK` (`CREATE_TRIGGER`) per ogni trigger montato; `WARN TABLE_NOT_FOUND` in tutti e due i giri (in simulazione era `DRYRUN`, come un'azione che sarebbe avvenuta); il nome del trigger tratta `''` come assente, come `fn_apply_delete_block_trigger`. Il gestore dei guasti d'ambiente è quello di 20261016-52, riga per riga. Firma con `%TYPE` |

⚠️ **Il dettaglio porta solo i rifiuti, e i salti si contano.** La prima stesura elencava anche i salti
dichiarati: la prova sul giro vero dello scratch (fatto datato, 2026-11-04) ne ha trovati 924, tutti
`NO_CLEANUP_COLUMN`. Una regola `*ALL` ne fa uno per ogni tabella senza la colonna, per costruzione, e
quell'elenco sarebbe finito a ogni corsa in `meta.esito`. Ora i salti stanno in `_saltate_motivi`
(`{"NO_CLEANUP_COLUMN": 924}`), e il riepilogo di quel giro pesa 130 byte.

La riga di `automation_delete_block` fuori ambito, ignorata senza traccia, non si corregge qui: è annotata
in `framework-automazione-db-migliorie` §2.4, come chiedeva la riga di D41.

#### 12.9.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto, `BEGIN … ROLLBACK`)

| Prova | Senza | Con |
| --- | --- | --- |
| `dbops/test-cleanup-framework` (plan da 16 a 19) | rossi 13, 15, 16 (un `void` non si fotografa: il test 13 ora cattura il riepilogo) | 19/19 |
| `dbops/test-delete-block-audit-v1` (nuovo, 7 test) | rossi 2, 5, 6 | 7/7 |
| `maintenance/test-cleanup-job-ambito-registro-v1`, `dbops/test-automazioni-guasto-ambiente-rilanciato-v1`, `maintenance/test-fn-run-and-log-lock-ed-esito-v1`, `maintenance/test-apply-storicizza-esito-v1`, `dbops/test-corpo-funzione-senza-commenti-v1`, `dbops/test-security-definer-search-path-v1` | verdi | verdi, uguali |

* **Da capo a fondo:** una tabella con un guard sul DELETE e una regola `CLEANUP_PURGE`, poi
  `CALL maintenance.proc_automations_cleanup_job()`: la corsa del giornale è `ok = false`,
  `E_JOB_ESITO_CON_SCARTI`, «riuscita con scarti: 2 falliti».
* **Il giro vero di oggi sullo scratch:** `_falliti = 0` (39 regole applicate, 924 salti): l'apply non
  rende rossa nessuna corsa da subito.
* Il DROP e CREATE non perde il permesso: EXECUTE all'app torna dai default privileges (test 19).
* Guardrail pre-commit verdi.

#### 12.9.3 Per Tid — ✅ 1 e 2 fatti (Tid, 2026-11-04: migrazione applicata, test verdi)

1. Apply su dbdev e sullo scratch di `20261104-51` e `-52`.
2. pgTAP (`test-cleanup-framework` e il nuovo `test-delete-block-audit-v1` dichiarano il runner owner):
   `dbops/test-cleanup-framework`,
   `dbops/test-delete-block-audit-v1`, `maintenance/test-cleanup-job-ambito-registro-v1`,
   `dbops/test-automazioni-guasto-ambiente-rilanciato-v1`.
3. ⚠️ Da sapere: da qui la prossima corsa di `automations_cleanup` con una tabella che rifiuta compare in
   `vw_job_run_da_guardare`. È il comportamento voluto; nessun lavoro per il BE.
4. Commit.

#### 12.9.4 Doc

`dbops/manual/fn_run_automations_cleanup.md` (nuova sezione sul riepilogo, test, nota),
`dbops/manual/fn_run_automations_delete_block.md` (che cosa scrive in audit, test nuovo, nota),
`dbops/manual/automation_delete_block.md`, `maintenance/manual/proc_automations_cleanup_job.md` (la
sezione «una corsa verde può nascondere…» ora dice il contrario), `guide/automazione-db.md` (una
frase); `framework-automazione-db-migliorie` §2.4.

### 12.10 Blocco 1d — due presidi che dicevano il falso (D43 + D7)

#### 12.10.1 Che cosa è stato scritto

| Dove | Difetto | Che cosa |
| --- | --- | --- |
| `20_code/dbops/20261104-53` | D43 | `vw_processi_che_bypassano` senza il debito dichiarato per nome: il debito era uno, `zeroerp_batch_fatturazione`, ritirato il 2026-10-15. Con lui spariscono la colonna `stato`, che senza debito varrebbe sempre `NON_DICHIARATO`, e la `nota` fissa. Resta `ruolo`, e la vista deve restare **vuota**. DROP e CREATE (colonne tolte; nessun dipendente; SELECT all'app dai default privileges); `security_invoker` |
| `80_data/sql/dbops/presidi.csv` | D43 | La riga del presidio perde `colonna_stato`/`stato_atteso` (si contano tutte le righe, soglia ZERO) e la nota si riscrive. I due mirror sono `runOnChange` |
| `20_code/dbops/20261104-54` | D7 | `vw_riferimenti_morti_rientrati`: una voce la cui funzione esce `NON_MISURATO` non è «rientrata». Il rosso della misura mancata sta in `vw_riferimenti_morti_da_sanare` e nel guardrail CI. La misura si legge una volta (CTE `MATERIALIZED`). Colonne invariate |
| `db/pgtap/dbops/test-processi-registro.sql` | D43 | Test 13: la vista è vuota, senza filtro di stato. Nuovo 13-bis (plan 16): la definizione non contiene letterali (un nome scritto lì diventa un'eccezione che sopravvive al ruolo) e il presidio non ha filtro di stato. È un presidio sul testo, dichiarato: un ruolo con BYPASSRLS non si crea in un test |
| `db/pgtap/dbops/test-riferimenti-morti-v1.sql` | D7 | Test 9-11 (plan 12): la vista viva su una misura **costruita**. Il suo testo, con la chiamata alla misura sostituita da una funzione in `pg_temp`; la 9 prova che la sostituzione avviene |
| `scripts/ritira_ruoli_dismessi.sh` | D43 | Leggeva `ruolo \|\| ' ' \|\| stato`: ora `ruolo` |

⚠️ **Il presidio del D7 non è quello che il brief chiedeva**, cioè una funzione costruita perché
`plpgsql_check` sollevi. Sullo scratch (2026-11-04) ho provato un errore di sintassi, un `1/0`, una
IMMUTABLE che solleva al planning, un record non assegnato, una polimorfica, un event trigger, un trigger su
vista, uno su partizionata e uno con transition table: `plpgsql_check` li **riferisce** tutti, nessuno lo fa
sollevare. Solleva per l'ambiente (estensione irraggiungibile, lock), non per una funzione. Da qui la
misura costruita.

**Residuo**, annotato e non corretto: gli anti-join della misura sono scritti due volte, nelle viste e in
`scripts/sql/guardrail_riferimenti_morti.sql`, che materializza la misura per non pagarla due volte. Il
guardrail si ferma sui `NON_MISURATO` prima del suo ramo (B), quindi oggi le due letture coincidono. Un
guardrail che legge le viste è la forma giusta; va con un giro sul guardrail, non qui.

#### 12.10.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto, `BEGIN … ROLLBACK`)

Il mirror del CSV lo fa Liquibase: nella prova la riga del presidio si è simulata con un UPDATE nella
stessa transazione.

| pgTAP | Senza | Con |
| --- | --- | --- |
| `dbops/test-processi-registro` | rosso il 13-bis | 16/16 |
| `dbops/test-riferimenti-morti-v1` | rosso il 10 (TAP n. 11: la voce `NON_MISURATO` esce rientrata) | 12/12 |
| `dbops/test-catalogo-presidi-v1`, `dbops/test-conta-presidio-per-variante-v1`, `dbops/test-presidi-testi-v1`, `dbops/test-presidio-processi-testo-per-causa-v1`, `dbops/test-corpo-funzione-senza-commenti-v1` | verdi | verdi, uguali |

Guardrail pre-commit verdi.

⛔ **Dopo l'apply, un rosso come app (Tid, 2026-11-04).** `test-riferimenti-morti-v1` falliva il test 9 (TAP
n. 10, «la sostituzione avviene»), poi la 10 cadeva su `permesso negato per la tabella tmp_raw`, ed era lento.
La causa: `pg_get_viewdef` qualifica i nomi rispetto al search_path di chi chiama, e l'app ha `dbops` nel suo;
il nome usciva senza schema, la sostituzione non avveniva, e i test 10-11 eseguivano la misura **vera** (una
compilazione di centinaia di funzioni, che dopo il conteggio DEFINER del test 6 trova `tmp_raw` del
proprietario). La mia prova era da owner col search_path di default. Correzione nel solo pgTAP: il testo si
legge sotto `SET LOCAL search_path = pg_catalog`, e se la sostituzione non avviene la 10 e la 11 sono rosse
con una riga sentinella, senza toccare la misura vera. Riprovato col search_path dell'app: con la vista
viva 12/12; con la vista di prima (20260804-64, rimessa in transazione) rosso il test 10. Il tempo del file
è quello del commit precedente (~3 s sullo scratch).

#### 12.10.3 Per Tid — ✅ 1 e 2 fatti (Tid, 2026-11-04: migrazione applicata, test verdi)

1. Apply su dbdev e sullo scratch di `20261104-53`, `-54` e del mirror di `presidi.csv`.
2. pgTAP: `dbops/test-processi-registro`, `dbops/test-riferimenti-morti-v1`, `dbops/test-catalogo-presidi-v1`,
   `dbops/test-conta-presidio-per-variante-v1`.
3. Commit.

Con il blocco 1d il giro 1 è chiuso.

ℹ️ **La durata di `test-riferimenti-morti-v1`** (Tid, 2026-11-04: «un po' lento»). Fatto datato: ~3 s sullo
scratch, uguale al commit precedente; quasi tutto sono due misure complete di `plpgsql_check` (~1,6 s
ciascuna: 717 funzioni e 1.971 coppie trigger-tabella), la seconda voluta dal test 6, che misura il percorso
del digest. Decisione di Tid: si lascia così. Le alternative scartate per ora: una misura per «forma» di
tabella delle funzioni trigger (cambio della misura, con un brief suo) o il test 6 solo in CI. Le decisioni di §4 sono prese, e l'ordine dei giri successivi è in §8.

#### 12.10.4 Doc

* `dbops/manual/vw_processi_che_bypassano.md` riscritta dallo Scopo in giù (niente stati, perché deve
  restare vuota, come si dichiarerebbe un debito nuovo, test, nota);
* `dbops/manual/vw_riferimenti_morti_rientrati.md` (la regola `NON_MISURATO`, i test 9-11, nota);
* `guide/processi-automatici-classe-e-identita.md` §6 (il controllo sul passe-partout non ammette debiti);
* `vendite/manual/fatture_fondi_fattura_source.md`: diceva al presente che il giro notturno attraversa la RLS
  con `BYPASSRLS` di `zeroerp_batch_fatturazione`, ritirato il 2026-10-15.
* Controllate e lasciate: `riferimenti_morti_esenzioni`, `vw_riferimenti_morti_da_sanare`,
  `fn_check_funzioni_riferimenti_morti`, `guide/presidi-e-registri-del-debito`,
  `guide/architettura-permessi-e-autorizzazioni`, `postgresql/row-level-security` (dicevano già «vuota»).

## 13. Rosso da zero sul blocco 1b (scratch `zeroerp_ruoli`, 2026-11-05)

Il migrate da zero sullo scratch si è fermato sul `20261104-50`. La sua `sqlCheck` vuole una sola
`maintenance.fn_job_run_log_failure`, e ne ha trovate due, a 10 e a 11 argomenti. Su dbdev non succede.

**Causa.** La firma a 11 argomenti (`p_sqlstate`) la porta il `20261016-39`, che ha `context: provision` e
sta in `changelog-provision-post.yaml`. Da zero, quindi, gira **dopo** il migrate principale. Il `20261103-66`
(proprietà in prestito, migrate principale) dà quella firma per fatta. Il suo `CREATE OR REPLACE` trova ancora
la firma a 10 e crea un secondo overload.

**Cura (team DB, 2026-11-05).** Il `-66` e il `-50` sono già su origin e restano come sono.

* `20_code/maintenance/20261103-29-fix-fn-job-run-log-failure-firma-sqlstate-da-zero` occupa uno slot libero
  prima del `-66`. La libertà dello slot è verificata sui file, sui `databasechangelog` di dbdev e dello
  scratch e sulla storia git. Il changeSet agisce solo dove manca la firma a 11: toglie quella a 10 e crea quella
  a 11 col corpo del `-39`. Su dbdev non fa niente.
* Il `20261015-03` e il `20261016-39` escono da `changelog-provision-post.yaml`. Da zero, rigirati dopo il
  migrate, ricreerebbero la firma a 10 e riporterebbero il corpo del `-39` sopra il `-66` e il `-50`, perdendo
  la D26.

**Prova** (SQL estratto, `BEGIN … ROLLBACK`):

* sullo scratch, dopo aver tolto la firma a 11 per simulare il percorso da zero, `-29`, `-66` e `-50` lasciano
  **una** funzione e le precondizioni del `-50` passano;
* su dbdev il `-29` non fa niente.

⚠️ Lo scratch attuale ha già i due overload, e lì il `-29` non fa niente: va ricostruito da zero
(`ci-local.sh --fresh`).

## 14. Giro 2 — le fusioni e la pipeline, 2026-11-07

**Il via di Tid (2026-11-07):** si parte col giro 2, sequenza `20261107-01`, senza incrociare l'altro cantiere.
Tid ricorda `%TYPE` ovunque un valore corrisponde a una colonna.

### 14.1 Che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `20_code/dbops/20261107-01` | D60, R6, §3.2 | `fn_audit_log_once`: tolto il ramo dblink, la riga nasce sempre nella transazione del chiamante; nuovo `p_duration_ms` in coda. Firma nuova: DROP + CREATE (nessuna dipendenza in `pg_depend`). Parametri e risultato a `%TYPE` sulle colonne del registro. COMMENT nuovo (non ne aveva) |
| `-02` | D3, D4 | Nuovo `dbops.fn_fusione_figlie`: le FK che puntano a un padre, dal catalogo (`conparentid = 0`), colonne in coppia. Si ferma su un padre senza chiave primaria di una colonna e su una figlia sotto RLS per chi lancia |
| `-03` | D3, D4 | Nuovo `dbops.fn_fusione_righe_doppie`: per ogni indice unico di ogni figlia che contiene una colonna della FK, le righe che la fusione renderebbe doppie. Rispetta NULLS NOT DISTINCT, il predicato di un indice parziale e le INCLUDE; non legge gli indici su espressioni |
| `-04` | D3, D4 | Nuovo `dbops.fn_fusione_ripunta_figlie`: prima i doppi (si ferma con l'elenco, le prime cento coppie), poi una UPDATE per figlia; un 23505 o 23P01 sfuggito al controllo risponde con lo stesso codice |
| `-05` → `-17` | D3, D45, R6 | `fn_admin_merge_stradario` (rinumerata, §14.7.5): la porta degli indirizzi (`zeroerp.maintenance_indirizzi_dettaglio`) aperta solo attorno al ripuntamento e riportata al valore di prima; validazioni con codice; durata in colonna; fuori il ramo d'audit `ERROR`. Firma a `%TYPE` (stessa identità) |
| `-06` | D4, D45, R6 | `fn_admin_merge_comune`: tutte le figlie dal catalogo (erano sei, ne ripuntava una); stesse correzioni della gemella |
| `-07` | D44 | `fn_check_pipeline_task_registered`: `E_PIPELINE_TASK_HANDLER_NOT_FOUND` per il task non registrato, `E_DBOPS_CHIAMATA_NON_VALIDA` per i parametri mancanti |
| `-08` | D44, Q14 ① | `fn_get_pipeline_task_implementation`: una variante chiesta e assente restituisce nessuna riga, non il default; codici come sopra |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | D44, D45 | Sei codici nuovi (id dei messaggi 1442-1447): `E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`, `E_COMUNE_NON_TROVATO`, `E_STRADARIO_NON_TROVATO` (DATO_ERRATO), `E_MERGE_RIGHE_DOPPIE` (CONFLITTO_STATO), `E_MERGE_FIGLIA_SOTTO_RLS`, `E_DBOPS_CHIAMATA_NON_VALIDA` (TECNICO, la famiglia «Chiamata non valida a %s: %s.» degli altri schemi) |

**Le scelte che non si vedono dal titolo:**

* **Tre building block, non uno.** «Chi sono le figlie» lo leggono sia il controllo dei doppi sia il
  ripuntamento: scritto una volta (regola del 2). Il controllo si può usare anche da solo, per vedere i doppi
  prima di fondere.
* **La porta degli indirizzi la apre la fusione, non il building block.** Quale guard aprire lo sa chi
  fonde. Se il ripuntamento solleva, il parametro torna al valore di prima con l'annullamento (della
  transazione o del savepoint di chi chiama): niente gestore. Lo prova il test 5.
* **Senza `SET search_path`** sui tre building block: le UPDATE fanno scattare i trigger delle figlie, che
  girano col search_path di chi chiama. Nomi tutti qualificati con `%I` e `regclass`.
* **Gli id sono `bigint`** nei building block: valgono per qualunque padre, e non c'è una colonna a cui
  ancorarli. Nelle fusioni e nella pipeline tutto è a `%TYPE`. ⚠️ Una colonna di `RETURNS TABLE` non accetta
  `%TYPE[]`: `colonne_fk` e `colonne_rif` sono `name[]`, il tipo di `pg_attribute.attname`, con la ragione
  accanto.
* **`STABLE` con un `fn_log_and_raise_error` dentro** (avviso di `plpgsql_check`): è la prassi del progetto,
  come nelle 134 funzioni che sollevano così.
* **Il ripiego del 23505.** Un indice su espressione, o una colonna che un trigger ricalcola dalla FK,
  sfuggono al controllo preventivo: il ripuntamento li intercetta e risponde con lo stesso codice, col
  vincolo e il dettaglio di PostgreSQL. Lo prova il test 23.
* **Il consiglio sbagliato tolto.** La prima stesura del messaggio diceva «fondere prima le vie»: non basta,
  perché la via fusa resta (Q16). Messaggio, COMMENT e pagine dicono di correggere il doppio.

### 14.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* L'estratto degli otto changeSet gira intero, con le sei righe dei CSV simulate da un INSERT (il mirror lo
  fa Liquibase). Firme: una per nome; quella di `fn_audit_log_once` ha 15 argomenti.
* `plpgsql_check` sulle otto: nessun errore; gli avvisi sono quelli di §14.1 e gli «OUT maybe unmodified» di
  una funzione che restituisce da SQL dinamico.
* pgTAP, senza e con l'estratto in testa:
  * nuovo `dbops/test-fusioni-comune-stradario-v1.sql` (28): con, 28/28; senza, si ferma al test 1
    (`p_duration_ms` non esiste);
  * `dbops/test-pipeline-task-registry.sql` (8 → 10): senza, rossi il 6, 7, 8 e 10 (il ripiego sul default
    e `E_GENERICO`); con, 10/10;
  * `dbops/test-registri-append-only-postura-v1.sql` (test 13 con la firma nuova): con, rossi da owner i
    16-19, per costruzione come dal giro C1; senza, si ferma al 13 (firma inesistente);
  * invariati e verdi con l'estratto: `test-audit-log-perimetro-scrittori-v1`, `test-character-n-v1`,
    `test-riferimenti-morti-v1`, `test-stati-check-scrittori-v1`, `test-vw-codici-errore-motivo-nominato`,
    `test-vw-codici-errore-valore-atteso`, `test-punti-canale-campo-v1`, `test-corpo-funzione-senza-commenti-v1`,
    `script/test-catalogo-messaggi-errore-completo` (arità dei segnaposto), `script/test-rubinetto-primo-motivo-v1`,
    `vendite/test-seed-pull-commessa-pipeline-v1`, `vendite/test-pipeline-consuma-plafond-seed-v1`,
    `maintenance/test-bump-toponomastica-v1`.
* Guardrail dei changelog e del preambolo pgTAP verdi; header di licenza a posto. Il pre-commit è rosso su
  `check-i18n-keys` per `vendite.righe.articolo_reason.obsoleto`, una chiave del cantiere degli articoli,
  non di questo giro.

### 14.3 Per Tid

1. Apply su dbdev e sullo scratch, coi due comandi di sempre (§12.3).
2. pgTAP **come app**: `dbops/test-fusioni-comune-stradario-v1.sql` (37), `dbops/test-pipeline-task-registry.sql`,
   `dbops/test-registri-append-only-postura-v1.sql`, `dbops/test-audit-log-perimetro-scrittori-v1.sql`,
   `script/test-catalogo-messaggi-errore-completo.sql`; per il blocco 2b anche `script/test-fn-search-stradario.sql`,
   `anagrafiche/test-fn-create-indirizzo-v1.sql`, `anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql`,
   `config/test-stradario-riclassificazione-unico.sql`.
3. La baseline B-7 (§14.4), poi il commit.

### 14.4 La baseline B-7 si muove: è una decisione

Calcolata in transazione sullo scratch, senza e con l'estratto, il giro 2 la cambia così:

| Codice | Prima | Dopo | Perché |
| --- | --- | --- | --- |
| `E_GENERICO` | 31 punti | 25 | i sei punti della pipeline escono |
| `E_DBOPS_CHIAMATA_NON_VALIDA` | — | `PARAMETRO`, 9 | codice nuovo: i guard di parametro delle fusioni, dei building block e della pipeline |
| `E_MERGE_RIGHE_DOPPIE` | — | `ECCEZIONE`, 2 | codice nuovo: il doppio trovato prima e quello intercettato alla scrittura |
| `E_PIPELINE_TASK_HANDLER_NOT_FOUND` | — | `NOT_FOUND`, 2 | il codice esisteva, ora lo solleva anche il DB |

⚠️ Sullo scratch la baseline committata differisce già, prima di questo giro, su
`E_ARTICOLO_ONERE_NATURA_MERCE`, `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`, `E_DDT_EMISSIONE_SOLO_ONERI` e
`E_DDT_ONERE_NON_FATTURABILE`: sono di altri cantieri, e vanno spiegati da loro.

### 14.5 Doc

* Pagine `manual/` riscritte: `fn_admin_merge_stradario`, `fn_admin_merge_comune` (il difetto descritto diventa
  il comportamento; codici, test). Aggiornate: `fn_audit_log_once` (niente ramo dblink, `p_duration_ms`, e il
  vocabolario senza `START`, stantio dal giro C1), `fn_check_pipeline_task_registered`,
  `fn_get_pipeline_task_implementation`. Nuove: `fn_fusione_figlie`, `fn_fusione_righe_doppie`,
  `fn_fusione_ripunta_figlie`. Le loro schede auto-generate nascono alla rigenerazione della doc.
* Guide: `messaggi-audit.md` (la sezione «Logging fuori transazione» diventa «Una riga della transazione»;
  l'esempio del batch non scrive più una riga `ERROR` prima di rilanciare; la durata in `p_duration_ms`),
  `automazione-db.md`, `riclassificazione-vie.md`, `postgresql/dblink.md` (R7),
  `postgresql/parametri-personalizzati-(GUC).md`.

### 14.6 Residuo del giro

* **R6, la metà che resta.** Le automazioni che scrivono un riepilogo di fine giro passano la durata in
  `p_duration_ms` quando ciascuna si riapre (giro 10).
* **BE6.** I codici nuovi del giro (§14.1) entrano nella rigenerazione di `error_policies_generated.py` alla
  fine del giro 3, come da §5.
* **`dbops.audit_log` senza scadenza alla nascita.** `test-registri-dbops-scadenza-v1` lo motivava col
  canale fuori transazione, che non c'è più: il motivo non regge. Si guarda con D16 (la scadenza
  `CLEANUP_AT`), nel giro 10.
* **Q16** (§4): decisa, è il blocco 2b (§14.7).

### 14.7 Blocco 2b — la via fusa resta, soppressa (Q16)

**Decisione di Tid (2026-11-07): (b).** Scritto e provato sullo scratch lo stesso giorno, col via di Tid.

#### 14.7.1 Che cosa è stato scritto

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261107-09` | `config.stradario.obsoleto_dal date` (la via soppressa); il vincolo `uq_stradario_comune_stradario_gen_cp` diventa un indice unico **parziale** sulle vie vive, con lo stesso nome; torna `ix_config_stradario_comune_id` (vedi sotto) |
| `20_code/dbops/20261107-17` (era il `-05`, vedi §14.7.5) | La fusione delle vie segna l'origine soppressa dopo il ripuntamento, con `LEAST(p_event_date, fn_data_operativa())`; una via soppressa non si fonde, né come origine né come destinazione (`E_STRADARIO_SOPPRESSO`, codice nuovo, id 1448) |
| `20_code/anagrafiche/20261107-10` | `fn_create_indirizzo`: l'`ON CONFLICT` sulla via nomina il predicato della chiave parziale |
| `20_code/script/20261107-11`, `-12` | `fn_search_stradario`, `fn_get_stradario` (ramo per comune): solo le vie vive |
| `20_code/script/20261107-13` | `fn_check_indirizzo_duplicato`: il flusso B risolve la via fra le vie vive |
| `20_code/anagrafiche/20261107-14` | `fn_provisiona_dati_di_sviluppo`: l'indirizzo di prova sulla prima via viva |
| `20_code/dbops/20261107-15` | `fn_pgtap_crea_indirizzo_dettaglio`: la prima via viva |
| `20_code/anagrafiche/20261107-16` | Il guard generico del ritiro (`dbops.trgfn_child_requires_non_obsolete_parent`) su `indirizzi_dettaglio → stradario`: un indirizzo non nasce su una via soppressa né vi si sposta |

**Le scelte:**

* **`obsoleto_dal`, non `attivo = false`**, come per il ritiro di una voce di catalogo: `attivo` vuol dire
  «riferimento valido», e lo storico degli indirizzi nomina ancora la via.
* **«Soppressa» = data valorizzata.** L'indice parziale vuole un predicato immutabile (`obsoleto_dal IS NULL`),
  e le letture usano lo stesso. Il guard generico usa invece `script.fn_e_obsoleto` (data raggiunta): i due
  coincidono perché la data la scrive solo la fusione, e mai oltre la data operativa (una soppressione è un
  fatto avvenuto, non un ritiro programmato). ⚠️ Una data futura scritta a mano li farebbe divergere: residuo
  qui sotto.
* **L'indice della FK `comune_id`.** `20_code/dbops/20260727-37` l'aveva tolto perché lo copriva il vincolo
  unico; un indice parziale non copre le vie soppresse, e `dbops.vw_fk_senza_indice` non lo conta. Torna,
  col nome della politica degli indici, prima del DROP del vincolo.
* **Il censimento dei lettori** (catalogo delle dipendenze per le viste, corpo delle funzioni, backend):
  scelgono una via per il nuovo le due ricerche (il backend passa da `fn_search_stradario`), la creazione
  dell'indirizzo, il controllo dei doppi, il provisioning e la fixture. Le tre viste degli indirizzi
  (`vw_indirizzo_completo`, `vw_indirizzi_dettaglio`, `vw_indirizzi_resolved_base`) mostrano indirizzi che
  esistono, e **non** si filtrano: sono la storia. `fn_resolve_codice_postale` risolve il CAP di una via già
  scelta, `proc_bump_toponomastica` rinormalizza tutte le vie: restano.
* La shadow `storico.stradario` salva la riga in `snapshot` jsonb: la colonna entra da sola.

#### 14.7.2 Le prove (scratch, come owner, SQL estratto in ordine di Liquibase, `BEGIN … ROLLBACK`)

* `dbops/test-fusioni-comune-stradario-v1.sql` (28 → 37): con i due blocchi, 37/37. Con colonna, indice e
  fusione ma **senza** i lettori riallineati (`-10` … `-16`): rossi il 31, 32, 33, e il file muore al 36 sull'`ON
  CONFLICT` di `fn_create_indirizzo` («nessun vincolo che combaci»), cioè il guasto che il `-10` previene.
  Il 15 ora prova anche che la via soppressa, con la stessa terna di una via viva della destinazione, non è
  un doppio.
* I 46 pgTAP che nominano vie o indirizzi, senza e con l'estratto: nessun rosso nuovo. Rosso uguale nei due
  versi `anagrafiche/test-catasto-unita-immobiliare` (una colonna `istanza_utility_id` che non esiste: un
  difetto del test, non di questo giro).
* I pgTAP del blocco 2a, con l'estratto intero: invariati (§14.2).
* `plpgsql_check` sulle sette funzioni: nessun errore; gli avvisi sono quelli dei corpi vivi.
* Guardrail dei changelog verdi sui sedici changeSet. La baseline B-7 non cambia rispetto a §14.4:
  `E_STRADARIO_SOPPRESSO` non entra nella misura delle famiglie.

#### 14.7.3 Doc

Pagine `manual/`: `config/stradario` (la chiave delle vie vive, la via soppressa, la colonna nel diagramma),
`dbops/fn_admin_merge_stradario`, `dbops/fn_admin_merge_comune` (fondere prima le vie ora funziona),
`script/fn_search_stradario`, `script/fn_get_stradario`, `script/fn_check_indirizzo_duplicato`,
`anagrafiche/fn_create_indirizzo`, `anagrafiche/indirizzi_dettaglio`, `dbops/fn_pgtap_crea_indirizzo_dettaglio`.
Guida `riclassificazione-vie.md`.

#### 14.7.4 Residuo

* **Una data futura su `obsoleto_dal` scritta a mano** farebbe divergere l'indice (la via è già fuori dalla
  chiave) dal guard (che la lascia ancora usare). Oggi la scrive solo la fusione; un guard che lo impedisca
  sarebbe un oggetto in più, e non è stato chiesto.
* **Il seed `80_data/sql/config/stradario.csv`** si carica per id con `loadUpdateData`, `runOnChange`: non
  conosce `obsoleto_dal` e non la tocca, ma riscrive `comune_id`. Una via spostata da una fusione dei comuni
  tornerebbe al comune del seed alla prossima modifica del CSV. Non nasce qui (vale per ogni fusione dei
  comuni da quando la funzione ripunta lo stradario): è il tema seed contro macchina, da decidere con Tid.
* **Il COMMENT di `fn_provisiona_dati_di_sviluppo`** nomina un brief: non si è riemesso, si riscrive nel giro 14.

#### 14.7.5 Il primo apply si è fermato sul `-05` (Tid, 2026-11-07)

«SQL Precondition failed. Expected '1' got '0'» sul `-05`, dopo `-14` … `-17` entrati su dbdev e sullo
scratch. **Causa:** la fusione delle vie del blocco 2b nomina `config.stradario.obsoleto_dal`, sia nella
preCondition sia in un `DECLARE … %TYPE`, che il `CREATE FUNCTION` risolve subito; la colonna nasce in
`00_schema/config/20261107-09`. Il migrate esegue in **ordine di numero su tutti i livelli**
(`changelog-autogen.yaml`), non prima `00_schema` e poi `20_code`: il `-05` girava prima del `-09`. La mia
prova eseguiva l'estratto per cartella e senza le preCondition, quindi non poteva vederlo.
**Cura:** il `-05`, mai entrato, diventa il `-17`, dopo la colonna; preCondition e `%TYPE` restano.
**Prova rifatta come la fa il migrate:** i changeSet non entrati in ordine di numero, ogni preCondition
eseguita come `SELECT` col valore atteso nel punto in cui cade, su dbdev e sullo scratch, in transazione
annullata: tutto passa; il test delle fusioni 37/37. ⚠️ La lezione per i giri dopo: la prova si fa sempre
in ordine di numero e con le preCondition.

### 14.8 Dopo l'apply: tre rossi come app (Tid, 2026-11-07)

`dbops/test-fusioni-comune-stradario-v1` come app, su dbdev e sullo scratch: rossi il 6, il 10 e il 30. Da
owner erano verdi.

**Test 6 e 10 — il nome della tabella dipende da chi chiama.** I tre building block componevano i nomi con
`regclass::text`, che toglie lo schema quando è nel `search_path` di chi chiama; quello dell'app contiene
`anagrafiche`. Quindi le chiavi del riepilogo del ripuntamento e i messaggi cambiavano a seconda di chi
lanciava la fusione (`indirizzi_dettaglio` invece di `anagrafiche.indirizzi_dettaglio`), e il SQL dinamico
risolveva la tabella col `search_path` di chi chiama, dove una tabella temporanea con lo stesso nome
avrebbe preso il posto di quella vera. È la trappola già nota («regclass: OID»); la mia prova era da owner,
col `search_path` di default. **Cura:** `20_code/dbops/20261107-18`, un building block
`dbops.fn_nome_qualificato(regclass)` (il nome sempre con lo schema, dal catalogo) e le tre funzioni
riscritte per usarlo dove il nome si scrive, si rimette in un SQL o serve a ordinare; nel risultato del
controllo dei doppi le colonne `regclass` passano per oid. Il test confronta i nomi con lo stesso building
block.

**Test 30 — l'indice della FK `comune_id` creato e subito tolto.** Il `-09` lo creava, ma
`80_data/sql/dbops/fk_index_policy_bonifica_ridondanze.csv` diceva `consentito = false` per quella FK (era
ridondante col vincolo unico totale, dal 2026-07-27), e `dbops.apply_fk_index_policy` in `90_end` toglie per
nome l'indice di una riga a `false`. La politica, invece, non lo ricreerebbe con la riga a `true`:
`dbops.vw_fk_senza_indice` guarda solo gli schemi di `dbops.automation_scope`, e `config` non c'è.
**Cura:** la riga del CSV a `true` (ora le due fonti della politica dicono la stessa cosa) e
`00_schema/config/20261107-19`, che rimette l'indice.

**Il test 2** spegneva l'interruttore del canale di log invece di rimetterlo com'era: nel resto del file il
registro degli errori non scriveva (l'avviso «canale di log spento» dell'output). Ora lo rimette.

**Le prove** (scratch e dbdev, in transazione annullata): `-18` e `-19` in ordine di numero con le
preCondition, poi la riga della politica come la scrive il mirror e la `CALL` di
`dbops.apply_fk_index_policy`, poi il test: 37/37 col `search_path` dell'app e 37/37 con quello di default.
Senza il `-18` il file si ferma (usa il building block). `plpgsql_check`: solo gli avvisi `STABLE` noti.
Guardrail verdi. Pagina nuova: `dbops/manual/fn_nome_qualificato`.

⛔ **L'apply del `-18` si è fermato** («non è possibile inserire comandi multipli in una istruzione
preparata»): il building block è `BEGIN ATOMIC`, e con `splitStatements: false` pgjdbc, dopo l'`END` di un
`BEGIN ATOMIC`, non spezza più sui `;`: il `COMMENT` che seguiva finiva nella stessa istruzione. È la
trappola già nota (`20260921-21`); psql la gestisce, per questo la prova con psql era verde. Il `-18` non era
entrato: corretto sul posto, con la funzione da sola nel primo `- sql:` e tutto il resto nel secondo.
**Provato attraverso il driver** (pgjdbc 42.7.10, un `Statement.execute` per change, in transazione
annullata) su dbdev e sullo scratch: i due change del `-18` e il `-19` passano.

⚠️ **Residuo per il giro 10d (Q14 ②):** `config` fuori dall'ambito delle automazioni vuol dire che le sue FK
non le vede `vw_fk_senza_indice` e la politica non ne crea gli indici, ma ne toglie quelli a `false`. E la
stessa FK ha una riga in due CSV (`fk_index_policy.csv` e quello della bonifica), contro «una tabella, un
CSV». Si guarda con la convergenza di `fk_index_policy`.
⚠️ **Correzione (2026-11-09, §29.1 punto 9):** `config` è nell'ambito (`config,*all`, dal 2025-11-23). La FK non si vedeva
per il filtro su `consentito` della vista, cioè per Q14 ② stessa.

⚠️ **La lezione per i giri dopo:** la prova si fa anche col `search_path` dell'app
(`django, public, config, dbops, script, anagrafiche`), non solo da owner, e con le automazioni di `90_end`
che possono disfare un oggetto creato in `00_schema`.

**✅ Applicato da Tid il 2026-11-07** su dbdev e sullo scratch, `20261107-01` … `-19` (senza `-05`,
rinumerato al `-17`) e i tre CSV; pgTAP di §14.3 verdi come app. Il giro 2 è chiuso. Restano: la baseline
B-7 (§14.4), il commit, e i residui di §14.6, §14.7.4 e §14.8, assegnati ai loro giri.

## 15. Giro 3 — i guard ATTIVO, 2026-11-07

**Via di Tid (2026-11-07):** giro 3, dopo il commit del giro 2 (`93b650e517`); YAML dal primo numero libero
(`20261107-20`), e `%TYPE` dove si ancora. Difetti: D5, D18, D46, D47, D49, D51 (con Q8).

### 15.1 Il censimento dei montaggi (D49, D18)

Letto dal catalogo dello scratch e di dbdev il 2026-11-07 (struttura, non popolazione): il generatore monta
il block e il require **sempre con cinque argomenti**; i require scritti a mano (sette dell'attivo, immediati,
su contratti, ordini e righe componenti; cinque dell'obsoleto, su pratiche, flussi, listini kit, attività di
commessa e indirizzi) ne hanno cinque, uno dell'obsoleto sei (l'esenzione). Nessun montaggio usava i
ripieghi: gli argomenti diventano obbligatori senza toccare un trigger. Tutti hanno una FK verso il padre;
il ramo «padre assente» (D5) resta un caso del modello (un require su chiave polimorfa), provato su TEMP.

Lettori di `tgargs` censiti sul vivo (corpo delle funzioni): `fn_trigger_attivo_orfani`,
`fn_ritira_attivo_eccezioni` e le tre di D6 (`fn_trigger_exists_block_by_args`, `…_require_by_args`,
`fn_drop_triggers_by_function_args`). Le altre cinque funzioni che nominano le trgfn lo fanno nei commenti.

### 15.2 Che cosa è stato scritto

| changeSet | Oggetto | Difetti |
| --- | --- | --- |
| `20_code/dbops/20261107-20` | nuovo `dbops.fn_trigger_attivo_argomenti(name, text[])`: la grammatica per nome dei tre trigger, tutti gli argomenti obbligatori, rinumera TG_ARGV (base 0) | D18, D49 |
| `20_code/dbops/20261107-21` | nuovo `dbops.fn_trigger_padre_stato(oid, name, text)`, DEFINER: stato del padre (jsonb) e «trovato», fuori dalla RLS, per le due require | D51, D5 |
| `20_code/dbops/20261107-22` | nuovo `dbops.fn_trigger_figlie_presenti(oid, name, text)`, DEFINER: le figlie che tengono acceso il padre, fuori dalla RLS | D51 |
| `20_code/dbops/20261107-23` | `trgfn_prevent_deactivate_if_children`: grammatica, argomenti obbligatori, figlie dal `-22`; una colonna referenziata o di stato che il padre non ha è `E_ATTIVO_BLOCK_ARGS` invece di un NULL | D18, D49, D51 |
| `20_code/dbops/20261107-24` | `trgfn_child_requires_active_parent`: `E_ATTIVO_PADRE_NON_ATTIVO`, `E_PADRE_INESISTENTE`, `E_TRIGGER_ARGOMENTI_INVALIDI`; padre dal `-21`; l'attivo della figlia letto sulla riga | D5, D18, D46, D49, D51 |
| `20_code/dbops/20261107-25` | `trgfn_child_requires_non_obsolete_parent`: `E_TRIGGER_ARGOMENTI_INVALIDI` nei rami di montaggio, `E_PADRE_INESISTENTE`; padre dal `-21` | D5, D18, D47, D49 |
| `20_code/dbops/20261107-26` | `fn_trigger_attivo_orfani` dalla grammatica; il motivo `ARGOMENTI_INSUFFICIENTI` diventa `ARGOMENTI_INVALIDI`; COMMENT di `fn_ritira_attivo_orfani` riscritto (lo nomina) | D18 |
| `20_code/dbops/20261107-27` | `fn_ritira_attivo_eccezioni` dalla grammatica, non per posizione | D18 |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_ATTIVO_PADRE_NON_ATTIVO` (CONFLITTO_STATO, id 1449), `E_PADRE_INESISTENTE` (DATO_ERRATO, id 1450); note di `E_ATTIVO_REQUIRE` (M35), `E_TRIGGER_ARGOMENTI_INVALIDI`, `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` riscritte | D46, D47, D5 |

I COMMENT dei sette oggetti sono riscritti per intero secondo §5d (niente brief, niente marcatori di
revisione, niente misure): il «⭐ rev 2026-08-20 … misurato 168 su 349» del block esce.

### 15.3 Le scelte dentro il giro (da guardare, Tid)

1. **`E_ATTIVO_REQUIRE` resta al generatore, non ai rami di montaggio del trigger.** D46 diceva «resta per
   il montaggio»: l'ho letto come «per chi monta», cioè il generatore, che è quello che il suo messaggio dice
   («Errore generazione regola ATTIVO_require»). I rami di montaggio della funzione trigger escono con
   `E_TRIGGER_ARGOMENTI_INVALIDI`, lo stesso codice di D47 per la gemella: una regola, un codice, nelle due
   require. Il block tiene i suoi (`E_ATTIVO_BLOCK_ARGS`, `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`), che non erano
   in discussione.
2. **La lettura fuori dalla RLS vale anche per la require dell'obsoleto.** D51/Q8 nominano i due guard
   ATTIVO; la require dell'obsoleto legge il padre con la stessa forma, e una lettura sola per le due require
   è la regola del 2. Un catalogo è obsoleto o no per tutti.
3. **Le due DEFINER ricevono il trigger, non i nomi.** Una DEFINER che esegue SQL dinamico su nomi passati
   dal chiamante leggerebbe qualunque colonna di qualunque tabella per chiunque la chiami: l'applicazione
   può montare un trigger con argomenti a piacere su una TEMP sua. Le due letture prendono `(tgrelid,
   tgname)`, leggono gli argomenti dal montaggio e rispondono solo se la tabella del trigger è del loro
   proprietario (cioè l'hanno montata le migrazioni). Rifiutano anche se la tabella da leggere è sotto RLS
   per il proprietario stesso (FORCE o un altro proprietario): «non ho potuto guardare» non diventa «non
   c'è». La regola, generale, è scritta in `linee-guida-trigger.md` §«BEFORE e AFTER».
4. **Il ramo della colonna referenziata NULL del block resta com'era** (si registra e si passa): nessuna
   figlia può riferire una chiave NULL, quindi il controllo saltato è corretto sul modello; non era in D49.
5. **Il rifiuto per l'operatore porta `campo`** (la colonna FK nelle require, la colonna attivo nel block)
   anche in `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`. Nessun `bersaglio`: il padre può essere una riga che
   l'operatore non vede.

### 15.4 Le prove (scratch `zeroerp_ruoli`, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* **L'estratto in ordine di numero, con le dieci preCondition** eseguite come `SELECT` col valore atteso al
  loro posto, e le due righe dei CSV simulate da un INSERT: passa intero su scratch e su dbdev, come owner.
  Dopo le prove i due database sono puliti (funzioni e messaggi nuovi assenti, corpi di oggi intatti).
* **`plpgsql_check`** sulle sei plpgsql (le trgfn con una tabella dei loro montaggi): nessun errore; solo
  gli avvisi «STABLE che chiama una VOLATILE» (`fn_log_and_raise_error`, `fn_get_override_col`), gli stessi
  delle fusioni del giro 2.
* **Il difetto, prima della correzione, come app** (sonda e file nuovo senza estratto): chiudendo i differiti
  nei panni dell'operatore di un'azienda, il listino attivo di un'altra risponde «Errore generazione regola
  ATTIVO_require. Sqlerrm: Padre non attivo» (`E_ATTIVO_REQUIRE`); lo stesso operatore spegne una tipologia
  usata da un listino attivo dell'altra azienda.
* **pgTAP** (con / senza l'estratto in testa; da owner salvo dove detto):

| File | Con | Senza |
| --- | --- | --- |
| nuovo `dbops/test-guard-attivo-grammatica-e-codici-v1` (23, runner owner: trigger su TEMP) | 23/23, anche col `search_path` dell'app | si ferma al 4 (la grammatica non esiste) |
| nuovo `dbops/test-guard-attivo-occhi-del-proprietario-v1` (9, runner app) | da owner 1, 3, 4, 5, 9 verdi; 2, 6, 7, 8 rossi per costruzione (dichiarato nel file) | come app: 1-2 verdi, 3-5 rossi col difetto, poi si ferma (le letture non esistono) |
| `dbops/test-trigger-attivo-orfani-v1` (ora runner owner, motivo rinominato) | 10/10 | rossi 4 e 7 (il motivo) |
| `catalogo/test-articoli-approvvigionamento-v1` (test 10: la frase nuova) | 12/12 | rosso il 10 |
| `dbops/test-trgfn-prevent-deactivate-if-children-pdp` (13), `config/test-trgfn-prevent-deactivate-if-children-toponomastica` (9), `dbops/test-automazione-attivo-eccezioni-v1` (8), `pratiche/test-guard-non-obsolete-parent-v1` (10), `vendite/test-articolo-ritirato-v1` (17), `dbops/test-fusioni-comune-stradario-v1` (37), `anagrafiche/test-fn-create-indirizzo-v1` (6) | tutti verdi | tutti verdi |
| presidi trasversali: `dbops/test-riferimenti-morti-v1` (12), `dbops/test-security-definer-search-path-v1` (5), `script/test-catalogo-messaggi-errore-completo` (7), `script/test-rubinetto-primo-motivo-v1` (7), `dbops/test-corpo-funzione-senza-commenti-v1` (15), `dbops/test-punti-canale-campo-v1` (18), `dbops/test-vw-codici-errore-valore-atteso` (7), `-motivo-nominato` (10) | tutti verdi | tutti verdi |
| `rls/test-rls-listini-ef-whitelist-write` (8, commento della fixture riscritto) | da owner 4 e 5 rossi, per costruzione | uguale |

* Guardrail dei changelog, del preambolo pgTAP, dei letterali e del fuso verdi; header di licenza a posto. Il
  pre-commit è rosso solo su `check-i18n-keys` per `vendite.righe.articolo_reason.obsoleto`, come al giro 2:
  la chiave è del cantiere degli articoli.
* ⚠️ Due corse con l'estratto hanno preso un deadlock contro sessioni concorrenti sullo scratch (una corsa
  pgTAP da `zeroerp_owner`, poi l'altro cantiere che provava le sue ALTER su `vendite.fatture`); rilanciate a
  scratch libero, sono passate. Non è un difetto del giro, ma le prove di due cantieri sullo stesso scratch
  si pestano.

### 15.5 La baseline B-7 si muove ancora

Fotografia di `scripts/sql/codici_errore_famiglie_snapshot.sql` in transazione sullo scratch, senza e con
l'estratto (le righe del giro 2, §14.4, non sono ancora nella baseline committata):

| Codice | Senza | Con | Perché |
| --- | --- | --- | --- |
| `E_ATTIVO_REQUIRE` | `NOT_FOUND`, 6 | — | i rami del trigger escono; resta il generatore, che la misura non legge |
| `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` | `NOT_FOUND`, 6 | — | i rami di montaggio e del padre assente escono (D47, D5) |
| `E_DBOPS_CHIAMATA_NON_VALIDA` | `PARAMETRO`, 9 | `PARAMETRO`, 15 | le due letture DEFINER, stessa famiglia |
| `E_TRIGGER_ARGOMENTI_INVALIDI` | `ECCEZIONE,ENUM,VALORE_ATTESO`, 6 | stesse, 10 | i rami di montaggio delle due require, nessuna famiglia nuova |

Nessun «nasce generico» né «accumula»: i due codici nuovi la misura non li legge. ⚠️ La fotografia «senza»
differisce dalla baseline committata anche fuori da questo brief (per esempio `E_GENERICO` a 9 punti,
`E_DDT_*`): sono di altri cantieri, e il confronto riga per riga resta di Tid.

### 15.6 Per Tid

1. Apply su dbdev e sullo scratch: `20261107-20` … `-27` e i due CSV dei codici.
2. pgTAP **come app**: i due nuovi (`dbops/test-guard-attivo-grammatica-e-codici-v1` gira da owner per il
   suo marcatore), `dbops/test-trigger-attivo-orfani-v1`, `catalogo/test-articoli-approvvigionamento-v1`,
   `rls/test-rls-listini-ef-whitelist-write`, `dbops/test-trgfn-prevent-deactivate-if-children-pdp`,
   `config/test-trgfn-prevent-deactivate-if-children-toponomastica`, `dbops/test-automazione-attivo-eccezioni-v1`,
   `pratiche/test-guard-non-obsolete-parent-v1`, `vendite/test-articolo-ritirato-v1`,
   `script/test-catalogo-messaggi-errore-completo`, `dbops/test-riferimenti-morti-v1`,
   `dbops/test-security-definer-search-path-v1`. ⚠️ Il giro cambia il comportamento di **tutti** i
   trigger ATTIVO: un rosso altrove nella suite, su un guard che legge figlie o padre di un'altra azienda,
   è da guardare come effetto di D51 (oggi la suite non ne ha uno noto).
3. La baseline B-7: le righe di §14.4 e di §15.5 insieme, dopo averle confrontate.
4. Il commit, e il via al giro 4.

**Esito (Tid, 2026-11-07):** apply su dbdev e sullo scratch, pgTAP di §15.6 verdi come app. La baseline B-7
resta da fare (punto 3).

**Punto 3 fatto** (sessione DB su richiesta di Tid, 2026-11-07): §16.6.

### 15.7 Doc

* Pagine `manual/` riscritte sul comportamento nuovo: `trgfn_child_requires_active_parent`,
  `trgfn_child_requires_non_obsolete_parent` (anche l'esenzione e i cablaggi, che non conosceva),
  `trgfn_prevent_deactivate_if_children`. Aggiornate: `fn_trigger_attivo_orfani`, `fn_ritira_attivo_orfani`,
  `fn_ritira_attivo_eccezioni`, `fn_trigger_argomenti`. Nuove: `fn_trigger_attivo_argomenti`,
  `fn_trigger_padre_stato`, `fn_trigger_figlie_presenti`, con le voci in `dbops/index.md` e `index.ci.md`
  (le schede auto-generate nascono alla rigenerazione della doc).
* Guide: `automazione-db.md` §4.2 (i codici, la lettura fuori dalla RLS, la grammatica);
  `linee-guida-trigger.md` (un guard che decide su una riga correlata non la legge sotto la RLS di chi
  scrive, e una DEFINER di lettura riceve il trigger, non i nomi; la grammatica ATTIVO come esempio di
  funzione condivisa).
* Q8, il censimento delle fixture: l'unica che chiudeva i differiti «nei panni di chi ha scritto» apposta è
  `rls/test-rls-listini-ef-whitelist-write`; il suo commento ora dice il vero (il contesto non conta più). Le
  altre fixture che cambiano attore non dipendevano dal require: nessuna da cambiare.

### 15.8 Residuo

* ~~**D6, giro 4.**~~ Fatto nel giro 4 (§16): i due riconoscimenti passano dalla grammatica di `-20` e sono
  nel presidio 23; il ritiro è generico e confronta l'array intero.
* **BE3 e BE6** (§5): il giro 3 è applicato, il team BE può farle.
* La require dell'obsoleto e gli altri trigger scritti a mano non sono nel presidio degli orfani (che guarda
  solo i generati): un montaggio a mano verso una colonna sparita ora si ferma con
  `E_TRIGGER_ARGOMENTI_INVALIDI` invece di passare, ma nessuno lo ritira da solo. È la scelta di oggi
  («orfano = nome morto» dei soli generati), non un difetto aperto.

## 16. Giro 4 — riconoscimento e strumenti, 2026-11-07

**Via di Tid (2026-11-07):** giro 4, YAML dal primo numero libero (`20261107-28`), `%TYPE`; primo id messaggio
libero 1451 (il giro non ne prende). Difetti: D6, D21 con M18, D53 (Q9).

### 16.1 Che cosa è stato scritto

| changeSet | Oggetto | Difetti |
| --- | --- | --- |
| `20_code/dbops/20261107-28` | `fn_trigger_exists_block_by_args`: funzione del trigger per OID (`'dbops.trgfn_…()'::regprocedure`), argomenti per nome da `fn_trigger_attivo_argomenti`, confronto esatto; firma da `text` a `name` (`%TYPE` del catalogo), DROP e CREATE | D6 |
| `20_code/dbops/20261107-29` | `fn_trigger_exists_require_by_args`: lo stesso, per il require | D6 |
| `20_code/dbops/20261107-30` | `fn_drop_triggers_by_function_args`: funzione per `to_regprocedure`, argomenti da `tgargs` uguali all'array chiesto, `DROP` con schema e nome dal catalogo; firma ancorata | D6 |
| `00_schema/dbops/20261107-31` | `chk_processi_bersagli_via` si allarga ai 34 modi di `script.fn_resolve_emittente_fiscale_id`, più `padre` fino al seed | D21 |
| `80_data/sql/dbops/processi_bersagli.csv` | riga 2 (`vendite.listini_versioni`): `padre` → `listino`, la via del guard montato | D21 |
| `90_end/20261107-32` | `chk_processi_bersagli_via` stretto sui modi del risolutore (`padre` esce), con un controllo che dice la riga fuori vocabolario; COMMENT di tabella e colonne riscritti | D21, M18 |
| `20_code/dbops/20261107-33` | `fn_foreign_keys_info(regclass)`: da `pg_constraint` con `unnest(conkey, confkey) WITH ORDINALITY`, schema compreso, cloni delle partizioni non ripetuti; DROP e CREATE (era `text`, `information_schema`) | D53 |
| `20_code/dbops/20261107-34` | `fn_find_file_usage`: le righe entranti di `fn_foreign_keys_info`, col nome del vincolo, la posizione e `referenced_column` (era `pk_column`); DROP e CREATE | D53 |

Nessun chiamante cambia: l'unico delle tre di D6 è `fn_run_automations_attivo`, che passa `name` e `text`
(`text → name` è implicito); le due di D53 non ne hanno (DB, backend, pgTAP, censiti il 2026-11-07). Le firme
nuove prendono i privilegi dai default dello schema, come le funzioni del giro 3.

⚠️ Le righe di `-31`, del CSV e di `-32` (D21) sono uscite dal giro il 2026-11-07 e passano al blocco 4b (§16.9).

### 16.2 Perché due passi per il vincolo delle vie

Il CSV dei bersagli lo carica `80_data`, dopo `00_schema`. Su dbdev la riga 2 dice ancora `padre` quando gira il
`-31`, quindi lì il vincolo deve ammetterlo; da zero, il CSV arriva già con `listino`, che il vincolo vecchio
respingerebbe. Il vincolo largo in `00_schema` regge tutti e due i casi, lo stretto nasce in `90_end`, dopo il
seed (la regola della memoria «CHECK su riga di seed: 90_end»).

### 16.3 Le scelte dentro il giro (da guardare, Tid)

1. **Il vocabolario delle vie è scritto due volte, dichiarato.** «Una sede» (D21) non è raggiungibile senza
   riscrivere il risolutore: un CHECK non legge il corpo di una funzione, e il risolutore è una catena di
   `IF p_modo = …` di 34 rami (DEFINER, toccato anche dall'altro cantiere). La sede del significato resta il
   risolutore; il CHECK è il suo specchio, e il pgTAP `test-processi-bersagli-via-modi-del-risolutore-v1` (1) li
   confronta testo contro testo, come il presidio di `commesse_push_log`. Alternativa scartata: un
   `script.fn_emittente_vie()` IMMUTABLE letto dal CHECK, che toglie la copia dal CHECK ma la sposta in una
   terza sede, perché il risolutore resterebbe com'è.
2. **Tutti i modi del risolutore sono vie dichiarabili**, non solo listino e magazzino: la via è per
   definizione il primo argomento del guard, e il guard accetta ogni modo.
3. **La regola «la via dichiarata è quella del guard montato»** è nel test 6 dello stesso file, come presidio
   sul seed (oggi le undici righe coincidono). Proposta per il giro 9, che riapre la vista: portarla in
   `vw_processi_dominio_senza_difesa` come motivo «guard montato con un'altra via», così la vede anche il
   panorama.
4. **D6, le firme passano a `name`.** Con `%TYPE` del catalogo la firma cambia, quindi DROP e CREATE invece di
   `CREATE OR REPLACE`. Il presidio dell'overload: dopo l'estratto c'è una sola funzione per nome (§16.4).
5. **D6, il ritiro resta generico**: confronta l'array intero e non applica la grammatica ATTIVO, perché non è
   una funzione ATTIVO (schema e nome della funzione sono parametri). Quindi non è nel presidio 23.
6. **D53, i nomi del risultato.** `fn_find_file_usage` prende `fk_name` e `posizione` (senza, le righe di una
   chiave composita non si raggruppano) e `pk_column` diventa `referenced_column` (la FK può puntare a una
   UNIQUE). `fn_foreign_keys_info` cambia parametro (`tabella text` → `p_tabella regclass`) e risultato
   (tabelle `regclass`, colonne `name`, `posizione`). Nessun chiamante.
7. **D53, le partizioni.** Un clone di FK che ripete il vincolo padre dallo stesso lato non si mostra; una
   partizione chiesta da sola vede le FK che la vincolano.

**Decisioni di Tid (2026-11-07):**

* **Scelta 1 → no al doppio elenco: sede unica, si riscrive il risolutore.** La forma della riscrittura è in
  §16.9 e aspetta la conferma di Tid; finché non c'è, D21 non va all'apply.
* **Scelta 3 → accettata:** nel giro 9 `vw_processi_dominio_senza_difesa` prende il motivo «guard montato con
  un'altra via» (la regola oggi è il test 6 di `test-processi-bersagli-via-modi-del-risolutore-v1`).
* **Residuo del 10b (§16.8) → è un difetto da risolvere** nel giro 10b, con D17.

### 16.4 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* **L'estratto nell'ordine di Liquibase** (`-28` … `-31`, `-33`, `-34`, la riga del CSV simulata da un
  UPDATE, poi il `-32`), con le tre preCondition eseguite come controllo: passa intero su scratch e dbdev. Dopo,
  una sola funzione per ognuno dei cinque nomi, con la firma nuova; dopo il ROLLBACK, i due database puliti
  (firme vecchie, riga 2 a `padre`, vincolo vecchio).
* **Il runner ATTIVO vero, con l'estratto:** i due riconoscimenti trovano tutti gli 833 trigger ATTIVO dello
  scratch (prima: nessuno); `fn_run_automations_attivo('CI', NULL, …)` in dry run e poi vero non ricrea, non
  toglie e non aggiunge nessun trigger.
* **`plpgsql_check`** su `fn_drop_triggers_by_function_args` e `fn_run_automations_attivo`: nessun avviso.
* **pgTAP** (scratch, da owner, con e senza l'estratto in testa):

| File | Con | Senza |
| --- | --- | --- |
| nuovo `dbops/test-trigger-attivo-riconoscimento-per-funzione-v1` (15, runner app: trigger su TEMP sue) | 15/15 | 7/15: le firme e i riconoscimenti rossi; come app la fixture si costruisce |
| nuovo `dbops/test-processi-bersagli-via-modi-del-risolutore-v1` (6, runner owner come `test-processi-registro`) | 6/6 | 1/6 |
| nuovo `dbops/test-fk-info-su-pg-constraint-v1` (9, runner app: TEMP sue, anche partizionate) | 9/9 | si ferma al 1 (la firma non esiste); come app la fixture si costruisce |
| `dbops/test-guard-attivo-grammatica-e-codici-v1` (presidio 23 esteso ai due riconoscimenti) | 23/23 | rosso il 23 |
| `dbops/test-processi-registro` (16), `dbops/test-presidi-debito-dichiarato` (8), `dbops/test-trigger-attivo-orfani-v1` (10), `dbops/test-automazione-attivo-eccezioni-v1` (8), `dbops/test-trgfn-prevent-deactivate-if-children-pdp` (13), `config/test-trgfn-prevent-deactivate-if-children-toponomastica` (9), `pratiche/test-guard-non-obsolete-parent-v1` (10), `rls/test-rls-fatture-stampa-coda-write-guard` (6), `vendite/test-event-log-deriva-scope` (7), `vendite/test-preventivo-scadenza-v1` (19) | tutti verdi | tutti verdi |
| presidi: `dbops/test-riferimenti-morti-v1` (12), `dbops/test-security-definer-search-path-v1` (5), `script/test-catalogo-messaggi-errore-completo` (7), `dbops/test-corpo-funzione-senza-commenti-v1` (15), `dbops/test-punti-canale-campo-v1` (18) | tutti verdi | tutti verdi |
| `dbops/test-guard-attivo-occhi-del-proprietario-v1` (runner app) | da owner 2, 6, 7, 8 rossi per costruzione, come dichiarato | uguale |

* Guardrail dei changelog, del preambolo pgTAP, dei letterali, del fuso e del v1 congelato verdi; header di
  licenza a posto. Il pre-commit è rosso solo su `check-i18n-keys` per `vendite.righe.articolo_reason.obsoleto`,
  come ai giri 2 e 3 (cantiere degli articoli).
* B-7: il giro non porta codici nuovi né nuovi punti di sollevamento.

### 16.5 Per Tid

1. Apply su dbdev e sullo scratch: `20261107-28`, `-29`, `-30`, `-33`, `-34`.
2. pgTAP **come app**: i due nuovi (`dbops/test-trigger-attivo-riconoscimento-per-funzione-v1`,
   `dbops/test-fk-info-su-pg-constraint-v1`), `dbops/test-guard-attivo-grammatica-e-codici-v1`, `dbops/test-processi-registro`,
   `dbops/test-presidi-debito-dichiarato`, `dbops/test-trigger-attivo-orfani-v1`,
   `dbops/test-automazione-attivo-eccezioni-v1`, `dbops/test-trgfn-prevent-deactivate-if-children-pdp`,
   `dbops/test-riferimenti-morti-v1`, `dbops/test-security-definer-search-path-v1`.
3. Il commit (giro 4 e baseline B-7, §16.6), poi il via al blocco 4b (§16.9).

**Esito (Tid, 2026-11-07):** apply su dbdev e sullo scratch, pgTAP di §16.5 verdi. Via al blocco 4b dato.

### 16.6 La baseline B-7 (§14.4 e §15.5), 2026-11-07

Su richiesta di Tid. Fotografia di `scripts/sql/codici_errore_famiglie_snapshot.sql` come app, in sola lettura:
scratch e dbdev rispondono uguale. In `db/baseline-codici-errore-famiglie.tsv` si sono cambiate **solo le sette
righe di questo brief**, con i valori misurati, senza `--update` (che avrebbe scritto anche le righe degli altri
cantieri):

| Codice | Prima | Dopo |
| --- | --- | --- |
| `E_ATTIVO_REQUIRE` | `NOT_FOUND`, 6 | — (esce: lo solleva solo il generatore, che la misura non legge) |
| `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` | `NOT_FOUND`, 5 | — (esce) |
| `E_DBOPS_CHIAMATA_NON_VALIDA` | — | `PARAMETRO`, 15 |
| `E_GENERICO` | `ENUM,NOT_FOUND,PARAMETRO`, 31 | stesse famiglie, 9 |
| `E_MERGE_RIGHE_DOPPIE` | — | `ECCEZIONE`, 2 |
| `E_PIPELINE_TASK_HANDLER_NOT_FOUND` | — | `NOT_FOUND`, 2 |
| `E_TRIGGER_ARGOMENTI_INVALIDI` | `ECCEZIONE,ENUM,VALORE_ATTESO`, 5 | stesse famiglie, 10 |

⚠️ `E_GENERICO` scende a 9 punti, non a 25: i sei del giro 2 e gli altri di altri cantieri. I punti sono
informativi (il confronto guarda le famiglie): si è scritto il valore misurato, l'unico che corrisponde a un
database. Il confronto dopo l'aggiornamento: nessun accumulo, nessun ristretto. Resta un «rientrato»,
`E_ARTICOLO_ONERE_NATURA_MERCE`, e restano fuori dalla baseline le righe nuove `E_DDT_EMISSIONE_SOLO_ONERI`,
`E_DDT_ONERE_NON_FATTURABILE`, `E_DDT_TRASPORTO_NON_DOVUTO`, `E_SORG_*` e i punti di `E_CONFIG_MANCANTE` e
`E_SORG_CONF`: sono dei cantieri degli articoli e della sorgente, e le allineano loro.

### 16.7 Doc

* Pagine `manual/` riscritte sul comportamento nuovo: `fn_trigger_exists_block_by_args`,
  `fn_trigger_exists_require_by_args`, `fn_drop_triggers_by_function_args`, `fn_foreign_keys_info`,
  `fn_find_file_usage`; aggiornate `fn_run_automations_attivo` (la strategia di esistenza) e
  `processi_bersagli` (le vie sono i modi del risolutore, il doppio elenco e il suo presidio).
  ⚠️ Quest'ultima è stata riportata com'era quando D21 è passato al blocco 4b: si riscrive lì.
* Nessuna guida descriveva i difetti chiusi. Il drawer dei processi mostra la via com'è (`listino` al posto di
  `padre`): nessuna chiave da tradurre.

### 16.8 Residuo

* La regola «via dichiarata = guard montato» nel presidio dei processi: **giro 9** (decisione di Tid,
  2026-11-07).
* **Difetto, giro 10b (decisione di Tid, 2026-11-07).** Il ritiro per argomenti (`reconcile_on_change`) con la strategia `BY_FUNCTION` toglie i trigger con gli
  argomenti **nuovi**, non quelli con argomenti vecchi sullo stesso nome: se cambia la colonna attivo di un
  padre (override), il `CREATE` trova il nome preso e si ferma con `E_ATTIVO_REQUIRE`/`E_ATTIVO_BLOCK`. Oggi la
  strategia del seed è `BOTH`, che decide col nome e non ci arriva: allora il trigger resta con gli argomenti
  vecchi, ed è lo stesso difetto visto dall'altro lato. Si risolve con la strategia di esistenza (D17), giro 10b.

### 16.9 D21, la sede unica: il registro dei modi (proposta, da confermare)

**Il fatto, sul corpo del 2026-11-07.** I 34 rami di `script.fn_resolve_emittente_fiscale_id` hanno tutti la
stessa forma: leggono una tabella per chiave (`id`, tranne `soggetto_ruolo`) e trovano l'emittente in uno di tre
modi:

| Forma | Che cosa fa | Modi |
| --- | --- | --- |
| radice PK | la colonna `emittente_fiscale_id` della tabella | fiscale (la tabella è `emittenti_fiscali`), magazzino, ddt, ordine, preventivo, offerta, contratto, reso, asset, pratica, documento_generato |
| radice SR | la colonna del soggetto-ruolo, unita a `emittenti_fiscali` | soggetto_ruolo (chiave `soggetto_ruolo_id` su `emittenti_fiscali`), fattura, contabile, listino, commessa, lotto |
| salto | una FK verso la testata, che ha il suo modo | le righe dei documenti, listino_versione, commessa_attivita, attivita_fatturabile, fattura_sdi, evento_asset, inventario, movimento, rettifica, trasferimento (`magazzino_id_from`), flusso; ente_incasso fa due salti, con un modo intermedio sul conto bancario |

**La proposta.**

1. Un registro `script.emittente_modi` (modo PK; tabella; colonna chiave; forma `PK`/`SR`/`SALTO`; colonna
   dell'emittente o della FK; modo padre per i salti, FK su sé stesso), scritto da un CSV: è **la** sede del
   vocabolario e del significato di ogni modo.
2. Il risolutore non si scrive più a mano: lo **genera** una funzione dal registro, con lo stesso SQL statico di
   oggi (un ramo per modo, i salti appiattiti in JOIN). Stessa velocità: lo chiamano 101 policy RLS e 41
   funzioni, e una versione a SQL dinamico le rallenterebbe tutte. Il registro cambia → il risolutore si rigenera.
3. `processi_bersagli.emittente_via` prende una FK verso il registro al posto del CHECK: `-31` e `-32` si
   riscrivono (non sono applicati), il pgTAP di confronto testo contro testo esce, e al suo posto un pgTAP
   prova che il risolutore generato risponde, per ogni modo, come quello di oggi (costruendo i casi).
4. Decisione del 2026-10-18 (D-3b-2, «una strada sola: il modo del risolutore»): la proposta la **completa**, non
   la revoca: la strada resta il risolutore, cambia chi lo scrive.

**Che cosa costa, e i nodi da decidere.**

* **Da zero, l'ordine.** Policy e funzioni che chiamano il risolutore nascono in `00_schema`/`20_code`, il CSV in
  `80_data`. Il registro deve quindi nascere col suo contenuto prima di loro (righe di sistema nello stesso
  changeSet della tabella, o in `70_dati_sistema`) e il CSV in `80_data` resta il mirror; oppure il risolutore a
  mano resta fino a `90_end`, dove si rigenera. Da scegliere nel disegno di dettaglio.
* **I due gemelli.** `script.fn_resolve_emittente_sr_id` (lotto, commessa, fattura, in convenzione SR) è la
  stessa domanda con un'altra risposta: il registro può generare anche quello, o restare fuori.
* **I 36 adattatori** `script.fn_scope_ef_whitelist_via_<modo>` sono un terzo elenco dei modi, per nome di
  funzione. Generarli dal registro è la stessa regola; si può fare qui o in un giro suo.
* **L'altro cantiere** (`brief-db-sorgente-documento-e-riga`) legge il risolutore (modi `movimento`,
  `evento_asset`) ma oggi non lo modifica: il lavoro va concordato con lui solo se aggiunge un modo.
* Il risolutore è DEFINER e regge la separazione fra aziende: la generazione è un DDL di una funzione di
  sicurezza, da provare con le policy (pgTAP di perimetro come app) prima dell'apply.

**Deciso (Tid, 2026-11-07): registro + risolutore generato, nel blocco 4b dopo l'apply del giro 4.**
**Perimetro (Tid, 2026-11-07):** il registro genera anche il gemello SR (`script.fn_resolve_emittente_sr_id`),
che oggi riscrive la strada di tre modi: diventa la stessa strada con la colonna del soggetto-ruolo in fondo, per
tutti i modi. I 36 adattatori `fn_scope_ef_whitelist_via_*` restano fuori: non ripetono la strada, solo il nome
del modo; un pgTAP controlla che ognuno nomini un modo del registro. Il loro ritiro, se servirà, è un giro suo
con il team BE (31 funzioni DB e 3 file del backend li chiamano).

Tolti dal giro 4 e tenuti per il 4b: `-31`, `-32`, `test-processi-bersagli-via-modi-del-risolutore-v1`, e anche
la riga del CSV `padre` → `listino`: senza il `-31` il vincolo di oggi non ammette `listino`, e l'apply si
fermerebbe sul CSV (la prima stesura di questo paragrafo diceva il contrario, ed era sbagliata). Pagina
`processi_bersagli` riportata com'era. Dopo il ritiro, l'estratto ridotto (`-28`, `-29`, `-30`, `-33`, `-34`) e i
pgTAP di §16.4 rifatti: verdi.

## 17. Blocco 4b — il registro dei modi dell'emittente (D21, M18), 2026-11-07

**Via di Tid (2026-11-07)**, dopo l'apply del giro 4 (pgTAP verdi). Decisioni di §16.9: registro + risolutore
generato con SQL statico; il registro genera anche il gemello SR; i 36 adattatori restano fuori, con un presidio.

### 17.1 Che cosa è stato scritto

| changeSet | Oggetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261107-31` | nuova `dbops.emittente_modi` | il registro: modo (PK), tabella, colonna chiave, forma `PK`/`SR`/`SALTO`, colonna, modo padre (FK su sé stessa, differita); CHECK su forma e padre |
| `00_schema/dbops/20261107-32` | `dbops.processi_bersagli` | via il CHECK `chk_processi_bersagli_via` |
| `20_code/dbops/20261107-35` | nuovo `dbops.trgfn_emittente_modi_solo_migrazione` + due trigger | il registro lo scrive solo il proprietario (`script.fn_is_proprietario_tabella`); righe e TRUNCATE; `E_EMITTENTE_MODI_NON_SCRIVIBILE` |
| `20_code/dbops/20261107-36` | nuovo `dbops.fn_risolutore_emittente_corpo(boolean)` | il corpo dei due risolutori dal registro, dopo il controllo (tabelle, colonne, catene); `E_EMITTENTE_MODI_INVALIDO` con tutti i problemi insieme |
| `20_code/dbops/20261107-37` | nuovo `dbops.fn_genera_risolutori_emittente()` | riscrive `script.fn_resolve_emittente_fiscale_id` e `script.fn_resolve_emittente_sr_id` solo se corpo o COMMENT sono diversi; firma ancorata (`%TYPE`), stessi tipi |
| `80_data/changelog/20261107-38` + `sql/dbops/emittente_modi.csv` | seed del registro | i 34 modi di oggi più `conto_bancario` (il passo intermedio di `ente_incasso`) |
| `80_data/sql/dbops/processi_bersagli.csv` | riga 2 | `padre` → `listino` |
| `90_end/20261107-39` | convergenza, `runAlways` | `SELECT dbops.fn_genera_risolutori_emittente()` a ogni migrate, dopo il seed |
| `90_end/20261107-40` | FK `fk_processi_bersagli_emittente_via` → `dbops.emittente_modi`, indice | con il controllo che nomina il bersaglio fuori vocabolario; COMMENT di tabella e colonne riscritti (M18) |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | due codici | `E_EMITTENTE_MODI_INVALIDO` (TECNICO, 1453), `E_EMITTENTE_MODI_NON_SCRIVIBILE` (NON_PERMESSO, 1454) |

pgTAP: nuovi `dbops/test-emittente-modi-registro-v1` (16, runner owner) e `dbops/test-emittente-modi-solo-migrazione-v1`
(4, runner app); `dbops/test-processi-registro` test 6 (la FK al posto del CHECK, su una tabella che non è già un
bersaglio: col CHECK parlava prima il vincolo, ora parlerebbe l'unicità).

### 17.2 L'ordine, da zero e su dbdev

Policy e funzioni che chiamano i risolutori nascono in `00_schema`/`20_code` con i risolutori scritti a mano; il
registro nasce vuoto in `00_schema`, il seed lo riempie in `80_data`, e in `90_end` il `-39` sostituisce i corpi
scritti a mano con quelli generati, con le stesse risposte. Il CHECK delle vie esce in `00_schema` (`-32`), la FK
entra in `90_end` (`-40`): in mezzo il CSV dei bersagli scrive `listino`, che il CHECK di prima non ammetteva. Da
quel momento un corpo scritto a mano (un changeSet di `20_code` di un altro cantiere) torna quello del registro al
migrate dopo: la regola è nel COMMENT delle due funzioni, nell'intestazione del corpo generato e in
`linee-guida-sql.md` §10.

### 17.3 Le scelte dentro il blocco (da guardare, Tid)

1. **Il registro in `dbops`**, accanto a `processi_bersagli` (lo schema dei registri); i risolutori restano in
   `script`, coi nomi di oggi.
2. **Un modo nuovo, `conto_bancario`**, per spezzare in due salti la strada di `ente_incasso`, che era l'unica con
   due JOIN in un ramo. È un modo vero (il conto bancario di un soggetto-ruolo), quindi è anche dichiarabile e
   chiamabile.
3. **Il gemello SR conosce ora tutti i modi**, non tre. Per le radici `SR` copia la colonna senza controllare che
   sia un emittente, come faceva per `lotto`, `commessa` e `fattura`; per le radici `PK` passa dall'emittente
   fiscale.
4. **Il corpo generato tiene la catena `IF p_modo = … ELSIF`** di oggi (non un `CASE`): i presidi che leggono il
   corpo dei risolutori non cambiano lettura, e la B-7 non si muove di famiglia.
5. **Il registro lo scrive solo il proprietario, con un guard**: è codice della funzione che separa le aziende, e
   il giro dei grant di `ci_apply` ridà all'applicazione i privilegi sulle tabelle di `dbops`. Il TRUNCATE lo ferma
   già la FK dei bersagli; il trigger resta per quando nessuno riferisce un modo.
6. **Due codici nuovi** invece di riusarne: nessuno esistente diceva «registro incoerente» o «scrittura non dal
   migrate», e riusarne uno avrebbe aggiunto una famiglia nella B-7.
7. **Un modo tolto dal CSV resta nella tabella** (il loader non cancella): il ritiro di un modo è un changeSet suo,
   dopo il censimento di guard e bersagli che lo nominano. È scritto nel loader e nella pagina del registro.

### 17.4 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* **L'estratto nell'ordine di Liquibase** (`-31`, `-32`, `-35` … `-37`, i quattro CSV simulati da INSERT/UPDATE
  generati dai CSV con `NULL` come il loader, `-39`, `-40`): passa su scratch e dbdev. 35 modi caricati; il
  generatore riscrive le due funzioni, e chiamato una seconda volta non riscrive niente. Una sola funzione per nome.
  Dopo il ROLLBACK i due database sono puliti (registro assente, riga 2 a `padre`, CHECK vecchio, corpo del
  risolutore con lo stesso md5).
* **Equivalenza sulla popolazione di dbdev** (fatto datato, 2026-11-07; la regola la provano i test costruiti):
  per ogni modo, ogni riga della sua tabella (10.031 in tutto; `asset`, `ente_incasso`, `evento_asset`,
  `fattura_sdi`, `trasferimento` senza righe), risolutore scritto a mano contro generato: **nessuna differenza** né
  per il fiscale né per i tre modi del gemello; e il soggetto-ruolo generato coincide sempre col soggetto-ruolo
  dell'emittente fiscale. Sullo scratch le tabelle sono vuote.
* **`plpgsql_check`** sui due risolutori generati, sul costruttore, sul generatore e sul guard: solo l'avviso
  «STABLE che chiama una VOLATILE» (`fn_log_and_raise_error`), come nei giri 2 e 3.
* **pgTAP** (scratch, da owner, con e senza l'estratto in testa):

| File | Con | Senza |
| --- | --- | --- |
| nuovo `dbops/test-emittente-modi-registro-v1` (16) | 16/16 | si ferma al 3 (il registro non esiste) |
| nuovo `dbops/test-emittente-modi-solo-migrazione-v1` (4, runner app) | da owner 1-3 rossi per costruzione (il proprietario scrive), 4 verde | si ferma (la tabella non esiste) |
| `dbops/test-processi-registro` (16) | 16/16 | rosso il 6 (la FK non c'è) |
| `script/test-catalogo-messaggi-errore-completo` (7) | 7/7, con le due righe dei codici simulate | 7/7 |
| `dbops/test-presidi-debito-dichiarato`, `test-riferimenti-morti-v1`, `test-security-definer-search-path-v1`, `test-corpo-funzione-senza-commenti-v1`, `test-punti-canale-campo-v1`, `test-vw-codici-errore-valore-atteso`, `script/test-rubinetto-primo-motivo-v1`, `rls/test-rls-fatture-stampa-coda-write-guard`, `vendite/test-event-log-deriva-scope` | tutti verdi | tutti verdi |
| regressione: i 13 file `rls/*ef-whitelist*`, `rls/test-rls-perimetro*`, `script/test-fn-scope-*`, e altri 100 di `rls/`, `magazzino/`, `pratiche/` | esito identico a «senza», file per file | — |

* **B-7 con l'estratto:** nessuna famiglia nuova; `E_DBOPS_CHIAMATA_NON_VALIDA` 15 → 16 punti e
  `E_PARAMETRO_INVALIDO` 255 → 256, stesse famiglie; i due codici nuovi la misura non li legge. La baseline non
  cambia.
* Guardrail dei changelog, del preambolo, dei letterali, del fuso, del v1 verdi; header di licenza a posto;
  pre-commit rosso solo su `check-i18n-keys` (cantiere degli articoli), come prima.

### 17.5 Per Tid

1. Apply su dbdev e sullo scratch: `20261107-31`, `-32`, `-35` … `-40`, `emittente_modi.csv`, `processi_bersagli.csv`,
   `codici_errore.csv`, `messaggi_errore.csv`.
2. pgTAP **come app**: `dbops/test-emittente-modi-solo-migrazione-v1` (i quattro verdi solo come app),
   `dbops/test-emittente-modi-registro-v1` (gira da owner per il marcatore), `dbops/test-processi-registro`,
   `script/test-catalogo-messaggi-errore-completo`, `vendite/test-event-log-deriva-scope`, e i `rls/` del perimetro
   (`rls/test-rls-*ef-whitelist*`, `rls/test-rls-perimetro*`): il blocco riscrive la funzione che leggono.
3. Il commit del giro 4, del blocco 4b e della baseline B-7; poi il via al giro 5.

**Esito (Tid, 2026-11-07):** apply su dbdev e sullo scratch, pgTAP di §17.5 verdi, le scelte di §17.3 restano
come sono. Giro 4, blocco 4b e baseline B-7 committati insieme dalla sessione DB, solo i file di questo cantiere (le
righe dell'altro cantiere nei due CSV dei codici restano fuori dal commit). Il giro 4 è chiuso.

### 17.6 Doc

* Pagine `manual/` nuove: `dbops/emittente_modi`, `fn_risolutore_emittente_corpo`, `fn_genera_risolutori_emittente`,
  `trgfn_emittente_modi_solo_migrazione`, `script/fn_resolve_emittente_sr_id`; riscritta
  `script/fn_resolve_emittente_fiscale_id` (i modi rimandano al registro: l'elenco a mano era una quinta copia);
  aggiornata `dbops/processi_bersagli` (le vie sono i modi del registro). Voci negli indici di `dbops` e `script`.
* `linee-guida-sql.md` §10: un modo nuovo è una riga del registro, mai un ramo scritto a mano.

### 17.7 Residuo

* La regola «via dichiarata = guard montato» resta il test 14 di `test-emittente-modi-registro-v1` fino al giro 9,
  che la porta in `vw_processi_dominio_senza_difesa` (§16.8).
* I 36 adattatori `script.fn_scope_ef_whitelist_via_*` restano scritti a mano; il test 13 controlla che ogni modo che
  nominano sia nel registro.
* La pagina `script/manual/trgfn_guard_emittente_scope.md` non elenca i modi, ma ha uno stile vecchio (marcatori di
  revisione): si rivede col giro dello schema `script`, non qui.

## 18. Giro 5 — la coda lavori sotto RLS (Q14 ③, D9), 2026-11-07

**Via di Tid (2026-11-07)**, coi numeri `20261107-51` … `-58` e `%TYPE`. Il giro si fa in due blocchi: il **5a**
(questo) prepara tutto ciò che la RLS chiede e corregge D9; il **5b** accende la RLS quando il drenatore del backend
lavora per azienda (BE10), e gli utenti tecnici esistono.

### 18.1 Le decisioni di Tid, prese nel giro (2026-11-07)

1. **Il drenatore lavora un'azienda alla volta**, come `draina_coda_stampa`: con l'utente tecnico di quell'azienda.
   I lavori SISTEMA li vede col ramo dell'identità di processo della policy, come `config.email_log`. Nessun ramo che
   gli mostri tutte le aziende: sarebbe la porta che R-2 (2026-09-05) ha chiuso.
2. **`fn_accoda_lavoro` diventa SECURITY DEFINER.** ⚠️ La domanda portava una premessa sbagliata, corretta prima della
   conferma: i job di pgAgent **non** subiscono la RLS, perché `zeroerp_job` chiama procedure DEFINER e accoda come
   proprietario. La DEFINER resta per due ragioni vere: sotto la policy, dopo un `ON CONFLICT` senza riga, una porta
   INVOKER non distingue «il vivo si è chiuso» (si riprova) da «il vivo c'è ma è di un'altra azienda» (la correzione
   di D9 girerebbe in tondo); e un operatore che accoda un lavoro SISTEMA sarebbe respinto dalla `WITH CHECK`.
3. **`draina_coda_lavori` passa a DOMINIO.** ⚠️ **Revoca** la decisione del 2026-09 in
   `work-done/brief-db-processi-automatici-identita-e-perimetro.md` §2.5 («`MANUTENZIONE` (è il worker, non il
   lavoro)»), presa quando la coda non aveva un perimetro. Con la coda sotto RLS il worker scrive righe che
   appartengono a un'azienda, che è la definizione di DOMINIO della guida (`processi-automatici-classe-e-identita`
   §3); e `script.fn_crea_utente_tecnico` dà un utente tecnico solo a un processo di DOMINIO.
4. **Un lavoro, un'azienda.** Un lavoro OPERATORE appartiene all'emittente attivo di chi lo accoda; un lavoro che
   copre più aziende non esiste: in modalità globale se ne accoda uno per azienda. Un lavoro SISTEMA non ha azienda.

### 18.2 Che cosa è stato scritto (blocco 5a)

| changeSet | Oggetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261107-51` | `dbops.coda_lavori` | nasce `emittente_fiscale_id` (FK → `anagrafiche.emittenti_fiscali`), riempita dallo scope per le righe di oggi, con un censimento che **ferma** il changeSet se un lavoro OPERATORE non ha azienda o ne nomina una che non esiste; `chk_coda_lavori_run_as_emittente` (OPERATORE ⇔ azienda) e `chk_coda_lavori_emittente_dallo_scope` (colonna = `scope->>'emittente_attivo_id'`); COMMENT di tabella riscritto |
| `20_code/script/20261107-52` | nuova `script.fn_scope_coda_lavori_perimetro` | la regola, pura e incorporata: OPERATORE se l'azienda è nel perimetro, SISTEMA al super admin e al drenatore, altro no, mai `NULL` |
| `20_code/dbops/20261107-53` | `dbops.fn_accoda_lavoro` | SECURITY DEFINER, `search_path` fissato, esecuzione tolta a `PUBLIC` e data a `zeroerp_app`; firma e `RETURNS` a `%TYPE`; scrive l'azienda dallo scope (`E_CODA_LAVORO_SENZA_EMITTENTE`); da una sessione dell'applicazione: OPERATORE solo a proprio nome e nel proprio perimetro (`E_CODA_SCOPE_ALTRUI`), vivo con la stessa chiave restituito solo se visibile (`E_CODA_CHIAVE_ALTRUI`); **D9**: il ciclo dell'upsert |
| `20_code/dbops/20261107-54` | policy `rls_coda_lavori_ef_perimetro` | `FOR ALL`, `WITH CHECK = USING`, chi guarda in tre sottoquery (super admin, drenatore, perimetro); **inerte**: nessun `ENABLE` |
| `20_code/dbops/20261107-55` | `dbops.vw_coda_lavori_da_guardare` | `security_invoker = true`, come la gemella della coda stampa |
| `20_code/dbops/20261107-56` | nuovo `dbops.fn_pgtap_scope_operatore` | helper di fixture: lo scope di chi è in sessione, con un'azienda del suo perimetro |
| `80_data/sql/dbops/processi.csv` | `draina_coda_lavori` | classe DOMINIO, descrizione |
| `80_data/sql/dbops/processi_bersagli.csv` | riga 53 | `dbops.coda_lavori`, via `fiscale`, colonna `emittente_fiscale_id`, `debito_dichiarato = true` (§18.4 punto 3) |
| `80_data/sql/dbops/rls_perimetro_debito.csv` | riga 92 | `POLICY_INERTE` su `dbops.coda_lavori`, con la ragione |
| `80_data/sql/dbops/presidi.csv`, `presidi_testi.csv` | `vw_coda_lavori_da_guardare` | perimetro `DEFINER` con la nota; l'azione dice anche «l'azienda non ha l'utente tecnico del drenatore» |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | tre codici | `E_CODA_LAVORO_SENZA_EMITTENTE` (TECNICO, 1455), `E_CODA_SCOPE_ALTRUI` (NON_PERMESSO, 1456), `E_CODA_CHIAVE_ALTRUI` (TECNICO, 1457) |

pgTAP nuovi: `rls/test-rls-coda-lavori-perimetro-v1` (14, runner owner: arma la RLS dentro la transazione) e
`dbops/test-fn-accoda-lavoro-porta-v1` (16, runner app; i rami dell'applicazione si saltano da owner e viceversa).
Riscritte le fixture di `dbops/test-coda-lavori`, `test-coda-accoda-classe` e `test-vw-coda-lavori-da-guardare`
(scope di fantasia → `fn_pgtap_scope_operatore`); la funzione pura entra nelle economiche di
`script/test-policy-funzioni-cost-v1` e nella regex di `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1`.

### 18.3 Il censimento di chi tocca la coda

| Chi | Come | Dopo il 5a | Dopo il 5b (RLS accesa) |
| --- | --- | --- | --- |
| backend, endpoint che accodano | `fn_accoda_lavoro` come app, con l'identità della richiesta | ⛔ un lavoro senza emittente attivo è respinto (BE10 a) | invariato |
| sveglie pgAgent (`fn_accoda_chiusura_scadenze`, `fn_guardiano_digest`) | `zeroerp_job` → procedura DEFINER → porta, da proprietario | invariato: il roster dà già l'azienda | invariato: il proprietario non subisce la RLS |
| drenatore (`claim`, reaper, `mark_*`) | come app, oggi **senza identità** | invariato | ⛔ senza utente tecnico non vede niente (BE10 b) |
| interfaccia (elenchi, conteggi, annulla, rimetti in coda, archivia) | come app con l'identità della richiesta, filtro `scope_key` a mano | invariato | vede la sua azienda; BE9 |
| `vw_coda_lavori_da_guardare` | persona: come app; digest: `fn_conta_presidio` (DEFINER) | invariato | la persona vede il suo perimetro, il digest tutto |
| `trgfn_coda_archiviazione` | trigger, legge solo la riga | invariato | invariato |

### 18.4 Le scelte dentro il giro (da guardare, Tid)

1. ⚠️ **`vw_coda_lavori_da_guardare` diventa `security_invoker` (`-55`) e perimetro `DEFINER`.** Rivede la prima metà
   della Q14 ③ («la vista vede tutte le aziende di proposito, è `LIBERO`»), che diceva anche «dopo la RLS si
   rivaluta il perimetro». Il digest continua a contare tutte le aziende (passa da `fn_conta_presidio`); a cambiare è
   chi la **legge**: senza `security_invoker` la vista mostrerebbe a chiunque i lavori di tutte le aziende anche con la
   coda sotto RLS, cioè la separazione aggirata da una vista. È la forma della gemella della stampa. Se non va: si
   tolgono `-55` e la riga di `presidi.csv` **prima** dell'apply su dbdev (lo scratch li ha già).
2. **La colonna si chiama `emittente_fiscale_id`**, non `emittente_soggetto_ruolo_id` (regola del 2026-10-04 per le
   tabelle nuove): è la stessa azienda che lo scope cattura in forma fiscale, e il CHECK le tiene uguali; in forma SR
   sarebbe una seconda copia da tradurre e tenere coerente con un trigger. La policy usa il perimetro fiscale.
3. **Il guard di scrittura `script.trgfn_guard_emittente_scope` non si monta.** Respinge le scritture senza utente
   dentro una DEFINER, e i lavori di pgAgent arrivano proprio così: la chiusura per scadenza si fermerebbe. La difesa
   in scrittura è la porta (che fa lo stesso controllo) più la policy. Il bersaglio resta `debito_dichiarato` anche
   dopo il 5b: da decidere se `vw_processi_dominio_senza_difesa` (giro 9) debba riconoscere una porta DEFINER come
   difesa, o se il guard vada insegnato a riconoscere il proprietario.
4. **Un lavoro SISTEMA lo accoda anche un operatore**: non ha azienda, e la classe del processo già impedisce che un
   lavoro di dominio vada SISTEMA.
5. **Fuori dall'applicazione la porta si fida** (la raggiunge solo il proprietario). Non controlla che una sveglia
   accodi solo per gli utenti tecnici del suo processo: si potrebbe, se Tid lo vuole.
6. **La FK fa nascere il blocco sul padre** (automazione ATTIVO): un'azienda con lavori in coda non si spegne finché
   le righe ci sono. È lo stesso di `config.email_log`; l'archiviazione non basta, serve cancellare o la regola del
   cleanup.
7. **Un builder pgTAP nuovo** (`fn_pgtap_scope_operatore`): la regola «scope valido per la porta» si sarebbe
   ricopiata in sei file.
8. **Ogni utente tecnico del drenatore vede i lavori SISTEMA**: più giri per azienda se li contendono, e `SKIP LOCKED`
   li dà a uno solo.
9. **Le righe di oggi senza azienda non si inventano**: il `-51` si ferma e le nomina (§18.6 punto 1).

### 18.5 Le prove

Sullo scratch `zeroerp_ruoli`, prima dell'apply: da owner, l'SQL estratto dagli YAML nell'ordine di Liquibase, i CSV
simulati da INSERT/UPDATE generati dai CSV, `BEGIN … ROLLBACK`, scratch verificato pulito dopo. I rami della porta «da
sessione dell'applicazione» li ho provati facendo contare come applicazione l'owner, nella sola copia di prova
(`pg_has_role(…, 'zeroerp_owner', …)` nella porta e nel test): è una prova della logica, e la corsa vera come app è
venuta dopo. ⚠️ Alle 15:30 lo scratch è stato **migrato** con questi changeSet (insieme al blocco `-59` … `-69`
dell'altro cantiere): da lì in poi i test sono girati sullo scratch applicato, **come app** dove il runner lo chiede.

| File | Prima dell'apply (con l'estratto) | Scratch applicato |
| --- | --- | --- |
| nuovo `rls/test-rls-coda-lavori-perimetro-v1` (14) | 14/14 | 14/14 (owner) |
| nuovo `dbops/test-fn-accoda-lavoro-porta-v1` (16) | da owner 11 + 5 skip; con l'owner contato come app 15 + 1 skip | **come app** 15 + 1 skip (il 16 è del proprietario) |
| `dbops/test-coda-lavori` (57) | rosso nella fixture prima della correzione; poi 57/57 | 57/57 come app |
| `dbops/test-coda-accoda-classe` (7), `test-vw-coda-lavori-da-guardare` (7) | rossi prima della correzione (scope senza azienda); poi verdi | verdi |
| `test-coda-archiviazione`, `test-coda-tipi-canale-e-run-as`, `test-tx-id-coerenza-non-registrato`, `test-processi-accensione-v1`, `test-fn-accoda-chiusura-scadenze`, `test-fn-guardiano-digest`, `test-chiusura-scadenze-una-volta-al-giorno-v1`, `test-stati-check-scrittori-v1`, `maintenance/test-vw-job-run-da-guardare` | verdi, uguali a «senza» | verdi |
| `script/test-policy-funzioni-cost-v1` (4) | rosso il 2 (funzione nuova senza `COST` né misura); dopo la voce fra le economiche, verde | verde come app |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1`, `rls/test-rls-perimetro-scoperto`, `rls/test-rls-policies-structure`, `rls/test-rls-write-policies-structure`, `rls/test-rls-viste-security-invoker`, `script/test-catalogo-messaggi-errore-completo`, `dbops/test-security-definer-search-path-v1`, `test-postura-proprietario-rls-v1`, `test-catalogo-presidi-v1`, `test-conta-presidio-per-variante-v1`, `test-corpo-funzione-senza-commenti-v1`, `test-emittente-modi-registro-v1`, `test-presidi-debito-dichiarato`, `test-presidio-processi-testo-per-causa-v1`, `test-presidi-testi-v1`, `test-processi-coda-automatica`, `test-processi-registro`, `test-riferimenti-morti-v1`, `test-vw-codici-errore-*`, `test-vw-funzioni-check-codici-sotto-jit-v1`, `test-vw-processi-*`, `test-codice-maiuscolo-v1`, `test-audit-log-perimetro-scrittori-v1`, `test-vw-fatture-stampa-coda-da-guardare`, `test-guard-attivo-grammatica-e-codici-v1`, `config/test-codici-errore-*` | verdi, identici a «senza» | quelli rilanciati: verdi |

* **La funzione pura** è incorporata: 20.000 righe in 4,8-5,1 ms contro 3 ms del filtro vuoto (scratch, owner).
* **D9 non si costruisce in un pgTAP**: la finestra sta fra due istruzioni della stessa funzione, e un trigger
  scatta prima del controllo del conflitto. Il test 6 della porta presidia la forma del ciclo; gli esiti del
  conflitto (vivo restituito, vivo altrui respinto) li provano i test 10 e 14.
* **B-7** sullo scratch applicato: nessun accumulo nuovo; i due «rientrati» (`E_ARTICOLO_ONERE_NATURA_MERCE`,
  `E_SORG_FORMATO`) sono dell'altro cantiere. Per questo giro la baseline non cambia.
* **Presidi dopo il giro** (fatto datato, 2026-11-07): `vw_processi_dominio_senza_identita` mostra
  `draina_coda_lavori` sui due database, `vw_emittenti_non_serviti` le 4 aziende del dbdev: sono gli utenti tecnici
  che mancano, ed è il segnale giusto. `vw_processi_dominio_senza_difesa` mostra la coda come debito dichiarato.
* Pre-commit sui file del giro: rosso solo `check-i18n-keys` (chiave dell'altro cantiere), come prima.

### 18.6 Per Tid

1. **Prima del migrate, sul dbdev, la correzione dei dati** (il `-51` altrimenti si ferma). Fatto datato,
   2026-11-07: 137 lavori OPERATORE **chiusi** senza emittente attivo nello scope, nessuno vivo: 71 FATTURAZIONE_GIRO
   e 66 FATTURAZIONE_NUMERA, dal 2026-07-21 al 2026-10-26; 5 hanno un'azienda sola in `emittente_ids`, 132 sono
   dell'admin in modalità globale (tutte le aziende). Proposta: ai 5 si scrive l'azienda, i 132 si tolgono (nessuna FK
   e nessun blocco li trattiene):

   ```sql
   UPDATE dbops.coda_lavori
      SET scope = scope || jsonb_build_object('emittente_attivo_id', (scope -> 'emittente_ids' ->> 0)::bigint)
    WHERE run_as = 'OPERATORE'
      AND scope ->> 'emittente_attivo_id' IS NULL
      AND jsonb_typeof(scope -> 'emittente_ids') = 'array'
      AND jsonb_array_length(scope -> 'emittente_ids') = 1;

   DELETE FROM dbops.coda_lavori
    WHERE run_as = 'OPERATORE'
      AND scope ->> 'emittente_attivo_id' IS NULL
      AND stato NOT IN ('PENDING', 'IN_CORSO');
   ```

2. Apply su dbdev: `20261107-51` … `-56` e i CSV `processi.csv`, `processi_bersagli.csv`, `rls_perimetro_debito.csv`,
   `presidi.csv`, `presidi_testi.csv`, `codici_errore.csv`, `messaggi_errore.csv`. Lo scratch li ha già.
3. pgTAP **come app**: `dbops/test-fn-accoda-lavoro-porta-v1`, `dbops/test-coda-lavori`,
   `dbops/test-vw-coda-lavori-da-guardare`, `dbops/test-coda-*`, `script/test-policy-funzioni-cost-v1`,
   `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1`, `script/test-catalogo-messaggi-errore-completo`;
   da owner per marcatore: `rls/test-rls-coda-lavori-perimetro-v1`, `dbops/test-coda-accoda-classe`,
   `rls/test-rls-perimetro-scoperto`, `dbops/test-processi-registro`, `dbops/test-presidi-debito-dichiarato`.
4. ⚠️ **Dall'apply il giro di fatturazione dal cockpit in modalità globale si rompe** (`E_CODA_LAVORO_SENZA_EMITTENTE`)
   finché il BE non fa BE10 (a): da un'azienda scelta funziona.
5. Uno sguardo alle scelte di §18.4, soprattutto la 1 e la 3.
6. Quando il BE ha fatto BE10 (b): gli utenti tecnici di `draina_coda_lavori`, uno per azienda, con
   `script.fn_crea_utente_tecnico('draina_coda_lavori', '<sigla dell'azienda>')`; poi il via al blocco 5b.

**Esito (Tid, 2026-11-07):** dati del dbdev corretti, apply su dbdev e scratch, pgTAP verdi. Il primo migrate sul
dbdev si era fermato, come previsto, sul censimento del `-51` (i 137 id), senza lasciare niente a metà. Blocco 5a
committato dalla sessione DB, solo i file di questo cantiere. Restano BE10 e gli utenti tecnici (punti 4-6), poi il 5b.

### 18.7 Doc

* Pagine `manual/` riscritte: `dbops/coda_lavori` (di chi è un lavoro, chi vede quali righe), `dbops/fn_accoda_lavoro`
  (la porta DEFINER, l'azienda, il ciclo dell'upsert, i codici), `dbops/vw_coda_lavori_da_guardare` (chi legge che
  cosa). Nuove: `script/fn_scope_coda_lavori_perimetro`, `dbops/fn_pgtap_scope_operatore`. Voci negli indici di
  `dbops` e `script`.
* Guida `gestione-code-di-lavoro`: un lavoro di una persona appartiene a un'azienda sola, e si accoda solo a proprio
  nome. La visibilità per azienda entra nella guida col 5b, quando è vera.
* COMMENT nuovi o riscritti: tabella, colonna e vincoli della coda, la porta, la funzione di scope, la policy.

### 18.8 Il blocco 5b, e il residuo

* **5b** (`-57`, `-58`; se serve un terzo numero, lo chiede): `ENABLE ROW LEVEL SECURITY` su `dbops.coda_lavori`, con
  una preCondition sulla postura; la riga 92 di `rls_perimetro_debito` tolta; la decisione dichiarata dell'indice
  della FK nuova in `fk_index_policy` (checklist di `linee-guida-sql` §10.9); `test-rls-coda-lavori-perimetro-v1`
  senza l'`ENABLE` locale (test della postura armata); la guida con la visibilità per azienda. ⚠️ Con la RLS accesa
  cambiano i SQLSTATE di due test di `test-coda-lavori` (55 e 57: la `WITH CHECK` parla prima del CHECK); si
  rivedono nel 5b. ⚠️ Provato nel 5b: sono 54, 55 e 56 (§18.9).
* Il bersaglio della coda resta debito dichiarato finché non si decide §18.4 punto 3 (giro 9).
* Le note di `brief-be-fe-gestione-code-lavori-stampa` («RLS su `dbops.coda_lavori` = ondata futura») restano: è un
  brief chiuso, e questo giro è l'ondata.

### 18.9 Blocco 5b — la RLS accesa, scritto il 2026-11-07

**Via di Tid (2026-11-07)**, con S-BE-2 dentro e il terzo numero `20261108-08` (dato da Tid). Prima del via:
EMITEST servita (Tid, 2026-11-07; dbdev: `vw_emittenti_non_serviti` vuota per `draina_coda_lavori`), le scelte di
§18.4 guardate: **1 ok, 3 ok** (il debito di scrittura resta dichiarato fino al giro 9).

| changeSet / file | Oggetto | Che cosa |
| --- | --- | --- |
| `20_code/dbops/20261107-57` | `dbops.coda_lavori` | `ENABLE ROW LEVEL SECURITY`, senza `FORCE`. preCondition: la policy c'è ed è `FOR ALL`, la porta è DEFINER, nessuna postura sbagliata (tabella dell'app, `BYPASSRLS` all'app, `FORCE`: 0). Corregge il COMMENT di `coda_lavori_tipi.run_as_default` («worker BYPASSRLS», falso) |
| `80_data/changelog/20261107-58` + `fk_index_policy_coda_lavori_emittente.csv` | `dbops.fk_index_policy` | `fk_coda_lavori_emittente_fiscale` a **false**, dichiarata (§10.9): nessuna query dell'applicazione entra dall'azienda, la policy la passa a una funzione; come `config.email_log`. **Confermata da Tid** (2026-11-07): il costo è la lettura intera della coda quando un'azienda si spegne o si cancella, gesti di amministrazione; si passa a true con una riga del CSV se una query entrerà dall'azienda |
| `80_data/changelog/20261108-08` + `rls_perimetro_debito.csv` | `dbops.rls_perimetro_debito` | la riga 92 (`POLICY_INERTE`) esce dal CSV e, con una `DELETE` per id e coordinate, da dove c'è |
| `80_data/sql/dbops/coda_lavori_tipi.csv` | `ESEGUI_PROCESSO` | **S-BE-2**: `run_as_default` SISTEMA, descrizione con la ragione (chi preme è l'attore, `richiesto_da`) |
| `80_data/sql/dbops/processi.csv` | `avvio_manuale` | la descrizione diceva «CODA perché l'identità è la sua»: il lavoro è SISTEMA, chi preme è l'attore |

pgTAP cambiati:

* `rls/test-rls-coda-lavori-perimetro-v1` (14 → 15): l'`ENABLE` locale esce, resta il `FORCE` (il runner è il
  proprietario, che senza non subisce la policy); il nuovo 15 pretende la RLS accesa dal changeSet.
* `dbops/test-coda-lavori` (57): con la RLS cambiano **54, 55 e 56**, non 55 e 57 come diceva §18.8 (provato, sotto).
  54 e 56 girano con la veste del drenatore (un lavoro SISTEMA lo vede e lo scrive solo lui o il super admin), 55 è una
  riga OPERATORE della propria azienda: tutte e tre passano la policy e cadono sul CHECK, prima e dopo l'`ENABLE`.
  ⚠️ L'ordine della fixture è voluto: prima l'operatore, poi il drenatore senza contesto, poi l'operatore per id (in CI,
  senza operatori, il contesto senza argomento potrebbe scegliere l'utente tecnico appena nato).
* `dbops/test-coda-archiviazione` (18): la fixture e i test 15-16 scrivevano un lavoro SISTEMA da operatore, che la
  policy respinge (42501 al posto del CHECK): ora un lavoro OPERATORE della propria azienda. L'archiviazione non
  dipende dal `run_as`.
* `dbops/test-coda-tipi-canale-e-run-as` (6): vedi sotto, la regola 2 si restringe; il 5 pretende SISTEMA.

**Decisione di Tid nel blocco (2026-11-07): la regola fra canale e `run_as` vale per i `CODA` di `DOMINIO`.** S-BE-2
rompeva l'invariante «sotto un `CODA` il tipo è OPERATORE, è la definizione del canale» (decisa il 2026-09-14 in
`work-done/brief-db-avvio-manuale-di-un-processo` §8.3), perché `avvio_manuale` è `CODA` + `MANUTENZIONE`. La regola
**si restringe** e la decisione del 09-14 è **revocata in parte**: un `CODA` di `DOMINIO` tocca i dati di un'azienda e
vuole l'identità di chi accoda; un `CODA` di `MANUTENZIONE` può essere SISTEMA, con chi preme come attore nel payload. Il
rischio che il 09-14 nominava («l'audit perde chi ha premuto») resta coperto da `richiesto_da`. Riscritti test 2 e 5, il
COMMENT di `run_as_default`, le pagine `processi` e `coda_lavori_tipi`, la descrizione di `avvio_manuale`.

**Il debito della scelta 3 (§18.4), com'è dopo il 5b.** Con la RLS accesa la scrittura della coda è difesa due volte: la
`WITH CHECK` della policy per ogni scrittura dell'applicazione (UPDATE del drenatore e dell'interfaccia, un INSERT
diretto), e la porta DEFINER per gli accodamenti. Il proprietario non subisce né l'una né il guard, per scelta. Il
presidio `vw_processi_dominio_senza_difesa` però riconosce la difesa di scrittura **solo dal nome** del guard
`trgfn_guard_emittente_scope`: la coda resta lì come «write-guard mancante», `DEBITO_DICHIARATO`. Il debito è quindi del
**presidio**, non un buco: al giro 9 si sceglie se il presidio impari a riconoscere una policy `FOR ALL` con `WITH CHECK`
(più una porta DEFINER) come difesa, o se il guard impari a lasciar passare il proprietario e allora si monta.

#### 18.9.1 Le prove (scratch `zeroerp_ruoli`, prima dell'apply)

Da owner, l'SQL estratto dagli YAML nell'ordine del migrate (`-57`, `-58`, `20261108-08`), i CSV simulati,
`BEGIN … ROLLBACK`, scratch verificato pulito dopo (`relrowsecurity = false`). Le preCondition del `-57` come `SELECT`:
1, 1, 0.

* **Come subisce la RLS l'applicazione, prima dell'apply.** Da owner non si passa all'app nella stessa transazione: si
  arma `ENABLE` + `FORCE`. ⚠️ Il `FORCE` fa subire la policy anche alla porta DEFINER, che nella realtà non la subisce:
  i rossi dentro `fn_accoda_lavoro` (fixture di `test-coda-lavori`, test 6 di `test-coda-accoda-classe`) sono di questa
  simulazione. Per `test-coda-lavori` la RLS si è armata **dopo** la fixture: prima delle correzioni rossi 54, 55, 56;
  dopo, 57/57. `test-coda-archiviazione` rosso dalla fixture prima, 18/18 dopo (lì l'INSERT era diretto, non della
  porta: rosso vero).
* **Come app vera** (RLS spenta, la postura di oggi): `test-coda-lavori` 57/57, `test-coda-archiviazione` 18/18.
* Con l'SQL del blocco in testa, «senza → con»: `test-rls-coda-lavori-perimetro-v1` 7/15 → **15/15** (prima
  dell'apply è rosso per costruzione: `FORCE` senza `ENABLE` non arma niente); `test-coda-tipi-canale-e-run-as` 5/6 →
  **6/6**; identici e verdi: `test-rls-perimetro-scoperto`, `test-rls-viste-security-invoker`,
  `test-rls-policies-structure`, `test-rls-write-policies-structure`, `test-postura-proprietario-rls-v1`,
  `test-presidi-debito-dichiarato`, `test-processi-registro`, `test-catalogo-presidi-v1`, `test-coda-accoda-classe`,
  `test-indici-letture-trasversali-v1`, `test-policy-funzioni-cost-v1`,
  `test-scope-ef-perimetro-una-volta-per-istruzione-v1`, `maintenance/test-vw-job-run-da-guardare`,
  `test-fn-guardiano-digest`, `test-fn-accoda-chiusura-scadenze`, `test-chiusura-scadenze-una-volta-al-giorno-v1`,
  `test-coda-lavori`, `test-coda-archiviazione`. Con `ENABLE` + `FORCE`, da owner, verdi anche
  `test-fn-accoda-lavoro-porta-v1`, `test-processi-accensione-v1`, `test-vw-coda-lavori-da-guardare`, `test-tx-id-coerenza-non-registrato`.
* `test-guard-attivo-occhi-del-proprietario-v1` è rosso da owner (2, 6, 7, 8) con e senza il blocco: è del runner (il
  file non ha marcatore, gira come app: 9/9).
* Guardrail `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch` verdi; pre-commit
  sui file del blocco verde.

#### 18.9.2 Per Tid

1. Apply su dbdev e scratch: `20261107-57`, `-58` e `20261108-08`, con i CSV `fk_index_policy_coda_lavori_emittente.csv`
   (nuovo), `rls_perimetro_debito.csv`, `coda_lavori_tipi.csv`, `processi.csv`.
2. pgTAP **come app**: `dbops/test-coda-lavori`, `dbops/test-coda-archiviazione`, `dbops/test-coda-tipi-canale-e-run-as`,
   `dbops/test-fn-accoda-lavoro-porta-v1`, `dbops/test-vw-coda-lavori-da-guardare`, `dbops/test-processi-accensione-v1`,
   `dbops/test-tx-id-coerenza-non-registrato`; da owner per marcatore: `rls/test-rls-coda-lavori-perimetro-v1`,
   `rls/test-rls-perimetro-scoperto`, `dbops/test-postura-proprietario-rls-v1`, `dbops/test-coda-accoda-classe`,
   `dbops/test-presidi-debito-dichiarato`.
3. ⚠️ Dall'apply: un'azienda senza l'utente tecnico del drenatore non viene drenata (`vw_emittenti_non_serviti`), e
   un lavoro SISTEMA lo vedono solo super admin e drenatore.
4. **Al team BE, all'apply:** S-BE-2 è fatta → `core/tests/db/test_avvio_manuale_catalogo.py`
   (`test_tipo_esegui_processo`) va girato a SISTEMA; e **BE9**: il filtro di perimetro scritto a mano si può ritirare,
   lo fa la RLS.

**Esito (Tid, 2026-11-07):** apply su dbdev e scratch (`databasechangelog`: i tre changeSet `EXECUTED`; la coda ha
`relrowsecurity = true`, `relforcerowsecurity = false`; la riga 92 del debito non c'è più; `ESEGUI_PROCESSO` è SISTEMA),
pgTAP verdi. Blocco 5b committato dalla sessione DB. **Il giro 5 è chiuso.**

## 19. Giro 6 — i presidi che guardano il campo sbagliato (Q14 ④, ⑦), 2026-11-07

**Via di Tid (2026-11-07)** («intanto procedi», dopo la conferma dell'indice false), coi numeri dal `20261108-10` (il `-09`
è dell'altro cantiere). **Decisione di Tid nel giro:** le due viste dei lotti si rinominano in «congelati», perché il
criterio non è più `stato_lotto = COMPLETATO`. Nessun lettore in backend o frontend (censito).

### 19.1 Che cosa è stato scritto

| changeSet / file | Oggetto | Che cosa |
| --- | --- | --- |
| `20_code/vendite/20261108-10` | `vendite.vw_lotti_congelati_con_gruppi_in_errore` | DROP del presidio di dbops e di `vw_lotti_chiusi_con_gruppi_in_errore`, CREATE col nome nuovo: `stato_lotto = 'COMPLETATO'` lascia il posto a `NOT pre_fiscale` di `vw_lotti_fase` (lo stato ignoto cade qui); nasce la colonna `stato_codice_interno`; COMMENT di vista e di tre colonne |
| `20_code/dbops/20261108-11` | `dbops.vw_lotti_congelati_con_errori_da_guardare` | il lettore a catalogo col nome nuovo; aggiunge solo l'emittente |
| `20_code/vendite/20261108-12` | tre COMMENT | il guard del COMPLETATO, `vw_lotti_segnalazioni_summary` e `vw_lotti_fermi_da_guardare`: nominavano la vista vecchia o descrivevano la spartizione vecchia («sull'ignoto il lotto non compare» ora è coperto dai congelati). Nessun corpo cambia |
| `80_data/changelog/20261108-13` | catalogo dei presidi | DELETE della riga col nome vecchio in `presidi_cause`, `presidi_testi`, `presidi` (il loader non cancella; precedente: `20261104-17`) |
| `presidi.csv`, `presidi_testi.csv` | tre righe | ⑦: la riga dei lotti col nome e la nota nuovi, la nota dei lotti fermi riallineata. ④: `vw_codici_errore_forme_condizione` passa a `CANCELLO`, `presidiato_da` = il passo B-7 di `ci-validate` (via `scripts/sql/codici_errore_famiglie_snapshot.sql`), nota e testi riscritti |

* Il commento nel **corpo** di `vendite.fn_annulla_lotto_da_draft` nomina ancora il nome vecchio: è un fatto datato
  (2026-09-07, vero allora), e non si riscrive la funzione per un commento storico. Lo stesso per i commenti storici di
  `test-annulla-lotto-non-riscrive-stato-v1` e `test-lotti-attivita-stato-esecuzione-v2`.
* ④: il COMMENT della vista dice «una MISURA, non un cancello» e resta: parla del conteggio, che non è un verdetto; il
  cancello è il B-7, che la legge. Lo dicono la nota del presidio e la pagina `manual/`.
* I GRANT delle due viste nuove li danno i privilegi di default degli schemi (`zeroerp_app`): nessun GRANT nei changeSet.

pgTAP:

* `vendite/test-lotti-fermi-verdetto-a-db-v1` (21 → 24): i tre casi costruiti della ⑦ — 22 congelato col job
  IN_ESECUZIONE e un esito in ERRORE (il buco: solo nei congelati), 23 COMPLETATO in bozza con un esito in ERRORE da due
  ore (il doppione: solo nei fermi), 24 stato fiscale ignoto (nei congelati, con lo stato NULL).
* `vendite/test-annullamento-chiude-la-vita-v1` (17 → 18): D nasce DEFINITIVA (la porta dell'esito si vede su un lotto
  congelato); B, annullato dalla bozza, prima è fermo (6), dopo è ANNULLATA e assente (10); il 18 nuovo gli riapre un
  documento in errore e lo fa comparire: la vista non filtra gli annullati.
* `vendite/test-lotti-gruppi-esito` (13): il lotto dei test 11-12 nasce DEFINITIVA.

### 19.2 Le prove (scratch `zeroerp_ruoli`, prima dell'apply)

Da owner, l'SQL estratto dagli YAML nell'ordine del migrate (`-10`, `-11`, `-12`, i CSV simulati, `-13`), `BEGIN …
ROLLBACK`. Le due viste nuove sono vuote sullo scratch. «Senza → con»:

| File | Senza | Con |
| --- | --- | --- |
| `vendite/test-lotti-fermi-verdetto-a-db-v1` (24) | 20/24 | 23/24 — il 18 (cecità senza veste) è rosso da owner per costruzione, come senza |
| `vendite/test-annullamento-chiude-la-vita-v1` (18) | 5/18 | 17/18 — il 16 è il gemello del 18 di sopra: da owner la vista vede la riga (1, non 0) |
| `vendite/test-lotti-gruppi-esito` (13) | 10/13 | 13/13 |
| `test-annulla-lotto-non-riscrive-stato-v1`, `test-lotti-attivita-stato-esecuzione-v2`, `test-catalogo-presidi-v1`, `test-presidi-testi-v1`, `test-conta-presidio-per-variante-v1`, `test-presidi-debito-dichiarato`, `test-presidio-processi-testo-per-causa-v1`, `rls/test-rls-viste-security-invoker`, `test-vw-codici-errore-valore-atteso`, `test-vw-codici-errore-motivo-nominato` | verdi | verdi, identici |

Guardrail `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch` verdi; pre-commit sui
file verde.

### 19.3 Per Tid

1. Apply su dbdev e scratch: `20261108-10`, `-11`, `-12`, `-13` e i CSV `presidi.csv`, `presidi_testi.csv`.
2. pgTAP **come app** (i tre file di `vendite` girano come app; da owner il test della cecità è rosso per
   costruzione): `vendite/test-lotti-fermi-verdetto-a-db-v1`, `vendite/test-annullamento-chiude-la-vita-v1`,
   `vendite/test-lotti-gruppi-esito`, `vendite/test-annulla-lotto-non-riscrive-stato-v1`; e
   `dbops/test-catalogo-presidi-v1`, `dbops/test-presidi-testi-v1`, `dbops/test-conta-presidio-per-variante-v1`.
3. Dopo l'apply, un primo sguardo ai due presidi sul dbdev: i congelati con un esito in errore che oggi nessuno vedeva
   possono comparire (è il buco che si chiude, non un rosso del giro).
4. ⚠️ Nel working tree ci sono modifiche dell'altro cantiere su due pgTAP del giro 5 (`test-fn-accoda-lavoro-porta-v1`,
   `test-rls-coda-lavori-perimetro-v1`: `pg_temp.come` passa da `fn_pgtap_set_contesto_operatore`) e il `20261108-09`.
   Non sono di questo giro e non vanno nel suo commit. `test-coda-lavori` (giro 5b) imposta ancora
   `app.current_user_id` a mano in `pg_temp.veste`: se l'altro cantiere uniforma i builder, è un punto da includere.

### 19.4 Doc

* `dbops/manual/vw_lotti_chiusi_con_errori_da_guardare.md` → `vw_lotti_congelati_con_errori_da_guardare.md` (rinominata
  e riscritta: l'asse, la tabella dei due presidi, le porte, i test, la storia).
* `dbops/manual/vw_lotti_fermi_da_guardare.md` (il buco e il doppione documentati come fatti di prima, l'asse comune),
  `vendite/manual/vw_lotti_segnalazioni_summary.md`, `dbops/manual/vw_codici_errore_forme_condizione.md` (④), la guida
  `processi-automatici-classe-e-identita.md`.
* Gli indici degli schemi li rigenera `gen_db_docs.py` alla build della doc; la pagina auto-generata della vista di
  `vendite` nasce lì. Non c'è una pagina `manual/` di `vendite` per la vista: non c'era nemmeno prima.
* Nessuna ricaduta BE: `api_lotto_segnalazioni_summary` non descrive la spartizione, e nessun codice legge le due viste.

### 19.5 Chiusura (2026-11-07)

Tid ha applicato il giro 6 su dbdev e scratch (`20261108-10` … `-13`, `presidi.csv`, `presidi_testi.csv`) e lanciato
come app i pgTAP di §19.3: verdi. Le pagine auto-generate (le due viste nuove, le due ritirate, gli indici degli schemi
`dbops` e `vendite`, i COMMENT riscritti dal `-12`) le ha rigenerate Tid ed entrano nel commit del giro. Restano fuori
le modifiche dell'altro cantiere (§19.3 punto 4: il `20261108-09`, `test-builder-pgtap-vincoli-immediate-v1`, i due
pgTAP del giro 5 e le pagine auto-generate delle quattro fixture `fn_pgtap_*`). **Il giro 6 è chiuso.**

## 20. Giro 7 — promesse senza esecutore, ricerca dei lookup (D35, D36, D37, D57), 2026-11-07

**Via di Tid (2026-11-07)**, coi numeri dal `20261108-25` (il `-14` … `-24` sono dell'altro cantiere) e il promemoria
sul `%TYPE`.

### 20.1 Le decisioni di Tid, prese nel giro (2026-11-07)

1. **Il perimetro del presidio di D35/D37**: i tre marcatori che promettono un'automazione vera, cioè `tx_id`,
   `storicizza` e `cleanup_at`. Le tabelle note entrano in un registro del debito, con la ragione. `data_update` e
   `user_update` restano fuori dal criterio (residuo, §20.9).
2. **D57**: il tetto del backend cade (BE4: `p_limit` NULL); la ricerca e la paginazione del backend restano dove
   sono. Il DB aggiunge lo spareggio `id` all'`ORDER BY`, così `p_limit` e `p_offset` diventano onesti per chiunque.
   **`p_offset` resta**: con lo spareggio è corretto, e toglierlo a metà firma romperebbe la chiamata per posizione.
   La firma non cambia.

Il censimento che ha portato alle due domande è **struttura** (colonne e trigger letti sul catalogo dello scratch, il
2026-11-07), non popolazione. Fatti datati: le tabelle con `tx_id` fuori dall'ambito sono 17 di `dbops`, di cui 8 coi
trigger montati a mano. Con `data_update` e senza nessuno che lo riscriva ce ne sono circa 30 in `dbops` e 10 in `ui`.
`storicizza` fuori dall'ambito: solo `shop.ricevute` e `dbops.audit_sources`. `cleanup_at` fuori dall'ambito: solo
`dbops.ai_query_log`.

### 20.2 Che cosa è stato scritto

| changeSet / file | Oggetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261108-25` | `dbops.audit_sources` | D37: `DROP COLUMN` di `tx_id`, `storicizza`, `data_update`, `user_update`; COMMENT della tabella riscritto |
| `00_schema/dbops/20261108-26` | `dbops.marcatori_automazione_debito` | il registro del debito: chiave (marcatore, schema, tabella), CHECK del vocabolario e della ragione (≥ 40), audit e `tx_id` coi trigger a mano (come `rls_perimetro_debito`) |
| `20_code/dbops/20261108-27` | `dbops.vw_marcatori_automazione_senza_esecutore` | il presidio, `security_invoker`, tre stati come `vw_rls_perimetro_scoperto` |
| `20_code/dbops/20261108-28` | `dbops.ai_query_log` | D36: `trg_ai_query_log_m50_cleanup_at_ins` (`trgfn_cleanup_at_alla_nascita`); COMMENT della tabella, di `user_id` e di `cleanup_at` (M9) |
| `20_code/dbops/20261108-29` | `dbops.fn_get_lookup_codici` | D57: `ORDER BY … NULLS LAST, t.id <stesso verso>`; DECLARE ancorato (quattro variabili sugli override, il tipo dell'id su `pg_type.typname`); firma e risultato identici; COMMENT riscritto (§5d) |
| `80_data/changelog/20261108-30` | `config.storico_set_storicizza` | DELETE della riga `dbops.audit_sources`: senza la colonna, `fn_apply_storicizza_defaults` fallirebbe su di lei a ogni corsa, e il sync non la pota (la tabella esiste) |
| `80_data/changelog/20261108-31` + `marcatori_automazione_debito.csv` | il registro | seed di catalogo: le dieci tabelle di `dbops` con `tx_id` e senza trigger (§20.9) |
| `80_data/changelog/20260429-08` + `audit_sources.csv` | il mirror di `audit_sources` | via le quattro colonne dal loader e dal CSV (mirror `runOnChange` + `ANY`, si può cambiare). ⛔ Da zero il loader gira **dopo** il DROP: con le colonne elencate il migrate morirebbe |
| `automation_scope.csv` | l'ambito | D35: `shop,*all`; D36: `dbops,ai_query_log` |
| `automation_rules_tbl.csv` | regola 28 | `CLEANUP_AT` di `dbops.ai_query_log`: 90 giorni, base `data_insert` (il 27 è `CODICE_MAIUSCOLO`) |
| `storico_scope_policy.csv` | riga 126 | `shop.ricevute`, modo `BA` su `billing_account_id`: la tabella è sotto RLS (senza riga sarebbe `SENZA_RIGA`, con `NESSUNO` sarebbe `PROTETTA_NESSUNO`); il soggetto-ruolo della riga è il cliente, non l'emittente |
| `presidi.csv`, `presidi_testi.csv` | catalogo | la vista nuova: `ZERO`, stato atteso `DEBITO_DICHIARATO`, registro, `SETTIMANALE`, `LIBERO`, `SVILUPPO` |

pgTAP:

* `dbops/test-marcatori-automazione-senza-esecutore-v1` (nuovo, 13, runner owner): il presidio sul database, le tre
  chiusure del giro, e su casi costruiti in uno schema di prova i tre marcatori, il trigger a mano, il trigger
  disabilitato, l'ambito, l'esclusione dalla pulizia, i tre stati, i due CHECK, il vocabolario letto dal CHECK, lo
  schema `storico` fuori.
* `dbops/test-registri-dbops-scadenza-v1` (4): il quinto registro, `ai_query_log`, nei quattro test.
* `dbops/test-fn-get-lookup-codici` (11 → 13): lo spareggio nei due versi e le pagine da due che, concatenate, danno
  la lista intera (casi costruiti). Le attese dei test 2-8 prendono lo spareggio anche loro: confrontavano due ordini
  entrambi indeterminati, e il verde dipendeva dai dati del catalogo.

### 20.3 Le scelte dentro il giro (da guardare, Tid)

1. **La vista guarda l'ambito, non il trigger montato dai runner.** Una tabella nuova nell'ambito non ha i trigger
   finché la convergenza non gira, ma la sua promessa ha un esecutore che arriva: guardare il trigger farebbe rosso il
   presidio fra l'apply e la convergenza, su un caso che il modello prevede. Il trigger a mano conta come esecutore
   per `tx_id` e `storicizza`, non per `cleanup_at` (il purge è solo del runner, e una tabella in
   `automation_cleanup_exclusions` resta scoperta).
2. **Lo stesso filtro dei runner**: tabelle `relkind = 'r'`, partizioni comprese (i runner le scorrono una a una e il
   trigger del padre si clona sulle partizioni), schema in `fn_resolve_scope`, tabella ammessa da `fn_table_in_scope`.
   Letto sui corpi dei runner `tx_id`, `storico`, `storico_provision` e `cleanup`.
3. **Lo schema `storico` è fuori**: le shadow ricopiano le colonne della madre. Le funzioni trigger si riconoscono per
   nome e schema, non con una costante `regprocedure` che legherebbe la funzione alla vista.
4. **Base `data_insert` per `ai_query_log`**: la tabella non ha un orario dell'evento diverso dall'INSERT. Nessuno la
   scrive via dblink (il limite di `error_log` e `audit_log`): il trigger alla nascita regge, come su `request_log`.
5. **La riga di `storico_set_storicizza` si cancella qualunque sia `insert_manuale`**: la colonna non c'è più per una
   decisione (Q4), non per un caso da guardare.
6. **`%TYPE` in `fn_get_lookup_codici`**: la firma e il `RETURNS TABLE` restano a tipi espliciti, con il perché scritto
   accanto (la funzione è polimorfa). Il DECLARE è ancorato dove esiste la colonna di cui la variabile è il riflesso.
   `VOLATILE` e `SECURITY INVOKER` scritti; nessun `COST`, `ROWS` o `SET` da ripetere (letti sul vivo).

### 20.4 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

L'SQL estratto nell'ordine del migrate (`-25` … `-29`), i CSV simulati come upsert (`audit_sources.csv` con le colonne
nuove, le righe nuove di scope, regola 28, mappa 126, presidi e testi, il registro), poi il `-30`. Il presidio,
sullo scratch, vede le **dieci** righe dichiarate e niente fuori da `DEBITO_DICHIARATO`, in tutti gli schemi.
`fn_get_lookup_codici` resta **una** funzione, con `pg_get_function_identity_arguments` e `pg_get_function_result`
identici al vivo. `fn_conta_presidio` sulla vista nuova dà 0. «Senza → con»:

| File | Senza | Con |
| --- | --- | --- |
| `dbops/test-marcatori-automazione-senza-esecutore-v1` (13) | — (la vista non c'è) | 13/13 |
| `dbops/test-registri-dbops-scadenza-v1` (4) | 1/4 | 4/4 |
| `dbops/test-fn-get-lookup-codici` (13) | 11/13 (12 e 13: il difetto) | 13/13 |
| `dbops/test-storico-scope-policy-v1` (36) | 36/36 | 34/36 → **36/36 dopo la convergenza su `shop`** (vedi sotto) |
| `storico/test-storico-scope-congelato-v1`, `test-fn-get-lookup-codici-obsoleto-v1`, `test-audit-sources-seed`, `script/test-fn-audit-summary`, `test-catalogo-presidi-v1`, `test-presidi-testi-v1`, `test-conta-presidio-per-variante-v1`, `maintenance/test-cleanup-job-ambito-registro-v1`, `test-cleanup-framework`, `script/test-giornale-registri-catalogo-v1`, `documenti/test-documenti-schema-base`, `rls/test-rls-viste-security-invoker`, `test-presidi-debito-dichiarato` | verdi | verdi, identici |

⚠️ **I due rossi di `test-storico-scope-policy-v1` (5 e 29) sono la finestra fra l'apply e la convergenza**: la riga
126 della mappa c'è, il trigger di storico su `shop.ricevute` non ancora, e `vw_storico_scope_da_dichiarare` la
mostra `RIGA_SENZA_MADRE`. Simulata nella stessa transazione la convergenza sul solo `shop` (audit, storico
provision, storico, `tx_id`, `fn_storico_arma_scope_tutte`): nascono `trg_ricevute_audit_data_user_upd`,
`trg_ricevute_gen_tx_id_ins_upd`, `trg_ricevute_z90_storico_upd_dlt` e la shadow `storico.ricevute`, la vista torna
vuota e il file è 36/36. Da zero, in CI, la convergenza la fa `ci_apply`.

Guardrail `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `pgtap_preambolo`,
`sql_letterali`, `timestamp_senza_fuso`, `v1_congelato` verdi; pre-commit sui file verde. Scratch pulito dopo le prove.

### 20.5 Per Tid

1. Apply su dbdev e scratch: `20261108-25` … `-31`, e i CSV `automation_scope.csv`, `automation_rules_tbl.csv`,
   `storico_scope_policy.csv`, `audit_sources.csv` (col loader `20260429-08`), `marcatori_automazione_debito.csv`,
   `presidi.csv`, `presidi_testi.csv`.
2. **Poi `make db-ci-apply`** (la convergenza): monta su `shop.ricevute` audit, `tx_id` e storico (la provision crea
   `storico.ricevute`, `fn_storico_arma_scope_tutte` arma lo scope `BA`). Prima, `test-storico-scope-policy-v1`
   5 e 29 sono rossi per la riga 126 senza madre (§20.4): non è un rosso del giro.
3. pgTAP: `dbops/test-marcatori-automazione-senza-esecutore-v1` (runner owner), `dbops/test-registri-dbops-scadenza-v1`,
   `dbops/test-fn-get-lookup-codici` e `-obsoleto-v1`, `dbops/test-storico-scope-policy-v1`,
   `storico/test-storico-scope-congelato-v1`, `dbops/test-audit-sources-seed`, `script/test-fn-audit-summary`,
   `dbops/test-catalogo-presidi-v1`, `dbops/test-presidi-testi-v1`.
4. Dopo la convergenza, `vw_fk_senza_indice` (una misura) ha tre righe in più: le tre FK di `shop.ricevute`, che ora
   è nell'ambito. Le tratta la politica degli indici delle FK (giro 10d).

### 20.6 Doc

* `dbops/manual/`: `ai_query_log.md` (la scadenza vera, i quattro pezzi), `audit_sources.md` (fuori dalle automazioni
  e senza le colonne), `fn_get_lookup_codici.md` (lo spareggio, il tetto che cade), `automation_scope.md` (il
  presidio); nuove `vw_marcatori_automazione_senza_esecutore.md` e `marcatori_automazione_debito.md`.
* `shop/manual/ricevute.md`: i trigger del framework dalla convergenza, lo storico col modo `BA`.
* Guide: `audit-e-tracciabilita.md` (la riga di `ai_query_log`, lo scope di `dbops`, il trigger alla nascita su tre
  registri), `integrazione-ai.md` (le domande si tengono novanta giorni), `presidi-e-registri-del-debito.md` (§3.7
  nuovo, la riga del §4).
* Le pagine auto-generate (le due nuove, i COMMENT riscritti, la scheda della funzione) le rigenera `gen_db_docs.py`
  dopo l'apply.

### 20.7 Ricadute BE

* **BE4** (§5), pronta da subito: non dipende dall'apply. ✅ Fatta (2026-11-07): `list_lookup_codici` passa
  `p_limit` NULL; la costante `LOOKUP_MAX_SOURCE_ROWS` e il commento «il limit interno è una guardia» sono
  ritirati, la docstring dice perché. Ricerca, ordinamento e paginazione restano dove sono; i 41 test delle
  lookup (API, DB, specializzate, pagina oltre l'ultima) verdi.
* Nessun'altra: `shop.ricevute` non ha scrittori nel backend; `script.vw_audit_sources`, `fn_audit_summary` e il
  backend dell'audit non leggono le quattro colonne ritirate; il backend inserisce in `ai_query_log` senza
  `cleanup_at`.

### 20.8 Residuo

* **Il debito dichiarato**: le dieci tabelle di `dbops` con `tx_id` e senza trigger (`automazione_chiusura_scadenze`,
  `cause_fallimento`, `codici_errore_senza_policy`, `emittente_modi`, `messaggi_errore_codici_legacy`, `presidi`,
  `presidi_cause`, `presidi_testi`, `riferimenti_morti_esenzioni`, `storico_scope_policy`). Per ognuna una decisione
  di Tid: i due trigger a mano, come su `dbops.processi`, o la colonna tolta, come su `audit_sources`. Proposta: si
  decide al giro 14, che riapre i COMMENT di `dbops`.
* **`data_update`/`user_update` senza esecutore** fuori dal criterio, per decisione (§20.1). Proposta: entra nel
  giro 14 come domanda, insieme al debito qui sopra; le tabelle di `ui` sono di un altro perimetro.
* Il marcatore si riconosce per **nome**: una colonna di storicizzazione rinominata con un override `STORICIZZA_COL`
  sfugge. Il limite è scritto nella pagina della vista e nella guida dei presidi; se si vuole chiuderlo, la vista legge l'override
  con `dbops.fn_get_override_col`, come la provision.

#### 20.8.1 Le decisioni di Tid sul residuo (2026-11-07)

1. **`tx_id` in `dbops`: si toglie**, tranne dove il valore fa da riferimento alle righe degli altri domini, cioè
   lega la riga a ciò che la stessa transazione ha scritto altrove (audit, storico, registri degli errori).
2. **`data_update` / `user_update`:** lo schema `ui` **entra nell'ambito** delle automazioni. `dbops` **resta fuori**,
   salvo i registri che ci sono già per nome: in `dbops` i trigger si montano **a mano**, e va scritto come regola.
   Se togliere le colonne o montare i trigger, tabella per tabella: **aperto** (§20.8.2, punto 2).
3. **Il marcatore riconosciuto per nome: si risolve.** La vista legge l'override con `dbops.fn_get_override_col`.

#### 20.8.2 Che cosa ne viene, sulla struttura dello scratch (2026-11-07)

Fatti datati, letti sul catalogo. In `dbops` le tabelle con `tx_id` sono 23:

* **le dieci del debito** (§20.8), senza il trigger del `tx_id` né quello di audit;
* **otto coi due trigger a mano, sempre in coppia** (`tx_id` e audit): `processi`, `processi_bersagli`,
  `processi_identita`, `coda_lavori`, `coda_lavori_tipi`, `rls_perimetro_debito`, `stati_check_dichiarazioni` e
  `marcatori_automazione_debito`, il registro nato al giro 7;
* **cinque registri nell'ambito per nome** (`audit_log`, `error_log`, `idempotency_keys`, `processi_accensione`,
  `sessioni_utente`), coi trigger del framework.

1. **Il criterio del `tx_id` vale anche per le otto coi trigger a mano**, non solo per le dieci: dove si toglie la
   colonna si tolgono anche i trigger. Prima di scrivere si censiscono, tabella per tabella, i **lettori** del
   `tx_id` (funzioni, viste, backend) e chi scrive la riga. Proposta di lettura del criterio: resta dove la riga la
   scrive una transazione di dominio o di sessione (`coda_lavori` e i cinque registri); si toglie dove la riga la
   scrive solo un seed, perché lì il `tx_id` lega la riga al solo migrate. Su questo il registro del debito si
   svuota dei `tx_id`, e resta la sede per gli altri marcatori.
2. **`data_update` / `user_update` in `dbops`, aperto.** Proposta della sessione DB: lo stesso criterio, guardato
   dallo **scrittore**. Una tabella che qualcuno aggiorna a runtime (una funzione o il backend) tiene le colonne e
   monta i due trigger a mano. Una tabella che scrive solo un seed le perde: chi e quando l'ha cambiata lo dicono già
   `databasechangelog` e git, e le colonne direbbero sempre «il migratore, al migrate». Va deciso insieme al punto
   1: sulle otto tabelle i due trigger stanno in coppia.
3. **`ui` nell'ambito: l'ambito è uno solo per tutte le automazioni.** `dbops.automation_scope` non ha una colonna
   per l'automazione: con `ui,*all`, come `shop` al giro 7, la convergenza monta su `ui` **tutto ciò che le regole
   prevedono**, non solo l'audit (13 tabelle, 10 con `data_update`, 6 con `attivo`, nessuna con `tx_id` o
   `storicizza`, nessuna sotto RLS). Si censiscono nel blocco i montaggi attesi (in particolare i guard ATTIVO sulle
   FK fra tabelle di `ui` e verso gli altri domini) e gli scrittori del backend, che potrebbero vedere un rifiuto
   nuovo. Nella guida `automazione-db.md` la frase «gli schemi fuori ambito (`ui`, `dbops`)» cambia.
4. **La regola «in `dbops` a mano»** va in `automazione-db.md` (§l'ambito, che oggi dice «`dbops` è nell'ambito
   tabella per tabella») e in `audit-e-tracciabilita.md`: `dbops` non entra con `*all`; una sua tabella entra per
   nome solo come registro con una scadenza; le altre, se tengono un marcatore, montano i trigger a mano, e la vista
   dei marcatori lo controlla.

✅ **Confermato da Tid (2026-11-07)**: il punto 2 col criterio dello scrittore, e il giro 7-bis.

**Quando:** non più al giro 14. Un giro **7-bis** subito dopo il giro 8, che ha già il via. Contiene i
punti 1, 2 e 4 e la lettura dell'override; tocca le stesse tabelle e lo stesso presidio, che così si riapre una volta
sola. `ui` nell'ambito (punto 3) in un blocco suo dello stesso giro, perché la convergenza monta su un altro schema.

### 20.9 Chiusura (2026-11-07)

Tid ha applicato il giro 7 su dbdev e scratch (`20261108-25` … `-31`, i sette CSV e il loader `20260429-08`), con la
convergenza che monta su `shop.ricevute` audit, `tx_id` e storico, e ha lanciato i pgTAP di §20.5: verdi. Le pagine
auto-generate (la vista e il registro nuovi, i COMMENT riscritti di `audit_sources`, `ai_query_log` e
`fn_get_lookup_codici`) si rigenerano con `gen_db_docs.py` ed entrano nel commit del giro. Restano fuori dal commit le
modifiche dell'altro cantiere (`20261108-14` … `-24`, `-32` … `-34` e i loro pgTAP). **Il giro 7 è chiuso**,
committato in `11203bab2e`; restano BE4 al team BE (§5) e il residuo di §20.8, proposto al giro 14.

La convergenza su `shop.ricevute` è letta sul catalogo, non dedotta dai test (sessione DB, 2026-11-07, sola lettura):
su dbdev e sullo scratch la tabella ha `trg_ricevute_audit_data_user_upd`, `trg_ricevute_gen_tx_id_ins_upd` e
`trg_ricevute_z90_storico_upd_dlt`, la shadow `storico.ricevute` esiste, `vw_storico_scope_da_dichiarare` è vuota e il
presidio dei marcatori ha le sue dieci righe dichiarate.

## 21. Giro 8 — le fixture: preparazione, 2026-11-07

Non è ancora scritto niente: il giro aspetta il via di Tid (§21.3).

### 21.1 D68 è già chiuso, dall'altro cantiere

`brief-db-sorgente-documento-e-riga` ha riscritto `dbops.fn_pgtap_crea_commessa_attivita` (`20261108-01`, poi
`20261108-34` per il nome nuovo del parametro della madre), su decisione di Tid del 2026-11-07: senza sorgente il
builder crea un consumo vero (`vendite.attivita_consumi`) e la chiave la compone `script.fn_segment_key`; con la
sorgente, la chiave nomina il documento col suo uid. La chiave `PGT-SEG-<md5>` non c'è più. La decisione revoca la
forma della Q12 (`MAN:<commessa>:<n>`), che qui non si applica. Resta di D68, per il giro 14, il solo COMMENT della
fixture (M36), se l'altro cantiere non l'ha già riscritto.

### 21.2 Gli altri difetti, sulla scheda del 2026-11-07

| # | Stato | Che cosa si vede oggi |
| --- | --- | --- |
| D63 | aperto | `fn_pgtap_crea_soggetto_pg` scrive ancora con INSERT `anagrafiche.soggetti` e due volte `indirizzi_soggetti` (gli obbligatori della matrice, poi il ripiego «il primo tipo ammesso» se non ce n'è nessuno) |
| D64 | aperto | `fn_pgtap_crea_indirizzo_dettaglio` (riscritta al giro 2 per la via viva, `20261107-15`) tiene l'`ON CONFLICT … DO UPDATE` al posto di `anagrafiche.fn_get_or_create_indirizzo_dettaglio` |
| D66 | aperto | `script.fn_pgtap_emittente_operatore` ripiega ancora su un operatore reale e poi sul primo emittente attivo per id (Q11: delega a `dbops.fn_pgtap_azienda_di_chi_agisce`) |
| D67 | aperto | `fn_pgtap_crea_lotto` scrive l'esito con un INSERT su `vendite.fatturazione_lotti_esiti` |
| D69 | aperto | `fn_pgtap_listino_aggiungi_articoli` scrive le righe senza periodicità; `fn_pgtap_crea_listino` le aggiunge con quel builder |
| D70 | aperto | `fn_pgtap_porta_a_stato` verso `CHIUSA` chiama `vendite.fn_chiudi_versioni_listino_scadute()` e non controlla lo stato raggiunto |
| D71 | aperto | `fn_pgtap_crea_ddt_da_ordine` conta le righe attive dell'ordine senza filtro di natura: un ordine con una riga di merce e un onere rifiuta `p_qta_da_evadere` |
| D73 | aperto | `script.fn_doc_stato_id` lo usa solo `fn_pgtap_crea_preventivo_con_righe`; gli altri builder che cercano uno stato si censiscono nel giro |
| D74 | aperto | «la prima valuta del catalogo» nei sette builder del brief |

Gli altri builder toccati oggi dall'altro cantiere (`20261108-09`: i COMMENT di `fn_pgtap_porta_a_stato` e
`fn_pgtap_crea_cliente_ba`) non cambiano il corpo: D70 e D74 restano come sono descritti. ⚠️ Prima di scrivere ogni
changeSet il corpo si riprende dalla scheda del giorno: l'altro cantiere lavora sugli stessi builder.

### 21.3 Il via (Tid, 2026-11-07)

1. **I numeri: dal primo libero.** Cercato su tutti i livelli, nel working tree e su `origin/Tito-dev`, e nei brief
   aperti: il più alto è il `20261108-34` (altro cantiere). **Tid dà il `20261108-41`**: il giro 8 parte da lì
   (`-35` … `-40` non sono di questo cantiere).
2. **D68 fuori dal giro: sì**, chiuso dall'altro cantiere con la decisione del 2026-11-07 che supera la Q12 (§21.1).
3. **D63, il ripiego «almeno un indirizzo»: come da proposta.** La fixture chiama
   `fn_crea_indirizzi_soggetto` con gli indirizzi obbligatori della matrice; il ripiego resta solo se il guard
   degli indirizzi pretende una riga anche quando la matrice non ne rende obbligatorio nessuno (lo si legge sul
   guard nel giro), e allora passa anche lui dalla madre.

### 21.4 Che cosa è stato scritto (2026-11-08)

Tre blocchi, `20261108-41` … `-60`, tutti in `20_code` (uno solo in `20_code/script`). Il corpo di ogni funzione
viene dalla doc auto-generata, verificata uguale al vivo dello scratch; firma, `RETURNS`, `SECURITY INVOKER` e la
firma dei `COMMENT ON` vengono dall'ultimo YAML che li ancorava con `%TYPE`. `fn_pgtap_porta_a_stato`, che nessuno
YAML aveva mai ancorato, ha i tipi espliciti con il perché accanto. Ogni COMMENT riscritto al presente (§5d).

| changeSet | Oggetto | Difetto | Che cosa |
| --- | --- | --- | --- |
| `-41` | `dbops.fn_pgtap_crea_indirizzo_dettaglio` | D64 | l'indirizzo da `anagrafiche.fn_get_or_create_indirizzo_dettaglio`: la riga spenta torna attiva, la via si risolve |
| `-42` | `dbops.fn_pgtap_porta_a_stato` | D70 | uno stato raggiunto diverso da quello chiesto solleva, per ogni testata |
| `-43` | `dbops.fn_pgtap_crea_ddt_da_ordine` | D71, D73 | riga restituita e riga da evadere di merce (`script.fn_natura_e_merce`); lo stato da `script.fn_doc_stato_id` |
| `-44` | `dbops.fn_pgtap_crea_lotto` | D67, D73 | l'esito trattenuto dalla porta `vendite.fn_segna_esito_gruppo_lotto` (con `errore_quando`); lo stato da `script.fn_doc_stato_id` |
| `-45` | `script.fn_pgtap_emittente_operatore` | D66 (Q11) | delega a `dbops.fn_pgtap_azienda_di_chi_agisce`: niente più ripieghi |
| `-46` | `dbops.fn_pgtap_crea_soggetto_pg` | D63 | testata, contatto e dati societari da `anagrafiche.fn_crea_soggetto_pg`, indirizzi da `fn_crea_indirizzi_soggetto`; il ripiego si ritira |
| `-47` | `dbops.fn_pgtap_valuta` (nuova) | D74 | la valuta delle radici della catena, una sede |
| `-48` | `dbops.fn_pgtap_crea_ddt` | D73, D74 | stato iniziale da `script.fn_doc_stato_iniziale_id` (era `'DRAFT'` in linea); valuta da `vendite.fn_get_valuta_id` |
| `-49`, `-50`, `-52`, `-55` | `_crea_ddt_riconsegna`, `_crea_ddt_senza_ordine`, `_crea_ordine_con_righe`, `_crea_reso` | D73 | lo stato da `script.fn_doc_stato_id` (la copia in linea si ritira) |
| `-51`, `-53`, `-54` | `_crea_ordine`, `_crea_preventivo`, `_crea_fattura` | D73, D74 | lo stato da `script.fn_doc_stato_id`: uno stato **spento** ora solleva prima di costruire; valuta da `vendite.fn_get_valuta_id` |
| `-56`, `-57`, `-58` | `_crea_cliente_ba`, `_crea_emittente`, `_crea_gestore` | D74 | la valuta da `dbops.fn_pgtap_valuta` |
| `-59` | `dbops.fn_pgtap_listino_aggiungi_articoli` | D69 | `p_periodicita` in coda, `DEFAULT NULL`; firma nuova (DROP + CREATE nello stesso changeSet) |
| `-60` | `dbops.fn_pgtap_crea_listino` | D69 | la tipologia di default è la prima ammessa che non è una quota fissa |

pgTAP nuovi: `dbops/test-fn-pgtap-porta-a-stato-v1` (3), `anagrafiche/test-fn-pgtap-crea-soggetto-pg-v1` (4),
`script/test-fn-pgtap-emittente-operatore-v1` (3), `dbops/test-fn-pgtap-valuta-v1` (3),
`dbops/test-fn-pgtap-crea-listino-v1` (3). Estesi: `anagrafiche/test-indirizzi-dettaglio-unicita-v1` (28 → 29),
`dbops/test-fn-pgtap-crea-ddt-da-ordine-v1` (16 → 17), `dbops/test-fn-pgtap-crea-lotto-v1` (test 8 con
`errore_quando`), `dbops/test-fn-pgtap-crea-ordine-v1` (11 → 13), `dbops/test-fn-pgtap-crea-preventivo-v1` (9 → 10),
`dbops/test-fn-pgtap-crea-fattura-v1` (15 → 17). Riallineato: `anagrafiche/test-fn-crea-contatto-v1` (test 2 e 12, §21.5
punto 2). I casi si costruiscono nella transazione del test: lo stato spento (una copia dello stato iniziale,
disattivata), la natura senza tipi obbligatori, l'utility con la quota fissa in testa, il billing account con una
valuta che non è la prima del catalogo.

### 21.5 Le scelte dentro il giro (da guardare, Tid)

1. **D74, due sedi e non una.** §2.9 chiedeva «un BB di fixture». Sul modello la valuta di un documento la risolve
   il dominio (`vendite.fn_get_valuta_id`: billing account, poi emittente, poi gestore), ed è quella che scrivono i
   trigger di default: i quattro builder di documento la chiedono lì. Solo le tre radici della catena (cliente BA,
   emittente, gestore) non hanno da chi prenderla, e usano `dbops.fn_pgtap_valuta`. Le sette copie si ritirano
   tutte; il test 3 di `test-fn-pgtap-valuta-v1` controlla che nessuna fixture legga più `config.valute` da sé.
2. **D63, il contatto della fixture cambia forma.** La madre scrive il contatto di default con il nominativo uguale
   alla ragione sociale (la fixture scriveva «Referente …» e `default_context = 'soggetto'`). È la forma
   dell'applicazione. Il test 2 di `test-fn-crea-contatto-v1` riallinea l'attesa; il test 12 conta la fixture fra
   chi passa dal BB del contatto, attraverso la madre.
3. **D66, l'identità OPERATORE.** `dbops.fn_pgtap_azienda_di_chi_agisce` pretende anche un'identità OPERATORE
   attiva per l'utente di contesto, che il vecchio helper non chiedeva. Delegare vuol dire prendere anche questa
   regola (Q11: una sede).
4. **D73 tocca anche `_crea_fattura`**, che §2.9 non elencava: cercava lo stato senza il filtro `attivo`, come ordine
   e preventivo. E `_crea_ddt` scriveva `'DRAFT'` in linea: ora lo stato iniziale della testata. Le frasi d'errore di
   ordine, preventivo e fattura restano le stesse con «attivo» aggiunto, così le attese dei test di oggi valgono.
5. **D71, la bolla senza merce.** La riga restituita si legge in `LEFT JOIN`: una bolla che non ha una riga di merce
   torna lo stesso, con la riga a NULL, invece di non tornare.
6. **D69, la firma.** `p_periodicita` in coda con `DEFAULT NULL`: le chiamate per posizione di oggi restano valide.
   La firma nuova vuole DROP + CREATE; nessun oggetto del catalogo ne dipende, e i GRANT li ridanno i privilegi di
   default e il loop dei grant.

### 21.6 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* `preConditions` estratte ed eseguite su scratch e dbdev: verdi.
* Applicati i 20 changeSet in una transazione annullata: firma, risultato, volatilità e sicurezza di ogni funzione
  identici al vivo (una sola funzione per nome); cambiano solo `fn_pgtap_listino_aggiungi_articoli` (il parametro in
  coda) e `fn_pgtap_valuta` (nuova).
* «Senza → con», sui file del giro: rosso **solo** il caso del difetto senza, tutto verde con.

| File | Senza | Con |
| --- | --- | --- |
| `anagrafiche/test-indirizzi-dettaglio-unicita-v1` (29) | 28/29 (29: l'indirizzo resta spento) | 29/29 |
| `dbops/test-fn-pgtap-porta-a-stato-v1` (3) | 2/3 (1: nessun errore) | 3/3 |
| `dbops/test-fn-pgtap-crea-ddt-da-ordine-v1` (17) | 16/17 (17: «ne ha 2») | 17/17 |
| `dbops/test-fn-pgtap-crea-lotto-v1` (9) | 8/9 (8: `errore_quando` vuoto) | 9/9 |
| `anagrafiche/test-fn-pgtap-crea-soggetto-pg-v1` (4) | 2/4 (1: «Referente», 4: il ripiego) | 4/4 |
| `script/test-fn-pgtap-emittente-operatore-v1` (3) | 1/3 (1, 3: il ripiego) | 3/3 |
| `anagrafiche/test-fn-crea-contatto-v1` (13) | 12/13 (2: l'attesa nuova) | 13/13 |
| `dbops/test-fn-pgtap-crea-ordine-v1` (13) | 11/13 (12: lo stato spento, 13: la valuta) | 13/13 |
| `dbops/test-fn-pgtap-crea-preventivo-v1` (10) | 9/10 (10: lo stato spento) | 10/10 |
| `dbops/test-fn-pgtap-crea-fattura-v1` (17) | 15/17 (16, 17) | 17/17 |
| `dbops/test-fn-pgtap-valuta-v1` (3) | — (la funzione non c'è) | 3/3 |
| `dbops/test-fn-pgtap-crea-listino-v1` (3) | 0/3 (1: la versione non si attiva) | 3/3 |

* Regressione del blocco 8a (`-41` … `-44`) su 620 file che usano un builder: 538 verdi; 82 rossi, di cui 79
  **identici senza** le correzioni (rossi preesistenti, presi da owner) e 3 che erano deadlock con altre sessioni
  sullo scratch, verdi rilanciati a scratch libero. Nessuna regressione.
* Regressione dei tre blocchi (`-41` … `-60`) su 974 file che chiamano una fixture `fn_pgtap_*`: 869 verdi; 105
  rossi, di cui 103 **identici senza** le correzioni (preesistenti, presi da owner). Gli altri due
  (`anagrafiche/test-soggetti-indirizzi-required`, `test-soggetti-ruoli-indirizzi-required`) aprono più transazioni
  e la prova con l'estratto non li sa comporre; usano solo `fn_pgtap_piva_libera` e `fn_pgtap_indirizzo_libero_forma`,
  che il giro non tocca. Nessuna regressione.
* Guardrail `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `pgtap_preambolo`, `precondition_seed`,
  `run_on_change`, `sql_letterali`, `timestamp_senza_fuso`, `v1_congelato` verdi; pre-commit sui file verde.

* **Dopo l'apply (Tid, 2026-11-08)**: `test-fn-crea-contatto-v1` 12 rosso come app su dbdev. Il ramo nuovo del test
  riconosceva la fixture con `f::text LIKE 'dbops.…'`: come app `dbops` è nel `search_path` e il `regprocedure` si
  stampa senza schema (da owner no, per questo la prova era verde). Ora la riconosce per OID. I dodici file di §21.6,
  come app sullo scratch: tutti verdi.

### 21.7 Per Tid

1. Apply su dbdev e scratch: `20261108-41` … `-60` (solo `20_code`, nessun CSV, nessun codice errore nuovo).
2. pgTAP: i dodici file di §21.6 (cinque nuovi: `dbops/test-fn-pgtap-porta-a-stato-v1`,
   `anagrafiche/test-fn-pgtap-crea-soggetto-pg-v1`, `script/test-fn-pgtap-emittente-operatore-v1`,
   `dbops/test-fn-pgtap-valuta-v1`, `dbops/test-fn-pgtap-crea-listino-v1`). Le fixture le usano quasi tutti i file:
   una corsa intera dice di più di una lista.
3. La baseline B-7 non dovrebbe muoversi (nessun codice, nessun presidio di catalogo).

### 21.8 Doc

* Pagine `manual/` riallineate, una per oggetto: le diciannove fixture di §21.4, più
  `dbops/manual/fn_pgtap_azienda_di_chi_agisce.md` (descriveva il ripiego di `script.fn_pgtap_emittente_operatore`);
  nuova `dbops/manual/fn_pgtap_valuta.md`.
* Le schede auto-generate (le COMMENT riscritte, la funzione nuova) le rigenera `gen_db_docs.py` dopo l'apply.

### 21.9 Residuo

* Nessun difetto del giro resta aperto. M36 (COMMENT di fixture) è chiuso per gli oggetti toccati qui; il resto va
  al giro 14.
* Subito dopo: il giro 7-bis (§20.8.2), confermato da Tid.

### 21.10 Chiusura (2026-11-08)

Tid ha applicato il giro 8 su dbdev e scratch (`20261108-41` … `-60`) e ha lanciato i pgTAP di §21.7: verdi, dopo
la correzione del test 12 di `test-fn-crea-contatto-v1` (§21.6, il confronto per OID). Le schede auto-generate (la
funzione nuova `dbops.fn_pgtap_valuta`, le firme e i COMMENT riscritti) si rigenerano con `gen_db_docs.py` ed entrano
nel commit del giro. Restano fuori dal commit le modifiche dell'altro cantiere. Committato da Tid in `8bbae0df7b`
(confluito in `Tito-dev` con la PR #51). **Il giro 8 è chiuso**; il prossimo è
il giro 7-bis (§20.8.2), poi il giro 9 (§8).

## 22. Il seguito del giro 7 su `shop`: il presidio e i grant (2026-11-08)

### 22.1 Il rosso

`dbops/test-storico-scope-policy-v1` come app (Tid, dbdev, 2026-11-08): «permesso negato per lo schema shop» al test
29, il file si ferma a 32 asserzioni su 36. La vista di presidio `dbops.vw_storico_scope_da_dichiarare` cercava la
madre di ogni riga di mappa con `to_regclass('schema.tabella')`. `to_regclass` rende NULL se la tabella non c'è, ma
**solleva** se chi legge non ha `USAGE` sullo schema; la vista è `security_invoker`. Dal giro 7 la mappa ha la riga 126,
`shop.ricevute`, e su `shop` l'app non aveva nessun grant: l'ACL dello schema era vuota su dbdev e sullo scratch, e
`shop` mancava dai due elenchi degli schemi dell'app (il loop `90_end/ci_apply/20260205-41` e la fase post di
`scripts/sql/provision_zeroerp.sql`). Provato come `zeroerp_app` su dbdev: `to_regclass('shop.ricevute')` solleva, la
stessa ricerca su `pg_class` + `pg_namespace` trova la tabella. Gli altri presidi con `regclass` lo convertono da oid o
da nomi del catalogo: il difetto è solo qui.

### 22.2 Le due decisioni (Tid, 2026-11-08)

1. **Il presidio non dipende dai privilegi di chi lo legge** («ok»): la madre si cerca sul catalogo.
2. **`shop` è uno schema dell'applicazione** («sì»): `shop.ricevute` ha la RLS e le policy del cliente dello shop e
   dell'operatore (`20260420-07`, `20260912-42`, `20261021-39`), che scattano solo per `zeroerp_app`; senza grant non
   avevano un lettore.

### 22.3 Che cosa è scritto

* `20_code/dbops/20261108-88`: `CREATE OR REPLACE VIEW dbops.vw_storico_scope_da_dichiarare`, la CTE `righe` cerca la
  madre su `pg_class` + `pg_namespace`; l'alias `pg_temp` (le righe di prova) è `pg_my_temp_schema()`, come per
  `to_regclass`. Il resto identico; COMMENT riscritto sul confronto; `security_invoker` ripetuto, i grant restano.
* `90_end/20261108-89`: a `zeroerp_app` su `shop` la postura di default degli schemi dell'app (USAGE, DML sulle
  tabelle del migratore, sequenze, EXECUTE, default privileges del migratore). Agisce subito su dev, dove il loop
  converge solo al prossimo `make db-ci-apply` e il provisioning non si rilancia.
* `shop` nel loop `20260205-41` (`v_schemas`) e in `_app_schemas` di `provision_zeroerp.sql`: le due sedi restano
  allineate.
* pgTAP `dbops/test-storico-scope-policy-v1`, test 33 nuovo (plan 37): una riga di mappa su `pg_toast`, che non ha USAGE
  né per l'app né per il migratore, esce `RIGA_SENZA_MADRE` e non un errore. Nel file erano già passati al catalogo i
  test 6, 6-bis, 8, 13 e 14 (stesso rimedio, nel working tree prima di questo giro).

### 22.4 Le prove (dbdev e scratch, `BEGIN … ROLLBACK`, SQL estratto dagli YAML)

* Equivalenza della madre, riga per riga sulle 123 righe della mappa: `to_regclass` e catalogo danno lo stesso oid,
  zero differenze, sui due database. La vista resta vuota prima e dopo; grant e `security_invoker` invariati.
* Come `zeroerp_app` su dbdev, il corpo nuovo come query: 0 righe, nessun errore (anche senza i grant di `-89`).
* `-89` due volte di seguito (idempotente): USAGE, DML, EXECUTE e le tre default privileges presenti.
* `test-storico-scope-policy-v1` da owner: senza l'estratto 36 su 37 e l'errore su `pg_toast` (il test 33 vede il
  difetto); con l'estratto 37/37, sui due database.
* I 29 pgTAP che citano `shop` o i grant dell'app, con e senza l'estratto: identici salvo il file sopra. Restano rossi da
  owner, uguali prima e dopo, i test di postura dell'app (`config/test-credenziali-porta-v1`,
  `dbops/test-registri-append-only-postura-v1`, `magazzino/test-porta-ledger-v1`,
  `maintenance/test-app-postura-job-run-log-v1`): si misurano come app.

### 22.5 Per Tid

1. Apply di `20261108-88` e `-89` su dbdev e scratch.
2. pgTAP come app: `dbops/test-storico-scope-policy-v1` (37), e i file di §22.4.
3. Doc: la scheda auto-generata della vista (il COMMENT) si rigenera con `gen_db_docs.py`.
4. Ricadute BE: nessuna (`shop.ricevute` non ha scrittori nel backend, §20.7).

## 23. Giro 7-bis — i marcatori di `dbops` seguono lo scrittore (§20.8.2), 2026-11-08

**Via di Tid (2026-11-08)**, coi numeri dal **`20261108-90`**: il `-86` … `-89` sono dell'altro cantiere e di §22,
che ha confermato di non volerne altri.

### 23.1 Il censimento (struttura, scratch `zeroerp_ruoli`, 2026-11-08)

Letti sul catalogo: colonne, trigger, `automation_scope`; gli scrittori dai corpi delle funzioni (`prosrc`), dal
backend (DML su `dbops.*`, anche su più righe) e dai loader di `80_data`/`90_end`; i lettori da `pg_depend` (viste,
regole, funzioni `BEGIN ATOMIC`, vincoli), dai corpi, dal backend e dai pgTAP. Sono fatti datati, non il motivo della
classe: la classe la dà lo **scrittore**, che è contratto (chi ha il diritto e il codice per scrivere la riga).

| Classe | Tabelle | Scrittore | Che cosa ne viene |
| --- | --- | --- | --- |
| **R** — registri nell'ambito per nome | `audit_log`, `error_log`, `idempotency_keys`, `processi_accensione`, `sessioni_utente` | transazioni di dominio o di sessione | nulla: restano coi trigger del framework |
| **S** — scritte a runtime, trigger a mano | `coda_lavori` (`fn_accoda_lavoro`, il drenatore del backend), `processi_identita` (`script.fn_crea_utente_tecnico`, `fn_riattiva_utente_tecnico`, dal cockpit) | transazioni di dominio o di sessione | nulla: tengono `tx_id`, `data_update`, `user_update` e i due trigger a mano |
| **A** — solo seed, con `tx_id` | coi due trigger a mano: `processi`, `processi_bersagli`, `coda_lavori_tipi`, `rls_perimetro_debito`, `stati_check_dichiarazioni`, `marcatori_automazione_debito`; senza (le dieci del debito): `automazione_chiusura_scadenze`, `cause_fallimento`, `codici_errore_senza_policy`, `emittente_modi`, `messaggi_errore_codici_legacy`, `presidi`, `presidi_cause`, `presidi_testi`, `riferimenti_morti_esenzioni`, `storico_scope_policy` | solo il migratore, dai CSV di `80_data` | via `tx_id`, `data_update`, `user_update` e i due trigger dove ci sono |
| **B** — solo seed (o solo `INSERT` a runtime), senza `tx_id` | `automation_cleanup_exclusions`, `automation_delete_block`, `automation_lock_columns`, `automazione_attivo_eccezioni`, `automazione_codice_eccezioni`, `automazione_guard_utility_tipo_ruolo`, `automazione_overlap`, `domini_task`, `fk_index_policy`, `lock_columns_conditional`, `pipeline_task_registry`, `pipeline_task_registry_impl` | il migratore; `fk_index_policy` anche il job `apply_fk_index_policy`, ma solo con `INSERT` | via `data_update`, `user_update` |
| — | `transaction_ids` | le funzioni del `tx_id` | fuori: è il registro stesso, append-only |

Sulle classi A e B nessun lettore delle tre colonne: nessuna vista, regola, vincolo o funzione `BEGIN ATOMIC` (da
`pg_depend`), nessun corpo, nessun modello o query del backend (`processi_repository.py:442` legge `user_update`
di `processi_accensione`, classe R). Due pgTAP le usano: `dbops/test-coda-lavori` (8 e 9, i trigger di
`coda_lavori_tipi`) e `dbops/test-tx-id-coerenza-non-registrato`, che usa `coda_lavori_tipi` come **veicolo** del
trigger `tx_id`.

### 23.2 Perché la classe B è un blocco a parte

Su A le tre colonne non stanno in nessun CSV né in nessun changeSet di fase successiva: il `DROP` va in
`00_schema`, come quello di `audit_sources` al giro 7. Su B no:

* `data_update`/`user_update` stanno nell'**header** di cinque CSV caricati, ognuno da **un** loader
  `runOnChange` + `ANY`: `domini_task.csv` (`20260208-06`), `pipeline_task_registry.csv` (`-07`),
  `pipeline_task_registry_impl.csv` (`-08`), `automation_delete_block_ruoli.csv` (`20260123-11`, tabella
  `automation_delete_block`) e `automation_lock_columns.csv` (`20260110-15`). Anche il loader dichiara le due
  colonne nelle voci `column:`. ⚠️ Corretto il 2026-11-08 (§23.11): la prima stesura contava «tredici loader» per
  `fk_index_policy.csv` e «otto» per `automation_lock_columns.csv`, ma gli altri file nominano il CSV solo nei
  commenti; `fk_index_policy.csv` non lo carica **nessun** changeSet (lo dice già il `20261106-99`), e mancava
  `automation_delete_block_ruoli.csv`;
* cinque changeSet di `80_data` **già applicati e senza `runOnChange`** scrivono `data_update = now()` su
  `lock_columns_conditional` (`20260522-04`, `20261010-01`, `20261013-04`, `-46`, `-51`) e su
  `automazione_guard_utility_tipo_ruolo` (`20260216-06`). Da zero girano **dopo** `00_schema`: un `DROP` lì
  rompe la CI, e quei file non si toccano.

Il `DROP` di B va quindi in `80_data` (o `90_end`), dopo l'ultimo changeSet che nomina le colonne, e con i CSV e i
loader ripuliti: è un lavoro di checksum, non di modello, e si fa dopo l'apply di A. I cinque loader sono mirror vivi
(`runOnChange` + `ANY`): si ripuliscono in place, senza file nuovi. È anche il blocco che chiude la
voce `dbops.fk_index_policy` del registro di `dbops/test-user-update-not-null-v1`.

### 23.3 I blocchi

| Blocco | Che cosa | Dove |
| --- | --- | --- |
| **7-bis-a** | classe A: via le tre colonne e i due trigger; il registro dei marcatori si svuota delle dieci righe `TX_ID`; la vista legge l'override di `STORICIZZA_COL` (§20.8.1, punto 3); la regola «in `dbops` a mano» nelle guide (§20.8.2, punto 4) e in `linee-guida-sql.md` §7 | `00_schema/dbops`, `20_code/dbops`, `80_data` |
| **7-bis-b** | classe B: via `data_update`/`user_update`, coi CSV e i loader | `80_data` |
| **7-bis-c** | `ui` nell'ambito (§20.8.2, punto 3): il censimento dei montaggi e degli scrittori del backend prima di scrivere | `80_data`, convergenza |

### 23.4 Blocco 7-bis-a — che cosa è scritto (2026-11-08)

| changeSet / file | Oggetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261108-90` | `coda_lavori_tipi`, `marcatori_automazione_debito`, `processi`, `processi_bersagli`, `rls_perimetro_debito`, `stati_check_dichiarazioni` | `DROP TRIGGER` dei due trigger a mano (`…_gen_tx_id_ins_upd`, `…_audit_data_user_ins_upd`), poi `DROP COLUMN` di `tx_id`, `data_update`, `user_update`; rollback che rimette colonne e trigger |
| `00_schema/dbops/20261108-91` | le dieci tabelle del debito `TX_ID` (§20.8) | `DROP COLUMN` delle tre colonne |
| `20_code/dbops/20261108-92` | `dbops.vw_marcatori_automazione_senza_esecutore` | la colonna di storicizzazione con `dbops.fn_get_override_col(…, 'STORICIZZA_COL', 'storicizza')`, come la provision (§20.8.1, punto 3); il resto identico; COMMENT della vista; rollback = il corpo del `-27` |
| `80_data/changelog/20261108-93` + `marcatori_automazione_debito.csv` | il registro | `DELETE` delle dieci righe `TX_ID` (filtro per nome, non `DELETE` totale); il CSV resta col solo header (il loader `-31` è un mirror che non cancella) |

pgTAP:

* `dbops/test-marcatori-automazione-senza-esecutore-v1` (13 → 16): 14 le chiusure del 7-bis (le sedici tabelle senza
  le tre colonne), 15 la colonna rinominata con l'override è il marcatore, 16 la colonna `storicizza` con l'override
  verso un'altra non lo è (casi costruiti).
* `dbops/test-coda-lavori` (57): 8 e 9 dicono ora che il catalogo dei tipi **non** ha marcatori né trigger.
* `dbops/test-tx-id-coerenza-non-registrato` (11): il veicolo del trigger non è più `coda_lavori_tipi` ma una tabella
  temporanea col trigger montato come lo monta il framework. Il file collauda il trigger, non una tabella: il soggetto
  se lo fabbrica. Verificato che l'app ha `TEMP` sul database ed `EXECUTE` sulla funzione.

### 23.5 Le scelte dentro il blocco (da guardare, Tid)

1. **`processi_identita` tiene le colonne.** La scrivono `script.fn_crea_utente_tecnico` e `fn_riattiva_utente_tecnico`,
   chiamate dal cockpit: è uno scrittore a runtime, anche se la tabella ha anche un seed.
2. **`fk_index_policy` va in B, non in S.** A runtime il job `apply_fk_index_policy` fa solo `INSERT … ON CONFLICT DO
   NOTHING` (`fn_populate_fk_index_policy`): nessuno la **aggiorna**, quindi `data_update`/`user_update` non dicono
   niente. Il criterio guarda chi aggiorna, non chi inserisce.
3. **Il COMMENT delle tabelle non cambia**: nessuno dei sedici nomina le tre colonne (letto sul vivo). Quello del
   registro le nomina come vocabolario, che resta vero.
4. **`cleanup_at` resta per nome**: la colonna del purge la sceglie il parametro `cleanup_column` della regola, non un
   override di colonna. Leggerlo nella vista vorrebbe dire risolvere la regola per tabella: residuo (§23.9).

### 23.6 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

L'SQL di `-90` … `-93` nell'ordine del migrate: 4 `ALTER TABLE` andati, la vista ricreata, `DELETE 10`; il presidio
sul database è **vuoto**. Regressione «senza → con» in sequenza sui **64** pgTAP che nominano le sedici tabelle, col
`databasechangelog` invariato prima e dopo la corsa:

| File | Senza | Con |
| --- | --- | --- |
| `dbops/test-marcatori-automazione-senza-esecutore-v1` (16) | 13/16 (14, 15, 16: il difetto) | 16/16 |
| `dbops/test-coda-lavori` (57) | 55/57 (8, 9: le attese nuove) | 57/57 |
| `dbops/test-tx-id-coerenza-non-registrato` (11) | 11/11 | 11/11 (prima della riscrittura: morto al test 4, «la colonna t.tx_id non esiste») |
| gli altri 61 | identici | identici |

Quattro rossi **identici** prima e dopo, non del giro: `dbops/test-emittente-modi-solo-migrazione-v1` (1/4, da owner il
guard «solo migrazione» lascia passare), `rls/test-rls-email-log-ambito` (4/6, da owner), `vendite/test-annullamento-chiude-la-vita-v1`
(17/18) e `vendite/test-lotti-fermi-verdetto-a-db-v1` (23/24). Come app li dirà la corsa di Tid.

Guardrail `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `pgtap_preambolo`, `precondition_seed`, `run_on_change`,
`sql_letterali`, `timestamp_senza_fuso`, `v1_congelato` verdi sui file del blocco.

### 23.7 Per Tid

1. Apply su dbdev e scratch: `20261108-90` … `-93` e il CSV `marcatori_automazione_debito.csv` (il loader `-31` si
   rilancia da solo, `runOnChange`, e non carica niente).
2. pgTAP come app: `dbops/test-marcatori-automazione-senza-esecutore-v1` (runner owner), `dbops/test-coda-lavori`,
   `dbops/test-tx-id-coerenza-non-registrato`, `dbops/test-catalogo-presidi-v1`, `dbops/test-processi-accensione-v1`,
   `dbops/test-storico-scope-policy-v1`, `dbops/test-user-update-not-null-v1` (4/4 con e senza, da owner).
3. Le schede auto-generate delle sedici tabelle e della vista si rigenerano con `gen_db_docs.py`.
4. Ricadute BE: **nessuna**. Nessuna query del backend legge le tre colonne di queste tabelle (§23.1).

### 23.8 Doc

* Guide: `automazione-db.md` §1.1 (la regola «in `dbops` a mano», lo scrittore, il residuo B) e la trappola del
  trigger a mano (l'eccezione di `dbops`); `audit-e-tracciabilita.md` §2.3 (chi non ha `tx_id`);
  `presidi-e-registri-del-debito.md` §3.7 (l'override, il registro vuoto, il limite che resta su `cleanup_at`).
* `linee-guida-sql.md` §7: l'eccezione di `dbops`.
* `dbops/manual/`: `vw_marcatori_automazione_senza_esecutore.md`, `marcatori_automazione_debito.md`, e la nota di
  migrazione del 2026-11-08 sulle altre quindici (`emittente_modi.md` prende la sezione, che non aveva).

### 23.9 Residuo

* ✅ **Blocco 7-bis-b** (§23.2, §23.11): chiuso il 2026-11-08 (§23.11.4).
* **`fk_index_policy.csv`**, che nessuno carica: al blocco 10d, non al 7-bis-b (§23.11).
* **Blocco 7-bis-c**: `ui` nell'ambito (§20.8.2, punto 3): scritto il 2026-11-08 (§23.12).
* `cleanup_at` riconosciuto per nome (§23.5, punto 4).

### 23.10 Chiusura del blocco a (2026-11-08)

Tid ha applicato il blocco 7-bis-a su dbdev e scratch (`20261108-90` … `-93` e `marcatori_automazione_debito.csv`) e
ha lanciato i pgTAP di §23.7: verdi. Letto sullo scratch (sessione DB, sola lettura): i quattro changeSet sono in
`databasechangelog`, e `dbops.vw_marcatori_automazione_senza_esecutore` è vuota. Le schede auto-generate delle sedici
tabelle e della vista si rigenerano con `gen_db_docs.py` ed entrano nel commit. **Il blocco a è chiuso** e committato
(`f7ce9855c5`). Il prossimo è il blocco 7-bis-b (§23.11).

### 23.11 Blocco 7-bis-b — il censimento e il via (2026-11-08)

**Via di Tid (2026-11-08).** Numeri dal **`20261109-31`**: Tid aveva indicato il `-15`, ma la sessione di
`brief-db-sorgente-documento-e-riga` (lotto M) occupa `20261108-94` … `-99` e `20261109-01` … `-14` e tiene
riservati fino al `-30`, per le correzioni della sua regressione (risposta di quella sessione, 2026-11-08). Il
`fk_index_policy.csv` orfano si ritira «se non usato»; il test 14 del presidio dei marcatori si estende alla classe B.

**Il censimento** (struttura; file del repo, schede auto-generate e catalogo dello scratch, 2026-11-08):

* **Le dodici tabelle:** nessun trigger. Undici hanno le due colonne `NOT NULL DEFAULT now()` /
  `DEFAULT CURRENT_USER`; `fk_index_policy` le ha nullable e senza default. Il rollback le rimette così.
* **Scrittori:** solo i sei changeSet congelati di `80_data` (§23.2; l'ultimo è il `20261013-51`) e i cinque loader.
  `dbops.fn_seed_automazione_overlap` le scriveva, ma è ritirata dal `20261104-10` (in `20_code`, prima di `80_data`).
  `fn_populate_fk_index_policy` e `fn_seed_fk_index_policy` non le nominano; le provision di `90_end` su
  `automation_lock_columns` contano e cancellano righe, non le nominano.
* **Lettori:** nessuno. Il backend legge `domini_task`, `pipeline_task_registry` e `_impl` (`dbops_repository.py`,
  `pipeline_repository.py`) senza le due colonne; `script.fn_doc_lock_regola` nomina `data_update`/`user_update` come
  colonne tecniche **dei documenti**, non di queste tabelle. Ricadute BE: nessuna.
* **pgTAP:** `dbops/test-user-update-not-null-v1` ha `dbops.fk_index_policy` nel registro del debito; dopo il `DROP`
  il suo test 2 («ogni voce è ancora nullable») è rosso finché la voce non esce. Esce nello stesso blocco.
* **L'ordine:** il `DROP` in `80_data/changelog/20261109-31`, dopo i congelati. Su dbdev i cinque loader ripuliti
  si rilanciano (checksum cambiato, `ANY`) prima del `DROP`, nello stesso update, e non scrivono più le colonne.

**Il `fk_index_policy.csv` non si ritira in questo blocco: passa al blocco 10d.** Nessun changeSet lo carica, ma il
file non è inerte nel significato: è l'**unica** sede scritta di decisioni `consentito = true` che da zero non
nascono. Fatto datato, letto il 2026-11-08 col CSV caricato in una tabella temporanea (`BEGIN … ROLLBACK`): sulle
FK vive il CSV ha 129 righe `true`; sullo scratch, costruito da zero, 2 sono `true`, 24 ci sono con un altro valore e
103 mancano (101 di queste hanno comunque un indice, nato dal changeSet della tabella). Su dbdev le righe del CSV
ci sono quasi tutte (353 su 372): vengono dal carico di gennaio, non da un changeSet di oggi. Non è la misura che
decide: sul modello, il registro dice «questa FK ha l'indice per decisione», e quella decisione da zero non ha
scrittore. È la domanda del blocco 10d (Q14 ②: «quelle scritte da un seed diventano decisioni», col censimento dei
seed): lì il CSV si legge riga per riga, le decisioni vere passano a un seed caricato, e solo allora il file si
ritira. Ritirarlo oggi toglierebbe l'unica traccia di quelle decisioni senza cambiare nessun database. In questo
blocco il CSV **non si tocca** (senza loader, le sue due colonne non incidono su niente).

**Che cosa si scrive:**

| changeSet / file | Che cosa |
| --- | --- |
| `80_data/changelog/20261109-31` | `DROP COLUMN data_update, user_update` sulle dodici tabelle di B; rollback che le rimette coi default e la nullabilità di oggi |
| i cinque CSV e i cinque loader di §23.2 | via le due colonne dall'header, dalle righe e dalle voci `column:` (mirror vivi, in place) |
| `dbops/test-user-update-not-null-v1` | `dbops.fk_index_policy` esce dal registro del debito, col commento |
| `dbops/test-marcatori-automazione-senza-esecutore-v1` | il test 14 (chiusure del 7-bis) si estende alle dodici tabelle di B: nessuna ha più `data_update`/`user_update` |
| doc | nota di migrazione nelle dodici pagine `dbops/manual/`; `automazione-db.md` §1.1 chiude il residuo B; schede auto-generate da rigenerare |

#### 23.11.1 Che cosa è scritto (2026-11-08)

Tutto quanto nella tabella qui sopra, più due precisazioni di regola che il blocco rende esplicite:
`automazione-db.md` §1.1 e `linee-guida-sql.md` §7 dicono ora che conta chi **aggiorna** la riga, non chi la
inserisce (il caso di `fk_index_policy`); in §1.1 i cataloghi delle regole del framework entrano nell'elenco dei
cataloghi senza le due colonne. `fk_index_policy.md` (manual) non cita più `test-user-update-not-null-v1` ma il
test 14 del presidio dei marcatori. `automazione_codice_eccezioni.md` prende la sezione delle note di migrazione,
che non aveva.

#### 23.11.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dallo YAML dopo la riga `BEGIN;`, `BEGIN … ROLLBACK`)

Regressione «senza → con» sui **40** pgTAP che nominano le dodici tabelle, col `databasechangelog` invariato
prima e dopo la corsa (8091 → 8091): **nessun file cambia esito**. Quattro rossi identici prima e dopo, non del
blocco: `magazzino/test-documenti-interni-guard-v1` (15/18), `magazzino/test-ubicazioni-guard-parent-v1` (12/13),
`vendite/test-esecutivi-ba-coppia-v1` (38/39) e `vendite/test-snapshot-indirizzi-fattura-v1` (15/16): lo scratch è
condiviso col lotto M dell'altro cantiere, e da owner; come app li dirà la corsa di Tid.

I due pgTAP riscritti, nei due versi:

| File | Nuovo, senza il `-31` | Vecchio, col `-31` | Nuovo, col `-31` |
| --- | --- | --- | --- |
| `dbops/test-marcatori-automazione-senza-esecutore-v1` (16) | rosso il 14 (il difetto) | 16/16 (non lo vedeva) | 16/16 |
| `dbops/test-user-update-not-null-v1` (4) | rosso l'1 (`fk_index_policy` nullable fuori registro) | rosso il 2 (voce chiusa nel registro) | 4/4 |

Guardrail `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `pgtap_preambolo`, `precondition_seed`,
`run_on_change`, `sql_letterali`, `timestamp_senza_fuso`, `v1_congelato` verdi sui file del blocco. I cinque
loader ripuliti non si provano senza un `update` (vietato): non nominano più le due colonne, e il loro CSV
nemmeno, quindi l'upsert non le tocca prima né dopo il `DROP`.

#### 23.11.3 Per Tid

1. Apply su dbdev e scratch: `20261109-31`; si rilanciano da soli (checksum cambiato, `runOnChange` + `ANY`) i
   cinque loader `20260110-15`, `20260123-11`, `20260208-06`, `-07`, `-08`.
2. pgTAP come app: `dbops/test-marcatori-automazione-senza-esecutore-v1` (runner owner),
   `dbops/test-user-update-not-null-v1`, `dbops/test-pipeline-task-registry`, `dbops/test-lock-columns-convergenza`,
   `dbops/test-delete-block-audit-v1`, `dbops/test-automazione-guard-utility-tipo-ruolo`,
   `dbops/test-indici-letture-trasversali-v1`.
3. Le schede auto-generate delle dodici tabelle si rigenerano con `gen_db_docs.py`.
4. Ricadute BE: **nessuna** (§23.11, lettori).

#### 23.11.4 Chiusura del blocco b (2026-11-08)

Tid ha applicato il blocco 7-bis-b su dbdev e scratch (`20261109-31` e i cinque loader rilanciati) e ha lanciato i
pgTAP di §23.11.3: verdi. Letto su tutti e due i database (sessione DB, sola lettura): il `-31` è in
`databasechangelog`, e nessuna delle dodici tabelle ha più `data_update` o `user_update`. Le schede auto-generate
delle dodici tabelle si rigenerano con `gen_db_docs.py` ed entrano nel commit. **Il blocco b è chiuso**; restano da
committare i suoi file (§23.11.1). Il prossimo è il blocco 7-bis-c (`ui` nell'ambito, §23.3), al via di Tid.
Committato da Tid in `286117c2f6`.

### 23.12 Blocco 7-bis-c — `ui` nell'ambito: il censimento (2026-11-08)

Il §20.8.2, punto 3, chiede il censimento **prima** di scrivere: con `ui,*all` in `automation_scope` la
convergenza monta su `ui` tutto ciò che le regole prevedono, non solo l'audit. Struttura letta sul catalogo dello
scratch, corpi delle funzioni e backend; i conteggi sono fatti datati, non il motivo.

**Che cosa monterebbe, regola per regola** (`automation_rules_tbl`):

| Regola | Su `ui` | Perché |
| --- | --- | --- |
| AUDIT_UPDATE | **8 tabelle**: `dashboard_definizione`, `dashboard_preset`, `lista_colonna`, `lista_colonna_permesso`, `lista_definizione`, `lista_preset`, `misure_pagina`, `widget` | il runner monta solo dove ci sono **tutte e due** le colonne; le due `*_preferenza_utente` hanno `data_update` senza `user_update`, e restano fuori |
| ATTIVO | **21 FK su 22** (manca solo quella verso `misure_pagina`, che non ha `attivo`) | il REQUIRE si monta su ogni FK il cui padre ha `attivo`, **anche se la figlia non ce l'ha**; il BLOCK sul padre |
| CODICE_MAIUSCOLO | sei colonne `codice`: `lista_definizione`, `lista_colonna`, `lista_preset`, `dashboard_definizione`, `dashboard_preset`, `widget` | due sono già eccezioni (`automazione_codice_eccezioni.csv`, Tid 2026-11-04); quattro no |
| TX_ID, STORICO, LOCK_COLUMNS, DATE_VALIDITA, CLEANUP | nulla | nessuna tabella di `ui` ha `tx_id`, `storicizza`, `codice_interno`, `valido_dal`/`valido_al` o `cleanup_at` |
| registri per nome (delete block, overlap, guard utility, lock) | nulla | nessuna riga di `ui` |

**I quattro nodi.** Sono decisioni di modello: senza, la convergenza su `ui` rompe qualcosa che oggi funziona.

**N1 — `data_update` dei preset non è l'audit.** Su `lista_preset` e `dashboard_preset` la colonna è la **data
del contenuto**: la scrivono a mano `ui.trgfn_preset_data_update_contenuto` (`a20`, solo quando cambia una colonna di
contenuto, col `WHEN` del trigger) e `ui.trgfn_preset_riga_tocca_preset` (dalle righe figlie). Il flag
«preset aggiornato» la confronta con lo snapshot `preset_base_data_update` della preferenza
(`ui.fn_resolve_lista_config`, `ui.fn_resolve_dashboard_config`, `dashboard_repository.py` e
`dashboard_preferenza_service.py` lato BE). Il trigger di audit generico la riscriverebbe a **ogni** UPDATE,
anche a una riscrittura uguale fatta dal seed, e il badge si accenderebbe per tutti dopo ogni migrazione. Sul modello
è una colonna con due significati (memoria del progetto: il significato di una colonna lo dà chi la scrive).
**Proposta:** (a) la data del contenuto passa a una colonna sua sui due preset (per esempio
`contenuto_aggiornato_il`), scritta dai due trigger a mano; `data_update` diventa l'audit come altrove; i due
risolutori leggono la colonna nuova; lo snapshot della preferenza si rinomina di conseguenza (ricaduta BE). In
alternativa (b) i due preset fuori dall'audit per eccezione: la colonna resta con due significati, e la scarto.

**N2 — Il guard ATTIVO su 21 FK, sette verso altri domini.** Dentro `ui` (14) e verso `anagrafiche.emittenti_fiscali`
(`lista_preset`, `dashboard_preset`), `config.profili_accesso` (`lista_preset`, `dashboard_preset`,
`lista_colonna_permesso`), `config.aree_funzionali` e `config.azioni_processo` (`widget`). Rifiuti nuovi che ne
vengono, sul modello:

* il BLOCK sul padre: non si spegne un emittente o un profilo che ha un preset vivo; non si spegne una lista con
  colonne o preset vivi; non si spegne un preset che un utente ha scelto (`*_preferenza_utente` non ha `attivo`:
  conta ogni riga);
* il REQUIRE sulla figlia: una preferenza non si salva su un preset spento, un preset non nasce su una lista spenta.
  Le due FK delle preferenze verso il preset sono `ON DELETE SET NULL`: va verificato che il guard non le disarmi o
  non le blocchi (memoria del progetto, «SET NULL disarma»).

**Proposta:** si decide FK per FK, con le stesse due domande del registro `automazione_attivo_eccezioni`: dentro
`ui` il guard dice il vero (un preset vivo su una lista spenta è incoerente); le preferenze utente verso il preset
vanno **in eccezione**, perché la preferenza è uno stato dell'utente e la risoluzione sa già ripiegare
(`fn_resolve_*`); le sette verso altri domini vanno guardate col dominio (spegnere un emittente o un profilo non
deve fermarsi su un preset di lista). Il censimento FK per FK si scrive nel blocco, prima del changeSet.

**N3 — Il backend scrive l'audit a mano.** `ui_admin_repository.py` passa `user_update` come parametro e mette
`data_update = now()` in `extra_set` negli UPDATE di `lista_definizione`, `lista_colonna` e `lista_preset`. Con il
trigger generico (che legge `app.jwt_user`) è la stessa regola su due livelli. **Ricaduta BE** (BE11, da aprire in §5):
gli UPDATE non scrivono più le due colonne. Sui preset va insieme a N1: oggi l'`extra_set` sposta la data del
contenuto anche quando l'admin cambia solo `attivo`.

**N4 — Le sette tabelle di `ui` nel registro del debito.** In `dbops/test-user-update-not-null-v1` ci sono
`dashboard_definizione`, `dashboard_preset`, `lista_colonna`, `lista_colonna_permesso`, `lista_definizione`,
`lista_preset` e `widget`: `user_update` nullable e senza default. Il test 3 del file diventa rosso appena prendono
l'audit (una voce che prende l'audit si chiude). Quindi nello stesso blocco: backfill dei NULL, `DEFAULT
CURRENT_USER` e `NOT NULL`, le voci fuori dal registro. ⚠️ Il backfill è un `UPDATE` su tabelle con `attivo`:
va scritto **prima** che la convergenza monti i guard, o li attraversa (memoria del progetto sul backfill).

**Codici (CODICE_MAIUSCOLO).** I codici di `lista_preset` (`clienti_default`), `dashboard_definizione` (`home`),
`dashboard_preset` (`home_default`) e `widget` (`home.benvenuto`) sono chiavi tecniche come quelle delle liste, lette per
nome da viste, BE e FE. **Proposta:** quattro righe in più in `automazione_codice_eccezioni.csv`, col motivo della
decisione del 2026-11-04.

**Il resto, senza nodi:** nessuna tabella di `ui` è sotto RLS né ha shadow in `storico`. Nella politica degli
indici entrano le FK di `ui` che i CSV `fk_index_policy_ui.csv` e `fk_index_policy_dashboard.csv` non
coprono già: si legge nel blocco. Nella guida `automazione-db.md` la frase «gli schemi fuori ambito (`ui`,
`dbops`)» cambia.

**Ordine proposto:** N4 (backfill e `NOT NULL`, `00_schema`) e N1 (la colonna del contenuto, i due trigger e i due
risolutori, `00_schema` e `20_code`), poi le eccezioni (ATTIVO e codici, `80_data`), e per ultima la riga
`ui,*all` di `automation_scope.csv`. Così la convergenza trova il terreno pronto. BE11 si apre insieme a N1 e N3.
**Numeri:** dal `20261109-32`, salvo conferma; il lotto M dell'altro cantiere tiene fino al `-30`.

**Decisioni di Tid, prima di scrivere:**

1. N1: (a) colonna del contenuto separata, o (b) i preset fuori dall'audit?
2. N2: il criterio per le FK del guard ATTIVO, cioè dentro `ui` sì, preferenze in eccezione, le sette verso altri
   domini da guardare una per una. Oppure un altro.
3. Le quattro eccezioni di CODICE_MAIUSCOLO.
4. BE11 (N1 + N3) al team BE, coordinata: lo snapshot della preferenza cambia nome se passa (a).

✅ **Decise da Tid (2026-11-08): tutte come da proposta.** N1 (a), la colonna del contenuto separata; N2 col criterio
proposto; le quattro eccezioni dei codici; BE11 al team BE. Numeri dal `20261109-32`.

#### 23.12.1 Due correzioni al censimento, trovate scrivendo (2026-11-08)

1. **I codici erano già tutti in eccezione.** Le quattro righe proposte (`lista_preset`, `dashboard_definizione`,
   `dashboard_preset`, `widget`) stavano già in `automazione_codice_eccezioni.csv`, decise da Tid il 2026-11-04 con le
   altre due: il censimento ne aveva lette solo due. Il CSV non cambia, il pgTAP del blocco lo controlla.
2. **N2, il criterio precisato.** Il BLOCK (`dbops.trgfn_prevent_deactivate_if_children`) conta **ogni** riga figlia
   quando la figlia non ha `attivo`. Le figlie di `ui` senza `attivo` sono righe di **composizione** (le colonne di un
   preset, i widget di una dashboard o di un preset, i permessi di una colonna): col guard un preset non si
   spegnerebbe mai, perché ha sempre le sue colonne. «Dentro `ui` il guard dice il vero» vale fra due entità che hanno
   entrambe `attivo`. Le parti vanno in eccezione come le preferenze: spegnere il tutto spegne le parti, e quale parte
   mostrare lo decidono i risolutori. Le sette FK verso altri domini, guardate una per una: le cinque verso emittente e
   profilo in eccezione (spegnere un'azienda o un profilo è un gesto del dominio); le due di `widget` verso area e
   azione **tengono** il guard, perché sono due entità con `attivo` e un widget acceso su un'area spenta è incoerente.
   Restano col guard **5 FK**: `lista_colonna.lista_id`, `lista_preset.lista_id`, `dashboard_preset.dashboard_id`,
   `widget.area_id`, `widget.azione_id`. In eccezione **16**. Nessun controesempio oggi sulle cinque (letto su
   dbdev e scratch, 2026-11-08): il rilancio di un loader non le fa scattare.

#### 23.12.2 Che cosa è scritto

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/ui/20261109-32` | `contenuto_aggiornato_il` sui due preset (backfill dalla data di oggi, poi `NOT NULL DEFAULT now()`, COMMENT); lo snapshot delle due preferenze si rinomina `preset_base_contenuto_aggiornato_il` |
| `00_schema/ui/20261109-33` | le sette tabelle del debito: backfill dei NULL dalla nascita, `data_update`/`user_update` `NOT NULL` col DEFAULT |
| `20_code/ui/20261109-34` | nasce `ui.trgfn_preset_contenuto_aggiornato`, i due trigger `a20` si ricreano col nome nuovo e lo stesso `WHEN`; `ui.trgfn_preset_data_update_contenuto` si ritira |
| `20_code/ui/20261109-35` … `-39` | `trgfn_preset_riga_tocca_preset`, le due `z90_clear_preset_base_ts`, `fn_resolve_lista_config`, `fn_resolve_dashboard_config`: corpo dal catalogo, cambiano solo le righe della colonna; rollback = il corpo di prima |
| `automazione_attivo_eccezioni.csv` | le 16 FK di §23.12.1 col motivo (preferenze, composizione, altri domini) |
| `automation_scope.csv` | `ui,*all` |
| pgTAP | nuovo `ui/test-ui-nell-ambito-v1` (10); riscritti sulla colonna nuova `ui/test-fn-resolve-lista-config-cascata-per-chiave-v1`, `ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1`, `ui/test-fn-resolve-lista-config-preset-aggiornato-v1`; in `dbops/test-user-update-not-null-v1` escono le sette voci di `ui` (resta `dbops.transaction_ids`) |
| doc | `ui/manual/`: `lista_preset`, `dashboard_preset`, le due preferenze, i due risolutori, le due `z90`; `automazione-db.md` §1.1 (`ui` nell'ambito, le eccezioni) e §CODICE_MAIUSCOLO |

`ui` è già fra gli schemi dell'applicazione nei due elenchi (loop dei grant di `ci_apply` e provisioning): a
differenza di `shop` al §22, non serve un changeSet di grant.

#### 23.12.3 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML dopo la riga `BEGIN;`, `BEGIN … ROLLBACK`)

L'SQL di `-32` … `-39` nell'ordine del migrate, più le righe nuove dei due CSV in upsert, gira fino in fondo sullo
scratch e su **dbdev** (coi dati veri del backfill). La convergenza si è simulata nella stessa transazione coi tre
runner (`fn_run_automations_audit_update`, `_attivo`, `_codice_maiuscolo` su `ui`, con `config` e `anagrafiche` per i
padri): monta l'audit sulle **8** tabelle attese, REQUIRE e BLOCK sulle **5** FK col guard (10 trigger), nessun guard
sulle 16 in eccezione, nessun `CODICE_MAIUSCOLO` su `ui`.

Regressione sui **38** pgTAP che nominano `ui`, in tre modi (senza il blocco, col blocco, col blocco più la
convergenza), col `databasechangelog` invariato: **nessun file cambia esito**. Rossi identici nei tre modi, non del
blocco: `config/test-pannello-porta-v1` (8/11), `script/test-fn-is-proprietario-tabella-v1` (5/7),
`script/test-search-soggetti-universale` (7/22), `ui/test-lista-competenza-gruppi-colonna-emittente-v1` (6/7),
`ui/test-lista-definizione-multi-emittente-v1` (3/9), `ui/test-lista-definizione-perimetro-emittente-v1` (7/8),
`ui/test-misure-pagina-v1` (17/18): da owner; come app li dirà la corsa di Tid. I file riscritti, nella versione nuova
senza il blocco, muoiono sulla colonna che non c'è; `ui/test-ui-nell-ambito-v1` 3/10 senza, 10/10 con e con la
convergenza; `dbops/test-user-update-not-null-v1` 3/4 senza (le sette tabelle nullable fuori dal registro), 4/4 con e
con la convergenza. Guardrail verdi sui file del blocco.

#### 23.12.4 Per Tid

1. Apply su dbdev e scratch: `20261109-32` … `-39`; i loader di `automazione_attivo_eccezioni.csv` (`20260925-49`) e
   di `automation_scope.csv` (`20250918-01`) si rilanciano da soli. **Poi `make db-ci-apply`** (o la passata
   `ci_apply`): è lì che i trigger montano su `ui`.
2. ⚠️ **BE11 va insieme**: dopo l'apply il salvataggio delle preferenze si rompe finché il BE non usa il nome nuovo
   dello snapshot (§5).
3. pgTAP come app: `ui/test-ui-nell-ambito-v1` (runner owner), i tre riscritti, `dbops/test-user-update-not-null-v1`,
   `dbops/test-codice-maiuscolo-v1`, `dbops/test-automazione-attivo-eccezioni-v1`, `ui/test-fn-resolve-lista-config`,
   `ui/test-fn-resolve-dashboard-config`.
4. Le schede auto-generate di `ui` (le tabelle toccate, le funzioni, la funzione nuova; quella ritirata sparisce) si
   rigenerano con `gen_db_docs.py`.

#### 23.12.5 Chiusura del blocco c (2026-11-08)

Tid ha applicato il blocco 7-bis-c su dbdev e scratch (`20261109-32` … `-39` e i due CSV), ha fatto girare la
convergenza e ha lanciato i pgTAP di §23.12.4: verdi. Letto su tutti e due i database (sessione DB, sola lettura): gli
otto changeSet sono in `databasechangelog`, `ui,*all` è nell'ambito, il trigger di audit è montato sulle 8 tabelle
attese, REQUIRE e BLOCK sulle 5 FK col guard (10 trigger), nessun `CODICE_MAIUSCOLO` su `ui`. Le schede auto-generate
sono rigenerate. **Il blocco c è chiuso, e con lui il giro 7-bis.** Resta BE11 al team BE (§5). Residuo del giro:
`cleanup_at` riconosciuto per nome (§23.5, punto 4) e il `fk_index_policy.csv` orfano, passato al blocco 10d.

## 24. Giro 9 — il processo vivo, e correzioni locali: preparazione (2026-11-08)

Difetti del giro (§8): D11 (Q2) con Q14 ⑤ e la scelta 3 di §18.4; D38, D39 (Q5); D8, D12, D22, D24, D52; Q14 ⑨.
Riverificati sulla struttura dello scratch `zeroerp_ruoli` (da owner, sola lettura). **Niente è scritto**: si
aspetta il via, con l'intervallo dei numeri.

### 24.1 La riverifica

| # | Esito | Che cosa c'è in più rispetto a §2 |
| --- | --- | --- |
| D11 | ✅ confermato | I lettori del ritiro sono **dodici**, non sette: le sette viste (`vw_emittenti_non_serviti`, `vw_processi_dominio_senza_difesa`, `…_senza_emittente`, `…_senza_identita`, `…_su_pgagent`, `vw_processi_programmazione`, `vw_processi_roster`) leggono `attivo AND obsoleto_dal IS NULL`; `script.fn_crea_utente_tecnico` e `script.fn_scope_identita_processo` lo stesso; `maintenance.fn_sveglia_accesa`, `dbops.trgfn_processi_accensione_guard` e `dbops.fn_processo_acceso_dichiarato` (via `fn_processo_acceso_su_valori`) leggono `obsoleto_dal IS NOT NULL`. Il test 8 di `test-processi-registro.sql` legge il solo `attivo` (§9.6 di `work-done/brief-db-sveglia-dei-processi`). Nel backend `processi_repository.py` filtra su `p.attivo` (`:238-240`). Nessuno legge la data come data: **un ritiro programmato spegne il processo il giorno in cui si scrive, non il giorno del ritiro** (nodo N1) |
| ⑤ | ✅ confermato | Il guard si riconosce da `proname = 'trgfn_guard_emittente_scope'`, senza schema né `tgenabled`. La nota del bersaglio `dbops.coda_lavori` in `processi_bersagli.csv` dice ancora «la RLS si arma solo quando il drenatore … lavora per azienda»: la RLS è accesa dal blocco 5b, la nota è stantia |
| D38 | ✅ confermato | `chk_automazione_chiusura_scadenze_classe` ammette anche `NULL` nel testo (la colonna è NOT NULL). Chiamanti di `p_classe`: il solo `db/pgtap/dbops/test-chiusura-scadenze-classe.sql:101` (`'MANUTENZIONE'`); l'handler chiama senza argomenti e resta compatibile |
| D39 | ✅ confermato | Il ramo `VARCHAR` fa sempre l'UPDATE dinamico; nel ramo `FK` la porta (`script.trgfn_doc_stato_solo_dal_verbo` per OID) si guarda, e senza porta il verbo dichiarato è ignorato. Le tre righe di oggi sono `FK`, con porta e verbo (fatto datato) |
| D8 | ✅ confermato | Esclude solo `indisprimary`; nessun riguardo per `conindid` né `indisreplident` |
| D12 | ✅ confermato | `SELECT … INTO` senza riga **assegna NULL** (non lascia il `FALSE` iniziale): con la riga assente, o `default_value` NULL, `IF NOT v_bypass_enabled` non entra e l'override di sessione non si legge. Il ramo «parametro assente» scrive `E_ERRORE_PARAMETRI_TABELLA` con `fn_log_error_only` (un `E_` che non ferma). Il `RAISE;` dopo `fn_log_and_raise_error` è irraggiungibile |
| D22 | ✅ confermato | CHECK `codice !~ '^[EW]_[A-Z0-9_]+$'` su `dbops.messaggi_errore_codici_legacy`; la costante `c_convenzione` in `scripts/sql/guardrail_codice_errore_strutturato.sql` |
| D24 | ✅ confermato | La vista unisce **ogni** pattern che combacia: un codice preso da EXACT e da un LIKE esce due volte, e la seconda riga nomina un `target` che la funzione non ha usato. Presidio esistente: `db/pgtap/dbops/test-vw-parameter-fk-surrogate-dangling-v1.sql` |
| D52 | ✅ confermato | `fn_storico_arma_scope` (`v_owner <> current_user` → `SKIP_OWNER`) e `fn_storico_backfill_scope` (`v_owner = current_user`); `fn_ensure_storico_table` usa già `pg_has_role(…, 'MEMBER')` o `rolsuper`. Altro chiamante: `scripts/sql/provision_storico_scope.sql` |
| ⑨ | ✅ confermato | `chk_sessioni_utente_evento` ammette `SCADENZA`; nessun lettore in backend né frontend |

### 24.2 I nodi (decisioni di Tid)

* **N1 — `chk_processi_accensione` legge la data come presenza.** È la conseguenza della Q2 («vivo = data vuota o
  non ancora arrivata»). Oggi il CHECK pretende le quattro colonne dell'accensione **NULL** appena `obsoleto_dal` è
  scritta, e sveglia e guard sollevano `E_PROCESSO_SENZA_SVEGLIA` dallo stesso momento: un ritiro programmato
  spegne (e fa fallire) il processo in anticipo. Un CHECK non può leggere la data di oggi. **Proposta:** il CHECK
  guarda solo il canale (un processo non `CODA` dichiara sempre la sua accensione, anche da ritirato, e da ritirato
  non la legge nessuno); sveglia e guard sollevano `E_PROCESSO_SENZA_SVEGLIA` per `CODA` o per ritiro **raggiunto**.
  Le righe 23 e 24 di `processi.csv` riprendono i quattro valori (quelli che avevano prima del ritiro, da `git log`).
* **N2 — il BB «processo vivo» c'è già.** `script.fn_e_obsoleto(date)` (STABLE, «data scritta e raggiunta» nel fuso
  aziendale) è la regola del ritiro di catalogo, la stessa che usa il guard OBSOLETO. **Proposta:** i dodici lettori
  passano a `NOT script.fn_e_obsoleto(p.obsoleto_dal)` e smettono di leggere `attivo`; niente funzione nuova
  (regola del 2: sarebbe una seconda copia). CHECK nuovo `chk_processi_ritiro_con_data`:
  `attivo OR obsoleto_dal IS NOT NULL`. Il test 8 di `test-processi-registro.sql` passa allo stesso predicato.
* **N3 — la scelta 3 di §18.4: che cosa conta come difesa di scrittura.** Sulla coda lavori la difesa c'è, ed è
  doppia: per l'app la policy `FOR ALL` con `WITH CHECK` (RLS accesa; l'app ha INSERT/UPDATE/DELETE), per chi scrive
  da proprietario la porta DEFINER `dbops.fn_accoda_lavoro`. Il presidio conosce solo il guard. Strade:
  (a) resta così, la riga `DEBITO_DICHIARATO` per sempre, con la nota corretta; (b) **il bersaglio dichiara la sua
  porta** — colonna `processi_bersagli.porta_scrittura` (nome qualificato), e la vista la conta come difesa se la
  funzione esiste ed è `SECURITY DEFINER` **e** la tabella ha RLS accesa con una policy che copre INSERT e UPDATE
  con `WITH CHECK`; (c) il guard impara a riconoscere il proprietario — scartata dalla sessione DB: aprirebbe ogni
  scrittura DEFINER. **Proposta: (b)**; la riga di `coda_lavori` esce dal presidio e `debito_dichiarato` torna
  `false`.
* **N4 — D39: verbo e porta.** **Proposta:** porta e verbo si valutano prima del dispatch, in tutti e due i rami;
  un verbo dichiarato si usa **sempre** (è la porta del dominio), e una porta senza verbo si rifiuta come oggi
  (`porta_senza_verbo_di_chiusura`), anche nel ramo `VARCHAR`. L'alternativa della §2.4 (verbo senza porta →
  errore) rifiuterebbe una configurazione corretta.
* **N5 — D22: dove sta la convenzione.** **Proposta:** `dbops.fn_codice_errore_conforme(text)` IMMUTABLE in
  `20_code`; il CHECK la chiama, riscritto in `90_end` (da zero `00_schema` gira prima della funzione); il guardrail
  chiama la funzione al posto della costante.
* **N6 — D12: il codice.** **Proposta:** `COALESCE(…, false)` sulla lettura del parametro; il ramo «parametro
  assente o NULL» scrive un `W_` nuovo, `W_TXID_BYPASS_PARAMETRO_ASSENTE` (messaggio registrato, id dal primo
  libero); via il `RAISE;` irraggiungibile. Porta BE6.

Senza nodo, come da §2 e §4: D38 (CHECK `classe = 'DOMINIO'`, `p_classe` ritirato con DROP e CREATE, rifiuto con
codice nel motore, `test-chiusura-scadenze-classe.sql` riscritto, la doc della Q5); D8 (indici di vincolo e di
replica identity primi nell'ordinamento ed esclusi da `indici_da_droppare`); D24 (un risolutore del pattern usato
da funzione e vista, `LATERAL … LIMIT 1`); D52 (membership nei due punti); ⑨ (`SCADENZA` esce dal vincolo, col
conteggio prima).

### 24.3 I blocchi

* **9a — il processo vivo:** D11 con N1 e N2, ⑤ con N3, il test 8. Tocca `processi`, `processi_bersagli`, i due CSV,
  le sette viste e le cinque funzioni: si apre una volta.
* **9b — le correzioni locali:** D38, D39, D8, D12, D22, D24, D52, ⑨. Ognuna sul suo oggetto; si possono provare
  insieme.

Ricadute BE, da scrivere in §5 al via: **BE12** — il filtro `attivo` di `processi_repository.py` diventa «vivo»
(letto dal DB, non ricalcolato); **BE6** per `W_TXID_BYPASS_PARAMETRO_ASSENTE`; il commento dell'handler della
chiusura (`chiusura_scadenze_handler.py:16`) se nomina `p_classe`.

**Numeri:** l'ultimo occupato del 2026-11-09 è il `-39` (blocco 7-bis-c); `-21` … `-30` sono dell'altro cantiere.
L'intervallo lo dà Tid.

### 24.4 Il via (Tid, 2026-11-08)

«ok procedi da primo libero»: N1-N6 come da proposta, numeri dal primo libero. Il primo libero, riletto
su albero, dbdev e scratch subito prima di scrivere, era il `20261109-40`; il giro ha preso `-40` … `-57`.

### 24.5 Che cosa è scritto

**Blocco 9a — il processo vivo**

| changeSet | Che cosa |
| --- | --- |
| `00_schema/dbops/20261109-40` | `chk_processi_ritiro_con_data` (`attivo OR obsoleto_dal IS NOT NULL`); `chk_processi_accensione` sul solo canale, `NOT VALID` (N1); COMMENT di `attivo`, `obsoleto_dal` e dei due vincoli |
| `00_schema/dbops/20261109-41` | `processi_bersagli.porta_scrittura` con il CHECK del nome qualificato (N3) |
| `20_code/dbops/20261109-42` | `fn_processo_acceso_su_valori` (IMMUTABLE → STABLE, firma invariata) e `trgfn_processi_accensione_guard`: «senza sveglia» = CODA o ritiro raggiunto; COMMENT di `fn_processo_acceso_dichiarato` |
| `20_code/maintenance/20261109-43` | `maintenance.fn_sveglia_accesa`: lo stesso |
| `20_code/script/20261109-44` | `script.fn_crea_utente_tecnico`, `script.fn_scope_identita_processo`: processo vivo da `script.fn_e_obsoleto` |
| `20_code/dbops/20261109-45` | sei viste dei processi (`vw_emittenti_non_serviti`, `…_senza_emittente`, `…_senza_identita`, `…_su_pgagent`, `vw_processi_programmazione`, `vw_processi_roster`): processo vivo da `script.fn_e_obsoleto`; COMMENT al presente |
| `20_code/dbops/20261109-46` | `vw_processi_dominio_senza_difesa` (⑤, N3): guard per OID, acceso, su INSERT e UPDATE; porta DEFINER dichiarata con RLS e policy su INSERT e UPDATE; processo vivo |
| `90_end/20261109-47` | `VALIDATE` di `chk_processi_accensione` dopo il CSV |
| `80_data` | `processi.csv`: righe 23 e 24 con l'accensione (`f,f,t,…,t`, vedi §24.6 punto 1); `processi_bersagli.csv`: colonna `porta_scrittura`, riga 53 (`dbops.coda_lavori`) con `dbops.fn_accoda_lavoro`, `debito_dichiarato = false`, nota riscritta; `codici_errore.csv`: descrizione di `E_PROCESSO_SENZA_SVEGLIA` |

**Blocco 9b — le correzioni locali**

| changeSet | Che cosa |
| --- | --- |
| `00_schema/dbops/20261109-48` | `chk_automazione_chiusura_scadenze_classe` = `DOMINIO` (D38), col controllo delle righe prima; COMMENT della colonna |
| `00_schema/dbops/20261109-49` | `chk_sessioni_utente_evento` senza `SCADENZA` (⑨), col conteggio prima; COMMENT di tabella e colonna |
| `20_code/dbops/20261109-50` | `fn_apply_chiusura_scadenze()`: DROP della `(text)`, CREATE senza `p_classe` (D38), rifiuto di un bersaglio non DOMINIO (motivo `classe_senza_esecutore`), porta e verbo prima del dispatch in tutti e due i rami (D39, N4); GRANT all'app |
| `20_code/dbops/20261109-51` | `vw_duplicate_indexes` (D8): indici di vincolo (`conindid`) e di replica identity primi ed esclusi da `indici_da_droppare` |
| `20_code/dbops/20261109-52` | `trgfn_tx_id_managed` (D12, N6): parametro assente = spento con `W_TXID_BYPASS_PARAMETRO_ASSENTE`, l'override di sessione si legge; via il `RAISE` irraggiungibile |
| `20_code/dbops/20261109-53` | `dbops.fn_codice_errore_conforme(text)` IMMUTABLE (D22, N5) |
| `20_code/script/20261109-54` | `script.fn_parameter_fk_surrogate_regola(text)` → l'id della regola (D24); `fn_check_parameter_fk_surrogate` la chiama |
| `20_code/dbops/20261109-55` | `vw_parameter_fk_surrogate_dangling` dal risolutore |
| `20_code/dbops/20261109-56` | `fn_storico_arma_scope`, `fn_storico_backfill_scope` (D52): `pg_has_role(…, 'USAGE')` |
| `90_end/20261109-57` | `chk_messaggi_errore_codici_legacy_non_conforme` chiama la funzione |
| `80_data` | `codici_errore.csv` e `messaggi_errore.csv`: `W_TXID_BYPASS_PARAMETRO_ASSENTE` (AVVISO, id messaggio **1459**) |
| `scripts/sql` | `guardrail_codice_errore_strutturato.sql` chiama `dbops.fn_codice_errore_conforme` al posto della costante |

pgTAP nuovi: `dbops/test-processo-vivo-v1` (26), `dbops/test-vw-duplicate-indexes-vincoli-v1` (5),
`dbops/test-tx-id-bypass-parametro-assente-v1` (5), `dbops/test-codice-errore-conforme-v1` (6),
`dbops/test-sessioni-utente-evento-v1` (2), `dbops/test-storico-scope-proprietario-membership-v1` (4).
Riscritti o estesi: `dbops/test-chiusura-scadenze-classe` (11, sul contratto nuovo, con D39),
`dbops/test-vw-parameter-fk-surrogate-dangling-v1` (4 → 6), `dbops/test-processi-accensione-v1` (test 1: STABLE),
`dbops/test-processi-registro` (test 8 e 15 col processo vivo), `dbops/test-fn-guardiano-digest` (il ritiro si scrive
con la sola data).

### 24.6 Le scelte dentro il giro (da guardare, Tid)

1. **Le righe ritirate 23 e 24 non avevano mai avuto l'accensione** (le colonne sono nate dopo il ritiro): la
   proposta N1 diceva «i valori di prima», che non esistono. Hanno preso i valori neutri di un processo spento:
   spento in tutti e due gli ambienti, spegnibile, accendibile in produzione. Con `accendibile_in_produzione = false`
   il test 43 di `test-processi-accensione-v1` («i non accendibili sono solo `smoke_notturno`») andava rosso: da
   ritirati quei valori non li legge nessuno, e `true` è quello che non dice niente.
2. **Il BB del processo vivo è `script.fn_e_obsoleto`**, come da N2: nessuna funzione nuova.
   `fn_processo_acceso_su_valori` resta «sui valori» ma diventa STABLE, perché il ritiro dipende dalla data di oggi
   (firma invariata, nessun chiamante da cambiare).
3. **D52: `USAGE`, non `MEMBER`.** `ALTER TABLE` e `CREATE POLICY` vogliono i privilegi del proprietario senza
   `SET ROLE`, cioè una membership con INHERIT; `MEMBER` è vero anche per un membro NOINHERIT, che poi fallirebbe
   sull'`ALTER`. Il caso vero (un ruolo membro) non si costruisce nei pgTAP (servirebbe CREATEROLE): il test prova la
   forma del corpo, e il limite è scritto nel file.
4. **D24: il risolutore restituisce l'id della regola**, non le sue colonne: un `RETURNS TABLE` perde la lunghezza dei
   `varchar`, e la vista del presidio non si sarebbe potuta sostituire con `CREATE OR REPLACE`. Chi legge unisce il
   registro sull'id. ⚠️ Resta un'ambiguità del registro: due `LIKE` della stessa lunghezza che prendono lo stesso
   codice non hanno un ordine definito (com'era prima). Non è un difetto di oggi del codice; se va chiusa, un vincolo
   sul registro.
5. **D12: il ramo «valore NULL» il modello non lo ammette** (`config.parameters.default_value` è NOT NULL): resta il
   solo caso «riga assente», che il `COALESCE` copre.
6. ⚠️ **Nodo nuovo, D12-bis, trovato provando D12 — non corretto, da decidere.** In fondo a `trgfn_tx_id_managed`
   `NEW.tx_id := COALESCE(dbops.tx_id di sessione, valore calcolato, uuidv7())`: l'id di sessione **vince sempre**.
   Così il ramo «id di sessione non registrato → `W_TXID_NOT_REGISTERED` e la sentinella» scrive l'avviso e poi
   assegna lo stesso l'id non registrato, contro il COMMENT e la guida («assegna nil»); e bypass e ramo normale
   danno lo stesso valore. Strade: (a) il `COALESCE` finale usa solo il valore calcolato (la sentinella vale
   davvero), (b) il ramo e il COMMENT si allineano al comportamento di oggi (l'id di sessione passa, l'avviso
   resta). Proposta: **(a)**, perché è quello che il codice `W_` promette e che la guida descrive. È la stessa
   funzione appena aperta: se Tid sceglie (a), un changeSet in coda al giro.
7. **D39: il verbo si usa sempre quando è dichiarato** (N4), anche senza porta e anche nel ramo `VARCHAR`; i pre-check
   del vocabolario (ramo `FK`) restano prima del verbo: una configurazione con codici sbagliati si rifiuta lo stesso.
8. **N3: la porta dichiarata si riconosce per nome** (`schema.nome` su `pg_proc`), non per firma: se la funzione avesse
   due firme, ne basterebbe una `DEFINER`. Il registro dichiara un nome qualificato e non una firma, e oggi la porta
   ha una firma sola; resta scritto qui perché non si perda.

### 24.10 Doc (2026-11-08)

Riallineate al comportamento nuovo le pagine `manual/` di `dbops` (processi, processi_bersagli, processi_accensione, le
tre funzioni dell'accensione, le sette viste dei processi, automazione_chiusura_scadenze, fn_apply_chiusura_scadenze,
vw_duplicate_indexes, trgfn_tx_id_managed, messaggi_errore_codici_legacy, vw_parameter_fk_surrogate_dangling, le due
dello scope di storico, sessioni_utente), `maintenance/manual/fn_sveglia_accesa.md`, `script/manual/`
(fn_crea_utente_tecnico, fn_scope_identita_processo, fn_check_parameter_fk_surrogate); due pagine nuove
(`dbops/manual/fn_codice_errore_conforme.md`, `script/manual/fn_parameter_fk_surrogate_regola.md`, i cui link alle
schede auto-generate si aprono dopo la rigenerazione); guide `processi-pgagent-funzionali.md` (Q5),
`audit-e-tracciabilita.md` (SCADENZA), `tx_id_implementation_guide.md` (il parametro assente). Debito documentale
preesistente, non toccato: `script/manual/fn_check_parameter_fk_surrogate.md` è ancora nel formato vecchio, e le
cornici di `fn_crea_utente_tecnico.md` e `fn_scope_identita_processo.md`.

### 24.7 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di Liquibase, dopo la riga `BEGIN;` di ogni file, `BEGIN … ROLLBACK`)

* L'SQL estratto dei due blocchi (con la simulazione dei CSV: righe 23, 24, 53 e il codice nuovo) si applica pulito;
  dopo, `chk_processi_accensione` e `chk_processi_ritiro_con_data` sono convalidati, `vw_processi_dominio_senza_difesa`
  è vuota (la riga di `coda_lavori` esce), `vw_parameter_fk_surrogate_dangling` vuota.
* I pgTAP nuovi e riscritti: **verdi** con l'SQL estratto, rossi senza (prima del giro).
* Tutti i pgTAP che nominano gli oggetti del giro (34 per il 9a, 25 per il 9b): **stesso esito prima e dopo**; i soli
  `not ok` sono i rossi da owner già dichiarati nei file (`test-emittente-modi-solo-migrazione-v1`,
  `test-rls-listini-ef-whitelist-write` 4-5, e i «rosso da owner» di credenziali, TOTP e contratto). Un rosso nuovo
  trovato e corretto nel giro: `test-fn-guardiano-digest` scriveva un ritirato senza accensione.
* B-7: lo snapshot delle forme dei codici è **identico** prima e dopo (227 righe).
* Il guardrail `guardrail_codice_errore_strutturato.sql` gira verde dentro la transazione col giro applicato.
* Guardrail di repository verdi: DDL su trigger generati, GRANT a ruoli batch, preambolo pgTAP, preCondition sul seed,
  `runOnChange`, letterali SQL, timestamp senza fuso, albero v1.

### 24.8 Per Tid

1. Apply su dbdev e scratch: `20261109-40` … `-57`, i CSV `processi.csv`, `processi_bersagli.csv`, `codici_errore.csv`,
   `messaggi_errore.csv` (i loader si rilanciano da soli).
2. pgTAP: i sei nuovi di §24.5, i cinque riscritti o estesi, e `dbops/test-fn-apply-chiusura-scadenze-v1`,
   `dbops/test-presidi-debito-dichiarato`, `dbops/test-vw-processi-programmazione`, `dbops/test-vw-processi-roster`,
   `dbops/test-processi-accensione-produzione-v1`, `script/test-fn-scope-identita-processo`,
   `script/test-fn-crea-utente-tecnico`, `rls/test-rls-email-outbox-ambito`, `storico/test-storico-scope-congelato-v1`.
3. La decisione sul nodo D12-bis (§24.6 punto 6).
4. Le schede auto-generate di `dbops`, `maintenance` e `script` si rigenerano con `gen_db_docs.py` dopo l'apply.

### 24.9 Ricadute BE (in §5)

* **BE12** — `backend/apps/core/db/processi_repository.py:238-240`: il filtro `attivo` dei processi non dice più se un
  processo è vivo. Il filtro «vivo» si chiede al DB (`NOT script.fn_e_obsoleto(p.obsoleto_dal)`), non si ricalcola.
* **BE6** — `W_TXID_BYPASS_PARAMETRO_ASSENTE` (AVVISO): rigenerare `error_policies_generated.py` (cambia anche la
  descrizione di `E_PROCESSO_SENZA_SVEGLIA`).
* Il commento di `chiusura_scadenze_handler.py:16` non nomina `p_classe`: niente da fare. La chiamata senza argomenti
  resta valida.

### 24.11 Chiusura (2026-11-08)

Tid ha applicato il giro 9 su dbdev e scratch e ha lanciato i pgTAP di §24.8: verdi. Letto su tutti e due i database
(sessione DB, sola lettura): i diciotto changeSet `20261109-40` … `-57` sono in `databasechangelog`. **Il giro 9 è chiuso** e
committato (solo i file del giro; dei due CSV dei codici solo le righe di `E_PROCESSO_SENZA_SVEGLIA` e
`W_TXID_BYPASS_PARAMETRO_ASSENTE`). Restano: BE12 e BE6 al team BE (§5), la decisione su D12-bis (§24.6 punto 6), la
rigenerazione delle schede auto-generate di `dbops`, `maintenance` e `script` (§24.8 punto 4; dopo, i link delle due pagine
nuove si aprono).

## 25. Giro 10a — i lock di colonna, con D12-bis: preparazione (2026-11-08)

Difetti del giro (§8): D25 (A), D28, D32, R2; BE2. In più **D12-bis**, deciso da Tid il 2026-11-08: strada **(a)** di
§24.6 punto 6. Via al giro dato da Tid lo stesso giorno. **Numeri:** `20261109-58` … `-79`, concordati con le due
sessioni DB aperte (l'altro cantiere parte dal `-80`; `-28` … `-30` restano suoi). Riletti liberi sull'albero e nei
due `databasechangelog` alle 2026-11-08 sera.

### 25.1 La riverifica (schede auto-generate di oggi, scratch per la struttura)

| # | Esito | Sul corpo di oggi |
| --- | --- | --- |
| D12-bis | ✅ confermato | In fondo a `dbops.trgfn_tx_id_managed`, `COALESCE(NULLIF(current_setting('dbops.tx_id', true), '')::uuid, v_new_tx_id, uuidv7())`: l'id di sessione vince sempre, quindi il ramo «non registrato» scrive `W_TXID_NOT_REGISTERED` e poi assegna lo stesso l'id non registrato. Secondo effetto, non scritto in §24.6: il cast nudo di quella riga **solleva** su una GUC malformata, che il blocco più in alto aveva già intercettato e trasformato in NULL. Lo dice anche il pgTAP `dbops/test-tx-id-coerenza-non-registrato.sql` (commento sopra il test 5: «residua discrepanza con la guida») |
| D25 | ✅ confermato, ⚠️ precisato | `dbops.vw_non_editable_fields` legge solo `automation_lock_columns` (`enabled = true`), senza `exec_mode`: il `codice_interno` che il runner blocca su ogni tabella dell'ambito non c'è. Quindi il form lo lascia acceso, e l'UPDATE lo rifiuta. Il resto del BE non scrive `codice_interno` fra i suoi `gaps`: compensa altre colonne (§25.4) |
| D28 | ✅ confermato | Le righe 1-4 di `lock_columns_conditional` ricopiano i tre `EXISTS` di `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva`. La divergenza del brief (`CURRENT_DATE`) l'ha già sanata `20261010-01`, ma le copie restano due. Le righe 6-13 chiamano già `catalogo.fn_articolo_usato`, cioè la forma giusta. `catalogo.articoli_componenti` non ha RLS (struttura, scratch) |
| D32 | ✅ confermato | `fn_lock_columns_divergenze` parte da `JOIN regola`: una tabella che nessuna regola `LOCK_COLUMNS` attiva copre esce dal confronto, con i suoi lock. Due varianti dello stesso buco: una regola di un altro `exec_mode` fa uscire la tabella nello stesso modo, e una tabella fuori dall'ambito (`fn_resolve_scope`, `fn_table_in_scope`, `relkind = 'r'`) non la guarda nessuno. Il test 4 di `test-lock-columns-convergenza.sql` si dice «su tutto il database» |
| R2 | ✅ confermato | `COALESCE(l.error_code, 'E_CODICE_NON_MODIFICABILE')`: `error_code` è NOT NULL senza DEFAULT dal `20261104-09` (D48) |

### 25.2 I nodi (decisioni di Tid)

* **N1 — D25: il form legge il lock VIVO, non quello atteso.** Il §2.2 proponeva «un risolutore unico del lock
  atteso, letto da vista e runner». Riverificando non regge: il lock atteso dipende da `exec_mode` (il runner lo
  calcola per `AUTO`, `CI` o `SCHEDULED`), e la vista non ha un modo da scegliere. Il form invece deve dire **ciò
  che l'UPDATE rifiuta** (§12.2 punto 1: lo stesso predicato del guard), e il guard qui è il trigger stesso.
  **Proposta:** un BB `dbops.vw_lock_columns_vivi`: una riga per tabella, trigger, colonna e codice, letta dalle
  coppie di argomenti dei trigger su `script.trgfn_lock_columns`. Lo leggono `fn_lock_columns_divergenze` (il suo
  CTE `vivo`) e `vw_non_editable_fields`, che diventa una proiezione del BB: `target_schema`, `target_table`,
  `column_name`, `error_code`, più `trigger_name`. Escono `exec_mode` e `note`, che sono attributi del registro e
  non del lock; il BE e `fn_non_editable_fields` leggono solo `column_name`. Se il vivo diverge dal registro, è il
  test 4 a diventare rosso: non tocca alla vista ripararlo. È una **revoca** della correzione scritta in §2.2, non
  di una decisione di Tid.
* **N2 — D32: una tabella senza regola.** Q3 (Tid, 2026-11-05): una riga spenta o cancellata vuol dire trigger
  tolto. **Proposta**, sulle tabelle dell'ambito:
  ① regola attiva del modo della corsa → come oggi;
  ② regola attiva **solo** di un altro modo → nessuna azione, come per le righe del registro di un altro modo
     (altrimenti `AUTO` toglierebbe ciò che `CI` crea, a ogni giro);
  ③ nessuna regola attiva (spenta, cancellata o mai scritta) → niente di atteso, e il lock vivo si toglie
     (`TOGLIE`). `codice_interno` è la colonna implicita del framework e conta sempre come nominata, quindi si
     toglie senza fermare il giro. Un'altra colonna che il registro non nomina ferma il giro con
     `E_LOCK_COLUMNS`, come oggi: lì non si cancella in silenzio.
  Fuori dall'ambito il runner non agisce: è il suo perimetro. Lo diventa invece un **presidio** nuovo nel pgTAP:
  nessun trigger su `trgfn_lock_columns` su una tabella che l'ambito non copre.
* **N3 — D28: i predicati della distinta.** **Proposta:** tre funzioni `catalogo.*`, `STABLE`, `SECURITY INVOKER`
  (la distinta non ha RLS), sul modello di `catalogo.fn_articolo_usato`:
  `fn_articolo_padre_di_distinta_in_vigore(uuid)` (check 1: `prodotto_id`, `validita @>` oggi),
  `fn_articolo_componente_di_distinta_in_vigore(uuid)` (check 2: `componente_id`, `validita @>` oggi),
  `fn_articolo_componente_di_distinta_da_oggi(uuid)` (check 3: `componente_id`, `validita &&` [oggi, ∞)).
  «Oggi» è sempre `script.fn_data_operativa()`. Il guard le chiama tutte e tre. Le righe 1-4 diventano
  `catalogo.fn_…($1::uuid)`. La riga 4 tiene la sua metà di stato («non è già composito»): nel guard è la
  transizione OLD → NEW, nel form lo stato della riga di oggi.
* **N4 — D28: come cambiano le righe 1-4.** `lock_columns_conditional` non ha un CSV. La sua sede sono cinque
  changeSet SQL di `80_data` (`20260522-04`, `20261010-01`, `20261013-04`, `-46`, `-51`), e il §11.2 non ha un
  secondo file da far divergere. Strade: (a) un changeSet nuovo di `80_data` con l'`UPDATE` di `condition_expr` e
  di `descrizione` sulle quattro righe, chiavato su colonna e testo vecchio, come `20261010-01`; (b) la tabella
  passa a un CSV con mirror, che vuol dire chiave naturale da trovare (l'UNIQUE comprende `condition_expr`), id di
  identity e cinque changeSet da ri-ancorare. **Proposta: (a).** La (b) è un giro di catalogo, non di questo
  difetto.

Senza nodo: **D12-bis** (a): il `COALESCE` finale diventa `COALESCE(v_new_tx_id, uuidv7())`, e il test 5 del pgTAP
asserisce la sentinella. **R2:** il `COALESCE` morto esce. I COMMENT degli oggetti riaperti si riscrivono al
presente, senza brief né marcatori (§5d): `fn_lock_columns_divergenze`, `fn_run_automations_lock_columns` (se il suo
testo cambia), `vw_non_editable_fields`, `fn_non_editable_fields`, il guard della distinta.

### 25.3 I changeSet previsti (`20261109-58` … `-79`)

| # | Fase | Che cosa |
| --- | --- | --- |
| `-58` | `20_code/dbops` | `trgfn_tx_id_managed` (D12-bis) |
| `-59` | `20_code/dbops` | `vw_lock_columns_vivi` (BB, N1) |
| `-60` | `20_code/dbops` | `fn_lock_columns_divergenze` (D32 con N2, R2, il CTE `vivo` dal BB) |
| `-61` | `20_code/dbops` | `vw_non_editable_fields` dal BB (D25, N1): DROP e CREATE perché le colonne cambiano, poi i GRANT; COMMENT di `fn_non_editable_fields` |
| `-62` | `20_code/catalogo` | i tre predicati (N3) |
| `-63` | `20_code/catalogo` | `trgfn_articoli_guard_flags_struttura_bom_attiva` dai predicati |
| `-64` | `80_data` | righe 1-4 di `lock_columns_conditional` (N4) |

pgTAP: `dbops/test-tx-id-coerenza-non-registrato` (test 5 più uno sulla sentinella);
`dbops/test-lock-columns-convergenza` (regola spenta → `TOGLIE` senza fermarsi su `codice_interno`; regola spenta e
colonna ignota → si ferma; regola di un altro modo → nessuna azione; il presidio fuori ambito);
`dbops/test-non-editable-fields-dal-lock-vivo-v1`, nuovo (`codice_interno` bloccato e senza riga nel registro →
elencato; colonna con la riga spenta → non elencata; `fn_non_editable_fields` lo stesso);
`catalogo/test-distinta-predicati-guard-e-form-v1`, nuovo (per ciascuno dei tre casi guard e form rispondono
uguale). Si rilanciano `dbops/test-fn-non-editable-fields-conditional`,
`catalogo/test-distinta-un-livello-e-onere-natura-v1`, `catalogo/test-articolo-usato-struttura-v1` e
`vendite/test-righe-articolo-ammesso-v1`.

### 25.4 Ricaduta BE (BE2, da scrivere in §5 al via sui nodi)

(Riscritta in §5, riga BE2, il 2026-11-08 col giro scritto.) Dopo l'apply la vista elenca **ogni colonna che un
trigger di lock blocca**, `codice_interno` compreso. I `gaps` del
BE che ripetono una colonna già bloccata dal DB si ritirano. Al 2026-11-08 sono `catalogo.articoli.codice` in
`catalogo_service.py` (bloccata da `automation_lock_columns`) e `codice` di `emittenti_fiscali` in
`emittenti_fiscali_service.py` (idem). Gli altri `gaps` (`uom_id` delle UdM operative, le dimensioni delle matrici)
non sono lock di colonna: restano finché il DB non li dichiara. La verifica la fa il team BE, colonna per colonna,
sulla vista dopo l'apply.

### 25.5 Il via sui nodi (Tid, 2026-11-08)

«ok inizia»: N1-N4 come da proposta, numeri `20261109-58` … `-79`. Riletti liberi subito prima di scrivere.

### 25.6 Che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261109-58` | `trgfn_tx_id_managed` (D12-bis): `NEW.tx_id := COALESCE(v_new_tx_id, uuidv7())`; COMMENT al presente |
| `20_code/dbops/20261109-59` | `vw_lock_columns_vivi` (N1), `security_invoker`, COMMENT di vista e colonne, `GRANT SELECT` all'app |
| `20_code/dbops/20261109-60` | `fn_lock_columns_divergenze` (D32 con N2, R2): le tre specie di tabella, il vivo dalla vista, `codice_interno` mai persa; COMMENT al presente |
| `20_code/dbops/20261109-61` | `vw_non_editable_fields` dal lock vivo (D25, N1): DROP e CREATE, `security_invoker`, GRANT; COMMENT di `fn_non_editable_fields` |
| `20_code/catalogo/20261109-62` | i tre predicati della distinta (N3), `BEGIN ATOMIC`, ognuno nel suo change; i COMMENT nell'ultimo |
| `20_code/catalogo/20261109-63` | `trgfn_articoli_guard_flags_struttura_bom_attiva` dai predicati; COMMENT al presente |
| `80_data/changelog/20261109-64` | le righe 1-4 di `lock_columns_conditional` dai predicati (N4 a), chiavate su colonna e testo di prima; si ferma se le righe aggiornate non sono quattro |
| `80_data/sql/dbops/presidi.csv` | la riga di `dbops.vw_lock_columns_vivi` (INVENTARIO) e la nota di `dbops.vw_non_editable_fields` riscritta |

`-65` l'ha preso la cura di §25.12; `-66` … `-79` restano liberi, di questo cantiere.

pgTAP: `dbops/test-tx-id-coerenza-non-registrato` (11 → 12: il 12 vuole la sentinella); `dbops/test-lock-columns-convergenza`
(22 → 29: il 23 è il presidio fuori ambito; 24 regola di un altro modo; 25-26 lock disabilitato; 27-29 regola spenta);
nuovi `dbops/test-non-editable-fields-dal-lock-vivo-v1` (9) e `catalogo/test-distinta-predicati-guard-e-form-v1` (7).

### 25.7 Le scelte dentro il giro (✅ ok di Tid, 2026-11-08)

1. **Il predicato del check 3 restituisce il codice del primo padre, non un booleano** (`fn_articolo_primo_padre_da_oggi`,
   NULL se non ce n'è). Il guard il codice lo mette nel messaggio: con un booleano, come in N3, il filtro sarebbe
   rimasto scritto due volte. La regola del form lo legge come `IS NOT NULL`.
2. **Un lock disabilitato (`tgenabled` D o R) non è allineato** e il confronto dà `RIGENERA`; la vista del form non
   ne elenca le colonne. È la stessa domanda di D32 («il lock vivo blocca davvero?»), sullo stesso oggetto.
3. **`vw_lock_columns_vivi` copre tutti gli schemi e i tipi di tabella**; l'ambito lo applica chi legge. Così il
   presidio fuori ambito (test 23) legge la stessa sede. Le tabelle partizionate (`relkind = 'p'`) restano fuori
   dal confronto, come prima: un lock su una tabella partizionata cade nel presidio fuori ambito.
4. **`vw_non_editable_fields` e la vista nuova sono `security_invoker`**, come `vw_codici_errore_argomenti_trigger`:
   leggono il catalogo di sistema, che è lo stesso per tutti.

### 25.8 Il nodo nuovo: N5 — una riga del registro su una tabella fuori ambito (da decidere, Tid)

Trovato confrontando la vista del form prima e dopo, su dbdev (2026-11-08, dentro una transazione annullata): entrano 75
righe `codice_interno` (è D25), ed **esce** `dbops.domini_task.codice`. La riga c'è in `automation_lock_columns.csv`
(riga 26, `AUTO`, attiva, «codice immutabile, lock esplicito»), ma `dbops.fn_table_in_scope('dbops', 'domini_task')` è
falso: il runner non ci arriva, nessun trigger la blocca, e l'UPDATE passa. La vista di prima diceva «bloccata»
(il falso); quella nuova dice il vero. Sul modello è una **promessa senza esecutore**: una riga del registro che nessun
giro può applicare. Strade: (a) la tabella entra nell'ambito per i lock (una regola d'ambito per `dbops.domini_task`,
o l'esclusione che la toglie si restringe); (b) la riga esce dal registro, e il codice resta modificabile; (c) un
presidio nuovo rende rossa ogni riga attiva di `automation_lock_columns` su una tabella fuori ambito, e poi (a) o (b).
**Proposta: (c) con (a)**: la riga dice una decisione (il codice è una chiave di sistema), e il presidio impedisce che
il caso si ripeta in silenzio. Non è nel giro scritto: lo apre la decisione.

**✅ Deciso (Tid, 2026-11-08): A, il codice è bloccato, ma col trigger montato a mano**: `domini_task` **non** entra
nell'ambito (che porterebbe anche le altre automazioni). Forma proposta dalla sessione DB, **confermata da Tid** (2026-11-08):
① la riga di `automation_lock_columns.csv` resta, ed è la **dichiarazione** del lock; ② il trigger lo monta un
changeSet di `20_code` (stesso nome da template, stessi argomenti che monterebbe il runner), non il runner, che fuori
dall'ambito non arriva; ③ il presidio fuori ambito (test 23 di `test-lock-columns-convergenza`) cambia regola: fuori
dall'ambito un lock è ammesso **solo** se ogni sua colonna ha una riga attiva nel registro con lo stesso codice, e
ogni riga attiva del registro su una tabella fuori ambito ha il suo lock vivo e abilitato (è la metà (c) di N5);
④ la guida (`automazione-db.md` §4.1, «un lock non si scrive a mano») dice l'eccezione: fuori dall'ambito il lock lo
monta una migrazione, e il registro lo dichiara comunque. Va nel giro 10b, che rifà l'ambito (D13).

### 25.9 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase, `BEGIN … ROLLBACK`)

* L'SQL estratto passa su scratch e dbdev; andata e ritorno (changes, poi rollback all'indietro) passa sullo scratch.
* Ogni `- sql:` passato anche dal driver di Liquibase (`postgresql-42.7.10.jar`, un `Statement.execute` per change, in
  transazione annullata): i tre `BEGIN ATOMIC` di `-62` compresi.
* L'upsert di **tutto** `presidi.csv` rifatto in transazione (59 righe): il mirror è risvegliabile.
* pgTAP, con l'SQL del giro inserito dopo la riga `BEGIN;`: sullo scratch verdi i quattro del giro (12, 29, 9, 7) e
  `dbops/test-fn-non-editable-fields-conditional` (4), `catalogo/test-distinta-un-livello-e-onere-natura-v1` (14),
  `vendite/test-righe-articolo-ammesso-v1` (18), `dbops/test-catalogo-presidi-v1` (11), `catalogo/test-articolo-colonne-struttura-v1` (12); su dbdev verdi i quattro del
  giro, `test-catalogo-presidi-v1` e `test-fn-non-editable-fields-conditional`.
  `catalogo/test-articolo-usato-struttura-v1`: 16 su 17, il 17 è dichiarato nel file «rosso da owner, verde come app»,
  ed è rosso uguale senza il giro.
* Guardrail Liquibase (`runOnChange`, preCondition sul seed, DDL su trigger di automazione, GRANT a ruoli batch, v1
  congelato, letterali, timestamp, preambolo pgTAP) verdi; pre-commit verde sui file del giro.
* Come app: la vista nuova si prova solo dopo l'apply (la creazione vuole l'owner).

### 25.10 Doc (2026-11-08)

Riscritte: `dbops/manual/vw_non_editable_fields.md`, `fn_lock_columns_divergenze.md`, `fn_non_editable_fields.md`,
`lock_columns_conditional.md` (la tabella regola → predicato → guard), `trgfn_tx_id_managed.md`;
`catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva.md`; `guide/automazione-db.md` §4.1 (regola spenta,
il form legge il vivo); `guide/tx_id_implementation_guide.md` Fasi 3 e 5. Nuove: `dbops/manual/vw_lock_columns_vivi.md`,
`catalogo/manual/fn_articolo_padre_di_distinta_in_vigore.md`, `…_componente_di_distinta_in_vigore.md`,
`fn_articolo_primo_padre_da_oggi.md`. Le schede auto-generate si rigenerano dopo l'apply (i link alle pagine nuove si
aprono allora).

### 25.11 Per Tid

1. **Apply** di `20261109-58` … `-64` e di `presidi.csv` su dbdev e scratch.
2. **pgTAP come app**: `dbops/test-tx-id-coerenza-non-registrato`, `dbops/test-lock-columns-convergenza`,
   `dbops/test-non-editable-fields-dal-lock-vivo-v1`, `catalogo/test-distinta-predicati-guard-e-form-v1`,
   `dbops/test-fn-non-editable-fields-conditional`, `dbops/test-catalogo-presidi-v1`,
   `catalogo/test-distinta-un-livello-e-onere-natura-v1`, `catalogo/test-articolo-usato-struttura-v1`,
   `vendite/test-righe-articolo-ammesso-v1`, `catalogo/test-articolo-colonne-struttura-v1`.
3. **N5** (§25.8).
4. Le scelte di §25.7.

### 25.12 Dopo l'apply: il presidio su tutto il database è lento (Tid, 2026-11-08)

Tid ha applicato `20261109-58` … `-64` e `presidi.csv` su dbdev e scratch: pgTAP verdi. Il test 4 di
`dbops/test-lock-columns-convergenza` però è **lento**: misurato sullo scratch, `fn_lock_columns_divergenze('CI', NULL)`
passa da circa 80 ms (corpo di prima, ricreato in transazione) a 9,7 s. La causa è nel `-60`: il planner stima **una**
riga per il CTE `regola` e lo unisce a `tab` con un nested loop, e il filtro `dbops.fn_col_exists(…, 'codice_interno')`
si rivaluta per ogni coppia (tabelle × tabelle). Prima lo stesso filtro stava in un CTE letto una volta sola.

Cura, `20_code/dbops/20261109-65`: la colonna `ha_ci` si calcola in `tab` (`MATERIALIZED`), una volta per tabella, e il
JOIN confronta un boolean. Comportamento invariato; COMMENT invariato; rollback = corpo di `-60`. Prova (scratch e
dbdev, corpo estratto in transazione): la funzione torna a 75-135 ms, andata e ritorno passano, il pgTAP intero passa
da 9,2 s a 0,36 s, 29 su 29 verdi su tutti e due. Anche il runner ne beneficia: chiama la funzione due volte per giro.

**Per Tid:** apply di `-65`, poi `dbops/test-lock-columns-convergenza` come app.

## 26. Giro 10b — il runner e il registro delle regole: preparazione (2026-11-08)

Difetti del giro (§8): D2, D10, D13, D16, D17, D17-bis, D20, D27, R1; in più N5 del giro 10a (§25.8: il lock di
`dbops.domini_task` montato a mano). Via di Tid alla preparazione: «ok procedi» (2026-11-08). Corpi letti dal catalogo
dello scratch (2026-11-08, uguali alle schede auto-generate dopo l'apply del 10a).

### 26.1 La riverifica

| # | Esito | Sul corpo di oggi |
| --- | --- | --- |
| D2 | ✅ confermato | In `fn_run_automations_cleanup` le conversioni di `ttl_days`, `apply_on_update` e `batch_limit` stanno **fuori** dai blocchi `BEGIN … EXCEPTION`; `trgfn_cleanup_at_alla_nascita` converte `ttl_days` all'INSERT. `automation_rules_tbl` non ha nessun CHECK: un `ttl_days` testuale ferma il giro e ogni INSERT dei registri coperti |
| D10 | ✅ confermato, con controesempi | `{fkhash6_if_long}` mette l'hash solo oltre 63 caratteri: due FK corte della stessa figlia verso lo stesso padre danno lo stesso nome, e con `BOTH` (nome **o** argomenti) il runner salta la seconda. Letto sul catalogo dello scratch (2026-11-08): sette coppie hanno due FK e un solo REQUIRE (`catalogo.articoli_componenti → articoli`, `vendite.fatture_righe → articoli` e `→ unita_misura`, `vendite.ddt → magazzino.magazzini`, `vendite.ddt_righe_prelievi → ubicazioni`, `vendite.commesse_attivita → unita_misura`, `pratiche.formule_tempo → template_flussi`). Il template del BLOCK ha la stessa forma |
| D13 | ✅ confermato, ⚠️ precisato | `fn_run_automations` non c'è più (ritirata). `fn_resolve_scope` restituisce `array_agg(schema_name)` **senza DISTINCT** (oggi `dbops` compare sette volte) e, sulla lista del chiamante, filtra con `btrim` ma restituisce il valore non pulito. `fn_seed_fk_index_policy` legge `automation_scope` da sé, solo per schema |
| D16 | ✅ confermato | `fn_cleanup_at_params` (letto dal trigger alla nascita) sceglie la regola senza `exec_mode` e senza `automation_cleanup_exclusions`; il runner le applica tutte e due. Senza `base_ts_column` il trigger usa `now()`, il runner la catena `data_insert` → `executed_at` → `occurred_at` → `created_at`. Il trigger scrive sempre `cleanup_at`, il runner la colonna di `cleanup_column` |
| D17 | ✅ confermato | La strategia d'esistenza è ricopiata in `_tx_id`, `_audit_update`, `_storico`, `_date_validita` e `_attivo`, con due default diversi (`BY_NAME`, e `BOTH` in `_date_validita`); un valore sconosciuto vale «c'è già», in silenzio. `_lock_columns` e `_codice_maiuscolo` già non la leggono: riconoscono il trigger dalla funzione |
| D17-bis | ✅ confermato | `rule_type`, `exec_mode`, `existence_strategy` (`automation_rules_tbl`) e `col_role` (`automation_overrides_cols`) sono `text` senza CHECK. I ruoli letti dal codice sono sette: `ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICIZZA_COL`, `STORICO_FK`, `CODICE_COL`, `CODICE_INTERNO_COL` |
| D20 | ✅ confermato | `_storico` ripiega su `trg_z90_{table}_storico_upd_dlt`, il seed dice `trg_{table}_z90_storico_upd_dlt` |
| D27 | ✅ confermato | `_audit_update` usa gli override `AUDIT_TS`/`AUDIT_USER` (e `params.audit_ts`/`audit_user`) solo per decidere se montare; il trigger nasce senza argomenti e `script.trgfn_audit_data_user_generic` scrive `data_update`/`user_update` per nome. Oggi nessun override li usa (`automation_overrides_cols.csv`, 2026-11-08) |
| R1 | ✅ confermato, ⚠️ precisato | I dry run firmano ancora `dbops.fn_run_automations` (ritirata) in `_audit_update`, `_date_validita` **e** `_lock_columns` |

### 26.2 I nodi (decisioni di Tid)

* **N1 — D17: la strategia d'esistenza si ritira.** Q3 (Tid, 2026-11-05) ha già deciso per i tre registri che il
  trigger si riconosce dalla funzione; `_lock_columns` e `_codice_maiuscolo` lo fanno già. Il nome di un trigger è
  un'etichetta che il runner sceglie, non la sua identità: due trigger con lo stesso nome possono fare cose diverse
  (D10), e lo stesso trigger può avere un altro nome. **Proposta:** un trigger del framework si riconosce **dalla
  funzione**, e dove la funzione ha argomenti (ATTIVO) **dagli argomenti**; il nome serve solo a crearlo.
  `existence_strategy` esce dal registro (colonna, CSV, mirror) e dai cinque runner. Alternativa: un BB
  `fn_trigger_esiste(rel, strategia, …)` che rifiuta una strategia sconosciuta, più un CHECK. ℹ️ Fatto datato, non
  motivo: sullo scratch nessun trigger porta il nome del framework con una funzione diversa (2026-11-08).
* **N2 — D10: il nome del trigger ATTIVO.** Con N1 il secondo REQUIRE (o BLOCK) si riconosce mancante, ma nasce col
  nome del primo e il `CREATE` fallisce. Strade: (a) l'hash dell'FK entra nel nome **quando serve** — nome oltre 63
  caratteri **o** un'altra FK della stessa figlia verso lo stesso padre — e il runner rinomina il trigger vivo delle
  coppie che oggi ne hanno uno solo; (b) l'hash sempre, e il runner rinomina tutti i trigger ATTIVO vivi. **Proposta:
  (a)**: il nome cambia solo dove il vecchio non distingue. Nessun file del repo nomina i sette trigger da rinominare.
* **N3 — D16: una sede per la scadenza.** **Proposta:** un risolutore `dbops.fn_cleanup_at_regola(schema, tabella)`
  letto da trigger e runner: la stessa regola (priorità, poi id), le esclusioni di `automation_cleanup_exclusions`
  (tabella esclusa = nessuna scadenza), la stessa catena della colonna base, la colonna di `cleanup_column`. Il
  trigger scrive la colonna dichiarata. Sull'`exec_mode`: il trigger alla nascita non è una corsa e non ha un modo,
  quindi una regola `CLEANUP_AT` vale sempre: CHECK `exec_mode = 'AUTO'` per `CLEANUP_AT` e `CLEANUP_PURGE`.
* **N4 — D2: i parametri si validano quando la regola entra.** **Proposta:** `dbops.fn_regola_params_validi(rule_type,
  params)` IMMUTABLE, chiamata da un CHECK su `automation_rules_tbl` (in `90_end`, dopo il CSV): per `CLEANUP_AT`
  `ttl_days` intero ≥ 1, `apply_on_update` booleano, `cleanup_column` e `base_ts_column` testo; per `CLEANUP_PURGE`
  `batch_limit` intero ≥ 1. Il runner non cambia: un parametro che entra è già valido.
* **N5 — D27: la manopola delle colonne di audit si ritira.** Le colonne di audit hanno nome fisso per contratto
  (`linee-guida-sql.md` §7), e il trigger le scrive per nome su ~ogni tabella: passargli gli argomenti vorrebbe dire
  un'assegnazione dinamica per riga. **Proposta:** `AUDIT_TS`/`AUDIT_USER` escono dal vocabolario di `col_role`,
  `audit_ts`/`audit_user` dai `params` della regola 2, e il runner legge `data_update`/`user_update`. Alternativa:
  argomenti al trigger.
* **N6 — D20: il nome del trigger sta nel registro, e solo lì.** **Proposta:** `name_template` obbligatorio (CHECK,
  non vuoto) per le regole che montano un trigger (`TX_ID`, `AUDIT_UPDATE`, `ATTIVO`, `STORICO`, `LOCK_COLUMNS`,
  `DATE_VALIDITA`, `CODICE_MAIUSCOLO`), e i runner perdono i loro `COALESCE` di ripiego (oggi sono sei, e uno
  diverge). Alternativa: allineare il solo ripiego di `_storico`.

Senza nodo:

* **D17-bis:** CHECK sui vocabolari — `rule_type` (i dieci di oggi), `exec_mode` (`AUTO`, `CI`, `SCHEDULED`),
  `col_role` (i sette ruoli letti, meno i due di N5) — con la forma canonica (maiuscolo, senza spazi): i runner
  smettono di normalizzare con `upper(btrim(…))`. Va annotato in `framework-automazione-db-migliorie` §2.4.
* **D13:** `fn_resolve_scope` con `DISTINCT` sul registro e il valore pulito sulla lista del chiamante.
  `fn_seed_fk_index_policy` passa al giro **10d**, che riapre `fk_index_policy` (stesso oggetto; §8, regola degli
  oggetti insieme).
* **R1:** ogni dry run firma col nome del suo runner.
* **N5 del 10a** (§25.8, forma confermata): il lock di `domini_task` da un changeSet, il test 23 riscritto,
  l'eccezione nella guida.

### 26.3 I blocchi

* **10b-1 — il registro:** D17-bis, N1 (via `existence_strategy`), N4, N5, N6: CHECK, colonna, CSV e mirror di
  `automation_rules_tbl` e `automation_overrides_cols`.
* **10b-2 — i runner:** D17 con N1, D10 con N2, D20, D27, R1 in `_tx_id`, `_audit_update`, `_storico`,
  `_date_validita`, `_attivo`, `_lock_columns`/`fn_lock_columns_divergenze` (il ripiego del nome); D13.
* **10b-3 — la scadenza:** D16 con N3: risolutore, trigger alla nascita, runner.
* **10b-4 — il lock fuori ambito:** N5 del 10a.

Ogni blocco si prova prima del successivo; l'1 e il 2 si applicano insieme (il 2 smette di leggere ciò che l'1 toglie).

**Numeri:** restano `20261109-66` … `-79` (quattordici). Il giro 10b ne chiederà probabilmente di più: l'intervallo
in più si concorda con l'altra sessione DB al via.

Ricadute BE: nessuna. Il registro delle regole non ha API, e `backend/` non nomina `existence_strategy`, `AUDIT_TS` né
`audit_ts` (grep, 2026-11-08).

### 26.4 Il via (Tid, 2026-11-08)

«si ok procedi»: N1-N6 come da proposta, via ai blocchi 10b-1 e 10b-2 (si applicano insieme). Numeri `20261109-66` …
`-75`, riletti liberi sull'albero e nei due `databasechangelog` subito prima di scrivere.

### 26.5 Che cosa è scritto (blocchi 10b-1 e 10b-2)

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261109-66` | `dbops.fn_regola_automazione_valida(rule_type, exec_mode, name_template, params)` IMMUTABLE (N4, N6, N3): params oggetto; nome obbligatorio per le regole che montano un trigger; ATTIVO con `block` e `require`, ognuno col segnaposto dell'hash; `CLEANUP_*` in AUTO; `ttl_days` e `batch_limit` interi ≥ 1, `apply_on_update` booleano |
| `20_code/dbops/20261109-67` | `fn_resolve_scope` senza doppi e senza spazi (D13); COMMENT nuovo |
| `20_code/dbops/20261109-68` | `_tx_id`: riconoscimento per funzione (N1), nome dal registro (N6) |
| `20_code/dbops/20261109-69` | `_audit_update`: per funzione, nome dal registro, colonne di audit col nome fisso (N5: via `AUDIT_TS`/`AUDIT_USER` e `params.audit_*`), dry run col proprio nome (R1) |
| `20_code/dbops/20261109-70` | `_storico`: per funzione, nome dal registro (D20: via il ripiego divergente); l'audit firma `dbops.fn_run_automations_storico` (era senza schema) |
| `20_code/dbops/20261109-71` | `_date_validita`: per funzione, nome dal registro, dry run col proprio nome (R1) |
| `20_code/dbops/20261109-72` | `_attivo`: riconoscimento per argomenti (N1); l'hash della FK nel nome quando due FK darebbero lo stesso nome sulla stessa tabella (N2, §26.6 punto 1); un vivo col nome non atteso si rigenera (ramo reconcile); template dal registro; l'audit firma `dbops.fn_run_automations_attivo` (era senza schema) |
| `20_code/dbops/20261109-73` | `fn_lock_columns_divergenze`: nome dal registro (N6); `_lock_columns`: dry run col proprio nome (R1) |
| `80_data/changelog/20261109-74` | DROP di `automation_rules_tbl.existence_strategy` (N1), dopo il mirror |
| `90_end/20261109-75` | CHECK `rule_type`, `exec_mode`, `regola_valida` su `automation_rules_tbl`; `col_role` su `automation_overrides_cols` (D17-bis), coi COMMENT |
| `80_data` | `automation_rules_tbl.csv`: via la colonna `existence_strategy`, `params` della regola 2 a `{}`, la nota della regola 27 non nomina più la strategia (modifica sul testo, virgolette invariate); il mirror `20250918-02` perde la voce della colonna (CRLF conservati) |

pgTAP nuovi: `dbops/test-registro-regole-vincoli-v1` (17), `dbops/test-attivo-due-fk-stessa-coppia-v1` (7). Riscritti:
`dbops/test-storico-nome-funzione-ritirato-v1` (5: il 3 riconosce per funzione, il 4 vuole la colonna assente),
`dbops/test-storico-salto-trigger-presente-v1` (3, e la firma qualificata dell'audit), `dbops/test-cleanup-framework` (19): niente più
`existence_strategy`.

### 26.6 Le scelte dentro il giro (da guardare, Tid)

1. **N2 è più largo di come l'avevo scritto.** La prima prova sullo scratch (runner su tutto il database) si è fermata:
   `config.sorgenti` ha due figlie **omonime** in due schemi, `vendite.ordini` e `acquisti.ordini`, e il nome del BLOCK
   nomina le tabelle senza schema: i due nomi coincidono. Con `BOTH` il secondo BLOCK si saltava in silenzio: è D10 in
   un'altra forma. La regola dell'hash è quindi «quando due FK darebbero lo stesso nome **sulla stessa tabella**»: per il
   REQUIRE, più FK della figlia verso padri omonimi (anche lo stesso padre due volte); per il BLOCK, figlie omonime
   verso lo stesso padre. Effetto sullo scratch e su dbdev (2026-11-08, transazione annullata, fatto datato):
   **28 BLOCK e 7 REQUIRE mancavano**; il giro dei runner toglie i 35 vivi col nome che non distingue e ne crea 70.
2. **Il trigger ATTIVO col nome vecchio si rigenera, non si rinomina**: il ramo `reconcile_on_change` che c'era già
   toglie per argomenti e ricrea. Nessun file del repo nomina i 35 trigger.
3. **I runner continuano a confrontare con `upper(btrim(…))`**: con la forma canonica del CHECK è codice morto ma
   innocuo; si toglie quando ognuno si riapre. Il COMMENT del CHECK di `rule_type` e il testata di `-75` lo dicono.
4. **`fn_seed_fk_index_policy` resta al giro 10d** (§26.2, D13).

✅ **Ok di Tid** (2026-11-08): «il via era su tutto, non escludeva la 26.6».

### 26.7 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase: i `20_code`, poi il mirror del CSV rifatto su tutte le righe, poi `-74`, poi `-75`; `BEGIN … ROLLBACK`)

* L'SQL passa su scratch e dbdev; andata e ritorno (rollback all'indietro) passa sullo scratch; ogni change passa dal
  driver di Liquibase (`postgresql-42.7.10.jar`).
* **I runner sul database intero dopo il giro** (`_tx_id`, `_audit_update`, `_storico`, `_date_validita`, `_attivo`,
  `_lock_columns`, modo `CI`): solo ATTIVO cambia qualcosa (punto 1 di §26.6), uguale su scratch e dbdev; gli altri non
  creano né tolgono niente. Il runner ATTIVO vecchio e nuovo durano uguale (circa 5,3 s sullo scratch, giro allineato).
* pgTAP con l'SQL del giro dopo `BEGIN;`, sullo scratch: verdi i venticinque che nominano runner, regole o override
  (fra cui i due nuovi e i tre riscritti). Con i runner **già girati** nella stessa transazione, i trentanove che toccano i
  trigger ATTIVO: verdi tranne tre, rossi uguali senza il giro e da owner (si lanciano come app):
  `dbops/test-guard-attivo-occhi-del-proprietario-v1` (4), `rls/test-rls-listini-ef-whitelist-write` (2),
  `pagamenti/test-distinta-numerazione-registro-v1` (2). Su dbdev verdi gli otto del giro e dei runner.
* Guardrail Liquibase verdi.

### 26.8 Per Tid

1. **Apply** di `20261109-66` … `-75`, del CSV e del mirror, su dbdev e scratch; poi `make db-ci-apply` (o il giro
   delle automazioni) perché il runner ATTIVO crei i 35 trigger mancanti e rigeneri i 35 col nome vecchio.
2. **pgTAP come app**: `dbops/test-registro-regole-vincoli-v1`, `dbops/test-attivo-due-fk-stessa-coppia-v1`,
   `dbops/test-storico-nome-funzione-ritirato-v1`, `dbops/test-storico-salto-trigger-presente-v1`,
   `dbops/test-cleanup-framework`, `dbops/test-lock-columns-convergenza`,
   `dbops/test-trigger-attivo-riconoscimento-per-funzione-v1`, `dbops/test-trigger-attivo-orfani-v1`,
   `dbops/test-catalogo-presidi-v1`, `magazzino/test-movimenti-attesi-forma-v1`, e dopo il giro delle automazioni la
   corsa completa (i trigger ATTIVO nuovi scattano su tabelle di dominio).
3. Le scelte di §26.6.

### 26.9 Doc (2026-11-08)

Riscritte (scritte da un agente su brief della sessione DB, rilette dalla sessione): `dbops/manual/automation_rules_tbl.md`,
`automation_overrides_cols.md`, `fn_get_override_col.md`, `fn_name_from_template.md`, `fn_resolve_scope.md` (con una sezione
«Note di migrazione» nuova), `fn_run_automations_attivo.md`, `_audit_update.md`, `_codice_maiuscolo.md`, `_date_validita.md`,
`_lock_columns.md`, `_storico.md`, `_tx_id.md`, `fn_lock_columns_divergenze.md`, `fn_trigger_exists_by_function.md`,
`_by_name.md`, `_block_by_args.md`, `_require_by_args.md`; `maintenance/manual/proc_automations_storico_job.md`;
`guide/automazione-db.md` (§1.2, §3.2, §4.2, §5.1, §5.3, §5.4 e gli esempi del CSV), `guide/storicizzazione-tabelle.md`,
`guide/tx_id_implementation_guide.md` (anche gli esempi di `rule_type` ed `exec_mode`, che il vocabolario chiuso rendeva
falsi). Nuova: `dbops/manual/fn_regola_automazione_valida.md`. Fuori perimetro, corretta perché falsa:
`anagrafiche/manual/catasto_unita_immobiliari.md` nominava il trigger di storico con la forma del ripiego ritirato
(`trg_z90_…`); il vivo è `trg_catasto_unita_immobiliari_z90_storico_upd_dlt` (catalogo dello scratch). Le schede
auto-generate e gli indici (`dbops/index.md`, `index.ci.md`) si rigenerano dopo l'apply.

### 26.10 Dopo l'apply: il pgTAP delle due FK è lento (Tid, 2026-11-08)

`dbops/test-attivo-due-fk-stessa-coppia-v1` impiegava 7,2 s sullo scratch. Il runner ATTIVO, anche limitato a uno
schema di prova, paga in testa a ogni giro `fn_ritira_attivo_eccezioni` (0,65 s) e `fn_ritira_attivo_orfani` (1,7 s)
**su tutto il database**, e il test lo chiama tre volte. Le due pulizie c'erano già prima del giro; la causa è comune:
`dbops.fn_trigger_attivo_argomenti`, SQL `IMMUTABLE`, si espandeva dentro chi la chiama e la rinumerazione dell'array
(`ARRAY(SELECT … unnest …)`) si ripeteva per ogni colonna letta, circa 2 ms a trigger su ~900. La pagano anche i
controlli per argomenti del runner e le tre funzioni trigger ATTIVO a ogni INSERT/UPDATE di una figlia.

Cura, `20_code/dbops/20261109-76`: la stessa grammatica in PL/pgSQL (`IMMUTABLE PARALLEL SAFE`, firma, colonne e COMMENT
invariati), l'array si calcola una volta per chiamata. Prova sullo scratch, in transazione: **risposte uguali** sui 890
casi (tutti i trigger ATTIVO vivi e i casi limite: base 0, argomento vuoto, numero sbagliato, funzione sconosciuta,
array vuoto e NULL); `fn_trigger_attivo_orfani` 1,77 s → 0,15 s, `fn_ritira_attivo_eccezioni` 0,65 → 0,08 s, il runner
ATTIVO su tutto il database 5,3 → 0,79 s; il pgTAP 7,2 → 0,7 s. Andata e ritorno passano. I pgTAP che nominano le
funzioni trigger ATTIVO o la grammatica verdi, tranne i due già rossi da owner (§26.7). Doc:
`dbops/manual/fn_trigger_attivo_argomenti.md` (il perché di PL/pgSQL, nota di migrazione).

**Per Tid:** apply di `-76`, poi come app `dbops/test-attivo-due-fk-stessa-coppia-v1`,
`dbops/test-guard-attivo-grammatica-e-codici-v1`, `dbops/test-trigger-attivo-orfani-v1`.

### 26.11 Chiusura dei blocchi 10b-1 e 10b-2 (2026-11-08)

Tid ha applicato `20261109-66` … `-76` su dbdev e scratch e ha lanciato i pgTAP di §26.8 e §26.10: verdi. Letto sui due
`databasechangelog` (sessione DB, sola lettura): gli undici changeSet ci sono. **I blocchi 10b-1 e 10b-2 sono chiusi**, da
committare. Restano del giro 10b: il blocco **10b-3** (D16 con N3, la scadenza: risolutore unico per trigger alla nascita e
runner) e il blocco **10b-4** (il lock di `dbops.domini_task` montato da un changeSet, il test 23 di
`test-lock-columns-convergenza` riscritto, l'eccezione nella guida). Dei progressivi concordati restano `-77` … `-79`:
per i due blocchi se ne concordano altri con l'altra sessione DB prima di scrivere.

## 27. Giro 10b, blocchi 10b-3 e 10b-4 — la scadenza e il lock fuori ambito (2026-11-08)

### 27.1 Il via (Tid, 2026-11-08)

«puoi ripartire. ora l'altro cantiere non ha bisogno di changeset»: via ai blocchi 10b-3 (D16 con N3) e 10b-4 (N5 del
10a). Numeri dal primo libero dopo il massimo sull'albero e sui due `databasechangelog` (letti subito prima di scrivere,
2026-11-08: il massimo era `20261109-83`, dell'altro cantiere): `20261109-84` … `-94`. `-77` … `-79` restano liberi.

### 27.2 Due nodi trovati scrivendo (decisioni di Tid, 2026-11-08)

* **N7 — la colonna della scadenza.** N3 diceva «il trigger scrive la colonna dichiarata» (`cleanup_column`). Scrivendo:
  tre lettori la ignorano e usano `cleanup_at` per nome (il trigger alla nascita, `script.fn_registra_tentativo_login`,
  `dbops.vw_marcatori_automazione_senza_esecutore`; anche `vendite.trgfn_logs_guard_delete` e
  `vendite.trgfn_event_log_append_only` leggono `OLD.cleanup_at`), e CLEANUP_AT e CLEANUP_PURGE hanno ognuna la sua
  `cleanup_column`: possono dire due colonne diverse, e il purge non troverebbe le scadenze. **Deciso: nome fisso
  `cleanup_at`**, come le colonne di audit (N5 del 10b): la chiave esce dai params, e il validatore chiude l'elenco delle
  chiavi del cleanup. Rivede la parte di N3 sulla colonna.
  **L'analisi chiesta da Tid** (2026-11-08, «non vorrei che l'altra colonna sia stata aggiunta per qualche motivo»):
  la chiave nasce il 2026-02-07 (`7550d18ede`, «aggiunto su framework attività di pulizia per tabelle che hanno la
  colonna cleanup_at») insieme a tutto il framework, come parametro generico con default `cleanup_at`; in tutta la
  storia del repo (`git log -S`) non ha mai avuto un valore diverso da `cleanup_at`, e nessun documento le dà un
  motivo. Sulla struttura dello scratch (2026-11-08) nessuna tabella ha una colonna di scadenza con un altro nome
  pensata per il framework: `config.token_monouso.scadenza` è la validità del token, con la sua pulizia
  (`fn_cleanup_token_scaduti`), e le tabelle di Django sono dell'applicazione. Nessun motivo trovato.
* **N8 — la base vuota.** Con la base NULL sulla riga il trigger partiva da `now()`, il runner saltava la riga.
  **Deciso: base vuota = nessuna scadenza** (la regola del runner, «in dubbio non si cancella»): la scadenza la scrive il
  job quando la base c'è. Vale anche per la tabella senza nessuna colonna base (prima il trigger usava `now()`).

### 27.3 Che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261109-84` | `dbops.fn_cleanup_esclusa(schema, tabella)`: la domanda dell'esclusione in una sede (regola del 2: la facevano da sé runner e vista, il risolutore era la terza copia) |
| `20_code/dbops/20261109-85` | `dbops.fn_cleanup_at_regola(schema, tabella)` (N3): la CLEANUP_AT più specifica; nessuna riga = non scade; `motivo_salto` EXCLUDED, NO_CLEANUP_COLUMN, MISSING_BASE_TS_COLUMN; base dichiarata o dalla catena |
| `20_code/dbops/20261109-86` | `trgfn_cleanup_at_alla_nascita` dal risolutore: esclusa, senza regola o senza base → NULL (N8) |
| `20_code/script/20261109-87` | `fn_registra_tentativo_login`: il ttl dal risolutore; COMMENT senza sigle di brief (§5d) |
| `20_code/dbops/20261109-88` | `fn_apply_cleanup_at` e `fn_purge_cleanup_expired`: colonna fissa; `p_cleanup_column` resta in firma e può solo confermare `cleanup_at` (E_PARAMETRO_INVALIDO); la base di `fn_apply_cleanup_at` è obbligatoria (ripiegava su `data_insert`, una terza regola) |
| `20_code/dbops/20261109-89` | `fn_run_automations_cleanup`: CLEANUP_AT dal risolutore, una regola per tabella; esclusione dal BB; via MISSING_TTL_DAYS (impossibile col CHECK, D2) |
| `20_code/dbops/20261109-90` | `vw_marcatori_automazione_senza_esecutore`: l'esclusione dal BB |
| `20_code/dbops/20261109-91` | DROP di `dbops.fn_cleanup_at_params` |
| `20_code/dbops/20261109-92` | `fn_regola_automazione_valida`: chiavi chiuse (CLEANUP_AT: `ttl_days`, `apply_on_update`, `base_ts_column`; CLEANUP_PURGE: `batch_limit`) (N7) |
| `90_end/20261109-93` | il CHECK `chk_automation_rules_tbl_regola_valida` si ricrea: le righe si ricontrollano col validatore nuovo |
| `20_code/dbops/20261109-94` | **10b-4**: `trg_domini_task_a10_lock_columns_upd` montato dal changeSet (nome dal template, argomenti del runner), col COMMENT che dice perché |
| `80_data` | `automation_rules_tbl.csv`: via `cleanup_column` dai params delle sedici regole CLEANUP_* (fine riga conservati); il mirror `20250918-02` (runOnChange) ricarica |

pgTAP nuovo: `dbops/test-cleanup-at-regola-unica-v1` (14: due regole sulla stessa tabella, una tabella con solo
`executed_at`, una esclusa, una senza base, una riga con base NULL; trigger e runner danno la stessa data; le tre tabelle
del login). Riscritti: `dbops/test-cleanup-framework` (13-16: il veto passa sull'UPDATE, vedi §27.4 punto 5; via
`cleanup_column` dalle regole di prova), `dbops/test-registro-regole-vincoli-v1` (19: l'11 senza `cleanup_column`, 18-19
nuovi), `dbops/test-lock-columns-convergenza` (30: il 23 con la regola nuova, il 30 nuovo); `dbops/test-registri-dbops-scadenza-v1`,
`dbops/test-idempotency-prenota-v1`, `vendite/test-registri-fatturazione-scadenza-alla-nascita`,
`vendite/test-event-log-append-only`, `vendite/test-event-log-deriva-scope`, `config/test-credenziale-login-v1`,
`config/test-credenziale-login-tempo-v1`: leggono il risolutore invece della funzione ritirata.

### 27.4 Le scelte dentro i blocchi (✅ decise da Tid, 2026-11-08: vedi §28.11)

1. **Una regola CLEANUP_AT per tabella anche nel runner.** Prima il runner applicava in ordine tutte quelle che coprivano
   la tabella, la `*all` compresa; il trigger ne prendeva una. Fatto datato (dry run prima/dopo, scratch e dbdev,
   2026-11-08): 42 applicazioni → 28, le 14 in meno sono la `*all` ripetuta sulle tabelle con una regola loro; le righe che
   ricevono una scadenza sono le stesse.
2. **Il trigger scrive NULL anche sopra un valore del chiamante** quando non c'è regola che si applichi (prima, senza
   regola, lo lasciava): «un diario non lascia scegliere quando scade» vale in tutti i rami.
3. **`p_cleanup_column` resta in firma** (i parametri non si tolgono) con un ruolo di controllo; il ritiro vero, se
   serve, lo decide Tid.
4. **Il login scrive `now() + ttl`**, non «base + ttl»: è la stessa cosa perché scrive `ultimo_fallimento_at = now()` nella
   stessa istruzione. Lo tiene fermo il test 11 del pgTAP nuovo (la base delle tre tabelle è `ultimo_fallimento_at`): se
   la regola cambiasse base, il test diventa rosso invece di lasciar passare una scadenza sbagliata.
5. **Il runner fa su ogni tabella prima la scadenza, poi il purge** (prima seguiva le priorità delle regole, che col seed
   davano lo stesso ordine). Per questo in `test-cleanup-framework` il veto di prova è sull'UPDATE: la scadenza rifiuta, e
   il purge che viene dopo prova che il giro prosegue.
6. **10b-4: il presidio è diviso in due test** (23: ogni colonna di un lock fuori ambito ha la sua riga attiva con lo
   stesso codice; 30: ogni riga attiva fuori ambito ha il suo lock vivo, abilitato, con la colonna nell'UPDATE OF). Il 30
   è rosso senza il `-94` (trova `dbops.domini_task codice`) e verde con.

### 27.5 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase: `-84` … `-92`, `-94`, poi il mirror del CSV rifatto su tutte le righe, poi `-93`; `BEGIN … ROLLBACK`)

* Andata e ritorno (i rollback all'indietro) passano su scratch e dbdev. Le preCondition passano.
* Il lock: un UPDATE del codice di un dominio è rifiutato con `E_CODICE_NON_MODIFICABILE`, uno della descrizione passa.
* pgTAP con l'SQL dei blocchi dopo la riga `BEGIN;`: verdi sullo scratch i dodici di §27.6; su dbdev i sette principali.
  Tutta la cartella `dbops/` sullo scratch: sei rossi, uguali senza i blocchi (si lanciano come app;
  `test-guard-attivo-occhi-del-proprietario-v1` era già in §26.7).
* Guardrail verdi (`ddl_su_trigger_automazione`, `precondition_seed`, `run_on_change`, `sql_letterali`,
  `grant_ruolo_batch`, `timestamp_senza_fuso`, `v1_congelato`, `pgtap_preambolo`). Il driver di Liquibase non è stato
  provato a parte: nessun corpo è `BEGIN ATOMIC`.

### 27.6 Per Tid

1. **Apply** di `20261109-84` … `-94` e del CSV del registro, su dbdev e scratch (il mirror `20250918-02` riparte da sé:
   è runOnChange). Nessun giro delle automazioni necessario.
2. **pgTAP come app:** `dbops/test-cleanup-at-regola-unica-v1`, `dbops/test-cleanup-framework`,
   `dbops/test-registro-regole-vincoli-v1`, `dbops/test-lock-columns-convergenza`, `dbops/test-registri-dbops-scadenza-v1`,
   `dbops/test-idempotency-prenota-v1`, `dbops/test-marcatori-automazione-senza-esecutore-v1`,
   `vendite/test-registri-fatturazione-scadenza-alla-nascita`, `vendite/test-event-log-append-only`,
   `vendite/test-event-log-deriva-scope`, `config/test-credenziale-login-v1`, `config/test-credenziale-login-tempo-v1`.
3. Le scelte di §27.4 (e quelle di §26.6, ancora da guardare).

Ricadute BE: nessuna. `backend/` non nomina `fn_cleanup_at_params`, `cleanup_column` né `CLEANUP_AT` (grep, 2026-11-08).

### 27.7 Doc (2026-11-08)

Scritte da un agente su brief della sessione DB, rilette dalla sessione. Nuove: `dbops/manual/fn_cleanup_at_regola.md`
(con la nota di migrazione: riassorbe `fn_cleanup_at_params`), `dbops/manual/fn_cleanup_esclusa.md`. Cancellata:
`dbops/manual/fn_cleanup_at_params.md` (oggetto ritirato). Riscritte: `dbops/manual/trgfn_cleanup_at_alla_nascita.md`,
`fn_run_automations_cleanup.md`, `fn_apply_cleanup_at.md`, `fn_purge_cleanup_expired.md`,
`automation_cleanup_exclusions.md` (l'esclusione ora ferma anche la scadenza alla nascita), `automation_rules_tbl.md`,
`fn_regola_automazione_valida.md`, `vw_marcatori_automazione_senza_esecutore.md`, `domini_task.md` (il lock del codice),
`automation_lock_columns.md`, `fn_lock_columns_divergenze.md`, `vw_lock_columns_vivi.md` (fuori ambito: lock e registro
coincidono); `script/manual/fn_registra_tentativo_login.md`; `maintenance/manual/proc_automations_cleanup_job.md` (fuori
elenco, falsa: regole «a strati»); `guide/automazione-db.md` (§1.2, §1.3, §4.1 l'eccezione del lock fuori ambito, §4.5,
§5.1, §8), `guide/audit-e-tracciabilita.md`, `linee-guida-trigger.md` (§«I trigger generati»: l'eccezione, col rimando).
Le schede auto-generate e gli indici si rigenerano dopo l'apply: fino ad allora i link a `fn_cleanup_at_regola` e
`fn_cleanup_esclusa` puntano a pagine che non ci sono ancora.

### 27.8 Residuo

* **`ILIKE r.target_table`**: nel risolutore e nel ciclo del purge il nome della tabella della regola è un pattern di
  LIKE, e `_` è un jolly (`event_log` copre anche una `eventXlog`). Preesistente, uguale nei due; non toccato perché
  cambia il significato di ogni regola del registro. Va annotato con D17-bis in `framework-automazione-db-migliorie` §2.4.

### 27.9 Chiusura dei blocchi 10b-3 e 10b-4 (2026-11-08)

Tid ha applicato `20261109-84` … `-94` e il CSV del registro su dbdev e scratch e ha lanciato i pgTAP di §27.6: verdi.
Letto sui due database (sessione DB, sola lettura, 2026-11-08): gli undici changeSet sono nel `databasechangelog`,
`dbops.fn_cleanup_at_params` non c'è più, nessuna regola porta `cleanup_column`, `trg_domini_task_a10_lock_columns_upd` è
montato. Le scelte di §26.6 sono ok (Tid: il via era su tutto). **Il giro 10b è chiuso**, da committare; restano da
guardare le scelte di §27.4. Le schede auto-generate e gli indici di `dbops` e `script` si rigenerano col prossimo giro
della doc. **Committato** (`148ec4eb20`, 2026-11-08, non pushato).

## 28. Giro 10c — DELETE_BLOCK, guard utility, overlap: preparazione (2026-11-08)

Difetti del giro (§8): D19, D33, D34, D30, D59, Q14 ⑪, ⑫, ⑬, R3; la regola della Q3 (§2.3) per DELETE_BLOCK e guard
utility. Via di Tid alla preparazione: «poi riparti», «punto successivo» (2026-11-08). Corpi letti dal catalogo dello
scratch (2026-11-08, dopo l'apply del 10b).

### 28.1 La riverifica

| # | Esito | Sul corpo di oggi |
| --- | --- | --- |
| D19 | ✅ confermato, ⚠️ precisato | Il nome di default `trg_%s_a10_delete_block_dlt` è composto con `format` in due posti (runner e `fn_apply_delete_block_trigger`), senza `fn_name_from_template`: una tabella lunga fa troncare il nome, il controllo per nome non lo trova e il giro dopo prende 42710. Il `NULLIF` nel runner oggi c'è; il runner passa all'apply il `trigger_name` grezzo |
| D33 | ✅ confermato | Il runner legge solo `enabled`, riconosce il trigger dal nome, non toglie niente: riga spenta o cancellata, `guc_key` o `trigger_name` cambiati non arrivano al trigger |
| ⑪ | ✅ confermato | `fn_apply_delete_block_trigger` crea `AFTER DELETE`; tutti i trigger vivi della funzione sono `AFTER` (fatto datato: otto, tutti righe del registro) |
| D34 | ✅ confermato | `fn_apply_automazione_guard_utility_tipo_ruolo` legge solo `enabled`, `DROP TRIGGER IF EXISTS` sul nome di oggi; nessun audit, il dry run non dice niente |
| D30 | ✅ confermato, ⚠️ precisato | L'apply filtra `LIKE '%_soggetto_ruolo_id'` e scarta la forma senza prefisso; colonne inesistenti saltate senza traccia. `script.trgfn_guard_utility_tipo_ruolo_by_cols` è generico (due argomenti, qualunque nome): il filtro non viene dal guard. Il seed non scrive più dal 2026-08-18 (è una diagnosi con un NOTICE), ma ha lo stesso filtro |
| ⑬ | ✅ confermato, ⚠️ precisato | Il guard utility non è in `dbops.processi`: lo chiama solo `ci_apply/20250627-31` (seed + apply), che non è `runAlways` e non si riscrive (§28.2 N5). Gli altri runner girano due volte da zero: da quel file e dalla catena dei processi (`ci_apply/20260926-10`, runAlways) |
| D59 | ✅ confermato | In `fn_apply_automazione_overlap` una colonna di chiave assente si salta in silenzio e il vincolo nasce con una chiave più corta |
| ⑫ | ✅ confermato, ⚠️ precisato | Nessuna gestione del `23P01`: dati sovrapposti fermano il giro intero. La regola si dà per applicata con **qualunque** `EXCLUDE` della tabella che nomina la colonna del periodo (`v_any_exclusion`), e il nome del vincolo devia su `_c` se esiste una relazione omonima |
| R3 | ✅ confermato | `ci_apply/20260205-41` (runOnChange, «il corpo si modifica in questo file») elenca ancora `dbops.fn_audit_begin` e `fn_audit_end`, che non esistono; anche `scripts/sql/provision_zeroerp.sql` |
| **nuovo** | ⚠️ trovato | `dbops.automazione_overlap` **non ha un CSV**: le sue righe le scrivono `INSERT`/`UPDATE` di `80_data` (`20260602-10`, `-22`, `20260626-04`, `20260928-42`, `20261028-30`), contro linee-guida-sql §11.2 e la regola «una tabella, un CSV» degli altri registri `automazione_*` |

### 28.2 I nodi (decisioni di Tid)

* **N1 — la Q3 su DELETE_BLOCK e guard utility.** Come per i lock (giro 10a): il trigger si riconosce dalla funzione e
  dagli argomenti; il runner porta il vivo all'atteso — riga spenta o cancellata → **TOGLIE**; argomenti, nome o momento
  diversi → **RIGENERA**; un trigger della funzione che nessuna riga dichiara → il runner **si ferma** e lo nomina, non lo
  cancella (stessa regola del lock scritto a mano). Una funzione delle divergenze per registro, letta dal runner e da un
  pgTAP su tutto il database (presidio). **Proposta:** sì, nella forma dei lock.
* **N2 — ⑪, il momento.** Il generatore crea `BEFORE DELETE … FOR EACH ROW`; un `AFTER` vivo è difforme e si rigenera
  (N1). Il nome resta `a10` (zona dei guard, ora vera). **Proposta:** sì.
* **N3 — D19, il nome di default.** In una sede sola, con `fn_name_from_template('trg_{table}_a10_delete_block_dlt')`;
  il nome serve solo a creare, il riconoscimento è dalla funzione (N1). Stessa forma per il guard utility, che già la usa.
* **N4 — D30, il filtro.** **Proposta:** il filtro esce (il guard è generico, il registro decide quale colonna); una
  colonna assente → audit `WARN` `COLUMN_MISSING`; il dry run scrive `DRYRUN`, il giro vero `OK`. Lo stesso nel seed. Le
  righe di oggi senza prefisso sono spente (fatto datato), quindi niente nasce senza una decisione.
* **N5 — ⑬, il processo.** Nasce `automations_guard_utility` in `dbops.processi` (`ci_ordine` 75, fra delete_block e
  overlap), con il runner `dbops.fn_run_automations_guard_utility`, la procedura `maintenance.proc_automations_guard_utility_job`
  e il job pgAgent come gli altri. `ci_apply/20250627-31` **non si tocca** (già eseguito, non runOnChange): continua a
  chiamare seed e apply sul database da zero, una volta, come fa con tutti gli altri runner che poi la catena dei processi
  rilancia; con la convergenza (N1) il secondo giro non cambia niente. Alternativa: riscriverlo (ha `validCheckSum: ANY`),
  che è un'eccezione alla regola dei changelog già mergiati e la decide Tid. **Proposta:** non toccarlo, dichiarato.
* **N6 — D59 e ⑫, l'overlap.** Ogni colonna di chiave deve esistere, altrimenti `WARN` `KEY_COLUMN_MISSING` e niente
  vincolo; ogni `ADD CONSTRAINT` in un blocco `EXCEPTION WHEN exclusion_violation`: `WARN` `DATI_SOVRAPPOSTI` con le
  coppie di id, e la regola dopo; la regola è applicata solo col **suo** vincolo (per nome), non con un qualsiasi
  `EXCLUDE`; presidio: regola attiva senza il suo vincolo. Su una regola spenta il vincolo **non** si toglie da solo
  (togliere un vincolo d'integrità è una decisione, non una convergenza): il presidio lo mostra. **Proposta:** sì.
* **N7 — il CSV dell'overlap** (nuovo). **Proposta:** `automazione_overlap.csv` con il mirror `runOnChange`, come gli
  altri registri; le righe dal catalogo di oggi, confrontate con i changeSet che le hanno scritte. I changeSet vecchi
  restano (non si riscrivono); quelli che fanno `UPDATE` su colonne che il CSV riscrive diventano innocui.
* **R3:** via i due nomi da `ci_apply/20260205-41` e da `provision_zeroerp.sql`; il pgTAP della postura li cerca già come
  assenti (test 14-15).

### 28.3 I blocchi

* **10c-1 — DELETE_BLOCK:** D19, D33, ⑪ (N1-N3): divergenze, runner che converge, apply `BEFORE`, presidio.
* **10c-2 — guard utility:** D30, D34, ⑬, R3 (N1, N4, N5): divergenze, runner nuovo, processo, procedura, job.
* **10c-3 — overlap:** D59, ⑫ (N6), il CSV (N7).

Ogni blocco si prova prima del successivo. **Numeri:** dal primo libero, `20261109-95` in poi (letti di nuovo subito
prima di scrivere).

Ricadute BE: da verificare al via — il processo nuovo compare nel panorama dei processi (§10 della guida delle
automazioni), che il BE legge dal catalogo; nessun codice nuovo previsto oltre ai motivi d'audit.

### 28.4 Il via (Tid, 2026-11-08)

«Il via sui sette punti: come da proposta. Procedi.» N1-N7 come da proposta. Numeri dal primo libero: `20261109-95` …
`-99`, poi `20261110-01` … `-06` (oltre il `-99` si passa al giorno dopo).

### 28.5 Che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261109-95` | `dbops.fn_nome_oggetto_dichiarato(nome, template, schema, tabella)`: il nome di un oggetto che un registro dichiara riga per riga, in una sede (D19, N3), per DELETE_BLOCK, guard utility e overlap; idempotente (§28.6 punto 1) |
| `20_code/dbops/20261109-96` | `dbops.fn_delete_block_divergenze(p_schemas)`: CREA, RIGENERA, TOGLIE, SCONOSCIUTO, sul modello dei lock (N1, N2) |
| `20_code/dbops/20261109-97` | `fn_apply_delete_block_trigger`: **BEFORE DELETE** (⑪), nome dal BB, un omonimo si ricrea |
| `20_code/dbops/20261109-98` | `fn_run_automations_delete_block`: converge (D33 con la Q3); si ferma con `E_DELETE_BLOCK` su un blocco che il registro non nomina; azioni d'audit CREA/RIGENERA/TOGLIE |
| `20_code/dbops/20261109-99` | `dbops.fn_guard_utility_divergenze(p_exec_mode, p_schemas)`: CREA, RIGENERA, TOGLIE, COLONNA_MANCANTE, SCONOSCIUTO; nessun filtro sul nome della colonna (D30, D34, N4) |
| `20_code/dbops/20261110-01` | `dbops.fn_run_automations_guard_utility`: il runner nuovo (⑬, N5), audit OK/DRYRUN e WARN COLUMN_MISSING, si ferma con `E_GUARD_UTILITY` |
| `20_code/dbops/20261110-02` | `fn_apply_automazione_guard_utility_tipo_ruolo`: la porta storica chiama il runner (la chiama ancora `ci_apply/20250627-31`) |
| `20_code/dbops/20261110-03` | `fn_seed_automazione_guard_utility_tipo_ruolo`: la diagnosi senza filtro sul nome (D30); COMMENT senza storia |
| `20_code/maintenance/20261110-04` | `maintenance.proc_automations_guard_utility_job()`: DEFINER, search_path fissato, niente EXECUTE a PUBLIC |
| `85_pgagent/20261110-05` | il job pgAgent `automations_guard_utility`, ogni notte alle 21:10; il passo nasce già avvolto nel cancello `maintenance.fn_sveglia_accesa` (correzione del 2026-11-08: la prima forma era nuda, l'hanno preso i test 20-21 di `dbops/test-installazione-ambiente-v1` su dbdev) |
| `20_code/dbops/20261110-06` | `fn_apply_automazione_overlap` (D59, ⑫, N6): KEY_COLUMN_MISSING, DATI_SOVRAPPOSTI (23P01, col dettaglio e lo SQLSTATE), NOME_OCCUPATO; il suo vincolo per nome; via `v_any_exclusion` e la variante `_c` |
| `80_data` | `processi.csv`: riga 49 `automations_guard_utility` (ci_ordine 75); `codici_errore.csv` e `messaggi_errore.csv`: `E_GUARD_UTILITY` (TECNICO, id 1460) |
| `90_end/ci_apply/20260205-41` (runOnChange) e `scripts/sql/provision_zeroerp.sql` | R3: via `fn_audit_begin`/`fn_audit_end` dalle porte riservate, e i commenti che le nominavano |

pgTAP nuovi: `dbops/test-delete-block-convergenza-v1` (16), `dbops/test-guard-utility-convergenza-v1` (14),
`dbops/test-overlap-regola-e-vincolo-v1` (9). Riscritto: `dbops/test-delete-block-audit-v1` (i nomi delle azioni).

### 28.6 Le scelte dentro il giro (✅ decise da Tid, 2026-11-08: vedi §28.11)

1. **Il BB del nome è idempotente, e `fn_name_from_template` no.** Trovato col test del nome lungo (D19):
   `fn_name_from_template` accorcia con `left(…, 56) || '_' || hash`, e se il taglio cade su un `_` lascia un doppio
   trattino basso; ripassato al template, il doppio si ripulisce e il nome cambia. Il BB prende com'è un nome che sta nei
   63 caratteri, quindi chi confronta e chi crea dicono lo stesso nome. `fn_name_from_template` non l'ho toccato (cambiare
   la sua uscita cambierebbe i nomi di oggetti vivi): è nel residuo (§28.9).
2. **Per togliere un blocco o un guard si spegne la riga, non la si cancella.** Un trigger della funzione senza nessuna
   riga del registro è SCONOSCIUTO e ferma il giro (N1): una riga cancellata e un trigger scritto a mano non si
   distinguono. È la regola dei lock («enabled = false se il blocco va tolto»).
3. **Le righe di un altro `exec_mode`** del guard utility lasciano la tabella fuori dal confronto (come i lock).
4. **Il dettaglio dei dati sovrapposti è la prima coppia**, quella che PostgreSQL mette nel `DETAIL` del 23P01 (le
   chiavi in conflitto), non l'elenco di tutte le coppie: calcolarle tutte vorrebbe dire riscrivere chiavi ed espressioni
   del registro in un self-join. Chi guarda l'audit trova la tabella, il vincolo e la prima coppia.
5. **Il UNIQUE … WITHOUT OVERLAPS sul periodo resta una forma valida** della regola overlap (è la forma temporale nativa);
   un EXCLUDE estraneo no.
6. **La porta storica del guard utility resta e chiama il runner** (N5: `ci_apply/20250627-31` non si riscrive); il
   seed resta, come diagnosi.
7. **Un codice nuovo, `E_GUARD_UTILITY`**, come `E_LOCK_COLUMNS` ed `E_DELETE_BLOCK` per i runner sorelle.

### 28.7 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase, le righe nuove dei tre CSV, `BEGIN … ROLLBACK`)

* Andata e ritorno passano su scratch e dbdev; le preCondition passano. Il blocco 10c-1 è stato provato anche da solo
  prima del 10c-2.
* Subito dopo l'SQL, prima dei runner, gli otto blocchi di DELETE di oggi sono RIGENERA (sono AFTER): li rigenera il
  primo giro delle automazioni. Il guard utility non ha divergenze.
* `CALL maintenance.proc_automations_guard_utility_job()`: una riga ok in `maintenance.job_run_log` sotto il codice del
  processo.
* pgTAP, con l'SQL e i due runner (delete_block e guard utility) dopo la riga `BEGIN;`: verdi i quattro del giro su
  scratch e dbdev. Tutta `dbops/` e i pgTAP che nominano overlap, guard utility, DELETE_BLOCK o le porte dell'audit,
  sullo scratch: otto rossi, sette uguali senza il giro (si lanciano come app; già in §26.7 e §27.5); il rosso nuovo è il
  test 7 di `dbops/test-processi-convergenza-ci` (il processo nuovo non ha ancora girato su questo database), atteso
  fino al primo giro.
* Guardrail verdi.

### 28.8 Per Tid

1. **Apply** di `20261109-95` … `-99` e `20261110-01` … `-06`, dei tre CSV (`processi.csv`, `codici_errore.csv`,
   `messaggi_errore.csv`), di `ci_apply/20260205-41` (runOnChange) e del job pgAgent, su dbdev e scratch.
2. **`make db-ci-apply`** (o il giro delle automazioni): rigenera BEFORE gli otto blocchi di DELETE e fa girare il
   processo nuovo, che serve al test 7 di `test-processi-convergenza-ci`.
3. **Provisioning, fase post, su dbdev** (`scripts/sql/provision_zeroerp.sql`): dà a `zeroerp_job` l'EXECUTE sulla
   procedura nuova; senza, il job notturno pgAgent fallisce per permesso. Sullo scratch lo fa `ci-local.sh`.
4. **pgTAP come app:** `dbops/test-delete-block-convergenza-v1`, `dbops/test-delete-block-audit-v1`,
   `dbops/test-guard-utility-convergenza-v1`, `dbops/test-overlap-regola-e-vincolo-v1`,
   `dbops/test-processi-convergenza-ci`, `dbops/test-registri-append-only-postura-v1`, `dbops/test-processo-vivo-v1`,
   `dbops/test-processi-accensione-v1`, `dbops/test-marcatori-automazione-senza-esecutore-v1`,
   `anagrafiche/create-cliente`, `anagrafiche/test-simula-subentro`.
5. Le scelte di §28.6, e il nodo N7-bis qui sotto.

**Ricadute BE:** il codice nuovo `E_GUARD_UTILITY` va nella rigenerazione delle politiche d'errore
(`backend/apps/core/services/error_policies_generated.py`, come BE6); il processo nuovo compare nel panorama dei
processi, che il BE legge dal catalogo (nessun codice da scrivere).

### 28.8-bis Doc (2026-11-08)

Scritte da un agente su brief della sessione DB, rilette dalla sessione. Nuove: `dbops/manual/fn_nome_oggetto_dichiarato.md`,
`fn_delete_block_divergenze.md`, `fn_guard_utility_divergenze.md`, `fn_run_automations_guard_utility.md`,
`maintenance/manual/proc_automations_guard_utility_job.md`. Riscritte: le pagine `manual/` di DELETE_BLOCK (registro,
apply, runner, job, `script.trgfn_delete_block_by_guc`), del guard utility (registro, apply, seed), dell'overlap
(registro, apply, job), `fn_name_from_template.md` (non idempotente), `fn_trigger_exists_by_name.md` (il runner
DELETE_BLOCK non la usa più); `guide/automazione-db.md` (§1.4, §4.3, §4.4, §4.6, §5.4, §8, §9.1, §9.3) e
`tutorial/framework-automazione-db.md` (la catena e le 21:10). I link alle cinque funzioni nuove si attivano con la
rigenerazione della doc auto-generata, dopo l'apply.

### 28.9 Il nodo N7-bis: il CSV dell'overlap non si può fare così com'è (da decidere, Tid)

N7 (il CSV di `dbops.automazione_overlap`) è deciso, ma scrivendo si ferma su un fatto tecnico: `key_columns` e
`key_expressions` sono `text[]`, e Liquibase non sa caricare un array da un CSV (il driver lo lega come stringa e
PostgreSQL lo rifiuta; è la ragione per cui questa è l'unica tabella di configurazione senza CSV). Strade:
(a) le due colonne diventano `jsonb` (array JSON): il CSV le carica come `params` delle regole, l'unico lettore è
`fn_apply_automazione_overlap`, e un CHECK ne fissa la forma (array di stringhe); (b) una colonna sola, un testo con le
colonne separate da virgola: è un array travestito da testo, e non regge le espressioni (che contengono virgole);
(c) il CSV con una colonna `COMPUTED` (SQL in una cella): fragile. **Proposta: (a)**, in un blocco 10c-4, con il CSV
ricostruito dalle sette righe di oggi confrontate con i cinque changeSet che le hanno scritte. Non è nel codice del giro.

**Residuo:** `dbops.fn_name_from_template` non è idempotente (§28.6 punto 1): va guardato con D17-bis in
`framework-automazione-db-migliorie` §2.4, perché cambiarne l'uscita cambia i nomi di oggetti vivi.

### 28.10 Dopo l'apply (2026-11-08)

Tid ha applicato il giro 10c su dbdev e scratch e ha lanciato i pgTAP: verdi. Letto sui due database (sessione DB, sola
lettura, 2026-11-08): gli undici changeSet sono nel `databasechangelog`; il processo `automations_guard_utility` e il
codice `E_GUARD_UTILITY` ci sono; nessuna divergenza né per DELETE_BLOCK né per il guard utility; gli otto blocchi di
DELETE sono `BEFORE` (tgtype 11); il processo nuovo ha righe riuscite in `maintenance.job_run_log`. ⚠️ Su dbdev
`zeroerp_job` non ha l'EXECUTE su `maintenance.proc_automations_guard_utility_job()` (sullo scratch sì): manca la fase post
del provisioning, e fino ad allora il job notturno pgAgent fallisce per permesso. **Il giro 10c è chiuso** salvo il nodo
N7-bis (il CSV dell'overlap, §28.9), da committare.

### 28.11 Le decisioni di Tid sulle scelte e sul nodo N7-bis (2026-11-08)

* **Il permesso su dbdev:** non con un GRANT a mano (linee-guida-sql §11.6 e §11.9) ma con la fase post del
  provisioning, da superuser: `sudo -u postgres psql -d zeroerp -v fase=post < scripts/sql/provision_zeroerp.sql`
  (l'ambiente di dbdev è già scritto). Tocca a Tid.
* **N7-bis: (a).** `key_columns` e `key_expressions` di `dbops.automazione_overlap` diventano `jsonb` (array di
  stringhe, con un CHECK sulla forma), e il registro prende il suo CSV col mirror. Blocco 10c-4.
* **§27.4**, una domanda alla volta: 1 una regola di scadenza per tabella ✅; 2 il trigger alla nascita decide sempre lui
  (NULL sopra il valore del chiamante) ✅; **3 `p_cleanup_column` esce dalla firma** di `fn_apply_cleanup_at` e
  `fn_purge_cleanup_expired` (Tid: «non possiamo lasciare una firma basata su un campo non più esistente; diverso è
  quando aggiungiamo un campo alla firma» — il parametro era la manopola ritirata, non la colonna `cleanup_at`, che resta);
  4 il login scrive adesso + ttl, presidiato dal test ✅; 5 prima la scadenza, poi il purge ✅; 6 due test per il
  lucchetto fuori ambito ✅.
* **§28.6:** **1 `fn_name_from_template` si corregge ora** (non al residuo): il doppio trattino basso dell'accorciamento
  si toglie all'origine, con il censimento dei nomi vivi che cambierebbero e i runner che li rigenerano; 2 per togliere
  un blocco o un guard si spegne la riga ✅; 3 l'`exec_mode` del guard utility come i lucchetti ✅; 4 la prima coppia dei
  dati sovrapposti basta ✅; 5 il `WITHOUT OVERLAPS` sul periodo vale ✅; 6 le due porte del guard utility restano (Tid
  aveva chiesto se un changeSet nuovo potesse ritirarle: no, perché `ci_apply/20250627-31` le chiama per nome su ogni
  database da zero, e la CI si fermerebbe; riscrivere quel file sarebbe un'eccezione, scartata) ✅; 7 `E_GUARD_UTILITY` ✅.
* **Il blocco 10c-4** porta quindi tre lavori: l'overlap in `jsonb` col CSV; il ritiro di `p_cleanup_column` (DROP e
  CREATE delle due funzioni, il runner del cleanup e i pgTAP che le chiamano); `fn_name_from_template` idempotente.

### 28.12 Blocco 10c-4 — nomi idempotenti, firma del cleanup, overlap in jsonb (2026-11-08/09)

Via di Tid: «ok procedi, ora l'altro cantiere è fermo» (2026-11-08). **Numeri:** l'altro cantiere aveva preso
`20261110-07` … `-33`; i primi YAML di questo blocco, scritti con `-07` … `-13`, sono stati tolti dall'albero prima che un
migrate potesse vederli (nessuno era nei `databasechangelog`) e rinumerati dal primo libero: `20261110-34` … `-41`.

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261110-34` | `fn_name_from_template` idempotente: il taglio oltre i 63 caratteri non lascia un `_` in coda (decisione §28.11) |
| `20_code/config/20261110-35` | rinomina del trigger di audit di `config.forme_giuridiche_tipi_soggetto_dettaglio` (`…audit_data__eaaf9f` → `…audit_data_eaaf9f`), changeSet a sé con preCondition `MARK_RAN` sul nome vecchio (§11.5): il runner dell'audit riconosce dalla funzione e non rinomina |
| `20_code/dbops/20261110-36` | `fn_apply_cleanup_at` e `fn_purge_cleanup_expired` senza `p_cleanup_column` (decisione §28.11), DROP e CREATE, e il runner del cleanup con le chiamate nuove |
| `20_code/dbops/20261110-37` | `fn_apply_automazione_overlap` legge le chiavi come array JSON; nasce `dbops.fn_jsonb_array_di_testi` per il CHECK |
| `20_code/dbops/20261110-41` | `fn_drop_triggers_by_function_args`: toglie i trigger montati su una partizione (`tgparentid = 0`), lascia i cloni (§28.12 punto 3) |
| `80_data/changelog/20261110-38` | `key_columns` e `key_expressions` da `text[]` a `jsonb`, in 80_data perché su un database da zero giri dopo i changeSet vecchi che scrivono il registro con letterali `text[]` (come il `20261109-74`) |
| `80_data/changelog/20261110-39` | il mirror del CSV `automazione_overlap.csv` (runOnChange; `primaryKey` sulla coppia schema-tabella; `nullValue: NULL`) |
| `90_end/20261110-40` | CHECK `chk_automazione_overlap_chiavi` sulla forma delle chiavi |

pgTAP nuovo: `dbops/test-nomi-e-chiavi-registri-v1` (9: tipi jsonb, il CHECK, l'idempotenza, nessun trigger vivo con
`__`, le due firme, nessun doppione ATTIVO). Riscritti: `dbops/test-cleanup-framework`,
`vendite/test-registri-fatturazione-scadenza-alla-nascita` (le firme), `dbops/test-overlap-tabella-sparita-v1`,
`test-overlap-regola-e-vincolo-v1`, `test-fn-apply-automazione-overlap-key-expressions-v1`,
`test-fn-apply-automazione-overlap-where-predicate-v1` (le chiavi come jsonb).

**Le scelte dentro il blocco (da guardare, Tid):**

1. **Il censimento dei nomi** (fatto datato, scratch e dbdev, 2026-11-08): 59 trigger vivi avevano `__` nel nome, 58 della
   famiglia ATTIVO e uno di audit. I primi li rigenera il runner ATTIVO al primo giro (riconosce dagli argomenti), il
   secondo lo rinomina il `-35`. Nessun file del repo li nomina, salvo un commento in
   `catalogo/test-articoli-approvvigionamento-v1`. Gli indici e i vincoli `not_null` con `__` hanno nomi dati da PostgreSQL,
   non dal template: fuori dal perimetro.
2. **Il CSV dell'overlap ha le sette righe che nascono dai changelog** (lo scratch). **Su dbdev ce ne sono dieci in più**,
   tutte spente (`active = false`, note come `non_versionata_o_non_rilevabile` o `exclude_constraint_detected`), scritte
   dal vecchio seed dell'overlap ritirato: il mirror non le cancella. Sono righe di una macchina sola: **domanda per Tid**
   — si tolgono a mano da dbdev (sono un difetto di dati, non di codice), o si lasciano? **Deciso** (Tid, 2026-11-09):
   si tolgono. Cancellate dalla sessione DB su dbdev, in una transazione che pretendeva esattamente dieci righe spente
   fuori dal CSV; due delle tabelle hanno un EXCLUDE, ma dichiarato a mano (`ex_scb_…`, `ex_src_…`), non della regola.
   Il registro di dbdev ora ha le sette righe del CSV.
3. **Un difetto nuovo, trovato provando:** il ramo che riconcilia il nome nel runner ATTIVO, su `vendite.note_preventivo`
   (una partizione di `vendite.note` con la FK dichiarata sulla partizione), non toglieva il trigger vivo e ne creava un
   secondo, perché `fn_drop_triggers_by_function_args` escludeva ogni partizione. Il `-41` lo cura (tocca i trigger della
   partizione stessa, lascia i cloni del padre); il test 9 del pgTAP nuovo presidia i doppioni. È un prerequisito del
   `-34`: senza, il cambio di nome avrebbe lasciato due REQUIRE sulla stessa riga.
4. **La rinomina del trigger di audit** è l'unica DDL su un trigger generato del giro, nella forma condizionale di §11.5.

**Le prove** (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML nell'ordine di Liquibase: i `20_code`, il
`-38`, il mirror simulato sulle sette righe, il `-40`; `BEGIN … ROLLBACK`): andata e ritorno passano su tutti e due; con il
runner ATTIVO dopo l'SQL, verdi il pgTAP nuovo, i quattro dei trigger ATTIVO, quello dell'overlap e quello del cleanup;
tutta `dbops/` e i pgTAP che nominano overlap, cleanup, i nomi o le note: sette rossi, uguali senza il blocco (si lanciano
come app). Guardrail verdi.

**Per Tid:**
1. **Apply** di `20261110-34` … `-41` e del CSV `automazione_overlap.csv`, su dbdev e scratch.
2. **`make db-ci-apply`**: il runner ATTIVO rigenera i 58 trigger col nome nuovo (sui due database).
3. **pgTAP come app:** `dbops/test-nomi-e-chiavi-registri-v1`, `dbops/test-cleanup-framework`,
   `vendite/test-registri-fatturazione-scadenza-alla-nascita`, `dbops/test-overlap-tabella-sparita-v1`,
   `dbops/test-overlap-regola-e-vincolo-v1`, `dbops/test-fn-apply-automazione-overlap-key-expressions-v1`,
   `dbops/test-fn-apply-automazione-overlap-where-predicate-v1`, `dbops/test-anti-overlap-enforcement-gate-v1`,
   `dbops/test-attivo-due-fk-stessa-coppia-v1`, `dbops/test-trigger-attivo-orfani-v1`,
   `dbops/test-trigger-attivo-riconoscimento-per-funzione-v1`.
4. La domanda del punto 2 (le dieci righe di dbdev).

**Applicato** da Tid (2026-11-09) su dbdev e scratch, pgTAP verdi. Resta il commit, quando Tid lo chiede.

Ricadute BE: nessuna (`backend/` non nomina le due funzioni del cleanup né le colonne dell'overlap; grep, 2026-11-08).

**Doc (2026-11-09):** scritta da un agente su brief della sessione DB, riletta dalla sessione. Nuova:
`dbops/manual/fn_jsonb_array_di_testi.md`. Riscritte: `dbops/manual/fn_name_from_template.md` (ora idempotente),
`fn_nome_oggetto_dichiarato.md`, `fn_drop_triggers_by_function_args.md` (le partizioni), `fn_apply_cleanup_at.md`,
`fn_purge_cleanup_expired.md`, `fn_run_automations_cleanup.md` (le firme), `automazione_overlap.md` (chiavi jsonb, il
CSV), `fn_apply_automazione_overlap.md`; `guide/automazione-db.md` (§4.3, §5.4, la checklist); `linee-guida-sql.md`
(fuori perimetro, falsa: diceva che un vincolo parziale non lo gestisce il framework, ma lo fa con `where_predicate`).
La scheda auto-generata di `forme_giuridiche_tipi_soggetto_dettaglio` porta il nome vecchio del trigger fino alla
rigenerazione dopo l'apply.

## 29. Giro 10d — la politica degli indici delle FK: preparazione (2026-11-09)

Il giro 10c è chiuso: il blocco 10c-4 è committato (`48b5d39354`, 2026-11-09). Questo è l'ultimo blocco del giro 10
(§8): Q14 ② (la FK a `false` che sparisce dal presidio), D23 (il nome dell'indice di una riga di politica), il
`fk_index_policy.csv` che nessuno carica (§23.11), la parte di D13 rimasta su `fn_seed_fk_index_policy` (§26.6
punto 4) e il residuo di §14.8. **Nessuno sviluppo prima del via di Tid**: qui ci sono la riverifica, i nodi e i
blocchi.

**Brief vicini verificati:** `framework-automazione-db-migliorie.md` §2.1 (il nome di `fn_populate_fk_index_policy`,
che la guida confondeva con l'apply): è un punto di documentazione, e questo giro riscrive comunque il COMMENT e la
pagina; non serve un brief nuovo. `brief-db-articoli-obsoleto-dal.md` dice che le righe delle FK nuove «le scrive il
prossimo `ci_apply`»: non è vero (punto 3 qui sotto), lo si corregge là quando quel brief si riapre.

### 29.1 La riverifica (schede auto-generate di oggi e catalogo dei due database, in sola lettura)

Struttura (il contratto):

1. **`dbops.fk_index_policy`**: `consentito boolean NOT NULL DEFAULT true`, `generated_by_script boolean NULL DEFAULT
   false`, `dll_command` con il CHECK `chk_fk_index_policy_dll_command_forma`. Il default `true` dice il contrario di
   ciò che fa la scoperta, che scrive `false`.
2. **Gli scrittori** dicono tre cose diverse: `fn_populate_fk_index_policy` scrive `false` sulle FK scoperte senza riga;
   `fn_seed_fk_index_policy` scrive `true` e `generated_by_script = true` sulle FK **già coperte** senza riga (dalla
   vista `vw_fk_con_indice_missing_policy`); i CSV scrivono una decisione. Q14 ② vuole un solo scrittore delle decisioni,
   il seed.
3. **Chi esegue la scoperta:** solo il job pgAgent della domenica (`maintenance.proc_apply_fk_index_policy_job(true)`).
   Non la esegue né il `90_end` (`20250626-31`, che chiama solo l'apply) né `ci_apply`. Su un database da zero, quindi,
   le FK nuove non hanno riga, e il presidio non sa distinguere «nuova» da «decisa».
4. **`fn_seed_fk_index_policy` non la chiama nessuno** (`grep` sul repo, 2026-11-09: solo i changeSet che la creano e
   la nota di `presidi.csv`). È una promessa senza esecutore, e scrive una decisione da un'automazione. Legge l'ambito
   da sé, per schema (D13).
5. **`vw_fk_senza_indice` fa due mestieri:** è l'ingresso della scoperta e la guardia 1 dell'apply (cioè il fatto «la FK
   è scoperta»), ed è anche il presidio. Il filtro `COALESCE(pol.consentito, true) = true` fa sparire dal fatto una FK
   decisa a `false`: è Q14 ②.
6. **D23 confermato:** il nome dell'indice si ricava dal `dll_command` in due modi. L'apply prende la sesta parola
   (`split_part(…, ' ', 6)`); `vw_indici_ridondanti_prefisso` usa `ILIKE '%' || nome || ' ON%'`, quindi un nome che è
   il suffisso di un altro, o che contiene `_` (il jolly di LIKE), aggancia la riga sbagliata e dice `AUTOMAZIONE_FK`.
7. **L'ambito si legge in due modi.** Le quattro viste della politica e `fn_seed_fk_index_policy` guardano solo lo
   schema (`EXISTS … sc.schema_name = …`); il framework ha il BB `dbops.fn_table_in_scope`, che legge anche
   `table_like`. Per `dbops`, l'ambito dichiara sette tabelle, ma la politica governa tutte le FK dello schema. Per
   esempio `dbops.coda_lavori` ha una decisione (`fk_index_policy_coda_lavori_emittente.csv`) e non è fra le sette.
   L'apply, poi, non legge l'ambito: scorre ogni riga. Una riga `false` fuori ambito fa il `DROP`, una riga `true`
   fuori ambito non crea mai (la guardia 1 vede solo l'ambito).
8. **Una tabella, trentacinque CSV:** 34 CSV laterali caricati, uno per cantiere, più il `dbops/fk_index_policy.csv`
   che nessuno carica (ha ancora le colonne `user_update`/`data_update` tolte nel 7-bis-b). Contro la regola «una
   tabella, un CSV» (`linee-guida-sql.md` §11.2).
9. **Il residuo di §14.8 era una diagnosi sbagliata.** `config` è nell'ambito: c'è `config,*all` in
   `automation_scope.csv` dal 2025-11-23, ed è letto sui due database. La FK `fk_stradario_comune_id` non compariva in
   `vw_fk_senza_indice` perché la sua riga era `false`: il filtro del punto 5, cioè Q14 ② stessa. La cura di allora (riga
   a `true` e l'indice in `20261107-19`) resta giusta.

Fatti datati, 2026-11-09. Servono a trovare gli errori, non a decidere:

| | dbdev | scratch (da zero) |
| --- | --- | --- |
| righe di politica (`false`/`true`) | 733 / 175 | 96 / 65 |
| FK nell'ambito senza riga | 139 | 845 |
| righe di `vw_fk_senza_indice` | 0 | 510 |
| righe su una FK che non c'è | 34 | 14 |

* Lo zero di dbdev è il difetto di Q14 ②, non un database in ordine: il job ha scritto `false` su ogni FK scoperta, e
  così sono uscite tutte dal presidio.
* Le 14 righe «senza FK» dello scratch sono le FK del ponte verso `django.auth_user`
  (`config/fk_index_policy_auth_user.csv`, `fk_index_policy_credenziali.csv`). In CI quelle FK nascono dopo Liquibase,
  quindi sono decisioni vere su FK che nascono più tardi, non righe morte. ⇒ **Nessuna pulizia può cancellare una riga
  di seed perché la FK manca.**
* I CSV, confrontati fra loro (solo i file): 504 chiavi, di cui 29 in due file. In 28 casi i due file sono l'orfano e un
  laterale (vince il laterale, l'unico che gira). **Un conflitto è fra due CSV caricati**:
  `pratiche.template_flussi_handler_eventi.fk_tfhe_template_flusso` è `true` in `pratiche/fk_index_policy_tfhe.csv`
  (`20260615-10`) e `false` in `dbops/fk_index_policy_bonifica_ridondanze.csv` (`20260727-38`). Oggi vince il file che
  gira per ultimo.
* L'orfano: 344 chiavi stanno solo lì. Sono la fotografia di dbdev del 2026-01-16 (`titodb`, `generated_by_script`
  copiato), cioè l'output delle due automazioni, non decisioni di un seed. Fanno eccezione le 15 righe aggiunte il
  2026-09-28/29 dai cantieri del magazzino, tutte `false`: decisioni vere, scritte in un file che nessuno carica (i
  changeSet di quei cantieri dicono «sta nel CSV principale»). Delle 115 `true` che ci sono solo lì, 104 sono su FK
  vive; 101 di queste hanno l'indice dal changeSet della tabella, quindi la riga non decide niente. **Tre sono scoperte
  da zero**: `anagrafiche.soggetti_ruoli.fk_tipi_ruoli_config`, `anagrafiche.soggetti.fk_titoli_cortesia_config`,
  `pagamenti.sepa_mandati.fk_sepa_mandati_billing_account`. Su dbdev hanno l'indice, da zero no.

### 29.2 I nodi (decisioni di Tid)

Q14 ② è già deciso (§4): `consentito` lascia il posto a `decisione` (`DA_DECIDERE` / `CON_INDICE` / `SENZA_INDICE`,
default `DA_DECIDERE`) e a `motivo`; la scoperta scrive solo `DA_DECIDERE` e solo sulle FK nuove; la decisione la
scrive solo un seed; il presidio mostra le `DA_DECIDERE`. I nodi che seguono sono quelli che la decisione lascia aperti.

* **N1 — Una tabella, un CSV.** I 34 laterali e l'orfano diventano un solo `80_data/sql/dbops/fk_index_policy.csv`,
  con un solo mirror (`loadUpdateData`, `primaryKey` sulla terna, `runOnChange` + `validCheckSums: ANY`). Gli YAML e i
  CSV laterali si cancellano, come per `famiglie_documento` il 2026-09-18; le righe in `databasechangelog` restano
  orfane. I changeSet di `DELETE` congelati restano, e il CSV unico non contiene le righe che quelli tolgono.
  **Proposta: sì.** Per il conflitto `fk_tfhe_template_flusso`, la proposta è `SENZA_INDICE`: è la decisione più
  recente, ed è motivata (la bonifica delle ridondanze); è anche ciò che oggi gira per ultimo.
* **N2 — Che cosa entra dall'orfano.** Proposta: entrano come decisioni solo le 15 righe del magazzino (`SENZA_INDICE`)
  e, **una per una, le tre FK scoperte da zero** con `true` (Tid decide: `CON_INDICE`, che da zero crea un indice che
  oggi c'è solo su dbdev, oppure `SENZA_INDICE`, che su dbdev lo toglie). Le altre 326 righe sono output delle
  automazioni: non entrano, e su dbdev diventano `DA_DECIDERE` (Q14 ②: «quelle scritte solo dall'automazione»).
  L'orfano si cancella.
* **N3 — Come si convertono le righe di oggi.** Proposta: il changeSet della colonna scrive `DA_DECIDERE` su tutte le
  righe, e il mirror del CSV unico, che gira dopo, riscrive le decisioni. Il risultato è uguale da zero e su dbdev, e
  non serve un censimento dei seed fatto a mano: il seed è il CSV. Escono anche `consentito` e `generated_by_script`.
  Il secondo è un marcatore copiato nei CSV coi valori di dbdev e oggi non dice chi ha scritto la riga: lo dice
  `decisione`. Il vocabolario sta in un CHECK, non in una tabella: sono tre valori che il codice legge, non un catalogo.
* **N4 — Che cosa fa l'apply con `DA_DECIDERE`.** Proposta: **niente**, né `CREATE` né `DROP`. Oggi una riga `false`
  scritta dall'automazione toglie l'indice per nome. Con N3, su dbdev le righe dell'automazione smettono di farlo: un
  indice nato in un changeSet col nome canonico non lo toglie più nessuno finché non c'è una decisione.
  `CON_INDICE` e `SENZA_INDICE` restano come oggi, con le due guardie.
* **N5 — Dove gira la scoperta.** Proposta: anche a ogni migrate, con un changeSet `runAlways` di `90_end`, oltre al job
  della domenica. Così il registro ha la stessa forma da zero e su dbdev, e il presidio vede le FK nuove già in CI.
  L'ordine rispetto all'apply non conta: l'apply ignora le `DA_DECIDERE` (N4). Alternativa: la scoperta resta solo nel
  job, e il presidio legge le FK scoperte senza riga direttamente dal catalogo.
* **N6 — Il fatto e il presidio si separano.** Proposta: `vw_fk_senza_indice` diventa solo il fatto («la FK è
  scoperta»), senza filtro sulla decisione e con la colonna `decisione` (NULL = senza riga). La leggono la scoperta e la
  guardia 1. Nasce il presidio `dbops.vw_fk_da_decidere`: le FK scoperte senza riga o `DA_DECIDERE`, più le
  `CON_INDICE` ancora scoperte dopo l'apply (una promessa non mantenuta). Va nel catalogo dei presidi
  (`presidi.csv` / `presidi_testi.csv`), e la riga di oggi di `vw_fk_senza_indice` cambia nota.
* **N7 — `fn_seed_fk_index_policy` e `vw_fk_con_indice_missing_policy` si ritirano.** Proposta: sì. Scrivono una
  decisione da un'automazione, contro Q14 ②, e non le esegue nessuno. Una FK coperta da un indice del suo changeSet non
  ha bisogno di una riga: la politica governa gli indici che crea lei. (Il corollario resta: una riga `SENZA_INDICE` col
  nome canonico toglie quell'indice.) Lettori da riallineare: `presidi.csv` (riga 18), `scripts/indicatori-qualita-db.sh`
  (riga 180, che oltretutto la chiama «FK senza indice fuori policy», cioè il contrario di ciò che è), le pagine
  `manual/`. Chiude la parte di D13 rimasta al giro 10d.
* **N8 — D23: il nome dell'indice in un posto solo.** Proposta: una colonna generata
  `indice_nome text GENERATED ALWAYS AS (substring(dll_command FROM '^CREATE INDEX IF NOT EXISTS ([a-z_][a-z0-9_$]*) ON '))
  STORED`, con la stessa grammatica del CHECK. L'apply e `vw_indici_ridondanti_prefisso` la confrontano per
  uguaglianza. I mirror non la scrivono (non la nominano). Alternativa: una funzione `IMMUTABLE` letta dai due.
* **N9 — Il perimetro della politica.** Due strade: (a) la politica segue `fn_table_in_scope`, come il resto del
  framework; allora `dbops.coda_lavori` e le altre tabelle di `dbops` fuori elenco escono dal governo, e le loro
  decisioni diventano inerti; aggiungerle all'ambito vorrebbe dire armare su di loro anche i trigger delle altre
  automazioni. (b) La politica degli indici governa **per schema**, per scelta dichiarata: l'indice di una FK serve a
  ogni tabella, mentre l'elenco delle tabelle serve ai trigger. In questo caso le cinque letture per schema diventano
  un BB solo, e il COMMENT e `automation_scope.md` lo dicono. **Proposta: (b).** In tutte e due le strade, l'apply agisce
  solo sulle righe nell'ambito; una riga fuori ambito non fa niente, e la mostra il presidio di N6.

### 29.3 I blocchi

| Blocco | Contenuto | Perché a parte |
| --- | --- | --- |
| 10d-1 | N1, N2, N3: il CSV unico e il suo mirror, la colonna `decisione` (con `motivo`), la conversione, le colonne che escono | La forma del registro. Viene prima, perché tutti i lettori la leggono |
| 10d-2 | N4, N5, N6, N8, N9: apply, scoperta, la vista del fatto, il presidio nuovo, il nome dell'indice, il perimetro | I lettori e gli scrittori della forma nuova, aperti una volta sola |
| 10d-3 | N7: il ritiro del seed e della vista, coi lettori | Un ritiro in un changeSet solo (D61) |

Dentro 10d-1 l'ordine conta. Lo `00_schema` aggiunge `decisione` e `motivo` e scrive `DA_DECIDERE`. Il mirror unico
(`80_data`) gira dopo i congelati. Il `DROP` di `consentito` e di `generated_by_script` sta in `80_data`, dopo i loader
congelati che le nominano: lo stesso schema del `20261109-31`. I loader laterali si cancellano, quindi da zero non
girano più. I `DELETE` congelati invece girano, e trovano le colonne ancora lì.

**pgTAP previsti:** nuovo, sulla politica: la FK `SENZA_INDICE` resta nel fatto e non compare nel presidio; una FK nuova
è `DA_DECIDERE` e compare nel presidio; l'apply non tocca una `DA_DECIDERE`; il nome dell'indice è un suffisso di un
altro e contiene `_` (D23); una riga fuori ambito non fa niente; il CSV unico non ha chiavi doppie e ogni riga nomina una
FK viva o una FK del ponte django. Da riscrivere: `dbops/test-indici-letture-trasversali-v1` (test 8, `consentito`),
`dbops/test-marcatori-automazione-senza-esecutore-v1` (riga 229, se il marcatore cambia),
`dbops/test-processi-jobname-wrapper` (se N5 tocca il processo). Si censiscono anche gli header dei pgTAP che citano
un laterale.

**Doc:** `dbops/manual/` di `fk_index_policy`, `apply_fk_index_policy`, `fn_populate_fk_index_policy`,
`vw_fk_senza_indice`, `vw_indici_ridondanti_prefisso`, `automation_scope`, `processi`, una pagina nuova per il
presidio; le due pagine dei ritirati si cancellano (N7); `guide/automazione-db.md`,
`guide/database-che-resta-veloce.md`, `linee-guida-sql.md` dove parlano di `consentito` (§11.2 sui CSV laterali). I
commenti `consentito = false` sparsi nei changeSet mergiati non si toccano: sono storia.

**Ricadute BE:** nessuna (`grep` su `backend/` e `frontend/src`, 2026-11-09: nessuno nomina la tabella né le viste).

**Numeri:** li dà Tid col via. Ci sono altre sessioni DB, e la regola del max+1 si riverifica subito prima di scrivere.

### 29.4 Le decisioni di Tid (2026-11-09)

«Accetto le proposte»: N1, N3-N9 come da §29.2; N1 col conflitto `fk_tfhe_template_flusso` a `SENZA_INDICE`; N9 (b).
**N2:** le 15 righe del magazzino entrano come `SENZA_INDICE`; **restano da decidere le tre FK scoperte da zero**
(`CON_INDICE` o `SENZA_INDICE`, una per una), perché N2 non aveva una proposta su di loro.

**Numeri riservati:** `20261110-42` … `-61` (il massimo usato era il `-41`, su file, scratch e dbdev, letto il
2026-11-09). Il giro ne prevede circa tredici; il resto è margine per le correzioni dopo l'apply. L'altro cantiere parte
dal `20261110-62`.

### 29.5 Che cosa è scritto (2026-11-09)

Via di Tid: «ok puoi iniziare» (2026-11-09). Numeri usati: `20261110-42` … `-54`; dal `-55` al `-61` restano liberi nel
range riservato.

| changeSet | Che cosa |
| --- | --- |
| `00_schema/dbops/20261110-42` | `decisione` (CHECK, default `DA_DECIDERE`), `motivo` (CHECK: mai vuoto), `indice_nome` generato dal `dll_command` (D23); COMMENT della tabella e delle colonne |
| `20_code/dbops/20261110-43` | il BB `dbops.fn_indici_schema_nell_ambito(schema)`, `LANGUAGE sql` espandibile (N9 b) |
| `20_code/dbops/20261110-44` | `vw_fk_senza_indice` solo il fatto, con `decisione` in coda (N6) |
| `20_code/dbops/20261110-45` | `vw_indici_ridondanti_prefisso` per nome esatto, `policy_decisione` (D23); DROP e CREATE |
| `20_code/dbops/20261110-46` | `vw_duplicate_indexes`: l'ambito dal BB (era la sesta copia della stessa lettura) |
| `20_code/dbops/20261110-47` | `apply_fk_index_policy` sui tre valori, solo nell'ambito (N4, N9) |
| `20_code/dbops/20261110-48` | `fn_populate_fk_index_policy`: `DA_DECIDERE` sulle FK nuove, via le `DA_DECIDERE` non più scoperte; mai una riga decisa |
| `20_code/dbops/20261110-49` | il presidio `vw_fk_da_decidere` (N6) |
| `20_code/dbops/20261110-50` | ritiro di `fn_seed_fk_index_policy` e `vw_fk_con_indice_missing_policy` (N7) |
| `80_data/changelog/20261110-51` | il mirror del CSV unico `80_data/sql/dbops/fk_index_policy.csv` (N1) |
| `80_data/changelog/20261110-52` | la riga del presidio ritirato esce dal catalogo |
| `80_data/changelog/20261110-53` | `DROP` di `consentito` e `generated_by_script`, dopo i congelati che le nominano (N3) |
| `90_end/20261110-54` | la scoperta a ogni migrate, `runAlways` (N5) |

**Cancellati** (confermato da Tid, 2026-11-09): i 34 loader laterali di `80_data/changelog/` (tutti e soli quelli che
caricavano un `fk_index_policy_*.csv`) e i loro 34 CSV, come per `famiglie_documento` il 2026-09-18. Nessun changeSet è
modificato; le righe in `databasechangelog` restano orfane. Il `fk_index_policy.csv` orfano è sostituito dal CSV unico,
con lo stesso nome: i commenti dei changeSet che dicevano «sta nel CSV principale» ora dicono il vero.
**Cataloghi:** `presidi.csv` e `presidi_testi.csv` (esce la vista ritirata, entra il presidio, note riscritte),
`processi.csv` (la nota della scoperta). **Altro:** `scripts/indicatori-qualita-db.sh` e
`dev/qualita-db-indicatori.md` contano il presidio nuovo.
**pgTAP:** nuovo `dbops/test-fk-index-policy-decisione-v1` (22, runner owner: si fabbrica due schemi, uno nell'ambito);
riscritto il test 8 di `dbops/test-indici-letture-trasversali-v1` (`decisione` e `indice_nome`).

Il CSV unico aveva 180 righe (65 `CON_INDICE`, 115 `SENZA_INDICE`): le 161 che lo scratch ha da zero (i 34 laterali più
`anagrafiche.pdp.fk_pdp_utility`, scritta in linea da `20260215-14`/`-15`) e 19 righe del file orfano scritte a mano.
Dopo le decisioni di §29.11 ne ha 179 (68 `CON_INDICE`, 111 `SENZA_INDICE`).

### 29.6 Le scelte dentro il giro (da guardare, Tid)

1. **Le righe dell'orfano scritte a mano sono 19, non 15.** Oltre alle 15 del magazzino ci sono 4 righe del 2026-05-24
   (`vendite.note_offerte_commerciali`, quattro FK, tutte `false`), scritte a mano e non dall'automazione. Sono entrate
   come `SENZA_INDICE`, perché è quello che dicevano. Le FK sono vive tutte e 19.
2. **`motivo` è vuoto in tutto il CSV.** Il perché delle decisioni passate sta nelle testate dei loader cancellati (git),
   ma è scritto per file, non per FK, e pieno di conteggi, nomi di brief e numeri di changeSet: copiarlo avrebbe portato
   nel dato proprio quello che non deve starci. Il `motivo` si scrive quando una decisione si riapre.
3. **Le tre FK di N2 non sono nel CSV**: aspettano la decisione di Tid. Fino ad allora su dbdev la loro riga esce (la FK
   è coperta dall'indice che c'è già, quindi non è scoperta) e l'indice resta; da zero sono `DA_DECIDERE` e l'indice
   non c'è. Con la decisione entrano nel CSV.
4. **`vw_duplicate_indexes` è entrata nel giro**: era la sesta copia della lettura dell'ambito per schema (regola del 2).
5. **Il presidio non ha `colonna_variante`**: i tre casi stanno nella colonna `caso`, con una sola frase per chi agisce.
6. **I changeSet di codice non hanno un ritorno indietro singolo** (`SELECT 1`): le versioni di prima leggevano
   `consentito`, che il giro toglie. Il giro torna indietro tutto insieme.
7. **Il guardrail del preambolo pgTAP** chiede di abbassare la soglia dei `throws_ok` senza discriminante (110 → 109): il
   calo viene dai pgTAP del cantiere `catalogo` nel working tree, non da questo giro. La soglia la cambia quel cantiere.

### 29.7 Le prove (scratch `zeroerp_ruoli` e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase dopo la riga `BEGIN;`, transazione annullata)

Ordine dell'SQL: `-42` … `-50`, il mirror simulato del CSV unico (UPDATE delle righe che ci sono, INSERT di quelle che
mancano, nessuna DELETE), i mirror simulati delle righe del giro in `presidi.csv` e `presidi_testi.csv`, `-52`, `-53`,
l'apply (`90_end/20250626-31`), `-54`.

* **Il pgTAP nuovo:** 22/22 sullo scratch e su dbdev (6,7 s).
* **Su dbdev nessun indice cambia**: nella stessa transazione zero indici tolti e zero nati. Fatti datati: delle righe
  di oggi 178 diventano decisioni (65 `CON_INDICE`, 113 `SENZA_INDICE`), 493 restano `DA_DECIDERE` (le FK nuove che il
  job aveva scritto `false`: il difetto di Q14 ②), 237 escono perché la FK non è più scoperta; 2 righe del CSV nascono.
  Il presidio su dbdev ha 493 righe `DA_DECIDERE`.
* **Regressione «senza → con»** su 16 pgTAP vicini (cataloghi dei presidi, processi, riferimenti morti con
  `plpgsql_check`, marcatori, letture trasversali, duplicati, e i cinque di `vendite` che nominano le viste): zero rossi
  senza e zero con, sullo scratch.
* **Guardrail** verdi: `run_on_change`, `v1_congelato`, `pgtap_preambolo`, `sql_letterali`, `timestamp_senza_fuso`,
  `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch`; pre-commit verde.

### 29.8 Per Tid

1. **Apply** di `20261110-42` … `-54` (e del CSV) su dbdev e scratch.
2. **pgTAP come app:** `dbops/test-fk-index-policy-decisione-v1` (runner owner), `dbops/test-indici-letture-trasversali-v1`,
   `dbops/test-catalogo-presidi-v1`, `dbops/test-presidi-testi-v1`, `dbops/test-riferimenti-morti-v1`,
   `dbops/test-vw-duplicate-indexes-vincoli-v1`, `dbops/test-processi-jobname-wrapper`.
3. **Le tre FK di N2**, una per una (§29.6 punto 3).
4. Le scelte di §29.6.

Ricadute BE: nessuna (`backend/` e `frontend/src` non nominano la tabella né le viste).

### 29.9 Doc (2026-11-09)

Scritta da un agente su istruzioni della sessione DB, riletta dalla sessione. Nuove: `dbops/manual/fn_indici_schema_nell_ambito.md`,
`dbops/manual/vw_fk_da_decidere.md`. Cancellate (oggetti ritirati): `dbops/manual/fn_seed_fk_index_policy.md`,
`dbops/manual/vw_fk_con_indice_missing_policy.md`, con i loro link. Riscritte: `dbops/manual/` di `fk_index_policy`,
`apply_fk_index_policy`, `fn_populate_fk_index_policy`, `vw_fk_senza_indice`, `vw_indici_ridondanti_prefisso`,
`vw_duplicate_indexes`, `automation_scope`, `fn_seed_automazione_guard_utility_tipo_ruolo`;
`maintenance/manual/proc_apply_fk_index_policy_job.md`; `guide/automazione-db.md` (§6 e §1.1), `linee-guida-sql.md`
(§8.6, §8.7, §10.9, §11.2), `guide/database-che-resta-veloce.md`, `tutorial/framework-automazione-db.md`,
`postgresql/row-level-security.md`; le pagine `manual/` di `config`, `vendite` e `documenti` che citavano il flag per una
FK precisa, tradotte nel vocabolario nuovo e verificate sul CSV unico. Tre di queste dicevano il falso già prima
(`offerte_commerciali`, `contratti`: «consentito=false come fk_preventivi_valuta», ma nessuna delle due FK ha una riga;
`fatturazione_lotti_gruppi`: la FK è coperta dalla UNIQUE e la scoperta non la registra). In `fatturazione_lotti_gruppi`
corretta anche la vista che segnala un indice ridondante per prefisso (è `vw_indici_ridondanti_prefisso`). Gli `index.md`
di schema e le schede auto-generate si rigenerano dopo l'apply: fino ad allora le schede dei due oggetti nuovi non
esistono, e i loro link sono morti.

### 29.10 Dopo l'apply (2026-11-09)

**Applicato** da Tid su dbdev e scratch: migrazione `20261110-42` … `-54` e il CSV unico, pgTAP come app verdi. Restano le
tre FK di N2 (§29.6 punto 3), le scelte di §29.6 e il commit del giro.

### 29.11 Le decisioni di Tid sulle scelte di §29.6, e il seguito (2026-11-09)

| Punto | Decisione | Che cosa ne viene |
| --- | --- | --- |
| 1, le 4 righe delle note delle offerte | erano di prova, non decisioni | escono dal CSV; `80_data/changelog/20261110-55` le toglie dove il mirror le aveva scritte (il mirror non cancella) |
| 2, `motivo` vuoto | ok: è un database di sviluppo | — |
| 3, le tre FK di N2 | `CON_INDICE` | entrano nel CSV coi comandi del vecchio file: `ix_anagrafiche_soggetti_ruoli_tipo_ruolo_id`, `ix_anagrafiche_soggetti_titolo_cortesia_id`, `ix_pagamenti_sepa_mandati_billing_account_id` |
| 4, 5, 6 | ok | — |
| 7, la soglia del preambolo | da correggere | già fatta: la soglia è a 109, l'ha abbassata il cantiere `catalogo` (`scripts/guardrail_pgtap_preambolo.py` nel suo working tree) |

Il CSV unico ha 179 righe (68 `CON_INDICE`, 111 `SENZA_INDICE`); la testata del mirror `-51` (runOnChange + ANY) lo dice.

**Le prove** (scratch e dbdev, da owner, transazione annullata: il mirror simulato col CSV nuovo, il `-55`, l'apply, la
scoperta): le tre FK sono `CON_INDICE` e coperte su tutti e due; sullo scratch l'apply crea i tre indici, su dbdev ci
sono già (la guardia 1 salta). Le quattro righe escono; la scoperta ne riregistra tre `DA_DECIDERE`, la quarta FK
(`fk_offnote_testata`) è coperta. La documentazione non nomina queste righe: nessuna pagina da cambiare.

**Per Tid:** apply del CSV unico e del `20261110-55` su dbdev e scratch; pgTAP `dbops/test-fk-index-policy-decisione-v1`.
Poi il commit del giro 10d.

## 30. Giro 11 — le etichette di prova: la FK della credenziale (Q14 ⑩), preparazione (2026-11-09)

Il giro 10d è chiuso: committato da Tid (`2050435065`, 2026-11-09). Il `20261110-55` è applicato su dbdev; nel
`databasechangelog` dello scratch, letto lo stesso giorno, non c'è ancora. **Numeri riservati** (Tid, 2026-11-09):
`20261110-56` … `-61`, poi il primo libero.

**Brief vicini verificati:** nessuno in `work-in-progress/` tocca `dbops.credenziali_di_prova`,
`dbops.trgfn_etichette_di_prova_guard` o `script.fn_elimina_credenziale` (grep, 2026-11-09).

### 30.1 La riverifica (schede auto-generate di oggi)

1. **`dbops.credenziali_di_prova`**: PK `auth_user_id`, nessuna FK. Il COMMENT dà il motivo («in CI `django.auth_user`
   nasce dopo Liquibase»), che è un fatto e non una ragione: le FK verso `django.auth_user` stanno nel ponte di `90_end`,
   con la preCondition `MARK_RAN` (per esempio `20260921-03`), e la gemella `soggetti_di_prova` ha la sua FK (verso
   `anagrafiche.soggetti`, `NO ACTION`). Il COMMENT cita anche un brief (§5d).
2. **`dbops.trgfn_etichette_di_prova_guard`** (montato su tutte e due le tabelle): rifiuta **ogni** UPDATE, DELETE e
   TRUNCATE con `E_ETICHETTA_DI_PROVA_IMMUTABILE`, e l'INSERT fuori da SVILUPPO.
3. **`script.fn_elimina_credenziale`** chiama la regola di `script.fn_check_credenziale_eliminabile`. Il motivo
   `CON_STORIA` ricava da `pg_constraint` (`script.fn_tabelle_che_trattengono`) le tabelle che trattengono la credenziale
   con una FK `RESTRICT` o `NO ACTION`. Le FK `CASCADE` non contano: le tabelle che le hanno seguono il `DELETE`.
4. **Orfani** (fatto datato, 2026-11-09): dbdev ha 8 etichette e nessuna senza credenziale; lo scratch nessuna etichetta.
   L'`ADD CONSTRAINT` passa; il changeSet li conta lo stesso e si ferma se ce n'è uno.
5. **L'indice della FK:** la colonna è la PK, quindi la FK è coperta e alla politica degli indici non serve una riga.

### 30.2 Il nodo (decisione di Tid)

**N1 — Che cosa succede a una credenziale di prova quando un SUPER_ADMIN la elimina.** §4 (Q14 ⑩) ha deciso la FK
`NO ACTION` «come la gemella» e ha lasciato al giro la scelta fra il rifiuto con codice e la porta che toglie etichetta
e utente insieme, proponendo la seconda. La riverifica (punto 3) cambia il conto delle due strade:

* **(a) `NO ACTION`: la credenziale etichettata non si elimina.** Non c'è codice da scrivere: la regola di eliminabilità
  vede la FK da `pg_constraint` e risponde `CON_STORIA` con `dbops.credenziali_di_prova` fra le tabelle. Così il
  pulsante è spento e la porta solleva `E_CREDENZIALE_CON_STORIA`. Il difetto è che la frase è falsa nel significato:
  un'etichetta non è storia. Diventa vera solo aggiungendo un motivo apposta (un codice nuovo e la rigenerazione BE).
* **(b) `CASCADE`: l'etichetta va via insieme alla credenziale.** La regola del guard diventa «un'etichetta non
  cambia, e si toglie **solo insieme alla sua radice**»: il DELETE di una riga è ammesso quando la radice
  (`django.auth_user` o `anagrafiche.soggetti`) non c'è più, cioè dentro la cascata della FK; resta rifiutato in ogni
  altro caso, e così TRUNCATE e UPDATE. `fn_elimina_credenziale` e la regola di eliminabilità restano come sono, e
  nessuno vede l'etichetta di una credenziale che non esiste (era il motivo della regola «non si toglie»: non
  nascondere un utente al presidio). La gemella resta `NO ACTION`: sulla sua radice la regola vale uguale, ma un
  soggetto con l'etichetta non si cancella comunque.

**Proposta: (b).** È quella di §4, e il modello la regge: l'etichetta descrive la credenziale e non le sopravvive.
(a) costa meno, ma dà al pulsante una ragione che non è quella vera.

### 30.3 I changeSet previsti (`20261110-56` …)

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/…-56` | (b) il guard: DELETE ammesso solo senza radice; COMMENT |
| `90_end/…-57` | la FK `fk_credenziali_di_prova_auth_user` verso `django.auth_user`, nel ponte (`MARK_RAN` senza django), `ON DELETE CASCADE` per (b) o `NO ACTION` per (a); prima, il conteggio degli orfani |
| `00_schema/dbops/…-58` | il COMMENT della tabella, senza il motivo falso e senza il brief |

pgTAP: su dbdev la FK c'è, in CI no (i due mondi, `skip()` motivato); (b) eliminare una credenziale etichettata toglie
anche l'etichetta, un DELETE diretto dell'etichetta resta rifiutato, e così il DELETE di una gemella con la radice viva;
(a) la regola di eliminabilità risponde `CON_STORIA`. Da riscrivere: `dbops/test-etichette-di-prova-v1` se prova il
DELETE. Doc: COMMENT della tabella; `dbops/manual/credenziali_di_prova.md`, `trgfn_etichette_di_prova_guard.md`,
`vw_radici_di_prova_in_produzione.md`, `soggetti_di_prova.md`, la pagina di `fn_elimina_credenziale`;
`backend/amm-software/manual/api_amm_software.md` al team BE, se ne parla.
Ricadute BE: nessuna con (b); con (a) nessuna, salvo il motivo nuovo se lo si vuole vero.

### 30.4 Il via e che cosa è scritto (2026-11-09)

Via di Tid: «ok b procedi» (2026-11-09): N1 strada (b). Numeri usati: `20261110-56` … `-58`; `-59` … `-61` restano liberi.

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261110-56` | `trgfn_etichette_di_prova_guard`: il DELETE di una riga è ammesso solo se la radice non c'è più (`django.auth_user` per le credenziali, `anagrafiche.soggetti` per i soggetti); `django.auth_user` assente = radice viva (fail-closed); COMMENT |
| `90_end/20261110-57` | la FK `fk_credenziali_di_prova_auth_user` verso `django.auth_user`, `ON DELETE CASCADE`, `ON UPDATE NO ACTION`, nel ponte (`MARK_RAN` senza django); prima, le etichette orfane per nome (con una sola si ferma) |
| `00_schema/dbops/20261110-58` | il COMMENT della tabella: la FK, l'etichetta che va via con la credenziale; senza il motivo falso e senza il brief |

pgTAP nuovo: `dbops/test-credenziale-di-prova-fk-v1` (6, runner owner): i due mondi; DELETE diretto con la credenziale
viva rifiutato; la regola di eliminabilità non conta l'etichetta come storia; UPDATE rifiutato; cancellare la credenziale
toglie l'etichetta (la cancellazione in un'istruzione a sé, il conteggio in un'altra); l'etichetta di un soggetto vivo non
si cancella. Il test 9 di `dbops/test-etichette-di-prova-v1` (DELETE con la radice viva) resta valido com'è.

**Le prove** (scratch e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase, `-56`, `-58`, `-57`, dopo la riga
`BEGIN;`, transazione annullata):

* il pgTAP nuovo 6/6 su tutti e due. **La prova del rosso:** con la sola FK e il guard di prima la cascata è respinta
  (`E_ETICHETTA_DI_PROVA_IMMUTABILE`): il `-56` è il prerequisito del `-57`;
* regressione «senza → con» sui pgTAP vicini (`dbops/test-etichette-di-prova-v1`,
  `anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1`, `dbops/test-riferimenti-morti-v1`,
  `config/test-credenziali-porta-v1`, `config/test-elimina-credenziale-v1`, `script/test-rubinetto-primo-motivo-v1`,
  `dbops/test-app-postura-schema-django-v1`): stesso esito senza e con. I rossi che ci sono (3 in
  `test-credenziali-porta-v1`, 1 in `test-elimina-credenziale-v1`) sono i test «come app» lanciati da owner: uguali senza il
  giro;
* guardrail verdi.

Fatto datato: sullo scratch `django.auth_user` c'è, ma il ponte ha 3 FK su 24 (le sorelle sono segnate `MARK_RAN` da quando
lo scratch è nato senza django); il `-57` è nuovo, e lì la FK nasce.

**Doc:** `dbops/manual/credenziali_di_prova.md` (la sezione «nessun legame» diventa «l'etichetta segue la credenziale»),
`trgfn_etichette_di_prova_guard.md`, `soggetti_di_prova.md`, `script/manual/fn_elimina_credenziale.md` (l'etichetta fra le
cose che vanno via con la credenziale). `backend/amm-software/manual/api_amm_software.md` non ne parla. Ricadute BE: nessuna.

**Per Tid:**
1. **Apply** di `20261110-56` … `-58` su dbdev e scratch.
2. **pgTAP come app:** `dbops/test-credenziale-di-prova-fk-v1` (runner owner), `dbops/test-etichette-di-prova-v1`,
   `config/test-elimina-credenziale-v1`, `dbops/test-riferimenti-morti-v1`.

### 30.5 Applicato (Tid, 2026-11-09)

Migrazione `20261110-56` … `-58` applicata da Tid su dbdev e scratch; pgTAP come app di §30.4 verdi. Resta il commit,
con i soli file del giro (non quelli del cantiere `catalogo`). Il giro 11 è chiuso col commit.

## 31. Giro 12 — i presidi dei codici anche sulle funzioni SQL (Q15), 2026-11-09

### 31.1 Il censimento (scratch `zeroerp_ruoli` e dbdev, 2026-11-09)

Fatti datati, non motivi: il perimetro lo decide Q15 (chi può sollevare un codice, non il linguaggio).

* **Sette viste di `dbops` limitano i corpi al plpgsql** con lo stesso filtro scritto a mano (`p.prolang = (SELECT oid
  FROM pg_language WHERE lanname = 'plpgsql')`): `vw_codici_errore_da_dichiarare`, `vw_punti_canale_campo`,
  `vw_funzioni_check_codici`, `vw_punti_primo_motivo`, `vw_bersagli_non_dichiarati`, `vw_codici_errore_forme_condizione`;
  `vw_stati_check_scrittori` ha una terza forma (`l.lanname = ANY (ARRAY['plpgsql','sql'])`). Regola del 2: un BB.
* **Una funzione `LANGUAGE sql` chiama `fn_log_and_raise_error`: `script.fn_get_contatti`**, con due difetti suoi:
  * la validazione di `p_soggetto_id` sta in una CTE (`validate`) che nessuno legge, e PostgreSQL non la esegue: con il
    soggetto NULL la funzione restituisce zero righe in silenzio (provato su tutti e due i database);
  * il codice è `ERRORE_PARAMETRI`, obsoleto dal 2026-08-05 (vivo: `E_ERRORE_PARAMETRI`). È l'unica chiamata, in
    qualsiasi linguaggio, con un codice letterale fuori dalla grammatica `E_`: la rinomina di agosto non l'ha vista
    perché i presidi leggevano il solo plpgsql. È il buco di Q15, già aperto.
* Nessuna funzione SQL nomina oggi un codice `E_`, un motivo `'codice'` o `fn_raise_primo_motivo_se_presente`:
  l'allargamento non fa comparire righe nuove, quindi nessuna rigenerazione BE dall'allargamento.

### 31.2 Le decisioni (Tid, 2026-11-09)

| Nodo | Decisione |
| --- | --- |
| N1 `fn_get_contatti` | Riscritta in plpgsql, con un codice **specifico**: `E_CONTATTI_SOGGETTO_OBBLIGATORIO`, canale `parametro` = `p_soggetto_id`. Codice nuovo: rigenerazione delle politiche d'errore lato BE (§5) |
| N2 `vw_codici_errore_forme_condizione` | Resta sul plpgsql: la sua grammatica è quella dell'`IF`/`EXCEPTION WHEN`, che una funzione SQL non ha. Il limite si dichiara nel COMMENT, con il BB |
| N3 il perimetro | Le cinque viste che leggono chi solleva, chi nomina, chi costruisce un bersaglio si allargano. Il filtro diventa un **BB**: `dbops.fn_corpo_leggibile(prolang)`; lo usa anche `vw_stati_check_scrittori`, la cui copia si ritira |

Numeri (Tid, 2026-11-09): `20261110-59` … `-61` e `20261110-80` … `-85`.

⚠️ **Numeri, correzione del 2026-11-09.** Il cantiere `catalogo` ha scritto `20261110-85` … `-93` nello stesso momento:
il `-85` di questo giro è passato a `-99`, poi Tid l'ha rinumerato al primo libero, **`20261110-94`**. Questo giro usa `-59` … `-61`, `-80` … `-84`, `-94`.

### 31.3 Che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261110-59` | Il BB `dbops.fn_corpo_leggibile(p_prolang pg_proc.prolang%TYPE)`: vero per plpgsql e sql (BEGIN ATOMIC compresa), falso per c, internal e NULL. `LANGUAGE sql STABLE`, senza `SET`: si espande nella query, e la lettura di `pg_language` diventa un InitPlan |
| `20_code/dbops/20261110-60` | `vw_codici_errore_da_dichiarare`: i due rami leggono il BB; COMMENT |
| `20_code/dbops/20261110-61` | `vw_punti_canale_campo`: la CTE `funzioni` legge il BB; COMMENT (tre frasi dicevano «plpgsql») |
| `20_code/dbops/20261110-80` | `vw_funzioni_check_codici`: il BB, e il prefiltro diventa `prosrc LIKE '%fn\_check\_%' OR prosqlbody IS NOT NULL`; COMMENT |
| `20_code/dbops/20261110-81` | `vw_punti_primo_motivo`: il BB, prefiltro allargato come sopra; COMMENT (il perimetro, che non c'era) |
| `20_code/dbops/20261110-82` | `vw_bersagli_non_dichiarati`: il BB, prefiltro allargato come sopra; COMMENT |
| `20_code/dbops/20261110-83` | `vw_stati_check_scrittori`: la terza copia del filtro (JOIN `pg_language` + elenco a mano) si ritira, legge il BB; perimetro invariato |
| `20_code/dbops/20261110-84` | `vw_codici_errore_forme_condizione`: solo il COMMENT, il perimetro plpgsql dichiarato e perché (N2) |
| `20_code/script/20261110-94` | `script.fn_get_contatti` in plpgsql: `IF p_soggetto_id IS NULL` → `E_CONTATTI_SOGGETTO_OBBLIGATORIO` (canale `parametro`, variadico vuoto esplicito); la query di prima senza la CTE morta; firma, `RETURNS TABLE`, GRANT invariati; COMMENT |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_CONTATTI_SOGGETTO_OBBLIGATORIO`, `DATO_ERRATO` (come gli altri `*_OBBLIGATORIO`), messaggio id **1464** «Indicare il soggetto di cui leggere i contatti.» |

**Le scelte che non si vedono dal titolo (da guardare, Tid):**

1. **Il prefiltro su `prosrc` era cieco alle BEGIN ATOMIC** (trovato scrivendo il pgTAP): per una sql BEGIN ATOMIC
   `prosrc` è vuoto, e tre viste (`-80`, `-81`, `-82`) l'avrebbero lasciata fuori anche col perimetro allargato. Il
   prefiltro diventa «`prosrc` … `OR prosqlbody IS NOT NULL`»: le BEGIN ATOMIC passano tutte al filtro vero, sul corpo
   deparsato. È la stessa classe di D15.
2. **La forma del BB:** `p_prolang = ANY (ARRAY(SELECT …))` dentro un `COALESCE(…, false)`, non un `EXISTS` per riga:
   espansa nella vista, la sottoquery non dipende dalla riga e si calcola una volta.
3. **La classe del codice nuovo** è `DATO_ERRATO`, come i 38 `*_OBBLIGATORIO` e `E_ERRORE_PARAMETRI`.
4. **I COMMENT delle viste aperte** sono corretti nelle sole frasi sul perimetro: i marcatori di revisione e i nomi
   di brief che contengono restano al giro 14 (Q13), che li tratta tutti insieme.
5. **`fn_get_contatti` resta VOLATILE** com'era: il giro non cambia la volatilità di chi la chiama.

### 31.4 Le prove (scratch e dbdev, da owner, SQL estratto dagli YAML in ordine di Liquibase, dopo la riga `BEGIN;`, transazione annullata)

* **I changeSet base sono il vivo:** riprodotti in transazione, le definizioni delle sette viste e delle due funzioni
  dei contatti sono uguali a `pg_get_viewdef` / `pg_get_functiondef` su tutti e due i database.
* **Prima e dopo, riga per riga** (`EXCEPT ALL` nei due versi, tutti e due i database, stesso esito):
  * `vw_codici_errore_da_dichiarare`, `vw_punti_canale_campo`, `vw_codici_errore_forme_condizione`: **una riga nuova**,
    `E_CONTATTI_SOGGETTO_OBBLIGATORIO` di `fn_get_contatti` (in `vw_punti_canale_campo`: `DIRETTO`, `IN_CHIAMATA`,
    `parametro`; in `forme_condizione`: famiglia `PARAMETRO`). Nessuna riga sparita;
  * `vw_funzioni_check_codici`: **37 righe nuove**, nessuna sparita. Sono funzioni sql che nominano una `fn_check_*`
    (fatto datato, 2026-11-09): le `script.fn_scope_ef_whitelist*` e `fn_get_user_emittenti_scope` con
    `fn_check_user_emittente_scope` / `fn_check_ultimo_super_admin_attivo` (check senza motivi: codice NULL),
    `pratiche.fn_check_pratica_chiudibile` con `fn_check_chiusura_pratica`, `vendite.fn_listini_selezionabili` con
    `fn_check_listino_documento` (`E_DOC_LISTINO_UTILITY_DIVERSA`, `E_DOC_LISTINO_EMITTENTE_DIVERSO`). È un
    INVENTARIO: le due viste che lo leggono non cambiano (`vw_punti_primo_motivo` resta a 22 righe, e in
    `vw_punti_canale_campo` non entra un ramo PRIMO_MOTIVO nuovo);
  * `vw_punti_primo_motivo`, `vw_bersagli_non_dichiarati`, `vw_stati_check_scrittori`: identiche.
* **`fn_get_contatti` con un soggetto:** su dbdev 854 righe, uguali prima e dopo, per lei e per `fn_get_contatto_default`
  (sullo scratch non ci sono contatti). Con il soggetto NULL tutte e due rifiutano `E_CONTATTI_SOGGETTO_OBBLIGATORIO`.
* **Tempi** (fatto datato, dbdev, 2026-11-09): `vw_codici_errore_da_dichiarare` da ~175 a ~290 ms,
  `vw_punti_canale_campo` da ~640 a ~740 ms; le altre invariate. È il costo dei ~1.260 corpi sql in più: il
  perimetro è il modello. Il test sotto JIT (`test-vw-funzioni-check-codici-sotto-jit-v1`) resta verde.
* **pgTAP nuovo** `dbops/test-presidi-codici-corpo-leggibile-v1` (11, runner owner): il BB; le cinque viste sui casi
  costruiti in uno schema di prova (una sql, una sql BEGIN ATOMIC, una check sql, un primo motivo a mano, un
  bersaglio); `forme_condizione` che resta fuori; `fn_get_contatti` e `fn_get_contatto_default` col soggetto NULL;
  nessuna chiamata diretta, in nessun corpo leggibile, con un codice letterale fuori dalla grammatica `E_`. 11/11 su
  tutti e due. **La prova del rosso:** con il BB e `fn_get_contatti` ma le viste di prima, i test 3-7 sono rossi.
* **Regressione «senza → con»**, stesso esito su tutti e due, nessun rosso: `anagrafiche/test-contatti-soggetto-cliente`,
  `config/test-costanti-catalogo-citate-dal-codice-v1`, `dbops/test-audit-log-perimetro-scrittori-v1`,
  `dbops/test-corpo-funzione-senza-commenti-v1`, `dbops/test-punti-canale-campo-v1`, `dbops/test-stati-check-scrittori-v1`,
  `dbops/test-vw-bersagli-non-dichiarati`, `dbops/test-vw-codici-errore-motivo-nominato`,
  `dbops/test-vw-codici-errore-valore-atteso`, `dbops/test-vw-funzioni-check-codici-sotto-jit-v1`,
  `pagamenti/test-righe-contabili-eliminazione-v1`, `script/test-canale-log-v1`,
  `script/test-catalogo-messaggi-errore-completo`, `script/test-rubinetto-primo-motivo-v1`,
  `dbops/test-riferimenti-morti-v1`, `config/test-codici-errore-obsoleto-dal`, `config/test-codici-errore-identita`.
* **Guardrail** (pre-commit sui file del giro): verdi.

**Doc** (2026-11-09): pagina nuova `dbops/manual/fn_corpo_leggibile.md`; riallineate le pagine `manual/` delle sette
viste e di `script/manual/fn_get_contatti.md` (anche lo schema delle priorità, che non aveva le condizioni su
`istanza_utility_id` del corpo vivo) e `fn_get_contatto_default.md`. L'indice di `dbops` è generato: la voce della
funzione nuova compare alla prossima generazione. `linee-guida-sql.md` non descrive il perimetro di queste viste.

### 31.5 Ricadute BE

* **BE6, giro 12** ✅ (team BE, 2026-11-09, da committare: policy rigenerata, ripiego in `error_messages_fallback.py`, guardrail verde)**:** il codice nuovo `E_CONTATTI_SOGGETTO_OBBLIGATORIO` (DATO_ERRATO, canale `parametro`) entra in
  `error_policies_generated.py` e, se serve, in `error_messages_fallback.py`. Finché manca, il guardrail
  `test_error_codes_db_policy_guardrail` (CI, `ZEROERP_TEST_DB_E2E=1`) lo segnala: è la regola, non un difetto.
* Nessun altro: le viste allargate non cambiano colonne, e `fn_get_contatti` non ha chiamanti nel backend.

### 31.6 Per Tid

1. **Apply** di `20261110-59` … `-61`, `-80` … `-84`, `-94` e dei due CSV dei codici, su dbdev e scratch.
2. **pgTAP:** `dbops/test-presidi-codici-corpo-leggibile-v1` (runner owner), `dbops/test-punti-canale-campo-v1`,
   `dbops/test-vw-funzioni-check-codici-sotto-jit-v1`, `script/test-rubinetto-primo-motivo-v1`,
   `dbops/test-stati-check-scrittori-v1`, `dbops/test-vw-bersagli-non-dichiarati`, `anagrafiche/test-contatti-soggetto-cliente`,
   `script/test-catalogo-messaggi-errore-completo`, `dbops/test-riferimenti-morti-v1`.
3. **Commit:** solo i file del giro. ⚠️ `codici_errore.csv` e `messaggi_errore.csv` hanno nel working tree anche
   modifiche del cantiere `catalogo` (righe `E_DOC_COMPONENTE_BOM_NON_VALIDA`, `E_ARTICOLO_KIT_SENZA_COMPONENTI`):
   di questo giro è solo l'ultima riga di ciascuno.

## 32. Le segnalazioni del BE del 2026-11-09 (S-BE-2, S-BE-3): verifica della sessione DB

Verificate sul catalogo di scratch e dbdev (2026-11-09). Si sviluppano dopo il via di Tid sui nodi.

**S-BE-2 — confermata.** La lista `amm.processi` (`ui.lista_definizione` id 66) ha in `lista_colonna.csv` la sola
colonna `attivo` (id 723). Il COMMENT di `dbops.processi.attivo` dice già che `attivo` non dice se il processo è vivo:
`attivo` è «riferimento valido», il ritiro sta in `obsoleto_dal` (`script.fn_e_obsoleto`). Fatto datato: un processo
su 29 è `attivo` e ritirato, su tutti e due i database. La correzione è solo nel seed (una riga `vivo` in
`lista_colonna.csv`, e il preset se `vivo` va nella vista standard): nessun changeSet.
Nodo per Tid: `attivo` resta a video accanto a `vivo`?

**S-BE-3 — confermata.** Su `anagrafiche.soggetti` nessun trigger blocca `codice_fiscale` o `partita_iva`: il lock
generico (`trg_soggetti_a10_lock_columns_upd`) copre solo `codice`; i due trigger che leggono CF e P.IVA
(`trgfn_soggetti_guard_cf_piva_obbligatori`, `trgfn_soggetti_valida_cf_piva_dispatch`) controllano presenza e
forma, non il cambio. `dbops.lock_columns_conditional` ha righe solo per `catalogo.articoli`, e lo applica solo
`catalogo.fn_articolo_colonne_struttura`: una riga per i soggetti senza un guard sarebbe la stessa promessa senza
esecutore, come dice la segnalazione. La chiave d'unicità è `uq_soggetto_idstato_id_fiscale_univoco`
(`stato_id`, `id_fiscale_univoco_cf_piva`). Nessuna funzione aggiorna CF o P.IVA di un soggetto: lo scrittore è la
PATCH del backend.
Nodi per Tid: (1) l'errore di battitura su un CF valorizzato — come si corregge, se il campo è immutabile;
(2) il riempimento di un campo vuoto è ammesso (la lettura della sessione BE); (3) i numeri dei changeSet.

**Fuori dal DB:** la pagina auto-generata di `script.fn_e_obsoleto` va rigenerata (COMMENT del giro 9).

### 32.1 Le decisioni (Tid, 2026-11-09)

S-BE-2 come da proposta: `vivo` visibile nella vista standard, `attivo` resta fra le colonne selezionabili ma non
visibile di default. S-BE-3: (1) un CF o una P.IVA scritti li cambia solo il SUPER_ADMIN; (2) un campo vuoto si
riempie; (3) la forma proposta. La pagina di `script.fn_e_obsoleto` non era vecchia per sé: era il **COMMENT vivo**
che diceva ancora «Non è la regola dei processi», e la pagina generata lo ricopia.

Numeri: `20261110-95` … `-98`, occupati con file scheletro appena decisi (il `-85` di §31 era andato a `catalogo`).

### 32.2 Che cosa è scritto

| Dove | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261110-95` | La regola, in un posto: `anagrafiche.fn_id_fiscale_bloccato(valore)` (scritto e chi agisce non è SUPER_ADMIN: `script.fn_is_super_admin` su `app.current_user_id`, senza utente vale no) e `anagrafiche.fn_soggetto_id_fiscale_bloccato(soggetto, colonna)` (la stessa letta sulla riga, per il form) |
| `20_code/anagrafiche/20261110-96` | Il guard `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`, `trg_soggetti_a10_guard_id_fiscale_immutabile_upd` BEFORE UPDATE OF `codice_fiscale`, `partita_iva`; legge la regola sul valore OLD; rifiuto `E_SOGGETTO_ID_FISCALE_IMMUTABILE` con `campo` = la colonna |
| `80_data/changelog/20261110-97` | Le due righe di `dbops.lock_columns_conditional` per `anagrafiche.soggetti`, con la condizione `fn_soggetto_id_fiscale_bloccato`: il form spegne ciò che il guard rifiuta |
| `20_code/script/20261110-98` | Il COMMENT di `script.fn_e_obsoleto`: è anche la regola del ritiro dei processi; via l'elenco dei lettori per nome (era già incompleto) e il nome del brief |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_SOGGETTO_ID_FISCALE_IMMUTABILE`, `CONFLITTO_STATO` (come `E_CODICE_NON_MODIFICABILE`), messaggio id **1465** col segnaposto del dato |
| `ui/lista_colonna.csv`, `ui/lista_preset_colonna.csv` | S-BE-2: la colonna `vivo` (id **1168**, boolean, filtrabile, ordinabile) della lista 66; nel preset 66 `vivo` visibile (ordine 85), `attivo` non più visibile |
| `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` | Nuovo, 11 test (app, contesto operatore e un SUPER_ADMIN costruiti) |
| `db/pgtap/anagrafiche/test-billing-account-guard-cf-confrontabile-v1.sql` | La preparazione che svuota CF e P.IVA di due soggetti la fa un SUPER_ADMIN costruito, poi si torna all'operatore |

**Le prove** (scratch e dbdev, SQL estratto, dopo la riga `BEGIN;`, transazione annullata): il pgTAP nuovo 11/11 su
tutti e due. **La prova del rosso:** con il guard non montato i test 1-4, 6 e 11 sono rossi. Regressione «senza →
con» su 19 pgTAP vicini (soggetti, lock e form, liste, codici, riferimenti morti): stesso esito, salvo i due di sotto.
I rossi che restano uguali sono i test «come app» lanciati da owner, dichiarati nel loro nome. Guardrail verdi.

**Doc** (2026-11-09): pagine nuove `anagrafiche/manual/trgfn_soggetti_guard_id_fiscale_immutabile.md` e
`anagrafiche/manual/fn_id_fiscale_bloccato.md`; riallineate `soggetti.md` (anche la definizione di
`id_fiscale_univoco_cf_piva`, che diceva `COALESCE` e non l'unione dei due), `trgfn_soggetti_guard_cf_piva_obbligatori.md`,
`dbops/manual/lock_columns_conditional.md`, `dbops/manual/fn_non_editable_fields.md`. Nessuna pagina manual descrive le
colonne della lista dei processi né ripeteva il falso di `fn_e_obsoleto`. Restano in `soggetti.md`, da guardare in un
giro di doc: due frasi su `tipo_soggetto` (rimosso) e il link `/dbzero/config/tipi_soggetto_dettaglio` senza `/tabelle/`.

### 32.3 N4: la ditta individuale che diventa privato — ✅ deciso (Tid, 2026-11-09: strada a)

`anagrafiche/test-soggetti-sesso-policy-v1`, test 15: una ditta individuale passa a privato **togliendo la P.IVA**
(`tipo_soggetto_dettaglio_id` → PR, `partita_iva = NULL`). Con la regola nuova l'operatore non può svuotare la
P.IVA, quindi il passaggio lo fa solo il SUPER_ADMIN, e il test riceve `E_SOGGETTO_ID_FISCALE_IMMUTABILE` invece del
rifiuto sul sesso che vuole provare.
* (a) il passaggio resta al SUPER_ADMIN (coerente con la decisione: la P.IVA esce dalla chiave d'unicità); il test
  15 fa il passo da SUPER_ADMIN e continua a provare il sesso. **Scelta da Tid.** Fatto: il SUPER_ADMIN nasce con
  le fixture (crearlo a metà file fa scattare il controllo differito degli indirizzi), il test 15 gira nel suo
  contesto e poi si torna all'operatore; 20/20 su scratch e dbdev, senza e con.
* (b) svuotare la P.IVA è ammesso quando la natura nuova non la prevede (cessazione dell'attività): un'eccezione
  dentro la regola, che va letta anche dal form.

### 32.4 Per Tid e per il team BE

1. **Apply** di `20261110-95` … `-98` e dei CSV (codici, `lista_colonna`, `lista_preset_colonna`).
2. **pgTAP:** `anagrafiche/test-soggetti-id-fiscale-immutabile-v1`, `anagrafiche/test-billing-account-guard-cf-confrontabile-v1`,
   `anagrafiche/test-soggetti-sesso-policy-v1`, `dbops/test-fn-non-editable-fields-conditional`,
   `dbops/test-non-editable-fields-dal-lock-vivo-v1`, `ui/test-fn-resolve-lista-config`, `script/test-catalogo-messaggi-errore-completo`.
3. **Team BE, dopo l'apply:** S-BE-2, `"vivo": _SQL_VIVO` in `PROCESSI_SORT_COLUMNS` e la cella (fino ad allora
   `test_liste_configurabili_seed` vede la colonna nel seed e non nel backend); S-BE-3, via il gap di CF e P.IVA,
   `record_id` al BB, il codice `E_SOGGETTO_ID_FISCALE_IMMUTABILE` sul campo nella PATCH e nelle politiche (BE6).

## 33. Giro 13 — il livello «sessione» esce dagli override (Q10), 2026-11-09

**Via di Tid (2026-11-09):** «puoi fare altro intanto, inizia dal 20261114», poi corretto: «volevo scrivere 20261111-14». Q10 era già deciso (§4): il livello esce
dal modello, da tutte e due le catene. Numeri `20261111-14` … `-17`, occupati appena scelti.

### 33.1 Il censimento (scratch e dbdev)

* Leggono il livello: `script.fn_get_parameter_full` (il parametro `p_session_key` e il livello 5),
  `script.fn_get_parameter_di_sessione` (la GUC `app.session_key`, che nessuno scrive). Chiamano la cascata con la
  firma intera: `script.fn_list_parameters_for_user` (7 argomenti posizionali) e il backend (§33.4).
* La colonna `config.parameter_overrides.session_key` sta in due vincoli: `uq_overrides_full_scope_v5` e
  `chk_parameter_overrides_un_ambito`. ⚠️ `DROP COLUMN` cancella in silenzio i vincoli che la nominano: l'unicità
  sparirebbe per intero, quindi si ricreano a mano.
* Fatto datato: nessuna riga con `session_key` su tutti e due i database. `storico.parameter_overrides` non ha la
  colonna. Nessuna vista e nessun trigger la legge.
* `80_data/sql/config/parameter_overrides.csv`: un CSV orfano (solo l'intestazione, con `tenant_id` e
  `session_key`, che non esistono più; nessun changeSet lo carica). Cancellato.

### 33.2 Che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/script/20261111-14` | `fn_get_parameter_full` senza `p_session_key`: DROP + CREATE (cambia l'identità), cascata a sei livelli, firma e risultato a `%TYPE`, una firma sola; GRANT all'app ripetuto; COMMENT |
| `20_code/script/20261111-15` | `fn_get_parameter_di_sessione`: non legge `app.session_key`, chiama la cascata **per nome**; COMMENT |
| `20_code/script/20261111-16` | `fn_list_parameters_for_user`: chiama la cascata per nome; COMMENT (vincolo v6, via marcatori e brief) |
| `00_schema/config/20261111-17` | Le righe di sessione si contano (con una sola si ferma); via i due vincoli, via la colonna; `uq_overrides_full_scope_v6` (NULLS NOT DISTINCT, cinque dimensioni) e `chk_parameter_overrides_un_ambito` (stesso nome, cinque dimensioni) ricreati; COMMENT dei vincoli e della tabella (diceva «tenant, user, sessione, funzione») |

**Le scelte (da guardare, Tid):**
1. **Il nome del vincolo cambia versione** (`_v5` → `_v6`), come le volte prima, perché cambia la definizione. Lo
   nominano l'upsert del backend (`ON CONFLICT ON CONSTRAINT`) e tre pgTAP: questi sono aggiornati, il backend va
   con BE8.
2. **Il parametro tolto stava in mezzo** alla firma: un chiamante a 7 argomenti posizionali fallisce subito («la
   funzione non esiste»), non legge in silenzio un valore sbagliato. I chiamanti del DB ora passano per nome.

**pgTAP aggiornati:** `config/test-fn-get-parameter-full-categoria-cliente-v1` (test 4: emittente su funzione; test
5: né la colonna né il parametro esistono più), `config/test-parameter-overrides-categoria-cliente-v1` (v6 presente,
v3-v5 rimossi), `script/test-fn-list-parameters-for-user` (test 18 per nome), e l'upsert su v6 in
`config/test-parameters-emittente-defaults-cascade`, `-uom-defaults-cascade-v1`, `-vendite-limiti-prezzi`.

### 33.3 Le prove

SQL estratto dagli YAML, dopo la riga `BEGIN;`, transazione annullata, scratch e dbdev.
* **Con il giro, nessun rosso del giro** su: `config/test-fn-get-parameter-full-categoria-cliente-v1` (9),
  `config/test-parameter-overrides-categoria-cliente-v1` (15), `script/test-fn-list-parameters-for-user` (18),
  `script/test-fn-get-parameter-di-sessione-v1` (15), `script/test-fn-get-parameter-full-emittente` (9, il test 1
  sulla firma viva a sei argomenti), `config/test-parameters-emittente-defaults-cascade`, `-vendite-limiti-prezzi`,
  `config/test-parameter-overrides-fk-surrogate-dispatch-v1`, `config/test-parameters-ammette-override-v1`,
  `config/test-parameters-tipo-valore-v1`, `dbops/test-vw-parameter-fk-surrogate-dangling-v1`,
  `vendite/test-listini-in-scadenza-senza-successore-v1`, `config/test-fk-auth-user-ponte-django-v1`,
  `dbops/test-nessun-timestamp-senza-fuso-v1`, `dbops/test-riferimenti-morti-v1`.
* **La prova del rosso:** i pgTAP aggiornati, senza il giro, sono rossi sul modello vecchio (la firma, il vincolo
  v6, la colonna).
* Rossi che non sono del giro: `config/test-elimina-credenziale-v1` 18 (come app, lanciato da owner: uguale senza);
  `config/test-parameters-uom-defaults-cascade-v1` 3 e 8: il file è già modificato dal cantiere `catalogo` per il
  suo giro 2 (`20261111-13`, il ritiro di `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE`), non ancora applicato; la versione
  committata è verde. ⚠️ Nello stesso file c'è la riga `v6` di questo giro: al commit le due modifiche convivono.
* Sullo scratch due corse sono morte su un deadlock con un'altra sessione (l'`ALTER TABLE` dell'innesto);
  rilanciate a scratch libero, verdi.
* Guardrail verdi.

**Numeri, correzione del 2026-11-09:** Tid aveva scritto «20261114» per «20261111-14»; i quattro changeSet sono
rinumerati `20261111-14` … `-17` (file, `logicalFilePath`, `id`, rimandi), e la data nei testi è la vera, 2026-11-09.

**Doc** (2026-11-09): riallineate `script/manual/fn_get_parameter_full.md` (la sezione degli overload diventa la
firma unica), `fn_get_parameter_di_sessione.md`, `fn_list_parameters_for_user.md`, `config/manual/parameter_overrides.md`,
`parameters.md` (anche due esempi col vecchio modello `tenant_id` / `scope_type`), `vendite/manual/fn_get_limite_emissione_default.md`
e la guida `configurazione-e-gestione-parametri.md` (cascata a sei livelli, «non esiste un override di sessione»).
Restano in `parameters.md`, da guardare in un giro di doc: «tenant» alle righe ~102 e ~196 (vecchio modello, non la
sessione).

### 33.4 BE8 — il percorso intero (elenco chiuso, 2026-11-09)

Dopo l'apply il backend chiama una firma che non esiste più e un vincolo che ha cambiato nome:
1. `backend/apps/core/db/parameter_repository.py`
   * `_SQL_RESOLVE` e `_SQL_RESOLVE_SE_DICHIARATO`: da 7 a 6 segnaposto, senza il `%s::text` della sessione
     (ordine: codice, emittente, utente, gruppi, funzione, categoria);
   * `get_parameter` e `get_parameter_se_dichiarato`: via il kwarg `session_key` e dalle liste dei parametri;
   * `_DIMENSIONI_OVERRIDE`: via `"session_key"`;
   * l'upsert (`ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5`, riga ~298) → `_v6`;
   * i commenti delle righe ~39, ~90, ~121, ~265 (cascata a sei livelli, vincolo v6).
2. `backend/apps/core/tests/services/test_parameter_repository_dimensioni.py:66` (l'asserzione sul nome v5) e il
   commento della riga 7; `backend/apps/core/tests/db/test_parameter_overrides_db.py:14` (commento).
3. `docs/it/dev/backend/catalogo-building-block-backend.md:360`: la cascata a sei livelli.
Nessun chiamante passa `session_key=` oggi; `ai_assistant/services/tool_registry.py:160` chiama con un argomento
solo e non cambia.

### 33.5 Per Tid

1. **Apply** di `20261111-14` … `-17` su dbdev e scratch (e la cancellazione del CSV orfano).
2. **pgTAP:** quelli di §33.2, più `script/test-fn-get-parameter-di-sessione-v1`, `script/test-fn-get-parameter-full-emittente`,
   `vendite/test-listini-in-scadenza-senza-successore-v1`, `dbops/test-riferimenti-morti-v1`.
3. **Team BE:** BE8 (§33.4), subito dopo l'apply: fino ad allora la lettura dei parametri dal backend fallisce.

### 33.6 Applicato (Tid, 2026-11-09)

S-BE-2, S-BE-3 (`20261110-95` … `-98`, i CSV dei codici e della lista) e il giro 13 (`20261111-14` … `-17`, il CSV
orfano tolto) applicati da Tid su dbdev e scratch; pgTAP di §32.4 e §33.5 verdi. Restano il commit e, al team BE,
BE8 (§33.4), S-BE-2 e S-BE-3 lato BE (§32.4 punto 3) e BE6 dei due codici nuovi. Il giro 13 si chiude col commit;
poi il giro 14 (§8), al via di Tid.

### 33.7 Il giro BE (team BE, 2026-11-09, `2af6d986f5`, PR #81)

| # | Che cosa |
| --- | --- |
| BE8 | `parameter_repository.py`: `_SQL_RESOLVE` e `_SQL_RESOLVE_SE_DICHIARATO` a sei segnaposto, via `session_key` da `get_parameter`, `get_parameter_se_dichiarato` e `_DIMENSIONI_OVERRIDE`, l'upsert su `uq_overrides_full_scope_v6`, i commenti (cascata a sei livelli). I due test del §33.4 e il catalogo BB backend. Fra l'apply e questo giro la lettura dei parametri dal backend falliva: dopo il giro, i worker di sviluppo ricaricati (HUP) |
| S-BE-2 | `"vivo": _SQL_VIVO` in `PROCESSI_SORT_COLUMNS` (l'espressione sale sopra la whitelist, una sola sede); la cella col tag «Vivo / Ritirato» in `ProcessiAutomaticiTab.vue`, due chiavi i18n |
| S-BE-3 | Il gap di CF e P.IVA è uscito da `soggetti_service._compute_non_editable_fields`: la lista viene tutta dal DB, letta sul record (`compute_non_editable_fields(..., record_id=...)`). Il gap di prima bloccava anche il SUPER_ADMIN, a cui il DB lascia la correzione. La PATCH non ha bisogno di una traduzione: il rifiuto del guard porta il campo e passa intatto (`update_with_dedup` traduce solo le `IntegrityError`) |
| BE6 | `E_SOGGETTO_ID_FISCALE_IMMUTABILE` in policy (rigenerata insieme ai codici del giro 2 di `catalogo`: le sole sette voci dei due giri, nessun codice del DB oltre git) e il suo ripiego senza `%s` |

**Le prove.** Sul DB vero: `core/tests/db/test_parameter_overrides_db` (la firma a sei e l'upsert su v6, invariati e verdi),
`core/tests/db/test_processi_filtro_vivo_db` (nuovo test: l'ordinamento per `vivo`),
`anagrafiche/tests/db/test_soggetti_id_fiscale_immutabile_db` (nuovo, 3 test: da operatore costruito CF/P.IVA scritti
sono nella lista; da SUPER_ADMIN costruito no; la PATCH che cambia un dato scritto con uno valido e libero riceve il codice
col campo). ⚠️ I due ruoli si costruiscono (`dbops.fn_pgtap_crea_operatore_umano`): l'helper `apri_contesto_operatore` sceglie
un `is_superuser`, che può essere anche SUPER_ADMIN, e il test sarebbe passato a vuoto.
`core/tests/db/test_lock_columns_vivo_db`: il soggetto passa al ramo per record. `test_liste_configurabili_seed` verde.

## 34. Giro 14 — i COMMENT rimasti e il presidio di testo: censimento (2026-11-09)

Censimento in sola lettura su dbdev, dopo l'apply del giro 13 e il commit `aaa12df0ef`. Il metro è
`linee-guida-sql.md` §5d. I numeri sono fatti datati (dbdev, 2026-11-09), non argomenti: servono a sapere che cosa
c'è da riscrivere, non a decidere il perimetro.

### 34.1 Le marche vietate nei COMMENT, per schema

Ricerca meccanica su `pg_description` (ogni oggetto: tabella, colonna, vista, funzione, procedura, trigger, vincolo,
indice). Marche: nome o percorso di brief, marcatore di revisione (`rev …`, `⭐`), id di changeSet, hash di commit,
data, sigla di cantiere (`§n`, `D-n`, `Qn`, «di Tid»), misura («n su m»). Le ultime tre danno falsi positivi: si
rileggono a mano.

| Schema | COMMENT | con almeno una marca | di cui con un brief |
| --- | ---: | ---: | ---: |
| vendite | 1720 | 575 | 480 |
| script | 397 | 302 | 248 |
| storico | 554 | 236 | 236 |
| config | 1004 | 215 | 156 |
| anagrafiche | 632 | 159 | 130 |
| **dbops** | 582 | **144** | 111 |
| pagamenti | 197 | 62 | 26 |
| magazzino | 203 | 39 | 31 |
| catalogo | 150 | 29 | 25 |
| documenti | 74 | 28 | 24 |
| ui | 77 | 23 | 21 |
| pratiche | 277 | 23 | 8 |
| **maintenance** | 37 | **12** | 10 |
| acquisti | 158 | 6 | 5 |
| shop | 20 | 0 | 0 |

* **`storico` non è debito a sé.** Le 236 righe sono **due** testi, ripetuti sulle 118 shadow: i COMMENT delle colonne
  `origine_schema` e `scope_emittente_fiscale_id` («Brief: brief-db-rls-storico-scope-congelato §4b (D1/D2)», più una
  data nel secondo). Li scrive il generatore `dbops.fn_storico_arma_scope`: si correggono **lì**, e si riemettono
  sulle shadow esistenti.
* **Il perimetro di questo brief** è `dbops` + `maintenance` + il generatore di `storico`: 156 oggetti più i due testi
  generati. L'elenco, oggetto per oggetto con le marche trovate, è nello scratchpad della sessione (`marche.tsv`); va
  nel changeSet, non qui.
* **Fuori perimetro**, gli altri schemi: circa 1.700 COMMENT. La §5d dice che quel debito si riscrive per famiglia,
  quando un lavoro riapre gli oggetti, non con una riscrittura di massa. Da qui il nodo N1.

### 34.2 Gli oggetti senza COMMENT (§3.2)

Restano: `dbops.audit_log`, `dbops.fn_list_indices`, `dbops.fn_schema_in_scope`, `dbops.fn_schema_match`,
`dbops.fn_table_in_scope`, `maintenance.job_run_log`. Gli altri di §3.2 sono stati scritti o ritirati nei giri.
In più `maintenance.test_pgagent_log`: residuo del bootstrap dell'albero v1 (congelato, §11.11), nessuno la scrive né la
legge, il pgTAP `maintenance/test-app-postura-job-run-log-v1` (test 11) presidia che l'app non ci abbia privilegi. Nodo N4.

### 34.3 Le M di §3.1, riverificate sul testo di oggi

**Chiuse dai giri** (frase falsa non più presente): M3, M7 (corpo, già nel giro 2), M10, M12 (oggetto
ritirato), M13, M14, M15, M16, M18, M22 (COMMENT e `presidi.csv`), M23 (COMMENT; resta la marca), M24 (vista
ritirata), M28 (COMMENT della funzione, `coda_lavori_tipi.csv`, pgTAP), M29 (`fn_sessione_del_migratore`,
`sessioni_utente`), M30, M31 (`fn_get_lookup_codici`; `trgfn_child_requires_non_obsolete_parent` ritirata), M33
(`fn_find_function_usage`), M34 (`fn_apply_delete_block_trigger`, `fn_seed_automazione_guard_utility_tipo_ruolo`,
`trgfn_cleanup_at_alla_nascita`, `fn_trigger_exists_*_by_args`; `fn_cleanup_at_params` e `fn_seed_automazione_overlap`
ritirate), M36 (`_cliente_ba_del_mondo`, `_crea_mondo_cliente`, `_crea_fattura`, `_crea_ordine`,
`_crea_commessa_attivita`), M39 (`fn_crea_utente_tecnico`), M9, M21, M35 (`codici_errore.csv`), M37
(`test-cleanup-framework`, il file dello scope congelato non c'è più).

**Ancora aperte:**

| # | Dove | Che cosa resta |
| --- | --- | --- |
| M1 | COMMENT `dbops.automation_scope` | «Scope opzionale per rollout filtrato» |
| M2 | COMMENT `dbops.storico_scope_policy` | «Cinque modi»: il CHECK ne ammette sei, manca `COPPIA`; più «Brief: …» |
| M4 | COMMENT `dbops.fn_grant_storico_shadows` | test 19 e ruolo batch ritirati, «audit SKIP», l'eredità del proprietario, una misura datata |
| M5 | COMMENT `dbops.fn_run_automations_storico_provision` | apici raddoppiati, «creare/aggiornare», `MANUAL` |
| M6 | COMMENT `dbops.fn_storico_backfill_scope` | «il pgTAP le conta come debito» |
| M8 | COMMENT `dbops.audit_sources.storico_table` | «NON esposto dalla vista pubblica» |
| M11 | COMMENT `dbops.trgfn_tx_id_managed` | «assegna script.uuid_nil()» nel ramo dell'id non registrato |
| M17 | COMMENT `dbops.vw_processi_programmazione_da_guardare` | «12 righe OK al 2026-09-06», «rev 2026-09-07», la cronaca dei sei mesi, «R-12» |
| M20 | `presidi.csv` righe di `vw_riferimenti_morti_da_sanare` (CHECK-KO → REALE, «779 su 780»), `vw_bersagli_non_dichiarati` («ci-validate.yaml»), `vw_codici_errore_forme_condizione` (cronaca «fino al 2026-11-07») | nota stantia o cronaca |
| M25 | COMMENT `dbops.fn_guardiano_digest` | «Finche' NOTIFICA_DIGEST_MUTO e' attivo = false» |
| M26 | COMMENT `dbops.fn_conta_presidio_per_variante`; `codici_errore.csv` (`E_PRESIDIO_NON_A_CATALOGO`) | «per la stessa ragione di fn_conta_presidio» (INVOKER); il codice lo solleva `fn_conta_presidio_per_variante` |
| M27 | COMMENT `dbops.fn_check_funzioni_riferimenti_morti` | «solo il test 7» |
| M28 | COMMENT tabella `dbops.automazione_chiusura_scadenze` | «chiamata dal job notturno chiusura_scadenze_daily» |
| M29 | COMMENT `dbops.fn_idempotency_prenota` | «la prenotazione committa da sola» |
| M31 | `messaggi_errore.csv` (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`) | nomina il guard ritirato, `CURRENT_DATE` e un brief |
| M32 | COMMENT `dbops.vw_emittenti_regime_non_confermato` | «o di un cambio senza conferma», «(D-1)» |
| M33 | COMMENT `dbops.fn_get_override_col`, `dbops.fn_get_child_fk_col` | `dbops._col_exists`; «di fatto STABLE» |
| M34 | COMMENT `dbops.lock_columns_conditional`, `dbops.automation_delete_block`, `dbops.automazione_overlap`, `dbops.automazione_attivo_eccezioni` | «colonne immutabili» e «rev 2026-05-22»; «tabelle sensibili (ruoli)»; manca `range_col` (da rileggere sulla forma jsonb del 10c-4); «Prima riga il 2026-09-25» e un brief |
| M35 | `automation_rules_tbl.csv` (regola `CLEANUP_AT` di `vendite.event_log`) | «il trigger a10 all'INSERT» |
| M36 | COMMENT `_cliente_del_builder` («cinque builder»), `_crea_commessa` e `_crea_contratto` (il cliente da `_crea_mondo_cliente`), `_crea_operatore_umano` («lo stesso UPDATE»), `_piva_libera()`, `_porta_a_stato` («testate senza la porta») | da riscrivere sul corpo di oggi |
| M37 | intestazioni di `test-fn-pgtap-crea-fattura-v1` («quattro anelli»), `test-audit-sources-seed` («3 colonne»), `test-fn-pgtap-crea-preventivo-v1`, `test-automazione-attivo-eccezioni-v1` | da rileggere |
| M19 | `db/pgtap/anagrafiche/test-identita-tecnica.sql:28-30` | «nei DUE sensi» |
| M38 | `scripts/sql/provision_storico_scope.sql:6` | rimanda a `work-in-progress/` |
| M39 | COMMENT `script.fn_check_versione_listino_attivabile` | due motivi; il corpo ne ha tre (`E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA`) |
| §3.3 | `dbops.fn_provisiona_dati_di_sviluppo` (§14), `trgfn_prevent_deactivate_if_children` | chiusi: la prima non ha più COMMENT da correggere, la seconda non ha più la misura |

Le aperte di §3.1 cadono quasi tutte su oggetti che portano anche le marche di §34.1: si riscrivono nella stessa
riga.

### 34.4 I nodi

* **N1 — il perimetro del presidio di testo.** Acceso su tutto il database sarebbe rosso per ~1.700 COMMENT di altri
  schemi, che la §5d lascia alla riscrittura per famiglia. Proposta: **due presidi**. (a) Un pgTAP su
  `obj_description` per `dbops`, `maintenance` e le colonne generate di `storico`: verde dopo questo giro, e da lì
  nessuna marca nuova nel perimetro. (b) Un **guardrail sui changeSet aggiunti** (come `check_license.py` sui file
  nuovi): un `COMMENT ON` in un file nuovo non contiene brief, marcatore di revisione, id di changeSet né hash. Ferma il
  debito nuovo in tutto il database senza un registro di 1.700 righe; il vecchio si riscrive quando la famiglia si
  riapre. Alternativa scartata: un registro del debito per oggetto (andrebbe tenuto a mano a ogni riscrittura).
* **N2 — che cosa controlla il presidio.** Solo le marche meccaniche e senza falsi positivi: brief, marcatore di
  revisione, id di changeSet, hash. Le date, le sigle e le misure si leggono a mano in questo giro, ma non entrano
  nel presidio: «D-1» e una data possono stare in una frase lecita, e un presidio che sbaglia insegna a ignorarlo.
* **N3 — le shadow di `storico`.** Si corregge il testo nel generatore `dbops.fn_storico_arma_scope` e lo stesso
  changeSet riemette i due COMMENT sulle shadow esistenti (un ciclo sulle shadow armate), senza riarmarle.
* **N4 — `maintenance.test_pgagent_log`.** Proposta: si ritira con un `DROP` in v2 (l'albero v1 non si tocca, la
  ricrea, il changeSet v2 la toglie), e il test 11 del pgTAP di postura diventa «la tabella non c'è». In alternativa
  un COMMENT che dica che cos'è.
* **N5 — la forma dei changeSet** (come detto in sessione): un changeSet di COMMENT per schema (`dbops`, `maintenance`,
  `script` per M39; il generatore di `storico` col suo changeSet), il presidio pgTAP e il guardrail per ultimi; i
  CSV (`presidi.csv`, `codici_errore.csv`, `messaggi_errore.csv`, `automation_rules_tbl.csv`) e le intestazioni dei
  file (M19, M37, M38) fuori dai changeSet. Stima: sei o sette changeSet.

### 34.5 Le decisioni di Tid (2026-11-09)

N1-N5 come da proposta. Numeri dal primo libero: `20261111-18` … `-24` per questo giro; **le altre sessioni dal
`20261111-25`**.

| changeSet | Che cosa |
| --- | --- |
| `-18` | `dbops`: COMMENT di tabelle, colonne, viste, vincoli e indici |
| `-19` | `dbops`: COMMENT di funzioni e procedure (fixture comprese) |
| `-20` | `maintenance`: COMMENT, `job_run_log` compresa |
| `-21` | `script`: il COMMENT di `fn_check_versione_listino_attivabile` (M39) |
| `-22` | `storico`: il generatore `dbops.fn_storico_arma_scope` e i due COMMENT riemessi sulle shadow (N3) |
| `-23` | `maintenance.test_pgagent_log` ritirata (N4) |
| `-24` | riserva |

Fuori dai changeSet: i CSV, le intestazioni di M19, M37, M38, il pgTAP del presidio e il guardrail sui changeSet
aggiunti (N1).

### 34.6 Scritto e provato (2026-11-09)

#### 34.6.1 I changeSet

| changeSet | Che cosa | Istruzioni |
| --- | --- | --- |
| `20_code/dbops/20261111-18` | COMMENT di tabelle, colonne, viste, vincoli, indici di `dbops`; nuovi `audit_log` e le due colonne di `automation_scope` | 108 |
| `20_code/dbops/20261111-19` | COMMENT di funzioni e procedure di `dbops`, fixture comprese; nuove le quattro funzioni di ambito (§3.2) | 55 |
| `20_code/maintenance/20261111-20` | COMMENT di `maintenance`; nuova `job_run_log` | 13 |
| `20_code/script/20261111-21` | `fn_check_versione_listino_attivabile`: i tre motivi (M39) | 1 |
| `20_code/dbops/20261111-22` | `fn_storico_arma_scope`: i due testi in una sede, e convergono su ogni shadow (N3) | 1 funzione |
| `00_schema/maintenance/20261111-23` | `DROP TABLE IF EXISTS maintenance.test_pgagent_log` (N4) | 1 |
| `20_code/dbops/20261111-24` | COMMENT di `fn_generate_tx_id` e `fn_sync_functions_owner`, di `postgres`, con la proprieta' in prestito | 2 |

Nei changeSet di soli COMMENT il rollback rimette i testi di oggi, letti da dbdev (`IS NULL` dove mancava); nel `-24`
no, per non rifare il prestito (stesso criterio di `20260929-09`).

#### 34.6.2 Fuori dai changeSet

* **Presidio pgTAP** `dbops/test-comment-al-presente-v1` (5 test, nuovo): le quattro marche su `dbops`, `maintenance` e le
  due colonne generate di `storico` (N1-a, N2).
* **Guardrail** `scripts/guardrail_comment_al_presente.py` (nuovo), passo in `ci-validate.yaml` prima dei letterali SQL:
  le quattro marche nei `COMMENT ON … IS '…'` dei changeSet dal `20261111-18`, solo `changes` (N1-b). Al 2026-11-09 guarda
  dodici changelog, cinque dell'altra sessione (`-25` … `-29`): nessuna marca.
* **CSV:** `presidi.csv` (M20: tre righe), `codici_errore.csv` (M26), `messaggi_errore.csv` (M31: la causa diceva
  `CURRENT_DATE` e nominava un brief), `automation_rules_tbl.csv` (M35: il trigger m50, non a10). ⚠️ `codici_errore.csv` e
  `messaggi_errore.csv` li sta cambiando anche la sessione `catalogo` (codici `E_BOM_*`): una riga mia per file.
* **Intestazioni:** M19 (`anagrafiche/test-identita-tecnica`: tre versi), M37 (`test-fn-pgtap-crea-fattura-v1`,
  `test-audit-sources-seed`, `test-fn-pgtap-crea-preventivo-v1`, `storico/test-storico-scope-congelato-v1`), M38
  (`scripts/sql/provision_storico_scope.sql`).
* **pgTAP cambiati nel merito:** `maintenance/test-app-postura-job-run-log-v1` test 11 (`hasnt_table`, N4);
  `dbops/test-automazione-attivo-eccezioni-v1` test 9 nuovo (M37: ogni riga del registro, non solo la prima, plan 9).
* **Debito del giro 12 chiuso:** `dbops/test-presidi-codici-corpo-leggibile-v1` non aveva `SET CONSTRAINTS ALL IMMEDIATE`
  (il guardrail del preambolo lo segnalava); ora il preambolo e' verde su tutti i file.
* **Doc:** `linee-guida-sql.md` §5d (i due presidi), `dbops/manual/fn_storico_arma_scope.md` (la convergenza dei
  commenti); `maintenance/manual/test_pgagent_log.md` cancellata (oggetto ritirato).

#### 34.6.3 Le scelte che non si vedono dal titolo (da guardare, Tid)

1. **`-22`, la convergenza dei commenti.** Il generatore scriveva i due COMMENT solo quando aggiungeva la colonna: un testo
   corretto non sarebbe mai arrivato alle 118 shadow gia' armate. Ora un passo 2c li riporta al testo quando sono diversi.
   Le shadow si allineano al migrate stesso, perche' `90_end/20260911-29` (runAlways) chiama `fn_storico_arma_scope_tutte`:
   alla prima passata 118 «ALLINEATA» e 118 righe `OK` in `dbops.audit_log`, alla seconda nessuna. L'alternativa (un blocco
   che riscrive i COMMENT sulle shadow) avrebbe ricopiato il testo in un secondo posto.
2. **`-24`, il prestito per due COMMENT.** E' il meccanismo di casa (`20260807-19`, `20260929-09`), pesante per un testo.
   L'alternativa era lasciare le due funzioni fuori dal presidio con un'eccezione per nome.
3. **Il guardrail vale per tutte le sessioni dal `20261111-18`**: anche per i changeSet di `catalogo` da qui in poi.
4. **Le frasi false trovate rileggendo**, oltre le M (dettaglio nelle testate dei changeSet): `vw_processi_che_bypassano`
   («pgAgent bypassa perche' e' superuser»: `zeroerp_job` non lo e'); `vw_af_senza_giro` («deve restare vuota», ma il
   catalogo la dice LAVORAZIONE); `vw_codici_errore_forme_condizione` («non e' un cancello», ma il catalogo la dice
   CANCELLO); i quattro flag di accensione di `processi` («NULL per CODA e ritirati»: solo CODA); `fn_get_override_col`
   (i ruoli `AUDIT_TS`/`AUDIT_USER` non esistono); `fn_pgtap_cliente_del_builder` (sei builder, non cinque).

#### 34.6.4 Correzioni al censimento di §34.3

* **M31:** `trgfn_child_requires_non_obsolete_parent` non e' ritirata: sta in `dbops`, non in `script` (cercata nello schema
  sbagliato). Il suo COMMENT era gia' giusto; restava la causa in `messaggi_errore.csv`, corretta.
* **M37:** il pgTAP dello scope congelato c'e', in `db/pgtap/storico/`; la frase su `titodb` e il SET ROLE era stantia,
  corretta.

#### 34.6.5 La prova, e che cosa resta a Tid

* **Prova** su dbdev, SQL estratto dai sette changeSet nell'ordine del migrate, in transazione annullata come
  `zeroerp_owner`, piu' la convergenza di `90_end/20260911-29`: tutto passa; il presidio nuovo 5/5. Con e senza l'estratto,
  stesse risposte per `test-builder-pgtap-vincoli-immediate-v1`, `test-vw-processi-programmazione-da-guardare`,
  `test-storico-scope-proprietario-membership-v1`, `storico/test-storico-scope-congelato-v1`,
  `test-storico-scope-policy-v1`, `test-sec-functions-owner-migratore-passa-v1`, `test-security-definer-search-path-v1`
  (tutti verdi) e `test-sec-functions-owner-riservato-v1` (5 rossi da owner, test «come app», uguali senza).
  `maintenance/test-app-postura-job-run-log-v1`: l'11 verde con l'estratto; il 9 e' rosso da owner anche senza (verde come
  app). Il `-24` da solo: proprietari tornati a `postgres`, copia di servizio sparita, nessuna riga temporanea.
* **Guardrail** verdi: `comment_al_presente`, `sql_letterali`, `run_on_change`, `timestamp_senza_fuso`,
  `precondition_seed` (ha preso una preCondition del `-24` sul registro, che da zero arriva da `80_data`: tolta),
  `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `v1_congelato`, `pgtap_preambolo`.
* **Non provato:** il migrate vero (pgjdbc), il caricamento dei CSV, la corsa come app, la CI da zero (dove le due funzioni
  di `postgres` sono ancora del migratore: il `-24` lo regge come il `20260929-09`).
* **Per Tid:**
  1. apply di `20261111-18` … `-24` e dei quattro CSV su dbdev e scratch;
  2. pgTAP: `dbops/test-comment-al-presente-v1` (nuovo), `maintenance/test-app-postura-job-run-log-v1`,
     `dbops/test-automazione-attivo-eccezioni-v1`, `dbops/test-presidi-codici-corpo-leggibile-v1`, quelli dello storico e
     del registro dei proprietari elencati sopra, `dbops/test-catalogo-presidi-v1` (il CSV dei presidi);
  3. la doc auto-generata dopo l'apply.
* **Ricadute BE:** nessuna. Cambiano testi che il pannello dei presidi mostra (`obj_description`), non colonne ne' codici.

#### 34.6.6 Applicato (2026-11-10)

* **Apply** di `20261111-18` … `-24` e dei quattro CSV su dbdev e scratch (Tid), **pgTAP di §34.6.5 verdi**. Le scelte di
  §34.6.3 restano come sono state scritte.
* **Doc auto-generata e commit:** Tid, `fe388dbfdf` (2026-11-10). Giro 14 chiuso.

#### 34.6.7 Correzione: il `-18` da zero (2026-11-11)

* **Il guasto.** Su un database ricostruito da zero il migrate si ferma sul `20261111-18`: «constraint
  `chk_presidi_chi_agisce_se_allarma` for table `presidi` does not exist». Il vincolo nasce in `90_end` (`20261006-07`,
  dopo il mirror del CSV dei presidi), e `20_code` gira prima. Su dbdev e scratch non si vedeva: il vincolo c'era gia'.
  L'intestazione del `-18` diceva «nessuno degli oggetti nasce dopo 20_code», e per questo oggetto era falso.
* **Censimento:** dei 108 bersagli dei COMMENT del `-18`, questo e' l'**unico** che nasce in `80_data` o in `90_end`.
* **Correzione:**
  * dal `-18` esce il COMMENT sul vincolo, in `changes` e in `rollback`; il changeSet prende `validCheckSums: ANY`,
    perche' dove e' gia' girato il checksum e' quello del testo di prima (`runOnChange: false`: non ri-esegue);
  * nuovo `90_end/20261111-66-update-comment-chk-presidi-chi-agisce-se-allarma`: lo stesso testo al presente, con
    preCondition HALT sull'esistenza del vincolo. Su dbdev e scratch riscrive il testo che c'e' gia'.
* **Provato:** l'SQL estratto del `-18` (change e rollback) e del `-66` su dbdev, in ROLLBACK, senza errori. **Non provato:**
  il migrate da zero, che e' il caso del guasto.
* **Per Tid:** rilanciare il migrate (da zero dove si era fermato, l'update su dbdev e scratch).
* **Lezione:** «nessun oggetto nasce dopo 20_code» si verifica, non si scrive: un COMMENT, come un DROP, va cercato anche
  nei changeSet di `80_data` e `90_end`.
* **Secondo guasto, stesso caso (2026-11-11):** rilanciato da zero, il migrate si ferma sul `20261111-20`: «constraint
  `chk_job_run_log_processo_dichiarato` for table `job_run_log` does not exist». Il vincolo nasce in
  `90_end/20260905-16`. La prima volta avevo censito solo il `-18`, non tutto il giro: errore mio.
  * **Censimento esteso**, ora su tutti i changeSet di questa revisione dal `20261111-18` (`-18` … `-24`, `-40` … `-46`,
    `-67`): ogni bersaglio di COMMENT cercato fra le creazioni di `70_dati_sistema`, `80_data`, `85_pgagent` e `90_end`.
    Resta **solo** questo. Il censimento riconosce anche il caso del `-18`, quindi trova quello che cerca. Il `-23`
    (DROP di `maintenance.test_pgagent_log`) non ha lettori nelle fasi successive. Il `-24` scrive in
    `dbops.sec_functions_owner` prima del CSV, ma e' scritto per reggere da zero (lo dice la sua intestazione).
  * **Correzione**, come per il `-18`: dal `-20` esce il COMMENT sul vincolo (in `changes` e in `rollback`) e il changeSet
    prende `validCheckSums: ANY`. Nuovo `90_end/20261111-68-update-comment-chk-job-run-log-processo-dichiarato`, con lo
    stesso testo e preCondition HALT.
  * **Provato:** l'SQL estratto del `-20` e del `-68`, change e rollback, su dbdev in ROLLBACK, senza errori. Il testo
    del `-68` e' identico a quello vivo. Guardrail verdi. **Non provato:** il migrate da zero.
  * **Per Tid:** rilanciare il migrate da zero, poi l'update su dbdev e scratch (il `-68` riscrive un testo che c'e' gia').

## 35. S-BE-1 — le frasi della famiglia ATTIVO senza tabelle: censimento (2026-11-10)

Il modello l'ha deciso Tid il 2026-11-07 (§5, «Decisione di Tid su S-BE-1»): la frase non nomina tabelle, la riga in
causa la dice il **bersaglio** (`config.tipi_entita` + id), un padre senza tipo non ha bersaglio e la frase regge da
sola, i nomi tecnici restano nel contesto del diario. Restava al team DB **da dove il trigger sa il tipo**. Il
censimento è su dbdev del 2026-11-10; le misure sono fatti datati, non motivi.

### 35.1 Chi solleva, e che cosa dice oggi

| Guard | Codici per l'operatore (classe) | Frase di oggi |
| --- | --- | --- |
| `dbops.trgfn_child_requires_active_parent` (REQUIRE) | `E_ATTIVO_PADRE_NON_ATTIVO` (CONFLITTO_STATO), `E_PADRE_INESISTENTE` (DATO_ERRATO) | «%s (%s = %s) non è attivo: non vi si può collegare una riga attiva di %s.» — «In %s non c'è nessuna riga con %s = %s: …» |
| `dbops.trgfn_child_requires_non_obsolete_parent` | `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (CONFLITTO_STATO), `E_PADRE_INESISTENTE` | «Catalogo non utilizzabile per nuove istanze (obsoleto): %s», con `%s` = «Catalogo schema.tabella obsoleto dal …» |
| `dbops.trgfn_prevent_deactivate_if_children` (BLOCK) | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST` (CONFLITTO_STATO) | «Non si puo' disattivare %s (%s = %s): ci sono ancora righe collegate [attive] in %s.» |

Tutte nominano `schema.tabella` all'operatore: S-BE-1 ne segnalava due, ma la malattia è della famiglia (N1). I codici
tecnici (`E_TRIGGER_ARGOMENTI_INVALIDI`, `E_ATTIVO_BLOCK_ARGS`, `…_FKCOL_NOT_FOUND`, `…_REF_NULL`) restano come sono.

### 35.2 I montaggi e i padri

* REQUIRE: 437 montaggi su 105 tabelle padre; «non ritirato»: 5 montaggi su 4 padri; BLOCK: 437 montaggi (lo specchio
  del REQUIRE). Ogni colonna montata è anche una FK vera verso il padre; `ref_col` è `id` dappertutto, tranne
  `anagrafiche.emittenti_fiscali` (anche `soggetto_ruolo_id`).
* **Padri con un tipo in `config.tipi_entita`**, letti dalle note dei tipi (la tabella del tipo non è una colonna):
  `catalogo.articoli` (ARTICOLO, 39 montaggi), `catalogo.articoli_componenti` (ARTICOLO_COMPONENTE, 7),
  `magazzino.assets` (ASSET, 8), `magazzino.eventi_assets` (EVENTO_ASSET, 1), `vendite.contratti_righe` (CONTRATTO_RIGA,
  2), `vendite.ddt_righe` (DDT_VENDITA_RIGA, 6), `vendite.listini_versioni` (LISTINO_VERSIONE, 6), `vendite.ordini_righe`
  (ORDINE_VENDITA_RIGA, 4), `vendite.preventivi_righe` (PREVENTIVO_RIGA, 3), `vendite.promo_articoli` (PROMO_ARTICOLO,
  2), `vendite.resi_righe` (RESO_VENDITA_RIGA, 4). Gli altri 94 padri sono cataloghi (`config.iva`, gli stati,
  `catalogo.unita_misura`, …) e anagrafiche senza tipo: per decisione, niente bersaglio.
* ⚠️ `magazzino.lotti` **non** è LOTTO: LOTTO è il lotto di fatturazione. È l'esempio del bersaglio sbagliato che porta
  l'operatore altrove (`brief-db-bersaglio-errore` L5: un bersaglio sbagliato è attivo, non inerte).

### 35.3 Che cosa c'è già, e che cosa no

* **Tabella → tipo:** oggi solo per i 17 tipi sorgente, attraverso `config.sorgenti.target_table`
  (`tipi_entita.sorgente_codice_interno`); dei padri di §35.2 ne copre uno (EVENTO_ASSET). Per i 22 tipi non sorgente
  la tabella sta solo nella nota. Nessuna funzione risolve una tabella nel suo tipo.
* **Forma del bersaglio:** `'bersaglio', jsonb_build_array(jsonb_build_object('tipo', …, 'id', …::text))` nel contesto
  di `fn_log_and_raise_error` (es. `vendite.fn_get_or_create_lotto`); il backend lo porta in `targets`.
* **Le regole già decise** (`brief-db-bersaglio-errore`): il tipo è un'entità logica, non una tabella (§3); il bersaglio
  va sui codici non TECNICO (§5.5): i cinque di §35.1 lo sono; non si punta al vuoto (§5.5, ragione 2); la derivazione
  automatica dal contesto è respinta (L5): il bersaglio si scrive esplicito.
* **Consumatori dei codici:** pgTAP 3/1/4/3/3 file (nell'ordine di §35.1: PADRE_NON_ATTIVO, PADRE_INESISTENTE,
  BLOCK_ACTIVE, BLOCK_EXIST, CATALOGO_OBSOLETO); backend 7/2/3/4/2 file (`error_messages_fallback.py` ha già le frasi
  senza tabelle), frontend 4 file per `E_ATTIVO_BLOCK_CHILDREN_EXIST`. Il backend legge frase e `targets` dai canali che
  ha già.

### 35.4 I nodi (da decidere, Tid)

**N1 — Il perimetro.** S-BE-1 nominava due codici; i guard della famiglia ne hanno cinque con la stessa frase.
**Proposta: tutti e cinque**, nello stesso giro: stessi tre guard, stesso catalogo, e un modello solo.

**N2 — La sede «tabella → tipo».** È un fatto del tipo (dove vivono le sue righe), uno per padre: non si ripete per
montaggio.
* **(a) proposta:** una colonna `tabella regclass` in `config.tipi_entita`, univoca, nulla per i tipi senza una tabella
  propria; per i tipi sorgente la tabella resta in `config.sorgenti.target_table` (una sede: `CHECK (NOT is_sorgente OR
  tabella IS NULL)`), e **un solo risolutore**, `config.fn_tipo_entita_di_tabella(regclass)`, legge le due strade. Il
  valore si scrive nel CSV di `tipi_entita` per gli 11 padri di §35.2 (dagli altri tipi solo dove la nota la dichiara).
* (b) la forma suggerita dal backend: il codice del tipo come **argomento del trigger**, scritto dal generatore. Anche il
  generatore dovrebbe però sapere il tipo della tabella: (b) non toglie (a), ci aggiunge una copia in 442 `tgargs`, e
  cambia la grammatica di `dbops.fn_trigger_attivo_argomenti`, condivisa dai tre guard e dai loro lettori.

**N3 — Quando si risolve il tipo.** Con (a): **proposta: nel guard, sul ramo del rifiuto** (`fn_tipo_entita_di_tabella`
chiamata solo prima di sollevare): nessun costo sulla scrittura che passa, nessun rimontaggio quando un tipo nasce.

**N4 — Quali rifiuti portano il bersaglio.**
* `E_ATTIVO_PADRE_NON_ATTIVO`, `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`: **sì**, il padre (tipo + id), se ha un tipo e se
  `ref_col` è la chiave del tipo (`key_selector`); altrimenti niente.
* `E_PADRE_INESISTENTE`: **no**, punterebbe sempre al vuoto (§5.5 ragione 2). Solo la frase.
* BLOCK (`…_CHILDREN_ACTIVE`, `…_CHILDREN_EXIST`): il padre è la riga che l'operatore sta spegnendo, il bersaglio utile
  sarebbero le figlie (n). **Proposta: in questo giro solo la frase**; le figlie come bersaglio sono una scelta a parte.

**N5 — I tipi che hanno una riga ma non una rotta.** `LISTINO_VERSIONE` dichiara nella nota che l'id da solo non basta
come bersaglio (la rotta chiede anche il listino); i tipi `…_RIGA` sono nati per note e provenienza. Il catalogo vuole
che un tipo da bersaglio abbia una rotta. **Proposta:** scrivere la tabella (N2) solo per i tipi che hanno una rotta
da id, cioè **non** per LISTINO_VERSIONE e per le righe finché il frontend non le apre; da confermare col catalogo delle
rotte del frontend (domanda al team FE, non lettura di `frontend/`).

**N6 — Le frasi.** Senza valori: «La riga a cui si collega non è attiva: non vi si può collegare una riga attiva.»,
«La riga a cui si collega non esiste.», «La riga a cui si collega è ritirata: non si può usare per una riga nuova.»,
«Non si può disattivare: ci sono ancora righe collegate attive.» / «… righe collegate.» (le frasi di ripiego del
backend, dove ci sono). Gli argomenti `VARIADIC` escono dai tre guard insieme alla frase (cambiare la frase senza gli
argomenti rompe chi li conta, e viceversa); padre, figlia, colonna e valore restano nel contesto del diario.

**Ricaduta BE prevista:** nessuna obbligatoria (frase e `targets` dai canali che legge); i 4 file del frontend su `E_ATTIVO_BLOCK_CHILDREN_EXIST` sono da
guardare solo se leggono la frase.

### 35.5 Le decisioni di Tid (2026-11-10)

**N1-N6 come da proposta**, e il via allo sviluppo. Numeri: `20261111-40` … `-46` (il catalogo era a `-37`; `-38` e
`-39` lasciati di margine all'altra sessione).

### 35.6 Scritto e provato (2026-11-10)

#### 35.6.1 I changeSet

| changeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261111-40` | `config.tipi_entita.tabella` (text, CHECK di forma, `NULL` per un tipo sorgente, univoca); COMMENT della tabella al presente |
| `20_code/script/20261111-41` | `script.fn_bersaglio_di_riga(schema, tabella, colonna, valore)`: il bersaglio dal catalogo, o NULL. `BEGIN ATOMIC`, DEFINER |
| `20_code/dbops/20261111-42` | `trgfn_child_requires_active_parent`: variadico vuoto; il padre spento porta il bersaglio |
| `20_code/dbops/20261111-43` | `trgfn_child_requires_non_obsolete_parent`: variadico vuoto (prima una frase composta col catalogo); il ritirato porta il bersaglio |
| `20_code/dbops/20261111-44` | `trgfn_prevent_deactivate_if_children`: variadico vuoto, nessun bersaglio |
| `20_code/script/20261111-45` | `fn_check_registro_disattivabile`: gli otto motivi senza `valori`; COMMENT al presente |
| `20_code/script/20261111-46` | `fn_check_famiglia_documento_disattivabile`: i due motivi senza `valori`; COMMENT al presente |

I tre trigger e le due check ripartono dal loro ultimo changeSet, verificato uguale al vivo; il rollback rimette corpo e
COMMENT di prima.

#### 35.6.2 Fuori dai changeSet

* **CSV:** `messaggi_errore.csv`, le cinque frasi senza segnaposti e le cause che dicevano «la tabella nominata nel
  messaggio»; la grafia di ogni riga resta la sua (`puo'` nelle due BLOCK, come il ripiego del backend).
  `tipi_entita.csv`, colonna `tabella` per cinque tipi: ARTICOLO, PROMO_ARTICOLO, LOTTO, DEFINIZIONE_WORKFLOW, FLUSSO.
* **Loader esteso sul posto:** `80_data/changelog/20260822-55` (mirror `runOnChange`, `validCheckSums: ANY`), una colonna
  in piu', come nel 2026-08 e nel 2026-10. Prima di toccarlo, CSV e DB confrontati riga per riga (`tipi_entita` 39/39,
  `eventi_dominio` 6/6): la riesecuzione scrive solo `tabella`.
* **pgTAP nuovo** `dbops/test-bersaglio-guard-attivo-v1` (21 test).
* **pgTAP riallineati** (asserivano «la frase nomina la tabella»): `catalogo/test-articoli-approvvigionamento-v1` (10),
  `catalogo/test-fn-riattiva-articolo-v1` (1), `dbops/test-guard-attivo-grammatica-e-codici-v1` (10),
  `dbops/test-guard-attivo-occhi-del-proprietario-v1` (5), `dbops/test-trgfn-prevent-deactivate-if-children-pdp` (8, 13),
  `script/test-fn-check-registro-disattivabile-v1` (5, 9), `vendite/test-registri-per-emittente-v1` (6). Ora asseriscono la
  frase del catalogo del codice giusto, cioè il ramo. `config/test-grammatica-catalogo-sorgenti-entita-v1` test 4 passa da
  LOTTO a TASK_RUN: LOTTO dichiara una tabella, e il CHECK nuovo rifiuterebbe prima della FK che il test prova.
* **Doc:** `manual/` dei tre trigger e di `fn_check_famiglia_documento_disattivabile`, pagina nuova
  `script/manual/fn_bersaglio_di_riga.md`, la guida `automazione-db.md` (§ la regola ATTIVO), `fn_riattiva_articolo.md`.

#### 35.6.3 Le scelte che non si vedono dal titolo (da guardare, Tid)

1. **`-41` DEFINER, eseguibile da `PUBLIC`.** I trigger girano come chi scrive, e `config.tipi_entita` la legge solo
   owner e app: un altro ruolo perderebbe il rifiuto di dominio per un permesso negato sul bersaglio. Stessa forma degli
   altri aiutanti dei guard (`fn_trigger_padre_stato`, `fn_trigger_attivo_argomenti`).
2. **Il tipo sorgente vale solo se `apribile`.** È lo stesso criterio di N5 («ha una pagina»), gia' scritto in
   `config.sorgenti`: EVENTO_ASSET (non apribile) non da' bersaglio.
3. **N5, i tipi scritti:** solo quelli con una rotta da id gia' provata (usati come bersaglio altrove, o dichiarata nella
   nota): ARTICOLO, PROMO_ARTICOLO, LOTTO, DEFINIZIONE_WORKFLOW, FLUSSO. **Da confermare col team FE** (passo
   9-nonagies-quater): ASSET, ARTICOLO_COMPONENTE, LISTINO_VERSIONE (la nota dice che l'id non basta), le righe.
   Aggiungerli e' una riga di CSV, senza toccare i trigger.
4. **Il contesto del diario** (padre, figlia, colonna, valore) non e' provato dal pgTAP: `dbops.error_log` si scrive via
   dblink solo col canale acceso, e il test non dipende dalla macchina. I trigger lo costruiscono come prima.

#### 35.6.4 Trovato per strada (non corretto)

* **`key_selector` diverso nei due cataloghi** per lo stesso tipo: PREVENTIVO e OFFERTA_COMMERCIALE sono `id` in
  `config.tipi_entita` e `uid` in `config.sorgenti`, mentre il COMMENT di `tipi_entita.key_selector` dice «stessi valori di
  config.sorgenti.key_selector, di proposito». Il bersaglio usa `tipi_entita` (come `vendite.fn_push_preventivo_a_ordine`,
  che punta PREVENTIVO per id). Oggi non tocca S-BE-1: nessuno dei due e' padre di un montaggio ATTIVO.
  ⚠️ **Rettifica (2026-11-11): non si allinea niente.** I due valori rispondono a domande diverse: `sorgenti.key_selector`
  e' la chiave con cui un documento cita la sua provenienza (la chiave mista id/uid, decisione definitiva di Tid del
  2026-10-19, guida `sorgente-polimorfa` §3), `tipi_entita.key_selector` quella con cui si apre la cosa a video. A essere
  falso e' solo il COMMENT di `tipi_entita.key_selector` («stessi valori … di proposito»): stesso vocabolario, valori
  che possono differire. **Scritto** (via di Tid, 2026-11-11): `00_schema/config/20261111-67-update-comment-tipi-entita-key-selector`,
  solo il COMMENT, valori invariati. Provato su dbdev (SQL estratto in ROLLBACK; il rollback rimette il testo di oggi,
  identico); guardrail `comment_al_presente`, `run_on_change`, `sql_letterali`, `v1_congelato`, `precondition_seed` verdi.
  Nessun pgTAP ne' codice BE legge quel testo. **Applicato** da Tid su dbdev e scratch (2026-11-11), riscontrato sul `databasechangelog` e sul COMMENT vivo. Resta la doc auto-generata.
  ✅ **Deciso da Tid** il 2026-11-11 (§35.8): dicono il vero tutti e due, ed è il COMMENT a sbagliare. ⚠️ Il `-67` lascia
  «'id' (la PK numerica)», falso per ARTICOLO (uuid): residuo in §35.8, passo 9-nonagies-septies.
* **Doc del backend:** `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md` (riga del guard di disattivazione)
  dice che il messaggio «nomina la tabella che sta bloccando»: da riscrivere dal team BE.

#### 35.6.5 La prova, e che cosa resta a Tid

* **Prova** su dbdev, SQL estratto da `-40` … `-46` nell'ordine del migrate piu' i valori dei due CSV (UPDATE per chiave,
  come il mirror), in transazione annullata come `zeroerp_owner`: il pgTAP nuovo 21/21; i trenta pgTAP che nominano i
  cinque codici, le due check o `tipi_entita`, con e senza l'estratto: cambiano solo i test riallineati di §35.6.2, tutti
  verdi con l'estratto. **Corsa larga**, i 353 pgTAP di `dbops`, `script`, `config` e `rls`, con e senza: cambiano solo
  quelli di §35.6.2 e il nuovo.
* ⚠️ **Trovato dalla corsa larga, e corretto:** `-45` e `-46` ricopiavano dall'ultimo YAML `SET search_path TO
  'pg_catalog', 'public'`, ma sul vivo c'e' anche `pg_temp` (aggiunto dopo da un `ALTER FUNCTION`, D6-bis): il CREATE OR
  REPLACE l'avrebbe tolto, e `dbops/test-security-definer-search-path-v1` (test 4) era rosso. Ora `pg_temp` c'e', anche
  nel rollback. Confrontati poi tutti gli attributi delle cinque funzioni prima e dopo l'estratto (sicurezza,
  volatilita', costo, `search_path`, proprietario, permessi, risultato): nessuna differenza.
* **Guardrail** verdi: `run_on_change`, `v1_congelato`, `pgtap_preambolo`, `comment_al_presente`, `sql_letterali`,
  `timestamp_senza_fuso`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch`.
* **Non provato:** il migrate vero (pgjdbc, la `BEGIN ATOMIC` del `-41` sta da sola nel suo `sql:`), il caricamento dei
  CSV dal loader, la corsa come app, la CI da zero.
* **Per Tid:**
  1. apply di `20261111-40` … `-46` e dei due CSV su dbdev e scratch;
  2. pgTAP: `dbops/test-bersaglio-guard-attivo-v1` (nuovo), i sette riallineati,
     `config/test-grammatica-catalogo-sorgenti-entita-v1` e `dbops/test-security-definer-search-path-v1`;
  3. la doc auto-generata dopo l'apply.
* **Ricadute BE:** nessuna obbligatoria: il backend legge frase e `targets` dai canali che ha gia', e i suoi test controllano
  i codici, non le frasi. Resta la doc di §35.6.4.

#### 35.6.6 Applicato (2026-11-11)

* **Apply** di `20261111-40` … `-46` e dei due CSV su dbdev e scratch (Tid), pgTAP verdi, doc auto-generata e **commit**
  (`67df18ad8d`). Riscontrato sul `databasechangelog` e sui dati di entrambi: cinque tipi con la `tabella`, le frasi nuove
  in `config.messaggi_errore`. **S-BE-1 chiuso.**
* Aperti fuori dal perimetro DB: N5 (team FE, passo 9-nonagies-quater) e la doc BE di §35.6.4.

#### 35.6.7 La risposta su N5 (team BE/FE, 2026-11-11)

* **Verificato in `frontend/src/core/bersagli.js`:** il frontend apre come bersaglio i documenti di `DOCUMENTO_DRAWER_TIPI`
  (FATTURA, COMMESSA, CONTRATTO, ORDINE_VENDITA, PREVENTIVO) piu' LOTTO, FLUSSO e DEFINIZIONE_WORKFLOW. ASSET,
  ARTICOLO_COMPONENTE, LISTINO_VERSIONE e le righe non hanno una destinazione: **nessuno dei quattro** va dichiarato, e
  `config.tipi_entita.tabella` resta NULL per loro come scritto in §35.6.3.
* ⚠️ **Trovato dal team BE:** nemmeno ARTICOLO e PROMO_ARTICOLO hanno una destinazione, e il DB ora li manda come bersaglio.
  Non si rompe niente (un tipo che il frontend non conosce non mostra il pulsante), ma il rifiuto piu' frequente, il padre
  articolo spento, arriva senza «Apri l'articolo». Non e' un difetto del DB: il catalogo dichiara la tabella di un tipo
  che si apre col solo id, e l'articolo si apre col solo id. Si chiude aggiungendo le due destinazioni (lavoro FE: **fatto**, vedi passo 9-nonagies-quater;
  §35.7).
* **Team BE** (§35.4): la frase di `api_emittenti_fiscali.md` è riscritta (passo 9-nonagies-quinquies).

### 35.7 Applicato e chiuso (2026-11-11)

* **Apply** di `20261111-40` … `-46` e dei due CSV su dbdev e scratch, pgTAP di §35.6.5 verdi, doc auto-generata:
  Tid, commit `67df18ad8d` (2026-11-11). **S-BE-1 è chiuso.**
* **Verificato dopo** (2026-11-11, sessione BE): i `manual/` e la guida `automazione-db.md` sono allineati
  (passo 12, prima metà). Resta una sola pagina che dice il contrario, ed è del backend: passo 9-nonagies-quinquies.
* **N5 chiuso** dal team FE (2026-11-11, 9-nonagies-quater): nessun tipo da aggiungere; ARTICOLO e PROMO_ARTICOLO ora si aprono.
* **Doc BE riscritta** (2026-11-11, 9-nonagies-quinquies).
* **`key_selector` deciso** (Tid, 2026-11-11, §35.8). **COMMENT** corretto in `20261111-67` e applicato, con un residuo (§35.8, 9-nonagies-septies,
  sessione DB); poi l'archiviazione (passo 12).

### 35.8 Il `key_selector` dei due cataloghi: deciso (Tid, 2026-11-11)

**La decisione.** `config.sorgenti.key_selector` e `config.tipi_entita.key_selector` si chiamano uguale e rispondono a
**due domande diverse**; restano diverse e non si unificano. Nessun dato cambia.

| Colonna | Domanda | PREVENTIVO, OFFERTA_COMMERCIALE |
| --- | --- | --- |
| `config.sorgenti.key_selector` | con che chiave il **lineage** collega il documento (`sorgente_uid` o `sorgente_id`, scelta dal BB che scrive) | `uid` |
| `config.tipi_entita.key_selector` | con che chiave il documento si **raggiunge** (rotte, bersaglio di un errore, timeline) | `id` |

Non era una decisione nuova: **completa** quella del 2026-08-24 (rilievo del BE, la nota di PREVENTIVO in
`tipi_entita.csv`: *«le due colonne si chiamano uguale e rispondono a domande diverse … il valore si misura sulle rotte,
non si eredita dall'altro catalogo»*) e la regola di `docs/it/dbzero/config/manual/sorgenti.md` (§«La chiave `id` o `uid`
la dichiara il tipo, e non si unifica»). Unificare romperebbe una delle due strade: o le rotte (`<int:preventivo_id>`), o
il collegamento «nasce da».

**Il difetto, ed è uno solo.** Il COMMENT di `config.tipi_entita.key_selector` (nato con `20260823-01`) dice due cose
false:

1. *«Stesso nome e stessi valori di config.sorgenti.key_selector, di proposito»*: i valori sono diversi di proposito
   dal 2026-08-24;
2. *«'id' (la PK numerica)»*: per ARTICOLO `id` è la PK, ed è un **uuid** (`catalogo.articoli.id`). Lo ha scoperto il
   FE il 2026-11-11, aprendo il bersaglio ARTICOLO: `key_selector` dice QUALE colonna, non che forma ha
   (`frontend/src/core/utils/idNellaForma.js`).

**Richiesta alla sessione DB** (passo 9-nonagies-septies): un changeSet nuovo in `00_schema/config/` che riscrive il
solo COMMENT, ripartendo dal COMMENT vivo (doc auto-generata), con rollback al testo di oggi. Testo proposto, da
rivedere nella forma della casa (§5d di `linee-guida-sql.md`):

> Con quale chiave si RAGGIUNGE questa entita' da fuori (il bersaglio di un errore, le rotte, la timeline): 'id' (la
> chiave primaria, numerica o uuid secondo la tabella) oppure 'uid' (il codice lungo). ⚠️ Non e'
> config.sorgenti.key_selector: quello dice con quale chiave il LINEAGE collega il documento, e per preventivi e offerte
> e' 'uid' mentre qui e' 'id'. Stesso nome, due domande: il valore si misura sulle rotte del frontend, non si eredita.
> ⛔ Il giornale non la usa: per vendite.event_log l'entity_id e' la PK id, sempre. ⚠️ Nessun DEFAULT, ed e' voluto:
> chi semina un tipo nuovo deve dichiarare la chiave invece di ereditarla.

Ricadute BE e FE: nessuna. Il FE legge la forma dell'id dalla propria mappa (`bersagli.js`, campo `forma`), non da
questa colonna.

**Esito** (2026-11-11): la sessione DB ha scritto `00_schema/config/20261111-67-update-comment-tipi-entita-key-selector`,
applicato da Tid su dbdev e scratch. **Punto 1 corretto**: il testo dice che il vocabolario è lo stesso e la domanda no.
⚠️ **Punto 2 no**: il testo dice ancora «'id' (la PK numerica)». Il `-67` è applicato e non si riscrive: serve un changeSet
nuovo che porti «la chiave primaria, numerica o uuid secondo la tabella» (passo 9-nonagies-septies).

**Residuo scritto** (sessione DB, 2026-11-11, via di Tid): `00_schema/config/20261111-81-update-comment-tipi-entita-key-selector-forma-id`.
Riparte dal COMMENT vivo su dbdev e cambia solo la parentesi, «'id' (la chiave primaria, numerica o uuid secondo la tabella)»,
più la frase «Dice quale colonna, non che forma ha il valore». Rollback al testo del `-67`. Provato su dbdev con l'SQL estratto
in transazione (ROLLBACK): il COMMENT nuovo si applica e il rollback rimette il testo vivo identico. Guardrail
`comment_al_presente`, `run_on_change`, `sql_letterali`, `v1_congelato` e `precondition_seed` verdi. Nessun pgTAP né codice BE
legge quel testo. **Applicato** da Tid su dbdev e scratch (2026-11-11). **Il brief è chiuso.**
