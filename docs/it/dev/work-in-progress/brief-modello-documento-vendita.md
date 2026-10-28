# Brief — Il modello del documento di vendita, scritto una volta

## ⏭️ Chi riparte — aggiornato al 2026-10-28 (giro 11, la fattura: DB tutto committato, `-01` … `-50`; il passaggio BE/FE del §15.8, di BE-1 … BE-3, FE-1, di «riporta in bozza» e di `azioni_permesse` committato su `dev/backend-tid`, §15.15; la stampa delle origini decisa, forma 6, richiesta al team DB, §15.16; K-S1 … K-S5 applicati e verdi, §15.17.1; BE-S1, BE-S2 fatti, §15.17.2; tocca a Tid, lo script K-S2. Giro 12, il listino: ricognizione e domande, §16)

**Riparte: Tid**, sul giro 11: **lo script una tantum K-S2** (`sql-una-tantum-copie-fattura-forma-6.sql`),
**subito**: il backend stampa in forma 6 (BE-S1, BE-S2 fatti e provati, §15.17.2), e finché lo script non gira le
copie degli emittenti 32 e 44 (template 77 e 2527, ancora in forma 5) non stampano. Poi il commit di BE-S1, BE-S2.
E sul giro 12 (la versione di listino, §16): le domande L-1 … L-5 e il via allo sviluppo. Il passaggio
BE/FE del giro 11 è committato (§15.15; suite Django sul DB provvisto 7013 test, vitest 988, verdi). Il **team DB**
ha in più richieste a priorità bassa: ritirare `E_COMMESSA_AZIONE_NON_AMMESSA` (§14.7); R-1 e R-2 (§14.8); il
lettore dello stato di cessazione (§11.7). **Tid**, coi dati `emetti_offerta`, `emetti_contratto`, `emetti_ordine`
ai profili su dbdev: letto il 2026-10-26, nessun profilo le ha, quindi in collaudo nessuno attiva o cessa un
contratto né conferma un ordine (§11.7). Giri 5-10: chiusi e committati (dettaglio nelle righe della tabella).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Bozza: il modello com'è oggi, le divergenze, le decisioni già prese | §2, §3 | — |
| 2 | ✅ **Tid** | M-1 … M-6, decise il 2026-10-24 | §4 | 1 |
| 2-bis | ✅ **Tid** | N-1 … N-3 (un documento nasce nel suo stato iniziale), decise il 2026-10-24 | §4-bis | 2 |
| 2-ter | ✅ team DB | Censimento di chi crea documenti gia' avanti (DB, backend, test Django, pgTAP), 2026-10-24 | §4-ter | 2-bis |
| 2-quater | ✅ **Tid** | P-1 … P-3, decise il 2026-10-24; e il modo di procedere (§5) | §4-ter | 2-ter |
| 2-quinquies | ✅ team DB | Primo giro scritto e provato: il BB della nascita su vendite e acquisti, 9 funzioni e 3 builder senza copie, 48 pgTAP portati, la richiesta al team BE | §4-quinquies | 2-quater |
| 2-sexies | ✅ **Tid** | Apply di `20261024-07` … `-25` e corsa pgTAP: verdi (2026-10-24); Q-1 decisa (B) | §4-quinquies | 2-quinquies |
| 2-sexies-bis | ✅ **Tid** | Q-2 … Q-4, decise il 2026-10-24 | §4-quinquies | — |
| 2-sexies-ter | ✅ team DB | Q-2 (tre builder estesi, non nuovi: Tid), Q-3, Q-4: `20261024-26` … `-28`, 28 pgTAP portati, presidi estesi | §4-sexies | 2-sexies-bis |
| 2-sexies-quater | ✅ **Tid** | Corsa pgTAP (come app) del secondo giro; R-1 (Q-3: la «definitiva» ferma nel lotto); i candidati e i residui | §4-sexies | 2-sexies-ter |
| 2-septies | ✅ team BE | Richiesta 1-5 fatta il 2026-10-24: policy e ripiego del codice nuovo, i 5 service e i loro repository senza lo stato iniziale, test e smoke portati alla nascita in bozza; revisione critica dello stesso giro (punto 6) | §4-quinquies | 2-sexies |
| 2-octies | ✅ team BE | Le sonde `richiedi_db_provvisto` sulle firme FINALI dei builder: le due della richiesta **e una terza** (articolo) rotta da prima; policy rigenerata; suite completa sul DB reale verde (2026-10-25) | §4-octies | 2-nonies |
| 2-octies-bis | ✅ **Tid** / team BE | BE-1 e BE-2 accettate da Tid e fatte (2026-10-25): il BB delle sonde fallisce sull'oggetto mancante; il runner del lotto tiene il codice del DB | §4-octies | 2-octies |
| 2-nonies | ✅ team DB / **Tid** | Terzo giro: debiti emersi chiusi, R-1 … R-6 e R-9 (`-29` … `-36`); applicati | §4-septies | 2-sexies-quater |
| 2-decies | ✅ team DB / **Tid** | Quarto giro: il pezzo comune (nessun cliente in più nei builder) e i builder delle fixture ripetute (`-37` … `-42`); applicati da Tid alle 23:50, corsa come app verde | §4-octies | 2-nonies |
| 3 | ✅ team DB | Il §2, corretto con le decisioni, diventa la guida `docs/it/guide/modello-documento-di-vendita.md`; le otto guide dei documenti rimandano lì (2026-10-25) | §6 | 2 |
| 3-bis | ✅ **Tid** | Rilettura della guida: le sei regole sono scritte come le ha decise (Tid, 2026-10-25: «sì, ok») | §6 | 3 |
| 4 | ✅ team DB / **Tid** · team BE | Giro 5 (bolla e reso): DB scritto, applicato e verde il 2026-10-25 (§7); tocca al BE (§7.6). Il piano: ogni documento portato al modello **tutto in una volta**, un documento per giro. ✅ Primo documento (Tid, 2026-10-25): **il DDT, col DDT d'acquisto** — il più vicino al modello; lì nascono i pezzi comuni di S-1 e S-2. S-1 (b) e S-2 (a) decise | §5, §6 | 3-bis |
| 4-bis | ✅ team BE | Giro 5 lato BE: §7.6 punti 1-5 (EMESSO solo da «Emetti», il 403 dalla riga del passaggio col BB `PassaggioDocumento`, codici, test DB); committato `4351164c1` | §7.9 | 4 |
| 4-bis-bis | ✅ **Tid** | Giro 6 = il preventivo; lettore in due pezzi, `fn_doc_stato_id` + `fn_doc_azione_passaggio` (2026-10-25) | §8 | 4-bis |
| 4-bis-ter | ✅ **Tid** | U-1 (a), U-2, U-3 come da proposta, e il via (2026-10-25) | §8.3 | 4-bis-bis |
| 4-bis-quater | ✅ team DB / **Tid** | Giro 6 scritto; `-37` … `-48` applicati da Tid (11:37); `-49` … `-52` scritti e provati in transazione; 22 pgTAP portati, regressione senza differenze | §8.4, §8.5 | 4-bis-ter |
| 4-bis-quinquies | ✅ **Tid** | Apply di `-49` … `-52` e corsa pgTAP: verdi (2026-10-25) | §8.4 | 4-bis-quater |
| 4-bis-quinquies-bis | ✅ team DB / **Tid** | Anticipati (Tid, 2026-10-25): concessioni trasferite a `emetti_preventivo` su dbdev (script del §8.9), `cambia_stato_preventivi` spenta nel CSV, migrate applicato | §8.9 | — |
| 4-bis-sexies | ✅ team BE | Richiesta §8.7 fatta: firma del verbo, 403 dalla riga (anche dalla pratica e su «Emetti»), lettori nuovi, rifiuto dell'emissione dal vocabolario su bolla, preventivo, contratto e ordine, controesempio. Non fatto il ritiro di `STATO_EMESSO`: manca il lettore del codice (richiesta al DB) | §8.10 | 4-bis-quinquies |
| 4-bis-sexies-bis | ✅ **Tid** | Commit del giro BE 6 (con la revisione critica, §8.10 punto 8) | §8.10 | 4-bis-sexies |
| 4-bis-sexies-ter | ✅ **Tid** | V-1 (lettore generico), V-2 (contratto, ordine e offerta nello stesso passaggio BE), V-3 (brief della nascita archiviato) | §8.11 | 4-bis-sexies |
| 4-bis-septies | ✅ team DB | Via di Tid (2026-10-25); giro DB di chiusura K-1 … K-6 scritto, provato in transazione su dbdev (8/8, presidio dei riferimenti morti 9/9) | §8.11 | 4-bis-sexies-ter |
| 4-bis-septies-bis | ✅ **Tid** | Apply di `20261025-70`, `-71` (dbdev, 15:27) e corsa pgTAP: verdi (2026-10-25) | §8.11 | 4-bis-septies |
| 4-bis-septies-ter | ✅ team DB | Censimento di cosa resta al cantiere, lato DB: elenco chiuso | §8.12 | 4-bis-septies-bis |
| 4-bis-septies-quater | ✅ **Tid** | W-1: l'ordine, **senza** l'ordine d'acquisto (acquisti tutti insieme, quando parte quel cantiere); ordine dei giri dopo: contratto, offerta, commessa, fattura, listino. W-2 e W-3: non ancora decise (W-2 torna come Z-3) | §8.12 | 4-bis-septies-ter |
| 4-bis-septies-quinquies | ✅ team DB | Giro 7, l'ordine: ricognizione, piano, domande | §9 | 4-bis-septies-quater |
| 4-bis-septies-sexies | ✅ **Tid** | Z-1 … Z-4 come da proposta, W-3 in un brief suo, via allo sviluppo | §9.3 | 4-bis-septies-quinquies |
| 4-bis-septies-septies | ✅ team DB / **Tid** | Giro 7 scritto (`-72` … `-82`, CSV), provato, applicato da Tid (15:59); 11 pgTAP portati, regressione letta | §9.4, §9.5 | 4-bis-septies-sexies |
| 4-bis-septies-octies | ✅ **Tid** | Migrazione applicata e corsa pgTAP verde (2026-10-25). Resta un dato: `emetti_ordine` ai profili su dbdev | §9.5, §9.6 | 4-bis-septies-septies |
| 4-bis-octies | ✅ team BE | Un passaggio solo, B-1 … B-6 del §8.11 e C-1 … C-6 del §9.6, fatto il 2026-10-25 | §9.7 | 4-bis-septies-bis |
| 4-bis-octies-bis | ✅ team BE | I due residui del §9.7: l'annullo dal vocabolario fatto; il «solo da DRAFT» sospeso su un difetto DB | §9.8 | 4-bis-octies |
| 4-bis-octies-ter | ✅ **Tid** | Commit del giro BE (`8023974de`, PR #1953); via al team DB per il difetto X → X (2026-10-26). Il dato `emetti_ordine` ai profili su dbdev: non verificato qui | §9.8 | 4-bis-octies-bis |
| 4-bis-octies-quater | ✅ team DB / **Tid** | Prima riga o guard di transizione: Tid sceglie la prima riga col codice comune (2026-10-26). Scritti `20261026-01` (X → X, `E_DOC_GIA_NELLO_STATO`) e `-02` (bolla, stato sconosciuto come i gemelli); 3 pgTAP estesi, regressione su 40 file senza differenze | §9.10 | 4-bis-octies-ter |
| 4-bis-octies-quinquies | ✅ **Tid** | Apply di `20261026-01`, `-02` e dei CSV degli errori; corsa pgTAP come app: verdi (2026-10-26) | §9.10 | 4-bis-octies-quater |
| 4-bis-octies-sexies | ✅ team BE | Richiesta del §9.10, punti 1-5: policy del codice nuovo, ritiro di `_assert_stato` e del controllo della bolla, test del secondo «Emetti» (2026-10-26) | §11.7 | 4-bis-octies-quinquies |
| 4-bis-nonies | ✅ **Tid** → team DB | Il via al giro 8: il contratto (ordine dei giri di W-1), 2026-10-26. Non aspetta il BE (§5) | §5 | 4-bis-septies-octies |
| 4-bis-nonies-bis | ✅ team DB | Giro 8, il contratto: ricognizione, piano, domande | §11 | 4-bis-nonies |
| 4-bis-nonies-ter | ✅ **Tid** | Y-1 … Y-4 come da proposta, e il via allo sviluppo (2026-10-26) | §11.3 | 4-bis-nonies-bis |
| 4-bis-nonies-quater | ✅ team DB / **Tid** | Giro 8 scritto (`-03` … `-13`, CSV) e provato in transazione; 18 pgTAP portati, 2 ritirati (Tid: 11 e 12 del sovrapposto), regressione su 68 file senza peggioramenti | §11.4, §11.5 | 4-bis-nonies-ter |
| 4-bis-nonies-quinquies | ✅ **Tid** | Apply del giro 8 e corsa pgTAP come app: verdi (2026-10-26). Il dato `emetti_contratto` ai profili su dbdev: non verificato qui | §11.5 | 4-bis-nonies-quater |
| 4-bis-nonies-sexies | ✅ team BE | Richiesta del §11.6 (sette punti), insieme a quella del §9.10 (2026-10-26); fuori elenco il messaggio della cessazione nel frontend e la pulizia dello smoke dei listini | §11.7 | 4-bis-nonies-quinquies |
| 4-bis-nonies-septies | ✅ **Tid** | Commit del passaggio BE (`fe041a1a1`, `0a08565be`, PR #1956), 2026-10-26 | §11.7 | 4-bis-nonies-sexies |
| 4-bis-nonies-septies-bis | **Tid** ⏭️ | Il dato `emetti_contratto` ed `emetti_ordine` ai profili su dbdev: letto il 2026-10-26, nessun profilo le ha | §11.7 | — |
| 4-bis-nonies-octies | team DB | Il lettore dello stato di cessazione (priorità bassa); poi il BE ritira `STATO_CESSATO` | §11.7 | — |
| 4-bis-decies | ✅ **Tid** → team DB | Il via al giro 9: l'offerta (ordine dei giri di W-1), 2026-10-26. Non aspetta il BE (§5) | §5 | 4-bis-nonies-quinquies |
| 4-bis-decies-bis | ✅ team DB | Giro 9, l'offerta: ricognizione, piano, domande; corretta la lettura dell'annullo del §8.12 (D-4) | §13 | 4-bis-decies |
| 4-bis-decies-ter | ✅ **Tid** | O-1 … O-6 come da proposta, e il via allo sviluppo (2026-10-26); D-N1 non entra nel giro | §13.3 | 4-bis-decies-bis |
| 4-bis-decies-quater | ✅ team DB | Giro 9 scritto (`-14` … `-28`, CSV) e provato in transazione; 25/25 il pgTAP nuovo, 24 pgTAP portati, regressione su 61 file senza peggioramenti | §13.4, §13.5 | 4-bis-decies-ter |
| 4-bis-decies-quinquies | ✅ **Tid** | Apply del giro 9 e corsa pgTAP come app: verdi (2026-10-26) | §13.7 | 4-bis-decies-quater |
| 4-bis-decies-sexies | ✅ team BE | Richiesta del §13.6 (nove punti) fatta il 2026-10-26: verbi, legami, 403 dalla riga, policy, frontend, test, doc | §13.8 | 4-bis-decies-quinquies |
| 4-bis-decies-sexies-bis | ✅ **Tid** | Commit del passaggio BE del giro 9 (il lettore `stato_id` ritirato, ok di Tid 2026-10-26): su `Tito-dev`, PR #1961 | §13.8 | 4-bis-decies-sexies |
| 4-bis-decies-septies-bis | team DB | Richiesta (priorità bassa, ok di Tid 2026-10-26): numero e link della revisione precedente nella finestra dell'annullo dell'offerta | §13.9 | — |
| 4-bis-decies-septies-ter | team DB | Richiesta (priorità bassa): dove la motivazione è AMMESSA sulla riga del passaggio, e il verbo dell'offerta rifiuta il resto (oggi la scrive su ogni passaggio) | §13.9 | — |
| 4-bis-decies-septies-quater | team DB | Proposta (§13.9): la guida del modello dichiara decisa l'asimmetria offerta/preventivo sulla revisione (scelta di Tid del 2026-07-16), col rimando | §13.9 | — |
| 4-bis-decies-septies | **Tid** | Il dato `emetti_offerta` (ed `emetti_contratto`, `emetti_ordine`) ai profili su dbdev | §13.7 | — |
| 4-bis-undecies | ✅ **Tid** → team DB | Il via al giro 10: la commessa, ricognizione (2026-10-26). Non aspetta il BE (§5) | §14 | 4-bis-decies-quinquies |
| 4-bis-undecies-bis | ✅ team DB | Giro 10, la commessa: ricognizione, piano, domande | §14 | 4-bis-undecies |
| 4-bis-undecies-ter | ✅ **Tid** | C-1 … C-4 (C-3: IN_ESECUZIONE si ritira, «riapri» → APERTA) e il via allo sviluppo (2026-10-26) | §14.3 | 4-bis-undecies-bis |
| 4-bis-undecies-quater | ✅ team DB | Giro 10 scritto (`-29` … `-36`, CSV) e provato in transazione; 20/20 il pgTAP nuovo, 21 pgTAP portati, regressione su 93 file senza peggioramenti | §14.4, §14.5 | 4-bis-undecies-ter |
| 4-bis-undecies-quinquies | ✅ **Tid** | Passo a mano del §14.4, apply del giro 10 e corsa pgTAP come app: verdi (2026-10-26), coi quattro file portati dopo la prima corsa e la guard d'uscita riscritta (§14.5) | §14.4, §14.5 | 4-bis-undecies-quater |
| 4-bis-undecies-quinquies-bis | ✅ **Tid** | I due passi per lo scratch da zero (`20261019-13`, `20261026-37`) applicati su dbdev (a vuoto) e ricostruzione dello scratch `zeroerp_ruoli` da zero passata; corsa pgTAP verde (2026-10-26/27) | §14.5 | 4-bis-undecies-quinquies |
| 4-bis-undecies-sexies | ✅ team BE | Richiesta del §14.6 (sette punti) fatta il 2026-10-27: firma, 403 dalla riga, difesa ritirata, IN_ESECUZIONE, test, doc; fuori elenco il gate del drawer | §14.7 | 4-bis-undecies-quinquies |
| 4-bis-undecies-septies | ✅ **Tid** | Commit del passaggio BE del giro 10 (PR #1963, su `Tito-dev`) | §14.7 | 4-bis-undecies-sexies |
| 4-bis-undecies-octies | ✅ **Tid** / team BE | Il parametro `permission` di `mapAvailableActionsToDrawerActions`: ritirato (ok Tid, 2026-10-27) | §14.7, §15.15 | 4-bis-undecies-sexies |
| 4-bis-undecies-nonies | team DB | Richiesta (priorità bassa): ritirare `E_COMMESSA_AZIONE_NON_AMMESSA` (`obsoleto_dal`); poi il BE toglie policy e ripiego | §14.7 | 4-bis-undecies-sexies |
| 4-bis-undecies-decies | ✅ team BE | Revisione del giro: regola del 1 sui sei documenti, BB `operatore_di_prova`; da provare e committare col §14.7 | §14.8 | 4-bis-undecies-sexies |
| 4-bis-undecies-undecies | team DB | Richieste (priorità bassa): R-1 `fn_crea_revisione_offerta` risponde 404 all'offerta che non c'è; R-2 lo stato d'accettazione nel vocabolario | §14.8 | — |
| 4-bis-duodecies | ✅ **Tid** → team DB | Il via alla ricognizione del giro 11: la fattura (2026-10-27); come lavora (il lotto guida gli stati e la stampa) | §15.1 | — |
| 4-bis-duodecies-bis | ✅ team DB | Giro 11: ricognizione (quattro assi di stato, scrittori, azioni esistenti) | §15.2 | 4-bis-duodecies |
| 4-bis-duodecies-ter | ✅ **Tid** | F-0 (D-G1 = c) … F-5 (D-N1 nel giro, con un pezzo standard) | §15.3 | 4-bis-duodecies-bis |
| 4-bis-duodecies-quater | ✅ **Tid** | Q-F1 … Q-F6 confermate come da proposta (2026-10-27) | §15.4 | 4-bis-duodecies-ter |
| 4-bis-duodecies-quinquies | ✅ team DB | Piano del giro 11, con P-1 e P-2 | §15.5 | 4-bis-duodecies-quater |
| 4-bis-duodecies-sexies | ✅ **Tid** | Il via allo sviluppo del giro 11, P-1 e P-2 come da proposta (2026-10-27) | §15.5 | 4-bis-duodecies-quinquies |
| 4-bis-duodecies-septies | ✅ team DB | Giro 11, lo stato di lotto e fattura: `20261027-01` … `-20` e i CSV, provati in transazione sullo scratch; 279 + 202 pgTAP prima/dopo, 16 portati, uno nuovo (21/22, il 4 dopo il migrate) | §15.6, §15.7 | 4-bis-duodecies-sexies |
| 4-bis-duodecies-octies | ✅ **Tid** | Il passo a mano su dbdev (i legami alle azioni ritirate), poi apply e corsa pgTAP come app | §15.7 | 4-bis-duodecies-septies |
| 4-bis-duodecies-nonies | ✅ **Tid** | Q-F6 = (b), i documenti a monte; Q-F5 = la vista DB (2026-10-27) | §15.9 | — |
| 4-bis-duodecies-decies | ✅ team DB | Il piano del lettore delle origini (D-G1) e del registro delle azioni di riga, con P-3 | §15.10 | 4-bis-duodecies-nonies |
| 4-bis-duodecies-duodecies | ✅ **Tid** | Il via ai due pezzi del §15.10, `citato_in_fattura`, P-3 come da proposta; e i sette pgTAP del giro 10 (2026-10-27) | §15.10 | 4-bis-duodecies-decies |
| 4-bis-duodecies-terdecies | ✅ team DB | Le origini (dalle righe fatturate, scostamento dichiarato) e il registro delle azioni di riga: `20261027-21` … `-25`, due pgTAP nuovi; provati in transazione | §15.11 | 4-bis-duodecies-duodecies |
| 4-bis-duodecies-quaterdecies | ✅ **Tid** | Apply di `20261027-21` … `-25`, pgTAP verdi, nessuna regressione (2026-10-27) | §15.11 | 4-bis-duodecies-terdecies |
| 4-bis-duodecies-sexdecies | ✅ **Tid** | Q-F7: la nota cita fattura e reso, e il DDT e l'ordine del reso; il via a P-F7 (2026-10-27) | §15.11 | 4-bis-duodecies-quaterdecies |
| 4-bis-duodecies-septendecies | ✅ team DB | P-F7 scritto: `20261027-26`, il CSV delle sorgenti, un pgTAP nuovo; provato in transazione | §15.11 | 4-bis-duodecies-sexdecies |
| 4-bis-duodecies-octodecies | ✅ **Tid** | Apply di `20261027-26` col CSV `sorgenti.csv`, pgTAP verdi, nessuna regressione (2026-10-27) | §15.11 | 4-bis-duodecies-septendecies |
| 4-bis-duodecies-novodecies | ✅ **Tid** | Il commit del giro DB 11 fino a `-26`: PR #1964; `-27` … `-39` committati su `dev/db-tid` (`6455df27f`), mergiati in `dev/backend-tid` | §15 | 4-bis-duodecies-octodecies |
| 4-bis-duodecies-novodecies-bis | ✅ team DB | Revisione delle guide contro il giro 11: guide, linee guida SQL, pagine manuali; `-27`, `-28` (soli commenti) provati in transazione | §15.12 | 4-bis-duodecies-octodecies |
| 4-bis-duodecies-vicies-nonies | ✅ **Tid** | Apply di `-27`, `-28` (2026-10-27) | §15.12 | 4-bis-duodecies-novodecies-bis |
| 4-bis-duodecies-unvicies | ✅ team DB | Richiesta BE: lo stato iniziale dalla testata, `20261027-29` … `-39` (K-3 nello stesso giro, via di Tid), un pgTAP nuovo; provati in transazione, regressione su 178 file invariata | §15.13 | 4-bis-duodecies-vicies-nonies |
| 4-bis-duodecies-duovicies | ✅ **Tid** | Apply di `-29` … `-39`, pgTAP verdi (2026-10-27) | §15.13 | 4-bis-duodecies-unvicies |
| 4-bis-duodecies-quinvicies | ✅ **Tid** | Richiesta BE dei passaggi permessi per riga: D-1 … D-4 come da proposta, via (2026-10-27) | §15.14 | — |
| 4-bis-duodecies-sexvicies | ✅ team DB | `20261027-40` … `-50`, un pgTAP nuovo; provati in transazione, regressione su 78 file invariata | §15.14 | 4-bis-duodecies-quinvicies |
| 4-bis-duodecies-septvicies | ✅ **Tid** | Apply di `-40` … `-50`, pgTAP verdi (2026-10-27) | §15.14 | 4-bis-duodecies-sexvicies |
| 4-bis-duodecies-trevicies | ✅ **Tid** | Il commit del giro DB 11 (`20261027-27` … `-39`, pgTAP, doc, brief): `6455df27f`, mergiato in `dev/backend-tid` | §15 | 4-bis-duodecies-duovicies |
| 4-bis-duodecies-novvicies | ✅ **Tid** | Il commit del giro DB 11, il resto: `-40` … `-50` in `241279d23` (PR #1966), in `dev/backend-tid` col fast-forward su `Tito-dev` (2026-10-27) | §15 | 4-bis-duodecies-septvicies |
| 4-bis-duodecies-octvicies | ✅ team BE → FE | `azioni_permesse` per riga della lista dei lotti, poi il kebab che lo legge (fail-closed): fatto e committato il 2026-10-27 | §15.14, §15.15 | 4-bis-duodecies-septvicies |
| 4-bis-duodecies-quattuorvicies | ✅ team BE | Lo stato iniziale dalla testata: `stato_iniziale(testata)` e «riporta in bozza» dalla riga (2026-10-27) | §15.13, §15.15 | 4-bis-duodecies-duovicies |
| 4-bis-duodecies-quindecies | ✅ team BE → FE | BE-1 (il dettaglio; la stampa ferma su una decisione), BE-2, BE-3, FE-1 (2026-10-27) | §15.15 | 4-bis-duodecies-quaterdecies |
| 4-bis-duodecies-undecies | ✅ team BE | La richiesta del §15.8 (sette punti), tranne il 403 di «riporta in bozza» (2026-10-27) | §15.15 | 4-bis-duodecies-octies |
| 4-bis-duodecies-vicies-octies | ✅ team DB | Il lettore dello stato iniziale per testata (`script.fn_doc_stato_iniziale_id`, `20261027-29`), applicato e verde | §15.13 | 4-bis-duodecies-undecies |
| 4-bis-duodecies-vicies-bis | ✅ **Tid** | La stampa delle origini: **forma 6** (D-S1, 2026-10-27), non `origini` accanto a `origine` | §15.15, §15.16 | 4-bis-duodecies-quindecies |
| 4-bis-duodecies-vicies-ter | ✅ team BE | Il commit del passaggio BE/FE del giro 11 su `dev/backend-tid`, su richiesta di Tid (2026-10-27) | §15.15 | 4-bis-duodecies-undecies |
| 4-bis-duodecies-vicies-quater | ✅ team BE | «Riporta in bozza» dalla riga del passaggio (`stato_del_modello="iniziale"`), 2026-10-27 | §15.13, §15.15 | 4-bis-duodecies-duovicies |
| 4-bis-duodecies-vicies-septies | ✅ team BE | Il builder della fattura in forma 6 (`origini` al posto di `origine`, BE-S1) e la scheda Critiche dalla vista (BE-S2), riavvio (2026-10-28) | §15.16.3, §15.17.2 | 4-bis-duodecies-trigies-bis |
| 4-bis-duodecies-trigies-septies | **Tid** ⏭️ | Lo script una tantum K-S2 sulle copie degli emittenti, subito dopo il riavvio del BE; poi il commit di BE-S1, BE-S2 | §15.16.3, §15.17.2 | 4-bis-duodecies-vicies-septies |
| 4-bis-duodecies-trigies | ✅ team DB | Ricognizione e piano della richiesta del §15.16: K-S1 … K-S5, la risposta a D-S2 = (b), la richiesta BE-S1, BE-S2 (2026-10-28) | §15.17 | 4-bis-duodecies-vicies-bis |
| 4-bis-duodecies-trigies-ter | ✅ **Tid** | D-S2 = (b) e via allo sviluppo di K-S1 … K-S5 (2026-10-28) | §15.17 | 4-bis-duodecies-trigies |
| 4-bis-duodecies-trigies-quater | ✅ team DB | K-S1 … K-S5 scritti e provati: `20261028-01`, `-02`, script una tantum, 2 pgTAP; regressione 39 file invariata (2026-10-28) | §15.17.1 | 4-bis-duodecies-trigies-ter |
| 4-bis-duodecies-trigies-bis | ✅ **Tid** | Apply di `20261028-01`, `-02` (2026-10-28, 12:18) e pgTAP come app: verdi; poi la sequenza del §15.16.3 (riavvio BE, script una tantum) | §15.16.3, §15.17 | 4-bis-duodecies-trigies-quater |
| 4-bis-duodecies-vicies-sexies | ✅ **Tid** → team DB | Il lettore `script.fn_doc_azioni_permesse` (scelta di Tid, 2026-10-27): fatto dal team DB, §15.14; il seguito BE/FE è 4-bis-duodecies-octvicies | §15.14, §15.15 | — |
| 4-bis-duodecies-vicies-quinquies | ✅ team DB | Domanda D-S2: la superficie delle segnalazioni del lotto (scheda Critiche) fuori dal registro; risposta (b), la vista le copre: confermata da Tid e scritta (`-02`, 2026-10-28) | §15.16, §15.17 | — |
| 4-bis-duodecies-trigies-quinquies | ✅ team DB | Giro 12, la versione di listino: ricognizione, piano, domande L-1 … L-5 (2026-10-28) | §16 | via di Tid |
| 4-bis-duodecies-trigies-sexies | **Tid** ⏭️ | L-1 … L-5 e via allo sviluppo del giro 12 | §16.3 | 4-bis-duodecies-trigies-quinquies |
| 4-ter | ✅ team DB | Il lettore codice → id dello stato e la domanda intera, la colonna `emissione` col suo lettore: fatti nel giro 6 (`-37` … `-41`) | §8.4 | 4-bis |
| 4-quater | ✅ team BE | Ritirata la composizione SQL del repository, sui lettori nuovi; `STATO_EMESSO` passa a 4-bis-octies | §8.10 | 4-ter |
| 5 | ✅ **Tid** | Fermo dei temi trasversali **allentato** (2026-10-25, scelta C): ammesso il tema che poggia su un pezzo comune già fatto, fermo quello da ricopiare documento per documento; scritto in PROJECT_CONTEXT | — | 3-bis |
| 5-bis | **Tid** | Ereditati dalla grammatica unica (chiusa il 2026-10-25): D-G1 ✅ deciso (c) nel giro 11 (§15.3); D-G2, la prova a video del lotto 2b | §10 | — |
| 5-ter | ✅ **Tid** → team DB + FE | Ereditato dalla nota di credito (2026-10-26): D-N1, le azioni per riga: nel giro 11, con un pezzo standard (F-5, 2026-10-27); la forma del pezzo è Q-F5 | §12, §15 | — |

Decisioni aperte di Tid: L-1 … L-5 del giro 12 (§16.3). Da committare: il §15.17 del brief e il giro K-S1 … K-S5, applicato e verde, e il §16 (`20261028-01`, `-02`, lo script una tantum, due pgTAP, una pagina manuale). W-3 è passata a [brief-db-scadenza-preventivi](brief-db-scadenza-preventivi.md) (E-1 … E-3). Da sapere (§8.10, §9.7, §11.7): il cambio stato generico dell'ordine rifiuta CONFERMATO (M-2); `POST /ordini/<id>/conferma/` non c'è più (Z-2); senza `emetti_ordine` nessuno conferma un ordine, e senza `emetti_contratto` nessuno attiva o cessa un contratto (su dbdev nessun profilo le ha, letto il 2026-10-26). Committati: il passaggio BE/FE del giro 11 (§15.15, `dev/backend-tid`, 2026-10-27), il giro DB 11 (fino a `-26` PR #1964; `-27` … `-39` in `6455df27f`; `-40` … `-50` in `241279d23`, PR #1966; tutto in `dev/backend-tid`), il passaggio BE del giro 10 (§14.7, §14.8, `7901c668a`, PR #1963), il giro DB 10 coi due passi per lo scratch da zero (PR #1962), il passaggio BE del giro 9 (§13.8, PR #1961), il giro DB 9 (`52e18d887`, PR #1960), il giro BE del §9.10 e del §11.6 (`fe041a1a1`, `0a08565be`, PR #1956), il §13 del brief (`a1fd65979`), il giro DB del §9.10 e il giro 8 (`7feb19970`, PR #1955), il giro BE del §9.7 … §9.9 (`8023974de`), il giro DB del §8.11 e il giro 7 (`2f66ca7bc`), il giro BE 6 (`dad26c37b`), il giro BE 5 (`4351164c1`), il giro DB 5 (`c3e34be02`), i giri 2-4 lato DB (`498cc8275`).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-21. **A chi:** Tid; poi team DB e BE.
> **Origine:** D2 e D3 di [brief-be-verifica-documentazione-api](../work-done/brief-be-verifica-documentazione-api.md)
> (azioni di processo mancanti fra gemelli; permesso del cambio stato del DDT). Analizzandole sono
> uscite due proposte che, senza saperlo, contraddicevano una decisione viva e ne revocavano
> un'altra (§3.2). Tid: «non mi sto più fidando… una volta in un modo, poi in un altro, poi si torna
> al precedente». Da qui la ricostruzione della storia (§1) e questo brief.
> **Brief vicini verificati:**
> [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md)
> (stato iniziale e verbo: candidato a confluire qui, M-6);
> [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md) (solo i nomi dei
> tipi: resta suo); [brief-db-magazzino-tutte-le-scritture-dal-verbo](brief-db-magazzino-tutte-le-scritture-dal-verbo.md)
> (magazzino; rimanda «`vendite`, brief suo»: è **questo**).

---

## 1. Perché questo brief — i fatti, con la data

Ricostruzione del 2026-10-21 su git, brief chiusi e guide (finestra 2026-09-01 → 2026-10-21).
Sono fatti datati: servono a capire, non decidono la forma (Regola zero).

* **I ritorni indietro veri sono pochissimi** (1-3: partite merce per riga, ritirata lo stesso
  giorno per prestazioni; icona e severity nelle capability, aggiunte ad aprile e tolte il 27-28/09;
  la firma con `%TYPE` persa e rimessa). Nessun brief della finestra ha disfatto il lavoro di un
  altro.
* **La sensazione di girare in tondo ha un'altra causa: ogni concetto del documento esiste in una
  copia per documento.** 11 funzioni di capability (`script.fn_available_actions_*`), 11 guard di
  transizione, 8 verbi d'annullo (`fn_annulla_*`). Ogni regola nuova che vale per tutti i documenti
  va ricopiata in 6-9 posti.
* Nella finestra sono arrivati **27 temi trasversali** (perimetro emittente, congelamento prezzi,
  icone, fuso aziendale, cache dei piani, indirizzi, annullo con legami, testata dopo l'emissione,
  articoli ammessi, grammatica unica, modelli standard…), ciascuno applicato **un documento alla
  volta**: il 61% dei changeSet sui documenti. `fn_available_actions_offerta` è stata riscritta 12
  volte, ogni volta per una ragione diversa.
* **Non esiste un documento che fissi il modello comune.** Ci sono sei guide per documento
  (`gestione-preventivi.md`, `-ordini`, `-ddt`, `-contratti`, `-offerte-commerciali`, `-commesse`)
  che si dichiarano «gemelle», ma la gemellanza non è scritta da nessuna parte.

Rimedio deciso da Tid il 2026-10-21: il fermo dei temi trasversali (PROJECT_CONTEXT), la regola
«un tema, un brief» (AGENTS.md) e questo modello, scritto **una volta**.

---

## 2. Il modello com'è oggi (bozza della guida)

> Descrive lo stato attuale. Dove i documenti fanno in modo diverso, la differenza è nel §3.

### 2.1 Stati e transizioni

* Ogni documento ha un vocabolario di stati (`config.stati_doc_*`) e una **matrice delle
  transizioni** in tabella (`config.transizioni_stati_*`): una riga = un passaggio ammesso.
* Un trigger `trgfn_*_guard_transizione` rifiuta ogni passaggio che non è nella matrice.
* La stessa matrice, con il suo `meta` (`action_key`, `label_key`, `requires_confirm`, `manuale`),
  alimenta i bottoni: la funzione di capability del documento la legge e dice quali azioni sono
  disponibili e perché le altre sono spente.

### 2.2 Chi scrive lo stato: il verbo

* Direzione decisa il 2026-09-24 (D-1/D-2 di
  [brief-db-permesso-nel-verbo-di-scrittura](../work-done/brief-db-permesso-nel-verbo-di-scrittura.md),
  guida `architettura-permessi-e-autorizzazioni.md` §7.4): **una scrittura = un verbo**. I domini
  nuovi nascono così; quelli esistenti ci passano «quando un cantiere tocca le loro scritture».
* Per `vendite` il passaggio era rimandato a «un brief suo», mai scritto: è questo.

### 2.3 Chi può: il permesso

* Le operazioni CRUD chiedono il livello sull'area; le operazioni di **processo** (emetti, cambia
  stato, annulla, genera…) chiedono un'**azione di processo** (`config.azioni_processo`).
* La regola ha **una sede sola**, nel DB (`script.fn_check_azione_processo`), e **due punti in cui
  si applica**, voluti (guida §7.4, «il backend chiede, non decide due volte»): l'endpoint
  (`post_permission`, risponde 403 subito) e il verbo (`script.fn_guard_azione`).

### 2.4 L'emissione

* L'emissione è il passaggio che dà il numero e, dove il documento si stampa, genera il PDF
  (rotta `/emetti/`, fabbrica `build_documenti_sorgente_views`).

### 2.5 L'annullo

* Ogni documento ha un verbo d'annullo; un documento con **legami** a valle si annulla solo se chi
  conferma dichiara quanti legami ha visto (guard comune `trgfn_doc_guard_annullo_con_legami`,
  [brief-db-annullo-documento-con-legami](../work-done/brief-db-annullo-documento-con-legami.md)).

---

## 3. Dove i documenti divergono oggi

### 3.1 Tabella per documento (censimento del 2026-10-21)

| Documento | Cambio stato | Matrice | Azione di processo | Emissione | Annullo |
| --- | --- | --- | --- | --- | --- |
| Preventivo | verbo `fn_cambia_stato_preventivo` (senza guard d'azione) | tabella | `cambia_stato_preventivi`, solo backend | solo da `/emetti/` | `fn_annulla_preventivo` → verbo generale |
| Contratto | UPDATE dal backend | **nel codice del trigger**; la tabella la legge solo la capability | nessuna | solo da `/emetti/` | `fn_annulla_contratto`, UPDATE dentro di sé |
| Offerta | UPDATE dal backend; gli stati di partenza ripetuti in Python | tabella (nome fuori serie `stati_doc_offerte_transizioni`) | nessuna | `/emetti/` | da ACCETTATA via guard (`fn_check_offerta_annullabile`), forma diversa dall'annullo con legami |
| Ordine | UPDATE dal backend | tabella | nessuna | `/emetti/`, ma `/conferma/` e `cambia-stato` accettano CONFERMATO (scelta del 2026-06-05) | `fn_annulla_ordine`, UPDATE dentro di sé |
| DDT | verbo `fn_cambia_stato_ddt` per ogni transizione (dal 2026-10-13) | tabella | `emetti_ddt` (emissione, annullo dell'emesso) e `registra_magazzino` (consegna di un trasferimento): **nel corpo del verbo**; emissione controllata anche dal backend | `/emetti/`, ma `cambia-stato` accetta EMESSO (copiato dall'ordine) | `fn_annulla_ddt` → verbo generale |
| Reso | verbi `fn_conferma_reso` / `fn_annulla_reso` | tabella | `conferma_reso`, backend + verbo | conferma | verbo |
| Commessa | verbo `fn_cambia_stato_commessa` (senza guard d'azione) | tabella | `cambia_stato_commessa`, solo backend | push | `fn_annulla_commessa` → verbo generale |
| Versione di listino | UPDATE dal backend | **nel codice del trigger** e ricopiata in Python (`_validate_versione_state_transition`); stato testo con CHECK, senza vocabolario | nessuna | — | — |
| Fattura | funzioni della pipeline; stato del lotto con UPDATE | tabella | azioni della pipeline, solo backend | pipeline | reset del lotto |

Fuori vendita, stessa domanda: pagamenti (stato di distinte e righe, abbinamenti, sistemazioni:
nessuna azione; i verbi di registrazione senza guard) e magazzino (conferma/annullo dei documenti
interni: nessuna azione; la registrazione col guard nel verbo).

### 3.2 Due proposte del 2026-10-21 ritirate, e perché

* **«Il backend toglie `post_permission`, niente controllo doppio»**: contraddiceva §7.4 della
  guida dei permessi, decisione viva. Ritirata.
* **«EMESSO solo da `/emetti/` anche per il DDT»**: non è una regola nuova, **revoca** l'opzione (i)
  di [brief-ordini-stampa](../work-done/brief-ordini-stampa.md) §6.2 (2026-06-05), che il DDT ha
  copiato il 2026-07-11. Torna come decisione M-2.

### 3.3 Altro emerso dal censimento

* Azioni a catalogo che nessuno usa: `genera_fattura`, `approva_fattura`, `emetti_fattura`;
  `approva_rimessa` già spenta.
* Pratica: il cambio stato generico (`cambia_stato_pratica`) accetta ogni passaggio della matrice,
  compreso APERTA ↔ SOSPESA: si potrebbe sospendere senza `sospendi_pratica` e senza la riga di
  sospensione. **Da verificare**: non è ancora provato.
* Il commento di `listini_service._validate_versione_state_transition` cita un brief che non esiste
  (`brief-db-listini-stato-chiusa-sync.md`).

---

## 4. Decisioni per Tid — una volta, per tutti i documenti

| # | Domanda | Oggi | Note |
| --- | --- | --- | --- |
| M-1 | Ogni cambio di stato passa da un verbo DB con il guard d'azione (completare D-1/D-2 su vendite)? | 4 modelli diversi (§3.1) | ✅ **Deciso da Tid il 2026-10-24: A** — sì, come cantiere, un documento per giro e tutto intero; **dopo** M-2 … M-5, che dicono come dev'essere fatto il verbo |
| M-2 | L'emissione si fa **solo** da `/emetti/` (con PDF) per tutti i documenti che si stampano? | sì per preventivo e contratto (2026-05-28); no per ordine (2026-06-05) e DDT (copiato) | ✅ **Deciso da Tid il 2026-10-24: A** — solo da `/emetti/`, per tutti: numero e PDF nascono insieme, in una transazione (il DDT prende il numero al passaggio a EMESSO, trigger `trg_ddt_z10_gen_numero_emesso`). **Revoca** l'opzione (i) del 2026-06-05 (ordine) e la copia del DDT (2026-07-11). Primo passo del cantiere: censire chi emette o conferma senza passare da `/emetti/` (import, passaggi da altri documenti) e decidere per ognuno |
| M-3 | L'azione richiesta da un passaggio si dichiara **sulla riga della matrice**, letta dal verbo, dall'endpoint e dalla capability? | nel DDT è scritta nel corpo del verbo; altrove solo sulla view | ✅ **Deciso da Tid il 2026-10-24: A** — l'azione sta sulla riga del passaggio (riga senza azione = solo il permesso sul documento); la leggono il verbo (controllo), il backend (403 subito, senza deciderla da sé: il doppio punto di applicazione del 2026-09-24 resta) e le capability (bottone nascosto). Motivo di Tid: un punto unico è ciò che rende configurabili i permessi; sparso in nove documenti sarebbe ingestibile. **Supera** «gate per `action_key` nel service» (2026-07-27) e «permesso fuori dalle capability» (2026-08-04). Risponde a D3 |
| M-4 | Quante azioni per documento: una «cambia stato X» (come preventivo e commessa) o separate (emetti / annulla come DDT e reso)? | miste | ✅ **Deciso da Tid il 2026-10-24: A** — per ogni documento UNA azione sui passaggi pesanti (emissione e annullo di un emesso), «chi fa disfa», come DDT e reso; gli altri passaggi (spedito, accettato, rifiutato…) chiedono solo il permesso sul documento. **Il preventivo non fa eccezione** (Tid): accetta e rifiuta perdono `cambia_stato_preventivi`; lo stesso vale per la commessa. Separare l'annullo dall'emissione, se servira', e' un cambio di riga (M-3), non un cantiere |
| M-5 | Le matrici scritte nel codice (contratto, versione di listino) passano in tabella, e le copie Python si ritirano? | contratto e listino fuori dal modello | ✅ **Deciso da Tid il 2026-10-24: A** — il guard del contratto legge `config.transizioni_stati_contratti` (gli IF si ritirano); la versione di listino prende vocabolario degli stati e matrice dei passaggi come gli altri; si ritirano le copie Python (`listini_service._validate_versione_state_transition`, gli stati di partenza di `offerte_service._cambia_stato_manuale`). Condizione di M-3: senza righe in tabella l'azione non ha dove stare. Si fa nel giro del documento (M-1) |
| M-6 | [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md) confluisce qui? | aperto, non iniziato, stesso tema (stato e verbo) | ✅ **Deciso da Tid il 2026-10-24: A** — confluisce (§4-bis). Nascere già avanti e' un passaggio «dal nulla» che nessuna matrice ammette. Va **all'inizio** del cantiere: chiude un buco gia' provato (la bolla emessa, numerata e vuota) |

### 4-bis. Confluito: un documento nasce nel suo stato iniziale (ex D32, M-6)

Da [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md)
(2026-10-13), confluito il 2026-10-24. Il caso, la prova e il censimento da fare restano scritti
là (§1-§3); le decisioni si prendono qui.

* **Il caso.** Le regole per uscire dalla bozza stanno tutte sul passaggio di stato (`BEFORE
  UPDATE`). Nessuna dice in che stato un documento puo' NASCERE: un `INSERT` gia' avanti le salta.
  Provato il 2026-10-13 sulla bolla: nasce EMESSA, numerata e senza righe, e dopo le righe non si
  aggiungono piu'.
* **Le sue decisioni**, ora di questo brief:

| # | Domanda | Note |
| --- | --- | --- |
| N-1 | La regola: (a) un documento nasce solo nello stato iniziale e il resto passa dal verbo; (b) all'INSERT si applicano le condizioni della transizione dall'iniziale allo stato chiesto | ✅ **Deciso da Tid il 2026-10-24: (a)** — nasce solo nello stato iniziale (letto dal vocabolario degli stati, non scritto nel codice); chi ha bisogno di un documento gia' avanti lo crea in bozza e chiama il verbo nella stessa transazione. Coerente con M-1; (b) avrebbe due copie dei controlli. Prima: il censimento di §3 del brief d'origine (funzioni DB, backend, fixture pgTAP → `dbops.fn_pgtap_porta_a_stato`) |
| N-2 | Il perimetro e l'ordine | ✅ **Deciso da Tid il 2026-10-24: A** — **primo giro del cantiere**, su tutti i documenti con la matrice dei passaggi insieme: UNA funzione (building block) che legge lo stato iniziale dal vocabolario di ogni documento, montata su ciascuno. Non e' una regola ricopiata nove volte (la causa del §1): e' una sede sola. Prima, il censimento su tutti i documenti |
| N-3 | Il codice | ✅ **Deciso da Tid il 2026-10-24: A, un codice unico** — `E_DOC_STATO_INIZIALE_NON_VALIDO` (nome di Tid: dice quale regola e' violata; nessun codice simile nel catalogo, verificato), classe **TECNICO**: nessuna maschera crea un documento gia' avanti, e' un difetto di chi scrive. Frase che dice qual e' lo stato giusto, coi nomi che legge l'operatore (etichette, non codici di colonna): «Il %s non può nascere nello stato %s: un documento nuovo nasce in %s.». ⚠️ Se il censimento trova un'API che accetta lo stato dal client in creazione, li' e' DATO_ERRATO col campo `stato`, dichiarato |

### 4-ter. Censimento: chi crea un documento, e in che stato (2026-10-24)

Letto dal codice (corpi delle funzioni su dbdev, `backend/`, `db/pgtap/`), non dai dati. Perimetro:
le testate che hanno un vocabolario di stati in tabella — preventivo, offerta, contratto, ordine,
DDT, reso, commessa, fattura di vendita; e `acquisti.ordini` / `acquisti.ddt`, che usano gli stessi
vocabolari degli ordini e dei DDT di vendita.

**Scrittori DB: nessuno crea un documento già avanti.** Le 11 funzioni che inseriscono una testata
nascono tutte nello stato iniziale: `fn_create_contratto`, `fn_push_offerta_a_contratto`,
`fn_genera_ordine_da_offerta`, `fn_push_preventivo_a_ordine`, `fn_genera_ddt_da_ordine`,
`fn_genera_ddt_riconsegna`, `fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`,
`fn_get_or_create_fattura_header`, `fn_get_or_create_commessa` (dal DEFAULT di colonna) e
`script.fn_scrivi_riga_da_jsonb` (lo usa `fn_create_contratto`). Nessuno scrittore di `acquisti`.

**Backend: nessuna API accetta lo stato dal client in creazione** (`CREATE_KEYS_*` di ordini, DDT,
resi, offerte, preventivi, contratti). Il caso DATO_ERRATO di N-3 non si presenta. Lo stato
iniziale lo scrive il service, cercandolo **per nome** (`_STATO_BOZZA`, `StatoOfferta.BOZZA`,
`get_stato_bozza_id`) in cinque service; le versioni di listino nascono `BOZZA` (DEFAULT, e
letterale nel clone).

**Lo stato iniziale è scritto in 16 posti, e nessuno lo legge dal vocabolario:** i letterali `'DRAFT'`/
`'BOZZA'` nelle funzioni DB, i 5 service, il DEFAULT `1` (un id) di `vendite.commesse`. Il
vocabolario non lo dichiara: `fase = 'APERTO'` cade oggi su una riga sola per vocabolario, ma
nessun vincolo lo garantisce e la colonna dice un'altra cosa (la frontiera della genealogia).
Diversi pgTAP lo trovano come «il primo per id» o «il primo per `ordine`»: funziona per caso,
come dice la Regola zero. → **P-1**.

**`vendite.fatture.stato_doc_fiscale_id` è nullable e senza DEFAULT.** Una fattura può nascere
senza stato: lo fanno 27 INSERT pgTAP e 4 test Django di `pagamenti`. Le altre sette testate hanno
la colonna NOT NULL. → **P-2**.

**pgTAP: 52 file creano almeno un documento già avanti** (contratti 10, preventivi 17,
fatture 12, offerte 8, commesse 7, ordini 4; un file può contare per più documenti). Con la regola
diventano rossi.

* **Tre builder** fanno l'INSERT direttamente nello stato chiesto: `dbops.fn_pgtap_crea_ordine`,
  `fn_pgtap_crea_preventivo`, `fn_pgtap_crea_fattura`. Si riscrivono come
  `fn_pgtap_crea_contratto`, che crea in DRAFT e poi fa il passaggio, cioè la forma di N-1. I loro
  chiamanti fuori bozza: i tre presidi `dbops/test-fn-pgtap-crea-*` e
  `pagamenti/test-sistemazione-annullo-riporto.sql`.
* **`dbops.fn_pgtap_porta_a_stato`** conosce solo ordine e preventivo: va esteso a tutti i
  documenti, leggendo vocabolario e matrice. Passare dalla matrice vuol dire soddisfare le
  condizioni d'uscita dalla bozza (righe, indirizzi, causale…). È il lavoro grosso del giro: un
  preventivo «EMESSO» di fixture oggi nasce vuoto, e dovrà avere quello che un'emissione vera
  pretende.
* Un test **fissa il comportamento di oggi**:
  `vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` riga 288 fa nascere un contratto
  ATTIVO e si aspetta `23P01`. Con la regola l'errore diventa quello di N-3.

I 52 pgTAP, per documento:

| Documento | File (sotto `db/pgtap/`) |
| --- | --- |
| Contratto | `dbops/test-fn-apply-chiusura-scadenze-v1`, `vendite/contratti/test_fn_successione_contratti`, `vendite/test-contratti-guard-transizione-stato-v1`, `vendite/test-contratto-attiva-spento-se-sovrapposto-v1`, `vendite/test-fn-list-contratti-da-pushare-v1`, `vendite/test-fn-resolve-iva-riga`, `vendite/test-testata-dopo-emissione-rdb-v1`, `vendite/test-vw-dash-aperto-v1`, `vendite/test-vw-dash-backlog-v1`, `vendite/test-vw-dash-fatturazione-v1` |
| Preventivo | `dbops/test-fn-pgtap-crea-preventivo-v1`, `pratiche/test-guida-avanza-esito-proiettato`, `pratiche/test-proiezione-stato-sorgente`, `pratiche/test-reconcile-tie-break-flusso-origine`, `script/test-fn-available-actions-preventivo-v1`, `script/test-trgfn-default-emittente-fiscale-v1`, `vendite/test-emissione-mirata-gruppi-fatturabili-v1`, `vendite/test-fatturazione-immediata-simmetria-sorgenti-v1`, `vendite/test-fn-crea-revisione-preventivo`, `vendite/test-fn-list-preventivi-da-pushare-v1`, `vendite/test-fn-list-preventivi-da-pushare-v2`, `vendite/test-fn-preventivo-ha-residuo-commessa-v1`, `vendite/test-vw-dash-aperto-v1`, `vendite/test-vw-dash-competenza-gruppi-riferimento-sorgente-v1`, `vendite/test-vw-dash-competenza-gruppi-v1`, `vendite/test-vw-dash-preventivi-revisione-attiva`, `vendite/test-vw-preventivi-superata-vs-abortito-v1` |
| Fattura | `dbops/test-fn-pgtap-crea-fattura-v1`, `pagamenti/test-sistemazione-annullo-riporto`, `vendite/test-fattura-guard-uscita-draft-v1`, `vendite/test-fattura-satelliti-lock-congelamento-v1`, `vendite/test-fondi-fattura-governo`, `vendite/test-fondi-fattura-lotto`, `vendite/test-fondi-fattura`, `vendite/test-fondo-fattura-cancellazione`, `vendite/test-fondo-fattura-eseguito`, `vendite/test-genera-scadenze-fattura-v1`, `vendite/test-snapshot-indirizzi-lotto-v1`, `vendite/test-snapshot-intestazione-fattura-v1` |
| Offerta | `script/test-fn-available-actions-offerta-v1`, `vendite/offerte_commerciali/test_fn_crea_revisione_offerta`, `vendite/offerte_commerciali/test_fn_push_offerta_a_contratto`, `vendite/offerte_commerciali/test_offerte_commerciali_state_machine`, `vendite/test-righe-esclusione-solo-non-si-vende-v1`, `vendite/test-testata-dopo-emissione-rdb-v1`, `vendite/test-vw-dash-backlog-v1`, `vendite/test-vw-dash-fatturazione-v1` |
| Commessa | `vendite/test-af-emessa-non-lockata-reset-e-riporto-v1`, `vendite/test-diagnostica-gruppi-fatturabili-v1`, `vendite/test-ordini-guard-transizione-v1`, `vendite/test-pull-non-prende-trattenuti-v1`, `vendite/test-select-perimetro-consegnato-v1`, `vendite/test-specchio-lane-diagnostica-v1`, `vendite/test-vw-commesse-attivita-emittibilita-v1` |
| Ordine | `dbops/test-fn-pgtap-crea-ordine-v1`, `script/test-trgfn-default-emittente-fiscale-v1`, `vendite/test-fn-list-ordini-da-pushare-v1`, `vendite/test-ordini-guard-transizione-v1` |
| DDT, reso | nessuno |

**Ricadute sul backend, da scrivere come richiesta al team BE** (lato DB non si toccano):

* `apps/vendite/tests/db/test_ricerca_liste_db.py:126` inserisce un preventivo EMESSO;
* `backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py:331` inserisce un preventivo
  copiando lo stato di uno esistente, qualunque sia;
* i 4 test di `apps/pagamenti/tests/db/` che creano fatture senza stato dipendono da P-2;
* i 5 service che scrivono lo stato iniziale per nome dipendono da P-2 (se il DB lo mette da sé,
  quelle cinque copie si ritirano).

Fuori dal perimetro, per memoria: i documenti interni di magazzino (stato testo con DEFAULT `DRAFT`
e un loro guard di transizione), le sistemazioni dei pagamenti (stato testo, e **hanno già** la
regola della nascita nel loro guard: «un atto non nasce già fatto»), le versioni di listino (il
vocabolario arriva con M-5).

| # | Domanda | Note |
| --- | --- | --- |
| P-1 | Come dichiara il vocabolario qual è il suo stato iniziale? (a) colonna `iniziale boolean` su ogni vocabolario, con indice unico parziale (uno solo per vocabolario); (b) `fase = 'APERTO'` più un vincolo d'unicità; (c) lo stato senza passaggi in ingresso nella matrice | ✅ **Deciso da Tid il 2026-10-24: (a)** — colonna `iniziale` con indice unico parziale. (b) darebbe un significato nuovo a una colonna che ne ha già uno; (c) si rompe se la matrice ammette un ritorno alla bozza (la fattura ha già EMESSA → DRAFT). Tocca 8 vocabolari (i CSV di `80_data`) |
| P-2 | Se l'INSERT non dice lo stato (NULL), la regola (a) lo rifiuta o (b) mette lo stato iniziale? | ✅ **Deciso da Tid il 2026-10-24: (b)** — il DB mette l'iniziale quando manca e rifiuta ogni altro stato. Lo stato iniziale si scrive in un posto solo e le 16 copie si ritirano nello stesso giro (regola del 2): letterali nelle funzioni DB, i 5 service, il DEFAULT `1` della commessa. La colonna della fattura diventa NOT NULL. Con (a) le copie restano, e la fattura senza stato va trattata a parte |
| P-3 | Il perimetro: le 8 testate di vendita più `acquisti.ordini` e `acquisti.ddt`? | ✅ **Deciso da Tid il 2026-10-24: sì, anche acquisti** — stessi vocabolari, nessuno scrittore da adeguare. In più (Tid): **acquisti parte con tutto ciò che vendite ha imparato**, senza rifarne gli errori (§5). Magazzino, sistemazioni e listino restano fuori finché non hanno un vocabolario in tabella |

### 4-quinquies. Primo giro: applicato, test verdi (2026-10-24)

**I changeSet** (`20261024-07` … `-25`, nell'ordine):

| # | Cosa |
| --- | --- |
| `-07` | colonna `iniziale` sugli 8 vocabolari, indice unico parziale `uq_<voc>_iniziale`, CHECK `chk_<voc>_iniziale_attivo`, backfill per codice (P-1) |
| `-08` | `vendite.commesse.stato_commessa_id` perde il DEFAULT `1`; `vendite.fatture.stato_doc_fiscale_id` diventa NOT NULL (P-2) |
| `-09` | `script.fn_stato_iniziale_id(regclass)`: l'unico lettore dello stato iniziale |
| `-10` | il BB `script.trgfn_doc_stato_iniziale`: stato assente → lo mette; iniziale → passa; altro → `E_DOC_STATO_INIZIALE_NON_VALIDO` (N-1, N-3) |
| `-11`, `-12` | montaggio `trg_<tabella>_a05_stato_iniziale_ins` sulle 8 testate di vendita e sulle 2 d'acquisto (N-2, P-3) |
| `-13` … `-21` | le 9 funzioni che scrivevano `'DRAFT'`/`'BOZZA'` non lo cercano più; `fn_push_preventivo_a_ordine` legge lo stato delle righe con `fn_stato_iniziale_id` |
| `-22` | `dbops.fn_pgtap_porta_a_stato` vale per tutte le 8 testate (fattura compresa, solo coi passaggi che il guard della fattura singola ammette) |
| `-23` … `-25` | i builder pgTAP di ordine, preventivo e fattura fanno nascere in bozza e portano avanti per la matrice (la fattura scrive prima gli snapshot di indirizzi e intestazione, come la pipeline) |

Dati: colonna `iniziale` in coda agli 8 CSV dei vocabolari, dichiarata nei 10 mirror che li caricano;
il codice `E_DOC_STATO_INIZIALE_NON_VALIDO` (TECNICO) in `messaggi_errore.csv` e `codici_errore.csv`.
La frase di N-3 diventa «Il documento %s non può nascere…»: il nome viene da
`config.sorgenti.etichetta` («Offerta», «Commessa»), e «Il Offerta» non si legge.
Doc: `docs/it/dbzero/script/manual/trgfn_doc_stato_iniziale.md`.

**Le copie ritirate nello stesso giro** (regola del 2): i letterali nelle 9 funzioni e il DEFAULT
`1` della commessa. Restano i 5 service del backend: richiesta qui sotto.

**pgTAP.** Nuovo `script/test-trgfn-doc-stato-iniziale-v1.sql` (18 test: il montaggio si ricava dal
catalogo, quindi una testata nuova senza il trigger fa rosso). Portati alla nascita in bozza i 52 file
del censimento più il presidio del builder dell'ordine (48 file toccati). Attese cambiate, dichiarate:

* `vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` test 19: il contratto «nato ATTIVO»
  si aspettava 23P01 dall'EXCLUDE, ora `E_DOC_STATO_INIZIALE_NON_VALIDO`. Il 23P01 non si raggiunge
  più per nessuna strada lecita (prima lo ferma la nascita, poi il guard di transizione): l'EXCLUDE
  resta provato nella forma (test 21-23);
* `vendite/test-testata-dopo-emissione-rdb-v1.sql`: test 37 nuovo (un contratto non nasce ATTIVO),
  piano 37;
* `dbops/test-fn-pgtap-crea-ordine-v1.sql`: il test 5 chiede ANNULLATO invece di CONFERMATO, e il
  test 10 nuovo fissa che un CONFERMATO senza righe lo ferma il guard vero, piano 10.

**Come è provato** (scratch `zeroerp_ruoli`, SQL estratto dai changeSet in transazione annullata,
come owner):

* regressione su 152 file (i 52 del censimento, gli 81 che chiamano le funzioni riscritte, 28
  presidi trasversali, il test nuovo): **109 verdi, 43 rossi identici a prima** (stesso conteggio,
  stesso errore: debiti di fixture preesistenti, per lo più «il primo billing account del
  database», che sullo scratch non c'è), **nessuna regressione**;
* per i file fermi su quei debiti il percorso nuovo è stato provato su copie con il mondo costruito
  dai builder (nello scratchpad della sessione, non nel repo);
* `plpgsql_check` senza errori sulle 11 funzioni; nessun doppione di firma; i guardrail statici e i
  due SQL della CI (`codice_errore_strutturato`, `riferimenti_morti`) verdi;
* i 10 mirror ricaricati per intero (57 righe) sopra i trigger di oggi, nella forma del loader
  (UPDATE, poi INSERT se manca): passano;
* ✅ applicato da Tid il 2026-10-24 su dbdev e scratch, corsa pgTAP verde (come applicazione, RLS
  attiva). Due file che pescano dati veri, rossi solo su dbdev, corretti nella stessa giornata:
  `test-fondi-fattura-governo` (Q-1) e `test-fn-resolve-iva-riga` (il contratto clonato senza listino
  prende una riga AGGIUNTA, con l'articolo scelto da `catalogo.fn_articoli_ammessi`).

**Aperti, per Tid:**

* ✅ **Q-1. Una fattura ANNULLATA il modello non la sa costruire** — **deciso da Tid il 2026-10-24:
  B**, il modello resta com'è. DRAFT → ANNULLATA c'è solo coi passaggi del lotto (`solo_lotto`), e
  l'annullo del lotto cancella le fatture. `vendite/test-fondi-fattura-governo.sql` (D-1/D-9) faceva
  nascere una sorgente ANNULLATA: ora è una sorgente **EMESSA**, perché la regola provata è «genera e
  propone solo una fattura DEFINITIVA» ed EMESSA è il caso più stretto (uscita dalla bozza,
  completa, lo stato subito prima). Provato su una variante col mondo costruito, sullo scratch già
  applicato: i due test verdi, file 29/30 (il rosso è il test 2, preesistente).
* ✅ **Q-2. Builder di fixture ripetuti** (regola del 2, proposti dal porting, non scritti): commessa
  emittibile (6 file), fattura «fuori bozza ma senza snapshot» (4 file), contratto figlio di
  un'offerta e contratto ATTIVO sul billing account del test (4 file). **Deciso da Tid il
  2026-10-24: A** — tre builder in `dbops`, e i 14 file passano a usarli nello stesso giro: le copie
  scrivono a mano la strada d'uscita dalla bozza, la stessa che questo giro ha accentrato.
* ✅ **Q-3.** `vendite/test-snapshot-indirizzi-lotto-v1.sql` rimette `DEFERRED` i soli tre trigger di
  coerenza lotto/fatture (il file era escluso dai differiti per quel guard, e
  `fn_pgtap_porta_a_stato` esce con `IMMEDIATE`). **Deciso da Tid il 2026-10-24: B** — si cura il
  debito invece di aggirarlo: la fixture allinea lo stato delle fatture a quello del lotto prima di
  chiudere, il `SET CONSTRAINTS … DEFERRED` si toglie, il file gira tutto `IMMEDIATE` e il guard di
  coerenza viene esercitato (la correzione è quella già scritta in testa al file, debito di
  brief-db-pgtap-runner-rls-baseline §22).
* ✅ **Q-4.** I debiti «primo billing account» (una decina di file) si curano col mondo costruito.
  **Deciso da Tid il 2026-10-24: dentro questo giro**, non a parte: insieme ai builder di Q-2.
* Fuori da questo giro: `dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` è rosso nel
  guardrail del preambolo già in HEAD (commit `dbb810c3d`).

**Richiesta al team BE** (si accetta che qualcosa resti rotto fino al loro giro, §5):

1. rigenerare `apps/core/services/error_policies_generated.py`
   (`manage.py genera_error_policies`): codice nuovo `E_DOC_STATO_INIZIALE_NON_VALIDO`, TECNICO;
2. i 5 service che scrivono lo stato iniziale per nome (`ordini_service`, `ddt_service`,
   `resi_service`, `offerte_service`, `preventivi_service`, con i loro repository) smettono di
   passarlo: il database lo mette da sé (P-2). Le cinque copie si ritirano;
3. `apps/vendite/tests/db/test_ricerca_liste_db.py:126` inserisce un preventivo EMESSO: va creato
   in bozza e portato avanti;
4. `backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py:331` copia lo stato di un
   preventivo esistente: va creato in bozza;
5. i 4 test di `apps/pagamenti/tests/db/` che creano fatture senza stato continuano a funzionare
   (lo stato lo mette il database): nessuna modifica, da sapere.

**Fatto dal team BE** (2026-10-24, `dev/backend-tid`, da committare):

1. `error_policies_generated.py` rigenerato (`--check` pulito, il codice è nel CSV in git) e la
   frase di ripiego in `error_messages_fallback.py`, senza segnaposto;
2. i 5 service non cercano più lo stato iniziale e i loro repository non lo scrivono: tolti il
   parametro di `create_ordine` / `create_ddt` / `create_reso` / `create_preventivo`, la colonna
   dalla whitelist d'inserimento delle offerte (`TESTATA_CREATE_COLUMNS`),
   `PreventiviRepository.get_stato_bozza_id` e `ResiRepository.get_stato_id_by_codice`, che non
   avevano altri chiamanti;
3. `test_ricerca_liste_db`: il preventivo nasce in bozza e va a EMESSO con
   `dbops.fn_pgtap_porta_a_stato`; contratto e offerta della stessa fixture non scrivono più lo stato;
4. `smoke-pratica-doc-sorgente-cross-emittente.py`: oltre a non copiare lo stato, costruisce **anche**
   il documento di casa (prima: «il primo preventivo dell'emittente», in qualunque stato). Lo smoke
   pretende che i due documenti abbiano lo stesso stato, perché la regola dell'ancora ordina anche
   sulla terminalità: con l'estraneo in bozza e quello di casa ANNULLATO vinceva il vivo, e il test
   misurava la terminalità invece del perimetro. Ora pareggiano per costruzione;
5. emersi dalla corsa e non in richiesta: tre test DB di creazione (`test_{ordini,ddt,resi}_create_db`)
   che passavano lo stato al repository; lo smoke bash `smoke-test-guida-inversione-preventivi.sh`,
   che faceva nascere un preventivo EMESSO (ora in bozza + `fn_pgtap_porta_a_stato`); l'etichetta
   `config_panel.campi.iniziale` in it/en per la colonna nuova dei vocabolari (presidio
   `test_config_panel_registro_db`);
6. revisione critica del giro (2026-10-24), su questo stesso diff:
   * presidio simmetrico sui 5 service: ordini e preventivi non avevano, come DDT, offerte e resi,
     l'asserzione che lo stato **non** arrivi al repository. Col repository mockato un
     `stato_doc_*_id` rimesso dal service sarebbe passato muto; aggiunta in `test_ordini_service` e
     `test_preventivi_service`;
   * `ResiRepository.get_stato_id_by_codice` ritirato (ok di Tid): l'unico chiamante era la
     creazione del reso. Tolta con lui l'asserzione `assert_not_called()` di `test_resi_service`,
     che senza il metodo non provava più niente;
   * smoke cross-emittente: `crea_preventivo` legge da sé il `soggetto_ruolo` dell'emittente (prima
     due letture diverse, una per «casa» e una per «estraneo»); l'esito stampa la **coda** dell'uid
     (`uid_breve`) e non la testa: gli uid sono UUIDv7, i primi caratteri sono il timestamp, e i due
     documenti nati nello stesso giro stampavano lo stesso prefisso. I `check` confrontavano già
     l'uid intero: era la diagnostica a non distinguerli, non l'esito;
   * `config_panel.campi.iniziale` rimessa in ordine alfabetico in it/en.

   Provato: `manage-test.sh` vendite/core/config verde; con `ZEROERP_TEST_DB_E2E=1` i test DB di
   vendite e config verdi sul DB reale (senza la variabile sono skippati: un verde senza non prova
   niente); `genera_error_policies --check` allineato; lo smoke cross-emittente TUTTO VERDE. ⚠️ Non
   eseguito: `smoke-test-guida-inversione-preventivi.sh` (vuole il login HTTPS col secondo fattore);
   il suo pezzo nuovo, `fn_pgtap_porta_a_stato` dal ruolo app, è esercitato da `test_ricerca_liste_db`.

Restano fixture di test che scrivono lo stato iniziale esplicito (`DRAFT`/`BOZZA`) in un INSERT: il
trigger le fa passare, e non sono copie della regola in codice di prodotto.

### 4-sexies. Secondo giro: Q-2 … Q-4 (2026-10-24)

**Verifica del giro BE, prima di partire.** Il commit `993dd7150` (PR #1936) fa i punti 1-5 della
richiesta: nessun service passa più lo stato in creazione. I `get_stato_id_by_codice` rimasti servono
al cambio di stato (giro M-1), non alla nascita.

**La scelta (Tid, 2026-10-24: «estendi i builder esistenti»).** Due dei tre builder proposti in Q-2
esistevano già in parte (`fn_pgtap_crea_commessa` + `_commessa_attivita`; `fn_pgtap_crea_contratto` con
ATTIVO e BA): un builder nuovo accanto sarebbe stato una seconda copia. Si estendono i tre esistenti,
parametri in coda, DROP + CREATE:

| # | Builder | Cosa aggiunge |
| --- | --- | --- |
| `-26` | `dbops.fn_pgtap_crea_commessa` | stato da raggiungere (per la matrice), BA del test (verificato dal BB), `p_con_attivita` (di default solo fuori bozza: l'uscita la pretende); RETURNS + `attivita_id`, `stato_commessa_id`. La sorgente ROOT resta del test |
| `-27` | `dbops.fn_pgtap_crea_fattura` | `p_spoglia_indirizzi`, `p_spoglia_intestazione`: la fattura si spoglia nell'ultimo stato non congelato del percorso (`congela_fiscale`, letto dal vocabolario: oggi EMESSA), poi arriva allo stato chiesto. Il COMMENT, stantio dal `-25`, riscritto |
| `-28` | `dbops.fn_pgtap_crea_contratto` | `p_offerta_id`: il figlio nasce dalla push `vendite.fn_push_offerta_a_contratto` (in produzione nasce solo così; `fn_create_contratto` non accetta l'offerta), sul cliente dell'offerta. Annullato, dichiara i legami da `vendite.fn_documento_legami`, come il backend |

Presidi estesi: commessa 6 → 11 test, fattura 8 → 12, contratto 8 → 11. Doc: le tre pagine `manual` e
la tabella dei builder in `pgtap-come-si-scrive-un-test.md` (era ferma a «stato scelto alla nascita»).

**I 28 pgTAP portati** (porting in cinque gruppi):

| Gruppo | File | Prima | Dopo |
| --- | --- | --- | --- |
| Commessa emittibile (Q-2) | `af-emessa-non-lockata-reset-e-riporto-v1`, `pull-non-prende-trattenuti-v1`, `select-perimetro-consegnato-v1`, `specchio-lane-diagnostica-v1`, `vw-commesse-attivita-emittibilita-v1`, `ordini-guard-transizione-v1` (solo la testata), `diagnostica-gruppi-fatturabili-v1` (+Q-4) | 6 verdi, 1 rosso | 7 verdi |
| Fattura senza snapshot (Q-2, Q-3) | `fattura-guard-uscita-draft-v1`, `snapshot-intestazione-fattura-v1`, `snapshot-indirizzi-lotto-v1`, `fattura-satelliti-lock-congelamento-v1` | 1 verde, 3 rossi | 4 verdi |
| Contratto e dashboard (Q-2, Q-4) | `vw-dash-backlog-v1`, `vw-dash-fatturazione-v1` (il figlio dalla push), `vw-dash-aperto-v1`, `dbops/test-fn-apply-chiusura-scadenze-v1`, `vw-dash-competenza-gruppi-v1`, `vw-dash-competenza-gruppi-riferimento-sorgente-v1`, `emissione-mirata-gruppi-fatturabili-v1` | 2 verdi, 5 rossi | 7 verdi |
| Preventivi (Q-4) | `fn-crea-revisione-preventivo`, `fn-list-preventivi-da-pushare-v1`, `-v2`, `vw-dash-preventivi-revisione-attiva`, `vw-preventivi-superata-vs-abortito-v1` | 5 rossi | 5 verdi |
| Fondi fattura (Q-4) | `fondi-fattura`, `fondi-fattura-lotto`, `fondo-fattura-cancellazione`, `fondo-fattura-eseguito`, `fondi-fattura-governo` (anche il test 2, rosso da prima del giro) | 5 rossi | 5 verdi |

**Attese cambiate, dichiarate nei file.** Nessun valore atteso delle asserzioni sul caso. Cambiano le
asserzioni di fixture (il test 0 o il test 2), che contavano le righe delle temp table o pescavano il
catalogo: ora contano le righe costruite, nella forma voluta. In `vw-dash-preventivi-revisione-attiva`
e `vw-preventivi-superata-vs-abortito-v1` il test 2 pescava «il primo OPERATORE» e riscriveva la sua
whitelist: ora è l'operatore del mondo, e l'asserzione è più stretta.

**Come è provato** (scratch `zeroerp_ruoli`, come owner):

* prima dell'apply: SQL estratto dai tre changeSet in transazione annullata; nessun doppione di firma,
  EXECUTE all'app, `plpgsql_check` pulito, i due SQL della CI (`riferimenti_morti`,
  `codice_errore_strutturato`) e i guardrail statici verdi; i 33 chiamanti dei tre builder identici
  prima e dopo;
* dopo l'apply di Tid (22:31): 64 file (i 28 portati, i 4 presidi, i 33 chiamanti), **63 verdi**;
  l'unico rosso, `test-annullo-documento-con-legami-v1` (29/30), è identico a prima del giro;
* ⚠️ non provato come app: la corsa di Tid. `test-diagnostica-gruppi-fatturabili-v1` gira come app
  (senza marcatore owner).

**Aperti, per Tid:**

* **R-1 (Q-3): la «definitiva» dentro il lotto in bozza.** La decisione diceva «la fixture allinea lo
  stato delle fatture a quello del lotto prima di chiudere». Non si può: il caso del file (test 3, 4,
  8) È una fattura DEFINITIVA in un lotto DRAFT, e una DEFINITIVA non torna in bozza; coi vincoli
  IMMEDIATE l'incoerenza scatta già all'INSERT del ponte. Il guard di coerenza ammette fuori passo solo
  le fatture `critical`. Il porting l'ha fatta entrare nel lotto **già ferma**: una segnalazione `C`
  in `vendite.fatture_log` (il flag lo accende il trigger z90 vero, non la fixture); il giro la salta
  per lo stato, non per il flag, quindi i test misurano la stessa cosa. DEFERRED tolto, file tutto
  IMMEDIATE, guard esercitato (controprova: senza la segnalazione il file si ferma sul guard).
  ⚠️ Se «la definitiva non ferma le altre» deve valere anche per una fattura NON critical, è il guard
  di coerenza a non ammetterlo: è un tema di modello, non di fixture. Da confermare.
* **Candidati a builder** (fixture ripetute che nessun builder copre; non scritti):
  * R-2: contratto ATTIVO con periodo e listino del test (bozza dal builder, UPDATE di date/listino,
    poi la matrice), 5 file delle dashboard;
  * R-3: la sorgente ROOT della commessa, 3 file;
  * R-4: il lotto DRAFT di fixture con l'esito che lo trattiene, 5 file;
  * R-5: il blocco «mondo + registro + catalogo» dei fondi (in pratica `fn_pgtap_crea_fattura` senza
    la fattura), 4 file; e `fn_pgtap_crea_fattura` non prende `minimo`, `totale_a_pagare`,
    `termine_pagamento_id`: le quattro fatture dei fondi restano INSERT a mano;
  * R-6: revisioni di preventivo con numero e rev fissati; `fn_pgtap_crea_preventivo` non accetta né
    restituisce il numero;
  * R-7: un secondo BA sullo stesso ruolo, su un'istanza nuova (`snapshot-indirizzi-lotto` lo scrive
    con `anagrafiche.fn_crea_billing_account` in una finestra differita);
  * R-8: un cliente senza indirizzi d'ambito FATTURA (i builder scrivono sempre il FATT generico);
  * R-9: il blocco «mondo + operatore + whitelist riscritta» delle dashboard.
* **Difetti dei builder, non corretti:** con il BA del test, `fn_pgtap_crea_commessa` e
  `fn_pgtap_crea_contratto` costruiscono comunque un cliente che non usano (chiamano
  `fn_pgtap_crea_mondo_cliente` prima): innocuo, ma le viste globali vedono un cliente in più. Il
  COMMENT di `fn_pgtap_crea_preventivo` è fermo a prima del `-24` («stato scelto alla nascita»).
  `fn_pgtap_crea_preventivo` e `fn_pgtap_crea_fattura` scelgono valuta e tipo documento «il primo per
  id». L'attività di `fn_pgtap_crea_commessa_attivita` ha `valuta_id` NULL (le fixture a mano la
  valorizzavano).

**Residui fuori dal giro** (debito noto, non curato qui):

* `test-ordini-guard-transizione-v1`: la fixture dell'ordine pesca ancora emittente e soggetto «il
  primo per id»;
* le commesse di `vw-dash-aperto`, `-backlog`, `-fatturazione` nascono ancora da INSERT a mano;
* `CANONE_NON_GENERATO`: il commento e il test 10 di `vw-dash-backlog` lo dichiarano, ma nessuna vista
  né funzione lo produce (c'è solo nel seed di `config.motivi_fermo`). Il test resta vero per un altro
  motivo (il contratto è fuori dal backlog);
* rossi sullo scratch per la pesca del primo BA, NON portati in questo cantiere: `test-fatturazione-
  reset-lotto-draft`, `test-fatture-atti-v1`, `test-resi-rinunce-scenario-v1`,
  `test-vw-preventivi-smistamento-v1`, `test-genera-scadenze-lotto-v1`, `test-arrotondamento-ambito-
  idempotenza-v1`, `test-chiave-fattura-tre-specchi-v1`, `test-data-documento-v1`,
  `test-fn-push-preventivo-a-ordine-v1` (esito del primo giro, §4-quinquies);
* altri debiti di fixture visti nel primo giro: articolo-onere pescato
  (`fn-preventivo-ha-residuo-commessa-v1`), `fn-resolve-iva-riga`, `proiezione-stato-sorgente`,
  `test_fn_successione_contratti`. Gli articoli-onere non si costruiscono (`causale_onere_id` UNIQUE,
  le 5 causali hanno l'articolo nel seed): si leggono per causale.

**Richiesta al team BE** (⚠️ firme aggiornate dal §4-septies, che le cambia di nuovo):

1. due test Django sondano la firma VECCHIA dei builder con `richiedi_db_provvisto`, e con la firma
   nuova **saltano in silenzio** (verde per sottrazione). Le firme FINALI, dopo il §4-septies, sono
   `dbops.fn_pgtap_crea_commessa(text,character varying,bigint,boolean,boolean)` e
   `dbops.fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean,boolean,numeric,bigint,boolean)`
   (rev §4-octies, `-42`; le righe qui sotto sono quelle del secondo giro, superate):
   * `apps/vendite/tests/db/test_prezzo_riga_commessa_db.py:133`:
     `"dbops.fn_pgtap_crea_commessa(text)"` → `"dbops.fn_pgtap_crea_commessa(text,character varying,bigint,boolean)"`;
   * `apps/core/tests/db/test_scritture_email_note_db.py:109`:
     `"dbops.fn_pgtap_crea_fattura(text,character varying,bigint)"` → `"dbops.fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean)"`;
2. nessun'altra ricaduta: i chiamanti BE (2 test Django, 3 smoke) passano al più tre argomenti e
   restano validi.

### 4-septies. Terzo giro: i debiti emersi e le decisioni R-1 … R-9 (2026-10-24)

Tid, 2026-10-24: «i debiti emersi vanno risolti»; R-1 sì (regola sotto), R-2, R-3, R-4, R-5 sì, R-6 e
R-9 come consigliato, R-7 e R-8 non ora (regola del 2: una copia sola).

**I debiti emersi, chiusi:**

* `CANONE_NON_GENERATO` non era un difetto del database: dal `20260707-03` i contratti non hanno un
  motivo di fermo finché non esiste il push ricorrente, e il codice resta nel seed **apposta**. Era il
  test (`vw-dash-backlog`, test 10 e commento) a dichiarare il motivo sbagliato: corretto;
* il COMMENT di `fn_pgtap_crea_preventivo` e quello di `fn_pgtap_crea_ordine` (fermi a prima del
  `-23`/`-24`): `20261024-29`, solo testo; e le due pagine `manual`;
* `test-ordini-guard-transizione-v1` e i nove file rossi «fuori giro» del §4-sexies: mondo costruito,
  tutti verdi; più altri otto rossi da pesca trovati nella regressione (articolo-onere, BA, chiave di
  sorgente, IVA) e `test-guard-lotto-fatture-stato-coerente` (il test del guard di coerenza, rosso dal
  test 1 per il primo BA: non provava niente);
* nove file con un solo rosso, diagnosticati (non toccati): **tutti dipendono dal ruolo** (l'owner dello
  scratch salta la RLS; come app sono verdi per costruzione). Nei quattro che non lo dichiaravano
  l'avviso è nel titolo del test.

**R-1, la regola di Tid:** «se un documento è in errore o in uno stato bloccante, gli altri non possono
passare a uno stato definitivo: prima i documenti non conformi si tolgono dal lotto; non può esistere un
documento definitivo se un altro dello stesso lotto è in errore». Completa D-Q (2026-07-31: «il lotto
NON avanza»), non revoca niente. Provato il 2026-10-24 che il DB **non** la applicava: lotto e fattura
sana DEFINITIVA, fattura in errore DRAFT nello stesso lotto; lo stop stava solo nel runner BE.

**I changeSet** (tutti `dbops` salvo `-34`/`-35`):

| # | Cosa |
| --- | --- |
| `-29` | COMMENT di `fn_pgtap_crea_preventivo` / `_ordine` allineati alla nascita in bozza |
| `-30` | `fn_pgtap_porta_a_stato` conosce il lotto di fatturazione (vuoto; con fatture si muove col verbo `fn_sync_lotto_fatture_stato`) |
| `-31` | NUOVO `fn_pgtap_crea_lotto` (R-4): dalla madre `fn_create_fatturazione_lotto`, stato per la matrice, esito che trattiene un gruppo |
| `-32` | `fn_pgtap_crea_commessa` + `p_con_sorgente_root` (R-3) |
| `-33` | `fn_pgtap_crea_contratto` + periodo, data e listino del test (R-2) |
| `-34` | (R-1 b) `vendite.vw_lotti_fatture_incoerenti` diventa la **sede unica** dell'invariante lotto ↔ fatture e il guard la legge (prima ripetevano lo stesso predicato); l'eccezione critical vale per chi resta **indietro**, non per una fattura già congelata davanti a un lotto non congelato |
| `-35` | (R-1 a) `vendite.trgfn_fatturazione_lotti_guard_stato`: un lotto FERMO (`vw_lotti_segnalazioni_summary.fermo`, la sede del runner) non entra in uno stato congelato e non abortito: `E_PIPELINE_LOTTO_CRITICAL`, lo stesso codice del runner; l'annullo resta ammesso |
| `-36` | `fn_pgtap_crea_fattura` + `minimo`, `totale_a_pagare`, `termine_pagamento_id` alla nascita (R-5) |

Dati: nota di `E_PIPELINE_LOTTO_CRITICAL` (`codici_errore.csv`, chi la solleva) e causa di
`E_LOTTO_FATTURE_STATO_INCOERENTE` (`messaggi_errore.csv`, citava ancora `esclusa`). Censimento di chi
muove i lotti: `fn_riporta_lotto_a_draft` cancella le fatture prima; la sync e la chiusura del
giornaliero lasciano INDIETRO le critical; l'annullo va in uno stato abortito; nel giro vero il runner
legge lo stesso verdetto prima di `update_lotto_stato_doc`. Nessuno produce il caso vietato.

Presidi: nuovi `dbops/test-fn-pgtap-crea-lotto-v1` (9) e `vendite/test-lotto-fermo-non-diventa-definitivo-v1`
(8: **rosso senza** i due guard, verde con; prova anche l'annullo e il rilancio che sblocca); estesi
commessa (13), contratto (14), fattura (14). Doc: le `manual` dei builder, di `porta_a_stato`, dei due
guard e della vista, la tabella dei builder della guida pgTAP.

**Porting** (agenti in parallelo, ogni file riprovato a mano): sorgente ROOT e lotto nei builder (11
file), dashboard con contratto col periodo, mondo costruito e commesse dal builder (7), revisioni dei
preventivi per la strada del dominio (2), pesca residua (12), test di coerenza. Attese cambiate,
dichiarate nei file: il codice del lotto in `diagnostica-gruppi-fatturabili` (test 13: quello della
madre, non `PGTAP-DG-LOTTO`); numeri di preventivo e di contratto letti dal dominio invece che fissi;
in `test_fn_successione_contratti` i casi 3 e 6 erano verdi per sottrazione (`is(NULL, NULL)`).

**Come è provato:** regressione prima/dopo su 134 file (builder `-29`…`-33`) e su 163 file (`-34`…`-36`):
nessuna regressione; le sole differenze sono i presidi nuovi e i due file del trucco «definitiva
critical nel lotto» (sotto). ⚠️ Tid ha applicato `-26`…`-28` alle 22:31 e `-29`…`-33` alle 23:02 mentre
le prove giravano: da lì le misure sono «senza». `-34`…`-36` applicati da Tid alle 23:26 (dbdev e scratch).

**Aperti / in corso:**

* ✅ `test-snapshot-indirizzi-lotto-v1` e `test-genera-scadenze-lotto-v1` provavano «la definitiva nel
  lotto in bozza non si tocca» costruendo una definitiva critical agganciata al lotto: con R-1 quel mondo
  non esiste. Il ramo che la salta resta nelle funzioni come **difesa dichiarata, non provata** (Regola
  zero). Diventano `skip` motivati il 4 e l'8 di indirizzi-lotto e il 4 di genera-scadenze (l'8 prova un
  critico di un altro task, e resta); attese aggiornate, dichiarate: indirizzi-lotto 2, 3, 9 (nessuna
  saltata), genera-scadenze 1 (nessuna oltre soglia, e le due in bozza contate davvero). Verdi con e senza
  i changeSet;
* ✅ i cinque pgTAP dei fondi passano a `fn_pgtap_crea_fattura` con i tre valori di R-5: verdi col `-36`.
  ⚠️ **Senza il `-36` non girano** (chiamano il builder a otto argomenti): dopo l'apply. Restano a mano le
  tre fatture la cui utility è il caso del test (diversa dal BA, o vuota): candidato `p_utility_id`;
* ✅ il marcatore `pgtap-contesto` nei tre file della pesca residua che aprono il contesto col mondo;
* **candidati a builder**, non scritti (regola del 2, decide Tid): due fixture ripetute in 3 file
  ciascuna (coppia di articoli MERCE + SERVIZIO; scheda precontrattuale della fornitura); l'attività di
  commessa «di push» (chiave del preventivo, stato di emissione) in 2 file; più gruppi trattenuti dallo
  stesso lotto (1 file); `p_iva_id` in `fn_pgtap_crea_articolo` (1 file); `listino_versione_id` e
  variazione globale nel contratto (1 file);
* **difetto comune dei builder**, da decidere: con il BA del test, commessa, contratto, fattura, ordine e
  lotto costruiscono comunque un cliente che non usano (chiamano `fn_pgtap_crea_mondo_cliente` prima).
  La cura è un BB «l'azienda del contesto» per quando il BA arriva dal test: tocca cinque builder;
* il guardrail del preambolo riconosce il contesto solo da `fn_pgtap_set_contesto_operatore(`: quattro
  dashboard tengono una riga ridondante per lui.

### 4-octies. Quarto giro: il pezzo comune e i builder delle fixture ripetute (2026-10-24)

Tid, 2026-10-24: «sul da decidere procedere ai miglioramenti: pezzo comune / builder quando ripetuti».
Criterio, quello dei builder del progetto: **entra ciò che ha una trappola d'ordine o ricopia una regola
del dominio, non ciò che serve spesso**; e alla seconda copia (regola del 2), con le copie ritirate nello
stesso giro.

| # | Cosa |
| --- | --- |
| `-37` | NUOVO `dbops.fn_pgtap_azienda_di_chi_agisce`: l'azienda del contesto aperto, dalla regola di produzione; estratta dal «ramo B» del mondo |
| `-38` | NUOVO `dbops.fn_pgtap_cliente_del_builder`: senza BA il mondo; col BA del test l'azienda di chi agisce e il BA verificato, **senza un cliente in più** |
| `-39` | `fn_pgtap_crea_mondo_cliente` usa `-37` (la copia si ritira) |
| `-40` | commessa, contratto, fattura, ordine, lotto: il blocco ricopiato cinque volte diventa una chiamata a `-38` |
| `-41` | `fn_pgtap_crea_commessa_attivita` + sorgente (la chiave da `script.fn_segment_key`, il SOLO costruttore: dieci pgTAP la componevano a mano, come i sedici rotti il 20-10), quantità, stati di approvazione/emissione, periodo |
| `-42` | `fn_pgtap_crea_fattura` + `p_senza_utility` (due copie nei fondi) |

✅ **Applicato e verde** (Tid, 2026-10-24): `-37` … `-42` alle 23:50 su dbdev e scratch, corsa pgTAP come
app verde. Prima dell'apply: regressione sullo scratch (come owner) su 174 file, nessuna regressione; sei
rossi identici prima e dopo, tutti dipendenti dal ruolo (l'owner salta la RLS), verdi come app.

Presidi: nuovo `dbops/test-fn-pgtap-cliente-del-builder-v1` (7: nessun cliente in più anche passando dai
cinque builder; rosso senza, verde con); estesi attività (14) e fattura (15: anche il valore restituito
senza utility, che il builder prima riportava sbagliato). Regressione del pezzo comune su 164 file:
nessuna differenza oltre al presidio nuovo.

**Porting**, ogni file riprovato a mano (verde col `-37` … `-42`):

* l'attività di push in otto file (`annullo-commessa`, `emissione-mirata-gruppi-fatturabili`,
  `fn-list-preventivi-da-pushare-righe-ids`, `-v2`, `fn-preventivo-ha-residuo-commessa`, `vw-dash-backlog`,
  `vw-dash-fatturazione`, `vw-preventivi-smistamento`): le chiavi ora le compone `script.fn_segment_key`.
  Tre righe scritte a mano con una chiave **inventata** che nessuna push produce (una sorgente PREVENTIVO
  con chiave `PGTAP-BL-NE-*`; una riga d'ordine con sorgente PREVENTIVO; la riga della commessa di B che
  puntava al preventivo di A) diventano righe della commessa, o della sorgente giusta. Attesa cambiata,
  dichiarata: in `emissione-mirata` il tipo documento del perimetro si legge dalle righe scritte (11, 12,
  16), non più «il primo tipo con un registro». Restano a mano, perché sono il caso: le chiavi con i
  suffissi `#CMP:` e `#RET:` (il match a prefisso, il classificatore) e il canone del contratto con la
  chiave del **mese** (`:M:AAAA-MM`; il builder non lo passa, un file solo), ma la base della chiave ora la
  compone il dominio anche lì; `fn-list-preventivi-da-pushare-v1` non ha righe da portare (la chiave a
  mano è l'attesa del suo test 2, il formato);
* la fattura senza utility nei due file dei fondi;
* `test-drop-uq-commesse-attivita-src-uid-partial-v1`, rosso da prima per la pesca del primo BA e con un
  uuid sintetico come sorgente (che il guard delle sorgenti oggi respinge): mondo costruito, preventivo
  vero, righe dal builder. 4/4 col `-41`.

Da sapere sui builder (nessuno rompe un test): l'attività del builder ha `data_attivita` = inizio del
periodo e `valuta_id` NULL (la madre non la deriva); chi ne avesse bisogno lo dichiara nel test.

**Valutati e lasciati** (non hanno trappola: spostare la riga in un builder non centralizza niente):
la scheda precontrattuale (un INSERT di 2-5 colonne, i cui valori sono il caso del test); la coppia di
articoli MERCE + SERVIZIO (il builder dell'articolo accetta già la natura); il controllo «l'operatore del
mondo è OPERATORE» delle dashboard (un'asserzione, non una fixture). Sotto la regola del 2 (una copia):
più gruppi trattenuti dallo stesso lotto, l'IVA nel builder dell'articolo, la versione di listino e la
variazione globale nel contratto, la fattura con un'utility diversa da quella del cliente.

La bolla generata da un ordine e il reso scritto a mano, ripetuti in tutta la suite, sono un tema suo:
[brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md) (chiuso il 2026-10-25; il reso è proseguito in [brief-db-pgtap-reso-costruito](../work-done/brief-db-pgtap-reso-costruito.md), chiuso anch'esso il 2026-10-25).

**Richiesta al team BE**, aggiornata: (1) le due sonde `richiedi_db_provvisto` sulle firme finali (sopra);
(2) dopo l'apply di `-35`, il DB può sollevare `E_PIPELINE_LOTTO_CRITICAL` anche dall'UPDATE dello stato
del lotto (`pipeline_repository.update_lotto_stato_doc`): il runner lo gestisce già come codice, ma
oggi lo produce solo lui; nessuna modifica attesa, da sapere.

**Fatto dal team BE** (2026-10-25, `dev/backend-tid`, da committare):

1. le sonde sulle firme finali, verificate su dbdev con `to_regprocedure` (non ricopiate dal brief):
   `test_prezzo_riga_commessa_db` → `fn_pgtap_crea_commessa(text,character varying,bigint,boolean,boolean)`,
   `test_scritture_email_note_db` → `fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean,boolean,numeric,bigint,boolean)`;
2. ⚠️ **una terza sonda rotta, fuori dalla richiesta**: `catalogo/tests/db/test_scritture_dinamiche_db`
   sondava `fn_pgtap_crea_articolo` con 5 argomenti, la firma è a 10 da `69844e217` (un brief
   precedente). Saltava in silenzio da allora; portata alla firma vera. Trovata controllando **tutte**
   le 21 sonde di firma della suite contro il DB: le altre 18 risolvono;
3. i tre test, che saltavano, girano e sono verdi (13 casi);
4. `error_policies_generated.py` rigenerato: il `--check` divergeva per la `note` nuova di
   `E_PIPELINE_LOTTO_CRITICAL` (solo il commento, nessuna classe cambiata);
5. suite completa con `ZEROERP_TEST_DB_E2E=1`: 6899 test, OK; l'unico skip è il presidio «verso 2,
   solo misurato» di `test_ui_action_e_canale_campi`, dichiarato.

Per Tid, due decisioni — ✅ **accettate il 2026-10-25, fatte** (sotto, «Fatto per BE-1 e BE-2»):

* **BE-1. Le sonde di firma sono un presidio che si spegne da solo.** Una sonda con la firma esatta
  di un builder trasforma ogni cambio di firma in uno skip muto — è successo tre volte, e la terza
  nessuno l'aveva vista. Proposta: un test che raccoglie le sonde dichiarate nella suite e, sul DB
  provvisto (sonda di default verde), è **rosso** se una non risolve. Tocca il BB
  `richiedi_db_provvisto` (`apps/core/tests/db_e2e.py`), trasversale a tutte le app.
* **BE-2. Il codice del DB nel runner del lotto si perde.** Il punto (2) qui sopra non regge: un
  `E_PIPELINE_LOTTO_CRITICAL` sollevato dal guard (`trgfn_fatturazione_lotti_guard_stato`) arriva
  al runner come `DatabaseError`, non come `ServiceError`; `run_pipeline` lo prende nel ramo
  `except Exception` e lo appiattisce in `E_PIPELINE`, e il driver esce con `ERRORE` invece che
  con `BLOCCATO_CRITICITA`. Oggi il guard scatta dal runner solo se il lotto diventa fermo **fra**
  il controllo Python e l'UPDATE (stessa sede, `vw_lotti_segnalazioni_summary.fermo`; il rilancio
  dello stesso step non cambia stato e il guard non scatta; il runner è l'unico che scrive quello
  stato): è un'ultima difesa, ma quando difende dice la cosa sbagliata. Vale per **ogni** codice
  strutturato del DB dentro uno step (`E_LOTTO_PARAMETRO_NON_COERENTE` dello stesso guard compreso).
  Proposta: nel ramo generico, un `DatabaseError` con un codice del catalogo
  (`diagnostica_db(...).codice_strutturato`) diventa un `ServiceError` con quel codice, attraverso il
  BB esistente (`ErrorManager.raise_from_database_error`), e segue il ramo di dominio.

**Fatto per BE-1 e BE-2** (2026-10-25, `dev/backend-tid`, da committare):

* **BE-1, nel BB e non con un test che scansiona i file.** `richiedi_db_provvisto`
  (`apps/core/tests/db_e2e.py`) legge sempre lo schema dalla sonda di default (assente → skip,
  ambiente) e la sonda del chiamante solo dopo (assente su schema presente → `AssertionError`). È la
  regola che header del BB e catalogo dichiaravano già («schema presente + oggetto assente è un
  difetto»), e che il parametro `sonda` contraddiceva. Una scansione col regex avrebbe mancato le
  cinque chiamate scritte su più righe; il BB le copre tutte, e anche quelle future. Presidio dei tre
  rami: `apps/core/tests/test_db_e2e_sonda.py`; voce del catalogo BB aggiornata;
* **BE-2.** `run_pipeline`: il ramo generico riconosce un `DatabaseError` col codice **strutturato**
  del catalogo (non il testo) e lo traduce col BB `raise_from_database_error` (frase e soluzione
  del catalogo, nessun doppione nel diario); il fallimento segue il ramo di dominio, estratto in
  `_registra_fallimento_di_dominio` per non copiarlo. Test in `test_pipeline_runner`: il codice
  arriva intatto, il driver esce con `BLOCCATO_CRITICITA`, un errore DB senza codice resta
  `E_PIPELINE`. Provato che i due test nuovi vanno rossi sul runner di prima;
* suite completa verde con e senza `ZEROERP_TEST_DB_E2E=1` (6905 e 6426 test); il cancello mypy
  (`check_mypy_baseline.py`) pulito.

---

## 5. Come si procede dopo le decisioni

Due regole di Tid, 2026-10-24, che valgono per il piano e per ogni giro:

* **Si ottimizza per la velocità.** Non c'è produzione: si sceglie la strada più corta verso il
  modello, a colpi secchi, senza fasi di convivenza fra vecchio e nuovo. **Si accetta che qualcosa
  non funzioni** (backend, smoke, test Django) finché il cantiere BE del giro non è chiuso. Il lato
  DB non aspetta il BE: consegna il giro e scrive al BE cosa si è rotto e come si ripara. Restano
  verdi i pgTAP, che sono lato DB e si portano nello stesso giro.
* **Acquisti nasce sul modello, non lo rincorre.** Ogni volta che un documento di vendita viene
  portato al modello, il suo gemello di acquisti (ordine, DDT) ci arriva **nello stesso giro**:
  stesso verbo, stessa matrice, stesse azioni, stessi building block. Niente «fase due»: la
  guida del modello (§2) è scritta per entrambi, e gli errori censiti nel §3 non si ripetono in
  acquisti perché acquisti non ne ha una copia sua da sbagliare.

* Il §2, corretto con le decisioni, diventa la guida. Da lì una proposta che non è nella guida, o
  la contraddice, si dichiara come revoca.
* Si porta **un documento per giro, tutto intero** al modello (verbo, matrice, azioni, emissione,
  annullo), invece di un tema per giro su nove documenti. L'ordine dei documenti si decide col piano.
* Prima di ricopiare una regola nelle 11 capability o negli 11 guard, si valuta se quella parte può
  vivere in un building block comune che legge la matrice: è la causa strutturale del §1.

---

## 6. Punto 3: la guida del modello (2026-10-25)

**Verifica del giro BE, prima di partire.** Il commit `9fbff66d2` (PR #1938) contiene quello che il
§4-octies dichiara: le tre sonde sulle firme finali, `richiedi_db_provvisto` che fallisce
sull'oggetto mancante (BE-1, presidio `test_db_e2e_sonda.py`), il runner del lotto che tiene il
codice del DB (BE-2), `error_policies_generated.py` rigenerato, la voce del catalogo BB.

**Scritto:**

* la guida [modello-documento-di-vendita](../../guide/modello-documento-di-vendita.md): il §2 di
  questo brief con le decisioni M-1 … M-6, N-1 … N-3, P-1 … P-3 dentro, in sei regole (nascita,
  vocabolario e matrice, verbo, permesso sul passaggio, emissione, annullo), gli acquisti (§5) e
  «come si porta un documento» (§5). La tabella del §3.1 diventa il §10 della guida, «a che punto è
  ogni documento», **riverificata il 2026-10-25 sulla doc auto-generata** (verbi con e senza
  `fn_guard_azione`, guard che leggono o no la matrice): nessuna differenza dal censimento del
  2026-10-21, oltre alla nascita in bozza ora presente ovunque. In più la riga degli acquisti
  (vocabolario e nascita sì, nessun guard di transizione);
* le otto guide dei documenti (`gestione-preventivi`, `-ordini`, `-ddt`, `-contratti`,
  `-offerte-commerciali`, `-commesse`, `fatturazione`, `gestione-listini`): il rimando nell'header e,
  in testa alla sezione degli stati, una riga che manda alle regole comuni e al §10. Il loro corpo
  **non** è riscritto: descrive com'è oggi ogni documento, e si riallinea nel giro di quel documento;
* `fatturazione.md`, regole del modello lotti: R-1 (il lotto fermo non diventa definitivo) mancava
  dalla guida, c'era solo nella scheda del guard;
* `readme.md` (regole trasversali ai documenti) e `mkdocs.yml` (nav, accanto a numerazione e IVA).

⚠️ La guida descrive come regola ciò che Tid ha deciso, anche dove i documenti non ci sono ancora
arrivati: il §10 dice dove. È la condizione del §5 («da lì una proposta che non è nella guida si
dichiara come revoca»), e differisce dalla norma delle guide («lo stato attuale») in modo
dichiarato.

**Domande per il piano (punto 4)**, emerse scrivendo la guida; la guida non le decide:

| # | Domanda | Proposta |
| --- | --- | --- |
| S-1 | **La porta.** La guida dei permessi (§7.4) dice che il verbo protegge solo se non si aggira, e per i domini nuovi toglie all'app `INSERT`/`UPDATE` sulle tabelle. Una testata di documento però l'app la scrive anche per i campi ordinari (CRUD). Come si chiude la sola colonna di stato? (a) privilegio per colonna; (b) un guard sulla colonna di stato che passa solo se attraversato dal verbo (`script.fn_is_proprietario_tabella`, già previsto dal §7.4 per questo); (c) nessuna porta, il verbo è la strada ma non l'unica | **(b)**: (a) si scontra col loop dei grant di `ci_apply`, che rimette i privilegi di tabella; (c) lascia che un `UPDATE` del backend salti il permesso, cioè il buco che M-1 chiude. Un guard solo, montato su ogni testata come quello della nascita ✅ **Deciso da Tid il 2026-10-25: (b)** |
| S-2 | **Un verbo per documento, o uno solo?** Il verbo di stato legge matrice e azione dalla riga (M-3): il suo corpo è lo stesso per ogni documento. (a) un BB comune che riceve il documento (la sua sorgente) e lo stato, con i verbi specifici (annulla, conferma, emetti) che lo chiamano; (b) un verbo per documento, come oggi DDT, preventivo e commessa | **(a)**: è la regola del §5 («prima di ricopiare una regola nei guard o nelle capability, un BB comune che legge la matrice») e la causa del §1; i tre verbi di oggi diventano chiamate al BB nel giro del loro documento ✅ **Deciso da Tid il 2026-10-25: (a)** |

✅ Tid, 2026-10-25: guida approvata; fermo allentato (C, in PROJECT_CONTEXT); primo documento il DDT
col DDT d'acquisto; S-1 (b), S-2 (a). Il giro si scrive col via di Tid.

---

## 7. Giro 5: il DDT al modello — ricognizione e piano (2026-10-25)

Via di Tid il 2026-10-25 («ok procedi»). Ricognizione sul codice (doc auto-generata, `backend/`,
`db/pgtap/`), prima di scrivere i changeSet.

### 7.1 Com'è oggi

* **Verbo.** `vendite.fn_cambia_stato_ddt` (DEFINER) fa ogni passaggio e, sulle bolle che muovono
  merce, i prelievi e i movimenti. Il permesso è scritto nel corpo: `emetti_ddt` verso EMESSO e per
  EMESSO → ANNULLATO, `registra_magazzino` alla consegna di un trasferimento che muove merce; gli altri
  passaggi senza controllo («al permesso del backend»). `fn_annulla_ddt` ritira i legami e chiama il
  verbo. Il backend passa già **sempre** dal verbo (giro A1 del 2026-10-12).
* **Porta.** Esiste già, ma a metà: la Regola 3 di `trgfn_ddt_guard_transizione` (GUC
  `zeroerp.ddt_cambio_stato` + `script.fn_is_proprietario_tabella`, `E_DDT_STATO_SOLO_DA_VERBO`) chiude
  solo emissione, annullo dell'emesso e consegna del trasferimento, e solo se la bolla muove merce. La
  stessa forma, copiata, sta sul reso (`E_RESO_STATO_SOLO_DA_VERBO`) e sui documenti interni di
  magazzino (`E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`): tre copie.
* **Chi scrive lo stato della bolla senza il verbo:** `vendite.fn_conferma_reso` (CONSEGNATO → RESO) e
  `vendite.fn_annulla_reso` (RESO → CONSEGNATO), i due passaggi di processo (`manuale = false`) della
  matrice; `dbops.fn_pgtap_porta_a_stato`; nei pgTAP 19 file con un `UPDATE` diretto e 12 con
  `porta_a_stato` sulla bolla (conteggio del 2026-10-25, per dimensionare il porting).
* **Capability.** `script.fn_available_actions_ddt` legge la matrice, ma non guarda il permesso: un
  bottone «Emetti» compare anche a chi non ha `emetti_ddt` (§12.1 della linee guida SQL: permesso ⇒
  nascondi).
* **Emissione (M-2).** `/emetti/` chiama `ddt_service.emetti`, che è `cambia_stato(…, 'EMESSO')`: la
  rotta generica `cambia-stato/` accetta EMESSO allo stesso modo.
* **La mappa dei documenti** (testata → colonna di stato, vocabolario, matrice) esiste in un posto
  solo, dentro `dbops.fn_pgtap_porta_a_stato`. Il verbo comune ne ha bisogno: è la seconda occorrenza.
* **DDT d'acquisto.** `acquisti.ddt` usa `config.stati_doc_ddt` e ha solo il trigger della nascita:
  nessun guard di transizione, nessun verbo, nessuna capability, nessun backend, zero righe. ⚠️ La
  decisione D-3 di [analisi-simmetria-ordini-acquisto](analisi-simmetria-ordini-acquisto.md)
  (Tid, 2026-09-02) dice che gli stati condivisi descrivono un documento **emesso da noi**, e che
  vendite e acquisti si separano con un satellite per ambito (`config.stati_doc_ddt_ambiti`, `ambito`
  nella chiave delle transizioni). Il satellite non c'è ancora.
* ⚠️ **Un'altra sessione** lavora in questo momento su
  [brief-db-pgtap-reso-costruito](../work-done/brief-db-pgtap-reso-costruito.md) (giro 2): una trentina di pgTAP di
  bolla e reso modificati e non committati, `20261025-05`/`-06` nuovi. Sono gli stessi file che questo
  giro deve portare.

### 7.2 Il piano (da confermare con le domande del §7.3)

**I pezzi comuni** (schema `script`, montati sulla bolla e riusati dai documenti dei giri dopo):

| Pezzo | Che cosa fa |
| --- | --- |
| la mappa dei documenti | testata → colonna di stato, vocabolario, matrice; estratta da `fn_pgtap_porta_a_stato`, che la legge (la copia si ritira) |
| l'azione sulla riga (M-3) | colonna `azione_processo_codename` sulla matrice (FK a `config.azioni_processo.permission_codename`, la chiave stabile: §6b delle linee guida), valorizzata nel CSV: emissione e annullo dell'emesso = `emetti_ddt` |
| la prima riga del verbo | legge la riga del passaggio, applica il permesso (l'azione della riga; senza azione il permesso sul documento resta al backend, niente `fn_guard_livello`: l'operatore dei pgTAP è bloccato su più aree) e rifiuta i passaggi di processo chiesti a mano |
| la primitiva di scrittura | apre la porta per **quel** documento e scrive lo stato. `SECURITY INVOKER` e non riservata: la porta chiede anche il proprietario, quindi dall'app si ferma da sola |
| la porta (S-1) | un guard sulla colonna di stato: passa solo dalla primitiva (GUC + proprietario). Prende il posto della Regola 3 della bolla, che si ritira |
| il permesso nelle capability | il bottone di un passaggio con azione si nasconde a chi non ce l'ha, dalla stessa riga |

**La bolla:** `fn_cambia_stato_ddt` comincia dalla prima riga comune e scrive con la primitiva; restano
suoi i prelievi e i movimenti. `fn_conferma_reso`/`fn_annulla_reso` scrivono lo stato della bolla con
la primitiva. `fn_pgtap_porta_a_stato` passa dal verbo per i documenti con la porta. pgTAP portati nello
stesso giro.

**Richiesta al BE** (da completare col percorso intero): `cambia-stato/` rifiuta EMESSO (M-2, solo
`/emetti/`); il 403 dell'endpoint legge l'azione dalla riga del passaggio, con la funzione del DB; i
codici nuovi in `error_policies_generated.py`.

### 7.3 Domande per Tid

Una alla volta, nel giro di domande del 2026-10-25.

* ✅ **T-1. L'altra sessione** — Tid: **B**, si parte subito; l'altra sessione ha committato
  (`2e1a6aaac`, 2026-10-25), l'albero è libero.
* ✅ **T-2. Il DDT d'acquisto** — Tid: **non si fa** in questo giro («il ddt acquisto no, non
  farlo»). Il giro porta la sola bolla di vendita; il DDT d'acquisto aspetta il satellite per ambito
  (D-3 di analisi-simmetria-ordini-acquisto). ⚠️ È un'eccezione dichiarata alla regola del §5 «nello
  stesso giro»: i pezzi comuni nascono generici, così il DDT d'acquisto li monta senza copie.
* ✅ **T-3. Il reso** — Tid: **A**, entra nel giro: il pezzo comune della porta sostituisce la sua
  copia (`E_RESO_STATO_SOLO_DA_VERBO`), `conferma_reso` passa sulla riga del passaggio. I documenti
  interni di magazzino restano fuori (nessun vocabolario degli stati in tabella): la loro porta resta,
  dichiarata.
* ✅ **T-4. `registra_magazzino` alla consegna del trasferimento** — Tid: **A**, resta nel verbo della
  bolla come permesso dell'operazione di magazzino dentro il passaggio; la riga CONSEGNATO non porta
  azioni. Scritto nella guida del modello §6 come regola.

### 7.4 Scritto (2026-10-25)

| # | Cosa |
| --- | --- |
| `-07` | NUOVO `script.fn_doc_stato_modello(regclass)`: la mappa, estratta da `fn_pgtap_porta_a_stato` |
| `-08` | colonna `azione_processo_codename` (FK al codename) su `config.transizioni_stati_ddt` e `_reso`; valori nei CSV, mirror `20260709-10` e `20260713-41` con la colonna e `nullValue: "NULL"` |
| `-09` | NUOVO `script.fn_doc_passaggio`: la riga viva del passaggio (manuale, azione), lettore unico |
| `-10` | NUOVO `script.fn_guard_passaggio`: prima metà del verbo (processo → `E_DOC_PASSAGGIO_DI_PROCESSO`; azione → `fn_guard_azione`) |
| `-11` | NUOVO `script.fn_doc_scrivi_stato`: seconda metà, la scrittura attraverso la porta (GUC `zeroerp.doc_cambio_stato` = `oid:id`, rimessa com'era) |
| `-12`, `-13` | NUOVO `script.trgfn_doc_stato_solo_dal_verbo` (`E_DOC_STATO_SOLO_DAL_VERBO`), montato `_a05_` su `vendite.ddt` e `vendite.resi` |
| `-14`, `-15` | i guard di transizione di bolla e reso perdono la loro porta del registro (Regola 3 e Regola 2): la copia si ritira |
| `-16` | `fn_cambia_stato_ddt` sul verbo comune; resta suo `registra_magazzino` (T-4) |
| `-17`, `-18` | `fn_conferma_reso`, `fn_annulla_reso` sul verbo comune; il flip della bolla (RESO ↔ CONSEGNATO) dalla scrittura comune |
| `-19` | `fn_pgtap_porta_a_stato`: la mappa comune; sotto la porta, i passi col verbo (solo manuali) e l'azione concessa |
| `-20`, `-21` | capability di bolla e reso: il passaggio con l'azione si nasconde a chi non ce l'ha |

Dati: `E_DOC_STATO_SOLO_DAL_VERBO` e `E_DOC_PASSAGGIO_DI_PROCESSO` (TECNICO) in `messaggi_errore.csv` e
`codici_errore.csv`; `E_DDT_STATO_SOLO_DA_VERBO` e `E_RESO_STATO_SOLO_DA_VERBO` obsoleti dal 2026-10-25.
Doc: cinque pagine `manual` nuove (script), le schede del reso, la guida del modello (§5, §6, §10),
`gestione-ddt` (§4.4), la tabella dei builder della guida pgTAP. pgTAP nuovo:
`script/test-doc-verbo-comune-e-porta-v1` (20).

**Attese cambiate, dichiarate:**

* l'annullo di un reso in **bozza** non chiede più `conferma_reso` (M-4: non è un passaggio pesante); il
  backend lo chiedeva staticamente (`ApiResoAnnulla.post_permission`), vedi la richiesta;
* una conferma (o un annullo) di un reso che non ha la riga del passaggio (già confermato, già annullato)
  risponde col codice dello stato (`E_RESO_STATO_NON_CONFERMABILE` / `_NON_ANNULLABILE`) anche a chi non
  ha l'azione: prima `E_PERMESSO_NEGATO`;
* **ogni** cambio di stato diretto di bolla e reso è rifiutato, non più solo quelli del magazzino;
* le capability di bolla e reso non mostrano più «Emetti» / «Conferma» / «Annulla» (dell'emesso o del
  confermato) a chi non ha l'azione.
* pgTAP, attese della regola ritirata (dichiarate nei file): `magazzino/test-ddt-scarico-v1` 4 e 16 (la
  bolla senza merce non passa più dall'`UPDATE` diretto), `test-ddt-trasferimento-v1` 8,
  `test-reso-carico-v1` 11 → `E_DOC_STATO_SOLO_DAL_VERBO`; `vendite/test-ddt-causale-immutabile-v1` 4:
  provava che il guard della causale legge lo stato VECCHIO quando causale e stato cambiano nella stessa
  istruzione. ⚠️ Con la porta quell'istruzione non si può più scrivere da fuori (il verbo scrive solo lo
  stato): il test ora asserisce il rifiuto della porta. ✅ **Confermato da Tid il 2026-10-25**: il test
  discrimina ancora, perché il lock della causale (`trg_ddt_a05_lock_fuori_bozza_upd`) scatta prima
  della porta (`…a05_stato_solo_dal_verbo_upd`): un lock che leggesse lo stato nuovo rifiuterebbe con la
  sua frase. La dipendenza dall'ordine dei nomi è scritta nel test. Tre test, dopo l'apply e prima del porting, erano verdi **per la ragione sbagliata** (prendevano il P0001 della porta
  invece del guard che provavano: `test-fn-check-ddt-emittibile-v1` 9, `test-ddt-solo-trasporto-causale-v1`
  2 e 3) passano dal verbo e cadono sul guard vero.

### 7.5 Incidente dell'apply (2026-10-25, 01:53)

Tid ha applicato `-07` … `-21` su dbdev e scratch mentre la prova era in corso; il migrate si è fermato
nel mirror `20260709-10`: la colonna nuova aveva celle vuote e il mirror `nullValue: ""`, Liquibase ha
scritto `''` e la FK l'ha rifiutata. ⛔ Era una trappola già scritta (memoria del 2026-09-28, mirror
`20260709-11`), e la prova col seed simulato in Python non la vede. Corretto: `nullValue: "NULL"` nei
due mirror e il token `NULL` nelle celle. Stato dopo l'incidente: i changeSet `-07` … `-21` applicati, le
azioni sulle righe **ancora NULL** fino al prossimo migrate (il mirror è `runOnChange`).

### 7.6 Richiesta al team BE (elenco chiuso)

Percorso censito: `ddt_service.cambia_stato` / `emetti`, `ApiDdtCambiaStato`, la fabbrica `/emetti/`
(`emetti_post_permission`), `ApiResoConferma` / `ApiResoAnnulla`, `ddt_repository`, il catalogo dei
messaggi di ripiego.

1. **M-2, solo da «Emetti».** `ddt_service.cambia_stato` (e `ApiDdtCambiaStato`) rifiuta `EMESSO`: la
   bolla si emette solo da `/emetti/`, che produce numero e PDF insieme. Codice: un `*_VALIDATION`
   del dominio (400), la frase dice di usare «Emetti».
2. **M-3, il 403 dalla riga del passaggio.** Il permesso dell'endpoint di un cambio di stato non si
   dichiara più a mano: si legge da `script.fn_doc_passaggio(<testata>, <stato corrente id>, <stato
   chiesto id>)` (colonna `azione_processo_codename`; NULL = basta `model_permission`) e si controlla
   con la stessa regola del DB, prima di aprire la transazione. Vale per `ApiDdtCambiaStato` (oggi
   nessun `post_permission`: l'annullo dell'emesso arrivava al DB senza 403 prima), per
   `ApiResoConferma` e `ApiResoAnnulla` (oggi `post_permission = "conferma_reso"` fisso: con M-4
   l'annullo di una bozza **non** lo chiede più, e il 403 statico lo rifiuterebbe), e per l'`/emetti/`
   della bolla (`emetti_post_permission="emetti_ddt"`: coincide con la riga, ma è una seconda copia).
3. **I codici.** Rigenerare `error_policies_generated.py`: `E_DOC_STATO_SOLO_DAL_VERBO`,
   `E_DOC_PASSAGGIO_DI_PROCESSO` (TECNICO, frasi chiuse o col solo identificativo del documento);
   `E_DDT_STATO_SOLO_DA_VERBO` / `E_RESO_STATO_SOLO_DA_VERBO` obsoleti (le due voci di
   `error_messages_fallback.py` e il commento di `ddt_repository.cambia_stato` si allineano).
4. **Da sapere, nessuna modifica attesa:** `cambia_stato` verso `RESO` (passaggio di processo) ora
   risponde `E_DOC_PASSAGGIO_DI_PROCESSO`; le capability nascondono le azioni senza permesso (il
   frontend non cambia: riceve meno azioni).
5. **I test DB che scrivono lo stato della bolla con un `UPDATE` diretto** (censiti il 2026-10-25, ora
   rifiutati con `E_DOC_STATO_SOLO_DAL_VERBO`): `apps/vendite/tests/db/_ddt_consegnato.py` (righe 75-77,
   EMESSO → SPEDITO → CONSEGNATO) e `apps/vendite/tests/db/test_date_consegna_righe_db.py` (riga 120).
   Si portano a `dbops.fn_pgtap_porta_a_stato('vendite.ddt', <id>, '<stato>')`, che passa dal verbo e
   concede all'utente del contesto l'azione del passaggio; senza un utente di contesto il verbo non vede
   la bolla (`E_DDT_NOT_FOUND`).

### 7.7 Debito emerso e chiuso nello stesso giro

* **`-22`: la frase del rifiuto di matrice di bolla e reso.** `E_STATO_DDT_TRANSIZIONE_NON_VALIDA` e
  `E_STATO_RESO_TRANSIZIONE_NON_VALIDA` hanno due segnaposto (stato da, stato a), ma i due guard
  passavano anche l'id del documento: a video «da 14566 a EMESSO» per un EMESSO → CONSEGNATO. Difetto di
  prima del giro, visto nel porting; corretto qui perché i due corpi erano appena stati riscritti
  (`-14`/`-15`, già applicati: non si toccano). Provato in transazione: compila, `plpgsql_check` pulito.
* Lasciato: `E_DDT_EMISSIONE_SENZA_RIGHE` riceve id e numero per un segnaposto solo, e mostra l'id; in
  bozza il numero non c'è ancora, e l'id è l'informazione giusta.

### 7.8 Applicato e verde (2026-10-25)

Tid: `-07` … `-22` applicati su dbdev e scratch (il mirror `20260709-10` è ripartito dopo la correzione
del §7.5, le azioni sulle righe sono valorizzate), corsa pgTAP verde. Un solo rosso visto come app prima
della corsa finale, corretto: il test 2 del presidio nuovo confrontava il **testo** di un `regclass`, che
dipende dal `search_path` (come app `config` ci sta e lo schema sparisce); ora i test 2 e 9 confrontano i
`regclass`. La corsa come app ha confermato anche i due test della porta (19, 20) che da owner non si
potevano provare.

### 7.9 Fatto dal team BE (2026-10-25) e richiesta al team DB per il giro dopo

**Fatto** (`dev/backend-tid`, da committare), sulla richiesta del §7.6:

1. **M-2.** `ddt_service.cambia_stato` rifiuta `EMESSO` con `400 E_DDT_VALIDAZIONE` (campo
   `stato_codice`, «La bolla si emette solo da «Emetti»…»); `emetti` passa da un corpo comune con
   `stato_del_modello="emissione"`. Frontend e smoke usavano già `/emetti/`.
2. **M-3, il 403 dalla riga.** BB nuovo in `core` (ok Tid, 2026-10-25): la view dichiara
   `post_passaggio = PassaggioDocumento(testata, documento_kwarg, stato_chiesto)` e
   `ZeroERPPermission` legge l'azione con `script.fn_doc_passaggio` (stato corrente → stato chiesto)
   prima della transazione. Con l'azione decide lei (semantica di `post_permission`); senza riga o
   senza azione, livello sul documento. Montato su `ApiDdtCambiaStato`, `/emetti/` della bolla
   (`emetti_passaggio` della factory documenti, esclusivo con `emetti_post_permission`),
   `ApiResoConferma`, `ApiResoAnnulla`. Le copie ritirate: `post_permission = "conferma_reso"` (due) e
   `emetti_post_permission="emetti_ddt"`. Catalogo BB, `api.md`, `api_ddt`, `api_resi`,
   `api_documenti_per_sorgente` aggiornati.
3. **Codici.** `error_policies_generated.py` rigenerato (i due nuovi, i due ritirati), ripiego senza
   segnaposto per `E_DOC_STATO_SOLO_DAL_VERBO` / `E_DOC_PASSAGGIO_DI_PROCESSO`, nota di ritiro sulle due
   voci vecchie, commento di `ddt_repository.cambia_stato` allineato.
5. **Test DB.** `_ddt_consegnato.py`, `test_date_consegna_righe_db.py` e (non in elenco)
   `test_ddt_cambia_stato_db.py`, che passava a EMESSO dal cambio stato generico: tutti dal verbo.

Emerso e non in richiesta: la sonda di `test_origine_ordine_sorgente_db` cercava
`dbops.fn_pgtap_crea_ordine` a tre argomenti; la firma è a quattro (`p_data`) da `fae207c9e`
(brief-db-pgtap-bolla-e-reso-costruiti, che dichiarava «nessuna ricaduta sul backend»). La sonda
falliva sull'oggetto mancante, come vuole BE-1: allineata.

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6923 test, verdi tranne 2 che **non sono di
questo giro**: `test_error_policies_divergenza_db` e `test_error_codes_db_policy_guardrail` vedono 5
codici `E_INDIRIZZO_*` presenti su dbdev ma non in git (brief-db-unicita-civico-indirizzi-dettaglio, in
corso). Si rigenera la policy dopo il suo push. mypy (cricchetto) e ruff puliti. Presidi nuovi:
`core/tests/api/test_permesso_passaggio.py`, `core/tests/test_passaggio_rotte.py` (il kwarg è nella
rotta, nessun `post_permission` accanto, la testata è sul modello), `vendite/tests/db/test_permesso_passaggio_db.py`.
⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Richiesta al team DB, per il giro dopo** (Tid, 2026-10-25). Per rispondere 403 il backend deve
passare a `script.fn_doc_passaggio` due **id** di stato, e oggi li ricava da sé componendo SQL sulla
mappa (`DocumentoModelloRepository.azione_del_passaggio`):

* lo stato **chiesto** arriva come codice e si traduce in id leggendo `codice_interno` del vocabolario.
  La colonna c'è, UNIQUE, negli otto vocabolari, ma `script.fn_doc_stato_modello` non la dichiara: è
  un pezzo del contratto del vocabolario che vive solo in Python;
* lo stato **corrente** si legge da `<testata>.<colonna_stato>`, con gli identificatori presi dalla
  mappa.

Si chiede un lettore DB unico per la traduzione codice → id dello stato di una testata (per esempio
`script.fn_doc_stato_id(p_testata regclass, p_codice text) RETURNS bigint`, il gemello di
`fn_stato_iniziale_id`). Da valutare se esporre direttamente la domanda intera,
`script.fn_doc_azione_passaggio(p_testata regclass, p_documento_id bigint, p_stato_a_codice text)`:
il backend non comporrebbe più SQL, e quel lettore servirebbe ai giri dei documenti successivi così
com'è. In entrambi i casi il backend cambia **solo** il repository (una funzione), e i presidi restano.

✅ **Deciso da Tid il 2026-10-25: sì, la colonna** (emerso dalla revisione critica del giro BE). M-2 («si emette solo
da Emetti») vale per **tutti** i documenti che si stampano, ma nessun vocabolario dice **quale** stato
è l'emissione: `config.stati_doc_ddt` ha `iniziale`, `is_abortito`, `fase`, `pdf_mode`, non un segno
dell'emissione. Il backend lo scrive quindi come letterale `EMESSO` (`ddt_service.STATO_EMESSO`, una
sede sola), e ogni documento dei giri dopo ne avrebbe uno suo: è la copia per documento che il §1
descrive. Proposta: il vocabolario dichiara lo stato di emissione come dichiara l'iniziale (colonna
`emissione boolean` con indice unico parziale, oppure un segno sulla riga della matrice), e il backend
lo legge invece di scriverlo: il cambio stato generico rifiuta lo stato di emissione di qualunque
documento, senza un letterale per documento. Il PDF nasce nel backend, quindi il rifiuto resta lì: al
DB si chiede solo di **dire** quale stato è l'emissione.

**Richiesta al team DB (seconda, insieme a quella sopra):**

1. colonna `emissione boolean NOT NULL DEFAULT false` sui vocabolari degli stati dei documenti che si
   stampano, con indice unico parziale (al più uno per vocabolario) e il CHECK «solo su una riga
   attiva», nella stessa forma di `iniziale` (P-1, `20261024-07`); valori dai CSV di `80_data` e
   colonna dichiarata nei mirror (⚠️ `nullValue`, §7.5). Quali vocabolari: quelli dei documenti che
   passano da «Emetti» (oggi la factory `/emetti/`: preventivo, offerta, contratto, ordine, DDT); il
   team DB verifica il perimetro sulla guida §7 e lo dichiara;
2. un lettore unico, gemello di `script.fn_stato_iniziale_id`: per esempio
   `script.fn_stato_emissione_id(p_testata regclass)`, NULL se il documento non si emette;
3. se si sceglie la domanda intera del punto sopra (`fn_doc_azione_passaggio`), può valere la pena
   esporre anche «il passaggio chiesto è l'emissione?», così il backend fa una chiamata sola.

**Ricaduta sul backend, al giro dopo:** `ddt_service.STATO_EMESSO` si ritira; il cambio stato generico
rifiuta lo stato di emissione letto dal DB, e `/emetti/` lo prende dallo stesso lettore (la factory non
riceve più lo stato in `emetti_passaggio`, solo la testata). Il presidio diventa generico su tutti i
documenti della factory.

---

## 8. Giro 6: il preventivo al modello — ricognizione e piano (2026-10-25)

✅ **Deciso da Tid il 2026-10-25:** il documento del giro è il **preventivo** (nessun gemello d'acquisto).
Il lettore del §7.9 si fa in **due pezzi**, come il backend chiedeva: `script.fn_doc_stato_id(p_testata
regclass, p_codice text)` (codice → id dello stato di una testata, il BB) e la domanda intera
`script.fn_doc_azione_passaggio(p_testata, p_documento_id, p_stato_a_codice)`, che lo compone e dice anche
se il passaggio è l'emissione. Il backend sceglie il lettore che gli serve; nessuno dei due compone SQL
sulla mappa. Lo sviluppo parte col via di Tid.

### 8.1 Com'è oggi (doc auto-generata e `backend/`, 2026-10-25)

* **Verbo.** `vendite.fn_cambia_stato_preventivo(id, codice, user)` è **INVOKER**, valida la matrice nel
  corpo (copia del guard di transizione, «voluta» dal 2026-08-05), scrive lo stato con un `UPDATE`.
  Nessun controllo di permesso. Codice → id scritto nel corpo (`codice_interno = p AND attivo`).
* **Guard di transizione** `trgfn_preventivi_guard_transizione`: matrice, condizioni dell'emissione
  (`fn_check_preventivo_emettibile`), prezzi autorizzati all'accettazione. Letterali `'EMESSO'`,
  `'ACCETTATO'`: sono condizioni di un passaggio, restano (guida §7, «le condizioni stanno sul passaggio»).
* **Annullo.** `fn_annulla_preventivo` (DEFINER) ritira i legami e chiama il verbo: già al modello.
* **Scrittori dello stato senza il verbo:** `vendite.fn_preventivo_proietta_stato_smistamento`
  (ACCETTATO ↔ EVASO, i passaggi di processo 4→10 e 10→4, `manuale = false`), consumata da push a
  ordine, ritiro dei legami e trigger della commessa. Il passaggio di processo EMESSO → SCADUTO (2→7) è
  nella matrice ma **nessuno lo scrive** (né DB né backend): si dichiara, non si tocca.
* **Azione.** `cambia_stato_preventivi` («emetti/accetta/rifiuta/annulla»), su **ogni** passaggio e solo
  nel backend: `ApiPreventivoStato`, `ApiPreventivoStatoDaPratica`, `ApiPreventivoCollegaPratica` (che
  non è un cambio di stato), `/emetti/` della factory (`emetti_post_permission`). Nessun profilo la
  riceve dai seed. È la divergenza dalla guida §6 («una azione, sui passaggi pesanti»).
* **Emissione (M-2).** Già lato BE: `preventivi_service.cambia_stato` rifiuta `'EMESSO'` con un
  letterale suo, `emetti` passa dal repository.
* **Codice → id dello stato, copie censite:** `fn_cambia_stato_preventivo`, `fn_cambia_stato_ddt`,
  `dbops.fn_pgtap_porta_a_stato`, `DocumentoModelloRepository.azione_del_passaggio` (BE). Quattro: il BB
  `fn_doc_stato_id` le ritira tutte nello stesso giro (quelle DB qui, quella BE nella richiesta).
* **pgTAP:** 6 file scrivono lo stato del preventivo con un `UPDATE` diretto, 39 passano da
  `porta_a_stato` o dal verbo (conteggio del 2026-10-25, per dimensionare il porting).
* ⚠️ **Controesempio, lato BE:** `cambia_stato` dichiara «ACCETTATO → ACCETTATO (no-op stato)» per
  aggiornare la modalità di fatturazione, ma poi chiama il verbo con lo stesso stato: la matrice non ha
  la riga 4→4 e il verbo risponde `E_PREV_TRANSIZIONE_NON_AMMESSA`. Va nella richiesta al BE.

### 8.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| `fn_doc_stato_id` | NUOVO BB in `script`: l'id dello stato **attivo** con quel `codice_interno` nel vocabolario della testata (dalla mappa), NULL se non c'è (decide il chiamante); testata fuori mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| `emissione` | colonna `boolean NOT NULL DEFAULT false` su `stati_doc_preventivi`, `_offerte`, `_contratti`, `_ordini`, `_ddt` (i documenti della factory `/emetti/`, guida §7), indice unico parziale e CHECK «solo su una riga attiva» come `iniziale`; valori dai CSV, mirror con la colonna (⚠️ `nullValue`, §7.5) |
| `fn_stato_emissione_id(p_testata)` | NUOVO lettore, gemello di `fn_stato_iniziale_id`: NULL se il documento non si emette |
| `fn_doc_azione_passaggio` | NUOVO: stato corrente del documento (dalla mappa) + `fn_doc_stato_id` + `fn_doc_passaggio`; restituisce `manuale`, `azione_processo_codename`, `emissione` (lo stato chiesto è quello di emissione). Nel perimetro di chi chiama (INVOKER) |
| matrice del preventivo | colonna `azione_processo_codename`, valori dal CSV: l'azione sui passaggi pesanti (U-1) |
| verbo | `fn_cambia_stato_preventivo` sul verbo comune: `fn_guard_passaggio` in testa, `fn_doc_scrivi_stato` per scrivere; la copia della matrice nel corpo si ritira (la fa il guard). Diventa DEFINER come la bolla: la porta vuole il proprietario |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.preventivi` |
| processo | `fn_preventivo_proietta_stato_smistamento` scrive con `fn_doc_scrivi_stato` (sola seconda metà, come il flip della bolla dal reso) |
| capability | `fn_available_actions_preventivo`: il passaggio con l'azione si nasconde a chi non ce l'ha |
| copie | `fn_cambia_stato_ddt` e `fn_pgtap_porta_a_stato` usano `fn_doc_stato_id`; `porta_a_stato` passa dal verbo per il preventivo (lo dice già il catalogo, porta montata) |
| pgTAP | i 6 `UPDATE` diretti a `porta_a_stato`; test nuovo dei due lettori e della colonna; i presidi del verbo comune estesi al preventivo |

**Richiesta al BE** (si scrive col percorso intero, a giro DB provato): `post_passaggio` su
`ApiPreventivoStato`, `ApiPreventivoStatoDaPratica` e `/emetti/` (le copie di `cambia_stato_preventivi`
si ritirano; `ApiPreventivoCollegaPratica` resta da decidere col BE, non è un passaggio); il repository
del §7.9 sui lettori nuovi; `STATO_EMESSO` e il letterale del preventivo ritirati, il rifiuto
dell'emissione letto dal DB per tutti i documenti della factory; il controesempio ACCETTATO → ACCETTATO;
i codici rigenerati.

### 8.3 Domande per Tid

✅ **Decise da Tid il 2026-10-25: U-1 (a), U-2 sì, U-3 sì, come da proposta; via allo sviluppo.**

* **U-1. L'azione del preventivo.** (a) azione **nuova** `emetti_preventivo` («emette un preventivo o
  annulla un preventivo emesso»), sulle righe 1→2 (emissione), 2→9 e 4→9 (annullo dell'emesso e
  dell'accettato), e `cambia_stato_preventivi` obsoleta; (b) si tiene `cambia_stato_preventivi` sulle
  stesse tre righe, cambiandole il significato. **Proposta (a)**: il gemello di `emetti_ddt`, e un
  profilo che oggi ha «cambia stato» per accettare e rifiutare non si ritrova in silenzio il potere di
  emettere e annullare.
* **U-2. ACCETTATO → ANNULLATO chiede l'azione?** La guida §6 dice «l'annullo di un documento emesso»;
  l'accettato è emesso. **Proposta: sì** (è dentro U-1).
* **U-3. `fn_doc_stato_id` legge solo gli stati attivi?** **Proposta: sì**: risponde alla domanda «verso
  quale stato vado», e uno stato spento non è una destinazione; i verbi di oggi filtrano già così (il
  repository BE no: è la copia che si ritira).

### 8.4 Scritto (2026-10-25)

| # | Cosa | Stato |
| --- | --- | --- |
| `-37` | colonna `emissione` su `stati_doc_preventivi`, `_offerte`, `_contratti`, `_ordini`, `_ddt`, con indice unico parziale e CHECK «attivo»; valori nei CSV (EMESSO, EMESSA, ATTIVO, CONFERMATO, EMESSO), dichiarata nei sei mirror dei vocabolari | applicato |
| `-38` | colonna `azione_processo_codename` su `config.transizioni_stati_preventivi`; nel CSV `emetti_preventivo` sulle righe 1→2, 2→9, 4→9; i due mirror con la colonna e `nullValue: "NULL"` | applicato |
| CSV | `azioni_processo`: `emetti_preventivo` (id 40) nuova; `cambia_stato_preventivi` marcata **obsoleta** nella descrizione ma **attiva** (vedi §8.6) | applicato su dbdev |
| `-39` | NUOVO `script.fn_doc_stato_id(testata, codice)`: codice → id dello stato attivo (U-3) | applicato |
| `-40` | NUOVO `script.fn_stato_emissione_id(testata)`: lo stato di emissione, NULL se il documento non si emette | applicato |
| `-41` | NUOVO `script.fn_doc_azione_passaggio(testata, id, codice)`: la domanda intera del backend (stati, emissione, riga del passaggio) | applicato |
| `-42` | `fn_cambia_stato_preventivo` sul verbo comune: firma (id, stato), DEFINER col predicato del perimetro, `fn_guard_passaggio` + `fn_doc_scrivi_stato`; ritirate dal corpo le copie della matrice e dell'annullabilità | applicato |
| `-43` | `fn_annulla_preventivo` chiama il verbo con la firma nuova | applicato |
| `-44` | `fn_cambia_stato_ddt`: codice → id e stato di emissione dai lettori comuni (nessun cambio di comportamento) | applicato |
| `-45` | `fn_preventivo_proietta_stato_smistamento`: ACCETTATO ↔ EVASO da `fn_doc_scrivi_stato`, DEFINER (§8.6) | applicato |
| `-46` | la porta montata su `vendite.preventivi` | applicato |
| `-47` | capability del preventivo: il passaggio con l'azione si nasconde a chi non ce l'ha; i motivi dell'emissione sulla colonna `emissione` | applicato |
| `-48` | `fn_pgtap_porta_a_stato`: il preventivo dal suo verbo, lo stato voluto da `fn_doc_stato_id` | applicato |
| `-49` | guard di transizione del preventivo: la regola «almeno una riga attiva» all'emissione (prima solo nel verbo: guida §7, «le condizioni stanno sul passaggio») | **da applicare** |
| `-50` | il verbo non ripete più la regola delle righe | **da applicare** |
| `-51` | COMMENT di `fn_stato_emissione_id`: i consumatori dopo `-49` | **da applicare** |
| `-52` | NUOVO builder `dbops.fn_pgtap_crea_preventivo_con_righe`: una riga valida e lo stato chiesto (gemello di quello dell'ordine) | **da applicare** |

Doc: tre pagine `manual` nuove (script), la guida del modello (riferimenti, §4, §7, §10), `gestione-preventivi`
§3.1 (chi cambia lo stato, quale permesso, SCADUTO), la tabella dei builder della guida pgTAP. pgTAP nuovo:
`script/test-doc-lettori-stato-e-preventivo-al-modello-v1` (22; il 22 è rosso da owner, verde come app).
Presidio del giro 5 esteso: `script/test-doc-verbo-comune-e-porta-v1` test 9 e 10 (la porta anche sul preventivo).

**Incidente (2026-10-25, 11:37).** Tid ha applicato `-37` … `-48` su dbdev e scratch mentre la regressione
girava; dopo l'apply ho ritoccato `-40` (COMMENT) e `-42` (tolta la regola delle righe), e i checksum non
tornavano. I due file sono riportati al contenuto applicato (corpo e COMMENT uguali al vivo su dbdev); le
modifiche stanno in `-50` e `-51`. ⚠️ **Sullo scratch** i mirror dei CSV non sono ripartiti: mancano
`emetti_preventivo` e i valori di `emissione` (dbdev li ha). Da rifare lo scratch prima della corsa pgTAP lì.

### 8.5 Regressione e porting dei pgTAP

Regressione da owner su dbdev, 399 file che toccano preventivo, bolla, capability, matrici e verbo comune: con
`-37` … `-48` applicati, i rossi dovuti al giro sono 21, in tre famiglie; `-49` … `-51` non cambiano nessun
esito. Il controesempio vero è il primo: **14 pgTAP emettevano preventivi senza righe**, perché
`porta_a_stato` scriveva lo stato con un `UPDATE` e la regola stava solo nel verbo. Ora lo stato passa dal
verbo e la regola dal guard, su ogni strada. Si portano al builder `-52`, non ricopiando la riga in ogni test
(criterio dei builder, §4-octies). Le altre due famiglie: 6 test con l'`UPDATE` diretto (ora la porta; si
portano al verbo, così provano ancora il guard) e i test con la firma vecchia del verbo.

Rossi **non** del giro, lasciati: i test «rosso da owner» (scope, porta) e `vendite/test-vw-dash-aperto-v1`
(chiede EVASO a `porta_a_stato`, che è un passaggio di processo: rosso anche prima del giro).
**Portato il 2026-10-25:** il caso (b), «CHIUSO, non abortito, non transitato», era un preventivo EVASO con
una riga residua, cioè uno stato che il modello non ammette più: EVASO lo scrive solo la proiezione dello
smistamento quando nessuna riga è RESIDUA, quindi un preventivo EVASO è anche transitato. Il caso ora è un
**contratto CESSATO** (esito POSITIVO, `is_transitato` NULL, il giudizio è sospeso), su un cliente suo per non
sovrapporsi al contratto ATTIVO del test 8, cessato a mano dalla matrice con `valido_al` = oggi. Lo stesso file emetteva due preventivi senza righe
(quello NEGATIVO e quello dell'emittente B): ora passano da `fn_pgtap_crea_preventivo_con_righe` sulla
testata del test, come i 9 del porting. Da lanciare (Tid).

**Portati (2026-10-25, tre agenti in parallelo), 22 file:** i 9 che scrivevano la testata a mano e la
emettevano senza righe passano a `fn_pgtap_crea_preventivo_con_righe(…, p_preventivo_id => …)`; i 5 col
builder in uno stato oltre la bozza passano al builder con le righe; 6 test con l'`UPDATE` diretto passano dal
verbo (con `emetti_preventivo` concessa) e provano ancora il **guard**, non la porta; il test del verbo e
quello dell'annullo con legami alla firma a due argomenti. Due test erano verdi per la ragione sbagliata e ora
discriminano: `test-fn-cambia-stato-preventivo` 7 e 8 (`throws_ok NULL` passavano sulla funzione
inesistente) e `test-preventivi-guard-transizione-v1` 3 (prendeva il P0001 della porta).
**Regressione finale da owner su dbdev, 400 file, con `-49` … `-52` in testa:** i 20 file rossi hanno gli
stessi test rossi di prima del porting (rossi da owner o rossi preesistenti), più il 22 del test nuovo,
rosso da owner per costruzione. Nessuna regressione.

**Attese cambiate nel porting, da guardare (Tid):**
* `vendite/test-preventivi-guard-transizione-v1` 6: contava due funzioni che sollevano
  `E_PREV_TRANSIZIONE_NON_AMMESSA` (verbo e guard); dal `-42` il verbo non ricopia la matrice, e il test ora
  asserisce che lo solleva **solo** il guard (sede unica);
* `vendite/test-fn-list-preventivi-da-pushare-v1` 7: «riga inattiva esclusa» costruiva un preventivo ACCETTATO
  con la sola riga spenta, che il modello non ammette più; ora il preventivo ha anche una riga attiva e il test
  asserisce **a livello di riga** (la spenta assente, l'attiva presente): più stretto, forma diversa;
* `script/test-fn-available-actions-preventivo-v1` 2: un ACCETTATO «senza righe» con la sola azione `annulla`
  non si costruisce più (senza residuo il preventivo è EVASO); con la riga di merce compare anche
  `genera_ordine`, e l'attesa è ora `["annulla","genera_ordine"]`. Il test 8, che leggeva un motivo da quel
  preventivo, lo legge ora dal preventivo in bozza, per non perdere una sorgente in silenzio;
* `dbops/test-fn-pgtap-crea-preventivo-v1`: due test in più (5b: il parametro di stato provato su ANNULLATO
  dalla bozza; 6b: il builder senza righe si ferma sull'emissione).

### 8.6 Attese cambiate e debiti, dichiarati

* **La proiezione dello smistamento è DEFINER** (`-45`). Prima un preventivo che chi chiamava non vedeva non si
  proiettava; ora sì, perché lo stato è la conseguenza dei residui, non una scelta di chi chiama. Il perimetro di
  chi agisce lo controllano i consumatori (il trigger delle righe di commessa legge sotto la RLS). EXECUTE resta
  PUBLIC: la chiama quel trigger per chiunque scriva le righe di commessa, anche un ruolo batch.
* **Il verbo fuori perimetro risponde `E_PREV_NOT_FOUND`** (prima `E_PREV_STATO_CORRENTE_NON_TROVATO`, che
  resta della revisione).
* **Righe all'emissione**: ora la regola vale su ogni strada, non solo dal verbo.
* **`cambia_stato_preventivi` non si spegne in questo giro.** Su dbdev è concessa a 4 profili e a 1 override:
  mettere `attivo = false` dal CSV fermerebbe il migrate sul guard delle figlie (vedi la memoria del ritiro di
  `approva_rimessa`). Si spegne quando il backend non la chiede più, togliendo prima a mano le concessioni.
  ⚠️ Chi oggi ha `cambia_stato_preventivi` **non** ha `emetti_preventivo`: la capability non gli mostra più
  «Emetti» e l'annullo dell'emesso, e il verbo glieli rifiuta. Concedere `emetti_preventivo` ai profili è un
  dato, da decidere (Tid).
* **EMESSO → SCADUTO non lo scrive nessuno**: la guida dei preventivi parlava di un job notturno che non
  esiste (verificato il 2026-10-25, DB e backend). Debito di prodotto, fuori da questo giro.
* Letterali rimasti, fuori dal perimetro del giro: `'ANNULLATO'` in `fn_annulla_preventivo` e nel verbo della
  bolla (la guida §8 vuole `is_abortito`).

### 8.7 Richiesta al team BE (elenco chiuso)

Percorso censito: `preventivi_repository.cambia_stato`, `preventivi_service.cambia_stato` / `emetti` /
`cambia_stato_da_pratica`, `ApiPreventivoStato`, `ApiPreventivoStatoDaPratica`, `ApiPreventivoCollegaPratica`,
la factory `/emetti/` del preventivo, `DocumentoModelloRepository`, i `get_stato_id_by_codice` dei repository.

1. **La firma del verbo.** `preventivi_repository.cambia_stato` chiama
   `vendite.fn_cambia_stato_preventivo(id, stato)`: il terzo argomento (`'django_api'`) non c'è più.
   **Oggi il cambio di stato del preventivo è rotto** finché non si cambia questa riga.
2. **Il 403 dalla riga del passaggio** (BB `PassaggioDocumento`): su `ApiPreventivoStato`,
   `ApiPreventivoStatoDaPratica` e `/emetti/` del preventivo (`emetti_passaggio` al posto di
   `emetti_post_permission="cambia_stato_preventivi"`). Le copie di `cambia_stato_preventivi` si ritirano.
   `ApiPreventivoCollegaPratica` non è un cambio di stato: il suo permesso lo decide il team BE (livello sul
   documento, o un'azione sua), ma non `cambia_stato_preventivi`, che si spegne.
3. **I lettori nuovi.** `DocumentoModelloRepository.azione_del_passaggio` legge
   `script.fn_doc_azione_passaggio` (o `script.fn_doc_stato_id` + `script.fn_doc_passaggio`) e non compone più
   SQL sulla mappa. I `get_stato_id_by_codice` di ordini, offerte, DDT e contratti sono la stessa traduzione:
   `script.fn_doc_stato_id` è la sede.
4. **L'emissione dal vocabolario (M-2).** `ddt_service.STATO_EMESSO` e il letterale `'EMESSO'` di
   `preventivi_service.cambia_stato` si ritirano: il cambio di stato generico rifiuta lo stato con
   `emissione = true` (colonna `emissione` di `fn_doc_azione_passaggio`, o `script.fn_stato_emissione_id`), per
   ogni documento della factory; `/emetti/` lo prende dallo stesso lettore.
5. **Controesempio.** `cambia_stato` verso ACCETTATO da ACCETTATO (aggiornare la modalità di fatturazione)
   chiama il verbo con lo stesso stato: la matrice non ha la riga 4→4 e la risposta è
   `E_PREV_TRANSIZIONE_NON_AMMESSA`. Il ramo «no-op» deve aggiornare i due campi senza chiamare il verbo.
6. **Da sapere, nessuna modifica attesa:** il verbo fuori perimetro risponde `E_PREV_NOT_FOUND`; un passaggio
   di processo chiesto (ACCETTATO → EVASO, EMESSO → SCADUTO) risponde `E_DOC_PASSAGGIO_DI_PROCESSO`; la
   capability nasconde «Emetti» e l'annullo dell'emesso a chi non ha `emetti_preventivo`. Nessun codice nuovo:
   la policy non si rigenera per questo giro.
7. **Test Django** che scrivono lo stato del preventivo con un `UPDATE` o chiamano il verbo a tre argomenti: si
   portano al verbo (o a `dbops.fn_pgtap_porta_a_stato`). Censimento del 2026-10-25: nessuna chiamata diretta
   nei test, solo il repository (punto 1).

### 8.8 Applicato e verde (2026-10-25)

Tid: `-49` … `-52` applicati, corsa pgTAP verde. Il giro DB 6 è chiuso; restano a DB solo lo spegnimento di
`cambia_stato_preventivi` dopo il giro BE e il dato dei profili (§8.6).

### 8.9 Anticipati: le concessioni passano a `emetti_preventivo`, `cambia_stato_preventivi` si spegne (2026-10-25)

Tid: i due passi del §8.6 si fanno subito, prima del giro BE.

✅ 2026-10-25: script eseguito su dbdev (4 + 1 righe), migrate applicato da Tid: `cambia_stato_preventivi` spenta.

* **Le concessioni** (dato di dbdev, nessun CSV le semina): le righe di `config.profili_accesso_azioni` (4: profili
  1, 3, 9221 negati, 9222 concesso) e di `config.user_override_azioni` (1, utente 6, concesso) passano da
  `cambia_stato_preventivi` a `emetti_preventivo`, **con lo stesso `abilitata`**: chi poteva emettere può
  ancora, chi era negato resta negato, e l'azione vecchia resta senza figlie. Script nel brief, sotto; provato
  in transazione su dbdev il 2026-10-25 (4 + 1 righe, zero residue, lo spegnimento passa il guard).
* **`cambia_stato_preventivi` spenta** nel CSV di `config.azioni_processo` (`attivo = false`, descrizione
  «ritirata»). ⚠️ **Ordine: prima lo script, poi il migrate**: con una figlia ancora attaccata il mirror di
  febbraio (`20260228-18`) si ferma sul guard delle figlie. Su un database da zero non ci sono figlie.
* ⚠️ **Il backend**: finché `post_permission = "cambia_stato_preventivi"` resta nelle tre view e nella factory,
  quegli endpoint rispondono 403 a tutti (l'azione è spenta). Era già rotto dalla firma del verbo (§8.7 punto
  1): il punto 2 della richiesta lo ripara.

```sql
UPDATE config.profili_accesso_azioni x
   SET azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'emetti_preventivo')
 WHERE x.azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'cambia_stato_preventivi');
UPDATE config.user_override_azioni x
   SET azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'emetti_preventivo')
 WHERE x.azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'cambia_stato_preventivi');
```


### 8.10 Fatto dal team BE (2026-10-25) e richiesta al team DB

**Fatto** (`dev/backend-tid`, da committare), sulla richiesta del §8.7:

1. **La firma del verbo.** `PreventiviRepository.cambia_stato(id, stato)` chiama
   `vendite.fn_cambia_stato_preventivo` a due argomenti; tolto il `'django_api'` dai tre chiamanti.
2. **Il 403 dalla riga.** `post_passaggio = PassaggioDocumento(...)` su `ApiPreventivoStato`,
   `ApiPreventivoStatoDaPratica` e `/emetti/` del preventivo (`emetti_passaggio`), con
   `model_permission = ("vendite", "preventivo")` per le righe senza azione. Il BB prende due campi
   nuovi: `campo_stato` (il preventivo porta lo stato in `nuovo_stato`, non in `stato_codice`) e
   `risolvi_documento` (la rotta dalla pratica porta il `pratica_id`: il preventivo ROOT lo ricava
   la stessa lettura del service). `ApiPreventivoCollegaPratica` chiede il **livello sul preventivo**:
   non è un passaggio, è una modifica del documento (scelta del team BE, come chiedeva il punto 2).
   Le tre copie di `cambia_stato_preventivi` ritirate; con loro `emetti_post_permission` della factory
   documenti, che non aveva più consumatori (e il controllo di esclusività che gli stava accanto).
3. **I lettori nuovi.** `DocumentoModelloRepository.azione_del_passaggio` legge
   `script.fn_doc_azione_passaggio`: nessun SQL composto sulla mappa. Una testata fuori mappa ora è
   `E_SCRIPT_CHIAMATA_NON_VALIDA` dal DB (prima un `RuntimeError` del backend: sempre un 500). I
   quattro `get_stato_id_by_codice` (ordini, offerte, DDT, contratti) delegano a
   `DocumentoModelloRepository.stato_id` → `script.fn_doc_stato_id`: ora leggono solo gli stati
   **attivi** anche offerte e contratti (U-3; prima no). La testata di ogni documento sta nel suo
   repository (`TESTATA_<DOC>`), una sede sola per service, view e catena dei permessi.
4. **L'emissione dal vocabolario, sul cambio stato generico.** BB nuovo
   `core/services/documento_modello.rifiuta_stato_di_emissione` (regola del 2): rifiuta lo stato con
   `emissione = true` (`fn_doc_stato_id = fn_stato_emissione_id`), 400 del dominio col campo del corpo.
   Montato su bolla, preventivo, contratto **e ordine**. Ritirati i letterali `EMESSO` (bolla,
   preventivo) e `ATTIVO` (contratto). ⚠️ Per l'**ordine** è un cambio di comportamento: il cambio
   stato generico accettava CONFERMATO (opzione (i) del 2026-06-05, revocata da M-2); il frontend non lo
   usava (passa da «Emetti»). Resta com'è `POST /ordini/<id>/conferma/` (la conferma senza PDF): è il
   «censire chi emette senza /emetti/» di M-2, da decidere nel giro dell'ordine. L'offerta non ha un
   cambio stato generico.
5. **Controesempio.** ACCETTATO → ACCETTATO aggiorna la modalità di fatturazione e non chiama il
   verbo; la risposta ha `stato_precedente = stato_nuovo = ACCETTATO`.
7. **Test.** Nessuna chiamata diretta al verbo nei test (come censito). Emerso: le classi di test dei
   quattro service chiedevano al DB lo stato di emissione; mixin nuovo `ModelloDocumentoMockatoMixin`
   (mock sul repository del BB, default «non è l'emissione»). Due classi sovrascrivevano `setUp` senza
   `super()` (ordini, preventivi): il mock non si applicava, e `TestPreventiviService`
   (`unittest.TestCase`) avrebbe interrogato il DB di sviluppo. Test nuovi: il rifiuto sull'ordine,
   l'ACCETTATO che non chiama il verbo, i due campi del BB, le rotte del preventivo nel presidio
   `test_passaggio_rotte`, le dichiarazioni delle view; sul DB reale
   `test_permesso_passaggio_db` (preventivo, stato di emissione, `stato_id`, testata fuori mappa) e il
   nuovo `test_preventivo_cambia_stato_db` (verbo a due argomenti, accettazione, ACCETTATO →
   ACCETTATO, il 400 dell'emissione), con le sonde sulle firme finali.
8. **Revisione critica dello stesso giro.** `_parse_cambio_stato_payload` leggeva `nuovo_stato` con
   `str(payload.get(...))`: `null` diventava `"None"`, e senza lo strip il rifiuto dell'emissione
   guardava un codice diverso da quello del permesso (`PassaggioDocumento` ripulisce). Ora
   `PayloadValidator.require_string` (400 col campo), con due test. `TESTATA_DDT` si importa dal
   repository anche in `views_ddt` e `ddt_documenti_views` (non più via `ddt_service`); il test della
   testata fuori mappa legge il codice dal campo strutturato (`structured_db_error_code`), non dal testo.

Doc: catalogo BB backend (`PassaggioDocumento`, voce nuova `rifiuta_stato_di_emissione`, factory),
`api.md`, `api_preventivi`, `api_preventivi_collega_pratica`, `api_documenti_per_sorgente`, e una
nota nella guida del modello (riga del preventivo: «il backend chiede ancora `cambia_stato_preventivi`»
non era più vero). ⚠️ Non toccato, è del team DB: `docs/it/dbzero/config/manual/azioni_processo.md`
elenca ancora `cambia_stato_preventivi` come attiva e non ha `emetti_preventivo`.

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6940 test: due rossi, entrambi ricadute del
giro DB 6 e non del codice di questo giro, corretti e rilanciati verdi: l'etichetta it/en della colonna
nuova `emissione` dei vocabolari (`config_panel.campi.emissione`, presidio
`test_config_panel_registro_db`, lo stesso caso di `iniziale` al primo giro) e la fixture di
`test_ricerca_liste_db`, che emetteva un preventivo senza righe (il controesempio del §8.5): ora passa da
`dbops.fn_pgtap_crea_preventivo_con_righe`. I due presidi della policy sono verdi (nessun codice nuovo).
mypy (cricchetto, 0 rilievi) e ruff puliti. ⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Non fatto, e perché: il codice dello stato di emissione per «Emetti».** Il §8.7 punto 4 chiede che
`/emetti/` prenda lo stato dal lettore e che `ddt_service.STATO_EMESSO` si ritiri. Il verbo di bolla e
preventivo prende il **codice** dello stato; il DB dà l'**id** (`fn_stato_emissione_id`) e nessun lettore
traduce id → codice. Leggerlo dal vocabolario nel backend vorrebbe dire comporre di nuovo SQL sulla mappa
(quello che il punto 3 ha appena tolto). Restano quindi, dichiarati con questo rimando: `STATO_EMESSO` in
`ddt_service` e in `preventivi_service` (una sede per documento, usata da `emetti` e dalla factory), e
`emetti_passaggio=(testata, stato)`.

**Richiesta al team DB (per il giro dopo):** un lettore del **codice** dello stato, gemello di
`script.fn_doc_stato_id`, per esempio `script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint)
RETURNS text` (oppure direttamente il codice dello stato di emissione di una testata: lo sceglie il team
DB). Con quello il backend legge una volta `fn_doc_stato_codice(t, fn_stato_emissione_id(t))`: si
ritirano i due `STATO_EMESSO`, `emetti_passaggio` riceve la sola testata, e il presidio dell'emissione
diventa generico sui documenti della factory. Ricaduta BE: il repository del modello e le due view
documentali.

**Residui per i giri dei documenti** (non toccati, per memoria): `contratti_service.emetti` e
`ordini_service.conferma` cercano lo stato di emissione per codice scritto (`"ATTIVO"`,
`_STATO_CONFERMATO`) ma scrivono l'id: lì basterebbe già `fn_stato_emissione_id`; `offerte_service.emetti`
usa `StatoOfferta.EMESSA`. Si allineano col giro del loro documento. ➡️ Superato da V-2 (§8.11): si
chiudono nello stesso passaggio BE.

### 8.11 Chiusura della richiesta del §8.10: il codice dello stato di emissione (2026-10-25)

Analisi del team DB sul percorso intero (lettori DB, repository del modello, factory documentale,
service), poi le decisioni di Tid. Lo scopo: dare al backend in un giro solo tutto quello che serve a
chiudere 4-bis-octies, senza residui per i giri dei documenti.

**Il punto che la richiesta non diceva.** «Emetti» fissa lo stato chiesto quando la view si definisce
(`emetti_passaggio=(TESTATA, STATO_EMESSO)` nelle due view documentali → `PassaggioDocumento(stato_chiesto=…)`),
cioè all'import, dove il DB non si interroga. Sostituire la costante col lettore sposterebbe il
letterale, non lo ritirerebbe: il permesso di «Emetti» deve chiedere lo stato di emissione **a ogni
richiesta**. Da qui `emetti_passaggio` con la sola testata.

**Fatti letti dalla struttura (2026-10-25).** I cinque vocabolari con la colonna `emissione` la
dichiarano tutti nei CSV di `80_data` (ordine `CONFERMATO`, preventivo `EMESSO`, bolla `EMESSO`,
offerta `EMESSA`, contratto `ATTIVO`); il CHECK `chk_stati_doc_<doc>_emissione_attivo` garantisce che lo
stato di emissione sia attivo. Reso, commessa e fattura non si emettono: `fn_stato_emissione_id` dà NULL.
I verbi di bolla e preventivo prendono il `codice_interno` e lo traducono con `fn_doc_stato_id`.

**Decisioni di Tid (2026-10-25).**

| # | Domanda | Decisione |
| --- | --- | --- |
| V-1 | Un lettore generico id → codice, o uno apposta per il codice dell'emissione | ✅ **Generico**: `script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint) RETURNS text`, gemello inverso di `fn_doc_stato_id`. Uno stato ha due chiavi (id e `codice_interno`): la traduzione nei due sensi sta nella stessa coppia; un lettore dell'emissione sarebbe una terza lettura della stessa cosa. Il backend compone `fn_doc_stato_codice(t, fn_stato_emissione_id(t))` |
| V-2 | Contratto, ordine e offerta nello stesso passaggio BE, o al giro del loro documento | ✅ **Stesso passaggio**: poggiano su pezzi comuni già fatti (scelta C del fermo). Per l'ordine si ritira solo il letterale: chi conferma senza `/emetti/` (M-2) resta al giro dell'ordine |
| V-3 | Archiviare subito `brief-db-documento-nasce-nello-stato-iniziale` | ✅ **Sì**: N-1 … N-3 decise qui (§4-bis) e costruite nel primo giro (§4-quinquies). Archiviato in `work-done/` il 2026-10-25, D32 chiuso nel registro |

**Il contratto del lettore (V-1).**

* Il codice che rende è il `codice_interno`, la chiave stabile, quella che leggono i verbi.
* Testata fuori mappa (`script.fn_doc_stato_modello`): `E_SCRIPT_CHIAMATA_NON_VALIDA`, come i gemelli.
* Id NULL o che il vocabolario non ha: NULL, decide il chiamante. Per «Emetti» un NULL vuol dire
  documento che non si emette: la factory monta `emetti_passaggio` solo dove l'emissione esiste.
* Nessun filtro sugli attivi: un id è già una riga esistente, e uno stato spento come destinazione lo
  rifiuta il verbo con `fn_doc_stato_id` (U-3). Per l'emissione il caso non si pone (il CHECK).
* `STABLE`, `SECURITY INVOKER` esplicito; parametri `bigint` e non `%TYPE` (vocabolario polimorfo, come i gemelli).

**Elenco chiuso, giro DB (dopo il via di Tid).**

| # | Che cosa |
| --- | --- |
| K-1 | ChangeSet in `20_code/script`: `script.fn_doc_stato_codice` (numero al prossimo progressivo del giorno, riletto prima di salvare) |
| K-2 | COMMENT di `script.fn_stato_emissione_id` e `script.fn_doc_stato_id`: il gemello e i consumatori nuovi («Emetti» del backend) |
| K-3 | pgTAP: per le cinque testate con l'emissione, il codice reso è quello che il vocabolario dichiara (letto dalla colonna, non scritto nel test); testata senza emissione → NULL; id inesistente → NULL; testata fuori mappa → `E_SCRIPT_CHIAMATA_NON_VALIDA`; andata e ritorno con `fn_doc_stato_id` |
| K-4 | `docs/it/dbzero/script/manual/fn_doc_stato_codice.md`; la coppia di lettori nella guida del modello |
| K-5 | `docs/it/dbzero/config/manual/azioni_processo.md`: `cambia_stato_preventivi` non più attiva, `emetti_preventivo` presente (§8.9) |
| K-6 | Questo brief: l'esito del giro e il passaggio al BE |

**Elenco chiuso, passaggio BE (dopo l'apply del giro DB).**

| # | Che cosa |
| --- | --- |
| B-1 | `DocumentoModelloRepository`: il codice dello stato di emissione di una testata (una lettura, i due lettori composti); NULL → il documento non si emette |
| B-2 | Il permesso di «Emetti» chiede lo stato a ogni richiesta: `emetti_passaggio` riceve la sola testata, `PassaggioDocumento` risolve lo stato chiesto dal lettore |
| B-3 | Ritirati `STATO_EMESSO` in `ddt_service` e `preventivi_service`: «Emetti» passa al verbo il codice letto |
| B-4 | V-2: `contratti_service.emetti` e `ordini_service.conferma` su `fn_stato_emissione_id` (scrivono l'id); `offerte_service.emetti` sul codice letto al posto di `StatoOfferta.EMESSA`; ritirati `"ATTIVO"` e `_STATO_CONFERMATO` |
| B-5 | Il presidio dell'emissione generico sui documenti della factory; test sul DB reale del lettore composto (le cinque testate, una senza emissione) |
| B-6 | Guida del modello, §«L'emissione», riga «Quale stato è l'emissione»: «Emetti» ne legge il codice con `script.fn_doc_stato_codice` (si scrive quando è vero, cioè con B-3) |

**Scritto e provato (team DB, 2026-10-25, dopo il via di Tid).**

| # | Fatto |
| --- | --- |
| K-1 | `20_code/script/20261025-70-create-fn-doc-stato-codice`: `script.fn_doc_stato_codice(regclass, bigint) RETURNS text`, `STABLE`, `SECURITY INVOKER`, il contratto qui sopra. Il `-69` era gia' preso dal lotto della grammatica |
| K-2 | `20_code/script/20261025-71-update-fn-doc-stato-id-emissione-commento-gemello`: i due COMMENT (il gemello inverso; «Emetti» fra i consumatori). Corpi invariati |
| K-3 | `db/pgtap/script/test-doc-stato-codice-v1.sql` (plan 8): forma; emissione composta sulle cinque testate contro la colonna `emissione` dei vocabolari; NULL su reso, commessa, fattura; andata e ritorno con `fn_doc_stato_id` su ogni stato attivo delle otto testate (contando gli stati provati, niente verde per sottrazione); id assente e NULL; stato spento che rende il suo codice; fuori mappa |
| K-4 | `docs/it/dbzero/script/manual/fn_doc_stato_codice.md`; il lettore nell'area tecnica della guida del modello. La riga «Emetti» della guida e' B-6: oggi non e' ancora vera |
| K-5 | `docs/it/dbzero/config/manual/azioni_processo.md`: `cambia_stato_preventivi` ritirata, `emetti_preventivo` con la sua forma (l'azione sulla riga del passaggio, come `emetti_ddt`) |
| K-6 | Questo paragrafo e il blocco «Chi riparte» |

**Provato** su dbdev, come owner, in transazione annullata (`BEGIN` e `ROLLBACK` del file, `psql -v ON_ERROR_STOP=1`): l'SQL estratto dai due YAML davanti al pgTAP nuovo, 8 eseguiti su 8 pianificati, tutti `ok`; lo stesso SQL davanti a `dbops/test-riferimenti-morti-v1` (plpgsql_check su ogni funzione), 9/9 (`ok 8` e' lo `skip` dichiarato del file). La corsa come app e lo scratch restano a Tid, dopo l'apply.

✅ **Applicato e verde** (Tid, 2026-10-25): `-70` e `-71` EXECUTED su dbdev alle 15:27 (`databasechangelog`), corsa pgTAP verde.

### 8.12 Cosa resta al cantiere, lato DB (censimento del 2026-10-25)

Letto dalla guida del modello (§10, la tabella per documento), dai debiti dichiarati dei giri (§7.7, §8.6, §4-septies)
e dai corpi vivi (doc auto-generata). Elenco chiuso: ogni cosa che manca è una riga qui, o non manca.

**I documenti ancora da portare al modello** (un documento per giro, tutto intero: §5). Fra parentesi quello che
la guida §10 segna ❌.

| # | Documento | Che cosa manca | Note |
| --- | --- | --- | --- |
| D-1 | Ordine (+ ordine d'acquisto, §5) | verbo di stato, azione sul passaggio, annullo dal verbo (`fn_annulla_ordine` scrive da sé) | matrice in tabella e colonna `emissione` già ci sono; da decidere qui `POST /ordini/<id>/conferma/` (M-2: chi conferma senza «Emetti»); l'ordine d'acquisto oggi non ha guard di transizione |
| D-2 | Commessa | l'azione `cambia_stato_commessa` sulla riga del passaggio e controllata dal verbo (oggi solo dal backend) | il più piccolo: verbo, matrice e annullo ci sono; matrice in `vendite`, non in `config` |
| D-3 | Contratto | matrice in tabella (oggi scritta nel guard), verbo, azione, annullo dal verbo | il backend scrive lo stato con `UPDATE` |
| D-4 | Offerta | verbo, azione, annullo con l'avviso dei legami invece di `fn_check_offerta_annullabile` (⚠️ corretto nel §13.1: il check resta, è la metà «prima ciò che vieta»; manca l'avviso); il nome della matrice fuori serie (`stati_doc_offerte_transizioni`) | gli stati di partenza ripetuti in Python |
| D-5 | Fattura | verbo al posto delle funzioni della pipeline e dell'`UPDATE` dello stato del lotto; azioni della pipeline sulla riga | il più lungo: tocca la pipeline di fatturazione |
| D-6 | Versione di listino | vocabolario degli stati (oggi testo con `CHECK`), matrice in tabella (oggi nel guard e in Python), verbo | parte da zero |
| D-7 | DDT d'acquisto | tutto | ⏸️ T-2 di Tid: aspetta il satellite per ambito (D-3 di analisi-simmetria-ordini-acquisto) |

**I debiti DB dichiarati e ancora aperti.**

| # | Debito | Dove è scritto |
| --- | --- | --- |
| X-1 | Letterali `'ANNULLATO'` in `vendite.fn_annulla_preventivo` (chiama il verbo con il codice) e in `vendite.fn_cambia_stato_ddt` (riconosce l'annullo dell'emesso confrontando il codice): la guida §8 vuole lo stato abortito letto dal vocabolario (`is_abortito`) | §8.6 |
| X-2 | EMESSO → SCADUTO del preventivo non lo scrive nessuno: la guida dei preventivi parlava di un job notturno che non esiste | §8.6 (debito di prodotto) |
| X-3 | R-7, R-8: due casi dei builder delle fixture | §4-septies, «non ora» per decisione di Tid: restano chiusi così |

Fuori da questo brief: pagamenti e magazzino (§3.1, «stessa domanda»); il tema è di tutte le famiglie e non si
apre senza l'ok di Tid (AGENTS.md).

**Decisioni per Tid.**

| # | Domanda | Consiglio del team DB |
| --- | --- | --- |
| W-1 | Il documento del giro dopo, e l'ordine dei successivi — ✅ **Tid 2026-10-25: l'ordine, senza acquisti; poi contratto, offerta, commessa, fattura, listino** | **D-1, l'ordine** (col gemello d'acquisto): è il più vicino al modello dopo bolla e preventivo, ha già matrice ed emissione, e chiude la domanda aperta di M-2 su `/conferma/`. Poi D-2 (piccolo), D-3, D-4, D-5, D-6. D-7 resta fermo su T-2 |
| W-2 | X-1: un giro a sé subito, o dentro il giro del prossimo documento | **Dentro il giro dell'ordine**: il lettore dello stato abortito serve anche lì (`fn_annulla_ordine`), e nasce una volta sola per i tre (regola del 2) |
| W-3 | X-2: lo scrive un job del DB, o si toglie SCADUTO dal modello del preventivo | Decisione di prodotto: se resta, è un processo con la sua riga di matrice di processo (`manuale = false`, già così) e un job; lo si scrive in un brief suo, non in questo |

## 9. Giro 7: l'ordine al modello — ricognizione e piano (2026-10-25)

✅ **Deciso da Tid il 2026-10-25 (W-1):** il documento del giro è l'**ordine di vendita**. L'ordine d'acquisto
**non** entra: come per il DDT (T-2), gli acquisti arrivano al modello tutti insieme, quando parte quel
cantiere (eccezione dichiarata alla regola del §5, «nello stesso giro»; i pezzi comuni restano generici).
Ordine dei giri dopo: contratto, offerta, commessa, fattura, versione di listino.

### 9.1 Com'è oggi (doc auto-generata e `backend/`, 2026-10-25)

* **Vocabolario e matrice.** `config.stati_doc_ordini`: DRAFT (iniziale), CONFERMATO (emissione), ALLOCATO,
  SPEDITO, CONSEGNATO, PARZIALMENTE_EVASO, EVASO, FATTURATO, ANNULLATO (`is_abortito`). Matrice
  `config.transizioni_stati_ordini`, nove righe: tre **manuali** (DRAFT → CONFERMATO «conferma», DRAFT →
  ANNULLATO e CONFERMATO → ANNULLATO «annulla») e sei **di processo** (`manuale: false`, fra CONFERMATO,
  PARZIALMENTE_EVASO ed EVASO). La matrice **non ha** la colonna `azione_processo_codename`. ALLOCATO,
  SPEDITO, CONSEGNATO e FATTURATO non hanno righe: nessun passaggio li raggiunge (si dichiara, non si tocca).
* **Guard di transizione** `trgfn_ordini_guard_transizione`: matrice, righe attive su DRAFT → CONFERMATO,
  `fn_check_ordine_confermabile`, `fn_check_ordine_annullabile`, prezzi autorizzati. Letterali `'DRAFT'`,
  `'CONFERMATO'`, `'ANNULLATO'`: condizioni di un passaggio, restano (come sul preventivo, §8.1).
* **Verbo di stato: non c'è.** Lo scrivono:
  * il **backend** con un `UPDATE` (`OrdiniRepository.update_stato`), da `ordini_service.conferma` (usata da
    «Emetti» **e** da `POST /ordini/<id>/conferma/`) e dal cambio stato generico. Sul generico, dopo il §8.10, non
    resta nessun passaggio manuale da scrivere con l'`UPDATE`: la conferma è rifiutata (emissione), l'annullo
    passa già da `fn_annulla_ordine`;
  * `vendite.fn_annulla_ordine` (DEFINER, ritira i legami) con un `UPDATE` suo e il letterale `'ANNULLATO'`;
  * `vendite.fn_ordine_proietta_stato_evasione` (**INVOKER**), i sei passaggi di processo, con un `UPDATE`.
    La chiamano `fn_genera_ddt_da_ordine`, i cinque verbi del reso, `fn_ddt_riga_correggi_qta_evasa` e il trigger
    `trgfn_dlt_block_ordrig_ddtrig`.
* **Azione: nessuna.** Nessuna azione dell'ordine a catalogo (`config.azioni_processo`).
* **«Emetti» e `/conferma/`.** `/emetti/` della factory chiama `ordini_service.conferma` e genera il PDF; dentro
  la stessa transazione completa lo step `CONFERMA_ORDINE` della pratica. `POST /ordini/<id>/conferma/` fa la sola
  transizione, senza PDF: il frontend la espone (`ordiniApi.confermaOrdine`, azione `conferma` dello store) ma
  **nessun componente la chiama** (letto il 2026-10-25). È il «chi conferma senza Emetti» di M-2.
* **Numero alla nascita.** `trgfn_ordini_gen_numero` numera l'ordine all'INSERT, scelta dichiarata nel corpo
  («l'ordine nasce numerato… i buchi da bozza scartata restano»). La guida §7 dice «il numero lo assegna il
  database al passaggio allo stato emesso»: è una divergenza (Z-4).
* **Capability** `fn_available_actions_ordine`: matrice e motivi; nessun filtro sull'azione.
* **pgTAP:** 19 file scrivono lo stato dell'ordine con un `UPDATE` diretto; 10 lo portano in EVASO o
  PARZIALMENTE_EVASO, che sono passaggi di processo: con la porta si costruiscono evadendo davvero
  (`dbops.fn_pgtap_crea_ddt_da_ordine`, già a catalogo). Conteggio del 2026-10-25, per dimensionare il porting.

### 9.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| matrice | colonna `azione_processo_codename` su `config.transizioni_stati_ordini` (FK alla chiave stabile, come preventivo e bolla), valori dal CSV: l'azione su DRAFT → CONFERMATO e CONFERMATO → ANNULLATO (Z-1); mirror con la colonna (⚠️ `nullValue`) |
| azione | `emetti_ordine` a catalogo (Z-1) |
| verbo | NUOVO `vendite.fn_cambia_stato_ordine(p_ordine_id, p_stato)`, gemello di quello del preventivo: DEFINER col predicato del perimetro (`fn_scope_ef_whitelist_via_ordine`), `fn_doc_stato_id`, `fn_guard_passaggio`, `fn_doc_scrivi_stato` |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.ordini` |
| annullo | `fn_annulla_ordine` chiama il verbo (lo stato d'annullo dal vocabolario se Z-3 = sì) |
| processo | `fn_ordine_proietta_stato_evasione` scrive con `fn_doc_scrivi_stato` (sola seconda metà) e diventa DEFINER, come la proiezione del preventivo (`-45`) |
| capability | `fn_available_actions_ordine`: il passaggio con l'azione si nasconde a chi non ce l'ha (stessa forma di bolla e preventivo) |
| fixture | `fn_pgtap_porta_a_stato` conosce il verbo dell'ordine; i 19 `UPDATE` diretti portati: al verbo dove provano il guard, a `crea_ddt_da_ordine` dove serve un EVASO o un PARZIALMENTE_EVASO |
| guida | §10, riga dell'ordine; la guida degli ordini rimanda al modello |

**Richiesta al BE** (si scrive col percorso intero, a giro DB provato): `OrdiniRepository.update_stato` si ritira
e `conferma` chiama il verbo (lo step della pratica resta nella stessa transazione); il 403 dalla riga del passaggio
(`PassaggioDocumento`) su «Emetti» e sull'annullo; il cambio stato generico senza `UPDATE`; `/conferma/` secondo Z-2;
`_STATO_CONFERMATO` già nel passaggio B-4 del §8.11.

### 9.3 Domande per Tid

✅ **Decise da Tid il 2026-10-25: Z-1, Z-2, Z-3, Z-4 come da proposta; W-3 in un brief separato
([brief-db-scadenza-preventivi](brief-db-scadenza-preventivi.md)); via allo sviluppo.**

* **Z-1. L'azione dell'ordine.** Proposta: azione **nuova** `emetti_ordine` («emette un ordine o annulla un ordine
  confermato») sulle righe DRAFT → CONFERMATO e CONFERMATO → ANNULLATO; DRAFT → ANNULLATO senza azione. È la guida §6
  («un'azione per documento, sui passaggi pesanti») e il gemello di `emetti_ddt` ed `emetti_preventivo`. ⚠️ Nessun
  profilo la riceve dai seed: dopo il giro chi non ce l'ha non vede «Emetti» né l'annullo del confermato. Concederla
  ai profili è un dato (su dbdev lo fa Tid, come per `emetti_preventivo`).
* **Z-2. `POST /ordini/<id>/conferma/`.** Proposta: **si ritira** (rotta, view, API e azione dello store del
  frontend, che nessun componente chiama). È l'ultimo «conferma senza Emetti» (M-2): l'ordine si conferma solo da
  «Emetti», con numero e PDF insieme. Alternativa: resta, e chiede la stessa azione di «Emetti».
* **Z-3 (era W-2). Lo stato d'annullo dal vocabolario.** Proposta: **sì, in questo giro**: lettore
  `script.fn_stato_abortito_id(p_testata)` (gemello di `fn_stato_iniziale_id` e `fn_stato_emissione_id`) e indice unico
  parziale su `is_abortito` nei vocabolari (oggi ognuno ne ha uno solo: fatto letto dai CSV, la regola è sul
  modello, «un documento ha un solo stato d'annullo»). Lo leggono `fn_annulla_ordine`, `fn_annulla_preventivo` e il
  verbo della bolla, che oggi scrivono `'ANNULLATO'` (X-1 chiuso). Alternativa: X-1 resta debito, l'ordine nasce col
  letterale come il preventivo.
* **Z-4. Il numero alla nascita.** L'ordine si numera all'INSERT, la guida §7 lo vuole all'emissione. Proposta:
  **fuori da questo giro**, dichiarato come divergenza nella riga dell'ordine della guida §10: spostarlo cambia la
  numerazione (e i buchi da bozza scartata), è un tema suo da decidere con la storia della scelta
  (`trgfn_ordini_gen_numero`, rev 2026-08-31). Alternativa: si porta in questo giro.

### 9.4 Scritto (2026-10-25)

| # | Cosa |
| --- | --- |
| `-72` | un solo stato d'annullo per vocabolario, ed è attivo: indice unico parziale `uq_<voc>_abortito` e CHECK `chk_<voc>_abortito_attivo` sugli otto vocabolari (Z-3) |
| `-73` | colonna `azione_processo_codename` su `config.transizioni_stati_ordini` (FK alla chiave stabile) |
| CSV | `azioni_processo`: `emetti_ordine` (id 41); matrice dell'ordine: `emetti_ordine` su DRAFT → CONFERMATO e CONFERMATO → ANNULLATO; mirror `20260605-11` con la colonna e `nullValue: "NULL"` |
| `-74` | NUOVO `script.fn_stato_abortito_id(testata)`: lo stato d'annullo dal vocabolario, gemello di `fn_stato_emissione_id` |
| `-75` | NUOVO `vendite.fn_cambia_stato_ordine(id, stato)`: il verbo dell'ordine sul verbo comune, DEFINER col predicato del perimetro; EXECUTE solo all'app |
| `-76` | `fn_annulla_ordine` chiama il verbo, con lo stato d'annullo dal vocabolario |
| `-77` | `fn_annulla_preventivo`: lo stato d'annullo dal vocabolario (X-1) |
| `-78` | `fn_cambia_stato_ddt`: l'annullo dell'emessa riconosciuto dallo stato d'annullo del vocabolario (X-1) |
| `-79` | `fn_ordine_proietta_stato_evasione` scrive con `fn_doc_scrivi_stato`, DEFINER (attesa cambiata dichiarata nel file: la proiezione vale per ogni ordine) |
| `-80` | la porta montata su `vendite.ordini` |
| `-81` | capability dell'ordine: il passaggio con l'azione si nasconde a chi non ce l'ha; motivi legati a `is_abortito` ed `emissione` |
| `-82` | `fn_pgtap_porta_a_stato`: l'ordine dal suo verbo |

Firme, `RETURNS TABLE` e `DECLARE` ancorati con `%TYPE`, anche nelle firme di GRANT e COMMENT (Tid, 2026-10-25);
`fn_cambia_stato_ddt` torna alle ancore di `20261001-20`. Prova in transazione: una sola funzione per nome dopo il
`CREATE OR REPLACE` (nessun sovraccarico nato dall'ancora).

Doc: pagine `manual` di `fn_stato_abortito_id` e `fn_cambia_stato_ordine`; la guida del modello (riferimenti, §8,
§10 riga dell'ordine con la divergenza del numero, Z-4); `gestione-ordini` §4.2 e §4.4; `azioni_processo.md`.
pgTAP nuovo: `vendite/test-ordine-al-modello-v1` (16; il 16 è rosso da owner, verde come app).

**Applicato da Tid** su dbdev alle 15:59, a metà della regressione (§9.5).

### 9.5 Regressione e porting dei pgTAP (2026-10-25)

La prima regressione prima/dopo (736 file che toccano documenti, stati, capability e presidi) non vale: l'apply di
Tid è caduto a metà corsa, e quattro corse in parallelo con la DDL dell'SQL estratto si sono bloccate a vicenda
(deadlock). Rifatta **in sequenza sul db migrato**, come owner: 70 file con almeno un rosso; letti uno per uno.

* **Del giro, 11 file**, tutti per la stessa causa: scrivevano lo stato dell'ordine con un `UPDATE` diretto (ora la
  porta), o cercavano «Conferma» con un utente senza `emetti_ordine`. Portati (tre agenti in parallelo, file
  diversi): al verbo dove provano il guard (con `emetti_ordine` concessa), a `porta_a_stato` o ai builder dove serve
  una fixture, all'**evasione vera** (`dbops.fn_pgtap_crea_ddt_da_ordine`) dove serviva un EVASO scritto a mano. Più
  il presidio `script/test-doc-verbo-comune-e-porta-v1`: la porta su quattro testate (anche l'ordine), e il
  «documento non ancora portato» del test 8 è ora la fattura, che arriva per ultima.
* **Non del giro, 59 file**: 57 con gli stessi rossi della corsa prima dell'apply (rossi da owner dichiarati e
  rossi preesistenti), 2 test di perimetro (`ddt-reason-catch-all` 18, `get-stato-push-segment` 12) rossi da owner
  per costruzione (l'owner salta la RLS), la cui corsa «prima» era morta nel deadlock.

**Dopo il porting**, rilanciati i 12 file (gli 11 e il test nuovo): tutti eseguiti contro il piano; rossi solo quelli
da owner dichiarati (`annullo-documento-con-legami` 30, `vw-situazione-merce-ordine` 11, `doc-verbo-comune-e-porta`
19 e 20, `ordine-al-modello` 16).

**Attese cambiate nel porting, da guardare (Tid):**
* `script/test-fn-check-prezzi-autorizzati-v1`: un test in più (30b, l'ordine è davvero EVASO dopo l'evasione), plan 45;
* `script/test-seed-stati-doc-ordini-evaso-v1` 5: da «la transizione CONFERMATO → EVASO è ammessa» (scritta a mano)
  a «l'evasione vera porta in EVASO»; il 7 ora dice che il rifiuto di EVASO → ANNULLATO viene dal guard;
* `vendite/test-ordini-guard-transizione-v1`: i `throws_ok` dei test 3, 5 e 7 controllavano solo `P0001` e passavano
  anche sulla porta; ora passano dal verbo e provano di nuovo il guard;
* `vendite/test-ritiro-alla-chiusura-documento-v1` 7 resta un `UPDATE`: riscrive lo stesso stato, e la porta lo lascia
  passare.

✅ **Applicato e verde** (Tid, 2026-10-25): migrazione su dbdev e corsa pgTAP verde.

⚠️ Nell'albero c'è anche `vendite/test-vw-dash-aperto-v1.sql` modificato alle 15:43, rev «§8.5»: non è di questo giro
(un'altra sessione), non l'ho toccato.

### 9.6 Richiesta al team BE (elenco chiuso)

Percorso intero letto il 2026-10-25 (`backend/apps/vendite`, `frontend/src/vendite/ordini`, test Django). Si fa in **un
passaggio**, insieme a B-1 … B-6 del §8.11 (lo stato di emissione letto dal DB): l'ordine ne usa il lettore.

| # | Che cosa | Dove |
| --- | --- | --- |
| C-1 | `OrdiniRepository.update_stato` si ritira (l'`UPDATE` ora lo ferma la porta: `E_DOC_STATO_SOLO_DAL_VERBO`); nuovo `cambia_stato(id, codice)` su `vendite.fn_cambia_stato_ordine`, gemello di `PreventiviRepository.cambia_stato` | `ordini_repository.py` |
| C-2 | `ordini_service.conferma` chiama il verbo con lo stato di emissione letto dal DB (B-1 del §8.11) e ritira `_STATO_CONFERMATO`; lo step `CONFERMA_ORDINE` della pratica resta nella stessa transazione. Il fail-fast `E_ORD_NESSUNA_RIGA` è la copia della Regola 2 del guard (`E_ORDINE_CONFERMA_SENZA_RIGHE`): si ritira (niente logica duplicata fra livelli) | `ordini_service.py` |
| C-3 | Il cambio stato generico: il ramo che non è l'annullo chiama il verbo invece di `update_stato`. Oggi la matrice non ha altri passaggi manuali (la conferma è rifiutata come emissione, l'annullo passa da `fn_annulla_ordine`): il ramo resta per i passaggi che la matrice potrà avere | `ordini_service.cambia_stato` |
| C-4 | Z-2: si ritira `POST /ordini/<id>/conferma/` (`ApiOrdineConferma`, la rotta, `ordiniApi.confermaOrdine`, l'azione `conferma` dello store e il suo mock nello spec, la doc API). L'ordine si conferma solo da «Emetti» | `views_ordini.py`, `urls_ordini.py`, `frontend/src/vendite/ordini/` |
| C-5 | Il 403 dalla riga del passaggio (`PassaggioDocumento`) su `ApiOrdineCambiaStato` (l'annullo del confermato chiede `emetti_ordine`) e su «Emetti» dell'ordine (`emetti_passaggio`, con la sola testata dopo B-2) | `views_ordini.py`, `ordini_documenti_views.py` |
| C-6 | Test: `test_ordini_service` (mock di `update_stato` → `cambia_stato`); l'helper DB `tests/db/_ddt_consegnato.py` scrive lo stato dell'ordine con un `UPDATE` (ora la porta): passa da `dbops.fn_pgtap_porta_a_stato` o da `dbops.fn_pgtap_crea_ordine_con_righe`; sonda `richiedi_db_provvisto` sulla firma del verbo nuovo; i codici della policy rigenerati se serve (nessun codice nuovo dal DB in questo giro) | `apps/vendite/tests/` |

**Da sapere.** Dopo il giro, chi non ha `emetti_ordine` non vede «Conferma» né l'annullo di un ordine confermato, e il
verbo glieli rifiuta. Concedere l'azione ai profili è un dato (su dbdev lo fa Tid, come per `emetti_preventivo`).
Fino al passaggio BE la conferma dal backend e il cambio stato generico rispondono `E_DOC_STATO_SOLO_DAL_VERBO`: è
la rottura accettata del §5, «il DB consegna e scrive al BE cosa si è rotto».

### 9.7 Fatto dal team BE (2026-10-25): B-1 … B-6 del §8.11 e C-1 … C-6 del §9.6

Un passaggio solo, `dev/backend-tid`, da committare.

**Lo stato di emissione letto dal DB (§8.11).**

| # | Fatto |
| --- | --- |
| B-1 | `DocumentoModelloRepository.stato_di_emissione(testata)` → `StatoDiEmissione(id, codice)` o None: una lettura, `fn_doc_stato_codice(t, fn_stato_emissione_id(t))`. BB service `documento_modello.stato_di_emissione(testata, *, function_name)`: None è `E_CONFIG_MANCANTE` (codice già a catalogo, `TECNICO`: è cablaggio, non dato) |
| B-2 | `PassaggioDocumento` prende il campo `emissione: bool` (esclusivo con `stato_chiesto`, `ValueError` alla definizione): lo stato chiesto lo legge a ogni richiesta, e solo quando servono documento e stato (la lettura resta pigra). `emetti_passaggio` della factory riceve la sola testata |
| B-3 | Ritirati `STATO_EMESSO` di `ddt_service` e `preventivi_service`: «Emetti» passa al verbo il codice letto |
| B-4 | `contratti_service.emetti` scrive l'id letto (via `"ATTIVO"`); `ordini_service.conferma` sul verbo col codice letto (via `_STATO_CONFERMATO`); `offerte_service.emetti` col codice letto al posto di `StatoOfferta.EMESSA` (la classe resta: le altre transizioni dell'offerta la usano come condizione) |
| B-5 | Presidio generico in `core/tests/test_passaggio_rotte.py`: ogni «Emetti» che legge il passaggio chiede lo stato al vocabolario, nessuno lo fissa; sul DB, ogni testata che lo dichiara ha lo stato di emissione. In `test_permesso_passaggio_db` il lettore composto sulle cinque testate, contro la colonna `emissione` dei vocabolari, e il reso → None |
| B-6 | Guida del modello §7, riga «Quale stato è l'emissione»: «Emetti» ne legge il codice con `fn_doc_stato_codice` |

**L'ordine al modello (§9.6).**

| # | Fatto |
| --- | --- |
| C-1 | `OrdiniRepository.update_stato` ritirato; nuovo `cambia_stato(id, codice)` su `vendite.fn_cambia_stato_ordine` |
| C-2 | `ordini_service.conferma` sul verbo con lo stato di emissione letto; lo step `CONFERMA_ORDINE` resta nella stessa transazione. Ritirato il fail-fast `E_ORD_NESSUNA_RIGA` della conferma (resta quello del push, che è un'altra regola); il rifiuto arriva dal guard, `E_ORDINE_CONFERMA_SENZA_RIGHE` |
| C-3 | Il ramo non-annullo del cambio stato generico chiama il verbo |
| C-4 | Ritirati `ApiOrdineConferma`, la rotta `/conferma/` (ora 404), `ordiniApi.confermaOrdine`, l'azione `conferma` dello store e il suo mock; doc `api_ordini` |
| C-5 | `post_passaggio` su `ApiOrdineCambiaStato` (l'annullo del confermato chiede `emetti_ordine`) e `emetti_passaggio=TESTATA_ORDINI` su «Emetti» dell'ordine |
| C-6 | `test_ordini_service` sul verbo; `_ddt_consegnato` conferma l'ordine con `fn_pgtap_porta_a_stato`; test nuovo `vendite/tests/db/test_ordine_cambia_stato_db` (sonde sulla firma del verbo e sul lettore: conferma dal verbo, senza `emetti_ordine` → `E_PERMESSO_NEGATO`, senza righe → il codice del guard, l'emissione dal generico → 400, annullo della bozza). Nessun codice nuovo: la policy non si rigenera |

**Emerso nello stesso giro.** I test unitari dell'offerta (`OfferteServiceTests`, `unittest.TestCase`) non avevano il
mixin del modello: `emetti` avrebbe chiesto lo stato al DB di sviluppo, verde per il motivo sbagliato. Ora hanno
`ModelloDocumentoMockatoMixin`, che prende `emissione_del_documento(codice)` (default: il documento non si emette).

**Doc:** catalogo BB backend (`PassaggioDocumento`, `stato_di_emissione`, factory), `api.md`, `api_ordini`,
`api_documenti_per_sorgente`, guida del modello (B-6 e la riga dell'ordine del §10).

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6960 test, verde (1 skip, 1 expected failure, come
prima). mypy (cricchetto, 0 rilievi) e ruff puliti; vitest dello store ordini ed ESLint sui file toccati puliti.
⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Residui:** ritirati nel §9.8 (il letterale dell'annullo) o sospesi su un difetto DB (il «solo da DRAFT» della
conferma). Da sapere: finché `emetti_ordine` non è concessa ai profili, nessuno conferma un ordine né annulla un
confermato (dato su dbdev, Tid).

### 9.8 I due residui del §9.7 (team BE, 2026-10-25, ok di Tid) e un difetto DB emerso

**1. Lo stato d'annullo dal vocabolario: fatto.** I service riconoscevano l'annullo confrontando lo stato chiesto
con i letterali `STATO_ANNULLATO` / `STATO_ANNULLATA` di `_annullo_con_legami`. Ora lo chiedono al DB: BB
`documento_modello.e_stato_di_annullo(testata, codice)` (`fn_doc_stato_id = fn_stato_abortito_id`), nel cambio
stato di ordine, bolla, preventivo, contratto e commessa (costante nuova `TESTATA_COMMESSE` nel suo repository).
La rotta dell'annullo del reso dichiarava lo stato fisso (`stato_chiesto=STATO_ANNULLATO`): ora
`PassaggioDocumento(stato_del_modello="annullo")`, letto a ogni richiesta. Per questo il campo `emissione` del §9.7
diventa `stato_del_modello: "emissione" | "annullo"`, e `StatoDiEmissione` diventa `StatoDocumento`. Le due
costanti sono ritirate. Test: sul DB, lo stato d'annullo delle otto testate contro la colonna `is_abortito`, e uno
stato non abortito che non lo è. Emerso: `CommesseServiceTests` (`unittest.TestCase`) non aveva il mixin del
modello e avrebbe chiesto al DB di sviluppo: ora ce l'ha; il mixin riconosce come annullo `ANNULLI_DI_PROVA`.

**2. Il «solo da DRAFT» della conferma dell'ordine: NON ritirato, e perché.** Il §9.7 lo chiamava copia della
matrice. Il test sul DB l'ha smentito: **il verbo comune accetta un passaggio allo stesso stato**, che nessuna
matrice ha. Provato il 2026-10-25 su dbdev, in transazione annullata:

| Documento | Richiesta | Esito |
| --- | --- | --- |
| Ordine | `fn_cambia_stato_ordine(id, 'CONFERMATO')` su un ordine CONFERMATO | passa: `CONFERMATO → CONFERMATO` |
| Preventivo | `fn_cambia_stato_preventivo(id, 'EMESSO')` su un preventivo EMESSO | passa: `EMESSO → EMESSO` |
| Bolla | `fn_cambia_stato_ddt(id, 'CONSEGNATO')` su una bolla CONSEGNATA | passa, nessun movimento |

La causa, dalla doc auto-generata: il guard di transizione esce subito quando lo stato non cambia (`IF NEW.<stato>
IS NOT DISTINCT FROM OLD.<stato> THEN RETURN NEW`, per esempio `trgfn_ordini_guard_transizione`), quindi la
matrice non viene consultata, e il verbo non rifiuta prima. Per l'ordine il controllo del service è oggi l'**unica**
cosa che ferma una seconda conferma: si lascia, dichiarato nel codice e nel test DB (`test_conferma_due_volte`, che
oggi si aspetta `E_ORD_STATO_TRANSIZIONE`).

⚠️ **Lo stesso buco è aperto su «Emetti» di preventivo e bolla**, che il controllo non l'hanno mai avuto: un secondo
`POST …/emetti/` su un documento già emesso passa dal verbo senza errore e genera un secondo PDF. Il bottone nel
frontend è nascosto dalle capability, ma un client può chiamare l'API. Non metto una copia del controllo nei due
service: sarebbe un tampone, e il difetto è nel modello.

**Richiesta al team DB (priorità alta, difetto del modello).** Il verbo comune rifiuta il passaggio X → X quando la
matrice non ha la riga X → X (in `script.fn_guard_passaggio` o nel verbo, lo sceglie il team DB), col codice di
transizione non ammessa del documento. Da decidere col team DB: cosa resta della scorciatoia «stato invariato» nei
guard (un `UPDATE` della riga che riscrive lo stesso stato, come `test-ritiro-alla-chiusura-documento-v1` 7, non deve
diventare un errore: la regola vale per il **verbo**, non per ogni `UPDATE`). Ricaduta BE dopo l'apply: si ritira
`_assert_stato` dalla conferma dell'ordine, `test_conferma_due_volte` si aspetta il codice della matrice, e un test
DB per preventivo e bolla prova che il secondo «Emetti» è rifiutato.

**Provato (§9.8):** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6963 test. Prima corsa: un rosso fuori perimetro,
`core/tests/db/test_processi_accensione_db.test_un_non_spegnibile_rifiuta_col_suo_codice` (`E_CORE_VALIDATION` al
posto di `E_PROCESSO_NON_SPEGNIBILE`), verde da solo e nella seconda corsa completa, verde per intero: instabile,
non toccato, da guardare a parte. mypy (cricchetto, 0 rilievi) e ruff puliti.

### 9.9 Tre ritocchi dopo la rilettura (team BE, 2026-10-25, ok di Tid)

* **Il controllo «lo stato esiste?» nel cambio stato dell'ordine: ritirato.** Leggeva l'id dello stato chiesto solo
  per un 400 del dominio, e l'id non era più usato: il verbo prende il codice e risponde da sé
  `E_STATO_WORKFLOW_NON_TROVATO`. Con lui è ritirato `OrdiniRepository.get_stato_id_by_codice`, rimasto senza
  chiamanti. Test: unitario (il codice del verbo passa) e sul DB (`test_stato_inesistente`).
* **Lo stesso controllo nella bolla: NON ritirato.** Provato sul DB: il verbo della bolla tratta uno stato
  sconosciuto come chiamata malformata, `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`, un 500 «segnala
  all'assistenza»), mentre i gemelli di ordine e preventivo rispondono `E_STATO_WORKFLOW_NON_TROVATO`. Togliere il
  controllo avrebbe trasformato un 400 in un 500. Resta, dichiarato nel codice.
  **Richiesta al team DB:** `vendite.fn_cambia_stato_ddt` risponde a uno stato che il vocabolario non ha con
  `E_STATO_WORKFLOW_NON_TROVATO`, come i gemelli (il ramo `v_stato_a_id IS NULL`; il guard dei parametri NULL o
  vuoti può restare tecnico). Si unisce alla richiesta del §9.8. Ricaduta BE dopo l'apply: si ritirano il controllo
  di `ddt_service._passa_a` e `DdtRepository.get_stato_id_by_codice`.
* **Test di `PassaggioDocumento`:** l'helper della view finta usava il parametro `ddt_id` per tutte le testate; ora
  ha un nome neutro, `documento_id`. Nessun cambio di comportamento.
* **Non toccato, già deciso:** `_STATI_DA_EMESSA` di `offerte_service` (gli stati di partenza di accettazione,
  rifiuto e revisione) è una copia Python della matrice, da ritirare per M-5 nel giro dell'offerta (D-4).

**Provato (§9.9):** test unitari di vendite, core e documenti verdi; test sul DB di `vendite` e il presidio delle
rotte verdi; mypy e ruff puliti. Suite completa (6964): 8 rossi, tutti fuori da questo giro e con la stessa causa,
il giro DB di `brief-db-parametri-senza-override` applicato su dbdev durante la sessione (`1b2e26556`, su
`dev/db-tid`): i codici nuovi `E_PARAMETER_OVERRIDE_NON_AMMESSO` / `_PRESENTI` senza policy (i due presidi della
policy) e il guard nuovo sugli override che rifiuta le fixture di `test_parameter_overrides_db` (5) e
`test_accessi_db` (1). Tocca al passaggio BE di quel brief.

### 9.10 Il difetto X → X e lo stato sconosciuto della bolla (team DB, 2026-10-26)

**La scelta (Tid, 2026-10-26): il rifiuto sta nella prima riga del verbo, con un codice comune.** Erano
due le sedi possibili:

| | Prima riga (`script.fn_guard_passaggio`), codice comune | Guard di transizione, codice del documento |
| --- | --- | --- |
| Dove | una funzione, per tutti i documenti sul modello e per quelli dei giri dopo | una riga in quattro guard, e in ogni giro futuro |
| Quando parla | prima di ogni lavoro del verbo | alla scrittura, dopo il lavoro fra le due metà |
| Codice | `E_DOC_GIA_NELLO_STATO`, nuovo | quello di transizione di ciascun documento |

Il secondo modo avrebbe fatto parlare tardi la bolla: un secondo «Emetti» rifà i controlli della merce
(`fn_check_ddt_merce`, che riprova i prelievi già consumati) prima della scrittura, e un motivo sbagliato,
come la giacenza, poteva arrivare prima della risposta giusta. La richiesta del §9.8 chiedeva il codice del
documento: è cambiato per questo motivo.

**Che cosa resta della scorciatoia «stato invariato» nei guard:** tutta. Il guard di transizione giudica i
**cambi** di stato e lascia passare un `UPDATE` che riscrive lo stesso stato (il salvataggio della riga
intera, `test-ritiro-alla-chiusura-documento-v1` 7). Il verbo chiesto con lo stato che il documento ha già
lo vede solo la prima riga. Sono due giudici che non si toccano, e la matrice resta l'unica fonte: una riga
X → X, se un giorno ci fosse, sarebbe un passaggio come gli altri.

**Scritto:**

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261026-01-update-fn-guard-passaggio-stesso-stato` | nessuna riga per il passaggio e stato chiesto = stato di oggi: `E_DOC_GIA_NELLO_STATO` («Il documento è già nello stato %s: non c'è niente da cambiare.», il codice dello stato da `script.fn_doc_stato_codice`) |
| `20261026-02-update-fn-cambia-stato-ddt-stato-sconosciuto` | §9.9: uno stato che il vocabolario della bolla non ha risponde `E_STATO_WORKFLOW_NON_TROVATO`, con lo stesso contesto e lo stesso valore dei gemelli. Il guard dei parametri NULL o vuoti resta tecnico |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_DOC_GIA_NELLO_STATO`, `CONFLITTO_STATO` (409), id 1399; la `causa` di `E_STATO_WORKFLOW_NON_TROVATO` elenca i quattro verbi che lo sollevano |
| guida del modello §5, pagina manuale di `fn_guard_passaggio` | la regola, scritta come stato attuale |

**Uniforme per costruzione, non per copia.** La regola vale per ogni documento che passa dal verbo comune:
oggi ordine, preventivo, bolla e reso. Contratto, offerta, commessa e fattura non ci passano ancora, e lo
stesso buco è aperto lì (letto il 2026-10-26: `vendite.fn_cambia_stato_commessa` fa l'`UPDATE` senza la prima
riga, e il guard di transizione della commessa esce a stato invariato). Non si chiude documento per documento:
si chiude **portandoli al verbo comune** nel loro giro (il contratto per primo), senza una riga in più. Nel
giro di ognuno, un pgTAP prova il secondo passaggio allo stesso stato.

Nella frase lo stato e non il documento: chi la legge è sul documento, e l'etichetta da `config.sorgenti`
sarebbe stata la terza copia della stessa lettura (porta e nascita nello stato iniziale la fanno già).

**Applicato e verde (Tid, 2026-10-26):** migrazione su dbdev e corsa pgTAP come app.

**Provato prima dell'apply (2026-10-26),** sullo scratch `zeroerp_ruoli` come `zeroerp_owner`: SQL estratto dai changeSet e
righe dei CSV, nella transazione annullata di ogni pgTAP (scratch rimasto pulito, md5 delle due funzioni
uguali a prima).

| pgTAP | Con | Senza | Test nuovi |
| --- | --- | --- | --- |
| `script/test-doc-verbo-comune-e-porta-v1` (plan 20 → 24) | 22/24 | 19/24 | 19 secondo «Emetti» della bolla, 20 secondo annullo del reso, 22 bolla con uno stato che non c'è: rossi senza. 21, un `UPDATE` che riscrive lo stesso stato passa: verde in tutte e due, è l'invariante |
| `vendite/test-ordine-al-modello-v1` (16 → 17) | 16/17 | 15/17 | 13 seconda conferma dell'ordine: senza, passa |
| `script/test-doc-lettori-stato-e-preventivo-al-modello-v1` (22 → 23) | 22/23 | 21/23 | 19 secondo «Emetti» del preventivo: senza, passa |

Gli unici rossi «con» sono i test della porta che lo dichiarano: rossi da owner, verdi come app.

**Regressione:** 40 pgTAP che chiamano i verbi (`fn_cambia_stato_*`, verbi del reso e d'annullo,
`fn_guard_passaggio`), prima e dopo: asserzioni eseguite, `ok` e `not ok` uguali su tutti e 40. Due muoiono
nella fixture in tutte e due le corse, `vendite/test-fn-cambia-stato-preventivo` e
`vendite/test-preventivi-guard-emissione-iva` (il billing account, già in tutte e due le baseline come
`ERRORE_FIXTURE`): letti a mano, nessuno chiede lo stato che il documento ha già. I builder delle fixture
non lo chiedono mai: il percorso di `dbops.fn_pgtap_porta_a_stato` da uno stato a sé stesso è vuoto.

**Attese cambiate, dichiarate:**

* la seconda conferma del reso risponde `E_DOC_GIA_NELLO_STATO` e non più `E_RESO_STATO_NON_CONFERMABILE`, e
  il secondo annullo `E_DOC_GIA_NELLO_STATO` e non più `E_RESO_STATO_NON_ANNULLABILE`: la prima riga viene
  prima del controllo del reso. Da tutti gli altri stati i due codici del reso restano;
* l'annullo di un ordine, di una bolla o di un preventivo già annullato (`fn_annulla_ordine`,
  `fn_annulla_ddt`, `fn_annulla_preventivo`) passava senza errore e senza cambiare niente: ora risponde
  `E_DOC_GIA_NELLO_STATO`;
* la bolla con uno stato che non c'è: `E_STATO_WORKFLOW_NON_TROVATO` (`NON_TROVATO`) invece di
  `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`).

**Richiesta al team BE, dopo l'apply (elenco chiuso):**

1. il codice nuovo `E_DOC_GIA_NELLO_STATO` (`CONFLITTO_STATO`): la policy rigenerata e il ripiego in
   `error_messages_fallback.py`, come per ogni codice nuovo (i due presidi della policy);
2. ordine: si ritira il controllo `_assert_stato` dalla conferma (§9.8 punto 2); `test_conferma_due_volte`
   si aspetta `E_DOC_GIA_NELLO_STATO`;
3. un test DB per preventivo e bolla: il secondo «Emetti» è rifiutato con `E_DOC_GIA_NELLO_STATO`, e non
   nasce un secondo PDF;
4. bolla (§9.9): si ritirano il controllo di `ddt_service._passa_a` e `DdtRepository.get_stato_id_by_codice`;
   il test sul DB dello stato che non c'è si aspetta `E_STATO_WORKFLOW_NON_TROVATO`;
5. il commento di `resi_service.conferma_reso` elenca i guard della funzione madre: si aggiunge la seconda
   conferma, `E_DOC_GIA_NELLO_STATO`.

Da sapere, nessuna modifica attesa: il ramo «no-op» del cambio stato del preventivo (ACCETTATO →
ACCETTATO, §8.7 punto 5), se chiamasse ancora il verbo, riceverebbe `E_DOC_GIA_NELLO_STATO` e non più
`E_PREV_TRANSIZIONE_NON_AMMESSA`.

## 10. Ereditati da brief-db-grammatica-unica-documenti (2026-10-25)

Il brief della grammatica unica si è chiuso il 2026-10-25 (lotto 4, il presidio) ed è in
[work-done](../work-done/brief-db-grammatica-unica-documenti.md). Due punti non erano grammatica e passano qui
(scelta di Tid, 2026-10-25):

* **D-G1 — il blocco «origine» della stampa della fattura, che non si vede mai** (dal suo §12.9, in fondo). I
  modelli della fattura (le versioni pubblicate 2334 e 3097 su dbdev, al 2026-10-19) hanno il blocco
  `fattura.origine.tipo`, ma `VenditeRepository.get_fattura_testata` non porta né `origine_tipo` né
  `origine_codice`: sulla carta il blocco resta sempre vuoto. Non è la correzione dell'ordine (L2b-1, etichetta in
  `config.sorgenti`): una fattura può nascere da più documenti. **Da decidere (Tid), nel giro della fattura**:
  togliere il blocco dal modello, o dire che cosa una fattura chiama «origine»;
* **D-G2 — la prova a video del lotto 2b** (dal suo §12.7, riga 6-septies-d), a Tid quando vuole: «Genera ordine»
  da un'offerta accettata; la finestra dell'annullo con legami di un ordine nato da offerta («Offerta …, torna
  trasformabile», col link) e di una commessa con righe da reso e da consumi; il pannello di smistamento di un
  preventivo misto (tag Ordine/Commessa, «Smista tutto» / «Smista selezionate», il routing verso ordine e
  commessa).

## 11. Giro 8: il contratto al modello — ricognizione e piano (2026-10-26)

✅ **Via di Tid il 2026-10-26** alla ricognizione del contratto, il primo dei giri dopo l'ordine (W-1). Lo
sviluppo parte con le risposte alle domande del §11.3.

### 11.1 Com'è oggi (doc auto-generata, dbdev e `backend/`, 2026-10-26)

* **Vocabolario e matrice.** `config.stati_doc_contratti`: DRAFT (iniziale, `is_bozza`), ATTIVO (emissione),
  CESSATO (terminale, esito positivo), ANNULLATO (`is_abortito`). Matrice `config.transizioni_stati_contratti`,
  tre righe, tutte **manuali**: DRAFT → ATTIVO «attiva», DRAFT → ANNULLATO «annulla», ATTIVO → CESSATO «cessa»
  (`requires_date`). La matrice **non ha** la colonna `azione_processo_codename`.
* **Guard di transizione** `trgfn_contratti_guard_transizione_stato`: ⛔ **non legge la matrice.** I passaggi
  ammessi sono scritti negli `IF` (DRAFT → ATTIVO, DRAFT → ANNULLATO, ATTIVO → CESSATO), e la tabella la legge
  solo la capability: è la «seconda matrice» della guida §4. Poi le condizioni dei passaggi, che restano: verso
  ATTIVO prezzi autorizzati, indirizzi del cliente, righe, contratto sovrapposto; ATTIVO → CESSATO chiede
  `valido_al`, e manuale non retroattiva (`E_CONTRATTO_VALIDO_AL_RETROATTIVO`). Codice del rifiuto:
  `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA`. Il trigger ha già il `WHEN` sullo stato che cambia.
* **Verbo di stato: non c'è.** Lo stato lo scrivono:
  * il **backend** con un `UPDATE` (`ContrattiRepository.update_stato`), da `contratti_service.emetti` («Emetti»,
    con il PDF nella stessa transazione) e da `cambia_stato` (la cessazione);
  * `vendite.fn_annulla_contratto` (DEFINER, ritira i legami) con un `UPDATE` suo e il letterale `'ANNULLATO'`;
  * il **job notturno** `dbops.fn_apply_chiusura_scadenze` (INVOKER, gira come `zeroerp_job`, che non è
    membro del proprietario): ATTIVO → CESSATO dei contratti con `valido_al` scaduto, con un `UPDATE`
    dinamico. Il framework è generico (`dbops.automazione_chiusura_scadenze`: contratti e versioni di
    listino). Accende la GUC `app.cessazione_automatica`, e il guard su quella GUC ammette la data passata.
    ⚠️ La GUC la può accendere qualunque sessione, anche l'applicazione: oggi chiunque scriva lo stato a mano
    con quella GUC cessa un contratto con una data passata.
* **La cessazione programmata sta in Python.** `cambia_stato` verso CESSATO: `valido_al` obbligatorio; se è
  futura scrive solo la data e lascia lo stato ATTIVO (lo chiuderà il job); se è oggi scrive data e stato. La
  regola «futura = programmata, oggi = immediata» e il «valido_al obbligatorio» sono decisioni di dominio
  fuori dal database, e il secondo ripete il guard. `fn_chiudi_contratto_per_successione` (il rinnovo
  dall'offerta) scrive solo `valido_al`: è una cessazione programmata anche lei.
* **Chi crea:** `fn_push_offerta_a_contratto` e la `create` del backend; nascono in DRAFT dal trigger della
  nascita. Nessuno crea o attiva un contratto senza «Emetti».
* **Azione: nessuna** a catalogo per il contratto.
* **Numero alla nascita.** `trgfn_contratti_gen_codice` numera all'INSERT (e a un UPDATE che svuota il
  numero), come l'ordine (Z-4): la guida §7 lo vuole all'emissione.
* **Capability** `fn_available_actions_contratto`: dalla matrice, coi motivi; nessun filtro sull'azione.
* **Backend, da sapere:** `cambia_stato` dichiara «resta per CESSATO, ANNULLATO, SOSPESO», e i test del
  service usano SOSPESO; il vocabolario non ha SOSPESO (letto il 2026-10-26).
* **pgTAP:** 21 file scrivono lo stato del contratto con un `UPDATE` diretto, il builder
  `dbops.fn_pgtap_crea_contratto` (12 file) costruisce ATTIVO con un `UPDATE`, 3 file provano il job su
  contratti. Conteggio del 2026-10-26, per dimensionare il porting.

### 11.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| matrice | colonna `azione_processo_codename` su `config.transizioni_stati_contratti` (FK alla chiave stabile), valori dal CSV secondo Y-1; mirror con la colonna (⚠️ `nullValue`) |
| guard | `trgfn_contratti_guard_transizione_stato` legge la matrice (Regola 1 come ordine e preventivo); gli `IF` dei passaggi si ritirano, le condizioni restano; il ramo «automatica» secondo Y-2 |
| azione | secondo Y-1 |
| verbo | NUOVO `vendite.fn_cambia_stato_contratto(p_contratto_id, p_stato)`, gemello di ordine e preventivo: DEFINER col predicato del perimetro (`fn_scope_ef_whitelist_via_contratto`), `fn_doc_stato_id`, `fn_guard_passaggio` (anche lo stato che ha già), `fn_doc_scrivi_stato` |
| cessazione | secondo Y-2 e Y-3 |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.contratti`; la fixture `fn_pgtap_porta_a_stato` conosce il verbo |
| annullo | `fn_annulla_contratto` chiama il verbo, lo stato d'annullo dal vocabolario (`fn_stato_abortito_id`) |
| capability | il passaggio con l'azione si nasconde a chi non ce l'ha (stessa forma degli altri) |
| fixture | `fn_pgtap_crea_contratto` costruisce ATTIVO dal verbo; i 21 `UPDATE` diretti portati al verbo o al builder; i 3 test del job secondo Y-2 |
| guida | §10, riga del contratto; la guida dei contratti rimanda al modello |

**Richiesta al BE** (col percorso intero, a giro DB provato): `ContrattiRepository.update_stato` si ritira;
«Emetti» e la cessazione chiamano il verbo; il 403 dalla riga del passaggio (`PassaggioDocumento`); la
cessazione programmata secondo Y-3; SOSPESO, che non esiste, esce da commento e test.

### 11.3 Domande per Tid

✅ **Decise da Tid il 2026-10-26: Y-1, Y-2, Y-3, Y-4 come da proposta; via allo sviluppo.**

* **Y-1. L'azione del contratto.** Proposta: azione **nuova** `emetti_contratto` («attiva un contratto o lo
  cessa») sulle righe DRAFT → ATTIVO e ATTIVO → CESSATO; DRAFT → ANNULLATO senza azione (M-4, come le altre
  bozze). È la guida §6 e il gemello di `emetti_ordine`: la cessazione è un passaggio pesante (ferma la
  fatturazione). ⚠️ Nessun profilo la riceve dai seed: concederla è un dato, su dbdev lo fai tu. Alternativa:
  l'azione sulla sola attivazione, la cessazione col solo permesso sul documento.
* **Y-2. La cessazione automatica del job.** Con la porta il job non scrive più lo stato con l'`UPDATE` (non è
  il proprietario). Proposta: per le testate della mappa del modello, il framework scrive attraverso la
  scrittura comune, da un pezzo `SECURITY DEFINER` (la versione di listino resta com'è fino al suo giro); la
  GUC `app.cessazione_automatica` si **ritira**. La regola si divide fra i due verbi: il guard chiede solo
  `valido_al`; il verbo manuale rifiuta la data passata; il job cessa solo i contratti scaduti. Così chiude
  anche il buco della GUC che chiunque può accendere. Alternativa: la porta riconosce il job come secondo
  scrittore, e la GUC resta.
* **Y-3. La cessazione programmata nel database.** Proposta: un verbo di cessazione,
  `vendite.fn_cessa_contratto(p_contratto_id, p_valido_al)`, decide lui: data passata → rifiuto; oggi →
  data e CESSATO dal verbo di stato; futura → solo la data (il job la chiuderà). Il backend chiama solo
  quello, e le due copie Python (la data obbligatoria, la scelta programmata/immediata) si ritirano.
  `fn_chiudi_contratto_per_successione` resta com'è (scrive una data futura, è già il caso «programmata»).
  Alternativa: la scelta resta nel backend, il verbo di stato riceve solo CESSATO.
* **Y-4. Il numero alla nascita.** Come Z-4 per l'ordine. Proposta: **fuori da questo giro**, dichiarato
  come divergenza nella riga del contratto della guida §10.

### 11.4 Scritto (2026-10-26)

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261026-03-alter-transizioni-contratti-azione-processo` | colonna `azione_processo_codename` su `config.transizioni_stati_contratti`, FK al catalogo delle azioni |
| CSV `azioni_processo` (id 42), `transizioni_stati_contratti`, mirror `20260528-06` | `emetti_contratto` a catalogo; sulle righe DRAFT → ATTIVO e ATTIVO → CESSATO (Y-1); mirror con la colonna e `nullValue: "NULL"` |
| `-04-update-trgfn-contratti-guard-transizione-matrice` | il guard legge la matrice (gli `IF` dei passaggi si ritirano); verso CESSATO `valido_al` valorizzata **e arrivata** (`<= fn_data_operativa()`) per chiunque; la GUC `app.cessazione_automatica` non si legge più (Y-2) |
| `-05-create-fn-cambia-stato-contratto` | il verbo di stato, gemello di quello dell'ordine |
| `-06-create-fn-cessa-contratto` | la cessazione con la sua data (Y-3): senza data `E_CONTRATTO_CESSAZIONE_SENZA_DATA`; prima riga comune; la strada dalla matrice; data passata `E_CONTRATTO_VALIDO_AL_RETROATTIVO`; oggi → CESSATO; futura → solo la data, `programmata = true` |
| `-07-create-fn-cessa-contratti-scaduti` | il verbo del job (Y-2): ATTIVO con `valido_al` passata, nel perimetro della sessione, → CESSATO dalla scrittura comune |
| `-08-update-fn-apply-chiusura-scadenze-verbo-di-chiusura` | il framework: per una testata sotto la porta chiama il suo verbo di chiusura (oggi il contratto); sotto la porta senza verbo, `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`; la GUC si ritira |
| `-09-update-fn-annulla-contratto-verbo-comune` | l'annullo passa dal verbo di stato, lo stato d'annullo dal vocabolario |
| `-10-create-trigger-stato-solo-dal-verbo-contratti` | la porta sul contratto |
| `-11-update-fn-available-actions-contratto-permesso-del-passaggio` | permesso ⇒ nascondi; l'attivazione dal vocabolario (`emissione`) |
| `-12`, `-13` (fixture) | `fn_pgtap_porta_a_stato` conosce il verbo del contratto; il builder attiva da lì |
| CSV errori | `E_CONTRATTO_CESSAZIONE_SENZA_DATA` (nuovo, `DATO_ERRATO`, id 1400); `E_CONTRATTO_VALIDO_AL_RETROATTIVO` cambia sede (dal guard al verbo della cessazione); la `causa` di `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` riscritta sulla matrice |
| doc | guida del modello §10 (riga del contratto), guida dei contratti §3.1, linee guida SQL §7c, le due pagine delle GUC, pagina manuale del guard; pagine manuali nuove dei tre verbi |

**Una precisazione su Y-2, dichiarata.** La proposta diceva «il guard chiede solo `valido_al`». Scritto, il
guard chiede `valido_al` **arrivata**: altrimenti il cambio di stato generico verso CESSATO, con una data
futura già scritta, cesserebbe un contratto prima della sua fine, scavalcando la cessazione programmata. Con
la data arrivata le strade dicono la stessa cosa: la cessazione di oggi, il job sugli scaduti, e il cambio di
stato generico solo dove il job arriverebbe comunque.

**Firme e tipi** (rilievo di Tid, 2026-10-26): i corpi presi dal vivo (`-08`, `-09`, `-11`, `-13`) avevano la
firma sciolta nei tipi base da `pg_get_functiondef`; firma e `RETURNS TABLE` ripresi ancorati dall'ultimo
YAML di ciascuna, con `SECURITY INVOKER` esplicito. I `DECLARE` nudi rimasti sono dei corpi esistenti e
sono valori calcolati (conteggi, SQL dinamico, jsonb) o id della fixture polimorfa, dichiarati nei loro
commenti.

### 11.5 Prova e regressione (2026-10-26)

Sullo scratch `zeroerp_ruoli` come `zeroerp_owner`: SQL estratto dei changeSet `-03` … `-13` e seed simulato
(azione, matrice, codice nuovo), nella transazione annullata di ogni file.

* **Nuovo** `vendite/test-contratto-al-modello-v1` (22): 21/22 da owner; il rosso è il 22, la porta, dichiarato
  «rosso da owner».
* **Regressione, prima del porting:** 64 file che toccano lo stato del contratto, il suo builder, la capability,
  l'annullo o il job. 18 cambiavano, tutti per le tre cause attese: la porta (l'`UPDATE` diretto dello stato),
  permesso ⇒ nascondi (senza `emetti_contratto` «Attiva» non c'è), la cessazione con data futura via cambio di
  stato. Tre erano già tronchi prima del giro, identici dopo (`test-documenti-canali-sync-v1`,
  `test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1`, `test-fn-resolve-prezzo-listino-v2-v1`).
* **Porting dei 18** (tre agenti in parallelo, ogni file provato col file composto) e di
  `script/test-doc-verbo-comune-e-porta-v1` (la porta su cinque testate: test 9 e 10). Attese cambiate,
  dichiarate in testa ai file:
  * `test-contratti-guard-transizione-stato-v1` (9 → 12): il 4 («ATTIVO → CESSATO con data futura ammesso»)
    ora è rifiutato, con 4b e 4c sulla cessazione programmata da `fn_cessa_contratto`; il 5 (retroattiva) lo
    rifiuta il verbo della cessazione; il 9 (la GUC) diventa il job, col 10 nuovo;
  * `test-contratto-attiva-spento-se-sovrapposto-v1` (24 → 22): **11 e 12 ritirati** (Tid, 2026-10-26).
    Provavano la quintupla di NEW in un `UPDATE` che cambiava date e stato insieme: con la porta lo stato lo
    scrive solo la scrittura comune, che tocca la sola colonna di stato, e il caso non ha più una strada. Il
    contratto cessato e il suo gemello vanno nel passato (un CESSATO con data futura non è più raggiungibile);
  * `test-trgfn-doc-righe-lock-fuori-bozza-v1`: il contratto cessato nasce nell'anno della data operativa
    (prima nel 2072), per la stessa ragione; cambia il dato, non l'attesa.
* **Regressione finale:** 68 file (i 64, il nuovo, e i pgTAP del modello di
  ordine, preventivo e verbo comune), in sequenza. **56 verdi pieni**, tutte le asserzioni eseguite. Gli altri
  12, ciascuno identico prima e dopo dove il file non è cambiato:
  * rossi da owner dichiarati (la porta, la GUC accesa a mano): `test-contratto-al-modello-v1` 22,
    `test-ordine-al-modello-v1` 17, `test-doc-lettori-stato-e-preventivo-al-modello-v1` 23,
    `test-doc-verbo-comune-e-porta-v1` 23 e 24, `test-annullo-documento-con-legami-v1` 30;
  * rossi già prima del giro, uguali dopo: `test-capability-annulla-aspetto-e-stato-leggibile-v1` (3),
    `test-contratti-utilities-guard-tipo-classe-v1` (6), `test-fn-contratto-righe-preview-nuovi-campi-v1` (1),
    `test-listini-versioni-guard-transizione-stato-v1` (7); tronchi già prima, uguali dopo:
    `test-documenti-canali-sync-v1`, `test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1`,
    `test-fn-resolve-prezzo-listino-v2-v1`.

  La misura che conta (come app) arriva dalla corsa di Tid dopo l'apply.
* **Applicato e verde (Tid, 2026-10-26):** migrazione su dbdev e corsa pgTAP come app.

### 11.6 Richiesta al team BE (elenco chiuso, dopo l'apply)

1. **«Emetti»** (`contratti_service.emetti`): lo stato dal verbo `vendite.fn_cambia_stato_contratto(id,
   'ATTIVO')`, nella stessa transazione del PDF; `ContrattiRepository.update_stato` si ritira (la porta
   rifiuta l'`UPDATE`).
2. **La cessazione** (`cambia_stato` verso CESSATO): chiama `vendite.fn_cessa_contratto(id, valido_al)` e
   restituisce `programmata`. Si ritirano le due copie Python: la data obbligatoria (ora
   `E_CONTRATTO_CESSAZIONE_SENZA_DATA`, campo `valido_al`) e la scelta programmata/immediata, con la scrittura
   di `valido_al` prima dello stato.
3. **Il 403 dalla riga del passaggio** (`PassaggioDocumento`) su «Emetti» e sulla cessazione: chiedono
   `emetti_contratto`. L'annullo della bozza no.
4. **Codici nuovi nella policy**: `E_CONTRATTO_CESSAZIONE_SENZA_DATA` (`DATO_ERRATO`) e, se non è già fatto col
   §9.10, `E_DOC_GIA_NELLO_STATO`; il ripiego in `error_messages_fallback.py`.
5. **SOSPESO**, che il vocabolario non ha, esce dal commento di `cambia_stato` e dai test del service.
6. **Test Django** che scrivono lo stato del contratto con un `UPDATE` o si aspettano la cessazione con data
   futura via cambio di stato: si portano al verbo e alla cessazione programmata.
7. **Doc** `docs/it/backend/vendite/manual/api_contratti.md` (riga ~1127): la chiusura dei contratti scaduti
   non usa più la GUC `app.cessazione_automatica`, ma il verbo `vendite.fn_cessa_contratti_scaduti`.

Da sapere, nessuna modifica attesa: l'handler della coda `chiusura_scadenze_handler` chiama ancora
`dbops.fn_apply_chiusura_scadenze()` e riceve lo stesso jsonb; un secondo «Emetti» o «Cessa» risponde
`E_DOC_GIA_NELLO_STATO`. ⚠️ `emetti_contratto` non lo riceve nessun profilo dai seed: senza, nessuno attiva
o cessa un contratto. Concederla è un dato, su dbdev lo fa Tid.

### 11.7 Fatto dal team BE (2026-10-26): §9.10 punti 1-5 e §11.6 punti 1-7, in un passaggio solo

**§9.10 — il passaggio allo stato che il documento ha già.**

1. `E_DOC_GIA_NELLO_STATO` (`CONFLITTO_STATO`, 409) ed `E_CONTRATTO_CESSAZIONE_SENZA_DATA` (`DATO_ERRATO`, 400):
   policy rigenerata dal catalogo (`genera_error_policies`, con git allineato al DB) e ripiego senza segnaposto in
   `error_messages_fallback.py`. Nello stesso giro la rigenerazione ha preso la nota nuova di
   `E_PARAMETER_OVERRIDE_NON_AMMESSO` (`31881207e`, brief-db-parametri-senza-override §6.8): classe invariata.
2. Ordine: `_assert_stato` ritirato dalla conferma. Seconda conferma e ordine inesistente li dice il verbo
   (`E_DOC_GIA_NELLO_STATO`, `E_ORD_NOT_FOUND`). `test_conferma_due_volte` (DB) si aspetta il codice nuovo; il test
   unitario della seconda conferma prova che il codice del verbo passa e che lo step della pratica non si chiude.
3. Secondo «Emetti»: test sul DB per la bolla (rifiutato con `E_DOC_GIA_NELLO_STATO` **prima** dei controlli della
   merce, giacenza invariata) e per il preventivo (il codice nel campo dedicato dell'eccezione). Che non nasca un
   secondo PDF lo prova la view, che è la factory comune di tutti i documenti: un rifiuto del verbo risponde 409 e
   `genera_documento` non parte (`test_ddt_api.test_emetti_rifiutato_non_genera_il_documento`).
4. Bolla: ritirati il controllo «lo stato esiste?» di `ddt_service._passa_a` e `DdtRepository.get_stato_id_by_codice`;
   lo stato che non c'è lo dice il verbo (`E_STATO_WORKFLOW_NON_TROVATO`), con un test sul DB.
5. `resi_service`: i commenti di `conferma_reso` e `annulla_reso` nominano la seconda conferma e il secondo annullo.

**§11.6 — il contratto.**

1. «Emetti» scrive lo stato dal verbo `fn_cambia_stato_contratto` (lo stato di emissione dal vocabolario);
   `ContrattiRepository.update_stato` e `get_stato_id_by_codice` ritirati.
2. La cessazione chiama `fn_cessa_contratto(id, valido_al)` e la risposta porta `programmata`. Ritirate le due copie
   Python (data obbligatoria, scelta programmata/immediata) e la PATCH di `valido_al` prima dello stato. Gli altri
   stati vanno al verbo di stato, che giudica anche lo stato che non c'è. ⚠️ **Una regola nuova, dichiarata**:
   `valido_al` con uno stato diverso da `CESSATO` è un 400 col campo. Prima veniva scritta con una PATCH accanto a
   qualunque passaggio; ora nessun verbo la scriverebbe, e scartarla in silenzio direbbe al client che è stata presa.
3. Il 403 dalla riga del passaggio: `emetti_passaggio=TESTATA_CONTRATTI` sulla view di «Emetti», `post_passaggio`
   (campo `codice_interno`) sul cambio stato; l'annullo della bozza resta al permesso sul documento.
4. Codici nella policy: vedi §9.10 punto 1.
5. SOSPESO uscito da commento e test.
6. Test Django portati: i test del service passano dai verbi (cessazione oggi e futura, i tre rifiuti del verbo, lo
   stato sconosciuto, l'annullo); test nuovo sul DB `vendite/tests/db/test_contratto_cambia_stato_db.py` (7: «Emetti»,
   senza azione, secondo «Emetti», cessazione oggi e programmata, senza data e retroattiva, annullo della bozza).
   `test_contratto_attiva_sovrapposto_db` concede `emetti_contratto`. `test_date_validita_guard_comune_db` ora cessa
   un contratto **ATTIVO**: da bozza la cessazione non ha più strada (il verbo guarda la matrice prima della data).
7. `api_contratti.md`: stati, cessazione, permessi e risposta del cambio stato, auth di «Emetti».

**Fuori dall'elenco, nello stesso passaggio.**

* **Frontend**, `ContrattoDrawer`: il messaggio dell'esito della cessazione legge `programmata` dalla risposta. Il
  calcolo locale «data futura = programmata» resta solo come anteprima nel dialog, prima della conferma.
* **Smoke** `smoke-test-listini-v5.sh`: tolto l'`UPDATE` diretto dello stato dei contratti dalla pulizia iniziale.
  La porta ora lo rifiuta, e girava nello stesso `psql -c` delle altre pulizie: il rifiuto le avrebbe annullate
  tutte, in silenzio. Tolta anche la cessazione senza data della pulizia finale. I contratti li chiude già
  `smoke_chiudi_contratti`, all'inizio e all'uscita.

**Richiesta al team DB (priorità bassa, scelta di Tid 2026-10-26: «fai a) e segnala al DB»).** Lo stato della
cessazione non ha un lettore nel vocabolario, come invece hanno l'emissione e l'annullo: `fn_cessa_contratto`
lo scrive come letterale (`v_cessato := 'CESSATO'`), e così `fn_cessa_contratti_scaduti`
(`fn_doc_stato_id(..., 'CESSATO')`). Per instradare la cessazione al suo verbo, il backend ha dovuto ricopiare lo
stesso letterale (`contratti_repository.STATO_CESSATO`, dichiarato). Si chiede un lettore dello stato di
cessazione, cioè l'esito positivo terminale (per esempio una colonna o un `esito` sul vocabolario, letto da una
funzione gemella di `fn_stato_abortito_id`), usato dai due verbi. Ricaduta BE dopo l'apply: `STATO_CESSATO`
si ritira e il service chiede al lettore.

**Provato:** suite completa sul DB reale (`ZEROERP_TEST_DB_E2E=1`), **6975 test verdi** (1 saltato, 1 fallimento
atteso, già noti); vitest di `vendite` (157 verdi); ruff, eslint, oxlint puliti; mypy col cricchetto a 0 rilievi.
Lo smoke non è stato lanciato. ⚠️ Senza `emetti_contratto` concessa al profilo nessuno attiva o cessa un contratto:
per il collaudo a video serve il dato su dbdev.

**Stato letto dal team DB (2026-10-26, dopo il commit).** Il passaggio è committato in due pezzi: `fe041a1a1`
(i punti sopra) e `0a08565be`, un ritocco fuori elenco, non descritto sopra:
* `ContrattoDrawer`: l'esito della cessazione si legge dal ritorno dell'azione dello store, non da quello di
  `execute`. Il dettaglio del contratto ha un campo `data` (la data del documento) che `execute` scambiava per
  l'envelope: `programmata` risultava sempre assente e il messaggio diceva «immediata» anche per una cessazione
  programmata;
* `error_ui_overrides.py`: il commento di `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` dice che la regola della data
  sta nel verbo della cessazione, non più nel guard.

Su dbdev, letto da `config.profili_accesso_azioni`: `emetti_ddt` su 2 profili, `emetti_preventivo` ed
`emetti_fattura` su 1, **`emetti_contratto` ed `emetti_ordine` su nessuno**. È un dato, non un difetto del
modello (i seed non le concedono, come per le altre): lo concede Tid. Resta aperta la richiesta al DB del
lettore dello stato di cessazione (riga 4-bis-nonies-octies, priorità bassa).

## 12. Ereditato da brief-design-note-credito-resi (2026-10-26)

Su indicazione di Tid (2026-10-26) il tema passa a questo brief, che tratta le azioni dei documenti sul modello.

* **D-N1 — il censimento dei gate delle azioni PER RIGA** (dal suo §45.9.6, archiviato in
  [work-done](../work-done/brief-design-note-credito-resi.md); la regola e il debito stanno in
  [linee-guida-sql §12.5](../../linee-guida-sql.md), §12.5.6 «Il censimento che non esiste»). Le capability di
  documento hanno il loro censimento (§12.4), le azioni di riga no: «Annulla l'accredito» era acceso su un
  accredito già emesso, ed è uscito solo in collaudo. Il lavoro: azione per azione, la sua sede
  (`script.fn_check_<azione>` + colonna di blocco nella vista di riga) e il FE che la legge (`disabled` +
  `tooltip`). Da fare prima che lo trovi il prossimo collaudo. DB + FE; quando, lo decide Tid.

**Coerenza col cantiere, letta dal team DB (2026-10-26).** Il tema sta bene qui: è il §12.5 delle linee guida
applicato alle azioni di riga, la stessa regola «permesso ⇒ nascondi, stato ⇒ disabilita col motivo» che i
giri portano sulle azioni di documento. Due cose da sapere quando si decide il quando:
* **è un tema su tutti i documenti** (le righe di preventivo, ordine, bolla, reso, contratto, offerta,
  commessa, fattura). Il fermo allentato (PROJECT_CONTEXT, scelta C del 2026-10-25) ammette un tema
  trasversale se poggia su un pezzo comune già fatto, e ferma quello da ricopiare documento per documento:
  una `fn_check_<azione>` per azione è proprio da ricopiare. Le strade sono due: ogni giro porta anche le
  azioni di riga del suo documento (offerta, commessa, fattura, listino; per i documenti già portati, un
  giro di recupero), oppure prima un pezzo comune che legga le azioni di riga e poi il censimento;
* **il censimento si fa sulla struttura**, non sulle righe di oggi: le azioni di riga si contano dalle viste
  di riga e dalle capability che le espongono, e un'azione senza sede è un debito anche se oggi non ha
  ancora sbagliato in collaudo.

## 13. Giro 9: l'offerta al modello — ricognizione e piano (2026-10-26)

✅ **Via di Tid il 2026-10-26** («puoi riprendere»), riga 4-bis-decies: la ricognizione dell'offerta, il giro dopo
il contratto (W-1). Lo sviluppo parte con le risposte alle domande del §13.3.

### 13.1 Com'è oggi (doc auto-generata, CSV e `backend/`, 2026-10-26)

* **Vocabolario e matrice.** `config.stati_doc_offerte`: BOZZA (iniziale), EMESSA (emissione), ACCETTATA,
  RIFIUTATA (terminale), SUPERATA (terminale, `is_superato`), ANNULLATA (terminale, `is_abortito`). Il commento
  della tabella dice ancora «senza is_abortito»: stantio, la colonna c'è. Matrice
  `config.stati_doc_offerte_transizioni`, sette righe: BOZZA → EMESSA «emetti», BOZZA → ANNULLATA «annulla»,
  EMESSA → ACCETTATA «accetta», EMESSA → RIFIUTATA «rifiuta», ACCETTATA → ANNULLATA «annulla», tutte manuali;
  EMESSA → SUPERATA e SUPERATA → EMESSA di **processo** (`manuale = false`). Rifiuto e i due annulli hanno
  `requires_motivazione` nel `meta`: è l'unica matrice che lo usa. ⛔ La matrice **non ha** la colonna
  `azione_processo_codename`, e il nome è fuori serie (le altre sono `transizioni_stati_*`).
* **Guard di transizione** `trgfn_offerte_commerciali_guard_transizione`: ✅ **legge già la matrice**. Poi le
  condizioni dei passaggi, che restano: il rientro da SUPERATA solo senza una revisione figlia viva
  (`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA`); all'emissione listino congelabile e congelamento, indirizzi del
  cliente, righe; verso EMESSA e ACCETTATA i prezzi autorizzati (non sul rientro); verso ANNULLATA
  `fn_check_offerta_annullabile`; le date dei passaggi. Codice del rifiuto: `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.
* **Verbo di stato: non c'è.** Lo stato lo scrivono:
  * il **backend** con un `UPDATE` (`OfferteRepository.update_stato`, con `motivazione_rifiuto` nella stessa
    istruzione), da `emetti`, `registra_esito` (accetta / rifiuta) e `annulla`;
  * il trigger `trgfn_offerte_commerciali_revisione` (`_z90_`, AFTER INSERT): la revisione nuova porta il padre
    EMESSA → SUPERATA con un `UPDATE`;
  * il trigger `trgfn_offerte_commerciali_rientro_padre` (`_z90_`, AFTER UPDATE): l'annullo dell'ultima revisione
    viva riporta il padre SUPERATA → EMESSA con un `UPDATE`, e lo stato di ritorno è il letterale `'EMESSA'`.
  
  ⚠️ Con la porta tutti e tre si fermano: i due trigger girano come chi scrive (la revisione nasce da
  `fn_crea_revisione_offerta`, INVOKER), e la porta vuole il proprietario.
* **Gli stati di partenza in Python** (`offerte_service`): `_STATI_EDITABILI` per «Emetti», `_STATI_DA_EMESSA`
  per l'esito e la revisione, `_STATI_PUSHABILI` per il push, `_ESITI_AMMESSI_DA_EMESSA`, e `_STATI_TERMINALI`
  (nessuno la legge). Ripetono la matrice e i guard delle madri (revisione, push, ordine), che rifiutano già da
  sé. La motivazione obbligatoria del rifiuto e dell'annullo è solo in Python (`guard_non_empty_string`): il
  `requires_motivazione` della matrice lo legge la capability per disegnare il campo, nessuno lo fa rispettare.
* **Annullo: nessun verbo.** `POST /annulla/` passa da `update_stato`. Il guard rifiuta l'annullo con un
  contratto o un ordine vivo nato dall'offerta (`fn_check_offerta_annullabile`): è la metà «prima ciò che vieta»
  che hanno anche preventivo, ordine e commessa (`fn_check_*_annullabile`, D-3 di brief-db-annullo-documento-con-legami),
  **non** una divergenza. ⚠️ Correzione del §8.12 (riga D-4) e della guida §10, che la davano per tale. Quello che
  manca è l'altra metà: l'offerta non è fra i documenti di `fn_documento_legami` e il guard comune dell'annullo
  non è montato sulla testata. E l'annullo di una revisione **riapre** il padre (SUPERATA → EMESSA) in silenzio:
  vedi O-4.
* **Azione: nessuna** a catalogo per l'offerta. Ogni passaggio chiede il solo permesso sul documento.
* **Numero alla nascita.** `trgfn_offerte_commerciali_gen_codice` numera all'INSERT (OFC-*), ogni revisione col
  suo: come ordine e contratto (Z-4, Y-4).
* **Capability** `fn_available_actions_offerta`: dalla matrice, coi motivi; nessun filtro sull'azione; i motivi
  per destinazione legati ai codici `'EMESSA'`, `'ACCETTATA'`, `'ANNULLATA'`.
* **Gemello d'acquisto: nessuno.**
* **pgTAP:** 29 file scrivono lo stato dell'offerta con un `UPDATE` diretto; nessun builder dell'offerta;
  `dbops.fn_pgtap_porta_a_stato` non conosce la testata. Conteggio del 2026-10-26, per dimensionare il porting.

### 13.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| matrice | colonna `azione_processo_codename` su `config.stati_doc_offerte_transizioni` (FK alla chiave stabile), valori dal CSV secondo O-1; mirror con la colonna (⚠️ `nullValue`); il nome secondo O-5 |
| azione | secondo O-1 |
| verbo | NUOVO `vendite.fn_cambia_stato_offerta(p_offerta_id, p_stato, p_motivazione)`, gemello di quello del contratto: DEFINER col predicato del perimetro (`fn_scope_ef_whitelist_via_offerta`), `fn_doc_stato_id`, `fn_guard_passaggio`, la motivazione secondo O-3, `fn_doc_scrivi_stato` |
| processo | i due passaggi della revisione secondo O-2 |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.offerte_commerciali`; la fixture `fn_pgtap_porta_a_stato` conosce il verbo |
| annullo | NUOVO `vendite.fn_annulla_offerta`, secondo O-4; lo stato d'annullo dal vocabolario (`fn_stato_abortito_id`) |
| guard | resta com'è (legge già la matrice); il letterale del rientro esce con O-2 |
| capability | permesso ⇒ nascondi, come gli altri; emissione e annullo dal vocabolario (`emissione`, `is_abortito`) invece dei codici |
| fixture | i 29 `UPDATE` diretti portati al verbo o a `fn_pgtap_porta_a_stato`; nessun builder nuovo (né trappola d'ordine né regola ricopiata) |
| guida | §10, riga dell'offerta (con la correzione sull'annullo); la guida delle offerte rimanda al modello; il commento stantio di `config.stati_doc_offerte` |

**Richiesta al BE** (col percorso intero, a giro DB provato): `OfferteRepository.update_stato` si ritira; «Emetti»,
l'esito e l'annullo chiamano i verbi; il 403 dalla riga del passaggio (`PassaggioDocumento`); i cinque insiemi di
stati del service e i `_assert_stato_corrente` davanti alle madri si ritirano; la motivazione secondo O-3; la
finestra dei legami secondo O-4.

### 13.3 Domande per Tid

* **O-1. L'azione dell'offerta.** Proposta: azione **nuova** `emetti_offerta` («emette un'offerta o annulla
  un'offerta accettata») sulle righe BOZZA → EMESSA e ACCETTATA → ANNULLATA; accetta e rifiuta col solo
  permesso sul documento; BOZZA → ANNULLATA senza azione (M-4). È la guida §6 («l'emissione e l'annullo di un
  documento emesso; spedito, accettato, rifiutato chiedono solo il permesso sul documento»), gemella di
  `emetti_preventivo`. ⚠️ Nessun profilo la riceve dai seed: concederla è un dato, su dbdev lo fai tu.
  Alternativa: l'azione anche su accetta e rifiuta, che oggi impegnano il cliente (ACCETTATA apre il push) —
  sarebbe un'eccezione alla guida §6, quindi un cambio del modello.
* **O-2. I passaggi di processo della revisione.** Proposta: **un building block** DEFINER,
  `vendite.fn_offerta_proietta_stato_revisione(p_offerta_id)`, gemello delle proiezioni di preventivo e ordine:
  il padre EMESSA con una revisione viva → lo stato di superamento (`is_superato`); il padre superato senza
  revisioni vive → lo stato di emissione (vocabolario, non `'EMESSA'`); altrimenti niente. Scrive con la sola
  seconda metà del verbo, attraverso la porta. I due trigger `_z90_` restano come **chiamanti** (prendono la causa
  su ogni strada: l'INSERT di una revisione, l'annullo di una revisione) e perdono il loro `UPDATE`; la regola
  «nessun rientro con una figlia viva» resta nel guard. Alternativa: la chiamano i verbi
  (`fn_crea_revisione_offerta`, `fn_annulla_offerta`) e i trigger si ritirano; un INSERT di revisione fuori dal
  verbo lascerebbe però due revisioni vive.
* **O-3. La motivazione del rifiuto e dell'annullo.** Proposta: il verbo la riceve (`p_motivazione`) e la
  scrive in `motivazione_rifiuto` nella stessa transazione, prima dello stato; se la riga del passaggio ha
  `requires_motivazione`, senza motivazione rifiuta con un codice nuovo (`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`,
  `DATO_ERRATO`). La regola passa dalla matrice al verbo, e la copia Python si ritira. Alternativa: il backend
  scrive la motivazione con un `UPDATE` (il lock la ammette in BOZZA, EMESSA e ACCETTATA) e poi chiama il
  verbo; la regola resta in Python.
* **O-4. L'annullo e i legami.** Proposta: il verbo d'annullo `vendite.fn_annulla_offerta(p_offerta_id,
  p_motivazione, p_legami_confermati)` come gli altri (prima ciò che vieta: `fn_check_offerta_annullabile`; poi
  la conferma; poi il verbo di stato), e il **padre superato è un legame** dell'offerta che si annulla
  (`fn_documento_legami`, ramo `OFFERTA_COMMERCIALE`; guard comune dell'annullo montato sulla testata): chi annulla
  una revisione vede che la revisione precedente torna emessa, e conferma. È la Regola 6 («un annullo che riapre
  altro si conferma»); il rientro lo fa poi la proiezione di O-2, niente da ritirare. Alternativa: il rientro
  resta silenzioso e il verbo non chiede conferma — è una **revoca** della Regola 6 per l'offerta, da scrivere
  nella guida.
* **O-5. Il nome della matrice.** Proposta: **fuori da questo giro**, dichiarato come divergenza nella riga
  dell'offerta della guida §10. La mappa del modello (`fn_doc_stato_modello`) la trova per registrazione, e
  nessuna regola dipende dal nome; la rinomina tocca il seed, il mirror, due file del backend e sei pgTAP, per un
  guadagno di sola uniformità. Alternativa: rinominarla qui (`config.transizioni_stati_offerte`).
* **O-6. Il numero alla nascita.** Come Z-4 e Y-4. Proposta: **fuori da questo giro**, dichiarato come
  divergenza nella riga dell'offerta della guida §10.

D-N1 (§12, le azioni di riga) resta aperta e non entra in questo giro senza una tua decisione: le righe
dell'offerta (eccezioni, componenti, approvazione del prezzo) ne sarebbero il primo caso.

✅ **Decise da Tid il 2026-10-26**: O-1 … O-6 come da proposta, e il via allo sviluppo. D-N1 **non** entra in
questo giro.

### 13.4 Scritto (2026-10-26)

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261026-14-alter-stati-doc-offerte-transizioni-azione-processo` | colonna `azione_processo_codename` sulla matrice dell'offerta, FK al catalogo delle azioni |
| `-15-comment-stati-doc-offerte-vocabolario` | il commento stantio del vocabolario («cinque stati», «senza is_abortito») riscritto |
| CSV `azioni_processo` (id 43), `stati_doc_offerte_transizioni`, mirror `20260524-22` | `emetti_offerta` a catalogo; sulle righe BOZZA → EMESSA e ACCETTATA → ANNULLATA (O-1); mirror con la colonna e `nullValue: "NULL"` |
| `-16-create-fn-cambia-stato-offerta` | il verbo di stato, gemello di quello del contratto, con la motivazione (O-3): obbligatoria dove la riga ha `requires_motivazione`, scritta in `motivazione_rifiuto` prima dello stato; vuota o di soli spazi = assente |
| `-17-create-fn-offerta-proietta-stato-revisione` | la proiezione dei due passaggi di processo (O-2), DEFINER, con la scrittura comune; lo stato di ritorno dal vocabolario (`emissione`) |
| `-18`, `-19` | i due trigger `_z90_` della revisione restano come chiamanti della proiezione: via i loro `UPDATE`, il guard sull'arità e il letterale `'EMESSA'` |
| `-20` … `-23` | il ramo `OFFERTA_COMMERCIALE` nei quattro pezzi comuni dell'annullo con legami (O-4): `fn_documento_legami` (il padre superato che torna emesso, PROVENIENZA), `fn_documento_ritira_legami` (prima `fn_check_offerta_annullabile`, poi la conferma), `fn_doc_porta_ritiro_ammette`, `trgfn_doc_guard_annullo_con_legami` |
| `-24-create-trigger-guard-annullo-con-legami-offerte` | l'avviso dell'annullo montato sull'offerta (`_m10_`) |
| `-25-create-fn-annulla-offerta` | il verbo d'annullo `(id, motivazione, legami_confermati)`, come O-4 |
| `-26-create-trigger-stato-solo-dal-verbo-offerte` | la porta sull'offerta |
| `-27-update-fn-available-actions-offerta-permesso-del-passaggio` | permesso ⇒ nascondi; i motivi dell'emissione e dell'annullo legati al vocabolario (`emissione`, `is_abortito`) |
| `-28-update-fn-pgtap-porta-a-stato-offerta` | la fixture conosce il verbo dell'offerta, con una motivazione sua dove la riga la chiede |
| CSV errori | `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA` (nuovo, `DATO_ERRATO`, id 1401); `E_DOC_ANNULLO_CON_LEGAMI`: nota, frase e soluzione nominano la revisione precedente dell'offerta |
| doc | guida del modello §10 (riga dell'offerta, intro); guida delle offerte (§3.1, §4.1, §4.4 nuovo, §12); pagine manuali nuove dei tre oggetti nuovi; aggiornate quelle del trigger della revisione, della matrice, del vocabolario, della testata, di `fn_crea_revisione_offerta` e di `fn_documento_legami` |

**Una precisazione su O-2, dichiarata.** La proposta diceva «il padre EMESSA con una revisione viva → superato».
Scritto, la condizione è «**non superato**» con una revisione viva: il superamento si chiede anche da un altro stato
e lo rifiuta la matrice (`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`), come faceva l'`UPDATE` del vecchio trigger. Con «solo
da EMESSA» una revisione inserita su un padre in bozza (fuori da `fn_crea_revisione_offerta`, che già lo rifiuta)
sarebbe passata in silenzio. Provato (test 23 del pgTAP nuovo).

**Da sapere.** `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` resta nel guard di transizione, per chiunque scriva, ma
dall'applicazione non si raggiunge più: la proiezione non chiede il rientro con una revisione viva, e la scrittura
comune dall'applicazione la ferma la porta. Il legame dell'offerta ripete in anticipo la domanda della proiezione
(«questo annullo riaprirà il padre?» contro «il padre ha revisioni vive?»): due domande sulla stessa regola,
dichiarato nel changeSet `-20`. La motivazione scritta su un passaggio che non la chiede si scrive lo stesso (O-3
alla lettera: «la riceve e la scrive»); oggi il backend la manda solo per rifiuto e annullo.

### 13.5 Prova e regressione (2026-10-26)

Sullo scratch `zeroerp_ruoli` come `zeroerp_owner`: SQL estratto dei changeSet `-14` … `-28` e seed simulato
(azione, matrice, codice nuovo), nella transazione annullata di ogni file. L'SQL estratto passa intero; le
preCondition contate a parte tornano.

* **Nuovo** `vendite/test-offerta-al-modello-v1` (25): **25/25 da owner**. Il 25 (la porta) è verde anche da owner:
  l'`UPDATE` diretto non accende la GUC della scrittura comune.
* **Regressione, prima del porting:** 61 file che muovono lo stato dell'offerta o toccano i pezzi cambiati (legami,
  annullo, porta, passaggio, capability, fixture). 24 cambiavano, per due cause attese: la porta (l'`UPDATE` diretto
  dello stato, in fixture) e permesso ⇒ nascondi (senza `emetti_offerta` «Emetti» e «Annulla» dall'accettata non ci
  sono).
* **Porting dei 24** (tre agenti in parallelo, ogni file provato col file composto): l'`UPDATE` di stato diventa il
  verbo o `dbops.fn_pgtap_porta_a_stato`; dove il file prova lo stato e non il permesso, la fixture concede
  `emetti_offerta`, dichiarato. Attese cambiate, dichiarate in testa ai file:
  * `test-offerte-rientro-padre-revisione-annullata`: 4-6, il padre non rientra in silenzio, l'annullo della revisione
    passa da `fn_annulla_offerta` con la conferma (O-4), stesso esito; 7, il rientro chiesto a mano con una revisione
    viva lo rifiuta il verbo come passaggio di processo (prima un `throws_ok` sul solo P0001 di un `UPDATE`, che oggi
    sarebbe verde per la porta, cioè per la ragione sbagliata);
  * `test_offerte_commerciali_state_machine`: le transizioni dei test 2-10 si chiedono al verbo, stesso esito
    atteso, con la motivazione dove serve;
  * `test-doc-verbo-comune-e-porta-v1`: 9 e 10, l'offerta entra fra le testate con la porta (da 5 a 6 montaggi).
* **Regressione finale**, in sequenza, sui 61 file col giro 9: **60 identici al prima**, con tutte le asserzioni
  eseguite; il nuovo da rosso a 25/25. Restano gli stessi rossi di prima, uguali prima e dopo: da owner
  `test-contratto-al-modello-v1` 22, `test-ordine-al-modello-v1` 17, `test-doc-verbo-comune-e-porta-v1` 23 e 24,
  `test-annullo-documento-con-legami-v1` 30; già rossi o tronchi prima del giro
  `test-capability-annulla-aspetto-e-stato-leggibile-v1` (2, 4, 8), `test-fn-available-actions-ddt-reason-catch-all-v1`
  18, `test-ddt-righe-evase-dall-ordine-v1` 43, `test-esecutivi-ba-coppia-v1` 39, `test-vw-situazione-merce-ordine-v1`
  11, `test-guard-uscita-commessa-v1` (tronco a 4/18).
* Scratch verificato pulito dopo le corse (nessun oggetto nuovo, trigger della revisione ancora quello vivo).
* Fuori tema, segnalato da un agente e non toccato: `test_offerte_eccezioni_componenti` elenca 1..26 in testa con
  `plan(27)`.

La misura che conta (come app) arriva dalla corsa di Tid dopo l'apply.

### 13.6 Richiesta al team BE (elenco chiuso, dopo l'apply)

Percorso letto il 2026-10-26: `offerte_service`, `offerte_repository`, `views_offerte`, `offerte_documenti_views`,
`urls_offerte`, `legami_views`, i test Django e il frontend dell'annullo con legami.

1. **«Emetti»** (`OfferteService.emetti`): lo stato dal verbo `vendite.fn_cambia_stato_offerta(id, <stato
   d'emissione dal vocabolario>, NULL)`, nella stessa transazione del PDF.
2. **L'esito** (`registra_esito`, `registra_accettazione`, `registra_rifiuto`): dal verbo, con la motivazione per il
   rifiuto. La motivazione obbligatoria la dice il database (`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`, campo
   `motivazione_rifiuto`): si ritira `guard_non_empty_string` sul campo `motivazione` (rifiuto e annullo).
3. **L'annullo** (`POST /annulla/`): `vendite.fn_annulla_offerta(id, motivazione, legami_confermati)`; il corpo della
   richiesta porta `legami_confermati`, come contratto, ordine e preventivo. Nuova rotta
   `GET /offerte/<id>/legami/` da `legami_views.build_legami_view` (il lettore è `fn_documento_legami
   ('OFFERTA_COMMERCIALE', id)`), e `get_legami` nel service.
4. **`OfferteRepository.update_stato`** si ritira (la porta rifiuta l'`UPDATE`), con `_assert_stato_corrente` davanti
   ai passaggi e i cinque insiemi di stati del service (`_STATI_EDITABILI`, `_STATI_DA_EMESSA`, `_STATI_PUSHABILI`,
   `_ESITI_AMMESSI_DA_EMESSA`, `_STATI_TERMINALI`) dove ripetono la matrice o i guard delle madri (revisione, push,
   ordine), che rifiutano già da sé. Dove un insieme serve ad altro (per esempio la validazione dell'`esito` in
   ingresso), resta, dichiarato.
5. **Il 403 dalla riga del passaggio** (`PassaggioDocumento`) su «Emetti» e sull'annullo dell'accettata: chiedono
   `emetti_offerta`. Accetta, rifiuta e l'annullo della bozza restano al permesso sul documento.
6. **Codici nella policy**: `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA` (`DATO_ERRATO`, 400, campo `motivazione_rifiuto`),
   col ripiego in `error_messages_fallback.py`; le frasi nuove di `E_DOC_ANNULLO_CON_LEGAMI`.
7. **Frontend**: l'annullo dell'offerta passa dalla finestra comune dei legami
   (`_shared/annullo/DocumentoAnnulloLegamiDialog`, `legamiApi`), come gli altri documenti: chi annulla una revisione
   vede che la precedente torna emessa e conferma. «Emetti» e «Annulla» dall'accettata si nascondono a chi non ha
   l'azione (lo dice già la capability).
8. **Test Django** che scrivono lo stato dell'offerta con un `UPDATE` (`tests/db/test_genera_ordine_da_offerta_db.py`,
   riga ~80) o che passano da `update_stato` (`tests/services/test_offerte_service.py`): al verbo o alla capability;
   test nuovi sul DB per «Emetti» senza azione, rifiuto senza motivazione, annullo di una revisione con e senza
   conferma.
9. **Doc** `docs/it/backend/vendite/manual/api_offerte.md`: stati, permessi, motivazione, legami dell'annullo.

Da sapere: ⚠️ `emetti_offerta` non la riceve nessun profilo dai seed: senza, nessuno emette un'offerta né annulla
un'accettata. Concederla è un dato, su dbdev lo fa Tid. Il numero alla nascita (O-6) e il nome della matrice (O-5)
restano fuori, dichiarati nella guida §10.

### 13.7 Applicato e verde; il backend dopo l'apply (2026-10-26)

**Applicato e verde (Tid, 2026-10-26):** migrazione del giro 9 su dbdev e corsa pgTAP come app.

**Verifica del backend, letta dal team DB dopo l'apply** (il codice di `dev/backend-tid` com'è, nessun commit BE
dopo `0a08565be`). Le correzioni BE già fatte sull'offerta nei giri 6-8 — lo stato d'emissione dal vocabolario
(`stato_di_emissione`, V-2/B-4 del §8.11), l'id dello stato dal lettore `fn_doc_stato_id`
(`OfferteRepository.get_stato_id_by_codice`), l'annullo senza stato di partenza scritto in Python
(`annulla`, `expected_from=None`, H-R3) — sono giuste nel merito, ma arrivano tutte allo stesso punto,
`OfferteService._cambia_stato_manuale` → `OfferteRepository.update_stato`, cioè un `UPDATE` della colonna di stato.
**Dopo l'apply quell'`UPDATE` lo rifiuta la porta** (`E_DOC_STATO_SOLO_DAL_VERBO`). Da adesso, su dbdev:

| Strada | Codice BE | Esito oggi | Punto del §13.6 |
| --- | --- | --- | --- |
| «Emetti» (`POST /offerte/<id>/emetti/`, factory dei documenti) | `OfferteService.emetti` → `_cambia_stato_manuale` | rifiutato dalla porta, il PDF non nasce (la transazione si annulla) | 1, 5 (manca `emetti_passaggio`) |
| Esito (`POST /registra-esito/`, accetta e rifiuta) | `registra_esito` → `registra_accettazione` / `registra_rifiuto` | rifiutato dalla porta | 2 |
| Annullo (`POST /annulla/`) | `annulla` | rifiutato dalla porta; e senza `legami_confermati` l'annullo di una revisione non avrebbe comunque la conferma | 3 |
| Crea revisione, push a contratto, genera ordine | `crea_revisione`, `push_a_contratto` e il verbo dell'ordine | **funzionano**: lo stato del padre lo scrive la proiezione dentro il DB | — (resta `_assert_stato_corrente` davanti, punto 4) |

Cosa resta valido delle correzioni di prima, e cosa si ritira col §13.6:
* `stato_di_emissione` resta: dà il **codice** dello stato d'emissione da passare al verbo (punto 1);
* `get_stato_id_by_codice` si ritira: il verbo prende il codice, non l'id (punto 4, con `update_stato`);
* `annulla` senza stato di partenza resta come scelta, ma passa da `fn_annulla_offerta` con la motivazione e
  `legami_confermati` (punto 3); `guard_non_empty_string` si ritira (punto 2);
* `_cambia_stato_manuale` si riduce al verbo (o sparisce): la difesa applicativa sugli stati di partenza
  (`expected_from`) ripete la matrice (punto 4).

Fuori dal backend, sempre da sapere: il frontend chiama `annullaOfferta(id, { motivazione })`
(`vendite/offerte/api/offerteApi.js`) senza la finestra dei legami (punto 7); i test Django
`tests/services/test_offerte_service.py` (che passano da `update_stato`) e `tests/db/test_genera_ordine_da_offerta_db.py`
(un `UPDATE` di stato nella fixture, riga ~80) ora sono rossi o lo diventano sul DB reale (punto 8). Nessuno smoke
scrive lo stato dell'offerta (cercato in `backend/scripts/tests`).

⚠️ Dato su dbdev: `emetti_offerta` (con `emetti_contratto` ed `emetti_ordine`) a nessun profilo finché Tid non le
concede: anche col BE portato, senza il dato nessuno emette un'offerta.

Il §13.6 resta l'elenco chiuso del passaggio BE: nessun punto nuovo, la tabella sopra dice solo che cosa è rotto
**adesso**, nell'attesa (rotture BE accettate fino a fine cantiere).

✅ **Risolto dal passaggio BE del §13.8** (2026-10-26): le tre strade passano dai verbi.

### 13.8 Fatto dal team BE (2026-10-26): §13.6 punti 1-9

1. **«Emetti»**: `OfferteService.emetti` chiama `vendite.fn_cambia_stato_offerta(id, <stato di emissione dal
   vocabolario>, NULL)` (`OfferteRepository.cambia_stato`), nella transazione del PDF della factory documenti.
2. **L'esito**: `registra_accettazione` / `registra_rifiuto` dal verbo; la motivazione arriva com'è (solo la forma:
   un non-stringa è un 400 col campo, vuota = assente) e l'obbligo lo dice il DB
   (`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`). Ritirato `guard_non_empty_string` su rifiuto e annullo.
3. **L'annullo**: `OfferteService.annulla(id, motivazione, legami_confermati)` → `vendite.fn_annulla_offerta`
   (`OfferteRepository.annulla`); il corpo porta `legami_confermati` (coerenza col BB `legami_confermati`). Nuova
   rotta `GET /offerte/<id>/legami/` (`build_legami_view`, `ApiOffertaLegami`) e `OfferteService.get_legami`
   (prima la testata, poi `legami_del_documento('OFFERTA_COMMERCIALE', id)`); `DocumentoLegami` conosce l'offerta.
4. **Ritirati** `OfferteRepository.update_stato` e `get_stato_id_by_codice`, `_cambia_stato_manuale` (ora
   `_cambia_stato`, il solo verbo), i `_assert_stato_corrente` davanti a revisione e push (resta l'esistenza, 404),
   `_STATI_DA_EMESSA`, `_STATI_PUSHABILI`, `_STATI_TERMINALI`, e da `StatoOfferta` i codici di emissione, annullo e
   superamento. **Restano, dichiarati**: `_STATI_EDITABILI` con `_assert_stato_corrente` per la sola
   **eliminazione** (non è un passaggio della matrice e la tabella non ha un guard sul DELETE); `_ESITI` (ex
   `_ESITI_AMMESSI_DA_EMESSA`), la validazione del campo `esito` in ingresso, non lo stato di partenza.
5. **Il 403 dalla riga del passaggio**: `emetti_passaggio=TESTATA_OFFERTE` su «Emetti»;
   `post_passaggio = PassaggioDocumento(stato_del_modello="annullo")` su `/annulla/` (l'accettata chiede
   `emetti_offerta`, la bozza il livello); `post_passaggio(campo_stato="esito")` su `/registra-esito/`: oggi senza
   azione, legge comunque la riga, così un'azione aggiunta alla matrice vale senza codice. Presidio
   `test_passaggio_rotte`: le rotte dell'offerta entrano fra le attese, e con loro quelle del **contratto**, che
   del giro 8 erano sul modello ma mancavano dall'elenco.
6. **Codici**: policy rigenerata dal catalogo (git allineato al DB): `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`
   (`DATO_ERRATO`) e la nota nuova di `E_DOC_ANNULLO_CON_LEGAMI`; ripieghi senza segnaposto in
   `error_messages_fallback.py` (il nuovo e la frase dei legami che nomina la revisione precedente).
7. **Frontend**: `OffertaDrawer` passa l'annullo da `useForzaturaConfermata` e dalla finestra comune
   `DocumentoAnnulloLegamiDialog` (la motivazione resta nella chiamata da ripetere; alla domanda del DB il dialog
   dell'esito lascia il posto alla finestra). La finestra ha la forma dell'offerta: la provenienza «torna
   emessa» (la revisione precedente), con la sua spiegazione. «Emetti» e «Annulla» dall'accettata li nasconde già
   la capability. ⚠️ **Fuori elenco, dichiarato**: `OffertaEsitoDialog` leggeva l'obbligo della motivazione da un
   elenco di modalità scritto nel componente; ora dalla capability (`requires_motivazione` dell'azione), la stessa
   riga che il verbo fa rispettare.
8. **Test**: i test del service passano dai verbi (codici del DB al posto dei pre-check; motivazione al verbo;
   annullo con domanda e conferma; corpo malformato; `get_legami`); `test_genera_ordine_da_offerta_db` porta
   l'offerta ad ACCETTATA con `dbops.fn_pgtap_porta_a_stato` al posto dell'`UPDATE`; nuovo
   `vendite/tests/db/test_offerta_cambia_stato_db.py` (6: «Emetti», senza azione, secondo «Emetti», rifiuto senza e
   con motivazione, annullo della bozza senza azione e senza motivazione, annullo di una revisione con legami,
   domanda e conferma, padre di nuovo EMESSA). Spec FE della finestra: la forma dell'offerta.
9. **Doc**: `api_offerte.md` (verbi, permessi del passaggio, motivazione, rotta e conferma dei legami, codici,
   dipendenze DB); cataloghi BB backend e frontend.

**Da sapere, emerso nel giro.**
* ⚠️ **La revisione precedente non è un nodo del lineage** (nessun arco offerta → offerta): nella finestra il
  legame esce col solo tipo («Offerta commerciale · la revisione precedente torna emessa»), senza codice e senza
  link. È la regola già scritta per ogni legame che il lineage non vede (il nome lo dà il lineage, decisione di
  Tid); se il codice serve a video, è una richiesta al DB (un arco di revisione nel lineage), non una copia BE.
* ✅ **`DocumentoModelloRepository.stato_id` ritirato** (ok di Tid, 2026-10-26): l'offerta era l'ultima a usarlo
  (`get_stato_id_by_codice`); via anche il suo test in `test_permesso_passaggio_db` (7) e la voce del catalogo.

**Provato:** suite completa sul DB reale (`ZEROERP_TEST_DB_E2E=1`), **6985 test verdi** (1 saltato, 1 fallimento
atteso, già noti); vitest completo (975 verdi, 143 file); ruff, eslint, oxlint e gli script `check-*` del frontend
puliti; mypy col cricchetto a 0 rilievi. Lo smoke non è stato lanciato (nessuno smoke tocca gli stati
dell'offerta). ⚠️ Senza `emetti_offerta` concessa al profilo nessuno emette un'offerta né annulla un'accettata:
per il collaudo a video serve il dato su dbdev.

**Revisione critica del passaggio BE (2026-10-26, decisioni di Tid).** Tre punti emersi rileggendo il diff, risolti
prima del commit:
* **Un solo 404.** «Emetti» e l'esito lasciavano l'esistenza al verbo (`E_OFFERTA_NON_TROVATA`), annullo,
  revisione, push e legami la leggevano prima (`E_VENDITE_NOT_FOUND`): due codici per la stessa offerta che non c'è.
  Ora `_cambia_stato` legge la testata come gli altri e come il cambio stato del contratto; il verbo la ricontrolla
  nel perimetro, come difesa del DB.
* **Il campo di `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`.** Il verbo nomina la colonna (`motivazione_rifiuto`, canale
  `COLUMN`), la richiesta porta `motivazione`: `error.fields` prometteva un input che non esiste. Lo traduce
  `OfferteService._db_errors`, per quel codice soltanto (un `context={"field": …}` avrebbe acceso il campo su ogni
  rifiuto del blocco). Prima occorrenza di una traduzione colonna → campo della richiesta: resta nel service.
* **La motivazione dell'accettazione.** Il dialog la offriva facoltativa e il backend la scartava in silenzio. Ora
  `registra_esito` con `ACCETTATA` e una motivazione non vuota è un 400 `E_VENDITE_VALIDATION` col campo
  `motivazione`; il dialog mostra il campo solo dove la riga del passaggio lo chiede (`requires_motivazione`), e
  la chiave `field_motivazione_optional_placeholder` è ritirata. Letterali di stato del drawer e del dialog su
  `STATO_OFFERTA`.

### 13.9 Dopo il giro BE: la revisione precedente nella finestra, e l'asimmetria col preventivo (2026-10-26)

**Richiesta al team DB (priorità bassa, ok di Tid 2026-10-26).** Nella finestra di conferma dell'annullo di una
revisione d'offerta il legame (la revisione precedente che torna emessa) esce **senza numero e senza link**:
«Offerta commerciale · la revisione precedente torna emessa». Il nome dei documenti collegati la finestra lo prende
dal lineage (`legami_del_documento` → `get_documento_passaggi`, decisione di Tid: il nome lo dà il lineage, il
lettore dei legami non porta etichette), e il lineage non ha un arco offerta → offerta: la revisione padre non è
fra i nodi «indietro» della revisione. Si chiede che il codice della revisione precedente arrivi alla finestra
dalla sede dei nomi, senza una seconda fonte nel backend. La strada la sceglie il team DB, sulla struttura del
lineage: per esempio un arco di revisione in `vendite.fn_documento_lineage_archi` (che allora comparirebbe anche nel
pannello «Passaggi» dell'offerta, dove oggi le revisioni stanno in un tab a parte: da valutare se è voluto). Ricaduta
BE/FE attesa: nessuna, se il nome arriva dal lineage col tipo `OFFERTA_COMMERCIALE` (è già fra le origini apribili
di `_ORIGINI_DOCUMENTO`, e la finestra mostra numero e link da sé).

**L'asimmetria col preventivo: già decisa, non è una domanda aperta.** Nel giro è emerso che preventivo e offerta
dicono in due modi «una revisione sostituisce la precedente»: l'offerta nello **stato** del padre (SUPERATA, e il
rientro a EMESSA all'annullo dell'ultima revisione viva, che per questo si conferma), il preventivo **calcolandolo**
(`vw_preventivi.is_attiva`; la rev. precedente resta EMESSO, e annullando la bozza di revisione torna da sola
quella valida: nessun legame da confermare). È una scelta di Tid del **2026-07-16**
([brief-db-preventivi-revisione-attiva-dashboard](../work-done/brief-db-preventivi-revisione-attiva-dashboard.md),
Opzione B scartata di proposito): «l'asimmetria con le offerte è corretta: l'offerta è un documento a sé per
revisione, il preventivo versiona lo stesso `numero`»; razionale in `guide/gestione-preventivi.md` §4.3. Riaprirla
sarebbe una **revoca** di quella decisione, e nessuno la propone. ⚠️ Resta un buco di scrittura, non di modello: la
guida del modello (`guide/modello-documento-di-vendita.md`) non nomina la differenza, e chi legge solo lei la
ritrova come divergenza. Proposta per il team DB, quando tocca la guida: una riga che la dichiari decisa, col
rimando alla guida dei preventivi.

**Richiesta al team DB (priorità bassa, dalla revisione critica del 2026-10-26).** `vendite.fn_cambia_stato_offerta`
scrive `motivazione_rifiuto` su **qualunque** passaggio che la riceve, anche su `EMESSA -> ACCETTATA`, dove la riga
non la chiede: il modello ammette un'offerta accettata con una «motivazione del rifiuto». Il backend oggi non la
passa (e la rifiuta in ingresso), ma la regola sta in Python e il verbo resta permissivo. Da decidere sul modello:
o la riga del passaggio dichiara anche dove la motivazione è **ammessa** (oggi c'è solo `requires_motivazione`), e
il verbo rifiuta il resto, o la colonna si scrive solo dove la riga la chiede. Ricaduta BE attesa: togliere il
controllo di `registra_esito` quando il verbo lo fa.

## 14. Giro 10: la commessa al modello — ricognizione e piano (2026-10-26)

✅ **Via di Tid il 2026-10-26** («procedi con ricognizione»): la ricognizione della commessa, il giro dopo l'offerta
(W-1). Lo sviluppo parte con le risposte alle domande del §14.3.

### 14.1 Com'è oggi (dbdev, CSV e `backend/`, 2026-10-26)

* **Vocabolario** `vendite.stati_commessa` (schema `vendite`, non `config`): BOZZA (`iniziale`), APERTA,
  IN_ESECUZIONE, PRONTA_FATTURAZIONE (`emittibile`: la pescano le attività fatturabili), CHIUSA (`chiude_commessa`),
  ANNULLATA (`is_abortito`, `chiude_commessa`). Ha `fase`, `modificabile`, `emittibile`, `chiude_commessa`; **non** ha
  `emissione`: la commessa non si stampa e nasce dalla push dei documenti a monte (guida §7, §10).
* **Matrice** `vendite.transizioni_stati_commessa`, dodici righe; ⛔ **non ha** `azione_processo_codename`. Manuali:
  «rendi pronta» (BOZZA, APERTA, IN_ESECUZIONE → PRONTA_FATTURAZIONE), «riapri» (PRONTA_FATTURAZIONE →
  IN_ESECUZIONE), «chiudi» (PRONTA_FATTURAZIONE, IN_ESECUZIONE → CHIUSA), «annulla» (da BOZZA, APERTA, IN_ESECUZIONE,
  PRONTA_FATTURAZIONE). Di processo (`manuale = false`): BOZZA → APERTA e APERTA → IN_ESECUZIONE. La mappa del modello
  la conosce già (`fn_doc_stato_modello`).
* **Guard di transizione** `trgfn_commesse_guard_transizione`: ✅ **legge già la matrice**
  (`E_COMMESSA_STATO_TRANSIZIONE_INVALIDA`); poi le condizioni per destinazione, dalle loro `fn_check_*`
  (`fn_check_commessa_pronta_fatturazione`, `fn_check_commessa_chiudibile`, `fn_check_commessa_annullabile`), legate ai
  codici `'PRONTA_FATTURAZIONE'`, `'CHIUSA'`, `'ANNULLATA'`. Restano.
* **Verbo di stato** `vendite.fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato, p_user)`: c'è, ma è **il verbo di
  prima del modello**: INVOKER, senza il predicato del perimetro, senza la prima riga comune (né azione, né «passaggio
  di processo», né lo stato che ha già: `E_DOC_GIA_NELLO_STATO` non c'è), scrive con un `UPDATE` suo, e ha il
  parametro `p_user` che gli altri verbi hanno perso (il preventivo l'ha perso nel giro 6, `20261025-43`). È l'unico
  scrittore della colonna (letto il 2026-10-26 su tutte le funzioni); lo chiamano:
  * il backend (`CommesseRepository.cambia_stato_commessa`, dal `POST .../commesse/<id>/stato/`);
  * `vendite.fn_annulla_commessa` (DEFINER, conferma i legami: ✅ già sul modello dell'annullo), con il letterale
    `'ANNULLATA'`;
  * `vendite.fn_rendi_commessa_emittibile`, **il ponte della push**: dopo un invio riuscito approva le righe di quel
    giro e porta la testata a PRONTA_FATTURAZIONE, **passando dalle righe «rendi pronta», che sono manuali**. Un
    passaggio che l'operatore chiede e che il sistema fa come conseguenza dell'invio, sulla stessa riga della matrice.
* ⚠️ **Due passaggi di processo senza chi li scrive.** BOZZA → APERTA e APERTA → IN_ESECUZIONE sono in matrice, ma
  nessuna funzione e nessun punto del backend li chiede (letto il 2026-10-26 sul codice; la guida delle commesse li
  elenca come «automatiche, push/ponte emittibilità»). Fatto datato, non un motivo: su dbdev nessuna commessa è in
  APERTA o IN_ESECUZIONE.
* **Azione**: `cambia_stato_commessa` («Cambia stato commessa (chiudi/riapri/annulla)») a catalogo, chiesta dal solo
  backend (`post_permission` della view dello stato) su **ogni** passaggio, compreso l'annullo della bozza. Il DB non la
  conosce.
* **Copie BE delle regole DB** (`commesse_service.cambia_stato_commessa`): la «difesa applicativa» che ammette solo lo
  stato di una `available_action` abilitata ripete due regole del DB: il passaggio di processo non si chiede a mano (la
  prima riga comune, `E_DOC_PASSAGGIO_DI_PROCESSO`, quando il verbo ce l'avrà) e le condizioni delle `fn_check_*` (il
  guard). Nasceva perché il verbo non rifiuta i passaggi di processo.
* **Capability** `fn_available_actions_commessa`: dalla matrice coi motivi; nessun filtro sull'azione; motivi legati ai
  codici di destinazione.
* **Numero**: la commessa ha il suo codice alla nascita; non si emette, quindi la regola §7 non la riguarda.
* **Gemello d'acquisto**: nessuno.
* **pgTAP** (conteggio del 2026-10-26, per dimensionare il porting): 9 file scrivono lo stato con un `UPDATE` diretto,
  20 chiamano `fn_cambia_stato_commessa`, 53 usano il builder `dbops.fn_pgtap_crea_commessa`, che porta lo stato con
  `dbops.fn_pgtap_porta_a_stato` (oggi un `UPDATE`, con la porta il verbo).

### 14.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| matrice | colonna `azione_processo_codename` su `vendite.transizioni_stati_commessa`, valori dal CSV secondo C-1; mirror con la colonna (⚠️ `nullValue`) |
| verbo | `vendite.fn_cambia_stato_commessa` portato al verbo comune, gemello di quello del contratto: DEFINER col predicato del perimetro (`fn_scope_ef_whitelist_via_commessa`), `fn_doc_stato_id`, `fn_guard_passaggio`, `fn_doc_scrivi_stato`; la firma secondo C-4 |
| ponte della push | secondo C-2 |
| passaggi senza causa | secondo C-3 |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.commesse`; `fn_pgtap_porta_a_stato` conosce il verbo |
| annullo | `fn_annulla_commessa` chiama il verbo nuovo; lo stato d'annullo dal vocabolario (`fn_stato_abortito_id`) |
| guard | resta com'è (legge già la matrice) |
| capability | permesso ⇒ nascondi; il motivo dell'annullo legato a `is_abortito`, quello di PRONTA_FATTURAZIONE a `emittibile`; CHIUSA resta sul codice (`chiude_commessa` vale anche per ANNULLATA) |
| fixture | i 9 `UPDATE` diretti al verbo o alla fixture; i 20 chiamanti del verbo secondo C-4; nessun builder nuovo |
| guida | §10 riga della commessa; la guida delle commesse (macchina di transizioni) rimanda al modello |

**Richiesta al BE** (col percorso intero, a giro DB provato): il 403 dalla riga del passaggio (`PassaggioDocumento`)
al posto di `post_permission = "cambia_stato_commessa"` su ogni passaggio; la «difesa applicativa» si ritira (la dice
il verbo); il repository segue la firma (C-4); la guida delle commesse e `api_commessa_stato.md`.

### 14.3 Domande per Tid

* **C-1. L'azione della commessa.** La guida §6 vuole un'azione sola, sui passaggi pesanti. La commessa non si emette:
  i suoi passaggi pesanti sono quelli che la mandano in fatturazione o la chiudono. Proposta: **riusare**
  `cambia_stato_commessa` (c'è già, i profili che oggi cambiano lo stato la hanno) sulle righe «rendi pronta»,
  «riapri», «chiudi» e sull'annullo di una commessa non in bozza; l'annullo della bozza senza azione (M-4, come gli
  altri documenti). Cambio visibile: oggi l'annullo della bozza chiede l'azione (dal backend), domani no.
  Alternativa: un'azione nuova (`emetti_commessa`?) per simmetria di nome coi gemelli; costa un dato da concedere a
  tutti i profili che oggi lavorano.
* **C-2. Il ponte della push.** La push porta la commessa a PRONTA_FATTURAZIONE come conseguenza di un invio
  riuscito, sulle stesse righe che l'operatore chiede con «rendi pronta». Proposta: `fn_rendi_commessa_emittibile`
  scrive lo stato con la **sola seconda metà** del verbo (`fn_doc_scrivi_stato`), DEFINER, come le proiezioni di
  preventivo, ordine e offerta: il permesso è quello della push (`run_commesse_push`, `push_commessa_preventivi`), non
  quello del passaggio manuale; la matrice e le condizioni le giudica il guard come oggi. Alternativa: il ponte passa
  dal verbo intero, e chi lancia la push deve avere anche l'azione di C-1.
* **C-3. I due passaggi di processo senza causa** (BOZZA → APERTA, APERTA → IN_ESECUZIONE). Proposta: **fuori da questo
  giro**, dichiarati come divergenza nella riga della commessa della guida §10 («passaggi di processo che nessuno
  scrive»): il verbo li rifiuterà comunque se chiesti a mano. Se APERTA e IN_ESECUZIONE servono ancora, e a chi, è una
  domanda sul vocabolario della commessa, non sul modello del cambio di stato. Alternativa: ritirarli qui (righe della
  matrice spente), con gli stati che restano raggiungibili solo da «riapri».
* **C-4. La firma del verbo.** Proposta: `fn_cambia_stato_commessa(p_commessa_id, p_stato)` **senza `p_user`**, come
  il preventivo nel giro 6: chi scrive lo dice l'audit dalla sessione. Cambio di firma (DROP + CREATE): si portano i
  chiamanti DB (annullo, ponte), il repository BE e i 20 pgTAP. Alternativa: tenere `p_user` (ignorato o usato per
  `user_update`), firma invariata.

D-N1 (le azioni di riga) resta fuori senza una tua decisione: le righe di commessa (approva, annulla attività) ne
sarebbero un caso.

✅ **Decise da Tid il 2026-10-26: C-1, C-2 e C-4 come da proposta; C-3 come sotto; via allo sviluppo.**

**C-3, decisa (Tid, 2026-10-26):** lo stato **IN_ESECUZIONE si ritira** («lavorazione in corso» è dello stato del
processo, non del documento: tema a parte, sotto). **«Riapri» porta ad APERTA**, che diventa «riaperta dopo essere
stata pronta»: da lì «rendi pronta», «chiudi» (oggi partiva da IN_ESECUZIONE) e «annulla» con l'azione. Il passaggio
di processo BOZZA → APERTA, che nessuno scrive, si spegne. Nessuna decisione precedente sul significato dei due stati
(sono del primo seed, giugno 2026; «riapri» del 2026-06-16, `13f7d34cf`): non è una revoca.

**C-3, l'idea di Tid (2026-10-26).** IN_ESECUZIONE dovrebbe dire «un processo sta lavorando la commessa»: mentre un
processo la lavora (da bozza ad aperta, da aperta a pronta…), la commessa passa in esecuzione, così si vede che il
lavoro è in corso; oppure uno stato a parte. Lettura del team DB, da decidere:
* «lavorazione in corso» è lo stato **del processo**, non del documento, e una sede c'è già per la push:
  `vendite.commesse_push_log`, una riga per giro in IN_ESECUZIONE finché il giro non chiude (anche quando muore a
  metà). Oggi però è per giro, non per commessa: il giro sa le sue commesse solo dentro `risultato.perimetro`;
* come stato del documento avrebbe tre problemi di forma: il processo lavora in una transazione, e gli altri vedono
  lo stato «in esecuzione» solo se il processo lo committa prima di lavorare; se il processo muore, la commessa resta
  in esecuzione e qualcuno deve riportarla indietro; e lo stato di prima (bozza, aperta) va ricordato per tornarci;
* proposta: la commessa **mostra** «lavorazione in corso» leggendola dal processo (una capability che guarda il giro
  aperto che la tocca), e il vocabolario dice cosa la commessa **è**. È un tema suo (legame giro ↔ commessa, e cosa
  vogliono dire APERTA e IN_ESECUZIONE), fuori da questo giro.

### 14.4 Scritto (2026-10-26)

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261026-29-alter-transizioni-stati-commessa-azione-processo` | colonna `azione_processo_codename` sulla matrice della commessa, FK al catalogo delle azioni |
| CSV `transizioni_stati_commessa`, mirror `20260607-05` | C-1: `cambia_stato_commessa` sulle righe 2, 5 («rendi pronta»), 6, 11 (annullo non in bozza), 10 («chiudi»); C-3: spente le righe 1 (BOZZA → APERTA) e 4, 7, 8, 9, 12 (IN_ESECUZIONE); nuove la 13 («riapri», PRONTA_FATTURAZIONE → APERTA) e la 14 («chiudi», APERTA → CHIUSA); mirror con la colonna e `nullValue: "NULL"` |
| CSV `stati_commessa` | IN_ESECUZIONE `attivo = false` (C-3) |
| CSV `azioni_processo` (id 30) | la descrizione di `cambia_stato_commessa` dice i passaggi nuovi |
| `-30-replace-fn-cambia-stato-commessa-verbo-comune` | il verbo sul verbo comune, DEFINER col predicato del perimetro, firma `(id, stato)` senza `p_user` (C-4): DROP + CREATE |
| `-31-create-fn-commessa-proietta-stato-emittibile` | la proiezione del passaggio della push allo stato emittibile (C-2), DEFINER, con la scrittura comune; lo stato dal vocabolario (`emittibile`) |
| `-32-update-fn-rendi-commessa-emittibile-proiezione` | il ponte della push chiama la proiezione (prima il verbo col letterale `'PRONTA_FATTURAZIONE'`) |
| `-33-update-fn-annulla-commessa-verbo-comune` | l'annullo chiama il verbo nella firma nuova, lo stato d'annullo dal vocabolario |
| `-34-create-trigger-stato-solo-dal-verbo-commesse` | la porta sulla commessa |
| `-35-update-fn-available-actions-commessa-permesso-del-passaggio` | permesso ⇒ nascondi; i motivi legati a `emittibile` e `is_abortito`; CHIUSA resta sul codice |
| `-36-update-fn-pgtap-porta-a-stato-commessa` | la fixture conosce il verbo della commessa |
| doc | guida del modello §10 (riga della commessa, intro); guida delle commesse (stati, passaggi); pagine manuali del verbo (riscritta), della matrice, del vocabolario, del ponte; nuova quella della proiezione |

⚠️ **Su dbdev, PRIMA del migrate, un passo a mano (Tid).** I CSV si caricano in ordine di nome: il mirror del
vocabolario (`20260226-07`) gira prima di quello della matrice (`20260607-05`). Spegnere IN_ESECUZIONE mentre le
righe della matrice che lo nominano sono ancora attive lo rifiuta il guard ATTIVO del vocabolario
(`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, provato sullo scratch il 2026-10-26), e il migrate si ferma su un changeSet di
febbraio. La correzione non può stare in un changeSet nuovo (§11.2, e girerebbe comunque dopo il mirror di
febbraio): è un dato, e si fa prima del migrate:

```sql
UPDATE vendite.transizioni_stati_commessa SET attivo = false WHERE id IN (4, 7, 8, 9, 12);
```

Poi il migrate porta la matrice al CSV (le stesse righe spente, più le altre). In CI non serve: il database nasce da
zero e il vocabolario si carica con un `INSERT`, che il guard non guarda. Nessuna commessa su dbdev è in
IN_ESECUZIONE (letto il 2026-10-26), altrimenti lo stesso guard avrebbe chiesto anche di spostarle.

### 14.5 Prova e regressione (2026-10-26)

Sullo scratch `zeroerp_ruoli` (col giro 9) come `zeroerp_owner`: SQL estratto dei changeSet `-29` … `-36` e seed
simulato **nell'ordine di dbdev**, col passo a mano del §14.4 prima del mirror del vocabolario, nella transazione
annullata di ogni file. Senza il passo il seed si ferma su `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (provato).

* **Nuovo** `vendite/test-commessa-al-modello-v1` (20): **20/20 da owner**.
* **Regressione, prima del porting:** 93 file che toccano lo stato, la matrice, il vocabolario, il builder, la
  capability, l'annullo o il ponte della commessa (più i presidi del modello). 21 cambiavano, per tre cause attese:
  la porta (l'`UPDATE` diretto in fixture), C-1 (l'azione su «rendi pronta» e sull'annullo fuori dalla bozza, in
  fixture che provano altro), C-3 (stati e righe della matrice contati; una commessa APERTA costruita senza righe,
  che ora si raggiunge solo da «riapri»).
* **Porting dei 21** (tre agenti in parallelo, ogni file provato col file composto). Attese cambiate, dichiarate in
  testa ai file:
  * `test-doc-verbo-comune-e-porta-v1` 9 e 10: la commessa entra fra le testate con la porta (7 montaggi);
  * `test-commesse-stati-commessa-v1` 4: l'elenco degli stati attivi, IN_ESECUZIONE ritirato;
  * `test-commesse-transizioni-stati-v1` 5: 14 righe, 8 attive;
  * `test-guard-uscita-commessa-v1` 3: l'uscita dal vicolo cieco è APERTA → CHIUSA;
  * `test-annullo-commessa-rettifica-v1` 2 e `test-annullo-commessa-v1` 19: stesso esito, la strada è il verbo
    (con l'`UPDATE` diretto la porta parlava prima del motivo che il test vuole vedere).
* **Regressione finale**, in sequenza, sui 93 file col giro 10: **92 identici al prima**, con tutte le asserzioni
  eseguite fin dove arrivavano prima; il nuovo da rosso a 20/20. Restano i rossi e i tronchi di prima, uguali.
* ⚠️ **Debito dichiarato, non di questo giro.** Diversi file della commessa sono **tronchi già prima del giro**
  («Parametro non valido: p_billing_account_id obbligatorio», «valore nullo in billing_account_id»): fra gli altri
  `test-commesse-stati-commessa-v1`, `test-commesse-transizioni-stati-v1`, `test-guard-uscita-commessa-v1`,
  `test-fn-available-actions-commessa-v1`, `test-attivita-fatturabili`, `test-commesse-schema-v1`. Le parti che
  oggi non si raggiungono non sono state portate: in `test-guard-uscita-commessa-v1` i test 10, 11 e 14a passano
  ancora da IN_ESECUZIONE; in `test-commesse-stati-commessa-v1` due chiamate al verbo chiederanno l'azione. Chi
  ripara il troncamento le porta.
* Scratch verificato pulito dopo le corse.

La misura che conta (come app) arriva dalla corsa di Tid dopo l'apply.

**Dopo l'apply e la corsa di Tid (2026-10-26).** Due file, tronchi sullo scratch ma completi su dbdev, si fermavano
sulle chiamate al verbo oltre il punto in cui lo scratch li tronca: `test-commesse-stati-commessa-v1` («rendi
pronta» e «chiudi» senza l'azione) e `test-commesse-transizioni-stati-v1` (11 e 12). Portati: l'azione
`cambia_stato_commessa` all'utente del contesto prima dei passaggi. Nel secondo anche un verde per la ragione
sbagliata: il test 8 («→ PRONTA senza righe approvate rifiutata», un `throws_ok` sul solo P0001) sarebbe scattato
per il permesso; con l'azione concessa prima, rifiuta per la regola delle righe. Cercati nello stesso giro gli
altri file con la stessa trappola dietro un rosso preesistente: portati `test-commessa-pronta-fatturazione-v1` (6 e
7 dal verbo; il 7 asserisce la frase di `E_COMMESSA_NESSUNA_RIGA_APPROVATA`, non più il solo P0001) e
`test-trigger-af-commessa-aware-v1` (la commessa a pronta dalla fixture). Non provabili sullo scratch (tronchi
prima): la misura è la corsa di Tid. ⚠️ Resta `test-guard-uscita-commessa-v1`: gli scenari B, C e D costruiscono
una commessa in IN_ESECUZIONE (BOZZA → APERTA → IN_ESECUZIONE), che non esiste più; vanno riscritti sul modello
nuovo (la commessa riaperta, APERTA) da chi ripara il suo troncamento, con i casi del vicolo cieco ripensati.

**La guard d'uscita riscritta (2026-10-26).** `test-guard-uscita-commessa-v1` costruiva gli scenari B, C, D in
IN_ESECUZIONE; ora partono dalla commessa riaperta (APERTA, da PRONTA con «riapri»): [B] il vicolo cieco è la
commessa riaperta e tutta emessa (la riga va a PRONTA, l'emissione vera la marca EMESSA, poi «riapri»), [C] riaperta
con una riga emessa e una da emettere, [D] riaperta senza righe emesse. Attese invariate.

**Applicato e verde (Tid, 2026-10-26):** passo a mano, migrazione del giro 10 (con `20261019-13` e `20261026-37`) e
corsa pgTAP come app.

**Fuori tema, emerso ricostruendo lo scratch (Tid, 2026-10-26).** `ci-local.sh --fresh` si ferma su
`00_schema/vendite/20261020-32` (brief-db-grammatica-unica-documenti, G-5): toglie `fk_registri_fatturazione_famiglia`
senza `IF EXISTS`, ma da zero quella FK nasce solo in `90_end/20260830-16`, dopo. E la rimette subito, mentre da zero
deve restare spenta durante `80_data` (i seed dei registri girano prima di quello delle famiglie). Il `-32` è
committato e applicato: non si tocca. Due passi suoi: `20261019-13` crea la FK se manca (prima del `-32`; un buco
di una data passata, fuori regola e dichiarato: il master autogenerato in modalità stretta non ammette un suffisso
come «-31a», e il 20-10 non ha numeri liberi prima del 32); `20261026-37` la toglie se `20260830-16` non è ancora
registrato, cioè da zero, e la rimette `90_end`. Su dbdev girano tutti e due a vuoto (FK presente, `20260830-16`
eseguito: letto il 2026-10-26). Provato sullo scratch fermo prima del `-32`, in transazione: FK presente dopo il
`-13`, il `-32` passa, assente dopo il `-37`.

✅ **Applicato e verde (Tid, 2026-10-26/27).** Su dbdev `20261019-13` e `20261026-37` sono registrati (a vuoto); lo
scratch `zeroerp_ruoli` si è ricostruito da zero fino in fondo (i 37 changeSet del 2026-10-26 registrati, il
vocabolario degli stati seminato: letto il 2026-10-27); corsa pgTAP verde, compresa la guard d'uscita riscritta.

### 14.6 Richiesta al team BE (elenco chiuso, dopo l'apply)

Percorso letto il 2026-10-26: `commesse_service.cambia_stato_commessa`, `CommesseRepository.cambia_stato_commessa`,
la view dello stato (`views.py`, `post_permission = "cambia_stato_commessa"`), il ponte della push
(`_rendi_commessa_emittibile`), i test Django, il frontend.

1. **La firma del verbo** (C-4): `CommesseRepository.cambia_stato_commessa` chiama
   `vendite.fn_cambia_stato_commessa(p_commessa_id, p_stato)`, senza `p_user` (oggi `p_nuovo_stato =>` e
   `p_user =>`: dopo l'apply la funzione con quei nomi non c'è più, e il cambio di stato della commessa si rompe).
2. **Il 403 dalla riga del passaggio** (`PassaggioDocumento`) al posto di `post_permission = "cambia_stato_commessa"`
   su ogni passaggio: «rendi pronta», «riapri», «chiudi» e l'annullo di una commessa non in bozza chiedono
   l'azione; **l'annullo della bozza no** (C-1, cambio visibile).
3. **La «difesa applicativa»** di `cambia_stato_commessa` (lo stato ammesso solo se è una `available_action`
   abilitata) si ritira: ripeteva due regole del DB, che ora le dice il verbo (il passaggio di processo chiesto a
   mano, `E_DOC_PASSAGGIO_DI_PROCESSO`) e il guard (le condizioni). Resta la lettura della capability per i
   `404`, se serve.
4. **Il ponte della push** (`_rendi_commessa_emittibile` → `fn_rendi_commessa_emittibile`): nessuna modifica, firma
   invariata; da sapere che il passaggio a pronta non chiede più l'azione del passaggio manuale (C-2).
5. **IN_ESECUZIONE ritirato** (C-3): l'etichetta (`stato_in_esecuzione` in `locales/it.json`) e il colore
   (`core/utils/severity.js`) della commessa restano senza uno stato che li usi: si tolgono, o restano dichiarati
   per lo storico. «Riapri» porta ad APERTA: la capability lo dice già (`target_state`).
6. **Test Django** che chiamano il verbo con `p_user`, usano IN_ESECUZIONE o si aspettano il 403 sull'annullo della
   bozza (`tests/api/test_commesse_api.py`, `tests/services/test_commesse_service.py`): alla firma e alla matrice
   nuove.
7. **Doc** `api_commessa_stato.md`: i passaggi, i permessi per passaggio, la firma.

Da sapere: nessun codice d'errore nuovo. `cambia_stato_commessa` la ha già un profilo su dbdev (letto il
2026-10-26): chi oggi cambia lo stato continua a farlo.

### 14.7 Fatto dal team BE (2026-10-27): §14.6 punti 1-7

1. **La firma del verbo** (C-4): `CommesseRepository.cambia_stato_commessa(commessa_id, nuovo_stato)` chiama
   `vendite.fn_cambia_stato_commessa(p_commessa_id => …, p_stato => …)`, senza `p_user`; il service e la view non
   portano più l'utente.
2. **Il 403 dalla riga del passaggio**: `ApiCommessaStato.post_passaggio = PassaggioDocumento(testata=TESTATA_COMMESSE,
   documento_kwarg="commessa_id", campo_stato="nuovo_stato")` al posto di `post_permission = "cambia_stato_commessa"`.
   L'annullo della bozza ricade sul livello sul documento (C-1, cambio visibile). Presidio
   `test_passaggio_rotte`: la rotta `commesse/<int:commessa_id>/stato/` entra fra le attese.
3. **La «difesa applicativa» ritirata**: `cambia_stato_commessa` non legge più la capability. L'esistenza la dice il
   lettore leggero (`get_commessa_stato_codice`, 404 `E_COMMESSA_NOT_FOUND`, lo stesso di `get_legami`), che dà anche lo
   `stato_da` della risposta dell'annullo; il resto il verbo, dentro `translate_db_errors`, col codice del DB
   (`E_DOC_PASSAGGIO_DI_PROCESSO`, `E_DOC_GIA_NELLO_STATO`, `E_STATO_WORKFLOW_NON_TROVATO`, i codici del guard).
4. **Il ponte della push**: nessuna modifica (firma invariata). Allineata la pagina `push_preventivo_handler.md`,
   che descriveva ancora il passaggio a pronta col verbo del cambio di stato (stantia già da prima del giro).
5. **IN_ESECUZIONE**: tolto da `STATO_COMMESSA_MAP` (`core/utils/severity.js`). ⚠️ **Correzione al punto 5**: la chiave
   `stato_in_esecuzione` di `locales/*.json` **non è della commessa**, è dei lotti (`vendite.lotti.stato_in_esecuzione`,
   letta da `LottiListView`): resta. La commessa non ha etichette sue per gli stati (le dà il DB).
6. **Test Django**: service (verbo nella firma nuova, il rifiuto arriva col codice del DB senza la difesa, 404 dal
   lettore leggero; ritirati i due test della difesa), API (azione della riga concessa e negata, riga senza azione →
   livello sul documento, la view dichiara il passaggio), e nuovo `vendite/tests/db/test_commessa_cambia_stato_db.py`
   (6, sul DB vero): l'azione delle righe, «riapri» senza azione (`E_PERMESSO_NEGATO`), «riapri» → APERTA (C-3), lo
   stato che ha già, IN_ESECUZIONE rifiutato dal vocabolario, l'annullo della bozza senza azione.
7. **Doc**: `api_commessa_stato.md` (passaggi e azione per riga, firma, codici, la proiezione della push); cataloghi BB
   backend (`PassaggioDocumento` ha un consumatore in più; la voce del service riscritta) e frontend.

**Fuori elenco, dichiarato.**
* ⚠️ **Il gate del drawer.** `CommessaGestioneDrawer` passava `permission: 'cambia_stato_commessa'` al mapper delle
  azioni (`mapAvailableActionsToDrawerActions`), che lo stampava su **ogni** pulsante di stato: dopo C-1 avrebbe
  nascosto anche l'annullo della bozza a chi non ha l'azione, mentre il backend lo ammette. Ritirato: la capability
  del giro 10 (`-35`) nasconde già il passaggio a chi non ha l'azione della sua riga (la stessa regola, una sede).
  Il gate di «Sblocca commessa» della dashboard di competenza resta: porta a «rendi pronta», che l'azione la chiede.
* L'operatore costruito da `dbops.fn_pgtap_crea_commessa` ha `cambia_stato_commessa` dal suo profilo (letto il
  2026-10-27): il test DB nega l'azione con un override utente spento, scritto nel test (nessun builder `dbops` del
  diniego: prima occorrenza).

**Decisioni e richieste aperte, emerse nel giro.**
* **Tid**: il parametro `permission` di `mapAvailableActionsToDrawerActions` resta **senza consumatori** (la commessa
  era l'unica): ritirarlo (col suo test in `useDrawerActions.spec.js`), o tenerlo per un dominio non ancora sul
  modello?
* **Team DB** (priorità bassa): `E_COMMESSA_AZIONE_NON_AMMESSA` lo sollevava solo il backend, e non lo solleva più:
  il codice resta a catalogo (`codici_errore.csv`, `messaggi_errore.csv`) senza chi lo usa. Da ritirare con
  `obsoleto_dal`; dopo, il BE toglie policy e ripiego (`error_messages_fallback.py`) rigenerando dal catalogo.

**Provato (2026-10-27):** suite completa sul DB reale (`ZEROERP_TEST_DB_E2E=1`), **6993 test verdi** (1 saltato, 1
fallimento atteso, già noti); vitest di `core` e `vendite` (746 verdi, 108 file); ruff, eslint e oxlint sui file
toccati, `guard:capability` puliti; mypy col cricchetto a 0 rilievi. Lo smoke non è stato lanciato: l'unico che tocca lo
stato della commessa (`smoke-test-ordini-giro-commessa.sh`, l'annullo) chiedeva l'azione già prima e la chiede ancora
(commessa non in bozza).

### 14.8 Revisione BE del giro (2026-10-27): regola del 1, due richieste al team DB

**Fatto dal team BE** (da committare, insieme al §14.7). ⚠️ Non ancora provato: la suite va rilanciata, il
«Provato» del §14.7 vale per il passaggio di prima.
* **Regola del 1** (Tid, 2026-10-27): un controllo «il documento c'è» davanti a un verbo che prende la testata nel
  perimetro e rifiuta da sé con un codice di classe NON_TROVATO è la stessa regola in due sedi, spesso con due codici.
  Ritirato dal cambio stato di commessa, ordine, bolla, contratto, preventivo e offerta (anche annullo, «Emetti» ed
  esito dell'offerta), dal passaggio offerta → contratto e dall'approvazione delle attività di commessa. Verificati
  prima gli undici verbi di stato, `fn_push_offerta_a_contratto` e `fn_approva_commessa_attivita` (INVOKER sotto la
  RLS). Dove lo stato serve alla risposta o a una decisione si legge col lettore leggero senza sollevare. Cambiano i
  codici del 404 (stessa classe, il frontend legge la classe): commessa `E_COMMESSA_NON_TROVATA`, contratto
  `E_CONTRATTO_NON_TROVATO`, offerta `E_OFFERTA_NON_TROVATA`. I resi erano già così.
* Commessa: le tre copie a mano del 404 (dettaglio, legami, porta oneri) dal BB `testata_o_not_found`.
* `cambia_stato_commessa`: un `nuovo_stato` non testuale (`null`, un numero) arrivava al verbo come stringa
  (`"None"`); ora è «stato mancante», 400, come lo legge `PassaggioDocumento`.
* Test: BB `operatore_di_prova` (`core/tests/_helpers/`, regola del 2), ritira le copie in 21 file.

**Richieste al team DB** (priorità bassa):
* **R-1. `vendite.fn_crea_revisione_offerta`, l'offerta che non c'è**: risponde `E_PARAMETRO_INVALIDO` (400) per un
  caso che è un 404, lo stesso difetto che `fn_push_offerta_a_contratto` ha corretto il 2026-08-06
  (`E_OFFERTA_NON_TROVATA`). Finché resta così il service legge prima la testata (`crea_revisione`); allineata la
  fn, il BE toglie quella lettura. Nella stessa fn lo stato da cui si revisiona è il letterale `'EMESSA'`: è lo
  stato di emissione del vocabolario (`script.fn_stato_emissione_id`).
* **R-2. Lo stato d'accettazione nel vocabolario**: il vocabolario dice iniziale, emissione e annullo, non
  l'accettazione. Il backend la scrive come letterale: `preventivi_service.cambia_stato` (il ramo della modalità di
  fatturazione: `"ACCETTATO"`, e `"EMESSO"`, che è l'emissione), `_STATI_FATTURABILI`, `_STATI_GENERA_PRATICA`;
  per l'offerta `StatoOfferta.ACCETTATA`. Proposta: una colonna come `emissione`, col suo lettore, per preventivi e
  offerte; poi il BE legge dal vocabolario, come per `rifiuta_stato_di_emissione` (§8.7).

---

## 15. Giro 11: la fattura al modello — ricognizione e domande (2026-10-27)

Via di Tid alla ricognizione (2026-10-27), ordine dei giri di W-1. **Non** è ancora il via allo sviluppo: Tid
chiede di chiarire prima i punti aperti (§15.4).

### 15.1 Come lavora la fattura (Tid, 2026-10-27)

La fattura non ha i pulsanti di processo degli altri documenti. **Il processo che muove gli stati è la gestione
dei lotti**: i pulsanti stanno sul lotto (genera, numera, riporta in bozza, annulla), e da lì parte anche la stampa.
Sulla fattura c'è solo la ristampa. Il giro quindi **non aggiunge un «Emetti» alla fattura**: porta al modello il
lotto, e fa sì che le fatture lo seguano attraverso il verbo e non con un `UPDATE`. ⛔ Il processo dei lotti e della
fattura (step, momenti, pulsanti), che sta nel backend, **non cambia** (Tid).

### 15.2 Com'è oggi (doc auto-generata, CSV e `backend/`, 2026-10-27)

**Quattro assi di stato**, non uno:

| Asse | Dove | Valori | Chi lo scrive |
| --- | --- | --- | --- |
| Fiscale, del lotto | `fatturazione_lotti.stato_doc_fiscale_id` | vocabolario `config.stati_doc_fiscale` (DRAFT, EMESSA, DEFINITIVA, INVIATA, REGISTRATA, ANNULLATA), condiviso con la fattura | il runner BE con `UPDATE` (`pipeline_repository.update_lotto_stato_doc`); `fn_riporta_lotto_a_draft`, `fn_annulla_lotto_da_draft`, `fn_close_giornaliero_lotto` |
| Fiscale, della fattura | `fatture.stato_doc_fiscale_id` | stesso vocabolario | `fn_sync_lotto_fatture_stato` (copia lo stato del lotto con `UPDATE`), `fn_numera_fattura_opz_emessa` (una fattura per volta, nello step numera), `fn_close_giornaliero_lotto` |
| Job, del lotto | `fatturazione_lotti.stato_lotto` (testo + `CHECK`) | IN_ESECUZIONE, COMPLETATO, ERRORE | il runner BE con `UPDATE` (`set_lotto_job_stato`), **con i valori e i passaggi ricopiati in Python**; `vendite.fn_set_fatturazione_lotto_stato` è morta (solo due pgTAP) e ha una matrice che **dissente** (il BE ammette COMPLETATO → ERRORE, motivato nel commento; la funzione no) |
| Operativo, del lotto | `fatturazione_lotti.stato_operativo` (testo + `CHECK`) | APERTO, CHIUSO | `fn_sync_lotto_fatture_stato` e `fn_close_giornaliero_lotto` (solo DB) |

Più `fatturazione_lotti_fatture.stato_esecuzione` (avanzamento della singola fattura nel giro) e `stato_sdi_id`.

**La matrice** `config.stati_doc_fiscale_transizioni` è una sola per lotto e fattura (`solo_lotto`, `solo_fattura`,
e `meta.tipo_lotto` per il giornaliero). I due guard (`trgfn_fatturazione_lotti_guard_stato`,
`trgfn_fatture_guard_stato`) la leggono già. Le righe con l'azione nel `meta` sono le tre manuali del lotto:
`riporta_a_draft` (EMESSA → DRAFT), `numera` (EMESSA → DEFINITIVA), `annulla` (DRAFT → ANNULLATA).

**Le azioni di processo che esistono già** (CSV `azioni_processo`), tutte controllate **solo** dal backend
(`post_permission`):

| Azione | Endpoint | Note |
| --- | --- | --- |
| `genera_fatture_lotti` | genera, rilancia | |
| `numera_fatture_lotti` | numera (anche in coda, `FATTURAZIONE_NUMERA`) | «irreversibile» |
| `reset_lotto_draft` | riporta il lotto in bozza | |
| `reset_lotto_fattura_draft` | **toglie una fattura** pre-fiscale dal lotto | il nome è rimasto quello vecchio (la funzione DB è stata rinominata, URL e permesso no) |
| `genera_fattura`, `approva_fattura`, `emetti_fattura` | nessuno | a catalogo, mai usate |

**La fattura da sola.** Le righe `solo_fattura` della matrice (DRAFT → EMESSA, EMESSA → INVIATA/DEFINITIVA,
DEFINITIVA → INVIATA, INVIATA → REGISTRATA) oggi le scrive solo la pipeline, fattura per fattura dentro il giro del
lotto. **Nessuno scrive REGISTRATA**, e non c'è uno stato per lo scarto SDI: l'invio allo SDI non è ancora un
processo (`fn_prepare_sdi_payload` prepara il tracciato, non registra l'esito).

**Debiti nei corpi**, che il giro chiude senza bisogno di decisioni: i letterali `'EMESSA'` e `'INVIATA'` in
`trgfn_fatture_guard_stato`, `fn_sync_lotto_fatture_stato` e `fn_numera_fattura_opz_emessa` (parametro di default);
la «retrocessione» del giornaliero decisa confrontando `ordine`, mentre R-1 vuole avanti/indietro dal vocabolario.

### 15.3 Decisioni di Tid (2026-10-27)

| # | Domanda | Decisione |
| --- | --- | --- |
| F-0 / D-G1 | Il riquadro «origine» della stampa della fattura, che esce sempre vuoto (§10) | ✅ **(c)**: l'elenco dei documenti d'origine, letto dalle righe (`fatture_righe.sorgente_tipo_id`, `sorgente_uid`), es. «Rif.: DDT 12, DDT 15, Commessa 7» |
| F-1 | La fattura cambia stato anche da sola, senza il lotto? | ✅ **Sì** (es. l'esito dello SDI): serve anche il verbo della singola fattura, non solo quello del lotto |
| F-2 | Il permesso dei pulsanti del lotto | ✅ Chi gestisce il lotto deve avere l'azione per **numerare**, e la stessa per **riportare in bozza**; nome proposto da Tid `numera_fattura`. Le azioni mai usate (`genera_fattura`, `approva_fattura`, `emetti_fattura`) si **ritirano** |
| F-3 | La fattura ha un annullo suo? | ✅ **No**: una fattura numerata si storna con la nota di credito; prima della numerazione la si toglie dal lotto |
| F-4 | Lo stato del job (`stato_lotto`) | ✅ **Si allinea al DB**: una regola sola, nessuna copia nel backend. ⛔ Il processo dei lotti e della fattura non cambia |
| F-5 / D-N1 | Le azioni per riga | ✅ Si correggono nel giro, ma **con un pezzo standard**: quando si passa agli altri documenti non si deve rimodificare niente |

### 15.4 Da chiarire con Tid prima dello sviluppo

* **Q-F1, il nome dell'azione (F-2).** Esiste già `numera_fatture_lotti` («irreversibile»), chiesta oggi da numera.
  Proposta: **si tiene quella**, senza un nome nuovo (`numera_fattura` sarebbe un doppione, e chi ha già il
  permesso nei profili lo perderebbe). Il «riporta in bozza» passa alla stessa azione e `reset_lotto_draft` si
  ritira.
* **Q-F2, gli altri pulsanti del lotto.** Restano da dire: **genera** e **rilancia** (`genera_fatture_lotti`, oggi
  separata), l'**annullo del lotto in bozza** (riga 11: proposta, solo il permesso sui lotti, perché non c'è niente
  di fiscale da disfare) e **togli la fattura dal lotto** (`reset_lotto_fattura_draft`: resta, ed è un'azione di
  riga, Q-F5). Proposta: `genera_fatture_lotti` resta com'è (è la produzione, non un passaggio di stato pesante).
* **Q-F3, la fattura da sola (F-1).** Oggi nessuno la fa muovere da sola, e lo stato dello scarto SDI non esiste.
  Proposta: il giro scrive **il verbo della fattura** sulle righe `solo_fattura` che ci sono (chiamato dalla
  pipeline al posto degli `UPDATE`), **senza** stati nuovi; l'esito dello SDI (registrata, scartata) lo aggiunge il
  cantiere dell'invio allo SDI, sulla matrice e sul verbo già pronti.
* **Q-F4, quali stati del lotto rientrano in F-4.** Proposta: lo stato del **job** (`stato_lotto`) prende una matrice
  in tabella e un verbo DB unico scrittore (la regola del backend, COMPLETATO → ERRORE compreso, perché è quella
  motivata); il runner chiama il verbo nei punti in cui oggi fa l'`UPDATE`, negli stessi momenti; la copia Python
  si ritira, la funzione morta si riscrive o si ritira. Lo stato **operativo** (APERTO/CHIUSO) lo scrive già solo il
  DB: fuori, salvo che Tid lo voglia dentro. Resta un `CHECK` sui testi o diventa un vocabolario come gli altri? Il
  team DB propone il vocabolario, perché la matrice in tabella ha bisogno di id.
* **Q-F5, il pezzo standard delle azioni per riga (F-5).** La forma per azione c'è già (linee guida SQL §12.5:
  `script.fn_check_<azione>`, colonna di blocco nella vista di riga, FE `disabled` + `tooltip`). Manca ciò che la
  rende ripetibile senza rimetterci mano: proposta del team DB, da discutere —
  1. un **registro** delle azioni di riga (azione, vista che la espone, colonna di blocco, funzione di check, azione
     di processo che la permette): è il censimento del §12.5.6, scritto una volta;
  2. un **presidio pgTAP** che per ogni riga del registro verifica che la vista abbia la colonna e che la funzione
     esista ed emetta il motivo;
  3. **un BB FE** che costruisce il pulsante di riga leggendo colonna di blocco e motivo, al posto dei 44 componenti
     che oggi lo fanno a mano (lato FE, richiesta al team).

  Nel giro: le azioni di riga del lotto (togli la fattura, e quelle del drawer del lotto) passano per il registro;
  gli altri documenti si iscrivono quando arriva il loro turno, senza toccare il pezzo comune.
* **Q-F6, D-G1 (c) nel dettaglio.** La testata ha anche un suo `sorgente_tipo_id`/`sorgente_uid`: proposta,
  l'elenco si legge **solo** dalle righe (una sede), distinti per documento, nell'ordine delle righe; la testata non
  si aggiunge. Il lettore lo scrive il DB (nome dal lineage, come la finestra dell'annullo), il BE lo porta in
  `get_fattura_testata`, il modello di stampa lo mostra.
* **La nota di credito: non è una domanda.** L'accredito di un reso (`fn_accredita_riga_reso`) scrive solo la
  riga di commessa negativa: «il documento NON nasce qui: nasce nel giro di fatturazione». La nota passa quindi dallo
  stesso lotto e dalla stessa matrice, e il giro la copre senza lavoro in più (letto il 2026-10-27).

✅ **Tid, 2026-10-27: Q-F1 … Q-F6 confermate come da proposta.** Il piano qui sotto le applica.

### 15.5 Il piano

Letto il 2026-10-27 sulla doc auto-generata, sui CSV e su `backend/`/`frontend/`. Già pronto dai giri prima: la
mappa del modello (`script.fn_doc_stato_modello`) conosce **già** `vendite.fatture` e `vendite.fatturazione_lotti`,
col filtro `solo_lotto`/`solo_fattura` sulla matrice condivisa; il verbo comune (`fn_doc_stato_id`,
`fn_guard_passaggio`, `fn_doc_scrivi_stato`) e la porta (`trgfn_doc_stato_solo_dal_verbo`) servono così come sono.

| Pezzo | Che cosa |
| --- | --- |
| matrice fiscale | colonna `azione_processo_codename` su `config.stati_doc_fiscale_transizioni` (FK al catalogo; senza, `fn_doc_passaggio` rifiuta la testata). CSV: `numera_fatture_lotti` sulle righe 3 (numera) e 2 (riporta in bozza), Q-F1; riga 11 (annullo della bozza) senza azione, Q-F2. ⚠️ `manuale` si legge da `meta` con **default true**: le righe di processo (1, 5 del lotto; 6 … 10 della fattura) oggi hanno `meta = {}` e risulterebbero manuali; il CSV le dichiara `"manuale": false`. Mirror con la colonna (⚠️ `nullValue`) |
| catalogo azioni | `genera_fattura`, `approva_fattura`, `emetti_fattura` (F-2) e `reset_lotto_draft` (Q-F1) ritirate nel CSV. ⚠️ Se un profilo le ha, il guard ATTIVO ferma il migrate (come IN_ESECUZIONE nel §14.4): passo a mano prima, su dbdev; chi ha `reset_lotto_draft` riceve `numera_fatture_lotti` (dato, Tid), altrimenti perde il «riporta in bozza» |
| verbo del lotto | `vendite.fn_cambia_stato_lotto(id, stato)` sul verbo comune, DEFINER col predicato del perimetro: i passaggi manuali (numera, riporta in bozza, annulla); dopo il lotto, le fatture lo seguono dal verbo della fattura |
| verbo della fattura | `vendite.fn_cambia_stato_fattura(id, stato)`, stesso schema, sulle righe `solo_fattura` (F-1, Q-F3): nessuno stato nuovo, l'esito SDI arriva col suo cantiere |
| passaggi di processo | chi è la causa scrive con `fn_doc_scrivi_stato` e basta (regola del verbo comune): `fn_sync_lotto_fatture_stato`, `fn_numera_fattura_opz_emessa`, `fn_close_giornaliero_lotto`, `fn_riporta_lotto_a_draft`, `fn_annulla_lotto_da_draft`. Lo step della pipeline che oggi il runner scrive con `UPDATE` (`update_lotto_stato_doc`) passa a una funzione DB di processo (nome nel giro), chiamata **negli stessi momenti**: il processo non cambia (F-4) |
| porte | `trgfn_doc_stato_solo_dal_verbo` `_a05_` su `vendite.fatture` e `vendite.fatturazione_lotti`. Da censire nel giro: la GUC di manutenzione `zeroerp.maintenance_reset_lotto_draft`, che oggi scavalca il guard del lotto |
| stato del job | vocabolario degli stati del job (IN_ESECUZIONE, COMPLETATO, ERRORE) e matrice in tabella con la regola del backend (COMPLETATO → ERRORE compreso, Q-F4); `fn_set_fatturazione_lotto_stato` riscritta su quella matrice e unica scrittrice, con la porta; la copia Python (`set_lotto_job_stato`) si ritira. Lo stato operativo resta fuori |
| debiti dei corpi | `'EMESSA'`, `'INVIATA'` dal vocabolario; la «retrocessione» del giornaliero da `congela_fiscale` e non da `ordine` (R-1) |
| capability | `fn_available_actions_lotto`: permesso ⇒ nascondi, letto dalla riga del passaggio (oggi il FE tiene la sua mappa azione → permesso, `LOTTO_AZIONE_PERMESSO`: è una copia, si ritira) |
| azioni di riga (Q-F5) | registro delle azioni di riga, presidio pgTAP sul registro, iscritte le azioni di riga del lotto («togli dal giro», `reset_lotto_fattura_draft`: la sede in riga c'è già); richiesta FE per il BB del pulsante di riga |
| origine (Q-F6) | lettore DB dei documenti d'origine di una fattura, dalle righe, distinti, nell'ordine delle righe, nome dal lineage |
| fixture | 11 pgTAP scrivono lo stato di fattura o lotto con `UPDATE` diretto (letto il 2026-10-27): al verbo o a `dbops.fn_pgtap_porta_a_stato` |
| guida | modello §10 (riga della fattura; le azioni a catalogo sistemate), guida della fatturazione, pagine manuali |

**Due scelte tecniche, che il team DB propone (Tid le può cambiare):**

* **P-1, la colonna dello stato del job.** Il vocabolario ha un id come gli altri; la colonna del lotto resta il
  **codice** (`stato_lotto`), con una FK sul codice del vocabolario. La garanzia è la stessa (nessun valore fuori
  vocabolario), il codice è la chiave naturale e i lettori in DB, BE e FE non si toccano. L'alternativa (colonna
  `stato_lotto_id`) è più uniforme ma riscrive ogni lettore, per lo stesso risultato.
* **P-2, «numera» è asincrona.** Il pulsante accoda un lavoro (`FATTURAZIONE_NUMERA`), e la scrittura la fa il job,
  non l'utente. Il permesso si chiede **quando l'utente preme** (403 dalla riga del passaggio, come gli altri
  documenti); il job scrive come passaggio di processo, di cui è la causa. Così il job non ha bisogno del permesso
  dell'utente.

**Richiesta al BE** (col percorso intero, a giro DB provato): il 403 dalla riga del passaggio (`PassaggioDocumento`)
su numera e riporta in bozza, al posto dei `post_permission`; il runner chiama le funzioni DB dello stato fiscale e
del job al posto degli `UPDATE`, negli stessi punti; si ritira la copia della matrice del job; `get_fattura_testata`
porta l'elenco delle origini e il modello di stampa lo mostra; test e doc. **Al FE:** si ritira `LOTTO_AZIONE_PERMESSO`;
il BB del pulsante di riga che legge il registro.

### 15.6 Scritto (2026-10-27): lo stato di lotto e fattura al modello

Via di Tid allo sviluppo (2026-10-27, «si ok procedi», con P-1 e P-2). Scritto e provato in transazione sullo
scratch; **non applicato**. Il registro delle azioni di riga (Q-F5) e il lettore delle origini (Q-F6) **non sono
scritti**: la ricognizione ha smentito una premessa di ciascuno, e tornano a Tid (§15.9).

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261027-01` (00_schema) | colonna `azione_processo_codename` su `config.stati_doc_fiscale_transizioni`, FK al catalogo |
| CSV `stati_doc_fiscale_transizioni`, mirror `20260210-01` | `numera_fatture_lotti` sulle righe 2 (riporta in bozza) e 3 (numera), Q-F1; `manuale` dichiarato su ogni riga (`false` sulle righe di processo 1, 4, 5 e 6 … 10, che il lettore leggeva come manuali per default); il mirror passa a `nullValue: "NULL"` col token nelle celle |
| CSV `azioni_processo` (id 2, 3, 4, 6, 27) | ritirate `genera_fattura`, `approva_fattura`, `emetti_fattura`, `reset_lotto_draft` (`attivo = false`); la descrizione di `numera_fatture_lotti` dice anche «riporta in bozza» |
| `-02` (00_schema) | `config.stati_lotto_job` (vocabolario, `codice_interno` UNIQUE) e `config.transizioni_stati_lotto_job` (la matrice, CHECK da ≠ a) |
| `-03`, `-04` (80_data), CSV | i tre stati del job e i cinque passaggi del backend (COMPLETATO → ERRORE compreso) |
| `-05` (90_end) | FK `fk_fatturazione_lotti_stato_lotto` sul codice (P-1) al posto del CHECK `chk_fatturazione_lotti_stato_job`; in 90_end perché valida i lotti che ci sono, dopo il seed |
| `-06` | `vendite.trgfn_fatturazione_lotti_guard_stato_job` (BEFORE UPDATE OF `stato_lotto`): la sola regola dei passaggi del job |
| `-07` | DROP `vendite.fn_set_fatturazione_lotto_stato` (morta, in disaccordo col backend) |
| `-08` | `vendite.fn_cambia_stato_lotto(id, stato)`: il verbo dei passaggi manuali del lotto, sul verbo comune, DEFINER |
| `-09` | `vendite.fn_lotto_proietta_stato_step(id, stato_id)`: il giro della pipeline porta il lotto allo stato dello step (processo: stato di uno step della pipeline del suo tipo, mai lo stato iniziale) |
| `-10` | `vendite.fn_fattura_proietta_stato(id, stato_id)`: il verbo della fattura (F-1, Q-F3), di processo; rifiuta un passaggio manuale |
| `-11` … `-13` | sync, numerazione, chiusura del giornaliero scrivono lo stato dai verbi (`-09`, `-10`), una fattura per volta |
| `-14`, `-15` | «riporta in bozza» e l'annullo chiamano il verbo del lotto dopo la pulizia; lo stato iniziale e quello d'annullo dal vocabolario (`iniziale`, `fn_stato_abortito_id`) |
| `-16` | `trgfn_fatture_guard_stato`: via la «retrocessione GIORNALIERO» decisa da `ordine` (R-1), già coperta dalla matrice |
| `-17`, `-18` | la porta su `vendite.fatture` e `vendite.fatturazione_lotti` |
| `-19` | `script.fn_available_actions_lotto`: permesso ⇒ nascondi, dalla riga del passaggio |
| `-20` | `dbops.fn_pgtap_porta_a_stato`: fattura e lotto coi loro verbi, anche sui passaggi di processo |
| CSV `stati_check_dichiarazioni` | due righe ESENTE: `fatturazione_lotti.stato_operativo = ERRORE` (nessuno lo scrive; il presidio lo vedeva per coincidenza nella funzione ritirata) e `fatturazione_lotti_fatture.stato_esecuzione = ERRORE` (scritto dalla sync attraverso `fn_resolve_stato_esecuzione`) |
| doc | guida del modello (§7 la forma della fattura, §10 la riga e l'intro, le azioni ritirate, lo stato del job); guida della fatturazione; pagine manuali nuove di `-06`, `-08`, `-09`, `-10` e delle due tabelle; tolta quella della funzione ritirata |

**Scostamenti dal piano del §15.5, dichiarati.**
* **Lo stato del job: un guard, non un verbo.** Il piano diceva «`fn_set_fatturazione_lotto_stato` riscritta e unica
  scrittrice». Leggendola, fa una cosa in più del backend: riscrive lo `stato_esecuzione` delle fatture del lotto.
  Farne lo scrittore avrebbe cambiato il processo (F-4 lo vieta). Quindi la regola sta in un guard sulla colonna, che
  giudica ogni scrittura, il runner tiene il suo `UPDATE` e ritira la sua copia della regola; la funzione si ritira.
* **«Il verbo della fattura» è di processo.** Oggi tutti i passaggi della fattura sono di processo: un verbo con la
  prima riga (permesso) non avrebbe un passaggio da fare. Il verbo con la prima riga nascerà quando l'esito SDI
  porterà passaggi manuali.
* **«Riporta in bozza» su un lotto già in bozza** fa la sola pulizia, come prima: lì non c'è passaggio, quindi
  niente permesso dalla riga (il backend chiede il permesso sul documento).
* **Debiti che restano, dichiarati**: i letterali `'EMESSA'` (cancello all'emissione di `trgfn_fatture_guard_stato`,
  default di `fn_numera_fattura_opz_emessa`) e `'INVIATA'` (chiusura del giornaliero nella sync): nessuna colonna
  del vocabolario fiscale dice «lo stato dell'emissione» o «lo stato dell'invio», e aggiungerla è una scelta sul
  vocabolario, non un ritocco. Il §15.2 li dava per chiusi nel giro: non lo sono.
* **Fatto da sapere su P-2**: i lavori della coda girano con l'identità dell'operatore che li ha accodati
  (`operator_identity_context`), quindi il job il permesso lo avrebbe. P-2 resta giusto per il batch notturno, che
  non ha un operatore; la scelta non cambia.

### 15.7 Prova e regressione (2026-10-27)

Sullo scratch `zeroerp_ruoli` (owner), l'SQL estratto dei changeSet dopo la riga `BEGIN;` di ogni pgTAP, col seed
dei CSV simulato (il loader di Liquibase, `nullValue` compreso, si prova solo all'apply).

* **279 pgTAP che nominano lotti, fatture, la matrice fiscale o le azioni**, prima e dopo: verdi 225 prima, 217
  dopo; 9 file cambiano esito, tutti spiegati e portati: 6 scrivevano lo stato con un `UPDATE` (ora dai verbi, attese
  invariate), il presidio del verbo comune (porta su 9 testate; il documento «non ancora portato» diventa l'ordine
  d'acquisto, fuori mappa), il presidio degli stati del CHECK (le due righe ESENTE), il presidio dei lock (la tabella
  nuova `config.stati_lotto_job` chiede il lock del codice: lo monta `ci_apply`, rosso solo prima). Dopo il porting i
  9 sono verdi, tranne i 2 «rossi da owner» di sempre del verbo comune.
* **Il pgTAP nuovo** `vendite/test-fattura-lotto-al-modello-v1` (22 test): 21/22; il 4 (le azioni ritirate) legge il
  CSV e diventa verde solo dopo il migrate.
* ⚠️ **Sette pgTAP del censimento si fermano presto già prima** (fixture che prendono cliente o utility dai dati:
  `test-stati-doc-transizioni-giornaliero`, `test-fn-list-emittibili-lane`, `test-fatture-righe-importo-e-kit-v1`,
  `test-annulla-lotto-non-riscrive-stato-v1`, `test-lotti-attivita-stato-esecuzione-v2`,
  `test-fatture-log-trigger-sync`, `test-lotti-gruppi-esito`): sullo scratch non arrivano alle righe che il giro
  tocca, quindi la misura non le vede. Li ho portati leggendoli (gli `UPDATE` dello stato ai verbi; la funzione
  ritirata alla scrittura del runner e al BB `fn_resolve_stato_esecuzione`); la prova vera è la corsa di Tid su
  dbdev. Attese cambiate, dichiarate in testa ai file: `test-lotti-attivita-stato-esecuzione-v2` (7, 8, 10, 12) e
  `test-stati-doc-transizioni-giornaliero` (3, da «qualunque errore» al messaggio del guard).
* **Rossi solo prima del migrate**, perché leggono il CSV di `azioni_processo`: il 4 del pgTAP nuovo e il 30 di
  `script/test-permessi-funzioni-risoluzione` (attesa cambiata: `reset_lotto_draft` spenta).
  `config/test-permessi-user-overrides` usava `approva_fattura` per il suo override di prova: ora
  `numera_fatture_lotti`.
* **I presidi trasversali** di `dbops/`, `script/`, `config/` fuori dal censimento (202 file), prima e dopo: 186 verdi
  in entrambe le corse, nessun file cambia esito.

⚠️ **Su dbdev, PRIMA del migrate, un passo a mano (Tid).** Spegnere le quattro azioni lo rifiuta il guard di
disattivazione: i profili e un utente le hanno ancora (provato su dbdev in transazione annullata il 2026-10-27:
`config.profili_accesso_azioni` le lega ai profili 1-4, 9221, 9222; `config.user_override_azioni` ha tre righe
dell'utente 6). Chi oggi «riporta in bozza» con `reset_lotto_draft` deve avere `numera_fatture_lotti` (letto: il solo
profilo che l'ha abilitata, il 9222, ha già anche `numera_fatture_lotti`). Il passo:

```sql
BEGIN;
-- chi aveva reset_lotto_draft abilitata riceve numera_fatture_lotti abilitata
UPDATE config.profili_accesso_azioni pn SET abilitata = true
  FROM config.profili_accesso_azioni pr
  JOIN config.azioni_processo r ON r.id = pr.azione_id AND r.permission_codename = 'reset_lotto_draft'
 WHERE pr.abilitata AND pn.profilo_accesso_id = pr.profilo_accesso_id
   AND pn.azione_id = (SELECT id FROM config.azioni_processo WHERE permission_codename = 'numera_fatture_lotti');
-- poi i legami alle quattro azioni ritirate
DELETE FROM config.user_override_azioni
 WHERE azione_id IN (SELECT id FROM config.azioni_processo
                      WHERE permission_codename IN ('genera_fattura','approva_fattura','emetti_fattura','reset_lotto_draft'));
DELETE FROM config.profili_accesso_azioni
 WHERE azione_id IN (SELECT id FROM config.azioni_processo
                      WHERE permission_codename IN ('genera_fattura','approva_fattura','emetti_fattura','reset_lotto_draft'));
COMMIT;
```

In CI non serve: il database nasce da zero e nessun seed lega profili alle azioni.

**Due rossi di dbdev, dopo l'apply (Tid, 2026-10-27), corretti nel test.**
`test-lotti-attivita-stato-esecuzione-v2` 9 e 10: il porting aveva tolto la scrittura del ponte che la funzione
ritirata faceva, e il lotto non era più fermo; il test ora scrive il ponte col BB della mappatura prima del 9. Il guard
del COMPLETATO è intatto. `test-fn-list-emittibili-lane`: si fermava sul verbo della commessa (giro 10) per
`E_PERMESSO_NEGATO`; il test ora concede `cambia_stato_commessa` all'operatore. Altri sette pgTAP del giro 10
chiamavano quel verbo senza concederla: portati allo stesso modo col via di Tid (2026-10-27) —
`test-fn-list-commesse-emittibili-fatturazione-immediata-v1`, `test-tipo-movimento-colonna-v1`,
`test-vw-af-merce-per-riga-v1`, `test-porta-oneri-giro-completo-v1`, `test-porta-oneri-contatore-cieco-v1`,
`test-fn-available-actions-commessa-v1`, `test-fn-emit-attivita-propaga-audit-pricing-v1`.

⚠️ **`test-fn-available-actions-commessa-v1`, terzo rosso di dbdev (Tid, 2026-10-27): la concessione era nel posto
sbagliato.** Il test 2 (BOZZA: `{annulla, rendi_pronta}`) vedeva `{annulla}`: dal `20261026-35`
`fn_available_actions_commessa` **nasconde** il passaggio a chi non ha l'azione, e la concessione arrivava dopo, solo
prima del verbo. Spostata nel setup, prima dei test di BOZZA: le capability si misurano su chi può agire. Negli altri
sette file nessuna lettura di capability precede la concessione (grep, 2026-10-27).
**Perché la regressione non l'ha visto**: sullo scratch tutti e otto i file si fermano nel setup
(`p_billing_account_id` nullo: lo scratch non ha un billing account con emittente), prima e dopo. Rosso uguale = nessuna
differenza, ma nessuna misura: questi otto si verificano **solo su dbdev**.

**Altri quattro rossi di dbdev (corsa di Tid, 2026-10-27), corretti nel test, attese invariate.** Nessuno era
nel censimento.

* `test-available-actions-lotto-v1`, effetto del `-19` (permesso ⇒ nascondi): il file sceglie lotti veri di dbdev
  e legge la capability con l'operatore del test, che non ha `numera_fatture_lotti`. Da EMESSA l'8 vedeva `{}` al
  posto di `{numera, riporta_a_draft}`, e il 9 un `enabled` nullo. La concessione ora sta prima dei test di stato. Il
  censimento non l'ha visto perché il file non scrive lo stato: lo legge.
* Tre pgTAP **del giro 8**, rimasti indietro: attivavano il contratto con un `UPDATE` diretto, che la porta ferma
  (`Lo stato del documento Contratto … si cambia solo dalle sue operazioni`). Ora passano da
  `dbops.fn_pgtap_porta_a_stato` (che concede `emetti_contratto`).
  * `test-fn-resolve-prezzo-listino-v2-v1` e `test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1`: il §11.5
    li dava «tronchi già prima del giro, uguali dopo», quindi nessuno li aveva portati. Su dbdev arrivano fino alla
    porta: se dopo il porting si fermano più avanti, è il troncamento di prima e va guardato a parte.
  * `test-bozza-non-operativa-e-preview-contratto-v1`, **mancato dal censimento del giro 8**: la fixture di
    PGTAP_MX_CNT passa da `fn_pgtap_porta_a_stato`. Il 3, l'attivazione rifiutata con un listino che ha solo la
    bozza, chiama il verbo `vendite.fn_cambia_stato_contratto` con `emetti_contratto` concessa (senza, il rifiuto
    sarebbe quello del permesso): stessa attesa, perché il rifiuto lo dà il guard di transizione che il verbo
    attraversa.

### 15.8 Richiesta al team BE (elenco chiuso, dopo l'apply)

Percorso letto il 2026-10-27: `pipeline_runner._execute_pipeline_step`, `pipeline_repository.update_lotto_stato_doc`
e `set_lotto_job_stato`, le view del lotto (`ApiResetLottoDraft`, `ApiRiportaLottoADraft`, le due di numera), il
frontend (`useLottoAzioni.js`, `LottoDrawer.vue`), i test Django che li toccano. **Dopo l'apply il giro della
pipeline si rompe** (punto 1): la porta non lascia passare l'`UPDATE` dello stato del lotto.

1. **Lo stato dello step**: `update_lotto_stato_doc` chiama `vendite.fn_lotto_proietta_stato_step(lotto_id,
   stato_doc_fiscale_id)`, nello stesso punto di `_execute_pipeline_step`. Nient'altro cambia nel runner.
2. **Lo stato del job**: `set_lotto_job_stato` tiene il suo `UPDATE` (stessi momenti, stessa nota in `meta`) e ritira
   la sua copia della regola (l'elenco dei tre valori e i passaggi ammessi): la dice il guard, con
   `E_LOTTO_PARAMETRO_NON_COERENTE` (parametro `transizione_stato_lotto`); un valore fuori vocabolario lo rifiuta la FK.
   Resta il no-op sullo stesso stato, se serve al runner.
3. **Il 403 dalla riga del passaggio** (`PassaggioDocumento`): «riporta in bozza» (`ApiRiportaLottoADraft`) e
   «numera» (le due view con `post_permission = "numera_fatture_lotti"`) chiedono l'azione della riga
   (`numera_fatture_lotti`); l'annullo della bozza (`ApiResetLottoDraft`) solo il permesso sul documento (Q-F2).
   Via i `post_permission = "reset_lotto_draft"`. Lo stato d'arrivo di «riporta in bozza» è lo stato iniziale del
   lotto: lo legge `script.fn_doc_stato_iniziale_id(testata)`, aggiunto su richiesta del team BE (§15.13). Mancava
   nella prima stesura di questo elenco.
4. **Le azioni ritirate**: nessun riferimento a `reset_lotto_draft`, `genera_fattura`, `approva_fattura`,
   `emetti_fattura` come permesso (il task di pipeline `reset_lotto_draft` è un altro nome e resta).
5. **Frontend**: si ritira `LOTTO_AZIONE_PERMESSO` per `numera`, `riporta_a_draft`, `annulla` (il permesso lo dice
   la capability, che nasconde il bottone); restano i tre verbi della pipeline che il DB non espone (`avanza_step`,
   `rigenera_bozza`, `rilancia_step`, con `genera_fatture_lotti`).
6. **Test Django** che scrivono lo stato di lotto o fattura con un `UPDATE`, usano `fn_set_fatturazione_lotto_stato`
   o `reset_lotto_draft` (`test_reset_lotto_draft_api.py`, `test_pipeline_repository.py`, `test_pipeline_runner.py`,
   `test_pipeline_step_executor.py`, `core/tests/api/test_permissions.py`): ai verbi e alle azioni nuove.
7. **Doc** delle API del lotto: i permessi per passaggio. Anche (revisione delle guide, 2026-10-27, §15.12):
   `api_lotti_list.md` cita il CHECK `chk_fatturazione_lotti_stato_job`, che dal `-05` è la FK
   `fk_fatturazione_lotti_stato_lotto`; `api_run_lotto_pipeline.md` cita la matrice di `set_lotto_job_stato`, che
   col punto 2 si ritira; `api_reset_lotto_draft.md` il permesso `reset_lotto_draft` (punto 3).

Da sapere: nessun codice d'errore nuovo. Il D-G1 (il riquadro «origine» della stampa) non è in questa richiesta:
aspetta la risposta del §15.9.

### 15.9 Due premesse smentite dalla ricognizione: tornano a Tid

* **Q-F6, le origini della fattura (D-G1 = c).** La proposta diceva «l'elenco si legge dalle righe». Le righe di
  fattura **non portano la sorgente**: `fatture_righe.sorgente_tipo_id` è nullable e la pipeline non la scrive (letto
  il 2026-10-27, struttura e dbdev); il legame passa dalle attività fatturabili (`attivita_fatturabili.fattura_riga_id`)
  alla commessa, e da lì ai documenti a monte. Il lineage della fattura, all'indietro, dà **la commessa**. La domanda:
  sulla carta, «origine» è
  (a) la commessa (il primo passo del lineage), o
  (b) i documenti commerciali a monte della commessa (DDT, ordine, contratto, preventivo…), risalendo il lineage oltre
  la commessa, che per il cliente è un contenitore interno, o
  (c) tutti e due.
  Consiglio del team DB: **(b)**. Il cliente riconosce la bolla o l'ordine, non la commessa; ed è la forma della
  fattura elettronica, che cita i DDT, l'ordine d'acquisto e il contratto.
* **Q-F5, il registro delle azioni di riga.** La proposta diceva «la vista che la espone, la colonna di blocco».
  L'unica azione di riga del lotto, «togli dal giro», prende il motivo del blocco da una `fn_check` (giusto), ma la
  colonna di riga la compone **il backend**, in una query del repository (`pipeline_repository`,
  `uscita_blocco_reason`): non c'è una vista DB da registrare. La domanda: nel giro si porta quella composizione in
  una vista DB (il backend la legge da lì, come vuole la regola del §12.5), e il registro nasce con la vista come
  superficie; oppure il registro ammette anche una superficie del backend (un nome, non verificabile dal presidio).
  Consiglio del team DB: **la vista DB**. Altrimenti il presidio del registro non può verificare la superficie, cioè
  proprio la parte che si dimentica.

✅ **Tid, 2026-10-27: Q-F6 = (b), i documenti a monte; Q-F5 = la vista DB.** Il piano dei due pezzi è al §15.10.

### 15.10 Il piano dei due pezzi rimasti (2026-10-27; ✅ Tid: via, nome della colonna e P-3 come da proposta)

**Le origini (Q-F6 = b).** Il lineage all'indietro risale già oltre la commessa (`vendite.fn_documento_lineage`, fino
a 10 livelli; il registro dei tipi è `config.sorgenti`). Manca **chi dice quali tipi si citano** in fattura: oggi
nessuna colonna di `config.sorgenti` distingue un documento commerciale (DDT, ordine, contratto…) da un contenitore
interno (la commessa, le attività). Scriverlo come elenco di codici nel lettore è il letterale che il modello vieta.

| pezzo | cosa |
| --- | --- |
| vocabolario | `config.sorgenti.citato_in_fattura boolean NOT NULL DEFAULT false` (nome da confermare), `true` su DDT, ordine, contratto, offerta, preventivo; `false` su commessa, attività e righe. Il CSV di `sorgenti` col mirror |
| lettore | `vendite.fn_fattura_origini(p_fattura_id)`: dal lineage all'indietro, i nodi con `citato_in_fattura`, distinti, ordinati per livello e poi per codice; restituisce tipo, uid, codice, etichetta, data del documento |
| presidio | pgTAP: una fattura da commessa che nasce da un ordine e da un DDT cita i due e non la commessa; una fattura senza documenti a monte non cita nulla |
| BE | richiesta: la stampa e il dettaglio della fattura leggono le origini dal lettore |

**P-3 (da decidere).** Per una fattura che nasce da più commesse, le origini sono **l'unione**: ogni documento una
volta sola. La fattura elettronica ammette più riferimenti per tipo, quindi l'unione non perde nulla.

**Il registro delle azioni di riga (Q-F5 = vista DB).** La colonna di blocco di «togli dal giro» la compone oggi il
repository del backend (`vendite_repository`, la query dei gruppi del lotto: `uscita_blocco_reason`,
`uscita_blocco_reason_key`, `n_trascinati`, dalla `fn_check_documento_escludibile_da_giro`).

| pezzo | cosa |
| --- | --- |
| vista | `vendite.vw_lotti_gruppi_azioni`: una riga per (lotto, gruppo), con le colonne di blocco dell'azione e `n_trascinati`, le stesse espressioni di oggi |
| registro | `config.azioni_riga` (azione, vista superficie, colonna motivo, colonna chiave del motivo, `fn_check` che la madre chiama per rifiutare); prima riga «togli dal giro» |
| presidio | pgTAP sul registro: ogni riga ha la vista, le due colonne e la `fn_check` vive; e la vista chiama la stessa `fn_check` della madre (dal viewdef) |
| BE | richiesta: la query dei gruppi legge le colonne dalla vista e smette di comporle |
| FE | richiesta: il pulsante di riga legge motivo e chiave dalle colonne nominate dal registro (un BB, non un pulsante per azione) |

`reset_lotto_fattura_draft` (l'altra azione per riga del lotto) si iscrive nel registro solo se ha già una sede in
riga; se non ce l'ha, resta fuori dal giro e si annota.

### 15.11 Scritto (2026-10-27): le origini e il registro delle azioni di riga

Provato in transazione sullo scratch (`zeroerp_ruoli`, giro 11 già applicato) e, per il lettore e la vista, sui dati di
dbdev con una copia `pg_temp` in transazione annullata. **Applicato su dbdev** (Tid, 2026-10-27; `databasechangelog`
letto lo stesso giorno): pgTAP verdi, compresi il presidio dei lock dopo il migrate e gli otto file della
concessione rossi sullo scratch (§15.7); nessuna regressione.

| changeSet | cosa |
| --- | --- |
| `00_schema/config/20261027-21` | `config.sorgenti.citato_in_fattura boolean NOT NULL DEFAULT false`; i valori nel CSV `sorgenti.csv` (mirror `20251002-21`, colonna aggiunta in place) |
| `20_code/vendite/20261027-22` | `vendite.fn_fattura_origini(p_fattura_id)`, INVOKER, STABLE |
| `00_schema/config/20261027-23` | `config.azioni_riga`, il registro |
| `20_code/vendite/20261027-24` | `vendite.vw_lotti_gruppi_azioni`, security_invoker, GRANT SELECT all'app |
| `80_data/changelog/20261027-25` | seed del registro dal CSV `azioni_riga.csv`: `ESCLUDI_DOCUMENTO_DA_GIRO` |

pgTAP nuovi: `vendite/test-fattura-origini-v1` (10/10) e `config/test-azioni-riga-registro-v1` (7/7; provato anche
contro un registro sbagliato: rossi i test 3, 5 e 6). Regressione sullo scratch, prima e dopo l'SQL del giro (365 file: i
presidi trasversali e ogni pgTAP che tocca lineage, `config.sorgenti`, perimetro ed esiti dei lotti): **nessun file
cambia esito** (294 verdi prima e dopo). Unico rosso nuovo, atteso: `dbops/test-lock-columns-convergenza` test 4
(`config.azioni_riga CREA`), il trigger di lock su `codice_interno` lo monta l'automazione dopo il migrate, come per
`config.stati_lotto_job`. Guardrail CI verdi; `guardrail_pgtap_preambolo` rosso su
`config/test-grammatica-presidio-tipo-documento-v1` (committato, non di questo giro), e chiede di abbassare la soglia
dei `throws_ok` senza discriminante a 112. Sette pgTAP del giro 10 portati: la concessione di
`cambia_stato_commessa` all'operatore (§15.7). Documentazione: le pagine manuali di `fn_fattura_origini`,
`vw_lotti_gruppi_azioni`, `azioni_riga`, la colonna in quella di `sorgenti`; la guida del modello (§6, §7); le linee
guida SQL §12.5.7, il registro.

**Scostamenti dal piano, dichiarati.**

* ⚠️ **Le origini partono dalle righe fatturate, non dalla fattura.** Il piano diceva «dal lineage all'indietro della
  fattura». Il pgTAP l'ha smentito: il lineage lega la fattura alla **commessa intera**, e risalendo da lì una fattura
  cita i documenti di **tutta** la commessa, anche quelli le cui righe sono in un'altra fattura (una commessa che
  raccoglie le bolle di più mesi le citerebbe tutte a ogni fattura). Sui dati di dbdev la fattura 23640 citava cinque
  ordini; dalle righe ne cita uno. Il lettore parte dalle righe di commessa delle attività fatturate qui (ogni riga
  porta il suo documento: livello 1) e risale il lineage da ciascuno (gli antenati: 1 + il loro livello). La chiave
  della riga (`<testata>.uid`) si traduce in quella del nodo (`key_selector`) con un join alla tabella del documento,
  letta dal registro (`config.fn_sorgente_tabella`): nessun tipo scritto nel lettore.
* **Fuori gli antenati raggiunti solo da un legame ritirato** (`is_legame_ritirato`, righe annullate): regola non
  scritta nel piano, è quella della sintesi del lineage (D-15).
* **Il lettore non restituisce la data del documento** (il piano la elencava): il lettore dei nodi non la porta, e
  aggiungerla tocca la grammatica dei nodi. Restituisce livello, tipo, etichetta, chiave e numero. Se la stampa la
  vuole, è una richiesta a parte.
* **Il presidio legge la dipendenza della vista da `pg_depend`**, non dal testo della vista: più solido.
* **`reset_lotto_fattura_draft` non si iscrive**: è un permesso del backend (`post_permission` di due rotte), senza
  una `fn_check` né una sede in riga nel database.
* **P-3 provato su due ordini, non sullo stesso ordine**: un documento sta in una sola commessa aperta alla volta
  (`fn_link_commessa_sorgente`), quindi «lo stesso documento da due commesse» non si costruisce; l'unicità la
  garantisce l'aggregazione del lettore.

**Domanda nuova per Tid — Q-F7, le origini della nota di credito.** Una nota di credito nasce da un reso (arco S) e
rettifica una fattura (arco N). Oggi fattura e reso non hanno `citato_in_fattura`, quindi la nota non li cita; la
fattura elettronica però vuole la fattura rettificata fra i riferimenti. Proposta del team DB: `citato_in_fattura` a
`true` anche su FATTURA e RESO_VENDITA. Il lettore oggi parte dalle righe di commessa, e le righe di una nota non ci
passano: andrebbe aggiunto il ramo delle righe rettificate (`fatture_righe.riga_rettificata_id`). Non scritto.

**Q-F7 decisa da Tid (2026-10-27): sì, la nota di credito cita la fattura rettificata e il reso.** Il principio, nelle
parole di Tid: *anche se di tipo diverso, sono sempre sorgenti*. Il lettore non deve avere un ramo «della nota di
credito», ma una regola sola per ogni documento di vendita.

Ricognizione (letture su dbdev, 2026-10-27; fatti datati, non motivi). La nota arriva ai suoi documenti per due archi
del lineage, **entrambi a grana di riga**:
* **N** (fattura → nota): da `fatture_righe.riga_rettificata_id`;
* **S** (reso → nota): da `resi_righe_accrediti` → attività fatturabile → riga di fattura.

Le righe di commessa delle note (accrediti, rettifiche) sono senza sorgente: è voluto. Per questo oggi il lettore non
trova niente. L'unico arco a grana di commessa è **G** (commessa → fattura): è il motivo per cui il lettore parte
dalle righe.

**Piano P-F7 (via di Tid, 2026-10-27; la nota cita anche il DDT e l'ordine del reso):**
1. `citato_in_fattura = true` su FATTURA e RESO_VENDITA (CSV `sorgenti.csv`).
2. `vendite.fn_fattura_origini` con una regola sola:
   * **livello 1** = i genitori diretti del documento nel lineage;
   * l'arco G, che è a grana di commessa, si sostituisce coi documenti delle righe fatturate (come oggi);
   * N e S entrano come sono.

   Nessun tipo scritto nella funzione: l'eccezione è un arco, non un tipo.
3. **La risalita non attraversa G.** Dalla fattura rettificata si risalirebbe alla commessa intera, cioè al difetto
   del §15.11. Una fattura citata porta già i suoi riferimenti, quindi la nota cita lei e non i suoi antenati. Dal reso
   invece si risale per R e H (reso → DDT → ordine) come per gli altri documenti.
4. pgTAP:
   * una nota da reso (cita reso e fattura, più il DDT del reso);
   * una nota da correzione (cita solo la fattura);
   * una fattura normale invariata;
   * il caso «non attraversa G»: la fattura rettificata ha una commessa con un secondo ordine non fatturato, che la nota non cita.
5. Guida §7, pagina manuale, `sorgenti.md`.

Deciso col via: la nota cita anche il DDT e l'ordine arrivati dal reso (sono legami a grana di riga).

**Scritto (2026-10-27): P-F7.** Provato in transazione sullo scratch e, per il lettore, sui dati di dbdev con una
copia `pg_temp` in transazione annullata. **Applicato su dbdev** (Tid, 2026-10-27, `-26` EXECUTED alle 17:25 col CSV
`sorgenti.csv`): pgTAP verdi, compresi `test-fattura-origini-nota-v1` e `test-fattura-origini-v1`, nessuna
regressione.

| changeSet / file | cosa |
| --- | --- |
| `20_code/vendite/20261027-26-update-fn-fattura-origini-sorgenti-di-ogni-tipo-mctit.yaml` | `vendite.fn_fattura_origini`: livello 1 = genitori diretti di ogni tipo (G sostituito dalle righe fatturate); risalita senza G e solo per legami vivi. Stessa firma (`CREATE OR REPLACE`) |
| `80_data/sql/config/sorgenti.csv` | `citato_in_fattura = t` su FATTURA e RESO_VENDITA (il mirror `20251002-21` è già `runOnChange`) |
| `db/pgtap/vendite/test-fattura-origini-nota-v1.sql` | nuovo, 8 test: nota da reso, nota di sola correzione, fattura ordinaria, la risalita che non attraversa G |
| `db/pgtap/vendite/test-fattura-origini-v1.sql` | test 2: l'insieme citato ora ha sette tipi |

Risultati:
* scratch: `test-fattura-origini-nota-v1` 8/8, `test-fattura-origini-v1` 10/10;
* mutante (risalita **attraverso** G): rossi i test 3, 4 e 7, e la nota cita le altre bolle e gli altri ordini
  della commessa. ⚠️ Il primo mutante lasciava verde il 4: la bolla DB era legata alla commessa senza righe,
  quindi con un legame ritirato, e la scartava il filtro dei legami vivi, non quello su G. Ora DB ha una riga
  viva sulla commessa e la precondizione del test esige il legame vivo;
* dbdev (`pg_temp`, letto il 2026-10-27): la nota 20024, che oggi non cita nulla, cita la fattura 835 e il reso 24
  (livello 1), il DDT 140 (2) e l'ordine 240 (3). Fuori gli ordini 174 e 631 e il preventivo, raggiungibili solo
  dalle commesse della fattura 835. Su 25 fatture ne cambia una sola, la nota;
* guardrail CI verdi, tranne il preambolo, rosso su un file committato che non è di questo giro (§15.11).

Scostamento dichiarato: la regola «solo legami vivi» ora vale sul **cammino** (ogni legame della risalita è vivo).
Prima bastava che il documento avesse **un** legame vivo, anche se gli si arrivava da uno ritirato. È più stretta e
più giusta; i test del `-22` restano verdi.

Doc: la pagina manuale `fn_fattura_origini` (la regola, l'esempio della nota), `sorgenti.md`, la guida §7.
Ricadute BE/FE: nessuna nuova. BE-1 legge la stessa funzione, che ora risponde anche per le note.

Resta: il commit del giro DB 11 (Tid).

#### 15.11.1 Richiesta al team BE (elenco chiuso, dopo l'apply)

| # | cosa | dove |
| --- | --- | --- |
| BE-1 | Stampa e dettaglio della fattura leggono le origini da `vendite.fn_fattura_origini(fattura_id)` (livello, tipo, etichetta, chiave, numero), nell'ordine in cui arrivano | servizio della stampa fattura, serializer del dettaglio |
| BE-2 | La query dei documenti del lotto legge `uscita_blocco_reason`, `uscita_blocco_reason_key` e `n_trascinati` da `vendite.vw_lotti_gruppi_azioni` (`LEFT JOIN` su `lotto_id`, `gruppo_key`) e toglie la `LATERAL` su `script.fn_check_documento_escludibile_da_giro` e la chiamata a `script.fn_gruppi_trascinati_da_uscita`; nomi delle colonne invariati | `vendite_repository.py` (query dei gruppi), con `test_lotto_gruppi_service`, che oggi cerca `AS uscita_blocco_reason` nell'SQL |
| BE-3 | Il registro `config.azioni_riga` arriva al frontend in sola lettura (codice, colonna del motivo, colonna della chiave), nella forma che il team BE sceglie (endpoint o configurazione della lista) | — |

#### 15.11.2 Richiesta al team FE (dopo BE-3)

* FE-1: un BB del pulsante di riga che, dato il codice dell'azione, legge dal registro le due colonne e da quelle il
  tooltip e lo stato del pulsante; «togli dal giro» è il primo consumatore. Le azioni per riga degli altri documenti
  si aggiungono con una riga di registro e la loro vista, senza un pulsante nuovo.

### 15.12 Revisione delle guide contro il giro 11 (2026-10-27)

Richiesta di Tid: le guide della fatturazione sono allineate al giro? Ci sono regole che lo contraddicono? Lette la
guida della fatturazione, quella dei cruscotti, quella del modello, le linee guida SQL §12.5, le pagine manuali e le
pagine API del lotto. Via di Tid alle correzioni; la prima dopo la spiegazione del perché (2026-10-27).

| # | Dove | Che cosa non tornava | Fatto |
| --- | --- | --- | --- |
| 1 | guida della fatturazione, «Rollback di step», punto 5 | dice che l'annullo chiude il lotto con `stato_lotto = COMPLETATO` | ✅ (Tid, 2026-10-27) l'annullo non scrive `stato_lotto` dal 2026-09-07 (`20260907-08`, brief-db-esito-gruppo-lotto §24), per scelta: la guida era vecchia, non la funzione. Il punto 5 ora dice ANNULLATA dal verbo del lotto, CHIUSO, e lo stato del job lasciato com'era, col perché |
| 2 | guida dei cruscotti §7.6 | le tre vie d'uscita non dicono chi le può usare | il paragrafo «Chi le può usare»: «riporta in lavorazione» col permesso di numerare, l'annullo col solo permesso sui lotti, il pulsante nascosto a chi non ce l'ha |
| 3 | guida della fatturazione, la nota di credito | gli archi N e R sì, l'arco S (reso → nota) no; le origini della nota non rimandate | l'arco S e il rimando al §7 della guida del modello |
| 4 | guida del modello §8 | «ogni documento ha un verbo d'annullo»: la fattura no (F-3) | l'eccezione, detta nel §8 |
| 5 | linee guida SQL §12.5.1, §12.5.4 | «una colonna» per il motivo di riga; il registro ne vuole due (`reason`, `reason_key`) | allineate al §12.5.7 |
| 6 | guida del modello, regole 3 e 5 | — | nessuna contraddizione: lo stato del job è dichiarato «non stato del documento», la fattura fuori da «Emetti» è dichiarata al §7 |
| 7 | pagine manuali `azioni_processo`, `user_override_azioni` | le azioni ritirate senza «ritirata»; esempi con azioni ritirate | segnate ritirate; esempi con azioni vive |
| 8 | commenti nel DB | il corpo di `fn_annulla_lotto_da_draft` e il COMMENT di `trgfn_fatturazione_lotti_guard_completato` citano come regola viva `fn_set_fatturazione_lotto_stato`, ritirata dal `-07` | `20261027-27` (corpo del `-15`, cambiano solo i commenti) e `20261027-28` (solo il COMMENT, dal testo vivo letto su dbdev) |
| 9 | pagine API del lotto (team BE) | il CHECK ritirato, la matrice Python, il permesso ritirato | aggiunte al punto 7 del §15.8 |

Prova di `-27` e `-28`: sullo scratch, SQL estratto in transazione annullata: il codice della funzione, tolti i
commenti e gli spazi, è identico a prima; il suo COMMENT è invariato; quello del guard è il nuovo. **Applicati su dbdev** (Tid, 2026-10-27, 17:55): il corpo porta la rev del `-27`, il COMMENT del guard quella del `-28`.
`ERRORE → COMPLETATO` resta vietato anche nella matrice nuova (CSV `transizioni_stati_lotto_job`, letto il
2026-10-27): il commento lo dice.

Resta, non toccato: la sorella `fn_riporta_lotto_a_draft` dice nel corpo «stato_lotto NON si tocca — ha una macchina
a stati cablata»; la regola non è più cablata ma in tabella. Il senso resta giusto; un ritocco solo di commento,
se Tid lo vuole.

### 15.13 Lo stato iniziale dalla testata (richiesta del team BE, 2026-10-27; ✅ Tid: via, K-3 nello stesso giro)

**La richiesta.** Il §15.8 punto 3 chiede «riporta in bozza» del lotto dalla riga del passaggio
(`fn_doc_azione_passaggio(testata, id, stato_a)`), e lo stato d'arrivo è lo stato iniziale. Lo leggeva solo
`script.fn_stato_iniziale_id(vocabolario)`: chi ha la testata avrebbe dovuto ricavare il vocabolario dalla mappa da
sé (la composizione ritirata dal backend al §8.7 punto 3) o scrivere `'DRAFT'`. Un buco di questo elenco, non del BE.

**Censimento dei chiamanti** (`pg_get_functiondef` sullo scratch, 2026-10-27). Di `fn_stato_iniziale_id` con un
vocabolario scritto accanto a una testata della mappa (copia della mappa): i nove builder pgTAP. Restano sul lettore
dal vocabolario, perché non hanno una testata della mappa: `script.trgfn_doc_stato_iniziale` (il vocabolario è un
argomento del trigger, montato anche sugli acquisti, fuori mappa) e `vendite.fn_push_preventivo_a_ordine` (lo stato
delle RIGHE dell'ordine, `ordini_righe.stato_doc_ordine_id`; la proposta in chat la contava fra le copie: sbagliato).

**Scritto.**

| # | changeSet | Che cosa |
| --- | --- | --- |
| K-1 | `20261027-29` | `script.fn_doc_stato_iniziale_id(regclass)`: vocabolario dalla mappa, fuori mappa `E_SCRIPT_CHIAMATA_NON_VALIDA`, la regola delegata a `fn_stato_iniziale_id` (NULL se non dichiarato). STABLE, SECURITY INVOKER. Nessun codice d'errore nuovo |
| K-3 | `20261027-30` … `-38` | i builder `fn_pgtap_crea_preventivo`, `_preventivo_con_righe`, `_ordine`, `_ordine_con_righe`, `_ddt_da_ordine`, `_ddt_senza_ordine`, `_ddt_riconsegna`, `_commessa`, `_fattura` leggono lo stato iniziale dalla testata. Corpo dall'ultimo YAML (firma coi `%TYPE`), verificato uguale al corpo vivo; cambia solo quella chiamata; COMMENT con la riga «Rev» |
| — | `20261027-39` | solo il COMMENT di `fn_stato_iniziale_id`: consumatori di oggi (citava `fn_pgtap_porta_a_stato`, che non la chiama) e il rimando al lettore dalla testata |
| K-4 | pgTAP `script/test-doc-stato-iniziale-id-v1` | 6 test: forma; il lotto → lo stato iniziale di `config.stati_doc_fiscale`; le nove testate della mappa = `fn_stato_iniziale_id(vocabolario)`, mai NULL; fuori mappa e NULL → chiamata non valida; vocabolario senza iniziale → NULL |
| K-5 | doc | pagina `manual/fn_doc_stato_iniziale_id`; guida del modello (Vedi anche, §4); §15.8 punto 3 |

**Applicato su dbdev, pgTAP verdi** (Tid, 2026-10-27).

**Prova** (scratch `zeroerp_ruoli`, owner, SQL estratto in transazione annullata, 2026-10-27): il pgTAP nuovo 6/6.
Regressione sui 178 pgTAP che usano i nove builder, ciascuno senza e con l'SQL estratto: piano, ok e not ok identici
in tutti; 13 file hanno rossi, gli stessi nelle due corse e tutti dichiarati «rosso da owner» (porta, GUC, scope
RLS), in coda ai file e dopo le fixture.

**Al team BE, dopo l'apply** (come da richiesta): `DocumentoModelloRepository.stato_iniziale(testata)` su
`script.fn_doc_stato_iniziale_id`, e `PassaggioDocumento(stato_del_modello="iniziale")` su `ApiRiportaLottoADraft`
(§15.8 punto 3).

### 15.14 I passaggi permessi per riga di lista (richiesta del team BE, 2026-10-27; ✅ Tid: D-1 … D-4 come da proposta, via)

**La richiesta.** La lista dei lotti non sa se l'operatore ha l'azione di un passaggio: il kebab propone «Numera»,
«Riporta in lavorazione», «Annulla» a tutti, e il rifiuto arriva al clic. Completa, non revoca, la risposta del
2026-08-04 (`work-done/risposta-db-azioni-lista-lotto` §3.3): il punto 2 («la riga ha già la verità che serve, lo
stato») è caduto col `-19`, che legge il permesso dalla riga del passaggio; restano il punto 1 (niente capability
intera per riga) e il punto 3 (il lettore è STABLE e non chiama `fn_check_*`).

**Ricognizione.** Il predicato «passaggi manuali vivi dallo stato corrente, permesso => nascondi» era scritto in
tutte e otto le `script.fn_available_actions_*` di vendita: il lettore chiesto sarebbe stato la nona copia. Le copie
divergevano già sul default di `meta.manuale` mancante (`fn_doc_passaggio`, i `ck_*_meta_ui` e la bolla:
manuale; lotto e commessa: di processo), e la capability del lotto filtrava anche `meta.tipo_lotto` contro la colonna
del documento, condizione che un lettore generico non vede. Il permesso dipende da utente e azione, non dal
documento.

**Decisioni (Tid, 2026-10-27).** D-1: la firma riceve lo STATO (`p_stato_da_id`), non il documento. D-2: le otto
capability passano al lettore nello stesso giro (regola del 2). D-3: vincolo, `meta.manuale` booleano dichiarato su
ogni riga delle otto matrici. D-4: vincolo, `meta.tipo_lotto` solo sui passaggi di processo.

**Scritto.**

| # | changeSet | Che cosa |
| --- | --- | --- |
| K-1 | `20261027-40` | `script.fn_doc_azioni_permesse(p_testata regclass, p_stato_da_id bigint)` → `TABLE(stato_a_id, stato_a_codice, action_key, azione_processo_codename, meta)`, STABLE, INVOKER: matrice viva e filtro dalla mappa, manuale e azione da `fn_doc_passaggio`, permesso => nascondi (azione NULL resta). Stato NULL: nessuna riga; fuori mappa `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| K-2 | `-41` … `-48` | le otto capability leggono da K-1 (corpo dall'ultimo YAML, verificato uguale al vivo); restano loro il bottone (`action_key`, `label_key`), abilitazione e motivi, l'ordine. Il lotto ritira il filtro `tipo_lotto` (D-4) |
| K-3 | `-49`, `-50` (`90_end`) | D-3 su otto matrici (`ck_<matrice>_meta_manuale_dichiarato`) e D-4 (`ck_stati_doc_fiscale_transizioni_tipo_lotto_solo_processo`); in `90_end` perché le righe le scrive il seed |
| K-4 | pgTAP `script/test-doc-azioni-permesse-v1` | 11 test: forma; lotto EMESSA senza/con `numera_fatture_lotti` ({} / {numera, riporta_a_draft}); DRAFT → annulla senza azione e senza concessioni; equivalenza col predicato di prima su ogni stato delle otto testate, senza e con la concessione; stato NULL; fuori mappa; i due vincoli |
| K-5 | doc | pagina `manual/fn_doc_azioni_permesse`; guida del modello (Vedi anche, §5 la dichiarazione di manuale, §6 capability e liste) |

**Due difetti trovati in prova, corretti prima dell'apply riuscito.** Il CHECK di `-49` scritto
`jsonb_typeof(meta -> 'manuale') = 'boolean'` lasciava passare la riga senza chiave (NULL ⇒ il CHECK passa): l'ha
visto il test 10, ora `jsonb_exists(meta, 'manuale') AND …`. E l'operatore `?` fuori da un corpo dollar-quoted:
l'apply di Tid si è fermato su `-49` («errore di sintassi a "$1"», il driver JDBC lo legge come segnaposto); ora
`jsonb_exists` in `-49` e `-50`. Il `-49` fallito non aveva lasciato vincoli.

**Applicato, pgTAP verdi** (Tid, 2026-10-27).

**Prova** (scratch `zeroerp_ruoli`, owner, SQL estratto in transazione annullata, 2026-10-27): pgTAP nuovo 11/11.
Regressione su 78 file (chi tocca le otto capability, le matrici, `fn_doc_passaggio`, il permesso, più i presidi
trasversali: riferimenti morti, catalogo messaggi, rubinetto del primo motivo, catalogo presidi): piano, ok e not ok
identici prima e dopo in tutti. L'apply di Tid (`-40` … `-48`, 19:39) è caduto a metà corsa: per i 36 file rimasti
lo stato «prima» è stato ricostruito in transazione (gli otto corpi vecchi, senza il BB). I rossi sono gli stessi
nelle due corse: «rosso da owner» (porta, GUC, scope RLS) e fixture che pescano cliente o utility dai dati
(`billing_account`/`utility_id` obbligatori sullo scratch).

**Al team BE, dopo l'apply.** La lista dei lotti chiama `script.fn_doc_azioni_permesse('vendite.fatturazione_lotti',
l.stato_doc_fiscale_id)` per riga (lo stato della riga, non l'id: D-1) e porta `azioni_permesse` (le `action_key`);
il kebab propone i verbi di stato solo se compaiono lì. Le altre liste possono adottarlo uguale, con la loro testata.
Nessun codice d'errore nuovo. Le capability del dettaglio non cambiano contratto.

### 15.15 Fatto dal team BE e FE (2026-10-27): §15.8, BE-1 … BE-3, FE-1

Sul giro DB 11 già in `dev/backend-tid` (merge #1964). Da committare (Tid).

| # | Che cosa | Dove |
| --- | --- | --- |
| §15.8.1 | Lo stato dello step dal verbo di processo: `update_lotto_stato_doc` chiama `vendite.fn_lotto_proietta_stato_step`, negli stessi punti del runner | `pipeline_repository.py` |
| §15.8.2 | `set_lotto_job_stato` tiene `UPDATE`, nota in `meta` e no-op sullo stesso stato; la copia della regola (tre valori, passaggi) è ritirata: decidono la FK e il guard | `pipeline_repository.py` |
| §15.8.3 | «Numera» di un lotto: `PassaggioDocumento` (testata `vendite.fatturazione_lotti`, arrivo `STATO_DEFINITIVA`, una costante sola per i tre letterali `'DEFINITIVA'` di service e handler). L'annullo della bozza: solo il livello sul documento. ⏸️ **«Riporta in bozza»: non fatto**, vedi sotto | `views.py`, `pipeline_service.py`, `fatturazione_numera_handler.py` |
| §15.8.4 | Nessun riferimento alle quattro azioni ritirate come permesso (resta il nome del task di pipeline `reset_lotto_draft`, che è un'altra cosa); esempi nei commenti FE portati a `numera_fatture_lotti` | BE e FE |
| §15.8.5 | `LOTTO_AZIONE_PERMESSO` tiene i soli tre verbi di pipeline; il parametro `permission` di `mapAvailableActionsToDrawerActions` ritirato (ok Tid, §14.7) | `useLottoAzioni.js`, `LottoDrawer.vue`, `useDrawerActions.js` |
| §15.8.6 | Test portati: repository (regola del job → «non giudica», verbo dello step), API dell'annullo (livello sul documento), dichiarazioni dei due «numera», `test_permissions`; smoke `ritorno-lotto-a-draft` e `fattura-indirizzi-snapshot` (scrivevano lo stato con un `UPDATE`: ora dai verbi) | `apps/*/tests`, `scripts/tests` |
| §15.8.7 | Doc API del lotto: permessi per passaggio | `api_reset_lotto_draft.md`, `api_fatturazione.md` |
| BE-1 | Il dettaglio della fattura porta `origini` da `vendite.fn_fattura_origini` (ordine della funzione, fissato con `WITH ORDINALITY`); ⏸️ **la stampa no**, vedi sotto | `vendite_repository.list_fattura_origini`, `vendite_service`, `fatture_views` |
| BE-2 | La query dei gruppi legge le tre colonne da `vendite.vw_lotti_gruppi_azioni`. ⚠️ Col filtro **costante** sul lotto (`(SELECT id FROM lotto)`): col join su `gr.lotto_id` la `UNION` della vista non riceveva il filtro e la check girava su ogni gruppo di ogni lotto visibile (EXPLAIN su dbdev, 2026-10-27) | `vendite_repository.py` |
| BE-3 | Lookup dedicato `GET /core/lookup/azioni-riga/` (non il generico: niente `codice`, due colonne in più) | `views_lookup.py`, `lookup_repository.py`, `api_azioni_riga_lookup.md` |
| FE-1 | BB `useAzioneRiga(codice)`: colonne dal registro, fail-closed; «togli dal giro» nelle sue tre superfici; `motivoUscitaBloccata` ritirata | `core/composables/useAzioneRiga.js` |

**Prove (2026-10-27).** Test Django dei moduli toccati: 215 verdi, più la lettura del registro sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`). Vitest: 179 verdi. Lint (ruff, eslint, oxlint), guard FE e cricchetto mypy: puliti. Sul DB vero, in transazione annullata: le origini della nota 20024 sono quelle del §15.11 (fattura 835, reso 24, DDT 140, ordine 240); il verbo dello step rifiuta lo stato iniziale e il guard del job uno stato fuori vocabolario, coi codici del DB. Smoke `ritorno-lotto-a-draft`: il giro avanza DRAFT → EMESSA dal verbo nuovo (caso 6). Gunicorn ricaricato. ⚠️ Suite completa **non** rilanciata.

**Dopo il merge del §15.13 (2026-10-27), in più.**

* `STATI_LOTTO`, lo specchio Python del CHECK `chk_fatturazione_lotti_stato_job`, ritirato: il CHECK non c'è più dal `-05`, e il presidio `test_specchi_dei_check_db` lo cercava ancora (sarebbe stato rosso sul DB provvisto). Il filtro `stato_lotto` della lista lotti legge `config.stati_lotto_job` con `richiedi_codice_a_vocabolario`. Pagine API `api_lotti_list.md`, `api_run_lotto_pipeline.md` (punto 7, aggiunte del §15.12).
* Il «da provare» del §14.8: la suite completa, rilanciata, aveva **un** rosso — `test_ddt_service.test_cambia_stato_ddt_not_found`, della revisione del §14.8: la classe non montava il mock del modello e il service interrogava il DB. Corretto (`ModelloDocumentoMockatoMixin`). Suite completa: 6474 test, verde; sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`) 7003 test, verde dopo una correzione: la colonna nuova `config.sorgenti.citato_in_fattura` (`-21`) non aveva l'etichetta del pannello di configurazione (`config_panel.campi`, it ed en; presidio `test_config_panel_registro_db`). Vitest: 980, verde.

**Fermi, tornano a Tid.** (Esito: D-S1 e D-S2 al §15.16.)

* ✅ **«Riporta in bozza»: fatto dopo il §15.13** (2026-10-27). `DocumentoModelloRepository.stato_iniziale(testata)` su `script.fn_doc_stato_iniziale_id`; `PassaggioDocumento(stato_del_modello="iniziale")` su `ApiRiportaLottoADraft`, via il `post_permission`. Provato sul DB vero: da un lotto EMESSA la riga chiede `numera_fatture_lotti`, da un lotto in bozza nessuna azione (decide il livello). Presidi: `test_passaggio_rotte` (le due rotte del lotto attese, e ogni rotta verso lo stato iniziale lo trova sul DB), `test_permesso_passaggio` 14, `test_permesso_passaggio_db` 11. Nessun `'DRAFT'` per dire «lo stato in cui si nasce» resta nel backend: quelli che restano dicono altro (stati modificabili dei service; la coppia DRAFT/EMESSA del runner = gli step pre-fiscali da rifare, candidata a `congela_fiscale`, fuori dal giro per F-4).
* **BE-1, la stampa: una forma nuova del contesto.** Il builder porta `origine` (un oggetto, sempre vuoto: D-G1) e il modello standard stampa `fattura.origine.tipo`. Un elenco al suo posto è una chiave cambiata, cioè `CONTEXT_VERSION` 6, e il contratto del builder vuole che **nello stesso giro** nasca la versione del modello che la legge (seed del modello standard, team DB; e le versioni pubblicate su dbdev). Senza, la stampa si ferma sul guard della forma. Da decidere: forma 6 col modello (proposta del team BE), oppure `origini` in più accanto a `origine` senza cambiare forma, che lascia viva la chiave vuota.
* **Una seconda superficie di «togli dal giro» fuori dal registro.** La lista delle segnalazioni del lotto (`pipeline_repository.list_lotto_segnalazioni`, scheda Critiche) compone ancora `uscita_blocco_reason` chiamando la check nel backend. La check è la stessa, quindi il motivo non diverge; ma il presidio del registro non vede questa superficie. Non portata alla vista: le righe delle segnalazioni non sono per costruzione le righe di `vw_lotti_gruppi_azioni` (perimetro ∪ esiti), e un `LEFT JOIN` vuoto direbbe «ammessa». Domanda per il team DB: una superficie registrata per le segnalazioni, o la vista che le copre.
* **Kebab della lista lotti.** Tolto il permesso dalla mappa FE (§15.8.5), «Numera», «Riporta in lavorazione» e «Annulla» compaiono nel kebab anche a chi non ha l'azione; al clic `eseguiVerificato` rilegge la capability, che li nasconde, e avvisa «azione non più disponibile». Nessun gesto passa, ma la frase non dice «non hai il permesso». ✅ **Tid, 2026-10-27: si sistema con un lettore DB leggero.** Richiesta al team DB (data in chat): `script.fn_doc_azioni_permesse(p_testata, p_id)`, generico, gemello di `fn_doc_azione_passaggio` — i passaggi manuali dallo stato corrente che l'operatore può fare (`stato_a_codice`, `action_key` da `meta`, azione), con lo stesso predicato del permesso di `fn_available_actions_lotto` (`-19`), **senza** `fn_check_*`. Completa, non revoca, la scelta del 2026-08-04 (risposta-db-azioni-lista-lotto §3.3: niente capability intera per riga): lì «la riga ha già la verità che serve» era lo stato, e col permesso dalla riga del passaggio lo stato non basta più. Poi il BE porta `azioni_permesse` in riga nella lista lotti e il kebab propone i verbi di stato solo se compaiono lì (fail-closed). ✅ **Fatto dal team DB** (§15.14, `-40` … `-50`, applicato e verde): la firma riceve lo stato, non l'id (D-1), `fn_doc_azioni_permesse(p_testata, p_stato_da_id)`. ✅ **Fatto dal team BE e FE** (2026-10-27, 4-bis-duodecies-octvicies):
  * BE: `azioni_permesse` (le `action_key`, ordinate; mai `null`) in coda a `_LOTTO_SELECT_COLS`, quindi in lista **e** nella testata del dettaglio, con `ARRAY(SELECT … FROM script.fn_doc_azioni_permesse(...))` nella proiezione: gira sulle sole righe della pagina, non entra nel `COUNT`. Misurato su dbdev: 101 lotti in ~40 ms, come prima. `TESTATA_LOTTI` spostata da `pipeline_repository` a `vendite_repository`, accanto alla lettura del lotto: l'import inverso era un ciclo (`pipeline_repository` → `commesse_repository` → `vendite_repository`). Pagina `api_lotti_list.md`.
  * FE: `verbiPlausibili` prende i verbi di stato da `azioni_permesse`, solo le chiavi con una chiamata in `VERBI` e non di pipeline; campo assente → nessun verbo (fail-closed). `lottoNumerabile` (la casella di selezione) resta sullo stato: la numerazione di più lotti ha il suo `post_permission`. La ristampa resta su DEFINITIVA: non è un passaggio.
  * Rifinitura dello stesso giro: la ristampa nel kebab non confronta più il codice dello stato con un `'DEFINITIVA'` scritto nel frontend, legge `ristampabile` della riga (posizione 29: lo stesso predicato con cui `ristampa_lotto` accetta, sulla costante `STATO_DEFINITIVA`, spostata accanto a `TESTATA_LOTTI` in `vendite_repository` per lo stesso ciclo d'import); fail-closed. Test nuovo `test_lotto_job_stato_db` (§15.8.2 sul DB vero: lo stato del job fuori vocabolario lo rifiuta il guard, col codice).
  * Presidi: `test_lotto_row_mapping` (posizione 28), `test_lotto_azioni_permesse_db` (nuovo, gli esempi del pgTAP via `get_lotto` e `list_lotti`, operatore senza e con `numera_fatture_lotti`), `useLottoAzioni.spec.js` (nuovo, sei casi). Suite Django sul DB provvisto 7013, vitest 988 (rilanciate prima del commit, 2026-10-27), ruff/eslint/mypy puliti; gunicorn ricaricato.

### 15.16 Richiesta al team DB: la stampa delle origini in forma 6, e D-S2 (team BE, 2026-10-27)

**Decisioni di Tid (2026-10-27).**

* **D-S1 = forma 6.** La fattura stampata porta la catena dei documenti di origine (`vendite.fn_fattura_origini`,
  la stessa del dettaglio, BE-1) **al posto** della chiave `origine`, che oggi è sempre vuota (D-G1). Non la via
  «`origini` accanto a `origine`»: lascerebbe nella stampa una chiave morta che sembra un dato.
* **D-S2.** La superficie delle segnalazioni del lotto (scheda Critiche) fuori dal registro: Tid concorda che la
  forma è del team DB (vedi §15.16.2).

#### 15.16.1 Che cosa serve al team DB (forma 6)

È il precedente dell'ordine in forma 3 ([brief-db-grammatica-unica-documenti §12.10](../work-done/brief-db-grammatica-unica-documenti.md)),
con la regola dei modelli standard (Q-5: i changeSet di evoluzione scrivono **solo** sullo standard).

**La forma 6 del contesto fattura** (la fissa il BE, è il contratto che il modello legge):

| Chiave | Forma 5 (oggi) | Forma 6 |
| --- | --- | --- |
| `fattura.origine` | `{codice, tipo}`, sempre `None` / `None` | **tolta** |
| `fattura.origini` | — | lista, nell'ordine di `vendite.fn_fattura_origini`; ogni elemento `{livello, tipo, etichetta, codice}` (`tipo` = `tipo_codice_interno`, `etichetta` = `config.sorgenti.etichetta`, `codice` può essere `None`); `[]` se la fattura non cita niente |

Il resto del contesto non cambia. Il render è `StrictUndefined`: un modello in forma 5 che legge `fattura.origine`
fallirebbe, ed è il motivo della forma nuova.

**R-S1 — changeSet `80_data`: lo standard «Fattura di vendita» (`FATTURA_VENDITA`), versione 2.** Copia della
pubblicata valida oggi (su dbdev la versione 1, id 3365, forma 5, letto il 2026-10-27), con la sola sezione
«Origine documento» sostituita: oggi è il blocco `{% if fattura.origine.tipo or fattura.origine.codice %}` …
`{% endif %}` (cinque occorrenze di `fattura.origine.`, seed `20261020-18`). Proposta di corpo (il team DB ne
decide la grafica):

```jinja
{% if fattura.origini %}
  <section class="section">
    <div class="label">Documenti di origine</div>
    <div class="box">
      {% for o in fattura.origini %}
        <div><strong>{{ o.etichetta }}</strong>{% if o.codice %}<span class="muted"> - {{ o.codice }}</span>{% endif %}</div>
      {% endfor %}
    </div>
  </section>
{% endif %}
```

`versione_contesto = 6`, pubblicata da `script.fn_data_operativa()`; sostituzione contata (le cinque occorrenze, né
una di più né una di meno), idempotente, ferma su una bozza già presente — come il `20261020-25`.

**R-S2 — script una tantum per le copie degli emittenti** (dati dell'applicazione, non un changeSet: come
`sql-una-tantum-l2b2-copie-ordine-forma-3.sql`). Su dbdev, letto il 2026-10-27, due copie stampano la fattura e
leggono `fattura.origine`: template 77 (versione 7, id 2334) e 2527 (versione 7, id 3097), entrambe in forma 5.
Dopo il riavvio del BE in forma 6 non stampano più (409 `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`) finché non hanno
una versione in forma 6. Lo script le cerca per criterio (modelli fattura degli emittenti la cui versione
stampata è in forma 5 e legge `fattura.origine.`), sostituisce la stessa sezione, le porta alla forma 6 e le
pubblica dalla data operativa; si ferma annullando tutto su una bozza attiva o su un conteggio diverso.

**R-S3 — pgTAP**: lo standard v2 in forma 6, pubblicato, senza `fattura.origine.` nel corpo; e la regressione.

#### 15.16.2 D-S2 — la scheda Critiche (domanda)

`pipeline_repository.list_lotto_segnalazioni` compone `uscita_blocco_reason` chiamando la check nel backend: il
motivo non diverge (la check è la stessa), ma il presidio del registro `config.azioni_riga` non vede questa
superficie. Le righe delle segnalazioni non sono per costruzione quelle di `vendite.vw_lotti_gruppi_azioni`
(perimetro ∪ esiti), e un `LEFT JOIN` vuoto direbbe «ammessa»: per questo il BE non l'ha portata alla vista.
Due strade, la scelta è del team DB: **(a)** una superficie registrata per le segnalazioni; **(b)** la vista che
copre anche le righe delle segnalazioni. Priorità bassa: oggi non sbaglia niente, è un buco nel presidio.

#### 15.16.3 La sequenza (proposta, da confermare col team DB)

1. Team DB: R-S1 … R-S3, provati in transazione.
2. Tid: apply. Da qui lo standard v2 (forma 6) non stampa finché il builder produce la 5; le copie degli
   emittenti in forma 5 stampano ancora.
3. Team BE: il builder della fattura a `CONTEXT_VERSION = 6` (`origini` da `list_fattura_origini`, `origine`
   tolta), test e doc; commit; riavvio del backend. Da qui stampa lo standard, le copie no.
4. Tid: lo script una tantum (R-S2), **subito dopo** il riavvio. Le righe di coda di stampa finite in errore nella
   finestra si rimettono in coda dalla gestione code.

⚠️ Il builder non passa alla forma 6 **prima** dell'apply: col modello in forma 5 pubblicato, ogni stampa di
fattura si fermerebbe al guard della forma (regola: il BE non va per primo sul contro-pezzo del DB).


### 15.17 Ricognizione e piano del team DB sul §15.16 (2026-10-28)

**Il percorso, censito** (doc auto-generata, changelog, pgTAP, guide; fatti di dbdev letti il 2026-10-28).

* **Chi legge `fattura.origine.`**: tre versioni pubblicate valide oggi, tutte in forma 5, nessuna bozza sui
  tre modelli. Lo standard `fattura_vendita` (template 2733, versione 1, id 3365, seed `20261020-18`) e le copie
  degli emittenti 32 (template 77, versione 7, id 2334) e 44 (template 2527, versione 7, id 3097). Cinque
  occorrenze in ognuna, tutte nel riquadro «Origine documento», e il riquadro è **lo stesso testo** nelle tre
  (stesso md5, dall'`{% if fattura.origine.tipo …` fino alla tabella delle righe). Il censimento del BE (§15.16.1)
  è confermato. Nessuna versione ha `context_schema` che nomini `origine`; nessuna copia dichiara
  `derivata_da_versione_id` (la vista dello scarto le mostra `ORIGINE_NON_DICHIARATA`, oggi come dopo).
* **La nota di credito** non ha un tipo d'output suo (`documenti.tipi_documento_output`: sei tipi, nessuna nota):
  si stampa col modello della fattura, quindi le sue origini (fattura rettificata, reso, §15.11 Q-F7) arrivano
  dalla stessa chiave `origini`, senza un pezzo in più.
* **pgTAP**: nessuno fissa la forma 5 della fattura né il testo del riquadro. **Guide**: la guida del modello
  (§«Le origini della fattura») dice già «a stampa e dettaglio»; `documenti-e-stampe.md` parla della forma in
  generale. Nessuna delle due cambia.
* ⚠️ **Lo scarto dal precedente dell'ordine** (`20261020-25`, forma 3): lì si sostituiva una **parola**
  (`ordine.origine.tipo` → `…etichetta`, contata due volte); qui si sostituisce un **blocco** (un `if` con un
  campo diventa un `for` su una lista). La sostituzione resta contata, sul blocco intero: il testo esatto del
  riquadro del seed, che deve comparire **una** volta; poi, sul risultato, zero `fattura.origine.` e una
  `fattura.origini`. Un modello ritoccato nel riquadro ferma il changeSet (o lo script) invece di pubblicare una
  copia a metà.

**Il piano (elenco chiuso).**

| # | Che cosa | Dove |
| --- | --- | --- |
| K-S1 (R-S1) | Lo standard «Fattura di vendita», versione 2: il riquadro del §15.16.1 (corpo del BE, etichetta «Documenti di origine»), `versione_contesto = 6`, pubblicata da `script.fn_data_operativa()`; copiata dalla pubblicata valida oggi, sostituzione del blocco contata, idempotente, ferma su una bozza; nella forma del `20261020-25` | `80_data/changelog/20261028-01` |
| K-S2 (R-S2) | Script una tantum per le copie degli emittenti: per criterio (modelli `FATTURA_VENDITA` non standard, attivi, la cui versione stampata oggi è in forma 5 e legge `fattura.origine.`), stesso blocco sostituito, forma 6, pubblicata dalla data operativa; si ferma annullando tutto su una bozza attiva o su un conteggio diverso; rilanciato non fa niente. Nella forma di `sql-una-tantum-l2b2-copie-ordine-forma-3.sql`; si cancella all'archiviazione | `work-in-progress/sql-una-tantum-copie-fattura-forma-6.sql` |
| K-S3 (R-S3) | pgTAP nuovo: lo standard ha una sola pubblicata valida oggi, in forma 6, che legge `fattura.origini` e non contiene `fattura.origine.`; nessuna bozza; la versione 1 non è più valida oggi | `documenti/test-template-standard-fattura-forma-6-v1` |
| K-S4 (D-S2) | La vista `vendite.vw_lotti_gruppi_azioni` copre anche i documenti nominati dal giornale del lotto: un terzo ramo dell'unione, `fatturazione_lotti_log.gruppo_key` non `NULL`. Stesse colonne, stesso ordine (`CREATE OR REPLACE VIEW`), `security_invoker` invariato | `20_code/vendite/20261028-02` |
| K-S5 (D-S2) | Il presidio del registro esteso: su un lotto costruito con una segnalazione di un documento **fuori** da gruppi ed esiti, ogni riga di `vendite.fn_list_lotto_segnalazioni` con `gruppo_key` ha la sua riga nella vista, col motivo della `fn_check` | `config/test-azioni-riga-registro-v1`, test 8 |

Prova prima dell'apply: SQL estratto di `-01` e `-02` sullo scratch, in transazione, con un secondo giro di `-01`
(idempotenza); lo script K-S2 su dbdev in transazione annullata, con un secondo giro nella stessa transazione;
regressione dei pgTAP che nominano modelli, forma dei dati, lotti e segnalazioni, prima e dopo.

⚠️ **K-S1 e K-S2 fanno la stessa sostituzione.** Non è una copia da estrarre (regola del 2): lo script è un dato
una tantum che si cancella all'archiviazione, come quello dell'ordine; il blocco vecchio e il nuovo sono
scritti nei due file, e la prova li confronta.

**D-S2, la risposta del team DB: (b), la vista copre le righe delle segnalazioni.** Il motivo è sul modello: la
vista dice «per ogni documento di cui il lotto parla, si può togliere dal giro?», e il giornale del lotto è uno
dei posti in cui il lotto parla di un documento. Oggi il dominio della vista è gruppi ∪ esiti (§15.11); col
ramo del giornale la `LEFT JOIN` della scheda Critiche è completa **per costruzione**, e il `NULL` sulle righe
del giro (`gruppo_key` vuota) resta quello di oggi. Completa la decisione del §15.10 (F-5, Q-F5 = vista DB), non
la revoca. La (a) non regge sul registro: `config.azioni_riga` ha **una** riga per azione
(`uq_azioni_riga_codice_interno`) e il BB `useAzioneRiga(codice)` la legge per codice; una seconda superficie
vorrebbe un secondo codice per lo stesso verbo, o il registro per (azione, superficie), e una seconda vista che
chiama la stessa `fn_check`: la seconda copia che il registro esiste per evitare. Il giornale ha l'indice su
`lotto_id`, quindi col filtro costante del BE (BE-2, §15.15) il ramo nuovo legge le sole righe del lotto.

**Richiesta al team BE, dopo l'apply (elenco chiuso; si aggiunge a quella del §15.16.3).**

| # | Che cosa | Dove |
| --- | --- | --- |
| BE-S1 | Il builder della fattura a `CONTEXT_VERSION = 6` (§15.16.3 punto 3): invariato | builder della fattura |
| BE-S2 | La scheda Critiche legge `uscita_blocco_reason` e `uscita_blocco_reason_key` da `vendite.vw_lotti_gruppi_azioni` (`LEFT JOIN` su `gruppo_key`, filtro costante sul lotto come in BE-2) e ritira la `LATERAL` su `script.fn_check_documento_escludibile_da_giro`; nomi e posizioni delle colonne invariati | `pipeline_repository.list_lotto_segnalazioni` |

La sequenza del §15.16.3 è confermata: K-S4 e BE-S2 non hanno vincoli d'ordine (la vista estesa non cambia
niente per chi la legge oggi), e viaggiano nello stesso apply e nello stesso passaggio BE.

**Domande per Tid.** D-S2 = (b), come sopra? E il via allo sviluppo di K-S1 … K-S5. ✅ Tid, 2026-10-28: sì a entrambe.

#### 15.17.1 Scritto e provato (2026-10-28; ✅ Tid: D-S2 = (b), via)

| File | Che cosa |
| --- | --- |
| `80_data/changelog/20261028-01-template-standard-fattura-vendita-origini-forma-6` | K-S1: lo standard «Fattura di vendita» v2, forma 6, «Documenti di origine» (il corpo del §15.16.1); i due blocchi composti riga per riga (`array_to_string`), così spazi e a capo non dipendono dall'indentazione del YAML |
| `20_code/vendite/20261028-02-update-vw-lotti-gruppi-azioni-documenti-del-giornale` | K-S4: il ramo del giornale (`gruppo_key` non `NULL`, disabilitate comprese); `security_invoker` riscritto, GRANT e COMMENT; il rollback torna al corpo del `20261027-24` |
| `work-in-progress/sql-una-tantum-copie-fattura-forma-6.sql` | K-S2: lo script per le copie degli emittenti (si lancia **dopo** il riavvio del BE in forma 6, §15.16.3 punto 4) |
| `db/pgtap/documenti/test-template-standard-fattura-forma-6-v1.sql` | K-S3, nuovo, 6 test |
| `db/pgtap/config/test-azioni-riga-registro-v1.sql` | K-S5: test 8, su un lotto costruito con una segnalazione di un documento fuori da gruppi ed esiti (e una del giro, che non conta) |
| `dbzero/vendite/manual/vw_lotti_gruppi_azioni.md` | il dominio della vista, le due letture del BE |

**Prove.**

* **Scratch `zeroerp_ruoli`, come owner, transazione annullata**: SQL estratto dei due changeSet (dal YAML, non
  riscritto), con il `-01` lanciato due volte. Lo standard passa a v1 `OBSOLETA` `[2000-01-01, 2026-10-28)` e v2
  `PUBBLICATA` forma 6 dal 2026-10-28, zero `fattura.origine.`; il secondo `-01` non fa niente (idempotente). La
  vista resta `security_invoker`, l'app la legge.
* **pgTAP, senza e con l'SQL del giro** (dopo la riga `BEGIN;`): il nuovo 2/6 → 6/6; il registro 7/8 → 8/8 (il
  test 8 è rosso senza il ramo del giornale).
* **Regressione**: 39 file che nominano modelli, forma dei dati, lotti, giornale, segnalazioni, registro: cambiano
  solo i due di questo giro. Sei rossi già presenti, **le stesse asserzioni** prima e dopo: test di RLS e di scope
  rossi da owner per costruzione (`test-documenti-generati-eventi` 16, `test-documenti-template-standard-app-v1`
  1-5, `test-annullamento-chiude-la-vita-v1`, `test-lotti-fermi-verdetto-a-db-v1`), `test-uscita-documento-dal-giro-v1`
  (un errore senza un `not ok`), `test-vw-giornale-entita` (si ferma su `p_tipo_doc_fiscale_id obbligatorio`,
  fixture d'altro cantiere).
* **dbdev, transazione annullata**: `-01`, `-02` e lo script K-S2 insieme. Lo script porta le copie 77
  (emittente 32) e 2527 (emittente 44) dalla versione 7 alla 8, forma 6; con un secondo giro nella stessa
  transazione non trova più niente. Alla fine i tre modelli che stampano la fattura sono in forma 6 e nessuno
  legge `fattura.origine.`. La vista estesa: 155 righe, nessun doppione.
* Cancelli statici verdi; `guardrail_pgtap_preambolo` resta rosso solo per
  `config/test-grammatica-presidio-tipo-documento-v1`, non di questo giro (§15.11).
* `%TYPE` (richiamo di Tid, 2026-10-28): nel blocco del `-01` e nello script, i due blocchi e le chiavi sono
  `html_template%TYPE`, la data di pubblicazione `valido_dal%TYPE`, la forma `versione_contesto%TYPE`; restano
  `text`/`integer` solo il nome del brief (un valore di `meta`) e i conteggi, col commento. Prove rifatte dopo:
  stessi esiti (6/6, 8/8, dbdev come sopra).
* Non provato prima dell'apply: i pgTAP **come app** (li lancia Tid), il giro BE.
* ✅ **Apply su dbdev** (Tid, 2026-10-28 12:18): `-01` e `-02` `EXECUTED`; lo standard stampa la versione 2 in forma
  6, le copie 77 e 2527 sono ancora alla 7 in forma 5 (le porta lo script, dopo il giro BE). ✅ **pgTAP come app**:
  verdi.

**Prossimi passi**: il team BE (BE-S1, BE-S2 del
§15.17); poi Tid lancia lo script K-S2 subito dopo il riavvio del backend in forma 6.

#### 15.17.2 Il passaggio BE: BE-S1, BE-S2 (team BE, 2026-10-28)

| # | Che cosa | Dove |
| --- | --- | --- |
| BE-S1 | `CONTEXT_VERSION = 6`: `fattura.origini` da `list_fattura_origini` (il lettore del dettaglio, dopo il cancello della testata), ogni elemento `{livello, tipo, etichetta, codice}` (`tipo` = `tipo_codice_interno`; id e uid fuori, il modello stampa e non naviga); `fattura.origine` tolta | `fattura_document_context_builder.py`; test 0, 2-ter, 4 |
| BE-S2 | La scheda Critiche legge `uscita_blocco_reason`, `uscita_blocco_reason_key` da `vendite.vw_lotti_gruppi_azioni` (`LEFT JOIN` su `gruppo_key`, filtro costante sul lotto come BE-2); ritirata la `LATERAL` sulla `fn_check`. Nomi e posizioni invariati | `pipeline_repository.list_lotto_segnalazioni`; test 29 di `test_pipeline_repository` |
| doc | La forma 6 della stampa | `api_fattura_dettaglio.md` |

**Prove (dbdev, transazione annullata).**

* Lo standard stampa la v2 (id 5064) in forma 6; le copie 77 (id 2334) e 2527 (id 3097) sono alla v7 in forma 5.
* Il contesto della fattura 20025: `origini = [{livello 1, ORDINE_VENDITA, «Ordine», ORD0000075}]`; il render
  dell'HTML della v2 (`_render_html_with_jinja`, StrictUndefined) stampa «Documenti di origine — Ordine -
  ORD0000075»; con `origini = []` la sezione non c'è.
* La scheda Critiche: sulle 29 coppie (lotto, documento) del giornale, nessuna senza riga nella vista e nessun
  motivo diverso da quello della `fn_check` (la lettura di prima); tre lotti letti in 6-12 ms.
* Suite Django sul DB provvisto, ruff, mypy: verdi (vedi il commit).

⚠️ Da qui alla fine dello script K-S2 le fatture degli emittenti 32 e 44 non si stampano (guard della forma): è la
finestra prevista dal §15.16.3, e lo script va lanciato subito.

## 16. Giro 12: la versione di listino al modello — ricognizione, piano e domande (2026-10-28)

Ultimo documento dell'ordine W-1 (Tid, 2026-10-25). Il via al giro: Tid, 2026-10-28. È il D-6 del §8.12, «parte da
zero»: la guida §10 segna ❌ in quattro colonne su sei. Brief vicini verificati: `brief-db-provenienza-prezzo-segue-il-prezzo`
(la provenienza del prezzo sulle righe, non lo stato della versione) e `listini-fornitori` (analisi degli
acquisti, ferma): nessuno tocca lo stato della versione.

### 16.1 Com'è oggi (doc auto-generata, dbdev, `backend/`, `frontend/`, 2026-10-28)

**Il database.**

* `vendite.listini_versioni.stato` è `varchar(16)` col `CHECK` `chk_listini_versioni_stato` (BOZZA, ATTIVA, CHIUSA),
  DEFAULT `'BOZZA'`: nessun vocabolario, nessuna matrice. La versione non è nella mappa delle testate
  (`script.fn_doc_stato_modello`), che vuole una colonna d'id verso un vocabolario.
* Lo stato regge due vincoli: `chk_listini_versioni_chiusa_con_fine` (CHIUSA ⇒ `valido_al`) e l'esclusione
  `ex_listini_versioni_no_overlap` (niente sovrapposizioni fra versioni attive **e chiuse** dello stesso listino,
  `WHERE stato IN ('ATTIVA','CHIUSA')`).
* I passaggi sono scritti nel guard `trgfn_listini_versioni_guard_transizione_stato` (`20260424-01`): BOZZA → ATTIVA
  sempre; ATTIVA → CHIUSA solo con `valido_al` passato; nient'altro.
* **Nessuna funzione DB scrive lo stato a mano**. Lo scrive il job `chiusura_scadenze_daily`
  (`dbops.fn_apply_chiusura_scadenze`, riga 1 di `dbops.automazione_chiusura_scadenze`, `tipo_stato = VARCHAR`):
  un `UPDATE` dinamico ATTIVA → CHIUSA a finestra scaduta. Per le testate sotto la porta il job chiama il verbo di
  chiusura, ma il verbo è scritto nel corpo per **una** testata (`IF … = 'vendite.contratti' THEN
  vendite.fn_cessa_contratti_scaduti()`).
* Lettori dei letterali di stato: nove funzioni (`fn_listino_versione_in_vigore`, `fn_resolve_prezzo_listino_v2_esito`,
  `fn_check_listino_congelabile`, `fn_check_listino_provenienza`, `fn_listino_ha_storia`,
  `fn_articolo_righe_vive_non_ammesse`, i guard di righe e componenti, la fixture `fn_pgtap_crea_listino`); le viste
  `vw_contratti_lista` e `vw_offerte_commerciali_lista` leggono la tabella. Le righe sono già immutabili fuori da
  BOZZA nel DB (`trgfn_listini_righe_guard_stato`, `…_comp_guard_immutabilita_v5`).
* Nessuna azione di processo per il listino; la nascita in BOZZA la dice il DEFAULT, senza guard (P-3 l'aveva
  lasciata fuori finché non avesse un vocabolario).

**Il backend e il frontend** (lo stato lo scrive il backend, `listini_repository.change_versione_state`, un
`UPDATE`; permesso: il livello sul modello `vendite.listino`). Regole del dominio che stanno **solo** lì:

| Regola | Dove |
| --- | --- |
| i passaggi (copia del guard) e il rifiuto dedicato di ATTIVA → CHIUSA | `listini_service._validate_versione_state_transition` (cita un brief che non esiste, §3.3) |
| l'attivazione vuole una versione attiva e **almeno una riga** (standalone + compositi distinti) | `_plan_versione_state_change`, `count_active_righe_versione` |
| all'attivazione si **chiudono le versioni precedenti** (`valido_al` = decorrenza nuova − 1), nella stessa transazione, con l'anteprima (`dry_run`) | `_plan_versione_state_change`, `find_versioni_per_autoclose`, `set_versione_valido_al` |
| campi modificabili per stato (BOZZA: tutti; ATTIVA: `valido_al`; CHIUSA: nessuno) | `_VERSIONE_PATCH_ALLOWED_BY_STATE` (nel DB c'è solo la metà di CHIUSA, sulle date) |
| si cancella solo una versione in BOZZA | `fn_delete_versione` |
| righe solo in BOZZA | `_assert_versione_bozza_for_riga_op`, `fn_rettifica_controllata_riga` (copia del guard DB) |
| lo «stato visibile»: CHIUSA se `valido_al` è passato anche se il DB dice ATTIVA (il job non è ancora passato); «Attiva» spento senza righe | `ListiniSearchTable.vue` (`statoVersioneVisibile`, `righe_count`) |

Le fixture: 13 pgTAP scrivono lo stato della versione con un `UPDATE` (su 31 che leggono la tabella).

### 16.2 Il piano (secondo le decisioni del §16.3)

| Pezzo | Che cosa |
| --- | --- |
| vocabolario | `config.stati_doc_listino_versioni` (CSV), BOZZA, ATTIVA, CHIUSA, con le colonne dei gemelli (stato iniziale, …) |
| colonna | `stato` testo → id verso il vocabolario (L-1); CHECK, esclusione e lettori portati |
| matrice | `config.transizioni_stati_listino_versioni` (CSV): BOZZA → ATTIVA manuale (con l'azione di L-3), ATTIVA → CHIUSA di processo (L-2); il guard di transizione legge la matrice, gli `IF` si ritirano |
| mappa | la versione entra in `script.fn_doc_stato_modello`; la porta `_a05_` montata |
| nascita | il guard della nascita nello stato iniziale (N-1), come le altre testate |
| verbi | `fn_attiva_versione_listino` (L-4: le regole dell'attivazione e la chiusura delle precedenti, DEFINER, sul verbo comune), la proiezione della chiusura a scadenza (L-2) |
| job | il verbo di chiusura dichiarato nella riga di `dbops.automazione_chiusura_scadenze` (L-2), non nel corpo |
| capability | i motivi dell'attivazione da una `fn_check` (niente righe, versione spenta), per riga di lista con `azioni_permesse` |
| regole per stato | L-5 |
| fixture | i 13 `UPDATE` al verbo o a `fn_pgtap_porta_a_stato`; `fn_pgtap_crea_listino` sul vocabolario |
| guida | riga della versione di listino al §10; `gestione-listini` rimanda al modello |

**Richiesta al BE e al FE** (a giro DB provato, elenco chiuso come sempre): l'attivazione dal verbo (con l'anteprima
dal lettore DB), il 403 dalla riga del passaggio, le copie della tabella del §16.1 ritirate, il kebab da
`azioni_permesse` e dal motivo del DB, lo «stato visibile» del frontend ritirato (L-2).

### 16.3 Domande per Tid

* **L-1. La forma dello stato.** Proposta: **colonna d'id** verso il vocabolario, come le otto testate già al modello:
  i pezzi comuni (mappa, verbo, porta, `fn_doc_azioni_permesse`) la presuppongono. Il costo è l'esclusione
  `ex_listini_versioni_no_overlap`: il suo `WHERE` non può leggere il vocabolario, quindi si riscrive sugli **id del
  seed** (CSV con id espliciti, stabili), con un presidio pgTAP che li confronta coi codici ATTIVA e CHIUSA; e la
  conversione sul posto della colonna, coi nove lettori DB e quelli del backend. Alternativa: la colonna resta il
  **codice**, con una FK sul codice del vocabolario (come lo stato del job del lotto, P-1): esclusione e lettori
  restano com'è, ma i pezzi comuni vanno estesi a una testata che scrive il codice, cioè si tocca il verbo comune di
  tutte le testate.
* **L-2. CHIUSA.** Resta uno stato **scritto**, da un passaggio di processo (ATTIVA → CHIUSA, `manuale = false`) che
  scrive solo la proiezione della scadenza, `vendite.fn_chiudi_versioni_listino_scadute`, chiamata dal job: gemello
  di `fn_cessa_contratti_scaduti`. Regola del 2: la seconda testata sotto la porta col suo verbo di chiusura, quindi il
  verbo si **dichiara** in una colonna di `dbops.automazione_chiusura_scadenze` e l'`IF` sul contratto si ritira.
  Lo «stato visibile» del frontend si ritira: fra la scadenza e il passaggio del job la versione è ATTIVA con
  `valido_al` passato, e la lista la mostra con la chiusura programmata (come la cessazione programmata del
  contratto), letta dal DB. Alternativa: CHIUSA **derivata** dalla data (non più scritta): toglie il job e la
  finestra, ma lo stato non è più un dato e l'esclusione e il CHECK cambiano significato.
* **L-3. L'azione.** L'attivazione è il passaggio pesante del listino: mette i prezzi in uso e chiude la versione
  precedente. Proposta: un'azione nuova, `attiva_listino`, sulla riga BOZZA → ATTIVA (gemella di `emetti_*`); va
  concessa ai profili che oggi gestiscono i listini (dato su dbdev, Tid). Alternativa: nessuna azione, decide il
  livello sul documento (M-3), come oggi.
* **L-4. Le regole dell'attivazione nel verbo.** Proposta: `vendite.fn_attiva_versione_listino(p_versione_id)`, una
  transazione: prima ciò che vieta (versione spenta, nessuna riga: `fn_check_versione_listino_attivabile`, motivi
  anche per la capability), poi la chiusura delle precedenti (`valido_al` = decorrenza − 1), poi lo stato dal verbo
  comune. Più il lettore dell'anteprima (le versioni che verrebbero chiuse), per il `dry_run`. Le copie del backend
  si ritirano. Non è una revoca: la regola D3 di `sviluppo-listini-v2` resta com'è, cambia la sede.
* **L-5. Le regole per stato fuori dal passaggio** (campi modificabili di ATTIVA e CHIUSA, cancellazione solo in
  BOZZA): oggi solo nel backend. Proposta: **nello stesso giro**, nel guard della versione (una regola, il backend
  traduce il codice). Alternativa: un brief a parte, fuori dal modello del cambio di stato.
