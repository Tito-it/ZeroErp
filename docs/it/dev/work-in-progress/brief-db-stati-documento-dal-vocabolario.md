# Brief DB — Gli stati dei documenti: ogni significato dal vocabolario

## ⏭️ Chi riparte — aggiornato al 2026-11-15

**Riparte: il team DB**, col giro 6f (il listino). Il FE ha fatto FE-G1 … FE-G4 (§6.24, §6.25), da committare su `dev/backend-tid` (2026-11-15). Il giro 6g-bis (§6.25: `_reason_valori` sugli altri cinque flag, `20261114-79 … -81`, D-VAL-2 (a)) è applicato e verde, con la doc rigenerata (Tid, 2026-11-15). Il giro 6g (`20261114-74 … -78`, D-VAL, D-MARCHE e D-SMIST (a)) è applicato e verde (Tid, 2026-11-15). Il BE/FE ha fatto le richieste dei giri 6a … 6e (§6.16 … §6.22): `338356674f`, entrato in `dev/db-tid` con la PR #120 (2026-11-14). I giri 6e (il reso, `20261114-47 … -57`, D-RESO (a)) e 6e-bis (`-58`) sono applicati e verdi (Tid, 2026-11-14). I giri 6c-bis (il guard della categoria ritirato, `20261114-35`, §6.20) e 6d (la bolla, `20261114-36 … -46`, §6.21) sono applicati e verdi (Tid, 2026-11-14); il BE ha BE-C1, il FE FE-D1 … FE-D3. Il giro 6c (il contratto, `20261114-27 … -34`, D-BOZZA (a), §6.19) è applicato e verde (Tid, 2026-11-14). I giri 6b (l'ordine, `20261114-14 … -20`, §6.17), 6b-bis, 6a-bis e 2-ter (`-22 … -26`, §6.18) sono applicati e verdi (Tid, 2026-11-14); il FE ha FE-O3, FE-P2 e FE-V3. D-EVAD e D-PDF decise (a) da Tid il 2026-11-14. Il giro 6a (il preventivo, `20261114-08 … -13`) è applicato e verde, con D-PROI decisa (a) (Tid, 2026-11-14). Il giro 5 è applicato e verde (Tid, 2026-11-14). D-LOCK e i giri 3 e 4, con D-ANN, sono applicati e verdi
(Tid, 2026-11-14). In parallelo il team BE (BE-V1, BE-T1, BE-T2: la rigenerazione dei codici, aggiunta il 2026-11-14 su segnalazione del BE) e il team FE
(FE-V2, FE-S8). Via di Tid del 2026-11-14 a tutti i giri («procedi anche con tutti gli altri giri»). Il giro 2-bis (V-1: `20261113-38`, `-39`) è applicato e verde (Tid, 2026-11-14). Il BE/FE ha fatto le richieste del giro 2 e di
D-SCAD (`fec6a713fa`, PR #112, 2026-11-14) e ha trovato V-1 e V-2 (§6.9).
Il giro 1 è applicato, verde e mergiato (2026-11-13); il BE ha fatto R-2 (`e174a302e2`), quindi nel giro 5 la
colonna `in_gioco` esce dalla vista.
Il 2026-11-12 il DB ha riverificato il brief sul catalogo di dbdev (§5) e, col via di Tid, ha scritto il giro 1 (§6).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ DB | i difetti, trovati riscrivendo le pagine `config/manual/stati_doc_*` (giro DOC.4 di `brief-db-sorgente-documento-e-riga`), verificati sul DB | §2 | — |
| 2 | ✅ Tid | il brief si apre: i difetti degli stati vanno qui, non nel cantiere della provenienza (2026-11-08) | — | — |
| 3 | ✅ Tid | **S-1**: `terminale` = nessun passaggio **a mano** in uscita; gli automatismi restano (A, 2026-11-08) | §3 | — |
| 4 | ✅ DB | censimento: per ogni difetto i lettori e gli scrittori, la proposta di correzione, il pgTAP, le ricadute (2026-11-08) | §4 | — |
| 5 | ✅ Tid | S-2 … S-10 come proposte dal DB («confermo la tua proposta», 2026-11-08) | §4.9 | — |
| 6 | ✅ Tid | via allo sviluppo (2026-11-12) | — | — |
| 7 | ✅ DB | giro 1, il vocabolario fiscale (②, ⑥, S-6, S-7 e la parte fiscale di S-2): nove changeSet, prova in transazione, pgTAP adeguati e nuovi (2026-11-12) | §6.2, §6.3 | — |
| 8 | ✅ Tid | apply del giro 1 (`20261112-44 … -52`) e pgTAP del §6.3: verdi (2026-11-13) | §6.3 | — |
| 8b | ✅ Tid | R-1 … R-3 come proposte dal DB; per R-2 il ritiro di `in_gioco` (2026-11-13) | §6.4 | — |
| 9 | ✅ DB | giro 2, l'offerta (③, S-3, S-10, S-2 per l'offerta, il builder): sei changeSet, due CSV, prova in transazione, pgTAP nuovo e uno adeguato (2026-11-13) | §6.5, §6.6 | via di Tid (2026-11-13) |
| 9b | ✅ Tid | apply di `20261112-59 … -64` e dei due mirror; pgTAP del §6.6: verdi (2026-11-13) | §6.6 | 9 |
| 9c | ✅ BE/FE | le richieste del giro 2: il rifiuto dal vocabolario (BE), `stato_terminale` al posto di `STATI_OFFERTA_TERMINALI` (FE) (`fec6a713fa`, 2026-11-14) | §6.7 | 9b |
| 9c-bis | ✅ Tid | D-SCAD: (a), `esito IS NULL` (2026-11-13) | §6.8 | — |
| 9c-ter | ✅ DB | D-SCAD: `20261112-65`, pgTAP esteso (plan 15), prova in transazione (2026-11-13) | §6.8 | 9c-bis |
| 9c-quater | ✅ Tid | apply di `20261112-65`, pgTAP `test-offerta-guard-dal-vocabolario-v1`: verde (2026-11-13) | §6.8 | 9c-ter |
| 9c-quinquies | ✅ BE/FE | le richieste di D-SCAD: `is_scaduta` nel dettaglio (BE), il badge dal flag da solo e il ritiro di `STATI_OFFERTA_SEGNALA_SCADENZA` (FE) (`fec6a713fa`, 2026-11-14) | §6.8 | 9c-quater |
| 9c-sexies | ✅ BE/FE | la verifica dei giri 2 e D-SCAD: V-1 e V-2, richieste al team DB (2026-11-14) | §6.9 | — |
| 9c-septies | ✅ DB | giro 2-bis, V-1: `20261113-38` (`vendite.fn_offerta_scaduta`), `-39` (la vista la compone), pgTAP esteso (plan 18), prova in transazione (2026-11-14) | §6.10 | via di Tid (2026-11-14) |
| 9c-octies | ✅ Tid | apply di `20261113-38`, `-39`; pgTAP `test-offerta-guard-dal-vocabolario-v1` (plan 18): verde (2026-11-14) | §6.10 | 9c-septies |
| 9c-nonies | ✅ BE | BE-V1 e BE-V1b: il dettaglio chiama `vendite.fn_offerta_scaduta` al posto della sottoquery sulla vista (da committare, 2026-11-14) | §6.10 | 9c-octies |
| 9c-decies | ✅ Tid | **D-LOCK**: (a), il lock riconosce la bozza da `iniziale` (2026-11-14) | §6.10 | — |
| 9c-undecies | ✅ DB | D-LOCK (a) e V-2: `20261113-40` (`script.fn_doc_lock_regola`), `-41` (`can_edit_eccezioni` dal lock); 48 pgTAP con l'estratto, tre riportati al modello, cinque test nuovi (2026-11-14) | §6.11 | 9c-decies |
| 9c-terdecies | ✅ Tid | apply di `20261113-40`, `-41`; i pgTAP del §6.11: verdi (2026-11-14) | §6.11 | 9c-undecies |
| 9c-duodecies | ✅ FE | FE-V2 e FE-V2b: il lucchetto del drawer dalle chiavi `can_edit_*` della capability, non dal codice BOZZA (da committare, 2026-11-14). Il corpo si chiude da `can_edit_utility` (`readonly` dell'`AppDrawer`, nessun `provide` del drawer); il sotto-drawer delle righe sta **fuori** dall'`AppDrawer` ed eredita i soli permessi, più `can_edit_eccezioni`. Trovato dalla verifica del 2026-11-14: dentro, `RigheEccezioniDrawer` chiudeva le righe anche col solo `can_edit_utility` falso (la V-2 rifatta nel FE). Spec `OffertaDrawer.spec.js` | §6.10 | — |
| 9d | ✅ DB | giro 3: `terminale`, bolla e reso (④, ⑦, S-4, S-5, S-3 del reso): `20261113-42 … -50`, 129 pgTAP con l'estratto, uno nuovo e tre adeguati (2026-11-14) | §6.12 | via di Tid (2026-11-14) |
| 9e | ✅ DB | giro 4: gli stati che nessun passaggio raggiunge (⑤, S-8, R-3): `20261114-03`, due CSV, il presidio nuovo della raggiungibilità (2026-11-14) | §6.13 | via di Tid (2026-11-14) |
| 9f | ✅ Tid | apply (verde, 2026-11-14) dei giri 3 e 4 (`20261113-42 … -50`, `20261114-03`); i pgTAP dei §6.12 e §6.13, e `vendite/test-documenti-numerazione-trasloco-v1` e `vendite/test-fn-list-ordini-da-pushare-v1`, che lo strumento non lancia | §6.12, §6.13 | 9d, 9e |
| 9g | ✅ Tid | **D-ANN**: (a), ANNULLATA non vale per la fattura (`applica_fattura` = false, dal CSV, 2026-11-14) | §6.12, §6.13 | — |
| 9h | ✅ Tid | i numeri dei giri 5 e 6: dal primo libero (Tid, 2026-11-14: «-04»; il `-04` l'aveva preso l'altra sessione, si parte dal `-05`) | §6.13 | — |
| 9i | ✅ DB | giro 5: il listino, i COMMENT stantii, `in_gioco` (⑧, S-9, §4.8, R-2): `20261114-05 … -07`, 31 pgTAP con l'estratto, tre adeguati (2026-11-14) | §6.14 | 9h |
| 9i-bis | ✅ Tid | apply di `20261114-05 … -07` (il `-05` al secondo tentativo, dopo la correzione della `preCondition`); i pgTAP del §6.14: verdi (2026-11-14) | §6.14 | 9i |
| 9i-ter | ✅ DB | giro 6: il censimento, circa 55 oggetti in sei documenti, e l'ordine (2026-11-14) | §6.15 | — |
| 9i-quater | ✅ DB | giro 6a, il preventivo: `20261114-08 … -13`, un pgTAP nuovo (plan 18), sei pagine `manual/` e il vocabolario; prova in transazione con 128 pgTAP (2026-11-14) | §6.16 | 9h |
| 9i-quinquies | ✅ Tid | ✅ **D-PROI** (a), 2026-11-14: la proiezione dello smistamento parte dallo stato di accettazione (`-13`, revoca in parte una riga del 2026-10-31). ✅ **D-PDF** (a), 2026-11-14: il PDF delle liste dalla vista (`pdf_mode`), non dal codice della bozza; ogni giro la sua vista lista, per offerta e preventivo i giri 2-ter e 6a-bis | §6.16 | — |
| 9i-sexies | ✅ Tid | apply di `20261114-08 … -13` e pgTAP del §6.16 verde (2026-11-14) | §6.16 | — |
| 9i-septies | ✅ BE | BE-P1: il ritiro di `STATO_PREVENTIVO_DRAFT`, che nessuno legge (da committare, `dev/backend-tid`, 2026-11-14) | §6.16 | — |
| 9i-octies | ✅ FE | FE-P1: il lucchetto del drawer del preventivo dalle chiavi `can_edit_*`, non dal codice DRAFT (gemello di FE-V2), col BB `useCorpoDocumento` (da committare, `dev/backend-tid`, 2026-11-14) | §6.16 | — |
| 9i-nonies | ✅ DB | giro 6b, l'ordine: `20261114-14 … -20`, un pgTAP nuovo (plan 22), sette pagine `manual/`; prova in transazione (2026-11-14) | §6.17 | — |
| 9i-decies | ✅ Tid | apply di `20261114-14 … -20` (il `-19` al secondo tentativo, col COMMENT fuori dal `BEGIN ATOMIC`) e pgTAP del §6.17: verdi (2026-11-14). ✅ **D-EVAD** (a), 2026-11-14 | §6.17 | 9i-nonies |
| 9i-decies-bis | ✅ DB | giro 6b-bis (D-EVAD): `script.fn_check_ordine_evadibile`, letto da `vendite.fn_genera_ddt_da_ordine` e dalla capability (`can_genera_ddt`); giri 2-ter e 6a-bis (D-PDF): `pdf_mode` nelle viste lista di offerta e preventivo; `20261114-22 … -26`, due pgTAP, prova con 160 file (2026-11-14) | §6.18 | — |
| 9i-decies-ter | ✅ Tid | apply di `20261114-22 … -26` e pgTAP del §6.18: verdi (2026-11-14) | §6.18 | — |
| 9i-decies-quater | ✅ FE | FE-O3 («Genera bolla» da `can_genera_ddt`, BB `azioneDaFlag`), FE-P2 e FE-V3 (il PDF delle liste da `pdf_mode`, BB `azionePdfLista`) (da committare, `dev/backend-tid`, 2026-11-14) | §6.18 | — |
| 9i-undecies | ✅ BE | BE-O1: il ritiro di `_STATI_PUSHABILI` (da committare, `dev/backend-tid`, 2026-11-14) | §6.17 | — |
| 9i-duodecies | ✅ FE | FE-O1: il lucchetto del drawer dell'ordine dalle chiavi `can_edit_*`; FE-O2: l'avviso dopo l'annullo dall'azione (da committare, `dev/backend-tid`, 2026-11-14) | §6.17 | — |
| 9i-terdecies | ✅ DB | giro 6c, il contratto: `20261114-27 … -34`, D-BOZZA (a) (via `is_bozza`), un pgTAP nuovo (plan 12), prova con 334 file (2026-11-14) | §6.19 | — |
| 9i-quattuordecies | ✅ Tid | apply di `20261114-27 … -34` e pgTAP del §6.19: verdi (2026-11-14) | §6.19 | — |
| 9i-quattuordecies-bis | ✅ DB | giro 6c-bis: il guard della categoria ritirato (`20261114-35`), il codice obsoleto (decisione di Tid del 2026-11-14) | §6.20 | — |
| 9i-quattuordecies-ter | ✅ Tid | apply di `20261114-35` e pgTAP del §6.20: verdi (2026-11-14) | §6.20 | — |
| 9i-quattuordecies-quater | ✅ BE | BE-C1: rigenerare `error_policies_generated.py` (il codice obsoleto) (da committare, `dev/backend-tid`, 2026-11-14) | §6.20 | — |
| 9i-quindecies | ✅ FE | FE-C1 … FE-C4 (drawer, azioni, avviso, PDF della lista del contratto) (da committare, `dev/backend-tid`, 2026-11-14); i residui del drawer sono il §6.23 | §6.19 | — |
| 9i-sedecies | ✅ DB | giro 6d, la bolla: `20261114-36 … -46`, un pgTAP nuovo (plan 14), sette pagine `manual/` e il vocabolario (2026-11-14) | §6.21 | — |
| 9i-septendecies | ✅ Tid | apply di `20261114-36 … -46` e pgTAP del §6.21: verdi (2026-11-14) | §6.21 | — |
| 9i-duodevicies | ✅ FE | FE-D1 … FE-D3 (drawer, PDF della lista, avviso dopo l'annullo della bolla) (da committare, `dev/backend-tid`, 2026-11-14) | §6.21 | — |
| 9i-undevicies | ✅ DB | giro 6e, il reso: `20261114-47 … -57`, D-RESO (a) (`script.fn_check_ddt_rendibile`, `can_genera_reso`, `can_riconsegna`), un pgTAP nuovo (plan 14), uno adeguato, undici pagine (2026-11-14) | §6.22 | — |
| 9i-vicies | ✅ Tid | apply di `20261114-47 … -58` e pgTAP del §6.22: verdi (2026-11-14) | §6.22 | — |
| 9i-vicies-bis | ✅ FE | FE-R1 (le due chiavi i18n: `check-i18n-keys` rosso fino ad allora), FE-R2 … FE-R4 («Genera reso», ri-spedizione e lucchetto del reso dalla capability; il ritiro di `STATO_RESO`) (da committare, `dev/backend-tid`, 2026-11-14) | §6.22 | — |
| 9i-vicies-ter | ✅ BE | BE-R1: il ritiro del guard gemello in `crea_reso`, col test sul DB vero (da committare, `dev/backend-tid`, 2026-11-14) | §6.22 | — |
| 9i-vicies-quater | ✅ Tid | D-VAL, D-MARCHE, D-SMIST decise (a), 2026-11-14 | §6.24 | — |
| 9i-vicies-quinquies | ✅ DB | giro 6g: `20261114-74 … -78`, un pgTAP nuovo (plan 12), cinque pagine `manual/`, §12.2 delle linee guida; prova in transazione (2026-11-15) | §6.24 | 9i-vicies-quater |
| 9i-vicies-sexies | ✅ Tid | apply di `20261114-74 … -78` e pgTAP del §6.24: verdi (2026-11-15) | §6.24 | 9i-vicies-quinquies |
| 9i-vicies-septies | ✅ FE | FE-G1 … FE-G3: i valori del motivo nella frase (`motivoFlag` + `testoMotivi`), il drawer del contratto dalle marche, lo smistamento del preventivo da `in_smistamento`; ritirate `STATO_CONTRATTO` e `STATO_PREVENTIVO` di `vendite/constants.js` (da committare, `dev/backend-tid`, 2026-11-15) | §6.24 | 9i-vicies-sexies |
| 9i-vicies-octies | ✅ Tid | D-VAL-2 decisa (a), 2026-11-15 | §6.25 | — |
| 9i-vicies-novies | ✅ DB | giro 6g-bis: `20261114-79 … -81`, sei casi nel pgTAP del 6g (plan 18), tre pagine `manual/`; prova in transazione (2026-11-15) | §6.25 | 9i-vicies-octies |
| 9i-vicies-novies-bis | ✅ Tid | apply di `-79 … -81`, pgTAP del §6.25 verdi, doc rigenerata (2026-11-15) | §6.25 | 9i-vicies-novies |
| 9i-vicies-decies | ✅ FE | FE-G4: nessuna frase da cambiare; con FE-G1 i tooltip ricevono i valori, e il banner dei motivi dell'offerta li passa alla frase (`riga_non_ammessa`). Nelle frasi senza segnaposto i valori si ignorano (decisione di Tid, 2026-11-15) (da committare, `dev/backend-tid`, 2026-11-15) | §6.25 | 9i-vicies-novies, FE-G1 |
| 9i-unvicies | **DB** ⏭️ | giro 6f: il listino | §6.15 | — |
| 9j | **BE** ⏭️ | BE-T1: la frase di `doc_terminale` in `api_percorso.md` | §6.12 | — |
| 9k | **FE** ⏭️ | FE-S8: costanti, chiavi i18n e commenti dei quattro stati d'ordine ritirati | §6.13 | 9f |
| 9i-quater | **DB** ⏭️ | giri 6a … 6f, un documento per volta: preventivo, ordine, contratto, bolla, reso, listino | §6.15 | — |
| 9j | ✅ BE | BE-T1 e BE-T2: la frase di `doc_terminale` in `api_percorso.md`; `error_policies_generated.py` rigenerato col codice nuovo, e il suo ripiego (da committare, 2026-11-14). In più, da S-3: la rotta della conferma del reso chiede lo stato di emissione al vocabolario (`stato_del_modello="emissione"`), via `resi_service.STATO_CONFERMATO` | §6.12 | — |
| 9k | ✅ FE | FE-S8: costanti, chiavi i18n e commenti dei quattro stati d'ordine ritirati, e la mappa di `severity.js` (da committare, 2026-11-14) | §6.13 | 9f |
| 10 | BE/FE | le ricadute del §4.10 degli altri giri (FE: costanti degli ordini, giro 4). Il giro 1 non ne ha; quelle del giro 2 sono la riga 9c | §4.10 | il giro che le porta |
| 11 | ✅ BE | R-2: il test Django che legge `in_gioco` passa a `pre_fiscale` (`e174a302e2`, 2026-11-13) | §6.4 | — |

**Decisioni aperte di Tid:** nessuna. D-VAL-2 (§6.25) decisa il 2026-11-15 (a). D-VAL, D-MARCHE e D-SMIST (§6.24) decise il 2026-11-14 (a). D-RESO (§6.22) decisa il 2026-11-14 (a). D-BOZZA (§6.19) decisa il 2026-11-14 (a). D-EVAD (§6.17) e D-PDF (§6.16) decise il 2026-11-14 (a). D-PROI decisa il 2026-11-14 (a), con l'apply di `-13`. D-ANN e D-LOCK decise il 2026-11-14 (a). D-SCAD decisa il 2026-11-13 (a). Decise il 2026-11-13 (§6.4): R-1, S-3 revocata per il fiscale (il cancello IVA
resta su EMESSA, eccezione voluta); R-2, `in_gioco` si ritira (giro 5, dopo la riga 11); R-3, il lotto non diventa
REGISTRATO (`applica_lotto` = false, giro 4). Decise il 2026-11-08: S-1, lettura A; S-2 … S-10 come proposte dal DB (§4.9; per S-8 il ritiro, non
l'`attivo = false`). **Lavoro da committare:** nessuno. Il giro 6g (§6.24: cinque changeSet, un pgTAP nuovo, cinque pagine `manual/`, §12.2 delle linee guida), la verifica e il giro 6g-bis del §6.25 (tre changeSet, il pgTAP del 6g esteso, tre pagine `manual/`), con la doc rigenerata, sono nel commit «Stati dal vocabolario: giri 6g e 6g-bis; provenienza del prezzo: giro 4» (2026-11-15). I giri 6c, 6c-bis, 6d, 6e e 6e-bis, applicati e verdi, sono nel commit «Stati del documento dal vocabolario: contratto, bolla e reso» (2026-11-14), con la doc rigenerata: il 6c (§6.19: otto changeSet, il CSV dei contratti, un pgTAP nuovo, due adeguati, sette pagine `manual/`), il 6c-bis (§6.20: un changeSet, una riga del catalogo dei codici, due pagine), il 6d (§6.21: undici changeSet, un pgTAP nuovo, nove pagine), il 6e e il 6e-bis (§6.22: dodici changeSet, un pgTAP nuovo, uno adeguato, undici pagine, una nuova). I giri 6a, 6b, 6b-bis, 6a-bis e 2-ter sono nel commit `f49e5233ca`. I giri 2-bis, D-LOCK, 3, 4 e 5 sono nel commit `f23460d27e`; D-SCAD (§6.8) è nel commit di questo brief, il giro 2 nel commit `2502514207`; la verifica del 2026-11-12
(§5) e il giro 1 (§6) sono nel commit `a9b7a0f32e` (PR #108).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-08. **A chi:** Tid, poi il team DB.
> **Origine:** il giro DOC.4 di `brief-db-sorgente-documento-e-riga` (§7.3 «Trovato da DOC.4»): riscrivendo le dieci
> pagine dei vocabolari degli stati sono emersi difetti fuori dal tema della provenienza. Tid, 2026-11-08: si apre un
> brief per gli stati.
> **Brief vicini verificati:** `work-done/brief-modello-documento-vendita` (chiuso il 2026-10-31: il significato di uno
> stato lo dice il vocabolario, non un letterale; questo brief ne chiude i residui, non ne revoca niente);
> `analisi-pratiche-valutazione-stato` e `brief-design-proiezione-stato-dominio` (leggono `fase`/`esito`/`terminale` per
> la proiezione nelle pratiche: sono i consumatori di S-1, non lo decidono); `gestione-pratiche-come-procedere` §3 (le
> segnalazioni di `pratiche`, separate per decisione di Tid). Nessun brief aperto sui vocabolari degli stati.
> **Ambito:** i vocabolari `config.stati_doc_*`, le loro matrici, i guard e i verbi che li leggono. ⚠️ Tocca tutti i
> documenti di vendita: è ammesso dal fermo allentato (PROJECT_CONTEXT, «poggia su un pezzo comune già fatto»: il
> vocabolario) e Tid ne ha dato l'ok (2026-11-08).

---

## 1. Il buco in una frase

La guida del modello del documento dice che il significato di uno stato (iniziale, emissione, accettazione, terminale,
annullo) lo dice il vocabolario; in alcuni punti il codice lo dice ancora con un letterale, o il vocabolario dichiara un
significato che la matrice smentisce.

## 2. I difetti (verificati sul DB, 2026-11-08; non provati in transazione)

| # | Difetto | Dove |
| --- | --- | --- |
| ② | Il lotto di fatturazione non nasce dal vocabolario: `vendite.fn_create_fatturazione_lotto` sceglie lo stato col letterale `'DRAFT'`, e `trgfn_doc_stato_iniziale` non è montato su `vendite.fatturazione_lotti` (mentre `fn_riporta_lotto_a_draft` legge già `iniziale`) | `vendite.fatturazione_lotti` |
| ③ | Il guard di transizione dell'offerta confronta i codici (`'BOZZA'`, `'EMESSA'`, `'ACCETTATA'`, `'ANNULLATA'`) nelle condizioni e nelle date del passaggio, invece di `emissione`, `accettazione`, `is_abortito` | `vendite.trgfn_offerte_commerciali_guard_transizione` |
| ④ | `terminale` è dichiarato su stati che hanno passaggi attivi in uscita (automatici): `SUPERATA→EMESSA` (offerte), `EVASO→ACCETTATO` (preventivi), `EVASO→PARZIALMENTE_EVASO` ed `EVASO→CONFERMATO` (ordini). Il COMMENT dice «non evolverà più», e `pratiche.fn_stato_sorgente` lo legge | vocabolari e matrici; S-1 |
| ⑤ | Quattro stati d'ordine attivi che nessun passaggio raggiunge: `ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO` | `config.stati_doc_ordini` |
| ⑥ | Il controllo di `applica_fattura` in `trgfn_fatture_guard_stato` sta nel solo ramo «prima assegnazione» (UPDATE con stato precedente NULL), che non scatta: lo stato è NOT NULL e lo mette il trigger alla nascita | `vendite.fatture` |
| ⑦ | Bolla e reso non dichiarano `esito` e `terminale`: li ricavano `vw_stato_sorgente_ddt` e `vw_stato_sorgente_reso` con una regola scritta nella vista | `config.stati_doc_ddt`, `config.stati_doc_reso` |
| ⑧ | (minore) `config.stati_doc_listino_versioni` non ha `fase` (e quindi il CHECK che lega `terminale` a `fase`), e l'indice di `iniziale` si chiama `ux_…` invece di `uq_…` | `config.stati_doc_listino_versioni` |

**COMMENT stantii** (ognuno è un changeSet): `config.stati_doc_reso` e la sua `meta` (`fase` in `meta.fase`: è una
colonna); `config.stati_doc_offerte_transizioni` («5 transizioni»: sono 7); `config.stati_doc_offerte` (manca
`accettazione`) e le colonne `ordine` (manca 60) e `is_superato` (lo scrive `vendite.fn_offerta_proietta_stato_revisione`);
`codice` di `stati_doc_contratti` (`SOSPESO`, che non c'è), `stati_doc_ddt` e `stati_doc_ordini` (CONFERMATA/ALLOCATA);
`stati_doc_fiscale.fase`; `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più: oggi
`partecipa_overlap_snapshot`, `ex_contratti_no_overlap`); le colonne di significato degli stati («Emetti» produce numero e
PDF: per offerta, contratto e ordine il numero è assegnato alla nascita).

Le pagine `manual/` descrivono già lo stato di oggi, difetti compresi (DOC.4, 2026-11-08).

## 3. Da decidere (Tid)

* **S-1 — che cosa vuol dire `terminale`.** Due letture, e decidono ④:
  * **A** «nessun passaggio **a mano** in uscita»: gli automatismi (la revisione che riapre, l'evasione che si
    riapre) restano ammessi; si corregge il COMMENT e si dichiara nella matrice quali passaggi sono di sistema
    (`meta.manuale` c'è già). Chi legge `terminale` per dire «finito per sempre» va censito.
  * **B** «nessun passaggio **in assoluto**»: gli stati con uscite perdono `terminale`, e chi oggi lo legge
    (la proiezione nelle pratiche) va rivisto perché un'offerta superata o un ordine evaso non sono più «chiusi».
  * ✅ **Decisa: A** (Tid, 2026-11-08). Proposta DB era A, perché `meta.manuale` distingue già i passaggi di sistema e la proiezione nelle pratiche vuole
    sapere se l'operatore ha ancora qualcosa da fare. Da confermare col censimento dei lettori.

## 4. Il censimento (team DB, 2026-11-08)

Fonti: i corpi in `pg_proc.prosrc` (commenti tolti), `pg_get_viewdef`, `pg_trigger`, `pg_constraint` su dbdev in sola
lettura; `grep` in `backend/apps` e `frontend/src`. Si legge la **struttura** (corpi, vincoli, seed in `80_data`, che è
contratto): nessun conteggio di righe entra come motivo. Nessuna prova in transazione: è un censimento.

Per ogni difetto: (1) chi scrive e chi legge, (2) la correzione sul modello (guida `modello-documento-di-vendita` §4: il
significato di uno stato lo dice il vocabolario), (3) il pgTAP che la presidia **costruendo** il caso, (4) le ricadute.

### 4.1 ② Il lotto non nasce dal vocabolario

**Chi scrive e chi legge.**

| Oggetto | Che cosa fa con lo stato del lotto |
| --- | --- |
| `vendite.fn_create_fatturazione_lotto` | **scrive**: sceglie `codice_interno = 'DRAFT' AND applica_lotto AND attivo … ORDER BY ordine LIMIT 1`, poi `INSERT`. È l'unico `INSERT` del DB sul lotto; lo chiamano `vendite.fn_get_or_create_lotto` (BE: `pipeline_repository.py:516`) e `dbops.fn_pgtap_crea_lotto` |
| `vendite.fatturazione_lotti.stato_doc_fiscale_id` | **nullable** (la fattura invece è `NOT NULL`); nessun trigger della nascita: `script.trgfn_doc_stato_iniziale` è montato su undici testate, non sul lotto |
| `vendite.fn_riporta_lotto_a_draft` | legge già `iniziale` (rev 2026-10-27): il modello giusto, accanto |
| `vendite.trgfn_fatturazione_lotti_guard_stato` | legge il NULL: il ramo «prima assegnazione» (vedi ⑥) |
| `vendite.vw_documenti_trattenuti_da_lotto`, `vendite.vw_lotti_fase` | gestiscono il lotto **senza stato** (LEFT JOIN fail-closed, stato «IGNOTO»): lo ammettono perché la colonna è nullable |

Trovati dal censimento, stessa famiglia (letterale `'DRAFT'` per dire «iniziale» sul vocabolario fiscale):
`script.fn_check_lotto_fatture_pre_fiscali`, `vendite.trgfn_fatture_guard_uscita_draft`; e
`vendite.fn_imposta_data_documento_lotto` con `codice_interno IN ('DRAFT','EMESSA')`, una copia sopravvissuta della
regola «prima del congelamento» che gli altri lettori leggono già da `congela_fiscale` (i commenti di
`fn_genera_scadenze_fattura` e fratelli lo dicono: «erano OTTO copie»). Entrano in S-2.

**Correzione.** (a) montare `script.trgfn_doc_stato_iniziale('stato_doc_fiscale_id', 'config.stati_doc_fiscale')` su
`vendite.fatturazione_lotti` (fascia `_a05_`, `BEFORE INSERT`); (b) `fn_create_fatturazione_lotto` non sceglie più lo
stato: passa NULL e lo mette il trigger (come la fattura); (c) `stato_doc_fiscale_id NOT NULL` (S-6); (d) CHECK sul
vocabolario «lo stato iniziale si applica al lotto e alla fattura» (`NOT iniziale OR (applica_lotto AND applica_fattura)`),
così il filtro `applica_lotto` della madre non serve più (vedi ⑥).

**pgTAP (costruito).** Estendere `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` col montaggio sul lotto:

1. un lotto inserito senza stato nasce nello stato marcato `iniziale`; uno inserito in uno stato diverso →
   `E_DOC_STATO_INIZIALE_NON_VALIDO`;
2. **la marca spostata**: in transazione `iniziale` passa da DRAFT a un altro stato con `applica_lotto` e
   `applica_fattura`; `vendite.fn_create_fatturazione_lotto` crea il lotto **lì** (prova che la madre non ricorda un codice);
3. il CHECK: uno stato iniziale senza `applica_lotto` è rifiutato.

Builder: `dbops.fn_pgtap_crea_lotto` (passa già dalla madre), `dbops.fn_pgtap_crea_mondo_cliente`,
`dbops.fn_pgtap_crea_emittente`.
⚠️ pgTAP da adeguare, perché inseriscono il lotto **a mano** e lo stato lo scelgono loro: con il trigger un lotto si
costruisce in bozza e si porta avanti con `dbops.fn_pgtap_porta_a_stato` (o si crea con `fn_pgtap_crea_lotto`). Passano
la colonna di stato: `vendite/test-vw-lotti-fase-v1`, `test-documento-trattenuto-da-lotto-v1`,
`test-annullamento-chiude-la-vita-v1`, `test-stati-doc-transizioni-giornaliero`, `test-reset-fattura-plafond-consumato-v1`,
`test-lotti-fermi-verdetto-a-db-v1`, `test-stampa-coda-tipo-documento-v1`, `test-vw-dash-competenza-v1` (DRAFT: passa).
La omettono (NULL → bozza, da rileggere se contano sul NULL): `test-registri-fatturazione-scadenza-alla-nascita`,
`test-ricalcola-riepiloghi-iva`, `test-motivo-non-fatturata-v1`, `test-fondi-fattura-lotto`,
`pagamenti/test-fn-get-or-create-vendite-contabile`, `rls/test-rls-lotti-satelliti`, `rls/test-rls-vendite-contabili-lotti`.
Con S-6 il caso «lotto senza stato» di `test-vw-lotti-fase-v1` (test 4, 5, 8) e di `test-documento-trattenuto-da-lotto-v1`
(test 4) non è più costruibile: si ritira insieme al ramo che provava.

**Ricadute.** BE: nessuna sul codice (il BE crea i lotti da `fn_get_or_create_lotto`, firma invariata). Due test Django
inseriscono un lotto a mano passando DRAFT (`backend/apps/vendite/tests/db/test_giornale_trasversale_perimetro.py:60`,
`test_riepilogo_esclude_trattenuti.py:152`): DRAFT è lo stato iniziale, passano anche col trigger. FE: nessuna
(`grep fatturazione_lotti frontend/src`: solo lettura da API).

### 4.2 ③ Il guard dell'offerta confronta i codici

**Chi scrive e chi legge.** `vendite.trgfn_offerte_commerciali_guard_transizione` (montato `BEFORE UPDATE OF
stato_doc_offerta_id`) legge i codici `BOZZA`, `EMESSA`, `ACCETTATA`, `ANNULLATA`, `RIFIUTATA` in sei punti: il
congelamento del listino, indirizzi e righe su BOZZA→EMESSA; i prezzi verso EMESSA/ACCETTATA; l'annullabilità verso
ANNULLATA; le quattro date del passaggio. Il superamento lo legge già da `is_superato`. I significati in colonna ci sono
tutti tranne il rifiuto: `iniziale` (BOZZA), `emissione` (EMESSA), `accettazione` (ACCETTATA), `is_abortito`
(ANNULLATA); **`RIFIUTATA` non ha una colonna** (S-3). Lettori delle date: BE `offerte_repository.py` (97-111, 194-195),
`types.py:937-938`, `script.fn_available_actions_offerta` (campi fermi).

⚠️ **Trovato dal censimento: ③ non è solo dell'offerta.** La stessa forma (un letterale per dire un significato che la
colonna già dichiara) sta nei guard di transizione di **ordine** (`'DRAFT'`→`'CONFERMATO'`, `'ANNULLATO'`),
**contratto** (`'ATTIVO'`, `'CESSATO'`), **preventivo** (`'ACCETTATO'`; l'emissione la legge già dal vocabolario) e
**bolla** (`'DRAFT'`→`'EMESSO'`), e in una quarantina di altri corpi (capability, verbi, guard di bolla, reso e listino):

| Famiglia | Corpi (letterale → colonna che lo dice già) |
| --- | --- |
| guard di transizione | `trgfn_ordini_guard_transizione` (DRAFT→iniziale, CONFERMATO→emissione, ANNULLATO→is_abortito); `trgfn_contratti_guard_transizione_stato` (ATTIVO→emissione, CESSATO→cessazione); `trgfn_preventivi_guard_transizione` (ACCETTATO→accettazione); `trgfn_ddt_guard_transizione` (DRAFT, EMESSO); `trgfn_preventivi_guard_annullamento` (ANNULLATO) |
| capability | `script.fn_available_actions_{contratto,ddt,offerta,ordine,preventivo,reso}` (`v_stato_cod = 'DRAFT'/'BOZZA'` per «in bozza»; EMESSO, ANNULLATO) |
| bolla | `trgfn_ddt_gen_numero_emesso`, `trgfn_ddt_guard_causale_emissione`, `trgfn_ddt_guard_indirizzi_obbligatori`, `trgfn_ddt_guard_transizione_approvazione` (EMESSO→emissione); `script.vw_stati_doc_ddt_merce_partita` (aggiunta il 2026-11-12, §5: EMESSO→emissione per trovare lo stato da cui si conta; il «da lì in poi» per `ordine` resta, scelta (a) di Tid del 2026-10-12) |
| contratto | `trgfn_contratti_freeze_listino_versione`, `trgfn_contratti_set_categoria_cliente_snapshot` (DRAFT, ATTIVO); `fn_get_contratto_attivo` (ATTIVO) |
| reso | `fn_conferma_reso`, `fn_annulla_reso`, `script.fn_check_reso_merce`, `trgfn_resi_righe_guard_quantita` (DRAFT, ANNULLATO) |
| preventivo, ordine | `fn_crea_revisione_preventivo` (DRAFT); `fn_list_ordini_da_pushare` (DRAFT, ANNULLATO) |
| listino | `trgfn_listini_kit_guard`, `trgfn_listini_righe_guard_stato`, `trgfn_listini_righe_guard_periodicita_quota_fissa`, `trgfn_listini_righe_comp_guard_immutabilita_v5`, `trgfn_listini_versioni_guard_per_stato`, `script.fn_check_versione_listino_eliminabile`, `fn_check_listino_provenienza`, `fn_listino_ha_storia`, `fn_resolve_prezzo_listino_v2_esito` (BOZZA→iniziale) |
| fiscale | i tre di ② (DRAFT); `trgfn_fatture_guard_stato` (`'EMESSA'` per il cancello IVA: il vocabolario fiscale non ha `emissione`, e non la avrà, R-1 del §6.4) |

Gli altri letterali del censimento nominano uno stato **senza** un significato dichiarato (EVASO, PARZIALMENTE_EVASO;
SPEDITO, CONSEGNATO, RESO della bolla; CONFERMATO del reso; ATTIVA, CHIUSA del listino): sono destinazioni o condizioni
di un processo, e il modello non ha ancora una colonna per dirle. Sono S-3.

**Correzione (l'offerta).** I confronti si scrivono sulle colonne della riga del vocabolario, lette una volta con la
`SELECT` che il guard fa già (la guida: «chi ha già in mano la riga legge la colonna»): `iniziale`/`emissione` per
l'emissione, `emissione OR accettazione` per i prezzi, `is_abortito` per l'annullo; le date per significato
(`emissione` → `data_emissione`, `accettazione` → `data_accettazione`, `is_abortito` → `data_annullamento`, il rifiuto
dalla colonna nuova se S-3). Il resto della famiglia, documento per documento (guida §11), se S-2.

**pgTAP (costruito).** Nuovo `vendite/test-offerta-guard-dal-vocabolario-v1.sql`:

1. il comportamento: BOZZA→EMESSA congela la versione di listino e scrive `data_emissione`; ACCETTATA→ANNULLATA con un
   contratto vivo nato dall'offerta → il motivo di `fn_check_offerta_annullabile`;
2. **la marca spostata**: in transazione `accettazione` passa da ACCETTATA a RIFIUTATA (indice unico parziale: prima
   false, poi true); EMESSA→RIFIUTATA ora scrive `data_accettazione` e solleva il cancello dei prezzi (con un prezzo in
   attesa costruito sulla riga): prova che il guard non ricorda un codice;
3. presidio **sulla forma**, dichiarato tale: il corpo (senza commenti) non nomina più i cinque codici.

Builder: `dbops.fn_pgtap_crea_mondo_cliente`, `dbops.fn_pgtap_crea_listino` + `dbops.fn_pgtap_listino_aggiungi_articoli`,
`dbops.fn_pgtap_porta_a_stato` (offerta, sui passaggi manuali), `dbops.fn_pgtap_concedi_azione`,
`dbops.fn_pgtap_crea_contratto` (`p_offerta_id`, per l'annullabilità). ⚠️ **Non c'è un builder dell'offerta**: oggi ogni
pgTAP che ne serve una la scrive a mano (`test-offerta-al-modello-v1`, `test-fn-available-actions-offerta-v1`,
`test-righe-*`…), cioè la regola di come nasce un'offerta è ricopiata. Proposta: `dbops.fn_pgtap_crea_offerta(p_etichetta,
p_stato_codice_interno, p_billing_account_id, …)` sulla falsariga di `fn_pgtap_crea_contratto`, nello stesso cantiere.

**Ricadute.** Dell'offerta sola: nessuna (codici d'errore e loro parametri invariati; `grep` in `backend/apps`
`frontend/src` dei codici d'errore del guard: solo `_db_errors`, che non cambia). Se S-3 (`rifiuto`):
`backend/apps/vendite/services/offerte_service.py` `registra_rifiuto` sceglie lo stato con `StatoOfferta.RIFIUTATA`, una
copia del significato: passerebbe a un lettore del vocabolario come `registra_accettazione` (`stato_di_accettazione`).

### 4.3 ④ `terminale` con passaggi in uscita (S-1 = A)

**La regola del seed contro la matrice** (lettura del contratto, 2026-11-08):

| Vocabolario | Stato | `terminale` | Uscite attive a mano | Uscite di processo | Con A |
| --- | --- | --- | --- | --- | --- |
| offerte | SUPERATA | true | — | →EMESSA | ✅ |
| preventivi | EVASO | true | — | →ACCETTATO | ✅ |
| ordini | EVASO | true | — | →CONFERMATO, →PARZIALMENTE_EVASO | ✅ |
| bolla (derivato) | CONSEGNATO | true | — (→ANNULLATO c'è, spenta) | →RESO | ✅ |
| bolla (derivato) | RESO | true | — | →CONSEGNATO | ✅ |
| **reso (derivato)** | **CONFERMATO** | **true** (`fase = CHIUSO`) | **→ANNULLATO** (`conferma_reso`) | — | ❌ (S-5) |
| ordini | PARZIALMENTE_EVASO | false | — | →CONFERMATO, →EVASO | ✅ (vedi S-4) |
| listino | ATTIVA | false | — | →CHIUSA | ✅ (vedi S-4) |

Con A i quattro casi del §2 sono **giusti**: correggere il COMMENT basta. Il solo stato che A smentisce è il reso
confermato, e lo produce la regola scritta nella vista (⑦), non un vocabolario.

**`meta.manuale` c'è già, ed è dichiarato ovunque.** Ogni matrice di vendita ha il CHECK
`ck_*_meta_manuale_dichiarato` (`meta ? 'manuale'` e booleano: preventivi, offerte, contratti, ordini, ddt, reso, listino,
fiscale, commessa) e `ck_*_meta_ui` (una riga manuale ha `action_key` e `label_key`). Lo leggono
`script.fn_doc_passaggio` (il verbo comune: `E_DOC_PASSAGGIO_DI_PROCESSO`) e `dbops.fn_pgtap_porta_a_stato`. Accanto,
`meta.nessuna_azione_key` sul vocabolario dichiara gli stati senza uscita a mano (lo presidia
`config/test-transizioni-uscita-manuale-v1`, regola R1). **Non serve dichiarare niente di nuovo nella matrice**: serve
che `terminale` e la matrice non possano dissentire.

**I lettori di `terminale`.**

| Lettore | Dove | Che cosa ci legge | Con A |
| --- | --- | --- | --- |
| `vendite.vw_stato_sorgente_{offerta,preventivo,ordine,contratto}` | DB | passano la colonna | ✅ trasporto |
| `vendite.vw_stato_sorgente_{ddt,reso}` | DB | la **calcolano** (`fase = 'CHIUSO'`) | ❌ ⑦ |
| `script.vw_stato_sorgente`, `pratiche.fn_stato_sorgente` | DB | unione e lettura per chiave | ✅ trasporto |
| `script.vw_pratica_doc_sorgente`, `script.vw_flusso_doc_sorgente` | DB | spareggio dell'ancora: prima il documento **non** terminale («il più vivo») | ✅ «niente da fare a mano»: una SUPERATA cede alla revisione viva; tornata EMESSA, risale (lettura a ogni query, nessuna copia) |
| `pratiche.fn_reconcile_sorgente` | DB | legge **solo** `esito`, non `terminale` | — (l'«auto-chiusura su terminale» del brief di design non è costruita) |
| `backend/apps/pratiche/db/pratiche_repository.py:75, 105`; `types.py:247` | BE | `doc_terminale` dalle due viste, al FE | ✅ trasporto |
| `frontend/src/pratiche/components/PraticaPercorso.vue:206, 337` | FE | sui passi fatti il Tag dello stato del documento si mostra finché non è terminale | ✅ «niente da fare a mano» |
| `frontend/src/vendite/offerte/constants.js:40` `STATI_OFFERTA_TERMINALI` (letto da `OffertaDrawer.vue:205`) | FE | severity del banner; il commento dice già «stati in cui l'operatore non ha più nulla da fare» e che SUPERATA può tornare EMESSA | ✅ di significato, ❌ **copia** del vocabolario in JS (S-10) |
| `config.stati_doc_*` COMMENT di `terminale` (offerte, ordini, preventivi, contratti) | DB | «non evolverà più» | ❌ da riscrivere |
| `config.stati_doc_listino_versioni.terminale` COMMENT | DB | «Nessun passaggio esce da qui» (lettura B) | ❌ da allineare |
| `brief-design-proiezione-stato-dominio.md:175` | doc | «il documento non evolverà più (auto-chiusura milestone)» | ❌ da allineare (debito documentale: fuori da questo file) |
| `db/pgtap/script/test-seed-stati-doc-ordini-evaso-v1.sql:16` | pgTAP | «resta terminale per l'operatore: nessuna uscita manuale» | ✅ |

Nessun lettore usa `terminale` per «finito per sempre» in modo da **fermare** qualcosa (un guard, un job, una copia
persistente): tutti proiettano a lettura. A regge.

**Correzione.** (a) Il COMMENT nuovo di `terminale`, uguale sui cinque vocabolari che la hanno (e su bolla e reso con ⑦):

> true = da questo stato non esce nessun passaggio **a mano**: nessuna riga attiva della matrice con `meta.manuale` =
> true. L'operatore non ha più niente da fare sul documento. Il sistema può ancora spostarlo coi passaggi di processo
> (`manuale` = false: la revisione annullata che riporta emessa la precedente, l'evasione che si riapre); per questo chi
> lo legge lo rilegge, non lo copia. CHECK: implica `fase` = CHIUSO. Non sostituisce `is_abortito`.

(b) Un **building block** che rende la regola un vincolo e non un'abitudine: `script.trgfn_doc_terminale_senza_uscita_manuale`,
montato sulle matrici (`INSERT`, `UPDATE OF stato_da_id, attivo, meta`) e sui vocabolari (`INSERT`, `UPDATE OF terminale`),
col montaggio che nomina vocabolario e matrice come `script.fn_doc_stato_modello`; rifiuta una riga attiva `manuale =
true` che esce da uno stato terminale, e `terminale = true` su uno stato che ne ha una. Codice nuovo (es.
`E_DOC_TERMINALE_CON_USCITA_MANUALE`), sollevato solo da chi scrive la configurazione (le migrazioni). Implicazione,
non equivalenza: S-4.

**pgTAP (costruito).** Nuovo `config/test-terminale-senza-uscita-manuale-v1.sql`, tutto in transazione sulla
configurazione (nessun builder: si scrivono vocabolario e matrice):

1. uno stato nuovo terminale e una riga **manuale** attiva che ne esce → rifiutata; la stessa riga `manuale = false` →
   ammessa; spenta (`attivo = false`) → ammessa, e riaccenderla → rifiutata;
2. `terminale = true` su uno stato con un'uscita manuale attiva → rifiutato;
3. il lettore, a lettura: un'offerta EMESSA con una revisione (`vendite.fn_crea_revisione_offerta`) è SUPERATA e
   `pratiche.fn_stato_sorgente` dice `terminale = true`; annullata la revisione (`vendite.fn_annulla_offerta`) torna
   EMESSA e dice `false`. Builder: quelli dell'offerta di ③ (e `fn_pgtap_crea_offerta`, se si fa).

**Ricadute.** BE: nessuna (`pratiche_repository.py` trasporta). FE: nessuna di comportamento; la copia
`STATI_OFFERTA_TERMINALI` è S-10.

### 4.4 ⑤ Quattro stati d'ordine che nessun passaggio raggiunge

**Chi li nomina.**

| Dove | Che cosa |
| --- | --- |
| seed `config.stati_doc_ordini` | ALLOCATO 30, SPEDITO 40, CONSEGNATO 50 (`fase` IN_CORSO), FATTURATO 70 (CHIUSO, POSITIVO, terminale, `nessuna_azione_key` `vendite.ordini.stato_info.fatturato`); nessuna riga della matrice entra né esce |
| `vendite.fn_list_ordini_da_pushare` | `NOT IN ('DRAFT','ANNULLATO','FATTURATO')`: FATTURATO come «cintura» (il commento: l'anti doppia fatturazione vera è il NOT EXISTS sulle attività EMESSA) |
| `acquisti.ordini`, `acquisti.ordini_righe`, `vendite.ordini_righe` | FK su `config.stati_doc_ordini`: il vocabolario è **condiviso** con l'acquisto, che non ha guard di transizione (guida §10, ❌). Sull'acquisto quei quattro stati non li ferma nessuno |
| `vendite.ordini.fatturazione_trigger` | CHECK `CONFERMATO / SPEDITO / CONSEGNATO`: **un altro asse** (l'evento che rende la merce fatturabile), che riusa i nomi; non legge il vocabolario |
| FE `frontend/src/vendite/ordini/constants.js:15-19` | `STATO_ORDINE.ALLOCATO/SPEDITO/CONSEGNATO/FATTURATO`: dichiarati, **nessun lettore** (`grep STATO_ORDINE.ALLOCATO …`: vuoto) |
| FE `frontend/src/locales/{it,en}.json` | `vendite.ordini.stato_info.fatturato` |
| BE | nessun riferimento fuori dai test (`grep` di ALLOCATO e FATTURATO in `backend/apps`, file `.py`) |
| pgTAP | `pratiche/test-proiezione-stato-sorgente` (test 19, la mappa D1 dei nove stati), `vendite/test-testata-dopo-emissione-v1:109`, `script/test-doc-lock-montaggio-v1:470`; ordinamento in `script/test-seed-stati-doc-ordini-evaso-v1` e `vendite/test-vw-situazione-merce-ordine-v1` |
| guide e brief | `guide/gestione-ordini.md:399` («fasi logistiche/finanziarie future, ⏳ non ancora raggiunti»); `work-done/brief-ordini-azioni-data-driven` §7.2 e D-2; `work-done/brief-modello-documento-vendita:1649-1654` («si dichiara, non si tocca»); `work-done/brief-db-proiezione-stato-dominio-rollout-offerte-ordini-contratti:88-92, 249`; `work-in-progress/analisi-simmetria-ordini-acquisto` §4.2 (③: il vocabolario condiviso «parla vendite»; FATTURATO ha un altro posto nel ciclo d'acquisto) |

**La storia della decisione.** Nati col vocabolario (`2a8d6324f6`, 2025-09-12, «preparazione tabelle ordini vendita»).
Il 2026-06-05 (`e52204a37f`, brief-ordini-azioni-data-driven) Tid ratifica **D-2**: fuori dalla matrice «finché privi di
driver», perché la spedizione e la consegna vivono negli stati della bolla e la fatturazione nel `fatturazione_trigger`;
«verranno aggiunti quando magazzino/DDT ne saranno i driver». Il 2026-06-08 (`76c81c832a`) arriva EVASO, poi
PARZIALMENTE_EVASO: l'avanzamento dell'ordine lo proietta il DB dalle bolle. Il modello del documento (ottobre) li
dichiara e non li tocca.

**Correzione.** È S-8. Proposta DB: ritirarli (vedi §4.9).

**pgTAP (costruito).** Un presidio sulla **forma** del contratto (il seed lo è), dichiarato tale: ogni stato attivo di
ogni vocabolario della mappa `script.fn_doc_stato_modello` è raggiungibile dallo stato iniziale lungo righe attive della
matrice. Perché non sia verde per sottrazione, il pgTAP **costruisce** il controesempio: in transazione inserisce uno
stato attivo senza righe in entrata e verifica che il presidio lo trovi. Nessun builder.

**Ricadute (se ritirati).** FE: `frontend/src/vendite/ordini/constants.js` (quattro voci), `frontend/src/locales/it.json`
e `en.json` (`vendite.ordini.stato_info.fatturato`); i commenti che citano `ALLOCATO` come esempio di descrizione
restano veri come esempio solo se lo stato c'è: da riscrivere. ⚠️ Elenco corretto il 2026-11-12 (§5): sono **sei**,
non tre — `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue`,
`frontend/src/vendite/components/CommessaGestioneDrawer.vue`, `frontend/src/vendite/components/ContrattoDrawer.vue`,
`frontend/src/vendite/ordini/components/OrdiniDrawer.vue`, `frontend/src/vendite/ddt/components/DdtDrawer.vue`,
`frontend/src/vendite/resi/components/ResoDrawer.vue`. BE: nessuna. Doc: `guide/gestione-ordini.md` (la riga della
tabella «⏳ non ancora raggiunti»).

### 4.5 ⑥ Il controllo di `applica_fattura` in un ramo che non scatta

**Chi scrive e chi legge.** `vendite.trgfn_fatture_guard_stato` (`BEFORE UPDATE OF stato_doc_fiscale_id`) controlla
`applica_fattura` solo se `OLD.stato_doc_fiscale_id IS NULL`: sulla fattura la colonna è `NOT NULL` e la mette
`trg_fatture_a05_stato_iniziale_ins`, quindi il ramo non è raggiungibile **per contratto**. Il gemello
`vendite.trgfn_fatturazione_lotti_guard_stato` ha lo stesso ramo su `applica_lotto`, e lì **è raggiungibile** perché la
colonna del lotto è nullable (②). Gli altri lettori di `applica_*`: `vendite.fn_create_fatturazione_lotto` (filtro sulla
bozza), `vendite.fn_list_fatturazione_pipeline_steps`, `config.fn_get_stati_doc_fiscale`, `dbops.fn_pgtap_crea_lotto`.
Il FE ne ha solo le etichette (`locales`, «Si applica alla fattura»). Il passaggio normale (OLD non NULL) **non** guarda
`applica_*` della destinazione: lo dice solo la matrice (`solo_lotto`/`solo_fattura`), che non lega la riga alle colonne.

**Correzione.** La regola sulla **destinazione**, non sulla prima assegnazione: a ogni cambio di stato il guard della
fattura chiede `applica_fattura` allo stato d'arrivo, quello del lotto `applica_lotto` (stesso codice
`E_LOTTO_PARAMETRO_NON_COERENTE`, parametro `stato_doc_fiscale_id`); la nascita è coperta dal CHECK di ② (lo stato
iniziale si applica a entrambi). Il ramo «prima assegnazione» si ritira dai due guard. È S-7.

**pgTAP (costruito).** In `vendite/test-stati-doc-transizioni-giornaliero` (o un file nuovo): in transazione
`applica_fattura = false` su uno stato raggiunto da una riga della fattura; la fattura costruita
(`dbops.fn_pgtap_crea_fattura`) portata lì da `vendite.fn_fattura_proietta_stato` → rifiutata; il lotto, con
`applica_lotto = false` e `dbops.fn_pgtap_crea_lotto` + `vendite.fn_lotto_proietta_stato_step` → rifiutato.

**Ricadute.** Nessuna (BE e FE non leggono `applica_*` se non come etichetta).

### 4.6 ⑦ Bolla e reso non dichiarano `esito` e `terminale`

**Chi scrive e chi legge.** `vendite.vw_stato_sorgente_ddt` e `vendite.vw_stato_sorgente_reso` scrivono la regola nella
vista: `esito` = NEGATIVO se `is_abortito`, POSITIVO se `fase = 'CHIUSO'`; `terminale` = `fase = 'CHIUSO'`. Li leggono
`script.vw_stato_sorgente` → `pratiche.fn_stato_sorgente`, `pratiche.fn_reconcile_sorgente` (l'**esito** fa avanzare il
milestone e si scrive in `pratiche.flussi.esito`), le due viste d'ancora, e da lì il BE (`pratiche_repository.py`) e il
FE (`PraticaPercorso.vue`). Lo fissa `vendite/test-vw-stato-sorgente-ddt-reso-v1` (test 3-8, 13). Gli altri vocabolari
dichiarano le due colonne, con il guard `config.trgfn_stati_doc_guard_esito_verdetto` (montato su preventivi, offerte,
ordini, contratti) e il CHECK `terminale ⇒ fase = CHIUSO`.

La regola della vista dissente da A sul reso confermato (§4.3): `fase = CHIUSO` ma l'annullo a mano è attivo.

**Correzione.** Le colonne `esito` e `terminale` (NOT NULL) su `config.stati_doc_ddt` e `config.stati_doc_reso`, il CHECK
`chk_*_terminale_chiuso`, il montaggio del guard dell'esito; il seed dichiara i valori che oggi calcola la vista, tranne
quello che A smentisce (S-5); le due viste leggono le colonne. I COMMENT stantii del reso (`meta.fase`) nello stesso
changeSet.

**pgTAP (costruito).** Adeguare `vendite/test-vw-stato-sorgente-ddt-reso-v1` (test 7 secondo S-5) e aggiungere **la
marca spostata**: in transazione `terminale`/`esito` cambiati su uno stato della bolla, la vista segue (prova che non
ricalcola da `fase`). Builder: `dbops.fn_pgtap_crea_ddt_da_ordine` (CONSEGNATO, EMESSO), `dbops.fn_pgtap_crea_reso` più
`vendite.fn_conferma_reso`/`vendite.fn_annulla_reso`, `dbops.fn_pgtap_concedi_azione`.

**Ricadute.** Nessuna: le viste espongono le stesse colonne (BE `pratiche_repository.py`, FE `PraticaPercorso.vue`
leggono `doc_esito`/`doc_terminale`, invariati). Cambia un valore (il reso confermato), se S-5.

### 4.7 ⑧ Il vocabolario della versione di listino (minore)

**Chi scrive e chi legge.** `config.stati_doc_listino_versioni` ha `iniziale` e `terminale`, non `fase`. La versione di
listino **non è una sorgente** (`config.sorgenti` non la nomina) e nessun corpo legge una sua `fase`: il CHECK
`terminale ⇒ fase = CHIUSO` esiste per la proiezione nelle pratiche, che il listino non ha. Il nome dell'indice
`ux_stati_doc_listino_versioni_iniziale` compare solo nello YAML `20261028-03` e nella pagina auto-gen; nessun pgTAP lo
nomina. I letterali BOZZA del listino sono in S-2, ATTIVA/CHIUSA in S-3.

**Correzione.** Rinominare l'indice in `uq_stati_doc_listino_versioni_iniziale`; allineare il COMMENT di `terminale` al
testo di ④; `fase` secondo S-9.

**pgTAP.** `has_index` sul nome nuovo nel pgTAP del listino al modello (`vendite/test-listino-versione-al-modello-v1`); è
un presidio sulla forma, dichiarato tale.

**Ricadute.** Nessuna.

### 4.8 COMMENT stantii del §2

Ognuno entra nel changeSet del vocabolario che si tocca (②, ④, ⑦, ⑧) o, per i vocabolari che il cantiere non tocca
altrimenti (contratti, fiscale, `vendite.contratti.is_abortito_snapshot`), in un changeSet di soli COMMENT. Nessun lettore
(i COMMENT li legge la doc auto-gen).

### 4.9 Le decisioni che il censimento chiede a Tid

* **S-2 — Il perimetro di ③.** Il guard dell'offerta è un caso di una famiglia (§4.2): un letterale per dire un
  significato che il vocabolario dichiara già in colonna (`iniziale`, `emissione`, `accettazione`, `cessazione`,
  `is_abortito`, `scadenza`, `is_superato`). **Proposta DB:** il cantiere prende **tutta la famiglia**, un documento per
  volta (offerta, preventivo, ordine, contratto, bolla, reso, listino, fiscale), con il presidio sulla forma per
  documento. *Perché:* la guida (§4, §11) non distingue fra un guard e una capability: una copia del significato è una
  seconda verità ovunque stia, e portarne via una sola lascia la regola ricopiata nelle altre.
* **S-3 — I significati che il vocabolario non ha.** Tre stati hanno un significato che il codice usa ma nessuna colonna
  dice: il **rifiuto** (offerta RIFIUTATA: `data_rifiuto`, la motivazione obbligatoria; preventivo RIFIUTATO),
  l'**emissione del reso** (CONFERMATO: lì nasce il numero, `trgfn_resi_gen_numero`; e da lì la merce è rientrata,
  `script.vw_stati_doc_reso_merce_rientrata`, nata il 2026-11-09, §5) e l'**emissione fiscale** (EMESSA: il
  cancello IVA di `trgfn_fatture_guard_stato`). **Proposta DB:** una colonna `rifiuto` su offerte e preventivi (come
  `accettazione`, col suo lettore `script.fn_stato_rifiuto_id`), `emissione` su `stati_doc_reso` e `stati_doc_fiscale`
  (⚠️ per `stati_doc_fiscale` **revocata** da Tid il 2026-11-13, R-1 del §6.4).
  Restano nominati col codice, attraverso `script.fn_doc_stato_id`, gli stati che sono **la destinazione di un
  processo** (EVASO, PARZIALMENTE_EVASO, SPEDITO, CONSEGNATO, RESO della bolla, ATTIVA e CHIUSA del listino): il processo
  nomina la sua destinazione come la nomina la riga della matrice. *Perché:* la colonna serve dove c'è un lettore che
  usa lo stato **per il suo significato**; dove il lettore vuole proprio quello stato, il codice è la chiave giusta.
* **S-4 — `terminale`: implicazione o equivalenza.** **Proposta DB:** implicazione: `terminale ⇒ nessuna uscita attiva a
  mano`, non il contrario. *Perché:* PARZIALMENTE_EVASO non ha uscite a mano ma l'operatore ha ancora da fare (le bolle):
  il lavoro può stare fuori dalla matrice; «niente da fare a mano» vuol dire anche niente da fare fuori dai bottoni di
  stato, e quello lo dichiara il vocabolario, non lo si deduce dalla matrice. Una riga spenta (`attivo = false`) non
  conta come uscita.
* **S-5 — Il reso confermato.** Con A non è terminale: l'annullo (storno) è un passaggio a mano attivo. **Proposta DB:**
  `terminale = false`, `esito` POSITIVO, `fase` resta CHIUSO (il CHECK lega solo terminale → CHIUSO; il reso ha fatto il
  suo lavoro, come l'offerta accettata che resta annullabile). *Perché:* è la stessa regola che vale per offerta e
  preventivo accettati, annullabili e non terminali. Il test 7 di `test-vw-stato-sorgente-ddt-reso-v1` cambia insieme.
* **S-6 — Lo stato del lotto `NOT NULL`.** **Proposta DB:** sì, come la fattura. *Perché:* la guida (§3) vuole che un
  documento nasca nel suo stato iniziale; un lotto senza stato non è sul modello, e i rami fail-closed che lo gestiscono
  (`vw_documenti_trattenuti_da_lotto`, `vw_lotti_fase`) proteggono un caso che il contratto non deve ammettere. I due
  test che lo costruiscono si ritirano con lui.
* **S-7 — `applica_*` sulla destinazione.** **Proposta DB:** il controllo a ogni ingresso nello stato, nei guard di
  fattura e lotto, più il CHECK «l'iniziale si applica a entrambi»; il ramo «prima assegnazione» si ritira. *Perché:* la
  matrice dice da dove a dove, il vocabolario dice a chi si applica lo stato: la regola sulla destinazione copre ogni
  strada, anche quelle future (lo stesso ragionamento del cancello IVA, «sulla destinazione, non sulla coppia»).
* **S-8 — ALLOCATO, SPEDITO, CONSEGNATO, FATTURATO.** **Proposta DB:** ritirarli dal vocabolario (con le loro chiavi
  i18n, le costanti FE e la «cintura» di `fn_list_ordini_da_pushare`). *Perché:* nel modello di oggi l'avanzamento
  dell'ordine lo proietta il DB dalle bolle (EVASO, PARZIALMENTE_EVASO), la spedizione e la consegna sono stati della
  bolla, la fatturazione è della commessa e della fattura: quattro stati d'ordine che le ripetono sarebbero una seconda
  verità, e D-2 li teneva solo «finché privi di driver». In più il vocabolario è condiviso con l'acquisto, che non ha
  guard: finché ci sono, un ordine d'acquisto li può prendere senza regola. Il giorno che servissero, il ciclo d'acquisto
  li dichiarerà nel suo cantiere (`analisi-simmetria-ordini-acquisto` §4.2 propone già il vocabolario per ambito).
  Alternativa: tenerli come «previsti», `attivo = false` e documentati.
* **S-9 — `fase` sulla versione di listino.** **Proposta DB:** non aggiungerla; solo il nome dell'indice e il COMMENT.
  *Perché:* `fase` è l'asse della proiezione nelle pratiche, e la versione di listino non è una sorgente; una colonna
  senza lettore è una dichiarazione che nessuno verifica.
* **S-10 — Le copie fuori dal DB.** `STATI_OFFERTA_TERMINALI` (FE) ripete `terminale`; `StatoOfferta.RIFIUTATA` in
  `registra_rifiuto` (BE) ripete il rifiuto (se S-3). **Proposta DB:** la capability dell'offerta
  (`script.fn_available_actions_offerta`) espone `terminale` dello stato corrente, il FE legge quella e ritira la costante;
  il BE sceglie il rifiuto dal vocabolario. *Perché:* la guida §11: le copie si ritirano nello stesso lavoro.

### 4.10 Le ricadute BE/FE, elenco chiuso

| Difetto | BE | FE |
| --- | --- | --- |
| ② | nessuna (due test Django passano DRAFT, che è l'iniziale) | nessuna |
| ③ | nessuna; con S-3: `backend/apps/vendite/services/offerte_service.py` (`registra_rifiuto`) | nessuna |
| ④ | nessuna | nessuna; con S-10: `frontend/src/vendite/offerte/constants.js`, `frontend/src/vendite/offerte/components/OffertaDrawer.vue` |
| ⑤ (S-8) | nessuna | `frontend/src/vendite/ordini/constants.js`, `frontend/src/locales/it.json`, `frontend/src/locales/en.json`; commenti nei sei drawer del §4.4 (elenco corretto il 2026-11-12) |
| ⑥ | nessuna | nessuna |
| ⑦ | nessuna (stesse colonne; cambia un valore con S-5) | nessuna |
| ⑧ | nessuna | nessuna |

Il codice d'errore nuovo di ④ lo solleva solo chi scrive la configurazione: da registrare (`codici_errore.csv`,
`messaggi_errore.csv`), senza ricadute sul BE oltre al catalogo generato.

## 5. Riverifica sul catalogo (team DB, 2026-11-12)

Fonti: `pg_proc.prosrc`, `pg_get_viewdef`, `pg_trigger`, `pg_index`, `pg_description`, seed e matrici su dbdev (applicato
fino al 2026-11-12), in sola lettura; `grep` in `backend/apps` e `frontend/src`. Fra il 2026-11-08 e il 2026-11-12 sono
entrati circa 400 changeSet, e un centinaio tocca oggetti nominati qui.

**Reggono tutti i difetti del §2 e i fatti del §4.** Letterale `'DRAFT'` nella madre del lotto, nessun trigger della
nascita sul lotto, colonna di stato nullable (②); i cinque codici nel guard dell'offerta, nessuna colonna `rifiuto`
(③); le uscite di processo da SUPERATA, EVASO (preventivi e ordini), CONSEGNATO e RESO della bolla, l'uscita a mano
CONFERMATO→ANNULLATO del reso (④, S-5); i quattro stati d'ordine fuori dalla matrice, la «cintura» FATTURATO di
`fn_list_ordini_da_pushare` (⑤); il ramo «prima assegnazione» di `trgfn_fatture_guard_stato` (⑥); la regola su
`fase = 'CHIUSO'` nelle due viste di bolla e reso (⑦); l'indice `ux_…` e la `fase` che manca sul listino (⑧); tutti i
COMMENT stantii del §2; nessun `terminale` letto da `fn_available_actions_offerta` (S-10). Esistono tutti i pgTAP
citati; non esistono ancora quelli nuovi (`test-offerta-guard-dal-vocabolario-v1`,
`test-terminale-senza-uscita-manuale-v1`) e il builder `dbops.fn_pgtap_crea_offerta`.

**Corretto in questa verifica.**

1. **Mancava al censimento di ③ la vista della bolla** `script.vw_stati_doc_ddt_merce_partita` (BB del 2026-10-12):
   trova lo stato da cui si conta col letterale `'EMESSO'`, mentre `config.stati_doc_ddt.emissione` lo dice già.
   Aggiunta alla riga «bolla» del §4.2. Il resto della regola, «da quello stato in poi» per `ordine`, è la scelta (a)
   di Tid del 2026-10-12 e **non** si tocca qui.
2. **Una vista nuova dopo il brief:** `script.vw_stati_doc_reso_merce_rientrata` (2026-11-09, gemella della
   precedente; la leggono `dbops.vw_resi_confermati_senza_carico`, `vendite.vw_resi_righe_effettive`,
   `vendite.vw_resi_da_riconsegnare`) trova lo stato col letterale `'CONFERMATO'`. È un lettore dell'**emissione del
   reso** di S-3: quando nasce `config.stati_doc_reso.emissione`, legge quella. Aggiunta a S-3.
3. **Le ricadute FE di S-8 erano incomplete.** I commenti che citano `ALLOCATO` come esempio stanno in sei drawer, non
   in tre, e due dei tre percorsi erano sbagliati. Elenco chiuso, coi percorsi interi, corretto nel §4.4 e nel §4.10.
4. Riferimenti di riga che si sono spostati: `guide/gestione-ordini.md` (la riga «⏳ non ancora raggiunti» oggi è la
   402); in `backend/apps/pratiche/db/pratiche_repository.py` il secondo lettore di `terminale` è la `LATERAL` su
   `script.vw_flusso_doc_sorgente` (intorno alla 104).

⚠️ **Per chi sviluppa: i corpi sono cambiati dopo il 2026-11-08.** Il comportamento letto qui regge, ma molti oggetti
del censimento hanno una revisione più recente del brief, e alcune sono più recenti della doc auto-generata:
`vendite.fn_conferma_reso`, `vendite.fn_annulla_reso` (2026-11-09/10), `vendite.fn_list_ordini_da_pushare`
(2026-11-08), `vendite.fn_resolve_prezzo_listino_v2_esito` (2026-11-12),
`vendite.trgfn_listini_righe_comp_guard_immutabilita_v5` (2026-11-11), `pratiche.fn_stato_sorgente` e
`pratiche.fn_reconcile_sorgente` (2026-11-08), `dbops.fn_pgtap_crea_lotto` e i builder di bolla, ordine, preventivo,
fattura e reso (2026-11-08). Il DDL si prende dalla doc auto-gen solo se è stata rigenerata dopo l'ultimo changeSet
sull'oggetto; altrimenti da `pg_get_functiondef`. Mai dagli YAML.

## 6. Lo sviluppo (team DB)

### 6.1 L'ordine dei giri

Un giro per vocabolario o per difetto, così ogni oggetto si apre una volta sola:

| Giro | Che cosa | Difetti e decisioni |
| --- | --- | --- |
| 1 ✅ applicato | il vocabolario fiscale: lotto e fattura | ②, ⑥, S-6, S-7; S-2 sul fiscale. L'emissione fiscale di S-3 è revocata (R-1) |
| 2 ✅ applicato | l'offerta | ③, S-3 (`rifiuto` su offerte e preventivi), S-10 per l'offerta, il builder `dbops.fn_pgtap_crea_offerta` |
| 2-bis ✅ applicato (V-1) | i trovati della verifica BE/FE | V-1 (la sede della scadenza) |
| 2-ter ✅ applicato | D-LOCK (a) e V-2 | ⑨: il lock riconosce la bozza dal vocabolario (§6.11) |
| 3 ✅ applicato | `terminale`, bolla e reso | ④ (il BB e i COMMENT), ⑦, S-4, S-5, S-3 (`emissione` del reso, coi due lettori del §5) |
| 4 ✅ applicato | gli stati d'ordine senza passaggi | ⑤, S-8, il presidio della raggiungibilità; R-3 (`applica_lotto` = false su REGISTRATA) |
| 5 ✅ applicato | il vocabolario del listino e i COMMENT stantii | ⑧, S-9, §4.8; R-2 (il ritiro di `in_gioco`, se la riga 11 è fatta) |
| 6 … | il resto della famiglia di S-2 | un documento per volta: preventivo, ordine, contratto, bolla, reso, listino |

### 6.2 Giro 1 — il vocabolario fiscale (2026-11-12)

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261112-44` | CHECK `chk_stati_doc_fiscale_iniziale_applica`: lo stato iniziale si applica a lotto e fattura (§4.1 d) |
| `20_code/vendite/20261112-45` | il trigger della nascita sul lotto, `trg_fatturazione_lotti_a05_stato_iniziale_ins` (§4.1 a) |
| `00_schema/vendite/20261112-46` | `vendite.fatturazione_lotti.stato_doc_fiscale_id NOT NULL` (S-6) |
| `20_code/vendite/20261112-47` | `vendite.fn_create_fatturazione_lotto` non sceglie più lo stato (§4.1 b) |
| `20_code/vendite/20261112-48` | `vendite.trgfn_fatture_guard_stato`: `applica_fattura` sulla destinazione, via il ramo «prima assegnazione» (S-7) |
| `20_code/vendite/20261112-49` | `vendite.trgfn_fatturazione_lotti_guard_stato`: lo stesso con `applica_lotto` (S-7) |
| `20_code/script/20261112-50` | `script.fn_check_lotto_fatture_pre_fiscali`: «pre-fiscale» da `congela_fiscale`, non da DRAFT ed EMESSA (S-2) |
| `20_code/vendite/20261112-51` | `vendite.trgfn_fatture_guard_uscita_draft`: la bozza da `iniziale` (S-2) |
| `20_code/vendite/20261112-52` | `vendite.fn_imposta_data_documento_lotto`: la finestra da `congela_fiscale` (S-2) |

Corpi presi da `pg_get_functiondef` su dbdev, testate ri-ancorate con `%TYPE`, COMMENT riscritti al presente; ogni
changeSet porta nel rollback il corpo e il COMMENT di prima. Il cancello IVA del guard della fattura resta sul codice
EMESSA (R-1: eccezione voluta). Fatto datato, 2026-11-12: ogni stato fiscale ha `applica_lotto` e `applica_fattura` true, e DRAFT ed
EMESSA sono gli unici con `congela_fiscale` false, quindi nessun passaggio di oggi cambia esito. I rami fail-closed di
`vendite.vw_lotti_fase` e `vendite.vw_documenti_trattenuti_da_lotto` restano (sono un LEFT JOIN corretto anche col
NOT NULL); si ritirano i casi dei pgTAP che li costruivano.

Guardrail delle forme, del COMMENT al presente e del preambolo pgTAP: verdi. Estratto provato in `ROLLBACK` sullo
scratch con `scripts/prova_changeset.py`: eseguito per intero, catalogo identico prima e dopo. BE/FE: nessuna ricaduta
(i due test Django che inseriscono un lotto passano DRAFT, che è lo stato iniziale). Pagine `manual/` riscritte:
`config/stati_doc_fiscale`, `vendite/fn_create_fatturazione_lotto`, `vendite/fatturazione_lotti`,
`script/fn_check_lotto_fatture_pre_fiscali`, `vendite/trgfn_fatture_guard_uscita_draft`,
`vendite/fn_imposta_data_documento_lotto`. La doc auto-generata non è rigenerata.

### 6.3 I pgTAP del giro 1

Nuovi o estesi:

* `script/test-trgfn-doc-stato-iniziale-v1` (plan 18 → 22): il lotto nel censimento dei montaggi (test 5, 6: dodici
  testate); nuovi 19 (il lotto dalla madre nasce nello stato iniziale), 20 (un lotto che nasce DEFINITIVA è
  rifiutato), 21 (la marca spostata: con `iniziale` su EMESSA la madre crea il lotto in EMESSA), 22 (il CHECK);
* `vendite/test-stato-fiscale-dal-vocabolario-v1` (nuovo, plan 8): S-7 su fattura e lotto, ognuno col suo contrasto;
  «pre-fiscale» con la marca spostata su `congela_fiscale`; il presidio sulla forma, che tiene a un punto solo l'eccezione di R-1.

Adeguati, perché facevano nascere il lotto in uno stato che il trigger ora rifiuta:

* `vendite/test-annullamento-chiude-la-vita-v1`, `vendite/test-lotti-fermi-verdetto-a-db-v1`,
  `vendite/test-motivo-non-fatturata-v1`: il lotto nasce in bozza e si porta allo stato voluto con
  `dbops.fn_pgtap_porta_a_stato`;
* `vendite/test-vw-lotti-fase-v1` (plan 8 → 5) e `vendite/test-documento-trattenuto-da-lotto-v1` (plan 7 → 6):
  stessa forma, e ritirati i test del lotto senza stato (S-6). In `test-lotti-fermi-verdetto-a-db-v1` c'era un terzo
  caso uguale, il test 24, che il §4.1 non elencava: ritirato anche quello (plan 24 → 23). Tolto da
  `test-vw-lotti-fase-v1` anche il testimone REGISTRATA, che un lotto non raggiunge (R-3);
* `test-documento-trattenuto-da-lotto-v1` ora **costruisce** il suo mondo (`dbops.fn_pgtap_crea_emittente_operatore`,
  runner owner come il gemello): prendeva emittente e tipo documento «da un lotto che c'è già», e su un database senza
  lotti (lo scratch, la CI) non scriveva niente, verde per sottrazione;
* `vendite/test-fondi-fattura-lotto`: solo il commento della fixture (il lotto ora nasce in bozza, come le figlie).

Regressione con `prova_changeset.py --pgtap`, senza e con l'estratto, su 118 file che nominano il vocabolario fiscale,
il lotto, il BB della nascita o gli oggetti toccati: tutti uguali o migliori. I rossi rimasti sono di prima:
`script/test-vw-giornale-entita` si interrompe senza e con l'estratto su un dato che lo scratch non ha (passa dalla
madre e non nomina lo stato del lotto); i test di perimetro RLS sono rossi da owner per costruzione. I pgTAP li lancia
Tid.

**Esito (Tid, 2026-11-13):** giro 1 applicato su dbdev, pgTAP del §6.3 verdi.

### 6.4 Trovati dal giro 1 — decisi da Tid (2026-11-13)

Decise da Tid il 2026-11-13, tutte e tre come proposte dal DB (per R-2 il ritiro, non il mantenimento).

* **R-1 — L'emissione fiscale di S-3: revocata.** S-3 proponeva `emissione` su `config.stati_doc_fiscale`, per il
  cancello IVA del guard della fattura. Il 2026-10-25 (`20261025-37`, brief-modello-documento-vendita §8) la colonna era
  nata **solo** sui cinque documenti che passano da «Emetti», e la fattura ne era stata esclusa apposta: «la pipeline
  non emette, il lettore risponde NULL». Il backend legge `script.fn_stato_emissione_id` per rifiutare l'emissione sul
  cambio stato generico: dare la colonna alla fattura cambierebbe anche quella risposta. **Deciso:** per il fiscale
  niente colonna `emissione`; il cancello IVA nomina EMESSA, ed è l'**unico** punto del fiscale che nomina un codice.
  Non è un debito: è un'eccezione voluta, tenuta a un punto solo dal test 8 di
  `test-stato-fiscale-dal-vocabolario-v1` (frase aggiornata il 2026-11-13). Se un giorno un secondo lettore vorrà
  sapere «da qui la fattura è emessa», serve una colonna col suo nome, non quella di «Emetti».
* **R-2 — `in_gioco` senza un caso suo: si ritira.** `vendite.vw_lotti_fase` ha due flag, `pre_fiscale` e `in_gioco`,
  e l'unico caso in cui dissentivano era il lotto senza stato (il test 8 di `test-vw-lotti-fase-v1`: «è tutta la
  ragione per cui sono due flag»). Con S-6 quel caso non esiste più: `in_gioco` è una copia di `pre_fiscale`, e una
  copia si ritira nello stesso cantiere. Lettori, censiti sul catalogo di dbdev e nel codice il 2026-11-13:

  | Lato | Lettore | Cosa cambia |
  | --- | --- | --- |
  | DB | `vendite.vw_dash_competenza_attivita` (`lfase.in_gioco`, motivo GIRO_IN_CORSO) | legge `pre_fiscale` |
  | DB | `vendite.vw_documenti_trattenuti_da_lotto` (`f.in_gioco`) | legge `pre_fiscale` |
  | DB | `script.fn_check_attivita_riportabile_da_emettere` (`f.in_gioco AS marchio_in_gioco`) | legge `pre_fiscale` |
  | BE | `backend/apps/vendite/tests/db/test_riepilogo_esclude_trattenuti.py` (righe 119-225: `SELECT in_gioco FROM vendite.vw_lotti_fase`, il metodo `_crea_lotto_in_gioco` e i commenti) | legge `pre_fiscale` |
  | FE | nessuno | — |

  **Chi cambia per primo:** il BE (riga 11 della testata), perché `pre_fiscale` c'è già e vale quanto `in_gioco`: il test
  passa prima e dopo. Poi il DB, nel giro 5: i tre lettori passano a `pre_fiscale` e la colonna esce dalla vista (che va
  ricreata con le sue dipendenti), insieme alle pagine `vw_lotti_fase`, `vw_documenti_trattenuti_da_lotto`,
  `vw_dash_competenza_attivita` e `fn_check_attivita_riportabile_da_emettere`, e ai pgTAP che la nominano
  (`test-vw-lotti-fase-v1`, `test-documento-trattenuto-da-lotto-v1`, `test-motivo-non-fatturata-v1`). Se il BE non ha
  ancora fatto la sua parte, il DB porta i tre lettori e lascia la colonna.
* **R-3 — REGISTRATA e il lotto: il lotto non diventa REGISTRATO.** REGISTRATA ha `applica_lotto` = true, ma nessuna riga
  della matrice porta un lotto in REGISTRATA (INVIATA → REGISTRATA è solo della fattura): la registrazione è un fatto
  della singola fattura. **Deciso:** `applica_lotto` = false su REGISTRATA, dal CSV, nel giro 4, insieme al presidio
  della raggiungibilità di ⑤, che altrimenti la segnalerebbe sull'asse del lotto. Così il vocabolario dice la stessa
  cosa della matrice.

Minori, da chiudere quando si riaprono gli oggetti: il BB della nascita, sul lotto, nomina la tabella
(`fatturazione_lotti`) nella frase del rifiuto, perché il lotto non è in `config.sorgenti` (come la versione di
listino; lo raggiunge solo un `INSERT` diretto, la madre non passa lo stato); il commento nel corpo di
`dbops.fn_pgtap_crea_lotto` dice ancora che lo stato DRAFT lo decide la madre.

### 6.5 Giro 2 — l'offerta (2026-11-13)

Il via di Tid è del 2026-11-13; il range `20261112-59 … -64` l'ha dato Tid, con una seconda sessione DB attiva.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261112-59` | la colonna `rifiuto` su `config.stati_doc_offerte` e `config.stati_doc_preventivi` (S-3): `NOT NULL DEFAULT false`, `chk_<vocabolario>_rifiuto_attivo`, `uq_<vocabolario>_rifiuto`, come `accettazione` |
| `80_data`, due CSV e due mirror | `stati_doc_offerte.csv` e `stati_doc_preventivi.csv`: colonna `rifiuto` in coda, vera su RIFIUTATA e RIFIUTATO; `- column: rifiuto` nei mirror `20260524-04` e `20250917-01` (`runOnChange` + `ANY`, §11.2) |
| `20_code/script/20261112-60` | `script.fn_stato_rifiuto_id(regclass)`, gemello di `fn_stato_accettazione_id` sul lettore comune (S-3). Nel DB non ha consumatori: il guard ha già la riga del vocabolario. Lo legge il BE (§6.7) |
| `20_code/vendite/20261112-61` | ③: `vendite.trgfn_offerte_commerciali_guard_transizione` legge le colonne. L'emissione è `iniziale` → `emissione`; i prezzi vanno verso `emissione` o `accettazione`; l'annullo verso `is_abortito`; le date dalla colonna della destinazione (`rifiuto` → `data_rifiuto`) |
| `20_code/script/20261112-62` | S-2 e S-10 per la capability: `script.fn_available_actions_offerta` legge «in bozza» da `iniziale` (i motivi delle righe dell'emissione, `can_edit_eccezioni`) ed espone la chiave nuova `stato_terminale`. Firma ancorata con `%TYPE`; il COMMENT, che era una cronaca, è riscritto al presente |
| `20_code/vendite/20261112-63` | S-2 per il cruscotto: `vendite.vw_dash_fatturazione_offerte` dà `DOC_BOZZA` da `iniziale` e `IN_ATTESA_ACCETTAZIONE` da `emissione`. Le colonne sono le stesse; `security_invoker` si ripete, perché un `CREATE OR REPLACE VIEW` senza opzioni le azzera |
| `20_code/dbops/20261112-64` | il builder `dbops.fn_pgtap_crea_offerta` (§4.2). Compone `fn_pgtap_cliente_del_builder` e `fn_pgtap_crea_listino`, fa nascere la testata come il backend (con l'indirizzo di default da `vendite.fn_doc_indirizzo_default`) e porta allo stato con `fn_pgtap_porta_a_stato` |

**Trovato riaprendo la famiglia dell'offerta** (non era nel censimento del §4.2): la vista
`vendite.vw_dash_fatturazione_offerte` nominava `'BOZZA'` ed `'EMESSA'` per il motivo del fermo. È entrata in questo
giro, perché S-2 prende la famiglia un documento per volta. Gli altri letterali che il censimento del 2026-11-13 ha
trovato non sono stati dell'offerta: `'RIFIUTATA'` delle commesse è l'approvazione delle attività, e
`'ANNULLATA'` di `vendite.fn_documento_lineage_legami` è lo stato di emissione di un'attività. I due `v_stato_cod`
che restano nella capability vanno ai building block del lucchetto (`fn_doc_testata_in_stato`,
`fn_doc_riga_modificabile`), che ragionano per codice nel loro montaggio: non sono una copia del significato.
⚠️ **Smentito il 2026-11-14 (§6.10, V-2):** il montaggio scrive la bozza con un codice (`stato_bozza`), e con
`iniziale` spostata il lock e la capability si separano. È il difetto ⑨, e la decisione è D-LOCK.

Corpi presi da `pg_get_functiondef` e `pg_get_viewdef` su dbdev il 2026-11-13. Ogni changeSet porta nel rollback la
definizione e il COMMENT di prima, letti dal catalogo e non ricopiati a mano. Con il vocabolario del seed ogni
passaggio ha l'esito di prima: cambia solo da dove si legge il significato. I codici d'errore, i loro parametri e il
montaggio del trigger restano gli stessi.

Pagine `manual/` scritte o riscritte: `config/stati_doc_offerte`, `config/stati_doc_preventivi`,
`script/fn_stato_rifiuto_id` (nuova), `script/fn_stato_per_colonna_id`, `script/fn_available_actions_offerta`,
`vendite/trgfn_offerte_commerciali_guard_transizione` (riscritta: descriveva ancora la versione di listino fissata
dal backend), `vendite/vw_dash_fatturazione_offerte`, `dbops/fn_pgtap_crea_offerta` (nuova); guida
`modello-documento-di-vendita` (il lettore del rifiuto). La doc auto-generata non è rigenerata.

### 6.6 La prova e i pgTAP del giro 2

* **Nuovo** `vendite/test-offerta-guard-dal-vocabolario-v1` (plan 12). Prova il builder, le date dal significato, il
  lettore del rifiuto sui tre casi, l'indice unico, `stato_terminale`, e due **marche spostate** in transazione,
  ognuna col suo contrasto. Con l'accettazione su RIFIUTATA, lo stesso passaggio scrive `data_accettazione`. Con
  l'iniziale su EMESSA, l'offerta emessa ha `can_edit_eccezioni` e il motivo `DOC_BOZZA`. Il test 12 è il presidio
  sulla forma: guard, capability e vista non nominano i codici dell'offerta. Il builder per ora non ha un test suo
  come i fratelli: lo provano i test 1-3.
* **Adeguato** `vendite/test-indirizzi-documento-seguono-cliente-v1`, test 3. È il censimento dei chiamanti di
  `vendite.fn_doc_indirizzo_default`, e il builder nuovo è un chiamante voluto, perché fa nascere l'offerta come il
  backend.

**Prova (scratch `zeroerp_ruoli`, 2026-11-13).** Il guardrail delle forme, del COMMENT al presente, dei letterali,
del `runOnChange` e del preambolo pgTAP è verde. L'estratto dei sei changeSet gira per intero in `ROLLBACK` e il
catalogo resta identico.

⚠️ **Il mirror è simulato.** `prova_changeset.py` non esegue i `loadUpdateData`, quindi i valori di `rifiuto` li ha
scritti un changeSet di sola prova nello scratchpad (un `UPDATE` per vocabolario), che non entra nel repo. Il
caricatore vero lo prova l'apply.

**Regressione** con `--pgtap`, senza e con l'estratto, sui 104 file che nominano gli oggetti toccati (i due
vocabolari, il guard, la capability, le due viste del cruscotto, i lettori degli stati):

* 103 uguali;
* uno peggiore, `test-indirizzi-documento-seguono-cliente-v1` (il chiamante nuovo), adeguato e poi verde con
  l'estratto (18/18). Senza l'estratto ora è rosso: chiede un builder che prima dell'apply non c'è;
* il test nuovo: 12/12 con l'estratto, interrotto senza (il builder non c'è).

Rossi uguali senza e con l'estratto, quindi già presenti: `test-ordine-al-modello-v1` (1) e
`test-refactor-qta-operativa-preventivi-v1` (5). I pgTAP li lancia Tid.

**Esito (Tid, 2026-11-13):** giro 2 applicato su dbdev, mirror compresi; pgTAP verdi.

### 6.7 Richieste al team BE/FE del giro 2 (elenco chiuso)

**Chi cambia per primo: il DB.** Le colonne e la chiave nuova devono esserci prima che BE e FE le leggano. Finché il
BE/FE non cambia, il comportamento resta quello di oggi: la chiave nuova la ignora chi non la legge.

| Lato | File | Che cosa |
| --- | --- | --- |
| BE | `backend/apps/core/db/documento_modello_repository.py` | il lettore `_LETTORE_RIFIUTO = "script.fn_stato_rifiuto_id"` e il metodo `stato_di_rifiuto(testata)`, gemelli di `stato_di_accettazione` |
| BE | `backend/apps/core/services/documento_modello.py` | `stato_di_rifiuto(testata, *, function_name)`, gemello di `stato_di_accettazione` |
| BE | `backend/apps/vendite/services/offerte_service.py` | `registra_rifiuto` sceglie lo stato con `stato_di_rifiuto(TESTATA_OFFERTE, …)` invece di `StatoOfferta.RIFIUTATA`, come `registra_accettazione`. `RIFIUTATA` resta come **parola dell'API** in `_ESITI`, come oggi `ACCETTATA` |
| FE | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | `isStatoTerminale` legge `capabilities.stato_terminale` invece di `STATI_OFFERTA_TERMINALI` |
| FE | `frontend/src/vendite/offerte/constants.js` | ritira `STATI_OFFERTA_TERMINALI` e il suo commento |

Non serve altro nel BE perché la capability viaggia intera sotto `capabilities` (`offerte_service.get_offerta`).

⚠️ **Fuori da questo elenco: D-SCAD, la scadenza dell'offerta.** ✅ Decisa da Tid il 2026-11-13: (a). Sviluppo al
§6.8. Trovata scrivendo S-10, verificata
sul catalogo il 2026-11-13. La regola «quest'offerta è scaduta» oggi sta in due metà:

* il DB, in `vendite.vw_offerte_commerciali_lista.is_scaduta`, dice solo «`validita_al` è passata
  (`script.fn_data_operativa`)», in **qualunque** stato;
* il FE la completa con `STATI_OFFERTA_SEGNALA_SCADENZA` (`BOZZA`, `EMESSA`), in **due** punti:
  `OfferteSearchTable.vue` (il badge della lista) e `OffertaDrawer.vue` (il badge del dettaglio). Un'offerta accettata,
  rifiutata o annullata con la validità passata non è «scaduta» per l'operatore.

È una regola di dominio scritta per metà nel frontend, ed è lavoro **DB**: la regola intera va nella vista, e il FE
legge il flag e ritira la costante. Il seed della lista ha anche la colonna configurabile «Scaduta» su `is_scaduta`
(`ui.lista_colonna` id 92), che oggi dice «sì» anche su un'offerta accettata: con la regola intera direbbe la stessa
cosa del badge.

**Che cosa vuol dire «gli stati in cui la scadenza conta».** Sul modello sono gli stati in cui il cliente non ha
ancora risposto: la bozza e l'offerta emessa. Due modi di dirlo dal vocabolario, e decide Tid:

* **(a) proposta DB: `esito IS NULL`**, cioè nessun verdetto ancora. È la domanda giusta («il cliente ha già
  risposto?») e regge uno stato futuro di attesa senza toccare la regola. Contro: `esito` nasce come proiezione per il
  motore pratiche, e qui gli si dà un secondo lettore;
* **(b) `iniziale OR emissione`**: due colonne che ci sono già, ma descrive gli stati di oggi, non la domanda. Uno
  stato nuovo di attesa andrebbe aggiunto alla regola.

Il giro, se Tid lo apre: un changeSet sulla vista (la stessa colonna, con il suo significato intero, e il COMMENT),
il pgTAP con la marca spostata, e una richiesta FE (due file). Il preventivo non ha questo problema: lì la scadenza
è uno stato (`scadenza`, scritto dal job).

### 6.8 D-SCAD — la scadenza dell'offerta (2026-11-13)

**Decisione (Tid, 2026-11-13): (a)**, `esito IS NULL`. Numero dato da Tid: `20261112-65`.

✅ **Applicato da Tid il 2026-11-13**, con il pgTAP `test-offerta-guard-dal-vocabolario-v1` (plan 15) verde; la pagina
generata della vista è rigenerata.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261112-65` | `vendite.vw_offerte_commerciali_lista.is_scaduta` = `esito IS NULL` **e** la validità passata (`script.fn_data_operativa`, come prima). Stesse colonne, `security_invoker` ripetuto; il COMMENT della vista, una cronaca, è riscritto al presente; `is_scaduta` prende il suo COMMENT di colonna |

`esito` prende un secondo lettore, per la stessa domanda («il cliente ha già risposto?»): scritto nella pagina
`config/stati_doc_offerte`. Pagina `vendite/vw_offerte_commerciali_lista` riscritta sulla regola intera.

**pgTAP.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 12 a plan 15:

* 13: l'emessa con la validità passata è scaduta;
* 14: la rifiutata con la validità passata non lo è;
* 15: con la marca spostata (un esito sullo stato EMESSA), l'emessa non è più scaduta.

**Prova (scratch, 2026-11-13).** I guardrail sono verdi. L'estratto gira per intero in `ROLLBACK` e il catalogo resta
identico. La regressione, senza e con l'estratto, sui 9 pgTAP che leggono la vista più quello esteso:

* 9 uguali;
* il test esteso: 13 ok / 2 not ok senza l'estratto, 15 ok con. I due rossi senza sono i test 14 e 15, cioè il
  difetto: la regola di prima dice «scaduta» anche a un'offerta rifiutata.

**Trovato:** il badge «Scaduta» del **dettaglio** (`OffertaDrawer.vue`) non si accende mai. Legge
`detail.is_scaduta`, che il dettaglio non porta: `offerte_service.get_offerta` legge la sua proiezione
(`_SELECT_COLS_OFFERTA`), non la vista.

**Richieste al team BE/FE (elenco chiuso).** Chi cambia per primo: il DB. Fino al passo FE la lista mostra il badge
come oggi, perché il filtro FE e la regola nuova dicono la stessa cosa sugli stati di oggi.

| Lato | File | Che cosa |
| --- | --- | --- |
| BE | `backend/apps/vendite/db/offerte_repository.py` | il dettaglio porta `is_scaduta` letto da `vendite.vw_offerte_commerciali_lista` (la sede della regola), non ricalcolato |
| FE | `frontend/src/vendite/offerte/components/OfferteSearchTable.vue` | il badge legge `data.is_scaduta` da solo, senza `STATI_OFFERTA_SEGNALA_SCADENZA` |
| FE | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | il badge legge `detail.is_scaduta` da solo |
| FE | `frontend/src/vendite/offerte/constants.js` | ritira `STATI_OFFERTA_SEGNALA_SCADENZA` e il commento in testa che la giustifica |


### 6.9 Trovati dalla verifica BE/FE dei giri 2 e D-SCAD (2026-11-14) — richieste al team DB

Le richieste del §6.7 e del §6.8 sono fatte sul branch `dev/backend-tid` (non committate al 2026-11-14), con i test
sul DB vero verdi. La verifica ha trovato due punti che si chiudono **solo nel DB**. Il BE/FE non mette un ripiego
nell'attesa.

* **V-1. `is_scaduta` del dettaglio costa la vista intera.** Il dettaglio legge il flag con una sottoquery
  correlata su `vendite.vw_offerte_commerciali_lista` (`_SELECT_COLS_OFFERTA`). Il piano su dbdev (2026-11-14,
  `EXPLAIN`) mostra che, per un solo booleano, la vista esegue la `LATERAL pratiche.fn_pratica_del_documento`, la
  sottoquery di `config.sorgenti` e rifà la RLS dell'offerta: il planner non scarta una funzione in `LATERAL`. Il
  risultato è giusto, ma il costo del dettaglio dipende da colonne che non legge. **Richiesta:** la regola ha una
  sede che si legge da sola, per esempio `vendite.fn_offerta_scaduta(offerta_id)` (o la chiave nella capability
  `fn_available_actions_offerta`), e la vista la compone. Il BE allora la legge da lì, in un solo punto.
* **V-2. «In bozza» nel drawer è ancora un codice.** `OffertaDrawer.vue` decide il lucchetto di corpo
  (`isWorkflowLocked`) con `stato !== STATO_OFFERTA.BOZZA`. È la stessa domanda che la capability ora legge da
  `iniziale` (S-2), e che il FE non può chiedere, perché la capability espone `stato_terminale` ma non «stato
  iniziale». Il commento del drawer dice che il lucchetto «sullo stato» è lo stesso nei cinque drawer gemelli
  (righe, utility, indirizzi). **Richiesta:** la chiave `stato_iniziale` (colonna `iniziale` del vocabolario)
  accanto a `stato_terminale`, nella capability dell'offerta e, giro per giro, in quelle degli altri documenti. Poi
  una richiesta FE: il lucchetto legge la chiave e non il codice.

Fuori dal DB, lato BE: il permesso della rotta `registra-esito` (`PassaggioDocumento`, campo `esito`) cercava la riga
della matrice con la **parola dell'API** (`ACCETTATA` / `RIFIUTATA`), mentre il verbo scrive lo stato del vocabolario
(`accettazione` / `rifiuto`). ✅ **Deciso da Tid il 2026-11-14 (opzione A) e fatto**: `PassaggioDocumento` prende
`stato_del_campo`, la mappa parola → ruolo (`offerte_service.RUOLO_DEGLI_ESITI`, la stessa del routing del service),
e cerca la riga verso lo stato del ruolo letto dal vocabolario. L'API non cambia. Presidi:
`core/tests/api/test_permesso_passaggio.py` (15-18) e `core/tests/test_passaggio_rotte.py` (8, sul DB vero).

⚠️ **Risposta del team DB: §6.10** (2026-11-14). V-1 è scritto; per V-2 la chiave chiesta non serve, e la
verifica ha trovato un difetto del lock (⑨, decisione D-LOCK).

### 6.10 Giro 2-bis — V-1 e V-2 (team DB, 2026-11-14)

Col via di Tid (2026-11-14, «procedi come da proposte»). **V-1 è applicato e verde (Tid, 2026-11-14); V-2 si ferma su
una decisione (D-LOCK).**

#### V-1 — la regola della scadenza ha una sede sua

**Il percorso, censito (2026-11-14).** Lato DB l'unico lettore della regola è la vista della lista: le altre funzioni
dell'offerta che nominano `validita_al` la ricopiano (revisione, contratto), ma non giudicano se è scaduta. Lato BE il
dettaglio (`offerte_repository._SELECT_COLS_OFFERTA`) la legge con una sottoquery sulla vista. Lato FE il drawer e la
lista leggono già il solo flag (§6.8). Il dettaglio è il secondo consumatore: la regola si estrae (regola del 2).

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261113-38` | **nuova** `vendite.fn_offerta_scaduta(p_esito, p_validita_al, p_data_riferimento)`: `esito IS NULL` e la validità passata. Riceve i valori e non l'id (linee-guida-sql §13.8): pura, `IMMUTABLE`, `LANGUAGE sql`, si incorpora. **Non** `STRICT`: l'esito vuoto è il caso normale. La data è un argomento, perché una sottoquery nel corpo impedirebbe l'incorporazione; chi chiama passa `script.fn_data_operativa()` |
| `20_code/vendite/20261113-39` | `vendite.vw_offerte_commerciali_lista.is_scaduta` = `vendite.fn_offerta_scaduta(sdo.esito, o.validita_al, (SELECT script.fn_data_operativa()))`. Stesse colonne, `security_invoker` ripetuto, i due COMMENT rimandano alla funzione. Rollback: il `20261112-65`, verificato uguale al vivo |

Non c'è una chiave nella capability. `is_scaduta` è un fatto del record, non un'azione. Se la capability si rompe, il
dettaglio arriva con il blob vuoto (`capabilities_o_vuoto`): il badge sparirebbe insieme alle azioni.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui due changeSet, con il pgTAP in coda: **18 ok / 0 not ok**;
catalogo identico dopo il `ROLLBACK`. Piano su dbdev come app (funzione in `pg_temp`, transazione annullata): la
funzione si incorpora, e la data operativa resta una `InitPlan`, calcolata una volta. Equivalenza con la vista viva su
dbdev: nessuna differenza. È un fatto datato e non prova la regola: la regola la provano i test 13-16, che i casi li
costruiscono.

**pgTAP.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 15 a plan 18:

* 16: la funzione sui valori: scaduta senza esito e con la validità passata; non con un esito, senza validità, o con
  la validità che scade oggi;
* 17: `IMMUTABLE` e non `STRICT`;
* 18: forma: la vista compone la funzione e non riscrive la regola (presidio sulla **forma**, dichiarato tale).

**Pagine `manual/`.** `vendite/fn_offerta_scaduta` (nuova), `vendite/vw_offerte_commerciali_lista` (la sezione di
`is_scaduta`, e la nota operativa «`is_scaduta` è grezzo», ferma a prima di D-SCAD), `config/stati_doc_offerte`. La doc
auto-generata non è rigenerata.

**Richiesta al team BE (elenco chiuso), dopo l'apply di `-38` e `-39`:**

| # | File | Che cosa |
| --- | --- | --- |
| BE-V1 | `backend/apps/vendite/db/offerte_repository.py` | in `_SELECT_COLS_OFFERTA` la sottoquery su `vendite.vw_offerte_commerciali_lista` diventa `vendite.fn_offerta_scaduta(sd.esito, o.validita_al, script.fn_data_operativa()) AS is_scaduta` (`sd` è già `config.stati_doc_offerte`); il commento in testa alla proiezione (righe 144-147) e quello sopra la colonna rimandano alla funzione, non alla vista |
| BE-V1b | `docs/it/backend/vendite/manual/api_offerte.md` | se cita la vista come sede di `is_scaduta` del dettaglio, la sede è la funzione |

Il contratto dell'API non cambia; il FE non ha niente da fare.

#### V-2 — il lucchetto del corpo: la domanda c'è già, ma ha due risposte

**La domanda del FE è «il corpo si modifica?», non «lo stato è l'iniziale?».** Per l'offerta la capability la risponde
già, sezione per sezione: `can_edit_eccezioni` (le righe dell'offerta sono `vendite.offerte_commerciali_eccezioni`),
`can_edit_utility`, `can_edit_indirizzi`, e `non_editable_fields` per la testata. Una chiave `stato_iniziale`, o una
`can_edit_righe` come quella di ordine e DDT, darebbe un secondo nome alla risposta che `can_edit_eccezioni` dà già.
⚠️ Questo **corregge la proposta del DB** fatta in chat il 2026-11-14 (`can_edit_righe`), e la richiesta V-2 del §6.9
(`stato_iniziale`).

**Il difetto trovato (⑨, nuovo: non è nel censimento del §4).** Le chiavi della capability e il trigger che ferma la
riga rispondono da due sedi diverse:

* `can_edit_eccezioni` = la colonna `iniziale` dello stato (giro 2, `20261112-62`);
* `can_edit_utility` e `can_edit_indirizzi` = `script.fn_doc_riga_modificabile`, che legge il montaggio del lock;
* il lock (`vendite.trgfn_doc_righe_lock_fuori_bozza`, `vendite.trgfn_doc_testata_lock_fuori_bozza`) riconosce la
  bozza dal **codice** scritto negli argomenti del trigger: la regola di `script.fn_doc_lock_regola` porta
  `stato_bozza = 'BOZZA'`, e `script.fn_doc_lock_colonna_bloccata` confronta `p_stato = stato_bozza`.

Con il vocabolario del seed le tre risposte coincidono. Con la marca spostata (test 10: `iniziale` su EMESSA) si
separano: la capability dice «modificabile» su un'offerta emessa, e il trigger rifiuta la riga. È la «terza via» di
linee-guida-sql §12.1: un'azione proposta che il guard rifiuta. Sul modello il caso esiste: `iniziale` è una colonna
del vocabolario, e il vocabolario si cambia.

⚠️ **Revoca un giudizio del giro 2.** Il §6.5 (2026-11-13) diceva che i building block del lucchetto «ragionano per codice
nel loro montaggio: non sono una copia del significato». Lo sono: `stato_bozza` dice lo stesso significato della colonna
`iniziale`, con un codice. Era un giudizio del team DB, non una decisione di Tid.

**Il perimetro (struttura, letta da `pg_trigger` su dbdev il 2026-11-14):** il lock è montato su **tutti e sette i
documenti di vendita**: offerta (`BOZZA`); preventivo, ordine, contratto, DDT, reso (`DRAFT`). Sono 28 tabelle tra
testate, righe, componenti, indirizzi e satelliti. È un tema di famiglia: tocca il fermo dei temi trasversali sui
documenti di vendita (PROJECT_CONTEXT), ed è ammesso perché poggia sul vocabolario, come il resto del brief.

**D-LOCK — da decidere (Tid).**

* **(a) Proposta DB.** Il building block del lock riconosce la bozza dalla colonna `iniziale` del vocabolario del
  documento, non dall'argomento `stato_bozza`. Il vocabolario si trova dal documento, come fa
  `script.fn_doc_stato_iniziale_id`. Poi la capability legge il lock in ogni sezione: `can_edit_eccezioni` da
  `script.fn_doc_riga_modificabile`, come utility e indirizzi, e la sede resta una. È un giro a sé, sui sette
  documenti. Va dentro S-2, che ha già preso la famiglia (Tid, 2026-11-08). ⚠️ Gli argomenti dei trigger non si toccano
  (linee-guida-sql §11.5, se il montaggio nasce da `ci_apply`): `stato_bozza` si ritira dalla **lettura**, e il suo
  ritiro dal montaggio è un passo che va censito a parte.
* **(b)** Solo la capability, subito: `can_edit_eccezioni` legge il lock (specchia il guard, §12.2 punto 1), e il lock
  resta sul codice fino al giro di (a). Il test 10 cambia significato: con `iniziale` spostata, la riga resta chiusa
  come il trigger. Chiude la divergenza capability/trigger sull'offerta, ma lascia il significato scritto per codice
  in 28 montaggi.

**La richiesta al FE non aspetta D-LOCK.** Le chiavi ci sono già, e la loro sede si corregge sotto, senza che il FE
cambi di nuovo:

| # | File | Che cosa |
| --- | --- | --- |
| FE-V2 | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | `isWorkflowLocked` non confronta `stato` con `STATO_OFFERTA.BOZZA`: ogni sezione si chiude dalla sua chiave della capability (`can_edit_eccezioni` per le righe, `can_edit_utility`, `can_edit_indirizzi`; la testata ha già `non_editable_fields`). Con la capability vuota il corpo resta chiuso (fail-closed, come `useTestataDocumento`). Il banner `banner_locked_post_bozza` si accende quando una sezione è chiusa |
| FE-V2b | i drawer gemelli che il commento del drawer nomina (righe, utility, indirizzi) | lo stesso, ciascuno con la chiave della sua sezione |

⚠️ `STATO_OFFERTA.BOZZA` può avere altri lettori nel FE: il censimento lo fa il team FE.

### 6.11 D-LOCK (a) — il lock riconosce la bozza dal vocabolario (team DB, 2026-11-14)

**Decisione (Tid, 2026-11-14): (a).** Questa sezione chiude anche V-2 dal lato DB.

**La correzione sta in un punto solo.** Tutti i lettori del lock passano da una sola grammatica,
`script.fn_doc_lock_regola`: i due trigger, `script.fn_doc_lock_montaggi`, e da lì `fn_doc_riga_modificabile`,
`fn_doc_colonna_modificabile`, `fn_doc_testata_in_stato` e le capability dei sette documenti. La regola calcola
`stato_bozza` dal vocabolario del documento, e tutti la seguono senza cambiare. L'argomento dello stato bozza resta
nella grammatica, nella sua posizione, e non si legge: i 28 montaggi restano com'erano. Con il seed lo stato iniziale di
ogni vocabolario è il codice che il montaggio scrive (preventivi, contratti, ordini, DDT, reso `DRAFT`; offerte `BOZZA`;
dbdev, 2026-11-14), quindi il comportamento di oggi non cambia.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261113-40` | `script.fn_doc_lock_regola`: `stato_bozza` = il codice dello stato iniziale (tipo documento → `config.sorgenti.target_table` → `script.fn_doc_stato_modello` → `script.fn_stato_iniziale_id`). Un tipo documento che non porta a uno stato iniziale è un montaggio sbagliato (`errore`, sollevato dal chiamante con `E_DOC_RIGHE_LOCK_MONTAGGIO`). COMMENT riscritto al presente |
| `20_code/script/20261113-41` | `script.fn_available_actions_offerta`: `can_edit_eccezioni` = `script.fn_doc_riga_modificabile('vendite.offerte_commerciali_eccezioni', stato)`, come utility e indirizzi |

Fuori dal difetto: `vendite.trgfn_doc_guard_delete_solo_bozza` legge già lo stato iniziale dal vocabolario. Solo la mail
(`config.email_outbox`) dice `DRAFT`, perché non ha un vocabolario.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui due changeSet, con ognuno dei **48** pgTAP che nominano il
lock o la capability dell'offerta. Tre fissavano il contratto vecchio e sono stati riportati al modello:

| pgTAP | Che cosa cambia |
| --- | --- |
| `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` (21) | provava «lo stato bozza è parametrico» (`TG_ARGV[2]` = EMESSO). Ora prova il contrario: l'argomento non si legge, e la riga passa sul DDT in bozza e non su quello emesso. Rosso senza l'estratto, verde con |
| `vendite/test-doc-emittente-utility-fermi-v1` (1-3) | la grammatica con un tipo documento finto (`'X'`). Ora usa `PREVENTIVO`, e la decisione «in bozza» si chiede con lo `stato_bozza` della regola |
| `vendite/test-testata-dopo-emissione-rdb-v1` (1) | il tipo documento finto `'DDT'` diventa `DDT_VENDITA` |

Esito con l'estratto: tutti verdi, tranne `vendite/test-esecutivi-ba-coppia-v1`, con un rosso che c'era già senza
l'estratto (fuori da questo cantiere). Catalogo identico dopo ogni `ROLLBACK`.

**pgTAP nuovi.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 18 a plan 23. Senza l'estratto 4 test
sono rossi, con l'estratto 23 su 23:

* 19: contrasto. Con lo stato iniziale su BOZZA, l'indirizzo dell'offerta emessa non si toglie
  (`E_DOC_DATI_COLLEGATI_NON_BOZZA`), e la capability lo dice;
* 20: ⭐ marca spostata. Con `iniziale` su EMESSA il lock legge EMESSA come bozza;
* 21: … l'indirizzo dell'offerta in BOZZA non si toglie più;
* 22: … quello dell'offerta emessa sì, e la capability lo proponeva;
* 23: … ed è tolto davvero.

**Pagine `manual/`.** `script/fn_doc_lock_regola`, `vendite/trgfn_doc_righe_lock_fuori_bozza`,
`vendite/trgfn_doc_testata_lock_fuori_bozza`, `script/fn_available_actions_offerta`.

**Debito residuo, dichiarato.** I 28 montaggi portano ancora l'argomento dello stato bozza, che non si legge. Toglierlo
vuol dire cambiare la grammatica (per la testata è un argomento posizionale obbligatorio) e rimontare 28 trigger. Non è
una seconda verità, perché nessuno lo legge, ma è rumore nel montaggio. Si toglie quando un giro rimonta quei trigger per
un'altra ragione; nel frattempo la pagina di `fn_doc_lock_regola` dice che non si legge.

**Ricadute BE/FE.** Nessuna nuova: il contratto della capability non cambia, e FE-V2 (§6.10) vale com'è.

### 6.12 Giro 3 — `terminale`, bolla e reso (team DB, 2026-11-14)

Col via di Tid (2026-11-14, «procedi anche con tutti gli altri giri»). Chiude ④, ⑦, S-4, S-5 e S-3 per il reso.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261113-42` | ⑦ e S-3: `esito` (FK verso `config.esiti_flussi_pratiche`) e `terminale` (CHECK verso `fase` CHIUSO) su `config.stati_doc_ddt` e `config.stati_doc_reso`; `emissione` su `config.stati_doc_reso` (indice unico parziale, CHECK attivo). COMMENT al presente |
| `00_schema/config/20261113-43` | ④ a: il COMMENT di `terminale` su offerte, ordini, preventivi, contratti, versioni di listino: nessun passaggio **a mano** in uscita (S-1, A), implicazione e non equivalenza (S-4) |
| `20_code/config/20261113-44` | il guard del verdetto (`config.trgfn_stati_doc_guard_esito_verdetto`) montato su bolla e reso |
| `20_code/script/20261113-45` | **nuova** `script.fn_doc_terminali_con_uscita_manuale(testata)`: le coppie (stato terminale, destinazione a mano) della configurazione |
| `20_code/script/20261113-46` | ④ b: **nuovo** building block `script.trgfn_doc_terminale_senza_uscita_manuale`, `CONSTRAINT TRIGGER` differito su sette vocabolari e sette matrici (14 montaggi, la testata come argomento); codice nuovo `E_DOC_TERMINALE_CON_USCITA_MANUALE` |
| `20_code/vendite/20261113-47` | ⑦: `vendite.vw_stato_sorgente_ddt` e `_reso` passano `esito` e `terminale` del vocabolario, non li calcolano da `fase` |
| `20_code/vendite/20261113-48` | S-3: `vendite.trgfn_resi_gen_numero` numera nello stato di `emissione`, non nel codice CONFERMATO |
| `20_code/script/20261113-49` | S-3, e la gemella della bolla trovata al §5: `script.vw_stati_doc_reso_merce_rientrata` e `script.vw_stati_doc_ddt_merce_partita` contano dallo stato di `emissione`, non da `'CONFERMATO'` ed `'EMESSO'` |
| `80_data/changelog/20261113-50` | il mirror della bolla ri-applicato dopo il seed degli esiti (`20260701-04`): `esito` ha una FK, e il mirror del `20250915-01` lo salta (`type: SKIP`). linee-guida-sql §11.2 |

**I dati (80_data).** CSV `stati_doc_ddt` (`esito`, `terminale`) e `stati_doc_reso` (`esito`, `terminale`, `emissione`), con
le colonne dichiarate nei due mirror. Sono i valori che la vista calcolava, tranne **S-5**: il reso CONFERMATO ha
`terminale` = false, `esito` POSITIVO, `fase` CHIUSO, ed è lo stato di `emissione`. Il codice nuovo è in coda a
`codici_errore.csv` e `messaggi_errore.csv` (id 1483). I CSV sono riscritti con `csv.writer` e `\n`: nessun CR.

**Il seed rispetta A** (dbdev, 2026-11-14, sulla configurazione): nessuno stato terminale ha un passaggio a mano in
uscita, tranne il reso CONFERMATO, che S-5 rende non terminale nello stesso giro. Il trigger nuovo è differito: da zero
i mirror lo attraversano a transazione finita. I changeSet storici di `80_data` che scrivono quelle tabelle toccano
`esito` e `meta`, non `terminale` né le uscite a mano.

**Il reso «non si emetteva».** Due pgTAP fissavano «reso, commessa e fattura non si emettono»: S-3 (Tid, 2026-11-08) dà al
reso la sua emissione. Sono stati riportati al modello: `script/test-doc-lettori-stato-e-preventivo-al-modello-v1`
(test 6-8) e `script/test-doc-stato-codice-v1` (test 2-3). Nessun lettore BE legge l'emissione del reso (i
`stato_di_emissione` del backend sono di preventivo, offerta, contratto, ordine e bolla), e nel DB
`script.fn_doc_azione_passaggio` non ha chiamanti: aggiungere `emissione` al reso non cambia nessun percorso.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui changeSet di `00_schema` e `20_code`, più un changeSet di
scratch che simula i due CSV e le righe del codice d'errore: il loader `loadUpdateData` non lo prova nessuno strumento,
e il token `NULL` è già misurato (§11.2). Esito con l'estratto, sui **129** pgTAP che nominano gli oggetti del giro:

* `config/test-terminale-senza-uscita-manuale-v1` (**nuovo**, plan 10): 10 su 10 (senza l'estratto, interrotto);
* `vendite/test-vw-stato-sorgente-ddt-reso-v1` (adeguato, plan 14): 14 su 14. Il test 7 cambia con S-5 (reso confermato
  non terminale); il nuovo test 14 sposta le marche (`esito` su EMESSO, `terminale` su CONSEGNATO) e la vista le segue;
* i due test dell'emissione del reso, riportati al modello: verdi;
* gli altri: invariati. I rossi che restano c'erano già senza l'estratto, e sono rossi da owner per costruzione
  (`test-doc-lettori-…` 23, `test-esecutivi-ba-coppia-v1`, `test-doc-verbo-comune-e-porta-v1`,
  `test-fn-available-actions-ddt-reason-catch-all-v1`);
* `vendite/test-documenti-numerazione-trasloco-v1` **non** l'ho fatto girare: non è transazionale (comincia con un
  `DO`), e lo strumento non lo lancia. Numera il reso alla conferma (test 8-9): con il seed lo stato di emissione è
  CONFERMATO, quindi deve restare verde. **Lo lancia Tid.**

**pgTAP nuovo** `config/test-terminale-senza-uscita-manuale-v1`, sulla matrice vera del reso, in transazione:

1. una riga a mano attiva ANNULLATO → DRAFT: rifiutata;
2. la stessa di processo: ammessa;
3. diventare a mano (`UPDATE` del solo `meta`): rifiutata;
4. spenta, e a mano: ammessa;
5. riaccesa (`UPDATE` del solo `attivo`): rifiutata;
6. `terminale` = true sul reso CONFERMATO, che ha l'annullo a mano: rifiutato;
7. la configurazione dei sette documenti: nessuna coppia (il seed di catalogo, non una popolazione);
8. forma: 14 montaggi differiti, per funzione e argomento;
9. la fattura, che non ha `terminale`: `E_SCRIPT_CHIAMATA_NON_VALIDA`;
10. il lettore rilegge: l'offerta SUPERATA è terminale, e annullata la revisione torna EMESSA e non lo è più.

**Pagine `manual/`.** `config/stati_doc_ddt`, `config/stati_doc_reso`, `config/stati_doc_listino_versioni`,
`vendite/vw_stato_sorgente_ddt`, `vendite/vw_stato_sorgente_reso`, `vendite/trgfn_resi_gen_numero`,
`script/vw_stati_doc_ddt_merce_partita`, `script/fn_doc_terminali_con_uscita_manuale` (nuova, anche per il trigger).

**Ricadute BE/FE (elenco chiuso).** Nessuna di comportamento: le viste espongono le stesse colonne, e il BE e il FE leggono
`doc_esito` e `doc_terminale` come prima. Cambia un valore: il reso confermato non è più terminale nel percorso della
pratica (`PraticaPercorso.vue` mostra il Tag dello stato finché il documento non è terminale: è il comportamento voluto
da S-5). Il codice d'errore nuovo lo solleva solo chi scrive la configurazione: niente nella tassonomia di `api.md`.
⚠️ *Corretto il 2026-11-14 (segnalazione del BE):* la frase sopra bastava per la tassonomia, non per l'elenco.
`backend/apps/core/services/error_policies_generated.py` ricopia **tutto** il catalogo, quindi ogni codice nuovo in
`codici_errore.csv` vuole la rigenerazione, chiunque lo sollevi. Le richieste sono due:

| # | File | Che cosa |
| --- | --- | --- |
| BE-T1 | `docs/it/backend/pratiche/manual/api_percorso.md:121` | `doc_terminale` non vuol dire «il documento non evolverà più»: vuol dire «da questo stato non esce nessun passaggio a mano; il sistema può ancora spostarlo» (S-1, A) |
| BE-T2 | `backend/apps/core/services/error_policies_generated.py` | rigenerare (`manage.py genera_error_policies`): entra `E_DOC_TERMINALE_CON_USCITA_MANUALE` (`DATO_ERRATO`, id 1483). Va bene nello stesso giro della rigenerazione chiesta dal cantiere dei template (`20261114-01 … -04`) |

#### ⑩ Trovato dal giro 4: ANNULLATA della fattura — ✅ deciso da Tid il 2026-11-14 (a), fatto nel §6.13

Il presidio della raggiungibilità (giro 4, §6.13) trova, oltre agli stati attesi, un caso che il censimento del §4 non
aveva visto. In `config.stati_doc_fiscale` lo stato ANNULLATA ha `applica_fattura` = true, ma nessuna riga della matrice
porta una **fattura** in ANNULLATA: l'unica entrata è DRAFT → ANNULLATA, che vale solo per il lotto (`solo_lotto`). Con il
modello di oggi una fattura pre-fiscale si cancella (`vendite.fn_elimina_fattura_da_lotto`, e l'annullo del lotto
`vendite.fn_annulla_lotto_da_draft` le elimina), e una fattura numerata si corregge con una nota di credito. Il guard
`vendite.trgfn_fatture_numerata_non_annulabile`, che rifiuta il passaggio in ANNULLATA di una fattura numerata (col
letterale `'ANNULLATA'`), protegge quindi un passaggio che la matrice non ammette.

È la stessa forma di R-3 (il vocabolario dice di più della matrice). **D-ANN, proposta DB:** `applica_fattura` = false su
ANNULLATA, dal CSV. Il guard `trgfn_fatture_numerata_non_annulabile` resta a presidio di una strada che la matrice
chiude: si ritira solo se nessuno scrive lo stato della fattura fuori dalla matrice, e il censimento di chi la scrive va
fatto prima. In alternativa (b): una riga di matrice DRAFT → ANNULLATA per la fattura, se l'annullo di una fattura
pre-fiscale deve esistere come stato e non come cancellazione.

**Deciso (Tid, 2026-11-14): (a).** `applica_fattura` = false su ANNULLATA, dal CSV (§6.13). Il guard
`trgfn_fatture_numerata_non_annulabile` resta: il censimento di chi scrive lo stato della fattura fuori dalla matrice non
è fatto, e finché non lo è il guard è una rete.

### 6.13 Giro 4 — gli stati che nessun passaggio raggiunge (team DB, 2026-11-14)

Col via di Tid (2026-11-14). Chiude ⑤, S-8 e R-3.

| ChangeSet / file | Che cosa |
| --- | --- |
| `80_data/changelog/20261114-03` | S-8: `DELETE` di ALLOCATO, SPEDITO, CONSEGNATO e FATTURATO da `config.stati_doc_ordini`, forward-only (linee-guida-sql §11.2: `loadUpdateData` non cancella). Nessuna riga della matrice li nomina e nessun documento, di vendita o d'acquisto, li porta (dbdev, 2026-11-14): se un database ne avesse, la FK ferma il `DELETE` e lo dice |
| CSV `stati_doc_ordini` | le quattro righe escono |
| CSV `stati_doc_fiscale` | R-3: `applica_lotto` = false su REGISTRATA; D-ANN (a): `applica_fattura` = false su ANNULLATA |

⚠️ **Numero.** Lavora un'altra sessione DB sullo stesso albero (i template dei documenti, `20261114-01`, `-02`). Il
`20261114-03` l'ha dato `scripts/prossimo_changeset.py` ed è stato occupato subito. Per i giri 5 e 6 il range lo dà
Tid.

**Fuori, di proposito.** La «cintura» FATTURATO di `vendite.fn_list_ordini_da_pushare` (`NOT IN ('DRAFT', 'ANNULLATO',
'FATTURATO')`): un codice che non esiste più non nomina niente, e la funzione si riapre nel giro dell'ordine (giro 6),
dove anche DRAFT e ANNULLATO escono dal letterale. Così si apre una volta sola. `vendite.ordini.fatturazione_trigger` è un
altro asse, che riusa i nomi: non c'entra.

**pgTAP nuovo** `config/test-stati-raggiungibili-v1` (plan 5). È un presidio sulla **forma** della configurazione (il seed
di catalogo), dichiarato tale:

1. per le dieci testate della mappa `script.fn_doc_stato_modello`, ogni stato attivo si raggiunge dallo stato iniziale
   lungo righe attive della matrice, col filtro della mappa; per fattura e lotto contano gli stati che valgono per loro
   (`applica_fattura`, `applica_lotto`). Nessuna eccezione: ANNULLATA della fattura (⑩) l'ha chiusa D-ANN;
2. controesempio costruito: uno stato attivo nuovo del reso, senza entrate, è trovato;
3. controesempio costruito: spenta l'unica riga che entra nel reso CONFERMATO, lo stato è trovato;
4. S-8: i quattro stati non ci sono più;
5. R-3 e D-ANN: REGISTRATA vale solo per la fattura, ANNULLATA solo per il lotto.

Senza l'estratto 1, 4 e 5 sono rossi; con l'estratto 5 su 5.

**La prova (2026-11-14).** Il `DELETE` estratto, più un changeSet di scratch che simula il CSV fiscale (R-3), con ognuno
dei **127** pgTAP che nominano i quattro stati, REGISTRATA, `applica_lotto` o i due vocabolari: 122 verdi, e un rosso nuovo atteso, riportato al modello: `pratiche/test-proiezione-stato-sorgente` (test 19, la mappa D1 dei nove stati d'ordine), ora sui cinque stati e col codice nel confronto, non per posizione: 31 su 31. Gli altri sono interruzioni presenti anche senza l'estratto (`script/test-vw-giornale-entita`; i due test dell'emissione del reso del §6.12, che vogliono le colonne del giro 3). `vendite/test-fn-list-ordini-da-pushare-v1` non è transazionale (manca il `ROLLBACK`) e lo strumento non lo lancia: **lo lancia Tid**.

pgTAP adeguato: `pratiche/test-proiezione-stato-sorgente` (19).

**D-ANN (a), la prova (2026-11-14).** Con il CSV fiscale simulato (R-3 e D-ANN), sui **73** pgTAP che nominano il vocabolario fiscale, `applica_fattura` o il guard della fattura numerata: 72 verdi, e `script/test-vw-giornale-entita`, interrotto anche senza l'estratto. Il presidio della raggiungibilità passa senza eccezioni. L'unico lettore che cambia risposta è `config.fn_get_stati_doc_fiscale('FATTURA')`, che non elenca più ANNULLATA fra gli stati della fattura; il backend non lo chiama. Pagina `config/stati_doc_fiscale` aggiornata.

**Pagine.** `config/stati_doc_ordini` (le righe dei quattro stati e la nota «restano attivi»), guida
`gestione-ordini` (la riga «⏳ non ancora raggiunti»).

**Richieste al team FE (elenco chiuso, dal §4.4 corretto al §5):**

| # | File | Che cosa |
| --- | --- | --- |
| FE-S8a | `frontend/src/vendite/ordini/constants.js` | via `STATO_ORDINE.ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO` (nessun lettore) |
| FE-S8b | `frontend/src/locales/it.json`, `en.json` | via `vendite.ordini.stato_info.fatturato` |
| FE-S8c | `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue`, `frontend/src/vendite/components/CommessaGestioneDrawer.vue`, `frontend/src/vendite/components/ContrattoDrawer.vue`, `frontend/src/vendite/ordini/components/OrdiniDrawer.vue`, `frontend/src/vendite/ddt/components/DdtDrawer.vue`, `frontend/src/vendite/resi/components/ResoDrawer.vue` | i commenti che citano `ALLOCATO` come esempio di descrizione: l'esempio è uno stato che non c'è più |

BE: nessuna (nessun riferimento fuori dai test).

### 6.14 Giro 5 — il listino, i COMMENT stantii, `in_gioco` (team DB, 2026-11-14)

Col via di Tid (2026-11-14), numeri dal primo libero: il `-04` lo aveva preso l'altra sessione, si parte dal `-05`. Chiude
⑧, S-9, i COMMENT del §2 (§4.8) e R-2. ✅ **Applicato da Tid il 2026-11-14**, pgTAP verdi.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261114-05` | ⚠️ Il primo apply (2026-11-14) si è fermato sulla `preCondition`: `indexExists` con il solo schema non trova l'indice su PostgreSQL. Il changeSet non era applicato: la `preCondition` diventa un `sqlCheck` sul catalogo, come in `20260703-05`. ⑧: l'indice `ux_stati_doc_listino_versioni_iniziale` diventa `uq_stati_doc_listino_versioni_iniziale`, il nome degli altri vocabolari. Nessun corpo, vincolo o pgTAP lo nominava. S-9: la versione di listino non prende `fase` |
| `00_schema/config/20261114-06` | §4.8: sedici COMMENT al presente, letti contro il catalogo di dbdev: `config.stati_doc_offerte` (mancavano accettazione e rifiuto), la sua matrice («5 transizioni»: sono sette, due di processo), `config.stati_doc_reso` e la sua `meta` (`fase` era «in meta.fase»), `ordine` e `is_superato` dell'offerta, `codice` di contratti, bolla e ordini (stati che non ci sono), `stati_doc_fiscale.fase`, `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più), `emissione` dei cinque vocabolari («Emetti produce numero e PDF»: vero solo per la bolla; gli altri hanno il numero dalla nascita) |
| `20_code/vendite/20261114-07` | R-2: i tre lettori di `in_gioco` passano a `pre_fiscale` (`script.fn_check_attivita_riportabile_da_emettere`, dove l'alias diventa `marchio_pre_fiscale`; `vendite.vw_documenti_trattenuti_da_lotto`; `vendite.vw_dash_competenza_attivita`), e `vendite.vw_lotti_fase` perde la colonna. `CREATE OR REPLACE VIEW` non toglie colonne: la vista e le sue **otto** dipendenti (catena da `pg_depend`) si tolgono dalla cima senza `CASCADE` e si ricreano dalla base, con `security_invoker` e i COMMENT, anche di colonna. I privilegi li danno i default dello schema per `zeroerp_owner`. I COMMENT che spiegavano `in_gioco` sono al presente |

**La prova (2026-11-14).** I tre changeSet, con ognuno dei **31** pgTAP che nominano le nove viste, la funzione,
l'indice o la postura `security_invoker`: tutti verdi. Una prova di scratch conferma che le nove viste ricreate hanno
`SELECT` per `zeroerp_app`, `security_invoker` e il COMMENT. Catalogo identico dopo ogni `ROLLBACK`.

**pgTAP adeguati.** `vendite/test-vw-lotti-fase-v1`: il test 1 (il contratto della vista) senza `in_gioco`; il test 5 ora
presidia, sulla forma, che nessuna vista e nessuna funzione lo legga più. Rosso senza l'estratto, verde con.
`vendite/test-motivo-non-fatturata-v1` (la fixture separa i due lotti su `pre_fiscale`) e
`vendite/test-documento-trattenuto-da-lotto-v1` (un commento).

**Pagine.** `vendite/vw_lotti_fase` (lo stato che non si risolve: non succede più, la vista lo difende lo stesso),
`script/fn_check_attivita_riportabile_da_emettere`. La doc auto-generata non è rigenerata.

**Ricadute BE/FE.** Nessuna: il BE legge `pre_fiscale` dal 2026-11-13 (`e174a302e2`); nel test Django restano solo i
commenti che raccontano il ritiro.

**Trovato per il giro 6.** Il contratto copia `is_draft_snapshot` da `config.stati_doc_contratti.is_bozza`
(montaggio di `vendite.trgfn_doc_snapshot_da_stato`), una colonna che dice la stessa cosa di `iniziale`: è una copia del
significato, della famiglia di S-2. Entra nel giro del contratto.

### 6.15 Giro 6 — il censimento (team DB, 2026-11-14)

**Il perimetro.** Il testo delle funzioni (commenti tolti) e delle viste degli schemi applicativi, contro i codici dei
sei vocabolari del giro (preventivo, ordine, contratto, bolla, reso, versione di listino), sul catalogo di dbdev il
2026-11-14: 104 oggetti nominano almeno un codice. Molti sono falsi positivi: lo stesso codice vive in vocabolari
diversi (BOZZA e CHIUSA di commesse, pratiche, template dei documenti; DRAFT dei documenti interni di magazzino e della
mail; ATTIVO delle automazioni, delle vesti, dei dispositivi). Tolti quelli, restano **circa 55 oggetti**.

**La regola per classificarli** (S-2 e S-3, Tid 2026-11-08):

* un codice usato **per il suo significato** (in bozza, emesso, accettato, annullato, terminale) si legge dalla colonna
  del vocabolario: è S-2;
* un codice che nomina **la destinazione di un processo** (EVASO, PARZIALMENTE_EVASO, SPEDITO, CONSEGNATO, RESO della
  bolla, ATTIVA e CHIUSA del listino) resta, attraverso `script.fn_doc_stato_id`: il processo nomina la sua
  destinazione come la nomina la riga della matrice;
* un codice di **un altro asse** che riusa i nomi (`vendite.ordini.fatturazione_trigger`: CONFERMATO, SPEDITO,
  CONSEGNATO) non è uno stato e non si tocca.

**Gli oggetti, per documento** (da classificare uno per uno sul corpo vivo):

| Documento | Oggetti |
| --- | --- |
| preventivo | `script.fn_available_actions_preventivo`, `vendite.fn_crea_revisione_preventivo`, `vendite.fn_preventivo_proietta_stato_smistamento`, `vendite.trgfn_preventivi_guard_annullamento`, `vendite.trgfn_preventivi_guard_transizione`, `vendite.vw_dash_fatturazione_preventivi` |
| ordine | `script.fn_available_actions_ordine`, `vendite.fn_list_ordini_da_pushare` (con la «cintura» FATTURATO del §6.13), `vendite.fn_ordine_proietta_stato_evasione`, `vendite.fn_situazione_merce_ordine`, `vendite.fn_genera_ddt_da_ordine`, `vendite.trgfn_ordini_guard_transizione`, `vendite.trgfn_ordini_normalize`, `vendite.vw_dash_fatturazione_ordini` |
| contratto | `script.fn_available_actions_contratto`, `vendite.fn_get_contratto_attivo`, `vendite.trgfn_contratti_freeze_listino_versione`, `vendite.trgfn_contratti_guard_transizione_stato`, `vendite.trgfn_contratti_set_categoria_cliente_snapshot`; lo snapshot `is_draft_snapshot` da `is_bozza` (§6.14) |
| bolla | `script.fn_available_actions_ddt` (`can_edit_righe = DRAFT`), `script.fn_check_ddt_emittibile`, `script.fn_check_ddt_riga_correggi_qta_evasa`, `vendite.fn_annulla_ddt`, `vendite.fn_cambia_stato_ddt`, `vendite.fn_ddt_push_diagnosi`, `vendite.trgfn_ddt_gen_numero_emesso`, `vendite.trgfn_ddt_guard_causale_emissione`, `vendite.trgfn_ddt_guard_indirizzi_obbligatori`, `vendite.trgfn_ddt_guard_transizione`, `vendite.trgfn_ddt_guard_transizione_approvazione`, `vendite.trgfn_ddt_riga_legame_guard`, `vendite.vw_dash_fatturazione_ddt`, `dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo` |
| reso | `script.fn_available_actions_reso`, `script.fn_check_reso_merce`, `vendite.fn_conferma_reso`, `vendite.fn_annulla_reso`, `vendite.fn_chiudi_riconsegna_reso`, `vendite.fn_riapri_riconsegna_reso`, `vendite.fn_genera_ddt_riconsegna`, `vendite.trgfn_resi_guard_ddt_consegnato`, `vendite.trgfn_resi_righe_guard_quantita` |
| versione di listino | `vendite.fn_attiva_versione_listino`, `script.fn_check_listino_congelabile`, `script.fn_check_versione_listino_chiudibile`, `script.fn_check_versione_listino_eliminabile`, `vendite.fn_chiudi_versioni_listino_scadute`, `vendite.fn_versioni_listino_da_chiudere`, `vendite.fn_listino_versione_in_vigore`, `vendite.fn_listino_ha_storia`, `vendite.fn_listini_attivi_uom_non_convertibili`, `vendite.fn_prezzi_legame_oltre_la_fine`, `vendite.fn_resolve_prezzo_listino_v2_esito`, `vendite.fn_check_listino_provenienza_emittente`, `vendite.trgfn_listini_kit_guard`, `vendite.trgfn_listini_righe_comp_guard_immutabilita_v5`, `vendite.trgfn_listini_righe_guard_periodicita_quota_fissa`, `vendite.trgfn_listini_righe_guard_stato`, `vendite.trgfn_listini_versioni_guard_per_stato`, `vendite.trgfn_listini_versioni_guard_transizione_stato` |

**L'ordine proposto.** Un documento per giro (6a … 6f), così ogni oggetto si apre una volta sola e ogni giro ha la sua
prova e il suo apply: preventivo, ordine, contratto, bolla, reso, listino. Ogni giro porta il presidio sulla forma
del documento (nessun codice dei suoi stati nei corpi dei suoi lettori di significato), come il test 12 di
`vendite/test-offerta-guard-dal-vocabolario-v1` per l'offerta, e una marca spostata dove il significato lo permette.

### 6.16 Giro 6a — il preventivo (team DB, 2026-11-14)

Col via di Tid ai giri (2026-11-14), numeri dal primo libero (`scripts/prossimo_changeset.py`). Corpi da
`pg_get_functiondef` e `pg_get_viewdef` su dbdev il 2026-11-14, firme ri-ancorate con `%TYPE` come nell'ultima
revisione di ciascuna; ogni rollback porta la definizione e il COMMENT di prima, letti dal catalogo. I COMMENT, che
erano cronache, sono riscritti al presente (§5d).

**Il censimento riaperto.** Il corpo vivo di ogni funzione e vista che legge gli stati del preventivo, commenti tolti,
contro i sette codici: i sei oggetti del §6.15 e tre builder `dbops`. Nessuno mancava. I builder restano fuori:
`fn_pgtap_crea_preventivo` e `fn_pgtap_crea_preventivo_con_righe` ricevono il codice dello stato a cui il test vuole
arrivare (la destinazione la nomina il test), e il ramo `'ANNULLATO'` di `fn_pgtap_porta_a_stato` è del reso (giro 6e).
Restano anche gli stati che i montaggi del lock di testata scrivono per la colonna (`competenza_mese`, `meta`:
`'EMESSO,ACCETTATO'`): sono la configurazione del montaggio, gli stati in cui la colonna resta aperta, come le righe
della matrice.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261114-08` | `vendite.trgfn_preventivi_guard_annullamento`: lo stato di annullo da `is_abortito` della destinazione, non da `'ANNULLATO'`. Il codice resta per il contesto dell'errore |
| `20_code/vendite/20261114-09` | `vendite.trgfn_preventivi_guard_transizione`: la Regola 3 (validità finita, prezzi) scatta su `script.fn_stato_accettazione_id`, come la Regola 2 su `fn_stato_emissione_id`. ⚠️ Il 2026-10-31 (`brief-modello-documento-vendita` §17.2) i letterali dei guard «restavano» come condizione del passaggio; S-2 (2026-11-08) prende la famiglia intera, e il giro 2 l'aveva già fatto per l'offerta |
| `20_code/script/20261114-10` | `script.fn_available_actions_preventivo`: `can_edit_righe` = `script.fn_doc_riga_modificabile('vendite.preventivi_righe', stato)`, come l'offerta dopo D-LOCK. Con il seed la risposta è quella di prima in tutti e sette gli stati (dbdev, 2026-11-14). Il contratto del blob non cambia |
| `20_code/vendite/20261114-11` | `vendite.fn_crea_revisione_preventivo`: «esiste già una revisione in bozza» da `sdp2.iniziale`, non da `'DRAFT'`. È lo stato in cui la revisione nuova nasce (`script.trgfn_doc_stato_iniziale`): con la marca spostata il guard non la vedeva e se ne creava una seconda |
| `20_code/vendite/20261114-12` | `vendite.vw_dash_fatturazione_preventivi`: `DOC_BOZZA` da `iniziale`, `IN_ATTESA_ACCETTAZIONE` da `emissione`, come l'offerta. Le due colonne entrano nel `GROUP BY`; stesse colonne, `security_invoker` ripetuto |
| `20_code/vendite/20261114-13` | **D-PROI** (a). `vendite.fn_preventivo_proietta_stato_smistamento` parte dallo stato di accettazione (la colonna) e ci torna da EVASO; EVASO resta col codice, destinazione del processo |

**D-PROI — la proiezione dello smistamento: decisa (a) da Tid il 2026-11-14, con l'apply di `-13`.** Il 2026-10-31 (§17.2 del brief del modello) la
proiezione «resta: è la proiezione fra due stati nominati, ed EVASO non ha una colonna». La ragione vale per EVASO, non
per ACCETTATO: lo smistamento si apre dallo stato di accettazione del vocabolario (la capability con
`can_push_commessa` e `can_genera_ordine`, `vendite.fn_push_preventivo_a_ordine`, `vendite.fn_list_preventivi_da_pushare`,
tutti dalla colonna dal 2026-10-31). Con la marca spostata il push lavora dal nuovo stato e la proiezione non scatta: il
preventivo smistato per intero non diventa EVASO, e da EVASO torna a ACCETTATO invece che allo stato da cui lo
smistamento si apre. È una revoca parziale di una decisione, quindi la decide Tid.
* **(a) — proposta DB:** applicare `-13`. Partenza e ritorno dalla colonna `accettazione`, EVASO col codice.
* **(b):** lasciare la proiezione com'è; `-13` si ritira dal repo e il test 18 del pgTAP con lui (il 10 cambia in
  `ACCETTATO,EVASO`).

**D-PDF — il PDF delle liste: trovato dal giro 6a, deciso (a) da Tid il 2026-11-14.** Le liste dei preventivi e delle offerte
spengono il PDF con il codice della bozza: `frontend/src/vendite/preventivi/components/PreventiviList.vue`
(`stato_codice_interno === 'DRAFT'`, due righe) e `frontend/src/vendite/offerte/components/OfferteSearchTable.vue`
(`=== 'BOZZA'`; il giro 2 non l'aveva visto). Il drawer legge il PDF dalla capability (`pdf.mode`, da `pdf_mode` del
vocabolario), la lista no, perché le viste lista (`vendite.vw_preventivi_lista`, `vendite.vw_offerte_commerciali_lista`)
non portano `pdf_mode`. È una copia della regola di stampa fuori dal DB (S-10), e probabilmente la stessa forma sta nelle
liste degli altri documenti: è un tema di famiglia, che il fermo allentato ammette perché poggia sul vocabolario.
* **(a) — proposta DB:** ogni giro del suo documento aggiunge `pdf_mode` alla vista lista (colonna in coda, §5f),
  e il FE spegne il PDF dove non è `ARCHIVE`; per l'offerta, un giro 2-ter. Ricadute FE: i file delle liste.
* **(b):** un giro unico per tutte le liste, dopo il 6f.

**Il pgTAP nuovo.** `vendite/test-preventivo-stati-dal-vocabolario-v1` (plan 18): otto contrasti col seed (la riga
dell'emesso non si scrive, i motivi del cruscotto, la seconda revisione, lo smistato EVASO, la strada che manca, la
validità finita che ferma l'accettazione e non il rifiuto, il ritorno da EVASO all'annullo dell'ordine), due presidi sulla forma (i cinque
lettori non nominano i codici; la proiezione nomina il solo EVASO) e otto marche spostate, ognuna rimessa al suo posto
prima della successiva. I casi si costruiscono dalle strade dell'applicazione: i passaggi manuali dal verbo
`vendite.fn_cambia_stato_preventivo` (con l'azione del passaggio concessa all'operatore), EVASO dal push all'ordine, il
ritorno da EVASO dall'annullo dell'ordine (`vendite.fn_annulla_ordine`). ⛔ Mai `script.fn_doc_scrivi_stato` dal test:
la porta vuole il proprietario della tabella, e il runner è `zeroerp_app`. La prima stesura lo faceva, verde sullo
scratch (la prova gira da owner) e rossa su dbdev alla fixture (`E_DOC_STATO_SOLO_DAL_VERBO`): corretta il 2026-11-14,
senza il marcatore `pgtap-runner: owner`, perché quei passaggi l'applicazione li fa. Con `iniziale` su EMESSO la capability e il lock dicono insieme che la riga dell'emesso si
scrive, il cruscotto dà DOC_BOZZA e la revisione dell'emesso trova la bozza in lui; con `emissione` su ACCETTATO il
cruscotto dà IN_ATTESA_ACCETTAZIONE all'accettato; con `is_abortito` su RIFIUTATO il guard dell'annullo parla prima
della matrice; con `accettazione` su RIFIUTATO la Regola 3 ferma il rifiuto dello scaduto; con `accettazione` su EMESSO
(e la riga di processo EVASO → EMESSO, aggiunta dal test) l'annullo dell'ordine riporta il preventivo EVASO a EMESSO. Il caso scaduto usa il fuso
come `vendite/test-preventivo-scadenza-v1`.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi: forme, COMMENT al presente, letterali,
`runOnChange`, preambolo pgTAP. L'estratto dei sei changeSet gira per intero in `ROLLBACK`, catalogo identico dopo.
Regressione con `--pgtap` sui **128** file che nominano gli oggetti toccati, il vocabolario, la tabella o i builder del
preventivo: 127 uguali senza e con l'estratto; il nuovo passa da 9/18 a 18/18. Senza l'estratto è verde il 12, ed è
giusto: è la metà del trigger, che legge lo stato iniziale dal `20261113-40`. Dieci file rossi uguali nelle due corse,
quindi già presenti sullo scratch; per i due che toccano preventivo e capability
(`test-doc-lettori-stato-e-preventivo-al-modello-v1`, il test 23 «rosso da owner»;
`test-capability-annulla-aspetto-e-stato-leggibile-v1`, quattro test sulla popolazione delle matrici) i test rossi sono
gli stessi, uno per uno. Gli altri: `test-ordine-al-modello-v1`, `test-refactor-qta-operativa-preventivi-v1`,
`test-esecutivi-ba-coppia-v1` (già noti), `test-articolo-usato-struttura-v1`, `test-documenti-generati-eventi`,
`test-doc-verbo-comune-e-porta-v1`, `test-lista-competenza-gruppi-colonna-emittente-v1`,
`test-annullo-documento-con-legami-v1`. I pgTAP li lancia Tid.

**Apply (Tid, 2026-11-14).** `20261114-08 … -13` applicati su dbdev e sullo scratch; il pgTAP nuovo, nella stesura
corretta, è verde da `testpgtap.sh` (ruolo applicativo).

**Pagine.** `vendite/trgfn_preventivi_guard_annullamento`, `vendite/trgfn_preventivi_guard_transizione` (riallineata
al corpo vivo: mancavano la riga attiva all'emissione, che dal 2026-10-25 sta nel guard e non più nel verbo, e la
validità finita), `script/fn_available_actions_preventivo` (le righe di `can_edit_*`; il resto della pagina resta una
cronaca, debito della famiglia), `vendite/fn_crea_revisione_preventivo` (e il suo `E_CONFIG_MANCANTE`, che il corpo
non solleva più), `vendite/vw_dash_fatturazione_preventivi`, `vendite/fn_preventivo_proietta_stato_smistamento` (diceva
INVOKER: è DEFINER dal 2026-10-25), `config/stati_doc_preventivi` (i lettori di ogni colonna; e l'«Emetti produce numero
e PDF» che il §6.14 aveva già tolto dal COMMENT). La doc auto-generata non è rigenerata.

**Richieste al team BE/FE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| BE-P1 | `backend/apps/vendite/services/_approvazioni_prezzo_constants.py` | ritirare `STATO_PREVENTIVO_DRAFT`: è il codice della bozza, e nessuno lo legge (`grep` su `backend/`, 2026-11-14) |
| FE-P1 | `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue` | `isReadonly` dalle chiavi `can_edit_*` della capability, non da `stato_codice_interno !== 'DRAFT'`: il gemello di FE-V2 per l'offerta. Il contratto della capability non cambia |

Le liste: D-PDF (a), giro 6a-bis. Nessun codice d'errore nuovo, nessuna chiave i18n nuova.

### 6.17 Giro 6b — l'ordine (team DB, 2026-11-14)

Col via di Tid al giro 6b (2026-11-14), numeri dal primo libero (`scripts/prossimo_changeset.py`). Corpi da
`pg_get_functiondef` e `pg_get_viewdef` su dbdev il 2026-11-14; le firme, coi loro `%TYPE`, dal changeSet che le ha
scritte per ultime (il catalogo li scioglie). Ogni rollback porta la definizione e il COMMENT di prima, letti dal
catalogo. I COMMENT che erano cronache sono riscritti al presente (§5d).

**Il vocabolario dell'ordine** ha `iniziale` (DRAFT), `emissione` (CONFERMATO), `is_abortito` (ANNULLATO) e
`terminale`; non ha `accettazione`. EVASO e PARZIALMENTE_EVASO sono destinazioni dell'evasione (S-3).

**Il censimento riaperto.** Il corpo vivo, commenti tolti, contro i cinque codici. ⚠️ Il primo passaggio cercava in
`prosrc`, che per le funzioni `BEGIN ATOMIC` è vuoto: rifatto su `pg_get_functiondef`, ha trovato
`vendite.fn_situazione_merce_ordine` (la soglia dell'impegno su `'CONFERMATO'`), che il §6.15 non elencava. Lo stesso
passaggio sul preventivo non trova niente: il giro 6a non ha perso oggetti. Restano fuori, per ragione:

* `vendite.trgfn_ordini_normalize`, `script.fn_check_ddt_emittibile`, `vendite.fn_ddt_push_diagnosi`: il
  `'CONFERMATO'` è `fatturazione_trigger`, un altro asse; lo stesso confronto resta nella capability, nella push-list e
  nel cruscotto;
* `vendite.trgfn_doc_guard_delete_solo_bozza`: il `'DRAFT'` è della bozza email, che non ha un vocabolario;
* i builder `dbops` (`fn_pgtap_crea_ordine*`, `fn_pgtap_crea_ddt_da_ordine`, `fn_pgtap_porta_a_stato`): ricevono la
  destinazione che il test vuole.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261114-14` | `script.fn_available_actions_ordine`: la bozza e l'annullo da `iniziale` e `is_abortito` nei quattro rami che li nominavano (i prezzi non autorizzati, le reason del push, la data di consegna confermata); `can_edit_righe` dal lock delle righe (`script.fn_doc_riga_modificabile`), come preventivo e offerta. Con il seed la risposta è la stessa nei cinque stati |
| `20_code/vendite/20261114-15` | `vendite.trgfn_ordini_guard_transizione`: Regole 2 e 5 dallo stato iniziale allo stato di emissione, Regola 3 verso lo stato di annullo, Regola 4 verso lo stato di emissione da qualunque partenza (come prima: il rientro dall'evasione compreso). La capability accendeva già gli stessi motivi dalle colonne (`20261025-81`) |
| `20_code/vendite/20261114-16` | `vendite.fn_ordine_proietta_stato_evasione`: senza legami di evasione l'ordine torna allo stato di emissione (`script.fn_stato_emissione_id`), non a `'CONFERMATO'`; PARZIALMENTE_EVASO ed EVASO restano col codice. È la forma di D-PROI (a) del preventivo |
| `20_code/vendite/20261114-17` | `vendite.fn_genera_ddt_da_ordine`: si evade dallo stato di emissione (la colonna) e da PARZIALMENTE_EVASO (il codice). Con la sola `-16`, una marca spostata riportava l'ordine in uno stato da cui la bolla non si generava più |
| `20_code/vendite/20261114-18` | `vendite.fn_list_ordini_da_pushare`: `NOT sdo.iniziale AND NOT sdo.is_abortito` al posto di `NOT IN ('DRAFT', 'ANNULLATO', 'FATTURATO')`; la «cintura» FATTURATO esce, perché dal `20261114-03` non nomina uno stato (§6.13) |
| `20_code/vendite/20261114-19` | `vendite.fn_situazione_merce_ordine` (`BEGIN ATOMIC`): la soglia dell'impegno è l'ordine dello stato con `emissione`, non di `'CONFERMATO'` |
| `20_code/vendite/20261114-20` | `vendite.vw_dash_fatturazione_ordini`: `DOC_BOZZA` da `iniziale`; la colonna entra nel `GROUP BY`; stesse colonne, `security_invoker` ripetuto |

**Il pgTAP nuovo.** `vendite/test-ordine-stati-dal-vocabolario-v1` (plan 22), sulle sole strade dell'applicazione
(il verbo `vendite.fn_cambia_stato_ordine` con l'azione concessa, i builder, l'annullo della bolla con
`vendite.fn_annulla_ddt`; mai `script.fn_doc_scrivi_stato`, lezione del §6.16). Dieci contrasti col seed, due presidi
sulla forma (i lettori non nominano i codici, tolto il confronto con `fatturazione_trigger`; proiezione e bolla
nominano solo PARZIALMENTE_EVASO ed EVASO) e dieci marche spostate: `iniziale` su CONFERMATO (capability, riga che
si scrive, cruscotto, push-list), `emissione` su EVASO (la bolla non si genera dal confermato, la riga non è più
impegnata, annullata la bolla l'ordine va a EVASO), `is_abortito` su EVASO (la reason del push, la push-list),
`emissione` su ANNULLATO (l'ordine vuoto non ci va: la Regola 2 segue la marca). Senza l'estratto 11/22: i dieci
contrasti e il 14, la metà del trigger, che legge lo stato iniziale da D-LOCK; con l'estratto 22/22.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi. L'estratto dei sette changeSet gira per intero
in `ROLLBACK`, catalogo identico dopo. ⚠️ Al primo tentativo il `-18` falliva («non è possibile cambiare il tipo
restituito»): la firma era stata presa da un changeSet vecchio (`20261020-92`) e non dall'ultimo (`20261113-17`, che
la riscrive con `DROP` + `CREATE`); corretto. Regressione con `--pgtap` sui **148** file transazionali che nominano gli
oggetti toccati, il vocabolario, la matrice o i builder dell'ordine: 148 con lo stesso esito senza e con l'estratto.
Due file la prova non li lancia: `vendite/test-documenti-numerazione-trasloco-v1` (un `DO` prima del `BEGIN`) e
`vendite/test-fn-list-ordini-da-pushare-v1` (nessun `ROLLBACK`); il secondo tocca il `-18`, e lo lancia Tid col
runner.

**L'apply (Tid, 2026-11-14) e il `-19`.** `20261114-14 … -18` sono applicati su dbdev e sullo scratch; l'update si è
fermato sul `-19`. Il COMMENT stava nello stesso `sql:` del corpo `BEGIN ATOMIC`, e pgjdbc un `BEGIN ATOMIC` lo esegue
solo da solo nel suo `sql:` (linee-guida-sql §5c; il `20261103-24` lo separava già). La prova passa da psql e non lo
vede. Il `-19` non è mai entrato: corretto nel file (il COMMENT in un change suo, nei `changes` e nel `rollback`),
riprovato in `ROLLBACK` con `-20` e il pgTAP nuovo (senza 19/22, con 22/22: i tre rossi senza sono cruscotto,
situazione merce e presidio sulla forma, cioè i due oggetti non applicati). Riapplicati da Tid il `-19` e il `-20`, i
pgTAP del giro sono verdi (2026-11-14). ⚠️ Col runner applicativo il presidio 12 era rosso: il nome della funzione
veniva da `regprocedure::text`, che omette lo schema nel `search_path` (`script` lo è per il runner, non per l'owner
della prova). Il nome ora si compone dal catalogo, schema compreso.

**Pagine.** `vendite/trgfn_ordini_guard_transizione` (riallineata al corpo vivo: la matrice che riportava era quella
del 2026-06, con CONFERMATO → ANNULLATO spento e gli stati ALLOCATO … FATTURATO; mancavano le regole 3-5 nei codici),
`script/fn_available_actions_ordine` (le righe di `can_edit_*`, la riga di CONFERMATO, la catena delle reason del push
con `ORDINE_ANNULLATO` e `ORDINE_GIA_INVIATO` che mancavano, le chiavi i18n nel namespace `vendite.ordini`; il resto
della pagina resta una cronaca, debito della famiglia), `vendite/fn_list_ordini_da_pushare`,
`vendite/vw_dash_fatturazione_ordini`, `vendite/fn_genera_ddt_da_ordine`, `vendite/fn_situazione_merce_ordine` (la
riga impegnata), `config/stati_doc_ordini` (i lettori di ogni colonna). La proiezione dell'evasione non ha una pagina
`manual/`. La doc auto-generata non è rigenerata.

**D-PDF, un dato in più.** La lista degli ordini (`OrdiniSearchTable.vue`) spegne già il PDF da `pdf_mode` della riga:
l'ordine segue già la forma (a) proposta nel §6.16, e non c'è niente da fare in questo giro.

**D-EVAD — «Genera bolla» nel drawer dell'ordine: trovato dal giro 6b, deciso (a) da Tid il 2026-11-14 (giro 6b-bis).** Il drawer accende
l'evasione con `STATI_ORDINE_EVADIBILI` (`frontend/src/vendite/ordini/constants.js`: CONFERMATO e
PARZIALMENTE_EVASO), una copia della regola di `vendite.fn_genera_ddt_da_ordine` fuori dal DB (S-10). La capability
non ha una chiave per l'evasione: senza, il FE non può leggerla.
* **(a) — proposta DB:** un giro 6b-bis. La regola esce in un building block (`script.fn_check_ordine_evadibile`,
  motivi nella forma delle `fn_check_*`), letto da `vendite.fn_genera_ddt_da_ordine` e dalla capability, che espone
  `can_genera_ddt` con `_reason` e `_reason_key` (famiglia 1). Poi il FE legge la chiave e ritira la costante.
  Ricadute: una chiave nuova nel contratto della capability, una `reason_key` nuova per il FE.
* **(b):** lasciare la costante, e scriverla fra i debiti di S-10.

**Richieste al team BE/FE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| BE-O1 | `backend/apps/vendite/services/ordini_service.py` (`_STATI_PUSHABILI`, `push_a_commessa`) | ritirare la whitelist degli stati pushabili: è la regola di `vendite.fn_list_ordini_da_pushare` scritta col codice. Subito dopo, `push_a_commessa` controlla già che ci siano righe da mandare (`count_righe_pushable`, `E_ORD_NESSUNA_RIGA`), e quelle righe le dà la push-list, che esclude lo stato iniziale e quello di annullo. Il perché in chiaro, se serve, sta in `can_push_commessa_reason` della capability |
| FE-O1 | `frontend/src/vendite/ordini/components/OrdiniDrawer.vue` | `isReadonly` dalle chiavi `can_edit_*` della capability, non da `stato_codice_interno !== STATO_ORDINE.DRAFT`: il gemello di FE-P1 e FE-V2. Il contratto della capability non cambia |
| FE-O2 | `frontend/src/vendite/ordini/stores/ordini.js` | l'avviso ai documenti collegati dopo l'annullo legge `statoCodice === STATO_ORDINE.ANNULLATO`: va legato all'azione (`key = 'annulla'` dell'azione scelta), non al codice della destinazione |

`STATI_ORDINE_EVADIBILI` aspetta il giro 6b-bis. Nessun codice d'errore nuovo, nessuna chiave i18n nuova.

### 6.18 Giri 6b-bis, 6a-bis e 2-ter — D-EVAD e D-PDF (team DB, 2026-11-14)

Col sì di Tid a D-EVAD (a) e D-PDF (a) (2026-11-14). Numeri `20261114-22 … -26`, assegnati da Tid: il `-21` è
dell'altra sessione DB.

| ChangeSet | Giro | Che cosa |
| --- | --- | --- |
| `20_code/script/20261114-22` | 6b-bis | NUOVO `script.fn_check_ordine_evadibile`: la regola «si evade dallo stato di emissione e da PARZIALMENTE_EVASO» in una funzione pura (motivi nella forma delle `fn_check_*`). Motivo `E_DDT_ORDINE_STATO_NON_EVADIBILE`, reason `ORDINE_NON_EVADIBILE`, reason_key `vendite.ordini.genera_ddt_reason.stato_non_evadibile` |
| `20_code/vendite/20261114-23` | 6b-bis | `vendite.fn_genera_ddt_da_ordine`: solleva il primo motivo della check (`script.fn_raise_primo_motivo_se_presente`), col bersaglio nel contesto come prima; escono `v_stato_ord` e `v_emissione` |
| `20_code/script/20261114-24` | 6b-bis | `script.fn_available_actions_ordine`: + `can_genera_ddt` · `_reason` · `_reason_key` (famiglia 1) dalla stessa check. Il contratto si allarga, nessuna chiave cambia |
| `20_code/vendite/20261114-25` | 6a-bis | `vendite.vw_preventivi_lista`: + `pdf_mode` in coda (`config.stati_doc_preventivi.pdf_mode`), lo stesso nome di `vendite.vw_ordini_lista`. COMMENT riscritto al presente |
| `20_code/vendite/20261114-26` | 2-ter | `vendite.vw_offerte_commerciali_lista`: + `pdf_mode` in coda |
| CSV `80_data/sql/config/messaggi_errore.csv` | 6b-bis | la frase di `E_DDT_ORDINE_STATO_NON_EVADIBILE` non nomina più i codici («attesi CONFERMATO o PARZIALMENTE_EVASO» → «la bolla si genera da un ordine confermato o evaso in parte»); mirror vivo (`runOnChange`), nessun changeSet |

Le due viste si leggono dal backend con `SELECT v.*`: la colonna arriva al FE senza altro. Il rollback di una vista
che ha preso una colonna fa `DROP` e ricrea, e rida il `GRANT` a `zeroerp_app` (`SELECT, INSERT, UPDATE, DELETE`,
`relacl` su dbdev).

**I pgTAP.** `vendite/test-ordine-stati-dal-vocabolario-v1` passa a plan 24: `8-bis` (contrasto: `can_genera_ddt`
falso in bozza col motivo, vero al confermato) e `17-bis` (con `emissione` su EVASO, `can_genera_ddt` falso sul
confermato); il presidio 11 aggiunge la bolla (nessun codice), il 12 guarda la check al posto della bolla (il solo
PARZIALMENTE_EVASO). Nuovo `vendite/test-liste-pdf-mode-dal-vocabolario-v1` (plan 4): le due liste danno PREVIEW in
bozza e ARCHIVE nell'emesso, e seguono `pdf_mode` della bozza spostato su ARCHIVE.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi (changeSet e CSV). Un solo estratto, nell'ordine
d'applicazione: `-19` e `-20` del giro 6b (ancora da applicare) e `-22 … -26`; gira per intero in `ROLLBACK`, catalogo
identico dopo. Regressione con `--pgtap` sui **160** file transazionali che nominano la capability, la bolla, il
builder della bolla, le due liste, la situazione merce, i cruscotti o il catalogo dei messaggi: tutti con lo stesso
esito o meglio. I due nuovi: l'ordine 24/24 con l'estratto, la lista 4/4; senza, si interrompono (la check e la
colonna non ci sono).

**Pagine.** Nuova `script/fn_check_ordine_evadibile`; `script/fn_available_actions_ordine` (la terna),
`vendite/fn_genera_ddt_da_ordine`, `vendite/vw_preventivi_lista`, `vendite/vw_offerte_commerciali_lista`,
`config/stati_doc_preventivi` e `config/stati_doc_offerte` (i lettori di `pdf_mode`).

**Richieste al team FE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| FE-O3 | `frontend/src/vendite/ordini/components/OrdiniDrawer.vue`, `frontend/src/vendite/ordini/constants.js`, i locales | «Genera bolla» da `can_genera_ddt` della capability (spento col tooltip di `can_genera_ddt_reason_key`), non da `STATI_ORDINE_EVADIBILI.includes(stato_codice_interno)`; poi ritirare `STATI_ORDINE_EVADIBILI`. Chiave i18n nuova: `vendite.ordini.genera_ddt_reason.stato_non_evadibile` |
| FE-P2 | `frontend/src/vendite/preventivi/components/PreventiviList.vue` | il PDF della riga da `pdf_mode !== 'ARCHIVE'`, non da `stato_codice_interno === 'DRAFT'` (due righe), come `OrdiniSearchTable.vue` |
| FE-V3 | `frontend/src/vendite/offerte/components/OfferteSearchTable.vue` | il PDF della riga da `pdf_mode !== 'ARCHIVE'`, non da `stato_codice_interno === 'BOZZA'` |

Il BE non ha niente da fare: la capability la trasporta, e le liste escono con `SELECT v.*`. Nessun codice d'errore
nuovo.

### 6.19 Giro 6c — il contratto, con D-BOZZA (team DB, 2026-11-14)

Col via di Tid al giro 6c (2026-11-14). Numeri `20261114-27 … -33`, assegnati da Tid; il `-34` (D-PDF, trovato a metà
giro) dal primo libero. Corpi da `pg_get_functiondef` e `pg_get_viewdef` su dbdev; firme dal changeSet che le ha
scritte per ultime; rollback con la definizione e il COMMENT di prima. I COMMENT sono al presente (§5d).

**Il vocabolario del contratto** ha `iniziale` (DRAFT), `emissione` (ATTIVO, l'attivazione: il contratto in vigore),
`cessazione` (CESSATO) e `is_abortito` (ANNULLATO). Aveva anche `is_bozza`, sullo stesso DRAFT di `iniziale`.

**D-BOZZA — `is_bozza`: decisa (a) da Tid il 2026-11-14.** `is_bozza` (dal `20260602-17`) la leggeva solo lo snapshot
`is_draft_snapshot` del contratto, che entra in `partecipa_overlap_snapshot` e quindi nel vincolo
`ex_contratti_no_overlap`. Il 2026-10-24 (`20261024-07`) era stata tenuta di proposito accanto a `iniziale` («dice
"è la bozza", non "si nasce qui"»); il 2026-11-14 D-LOCK ha fatto coincidere bozza e stato iniziale per lock e
capability. ⚠️ È una **revoca** della riga del 24 ottobre: due marche per lo stesso significato potevano divergere, e
l'esclusività avrebbe liberato uno stato diverso da quello che il lock lascia scrivere. La nota del §6.14, che le dava
già per uguali, era giusta nell'esito e sbagliata nella storia. Lettori di `is_bozza` sul catalogo di dbdev: solo il
montaggio del trigger; nessuna funzione, vista, vincolo o indice; niente in `backend/` né in `frontend/`.

**Il censimento.** Il corpo vivo (`pg_get_functiondef`, commenti tolti) contro i quattro codici: i cinque oggetti del
§6.15, nessuno in più. Restano fuori: i builder `dbops` (destinazioni del test), `trgfn_doc_guard_delete_solo_bozza`
(il DRAFT della mail) e, nel BE, le sottostringhe con cui `contratti_service.py` riconosce il testo di un errore
(`("ANNULLATO", "fatture")`), che non sono una regola di stato.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261114-33` | `DROP COLUMN config.stati_doc_contratti.is_bozza`; il COMMENT di `vendite.contratti.is_draft_snapshot` dice da dove viene oggi. Da zero e su ogni database gira prima del `-32` (ordine per fase); fra i due nessuno scrive i contratti. Il CSV perde la colonna (5 righe toccate: intestazione e 4 stati); i due caricatori vivi (`20260520-08`, `20260806-14`) mappano dall'intestazione e non la elencano |
| `20_code/script/20261114-27` | `script.fn_available_actions_contratto`: i motivi delle righe ammesse dallo stato iniziale, `can_edit_righe` dal lock delle righe |
| `20_code/vendite/20261114-28` | `vendite.fn_get_contratto_attivo`: il contratto in vigore è quello nello stato di emissione (`AND s.emissione`) |
| `20_code/vendite/20261114-29` | `vendite.trgfn_contratti_freeze_listino_versione`: scatta dallo stato iniziale allo stato di emissione |
| `20_code/vendite/20261114-30` | `vendite.trgfn_contratti_guard_transizione_stato`: la data arrivata verso lo stato di cessazione, i quattro motivi dell'attivazione verso lo stato di emissione |
| `20_code/vendite/20261114-31` | `vendite.trgfn_contratti_set_categoria_cliente_snapshot`: la categoria si cambia nello stato iniziale (`IS FALSE`: uno stato che non si legge non rifiuta, come prima) |
| `20_code/vendite/20261114-32` | rimonta `vendite.trgfn_doc_snapshot_da_stato` su `vendite.contratti` con `('is_draft_snapshot', 'iniziale')`; tolti per funzione tutti i nomi, lo storico `…_sync_is_abortito_snapshot_ins_upd` compreso. Valori invariati col seed: nessun backfill |
| `20_code/vendite/20261114-34` | `vendite.vw_contratti_lista`: + `pdf_mode` in coda (D-PDF (a)): `ContrattiSearchTable.vue` spegne il PDF con `'DRAFT'` |

**Trovato: il guard della categoria non parla mai** (ritirato col giro 6c-bis, §6.20, decisione di Tid del 2026-11-14). Fuori bozza il cambio di `categoria_cliente_id_snapshot` lo
rifiuta prima il lock della testata (`trg_contratti_a05_lock_fuori_bozza_upd`, `E_DOC_CONDIZIONI_FUORI_BOZZA`): il
guard `a10` (`E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE`) è una seconda sede della stessa regola. Tutti e due leggono lo
stato iniziale, quindi oggi non divergono.

**I pgTAP.** Nuovo `vendite/test-contratto-stati-dal-vocabolario-v1` (plan 12), sulle strade dell'applicazione (il
builder, il verbo `vendite.fn_cambia_stato_contratto` con l'azione concessa): cinque contrasti, due presidi sulla
forma (i cinque lettori non nominano i codici; `is_bozza` non c'è più) e cinque marche spostate: `iniziale` su ATTIVO
(capability, categoria, lo snapshot che segue lo stato iniziale), `emissione` su DRAFT (il contratto in vigore),
`cessazione` su ANNULLATO (la data di fine segue la marca). Senza l'estratto 5/12 (i contrasti), con 12/12.
`vendite/test-contratto-attiva-spento-se-sovrapposto-v1`: il test 24 passa da `is_bozza` a `iniziale`.
`vendite/test-liste-pdf-mode-dal-vocabolario-v1`: plan 6, + la lista dei contratti.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi tranne `check-i18n-keys`, rosso per la chiave del
§6.18 che il FE non ha ancora (`vendite.ordini.genera_ddt_reason.stato_non_evadibile`, FE-O3): non è di questo giro,
ma bloccava ogni commit finché non è arrivata (BE `ba8426e865`, 2026-11-14). Estratto nell'ordine d'applicazione (`-33`, poi `-27 … -32`), per intero in
`ROLLBACK`, catalogo identico dopo. Regressione con `--pgtap` sui **334** file transazionali che nominano il contratto:
tutti con lo stesso esito o meglio. Il `-34` provato a parte, col test delle liste (6/6).

**Pagine.** `config/stati_doc_contratti` (la bozza è lo stato iniziale, i lettori di ogni colonna, la nota di
migrazione), `vendite/trgfn_contratti_guard_transizione_stato` (riallineata al corpo vivo: descriveva un grafo con
SOSPESO, senza l'annullo dalla bozza, con la cessazione su `CURRENT_DATE`), `vendite/trgfn_doc_snapshot_da_stato`,
`vendite/trgfn_contratti_freeze_listino_versione`, `vendite/fn_get_contratto_attivo`,
`vendite/trgfn_contratti_set_categoria_cliente_snapshot`, `script/fn_available_actions_contratto` (la riga di
`can_edit_righe`; il resto resta una cronaca, debito della famiglia).

**Richieste al team FE (elenco chiuso).** Il BE non ha niente da fare.

| # | File | Che cosa |
| --- | --- | --- |
| FE-C1 | `frontend/src/vendite/components/ContrattoDrawer.vue` | `isContractLocked` e `isDraft` (il payload del salvataggio) dalle chiavi `can_edit_*` e da `non_editable_fields` della capability, non da `stato_codice_interno !== STATO_CONTRATTO.DRAFT`: il gemello di FE-P1, FE-O1, FE-V2 |
| FE-C2 | `frontend/src/vendite/components/ContrattoDrawer.vue` | il dialog d'emissione e l'annullo con dichiarazione si legano all'azione (`key` `attiva`, `annulla`), non a `target_state === STATO_CONTRATTO.ATTIVO` / `ANNULLATO` |
| FE-C3 | `frontend/src/vendite/stores/contratti.js` | l'avviso ai documenti collegati dopo l'annullo dall'azione, non da `STATO_CONTRATTO.ANNULLATO` (gemello di FE-O2) |
| FE-C4 | `frontend/src/vendite/components/ContrattiSearchTable.vue` | il PDF della riga da `pdf_mode !== 'ARCHIVE'` (`-34`), non da `stato_codice_interno === 'DRAFT'` (tre righe) |

### 6.20 Giro 6c-bis — il guard della categoria del contratto, ritirato (team DB, 2026-11-14)

Decisione di Tid del 2026-11-14 («ritiriamolo»), sul rilievo del §6.19. Numero `20261114-35`, dal primo libero.

**Il perché.** `vendite.trgfn_contratti_set_categoria_cliente_snapshot` faceva due cose: in `INSERT` riempie
`categoria_cliente_id_snapshot` dal billing account; in `UPDATE` rifiutava il cambio fuori bozza
(`E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE`). Il secondo ramo è una seconda sede della regola del lock della testata
(`trg_contratti_a05_lock_fuori_bozza_upd`), che blocca la stessa colonna in tutti gli stati fuori bozza, senza
eccezioni, e parla per primo (`a05` prima di `a10`): il guard non parlava mai.

**Verificato prima (dbdev, 2026-11-14).** Il lock non ha porte di override (nessun `current_setting` nel corpo);
la colonna del contratto la scrivono in `INSERT` `vendite.fn_create_contratto` e in `UPDATE` la PATCH del backend, che
passa dal lock (le altre funzioni che nominano `categoria_cliente_id_snapshot` scrivono la colonna omonima delle
attività di commessa); nessun pgTAP solleva il codice.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261114-35` | la funzione tiene il solo ramo `INSERT`; il trigger si rimonta `BEFORE INSERT` come `trg_contratti_a10_set_categoria_cliente_snapshot_ins` (tolto per funzione l'unico nome dei changelog, `…_ins_upd`); stessa fase `a10` |
| CSV `80_data/sql/config/codici_errore.csv` | `E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE` con `obsoleto_dal` = 2026-11-14 e la ragione nella nota: resta a catalogo e smette di essere sollevato (la forma di `E_ORD_ANNULLA_IN_COMMESSA`) |

**Il pgTAP.** `vendite/test-contratto-stati-dal-vocabolario-v1` passa a plan 14: il 13 (forma: il trigger è solo
`BEFORE INSERT`, e la funzione non nomina più il codice) e il 14 (alla nascita, senza categoria, il contratto la prende
dal billing account). I test 3 e 9 (il rifiuto fuori bozza lo dà il lock) restano.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi, `check-i18n-keys` compreso: la chiave del §6.18
è arrivata col commit del BE `ba8426e865`. Il `-35` gira per intero in `ROLLBACK`, catalogo identico dopo. Regressione
sui **334** file transazionali che nominano il contratto: tutti con lo stesso esito. Il test del contratto: con
l'estratto 14/14, senza 13/14 (il rosso è il 13, la forma del trigger).

**Pagine.** `vendite/trgfn_contratti_set_categoria_cliente_snapshot` (riscritta: la nascita, e chi congela la
categoria), `config/stati_doc_contratti` (la bozza congela la categoria attraverso il lock).

**Richieste al team BE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| BE-C1 | `backend/apps/core/services/error_policies_generated.py`, `error_messages_fallback.py` | rigenerarli dopo l'apply (`manage.py genera_error_policies`): `E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE` è obsoleto. Nessuna logica del BE lo legge |

Nessuna ricaduta FE.

**Apply (Tid, 2026-11-14).** `20261114-35` applicato su dbdev; il pgTAP del §6.19 (plan 14, coi test 13 e 14 del
ritiro) è verde.

### 6.21 Giro 6d — la bolla (team DB, 2026-11-14)

Numeri `20261114-36 … -46`, dal primo libero (Tid, 2026-11-14: «prendi il primo libero»). Corpi da
`pg_get_functiondef` e `pg_get_viewdef` su dbdev; firme dal changeSet che le ha scritte per ultime; rollback con la
definizione e il COMMENT di prima. I COMMENT che erano cronache sono riscritti al presente (§5d).

**Il vocabolario della bolla** ha `iniziale` (DRAFT), `emissione` (EMESSO) e `is_abortito` (ANNULLATO). SPEDITO,
CONSEGNATO e RESO sono destinazioni del processo (S-3) e restano col codice.

**Il censimento.** Il corpo vivo (`pg_get_functiondef`, commenti tolti) contro i sei codici: i 14 oggetti del §6.15,
nessuno in più. Restano col codice, per ragione: `vendite.fn_cambia_stato_ddt` (CONSEGNATO di un trasferimento),
`vendite.fn_ddt_push_diagnosi` (RESO), `dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo` (CONSEGNATO) e la soglia
SPEDITO del cruscotto: destinazioni del processo. `script.fn_check_ddt_emittibile` legge `fatturazione_trigger`, un
altro asse. Gli oggetti del reso che nominano gli stati della bolla (`vendite.fn_conferma_reso`, `vendite.fn_annulla_reso`,
`vendite.trgfn_resi_guard_ddt_consegnato`, `script.fn_check_reso_merce`, `vendite.trgfn_resi_righe_guard_quantita`)
sono del giro 6e.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261114-36` | `script.fn_available_actions_ddt`: i quattro rami dei motivi dell'emissione su `sa.emissione`; `can_edit_righe` dal lock delle righe. `SET plan_cache_mode` ripetuto (§13.7) |
| `20_code/script/20261114-37` | `script.fn_check_ddt_riga_correggi_qta_evasa`: DDT_NON_IN_BOZZA dove il lock delle righe non lascia scrivere (`script.fn_doc_riga_modificabile` `IS NOT TRUE`), la stessa frase |
| `20_code/vendite/20261114-38` | `vendite.fn_annulla_ddt`: la destinazione è lo stato di annullo del vocabolario (`script.fn_doc_stato_codice` di `script.fn_stato_abortito_id`), come `vendite.fn_annulla_ordine` |
| `20_code/vendite/20261114-39` | `vendite.trgfn_ddt_gen_numero_emesso`: il numero nello stato di emissione |
| `20_code/vendite/20261114-40` | `vendite.trgfn_ddt_guard_causale_emissione`: il gate del valore delle righe nello stato di emissione |
| `20_code/vendite/20261114-41` | `vendite.trgfn_ddt_guard_indirizzi_obbligatori`: gli indirizzi nello stato di emissione |
| `20_code/vendite/20261114-42` | `vendite.trgfn_ddt_guard_transizione`: la riga attiva dallo stato iniziale allo stato di emissione |
| `20_code/vendite/20261114-43` | `vendite.trgfn_ddt_guard_transizione_approvazione`: i prezzi nello stato di emissione |
| `20_code/vendite/20261114-44` | `vendite.trgfn_ddt_riga_legame_guard`: il ritiro con la bolla nello stato iniziale (il codice dell'iniziale, perché il lettore della testata rende il codice: la forma di `vendite.trgfn_doc_guard_delete_solo_bozza`) |
| `20_code/vendite/20261114-45` | `vendite.vw_dash_fatturazione_ddt`: `DOC_BOZZA` da `iniziale`; la colonna nel `GROUP BY` |
| `20_code/vendite/20261114-46` | `vendite.vw_ddt_lista`: + `pdf_mode` in coda (D-PDF (a)): `DdtSearchTable.vue` spegne il PDF con `STATO_DDT.DRAFT` |

**Il pgTAP nuovo.** `vendite/test-ddt-stati-dal-vocabolario-v1` (plan 14), sulle strade dell'applicazione (i builder,
il verbo `vendite.fn_cambia_stato_ddt` con l'azione concessa, `vendite.fn_annulla_ddt`): sette contrasti, un presidio
sulla forma e sei marche spostate: `iniziale` su EMESSO (capability, riga che si scrive, cruscotto, correzione della
quantità), `emissione` su SPEDITO (la bolla portata in EMESSO non prende il numero; il contrasto sì), `is_abortito` su
CONSEGNATO (l'annullo va verso CONSEGNATO, che la matrice non ha dalla bozza). Con l'estratto 14/14; senza si
interrompe al 6 (`pdf_mode` della lista arriva col `-46`). ⚠️ Una lettura dello stato dopo un verbo va in
un'istruzione sua: un attrezzo `STABLE` nella stessa istruzione vede la riga com'era all'inizio (corretto nel test 7).

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi (forme, COMMENT al presente, letterali,
`runOnChange`, timestamp, DDL sui trigger d'automazione, preambolo pgTAP). Estratto `-36 … -46` per intero in
`ROLLBACK`, catalogo identico dopo. Regressione con `--pgtap` sui **204** file transazionali che nominano la bolla:
tutti con lo stesso esito; il test nuovo si interrompe senza l'estratto (5 ok) e va 14/14 con. Fuori dalla prova i
due file non transazionali (`vendite/test-documenti-numerazione-trasloco-v1`, `vendite/test-fn-list-ordini-da-pushare-v1`):
li copre il giro dei pgTAP su dbdev.

**Apply (Tid, 2026-11-14).** `20261114-36 … -46` applicati su dbdev; i pgTAP verdi, il nuovo compreso.

**Pagine.** `config/stati_doc_ddt` (i lettori di ogni colonna, la bozza, le destinazioni del processo),
`script/fn_available_actions_ddt`, `vendite/trgfn_ddt_gen_numero_emesso`, `vendite/trgfn_ddt_guard_causale_emissione`,
`vendite/trgfn_ddt_guard_indirizzi_obbligatori`, `vendite/trgfn_ddt_guard_transizione_approvazione`,
`vendite/vw_dash_fatturazione_ddt`, `vendite/vw_ddt_lista`. Correzione della quantità, annullo e guard del legame non
hanno una pagina `manual/`.

**Trovato per il giro 6e.** Il drawer della bolla accende «Genera reso» con `stato_codice_interno ===
STATO_DDT.CONSEGNATO` (`DdtDrawer.vue`): una copia della regola di `vendite.trgfn_resi_guard_ddt_consegnato`. La
capability della bolla non ha una chiave per il reso: la forma è quella di D-EVAD (una check, la chiave nella
capability), da proporre col giro del reso.

**Richieste al team FE (elenco chiuso).** Il BE non ha niente da fare.

| # | File | Che cosa |
| --- | --- | --- |
| FE-D1 | `frontend/src/vendite/ddt/components/DdtDrawer.vue` | il lucchetto del drawer dalle chiavi `can_edit_*` della capability, non da `stato_codice_interno !== STATO_DDT.DRAFT` (gemello di FE-P1, FE-O1, FE-C1, FE-V2) |
| FE-D2 | `frontend/src/vendite/ddt/components/DdtSearchTable.vue` | il PDF della riga da `pdf_mode !== 'ARCHIVE'` (`-46`), non da `STATO_DDT.DRAFT` (due righe) |
| FE-D3 | `frontend/src/vendite/ddt/stores/ddt.js` | l'avviso ai documenti collegati dopo l'annullo dall'azione, non da `STATO_DDT.ANNULLATO` (gemello di FE-O2, FE-C3) |

### 6.22 Giro 6e — il reso (team DB, 2026-11-14)

Col via di Tid (2026-11-14, «procedi 6e»). Numeri `20261114-47 … -57`, dal primo libero. Corpi da
`pg_get_functiondef` su dbdev; firme dal changeSet che le ha scritte per ultime (quella della capability del reso,
che era `bigint` nudo, ancorata con `%TYPE`); rollback con la definizione e il COMMENT di prima. I COMMENT che erano
cronache sono riscritti al presente (§5d).

**Il vocabolario del reso** ha `iniziale` (DRAFT), `emissione` (CONFERMATO: la conferma è l'emissione, lì nasce il
numero e la merce rientra) e `is_abortito` (ANNULLATO). Nessuna destinazione di processo sua; CONSEGNATO e RESO della
bolla, che conferma e annullo scrivono, sono destinazioni del processo della bolla (S-3) e restano col codice.

**Il censimento.** Il corpo vivo (commenti tolti) contro i tre codici, sulle funzioni e viste che nominano il reso:
12 oggetti. Dei 9 del §6.15 ne entrano 8; `vendite.trgfn_resi_guard_ddt_consegnato` nomina CONSEGNATO, una destinazione
della bolla, ed entra per D-RESO. In più `vendite.trgfn_resi_righe_guard_quantita`, che il §6.15 elencava, e
`vendite.fn_chiudi_riconsegna_reso`, `vendite.fn_riapri_riconsegna_reso` e `vendite.fn_genera_ddt_riconsegna` con la
stessa porta. Restano fuori, per ragione: `vendite.fn_ddt_push_diagnosi` (CONFERMATO è il `fatturazione_trigger`
dell'ordine, un altro asse), `vendite.trgfn_doc_guard_delete_solo_bozza` (DRAFT è di `config.email_outbox`, che non
ha un vocabolario), i builder `dbops.fn_pgtap_crea_reso` e `dbops.fn_pgtap_porta_a_stato` (ricevono lo stato a cui il
test vuole arrivare). Le viste che leggono lo stato del reso (`vw_resi_righe_effettive`, `vw_stato_sorgente_reso`,
`vw_resi_lista`, …) non nominano codici. Il reso non ha le colonne della stampa: D-PDF non lo tocca.

**D-RESO — «Genera reso» e la ri-spedizione dalla capability: decisa (a) da Tid il 2026-11-14.** Due copie nel
frontend di regole del DB, trovate col giro 6d (§6.21) e con questo:

* il drawer della bolla accende «Genera reso» con `stato === CONSEGNATO`, una copia di
  `vendite.trgfn_resi_guard_ddt_consegnato` senza la bolla di trasferimento; e il service `crea_reso` ne ha una terza,
  con lo stesso limite. (a): la regola esce in `script.fn_check_ddt_rendibile`, letta dal trigger e dalla capability
  della bolla (`can_genera_reso`), la forma di D-EVAD;
* il drawer del reso accende la ri-spedizione con `stato === CONFERMATO`, la porta dei tre verbi della riconsegna.
  (a): la capability del reso emette `can_riconsegna`, dalla stessa colonna `emissione` che i verbi leggono.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261114-47` | NUOVO `script.fn_check_ddt_rendibile`: i motivi per cui da una bolla non nasce un reso, E_RESO_DA_DDT_TRASFERIMENTO prima di E_RESO_DDT_NON_CONSEGNATO (l'ordine del trigger); la bolla assente dà il secondo, come prima. Due `reason_key` nuove |
| `20_code/vendite/20261114-48` | `vendite.trgfn_resi_guard_ddt_consegnato`: il primo motivo della check (`script.fn_raise_primo_motivo_se_presente`), stessi codici; `sorgente_id` nullo lo lascia al vincolo `chk_resi_sorgente_forma` |
| `20_code/script/20261114-49` | `script.fn_available_actions_ddt`: + `can_genera_reso` · `_reason` · `_reason_key` dalla check |
| `20_code/script/20261114-50` | `script.fn_available_actions_reso`: il motivo degli accrediti su `sa.is_abortito`, quelli della merce su `sa.emissione` (calcolati in ogni stato: da dove si conferma lo dice la matrice); `can_edit_righe` dal lock delle righe; + `can_riconsegna` dalla colonna `emissione` |
| `20_code/script/20261114-51` | `script.fn_check_reso_merce`: i resi non annullati del tetto per prelievo da `is_abortito` |
| `20_code/vendite/20261114-52` | `vendite.fn_conferma_reso`: la destinazione da `script.fn_stato_emissione_id`; E_RESO_STATO_NON_CONFERMABILE dove la matrice non ha il passaggio (`script.fn_doc_passaggio`), non fuori da DRAFT |
| `20_code/vendite/20261114-53` | `vendite.fn_annulla_reso`: la destinazione da `script.fn_stato_abortito_id`; E_RESO_STATO_NON_ANNULLABILE dove la matrice non ha il passaggio, non fuori da `('DRAFT','CONFERMATO')`; lo storno se lo stato di partenza è di emissione |
| `20_code/vendite/20261114-54` | `vendite.fn_genera_ddt_riconsegna`: E_RESO_NON_CONFERMATO fuori dallo stato di emissione |
| `20_code/vendite/20261114-55` | `vendite.fn_chiudi_riconsegna_reso`: idem |
| `20_code/vendite/20261114-56` | `vendite.fn_riapri_riconsegna_reso`: idem |
| `20_code/vendite/20261114-57` | `vendite.trgfn_resi_righe_guard_quantita`: i resi non annullati da `is_abortito` |

⚠️ **Conferma e annullo: perché la matrice e non una colonna.** «Da DRAFT si conferma», «da DRAFT e CONFERMATO si
annulla» non sono significati di uno stato: sono le righe di `config.transizioni_stati_reso`. Il guard del permesso
(`script.fn_guard_passaggio`), che parla una riga prima, su una riga assente fra due stati diversi tace: il rifiuto
del verbo resta, e legge lo stesso lettore (`script.fn_doc_passaggio`). Con il seed le risposte sono quelle di prima;
dallo stato di destinazione parla il guard (`E_DOC_GIA_NELLO_STATO`).

**Il pgTAP nuovo.** `vendite/test-reso-stati-dal-vocabolario-v1` (plan 14), sulle strade dell'applicazione (i
builder di bolla e reso, la conferma dal verbo, l'annullo da `vendite.fn_annulla_reso`, i tre verbi della
riconsegna): sette contrasti (fra cui `can_genera_reso` e il trigger, che rispondono uguale), due presidi sulla forma
(i lettori non nominano DRAFT, CONFERMATO e ANNULLATO; il trigger del reso dalla bolla non nomina CONSEGNATO e
TRASF_OUT) e quattro marche spostate, in cinque test: `iniziale` su CONFERMATO (`can_edit_righe`), `emissione` su DRAFT
(`can_riconsegna` e la ri-spedizione, che rispondono uguale), `is_abortito` su DRAFT (l'annullo del confermato va
verso DRAFT, che la matrice non ha) e su CONFERMATO (il reso confermato esce dal tetto della quantità). Con
l'estratto 14/14; senza 5/14 (le chiavi e le risposte nuove).

**Un pgTAP adeguato.** `config/test-costanti-catalogo-citate-dal-codice-v1`, test 4 (anti-marciume): la riga
(stati_doc_reso ANNULLATO, `script.fn_available_actions_reso`) esce. Il presidio guardava che un codice rinominato
non riaccendesse il bottone dell'annullo; con `is_abortito` il codice non c'è più, e il test 4 lo diceva, come la
sua testata prevede. Esce anche la lettura di `config.stati_doc_reso` fra i presenti, che nessuna riga chiedeva; il
conteggio del test 1 passa da 7 a 6.

**La prova (scratch `zeroerp_ruoli`, 2026-11-14).** Guardrail verdi (forme, COMMENT al presente, letterali,
`runOnChange`, timestamp, DDL sui trigger d'automazione, preambolo pgTAP). Estratto `-47 … -57` per intero in
`ROLLBACK`, catalogo identico dopo. Regressione con `--pgtap` sui **392** file transazionali che nominano il reso, la
riconsegna o la capability della bolla, più i presidi che leggono il catalogo delle funzioni: con l'estratto tutti
verdi tranne uno, `script/test-catalogo-messaggi-errore-completo` test 7 (i valori del motivo DDT_NON_CONSEGNATO non
erano i segnaposti della sua frase: corretto nel giro 6e-bis, sotto). ⚠️ Il giro è stato applicato (dbdev e scratch,
22:11) a regressione in corso: dopo quell'ora le corse «senza» avevano già l'estratto, e il confronto senza/con vale
solo per i file passati prima. Il lato «con» vale per tutti. Fuori dalla prova i tre file non transazionali
(`config/test-toponomastica-stradario-generale`, `vendite/test-documenti-numerazione-trasloco-v1`,
`vendite/test-fn-list-ordini-da-pushare-v1`): li copre il giro dei pgTAP su dbdev.

**Apply (Tid, 2026-11-14).** `20261114-47 … -57` applicati su dbdev e sullo scratch (databasechangelog, 22:11);
il `-58` dopo. I pgTAP verdi su dbdev (Tid).

**Giro 6e-bis — i valori del motivo (`20_code/script/20261114-58`).** `script.fn_check_ddt_rendibile` dava al motivo
E_RESO_DDT_NON_CONSEGNATO due valori (numero e stato della bolla), ma la frase del codice non ha segnaposti:
`format()` li ignora, e il test 7 del catalogo dei messaggi pretende l'uguaglianza. Ora `valori` =
`jsonb_build_array()`; l'id e lo stato restano nel dettaglio. Il `-47` è applicato e non si tocca: CREATE OR
REPLACE, rollback al corpo del `-47`. Provato in `ROLLBACK` sullo scratch, col giro applicato: il test 7 da rosso a
verde (senza 6/7, con 7/7), il test del reso 14/14.

**Pagine.** `config/stati_doc_reso` (chi legge ogni colonna, la matrice per conferma e annullo),
`script/fn_available_actions_reso`, `script/fn_available_actions_ddt` (`can_genera_reso`), NUOVA
`script/fn_check_ddt_rendibile`, `vendite/fn_conferma_reso`, `vendite/fn_annulla_reso`,
`vendite/fn_genera_ddt_riconsegna`, `vendite/fn_chiudi_riconsegna_reso`, `vendite/fn_riapri_riconsegna_reso`,
`vendite/trgfn_resi_guard_ddt_consegnato`, `vendite/trgfn_resi_righe_guard_quantita`. `script.fn_check_reso_merce`
non ha una pagina `manual/`. ⚠️ La pagina autogenerata della check nuova (`script/funzioni/`) e gli indici dello
schema nascono con la rigenerazione della doc.

**Richieste al team FE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| FE-R1 | `frontend/src/locales/it.json`, `en.json` | le chiavi `vendite.ddt.genera_reso_reason.trasferimento` (un valore: il numero della bolla) e `vendite.ddt.genera_reso_reason.non_consegnato` (nessun valore, `-58`). ⚠️ Fino ad allora `check-i18n-keys` è rosso e blocca ogni commit, come per FE-O3 |
| FE-R2 | `frontend/src/vendite/ddt/components/DdtDrawer.vue` | «Genera reso» (`showResoAction`) da `can_genera_reso`, spento col motivo (`can_genera_reso_reason_key`), non da `stato_codice_interno === STATO_DDT.CONSEGNATO` (gemello di FE-O3) |
| FE-R3 | `frontend/src/vendite/resi/components/ResoDrawer.vue` | la ri-spedizione e la sua dialog (`isConfermato`) da `can_riconsegna`, non da `STATO_RESO.CONFERMATO`; il lucchetto (`isReadonly`) dalle chiavi `can_edit_*` della capability, non da `!== STATO_RESO.DRAFT` (gemello di FE-D1) |
| FE-R4 | `frontend/src/vendite/resi/constants.js`, `frontend/src/vendite/_shared/situazioneMerce/situazioneMerceCostanti.js` | dopo FE-R3, `STATO_RESO` non ha più lettori: si ritira, col commento che lo cita. La mappa dei colori (`STATO_RESO_MAP` in `core/utils/severity.js`) è presentazione e resta |

**Richieste al team BE (elenco chiuso).**

| # | File | Che cosa |
| --- | --- | --- |
| BE-R1 | `backend/apps/vendite/services/resi_service.py`, `backend/apps/vendite/tests/services/test_resi_service.py` | `crea_reso`: ritirare il guard gemello (`ErrorManager.require` su `_STATO_DDT_SORGENTE`) e la costante. È una terza copia della regola, senza la bolla di trasferimento: risponde il trigger, con lo stesso codice (409) e in più E_RESO_DA_DDT_TRASFERIMENTO. Il test 9 del service esce o passa a un test d'integrazione. `get_ddt_sorgente` resta (lo usa `list_righe_ddt_per_reso`) |

Chi cambia per primo: il DB. Con il giro applicato FE e BE di oggi funzionano: le chiavi nuove si aggiungono, nessuna
cambia, e il guard del service risponde come il trigger.

### 6.23 Dal BE/FE dei giri 6a … 6e — richieste al team DB (2026-11-14)

> **Chi scrive:** team BE/FE (`dev/backend-tid`), 2026-11-14. **A chi:** il team DB. Decisione di Tid del 2026-11-14:
> le tre si chiedono al DB; il FE non mette un ripiego nell'attesa.

Le richieste BE/FE dei §6.16 … §6.22 sono fatte (da committare, `dev/backend-tid`), e quelle di simmetria che Tid ha
chiesto in più: anche lo store e il drawer del preventivo riconoscono emissione, accettazione e annullo dal verbo
(`key`), non dalla destinazione. Tre building block nuovi, approvati da Tid: `useCorpoDocumento` (il lucchetto dei
sei drawer documento), `useEntityCapabilities.azioneDaFlag` («Genera bolla», «Genera reso»), `azionePdfLista` (il
PDF delle cinque liste); in più `avvisaDopoAzione` nel BB dell'avviso dopo l'annullo. Lo usa anche la commessa (store e `CommessaGestioneDrawer`, 2026-11-14): la sua matrice
(`transizioni_stati_commessa`) dà `action_key = annulla` a tutti i passaggi verso ANNULLATA, e solo a quelli. Restano tre punti che il FE
non chiude da solo, perché il dato non è nella capability.

* **R-V1. I valori del motivo non arrivano.** `script.fn_check_ddt_rendibile` dà al motivo `DDT_TRASFERIMENTO` un
  valore (il numero della bolla), ma `script.fn_available_actions_ddt` ne porta solo `can_genera_reso_reason` e
  `_reason_key`: i `valori` si perdono. La frase i18n del trasferimento (FE-R1) l'abbiamo scritta **senza**
  segnaposto: con `{0}` il tooltip mostrerebbe `{0}`. Nessuna capability oggi porta i valori di un motivo.
  **Richiesta:** una forma di casa per i valori del motivo di un flag, per esempio `<flag>_reason_valori` (array,
  vuoto se la frase non ne ha), a cominciare da `can_genera_reso`. Il FE poi li passa alla frase in
  `azioneDaFlag` e `azioneNegata` (il mapper delle azioni di stato li legge già, `useDrawerActions`), e la frase
  del trasferimento riprende il numero.
* **R-V2. Il drawer del contratto legge ancora tre codici di stato** (`ContrattoDrawer.vue`), fuori dall'elenco
  chiuso del §6.19:
  * il banner «fuori bozza» sceglie fra `banner_locked_attivo` (info) e `banner_locked_cessato` (warn) con
    `stato === CESSATO`. È la domanda «lo stato è terminale?»: l'offerta la chiede a `stato_terminale` della sua
    capability, quella del contratto non la emette;
  * il campo `valido_al` si vede in creazione, in bozza, in CESSATO e in ATTIVO con la data valorizzata, e
    l'etichetta dice «Data cessazione» in CESSATO, «Cessazione programmata» in ATTIVO con la data, «Valido al»
    altrimenti. Sono le marche `iniziale`, `emissione` e `cessazione` del vocabolario.

  **Richiesta:** nella capability del contratto le marche dello stato corrente che il drawer legge,
  `stato_terminale` (colonna `terminale`, come l'offerta) e `stato_cessazione` (colonna `cessazione`); per
  «bozza» il FE usa già il lock (`useCorpoDocumento`), per l'emissione basta «non iniziale e non cessazione»
  se il DB conferma che il contratto non ha altri stati vivi. Se il DB preferisce un'altra forma (per esempio
  un'unica chiave `stato_marca`), la scelga lui: il FE si adegua. Poi una richiesta FE: banner ed etichetta dalle
  chiavi, e i tre confronti con `STATO_CONTRATTO` escono.
* **R-V3. Lo smistamento del preventivo si mostra da due codici.** `PreventiviDrawer.vue` (`showSmistamento`)
  apre il pannello dello smistamento con `stato === ACCETTATO || stato === EVASO`: «dall'accettazione in poi»,
  EVASO in consultazione. La capability ha `can_push_commessa` e `can_genera_ordine` (eseguibili adesso), non
  «il preventivo è uno che si smista». **Richiesta:** la chiave che lo dice, dalla colonna del vocabolario che il DB
  ritiene giusta (l'esito positivo dell'accettazione, o una marca sua). Poi una richiesta FE: `showSmistamento` dalla
  chiave, e `STATO_PREVENTIVO.ACCETTATO`/`EVASO` escono dal drawer.

Chi cambia per primo: il DB. Le chiavi nuove si aggiungono e nessuna cambia: il FE di oggi continua a funzionare.

### 6.24 Risposta DB a R-V1 … R-V3: ricognizione e tre decisioni (2026-11-14)

> ✅ **Decise da Tid il 2026-11-14: D-VAL (a), D-MARCHE (a), D-SMIST (a)** («ok come da proposta»).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-14. **A chi:** Tid per le decisioni, poi il team DB (giro 6g).
> Letti sulla doc auto-generata, rigenerata in `a568963fea` dopo l'ultimo changeSet sugli oggetti
> (`20261114-58`). **Brief vicini verificati:** nessuno in `work-in-progress/` tocca le tre capability o le tre
> chiavi; `piano-be-fe-magazzino-lotto-3.md` cita solo la forma `reasons` della bolla. Precedenti in `work-done/`:
> `brief-db-reso-motivi-conferma-con-valori.md` (2026-10-14: `reasons` coi `valori` su un'**azione**) e
> `brief-db-i-motivi-si-fermano-dentro-la-check.md` (la check emette i valori). Nessuno dei due ha deciso la forma
> per un **flag**: R-V1 è nuova, e completa quelle due decisioni.

#### R-V1 — i valori del motivo di un flag (D-VAL)

**Stato.** `script.fn_check_ddt_rendibile` dà a `E_RESO_DA_DDT_TRASFERIMENTO` i `valori` (il numero della bolla, o
l'id); `script.fn_available_actions_ddt` ne copia `reason` e `reason_key` in `can_genera_reso_reason` e
`_reason_key`, e i `valori` si perdono. Il difetto è reale sul modello: la frase del motivo ha un valore, e il
flag non lo porta.

**Forma.** Su un'**azione** la forma di casa è la terna `enabled`/`reason`/`reason_key` più `reasons` (§12.2 delle
linee guida; brief del 2026-10-14). Un **flag** è il primo motivo appiattito in chiavi sorelle: `<flag>_reason`,
`<flag>_reason_key`. Strade:

* **(a)** ⭐ `<flag>_reason_valori`, l'array `valori` del primo motivo, `[]` quando il flag è vero o la frase non ha
  segnaposti. È la richiesta del FE: le chiavi sorelle diventano i tre campi dell'oggetto motivo, uno per uno, e
  nessun lettore deve sapere di un array di oggetti;
* **(b)** `<flag>_reasons`, l'array intero della check, come `reasons` sulle azioni. Più simmetrica con le azioni,
  ma la check della bolla esce al primo motivo: l'array ha sempre un elemento, e il FE dovrebbe leggere due forme
  per la stessa frase.

⚠️ **Il fatto sotto il perimetro qui sotto è sbagliato (verifica DB del 2026-11-15, §6.25).** `can_genera_reso`
non è l'unico flag la cui sorgente emette valori: ce ne sono altri cinque, e la regola scritta nel §12.2 li
lascia fuori regola dal giorno in cui nasce.

**Perimetro.** Solo `can_genera_reso` in questo giro, perché è l'unico flag la cui sorgente emette valori; la
regola si scrive nel §12.2 delle linee guida (la forma del flag), e gli altri flag la prendono quando la loro
sorgente avrà valori. Portarla su tutte le capability adesso sarebbe un tema ricopiato documento per documento:
il fermo del 2026-10-21 lo vieta senza l'ok di Tid.

**Ricaduta FE**, dopo il giro: la frase `vendite.ddt.genera_reso_reason.trasferimento` riprende `{0}`, e
`azioneDaFlag`/`azioneNegata` passano `<flag>_reason_valori` alla frase.

#### R-V2 — le marche dello stato del contratto (D-MARCHE)

**Stato.** `config.stati_doc_contratti` ha quattro stati: DRAFT (`iniziale`), ATTIVO (`emissione`), CESSATO
(`cessazione`, `terminale`) e **ANNULLATO** (`is_abortito`, `terminale`, nessuna delle tre marche). Le marche
`iniziale`, `emissione`, `cessazione` hanno un indice unico parziale ciascuna. La capability del contratto emette
`stato_codice_interno` e `stato_codice`, nessuna marca; quella dell'offerta emette `stato_terminale` (giro 2,
`20261112-62`).

⚠️ **La deduzione proposta dal FE non regge sul modello.** «Emissione = non iniziale e non cessazione» vale anche
per ANNULLATO, che è un quarto stato. Non va dedotta: va emessa.

⚠️ **Il FE di oggi sbaglia già su ANNULLATO.** Col banner scelto da `stato === CESSATO`, un contratto annullato
riceve il banner informativo dell'attivo. Con `stato_terminale` prende quello di avviso.

**Proposta (a)** ⭐: quattro chiavi booleane, una per colonna, coi nomi dell'offerta: `stato_terminale`,
`stato_emissione`, `stato_cessazione` e, per completezza, `stato_iniziale`. Il FE ne legge tre. Scartata la chiave
unica `stato_marca`: le marche non si escludono (CESSATO è `cessazione` **e** `terminale`), e una chiave sola
dovrebbe scegliere fra le due. **(b)** solo le tre che il drawer legge oggi (`stato_terminale`, `stato_emissione`,
`stato_cessazione`).

**Ricaduta FE**, dopo il giro: banner da `stato_terminale`; il campo `valido_al` si vede in creazione, con
`stato_iniziale` (o il lock della bozza), con `stato_cessazione` e con `stato_emissione` più la data; le etichette
seguono le stesse chiavi. I tre confronti con `STATO_CONTRATTO` escono.

#### R-V3 — lo smistamento del preventivo (D-SMIST)

**Stato.** Il predicato «il preventivo è uno che si smista» esiste già, una volta sola, in
`vendite.fn_preventivo_proietta_stato_smistamento`: `v_accettazione OR v_stato = 'EVASO'`. Lì EVASO si nomina
col codice per decisione (D-PROI (a), 2026-11-14: «EVASO resta la destinazione nominata del processo»).
`config.stati_doc_preventivi` non ha una colonna che distingua EVASO da RIFIUTATO, SCADUTO e ANNULLATO: sono tutti
`CHIUSO` e `terminale`, e `esito` non è nel seed.

Emettere la chiave nella capability sarebbe la **seconda copia** del predicato: regola del 2, si estrae. Strade:

* **(a)** ⭐ un building block `vendite.fn_preventivo_in_smistamento(<stato>)` → boolean, con dentro il predicato di
  oggi; lo leggono la proiezione (che perde la sua copia) e `script.fn_available_actions_preventivo`, che emette
  `in_smistamento`. Nessun cambio di modello: EVASO resta nominato col codice, in un posto solo;
* **(b)** una marca nuova del vocabolario (`smistamento`, vera su ACCETTATO ed EVASO), letta da tutti e due.
  È un cambio di **modello**, e **revoca in parte D-PROI**: EVASO non sarebbe più riconosciuto col codice nella
  partenza della proiezione. Vale la pena solo se lo smistamento deve essere configurabile.

**Ricaduta FE**, dopo il giro: `showSmistamento` da `in_smistamento`, e `STATO_PREVENTIVO.ACCETTATO`/`EVASO` escono
dal drawer.

#### Il giro 6g, se le tre passano come raccomandate

Cinque changeSet di `20_code`: le capability della bolla e del contratto, il BB, la proiezione che lo legge e la
capability del preventivo. Poi un pgTAP per capability toccata (costruiti: una bolla di trasferimento, un contratto per
ognuno dei quattro stati, un preventivo per ognuno dei sette), le pagine `manual/` e il §12.2 delle linee guida.
Chi cambia per primo: il DB. Le chiavi nuove si aggiungono e nessuna cambia: il FE di oggi continua a funzionare.

#### Giro 6g — fatto dal DB (2026-11-15), applicato e verde (Tid, 2026-11-15)

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261114-74` | `script.fn_available_actions_ddt`: + `can_genera_reso_reason_valori`, i `valori` del primo motivo di `script.fn_check_ddt_rendibile`, `[]` col flag vero o con una frase senza segnaposti (D-VAL) |
| `20_code/script/20261114-75` | `script.fn_available_actions_contratto`: + `stato_iniziale`, `stato_emissione`, `stato_cessazione`, `stato_terminale`, le colonne del vocabolario dello stato corrente (D-MARCHE) |
| `20_code/vendite/20261114-76` | NUOVO `vendite.fn_preventivo_in_smistamento(p_accettazione, p_stato)`: vero dallo stato di accettazione e da EVASO, mai `NULL`; `LANGUAGE sql`, `IMMUTABLE`, non `STRICT` (D-SMIST) |
| `20_code/vendite/20261114-77` | `vendite.fn_preventivo_proietta_stato_smistamento`: la partenza dal building block, la sua copia del predicato esce |
| `20_code/script/20261114-78` | `script.fn_available_actions_preventivo`: + `in_smistamento`, dal building block |

Pgtap nuovo: `vendite/test-capability-valori-marche-smistamento-v1` (plan 12; la bolla di trasferimento, le quattro
marche del contratto nei quattro stati con contrasto, due marche spostate, il building block su sette coppie, due
presidi sulla forma dichiarati tali). Doc: le pagine `manual/` delle tre capability, della proiezione e del building
block (nuova); la forma del flag col suo motivo in `linee-guida-sql.md` §12.2. Le chiavi sono nuove e nessuna cambia: il
FE di oggi funziona. Nessuna `reason_key` nuova.

**Prova (2026-11-15, `scripts/prova_changeset.py` su `zeroerp_ruoli`, in ROLLBACK).** L'estratto passa per intero e il
catalogo resta identico. Il pgTAP nuovo: 12 ok con l'estratto (senza si interrompe: il building block non c'è). Senza
regressioni, prima e dopo uguali: `test-preventivo-stati-dal-vocabolario-v1` (18), `test-contratto-stati-dal-vocabolario-v1`
(14), `test-reso-stati-dal-vocabolario-v1` (14), `test-ddt-trasferimento-v1` (13), `test-doc-stati-dal-vocabolario-v1`
(13), `test-annullo-commessa-v1` (37), `test-corpo-funzione-senza-commenti-v1`, `test-security-definer-search-path-v1`,
`test-plan-cache-mode-piano-generico-v1`. ⚠️ `test-contratto-al-modello-v1` ha un rosso **preesistente** (21 ok, 1 not ok
anche senza l'estratto), da spiegare: non è di questo giro. Guardrail statici verdi (COMMENT al presente, forme,
letterali, runOnChange). La doc auto-generata è da rigenerare dopo l'apply.

#### Richieste al team FE, dopo l'apply del giro 6g

| # | Che cosa | File |
| --- | --- | --- |
| FE-G1 | La frase `vendite.ddt.genera_reso_reason.trasferimento` riprende il segnaposto `{0}` (il numero della bolla), in `it.json` e `en.json`; `azioneDaFlag` e `azioneNegata` passano alla frase `<flag>_reason_valori` (vuoto = nessun valore) | `frontend/src/locales/it.json`, `frontend/src/locales/en.json`, `frontend/src/core/composables/useEntityCapabilities.js` (e il suo spec) |
| FE-G2 | Il banner fuori bozza da `stato_terminale` (avviso se vero, informativo altrimenti); il campo `valido_al` si vede in creazione, con `stato_iniziale`, con `stato_cessazione` e con `stato_emissione` più la data; l'etichetta «Data cessazione» con `stato_cessazione`, «Cessazione programmata» con `stato_emissione` e la data, «Valido al» altrimenti. Escono i tre confronti con `STATO_CONTRATTO`. ⚠️ Cambia a video l'annullato: oggi riceve il banner informativo dell'attivo, con `stato_terminale` prende quello di avviso | `frontend/src/vendite/components/ContrattoDrawer.vue` |
| FE-G3 | `showSmistamento` da `in_smistamento`; `STATO_PREVENTIVO.ACCETTATO` ed `EVASO` escono dal drawer | `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue` |

Il BE non ha codice da cambiare: passa il blob della capability così com'è, come per i `reasons` del reso
(2026-10-14). Se un serializer o un test del BE elenca le chiavi del blob, il BE lo dice.

### 6.25 Verifica DB del giro 6g (2026-11-15, dopo l'apply): cinque flag fuori dalla regola del §12.2

> **Chi scrive:** sessione di revisione DB (`dev/db-tid`), 2026-11-15, su `20261114-74 … -78` già applicati
> (dbdev e scratch, `databasechangelog` delle 09:30-09:31). **A chi:** Tid, per D-VAL-2.

**Il resto del giro regge.** I corpi coincidono con la doc auto-generata rigenerata; volatilità, `SECURITY`,
`SET` e privilegi sono quelli di prima (`fn_available_actions_ddt` tiene `plan_cache_mode`); il building block
dà `false` e mai `NULL` (`IS TRUE` lega più stretto di `OR`); proiezione e capability lo leggono, e la copia
del predicato è uscita. Il pgTAP nuovo costruisce i casi e sposta le marche, e i due presidi di forma (11, 12)
sono dichiarati tali.

**Il difetto: la regola nasce già violata.** Il §12.2 dice che `<flag>_reason_valori` «si emette quando la
sorgente del motivo ha valori». Il §6.24 (R-V1, «Perimetro») ha portato la chiave sul solo `can_genera_reso`,
dicendo che è l'unico flag la cui sorgente emette valori. Non è vero. Lette sulla doc auto-generata, cinque
sorgenti di flag emettono già `valori` non vuoti, e i loro flag ne portano solo `reason` e `reason_key`:

| Capability | Flag | Sorgente del motivo | `valori` della sorgente |
| --- | --- | --- | --- |
| `script.fn_available_actions_ordine` | `can_edit_data_consegna_confermata` | `script.fn_check_ordine_data_consegna_confermata` | etichetta, stato, verbo |
| `script.fn_available_actions_ordine` | `can_genera_ddt` | `script.fn_check_ordine_evadibile` | numero dell'ordine (o id), stato |
| `script.fn_available_actions_offerta` | `can_push_contratto` | `script.fn_check_righe_documento` | etichetta, codice articolo |
| `script.fn_available_actions_offerta` | `can_genera_ordine` | `script.fn_check_righe_offerta_in_ordine` | etichetta, codice articolo |
| `script.fn_available_actions_documento_interno` | `can_registra` | `script.fn_check_documento_interno_registrabile` | stato, id del documento o della riga |

È lo stesso difetto che R-V1 correggeva sulla bolla: la frase ha un segnaposto e il flag non lo porta. Il
FE-G1 è generico (`azioneDaFlag` passa `<flag>_reason_valori` a ogni frase), quindi un flag senza la chiave
non rompe niente: la sua frase continua a mostrare `{0}`, o tace il dato.

> ✅ **Decisa da Tid il 2026-11-15: D-VAL-2 (a)** («ok a come da tua proposta»); la strada (b) è
> scartata. Il giro 6g-bis è fatto e applicato lo stesso giorno: sotto, «Giro 6g-bis».

**D-VAL-2 (Tid).** Il tema tocca tre famiglie di documenti, e il fermo del 2026-10-21 chiede l'ok di Tid:

* **(a)** ⭐ un giro 6g-bis: `_reason_valori` sui cinque flag, tre changeSet di `20_code` (ordine, offerta,
  documento interno), un caso costruito per flag nel pgTAP del 6g, le tre pagine `manual/`. Nessuna chiave
  cambia: il FE di oggi funziona, e con FE-G1 le frasi riprendono i segnaposti. Prima il DB, poi il FE
  controlla le cinque frasi in `it.json`/`en.json`;
* **(b)** la regola del §12.2 resta com'è e i cinque flag restano debito, con un brief «aperto, non
  iniziato».

Con il giro 6g-bis il §12.2 non ha eccezioni: ogni flag la cui sorgente ha valori porta `_reason_valori`.

#### Giro 6g-bis — fatto dal DB e applicato (2026-11-15)

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261114-79` | `script.fn_available_actions_ordine`: + `can_edit_data_consegna_confermata_reason_valori` (i valori di `script.fn_check_ordine_data_consegna_confermata`; `[]` nello stato iniziale, dove il motivo `ORDINE_IN_BOZZA` è della capability) e + `can_genera_ddt_reason_valori` (di `script.fn_check_ordine_evadibile`) |
| `20_code/script/20261114-80` | `script.fn_available_actions_offerta`: + `can_push_contratto_reason_valori` e + `can_genera_ordine_reason_valori` (di `script.fn_check_righe_documento` e `script.fn_check_righe_offerta_in_ordine`; `[]` coi motivi della capability: documento già generato, offerta non accettata) |
| `20_code/script/20261114-81` | `script.fn_available_actions_documento_interno`: + `can_registra_reason_valori` (di `script.fn_check_documento_interno_registrabile`). La firma resta a tipi nudi, con la ragione accanto: l'id è di tre tabelle |

Il corpo viene da `pg_get_functiondef`, identico alla doc auto-generata; firma ri-ancorata come nell'ultimo
changeSet di ciascuna funzione; `CREATE OR REPLACE`, attributi e privilegi invariati (`STABLE`, `INVOKER`,
nessun `SET`, `COST 100`). Il rollback torna al corpo e al `COMMENT` di prima. `can_push_commessa` dell'ordine
non cambia: i suoi motivi sono scritti dalla capability, senza valori.

**pgTAP:** `vendite/test-capability-valori-marche-smistamento-v1`, da 12 a 18. I casi sono costruiti: l'ordine
in bozza, confermato ed evaso; l'offerta accettata con un servizio, una in bozza, e una riga che il vocabolario
della natura esclude; un inventario in bozza e uno confermato senza righe. Per ciascuno, il flag spento coi
valori e il suo contrasto (`[]`).

**Prova (2026-11-15, `scripts/prova_changeset.py` sullo scratch, in ROLLBACK).** L'estratto passa per intero e il
catalogo resta identico. Verdi: il pgTAP esteso (18), `test-ordine-stati-dal-vocabolario-v1` (24),
`test-fn-available-actions-offerta-v1` (19), `test-capability-documenti-interni-v1` (14),
`test-righe-ammesse-ai-passi-e-annullo-v1` (25), `test-capability-motivi-e-nessuna-azione-v1` (13).
⚠️ Mentre la prova girava Tid aveva già applicato `-79 … -81` (10:50 su dbdev, 10:51 sullo scratch), quindi la
corsa «senza» ha girato anch'essa sulle funzioni nuove: il confronto «prima/dopo» non c'è. Che i casi 13-18
distinguano lo si legge dal test: senza la chiave nuova `concat_ws` salta il `NULL` e la stringa non torna.
⚠️ **La prova gira da owner, e la RLS non la esercita.** Su dbdev, come `zeroerp_app` (Tid, 2026-11-15), il test si
fermava a 13/18: l'inventario era rifiutato dalla policy, perché il magazzino nasceva in una CTE della stessa
istruzione e la policy, che ne legge l'emittente con una funzione `STABLE`, non lo vedeva. Corretto: il magazzino
nasce in un'istruzione sua. Rilanciato come applicazione: 18/18 (Tid, 2026-11-15).

#### Richiesta al team FE, dopo il giro 6g-bis

| # | Che cosa | File |
| --- | --- | --- |
| FE-G4 | Nessuna frase da cambiare. `common.azione_reason.riga_non_ammessa` ha già `{0}` e `{1}`: oggi, nel tooltip di `can_push_contratto` e `can_genera_ordine` dell'offerta, escono vuoti, e con FE-G1 (`azioneDaFlag` passa `<flag>_reason_valori`) si riempiono. Le frasi di `vendite.ordini.data_consegna_confermata_reason.stato_non_ammette`, `vendite.ordini.genera_ddt_reason.stato_non_evadibile` e `magazzino.documenti_interni.registra_reason.*` non hanno segnaposti: i valori arrivano, e usarli resta una scelta del FE. Da controllare: il FE-G1 legge `_reason_valori` per **ogni** flag, non solo per `can_genera_reso` | `frontend/src/core/composables/useEntityCapabilities.js` (con FE-G1) |
