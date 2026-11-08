# Brief DB — La sorgente polimorfa: un documento, una riga, una grammatica sola

## ⏭️ Chi riparte — aggiornato al 2026-11-08

**Riparte: Tid** con le decisioni sui difetti ① … ⑬ di DOC.4 e sulla pagina `pratiche/manual/trgfn_sospensioni_giornale` (§7.3 «Trovato da DOC.4»), poi il **team DB** col giro finale dei reperti del §7.3 (COMMENT stantii, codice morto, la nota di `presidi.csv`), poi l'archiviazione. Il **BE** ha BE-Z.6-a (§8.24): il CSV dei tre codici è applicato. Fatti da Tid il 2026-11-08: l'apply di `codici_errore.csv` (i tre codici ritirati) e gli smoke del §8.22 e del percorso pratica (riga 9-quinquies). Il lotto DOC è fatto (DOC.1 … DOC.4, 2026-11-08) e committato con questo brief. Il §8 è chiuso lato codice (merge #66). I lotti DB 0, R, T, C, D, P, M, Z sono chiusi, applicati e committati; gli acquisti restano fuori (cantiere `acquisti`).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | il modello: tipo + chiave del documento (`sorgente_id` o `sorgente_uid`) + `sorgente_riga` = la riga (2026-11-06) | §4 | — |
| 2 | ✅ DB | storia, censimento delle forme, dei dati e dei lettori (dbdev, 2026-11-06) | §2, §3 | — |
| 3 | ✅ Tid | S-1 … S-7, tutte decise (2026-11-06) | §6.1 | — |
| 3-bis | ✅ Tid | analisi critica: S-8, S-9 decise; S-10 da analizzare; S-7 precisata (2026-11-06) | §6.2, §7.1 | — |
| 4 | ✅ DB | censimento di dettaglio (quattro schede); difetti vivi; decisioni da prendere (2026-11-06) | §3.6, §6.3, Appendice | — |
| 5 | ✅ Tid | D-1 … D-6, D-8, D-11 come proposti; D-12: SQL manuali su dbdev (2026-11-06) | §6.3 | — |
| 5-bis | ✅ Tid | D-9 come proposta (2026-11-06) | §6.3 | — |
| 5-ter | ✅ DB | D-10: verifica di chi impedisce oggi la doppia fatturazione fra documenti collegati (2026-11-06) | §6.4 | — |
| 5-quater | ✅ Tid | D-10 approvata: il registro dei canali si ritira; D-7 decade (2026-11-06) | §6.4 | — |
| 6 | ✅ DB | piano a lotti definitivo (2026-11-06) | §7.2 | — |
| 7 | ✅ Tid | via allo sviluppo del lotto 0 (2026-11-06) | §7.2 | — |
| 7-bis | ✅ DB | giro 0.1 del lotto 0: catalogo dei livelli, colonne, BB che risolve e che scrive, guard unico; provato in transazione (2026-11-06) | §7.2 «Lotto 0, i giri» | — |
| 7-ter | ✅ Tid | apply del giro 0.1 (`20261106-04` … `-16`, CSV), pgTAP verdi (2026-11-06) | §7.2 | — |
| 7-quater | ✅ DB | giro 0.2: lato «in uscita», presidio degli orfani a tre livelli, presidio di struttura; provato in transazione (2026-11-06) | §7.2 «Lotto 0, i giri» | — |
| 7-quinquies | ✅ Tid | apply del giro 0.2 (`20261106-17` … `-21`, CSV dei codici), pgTAP verdi (2026-11-06) | §7.2 | — |
| 7-sexies | ✅ Tid | `sql-una-tantum-sorgenti-orfane-canali.sql` eseguito su dbdev: presidio degli orfani vuoto (2026-11-06) | §7.2 «Il giro 0.2» | — |
| 7-septies | ✅ DB | giro 0.3: i lettori della sorgente di testata nelle due grammatiche, i lettori polimorfi sul BB che risolve; provato in transazione (2026-11-06) | §7.2 «Il giro 0.3» | — |
| 7-octies | ✅ Tid | apply del giro 0.3 (`20261106-22` … `-45`), pgTAP verdi; verde anche il presidio della revisione del preventivo, con le quattro esclusioni `sorgente_*` rinviate al lotto R (2026-11-06) | §7.2 | — |
| 7-nonies | ✅ Tid | via al lotto R (2026-11-06) | §7.2 «Lotto R» | — |
| 7-decies | ✅ DB | giro R.1: provenienza scritta dai sei verbi delle righe di vendita, guard unico montato, residui «import» tolti, righe derivate esistenti convertite; provato in transazione (2026-11-06) | §7.2 «Lotto R, i giri» | — |
| 7-undecies | ✅ Tid | apply del giro R.1 (`20261106-46` … `-58`), pgTAP verdi (2026-11-06) | §7.2 | — |
| 7-duodecies | ✅ DB | giro R.2: ritiro dei sei tipi `*_RIGA` di vendita; i COMMENT del giro 0.3 al presente (proposta DB accettata da Tid, 2026-11-06); provato in transazione | §7.2 «Il giro R.2» | — |
| 7-terdecies | Tid | apply del giro R.2 (`20261106-59`, `-60`, `sorgenti.csv`, `tipi_entita.csv`): ✅ applicato, pgTAP verdi (2026-11-06) | §7.2 | — |
| 7-quaterdecies | ✅ Tid | via al lotto T (2026-11-06) | §7.2 «Lotto T» | — |
| 7-quindecies | ✅ DB | lotto T in cinque giri; giro T.1: ritiro del registro dei canali (D-10); provato in transazione (2026-11-06) | §7.2 «Lotto T, i giri» | — |
| 7-sexdecies | ✅ Tid | apply del giro T.1 (`20261106-61`, `-62`, `storico_scope_policy.csv`), pgTAP verdi, nessuna regressione (2026-11-06) | §7.2 «Il giro T.1» | — |
| 7-sexdecies-bis | ✅ DB | giro T.2: bolle e resi nella grammatica del modello, la riconsegna dal reso (D-4); provato in transazione (2026-11-06) | §7.2 «Il giro T.2» | — |
| 7-sexdecies-ter | ✅ Tid | apply del giro T.2 (`20261106-63` … `-73`; `-63` corretto dopo il primo apply), pgTAP verdi, nessuna regressione (2026-11-06) | §7.2 «Il giro T.2» | — |
| 7-septdecies | ✅ Tid | T.4: il contratto si cancella solo da bozza vuota, come le altre testate (proposta DB accettata, 2026-11-06) | §7.2 «Lotto T, i giri» | — |
| 7-septdecies-bis | ✅ Tid | via al giro T.3 (2026-11-07) | §7.2 «Lotto T, i giri» | — |
| 7-septdecies-ter | ✅ DB | giro T.3: ordini, contratti, fatture nella grammatica del modello; i tre verbi, i lettori, il guard unico, l'unicità sull'offerta (D-8), V-1; provato in transazione (2026-11-07) | §7.2 «Il giro T.3» | — |
| 7-septdecies-quater | ✅ Tid | apply del giro T.3 (`20261106-74` … `-87`), pgTAP verdi, committato (2026-11-07, `b86108e56a`) | §7.2 «Il giro T.3» | — |
| 7-octodecies | ✅ DB | giro T.4: ordini, bolle, resi e contratti si cancellano solo da bozza vuota; il guard esistente prende la metà «vuota», legge lo stato dal BB, diventa DEFINER; provato in transazione (2026-11-07) | §7.2 «Il giro T.4» | — |
| 7-octodecies-ter | ✅ Tid | il contratto precedente di altri contratti non si cancella: `fk_contratti_parent` da `SET NULL` a `NO ACTION` (2026-11-07) | §7.2 «Il giro T.4» | — |
| 7-octodecies-bis | ✅ Tid | apply del giro T.4 (`20261106-88` … `-91`, i due CSV dei codici, il CSV del registro indici), pgTAP verdi come applicazione (2026-11-07) | §7.2 «Il giro T.4» | — |
| 7-novodecies | ✅ Tid | via al giro T.5 (2026-11-07) | §7.2 «Lotto T, i giri» | — |
| 7-novodecies-bis | ✅ DB | giro T.5: i verbi non scrivono più le colonne parallele, il lock le toglie, le colonne si ritirano coi loro indici e vincoli; provato in transazione (2026-11-07) | §7.2 «Il giro T.5» | — |
| 7-vicies | ✅ Tid | apply del giro T.5 (`20261106-92` … `-99`, i due CSV dei codici), pgTAP verdi come applicazione (2026-11-07). ⚠️ Dall'apply i due percorsi BE del §8.8 (BE-T.5-a, BE-T.5-b) danno errore, come accettato dal piano | §7.2 «Il giro T.5», §8.8 | — |
| 7-vicies-bis | ✅ Tid | via al lotto C («procedere con lo sviluppo», 2026-11-07) | §7.2 | — |
| 7-vicies-ter | ✅ DB | lotto C in quattro giri; giro C.1: `attivita_fatturabili` e `fatture_righe` (V-3, V-2, D-1, D-3); provato in transazione (2026-11-07) | §7.2 «Lotto C, i giri» | — |
| 7-vicies-quater | ✅ Tid | apply del giro C.1 (`20261107-41` … `-50`), pgTAP verdi come applicazione (2026-11-07). La convergenza `ci_apply` è passata al secondo update, dopo aver alzato il limite dei file aperti del servizio PostgreSQL (§7.2 «L'apply del giro C.1»). ⚠️ Dall'apply i percorsi BE del §8.9 danno errore, come accettato dal piano | §7.2 «Il giro C.1», §8.9 | — |
| 7-vicies-quinquies | ✅ Tid | via al giro C.2 (`commesse_sorgenti`), «riprendi sviluppo», numerazione da `-59` (da `-51` a `-58` sono di un altro cantiere) (2026-11-07) | §7.2 «Lotto C, i giri» | — |
| 7-vicies-sexies | ✅ DB | giro C.2: `commesse_sorgenti` nelle colonne tipizzate (S-4), unicità sulla chiave nuova, guard unico al posto del testuale; commessa viva, porta del link, flag di corsia, emittente e lineage sulle colonne del modello; il ponte testuale dell'emittente si ritira; provato in transazione (2026-11-07) | §7.2 «Il giro C.2» | — |
| 7-vicies-septies | ✅ Tid | apply del giro C.2 (`20261107-59` … `-69`), convergenza `ci_apply` passata, pgTAP verdi come applicazione (2026-11-07). ⚠️ Dall'apply la voce BE-C.2-a del §8.10 dà errore, come accettato dal piano | §7.2 «Il giro C.2», §8.10 | — |
| 7-vicies-octies | ✅ Tid | via al giro C.3 (`commesse_attivita`), «riprendere lo sviluppo» (2026-11-07) | §7.2 «Lotto C, i giri» | — |
| 7-vicies-octies-bis | ✅ Tid | D-6 precisata: la chiave del gruppo fatturabile prende l'uid dalla `segment_key`, non dal BB che risolve (2026-11-07) | §7.2 «Il giro C.3» | — |
| 7-vicies-octies-ter | ✅ Tid | il guard unico su `commesse_attivita` a livello DOCUMENTO, perché le quote fisse del listino di un contratto vengono dal contratto intero; le fixture dei pgTAP passano a un consumo vero al posto della commessa fittizia (2026-11-07) | §7.2 «Il giro C.3» | — |
| 7-vicies-novies | ✅ DB | giro C.3: `commesse_attivita` nella grammatica del modello (S-5), guard unico (DOCUMENTO), guard della chiave del push, la chiave del gruppo dalla `segment_key` (D-6), lettori e viste, fixture sui consumi; 71 pgTAP allineati; provato in transazione (2026-11-07) | §7.2 «Il giro C.3» | — |
| 7-tricies | ✅ Tid | apply del giro C.3 (`20261107-70` … `-99`, `20261108-01` … `-05`, i due CSV dei codici) su dbdev e scratch, pgTAP verdi come applicazione (2026-11-07). ⚠️ Dall'apply gli smoke del §8.11 (BE-C.3-c) danno errore, come accettato dal piano | §7.2 «Il giro C.3», §8.11 | — |
| 7-tricies-bis-commit | ✅ Tid | commit del giro C.3 su `dev/db-tid` (2026-11-07, `6a21da572d`) | — | — |
| 7-tricies-bis | ✅ Tid | V-7: vale il codice della commessa, come la dashboard (2026-11-07) | §3.6 | — |
| 7-tricies-quater | ✅ Tid | via alla correzione di V-7 (proposta DB in §3.6) (2026-11-07) | §3.6 | — |
| 7-tricies-ter | ✅ Tid | via al giro C.4 (`ATTIVITA` esce dalle sorgenti) (2026-11-07) | §7.2 «Lotto C, i giri» | — |
| 7-tricies-quinquies | ✅ DB | giro C.4: `ATTIVITA` esce da `config.sorgenti` e resta entità, il lato «in uscita» su `attivita_fatturabili` lo smonta la convergenza; V-7: il riferimento di un gruppo senza numero è il codice della commessa; provato in transazione (2026-11-07) | §7.2 «Il giro C.4» | — |
| 7-tricies-sexies | ✅ Tid | apply del giro C.4 (`20261108-06`, `-07`, `sorgenti.csv`, `tipi_entita.csv`) su dbdev (19:06) e scratch (19:07), pgTAP verdi come applicazione, committato su `dev/db-tid` (2026-11-07) | §7.2 «Il giro C.4» | — |
| 7-tricies-septies | ✅ Tid | via al lotto D (2026-11-07) | §7.2 «Lotto D» | — |
| 7-tricies-octies | ✅ DB | giro D.1: `documenti_generati` nelle colonne tipizzate col BB che scrive, una serie di versioni per documento (V-6 senza SQL manuale), guard unico (DOCUMENTO, BLOCCA), snapshot su `sorgente_id`; la coda di stampa perde `sorgente_uid` ed è esente dal guard col motivo (FK vera); provato in transazione (2026-11-07) | §7.2 «Il giro D.1, le scelte» | — |
| 7-tricies-novies | ✅ Tid | apply del giro D.1 (`20261108-14` … `-21`) su dbdev (23:05) e scratch (23:11); pgTAP verdi come applicazione (Tid, e la regressione DB del giro K.1 sullo scratch), committato su `dev/db-tid` (2026-11-07). ⚠️ Dall'apply i percorsi BE del §8.13 danno errore, come accettato dal piano | §7.2 «Il giro D.1, le scelte», §8.13 | — |
| 7-quadragies | ✅ Tid | richiesta BE e via al giro K.1, il nome della chiave (2026-11-07) | §7.2 «Il giro K.1» | — |
| 7-quadragies-bis | ✅ DB | giro K.1: `p_sorgente_chiave` nella madre e nella porta, la chiave `sorgente_chiave` del batch, i quattro chiamanti per nome, 54 pgTAP allineati; provato in transazione (2026-11-07) | §7.2 «Il giro K.1» | — |
| 7-quadragies-ter | ✅ Tid | apply del giro K.1 (`20261108-22` … `-24`, `-32` … `-34`) su dbdev (23:10) e scratch (23:11); pgTAP verdi come applicazione (Tid, e la regressione DB sullo scratch), committato su `dev/db-tid` (2026-11-07). ⚠️ Dall'apply il push del BE dà errore fino a BE-K.1-a e -b (§8.14) | §7.2 «Il giro K.1», §8.14 | — |
| 7-quadragies-quater | ✅ Tid | l'esenzione della coda di stampa dal guard confermata come proposta DB: la FK resta, esente dal solo guard (2026-11-07) | §7.2 «Il giro D.1, le scelte» | — |
| 7-quadragies-quinquies | ✅ Tid | la colonna della chiave nei cinque lister del push si chiama `sorgente_chiave`, «teniamo tutto pulito»; anche il parametro del builder `dbops.fn_pgtap_crea_commessa_attivita` diventa `p_sorgente_chiave`, coi pgTAP che lo chiamano (2026-11-07) | §7.2 «Il giro K.1» | — |
| 7-quadragies-sexies | ✅ DB | giro K.2: i cinque lister con `sorgente_chiave` (COMMENT al presente), il builder con `p_sorgente_chiave`, due esempi d'uso superati, 40 pgTAP allineati, BE-K.2-a; provato in transazione (2026-11-07) | §7.2 «Il giro K.2», §8.15 | — |
| 7-quadragies-septies | ✅ Tid | CI da zero ferma sul `20261107-70` («index `ix_commesse_attivita_sorgente_competenza` does not exist»: nasce in `90_end/20260703-58`, che da zero gira dopo). Rimedio senza toccare il `-70`: `00_schema/vendite/20261107-05` lo crea se manca finché `sorgente_uid` è testo, `90_end/20261108-35` lo toglie se il `-58` l'ha rifatto; su dbdev tutti e due a vuoto (2026-11-07). Applicato su dbdev e scratch (2026-11-08, 00:20), committato (`8bbae0df7b`) | §7.2 «Il giro C.3» | — |
| 7-quadragies-octies | ✅ Tid | apply del giro K.2 (`20261108-36` … `-40`, `-61` … `-63`), pgTAP verdi come applicazione, committato su `dev/db-tid` (2026-11-08). ⚠️ Dall'apply il push del BE perde la chiave fino a BE-K.2-a (§8.15) | §7.2 «Il giro K.2» | — |
| 7-quadragies-novies | DB | CI da zero ferma su `80_data/changelog/20260224-37` («column a.sorgente_tipo_id does not exist»): il backfill del pregresso di febbraio legge `attivita_fatturabili.sorgente_tipo_id`, che da zero `00_schema/vendite/20261107-45` (giro C.1) ha già tolto, perché `00_schema` corre tutto prima di `80_data`. Rimedio: preCondition `columnExists` + `onFail: MARK_RAN` (da zero non c'è storico da riallineare; le preConditions non entrano nel checksum, su dbdev resta EXECUTED). Censiti `80_data` e `90_end` contro tutte le colonne tolte dal cantiere: nessun'altra mina (2026-11-08) | §7.2 «Il giro C.1» | commit di Tid, poi CI |
| 7-quinquagies | ✅ Tid | via al lotto P («il via al lotto P, quando vuoi»), numerazione dal primo progressivo libero del giorno (2026-11-08) | §7.2 «Lotto P» | — |
| 7-quinquagies-bis | ✅ DB | giro P.1: `pratiche_sorgenti` e `reconcile_errori` nelle colonne tipizzate (S-4, D-9), la pratica del documento, lo stato e il reconcile sulle colonne del modello, le sette liste e la sintesi della lineage, E-9 (il reconcile per codice), E-10, i tre verbi sul BB, il guard unico, il guard testuale ritirato; 12 pgTAP allineati, uno nuovo; provato in transazione (2026-11-08) | §7.2 «Il giro P.1, le scelte», §8.16 | — |
| 7-quinquagies-ter | ✅ Tid | apply del giro P.1 (`20261108-64` … `-87`) su dbdev e scratch, pgTAP verdi come applicazione, committato su `dev/db-tid` (2026-11-08). ⚠️ Dall'apply i percorsi BE del §8.16 danno errore, come accettato dal piano | §7.2 «Il giro P.1, le scelte», §8.16 | 7-quinquagies-bis |
| 7-sexagies | ✅ DB + Tid | riverifica di D58, D29, ⑧ prima del lotto M: viste e scrittori invariati, censimento §2.4 corretto; Tid: A (riga = bolla + conteggio), B (BB del reso + le due copie di `vendite`), C (presidio dell'arrivo del trasferimento) come proposti, pgTAP confermati (2026-11-08) | §7.2 «Lotto M», «Riverifica fatta» | — |
| 7-sexagies-bis | ✅ Tid | via al lotto M («l'altro cantiere è fermo, puoi iniziare lo sviluppo»); «ricorda l'utilizzo di %type» (2026-11-08) | §7.2 «Lotto M, i giri» | — |
| 7-sexagies-ter | ✅ DB | lotto M in quattro giri; giro M.1: il registro nella grammatica del modello (conversione, identità equivalente, primitiva, storno per documento, disponibilità per prefisso, sette verbi, guard unico), i presidi D58, D29, ⑧, C, M22, M23; due pgTAP nuovi, quindici allineati; provato in transazione (2026-11-08) | §7.2 «Il giro M.1, le scelte», §8.17 | — |
| 7-sexagies-quater | ✅ Tid | apply del giro M.1 (`20261108-94` … `-99`, `20261109-01` … `-14`, `presidi.csv`, `presidi_testi.csv`, `codici_errore.csv`), pgTAP verdi come applicazione, committato su `dev/db-tid` (2026-11-08). ⚠️ Dall'apply la consultazione dei movimenti per documento del BE è vuota fino a BE-M.1-a (§8.17), come accettato dal piano | §7.2 «Il giro M.1, le scelte», §8.17 | — |
| 7-sexagies-quinquies | ✅ Tid | via al giro M.2, con le due scelte DB: il ritiro del guard tipizzato anticipato dal lotto Z, i CHECK col nome `…_sorgente_forma` («si procedi con le scelte», 2026-11-08) | §7.2 «Il giro M.2, le scelte» | — |
| 7-sexagies-sexies | ✅ DB | giro M.2: testate di magazzino ed evento nella grammatica del modello (conversione, CHECK di forma, indici), guard unico, MODELLO_A fuori dal perimetro, guard tipizzato ritirato; le due descrizioni di `lista_colonna.csv` (UI-M.1-a); un pgTAP nuovo, quattro allineati; provato in transazione (2026-11-08) | §7.2 «Il giro M.2, le scelte», §8.18 | — |
| 7-sexagies-septies | ✅ Tid | apply del giro M.2 (committato `ad13694ffb`) (`20261109-15` … `-19`, `ui/lista_colonna.csv`): ✅ applicato su dbdev e scratch (2026-11-08, 12:11), pagine auto-generate rigenerate; `magazzino/test-sorgente-testate-v1` 16/16 su tutti e due (verifica DB, da owner); pgTAP verdi (Tid, 2026-11-08). Resta il commit | §7.2 «Il giro M.2, le scelte», §8.17 | 7-sexagies-sexies |
| 7-sexagies-octies | ✅ Tid | commit del giro M.2 (`ad13694ffb`) e via al giro M.3 («procedi», 2026-11-08) | — | — |
| 7-sexagies-novies | ✅ DB | giro M.3: i cinque tipi di foglia escono da `config.sorgenti`, restano entità; tre pgTAP allineati; provato in transazione (2026-11-08) | §7.2 «Il giro M.3, le scelte», §8.19 | — |
| 7-septuagies | ✅ Tid | apply del giro M.3 (`80_data/changelog/20261109-20`, `tipi_entita.csv`, `sorgenti.csv`) su dbdev (12:37) e scratch (12:38): i due mirror RERAN, il DELETE EXECUTED, pgTAP verdi (Tid, 2026-11-08); committato su `dev/db-tid` | §7.2 «Il giro M.3, le scelte» | 7-sexagies-novies |
| 7-septuagies-bis | ✅ Tid | il giro M.4 (acquisti) passa all'analisi degli acquisti, col riallineamento delle tabelle d'acquisto alla vendita (2026-11-08) | `analisi-simmetria-ordini-acquisto.md` §4.6-bis | — |
| 7-septuagies-ter | ✅ Tid | via al lotto Z («procedi»); Z-a, Z-b, Z-c e R-P.1-1 come proposti (2026-11-08) | §7.2 «Lotto Z, il censimento e i giri» | — |
| 7-septuagies-quater | ✅ DB | giro Z.1: scope senza `ROW_VALIDATOR`, natura in `categoria` (con l'una tantum), codice ritirato, vista per flusso, COMMENT; un pgTAP nuovo, uno allineato; provato in transazione (2026-11-08) | §7.2 «Il giro Z.1, le scelte», §8.20 | — |
| 7-septuagies-quinquies | ✅ Tid | apply del giro Z.1 completato su dbdev e scratch (l'una tantum, poi il migrate), pgTAP verdi; committato su `dev/db-tid` (2026-11-08) | §7.2 «L'apply del giro Z.1» | — |
| 7-septuagies-sexies | ✅ DB | giro Z.2, il censimento: stati iniziali, righe, figli, chi cancella; il guard confronta il letterale `'DRAFT'`; difetto della revisione d'offerta cancellata; proposte Z2-a … Z2-e (2026-11-08) | §7.2 «Il giro Z.2, il censimento» | — |
| 7-septuagies-septies | ✅ Tid | Z2-a … Z2-e, la revoca dei pre-check BE di cancellazione, il messaggio generico per tutti, il via al giro Z.2 («ok procedi», 2026-11-08) | §7.2 «Il giro Z.2, il censimento» | — |
| 7-septuagies-octies | ✅ DB | giro Z.2: il guard su preventivo, offerta e commessa, lo stato iniziale dal vocabolario, la revisione cancellata riporta la madre, il messaggio generico; un pgTAP esteso, cinque allineati; provato in transazione (2026-11-08) | §7.2 «Il giro Z.2, le scelte», §8.21 | — |
| 7-septuagies-novies | ✅ Tid | apply del giro Z.2 (`20_code/vendite/20261109-25` … `-27`, `config/codici_errore.csv`, `config/messaggi_errore.csv`) su dbdev e scratch (15:10), pgTAP verdi come applicazione (2026-11-08). Resta il commit. ⚠️ Dall'apply un'offerta in bozza con eccezioni non si elimina più dal BE (§8.21), come accettato dal piano | §7.2 «Il giro Z.2, le scelte» | — |
| 8 | ✅ DB | lotto Z: giro Z.4, la chiusura: il presidio di struttura col suo elenco finale, il debito degli acquisti precisato, il §8 chiuso (2026-11-08) | §7.2 «Il giro Z.4, la chiusura», §8.22 | — |
| 8-ter | ✅ DB | giro Z.5 (V-7-bis): la segnalazione del lotto dichiara la commessa, il riferimento della scheda Critiche la usa; un pgTAP esteso; provato in transazione (2026-11-08) | §7.2 «Il giro Z.5, le scelte», §8.23 | — |
| 8-quater | ✅ Tid | apply del giro Z.5 (`00_schema/vendite/20261109-80`, `20_code/vendite/-81` … `-83`) su dbdev e scratch (16:18), pgTAP verdi come applicazione (2026-11-08); commit dopo il fast-forward su `Tito-dev` | §7.2 «Il giro Z.5, le scelte» | — |
| 8-bis | ✅ Tid | commit del giro Z.4 (`dbops/test-sorgenti-struttura-v1`, questo brief) e di R-M.2-1 (`ui/lista_colonna.csv`, `ui/lista_preset_colonna.csv`, con le due chiavi i18n di FE-M.2-1 in `it.json`/`en.json`, o il pre-commit è rosso); poi l'apply del seed. Il lotto DB del cantiere è chiuso | §8.22 | 8 |
| 9-bis | ✅ BE | il §8 fino al lotto T: codici, reso, ordine dal preventivo, contratto dall'offerta (2026-11-07, da committare su `dev/backend-tid`). I due percorsi rotti dal giro T.5 sono ripristinati | §8 «Stato al 2026-11-07, dopo il giro BE» | — |
| 9-ter | ✅ BE | il §8.13 (D.1: stampa e drenatore della coda) e il §8.14 (K.1: il nome della chiave del push), i due percorsi rotti dall'apply (2026-11-07, da committare su `dev/backend-tid`) | §8.14 «Stato al 2026-11-07, dopo il giro BE di D.1 e K.1» | — |
| 9-quater | ✅ BE | il §8.16 (P.1: il link documento → pratica, scrittore e lettori), il presidio `pratiche/tests/db/test_link_pratica_sorgente_db`; richieste al DB R-P.1-1, R-P.1-2 (2026-11-08, committato `03fe67e2ac`, merge #57); R-P.1-1 e R-P.1-2 vanno al giro DB di fine cantiere | §8.16 «Stato al 2026-11-08, dopo il giro BE di P.1» | — |
| 9-quinquies | ✅ Tid | gli smoke via API del percorso pratica, fatti (2026-11-08). ✅ BE-P.1-e decisa (2026-11-08): il pre-check «pratiche collegate» si ritira (A) | §8.16 | — |
| 9-sexies | ✅ BE/FE | il §8.17 (M.1: il registro per documento su `sorgente_id`, `sorgente_id` e `sorgente_dettaglio` in SELECT e tipi, i codici dei documenti nell'API, nel FE e nelle etichette); nello stesso giro `autospec` su tutte le patch di repository, col presidio `core/tests/test_presidio_autospec_repository` (2026-11-08, committato `1b45fcc58c`, merge #58) | §8.17 «Stato al 2026-11-08, dopo il giro BE di M.1» | — |
| 9-septies | ✅ BE | il §8.18 (M.2: BE-M.2-a, la testata di magazzino proietta `sorgente_id` e legge `sorgente_riga` come riga; il presidio `magazzino/tests/db/test_documento_interno_db` n. 14); il §8.19 era già chiuso col giro BE di M.1 (le costanti `…_RIGA` ritirate, `test_sorgenti_seed` verde); UI-M.1-a fatta dal DB nel giro M.2 (2026-11-08, committato `41c03ef551`) | §8.19 «Stato al 2026-11-08, dopo il giro BE di M.2» | — |
| 9-octies | DB | dal giro BE di M.2: R-P.1-2 anticipata, ✅ già fatta nel giro Z.1 (`codici_errore.csv:422` ha `obsoleto_dal` = 2026-11-08: il BE l'aveva letta su una copia precedente al commit; ora il BE rigenera le policy, BE-Z.1-b); R-M.2-1, le due colonne della lista dei movimenti, ✅ fatta (via di Tid, 2026-11-08: `ui/lista_colonna.csv` e `ui/lista_preset_colonna.csv`); poi FE-M.2-1, le due chiavi i18n, nello stesso commit del seed | §8.22 | — |
| 9-nonies | ✅ BE | il §8.20 e il §8.21 lato BE (BE-Z.1-a, BE-Z.1-b, BE-Z.2-a, BE-Z.2-b), col codice rimasto morto ritirato e i presidi `vendite/tests/db/test_elimina_bozza_vuota_db` e `pratiche/tests/db/test_link_pratica_sorgente_db` n. 4; richiesta al DB R-Z.2-1 (2026-11-08, committato su `dev/backend-tid`). Resta UI-Z.2-a al FE | §8.22 | 8 |
| 9-decies | ✅ BE/FE | BE-Z.5-a (la commessa della segnalazione, col presidio sul DB vero) e UI-Z.2-a (nessuna azione: il FE non offre l'eliminazione di offerta e commessa); suite BE intera verde (2026-11-08, committato `57a52646e7`, merge #66) | §8.22, §8.23 | 8-quater |
| 9 | ✅ BE/FE + Tid | il §8 chiuso lato codice; gli smoke del §8.22 e del percorso pratica fatti da Tid (2026-11-08) | §8.22 | — |
| 10 | DB | la documentazione del §7.3 (lotto DOC): ✅ DOC.1 … DOC.4 fatti (2026-11-08). ✅ Applicato da Tid il CSV dei tre codici (2026-11-08). Restano le decisioni di Tid sui difetti ① … ⑬, il giro DB dei reperti (§7.3 «Trovato riscrivendo», «Trovato da DOC.4»), BE-Z.6-a, poi l'archiviazione | §7.3 | Tid |

**Decisioni aperte di Tid:** i difetti ① … ⑬ trovati da DOC.4 (correggerli nel giro finale, in un brief a parte o lasciarli) e il ritiro della pagina `pratiche/manual/trgfn_sospensioni_giornale` (§7.3 «Trovato da DOC.4»). Decisa il 2026-11-08: V-7-bis, la commessa la scrive chi solleva la segnalazione (giro Z.5); `vendite.vw_preventivi_pratiche` non si ritira qui, la decide il cantiere pratiche. Decise il 2026-11-08: Z2-a … Z2-e; i pre-check BE di cancellazione si ritirano, la regola sta solo nel DB (revoca della scelta del giro T.4); il messaggio resta generico per tutti i documenti («o specifici per ogni documento o tutti generici»). Decise il 2026-11-08: BE-P.1-e, il pre-check «pratiche collegate» di `elimina_preventivo` si ritira (A); la regola «si cancella solo la bozza vuota» va a DB su preventivi, offerte e commesse nel lotto Z; la bozza vuota che si porta via il suo aggancio alla pratica (C) è una proposta scritta in `gestione-pratiche-come-procedere.md` §3, da decidere dopo (§8.16). Decisa il 2026-11-08: UI-M.1-a, la lista dei movimenti mostra anche documento e dettaglio (§8.17, nel lotto BE/FE). Da guardare (giro M.1, §7.2 «Tre fatti trovati in prova»): il pgTAP di ⑧ è costruito con un'uscita a giacenza zero, perché un carico senza valore porta la media a zero e non a NULL. Decise il 2026-11-08, giro P.1 (§7.2 «Il giro P.1, le scelte»): l'unicità del link alla pratica senza `sorgente_riga` (Tid: «sì»); il guard testuale si ritira nel giro P.1 (Tid: «da fare»). Il nome del file `script/test-guard-sorgente-polimorfa-testuale-v1` è una scelta del team DB, non una decisione di Tid (Tid, 2026-11-08). Decise il 2026-11-07: l'esenzione della coda di stampa dal guard unico, confermata (la FK resta, §7.2 «Il giro D.1, le scelte»); la chiave `sorgente_chiave` anche nei cinque lister del push e nel builder pgTAP (§7.2 «Il giro K.1»). ⏭️ Da applicare del giro K.2: niente (`20_code/vendite/20261108-36` … `-40`, `20_code/dbops/20261108-61` … `-63` applicati da Tid, pgTAP verdi, 2026-11-08). `20_code/dbops/20261108-09` (i COMMENT di quattro builder pgTAP) risulta applicato su dbdev e scratch (2026-11-07, 22:30), col suo presidio verde. ⚠️ Da guardare all'apply di V-7: un documento senza numero che non sta più in una commessa aperta ripiega ancora sulla chiave grezza (§7.2 «Il giro C.4»).
**Lavoro da committare:** il lotto DOC (2026-11-08): DOC.1 … DOC.4 (le guide, `linee-guida-sql.md`, le pagine `manual/` dei giri DOC.3 e DOC.4, `PROJECT_CONTEXT.md`, `mappa-concentrica.md`, `dev/ricette-dove-intervenire.md`, i nove documenti aperti di DOC.4 e `brief-db-articoli-obsoleto-dal.md`), le tre righe di `80_data/sql/config/codici_errore.csv` (applicate da Tid, 2026-11-08), questo brief. ✅ Committato su `dev/db-tid` (2026-11-08). Non del cantiere: le pagine auto-generate rigenerate e `brief-db-revisione-dbops.md`. Prima: il giro Z.5, applicato (2026-11-08): `00_schema/vendite/20261109-80`, `20_code/vendite/20261109-81` … `-83`, i pgTAP `vendite/test-riferimento-gruppo-fatturabile-v1` e `vendite/test-sorgente-commenti-al-presente-v1`, le tre pagine `manual/` (`fn_riferimento_gruppo_fatturabile`, `fn_log_pipeline_fase`, `fatturazione_lotti_log`), questo brief. Prima: il giro Z.4 e R-M.2-1 sono committati su `dev/db-tid` (2026-11-08): `db/pgtap/dbops/test-sorgenti-struttura-v1.sql`, `80_data/sql/ui/lista_colonna.csv`, `80_data/sql/ui/lista_preset_colonna.csv`, le due chiavi i18n (FE-M.2-1), le pagine auto-generate dei giri Z.1 e Z.2, questo brief. Non del cantiere, lasciati fuori: le pagine auto-generate e il brief di `brief-db-revisione-dbops`. Le pagine auto-generate rigenerate nell'albero non sono del cantiere. Prima: il giro Z.2, committato (merge #61): `20_code/vendite/20261109-25`, `-26`, `-27`; in `config/codici_errore.csv` le sole righe di `E_DELETE_DOC_NON_BOZZA` ed `E_DELETE_DOC_CON_RIGHE` (le altre modifiche del file sono dell'altra sessione: separarle); `config/messaggi_errore.csv`; i pgTAP `vendite/test-delete-testate-solo-bozza-vuota-v1`, `script/test-sorgente-in-uscita-v1`, `pratiche/test-sorgente-pratiche-sorgenti-v1`, `vendite/test-sorgente-testate-ordini-contratti-v1`, `vendite/test-sorgente-righe-vendita-v1`, `vendite/test-ddt-righe-evase-dall-ordine-v1`; la pagina `vendite/manual/trgfn_doc_guard_delete_solo_bozza.md`; questo brief. Il giro Z.1 è committato su `dev/db-tid` (2026-11-08): `00_schema/config/20261109-21`, `20_code/script/20261109-23`, `-24`, `90_end/20261109-22`, `config/sorgenti.csv`, `config/codici_errore.csv`, `sql-una-tantum-sorgenti-categoria-evento.sql`, i pgTAP `pratiche/test-vw-flusso-doc-sorgente-v1` (nuovo) e `config/test-sorgenti-scope-pulizia-v1`, questo brief. Prima: niente del cantiere. Il giro M.3 (`80_data/changelog/20261109-20`, `tipi_entita.csv`, `sorgenti.csv`, i tre pgTAP allineati, il commento del debito in `dbops/test-sorgenti-struttura-v1`, `analisi-simmetria-ordini-acquisto.md` §4.6-bis, questo brief) è committato su `dev/db-tid` (2026-11-08). Non del cantiere, lasciati fuori: i file dell'altra sessione (`ui/20261109-32` … `-39`, i CSV e i pgTAP di `dbops`/`ui`, `config/tabelle/aree_funzionali.md`, `azioni_processo.md`, `guide/automazione-db.md`, `brief-db-revisione-dbops.md`). Il giro M.2 è committato (`ad13694ffb`, 2026-11-08). Non del cantiere, da lasciare fuori: `brief-db-revisione-dbops.md`. Prima: il giro M.1 (i venti changeSet `20261108-94` … `-99`, `20261109-01` … `-14`, i tre CSV, i due pgTAP nuovi `dbops/test-presidi-magazzino-grana-v1` e `magazzino/test-sorgente-registro-v1`, i quindici allineati, le pagine auto-generate dei suoi oggetti e i due indici, questo brief) è committato su `dev/db-tid` (2026-11-08). Non del cantiere, lasciati fuori: il blocco 7-bis-b di `brief-db-revisione-dbops` (`20261109-31`, i cinque loader e i CSV di `dbops`, le pagine di `dbops/tabelle` e `dbops/manual`, due pgTAP, le due guide) e quel brief. Prima: Il giro P.1 (i ventiquattro changeSet `20261108-64` … `-87`, il pgTAP nuovo `pratiche/test-sorgente-pratiche-sorgenti-v1`, i dodici pgTAP allineati, le pagine auto-generate rigenerate, le due pagine del guard testuale cancellate, questo brief) è committato su `dev/db-tid` (2026-11-08), insieme al seguito del giro 7 di `brief-db-revisione-dbops` su `shop` (`20261108-88`, `-89`, il loop `ci_apply`, il provisioning, `dbops/test-storico-scope-policy-v1`; il §22 di quel brief resta fuori dal commit, per scelta di Tid). Il rimedio alla CI da zero (`00_schema/vendite/20261107-05`, `90_end/20261108-35`) è committato (`8bbae0df7b`). Il giro K.2 (gli otto changeSet, i 40 pgTAP allineati, questo brief) è committato su `dev/db-tid` (2026-11-08). Non del cantiere, da lasciare fuori: i changeSet `20261108-41` … `-46` coi loro pgTAP, e `brief-db-revisione-dbops.md`. Il giro D.1 (gli otto changeSet, il pgTAP nuovo `documenti/test-sorgente-documenti-generati-v1`, i quindici pgTAP allineati), il giro K.1 (sei changeSet, 54 pgTAP allineati), `20_code/dbops/20261108-09` col presidio `dbops/test-builder-pgtap-vincoli-immediate-v1`, le pagine auto-generate dei loro oggetti e questo brief sono committati su `dev/db-tid` (2026-11-07). Non del cantiere, lasciati fuori: i changeSet `20261108-25` … `-31` coi loro CSV, pgTAP e pagine, i due indici auto-generati, le tre guide e `brief-db-revisione-dbops.md`. Il giro C.4 e V-7 (`20261108-06`, `-07`, `sorgenti.csv`, `tipi_entita.csv`, i cinque pgTAP allineati, questo brief) sono committati su `dev/db-tid` (2026-11-07). Il giro C.3 (`20261107-70` … `-99`, `20261108-01` … `-05`) è committato (`6a21da572d`). Il giro C.2 (`20261107-59` … `-69`) è committato (`036e047ecc`). I changeSet `20261107-51` … `-55` (la coda dei lavori) sono di un altro cantiere, committati a parte (`347cc46f02`). Il giro C.1 (`20261107-41` … `-50`) è committato (`e1713fff2e`). Il giro T.5 (`20261106-92` … `-99`) è committato (`d385cbd3d3`). Il giro T.4 (`20261106-88` … `-91`, i tre CSV, il pgTAP nuovo, i quattro pgTAP allineati, le due pagine `manual/`, questo brief) è committato su `dev/db-tid` il 2026-11-07; il giro T.3 anche (`b86108e56a`). I giri T.1 e T.2 (`20261106-61` … `-73`, `storico_scope_policy.csv`, i pgTAP, le
pagine `manual/` cancellate, questo brief) sono committati su `dev/db-tid` il 2026-11-06. Il lotto 0 intero e il lotto R (giri R.1 e R.2: changeSet `20261106-46` …
`-60`, i due CSV, i pgTAP, i due brief) sono committati su `dev/db-tid` il 2026-11-06. ⚠️ I test Django sono rossi finché il BE non rigenera il file delle policy d'errore (§8.1
BE-0.1-a, §8.2 BE-0.2-a): accettato dal piano, va detto nella PR.

**Fermo collegato, sciolto dal giro R.1:** il lotto B di `brief-db-articoli-obsoleto-dal` (verbi che scrivono la
sorgente, `20261105-15…-19`, mai entrati nell'albero) è riscritto qui sul modello, `20261106-51` … `-56`. Il
§9 di quel brief (indici «idempotenza import», commenti, import esterno su tabella di collegamento) confluisce qui.
Il lotto A dello stesso brief è applicato e resta: legge solo «la sorgente c'è o no».

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-06. **A chi:** Tid, poi il team DB, poi BE/FE.
> **Origine:** Tid, 2026-11-06, sui verbi dell'offerta: *«abbiamo usato male la chiave: sorgente_riga è la riga del
> documento, il fatto che ora su sorgente_riga si metta la testata è errato; dovrebbero esistere sorgente_uid,
> sorgente_id e sorgente_riga»*; *«sorgente_uid e sorgente_id servivano per distinguere le tabelle che hanno chiave
> uid da id»*; *«va verificato dove si è propagato il problema, come viene letta la sorgente polimorfa. Dare una
> dimensione al buco»*.
> **Brief vicini verificati:** `work-done/brief-db-guard-sorgente-polimorfa` (2026-07-18: modello A e B, D1 «la colonna
> `sorgente_riga` ha due scopi», D4 rinviata), `work-done/brief-db-bonifica-pgtap-sorgente-polimorfa`,
> `work-done/brief-db-commesse-multi-sorgente`, `work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione`
> (D-1…D-3: il magazzino sul modello A; D-2 lascia aperti gli indici unici vecchi),
> `work-done/brief-db-grammatica-unica-documenti` (K-1 del 2026-10-19: la chiave id/uid di un tipo non si unifica;
> `fn_segment_key`, il costruttore unico della chiave d'idempotenza del push). Nessun brief aperto sul tema.
> **Ambito:** trasversale: vendite, acquisti, magazzino, pratiche, documenti. È un cambio di modello: si decide prima,
> si misura il dettaglio dopo.

---

## 1. Il buco in una frase

Lo **stesso concetto**, «questo record nasce da quel documento (e da quella sua riga)», è scritto oggi in **sette
grammatiche diverse** nelle stesse colonne `sorgente_*`. Ogni lettore deve sapere quale grammatica ha la tabella che
sta leggendo; se sbaglia, la query torna **zero righe in silenzio**.

## 2. La storia (fatti, con le date)

1. **2025-09-06** — `vendite.ordini` nasce con `source_tipo_id` + `source_id uuid`, «Origine import (**id
   esterno**)», più un indice unico «idempotenza import». Sulle righe (ordini, fatture, attività) c'è anche
   `source_riga`: «Progressivo/ID **riga nella sorgente**». Lo schema originale è quello di Tid: il documento + la sua
   riga.
2. **2025-10-05** — rinomino `source_*` → `sorgente_*` (`20251005-01…-06`, più le testate di magazzino
   `-23`/`-24`). Le colonne si ricreano uguali, indice compreso.
3. **2026-02-09** — `20260209-01`, il primo guard polimorfo, **rilegge** le colonne: `sorgente_riga` è la chiave
   quando `key_selector = 'id'`, `sorgente_uid` quando è `'uid'`, in alternativa. Una testata a chiave `id` finisce
   così in `sorgente_riga`. Per riferire una riga nascono i tipi `*_RIGA` in `config.sorgenti`.
4. **2026-07-18** — `brief-db-guard-sorgente-polimorfa` dà un nome alle due letture: **modello A** (colonne
   alternative) e **modello B** (tabelle di collegamento: chiave testuale del documento + `sorgente_riga` = la riga, cioè
   il modello di Tid). D1 di Tid: `sorgente_riga` si tiene, «doppio scopo documentato». D4 (verificare che la riga
   esista) rinviata: `config.sorgenti` conosce la tabella del documento, non quella delle righe.
5. **2026-07-09** — `20260709-01` toglie l'indice unico su `vendite.ddt`, che vietava più bolle per ordine. Solo lì.
6. **2026-09-15** — il magazzino (Lotto 1) adotta il modello A su sei tabelle.
7. **2026-11-05** — il lotto A di `brief-db-articoli-obsoleto-dal` lo adotta sulle righe di vendita e d'acquisto.
8. **2026-11-06** — la «testata + progressivo» decisa per l'offerta non ci sta nel modello A (vuole una sola delle due
   colonne): è il modello di Tid che riemerge.

## 3. La dimensione (dbdev, 2026-11-06: fatto datato, non motivo)

### 3.1 Le sette grammatiche

29 tabelle hanno `sorgente_tipo_id`. Per i tipi a chiave `id` scrivono:

| # | Grammatica | Tabelle | Cosa c'è per un tipo a chiave `id` |
| --- | --- | --- | --- |
| G1 | testata, solo `sorgente_uid uuid` | `vendite.ordini`, `ddt`, `fatture`, `contratti`, `resi`; `acquisti.ordini`, `acquisti.ddt` | l'**uid** del documento, contro il `key_selector`. Non hanno `sorgente_riga` |
| G2 | modello A: `sorgente_riga` **oppure** `sorgente_uid` | `magazzino.movimenti`, `movimenti_attesi`, le quattro testate; le righe del lotto A (`preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe`, `acquisti.ddt_righe`) | l'**id** in `sorgente_riga`, del documento o della riga secondo il tipo |
| G3 | modello B: `sorgente_uid text` canonico + `sorgente_riga` = riga | `pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti` | `id::text` del documento; la riga a parte |
| G4 | `sorgente_uid text` = sempre l'uid | `vendite.commesse_attivita`, `vendite.documenti_fatturazione_canali` | l'**uid** come testo, contro il `key_selector` |
| G5 | tipo COMMESSA + `sorgente_riga` = riga della commessa | `vendite.attivita_fatturabili`, `vendite.fatture_righe` | `sorgente_riga` = `commesse_attivita.id` (64/64, 8/8); `sorgente_uid` = un hash, non la commessa |
| G6 | mista nella stessa tabella | `documenti.documenti_generati` | l'uid per CONTRATTO, DDT, ORDINE; per FATTURA **tutte e due**: l'uid dalla UI (`sorgente_documenti_views.py`), l'id dal drainer della coda di stampa (corretto dal censimento, Appendice) |
| G7 | `sorgente_id bigint` + `sorgente_uid text` | `vendite.fatture_stampa_coda` | l'id, scritto due volte |

Più `pratiche.reconcile_errori` (testo, senza FK) e `documenti.template_documenti` (solo il tipo, non è una
provenienza).

#### 3.1-bis Che cosa mancava al conteggio (analisi critica, 2026-11-06)

Tre tabelle con `sorgente_*` non comparivano nella tabella sopra:

| Tabella | Che cosa ha | Grammatica |
| --- | --- | --- |
| `acquisti.ordini_righe` | `sorgente_tipo_id`, `sorgente_uid uuid` «Origine import», `sorgente_riga DEFAULT 0`; indice unico `uq_ordini_righe_v_sorgente_fk (tipo, uid)`; **nessun guard** | G1 di riga (import) |
| `magazzino.eventi_assets` | modello A con CHECK «esattamente una chiave»; guard tipizzato. L'evento è a sua volta il **bersaglio** del tipo `EVENTO_ASSET` (sorgente del movimento) | G2; il tipo `EVENTO_ASSET` è S-10 |
| `vendite.attivita_fatturabili.sorgente_origine_tipo_id` | una **quarta** colonna: il tipo del documento d'origine (copiato da `commesse_attivita.sorgente_tipo_id` da `fn_emit_…`), **senza chiave** | provenienza a metà, in G5 |

**G1 non è una grammatica sola.** Le stesse colonne, sulle testate, dicono cose diverse (lo scrivono i manuali
delle tabelle):

| Tabella | Che cosa vuol dire oggi `sorgente_tipo_id + sorgente_uid` | Fonte |
| --- | --- | --- |
| `vendite.ordini`, `vendite.fatture`, `acquisti.ordini`, `acquisti.ddt`, le righe d'ordine | **import da un sistema esterno** (idempotenza CRM), «distinto da `documento_origine_*`» | manuali `ordini` §idempotenza, `fatture` §idempotenza; commenti di colonna «Origine import (uid)» |
| `vendite.ddt`, `vendite.resi` | il **documento padre** (l'ordine, la bolla), per uid | manuali `ddt`, `resi` |
| `vendite.contratti` | l'offerta, **scritta due volte**: `fn_push_offerta_a_contratto` valorizza `sorgente_*` **e** `offerta_id` | corpo della funzione |

Col §4 l'import esce da queste colonne (tabella di collegamento propria): sulle testate dove oggi vogliono dire
«import», `sorgente_*` **cambia significato** e diventa la provenienza. Gli indici «idempotenza import» si ritirano
con l'import, non prima.

**Lo stesso concetto vive anche fuori da `sorgente_*`** (G8, le colonne parallele):

| Dove | Che cosa | Regola di dominio che porta |
| --- | --- | --- |
| `vendite.ordini.documento_origine_tipo` (codice di `config.sorgenti`) + `documento_origine_id bigint` | la provenienza da preventivo o offerta, **per id** anche per il preventivo, che nel catalogo ha chiave `uid` | `uq_ordini_v_documento_origine_offerta` (un ordine vivo per offerta) |
| `vendite.contratti.offerta_id` (FK) | l'offerta del contratto | `uq_contratti_offerta_id` (un contratto vivo per offerta) |
| `vendite.ordini_righe_fulfillment` | riga di bolla ↔ riga d'ordine | la quantità evasa. ⚠️ Corretto dal censimento (2026-11-06): **non** è lo stesso fatto della sorgente. È un legame N:M che porta una quantità e la guardia contro l'over-fulfillment (`E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI`), si ritira, ha FK `RESTRICT` sui due lati: **non può confluire** (eccezione a S-8) |

Sono il caso di S-8 (§6.2). Il censimento ne ha trovate altre due: `vendite.ordini_righe.preventivo_riga_id` (FK
fisica, legame di **consumo** che `fn_documento_ritira_legami` azzera all'annullo: non può confluire) e
`acquisti.ddt.ordine_id` (FK parallela: può confluire, perdendo la FK).

**Esempio** (numeri di fantasia, comportamento del codice). Ordine `id 163`, `uid 0192ab…`, riga `5001`; ne nasce la
bolla 77 con il prelievo 12. Oggi «viene dall'ordine 163» si legge così: `commesse_sorgenti.sorgente_uid = '163'`;
`commesse_attivita.sorgente_uid = '0192ab…'`; `ddt.sorgente_uid = 0192ab…` (uuid); `ddt_righe`: tipo
ORDINE_VENDITA_RIGA, `sorgente_riga = 5001` (previsto dal lotto B); `magazzino.movimenti`: tipo
DDT_VENDITA_PRELIEVO, `sorgente_riga = 12`. Sei `WHERE` diversi; uno sbagliato torna zero righe. Col §4: ovunque
tipo ORDINE_VENDITA, `sorgente_id = 163`, `sorgente_riga` = 5001 o NULL.

### 3.2 I dati

* **~6.860 righe** hanno una sorgente scritta.
* **~2.850** hanno l'uid dove il `key_selector` dice `id`:
  * `documenti_fatturazione_canali` 1.385;
  * `documenti_generati` 648;
  * `commesse_attivita` 515;
  * `ddt` 216;
  * `resi` 88.

  Oggi sono **coerenti con la grammatica della loro tabella**, ma non con `config.sorgenti`.
* **387 orfani** in `documenti_fatturazione_canali`: la sorgente punta a un documento che non esiste più.
  * PREVENTIVO 352, CONTRATTO 14, DDT 16, ORDINE 5;
  * letti come owner: la RLS di quelle tabelle non è forzata, quindi non nasconde righe;
  * nessuna FK e nessun guard lo impediscono: è la tabella G4 senza guard.
* Il **modello di Tid è già vivo in tre posti**, con tre forme: G3 (testo), G5 (tipo COMMESSA + riga) e la «testata +
  progressivo» dell'offerta.

### 3.3 I lettori

| Dove | Quanti |
| --- | --- |
| funzioni DB che nominano le colonne | 92 (vendite 54, script 16, dbops 7, magazzino 6, documenti 5, pratiche 4) |
| viste | 26 (vendite 15, dbops 5, script 3, documenti 3) |
| di cui scrivono la sorgente | 19 |
| leggono `key_selector` | 16 |
| usano i BB `script.fn_sorgente_chiave_id/_uuid` | 8 |
| BE: file Python (test compresi) | 79 |
| FE: file | 10 |
| pgTAP: file | 165 |

⚠️ **Ricontati dal censimento** (2026-11-06, `zeroerp_ruoli`): il metodo sul corpo delle funzioni non vede quelle
scritte con `BEGIN ATOMIC`. Il perimetro è **98 funzioni + 26 viste**: di queste, 4 nominano le colonne solo nei
commenti e 13 solo `sorgente_tipo_id`. Chi scrive la sorgente sono 29, non 19. I BB della chiave li usano 7 oggetti.
La lista nominativa, per schema e per lotto, è nell'Appendice (scheda pratiche-documenti-BB, §D).

**I BB del meccanismo** (da tenere allineati):

* i guard `script.trgfn_guard_sorgente_polimorfa_tipizzata` e `_testuale`;
* `script.fn_sorgente_chiave_id/_uuid`;
* `vendite.fn_get_sorgente_documento_ref`;
* `vendite.fn_link_commessa_sorgente`;
* `pratiche.fn_stato_sorgente`;
* `script.vw_stato_sorgente` con i sei rami `vendite.vw_stato_sorgente_*`;
* `script.vw_pratica_doc_sorgente`;
* `script.fn_check_sorgente_chiudibile`;
* `script.fn_get_sorgente_emittente_sr_id`;
* `vendite.fn_commessa_viva_di_sorgente`;
* `vendite.fn_ritira_commessa_attivita_da_sorgente`;
* `magazzino.fn_storna_movimenti_sorgente`;
* **il presidio degli orfani** `dbops.fn_sorgenti_orfane` + `fn_sorgenti_orfane_perimetro` (vista
  `dbops.vw_sorgenti_orfane`). Legge `sorgente_riga` come chiave del documento, e il suo perimetro pretende
  **entrambe** le colonne di chiave: `documenti_fatturazione_canali` (solo `sorgente_uid`) ne è fuori, ed è per
  questo che i 387 orfani del §3.2 non li segnalava.

Più chi nomina i **codici** dei tipi `*_RIGA` (S-2): `config.tipi_entita` (FK `fk_tipi_entita_sorgenti`,
`is_sorgente = true` sulle 11 righe `*_RIGA` e sui due livelli sotto la riga, G-1 del 2026-10-19), lo scope delle
note (`script.fn_scope_note_ef_perimetro`, `fn_scope_note_magazzino_ef_perimetro`), il BE
(`apps/config/sorgenti.py`, `apps/magazzino/db/famiglie.py`).

### 3.4 Che cosa costa già oggi

* **La lineage traduce a mano.** `vendite.fn_documento_lineage_legami` cerca le righe di commessa con un `CASE` per
  tipo, che rilegge l'uid del documento da preventivi, ordini, contratti e ddt, perché `commesse_attivita` (G4)
  scrive l'uid dove `commesse_sorgenti` (G3) scrive l'id. Ogni tipo nuovo va aggiunto lì a mano. Il
  `brief-db-guard-sorgente-polimorfa` §1d l'aveva già segnato: stesse colonne, stesso push, valori diversi.
* **Gli indici unici «idempotenza import»** (sette documenti) bloccano la derivazione: due righe da un'offerta, un
  secondo ordine dopo un annullo. Sulle testate di magazzino coprono solo la chiave `uid`, quindi non controllano
  niente.
* **Le testate G1 non possono scrivere la chiave giusta**: non hanno né `sorgente_riga` né `sorgente_id`.
* **Il guard tipizzato non può verificare la riga**: legge una sola chiave (D4 rinviata a luglio).
* **Gli orfani** del §3.2.
* **`sorgente_riga DEFAULT 0`** su `vendite.ordini_righe`, `acquisti.ordini_righe`, `vendite.fatture_righe`,
  `vendite.attivita_fatturabili` («0 se non applicabile»): nel modello lo 0 è una riga che non esiste; il
  documento intero è NULL.
* **Gli indici unici da riclassificare sono più dei sette di testata**: anche quelli di riga
  (`uq_*_righe_v_sorgente_fk (tipo, uid)` su ordini_righe di vendita e d'acquisto e su fatture_righe) e quelli
  delle testate di magazzino. Le regole di dominio vive che stanno su una sorgente: `uq_doc_fatt_canali_un_aperto`,
  `uq_documenti_generati_sorgente_progressivo`, `uq_ordini_v_documento_origine_offerta`, `uq_contratti_offerta_id`,
  `uq_pratiche_sorgenti_pratica_tipo_uid_ruolo`, `uq_commesse_sorgenti_src_uid_commessa` e
  **`uq_mag_movimenti_identita`**, l'idempotenza delle registrazioni di magazzino: con S-3 la sua chiave cambia
  (tipo + documento + riga + dettaglio) e deve restare **equivalente**, o si registra due volte.
* **Il guard non controlla l'esclusività**: niente impedisce di valorizzare entrambe le chiavi (solo
  `eventi_assets` ha un CHECK).

### 3.5 Che cosa revoca (dichiarato, 2026-11-06)

Il modello del §4 **non** unifica la chiave: `key_selector` resta, preventivo e offerta restano a `uid`, **K-1 del
2026-10-19 resta**. Revoca invece, e va scritto qui perché chi legge la guida trova «decisione definitiva»:

* la **D1** del 2026-07-18 (`brief-db-guard-sorgente-polimorfa` §3): `sorgente_riga` col «doppio scopo
  documentato» → ha un solo scopo, la riga;
* il **modello A** (colonne alternative) e il **modello B** (chiave testuale) di quel brief, e con loro le due
  funzioni sorelle `_tipizzata` / `_testuale` (D3) → un guard solo;
* nella guida `sorgente-polimorfa.md` il §4a («colonne che sembrano polimorfe ma non lo sono»:
  `commesse_attivita` «sempre l'uid», `ddt`/`resi` «colonna tipizzata diretta», `attivita_fatturabili` «hash») e le
  motivazioni del §4 che si appoggiano a quelle eccezioni;
* il manuale di `config.sorgenti` §Convenzione chiave sorgente, per le stesse parti;
* con S-2, la **G-2** del 2026-10-18 (`brief-db-grammatica-unica-documenti`: «righe e varianti: dentro» il
  catalogo delle sorgenti).

**Non si converte**, e va scritto nella guida: la `segment_key` (`fn_segment_key`) e la chiave del gruppo
fatturabile (`fn_build_gruppo_fatturabile_key`) contengono l'uid anche per i tipi a chiave `id`. Non sono una
provenienza: sono chiavi d'idempotenza, salvate in lotti, esiti e log. Restano costruite con l'uid, che il BB di
risoluzione fornisce (§6.3, D-6).

### 3.6 Difetti vivi trovati dal censimento (2026-11-06)

Non aspettano il modello: sono sbagliati oggi. Per ognuno, se i dati di dbdev vanno corretti a mano, lo decide Tid.

| # | Difetto | Dove | Effetto |
| --- | --- | --- | --- |
| V-1 | `fn_push_offerta_a_contratto`, con una pratica, scrive in `pratiche_sorgenti` il tipo CONTRATTO (chiave `id`) con l'**uuid** del contratto | il guard `_testuale` lo rifiuta (`E_SORG_FORMATO`) | il percorso BE «offerta → contratto con pratica» si ferma. Nessun pgTAP lo prova. ✅ Corretto nel giro T.3 (`20261106-87`), provato dal test 8 di `vendite/test-sorgente-testate-ordini-contratti-v1` (2026-11-07) |
| V-2 | `vw_preventivi_smistamento_righe` cerca l'attività fatturabile con `af.sorgente_uid = p.uid AND af.sorgente_riga = pr.id`: grammatica sbagliata | la vista | non trova mai niente: gli stati FATTURATA ed EMESSA_AF del dialogo di smistamento non compaiono mai |
| V-3 | l'impronta di `attivita_fatturabili.sorgente_uid` non è stata ricalcolata quando la `segment_key` è stata riscritta (2026-10-20) | dbdev, 62 righe su 64 (fatto datato) | ipotesi da provare con un pgTAP: un'attività liberata non si ritrova, l'INSERT sbatte su `uq_attivita_fatturabili_commessa_attivita` e la commessa si ferma a ogni giro |
| V-4 | la cancellazione di reso e contratto non ha regola DB; «si cancella solo la bozza vuota» per ordini, DDT e resi sta solo nel BE | testate di vendita | un reso confermato cancellato lascia **movimenti di magazzino orfani** |
| V-5 | i canali di fatturazione si aprono all'INSERT della bozza e non si tolgono al DELETE | `trgfn_documenti_sync_canali` | spiega gli orfani PREVENTIVO, ORDINE e DDT del §3.2; i 14 CONTRATTO restano senza spiegazione (nel repo nessun DELETE di contratti) |
| V-6 | la stessa fattura in `documenti_generati` con due chiavi | UI e drainer | la lista UI non vede i PDF del drainer; due serie di `progressivo_sorgente` |
| V-7 | il **riferimento** di un gruppo fatturabile il cui documento non ha numero (i consumi: `label_selector` NULL) diverge: `vendite.vw_dash_competenza_gruppi` ripiega sul codice della commessa, `vendite.fn_riferimento_gruppo_fatturabile` (che conosce solo la chiave) sulla chiave grezza | le due scritture della stessa scala di ripiego (il test 16 di `vendite/test-riferimento-gruppo-fatturabile-v1` le dichiara gemelle) | la dashboard Competenza e la scheda Critiche del lotto nominano lo stesso gruppo di consumi in due modi. Trovato dalla regressione del giro C.3 (2026-11-07): prima nessun test costruiva un gruppo di consumi. ✅ **Tid, 2026-11-07: vale il codice della commessa** (il ripiego della dashboard). Proposta DB: `fn_riferimento_gruppo_fatturabile`, che conosce solo la chiave, trova la commessa del documento con `vendite.fn_commessa_viva_di_sorgente` (il BB del giro C.2) e ne usa il codice prima della chiave grezza; la firma non cambia. ✅ Corretto col giro C.4 (`20261108-07`), provato dai test 16 e 17 di `vendite/test-riferimento-gruppo-fatturabile-v1`, che costruiscono un gruppo di consumi (2026-11-07) |

Guida, manuali e memoria del team si riscrivono **nel lotto DOC**, alla fine, dal censimento del §7.3 (Tid, 2026-11-06): una volta sola, sullo stato finale.

## 4. Il modello (Tid, 2026-11-06)

* `sorgente_tipo_id` → `config.sorgenti`: il tipo del **documento**.
* La chiave del **documento**, una sola delle due, secondo il `key_selector` del tipo:
  * `sorgente_id bigint`, se il documento ha chiave `id`;
  * `sorgente_uid uuid`, se ha chiave `uid`.
* `sorgente_riga` = la **riga** di quel documento; NULL se la provenienza è il documento intero.
* Una grammatica sola per tutte le tabelle, scritta da un BB unico e validata da un guard unico, che controlla anche che
  la riga appartenga al documento.
* **Unicità solo dove il dominio ha una regola**, dichiarata e sulla chiave giusta (`NULLS NOT DISTINCT`, parziale su
  `sorgente_tipo_id IS NOT NULL`). Nessuna unicità «per sorgente» generica.
* **L'import da un sistema esterno** non usa queste colonne: avrà una tabella di collegamento propria (canale, tipo
  record, id esterno `text`), come da `brief-db-articoli-obsoleto-dal` §9.2.

## 5. Che cosa NON è questo brief

* Non è il magazzino (D-5, l'ODL) né l'import esterno: li tocca solo perché usano le stesse colonne.
* Non riscrive la lineage: la semplifica, quando le grammatiche diventano una.

## 6. Da decidere (Tid)

| # | Domanda | Perché serve | Proposta DB |
| --- | --- | --- | --- |
| S-1 | **`sorgente_riga` è l'id della riga o un progressivo?** | L'offerta espansa non ha una riga sua (listino o eccezione) | l'**id della riga** quando esiste; `fn_offerta_righe_espanse` restituisce la riga d'origine |
| S-2 | **I tipi `*_RIGA` in `config.sorgenti` si ritirano?** | Col modello il tipo è il documento: PREVENTIVO_RIGA e simili diventano doppioni | sì; `config.sorgenti` prende la tabella delle righe (la `target_righe_table` della D4 di luglio) |
| S-3 | **I livelli sotto la riga** (`DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`, sorgenti di `magazzino.movimenti`) | Sono la riga di una riga: due livelli non bastano | da decidere: terzo livello, oppure il prelievo resta un tipo a sé con chiave `id` (documento = il prelievo, nessuna riga) |
| S-4 | **Le tabelle di collegamento (G3) tengono il testo?** | `pratiche_sorgenti` e `commesse_sorgenti` hanno una chiave `text` canonica con `ON CONFLICT` vivi | allineate alle colonne tipizzate, per avere una sola grammatica |
| S-5 | **Le ~2.850 righe con l'uid per un tipo `id`** si convertono? | Senza conversione restano due grammatiche | sì, conversione con l'id del documento (dato derivato, non si perde niente); la lineage perde il `CASE` |
| S-6 | **Gli orfani** (387) e le tabelle senza guard (G1, G4, G6, G7) | Nessuno impedisce una sorgente che non esiste | guard unico su tutte; gli orfani si censiscono e si decide, prima del guard |
| S-7 | **G5** (`attivita_fatturabili`, `fatture_righe`): il tipo resta COMMESSA con la riga della commessa? | È già documento + riga; l'uid è un hash d'idempotenza, non una chiave | sì al tipo e alla riga; l'hash esce da `sorgente_uid` e va in una colonna sua |

### 6.1 Stato delle decisioni (2026-11-06)

* ✅ **S-1 (Tid):** `sorgente_riga` = l'id della riga quando la riga esiste; per l'offerta, `fn_offerta_righe_espanse`
  restituisce la riga d'origine.
* ✅ **S-3 (Tid ha delegato la scelta al team DB: «fare la scelta migliore»):** un **terzo livello**,
  `sorgente_dettaglio bigint`, solo sulle tabelle che riferiscono la riga di una riga (oggi `magazzino.movimenti` e
  `movimenti_attesi`). Tipo = DDT_VENDITA, documento = la bolla, riga = la riga della bolla, dettaglio = il prelievo.
  Il «tipo a sé» (il prelievo come documento) è scartato: romperebbe la regola «il tipo è il documento», e ogni
  lettore dovrebbe risalire a mano prelievo → riga → bolla, cioè la traduzione che questo brief toglie.
  `config.sorgenti` prende la tabella del dettaglio accanto a quella delle righe (S-2).
* ✅ **S-5 (Tid):** si convertono solo le righe con l'uid di un documento padre che ha chiave `id`: si mette l'id del
  padre in `sorgente_id`. Dove il padre ha chiave `uid` (preventivo, offerta) non cambia niente.
* ✅ **S-6 (Tid):** un guard unico impedisce una sorgente che non esiste. Gli orfani sono dati di test: si puliscono
  con un one-shot manuale su dbdev prima di montare il guard (dati di test → correzione manuale, non migration, come
  nel `brief-db-guard-sorgente-polimorfa` Appendice A). Da zero non ce ne sono.
* ✅ **S-2 (Tid):** i tipi `*_RIGA` si ritirano: una riga si scrive col tipo del suo documento + `sorgente_riga`.
  `config.sorgenti` prende la tabella delle righe (e, dove c'è, quella del dettaglio, S-3): serve al guard per
  verificare che la riga esista e appartenga a quel documento.
* ✅ **S-4 (Tid):** anche `pratiche_sorgenti` e `commesse_sorgenti` passano alle due colonne tipizzate
  (`sorgente_id` / `sorgente_uid`), con lo stesso guard e gli stessi BB. Si riscrivono i loro lettori e scrittori,
  compresi gli `ON CONFLICT` vivi: `pratiche_repository.upsert_pratica_sorgente` nel BE e la funzione dei canali.
* ✅ **S-7 (Tid):** in `attivita_fatturabili` e `fatture_righe` l'impronta d'idempotenza esce da `sorgente_uid` e va in
  una colonna sua, con un nome che dice che cos'è. `sorgente_*` resta la sola provenienza (COMMESSA, la commessa, la
  sua riga). Prima si verifica chi la calcola e chi la legge: `md5(segment_key)` coincide su 2 righe di 64, quindi la
  formula è un'altra.

**Tutte le decisioni del §6 sono prese (2026-11-06).**

### 6.2 Dall'analisi critica (2026-11-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| S-8 | Le **colonne parallele** (G8: `ordini.documento_origine_*`, `contratti.offerta_id`, `ordini_righe_fulfillment`) | ✅ **Tid:** confluiscono in `sorgente_*`. Se descrivono una provenienza polimorfa, si usa sempre lo stesso meccanismo. Il censimento **segnala** che cosa non può rientrare, con il motivo; l'eccezione la decide Tid. Le regole di unicità che portano si trasferiscono sulla chiave nuova |
| S-9 | La **cancellazione** del documento sorgente (gli orfani tornano anche dopo S-6) | ✅ **Tid:** la governa la regola padre-figli della tabella padre. Se la cancellazione è permessa, le azioni conseguenti sui figli si fanno **dentro le regole DB**, non fuori. Il legame polimorfo non ha FK: il censimento dice quali `target_table` ammettono la cancellazione e che cosa succede oggi ai figli; il lotto 0 dà al meccanismo il suo lato «in uscita», derivato dal catalogo |
| S-10 | I **tipi che non sono documenti** (`EVENTO_ASSET`, `ATTIVITA`; con S-2 il tipo è «il documento») | ⏳ **da analizzare** (Tid: «si potrebbe pensare a qualche cosa che descrive altro?»). Ipotesi da verificare nel censimento: il tipo è **l'oggetto di provenienza**, e il catalogo dice se ha righe (`target_righe_table`) o no. Un oggetto senza righe (l'evento, l'attività) ha solo la chiave e `sorgente_riga` sempre NULL, verificato dal guard. Prima si misura chi scrive davvero questi tipi |
| S-7 | (precisata) l'**impronta** di `attivita_fatturabili.sorgente_uid` | ✅ **Tid:** se esiste, c'è un motivo. Si **verifica** con certezza piena che nessuno la usi (DB, BE, FE, pgTAP, e il motivo per cui è nata) **prima** di pulirla. Fatto noto: la formula è `md5(segment_key)` in `fn_emit_attivita_fatturabili_da_commessa`, che la usa per ritrovare la riga già emessa; la tabella ha anche `uq_attivita_fatturabili_commessa_attivita` |
| — | il **lotto A** di `brief-db-articoli-obsoleto-dal` (`20261105-02`, `-03`, `-14`, non ancora committati) | ✅ **Tid:** nessuna riscrittura. Si fanno YAML nuovi |

S-7 e S-10 sono analizzate nel censimento: le proposte sono D-1 e D-2 del §6.3.

### 6.3 Le decisioni che il censimento chiede (2026-11-06)

✅ **Tid, 2026-11-06:** D-1 … D-6, D-8 e D-11 come proposti. D-12: i dati di dbdev si correggono con **SQL manuali**, non con migration; il codice nel lotto che tocca l'oggetto. D-9 come proposta (Tid, 2026-11-06). D-10: il registro dei canali si ritira (Tid, 2026-11-06, dopo il §6.4); D-7 decade con lui.

| # | Domanda | Che cosa dice il censimento | Proposta DB |
| --- | --- | --- | --- |
| D-1 | **S-7, l'impronta** | Un solo lettore: `fn_emit_attivita_fatturabili_da_commessa`, che la usa per ritrovare l'attività già emessa (ripresa dopo una liberazione). Gli altri la caricano e la ignorano. È nata il 2026-02-24 (`20260224-13`), quando l'unicità stava su (tipo, uid); lo stesso giorno `20260224-42` l'ha spostata su `commessa_attivita_id`. Vedi V-3 | la ricerca si fa per `commessa_attivita_id` (FK NOT NULL, unica 1:1); l'impronta si ritira, non si sposta. Prima un pgTAP che costruisce il caso V-3 |
| D-2 | **S-10, i tipi che non sono documenti** | `EVENTO_ASSET` non lo scrive nessuno (l'operazione non esiste ancora). `ATTIVITA` come sorgente non ha scrittori: vive come genitore della FK di `tipi_entita`, per le note | il tipo è **l'oggetto di provenienza**. Il catalogo dichiara i suoi livelli (tabella delle righe e del dettaglio, ognuna con la sua FK; NULL se non ci sono), e il guard della tabella che scrive fissa il **livello minimo** (il registro di magazzino vuole sempre l'ultimo). `ATTIVITA` esce dalle sorgenti e resta in `tipi_entita`. Le alternative, con i pro e i contro, sono nella scheda magazzino §7 |
| D-3 | **Eccezioni a S-8** | Non possono confluire: `ordini_righe_fulfillment` (di vendita e d'acquisto: quantità, N:M, si ritira) e `ordini_righe.preventivo_riga_id` (consumo, si azzera all'annullo). Ridondanti: `attivita_fatturabili.sorgente_*` (copia di `commessa_id` e `commessa_attivita_id`, FK NOT NULL), `sorgente_origine_tipo_id` (un tipo senza chiave, ricavabile), `fatture_stampa_coda.sorgente_uid` (doppione di `sorgente_id`, che è già una FK vera). Può confluire perdendo la FK: `acquisti.ddt.ordine_id` | le due eccezioni restano, con la sorgente scritta accanto; i ridondanti si ritirano; `acquisti.ddt.ordine_id` confluisce, e la protezione della FK la dà il lato «in uscita» (S-9) |
| D-4 | **La bolla di riconsegna** | la testata dichiara l'ordine, le righe previste dal lotto B dichiarerebbero la riga del reso | la provenienza è il **reso**; il legame con l'ordine resta nel fulfillment |
| D-5 | **S-1 per l'offerta** | `fn_offerta_righe_espanse` non restituisce un id di riga. Le righe da eccezione ce l'hanno (`offerte_commerciali_eccezioni.id`), quelle del solo listino no. OFFERTA e COMMESSA non hanno una tabella delle righe «normale» | riga da eccezione → `sorgente_riga` = l'eccezione; riga del solo listino → NULL (la provenienza è l'offerta intera). Il catalogo dichiara come tabella delle righe le eccezioni per OFFERTA e `commesse_attivita` per COMMESSA |
| D-6 | **S-5 e le chiavi salvate** | la chiave del gruppo fatturabile e la `segment_key` contengono l'uid e sono salvate (lotti, esiti, log) | non si convertono: restano costruite con l'uid, fornito dal BB di risoluzione (§3.5) |
| D-7 | **I canali del preventivo** | portare la provenienza dell'ordine in `sorgente_*` accende in `trgfn_documenti_sync_canali` il ramo che segna CONSUMATO il canale del preventivo, oggi morto | da decidere: è il comportamento voluto? |
| D-8 | **L'unicità sull'offerta** | su `sorgente_tipo_id` il predicato parziale di `uq_ordini_v_documento_origine_offerta` e `uq_contratti_offerta_id` chiede l'id letterale del tipo (14, esplicito nel seed) | indice parziale sull'id del tipo, presidiato da un pgTAP sul seed |
| D-9 | **Eccezioni a S-6** | `pratiche.reconcile_errori` è un log scritto dentro un `EXCEPTION`; `template_documenti` e le altre colonne di solo tipo non sono una provenienza | fuori dal guard d'esistenza; il presidio di struttura si aggancia a `sorgente_id`/`sorgente_uid`, non a `sorgente_tipo_id` |
| D-10 | **Il registro dei canali** | `documenti_fatturazione_canali` non ha lettori fuori dalla funzione che lo scrive | da decidere se tenerlo. Se resta, la cancellazione della bozza si porta via il canale dentro il DB (S-9) |
| D-11 | **La provenienza di testata della fattura** | la fattura aggrega: oggi nessuno scrive `fatture.sorgente_*` | colonne presenti, NULL salvo casi futuri |
| D-12 | **I difetti vivi V-1 … V-6** (§3.6) | | si correggono nel lotto che tocca il loro oggetto; i dati di dbdev a mano, se Tid preferisce |

### 6.4 D-10 approfondito: chi impedisce oggi la doppia fatturazione (2026-11-06)

**Il registro dei canali.** È nato dal progetto di febbraio (`work-done/gestione-commesse-v2.md` §24). Lo scopo
scritto era «prevenire la doppia fatturabilità cross-canale»: un documento si fattura per una strada sola. È stata
costruita solo la metà che **registra**, cioè `trgfn_documenti_sync_canali` su preventivi, ordini, DDT e contratti,
più `fn_set_documento_canale_stato`. La metà che **blocca** non è mai stata costruita. [F] su `zeroerp_ruoli`, con
`pg_get_functiondef` (quindi anche le funzioni `BEGIN ATOMIC`), `pg_views`, `pg_policies`, `pg_trigger` e
`pg_constraint`, più grep su BE, FE e script. Della tabella si trovano solo:

* la funzione che la scrive, chiamata solo dal trigger;
* i quattro trigger;
* tre pgTAP (`test-documenti-fatturazione-canali-v1`, `test-documenti-canali-sync-v1`, `test-stati-check-scrittori-v1`);
* una riga di `storico_scope_policy.csv`.

Nessuna vista, funzione, policy, FK o codice BE/FE la legge.

**La regola che voleva dare esiste già, nel posto dove si decide che cosa va in commessa.** La tengono i
predicati di eleggibilità del push:

| Strada doppia temuta | Chi la impedisce oggi | Come |
| --- | --- | --- |
| preventivo **e** ordine nato da lui | la smistatura per riga, secondo la natura | `vw_preventivi_righe_smistabili_ordine` prende solo la merce (`fn_natura_e_merce IS TRUE`) non ancora passata a un ordine (`NOT EXISTS ordini_righe.preventivo_riga_id`). `vw_preventivi_righe_smistabili_commessa` prende solo natura NULL o con destinazione COMMESSA. I due insiemi non si toccano: MERCE → ordine, SERVIZIO_UNA_TANTUM → commessa, SERVIZIO_RICORRENTE → contratto |
| ordine **e** la sua bolla | la corsia di fatturazione, `ordini.fatturazione_trigger` | `fn_list_ordini_da_pushare` prende solo `CONFERMATO`; `fn_ddt_push_diagnosi` scarta la riga di bolla con ordine `CONFERMATO` (rank 6). Una sola delle due |
| lo stesso documento due volte | lo stato del segmento e la commessa viva | `script.fn_get_stato_push_segment = 'LIBERA'` in ogni lister; un documento in una sola commessa aperta (`fn_link_commessa_sorgente`) |

Il caso «offerta → contratto» non è una strada doppia: l'offerta non va in commessa, ci va il contratto.

**Il limite è lo stesso per le due soluzioni.** Queste regole stanno nei predicati di chi elenca, non nella madre
`fn_upsert_commessa_attivita`: un chiamante che saltasse il lister le aggirerebbe. Il registro non cambierebbe
niente, perché nessuno lo legge. Se la madre debba ricontrollare l'esclusività è un altro tema, fuori da D-10.

**Proposta DB: (a), il registro si ritira.**

* Si tolgono la tabella, i quattro trigger, `trgfn_documenti_sync_canali`, `fn_set_documento_canale_stato`, i due
  pgTAP dedicati, il passaggio in `test-stati-check-scrittori-v1`, la riga di `storico_scope_policy.csv`, le pagine
  `manual/` (oggetto ritirato = si cancella) e la sezione 24 come riferimento vivo.
* Gli orfani di V-5 e la sua grammatica G4 spariscono con lui. D-7 decade.
* Se un giorno servisse una policy di esclusività **configurabile** (lo stato `BLOCCATO` del progetto di febbraio,
  mai scritto), nascerà dove si decide l'eleggibilità, non come registro parallelo.

## 7. Dopo le decisioni

### 7.1 Il censimento (✅ fatto, 2026-11-06: Appendice)

Per **ogni** tabella del §3.1 e §3.1-bis, più le colonne parallele G8, una scheda in Appendice:

* grammatica di oggi e significato scritto (commento di colonna, manuale);
* chi **scrive** (funzioni DB, BE) e chi **legge** (funzioni, viste, BE, FE, pgTAP);
* default, CHECK, indici unici, ognuno classificato: **regola di dominio** / **idempotenza import** / **residuo**;
* guard montati;
* la cancellazione del bersaglio (S-9): la `target_table` la ammette? che cosa succede oggi ai figli?;
* il lotto di destinazione, e che cosa **non può rientrare** nel meccanismo (S-8), col motivo.

Più tre schede trasversali: i BB del §3.3 (che cosa cambia in ciascuno), i consumatori dei codici `*_RIGA` (S-2),
e l'analisi di S-10 e dell'impronta di S-7.

### 7.2 Il piano a lotti (definitivo, 2026-11-06)

Tutte le decisioni del §6 sono prese. Il piano ha otto lotti: uno trasversale, sei di famiglia e uno di chiusura.

#### Le regole che valgono per ogni lotto

* **Solo YAML nuovi.** I changeSet del lotto A (`20261105-*`) non si riscrivono. DDL e corpi si prendono dalla doc
  auto-generata.
* **L'ordine dentro il lotto è sempre lo stesso:**
  1. colonne nuove;
  2. conversione dei dati, nello stesso changeSet della colonna: è la migrazione del modello, non una correzione;
  3. guard unico montato;
  4. scrittori e lettori riscritti sui BB;
  5. pgTAP che **costruiscono** i casi (documento intero, riga, dettaglio, chiave sbagliata, riga di un altro
     documento, bersaglio cancellato);
  6. ritiro dei tipi e delle colonne vecchie.
* **Il ritiro di un tipo viene per ultimo.** Il guard di oggi rifiuta i tipi spenti (`attivo = true`), quindi un
  tipo spento prima della conversione rompe ogni UPDATE sulle sue righe. In `config.tipi_entita` prima
  `is_sorgente = false`, poi il ritiro dalle sorgenti: l'entità (giornale, note, errori) resta.
* **I dati sbagliati di dbdev si correggono con SQL manuali** (D-12), prima di montare il guard: orfani (S-6), V-6.
  Da zero (CI) non ci sono.
* ⛔ **Prima tutto il DB, poi il BE una volta sola** (Tid, 2026-11-06: «evitiamo i palleggi DB → BE → DB → BE»).
  I lotti 0 … Z si fanno tutti, uno dopo l'altro, senza fermarsi ad aspettare il BE. Fra un lotto e l'altro il BE
  si può rompere: è accettato (il progetto non è in produzione). I test Django della CI saranno rossi fino al lotto
  BE, e va dichiarato a ogni PR.
* **La richiesta BE/FE si accumula** nel §8 durante i lotti DB, con il percorso intero (firma, colonna, valore,
  codice d'errore) di ogni cambio, e si consegna **una volta**, completa, dopo il lotto Z.
* **Nei lotti DB** si scrivono solo i commenti di colonna e di funzione, che fanno parte del changeSet. Guide,
  manuali e doc di sviluppo si aggiornano tutti nel **lotto DOC**, dal censimento del §7.3.

#### Lotto 0 — il meccanismo (trasversale, additivo: non rompe niente)

* **Catalogo.** In `config.sorgenti`: per ogni tipo i suoi livelli, cioè la tabella delle righe e quella del
  dettaglio, ognuna con la sua colonna FK verso il livello sopra. Sono dichiarate (non ricavate da `pg_constraint`)
  e un pgTAP verifica che la FK esista. NULL = il livello non c'è (D-2). OFFERTA → le eccezioni; COMMESSA →
  `commesse_attivita` (D-5). La mappa completa è nella scheda pratiche-documenti-BB §C.2.
* **BB che scrive.** Riceve il tipo e una chiave qualsiasi (id o uid) e restituisce la coppia giusta. Nasce da
  `vendite.fn_link_commessa_sorgente`, che ha già quella forma, ed estratto in `script`.
* **BB che risolve.** Da tipo + chiave restituisce id, uid e numero del documento. Nasce da
  `vendite.fn_get_sorgente_documento_ref` e `config.fn_sorgente_tabella`. Le copie si ritirano nello stesso giro
  (regola del 2).
  * ⭐ **Ponte di transizione, dichiarato.** Finché una famiglia non è convertita, il BB che risolve sa leggere
    anche la sua grammatica vecchia, e la sa leggere **lui solo**. I lettori trasversali (lineage, legami, ritiro dei
    legami, push, diagnosi DDT, resi) si riscrivono **una volta** in questo lotto, sul BB, e non si ritoccano a ogni
    lotto. Ogni lotto di famiglia toglie dal ponte il suo ramo; il lotto di chiusura verifica che il ponte sia vuoto.
* **Guard unico.** Controlla: una sola chiave, quella che dice il catalogo; il documento esiste; la riga appartiene
  al documento; il dettaglio appartiene alla riga. Prende per argomento il **livello minimo** della tabella (il
  registro di magazzino vuole sempre il dettaglio). Il CHECK di forma (tutto NULL o tipo + una chiave) va per
  tabella.
* **Lato «in uscita» (S-9).** Un BB montato sui bersagli, derivato dal catalogo, applica la regola padre-figli
  della tabella padre: o blocca la cancellazione, o fa le azioni conseguenti sui figli polimorfi.
* **Presidi.**
  * Orfani: `dbops.fn_sorgenti_orfane` riscritta a tre livelli. Il perimetro è ogni tabella con
    `sorgente_id`/`sorgente_uid`, non solo quelle col guard.
  * Struttura, in CI: una tabella con `sorgente_id`/`sorgente_uid` senza il guard unico è rossa. Non si aggancia a
    `sorgente_tipo_id` (D-9). Unica esenzione dichiarata: `pratiche.reconcile_errori`.
* **Le colonne nuove dove mancano**, nullable, vuote: `sorgente_id` dappertutto; `sorgente_riga` su
  `commesse_attivita`; `sorgente_dettaglio` su `magazzino.movimenti` e `movimenti_attesi`. Sono additive: i lotti
  dopo le riempiono.

##### Lotto 0, i giri (team DB, 2026-11-06)

Il lotto 0 è grande: si fa in **tre giri**, ognuno additivo e provato da solo. Il primo non tocca niente di vivo
tranne due funzioni che ritirano la loro copia (regola del 2).

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **0.1** | catalogo dei livelli, colonne nuove, BB che risolve (con il ponte), BB che scrive, guard unico, codici | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |
| **0.2** | lato «in uscita» (S-9) montato sui bersagli; presidio degli orfani a tre livelli; presidio di struttura in CI | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |
| **0.3** | i lettori trasversali sul BB che risolve (lineage, legami, ritiro dei legami, push, diagnosi DDT, resi) e `script.fn_get_sorgente_emittente_sr_id` | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |

**Il giro 0.1, le scelte** (nomi e grammatica li ha scelti il team DB; nessuna è un cambio di modello):

* **Catalogo.** `config.sorgenti` prende `righe_table`, `righe_fk_column`, `dettaglio_table`, `dettaglio_fk_column`
  (`regclass` + `varchar(63)` con CHECK d'identificatore, come `label_selector`), con i CHECK di coppia e di
  gerarchia. I valori nel CSV, mirror `20251002-21` esteso in place. La mappa è quella della scheda §C.2, più
  `DISTINTA_INCASSO` → `pagamenti.vendite_contabili_righe.contabile_id`. ⚠️ Fuori dalla mappa, dichiarato:
  `ATTIVITA_CONSUMI`, `EMAIL` (documenti senza righe), i `*_RIGA`, `DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`,
  `EVENTO_ASSET`, `ATTIVITA`.
* **`config.fn_sorgente_livelli(tipo)`**: schema, nome e oid di documento, righe e dettaglio da `pg_class`, più
  «il documento ha l'uid?» e «la colonna dell'etichetta esiste?». `config.fn_sorgente_tabella` ci si appoggia (regola
  del 2, firma invariata).
* **BB che risolve**: `script.fn_sorgente_documento(tipo, sorgente_id, sorgente_uid)` → `(documento_id,
  documento_uid, documento_numero)`. Una riga sempre, mai un errore, INVOKER. Legge la chiave che riceve
  (la coerenza chiave/tipo è del guard). **Ponte**: `script.fn_sorgente_documento_da_chiave(tipo, chiave text)`,
  per le grammatiche che scrivono la chiave come testo o l'uid per un tipo `id`. `vendite.fn_get_sorgente_documento_ref`
  diventa un passaggio sul ponte (firma e `ROWS 1` invariati).
* **BB che scrive**: `script.fn_sorgente_chiave(tipo, chiave text)` → `(sorgente_id, sorgente_uid)`, la coppia
  giusta per il `key_selector`; traduce una chiave dell'altra specie, solleva con i codici della normalizzazione di
  `fn_link_commessa_sorgente`, che ora lo chiama. La riga e il dettaglio non passano di qui: li verifica il guard.
* **Guard unico**: `script.trgfn_guard_sorgente(livello_minimo, azione_cancellazione)`. Prima la **forma**, dal
  catalogo (tipo attivo, una sola chiave, livelli previsti, livello minimo limitato a quelli del tipo), poi
  l'**esistenza** (documento col BB che risolve, riga del documento, dettaglio della riga). Le colonne da
  `to_jsonb(NEW)`: una tabella senza `sorgente_dettaglio` monta lo stesso guard. Gli argomenti li legge
  `script.fn_sorgente_guard_argomenti`, la stessa funzione che userà il giro 0.2 su `pg_trigger.tgargs`.
  Livelli: `DOCUMENTO` (default) | `RIGA` | `DETTAGLIO`; azione: `BLOCCA` (default) | `CANCELLA`.
* **Codici nuovi**, tutti `TECNICO` (la provenienza la scrive il codice, non un form):
  `E_SORG_CHIAVE_NON_CONFORME`, `E_SORG_RIGA_NON_DEL_DOCUMENTO`, `E_SORG_DETTAGLIO_NON_DELLA_RIGA`,
  `E_SORG_LIVELLO_NON_PREVISTO`, `E_SORG_LIVELLO_MANCANTE`. Riusati: `E_SORG_CONF`, `E_SORG_FORMATO`,
  `E_SORG_KEY_MISSING`, `E_SORG_NORM_NON_RISOLTA`, `E_SORG_NOT_FOUND`.
* **Colonne non aggiunte**, dichiarato: `documenti_fatturazione_canali` (si ritira nel lotto T),
  `attivita_fatturabili` (le sue `sorgente_*` si ritirano nel lotto C), `fatture_stampa_coda` (ha già
  `sorgente_id`).

**Differenze di comportamento del giro 0.1** (dichiarate; la prova sotto dice chi le vede):

* `fn_get_sorgente_documento_ref`: un id per un tipo a chiave `uid` (il preventivo) ora si risolve; un id per un
  tipo a chiave `id` si risolve solo se il documento esiste ed è visibile.
* `fn_link_commessa_sorgente`: un id per un tipo `uid` si traduce nel suo uid (prima `E_SORG_FORMATO`); un uuid con
  le maiuscole per un tipo `id` è `E_SORG_FORMATO` (prima si traduceva); un id inesistente solleva
  `E_SORG_NOT_FOUND` già nella porta, non dal guard all'INSERT.

**I changeSet del giro 0.1:** `20261106-04` (catalogo), `-05` … `-09` (colonne: vendite, acquisti, magazzino,
pratiche, documenti), `-10` (`fn_sorgente_livelli`), `-11` (BB che risolve e ponte), `-12` (BB che scrive), `-13`
(`fn_get_sorgente_documento_ref`), `-14` (`fn_link_commessa_sorgente`), `-15` (guard unico), `-16` (80_data:
l'esenzione del guard nel registro dei riferimenti morti); `sorgenti.csv` e il loader `20251002-21`;
`codici_errore.csv`, `messaggi_errore.csv`. pgTAP nuovi: `config/test-sorgenti-livelli-v1`,
`script/test-sorgente-documento-e-chiave-v1`, `script/test-guard-sorgente-v1`.

⚠️ **Il guard nasce senza tabelle**, e `dbops/test-riferimenti-morti-v1` (test 3) segnala una funzione trigger che
nessuno monta. Per la durata del lotto 0 è un debito dichiarato: `20261106-16` lo scrive in
`dbops.riferimenti_morti_esenzioni`, come fece `20260804-65` per la sorella `_tipizzata`. **Il lotto R, che lo monta
per primo, toglie la voce nello stesso giro** (precedente `20260915-18`): altrimenti il test 4 dello stesso presidio
è rosso.

**La prova del giro 0.1** (2026-11-06, scratch `zeroerp_ruoli`, come `zeroerp_owner`, tutto in una transazione
annullata; lo scratch è stato verificato pulito dopo, md5 dei corpi toccati invariati):

* l'SQL **estratto** dai sedici changeSet, più l'upsert del CSV delle sorgenti rifatto su **tutte** le 29 righe
  (nessuna irriscrivibile) e i cinque codici dai due CSV: gira intero;
* i tre pgTAP nuovi in coda: 12/12, 27/27, 24/24. Mutazione: una `righe_fk_column` sbagliata nel catalogo fa
  rossi il 3 e il 5 di `test-sorgenti-livelli-v1`;
* **prima/dopo** su 48 pgTAP che chiamano direttamente `fn_link_commessa_sorgente`, `fn_get_sorgente_documento_ref`,
  `fn_sorgente_tabella` o leggono il catalogo delle sorgenti: 618 ok e 5 rossi **identici** nelle due corse. I 5
  sono test di scope, rossi da owner per costruzione (la RLS non c'è): `script/test-fn-available-actions-ddt-reason-catch-all-v1`
  16, `pagamenti/test-distinta-numerazione-registro-v1` 18-19, `vendite/test-fn-af-merce-per-riga-chiusura-v1` 13,
  `vendite/test-vw-situazione-merce-ordine-v1` 11;
* i presidi su tutte le funzioni e tutti i codici, prima/dopo: `dbops/test-riferimenti-morti-v1` 12/12 (con
  `-16`), `script/test-catalogo-messaggi-errore-completo`, `config/test-codici-errore-identita`, `-obsoleto-dal`,
  `dbops/test-vw-codici-errore-valore-atteso`, `-motivo-nominato`: tutti verdi;
* guardrail statici (`scripts/guardrail_*.py`, licenze, segreti): verdi. Il rosso di `check_i18n_keys`
  (`vendite.righe.articolo_reason.obsoleto`) è preesistente, del lotto A di `brief-db-articoli-obsoleto-dal`.

Non coperto dalla prova, e resta di Tid: l'apply, la corsa dei pgTAP **come applicazione** (la RLS), la baseline.

**Il giro 0.2, le scelte** (team DB, 2026-11-06):

* **Chi monta il guard**: `script.fn_sorgente_guard_montaggi()`, da `pg_trigger` con la grammatica degli argomenti
  del guard (`fn_sorgente_guard_argomenti` su `dbops.fn_trigger_argomenti`). Delle tabelle temporanee tiene solo quelle
  della sessione, leggibili da chi chiede. La leggono i tre pezzi sotto.
* **Lato «in uscita» (S-9)**: `script.trgfn_sorgente_in_uscita()`, `AFTER DELETE FOR EACH STATEMENT` con la tabella di
  transizione `vecchie`, montato su **ogni** tabella che il catalogo dichiara come documento, righe o dettaglio. Per
  ogni figlio (una tabella che monta il guard unico) guarda la colonna del livello: `sorgente_id`/`sorgente_uid` secondo
  il `key_selector`, `sorgente_riga`, `sorgente_dettaglio`. **L'azione la dichiara il figlio**, nel secondo argomento
  del suo guard, come un `ON DELETE`: `BLOCCA` → `E_SORG_ORIGINE_REFERENZIATA` (`CONFLITTO_STATO`, il conteggio nella
  frase); `CANCELLA` → i figli se ne vanno con l'origine. Prima si contano i figli che bloccano, poi si cancella: se
  uno blocca, non si cancella niente. **SECURITY DEFINER**, come una FK: vede anche i figli che la RLS nasconde a chi
  cancella. Nel lotto 0 nessun figlio vero: gira e non trova niente.
* **Il montaggio deriva dal catalogo**: `dbops.fn_sorgente_converge_uscita()` monta il trigger dove il catalogo lo
  chiede e lo toglie dove non lo chiede più; la lancia `90_end/20261106-21` (`runAlways`), dopo i seed. Una riga nuova
  di `config.sorgenti` converge alla migrazione successiva, senza changeSet suo. Nome
  `trg_[<schema>_]<tabella>_a10_sorgente_in_uscita_dlt`.
* **Presidio degli orfani** (`dbops.fn_sorgenti_orfane_perimetro`, `fn_sorgenti_orfane`, `vw_sorgenti_orfane`,
  ricreate: cambiano le colonne). Il perimetro è **ogni** tabella con `sorgente_tipo_id` e `sorgente_id` o
  `sorgente_uid` (fuori lo storico), con la sua **grammatica**, dal guard che monta: `UNICO` (a tre livelli),
  `MODELLO_A` (il guard tipizzato), `TESTUALE` (nessun guard: chiave in `sorgente_uid`, letta con la regola del ponte).
  Esenzioni dichiarate in colonna, col motivo: dagli orfani `attivita_fatturabili` e `fatture_righe` (G5:
  `sorgente_uid` non è la chiave del documento) e `reconcile_errori` (log); dal guard solo `reconcile_errori` (D-9).
  La vista ha in più `grammatica`, `livello`, `sorgente_id`, `sorgente_dettaglio`.
* **Presidio di struttura**: `dbops/test-sorgenti-struttura-v1`. Le tabelle del perimetro senza il guard unico sono
  un **elenco chiuso** (27 oggi, per lotto): ogni lotto di famiglia ne toglie le sue nello stesso giro, una tabella
  nuova con la provenienza e senza guard fa rosso, il lotto Z lo trova vuoto.

⚠️ **Il perimetro più largo accende il presidio su dbdev.** Misurato dopo l'apply (dbdev, 2026-11-06, come
`zeroerp_owner`: fatto datato): `dbops.vw_sorgenti_orfane` ha **387 righe, tutte in
`vendite.documenti_fatturazione_canali`** (TESTUALE, livello DOCUMENTO): PREVENTIVO 352, DDT_VENDITA 16, CONTRATTO 14,
ORDINE_VENDITA 5. Sono i 387 del §3.2, canali di documenti cancellati (V-5). Nessun'altra tabella del perimetro ha
orfani. Da zero non ce ne sono.

**La correzione dei dati** (S-6, D-12: SQL a mano, non migration):
[`sql-una-tantum-sorgenti-orfane-canali.sql`](sql-una-tantum-sorgenti-orfane-canali.sql). In una transazione cancella
le **sole** righe che il presidio indica (per id, dalla vista), poi verifica che il presidio sia vuoto e altrimenti
annulla tutto. Si può: nessuna FK punta al registro, nessuno lo legge (§6.4), sul `DELETE` gira solo lo storico
(la cancellazione resta tracciata). Provato su dbdev con `ROLLBACK` al posto del `COMMIT`: 387 cancellati, presidio
vuoto. ✅ **Eseguito da Tid su dbdev il 2026-11-06**: `dbops.vw_sorgenti_orfane` è vuota. Il test 11 di `dbops/test-sorgenti-orfane-v1` non conta più «esattamente
uno» (era una misura della popolazione di dbdev): confronta il contatore con la vista.

**I changeSet del giro 0.2:** `20261106-17` (`fn_sorgente_guard_montaggi`), `-18` (`trgfn_sorgente_in_uscita`),
`-19` (`dbops.fn_sorgente_converge_uscita`), `-20` (presidio degli orfani), `-21` (90_end, la convergenza);
`codici_errore.csv` e `messaggi_errore.csv` (`E_SORG_ORIGINE_REFERENZIATA`). pgTAP: nuovi
`script/test-sorgente-in-uscita-v1`, `dbops/test-sorgenti-struttura-v1`; riscritto `dbops/test-sorgenti-orfane-v1`.

**La prova del giro 0.2** (2026-11-06, scratch `zeroerp_ruoli` col giro 0.1 applicato, come `zeroerp_owner`, in
transazione annullata): l'estratto gira, la convergenza monta il trigger su tutte le tabelle del catalogo;
`test-sorgente-in-uscita-v1` 14/14, `test-sorgenti-orfane-v1` 12/12, `test-sorgenti-struttura-v1` 5/5, e i tre pgTAP
del giro 0.1 ancora verdi sopra l'estratto. **Prima/dopo** su 45 pgTAP (quelli che cancellano da una tabella del catalogo, dove ora gira il lato «in uscita», più
i presidi trasversali: riferimenti morti, `search_path` delle DEFINER, il pin di `test-porta-ledger-v1`, catalogo dei
messaggi, codici, `security_invoker` delle viste): 693 ok e 8 rossi **identici** nelle due corse. Gli 8 sono test di
permesso come applicazione, rossi da owner per costruzione (`magazzino/test-porta-ledger-v1` 4-7,
`magazzino/test-documenti-interni-guard-v1` 7, 8, 11, `vendite/test-ddt-righe-evase-dall-ordine-v1` 43).

Non coperto, e resta di Tid: l'apply, la corsa come applicazione, la baseline.

**Il giro 0.3, le scelte** (team DB, 2026-11-06; nessuna è un cambio di modello):

* **Due strumenti, non uno.** «Sul BB che risolve» vale per chi non sa in quale tabella sta il documento: il tipo è
  polimorfo, e la risposta la dà `script.fn_sorgente_documento` (o il ponte, se la chiave arriva come testo). Chi invece
  sa già dove cercare (una bolla viene da un ordine, un reso da una bolla) non ha bisogno del BB: gli serve la
  **regola d'incontro del modello**, `(doc.id = x.sorgente_id OR doc.uid = x.sorgente_uid)`. È vera nelle due
  grammatiche di oggi e anche nel modello finale (il guard unico vuole una sola chiave). È il join della chiave
  polimorfa, come quello di una FK: si scrive in linea, non dietro una funzione, perché il planner la deve portare sugli
  indici (`id`, `uid`, `(tipo, sorgente_*)`). Una funzione per riga nella lineage, che è insiemistica e seminata per
  chiave, avrebbe spento i piani.
* **Il perimetro: chi si romperebbe in silenzio.** I lettori delle testate G1 (bolla → ordine, reso → bolla), che il
  lotto T converte all'id (S-5), e i lettori polimorfi che traducevano tipo per tipo:
  * **regola d'incontro:** `fn_documento_lineage_archi` (archi H e R, nei rami «tutti» e in quelli seminati),
    `fn_ddt_trigger_ordine_testata` e i suoi due chiamanti (diagnosi del push, check di emissione),
    `fn_ddt_vincoli_cliente` e i suoi due chiamanti (guard del cliente, capability), `trgfn_ddt_normalize`, i quattro
    trigger del reso (`normalize`, `default_magazzino`, `guard_cliente_ddt`, `guard_ddt_consegnato`), `fn_conferma_reso`,
    `fn_annulla_reso`, il lato che legge di `fn_genera_ddt_riconsegna`, il motivo 1 di `fn_check_ordine_annullabile`,
    `SALTA_CON_SORGENTE` di `trgfn_default_emittente_fiscale`;
  * **BB che risolve:** `fn_documento_lineage_legami` (il `CASE` B/E/F/U → il ponte), `fn_documento_legami` (cinque
    letture per tabella → una), `fn_documento_ritira_legami` (due → una), `script.fn_get_sorgente_emittente_sr_id`
    (firma nuova sulle colonne del modello, che risolve col BB; la testuale controlla la forma e le passa).
* **Firme.** `fn_ddt_trigger_ordine_testata` e `fn_ddt_vincoli_cliente` prendono `sorgente_id` **in coda**, `DEFAULT
  NULL`. La firma nuova nasce accanto alla vecchia, i chiamanti passano alla nuova, poi la vecchia si ritira: la diagnosi
  è `BEGIN ATOMIC` e la sua dipendenza va spostata prima del `DROP`. Indici nuovi `ix_ddt_v_sorgente_id`,
  `ix_resi_sorgente_id` (parziali, oggi vuoti), gemelli di quelli sull'uid.
* **Le firme ripulite.** Dove l'ultimo YAML aveva perso il `%TYPE` (copiato dall'auto-gen), la firma riprende
  l'ancoraggio: `fn_check_ordine_annullabile(vendite.ordini.id%TYPE)` e `fn_available_actions_ddt(vendite.ddt.id%TYPE)`
  (lo stesso tipo risolto: la firma non cambia). `SECURITY INVOKER` diventa esplicito dove mancava.

**Che cosa resta ai lotti, dichiarato** (cambia con la colonna, o è il lato che scrive):

* **lotto C:** il confronto con `commesse_attivita.sorgente_uid` e `commesse_sorgenti.sorgente_uid` (G3/G4 testuali)
  in lineage, legami, ritiro e `fn_check_sorgente_chiudibile`; gli archi B/E/F/U della lineage su `commesse_sorgenti`; i
  lister del push (scrivono la chiave G4 per la madre); `fn_resolve_termini_pagamento` (legge l'uid della riga di
  commessa); la firma testuale di `fn_get_sorgente_emittente_sr_id`, coi suoi due chiamanti;
* **lotto T:** le viste di lista `vw_ddt_lista`, `vw_resi_lista` (espongono `sorgente_uid` al BE: è un contratto, e
  cambia con la conversione); le colonne ferme della capability (`c_non_edit_draft`) e gli argomenti del lock della
  testata (`trgfn_doc_testata_lock_fuori_bozza`), che prendono `sorgente_id` insieme; la sorgente che **scrivono**
  `fn_genera_ddt_da_ordine` e `fn_genera_ddt_riconsegna` (D-4) e il registro dei canali (si ritira);
* **resi nella grammatica del lotto T:** `resi.sorgente_uid` è `NOT NULL`, quindi un reso col solo `sorgente_id` oggi
  non si può costruire: i suoi lettori sono provati dall'equivalenza sulla popolazione, e il lotto T li ripassa.

**I changeSet del giro 0.3:** `20261106-22` (indici), `-23` (emittente della sorgente), `-24` … `-27` (ordine di
testata: firma nuova, diagnosi, check di emissione, ritiro della firma vecchia), `-28` … `-31` (vincoli del cliente:
firma nuova, guard, capability, ritiro), `-32` (normalize della bolla), `-33` … `-36` (i quattro trigger del reso),
`-37` … `-39` (conferma, annullo, ri-consegna), `-40` (annullabilità dell'ordine), `-41` (emittente di default), `-42`
(legami), `-43` (ritiro dei legami), `-44` (legame della lineage), `-45` (archi della lineage). pgTAP: nuovo
`vendite/test-sorgente-testate-due-grammatiche-v1`; aggiornato `vendite/test-fn-ddt-trigger-ordine-testata-v1` (test
1, la firma). Nessun codice nuovo, nessun CSV.

**La prova del giro 0.3** (2026-11-06, come `zeroerp_owner`, sempre in transazione annullata; scratch e dbdev
verificati intatti dopo):

* **i corpi di partenza sono quelli vivi:** per ognuno dei 22 oggetti riscritti, il `CREATE` dell'ultimo YAML rieseguito
  sullo scratch dà lo stesso `pg_get_functiondef` del vivo. Unica eccezione, dichiarata: a
  `fn_get_sorgente_emittente_sr_id` mancava `pg_temp` nel `search_path`, che gli ha dato `20261103-04`;
* **l'estratto** dei 24 changeSet gira intero sullo scratch `zeroerp_ruoli` e su dbdev; `plpgsql_check` sulle 17
  funzioni plpgsql toccate non dà errori (solo gli avvisi già noti: STABLE che chiama `fn_log_and_raise_error`, due
  variabili inutilizzate preesistenti in `fn_genera_ddt_riconsegna`);
* **equivalenza prima/dopo su tutta la popolazione di dbdev**, `EXCEPT ALL` nei due versi, zero differenze: archi della
  lineage, tutti (1616) e seminati da ogni ordine, bolla e reso (1371); il legame di ogni arco (1616); diagnosi del push
  (323); check di emissione e ordine di testata di ogni bolla (250); vincoli del cliente (427); annullabilità di ogni
  ordine (592); legami di ogni documento dei sei tipi (1979); emittente di ogni riga di `commesse_sorgenti` (876). I
  numeri sono fatti datati di dbdev: dicono che la popolazione di oggi non vede differenze, non che il ramo nuovo è
  provato (quello lo prova il pgTAP sotto);
* **tempi della lineage su dbdev**, prima → dopo, stessa sessione: tutti gli archi 7,9 → 5,2 ms (a cache calda); semi di
  tutti gli ordini 903 → 789 ms; semi di tutte le bolle 316 → 323 ms. Invariati;
* **il ramo nuovo si costruisce**: `vendite/test-sorgente-testate-due-grammatiche-v1` porta una bolla nella grammatica
  del lotto T (l'ordine nel solo `sorgente_id`) e la fa leggere a ogni lettore: 16/16. Mutazioni: senza l'estratto
  cade al test 2; con l'estratto e il `trgfn_ddt_normalize` di prima la bolla nuova (test 10) è rifiutata dal guard del
  cliente;
* **regressione prima/dopo su 122 pgTAP** (chi nomina un oggetto toccato, i builder di bolla e reso, chi scrive bolle e
  resi): 1697 → 1713 ok; i 20 rossi sono **identici** riga per riga nelle due corse, tutti di scope o di permesso, rossi
  da owner per costruzione (es. `script/test-guard-emittente-senza-utente` 4, 5, 9, 10; `vendite/test-esecutivi-ba-coppia-v1`
  39 «rosso da owner, verde come app»). Le sole differenze sono le attese: il test nuovo e il test 1 di
  `test-fn-ddt-trigger-ordine-testata-v1`, che ora vuole la firma con `sorgente_id`;
* guardrail statici (`scripts/guardrail_*.py`, licenze): verdi.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il
2026-11-06:** apply dei 24 changeSet, pgTAP verdi.

⚠️ **Un rosso emerso alla corsa, e non dal giro 0.3:** il presidio sull'elenco della copia
(`vendite/test-fn-crea-revisione-preventivo-riga-completa-v1`, test 1) era rosso già dal lotto A, per le quattro
colonne `sorgente_*` di `preventivi_righe` (`20261105-02` e `20261106-05`) che nessuno aveva censito. La regressione
del giro non lo comprendeva, perché il file non nomina nessun oggetto toccato. Le colonne sono dichiarate escluse nel
test, con il rinvio al lotto R: la provenienza della revisione si scrive (revisione di partenza), non si ricopia
dalla rev N. Il debito è scritto nel lotto R.

#### Lotto R — righe di vendita (primo: sblocca il lotto B di `brief-db-articoli-obsoleto-dal`)

* **Le tabelle:** `preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe` (colonne del lotto A, vuote)
  e `fatture_righe` (`DROP DEFAULT 0`, l'indice unico `(tipo, uid)` ritirato). Le righe già nate da un documento,
  dove l'origine si ricava in modo esatto dai legami salvati, prendono la provenienza (giro R.1, sotto).
* **I verbi del lotto B** si scrivono direttamente sul modello, con il BB che scrive:
  * offerta: riga da eccezione → l'eccezione, riga del solo listino → NULL (D-5);
  * riconsegna: la provenienza è il reso (D-4).
* **Le copie esplicite delle righe si allineano nello stesso giro.** Il presidio
  `vendite/test-fn-crea-revisione-preventivo-riga-completa-v1` dichiara escluse le quattro colonne `sorgente_*` di
  `preventivi_righe`, con il rinvio a questo lotto (rev 2026-11-06). Prima era rosso dal lotto A, perché nessuno le aveva
  censite. Quando `fn_crea_revisione_preventivo` scrive la provenienza, le quattro esclusioni si tolgono: altrimenti
  il test 2 le segnala come stantie. Per le altre copie esplicite (push, DDT, riconsegna, contratto) il censimento
  si fa con `prosrc ~* 'INSERT\s+INTO\s+vendite\.<righe>\s*\('`.
* **Il primo montaggio del guard unico** toglie la sua voce da `dbops.riferimenti_morti_esenzioni` (messa da
  `20261106-16`), nello stesso giro.
* **Restano accanto alla sorgente** (D-3): `ordini_righe.preventivo_riga_id` e `ordini_righe_fulfillment`. Il commento
  di `ddt_righe` che li dava per «lo stesso fatto» si corregge.
* **Alla fine:** ritiro dei sei tipi `*_RIGA` di vendita (nessuna funzione, né BE né FE li nomina), delle loro voci di
  `tipi_entita` come sorgente, e delle chiavi di traduzione.

##### Lotto R, i giri (team DB, 2026-11-06)

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **R.1** | i residui «import» tolti, le righe derivate esistenti convertite, il CHECK di forma, gli indici «chi deriva da X», i sei verbi che scrivono la provenienza, il guard unico al posto del tipizzato, l'esenzione del registro dei riferimenti morti tolta | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |
| **R.2** | ritiro dei sei tipi `*_RIGA` di vendita (`config.tipi_entita.is_sorgente = false`, poi `config.sorgenti`); i COMMENT del giro 0.3 riscritti al presente | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |

R.2 viene dopo perché il ritiro di un tipo va per ultimo (regole di ogni lotto), e perché il guard tipizzato, che
ancora li accetta, resta montato sul magazzino fino al lotto M.

**Il giro R.1, le scelte** (team DB, 2026-11-06; nessuna è un cambio di modello):

* **Il BB che scrive, citato per codice:** `script.fn_sorgente_provenienza(codice_interno, chiave)` → (tipo,
  `sorgente_id`, `sorgente_uid`). Delega a `script.fn_sorgente_chiave` e solleva `E_SORG_CONF` su un codice che non è
  un tipo. Sei verbi avrebbero ripetuto la lettura del tipo per codice e il controllo (regola del 2). Ogni verbo lo
  chiama **una volta per documento**, prima del ciclo; `sorgente_riga` la mette lui, riga per riga, nello STESSO
  INSERT.
* **Che cosa scrivono i sei verbi** (S-1, D-4, D-5):

  | Verbo | Tabella | Tipo | `sorgente_riga` |
  | --- | --- | --- | --- |
  | `vendite.fn_crea_revisione_preventivo` | `preventivi_righe` | PREVENTIVO (la rev N) | la riga copiata |
  | `vendite.fn_push_preventivo_a_ordine` | `ordini_righe` | PREVENTIVO | la riga (= `preventivo_riga_id`, che resta accanto, D-3) |
  | `vendite.fn_genera_ordine_da_offerta` | `ordini_righe` | OFFERTA_COMMERCIALE | l'eccezione; NULL per la riga del solo listino |
  | `vendite.fn_push_offerta_a_contratto` | `contratti_righe` | OFFERTA_COMMERCIALE | l'eccezione copiata |
  | `vendite.fn_genera_ddt_da_ordine` | `ddt_righe` | ORDINE_VENDITA | la riga d'ordine |
  | `vendite.fn_genera_ddt_riconsegna` | `ddt_righe` | RESO_VENDITA | la riga del reso |

  La revisione **non ricopia** la provenienza della rev N: quella dice da dove veniva la rev N.
* **`vendite.fn_offerta_righe_espanse` prende `eccezione_id`** in coda al RETURNS TABLE (S-1: «restituisce la riga
  d'origine»). DROP + CREATE; i due chiamanti plpgsql (`script.fn_check_righe_offerta_in_ordine`,
  `vendite.fn_genera_ordine_da_offerta`) leggono le colonne con un elenco di alias posizionale e lo allineano.
* **Il guard unico** sostituisce il tipizzato sulle quattro tabelle, con lo stesso nome (l'ordine fra i BEFORE ROW
  non cambia), su INSERT e UPDATE OF le quattro colonne. Livello minimo: RIGA su preventivi, bolle e contratti;
  DOCUMENTO sugli ordini, perché la riga del solo listino cita l'offerta intera. Azione alla cancellazione
  dell'origine: **BLOCCA** su tutte, come una FK: una riga d'origine o un documento citati non si cancellano
  (`E_SORG_ORIGINE_REFERENZIATA`).
* **CHECK di forma** `chk_<tabella>_sorgente_forma` sulle quattro: tutto NULL, o il tipo con una sola chiave. Non su
  `fatture_righe`: la sua `sorgente_uid` è ancora l'impronta (G5), e passa al lotto C con `attivita_fatturabili`
  (il presidio di struttura la segna così).
* **I residui «import» se ne vanno:** `DEFAULT 0` di `sorgente_riga` su `ordini_righe` e `fatture_righe`; gli indici
  unici `uq_ordini_righe_v_sorgente_fk` e `uq_fatture_righe_v_sorgente_fk`. Il primo avrebbe vietato due righe
  dallo stesso preventivo o dalla stessa offerta.
* **Otto indici non unici «chi deriva da X»**, parziali, (tipo, chiave) e (tipo, riga): li usa il lato «in uscita»
  a ogni cancellazione dell'origine.
* **Le righe esistenti nate da un documento prendono la provenienza**, dove l'origine si ricava in modo esatto da un
  legame salvato: ordini dal preventivo (`preventivo_riga_id`), bolle dall'ordine (`ordini_righe_fulfillment`),
  riconsegne dal reso (`resi_righe_riconsegne`, che vince sul fulfillment, D-4); solo con un'origine sola. È la
  migrazione del modello, nel changeSet della forma (regole di ogni lotto, punto 2), coi trigger della tabella spenti
  e riaccesi come erano. Gli 0 di `ordini_righe.sorgente_riga` (riga che non esiste) diventano NULL. Da zero le
  tabelle sono vuote.
* **I COMMENT riscritti seguono `linee-guida-sql` §5d** (al presente, senza brief, rev, changeSet, misure): quelli
  delle otto funzioni toccate e delle sedici colonne sono riscritti interi, non con un prefisso.

**Che cosa resta, dichiarato:**

* **Revisioni del preventivo e contratti dall'offerta già esistenti** restano senza provenienza: nessun legame
  salvato dice da quale riga vengono (un abbinamento per articolo non sarebbe esatto). Le righe nuove la portano.
* **La testata della riconsegna** dichiara ancora l'ordine (order-backed) o il reso: D-4 la porta al reso nel lotto T,
  con le testate.
* **`fatture_righe`**: guard e CHECK al lotto C (G5).
* ✅ **Deciso (Tid, 2026-11-06, «accetto la tua proposta»): la proposta DB sotto, nel giro R.2.**
* ⚠️ **Debito mio: i COMMENT del giro 0.3.** I 22 COMMENT di funzione e i 2 di indice scritti da
  `20261106-22` … `-45` cominciano con «⭐ rev 2026-11-06 (20261106-NN, brief-…)», contro `linee-guida-sql` §5d
  (vale da subito per ogni COMMENT nuovo o riscritto). Sono applicati e committati: serve un changeSet di soli
  `COMMENT ON`. **Proposta DB:** in R.2, i 24 COMMENT riscritti interi al presente (sono una famiglia sola: i
  lettori della sorgente), più un pgTAP che controlla il testo di `obj_description` di quegli oggetti. Alternativa
  più leggera: togliere solo il prefisso, lasciando il testo di prima, anch'esso fuori regola, al lavoro che li
  riapre (molti li riapre il lotto T).

**I changeSet del giro R.1:**

| changeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20261106-46` | DROP DEFAULT 0 e indici unici «import»; conversione delle righe derivate esistenti; CHECK di forma; COMMENT delle colonne |
| `00_schema/vendite/-47` | gli otto indici «chi deriva da X» |
| `20_code/script/-48` | `script.fn_sorgente_provenienza` |
| `20_code/vendite/-49` | `vendite.fn_offerta_righe_espanse` + `eccezione_id` (DROP + CREATE, GRANT) |
| `20_code/script/-50` | `script.fn_check_righe_offerta_in_ordine`: l'alias nuovo |
| `20_code/vendite/-51` … `-56` | i sei verbi (tabella sopra) |
| `20_code/vendite/-57` | il guard unico sulle quattro righe, al posto del tipizzato |
| `80_data/changelog/-58` | via la voce `script.trgfn_guard_sorgente` da `dbops.riferimenti_morti_esenzioni` |

pgTAP: nuovo `vendite/test-sorgente-righe-vendita-v1` (22 casi); allineati
`vendite/test-fn-crea-revisione-preventivo-riga-completa-v1` (le quattro esclusioni tolte),
`dbops/test-sorgenti-struttura-v1` (il debito cala di quattro tabelle), `vendite/test-fattura-origini-v1` e
`vendite/test-documento-lineage-seminata-v1` (la provenienza scritta a mano passa da PREVENTIVO_RIGA modello A a
PREVENTIVO + uid + riga). Nessun codice nuovo, nessun CSV.

**La prova del giro R.1** (2026-11-06, come `zeroerp_owner`, sempre in transazione annullata):

* **i corpi di partenza sono quelli vivi:** per le otto funzioni riscritte il CREATE dell'ultimo YAML, rieseguito,
  dà lo stesso `pg_get_functiondef` del vivo, su scratch e su dbdev;
* **l'estratto** dei 13 changeSet gira intero su scratch e dbdev; `plpgsql_check` sulle nove funzioni: solo avvisi
  noti (variabili inutilizzate preesistenti, STABLE che chiama `fn_log_and_raise_error`);
* **la conversione su dbdev** (fatto datato): 317 righe d'ordine prendono PREVENTIVO, 216 righe di bolla
  ORDINE_VENDITA e 80 RESO_VENDITA; ogni riga citata è del documento citato (zero eccezioni), nessuno 0 resta,
  `dbops.vw_sorgenti_orfane` vuota, l'esenzione è uscita, i quattro montaggi hanno argomenti validi;
* **il ramo nuovo si costruisce:** `vendite/test-sorgente-righe-vendita-v1` chiama i sei verbi sulla strada
  dell'applicazione e prova guard, forma e lato in uscita: 22/22 su scratch e su dbdev. Senza l'estratto è rosso
  dal test 1, compreso il 6 (la revisione su un articolo ritirato, il buco del lotto B);
* **regressione prima/dopo su 566 pgTAP** (chi nomina un verbo, un builder di documento, le righe di vendita, una
  cancellazione su vendite, i presidi trasversali; sullo scratch): 7224 → 7245 ok. I 69 rossi, in 40 file, sono
  **identici** riga per riga nelle due corse: test di scope o di permesso, rossi da owner per costruzione. Le sole
  differenze sono le attese: il test nuovo, il test 2 di `dbops/test-sorgenti-struttura-v1` (il debito cala) e il
  test 1 di `vendite/test-fn-crea-revisione-preventivo-riga-completa-v1` (le colonne ora nominate). Verdi nelle due
  corse `vendite/test-fattura-origini-v1` (10) e `vendite/test-documento-lineage-seminata-v1` (22);
* guardrail statici (`scripts/guardrail_*.py`): verdi.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il
2026-11-06:** apply dei 13 changeSet, pgTAP verdi.

**Il giro R.2, le scelte** (team DB, 2026-11-06):

* **I sei tipi `*_RIGA` di vendita escono da `config.sorgenti`** (S-2): PREVENTIVO_RIGA, CONTRATTO_RIGA,
  ORDINE_VENDITA_RIGA, DDT_VENDITA_RIGA, FATTURA_RIGA, RESO_VENDITA_RIGA. Censimento (dbdev, 2026-11-06, fatto
  datato): nessuna riga li porta in nessuna delle colonne con FK verso `config.sorgenti`; nessuna funzione, vista,
  BE o FE li usa come sorgente; un pgTAP li asseriva (`magazzino/test-causali-e-sorgenti-seed-v1`).
* **L'entità resta.** In `config.tipi_entita` le sei righe restano, con `is_sorgente = false`: `ORDINE_VENDITA_RIGA`
  è il bersaglio di `vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna`, e le entità servono a note,
  giornale ed errori. Le chiavi di traduzione `config.tipi_entita.<x>_riga` quindi **restano**: sono l'etichetta
  dell'entità. Il piano diceva «e delle chiavi di traduzione»: era sbagliato, perché le chiavi sono dell'entità, non
  della sorgente.
* **La forma del ritiro, in tre posti nell'ordine in cui girano:** `tipi_entita.csv` (`is_sorgente = f`, il mirror
  `20260822-55`: `sorgente_codice_interno`, generata, torna NULL e la FK verso `config.sorgenti` non la tiene più);
  `sorgenti.csv` senza le sei righe (il mirror `20251002-21`: da zero non nascono); `80_data/changelog/20261106-60`,
  che le cancella dove esistono e in 80_data gira dopo i due mirror. Una tabella, un CSV: nessun seed laterale.
* **I COMMENT del giro 0.3** (decisione di Tid): `20261106-59` riscrive interi al presente i 21 COMMENT di funzione
  e i 2 di indice del giro 0.3, con le firme ancorate dei loro changeSet. Il presidio
  `vendite/test-sorgente-commenti-al-presente-v1` li controlla, insieme ai COMMENT del lotto R: un elenco chiuso di
  oggetti per nome, e una regex sul testo (rev + anno, «brief-», id di changeSet, la stella, le sigle di decisione).
  «lotto» non è vietato: i lotti di fatturazione sono dominio.

**I changeSet del giro R.2:** `20_code/vendite/20261106-59` (i COMMENT), `80_data/changelog/20261106-60` (il DELETE),
`80_data/sql/config/sorgenti.csv` e `tipi_entita.csv`. pgTAP: nuovo `vendite/test-sorgente-commenti-al-presente-v1`
(5); `vendite/test-sorgente-righe-vendita-v1` + 2 casi (23, 24: non più sorgenti, ancora entità); allineati
`magazzino/test-causali-e-sorgenti-seed-v1` (restano le quattro sorgenti di magazzino) e
`config/test-sorgenti-scope-pulizia-v1` (test 6: nessuna sorgente ROW_VALIDATOR).

**La prova del giro R.2** (2026-11-06, come `zeroerp_owner`, in transazione annullata, su scratch e dbdev):

* l'estratto (`-59`, `-60`, con il caricamento di `tipi_entita.csv` simulato dall'UPDATE che il mirror farebbe) gira
  intero; la convergenza del lato «in uscita» dopo il DELETE non monta e non smonta niente;
* `vendite/test-sorgente-righe-vendita-v1` 24/24, `vendite/test-sorgente-commenti-al-presente-v1` 5/5,
  `magazzino/test-causali-e-sorgenti-seed-v1` 11/11, su scratch e su dbdev. Senza l'estratto: il presidio dei
  COMMENT è rosso ai test 2 e 5 (le 21 funzioni e i 2 indici del giro 0.3), i casi 23 e 24 rossi;
* **regressione prima/dopo su 359 pgTAP** (chi legge `config.sorgenti`, `config.tipi_entita`, i COMMENT, la
  sorgente, i legami e la lineage; sullo scratch): 4680 → 4683 ok, 54 rossi in 32 file **identici** riga per riga
  nelle due corse (scope e permessi, rossi da owner per costruzione). Differenze: le due attese (i due pgTAP del
  giro) e **una trovata dalla regressione**: `config/test-sorgenti-scope-pulizia-v1` test 6 asseriva le sei
  sorgenti ROW_VALIDATOR per nome, in una stringa sola, e il censimento (grep dei codici fra apici) non l'aveva
  vista. Capovolto al modello: nessuna sorgente ROW_VALIDATOR. 9/9 su scratch e dbdev;
* guardrail statici: verdi (il preambolo del presidio nuovo ha il contesto applicativo).

⚠️ **Non provato qui: i due mirror veri.** Il caricamento di `tipi_entita.csv` e `sorgenti.csv` lo fa Liquibase,
e un seed simulato non prova il loader. Lo prova l'apply. ✅ **Provato dall'apply di Tid (dbdev, 2026-11-06):** i due
mirror (`20251002-21`, `20260822-55`) sono RERAN, `20261106-59` e `-60` EXECUTED; i sei tipi non sono più in
`config.sorgenti` e restano in `config.tipi_entita` con `is_sorgente` false (verifica DB dello stesso giorno).

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline.

#### Lotto T — testate di vendita

* **L'import esterno esce** da `ordini.sorgente_*` e `fatture.sorgente_*`. Oggi nessuno lo scrive: gli indici
  «idempotenza import» si ritirano. La tabella di collegamento dell'import (§4) nasce con il primo import vero, non ora.
* **Le colonne parallele confluiscono** (S-8): `ordini.documento_origine_*` (per il preventivo la chiave passa da id a
  uid) e `contratti.offerta_id`. Le regole «un'offerta, un ordine/contratto vivo» passano sull'indice parziale per id
  del tipo, presidiato da un pgTAP sul seed (D-8).
* **Si convertono** `ddt` e `resi`: da uid dell'ordine o della bolla a `sorgente_id` (S-5).
* **Fattura:** colonne presenti, NULL (D-11).
* **Il registro dei canali si ritira** (D-10, §6.4): la tabella, i quattro trigger, le due funzioni, i pgTAP, la riga
  di `storico_scope_policy.csv` e le pagine `manual/`. Con lui se ne vanno V-5 e G4. D-7 decade.
* **Lato «in uscita»** su resi e contratti (V-4). La regola «si cancella solo la bozza vuota» passa dal BE al DB per
  ordini, DDT e resi; il BE resta come controllo preventivo.
* **Voci per il §8 (BE):** `ordini_service` / `ordini_repository` (`documento_origine` → sorgente), `resi_repository` /
  `resi_service`, `offerte_service` (il campo `OffertaPushResult.sorgente_uid` che contiene il contratto). Il FE legge
  solo gli alias delle viste: se le viste li tengono, il FE non cambia.

##### Lotto T, i giri (team DB, 2026-11-06)

Il lotto T si fa in cinque giri, ognuno provato da solo. L'ordine segue le regole di ogni lotto (colonne e
conversione, guard, scrittori e lettori, ritiro per ultimo) e un vincolo in più: prima si toglie chi legge le
colonne di oggi, poi se ne cambia la grammatica.

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **T.1** | ritiro del registro dei canali (D-10): tabella, shadow di storico, i quattro trigger, le due funzioni, le registrazioni di catalogo, i due pgTAP, le pagine `manual/` | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |
| **T.2** | bolle e resi (S-5, D-4): conversione all'id, CHECK di forma (per il reso al posto del NOT NULL dell'uid), guard unico, i due verbi che scrivono la bolla (la riconsegna dichiara il **reso**), il builder pgTAP del reso, le viste di lista, la corsia dell'ordine dietro un reso, lock fuori bozza e colonne ferme della capability con `sorgente_id` | ✅ applicato da Tid, pgTAP verdi (2026-11-06) |
| **T.3** | ordini, contratti, fatture: l'import esce (indici «idempotenza import»), `documento_origine_*` e `offerta_id` confluiscono in `sorgente_*` (preventivo e offerta per uid), l'unicità «un'offerta, un ordine/contratto vivo» sull'indice parziale per id del tipo con il pgTAP sul seed (D-8), guard unico, i tre verbi di push e i lettori | ✅ applicato da Tid, pgTAP verdi (2026-11-07) |
| **T.4** | la cancellazione (V-4): «si cancella solo la bozza vuota» nel DB per ordini, bolle, resi e contratti; il contratto precedente di altri contratti non si cancella | ✅ applicato da Tid, pgTAP verdi (2026-11-07) |
| **T.5** | ritiro delle colonne parallele (`documento_origine_*` con la FK per codice, il CHECK di co-presenza e i due indici `uq_ordini_v_documento_origine_offerta`, `ix_ordini_documento_origine`; `offerta_id` con la FK e `uq_contratti_offerta_id`), insieme alle righe dei tre verbi che le scrivono ancora e alle loro terne nel lock fuori bozza; il presidio di struttura ha già perso le cinque testate (T.2, T.3) | ✅ applicato da Tid, pgTAP verdi (2026-11-07) |

✅ **Deciso per T.4 (Tid, 2026-11-06, «confermo tua proposta»):** il contratto, che oggi non ha né una regola DB di
cancellazione né un percorso BE che lo cancelli (`zeroerp_app` ha il privilegio DELETE), prende la stessa regola delle
altre testate: si cancella **solo la bozza vuota**. Scartata l'alternativa «il contratto non si cancella mai, solo
l'annullo».

**Il giro T.1, le scelte** (team DB, 2026-11-06; nessuna è un cambio di modello: è D-10):

* **Primo perché toglie un lettore.** `trgfn_documenti_sync_canali` leggeva `ordini.sorgente_*` e `ddt.sorgente_*`
  (l'uid come testo, G4): ritirato lui, T.2 e T.3 cambiano la grammatica delle testate senza un lettore in più da
  riscrivere e poi buttare. D-7 decade, V-5 sparisce.
* **Un changeSet solo per lo schema** (`00_schema/vendite/20261106-61`): i quattro trigger scritti a mano
  (`trg_{preventivi,ordini,ddt}_z90_sync_canali_ins_upd`, `trg_contratti_z90_sync_canali_ins`), poi le due funzioni,
  poi la tabella (senza `CASCADE`: una dipendenza non censita ferma il migrate), poi la shadow
  `storico.documenti_fatturazione_canali` (`IF EXISTS`: da zero, al primo passaggio, la crea ci_apply dopo). Un
  `DROP FUNCTION` staccato fallirebbe sui trigger; un `DROP TABLE` prima delle funzioni lascerebbe i trigger a scrivere
  nel vuoto. I trigger di automazione della tabella (audit, tx_id, storico, require_attivo) cadono con lei, senza DDL
  loro (`linee-guida-sql` §11.5). Rollback: forward-only, dichiarato.
* **La storia del registro se ne va con lui.** La shadow ha la storia di un registro che nessuno leggeva (1116 righe
  su dbdev, 2026-11-06: fatto datato). Senza la madre non riceve più niente.
* **Le registrazioni di catalogo** (`80_data/changelog/20261106-62`, come `20260912-09` per la legacy del 12-09): la
  riga 101 di `dbops.storico_scope_policy` (altrimenti riga senza madre, test 5 di `dbops/test-storico-scope-policy-v1`)
  esce dal CSV e, dove c'è, dal DELETE, perché il mirror `loadUpdateData` non cancella; la registrazione automatica in
  `config.storico_set_storicizza`. `dbops.fk_index_policy` tiene due righe (`consentito = false`) per una tabella che
  non c'è: il registro ne ha già altre venti così (dbdev, 2026-11-06) e nessun presidio le legge; non si toccano.
* **Che cosa non cambia:** nessuna funzione, vista, policy, FK, BE o FE nomina il registro (catalogo vivo e grep,
  2026-11-06). Nessuna voce per il §8. Il test 1 di `dbops/test-stati-check-scrittori-v1` elenca ancora
  `documenti_fatturazione_canali.stato_canale` fra le colonne misurate il 21-09: è voluto, la sua via d'uscita è
  «colonna tolta», e la riga non si tocca.

**I changeSet del giro T.1:** `00_schema/vendite/20261106-61` (il ritiro), `80_data/changelog/20261106-62` (le
registrazioni), `80_data/sql/dbops/storico_scope_policy.csv` (riga 101 tolta). pgTAP: nuovo
`vendite/test-registro-canali-ritirato-v1` (8); cancellati `vendite/test-documenti-canali-sync-v1` e
`vendite/test-documenti-fatturazione-canali-v1`; allineato `dbops/test-sorgenti-struttura-v1` (il debito cala di
una tabella). Cancellate le pagine `manual/` dei tre oggetti e della shadow. Nessun codice nuovo.

**La prova del giro T.1** (2026-11-06, come `zeroerp_owner`, in transazione annullata):

* `vendite/test-registro-canali-ritirato-v1`: 8/8 con l'estratto su scratch e dbdev; senza, rosso dal test 1;
* **regressione prima/dopo su 335 pgTAP** (tutti `dbops/`, `storico/`, `maintenance/`, e chi crea o cancella
  preventivi, ordini, bolle e contratti o chiama un verbo che li genera; sullo scratch): 4170 ok e 43 rossi nelle due
  corse. I rossi sono gli stessi riga per riga (scope e permessi, rossi da owner per costruzione), con due scambi:
  `dbops/test-sorgenti-struttura-v1` test 2 diventa verde (l'atteso: il debito cala), e
  `dbops/test-trigger-attivo-orfani-v1` test 3 diventa rosso;
* ⚠️ **quel rosso è previsto dal test, e lo chiude `ci_apply`.** Il framework ATTIVO aveva generato su
  `config.sorgenti` il trigger `trg_sorgenti_a10_documenti_fatturazione_canali_block_deact_upd` per la figlia: senza
  la figlia è un orfano (`TABELLA_ASSENTE`). Lo ritira il generatore (`dbops.fn_ritira_attivo_orfani`, chiamato dalla
  convergenza delle automazioni): in CI gira dopo i DROP, e su dbdev lo fa l'`update` di Tid, che senza `--contexts`
  ripassa anche `ci_apply`. Provato: con l'estratto e la chiamata del ritiro, il test 3 torna verde. Finché il ritiro
  non gira, disattivare una sorgente sbatterebbe su quel trigger;
* guardrail statici (`scripts/guardrail_*.py`): verdi.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il
2026-11-06:** apply di `-61` e `-62`, pgTAP verdi, nessuna regressione.

**Il giro T.2, le scelte** (team DB, 2026-11-06; nessuna è un cambio di modello: sono S-5, S-6 e D-4):

* **Prima i lettori, poi i dati.** Le viste di lista, le capability e la corsia dell'ordine (`-63` … `-67`) vengono
  prima della conversione (`-68`): leggono già le due grammatiche. Poi il guard (`-69`), il lock (`-70`) e i tre
  scrittori (`-71` … `-73`). Gli altri lettori di bolle e resi leggono già con la regola d'incontro dal giro 0.3.
* **La conversione è generica.** L'uid di un tipo a chiave `id` diventa l'id col ponte del BB che risolve
  (`script.fn_sorgente_documento_da_chiave`), per ogni tipo del catalogo, non con un join per tipo. Gira coi trigger
  della tabella spenti e riaccesi com'erano (il lock fermerebbe la bolla emessa), come nel giro R.1. Una chiave non
  risolta (un orfano) farebbe fallire il CHECK di forma nello stesso changeSet: il migrate si ferma, ed è voluto (S-6).
  Il `DROP NOT NULL` dell'uid del reso va **prima** della conversione. Lo scratch, vuoto, non lo vedeva: l'ha trovato
  la prova su dbdev.
* **La riconsegna dichiara il reso (D-4)**, in testata come sulle righe: `fn_genera_ddt_riconsegna` legge la
  provenienza una volta con `script.fn_sorgente_provenienza`, per testata e righe, e non cerca più l'ordine dietro il
  reso. Le bolle esistenti passano al reso quando le loro righe sono riconsegne di un reso solo
  (`resi_righe_riconsegne`).
* ⭐ **La corsia di fatturazione dell'ordine resta dietro la riconsegna.** `fn_ddt_trigger_ordine_testata` dà alla
  diagnosi del push e al check di emissione la corsia dell'ordine, per la sola riga-onere senza fulfillment. Con la
  testata sul reso sarebbe diventata NULL, e l'onere di una riconsegna avrebbe cambiato strada senza che nessuno
  l'avesse deciso. Il ramo nuovo prende l'ordine dietro le righe del reso (`resi_righe.ordine_riga_id`, la prima per
  id): è la regola con cui la riconsegna stabiliva se era «nata da un ordine», che ora vive solo qui.
* **Il guard unico** su bolla e reso: livello `DOCUMENTO`, azione `BLOCCA`, INSERT e UPDATE OF le tre colonne, nome
  a10 (prima dei trigger di dominio che rileggono la sorgente). Il CHECK di forma: la bolla ha nessuna sorgente o il
  tipo con una chiave sola; il reso ha sempre il tipo con una chiave sola.
* **Il lock fuori bozza e le colonne ferme** prendono `sorgente_id` accanto a `sorgente_uid` (terna nuova subito
  dopo; il lock è montato a mano, si rimonta qui). Le capability cambiano solo l'elenco: i COMMENT restano.
* **Le viste di lista** espongono `sorgente_id` in coda (`CREATE OR REPLACE VIEW` può solo appendere) e cercano
  l'origine con la regola d'incontro. Quella dei resi ora filtra anche sul tipo `DDT_VENDITA`: prima un uid di un
  altro tipo avrebbe trovato una bolla per caso. Per la riconsegna `vw_ddt_lista.ordine_origine_*` è NULL: viene da un
  reso (§8.5, BE-T.2-c).
* **Il payload del push** (`fn_list_ddt_da_pushare`, chiave `ordine_sorgente_uid`) non cambia: è l'uid dell'ordine
  letto dalla riga attraverso il fulfillment, non la colonna della testata. Il piano lo elencava per errore.
* **I COMMENT riscritti** (`linee-guida-sql` §5d): la corsia dell'ordine, i due verbi, il builder, le due viste e le
  sei colonne. Il presidio `vendite/test-sorgente-commenti-al-presente-v1` li copre già per le funzioni del suo elenco.

**Che cosa cambia per chi legge, dichiarato:**

* **Lineage:** sparisce l'arco di testata ordine → riconsegna (78 su dbdev, 2026-11-06: fatto datato). La riconsegna
  resta discendente dell'ordine attraverso la bolla d'origine e il reso.
* **Chi scrive l'uid per un tipo a chiave `id`** ora è rifiutato (`E_SORG_CHIAVE_NON_CONFORME`): il BE che crea il
  reso (§8.5, BE-T.2-a) e nove pgTAP che scrivono a mano la sorgente di bolle e resi (allineati in questo giro).

**I changeSet del giro T.2:** `20_code/vendite/20261106-63` (la corsia dell'ordine, ramo del reso), `-64`
(`vw_ddt_lista`), `-65` (`vw_resi_lista`), `20_code/script/-66` e `-67` (le colonne ferme della capability),
`00_schema/vendite/-68` (conversione, NOT NULL, CHECK di forma, COMMENT di colonna), `20_code/vendite/-69` (il guard
unico), `-70` (il lock fuori bozza), `-71` (la bolla dall'ordine), `-72` (la riconsegna), `20_code/dbops/-73` (il
builder pgTAP del reso). Nessun codice nuovo, nessun CSV. pgTAP: nuovo `vendite/test-sorgente-testate-bolle-resi-v1`
(19); allineati `dbops/test-sorgenti-struttura-v1` (il debito cala di due tabelle) e quattordici pgTAP che
scrivevano o asserivano l'uid in testata: `dbops/test-fn-pgtap-crea-ddt-da-ordine-v1`, `dbops/test-fn-pgtap-crea-reso-v1`,
`dbops/test-sorgenti-orfane-v1` (il caso TESTUALE passa su una tabella del test, le due testate sono UNICO),
`magazzino/test-reso-carico-v1`, `script/test-trgfn-default-emittente-fiscale-v1`,
`vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1`, `vendite/test-documento-lineage-seminata-v1`,
`vendite/test-esecutivi-ba-coppia-v1`, `vendite/test-fn-ddt-trigger-ordine-testata-v1`,
`vendite/test-fn-genera-ddt-da-ordine-v1`, `vendite/test-resi-righe-guard-origine-coerente-v1`,
`vendite/test-sorgente-righe-vendita-v1` (test 4: solo le quattro righe), `vendite/test-testata-dopo-emissione-rdb-v1`,
`vendite/test-testata-dopo-emissione-v1` (le colonne del lock).

**La prova del giro T.2** (2026-11-06, come `zeroerp_owner`, in transazione annullata):

* **i corpi di partenza sono quelli vivi:** per le nove funzioni e viste riscritte il CREATE dell'ultimo YAML,
  rieseguito, dà lo stesso `pg_get_functiondef` / `pg_get_viewdef` del vivo, su scratch e su dbdev;
* `vendite/test-sorgente-testate-bolle-resi-v1`: 19/19 con l'estratto su scratch e dbdev; senza, 7 rossi;
  `plpgsql_check` sulle cinque funzioni plpgsql: solo avvisi preesistenti (`v_stato`, `v_reso_uid` della riconsegna,
  `v_reso_stato` del builder);
* **la conversione su dbdev** (fatto datato): 137 bolle dall'ordine e 80 dal reso (78 riconsegne passate dall'ordine
  al reso, 1 già sul reso, 1 senza sorgente che era una riconsegna), 33 senza sorgente; 88 resi; nessun uid rimasto
  per un tipo a chiave `id`; `dbops.vw_sorgenti_orfane` vuota;
* **equivalenza prima/dopo su tutta la popolazione di dbdev**, `EXCEPT ALL` nei due versi: diagnosi del push (323),
  check di emissione di ogni bolla (250), lister del push (112), capability di bolle e resi (salvo l'elenco delle
  colonne ferme): zero differenze. Archi della lineage: 78 tolti, nessuno aggiunto, su 1616. Sono gli archi di testata
  ordine → riconsegna (sopra);
* **regressione prima/dopo su 440 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina bolle, resi, i loro verbi e
  builder, la lineage, le capability, le viste di lista o la sorgente; sullo scratch): fuori dai quattordici file
  allineati e dai due del giro, i rossi sono gli stessi riga per riga nelle due corse (scope e permessi, rossi da owner
  per costruzione). Dopo l'allineamento, i quindici file (con il nuovo) rifatti prima/dopo: 321 ok e 2 rossi, il 39 di
  `vendite/test-esecutivi-ba-coppia-v1` (dichiarato «rosso da owner, verde come app») e il 2 del presidio di struttura,
  che è verde quando l'estratto comprende anche il giro T.1 (lo scratch non l'ha ancora applicato): T.1 + T.2 insieme,
  presidio di struttura 5/5, `vendite/test-registro-canali-ritirato-v1` 8/8, il pgTAP nuovo 19/19, su scratch e dbdev;
* ⚠️ **un cambio di codice d'errore, dichiarato.** Una bolla o un reso che citano un documento che non esiste ora si
  fermano al guard unico (a10) con `E_SORG_NOT_FOUND`, prima del guard del cliente (z10), che dava
  `E_DOC_SORGENTE_NON_TROVATA`. Il caso è lo stesso, rifiutato prima. Per bolla e reso il controllo d'esistenza del
  guard del cliente diventa un doppione del guard unico: il ritiro di quel ramo è nel lotto Z (§8.5, voce BE-T.2-e per
  il BE);
* guardrail statici: verdi;
* ⚠️ **all'apply di Tid (dbdev, 2026-11-06) `-63` si è fermato**: «non è possibile inserire comandi multipli in una
  istruzione preparata». La funzione è `BEGIN ATOMIC`, e pgjdbc dopo l'`END;` non spezza più le istruzioni: il
  `COMMENT` nello stesso `- sql:` finiva nella stessa Parse. psql non lo vede, e la prova era passata da psql. Liquibase ha
  annullato il changeSet (`-61` EXECUTED, `-63` no): il file, mai applicato, è corretto in place, col `COMMENT` in un
  `- sql:` suo, come `-24`. **Riprovato attraverso il driver di Liquibase** (`postgresql-42.7.10.jar`, un
  `Statement.execute` per ogni `- sql:`, in una transazione annullata su dbdev): i quindici `- sql:` di `-62` … `-73`
  passano in ordine; la forma vecchia riprodotta dà lo stesso errore.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il
2026-11-06:** apply degli undici changeSet (`-63` corretto), pgTAP verdi, nessuna regressione.

**Il giro T.3, le scelte** (team DB, 2026-11-07; nessuna è un cambio di modello: sono S-8, D-8, D-11 e V-1 per D-12):

* **Le colonne parallele restano scritte fino al giro T.5.** I tre verbi scrivono la provenienza in `sorgente_*` **e**,
  accanto, `documento_origine_*` (l'ordine) e `offerta_id` (il contratto). Tutti i lettori DB passano a `sorgente_*`
  in questo giro; le colonne parallele restano vere per i lettori del BE (§8.6), che il lotto BE sposta, e si ritirano
  in T.5 con le righe che le scrivono. Ritirarle ora avrebbe lasciato dati vecchi convertiti e righe nuove senza la
  colonna, cioè due verità per lo stesso lettore. È la regola «il ritiro va per ultimo».
* **La conversione è generica**, come in T.2: il tipo dal codice di `documento_origine_tipo` (o OFFERTA_COMMERCIALE per
  `offerta_id`), la chiave dal BB che scrive (`script.fn_sorgente_chiave`, che traduce l'id del preventivo o
  dell'offerta nel loro uid e solleva su un'origine che non esiste: il migrate si ferma, S-6). Coi trigger della
  tabella spenti e riaccesi com'erano. Gli indici «idempotenza import» (`uq_ordini_v_sorgente_fk`,
  `uq_fatture_v_sorgente_fk`) cadono **prima**: su (tipo, uid) avrebbero vietato due ordini dallo stesso preventivo.
* **D-8, l'unicità sull'offerta**: `uq_ordini_v_sorgente_offerta` e `uq_contratti_sorgente_offerta`, unici
  `NULLS NOT DISTINCT` su (tipo, `sorgente_id`, `sorgente_uid`), parziali su `sorgente_tipo_id = 14 AND NOT
  is_abortito_snapshot`. Il predicato nomina l'id del seed; lo presidia il test 4 del pgTAP nuovo, che lo confronta con
  il catalogo. Accanto, sei indici «chi deriva da X» (tipo + `sorgente_id`, tipo + `sorgente_uid`, sulle tre testate):
  li usa il lato in uscita a ogni cancellazione di un'origine.
* **Il guard unico** su ordine, contratto e fattura: livello `DOCUMENTO`, azione `BLOCCA`, a10. Per il contratto
  `BLOCCA` è la protezione che oggi dà `fk_contratti_offerta`, e resta quando `offerta_id` se ne va. Il lock fuori
  bozza di ordine e contratto prende la terna di `sorgente_id` (rimontato dai `pg_get_triggerdef` vivi).
* **I lettori** usano la regola d'incontro del modello, `(doc.id = x.sorgente_id OR doc.uid = x.sorgente_uid)`, come
  H e R dal giro 0.3: documenti vivi dell'offerta, annullabilità del preventivo (motivo 1), legami PROVENIENZA di
  ordine e contratto, archi A, C, D della lineage nei due modi (le chiavi del seme prendono `t_off`), lista ordini,
  dashboard delle offerte. `vw_ordini_lista` tiene gli alias che BE e FE leggono (`documento_origine_tipo`, `_id`,
  `_codice`, stessi tipi) calcolati dalla provenienza, e appende le tre `sorgente_*`; `vw_fatture_lista` appende
  `sorgente_id` (D-11: di norma NULL).
* **I verbi** leggono la provenienza una volta, prima della testata, col BB che scrive per codice
  (`script.fn_sorgente_provenienza`), e la usano per testata e righe. In `fn_push_offerta_a_contratto` la lettura a
  mano del tipo OFFERTA_COMMERCIALE se ne va (regola del 2): un tipo assente dal catalogo ora è `E_SORG_CONF` dal BB, non
  `E_CONFIG_MANCANTE`; tecnici tutti e due.
* **V-1 si chiude qui** (D-12: nel lotto che tocca l'oggetto). Con una pratica, il push a contratto scriveva in
  `pratiche_sorgenti` l'uid del contratto, che ha chiave `id`: il guard testuale lo rifiutava e il percorso si fermava.
  Ora scrive l'id, come il push a ordine. Nessun dato da correggere: il percorso non era mai arrivato in fondo.
* **Firme e COMMENT.** Le firme da YAML con `%TYPE` (`fn_check_preventivo_annullabile` riprende
  `vendite.preventivi.id%TYPE` e `SECURITY INVOKER` esplicito, che l'auto-gen aveva sciolto), i corpi dal vivo. I
  COMMENT riscritti al presente (`linee-guida-sql` §5d), compresi i tre di vista, che erano cronaca; il COMMENT di
  `fn_documento_legami` resta vero e non si tocca. Il presidio `vendite/test-sorgente-commenti-al-presente-v1` prende
  le funzioni, le tre testate e gli otto indici del giro.

**Che cosa cambia per chi legge, dichiarato:**

* **Un'offerta o un preventivo citati non si cancellano** (`E_SORG_ORIGINE_REFERENZIATA`), come una FK: per l'offerta
  col contratto c'era già la FK, per il preventivo con l'ordine no (un preventivo in bozza citato da un ordine scritto a
  mano si cancellava).
* **Un ordine o un contratto con una provenienza che non esiste** ora sono rifiutati (`E_SORG_NOT_FOUND`): prima
  `documento_origine_id` era polimorfo e senza controllo.
* **Lettori su un'offerta invisibile:** `fn_offerta_documenti_vivi` legge l'offerta sotto la RLS di chi chiama; un'offerta
  che non vede non ha documenti vivi. I tre consumatori la leggono prima con la stessa RLS.

**I changeSet del giro T.3:** `00_schema/vendite/20261106-74` (indici «import» via, conversione, CHECK di forma, COMMENT
di colonna), `-75` (gli otto indici), `20_code/vendite/-76` (il guard unico), `-77` (il lock), `-78` (documenti vivi
dell'offerta), `20_code/script/-79` (annullabilità del preventivo), `20_code/vendite/-80` (legami), `-81` (lineage), `-82`
(`vw_ordini_lista`), `-83` (`vw_dash_fatturazione_offerte`), `-84` (`vw_fatture_lista`), `-85` … `-87` (i tre verbi).
Nessun codice nuovo, nessun CSV. pgTAP: nuovo `vendite/test-sorgente-testate-ordini-contratti-v1` (24); allineati
`dbops/test-sorgenti-struttura-v1` (il debito perde le tre testate), `vendite/test-sorgente-commenti-al-presente-v1`
(l'elenco chiuso), `vendite/test-testata-dopo-emissione-v1` (le colonne del lock), `dbops/test-sorgenti-orfane-v1`
(test 2: le testate sono UNICO) e le sei fixture della regressione (sotto).

**La prova del giro T.3** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **i corpi di partenza sono quelli vivi:** per le dieci funzioni e viste riscritte, `pg_get_functiondef` /
  `pg_get_viewdef` prima e dopo l'estratto differiscono solo nei punti della provenienza; intestazioni, clausole
  (`SET jit`, `plan_cache_mode`, `SECURITY DEFINER` e `search_path` dei legami), privilegi e `security_invoker` delle
  viste identici. Il lock è rimontato dai `pg_get_triggerdef` vivi, uguali su scratch e dbdev;
* **l'estratto** dei quattordici changeSet gira intero su scratch e dbdev; i 24 `- sql:` passano anche attraverso il
  driver di Liquibase (`postgresql-42.7.10.jar`, un `Statement.execute` per change, in transazione annullata su
  dbdev); `plpgsql_check` sulle cinque funzioni plpgsql: solo gli avvisi già noti (STABLE che chiama
  `fn_log_and_raise_error`);
* **la conversione su dbdev** (fatto datato, 2026-11-07): 317 ordini prendono PREVENTIVO e 6 OFFERTA_COMMERCIALE,
  tutti con l'uid del documento di `documento_origine_id`; nessun ordine resta con l'origine e senza provenienza; il
  contratto da offerta (1) è coerente con `offerta_id`; nessuna fattura ha una sorgente; `dbops.vw_sorgenti_orfane`
  vuota;
* **equivalenza prima/dopo su tutta la popolazione di dbdev**, `EXCEPT ALL` nei due versi, zero differenze: documenti
  vivi di ogni offerta, annullabilità di ogni preventivo (748), legami di ogni ordine, contratto e offerta, archi della
  lineage tutti (1538) e seminati da ogni preventivo, offerta, ordine e contratto, `vw_ordini_lista` (592),
  `vw_dash_fatturazione_offerte`, `vw_fatture_lista`, capability di offerte e preventivi. Dice che la popolazione di
  oggi non vede differenze, non che il ramo nuovo è provato: quello lo prova il pgTAP sotto;
* **il ramo nuovo si costruisce:** `vendite/test-sorgente-testate-ordini-contratti-v1` chiama i tre verbi sulla strada
  dell'applicazione (il push a contratto con una pratica, V-1), poi **azzera le colonne parallele** dei documenti in
  bozza e fa leggere la sola provenienza a ogni lettore: 24/24 su scratch e su dbdev. Senza l'estratto è rosso dal
  test 1, e si ferma al push con pratica (V-1 riprodotto: `E_SORG_FORMATO`);
* **regressione prima/dopo su 605 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina le tre testate, i loro verbi e
  builder, i lettori riscritti, la sorgente, i presidi trasversali; sullo scratch, in sequenza, `databasechangelog`
  invariato durante la corsa): 7622 → 7621 ok prima degli allineamenti. Fuori dai file del giro, cambiano nove file:
  * **sei fixture che costruivano a mano un ordine «da offerta» o «da preventivo» scrivendo solo la colonna
    parallela** (`script/test-fn-available-actions-offerta-v1` 12,
    `vendite/offerte_commerciali/test_fn_push_offerta_a_contratto` 9, `vendite/test-annullo-documento-con-legami-v1`
    20 e 23, `vendite/test-documento-lineage-seminata-v1` 9, 17-19, `vendite/test-fattura-origini-v1` 4 e 9,
    `vendite/test-grammatica-origine-destinazione-sorgenti-v1` 10 e 11): è il cambio voluto, i lettori leggono la
    provenienza. Allineate: la fixture scrive anche `sorgente_*`, come il verbo. La grammatica usava un'offerta
    inventata (un id che nessuna offerta ha), che il guard unico ora rifiuta: costruisce un'offerta vera in bozza;
  * `dbops/test-sorgenti-orfane-v1` test 2 asseriva TESTUALE per ordini, contratti e fatture: ora UNICO, l'atteso;
  * `script/test-fn-log-and-raise-error-constraint-codice` e `script/test-rubinetto-primo-motivo-v1` sono morti di
    **deadlock** sul `DROP INDEX` in testa all'estratto, con un'altra sessione che lavorava sullo scratch: rifatti da
    soli, 5/5 e 7/7.
  Dopo gli allineamenti i nove file, rifatti con l'estratto: tutti verdi, salvo il 30 di
  `test-annullo-documento-con-legami-v1`, rosso uguale anche prima (il permesso del proprietario: rosso da owner per
  costruzione). Gli altri rossi delle due corse (103) sono gli stessi riga per riga: scope e permessi, rossi da owner;
* guardrail statici (`scripts/guardrail_*.py`, preambolo pgTAP, licenze): verdi.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il
2026-11-07:** apply dei quattordici changeSet, pgTAP verdi (commit `b86108e56a`).

**Il giro T.4, le scelte** (team DB, 2026-11-07; nessuna è un cambio di modello: è V-4, con la decisione di Tid del
2026-11-06 sul contratto):

* **Un guard solo, quello che c'è.** `vendite.trgfn_doc_guard_delete_solo_bozza` faceva già la metà «in bozza» per
  ordine, bolla e bozza email (Tid, 2026-08-26). Prende la metà «vuota» e si monta su reso e contratto (`-89`). Una
  funzione nuova accanto sarebbe stata una seconda copia della stessa regola.
* **«Vuota» = nessuna riga attiva.** È il predicato del BE (`count_righe`, `attivo IS TRUE`) e delle capability
  (`senza_righe`): spostare la regola nel DB non ne cambia il significato. Una bozza con sole righe disattivate si
  cancella, e quelle righe seguono la testata nella cascata. Codice nuovo `E_DELETE_DOC_CON_RIGHE` (`CONFLITTO_STATO`),
  detto **dopo** `E_DELETE_DOC_NON_BOZZA`: fuori bozza il rimedio è annullare, in bozza è togliere le righe o annullare.
* **Lo stato dal BB** `script.fn_get_stato_testata_documento` (regola del 2): il guard leggeva a mano i vocabolari di
  bolla e ordine, il BB dà stato ed etichetta delle stesse testate (e di reso, contratto, mail). Con quattro testate le
  letture a mano sarebbero diventate quattro. Escono; le etichette dei messaggi restano le stesse.
* ⭐ **SECURITY DEFINER** (`search_path = pg_catalog, pg_temp`), come il lato «in uscita» della provenienza. La metà
  «vuota» legge le righe, che hanno RLS, e la cascata che segue non passa dalla RLS: un guard invoker giudicherebbe sulle
  righe che il chiamante vede, e la cascata cancellerebbe anche le altre. Oggi le due cose coincidono per costruzione (la
  policy delle righe risolve l'emittente dalla testata, e solo l'OPERATORE scrive le testate): la postura toglie la
  dipendenza da quella policy. Il test 2 del pgTAP nuovo la presidia.
* **Il ramo per schema e tabella**, non per sola tabella: prima `acquisti.ddt` si sarebbe letto come la bolla di
  vendita, se qualcuno vi avesse montato il guard.

**Che cosa cambia per chi legge, dichiarato:**

* **Un reso confermato non si cancella più** (`E_DELETE_DOC_NON_BOZZA`): lasciava orfani i movimenti di magazzino (V-4).
* **Un contratto si cancella solo da bozza vuota.** Oggi nessun percorso BE lo cancella; `zeroerp_app` ha il privilegio.
* **Una bozza con righe attive non si cancella più dal DB**, su nessuna delle quattro testate. Il BE lo controllava già
  prima (`E_ORD_STATO_TRANSIZIONE`, `E_DDT_STATO_TRANSIZIONE`, `E_RESO_STATO_TRANSIZIONE`) e continua a farlo: per l'utente
  non cambia niente (§8.7). Cambia per chi cancellava una bozza con righe da SQL: tre pgTAP (sotto).
* **Il contratto precedente di altri contratti non si cancella** (`E_DELETE_CONTRATTO_CON_SUCCESSIVI`), nemmeno da
  bozza vuota. ✅ **Deciso da Tid il 2026-11-07** («che i figli perdono il padre non va bene»), sull'osservazione del
  team DB: `fk_contratti_parent` era `ON DELETE SET NULL` dalla baseline (2025-08-30, senza una decisione scritta), e
  con la cancellazione delle bozze vuote avrebbe staccato i successori in silenzio. La forma è la coppia del fulfillment
  delle righe: la FK passa a `NO ACTION` ed è la protezione, da qualunque percorso (`-90`); il guard dice prima la frase,
  con lo stesso predicato e il numero dei successori (`-88`); l'indice parziale della FK si accende nel registro
  (`-91`), perché FK e guard cercano i successori a ogni cancellazione. Nessuna funzione cancella contratti, e l'unico
  scrittore della colonna è `vendite.fn_create_contratto` (catalogo vivo e grep, 2026-11-07).

**I changeSet del giro T.4:** `20_code/vendite/20261106-88` (il guard: la bozza vuota, lo stato dal BB, DEFINER, il
contratto precedente), `-89` (il montaggio su resi e contratti), `00_schema/vendite/-90` (`fk_contratti_parent` a `NO
ACTION`, col COMMENT del vincolo), `80_data/changelog/-91` con `80_data/sql/vendite/fk_index_policy_contratti_parent.csv`
(l'indice parziale della FK: CSV dedicato come i trenta seed del registro prima di lui, perché `fk_index_policy.csv`
non ha un changeSet che lo carica in `migrations_v2`), `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv`
(i due codici nuovi, id 1451 e 1452; la nota di `E_DELETE_DOC_NON_BOZZA` prende reso e contratto). Nessuna funzione
nuova. pgTAP: nuovo `vendite/test-delete-testate-solo-bozza-vuota-v1` (19); allineati `script/test-sorgente-in-uscita-v1`,
`vendite/test-ddt-righe-evase-dall-ordine-v1` (27), `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` (11) e
`vendite/test-delete-righe-documento-bozza-v1` (4), che cancellavano una bolla in bozza con righe attive. Pagine `manual/`: `vendite/trgfn_doc_guard_delete_solo_bozza`
riscritta, `script/fn_get_stato_testata_documento` (il consumatore nuovo).

**Gli allineamenti, uno per uno:**

* `script/test-sorgente-in-uscita-v1` (8-11): la cascata dal documento portava la riga attiva e il suo prelievo. Ora la
  bolla si svuota prima: il prelievo se ne va (tolto il figlio che lo bloccava) e la riga si disattiva. Il figlio
  CANCELLA del 9 dichiara la riga disattivata invece del prelievo, perché la cascata dal documento porta ormai solo righe
  disattivate (un prelievo vivo impedisce di disattivare la sua riga). Il livello dettaglio resta provato dal 4-5;
* `vendite/test-ddt-righe-evase-dall-ordine-v1` (27, «la bolla in bozza si elimina intera»): è una conseguenza del
  modello di allora, non una decisione (D-3 di quel brief riguarda il togliere una riga in bozza). Ora la bolla con la
  riga evasa è rifiutata, e la strada è D-3: si toglie la riga, poi la bozza vuota, e l'ordine torna CONFERMATO;
* `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` (11, «il cascade non è fermato dal BB») e
  `vendite/test-delete-righe-documento-bozza-v1` (4, «la testata si elimina, e le righe la seguono»): la riga della
  bolla in bozza si disattiva prima, e la cascata la porta. Attese invariate. Il secondo costruisce il DELETE con
  `format('%I')`: il primo censimento (grep sul testo `DELETE FROM vendite.ddt`) non l'aveva visto, l'ha trovato la
  regressione.

**La prova del giro T.4** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **il corpo di partenza è quello vivo:** `pg_get_functiondef` del guard uguale su scratch e dbdev e uguale alla doc
  auto-generata; il rollback di `-88` lo rimette;
* **l'estratto** dei due changeSet, con le due righe nuove dei CSV, gira su scratch e dbdev; `plpgsql_check` sul guard
  montato su `vendite.resi` e su `config.email_outbox`: nessun avviso;
* `vendite/test-delete-testate-solo-bozza-vuota-v1`: 19/19 con l'estratto su scratch e su dbdev; senza, 5/19 (passano
  solo i casi che erano già veri: cancellare la bozza vuota, il rifiuto dell'ordine confermato). Il seed di `-91` è
  simulato con l'upsert della riga del registro e `CALL dbops.apply_fk_index_policy()`: l'indice nasce parziale, col
  nome registrato, su tutti e due (sullo scratch la riga del registro non c'era, e il `loadUpdateData` la inserisce);
* **regressione prima/dopo su 178 pgTAP** (tutti `dbops/`, `storico/`, `maintenance/`, chi nomina la mail, il guard, i
  suoi codici, il lettore dello stato, il guard delle righe, e chi cancella una delle quattro testate; sullo scratch, in
  sequenza; prima = il file di HEAD senza estratto, dopo = il file dell'albero con l'estratto): fuori dai file del giro,
  i rossi sono gli stessi riga per riga (scope e permessi, rossi da owner per costruzione). Tre differenze, spiegate:
  * `vendite/test-delete-righe-documento-bozza-v1` test 4: il quarto allineamento (sopra), poi 10/10 con e senza;
  * `vendite/test-contratti-modalita-pricing-v1`: nella corsa «dopo» il file non ha prodotto righe; rifatto da solo con
    l'estratto, 4/4. Era occupazione dello scratch, non il giro;
  * `dbops/test-guard-attivo-grammatica-e-codici-v1` test 23: il file è modificato nell'albero da un altro cantiere
    (`brief-db-revisione-dbops`, changeSet `20261107-28` … `-31` non ancora committati). Il file dell'albero è rosso al 23
    anche senza l'estratto; quello di HEAD con l'estratto è verde. Non è del giro;
* **dopo il contratto precedente** (`-90`, `-91`, il ramo nuovo del guard), prima/dopo sui diciannove pgTAP che
  leggono le azioni delle FK, `parent_contratto_id` o il registro degli indici, e sui presidi `dbops` di codici,
  messaggi, postura e indici: esiti uguali riga per riga. Fanno eccezione il 27 allineato delle bolle e due file
  dell'altro cantiere: il 23 già detto e `dbops/test-fk-info-su-pg-constraint-v1`, nuovo e non in HEAD, rosso uguale
  con e senza l'estratto perché aspetta una funzione che quel cantiere non ha ancora applicato;
* i quattro file allineati, con l'estratto, anche su dbdev: verdi, salvo il 43 di
  `vendite/test-ddt-righe-evase-dall-ordine-v1`, dichiarato «rosso da owner, verde come app» e rosso uguale su HEAD;
* guardrail statici (`scripts/guardrail_*.py`, licenze): verdi. Il controllo i18n segnala
  `vendite.righe.articolo_reason.obsoleto`, preesistente e di un altro brief.
* ⚠️ **alla corsa come applicazione (Tid, 2026-11-07) il test 1 del pgTAP nuovo era rosso**: confrontava
  `tgrelid::regclass::text` con nomi qualificati, e come app `config` sta nel `search_path`, quindi usciva
  `email_outbox` senza schema. Da owner era verde, ed è per questo che la prova non l'ha visto. Corretto prima del
  commit: schema e nome da `pg_class` + `pg_namespace`; riprovato anche con gli schemi del test nel `search_path`.

**Fatto da Tid il 2026-11-07:** apply di `-88` … `-91` e dei tre CSV, pgTAP verdi come applicazione.

**Il giro T.5, le scelte** (team DB, 2026-11-07; via di Tid lo stesso giorno; nessuna è un cambio di modello: è S-8,
il ritiro che il giro T.3 aveva rinviato):

* **Prima chi scrive, poi il lock, poi le colonne.** I tre verbi smettono di scrivere le colonne parallele (`-92` …
  `-94`); il lock fuori bozza di ordine e contratto perde le loro terne (`-95`); poi le colonne se ne vanno, con ciò che
  vive solo per loro (`-96`, `-97`). L'ordine conta: il lock legge la testata con `to_jsonb`, e una colonna del montaggio
  che la testata non ha è `E_DOC_RIGHE_LOCK_MONTAGGIO` a ogni UPDATE (verificato sul corpo del lock).
* **I verbi dal changeSet del T.3, non riscritti.** Firma con `%TYPE`, corpo e COMMENT da `-85` … `-87`, che rieseguiti
  danno lo stesso `pg_get_functiondef` del vivo; cambiano solo le righe delle colonne parallele e le frasi che le
  citano. Il rollback è quel changeSet. Nessuna variabile nuova.
* **Che cosa prende il posto di ciò che se ne va.** «Un'offerta, un ordine o contratto vivo» resta sugli indici della
  provenienza (`uq_ordini_v_sorgente_offerta`, `uq_contratti_sorgente_offerta`, D-8 del T.3). La protezione di
  `fk_contratti_offerta` (un'offerta citata non si cancella) la dà il guard unico (BLOCCA) col lato «in uscita», dal T.3.
  La FK per codice dell'ordine verso `config.sorgenti` la sostituisce `fk_ordini_v_sorgente_tipo`, per id.
* **I COMMENT che nominavano ciò che se ne va** si riscrivono dal testo vivo, cambiando solo quella frase: il BB degli
  snapshot di stato (`-98`), la tabella delle offerte, la colonna `ordini.is_abortito_snapshot` e i due trigger degli
  snapshot (in `-96`, `-97`). Il COMMENT di `vw_ordini_lista` resta vero: gli alias `documento_origine_*` restano,
  calcolati dalla provenienza.
* **Il registro degli indici FK** perde le righe delle due FK ritirate (`-99`, la forma di `20261001-25`).
* **Tre testi di codici d'errore** citavano gli indici o le colonne ritirate (`E_ORD_OFFERTA_GIA_CONVERTITA`,
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`, `E_OFFERTA_ORDINE_GIA_GENERATO`): riscritti sui documenti vivi dell'offerta e sugli
  indici della provenienza. La soluzione dell'ultimo diceva «eliminarlo»: un ordine con righe dal giro T.4 non si
  elimina, si annulla, e un ordine annullato non consuma l'offerta.
* **Che cosa non cambia:** nessuna funzione, vista o trigger generato da `ci_apply` legge le colonne (catalogo vivo e
  grep, 2026-11-07); nessun changeSet di `80_data` o `90_end` le pretende (il template standard dell'ordine,
  `20261020-25`, le nomina solo nei commenti); nessuna tabella di storico ha quelle colonne. Il builder
  `dbops.fn_pgtap_crea_contratto` passa dal verbo e non cambia.

**Che cosa cambia per chi legge, dichiarato:**

* **Il BE si rompe nei due punti del §8.6** (BE-T.3-b, BE-T.3-c): `ordini_repository.get_ordine_by_documento_origine`
  e il join offerta → contratto di `offerte_repository`. Era accettato dal piano (il lotto BE viene dopo il lotto Z):
  dall'apply quei due percorsi danno errore finché il BE non li sposta. I lettori che passano dagli alias di
  `vw_ordini_lista` (la stampa dell'ordine, la lista FE) non cambiano (§8.8).
* **Lineage, documenti vivi, lista ordini:** nessuna differenza su tutta la popolazione di dbdev (sotto).

**I changeSet del giro T.5:** `20_code/vendite/20261106-92` … `-94` (i tre verbi), `-95` (il lock fuori bozza di ordine
e contratto), `00_schema/vendite/-96` (`ordini`: via `documento_origine_*`, i due indici, il CHECK e la FK per codice; i
COMMENT dello snapshot), `-97` (`contratti`: via `offerta_id`, l'indice unico e la FK; i COMMENT della tabella delle
offerte e dello snapshot), `20_code/vendite/-98` (il COMMENT del BB degli snapshot), `80_data/changelog/-99` (il
registro degli indici FK); `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (i tre testi). Nessuna
funzione nuova, nessun codice nuovo.

**Gli allineamenti dei pgTAP (diciassette file):**

* **presidi di struttura che asserivano gli oggetti ritirati**, ora asseriscono la loro assenza e la regola sulla
  provenienza: `vendite/test-ordini-modello-ext` (6-12: le due metà della regola A1, nessuna UNIQUE piena e una
  parziale sulla sola offerta, ora su `sorgente_*`), `vendite/test-grammatica-origine-destinazione-sorgenti-v1` (1, 6, 8,
  9: l'origine è una FK per id, il codice corto non si può più scrivere), `vendite/test-annullo-documento-con-legami-v1`
  (5: gli indici unici sui soli vivi sono quelli della provenienza), `vendite/test-testata-dopo-emissione-v1` (l'elenco
  delle colonne del lock);
* **fixture che scrivevano la colonna parallela accanto alla provenienza**, ora la sola provenienza:
  `script/test-fn-available-actions-offerta-v1` (anche 14-15: il secondo ordine dalla stessa offerta sbatte su
  `uq_ordini_v_sorgente_offerta`; i due ordini dallo stesso preventivo citano un preventivo vero, perché il guard unico
  vuole un documento che esiste), `vendite/offerte_commerciali/test_fn_push_offerta_a_contratto`,
  `vendite/test-annullo-documento-con-legami-v1`, `vendite/test-fattura-origini-v1`,
  `vendite/test-documento-lineage-seminata-v1`;
* **lettori della colonna parallela**, ora della provenienza: `vendite/test-fn-push-preventivo-a-ordine-v1` (3, 8b),
  `vendite/offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1` (13),
  `vendite/test-sorgente-testate-ordini-contratti-v1` (5-7; l'azzeramento delle colonne prima dei lettori non serve
  più), e chi riconosceva il contratto nato dall'offerta da `offerta_id`: `dbops/test-fn-pgtap-crea-contratto-v1` (9,
  10), `vendite/offerte_commerciali/test_offerte_commerciali_end_to_end` (3),
  `vendite/offerte_commerciali/test_offerte_eccezioni_componenti` (20),
  `vendite/offerte_commerciali/test_push_offerta_fissa_qta_operativa` (3, 4),
  `vendite/offerte_commerciali/test_fn_push_offerta_successione` (3, 5), `vendite/test-righe-gemelle-secondo-giro-v1`.
  Gli ultimi due lettori (`successione`, e il 4 di `fissa_qta_operativa`) li ha trovati la regressione: il censimento
  cercava `offerta_id` con un alias del contratto, e lì la colonna è scritta senza alias o in un `JOIN … ON`;
* ⚠️ **un difetto preesistente, corretto nello stesso file:** il test 3 di
  `vendite/test-sorgente-testate-ordini-contratti-v1` (giro T.3) confrontava `regclass::text` con nomi qualificati, la
  trappola del test 1 del giro T.4. Come app è verde perché `vendite` non sta nel `search_path` dell'app; con lo schema
  nel `search_path` è rosso anche su HEAD. Ora schema e nome vengono da `pg_class` + `pg_namespace`.

**La prova del giro T.5** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **i corpi di partenza sono quelli vivi:** i tre changeSet del T.3 (`-85` … `-87`), rieseguiti, danno lo stesso
  `pg_get_functiondef` del vivo su dbdev; il lock è rimontato dai `pg_get_triggerdef` vivi, uguali su scratch e dbdev;
  i COMMENT riscritti partono dal testo vivo, uguale su scratch e dbdev;
* **l'estratto** degli otto changeSet gira intero su scratch e dbdev, nell'ordine dei numeri; dopo, le colonne non
  ci sono più. `plpgsql_check` sui tre verbi: nessun avviso, prima e dopo;
* **equivalenza prima/dopo su tutta la popolazione di dbdev** (fatto datato, 2026-11-07), `EXCEPT ALL` nei due versi,
  zero differenze: `vw_ordini_lista` (597), i documenti vivi di ogni offerta, gli archi della lineage (1551). La
  capability di ogni ordine e contratto (1110) cambia solo in `non_editable_fields`, che perde esattamente
  `documento_origine_tipo`, `documento_origine_id` e `offerta_id` (§8.8);
* **regressione prima/dopo su 386 pgTAP** (tutti `dbops/`, `storico/`, `maintenance/`, e chi nomina ordini, contratti,
  offerte, preventivi, i tre verbi, i loro builder, la lineage, i legami, la lista ordini o i documenti vivi; sullo
  scratch, in sequenza; prima = il file di HEAD senza estratto, dopo = il file dell'albero con l'estratto): 4896 ok
  prima. Fuori dai file allineati i rossi sono gli stessi riga per riga (scope e permessi, rossi da owner per
  costruzione). Tre differenze, spiegate: i due lettori di `offerta_id` sfuggiti al censimento (sopra), allineati e
  poi verdi con e senza l'estratto su scratch e dbdev; il 6 di `dbops/test-processi-registro`, file modificato
  nell'albero dall'altro cantiere (`brief-db-revisione-dbops`): rosso anche senza l'estratto, verde il file di HEAD con
  l'estratto. Non è del giro;
* **i diciassette file del giro, con l'estratto, su dbdev:** verdi, salvo il 30 di
  `vendite/test-annullo-documento-con-legami-v1`, «rosso da owner» già dichiarato; e verdi anche rilanciati con gli schemi
  `vendite`, `config`, `script`, `dbops` nel `search_path` (la prova che al giro T.4 mancava);
* guardrail statici (`scripts/guardrail_*.py`, licenze): verdi.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione (la RLS), la baseline. **Fatto da Tid il 2026-11-07:** apply di `-92` … `-99` e dei due CSV, pgTAP verdi come applicazione.

#### Lotto C — commesse e fatturazione

* `commesse_sorgenti`: da testo alle colonne tipizzate (S-4).
* `commesse_attivita`: conversione all'id per i tipi a chiave `id` (S-5) e `sorgente_riga` riempita. La
  `segment_key` e la chiave del gruppo fatturabile **non** si convertono (D-6).
* `attivita_fatturabili`, nell'ordine:
  1. il pgTAP che costruisce V-3;
  2. la ricerca per `commessa_attivita_id`;
  3. il ritiro dell'impronta (D-1);
  4. il ritiro di `sorgente_*` e `sorgente_origine_tipo_id`, ridondanti (D-3), e del `DEFAULT 0`.
* **V-2:** `vw_preventivi_smistamento_righe` sul BB che risolve.
* **`ATTIVITA` esce dalle sorgenti** e resta in `tipi_entita` (D-2).
* **Voci per il §8 (BE):** `pipeline_repository` (parametro `sorgente_uid: int`), `commesse_repository` e
  `commesse_service`, il dataclass `AttivitaDaFatturare`.

##### Lotto C, i giri (team DB, 2026-11-07)

Quattro giri, ognuno provato da solo. Prima quello che toglie lettori (le colonne dell'attività fatturabile
leggevano la riga di commessa di oggi), poi le due grammatiche che cambiano, il ritiro del tipo per ultimo.

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **C.1** | `attivita_fatturabili` e `fatture_righe` (G5): il pull ritrova la riga emessa per `commessa_attivita_id` (V-3, D-1); i lettori delle colonne dell'attività (normalize, catena dei termini, smistamento V-2) leggono la riga di commessa; via `sorgente_*` e `sorgente_origine_tipo_id` (D-3); `fatture_righe` nel modello (conversione, CHECK, guard unico); il presidio degli orfani perde le due esenzioni | ✅ DB, provato in transazione; ✅ applicato da Tid, pgTAP verdi (2026-11-07) |
| **C.2** | `commesse_sorgenti` (S-4): dal testo alle colonne tipizzate (`sorgente_uid` da `text` a `uuid`, `sorgente_id`), l'unicità sulla chiave nuova, il guard unico al posto del testuale; `fn_link_commessa_sorgente`, `fn_commessa_viva_di_sorgente` e i lettori (archi della lineage, chiudibile, annullabilità dell'ordine, guard della fatturazione immediata, guard dell'emittente, la firma testuale di `fn_get_sorgente_emittente_sr_id`), il builder | ✅ DB, provato in transazione; ✅ applicato da Tid, pgTAP verdi (2026-11-07) |
| **C.3** | `commesse_attivita` (S-5): all'id per i tipi a chiave `id`, `sorgente_uid` a `uuid`, `sorgente_riga` riempita; CHECK di forma e guard unico; la madre e i cinque lister del push; i lettori (legami, ritiro, lineage, origini della fattura, gruppo fatturabile con l'uid dal BB che risolve, D-6); il ramo del ponte per le commesse | ✅ DB, provato in transazione; ✅ applicato da Tid, pgTAP verdi (2026-11-07) |
| **C.4** | `ATTIVITA` esce dalle sorgenti e resta in `tipi_entita` (D-2); il lato «in uscita» su `attivita_fatturabili` si smonta con la convergenza; con lui la correzione di V-7 | ✅ DB, provato in transazione; ✅ applicato da Tid (2026-11-07) |

**Il giro C.1, le scelte** (team DB, 2026-11-07; via di Tid lo stesso giorno, «procedere con lo sviluppo»; nessuna è
un cambio di modello: sono D-1, D-3, S-7, V-2 e V-3 per D-12):

* **La riga già emessa si ritrova per `commessa_attivita_id`** (`-41`). È la FK NOT NULL della provenienza, unica
  (`uq_attivita_fatturabili_commessa_attivita`): non dipende dal formato della `segment_key` e non esce dalla
  commessa (il caveat C1 si chiude). Il pull smette di scrivere `sorgente_*` e `sorgente_origine_tipo_id`, e con loro
  se ne va la lettura del tipo COMMESSA dal catalogo, che serviva solo a scriverle.
* **I lettori passano alla riga di commessa** prima del ritiro: il normalize prende il tipo del documento d'origine
  da `commesse_attivita.sorgente_tipo_id` per la FK, e la riga senza documento (onere, rettifica) prende COMMESSA,
  come prima col ripiego su `sorgente_tipo_id` (`-42`; il trigger si rimonta senza le colonne della provenienza e con
  `commessa_attivita_id` nell'`UPDATE OF`). La catena dei termini parte dalla riga di commessa e cerca ordine e
  preventivo con la regola d'incontro del modello (`-43`): vera oggi e dopo il giro C.3, che non la deve ritoccare.
* **V-2 attraverso la riga di commessa** (`-44`). FATTURATA ed EMESSA_AF cercano le righe di commessa del segmento
  della riga del preventivo (`segment_base = fn_segment_key(PREVENTIVO, uid, riga)`, la stessa chiave di
  IN_COMMESSA), non annullate, e da lì l'attività per `commessa_attivita_id`. ⚠️ Il piano diceva «sul BB che risolve»:
  non serve, perché il tipo è noto (è la regola del giro 0.3: chi sa dove cercare usa la regola d'incontro, non il
  BB), e la chiave del segmento resta sull'uid (D-6). Così i tre stati leggono la stessa chiave.
* **Il ritiro** (`-45`): le quattro colonne con le due FK e il `DEFAULT 0`. Il trigger ATTIVO generato sulla FK
  blocca il `DROP COLUMN` e si toglie prima, con `IF EXISTS` (§11.5: da zero non c'è ancora); il gemello su
  `config.sorgenti` lo ritira il generatore a `ci_apply`, come al giro T.1. Le righe del registro degli indici FK
  escono in `-50`.
* **`fatture_righe` nel modello** (`-46` … `-48`). Le righe nate da una riga di commessa dicevano COMMESSA, la riga
  e un'impronta in `sorgente_uid`: prendono la commessa in `sorgente_id` (la chiave del tipo), l'impronta se ne va
  (S-7: tipo e riga restano). Coi trigger spenti e riaccesi com'erano (la riga di una fattura emessa è bloccata), solo
  dove la riga di commessa c'è: un orfano ferma il CHECK, ed è voluto (S-6). Poi il CHECK di forma, i COMMENT delle
  colonne al presente, tre indici «chi deriva da X» e il guard unico, livello DOCUMENTO e azione BLOCCA.
* **Il presidio degli orfani** (`-49`) perde le esenzioni delle due tabelle: `attivita_fatturabili` esce dal perimetro
  da sola (non ha più le colonne), `fatture_righe` è UNICO. Resta il log dei reconcile.
* **Firme e COMMENT.** Firme con `%TYPE` dagli ultimi YAML (`20261031-47`, `20260227-06`, `20261008-70`,
  `20261106-20`), che rieseguiti danno lo stesso `pg_get_functiondef` del vivo su dbdev e scratch; COMMENT riscritti
  al presente (`linee-guida-sql` §5d), quello della catena dei termini con la firma ancorata.

**Che cosa cambia per chi legge, dichiarato:**

* **Il pull non si ferma più su una riga liberata** la cui chiave del segmento è cambiata dopo l'emissione (V-3). Su
  dbdev (fatto datato, 2026-11-07, prova a secco su 366 commesse): 4 righe in 2 commesse passano da «inserita» ad
  «aggiornata». Sono attività liberate con l'impronta stantia: un giro vero le avrebbe fermate con `23505`.
* **Lo smistamento mostra FATTURATA ed EMESSA_AF** (V-2): su dbdev 13 righe di preventivo passano da IN_COMMESSA a
  FATTURATA; le altre colonne della vista sono identiche.
* **`attivita_fatturabili` non ha più `sorgente_*`**: il BE le legge in due punti e gli smoke le scrivono (§8.9).
* **Una riga di fattura con una provenienza** ora è validata dal guard unico: la parte IVA del plafond che ricopia la
  provenienza della capofila senza `sorgente_id` è rifiutata dal CHECK (§8.9, BE-C.1-c).

**I changeSet del giro C.1:** `20_code/vendite/20261107-41` (il pull), `-42` (il normalize e il suo trigger), `-43`
(la catena dei termini), `-44` (lo smistamento), `00_schema/vendite/-45` (via le colonne di `attivita_fatturabili`),
`-46` (`fatture_righe`: conversione, CHECK, COMMENT), `-47` (i tre indici), `20_code/vendite/-48` (il guard unico),
`20_code/dbops/-49` (il perimetro degli orfani), `80_data/changelog/-50` (il registro degli indici FK). Nessun codice
nuovo, nessun CSV, nessuna funzione nuova. pgTAP: nuovo `vendite/test-sorgente-attivita-fatturabili-v1` (20);
allineati i presidi `dbops/test-sorgenti-struttura-v1` (il debito perde le due tabelle), `dbops/test-sorgenti-orfane-v1`
(test 3: un'esenzione sola), `vendite/test-sorgente-commenti-al-presente-v1` (l'elenco chiuso) e i file che scrivevano o
leggevano le colonne ritirate (sotto).

**Gli allineamenti dei pgTAP (nove file):**

* **i presidi:** `dbops/test-sorgenti-struttura-v1` (2: il debito perde le due tabelle; nomi dal perimetro),
  `dbops/test-sorgenti-orfane-v1` (3: un'esenzione sola; i nomi da `pg_class`), `vendite/test-sorgente-commenti-al-presente-v1`
  (l'elenco chiuso prende le tre funzioni, il perimetro, `fatture_righe` e i tre indici);
* **chi scriveva le colonne ritirate:** `vendite/test-attivita-fatturabili.sql` (22: al posto del «DEFAULT 0» l'assenza
  delle colonne; 30-31 senza le colonne), `vendite/test-fatturazione-draft.sql` (la fixture);
* **chi le leggeva:** `vendite/test-commesse-core-functions-v1` (la propagazione: la provenienza è la riga di commessa),
  `vendite/test-resolve-termini-livello-sorgente-v1` (1: l'invariante di forma riscritta sulla forma che resta),
  `vendite/test-sorgente-origine-tipo-doc-fiscale-v1` (1, 2, 6, 9, 10: §26 resta, il tipo d'origine si legge dalla riga
  di commessa), `vendite/test-porta-oneri-giro-completo-v1` (8: un secondo pull non crea una seconda AF).

**La prova del giro C.1** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **i corpi di partenza sono quelli vivi:** i quattro YAML di partenza, rieseguiti, danno lo stesso
  `pg_get_functiondef` del vivo (con clausole e privilegi) su dbdev e scratch;
* **l'estratto** dei dieci changeSet gira intero su scratch e dbdev; su dbdev le 8 righe di fattura con COMMESSA
  passano alla commessa della loro riga (8 su 8), il presidio degli orfani è vuoto, il guard è montato con argomenti
  validi, le sette viste sopra lo smistamento restano; `plpgsql_check` sulle tre funzioni: solo l'avviso noto (STABLE
  che chiama `fn_log_and_raise_error`);
* **il ramo nuovo si costruisce:** `vendite/test-sorgente-attivita-fatturabili-v1` 20/20 su scratch e dbdev. Senza
  l'estratto è rosso dalla forma (1-3) e al 5 riproduce V-3 esattamente: `23505 uq_attivita_fatturabili_commessa_attivita`;
* **equivalenza prima/dopo su tutta la popolazione di dbdev:** catena dei termini di ogni attività (64), zero
  differenze nei due versi; smistamento e pull a secco: le differenze dette sopra, nessun'altra;
* **regressione prima/dopo su 270 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina attività fatturabili, righe di
  fattura, righe di commessa, il pull, la catena dei termini, lo smistamento e le sue viste, il perimetro degli orfani;
  sullo scratch, in sequenza; prima = il file di HEAD senza estratto, dopo = il file dell'albero con l'estratto): 3217
  ok prima. Fuori dai file del giro i rossi sono gli stessi riga per riga (scope e permessi, rossi da owner per
  costruzione). Tre differenze, spiegate:
  * `vendite/test-porta-oneri-giro-completo-v1` (8): leggeva `sorgente_tipo_id` dell'attività. Il censimento cercava
    le colonne con un alias dell'attività, e qui la colonna è letta da una tabella temporanea della fixture. Allineato
    (sotto), poi 9/9 prima e dopo;
  * `dbops/test-trigger-attivo-orfani-v1` (3): il trigger ATTIVO `trg_sorgenti_a10_attivita_fatturabili_block_deact_upd`
    su `config.sorgenti`, gemello della FK ritirata, resta orfano finché non gira il ritiro del generatore. Previsto
    dal test, come al giro T.1: con l'estratto e `dbops.fn_ritira_attivo_orfani()`, 10/10. In CI gira dopo i DROP, su
    dbdev lo fa l'`update` senza `--contexts`. Finché non gira, disattivare una sorgente sbatterebbe su quel trigger;
  * due file troncati nelle **due** corse da un limite d'ambiente («Troppi file aperti» nel caricare
    `llvmjit.so`): `vendite/test-riporta-lotto-a-draft-v1` e `vendite/test-sorgente-righe-vendita-v1`, rifatti con
    `jit = off`: 14/14 e 24/24 prima e dopo, su scratch e dbdev. Non è del giro: la causa è il limite dei file aperti
    del servizio PostgreSQL, vedi «L'apply del giro C.1» qui sotto;
* **i file allineati, con l'estratto, su dbdev**, e rilanciati con gli schemi `vendite`, `config`, `script`, `dbops`
  nel `search_path`: tutti verdi. ⚠️ **Un difetto preesistente, corretto nello stesso file:** `dbops/test-sorgenti-orfane-v1`
  confrontava `regclass::text` coi nomi qualificati (test 3, 6, 8, 9, 10: rossi anche su HEAD con lo schema nel
  `search_path`, verdi come app per caso). Ora i nomi vengono da `pg_class` + `pg_namespace` (`pg_temp.qn`): 12/12 nei
  due modi, su scratch e dbdev. Lo stesso per il test 2 di `dbops/test-sorgenti-struttura-v1`;
* guardrail statici (`scripts/guardrail_*.py`, licenze): verdi.

⚠️ **Un incidente durante il censimento, dichiarato:** un `plpgsql_check` lanciato su **tutte** le funzioni plpgsql di
dbdev in una volta, dentro una transazione col `DROP COLUMN` in prova, ha fatto cadere il backend, e il cluster è
passato da un crash recovery (12:35, 2026-11-07: tutte le connessioni ricominciate). La transazione era aperta ed è
stata annullata: nessun dato toccato (verificato dopo). Da lì il censimento è sui corpi (`pg_get_functiondef`) e il
`plpgsql_check` una funzione alla volta, sullo scratch.

Non coperto, e resta di Tid: la baseline.

**L'apply del giro C.1** (Tid, 2026-11-07): i dieci changeSet entrano su dbdev e sullo scratch al primo `update`. La
convergenza `ci_apply` (`20260926-10`, che rigira a ogni update) cade invece su entrambi con
`apertura del segmento di memoria condivisa "/PostgreSQL.N" fallito: Troppi file aperti`, nel controllo su
`maintenance.job_run_log` dopo un processo (query parallela). La transazione della convergenza si annulla intera; i
changeSet del giro restano, perché Liquibase committa per changeSet. La causa è l'ambiente, non il giro: il servizio
PostgreSQL partiva col limite di sistema di 1024 file aperti per processo, con `max_files_per_process = 1000` e
`io_method = io_uring`, e la sessione lunga della convergenza li esauriva (la stessa causa dei due file troncati della
regressione). Tid alza il limite del servizio (`LimitNOFILE=65536` nel drop-in systemd di `postgresql@18-main`), riavvia
e rilancia: convergenza passata, ritiro del trigger ATTIVO orfano compreso, pgTAP verdi come applicazione. Il requisito
per ogni installazione è scritto in `installazione.md` (§7.3 D, «Aggiunte dal giro C.1»).

**Il giro C.2, le scelte** (team DB, 2026-11-07; via di Tid lo stesso giorno, «riprendi sviluppo»; nessuna è un cambio
di modello: è S-4 con il §4):

* **La forma** (`-59`). La chiave del documento passa dal testo canonico alle due colonne del modello: le righe dei tipi
  a chiave `id` (ordine, contratto, DDT) prendono l'id in `sorgente_id`, quelle del preventivo tengono l'uid in
  `sorgente_uid`, ora `uuid`. Conversione coi trigger spenti e riaccesi com'erano, cast senza rete (il guard testuale
  garantiva la forma: un valore fuori forma ferma il migrate). Poi l'unicità per commessa sulla chiave nuova
  (`uq_commesse_sorgenti_sorgente_commessa`, `NULLS NOT DISTINCT`, il nome nuovo dice la chiave), il CHECK di forma
  (`num_nonnulls = 1`: il tipo è NOT NULL) e i COMMENT delle quattro colonne. Due indici parziali «chi deriva da X»
  (`-60`): per tipo e `sorgente_uid`, per tipo e `sorgente_riga`; per tipo e `sorgente_id` serve l'unicità.
* **Chi lega il tipo della colonna si toglie prima** (pg_depend, dbdev): la lineage degli archi (BEGIN ATOMIC) con la
  sua vista, e i due trigger scritti a mano con `sorgente_uid` in `UPDATE OF`. ⚠️ Provato: senza il DROP, l'`ALTER
  TYPE` muore su `fn_documento_lineage_archi` (scratch, in transazione). Forma di `20261019-87`: DROP senza CASCADE e
  senza IF EXISTS, ricreati da `-66` e `-67` nella stessa corsa.
* **Il guard unico al posto del testuale** (`-69`), livello DOCUMENTO e azione BLOCCA come su tutte le tabelle della
  provenienza, con lo **stesso nome** del testuale: i BEFORE ROW scattano in ordine alfabetico, e il guard
  dell'emittente (`…a10_guard_sorgente_omogeneita_ins_upd`) deve parlare dopo quello che verifica che il documento
  esista. Il lato in uscita è già montato su ordini, preventivi, contratti e DDT (lo legge dai montaggi): da questo
  giro un documento collegato a una commessa non si cancella, nemmeno in bozza (`E_SORG_ORIGINE_REFERENZIATA`).
* **La commessa viva sulle colonne del modello** (`-61`): `(tipo, sorgente_id, sorgente_uid)` con la regola d'incontro.
  Chi ha il documento passa il suo id e il suo uid (la colonna che il key_selector non usa è NULL), chi ha la chiave
  del modello passa quella. DROP della firma testuale + CREATE: il secondo parametro cambia tipo.
* **La porta del link** (`-62`) scrive la chiave che il BB `script.fn_sorgente_chiave` restituisce, senza renderla a
  testo; idempotenza e commessa viva con la regola d'incontro; la chiave del lock advisory resta la stessa stringa.
  ⛔ La firma **non** cambia: `p_sorgente_uid` resta `text` (è la chiave come la passa il chiamante, e il BB la
  traduce), scritto esplicito e non più `%TYPE`: il `%TYPE` di oggi darebbe `uuid` e un overload accanto a quello che il
  chiamante risolve.
* **Il flag di corsia** (`-63`): il guard passa l'id e l'uid del documento alla commessa viva, e la lettura del
  key_selector se ne va. Il messaggio nomina il documento col suo id.
* **L'emittente** (`-64`): check e guard prendono `(commessa, tipo, sorgente_id, sorgente_uid)` e chiamano il
  risolutore sulle colonne del modello del giro 0.3; trigger rimontato con `sorgente_id` nell'`UPDATE OF`. Il **ponte
  testuale** del risolutore (`script.fn_get_sorgente_emittente_sr_id(bigint, text)`) resta senza chiamanti e si ritira
  (`-65`), come il giro 0.3 aveva scritto. Nessun chiamante nel backend.
* **La lineage** (`-66`, `-67`): i rami B, E, F, U leggono `sorgente_uid` (preventivo) e `sorgente_id` (ordine,
  contratto, DDT) senza cast; le quattro chiavi testuali del seme se ne vanno. La vista torna identica (definizione e
  COMMENT confrontati prima e dopo): il suo COMMENT porta ancora i marcatori di storia di ottobre, e resta com'è
  (non è un oggetto del giro; lotto DOC).
* **La fixture** (`-68`): la sorgente ROOT di `dbops.fn_pgtap_crea_commessa` va in `sorgente_id`.
* ⚠️ **Fuori dal giro, dichiarato:** `fn_check_sorgente_chiudibile`, `fn_check_ordine_annullabile`,
  `fn_ritira_commessa_attivita_da_sorgente`, `trgfn_doc_guard_chiusura_sorgente` e `fn_build_gruppo_fatturabile_key`
  nominano `commesse_sorgenti` solo nei commenti del corpo («non è la chiave di `commesse_sorgenti`»): leggono
  `commesse_attivita`, e li riscrive il giro C.3, che cambia la loro chiave. Il piano li elencava qui per il nome.

**Che cosa cambia per chi legge, dichiarato:**

* **La riga del link adesso si verifica.** `sorgente_riga` era «non validata»: i pgTAP passavano `p_sorgente_riga => 1`
  o `2` su link di tipo COMMESSA, un valore che nessuno leggeva. Ora il guard unico la controlla
  (`E_SORG_RIGA_NON_DEL_DOCUMENTO`). La porta in produzione non la scrive (`fn_upsert_commessa_attivita` passa NULL):
  nessun percorso vivo cambia, cambiano i 21 punti dei test (sotto).
* **Un documento in una commessa non si cancella** (BLOCCA): oggi i verbi di cancellazione vogliono la bozza vuota, e
  una bozza non va in commessa; il guard lo rende un vincolo.
* **Il backend** che chiama la commessa viva con la chiave testuale si rompe dall'apply (§8.10).

**I changeSet del giro C.2:** `00_schema/vendite/20261107-59` (la forma, con i DROP della lineage e dei due trigger),
`-60` (i due indici), `20_code/vendite/-61` (la commessa viva), `-62` (la porta del link), `-63` (il flag di corsia),
`-64` (l'emittente e il suo trigger), `20_code/script/-65` (il ponte testuale si ritira), `20_code/vendite/-66` (la
lineage), `-67` (la sua vista), `20_code/dbops/-68` (la fixture), `20_code/vendite/-69` (il guard unico). Il numero
`-59` l'ha dato Tid (da `-51` a `-58` sono di un altro cantiere), ricontato prima di salvare: libero nei file, nei rami
e nei due `databasechangelog`. Nessun codice nuovo, nessun CSV. pgTAP nuovo: `vendite/test-sorgente-commesse-sorgenti-v1`
(22).

**Gli allineamenti dei pgTAP (37 file):**

* **i presidi:** `dbops/test-sorgenti-struttura-v1` (il debito perde `commesse_sorgenti`),
  `vendite/test-sorgente-commenti-al-presente-v1` (l'elenco chiuso prende le sette funzioni, la tabella e i due indici;
  esce il ponte ritirato);
* **il guard testuale** (`script/test-guard-sorgente-polimorfa-testuale-v1`): resta montato solo su
  `pratiche.pratiche_sorgenti` (lo ritira il lotto P), quindi i suoi casi d'INSERT (7-11, 19-21) si scrivono su una
  pratica costruita; il 6 chiede che `commesse_sorgenti` monti il guard unico; i casi della porta (12, 16, 24)
  rileggono `sorgente_id`; il censimento 17 chiede la colonna giusta per il key_selector;
* **chi chiamava il ponte o le firme vecchie:** `vendite/test-commessa-sorgente-emittente-omogeneo-v1` (2, 3, 4 sulle
  colonne; il 7 chiede che il ponte non ci sia), `vendite/test-sorgente-testate-due-grammatiche-v1` (13: il ponte
  ritirato; il vecchio 15 esce, piano 15), `vendite/test-annullo-commessa-v1`,
  `vendite/test-fn-link-commessa-sorgente-multi-sorgente-v1`;
* **chi leggeva o scriveva la chiave in testo:** `dbops/test-fn-pgtap-crea-commessa-v1`,
  `rls/test-rls-commesse-satelliti`, `script/test-sorgente-documento-e-chiave-v1`, `vendite/test-commesse-schema-v1`,
  `vendite/test-commesse-core-functions-v1`, `vendite/test-documento-lineage-v1`,
  `vendite/test-documento-lineage-seminata-v1`, `vendite/test-drop-uq-commesse-attivita-src-uid-partial-v1`,
  `vendite/test-fattura-origini-v1`, `vendite/test-fatturazione-immediata-simmetria-sorgenti-v1` (commenti),
  `vendite/test-genera-scadenze-lotto-v1`, `vendite/test-ordini-guard-transizione-v1`,
  `vendite/test-push-contratto-dalla-madre-v1`;
* **la riga fittizia** (`p_sorgente_riga => 1` o `2` → `NULL`, il link al documento intero come lo scrive la porta):
  `script/test-fn-available-actions-ddt-reason-catch-all-v1`, `vendite/test-annulla-commessa-attivita-v1`,
  `vendite/test-attivita-guardrail-commessa-v1`, `vendite/test-commesse-core-functions-v1`,
  `vendite/test-fn-af-merce-per-riga-chiusura-v1`, `vendite/test-fn-batch-upsert-commessa-attivita-v1`,
  `vendite/test-fn-emit-attivita-propaga-audit-pricing-v1`, `vendite/test-fn-list-ddt-da-pushare-contatore-v1`,
  `vendite/test-guard-tipo-doc-emittibile-v1`, `vendite/test-porta-oneri-contatore-cieco-v1`,
  `vendite/test-porta-oneri-giro-completo-v1`, `vendite/test-sorgente-origine-tipo-doc-fiscale-v1`,
  `vendite/test-tipo-movimento-colonna-v1`, `vendite/test-vw-af-merce-per-riga-v1`,
  `vendite/test-vw-dash-backlog-resi-v1`, `vendite/test-vw-partite-merce-v1`,
  `vendite/test-vw-resi-da-accreditare-contatore-v1`, `vendite/test-vw-situazione-merce-ordine-v1`.

**La prova del giro C.2** (2026-11-07, in transazione annullata, con l'utente di ciascun database):

* **i corpi di partenza sono quelli vivi:** i sette YAML di partenza (`20261106-14`, `20261012-47`, `20260826-51` con
  il `search_path` di `20261103-04`, `20260826-45`, `20261027-37`, `20261106-81`, `20261012-44`), rieseguiti, danno lo
  stesso `pg_get_functiondef` e le stesse clausole del vivo, su dbdev e scratch;
* **l'estratto** degli undici changeSet gira intero su scratch e dbdev; `plpgsql_check` sulle sei funzioni plpgsql
  toccate e sulla madre delle righe, che chiama la porta,, una alla volta e solo sullo scratch: pulito;
* **il ramo nuovo si costruisce:** `vendite/test-sorgente-commesse-sorgenti-v1` 22/22 su scratch e dbdev; senza
  l'estratto è rosso dal test 1 e si ferma al 6;
* **equivalenza prima/dopo su tutta la popolazione di dbdev** (fatto datato): 885 link convertiti (212 contratti, 282
  ordini, 2 DDT in `sorgente_id`; 389 preventivi in `sorgente_uid`), la chiave uguale a quella testuale di prima su
  tutti; commessa viva, emittente e verdetto di omogeneità di ogni link identici (885 su 885); 1551 archi della vista
  identici (B 389, E 282, F 212, U 2) e 2077 archi dal seme di ogni nodo dei rami B, E, F, U identici; vista identica
  (definizione e COMMENT); presidio degli orfani vuoto;
* **regressione prima/dopo su 295 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina il link, la porta, la commessa
  viva, il risolutore dell'emittente, la lineage, il flag di corsia, la fixture della commessa, la madre delle righe, i
  lister del push, i guard e i presidi della provenienza; sullo scratch, in sequenza): 3668 ok prima. 36 file
  diversi, tutti allineati e rilanciati sull'albero di oggi: verdi su scratch e dbdev. Tre rossi restano, gli stessi
  test prima e dopo: `script/test-fn-available-actions-ddt-reason-catch-all-v1` (18),
  `vendite/test-fn-af-merce-per-riga-chiusura-v1` (13), `vendite/test-vw-situazione-merce-ordine-v1` (11 sullo
  scratch; 11 e 17 su dbdev). Non sono del giro;
* guardrail statici (`scripts/guardrail_*.py`, licenze): verdi.

Non coperto, e resta di Tid: la baseline.

**L'apply del giro C.2** (Tid, 2026-11-07): gli undici changeSet entrano sullo scratch (15:30) e su dbdev (15:42), e la
convergenza `ci_apply` (`20260926-10`) passa nella stessa corsa su tutti e due: il limite dei file aperti alzato dopo
il giro C.1 tiene. pgTAP verdi come applicazione. Dopo, il commit del giro e il merge di `Tito-dev` (il BE ha chiuso il
§8 fino al lotto T): il solo conflitto è il brief, che contiene già le righe del BE, quindi si tiene la versione di
`dev/db-tid`.

⚠️ **Dopo l'apply, corretto** (Tid, 2026-11-07, corsa col runner): `script/test-guard-sorgente-polimorfa-testuale-v1`
test 6 confrontava `tgfoid::regproc::text` con il nome qualificato, e col runner (schema `script` nel `search_path`)
il testo esce senza schema. Lo stesso confronto era nel test 5 del pgTAP nuovo (`regprocedure::text`). Ora schema e
nome vengono da `pg_proc` + `pg_namespace` (e `oidvectortypes`): 24/24 e 22/22 su dbdev, con e senza gli schemi nel
`search_path`. È la stessa trappola del `regclass::text` del giro C.1.

**Il giro C.3, le scelte** (team DB, 2026-11-07; via di Tid lo stesso giorno, «riprendere lo sviluppo»). Le due
decisioni di Tid e la conseguenza della prima sono qui sotto; il resto non è un cambio di modello (S-5 con il §4).

* ✅ **D-6 precisata (Tid, 2026-11-07): l'uid della chiave del gruppo fatturabile si legge dalla `segment_key`.** Dopo
  la conversione ordine, contratto e DDT tengono l'id in `sorgente_id` e `sorgente_uid` è NULL, quindi la chiave
  `CODICE:<uid>` non si può più costruire dalla colonna. D-6 diceva «fornito dal BB di risoluzione», ma
  `script.fn_sorgente_documento` fa un `EXECUTE` per riga, e la chiave si calcola dentro le viste di emissione e di
  competenza su tutte le righe di commessa: è il caso che il giro 0.3 aveva escluso per la lineage. La `segment_key`
  contiene l'uid del documento per costruzione (`script.fn_segment_key`), non si converte (D-6) e non cambia dopo
  l'INSERT: le chiavi salvate in lotti, esiti e log restano identiche. Il lettore nuovo sta nella famiglia della
  chiave, accanto a `fn_segment_key_sorgente` e `fn_segment_key_riga`. Le alternative scartate: il BB che risolve
  (SQL dinamico per riga); i join tipizzati in linea su ordini, contratti e DDT (la stessa regola polimorfa copiata in
  una decina di lettori).

* ✅ **Il livello del guard: DOCUMENTO (Tid, 2026-11-07).** Proposto prima RIGA (una riga di push nasce da una riga del
  documento), ma il codice lo smentisce: `fn_contratti_addebiti_maturati` addebita anche le **quote fisse del listino**
  del contratto, che non hanno una riga del contratto (`riga_id` NULL, chiave `CONTRATTO:<uid>:A:<articolo>:M:<mese>`):
  la loro provenienza è il contratto intero. Il guard ha un livello minimo per tabella, non per tipo. Quindi DOCUMENTO,
  come `commesse_sorgenti` e `fatture_righe`: la riga, quando c'è, si verifica (`E_SORG_RIGA_NON_DEL_DOCUMENTO`). Le righe
  di push che vengono da una riga la scrivono sempre; gli **storni** del canone, che oggi escono dal lister con
  `riga_id` NULL, prendono la riga del pezzo che stornano. Scartato: un minimo per tipo nel meccanismo del lotto 0.
* ✅ **Le fixture dei pgTAP (Tid, 2026-11-07).** Il builder `dbops.fn_pgtap_crea_commessa_attivita`, senza sorgente,
  scriveva la **commessa stessa** come provenienza (tipo COMMESSA, l'id della commessa in `sorgente_uid`, una chiave
  `PGT-SEG-…` scritta a mano), e così i pgTAP che chiamano la madre o scrivono la tabella a mano. Non è una provenienza
  del modello. Al suo posto un **consumo vero** (`vendite.attivita_consumi`): è un documento senza righe, lo leggono solo
  il suo lister, il risolutore dell'emittente (dal billing account) e `fn_riporta_attivita_da_emettere`, e ha lo stesso
  tipo documento di default della commessa (FRONTOFFICE). La chiave si costruisce con `script.fn_segment_key`, come
  nel push: con D-6 la chiave del gruppo la legge da lì.

* ⭐ **D-6 revoca una nota del 2026-07-27, e completa G-8.** Il COMMENT della chiave del gruppo diceva «non derivarla
  da segment_key» (`work-done/brief-db-emissione-fattura-per-documento-sorgente`, nota al §A1): i prefissi della chiave
  (`ORD:`, `MAN:`) erano allora «una convenzione di leggibilità, non un contratto». Dal 2026-10-20 non lo sono più: la
  grammatica unica (G-8) ha fatto di `script.fn_segment_key` l'unico costruttore, e `fn_segment_key_sorgente`/`_riga`
  la leggono già come contratto. ⭐ **La conseguenza, proposta DB:** se la chiave del gruppo legge l'uid dalla chiave
  del push, una chiave fuori grammatica lo rende impossibile da costruire, e una chiave con l'uid di un altro documento
  lo sbaglia in silenzio. Un guard nuovo, `vendite.trgfn_commesse_attivita_guard_sorgente_segment` (`20261108-03`,
  `-04`), verifica che la chiave di una riga con provenienza cominci con il codice del tipo e l'uid del suo documento;
  codice `E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO` (TECNICO). Il push la compone sempre così; le fixture e gli smoke
  no (sotto, §8.11).
* **La forma** (`-70`). Le righe dei tipi a chiave id prendono l'id del documento in `sorgente_id`, tradotto dal ponte
  del BB che risolve; quelle del preventivo tengono l'uid, ora `uuid`. La riga del documento passa dalla chiave del push
  (`:R:<riga>`) a `sorgente_riga`, per i tipi che hanno righe; senza `:R:` (quote fisse del listino di un contratto,
  consumi) resta NULL. Coi trigger spenti e riaccesi com'erano; un documento che non si risolve, o una riga che non è del
  suo documento, fermano il migrate (S-6). Prima si tolgono le sei viste che legano la colonna (ricreate da `-93` …
  `-98`), l'indice `(sorgente_uid, competenza_mese)` e il CHECK della coppia; poi il CHECK di forma e tre indici «chi
  deriva da X» (`-71`): per tipo e `sorgente_id`, per tipo e `sorgente_uid`, per tipo e `sorgente_riga`.
* **La madre e il batch** (`-75`, `-76`). La madre traduce la chiave del chiamante con il BB che scrive
  (`script.fn_sorgente_chiave`, come la porta del link) e scrive la riga che il lister restituisce, `p_sorgente_riga` in
  coda (DROP + CREATE). `p_sorgente_uid` resta `text`, la chiave come la passa il chiamante, scritto esplicito: il `%TYPE`
  di oggi darebbe `uuid` e un uid per un tipo a chiave id non si potrebbe più passare. ⚠️ **I lister non cambiano**:
  proiettano già tipo, uid del documento e `riga_id`, e la madre traduce. Il piano li elencava qui per il nome.
* **Gli storni del canone** (`-77`). Uscivano da `fn_contratti_addebiti_maturati` con `riga_id` NULL, cioè perdevano la
  riga del pezzo che stornano: ora la prendono da lui. Le tre letture della riga di commessa del contratto cercano per tipo
  e `sorgente_id`.
* **La chiave del gruppo** (`-72` … `-74`). Il lettore `script.fn_segment_key_uid`, nella famiglia della chiave; la regola
  «l'uid del documento di una riga di commessa» in `vendite.fn_documento_uid_di_attivita`, la chiave del gruppo in
  `vendite.fn_gruppo_fatturabile_key_di_attivita` (regola del 2: la stessa espressione stava in dieci lettori, ed è
  cambiata). Il costruttore `fn_build_gruppo_fatturabile_key` non cambia forma: firma e `DECLARE` passano a `text`
  esplicito, perché il `%TYPE` della colonna in PL/pgSQL si risolve alla prima esecuzione e avrebbe cambiato tipo in
  silenzio.
* **I lettori sulle colonne del modello.** Ritiro e chiudibilità (`-78`, `-79`) prendono tipo, `sorgente_id`,
  `sorgente_uid` con la regola d'incontro, come la commessa viva del giro C.2 (DROP della firma testuale + CREATE); i
  loro quattro chiamanti (`-80` … `-83`) passano id e uid del documento. Legami, legame della lineage, origini della
  fattura, annullo della riga, proiezione sul preventivo (`-84` … `-88`) leggono le colonne del modello; la lista delle
  righe di commessa (`-89`) e le viste di competenza (`-94`) **tengono il contratto col backend**: `sorgente_uid` resta
  `text` ed è l'uid del documento per ogni tipo, letto dal documento o dalla chiave. Esito, selezione e gruppi del lotto
  (`-90` … `-92`) e le viste (`-93` … `-98`) prendono la chiave del gruppo dalla funzione della riga.
* **Il guard unico** (`20261108-02`), livello DOCUMENTO e azione BLOCCA. Il lato in uscita è già montato su documenti e
  righe del catalogo: da qui un documento, o una sua riga, citato da una riga di commessa non si cancella.
* **Le fixture** (`-99`, `20261108-01`). `dbops.fn_pgtap_crea_consumo`, e il builder della riga di commessa che senza
  sorgente costruisce un consumo e con la sorgente compone la chiave del push con l'**uid** del documento, qualunque
  forma di chiave passi il test (difetto trovato dal guard della chiave: col solo id la chiave nominava l'id).
* ⚠️ **Fuori dal giro, dichiarato:** `fn_resolve_termini_pagamento` (la regola d'incontro del giro C.1 regge, il cast
  `::uuid` su una colonna già `uuid` non cambia niente); `fn_riferimento_gruppo_fatturabile` e
  `vw_dash_competenza_gruppi`, che risolvono il documento dalla chiave del gruppo col ponte (la chiave è testo per D-6:
  il lotto Z dirà se il ponte resta per loro); i COMMENT delle sei viste ricreate, che tengono i marcatori di storia del
  vivo (lotto DOC).
* **Le fixture, in dettaglio** (`-99`, `20261108-01`, `-05`). Tre builder: `dbops.fn_pgtap_crea_consumo` (un consumo, con il
  tipo e la chiave del push), `dbops.fn_pgtap_consumo_della_commessa` (lo stesso consumo a ogni chiamata, per i test che
  scrivono più righe sulla stessa commessa: una provenienza, un link) e `dbops.fn_pgtap_provenienza_da_chiave` (la
  provenienza che una chiave del push nomina: tipo, chiave, riga; il verso inverso del push). Il builder della riga di
  commessa prende `p_chiave_etichetta` in coda (DROP + CREATE: è di questo giro). ⭐ **L'etichetta del test si aggiunge
  con `:`, non con `#`**: la base della chiave (`segment_base`, su cui si calcola lo stato del push) è ciò che precede il
  primo `#`, e con `#` righe di etichette diverse avrebbero avuto la stessa base, che in origine non avevano.
* **Numerazione.** Oltre `-99` si passa al giorno dopo (memoria di Tid del 2026-10-18): `20261108-01` … `-05`.

**Il guard della chiave del push (`20261108-03`, `-04`): che cosa guardare prima dell'apply** (proposta DB, non decisa):

* **la regola**: una riga di commessa con un tipo deve avere una `segment_key` che comincia con `<codice_interno del tipo>:<uid del
  documento>` (poi `:`, `#` o la fine). Non guarda la riga (`:R:`): la chiave del gruppo usa solo codice e uid. Le righe senza tipo
  (ONERE manuale, RETTIFICA) passano;
* **perché serve**: con D-6 la chiave del gruppo legge l'uid dalla `segment_key`; senza il guard una chiave con l'uid di un altro
  documento metterebbe la riga nel gruppo sbagliato senza errore. Toglierlo vuol dire accettare quel rischio, dichiarato;
* **chi può sbattere**: il push no (compone la chiave con `script.fn_segment_key` dal documento); i verbi del DB che scrivono righe
  con un tipo (madre, batch, addebiti del contratto) nemmeno, provato dalla regressione; **gli smoke del backend sì** (§8.11,
  BE-C.3-c), e ogni scrittura a mano futura che inventi una chiave;
* **quando parla**: dopo il guard unico (ordine alfabetico, test 4 del pgTAP nuovo), quindi su un documento che esiste; su `UPDATE`
  solo se il `SET` tocca `segment_key` o le colonne della chiave;
* **quanto costa**: una lettura del documento col BB che risolve a ogni `INSERT` (e `UPDATE` di quelle colonne), come il guard unico;
* **il codice**: `E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`, classe TECNICO (la chiave la scrive il codice, non un form): va bene
  la classe, va bene la frase (`La chiave %s della riga di commessa non nomina il documento di origine %s %s.`)?

**Che cosa cambia per chi legge, dichiarato:**

* **La chiave del push di una riga con provenienza è un vincolo**: deve nominare il documento della provenienza
  (`E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`). Il push la compone già così; gli smoke del backend no (§8.11).
* **Un documento, o una sua riga, citato da una riga di commessa non si cancella** (`E_SORG_ORIGINE_REFERENZIATA`, il
  lato in uscita). Prima nessuno lo verificava; una riga di commessa con una provenienza che non esiste ora è rifiutata.
* **La madre verifica la chiave del chiamante** (`script.fn_sorgente_chiave`): una chiave che non è un id o un uuid, o
  un documento che non c'è, sono rifiutati prima di scrivere. Prima la chiave si scriveva com'era, e le fixture ne
  scrivevano di inventate (`EXT-…`, `BEXT-…`).
* **Gli storni del canone escono dal lister con la riga** del pezzo che stornano.
* **Le fixture**: una riga di commessa senza sorgente nasce da un consumo vero, e la madre lega il consumo alla commessa
  (il primo link è ROOT). Una commessa del builder con un'attività ha quindi una ROOT: due pgTAP che la scrivevano a
  mano sono allineati.

**I changeSet del giro C.3:** `00_schema/vendite/20261107-70` (la forma, con i DROP delle sei viste), `-71` (i tre indici),
`20_code/script/-72` (`fn_segment_key_uid`), `20_code/vendite/-73` (la chiave del gruppo, tipo esplicito), `-74` (l'uid del
documento e la chiave del gruppo della riga), `-75` (la madre), `-76` (il batch), `-77` (gli addebiti del contratto), `-78`
(il ritiro), `20_code/script/-79` (la chiudibilità), `20_code/vendite/-80` (il guard della chiusura), `-81` (il ritiro dei
legami), `20_code/script/-82`, `-83` (annullabilità di ordine e preventivo), `20_code/vendite/-84` … `-91` (legami, legame
della lineage, origini della fattura, annullo della riga, proiezione sul preventivo, lista delle righe, esito dei gruppi,
selezione), `20_code/script/-92` (gruppi del lotto), `20_code/vendite/-93` … `-97` e `20_code/script/-98` (le sei viste),
`20_code/dbops/-99` (i consumi delle fixture), `20261108-01` (il builder della riga), `20_code/vendite/20261108-02` (il guard
unico), `-03`, `-04` (il guard della chiave del push), `20_code/dbops/-05` (la provenienza dalla chiave). CSV:
`codici_errore.csv`, `messaggi_errore.csv` (`E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`, messaggio 1458). pgTAP nuovo:
`vendite/test-sorgente-commesse-attivita-v1` (22).

**Da zero, l'indice ritirato (CI, 2026-11-07):** il `-70` toglie `ix_commesse_attivita_sorgente_competenza` senza
IF EXISTS, ma l'indice nasce in `90_end/20260703-58`, che su un database da zero gira dopo tutto `00_schema`. Due
changeSet di contorno, il `-70` resta com'è: `00_schema/vendite/20261107-05` crea l'indice se manca, solo finché
`sorgente_uid` è ancora testo (cioè prima del `-70`); `90_end/20261108-35` lo toglie se il `-58` l'ha ricreato dopo.
Su dbdev girano tutti e due a vuoto.

**Gli allineamenti dei pgTAP (71 file), per forma:**

* **la provenienza fittizia COMMESSA, con chiavi scritte a mano** (`SEG-…`, `PGT-…`, `EXT-…`): passano al consumo della
  commessa, chiave `<chiave del consumo>:<etichetta del test>` (le chiamate alla madre e le scritture dirette, da due
  trasformatori che lavorano sugli argomenti per nome e sulle colonne per posizione);
* **la chiave di un documento vero con la COMMESSA come provenienza** (i lettori della merce, che leggono la bolla o
  l'ordine dalla chiave): la provenienza diventa il documento che la chiave nomina (`dbops.fn_pgtap_provenienza_da_chiave`);
* **documenti inventati** (uid casuali di bolle, ordini, preventivi; righe fittizie `:R:900001`): documenti veri dai
  builder, a livello di documento quando il numero di riga è sintetico; l'etichetta della chiave dove la riga era solo
  un modo di distinguere due righe;
* **i lettori**: la chiave del gruppo dalla funzione della riga; i confronti `ca.sorgente_uid = <uid>::text` con
  `vendite.fn_documento_uid_di_attivita`; le firme nuove di ritiro e chiudibilità; la riga dal lister dove il test fa da
  push (`p_sorgente_riga => riga_id`);
* **i presidi**: `dbops/test-sorgenti-struttura-v1` (il debito perde `commesse_attivita`),
  `vendite/test-sorgente-commenti-al-presente-v1` (l'elenco chiuso prende le funzioni, la tabella e gli indici del giro);
* **i casi in cui il guard aveva ragione**, e il test è stato riscritto sul modello: la riga 4242 fittizia del builder
  (`dbops/test-fn-pgtap-crea-commessa-attivita-v1`), la riga che prende la chiave di un'altra commessa senza la sua
  provenienza (`vendite/test-sorgente-attivita-fatturabili-v1`), lo storno senza riga
  (`vendite/test-push-contratto-canoni-v1`, test 10: fissava il difetto), la sorgente di prova senza documento
  (`vendite/test-fn-list-commessa-attivita-sorgente-codice-interno-v1`);
* **un difetto trovato, non corretto**: V-7 (§3.6), il riferimento di un gruppo di consumi.

L'elenco completo è nel diff del giro (`db/pgtap/`).

**La prova del giro C.3** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **i corpi di partenza sono quelli vivi**: ogni funzione riscritta prende il corpo da `pg_get_functiondef` (dbdev) e la
  firma dall'ultimo YAML che la ancorava; dopo l'estratto, le funzioni con `CREATE OR REPLACE` hanno firma, risultato,
  `SECURITY`, volatilità, `SET`, `COST` e `ROWS` identici al vivo, una sola funzione per nome; cambiano solo le tre
  ricreate apposta (madre, ritiro, chiudibilità). Le sei viste hanno colonne con lo stesso nome e tipo; le due ricreate
  identiche hanno la stessa definizione;
* **l'estratto** dei 39 changeSet gira intero su scratch e dbdev; `plpgsql_check` su 22 funzioni, una alla volta sullo
  scratch: solo gli avvisi noti (STABLE che chiama `fn_log_and_raise_error`, la variabile di ciclo già nei corpi vivi);
* **il ramo nuovo si costruisce**: `vendite/test-sorgente-commesse-attivita-v1` 22/22 su scratch e dbdev; senza l'estratto
  è rosso dal test 1;
* **equivalenza prima/dopo su tutta la popolazione di dbdev** (fatto datato), `EXCEPT ALL` nei due versi, zero differenze:
  la chiave del gruppo di ogni riga di commessa (920), le viste di competenza col contesto di un super admin (706 attività,
  677 gruppi, 141 righe mensili), emittibilità (920), gruppi serviti e righe di lotto (39 e 39), la lista di ogni commessa
  (920), l'annullabilità di ogni ordine e preventivo (1351), i legami di ogni documento dei sei tipi (2000), il legame di
  ogni arco della lineage (1551), le origini di ogni fattura (52), gli addebiti del contratto (6), l'esito dei gruppi di
  ogni lotto (45). La forma: su dbdev 520 righe passano a `sorgente_id`, 388 tengono l'uid, tutte le 908 righe di push
  prendono la riga dalla chiave, e ognuna appartiene al suo documento;
* **regressione prima/dopo su 273 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina un oggetto toccato o i builder della
  commessa; sullo scratch, in sequenza; prima = l'albero senza estratto, dopo = l'albero allineato con l'estratto): 3350
  ok prima, 3372 dopo (il file nuovo), piano 3406 in tutte e due. I rossi restano gli stessi test, numero per numero:
  scope e permessi, rossi da owner per costruzione;
* **i 71 file allineati e il pgTAP nuovo, con l'estratto, su dbdev**: 928 ok su 935; i rossi sono gli stessi test dello
  scratch (scope e permessi), più il 17 di `vendite/test-vw-situazione-merce-ordine-v1`, già rosso solo su dbdev al giro C.2;
* guardrail statici (`scripts/guardrail_*.py`, pre-commit): verdi, tranne `guardrail_pgtap_preambolo`, rosso per due
  file del cantiere della coda lavori (`dbops/test-fn-accoda-lavoro-porta-v1`, `rls/test-rls-coda-lavori-perimetro-v1`,
  committati in `347cc46f02`): non sono del giro.

Non coperto, e resta di Tid: la baseline.

**L'apply del giro C.3** (Tid, 2026-11-07): i 35 changeSet entrano su dbdev (18:49) e sullo scratch (18:49), con i
due CSV dei codici; pgTAP verdi come applicazione. Da qui il guard della chiave del push (`20261108-03`, `-04`) è montato:
gli smoke del backend che scrivono chiavi a mano si rompono (§8.11, BE-C.3-c), come accettato dal piano.

**Il giro C.4, le scelte** (team DB, 2026-11-07; via di Tid lo stesso giorno, al giro e a V-7). Nessuna è un cambio di
modello: sono D-2 e la decisione di Tid su V-7.

* **`ATTIVITA` esce da `config.sorgenti`** (D-2). Niente nasce da un'attività fatturabile: nessuna funzione, né BE né FE,
  la scrive o la legge come provenienza; la provenienza dell'attività è la sua riga di commessa (`commessa_attivita_id`,
  FK NOT NULL) e dal giro C.1 la tabella non ha più colonne `sorgente_*`. Il tipo stava a catalogo come genitore della FK di
  `config.tipi_entita`. Censimento delle FK verso `config.sorgenti` (30, su `id` e su `codice_interno`; dbdev, fatto
  datato): nessuna riga porta il tipo, salvo la gemella in `tipi_entita`.
* **L'entità resta.** `config.tipi_entita.ATTIVITA` tiene le note delle attività (`vendite.note_attivita_fatturabili`,
  `script.fn_scope_note_ef_perimetro`) e la sua chiave di traduzione; `is_sorgente` passa a false e la nota del CSV dice
  il perché.
* **La forma del ritiro** è quella del giro R.2, nei tre posti nell'ordine in cui girano: `tipi_entita.csv`
  (`is_sorgente = f`), `sorgenti.csv` senza la riga, `80_data/changelog/20261108-06` che la cancella dove esiste.
* **Il lato «in uscita»** su `vendite.attivita_fatturabili` lo smonta la convergenza di `90_end` (`20261106-21`) nella
  stessa migrazione: la tabella non è più documento, righe o dettaglio di nessun tipo. Nessun changeSet suo. COMMESSA
  resta l'unico tipo dello scope `PIPELINE_MARKER`.
* **V-7** (`20_code/vendite/20261108-07`): `fn_riferimento_gruppo_fatturabile` cerca la commessa quando il numero
  manca. Forma `MAN:<commessa>`: dalla chiave, come prima. Forma documento senza numero (un consumo): la commessa aperta
  del documento, `vendite.fn_commessa_viva_di_sorgente`, con l'id del documento (lo dà già la risoluzione del numero,
  `fn_get_sorgente_documento_ref`) e l'uid della chiave (`script.fn_sorgente_chiave_uuid`, che non solleva), con la
  regola d'incontro. Firma e `RETURNS` restano `text` esplicito, motivato nel corpo; `DECLARE` ancorato dove c'è una
  colonna. ⚠️ Il limite, dichiarato: un documento che non sta più in una commessa aperta ripiega ancora sulla chiave
  grezza; la dashboard non lo mostra, perché le sue righe vengono dalle righe di commessa da emettere.

**Che cosa cambia per chi legge, dichiarato:**

* **La scheda Critiche del lotto nomina un gruppo di consumi col codice della commessa**, come la dashboard Competenza.
* **Cancellare un'attività fatturabile non passa più dal lato «in uscita»**: niente la cita come provenienza.
* **`config.sorgenti` non ha più l'id 1.** Lo cercava per id un solo pgTAP (sotto), che il censimento sui codici non
  vedeva.

**I changeSet del giro C.4:** `80_data/changelog/20261108-06` (il DELETE), `20_code/vendite/20261108-07` (V-7);
`80_data/sql/config/sorgenti.csv`, `tipi_entita.csv`. Nessun codice d'errore nuovo, nessuna funzione nuova. pgTAP
allineati (cinque): `vendite/test-sorgente-attivita-fatturabili-v1` (+3, 21-23: non è una sorgente, resta un'entità, il
lato in uscita smontato), `vendite/test-riferimento-gruppo-fatturabile-v1` (16 costruisce anche un gruppo di consumi, +1:
17, il codice della commessa), `config/test-sorgenti-scope-pulizia-v1` (5: `PIPELINE_MARKER` è la sola COMMESSA),
`vendite/test-sorgente-commenti-al-presente-v1` (l'elenco chiuso prende la funzione di V-7),
`vendite/test-attivita-fatturabili.sql` (6: chiedeva la sorgente `id = 1`; ora l'entità delle note, per codice).

**La prova del giro C.4** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **l'estratto** dei due changeSet, col caricamento della riga di `tipi_entita.csv` simulato da un UPDATE e la convergenza
  di `90_end`, gira intero su scratch e dbdev; la convergenza smonta un trigger solo,
  `vendite.attivita_fatturabili`; `plpgsql_check` sulla funzione: pulito;
* **i rami nuovi si costruiscono**: con l'estratto i cinque file sono verdi su scratch e dbdev; senza, rossi esattamente
  sui casi nuovi (21-23; 16-17, dove il 16 riproduce V-7: `ATTIVITA_CONSUMI:false`, e il 17 dà la chiave grezza al
  posto del codice della commessa; il 5 dello scope; il 2 del presidio dei COMMENT, che vede i marcatori di storia del
  COMMENT vivo);
* **equivalenza prima/dopo su dbdev** (fatto datato): 88 chiavi di gruppo (dashboard, gruppi, esiti e log dei lotti),
  zero differenze, e la dashboard coincide con la funzione su tutte le sue righe, prima e dopo. Nessun gruppo di consumi
  nella popolazione: il ramo cambiato lo provano solo i casi costruiti (16, 17);
* **regressione prima/dopo su 283 pgTAP** (tutti `dbops/` e `storico/`, e chi nomina `config.sorgenti`,
  `config.tipi_entita`, il riferimento, la lista delle segnalazioni, la dashboard, il lato in uscita e la sua
  convergenza, lo scope `PIPELINE_MARKER`, le note delle attività; sullo scratch, in sequenza; prima = l'albero di HEAD
  senza estratto, dopo = l'albero allineato con l'estratto): 3646 ok prima, 3650 dopo; 37 rossi, gli stessi test numero
  per numero (scope e permessi, rossi da owner per costruzione). Le differenze sono i quattro casi nuovi e **una trovata
  dalla regressione**: il test 6 di `vendite/test-attivita-fatturabili.sql` cercava la sorgente per id, e il censimento
  (sui codici fra apici) non lo vedeva. Allineato, 36/36 su scratch e dbdev;
* guardrail statici: verdi, tranne `guardrail_pgtap_preambolo`, rosso per i due file del cantiere della coda lavori, come
  al giro C.3.

⚠️ **L'apply è arrivato durante la prova** (Tid: dbdev 19:06, scratch 19:07, con i due mirror e la convergenza). Il
«prima» della regressione era già finito (19:03–19:06); il «dopo» è girato in parte sullo scratch già applicato, dove
l'estratto non cambia niente (`DELETE 0`, la convergenza vuota): stesso stato. Il test 6 di
`vendite/test-attivita-fatturabili.sql` era ancora quello di HEAD al momento dell'apply: rosso sui due database fino
all'allineamento di questo giro. Dopo l'apply: `ATTIVITA` non è in `config.sorgenti` ed è entità con `is_sorgente` false,
il lato in uscita su `attivita_fatturabili` è smontato, la funzione ha lo stesso corpo sui due database.

**Dopo l'apply** (Tid, 2026-11-07): pgTAP verdi come applicazione, col test 6 di `vendite/test-attivita-fatturabili.sql` allineato.

Non coperto, e resta di Tid: la baseline.

#### Lotto D — documenti generati e coda di stampa

* `documenti_generati`:
  1. un SQL manuale su dbdev rinumera i progressivi doppi della stessa fattura (V-6);
  2. la conversione;
  3. il guard.
* `fatture_stampa_coda`: `sorgente_uid` si ritira (doppione di `sorgente_id`, che è una FK vera).
* **Voci per il §8 (BE):** il drainer della coda passa `sorgente_id`; `sorgente_documenti_views`; i `*_document_context_builder`.

#### Il giro D.1, le scelte (2026-11-07)

Un giro solo: le due tabelle sono piccole e non hanno lettori DB della chiave (censimento 2026-11-07: nessuna funzione
né vista legge `documenti_generati.sorgente_uid`; della coda, `vendite.fn_accoda_stampe_lotto` la scrive e
`dbops.vw_fatture_stampa_coda_da_guardare` la proietta).

* **`documenti_generati` alla grammatica del modello** (`00_schema/documenti/20261108-14`). Ogni riga passa alla coppia
  del BB che scrive, `script.fn_sorgente_chiave(tipo, chiave text)`: traduce una chiave dell'altra specie leggendo il
  documento, quindi l'uid di un ordine, di una bolla, di un contratto o di una fattura stampata dalla UI diventa il suo
  id, e una chiave che non trova il documento ferma il migrate. Coi trigger spenti e riaccesi com'erano (lo snapshot è
  immutabile, e questa è la migrazione del modello). `sorgente_uid` diventa `uuid`; l'unicità delle versioni
  `uq_documenti_generati_sorgente_progressivo` passa sulla chiave nuova, con lo stesso nome e `NULLS NOT DISTINCT`; il
  CHECK di forma `chk_documenti_generati_sorgente_forma`; via il CHECK «uid non vuoto». I COMMENT delle colonne, che
  non c'erano, al presente.
* **V-6, senza SQL manuale.** Il piano lo prevedeva per rinumerare le due serie di progressivi della stessa fattura.
  Su dbdev non serve (fatto datato, 2026-11-07): le 31 stampe FATTURA sono tutte in forma id, cioè del drenatore; la UI
  non ha mai stampato una fattura. La rete resta nel changeSet: se due versioni della stessa fattura hanno lo stesso
  numero, l'unicità nuova ferma il migrate e si rinumera a mano, prima. Da qui in avanti la serie è una per documento,
  qualunque strada lo stampi (pgTAP, test 6).
* **Il guard unico, `DOCUMENTO` + `BLOCCA`** (`20_code/documenti/20261108-17`). `CANCELLA` non è possibile: il documento
  generato è append-only (`trg_documenti_generati_a10_block_delete_dlt`). Il lato «in uscita» sulle tabelle dei sei
  documenti è già montato.
* **Lo snapshot prende `sorgente_id`** (`20_code/documenti/20261108-16`): le due chiavi si confrontano con
  `IS DISTINCT FROM`, perché una delle due è sempre NULL e `!=` su NULL direbbe «uguale».
* **La coda perde `sorgente_uid`** (`00_schema/vendite/20261108-18`, che toglie anche la vista del presidio,
  `20_code/vendite/20261108-19` per l'accodamento, `20_code/dbops/20261108-20` per la vista ricreata, con
  `security_invoker` e lo stesso GRANT).
* **⚖️ La coda è esente dal guard unico, col motivo** (`20_code/dbops/20261108-21`). Proposta DB, ✅ confermata da Tid (2026-11-07).
  La coda resta nel perimetro (ha `sorgente_tipo_id` e `sorgente_id`), ma la sua chiave è una FK vera verso
  `vendite.fatture`, `ON DELETE CASCADE`. Con il guard unico, `BLOCCA` fermerebbe la cancellazione di una fattura che
  la FK porta via con la sua coda; `CANCELLA` farebbe la stessa cosa della FK una seconda volta. E la cleanup delle
  fatture trova le figlie da `pg_constraint`: senza la FK non vedrebbe la coda. Quindi la FK resta, e la coda entra
  nelle esenzioni del perimetro accanto al log dei reconcile: esente dal **solo** guard, non dal presidio degli orfani.
  ⚠️ Il prezzo, dichiarato: la forma (il tipo è FATTURA) non la verifica nessuno; la tengono l'unico scrittore e la
  FK, che non accetta un id che non sia una fattura. L'alternativa è ritirare la FK e montare il guard con `CANCELLA`:
  costa la cleanup delle fatture.

**Che cosa cambia per chi legge, dichiarato:**

* **Un documento stampato non si cancella** (`E_SORG_ORIGINE_REFERENZIATA`): prima la cancellazione passava e lasciava
  la stampa orfana. Riguarda i sei tipi che si stampano; il caso vivo è stretto (un preventivo o un'offerta si stampano
  dopo l'emissione, ordini, bolle, resi e contratti si cancellano solo da bozza vuota, la fattura numerata non si
  cancella), ma ora la regola sta nel DB e non nel percorso.
* **La lista delle stampe di un documento vede anche quelle del drenatore**: la chiave è una sola.
* **Il BE che scrive o legge la chiave come testo dà errore** fino alle sue voci (§8.13).

**I changeSet del giro D.1:** `00_schema/documenti/20261108-14` (la forma), `-15` (due indici «chi deriva da X»:
`sorgente_uid` e `sorgente_riga`; `sorgente_id` lo serve l'unicità), `20_code/documenti/20261108-16` (lo snapshot),
`-17` (il guard), `00_schema/vendite/20261108-18` (la colonna della coda e la vista), `20_code/vendite/20261108-19`
(l'accodamento), `20_code/dbops/20261108-20` (la vista), `-21` (l'esenzione). Nessun codice d'errore nuovo, nessuna
funzione nuova; firme invariate (`%TYPE` dove c'è la colonna). pgTAP nuovo:
`documenti/test-sorgente-documenti-generati-v1` (18: forma, stampe per uid e per id, una serie per documento, guard,
snapshot, `BLOCCA`, orfani, la coda). pgTAP allineati (quindici): i due presidi del perimetro,
`dbops/test-sorgenti-struttura-v1` (1: due esenzioni; 2: il debito perde le due tabelle del lotto D) e
`dbops/test-sorgenti-orfane-v1` (3: le due esenzioni, trovato dalla regressione); le sei fixture che
stampavano una chiave inventata (`'PGTAP-…'`) stampano un preventivo vero, costruito dal builder nel mondo
dell'operatore (`documenti/test-documenti-generati`, `-eventi`, `-file`, `-template-standard-v1`,
`-template-porta-unica-v1`, `-versione-contesto-v1`, dove le stampe si distinguono per numero e non più per chiave), e
`rls/test-rls-documenti-satelliti` una fattura vera per mondo, costruita e stampata nel contesto del suo operatore; i
quattro della coda tolgono la colonna dalle INSERT (`dbops/test-coda-archiviazione`, `rls/test-rls-fatture-stampa-coda`,
`-write-guard`, `vendite/test-stampa-coda-tipo-documento-v1`), il fondamento chiede che non ci sia
(`vendite/test-stampa-coda-fondamenta-v1`, 4: `hasnt_column`), e il presidio della coda riconosce le sue righe da
`ultimo_errore` (`dbops/test-vw-fatture-stampa-coda-da-guardare`).

**La prova del giro D.1** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **l'estratto** degli otto changeSet, con la convergenza di `90_end`, gira intero su scratch e dbdev. Su dbdev converte
  1.384 stampe (fatto datato): 418 contratti, 106 bolle, 166 ordini e 31 fatture passano a `sorgente_id`, 651 preventivi
  e 12 offerte a `sorgente_uid uuid`; zero orfani, nessuna collisione sull'unicità nuova. La convergenza non monta
  niente (il lato in uscita sui sei documenti c'era già). La vista ricreata resta `security_invoker`, con gli stessi
  privilegi di prima;
* **i rami nuovi si costruiscono**: il pgTAP nuovo è 18/18 con l'estratto su scratch e dbdev; senza, rosso su 15 casi
  (la forma, la stampa per id, il guard, lo snapshot, `BLOCCA`, la coda);
* **regressione prima/dopo su 626 pgTAP** (tutti `dbops/`, `config/`, `documenti/`, `rls/`, `script/`, e chi nomina
  `documenti_generati`, la stampa, la sorgente, la cleanup delle fatture o `genera_documento`; sullo scratch, in
  sequenza; prima = l'albero di HEAD senza estratto, dopo = l'albero allineato con l'estratto): 7607 ok prima, 7608 dopo,
  gli stessi rossi numero per numero (scope, permessi e credenziali, rossi da owner per costruzione). Le differenze: il
  presidio del `-09`, che su HEAD non c'è, e **una trovata dalla regressione**: il test 3 di
  `dbops/test-sorgenti-orfane-v1` elenca anche lui le esenzioni del perimetro, e il censimento (sul presidio di
  struttura) non lo vedeva. Allineato, 12/12 su scratch e dbdev, rosso sul 3 senza estratto. Le quattordici fixture
  allineate danno sullo scratch gli stessi verdi di HEAD;
* **un rosso preesistente, non di questo giro**: il test 16 di `documenti/test-documenti-generati-eventi` (vuole
  `42501` dalla RLS, riceve `23503` dalla FK) è rosso su HEAD su scratch e dbdev, prima di ogni modifica;
* guardrail statici: verdi (preambolo, DDL sui trigger d'automazione, GRANT, preCondition, `runOnChange`, letterali,
  timestamp, v1 congelato).

**Dopo l'apply** (Tid, 2026-11-07, dbdev 23:05, scratch 23:11): pgTAP verdi come applicazione.

Non coperto, e resta di Tid: la baseline.

#### Il giro K.1 — il nome della chiave (richiesta BE, 2026-11-07)

Il BE chiede, per tenere pulito, che il parametro della chiave del documento si chiami `p_sorgente_chiave` nella
madre della riga di commessa e nella porta del link, e che lo seguano la chiave JSON del batch e i chiamanti SQL per
nome. Via di Tid del 2026-11-07, coi progressivi `-22`, `-23`, `-24` e poi il primo libero (`-32`, `-33`, `-34`: da
`-25` a `-31` sono di un altro cantiere).

* **Perché.** Il parametro riceve la chiave come la ha il chiamante, l'id o l'uid in testo, per qualunque tipo: il nome
  `p_sorgente_uid` diceva «uid» anche quando passava un id, e dal modello (S-4) `sorgente_uid` è la colonna `uuid` dei
  tipi a chiave uid. Il tipo resta `text` esplicito, motivato: non è una colonna, è la chiave in testo che il BB che
  scrive traduce.
* **La porta e la madre** (`20_code/vendite/20261108-22`, `-23`): il nome di un parametro non cambia con
  `CREATE OR REPLACE`, quindi DROP + CREATE della stessa firma di tipi (con i `%TYPE` dei changeSet di prima). Nessun
  oggetto dipende dalle due funzioni (`pg_depend`, dbdev e scratch). Corpi dai loro ultimi changeSet, verificati uguali
  al vivo sui due database, col solo nome cambiato (nella porta anche il messaggio del parametro mancante); COMMENT dal
  vivo col nome nuovo; i privilegi tornano uguali (PUBLIC, `zeroerp_app`, il proprietario).
* **I chiamanti per nome** (`-24` il batch, con la chiave JSON `sorgente_chiave`; `-32` la porta degli oneri; `-33`
  l'accredito della riga di reso; `20_code/dbops/20261108-34` il builder pgTAP): `CREATE OR REPLACE`, stesse firme, corpi
  dai loro ultimi changeSet, uguali al vivo.
* **⚖️ Il parametro del builder `dbops.fn_pgtap_crea_commessa_attivita` resta `p_sorgente_uid`** in questo giro: la
  richiesta nomina la madre e la porta, e il builder lo chiamano per nome una trentina di pgTAP. ✅ Tid (2026-11-07):
  si rinomina anche lui, `p_sorgente_chiave`, nel giro K.2, coi pgTAP che lo chiamano.

**I pgTAP allineati:** 53 file, 97 chiamate per nome alla porta o alla madre (sostituite solo dentro le parentesi di
quelle due chiamate: altre venti funzioni hanno un parametro con lo stesso nome, e lì resta); la chiave JSON del batch in
`vendite/test-fn-batch-upsert-commessa-attivita-v1` e `vendite/test-riga-listino-propagata-dalla-commessa-v1`; e
`vendite/test-onere-batch-e-sezione-documento-v1`, trovato dalla regressione (sotto). In tutto 54 file.

* **⚖️ Due nomi per la stessa chiave, trovato dalla regressione.** I cinque lister del push
  (`vendite.fn_list_{preventivi,ordini,ddt,contratti,consumi}_da_pushare`) restituiscono la chiave del documento nella
  colonna `sorgente_uid`, e il batch ora la vuole in `sorgente_chiave`. Il BE costruisce le righe del batch da sé
  (`commesse_repository.py:1150`), quindi gli basta BE-K.1-b; un pgTAP passava invece la riga del lister così com'era
  (`vendite/test-onere-batch-e-sezione-documento-v1`, `to_jsonb(l)`), e lì la chiave arrivava NULL: allineato, copiando
  la colonna nella chiave. ✅ Deciso (Tid, 2026-11-07, «teniamo tutto pulito»): anche la colonna dei lister prende
  il nome `sorgente_chiave` (giro K.2, sotto). Costa cinque `RETURNS TABLE` da ricreare (DROP + CREATE) e i lettori BE della colonna (`commesse_source_handlers`,
  `PushableRow`).

**La prova del giro K.1** (2026-11-07):

* **i corpi** vengono dagli ultimi changeSet delle sei funzioni, verificati uguali al `prosrc` vivo su dbdev e scratch;
  l'SQL estratto dai sei file gira intero sui due database in transazione annullata, con gli stessi privilegi di prima,
  nessun COMMENT che nomini il nome vecchio, e `plpgsql_check` pulito (l'unico avviso, la variabile `i` del batch, c'è
  già sul vivo); un campione di nove pgTAP (madre, porta, batch, oneri, accredito, builder, link, presidio dei COMMENT)
  dà 119 ok su dbdev;
* ⚠️ **l'apply è arrivato durante la regressione** (Tid: il D.1, il K.1 e i changeSet `-25` … `-31` di un altro cantiere,
  dbdev 23:05–23:10, scratch 23:11). Il «dopo» con l'estratto non vale (l'estratto del D.1 su un database già applicato
  si ferma al primo DROP), e il «prima» di HEAD vale solo per i 529 file finiti prima delle 23:11:05 sullo scratch. La
  prova giusta diventa l'albero allineato senza estratto sul database applicato (scratch, 677 pgTAP: tutti quelli del
  giro D.1 e chi nomina la madre, la porta, il batch, gli oneri, l'accredito, il builder o le commesse), confrontato col
  «prima» valido: il «prima» del giro D.1 (HEAD, prima dell'apply, 625 file) e i 529 del K.1. 8207 ok; su 656 file con un
  «prima» valido, diversi due: `dbops/test-fn-get-lookup-codici` (dell'altro cantiere, verde, 11 → 13) e
  `vendite/test-onere-batch-e-sezione-documento-v1`, **il difetto sopra**, allineato e 10/10 su scratch e dbdev. Dei 21
  senza un «prima» valido, uno solo rosso, il 17 di `vendite/test-ordine-al-modello-v1`, dichiarato «rosso da owner»
  nel file stesso.

**Dopo l'apply** (Tid, 2026-11-07): pgTAP verdi come applicazione.

Non coperto, e resta di Tid: la baseline.

#### Il giro K.2 — la chiave col suo nome anche nei lister e nei builder (Tid, 2026-11-07)

Decisione e via di Tid del 2026-11-07 («teniamo tutto pulito»; «sistemare anche i test pgTAP»). Progressivi: `-36`
… `-40` e poi, per indicazione di Tid, `-61`, `-62`, `-63` (`-35` è del rimedio alla CI da zero, riga 7-quadragies-septies; `-41` … `-46` di un altro cantiere).

* **I cinque lister del push** (`20_code/vendite/20261108-36` … `-40`: preventivi, ordini, DDT, contratti, consumi):
  la colonna della chiave del documento si chiama `sorgente_chiave` (prima `sorgente_uid`). È la chiave come la
  riceve la madre (`p_sorgente_chiave`) e come la legge il batch (la chiave JSON `sorgente_chiave`): una riga del
  lister passa al batch così com'è. Il nome di una colonna di `RETURNS TABLE` non cambia con `CREATE OR REPLACE`:
  DROP + CREATE della stessa firma. Nessun oggetto dipende dai lister (`pg_depend`, dbdev e scratch); i chiamanti DB
  (`script.fn_available_actions_ordine`, la riconsegna) non leggono la colonna. Dichiarazione e corpo dall'ultimo YAML
  di ciascuno, corpo verificato uguale al vivo; nel lister dei preventivi cambia anche l'alias (`AS
  sorgente_chiave`). `SECURITY INVOKER` esplicito anche su contratti e consumi, che l'ultimo YAML non dichiarava (è
  il default). Il `plan_cache_mode` del lister DDT resta.
* **⚖️ `%TYPE`, trovato prima di scrivere.** La colonna era ancorata a `vendite.commesse_attivita.sorgente_uid%TYPE`,
  risolta a `text` al CREATE; dal giro C.3 quella colonna è `uuid`, e ricreata la funzione l'ancora avrebbe dato
  `uuid`. Il valore è l'uid del documento in testo, che la madre traduce: `text` esplicito, col perché scritto
  accanto. Le altre colonne restano ancorate e si risolvono ai tipi di prima (prova sotto).
* **I COMMENT dei cinque lister si riscrivono al presente** (linee-guida-sql §5d: il debito si chiude per famiglia
  quando un lavoro riapre gli oggetti): via revisioni, brief, sigle e id di changeSet; restano il comportamento, i
  codici d'errore, gli oggetti con cui lavorano, e la frase nuova sulla chiave. Le frasi superate sono cadute (per
  gli ordini «esclude EMESSA via NOT EXISTS»: oggi decide `script.fn_get_stato_push_segment`). I commenti dentro i
  corpi non si toccano.
* **Il builder `dbops.fn_pgtap_crea_commessa_attivita`** (`20_code/dbops/20261108-61`): il parametro della chiave si
  chiama `p_sorgente_chiave` (prima `p_sorgente_uid`), `text` esplicito come prima. DROP + CREATE della stessa firma
  di tipi; l'unico chiamante DB (`dbops.fn_pgtap_crea_commessa`) lo chiama per posizione. Corpo da `-34` col solo nome
  cambiato (anche nell'esempio d'uso e nel messaggio della guardia); COMMENT dal vivo col nome nuovo.
* **Due esempi d'uso superati, trovati dal censimento** (`-62`, `-63`, via di Tid): il commento d'uso nel corpo di
  `dbops.fn_pgtap_crea_consumo` mostrava `p_sorgente_uid =>` verso la madre (rimasto dal giro K.1), quello di
  `dbops.fn_pgtap_fattura_attivita` verso il builder. `CREATE OR REPLACE`, stessa firma, corpo dall'ultimo YAML col
  solo commento cambiato; del secondo il COMMENT perde il rimando al brief (§5d).

**I pgTAP allineati** (40 file): 31 chiamano il builder per nome (49 sostituzioni, solo dentro le parentesi della
chiamata al builder: altre funzioni hanno un parametro con lo stesso nome, e lì resta); 10 leggono la colonna dei
lister (`pr.sorgente_chiave` da una tabella fatta col lister, `v ->> 'sorgente_chiave'` da `to_jsonb` di una riga del
lister, la riga finta del consumo in `vendite/test-push-contratto-dalla-madre-v1`); `vendite/test-onere-batch-e-sezione-documento-v1`
passa al batch la riga del lister così com'è, senza copiare la colonna (uno dei 10 sta anche fra i 31).

**La prova del giro K.2** (2026-11-07, come `zeroerp_owner`, in transazione annullata):

* **l'SQL estratto** degli otto changeSet gira intero su scratch e dbdev: una funzione per nome; argomenti, risultato
  (salvo la colonna rinominata), privilegi, `plan_cache_mode`, `SECURITY` e volatilità uguali al vivo; corpo
  identico nei lister di ordini, DDT, contratti e consumi; nessun nome vecchio rimasto dove serve; `plpgsql_check`
  pulito. Su dbdev (fatto datato) i lister letti per nome, come il backend, danno la colonna nuova su ogni riga: 17
  preventivi, 131 ordini, 126 bolle, 6 contratti, nessun consumo. dbdev e scratch intatti dopo (md5 di corpi,
  COMMENT e risultati);
* **regressione prima/dopo su 85 pgTAP** (i 40 allineati, chi nomina i lister, il builder o il batch; sullo scratch,
  in sequenza; prima = HEAD senza estratto, dopo = l'albero allineato con l'estratto): 987 ok prima e 987 dopo,
  nessun file diverso, gli stessi sei rossi numero per numero, tutti di scope (rossi da owner per costruzione). Nessun
  apply durante la corsa (`databasechangelog` dello scratch uguale prima e dopo);
* **i 40 allineati senza l'estratto sono tutti rossi** (il builder o la colonna col nome nuovo non esistono): la prova
  vede il cambio;
* guardrail statici: verdi (`runOnChange`, preCondition, letterali, timestamp, DDL sui trigger d'automazione, GRANT,
  preambolo, v1 congelato).

**Dopo l'apply** (Tid, 2026-11-08): pgTAP verdi come applicazione.

Non coperto, e resta di Tid: la baseline.

#### Lotto P — pratiche

* `pratiche_sorgenti`: da testo alle colonne tipizzate (S-4). Si riscrive l'`ON CONFLICT` vivo di
  `pratiche_repository.upsert_pratica_sorgente`.
* **V-1:** `fn_push_offerta_a_contratto` scrive la pratica col BB che scrive. Il pgTAP prova il percorso con una
  pratica.
* `reconcile_errori`: prende la forma delle colonne, senza guard d'esistenza (D-9).
* **Le due fragilità del censimento:** il letterale `'2'` del trigger di reconcile passa al codice;
  `vw_preventivi_pratiche.sorgente_id` (l'id del legame) si rinomina, perché collide con la colonna nuova.

##### Lotto P, il giro (team DB, 2026-11-08)

Un giro solo, P.1: il lotto è una famiglia piccola (due tabelle, quattro lettori, tre scrittori), e le sue parti si
tengono una con l'altra. La colonna cambia tipo, e con lei cambiano le firme che la leggono.

**Il giro P.1, le scelte** (team DB, 2026-11-08; via di Tid lo stesso giorno, «il via al lotto P»; nessuna è un cambio
di modello: è S-4 con il §4, lo stesso passo del giro C.2 su `commesse_sorgenti`):

* **La forma** (`-64`). Le righe dei tipi a chiave `id` (ordine, contratto, commessa) prendono l'id in `sorgente_id`,
  quelle del preventivo tengono l'uid in `sorgente_uid`, ora `uuid`. Conversione coi trigger spenti e riaccesi
  com'erano, cast senza rete (il guard testuale garantiva la forma). Poi l'unicità per pratica e ruolo sulla chiave
  nuova (`uq_pratiche_sorgenti_pratica_sorgente_ruolo`, `NULLS NOT DISTINCT`), il CHECK di forma (`num_nonnulls =
  1`) e i COMMENT delle quattro colonne. Tre indici parziali «chi deriva da X» (`-65`): per tipo e `sorgente_id`, per
  tipo e `sorgente_uid`, per tipo e `sorgente_riga`. L'unicità comincia con `pratica_id` e serve chi parte dalla
  pratica, non chi parte dal documento.
* **L'unicità senza `sorgente_riga`** (Tid, 2026-11-08: «sì»). La regola: in una pratica, con lo stesso ruolo,
  un documento compare una volta sola. Esempio: la pratica 7 ha il preventivo P-12 come ROOT. Senza la riga
  nell'unicità, un secondo link «pratica 7, P-12, ROOT» è rifiutato (o, dai verbi, assorbito dall'`ON CONFLICT`),
  anche se porta una riga. Con la riga dentro, «P-12 intero», «P-12 riga 3» e «P-12 riga 5» sarebbero tre link
  diversi, tutti accettati: lo stesso preventivo tre volte nella stessa pratica. Il link alla pratica è al documento
  (il guard è montato a livello DOCUMENTO), quindi la riga non distingue due link. Oggi nessuno scrive la riga (sempre
  NULL): la scelta non cambia un dato, decide che cosa dirà la regola quando qualcuno la scriverà. Il censimento
  (scheda A.1) proponeva la riga dentro; il giro C.2 l'ha lasciata fuori su `commesse_sorgenti`.
* **Chi lega il tipo della colonna si toglie prima** (pg_depend, dbdev): le due viste
  (`script.vw_pratica_doc_sorgente`, `vendite.vw_preventivi_pratiche`) e il guard testuale. ⚠️ **Il ponte della pratica
  del documento.** `pratiche.fn_pratica_del_documento(bigint, text)` è BEGIN ATOMIC e lega la colonna, ma la chiamano le
  sette viste di lista: toglierla vorrebbe dire toglierle tutte. In `-64` diventa plpgsql (`CREATE OR REPLACE`, stessa
  firma, stesso risultato), che non lega le colonne, e cerca già nelle colonne del modello. La firma tipizzata nasce
  accanto (`-67`), le viste (`-68` … `-74`) e la sintesi della lineage (`-75`) vi passano, il ponte si ritira (`-76`)
  nella stessa corsa.
* **La pratica del documento** (`-67`): `(tipo, sorgente_id, sorgente_uid)` con la regola d'incontro, come la commessa
  viva del giro C.2. Le liste passano l'id e l'uid del documento, senza leggere il `key_selector`. Su
  `pratiche_sorgenti` l'`OR` arriva ai due indici parziali (`BitmapOr`, provato).
* **La sintesi della lineage** (`-75`): il seme della lineage resta testuale (firma pubblica `(bigint[], text[])`), e la
  chiave del nodo si traduce nelle due colonne coi BB canonici `script.fn_sorgente_chiave_id` / `_uuid`.
* **Lo stato del documento** (`-77`): `fn_stato_sorgente(tipo, sorgente_id, sorgente_uid)`, anche il risultato nelle
  colonne del modello. ⚠️ **Due letture e non un OR.** Provato su dbdev: un `OR` sulle due chiavi contro la union
  `script.vw_stato_sorgente` non scende nei rami e la legge per intero (hash join su tutte le tabelle-documento, anche
  per un documento solo). Restano due letture statiche con l'uguaglianza, come prima, ma sulle colonne native. Stessa
  ragione per `vw_pratica_doc_sorgente` (`-81`): un ramo per chiave nella LATERAL.
* **Il reconcile** (`-78`): firma tipizzata, link con la regola d'incontro. Il log dello skip ambiguo scrive la chiave
  del **link**, che ha già la forma del modello.
* **Il log** (`-66`, D-9): `reconcile_errori` prende le due colonne, la conversione ha la rete (una chiave non
  convertibile resta nel messaggio), CHECK «al più una chiave», nessun guard. Il tipo resta facoltativo.
* **E-9, il trigger del reconcile** (`-79`, `-80`): l'unico argomento è il codice del tipo (`'PREVENTIVO'`), id e
  `key_selector` dal catalogo. Un codice che non è un tipo non ferma il cambio di stato: si registra come
  `E_SORG_CONF`.
* **E-10** (`-82`): in `vw_preventivi_pratiche` l'id del link si chiama `pratica_sorgente_id`.
* **Gli scrittori** (`-83` … `-85`): i tre verbi scrivono il link con la provenienza di `script.fn_sorgente_provenienza`,
  come testate e righe dal giro T.3. Un tipo assente o spento dà `E_SORG_CONF` dal BB (prima `E_CONFIG_MANCANTE`
  scritto nel verbo, che ha altri sessanta scrittori e resta). Le firme col `%TYPE` (stessi tipi risolti, nessun
  overload, verificato).
* **Il guard unico** (`-86`), DOCUMENTO e BLOCCA, con lo stesso nome del testuale. Da qui un documento collegato a una
  pratica non si cancella (`E_SORG_ORIGINE_REFERENZIATA`). Per il preventivo la regola stava solo nel BE (S-9). Il lato
  in uscita c'è già su tutti i documenti che una pratica cita: la convergenza in transazione non monta niente di nuovo.
* **Il guard testuale si ritira qui** (`-87`), non nel lotto Z (Tid, 2026-11-08: «da fare»). Senza montaggi il presidio `dbops.fn_check_funzioni_riferimenti_morti` lo
  segnalerebbe «senza alcun trigger». Il lotto Z ritira ancora la `_tipizzata`. ⚠️ **Per il lotto Z:**
  `script.fn_sorgente_chiave_id` / `_uuid` hanno un consumatore in più, la sintesi della lineage, finché il seme della
  lineage è testuale: il ritiro dei due BB va pensato con lei.
* **La firma dei COMMENT** si scrive col `%TYPE` anche in `COMMENT ON` e `DROP FUNCTION` (Tid, 2026-11-08: «ricorda di
  utilizzare %type»). Il tipo esplicito resta solo dove non c'è una colonna: la chiave polimorfa resa a testo, i
  contatori, gli array.

**I changeSet del giro P.1:** `00_schema/pratiche/20261108-64` (la forma, il ponte, i DROP), `-65` (i tre indici),
`-66` (il log), `20_code/pratiche/-67` (la pratica del documento), `20_code/vendite/-68` … `-74` (le sette viste di
lista), `-75` (la sintesi della lineage), `20_code/pratiche/-76` (il ponte si ritira), `-77` (lo stato), `-78` (il
reconcile), `-79` (il trigger del reconcile), `20_code/vendite/-80` (il suo montaggio), `20_code/script/-81`
(`vw_pratica_doc_sorgente`), `20_code/vendite/-82` (`vw_preventivi_pratiche`), `-83` … `-85` (i tre verbi),
`20_code/pratiche/-86` (il guard unico), `20_code/script/-87` (il guard testuale si ritira). Ventiquattro changeSet,
primo progressivo libero dopo `-63` (ricontato nei file, nei rami e nei due `databasechangelog`). ⚠️ Nati come
`20261109-01` … `-24` e rinumerati prima di ogni apply (Tid, 2026-11-08: si parte dall'ultimo libero del giorno).
Nessun codice nuovo, nessun CSV. pgTAP nuovo: `pratiche/test-sorgente-pratiche-sorgenti-v1` (24). Pagina `manual/` del
guard testuale cancellata.

**Gli allineamenti dei pgTAP (12 file):** `dbops/test-sorgenti-struttura-v1` (il debito perde `pratiche_sorgenti`; il
test 4 guarda la sola `_tipizzata`), `vendite/test-sorgente-commenti-al-presente-v1` (l'elenco chiuso prende cinque
funzioni, le due tabelle e quattro indici), `documenti/test-sorgente-documenti-generati-v1` e
`vendite/test-sorgente-commesse-sorgenti-v1` (le sorelle vecchie per nome da `pg_proc`: un `::regproc` su una funzione
ritirata è un errore, non uno zero), `script/test-guard-sorgente-polimorfa-testuale-v1` (restano la porta del link e i
censimenti, 16; escono i casi del guard e delle forme testuali; il nome del file resta), `pratiche/test-guida-avanza-esito-proiettato`,
`pratiche/test-reconcile-tie-break-flusso-origine`, `pratiche/test-pratiche-sorgenti-flusso`,
`pratiche/test-proiezione-stato-sorgente` (29-31 riscritti: le forme testuali non hanno più oggetto),
`vendite/test-vw-stato-sorgente-ddt-reso-v1` (10-11), `vendite/test-fn-genera-pratica-da-preventivo-v1`,
`vendite/test-sorgente-testate-ordini-contratti-v1` (8).

**La prova del giro P.1** (2026-11-08, in transazione annullata, come owner di ciascun database):

* **i corpi di partenza sono quelli vivi**, identici su dbdev e scratch (md5 delle dodici definizioni);
* **l'estratto** dei ventiquattro changeSet gira intero su scratch e dbdev; `plpgsql_check` sulle sei funzioni plpgsql
  toccate e sul trigger (sullo scratch): pulito, salvo l'avviso STABLE/VOLATILE sul `PERFORM fn_log_and_raise_error`,
  che c'era già;
* **il ramo nuovo si costruisce:** `pratiche/test-sorgente-pratiche-sorgenti-v1` 24/24 su scratch e dbdev; senza
  l'estratto è rosso dal test 1 e si ferma al 6;
* **equivalenza prima/dopo su dbdev** (fatto datato): 568 link convertiti (260 preventivi in `sorgente_uid`; 197
  commesse e 111 ordini in `sorgente_id`), la chiave uguale a quella testuale di prima su tutti; uscite identiche
  delle sette liste (371 righe con pratica), di `vw_pratica_doc_sorgente` (260), di `vw_preventivi_pratiche` (260) e
  della sintesi della lineage (134 nodi con pratica, su un seme di 400); le sette viste identiche salvo la chiamata,
  `security_invoker` e COMMENT intatti; firme dei verbi invariate; grant delle viste e funzioni ricreate uguali a
  prima; presidio degli orfani vuoto;
* **i tempi su dbdev** (fatto datato): `vw_pratica_doc_sorgente` intera da 23,7 a 11,7 ms, una pratica da 4,0 a
  2,8 ms; la lista dei preventivi da 13,8 a 12,2 ms; la chiave arriva all'indice in ogni ramo della union;
* **regressione prima/dopo su 64 pgTAP** (chi nomina le due tabelle, le tre funzioni di pratiche, le due viste, le
  sette liste, la sintesi, i tre verbi, il guard testuale e il presidio dei riferimenti morti; sullo scratch, in
  sequenza, ON_ERROR_STOP): 53 uguali, 11 allineati; dopo, 65 file e 1035 asserzioni eseguite su 1035 pianificate,
  verdi su scratch e i 13 toccati anche su dbdev. Un rosso resta, lo stesso prima e dopo:
  `vendite/test-annullo-documento-con-legami-v1` (30). Non è del giro;
* guardrail statici (`scripts/guardrail_*.py`, preambolo pgTAP, licenze): verdi;
* la convergenza del lato in uscita (`dbops.fn_sorgente_converge_uscita`) dopo l'estratto: nessun trigger montato o
  tolto.

Non coperto, e resta di Tid: l'apply, la convergenza `ci_apply` vera, la baseline.

**Per il lotto DOC** (§7.3): restano link alla pagina `manual/` cancellata del guard testuale in
`guide/sorgente-polimorfa.md`, `config/manual/sorgenti.md`, `script/manual/fn_sorgente_chiave_id.md`, `_uuid.md`,
`fn_get_sorgente_emittente_sr_id.md`, `trgfn_guard_sorgente_polimorfa_tipizzata.md`, `vendite/manual/commesse_sorgenti.md`,
`fn_link_commessa_sorgente.md`. Il messaggio di `E_SORG_FORMATO` in `messaggi_errore.csv` nomina il guard ritirato.
Quello di `E_STATO_SORGENTE_PARAM_INVALIDO` dice `sorgente_uid=%s` per una chiave che ora è id o uid. Il perimetro
degli orfani etichetta `reconcile_errori` come `TESTUALE`, perché non ha guard: un'etichetta stantia per una tabella
esente, da rivedere nel lotto Z.

#### Lotto M — magazzino e acquisti

* **Magazzino:**
  * i movimenti passano al tipo del documento + riga + dettaglio (S-3);
  * `uq_mag_movimenti_identita` riscritto **equivalente**, caso per caso (scheda magazzino §2);
  * i sei verbi, `fn_scrivi_movimento`, `fn_storna_movimenti_sorgente`, `fn_check_disponibilita_uscita` (attesa a
    livello riga contro movimento a livello dettaglio: confronto per prefisso), le due viste `dbops`;
  * i quattro indici unici residui delle testate si ritirano.
* ⚠️ **Prima i verbi, poi il ritiro dei tipi.** `fn_cambia_stato_ddt` e `fn_annulla_reso` cercano
  `DDT_VENDITA_PRELIEVO` / `RESO_VENDITA_RIENTRO` senza filtro su `attivo`: se il tipo non c'è, saltano lo storno senza
  errore. I cinque tipi si ritirano solo dopo.
* **Le tre viste `dbops` di magazzino portano anche tre difetti di
  [brief-db-revisione-dbops](brief-db-revisione-dbops.md)** (§8.1 di quel brief), che confluiscono qui per
  decisione di Tid (2026-11-06): le viste si riscrivono una volta sola.
  * **D58** — `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico`: la domanda va alla grana del
    **prelievo** e del **rientro**, non del documento. Il contratto del posting è un movimento per prelievo e un
    carico per rientro: con un `NOT EXISTS` sul documento intero, uno scarico parziale non fa scattare niente;
  * **D29** (+ M22) — `vw_resi_confermati_senza_carico`: lo stato «merce rientrata» si legge da un BB gemello di
    `script.vw_stati_doc_ddt_merce_partita` (`script.vw_stati_doc_reso_merce_rientrata`), non dal letterale
    `'CONFERMATO'`; le note di `presidi.csv` e i COMMENT di `vendite.fn_ddt_muove_merce` / `fn_reso_muove_merce`
    nominano come porta `script.trgfn_doc_stato_solo_dal_verbo`, non le regole ritirate dei guard di transizione;
  * **Q14 ⑧** (+ M23) — `vw_magazzino_movimenti_senza_costo`: gli storni escono (`storno_di_movimento_id IS NULL`).
    Lo storno di un'uscita senza costo è un'entrata senza costo, conseguenza di una causa (il carico senza valore)
    che la vista mostra già. Nella nota del presidio, l'elenco degli scrittori è completo (`fn_posta_trasferimento`,
    `fn_storna_movimenti_sorgente`, `vendite.fn_posta_ddt`, `vendite.fn_posta_reso`) e compare il carico da reso
    senza costo.
  * Il dettaglio (fatto, correzione, presidio, documentazione da riscrivere) sta in `brief-db-revisione-dbops`:
    D58 §2.7, D29 §2.2, ⑧ §4 Q14, M22 e M23 §3.1.
* ⛔ **Promemoria prima del via al lotto M: si riverifica l'analisi delle tre viste.** Non si sviluppa sulla sola
  base di questo elenco:
  1. il censimento di §«Censimento — magazzino e acquisti» (§2.4, «Che cosa si riscrive insieme all'indice»)
     propone per le prime due `m.sorgente_tipo_id = DDT_VENDITA AND m.sorgente_id = d.id`, cioè la domanda sul
     documento intero che D58 dice sbagliata. Va riscritta alla grana di riga e dettaglio, prima di scrivere il
     changeSet;
  2. si rileggono le tre viste e i loro scrittori sulla scheda auto-generata del giorno: D58, D29 e ⑧ sono stati
     scritti il 2026-11-04/06, e il lotto R e il lotto T possono averli cambiati;
  3. si conferma con Tid il pgTAP per ciascuno: bolla con due prelievi e uno solo scaricato (la vista la
     segnala); reso confermato riconosciuto dal BB; uscita senza costo stornata (lo storno non compare, il carico
     che l'ha causata sì).
* ✅ **Riverifica fatta (team DB, 2026-11-08), decisioni di Tid (2026-11-08: «A, B, C ok proposta, per i test
  confermo le tue scelte»).**
  * **Fatti.** Le tre viste sono quelle del 2026-11-04 (le due del posting) e del 2026-10-26 (quella del costo); gli
    scrittori (`vendite.fn_posta_ddt`, `vendite.fn_posta_reso`, `magazzino.fn_scrivi_movimento`) sono del 2026-10-26:
    i lotti R e T non li hanno toccati, l'analisi di D58, D29 e ⑧ regge. Il contratto del posting è più stretto di
    come lo dice D58: **un movimento per prelievo delle righe attive** (`dr.attivo`), **un carico per rientro delle
    righe attive** (`rr.attivo`); il presidio fa la stessa domanda, altrimenti segnala un prelievo che il verbo non
    doveva scaricare. Le tre viste non hanno lettori BE/FE: le leggono `presidi.csv`, `presidi_testi.csv` e tre pgTAP
    (`magazzino/test-reso-carico-v1`, `magazzino/test-fn-scrivi-movimento-valore-v1`,
    `script/test-vw-stati-doc-ddt-merce-partita-v1`).
  * **D58, la domanda alla grana giusta (correzione del censimento §2.4):** per ogni prelievo `p` di una riga attiva
    `dr` della bolla `d`, `NOT EXISTS` di un movimento `sorgente_tipo_id = DDT_VENDITA`, `sorgente_id = d.id`,
    `sorgente_riga = dr.id`, `sorgente_dettaglio = p.id`, `qta < 0`, non storno; per il reso lo stesso con
    `RESO_VENDITA`, il rientro e `qta > 0`.
  * **A — la riga della vista resta la bolla (il reso)**, con in coda una colonna col numero di prelievi (rientri)
    senza movimento: `CREATE OR REPLACE` (colonne esistenti invariate), i testi di `presidi_testi.csv` («alcune
    bolle…») restano veri, e il rimedio è sulla bolla («da dove è passata l'emissione»).
  * **B — D29 con la regola del 2:** nasce `script.vw_stati_doc_reso_merce_rientrata` (gemello di
    `vw_stati_doc_ddt_merce_partita`: uscito dalla bozza, `ordine >=` quello di `CONFERMATO`, non abortito, dal
    catalogo, mai NULL). Nello **stesso giro** passano al BB anche le due copie del letterale `'CONFERMATO'` letto
    come «merce rientrata»: `vendite.vw_resi_righe_effettive` (che si dichiara «helper unico merce tornata
    indietro») e `vendite.vw_resi_da_riconsegnare`. Resta fuori `fn_annulla_reso` (`v_stato NOT IN
    ('DRAFT','CONFERMATO')`): è una regola di transizione, non «merce rientrata».
  * **C — buco nuovo, entra nel lotto M:** nessun presidio vede una bolla di trasferimento CONSEGNATA con un
    prelievo senza il suo `TRASF_IN` (l'arrivo). Si aggiunge come controllo separato alla stessa grana
    (prelievo di riga attiva → entrata `TRASF_IN` non storno), nel giro che riapre le viste.
  * **I pgTAP (confermati da Tid):**
    1. D58: bolla con due prelievi, uno solo scaricato → la vista la segnala. Lo stato rotto i verbi non lo
       producono: il test lo fabbrica da owner, nella sua transazione (secondo prelievo aggiunto dopo l'emissione,
       lock disattivato), perché il presidio esiste per vedere una porta che non ha tenuto. In più: il gemello sul
       reso (due rientri, uno solo caricato) e un prelievo su riga non attiva, che **non** compare;
    2. D29: con i tre stati di oggi BB e letterale rispondono uguale (verde per sottrazione). Il test aggiunge nella
       transazione uno stato dopo `CONFERMATO` (ordine 25, non abortito) con un reso senza carico → la vista lo
       vede; e il controllo sul viewdef senza `'CONFERMATO'`, come il test 8 del BB della bolla;
    3. ⑧: carico senza costo → uscita senza costo → storno: il carico compare, lo storno no. Si fissa anche che
       l'entrata gemella `TRASF_IN` senza costo **resta**: lo storno è neutro sul valore (rende allo stesso
       magazzino una quantità uscita a valore zero, la media torna com'era), la `TRASF_IN` porta quantità senza
       valore in un altro magazzino e lì diluisce la media. Il test impedisce di «semplificare» il filtro in
       «fuori le entrate a costo copiato»;
    4. C: bolla di trasferimento consegnata con un prelievo senza `TRASF_IN` → il controllo la vede.
* **Acquisti** ➡️ **passati all'analisi degli acquisti** (Tid, 2026-11-08: «tutte le tabelle acquisti speculari a
  vendita devono essere riallineate nelle logiche simili»), `analisi-simmetria-ordini-acquisto.md` §4.6-bis. Il
  perimetro che passa, invariato:
  * `ordini` e `ddt`: l'import esce, come in T;
  * `ordini_righe`: `DROP DEFAULT 0`;
  * `ddt_righe`: il guard unico;
  * `acquisti.ddt.ordine_id` confluisce, e la protezione della FK la dà il lato «in uscita» (D-3);
  * il fulfillment d'acquisto resta.
* **Voci per il §8 (BE/FE):** cambia l'API `GET /magazzino/movimenti` (valori di `sorgente_tipo`, `sorgente_id`,
  `sorgente_dettaglio`); in BE `magazzino_repository`, `types.py`, `famiglie.py`, `config/sorgenti.py`; il seed UI
  `lista_colonna.csv`; in FE `vocabolari.js`, `etichette.js`, i locales e quattro componenti. Elenco chiuso nella
  scheda magazzino §8.

##### Lotto M, i giri (team DB, 2026-11-08)

Via di Tid il 2026-11-08 («l'altro cantiere è fermo, puoi iniziare lo sviluppo»). Il lotto si fa in **quattro giri**.
Il registro va per primo e da solo: conversione dei dati, identità, primitiva, verbi e presidi cambiano nello stesso
apply, perché ognuno legge la forma dell'altro.

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **M.1** | il registro (`movimenti`, `movimenti_attesi`): dati convertiti, identità equivalente, primitiva, storno per documento, disponibilità per prefisso, i sette verbi, guard unico; i presidi D58, D29 (+ il BB e le due viste di `vendite`), ⑧, C; M22, M23 | ✅ applicato da Tid, pgTAP verdi, committato (2026-11-08) |
| **M.2** ✅ `ad13694ffb` | le testate di magazzino e l'evento (`inventari`, `rettifiche`, `trasferimenti`, `eventi_assets`): guard unico (DOCUMENTO), CHECK di forma, i quattro indici unici residui si ritirano; la grammatica MODELLO_A esce dal perimetro degli orfani; il guard tipizzato si ritira | ✅ applicato da Tid, pgTAP verdi (2026-11-08), da committare |
| **M.3** | il ritiro dei cinque tipi di foglia: `config.tipi_entita.is_sorgente = false`, poi `config.sorgenti`; il seed pgTAP che li pretende (`magazzino/test-causali-e-sorgenti-seed-v1`) | ✅ applicato da Tid, pgTAP verdi, committato (2026-11-08) |
| **M.4** | acquisti: l'import esce da ordini e DDT, `ordini_righe` perde il `DEFAULT 0`, il guard unico su `ddt_righe`, `ddt.ordine_id` (D-3) | ➡️ **passato** all'analisi degli acquisti (Tid, 2026-11-08): `analisi-simmetria-ordini-acquisto.md` §4.6-bis. Le tabelle d'acquisto si riallineano alla vendita in un cantiere solo |

**Il giro M.1, le scelte** (team DB, 2026-11-08; nessuna è un cambio di modello: è S-3 con il §4, la scheda magazzino
§2 e le decisioni A, B, C):

* **La conversione** (`-94`). I movimenti passano dalla foglia al documento coi trigger della tabella spenti e
  riaccesi com'erano, come nel giro P.1: `DDT_VENDITA_PRELIEVO` → `DDT_VENDITA` + bolla + riga + prelievo,
  `RESO_VENDITA_RIENTRO` → `RESO_VENDITA` + reso + riga + rientro, `*_RIGA` → il documento interno + la riga,
  `EVENTO_ASSET` → l'evento in `sorgente_id`. Gli storni seguono la stessa regola. Un movimento che resta senza la
  chiave del documento ferma il migrate: la conversione non inventa una foglia che non c'è.
* **L'identità** (`-94`) è `(tipo, sorgente_id, sorgente_uid, riga, dettaglio, causale, asset, lotto, ubicazione)
  NULLS NOT DISTINCT`, stesso nome. È equivalente alla vecchia per le due condizioni della scheda §2.2: il guard unico
  verifica la catena e, col livello minimo DETTAGLIO, impone a ogni tipo la foglia più bassa che ha. Le prime due
  colonne servono anche chi cerca per documento (lo storno, i presidi).
* **La forma** (`-94`): `chk_mag_movimenti_sorgente_chiave` diventa «una sola chiave del documento»; quello degli
  attesi, «senza tipo niente, col tipo una sola chiave»: riga e dettaglio li verifica il guard.
* **La primitiva** (`-96`): `p_sorgente_id` e `p_sorgente_dettaglio` in coda; `p_sorgente_riga` è ora la riga del
  documento. Passi 1, 9, 10, 11 e 13 riscritti insieme all'indice, perché frase e rete non divergano.
* **La disponibilità** (`-95`): i due livelli in coda; l'attesa è propria per **prefisso** (scheda §1.2, già nel
  piano): un'attesa del documento intero è propria di ogni sua riga, un'attesa di una riga non lo è di un'altra.
* **Lo storno per documento** (`-97`): la chiave del documento in coda, obbligatoria; `p_sorgente_righe` NULL = tutto
  il documento. Chi lo chiama con la firma di prima (tipo e foglie) riceve `E_MAG_CHIAMATA_NON_VALIDA`, non uno storno
  sbagliato. Resta generico: nessun nome di `vendite` in `magazzino`.
* **I sette verbi** (`-98`, `-99`, `20261109-01` … `-05`): i cinque posting scrivono la provenienza col BB
  `script.fn_sorgente_provenienza`, come testate e righe di vendita dal giro T.3. Un tipo assente o spento dà
  `E_SORG_CONF` (prima `E_CONFIG_MANCANTE`, scritto nel verbo). `fn_posta_reso` rilegge il costo dell'uscita
  d'origine per bolla, riga e prelievo. ⛔ `fn_cambia_stato_ddt` e `fn_annulla_reso` stornano per documento e **non
  saltano più lo storno in silenzio**: un tipo che manca è `E_CONFIG_MANCANTE`. È la trappola del ritiro della scheda
  §0.4: chiusa qui, prima di M.3.
* **Il guard unico** (`20261109-07`), stesso nome del tipizzato: `movimenti` DETTAGLIO e BLOCCA (un ledger non si
  cancella: non c'è un'azione conseguente ammissibile), `movimenti_attesi` DOCUMENTO e BLOCCA. Il lato «in uscita» c'è
  già su tutti i bersagli del catalogo.
* **I permessi**: primitiva e storno ricreati sono riservati come prima, `REVOKE` da `PUBLIC` **e** da `zeroerp_app`.
  Trovato in prova: su dbdev i privilegi di default danno `EXECUTE` all'app su una funzione appena creata, quindi il
  solo `PUBLIC` non bastava. Le due voci sono già in `v_fn_riservate` del loop di `ci_apply` (per nome).
* **I presidi** (`20261109-06` … `-13`), con le decisioni A, B, C: la domanda per prelievo e per rientro di riga
  attiva, con il conteggio in coda; il BB `script.vw_stati_doc_reso_merce_rientrata` e le tre copie del letterale che
  passano a lui; gli storni fuori da `vw_magazzino_movimenti_senza_costo` (e le due colonne nuove in coda); il presidio
  nuovo `dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo` (ZERO, GIORNALIERA, DEFINER), registrato nei due CSV.
  Il letterale `CONSEGNATO` del presidio C non copia quello del verbo: lì è l'evento del passaggio, qui l'insieme degli
  stati in cui l'arrivo deve esserci.
* **M22, M23**: i COMMENT di `fn_ddt_muove_merce` e `fn_reso_muove_merce` (`20261109-14`) e le note di `presidi.csv`
  nominano la porta di oggi; la nota e il COMMENT della spia del costo elencano tutti gli scrittori.
  `codici_errore.csv`: la descrizione di `E_MAG_MOVIMENTO_GIA_REGISTRATO` dice le nove colonne.

**Tre fatti trovati in prova, dichiarati:**

* ⚠️ **Il caso del pgTAP di ⑧ non si costruisce come descritto.** Un carico senza valore porta la media a **zero**, non
  a NULL (`magazzino.vw_costo_medio` = valore / quantità): le uscite dopo di lui hanno costo 0. Un'uscita **senza**
  costo nasce solo quando la giacenza è a zero o sotto, cioè da una causale che ammette lo stock negativo
  (`magazzino.causali.consente_stock_negativo`: la colonna c'è, il seed oggi non ne accende nessuna). Il pgTAP la
  costruisce così, con la primitiva e due causali di prova in transazione. «Il carico che l'ha causata» non c'è: la
  causa è la giacenza a zero, non un carico. La regola della vista non cambia: lo storno non entra, la gemella resta.
  Prima della correzione il test passava a vuoto: lo storno era a costo 0, non NULL.
* **Una riga spenta con prelievi il modello non la ammette** (la riga con prelievi non si spegne, il prelievo vuole
  la riga attiva). Il filtro `dr.attivo` dei presidi segue il contratto del posting, ma non c'è un caso da costruire, e
  il pgTAP non lo finge.
* **Il buco S-9 del reso era già chiuso** dal giro T.4: `trg_resi_a10_guard_delete_solo_bozza_dlt` parla per primo.
  Il registro aggiunge la sua rete: spenta la sola regola di stato, il reso coi carichi non si cancella lo stesso
  (`E_SORG_ORIGINE_REFERENZIATA`), e così una riga di bolla movimentata.

**Debito del giro, dichiarato:** fino al giro M.3 i cinque tipi di foglia restano attivi, e il guard unico accetta un
movimento che li usa senza livelli (la grammatica vecchia sotto il guard nuovo); nessun verbo li scrive più. Fino al giro
M.2 il ramo MODELLO_A del presidio degli orfani non ha un caso costruito (`dbops/test-sorgenti-orfane-v1`, test 5, ora
sul registro): le tabelle che lo montano ancora non le scrive nessuno. ✅ Chiuso dal giro M.2: il ramo non c'è più.

**I changeSet del giro M.1:** `00_schema/magazzino/20261108-94` (forma, conversione, identità), `20_code/script/-95`
(disponibilità), `20_code/magazzino/-96` (primitiva), `-97` (storno), `-98`, `-99`, `20261109-01` (i tre posting di
magazzino), `20_code/vendite/20261109-02`, `-03` (posting di bolla e reso), `-04`, `-05` (annullo di bolla e reso),
`20_code/script/-06` (il BB del reso), `20_code/magazzino/-07` (guard unico), `20_code/vendite/-08`, `-09` (le due viste
del reso), `20_code/dbops/-10` … `-13` (i quattro presidi), `20_code/vendite/-14` (M22). Venti changeSet; `20261109-15`
… `-30` riservati al lotto (accordo con la sessione di `brief-db-revisione-dbops`, che parte da `-31`). CSV:
`dbops/presidi.csv`, `dbops/presidi_testi.csv`, `config/codici_errore.csv`. Nessun codice nuovo. pgTAP nuovi:
`dbops/test-presidi-magazzino-grana-v1` (15), `magazzino/test-sorgente-registro-v1` (15).

**Gli allineamenti dei pgTAP (15 file):** `dbops/test-sorgenti-orfane-v1` (1, 5), `dbops/test-sorgenti-struttura-v1`
(il debito perde il registro), `magazzino/test-ddt-scarico-v1` (7), `-movimenti-attesi-forma-v1` (8, 9),
`-reso-carico-v1`, `-reso-carico-kit-seriali-v1` (il rientro è il dettaglio), `-fn-scrivi-movimento-controlli-v1`,
`-disponibilita-v1`, `-seriali-v1`, `-valore-v1`, `-valore-giacenza-divergenza-owner-v1` (la fixture passa al tipo
`INVENTARIO` e ogni chiamata prende in coda l'inventario della riga), `-movimenti-vincoli-v2` (provenienza del modello;
2-5 con le frasi del guard unico), `rls/test-rls-magazzino-perimetro-v1`. Le note di magazzino restano sui codici
`*_RIGA` di `config.tipi_entita`: sono entità, non sorgenti.

**La prova del giro M.1** (2026-11-08, in transazione annullata, come owner di ciascun database):

* l'**estratto** dei venti changeSet gira intero su scratch e dbdev; `plpgsql_check` sulle dieci funzioni toccate
  (scratch) è pulito, salvo gli avvisi che c'erano già (variabili mai lette, STABLE con il raise);
* **la conversione su dbdev** (fatto datato, 2026-11-08): 387 movimenti (DDT_VENDITA 128, RESO_VENDITA 168,
  RETTIFICA 91), per tutti la foglia di prima coincide con la più bassa della provenienza nuova; un `UPDATE` a vuoto
  su tutto il registro passa il guard unico (la catena regge su ogni riga); presidio degli orfani vuoto;
* **equivalenza dei presidi su dbdev**: i due del posting e quello dell'arrivo vuoti prima e dopo; la spia del costo
  dopo = prima meno gli storni; `vw_resi_righe_effettive` (98 righe) e `vw_resi_da_riconsegnare` identiche (`EXCEPT
  ALL` nei due versi); `security_invoker` e ACL al loro posto;
* **i rami nuovi si costruiscono**: i due pgTAP nuovi 15/15 su scratch e dbdev. Senza l'estratto sono rossi (il
  registro si ferma al test 11, i presidi muoiono al primo); una mutazione (la spia del costo senza il filtro sugli
  storni) accende il solo test 11 dei presidi;
* **regressione prima/dopo su 223 pgTAP** sullo scratch (chi nomina un oggetto o un tipo toccato, chi emette bolle,
  conferma resi, posta documenti interni o scrive attese; in sequenza, ON_ERROR_STOP): 206 uguali, 15 allineati,
  verdi anche su dbdev. Seconda corsa intera con l'estratto definitivo, 225 file con i due nuovi: 3119 asserzioni
  verdi su 3173 pianificate; i rossi sono gli stessi della corsa «prima», riga per riga, tutti test di scope o di
  permesso rossi da owner per costruzione (es. `magazzino/test-porta-ledger-v1` 4-7,
  `magazzino/test-documenti-interni-guard-v1` 7, 8, 11), più `vendite/test-annullo-documento-con-legami-v1` (30), già
  noto, e `dbops/test-marcatori-automazione-senza-esecutore-v1` (14), rosso anche senza l'estratto: è il test del
  blocco 7-bis-b di `brief-db-revisione-dbops`, non ancora applicato. Nessuna regressione del giro;
* scratch e dbdev intatti dopo la prova (oggetti nuovi assenti, firma e indice di prima, nessuna causale di prova);
* guardrail statici (`scripts/guardrail_*.py`): verdi.

Non coperto, e resta di Tid: l'apply, la convergenza `ci_apply` vera, la corsa come applicazione, la baseline. **Fatto da
Tid il 2026-11-08:** apply del giro su dbdev, pgTAP verdi.

**Il giro M.2, le scelte** (team DB, 2026-11-08; via di Tid il 2026-11-08, «si procedi con le scelte»: il ritiro del
guard tipizzato anticipato dal lotto Z a questo giro, i CHECK col nome `…_sorgente_forma`):

* **La forma e la conversione** (`20261109-15`). Le quattro tabelle (`inventari`, `rettifiche`, `trasferimenti`,
  `eventi_assets`) perdono i quattro indici unici residui (tipo, uid) e il CHECK del modello A. Le righe passano al
  modello coi trigger spenti e riaccesi com'erano, come nel giro M.1: per un tipo documento o per l'evento (oggetto
  senza righe), con chiave `id`, la chiave va da `sorgente_riga` a `sorgente_id`; un tipo `*_RIGA` di magazzino diventa
  il documento più la riga; la chiave `uid` resta dov'è. ⛔ Una riga che resta col tipo e senza la chiave del documento
  ferma il migrate: una foglia che non c'è più, o un prelievo / un rientro, che una testata (senza
  `sorgente_dettaglio`) non può scrivere. La provenienza resta **facoltativa**, e `sorgente_riga` resta: una testata
  può nascere da una riga di un documento (le testate di vendita non l'hanno, quelle di magazzino sì da prima).
* **Il CHECK di forma** `chk_mag_<tabella>_sorgente_forma`, come sulle tabelle di vendita: tutto NULL, o il tipo con una
  sola chiave del documento. Nessun pgTAP, CSV o codice nominava i nomi vecchi (`…_sorgente_chiave`, grep 2026-11-08).
* **Gli indici «chi deriva da X»**: dodici, non unici e parziali, per `sorgente_id`, `sorgente_uid`, `sorgente_riga` di
  ciascuna tabella, come sulle righe di vendita (giro R.1). Li usa il lato «in uscita» quando si cancella un'origine.
  Nessuna unicità per sorgente: il dominio non ha una regola «un inventario per documento» (scheda magazzino §1.3).
* **Il guard unico** (`20261109-16`), stesso nome del tipizzato: DOCUMENTO e BLOCCA, come le testate di vendita. Un
  documento, o una sua riga, citati da una testata di magazzino o da un evento non si cancellano.
* **Il perimetro e il presidio degli orfani** (`-17`, `-18`): esce la grammatica MODELLO_A, che non ha più tabelle;
  restano UNICO e TESTUALE (acquisti, fino al giro M.4). Corpi dalla doc auto-generata, md5 del corpo di
  `fn_sorgenti_orfane` verificato contro dbdev.
* **Il guard tipizzato si ritira** (`-19`), come la sorella testuale nel giro P.1: senza montaggi farebbe rosso
  `dbops/test-riferimenti-morti-v1` (test 3). Il lotto Z non lo ritira più. Cancellate le sue due pagine
  (`script/funzioni/`, `script/manual/`); la guida `sorgente-polimorfa.md` lo cita ancora, come cita la testuale: è
  del lotto DOC (§7.3).

**I changeSet del giro M.2:** `00_schema/magazzino/20261109-15` (forma, conversione, indici, commenti),
`20_code/magazzino/-16` (guard unico), `20_code/dbops/-17` (perimetro), `-18` (presidio degli orfani),
`20_code/script/-19` (ritiro del tipizzato). Nessun CSV, nessun codice nuovo. Restano liberi `-20` … `-30` per il lotto.
pgTAP nuovo: `magazzino/test-sorgente-testate-v1` (16). Allineati: `dbops/test-sorgenti-orfane-v1` (1: tutte UNICO),
`dbops/test-sorgenti-struttura-v1` (2: il debito è solo acquisti; 4: le due sorelle non esistono più),
`script/test-guard-sorgente-polimorfa-testuale-v1` (2: `hasnt_function`), `vendite/test-sorgente-commenti-al-presente-v1`
(le quattro tabelle, i dodici indici e `fn_sorgenti_orfane` entrano nell'elenco).

**La prova del giro M.2** (2026-11-08, in transazione annullata, come owner di ciascun database):

* l'**estratto** dei cinque changeSet gira intero su scratch e dbdev; `plpgsql_check` su `fn_sorgenti_orfane`: solo gli
  avvisi dell'SQL dinamico che c'erano già;
* **la conversione si costruisce** (scratch): righe nel modello A scritte col guard di prima (un inventario da una bolla
  per id in `sorgente_riga`, una rettifica da `INVENTARIO_RIGA`, un trasferimento da `INVENTARIO`, un evento da una
  bolla) → dopo l'estratto tipo, documento e riga sono quelli del modello, un `UPDATE` a vuoto passa il guard unico,
  presidio degli orfani vuoto, trigger tutti riaccesi. Una rettifica che cita un prelievo (`DDT_VENDITA_PRELIEVO`)
  ferma il migrate con la sua frase;
* **dbdev** (fatto datato, 2026-11-08): nessuna testata ha una provenienza, la conversione non tocca niente; un `UPDATE`
  a vuoto su tutti gli inventari (2) e le rettifiche (94) passa il guard; perimetro 20 UNICO e 6 TESTUALE, orfani zero;
* **i rami si costruiscono**: il pgTAP nuovo 16/16 su scratch e dbdev, rosso senza l'estratto; una mutazione (l'elenco
  `UPDATE OF` dell'inventario senza `sorgente_id`) accende il solo test 13;
* **prima/dopo su 46 pgTAP** sullo scratch (chi nomina le quattro tabelle, i posting dei documenti interni, il perimetro,
  i guard della provenienza, il lato «in uscita», i riferimenti morti): cambiano solo i quattro allineati (rossi prima,
  verdi dopo) e il nuovo; i rossi che restano sono gli stessi nelle due corse, test di permesso rossi da owner per
  costruzione (`magazzino/test-porta-ledger-v1` 4-7, `-documenti-interni-guard-v1` 7, 8, 11,
  `-blocco-manuale-e-porta-lotto3-v1` 8, `script/test-fn-is-proprietario-tabella-v1` 5, 6). Su dbdev verdi i nove
  file del giro (il nuovo, i quattro allineati, riferimenti morti, lato «in uscita», guard unico, RLS di magazzino);
* scratch e dbdev intatti dopo la prova; guardrail statici verdi.

⚠️ Trovato in prova: la cancellazione dell'origine si prova su una bolla **vuota**. Su una bolla con righe parla prima
la regola «si cancella solo la bozza vuota» del giro T.4, e il test asserirebbe la regola sbagliata.

Non coperto, e resta di Tid: l'apply, la convergenza `ci_apply` vera, la corsa come applicazione, la baseline.

**Il giro M.3, le scelte** (team DB, 2026-11-08; via di Tid il 2026-11-08, «procedi»). Nessuna è un cambio di modello:
è S-2 e S-3, nella forma del giro R.2.

* **Escono da `config.sorgenti`** `INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `DDT_VENDITA_PRELIEVO`,
  `RESO_VENDITA_RIENTRO`. Censimento (dbdev, 2026-11-08, fatto datato): nessuna riga li porta in nessuna colonna con
  FK verso `config.sorgenti` (solo le cinque righe di `config.tipi_entita`); nessuna funzione, vista o policy li usa
  come sorgente. ⛔ L'ordine del piano è rispettato: i verbi prima (giro M.1, l'annullo non salta più lo storno), poi
  il ritiro. `EVENTO_ASSET` resta: è un oggetto senza righe.
* **L'entità resta**, con `is_sorgente = false`: le note di magazzino hanno le loro partizioni
  (`note_inventario_riga`, …) e `script.fn_scope_note_magazzino_ef_perimetro` le nomina. Le chiavi di traduzione
  `config.tipi_entita.<x>` restano. La nota delle cinque righe dice al presente come si scrive la provenienza.
* **La forma del ritiro**, come il giro R.2: `tipi_entita.csv` (`is_sorgente = f`), `sorgenti.csv` senza le cinque
  righe, `80_data/changelog/20261109-20` che le cancella dove ci sono, dopo i due mirror. La convergenza del lato «in
  uscita» non smonta niente: ogni tabella dei cinque è ancora righe o dettaglio di un tipo documento.

**I changeSet del giro M.3:** `80_data/changelog/20261109-20` (il DELETE), `80_data/sql/config/tipi_entita.csv`,
`80_data/sql/config/sorgenti.csv`. pgTAP allineati: `magazzino/test-sorgente-registro-v1` (+16, 17: non più sorgenti,
ancora entità), `magazzino/test-causali-e-sorgenti-seed-v1` (7-9: le sorgenti di magazzino sono i tre documenti
interni, CATALOGO con la tabella delle righe, e l'evento, MAGAZZINO), `magazzino/test-porta-ledger-v1` (la fixture
col tipo INVENTARIO e la chiave del documento). Restano liberi `-21` … `-30`.

**La prova del giro M.3** (2026-11-08, in transazione annullata, come owner, su scratch e dbdev):

* l'estratto (il DELETE, con il caricamento di `tipi_entita.csv` simulato dall'UPDATE che il mirror farebbe) gira:
  5 entità spente, 5 sorgenti cancellate, 17 restano; la convergenza del lato «in uscita» non cambia niente (33
  montaggi prima e dopo);
* **regressione prima/dopo su 188 pgTAP** sullo scratch (chi legge `config.sorgenti`, `config.tipi_entita`, i codici,
  i posting, le note di magazzino, il lato «in uscita», i riferimenti morti): 2629 → 2631 ok; cambiano solo i casi
  16 e 17 del registro (rossi prima, verdi dopo); i 24 rossi sono gli stessi nelle due corse, test di permesso e di
  scope rossi da owner per costruzione, più `script/test-vw-giornale-entita` che si ferma all'avvio in tutte e due;
* su dbdev verdi i sette file del perimetro (registro, seed, livelli, RLS di magazzino, testate, lato «in uscita»,
  orfani); guardrail statici verdi.

⚠️ **Non provato qui: i due mirror veri** (`20251002-21`, `20260822-55`). Il seed simulato non prova il loader: lo
prova l'apply. ✅ **Provato dall'apply di Tid** (2026-11-08, dbdev 12:37, scratch 12:38): i due mirror RERAN,
`20261109-20` EXECUTED; i cinque tipi non sono più in `config.sorgenti` e restano in `config.tipi_entita` con
`is_sorgente` false (verifica DB dello stesso giorno).

#### Lotto Z — chiusura del DB

* ⚠️ **Senza gli acquisti** (passati all'analisi degli acquisti, §4.6-bis di quel documento, 2026-11-08) il lotto Z non
  chiude «tutto vuoto». Resta, come debito **dichiarato e passato**, a elenco chiuso:
  * il debito del presidio di struttura (`dbops/test-sorgenti-struttura-v1`, test 2): `acquisti.ddt`, `ddt_righe`,
    `ordini`, `ordini_righe`, che si svuota col cantiere acquisti. Una tabella nuova senza il guard resta rossa;
  * il ramo TESTUALE di `dbops.fn_sorgenti_orfane` (la chiave in `sorgente_uid` letta con la regola del ponte), che legge
    solo quelle quattro tabelle: si ritira con loro. ⚠️ Precisato al giro Z.4 (2026-11-08): l'etichetta `TESTUALE` del
    perimetro (`dbops.fn_sorgenti_orfane_perimetro`) vuol dire «senza il guard unico», e copre anche le due esenzioni
    (`pratiche.reconcile_errori`, esclusa dagli orfani col motivo; `vendite.fatture_stampa_coda`, senza `sorgente_uid`,
    che il ramo salta). Quando il ramo si ritira, l'etichetta delle due esenzioni si rinomina (per esempio `ESENTE`),
    nello stesso giro degli acquisti.
  Il ponte del BB che risolve (`script.fn_sorgente_documento_da_chiave`) non dipende dagli acquisti: lo leggono la
  lineage di vendita e un builder pgTAP (dbdev, 2026-11-08).
* Il ponte del BB che risolve è vuoto: un pgTAP lo verifica.
* Si ritirano `script.fn_sorgente_chiave_id/_uuid`, la colonna
  `config.sorgenti.categoria` e lo scope `ROW_VALIDATOR`.
* Il controllo d'esistenza della sorgente nei guard di dominio di bolla e reso (`E_DOC_SORGENTE_NON_TROVATA` in
  `trgfn_ddt_guard_cliente_sorgente` / `fn_ddt_vincoli_cliente` e nei trigger del reso) è un doppione del guard unico
  dal giro T.2: si ritira, e il guard di dominio tiene solo la regola del cliente (regola del 2).
* Il §8 (richiesta BE/FE) è completo e chiuso.
* Le richieste del BE al DB (§8.16, 2026-11-08): R-P.1-1 (una sede DB per flusso della regola d'ancora, con la regola
  d'ordine da decidere con Tid) e R-P.1-2 (`E_PRATICA_SORGENTE_TIPO_INVALIDO` si ritira dai CSV dei codici e dei
  messaggi). Si chiudono nel giro DB di fine cantiere, insieme ai difetti che il lotto BE/FE raccoglie.
* La regola «si cancella solo la bozza vuota» a DB su `vendite.preventivi`, `vendite.offerte_commerciali` e
  `vendite.commesse`, come il giro T.4 per ordini, bolle, resi e contratti (Tid, 2026-11-08, seguito di BE-P.1-e,
  §8.16). È la regola della tabella padre che S-9 chiede prima di ogni azione sui figli polimorfi. Prima si censiscono
  gli stati iniziali e le righe di ciascuno (le commesse hanno attività, non righe) e i chiamanti che cancellano.

##### Lotto Z, il censimento e i giri (team DB, 2026-11-08)

Via di Tid il 2026-11-08 («procedi»). Il censimento (dbdev, 2026-11-08: corpi da `pg_get_functiondef`, viste,
policy, BE, pgTAP) smentisce **tre** punti del piano, scritto il 2026-11-06 prima dei giri che li hanno cambiati.
Sul modello, non sui dati: ognuno è una proposta per Tid (Z-a, Z-b, Z-c sotto).

* **Il ponte del BB che risolve non ha più rami per tabella.** `script.fn_sorgente_documento_da_chiave` è ormai solo
  «chiave in testo → `script.fn_sorgente_documento`». Lo leggono chiavi che sono testo **per costruzione**, non tabelle
  in una grammatica vecchia: i nodi della lineage (`fn_documento_lineage_legami`), la chiave del gruppo fatturabile
  costruita con l'uid (D-6: `fn_split_gruppo_fatturabile_key`, `fn_riferimento_gruppo_fatturabile`,
  `fn_list_lotto_segnalazioni`, `vw_dash_competenza_gruppi`), `vendite.fn_get_sorgente_documento_ref`, un builder
  pgTAP. «Il ponte è vuoto» vale come **nessuna tabella scrive più la chiave in testo**: lo presidia già
  `dbops/test-sorgenti-struttura-v1` (test 2: fuori dal guard unico solo il debito degli acquisti e le due esenzioni).
  Il COMMENT del ponte («si svuota lotto per lotto») va riscritto al presente.
* **Z-a — `script.fn_sorgente_chiave_id/_uuid` non si possono ritirare.** Sono il lettore della forma canonica di una
  chiave in testo, e chiavi in testo ce ne sono per decisione: la `sorgente_chiave` del BE e della madre (K.1, K.2), i
  nodi della lineage, le chiavi D-6. Li usano il BB che scrive (`script.fn_sorgente_chiave`), il guard unico (l'uid in
  forma canonica), il ponte, la lineage, il presidio degli orfani (ramo TESTUALE). **Proposta: restano**, e il punto
  esce dal lotto Z. ✅ **Tid, 2026-11-08: restano.**
* **Z-b — `config.sorgenti.categoria` non è ricavabile dai livelli.** Il censimento di aprile (scheda magazzino §7.3)
  lo dava per ridondante con `righe_table`: non lo è, perché `EMAIL` e `ATTIVITA_CONSUMI` sono documenti senza righe.
  Dopo il giro M.3 l'unico tipo che non è un documento è `EVENTO_ASSET`, ancora con categoria `RIGA`. La legge il BE per
  elencare i tipi documento numerabili (`vendite/db/famiglie_repository.py:335`, `CATEGORIA_SORGENTE_DOCUMENTO`), la
  scrive il builder `dbops.fn_pgtap_crea_sorgente`. **Proposta: la colonna resta, col vocabolario della natura**
  (`DOCUMENTO` / `EVENTO`, `EVENTO_ASSET` da `RIGA` a `EVENTO`, un CHECK sui due valori): dice che cosa è il tipo,
  come proponeva la scheda §7.3. Il BE non cambia. ✅ **Tid, 2026-11-08: resta, `DOCUMENTO` / `EVENTO`.**
* **Z-c — il controllo d'esistenza nei guard di dominio di bolla e reso non è un doppione puro.** Il guard unico
  verifica la sorgente quando la si **scrive**. `vendite.trgfn_ddt_guard_cliente_sorgente` (e
  `trgfn_resi_guard_cliente_ddt`) scattano anche quando cambia **solo il billing account**, e se il documento
  d'origine non si vede (per esempio sotto RLS) rifiutano con `E_DOC_SORGENTE_NON_TROVATA` invece di lasciar passare:
  è il fail-closed del 2026-10-10 («una bolla poteva nascere dall'ordine di un altro emittente col BA del proprio»).
  Toglierlo lo riaprirebbe. **Proposta: resta**, e il COMMENT dice che cosa copre che il guard unico non copre. ✅ **Tid, 2026-11-08: resta.**
* **R-P.1-1 — la regola d'ancora per flusso** (richiesta BE, §8.16). La vista per pratica (`script.vw_pratica_doc_sorgente`)
  ordina: documento risolto, non terminale, ROOT, il più recente. La copia BE per flusso (`_doc_sorgente_lateral`):
  ROOT, il più recente. Un flusso ha un solo ROOT (`uq_pratiche_sorgenti_flusso_root`): la differenza conta solo per
  un flusso senza ROOT con più collegati. **Proposta: una vista `script.vw_flusso_doc_sorgente`**, una riga per
  `flusso_id`: prima il ROOT (è il documento del passo, per definizione), poi lo stesso spareggio della pratica
  (risolto, non terminale, il più recente). La copia BE si ritira. ✅ **Tid, 2026-11-08: ROOT, poi lo spareggio della
  pratica.**

**I giri** (decisioni prese il 2026-11-08; Z.3 confluisce in Z.1):

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **Z.1** | lo scope `ROW_VALIDATOR` esce da `chk_sorgenti_scope` (nessuna sorgente lo usa dal giro R.2); `E_PRATICA_SORGENTE_TIPO_INVALIDO` esce dai CSV dei codici e dei messaggi (R-P.1-2); la natura in `categoria` (Z-b); la vista per flusso (R-P.1-1); i COMMENT del ponte, di Z-a e di Z-c al presente | ✅ applicato da Tid su dbdev e scratch, pgTAP verdi, committato (2026-11-08) |
| **Z.2** | la regola «si cancella solo la bozza vuota» su `vendite.preventivi`, `offerte_commerciali`, `commesse` (Tid, 2026-11-08), come il giro T.4: prima il censimento degli stati iniziali, delle righe (le commesse hanno attività) e di chi cancella | ✅ applicato da Tid su dbdev e scratch, pgTAP verdi (2026-11-08, `20261109-25` … `-27`); resta il commit |
| **Z.4** | chiusura: il §8 completo e chiuso, il debito degli acquisti dichiarato (sopra), il presidio di struttura col suo elenco finale | ✅ fatto (2026-11-08): nessun changeSet; il presidio allineato, il §8 chiuso (§8.22) |

**Il giro Z.1, le scelte** (team DB, 2026-11-08):

* **Lo scope** (`00_schema/config/20261109-21`): `chk_sorgenti_scope` senza `ROW_VALIDATOR`, stesso nome. Nessun seed lo
  scrive (`sorgenti.csv` è l'unico scrittore del catalogo), quindi da zero il CHECK non incontra righe che lo violano.
* **La natura** (Z-b): il COMMENT di `categoria` in `-21`; `sorgenti.csv` porta `EVENTO_ASSET` a `EVENTO`; NOT NULL e
  `chk_sorgenti_categoria` (`DOCUMENTO` / `EVENTO`) in `90_end/20261109-22`, dopo il mirror: in `00_schema`
  fermerebbero dbdev, che ha ancora `RIGA`. ⛔ Il mirror su dbdev e scratch **non può** scrivere il valore nuovo:
  `categoria` è sotto lucchetto (`trg_sorgenti_a10_lock_columns_upd`), e un mirror di `80_data` gira prima di ogni
  changeSet datato oggi. Il dato si corregge a mano prima del migrate (D-12):
  [`sql-una-tantum-sorgenti-categoria-evento.sql`](sql-una-tantum-sorgenti-categoria-evento.sql), in una transazione,
  con la porta del lucchetto aperta solo lì. Da zero non serve: la riga nasce con un INSERT, già `EVENTO`.
* **Il codice ritirato** (R-P.1-2): `E_PRATICA_SORGENTE_TIPO_INVALIDO` prende `obsoleto_dal = 2026-11-08` in
  `codici_errore.csv`, con la nota del perché. Non si cancella: è la regola della guida dei messaggi d'errore («ritirare
  un codice, non cancellarlo»: `dbops.error_log` ci punta).
* **La vista per flusso** (`20_code/script/20261109-23`, R-P.1-1): `script.vw_flusso_doc_sorgente`, una riga per
  `flusso_id`, stesse colonne della gemella per pratica più `flusso_id`; prima il ROOT, poi risolto, vivo, il più
  recente. `security_invoker=on`; i privilegi li dà il loop di `ci_apply`.
* **I COMMENT** (`20_code/script/20261109-24`): il ponte al presente (le chiavi testo per costruzione, Z-a); i due guard
  del cliente dicono che cosa coprono che il guard unico non copre (Z-c). Nessun corpo cambia.

**I changeSet del giro Z.1:** `00_schema/config/20261109-21`, `20_code/script/-23`, `-24`, `90_end/20261109-22`; CSV
`config/sorgenti.csv`, `config/codici_errore.csv`; SQL una tantum `sql-una-tantum-sorgenti-categoria-evento.sql`.
pgTAP nuovo: `pratiche/test-vw-flusso-doc-sorgente-v1` (7). Allineato: `config/test-sorgenti-scope-pulizia-v1` (+10:
`ROW_VALIDATOR` rifiutato; +11: la natura). Restano liberi `-25` … `-30`.

**La prova del giro Z.1** (2026-11-08, in transazione annullata, come owner, su scratch e dbdev, nell'ordine del
migrate: l'una tantum, `-21`, `-23`, `-24`, i due mirror simulati, `-22`):

* l'estratto gira su tutti e due; senza l'una tantum il lucchetto rifiuta l'UPDATE di `categoria`: il migrate si
  ferma sul mirror, non scrive niente in silenzio;
* **la vista su dbdev** (fatto datato, 2026-11-08): 14 flussi, lo stesso documento della copia BE per ognuno (tutti
  hanno solo il ROOT); il caso che le distingue (un flusso senza ROOT, un ROOT con un collegato più recente) lo
  costruisce il pgTAP;
* il pgTAP nuovo 7/7 su scratch e dbdev, rosso senza l'estratto; una mutazione (l'ordine della gemella, il ROOT dopo
  lo spareggio) accende il solo test 3. ⚠️ Trovato in prova: la commessa non è proiettata da
  `script.vw_stato_sorgente` (risolto false anche nella vista per pratica), quindi il test 6 prova il ramo NULL-safe;
* **regressione prima/dopo su 325 pgTAP** sullo scratch (chi legge il catalogo delle sorgenti, i codici e i messaggi,
  le viste della pratica, i link, il ponte, i due guard, i COMMENT, i riferimenti morti): 4496 → 4504 ok; cambiano
  solo i due file del giro; i 31 rossi sono gli stessi nelle due corse;
* guardrail statici verdi.

**L'apply del giro Z.1** (dbdev, 2026-11-08, 13:15): il migrate ha applicato `-21`, `-23`, `-24` e si è fermato,
come previsto, sul mirror di `sorgenti.csv` (lucchetto di `categoria`): l'una tantum non era stata eseguita. Niente è
scritto a metà (`EVENTO_ASSET` è ancora `RIGA`, `-22` non c'è). ⏭️ **Per completare:** su dbdev l'una tantum, poi il
migrate; sullo scratch l'una tantum **prima** del migrate. ✅ **Fatto da Tid** (2026-11-08): l'una tantum e il migrate
su dbdev (`-22` alle 13:19) e scratch (13:20); `EVENTO_ASSET` è `EVENTO`, `chk_sorgenti_categoria` c'è,
`E_PRATICA_SORGENTE_TIPO_INVALIDO` ha `obsoleto_dal`; pgTAP verdi (verifica DB dello stesso giorno).

##### Il giro Z.2, il censimento (team DB, 2026-11-08)

Letto sulla struttura di dbdev (vincoli, trigger, corpi da `pg_get_functiondef`, catalogo delle sorgenti, mappa del
modello), sul BE e sui pgTAP. Nessun conteggio di righe entra nelle proposte.

**Gli stati iniziali.** Tutte e tre le testate nascono nello stato iniziale del loro vocabolario
(`script.trgfn_doc_stato_iniziale`), stanno nella mappa del modello (`script.fn_doc_stato_modello`) e nel lettore
dello stato (`script.fn_get_stato_testata_documento`, rami `PREVENTIVO`, `OFFERTA_COMMERCIALE`, `COMMESSA`).

| Testata | Vocabolario | Stato iniziale (`iniziale = true`) |
| --- | --- | --- |
| `vendite.preventivi` | `config.stati_doc_preventivi` | `DRAFT` |
| `vendite.offerte_commerciali` | `config.stati_doc_offerte` | `BOZZA` |
| `vendite.commesse` | `vendite.stati_commessa` | `BOZZA` |

⚠️ Il guard del giro T.4 (`vendite.trgfn_doc_guard_delete_solo_bozza`) confronta lo stato col **letterale** `'DRAFT'`:
montato su offerta e commessa rifiuterebbe sempre, anche la bozza. Va contro B-2 (Tid, 2026-10-27, COMMENT di
`script.fn_doc_stato_iniziale_id`: «nessuno scrive 'DRAFT' per dire lo stato in cui si nasce»); per le quattro testate
di oggi il letterale coincide col vocabolario, per costruzione e non per regola.

**Le righe («vuota»).** Il catalogo (`config.sorgenti.righe_table`) dice già quali sono:

| Testata | Righe dal catalogo | `attivo` | FK verso la testata | Altri figli |
| --- | --- | --- | --- | --- |
| preventivo | `preventivi_righe` | sì | `CASCADE` | indirizzi, riepiloghi IVA, note: `CASCADE` |
| offerta | `offerte_commerciali_eccezioni` | sì | `CASCADE` | utilities, indirizzi, note: `CASCADE`; le revisioni (`revisione_padre_id`, `revisione_radice_id`): `NO ACTION` |
| commessa | `commesse_attivita` | **no** | `NO ACTION` | `commesse_sorgenti`, `attivita_fatturabili`: `NO ACTION` |

* La commessa con attività, documenti collegati o fatturabili **già oggi non si cancella**, ma con un 23503 della FK,
  senza frase. Le fatturabili presuppongono un'attività (`fk_attivita_fatturabili_commessa_attivita`).
* L'offerta non ha righe proprie: il contenuto viene dal listino, e le eccezioni sono le sue «righe» per il catalogo e
  per il lock fuori bozza (montato su eccezioni e loro componenti).
* Il predicato del BE per il preventivo è lo stesso del guard: `count_righe` conta `attivo IS TRUE`
  (`_righe_repo_mixin.py:83`).

**Il lato «in uscita».** I venti figli col guard unico dichiarano tutti `BLOCCA`: un preventivo, un'offerta o una
commessa citati da un documento, da una pratica o da una stampa non si cancellano (`E_SORG_ORIGINE_REFERENZIATA`),
anche in bozza. Resta com'è: è la protezione di S-9, e parla **dopo** il guard (AFTER STATEMENT contro BEFORE ROW).

**⚠️ Un difetto vivo: la revisione dell'offerta cancellata lascia la madre SUPERATA.** La revisione nasce in bozza e la
sua nascita porta la madre a SUPERATA (`trg_offerte_commerciali_z90_revisione_ins` →
`vendite.fn_offerta_proietta_stato_revisione`). L'annullo della revisione la riporta a EMESSA
(`trg_offerte_commerciali_z90_rientro_padre_upd`); il `DELETE` no, perché nessun trigger lo guarda. Il BE oggi la
cancella (`elimina_offerta` controlla solo lo stato `BOZZA`), quindi il percorso è aperto. La madre, invece, non è mai
una bozza (la revisione nasce solo da uno stato di emissione, `fn_crea_revisione_offerta`): la sua cancellazione la
ferma già la metà «in bozza», e la FK resta dietro. Il preventivo non ha il caso: la revisione non tocca la madre.

**Chi cancella.**

* **DB:** nessuna funzione cancella una delle tre testate.
* **BE:** `preventivi_service.elimina_preventivo` (stato iniziale, righe attive, pratiche collegate: l'ultimo si ritira,
  BE-P.1-e); `offerte_service.elimina_offerta` (solo `BOZZA`, **nessun** controllo sulle eccezioni). La commessa: nessun
  percorso.
* **pgTAP:** cinque file cancellano un preventivo, tutti attendendo `E_SORG_ORIGINE_REFERENZIATA`
  (`script/test-sorgente-in-uscita-v1` 13-14, `pratiche/test-sorgente-pratiche-sorgenti-v1` 20,
  `vendite/test-sorgente-testate-ordini-contratti-v1` 24, `vendite/test-sorgente-righe-vendita-v1` 21,
  `documenti/test-sorgente-documenti-generati-v1` 13): dove la fixture ha righe attive o non è in bozza, il guard
  parlerà prima, con un altro codice. Quattro file cancellano commesse nelle pulizie
  (`anagrafiche/test-billing-account-guard-parent`, `vendite/test-commessa-sorgente-emittente-omogeneo-v1`,
  `vendite/test-commesse-emittente-invariante-v1`, `pratiche/test-pratiche-sorgenti-flusso`): si fermano se la commessa
  non è in bozza. Si verificano uno per uno in prova, come al giro T.4. Le cancellazioni costruite con `format()` sono
  comprese; nessun pgTAP cancella un'offerta.

**Le proposte (per Tid).** Nessuna è un cambio di modello: è la regola del giro T.4 sulle tre testate che mancano.

* **Z2-a — lo stato iniziale dal vocabolario, non dal letterale.** Il guard legge il codice dello stato iniziale con
  `script.fn_doc_stato_codice(TG_RELID, script.fn_doc_stato_iniziale_id(TG_RELID))` e lo confronta con lo stato del
  lettore. La mail resta col suo ramo (non ha un vocabolario: lo stato è la colonna). Per le quattro testate di oggi non
  cambia niente.
* **Z2-b — l'offerta vuota = nessuna eccezione attiva** (le righe del catalogo). Cambia per il BE: una bozza con
  eccezioni, che oggi si cancella, sarà rifiutata (`E_DELETE_DOC_CON_RIGHE`). L'alternativa è la sola metà «in bozza»
  per l'offerta: non la propongo, perché il catalogo e il lock trattano le eccezioni come righe.
* **Z2-c — la commessa vuota = nessuna attività e nessun documento collegato** (`commesse_sorgenti`): il guard dice
  prima ciò che la FK già impedisce. Senza `attivo`, ogni attività conta. Le fatturabili seguono dalle attività.
  L'alternativa: solo le attività, i collegamenti restano al 23503 della FK.
* **Z2-d — la revisione cancellata riporta la madre**, dentro le regole DB (S-9): la proiezione dello stato sulla madre
  scatta anche al `DELETE` della revisione, come all'annullo. L'alternativa: una revisione non si cancella, si annulla
  (un ramo in più nel guard, un codice nuovo).
* **Z2-e — i codici restano quelli del giro T.4.** `E_DELETE_DOC_NON_BOZZA` ed `E_DELETE_DOC_CON_RIGHE` (la frase dice
  «righe», che per la commessa sono le attività): si aggiornano solo le note e la soluzione nei due CSV, che nominano
  le testate. Nessun codice nuovo, salvo l'alternativa di Z2-d.
* **I pre-check BE** di stato e righe restano come controllo preventivo (come al giro T.4); a `elimina_offerta` serve
  quello delle eccezioni, o la frase del DB (richiesta BE nel §8, al giro).

**Le decisioni di Tid (2026-11-08):** Z2-a … Z2-e «ok, concorde»; il difetto della revisione si chiude (Z2-d come
proposto, la proiezione al `DELETE`); «righe ok, messaggio comprensibile».

* **Perché offerta e commessa sono ancora `BOZZA`** (domanda di Tid). Il 2026-10-24 (P-1 di
  `work-done/brief-modello-documento-vendita`) si è uniformato il **modo di dire** lo stato iniziale (la colonna
  `iniziale`, nessun letterale), non i codici: nove funzioni smisero di scrivere `'DRAFT'`/`'BOZZA'`. Il guard della
  cancellazione (2026-08-26, esteso al giro T.4) è sfuggito a quel giro, perché sulle sue quattro testate il codice
  iniziale è `DRAFT` per caso. Z2-a chiude il residuo; rinominare i codici non serve.
* **Aperto — il messaggio.** «%s ha ancora delle righe» non si capisce su commessa e offerta, e cambiare il numero dei
  segnaposto romperebbe chi formatta il testo. Proposta DB: due codici fratelli, `E_DELETE_OFFERTA_CON_ECCEZIONI` e
  `E_DELETE_COMMESSA_NON_VUOTA` (le attività e i documenti collegati, coi conteggi); il preventivo resta su
  `E_DELETE_DOC_CON_RIGHE`.
* ✅ **Deciso da Tid il 2026-11-08 — chi cancella, uniforme a DB** («sì, mi sembra la scelta migliore: perché ripetere
  la regola»). Origine (Tid: «dovrebbe essere uniforme su DB»). Dopo Z.2 la regola sta nel guard
  per le sette testate di vendita e la mail (la fattura ha la sua, `numero IS NULL`). Proposta DB: **si revoca** la
  scelta del giro T.4 («i pre-check di stato e righe restano come controllo preventivo», 2026-11-07): i pre-check di
  `elimina_ordine`, `elimina_ddt`, `elimina_reso`, `elimina_preventivo`, `elimina_offerta` si ritirano nel lotto BE/FE
  (richiesta nel §8), e il BE porta la frase del DB.

**La numerazione.** Liberi `20261109-25` … `-30` (albero e `databasechangelog` di dbdev, 2026-11-08); l'altra sessione ha
`-31` … `-39`. Stima: il guard (`20_code/vendite`), il montaggio sulle tre testate, la proiezione della revisione al
`DELETE`, i due CSV: dentro i sei. Se servono di più, il range lo dà Tid prima di scrivere.

**Il giro Z.2, le scelte** (team DB, 2026-11-08; via di Tid lo stesso giorno, «ok procedi»; il messaggio generico per
tutti, Tid: «o specifici per ogni documento o tutti generici»):

* **Un guard solo, quello del giro T.4** (`-25`): tre rami nuovi nella stessa funzione, montata sulle tre testate
  (`-26`). Il corpo di partenza è il vivo (`-88`, uguale su scratch e dbdev); il rollback è il blocco `changes` di `-88`.
* **Lo stato iniziale** (Z2-a): `script.fn_doc_stato_codice(TG_RELID, script.fn_doc_stato_iniziale_id(TG_RELID))`, dalla
  mappa del modello. I due BB sono INVOKER senza `search_path` proprio: girano dentro il guard DEFINER con `pg_catalog,
  pg_temp`, e lo reggono perché qualificano tutto (il `%s` di un `regclass` mette lo schema quando non è nel percorso).
  La mail tiene `'DRAFT'` nel suo ramo: non ha vocabolario. Se il vocabolario non dichiarasse l'iniziale, il guard
  rifiuta (fail-closed), e il contesto dell'errore porta `stato_iniziale`.
* **I tipi** (Tid: «ricorda l'uso di %TYPE»): `v_stato`, `v_iniziale`, `v_etichetta` sono polimorfi (sette vocabolari e la
  mail), `v_ha_righe` una risposta, `v_successivi` un conteggio: nessuno è il riflesso di una colonna, e la testata del
  corpo lo dichiara. Il ramo nuovo del rientro non dichiara variabili.
* **La revisione cancellata** (Z2-d, `-27`): la stessa funzione del rientro prende il ramo `DELETE` (la causa è una
  revisione che non c'è più), montata `AFTER DELETE FOR EACH ROW`, `_z90_`, come il ramo `UPDATE`. La proiezione non
  cambia: conta le revisioni vive che restano. La cancellazione non chiede conferma dei legami, perché una bozza vuota
  non ne ha. Il rollback è il blocco `changes` di `20261026-19` (uguale al vivo).
* **Il messaggio** (Z2-e): un codice per tutti; il testo dice «contenuto (righe, eccezioni, attività o documenti
  collegati)», con un segnaposto come prima; causa e soluzione nominano che cosa svuotare per documento. Le note dei due
  codici in `codici_errore.csv` nominano le tre testate.

**Che cosa cambia per chi legge, dichiarato:**

* **Un preventivo o un'offerta fuori bozza non si cancellano più** con un `DELETE` diretto (`E_DELETE_DOC_NON_BOZZA`); la
  commessa nemmeno, e prima la fermava solo la FK se aveva attività.
* **Un'offerta in bozza con eccezioni attive non si cancella più**: il BE oggi la cancellava (§8.21, BE-Z.2-a).
* **La commessa non vuota** riceve la frase invece del 23503.
* **La revisione d'offerta cancellata riporta la madre** allo stato d'emissione.

**I changeSet del giro Z.2:** `20_code/vendite/20261109-25` (il guard), `-26` (il montaggio su preventivi, offerte,
commesse), `-27` (il rientro della madre al `DELETE`, col suo trigger); `80_data/sql/config/codici_errore.csv` (le note di
`E_DELETE_DOC_NON_BOZZA` ed `E_DELETE_DOC_CON_RIGHE`) e `messaggi_errore.csv` (testo, causa, soluzione di
`E_DELETE_DOC_CON_RIGHE`). Nessuna funzione nuova, nessun codice nuovo. pgTAP esteso: `vendite/test-delete-testate-solo-bozza-vuota-v1` (19 →
32); allineati i cinque sotto. Pagina `manual/`: `vendite/trgfn_doc_guard_delete_solo_bozza`. Restano liberi `-28` …
`-30`. ⏭️ Numerazione concordata con la sessione di `brief-db-revisione-dbops` (2026-11-08): `-28` … `-30` restano di
questo brief, quella sessione prende `-58` … `-79`, questo brief riparte dal `20261109-80`.

**Gli allineamenti, uno per uno:**

* `script/test-sorgente-in-uscita-v1` (13-14), `pratiche/test-sorgente-pratiche-sorgenti-v1` (20),
  `vendite/test-sorgente-testate-ordini-contratti-v1` (24), `vendite/test-sorgente-righe-vendita-v1` (21): provano il
  rifiuto del lato «in uscita» (`E_SORG_ORIGINE_REFERENZIATA`) su un preventivo in bozza **con righe**, e ora parla
  prima il guard (`E_DELETE_DOC_CON_RIGHE`). L'attesa non cambia: le righe si disattivano prima del `DELETE` (in bozza
  si può), la bozza è vuota, e a rifiutare resta il figlio. Cambiare l'attesa avrebbe tolto la prova del blocco;
* `vendite/test-ddt-righe-evase-dall-ordine-v1` (27): leggeva il **testo** del messaggio («ha ancora delle righe»).
  Il censimento non l'aveva visto (cercava chi cancella, non chi legge la frase); l'ha trovato la regressione. Ora
  «ha ancora del contenuto». Senza l'apply del CSV resta rosso: dipende dal testo, non dal guard;
* ⚠️ **un difetto preesistente, corretto nello stesso file:** il test 4 di `vendite/test-sorgente-righe-vendita-v1`
  (giro R.1) confrontava `regclass::text` con nomi qualificati, la trappola del test 1 del giro T.4: rosso con
  `vendite` nel `search_path` anche su HEAD. Ora schema e nome dalle colonne del lettore dei montaggi.
* Le quattro pulizie di commesse e la stampa del preventivo (`documenti/test-sorgente-documenti-generati-v1` 13) non
  cambiano: le commesse cancellate sono bozze vuote, e il preventivo stampato non ha righe.

**La prova del giro Z.2** (2026-11-08, come owner, in transazione annullata, su scratch e dbdev; l'estratto dei tre
changeSet nell'ordine dei numeri, con l'upsert simulato della riga di `messaggi_errore.csv`):

* **i corpi di partenza sono quelli vivi:** il corpo del guard in `-88` e del rientro in `20261026-19` hanno lo stesso
  `prosrc` del vivo (md5) su scratch e dbdev: sono i rollback;
* `plpgsql_check` sul guard montato su preventivi, offerte, commesse e mail, e sul rientro: nessun avviso;
* `vendite/test-delete-testate-solo-bozza-vuota-v1`: 32/32 con l'estratto su scratch e dbdev; senza, rossi 1, 16, 20,
  21, 23, 25 e il file si ferma sulla revisione (la madre resta superata). Una **mutazione** (l'estratto senza il
  trigger `_dlt` del rientro) accende il solo 27;
* **regressione prima/dopo su 198 pgTAP** (tutti `dbops/`, chi cancella o costruisce le tre testate, chi nomina il
  guard, i codici, il rientro, la revisione, i lettori dello stato iniziale, i messaggi; sullo scratch, in sequenza;
  prima e dopo sul file di HEAD, per isolare il giro dall'altra sessione, che ha sei pgTAP nuovi non in HEAD, esclusi):
  2509 → 2516 ok. Fuori dal file del giro cambiano solo i cinque allineati sopra; gli altri rossi sono gli stessi riga
  per riga;
* i sei file del giro, con l'estratto, verdi su scratch e dbdev e con `vendite`, `config`, `script`, `dbops` nel
  `search_path`, salvo il 43 di `vendite/test-ddt-righe-evase-dall-ordine-v1`, «rosso da owner» già dichiarato;
* guardrail statici e licenze: verdi.

Non coperto, e resta di Tid: l'apply (i tre changeSet e i due CSV), la corsa dei pgTAP come applicazione (la RLS), la
baseline. **Fatto da Tid il 2026-11-08:** apply dei tre changeSet e dei due CSV su dbdev e scratch (15:10; verifica DB:
`databasechangelog` EXECUTED, i quattro trigger montati, il testo nuovo del messaggio), pgTAP verdi come applicazione.

⚠️ **Nell'albero, non del giro:** un'altra sessione (`brief-db-revisione-dbops`) scrive in `codici_errore.csv` nello
stesso momento (la riga di `E_PROCESSO_SENZA_SVEGLIA` e il codice nuovo `W_TXID_BYPASS_PARAMETRO_ASSENTE`, coi suoi
changeSet `20261109-40` … `-57`). Al commit le righe si separano.

**Il giro Z.4, la chiusura** (team DB, 2026-11-08; via di Tid lo stesso giorno, «riprendi lo sviluppo»). Nessun
changeSet: è un giro di presidi e di documento.

* **Il presidio di struttura col suo elenco finale** (`dbops/test-sorgenti-struttura-v1`): il debito sono le quattro
  tabelle degli acquisti, dichiarate e passate al loro cantiere; l'intestazione lo scrive come elenco finale. Il test 2
  dice anche la grammatica (`TESTUALE`), perché è quella che le quattro tabelle tengono in vita. ⚠️ Il test 1
  confrontava `regclass::text`: rosso con `dbops` o `pratiche` nel `search_path` di chi lancia (verde come app e come
  owner per caso). Ora schema e nome dal perimetro, come il test 2. Verde su scratch e dbdev, con e senza gli schemi nel
  `search_path`; una mutazione (una tabella con la provenienza e senza guard, dentro la transazione) accende il test 2 e
  la nomina.
* **Il ponte è vuoto** nel senso deciso al giro Z.1: nessuna tabella scrive più la chiave in testo, fuori dal debito
  degli acquisti. Lo presidia lo stesso test 2.
* **Il debito degli acquisti, precisato** (sopra, «Lotto Z»): il ramo TESTUALE degli orfani legge solo le quattro
  tabelle; l'etichetta del perimetro copre anche le due esenzioni, e si rinomina quando il ramo si ritira.
* **Le richieste del BE al DB** (R-P.1-1, R-P.1-2) sono chiuse nel giro Z.1. UI-M.1-a era già fatta nel giro M.2: la
  nota BE che la dava aperta era scritta su una copia precedente (§8.17); il doppione nato dal merge è tolto.
* **Il §8 è completo e chiuso** (§8.22).

**Il giro Z.5, le scelte** (team DB, 2026-11-08; V-7-bis, via di Tid lo stesso giorno). È il completamento di una
decisione esistente, non un cambio: `brief-db-uscita-documento-dal-giro` §6 (2026-09-08) ha deciso che di una
segnalazione «**lo dichiara chi scrive**, il database non lo deriva» per il documento (`gruppo_key`); qui lo stesso vale
per la commessa.

* **La colonna** (`00_schema/vendite/20261109-80`): `vendite.fatturazione_lotti_log.commessa_id bigint`, nullable,
  **senza FK** e senza indice. Senza FK per la regola di `gruppo_key`: un log non deve poter fallire dentro il ramo
  `EXCEPTION` di chi lo scrive. Nessuno storico, nessuna copia di riga della tabella.
* **Lo scrittore** (`20_code/vendite/-81`): `vendite.fn_log_pipeline_fase` prende `p_commessa_id`, nono, in coda
  (`%TYPE` della colonna); un id assente o `<= 0` diventa NULL senza sollevare. DROP + CREATE (con la firma vecchia viva
  ogni chiamata corta sarebbe ambigua: lo diceva già il suo COMMENT), GRANT a `zeroerp_app` di nuovo, COMMENT riscritto.
  Le cinque funzioni DB chiamanti non la passano: scrivono segnalazioni del giro o l'uscita di un documento, e la
  commessa non la sanno. La passa il BE (BE-Z.5-a).
* **Il riferimento** (`-82`): `vendite.fn_riferimento_gruppo_fatturabile` prende `p_commessa_id` (in coda, DEFAULT
  NULL): per un documento senza numero vince sulla commessa aperta del documento. Il numero e la forma `MAN:` come
  prima. DROP + CREATE, GRANT, COMMENT.
* **La lista** (`-83`): `vendite.fn_list_lotto_segnalazioni` passa la commessa della riga o, se la riga non la dice,
  quella **unica** dichiarata dalle altre righe dello stesso documento nello stesso lotto (due commesse diverse non si
  scelgono: si lascia il ripiego). CREATE OR REPLACE sulla definizione viva, nessun'altra riga cambia.
* Corpi di partenza: il vivo, uguale su scratch e dbdev e uguale agli ultimi changeSet (`20260909-21`, `20261108-07`,
  `20260908-32`); i rollback sono la definizione viva col suo COMMENT e GRANT.

**Che cosa cambia per chi legge, dichiarato:** la scheda Critiche nomina un gruppo di consumi col codice della commessa
**di quel lotto** quando la segnalazione la dichiara; fino a BE-Z.5-a il BE non la passa, e il riferimento resta quello
di oggi (la commessa aperta, poi la chiave). Nessun chiamante si rompe.

**I changeSet del giro Z.5:** `00_schema/vendite/20261109-80`, `20_code/vendite/-81`, `-82`, `-83`. pgTAP esteso:
`vendite/test-riferimento-gruppo-fatturabile-v1` (17 → 23). Pagine `manual/`: `vendite/fn_riferimento_gruppo_fatturabile`,
`fn_log_pipeline_fase`, `fatturazione_lotti_log`. Allineato: `vendite/test-sorgente-commenti-al-presente-v1` (l'elenco
nomina la firma nuova del riferimento, `(text, bigint)`). Liberi `-84` … in su (dal `-80`, numerazione concordata).

**La prova del giro Z.5** (2026-11-08, come owner, in transazione annullata, su scratch e dbdev; l'estratto dei quattro
changeSet nell'ordine del migrate):

* **i corpi di partenza sono quelli vivi:** le tre funzioni hanno lo stesso `pg_get_functiondef` su scratch e dbdev, e lo
  stesso `prosrc` degli ultimi changeSet (md5); nessun oggetto dipende da loro;
* `plpgsql_check`: nessun avviso sul verbo e sul riferimento; sulla lista i soli «extra» del suo SQL dinamico, già
  prima. Privilegi uguali a prima, una firma sola per funzione;
* `vendite/test-riferimento-gruppo-fatturabile-v1`: 23/23 con l'estratto su scratch e dbdev, anche con `vendite`,
  `config`, `script`, `dbops` nel `search_path`; senza, il file si ferma alla firma nuova. Una mutazione (la lista senza
  la riga sorella) accende il solo 23. La commessa del consumo si annulla col suo verbo
  (`vendite.fn_annulla_commessa`, i legami contati da `vendite.fn_documento_legami`): è il caso che prima dava la chiave
  grezza (18);
* **regressione prima/dopo su 140 pgTAP** (tutti `dbops/` e chi chiama il verbo, il riferimento, la lista, l'uscita dal
  giro o legge il log del lotto; sullo scratch, file di HEAD nelle due corse): 1526 → 1529 ok. Una sola differenza vera,
  ⚠️ **trovata dalla regressione**: `vendite/test-sorgente-commenti-al-presente-v1` 1-2, perché l'elenco nominava la firma
  vecchia e perché il COMMENT nuovo portava marcatori di storia (§5d). Riscritti al presente il COMMENT del riferimento,
  quello della colonna e la parte nuova di quello del verbo; l'elenco prende la firma nuova; poi 5/5 su scratch e dbdev.
  Senza l'apply il presidio resta rosso: nomina una firma che ancora non c'è. `script/test-vw-giornale-entita` è rosso
  uguale nelle due corse (cambia solo il numero di riga dell'errore, per l'estratto in testa);
* guardrail statici e licenze: verdi.

⚠️ **Debito dichiarato, non del giro:** il COMMENT di `vendite.fn_log_pipeline_fase` porta dal 2026-09-08 marcatori di
storia (rev, nomi di brief, id di changeSet, sigle), contro §5d; il giro ha riscritto al presente solo la parte nuova.
Va riscritto intero quando la funzione si tocca per sé, e entra allora nell'elenco del presidio.

Non coperto, e resta di Tid: l'apply, la corsa dei pgTAP come applicazione, la baseline. **Fatto da Tid il 2026-11-08:**
apply dei quattro changeSet su dbdev e scratch (16:18; verifica DB: `databasechangelog` EXECUTED, la colonna c'è),
pgTAP verdi come applicazione.

#### Lotto BE/FE — una volta sola

* Il team BE/FE riceve il §8 intero e porta backend, frontend, test Django e smoke allo stato del DB.
* Se emerge un difetto DB, si raccoglie in un elenco e si chiude in **un** giro DB alla fine, non uno per volta.

#### Lotto DOC — la documentazione, per ultima

* Si aggiorna tutto il censimento del §7.3: guide, manuali DB e BE, doc di sviluppo, memoria, documenti aperti.
* K-1 resta, e la guida lo dice.
* Il brief va in `work-done/`.

#### L'ordine, e perché

0 → R → T → C → D → P → M → Z → BE/FE → DOC.

* Il lotto 0 viene prima di tutto, perché ogni altro lotto lo usa.
* R viene subito dopo, perché sblocca il lotto B degli articoli obsoleti e non ha dati da convertire.
* T viene prima di C, D, P e M perché le testate di vendita sono i **bersagli** di tutti gli altri: il lato «in
  uscita» e la conversione di bolle e resi servono a commesse, pratiche e magazzino.
* M viene per ultimo fra le famiglie: è quello con più BE/FE, e il suo indice di idempotenza è il cambio più
  delicato.

### 7.3 La documentazione da aggiornare alla fine (censimento, 2026-11-06)

**Il metodo.** Ho cercato in `docs/`, `.codex/`, `README` e `CLAUDE.md` i nomi del meccanismo: le colonne
`sorgente_*`, `key_selector`, `config.sorgenti`, i tipi `*_RIGA` e i livelli sotto la riga, «polimorf», «modello
A/B», il registro dei canali, `documento_origine_*` e i BB. Restano **fuori**:

* la doc auto-generata (`<schema>/tabelle|funzioni|views`, gli `index.md` / `index.ci.md` di schema): si rigenera, non
  si scrive a mano;
* i documenti in `work-done/`: sono storia, non si riscrivono.

Risultato: **234 file**. Si aggiornano tutti nel **lotto DOC** (§7.2), dopo il BE, così descrivono lo stato finale
una volta sola.

**Il lotto DOC anticipato** (Tid, 2026-11-08: «anticipare il lotto doc riscrivendo la documentazione che non è
aggiornata», «riscrivi anche le guide collegate»). A giri, dal più importante; i manuali `backend/*/manual`, i due
cataloghi BB e `api.md` restano al team BE/FE. Le parti che dipendono da BE-Z.5-a e UI-Z.2-a descrivono lo stato del DB.

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **DOC.1** | le sedi del concetto (A) | ✅ fatto (2026-11-08), salvo il seed: ✅ `guide/sorgente-polimorfa.md` riscritta sul modello (due ancore esplicite, `la-chiave-del-documento` e `grafi-tra-documenti`, e i due link di `mappa-concentrica.md` ripuntati); ✅ `config/manual/sorgenti.md` riscritta nella cornice. ✅ `linee-guida-sql.md` §6e (la regola della provenienza, scritta una volta; il caso del §13.3 riscritto); ✅ `acquisti/_dominio-acquisti.md` (la provenienza in vendite e quella, ancora vecchia, degli acquisti; «verificato sulla struttura», non sulla popolazione); ✅ la memoria del team (`reference_sorgente_polimorfa_key_selector` riscritta, i motivi di `fb_chiave_id_uid_non_si_unifica` aggiornati, due correzioni puntuali). Resta solo la nota del presidio in `presidi.csv`: è un seed, va col giro DB finale. `config/manual/tipi_entita.md` non esiste: la sede è il COMMENT |
| **DOC.2** | le guide di dominio (B) | ✅ fatto (2026-11-08): `fatturazione` (lo schema ER, l'idempotenza sulla riga di commessa), `gestione-commesse` (la cancellazione solo da bozza vuota, l'idempotenza, `sorgente_origine_tipo_id` ritirato), `gestione-ordini` e `gestione-ddt` (la provenienza, la bozza vuota, i codici del DB al posto dei pre-check BE; un link morto a `fn_ddt_legami` ripuntato), `gestione-offerte-commerciali` (la provenienza al posto di `offerta_id` e `documento_origine_*`, gli indici sui vivi, §4.5 la bozza vuota e la revisione cancellata), `gestione-contratti` (la cancellazione, il contratto precedente, i codici), `gestione-preventivi` (la bozza vuota, il lato «in uscita», i codici), `gestione-pratiche-configurazione` (la chiave dell'entry-point), `uso-di-obsoleto` (il blocco datato dissolto: i verbi scrivono la sorgente), `pgtap-come-si-scrive-un-test` (`p_sorgente_chiave`). Verificate e invariate: `gestione-pratiche`, `documenti-e-stampe`, `modello-documento-di-vendita`. Data di revisione 8 novembre su ognuna |
| **DOC.3** | le pagine `manual/` DB (D), per lotto | ✅ fatto (2026-11-08): 104 pagine aggiornate in tutto, verificate sul DB, controlli di cornice e link puliti su tutte; il resto del censimento in quattro gruppi (vendite 1 e 2, gli altri schemi 3 e 4), le invariate col loro motivo. Prima: ✅ le 38 pagine che citavano nomi ritirati (guard A/B, tipi `*_RIGA`, colonne parallele, canali), 31 aggiornate e 7 invariate perché le occorrenze erano codici di `config.tipi_entita` o non riguardavano la provenienza (2026-11-08); resta il resto del censimento D |
| **DOC.4** | i documenti aperti (E) e quelli di contesto lato DB (C, senza i cataloghi BB) | ✅ fatto (2026-11-08). **C:** `PROJECT_CONTEXT.md` (la voce del cantiere fra gli aperti, la regola e le sue sedi), `mappa-concentrica.md` (la riga «La provenienza ha un modello solo», gli acquisti ancora nella grammatica precedente; la data in testa resta: vale per le misure), `dev/ricette-dove-intervenire.md` (il documento che nasce da un altro: §6e); `index.md` e `readme` invariati (solo il nome della guida); il changelog della mappa è storia. **E:** un avviso di allineamento datato, col rimando alla guida e a questo brief, in `analisi-db-magazzino-aggancio-documento-e-produzione` (superata per D-1, D-2, D-3, D-7, D-9; viva per D-5), `analisi-db-magazzino-carico-e-scarico` (la forma della sorgente, l'indice d'identità di oggi), `brief-design-proiezione-stato-dominio`, `brief-design-guida-rollout-multidominio`, `valutazione-modello-di-dominio-db`, `analisi-pratiche-domini-anello3`, `sviluppo-listini-da-flussi` (l'opzione B da riscrivere sul modello), `sviluppo-preventivi-acquisti`, `brief-db-addebito-trasporto-ordine` (§6.4 fotografia); `brief-db-articoli-obsoleto-dal` allineato («Chi riparte», lotto B applicato, «modello A» superato). Invariati: `analisi-simmetria-ordini-acquisto` (già allineato al giro M.4), `integrazione-con-sistemi-esterni`, `analisi-db-commessa-e-produzione-predisposizione`, `piano-migrazione-primevue-5`, `fatturazione-modello-utilities-gas-ee-idrico`, `analisi-pratiche-valutazione-stato` e l'allegato dei codici (nessun passaggio sul tema); `brief-db-revisione-dbops` è dell'altra sessione (il suo residuo sul nome `sorgente_uid`, righe 770-775, è chiuso dai giri K.1 e K.2: glielo si segnala); i due SQL una tantum del cantiere vanno in `work-done/` col brief. **Le pagine raccolte da DOC.3:** i dieci `config/manual/stati_doc_*` riscritti (`iniziale`, `emissione`, `accettazione`, `cessazione`, `scadenza` coi lettori; stati mancanti; vincoli corretti); `script/manual/trgfn_componenti_guard_coerenza_bom` (cinque montaggi, `listini_righe_componenti` ha il suo guard), `trgfn_note_validate_generic` (otto partizioni, due d'acquisto), `vw_giornale_entita`; `vendite/manual/vw_dash_competenza_attivita`, `fn_documento_lineage`, `fn_diagnostica_gruppi_fatturabili`; tutte le 99 pagine di `pratiche/manual` passano i sei controlli (92 riscritte: codici con `E_`, montaggi e scrittori verificati sul DB). Verificato a campione sul DB |

⚠️ **Trovato riscrivendo, per il giro DB finale** (ogni correzione di COMMENT è un changeSet, con la sua pagina
auto-generata; verificati sul DB il 2026-11-08):

* COMMENT stantii: `config.sorgenti.scope` (descrive `ROW_VALIDATOR`, ritirato al giro Z.1, e per `MAGAZZINO` le righe di
  inventario, rettifica e trasferimento, uscite al giro M.3); `script.fn_get_sorgente_emittente_sr_id` («la porta
  testuale … passa qui»: c'è solo la firma sulle colonne); `script.fn_sorgente_chiave_id` / `_uuid` (nominano come
  consumatori `pratiche.fn_stato_sorgente` e `script.vw_pratica_doc_sorgente`, che non le usano più);
  `vendite.fn_select_attivita_fatturabili` («`sorgente_tipo_id`/`sorgente_uid` rioccupati dall'idempotenza del pull»:
  colonne ritirate); `vendite.attivita_fatturabili.commessa_attivita_id` («nullable in fase transitoria»: è NOT NULL);
  `vendite.vw_documento_lineage_archi` (`commesse_sorgenti.sorgente_uid` «polimorfa» con `id::text`); `vendite.fn_documento_legami`
  (attribuisce `origine_id` della commessa a `fn_get_sorgente_documento_ref`; il corpo usa `script.fn_sorgente_documento`);
* **codice morto**: `vendite.trgfn_attivita_fatturabili_normalize` esce appena `commessa_attivita_id` è valorizzato, cioè
  sempre (NOT NULL dal giro C.1): la normalizzazione di `competenza_mese`, `competenza_dal`, `competenza_al` non gira mai.
  Non è un difetto di comportamento: l'unico scrittore, `fn_emit_attivita_fatturabili_da_commessa`, copia quei campi dalla
  riga di commessa, che ha già il CHECK «primo del mese» e le date NOT NULL. Il ramo serviva all'AF senza riga di commessa,
  che il modello non ammette più: si ritira. La pagina `manual/` è già corretta (2026-11-08).
* ✅ **scritto (2026-11-08, Tid: «scrivilo ora»), da applicare:** **tre codici senza più chi li solleva** (segnalazione del BE, 2026-11-08, verificata: nessuna funzione DB, nel BE solo un
  commento storico in `_righe_bozza_guard.py:16-17`): `E_DDT_STATO_TRANSIZIONE`, `E_RESO_STATO_TRANSIZIONE`,
  `E_PREV_STATO_NON_MODIFICABILE`. Li sollevavano i pre-check di cancellazione ritirati con BE-Z.2-a. Si ritirano come
  `E_PRATICA_SORGENTE_TIPO_INVALIDO` al giro Z.1: `obsoleto_dal` e la nota in `codici_errore.csv`, senza cancellare la riga
  (`dbops.error_log` ci punta); poi il BE rigenera le policy. ⚠️ `E_ORD_STATO_TRANSIZIONE` resta: lo solleva ancora
  `ordini_service.py:1033`. ⚠️ Il CSV lo scrive anche la sessione di `brief-db-revisione-dbops`: si avvisa prima.
  **Fatto:** le tre righe di `80_data/sql/config/codici_errore.csv` con `obsoleto_dal = 2026-11-08` e la nota (l'altra
  sessione avvisata prima; il file non aveva modifiche aperte). Nessun changeSet: le ricarica il mirror esistente
  (`80_data/changelog/20260807-15`, `runOnChange`), come al giro Z.1. Prova: l'`UPDATE` del mirror simulato in transazione
  sui 12 pgTAP che leggono il catalogo dei codici, sullo scratch, nessuna differenza. La riga del codice tolta da
  `guide/gestione-ddt.md`. Al BE: §8.24;
* **altri COMMENT e commenti stantii** (dal resto di DOC.3, 2026-11-08): `script.vw_stato_sorgente` («dato
  (`sorgente_tipo_id`, `sorgente_uid`)», «leggila per testo», marcatori di storia); i COMMENT dei giri M datati «2026-11-09»
  e con marcatori di storia (`script.vw_stati_doc_reso_merce_rientrata`, `dbops.vw_ddt_emessi_senza_scarico`,
  `dbops.vw_resi_confermati_senza_carico`, `vendite.fn_reso_muove_merce`, `dbops.fn_pgtap_crea_sorgente`); la `causa` di
  `E_ORD_ANNULLA_IN_COMMESSA` (obsoleto) cita `commesse_sorgenti` con la chiave id; i commenti nel corpo di
  `vendite.fn_ddt_vincoli_cliente` e `script.fn_check_ordine_annullabile` («oggi l'uid, dal lotto T l'id»); l'intestazione
  di `script/test-guard-sorgente-polimorfa-testuale-v1` («resta montato solo su `pratiche_sorgenti`»: non è più montato).
  Dal gruppo 2 di vendite: `vendite.trgfn_commesse_attivita_proietta_stato_preventivo` («sorgente_uid = uid::text»: è uuid);
  `vendite.vw_stato_sorgente_ddt` (`resi.sorgente_uid` «colonna tipizzata diretta»: il reso dichiara la bolla in
  `sorgente_id`); `vendite.vw_stato_sorgente_{preventivo,offerta,ordine,contratto}` («coerente con pratiche_sorgenti»);
  `vendite.vw_contratti_lista` (le colonne `frontiera_*`, che non ha più); `vendite.vw_documento_lineage_nodi` («base di
  vw_documento_lineage», ritirata); `config.sorgenti.apribile` («falso per le righe»: i tipi di riga non ci sono più);
* **due indici forse inutili, da verificare sul modello** (gruppo 2 di vendite, 2026-11-08): `vendite.ix_resi_sorgente`
  (`sorgente_tipo_id`, `sorgente_uid`) e `vendite.ix_ddt_v_sorgente` (idem, parziale sul tipo). La provenienza di bolla e
  reso oggi sta in `sorgente_id` (ordine, reso, bolla hanno chiave id), e ci sono già gli indici su `sorgente_id`. ⚠️ Si
  ritirano solo se il modello non ammette un tipo a chiave uid come provenienza di bolla o reso (un CHECK o un guard di
  dominio sul tipo): che oggi siano vuoti non è un motivo (regola zero);
* **due domande di modello per Tid** (gruppo 1 di vendite, 2026-11-08): la provenienza di `vendite.resi` deve essere solo
  `DDT_VENDITA`? Oggi `chk_resi_sorgente_forma` la vuole obbligatoria ma niente ne fissa il tipo, e il guard del cliente
  sugli altri tipi esce senza controllare (è la stessa domanda che decide i due indici sopra). E le righe di fattura: nessun
  verbo ne scrive la provenienza (la origine passa da attività fatturabile → riga di commessa), solo la fixture pgTAP: è
  voluto (memoria `ref_righe_fattura_senza_sorgente`) o il guard unico su `fatture_righe` è montato su colonne che nessuno
  usa?;
* **altri commenti stantii** (gruppo 1 di vendite): i COMMENT di `vendite.fn_documento_lineage_archi` (il seme «(tipo_id,
  uid::text)»), `vendite.fn_fattura_origini` (la chiave tradotta con un join), `vendite.fn_documento_lineage` (marcatori e
  «sorgente unica: vw_documento_lineage_archi»); i commenti nel corpo di `fn_genera_ddt_riconsegna` («resi.sorgente_uid
  e' NOT NULL») e `fn_annulla_commessa_attivita` (la disciplina del chiamante, superata dal CHECK);
* **i confronti `d.id = x.sorgente_id OR d.uid = x.sorgente_uid`** in `vendite.trgfn_resi_normalize`,
  `trgfn_resi_guard_ddt_consegnato`, `fn_conferma_reso`, `fn_annulla_reso`, nelle liste e nel builder `dbops.fn_pgtap_crea_reso`:
  per un tipo a chiave id il ramo uid è morto, e un `OR` fra le due chiavi può impedire l'uso dell'indice (la forma già
  nota: un ramo per chiave). Da valutare col piano, come applicazione.

⚠️ **Trovato da DOC.4, per il giro DB finale o per Tid** (verificato sul DB il 2026-11-08; fuori dal tema provenienza):

* **COMMENT stantii** (ognuno è un changeSet): `config.stati_doc_reso` e la sua `meta` (`fase` in `meta.fase`: è una colonna);
  `config.stati_doc_offerte_transizioni` («5 transizioni»: sono 7); `config.stati_doc_offerte` (manca `accettazione`), le sue
  colonne `ordine` (manca 60) e `is_superato` (lo scrive `vendite.fn_offerta_proietta_stato_revisione`); `codice` di
  `stati_doc_contratti` (`SOSPESO`), `stati_doc_ddt` e `stati_doc_ordini` (CONFERMATA/ALLOCATA); `stati_doc_fiscale.fase`;
  `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più: oggi
  `partecipa_overlap_snapshot`, `ex_contratti_no_overlap`); le colonne di significato degli stati («Emetti» dà numero e PDF:
  per offerta, contratto e ordine il numero è alla nascita); `script.vw_giornale_entita` (`attivita_fatturabili_log`);
  `vendite.fn_documento_lineage` («sorgente unica: vw_documento_lineage_archi»); `script.trgfn_componenti_guard_coerenza_bom`
  (i montaggi); in `pratiche` i codici citati senza `E_` o col numero (`fn_guard_ripetibilita_flusso`, `fn_risolvi_definizione`,
  `fn_fork_definizione`, `fn_pubblica_definizione`, `fn_nuova_versione_definizione`, `trgfn_pratiche_guard_pin_immutabile`,
  `trgfn_template_flussi_default_definizione`, `trgfn_flussi_guard_definizione`, `trgfn_tfap_guard_compatibilita`,
  `trgfn_tfhe_guard_no_proiezione`, `trgfn_template_flussi_guard_immutabile`, `trgfn_template_flussi_figli_guard_immutabile`,
  `trgfn_workflow_definizioni_guard`, `trgfn_pratiche_guard_chiusura_flussi`), `pratiche.flussi.esito` e
  `template_flussi_handler_eventi.esito_richiesto` (mancano `MERCE_PRESENTE`, `SOLO_SERVIZI`),
  `trgfn_tipi_prestazione_bootstrap_definizione` (`fn_fork_nuova_versione`, che non esiste), `trgfn_sospensioni_set_periodo` e
  `trgfn_calcoli_tempo_set_periodo` («Migrazione daterange»), `allegati_pratiche`/`allegati_flussi` («immutabili»: nessun
  vincolo), `sospensioni.data_riattivazione_prevista` (il job pgAgent non esiste), marcatori e sigle in
  `fn_prendi_in_carico_flusso`, `trgfn_pratiche_guard_contesto`, `script.trgfn_note_validate_generic`,
  `trgfn_flussi_autochiusura_pratica`; commenti nel corpo di `trgfn_sospensioni_propaga`, `trgfn_allegati_*_giornale` («tx_id
  NULL»), `trgfn_pratiche_default_definizione`, `fn_guard_prerequisiti_flusso`, `trgfn_flussi_calcolo_tempo_completamento`
  (il flusso senza template non esiste più);
* **difetti da guardare** (domande per Tid, non provati in transazione): ① `pratiche.flussi.data_fine` non la scrive nessuno, ma
  `trgfn_flussi_calcolo_tempo_completamento` la usa come `data_inizio_calcolo` NOT NULL: il conteggio fallirebbe al
  completamento di un flusso con formula attiva (scritto in `pratiche/manual/calcoli_tempo`); ② il lotto di fatturazione non
  nasce dal vocabolario (`fn_create_fatturazione_lotto` sceglie col letterale `'DRAFT'`, `trgfn_doc_stato_iniziale` non
  montato); ③ il guard di transizione dell'offerta confronta i codici (`'BOZZA'`, `'EMESSA'`…) invece dei significati;
  ④ `terminale` dichiarato su stati che hanno passaggi automatici in uscita (`SUPERATA→EMESSA`, `EVASO→ACCETTATO`,
  `EVASO→PARZIALMENTE_EVASO`/`CONFERMATO`), e lo legge `pratiche.fn_stato_sorgente`; ⑤ quattro stati d'ordine attivi
  (`ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO`) che nessun passaggio raggiunge; ⑥ in `trgfn_fatture_guard_stato` il
  controllo di `applica_fattura` sta in un ramo che non scatta; ⑦ bolla e reso ricavano `esito`/`terminale` nella vista;
  ⑧ `stati_doc_listino_versioni` senza `fase` e con l'indice `ux_…`; ⑨ `regole_generazione.esito_richiesto` ammette
  `QUALSIASI`, che nessun flusso ha; ⑩ `pratiche.fn_copia_definizione` eseguibile da PUBLIC (verificato), mentre
  `fn_fork_definizione` è riservata all'app; ⑪ il nome nel log di `trgfn_flussi_guard_transizione` ha uno spazio
  (`'pratiche. trgfn_…'`); ⑫ `script.trgfn_lock_columns` montato su `pratiche.tipi_prestazione` senza righe nel registro;
  ⑬ il pgTAP della BoM non fa scattare il controllo 4 (un `pass()` vuoto) e il punto 7 nomina un codice ritirato;
* **una pagina senza oggetto:** `pratiche/manual/trgfn_sospensioni_giornale` descrive una funzione che nel DB non c'è (ci sono
  `_ins` e `_riattivazione`): da cancellare, se Tid conferma.

#### A. Le sedi del concetto: si riscrivono

| Documento | Che cosa cambia |
| --- | --- |
| `docs/it/guide/sorgente-polimorfa.md` | è la guida del meccanismo. Si riscrive sul modello: §2 (due modelli → uno), §2a (le quattro domande e i BB nuovi), §4 (K-1 resta, cadono le motivazioni del §3.5), §4a (le colonne «che sembrano polimorfe» non esistono più), §5, §6 (il grafo legge dal BB che risolve), area tecnica |
| `80_data/sql/dbops/presidi.csv`, riga `dbops.vw_sorgenti_orfane` | la nota descrive il perimetro vecchio (FK + due colonne + guard tipizzato): riscriverla sul perimetro della provenienza (giro 0.2). ⚠️ Il mirror rilegge tutto il CSV: provare l'upsert intero |
| `docs/it/dbzero/config/manual/sorgenti.md` | §Convenzione chiave sorgente; i livelli (righe, dettaglio, colonne FK); `categoria` e `ROW_VALIDATOR` ritirati; la colonna `area` descritta e assente (E-11) |
| `docs/it/dbzero/config/manual/tipi_entita.md` e il commento di tabella | `is_sorgente` dopo il ritiro dei tipi di riga |
| `docs/it/linee-guida-sql.md` | la regola, scritta una volta: una tabella nuova che dice «nasce da» usa le colonne del modello, il BB che scrive e il guard unico; il presidio in CI la fa valere. Da rivedere anche i passaggi su `key_selector` (riga 250), `config.sorgenti` (384, 1881) e il cast di `sorgente_uid` sotto policy (2882) |
| `docs/it/dbzero/acquisti/_dominio-acquisti.md` | cita il caso «`sorgente_uid` significava due cose» (riga 25): ora è chiuso |
| la memoria del team | `fb_chiave_id_uid_non_si_unifica` (già annotata), `reference_sorgente_polimorfa_key_selector`, `ref_righe_fattura_senza_sorgente`, e chi cita i modelli A/B |

#### B. Le guide di dominio: si aggiornano i passaggi

| Guida | Dove |
| --- | --- |
| `guide/fatturazione.md` | lo schema delle tabelle (righe 121-129), l'idempotenza delle AF «sulla chiave sorgente» (317, 1317): ora è `commessa_attivita_id` (D-1) |
| `guide/gestione-commesse.md` | idempotenza (526), `fn_link_commessa_sorgente` (546, 616), la riga di commessa che eredita `sorgente_uid` (782) |
| `guide/gestione-ordini.md` | l'origine documentale `documento_origine_*` (186-187) → `sorgente_*` (S-8); la bozza vuota che si elimina (544): la regola ora sta anche nel DB (giro T.4) |
| `guide/gestione-ddt.md` | «da dove arriva» (133, 153): `sorgente_id` dell'ordine; la bozza vuota che si elimina (379), come per l'ordine (giro T.4) |
| `guide/gestione-contratti.md` | non dice come si cancella un contratto: solo da bozza vuota (giro T.4, Tid 2026-11-06) |
| `guide/gestione-offerte-commerciali.md` | il vincolo `uq_ordini_v_documento_origine_offerta` (505), che cambia chiave (D-8) |
| `guide/gestione-pratiche.md`, `gestione-pratiche-configurazione.md` | il legame pratica → documento (56, 633; 196-197) |
| `guide/uso-di-obsoleto.md` | la «riga derivata» riconosciuta dalla sorgente (194, 262, 326) |
| `guide/pgtap-come-si-scrive-un-test.md` | i builder con la sorgente (121) |
| `guide/documenti-e-stampe.md`, `modello-documento-di-vendita.md` | da verificare: citano `sorgente_tipo_id` come tipo di template e `citato_in_fattura`, che non cambiano |

#### C. I documenti di sviluppo e di contesto

| Documento | Che cosa |
| --- | --- |
| `.codex/PROJECT_CONTEXT.md` | una riga sul cantiere finché è aperto; alla chiusura, la regola nuova |
| `docs/it/mappa-concentrica.md` (+ `dev/mappa-concentrica-changelog.md`) | «un nome per ogni tipo di documento» (492), lineage (519), acquisti (418) |
| `dev/backend/catalogo-building-block-backend.md` | `SORGENTE_<codice>` e `SorgentiRepository` (935-936), i BB che il BE usa per leggere una sorgente |
| `dev/frontend/catalogo-building-block-frontend.md` | `SORGENTE_CODES` (1197), lineage (1121) |
| `dev/api.md` | il lookup `tipi-entita` con `key_selector` (94): da verificare |
| `dev/ricette-dove-intervenire.md` | il rimando a `config.sorgenti` (120) |
| `readme.md`, `index.md` | solo il link alla guida: da verificare |

#### D. Le pagine `manual/` degli oggetti DB e BE (175 file)

Raggruppate per lotto: il lotto dice quale oggetto è cambiato, la pagina si aggiorna nel lotto DOC. Le pagine degli
oggetti **ritirati** non aspettano: si cancellano nel giro che li ritira (un oggetto ritirato non lascia la sua scheda
nell'indice). Ogni giro aggiunge qui le pagine che ha toccato e il censimento non aveva.

* ✅ **Già cancellate dal giro T.1** (2026-11-06, oggetti ritirati): `storico/documenti_fatturazione_canali`,
  `vendite/documenti_fatturazione_canali`, `vendite/fn_set_documento_canale_stato`, `vendite/trgfn_documenti_sync_canali`.
  Nelle righe sotto restano barrate.
* **Aggiunte dal giro T.2** (2026-11-06, pagine toccate e non censite) (4): `script/fn_available_actions_ddt`,
  `script/fn_available_actions_reso` (colonne non modificabili in bozza), `vendite/trgfn_doc_testata_lock_fuori_bozza`
  (gli argomenti montati su bolla e reso), `dbops/fn_pgtap_crea_reso` (fixture: la provenienza dal BB che scrive).
  `vendite/fn_ddt_trigger_ordine_testata` non ha pagina `manual/`: la sua sede è il COMMENT. Delle pagine già nell'elenco,
  T.2 cambia `vendite/ddt`, `vendite/resi`, `vendite/vw_ddt_lista`, `vendite/vw_resi_lista` (lotto T),
  `vendite/fn_genera_ddt_da_ordine`, `vendite/fn_genera_ddt_riconsegna` (elencate al lotto R: la testata cambia in T.2).

* **Aggiunte dal giro C.1** (2026-11-07, pagine toccate e non censite) (1): `vendite/vw_preventivi_smistamento_righe`
  (FATTURATA ed EMESSA_AF dalla riga di commessa, V-2). Delle pagine già nell'elenco, C.1 cambia
  `vendite/attivita_fatturabili` (le colonne `sorgente_*` ritirate; il manuale dava ancora per vivo l'indice unico
  ritirato a febbraio, R-5), `vendite/fatture_righe` (elencata al lotto R: la grammatica cambia in C.1),
  `vendite/fn_emit_attivita_fatturabili_da_commessa`, `vendite/trgfn_attivita_fatturabili_normalize`,
  `vendite/fn_resolve_termini_pagamento` e `dbops/fn_sorgenti_orfane_perimetro`.
  Fuori dal manuale: `installazione.md`, il requisito del limite dei file aperti del servizio PostgreSQL
  (§7.2 «L'apply del giro C.1»), ✅ scritto il 2026-11-07.
* **Aggiunte dal giro C.2** (2026-11-07, pagine toccate e non censite) (5): `vendite/fn_check_commessa_sorgente_emittente_omogeneo`,
  `vendite/fn_guard_commessa_sorgente_emittente`, `vendite/trgfn_commesse_sorgenti_guard_emittente` (le colonne del
  modello), `vendite/vw_documento_lineage_archi` (ricreata identica; il suo COMMENT porta ancora i marcatori di storia),
  `dbops/fn_pgtap_crea_commessa` (la ROOT in `sorgente_id`). Delle pagine già nell'elenco, C.2 cambia
  `vendite/commesse_sorgenti` (la chiave tipizzata, l'unicità nuova, il guard unico, il «non validata» di
  `sorgente_riga` non è più vero), `vendite/fn_link_commessa_sorgente`, `vendite/fn_commessa_viva_di_sorgente` (la
  firma), `vendite/trgfn_guard_fatturazione_immediata_immutabile`, `vendite/fn_documento_lineage_archi`,
  `script/fn_get_sorgente_emittente_sr_id` (la porta testuale si ritira: la pagina resta, l'oggetto c'è con la firma
  sulle colonne) e `script/trgfn_guard_sorgente_polimorfa_testuale` (montato solo su `pratiche_sorgenti`). Fuori dal
  manuale: la guida `sorgente-polimorfa` (§2, §4: la chiave canonica testuale del link) e il catalogo dei messaggi,
  dove la soluzione di `E_FATT_IMMEDIATA_NON_MODIFICABILE` dà una query con `sorgente_uid = '<uid>'` e la descrizione
  parla di un UNIQUE globale che non c'è più dal 2026-10-12 (il testo si corregge nel lotto DOC, col CSV dei messaggi).

* **Lotto 0 (meccanismo, catalogo)** (18): `config/sorgenti`, `dbops/fn_sorgenti_orfane_perimetro`, `dbops/fn_sorgenti_orfane`, `dbops/vw_sorgenti_orfane`, `pratiche/fn_stato_sorgente`, `script/fn_get_sorgente_emittente_sr_id`, `script/fn_sorgente_chiave_id`, `script/fn_sorgente_chiave_uuid`, `script/trgfn_guard_sorgente_polimorfa_testuale`, `script/trgfn_guard_sorgente_polimorfa_tipizzata`, `script/vw_stato_sorgente`, `vendite/fn_get_sorgente_documento_ref`, `vendite/vw_stato_sorgente_contratto`, `vendite/vw_stato_sorgente_ddt`, `vendite/vw_stato_sorgente_offerta`, `vendite/vw_stato_sorgente_ordine`, `vendite/vw_stato_sorgente_preventivo`, `vendite/vw_stato_sorgente_reso`.
* **Lotto R** (11): `dbops/vw_ddt_emessi_senza_scarico`, `vendite/fatture_righe`, `vendite/fn_documento_legami`, `vendite/fn_documento_lineage_archi`, `vendite/fn_genera_ddt_da_ordine`, `vendite/fn_genera_ddt_riconsegna`, `vendite/fn_list_ddt_da_pushare`, `vendite/fn_list_ordini_da_pushare`, `vendite/fn_list_preventivi_da_pushare`, `vendite/fn_push_offerta_a_contratto`, `vendite/ordini_righe`.
* **Lotto T** (21): `dbops/vw_resi_confermati_senza_carico`, `script/fn_check_ordine_annullabile`, `script/trgfn_default_emittente_fiscale`, ~~`storico/documenti_fatturazione_canali`~~, `vendite/contratti`, `vendite/ddt`, ~~`vendite/documenti_fatturazione_canali`~~, `vendite/fatture`, `vendite/fn_accoda_stampe_lotto`, `vendite/fn_list_commessa_attivita`, `vendite/fn_resolve_termini_pagamento`, `vendite/fn_select_attivita_fatturabili`, `vendite/ordini`, `vendite/resi`, `vendite/trgfn_ddt_normalize`, `vendite/trgfn_resi_guard_ddt_consegnato`, `vendite/trgfn_resi_normalize`, `vendite/vw_dash_competenza_attivita`, `vendite/vw_ddt_lista`, `vendite/vw_lotti_gruppi_serviti`, `vendite/vw_resi_lista`.
* **Lotto C** (22): `script/fn_check_sorgente_chiudibile`, `vendite/attivita_fatturabili`, `vendite/commesse_attivita`, `vendite/commesse_sorgenti`, `vendite/fn_aggiungi_onere_commessa`, `vendite/fn_annulla_commessa_attivita`, `vendite/fn_batch_upsert_commessa_attivita`, `vendite/fn_build_gruppo_fatturabile_key`, `vendite/fn_commessa_viva_di_sorgente`, `vendite/fn_emit_attivita_fatturabili_da_commessa`, `vendite/fn_fattura_origini`, `vendite/fn_link_commessa_sorgente`, `vendite/fn_list_consumi_da_pushare`, `vendite/fn_list_contratti_da_pushare`, `vendite/fn_ritira_commessa_attivita_da_sorgente`, `vendite/fn_split_gruppo_fatturabile_key`, `vendite/fn_upsert_commessa_attivita`, `vendite/trgfn_attivita_fatturabili_normalize`, `vendite/trgfn_commesse_attivita_proietta_stato_preventivo`, `vendite/trgfn_doc_guard_chiusura_sorgente`, `vendite/trgfn_guard_fatturazione_immediata_immutabile`, `vendite/vw_dash_competenza_gruppi`.
* **Lotto D** (6): `documenti/documenti_generati`, `documenti/template_documenti`, `documenti/trgfn_documenti_generati_protect_snapshot`, `vendite/fatture_stampa_coda`, ~~`vendite/fn_set_documento_canale_stato`~~, ~~`vendite/trgfn_documenti_sync_canali`~~.
* **Lotto P** (8): `pratiche/fn_pratica_del_documento`, `pratiche/fn_reconcile_sorgente`, `pratiche/pratiche_sorgenti`, `pratiche/reconcile_errori`, `pratiche/trgfn_documento_reconcile_proiezione`, `script/vw_pratica_doc_sorgente`, `vendite/fn_genera_pratica_da_preventivo`, `vendite/vw_preventivi_pratiche`.
* **Lotto M** (8): `magazzino/eventi_assets`, `magazzino/fn_posta_inventario`, `magazzino/fn_posta_rettifica`, `magazzino/inventari`, `magazzino/movimenti_attesi`, `magazzino/movimenti`, `magazzino/rettifiche`, `magazzino/trasferimenti`.
* **fixture pgTAP (seguono la tabella)** (1): `dbops/fn_pgtap_crea_commessa`.
* **solo commento: da verificare** (5): `documenti/fn_risolvi_template_applicabile`, `documenti/trgfn_documenti_generati_check_coerenza`, `pratiche/fn_copia_definizione`, `script/fn_check_preventivo_annullabile`, `vendite/fn_get_tipo_doc_fiscale_id`.
* **menzione di passaggio: da verificare (spesso codici di `tipi_entita` per le note, che restano)** (46): `anagrafiche/vw_clienti_codice_ba`, `catalogo/trgfn_articoli_guard_flags_struttura_bom_attiva`, `config/stati_assets`, `config/stati_doc_contratti`, `config/stati_doc_offerte`, `config/stati_doc_ordini`, `config/stati_doc_preventivi`, `config/trgfn_sorgenti_normalize`, `dbops/automation_lock_columns`, `dbops/fn_pgtap_crea_sorgente`, `dbops/fn_ritira_attivo_orfani`, `dbops/fn_trigger_attivo_orfani`, `dbops/trgfn_child_requires_active_parent`, `dbops/vw_storico_scope_da_dichiarare`, `magazzino/causali`, `magazzino/fn_get_magazzino_note`, `magazzino/inventari_righe`, `magazzino/rettifiche_righe`, `magazzino/trasferimenti_righe`, `pagamenti/sistemazioni`, `pratiche/template_flussi_avanzamento_proiezione`, `pratiche/template_flussi`, `pratiche/trgfn_flussi_guard_chiusura_prematura`, `script/fn_available_actions_offerta`, `script/fn_resolve_controparte_sr_id`, `script/fn_scope_ef_whitelist_via_evento_asset`, `script/fn_scope_ef_whitelist_via_inventario`, `script/fn_scope_ef_whitelist_via_rettifica`, `script/fn_scope_ef_whitelist_via_trasferimento`, `script/fn_scope_note_magazzino_ef_perimetro`, `script/trgfn_componenti_guard_coerenza_bom`, `script/trgfn_note_validate_generic`, `script/vw_giornale_entita`, `vendite/fn_diagnostica_gruppi_fatturabili`, `vendite/fn_documento_lineage`, `vendite/fn_partite_merce`, `vendite/offerte_commerciali`, `vendite/resi_righe_rientri`, `vendite/trgfn_commesse_attivita_guard_tipo_doc_emittibile`, `vendite/trgfn_doc_snapshot_da_stato`, `vendite/trgfn_ordini_guard_transizione`, `vendite/vw_contratti_lista`, `vendite/vw_dash_fatturazione_offerte`, `vendite/vw_documento_lineage_archi`, `vendite/vw_documento_lineage_nodi`, `vendite/vw_ordini_lista`.
* **manuali del backend (`docs/it/backend/*/manual`): lotto BE/FE** (29): `backend:catalogo/api_catalogo`, `backend:core/api_tipi_entita_lookup`, `backend:documenti/api_documenti_helpers`, `backend:documenti/api_documenti_templates`, `backend:magazzino/api_magazzino`, `backend:pratiche/api_coda_lavoro`, `backend:pratiche/api_percorso`, `backend:pratiche/api_pratica_detail`, `backend:vendite/api_commessa_attivita`, `backend:vendite/api_commessa_oneri`, `backend:vendite/api_commessa_stato`, `backend:vendite/api_contratti`, `backend:vendite/api_dashboard_aperto`, `backend:vendite/api_dashboard_backlog`, `backend:vendite/api_dashboard_competenza`, `backend:vendite/api_ddt`, `backend:vendite/api_famiglie_documento`, `backend:vendite/api_fatture_list`, `backend:vendite/api_iva_resolve`, `backend:vendite/api_lineage_passaggi`, `backend:vendite/api_offerte`, `backend:vendite/api_ordini`, `backend:vendite/api_preventivi_collega_pratica`, `backend:vendite/api_preventivi`, `backend:vendite/api_run_commesse_push`, `backend:vendite/api_situazione_merce`, `backend:vendite/modello-contratti`, `backend:vendite/offerte_service`, `backend:vendite/push_preventivo_handler`.

#### E. I documenti aperti in `work-in-progress/` che toccano il tema

Si allineano nel lotto DOC con un rimando a questo brief, oppure si chiudono se il loro oggetto è superato:

| Documento | Che cosa |
| --- | --- |
| `brief-db-articoli-obsoleto-dal.md` | il suo lotto B si scrive nel lotto R; il §137 («modello A») è superato. **Si allinea subito**, nel lotto R, perché è vivo |
| `analisi-db-magazzino-aggancio-documento-e-produzione.md` | D-1…D-3 sul modello A: superate da S-3 |
| `analisi-db-magazzino-carico-e-scarico.md` | `uq_mag_movimenti_identita` (603): riscritto nel lotto M |
| `brief-design-proiezione-stato-dominio.md`, `brief-design-guida-rollout-multidominio.md` | `config.sorgenti` come registro dei tipi, il reconcile con `key_selector` letterale (E-9) |
| `valutazione-modello-di-dominio-db.md`, `analisi-pratiche-domini-anello3.md` | i puntatori polimorfi dichiarati |
| `sviluppo-listini-da-flussi.md` | l'«opzione B polimorfica» con due colonne id/uuid: va scritta sul modello di questo brief |
| `sviluppo-preventivi-acquisti.md`, `integrazione-con-sistemi-esterni.md` | i documenti d'acquisto futuri e l'import esterno (§4: tabella di collegamento propria) |
| altri con una menzione (`analisi-db-commessa-e-produzione-predisposizione`, `brief-db-addebito-trasporto-ordine`, `brief-db-revisione-dbops`, `analisi-simmetria-ordini-acquisto`, `piano-migrazione-primevue-5`, `fatturazione-modello-utilities-gas-ee-idrico`, `analisi-pratiche-valutazione-stato`, due SQL una tantum, `allegati/codici-errore-classe-note.csv`) | da verificare |


## 8. Richiesta al team BE/FE (unica, si consegna dopo il lotto Z)

> Si riempie durante i lotti DB: ogni lotto aggiunge qui i suoi cambi, con il percorso intero. Finché il lotto Z non
> è chiuso, **non è da implementare**. Il punto di partenza è l'elenco chiuso dei file per famiglia nelle schede
> dell'Appendice.

### 8.1 Dal lotto 0, giro 0.1 (2026-11-06)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-0.1-a ✅ | cinque codici nuovi, classe `TECNICO`: `E_SORG_CHIAVE_NON_CONFORME`, `E_SORG_RIGA_NON_DEL_DOCUMENTO`, `E_SORG_DETTAGLIO_NON_DELLA_RIGA`, `E_SORG_LIVELLO_NON_PREVISTO`, `E_SORG_LIVELLO_MANCANTE` | `config.codici_errore` → `config.vw_codici_errore_identita` → il file generato delle policy (`error_policies_generated.py`) | rigenerare il file col comando che lo produce: il controllo di divergenza (`test_error_policies_divergenza_db`) è rosso finché non lo si fa. Nessun `ui_action`: sono 500 |
| BE-0.1-b | `vendite.fn_get_sorgente_documento_ref`: un id per un tipo a chiave `uid` ora si risolve; un id per un tipo a chiave `id` torna solo se il documento esiste ed è visibile | firma, colonne e `ROWS 1` invariati | nessuna azione attesa; lo leggono `vendite_repository` e `types.py` per il numero del documento d'origine. Da verificare negli smoke delle liste che lo usano |
| BE-0.1-c | `config.fn_sorgente_tabella` sul BB dei livelli | firma e risultato invariati | nessuna (`famiglie_repository`) |
| — | le colonne nuove (`sorgente_id`, `sorgente_riga` su `commesse_attivita`, `sorgente_dettaglio`) | vuote | nessuna finché un lotto di famiglia non le scrive |

### 8.2 Dal lotto 0, giro 0.2 (2026-11-06)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-0.2-a ✅ | codice nuovo `E_SORG_ORIGINE_REFERENZIATA`, classe `CONFLITTO_STATO` (409): la cancellazione di un documento, una riga o un dettaglio da cui altri record dichiarano di nascere | `config.codici_errore` → file generato delle policy | rigenerare il file (come BE-0.1-a). Lo solleva il DB su un `DELETE`: le cancellazioni del BE (bozze di preventivo, ordine, bolla, righe) lo ricevono come 409 con la frase pronta. Nessun campo da accendere |
| BE-0.2-b | `dbops.vw_sorgenti_orfane` ha colonne nuove (`grammatica`, `livello`, `sorgente_id`, `sorgente_dettaglio`) | vista del presidio | nessuna attesa: la legge il digest dei presidi, non il BE. Da verificare con un grep sui lettori |

### 8.3 Dal lotto 0, giro 0.3 (2026-11-06)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| — | i lettori della sorgente di testata leggono anche `sorgente_id`; firme con `sorgente_id` in coda per `vendite.fn_ddt_trigger_ordine_testata` e `vendite.fn_ddt_vincoli_cliente` | nessuna delle funzioni toccate cambia firma o colonne per il BE (grep su `backend/apps`, 2026-11-06: il BE chiama per nome solo `fn_documento_legami`, firma invariata) | nessuna |
| — | `script.fn_get_sorgente_emittente_sr_id(tipo, sorgente_id, sorgente_uid)`, firma nuova; la testuale resta | il BE non la chiama (solo un commento nel file generato delle policy) | nessuna |
| — | il dettaglio JSON di alcuni errori dei guard di bolla e reso porta in più `sorgente_id` | `E_DOC_SORGENTE_NON_TROVATA`, `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`, `E_RESO_DA_DDT_TRASFERIMENTO`, `E_RESO_DDT_NON_CONSEGNATO` | nessuna: chiave in più, nessuna tolta |

### 8.4 Dal lotto R, giro R.1 (2026-11-06)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-R.1-a | le cancellazioni di un'origine citata da una riga di vendita ora si fermano con `E_SORG_ORIGINE_REFERENZIATA` (codice di BE-0.2-a, nessun codice nuovo): la riga o la testata di un reso da cui è nata una riconsegna, l'eccezione di un'offerta da cui sono nate righe d'ordine o di contratto, la riga di un preventivo citata da una riga d'ordine o da una revisione | `DELETE` del BE sulle bozze e sulle loro righe | nessuna, se BE-0.2-a è fatto: è un 409 con la frase pronta |
| — | `ordini_righe.sorgente_riga` senza DEFAULT 0 (NULL sulla riga scelta a mano) | colonna | nessuna: grep su `backend/apps` (2026-11-06): il BE non scrive né legge la sorgente delle righe d'ordine |
| — | `vendite.fn_offerta_righe_espanse` ha una colonna in più in coda (`eccezione_id`) | funzione | nessuna: il BE non la chiama (grep, 2026-11-06) |

### 8.5 Dal lotto T, giro T.2 (2026-11-06)

Il giro T.1 (ritiro del registro dei canali) non ha voci: BE e FE non lo nominano (grep, 2026-11-06).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-T.2-a ✅ | il reso si scrive con la chiave della bolla in `sorgente_id`: l'uid della bolla in `sorgente_uid` ora è rifiutato dal guard unico con `E_SORG_CHIAVE_NON_CONFORME` (codice esistente, `TECNICO`) | `resi_service.py:534-535` → `resi_repository.create_reso` (`:636`, `:647`), `INSERT INTO vendite.resi` | passare `sorgente_id` = l'id della bolla (e `sorgente_uid` NULL), oppure prendere la coppia da `script.fn_sorgente_provenienza('DDT_VENDITA', <id bolla>)`, il BB che scrive. Test: `tests/services/test_resi_service.py:261`, `tests/db/test_resi_create_db.py:58-83`, `tests/services/test_righe_bozza_guard.py:321` (INSERT a mano con l'uid) |
| BE-T.2-b ✅ | la bolla d'origine del reso non si trova più per uid: dopo la conversione `resi.sorgente_uid` è NULL | `resi_repository.get_stato_e_ddt_origine` (`:333`, `LEFT JOIN vendite.ddt d ON d.uid = r.sorgente_uid`) | il join con la regola d'incontro, `(d.id = r.sorgente_id OR d.uid = r.sorgente_uid)`, oppure `ddt_origine_id` da `vendite.vw_resi_lista`, che lo dà già |
| BE-T.2-c | `vendite.vw_ddt_lista`: colonna nuova `sorgente_id` (in coda); `sorgente_uid` NULL per ogni bolla di oggi (le sue sorgenti hanno chiave `id`); per la **bolla di riconsegna** `sorgente_codice_interno` = `RESO_VENDITA` e `ordine_origine_id`/`ordine_origine_numero` NULL (la provenienza è il reso, D-4) | vista → `ddt_repository.py:72` (filtro su `ordine_origine_numero`), FE `DdtSearchTable.vue:9` (colonna `ordine_origine_numero`) | nessuna obbligatoria. Da decidere lato BE/FE: la riconsegna non si trova più filtrando per numero d'ordine, e la sua colonna «ordine» è vuota. Se serve mostrarne l'origine, la vista ha tipo e chiave della sorgente (il reso) |
| BE-T.2-d | `vendite.vw_resi_lista`: colonna nuova `sorgente_id` (in coda); `sorgente_uid` NULL; `ddt_origine_id`/`ddt_origine_numero` invariati | vista → FE `ResoDrawer.vue:353`, `ResoForm.vue:92` | nessuna: il FE legge `ddt_origine_*`, che restano |
| — | le colonne non modificabili in bozza di bolla e reso (`non_editable_fields` della capability) contengono anche `sorgente_id` | `script.fn_available_actions_ddt`, `script.fn_available_actions_reso` | nessuna: nessun form espone la sorgente |
| — | la lineage non ha più l'arco di testata ordine → riconsegna: la riconsegna discende dall'ordine attraverso la bolla d'origine e il reso | `vendite.fn_documento_lineage_*` | nessuna attesa; da guardare nello smoke di «Transito» su una riconsegna |
| BE-T.2-e | una bolla o un reso con una sorgente che non esiste: il codice è `E_SORG_NOT_FOUND` (dal guard unico, `TECNICO`), non più `E_DOC_SORGENTE_NON_TROVATA` | INSERT/UPDATE di `vendite.ddt` e `vendite.resi` | se il BE o il FE mappano `E_DOC_SORGENTE_NON_TROVATA` su bolle e resi, la mappa prende anche `E_SORG_NOT_FOUND` (grep, 2026-11-06: il codice compare solo nelle policy generate e in `error_messages_fallback.py:446`) |


### 8.6 Dal lotto T, giro T.3 (2026-11-07)

Fino al giro T.5 le colonne parallele (`ordini.documento_origine_*`, `contratti.offerta_id`) restano scritte dai verbi
accanto alla provenienza: i lettori BE di oggi non si rompono in T.3. Si rompono in T.5, quando le colonne si
ritirano; le voci sotto vanno fatte con il lotto BE, che arriva dopo il lotto Z (cioè dopo T.5).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-T.3-a ✅ | l'ordine dall'offerta sbatte su un indice nuovo, `uq_ordini_v_sorgente_offerta` (23505), quando la provenienza è scritta e la colonna parallela no; dal giro T.5 è l'unico | `ordini_service.py:88` (`_UNIQUE_CONSTRAINTS`, mappa `uq_ordini_v_documento_origine_offerta` → `E_ORD_OFFERTA_GIA_CONVERTITA`) | aggiungere `uq_ordini_v_sorgente_offerta` con lo stesso codice e la stessa frase; la voce vecchia si toglie con T.5. Gemello sul contratto: `uq_contratti_sorgente_offerta` (oggi nessuna mappa BE per `uq_contratti_offerta_id`: il verbo lo previene con `E_OFFERTA_CONTRATTO_GIA_GENERATO`) |
| BE-T.3-b ✅ | l'ordine nato dal preventivo si trova dalla provenienza: `sorgente_tipo_id` PREVENTIVO + `sorgente_uid` = l'uid del preventivo. `documento_origine_*` si ritira in T.5 | `ordini_repository.get_ordine_by_documento_origine` (`:426-433`, `WHERE documento_origine_tipo = %s AND documento_origine_id = %s`) ← `post_smistamento_handler.py:73`, `preventivi_service.py:2144` | leggere da `vendite.vw_ordini_lista` (`documento_origine_tipo`, `documento_origine_id`: alias stabili, ora calcolati dalla provenienza), oppure la regola d'incontro su `vendite.ordini` (`(p.id = o.sorgente_id OR p.uid = o.sorgente_uid)` col tipo). Test: `tests/db/test_origine_ordine_sorgente_db.py:56` (scrive la colonna parallela a mano, con un'offerta che non esiste: dal giro T.3 la vista la legge dalla provenienza, e dal T.5 la colonna non c'è), `tests/db/test_genera_ordine_da_offerta_db.py:129`, `tests/handlers/test_post_smistamento_handler.py`, `tests/services/test_preventivi_service.py:740` |
| BE-T.3-c ✅ | il contratto nato dall'offerta si trova dalla provenienza; `offerta_id` si ritira in T.5 | `offerte_repository.py:228` (`LEFT JOIN vendite.contratti c ON c.offerta_id = o.id AND NOT c.is_abortito_snapshot`) | leggere da `vendite.fn_offerta_documenti_vivi(offerta_id)`, la sede unica dei documenti vivi, o con la regola d'incontro su `contratti.sorgente_*` |
| — | `vendite.vw_ordini_lista`: tre colonne nuove in coda (`sorgente_tipo_id`, `sorgente_id`, `sorgente_uid`); `documento_origine_tipo`, `_id`, `_codice` invariati di nome, tipo e valore, calcolati dalla provenienza | vista → `ordini_repository.py:280-286` (etichetta dell'origine per la stampa), FE `OrdiniSearchTable.vue` | nessuna |
| — | `vendite.vw_fatture_lista`: `sorgente_id` in coda, di norma NULL | vista | nessuna |
| — | `vendite.fn_push_offerta_a_contratto`: con una pratica il percorso ora va in fondo (V-1); il contratto entra in `pratiche_sorgenti` con l'id. Un tipo OFFERTA_COMMERCIALE assente dal catalogo è `E_SORG_CONF`, non più `E_CONFIG_MANCANTE` (tecnici tutti e due) | `offerte_service` (push a contratto con pratica) | nessuna obbligatoria; da guardare nello smoke «offerta → contratto con pratica», che prima si fermava con `E_SORG_FORMATO` |
| — | un ordine o un contratto con una provenienza inesistente, o con la chiave della specie sbagliata, sono rifiutati dal guard unico (`E_SORG_NOT_FOUND`, `E_SORG_CHIAVE_NON_CONFORME`, `TECNICO`); un preventivo o un'offerta citati non si cancellano (`E_SORG_ORIGINE_REFERENZIATA`, codice di BE-0.2-a) | INSERT/UPDATE di `vendite.ordini`, `vendite.contratti`, `vendite.fatture`; DELETE delle bozze di preventivo | nessuna: il BE non scrive la provenienza di testata (grep, 2026-11-07); i 409 hanno la frase pronta |

### 8.7 Dal lotto T, giro T.4 (2026-11-07)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-T.4-a ✅ | codici nuovi `E_DELETE_DOC_CON_RIGHE` e `E_DELETE_CONTRATTO_CON_SUCCESSIVI` (`CONFLITTO_STATO`, 409): una bozza con righe attive non si cancella, un contratto precedente di altri contratti nemmeno | `apps/core/services/error_policies_generated.py`, `error_messages_fallback.py` | rigenerarli dal catalogo, insieme a BE-0.1-a e BE-0.2-a |
| — | ordine, bolla, reso e contratto si cancellano solo da bozza vuota anche nel DB; un reso confermato non si cancella più | `ordini_service.elimina_ordine`, `ddt_service.elimina_ddt`, `resi_service.elimina_reso` | nessuna: il controllo del BE resta come controllo preventivo, e ha lo stesso significato (stato iniziale, zero righe attive). I 409 del DB arrivano solo da un percorso che il BE non ha. Nessun percorso cancella un contratto (grep, 2026-11-07) |

### 8.8 Dal lotto T, giro T.5 (2026-11-07)

Le colonne parallele non ci sono più: le due voci di T.3 che le leggevano (§8.6) si rompono dall'apply del giro T.5.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-T.5-a ✅ | `vendite.ordini.documento_origine_tipo` e `_id` non esistono più | `ordini_repository.get_ordine_by_documento_origine` (`:426-433`) ← `post_smistamento_handler.py:73`, `preventivi_service.py:2144`; test `tests/db/test_origine_ordine_sorgente_db.py:56`, `tests/db/test_genera_ordine_da_offerta_db.py:129` | è BE-T.3-b: leggere da `vendite.vw_ordini_lista` (alias stabili) o con la regola d'incontro su `sorgente_*` |
| BE-T.5-b ✅ | `vendite.contratti.offerta_id` non esiste più | `offerte_repository.py:228` (`LEFT JOIN vendite.contratti c ON c.offerta_id = o.id`) | è BE-T.3-c: `vendite.fn_offerta_documenti_vivi(offerta_id)` |
| BE-T.5-c ✅ | `uq_ordini_v_documento_origine_offerta` non esiste più | `ordini_service.py:88` (`_UNIQUE_CONSTRAINTS`) | la voce vecchia si toglie; resta `uq_ordini_v_sorgente_offerta` (BE-T.3-a) |
| — | `vw_ordini_lista`: `documento_origine_tipo`, `_id`, `_codice` restano, calcolati dalla provenienza | `ordini_repository.py:280-286`, `ordine_document_context_builder.py:213`, FE `OrdiniSearchTable.vue` | nessuna |
| — | la capability perde dalle colonne ferme `documento_origine_*` dell'ordine e `offerta_id` del contratto (`non_editable_fields`, dal montaggio del lock). Su tutti gli ordini e contratti di dbdev è l'unica differenza della capability (2026-11-07) | capability di ordine e contratto | nessuna, se il FE non le nomina (grep FE, 2026-11-07: le nomina solo un commento) |

**Stato al 2026-11-07, dopo il giro BE** (team BE, da committare). Fatte le voci segnate ✅ di §8:

* **I codici** (BE-0.1-a, BE-0.2-a, BE-T.4-a): policy rigenerate e ripieghi scritti, nello stesso giro di
  BE6 di `brief-db-revisione-dbops`.
* **Il reso** (BE-T.2-a/b): `ResiRepository.create_reso` riceve la bolla (`ddt_id`) e scrive la coppia di
  `script.fn_sorgente_provenienza('DDT_VENDITA', <id>)`, il BB che scrive; il service non legge più il tipo
  in `config.sorgenti` (il BB solleva su tipo spento o bolla non visibile). `get_stato_e_ddt_origine` incontra
  la bolla con la regola del modello. I tre test che scrivevano l'uid a mano passano dal repository.
* **L'ordine dal preventivo** (BE-T.3-b, BE-T.5-a): `get_ordine_by_documento_origine` parte dalla coppia del
  BB che scrive e incontra l'ordine con la regola del modello; `vw_ordini_lista` non porta
  `is_abortito_snapshot`, che il lettore filtra. `test_origine_ordine_sorgente_db` riscritto su un preventivo
  vero; il caso dei legami (provenienza dall'offerta) è passato a `test_genera_ordine_da_offerta_db`, sull'ordine
  che genera il verbo. Il test del «codice corto» rifiutato dalla FK di `documento_origine_tipo` è uscito con la
  colonna.
* **Il contratto dall'offerta** (BE-T.3-c, BE-T.5-b): il dettaglio dell'offerta legge il contratto vivo da
  `vendite.fn_offerta_documenti_vivi`. Nessun test sul DB leggeva quel dettaglio: ne è nato uno (push, prima e
  dopo).
* **L'indice dell'ordine dall'offerta** (BE-T.3-a, BE-T.5-c): la mappa di `ordini_service` nomina
  `uq_ordini_v_sorgente_offerta`.
* BE-T.2-e: nessuna mappa BE su `E_DOC_SORGENTE_NON_TROVATA`, niente da fare.

### 8.9 Dal lotto C, giro C.1 (2026-11-07)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-C.1-a ✅ | `vendite.attivita_fatturabili.sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga`, `sorgente_origine_tipo_id` non esistono più | `PipelineRepository.list_attivita_da_fatturare` (`pipeline_repository.py:1824-1826`, `:1860-1862`) → il dataclass `AttivitaDaFatturare` (`:189-191`); test `tests/services/test_fatture_righe_service.py:242-244` | togliere le tre colonne dalla SELECT e i tre campi dal dataclass: il consumatore unico (`fatture_righe_service.py`) non li legge (censimento S-7, L5). La provenienza dell'attività è `commessa_attivita_id` |
| BE-C.1-b ✅ | gli smoke che scrivono o leggono le stesse colonne | `backend/scripts/tests/_smoke_fatturazione.py:204, 268, 281` (INSERT con `sorgente_tipo_id`, `uuid4()` in `sorgente_uid`, `sorgente_origine_tipo_id`); `smoke-push-termine-documento-commessa.py:340` (JOIN su `a.sorgente_tipo_id`) e `:413-418` (INSERT che copia `a.sorgente_tipo_id` e scrive `sorgente_uid`) | togliere le colonne dagli INSERT; il JOIN legge il tipo dalla riga di commessa (`commesse_attivita.sorgente_tipo_id` per `commessa_attivita_id`) |
| BE-C.1-c ✅ | una riga di fattura con il tipo vuole la chiave del documento: CHECK `chk_fatture_righe_sorgente_forma` (23514) e il guard unico (`E_SORG_CHIAVE_NON_CONFORME`, `E_SORG_RIGA_NON_DEL_DOCUMENTO`, `E_SORG_NOT_FOUND`, `TECNICO`) | `PipelineRepository.list_righe_per_plafond` (`:1959`) e `insert_parte_plafond` (`:2005-2014`): la parte IVA ricopia `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` della capofila | ricopiare anche `sorgente_id` (e leggerlo in `list_righe_per_plafond`). Oggi tocca le sole righe di fattura nate da una riga di commessa (la commessa sta in `sorgente_id`); le righe aggregate le scrive NULL `:3489-3503`, che resta valido |
| — | `vendite.vw_preventivi_smistamento_righe`: FATTURATA ed EMESSA_AF ora compaiono (V-2) | vista → `PreventiviSmistamentoDialog.vue:148`, `frontend/src/vendite/constants.js:175-181`, i servizi preventivi e ordini | nessuna obbligatoria: gli stati c'erano già nel FE, ora arrivano. Da guardare nello smoke del dialogo di smistamento |
| — | il pull (`fn_emit_attivita_fatturabili_da_commessa`) non solleva più `E_CODICE` per un tipo COMMESSA assente dal catalogo; firma, colonne e codici invariati per il resto | `commesse_service` / pipeline (chiamata del pull) | nessuna |

### 8.10 Dal lotto C, giro C.2 (2026-11-07)

Dall'apply del giro C.2 la voce BE-C.2-a si rompe (accettato dal piano).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-C.2-a ✅ | `vendite.fn_commessa_viva_di_sorgente(bigint, text)` non c'è più: la firma è `(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)`, con la regola d'incontro | `CommesseRepository.get_commessa_viva_by_sorgente` (`commesse_repository.py:837-868`, SQL `SELECT vendite.fn_commessa_viva_di_sorgente(s.id, %s)`), chiamato da `preventivi_service.py:2082` con l'uid del preventivo; test `tests/services/test_commesse_repository.py:217-250`, `test_preventivi_service.py:855` | passare le due chiavi del documento: per il preventivo `(s.id, NULL, %s::uuid)`. Chi ha il documento può passare id e uid insieme; il parametro `sorgente_chiave` lascia il posto a `sorgente_id` / `sorgente_uid`. Il codice `E_COMMESSA_SORGENTE_SCONOSCIUTA` resta |
| BE-C.2-b | `vendite.commesse_sorgenti.sorgente_uid` è `uuid` e tiene solo la chiave dei tipi a uid (preventivo); ordine, contratto, DDT e COMMESSA stanno in `sorgente_id`. CHECK `chk_commesse_sorgenti_sorgente_forma` (23514), unicità `uq_commesse_sorgenti_sorgente_commessa` (23505), guard unico (`E_SORG_CHIAVE_NON_CONFORME`, `E_SORG_RIGA_NON_DEL_DOCUMENTO`, `E_SORG_NOT_FOUND`, `TECNICO`) | il BE non scrive né legge la tabella (censimento S-4: la porta è la madre DB, `commesse_source_handlers.py:471`) | nessuna; i commenti di `commesse_repository.py:845-847` («`id::text` per ordine, contratto, bolla e consumi») si allineano |
| — | contesti d'errore: `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` e `E_COMMESSA_SORGENTE_EMITTENTE_MISTO` portano `sorgente_id` e `sorgente_uid` (prima solo `sorgente_uid`, la chiave testuale); `E_FATT_IMMEDIATA_NON_MODIFICABILE` nomina il documento col suo id e perde `chiave_canonica` (tiene `documento_id`, `documento_uid`) | i messaggi passano da `ErrorManager`; nessun consumatore BE/FE legge quelle chiavi (grep, 2026-11-07) | nessuna |
| — | un documento collegato a una commessa non si cancella: `E_SORG_ORIGINE_REFERENZIATA` dal lato in uscita (ordini, preventivi, contratti, DDT) | `delete_ordine`, `delete_ddt`, `elimina_preventivo` (BE, solo da bozza vuota) | nessuna obbligatoria: una bozza non va in commessa. Da guardare se un giorno un documento in commessa tornasse in bozza |

### 8.11 Dal lotto C, giro C.3 (2026-11-07)

Dall'apply del giro C.3 si rompono gli smoke della voce BE-C.3-c; le altre voci sono da fare, non rotture.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-C.3-a ✅ | `vendite.fn_upsert_commessa_attivita` prende `p_sorgente_riga` in coda (`DEFAULT NULL`); il batch legge la chiave `sorgente_riga` di ogni riga. Senza, la riga di push nasce a livello documento: il guard la ammette, ma la provenienza perde la riga | `CommesseRepository.upsert_attivita` (`commesse_repository.py:1006-1081`, `p_sorgente_uid => %s`), il payload del batch (`:1129-1130`, `:1198`), `commesse_source_handlers.py:770` (dalla riga del lister) | passare `p_sorgente_riga => row.riga_id` (e `"sorgente_riga": ...` nel batch); i lister lo restituiscono già (`riga_id`; i consumi non ce l'hanno: NULL). `p_sorgente_uid` resta com'è, l'uid del documento in testo |
| BE-C.3-b | `vendite.commesse_attivita.sorgente_uid` è `uuid` e tiene solo la chiave dei tipi a uid (preventivo); ordine, contratto, DDT, consumi stanno in `sorgente_id`; la riga in `sorgente_riga`. CHECK `chk_commesse_attivita_sorgente_forma` (23514), guard unico (`E_SORG_CHIAVE_NON_CONFORME`, `E_SORG_RIGA_NON_DEL_DOCUMENTO`, `E_SORG_NOT_FOUND`, `TECNICO`) | il BE non legge la colonna dalla tabella: la lista (`fn_list_commessa_attivita`) e le viste di competenza tengono `sorgente_uid` `text` con l'uid del documento per ogni tipo | nessuna. Da sapere: un documento, o una sua riga, citato da una riga di commessa non si cancella (`E_SORG_ORIGINE_REFERENZIATA`) |
| BE-C.3-c ✅ | la chiave del push di una riga con provenienza deve cominciare con il codice del tipo e l'uid del documento (`E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`, `TECNICO`, nuovo) | gli smoke: l'helper `crea_riga_commessa` (`backend/scripts/tests/_smoke_commessa.py:38-85`, sorgente di default COMMESSA con l'id della commessa, chiavi `SMOKE:...` scritte a mano) e i suoi chiamanti (`smoke-fattura-scadenze.py`, `smoke-group-attivita-contratto.py`, `smoke-ritorno-lotto-a-draft.py`, `smoke-push-termine-documento-commessa.py`, `smoke-fattura-aggregazione-termini.py`); `smoke-push-onere-ordine.py:162-175` legge `ca.sorgente_uid` aspettando l'uid dell'ordine | l'helper compone la chiave con `script.fn_segment_key(<codice>, <uid del documento>, <riga>)` su un documento vero (come fa ora il builder pgTAP: un consumo, `dbops.fn_pgtap_crea_consumo`, o il documento del test); lo smoke dell'onere legge `ca.sorgente_id` (l'id dell'ordine) |
| BE-C.3-d | codice nuovo `E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO` nei CSV | `error_policies_generated.py` | rigenerare il file delle policy d'errore |
| — | `vendite.fn_ritira_commessa_attivita_da_sorgente` e `script.fn_check_sorgente_chiudibile` prendono `(tipo, sorgente_id, sorgente_uid, ...)` con la regola d'incontro, al posto della chiave testuale | nessun chiamante nel BE (grep, 2026-11-07) | nessuna |
| BE-C.3-e | V-7, dall'apply di `20261108-07` (giro C.4): per un gruppo il cui documento non ha numero (i consumi), `vendite.fn_riferimento_gruppo_fatturabile` restituisce il codice della commessa invece della chiave grezza, come la colonna `riferimento` di `vendite.vw_dash_competenza_gruppi` | `fn_list_lotto_segnalazioni` (colonna del riferimento della scheda Critiche del lotto); nessuna chiamata diretta nel backend (grep, 2026-11-07) | nessuna: cambia solo il testo mostrato; se il FE o i test BE confrontano il riferimento con la chiave, si allineano |
| — | contesti d'errore: `E_RIGA_COMMESSA_NON_MANUALE` porta `sorgente_id` e `sorgente_uid` (prima solo `sorgente_uid`), il documento lo nomina il BB che risolve; `E_RITIRO_SORGENTE_PARAMETRO_MANCANTE` nomina `p_sorgente_id / p_sorgente_uid` | i messaggi passano da `ErrorManager`; nessun consumatore legge quelle chiavi (grep, 2026-11-07) | nessuna |

**Stato al 2026-11-07, dopo il giro BE del lotto C** (team BE, da committare). Fatte le voci segnate ✅
di §8.9, §8.10, §8.11; gli undici smoke rossi dall'apply (nove Python, due bash) sono tornati verdi.

* **L'attività senza provenienza sua** (BE-C.1-a): `AttivitaDaFatturare` e la SELECT di
  `list_attivita_da_fatturare` non hanno più le tre colonne; il test del servizio righe le toglie dal builder.
* **La parte IVA del plafond** (BE-C.1-c): `insert_parte_plafond` ricopia la provenienza **intera** della
  capofila, `sorgente_id` compreso, e `list_righe_per_plafond` lo legge.
* **La commessa viva di un documento** (BE-C.2-a): `CommesseRepository.get_commessa_viva_by_sorgente`
  prende `sorgente_id` / `sorgente_uid` al posto di `sorgente_chiave` e chiama la firma nuova; il preventivo
  passa il suo uid. ⚠️ Era la causa di `smoke-test-pratica-preventivi-bivio.sh` (ASSERZIONE): il bivio
  aggancia la commessa alla pratica da qui.
* **La riga del documento nel push** (BE-C.3-a): `CommessaAttivitaInput.sorgente_riga`, passato come
  `p_sorgente_riga` alla madre e come chiave `sorgente_riga` al batch; il push lo prende dal `riga_id` del
  lister (`PushableRow.riga_sorgente_id`; i consumi: NULL). Lo prova lo smoke dell'onere, che ora legge
  anche la riga.
* **Gli smoke** (BE-C.1-b, BE-C.3-c). ⛔ La sorgente COMMESSA che l'helper usava di default **non può più
  essere** la provenienza di una riga di commessa: `vendite.commesse` non ha `uid`, e il guard della chiave
  ne vuole uno. L'helper `crea_riga_commessa` vuole ora la sorgente esplicita; la riga di uno smoke viene da
  un **consumo vero** della sua commessa (`_smoke_commessa.consumo_di_commessa`, dal builder
  `dbops.fn_pgtap_crea_consumo`), uno per commessa e condiviso dalle sue righe (il kit vuole la stessa radice
  di chiave per padre e componenti), e la chiave la compone `chiave_di_commessa` col suffisso dello smoke.
  Le INSERT di attività non scrivono più le colonne ritirate; lo smoke del termine legge il tipo dalla riga
  di commessa (la «forma reale» è ora `commessa_attivita_id` + la riga che nomina l'ordine); quello
  dell'onere legge `sorgente_id` e `sorgente_riga`.
  ⚠️ **Il difetto trovato per strada, che non dava errore a chi lo aveva**: i builder `fn_pgtap_crea_*`
  escono con `SET CONSTRAINTS ALL IMMEDIATE`, per contratto, e l'impostazione vale per il resto della
  transazione. Uno smoke che dopo il builder esegue la pipeline vera vedeva un guard differito scattare a
  metà verbo (`E_LOTTO_FATTURE_STATO_INCOERENTE` sulla numerazione, che al commit non sarebbe scattato).
  `_smoke_contesto.ripristina_vincoli_differiti` rimette differiti **i soli** vincoli che il catalogo
  dichiara `INITIALLY DEFERRED`, e `consumo_di_commessa` lo chiama dopo il builder.
  ⏭️ **Per il team DB, da decidere**: ogni smoke che chiama un builder e poi un verbo ha lo stesso rischio
  (oggi `fn_pgtap_crea_ddt_da_ordine` in `smoke-nota-credito-resi`, verde perché il suo percorso non
  incontra un guard differito). Se un builder potesse lasciare i vincoli come li ha trovati — o dichiarare
  nel COMMENT che li chiude — il BB lato smoke non servirebbe.
  ↩️ **Risposta del team DB (2026-11-07).** Il contratto c'è già, ed è voluto: i builder escono IMMEDIATE
  per chiudere la **propria** unità di lavoro, così una fixture rotta si ferma nel builder e non tre verbi
  dopo (guida `pgtap-come-si-scrive-un-test`, §«Il mondo si costruisce»: «gli helper escono con i vincoli
  IMMEDIATE»). «Lasciarli come li ha trovati» non si può: in PostgreSQL il modo dei vincoli di una
  transazione non si legge, quindi non si ripristina (la stessa guida lo dice per la riga di contesto).
  Resta la dichiarazione, ed è quasi tutta già scritta: il COMMENT di 21 builder su 25 dice che escono
  IMMEDIATE; mancano `fn_pgtap_crea_cliente_ba`, `fn_pgtap_crea_emittente_operatore`,
  `fn_pgtap_crea_soggetto_ruolo` e `fn_pgtap_porta_a_stato` (dbdev, 2026-11-07). Quei quattro COMMENT
  li chiude `20_code/dbops/20261108-09` (via di Tid, 2026-11-07), e il presidio
  `dbops/test-builder-pgtap-vincoli-immediate-v1` tiene la regola per i builder futuri: perimetro derivato dal
  corpo, senza elenco. Provato in transazione su scratch e dbdev: 2/2 con l'estratto, senza il test 2 nomina
  i quattro. ⇒ **`ripristina_vincoli_differiti`
  è la risposta giusta e resta**: rimette differiti solo i vincoli `INITIALLY DEFERRED`, cioè proprio il
  default della transazione. `SET CONSTRAINTS ALL DEFERRED`, che usano i pgTAP «fattura + atto», differirebbe
  anche i `DEFERRABLE INITIALLY IMMEDIATE`, e in uno smoke non va. Ogni smoke che chiama un builder e poi
  un verbo vero lo chiama dopo il builder, anche `smoke-nota-credito-resi`, che oggi è verde solo perché il
  suo percorso non incontra un guard differito. Lato DB non serve un BB gemello: i pgTAP vogliono IMMEDIATE,
  e il solo consumatore è lo smoke.
* **Fuori dal brief, nello stesso giro**: `smoke-test-soggetti.sh` leggeva `ruolo_codice`, rinominato in
  `ruolo_codice_interno` dal commit `61eb42c39` (2026-11-04): il parser falliva in silenzio e la lista dei
  ruoli sembrava vuota.
* BE-C.3-d: la policy rigenerata e il ripiego di `E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO` sono nel
  working tree (non di questo giro). BE-C.2-b, BE-C.3-b, BE-C.3-e e le voci «—»: nessuna azione. L'esempio
  `"ATTIVITA"` di `test_sorgenti_repository.py` (§8.12) resta: è una stringa su un cursore finto.

### 8.12 Dal lotto C, giro C.4 (2026-11-07)

Nessuna rottura. V-7 è la voce BE-C.3-e del §8.11.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| — | `config.sorgenti` non ha più il tipo `ATTIVITA` (id 1); `config.tipi_entita.ATTIVITA` resta, con `is_sorgente` false: le note delle attività fatturabili non cambiano | `apps/config/sorgenti.py` non ha la costante; `config/tests/db/test_sorgenti_repository.py:71-72` usa `"ATTIVITA"` solo come stringa d'esempio, su un cursore finto (grep, 2026-11-07) | nessuna obbligatoria; l'esempio del test si può passare a un codice che esiste (`COMMESSA`) |
| — | cancellare un'attività fatturabile non passa più dal lato «in uscita» (`E_SORG_ORIGINE_REFERENZIATA`): niente nasce da un'attività | nessun percorso BE lo aspettava | nessuna |

### 8.13 Dal lotto D, giro D.1 (2026-11-07)

⚠️ Dall'apply la stampa di un documento e il drenatore della coda danno errore fino a BE-D.1-a … -e. Percorso intero,
elenco chiuso (grep su `backend/apps`, 2026-11-07, fuori dai test).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-D.1-a ✅ | `documenti.documenti_generati`: la chiave del documento stampato sta in `sorgente_id` (tipi a chiave id: ordine, DDT, contratto, fattura) **oppure** in `sorgente_uid uuid` (preventivo, offerta), mai tutte e due (`chk_documenti_generati_sorgente_forma`); il guard unico rifiuta la chiave sbagliata (`E_SORG_CHIAVE_NON_CONFORME`) | `documenti/services/document_generation_service.py:192-330` (`genera_documento` riceve già `sorgente_id` e `sorgente_uid`), `:448-525` (la ristampa); `documenti/db/documenti_repository.py:229-240` (`DOCUMENTO_GENERATO_CREATE_COLUMNS` non ha `sorgente_id`) | scrive la coppia del `key_selector` del tipo: `sorgente_id` per i tipi a chiave id, `sorgente_uid` per quelli a uid. La coppia giusta da una chiave qualsiasi la dà `script.fn_sorgente_chiave(tipo, chiave text)`. `sorgente_id` entra nelle colonne dell'INSERT |
| BE-D.1-b ✅ | il progressivo delle versioni è uno per documento, sulla chiave nuova (`uq_documenti_generati_sorgente_progressivo`: tipo, `sorgente_id`, `sorgente_uid`, riga, progressivo, `NULLS NOT DISTINCT`) | `documenti_repository.next_progressivo_sorgente` (`:1255-1290`: MAX+1 su `sorgente_uid = %s`) | MAX+1 sulla chiave del tipo (`sorgente_id = %s` oppure `sorgente_uid = %s::uuid`), riga con `IS NOT DISTINCT FROM` |
| BE-D.1-c ✅ | la lista e il dettaglio delle stampe di un documento si cercano sulla chiave del tipo; `sorgente_uid` è `uuid` | `documenti_repository.list_documenti_per_sorgente` (`:1372-1420`, filtra `d.sorgente_uid = %s` col testo), le SELECT di dettaglio (`:1437`, `:1496`, `:1546`); `documenti/api/sorgente_documenti_views.py:178`, `:239`, `:354` (`sorgente_uid=str(entity["uid"])` per i sei domini); FE `documenti/components/DocumentiGeneratiSorgenteList.vue` (via API) | la factory passa la chiave del tipo (l'id dell'entità per ordine, DDT, contratto, fattura; l'uid per preventivo e offerta), il repository filtra sulla colonna giusta e restituisce `sorgente_id` accanto a `sorgente_uid`. Se il contratto dell'API cambia, il componente FE lo segue. Da qui la lista vede anche le stampe del drenatore |
| BE-D.1-d ✅ | `vendite.fatture_stampa_coda.sorgente_uid` non c'è più: la fattura è in `sorgente_id` | `vendite/db/pipeline_repository.py:2705` (`RETURNING … c.sorgente_uid`); `vendite/services/stampa_coda_drainer_service.py:265` (`sorgente_uid=str(item["sorgente_uid"])` a `genera_documento`) | il claim non la restituisce; il drenatore passa a `genera_documento` la fattura in `sorgente_id`, come chiede BE-D.1-a |
| BE-D.1-e | un documento che ha una stampa non si cancella (`E_SORG_ORIGINE_REFERENZIATA`, `CONFLITTO_STATO`, già nel registro) | la cancellazione delle bozze e dei preventivi; oggi il caso è stretto (si stampa dopo l'emissione, e i documenti si cancellano solo da bozza vuota) | nessuna obbligatoria: il codice c'è già. Se un percorso cancella una bozza stampata, il messaggio lo dice |
| — | `ai_assistant/tools/documenti_tools.py:105-135` risolve l'uid del PREVENTIVO dall'id e lo passa | solo PREVENTIVO, a chiave uid | nessuna, se `genera_documento` (BE-D.1-a) sceglie la colonna dal tipo |
| — | i `*_document_context_builder` (`vendite/services/{preventivo,offerta,contratto,ddt,fattura}_document_context_builder.py`) ricevono `sorgente_id` da `build_context` | non leggono la chiave della stampa (grep, 2026-11-07) | nessuna |

### 8.14 Dal giro K.1, il nome della chiave (2026-11-07)

⚠️ Dall'apply il push di una riga di commessa dà errore fino a BE-K.1-a e -b (richiesta del BE: chiude la sua voce).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-K.1-a ✅ | `vendite.fn_upsert_commessa_attivita` e `vendite.fn_link_commessa_sorgente`: il parametro della chiave del documento si chiama `p_sorgente_chiave` (prima `p_sorgente_uid`); tipo e significato invariati | `vendite/db/commesse_repository.py:1058` (`p_sorgente_uid => %s` verso la madre); nessuna chiamata BE alla porta per nome (grep, 2026-11-07) | il nome nuovo nella chiamata |
| BE-K.1-b ✅ | `vendite.fn_batch_upsert_commessa_attivita`: la chiave della riga è `sorgente_chiave` (prima `sorgente_uid`). Una riga con la chiave vecchia passa la chiave NULL | `commesse_repository.py:1150` (`"sorgente_uid": inp.sorgente_uid` nella riga del batch); da verificare se finiscono nel batch `vendite/services/commesse_push_orchestrator.py:269` e `vendite/db/resi_repository.py:680` | la chiave nuova nelle righe del batch |

**Stato al 2026-11-07, dopo il giro BE di D.1 e K.1** (team BE, da committare su `dev/backend-tid`). Fatte le voci
segnate ✅ di §8.13 e §8.14: i due percorsi rotti dall'apply (la stampa e il suo drenatore, il push) sono ripristinati.

* **K.1, il nome della chiave del push** (BE-K.1-a, -b). Il campo di `CommessaAttivitaInput` si chiama
  `sorgente_chiave`, come il parametro della madre (`p_sorgente_chiave =>`) e la chiave della riga del batch
  (`"sorgente_chiave"`): un nome solo dal dataclass al DB, nessun punto che traduce. Il push lo riempie con l'uid
  che il lister restituisce. Allineati anche la fixture SQL di `vendite/tests/db/test_ricerca_liste_db` (madre e
  porta del link) e l'helper degli smoke `_smoke_commessa.crea_riga_commessa`. I due punti che il §8.14 lasciava
  «da verificare» non vanno nel batch: `resi_repository.create_reso` scrive le colonne vere di `vendite.resi`,
  `commesse_push_orchestrator:269` il perimetro nel log del push.
  ⭐ **Il presidio nuovo** `vendite/tests/db/test_commesse_porta_nomi_db`: ogni `p_… =>` di `upsert_attivita` è un
  parametro della madre (`proargnames`), e ogni chiave di una riga del batch è letta dal wrapper (`v_row ->> '…'`
  nel corpo). Rosso per mutazione su tutti e due i nomi vecchi. È il difetto che nel batch non dà errore: una
  chiave che nessuno legge è un NULL passato in silenzio.
* **D.1, la chiave della stampa** (BE-D.1-a … -d). `genera_documento` e `list_documenti_per_sorgente` prendono
  l'id dell'entità (`sorgente_id`, quello che il builder del contesto usava già) e **non più `sorgente_uid`**: la
  coppia da scrivere e da cercare la dà il DB, `DocumentiRepository.chiave_sorgente` → `script.fn_sorgente_chiave`,
  una sede per i due usi (`_chiave_documento` del service). `sorgente_id` entra nelle colonne dell'INSERT;
  progressivo e lista contano sullo stesso frammento, `_filtro_documento_sorgente`, che rifiuta due chiavi o
  nessuna (`ValueError`, mai un filtro vuoto che ridarebbe 1 a ogni stampa). Le SELECT di lista e dettaglio
  restituiscono `sorgente_id` accanto a `sorgente_uid` (che resta testo nel contratto API). Il claim della coda di
  stampa non restituisce più `sorgente_uid` e il drenatore passa la fattura per id (prima del giro: `EXPLAIN` del
  claim rosso con `UndefinedColumn` su dbdev, ora verde). Il tool AI `cerca_documenti_generati` non risolve più
  l'uid: la sua mappa è la verifica d'accesso delle sorgenti abilitate (`_SORGENTE_VERIFICHE`).
  Presidio nuovo `documenti/tests/db/test_chiave_stampa_db`: il ramo a chiave **id** si costruisce con un ordine
  vero (gli altri test sul DB stampano solo preventivi), dall'id e dall'uid la stessa coppia, progressivo e lista
  eseguiti. Le fixture DB di `test_ricerca_liste_db` e `test_scritture_dinamiche_db` di documenti scrivevano una
  stampa con una chiave inventata (`"scrdin-1"`, un uuid finto) e «la prima sorgente per id»: ora citano il
  preventivo vero di `dbops.fn_pgtap_crea_preventivo`, col tipo cercato per codice.
* **FE**: nessuna modifica. `DocumentiGeneratiSorgenteList.vue` non legge la chiave; la lista riceve in più
  `sorgente_id`.
* BE-D.1-e: nessuna azione, il codice c'è già.
* ⏭️ **Per la decisione aperta di Tid sul nome della colonna dei lister** (riga 7-quadragies-quater): lato BE i
  lister restituiscono l'**uid del documento** per ogni tipo, e `PushableRow.sorgente_uid` lo dice giusto; il nome
  che diceva «uid» portando un id era quello della madre, ora chiuso da K.1. Un fatto per la decisione, non una
  proposta.

### 8.15 Dal giro K.2, la colonna della chiave dei lister (2026-11-07)

⚠️ Dall'apply il push dal BE perde la chiave del documento fino a BE-K.2-a: il BE legge le colonne dei lister per nome.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-K.2-a ✅ | I cinque lister del push (`vendite.fn_list_{preventivi,ordini,ddt,contratti,consumi}_da_pushare`): la chiave del documento esce nella colonna `sorgente_chiave` (prima `sorgente_uid`); tipo (`text`) e valore (l'uid del documento in testo) invariati | `vendite/db/commesse_repository.py:137` (`_PUSHABLE_SHARED_COLS`, `"sorgente_uid"`), `:369` (`_col("sorgente_uid")`), `:320` (`PushableRow.sorgente_uid`); i lettori di `row.sorgente_uid`: `vendite/services/commesse_source_handlers.py:770`, `:879`, `:882` | leggere la colonna `sorgente_chiave`. Il nome del campo di `PushableRow` è del BE; con BE-K.1-b la riga del lister può andare al batch così com'è |

**Stato al 2026-11-08, dopo il giro BE di K.2** (team BE, da committare su `dev/backend-tid`). Il push è ripristinato.

* Il campo di `PushableRow` si chiama `sorgente_chiave`, come la colonna dei lister, il campo di
  `CommessaAttivitaInput` e la chiave del batch: un nome solo dal lister al DB. Cambiati la whitelist
  `_PUSHABLE_SHARED_COLS`, il guard «chiave o segment_key NULL», il passaggio alla madre
  (`commesse_source_handlers`, `sorgente_chiave=row.sorgente_chiave`) e il lettore dei kit del contratto
  (`_componenti_listino_loader`); allineati i mock di `test_commesse_repository` e `test_commesse_source_handlers`.
* ⭐ **Il presidio esteso** `vendite/tests/db/test_commesse_porta_nomi_db`, test 3 `test_colonne_dei_lister`: ogni
  colonna che il binding legge con `_col` esce dalla RETURNS TABLE di **tutti e cinque** i lister (catalogo,
  `proargmodes = 't'`); le tre opzionali (`termine_pagamento_id`, `modalita_pagamento_id`, `causale_onere_id`) da
  almeno uno. Rosso per mutazione col nome vecchio nella whitelist. Prima i test della lettura erano solo coi mock,
  che specchiano la whitelist del BE: verdi anche col nome che il DB non dà più.
* Provato sul percorso vero: `smoke-push-termine-documento-commessa` verde su dbdev (lister → `PushableRow` →
  madre → fattura, in rollback).
* ✅ **Il filtro del push singolo** (decisione di Tid, 2026-11-08): si chiamava `sorgente_uid` ma portava l'**id** del
  documento, il 4° parametro `p_<sorgente>_id` dei lister. Ora è `sorgente_id` lungo tutta la catena:
  `fetch_pushable_rows` → `handler.run` → `CommessaPushOrchestrator.run` → `pr_run_commesse_push_one` → i chiamanti
  di DDT, ordini e preventivi, e i due smoke del push. Cambia anche la chiave del perimetro scritto in
  `commesse_push_log.risultato` (`perimetro.sorgente_id`): nessun lettore fuori dai test (grep su BE, FE e doc DB). I
  `sorgente_uid` che restano nel BE sono chiavi vere o testuali di altre porte (il link della commessa, la stampa, le
  liste), non questo filtro.

### 8.16 Dal lotto P, giro P.1 (2026-11-08)

⚠️ Dall'apply il link documento → pratica dal BE dà errore fino a BE-P.1-a, e i lettori del link fino a BE-P.1-b e -c.
Il BE non chiama direttamente `fn_pratica_del_documento`, `fn_stato_sorgente` né `fn_reconcile_sorgente` (grep,
2026-11-08: solo commenti).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-P.1-a ✅ | `pratiche.pratiche_sorgenti`: la chiave del documento sta in `sorgente_id` (tipi a chiave id: ordine, contratto, commessa) **oppure** in `sorgente_uid uuid` (preventivo), mai tutte e due (`chk_pratiche_sorgenti_sorgente_forma`); il guard unico rifiuta la chiave sbagliata (`E_SORG_CHIAVE_NON_CONFORME`) e il documento che non c'è (`E_SORG_NOT_FOUND`). L'unicità è `uq_pratiche_sorgenti_pratica_sorgente_ruolo` (pratica, tipo, `sorgente_id`, `sorgente_uid`, ruolo, `NULLS NOT DISTINCT`) | `pratiche/db/pratiche_repository.py:984-1006` (`upsert_pratica_sorgente`: INSERT di `sorgente_uid` testo, `ON CONFLICT (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)`); chiamanti `vendite/services/preventivi_service.py:901` (PREVENTIVO, `prev["uid"]`), `:2087` (COMMESSA, `str(commessa_id)`), `vendite/handlers/post_smistamento_handler.py:87` (ORDINE_VENDITA, `str(ordine_id)`) | scrive la coppia del `key_selector` del tipo. La dà `script.fn_sorgente_chiave(tipo, chiave text)` da una chiave qualsiasi in testo, quindi i tre chiamanti possono restare come sono. L'`ON CONFLICT` punta al vincolo nuovo (`ON CONFLICT ON CONSTRAINT uq_pratiche_sorgenti_pratica_sorgente_ruolo`, come i verbi DB) |
| BE-P.1-b ✅ | i lettori del link cercano il documento sulla colonna del suo tipo: `sorgente_uid` è `uuid`, l'id sta in `sorgente_id` | `pratiche_repository.py:1015-1028` (`get_pratica_id_by_sorgente`, `ps.sorgente_uid = %s`; chiamante `vendite/services/ordini_service.py:354`, `str(ordine_id)`), `:1032-1043` (`_sorgente_link_exists`); `vendite/db/preventivi_repository.py:132`, `:607`, `:635` (`p_link.uid::text = ps.sorgente_uid` → `p_link.uid = ps.sorgente_uid`); `vendite/db/ordini_repository.py:460` (`ps.sorgente_uid::bigint` → `ps.sorgente_id`) | la colonna del tipo, senza cast a testo. Per i due metodi che ricevono una chiave in testo: `script.fn_sorgente_chiave`, oppure la regola d'incontro (`ps.sorgente_id = %s OR ps.sorgente_uid = %s`) con id e uid del documento |
| BE-P.1-c ✅ | `script.vw_pratica_doc_sorgente`: la chiave testuale `sorgente_uid` lascia il posto a `sorgente_id bigint` + `sorgente_uid uuid` (una sola valorizzata); le altre colonne identiche. ⭐ La vista è la sede della regola d'ancora che il BE ricopia in `_doc_sorgente_lateral` | `pratiche_repository.py:96-120` (`_doc_sorgente_lateral`: la LATERAL coi due rami `fn_sorgente_chiave_uuid/_id(ps.sorgente_uid)`, ora rotti); `:235` (JOIN alla vista, legge `sorgente_descrizione`) | la copia BE della regola si ritira, e i lettori passano dalla vista (regola del 2). Se resta, i due rami leggono `ps.sorgente_uid` e `ps.sorgente_id` senza i BB canonici |
| BE-P.1-d ✅ | `vendite.vw_preventivi_pratiche`: l'id del link si chiama `pratica_sorgente_id` (prima `sorgente_id`, E-10) | `vendite/db/preventivi_repository.py:1407` (`list_pratiche`, `SELECT *`), il tipo `PreventivoPraticaRow` e chi serializza `sorgente_id` | il nome nuovo; se l'API espone il campo, il FE lo segue |
| BE-P.1-e ✅ deciso | un preventivo (o un ordine, un contratto, una commessa) collegato a una pratica non si cancella: lo blocca il DB (`E_SORG_ORIGINE_REFERENZIATA`, `CONFLITTO_STATO`, già nel registro) | `vendite/services/preventivi_service.py:555-592` (`elimina_preventivo`, il pre-check «niente pratiche collegate» su `list_pratiche`) | **Tid, 2026-11-08: si ritira** (scelta A). Il pre-check legge lo stesso aggancio che il guard conta (`vw_preventivi_pratiche` → `pratiche_sorgenti` per uid del preventivo): una regola, una sede. Restano, come controllo preventivo, quelli di stato e righe, finché il DB non ha la sua regola sul preventivo (lotto Z) |
| — | i due verbi DB che scrivono il link sollevano `E_SORG_CONF` (non più `E_CONFIG_MANCANTE`) su un tipo assente o spento | `vendite.fn_genera_pratica_da_preventivo`, `vendite.fn_push_offerta_a_contratto` | nessuna: `E_SORG_CONF` è già nelle policy |

**Stato al 2026-11-08, dopo il giro BE di P.1** (team BE, da committare su `dev/backend-tid`). Fatte le voci segnate
✅; il link documento → pratica e i suoi lettori sono ripristinati.

* **Chi scrive il link** (BE-P.1-a). `PraticheRepository.upsert_pratica_sorgente` prende la coppia da
  `script.fn_sorgente_provenienza(codice, chiave)`, lo stesso BB dei verbi DB e del reso (§8.8), e l'`ON CONFLICT ON
  CONSTRAINT uq_pratiche_sorgenti_pratica_sorgente_ruolo`. Il parametro si chiama `sorgente_chiave` (una chiave
  qualsiasi del documento, in testo: come K.1 e K.2): i tre chiamanti passano quello che passavano. Il controllo «codice
  non in `config.sorgenti`» del BE (`E_PRATICA_SORGENTE_TIPO_INVALIDO`, con `_sorgente_link_exists`) esce: lo dice il BB
  con `E_SORG_CONF`, e l'`ON CONFLICT DO UPDATE` conta la riga anche quando il link c'era.
* **Chi lo legge** (BE-P.1-b). `get_pratica_id_by_sorgente` (parametro `sorgente_chiave`) parte dalla coppia dello
  stesso BB e incontra il link con la regola del modello, come `get_ordine_by_documento_origine`; i tre lettori del
  preventivo ROOT incontrano `p_link.uid = ps.sorgente_uid` senza cast; `get_ordine_id_by_pratica` legge `ps.sorgente_id`.
* **La LATERAL per-flusso** (BE-P.1-c). L'ancora a livello pratica passa già dalla vista. La LATERAL che resta nel BE è
  l'ancora **per flusso** (`ps.flusso_id = f.id`, percorso e coda di lavoro): un'altra regola d'ordine (ROOT, poi il più
  recente), che la vista, una riga per pratica, non dà. I due rami leggono ora `ps.sorgente_uid` e `ps.sorgente_id`
  senza `script.fn_sorgente_chiave_uuid/_id`: il BE non è più un consumatore dei due BB che il lotto Z ritira.
  ⚠️ Resta la **seconda copia** della regola «link → stato del documento, un ramo per chiave»: vedi la richiesta R-P.1-1
  sotto.
* **BE-P.1-d**: nessun lettore BE del campo rinominato (`PreventivoPraticaRow` non lo ha, `list_pratiche` serve solo il
  conteggio di `elimina_preventivo`); il FE non lo nomina (grep, 2026-11-08).
* **BE-P.1-e**: non fatto, è una decisione di Tid (sotto).
* **Revisione critica dello stesso giro** (2026-11-08). I ruoli del link (`ROOT`, `COLLEGATO`) erano letterali in sei
  file: ora `RUOLO_LINK_ROOT` / `RUOLO_LINK_COLLEGATO` in `apps/pratiche/types.py`, passati come parametro nell'SQL.
  I due lettori «preventivo → pratica/flusso» di `preventivi_repository` ripetevano lo stesso blocco: un frammento solo
  (`_ROOT_PREVENTIVO_DI_REVISIONE_FROM`), accanto a quello della rev attiva. I mock di `PraticheRepository` nei tre
  test unitari toccati sono `autospec`: il nome vecchio del parametro è un `TypeError` (provato per mutazione), prima
  passava.
* ⭐ **Il presidio nuovo** `pratiche/tests/db/test_link_pratica_sorgente_db` (4 test, `ZEROERP_TEST_DB_E2E=1`): i due rami
  si costruiscono (un preventivo a chiave uid, ROOT dal verbo DB; un ordine a chiave id, COLLEGATO dal BE), ciascuno
  citato dall'id e dall'uid; idempotenza dell'`ON CONFLICT`; i lettori del preventivo e dell'ordine; `E_SORG_CONF` su un
  codice fuori catalogo; il percorso con la LATERAL eseguito. Rosso sul codice di prima (3 errori, 1 fallimento), verde
  dopo. Prima di questo giro lo scrittore e il reverse erano provati solo coi mock.
* Provati: i test Django toccati (225, verdi), `smoke-pratica-doc-sorgente-cross-emittente` verde su dbdev (in
  rollback; allineato il commento sul guard, ora quello unico), ruff e il cancello mypy verdi.
  ⏭️ **Da lanciare da Tid** (vogliono la password di `dev.smoke`): `smoke-test-pratica-preventivi-bivio.sh` (il
  percorso intero: ROOT, ordine COLLEGATO, commessa COLLEGATO) e `smoke-test-guida-inversione-preventivi.sh`.

**Richieste al team DB dal giro BE di P.1** (per il giro DB di fine cantiere, §7.2 «Lotto BE/FE»):

* **R-P.1-1 — la sede per-flusso della regola d'ancora.** `script.vw_pratica_doc_sorgente` è la sede della regola
  a livello pratica; il BE ne tiene la gemella per flusso (`pratiche_repository._doc_sorgente_lateral`, usata da
  `get_percorso_pratica` e `list_coda_lavoro`), con un'altra regola d'ordine. Proposta: una sede DB per flusso
  (una vista `script.vw_flusso_doc_sorgente`, una riga per `flusso_id`, gli stessi due rami della LATERAL), così la
  copia BE si ritira (regola del 2). Da decidere con Tid se la regola d'ordine per flusso deve restare diversa da quella
  per pratica, o allinearsi.
* **R-P.1-2 — `E_PRATICA_SORGENTE_TIPO_INVALIDO` senza più chi lo solleva.** Lo sollevava solo il BE
  (`upsert_pratica_sorgente`); nessuna funzione DB lo nomina (doc auto-generata, 2026-11-08). Da ritirare dai CSV dei
  codici e dei messaggi, e poi dalle policy generate e dal ripiego BE nello stesso giro.

**Decisione di Tid su BE-P.1-e (2026-11-08): A, il pre-check si ritira**, con due seguiti. ① Il DB non ha la regola «si
cancella solo la bozza vuota» su `vendite.preventivi`, `offerte_commerciali` e `commesse` (il giro T.4 l'ha messa su
ordini, bolle, resi e contratti): stato e righe del preventivo li controlla solo il BE, e un `DELETE` diretto di un
preventivo accettato senza agganci passerebbe. Entra nel lotto Z. ② Il caso vero dietro la domanda: la bozza creata dal
flusso PREVENTIVAZIONE e agganciata subito alla pratica (ROOT), se abbandonata vuota non si cancella. La proposta che
la bozza si porti via il suo aggancio (C, guard di `pratiche_sorgenti` da BLOCCA a CANCELLA) è un cambio di modello che
vale per ogni documento collegabile, e richiede ① prima: scritta in `gestione-pratiche-come-procedere.md` §3.

**La domanda posta a Tid (BE-P.1-e), per la storia.** Il pre-check di `elimina_preventivo` («niente pratiche collegate», su
`list_pratiche`) ripete il guard DB (`E_SORG_ORIGINE_REFERENZIATA`). Proposta BE: ritirarlo, con `list_pratiche` e
`PreventivoPraticaRow` che restano senza consumatori, e il test `test_elimina_preventivo_con_pratiche_bloccato` che passa
sul DB. A favore: una regola, una sede. Contro: il messaggio del DB è generico («documento referenziato»), quello del BE
dice «pratiche collegate». Il giro T.4 ha lasciato i pre-check di stato e righe come «controllo preventivo»: qui il
brief dice «si può ritirare».

### 8.17 Dal lotto M, giro M.1 (2026-11-08)

⚠️ Dall'apply la consultazione dei movimenti per documento dà risultati vuoti fino a BE-M.1-a: il BE filtra per il
tipo della riga (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`), che nessun movimento ha più. Il BE non chiama la primitiva, lo
storno né la disponibilità (grep, 2026-11-08: solo un commento in `magazzino_repository.py:946`). I cinque tipi di
foglia restano in `config.sorgenti` fino al giro M.3: le costanti BE e il test del seed non si rompono ora, ma
vanno ritirati con M.3 (la voce è BE-M.3-a, §8.19).

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-M.1-a ✅ | `magazzino.movimenti`: `sorgente_tipo_id` è il tipo del **documento** (`INVENTARIO`, `RETTIFICA`, `TRASFERIMENTO`, `DDT_VENDITA`, `RESO_VENDITA`; `EVENTO_ASSET` resta), la chiave del documento sta in `sorgente_id`, la riga in `sorgente_riga`, il dettaglio (prelievo, rientro) nella colonna nuova `sorgente_dettaglio`. I movimenti di oggi sono convertiti | `magazzino/db/magazzino_repository.py:986-997` (`list_movimenti`: il filtro `documento_sorgente` = `sg.codice_interno = <tipo della riga> AND EXISTS (… r.id = mv.sorgente_riga AND r.<fk> = %s)`), `:383-384` (`_MOVIMENTI_SELECT`), `magazzino/db/famiglie.py:56,84,103` (`sorgente_codice_interno` della famiglia = `INVENTARIO_RIGA` / `RETTIFICA_RIGA`), `magazzino/services/consultazione_service.py` (i parametri `inventario_id` / `rettifica_id`) | il filtro per documento diventa `sg.codice_interno = <tipo del documento> AND mv.sorgente_id = %s`, e l'`EXISTS` sulle righe se ne va; la famiglia porta il tipo del documento (`INVENTARIO`, `RETTIFICA`; il campo `fk_riga` non serve più al filtro). La SELECT proietta anche `sorgente_id` e `sorgente_dettaglio` |
| BE-M.1-b ✅ | il parametro `sorgente_tipo` dell'API prende i codici dei documenti | `magazzino/api/views.py:845` (filtro), `:862-863` (descrizione OpenAPI «INVENTARIO_RIGA, RETTIFICA_RIGA, …») | i valori nuovi nel contratto e nella descrizione |
| BE-M.1-c ✅ | `MovimentoRow`, `BloccoRow`: le colonne `sorgente_id`, `sorgente_dettaglio` | `magazzino/types.py:182-184`, `:212-214`; `_BLOCCHI_SELECT` (`magazzino_repository.py:355-356`) | i due campi nuovi (nullable) |
| BE-M.1-d ✅ | i test e lo smoke che si aspettano i codici di riga sui movimenti | `magazzino/tests/services/test_magazzino_service.py:94`, `tests/api/test_magazzino_api.py:316`, `tests/db/test_documento_interno_db.py:194`, `backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py:25,116-118` | i codici dei documenti |
| UI-M.1-a | il seed della lista dei movimenti descrive il tipo della riga | `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv:865-866` | ✅ le due descrizioni (tipo del documento, riga del documento) le ha corrette il team DB nel giro M.2; restano le colonne nuove (documento, dettaglio), decise da Tid per il lotto BE/FE |
| FE-M.1-a ✅ | i codici della sorgente del movimento | `frontend/src/magazzino/vocabolari.js:62-66` (`SORGENTE_MOVIMENTO`), `:112`, `:131` (la sorgente delle famiglie), `etichette.js` (`PREFISSO_SORGENTE_MOVIMENTO`), `locales/it.json` e `en.json` (`magazzino.movimenti.sorgente.INVENTARIO_RIGA` …), `components/MovimentiSearchTable.vue` (filtro e cella), `stores/movimenti.js` (deep-link `inventario_id` / `rettifica_id`), `views/MovimentiView.vue`, `DisponibilitaBlocchiPopover.vue` | i codici dei documenti e le loro etichette; il deep-link per documento |
| — | i presidi: `dbops.vw_ddt_emessi_senza_scarico` e `vw_resi_confermati_senza_carico` prendono in coda un conteggio (`prelievi_senza_scarico`, `rientri_senza_carico`), `vw_magazzino_movimenti_senza_costo` le colonne `sorgente_id`, `sorgente_dettaglio`; nasce `dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo`, con la sua riga in `dbops.presidi` e `presidi_testi` | digest e pagina dei presidi (leggono il catalogo) | nessuna obbligatoria: il catalogo porta la riga nuova |
| — | i cinque posting (inventario, rettifica, trasferimento, bolla, reso) sollevano `E_SORG_CONF` (non più `E_CONFIG_MANCANTE`) su un tipo assente o spento; l'annullo di bolla e reso solleva `E_CONFIG_MANCANTE` se il tipo del documento manca, invece di saltare lo storno | i verbi DB | nessuna: i due codici sono già nelle policy |
| — | `codici_errore.csv`: la descrizione di `E_MAG_MOVIMENTO_GIA_REGISTRATO` (le nove colonne dell'identità) | il file generato delle policy d'errore | rigenerarlo, come per ogni CSV dei codici |


### 8.18 Dal lotto M, giro M.2 (2026-11-08)

Nessuna voce obbligatoria: le testate di magazzino e l'evento la provenienza non la scrive nessuno, né il DB né il BE
(grep, 2026-11-08). Cambia il significato delle colonne che il BE legge.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-M.2-a ✅ | `magazzino.inventari`, `rettifiche`, `trasferimenti`, `eventi_assets`: la chiave del documento d'origine sta in `sorgente_id` (o `sorgente_uid`), `sorgente_riga` è la riga di quel documento (NULL = il documento intero); il guard unico rifiuta la chiave sbagliata (`E_SORG_CHIAVE_NON_CONFORME`), il documento che non c'è (`E_SORG_NOT_FOUND`), la riga di un altro documento (`E_SORG_RIGA_NON_DEL_DOCUMENTO`). Un documento citato non si cancella (`E_SORG_ORIGINE_REFERENZIATA`) | `magazzino/db/magazzino_repository.py:238` (`_documento_select`: `t.sorgente_tipo_id, t.sorgente_riga, t.sorgente_uid`), `magazzino/types.py:44-46` (`DocumentoInternoRow`) | proiettare anche `sorgente_id` (nullable) e leggere `sorgente_riga` come riga, non come chiave. I quattro codici sono già nelle policy |

### 8.19 Dal lotto M, giro M.3 (2026-11-08)

⚠️ Dal commit del giro il test Django `config/tests/test_sorgenti_seed.py::test_ogni_costante_e_un_codice_attivo_del_seed`
è rosso: legge `sorgenti.csv`, che non ha più `INVENTARIO_RIGA` e `RETTIFICA_RIGA`. Accettato dal piano.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-M.3-a ✅ | `config.sorgenti` non ha più `INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`; restano entità di `config.tipi_entita` (`is_sorgente = false`), per note ed errori | `config/sorgenti.py:60-62` (le costanti `SORGENTE_INVENTARIO_RIGA`, `SORGENTE_RETTIFICA_RIGA`); `config/tests/test_sorgenti_seed.py`; i lettori delle costanti (`magazzino/db/famiglie.py:34,84,103`, già in BE-M.1-a) | le due costanti si ritirano; servono `SORGENTE_INVENTARIO`, `SORGENTE_RETTIFICA` (e `SORGENTE_TRASFERIMENTO` se la famiglia nasce), che la famiglia usa al posto delle vecchie. Con BE-M.1-a, nello stesso giro |
| FE-M.3-a ✅ | i codici di foglia non arrivano più come sorgente di un movimento | `frontend/src/magazzino/vocabolari.js` (`SORGENTE_MOVIMENTO`), i locales `magazzino.movimenti.sorgente.<codice>` | i codici dei documenti, con FE-M.1-a. Le chiavi `config.tipi_entita.<x>_riga` restano: sono l'etichetta dell'entità |

**Stato al 2026-11-08, dopo il giro BE di M.2** (team BE, da committare su `dev/backend-tid`). Fatte le voci segnate ✅.

* **BE-M.2-a.** `_documento_select` (`magazzino/db/magazzino_repository.py`) proietta anche `t.sorgente_id`;
  `DocumentoInternoRow` (`magazzino/types.py`) ha `sorgente_id: int | None`, col commento sulla grammatica (tipo,
  chiave, riga = la riga del documento, NULL = il documento intero). Nessuno scrive le quattro colonne, né il BE né il
  FE: il BE le legge soltanto. `eventi_assets` non ha lettori nel BE.
* **Il presidio** è il test 14 di `magazzino/tests/db/test_documento_interno_db` (DB vero): il documento d'origine si
  costruisce (un altro inventario, un tipo delle sorgenti come la bolla del pgTAP), la provenienza si scrive con l'SQL
  perché nessun verbo la scrive; la testata torna tipo, chiave e riga, poi la chiave senza riga.
* **BE-M.3-a e FE-M.3-a** erano già chiuse dal giro BE di M.1: le costanti `…_RIGA` ritirate, `test_sorgenti_seed`
  verde sul seed nuovo.
* **UI-M.1-a** è fatta dal DB nel giro M.2 (le due descrizioni di `lista_colonna.csv:865-866`).

**Richieste al team DB dal giro BE di M.2** (2026-11-08):

* **R-M.2-1 — la lista dei movimenti mostra documento e dettaglio** (decisione di Tid del 2026-11-08, UI-M.1-a).
  Due righe nuove in `80_data/sql/ui/lista_colonna.csv` per la lista dei movimenti (`lista_id` 77, gruppo
  «Sorgente», accanto a `sorgente_codice_interno` e `sorgente_riga`): `sorgente_id` (`numeric`, «la chiave del
  documento da cui è nato»; vuota per un evento d'asset, che sta in `sorgente_uid`) e `sorgente_dettaglio`
  (`numeric`, colonna `bigint`: l'id del dettaglio della riga, il prelievo della bolla o il rientro del reso; vuota
  per gli altri documenti). Etichette, ordine, larghezza, flag
  (filtrabile/ordinabile/esportabile) e chiavi i18n le sceglie il DB nella forma delle due righe vicine; le chiavi
  i18n (`magazzino.movimenti.col_sorgente_id`, `…col_sorgente_dettaglio`) le aggiunge poi il FE in `it.json` /
  `en.json`. Il BE non cambia: `_MOVIMENTI_SELECT` proietta già le due colonne e `MovimentoRow` le ha. ⚠️ Se le
  colonne diventano filtrabili od ordinabili, il BE le deve aggiungere a `MOVIMENTI_SORT_COLUMNS` e ai filtri: va
  detto nella consegna.
* **R-P.1-2, da anticipare** (§8.16). Su dbdev `E_PRATICA_SORGENTE_TIPO_INVALIDO` risulta già **ritirato** (2026-11-08,
  con la nota «Lo sollevava solo il backend…»), ma `80_data/sql/config/codici_errore.csv:422` non porta né
  `obsoleto_dal` né la nota: il DB è avanti rispetto a git. Effetto: `core/tests/test_error_policies_divergenza_db` è
  rosso, e il BE **non** rigenera `error_policies_generated.py` finché il ritiro non è nel CSV (rigenerare col DB
  avanti scriverebbe nel repo una cosa che il repo non contiene). Si chiede di portare il ritiro nel CSV; poi il BE
  rigenera.

**Stato al 2026-11-08, dopo il giro BE di M.1** (team BE, committato `1b45fcc58c`, merge #58). Fatte le voci segnate
✅; la consultazione dei movimenti per documento è ripristinata.

* **Il filtro per documento** (BE-M.1-a). `list_movimenti` filtra `sg.codice_interno = <tipo del documento> AND
  mv.sorgente_id = %s`: l'`EXISTS` sulle righe se n'è andato. La famiglia porta il tipo del documento
  (`SORGENTE_INVENTARIO`, `SORGENTE_RETTIFICA` in `apps/config/sorgenti.py`; le costanti `…_RIGA` sono ritirate, nessun
  modulo le nomina). `fk_riga` e `tabella_righe` restano nel registro `FAMIGLIE`: li usano i lettori e gli scrittori
  delle righe, non più il filtro. Il filtro usa `uq_mag_movimenti_identita`, che comincia per `(sorgente_tipo_id,
  sorgente_id)`.
* **API e tipi** (BE-M.1-b, -c). La descrizione OpenAPI di `sorgente_tipo` elenca i codici dei documenti;
  `MovimentoRow` e `BloccoRow` hanno `sorgente_id` e `sorgente_dettaglio`, proiettati da `_MOVIMENTI_SELECT` e
  `_BLOCCHI_SELECT`.
* **Test e smoke** (BE-M.1-d). I codici dei documenti; i test sul DB vero provano anche `sorgente_id` = il documento e
  `sorgente_riga` = la riga (inventario), e il tipo e la chiave (rettifica).
* **FE** (FE-M.1-a). `SORGENTE_MOVIMENTO` in `magazzino/vocabolari.js` ha i sei tipi di documento che scrivono sul
  registro, le famiglie la sorgente del documento, `it.json` / `en.json` le sei etichette. `etichette.js`,
  `MovimentiSearchTable.vue`, `stores/movimenti.js`, `MovimentiView.vue` e `DisponibilitaBlocchiPopover.vue` non
  cambiano: leggono il vocabolario, e il deep-link resta `inventario_id` / `rettifica_id`.
* **Il file delle policy d'errore** è rigenerato (la descrizione di `E_MAG_MOVIMENTO_GIA_REGISTRATO`).
* ⏭️ **Resta al DB: UI-M.1-a.** `lista_colonna.csv:865` descrive ancora la colonna «(INVENTARIO_RIGA, RETTIFICA_RIGA,
  …)». È un seed: si cambia dal CSV, nel primo giro DB utile.
  ✅ **Già fatto (verifica DB al merge, 2026-11-08):** le due descrizioni sono corrette dal giro M.2 (`ad13694ffb`);
  la nota è stata scritta su una copia precedente.
* **Nello stesso giro: `autospec` su tutte le patch di repository.** Nato dai mock di `PraticheRepository` del §8.16, è
  esteso a tutta la suite e reso regola ([api.md](../api.md) §Test) con un presidio,
  `apps/core/tests/test_presidio_autospec_repository.py`; la storia e i conti sono nella sua intestazione. Il presidio
  vede anche `patch("…XRepository.metodo")` e `unittest.mock.patch`. Un caso strutturale: il test del cancello degli
  obblighi ripatchava il mock di `AuthRepository.get_fatti_obblighi` già messo da `JwtMockedApiTest`, e con `autospec`
  è `InvalidSpecError`; ora la base espone `mock_fatti_obblighi` e il test lo configura. Aggiornati
  `sicurezza-e-qualita-statica.md` («Perché» di mypy) e `qualita-be-fe-indicatori.md`.
* Provati: la suite Django intera (6.569 test, verde), i test di `magazzino` sul DB vero (97, `ZEROERP_TEST_DB_E2E=1`),
  `core/tests/db/test_obblighi_e_secondo_fattore_db` sul DB vero (14), i test FE di `src/magazzino` (19), ruff verde.
  ⏭️ **Da lanciare da Tid**: `backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py` (allineato, non eseguito).

### 8.20 Dal lotto Z, giro Z.1 (2026-11-08)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-Z.1-a | la regola d'ancora per flusso ha la sua sede DB: `script.vw_flusso_doc_sorgente` (una riga per `flusso_id`; colonne di `script.vw_pratica_doc_sorgente` più `flusso_id`: `pratica_id`, `sorgente_tipo_id`, `sorgente_id`, `sorgente_uid`, `ruolo_link`, `sorgente_descrizione`, `risolto`, `stato_codice_interno`, `stato_codice`, `stato_descrizione`, `fase`, `esito`, `terminale`). Ordine: prima il ROOT, poi risolto, non terminale, il più recente (R-P.1-1, Tid 2026-11-08) | `pratiche/db/pratiche_repository.py:102` (`_doc_sorgente_lateral`) e i due chiamanti `:806` (percorso della pratica, `ps.pratica_id = p.id AND ps.flusso_id = f.id`), `:1518` (coda di lavoro) | il JOIN alla vista per `flusso_id` al posto della LATERAL; la copia BE si ritira (regola del 2). ⚠️ Lo spareggio cambia solo per un flusso senza ROOT: prima vinceva il collegato più recente, ora il più vivo |
| BE-Z.1-b | `E_PRATICA_SORGENTE_TIPO_INVALIDO` ha `obsoleto_dal = 2026-11-08` (R-P.1-2): nessuno lo solleva | `core/services/error_policies_generated.py`, `error_messages_fallback.py` | rigenerare il file delle policy dal CSV; il ripiego BE lo perde se il generatore esclude i codici obsoleti, altrimenti resta (la frase si legge ancora per lo storico) |
| — | `config.sorgenti.categoria` ha due valori, `DOCUMENTO` ed `EVENTO` (`EVENTO_ASSET` passa da `RIGA` a `EVENTO`), NOT NULL | `vendite/db/famiglie_repository.py:335` (filtro `categoria = 'DOCUMENTO'`), `config/sorgenti.py:45-47` | nessuna: il filtro resta giusto. Il commento di `config/sorgenti.py:60` («categoria RIGA») si aggiorna con BE-M.3-a |

### 8.21 Dal lotto Z, giro Z.2 (2026-11-08)

⚠️ Dall'apply un'offerta in bozza con eccezioni attive non si elimina più (`E_DELETE_DOC_CON_RIGHE`), e un preventivo,
un'offerta o una commessa fuori bozza nemmeno con un `DELETE` diretto. Il percorso del BE non si rompe: riceve un
`CONFLITTO_STATO` (409) che prima non poteva arrivare.

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-Z.2-a | la regola «si cancella solo la bozza vuota» sta solo nel DB, per le sette testate di vendita (Tid, 2026-11-08: «perché ripetere la regola»; revoca la scelta del giro T.4, che teneva i pre-check come controllo preventivo) | `ordini_service.elimina_ordine:590`, `ddt_service.elimina_ddt:464`, `resi_service.elimina_reso:572`, `preventivi_service.elimina_preventivo:562` (stato iniziale, righe, pratiche: il terzo è BE-P.1-e), `offerte_service.elimina_offerta:797` (`_STATI_EDITABILI`) | i pre-check di stato, righe e pratiche si ritirano; il service chiama il `DELETE` e lascia passare l'errore del DB (`E_DELETE_DOC_NON_BOZZA`, `E_DELETE_DOC_CON_RIGHE`, `E_DELETE_CONTRATTO_CON_SUCCESSIVI`, `E_SORG_ORIGINE_REFERENZIATA`). Resta il 404 del documento che non c'è. I test Django che asserivano i codici dei pre-check (`E_PREV_STATO_NON_MODIFICABILE`, `E_ORD_STATO_TRANSIZIONE`, `E_DDT_STATO_TRANSIZIONE`, `E_RESO_STATO_TRANSIZIONE` sull'eliminazione) passano ai codici del DB |
| BE-Z.2-b | il testo di `E_DELETE_DOC_CON_RIGHE` è generico: «%s ha ancora del contenuto (righe, eccezioni, attività o documenti collegati): si può eliminare solo una bozza vuota.»; causa e soluzione nominano che cosa svuotare per documento. Un codice solo per tutti (Tid, 2026-11-08) | `core/services/error_messages_fallback.py:375`, `error_policies_generated.py` | rigenerare le policy dal CSV e allineare il ripiego al testo nuovo |
| UI-Z.2-a | la bozza «abbandonata» si elimina se è vuota anche per offerta (nessuna eccezione attiva) e commessa (nessuna attività, nessun documento collegato) | FE: il filtro dell'abbandono bozza sul conteggio delle righe | se il FE offre l'eliminazione dell'offerta o della commessa, la condiziona come per il preventivo, o mostra la frase del DB |

### 8.22 Il §8 chiuso (lotto Z, giro Z.4, 2026-11-08)

Il DB non aggiunge voci: il §8 è l'elenco **chiuso** che il lotto BE/FE porta allo stato del DB. Un difetto DB che il
lotto BE/FE trovasse si raccoglie e si chiude in **un** giro DB alla fine (§7.2 «Lotto BE/FE»).

**Da fare** (il percorso del BE o del FE cambia):

| Voce | In breve |
| --- | --- |
| BE-Z.5-a ✅ | il pull per commessa passa la commessa alle segnalazioni (`p_commessa_id`, §8.23). ✅ Fatto (2026-11-08): `log_pipeline_fase(commessa_id=…)` per nome, `log_error(commessa_id=…)`, `item_failed` passa `item` su ogni riga, anche quella «del giro». Presidi: i tre test unitari e `vendite/tests/db/test_pull_tutte_fallite_scrittura_reale` n. 3, sul DB vero: la riga `E_PULL_COMMESSA` di `fatturazione_lotti_log` porta `commessa_id` (prova anche il binding del nono parametro) |
| BE-Z.1-a ✅ | la regola d'ancora per flusso da `script.vw_flusso_doc_sorgente`; la copia `_doc_sorgente_lateral` si ritira. ✅ Fatto (2026-11-08): `_doc_sorgente_flusso(flusso_col)`, LATERAL con `LIMIT 1` sulla vista (senza, il planner calcola la vista intera: EXPLAIN su dbdev), per percorso e coda. Presidio `pratiche/tests/db/test_link_pratica_sorgente_db` n. 4, ora su un flusso vero (operatore di fixture, flusso assegnato, ROOT ancorato): percorso e coda proiettano il documento solo su quel flusso |
| BE-Z.1-b ✅ | `E_PRATICA_SORGENTE_TIPO_INVALIDO` obsoleto: policy rigenerate, il ripiego (`error_messages_fallback.py:1082`). ✅ Fatto (2026-11-08): il codice è in `CODICI_RITIRATI`; il ripiego resta, come per ogni codice ritirato (lo storico di `dbops.error_log` deve restare leggibile) |
| BE-Z.2-a ✅ | i pre-check di cancellazione dei cinque service si ritirano; resta il 404. ✅ Fatto (2026-11-08): `elimina_ordine`, `elimina_ddt`, `elimina_reso`, `elimina_preventivo` (anche «pratiche collegate», BE-P.1-e), `elimina_offerta` chiamano il `DELETE` e alzano il 404 del dominio sul `DELETE` che non tocca niente (il preventivo non risponde più `noop`). Ritirati con loro i BB rimasti senza consumatori: i tre `_assert_stato_iniziale`, `_STATI_EDITABILI` e `_assert_stato_corrente` dell'offerta, `core.services.documento_modello.e_stato_iniziale` (resta `DocumentoModelloRepository.stato_iniziale`), `PreventiviRepository.list_pratiche` e `PreventivoPraticaRow`. Presidi: i test dei cinque service (il rifiuto del DB passa col suo codice, nessuna lettura prima del `DELETE`, il 404) e `vendite/tests/db/test_elimina_bozza_vuota_db` sul DB vero (preventivo e ordine: fuori bozza, con righe, vuota, inesistente) |
| BE-Z.2-b ✅ | il testo generico di `E_DELETE_DOC_CON_RIGHE` nel ripiego (`error_messages_fallback.py:375`). ✅ Fatto (2026-11-08), con le policy rigenerate |
| UI-Z.2-a ✅ | l'eliminazione della bozza abbandonata di offerta e commessa, condizionata come per il preventivo. ✅ Nessuna azione (verificato dal BE/FE, 2026-11-08): il FE **non** offre quell'eliminazione. `OffertaDrawer` non usa `useDrawerAutosaveBozza` e non ha un abbandono; la commessa non ha un percorso di eliminazione né nel FE né nel BE. Ritirate (Tid, 2026-11-08: «togliere») l'azione `elimina` dello store `vendite/offerte/stores/offerte.js` e la funzione `deleteOfferta` di `offerteApi.js`, senza consumatori; l'endpoint `DELETE` del BE resta (BE-Z.2-a) |
| FE-M.2-1 ✅ | le due chiavi i18n delle colonne nuove della lista dei movimenti (il seed è fatto, R-M.2-1 sotto): `magazzino.movimenti.col_sorgente_id` («Documento sorgente» / «Source document»), `…col_sorgente_dettaglio` («Dettaglio sorgente» / «Source detail»). ⛔ Nello stesso commit del seed, o il controllo i18n è rosso. ✅ Aggiunte dal team DB nel commit del seed, su eccezione al perimetro decisa da Tid (2026-11-08); `check_i18n_keys` pulito |

**Da verificare negli smoke, nessuna azione attesa:** BE-0.1-b (il riferimento del documento d'origine), BE-R.1-a e
BE-D.1-e (le cancellazioni fermate da `E_SORG_ORIGINE_REFERENZIATA`), BE-T.2-c (la lista delle bolle, la riconsegna dal
reso), BE-C.2-b e BE-C.3-b (le colonne tipizzate di commessa), BE-C.3-e (il riferimento del gruppo senza numero).

**Nessuna azione** (verificato dal DB, 2026-11-08): BE-0.1-c, BE-T.2-d; BE-0.2-b (nessun lettore BE o FE di
`dbops.vw_sorgenti_orfane`); BE-T.2-e (`E_DOC_SORGENTE_NON_TROVATA` resta solo nel ripiego BE, nessuna mappa); BE-C.3-d
(il codice è nelle policy rigenerate). Le voci segnate ✅ sono fatte dal BE (righe 9-bis … 9-septies).

**Richiesta del BE al DB dal giro BE di Z.1/Z.2 (2026-11-08), per il giro DB di fine cantiere:** **R-Z.2-1** —
`vendite.vw_preventivi_pratiche` non ha più lettori nel BE: l'unico era `PreventiviRepository.list_pratiche`, ritirato con
il pre-check «pratiche collegate» (BE-P.1-e). Il DB valuta se ritirare la vista o se ha un consumatore suo. ✅ **Risposta (Tid, 2026-11-08):** non si ritira in questo cantiere: è del dominio pratiche (sotto, «`vendite.vw_preventivi_pratiche` senza consumatori nel BE»).

**V-7-bis — il riferimento di un gruppo di consumi, a commessa chiusa** (analisi DB, 2026-11-08, su richiesta di Tid:
«fai subito»). Va al giro DB di fine cantiere. Il limite dichiarato al giro C.4 non è un caso da tollerare, perché il
modello lo ammette. `vendite.fn_riferimento_gruppo_fatturabile` (unico chiamante: `vendite.fn_list_lotto_segnalazioni`,
la scheda Critiche) trova la commessa di un documento senza numero (il consumo, `label_selector` NULL) con
`vendite.fn_commessa_viva_di_sorgente`, che risponde a un'altra domanda («in quale commessa **aperta** il documento si
riusa»). A commessa chiusa o annullata torna la chiave grezza; su un lotto vecchio col documento rientrato in una
commessa nuova dà il codice **sbagliato**. La domanda giusta è «di quale commessa era il gruppo **in quel lotto**». Le
fonti, sulla struttura:

* la vista `vendite.vw_dash_competenza_attivita` lega attività e lotto (`lotto_provenienza_id`, da `lock_batch_id` /
  `emit_batch_id`), ma solo per le attività fatturabili già **consegnate**: una Critica nasce spesso prima, mentre il
  documento fallisce;
* `meta.context.commessa_id` della segnalazione: JSON senza contratto, non è una sede;
* il perimetro `vendite.fatturazione_lotti_gruppi`: lo scrive il BE solo per il giro **mirato**; un lotto di massa non
  ce l'ha. Scartato;
* **la segnalazione stessa**: `fatturazione_lotti_log.gruppo_key` «lo scrive chi solleva»; una colonna `commessa_id`
  scritta allo stesso modo (un parametro in coda a `vendite.fn_log_pipeline_fase`) direbbe la commessa anche prima
  della consegna.

**Proposta DB: la quarta**, col censimento dei chiamanti prima di scriverla (`fn_escludi_documento_da_giro`,
`fn_log_lotto_esito_fatture`, `fn_snapshot_fattura_lotto`, `fn_genera_scadenze_lotto`, `fn_annulla_lotto_da_draft`,
`pipeline_repository` del BE): chi ha la commessa nel momento del fallimento. È un cambio di modello del log: va prima
cercata la decisione esistente (`work-done/brief-db-uscita-documento-dal-giro`, che ha scritto il COMMENT di
`gruppo_key`). Ripiego minimo, sconsigliato: l'ultimo link a qualunque stato (sparisce la chiave grezza, resta il codice
sbagliato su un lotto vecchio). ✅ **Tid, 2026-11-08: la proposta** («ok procedi con proposta»): giro Z.5, §7.2.

**`vendite.vw_preventivi_pratiche` senza consumatori nel BE** (segnalazione del BE, 2026-11-08: l'unico lettore era
`list_pratiche`, il pre-check di `elimina_preventivo` che si ritira con BE-P.1-e). Verificato: nessuna vista o funzione
DB la legge; la leggono due pgTAP (`pratiche/test-sorgente-pratiche-sorgenti-v1`, `rls/test-rls-viste-security-invoker`).
⛔ **Non si ritira in questo cantiere** (Tid, 2026-11-08: «la vista della pratica dipende da altro cantiere»): è un oggetto
del dominio pratiche, che questo cantiere ha solo riscritto sulle colonne tipizzate (giro P.1, `20261108-82`), e due
documenti aperti del cantiere pratiche la citano come base da riusare (`analisi-pratiche-valutazione-stato.md`,
`brief-design-proiezione-stato-dominio.md`). Il ritiro, o il riuso, lo decide il cantiere pratiche
(`gestione-pratiche-come-procedere.md`).

**Le richieste del BE al DB, al giro Z.4:** R-P.1-1 e R-P.1-2 chiuse nel giro Z.1 (R-P.1-2 «anticipata» del giro BE di
M.2 era già nel CSV: il BE l'aveva letta su una copia precedente al commit). **R-M.2-1 resta al DB**: le due righe di
`ui/lista_colonna.csv` per la lista dei movimenti (§8.19). Proposta DB, nella forma di `sorgente_riga`: `sorgente_id`
(«Documento sorgente», la chiave del documento; vuota per un evento d'asset) dopo `sorgente_codice_interno`, e
`sorgente_dettaglio` («Dettaglio sorgente», il prelievo della bolla o il rientro del reso) dopo `sorgente_riga`; gruppo
«Sorgente», `numeric`, allineate a destra, **né filtrabili né ordinabili** come `sorgente_riga`, esportabili. Così il BE
non tocca `MOVIMENTI_SORT_COLUMNS` né i filtri; il FE aggiunge `magazzino.movimenti.col_sorgente_id` e
`…col_sorgente_dettaglio`. Nessun changeSet: è il CSV, col suo loader. ✅ **Via di Tid (2026-11-08, «ok come da
proposta») e fatto:** `ui/lista_colonna.csv` id 1166 (`sorgente_id`, ordine 125) e 1167 (`sorgente_dettaglio`, ordine
135), e ⚠️ le due righe del preset base `movimenti_default` in `ui/lista_preset_colonna.csv` (nascoste, ordine 125 e
135): senza, il risolutore le metteva in fondo, perché l'ordine e la visibilità li dà il preset (trovato in prova).
I due mirror sono `runOnChange`, il resync delle identità è `runAlways`; la lista non ha `vista_sql`, quindi il trigger
di `campo_sorgente` non verifica niente: le due colonne le proietta `_MOVIMENTI_SELECT` del BE. Prova (2026-11-08, in
transazione annullata, scratch e dbdev): l'upsert delle quattro righe passa, `ui.fn_resolve_lista_config` dà le due
colonne nascoste al loro posto; prima/dopo sui 37 pgTAP di `ui/` e di chi legge liste e preset, 524 ok in tutte e due le
corse, nessuna differenza. ⛔ **Le due chiavi i18n entrano nello stesso commit del seed:** `scripts/check_i18n_keys.py`
(pre-commit sui CSV di `80_data`, e la CI del frontend) è rosso finché `it.json` ed `en.json` non hanno
`magazzino.movimenti.col_sorgente_id` («Documento sorgente» / «Source document») e `…col_sorgente_dettaglio`
(«Dettaglio sorgente» / «Source detail»), accanto a `col_sorgente_riga` (riga 5213). Il FE non è nel perimetro DB: le
aggiunge il FE (FE-M.2-1). ✅ Aggiunte dal team DB nello stesso commit, su eccezione al perimetro decisa da Tid (2026-11-08).

### 8.23 Dal lotto Z, giro Z.5 (2026-11-08)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-Z.5-a ✅ | `vendite.fn_log_pipeline_fase` ha il nono parametro `p_commessa_id` (in coda, DEFAULT NULL), scritto in `fatturazione_lotti_log.commessa_id`: la commessa di cui parla la segnalazione, per il riferimento della scheda Critiche (V-7-bis) | `pipeline_repository.log_pipeline_fase:1337` (chiamata per nome), `pipeline_error_logger.log_error`, `pipeline_step_executor.item_failed:154` (il pull per commessa: `context["commessa_id"] = item`) | `log_pipeline_fase` e `log_error` prendono `commessa_id` e lo passano per nome; `item_failed` passa `item`, la commessa da cui ricava i documenti. Gli altri chiamanti non cambiano. ✅ Fatto (2026-11-08, §8.22) |

### 8.24 Dal giro DB di fine cantiere (2026-11-08)

| # | Che cosa cambia | Percorso | Che cosa fa il BE/FE |
| --- | --- | --- | --- |
| BE-Z.6-a | `E_DDT_STATO_TRANSIZIONE`, `E_RESO_STATO_TRANSIZIONE`, `E_PREV_STATO_NON_MODIFICABILE` hanno `obsoleto_dal = 2026-11-08` (nessuno li solleva più, dopo BE-Z.2-a) | `core/services/error_policies_generated.py`, `error_messages_fallback.py`; `core/tests/services/test_error_policies_classi.py:225-231` (chiama `E_PREV_STATO_NON_MODIFICABILE` «il gemello vivo»); i docstring di `vendite/tests/services/test_ddt_service.py` e `test_resi_service.py` | rigenerare le policy dopo l'apply (il codice entra fra i ritirati, il ripiego resta per lo storico); allineare il test e i docstring |

---

## Appendice — Il censimento di dettaglio (2026-11-06)

> Sola lettura: struttura da `zeroerp_ruoli` (costruito da zero, senza dati) e dal catalogo, corpi dalla doc
> auto-generata, significato dai manuali, grep su BE, FE e pgTAP. I numeri di dati sono quelli di dbdev del §3, fatti
> datati. [F] = fatto verificato col riferimento; il resto è dichiarato ipotesi o proposta. Quattro schede, una per
> famiglia. Le decisioni che ne escono sono raccolte al §6.3.

### Censimento — documenti di vendita (testate, righe, colonne parallele G8)

> **Per:** `brief-db-sorgente-documento-e-riga` §7.1, Appendice. **Chi:** team DB, 2026-11-06, sola lettura.
> **Fonti:** struttura dal DB scratch (`zeroerp_ruoli`, come `zeroerp_owner`: **vuoto di dati**, quindi qui non ci sono
> conteggi nuovi; i numeri citati sono quelli del brief, dbdev 2026-11-06, fatti datati). Corpi delle funzioni da
> `pg_get_functiondef` (identici alla doc auto-generata `docs/it/dbzero/vendite/funzioni/*.md`, citata per riga).
> Significato dai manuali `docs/it/dbzero/vendite/manual/`. BE `backend/apps`, FE `frontend/src`, pgTAP `db/pgtap`.
> **Legenda:** **[F]** fatto verificato (con file:riga o query); **[I]** ipotesi/deduzione da verificare.
>
> **Stato dei changeSet citati:** `20261105-01…-14` e `20261106-01…-03` risultano **EXECUTED** nel
> `databasechangelog` dello scratch [F]. I `20261105-15…-19` (lotto B) **non esistono nell'albero** [F]
> (`find db/changelog/migrations_v2 -name '2026110[56]*'`): sono parcheggiati fuori repo (brief obsoleto-dal §7.2). Quindi
> **oggi nessun verbo DB scrive la sorgente su una riga di vendita** [F] (vedi §0.2).

---

#### 0. Quadro d'insieme

##### 0.1 Colonne di oggi [F] (`information_schema.columns` + `col_description`)

| Tabella | `sorgente_tipo_id` | `sorgente_uid` | `sorgente_riga` | `sorgente_id` | Parallele | Grammatica |
| --- | --- | --- | --- | --- | --- | --- |
| `vendite.ordini` | bigint NULL | uuid NULL | — | — | `documento_origine_tipo varchar` (FK `config.sorgenti.codice_interno`) + `documento_origine_id bigint` | G1 «import» + G8 |
| `vendite.ddt` | bigint NULL | uuid NULL | — | — | — | G1 «padre per uid» |
| `vendite.resi` | bigint **NOT NULL** | uuid **NOT NULL** | — | — | — | G1 «padre per uid» |
| `vendite.contratti` | bigint NULL | uuid NULL | — | — | `offerta_id bigint` FK `offerte_commerciali(id)` | G1 + G8 (doppia scrittura) |
| `vendite.fatture` | bigint NULL | uuid NULL | — | — | — | G1 «import» |
| `vendite.preventivi_righe` | bigint NULL | uuid NULL | bigint NULL | — | — | G2 (lotto A) |
| `vendite.ordini_righe` | bigint NULL | uuid NULL | bigint NULL **DEFAULT 0** | — | `preventivo_riga_id` FK `preventivi_righe(id)` | G2 + G8 non censita |
| `vendite.ddt_righe` | bigint NULL | uuid NULL | bigint NULL | — | `ordini_righe_fulfillment` (tabella) | G2 + G8 |
| `vendite.contratti_righe` | bigint NULL | uuid NULL | bigint NULL | — | — | G2 (lotto A) |
| `vendite.fatture_righe` | bigint NULL | uuid NULL | bigint NULL **DEFAULT 0** | — | `riga_rettificata_id`, `riga_capofila_id` (FK fisiche) | G5 (residuo «import») |

Nessuna tabella del perimetro ha `sorgente_id` [F]. Nessun CHECK sulle colonne `sorgente_*` in tutto il perimetro
(né di forma né di esclusività) [F] (`pg_constraint`, solo FK). L'unico CHECK di provenienza è
`chk_ordini_documento_origine_copres` (tipo e id co-presenti) [F].

##### 0.2 Chi scrive oggi (tutto il perimetro) [F]

Ricerca di `INSERT … (… sorgente_*/documento_origine_*/offerta_id …)` e `UPDATE … SET` su tutti i corpi (`pg_proc`,
`BEGIN ATOMIC` compresi) e sul BE:

| Scrittore | Tabella | Valore scritto |
| --- | --- | --- |
| `vendite.fn_genera_ddt_da_ordine` (doc `fn_genera_ddt_da_ordine.md:108`) | `ddt` | `ORDINE_VENDITA` + **`ordini.uid`** |
| `vendite.fn_genera_ddt_riconsegna` (`fn_genera_ddt_riconsegna.md:141`, `:150`) | `ddt` | con ordine: `ORDINE_VENDITA` + `ordini.uid`; senza: `RESO_VENDITA` + **`resi.uid`** |
| `vendite.fn_push_offerta_a_contratto` (`fn_push_offerta_a_contratto.md:241`) | `contratti` | `OFFERTA_COMMERCIALE` + `offerte_commerciali.uid` **e** `offerta_id` = id |
| `vendite.fn_push_preventivo_a_ordine` (`fn_push_preventivo_a_ordine.md:164`) | `ordini` | `documento_origine_tipo='PREVENTIVO'` + `documento_origine_id` = **`preventivi.id`** |
| `vendite.fn_genera_ordine_da_offerta` (`fn_genera_ordine_da_offerta.md:166`) | `ordini` | `'OFFERTA_COMMERCIALE'` + `offerte_commerciali.id` |
| `vendite.fn_push_preventivo_a_ordine` (`:209`) | `ordini_righe` | `preventivo_riga_id` (non la sorgente) |
| `vendite.fn_genera_ddt_da_ordine` (`:237`), `fn_genera_ddt_riconsegna` | `ordini_righe_fulfillment` | `(ordine_riga_id, ddt_riga_id, qta_evasa)` |
| BE `vendite/db/resi_repository.py:646-647` ← `services/resi_service.py:534-535` | `resi` | `DDT_VENDITA` + `str(ddt["uid"])` |
| BE `vendite/db/pipeline_repository.py:3503` | `fatture_righe` | **`NULL, NULL, NULL` esplicito** (la riga aggrega n attività) |
| BE `vendite/db/pipeline_repository.py:2014` | `fatture_righe` | la «parte» IVA **copia** `sorgente_*` dalla capofila |
| `dbops.fn_pgtap_crea_reso` (builder pgTAP) | `resi` | `DDT_VENDITA` + ddt uid |

**Nessuno scrive** `ordini.sorgente_*`, `fatture.sorgente_*`, la sorgente di `preventivi_righe`, `ordini_righe`,
`ddt_righe`, `contratti_righe` [F] (`vendite.fn_get_or_create_fattura_header` è l'unico INSERT di `fatture` e non
le nomina, `fn_get_or_create_fattura_header.md:206`). Gli INSERT di `ordini_righe` (`fn_push_preventivo_a_ordine`,
`fn_genera_ordine_da_offerta`, `dbops.fn_pgtap_crea_ordine_con_righe`, BE) non nominano `sorgente_riga`: prendono il
**DEFAULT 0** con `sorgente_tipo_id NULL` [F]. Il brief (§3.2) cita 8 righe `COMMESSA` su `fatture_righe` «solo dal
builder `dbops.fn_pgtap_fattura_attivita`»: il corpo attuale del builder **non scrive** `sorgente_*` [F]; le 8 righe
di dbdev sono residui di una versione precedente o di un altro scrittore [I].

##### 0.3 Guard montati [F] (`pg_trigger`)

| Tabella | `trgfn_guard_sorgente_polimorfa_tipizzata` | `trgfn_child_requires_active_parent` (config.sorgenti.attivo) | Altri sulla sorgente |
| --- | --- | --- | --- |
| `ordini` | **no** | sì | lock fuori bozza su `sorgente_tipo_id, sorgente_uid, documento_origine_tipo, documento_origine_id` (`E_DOC_SORGENTE_FUORI_BOZZA`); `trg_ordini_z90_sync_canali_ins_upd` (UPDATE OF sorgente_*) |
| `ddt` | **no** | sì | lock fuori bozza su `sorgente_*`; `trg_ddt_z10_guard_cliente_sorgente_ins_upd`; `trg_ddt_z90_sync_canali_ins_upd` (UPDATE OF sorgente_*); `trgfn_ddt_normalize` |
| `resi` | **no** | sì | lock fuori bozza su `sorgente_*`; `trgfn_resi_normalize`, `_guard_cliente_ddt`, `_guard_ddt_consegnato`, `_default_magazzino` |
| `contratti` | **no** | sì | lock fuori bozza su `offerta_id, sorgente_tipo_id, sorgente_uid` |
| `fatture` | **no** | sì | — |
| `preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe` | **sì** (`…_a10_guard_sorgente_ins_upd`, da `20261105-14`) | sì | `trgfn_righe_guard_articolo_ammesso` legge `sorgente_tipo_id` (tgargs) come esenzione |
| `fatture_righe` | **no** | sì | — |

Quindi la **testata non ha nessun controllo d'esistenza** della sorgente; lo fanno solo i trigger di dominio di
`ddt`/`resi` che la rileggono (normalize e guard cliente), per i tipi che conoscono [F].

##### 0.4 Il presidio degli orfani vede solo le righe [F]

`dbops.fn_sorgenti_orfane_perimetro` (`fn_sorgenti_orfane_perimetro.md:48`) prende le tabelle con FK a
`config.sorgenti` **e** colonne `sorgente_riga` + `sorgente_uid` **e** il guard `_tipizzata` montato. Risultato sullo
scratch: dal perimetro vendite entrano solo `preventivi_righe`, `contratti_righe`, `ordini_righe`, `ddt_righe`.
**Fuori**: tutte e cinque le testate e `fatture_righe` (ha le tre colonne ma non il guard). Precisazione al §3.3 del
brief: non basta «entrambe le colonne», serve anche il guard.

---

#### 1. Testate

##### 1.1 `vendite.ordini`

**1. Colonne e significato.** `sorgente_tipo_id` «FK → config.sorgenti.id (tipo sorgente import)», `sorgente_uid`
«Origine import (uid)» [F commento]. Manuale `ordini.md:29, :146, :192, :198, :250-255`: idempotenza d'import da CRM,
«distinta da `documento_origine_*`». Provenienza vera in `documento_origine_tipo` + `documento_origine_id` (G8).
⚠️ Due **documentazioni stantie** [F]: il commento di `documento_origine_id` dice «NESSUNA UNIQUE (più ordini da una
stessa origine)», ma esiste `uq_ordini_v_documento_origine_offerta`; il manuale `ordini.md:241` dice «varchar + CHECK
vocabolario chiuso PREVENTIVO / OFFERTA», ma dal `20261019-87` è una FK a `config.sorgenti(codice_interno)`.

**2. Scrittori.** `sorgente_*`: **nessuno** [F]. `documento_origine_*`: `fn_push_preventivo_a_ordine` (`PREVENTIVO` +
**id** del preventivo, che in `config.sorgenti` ha chiave **uid**) e `fn_genera_ordine_da_offerta`
(`OFFERTA_COMMERCIALE` + **id** dell'offerta, chiave **uid** a catalogo) [F]. Il BE non scrive: rilegge
(`ordini_service.py:542`, `:575` restituisce `"documento_origine": {"tipo", "id"}` al FE).

**3. Lettori.**

* `sorgente_*` — **`vendite.trgfn_documenti_sync_canali`** ramo ordini (`trgfn_documenti_sync_canali.md:121`): se
  `sorgente_tipo_id` è `PREVENTIVO`, segna il canale del preventivo **CONSUMATO** con `NEW.sorgente_uid::text`. Cioè:
  il codice legge `ordini.sorgente_*` come **provenienza**, non come import. Il ramo è **morto** perché il push scrive
  `documento_origine_*` [F: nessuno scrive `ordini.sorgente_*`; nessun verbo di push chiama
  `fn_set_documento_canale_stato`]. ⚠️ Portare la provenienza in `sorgente_*` lo **accende**: il canale PREVENTIVO
  passerà a CONSUMATO alla generazione dell'ordine. È un cambio di comportamento da decidere [I: probabilmente quello
  voluto in origine]. Le legge anche il lock fuori bozza (tgargs); `vw_ordini_lista` non le espone [F].
* `documento_origine_*` — `vw_ordini_lista` (`:86`, join per **id** su preventivi e offerte, `documento_origine_codice`
  per tipo con `CASE`), `vendite.fn_documento_lineage_archi` (`:103`, per id), `vendite.fn_documento_legami`
  (`:103`), `vendite.fn_offerta_documenti_vivi` (`:27`), `script.fn_check_preventivo_annullabile` (`:88`),
  `vw_dash_fatturazione_offerte`, BE `ordini_repository.py:432-433` (`get_ordine_by_documento_origine(tipo, id)`),
  `ordini_repository.py:286` (etichetta per la stampa), `ordine_document_context_builder.py:213-215`; FE
  `OrdiniSearchTable.vue:10` (colonna `documento_origine_codice` via catalogo `ui.lista_colonna` riga 125).
* pgTAP che costruiscono/asseriscono `documento_origine_*`: `vendite/test-fn-push-preventivo-a-ordine-v1.sql`,
  `test-annullo-documento-con-legami-v1.sql`, `test-fattura-origini-v1.sql`, `test-ordini-modello-ext.sql`,
  `test-testata-dopo-emissione-v1.sql`, `test-grammatica-origine-destinazione-sorgenti-v1.sql`,
  `test-documento-lineage-seminata-v1.sql`, `offerte_commerciali/test_fn_push_offerta_a_contratto.sql`,
  `offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1.sql`, `script/test-fn-available-actions-offerta-v1.sql`
  (10 file). BE test: `test_origine_ordine_sorgente_db.py`, `test_genera_ordine_da_offerta_db.py`,
  `test_ordine_document_context_builder.py`.

**4. Vincoli e indici.**

| Indice / vincolo | Classificazione | Motivo |
| --- | --- | --- |
| `uq_ordini_v_sorgente_fk (sorgente_tipo_id, sorgente_uid) WHERE tipo NOT NULL` | **idempotenza import** | commento «Idempotenza import»; nessuno scrive le colonne; con §4 si ritira |
| `uq_ordini_v_documento_origine_offerta (documento_origine_tipo, documento_origine_id) WHERE tipo='OFFERTA_COMMERCIALE' AND NOT is_abortito_snapshot` | **regola di dominio** | «un'offerta genera al più un ordine vivo» (D-3/D-6 annullo); lettore `fn_offerta_documenti_vivi`; nome mappato nel BE `ordini_service.py:88` |
| `ix_ordini_documento_origine` (non unico) | ricerca | lineage seminata ramo A |
| `chk_ordini_documento_origine_copres` | forma | co-presenza; da sostituire col CHECK di forma del modello |
| `fk_ordini_documento_origine_tipo_sorgenti` (codice, `ON DELETE RESTRICT`) | FK | sparisce con la confluenza |

⚠️ **Trasferire `uq_…_offerta` sulla chiave nuova** [I tecnico]: il predicato oggi nomina il **codice**
(`'OFFERTA_COMMERCIALE'`); su `sorgente_tipo_id` servirebbe l'**id** letterale (14, esplicito nel seed
`config/sorgenti.csv:10`) in un indice parziale, oppure una via diversa (indice parziale per id con presidio, o
guard). Da decidere nel lotto.

**5. Guard.** Nessun guard di esistenza né su `sorgente_*` né su `documento_origine_*` [F]: il test BE
`test_origine_ordine_sorgente_db.py` lo dice esplicitamente («l'id dell'offerta è polimorfo (nessuna FK), quindi non
serve un'offerta vera»). Un `documento_origine_id` inesistente passa.

**6. S-9 (bersaglio `ORDINE_VENDITA`, e `ORDINE_VENDITA_RIGA` per le righe).** DELETE ammesso solo in DRAFT
(`trg_ordini_a10_guard_delete_solo_bozza_dlt`, `trgfn_doc_guard_delete_solo_bozza.md:44`) [F]; «zero righe» lo
controlla **solo il BE** (`ordini_service.elimina_ordine`, abbandono bozza) [F]. Figli fisici: righe, indirizzi, note
`ON DELETE CASCADE`; `shop.ricevute` NO ACTION. Figli **polimorfi** che possono già esistere su un ordine in bozza:

* `vendite.documenti_fatturazione_canali` — il canale ORDINE lo apre `trg_ordini_z90_sync_canali_ins_upd` **all'INSERT**
  [F]; nessun trigger lo toglie al DELETE [F] → la bozza abbandonata lascia un orfano. È il meccanismo coerente con i
  5 orfani ORDINE del brief §3.2 [I forte];
* `pratiche.pratiche_sorgenti` — `fn_push_preventivo_a_ordine` aggancia l'ordine nuovo alla pratica (INSERT in
  `pratiche_sorgenti`) [F]; il DELETE non lo stacca [F] → orfano possibile [I];
* `documenti.documenti_generati` (stampa), `vendite.commesse_sorgenti`/`commesse_attivita` (dopo il push) — non in
  bozza, di norma [I].

Nessun trigger AFTER DELETE su nessuna testata del perimetro [F]: oggi **ai figli polimorfi non succede niente**.
L'unico «lato in uscita» esistente è `vendite.trgfn_doc_guard_chiusura_sorgente` (su `ordini`, `ddt`, `contratti`),
che però guarda l'**annullo**, non la cancellazione, e solo i figli in `commesse_attivita` (via
`script.fn_check_sorgente_chiudibile`).

**7. S-8.**

* `documento_origine_*` → **può confluire** in `sorgente_*`: è provenienza e resta sull'ordine annullato (commento
  della colonna). Conversione: PREVENTIVO e OFFERTA hanno chiave `uid` → `sorgente_uid` = uid del documento (oggi c'è
  l'id: S-5 al contrario, va convertito *verso* l'uid). `sorgente_riga` NULL (documento intero). Ricadute: la
  regola `uq_…_offerta` (§4 sopra), l'FK per codice, il BE che cerca per `(tipo, id)` e il contratto di risposta
  `documento_origine {tipo, id}`.
* `sorgente_*` «import» → si svuota (nessun dato da nessuno scrittore) e cambia significato; indice da ritirare.

**8. Lotto e note.** Famiglia «testate di vendita», **dopo** il lotto righe. Aggiungere `sorgente_id bigint` (e
`sorgente_riga` se la testata deve poter dire la riga — non serve: le testate nascono da un documento intero [I]).
Allungare i tgargs del lock fuori bozza con le colonne nuove (`sorgente_id`; vedi memoria «UPDATE OF»), e
`trg_ordini_z90_sync_canali_ins_upd` `UPDATE OF`.

##### 1.2 `vendite.ddt`

**1. Colonne.** Commenti «tipo sorgente import» / «Origine import (uid)» [F] — **sbagliati**: il manuale `ddt.md:18,
:62, :73, :82` dice documento padre (`ORDINE_VENDITA` + `ordini.uid`), lookup DDT-per-ordine. G1 «padre per uid» con
un tipo a chiave `id`.

**2. Scrittori.** `fn_genera_ddt_da_ordine` (ORDINE_VENDITA + ordini.uid), `fn_genera_ddt_riconsegna` (ORDINE_VENDITA +
ordini.uid, oppure **RESO_VENDITA + resi.uid**) [F]. Il BE non la scrive (`CREATE_KEYS_DDT` in `ddt_service.py:148` non
la contiene) [F]. ⚠️ **Incoerenza testata/righe nella riconsegna** [F+I]: con ordine, la testata dice ORDINE_VENDITA
mentre le righe — col lotto B parcheggiato — direbbero `RESO_VENDITA_RIGA`. Testata e righe punterebbero a due
documenti diversi. Va deciso qual è la provenienza della bolla di riconsegna (il reso, e l'ordine resta nel
fulfillment? [I proposta]).

**3. Lettori** (tutti per **uid**, `o.uid = d.sorgente_uid`, filtrati sul codice `ORDINE_VENDITA` o `RESO_VENDITA`) [F]:
`vendite.trgfn_ddt_normalize` (`:70`, eredita BA/utility dall'ordine), `vendite.fn_ddt_vincoli_cliente` (`:61`, `:67`)
→ `trgfn_ddt_guard_cliente_sorgente` (confronta anche NEW/OLD di `sorgente_uid`), `vendite.fn_ddt_trigger_ordine_testata`
(`:21`, `BEGIN ATOMIC`, parametro `uuid`) ← `script.fn_check_ddt_emittibile` (`:247`), `script.fn_check_ordine_annullabile`
(`:72`), `script.fn_available_actions_ddt` (`non_editable_fields`), `script.fn_check_ddt_riga_correggi_qta_evasa`,
`vendite.fn_ddt_push_diagnosi`, `vendite.fn_list_ddt_da_pushare` (`:106`, `:164` espone `ordine_sorgente_uid` nel
payload del push), `vendite.fn_documento_lineage_archi` (`:217`), `vendite.vw_ddt_lista` (`:94`, espone
`sorgente_uid`, `ordine_origine_id`, `ordine_origine_numero`), `vendite.trgfn_documenti_sync_canali` (`:165`, consuma il
canale ORDINE con `NEW.sorgente_uid::text`, cioè l'uid). BE: `ddt_repository.py:72` (filtro su
`ordine_origine_numero`). FE: `DdtSearchTable.vue:9` (colonna `ordine_origine_numero`). pgTAP che costruiscono o
asseriscono `ddt.sorgente_uid`: `test-fn-genera-ddt-da-ordine-v1`, `test-fn-ddt-trigger-ordine-testata-v1`,
`test-documento-lineage-v1`, `test-documento-lineage-seminata-v1`, `test-documenti-canali-sync-v1`,
`test-ddt-da-ordine-emittente-prima-dei-lettori-v1`, `test-esecutivi-ba-coppia-v1`, `test-testata-dopo-emissione-rdb-v1`,
`test-fatturazione-immediata-simmetria-sorgenti-v1`, `script/test-capability-motivi-e-nessuna-azione-v1`,
`script/test-trgfn-default-emittente-fiscale-v1`, `dbops/test-fn-pgtap-crea-ddt-da-ordine-v1`,
`dbops/test-fn-pgtap-crea-ddt-senza-ordine-v1`, `magazzino/test-ddt-trasferimento-v1` (14 file, insieme ai resi sotto).

**4. Vincoli.** `ix_ddt_v_sorgente (tipo, uid) WHERE tipo NOT NULL`, **non unico** dal `20260709-01` → ricerca, non una
regola [F]. Nessun CHECK.

**5. Guard.** Nessun guard polimorfo; l'esistenza la verificano di fatto `trgfn_ddt_guard_cliente_sorgente`
(`E_DOC_SORGENTE_NON_TROVATA`, solo per ORDINE_VENDITA e RESO_VENDITA) [F].

**6. S-9 (bersaglio `DDT_VENDITA`, `DDT_VENDITA_RIGA`, `DDT_VENDITA_PRELIEVO`).** DELETE solo DRAFT (trigger DB) e
«zero righe» solo nel BE (`ddt_service.elimina_ddt`) [F]. `ordini_righe_fulfillment.ddt_riga_id` e `resi_righe.*`
sono `ON DELETE RESTRICT`/NO ACTION, `trgfn_dlt_block_ordrig_ddtrig` blocca la riga con legami [F]. Figli polimorfi:
canale DDT aperto all'INSERT da `sync_canali` e mai tolto → orfano alla cancellazione della bozza (16 orfani DDT nel
brief) [F meccanismo, I attribuzione]; `vendite.resi` (DDT_VENDITA per uid) nasce solo su DDT CONSEGNATO
(`trgfn_resi_guard_ddt_consegnato`), quindi non su una bozza [F]; `magazzino.movimenti` solo dopo l'emissione [I].

**7. S-8.** Nessuna colonna parallela di testata; il legame testata↔testata coi figli è anche ricostruibile dal
fulfillment (manuale `ddt.md:18`).

**8. Lotto.** Testate di vendita. Conversione S-5: `sorgente_id` = `ordini.id` (o `resi.id`), `sorgente_uid` a NULL.
Riscrivere tutti i lettori sopra (sono **13 funzioni/viste** che fanno `uid = sorgente_uid`), il payload del push
(`ordine_sorgente_uid`), `sync_canali` (canali G4, uid: S-5 dice di convertire anche quelli), tgargs del lock e
`UPDATE OF` del trigger canali.

##### 1.3 `vendite.resi`

**1. Colonne.** `sorgente_tipo_id` NOT NULL «FK → config.sorgenti.id (DDT_VENDITA)», `sorgente_uid` NOT NULL «UID del
DDT di provenienza (vendite.ddt.uid)» [F]. Manuale `resi.md:27-28`: «l'unica sorgente è DDT_VENDITA, risolta per uid».
G1 «padre per uid», con DDT a chiave `id`. È l'**unica** tabella del perimetro con la sorgente obbligatoria [F].

**2. Scrittori.** BE `resi_service.py:534-535` → `resi_repository.create_reso` (`:646-647`), con l'uid del DDT;
`dbops.fn_pgtap_crea_reso` [F]. Nessun verbo DB.

**3. Lettori** (tutti per uid): `trgfn_resi_normalize` (`:67`), `trgfn_resi_guard_ddt_consegnato` (`:41`),
`trgfn_resi_guard_cliente_ddt` (`:50`), `trgfn_resi_default_magazzino` (`:30`), `fn_conferma_reso` (`:107`, `FOR
UPDATE` sul DDT), `fn_annulla_reso` (`:76`), `fn_posta_reso`, `fn_genera_ddt_riconsegna` (`LEFT JOIN vendite.ddt d ON
d.uid = r.sorgente_uid`, col commento «nulla impone che il tipo sia DDT_VENDITA»), `fn_ddt_vincoli_cliente`,
`fn_documento_lineage_archi` (`:229`), `script.fn_available_actions_reso`, `vw_resi_lista` (`:65`, `ddt_origine_id`,
`ddt_origine_numero`). BE `resi_repository.py:333` (`get_stato_e_ddt_origine`, `d.uid = r.sorgente_uid`). FE
`ResoDrawer.vue:353` (`ddt_origine_id`), `ResoForm.vue:92` (`ddt_origine_numero`). pgTAP:
`test-resi-motore-v1`, `test-resi-righe-guard-origine-coerente-v1`, `magazzino/test-reso-carico-v1`,
`dbops/test-fn-pgtap-crea-reso-v1`, più quelli della lineage.

**4. Vincoli.** `ix_resi_sorgente (tipo, uid)` non unico, senza predicato [F]; `NOT NULL` su entrambe. Nessuna
unicità: più resi per lo stesso DDT ammessi (corretto, regola di dominio assente).

**5. Guard.** Nessun guard polimorfo; i trigger di dominio non verificano che il **tipo** sia DDT_VENDITA quando
leggono (filtrano solo l'uid in alcuni punti) [F per `fn_genera_ddt_riconsegna`].

**6. S-9 (bersaglio `RESO_VENDITA`, `RESO_VENDITA_RIGA`, `RESO_VENDITA_RIENTRO`).** ⚠️ **Nessun guard DB di
cancellazione sulla testata** [F]: «DRAFT e 0 righe» è solo nel BE (`resi_service.elimina_reso`, `resi_repository.py:678`).
Il DELETE di un reso **senza righe** passa da DB in qualunque stato (le righe hanno il lock fuori bozza, che scatta
solo se ci sono righe da cancellare in cascata) [I dedotto dai trigger]. Contro S-9 («dentro le regole DB»). Figli
polimorfi: la bolla di riconsegna (`RESO_VENDITA` + uid) e i movimenti di rientro nascono solo dopo la conferma [I].

**7. S-8.** Nessuna parallela di testata (sulle righe: `resi_righe.ddt_riga_id`, `ordine_riga_id` FK fisiche, fuori dal
mio perimetro).

**8. Lotto.** Testate. Conversione: `sorgente_id` = `ddt.id`; il NOT NULL va spostato su un CHECK «esattamente una
chiave» (le due colonne diventano alternative). BE: `create_reso` passa l'uid → col BB «scrive» del lotto 0 può
continuare a passarlo; `get_stato_e_ddt_origine` va riscritto. Aggiungere un guard DB di cancellazione (S-9).

##### 1.4 `vendite.contratti`

**1. Colonne.** `sorgente_tipo_id` «tipo del documento sorgente del push (es. OFFERTA_COMMERCIALE). NULL per contratti
creati direttamente», `sorgente_uid` «UUID uid del documento sorgente del push (es. offerta.uid)», `offerta_id` «FK a
offerte_commerciali … UNIQUE garantisce idempotenza pattern A» [F commenti]. **Già provenienza**, corretta col
catalogo (OFFERTA ha chiave uid): è l'unica testata G1 che è già sul modello, a parte la mancanza di `sorgente_id`.

**2. Scrittori.** Solo `fn_push_offerta_a_contratto` (`:241`): scrive **due volte** lo stesso fatto [F].

**3. Lettori.** `sorgente_*`: nessun lettore DB trovato oltre al lock fuori bozza [F]. `offerta_id`:
`fn_offerta_documenti_vivi` (`:21`), `fn_documento_legami` (`:213`), `fn_documento_lineage_archi` (`:128`),
`vw_dash_fatturazione_offerte` (`:52`), BE `offerte_repository.py:228` (`c.offerta_id = o.id AND NOT
c.is_abortito_snapshot`). Il BE restituisce `OffertaPushResult.sorgente_uid` = **uid del contratto**
(`offerte_service.py:974`), non della sorgente: nome fuorviante nel contratto API (FE `offerteApi.js:119`,
`stores/offerte.js:175`) [F]. pgTAP su `offerta_id` dei contratti: 25 file (elenco in coda, §5).

**4. Vincoli.** `uq_contratti_offerta_id (offerta_id) WHERE offerta_id NOT NULL AND NOT is_abortito_snapshot` =
**regola di dominio** («un'offerta genera al più UN contratto vivo», D-3/D-6) [F]. `fk_contratti_offerta` NO ACTION.
Nessun indice su `sorgente_*`.

**5. Guard.** Nessuno sulla sorgente.

**6. S-9 (bersaglio `CONTRATTO`, `CONTRATTO_RIGA`).** ⚠️ **Nessun guard DB di cancellazione sulla testata**, nessun
metodo BE di cancellazione [F]; `zeroerp_app` ha il privilegio DELETE [F]. Le righe hanno il lock fuori bozza in
cascata; `contratti_utilities` RESTRICT; `attivita_fatturabili`, `commesse_attivita`, `fatture_atti` NO ACTION. Figli
polimorfi: canale DIRETTO aperto all'INSERT (`sync_canali` ramo contratti) e mai tolto (14 orfani CONTRATTO nel
brief) [F meccanismo]. Ma senza un percorso BE di DELETE da dove vengono? [I: pgTAP/fixture o cancellazioni dirette
su dbdev].

**7. S-8 — `offerta_id`.** Può confluire [I]: è provenienza (il contratto annullato la conserva). Ma porta **una cosa
che il guard polimorfo non dà**: la FK fisica impedisce di cancellare un'offerta che ha un contratto. Col modello
quella protezione deve venire dal lato «in uscita» del lotto 0 (S-9), altrimenti si perde. La regola
`uq_contratti_offerta_id` si trasferisce su `(sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL AND NOT
is_abortito_snapshot` (oggi la sola sorgente del contratto è l'offerta; se domani ce ne fossero altre, ricade il
problema del predicato per id del §1.1).

**8. Lotto.** Testate. Aggiungere `sorgente_id`; ritirare `offerta_id` (con FK, indice, tgargs del lock) dopo aver
riscritto i 4 lettori DB e quello BE.

##### 1.5 `vendite.fatture`

**1. Colonne.** «FK → config.sorgenti (ex source_tipo testuale)», «Origine import (uid)» [F]. Manuale `fatture.md:34,
:115-118, :142-146, :155`: idempotenza d'import da sistemi esterni.

**2. Scrittori.** **Nessuno** [F].

**3. Lettori.** Solo `vw_fatture_lista` (`:76`, espone `sorgente_tipo_id`, `sorgente_codice_interno`, `sorgente_uid`)
[F]. Nessun BE/FE specifico trovato.

**4. Vincoli.** `uq_fatture_v_sorgente_fk (tipo, uid) WHERE tipo NOT NULL` = **idempotenza import** [F commento].

**5. Guard.** Nessuno.

**6. S-9 (bersaglio `FATTURA`, `FATTURA_RIGA`).** DELETE ammesso solo se `numero IS NULL`
(`trg_fatture_a05_guard_numero_fiscale_upd_dlt … WHEN (old.numero IS NOT NULL)`, `trgfn_fatture_guard_numero_fiscale.md:32`)
[F]; molti figli fisici NO ACTION (pagamenti, SDI, fondi, lotti) che di fatto proteggono. Figli polimorfi:
`fatture_stampa_coda` (FK fisica CASCADE + sorgente G7), `documenti_generati` (FATTURA per id) [F dal brief e da
`pg_constraint`].

**7. S-8.** Nessuna parallela. **Che cosa sarebbe la provenienza di una fattura?** [I] La fattura aggrega n attività
di n commesse: una provenienza unica di testata in generale **non esiste** (la tracciabilità passa da
`attivita_fatturabili.fattura_riga_id`, commento in `pipeline_repository.py:3500-3502`). La nota di credito ha già
`fatture_rettifiche` (FK fisiche). Proposta: colonne del modello presenti per uniformità, di norma NULL; da decidere se
servono.

**8. Lotto.** Testate; banale (nessun dato, nessun lettore oltre la vista). Si ritira l'indice import.

---

#### 2. Righe

##### 2.1 `vendite.preventivi_righe`

**1.** Colonne del lotto A (`20261105-02`), modello A: «la chiave sta in `sorgente_riga` (key_selector id) o
`sorgente_uid` (uid)». Tipo previsto: `PREVENTIVO_RIGA` (la revisione) [F commento].
**2. Scrittori.** Nessuno oggi [F]. Previsto dal lotto B `-16` (`fn_crea_revisione_preventivo`, PREVENTIVO_RIGA).
Col modello: `PREVENTIVO` + `sorgente_uid` = uid della **revisione di partenza** + `sorgente_riga` = id della riga
copiata [I proposta].
**3. Lettori.** Guard tipizzato, guard articolo (esenzione: «sorgente_tipo_id IS NOT NULL»),
`dbops.trgfn_child_requires_non_obsolete_parent` (esenzione lotto A), presidio orfani [F].
**4. Vincoli.** FK `fk_preventivi_righe_sorgente_tipo`; nessun indice, nessun CHECK [F].
**5. Guard.** `trg_preventivi_righe_a10_guard_sorgente_ins_upd` (tipizzata) + `child_requires_active_parent` [F].
**6. S-9 (bersaglio `PREVENTIVO_RIGA`).** DELETE della riga: lock fuori bozza; `ordini_righe.preventivo_riga_id` FK NO
ACTION blocca la riga consumata da un ordine [F]. La testata `preventivi`: CASCADE sulle righe; canale PREVENTIVO
aperto all'INSERT e mai tolto → coerente coi 352 orfani PREVENTIVO del brief [F meccanismo].
**8. Lotto.** Primo lotto di famiglia (righe di vendita).

##### 2.2 `vendite.ordini_righe`

**1.** Colonne del 2025 (non del lotto A, che qui ha solo montato il guard): `sorgente_tipo_id` «tipo di sorgente»,
`sorgente_uid` «Origine import (uid)», `sorgente_riga` **DEFAULT 0** «Progressivo/ID riga nella sorgente (0 se non
applicabile)» [F]. Manuale `ordini_righe.md:16, :41, :132`: «idempotenza della sorgente / import».
**2. Scrittori.** Nessuno scrive il tipo [F]; tutti gli INSERT lasciano `sorgente_riga = 0` col tipo NULL (§0.2).
Previsti: lotto B `-15` (`PREVENTIVO_RIGA` accanto a `preventivo_riga_id`) e i verbi dell'offerta («testata +
progressivo», fermati). Col modello: da preventivo `PREVENTIVO` + uid preventivo + `sorgente_riga` = id della riga;
da offerta `OFFERTA_COMMERCIALE` + uid offerta + `sorgente_riga` = **vedi §4 (S-1)**.
**3. Lettori.** Guard tipizzato, guard articolo, presidio orfani; BE nessuno [F]. pgTAP che la scrivono a mano:
`test-fattura-origini-v1.sql:91` (con commento che cita `chk_ordini_righe_preventivo_ha_sorgente`, **vincolo che non
esiste** perché sta nel `-19` parcheggiato), `test-documento-lineage-seminata-v1.sql` [F].
**4. Vincoli.**

| Indice / default | Classificazione | Motivo |
| --- | --- | --- |
| `uq_ordini_righe_v_sorgente_fk (tipo, uid) WHERE tipo NOT NULL` | **idempotenza import → residuo** | blocca due righe dalla stessa offerta e il secondo ordine dopo l'annullo (brief §3.4); per i tipi a chiave `id` non morde (uid NULL, NULL distinti) |
| `DEFAULT 0` su `sorgente_riga` | **residuo** | lo 0 è una riga che non esiste; con un tipo a chiave `uid` (offerta) la riga avrebbe `sorgente_uid` **e** `sorgente_riga = 0` se il verbo non nomina la colonna: due chiavi, e il guard non controlla l'esclusività |

**5. Guard.** Tipizzata (da `20261105-14`), `child_requires_active_parent`, `trgfn_dlt_block_ordrig_ddtrig` [F].
**6. S-9 (bersaglio `ORDINE_VENDITA_RIGA`).** DELETE bloccato se ha fulfillment (`E_DELETE_BLOCKED_FUL`) o
`resi_righe` (`E_DELETE_RIGA_DOC_REFERENZIATA`), più lock fuori bozza [F, `trgfn_dlt_block_ordrig_ddtrig.md:94`]. **Non**
guarda le `ddt_righe` che la nominano come sorgente (oggi nessuna; col lotto righe sì) → col modello il controllo
diventa del lato «in uscita» [I].
**7. S-8 — `preventivo_riga_id`** (FK fisica, **non censita dal brief nel G8**): ⛔ **non può confluire** [F]. Non è
una provenienza ma un **legame di consumo**: `vendite.fn_documento_ritira_legami` lo azzera all'annullo dell'ordine
per «rilasciare» la riga del preventivo (`fn_documento_ritira_legami.md:165`), mentre la provenienza deve restare
sull'ordine annullato. Lo leggono `fn_documento_legami`, `fn_documento_lineage_legami`, `fn_doc_porta_ritiro_ammette`,
`fn_push_preventivo_a_ordine` (idempotenza: la riga già consumata non si ripusha [I]) e 11 pgTAP. La sorgente si
scrive **accanto** (era il disegno del `-15`). Eccezione da far decidere a Tid.
**8. Lotto.** Righe di vendita: togliere il DEFAULT 0, convertire gli 0 esistenti in NULL (tutti col tipo NULL [I da
verificare su dbdev]), ritirare l'indice unico, CHECK di forma.

##### 2.3 `vendite.ddt_righe`

**1.** Lotto A; commento: «ORDINE_VENDITA_RIGA dalla bolla da ordine, RESO_VENDITA_RIGA dalla riconsegna … nello
STESSO INSERT, prima del legame in `ordini_righe_fulfillment`» [F].
**2. Scrittori.** Nessuno oggi: `fn_genera_ddt_da_ordine.md:192` non la nomina [F]. Previsti `-17`/`-18`. Col modello:
`ORDINE_VENDITA` + `sorgente_id` = ordine + `sorgente_riga` = riga d'ordine; riconsegna `RESO_VENDITA` + reso + riga
di reso (vedi l'incoerenza con la testata in §1.2).
**3. Lettori.** Guard tipizzato, guard articolo, presidio orfani; pgTAP `magazzino/test-ddt-scarico-v1.sql` [F].
**4. Vincoli.** Solo FK; nessun indice [F].
**5. Guard.** Tipizzata, `child_requires_active_parent`, `trgfn_dlt_block_ordrig_ddtrig` [F].
**6. S-9 (bersaglio `DDT_VENDITA_RIGA`).** DELETE bloccato con fulfillment, `resi_righe`, `resi_righe_riconsegne`
(FK NO ACTION) e lock fuori bozza; `ddt_righe_prelievi` CASCADE [F].
**7. S-8 — `ordini_righe_fulfillment`**: vedi §3.2. ⛔ non può confluire.
**8. Lotto.** Righe di vendita.

##### 2.4 `vendite.contratti_righe`

**1.** Lotto A; tipo previsto `OFFERTA_COMMERCIALE` («dal contratto nato dall'offerta») [F].
**2. Scrittori.** Nessuno oggi [F]. `fn_push_offerta_a_contratto` copia **1:1** le righe da
`vendite.offerte_commerciali_eccezioni` (`fn_push_offerta_a_contratto.md:295`, loop `ORDER BY id`) [F]: col modello
`OFFERTA_COMMERCIALE` + uid offerta + `sorgente_riga` = **`offerte_commerciali_eccezioni.id`**. Qui S-1 funziona.
**3–5.** Come le altre righe del lotto A; in più `trgfn_righe_guard_esclusione_immutabile`, lock su `tipo_eccezione` [F].
**6. S-9 (bersaglio `CONTRATTO_RIGA`).** Lock fuori bozza; componenti CASCADE; figli polimorfi (commesse_attivita?) [I].
**8. Lotto.** Righe di vendita; `config.sorgenti` per OFFERTA_COMMERCIALE prende `target_righe_table =
offerte_commerciali_eccezioni` (FK `offerta_id`).

##### 2.5 `vendite.fatture_righe`

**1.** «FK → config.sorgenti (ex source_tipo testuale)», `sorgente_uid` «Origine import (uid)», `sorgente_riga`
DEFAULT 0 «Progressivo/ID riga nella sorgente» [F]. Manuale `fatture_righe.md:78` «sulle righe prodotte
dall'aggregazione sono NULL», `:121` «unique parziale (idempotenza)». G5 nel brief (tipo COMMESSA + riga di commessa).
**2. Scrittori.** BE `pipeline_repository.py:3503`: `NULL, NULL, NULL` espliciti (quindi niente 0) [F];
`pipeline_repository.py:2014`: la parte IVA copia le tre colonne dalla capofila [F]. Nessuno scrive COMMESSA oggi [F].
**3. Lettori.** BE `pipeline_repository.py:1959` (`list_righe_per_plafond`, le passa al plafond) [F]. Nessuna funzione
DB legge `fatture_righe.sorgente_*` (le funzioni di fatturazione leggono `commesse_attivita`) [F].
**4. Vincoli.** `uq_fatture_righe_v_sorgente_fk (tipo, uid) WHERE tipo NOT NULL` = **residuo**: ⚠️ con una sorgente
valorizzata, la copia della capofila sulla parte (`:2014`) **violerebbe** l'indice (stessa coppia due volte) [I
dedotto]. `DEFAULT 0` residuo.
**5. Guard.** Solo `child_requires_active_parent` e il congelamento [F]: nessun guard polimorfo, fuori dal presidio
orfani.
**6. S-9 (bersaglio `FATTURA_RIGA`).** Congelamento (`trgfn_fattura_satellite_guard_congelamento`); figli fisici
`attivita_fatturabili`, `commesse_attivita`, `resi_righe_accrediti`, titoli IVA NO ACTION [F].
**7. S-8.** `riga_rettificata_id` / `riga_capofila_id` sono FK fisiche monomorfe con regole proprie (gemella della
rettifica, spezzatura IVA): **restano fuori** [I proposta]. La provenienza COMMESSA vale per la riga di una sola
attività; per la riga aggregata resta NULL (decisione già scritta nel manuale).
**8. Lotto.** Insieme a `attivita_fatturabili` (S-7, perimetro altrui) o alle righe di vendita; il codice
`FATTURA_RIGA` è usato anche come **tipo entità** in errori/riepiloghi (`trgfn_fatture_guard_stato`,
`trgfn_fatture_righe_guard_riga_capofila`, `fn_ricalcola_riepilogo_iva_fattura`, `fn_check_fattura_emettibile`) [F]:
non va confuso col tipo sorgente nel ritiro S-2.

---

#### 3. Colonne parallele G8 (S-8)

##### 3.1 `ordini.documento_origine_*` e `contratti.offerta_id`

Vedi §1.1.7 e §1.4.7: **possono confluire**, con due attenzioni [I]: (a) la regola d'unicità sull'offerta va
riscritta su `sorgente_tipo_id` (predicato per id, non per codice); (b) `offerta_id` ha una FK fisica che oggi
impedisce di cancellare l'offerta: va sostituita dal lato «in uscita» (S-9), non persa. Per l'ordine la chiave
cambia **di tipo** (oggi id, a catalogo uid).

##### 3.2 `vendite.ordini_righe_fulfillment`

⛔ **Non può confluire** [F]. Motivi concreti:

1. **porta una quantità** (`qta_evasa`, CHECK `> 0` e finito), con la guardia di over-fulfillment
   `trgfn_ordini_ful_guard_consistenza` (lock sulla riga d'ordine, residuo reso-aware);
2. **è N:M**: `uq_ordini_r_ful_v_pair (ordine_riga_id, ddt_riga_id)` ammette più righe d'ordine per una riga di DDT, e
   il codice lo sa (`E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI`, `fn_check_ddt_riga_correggi_qta_evasa.md:125`); una sola
   `sorgente_riga` non lo può dire;
3. **si ritira** (`vendite.fn_ddt_riga_ritira_legami` lo cancella; `trgfn_ddt_riga_legame_guard` ne governa UPDATE e
   DELETE), mentre la provenienza resta;
4. FK fisiche `ON DELETE RESTRICT` su entrambi i lati, che proteggono riga d'ordine e riga di bolla.

Lettori (27 oggetti DB) [F]: `fn_partite_merce`, `fn_situazione_merce_ordine`, `fn_resi_da_accreditare`,
`fn_ordine_ha_residuo_evasione`, `fn_ordine_proietta_stato_evasione`, `fn_ordine_riga_spedita`, `fn_ddt_riga_evasa`,
`fn_ddt_riga_correggi_qta_evasa`, `fn_ddt_push_diagnosi`, `fn_ddt_vincoli_cliente`, `fn_doc_porta_ritiro_ammette`,
`fn_documento_legami`, `fn_documento_lineage_legami`, `trgfn_resi_righe_guard_origine_coerente`,
`script.fn_check_ddt_emittibile`, `script.fn_check_ddt_riga_correggi_qta_evasa`, le viste `vw_dash_fatturazione_ddt`,
`vw_dash_fatturazione_ordini`, `vw_ordini_righe_dettaglio`; BE `resi_repository.py:1089, :1096`,
`_coda_documento_filtro.py:72`; 19 pgTAP. Proposta [I]: la sorgente della riga di bolla dice **da dove è nata**
(la riga d'ordine da cui il verbo l'ha generata), il fulfillment dice **quanto evade e di chi**. Sono due fatti, non
lo stesso fatto due volte come dice il commento di `ddt_righe.sorgente_tipo_id`: il commento va riscritto. Eccezione
da far decidere a Tid.

##### 3.3 Parallele che il brief non elenca [F]

| Colonna | Che cosa | Verdetto proposto |
| --- | --- | --- |
| `ordini_righe.preventivo_riga_id` (FK) | consumo della riga di preventivo, azzerato all'annullo | ⛔ fuori (§2.2.7) |
| `fatture_righe.riga_rettificata_id`, `riga_capofila_id` (FK) | rettifica, spezzatura IVA | fuori: monomorfe, regole proprie |
| `contratti.parent_contratto_id` (FK SET NULL) | successione di contratti | fuori [I]: non è «nasce da un documento» nel senso della sorgente, ma va detto |
| `resi_righe.ddt_riga_id`, `ordine_riga_id` (FK) | origine della riga di reso | fuori perimetro mio; da censire con i resi_righe |

---

#### 4. `fn_offerta_righe_espanse` e i verbi dell'offerta (S-1)

[F] `vendite.fn_offerta_righe_espanse(p_offerta_id)` restituisce `articolo_id, …, tipo_eccezione, origine,
componenti` (`fn_offerta_righe_espanse.md:16`): **nessun id di riga**. Le righe vengono da due fonti:

* PARTE 1 — `vendite.fn_espandi_listino_versione` (che a sua volta non restituisce l'id della riga di listino) con
  l'overlay `LEFT JOIN offerte_commerciali_eccezioni` (OVERRIDE/ADESIONE; ESCLUSIONE tolte);
* PARTE 2 — `offerte_commerciali_eccezioni` di tipo AGGIUNTA.

Conseguenza per S-1 («`sorgente_riga` = l'id della riga quando esiste») [I]: per le righe che vengono da
un'eccezione, la riga d'origine **esiste** ed è `offerte_commerciali_eccezioni.id`; per quelle del solo listino
**non esiste una riga dell'offerta** (la riga è della versione di listino, un altro documento). Quindi:
`sorgente_riga` = id dell'eccezione se c'è, **NULL** altrimenti (provenienza = l'offerta intera). La funzione deve
esporre l'`id` dell'eccezione (colonna in coda, `DROP` + `CREATE` per RETURNS TABLE); `fn_espandi_listino_versione`
non va toccata. Lettori della funzione: `fn_genera_ordine_da_offerta`, `script.fn_check_righe_offerta_in_ordine` [F].
Il catalogo per OFFERTA_COMMERCIALE prende `target_righe_table = vendite.offerte_commerciali_eccezioni`, colonna FK
`offerta_id`. Per il guard «la riga appartiene al documento» è sufficiente.

Verbi che generano un documento da un altro [F]: `fn_push_preventivo_a_ordine`, `fn_genera_ordine_da_offerta`,
`fn_push_offerta_a_contratto`, `fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`, `fn_crea_revisione_preventivo`
(righe), `fn_crea_revisione_offerta` (testata offerta, fuori dalle colonne sorgente). Più il BE `crea_reso`.

---

#### 5. Conteggi pgTAP [F]

970 file pgTAP in totale. Sulle colonne del perimetro: `documento_origine_*` 10 file; `ddt`/`resi.sorgente_uid` 18;
`sorgente_*` delle righe 4 (`test-fn-accredita-riga-reso-v1`, `test-fattura-origini-v1`,
`test-documento-lineage-seminata-v1`, `magazzino/test-ddt-scarico-v1`); nomi degli indici d'idempotenza/origine 3
(`script/test-fn-available-actions-offerta-v1`, `test-annullo-documento-con-legami-v1`,
`test-grammatica-origine-destinazione-sorgenti-v1`); fulfillment 19; `preventivo_riga_id` 11; `offerta_id` dei
contratti 25.

---

#### 6. Riepilogo

##### 6.1 Ricadute BE/FE (file)

* `backend/apps/vendite/db/resi_repository.py` (`create_reso` :635-650; `get_stato_e_ddt_origine` :333) e
  `services/resi_service.py:515-535` — scrittura e lettura del DDT d'origine per uid.
* `backend/apps/vendite/db/ordini_repository.py:286, :432-433` — origine per `(codice, id)`.
* `backend/apps/vendite/services/ordini_service.py:88` (mappa del nome `uq_ordini_v_documento_origine_offerta`),
  `:542`, `:575` (risposta `documento_origine {tipo, id}`).
* `backend/apps/vendite/services/ordine_document_context_builder.py:213-215` (origine in stampa).
* `backend/apps/vendite/db/offerte_repository.py:228` (`c.offerta_id`), `services/offerte_service.py:974` e
  `types.py:1095` (`OffertaPushResult.sorgente_uid` = uid del **contratto**: nome da correggere).
* `backend/apps/vendite/db/ddt_repository.py:72` (filtro `ordine_origine_numero`, stabile se la vista tiene l'alias).
* `backend/apps/vendite/db/pipeline_repository.py:1959, :2002-2014, :3485-3503` (righe di fattura).
* `backend/apps/vendite/services/resi_service.py:92` (mappa `fk_resi_sorgente_tipo`).
* Capability: `script.fn_available_actions_ddt` / `_reso` espongono `non_editable_fields` con `sorgente_uid` → il FE
  li legge come campi bloccati (da allungare con `sorgente_id`).
* FE: `vendite/resi/components/ResoDrawer.vue:353`, `ResoForm.vue:92`, `vendite/ordini/components/OrdiniSearchTable.vue`,
  `vendite/ddt/components/DdtSearchTable.vue`, `vendite/offerte/api/offerteApi.js:96,:119`,
  `vendite/offerte/stores/offerte.js:164,:175`. Tutti leggono **alias derivati** delle viste
  (`ddt_origine_*`, `ordine_origine_*`, `documento_origine_codice`): se le viste tengono gli alias, il FE non cambia.
* Test BE: `test_origine_ordine_sorgente_db.py`, `test_genera_ordine_da_offerta_db.py`, `test_resi_create_db.py`,
  `test_resi_service.py`, `test_ddt_service.py`, `test_offerte_service.py`, `test_ordine_document_context_builder.py`,
  `api/test_ddt_api.py`, `api/test_ordini_api.py`, `api/test_contratti_api.py`.

##### 6.2 Dubbi aperti (per Tid)

1. **Riconsegna**: la bolla di riconsegna con ordine dichiara oggi l'ORDINE in testata; le sue righe (piano lotto B)
   il RESO. Qual è la provenienza? (proposta: il reso; l'ordine resta nel fulfillment).
2. **S-1 per l'offerta**: le righe del solo listino non hanno una riga dell'offerta → `sorgente_riga` NULL. Va bene, o
   si vuole la riga della versione di listino (che è un altro documento, e romperebbe «il tipo è il documento»)?
3. **S-8, eccezioni da confermare**: `ordini_righe_fulfillment` (quantità, N:M, si ritira) e
   `ordini_righe.preventivo_riga_id` (consumo, si azzera all'annullo) **restano**; la sorgente si scrive accanto.
4. **`trgfn_documenti_sync_canali`**: portare la provenienza dell'ordine in `sorgente_*` accende il ramo morto che
   consuma il canale PREVENTIVO. È voluto?
5. **Unicità sull'offerta** (`uq_ordini_v_documento_origine_offerta`, `uq_contratti_offerta_id`): su
   `sorgente_tipo_id` il predicato parziale chiede l'id letterale del tipo. Indice parziale per id (seed a id esplicito)
   o guard?
6. **S-9, cancellazioni fuori dal DB**: «DRAFT e zero righe» per ordini, DDT e resi è solo nel BE; resi e contratti
   non hanno nessun guard DB di DELETE sulla testata. Il meccanismo degli orfani di `documenti_fatturazione_canali`
   (canale aperto all'INSERT, mai chiuso al DELETE della bozza) spiega i numeri del brief per ORDINE, DDT, PREVENTIVO;
   per CONTRATTO non c'è un percorso BE di cancellazione: da dove vengono i 14?
7. **`fatture`**: serve davvero una provenienza di testata per un documento che aggrega? (proposta: colonne presenti,
   NULL salvo casi futuri).
8. **Le 8 righe COMMESSA di `fatture_righe` su dbdev**: il builder citato dal brief non le scrive più; chi le ha
   scritte?
9. **Documentazione stantia da riscrivere nello stesso lotto**: commento di `ordini.documento_origine_id` («NESSUNA
   UNIQUE»), manuale `ordini.md:241` (CHECK chiuso), commenti «import» di `ddt.sorgente_*`, manuali `ordini.md`,
   `fatture.md`, `ordini_righe.md`, `fatture_righe.md` (idempotenza import), commento di `ddt_righe.sorgente_tipo_id`
   («lo stesso fatto due volte»), il commento del pgTAP `test-fattura-origini-v1.sql:88` che cita un CHECK che non
   esiste.

### Censimento: commesse, pipeline di fatturazione, canali

> **Per:** `brief-db-sorgente-documento-e-riga` §7.1 (Appendice). **Chi:** team DB, 2026-11-06. Sola lettura.
> **Fonti:** doc auto-generata `docs/it/dbzero/vendite/{tabelle,funzioni,views}/`, i manuali, il catalogo di
> `zeroerp_ruoli` (scratch, vuoto di dati: **struttura**, non dbdev), grep su `backend/`, `frontend/src`,
> `db/pgtap`, `backend/scripts/tests`, `scripts/`. La storia dai brief `work-done` e dal `git log`.
> **Legenda:** ✅ FATTO (file:riga o catalogo) · 🔶 IPOTESI (ragionata sul codice, da confermare) · 📅 dato
> datato (dbdev, non è un motivo).

---

#### 0. In breve

| # | Scoperta | Grado |
| --- | --- | --- |
| 1 | **L'impronta** `attivita_fatturabili.sorgente_uid` ha **un solo lettore vero**: `fn_emit_attivita_fatturabili_da_commessa`, per ritrovare la riga AF che ha già emesso lei (il ramo UPDATE, cioè la ripresa dei residui dopo `fn_libera_attivita_fatturabili`). Altri tre la leggono senza usarla (§S-7.1) | ✅ |
| 2 | **L'impronta è già rotta su dbdev dal 2026-10-20.** Lo SQL una tantum del 2e ha riscritto le `segment_key` (350) e la loro copia nel `meta` delle AF (62), ma **non** `sorgente_uid = md5(segment_key)`. Le 62 AF di prima non si ritrovano più per impronta: è il «2 su 64» del §6.1 | ✅ codice + 📅 numeri |
| 3 | Su quelle 62, se la riga viene liberata e il giro la riprende, `fn_emit` non la trova, va nel ramo INSERT e urta `uq_attivita_fatturabili_commessa_attivita` (23505, errore non registrato). La commessa fallisce a ogni giro | 🔶 da provare |
| 4 | La stessa ricerca si fa **per `commessa_attivita_id`** (FK NOT NULL, UNIQUE, 1:1): non dipende dal formato della chiave e chiude anche il caveat C1 (collisione fra commesse). L'impronta si può togliere senza colonna nuova. La decisione è di Tid | ✅ struttura |
| 5 | `vw_preventivi_smistamento_righe` cerca l'AF con `af.sorgente_uid = p.uid AND af.sorgente_riga = pr.id`: grammatica sbagliata, **non scatta mai**. Gli stati `FATTURATA` ed `EMESSA_AF` del dialogo di smistamento (FE) sono morti, e nessun pgTAP li prova | ✅ |
| 6 | **`documenti_fatturazione_canali` non ha lettori**: niente BE, FE o vista. La legge solo la funzione che la scrive. I 387 orfani nascono dalla cancellazione delle bozze («abbandono bozza», BE), che non tocca il canale aperto dal trigger all'INSERT | ✅ percorso, 📅 numeri |
| 7 | `commesse_attivita` **non ha `sorgente_riga`**: la riga sta solo dentro `segment_key` (`:R:<id>`), e la leggono `fn_segment_key_riga` e `segment_base`. Col §4 serve una colonna nuova | ✅ |
| 8 | ⚠️ **Ricaduta nascosta di S-5:** `fn_build_gruppo_fatturabile_key` costruisce `<CODICE>:<commesse_attivita.sorgente_uid>`, e quella chiave è **salvata** in `fatturazione_lotti_gruppi`, `_esiti`, `_log`. Se `commesse_attivita` passa all'id, le chiavi salvate non corrispondono più. Lo stesso vale per `segment_key`, che porta l'uid | ✅ |
| 9 | Su `attivita_fatturabili` (G5) le colonne `sorgente_*` del §4 sarebbero **copie** di `commessa_id` e `commessa_attivita_id` (FK NOT NULL). È un caso da segnalare per S-8 | ✅ struttura |

---

#### 1. Scheda `vendite.commesse_sorgenti` (G3)

**1. Colonne** (catalogo ✅)

| Colonna | Tipo | NULL | Default | Commento | Significato (manuale `commesse_sorgenti.md:33-42`) |
| --- | --- | --- | --- | --- | --- |
| `sorgente_tipo_id` | bigint | NOT NULL | — | — | il tipo del documento |
| `sorgente_uid` | text | NOT NULL | — | — | chiave **canonica** secondo `key_selector`: uid testuale per preventivo e offerta, `id::text` per ordine, contratto, DDT, consumi |
| `sorgente_riga` | bigint | sì | — | — | «grana di riga del link, non validata». 🔶 nessuno la scrive: `fn_upsert_commessa_attivita` chiama il link senza `p_sorgente_riga`, quindi è sempre NULL |

Grammatica: **G3** (testo canonico, la riga a parte).

**2. Scrittori**

* ✅ DB: `vendite.fn_link_commessa_sorgente` è l'unica porta. Normalizza: per un tipo a chiave `id` traduce l'uuid
  in `id::text` (`EXECUTE format('SELECT id::text FROM %s WHERE uid = $1')`). La chiama
  `vendite.fn_upsert_commessa_attivita` (corpo ~riga 260, solo per lo scope `PUSH_COMMESSA`), con lo **stesso**
  `p_sorgente_uid` che scrive grezzo in `commesse_attivita`. Fixture: `dbops.fn_pgtap_crea_commessa`.
* ✅ BE: nessuna scrittura diretta. Il commento `commesse_source_handlers.py:471` lo conferma: il link lo scrive la
  madre DB.

**3. Lettori** (✅ catalogo)

* `vendite.fn_commessa_viva_di_sorgente`: `cs.sorgente_uid = p_sorgente_chiave` (canonica).
* `vendite.fn_emit_attivita_fatturabili_da_commessa`: cerca la ROOT, senza leggere la chiave.
* `vendite.fn_documento_lineage_archi`: un **CASE per tipo** in due punti, `(cs.sorgente_uid)::uuid` per il preventivo
  e `::bigint` per ordine, contratto e DDT, più i join `p.uid = cs.sorgente_uid::uuid`, `o.id = …::bigint`,
  `c.id::text = cs.sorgente_uid`, `d.id::text = …`. È un secondo CASE oltre a quello di `_legami` (§BB).
* `script.fn_check_sorgente_chiudibile`, `script.fn_check_ordine_annullabile`,
  `vendite.trgfn_guard_fatturazione_immediata_immutabile`.
* BE (3 file): `commesse_repository.py:842-856` (passa per `fn_commessa_viva_di_sorgente`); pratiche e preventivi
  leggono `pratiche_sorgenti`, non questa tabella.
* pgTAP: 22 file.

**4. Vincoli e indici**

| Oggetto | Definizione | Classe | Motivo |
| --- | --- | --- | --- |
| `uq_commesse_sorgenti_src_uid_commessa` | UNIQUE (tipo, uid, commessa) | **regola di dominio** | un documento compare una volta per commessa (manuale :21). Col §4 si sposta su (tipo, `sorgente_id`/`sorgente_uid`, commessa) con `NULLS NOT DISTINCT` |
| `uq_commesse_sorgenti_commessa_root` | UNIQUE (commessa) WHERE ROOT | dominio, non sulla sorgente | resta com'è |
| `chk_commesse_sorgenti_ruolo` | ROOT \| COLLEGATO | — | resta |

**5. Guard:** `trg_commesse_sorgenti_a10_guard_sorgente_ins_upd` → `script.trgfn_guard_sorgente_polimorfa_testuale`
(formato ed esistenza); `trgfn_commesse_sorgenti_guard_emittente` (omogeneità dell'emittente);
`trgfn_child_requires_active_parent` sul tipo; storico.

**6. Cancellazione del bersaglio (S-9):** nessuna FK. Preventivo: `elimina_preventivo`
(`preventivi_service.py:558-592`) vuole BOZZA, zero righe, zero pratiche. Non controlla le commesse, ma una bozza
senza righe non ha push (🔶). Ordine e DDT: `delete_ordine`/`delete_ddt` (BE, abbandono bozza) vogliono DRAFT.
🔶 Da verificare che un ordine in DRAFT non possa avere un link di commessa. Nessun trigger DELETE pulisce il link.

**7. Lotto e note:** lotto «commesse» (S-4). Va a `sorgente_id` per ordine, contratto, DDT e consumi e a
`sorgente_uid uuid` per preventivo e offerta. Riscrivere l'ON CONFLICT e la normalizzazione di
`fn_link_commessa_sorgente`, `fn_commessa_viva_di_sorgente` (parametro `text`) e i due CASE della lineage.

---

#### 2. Scheda `vendite.commesse_attivita` (G4)

**1. Colonne** (✅)

| Colonna | Tipo | NULL | Commento | Significato (manuale `commesse_attivita.md:45-80`) |
| --- | --- | --- | --- | --- |
| `sorgente_tipo_id` | bigint | sì | — | tipo del documento d'origine; NULL solo per ONERE manuale e RETTIFICA |
| `sorgente_uid` | text | sì | — | **l'uid del documento, sempre**, anche per i tipi a chiave `id` |
| *(manca)* `sorgente_riga` | — | — | — | ✅ non c'è. La riga sta in `segment_key` (`<CODICE>:<uid>:R:<riga>[:M:<mese>][#CMP:…\|#RET:…]`) |
| `segment_key` varchar(128) / `segment_base` (generata) | — | NOT NULL | — | chiave d'idempotenza del push; contiene **l'uid** del documento e la riga |

Grammatica: **G4** (l'uid come testo); la riga in **V8** (dentro la chiave).

**2. Scrittori**

* ✅ DB: `vendite.fn_upsert_commessa_attivita` (`ON CONFLICT (commessa_id, segment_key)`, scrive
  `NULLIF(btrim(p_sorgente_uid),'')` grezzo). Il valore arriva dalle `fn_list_*_da_pushare`, che proiettano
  `<testata>.uid::text` (per esempio `fn_list_preventivi_da_pushare`: `p.uid::text AS sorgente_uid`). La chiamano
  `fn_batch_upsert_commessa_attivita`, `fn_aggiungi_onere_commessa` (sourceless), `fn_accredita_riga_reso`
  (`p_sorgente_uid => NULL`, RETTIFICA) e `dbops.fn_pgtap_crea_commessa_attivita`.
* ✅ BE: `commesse_repository.py:1006-1081` (`p_sorgente_uid => inp.sorgente_uid`) e `:1198` (batch). Il valore
  arriva da `commesse_source_handlers.py:770` (`row.sorgente_uid` della fn_list).
  ⚠️ **Nome ingannevole:** nel BE `fetch_pushable_rows(…, sorgente_uid: int)` (`commesse_repository.py:498`) e
  `pr_run_commesse_push_one(sorgente_uid: int)` (`commesse_service.py:337`) portano **l'id** del documento come
  filtro, con lo stesso nome della colonna. Chiamanti: `preventivi_service.py:1999`, `ordini_service.py:1073`,
  `ddt_service.py:1091`.

**3. Lettori** (✅, 25 funzioni e 7 viste nel catalogo, tutte con la grammatica uid)

* `vendite.fn_build_gruppo_fatturabile_key(tipo, uid, commessa)` → `CODICE:<uid>` o `MAN:<commessa>`. La chiamano
  `vw_commesse_attivita_emittibilita`, `vw_dash_competenza_attivita`, `vw_lotti_gruppi_serviti`,
  `script.vw_lotto_documento_righe`, `fn_list_commessa_attivita`, `fn_select_attivita_fatturabili` (filtro
  `p_gruppi`), `fn_esito_gruppi_giro`, `script.fn_gruppi_di_commessa_nel_lotto`. ⚠️ **La chiave è salvata**:
  `fatturazione_lotti_gruppi.gruppo_key`, `fatturazione_lotti_esiti.gruppo_key`, `fatturazione_lotti_log.gruppo_key`
  (text). Convertire la colonna (S-5) cambia le chiavi nuove, e quelle salvate non corrispondono più (vedi §R-1).
* `vendite.fn_get_sorgente_documento_ref(tipo, text)`: prova prima l'uuid (`WHERE t.uid = $1`), poi l'id se
  `key_selector='id'`. Quindi legge **entrambe** le grammatiche.
* `vendite.fn_documento_lineage_legami`: il CASE per tipo (`fn_documento_lineage_legami.md:42`).
* `vendite.fn_documento_legami`, `fn_documento_ritira_legami` (`SELECT d.uid::text` / `c.uid::text`, poi
  `fn_check_sorgente_chiudibile`), `fn_ritira_commessa_attivita_da_sorgente` (`ca.sorgente_uid = v_uid`),
  `fn_fattura_origini` (dinamico: `x.uid::text = $1`), `fn_resolve_termini_pagamento` (`v_src_uid::uuid`, solo
  ORDINE_VENDITA e PREVENTIVO), `fn_annulla_commessa_attivita`, `trgfn_commesse_attivita_proietta_stato_preventivo`,
  `fn_contratti_addebiti_maturati`, `script.fn_check_ordine_annullabile`.
* Da `segment_key`: `script.fn_segment_key_sorgente/_riga` in `fn_af_merce_per_riga`;
  `script.fn_get_stato_push_segment(fn_segment_key(…uid…))` in `vw_preventivi_smistamento_righe` e
  `vw_preventivi_righe_smistabili_commessa`.
* BE: 19 file. Il principale è `commesse_repository.py:137, 284-402, 1677` (`sorgente_uid` della lista).
* FE: nessun riferimento diretto (✅ grep `frontend/src`).
* pgTAP: 84 file.
* ⚠️ Doc stantia: il manuale (`commesse_attivita.md:66-67`) cita `vw_dash_fatturazione_contratti … AND
  ca.sorgente_uid = c.uid::text`, ma la vista oggi non legge `commesse_attivita` (✅ viewdef).

**4. Vincoli e indici**

| Oggetto | Classe | Motivo |
| --- | --- | --- |
| `chk_commesse_attivita_sorgente_pair` (tipo e uid insieme NULL o insieme pieni) | forma | col §4 diventa «tipo ⇒ esattamente una chiave» |
| `chk_commesse_attivita_senza_sorgente_onere_rettifica` | **dominio** | NORMALE ⇒ sorgente; resta |
| `uq_commesse_attivita_commessa_segment` (commessa, segment_key) | **idempotenza del push** | non è sulla sorgente, ma la chiave contiene l'uid |
| `ix_commesse_attivita_sorgente_competenza` (sorgente_uid, competenza_mese) | non unico | senza il tipo; da rifare sulla chiave nuova |
| storia: `uq_commesse_attivita_src_uid_partial` | residuo, ritirato | `test-drop-uq-commesse-attivita-src-uid-partial-v1` |

**5. Guard:** ✅ **nessun guard polimorfo**. C'è solo `trgfn_child_requires_active_parent` sul tipo. Il manuale
(:83-86) lo dice: la tabella è «fuori dal perimetro».

**6. S-9:** nessuna FK verso il documento. Il ritiro (`fn_ritira_commessa_attivita_da_sorgente`) scatta
**all'annullo** del documento (`fn_documento_ritira_legami`), non alla cancellazione. Alla cancellazione di una bozza
non c'è niente da ritirare, se la bozza non ha push (🔶 come §1.6).

**7. Lotto e note:** S-5 si applica: ordine, contratto, DDT e consumi passano da uid a `sorgente_id`. Serve la colonna
`sorgente_riga` (l'id della riga del documento, da `fn_segment_key_riga`; per il contratto la riga, mentre il mese
resta nella chiave; per i consumi NULL). ONERE e RETTIFICA restano sourceless. La conversione tocca la chiave dei
gruppi (§R-1). 🔶 Se si vuole tenere `segment_key` immutata, il push dovrà continuare a costruirla con l'uid anche
dopo S-5.

---

#### 3. Scheda `vendite.attivita_fatturabili` (G5)

**1. Colonne** (✅ catalogo; commenti di colonna **stantii**)

| Colonna | Tipo | NULL | Default | Commento | Che cosa c'è davvero |
| --- | --- | --- | --- | --- | --- |
| `sorgente_tipo_id` | bigint | sì | — | «FK → config.sorgenti (ex sorgente_tipo testuale)» | sempre **COMMESSA** (scritto da `fn_emit`) |
| `sorgente_uid` | **uuid** | sì | — | «**Origine import (uid)**» (falso) | **l'impronta**: `md5(segment_key)` formattato come uuid (`fn_emit…md5:215`) |
| `sorgente_riga` | bigint | sì | **0** | «ID riga nella sorgente (0 se non applicabile)» | `commesse_attivita.id` (`fn_emit`: `sorgente_riga = v_row.id`). Il normalize mette 0 se è NULL e il tipo c'è |
| `sorgente_origine_tipo_id` | bigint | sì | — | «sorgente business originale … popolata da fn_emit» | copia di `commesse_attivita.sorgente_tipo_id`, **senza chiave** |
| `commessa_id`, `commessa_attivita_id` | bigint | NOT NULL | — | FK | la vera provenienza (FK) |

Grammatica: **G5**. Nel §4 diventerebbe tipo COMMESSA (`key_selector=id`, `target_table=vendite.commesse`),
`sorgente_id = commessa_id`, `sorgente_riga = commessa_attivita_id`: **due copie delle FK NOT NULL** (vedi S-8, §R-3).

**2. Scrittori**

* ✅ DB: solo `vendite.fn_emit_attivita_fatturabili_da_commessa` (INSERT e UPDATE). `fn_libera_attivita_fatturabili`
  e `fn_select_attivita_fatturabili` toccano lock e stato, non la sorgente.
* ✅ Smoke e pgTAP (scrittori di prova, non lettori): `_smoke_fatturazione.py:266-284` (`str(uuid.uuid4())` e
  `t["sorgente_tipo_id"]`); `smoke-push-termine-documento-commessa.py:405-425` (uuid4); `test-attivita-fatturabili.sql:669-760`
  e `test-fatturazione-draft.sql:127` (INSERT diretti).

**3. Lettori:** vedi **§S-7**, che li elenca uno per uno.
`sorgente_origine_tipo_id` lo legge solo `trgfn_attivita_fatturabili_normalize` (risoluzione del `tipo_doc_fiscale_id`);
`fn_resolve_termini_pagamento` lo nomina solo in un commento.
`sorgente_tipo_id`: `fn_resolve_termini_pagamento` (`= 'COMMESSA'`), il normalize (fallback del tipo documento), i
pgTAP (`test-commesse-core-functions-v1.sql:551`, `s.codice = 'COMMESSA'`).

**4. Vincoli e indici**

| Oggetto | Classe | Motivo |
| --- | --- | --- |
| `uq_attivita_fatturabili_commessa_attivita` UNIQUE (commessa_attivita_id) | **idempotenza del pull / regola 1:1** | una AF per riga di commessa; nata con `20260224-42` |
| ~~`uq_attivita_fatturabili_v_sorgente_fk`~~ (tipo, uid) WHERE tipo NOT NULL | **residuo «idempotenza import», ritirato** | nato con `20251005-03`, tolto con `20260224-42`. ⚠️ il manuale lo dà ancora per vivo (`attivita_fatturabili.md:27,78-79,116,195`) |
| `DEFAULT 0` su `sorgente_riga` + normalize «0 se NULL» | residuo | nel modello 0 è una riga che non esiste |
| nessun indice su `sorgente_uid` | — | la ricerca per impronta di `fn_emit` fa una scansione (dentro la RLS) |

**5. Guard:** ✅ nessun guard polimorfo (agganciato con `20251026-02`, **tolto apposta** con `20260225-45`:
«ridondante con FK commessa_attivita_id nel flusso commessa-only»; D6 del 2026-07-18: «resta staccato»).
Il controllo «tipo attivo» c'è solo su `sorgente_origine_tipo_id` (`trg_attivita_fatturabili_a10_sorgenti_require_attivo`),
**non** su `sorgente_tipo_id`.

**6. S-9:** il bersaglio è la commessa e la sua riga, con FK `NO ACTION`: una riga di commessa con AF non si
cancella. Nessuna funzione DB cancella AF (✅ catalogo: nessun `DELETE FROM vendite.attivita_fatturabili`). Il
guard `trgfn_attivita_fatturabili_guard_fatturato` presidia il DELETE.

**7. Lotto e note:** S-7 (§S-7.5). `sorgente_riga DEFAULT 0` e il ramo del normalize vanno via insieme.
`sorgente_origine_tipo_id` è «provenienza a metà»: col §4 la provenienza di business si legge da
`commesse_attivita` tramite la FK, e la colonna serve solo al tipo documento (S-8, vedi §R-3).

---

#### 4. Scheda `vendite.documenti_fatturazione_canali` (G4, senza guard)

**1. Colonne** (✅): `sorgente_tipo_id` bigint NOT NULL, `sorgente_uid` text NOT NULL (CHECK non vuoto),
`target_sorgente_tipo_id` bigint NULL, `target_sorgente_uid` text NULL (CHECK della coppia), `canale_codice`,
`stato_canale` (default APERTO). Nessun commento di colonna. Manuale `documenti_fatturazione_canali.md` (rev.
24-02-2026): «registro tecnico unico dei canali fatturabili per documento sorgente». Storia: `gestione-commesse-v2.md`
§24, dove `sorgente_uid text` fu scelto «per coerenza con commesse_*».
Grammatica: **G4**, l'**uid** come testo, anche per il **target**. È una **seconda** coppia polimorfa sulla stessa
riga (`target_sorgente_*`), da prevedere nel modello e nel presidio di CI (il nome comincia con `target_`).

**2. Scrittori** (✅): solo `vendite.fn_set_documento_canale_stato` (`ON CONFLICT (sorgente_tipo_id, sorgente_uid,
canale_codice)`, e all'apertura blocca gli altri canali APERTI). La chiama solo `vendite.trgfn_documenti_sync_canali`,
montata su:

| Tabella | Trigger | Che cosa scrive |
| --- | --- | --- |
| `vendite.preventivi` | AFTER INSERT OR UPDATE OF uid | canale PREVENTIVO APERTO, `NEW.uid::text` |
| `vendite.ordini` | AFTER INSERT OR UPDATE OF sorgente_tipo_id, sorgente_uid | ORDINE_VENDITA APERTO (`NEW.uid`); se viene da un preventivo, il PREVENTIVO diventa CONSUMATO con target l'ordine |
| `vendite.ddt` | idem | DDT_VENDITA APERTO; se viene da un ordine, ORDINE CONSUMATO con target il DDT |
| `vendite.contratti` | AFTER INSERT | DIRETTO APERTO sul contratto |

Nessuno scrittore BE (✅ grep).

**3. Lettori** (✅): **nessuno** fuori dalla funzione che la scrive (l'UPDATE di auto-blocco). Nessuna vista, nessun
file BE o FE. pgTAP: `test-documenti-fatturazione-canali-v1.sql`, `test-documenti-canali-sync-v1.sql`,
`dbops/test-stati-check-scrittori-v1.sql:165` (censimento degli stati). 🔶 Il «prevenire doppia fatturabilità» del
manuale oggi non lo fa nessuno: è un registro che si scrive e basta.

**4. Vincoli e indici**

| Oggetto | Classe | Motivo |
| --- | --- | --- |
| `uq_doc_fatt_canali_sorgente_canale` (tipo, uid, canale) | **idempotenza** | è il bersaglio dell'`ON CONFLICT` della porta |
| `uq_doc_fatt_canali_un_aperto` (tipo, uid) WHERE APERTO | **regola di dominio** | un solo canale aperto per documento (citata nel §3.4 del brief) |
| `chk_doc_fatt_canali_target_pair`, `_sorgente_uid_not_blank`, `_canale`, `_stato`, `_motivo_blocco` | forma | — |

**5. Guard:** ✅ nessun guard polimorfo; c'è `child_requires_active_parent` su entrambi i tipi.

**6. S-9 — da dove vengono i 387 orfani** (📅 PREVENTIVO 352, CONTRATTO 14, DDT 16, ORDINE 5):

* ✅ **Il percorso:** ogni INSERT di preventivo, ordine e DDT apre il suo canale (trigger). Nessun trigger DELETE e
  nessuna FK toglie il canale quando il documento sparisce.
* ✅ **Chi cancella i documenti:**
  * **preventivi**: `PreventiviRepository.delete_preventivo` (`preventivi_repository.py:659-665`), da
    `elimina_preventivo` (`preventivi_service.py:545-592`), il pattern **«abbandono bozza»** del drawer FE.
    All'apertura del drawer si crea subito la BOZZA (così il trigger apre il canale), poi la si cancella se
    l'utente esce senza righe. Il canale resta. Spiega la grandezza del numero: una bozza a ogni apertura del
    drawer abbandonata.
  * il changeSet `80_data/20260501-15-cleanup-preventivi-malformati` (`DELETE FROM vendite.preventivi WHERE
    billing_account_id IS NULL AND istanza_utility_id IS NULL`), anche lui senza toccare i canali;
  * **ordini**: `delete_ordine` (`ordini_repository.py:491-497`, abbandono bozza; guard DB
    `trgfn_doc_guard_delete_solo_bozza`);
  * **DDT**: `delete_ddt` (`ddt_repository.py:473-476`, idem).
* 🔶 **CONTRATTO 14: il codice non li spiega.** Nessun `DELETE FROM vendite.contratti` nel repo (BE, DB, pgTAP,
  smoke, changelog, brief). Due ipotesi: cancellazioni a mano su dbdev, oppure pgTAP storici caduti a metà senza
  transazione. Da guardare su dbdev con `user_insert`/`data_insert` e `meta->>'event'` dei canali orfani.
* 🔶 Un'altra fonte possibile, oggi teorica: `UPDATE OF uid` su preventivi apre un canale col nuovo uid e lascia
  quello vecchio.
* Le `target_table` (S-9): preventivi, ordini e DDT **ammettono** la cancellazione (solo in bozza). I figli con FK
  (righe, indirizzi, note) vanno in CASCADE. I figli polimorfi (canali, e da verificare `documenti_generati`)
  restano orfani. Contratti: nessun percorso di cancellazione, ma nessun guard la vieta.
* Il presidio `dbops.fn_sorgenti_orfane_perimetro` non li vedeva: pretende `sorgente_riga` e il guard tipizzato
  (brief §3.3).

**7. Lotto e note:** S-5 si applica a sorgente **e** target (ordine, DDT, contratto → id; preventivo resta uid).
Le chiamate del trigger cambiano (`NEW.id` al posto di `NEW.uid::text` per i tipi a chiave `id`). Il «lato in
uscita» del lotto 0 deve chiudere la cancellazione delle bozze. Siccome il registro non ha lettori, **Tid può
decidere** se tenerlo: se il registro va tenuto, per dominio la cancellazione della bozza dovrebbe togliere il
canale (S-9: «dentro le regole DB»).

---

#### 5. Scheda `vendite.fatture_stampa_coda` (G7)

**1. Colonne** (✅): `sorgente_tipo_id` bigint NOT NULL («oggi sempre FATTURA»), `sorgente_id` bigint NOT NULL
(«= vendite.fatture.id (FK). Chiave di delega RLS»), `sorgente_uid` text NOT NULL («convenzione key_selector
FATTURA = id::text»). Grammatica **G7**: l'id scritto due volte. È la sola tabella del perimetro che ha già
`sorgente_id bigint`.

**2. Scrittori** (✅): `vendite.fn_accoda_stampe_lotto` (`f.id, f.id::text`, `fn_accoda_stampe_lotto.md:69`).

**3. Lettori** (✅):

* `dbops.vw_fatture_stampa_coda_da_guardare` proietta le tre colonne.
* La RLS `rls_fatture_stampa_coda_ef_whitelist` e il guard `trgfn_guard_emittente_scope('fattura','sorgente_id')`
  usano **`sorgente_id`**.
* BE: `pipeline_repository.py:2700` (`RETURNING … c.sorgente_id, c.sorgente_uid`);
  `stampa_coda_drainer_service.py:293` passa `sorgente_uid=str(item["sorgente_uid"])` a `genera_documento`. 🔶 Da
  qui viene l'id della FATTURA in `documenti_generati.sorgente_uid` (la G6 «mista»).

**4. Vincoli e indici:** `ex_fatture_stampa_coda_vivo` EXCLUDE (tipo, `sorgente_id`, tipo output) WHERE
PENDING/IN_CORSO, **regola di dominio** (una stampa viva per fattura e tipo), già sulla chiave giusta.
`ix_fatture_stampa_coda_sorgente_id`. FK `fk_fatture_stampa_coda_fattura (sorgente_id) → fatture ON DELETE CASCADE`.

**5. Guard:** nessun guard polimorfo; l'FK fa da guard di esistenza (solo FATTURA).

**6. S-9:** ✅ è l'unica del perimetro con una vera FK. `vendite.fn_cleanup_fatture_by_ids` cancella le fatture e la
coda va in CASCADE. Niente orfani possibili.

**7. Lotto e note:** col §4 `sorgente_uid` diventa NULL (FATTURA ha chiave `id`) e la colonna si ritira. Il BE deve
passare `sorgente_id` al drainer, e la stessa correzione arriva a `documenti_generati` (G6). Domanda per S-8: la FK
su `sorgente_id` resta? È una FK «monomorfa» su una colonna polimorfa, regge solo finché il tipo è uno.

---

#### 6. I BB del perimetro: che cosa cambia

| BB | Oggi | Col §4 |
| --- | --- | --- |
| `vendite.fn_link_commessa_sorgente(commessa, tipo, text, riga)` | normalizza uid → `id::text`; advisory lock su `hashtext(tipo:uid)`; regola «una commessa viva» | riceve una chiave qualsiasi, la risolve col BB «che scrive» del lotto 0, scrive `sorgente_id` o `sorgente_uid`; il lock sulla chiave nuova |
| `vendite.fn_upsert_commessa_attivita` | scrive l'uid grezzo, poi chiama il link con lo stesso uid | scrive la chiave giusta più `sorgente_riga` (dalla riga della fn_list) |
| `vendite.fn_list_*_da_pushare` (5) | proiettano `<testata>.uid::text AS sorgente_uid`, `riga_id`, `fn_segment_key(CODICE, uid, riga[, mese])` | proiettano tipo, chiave e riga; `segment_key` (🔶) resta sull'uid per non cambiare le chiavi salvate |
| `vendite.fn_commessa_viva_di_sorgente(tipo, text)` | uguaglianza sulla chiave canonica | firma con le due chiavi (o la chiave risolta) |
| `vendite.fn_ritira_commessa_attivita_da_sorgente(tipo, text uid, …)` | `ca.sorgente_uid = v_uid` | sulla chiave nuova; i chiamanti (`fn_documento_ritira_legami`, `fn_documento_legami`) smettono di rileggere `d.uid::text` |
| `vendite.fn_documento_lineage_legami` | CASE per arco B/E/F/U che rilegge l'uid da preventivi, ordini, contratti e DDT | il CASE sparisce: `ca.sorgente_id = <id>` o `ca.sorgente_uid = <uid>` dal risolutore |
| `vendite.fn_documento_lineage_archi` | **altri** CASE per tipo su `commesse_sorgenti` (`::uuid` / `::bigint`) | idem (non era nel §3.4 del brief) |
| `vendite.fn_get_sorgente_documento_ref(tipo, text)` | prova uuid poi id: legge le due grammatiche | diventa (o chiama) il BB «che risolve» del lotto 0 |
| `vendite.fn_set_documento_canale_stato(tipo, text, canale, stato, target_tipo, target_text, …)` | testo, uid | due coppie tipizzate; ON CONFLICT e indice parziale sulla chiave nuova (`NULLS NOT DISTINCT`) |
| `vendite.fn_build_gruppo_fatturabile_key(tipo, uid, commessa)` | `CODICE:<uid>` | ⚠️ §R-1 |
| `script.fn_segment_key(sorgente, uid, riga, mese)` / `_sorgente` / `_riga` | costruttore unico; `_riga` legge `:R:(\d+)` | non è una colonna `sorgente_*`, ma porta la provenienza (V8). Dopo il lotto la riga si legge dalla colonna; `fn_segment_key_riga` resta per ONERE e RETTIFICA |

---

#### S-7 — L'impronta di `attivita_fatturabili.sorgente_uid`

##### S-7.1 Ogni lettore, uno per uno

Ricerca su: corpo di tutte le funzioni (`prosrc`, e `pg_get_functiondef` per le 86 `BEGIN ATOMIC`), tutte le viste
(nessuna materializzata), le policy RLS, il BE (Python con SQL raw, test compresi), il FE, i pgTAP, gli smoke
`backend/scripts/tests`, `scripts/`. Gli alias si sono letti nel contesto (`a.`, `af.`, `ca.`, `cs.`, `r.`, `c.`).

| # | Dove | Che cosa fa con `attivita_fatturabili.sorgente_uid` | Esito |
| --- | --- | --- | --- |
| L1 | `vendite.fn_emit_attivita_fatturabili_da_commessa` (`fn_emit…md:215-226`) | calcola `md5(v_row.segment_key)` come uuid e cerca `a.sorgente_tipo_id = COMMESSA AND a.sorgente_uid = <impronta> FOR UPDATE`. Trovata: ramo UPDATE (o `E_RIGA_GIA_FATTURATA`). Non trovata: ramo INSERT. Conta anche `inserted`/`updated` del dry-run | **USO VERO, l'unico** |
| L2 | `vendite.fn_resolve_termini_pagamento` (`.md:62`, `:114`, `:125`) | carica `a.sorgente_uid` in `v_sorgente_uid`, ma lo usa solo se il codice è ORDINE_VENDITA o PREVENTIVO. Per le AF (sempre COMMESSA) lo **sovrascrive** con l'uid di `commesse_attivita` oppure non lo usa | letto, **mai usato** |
| L3 | `vendite.vw_preventivi_smistamento_righe` (`views/vw_preventivi_smistamento_righe.md:37,40`) | `af.sorgente_uid = p.uid AND af.sorgente_riga = pr.id` (senza il tipo) | letto con la **grammatica sbagliata**: l'impronta non è mai l'uid del preventivo, e `sorgente_riga` è l'id della riga di commessa. **Il ramo è morto** (§S-7.4) |
| L4 | `vendite.fn_select_attivita_fatturabili` (`RETURNING a.*` / `SELECT a.*`, `.md:117,119`) | restituisce la riga intera | il chiamante BE (`pipeline_repository.py:1749`) **scarta** il risultato |
| L5 | BE `PipelineRepository.list_attivita_da_fatturare` (`pipeline_repository.py:1825, 1861`) | `a.sorgente_uid` nel dataclass `AttivitaDaFatturare.sorgente_uid` (`:190`) | il consumatore unico `fatture_righe_service.py` **non lo legge** (✅ grep: nessuna occorrenza di `sorgente`; niente `asdict`/`getattr`). Le righe di fattura prendono la sorgente a NULL in SQL (`pipeline_repository.py:3500-3503`) |
| L6 | BE test `test_fatture_righe_service.py:243` | costruisce il dataclass con `sorgente_uid=f"SRC-{id}"` | fixture, non lettore |
| — | `dbops.fn_sorgenti_orfane_perimetro` | il perimetro pretende il guard tipizzato: AF ne è **fuori** | non legge |
| — | `script.trgfn_storico_generic` | copia la riga nello storico | copia, non lettore |
| — | smoke `_smoke_fatturazione.py:268-282`, `smoke-push-termine-documento-commessa.py:413-425` | **scrivono** `uuid.uuid4()` | scrittori di prova |
| — | pgTAP (49 file con AF e `sorgente_uid`) | nessun `af.`/`a.sorgente_uid`, nessun `md5(…segment_key…)`; le occorrenze nude sono liste di INSERT (`test-attivita-fatturabili.sql:683,741`, `test-fatturazione-draft.sql:127`) o colonne di `commesse_attivita`/`commesse_sorgenti` | nessun lettore |
| — | FE | nessuna occorrenza | — |
| — | `sorgente_riga` di AF | lettori: solo L3 (`script.fn_check_disponibilita_uscita` è un falso positivo, `p_sorgente_riga`) | — |

Le occorrenze vicine **di altre tabelle**, da non confondere: `fn_fattura_origini`, `fn_list_commessa_attivita`,
`fn_esito_gruppi_giro`, `fn_select_attivita_fatturabili` (filtro `p_gruppi`), `fn_gruppi_di_commessa_nel_lotto`,
`vw_dash_competenza_attivita`, `vw_lotti_gruppi_serviti`, `vw_lotto_documento_righe` leggono **`ca.sorgente_uid`**
(`commesse_attivita`); `fn_annulla_reso` legge `resi.sorgente_uid`; `fn_accredita_riga_reso` passa
`p_sorgente_uid => NULL` all'upsert della commessa.

##### S-7.2 Perché è nata (storia)

1. **2025-10-05** `20251005-03`: `sorgente_uid uuid`, commento «Origine import (uid)», più
   `uq_attivita_fatturabili_v_sorgente_fk (sorgente_tipo_id, sorgente_uid) WHERE tipo NOT NULL`, «Idempotenza
   import».
2. **2026-02-24** `20260224-13` (commit `b44c924846`): nasce `fn_emit`, «idempotenza su sorgente COMMESSA +
   segment_key», «sorgente AF sempre COMMESSA + hash(segment_key)». La colonna era `uuid` e c'era l'indice unico
   su (tipo, uid): la chiave testuale `segment_key` doveva diventare un uuid deterministico. È il motivo della
   nascita (🔶 ricostruito, coerente con `gestione-commesse-v2.md:759, 1850-1851`).
3. **Lo stesso giorno** `20260224-42`: tolto quell'indice unico; nasce
   `uq_attivita_fatturabili_commessa_attivita` («unicità tecnica riga AF emessa da commessa_attivita») e
   `commessa_attivita_id` diventa NOT NULL. **Dal 2026-02-24 l'idempotenza vera è `commessa_attivita_id`**; la
   ricerca per impronta è rimasta.
4. **2026-02-25** `20260225-45`: tolto il guard polimorfo su AF, perché «la FK `commessa_attivita_id` copre già
   la validazione». L'impronta non si risolve contro `config.sorgenti`, per costruzione
   (`brief-db-guard-sorgente-polimorfa` §1e R2).
5. **2026-07-18** `brief-db-guard-sorgente-polimorfa` §1d: «hash md5(segment_key), idempotenza pull, fuori da questo
   brief»; D6: resta staccato.
6. **Caveat C1** (`brief-db-fatturazione-due-lenti` §2.3): la ricerca **non filtra per commessa**. Una collisione
   di `segment_key` fra commesse diverse riaggancerebbe l'AF di un'altra commessa. «Oggi nessun percorso di
   produzione lo genera.»
7. **2026-09-04** (`brief-residuo-fatturabili…` :370-385) e `brief-db-lavoro-che-non-torna-indietro` :970-974: la
   ricerca per impronta è **la ragione per cui `fn_libera_attivita_fatturabili` libera invece di cancellare**. Il
   giro dopo ritrova l'AF e la aggiorna. Si cita come il motivo per cui la ripresa regge anche su RETTIFICA e
   ONERE, che non hanno sorgente.
   🔶 Lo stesso vale con `commessa_attivita_id`, che ogni riga ha (NOT NULL).
8. **2026-10-20** `brief-db-grammatica-unica-documenti` 2e: cambio di formato delle chiavi (`PREV:`→`PREVENTIVO:`
   …) con lo SQL una tantum `work-in-progress/sql-una-tantum-2e-chiavi-e-registri.sql`. Il passo 1 riscrive
   `commesse_attivita.segment_key` (350); il passo 2 riscrive `attivita_fatturabili.meta->>'segment_key'` (62),
   con la frase «nessuno le usa per ritrovare una riga». **Nessun passo ricalcola `attivita_fatturabili.sorgente_uid`.**
   Su dbdev è stato eseguito con COMMIT da Tid (§13 del brief).

##### S-7.3 Il cambio di formato rompe la ricerca? Che cosa succede allora

* ✅ **La ricerca manca le righe.** Per ogni AF emessa prima del 2026-10-20 la `segment_key` della sua riga di
  commessa è cambiata, l'impronta salvata no, quindi `md5(segment_key nuova) ≠ sorgente_uid`. 📅 Il §6.1 del brief
  misura «md5(segment_key) coincide su 2 righe di 64»; lo SQL una tantum ha riscritto 62 copie nel `meta`.
  **62 + 2 = 64**: le 62 sono le AF di prima del cambio, le 2 sono nate dopo (o hanno una chiave `MAN`, che non è
  cambiata). La formula **non** è un'altra: è la stessa su una chiave cambiata. Da confermare su dbdev:
  `md5(ca.segment_key)` contro `af.sorgente_uid` e contro `md5(af.meta->>'segment_key')` con la mappa vecchia.
* 🔶 **Quando morde.** Serve un'AF di prima del 2026-10-20 **non fatturata** la cui riga di commessa torni
  `NON_EMESSA` con classe PRONTA. Lo fanno `fn_libera_attivita_fatturabili` (`.md:119`, tiene l'AF e rimette la
  riga a NON_EMESSA) e chi la chiama: lo storno dal lotto, `fn_cleanup_fatture_by_ids`, gli annulli del reso e la
  porta «Elimina dal lotto». Al giro dopo `fn_emit` non trova l'AF e fa INSERT con lo stesso
  `commessa_attivita_id`, e `uq_attivita_fatturabili_commessa_attivita` rifiuta con **23505**. Non è un codice
  registrato, quindi esce come errore generico. La commessa fallisce a ogni giro (residuo che non si riprende
  più). Il dry-run conta `inserted` al posto di `updated`. Un'AF già fatturata non è toccata: la riga resta EMESSA
  e non rientra.
* ✅ **Da zero (CI, scratch)** il caso non esiste: le chiavi nascono già nella forma nuova. I pgTAP che provano la
  ri-emissione (per esempio `test-commesse-core-functions-v1.sql` «Rerun emit…», la sentinella C1) restano verdi:
  non cambiano mai la chiave fra due emissioni.
* ⚠️ **Il rischio torna** a ogni cambio della `segment_key`. Il lotto commesse di questo brief potrebbe portarne uno
  (S-5: la chiave contiene l'uid).

##### S-7.4 Il ramo morto di `vw_preventivi_smistamento_righe`

✅ Gli stati `FATTURATA` ed `EMESSA_AF` cercano un'AF con `sorgente_uid = preventivo.uid` e `sorgente_riga =
riga del preventivo`. Nessuno scrittore produce un'AF così (l'unico, `fn_emit`, scrive COMMESSA, impronta e id della
riga di commessa). Il ramo non scatta mai. La riga cade su `IN_COMMESSA`, se il segmento non è LIBERA. Consumatori
vivi: `PreventiviSmistamentoDialog.vue:148`, `frontend/src/vendite/constants.js:175-181`, i servizi preventivi e
ordini. pgTAP: `test-vw-preventivi-smistamento-v1.sql` non prova `FATTURATA` né `EMESSA_AF`. Storia del predicato:
`525b8847f4` (2026-04-03), `e14ecde04a` (2026-06-12). È un errore di lettura da correggere nello stesso lotto, con
la catena `commesse_attivita` → AF per `commessa_attivita_id`, e la riga del preventivo da `segment_base` o dalla
nuova `sorgente_riga` di `commesse_attivita`.

##### S-7.5 Conclusione

**Usata solo da `fn_emit_attivita_fatturabili_da_commessa`, per ritrovare la riga AF già emessa dalla stessa riga di
commessa** (la ripresa dei residui). Nessun altro la usa: due lettori la caricano senza servirsene (L2, L5), uno la
legge con una grammatica sbagliata e non trova mai niente (L3), uno la restituisce a un chiamante che la scarta (L4).

* **Certezza:** alta per DB (catalogo intero, anche `BEGIN ATOMIC`, viste, policy), BE, FE e pgTAP. Il lavoro
  dell'impronta lo fa già `commessa_attivita_id` (FK NOT NULL + UNIQUE 1:1): `WHERE a.commessa_attivita_id =
  v_row.id`. È anche più corretto: niente C1 e niente dipendenza dal formato della chiave, e ripara le 62 righe di
  dbdev senza toccarle.
* **Che cosa ne segue (proposta, la decisione è di Tid):** S-7 diceva «l'impronta va in una colonna sua». Il
  censimento dice che **non serve una colonna**: basta cambiare la ricerca. L'impronta si ritira con la colonna
  (o con il suo valore, se `sorgente_uid` resta per il modello).
* **Resta da verificare:**
  1. sul **catalogo di dbdev** (qui è lo scratch) la stessa ricerca, `prosrc ILIKE '%attivita_fatturabili%' AND ILIKE
     '%sorgente_uid%'`, che deve dare le stesse 13 funzioni e 4 viste;
  2. su dbdev, il conteggio delle AF non fatturate con impronta stantia (quelle esposte a §S-7.3);
  3. che nessuno script fuori dal repo (job pgAgent, report a mano, `dbdev.session.sql`) legga la colonna. Nel repo
     non ce n'è.

---

#### R. Ricadute e domande per Tid

* **R-1 (S-5 su `commesse_attivita`): la chiave dei gruppi è salvata.** `fn_build_gruppo_fatturabile_key` usa
  `ca.sorgente_uid`, e le chiavi vivono in `fatturazione_lotti_gruppi`, `_esiti` e `_log`, lette da
  `vw_commesse_attivita_emittibilita` (trattenute: `t.gruppo_key = fn_build…(ca…)`), `fn_esito_gruppi_giro` e
  `p_gruppi` dal BE. Convertire la colonna senza convertire le chiavi salvate stacca i trattenimenti dei lotti in
  corso, in silenzio (zero righe). Due strade: la chiave del gruppo continua a costruirsi con l'uid (risolto dal
  BB), oppure si convertono anche le chiavi salvate. Per `segment_key` c'è la stessa scelta (S-7.3).
* **R-2 (S-9 canali):** il registro canali non ha lettori. Va deciso se tenerlo. Se resta, la cancellazione delle
  bozze (BE «abbandono bozza») deve portarsi via il canale dentro il DB. Lo stesso controllo serve per
  `documenti_generati` (fuori dal mio perimetro).
* **R-3 (S-8): candidati a «non rientra» o «ridondante», col motivo.**
  `attivita_fatturabili.sorgente_*` col §4 sarebbe la copia di `commessa_id` e `commessa_attivita_id` (FK NOT
  NULL). `sorgente_origine_tipo_id` è il tipo di business senza chiave, che si ricava da `commesse_attivita` con la
  FK. `fatture_stampa_coda.sorgente_id` è già una FK vera (CASCADE) verso la sola FATTURA.
* **R-4 (BE, percorso intero da scrivere nel brief):** il parametro BE `sorgente_uid: int` (id del documento) in
  `fetch_pushable_rows` e `pr_run_commesse_push_one` va rinominato quando cambia la colonna. Il drainer della coda
  di stampa deve passare `sorgente_id`. Il dataclass `AttivitaDaFatturare` perde `sorgente_uid` e `sorgente_riga`,
  che nessuno usa.
* **R-5 (doc stantia, nello stesso lotto):** il manuale di `attivita_fatturabili` (:27, :78-79, :116, :195) dà per
  vivo l'indice unico ritirato il 2026-02-24. Il manuale di `commesse_attivita` (:66-67) cita un join di
  `vw_dash_fatturazione_contratti` che non c'è più. Il commento di colonna di `attivita_fatturabili.sorgente_uid`
  («Origine import (uid)») è falso.

### Censimento — magazzino e acquisti (brief-db-sorgente-documento-e-riga §7.1)

> **Chi:** team DB, sessione di censimento in sola lettura, 2026-11-06.
> **Fonti:** cataloghi di dbdev (`pg_constraint`, `pg_index`, `pg_trigger`, `pg_proc`, `pg_get_functiondef`,
> `information_schema`, letti con `db/internal.ruoli.env`), manuali `docs/it/dbzero/<schema>/manual/`, BE
> `backend/apps`, FE `frontend/src`, pgTAP `db/pgtap`. Nessun YAML usato per la struttura (solo
> `public.databasechangelog` per lo stato di applicazione del lotto A).
> **Legenda:** ✅ FATTO VERIFICATO (dove: file:riga, oppure oggetto DB) · 🔶 IPOTESI / PROPOSTA.
> **Dati:** con il ruolo di `internal.ruoli.env` tutte le tabelle del perimetro risultano a 0 righe (fatto datato,
> letto sotto la RLS di quel ruolo: non è un motivo e non è una misura del dominio).
> **Modello di riferimento:** §4 + S-3: `sorgente_tipo_id` (documento) + `sorgente_id bigint` | `sorgente_uid uuid`
> (secondo `key_selector`) + `sorgente_riga` (riga del documento, NULL = documento intero) + solo su
> `magazzino.movimenti` / `movimenti_attesi` `sorgente_dettaglio` (la riga della riga).

---

#### 0. In una pagina

1. ✅ **Il magazzino scrive oggi sempre la FOGLIA, mai il documento.** I sei scrittori del registro mettono in
   `sorgente_riga` l'id del record più basso (prelievo, rientro, riga d'inventario/rettifica/trasferimento) con un tipo
   `*_RIGA` / `*_PRELIEVO` / `*_RIENTRO`. Nessuno scrive `sorgente_uid` su magazzino. È G2 «puro»: chiave = foglia.
2. ✅ **`uq_mag_movimenti_identita` è l'idempotenza della registrazione per foglia + causale + tranche**, con due
   dipendenti: il controllo esplicito al passo 10 di `fn_scrivi_movimento` (`E_MAG_MOVIMENTO_GIA_REGISTRATO`) e il
   confronto di specchio dello storno al passo 9. **Nessun `ON CONFLICT`** lo usa. Con S-3 resta equivalente **solo se il
   guard garantisce la catena** dettaglio ∈ riga ∈ documento **e** se per ogni tipo il livello scritto è fisso (§2).
3. ✅ **Nessuno scrive le testate di magazzino** (`inventari`, `rettifiche`, `trasferimenti`) né `eventi_assets` né
   `movimenti_attesi` con sorgente: BE e DB solo le leggono. **Nessuno scrive `EVENTO_ASSET`** come sorgente di un
   movimento (l'operazione «non esiste», manuale `eventi_assets`). Su acquisti **nessuno scrive niente**: nessuna
   funzione DB, `backend/apps/acquisti` è vuota.
4. ⛔ **Trappola di ritiro (S-2/S-3):** tre verbi leggono il tipo **senza** `attivo` e, se non lo trovano, **saltano in
   silenzio lo storno** (`vendite.fn_cambia_stato_ddt`, `vendite.fn_annulla_reso`) o lo leggono per il costo
   (`vendite.fn_posta_reso`). Ritirare/cancellare `DDT_VENDITA_PRELIEVO`/`RESO_VENDITA_RIENTRO` prima di aver
   riscritto i verbi = annullo di bolla/reso che non storna il magazzino, senza errore. Spegnerli (`attivo=false`)
   prima della conversione = ogni storno rifiutato dal guard (che vuole il tipo attivo).
5. ⛔ **S-9, un buco vero:** `vendite.resi` **non ha un guard di DELETE** di testata (gli altri documenti sì:
   `trgfn_doc_guard_delete_solo_bozza` su `ddt`, `documento_interno_guard_transizione` sulle testate di magazzino).
   La regola «si cancella solo la bozza senza righe» vive **solo nel BE** (`resi_service.elimina_reso`,
   `backend/apps/vendite/services/resi_service.py:582-598`). Un `DELETE` di un reso CONFERMATO (grant DELETE a
   `zeroerp_app`) va in cascata su `resi_righe` → `resi_righe_rientri` (il lock di riga «padre assente = cascade»
   passa) e lascia **movimenti `RESO_VENDITA_RIENTRO` orfani**.
6. ✅ **Il BE traduce già a mano «documento → righe» per il registro:** `list_movimenti(documento_sorgente=…)`
   (`backend/apps/magazzino/db/magazzino_repository.py:989-997`) cerca i movimenti di un inventario con un `EXISTS`
   sulle righe. Col modello diventa `sorgente_tipo = INVENTARIO AND sorgente_id = :id`. Stessa traduzione in
   `dbops.vw_ddt_emessi_senza_scarico` / `vw_resi_confermati_senza_carico` e nei verbi di storno (raccolgono
   l'array dei prelievi della bolla).
7. ✅ **Il catalogo ha già i tipi-documento giusti** per il magazzino e gli acquisti: `INVENTARIO` (25),
   `RETTIFICA` (26), `TRASFERIMENTO` (27), `ORDINE_ACQUISTO` (23), `DDT_ACQUISTO` (24), tutti `key_selector='id'`,
   scope `CATALOGO`, nati il 2026-10-19. Mancano solo i livelli `target_righe_table` / `target_dettaglio_table`.
8. ✅ **Acquisti:** testate e `ordini_righe` sono G1 «import» (indici unici «Idempotenza import» con nome `_v_` copiato
   da vendite); `acquisti.ddt_righe` ha il modello A del lotto A (applicato su dbdev: `20261105-03` EXECUTED) **senza
   guard polimorfo e senza CHECK di esclusività**; esiste un `ORDINE_ACQUISTO` ma **non** un `ORDINE_ACQUISTO_RIGA`,
   quindi il commento di colonna («la riga dell'ordine d'acquisto», chiave in `sorgente_riga`) oggi **non è
   scrivibile**: lo diventa solo col modello §4.
9. ✅ **S-8 in acquisti** (non censito nel §3.1-bis): `acquisti.ddt.ordine_id` (FK, parallela a `sorgente_*`) e
   `acquisti.ordini_righe_fulfillment` (ponte con quantità). Il ponte d'acquisto è **`ON DELETE CASCADE`** sui due lati,
   quello di vendita **`RESTRICT`**: il «va verificato» del manuale `ordini_righe_fulfillment` ha la risposta, ed è
   «non vale la stessa policy».
10. 🔶 **S-10:** l'ipotesi del brief regge sul modello (vedi §9), con una precisazione: il catalogo deve dire anche il
    **livello obbligatorio per consumatore** (il registro vuole sempre la foglia), non solo «ha righe o no».

---

#### 1. Schede tabella

Per ogni tabella: (1) colonne e grammatica · (2) scrittori · (3) lettori · (4) default/CHECK/unici · (5) guard ·
(6) S-9 · (7) note e lotto.

##### 1.1 `magazzino.movimenti` — il registro

**(1) Colonne** ✅ (`information_schema`, commenti di colonna):

| Colonna | Tipo | Null | Default | Commento (sintesi) |
| --- | --- | --- | --- | --- |
| `sorgente_tipo_id` | bigint | **NOT NULL** (D-6) | — | «Il TIPO di record che ha generato il movimento (DDT_VENDITA_RIGA, INVENTARIO_RIGA, RETTIFICA_RIGA, TRASFERIMENTO_RIGA, EVENTO_ASSET, …)» |
| `sorgente_riga` | bigint | sì | — | «Chiave del record sorgente quando key_selector = id. Esattamente una fra sorgente_riga e sorgente_uid» |
| `sorgente_uid` | uuid | sì | — | idem per `uid` |

⚠️ Il commento di `sorgente_tipo_id` nomina `DDT_VENDITA_RIGA`, che **nessuno scrive** sul registro: lo scrittore vero
è `DDT_VENDITA_PRELIEVO`. Commento stantio.

Grammatica oggi: **G2, chiave = foglia** (il record più basso dell'operazione). Significato (manuale `movimenti.md`
§«Le quattro regole», 1): «ogni movimento dice *quale operazione* lo ha generato».

**(2) Scrittori** ✅ — tutti passano da `magazzino.fn_scrivi_movimento` (unica porta, `INSERT` al passo 13):

| Verbo | Tipo scritto | `sorgente_riga` = | Causale | Posizione |
| --- | --- | --- | --- | --- |
| `vendite.fn_posta_ddt(…,'USCITA')` (da `fn_cambia_stato_ddt` all'emissione) | `DDT_VENDITA_PRELIEVO` (21) | `ddt_righe_prelievi.id` | `fn_ddt_causale_magazzino` (vendita, `TRASF_OUT`, …) | lotto/asset/ubicazione del prelievo; `transfer_uid = ddt.uid` se `TRASF_OUT` |
| `vendite.fn_posta_ddt(…,'ARRIVO')` (consegna bolla di trasferimento) | `DDT_VENDITA_PRELIEVO` | `ddt_righe_prelievi.id` (lo **stesso** prelievo) | `TRASF_IN` | `ubicazione_arrivo_id`, magazzino d'arrivo |
| `vendite.fn_posta_reso` | `RESO_VENDITA_RIENTRO` (22) | `resi_righe_rientri.id` | `CARICO_RESO_VEN` | lotto/asset dal prelievo d'origine, ubicazione del rientro |
| `magazzino.fn_posta_inventario` | `INVENTARIO_RIGA` (17) | `inventari_righe.id` (dal piano) | dal piano (`causale_codice_interno`) | della riga |
| `magazzino.fn_posta_rettifica` | `RETTIFICA_RIGA` (18) | `rettifiche_righe.id` | `RETT_POS`/`RETT_NEG` | della riga |
| `magazzino.fn_posta_trasferimento` | `TRASFERIMENTO_RIGA` (19) | `trasferimenti_righe.id`, **due volte** | `TRASF_OUT` + `TRASF_IN` | `ubicazione_id_da` / `_a`, `transfer_uid = trasferimenti.uid` |
| `magazzino.fn_storna_movimenti_sorgente` (da `fn_cambia_stato_ddt` all'annullo, `fn_annulla_reso`) | **copia** dell'originale | **copia** | `STORNO_POS`/`STORNO_NEG` | copia; `storno_di_movimento_id` |
| — `EVENTO_ASSET` (20) | **nessuno** | — | (`ASSET_INSTALL`/`ASSET_RIENTRO` esistono in `causali`) | — |

Nessuno scrive `sorgente_uid` sul registro. BE: nessuna scrittura diretta (le famiglie chiamano `fn_posta_*`).

**(3) Lettori** ✅

* DB:
  * `fn_scrivi_movimento` passo 9 (storno: `sorgente_tipo_id`, `sorgente_riga`, `sorgente_uid` uguali all'originale) e
    passo 10 (identità, `IS NOT DISTINCT FROM` sulla 7-upla);
  * `fn_storna_movimenti_sorgente(p_tipo, p_righe bigint[])`: `WHERE sorgente_tipo_id = p AND sorgente_riga = ANY(p_righe)`;
  * `vendite.fn_posta_reso`: rilegge il costo dell'uscita d'origine con `sorgente_tipo_id = DDT_VENDITA_PRELIEVO AND
    sorgente_riga = prelievo_id AND qta < 0 AND storno_di_movimento_id IS NULL`;
  * `script.fn_check_disponibilita_uscita`: riceve la sorgente di chi chiede (tipo, riga, uid) e la confronta con gli
    attesi (vedi 1.2);
  * viste `dbops.vw_ddt_emessi_senza_scarico` (`m.sorgente_riga = p.id` + `codice_interno = 'DDT_VENDITA_PRELIEVO'`),
    `dbops.vw_resi_confermati_senza_carico` (idem con `RESO_VENDITA_RIENTRO`), `dbops.vw_magazzino_movimenti_senza_costo`
    (proietta le tre colonne);
  * `dbops.fn_sorgenti_orfane` / `_perimetro` (dinamico, legge `sorgente_riga` come chiave del `target_table`);
  * `script.fn_resolve_emittente_fiscale_id('movimento', …)`: non legge la sorgente (dal magazzino).
* BE:
  * `MagazzinoRepository._MOVIMENTI_SELECT` (`backend/apps/magazzino/db/magazzino_repository.py:382-390`) proietta
    `sorgente_tipo_id`, `sorgente_codice_interno`, `sorgente_riga`, `sorgente_uid`;
  * `list_movimenti`: filtro `sorgente_codice_interno` (`:986-988`) e **traduzione a mano documento → righe**
    `documento_sorgente` (`:989-997`, `EXISTS (… r.id = mv.sorgente_riga AND r.{fk_riga} = %s)`), alimentata da
    `consultazione_service` (`backend/apps/magazzino/services/consultazione_service.py:153-157`) coi parametri
    `inventario_id` / `rettifica_id`;
  * API: parametro `sorgente_tipo` = `config.sorgenti.codice_interno` (`backend/apps/magazzino/api/views.py:845`,
    descrizione OpenAPI `:863` «INVENTARIO_RIGA, RETTIFICA_RIGA, …»);
  * tipi: `MovimentoRow` (`backend/apps/magazzino/types.py:212-215`).
* UI a catalogo: `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv:865-866` (colonne
  `sorgente_codice_interno` «INVENTARIO_RIGA, RETTIFICA_RIGA, …» e `sorgente_riga` «L'id della riga del documento
  sorgente»).
* FE: `frontend/src/magazzino/vocabolari.js:62-66` (`SORGENTE_MOVIMENTO = {INVENTARIO_RIGA, RETTIFICA_RIGA}`),
  `:112`, `:131` (sorgente della famiglia), filtro e cella in `components/MovimentiSearchTable.vue:71,197-200`,
  deep-link `inventario_id`/`rettifica_id` in `stores/movimenti.js:36-39`, `views/MovimentiView.vue`; etichette
  `locales/it.json:5222-5223`, `locales/en.json:5222-5223` (chiavi `magazzino.movimenti.sorgente.INVENTARIO_RIGA` …).
* pgTAP (12 file che leggono la sorgente del registro): `magazzino/test-movimenti-vincoli-v2.sql` (casi 11-15
  sull'identità e lo storno), `test-fn-scrivi-movimento-controlli-v1.sql` (`E_MAG_MOVIMENTO_GIA_REGISTRATO`),
  `test-fn-scrivi-movimento-disponibilita-v1.sql`, `-valore-v1`, `-seriali-v1`, `test-porta-ledger-v1.sql`,
  `test-ddt-scarico-v1.sql`, `test-ddt-trasferimento-v1.sql`, `test-reso-carico-v1.sql`,
  `test-reso-carico-kit-seriali-v1.sql`, `test-valore-giacenza-divergenza-owner-v1.sql`,
  `test-blocco-manuale-e-porta-lotto3-v1.sql` (storno), `dbops/test-sorgenti-orfane-v1.sql`,
  `rls/test-rls-magazzino-perimetro-v1.sql`, `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1.sql`.

**(4) Default, CHECK, unici** ✅

| Oggetto | Definizione | Classificazione |
| --- | --- | --- |
| `chk_mag_movimenti_sorgente_chiave` | `(sorgente_riga IS NOT NULL) <> (sorgente_uid IS NOT NULL)` | forma (modello A): si riscrive «una sola chiave di documento» |
| NOT NULL su `sorgente_tipo_id` | D-6 | regola di dominio (resta) |
| `uq_mag_movimenti_identita` | `(sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id) NULLS NOT DISTINCT` | **regola di dominio** (idempotenza della registrazione), vedi §2 |
| `uq_mag_movimenti_storno_di` | `(storno_di_movimento_id)` | regola di dominio, non tocca la sorgente |
| nessun indice di ricerca sulla sorgente oltre l'unico | — | 🔶 i lettori «per documento» (§2.4) vorranno il prefisso `(sorgente_tipo_id, sorgente_id)`: l'unico nuovo lo dà se la colonna è seconda |

**(5) Guard e trigger** ✅: `trg_movimenti_a10_guard_sorgente_ins_upd` (`script.trgfn_guard_sorgente_polimorfa_tipizzata`,
`BEFORE INSERT OR UPDATE OF sorgente_tipo_id, sorgente_riga, sorgente_uid`); `trg_movimenti_a10_sorgenti_require_attivo_ins_upd`
(constraint trigger deferred, `config.sorgenti.attivo`). Il guard tipizzato è INVOKER, verifica solo che la foglia esista
nel `target_table` (`EXECUTE … WHERE id = $1`), rifiuta il tipo spento (`attivo = true` nella SELECT del catalogo).

**(6) S-9** — vedi §6 (bersagli per tipo).

**(7) Note** ✅: il registro non ha `attivo` né DELETE logico (manuale «Un ledger non si spegne: si storna»).
`magazzino_id` **non** è nella chiave d'identità (le righe OUT/IN di un trasferimento si distinguono per causale).
⛔ Vincolo d'anello: `dbops.vw_magazzino_dipendenze_inverse` (CANCELLO, rosso in CI via
`db/pgtap/magazzino/test-registro-non-nomina-i-consumatori-v1.sql`) vieta che un oggetto di `magazzino` nomini
`vendite`/`acquisti`/`pagamenti`: il nuovo guard, il nuovo storno e il lato «in uscita» del registro devono restare
**guidati dal catalogo** (`config.sorgenti`), mai con un `JOIN vendite.…` scritto in `magazzino`.
**Lotto:** famiglia «magazzino» (registro + attesi), dopo il lotto 0; insieme ai verbi di `vendite` che scrivono il
registro (`fn_posta_ddt`, `fn_posta_reso`, `fn_cambia_stato_ddt`, `fn_annulla_reso`), perché tipo e storno cambiano
nello stesso passo.

##### 1.2 `magazzino.movimenti_attesi`

**(1)** ✅ `sorgente_tipo_id` bigint null («Il documento che genera l'attesa, se c'è. NULL = attesa senza documento
(blocco manuale)»); `sorgente_riga` bigint null, `sorgente_uid` uuid null, **senza commento**. Grammatica G2.
Il commento dice già «il documento»: è il modello §4 nella parola, G2 nella forma.

**(2) Scrittori** ✅: `magazzino.fn_apri_blocco` scrive **solo** blocchi manuali, **senza sorgente** (il corpo non nomina
`sorgente_*`). Nessuno scrive un'attesa con sorgente (la «merce prelevata non ancora uscita» del manuale non ha ancora
verbo).

**(3) Lettori** ✅: `fn_libera_blocco` (`AND a.sorgente_tipo_id IS NULL`: libera solo i manuali);
`script.fn_check_disponibilita_uscita` (righe 159-170 del corpo: esclude gli attesi «della stessa sorgente» con
`a.sorgente_tipo_id = p_tipo AND a.sorgente_riga IS NOT DISTINCT FROM p_riga AND a.sorgente_uid IS NOT DISTINCT FROM
p_uid`); `vw_disponibilita` (somma tutti gli attesi APERTA in uscita, non legge la sorgente); BE `_BLOCCHI_SELECT`
(`magazzino_repository.py:348-362`), `BloccoRow` (`types.py:175-188`), FE `DisponibilitaBlocchiPopover.vue:103`;
pgTAP `magazzino/test-movimenti-attesi-forma-v1.sql`.

**(4)** ✅ `chk_mag_movimenti_attesi_sorgente_chiave` (tipo NULL ⇒ nessuna chiave; tipo ⇒ esattamente una),
`chk_mag_movimenti_attesi_data_solo_senza_documento`, `chk_mag_movimenti_attesi_per_chi` (tipo o soggetto o nota).
**Nessun indice unico sulla sorgente** (corretto: un documento può generare più attese). Classificazione: CHECK di forma
→ riscritti sul modello; i due CHECK di dominio restano (leggono solo `sorgente_tipo_id IS NULL`).

**(5)** ✅ guard tipizzato + `require_attivo`, come il registro.

**(6)** nessun bersaglio scritto oggi.

**(7)** 🔶 **Punto di modello per S-3:** il confronto «stessa sorgente» di `fn_check_disponibilita_uscita` oggi è
un'uguaglianza sulla terna. Un'attesa nascerà al livello **riga** (la riga d'ordine o di bolla prenotata) e il
movimento che la consuma al livello **dettaglio** (il prelievo): con l'uguaglianza a quattro colonne il movimento non
riconoscerebbe più come «propria» l'attesa del suo documento e la conterebbe come altrui. La regola va scritta come
**prefisso**: l'attesa è propria se tipo + documento coincidono e i livelli che l'attesa valorizza coincidono
(`a.sorgente_riga IS NULL OR a.sorgente_riga = p_riga`, idem per il dettaglio). È una decisione di dominio («di chi è
l'attesa»), non un dettaglio tecnico. Lotto: famiglia magazzino, con il registro.

##### 1.3 `magazzino.inventari` · 1.4 `magazzino.rettifiche` · 1.5 `magazzino.trasferimenti` (le tre testate)

Uguali nella forma; le differenze sono indicate.

**(1)** ✅ `sorgente_tipo_id` bigint null (commento «FK → config.sorgenti(id)» su trasferimenti, assente su inventari e
rettifiche); `sorgente_uid` uuid null (commento «Identificatore esterno documento» su trasferimenti, assente sugli
altri); `sorgente_riga` bigint null («Chiave del record sorgente quando key_selector = id; con sorgente_uid esattamente
una, e solo se sorgente_tipo_id»). Significato (manuali `inventari.md:53-59`, `rettifiche.md:38-…`,
`trasferimenti.md:68-74`): «la sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è uno».
Grammatica G2.

**(2) Scrittori** ✅: **nessuno**. Il BE crea la testata con `magazzino_id`, `data`, `descrizione`, `meta`
(`magazzino_repository.py:582-598`) e aggiorna solo `data`, `descrizione`, `meta` (`:396`); nessuna funzione DB valorizza
la sorgente di una testata. I trasferimenti non hanno neppure una famiglia BE (`famiglie.py:115-118`, «una terza famiglia
è una riga qui»).

**(3) Lettori** ✅: BE `_documento_select` (`magazzino_repository.py:238`) e `DocumentoInternoRow`
(`types.py:44-46`); `dbops.fn_sorgenti_orfane` (perimetro dinamico). Nessuna funzione o vista DB legge la sorgente di una
testata.

**(4)** ✅

| Tabella | CHECK | Unico | Classificazione |
| --- | --- | --- | --- |
| `inventari` | `chk_mag_inventari_sorgente_chiave` | `uq_mag_invetario_sorgente_fk (sorgente_tipo_id, sorgente_uid) WHERE tipo IS NOT NULL AND uid IS NOT NULL` (refuso «invetario» dichiarato nel manuale `inventari.md:106`) | **residuo**: copre solo il ramo `uid`, nessun tipo ammesso dal dominio ha oggi chiave `uid` per una testata di magazzino; nessuna decisione lo nomina (analisi magazzino, «Realizzato» D-2) |
| `rettifiche` | `chk_mag_rettifiche_sorgente_chiave` | `uq_mag_rettifiche_source_fk` (stesso predicato) | **residuo** |
| `trasferimenti` | `chk_mag_trasferimenti_sorgente_chiave` | `uq_mag_trasf_sorgente_fk (tipo, uid) WHERE tipo IS NOT NULL` | **residuo**: col ramo `id` l'uid è NULL e i NULL sono distinti, quindi non controlla niente |

Nessun pgTAP nomina i tre indici (grep su `db/pgtap`: 0 file). FK: `fk_mag_inventari_sorgenti_tipo` è
`ON UPDATE RESTRICT`, le altre `ON UPDATE CASCADE` (difformità minore).

**(5)** ✅ guard tipizzato + `require_attivo` + `trgfn_documento_interno_guard_transizione` (`BEFORE DELETE OR UPDATE OF
stato`).

**(6) S-9 come bersaglio** — vedi §6: la testata è anche il **documento** dei movimenti col modello nuovo.

**(7)** 🔶 Lotto: famiglia magazzino. Gli unici si **ritirano** (nessuna regola di dominio «un inventario per
documento»: se il dominio la volesse, va dichiarata, non ereditata). Il CHECK di forma si riscrive.

##### 1.6 `magazzino.eventi_assets`

**(1)** ✅ `sorgente_tipo_id` bigint null; `sorgente_uid` uuid null («Identificatore esterno documento»);
`sorgente_riga` bigint null (commento lotto 1, D-1). Significato (manuale `eventi_assets.md`, §«La sorgente, come sul
registro»): facoltativa, «da quale documento l'operazione è nata». **Doppio ruolo**: ha una sorgente **ed è** il
`target_table` del tipo `EVENTO_ASSET` (sorgente del movimento).

**(2) Scrittori** ✅: **nessuno** (nessuna funzione DB nomina la tabella tranne il risolutore dell'emittente; nessun file
BE; solo fixture pgTAP).

**(3) Lettori** ✅: `script.fn_resolve_emittente_fiscale_id('evento_asset', …)` (dall'asset, non dalla sorgente);
`dbops.fn_sorgenti_orfane`; pgTAP `dbops/test-sorgenti-orfane-v1.sql`, `rls/test-rls-magazzino-perimetro-v1.sql`,
`magazzino/test-causali-e-sorgenti-seed-v1.sql:108`.

**(4)** ✅ `chk_mag_eventi_assets_sorgente_chiave` (unica tabella del §3.1 con il CHECK di esclusività, come dice il brief);
`uq_mag_eventi_assets_sorgente_fk (tipo, uid) WHERE tipo IS NOT NULL` → **residuo** (stessa analisi dei trasferimenti).

**(5)** ✅ guard tipizzato, `require_attivo` su sorgenti/asset/tipo evento, `block_deact` verso `note_evento_asset`.

**(6)** vedi §6. **(7)** S-10, §9.

##### 1.7 `acquisti.ordini` · 1.8 `acquisti.ddt` (testate)

**(1)** ✅ `sorgente_tipo_id` bigint null («FK → config.sorgenti(id)»), `sorgente_uid` uuid null («Origine import
(uid)»). **Niente `sorgente_riga`**. Grammatica **G1 «import»**.

**(2) Scrittori** ✅: nessuno (nessuna funzione DB; `backend/apps/acquisti` contiene solo scheletri vuoti: `models.py`,
`api/views.py`, nessun `db/`/`services/` popolato).

**(3) Lettori** ✅: nessuno oltre il perimetro di `trgfn_child_requires_active_parent`. Non sono nel perimetro di
`fn_sorgenti_orfane` (non hanno `sorgente_riga` né guard).

**(4)** ✅ `uq_ordini_v_sorgente_fk` (su `acquisti.ordini`) e `uq_ddt_v_sorgente_fk` (su `acquisti.ddt`):
`(sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL`, commento «Idempotenza import». →
**idempotenza import**: escono con l'import (tabella di collegamento propria, §4), non prima. Il suffisso `_v_` è un
residuo di copia da vendite. Nessun pgTAP li nomina.

**(5)** ✅ solo `require_attivo` sul tipo. **Nessun guard polimorfo**.

**(6) S-9** ✅: nessun guard di DELETE di testata (solo `trgfn_storico_generic`); `acquisti.ordini_righe` è
`ON DELETE CASCADE` dall'ordine; `acquisti.ddt.ordine_id` è `NO ACTION` (un ordine con DDT non si cancella per FK).
Come bersaglio: `ORDINE_ACQUISTO` e `DDT_ACQUISTO` oggi non sono scritti da nessuna tabella.

**(7) S-8** ✅: `acquisti.ddt.ordine_id` («FK → acquisti.ordini(id) (opzionale)») è una **colonna parallela** non elencata
nel §3.1-bis: dice la stessa provenienza di `sorgente_*` = ORDINE_ACQUISTO. 🔶 Può rientrare (tipo ORDINE_ACQUISTO +
`sorgente_id`), ma oggi è una FK vera: rientrando si perde la FK e la si sostituisce con guard + lato «in uscita». Da
segnalare a Tid come eccezione possibile (la FK dà integrità gratis; la sorgente dà la grammatica unica). Lotto: famiglia
acquisti, dopo l'import.

##### 1.9 `acquisti.ordini_righe`

**(1)** ✅ `sorgente_tipo_id` («FK → config.sorgenti(id)»), `sorgente_uid uuid` («Origine import (uid)»),
`sorgente_riga bigint DEFAULT 0` («ID/prog. riga nella sorgente (0 se non applicabile)»). Manuale `ordini_righe.md:19`:
«**campi di idempotenza**: servono a rendere ripetibile l'inserimento — un import o un re-invio non devono duplicare
le righe». Grammatica **G1 di riga (import)**, come da §3.1-bis.

**(2)/(3)** ✅ nessuno scrittore né lettore.

**(4)** ✅ `DEFAULT 0` → **residuo** (nel modello 0 è una riga inesistente; documento intero = NULL): `DROP DEFAULT` e,
dove ci fossero dati, `0 → NULL`. `uq_ordini_righe_v_sorgente_fk (tipo, uid) WHERE tipo IS NOT NULL` → **idempotenza
import**.

**(5)** ✅ solo `require_attivo`. **(6)** bersaglio di `acquisti.ordini_righe_fulfillment` (CASCADE) e di
`acquisti.note_ordini` (CASCADE). **(7)** Lotto: famiglia acquisti, con l'import.

##### 1.10 `acquisti.ddt_righe`

**(1)** ✅ (lotto A, `20261105-03` EXECUTED su dbdev il 2026-11-05 18:40): `sorgente_tipo_id` («da dove viene la riga, se
l'ha generata un verbo (per esempio la riga dell'ordine d'acquisto). NULL = riga scelta dall'operatore. Si scrive nello
STESSO INSERT, prima del legame in acquisti.ordini_righe_fulfillment; la chiave sta in sorgente_riga (key_selector id)
o sorgente_uid (uid). Il guard dell'articolo ritirato legge questa colonna»), `sorgente_uid`, `sorgente_riga`
(«l'id della riga di partenza»). Grammatica G2 dichiarata.

⛔ **Non scrivibile come descritto:** in `config.sorgenti` c'è `ORDINE_ACQUISTO` (testata, `acquisti.ordini`) ma **non**
`ORDINE_ACQUISTO_RIGA`. Con G2 «la riga dell'ordine d'acquisto» in `sorgente_riga` vorrebbe un tipo di riga che non
esiste; con `ORDINE_ACQUISTO` il guard leggerebbe `sorgente_riga` come id dell'**ordine**. Il modello §4 lo risolve senza
tipi nuovi: `ORDINE_ACQUISTO` + `sorgente_id = ordine` + `sorgente_riga = ordini_righe.id`.

**(2)/(3)** ✅ nessuno scrittore. Lettori: nessuno in pratica; il guard dell'articolo ritirato
(`trgfn_righe_guard_articolo_ammesso`) **non è montato** su `acquisti.ddt_righe` (nessun trigger relativo in
`pg_trigger`).

**(4)** ✅ nessun CHECK di esclusività, nessun indice sulla sorgente. **(5)** solo `require_attivo`; **nessun guard
polimorfo** (la tabella non è nel perimetro di `fn_sorgenti_orfane_perimetro`, che invece contiene già le quattro righe
di vendita del lotto A).

**(6)** bersaglio di `ordini_righe_fulfillment` (CASCADE) e `note_ddt` (CASCADE); bersaglio futuro del carico
(`CARICO_ACQ`, manuale `ddt_righe.md`: «oggi quel collegamento non esiste»).

**(7) S-8** ✅ `acquisti.ordini_righe_fulfillment` (`ordine_riga_id`, `ddt_riga_id`, `qta_ricevuta`; **`ON DELETE CASCADE`**
su entrambe le FK, contro `RESTRICT` di `vendite.ordini_righe_fulfillment`). 🔶 **Non può rientrare** in `sorgente_*`:
porta una **quantità** (evasione parziale e multipla, N:M), non solo una provenienza. La sorgente della riga di DDT è la
provenienza **principale**; il ponte resta il registro delle quantità. Eccezione da proporre a Tid con questo motivo.
Lotto: famiglia acquisti (insieme al verbo di ricezione, che oggi non esiste: costruirlo direttamente sul modello).

---

#### 2. Scheda speciale — `uq_mag_movimenti_identita`

##### 2.1 Che cosa garantisce oggi ✅

* **Definizione:** `UNIQUE (sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id)
  NULLS NOT DISTINCT`; commento: «L'identità del movimento è l'OPERAZIONE-PER-TRANCHE … È GLOBALE, non per magazzino: la
  sorgente è nella chiave» (D-4, D-L1-c).
* **Che cosa vuol dire:** una stessa **foglia** (prelievo, rientro, riga) può produrre un solo movimento per **verbo**
  (la causale) e per **tranche** (asset, lotto, ubicazione). È l'idempotenza della registrazione: ripostare una bolla,
  un reso, un inventario non duplica il registro.
* **Chi ne dipende:**
  * `fn_scrivi_movimento` **passo 10**: SELECT esplicita sulla stessa 7-upla con `IS NOT DISTINCT FROM`, che solleva
    `E_MAG_MOVIMENTO_GIA_REGISTRATO` («la madre dà la frase, il UNIQUE resta la rete»). Va riscritta **insieme**
    all'indice, altrimenti frase e rete divergono;
  * `fn_scrivi_movimento` **passo 9** (storno): pretende `sorgente_tipo_id`, `sorgente_riga`, `sorgente_uid` uguali
    all'originale; lo storno non collide con l'originale **perché la causale cambia** (`STORNO_POS`/`_NEG`);
  * **nessun `ON CONFLICT`** su questo indice (grep su `pg_proc` e BE: nessuno). Nessun verbo «riprova».
  * pgTAP: `magazzino/test-movimenti-vincoli-v2.sql` casi 11-13 (collisione, tranche diversa, OUT/IN),
    `test-fn-scrivi-movimento-controlli-v1.sql` (`E_MAG_MOVIMENTO_GIA_REGISTRATO`).
* **Effetto collaterale voluto:** una foglia già movimentata e stornata **non si può ripostare** con la stessa causale
  (l'originale c'è ancora): rifare = nuova foglia. Va preservato.

##### 2.2 Perché col modello S-3 l'equivalenza non è automatica

La chiave nuova è `(sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, sorgente_dettaglio, causale_id,
asset_id, lotto_id, ubicazione_id) NULLS NOT DISTINCT`. Oggi la foglia **da sola** identifica la registrazione, e tutto ciò
che sta sopra (riga, documento) è funzione della foglia. Col modello nuovo la foglia è affiancata da due colonne in più
scritte dal verbo: se queste potessero essere **sbagliate o diverse** per la stessa foglia, due registrazioni della stessa
foglia non collidono più. L'equivalenza regge a due condizioni, **entrambe di modello**:

1. 🔶 **Catena verificata** dal guard unico: `sorgente_dettaglio` appartiene a `sorgente_riga`, che appartiene a
   `sorgente_id` (FK di livello dichiarate in `config.sorgenti`, lotto 0). Con la catena vera, `(tipo, doc, riga, dett)`
   è in biiezione con `(tipo_foglia_di_oggi, foglia)`. Le FK di catena sono NOT NULL e immobili fuori bozza
   (`ddt_righe_prelievi.ddt_riga_id NOT NULL`, `resi_righe_rientri.resi_riga_id NOT NULL`, `*_righe.<testata>_id NOT NULL`;
   lock di bozza/stato su tutte le righe), quindi la biiezione non si rompe dopo la scrittura.
2. 🔶 **Livello fisso per tipo sul registro:** oggi è il **tipo** a imporre il livello (PRELIEVO = sempre la foglia). Dopo,
   `DDT_VENDITA` ammette tre livelli (documento, riga, dettaglio): se un verbo scrivesse lo stesso fatto a livello riga e
   un altro a livello dettaglio non colliderebbero. Serve una regola: **sul registro, se il catalogo dichiara un
   `target_dettaglio_table` per il tipo, `sorgente_dettaglio` è obbligatorio; se dichiara solo le righe,
   `sorgente_riga` è obbligatorio** (la foglia più bassa che il tipo ha). È un parametro del guard sulla tabella
   (TG_ARGV, «livello minimo = foglia»), non un CHECK fisso, perché `movimenti_attesi` vuole invece livelli liberi
   (§1.2).

Con 1 e 2 la vecchia chiave e la nuova separano esattamente le stesse coppie di righe.

##### 2.3 I casi, uno per uno

| Caso | Chiave di oggi (tipo, riga, uid · causale · tranche) | Chiave nuova (tipo, id, uid, riga, dettaglio · causale · tranche) | Note |
| --- | --- | --- | --- |
| **Prelievo** (uscita bolla) | `DDT_VENDITA_PRELIEVO`, prelievo, ∅ · causale bolla · lotto/asset/ubic. del prelievo | `DDT_VENDITA`, ddt.id, ∅, ddt_righe.id, prelievo.id · idem · idem | il prelievo di un **componente** di kit (`ddt_riga_componente_id`) resta un dettaglio della riga: il componente è ricavabile dal prelievo, non serve un quarto livello |
| **Arrivo** (bolla di trasferimento) | `DDT_VENDITA_PRELIEVO`, **stesso** prelievo · `TRASF_IN` · ubic. d'arrivo | `DDT_VENDITA`, ddt, ∅, riga, prelievo · `TRASF_IN` · ubic. d'arrivo | non collide con l'uscita: causale diversa, come oggi |
| **Storno** di prelievo | copia · `STORNO_POS` (o `_NEG` per l'arrivo) · copia | copia delle cinque colonne · idem | `fn_storna_movimenti_sorgente` copia già la riga intera: basta che copi anche `sorgente_id`/`dettaglio` |
| **Rientro** (reso) | `RESO_VENDITA_RIENTRO`, rientro, ∅ · `CARICO_RESO_VEN` · lotto/asset del prelievo, ubic. del rientro | `RESO_VENDITA`, reso.id, ∅, resi_righe.id, rientro.id · idem · idem | il legame col prelievo d'origine resta nel dato del rientro (`ddt_riga_prelievo_id`), non nella sorgente |
| **Inventario** | `INVENTARIO_RIGA`, inventari_righe.id, ∅ · dal piano · della riga | `INVENTARIO`, inventari.id, ∅, inventari_righe.id, ∅ · idem · idem | dettaglio NULL: `NULLS NOT DISTINCT` lo tratta come valore, collisione identica |
| **Rettifica** | `RETTIFICA_RIGA`, riga, ∅ · `RETT_POS`/`_NEG` · della riga | `RETTIFICA`, rettifiche.id, ∅, riga, ∅ · idem · idem | — |
| **Trasferimento** (documento interno) | `TRASFERIMENTO_RIGA`, riga, ∅ · `TRASF_OUT` e `TRASF_IN` · ubic. da / a | `TRASFERIMENTO`, trasferimenti.id, ∅, riga, ∅ · idem · idem | due righe per riga, causali diverse, come oggi |
| **Evento asset** (nessuno scrittore) | `EVENTO_ASSET`, evento.id, ∅ · `ASSET_INSTALL`/`_RIENTRO` · asset | `EVENTO_ASSET`, evento.id, ∅, ∅, ∅ · idem · idem | oggetto senza righe (S-10): riga e dettaglio sempre NULL |
| *Futuro:* carico da DDT d'acquisto | — | `DDT_ACQUISTO`, ddt.id, ∅, ddt_righe.id, (∅ o la tranche di ricezione se nascerà) | va deciso **prima** del verbo quale sia la foglia (riga o «ricevimento per lotto»): è la regola 2 |

##### 2.4 Che cosa si riscrive insieme all'indice (perché resti equivalente)

* `fn_scrivi_movimento`: firma (aggiunge `p_sorgente_id`, `p_sorgente_dettaglio`; parametri in coda), passo 1 (forma:
  «una sola chiave di documento»), passo 9 (specchio: cinque colonne), passo 10 (identità: nove colonne), passo 11
  (passa la sorgente intera a `fn_check_disponibilita_uscita`), passo 13 (INSERT).
* `fn_storna_movimenti_sorgente(p_tipo, p_righe[])` 🔶 → per documento: `(p_tipo, p_sorgente_id | p_sorgente_uid,
  p_righe bigint[] DEFAULT NULL = tutto il documento)`. I due chiamanti oggi **raccolgono** l'array dei prelievi/rientri
  della bolla/del reso con un JOIN (`fn_cambia_stato_ddt`: `array_agg(p.id) … WHERE dr.ddt_id = p_ddt_id`;
  `fn_annulla_reso`: idem sui rientri): col modello passano il documento e basta. Resta generico (nessun nome di
  `vendite` in `magazzino`).
* `vendite.fn_posta_reso`: il costo dell'uscita si rilegge per `(DDT_VENDITA, ddt, riga, prelievo, qta<0, non storno)`;
  il rientro conosce già prelievo → riga → ddt via join.
* `script.fn_check_disponibilita_uscita`: confronto «propria» per prefisso (§1.2).
* `dbops.vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico`: ~~`m.sorgente_tipo_id = DDT_VENDITA AND
  m.sorgente_id = d.id`~~ ⛔ **corretto il 2026-11-08**: quella è la domanda sul documento intero che D58 dice
  sbagliata (uno scarico parziale non accende niente). La domanda resta per prelievo di riga attiva (per rientro):
  `sorgente_tipo_id = DDT_VENDITA, sorgente_id = d.id, sorgente_riga = dr.id, sorgente_dettaglio = p.id` — §7.2
  «Lotto M», «Riverifica fatta».
* pgTAP che costruiscono la 7-upla a mano (§1.1 (3)).

---

#### 3. Scheda — i tipi di magazzino `*_RIGA`, `*_PRELIEVO`, `*_RIENTRO`, `EVENTO_ASSET` (S-2, S-3)

##### 3.1 Il catalogo oggi ✅ (`config.sorgenti`)

| id | codice_interno | categoria | target_table | key | scope | Diventa |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | INVENTARIO_RIGA | RIGA | magazzino.inventari_righe | id | MAGAZZINO | `INVENTARIO` (25) + riga |
| 18 | RETTIFICA_RIGA | RIGA | magazzino.rettifiche_righe | id | MAGAZZINO | `RETTIFICA` (26) + riga |
| 19 | TRASFERIMENTO_RIGA | RIGA | magazzino.trasferimenti_righe | id | MAGAZZINO | `TRASFERIMENTO` (27) + riga |
| 21 | DDT_VENDITA_PRELIEVO | RIGA | vendite.ddt_righe_prelievi | id | MAGAZZINO | `DDT_VENDITA` (8) + riga + dettaglio |
| 22 | RESO_VENDITA_RIENTRO | RIGA | vendite.resi_righe_rientri | id | MAGAZZINO | `RESO_VENDITA` (15) + riga + dettaglio |
| 20 | EVENTO_ASSET | RIGA | magazzino.eventi_assets | id | MAGAZZINO | resta (S-10): oggetto senza righe |
| 23-27 | ORDINE_ACQUISTO, DDT_ACQUISTO, INVENTARIO, RETTIFICA, TRASFERIMENTO | DOCUMENTO | testate | id | CATALOGO | restano, prendono `target_righe_table` |

Livelli da dichiarare nel lotto 0 (🔶, nomi indicativi): `DDT_VENDITA` → righe `vendite.ddt_righe(ddt_id)`, dettaglio
`vendite.ddt_righe_prelievi(ddt_riga_id)`; `RESO_VENDITA` → `vendite.resi_righe(reso_id)`, `vendite.resi_righe_rientri(resi_riga_id)`;
`INVENTARIO` → `magazzino.inventari_righe(inventario_id)`; `RETTIFICA` → `magazzino.rettifiche_righe(rettifica_id)`;
`TRASFERIMENTO` → `magazzino.trasferimenti_righe(trasferimento_id)`; `ORDINE_ACQUISTO` → `acquisti.ordini_righe(ordine_id)`;
`DDT_ACQUISTO` → `acquisti.ddt_righe(ddt_id)`; `EVENTO_ASSET` → nessuno.

##### 3.2 Chi li nomina ✅

| Dove | Codici | Uso |
| --- | --- | --- |
| `magazzino.fn_posta_inventario` / `_rettifica` / `_trasferimento` | INVENTARIO_RIGA / RETTIFICA_RIGA / TRASFERIMENTO_RIGA | lookup per `codice_interno AND attivo`, `E_CONFIG_MANCANTE` se manca |
| `vendite.fn_posta_ddt` | DDT_VENDITA_PRELIEVO | idem, con `attivo` |
| `vendite.fn_posta_reso` | RESO_VENDITA_RIENTRO (con `attivo`), DDT_VENDITA_PRELIEVO (**senza** `attivo`, per il costo) | — |
| `vendite.fn_cambia_stato_ddt` | DDT_VENDITA_PRELIEVO **senza** `attivo`; `IF v_sorgente_id IS NOT NULL` → **storno saltato in silenzio** | ⛔ |
| `vendite.fn_annulla_reso` | RESO_VENDITA_RIENTRO **senza** `attivo`; stesso salto silenzioso | ⛔ |
| `dbops.vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico` | PRELIEVO, RIENTRO (letterale) | presidi |
| `script.fn_scope_note_magazzino_ef_perimetro` | INVENTARIO_RIGA, RETTIFICA_RIGA, TRASFERIMENTO_RIGA, EVENTO_ASSET | ⚠️ sono codici di **`config.tipi_entita`** (partizioni `magazzino.note`, FK `fk_mag_note_target_tipo`), **non** di `config.sorgenti`: **restano** |
| `config.tipi_entita` | le 11 righe `is_sorgente = true` (fra cui le 7 di magazzino) | FK `fk_tipi_entita_sorgenti` (`sorgente_codice_interno` generata → `config.sorgenti.codice_interno`): prima `is_sorgente = false`, poi il ritiro del tipo (brief §7.2); l'entità resta (note, giornale) |
| `magazzino.note` | partizioni `note_inventario_riga`, `note_rettifica_riga`, `note_trasferimento_riga`, `note_evento_asset` | entità, restano |
| BE `backend/apps/config/sorgenti.py:59-60` | `SORGENTE_INVENTARIO_RIGA`, `SORGENTE_RETTIFICA_RIGA` | presidiate da `backend/apps/config/tests/test_sorgenti_seed.py` (esistenza e attività nel seed): rosso se si ritirano senza aggiornarle. ⚠️ Mancano `SORGENTE_INVENTARIO` / `_RETTIFICA` / `_TRASFERIMENTO` |
| BE `backend/apps/magazzino/db/famiglie.py:34,56,84,103` | `sorgente_codice_interno` della famiglia | diventa il tipo **documento**; il campo `fk_riga` resta ma non serve più al filtro |
| BE `backend/apps/magazzino/api/views.py:845,863` | parametro `sorgente_tipo` (valori `*_RIGA`) | **contratto API**: i valori cambiano |
| BE test | `magazzino/tests/services/test_magazzino_service.py:94`, `tests/api/test_magazzino_api.py:316`, `tests/db/test_documento_interno_db.py:194`, `backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py:25,116-118` | asserzioni sul codice |
| UI seed | `ui/lista_colonna.csv:865-866` | descrizioni colonna |
| FE | `frontend/src/magazzino/vocabolari.js:62-66,112,131`; `locales/it.json:5222-5223`, `en.json:5222-5223` | filtro, etichette, deep-link |
| pgTAP | INVENTARIO_RIGA 11 file, RETTIFICA_RIGA 2, TRASFERIMENTO_RIGA 3, EVENTO_ASSET 2, DDT_VENDITA_PRELIEVO 1 (`magazzino/test-ddt-scarico-v1.sql`), RESO_VENDITA_RIENTRO 2; più `magazzino/test-causali-e-sorgenti-seed-v1.sql:105-108,132` che **pretende** le quattro righe MAGAZZINO | — |

Falsi positivi esclusi: `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` (codice d'errore, `magazzino_service.py:100`,
`error_messages_fallback.py:815`, `error_policies_generated.py:1111`) non è la sorgente.

##### 3.3 Ordine di ritiro che non rompe (🔶, per il piano a lotti)

1. lotto 0: livelli nel catalogo, guard unico, BB;
2. riscrittura dei **sei** verbi + `fn_storna_movimenti_sorgente` + presidi `dbops` nello **stesso** changeSet di
   famiglia (i verbi di storno leggono il tipo senza `attivo`: se il tipo sparisse prima, l'annullo non storna);
3. conversione dei dati del registro (foglia → documento + riga + dettaglio: è derivabile per join, nessuna perdita);
4. BE/FE (contratto `sorgente_tipo`, famiglie, costanti, etichette);
5. `config.tipi_entita.is_sorgente = false`, poi ritiro (attivo=false o cancellazione) dei 5 tipi in `config.sorgenti` e
   del seed pgTAP che li pretende. `EVENTO_ASSET` non si ritira.

---

#### 4. Scheda — i BB del perimetro (che cosa cambia)

| BB | Oggi | Col modello |
| --- | --- | --- |
| `magazzino.fn_scrivi_movimento` | tipo + una chiave (riga \| uid) | tipo + chiave documento + riga + dettaglio; passi 1, 9, 10, 11, 13 (§2.4). Riceve **anche** l'uid del documento se il chiamante ce l'ha (il BB «che scrive» del lotto 0 decide la colonna) |
| `magazzino.fn_storna_movimenti_sorgente` | `(tipo, righe[])` sulla foglia | `(tipo, documento, righe[] facoltativo)`; copia le cinque colonne |
| `vendite.fn_posta_ddt` | PRELIEVO + prelievo.id | DDT_VENDITA + ddt.id + dr.id + p.id (ha già tutto nel cursore) |
| `vendite.fn_posta_reso` | RIENTRO + rientro.id; lettura costo per PRELIEVO | RESO_VENDITA + reso + rr.id + x.id; costo per DDT_VENDITA + ddt + riga + prelievo |
| `magazzino.fn_posta_inventario` / `_rettifica` / `_trasferimento` | `*_RIGA` + riga.id | `INVENTARIO`/… + testata.id + riga.id (la testata è già in mano: `p_<doc>_id`) |
| `vendite.fn_cambia_stato_ddt`, `vendite.fn_annulla_reso` | raccolgono l'array delle foglie | passano il documento; ⛔ smettere di saltare lo storno quando il tipo non c'è (è un `E_CONFIG_MANCANTE`, non un «niente da fare») |
| `script.fn_check_disponibilita_uscita` | uguaglianza sulla terna | prefisso sul documento (§1.2) |
| `script.trgfn_guard_sorgente_polimorfa_tipizzata` | foglia esiste nel target | guard unico: documento esiste, riga ∈ documento, dettaglio ∈ riga, livello minimo per tabella (TG_ARGV), esclusività delle chiavi |
| `dbops.fn_sorgenti_orfane(_perimetro)` | perimetro = tabelle con `sorgente_riga` + `sorgente_uid` + guard tipizzato; chiave = `sorgente_riga` | perimetro = tabelle col guard unico; anti-join a tre livelli (documento, riga, dettaglio). ⚠️ `acquisti.*` ne è fuori oggi |

---

#### 5. Scheda — S-8 nel perimetro

| Colonna parallela | Che cosa dice | Può rientrare? | Motivo |
| --- | --- | --- | --- |
| `acquisti.ddt.ordine_id` (FK NO ACTION) | il DDT viene dall'ordine d'acquisto | 🔶 sì, nella forma; da decidere | la FK dà integrità e blocco della cancellazione dell'ordine; rientrando servono guard unico + lato «in uscita» (S-9) per avere lo stesso effetto |
| `acquisti.ordini_righe_fulfillment` (CASCADE/CASCADE) | quanta riga d'ordine copre la riga di DDT | 🔶 **no** | porta `qta_ricevuta`, N:M, evasioni parziali: è un registro di quantità, non una provenienza. `ddt_righe.sorgente_*` dice la riga d'ordine principale (scritta «nello stesso INSERT, prima del legame»: stesso fatto due volte, ma il ponte dice di più) |
| `vendite.resi_righe_rientri.ddt_riga_prelievo_id` (FK) | quale prelievo della bolla rientra | no (fuori dal mio perimetro, segnalato) | non è la provenienza del rientro (che è il reso): è il dato «che cosa torna», letto da `fn_posta_reso` per lotto/asset/costo |
| `magazzino.movimenti.storno_di_movimento_id` | lo storno di quale movimento | no | non è una provenienza polimorfa: FK interna al registro, unica |
| `magazzino.movimenti.transfer_uid` | coppia OUT/IN | no | legame interno (costo della gemella), non una sorgente |

---

#### 6. Scheda — S-9, la cancellazione dei bersagli (stato di oggi)

✅ = verificato su `pg_trigger` / `pg_constraint` / `role_table_grants`; tutti i bersagli hanno `GRANT DELETE` a
`zeroerp_owner` e `zeroerp_app`.

| Tipo → bersaglio | Il DELETE è ammesso? | E i movimenti? |
| --- | --- | --- |
| `DDT_VENDITA_PRELIEVO` → `vendite.ddt_righe_prelievi` (FK CASCADE da `ddt_righe` e `ddt_righe_componenti`) | solo con la bolla in bozza: `trgfn_doc_righe_lock_fuori_bozza` (a05) sulla riga e sul prelievo; testata `trgfn_doc_guard_delete_solo_bozza`; riga `trgfn_dlt_block_ordrig_ddtrig` | i movimenti nascono all'**emissione** (fuori bozza) e l'annullo li storna: il prelievo movimentato non è cancellabile. ✅ coperto dalla regola di stato, **non** dal legame |
| `RESO_VENDITA_RIENTRO` → `vendite.resi_righe_rientri` (FK CASCADE da `resi_righe`) | riga e rientro: lock di bozza. **Testata `vendite.resi`: nessun guard di DELETE** | ⛔ un `DELETE FROM vendite.resi` di un reso CONFERMATO passa in cascata (il lock di riga tratta «padre assente» come cascade già autorizzato: commento del BB, «la regola di stato sul padre l'ha già applicata il suo guard», che qui **non c'è**) → movimenti `CARICO_RESO_VEN` orfani. La regola sta solo nel BE (`resi_service.py:582-598`) |
| `INVENTARIO_RIGA` / `RETTIFICA_RIGA` / `TRASFERIMENTO_RIGA` → `magazzino.*_righe` (FK CASCADE dalla testata) | righe: `trgfn_documento_interno_righe_guard_testata` (solo testata DRAFT); testata: `trgfn_documento_interno_guard_transizione` (DELETE solo DRAFT) | i movimenti nascono a POSTED (terminale): righe movimentate non cancellabili. ✅ coperto dalla regola di stato |
| `EVENTO_ASSET` → `magazzino.eventi_assets` (FK **CASCADE** da `magazzino.assets`) | **nessun guard di DELETE**; cancellabile sempre | oggi nessun movimento la usa; quando ci sarà, cancellare l'evento (o l'asset, se non bloccato da `fk_mag_movimenti_asset` NO ACTION) lascia il movimento orfano. ⚠️ Da coprire **prima** di costruire l'operazione |
| `INVENTARIO` / `RETTIFICA` / `TRASFERIMENTO` (testate come documento dei movimenti, col modello nuovo) | DELETE solo in DRAFT | ✅ coperto |
| `ORDINE_ACQUISTO` / `DDT_ACQUISTO` | nessun guard di DELETE in acquisti; righe e fulfillment in CASCADE | oggi nessun figlio polimorfo; il carico da DDT d'acquisto, quando nascerà, avrà bisogno di una regola di stato **a DB** |

🔶 Per il lato «in uscita» del lotto 0: la regola che oggi protegge il registro è **la regola di stato del documento**, non
un legame. Il lato «in uscita» derivato dal catalogo può essere un trigger `BEFORE DELETE` montato sul `target_table` (e
sui livelli righe/dettaglio) che rifiuta se esistono figli polimorfi; per il registro non c'è un'«azione conseguente»
ammissibile (il ledger non si cancella), quindi l'azione è **RESTRICT**. Il primo buco che chiude è `vendite.resi`
(che comunque merita il suo `trgfn_doc_guard_delete_solo_bozza`, come `ddt` e `ordini`).

---

#### 7. Scheda — S-10, `EVENTO_ASSET` e i tipi non documento

##### 7.1 Fatti ✅

* `EVENTO_ASSET` (id 20): `categoria = 'RIGA'`, `target_table = magazzino.eventi_assets`, `key_selector = 'id'`,
  scope `MAGAZZINO`, `tipo_doc_fiscale_id` NULL.
* **Nessuno lo scrive** come sorgente: nessuna funzione DB (le uniche che nominano `eventi_assets` sono il risolutore
  dell'emittente), nessun file BE o FE; solo il seed pgTAP che ne pretende l'esistenza
  (`magazzino/test-causali-e-sorgenti-seed-v1.sql:108`) e la fixture RLS delle note. Le causali `ASSET_INSTALL` (−1) e
  `ASSET_RIENTRO` (+1) esistono in `magazzino.causali`.
* Manuale `eventi_assets.md` §Scopo: «l'evento è la **sorgente** del movimento (`EVENTO_ASSET`): è così che i due lati si
  legano. Scriverli insieme … è compito dell'operazione che li produce, **che ancora non esiste**».
* L'evento ha a sua volta una sorgente facoltativa («da quale documento l'operazione è nata»): catena
  movimento → evento → documento.
* Anche `ATTIVITA` (id 1, `categoria RIGA`, `vendite.attivita_fatturabili`) non è scritto come sorgente da nessuna
  funzione DB (solo `script.fn_scope_note_ef_perimetro` lo nomina come entità di nota e una fixture pgTAP).

##### 7.2 Che cos'è l'evento rispetto a «il tipo è il documento»

L'evento **non è un documento** (non ha numero, non ha righe, non ha stati di documento) ma è un **fatto registrato con
identità propria**: «a questo asset, in questa data, è successo questo». È la stessa natura dell'operazione che D-6 chiede
a monte di ogni movimento («ogni movimento ha un'operazione a monte; la correzione a mano è una rettifica»). Per il
registro conta che la provenienza sia un **oggetto verificabile**, non che sia un documento commerciale.

##### 7.3 L'ipotesi del brief

> il tipo = l'oggetto di provenienza; il catalogo dice se ha righe (`target_righe_table`) o no; un oggetto senza righe ha
> solo la chiave e `sorgente_riga` sempre NULL.

🔶 **Regge sul modello**, con due precisazioni:

1. **«Ha righe» non basta: serve anche «ha dettaglio»** (S-3) — la stessa colonna di catalogo per livello, NULL = livello
   assente. Il guard deriva da lì la forma ammessa: senza `target_righe_table` ⇒ `sorgente_riga IS NULL` e
   `sorgente_dettaglio IS NULL`.
2. **La forma ammessa dipende anche dal consumatore**, non solo dall'oggetto: il registro vuole la foglia (§2.2 regola 2),
   le attese e le provenienze di documento accettano livelli liberi. Il catalogo dice **che cosa esiste**; il montaggio del
   guard sulla tabella dice **quale livello serve**.

Conseguenze: `categoria` (`DOCUMENTO`/`RIGA`) diventa ridondante con `target_righe_table` per i tipi che restano (dopo
S-2 non ci saranno più tipi `RIGA`). 🔶 O si ricava dai livelli, o si rinomina il vocabolario in qualcosa che dica la
natura (`DOCUMENTO` / `EVENTO`): l'unico lettore BE è `vendite/db/famiglie_repository.py:339`
(`CATEGORIA_SORGENTE_DOCUMENTO`). Nessuna funzione o vista DB legge `categoria`.

##### 7.4 Alternative

| # | Alternativa | Pro (sul modello) | Contro (sul modello) |
| --- | --- | --- | --- |
| A | **Ipotesi del brief**: l'evento è un oggetto di provenienza senza righe | una grammatica sola; il guard unico la copre senza casi speciali; regge anche l'ODL futuro (D-5, documento **con** righe di materiali) e qualunque «fatto» di magazzino senza documento commerciale; l'identità del registro resta equivalente (§2.3) | la parola «documento» del §4 va allargata a «oggetto di provenienza»; la catena movimento → evento → documento ha un salto in più per la lineage (ma è un salto **dichiarato**, non un CASE) |
| B | La sorgente del movimento è il **documento** dell'evento (la bolla d'installazione), e l'evento si lega al movimento con una FK diretta (`eventi_assets.movimento_id` o viceversa), entrambi in `magazzino` | «il tipo è il documento» resta letterale; la lineage dal movimento arriva al documento senza salti; il legame evento↔movimento diventa una FK vera (integrità e S-9 gratis) | un evento **senza documento** (manutenzione interna, sostituzione in campo) lascerebbe il movimento senza sorgente: contro D-6, a meno di inventare un documento; due provenienze per lo stesso fatto (evento.sorgente e movimento.sorgente) da tenere allineate: è il doppione G8 che il brief toglie |
| C | L'evento diventa un **documento interno** (testata + righe, come inventario/rettifica): un'«operazione su asset» con N eventi | uniforme alle tre famiglie esistenti; il tipo è davvero un documento con righe | struttura nuova senza un bisogno di dominio dichiarato (un evento è uno, non N); un livello in più per un fatto atomico |
| D | Tipi non documento **fuori** da `config.sorgenti`, in un catalogo a parte | separa i concetti | due cataloghi = due grammatiche e due guard: è esattamente ciò che il brief toglie; rompe la FK `fk_mag_movimenti_sorgente_tipo` |

🔶 **Raccomandazione:** A, con la precisazione dei livelli per consumatore. B solo se Tid decide che **ogni** evento ha
sempre un documento a monte (allora il movimento punta al documento e l'evento al movimento con FK). La scelta va fatta
**prima** di costruire l'operazione dell'evento (che oggi non c'è: nessuna conversione dati).

---

#### 8. Richieste BE/FE emerse (percorso intero, elenco chiuso del perimetro)

1. **API `GET /magazzino/movimenti`**: `sorgente_tipo` cambia valori (`INVENTARIO_RIGA` → `INVENTARIO`, …);
   `inventario_id` / `rettifica_id` diventano `sorgente_tipo + sorgente_id` (il repository perde l'`EXISTS` sulle righe,
   `magazzino_repository.py:989-997`); `MovimentoRow`/`BloccoRow`/`DocumentoInternoRow` prendono `sorgente_id`,
   `sorgente_dettaglio` (`types.py:44-46,183-184,212-215`); `famiglie.py` (campo `sorgente_codice_interno`),
   `config/sorgenti.py` (costanti nuove, ritiro delle `*_RIGA`, `test_sorgenti_seed.py`), test BE elencati in §3.2.
2. **UI seed** `lista_colonna.csv:865-866` (descrizioni; colonne nuove per documento e dettaglio).
3. **FE** `magazzino/vocabolari.js` (`SORGENTE_MOVIMENTO`, `sorgente` delle famiglie), `etichette.js`
   (`PREFISSO_SORGENTE_MOVIMENTO`), `locales/it.json`/`en.json` (chiavi), `MovimentiSearchTable.vue`,
   `DisponibilitaBlocchiPopover.vue`, `stores/movimenti.js`, `views/MovimentiView.vue`.
4. **Vendite (resi):** la regola «si cancella solo il reso in bozza» va portata a DB (S-9, §6); il BE resta come
   pre-controllo.

---

#### 9. Lotti di destinazione (proposta per §7.2)

| Lotto | Tabelle / oggetti del perimetro |
| --- | --- |
| 0 (trasversale) | livelli in `config.sorgenti` per DDT_VENDITA, RESO_VENDITA, INVENTARIO, RETTIFICA, TRASFERIMENTO, ORDINE_ACQUISTO, DDT_ACQUISTO; guard unico con «livello minimo» per tabella; lato «in uscita» (primo caso: `vendite.resi`); `fn_sorgenti_orfane` a tre livelli |
| Magazzino | `movimenti`, `movimenti_attesi` (+ `sorgente_id`, `sorgente_dettaglio`), le tre testate, `eventi_assets`; `uq_mag_movimenti_identita` riscritto (§2); i 4 unici residui ritirati; `fn_scrivi_movimento`, `fn_storna_movimenti_sorgente`, i 6 verbi, `fn_check_disponibilita_uscita`, 2 viste `dbops`; poi ritiro dei 5 tipi |
| Acquisti | `ordini`, `ddt` (+ `sorgente_id`, conversione import), `ordini_righe` (`DROP DEFAULT 0`), `ddt_righe` (guard unico); unici «import» ritirati con l'import; decisione S-8 su `ddt.ordine_id`; il fulfillment resta |

### Censimento — pratiche, documenti, BB trasversali, catalogo e codici

> **Per:** `brief-db-sorgente-documento-e-riga` §7.1 (schede di tabella, scheda BB, consumatori dei codici `*_RIGA`).
> **Chi, quando:** team DB, sola lettura, 2026-11-06.
> **Fonti:** cataloghi PostgreSQL di `zeroerp_ruoli` (struttura, vuoto di dati), corpi da `pg_get_functiondef` /
> `pg_views` (sono gli stessi che finiscono nella doc auto-generata), manuali `docs/it/dbzero/*/manual/`, `grep`
> su `backend/apps`, `frontend/src`, `db/pgtap`, `db/changelog/migrations_v2/80_data`.
> **Convenzione:** **FATTO** = verificato, con la fonte (file:riga o oggetto DB). **IPOTESI** = da verificare.
> I numeri sono fatti datati, non motivi (regola zero).

---

#### 0. Che cosa trova questo censimento (in breve)

1. **Bug latente, FATTO dal codice.** `vendite.fn_push_offerta_a_contratto` (ramo `p_pratica_id IS NOT NULL`)
   scrive in `pratiche.pratiche_sorgenti` il tipo `CONTRATTO` (`key_selector = 'id'`) con
   `sorgente_uid = v_contratto_uid::text`, cioè l'**uuid** (`v_contratto_uid vendite.contratti.uid%TYPE`, valorizzato
   da `RETURNING id, uid`). Il guard `_testuale` montato sulla tabella chiama `fn_sorgente_chiave_id(uuid)` → `NULL`
   → **`E_SORG_FORMATO`**. Il BE espone il ramo: `ApiOffertaPushContratto` accetta `pratica_id`
   (`backend/apps/vendite/api/views_offerte.py:503-516`), `offerte_service.push_a_contratto` lo passa
   (`offerte_service.py:938-958`), `offerte_repository.py:1086`. **Nessun pgTAP lo esercita**: tutti e sei i test
   del verbo passano `NULL` (es. `test_fn_push_offerta_a_contratto.sql:260`). Col modello il problema sparisce
   (il BB di scrittura riceve l'uid e salva l'id), ma va scritto: oggi un push con pratica fallisce.
2. **G6 è mista anche dentro FATTURA, FATTO dal codice.** In `documenti.documenti_generati` la fattura entra da **due**
   strade con due chiavi: la UI (`build_documenti_sorgente_views`, `sorgente_documenti_views.py:178,239`, entità da
   `get_fattura_for_documento_generation` che espone `f.uid::text AS uid`, `vendite_repository.py:4218`) scrive
   l'**uid**; il drainer della coda (`stampa_coda_drainer_service.py:293`) scrive `item["sorgente_uid"]`, che
   `vendite.fn_accoda_stampe_lotto` valorizza con `f.id::text`. Conseguenze: la lista UI (`sorgente_documenti_views.py:354`,
   filtra sull'uid) **non vede** i PDF stampati dal drainer, e `uq_documenti_generati_sorgente_progressivo` +
   `next_progressivo_sorgente` (MAX+1) tengono **due serie di progressivi** per la stessa fattura. Il brief (§3.1 G6)
   dice «l'id per FATTURA»: va corretto in «l'id dal drainer, l'uid dalla UI».
3. **I numeri del §3.3 si riproducono** con un metodo dichiarato (§D): 92 funzioni / 26 viste (`prosrc ~
   'sorgente_(uid|riga|tipo_id)'`). **Il metodo è cieco a `BEGIN ATOMIC`** (`prosrc` vuoto): mancano **6 funzioni**
   vere (`vendite.fn_documento_lineage_archi`, `fn_ddt_push_diagnosi`, `fn_ddt_trigger_ordine_testata`,
   `pratiche.fn_pratica_del_documento`, `documenti.fn_template_motivo_non_coerente`, `fn_template_esito_risoluzione`).
   Il perimetro giusto è **98 funzioni + 26 viste**; di queste **4 nominano le colonne solo nei commenti** e **13 solo
   `sorgente_tipo_id`** (il tipo del modello di stampa, fuori dal meccanismo).
4. **I codici `*_RIGA` di vendita non li scrive nessuno dei verbi oggi in DB**: nessuna funzione o vista li nomina
   come letterale (l'unico, `ORDINE_VENDITA_RIGA` in `trgfn_ordini_righe_guard_onere_senza_data_consegna`, è
   un'etichetta in un `jsonb` d'errore). Li scrivono i pgTAP del lotto A non committato e li leggono i guard per
   `id`. BE e FE non li nominano mai come costanti. Il ritiro (S-2) costa poco **lato codice**; pesa sul seed
   (`sorgenti.csv`, `tipi_entita.csv`), sulle `etichetta_key` FE (`locales/*.json:5974-5979`) e su due pgTAP di catalogo.
5. **S-2 revoca anche G-2** del 2026-10-18 («righe e varianti: dentro», `brief-db-grammatica-unica-documenti` §5): il
   §3.5 del brief non lo elenca.
6. **Due eccezioni a S-6 da far decidere a Tid**: `pratiche.reconcile_errori` (un log «resiliente», scritto *dentro*
   un `EXCEPTION WHEN OTHERS`: un guard d'esistenza lo farebbe tacere) e `documenti.template_documenti` (solo il tipo,
   non è una provenienza). Il presidio di struttura del lotto 0 deve riconoscerle.
7. **Il catalogo per le righe non basta per l'offerta**: `OFFERTA_COMMERCIALE` non ha una tabella delle righe; le
   righe espanse vengono da listino **o** eccezione (`vendite.fn_offerta_righe_espanse` restituisce solo `origine
   varchar`, **nessun id di riga**). Una colonna `target_righe_table` sola non la descrive (S-1 da ripassare).

---

#### A. Schede di tabella

##### A.1 `pratiche.pratiche_sorgenti` (G3)

| Voce | Oggi (FATTO) |
| --- | --- |
| Colonne | `sorgente_tipo_id bigint NOT NULL` (FK `fk_pratiche_sorgenti_tipo` → `config.sorgenti`, `ON UPDATE CASCADE`); `sorgente_uid text NOT NULL` — commento «Identificatore della sorgente (es. UUID preventivo). Text per flessibilita'»; `sorgente_riga bigint` NULL — «ID riga specifica della sorgente (opzionale)»; `ruolo_link varchar(30) DEFAULT 'ROOT'` (`ROOT`/`COLLEGATO`); `flusso_id` |
| Significato scritto | manuale `config/manual/sorgenti.md` §Convenzione: uid per PREVENTIVO/OFFERTA, `id::text` per gli altri (forma canonica dal 2026-10-05) |
| Guard | `trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd` → `script.trgfn_guard_sorgente_polimorfa_testuale`, **`UPDATE OF sorgente_tipo_id, sorgente_uid`** (non `sorgente_riga`: la riga non è mai verificata); `..._sorgenti_require_attivo` (constraint trigger, tipo attivo); `..._guard_coerenza_flusso` |
| Indici unici | `uq_pratiche_sorgenti_pratica_tipo_uid_ruolo (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` → **regola di dominio** (un documento compare una volta per pratica e ruolo) **e** bersaglio di tre `ON CONFLICT`; `uq_pratiche_sorgenti_flusso_root (flusso_id) WHERE ROOT` → regola di dominio, non tocca la sorgente. Non unico: `ix_pratiche_sorgenti_tipo_uid` |
| Scrittori DB | `vendite.fn_genera_pratica_da_preventivo` (PREVENTIVO, `v_uid::text`, ROOT); `vendite.fn_push_preventivo_a_ordine` (PREVENTIVO `v_preventivo_uid::text` ROOT; ORDINE_VENDITA `v_ordine_id::text` COLLEGATO + `flusso_id`; entrambi `ON CONFLICT ON CONSTRAINT uq_…_ruolo DO NOTHING`); `vendite.fn_push_offerta_a_contratto` (CONTRATTO **`v_contratto_uid::text`** COLLEGATO, `ON CONFLICT ON CONSTRAINT … DO NOTHING`: il bug del §0.1) |
| Scrittori BE | `PraticheRepository.upsert_pratica_sorgente` (`backend/apps/pratiche/db/pratiche_repository.py:973-1006`): `INSERT … SELECT … FROM config.sorgenti WHERE codice_interno = %s ON CONFLICT (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link) DO UPDATE SET flusso_id = COALESCE(…)`. Chiamanti: `preventivi_service.py:901` (PREVENTIVO, `prev["uid"]`, ROOT, `flusso_id`); `preventivi_service.py:2087` (COMMESSA, `str(commessa_id)`, COLLEGATO); `post_smistamento_handler.py:87` (ORDINE_VENDITA, `str(ordine_id)`, COLLEGATO). **Nessun chiamante passa `sorgente_riga`**: è sempre NULL |
| Lettori DB | `script.vw_pratica_doc_sorgente` (due rami `fn_sorgente_chiave_uuid/_id(ps.sorgente_uid)`); `pratiche.fn_reconcile_sorgente` e `fn_pratica_del_documento` (`ps.sorgente_uid = p_sorgente_uid`, testo); `vendite.vw_preventivi_pratiche` (`ps.sorgente_uid = p.uid::text`); attraverso `fn_pratica_del_documento` le sette viste `vendite.vw_*_lista` e `fn_documento_lineage_sintesi` |
| Lettori BE | `pratiche_repository.py:104` (`_doc_sorgente_lateral`, stessi due rami della vista), `:1015-1043` (`get_pratica_id_by_sorgente`, `_sorgente_link_exists`, testo); `preventivi_repository.py:132` (`p_link.uid::text = ps.sorgente_uid`), `:607`, `:635`, `:1407`; `ordini_repository.py:451` (`ps.sorgente_uid::bigint`); `ordini_service.py:352` |
| FE | nessuno nomina la tabella |
| pgTAP | 9 file (`script/test-guard-sorgente-polimorfa-testuale-v1`, `pratiche/test-proiezione-stato-sorgente`, `test-reconcile-tie-break-flusso-origine`, `test-pratiche-sorgenti-flusso`, `test-guida-avanza-esito-proiettato`, `vendite/test-fn-genera-pratica-da-preventivo-v1`, `test-vw-stato-sorgente-ddt-reso-v1`, `test-fn-push-preventivo-a-ordine-v1`, `rls/test-rls-pratiche-satelliti`) |
| RLS | `rls_pratiche_sorgenti_ef_whitelist` legge `pratica_id`, non la sorgente: il cambio di colonne non la tocca |
| Storico | `storico.pratiche_sorgenti` tiene uno `snapshot jsonb`: niente colonne da allineare, ma gli snapshot vecchi restano con la chiave testuale (da dire nel manuale, non da convertire) |
| S-9 cancellazione | PREVENTIVO: `vendite.preventivi` ha `DELETE` concesso a `zeroerp_app` e **nessun trigger DELETE**; la regola «niente pratiche collegate» sta **nel BE** (`preventivi_service.elimina_preventivo`, `preventivi_service.py:561-592`), non nel DB: contro S-9. ORDINE_VENDITA: `trg_ordini_a10_guard_delete_solo_bozza_dlt` (`trgfn_doc_guard_delete_solo_bozza`) **non guarda `pratiche_sorgenti`**: un ordine in bozza collegato a una pratica si cancella e lascia il link orfano (FATTO dal codice; se il percorso UI lo consenta è IPOTESI). CONTRATTO e COMMESSA: `DELETE` concesso, nessun trigger DELETE |
| Lotto | **P** (pratiche), dopo il lotto 0. Colonne `sorgente_id bigint` + `sorgente_uid uuid` (la `text` si converte), `sorgente_riga` resta (sempre NULL oggi). Unico nuovo: `(pratica_id, sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, ruolo_link) NULLS NOT DISTINCT`, **regola di dominio**; i tre `ON CONFLICT ON CONSTRAINT` DB e quello per colonne del BE cambiano bersaglio nello stesso lotto. Richiesta BE: `upsert_pratica_sorgente` e i suoi tre chiamanti, i cinque lettori BE |
| Non rientra (S-8) | niente |

##### A.2 `pratiche.reconcile_errori`

| Voce | Oggi (FATTO) |
| --- | --- |
| Colonne | `sorgente_tipo_id bigint` NULL — «Tipo sorgente … del documento che ha innescato il reconcile»; `sorgente_uid text` NULL — «UID del documento (chiave nativa castata a text)»; `pratica_id`, `flusso_id` **senza FK, di proposito** («log resiliente», commenti di colonna). Nessuna FK su `sorgente_tipo_id` |
| Scrittori | solo DB: `pratiche.trgfn_documento_reconcile_proiezione` (nel suo `EXCEPTION WHEN OTHERS`) e `pratiche.fn_reconcile_sorgente` (skip `E_RECONCILE_AMBIGUO`), entrambi dentro un blocco che su errore fa `RAISE WARNING` |
| Che valore scrive | l'unico trigger montato è `trg_preventivi_z90_reconcile_proiezione_upd` su `vendite.preventivi`, `tgargs ('2', 'uid')`: **l'id della sorgente scritto come letterale** (`'2'` = PREVENTIVO) e la colonna da leggere da `to_jsonb(NEW)`. Quindi oggi: tipo 2, uid del preventivo |
| Lettori | nessuna funzione, vista, BE o FE legge le righe; il codice `E_RECONCILE_AMBIGUO` è citato in `error_policies_generated.py:1465`; pgTAP 3 file |
| Indici | `ix_reconcile_errori_sorgente (sorgente_tipo_id, sorgente_uid)`, non unico. Nessun unico |
| Guard | nessuno |
| S-9 | è un log: la cancellazione del documento non deve toccarlo |
| Lotto | **P**, con `pratiche_sorgenti`: due colonne tipizzate scritte dal BB di scrittura (o, se il trigger di reconcile resta generico, il trigger passa al BB il tipo e la chiave). Il `'2'` in `tgargs` va sostituito dal codice (`'PREVENTIVO'`), come fanno già i trigger `trgfn_doc_guard_chiusura_sorgente` |
| Eccezione da far decidere (S-6) | **il guard d'esistenza non va montato qui**: il log serve proprio quando qualcosa è andato storto, e un guard che rifiuta lo farebbe cadere nel `RAISE WARNING`. Proposta: CHECK di forma (una sola chiave) sì, esistenza no; il presidio di struttura la deve elencare come eccezione dichiarata |

##### A.3 `documenti.documenti_generati` (G6)

| Voce | Oggi (FATTO) |
| --- | --- |
| Colonne | `sorgente_tipo_id bigint NOT NULL` (FK `documenti_generati_sorgente_tipo_id_fkey`, `ON DELETE RESTRICT`); `sorgente_uid text NOT NULL` (CHECK `chk_documenti_generati_sorgente_uid_non_vuoto`); `sorgente_riga bigint` NULL; `progressivo_sorgente integer NOT NULL` (CHECK `> 0`). **Nessun commento di colonna** |
| Scrittori | solo BE: `DocumentGenerationService.genera_documento` (`backend/apps/documenti/services/document_generation_service.py:192-330`), che **riceve già** `sorgente_id` (int) e `sorgente_uid` (str). Chiamanti: la factory `build_documenti_sorgente_views` (`documenti/api/sorgente_documenti_views.py:173-178` genera, `:234-239` ristampa) per i sei domini — preventivo, offerta, ordine, ddt, contratto, fattura (`vendite/api/*_documenti_views.py`) — sempre con `sorgente_uid=str(entity["uid"])`; il drainer `stampa_coda_drainer_service.py:288-293` con la chiave della coda (id::text). `sorgente_riga` **mai passato** (default `None`): sempre NULL |
| Valore per tipo | uid per PREVENTIVO, OFFERTA_COMMERCIALE, ORDINE_VENDITA, DDT_VENDITA, CONTRATTO; FATTURA **uid dalla UI, id dal drainer** (§0.2) |
| Lettori | BE: `documenti_repository.next_progressivo_sorgente` (`:1261-1290`, MAX+1 per `(tipo, uid, riga)`), `list_documenti_per_sorgente` (`:1382-1420`), le SELECT di dettaglio (`:1437`, `:1496`, `:1546`); `ai_assistant/tools/documenti_tools.py:120-135` (solo PREVENTIVO, risolve l'uid). DB: nessuna funzione legge la chiave (`trgfn_documenti_generati_check_coerenza` legge solo il tipo, via `fn_template_motivo_non_coerente`; `trgfn_documenti_generati_protect_snapshot` congela `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga`). FE: `documenti/components/DocumentiGeneratiSorgenteList.vue` (lista per sorgente via API) |
| Indici unici | `uq_documenti_generati_sorgente_progressivo (sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente) NULLS NOT DISTINCT` → **regola di dominio** (numerazione delle versioni per documento); `uq_documenti_generati_uid` → identità |
| Guard | nessun guard di sorgente; `trg_…_block_delete_dlt` (il documento generato non si cancella), `check_coerenza`, `protect_snapshot`, `guard_emittente_scope`, `guard_versione_contesto`, `require_attivo` sul tipo |
| RLS | `rls_documenti_generati_ef_whitelist` su `emittente_fiscale_id`: non tocca la sorgente |
| S-9 | i bersagli (preventivi, offerte, contratti: `DELETE` concesso e nessun trigger DELETE; ordini e ddt: solo bozza) si cancellano senza guardare `documenti_generati`. Per preventivo e offerta il documento si genera solo dopo l'emissione (`emetti_call` prima di `genera_documento`), quindi il caso reale è stretto; ma la regola sta nel percorso, non nel DB (IPOTESI: nessun DELETE di un documento emesso). Fattura: `trg_fatture_a05_guard_numero_fiscale_upd_dlt` |
| Lotto | **D** (documenti), dopo il lotto 0. `sorgente_id`/`sorgente_uid uuid` secondo `key_selector`; conversione S-5 (uid → id per ORDINE, DDT, CONTRATTO e la parte UI di FATTURA); **attenzione all'unico**: convertendo la fattura, le due serie di progressivi collidono su `(tipo, id, NULL, n)` → la conversione deve **rinumerare** o il vincolo cade. Da decidere prima (dato di test, one-shot manuale come S-6?). Unico nuovo `(tipo, sorgente_id, sorgente_uid, sorgente_riga, progressivo) NULLS NOT DISTINCT`. `protect_snapshot` prende `sorgente_id`. Richiesta BE: `genera_documento` scrive la chiave giusta (ha già entrambe), `next_progressivo_sorgente`, `list_documenti_per_sorgente`, la factory delle view, il drainer, il tool AI |

##### A.4 `documenti.template_documenti` (solo il tipo)

| Voce | Oggi (FATTO) |
| --- | --- |
| Colonne | solo `sorgente_tipo_id bigint NOT NULL` (FK, `ON DELETE RESTRICT`): il **tipo di documento** per cui vale il modello. Nessuna chiave |
| Indici unici | `uq_template_documenti_emittente_sorgente_codice`, `…_codice_interno`, `uq_template_documenti_default_attivo`, `uq_template_documenti_id_tipo_sorgente` → tutti **regola di dominio** sul catalogo dei modelli, non provenienze |
| Lettori | `documenti.fn_risolvi_template_applicabile`, `fn_template_motivo_non_coerente`, `fn_template_esito_risoluzione`, `fn_personalizza_template_standard`, `trgfn_template_documenti_versioni_guard_derivata_da`, tre viste `vw_template_*`; BE 15 file non di test; FE 6 file; pgTAP 22 |
| Valori oggi | i sei documenti (PREVENTIVO, OFFERTA_COMMERCIALE, ORDINE_VENDITA, DDT_VENDITA, CONTRATTO, FATTURA); **nessun `*_RIGA`** (FATTO su `zeroerp_ruoli`, seed) |
| Lotto | **fuori dal meccanismo**: non cambia. Due cose sole: (a) il **presidio di struttura** del lotto 0 non deve contarla fra le tabelle «con `sorgente_*` senza guard» — la chiave del presidio è la presenza di `sorgente_id`/`sorgente_uid`, non di `sorgente_tipo_id`; (b) S-2 la tocca solo se un modello nascesse su un tipo `*_RIGA`: oggi no |
| Stesso caso | `pratiche.template_flussi.attende_sorgente_tipo_id`, `vendite.attivita_fatturabili.sorgente_origine_tipo_id`, `vendite.documenti_fatturazione_canali.target_sorgente_tipo_id`: colonne di solo tipo, da escludere dal presidio con lo stesso criterio |

---

#### B. I BB del meccanismo

Legenda colonna «Lotto 0»: **S** = diventa (o fonda) il BB unico di **scrittura**; **R** = di **risoluzione**; **G** = il
**guard** unico; **O** = il presidio degli orfani / lato «in uscita»; **L** = lettore da riscrivere, non BB.

| BB | Che cosa legge oggi come chiave (FATTO) | Chi lo usa (DB / BE / pgTAP) | Che cosa cambia col modello | Lotto 0 |
| --- | --- | --- | --- | --- |
| `script.trgfn_guard_sorgente_polimorfa_tipizzata` | `key_selector='id'` → **`NEW.sorgente_riga`** come id del **documento**; `'uid'` → `NEW.sorgente_uid` (uuid). `EXECUTE format('… FROM %s WHERE id = $1', v_tbl::text)`. Rifiuta i tipi spenti (`attivo = true` nel filtro → `E_SORG_CONF`). Non controlla l'esclusività, non conosce la riga | montato su 10 tabelle: 6 di magazzino + `preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe` (`acquisti.ddt_righe` ha le colonne ma **non il guard** su questo DB). pgTAP 2 | legge `sorgente_id`/`sorgente_uid` secondo `key_selector`; verifica che `sorgente_riga` appartenga al documento (tabella righe + colonna FK dal catalogo) e `sorgente_dettaglio` alla riga; esclusività | **G** (si fonde con `_testuale` in uno solo) |
| `script.trgfn_guard_sorgente_polimorfa_testuale` | `sorgente_uid text` → `fn_sorgente_chiave_id/_uuid` secondo `key_selector`; non legge `sorgente_riga` | montato su `pratiche_sorgenti`, `commesse_sorgenti`. pgTAP 1 | si ritira (S-4: anche le G3 passano alle colonne tipizzate) | **G** (ritirato nel guard unico) |
| `script.fn_sorgente_chiave_id` / `_uuid` | forma canonica di una chiave testuale (`id::text`, `uuid::text`), `NULL` se non lo è | DB: i due guard, `pratiche.fn_stato_sorgente`, `script.fn_get_sorgente_emittente_sr_id`, `vendite.fn_documento_lineage_legami`, `fn_get_sorgente_documento_ref`, `fn_link_commessa_sorgente`, vista `script.vw_pratica_doc_sorgente` (**7**, non 8 come il §3.3); BE `pratiche_repository.py:104`. pgTAP 2 | servono ancora **solo dentro il BB di scrittura** (chi passa una chiave testuale qualsiasi) e nel resolver; spariscono da guard e lettori | **S/R** (interni) |
| `vendite.fn_link_commessa_sorgente` | normalizza: per un tipo `id` traduce l'uuid del chiamante in `id::text` (`EXECUTE 'SELECT id::text FROM %s WHERE uid = $1'`), formato non conforme → `E_SORG_FORMATO`, uuid non risolvibile → `E_SORG_NORM_NON_RISOLTA` | 4 funzioni DB, 37 pgTAP | è **già** la forma del BB di scrittura («riceve una chiave qualsiasi, salva quella giusta»), ristretta a una tabella: va estratto e generalizzato, poi questa lo chiama | **S** (modello da estrarre) |
| `vendite.fn_get_sorgente_documento_ref` | `(tipo, chiave text)` → `(documento_id, documento_numero)` via `target_table`, `key_selector`, `label_selector`, coi BB chiave | 7 funzioni + `vw_dash_competenza_gruppi`; BE 2; pgTAP 5 | è **già** il resolver: con le colonne tipizzate la firma prende `(tipo, sorgente_id, sorgente_uid)` (o resta testuale per i chiamanti di passaggio); i lettori col `CASE` per tipo (lineage) lo chiamano invece di tradurre | **R** (da promuovere a `script`) |
| `config.fn_sorgente_tabella` | schema/nome/oid della `target_table` **da `pg_class`** (commento: «⛔ Mai `target_table::text`») | 5 funzioni (storia emittente BA, famiglie, `fn_fattura_origini`), pgTAP 4, BE 1 | il guard unico e il resolver la usano al posto di `v_tbl::text` (oggi i guard, gli orfani e `fn_link_commessa_sorgente` usano `%s` col testo del `regclass`: corretto finché testo e uso stanno nella stessa sessione, ma è la seconda via per lo stesso dato — regola del 2). Serve la gemella per tabella righe e dettaglio | **R** (base comune) |
| `dbops.fn_sorgenti_orfane` + `fn_sorgenti_orfane_perimetro` + `vw_sorgenti_orfane` | per `key_selector='id'` cerca il documento con **`sorgente_riga`**; il perimetro esige `sorgente_riga` **e** `sorgente_uid` **e** il guard `_tipizzata` montato → copre solo le 10 tabelle del guard tipizzato (per questo i 387 orfani di `documenti_fatturazione_canali` non c'erano); `pratiche_sorgenti`, `commesse_sorgenti`, `documenti_generati` ne sono fuori | pgTAP 2 (+1 la vista) | il perimetro si ricava **dal guard unico** (ogni tabella che lo monta), la chiave da `sorgente_id`/`sorgente_uid`; aggiunge riga e dettaglio orfani | **O** |
| `script.vw_stato_sorgente` + i sei `vendite.vw_stato_sorgente_*` | ogni ramo espone **già** `sorgente_chiave_uuid` (preventivo, offerta) e `sorgente_chiave_id` (ordine, contratto, ddt, reso), più `sorgente_uid text` (uid o `id::text`) | `pratiche.fn_stato_sorgente`, `fn_reconcile_sorgente` (via la prima), `script.vw_pratica_doc_sorgente`; BE `pratiche_repository.py:104`; FE 1; pgTAP 3 | è già nel modello: le due colonne native si rinominano `sorgente_id`/`sorgente_uid`, la `text` si ritira quando l'ultimo lettore (BE `_doc_sorgente_lateral`) è riscritto. Nessun ramo per FATTURA, COMMESSA: non serve oggi | **R** (proiezione di stato) |
| `script.vw_pratica_doc_sorgente` | `pratiche_sorgenti.sorgente_uid` text → due rami coi BB chiave | `pratiche.fn_stato_sorgente`, `vendite.fn_get_sorgente_documento_ref` (citazioni), BE 1, pgTAP 4 | join diretto `(tipo, sorgente_id, sorgente_uid)`, i due rami spariscono | **L** (lotto P) |
| `pratiche.fn_stato_sorgente(tipo, uid text)` | prova prima uuid, poi id, con i BB chiave; sentinella `UNKNOWN` | `fn_reconcile_sorgente`; BE 2; pgTAP 4 | firma tipizzata (o passa dal resolver); i due rami spariscono | **L** (lotto P) |
| `pratiche.fn_reconcile_sorgente(tipo, uid text)` | `ps.sorgente_uid = p_sorgente_uid` (testo) | `trgfn_documento_reconcile_proiezione`; BE 4; FE 1; pgTAP 2 | come sopra; scrive `reconcile_errori` tipizzata | **L** (lotto P) |
| `pratiche.trgfn_documento_reconcile_proiezione` | `tgargs ('2','uid')`: id della sorgente come **letterale** + nome della colonna chiave | montato solo su `vendite.preventivi`; pgTAP 0 diretti | il tipo per **codice**; la chiave la sceglie il catalogo (`key_selector`), non il `tgargs`: un trigger generico «documento cambia stato → reconcile» non deve sapere quale colonna leggere | **L** (lotto P); candidato a usare il resolver |
| `script.fn_check_sorgente_chiudibile(tipo, uid text)` | `commesse_attivita.sorgente_uid = btrim(p)` (G4: **sempre l'uid**) | `fn_check_ordine_annullabile`, `fn_check_preventivo_annullabile` (`v_uid::text`), `fn_documento_ritira_legami`, `fn_ritira_commessa_attivita_da_sorgente`, `trgfn_doc_guard_chiusura_sorgente` (`to_jsonb(NEW)->>'uid'` su ordini, ddt, contratti); BE 1; pgTAP 3 | dopo S-5 su `commesse_attivita` **tutti i chiamanti** passano l'id per ORDINE/DDT/CONTRATTO: firma tipizzata e chiamanti nello stesso lotto della tabella | **L** (lotto C) |
| `script.fn_get_sorgente_emittente_sr_id(tipo, uid text)` | `target_table` + `key_selector` + BB chiave; legge `emittente_soggetto_ruolo_id` / `emittente_fiscale_id` / `billing_account_id` dalla tabella | `vendite.fn_check_commessa_sorgente_emittente_omogeneo`, `fn_guard_commessa_sorgente_emittente`; BE 1; pgTAP 1 | diventa un **utente del resolver** (risolve il documento, poi legge l'emittente) | **R** (consumatore) |
| `vendite.fn_commessa_viva_di_sorgente(tipo, chiave text)` | `cs.sorgente_uid = p_sorgente_chiave` (G3) | `fn_link_commessa_sorgente`, `trgfn_guard_fatturazione_immediata_immutabile`; BE (`CommesseRepository.get_commessa_viva_by_sorgente`, chiamato con l'**uid** del preventivo, `preventivi_service.py:2083`) | firma tipizzata | **L** (lotto C) |
| `vendite.fn_ritira_commessa_attivita_da_sorgente` | `ca.sorgente_uid = v_uid` (G4) | `fn_documento_legami`, `fn_documento_ritira_legami` | firma tipizzata, chiamanti con l'id | **L** (lotto C) |
| `magazzino.fn_storna_movimenti_sorgente(tipo, righe bigint[])` | `m.sorgente_riga = ANY(...)` (G2: la riga, o il prelievo, come chiave unica) | `vendite.fn_annulla_reso`, `fn_cambia_stato_ddt` | con S-3: documento + riga + dettaglio | **L** (lotto M) |
| `script.fn_segment_key` / `fn_segment_key_sorgente` | costruttore della chiave d'idempotenza del push (`'<CODICE>:<uid>'`) | 11 funzioni + 4 viste | **non è una provenienza** (K-1 lo lascia): resta, ma la chiave d'idempotenza oggi usa l'uid anche per tipi `id` (`fn_list_consumi_da_pushare`: `ac.uid::text`, tipo ATTIVITA_CONSUMI `key_selector='id'`). Non va «convertita» con S-5: cambierebbe ogni chiave già emessa | fuori; da dichiarare nella guida |
| `vw_sorgenti_consumatori` | **non esiste** (FATTO: nessun oggetto con quel nome) | — | è il presidio «chi legge le sorgenti» che il lotto 0 può far nascere insieme al presidio di struttura | da creare (proposta) |

**Fixture pgTAP che scrivono il catalogo o le sorgenti** (seguono i lotti): `dbops.fn_pgtap_crea_sorgente` (legge
`categoria`, `key_selector`: va aggiornata quando il catalogo prende le colonne delle righe),
`fn_pgtap_crea_commessa`, `fn_pgtap_crea_commessa_attivita`, `fn_pgtap_crea_reso`, `fn_pgtap_fattura_attivita`.

**Errori del meccanismo** (`E_SORG_*`): 5 pgTAP, 3 file BE (policy generate); il guard unico li eredita,
`E_SORG_FORMATO` resta solo nel BB di scrittura (una chiave testuale malformata), si aggiungono quelli di riga e dettaglio
(«riga non del documento»), da registrare in `codici_errore.csv`/`messaggi_errore.csv`.

---

#### C. Il catalogo e i codici

##### C.1 `config.sorgenti` — chi legge le colonne (FATTO, `zeroerp_ruoli`)

29 righe. Colonne di comportamento e loro lettori:

| Colonna | Lettori DB | Lettori BE | Nota |
| --- | --- | --- | --- |
| `categoria` (`DOCUMENTO`/`RIGA`, **lock**: `trg_sorgenti_a10_lock_columns_upd`) | nessuna funzione la legge per decidere; solo le fixture `dbops.fn_pgtap_crea_sorgente`, `fn_pgtap_crea_commessa_attivita` | `vendite/db/famiglie_repository.py:339` (`CATEGORIA_SORGENTE_DOCUMENTO`, `apps/config/sorgenti.py:45`) | il ritiro dei `*_RIGA` lascia `RIGA` su `ATTIVITA`, `EVENTO_ASSET`, `DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`, `INVENTARIO_RIGA`… (S-3, S-10). Essendo bloccata, una correzione di categoria è un DELETE+INSERT del tipo |
| `scope` (CHECK con 9 valori) | `vendite.fn_upsert_commessa_attivita` (`s.scope = 'PUSH_COMMESSA'`) | `vendite/db/commesse_repository.py:447-480` (allinea `_SORGENTE_FN_MAP` ai tipi `PUSH_COMMESSA`) | `ROW_VALIDATOR` è lo scope **solo** dei sei `*_RIGA` di vendita e **nessuno lo legge** (DB, BE; solo il commento `vendite/types.py:1476` e il pgTAP `config/test-sorgenti-scope-pulizia-v1`): col ritiro il valore esce dal CHECK |
| `target_table` (`regclass`) | 9: i due guard, `dbops.fn_sorgenti_orfane`, `script.fn_get_sorgente_emittente_sr_id`, `vendite.fn_get_sorgente_documento_ref`, `fn_link_commessa_sorgente`, `config.fn_sorgente_tabella`, `script.trgfn_doc_stato_iniziale`, `trgfn_doc_stato_solo_dal_verbo` | via `fn_sorgente_tabella` (1 file) | resta la tabella del **documento** |
| `key_selector` | 17 funzioni (elenco in §D: guard, orfani, resolver, `fn_check_ordine/preventivo_annullabile`, `fn_accoda_stampe_lotto`, `fn_fattura_origini`, `fn_genera_ddt_riconsegna`, `fn_push_preventivo_a_ordine`, `trgfn_guard_fatturazione_immediata_immutabile`, due fixture); nessuna vista | — | resta (K-1); diventa il selettore della **colonna** (`sorgente_id` o `sorgente_uid`), non più della forma del testo |
| `tipo_doc_fiscale_id` | `vendite.fn_get_tipo_doc_fiscale_id` ← `trgfn_attivita_fatturabili_normalize` | — | i `*_RIGA` hanno lo stesso valore della testata (PREVENTIVO_RIGA 2 = PREVENTIVO 2; gli altri 1 = 1): ritirarli non cambia il risultato |
| `label_selector`, `etichetta`, `apribile`, `citato_in_fattura` | resolver, stampa, `fn_fattura_origini` | sì | i `*_RIGA` hanno `label_selector` NULL, `citato_in_fattura = false`: non pesano |

⚠️ **Il manuale cita la colonna `area`** (§«Area documentale», aggiunta 27-07-2026) **che su `zeroerp_ruoli` non
esiste** (FATTO: `\d config.sorgenti`). O è stata ritirata senza aggiornare il manuale, o il DB di scratch è indietro:
da verificare sul `databasechangelog` di dbdev. Fuori dal perimetro, ma il manuale si riscrive nello stesso lotto (§3.5).

**Le FK verso il catalogo.** 34 vincoli referenziano `config.sorgenti` (29 su `id`, 5 su `codice_interno`:
`config.tipi_entita`, `config.nature_vendita`, `config.tipi_indirizzi_allowed`, `vendite.famiglie_documento`,
`vendite.ordini.documento_origine_tipo`). Per ognuna c'è un `trg_sorgenti_a10_<tabella>_block_deact_upd`
(`dbops.trgfn_prevent_deactivate_if_children`): **un tipo `*_RIGA` non si spegne finché una riga lo usa** — conferma
l'ordine del §7.2 (convertire, poi spegnere). I valori di `nature_vendita`, `tipi_indirizzi_allowed`,
`famiglie_documento`, `template_documenti`, `template_flussi` sono tutti documenti: **nessun `*_RIGA`**.

##### C.2 Che cosa serve aggiungere al catalogo (lotto 0)

Mappa documento → righe → colonna FK, **ricavata oggi da `pg_constraint`** (FATTO) e da dichiarare come dato:

| Documento | Tabella righe | Colonna FK verso il documento | Dettaglio (S-3) | Colonna FK verso la riga |
| --- | --- | --- | --- | --- |
| PREVENTIVO | `vendite.preventivi_righe` | `preventivo_id` | — | — |
| CONTRATTO | `vendite.contratti_righe` | `contratto_id` | — | — |
| ORDINE_VENDITA | `vendite.ordini_righe` | `ordine_id` | — | — |
| DDT_VENDITA | `vendite.ddt_righe` | `ddt_id` | `vendite.ddt_righe_prelievi` | `ddt_riga_id` |
| FATTURA | `vendite.fatture_righe` | `fattura_id` | — | — |
| RESO_VENDITA | `vendite.resi_righe` | `reso_id` | `vendite.resi_righe_rientri` | `resi_riga_id` |
| ORDINE_ACQUISTO | `acquisti.ordini_righe` | `ordine_id` | — | — |
| DDT_ACQUISTO | `acquisti.ddt_righe` | `ddt_id` | — | — |
| INVENTARIO / RETTIFICA / TRASFERIMENTO | `magazzino.*_righe` | `inventario_id` / `rettifica_id` / `trasferimento_id` | — | — |
| COMMESSA | (G5) `vendite.commesse_attivita` | `commessa_id` | — | — |
| OFFERTA_COMMERCIALE | **nessuna tabella righe**: le righe espanse vengono da listino **o** da `offerte_commerciali_eccezioni` (`offerta_id`) | — | — | — |

Proposta di colonne: `righe_table regclass`, `righe_fk_column name`, `dettaglio_table regclass`,
`dettaglio_fk_column name`, con un presidio (pgTAP o CHECK di convergenza in `90_end`) che verifichi in
`pg_constraint` che la FK dichiarata esiste davvero — dichiarata, non ricavata, come chiede il §7.2.

⚠️ **Per OFFERTA_COMMERCIALE e COMMESSA il modello va precisato** (da far decidere): la riga d'offerta è polimorfa
(listino/eccezione) e `fn_offerta_righe_espanse` oggi **non restituisce un id di riga** (firma:
`… origine character varying, componenti jsonb`), quindi S-1 («restituisce la riga d'origine») è ancora da costruire;
la «riga» della COMMESSA è `commesse_attivita` (G5, S-7), che però è anche tabella con sorgente propria.

##### C.3 `config.tipi_entita` (FATTO)

* 39 righe; `is_sorgente = true` su 29, cioè **tutte** le sorgenti (non solo le 11 `*_RIGA`); colonna generata
  `sorgente_codice_interno` + FK `fk_tipi_entita_sorgenti` → `config.sorgenti(codice_interno)`, **senza `ON DELETE`**:
  una riga `*_RIGA` di `config.sorgenti` non si cancella finché la gemella in `tipi_entita` ha `is_sorgente = true`.
  Conferma l'ordine del §7.2: prima `is_sorgente = false`, poi il ritiro.
* `key_selector` di `tipi_entita` è `id` per tutti (anche PREVENTIVO e OFFERTA): è K-1 (aprire ≠ collegare).
* **Lettori di `tipi_entita` nel DB** (7): `vendite.trgfn_event_log_deriva_scope` (accetta solo i tipi con
  `modo_risoluzione_emittente` NOT NULL: COMMESSA, FATTURA, LOTTO → **nessun `*_RIGA` è giornalabile**, il giornale
  non li usa); `script.fn_check_articolo_riga_su_contesto` (`%TYPE`); `dbops.vw_bersagli_non_dichiarati` (bersagli
  d'errore nei corpi plpgsql); `dbops.vw_eventi_non_dichiarati`; citazioni in commento in `fn_log_and_raise_error`,
  `fn_cancella_fondo_fattura`, `fn_push_preventivo_a_ordine`. **Nessuno legge `is_sorgente`.**
* **Note.** Le partizioni delle note per `target_tipo`: vendite `ATTIVITA`, `CONTRATTO`, `DDT_VENDITA`, `FATTURA`,
  `OFFERTA_COMMERCIALE`, `ORDINE_VENDITA`, `PREVENTIVO` (+ `anchor_tipo DOCUMENTO|RIGA` e `target_riga_id`: **le note
  di vendita usano già «tipo del documento + riga»**, il modello di Tid); magazzino ha invece partizioni **per riga**
  (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `EVENTO_ASSET`) e la stessa coppia `anchor_tipo`/
  `target_riga_id`: due grammatiche anche lì. Nessuna partizione per un `*_RIGA` di vendita. Scope:
  `script.fn_scope_note_ef_perimetro` (vendite, incluso `ATTIVITA`) e `fn_scope_note_magazzino_ef_perimetro`
  (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `EVENTO_ASSET`). **Il §3.3 del brief attribuisce i
  `*_RIGA` a `fn_scope_note_ef_perimetro`: non li nomina** (li nomina solo la variante di magazzino).
* **Ritirando i `*_RIGA` di vendita da `config.sorgenti`**: in `tipi_entita` le sei righe restano (entità «riga di
  …», `etichetta_key config.tipi_entita.<x>_riga`), con `is_sorgente = false`. Oggi nessun giornale, nota o bersaglio
  d'errore le usa nel DB (FATTO sul codice; i dati non li misura questo DB vuoto).

##### C.4 Consumatori dei codici (DB, BE, FE, pgTAP, seed)

| Codice | DB (funzioni/viste/trigger/CHECK) | BE | FE | pgTAP | Seed CSV |
| --- | --- | --- | --- | --- | --- |
| `PREVENTIVO_RIGA` | nessuno; i guard lo risolvono per id via `target_table` | nessuno | `locales/it.json:5974`, `en.json:5974` (`config.tipi_entita.preventivo_riga`) | 4: `vendite/test-fattura-origini-v1:93`, `test-documento-lineage-seminata-v1:137` (**lotto A, modificati non committati**, scrivono la sorgente di `ordini_righe`), `config/test-sorgenti-scope-pulizia-v1:111`, `magazzino/test-causali-e-sorgenti-seed-v1:99` | `sorgenti.csv:12`, `tipi_entita.csv:19` |
| `CONTRATTO_RIGA` | nessuno | nessuno | locales `:5975` | 2 (scope-pulizia, causali-seed) | `sorgenti.csv:13`, `tipi_entita.csv:20` |
| `ORDINE_VENDITA_RIGA` | `vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna` (solo etichetta `'tipo'` nel `jsonb` dell'errore `E_RIGA_ONERE_DATA_CONSEGNA`, non una sorgente) | `error_policies_generated.py:1588` (commento) | locales `:5976` | 2 | `sorgenti.csv:14`, `tipi_entita.csv:21`; `codici_errore.csv:1164` (testo) |
| `DDT_VENDITA_RIGA` | nessuno | nessuno | locales `:5977` | 2 | `sorgenti.csv:15`, `tipi_entita.csv:22` |
| `FATTURA_RIGA` | nessuno | nessuno | locales `:5978` | 2 | `sorgenti.csv:16`, `tipi_entita.csv:23` |
| `RESO_VENDITA_RIGA` | nessuno | nessuno | locales `:5979` | 2 | `sorgenti.csv:17`, `tipi_entita.csv:24` |
| `ATTIVITA` **come sorgente** (id 1, `RIGA`, `PIPELINE_MARKER`, `vendite.attivita_fatturabili`) | **nessuno lo scrive né lo legge come sorgente** (nessun letterale, nessun `codice_interno = 'ATTIVITA'`); è solo parent FK del tipo entità e ha `tipo_doc_fiscale_id = 1` | nessuno (`apps/config/sorgenti.py` non ha la costante); solo `config/tests/db/test_sorgenti_repository.py:71` come stringa d'esempio | nessuno | nessuno | `sorgenti.csv:3` |
| `ATTIVITA` **come tipo entità** (note, scope) | partizione `vendite.note_attivita_fatturabili`, `script.fn_scope_note_ef_perimetro` | — | locales `tipi_entita.attivita` | `vendite/test-attivita-fatturabili.sql:411,440` (`n.target_tipo = 'ATTIVITA'`) | `tipi_entita.csv:16` |
| `ATTIVITA_CONSUMI` | `vendite.fn_list_consumi_da_pushare` (risolve il tipo, scrive `sorgente_uid = ac.uid::text` e `fn_segment_key('ATTIVITA_CONSUMI', ac.uid::text)` con `key_selector = 'id'`: **G4**) | `apps/config/sorgenti.py:56` (`SORGENTE_ATTIVITA_CONSUMI`), `commesse_source_handlers.py:930`, `api/views.py:1766` (help text), `_annullo_con_legami.py:84`; test 4 file | `vendite/dashboardAree.spec.js:49`, `_shared/annullo/DocumentoAnnulloLegamiDialog.spec.js:200-225`; locales `attivita_consumi` | 11 file | `sorgenti.csv:8`, `tipi_entita.csv` |

Lettura per S-2 e S-10 (IPOTESI da confermare coi dati di dbdev): il ritiro dei sei `*_RIGA` di vendita, lato codice,
tocca **solo seed, locales e due pgTAP di catalogo**, più le righe scritte dal lotto A non committato. `ATTIVITA` come
sorgente è oggi un tipo **senza scrittori**: per S-10 è il primo candidato a «non è un documento», e la sua voce in
`config.sorgenti` esiste solo per far da genitore alla FK di `tipi_entita` (dove serve, per le note). `ATTIVITA_CONSUMI`
è un documento (testata `vendite.attivita_consumi`) scritto con l'uid sotto `key_selector = 'id'`: rientra in S-5 sulle
tabelle commesse, ma la sua `segment_key` no (vedi §B, `fn_segment_key`).

---

#### D. I numeri del §3.3 ricontati, e la lista per lotto

##### D.1 Metodo e risultato (2026-11-06, `zeroerp_ruoli`)

| Misura | Metodo | Brief | Oggi | Nota |
| --- | --- | --- | --- | --- |
| funzioni | `pg_proc.prosrc ~ 'sorgente_(uid\|riga\|tipo_id)'`, schemi applicativi | 92 | **92** (vendite 54, script 16, dbops 7, magazzino 6, documenti 5, pratiche 4) | riprodotto |
| funzioni `BEGIN ATOMIC` | `pg_get_functiondef` sulle stesse colonne, per chi ha `prosrc` vuoto | — | **+6** (vendite 3, documenti 2, pratiche 1) | cieco del metodo del brief |
| perimetro vero | unione | — | **98** | di cui 4 solo nei commenti, 13 solo `sorgente_tipo_id` |
| viste | `pg_views.definition ~ …` | 26 | **26** (vendite 15, dbops 5, script 3, documenti 3) | riprodotto; 3 delle documenti solo il tipo |
| scrivono la sorgente | `INSERT`/`UPDATE … SET` con una colonna `sorgente_*`, `NEW.sorgente_* :=`, o `p_sorgente_* =>` verso un verbo | 19 | **29** | il metodo largo conta anche i passaggi di parametro e 3 fixture pgTAP; `documenti_generati` non ha scrittori DB (solo BE) |
| leggono `key_selector` | `pg_get_functiondef ~ 'key_selector'` | 16 | **17** funzioni, 0 viste | 16 col solo `prosrc`; la 17ª è `dbops.fn_pgtap_crea_sorgente` |
| usano i BB chiave | chiamano `fn_sorgente_chiave_id/_uuid` | 8 | **6 funzioni + 1 vista** | |
| BE file | `grep -rlE 'sorgente_(uid\|riga\|tipo_id)' backend --include=*.py` | 79 | **79** (71 in `apps`, 31 non di test) | |
| FE file | stesso su `frontend/src` | 10 | **10** (8 file di codice + 2 locales, elenco sotto) | |
| pgTAP file | stesso su `db/pgtap` | 165 | **166** | +1 da un test nuovo |

FE (10): `config/stores/templateDocumenti.js`, `config/components/TemplateDocumentiSearchTable.vue`,
`TemplateDocumentoDrawer.vue`, `TemplateRisoluzionePannello.vue` (solo il tipo del modello),
`pratiche/components/FlussoDrawer.vue`, `vendite/components/CommessaGestioneDrawer.vue`,
`vendite/offerte/stores/offerte.js`, `vendite/offerte/api/offerteApi.js`, `locales/it.json`, `locales/en.json`.

**Funzioni solo nei commenti** (non cambiano): `dbops.fn_pgtap_fattura_attivita`, `pratiche.fn_copia_definizione`,
`script.fn_check_preventivo_annullabile` (ma è **chiamante** di `fn_check_sorgente_chiudibile` con l'uid: lotto C),
`script.fn_segment_key_sorgente`.
**Solo `sorgente_tipo_id`** (fuori dal meccanismo, salvo nota): `dbops.trgfn_child_requires_non_obsolete_parent`,
`documenti.fn_personalizza_template_standard`, `fn_risolvi_template_applicabile`, `fn_template_motivo_non_coerente`,
`fn_template_esito_risoluzione`, `trgfn_documenti_generati_check_coerenza`,
`trgfn_template_documenti_versioni_guard_derivata_da`, `magazzino.fn_libera_blocco`,
`vendite.fn_get_tipo_doc_fiscale_id`, `script.fn_check_ddt_riga_correggi_qta_evasa`, le viste
`documenti.vw_template_versioni_stampabili`, `vw_template_risoluzione_emittente`, `vw_template_personalizzati_scarto`.

##### D.2 Lista nominativa per schema

Colonne: le tabelle con `sorgente_*` **nominate qualificate** nel corpo (euristica: chi passa per `NEW`, parametri o
SQL dinamico ha la tabella di montaggio); «Scrive» = `INSERT`/`UPDATE` su quelle tabelle; segni: `KS` legge
`key_selector`, `CHIAVE` usa i BB chiave, `TT` legge `target_table`, `ATOMIC` corpo `BEGIN ATOMIC`, i codici nominati.
**Lotto proposto**: `0` trasversale; `R` righe di vendita; `T` testate G1; `C` commesse/fatturazione (G3 commesse, G4,
G5); `D` documenti (G6, G7, canali); `M` magazzino; `P` pratiche; combinazioni = la funzione tocca più famiglie e va
riscritta nel **primo** lotto che le cambia una chiave, poi ritoccata. È una proposta da incrociare con gli altri
censimenti di famiglia.

###### Funzioni `dbops` (7)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_pgtap_crea_commessa` | vendite.commesse_attivita, vendite.commesse_sorgenti | commesse_sorgenti | KS | segue la tabella (fixture pgTAP) |
| `fn_pgtap_crea_commessa_attivita` | vendite.commesse_attivita | — | ATTIVITA | segue la tabella (fixture pgTAP) |
| `fn_pgtap_crea_reso` | vendite.ddt, vendite.ddt_righe, vendite.resi | resi | — | segue la tabella (fixture pgTAP) |
| `fn_pgtap_fattura_attivita` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture, vendite.fatture_righe | attivita_fatturabili, fatture_righe | — | — (solo commento) |
| `fn_sorgenti_orfane` | — (NEW / parametri / SQL dinamico) | — | KS TT | 0 |
| `fn_sorgenti_orfane_perimetro` | — (NEW / parametri / SQL dinamico) | — | KS | 0 |
| `trgfn_child_requires_non_obsolete_parent` | montato su pratiche.flussi, pratiche.pratiche, vendite.commesse_attivita, vendite.listini_kit | — | — | — (solo il tipo) |

###### Funzioni `documenti` (7)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_personalizza_template_standard` | documenti.template_documenti | template_documenti | — | — (solo il tipo) |
| `fn_risolvi_template_applicabile` | documenti.template_documenti | — | — | — (solo il tipo) |
| `fn_template_esito_risoluzione` | — (NEW / parametri / SQL dinamico) | — | ATOMIC | — (solo il tipo) |
| `fn_template_motivo_non_coerente` | documenti.template_documenti | — | ATOMIC | — (solo il tipo) |
| `trgfn_documenti_generati_check_coerenza` | montato su documenti.documenti_generati | — | — | — (solo il tipo) |
| `trgfn_documenti_generati_protect_snapshot` | montato su documenti.documenti_generati | — | — | D |
| `trgfn_template_documenti_versioni_guard_derivata_da` | documenti.template_documenti; montato su documenti.template_documenti_versioni | — | — | — (solo il tipo) |

###### Funzioni `magazzino` (6)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_libera_blocco` | magazzino.movimenti_attesi | movimenti_attesi | — | — (solo il tipo) |
| `fn_posta_inventario` | magazzino.inventari | inventari | INVENTARIO_RIGA | M |
| `fn_posta_rettifica` | magazzino.rettifiche | rettifiche | RETTIFICA_RIGA | M |
| `fn_posta_trasferimento` | magazzino.trasferimenti | trasferimenti | TRASFERIMENTO_RIGA | M |
| `fn_scrivi_movimento` | magazzino.movimenti | movimenti | — | M |
| `fn_storna_movimenti_sorgente` | magazzino.movimenti | — | — | M |

###### Funzioni `pratiche` (5)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_copia_definizione` | — (NEW / parametri / SQL dinamico) | — | — | — (solo commento) |
| `fn_pratica_del_documento` | pratiche.pratiche_sorgenti | — | ATOMIC | P (pratiche) |
| `fn_reconcile_sorgente` | pratiche.pratiche_sorgenti, pratiche.reconcile_errori | reconcile_errori | — | P (pratiche) |
| `fn_stato_sorgente` | — (NEW / parametri / SQL dinamico) | — | CHIAVE | 0 |
| `trgfn_documento_reconcile_proiezione` | pratiche.pratiche_sorgenti, pratiche.reconcile_errori; montato su vendite.preventivi (tgargs 2, uid) → pratiche_sorgenti, reconcile_errori | reconcile_errori | — | P (pratiche) |

###### Funzioni `script` (16)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_available_actions_ddt` | vendite.ddt, vendite.ddt_righe | — | — | R+T |
| `fn_available_actions_reso` | vendite.resi | — | — | T |
| `fn_check_ddt_emittibile` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe | — | — | R+T |
| `fn_check_ddt_riga_correggi_qta_evasa` | vendite.ddt, vendite.ddt_righe | — | — | — (solo il tipo) |
| `fn_check_disponibilita_uscita` | magazzino.movimenti, magazzino.movimenti_attesi | — | — | M |
| `fn_check_ordine_annullabile` | vendite.commesse_attivita, vendite.commesse_sorgenti, vendite.ddt, vendite.ordini | — | KS | T+C |
| `fn_check_preventivo_annullabile` | vendite.ordini | — | KS | — (solo commento) |
| `fn_check_sorgente_chiudibile` | vendite.commesse_attivita, vendite.commesse_sorgenti | — | — | C |
| `fn_get_sorgente_emittente_sr_id` | — (NEW / parametri / SQL dinamico) | — | KS CHIAVE TT | 0 |
| `fn_gruppi_di_commessa_nel_lotto` | vendite.commesse_attivita | — | — | C |
| `fn_segment_key_sorgente` | — (NEW / parametri / SQL dinamico) | — | — | — (solo commento) |
| `fn_sorgente_chiave_id` | — (NEW / parametri / SQL dinamico) | — | KS CHIAVE | 0 |
| `fn_sorgente_chiave_uuid` | — (NEW / parametri / SQL dinamico) | — | CHIAVE | 0 |
| `trgfn_default_emittente_fiscale` | montato su 11 testate (emittente, non sorgente) | — | — | T (legge `sorgente_tipo_id`+`sorgente_uid` della riga per l'emittente) |
| `trgfn_guard_sorgente_polimorfa_testuale` | montato su pratiche.pratiche_sorgenti, vendite.commesse_sorgenti | — | KS CHIAVE TT | 0 |
| `trgfn_guard_sorgente_polimorfa_tipizzata` | montato su 6 magazzino + 4 righe vendita (preventivi/ordini/ddt/contratti_righe) | — | KS TT | 0 |

###### Funzioni `vendite` (57)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `fn_accoda_stampe_lotto` | vendite.fatture, vendite.fatture_stampa_coda | fatture_stampa_coda | KS | T+D |
| `fn_accredita_riga_reso` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.ddt, vendite.ddt_righe, vendite.fatture, vendite.fatture_righe, vendite.ordini, vendite.ordini_righe | — | — | R+T+C |
| `fn_aggiungi_onere_commessa` | vendite.commesse_attivita | — | — | C |
| `fn_annulla_commessa_attivita` | vendite.commesse_attivita | commesse_attivita | — | C |
| `fn_annulla_reso` | vendite.commesse_attivita, vendite.ddt, vendite.ddt_righe, vendite.ordini_righe, vendite.resi | — | RESO_VENDITA_RIENTRO | R+T+C |
| `fn_batch_upsert_commessa_attivita` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_build_gruppo_fatturabile_key` | vendite.commesse_attivita | — | — | C |
| `fn_check_commessa_sorgente_emittente_omogeneo` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_commessa_viva_di_sorgente` | vendite.commesse_sorgenti | — | — | C |
| `fn_conferma_reso` | vendite.ddt, vendite.ddt_righe, vendite.ordini_righe, vendite.resi | — | — | R+T |
| `fn_contratti_addebiti_maturati` | vendite.commesse_attivita, vendite.contratti, vendite.contratti_righe | — | — | R+T+C |
| `fn_ddt_push_diagnosi` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe | — | ATOMIC | R+T |
| `fn_ddt_trigger_ordine_testata` | vendite.ordini | — | ATOMIC | T |
| `fn_ddt_vincoli_cliente` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe, vendite.resi | — | — | R+T |
| `fn_documento_legami` | vendite.commesse_attivita, vendite.contratti, vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe, vendite.preventivi_righe | — | — | R+T+C |
| `fn_documento_lineage_archi` | vendite.attivita_fatturabili, vendite.commesse_sorgenti, vendite.contratti, vendite.ddt, vendite.ddt_righe, vendite.fatture, vendite.fatture_righe, vendite.ordini, vendite.resi | — | ATOMIC | R+T+C |
| `fn_documento_lineage_legami` | vendite.commesse_attivita, vendite.contratti, vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe, vendite.preventivi_righe | — | CHIAVE | R+T+C |
| `fn_documento_ritira_legami` | vendite.commesse_attivita, vendite.contratti, vendite.ddt, vendite.ddt_righe, vendite.ordini_righe, vendite.preventivi_righe | ordini_righe | — | R+T+C |
| `fn_emit_attivita_fatturabili_da_commessa` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.commesse_sorgenti | attivita_fatturabili, commesse_attivita | — | C |
| `fn_esito_gruppi_giro` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture_righe | — | — | C |
| `fn_fattura_origini` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture_righe | — | KS | C |
| `fn_genera_ddt_da_ordine` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe | ddt, ddt_righe | — | R+T |
| `fn_genera_ddt_riconsegna` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe, vendite.resi | ddt, ddt_righe | KS | R+T |
| `fn_genera_pratica_da_preventivo` | pratiche.pratiche_sorgenti | pratiche_sorgenti | — | P (pratiche) |
| `fn_get_sorgente_documento_ref` | vendite.commesse_attivita | — | KS CHIAVE TT | 0 |
| `fn_get_tipo_doc_fiscale_id` | — (NEW / parametri / SQL dinamico) | — | — | — (solo il tipo) |
| `fn_guard_commessa_sorgente_emittente` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_link_commessa_sorgente` | vendite.commesse_sorgenti | commesse_sorgenti | KS CHIAVE TT | C |
| `fn_list_commessa_attivita` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture, vendite.fatture_righe | — | — | T+C |
| `fn_list_consumi_da_pushare` | — (NEW / parametri / SQL dinamico) | — | ATTIVITA_CONSUMI | C |
| `fn_list_contratti_da_pushare` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_list_ddt_da_pushare` | vendite.ddt, vendite.ddt_righe, vendite.ordini, vendite.ordini_righe | — | — | R+T |
| `fn_list_ordini_da_pushare` | vendite.ordini, vendite.ordini_righe | — | — | R+T |
| `fn_list_preventivi_da_pushare` | vendite.preventivi_righe | — | — | R |
| `fn_posta_ddt` | vendite.ddt, vendite.ddt_righe | — | DDT_VENDITA_PRELIEVO | R+T |
| `fn_posta_reso` | magazzino.movimenti, vendite.ddt_righe, vendite.resi | — | DDT_VENDITA_PRELIEVO RESO_VENDITA_RIENTRO | R+T+M |
| `fn_push_offerta_a_contratto` | pratiche.pratiche_sorgenti, vendite.contratti, vendite.contratti_righe | pratiche_sorgenti, contratti, contratti_righe | — | R+T+P |
| `fn_push_preventivo_a_ordine` | pratiche.pratiche_sorgenti, vendite.ordini, vendite.ordini_righe | pratiche_sorgenti, ordini, ordini_righe | KS | R+T+P |
| `fn_resolve_termini_pagamento` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.ordini | — | — | T+C |
| `fn_riferimento_gruppo_fatturabile` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_ritira_commessa_attivita_da_sorgente` | vendite.commesse_attivita | commesse_attivita | — | C |
| `fn_select_attivita_fatturabili` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture | attivita_fatturabili | — | T+C |
| `fn_set_documento_canale_stato` | vendite.documenti_fatturazione_canali | documenti_fatturazione_canali | — | D |
| `fn_split_gruppo_fatturabile_key` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `fn_upsert_commessa_attivita` | vendite.commesse_attivita | commesse_attivita | — | C |
| `trgfn_attivita_fatturabili_normalize` | montato su vendite.attivita_fatturabili |  NEW | — | C |
| `trgfn_commesse_attivita_proietta_stato_preventivo` | vendite.commesse_attivita; montato su vendite.commesse_attivita | — | — | C |
| `trgfn_commesse_sorgenti_guard_emittente` | montato su vendite.commesse_sorgenti | — | — | C |
| `trgfn_ddt_guard_cliente_sorgente` | montato su vendite.ddt | — | — | T |
| `trgfn_ddt_normalize` | vendite.ordini; montato su vendite.ddt | — | — | T |
| `trgfn_doc_guard_chiusura_sorgente` | montato su vendite.ordini, ddt, contratti → commesse_attivita | — | — | C |
| `trgfn_documenti_sync_canali` | montato su preventivi, ordini, ddt, contratti → documenti_fatturazione_canali | — | — | D |
| `trgfn_guard_fatturazione_immediata_immutabile` | vendite.commesse_sorgenti; montato su preventivi, ordini, ddt, contratti → commesse_sorgenti | — | KS | C |
| `trgfn_resi_default_magazzino` | vendite.ddt; montato su vendite.resi | — | — | T |
| `trgfn_resi_guard_cliente_ddt` | vendite.ddt; montato su vendite.resi | — | — | T |
| `trgfn_resi_guard_ddt_consegnato` | vendite.ddt; montato su vendite.resi | — | — | T |
| `trgfn_resi_normalize` | vendite.ddt; montato su vendite.resi | — | — | T |

###### Viste `dbops` (5)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `vw_ddt_emessi_senza_scarico` | magazzino.movimenti, vendite.ddt, vendite.ddt_righe | — | DDT_VENDITA_PRELIEVO | R+T+M |
| `vw_fatture_stampa_coda_da_guardare` | vendite.fatture_stampa_coda | — | — | D |
| `vw_magazzino_movimenti_senza_costo` | magazzino.movimenti | — | — | M |
| `vw_resi_confermati_senza_carico` | magazzino.movimenti, vendite.resi | — | RESO_VENDITA_RIENTRO | T+M |
| `vw_sorgenti_orfane` | — (NEW / parametri / SQL dinamico) | — | TT | 0 |

###### Viste `documenti` (3)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `vw_template_personalizzati_scarto` | documenti.template_documenti | — | — | — (solo il tipo) |
| `vw_template_risoluzione_emittente` | documenti.template_documenti | — | — | — (solo il tipo) |
| `vw_template_versioni_stampabili` | documenti.template_documenti | — | — | — (solo il tipo) |

###### Viste `script` (3)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `vw_lotto_documento_righe` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture_righe | — | — | C |
| `vw_pratica_doc_sorgente` | pratiche.pratiche_sorgenti | — | CHIAVE | P (pratiche) |
| `vw_stato_sorgente` | — (NEW / parametri / SQL dinamico) | — | — | 0 |

###### Viste `vendite` (15)

| Oggetto | Tabelle con `sorgente_*` che nomina | Scrive | Segni | Lotto |
| --- | --- | --- | --- | --- |
| `vw_commesse_attivita_emittibilita` | vendite.commesse_attivita | — | — | C |
| `vw_dash_competenza_attivita` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture, vendite.fatture_righe | — | — | T+C |
| `vw_dash_competenza_gruppi` | — (NEW / parametri / SQL dinamico) | — | — | C |
| `vw_ddt_lista` | vendite.ddt, vendite.ordini | — | — | T |
| `vw_fatture_lista` | vendite.fatture | — | — | T |
| `vw_lotti_gruppi_serviti` | vendite.attivita_fatturabili, vendite.commesse_attivita, vendite.fatture, vendite.fatture_righe | — | — | T+C |
| `vw_preventivi_pratiche` | pratiche.pratiche_sorgenti | — | — | P (pratiche) |
| `vw_preventivi_smistamento_righe` | vendite.attivita_fatturabili, vendite.ordini, vendite.ordini_righe, vendite.preventivi_righe | — | — | R+T+C |
| `vw_resi_lista` | vendite.ddt, vendite.resi | — | — | T |
| `vw_stato_sorgente_contratto` | vendite.contratti | — | — | 0 |
| `vw_stato_sorgente_ddt` | vendite.ddt | — | — | 0 |
| `vw_stato_sorgente_offerta` | — (NEW / parametri / SQL dinamico) | — | — | 0 |
| `vw_stato_sorgente_ordine` | vendite.ordini | — | — | 0 |
| `vw_stato_sorgente_preventivo` | — (NEW / parametri / SQL dinamico) | — | — | 0 |
| `vw_stato_sorgente_reso` | vendite.resi | — | — | 0 |

##### D.3 Riepilogo per lotto (proposta)

Conteggio sulle 124 voci della lista (98 funzioni + 26 viste): `0` 17; `C` 27; `T` 12; `R+T` 10; `R+T+C` 8; `M` 7;
`P` 6; `T+C` 6; `D` 4; `R+T+P` 2; `R+T+M` 2; `R` 1; `T+D` 1; `T+M` 1; fixture pgTAP 3; solo commento 4; solo il tipo 13.
Le combinazioni (`R+T…`) sono i lettori trasversali — lineage (`fn_documento_lineage_*`, `fn_documento_legami`,
`fn_documento_ritira_legami`), push e diagnosi DDT, resi: sono quelli che il resolver unico del lotto 0 deve
semplificare **prima** dei lotti di famiglia, altrimenti si riscrivono una volta per lotto.

---

#### E. Segnalazioni per Tid e per il brief

| # | Che cosa | Tipo | Dove va |
| --- | --- | --- | --- |
| E-1 | `fn_push_offerta_a_contratto` con pratica → `E_SORG_FORMATO` (§0.1) | FATTO dal codice; nessun pgTAP | richiesta di test nel lotto P; il verbo si riscrive col BB di scrittura |
| E-2 | FATTURA in `documenti_generati` con due chiavi; due serie di progressivi; lista UI cieca ai PDF del drainer (§0.2, §A.3) | FATTO dal codice | §3.1 G6 da correggere; la conversione S-5 deve rinumerare o decidere prima |
| E-3 | `reconcile_errori` senza guard d'esistenza (log resiliente) | eccezione a S-6 | Tid |
| E-4 | `template_documenti` (e le altre colonne di solo tipo) fuori dal meccanismo; il presidio di struttura si aggancia a `sorgente_id`/`sorgente_uid`, non a `sorgente_tipo_id` | precisazione al lotto 0 | brief §7.2 |
| E-5 | S-2 revoca anche **G-2** («righe e varianti: dentro») | dichiarazione mancante | brief §3.5 |
| E-6 | OFFERTA (righe polimorfe, nessun id di riga da `fn_offerta_righe_espanse`) e COMMESSA (righe = `commesse_attivita`) non stanno in una `righe_table` sola | modello da precisare | Tid, S-1 / lotto 0 |
| E-7 | metodo del §3.3 cieco a `BEGIN ATOMIC`: 98 funzioni, non 92; BB chiave usati da 7, non 8; `fn_scope_note_ef_perimetro` non nomina i `*_RIGA` | correzione numeri | brief §3.3 |
| E-8 | cancellazioni senza regola DB: preventivo (regola nel BE), ordine in bozza collegato a pratica, contratto/offerta/reso/commessa con `DELETE` concesso e nessun trigger DELETE | S-9, FATTO | lato «in uscita» del lotto 0 |
| E-9 | `trg_preventivi_z90_reconcile_proiezione_upd` passa l'**id** della sorgente come letterale (`'2'`) | fragilità, FATTO | lotto P (per codice) |
| E-10 | `vendite.vw_preventivi_pratiche` espone `ps.id AS sorgente_id` (l'id del **link**): col modello il nome collide con la colonna nuova | trappola di nome | lotto P (rinominare la colonna della vista; un consumatore BE, `preventivi_repository.py:1407`) |
| E-11 | il manuale di `config.sorgenti` descrive la colonna `area`, assente su `zeroerp_ruoli` | da verificare su dbdev | riscrittura del manuale (§3.5) |
| E-12 | `fn_segment_key` usa l'uid per tipi `id` (ATTIVITA_CONSUMI e push): non è provenienza, non si converte con S-5 | da dichiarare | guida `sorgente-polimorfa.md` |
