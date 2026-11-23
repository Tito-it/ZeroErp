# Brief DB — Revisione dello schema `ui`: la documentazione, i difetti di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-23 (sessione DB, dopo l'apply del giro 8b)

**Riparte: Tid col commit; poi la sessione DB con la chiusura** (§10). Il giro 8 e il giro 8b sono applicati per intero (`20261123-16` … `-36`), pgTAP verdi, documentazione aggiornata (Tid, 2026-11-23); la regola «l'utente della connessione si legge solo con `script.fn_utente_di_sessione`» è scritta nella pagina delle GUC, nel contratto GUC e nelle linee guida SQL (§3.6-sexies). Il team BE con BE34 (§6). Nessuna decisione aperta. Da committare: il giro 8 e il giro 8b (ventuno changeSet, i tre pgTAP toccati, le pagine `manual/` e le guide di §3.6-sexies, la pagina delle GUC, le due note in `codici_errore.csv`), le richieste di BE32 e BE33 (riga 8-sexies), la doc auto-generata, questo brief.

Lo stato di prima (sessione DB, dopo la scrittura del giro 8b): **Riparte: Tid con l'apply del giro 8b** (le policy: `20261123-27` … `-36`, scritti e provati sullo scratch, §3.6-sexies), poi come app i pgTAP `script/test-fn-utente-di-sessione-v1` (plan 17), `script/test-policy-funzioni-cost-v1`, `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` e la cartella `rls/` (le policy di nove schemi cambiano: conviene la corsa intera), la doc auto-generata di `dbops` e di `magazzino` (ancora da rigenerare dal `-26`); **poi la sessione DB con la chiusura** (§10). Il team BE con BE34 (§6, allargata alle letture sotto RLS). Nessuna decisione aperta. Da committare: il giro 8 e il giro 8b (ventuno changeSet, i tre pgTAP toccati, le pagine `manual/` e le guide di §3.6-sexies, le due note in `codici_errore.csv`), le richieste di BE32 e BE33 (riga 8-sexies), la doc auto-generata, questo brief.

Lo stato di prima (sessione DB, dopo l'apply del `-26`): **Riparte: Tid con la doc auto-generata di `magazzino` e il commit del giro 8; poi la sessione DB** con la misura delle 177 policy (§3.6-sexies, «Le policy»), l'ultimo punto del giro 8 prima della chiusura (§10); il team BE con BE34 (§6). Il giro 8 è applicato per intero: `20261123-16` … `-26`, pgTAP verdi (Tid, 2026-11-23). Verificato sul vivo lo stesso giorno: in `magazzino` nessuna funzione legge più `app.current_user_id` da sé. Nessuna decisione aperta. Da committare: il giro 8 (undici changeSet, `script/test-fn-utente-di-sessione-v1`, `ui/test-ui-misura-lista-e-contesto-ricerca-v1`, le pagine `manual/` di `fn_utente_di_sessione`, `fn_lista_colonne_ricerca_full`, `fn_guard_super_admin`, `fn_guard_azione`, `fn_guard_livello`, `fn_get_uo_id_for_user`, la guida `contratto-guc-app`, le linee guida SQL, le due note in `codici_errore.csv`), le richieste di BE32 e BE33 (riga 8-sexies: `20261122-48`, `-49`, `messaggi_errore.csv`, `ui/test-misure-pagina-v1`, la pagina `manual/` di `fn_get_misure_pagina`), la doc auto-generata rigenerata, questo brief.

Lo stato di prima (sessione DB, dopo la scrittura del `-26`): **Riparte: Tid con l'apply del `20261123-26`** (`magazzino` al BB, scritto e provato: §3.6-sexies), poi il pgTAP `script/test-fn-utente-di-sessione-v1` come app (il presidio non ha più l'esenzione di `magazzino`), i pgTAP di `magazzino` e la doc auto-generata di `magazzino`; **poi la sessione DB** con la misura delle 177 policy (§3.6-sexies, «Le policy»); il team BE con BE34 (§6), già sbloccato. `20261123-16` … `-25` sono applicati coi pgTAP verdi (Tid, 2026-11-23). Nessuna decisione aperta. Da committare: il giro 8 intero (undici changeSet, i due pgTAP, le pagine `manual/` e le guide del paragrafo qui sotto, le due note in `codici_errore.csv`), le richieste di BE32 e BE33 (riga 8-sexies) e la doc auto-generata rigenerata. `messaggi_errore.csv` e `codici_errore.csv` portano ormai solo le righe di questo brief: l'altra sessione ha committato le sue (`9d0237027a`).

Lo stato di prima (sessione DB, dopo la scrittura del giro 8): **Riparte: Tid con l'apply del giro 8** (Q60 (a), fatta qui per decisione di Tid del 2026-11-23: §3.6-sexies, riga 8-septies): `20261123-16` … `-25`, scritti e provati sullo scratch. Il BB `script.fn_utente_di_sessione` e le funzioni e viste di `ui`, `script`, `anagrafiche`, `catalogo`, `config`, `dbops`, `pagamenti`, `vendite` che passano a lui; poi i pgTAP `script/test-fn-utente-di-sessione-v1` (nuovo) e `ui/test-ui-misura-lista-e-contesto-ricerca-v1` come app, e una corsa intera (i lettori toccati sono una sessantina: verbi di `vendite`, credenziali, TOTP, builder pgTAP); la doc auto-generata degli otto schemi. **Poi la sessione DB** col `-26` (`magazzino`, dopo il commit dell'altra sessione DB: 2b) e la misura delle 177 policy (§3.6-sexies, «Le policy»); il team BE con BE34 (§6), dopo l'apply. Numeri `-16` … `-25` concordati da Tid con l'altra sessione; il `-26` è riservato. Le richieste di BE32 e BE33 sono applicate (riga 8-sexies), da committare. ⚠️ `messaggi_errore.csv` e `codici_errore.csv` hanno anche righe dell'altra sessione DB: si committano solo le righe di questo brief. Nessuna decisione aperta. Da committare, oltre a quanto sotto: i dieci changeSet del giro 8, `script/test-fn-utente-di-sessione-v1`, `ui/test-ui-misura-lista-e-contesto-ricerca-v1`, le pagine `manual/` di `fn_utente_di_sessione`, `fn_lista_colonne_ricerca_full`, `fn_guard_super_admin`, `fn_guard_azione`, `fn_guard_livello`, `fn_get_uo_id_for_user`, la guida `contratto-guc-app`, le linee guida SQL, le due note in `codici_errore.csv`.

Lo stato di prima (sessione DB, dopo l'apply delle richieste di BE32 e BE33): **Riparte: Tid col commit delle richieste di BE32 e BE33, poi la sessione DB con la chiusura** (§10). `20261122-48`, `20261122-49` e il messaggio di `E_UI_COLONNA_IN_USO` sono applicati su dbdev, coi pgTAP verdi e la doc auto-generata di `ui` rigenerata (Tid, 2026-11-23; riga 8-sexies). Da committare: i due changeSet, la riga di `E_UI_COLONNA_IN_USO` in `messaggi_errore.csv`, `ui/test-misure-pagina-v1`, la pagina `manual/` di `fn_get_misure_pagina`, le tre pagine auto-generate di `ui` (`funzioni/fn_get_misure_pagina`, `tabelle/lista_preferenza_utente`, `tabelle/dashboard_preferenza_utente`), questo brief. ⚠️ `messaggi_errore.csv` ha anche una riga dell'altra sessione DB (`E_MAG_DOCUMENTO_TESTATA_CONGELATA`): si committa solo la riga di questo brief, o si lascia il file al commit dell'altra sessione. Alla chiusura restano: Q60 (a) in un brief nuovo, aperto prima dell'archiviazione (§7.1); il controllo a video di BE29 e del residuo di BE25 (2), del team BE/FE (riga 8-ter), che passa a un brief BE se non è fatto; poi l'archiviazione in `work-done/`. Nessuna decisione aperta.

Lo stato di prima (sessione DB, dopo la scrittura delle richieste di BE32 e BE33): **Riparte: Tid con l'apply delle richieste di BE32 e BE33** (riga 8-sexies, scritte e provate sullo scratch il 2026-11-23): `20261122-48` (via `default_compatta` e `default_pagina` da `ui.fn_get_misure_pagina`), `20261122-49` (il COMMENT delle due preferenze, §3.5-bis) e il messaggio di `E_UI_COLONNA_IN_USO` in `messaggi_errore.csv`; poi il pgTAP `ui/test-misure-pagina-v1` come app (atteso 19/0; da owner il 16 è rosso per costruzione) e la doc auto-generata di `ui`; **poi la sessione DB con la chiusura** (§10). Numeri `-48` e `-49` presi dalla sessione DB col via di Tid sulla proposta, con l'altra sessione DB attiva. Nessuna ricaduta BE: il BE non legge più le due chiavi, e il testo del messaggio è quello del suo ripiego. Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Da committare: i due changeSet, `messaggi_errore.csv`, `ui/test-misure-pagina-v1`, la pagina `manual/` di `fn_get_misure_pagina`, questo brief.

Lo stato di prima (sessione DB, dopo le verifiche dei giri 7 e 5; merge con BE32 e BE33): **Riparte: la sessione DB con le due richieste nate da BE32 e BE33** (riga 8-sexies, §6: il ritiro di `default_compatta` e `default_pagina` da `ui.fn_get_misure_pagina`, che nessuno legge più; il messaggio a catalogo di `E_UI_COLONNA_IN_USO`, che nomina ancora le preferenze), **poi la chiusura** (§10). Le verifiche dei giri 7 e 5 sono fatte e committate su `dev/db-tid` (2026-11-23): giro 7 in §3.6-quinquies, «La verifica del giro 7»; giro 5 in §3.5-bis, «La verifica». I due pgTAP che toccano (`ui/test-seed-primo-impianto-ui-software-v1`, 22/0; `ui/test-ui-catalogo-dashboard-v1`, 29/0) sono verdi (Tid, 2026-11-23). Il team BE/FE ha chiuso BE32 (la parte Q56) e BE33 il 2026-11-23, verdi, committati su `dev/backend-tid` (`1a1720cdde`). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Il COMMENT ON TABLE delle due preferenze aspetta il prossimo changeSet di `ui` (§3.5-bis): può viaggiare con quello della riga 8-sexies. ⚠️ Il `20261122-40` (`dbops.fn_pgtap_definizione_vincolo`) non è di questo brief: è dell'altra sessione DB attiva il 2026-11-22.

Lo stato di prima (team BE/FE, dopo BE32 e BE33): **Riparte: la sessione DB, in sessioni nuove: il `/verifica-db` del giro 7 intero** (`20261122-34` … `-39` e `-41` … `-43`, §3.6-quinquies), **poi quello del giro 5** (`/verifica-db d75ff94dab`), **e le due richieste nate da BE32 e BE33** (§6: il ritiro di `default_compatta` e `default_pagina` da `ui.fn_get_misure_pagina`, che nessuno legge più; il messaggio a catalogo di `E_UI_COLONNA_IN_USO`, che nomina ancora le preferenze), poi la chiusura (§10). Tid: la doc auto-generata di `dbops` e `script`. Il team BE/FE ha chiuso BE32 (la parte Q56) e BE33 il 2026-11-23, verdi, **da committare** su `dev/backend-tid`. Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. ⚠️ Il `20261122-40` (`dbops.fn_pgtap_definizione_vincolo`) non è di questo brief: è dell'altra sessione DB attiva il 2026-11-22.

Lo stato di prima (sessione DB, dopo le verifiche dei giri 7 e 5): **Riparte: la sessione DB con la chiusura** (§10). I due pgTAP toccati dalle verifiche dei giri 7 e 5 (`ui/test-seed-primo-impianto-ui-software-v1`, 22/0; `ui/test-ui-catalogo-dashboard-v1`, 29/0) sono verdi (Tid, 2026-11-23). Le verifiche sono fatte (2026-11-23): giro 7 in §3.6-quinquies, «La verifica del giro 7»; giro 5 in §3.5-bis, «La verifica». Nessun changeSet toccato. Il team BE riparte con BE32 e BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Il COMMENT ON TABLE delle due preferenze aspetta il prossimo changeSet di `ui` (§3.5-bis). Le verifiche sono committate su `dev/db-tid` (2026-11-23).

Lo stato di prima (sessione DB, dopo l'apply della regola del 2): **Riparte: la sessione DB, in sessioni nuove: il `/verifica-db` del giro 7 intero** (Q57, Q58, Q54 e la regola del 2: `20261122-34` … `-39` e `-41` … `-43`, applicati su dbdev coi pgTAP verdi, Tid, 2026-11-22 e 2026-11-23; §3.6-quinquies), **poi quello del giro 5** (`/verifica-db d75ff94dab`), poi la chiusura (§10). Tid: la doc auto-generata di `dbops` e `script`. Il team BE riparte con BE32 e BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Il giro 7 è committato su `dev/db-tid` (2026-11-23), con la doc auto-generata di `ui`. ⚠️ Il `20261122-40` (`dbops.fn_pgtap_definizione_vincolo`) non è di questo brief: è dell'altra sessione DB attiva il 2026-11-22.

Lo stato di prima (sessione DB, dopo la scrittura della regola del 2): **Riparte: Tid con l'apply della regola del 2** (`20261122-41` … `-43`: il BB `dbops.fn_seed_elenco_colonne` e le due sedi che lo leggono, scritti e provati sullo scratch; §3.6-quinquies, «Q54, la regola del 2»), col pgTAP nuovo `dbops/test-fn-seed-elenco-colonne-v1` e quelli del seed, e la doc auto-generata di `dbops` e `script`; **poi la sessione DB, in sessioni nuove: il `/verifica-db` del giro 7 intero** (Q57, Q58, Q54 e la regola del 2: `20261122-34` … `-39` e `-41` … `-43`), **poi quello del giro 5** (`/verifica-db d75ff94dab`), poi la chiusura (§10). Il team BE riparte con BE32 e BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Da committare: il giro 7 (nove changeSet, i CSV dei messaggi e del registro del seed col suo caricatore, quattro pgTAP, sette pagine `manual/`, linee-guida-sql, la guida `automazione-db`, questo brief) e la doc auto-generata di `ui` rigenerata. ⚠️ Il `20261122-40` (`dbops.fn_pgtap_definizione_vincolo`) non è di questo brief: è dell'altra sessione DB attiva il 2026-11-22.

Lo stato di prima (sessione DB, dopo l'apply di Q54): **Riparte: la sessione DB, in sessioni nuove: il `/verifica-db` del giro 7 intero** (Q57, Q58, Q54: `20261122-34` … `-39`, applicati su dbdev coi pgTAP verdi, Tid, 2026-11-22; §3.6-quinquies), **poi quello del giro 5** (`/verifica-db d75ff94dab`), poi la chiusura (§10). Tid: la doc auto-generata di `dbops` e `script` e la decisione sulla regola del 2 della lettura degli elenchi del seed (§3.6-quinquies, «Q54, il giro»). Il team BE riparte con BE32 e BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Da committare: il giro 7 (sei changeSet, i CSV dei messaggi e del registro del seed col suo caricatore, tre pgTAP, sei pagine `manual/`, linee-guida-sql, la guida `automazione-db`, questo brief) e la doc auto-generata di `ui` rigenerata.

Lo stato di prima (sessione DB, dopo la scrittura di Q54): **Riparte: Tid con l'apply di Q54** (`20261122-36` … `-39` e il CSV del registro del seed, scritti e provati sullo scratch: §3.6-quinquies, «Q54, il giro»), coi pgTAP del seed e di `ui`, la doc auto-generata di `dbops` e `script` e la decisione sulla regola del 2 della lettura degli elenchi (stessa sezione); **poi la sessione DB, in sessioni nuove**: il `/verifica-db` del giro 7 intero (Q57, Q58, Q54) e quello del giro 5 (`/verifica-db d75ff94dab`). Il team BE riparte con BE32 e BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta oltre a quella della regola del 2. Da committare: il giro 7 (sei changeSet, i CSV dei messaggi e del registro del seed col suo caricatore, tre pgTAP, sei pagine `manual/`, linee-guida-sql, la guida `automazione-db`, questo brief) e la doc auto-generata di `ui` rigenerata.

Lo stato di prima (sessione DB, dopo l'apply del giro 7): **Riparte: la sessione DB, in sessioni nuove: il `/verifica-db` del giro 7** (`20261122-34` e `-35`, applicati su dbdev coi pgTAP verdi, Tid, 2026-11-22: §3.6-quinquies), **il `/verifica-db` del giro 5** (`/verifica-db d75ff94dab`) **e Q54 (a)**, col piano di §3.6-quinquies e un range di numeri di Tid. Tid: la doc auto-generata di `ui` da rigenerare dopo il giro 7, e il commit del giro. Il team BE riparte con BE32 e con BE33 (§6), sbloccata dall'apply. Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Da committare: il giro 7 (due changeSet, `messaggi_errore.csv`, due pgTAP, due pagine `manual/`, questo brief).

Lo stato di prima (sessione DB, dopo la scrittura del giro 7): **Riparte: Tid con l'apply del giro 7** (`20261122-34` e `-35`, Q57 e Q58, scritti e provati sullo scratch: §3.6-quinquies), coi pgTAP di `ui` come app e la doc auto-generata; **poi la sessione DB, in sessioni nuove**: il `/verifica-db` del giro 7, il `/verifica-db` del giro 5 (`/verifica-db d75ff94dab`) e Q54 (a), col piano di §3.6-quinquies e un range di numeri di Tid. Il team BE riparte con BE32 e, dopo l'apply, con BE33 (§6). Q60 (a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Da committare: il giro 7 (due changeSet, `messaggi_errore.csv`, due pgTAP, due pagine `manual/`, questo brief). Le quattro verifiche sono committate (`47677fd8bc`).

Lo stato di prima (sessione DB, dopo la decisione di Q54): **Riparte: la sessione DB, in sessioni nuove: il `/verifica-db` del giro 5** (`/verifica-db d75ff94dab`, l'ultimo), **poi il
giro 7** con le decisioni prese e non ancora scritte: Q54 (a), il seed che non riporta a OLD l'impronta della
composizione (changeSet sul BB del seed in `script`); Q57 (a), il ritiro della card nello stesso statement; Q58 (a), i
default per uso in `ui.fn_get_misure_pagina`, con la richiesta al BE/FE; e, con la riscrittura di Q58, il COMMENT di
`ui.fn_misura_pagina_default` e la soluzione di `E_UI_CHIAMATA_NON_VALIDA` in `messaggi_errore.csv` (§3.6-quater, «La
verifica»). Il giro 7 vuole il via di Tid e, dopo l'apply, il suo `/verifica-db`. Il team BE riparte con BE32 (§6). Q60
(a) va in un brief nuovo (§7.1). Nessuna decisione aperta. Le quattro verifiche sono committate (`47677fd8bc`).

Lo stato di prima (sessione DB, dopo le verifiche di Q55 e dei giri 3, 4 e 6): **Riparte: Tid con Q54 (§7.1) e col commit delle quattro verifiche (i pgTAP toccati dalla verifica del giro 6 sono verdi, Tid, 2026-11-22); il team BE con BE32 (§6); la sessione DB col `/verifica-db` del giro 5** (`/verifica-db d75ff94dab`) (il 6a-6c è fatto, 2026-11-22, §3.6-quater «La verifica»), in una sessione nuova, e con Q57 (a) e Q58 (a), decise da Tid il 2026-11-22, in una sessione sua; Q60 (a), decisa da Tid il 2026-11-22, va in un brief nuovo (§7.1), da aprire in una sessione DB dopo aver cercato i brief vicini. I pgTAP toccati dalle tre verifiche sono verdi (Tid, 2026-11-22). Le verifiche di Q55 (`d265aaa463`), del giro 3 (`ea04ec5f45`) e del giro 4 (`2959cc7396`) sono fatte nella stessa sessione, per scelta di Tid (2026-11-22): esiti in §3.2-bis, §3.3-bis e §3.4-bis, «La verifica». Nessun changeSet toccato: le correzioni sono su pgTAP, pagine `manual/` e commenti di testata dei caricatori. Ne nascono Q57 (il ritiro della card cancellata nello stesso statement) e Q58 (i default per uso nella lettura dell'applicazione); il COMMENT di `ui.fn_misura_pagina_default` nomina un chiamante che non la chiama più, e aspetta la prossima riscrittura della funzione. Il caso 15 di `ui/test-ui-ritiro-voce-preferenze-v1` è verde nella corsa di Tid; da lanciare i pgTAP toccati per i giri 3 e 4.

Lo stato di prima (sessione DB, dopo la verifica dell'1b): **Riparte: il team BE con BE32 (§6, Q56 decisa (a)), Tid con Q54 (§7.1), e la sessione DB col `/verifica-db` di Q55 e poi del giro 3** (`/verifica-db ea04ec5f45`), ciascuno in una sessione nuova. Q55 (`20261122-26` … `-28`, §3.2-bis, «Q55, il giro») è migrata su dbdev coi pgTAP verdi (Tid, 2026-11-22), da committare. La verifica del giro 2 è fatta (2026-11-22, §3.2-bis, «La verifica sul commit»): sul solo `eaed059e6e`, perché `2e867df589` è del cantiere della provenienza del prezzo e non tocca `ui`; nessun difetto di corpo, un COMMENT che dice il falso (`ui.fn_intero_da_jsonb`, la pagina `manual/` corretta, il COMMENT aspetta un changeSet) e un difetto di modello (Q55, decisa (a) da Tid lo stesso giorno, scritta e provata: §3.2-bis, «Q55, il giro»). La verifica dell'1a è fatta (2026-11-22, §3.1-bis, «La verifica»): nessun difetto nei changeSet, un presidio di U3 aggiunto al pgTAP, verde (Tid, 2026-11-22), da committare. Anche la verifica dell'1b è fatta (2026-11-22, §3.1-ter, «La verifica sul commit»): un difetto del seed sull'impronta (Q54, a Tid) e la pagina `manual/` di `trgfn_preset_riga_tocca_preset` corretta, da committare. Deciso da Tid il 2026-11-22: la verifica si fa **un giro per volta**, ciascuno sul suo commit e in una sessione sua, nell'ordine 1a `8668768481`, 1b `986baa5d8d`, 2 `eaed059e6e` (`2e867df589`, citato qui prima, è di un altro cantiere), 3 `ea04ec5f45`, 4 `2959cc7396`, 5 `d75ff94dab`, 6a-6c `53440091fc`. Non si passa un intervallo, perché fra quei commit ci sono quelli di altri cantieri (anagrafiche, magazzino, fornitore, PG19). Ogni verifica scrive il suo esito qui e nella riga 8-bis, e dice chi riparte con il giro dopo. Dopo il giro 6 viene la chiusura (§10). Le ricadute BE/FE sono committate (`2caffd1ee0` per i giri 2-5, `ecc51bf31a` per il giro 6, PR #204) e sono già in `dev/db-tid`. Al BE/FE resta solo il controllo a video di BE29 e del residuo di BE25 (2): se alla chiusura non è fatto, passa a un brief BE (§10).

Lo stato di prima (team BE/FE, dopo il giro 6): **Riparte: la sessione DB, in una sessione nuova**, col `/verifica-db` dei giri 1a-6c e la chiusura (§10). Le ricadute BE/FE del giro 6 sono fatte e verdi, da committare su `dev/backend-tid` (team BE/FE, 2026-11-22, §6): BE10 (la misura di partenza, con tre decisioni di Tid), BE18 (U39: le due letture «lista accesa per codice» dal BB), BE31 (anche `utente_di_sessione` del BE non dà più il 22P02: codice del dominio che chiede), BE29 (16 copie FE dell'ordinamento ritirate). Suite BE verde (6728), vitest verde (1281). Il residuo di BE25 (2) è fatto lo stesso giorno (§6: la partenza su ogni porta, 29 view, e le copie FE ritirate anche su 21 superfici di catalogo che il censimento contava fuori). Al BE/FE resta solo il controllo a video di BE29 e del residuo.

Lo stato di prima (sessione DB, notte del 2026-11-22): **Riparte: la sessione DB, in una sessione nuova**, col `/verifica-db` dei giri 1a-6c e la chiusura (§10). Il giro 6 è finito: 6a e 6b applicati su dbdev, e i pgTAP di `ui`, compresi quelli del 6c, verdi come app (Tid, 2026-11-22); tutto committato su `dev/db-tid` il 2026-11-22. **Al team BE/FE** BE10, BE18, BE29 e BE31 (§6). Il giro 6b (`20261121-34` … `-37`: i COMMENT di `ui` e i registri CSV, §3.6-ter) è applicato su dbdev coi pgTAP verdi (Tid, 2026-11-22). Il giro 6a (`20261121-26` … `-33`, il seed di U40, §3.6-bis) è applicato su dbdev coi pgTAP di `ui` verdi (Tid, 2026-11-22). Ora tocca anche al **team BE/FE** con BE10 (la lettura `ui.fn_misura_lista`), BE29 (U40 nel seed) e BE31 (il codice di U38), §6; poi il `/verifica-db` dei giri 1a-6, in una sessione nuova. Il giro 6a non è committato.

Lo stato di prima (team BE/FE, sera del 2026-11-22): **riparte il team BE/FE**, con il commit del lavoro del 2026-11-22 e il residuo di BE25 (2) (§6: 18 liste servite da view che non dichiarano `lista_codice`, dove il BE non applica ancora l'ordinamento del preset). BE20 e BE25 (2) sono fatti (2026-11-22). **Alla sessione DB** il `/verifica-db` dei giri 1a-5 e il giro 6, che ha una voce nuova: **U40** (§3.6, l'ordinamento di partenza nel seed dei preset, chiesto dal team BE il 2026-11-22). Q51 è decisa da Tid il 2026-11-22: (c) (§3.6). BE30 è fatto (§6: il codice lo faceva già, ora è presidiato). I due punti nati scrivendo sono decisi da Tid il 2026-11-22 (§6: BE13 confermato; BE14, le fatture non chiedono più la sintesi, fatto). Il 2026-11-22 il team BE/FE ha fatto e provato sul DB vero BE8, BE11 (giro 2, col «null» tolto dal FE: decisione di Tid dello stesso giorno), BE10, FE1 (giro 3), BE12-BE15, BE27 (giro 4), BE17, BE21, BE28 (giro 5): `apps.ui` e `apps.core` verdi salvo un rosso non di questo brief (sotto), vitest verde. Le policy sono rigenerate dopo che il branch ha preso `e00a3c727` (PR #188): `apps.ui`, `apps.core`, `apps.anagrafiche` e `apps.vendite` verdi. R-BE3 e BE26 sono committati (`ae2336fcf`, PR #187). Il giro 3 (`20261120-36` … `-42`, §3.3-bis: le misure; Q44-Q46 decise il 2026-11-21) è committato (`ea04ec5f4`, PR #184) con la doc auto-generata, che lo mostra applicato su dbdev (l'enum, `lista_definizione.uso_misura`, il lucchetto di `misure_pagina.misura`): ⏳ la sessione DB registra qui l'apply e la corsa dei pgTAP di `ui` (rilevato dal team BE all'arrivo, 2026-11-21). **Alla sessione DB** il `/verifica-db` dei giri 1a, 2 e 3 (in una sessione nuova). Il giro 2 è applicato su dbdev coi pgTAP verdi: 2a (`20261120-21` … `-31`) e 2b (`20261120-32` … `-35`) (Tid, 2026-11-21); ~~R-BE3 non è ancora fatto, quindi la lista admin dei preset legge una colonna che non c'è più: rottura accettata in sviluppo~~ (chiusa con R-BE3, 2026-11-21). Q40 (b), Q41 (a) e Q42 (a) sono decise (Tid, 2026-11-21, §7.1). Le ricadute BE/FE del giro 1b (la parte 1b di BE7 e BE25 (1b), §6) e la risposta a R-BE2 (§3.2-bis) sono fatte dal team BE/FE il 2026-11-21, verdi e committate (`78e17ec4f`, in `Tito-dev` con la PR #175); per Q40 il team BE ha verificato che nessun componente FE scrive `col` (§3.2-bis, «Verifica per Q40»); BE9 era già verificato. Il residuo di BE22 è chiuso: id 665 spento nel CSV e migrato su dbdev (2026-11-21). Il giro 1b (`20261120-02` … `-11`, §3.1-ter) è applicato su dbdev con i pgTAP verdi (Tid, 2026-11-20), dopo il `/verifica-db` dello stesso giorno (quattro correzioni di testo, nessuna al codice: §3.1-ter, «La verifica»); committato (`986baa5d8d`, PR #172) con la doc auto-generata rigenerata. Alla sessione DB resta il `/verifica-db` del giro 1a, da fare. Il giro 2 parte col via di Tid. Le ricadute del giro 1a (BE5-BE7, BE22-BE24, §6) sono fatte e verdi. Il giro 1a (`20261119-09` … `-14`, §3.1-bis) è applicato su dbdev con i pgTAP verdi (Tid, 2026-11-20). Le tabelle di `ui` sono iscritte al seed di primo impianto (Q27, nel
[brief del seed](../work-done/2026/brief-db-seed-primo-impianto-non-si-riscrive.md) §16.15, changeSet `20261119-01` … `-05`, applicati su
dbdev con i pgTAP verdi il 2026-11-20): i giri che toccano i CSV di `ui` sono sbloccati. Le decisioni Q1-Q36 sono prese
(2026-11-18 … 2026-11-20); Q27-Q36, dall'analisi critica del 2026-11-20, completano o sostituiscono alcune delle prime, e
le scelte superate sono barrate (§7, §7.1 e le schede). Il giro 0 è fatto e committato (`de25065c21`): le 32 pagine
`manual/` allo standard (28 riscritte, 4 nuove), la guida `configurazione-liste` riallineata al codice, il censimento
(§3-§6).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Giro 0: 32 pagine `ui/manual/` allo standard, guida `configurazione-liste` riallineata, link della mappa concentrica | §8 | — |
| 2 | ✅ sessione DB | Censimento in sola lettura: difetti, metadati, pgTAP, ricadute BE/FE | §3-§6 | — |
| 3 | ✅ Tid | Doc auto-generata rigenerata (dopo l'1a e dopo l'1b, nel commit `986baa5d8d`) | §8.3 | 1 |
| 4 | ✅ Tid | Le decisioni Q1-Q26 e l'ordine dei giri, prese dal 2026-11-18 al 2026-11-20 | §2, §7 | 2 |
| 4-bis | ✅ Tid | Le decisioni Q27-Q36, prese il 2026-11-20 come raccomandate | §7.1 | 4 |
| 4-ter | sessione DB | Q27: le tabelle di `ui` nel censimento del brief del seed. ✅ Censimento e QU1-QU5 decise; ✅ il giro che le iscrive (`20261119-01` … `-05`) applicato su dbdev, pgTAP verdi (Tid, 2026-11-20) | brief del seed, §16.15 | 4-bis |
| 5 | team BE | Le ricadute «subito» (BE1, BE2, BE4), che non aspettano il DB; e la verifica di BE9 prima del giro 2 (Q35). ✅ BE1, BE2, BE4 fatti e verdi; ✅ BE9 verificato: nessuno applica ordinamento e filtri risolti, ne nasce Q37, decisa (a): li applica il BE, voce BE25 (2026-11-20, esito in §6); rivisti con `/verifica` e committati su `dev/backend-tid` il 2026-11-21 | §6 | — |
| 6 | ✅ Tid | Il via al giro 1a (2026-11-20) | §2 | 4-ter |
| 6-bis | ✅ Tid | Q37-Q39 (§7.1) decise come raccomandate e il via all'1b (2026-11-20) | §3.1-ter, §7.1 | — |
| 7 | sessione DB | I giri 1a, 1b, 2-6, uno per volta, ciascuno con apply e pgTAP di Tid. ✅ 1a applicato, pgTAP verdi (2026-11-20); ✅ 1b (`20261120-02` … `-11`, §3.1-ter) verificato, applicato, pgTAP verdi (2026-11-20), committato con la doc auto-generata; ✅ il residuo di BE22 (id 665 spento nel CSV, migrato su dbdev il 2026-11-21); ✅ il `/verifica-db` dell'1a (2026-11-22); ✅ il piano del giro 2 (§3.2-bis), riallineato il 2026-11-21 a R-BE2, a Q40-Q42 e al ritiro di Q38/Q39 §6; ✅ Q43 (a) e il via al giro 2 (Tid, 2026-11-21); ✅ 2a scritto e applicato (2026-11-21); ✅ 2b scritto, applicato, pgTAP verdi (Tid, 2026-11-21); ⏳ il `/verifica-db` del giro 2; ✅ il via al giro 3 e Q44-Q46 (Tid, 2026-11-21); ✅ giro 3 scritto e provato (`20261120-36` … `-42`, 2026-11-21), committato (`ea04ec5f4`, PR #184), applicato secondo la doc auto-generata; ✅ apply e pgTAP del giro 3 (Tid, 2026-11-21, §3.3-bis); ✅ il `/verifica-db` del giro 3 (2026-11-22, §3.3-bis: due correzioni di testo, Q58 a Tid) | §2, §3.2-bis, §3.3-bis | 6-bis |
| 7-bis | team BE/FE | Le ricadute del giro 2, tutte insieme (2b applicato il 2026-11-21). ✅ R-BE3 e BE26 fatti e verdi sul DB provvisto (2026-11-21, esito in §3.2-bis, «Esito di R-BE3 e BE26»), committati (`ae2336fcf`); ✅ BE8, BE11, BE20 e BE25 (2) fatti e verdi (2026-11-22, §6), committati (`2caffd1ee0`); ✅ il residuo di BE25 (2) (2026-11-22, §6) | §3.2-bis, «Le ricadute BE/FE del giro 2» | 7 |
| 8 | team BE/FE | Le ricadute di ogni giro, dopo il suo apply. Giro 1a: ✅ BE5, BE6, BE7 (parte 1a), BE22, BE23, BE24 fatti e verdi (2026-11-20, esito in §6), committati in `7e65518b9`. Giro 1b: ✅ BE7 (parte 1b) e BE25 (1b) fatti e verdi (BE + FE, 2026-11-21, esito in §6), committati in `78e17ec4f`. Giro 2: ✅ BE8, BE11, BE20, BE25 (2) (2026-11-22; residuo di BE25 (2) in §6). Giro 3: ✅ BE10, FE1 (2026-11-22). Giro 4: ✅ BE12-BE15, BE27 (2026-11-22; BE13 e BE14 decisi da Tid lo stesso giorno). Giro 5: ✅ BE17, BE21, BE28 (2026-11-22). Giri 2-5 committati in `2caffd1ee0` | §6 | 7 |
| 8-bis | sessione DB | Giro 6 (via di Tid, 2026-11-22, con BE10). ✅ 6a scritto, provato, applicato coi pgTAP verdi (`20261121-26` … `-33`, U40 nel seed, §3.6-bis; Tid, 2026-11-22); ✅ 6b, i metadati, applicato coi pgTAP verdi (`20261121-34` … `-37`, §3.6-ter; Tid, 2026-11-22); ✅ Q52 (b), Q53 (a); ✅ il 6c, i pgTAP, verdi come app (§3.6-quater; Tid, 2026-11-22); ✅ committato il 2026-11-22; ⏳ `/verifica-db` un giro per volta, ciascuno sul suo commit e in una sessione nuova (Tid, 2026-11-22; vale anche per le verifiche dell'1a, del 2 e del 3 della riga 7): 1a ✅ (2026-11-22, un caso aggiunto al pgTAP, verde, §3.1-bis), 1b ✅ (2026-11-22, §3.1-ter; Q54 decisa (a) da Tid il 2026-11-22, da scrivere nel giro 7), 2 ✅ (2026-11-22, §3.2-bis; ne nascono Q55 e il COMMENT di `fn_intero_da_jsonb`, scritti in `20261122-26` … `-28` e migrati coi pgTAP verdi, Tid, 2026-11-22; ⏳ il loro `/verifica-db` ✅, 2026-11-22: un caso aggiunto al pgTAP, verde, Q57 a Tid), 3 ✅ (2026-11-22, §3.3-bis: Q58), 4 ✅ (2026-11-22, §3.4-bis: tre pgTAP rafforzati, quattro test del seed col BB, quattro riferimenti a oggetti ritirati), 5 ✅ (2026-11-23, §3.5-bis «La verifica»: un pgTAP rafforzato, tre pagine `manual/` e una guida corrette, il COMMENT delle preferenze a un changeSet futuro), 6a-6c ✅ (2026-11-22, §3.6-quater «La verifica»: due pgTAP rafforzati e verdi nella corsa di Tid, una pagina `manual/` e il riepilogo dei ritiri corretti, Q60 decisa (a) da Tid il 2026-11-22) | §3.6-bis | 7 |
| 8-ter | team BE/FE | Le ricadute del 6a, dopo l'apply: BE10, BE29, BE31; del 6b: BE18 (le note dei codici `E_UI_*`). ✅ Tutte fatte e verdi (2026-11-22), committate (`ecc51bf31a`, PR #204); ⏳ BE29 e il residuo di BE25 (2) a video | §6 | 8-bis |
| 8-quater | sessione DB | Giro 7, le decisioni dalle verifiche (via di Tid, 2026-11-22). ✅ Q57 (`20261122-34`), Q58 (`-35`, con BE33), il COMMENT di `ui.fn_misura_pagina_default` e la soluzione di `E_UI_CHIAMATA_NON_VALIDA`: scritti e provati sullo scratch, ✅ applicati su dbdev coi pgTAP verdi (Tid, 2026-11-22), doc auto-generata di `ui` rigenerata da Tid; ✅ Q54 (a) (`-36` … `-39`, il CSV del registro): scritto e provato sullo scratch, ✅ applicato su dbdev coi pgTAP verdi (Tid, 2026-11-22); ✅ la regola del 2, decisa da Tid il 2026-11-22 (il BB `dbops.fn_seed_elenco_colonne`, `-41` … `-43`): scritta e provata sullo scratch, ✅ applicata su dbdev coi pgTAP verdi (Tid, 2026-11-23); ✅ la doc auto-generata di `dbops` e `script` (`b006c276ec`); ✅ il `/verifica-db` del giro intero (2026-11-23, §3.6-quinquies «La verifica del giro 7»: un caso aggiunto al pgTAP del seed, una guida corretta) | §3.6-quinquies | 8-bis |
| 8-quinquies | team BE/FE | Le ricadute del giro 7 e il residuo di BE32: ✅ BE32 (la parte Q56: le preferenze non fermano più la cancellazione di una colonna) e ✅ BE33 (il FE legge `default_per_uso`) fatti e verdi (2026-11-23); ✅ committati su `dev/backend-tid` (`1a1720cdde`) | §6 | 8-quater |
| 8-sexies | sessione DB | Le due richieste di BE32 e BE33: il ritiro di `default_compatta` e `default_pagina` da `ui.fn_get_misure_pagina` (changeSet nuovo, con il caso 19 di `ui/test-misure-pagina-v1` e la pagina `manual/`), il messaggio di `E_UI_COLONNA_IN_USO` in `messaggi_errore.csv`. ✅ Scritte e provate sullo scratch (2026-11-23): `20261122-48`, il CSV, e con loro `20261122-49` (il COMMENT delle preferenze, §3.5-bis); ✅ applicate su dbdev coi pgTAP verdi, doc auto-generata di `ui` rigenerata (Tid, 2026-11-23); ⏳ il commit | §6, BE32 e BE33 | 8-quinquies, merge del BE |
| 8-septies | sessione DB | Giro 8, Q60 (a) qui (Tid, 2026-11-23): l'utente di sessione da `script.fn_utente_di_sessione`. ✅ `20261123-16` … `-25` scritti, provati, applicati coi pgTAP verdi (Tid, 2026-11-23); ✅ `-26` (`magazzino`) scritto, provato, applicato coi pgTAP verdi (Tid, 2026-11-23); ✅ giro 8b, le 177 policy (`-27` … `-36`), scritto, provato, applicato coi pgTAP verdi (Tid, 2026-11-23); ✅ la regola nella documentazione: l'utente della connessione si legge solo con `script.fn_utente_di_sessione` | §3.6-sexies | 8-sexies |
| 9 | sessione DB | Archiviazione in `work-done/` (Q60 si fa qui: riga 8-septies) | §10, §7.1 | 7, 8, 8-quater, 8-sexies, 8-septies |

**Decisioni di Tid:** Q1-Q11 prese il 2026-11-18, Q12-Q25 il 2026-11-19, Q26 il 2026-11-20 (registrate in §7 e nelle
schede dei difetti), Q27-Q36 il 2026-11-20 (§7.1). Q37-Q39 §7.1 e Q37-Q39 §6 il 2026-11-20 come raccomandate. Q40 (b),
Q41 (a) e Q42 (a) il 2026-11-21 (§7.1, dal piano del giro 2). Q43 (a) il 2026-11-21 (chi cambia per primo nel ritiro
di filtri e ordinamento: il BE, §7.1). Q44-Q46 il 2026-11-21 (§7.1, dal piano del giro 3). Q47 (a) e Q48 (a) il 2026-11-21 (§7.1, dal piano del giro 4). Q49 (a) il 2026-11-21 (§7.1, la dashboard spenta come la lista: giro 5). Q50 (a) il 2026-11-21 (§7.1, il «mai vuota» resta quello di luglio). BE8, la chiave a null: la toglie il FE (Tid, 2026-11-22, §3.2-bis). BE13 (il ritiro della normalizzazione «azione ⇒ non esportabile») confermato e BE14 (le fatture non chiedono la sintesi della genealogia) deciso da Tid il 2026-11-22. Q51 (c) il 2026-11-22 (§3.6). Q52 (b) e Q53 (a) il 2026-11-22 (§3.6-quater, il giro 6c dei pgTAP). Il `/verifica-db` un giro per volta, ciascuno sul suo commit, il 2026-11-22 (testata). Q55 (a) il 2026-11-22, con la forma «solo lucchetti» per gli UPDATE (§7.1). Q56 (a) il 2026-11-22 (§7.1: il BE ritira il rifiuto alla cancellazione di una colonna che una preferenza nomina, BE32). Q57 (a) e Q58 (a) il 2026-11-22 (§7.1, dai `/verifica-db` di Q55 e del giro 3). Q60 (a) il 2026-11-22 (§7.1, dal `/verifica-db` del giro 6: un BB in `script` per l'utente di sessione, in un brief nuovo). Q54 (a) il 2026-11-22 (§7.1, dal `/verifica-db` dell'1b: l'impronta torna vera nel momento del ritiro). **Nessuna decisione aperta.** ⚠️ **Numeri doppi** (trovati il 2026-11-21): Q37, Q38 e Q39 esistono due volte, in §7.1
(l'impronta, l'ignorato, la data per chiave: giro 1b) e in §6 (chi applica l'ordinamento, il ritiro dei filtri, il clic
che non si ricorda: giro 2); BE25 esiste due volte in §6 (il codice d'errore del giro 1b, l'ordinamento applicato del
giro 2). I due numeri sono citati in changeSet già committati e nel codice BE, quindi non si rinumera: si scrive
«Q38 §7.1» / «Q38 §6» e «BE25 (1b)» / «BE25 (2)». I numeri nuovi partono da Q43, BE26 e R-BE3. **Committato:** fino al giro 2
compreso (`eaed059e6e`, PR #183) e il giro 3 (§3.3-bis: changeSet `20261120-36` … `-42`, CSV, pgTAP, pagine `manual/`,
guida, Q44-Q46: `ea04ec5f4`, PR #184). **Committato** su `dev/db-tid` il 2026-11-22: i giri 6a, 6b e 6c. **Committate** su `dev/backend-tid` le ricadute BE/FE del 2026-11-22 (BE8, BE10, BE11,
BE12-BE15, BE17, BE20, BE21, BE25 (2), BE27, BE28, FE1 in `2caffd1ee0`; il giro 6 in `ecc51bf31a`, PR #204). **Committate** in `d265aaa463` (2026-11-22) le verifiche dell'1a, dell'1b e del giro 2 e Q55. **Committate** in `47677fd8bc` (2026-11-22):
le verifiche di Q55 e dei giri 3, 4 e 6 (2026-11-22, §3.2-bis, §3.3-bis, §3.4-bis «La verifica»): sette
pgTAP (`ui/test-ui-ritiro-voce-preferenze-v1`, `ui/test-ui-catalogo-liste-v1`, `ui/test-ui-catalogo-dashboard-v1`,
i quattro `ui/test-lista-*-seed`), sette pagine `manual/`, le testate di due caricatori di `80_data` (solo commenti)
e questo brief; e la verifica del giro 6 (§3.6-quater, «La verifica»): `ui/test-ui-liste-casi-del-modello-v1`,
`ui/test-ui-dashboard-casi-del-modello-v1` e la pagina `manual/` di `fn_misura_pagina_risolta`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-18; decisioni registrate fino al 2026-11-21. **A chi:** Tid e team DB.
> **Origine:** revisione della documentazione dello schema `ui` chiesta da Tid: allinearla allo standard e alle
> funzionalità, togliere le parti stantie, segnalare dove il codice non rispetta ciò che è scritto. Metodo dei brief di
> revisione di `catalogo`, `dbops` e `documenti`
> ([brief-db-revisione-documenti](../work-done/2026/brief-db-revisione-documenti.md)).
> **Brief vicini verificati:** [sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md) tiene
> gli sviluppi non fatti delle liste (viste nominate, condivisione) e la domanda sulle dashboard: sono funzionalità
> nuove, non revisione, e qui non si toccano. [piano-be-fe-endpoint-senza-porta](piano-be-fe-endpoint-senza-porta.md)
> cita una lista di `ui` solo come fatto. Nel [registro dei residui](registro-residui-aperti.md) nessuna voce ha per
> oggetto le tabelle o le funzioni di `ui`. ⚠️ Mancava, trovato il 2026-11-20:
> [brief-db-seed-primo-impianto-non-si-riscrive](../work-done/2026/brief-db-seed-primo-impianto-non-si-riscrive.md). Le tabelle di catalogo
> di `ui` sono mirror `runOnChange` (`loadUpdateData`) che l'app scrive dalle pagine admin: il suo caso esatto, e il
> suo §7 rimanda il censimento di queste tabelle al suo giro 1. Deciso da Tid il 2026-11-20 (Q27): le tabelle si
> dichiarano nel censimento di quel brief, e i giri di qui che toccano i CSV di `ui` partono dopo.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/ui/…`), rigenerata il
2026-11-14. Nessun changeSet successivo tocca gli oggetti di `ui` (verificato il 2026-11-18). Il giro 0 ha letto i corpi
dal catalogo di dbdev. Prima di scrivere un giro si riverifica: un changeSet successivo sull'oggetto rende stantia la
doc auto-generata.

## 1. Il perimetro

Lo schema `ui` ha 13 tabelle in tre famiglie e 19 funzioni (8 funzioni e 11 trigger function); non ha viste:

* **le liste**: definizione, colonne, permessi di colonna, preset, composizione del preset, preferenza dell'utente;
* **le misure di pagina**: il catalogo delle righe per pagina;
* **le dashboard**: definizione, catalogo dei widget, pool, preset, composizione, preferenza.

Si contano anche i trigger generici montati sulle tabelle (regola ATTIVO, audit), le eccezioni ATTIVO di `dbops` che le
riguardano e le copie della stessa regola trovate nel backend.

Ogni difetto si regge sul **modello**: che cosa ammettono colonne, vincoli e corpi. Nessun conteggio di righe entra come
motivo; dove compare un numero, è un fatto datato al 2026-11-18.

**Un fatto del modello, non un difetto.** `ui` non segue il modello «una scrittura = un verbo»: `zeroerp_app` ha
INSERT, UPDATE e DELETE diretti su tutte le tabelle tranne `misure_pagina`, che legge soltanto, e nessuna tabella ha
RLS. Il dominio ci passerà quando un cantiere toccherà le sue scritture (PROJECT_CONTEXT, «I domini nuovi nascono con il
permesso applicato dal DB»). Diversi difetti qui sotto sono regole che oggi tiene solo il backend: su un dominio a verbi
starebbero nel verbo.

## 2. Il piano: i giri

Deciso da Tid il 2026-11-19 (Q24): i giri nell'ordine della tabella; il giro 1 diviso in 1a e 1b il 2026-11-20 (Q36).
Ogni giro che tocca un CSV di `ui` parte dopo il censimento del brief del seed (Q27). L'ordine è per gravità. I lavori sugli stessi oggetti vanno insieme, perché ogni tabella si apra una
volta sola, e liste e dashboard si correggono nello stesso giro: dove sono gemelle, una copia corretta da sola
diverge dall'altra. Ogni giro comprende changeSet, pgTAP che costruiscono i propri soggetti, COMMENT e pagine `manual/`
riallineati (la riga di «⚠️ Che cosa oggi non copre» del difetto chiuso si toglie); poi l'apply di Tid e il via al giro
dopo.

| Giro | Classe | Contenuto | Ricadute BE/FE | Perché insieme |
| --- | --- | --- | --- | --- |
| 1a | A + B + C | **Il preset di base.** U1 (lo snapshot scritto dal DB), U2, U3, U4 con Q28, U5, U7, U9; il ritiro di `is_default` (Q26) con l'UNIQUE di Q30 | BE5, BE6, BE22 | I due resolver e i due trigger z90: la scelta del preset di base |
| 1b | B + C | **Il banner per chiave.** U6 con la forma di Q29, U8, Q33 col mezzo di Q37, Q38, Q39 (§3.1-ter) | BE7, BE25 | `trgfn_preset_*`, lo snapshot e l'ignorato per chiave, il flag del preset aggiornato |
| 2 | A + B + C | **La forma della preferenza e i widget nuovi.** U10-U14; U19 (il BB della misura, letto dal guard di forma); il tetto 1-100 di `dimensione_max` nella preferenza (U21, parte del guard di forma) | BE8, BE9, BE11, BE20 | Il guard di forma comune a liste e dashboard, il conteggio dei nuovi, ordinamento e filtri, i legami fra preset, colonne e pool |
| 3 | A + B | **Le misure.** U15-U18, U20; U21 sul preset (CHECK, l'8 in una sede) | BE10, FE1 | `misure_pagina`, i guard di `pagina_dimensione`, `dimensione_max` della dashboard |
| 4 | B + C | **Il catalogo delle liste.** U22-U30 (U22 con Q35, U27 con il presidio di Q32); U37 (si riscrive `valida_campo_sorgente`) | BE12-BE15 | `lista_definizione`, `lista_colonna`, i loro trigger e i permessi di colonna |
| 5 | B + C | **Il catalogo delle dashboard.** U31-U36 (U32 col constraint trigger differito di Q31); in chiusura la guida `configurazione-dashboard` (Q25) | BE17 | Le cinque tabelle che l'app non scrive, il widget |
| 6 | C | **Pulizia.** Metadati (§4), codici errore, pgTAP deboli (§5), U38 (con il codice d'errore di Q35), U39 | BE18 | Ciò che nessun giro precedente ha già aperto |

## 3. I difetti di codice

Forma compatta: **fatto** · **correzione proposta** · **presidio**. Le classi sono quelle dei brief precedenti:

* **A**: contraddice un contratto deciso, oppure è sbagliato ogni volta che il ramo si percorre;
* **B**: un caso che il modello ammette e che non è gestito;
* **C**: pulizia, doppie sedi.

La colonna «Aree» rimanda ai rapporti del giro 0 (A catalogo delle liste, B preset e risoluzione, C misure, D
dashboard, E guida). Dove due aree hanno trovato lo stesso difetto, qui è una voce sola.

| Classe | Difetti |
| --- | --- |
| **A** | U1, U10, U15 |
| **B** | U2, U3, U4, U5, U6, U7, U11, U12, U13, U14, U16, U17, U18, U20, U21, U22, U23, U24, U25, U26, U27, U28, U29, U31, U32 |
| **C** | U8, U9, U19, U30, U33, U34, U35, U36, U37, U38, U39 |

### 3.1 Giri 1a e 1b — il preset di base e il banner

**U1 (A) — Il trigger z90 cancella lo snapshot appena scritto** · aree B, D · Q1.

* **Fatto.** `trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts` e il gemello delle dashboard sono
  `BEFORE UPDATE OF preset_base_id`: se il preset di base cambia, azzerano `preset_base_contenuto_aggiornato_il` e
  `preset_aggiornato_ignored_at`. L'upsert del BE (`backend/apps/ui/db/ui_repository.py:346`,
  `dashboard_repository.py:136-140`) scrive nella stessa istruzione il preset nuovo e il suo snapshot, e il trigger
  azzera lo snapshot. Così, ogni volta che un salvataggio cambia il preset di base, il banner del preset aggiornato
  resta muto fino al salvataggio successivo. Verificato sul corpo il 2026-11-18. Un pgTAP
  (`test-fn-resolve-lista-config-cascata-per-chiave-v1.sql:321-325`) lo aggira con un secondo UPDATE. I due corpi sono
  identici riga per riga.
* **Correzione proposta.** (a) Il trigger azzera lo snapshot solo se lo stesso UPDATE non ne porta uno nuovo. (b) Lo
  snapshot lo scrive il DB, leggendo il contenuto del preset di base. **Raccomandata (b)**, insieme a U2. In tutte e due
  le strade c'è una funzione sola, montata sulle due tabelle.
* **Decisione (Q1, Tid, 2026-11-18).** (b): lo snapshot lo scrive il DB, leggendolo dal preset di base; una funzione sola sulle due tabelle.
* **Presidio.** Due preset costruiti: una preferenza su A, poi l'upsert su B. Lo snapshot deve essere quello di B, e il
  flag si deve accendere quando B cambia.

**U2 (B) — Il preset di base salvato non è quello usato: la cascata ha una copia nel BE** · aree B, D · Q2.

* **Fatto.** Il resolver non espone il preset di base. Il BE lo ricalcola con una copia sua della cascata
  (`ui_repository.py:69-145`, `fetch_preset_base_snapshot`, che si dichiara «drift risk»). La copia prende il primo
  preset di default acceso; il DB prende il primo con una colonna o un widget acceso. In più `_GUC_VESTE_EXPR` (`:32`)
  fallisce su una veste fuori dominio, dove `fn_veste_corrente` ripiega su NULL. Quando le due scelte differiscono, il
  banner confronta un preset diverso da quello che l'utente vede.
* **Correzione proposta.** Il resolver espone una chiave additiva `preset_base` (id e data del contenuto), per le liste e
  le dashboard. Il BE salva quella e ritira la copia nello stesso cantiere (regola del 2).
* **Decisione (Q2, Tid, 2026-11-18).** Sì: chiave additiva `preset_base` nei due resolver; il BE ritira la sua copia della cascata nello stesso cantiere.
* **Presidio.** Un preset di ruolo senza colonne accese e uno di sistema: `preset_base` deve essere quello di sistema.

**U3 (B) — La scelta del preset di base guarda il primo preset di ruolo, e non il pool** · aree B, D.

* **Fatto.** Al passo del ruolo, `ORDER BY pa.priorita LIMIT 1` prende il preset del profilo più prioritario. Se quel
  preset non ha colonne accese, la cascata scende all'azienda senza guardare i profili successivi, mentre COMMENT ed
  eccezione ATTIVO dicono «il primo con colonne». Se nessun preset ha colonne, le colonne vengono dal catalogo, ma
  ordinamento, filtri e misura (con la loro `origine`) vengono dall'ultimo preset trovato. Nella dashboard la base
  chiede solo «almeno un widget acceso», non che il widget stia nel pool: un preset fatto di widget fuori dal pool
  vince, e la home mostra solo le card aggiunte, spente.
* **Correzione proposta.** Il filtro «almeno una colonna accesa», e per la dashboard «almeno un widget acceso nel pool»,
  dentro la query di ogni livello, prima del `LIMIT`. Un solo preset di base per la risoluzione, oppure nessuno.
* **Presidio.** Due profili costruiti, il primo con un preset senza colonne accese: deve vincere il secondo. Un preset di
  ruolo della dashboard con widget fuori dal pool: deve vincere quello di sistema.

**U4 (B) — A parità di priorità il preset di ruolo è scelto a caso** · aree B, D.

* **Fatto.** Né i due resolver né la copia del BE (`ui_repository.py:95`) hanno uno spareggio. Con la veste NULL,
  `script.fn_get_profili_accesso_applicabili` può dare due PORTALE di uguale priorità (lo dice il suo commento). Il
  COMMENT del resolver delle dashboard dice «deterministico per priorita».
* **Correzione proposta.** ~~Lo spareggio esplicito, sull'id del preset.~~ Superata il 2026-11-20: un esito che
  dipende da un id è un'ambiguità del modello (Regola zero). La parità nasce dalla veste NULL, e la correzione sta nel
  suo significato, uno solo per preset e permessi.
* **Decisione (Q28, Tid, 2026-11-20).** (a): con la veste NULL il passo del ruolo si salta, e la cascata parte
  dall'azienda; i permessi di colonna restano al più restrittivo fra le vesti (Q17). Il ripiego non allarga mai, e la
  parità non può più nascere. Lo stesso nel resolver delle dashboard, e il COMMENT «deterministico per priorita» (M7)
  si riscrive su questa regola.
* **Presidio.** Due binding PORTALE costruiti, veste NULL: vince il preset d'azienda, o quello di sistema.

**U5 (B) — Il banner legge il preset salvato anche se è spento o non è più la base** · aree B, D · Q3.

* **Fatto.** Il passo del flag legge `contenuto_aggiornato_il` per `id = preset_base_id`, senza guardare `attivo` né se
  quel preset è ancora la base dell'utente. Un preset spento, o non più base, accende il banner se cambia. Il motivo
  dell'eccezione ATTIVO («ripiegano già sul livello successivo») vale per la cascata, non per il flag.
* **Correzione proposta.** (a) Il flag tace se il preset salvato non è la base di oggi. (b) Un esito suo, «base
  cambiata», che propone il riallineamento. **Raccomandata (b)**, come chiave additiva.
* **Decisione (Q3, Tid, 2026-11-18).** (b): un esito suo, «base cambiata», come chiave additiva.
* **Presidio.** Un preset spento dopo il salvataggio, poi modificato: il flag resta spento, oppure dà l'esito nuovo.

**U6 (B) — Il banner si accende per chiavi che seguono già il preset** · area B · Q4.

* **Fatto.** La cascata è per chiave, ma la data del contenuto è una per tutto il preset. Una preferenza di sola misura
  vede il banner quando cambia l'ordinamento, che le arriva già.
* **Correzione proposta.** (a) Una data del contenuto per chiave (colonne, ordinamento, filtri, misura), e il flag guarda
  solo le chiavi di origine `preferenza`. (b) Resta per preset intero. **Raccomandata (a).**
* **Decisione (Q4, Tid, 2026-11-18).** (a): una data del contenuto per chiave sul preset; il flag guarda solo le chiavi di origine `preferenza`.
* **Decisione (Q29, Tid, 2026-11-20), che completa Q4 dal lato della preferenza.** (a): lo snapshot
  (`preset_base_contenuto_aggiornato_il`, scritto dal DB per Q1) e l'ignorato (`preset_aggiornato_ignored_at`) diventano
  un JSONB `{chiave: data}` ciascuno, con le chiavi validate dal guard di forma (Q6). Le chiavi sono quelle della
  `configurazione`: `colonne`, `ordinamento`, `filtri`, `pagina_dimensione` per le liste; `widget`, `dimensione_max` per le
  dashboard. Una chiave nuova non chiede DDL. Giro 1b.
* **Presidio.** Una preferenza di sola misura e un cambio di `ordinamento_default`: il flag resta spento.

**U7 (B) — Il preset di un'azienda spenta si applica** · area D (e le liste, stessa forma) · Q5.

* **Fatto.** Il passo dell'azienda confronta `p_emittente_fiscale_id` senza guardare `emittenti_fiscali.attivo`. I
  motivi delle eccezioni ATTIVO dei preset d'azienda dicono che quel preset «non si applica già». Per i profili è vero,
  perché li filtra `fn_get_profili_accesso_applicabili`; per l'azienda no.
* **Correzione proposta.** (a) Il join sull'azienda accesa. (b) Il motivo dell'eccezione corretto. **Raccomandata (a).**
* **Decisione (Q5, Tid, 2026-11-18).** (a): il passo dell'azienda considera solo le aziende accese, nelle due cascate.
* **Presidio.** Il preset di un'azienda spenta: si ripiega sul sistema.

**U8 (C) — La data del contenuto del preset si scrive a mano** · area B.

* **Fatto.** `contenuto_aggiornato_il` si scrive con un INSERT o un UPDATE dell'app senza toccare il contenuto (lo fa
  anche un pgTAP del flag).
* **Correzione proposta.** Un lucchetto: la colonna la scrivono solo i due trigger `trgfn_preset_*`.
* **Presidio.** UPDATE diretto della colonna come app, rifiutato.

**U9 (C) — La lettura del preset è scritta tre volte in ogni resolver** · aree B, D.

* **Fatto.** In ciascuno dei due resolver i tre livelli (ruolo, azienda, sistema) ripetono la stessa sotto-query.
  `fn_get_profili_accesso_applicabili` è chiamata due volte nello stesso resolver delle liste. Il calcolo del flag è
  ripetuto fra liste e dashboard.
* **Correzione proposta.** Si unifica nel giro 1, che riapre comunque le due funzioni: un BB per la scelta del preset di
  base e uno per il flag, letti dai due resolver.

### 3.1-bis Il piano del giro 1a (sessione DB, 2026-11-20)

Corpi vivi letti da `pg_get_functiondef` su dbdev il 2026-11-20 (uguali alla doc auto-generata). ChangeSet dal range di
Tid, dopo `20261119-08`.

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `ui.fn_preset_di_base(p_famiglia, p_contenitore_id, p_auth_user_id, p_veste, p_emittente_fiscale_id)` | Il BB della scelta, uno per le due famiglie (`'lista'`, `'dashboard'`): un candidato vale se è acceso e ha contenuto (una colonna attiva; un widget acceso **nel pool**); ruolo solo con la veste valorizzata, azienda solo accesa, poi sistema; ordine per livello e priorità del profilo. Restituisce id, ambito e `contenuto_aggiornato_il`, oppure nessuna riga | U3, U4/Q28, U7, U9 |
| `ui.fn_preset_aggiornato(snapshot, contenuto, ignorato)` | Il BB del flag, IMMUTABLE; il giro 1b lo porta per chiave (Q29) | U9 |
| I due resolver | 2b-2d sostituiti dalla chiamata al BB e da una lettura del preset scelto; il passo 1 (`fn_get_profili_accesso_applicabili`) esce, lo legge il BB. Chiavi additive: `preset_base` (`{id, ambito, contenuto_aggiornato_il}` oppure `null`) e `preset_base_cambiato` (la preferenza ha un preset di base salvato e non è quello di oggi). Il flag si calcola solo quando la base salvata è quella di oggi, dal contenuto che il BB ha già letto | U2, U5/Q3 |
| `ui.trgfn_preferenza_preset_base_snapshot()` | Una funzione sola sulle due preferenze (`TG_ARGV[0]` = la tabella dei preset), `BEFORE INSERT OR UPDATE OF preset_base_id, preset_base_contenuto_aggiornato_il`: lo snapshot lo scrive il DB dal preset di base, quello che arriva dall'app non conta; se la base cambia, l'ignorato si azzera. Sostituisce i due z90, che si tolgono | U1/Q1 |
| `is_default` | Si spengono i preset accesi con `is_default = false` (il resolver non li ha mai applicati: il comportamento resta identico; dbdev 2026-11-20: zero), poi `DROP COLUMN` su liste e dashboard (gli indici `uq_*_default` cadono con lei) e l'UNIQUE parziale `WHERE attivo` sul posto, `NULLS NOT DISTINCT` (linee-guida-sql §8.4-bis). Il loader e il CSV dei due preset senza la colonna; la riga 5 del registro del seed senza `is_default` | Q26, Q30 |
| pgTAP | I quindici che scrivono `is_default` sui preset (tredici in `ui`, due in `vendite`); i presidi di U1-U5, U7; i test dello z90 che lo aggiravano (`…-cascata-per-chiave-v1:321-325`, `…-preset-aggiornato-v1` caso F) | |

**Chi cambia per primo.** Il DB. Dopo l'apply il BE che scrive `is_default` si rompe (BE22): rottura accettata in sviluppo,
la richiesta al team parte con l'apply insieme a BE5, BE6, BE7, BE23.

**Lo stato (2026-11-20).** Scritti `20261119-09` … `-14`, il loader e il CSV dei due preset senza `is_default`, la riga 5
del registro del seed; quindici pgTAP adeguati e `ui/test-fn-preset-di-base-v1` nuovo (20 test). Provato sullo scratch
(`prova_changeset.py`, con uno YAML di prova per la riga del registro e la convergenza): estratto per intero, catalogo
identico dopo il ROLLBACK; il test nuovo 20 ok; dei quindici, tredici con gli stessi verdi o di piu' e nessun rosso nuovo,
`test-fn-resolve-dashboard-config` e `test-misure-pagina-v1` con i rossi che avevano gia' da owner (sono test da app).
⚠️ Corretto dopo l'apply: i rossi 6 e 10 di `test-fn-resolve-dashboard-config` non erano del runner ma di Q28. Il file
girava con la veste NULL, e ora il ruolo non concorre senza veste. Il file dichiara ora CLIENTE_PORTALE, la veste della
sua fixture, come il gemello delle liste: era la domanda che brief-db-pgtap-runner-rls-baseline §11 lasciava al
cantiere `ui`. ✅ Applicato da Tid il 2026-11-20, pgTAP verdi, doc auto-generata rigenerata. Restano al giro 1b U6, U8, Q29, Q33; i marcatori di cronaca dentro i corpi dei
resolver (§4.3) li toglie l'1b, che li riscrive di nuovo: qui sono riscritte la testata e il COMMENT.

**La verifica (`/verifica-db 8668768481`, sessione DB, 2026-11-22).** Sul commit, già applicato e su `main`.
Nessun difetto nei changeSet: i numeri del 20261119 non sono doppi; i due loader toccati (`20260507-08`, `20260722-04`)
sono `loadUpdateData` `runOnChange` di `80_data`, e i loro CSV non hanno due preset accesi nello stesso posto; su un
database da zero la catena regge, perché le versioni dei resolver che leggono `is_default` sono plpgsql (corpo non
validato alla creazione) e nessun seed scrive la colonna; `is_default` non ha più lettori in pgTAP, viste, CSV e pagine
`manual/`. `fn_preset_di_base`, il trigger dello snapshot e i nomi dei trigger sono stati riscritti dai giri 1b, 2 e 5:
il corpo di oggi non porta difetti dell'1a. **Corretto:** `ui/test-fn-preset-di-base-v1` non costruiva il presidio di U3
sul ruolo (due profili, il primo con un preset senza colonne attive): il test aveva un profilo solo, e il difetto che U3
correggeva non lo copriva nessun caso. Aggiunto il caso 25: preset di ruolo vuoto per il profilo AD_HOC (priorità 1),
con una colonna attiva per il PORTALE della veste OPERATORE (priorità 3, costruito se il seed non lo porta); vince il
secondo. Senza un PORTALE applicabile il preset nasce senza profilo e lo rifiuta il CHECK dell'ambito: rosso, non verde
a vuoto. Corretta anche la testata («plan 20» → 25). ✅ Verde, 25/25 (Tid, 2026-11-22).

⚠️ **Residuo del giro 1a, trovato il 2026-11-20 dalla sessione che prepara l'1b.** I COMMENT di tre colonne non sono
stati riscritti: `preset_base_contenuto_aggiornato_il` delle due preferenze dice ancora «NULL se il preset di base
cambia (trigger z90)»; `lista_preferenza_utente.preset_aggiornato_ignored_at` dice ancora «DEF-2» e «confronta con
`lista_preset.data_update`» (M5); il gemello delle dashboard non ha COMMENT. L'1b cambia la forma di queste colonne e li
riscrive comunque.

### 3.1-ter Il piano del giro 1b (sessione DB, 2026-11-20) — applicato, pgTAP verdi

Corpi vivi letti da dbdev il 2026-11-20 (trigger da `pg_get_triggerdef`, colonne e dipendenze da `pg_attribute` e
`pg_depend`): uguali alla doc auto-generata, rigenerata dopo il giro 1a. Nessun changeSet dopo `20261119-14` tocca
oggetti di `ui` (`20261120-01` è su `vendite`).

**Che cosa ha trovato la verifica, prima di scrivere.**

* **Q33 non regge sul suo controesempio.** Provato su dbdev il 2026-11-20, su tabelle temporanee in una transazione
  annullata. PostgreSQL rifiuta le transition table su un trigger con più di un evento («non si può specificare una
  tabella di transizione per trigger con più di un evento»): servono tre trigger, uno per evento. Il punto che decide è
  un altro: il DELETE + INSERT identico del BE sono **due istruzioni**, e ciascun trigger vede solo la sua. Il DELETE
  vede «tolte tutte», l'INSERT vede «aggiunte tutte», e nessuno dei due può concludere «insieme uguale». Lo stesso
  succede con le due operazioni in un'istruzione sola (CTE scrivibile): i trigger per istruzione scattano separati per
  evento. Un constraint trigger differito, che vedrebbe la fine della transazione, esiste solo `FOR EACH ROW` (errore
  di sintassi su `FOR EACH STATEMENT`). → Q37.
* **`contenuto_aggiornato_il` ha un secondo lettore, che il brief non nominava**: il seed di primo impianto (giro 3 del
  [brief del seed](../work-done/2026/brief-db-seed-primo-impianto-non-si-riscrive.md), §16.15, QU1-QU2). La colonna è
  dell'installazione nella riga 5 del registro, e una scrittura dell'app che la sposta rende personalizzato il preset:
  da quel momento il migrate non riscrive più la sua composizione. Oggi il DELETE + INSERT identico del BE personalizza
  per finta un preset di seed. Q37 corregge anche questo. Ne segue un vincolo per il giro: la colonna **resta** (cambia
  forma, non nome) e ogni colonna nuova del preset entra nella riga 5 del registro, o la tabella diventa
  `NON_CLASSIFICATA`.
* **L'ignorato non serve, se lo snapshot lo scrive il DB.** Il flag di oggi è
  `contenuto > snapshot AND (ignorato IS NULL OR ignorato < contenuto)`, cioè `contenuto > max(snapshot, ignorato)`:
  conta solo il più recente dei due. Dal giro 1a ogni scrittura che nomina `preset_base_id` riallinea lo snapshot al
  contenuto di oggi (Q1). «Ignora» può essere quella scrittura: il banner si spegne e si riaccende al cambio successivo
  del preset, come oggi. Per chiave vale lo stesso: riallineare anche le chiavi che non sono in banner non cambia niente,
  perché quelle hanno già `contenuto ≤ snapshot`, oppure seguono il preset e il flag non le guarda. → Q38.
* **La forma della data per chiave lato preset non è decisa.** Q4 dice «una data per chiave sul preset»; Q29 dà la
  forma solo dal lato della preferenza. → Q39.

**I pezzi** (nella forma di Q37-Q39, decise come raccomandate; le differenze dalla scrittura sono in «Lo stato», qui sotto):

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `contenuto_aggiornato_il` dei due preset | Da `timestamptz` a `jsonb` `{chiave: data}`, stesso nome (Q39): `colonne`, `ordinamento`, `filtri`, `pagina_dimensione` per le liste; `widget`, `dimensione_max` per le dashboard. Le righe esistenti hanno tutte le chiavi alla data che la colonna porta oggi, non a `now()` (il banner resta identico). `DEFAULT` tolto: la scrive il trigger | U6/Q4 |
| `composizione_impronta` dei due preset (Q37) | Colonna nuova, `text NOT NULL`: l'impronta della composizione (le righe del preset, ordinate). Entra fra le colonne dell'installazione nella riga 5 del registro del seed | Q33 |
| `ui.fn_preset_impronta(p_famiglia, p_preset_id)` (Q37) | Il BB dell'impronta, `STABLE`: una sede per i due trigger qui sotto | Q33 |
| `ui.trgfn_preset_contenuto_aggiornato()` | `BEFORE INSERT OR UPDATE`, senza `WHEN`: all'INSERT tutte le chiavi a `now()`; all'UPDATE riparte da `OLD` (il lucchetto di U8: scritto come rifiuto, «Lo stato»), sposta le chiavi le cui colonne sono cambiate e ricalcola l'impronta: se è diversa da `OLD`, sposta `colonne` (o `widget`) | U6, U8 |
| `ui.trgfn_preset_riga_tocca_preset()` (Q37) | Diventa un constraint trigger `DEFERRABLE INITIALLY DEFERRED`, per riga: a fine transazione tocca il preset solo se l'impronta di oggi è diversa da quella salvata. Un DELETE + INSERT identico, e la riscrittura del seed, non spostano niente | Q33 |
| Snapshot delle due preferenze | `preset_base_contenuto_aggiornato_il` da `timestamptz` a `jsonb`, la copia della mappa del preset di base; lo scrive `trgfn_preferenza_preset_base_snapshot` come oggi. Le righe esistenti: ogni chiave a `max(snapshot, ignorato)`, che conserva il banner di oggi | U6/Q29 |
| `preset_aggiornato_ignored_at` delle due preferenze (Q38) | Si ritira (`DROP COLUMN`); «Ignora» è una scrittura che nomina `preset_base_id`. Con Q38 (b): `jsonb` come lo snapshot | Q29 |
| `ui.fn_preset_aggiornato` | Nuova firma `(p_snapshot jsonb, p_contenuto jsonb, p_chiavi text[]) RETURNS text[]`, ~~`IMMUTABLE`~~ `STABLE` («Lo stato», qui sotto): le chiavi del banner, fra quelle di origine `preferenza`. La firma vecchia si toglie (`DROP`), non resta un overload | U6 |
| `ui.fn_preset_di_base` | Restituisce la mappa `jsonb`. `DROP` + `CREATE`: il corpo `BEGIN ATOMIC` dipende dalla colonna, e l'`ALTER TYPE` non passa finché c'è | — |
| I due resolver | Il flag per chiave sulle sole chiavi di origine `preferenza`; chiave additiva `preset_aggiornato_chiavi` (l'elenco); `preset_base.contenuto_aggiornato_il` diventa la mappa. Via i marcatori di cronaca dai corpi (§4.3) e M6, M7 nei COMMENT | U6, M6, M7 |
| COMMENT | Le colonne toccate (compreso il residuo dell'1a qui sopra, M5) e le funzioni riscritte, secondo §5d | M5 |
| pgTAP | I cinque che leggono le tre colonne (`…-cascata-per-chiave-v1` liste e dashboard, `…-preset-aggiornato-v1`, `test-fn-preset-di-base-v1`, `test-ui-nell-ambito-v1`). Presidi nuovi: U6 (preferenza di sola misura, cambia l'ordinamento: flag spento); U8 (l'app scrive la mappa: rifiutata); Q33 (DELETE + INSERT identico: data ferma; un cambio vero: data spostata); Q38 («Ignora» spegne il banner, il cambio dopo lo riaccende). ⚠️ Il trigger differito scatta al commit: i pgTAP che lo provano chiedono `SET CONSTRAINTS … IMMEDIATE` | |
| Doc | Le pagine `manual/` delle funzioni e delle tabelle toccate, `fn_preset_impronta` nuova; la guida `configurazione-liste` dove parla del banner | |

**Ordine dentro il giro.** Prima i `DROP` di ciò che dipende dalle colonne (i due trigger dello snapshot, che le nominano
in `UPDATE OF`; `fn_preset_di_base`; la firma vecchia di `fn_preset_aggiornato`). Poi gli `ALTER` con la conversione
delle righe, poi le funzioni e i trigger nuovi.

**Garanzie ritirate** (AGENTS.md, «Una garanzia ritirata si censisce in tutti i lettori»):

| Oggetto | La proprietà che i lettori davano per scontata | Lettori lato DB, con l'esito |
| --- | --- | --- |
| `contenuto_aggiornato_il` dei preset | È un `timestamptz`, uno per preset | I due resolver, `fn_preset_di_base`, `fn_preset_aggiornato`, i tre trigger di `ui`: si riscrivono nel giro. Il meccanismo del seed la legge per nome dal registro, non per tipo: non ne dipende |
| La stessa colonna | Dopo una scrittura della composizione è già spostata, nella stessa transazione | Il seed (QU2): la personalizzazione si registra al commit della transazione dell'app; nella stessa transazione non c'è un migrate che la legga. Non ne dipende |
| `preset_base_contenuto_aggiornato_il` | È un `timestamptz` | I due resolver e il trigger dello snapshot: si riscrivono nel giro |
| `preset_aggiornato_ignored_at` | Esiste, e la scrive il BE | Nessun lettore DB oltre ai resolver, riscritti nel giro |

Lato BE/FE la richiesta è BE7 riscritta (§6): **«censisci i lettori di `contenuto_aggiornato_il` (preset),
`preset_base.contenuto_aggiornato_il` (resolver), `preset_base_contenuto_aggiornato_il` e
`preset_aggiornato_ignored_at` (preferenze) che contano su un `timestamptz`, o sull'esistenza dell'ignorato»**.

**Chi cambia per primo.** Il DB. Dopo l'apply si rompe il BE che scrive `preset_aggiornato_ignored_at` (rottura
accettata in sviluppo); la richiesta parte con l'apply.

**Lo stato (2026-11-20).** Scritti `20261120-02` … `-11`:

| ChangeSet | Che cosa |
| --- | --- |
| `-02` (`00_schema`) | `composizione_impronta` nasce nuda sui due preset |
| `-03` (`20_code`) | `ui.fn_preset_impronta`, col risultato ancorato alla colonna (`%TYPE`) |
| `-04` (`00_schema`) | i `DROP` di ciò che blocca l'`ALTER TYPE`; le tre colonne a `jsonb` con la conversione delle righe; il backfill dell'impronta coi trigger spenti per nome; `NOT NULL`; via l'ignorato; i COMMENT di colonna (compreso il residuo dell'1a) |
| `-05` | `ui.trgfn_preset_contenuto_aggiornato`: guard e derivazione, `BEFORE INSERT OR UPDATE` senza `WHEN`, rimontato per funzione coi nomi storici |
| `-06` | `ui.trgfn_preset_riga_tocca_preset`: constraint trigger differito, scrive l'impronta solo se è cambiata |
| `-07` | `ui.fn_preset_aggiornato(jsonb, jsonb, text[]) RETURNS text[]`, la firma vecchia tolta |
| `-08` | `ui.fn_preset_di_base` ricreata, corpo identico |
| `-09` | `ui.trgfn_preferenza_preset_base_snapshot` senza l'ignorato; i due trigger rimontati |
| `-10`, `-11` | i due resolver: banner per chiave, `preset_aggiornato_chiavi`, via i marcatori di cronaca dei corpi (§4.3), M6, M7 |
| `80_data` | riga 5 del registro del seed con `composizione_impronta` fra le colonne dell'installazione; `E_UI_PRESET_CONTENUTO_DERIVATO` in `codici_errore.csv` e `messaggi_errore.csv` (id 1517) |

Quattro scelte della scrittura che il piano non diceva, sul modello:

* **Il lucchetto di U8 rifiuta, non ignora** (`E_UI_PRESET_CONTENUTO_DERIVATO`, come diceva il presidio di U8; il
  piano qui sopra diceva «ignorata»). Il trigger del seed (`a00`) giudica la personalizzazione sul valore scritto,
  prima della derivazione: una scrittura ignorata personalizzerebbe per finta un preset di seed. Rifiuta chi scrive
  la data, e chi scrive un'impronta diversa da quella della composizione di oggi; l'impronta vera la scrive solo il
  trigger differito, ed è il valore che il seed vede cambiare.
* **L'ora è `clock_timestamp()`, non `now()`.** Con `now()` un cambio del preset nella stessa transazione dopo lo
  snapshot ha la stessa data dello snapshot, e il banner non lo vede mai. Ne segue che i pgTAP non retrodatano più:
  salvano la mappa e guardano le chiavi che si spostano.
* **La colonna nasce prima della funzione** (`-02`, poi `-03`), perché la funzione ancori il risultato con `%TYPE`
  (Tid, 2026-11-20). Il giro ha preso un numero in più del piano.
* **`ui.fn_preset_aggiornato` è `STABLE`, non `IMMUTABLE`** come diceva il piano: legge le date dalla mappa con
  `::timestamptz` da testo, una conversione che dipende dalla sessione (`TimeZone`, `DateStyle`). Trovato dal
  `/verifica-db` del 2026-11-20, che allinea qui il piano al codice.

**Le prove.** `scripts/prova_changeset.py` sullo scratch, i dieci changeSet più uno YAML di prova (nello scratchpad)
che fa ciò che fanno i mirror di `80_data` e la rete di `90_end`: la riga 5 del registro, il runner del seed, il
codice d'errore. Estratto eseguito per intero, catalogo identico dopo il ROLLBACK. pgTAP (da owner):

| pgTAP | Senza → con l'estratto |
| --- | --- |
| `ui/test-ui-nell-ambito-v1` (adeguato) | 6/2 rossi, interrotto → 10/0 |
| `ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1` (adeguato, 11 → 13) | 5/0, interrotto → 13/0 |
| `ui/test-fn-resolve-lista-config-cascata-per-chiave-v1` (adeguato, 19 → 22) | 10/0, interrotto → 22/0 |
| `ui/test-fn-preset-di-base-v1` (adeguato, 20 → 24) | 0/0, interrotto → 24/0 |
| `ui/test-fn-resolve-lista-config-preset-aggiornato-v1` (riscritto) | 4/2 → 6/0 |
| `ui/test-seed-primo-impianto-ui-installazione-v1` (18 → 19) | 13/6 → 13/6: i sei rossi di prima, da owner (test da app) |
| `ui/test-seed-primo-impianto-ui-software-v1`, `ui/test-fn-resolve-dashboard-config` | 16/0 → 16/0; 12/0 → 12/0 |
| `script/test-catalogo-messaggi-errore-completo`, `dbops/test-riferimenti-morti-v1` | 7/0 → 7/0; 12/0 → 12/0 |

⚠️ Il caso 18 di `…-lista-config-cascata-per-chiave-v1` asseriva il contrario di U6 (preferenza di sole colonne, cambia la
misura del preset, banner acceso): è riscritto come presidio di U6. I presidi nuovi: U6 sulle due famiglie; U8 come app
(data e impronta finta rifiutate); Q33 coi vincoli differiti (DELETE + INSERT identico fermo, un ordine cambiato
sposta `colonne`); Q38 («Ignora» chiude, il cambio dopo riaccende); il seed (composizione riscritta uguale dall'app: il
preset resta intatto, il caso 15, che da owner passa per costruzione e va letto come app). Guardrail dei changeSet e
del preambolo pgTAP verdi.

**La doc.** Riscritte le pagine `manual/` di `fn_preset_aggiornato`, `trgfn_preset_contenuto_aggiornato`,
`trgfn_preset_riga_tocca_preset`, `trgfn_preferenza_preset_base_snapshot`; nuova `fn_preset_impronta`; riallineate
`fn_preset_di_base`, i due resolver, i due preset, le due composizioni, le due preferenze (le righe «⚠️ Che cosa oggi non
copre» di U6, U8 e della sostituzione in blocco tolte), le pagine del seed `automazione_seed_primo_impianto` e
`trgfn_seed_primo_impianto`, la guida `configurazione-liste` §10.5. La doc auto-generata e `ui/index.md` li rigenera
Tid dopo l'apply.

**La verifica (`/verifica-db`, sessione nuova, 2026-11-20).** Nessun difetto di codice: corpi dei resolver confrontati con
quelli vivi su dbdev, catena delle `preConditions`, censimento dei lettori delle colonne (funzioni, `BEGIN ATOMIC` da
`pg_depend`, viste, fasi tardive), nessun clone dei preset, nessun caricamento di `80_data` coi trigger spenti; la
prova ripetuta su ventidue pgTAP, nessun rosso nuovo. Corretti quattro testi:

* l'avvertenza di `-06` e della pagina `trgfn_preset_riga_tocca_preset` sugli eventi trigger in sospeso: bloccano
  l'`ALTER` della composizione, che li accoda, non del preset (provato su tabelle temporanee);
* la nota di `E_UI_PRESET_CONTENUTO_DERIVATO` in `codici_errore.csv`, senza apostrofi;
* «tutte le chiavi alla data di oggi» (testata di `-04` e tabella dei pezzi qui sopra): è la data che la colonna porta,
  non `now()`;
* `fn_preset_aggiornato` `STABLE` e non `IMMUTABLE`, allineato nel piano.

Limiti dichiarati, non chiusi: il caricamento dei CSV dei preset da zero passa dal trigger (senza `DEFAULT`) e lo
prova solo la CI; per le dashboard «Ignora» e il DELETE + INSERT identico non hanno un pgTAP proprio (la funzione è
quella delle liste; lo dichiara la pagina `dashboard_preferenza_utente`).

**L'apply.** ✅ `20261120-02` … `-11` applicati su dbdev da Tid il 2026-11-20 (23:55), pgTAP verdi. Parte la richiesta
al team BE/FE: la parte 1b di BE7 e BE25 (§6).

**La verifica sul commit (`/verifica-db 986baa5d8d`, sessione DB, 2026-11-22).** Il commit è applicato e su `main`, e nessuno
dei suoi YAML è stato toccato dopo. Numeri, `id` e `logicalFilePath` sono allineati. I corpi vivi di `fn_preset_impronta`,
`fn_preset_aggiornato`, `trgfn_preset_riga_tocca_preset` e `trgfn_preferenza_preset_base_snapshot` (nessun giro li ha
riscritti) sono quelli del giro. Gli altri oggetti li hanno riscritti i giri 2, 5 e 6, e si verificano lì. L'impronta
copre tutte le colonne di contenuto delle due composizioni di oggi, e la riga 5 del registro tutte le colonne di
`lista_preset`.
**Un difetto (Q54, decisa (a) da Tid il 2026-11-22, da scrivere nel giro 7):** il software toglie una riga dalla composizione di un preset che l'installazione ha
personalizzato (una colonna ritirata). Il trigger del seed (`a00`) riporta `composizione_impronta` a OLD con un
`WARNING`, e l'impronta salvata non è più quella della composizione: provato sullo scratch come migratore, in
`ROLLBACK`. Il corpo del trigger differito dice che cosa segue: alla scrittura successiva dell'installazione, **anche
una riscrittura uguale**, la chiave `colonne` si sposta e il banner si accende in ritardo, a una scrittura che non ha
cambiato niente. È il caso che Q37 voleva chiudere. Come app non è provato, perché l'impronta resta indietro solo nella
sessione del migratore. La pagina `manual/` di `trgfn_preset_riga_tocca_preset` lo dichiarava già come limite, ma con
la conseguenza sbagliata: **corretta**. La correzione del codice vuole un changeSet nuovo e tocca il modello del seed
(§7.1, Q54).

### 3.2 Giro 2 — la forma della preferenza e i widget nuovi

**U10 (A) — Il badge dei widget nuovi conta anche quelli che l'utente non può vedere** · area D.

* **Fatto.** Il passo 3 di `fn_resolve_dashboard_config` conta i widget accesi del pool assenti dalla configurazione,
  prima del filtro per area e azione del passo 4, e non ricalcola dopo. Il gemello delle liste ricalcola dopo il filtro
  (passo 5-bis): le due copie hanno divergito. Verificato sul corpo il 2026-11-18.
* **Correzione proposta.** Il conteggio dopo il filtro, come nelle liste.
* **Presidio.** Un utente senza l'area, un widget di quell'area nel pool e un preset che non lo nomina:
  `widget_nuovi = 0`.

**U11 (B) — Una voce senza codice spegne l'aggiunta di colonne e widget nuovi** · area D.

* **Fatto.** Le colonne o i widget nuovi si cercano con `codice NOT IN (SELECT elem->>'codice' …)`. Se una voce della
  preferenza o del preset non ha codice, l'elenco contiene un NULL, il `NOT IN` non è mai vero e nessun elemento nuovo
  entra più. Vale per tutti e due i resolver.
* **Correzione proposta.** `NOT EXISTS`. La voce senza codice si chiude anche con U12.
* **Presidio.** Una preferenza con una voce senza codice e un elemento nuovo nel catalogo: il nuovo arriva.

**U12 (B) — La forma della preferenza la verifica solo il backend** · aree B, D · Q6.

* **Fatto.** Della `configurazione` il DB verifica solo la misura di pagina delle liste; della dashboard niente. Una riga
  con `ordine` o `larghezza` non interi, o con `widget` che non è un array, fa fallire il resolver con un 22P02 grezzo:
  quella lista, o la home, non si apre più per quell'utente. Una voce senza `visibile` esce con `visibile: null`, e un
  codice ripetuto esce due volte. Oggi la regola vive in `lista_preferenza_service.py:231` e in
  `dashboard_preferenza_service.py:161-253`.
* **Correzione proposta.** (a) Un guard di forma sulle due preferenze, comune (oggetto, chiavi ammesse, voci con codice
  unico e tipi giusti). (b) Un resolver tollerante, che scarta le voci malformate. **Raccomandata (a)**, più i cast
  sicuri nei resolver per le righe scritte prima del guard.
* **Decisione (Q6, Tid, 2026-11-18).** (a): un guard di forma comune alle due preferenze, più i cast sicuri nei resolver per le righe scritte prima del guard; la copia della regola nel BE si ritira.
* **Presidio.** Un `throws_ok` per ogni forma rifiutata; un resolver che non cade su una riga scritta senza il trigger.

**U13 (B) — Ordinamento e filtri passano senza filtro** · area B · Q7.

* **Fatto.** L'ordinamento e i filtri della preferenza o del preset passano così come sono. Possono nominare colonne
  spente, non `ordinabile` o non `filtrabile`, o BLOCCATO per l'utente: un ordinamento su una colonna sensibile resta
  nel JSON.
* **Correzione proposta.** Nel resolver si tolgono le voci di colonne spente, non ammesse o BLOCCATO. Prima va decisa la
  convenzione di `col`, codice o campo sorgente (Q7). Fatto datato, 2026-11-18: su dbdev, dove codice e campo sorgente
  differiscono, i 5 ordinamenti dei preset usano il campo sorgente; il FE ordina per campo sorgente (`sortField` di
  PrimeVue); un test BE (`test_lista_preferenza_service.py:63`) scrive il codice.
* **Decisione (Q7, Tid, 2026-11-18).** `col` è il **codice** della colonna: identità stabile, stessa chiave delle voci
  `colonne`. Le 5 righe del seed che usano il campo sorgente si convertono; il resolver espone in uscita anche il campo
  sorgente, che il FE usa per ordinare. All'ingresso (Q34, Tid, 2026-11-20): il guard di forma rifiuta un `col` che non
  è un codice della lista, e la traduzione dal campo sorgente la fa il BE (BE20); un guard non riscrive in silenzio ciò
  che riceve. ⚠️ Completata da Q40 (b), Tid, 2026-11-21: la traduzione non nasce, chi scrive `col` scrive il codice
  (§3.2-bis, «Verifica per Q40»); il rifiuto del guard resta.
* **Presidio.** Un ordinamento su una colonna spenta e uno su una sensibile senza grant: escono tolti.

**U14 (B) — Nessun vincolo lega fra loro preset, colonne, pool e preferenza** · aree B, D · Q8.

* **Fatto.** Quattro legami che il modello non chiede:
  * la riga di `lista_preset_colonna` può citare una colonna di un'altra lista; il resolver riabbina per codice, e con
    un codice uguale prende ordine e larghezza di un'altra colonna;
  * la riga di `dashboard_preset_widget` può proporre un widget fuori dal pool della dashboard (la vecchia pagina lo
    chiamava «vincolo di seed»), e togliere un widget dal pool non tocca i preset che lo propongono;
  * il `preset_base_id` di una preferenza può essere il preset di un'altra lista o di un'altra dashboard;
  * `lista_id`, `ambito`, il profilo e l'azienda della testata di un preset si possono cambiare: lo rifiuta solo il
    servizio.
* **Correzione proposta.** FK composite (l'id con la lista o la dashboard) dove la chiave lo consente, altrimenti un
  guard; un lucchetto di colonna sulla testata del preset; per il pool, il DELETE di un widget citato da un preset
  bloccato, oppure in cascata (Q8).
* **Decisione (Q8, Tid, 2026-11-18).** Il DELETE di un widget dal pool è **bloccato** finché un preset lo propone; il
  messaggio nomina i preset. Stessa regola delle colonne delle liste oggi (FK NO ACTION): Q18 va tenuta coerente.
* **Presidio.** Un INSERT incrociato rifiutato per ciascuno dei quattro legami; l'UPDATE di `lista_id` del preset
  rifiutato.

### 3.2-bis Il piano del giro 2 (sessione DB, 2026-11-21) — applicato, pgTAP verdi, verificato il 2026-11-22

Corpi vivi letti da dbdev il 2026-11-21 (`pg_get_functiondef`, `pg_get_triggerdef`, `pg_constraint`): i due resolver
sono quelli di `20261120-10` e `-11`, uguali alla doc auto-generata rigenerata dopo l'1b. Nessun changeSet dopo
`20261120-11` tocca oggetti di `ui`. Prima di scrivere si riverifica.

**Che cosa ha trovato la lettura, prima di scrivere.**

* **La forma di `filtri` non è scritta da nessuna parte.** Il COMMENT di `lista_preset.filtri_default` dice «formato
  JSONB condiviso con il componente Vue filtri. Definirlo prima di seedare i preset»; la guida non lo descrive; il
  COMMENT di `configurazione` lo nomina e basta. Un guard di forma (Q6) e il filtro delle voci (U13) chiedono una
  forma: senza, il DB può solo dire «un oggetto», e non sa quali chiavi siano colonne. La forma la conosce il BE, che
  la valida oggi (la copia di BE8). → R-BE2, prima di scrivere il guard.
* **Il DB non sa che cosa il BE accetta oggi, voce per voce.** Il guard di Q6 sostituisce la copia del BE
  (`lista_preferenza_service.py`, `dashboard_preferenza_service.py`): se la regola del DB è più stretta, una scrittura
  che oggi passa si rompe; se è più larga, la copia ritirata portava via una garanzia. Quali campi della voce sono
  obbligatori (`larghezza` può mancare?), quali chiavi ammesse, se il codice deve essere della lista: lo dice il BE.
  → R-BE2, insieme alla forma di `filtri`.
* **La traduzione da campo sorgente a codice (Q34) è ambigua nel modello.** Nessun vincolo impedisce a due colonne
  della stessa lista di avere lo stesso `campo_sorgente`; allora il campo che il FE manda non dice quale colonna.
  Fatto datato, 2026-11-21: su dbdev nessuna lista ne ha due, e 164 colonne hanno codice diverso dal campo. → Q40,
  decisa (b) il 2026-11-21: chi scrive `col` manda il codice, nessuno traduce, e l'ambiguità non ha più un lettore.
* **Il `col` di cinque preset del seed è un campo sorgente** (Q7). Fatto datato, 2026-11-21: i preset 1, 18, 90, 95,
  107 (`ragione_sociale_completa` → `ragione_sociale`, `comune_descrizione` → `comune`, `revisione_numero` → `rev`,
  `tipo_prestazione_descrizione` → `tipo_prestazione`). `ordinamento_default` è una colonna dell'installazione nella
  riga 5 del registro del seed: il CSV corretto raggiunge le righe intatte, non quelle personalizzate. La conversione
  delle personalizzate (e delle preferenze, dove il FE scrive oggi il campo sorgente) è un backfill di forma, come
  quello di `-04` dell'1b: nel changeSet di schema, coi trigger spenti per nome, prima del guard.
* **Un UPDATE che non cambia la `configurazione` non deve passare dal guard.** «Ignora» (Q38) e il riallineamento
  riscrivono la preferenza; se l'upsert del BE rimanda la `configurazione` com'è, una riga scritta prima del guard
  verrebbe rifiutata proprio mentre l'utente chiude il banner. Il guard giudica l'UPDATE solo se
  `NEW.configurazione IS DISTINCT FROM OLD.configurazione`.
* **I legami di U14 si chiudono con FK composite**, che valgono per costruzione da tutti e due i lati: la preferenza ha
  già `lista_id` e `dashboard_id`, e `ON DELETE SET NULL (preset_base_id)` (PostgreSQL 15+, dbdev è 18) tiene la
  regola di oggi. Le composizioni dei preset no: `lista_preset_colonna` e `dashboard_preset_widget` non portano la
  lista né la dashboard. → Q41. Fatto datato, 2026-11-21: zero righe che violano i quattro legami; il changeSet
  bonifica lo stesso (il modello le ammette), prima dei vincoli.

**I pezzi** (nella forma di Q40 (b), Q41 (a), Q42 (a), decise da Tid il 2026-11-21, con la risposta di R-BE2 e il
ritiro di Q38/Q39 §6; che cosa è cambiato dalla prima stesura lo dice «Il riallineamento del 2026-11-21», qui sotto):

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `ui.fn_intero_da_jsonb(p_valore jsonb)` | Il BB della misura (U19): un `number` intero di al più nove cifre, altrimenti NULL; mai un cast che cade. `IMMUTABLE`. Lo leggono il guard di forma, `fn_guard_misura_pagina` e i due resolver: la stringa `"25"`, che il resolver delle liste oggi accetta e il guard rifiuta, non vale più in nessuna sede | U19 |
| `ui.fn_dimensione_max_ammessa(p_valore integer)` | Il tetto 1-100 della dashboard, in una sede (Q12): lo leggono il guard di forma e il resolver delle dashboard. L'8 e il CHECK sul preset restano al giro 3 | U21 (preferenza) |
| `ui.fn_check_forma_configurazione(p_famiglia, p_contenitore_id, p_configurazione)` (nella prima stesura `fn_guard_forma_preferenza`: è una `fn_check_*`, che restituisce il motivo, e il trigger `ui.trgfn_preferenza_guard_forma` solleva) | Il guard di forma comune (Q6). La radice è un oggetto con le sole chiavi della famiglia, nessuna a `null`: `colonne` e `pagina_dimensione` per le liste (`ordinamento` e `filtri` escono, Q38/Q39 §6), `widget` e `dimensione_max` per le dashboard. `colonne`/`widget` è un array di oggetti con le sole chiavi della voce (`codice`, `ordine`, `larghezza`, `visibile`, `fissata`; per il widget `codice`, `ordine`, `visibile`): `codice` testo non vuoto, unico nell'array, del contenitore in qualsiasi stato (Q42: una colonna della lista, un widget del pool); `ordine` e `larghezza` interi positivi, letti dal BB della misura; `visibile` e `fissata` booleani. Ogni campo della voce tranne `codice` può mancare, nessuno è `null` (R-BE2). `pagina_dimensione` col guard di oggi, `dimensione_max` col BB del tetto. Codice nuovo `E_UI_CONFIGURAZIONE_FORMA` (`DATO_ERRATO`, come `E_UI_MISURA_PAGINA_NON_AMMESSA`), segnaposto la tabella, la chiave e il motivo; lo stesso codice lo usa il guard del preset | U12, U21 |
| Il trigger del guard sulle due preferenze | `BEFORE INSERT OR UPDATE OF configurazione`, l'UPDATE giudicato solo se la `configurazione` cambia. Sulle liste sostituisce `trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd` e la sua funzione, che si tolgono (la misura la giudica il guard di forma) | U12 |
| Il guard di `ordinamento_default` del preset | Un array di oggetti con le sole chiavi `col` e `dir`: `col` un codice della lista in qualsiasi stato (Q7, Q34, Q42), unico nell'array; `dir` `asc` o `desc`. `null` resta ammesso (la colonna è nullable: il preset non dice l'ordinamento). Sul trigger `a10` del preset, accanto a quello della misura, con `E_UI_CONFIGURAZIONE_FORMA`. È la prima sede della forma di un ordinamento (la preferenza non lo porta più): resta scritta sul posto. `filtri_default` non ha guard: la colonna si ritira | U13, Q34 |
| I due resolver | Il conteggio di `widget_nuovi` dopo il filtro di area e azione, come le liste al passo 5-bis (U10); `NOT EXISTS` al posto di `NOT IN` nel merge (U11); i cast di `ordine`, `larghezza`, `visibile`, `fissata` dal BB, una voce senza codice scartata, un codice ripetuto preso una volta (le righe scritte prima del guard, U12). **Liste:** `ordinamento` e `filtri` escono dall'uscita, da `origine` e dalle chiavi che il banner confronta (Q38/Q39 §6); l'ordinamento risolto lo dà solo il BB della riga dopo | U10, U11, U12 |
| `ui.fn_ordinamento_lista(p_lista_codice, p_auth_user_id, p_emittente_fiscale_id)` | La richiesta di BE25 (2): l'ordinamento di partenza di una lista per un utente, senza la risoluzione intera a ogni pagina. Il preset di base dalla sede del resolver (`ui.fn_preset_di_base`), altrimenti `[]`; via le voci di colonne spente, non `ordinabile` o BLOCCATO per l'utente (`ui.fn_lista_colonne_livello`); ogni voce esce come `{col, dir, campo_sorgente}` (Q7: il BE ordina per campo, il FE accende l'intestazione dalla risposta della lista). `STABLE`. È la sola sede dell'ordinamento risolto: il resolver non lo ricopia | U13, BE20, BE25 (2) |
| Il ritiro di filtri e ordinamento della preferenza (Q38/Q39 §6, passo 2) | Nel changeSet di schema, coi trigger spenti per nome: `configurazione - 'ordinamento' - 'filtri'` sulle preferenze di lista; le chiavi `ordinamento` e `filtri` tolte dalla data del contenuto dei preset di lista e dallo snapshot delle preferenze (il banner non ha più quelle chiavi da confrontare: una preferenza non le personalizza); poi `DROP COLUMN ui.lista_preset.filtri_default`. `trgfn_preset_contenuto_aggiornato`: la mappa delle liste diventa `colonne`, `pagina_dimensione`. La colonna esce dalla riga 5 del registro del seed (`automazione_seed_primo_impianto.csv`, colonne dell'installazione) nello stesso giro; il loader di `lista_preset.csv` non la porta già. Il COMMENT di `configurazione` dice le chiavi che restano | Q38 §6, Q39 §6 |
| I legami (Q41 (a)) | FK composite `(preset_base_id, lista_id)` → `lista_preset (id, lista_id)` e il gemello delle dashboard, `ON DELETE SET NULL (preset_base_id)`, al posto delle FK di oggi; `lista_id` su `lista_preset_colonna` e `dashboard_id` su `dashboard_preset_widget`, scritte dal DB dal preset, con le FK composite verso il preset, la colonna della lista e il pool (`dashboard_widget`, la sua PK). Gli UNIQUE `(id, lista_id)` e `(id, dashboard_id)` che le FK chiedono | U14 |
| Il pool (Q8) | `BEFORE DELETE` su `dashboard_widget`: rifiutato finché un preset propone il widget, il messaggio nomina i preset (codice nuovo); la FK composita resta la rete | U14, Q8 |
| La testata del preset | Un lucchetto: `lista_id`/`dashboard_id`, `ambito`, profilo e azienda non cambiano dopo l'INSERT (codice nuovo). Il CSV li riscrive uguali, e passa | U14 |
| Seed e backfill | `lista_preset.csv`: i cinque `col` col codice (Q7). Nel changeSet di schema, coi trigger spenti per nome: il `col` dei preset personalizzati tradotto dove il campo dice una colonna sola, la voce tolta dove non la dice (le preferenze non portano più `ordinamento`: le pulisce il ritiro); le voci di U14 incrociate tolte e le basi altrui a NULL; `lista_id`/`dashboard_id` delle composizioni valorizzate dal preset prima del `NOT NULL` e delle FK. La riga 6 del registro del seed (la composizione figlia) resta: `lista_id` è derivata, non dell'installazione | Q7, U14 |
| COMMENT e doc | `configurazione` delle due preferenze e `ordinamento_default` (la forma scritta, non più «da definire»); le pagine `manual/` delle funzioni e delle tabelle toccate, e quella di `lista_preset` senza `filtri_default`; la guida `configurazione-liste` dove descrive preferenza, ordinamento e filtri (i filtri di partenza sono dello store, l'ordinamento di partenza è del preset); la pagina nuova di ogni BB e di `ui.fn_ordinamento_lista` | M |
| pgTAP | Il guard: un `throws_ok` per ogni forma rifiutata, sulle due famiglie (compresa una preferenza di lista con `ordinamento` o `filtri`, e una voce con un campo a `null`), e un UPDATE di sola base su una riga malformata che passa; il guard del preset (`col` non codice, `dir` fuori dominio, `col` ripetuto). I resolver: U10 (utente senza l'area, widget di quell'area nel pool: `widget_nuovi = 0`), U11 (voce senza codice scritta senza il trigger, colonna nuova in catalogo: arriva), U12 (riga malformata scritta senza il trigger: il resolver non cade), l'uscita delle liste senza `ordinamento` né `filtri`. `ui.fn_ordinamento_lista`: voci su colonna spenta, non ordinabile e sensibile senza grant tolte; `campo_sorgente` in uscita; nessun preset: `[]`. Il ritiro: la mappa del contenuto di un preset di lista ha le sole chiavi `colonne`, `pagina_dimensione`. U14: un INSERT incrociato rifiutato per legame, l'UPDATE della testata rifiutato, il DELETE dal pool rifiutato col nome del preset. Da adeguare quelli che scrivono preferenze o leggono le chiavi ritirate (`ui/test-fn-resolve-*`, `test-fn-preset-di-base-v1`, `test-misure-pagina-v1`, `test-ui-nell-ambito-v1`, `test-liste-preset-default-v1`, `vendite/test-righe-gemelle-secondo-giro-v1`, da rileggere: nomina `ordinamento`) e quelli che scrivono composizioni | |

**Garanzie ritirate.**

| Oggetto | La proprietà che i lettori davano per scontata | Lettori lato DB, con l'esito |
| --- | --- | --- |
| ~~`ordinamento` e `filtri` dei due resolver~~ ⚠️ Superata dalle righe sotto (2026-11-21): con Q38/Q39 §6 le due chiavi escono dal resolver | ~~Escono come la preferenza o il preset li ha salvati~~ | — |
| `ui.lista_preset.filtri_default` (la colonna) | Esiste, e il resolver la dà come `filtri` | DB: `fn_resolve_lista_config`, `trgfn_preset_contenuto_aggiornato` (la mappa per chiave), la riga 5 del registro del seed: adeguati in questo giro. Nessuna vista la legge (`pg_views`, 2026-11-21). BE: `ui_admin_repository.py:82` la legge (R-BE3) |
| Le chiavi `ordinamento` e `filtri` della preferenza di lista | Una preferenza le può portare, e il resolver le usa prima del preset | DB: solo il resolver, adeguato; il guard nuovo le rifiuta. BE: la whitelist di `lista_preferenza_service.py:41` e `:192-200` (R-BE3) |
| `ordinamento`, `filtri`, `origine.ordinamento`, `origine.filtri` in uscita dal resolver delle liste | Ci sono sempre | Nessun lettore DB. BE/FE: BE9 dice che nessun service li legge; il censimento intero è R-BE3 |
| Le chiavi `ordinamento` e `filtri` della data del contenuto dei preset di lista e dello snapshot | Ci sono per ogni preset di lista e ogni snapshot | DB: `fn_preset_aggiornato` riceve le chiavi dal resolver (adeguato); `trgfn_preferenza_preset_base_snapshot` copia la mappa intera e non dipende dalle chiavi. BE/FE: `preset_base.contenuto_aggiornato_il` e `preset_aggiornato_chiavi` in uscita (R-BE3) |
| `ordinamento_default` del preset, in lettura | Il resolver lo dà com'è salvato | Nessun lettore DB; la sede nuova (`ui.fn_ordinamento_lista`) ne toglie le voci non ammesse. BE25 (2) nasce su quella |
| `pagina_dimensione` della preferenza | Il resolver delle liste accetta anche la stringa `"25"` | Solo il resolver. Il guard la rifiutava già: vale per le righe scritte prima del guard |
| `widget_nuovi` | Conta anche i widget che l'utente non vede | Solo il resolver |

Lato BE/FE la richiesta è **«censisci i lettori di `ordinamento`, `filtri` e `widget_nuovi` del resolver che contano su
ciò che è stato salvato, o su un conteggio prima del filtro»**, accanto a BE8, BE9, BE11, BE20. ⚠️ Allargata dal
riallineamento del 2026-11-21: è R-BE3, qui sotto.

**Chi cambia per primo.** Il DB, salvo R-BE2, che viene prima di scrivere. Dopo l'apply un salvataggio
dell'ordinamento col campo sorgente è rifiutato finché il BE non traduce (BE20): rottura accettata in sviluppo, come
all'1a; la richiesta parte con l'apply. ⚠️ Superato da Q40 (b), 2026-11-21: il BE non traduce, e nessuna scrittura
del FE porta `col` (§3.2-bis, «Verifica per Q40»); il rifiuto tocca solo una chiamata diretta all'API admin dei preset
col campo al posto del codice.

**Prima di scrivere: R-BE2 al team BE (con la verifica di BE9, Q35).** Che forma ha oggi, voce per voce, ciò che il BE
accetta nella `configurazione` delle due preferenze e in `ordinamento_default`/`filtri_default` dei preset: le chiavi
ammesse, i campi obbligatori di ogni voce e i loro tipi, se il codice deve essere della lista o del pool, e la forma di
`filtri` che il FE manda. Senza, il guard o rompe una scrittura che oggi passa o ritira una garanzia senza saperlo.

**Risposta di R-BE2 (team BE, 2026-11-21).** Che cosa il BE accetta oggi, letto dal codice (`_validate_payload` dei due service delle preferenze, `_build_create_data`/`_build_update_data` di `lista_preset_admin_service.py`) e da ciò che il FE manda (`useListaConfig`, `useDashboardConfig`, `ListaColonneModal`):

| Dove | Che cosa passa oggi | Che cosa il BE NON guarda |
| --- | --- | --- |
| Preferenza di lista, radice | Un oggetto. Chiavi ammesse `colonne`, `ordinamento`, `filtri`, `pagina_dimensione` (altre: 400). Almeno una chiave valorizzata (vuota: 400, si usa la DELETE). Una chiave a `null` non si salva | — |
| `colonne` | Una lista; ogni voce un oggetto con le sole chiavi `codice`, `ordine`, `larghezza`, `visibile`, `fissata`. `codice` stringa non vuota (salvata senza spazi in testa e in coda). `ordine`, `larghezza`: interi positivi fino al tetto di `bigint`; una stringa di sole cifre si accetta e **si salva come intero**. `visibile`, `fissata`: booleani JSON. Tutto facoltativo tranne `codice`; un campo a `null` **esce dalla voce** (il FE manda `larghezza: null` quando l'operatore la svuota, e la riga salvata non ha la chiave): a DB `larghezza` può mancare, non è mai `null` | Che il codice sia della lista (passa qualsiasi stringa); i codici ripetuti; la lunghezza dell'elenco |
| `ordinamento` | Una lista, contenuto non guardato | Tutto: `col`, `dir`, la forma delle voci. Dal 2026-11-20 (Q38/Q39, passo 1) il FE non lo manda più; un PUT diretto passa fino al passo (3) |
| `filtri` | Un oggetto, contenuto non guardato | Tutto. **Il FE non lo manda** (dal 2026-11-20, e prima mandava ciò che la risoluzione gli aveva dato): una forma di `filtri` scritta dal FE non esiste. I filtri di partenza sono degli store (`filterDefaults`) |
| `pagina_dimensione` | Un intero positivo (la forma); quale misura, lo dice il guard DB (`E_UI_MISURA_PAGINA_NON_AMMESSA`) | — |
| Preferenza di dashboard | Chiavi `widget`, `dimensione_max` (altre: 400), almeno una. `widget`: lista di al più 100 voci, ogni voce `{codice, ordine, visibile}` (altre chiavi: 400), `codice` stringa non vuota, `ordine` intero positivo, `visibile` booleano, codici ripetuti rifiutati. `dimensione_max`: intero positivo ≤ 100 (BE11 lo porta al DB) | Che il codice sia del pool |
| Preset di lista (CRUD admin) | `ordinamento_default`: una lista o `null`, contenuto non guardato. `pagina_dimensione`: intero positivo o `null` (= il default). `filtri_default`: non più scrivibile dal 2026-11-20 (400) | Il contenuto di `ordinamento_default`. ⚠️ Il drawer admin del FE non lo scrive: oggi lo scrivono solo il seed e una chiamata API diretta |
| Preset di dashboard | Nessun CRUD nel BE: li scrive solo il seed | — |

Che cosa ne segue per il guard (fatti, non decisioni): una regola più stretta del BE sul codice (della lista o del pool, Q42) e sui codici ripetuti delle colonne **non rompe nessuna scrittura del FE di oggi**, che manda le colonne della risoluzione, una voce per codice; può rompere solo una chiamata diretta. `larghezza` (e `ordine`, `visibile`, `fissata`) può mancare dalla voce, e non arriva mai `null` dal BE: il guard può ammettere l'assenza e rifiutare il `null` senza che nessun salvataggio cambi. `ordinamento` e `filtri` della preferenza non li scrive più nessuno dal FE, e con Q38/Q39 escono dalla preferenza: il guard non ha da dare una forma a `filtri`. Per `ordinamento_default` del preset la forma `{col, dir}` è quella del seed; il BE non la verifica, quindi il guard non ritira nessuna garanzia del BE. La copia di queste regole nel BE si ritira con BE8, BE11 e il passo (3) di Q38, dopo l'apply.

**Verifica per Q40 (team BE, 2026-11-21).** Q40 raccomanda (b) «se l'ordinamento passa dal FE al BE per codice senza costi». Letto dal codice: **nessun componente FE scrive `col`**. La preferenza non porta più `ordinamento` (Q39, passo 1: `_PAYLOAD_ROOT_KEYS` di `useListaConfig.js` ha solo `colonne` e `pagina_dimensione`); il drawer dei preset (`ListaPresetDrawer.vue`) non ha il campo `ordinamento_default`, che si scrive solo dal seed o da una chiamata diretta all'API admin dei preset (`lista_preset_admin_service.py`, che oggi lo accetta come lista senza guardarne le voci). L'ordinamento che il FE mostra arriverà dalla risposta (BE25), con il `campo_sorgente` in uscita dal resolver (U13): il FE non deve mai tradurre un campo in codice. Ne segue che (b) non costa niente lato FE e che la traduzione del BE prevista da BE20 (salvataggio di preferenza e preset) non ha un chiamante: con (b) si ritira prima di nascere, e una chiamata diretta con un campo al posto del codice la rifiuta il guard (Q34). Resta di BE20 la sola lettura del `campo_sorgente` dalla risposta.

**Le decisioni di questo piano** (§7.1): Q40, Q41, Q42; dal riallineamento, Q43.

**Il riallineamento del 2026-11-21 (sessione DB).** La prima stesura dei pezzi (2026-11-21, mattina) è venuta prima
della risposta di R-BE2 e non portava le decisioni di §6 del 2026-11-20 (Q38 §6, Q39 §6) né la richiesta di BE25 (2).
Corpi e struttura riletti da dbdev lo stesso giorno: nessun changeSet dopo `20261120-11` tocca oggetti di `ui`; le
chiavi `filtri`/`ordinamento` e le colonne `filtri_default`/`ordinamento_default` le leggono solo
`fn_resolve_lista_config` e `trgfn_preset_contenuto_aggiornato` (`pg_proc`), nessuna vista (`pg_views`); la riga 5 del
registro del seed elenca `filtri_default` fra le colonne dell'installazione. Che cosa è cambiato nei pezzi:

* **Il ritiro di Q38/Q39 §6 entra nel giro** (il passo (2) che quelle decisioni affidavano al giro 2): chiavi della
  preferenza, uscita del resolver, data del contenuto e snapshot, `DROP COLUMN filtri_default`, registro del seed. La
  prima stesura validava ancora `ordinamento` e `filtri` nella preferenza e `filtri_default` nel preset.
* **Le regole della voce vengono da R-BE2**: un campo può mancare, mai `null`; chiavi della voce chiuse; il codice
  unico e del contenitore (più stretto del BE, che non lo guardava: non rompe nessuna scrittura del FE di oggi, che
  manda le colonne della risoluzione). La regola dell'API «almeno una chiave, il vuoto è una DELETE» resta del BE: è
  il contratto dell'endpoint, non una forma del dato, e il DB non la porta (una `configurazione` `{}` segue il preset
  in tutto). Il tetto di 100 voci del widget non si porta: codice unico e del pool lo limitano già.
* **L'ordinamento risolto ha una sede sua**, `ui.fn_ordinamento_lista`, chiesta da BE25 (2): U13 (le voci non
  ammesse tolte, `campo_sorgente` in uscita) vive lì, non nel resolver, che la chiave non l'ha più.
* **Un codice d'errore per le due forme**, `E_UI_CONFIGURAZIONE_FORMA`, al posto di `E_UI_PREFERENZA_FORMA` della
  prima stesura: lo producono il guard della preferenza e quello del preset, e il preset non è una preferenza. Restano
  da nominare, alla scrittura, il codice del DELETE dal pool (`CONFLITTO_STATO`, come `E_UI_COLONNA_IN_USO`) e quello
  del lucchetto della testata.

**Lo stato della scrittura (sessione DB, 2026-11-21).** Il giro si scrive in due parti, con un apply solo o due a
scelta di Tid: **2a** (forma, ritiro di filtri e ordinamento, resolver, ordinamento risolto) e **2b** (i legami di U14:
FK composite, `lista_id`/`dashboard_id` sulle composizioni, il pool, il lucchetto della testata). ✅ 2a scritto:
`20261120-21` `ui.fn_intero_da_jsonb`; `-22` `ui.fn_dimensione_max_ammessa`; `-23` `fn_guard_misura_pagina` dal BB;
`-24` `ui.fn_check_forma_configurazione`; `-25` (00_schema) il ritiro e il backfill di forma; `-26`
`ui.trgfn_preferenza_guard_forma` e i due montaggi, via il guard della sola misura; `-27` il guard di
`ordinamento_default`; `-28` la mappa del contenuto; `-29`, `-30` i due resolver; `-31` `ui.fn_ordinamento_lista`. CSV:
`E_UI_CONFIGURAZIONE_FORMA` (codici e messaggi, id 1519), i cinque `col` di `lista_preset.csv`, la riga 5 del
registro del seed senza `filtri_default`. Provati insieme sullo scratch (`prova_changeset.py`, ROLLBACK). Il nome del
codice d'errore è uno per le due forme; quello di 2b si sceglie scrivendo 2b. ✅ pgTAP adeguati al contratto
nuovo, ciascuno con la ragione in testata: `test-fn-preset-di-base-v1` e
`test-fn-resolve-lista-config-preset-aggiornato-v1` (il banner sulla misura, non più sull'ordinamento),
`test-fn-resolve-lista-config-cascata-per-chiave-v1` (le due chiavi; la chiave null la rifiuta il guard; cambiare
`ordinamento_default` non sposta chiavi), `test-fn-resolve-lista-config` (fixture senza le due chiavi),
`test-misure-pagina-v1` (i trigger della misura cercati per funzione), `test-ui-nell-ambito-v1` (la chiave che si
sposta è la misura). ✅ pgTAP nuovo `ui/test-ui-forma-configurazione-v1` (31: il guard sulle due famiglie, le righe
scritte prima del guard, U10-U13, il guard del preset, `ui.fn_ordinamento_lista`, la struttura). Provati con
l'estratto sullo scratch: verdi tutti i pgTAP di `ui` e `vendite/test-righe-gemelle-secondo-giro-v1`, salvo il
presidio delle divergenze del seed (sotto) e i rossi che c'erano già senza l'estratto. ⏳ le pagine `manual/` e la
guida `configurazione-liste`; poi 2b. ✅ Pagine `manual/` e guida di 2a riallineate (2026-11-21; la pagina del guard
ritirato si cancella, standard-guide).
✅ **2b scritto** (2026-11-21): `20261120-32` (00_schema) `lista_id` e `dashboard_id` sulle composizioni, la bonifica
delle righe incrociate, gli UNIQUE `(id, lista_id)` / `(id, dashboard_id)` e sei FK composite **accanto** a quelle di
oggi (che restano coi loro nomi: il BE ne mappa una, le eccezioni ATTIVO e la policy degli indici FK sono scritte su di
loro, e il framework ATTIVO legge solo le FK a una colonna); `-33` `ui.trgfn_preset_riga_contenitore` (a20, la colonna
derivata dal preset); `-34` il guard del pool (`E_UI_WIDGET_IN_USO`, Q8); `-35` (90_end) il runner dei lucchetti su
`ui`. CSV: otto lucchetti del posto del preset (`E_UI_PRESET_POSTO_IMMUTABILE`) in `automation_lock_columns.csv`, sei
righe `SENZA_INDICE` in `fk_index_policy.csv` (le colonne di ricerca sono già coperte), i due codici (messaggi 1520,
1521). pgTAP nuovo `ui/test-ui-legami-preset-v1` (14); adeguato `test-fn-preset-di-base-v1`, il cui caso 11 costruiva
un preset con un widget fuori dal pool, cioè la riga che il modello ora rifiuta: ora lo costruisce con l'unico widget
del pool spento. Provati sullo scratch: i casi 1-10 verdi; il 7 diventa verde col CSV dei messaggi caricato; 11-14
nella prova non girano (da owner il preset nasce «del software» e il seed non lo lascia cancellare; il lucchetto lo
monta il runner dal registro) e li prova la corsa dopo l'apply. Regressione sugli altri pgTAP di `ui`: verdi.
✅ **2b applicato su dbdev, pgTAP verdi** (Tid, 2026-11-21), compresi i casi 11-14 di `test-ui-legami-preset-v1`.
⏳ La doc auto-generata di `ui` da rigenerare dopo 2b: le schede di `ui.trgfn_preset_riga_contenitore` e
`ui.trgfn_ui_dashboard_widget_guard_in_uso`, a cui le pagine `manual/` già rimandano, nascono lì.
⚠️ **Trovato scrivendo, per il giro 3** (le misure; ✅ chiuso da U16 e U17, §3.3-bis): il guard di forma giudica la misura a ogni cambio della
configurazione, quindi una preferenza con una misura uscita dopo dal catalogo non salva più le colonne finché l'utente
non cambia la misura. Il modello lo ammette (U16/U17 fanno uscire una misura). La correzione sta col giro 3. Nella prova il presidio delle divergenze del seed è rosso
finché il mirror del registro e il giro delle automazioni non rimontano il trigger senza `filtri_default`: al migrate si
riallinea.

**Le ricadute BE/FE del giro 2** (tutte insieme dopo l'apply di 2b, decisione di Tid del 2026-11-21). Il percorso
intero, elenco chiuso dei punti noti; per ogni garanzia ritirata il censimento dei lettori resta da fare (R-BE3, punto 2):

1. **R-BE3** (qui sotto): via `filtri`/`ordinamento` dalla whitelist della preferenza e `filtri_default` dalla lettura
   admin dei preset (oggi rotta su dbdev); il censimento dei lettori dell'uscita dei resolver.
2. **BE8**: la copia della forma della preferenza (`lista_preferenza_service.py:188-231`,
   `dashboard_preferenza_service.py:161-253`) si ritira; il DB risponde `E_UI_CONFIGURAZIONE_FORMA` (`DATO_ERRATO`, un
   400) con la chiave e il motivo. Resta del BE la regola dell'API «almeno una chiave, il vuoto è una DELETE».
3. **BE11**: il tetto 100 di `dimensione_max` (`_MAX_WIDGET_PAYLOAD`) si ritira: lo giudica il DB.
4. **BE20**: la lettura di `campo_sorgente` dalla risposta di `ui.fn_ordinamento_lista`; un 400 leggibile per
   `E_UI_CONFIGURAZIONE_FORMA` su `ordinamento_default` del CRUD admin dei preset (il campo sorgente al posto del
   codice è rifiutato).
5. **BE25 (2)**: senza `order_by`, la lista configurabile ordina con `ui.fn_ordinamento_lista(lista_codice,
   auth_user_id, emittente_fiscale_id)` (`[{col, dir, campo_sorgente}]`, già senza le colonne non ammesse); l'export
   lo stesso; la risposta dice l'ordinamento applicato e il FE accende l'intestazione da lì. Si ritirano gli `orderBy`
   degli store e i `default_order` che ricopiano il preset (l'elenco è in BE9, §6).
6. **BE26** (2b): i codici e i vincoli nuovi in policy e ripiego: `E_UI_CONFIGURAZIONE_FORMA`, `E_UI_WIDGET_IN_USO`
   (`CONFLITTO_STATO`), `E_UI_PRESET_POSTO_IMMUTABILE` (`CONFLITTO_STATO`); i nomi delle FK composite che un salvataggio
   del BE può incontrare (`fk_ui_lista_preset_colonna_colonna_della_lista` quando la composizione nomina una colonna di
   un'altra lista, `fk_ui_lista_preferenza_utente_preset_della_lista` e il gemello delle dashboard quando la base è di
   un altro contenitore), dove il servizio li mappa per nome. La colonna `lista_id` di `ui.lista_preset_colonna` la
   scrive il DB: il BE non la passa. La whitelist dell'UPDATE del preset non porta già il posto: il lucchetto non
   rompe niente di oggi.
7. La doc del BE: `docs/it/backend/ui/manual/api_ui_admin_personalizzazioni.md` (`filtri_default`,
   `ordinamento_default`), `api_ui_liste.md` (la cascata a due chiavi, niente `ordinamento`/`filtri` in uscita), il
   catalogo BB backend alla voce `UiRepository.resolve_lista_config` (riga 1403 al 2026-11-21).

**Chi cambia per primo, riallineato.** Il `DROP COLUMN filtri_default` rompe la lettura admin dei preset
(`ui_admin_repository.py:82`) finché il BE non la toglie, e il guard rifiuta un PUT diretto che porta `ordinamento` o
`filtri`, che la whitelist del BE lascia ancora passare. → Q43.

**R-BE3 al team BE** (Q43 (a), decisa il 2026-11-21: prima dell'apply del giro 2):

1. la parte del passo (3) di Q38 §6 che non aspetta il DB: via `filtri` e `ordinamento` dalla whitelist di
   `lista_preferenza_service.py:41` e `:192-200`; via `filtri_default` dalla lettura admin (`ui_admin_repository.py:82`,
   i commenti di `:662`, `:720` e di `lista_preset_admin_service.py:77`) e dallo schema OpenAPI, se la lettura lo espone;
2. **censisci i lettori**, in `backend/` e `frontend/`, di `ordinamento`, `filtri`, `origine.ordinamento`,
   `origine.filtri`, delle chiavi `ordinamento`/`filtri` di `preset_base.contenuto_aggiornato_il` e di
   `preset_aggiornato_chiavi` in uscita da `ui.fn_resolve_lista_config` **che contano sul fatto che ci siano**, e di
   `widget_nuovi` di `ui.fn_resolve_dashboard_config` che contano su un conteggio prima del filtro d'area. Un lettore
   che chiede qualcosa al DB torna qui, prima della scrittura.

Dopo l'apply, non prima: BE8 (la copia della forma si ritira, resta la regola dell'API), BE11, BE20 (la lettura di
`campo_sorgente` e il 400 di `E_UI_CONFIGURAZIONE_FORMA`), BE25 (2) su `ui.fn_ordinamento_lista`; i codici nuovi in
policy e ripiego.

**Esito di R-BE3 e BE26 (team BE, 2026-11-21).** Prima del giro, sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`), 8 test di
`apps.ui.tests.db` erano rossi, e la suite unitaria mockata verde: la lettura admin dei preset cadeva su
`p.filtri_default` (`UndefinedColumn`, anche dentro l'UPDATE, che rilegge il preset: per questo una misura fuori
catalogo usciva `E_DATABASE`), il DELETE di una colonna in un preset incontrava la FK composita nuova al posto di
quella mappata, e tre test di audit muovevano la chiave `ordinamento`. Dopo: 26 su 26 verdi.

* **R-BE3, punto 1.** Via `filtri_default` dalla SELECT e dai commenti (`ui_admin_repository.py`,
  `lista_preset_admin_service.py`): lo schema OpenAPI non lo esponeva. Via `ordinamento` e `filtri` dalla whitelist
  della preferenza (`lista_preferenza_service.py`) e dal serializer di `ApiListaPreferenzaView`: nel corpo sono un 400
  `E_UI_PREFERENZA_VALIDAZIONE`; test unitario nuovo.
* **R-BE3, punto 2, il censimento.** Letti `backend/` e `frontend/`: **nessun lettore** di `ordinamento`, `filtri`,
  `origine.ordinamento`, `origine.filtri` in uscita da `ui.fn_resolve_lista_config`. `preferenzaPerChiave.js` scorre
  le chiavi che il chiamante gli passa (`colonne`, `pagina_dimensione`), `ListaColonneModal` legge solo
  `origine.pagina_dimensione`, `BannerPreset` mostra le chiavi che il DB manda in `preset_aggiornato_chiavi` senza un
  elenco suo. Restavano solo commenti stantii in `useListaConfig.js`, riallineati. `widget_nuovi`: lo leggono
  `useDashboardConfig` (badge in `HomeView`, conteggio in `DashboardWidgetModal`) come numero da mostrare; nessuno ci
  conta su un conteggio prima del filtro d'area (il conteggio dopo il filtro è quello giusto per il badge). Nessuna
  richiesta torna al DB.
* **BE26.** `genera_error_policies` rigenerato col catalogo in git (`--check` allineato): le sole tre voci nuove,
  `E_UI_CONFIGURAZIONE_FORMA` (`DATO_ERRATO`), `E_UI_PRESET_POSTO_IMMUTABILE` e `E_UI_WIDGET_IN_USO`
  (`CONFLITTO_STATO`); i tre ripieghi senza segnaposto in `error_messages_fallback.py`; nessun override di
  `ui_action` (`E_UI_COLONNA_IN_USO`, il gemello, usa il default della classe). FK composite: il DELETE di una colonna
  (`lista_colonna_admin_service.py`) mappa anche `fk_ui_lista_preset_colonna_colonna_della_lista` sullo stesso rifiuto
  della FK sulla sola colonna; il replace della composizione (`lista_preset_admin_service.py`, mappa nuova
  `_FK_COMPOSIZIONE`) dà `400 E_UI_PRESET_VALIDAZIONE` sul campo `colonne` per una colonna inesistente o di un'altra
  lista (test sul DB nuovo, `test_cancellazione_colonna_db` 4). Le FK composite delle preferenze non hanno un punto da
  mappare: il BE scrive `preset_base_id` dalla risoluzione della stessa lista, e non mappa per nome l'upsert. Il pool
  dei widget e i preset di dashboard il BE non li scrive: per `E_UI_WIDGET_IN_USO` bastano policy e ripiego.
* **Il presidio del seed sull'ordinamento** (`apps/core/tests/test_liste_configurabili_seed.py`, 5-bis e 5-ter) era
  rosso: chiedeva che `col` fosse un `campo_sorgente` (K-4 di brief-db-lista-colonna-campo-sorgente-null). Q40 (b) e
  Q42 lo revocano: ora chiede il **codice** di una colonna della lista in qualsiasi stato, e il rosso costruito usa il
  campo sorgente di una colonna divergente.
* **Doc.** `api_ui_admin_personalizzazioni.md` (via `filtri_default`, la forma di `ordinamento_default`, il lucchetto
  del posto, la FK della composizione) e `api_ui_liste.md` (cascata a due chiavi, preferenza senza `ordinamento` e
  `filtri`); il catalogo BB alle voci `UiRepository.resolve_lista_config` e `ListaPreferenzaService.upsert`, con
  l'indice rigenerato.
* ⚠️ **Per BE8, trovato leggendo.** Oggi il BE toglie dalla voce un campo a `null` (il FE manda `larghezza: null`
  quando l'operatore la svuota) e salva come intero una stringa di sole cifre; il guard del DB rifiuta l'uno e l'altra.
  Ritirare la copia per intero farebbe di «svuota la larghezza» un 400: quella conversione è trasporto, non forma, e
  va decisa con BE8 (resta nel BE, o il FE smette di mandare il `null`). ✅ **Deciso da Tid il 2026-11-22: il FE smette di mandare il
  `null`** (raccomandata): il contratto dell'API resta quello del DB, uno solo. La stringa di cifre non la converte
  più nessuno: è un rifiuto di forma.

**La verifica sul commit (`/verifica-db eaed059e6e`, sessione DB, 2026-11-22).** Il giro 2 sta tutto in `eaed059e6e`
(`20261120-21` … `-35`, CSV, pgTAP, doc): `2e867df589`, che la testata nominava, è del cantiere della provenienza del
prezzo e non tocca `ui`. Il commit è applicato e su `main`, e nessuno dei suoi YAML è stato toccato dopo; numeri, `id` e
`logicalFilePath` sono allineati. Sono ancora vivi i corpi di `fn_intero_da_jsonb`, `fn_dimensione_max_ammessa`,
`fn_guard_misura_pagina`, `fn_check_forma_configurazione`, `fn_ordinamento_lista`, `trgfn_preset_riga_contenitore`
e gli schemi di `-25` e `-32`. Gli altri oggetti li hanno riscritti i giri 3, 5 e 6, e si verificano lì; il montaggio
del guard di forma copre già il contenitore (`UPDATE OF configurazione, lista_id`). Su un database da zero la catena
regge: l'autogen segue l'ordine temporale, quindi le precondizioni di `-25` trovano i BB di `-21` e `-24`, e nei seed
il pool viene prima dei preset di dashboard. Il lucchetto del posto non si scontra con le FK di profilo e azienda (NO
ACTION) e passa la colonna al messaggio. Le FK verso pool e colonne sono NO ACTION, quindi nessuna cascata incontra il
guard del pool. `ui/test-ui-forma-configurazione-v1` e `ui/test-ui-legami-preset-v1` costruiscono i loro casi.
**Corretto:** la pagina `manual/` di `ui.fn_intero_da_jsonb`. Diceva, come il COMMENT, che un numero in notazione
esponenziale non vale. Provato sullo scratch: jsonb normalizza il numero quando lo legge, quindi `1e2` e `1.0e2` danno
100, mentre `100.0` e `2.50e1` (conservati come `100.0` e `25.0`) danno NULL. Conta la forma conservata, non la
grafia. Il comportamento va bene (`1e2` è l'intero 100); il **COMMENT** dice il falso e vuole un changeSet nuovo
(da fare col prossimo giro che apre `ui`, o da solo: Tid).
**Un difetto di modello (Q55, a Tid):** si cancella una `ui.lista_colonna` che nessun preset nomina, e il DELETE passa.
Le preferenze tengono la voce col codice ritirato (il resolver la salta), e da lì il guard di forma rifiuta ogni
scrittura che conserva la chiave `colonne` con `E_UI_CONFIGURAZIONE_FORMA` («… non è una colonna della lista»), anche
un cambio della sola misura. Provato sullo scratch come migratore, con la porta del seed aperta, in `ROLLBACK`. Lo
stesso vale per una card tolta dal pool (`ui.dashboard_widget`) che una preferenza nomina. È il caso che questo piano
voleva evitare («una riga che il guard rifiuterebbe bloccherebbe il prossimo salvataggio»): il backfill di `-25` ha
messo in forma le righe di allora, ma il ritiro di una colonna o di una card ne produce di nuove. Per la misura
l'hanno chiuso U16 e U17 al giro 3; per colonne e card no. Il changeSet
`80_data/changelog/20261121-01` (brief-db-fornitore-doppioni-del-soggetto) ha ritirato tre colonne dei fornitori
contando su «il guard di forma non confronta i codici col catalogo», che è falso. Se il FE rimanda le colonne della
risoluzione (già senza la voce) il rifiuto non si vede; se una scrittura conserva le colonne salvate, sì.

**Q55, il giro (sessione DB, 2026-11-22).** Decisa (a) da Tid; per gli UPDATE la forma «solo lucchetti», decisa
lo stesso giorno: le strade che con un UPDATE fanno uscire un codice dal suo contenitore sono identità
(linee-guida-trigger, «Una FK di appartenenza non si presidia con un ramo `UPDATE OF`»), e il ritiro passa solo dal
DELETE. Numeri `20261122-26` … `-28`, dati da Tid (l'altra sessione DB ha preso `-29` e seguenti).

| Pezzo | Che cosa |
| --- | --- |
| `20261122-26` (20_code) | `ui.fn_configurazione_senza_codici(configurazione, elenco, codici)`, il BB (IMMUTABLE): toglie da `colonne` o `widget` le voci di quei codici; l'elenco che resta vuoto esce e segue il preset; senza voci da togliere la configurazione torna com'è. `ui.trgfn_voce_ritira_dalle_preferenze`, montata `AFTER DELETE` per riga, fase z10, su `ui.lista_colonna` e su `ui.dashboard_widget`: la voce esce dalle preferenze di quel contenitore, passando dai loro trigger. La bonifica delle voci già orfane (le tre colonne dei fornitori di `20261121-01`), con lo stesso BB e dai trigger |
| `20261122-27` (20_code) | Il COMMENT di `ui.fn_intero_da_jsonb`: conta la forma conservata del numero, non la grafia |
| `20261122-28` (90_end) | Il runner dei lucchetti su `ui`: `lista_colonna.lista_id` (col codice `E_UI_COLONNA_CODICE_IMMUTABILE` del codice, nota e soluzione allargate), `dashboard_widget.dashboard_id` e `widget_id`, `widget.codice` (codice nuovo `E_UI_WIDGET_IMMUTABILE`, `CONFLITTO_STATO`, messaggio 1531) |
| pgTAP | `ui/test-ui-ritiro-voce-preferenze-v1` nuovo (14): il BB, il ritiro della colonna (la voce esce, l'altra lista no, **il controesempio**: dopo il ritiro si cambia la sola misura e si salva, l'elenco vuoto segue il preset), il ritiro della card, i quattro lucchetti, il montaggio per funzione. `ui/test-ui-legami-preset-v1`, caso 4: il cambio di lista della colonna lo rifiuta ora il lucchetto, prima della FK (la FK resta la rete, e la prova il caso 3) |
| Doc | Pagine `manual/` nuove di `fn_configurazione_senza_codici` e `trgfn_voce_ritira_dalle_preferenze`; riallineate `lista_colonna`, `dashboard_widget`, `widget`, `lista_preferenza_utente`, `dashboard_preferenza_utente`, `trgfn_preferenza_guard_forma` (via i due «Che cosa oggi non copre» superati: la misura l'aveva già chiusa U16 al giro 3), `fn_intero_da_jsonb` |

**La prova** (`prova_changeset.py`, sullo scratch, da owner, `ROLLBACK`): l'estratto gira per intero. Il pgTAP nuovo
14/14 e `test-ui-legami-preset-v1` 14/14 con le righe dei tre CSV **simulate** in uno YAML di appoggio (la prova non
carica i CSV, e senza le righe del registro il runner non monta i lucchetti: 10-13 rossi). Regressione sui 34 pgTAP di
`ui`: nessun rosso nuovo; i rossi già presenti senza l'estratto sono gli stessi con l'estratto. Le precondizioni di
`-28` (le quattro righe del registro, i due codici) la prova le legge prima della simulazione, e sullo scratch
mancano: al migrate le scrive `80_data`, che gira prima di `90_end`. Non provato: il ruolo dell'app (il trigger è
INVOKER, l'app ha `UPDATE` sulle preferenze e `DELETE` sulle colonne, e le preferenze non hanno row level security);
la bonifica su righe vere (sullo scratch non ci sono preferenze orfane).

**L'apply.** ✅ `20261122-26` … `-28` migrati su dbdev da Tid il 2026-11-22, pgTAP verdi. Il primo migrate era
caduto sul loader di `messaggi_errore.csv`: la soluzione riscritta di `E_UI_COLONNA_CODICE_IMMUTABILE` portava una
virgola in un campo senza virgolette (riga 1265, sette campi su sei); corretta mettendo il campo tra virgolette, e il
conteggio dei campi rifatto sui tre CSV toccati. Parte la richiesta al team BE: BE32 (§6). ⏳ La doc auto-generata di
`ui` da rigenerare: le schede di `ui.fn_configurazione_senza_codici` e `ui.trgfn_voce_ritira_dalle_preferenze`, a cui
le pagine `manual/` già rimandano, nascono lì. ✅ Il `/verifica-db` di Q55 (sotto).

**La verifica (`/verifica-db d265aaa463`, sessione DB, 2026-11-22; con i giri 3 e 4 nella stessa sessione, per scelta di
Tid).** Il commit è applicato su dbdev e pushato. Nessun difetto nei changeSet `-27` e `-28`, nei CSV (sei campi per
riga, il messaggio 1531 unico) né nei lucchetti, e nessun pgTAP rotto dai lucchetti nuovi (cercati gli `UPDATE` di
`lista_colonna.lista_id`, `dashboard_widget` e `widget.codice`: c'è solo il caso 4 di `test-ui-legami-preset-v1`, già
adeguato). Le FK verso `lista_definizione` e `dashboard_definizione` sono senza azione: nessuna cancellazione a cascata
passa dal ritiro. Il COMMENT nuovo di `ui.fn_intero_da_jsonb` provato sui quattro esempi che cita. Trovato:
* **Un caso del ritiro della card senza test**: il filtro sulla dashboard (la stessa card nel pool di un'altra
  dashboard, con la sua preferenza). Aggiunto come caso 15 di `ui/test-ui-ritiro-voce-preferenze-v1` (plan 15), con la
  riga del test nella pagina `manual/` del trigger. Verde sullo scratch e nella corsa di Tid (2026-11-22).
* **Q57, a Tid** (§7.1): la card tolta dal pool e cancellata dal catalogo **nello stesso statement** (una CTE che
  cancella la riga del pool e il widget) lascia la voce nella preferenza. Il trigger `AFTER` scatta a fine statement,
  quando `ui.widget` non ha più la riga: il codice letto è NULL, `ARRAY[NULL]` non toglie niente, e la preferenza torna
  a non salvarsi (il difetto di Q55). La FK senza azione non lo ferma, perché la controlla anche lei a fine statement,
  quando la riga del pool non c'è più. Provato sullo scratch in transazione annullata: la preferenza resta con due card
  invece di una. Lo incontra solo chi scrive il catalogo (il migrate), ma il modello lo ammette. Correzione proposta, con
  un changeSet nuovo: nel ramo della dashboard non cercare il codice della card ritirata, ma togliere dalle preferenze di
  `OLD.dashboard_id` ogni codice che il pool non ha più (la stessa domanda della bonifica, ristretta alla dashboard).

**La ricaduta sul BE** (BE32, §6; Q56 decisa (a) da Tid il 2026-11-22, il rifiuto si ritira): il service delle colonne conta le preferenze che nominano la colonna e
rifiuta la cancellazione (`E_UI_COLONNA_IN_USO`, «in uso da preferenze utente»). Con Q55 il database ritira la voce
da sé, e quel rifiuto non protegge più niente.

### 3.3 Giro 3 — le misure

**U15 (A) — `lista_preset.pagina_dimensione` ha `DEFAULT 25`, il COMMENT dice «NULL = il default»** · aree B, C · Q9.

* **Fatto.** Un INSERT che non nomina la colonna scrive 25 fisso, non NULL: il preset non segue più il default `PAGINA`
  del catalogo, e se 25 esce dal catalogo quell'INSERT è rifiutato. È una seconda sede del default. Verificato il
  2026-11-18. Il BE passa la colonna esplicita (`ui_admin_repository.py:622-644`), quindi lo scatto riguarda il seed e
  ogni scrittura futura che non la nomina.
* **Correzione proposta.** `DROP DEFAULT`. Le righe del seed che scrivono 25 o 10 esplicitamente si decidono una per una:
  quelle che intendono «il default» passano a NULL (Q9).
* **Decisione (Q9, Tid, 2026-11-18).** Sì `DROP DEFAULT`. Le righe del seed per gruppo, non una per una (fatto
  datato, dbdev 2026-11-18: 113 preset, 70 a 25, 36 a 10, 3 a 50, 4 NULL):
  * **25 → NULL**: seguono lo standard `PAGINA`;
  * **50 → NULL** anche loro (le liste fornitori, soggetti e «fondi fattura da decidere»): Tid li porta allo standard;
  * **10 → NULL**, con la lista che dichiara l'uso `COMPATTA` (Q11 decisa (a)).
* **Presidio.** Un INSERT senza la colonna: `pagina_dimensione IS NULL`.

**U16 (B) — Una misura citata solo da preferenze si toglie, e poi la preferenza non si aggiorna più** · area C · Q10.

* **Fatto.** La FK verso il catalogo arriva solo dai preset. Una misura citata solo da preferenze si toglie o si
  riscrive senza rifiuto. Il guard della preferenza (`INSERT OR UPDATE OF configurazione`) giudica il valore che resta:
  da quel momento ogni UPDATE della preferenza è rifiutato, anche se tocca solo le colonne. Il resolver, invece, scarta
  la misura e risponde lo standard.
* **Correzione proposta.** (a) Il guard giudica solo un valore nuovo. (b) Il ritiro di una misura dal catalogo toglie la
  chiave dalle preferenze. **Raccomandata (b)**: per il resolver una misura ritirata non è già più una scelta.
* **Decisione (Q10, Tid, 2026-11-18).** (b): il ritiro di una misura dal catalogo toglie la chiave dalle preferenze che la
  citano; il resto della preferenza non si tocca.
* **Presidio.** Una misura di prova, una preferenza che la cita, la misura tolta, poi l'UPDATE delle sole colonne.

**U17 (B) — `misure_pagina.misura` «non si riscrive», ma niente lo impedisce** · area C.

* **Fatto.** Il COMMENT lo dice, ma nessun lucchetto lo impone. Se nessun preset cita la misura, l'UPDATE passa: le
  preferenze che la citano restano orfane, e `uso_default` resta sulla riga, che ora ha il numero nuovo.
* **Correzione proposta.** Un lucchetto di colonna, nel registro dei lucchetti già usato dagli altri cataloghi.
* **Presidio.** L'UPDATE di `misura` è rifiutato.

**U18 (B) — Il catalogo può restare senza un default** · area C.

* **Fatto.** `uq_misure_pagina_uso_default` dice «al più una» riga per uso, non «esattamente una». Togliere il default
  riesce. Da quel momento `fn_get_misure_pagina` solleva `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`, e il FE si ferma nel
  guard del router a ogni pagina (`router/index.js:766-778`).
* **Correzione proposta.** Un constraint trigger differito: a fine transazione `COMPATTA` e `PAGINA` hanno una riga
  ciascuna.
* **Presidio.** Togliere l'uso `PAGINA` senza spostarlo è rifiutato al commit; spostarlo nella stessa transazione passa.

**U19 (C) — Tre regole per la stessa misura scritta nel JSONB** · area C.

* **Fatto.** Il guard vuole un numero di al più nove cifre. Il resolver delle liste accetta anche la stringa `"25"`, che
  il guard rifiuta. Il resolver della dashboard ha una terza espressione.
* **Correzione proposta.** Un BB `ui` «la misura di un JSONB, o niente», letto dal guard e dai due resolver. Si scrive
  nel giro 2, insieme al guard di forma di U12 che lo legge (§2).

**U20 (B) — La lista ripiega sempre sul default `PAGINA`** · area C · Q11.

* **Fatto.** Il ripiego del resolver è sempre il default `PAGINA`. Una lista configurabile mostrata compatta (in un
  drawer o in un dialog) non può dire `COMPATTA`: il 10 sta scritto nei preset del seed, e se `COMPATTA` si sposta quei
  preset restano a 10.
* **Correzione proposta.** (a) `lista_definizione` dichiara l'uso (`COMPATTA` o `PAGINA`) e il resolver ripiega su quel
  default. (b) Resta così.
* **Decisione (Q11 e Q11-bis, Tid, 2026-11-18).** (a): `lista_definizione` dichiara l'uso (`COMPATTA` o `PAGINA`,
  iniziale `PAGINA`; le liste di righe segnate `COMPATTA` nel seed) e il resolver ripiega sul default di quell'uso. Con
  Q9, i preset a 10 diventano NULL. Q11-bis: le liste configurabili prendono la misura dal DB; `DEFAULT_LIMIT` del BE
  resta solo per gli endpoint fuori catalogo, dichiarato come regola dell'API (BE10).

**U21 (B) — Il massimo di card della dashboard non ha una sede** · aree C, D · Q12.

* **Fatto.** `dimensione_max` è un tetto («al più N card»), non una scelta del paginatore: non è una seconda sede di
  `misure_pagina`, e la regola del 2 non si applica. Però:
  * sul preset la colonna è nullable, ha `DEFAULT 8` e nessun CHECK: 0 e i negativi passano, e il FE li tratta come
    «nessun tetto» (`useDashboardConfig.js:185`, `DashboardWidgetModal.vue:81`), un significato che il DB non dichiara;
  * nella preferenza la verifica la fa solo il BE (`dashboard_preferenza_service.py:205-220`, un tetto di 100 preso da
    una costante che il suo commento dice di un'altra regola);
  * l'8 sta in quattro sedi: il default della colonna, una costante del resolver, `useDashboardConfig.js:173` e
    `DashboardWidgetModal.vue:37`. Il resolver non risponde mai NULL, quindi i ripieghi del FE non servono.
* **Correzione proposta.** (a) `CHECK (dimensione_max > 0)` sul preset, dove NULL vuol dire lo standard; il guard di forma
  sulla preferenza (U12); l'8 in una sede DB sola. (b) Un catalogo di scelte come `misure_pagina`. **Raccomandata (a).**
  Da decidere anche se il tetto 100 sta nel DB e se «≤0 = nessun tetto» resta (raccomandato: no).
* **Decisione (Q12, Tid, 2026-11-19).** (a): `CHECK (dimensione_max > 0)` sul preset, NULL = lo standard, l'8 in una
  sede DB sola; il tetto 100 sta nel DB (guard di forma, Q6), il tetto vale fra 1 e 100; «≤0 = nessun tetto» non
  esiste. BE e FE ritirano le loro copie dell'8 e del 100 (BE11, FE1).
* **Presidio.** Un preset a 0 è rifiutato; nella preferenza sono rifiutati `"abc"`, 0 e -1.

### 3.3-bis Il piano del giro 3 (sessione DB, 2026-11-21)

Corpi e struttura letti da dbdev il 2026-11-21 (`pg_get_functiondef`, `pg_trigger`, `\d`): l'ultimo changeSet su `ui` è
`20261120-35`; i resolver sono quelli di `20261120-29` e `-30`. Il via di Tid al giro è del 2026-11-21.

**Che cosa ha trovato la lettura, prima di scrivere.**

* **`lista_preset.pagina_dimensione` è una colonna dell'installazione** nel registro del seed (riga 5): il CSV la scrive
  solo sulle righe di seed intatte. Q9 arriva quindi su ogni preset non personalizzato; su quelli personalizzati la misura
  resta quella scelta dall'installazione, che il modello ammette.
* **Il vocabolario degli usi (`COMPATTA`, `PAGINA`) avrebbe avuto tre copie**: il CHECK di `misure_pagina.uso_default`,
  la colonna nuova di U20 e il constraint trigger di U18, che deve elencarli. → Q44.
* **Il tetto 1-100 ha già una sede**, `ui.fn_dimensione_max_ammessa` (giro 2). Un CHECK letterale sul preset la
  ricopierebbe. → Q45.
* **La colonna nuova di `lista_definizione` va classificata** nel registro del seed (riga 3, per colonna): senza, il
  giro delle automazioni non rimonta il trigger (linee-guida-sql §11.7). → Q46.
* **Il «Trovato scrivendo» del giro 2** (§3.2-bis: una preferenza con una misura uscita dal catalogo non salva più le
  colonne) si chiude con U16 e U17: la misura non si riscrive e il ritiro toglie la chiave nella stessa istruzione.
  Non serve una bonifica: il backfill `20261120-25` ha portato in forma le preferenze, il guard tiene le scritture e
  nessun changeSet cancella righe di `misure_pagina` (la struttura dei changelog, non un conteggio).
* **Il seed sposta la data del contenuto**: un preset da 25 a NULL, o da 8 a NULL, cambia ciò che dice («25 fisso» →
  «lo standard»), e `trgfn_preset_contenuto_aggiornato` sposta la chiave della misura. Chi ha una misura sua su quella
  lista vede il banner del preset aggiornato una volta, anche se il valore risolto non cambia. Accettato: è un cambio
  vero del preset.

**I pezzi.**

| changeSet | Che cosa | Difetto |
| --- | --- | --- |
| `20261120-36` (00_schema) | L'enum `ui.uso_misura_pagina` (Q44); `misure_pagina.uso_default` passa all'enum e perde il CHECK; `lista_definizione.uso_misura` (enum, NOT NULL, iniziale `PAGINA`) | U20, Q44 |
| `20261120-37` (00_schema) | `DROP DEFAULT` su `lista_preset.pagina_dimensione` e `dashboard_preset.dimensione_max`; CHECK del tetto sul preset col BB (Q45); i COMMENT delle due colonne (M1) | U15, U21 |
| `20261120-38` (20_code) | `ui.fn_misura_pagina_default`: il confronto con l'enum; la firma resta | U20 |
| `20261120-39` (20_code) | Il constraint trigger differito su `misure_pagina`: a fine transazione ogni uso dell'enum ha il suo default (chiede `fn_misura_pagina_default`, che solleva) | U18 |
| `20261120-40` (20_code) | Il ritiro di una misura toglie la chiave dalle preferenze di lista che la citano (`AFTER DELETE`) | U16 |
| `20261120-41` (20_code) | `ui.fn_resolve_lista_config`: il ripiego sul default dell'uso della lista | U20 |
| `20261120-42` (90_end) | Il runner dei lucchetti su `ui`: monta il lucchetto di `misure_pagina.misura` | U17 |

CSV: `lista_definizione.csv` con `uso_misura` (`COMPATTA` sulle 36 liste che il seed apriva a 10), il loader
`20260507-06` con la colonna; `lista_preset.csv` con i 25, i 50 e i 10 a NULL (Q9); `dashboard_preset.csv` con l'8 a
NULL (Q12); la riga 3 del registro del seed con `uso_misura` fra le colonne del software (Q46); il lucchetto di
`misure_pagina.misura` in `automation_lock_columns.csv`; il codice `E_UI_MISURA_PAGINA_IMMUTABILE`
(`CONFLITTO_STATO`, messaggio 1523). pgTAP nuovo `ui/test-ui-misure-catalogo-e-uso-v1`; adeguati quelli che
asserivano il contratto di prima.

⚠️ **Numerazione** (Tid, 2026-11-21): il giro usa il progressivo `20261120-NN`, dal primo libero (`-36`); il `20261121`
è dell'altra sessione aperta sullo stesso albero (il lucchetto dell'emittente, `20261121-09`). La prima stesura dei file
portava `20261121-08` … `-14`, rinumerati prima di ogni prova.

✅ **Scritto e provato** (sessione DB, 2026-11-21). I sette changeSet nella tabella sopra; CSV: `lista_definizione.csv`
(36 `COMPATTA`, 77 `PAGINA`) col loader `20260507-06`, `lista_preset.csv` (109 misure a NULL), `dashboard_preset.csv`
(l'8 a `NULL`, e il commento del loader `20260722-04`), la riga 3 del registro del seed, il lucchetto, il codice e il
messaggio. Pagine `manual/`: `misure_pagina`, `lista_preset`, `dashboard_preset`, `lista_definizione`,
`fn_misura_pagina_default`, `fn_resolve_lista_config`, `fn_dimensione_max_ammessa`, e due nuove
(`trgfn_misure_pagina_guard_default_per_uso`, `trgfn_misure_pagina_ritira_dalle_preferenze`); la guida
`configurazione-liste` §2.6 e §3. pgTAP adeguati, con la ragione sopra la riga: `test-misure-pagina-v1` (l'enum non ha
collation: si ordina sul testo) e i quattro `test-lista-{contratti,preventivi,ordini,offerte}-seed` (il preset di
sistema ha la misura NULL, non 25).

**La prova** (`prova_changeset.py`, sullo scratch, `-36` … `-41` in ROLLBACK): l'estratto gira intero. Il pgTAP nuovo
è verde 17 su 18; il caso 15 (il lucchetto) lo monta il runner di `-42`, e lo prova la corsa dopo l'apply. Regressione su
tutti i 28 pgTAP di `ui`, senza e con l'estratto: verdi, salvo quattro.

* `test-lista-definizione-perimetro-emittente-v1` e `test-ui-legami-preset-v1` si fermano uguali **senza** l'estratto: la
  prova gira da owner, e il seed non lascia cancellare una riga nata dal seed (gia' visto nel giro 2b).
* `test-misure-pagina-v1`, caso 16: rosso da owner per costruzione, uguale senza l'estratto.
* `test-seed-primo-impianto-ui-installazione-v1`, caso 3 (le divergenze della regola su `ui`): nuovo rosso nella sola
  prova. L'estratto aggiunge `uso_misura`, ma il registro del seed (CSV) non è caricato e il trigger non è rimontato. Al
  migrate il mirror del registro e il giro delle automazioni lo riallineano: è lo stesso caso di `filtri_default` nel
  giro 2.

⚠️ **Prima corsa di Tid col runner** (2026-11-21): il test nuovo si fermava a «permesso negato per la tabella
misure_pagina». Il runner gira come applicazione, e la prova sull'estratto gira da owner: la differenza non si vedeva.
Il test scrive il catalogo, che l'applicazione legge soltanto: marcato `pgtap-runner: owner` col motivo (forma 3 del
criterio di `scripts/testpgtap.sh`: il guard difende da uno scrittore privilegiato).

✅ **Applicato** su dbdev con i pgTAP di `ui` verdi, compreso il caso 15 del test nuovo (il lucchetto montato da `-42`),
e committato con la doc auto-generata rigenerata, schede dei due trigger nuovi comprese (Tid, 2026-11-21,
`ea04ec5f45`). ✅ Il `/verifica-db` del giro (sotto).

**La verifica (`/verifica-db ea04ec5f45`, sessione DB, 2026-11-22).** Il commit è applicato e pushato. I sette changeSet
sono puliti: nomi, id e `logicalFilePath` allineati, preCondition su oggetti nati prima, proprietà fuori dal corpo
ripetute, COMMENT al presente. Lo sono anche i CSV (113 misure dei preset a NULL, le 36 a 10 coincidono con le 36 liste
`COMPATTA`) e il pgTAP nuovo (plan 18, il mondo costruito). Trovato:
* **La testata del caricatore delle misure insegnava una strada che `-39` chiude.**
  `80_data/changelog/20260930-02` diceva di spostare un default «in due giri del CSV: prima si toglie, poi si mette». Il
  trigger differito rifiuta al commit il primo giro, che lascia un uso senza default. Resta un giro solo, e l'indice
  unico parziale, che non è differibile, lo fa passare solo se nel CSV la riga che perde l'uso viene prima di quella che
  lo prende. Corretti la testata (è un commento: il checksum non cambia, e il caricatore ha `validCheckSums: ANY`) e la
  pagina `manual/` di `misure_pagina`.
* **Q58, a Tid** (§7.1): `ui.fn_get_misure_pagina`, la lettura dell'applicazione, scrive a mano i due usi (`'COMPATTA'` e
  `'PAGINA'`, nelle chiavi fisse `default_compatta` e `default_pagina`). Con un valore nuovo dell'enum
  `ui.uso_misura_pagina` il trigger di `-39` pretende il suo default, ma l'applicazione non lo vede. È la sede del
  vocabolario fuori dall'enum che Q44 voleva togliere, e i censimenti di `-36` e di §3.3 non la contavano. Chiuderla
  vuole un changeSet sulla funzione e un contratto nuovo verso BE/FE (per esempio un oggetto dei default per uso,
  costruito da `enum_range`).
* **Chi chiede `ui.fn_misura_pagina_default`**: dopo il giro 6 (`20261121-27`) il resolver non la chiama più, e passa da
  `ui.fn_misura_pagina_risolta`, che serve anche `ui.fn_misura_lista`. Lo dice `pg_depend` su dbdev: i chiamanti
  sono `fn_get_misure_pagina`, il guard di `-39` e `fn_misura_pagina_risolta`. Corretta la pagina `manual/`. Il COMMENT
  della funzione nomina ancora il resolver: si corregge alla prossima riscrittura della funzione, con un changeSet
  nuovo (debito di testo, nessun comportamento).
* La testata e la riga 7 di questo brief davano ancora «⏳ registrare apply e pgTAP del giro 3»: allineate.

**Le ricadute BE/FE del giro 3** (⏳ da ora, giro applicato il 2026-11-21): BE10 e FE1 (§6). Nessuna garanzia ritirata: il giro aggiunge vincoli
e toglie due default. Un `INSERT` del BE in `ui.lista_preset` o `ui.dashboard_preset` che non nomina la misura ora
scrive NULL (lo standard) invece di 25 o 8: il BE la passa esplicita (`ui_admin_repository.py:622-644`, §3.3 U15),
quindi niente cambia; se ne passa una, il resolver la rispetta come prima. Il codice nuovo
`E_UI_MISURA_PAGINA_IMMUTABILE` non lo incontra l'app, che non scrive `misure_pagina`.

### 3.4 Giro 4 — il catalogo delle liste

**U22 (B) — Una lista con colonne o preset accesi non si spegne** · area A · Q13.

* **Fatto.** I trigger `trg_lista_definizione_a10_lista_colonna_block_deact_upd` e `…_lista_preset_block_deact_upd`
  rifiutano lo spegnimento di una lista con figli accesi. Per spegnerla si spengono prima tutte le colonne e tutti i
  preset, e alla riaccensione non resta traccia di quali erano accesi. Una lista spenta già non risponde
  (`fn_lista_da_codice`). Fino al giro 0 la guida diceva il contrario («preset, colonne e preferenze sopravvivono»);
  ora descrive il blocco.
* **Correzione proposta.** (a) Le FK `lista_id` di colonne e preset fra le eccezioni ATTIVO: la lista spenta sospende le
  sue parti, come la decisione del 2026-11-08 sulle righe di composizione. (b) Il blocco resta, e la guida lo dice già.
  **Raccomandata (a).**
* **Decisione (Q13, Tid, 2026-11-19).** (a): la lista spenta sospende colonne e preset senza toccarli; le FK `lista_id`
  entrano fra le eccezioni ATTIVO, nella forma della decisione del 2026-11-08. Alla riaccensione tutto torna com'era.
* **Decisione (Q35, Tid, 2026-11-20), che completa Q13.** Le preferenze della lista spenta restano, e si sospendono con
  la lista. Una riaccensione rifiutata dalla verifica di Q16 nomina le colonne orfane.
* **Presidio.** Una lista costruita con colonna e preset accesi si spegne (`lives_ok`) e `fn_lista_da_codice` la
  rifiuta; dopo la riaccensione le colonne sono intatte.

**U23 (B) — Le dichiarazioni del seed le può cambiare l'app** · area A · Q14.

* **Fatto.** Il guard «solo il proprietario» copre `multi_emittente` e nient'altro:
  * `perimetro_emittente`: il COMMENT dice «mai da interfaccia», ma l'app ha UPDATE e niente la sorveglia. Portarla a
    `false` apre la schermata senza chiedere l'azienda, cioè lo stesso effetto che il guard impedisce su
    `multi_emittente`;
  * il `codice`, la `vista_sql` e lo `schema_dati` di una lista certificata: rinominarli sposta la certificazione su
    un'altra schermata o un'altra vista (il BE li ammette, `lista_definizione_admin_service.py:76-80`);
  * il `codice` di una colonna, che è la chiave delle preferenze e dei preset (JSONB per codice): il BE lo ammette
    (`ui_admin_repository.py:473-479`).
* **Correzione proposta.** `perimetro_emittente` nello stesso guard di `multi_emittente` (una funzione sola, con l'elenco
  delle colonne); il codice della lista e quello della colonna immutabili; il cambio di vista di una lista certificata
  solo dall'owner. `ricerca_min_caratteri` a scelta di Tid.
* **Decisione (Q14, Tid, 2026-11-19).** Tutte e cinque: `perimetro_emittente` nello stesso guard di `multi_emittente`
  (una funzione sola, con l'elenco delle colonne); il codice della lista immutabile; il codice della colonna
  immutabile; ~~vista e schema dati di una lista certificata solo dall'owner~~ (superata da QU4); `ricerca_min_caratteri`
  resta all'app (è una regolazione, non una dichiarazione del codice).
* **Decisione (Q27, Tid, 2026-11-20), che completa Q14.** Il mirror `runOnChange` di `lista_definizione` carica anche
  `ricerca_min_caratteri`, e il migrate riscriverebbe la regolazione dell'app al primo cambio del CSV. La colonna si
  dichiara d'installazione nel censimento del brief del seed, con le altre tabelle di `ui` che l'app scrive.
* **Decisione (QU4 del brief del seed, §16.15, Tid, 2026-11-20).** Una lista certificata nasce sempre dal seed, e sulle
  righe di seed `codice`, `schema_dati`, `vista_sql` e i due flag sono colonne del software (`E_SEED_COLONNA_DEL_SOFTWARE`).
  Di Q14 resta qui ciò che il seed non copre: `codice` della lista e della colonna immutabili, `multi_emittente` e
  `perimetro_emittente` solo dal migratore, su ogni riga. «Vista e schema dati di una lista certificata solo dall'owner»
  si ritira: la tiene il seed per colonna, e due guard per la stessa regola divergono.
* **Presidio.** Come app, ciascun UPDATE è rifiutato; come owner passa.

**U24 (B) — Un'azione può avere un campo sorgente, e allora entra nella ricerca** · area A.

* **Fatto.** Il COMMENT dice «campo_sorgente NULL per azione», ma il modello lo ammette valorizzato, e
  `valida_campo_sorgente` salta le azioni. Un'azione con un campo inventato e `ricercabile_full` entra in
  `fn_lista_colonne_ricerca_full`, e la ricerca interroga un campo che non c'è.
* **Correzione proposta.** `CHECK (tipo_colonna <> 'azione' OR campo_sorgente IS NULL)`, e il salto nel trigger si ritira.
* **Presidio.** Un'azione con un campo sorgente è rifiutata.

**U25 (B) — Una colonna composta esportabile esce vuota** · area E.

* **Fatto.** Una colonna con `campo_sorgente` NULL, tipo diverso da `azione` ed `esportabile = true` (il default) è
  ammessa. Il BE la esporta come una colonna di celle vuote (`lista_export_service.py:205-212`), mentre il contratto
  dice che le composte non si esportano, come le azioni. Oggi lo tiene solo il seed.
* **Correzione proposta.** Un CHECK gemello di `chk_ui_lista_colonna_azione_non_esportabile`: senza campo sorgente,
  non esportabile.
* **Presidio.** Il CHECK su una colonna composta esportabile.

**U26 (B) — I nomi della lineage passano su qualunque lista** · area A · Q15.

* **Fatto.** `valida_campo_sorgente` accetta, per ogni lista, anche i nomi di `vendite.vw_documento_lineage_sintesi_colonne`.
  Il catalogo non sa quali colonne non stanno nella vista, quindi ricerca, filtri e ordinamento le trattano come
  colonne della vista. Il guard di `ui` dipende da una vista di `vendite`.
* **Correzione proposta.** (a) La lista dichiara che legge la lineage, e i nomi si ammettono solo lì. (b) Un marcatore
  sulla colonna (vista oppure lineage), letto dal guard e da `ricerca_full`. **Raccomandata (b).**
* **Decisione (Q15, Tid, 2026-11-19).** (b): un marcatore sulla colonna (vista oppure lineage), letto dal guard e da
  `ricerca_full`; filtri e ordinamento escludono le colonne lineage. Per rifiutare un nome della lineage su una lista non
  documentale serve il lato lista: prima del giro si cerca se il DB sa già quali liste sono documentali (per esempio
  dalla configurazione delle sorgenti che il BE legge, `config.sorgenti`); se c'è si usa quella, altrimenti la
  dichiarazione (a). La dipendenza del guard di `ui` da una vista di `vendite` si ritira.
* **Presidio.** Un nome della lineage su una lista non documentale è rifiutato.

**U27 (B) — Le colonne non si riverificano quando la vista cambia, né su una lista spenta** · area A · Q16.

* **Fatto.**
  * Né un cambio di `vista_sql` o di `schema_dati`, né una vista che perde colonne riverificano le colonne. Le vede solo
    il pgTAP del catalogo, e sulle sole righe del seed; un cambio fatto dalla pagina tecnica gli sfugge. Il test spiega
    perché la verifica non sta nel trigger della definizione: l'ordine di carico dei CSV.
  * Il gemello della vista salta sulle liste spente, `valida_campo_sorgente` no. Su una lista spenta registrata prima
    della sua vista (un percorso che la guida descrive) non entrano colonne con un campo sorgente.
  * Tutti e due i trigger ammettono viste, viste materializzate e tabelle, ma non le tabelle partizionate, che esistono.
* **Correzione proposta.** (a) Per le scritture che non vengono dall'owner, un controllo immediato al cambio di vista; il
  salto sulle liste spente, con la verifica all'accensione; le partizionate ammesse. Il tutto in un BB «relazione e
  attributo di una lista», letto dai due trigger e dal pgTAP. (b) Solo il presidio pgTAP. **Raccomandata (a).**
* **Decisione (Q16, Tid, 2026-11-19).** (a): controllo immediato al cambio di vista per le scritture dell'app (il seed
  resta al pgTAP); salto sulle liste spente con la verifica all'accensione (coerente con Q13); partizionate ammesse; un
  BB «relazione e attributo di una lista» letto dai due trigger e dal pgTAP.
* **Decisione (Q32, Tid, 2026-11-20), che completa Q16.** Una vista che perde colonne (un DDL sulla vista, che nessun
  trigger di `ui` vede): un presidio `dbops` confronta le colonne di ogni lista con la sua relazione, e legge il BB
  «relazione e attributo di una lista». Copre anche le liste create dall'app, che il pgTAP sul seed non vede.
* **Presidio.** Come app, un cambio di vista che lascia orfana una colonna è rifiutato; su una lista spenta la colonna è
  accolta e rifiutata all'accensione; una lista su una partizionata è accolta.

**U28 (B) — Testi vuoti ammessi su liste, dashboard e widget** · aree A, D.

* **Fatto.** `lista_colonna` ha i CHECK «non vuoto»; `lista_definizione` no (`vista_sql`, `schema_dati`, `codice`,
  `descrizione`, `note`), e nemmeno le testate delle dashboard e il widget (`codice`, `etichetta`,
  `etichetta_i18n_key`, `contatore_key`). Una `vista_sql = ''` su una lista spenta entra, e da lì fa rifiutare ogni
  colonna con un campo sorgente.
* **Correzione proposta.** I CHECK «non vuoto», con una bonifica se il catalogo ne ha.
* **Presidio.** Una stringa vuota per colonna, rifiutata.

**U29 (B) — Con la veste NULL, il permesso di colonna lo decide l'identità più permissiva** · area A · Q17.

* **Fatto.** Se `p_veste` è NULL, in `fn_lista_colonne_livello` concorrono i profili di tutte le identità dell'utente: un
  AD_HOC `TUTTO` dell'identità di portale scavalca un REPARTO `BLOCCATO` dell'operatore. I due chiamanti passano NULL
  quando la variabile di sessione manca o è fuori dominio. Un ripiego pensato per la presentazione fa da permesso di
  riservatezza.
* **Correzione proposta.** (a) Nessun permesso, come senza utente. (b) Per ogni colonna, il livello più restrittivo fra
  le vesti. (c) Resta così. **Raccomandata (b)**: non allarga mai, e la schermata si apre lo stesso.
* **Decisione (Q17, Tid, 2026-11-19).** (b): con la veste NULL, per ogni colonna vale il livello più restrittivo fra le
  vesti dell'utente; il ripiego non allarga mai. La stessa regola vale per la cascata dei preset, che con la veste NULL
  salta il passo del ruolo (Q28, 2026-11-20, U4).
* **Presidio.** Un utente con due identità, la variabile vuota: la colonna resta BLOCCATO.

**U30 (C) — La cancellazione di una colonna in un preset: il commento dice cascata, la FK blocca** · aree A, E · Q18.

* **Fatto.** `fk_lista_preset_colonna_lista_colonna` è NO ACTION: una colonna che sta in un preset non si cancella. Il
  commento del BE (`lista_colonna_admin_service.py:276-279`, `ui_admin_repository.py:509-510`) dice «CASCADE». Il
  controllo preventivo conta solo le preferenze, quindi il caso del preset finisce nel ripiego generico dell'errore
  d'integrità. Il messaggio di `E_UI_COLONNA_IN_USO` cita anche i permessi, che invece vanno a cascata.
* **Correzione proposta.** (a) CASCADE: la riga del preset è di composizione, come il permesso. (b) NO ACTION, con il
  controllo preventivo che conta anche i preset, il commento e il testo corretti. **Raccomandata (a).**
* **Decisione (Q18, Tid, 2026-11-19).** (b): la FK resta NO ACTION, coerente con Q8 (il widget tolto dal pool). Il
  controllo preventivo conta anche i preset; il messaggio di `E_UI_COLONNA_IN_USO` nomina i preset e non i permessi
  (che vanno a cascata); i commenti del BE si correggono. Il gesto ordinario resta lo spegnimento della colonna.

### 3.4-bis Il piano del giro 4 (sessione DB, 2026-11-21) — applicato, pgTAP verdi

Corpi e struttura letti da dbdev il 2026-11-21 (`pg_get_functiondef`, `pg_trigger`, `\d`), dopo l'apply del giro 3:
nessun changeSet dei giri 1-3 tocca i corpi di U22-U30 (`valida_campo_sorgente`, `valida_vista_sql`, il guard
multi-emittente, `fn_lista_colonne_livello`). Il via di Tid al giro è del 2026-11-21.

**Che cosa ha trovato la lettura, prima di scrivere.**

* **Q15: il DB non sa quali liste sono documentali.** `config.sorgenti` non porta la lista e `lista_definizione` non
  porta la sorgente; nessuna colonna lega le due. Q15 dice che allora serve la dichiarazione dal lato della lista
  (a). → Q47, la forma.
* **Il nome di una colonna della lineage, senza `vendite`.** Q15 ritira la dipendenza del guard di `ui` da
  `vendite.vw_documento_lineage_sintesi_colonne`: il guard non può più verificare che `frontiera_codice` esista. →
  Q48, chi lo verifica.
* **Il seed rispetta già la forma di Q15.** Le sei colonne `transito` (`frontiera_codice`, sulle liste contratti, DDT,
  offerte, ordini, preventivi, resi) non sono filtrabili, ordinabili né ricercabili (fatto datato, dbdev 2026-11-21).
  Si può dire con un CHECK: una colonna della lineage non è filtrabile, ordinabile né `ricercabile_full`. Il CHECK è
  la sede unica, e `fn_lista_colonne_ricerca_full` non deve leggere il marcatore: con il CHECK non le incontra.
* **Sulle liste senza vista la verifica del campo non c'è.** `vista_sql` è nullable: una lista servita da una funzione
  del BE (le pagine admin, i lotti, le distinte) non ha relazione da confrontare, e il guard salta. È il modello, non un
  difetto nuovo. Le colonne di quelle liste che oggi passano «perché il nome sta nella lineage» (`codice`,
  `stato_descrizione`…) passano per il salto, non per la lineage: il ritiro di Q15 non le tocca.
* **Q13 ritira una garanzia.** Oggi `trgfn_child_requires_active_parent` garantisce «una colonna accesa, o un preset
  acceso, sta su una lista accesa». Con le due FK `lista_id` fra le eccezioni ATTIVO, una lista spenta tiene colonne e
  preset accesi. → «Garanzie ritirate», sotto.
* **U23: il codice immutabile ha già lo strumento.** Il registro dei lucchetti (`dbops.automation_lock_columns`) e il
  runner su `ui` tengono già il posto del preset e la misura del catalogo; il seed riscrive uguale e passa. Il codice
  della lista e quello della colonna entrano lì, non in un trigger nuovo.
* **U23: `perimetro_emittente` va nel guard al contrario.** Il guard di `multi_emittente` scatta all'INSERT solo se il
  flag nasce acceso, perché il pericolo è `true`. Per `perimetro_emittente` il pericolo è `false` (la schermata si apre
  senza chiedere l'azienda). Il guard comune riceve, per ogni colonna, il valore che si può scrivere senza permesso.
* **U24 e U25 rendono superfluo `chk_ui_lista_colonna_azione_non_esportabile`.** «Un'azione non ha campo sorgente»
  (U24) e «senza campo sorgente, non esportabile» (U25) insieme dicono già che un'azione non si esporta: il CHECK di
  oggi diventa una seconda sede della stessa regola, e si ritira (regola del 2). Il BE lo mappa per nome (BE13).
* **U28: nessuna bonifica.** Nessuna stringa vuota nelle colonne di U28 (fatto datato, dbdev 2026-11-21): i CHECK
  entrano senza correzioni del catalogo.
* **U29: le vesti dell'utente si leggono dalla regola che c'è.** «La veste è utilizzabile» ha il suo BB
  (`script.fn_veste_utilizzabile`); le vesti di un utente sono le sue identità per cui vale. Con la veste NULL la
  funzione calcola il livello sotto ciascuna e tiene il più restrittivo. Una veste senza profili conta anche lei: le
  sue colonne sensibili sono BLOCCATO, e saltarla allargherebbe.
* **U27: il presidio di Q32 vede anche le liste dell'app.** Il pgTAP di oggi (`test-lista-colonna-campo-sorgente-in-vista-v1`)
  copre il seed. Il presidio `dbops` legge lo stesso BB e confronta ogni lista accesa con la sua relazione.

**I pezzi** (numeri dal primo libero del progressivo `20261120`, da riverificare con `prossimo_changeset.py` prima di
ogni file).

| changeSet | Che cosa | Difetto |
| --- | --- | --- |
| `-43` (00_schema) | L'enum `ui.origine_campo_lista` (`VISTA`, `LINEAGE`); `lista_colonna.origine_campo` (NOT NULL, iniziale `VISTA`); la dichiarazione della lista di Q47; i CHECK di U24, di U25 e della lineage (né filtrabile, né ordinabile, né ricercabile); il ritiro di `chk_ui_lista_colonna_azione_non_esportabile`; i COMMENT | U24, U25, U26 |
| `-44` (00_schema) | I CHECK «non vuoto»: `lista_definizione` (`codice`, `descrizione`, `schema_dati`, `vista_sql`, `note`), `dashboard_definizione` (`codice`, `descrizione`, `note`), `widget` (`codice`, `etichetta`, `etichetta_i18n_key`, `contatore_key`) | U28 |
| `-45` (20_code) | Il BB `ui.fn_lista_relazione_ha_attributo(schema, relazione, attributo)`: la relazione esiste (vista, vista materializzata, tabella, tabella partizionata) e, con l'attributo, ha la colonna | U27 |
| `-46` (20_code) | `valida_campo_sorgente` riscritta: legge il BB; salta sulle liste spente (la verifica è all'accensione); una colonna `VISTA` sta nella relazione, una `LINEAGE` sta su una lista che la dichiara; via il ramo `= ''` e il salto delle azioni; via la lettura di `vendite`. Il trigger aggiunge `origine_campo` alle colonne di `UPDATE OF` | U26, U27, U37, U24 |
| `-47` (20_code) | `valida_vista_sql` riscritta: legge il BB, ammette le partizionate; per chi non è il proprietario, al cambio di vista o di schema e all'accensione rifiuta se una colonna accesa `VISTA` resta orfana, e le nomina (Q35) | U27, Q35 |
| `-48` (20_code) | Il guard delle dichiarazioni di `lista_definizione`: una funzione sola per `multi_emittente`, `perimetro_emittente` e la dichiarazione di Q47, ciascuna col valore ammesso senza permesso; il messaggio nomina la colonna | U23 |
| `-49` (20_code) | `fn_lista_colonne_livello`: con la veste NULL, per ogni colonna il livello più restrittivo fra le vesti utilizzabili dell'utente; senza vesti, i livelli di ripiego | U29 |
| `-50` (20_code o 90_end) | Il presidio di Q32: la funzione che confronta le colonne `VISTA` di ogni lista accesa con la sua relazione, col BB; la riga in `presidi.csv` e i testi | U27, Q32 |
| `-51` (90_end) | Il motore ATTIVO ritira il block su `lista_definizione` e il require su `lista_colonna` e `lista_preset` (le due eccezioni nuove) | U22 |
| `-52` (90_end) | Il runner dei lucchetti su `ui`: `lista_definizione.codice` e `lista_colonna.codice` | U23 |

CSV: `automazione_attivo_eccezioni.csv` (`ui.lista_colonna.lista_id`, `ui.lista_preset.lista_id`, col motivo di Q13);
`automation_lock_columns.csv` (le due righe del codice); `lista_definizione.csv` con la dichiarazione di Q47 sulle sei
liste documentali e `lista_colonna.csv` con `origine_campo = LINEAGE` sulle sei colonne `transito`, coi loro loader; il
registro del seed con le due colonne nuove fra quelle del software (come `multi_emittente` e `campo_sorgente`, QU4);
codici e messaggi: le colonne orfane alla riaccensione o al cambio di vista, i due codici immutabili, il testo di
`E_UI_COLONNA_IN_USO` che nomina i preset e non i permessi (U30, Q18), il testo di
`E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` che nomina la colonna. pgTAP nuovo `ui/test-ui-catalogo-liste-v1` coi presidi
di U22-U30 (soggetti costruiti nel test); adeguati `test-lista-colonna-campo-sorgente-in-vista-v1` (legge il BB e il
marcatore) e il test 7 dei `test-lista-*-seed` (la lineage dal marcatore, non dal nome).

**Garanzie ritirate** (AGENTS.md, «Una garanzia ritirata si censisce in tutti i lettori»).

| Oggetto | Proprietà che i lettori davano per scontata | Lettori DB | Esito |
| --- | --- | --- | --- |
| `ui.lista_colonna.attivo`, `ui.lista_preset.attivo` | «Una colonna accesa, un preset acceso, stanno su una lista accesa» | `fn_resolve_lista_config`, `fn_ordinamento_lista`, `fn_lista_colonne_ricerca_full` | Non ne dipendono: entrano dalla lista per codice (`fn_lista_da_codice`), che rifiuta la lista spenta |
| | | `fn_lista_colonne_livello`, `fn_preset_di_base` | Non ne dipendono: ricevono l'id della lista dai tre sopra |
| | | `fn_check_forma_configurazione`, `trgfn_ui_lista_preset_guard_ordinamento` | Non ne dipendono: chiedono che il codice sia una colonna della lista, in qualsiasi stato (Q42) |
| | | `trgfn_preset_contenuto_aggiornato`, `trgfn_preset_riga_*`, `trgfn_preferenza_preset_base_snapshot` | Non ne dipendono: leggono il preset per id, per la data e l'impronta, non per servirlo |
| | | `dbops.vw_liste_multi_emittente_non_certificate` | Non ne dipende: espone `lista_attiva` accanto alle colonne |
| | | `vendite.fn_list_lotto_task_runs` | Non ne dipende: cita `lista_colonna` solo in un commento |

Richiesta al team BE/FE (nuova, BE27): **«censisci i lettori di `ui.lista_colonna.attivo` e `ui.lista_preset.attivo`
che contano su “la lista è accesa”»**. Già noti: le pagine admin di colonne e preset (`lista_colonna_admin_service.py`,
`ui_admin_repository.py`), che con BE15 smettono di trattare lo spegnimento come rifiutato. Il censimento si fa
all'arrivo del giro (`/arrivi-db`), prima di cominciare.

**Le ricadute BE/FE del giro 4** (⏳ da ora, giro applicato il 2026-11-21), con l'elenco dei file noti; il team BE censisce anche quelli che non
conosco (AGENTS.md, «richiesta BE: percorso intero»):

* **BE12** (§6), esteso: `codice` della lista e della colonna fuori dai campi modificabili, coi codici nuovi
  `E_UI_LISTA_CODICE_IMMUTABILE` ed `E_UI_COLONNA_CODICE_IMMUTABILE`; **`perimetro_emittente` non è più scrivibile
  dall'app** (oggi lo è: se la pagina admin lo espone, esce); `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` è ritirato
  (`obsoleto_dal` 2026-11-21) e al suo posto arriva `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE`, che nomina la colonna
  (mappa d'errore e `docs/it/backend/ui/manual/api_ui_admin_personalizzazioni.md:647`); `E_UI_LISTA_COLONNE_ORFANE`
  dal salvataggio di una definizione (cambio di vista o riaccensione) e `E_UI_LINEAGE_NON_DICHIARATA` da quello di
  una colonna.
* **BE13** (§6), esteso: in `_CHECK_CONSTRAINTS` esce `chk_ui_lista_colonna_azione_non_esportabile` ed entrano
  `chk_ui_lista_colonna_azione_senza_campo`, `chk_ui_lista_colonna_senza_campo_non_esportabile`,
  `chk_ui_lista_colonna_lineage_solo_mostrata` e i cinque `chk_lista_definizione_*_non_vuot*`. Nel drawer delle colonne
  «Esportabile» spento quando manca il campo sorgente (come già per le azioni).
* **BE14** (§6), esteso: **chi decide che una colonna legge la lineage legge `origine_campo`**, non più «il nome non
  sta nella vista ma sta in `vendite.vw_documento_lineage_sintesi_colonne`» (la regola che il DB ha appena ritirato,
  Q15); e la sintesi si chiede solo per le liste con `legge_lineage`. Con il CHECK della lineage la ricerca libera non
  riceve più colonne `LINEAGE` dal DB: il BE verifica se `_helpers.py:315-330` ne aggiunge per altra strada.
  `origine_campo` è nuovo anche nella pagina admin delle colonne (lettura, e scrittura se il drawer lo espone).
* **BE15** (§6): il toggle «attivo» di una definizione con figli accesi non fallisce più; il ramo che intercetta
  `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le liste si ritira.
* **BE27** qui sopra: il censimento dei lettori di `attivo` che contano su «la lista è accesa». ✅ **Fatto (BE, 2026-11-22): nessuno ne
  dipende.** Il catalogo di una lista per la lettura e l'export (`ui_repository.py`, la query delle colonne) filtra
  `ld.attivo` della lista stessa; `list_colonne_by_lista` (l'aiuto alla composizione dei preset) passa da
  `get_definizione`, che chiede la lista accesa; `fetch_flag_perimetro` filtra la lista accesa; le pagine admin di
  colonne e preset mostrano il loro `attivo` accanto a quello della lista, e non ne deducono niente. Nel FE nessuno
  legge `attivo` di colonne o preset per dire che la lista è accesa.
* Il testo di `E_UI_COLONNA_IN_USO` ora dice «preferenze utente o preset» (Q18): se il BE lo ricompone a mano, si
  allinea.

Un `INSERT` del BE in `ui.lista_definizione` che non nomina le tre dichiarazioni passa come prima (nasce coi valori che
non promettono niente).

✅ **Scritto e provato** (sessione DB, 2026-11-21, dopo Q47 (a) e Q48 (a), §7.1). I dieci changeSet della tabella sopra,
numeri `20261120-43` … `-52` come previsti; i CSV (codici e messaggi: cinque codici nuovi con i messaggi 1524-1528,
`E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` ritirato, i testi di 428, 429 e 744; due eccezioni ATTIVO; due lucchetti; le
righe 3 e 4 del registro del seed con `legge_lineage` e `origine_campo` fra le colonne del software; `legge_lineage` sulle
sei liste documentali e `origine_campo = LINEAGE` sulle sei colonne «transito», coi tre loader; il presidio in
`presidi.csv` e `presidi_testi.csv`). Il guard delle dichiarazioni ha un nome nuovo,
`ui.trgfn_lista_definizione_guard_dichiarazioni`: il vecchio si toglie con il suo trigger, e il COMMENT di
`script.fn_is_proprietario_tabella`, che lo nominava, si riscrive al presente. Pagine `manual/`: `lista_definizione`,
`lista_colonna`, `lista_preset`, `lista_colonna_permesso`, `fn_lista_colonne_livello`, `fn_lista_colonne_ricerca_full`,
`fn_veste_corrente`, `dashboard_definizione`, `widget`, i due guard del catalogo, quella del guard rinominato (spostata),
e due nuove (`fn_lista_relazione_ha_attributo`, `dbops/manual/vw_liste_colonne_campo_orfano`); fuori da `ui`
`automazione_attivo_eccezioni`, `fn_is_proprietario_tabella`, `vw_documento_lineage_sintesi_colonne`; la guida
`configurazione-liste` (§2.1, §5.1.1, §5.2, §5.2.2, §10.4, §11.3, §11.4, §11.6).

⚠️ **Corretto scrivendo, U37** (controesempio: il caso 8 di `ui/test-fn-lista-colonne-ricerca-full-v1`). Il ramo
`campo_sorgente = ''` del guard delle colonne **non era morto**: il guard è un `BEFORE ROW` e parla prima dei CHECK.
Tolto, una stringa vuota riceveva «campo non trovato nella vista» invece di `chk_lista_colonna_campo_sorgente_non_vuoto`,
il vincolo che dice la cosa giusta e che il BE mappa sul campo. Il ramo resta, con la ragione giusta («lascia parlare il
vincolo», anche per la stringa di soli spazi); si toglie solo il commento stantio sul seed CSV. La scheda U37 (§3.6) era
sbagliata nella premessa.

**La prova** (`prova_changeset.py`, sullo scratch, owner). L'estratto `-43` … `-50` gira intero; per provare anche
`-51` e `-52` un YAML di prova nello scratchpad simula i CSV (registri, codici, le dichiarazioni del seed, il presidio):
non prova i loader, prova il resto. Pgtap nuovo `ui/test-ui-catalogo-liste-v1` (28 casi): 22 verdi. I sei rossi (9, 10,
17, 18, 20, 23) sono i casi in cui il guard **esenta il proprietario**: la prova gira da owner, e la differenza si vede
solo col runner (il test gira come applicazione, come chiede il suo header; il 23 dipende dal 17). Il presidio è a zero
sul catalogo con il seed simulato. Regressione su tutti i pgTAP di `ui` e sui vicini fuori schema (35 file), senza e con
l'estratto: verdi, salvo cinque già spiegati.

* `test-lista-definizione-perimetro-emittente-v1` e `test-ui-legami-preset-v1`: si fermano uguali **senza** l'estratto
  (owner, il seed non lascia cancellare una riga nata dal seed; già visto nei giri 2b e 3).
* `test-seed-primo-impianto-ui-installazione-v1`, caso 3: il registro del seed non è ricaricato nella prova (lo stesso
  caso di `uso_misura` nel giro 3); al migrate lo riallinea il giro delle automazioni.
* `test-catalogo-presidi-v1`, caso 2: la riga del presidio arriva dal CSV; con la riga simulata è verde (provato a parte,
  insieme a `test-presidi-testi-v1`).

Adeguati, con la ragione sopra la riga: `test-ui-nell-ambito-v1` (le due FK passano fra le eccezioni: tre guard, diciotto
eccezioni), `test-fn-is-proprietario-tabella-v1` (il guard rinominato e il codice nuovo),
`test-lista-definizione-perimetro-emittente-v1` (la lista di prova nasce col perimetro di default: `false` ora lo
rifiuta il guard), `test-lista-colonna-testi-non-vuoti-v1` e `test-fn-lista-colonne-ricerca-full-v1` (le fixture
costruivano colonne composte esportabili, che U25 rifiuta; la prima ora scrive su una lista senza vista, perché sul campo
vuoto parli il vincolo), `test-lista-colonna-campo-sorgente-in-vista-v1` e il test 7 dei quattro `test-lista-*-seed` (il
BB e il marcatore al posto della lineage per nome).

✅ Applicato su dbdev, pgTAP verdi (Tid, 2026-11-21): `ui`, più `script/test-fn-is-proprietario-tabella-v1`,
`dbops/test-catalogo-presidi-v1`, `dbops/test-presidi-testi-v1`; verdi col runner anche i sei casi del proprietario
esentato di `test-ui-catalogo-liste-v1` (9, 10, 17, 18, 20, 23), che la prova da owner non poteva vedere. ⏳ Restano il
commit, il `/verifica-db` del giro e la doc auto-generata da rigenerare (le schede del BB, del
guard rinominato, del presidio e dell'enum nascono lì; la scheda della funzione ritirata va tolta).
✅ Committato con la doc auto-generata (`2959cc7396`); ✅ il `/verifica-db` (sotto).

**La verifica (`/verifica-db 2959cc7396`, sessione DB, 2026-11-22).** Il commit è applicato e pushato. Nei dieci
changeSet nessun difetto: meccanica, §11.4 (le preCondition sui CSV stanno in 90_end), §11.5, le proprietà ripetute
di `-49`, l'`UPDATE OF` del guard del campo con `origine_campo`, il guard ritirato che non lascia funzioni, trigger né
COMMENT, e `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` obsoleto, con i residui solo lato BE (BE12). Puliti anche i CSV
(`lista_colonna` 25 campi per riga, 6 `LINEAGE`; `legge_lineage` sulle liste 4-9), il presidio iscritto e
`security_invoker`. I COMMENT di `multi_emittente` e `perimetro_emittente` che nominavano il guard ritirato li ha già
riscritti `20261121-34`. Trovato e corretto:
* **Il presidio `dbops.vw_liste_colonne_campo_orfano` aveva un solo ramo su quattro costruito**, `CAMPO_ASSENTE`. Con
  Q48 (a) è l'unica verifica del nome di una colonna LINEAGE, e nessun test lo provava. Aggiunti a
  `ui/test-ui-catalogo-liste-v1` il caso 29 (la relazione tolta con un DDL: `RELAZIONE_ASSENTE`, senza le sue colonne)
  e il caso 30 (una colonna LINEAGE su un nome inventato: `LINEAGE_SCONOSCIUTA`, con lo `skip` dei casi 7-8).
  `LINEAGE_NON_DICHIARATA` resta senza caso, perché come applicazione il guard la rifiuta prima (caso 6): lo dice la
  pagina `manual/` del presidio.
* **U28 provava due CHECK dei testi vuoti su dodici.** Aggiunti un caso per CHECK, riconosciuto per nome: i casi 31-34
  di `ui/test-ui-catalogo-liste-v1` (codice, descrizione, `schema_dati` e note della lista; plan 34) e i casi 22-26 di
  `ui/test-ui-catalogo-dashboard-v1` (codice, chiave i18n e chiave del contatore del widget, codice e note della
  dashboard; plan 26).
* **Regola del 2**: il test 7 dei quattro `test-lista-*-seed` faceva la domanda «la relazione ha il campo?» con
  `information_schema.columns` e il nome della vista scritto a mano. Ora la fa con `ui.fn_lista_relazione_ha_attributo`
  sulla vista che la lista dichiara.
* **Riferimenti a oggetti ritirati**: la pagina `manual/` di `lista_preset` citava ancora
  `trgfn_child_requires_active_parent` (tolto da `-51`). Le pagine `manual/` di `vw_liste_multi_emittente_non_certificate`
  e di `trgfn_emittente_modi_solo_migrazione`, e la testata del caricatore `80_data/changelog/20260507-06`, nominavano il
  guard ritirato: ora nominano `trgfn_lista_definizione_guard_dichiarazioni`.
Provato sullo scratch: `test-ui-catalogo-liste-v1` 34/34 come applicazione, `test-ui-catalogo-dashboard-v1` 26/26 da
owner, i quattro `test-lista-*-seed` senza rossi. Verdi anche nella corsa di Tid (2026-11-22).

### 3.5 Giro 5 — il catalogo delle dashboard

**U31 (B) — L'app ha la scrittura sulle tabelle che nessun servizio scrive** · area D · Q19.

* **Fatto.** `zeroerp_app` ha DML su `dashboard_definizione`, `dashboard_widget`, `widget`, `dashboard_preset` e
  `dashboard_preset_widget`. Il backend scrive solo `dashboard_preferenza_utente` (verificato: `dashboard_repository.py`
  `:127`, `:164`, `:179`). L'header dei due pgTAP delle dashboard dice «il SELECT-only del ruolo applicativo è corretto»,
  ma il GRANT dice il contrario.
* **Correzione proposta.** Le cinque tabelle nella lista delle tabelle in sola lettura per l'app, come la Q10 di
  `documenti`.
* **Decisione (Q19, Tid, 2026-11-19).** Sì: le cinque tabelle di catalogo in sola lettura per l'app; le preferenze restano
  scrivibili. Una futura pagina admin delle dashboard riapre la scrittura, insieme a sé, sulle sole tabelle che scrive.
* **Presidio.** `throws_ok` 42501 come app.

**U32 (B) — «La home non è mai vuota» non ha presidio** · area D · Q20.

⚠️ Il piano del giro 5 (§3.5-bis, 2026-11-21) ha trovato che il widget senza area né azione è spento per decisione di
Tid del 2026-07-22: la scheda non la citava. → Q50 (§7.1), decisa (a) il 2026-11-21: niente trigger, la regola resta
quella di luglio («nessun vuoto muto», lo stato vuoto lo dice il FE).

* **Fatto.** Il catalogo dichiara che una dashboard ha sempre una card da mostrare, ma nessun vincolo chiede che il
  pool abbia un widget acceso senza area né azione. Fatto datato (dbdev, 2026-11-18): l'unico widget senza area né
  azione è spento.
* **Correzione proposta.** ~~Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un trigger.~~
  Superata da Q31: un constraint trigger differito.
* **Decisione (Q20, Tid, 2026-11-19).** ~~Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un
  trigger: la regola attraversa pool, widget e interruttore, e un trigger bloccherebbe i passaggi intermedi
  legittimi.~~ Superata da Q31.
* **Decisione (Q31, Tid, 2026-11-20).** Lo stesso strumento di U18: un constraint trigger differito. A fine transazione
  ogni dashboard accesa ha nel pool un widget acceso senza area né azione. Il differito ammette i passaggi intermedi, e
  dopo Q19 anche questo catalogo lo scrive solo l'owner, come `misure_pagina`. Il trigger si monta su pool, widget e
  definizione. Nel giro 5, sul seed: accendere o creare il widget senza area né azione, senza il quale il trigger
  rifiuta il commit.

**U33 (C) — Area e azione del widget possono dire due cose** · area D · Q21.

* **Fatto.** `widget.area_id` può essere un'area diversa da quella dell'azione `azione_id`.
* **Correzione proposta.** Se c'è l'azione, l'area è nulla oppure quella dell'azione.
* **Decisione (Q21, Tid, 2026-11-19).** Se c'è l'azione, l'area è nulla oppure quella dell'azione (la versione
  tollerante, non «solo nulla»). Fatto datato, dbdev 2026-11-19: nessuno dei 4 widget ha un'azione.

**U34 (C) — «La dashboard accesa per codice» sta in due posti** · area D.

* **Fatto.** Il passo 0 del resolver e `dashboard_repository.py:66-78`. Le liste hanno il BB `fn_lista_da_codice`.
* **Correzione proposta.** Un BB `ui.fn_dashboard_da_codice`, e il BE lo chiama.

**U35 (C) — `dashboard_preset.emittente_fiscale_id` è `integer`** · area D.

* **Fatto.** `emittenti_fiscali.id` e il gemello `lista_preset.emittente_fiscale_id` sono `bigint`.
* **Correzione proposta.** Allineare il tipo.

**U36 (C) — Le due preferenze non hanno audit** · area D · Q22.

* **Fatto.** `lista_preferenza_utente` e `dashboard_preferenza_utente` non hanno né il trigger d'audit né `user_*`, e
  `data_update` la scrive il BE.
* **Correzione proposta.** Da confermare se è voluto (la preferenza è dell'utente che la scrive). Se sì, lo dice il
  COMMENT; se no, il trigger d'audit.
* **Decisione (Q22, Tid, 2026-11-19).** Voluto: le due preferenze restano senza audit (dato personale, di un solo
  utente, ad alta frequenza) e il COMMENT delle due tabelle lo dichiara. `data_update` la scrive il DB, non il BE: una
  sede sola, come lo snapshot del preset di base (Q1). Ricaduta: il BE smette di scriverla.

**Q49 — La dashboard spenta sospende i suoi preset** · area D · la gemella di Q13, trovata scrivendo il giro 4.

* **Fatto.** `dashboard_preset.dashboard_id` tiene il blocco ATTIVO generato: una dashboard con preset accesi non si
  spegne. Dal giro 4 una lista sì (`lista_colonna.lista_id` e `lista_preset.lista_id` fra le eccezioni, §3.4-bis).
* **Decisione (Q49, Tid, 2026-11-21).** (a): la stessa forma delle liste. La FK entra fra le eccezioni ATTIVO
  (`automazione_attivo_eccezioni.csv`, con la ragione) e il ritiro dei guard passa da `dbops.fn_ritira_attivo_eccezioni()`
  in `90_end`, senza DDL sui trigger generati. La dashboard spenta sospende i preset senza toccarli; riaccesa, tornano.
  Da censire nel piano del giro: chi legge i preset di una dashboard spenta (resolver e pgTAP dell'ambito, come
  `test-ui-nell-ambito-v1` per le liste) e `dashboard_widget.dashboard_id`, se ha lo stesso blocco.

### 3.5-bis Il piano del giro 5 (sessione DB, 2026-11-21)

Struttura e corpi letti da dbdev il 2026-11-21 (`\d`, `pg_get_functiondef`, `pg_depend`), dopo l'apply e il commit del
giro 4 (`2959cc7396`, doc auto-generata rigenerata). Il via di Tid è del 2026-11-21, coi numeri del progressivo
`20261120` dal primo libero (`-53`).

**Che cosa ha trovato la lettura, prima di scrivere.**

* **U32/Q31 revoca una decisione di Tid del 2026-07-22.** Il widget senza area né azione è `home.benvenuto`, ed è
  spento **di proposito**: [brief-db-dashboard-home-rimuovi-benvenuto](../work-done/2026/brief-db-dashboard-home-rimuovi-benvenuto.md)
  (chiuso il 2026-07-22, validato a video da Tid). Il «mai vuota» del [brief della home](../work-done/2026/brief-db-dashboard-home.md)
  §3.bis vuol dire «nessun vuoto muto», e lo tiene il FE con due stati vuoti che dicono il vero («Nessuna card
  attiva…», «Nessuna card disponibile per il tuo profilo»): una card di riempimento lo nascondeva. Il constraint
  trigger di Q31 obbliga a riaccendere quella card, o a crearne un'altra uguale: le schede U32 e Q31 non citavano il
  brief di luglio. → Q50.
* **Q49: `dashboard_widget.dashboard_id` non ha il blocco.** La composizione del pool è già fra le eccezioni ATTIVO
  (2026-11-08). Il blocco della dashboard nasce da una sola FK, `dashboard_preset.dashboard_id`
  (`trg_dashboard_definizione_a10_dashboard_preset_block_deact_upd` e il require gemello sul preset).
* **U35 tocca un trigger generato e una funzione `BEGIN ATOMIC`.** Da `pg_depend` dipendono da
  `dashboard_preset.emittente_fiscale_id`: `ui.fn_preset_di_base` (corpo `BEGIN ATOMIC`), il lucchetto del posto
  `trg_dashboard_preset_a10_lock_columns_upd` (`UPDATE OF`, generato dal runner dei lucchetti in `90_end`), la FK,
  l'indice della FK, l'UNIQUE del posto e il CHECK dell'ambito. L'`ALTER TYPE` non passa finché ci sono i primi due:
  si tolgono (`IF EXISTS`: su un database da zero il lucchetto nasce dopo, in `90_end`), la funzione si ricrea uguale
  e il runner rimonta il lucchetto. Stessa forma del giro 1b (§3.1-ter, «Ordine dentro il giro»).
* **U33 ha uno strumento senza trigger: una FK composita.** `widget (azione_id, area_id) → config.azioni_processo (id,
  area_id)`, `MATCH SIMPLE`: con `area_id` nullo la FK non si controlla, con l'area valorizzata deve essere quella
  dell'azione. È esattamente Q21 («nulla oppure quella dell'azione»), e presidia anche l'altro verso: l'azione non
  cambia area finché un widget la cita con l'area (oggi `azioni_processo.area_id` non ha lucchetto). Chiede un UNIQUE
  `(id, area_id)` su `config.azioni_processo`, superfluo come unicità ma necessario come bersaglio. Le FK composite
  sono la forma già usata dal giro 2b per i legami fra preset e pool.
* **Dopo U31 nessun codice d'errore nuovo per U33.** Il catalogo lo scrive solo l'owner, con un changeSet: la
  violazione la legge chi scrive il seed, come il DELETE di una misura citata (§3.7).
* **U31 rompe tre pgTAP e un test BE che fabbricano dashboard da app.** `test-ui-legami-preset-v1`,
  `test-fn-preset-di-base-v1` e `test-ui-catalogo-liste-v1` (casi 327-333) scrivono `dashboard_definizione`, `widget`
  e `dashboard_widget` senza `pgtap-runner: owner`; i due test del resolver e quelli delle misure e della forma
  dichiarano già l'owner. Lato BE `backend/apps/ui/tests/db/test_audit_ui_dal_trigger_db.py` fabbrica una dashboard
  (il caso gemello di «Ignora», BE7 parte 1b): trovato per nome di file, il contenuto non l'ho letto.
* **U36: `script.trgfn_audit_data_user_generic` non si può riusare.** Scrive anche `user_update`, che le preferenze
  non hanno (Q22). Serve un trigger suo, una funzione sola per le due preferenze, che scrive `data_update` a ogni
  INSERT e UPDATE; il valore che arriva dall'app non conta, come lo snapshot di Q1.
* **U34: il BB ha il modello accanto.** `ui.fn_lista_da_codice` restituisce la riga e rifiuta con
  `E_UI_LISTA_NON_TROVATA`; il gemello rifiuta con `E_UI_DASHBOARD_NON_TROVATA`, il codice che il passo 0 del resolver
  solleva già. La nota del codice (§4.3: «gemello del precedente», senza referente) si riscrive.

**I pezzi** (numeri da `-53`, riverificati con `prossimo_changeset.py` prima di ogni file).

| changeSet | Che cosa | Difetto |
| --- | --- | --- |
| `-53` (00_schema) | U35: `DROP TRIGGER IF EXISTS trg_dashboard_preset_a10_lock_columns_upd`, `DROP FUNCTION IF EXISTS ui.fn_preset_di_base`, `emittente_fiscale_id` a `bigint` | U35 |
| `-54` (20_code) | `ui.fn_preset_di_base` ricreata, corpo identico (dalla doc auto-generata) | U35 |
| `-55` (00_schema) | U33: UNIQUE `uq_azioni_processo_id_area` su `config.azioni_processo (id, area_id)`; FK `fk_ui_widget_azione_della_sua_area` `(azione_id, area_id)`; COMMENT | U33 |
| `-56` (00_schema) | U36: `data_update` delle due preferenze ripiena da `data_insert` dove è NULL, poi `NOT NULL`; i COMMENT di tabella e colonna («senza audit, voluto»: Q22) | U36 |
| `-57` (20_code) | `ui.trgfn_preferenza_data_update()`, montata `BEFORE INSERT OR UPDATE` sulle due preferenze | U36 |
| `-58` (20_code) | Il BB `ui.fn_dashboard_da_codice(p_dashboard_codice)`: la riga se esiste ed è accesa, altrimenti `E_UI_DASHBOARD_NON_TROVATA` | U34 |
| `-59` (20_code) | `ui.fn_resolve_dashboard_config`: il passo 0 chiama il BB; il commento del catalogo grezzo («mai vuota») riscritto secondo Q50 | U34, Q50 |
| `-60` (90_end) | U31: a `zeroerp_app` SELECT soltanto sulle cinque tabelle di catalogo (la forma di `20261115-98`); le altre due sedi sono il loop `ci_apply/20260205-41` (`v_tabelle_sola_lettura_app`, `runOnChange`) e il blocco «POSTURA DICHIARATA» di `scripts/sql/provision_zeroerp.sql` | U31 |
| `-61` (90_end) | Q49: il motore ATTIVO ritira block e require su `dashboard_preset.dashboard_id` (`dbops.fn_ritira_attivo_eccezioni()`, come `-51`) | Q49 |
| `-62` (90_end) | Il runner dei lucchetti su `ui` rimonta il lucchetto del posto tolto da `-53` | U35 |
| (Q50 (b)) | Solo se Q50 decide (b): il constraint trigger differito di U32 su pool, widget e definizione, e `home.benvenuto` acceso nel CSV | U32 |

CSV: `automazione_attivo_eccezioni.csv` (`ui.dashboard_preset.dashboard_id`, con la ragione di Q13 e Q49); la nota di
`E_UI_DASHBOARD_NON_TROVATA` in `codici_errore.csv`; `fk_index_policy.csv` per la FK composita di U33 (l'indice
`ix_ui_widget_azione_id` la copre già in testa). pgTAP nuovo `ui/test-ui-catalogo-dashboard-v1`, coi soggetti costruiti
nel test: U31 (`throws_ok` 42501 come app su ciascuna delle cinque, la preferenza resta scrivibile), U33 (area diversa
da quella dell'azione rifiutata; area nulla ammessa; l'azione non cambia area), U34 (codice spento, assente, NULL),
U35 (il tipo è quello di `emittenti_fiscali.id`; il lucchetto del posto c'è ancora), U36 (`data_update` scritta dal DB
all'INSERT e all'UPDATE, anche se l'app ne manda un'altra), Q49 (dashboard con preset accesi spenta; il resolver la
rifiuta; riaccesa, il preset torna). Adeguati: `test-ui-nell-ambito-v1` (un guard in meno, un'eccezione in più); i tre
pgTAP qui sopra che fabbricano dashboard da app (la fixture del catalogo come owner, il resto come prima); gli header
dei due test del resolver (M13: «il SELECT-only del ruolo applicativo» ora è vero, e lo dice il GRANT). Pagine
`manual/`: le sei tabelle delle dashboard, `fn_resolve_dashboard_config`, `fn_preset_di_base`, il BB nuovo; in
chiusura la guida `configurazione-dashboard` (Q25).

**Garanzie ritirate** (AGENTS.md, «Una garanzia ritirata si censisce in tutti i lettori»).

| Oggetto | Proprietà che i lettori davano per scontata | Lettori DB | Esito |
| --- | --- | --- | --- |
| `ui.dashboard_preset.attivo` | «Un preset acceso sta su una dashboard accesa» | `fn_resolve_dashboard_config` | Non ne dipende: entra dalla dashboard per codice, accesa (passo 0, dal giro il BB) |
| | | `fn_preset_di_base` | Non ne dipende: riceve l'id della dashboard dal resolver |
| | | `trgfn_preset_contenuto_aggiornato`, `trgfn_preset_riga_*`, `trgfn_preferenza_preset_base_snapshot` | Non ne dipendono: leggono il preset per id, per la data e l'impronta |
| | | `trgfn_ui_dashboard_widget_guard_in_uso` | Non ne dipende: chiede se un preset cita il widget, in qualsiasi stato |

Nessuna vista e nessun job di `dbops` leggono le tabelle delle dashboard (cercato nei corpi e nelle viste, 2026-11-21).

**Le ricadute BE/FE del giro 5** (dopo l'apply), con i file noti; il team censisce anche quelli che non conosco:

* **BE17** (§6): `get_dashboard_id` (`dashboard_repository.py:66-78`) chiama `ui.fn_dashboard_da_codice` e, se vuole
  «niente», intercetta `E_UI_DASHBOARD_NON_TROVATA` (la forma di Q23 per le liste).
* **BE21** (§6): l'upsert delle due preferenze smette di passare `data_update` (`ui_repository.py`,
  `dashboard_repository.py:127-179`); un valore passato non conta.
* **BE28** (nuova): **«censisci i lettori di `ui.dashboard_preset.attivo` che contano su “la dashboard è accesa”»**, e
  chi spegne una dashboard intercettando `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`. Con U31 nessuna scrittura delle cinque
  tabelle passa più dall'app (BE19 l'aveva verificato per il codice): il test
  `apps/ui/tests/db/test_audit_ui_dal_trigger_db.py`, che fabbrica una dashboard, la deve fabbricare con un ruolo che
  scrive il catalogo, o usare la `home` del seed.

✅ **Q50 decisa (a)** (Tid, 2026-11-21): la riga «(Q50 (b))» della tabella non si scrive; `-59` riscrive il commento del
catalogo grezzo sulla regola di luglio.

✅ **Scritto e provato** (sessione DB, 2026-11-21). I dieci changeSet della tabella, numeri `20261120-53` … `-62` come
previsti. CSV: la riga Q49 in `automazione_attivo_eccezioni.csv`, la FK composita in `fk_index_policy.csv`
(`SENZA_INDICE`), la nota di `E_UI_DASHBOARD_NON_TROVATA` in `codici_errore.csv` e la sua causa in
`messaggi_errore.csv` (id 555), che ora nominano il BB. Le altre due sedi della porta: il loop
`ci_apply/20260205-41` (`v_tabelle_sola_lettura_app`, con la sua nota in testa) e `scripts/sql/provision_zeroerp.sql`
(il blocco della porta del pannello, accanto a `ui.misure_pagina`). Tre scelte della scrittura che il piano non diceva:

* **`-54` toglie il cast `::bigint`** del ramo delle dashboard di `fn_preset_di_base`: serviva solo ad allineare il tipo
  delle due famiglie nella UNION. Scelta e firma invariate.
* **`-59` riprende la firma da `20261120-30`**, coi suoi `%TYPE`: il corpo viene dal catalogo vivo (uguale alla doc
  auto-generata), ma `pg_get_functiondef` scioglie i `%TYPE` della firma, e `guardrail_forme_changeset.py` lo ha
  fermato (`type-perso`). Il corpo è quello di `-30` salvo il passo 0 e il commento del catalogo grezzo.
* **Il pgTAP nuovo gira da owner**, col motivo: dopo U31 l'applicazione non fabbrica più dashboard, e gli helper
  `fn_pgtap_*` sono INVOKER. La porta la asserisce `has_table_privilege`; il rifiuto come applicazione (42501) lo provano
  i casi 25-26 di `test-ui-catalogo-liste-v1`, che fino al giro 4 provavano i CHECK dei testi vuoti di widget e
  dashboard, spostati nei casi 20-21 del test nuovo.

⚠️ **Corretto scrivendo: tre pgTAP fabbricavano dashboard come applicazione.** `test-ui-legami-preset-v1` e
`test-fn-preset-di-base-v1` passano a `pgtap-runner: owner`, col motivo (nessun loro caso tocca un guard che esenta il
proprietario: lo fanno solo `trgfn_lista_definizione_guard_dichiarazioni` e `valida_vista_sql`, verificato sul corpo
il 2026-11-21); `test-ui-catalogo-liste-v1` cambia i casi 25-26, come sopra. Adeguati anche `test-ui-nell-ambito-v1`
(due guard, diciannove eccezioni) e gli header dei due test del resolver (M13, Q50).

**La prova** (`prova_changeset.py`, sullo scratch, owner; uno YAML di prova nello scratchpad simula la riga Q49 del
CSV delle eccezioni). Estratto eseguito per intero, catalogo identico dopo il ROLLBACK. Il test nuovo
`ui/test-ui-catalogo-dashboard-v1`: senza l'estratto 5 ok / 4 rossi, interrotto; con l'estratto 21/21. Regressione su
tutti i 30 pgTAP di `ui` e su cinque vicini fuori schema (`dbops/test-user-update-not-null-v1`,
`test-codice-maiuscolo-v1`, `test-seed-primo-impianto-postura-v1`, `test-indici-letture-trasversali-v1`,
`config/test-fn-scrivi-profilo-accesso-v1`): stessi esiti senza e con, salvo `test-ui-nell-ambito-v1` (da 9/1 a 10/0)
e il test nuovo. I rossi da owner che restano sono già spiegati: i sei del proprietario esentato e, da ora, i casi
25-26 di `test-ui-catalogo-liste-v1` (il 42501 si vede solo da app); `test-lista-definizione-perimetro-emittente-v1`
si ferma uguale senza e con (owner sullo scratch, una riga nata dal seed non si cancella; da app, sul runner, no).

⚠️ **Corretto dopo il primo giro di Tid (2026-11-22).** `test-ui-legami-preset-v1` si fermava allo stesso modo, e
l'avevo letto come il rosso dello scratch: ma ora il test gira da owner anche sul runner, e il preset di lista che la
fixture scrive nasce dal seed. Il caso 11 lo cancella dalla porta di manutenzione
(`zeroerp.allow_seed_primo_impianto_override`), che è la strada del migratore. Riprovato sullo scratch:
`test-ui-legami-preset-v1` 14/14, `test-fn-preset-di-base-v1` 24/24, `test-ui-catalogo-dashboard-v1` 21/21.

✅ **Giro 5 applicato su dbdev, pgTAP verdi** (Tid, 2026-11-22), col caso 11 corretto. Da qui partono le ricadute BE/FE
(sotto). Resta da rigenerare la doc auto-generata. Presidi statici verdi: COMMENT al presente, DDL su trigger generati, `runOnChange`,
preCondition sul seed, GRANT ai ruoli batch, forme dei changeSet, preambolo dei pgTAP, letterali SQL, timestamp senza
fuso, v1 congelato.

Doc: pagine `manual/` delle sei tabelle delle dashboard, di `lista_preferenza_utente`, `fn_resolve_dashboard_config`
(anche il ⚠️ stantio sulla dimensione del preset, che il CHECK del giro 3 controlla già), `fn_preset_di_base`; due
nuove (`fn_dashboard_da_codice`, `trgfn_preferenza_data_update`); fuori da `ui` `config/manual/azioni_processo` (il
bersaglio della FK composita) e `dbops/manual/automazione_attivo_eccezioni` (la riga Q49 e quella del giro 4 nella
tabella, che mancava). Q25: la guida nuova
[configurazione-dashboard](../../guide/configurazione-dashboard.md), nel menu delle guide dei due `mkdocs*.yml` e
nei «Vedi anche» della guida delle liste.

⏳ Restano l'apply di Tid coi pgTAP (col runner: il test nuovo da owner, i casi 25-26 di
`test-ui-catalogo-liste-v1` da app), il commit, la doc auto-generata da rigenerare (nascono le schede del BB e della
trigger function nuove) e il `/verifica-db` del giro.

**La verifica** (sessione DB, 2026-11-23, `/verifica-db d75ff94dab`). Nei dieci changeSet nessun difetto di codice. Il
corpo di `fn_preset_di_base` in `-54` è quello di `-08` salvo il cast. Le preCondition e l'ordine da zero reggono
(§11.14). Le tre sedi della porta U31 sono allineate: `-60`, il loop `20260205-41`, il provisioning. I CSV sono integri
e la doc auto-generata è rigenerata. Corretto `ui/test-ui-catalogo-dashboard-v1`, che passa da plan 26 a 29:
* i casi 6 e 9 asseriscono il nome della FK composita (`fk_ui_widget_azione_della_sua_area`), non il solo 23503;
* il caso 27 è nuovo, per Q49: un preset nasce acceso sotto una dashboard spenta;
* i casi 28-29 sono nuovi, per U36: `trgfn_preferenza_data_update` anche sulla preferenza di lista, che il test costruisce.

29/0 sullo scratch con `prova_changeset.py`, senza e con l'estratto di `-62`. Corrette anche le pagine `manual/`
`trgfn_preferenza_data_update`, `dashboard_preferenza_utente` e `lista_preferenza_utente`, e la guida
`configurazione-dashboard` (§3 la card tolta dal pool, §6 chi scrive la preferenza). Dicevano che la preferenza la
scrive solo il proprietario, o solo il backend. La riscrive anche il database, quando ritira una voce uscita dal
catalogo (`trgfn_misure_pagina_ritira_dalle_preferenze`, `trgfn_voce_ritira_dalle_preferenze`). ⏳ Il COMMENT ON TABLE
delle due preferenze (`-56`) ha la stessa frase («scritto solo dal suo proprietario»), ma dice già che `data_update` la
scrive il database a ogni scrittura. Da correggere col prossimo changeSet di `ui` (Tid). Nessuna ricaduta BE: nessuna
garanzia è ritirata.

### 3.6 Giro 6 — pulizia

| # | Dove | Fatto | Correzione proposta |
| --- | --- | --- | --- |
| U37 | `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` | ⚠️ **Superata** (§3.4-bis, «Corretto scrivendo, U37»): il ramo non è morto, perché il guard parla prima del CHECK, e resta; si è tolto solo il commento stantio. La scheda di prima: testa ancora `= ''`: è un ramo morto (il CHECK vieta il vuoto), e il commento che lo giustifica col seed CSV è stantio | Si toglie alla prima riscrittura (giro 4) |
| U38 | `fn_lista_colonne_ricerca_full`, guard multi-emittente | Un filtro ripete il CHECK del campo sorgente; l'id utente è ancorato a una colonna di un'altra tabella; una variabile utente non numerica dà un 22P02 grezzo. Il guard multi passa un codice d'area diverso dagli altri (`'ui'` e il nome senza schema) | Filtro tolto, ancora propria; codici d'area allineati. La variabile non numerica (Q35, Tid, 2026-11-20): un codice d'errore dedicato, non il 22P02 |
| U39 | `fn_lista_da_codice`, BE | Due copie di «lista accesa per codice» nel BE (`ui_repository.py:218-226`, `core/db/lista_catalogo_repository.py:64-70`): il BB rifiuta, e quei lettori vogliono «niente» | Q23, deciso da Tid il 2026-11-19: il BE chiama il BB e intercetta `E_UI_LISTA_NON_TROVATA`; nessun BB nuovo |
| U40 | `ui.lista_preset` (seed, `ordinamento_default`), richiesta del team BE (`/verifica` di BE25 (2), 2026-11-22) | Il preset è la sede dell'ordinamento di partenza (Q37 (a)), ma su 31 liste con `lista_codice` il preset di sistema non lo dichiara (seed letto il 2026-11-22): lì vale il default scritto nel repository, l'intestazione resta spenta, e su 13 liste il FE ne tiene una copia per accenderla (`orderBy`/`defaultSortField`) — una seconda sede | Valorizzare `ordinamento_default` (`[{"col": <codice>, "dir": …}]`) dove il default del repository **è** una colonna ordinabile a catalogo, col suo verso (tabella sotto). Dove non lo è (clausole a più criteri, `id` non a catalogo) il preset resta senza: l'intestazione spenta è corretta. ⚠️ Il BB ordina per **una** colonna più lo spareggio: dove il default del repository ha più criteri (segnati ⚠️), il repository tiene i suoi criteri successivi come spareggio (**Q51 (c)**, Tid 2026-11-22; BE30), quindi il preset si dichiara anche lì. Dopo il push, BE29 ritira le copie FE |

**U40, il dettaglio** (mappatura del team BE, 2026-11-22: default letto da view, service e repository; colonna e preset dal seed).
Colonna = il `codice` a catalogo, tutte `ordinabile = t`. ✅ **Riletto dalla sessione DB sui CSV (2026-11-22):** per
ognuna delle 20 liste la colonna c'è in `lista_colonna.csv`, accesa e ordinabile; ogni lista ha un solo preset in
`lista_preset.csv` (l'id è quello della lista), con `ordinamento_default` vuoto. La forma da scrivere è quella già in uso
nel seed (`[{"col":"codice","dir":"asc"}]`).

| Lista | Default del repository | Colonna | Copia FE da ritirare (BE29) |
| --- | --- | --- | --- |
| `anagrafiche.titoli_iva_sfondati` | eccedenza DESC, `id` | `eccedenza` desc | `titoliIvaSfondati.js` |
| `anagrafiche.titolo_iva_movimenti` | `data_movimento` DESC, `id` | `data` desc | — |
| `magazzino.disponibilita` ⚠️ | `articolo_codice`, `articolo_id`, `magazzino_id` ASC | `articolo_codice` asc | `DisponibilitaSearchTable.vue` |
| `magazzino.disponibilita_articoli` ⚠️ | `articolo_codice`, `articolo_id` ASC | `articolo_codice` asc | `DisponibilitaSearchTable.vue` |
| `magazzino.inventari` | `data` DESC, `id` | `data` desc | `documentiInterni.js`, `DocumentiInterniSearchTable.vue` |
| `magazzino.rettifiche` | `data` DESC, `id` | `data` desc | come sopra |
| `magazzino.inventario_piano` ⚠️ | `articolo_codice` ASC + ubicazione, lotto, asset | `articolo_codice` asc | — |
| `magazzino.inventario_righe` | `id` ASC | `id` asc | — |
| `magazzino.rettifica_righe` | `id` ASC | `id` asc | — |
| `magazzino.magazzini` | `codice` ASC, `id` | `codice` asc | `magazzini.js`, `MagazziniSearchTable.vue` |
| `magazzino.ubicazioni` | `codice` ASC, `id` | `codice` asc | `ubicazioni.js` |
| `magazzino.movimenti` | `data_mov` DESC, `id` | `data_mov` desc | `movimenti.js`, `MovimentiSearchTable.vue` |
| `pagamenti.canali_incasso` | `codice` ASC, `id` (nel service) | `codice` asc | `canaliIncasso.js`, `CanaliIncassoSearchTable.vue` |
| `pagamenti.distinta_righe` | `id` DESC | `id` desc | — |
| `vendite.contratto_righe` | `articolo_codice` ASC, chiave di riga | `articolo_codice` asc | — |
| `vendite.offerta_righe` | `articolo_codice` ASC, chiave di riga | `articolo_codice` asc | — |
| `vendite.lotti` | `data_insert` DESC, `id` | `data_insert` desc | `vendite/stores/lotti.js` |
| `vendite.resi` | `data` DESC, `id` | `data` desc | `resi.js`, `ResiSearchTable.vue` |
| `vendite.resi_da_accreditare` ⚠️ | `data` DESC, `reso_id` DESC, `resi_riga_id` ASC | `data` desc | `resiCoda.js`, `ResiCodaTable.vue` |
| `vendite.resi_da_riconsegnare` ⚠️ | come sopra | `data` desc | come sopra |

Restano senza ordinamento a preset, perché il loro default non è una colonna: `anagrafiche.soggetto_titoli_iva`
(validità, a più criteri), `anagrafiche.titolo_iva_ambiti` (`livello` non ordinabile, ordine della gerarchia),
`pagamenti.sistemazioni_fattura` e `vendite.lotto_fatture` (`id` non a catalogo), `vendite.commesse_attivita`
(default nella funzione DB), `vendite.lotto_gruppi`, `vendite.ddt_righe`, `vendite.fattura_righe`,
`vendite.ordine_righe`, `vendite.preventivo_righe`, `vendite.reso_righe` (a più criteri o non a catalogo).

**Q51 ✅ decisa da Tid il 2026-11-22: (c).** Sulle liste segnate ⚠️ il default del repository ha più criteri
(per esempio la disponibilità: articolo, poi magazzino). Il preset sa dire una colonna sola, e il BB ordina per
quella più lo spareggio tecnico: a parità di articolo i magazzini uscirebbero in un altro ordine. Le strade erano
(a) il preset si dichiara e si accetta il nuovo ordine dei pari, (b) quelle liste restano senza preset finché
`sql_order_clause` non ordina per più voci, (c) il repository tiene i suoi criteri successivi come spareggio quando
la colonna del preset è la sua prima. **Vale la (c)**: l'ordine resta quello di oggi, l'intestazione si accende, e
il «da dove parte la lista» ha una sede sola, il preset. Quindi **U40 vale anche per le cinque liste ⚠️**, e il
seed le dichiara come le altre; il lavoro sui repository era del team BE (BE30): ✅ già così nel codice, presidiato il 2026-11-22.

### 3.6-bis Il piano del giro 6 (sessione DB, 2026-11-22)

Il via di Tid è del 2026-11-22, con BE10 dentro il giro. Il giro si divide come l'1 e il 2: **6a**, il codice che il
team BE aspetta (U40, BE10, U38); **6b**, la pulizia dei metadati (§4) e dei pgTAP (§5), che non ha ricadute sul BE se
non BE18. ⚠️ **Numerazione** (Tid, 2026-11-22): il progressivo è `20261121-NN` dal primo libero, `-26`.

**Che cosa ha trovato la lettura, prima di scrivere** (corpi dal vivo, dbdev, 2026-11-22).

* **BE10 è la seconda copia di una regola.** La cascata della misura (preferenza, preset di base, default dell'uso)
  stava solo nel passo 5-ter di `fn_resolve_lista_config`. Una funzione che risponde la sola misura la ricopierebbe: si
  estrae il BB `ui.fn_misura_pagina_risolta` e lo leggono i due (regola del 2).
* **U38, il codice dedicato esiste già.** `E_UI_CHIAMATA_NON_VALIDA` (TECNICO) vuol dire «il contesto di sessione della
  richiesta non è quello di un utente». Oggi lo solleva il BE quando la GUC è vuota o è di un altro utente. Una GUC non
  numerica è lo stesso difetto: si riusa, se ne aggiorna la nota e la causa. Q35 chiedeva un codice al posto del 22P02,
  non un gemello.
* **U38, i codici d'area.** Il guard multi-emittente nominato dalla scheda non c'è più: l'ha sostituito
  `trgfn_lista_definizione_guard_dichiarazioni` nel giro 4, già con `'database'`. Passano invece `'ui'` quattro funzioni
  scritte dopo: `trgfn_ui_lista_preset_guard_ordinamento`, `trgfn_ui_dashboard_widget_guard_in_uso` (giro 2) e, sul solo
  raise del codice di dominio, `trgfn_preset_contenuto_aggiornato` e `trgfn_preferenza_guard_forma`. Le ultime due le ha
  trovate il presidio del giro (caso 16), non la lettura a vista: `'database'` e `'ui'` stavano nella stessa funzione.
* **U40 non chiede un changeSet.** `ordinamento_default` è una colonna dell'installazione nel registro del seed (riga
  5): il CSV la scrive sui preset di seed intatti, e un'installazione che l'ha cambiata tiene la sua. I due preset
  gemelli (offerta e contratto, `vendite/test-righe-gemelle-secondo-giro-v1` caso 29) ricevono lo stesso valore.

**I pezzi del 6a.**

| changeSet | Che cosa | Difetto |
| --- | --- | --- |
| `20261121-26` (20_code) | `ui.fn_misura_pagina_risolta(preferenza, preset, uso)`: misura, standard, origine. `BEGIN ATOMIC` | BE10 |
| `20261121-27` (20_code) | `ui.fn_resolve_lista_config`: il passo 5-ter chiede al BB; il contratto d'uscita non cambia | BE10 |
| `20261121-28` (20_code) | `ui.fn_misura_lista(lista_codice, auth_user_id, emittente_fiscale_id)`: la sola misura, gemella di `fn_ordinamento_lista` | BE10 |
| `20261121-29` (20_code) | `ui.fn_lista_colonne_ricerca_full`: GUC non intera → `E_UI_CHIAMATA_NON_VALIDA`; id utente `integer`; via il filtro che ripeteva il CHECK; COMMENT al presente | U38 |
| `20261121-30` … `-33` (20_code) | L'area `'database'` nei quattro guard sopra | U38 |

CSV: `lista_preset.csv` (U40, i 20 preset della tabella di §3.6); `codici_errore.csv` e `messaggi_errore.csv` (nota e
causa di `E_UI_CHIAMATA_NON_VALIDA`). Pagine `manual/`: due nuove (`fn_misura_pagina_risolta`, `fn_misura_lista`),
`fn_resolve_lista_config`, `fn_lista_colonne_ricerca_full` (le due righe di «che cosa oggi non copre» chiuse); la guida
`configurazione-liste` §2.6. pgTAP nuovo `ui/test-ui-misura-lista-e-contesto-ricerca-v1` (16 casi, gira come app).

**La prova** (`prova_changeset.py`, sullo scratch, `-26` … `-33` in ROLLBACK, 2026-11-22). L'estratto gira intero, il
catalogo resta identico. Il test nuovo è verde 16 su 16. Resta una firma sola per ciascuna delle quattro funzioni. Le
preCondition di `-27` e `-28` risultano «non girerebbe» sullo scratch perché chiedono il BB di `-26`, che al migrate le
precede. La regressione su tutti i pgTAP di `ui`, senza e con l'estratto, dà gli stessi esiti. ⚠️ **Corretto il
2026-11-22 (6c):** qui c'era scritto «30 verdi», ma il conteggio era quello dei file con l'esito uguale nelle due corse, non
dei file verdi. Da owner sullo scratch erano rossi, uguali nelle due corse, anche `test-ui-catalogo-liste-v1` (8),
`test-seed-primo-impianto-ui-installazione-v1` (6), `test-lista-competenza-gruppi-colonna-emittente-v1` (1),
`test-lista-fornitori-seed` (1), `test-misure-pagina-v1` (1) e `test-lista-definizione-multi-emittente-v1` (5): sono i rossi
della veste (girano come app), e la corsa di Tid come app era verde. `test-lista-definizione-perimetro-emittente-v1` si
interrompeva (da owner il seed non lascia cancellare una riga di seed, già visto nel giro 3; corretto nel 6c). Cancelli statici verdi: `comment_al_presente`, `forme_changeset`, `sql_letterali` e
gli altri della CI. Su richiesta di Tid il `%TYPE` è anche nelle firme di `COMMENT ON` e `DROP FUNCTION`, e `p_preset`
del BB è ancorato a `ui.lista_preset.pagina_dimensione`.

✅ **Applicato** su dbdev con i pgTAP di `ui` verdi (Tid, 2026-11-22). Il via al 6b è dello stesso giorno.

**Le ricadute BE/FE del 6a** (dopo l'apply): BE10 (la lettura nuova), BE29 (sbloccato da U40), BE31 (§6). Nessuna
garanzia ritirata. Cambia un codice d'errore: `fn_lista_colonne_ricerca_full` con una GUC non intera dava 22P02 e ora dà
`E_UI_CHIAMATA_NON_VALIDA`.

⚠️ **Visto lavorando, non di questo giro** (2026-11-22): un'altra sessione sta ritoccando
`80_data/changelog/20260802-23-seed-ui-lista-18-drop-colonna-descrizione` (`validCheckSums: ANY`, via l'UPDATE
dell'ordinamento che il guard del giro 2 rifiuta, e che fermava il migrate da zero). È una ricaduta del giro 2. Non è
toccata qui.

### 3.6-ter Il giro 6b, i metadati (sessione DB, 2026-11-22)

Via di Tid del 2026-11-22. La parte pgTAP di §5 passa a un giro 6c (sotto): il censimento l'ha trovata più grande della
pulizia, e due punti chiedono una decisione.

**Che cosa ha trovato la lettura, prima di scrivere** (catalogo di dbdev, 2026-11-22, col 6a applicato).

* **Una fase tardiva riscrive un COMMENT corretto.** `90_end/20260930-11` scrive il COMMENT di
  `ui.lista_preset.pagina_dimensione` col testo di allora (un brief, «NULL = il default PAGINA»). Il giro 3 l'ha
  riscritto in `00_schema` (`20261120-37`), ma su un database da zero `90_end` gira dopo (linee-guida-sql §5d, §11.14):
  in CI il COMMENT era ancora quello vecchio, su dbdev quello nuovo. M1 era chiuso solo su dbdev. Cercate le altre fasi
  tardive: nessun altro COMMENT di `ui` toccato dal giro è riscritto dopo la sua fase (`20_code/20261120-26` e
  `90_end/20261112-30` commentano oggetti che il giro non tocca).
* **Il debito di §4.2, contato sul vivo** (fatto datato, 2026-11-22): 93 colonne di tabella su 144 senza COMMENT, 12
  trigger scritti a mano su 23, sei COMMENT di tabella generici, cinque COMMENT di colonna con brief o sigle, cinque
  COMMENT di funzione con brief, date o l'elenco dei chiamanti di prima.
* **Il precedente di `documenti` decide il perimetro.** COMMENT su tutte le colonne e su ogni trigger scritto a mano;
  sui vincoli, solo su quelli che fanno valere una regola che il nome non dice. I trigger delle automazioni (audit,
  lucchetti, seed, ATTIVO) restano senza, in tutti gli schemi.
* **I registri CSV hanno due regole diverse.** Le note dei codici d'errore si scrivono al presente: finiscono nei
  commenti di `error_policies_generated.py` (`documenti`: 0 note con brief su 36). I motivi delle eccezioni ATTIVO e le
  note dei lucchetti tengono il riferimento alla decisione: è il registro della decisione (`documenti` 5 su 5, `catalogo`
  8 su 8; i lucchetti fuori da `ui`, 40 su 78). Lì si corregge solo ciò che dice il falso.
* **M8 non dice più il falso.** Dopo U7 il preset di un'azienda spenta o di un profilo spento non si applica davvero; è
  sbagliato il perché che il motivo dà («la cascata dei risolutori parte dalla veste corrente»).
* M3, M4, M5, M10, M13 e la parte di M11 sul corpo sono chiusi dai giri 1-5. M6 e M7 erano nei corpi dei due resolver,
  riscritti nei giri 1a e 2.

**I pezzi.**

| changeSet | Che cosa | Voci |
| --- | --- | --- |
| `20261121-34` (00_schema) | COMMENT di tabelle e colonne: tutte le 93 senza, sei di tabella generici, nove di colonna con brief, sigle o una fotografia | §4.1 M9, §4.2, §4.3 |
| `20261121-35` (00_schema) | COMMENT dei vincoli che dicono una regola: ambito dei preset, le tre regole del campo sorgente, la soglia della ricerca, le coppie che reggono i vincoli composti, il default per uso | §4.2 |
| `20261121-36` (20_code) | COMMENT dei dodici trigger scritti a mano e di quattro funzioni (`fn_get_misure_pagina`, `fn_lista_da_codice`, `fn_misura_pagina_ammessa`, `fn_veste_corrente`) | §4.2, §4.3 |
| `20261121-37` (90_end) | Il COMMENT di `pagina_dimensione` dopo `20260930-11`; la FK della misura, il trigger del guard della misura e la sua funzione, nati in `90_end` | §4.1 M1 |

CSV: `codici_errore.csv`, le note di quindici codici `E_UI_*` al presente (via brief, sigle, date, id di messaggio, i
«·»); `messaggi_errore.csv`, la causa di `E_UI_LISTA_NON_TROVATA` (i chiamanti di oggi) e messaggio e soluzione di
`E_UI_CAMPO_SORGENTE_NON_TROVATO` (M12: «relazione» al posto di «view», vale anche in UPDATE, niente query SQL nel rimedio;
i due segnaposto restano nell'ordine); `automazione_attivo_eccezioni.csv`, il perché di M8 sulle cinque righe e il nome di
`ui.fn_preset_di_base` sulle quattro delle preferenze. Presidio: `ui` entra nel perimetro di
`dbops/test-comment-al-presente-v1` (anche nel caso 7, i trigger), e linee-guida-sql §5d lo elenca.

**La prova** (`prova_changeset.py`, sullo scratch, `-34` … `-37` in ROLLBACK, 2026-11-22). L'estratto gira intero, il
catalogo resta identico. `dbops/test-comment-al-presente-v1`: senza l'estratto 6 su 8 (rossi il 2 e il 4, i brief e gli
id di changeSet dei COMMENT di `ui`: il presidio vede il debito), con l'estratto 8 su 8. Dopo l'estratto nessuna colonna
di `ui` e nessun trigger scritto a mano è senza COMMENT, e nessun COMMENT di `ui` porta date, sigle di decisione (Q, U, BE,
DEF, P-) o paragrafi. Il `%TYPE` nelle firme di `COMMENT ON FUNCTION` passa. Cancelli statici verdi.

✅ **Applicato** su dbdev coi pgTAP verdi, compreso `dbops/test-comment-al-presente-v1` (Tid, 2026-11-22). Ricaduta BE: BE18
(rigenerare `error_policies_generated.py` e il ripiego per le note nuove), insieme a BE31. Nessun comportamento cambia.

### 3.6-quater Il giro 6c, i pgTAP: il censimento (sessione DB, 2026-11-22) — Q52 (b), Q53 (a)

Censimento in sola lettura dei pgTAP di `ui` contro §5, fatto il 2026-11-22 dopo i giri 1a-6a (i numeri di riga sono di
quel giorno).

**Iterano su ciò che c'è — ancora aperti.**

| Test | Che cosa | Correzione |
| --- | --- | --- |
| `test-fn-resolve-lista-config.sql`, caso 11 | Il profilo di priorità > 1 preso dal vivo (`WHERE priorita > 1 LIMIT 1`): senza, l'INSERT dà zero righe e il caso passa lo stesso. Misure scritte a mano (10, 50, 100, 25). L'intestazione dice che il file non usa `fn_pgtap_set_contesto_operatore`, e la chiama | Un secondo profilo costruito; misure dal catalogo; intestazione vera |
| `test-fn-resolve-dashboard-config.sql`, caso 10 | Lo stesso profilo dal vivo | Il profilo costruito |
| `test-fn-resolve-lista-config-contatore-colonne-nuove-v1` | La prima lista accesa del seed e un suo campo; due `skip` se manca l'utente | Lista su tabella temporanea, via gli `skip` |
| `test-fn-resolve-lista-config-cascata-per-chiave-v1`, fixture | Tre misure dal catalogo senza `skip()` (con meno di tre misure diventano NULL). L'intestazione dice plan 19, il file 22, e cita un test che non esiste | `skip()` dichiarato; intestazione vera |
| `test-fn-resolve-lista-config-preset-aggiornato-v1`, caso F | Asserisce solo il banner spento, che con la base NULL lo è comunque | Asserire lo snapshot NULL |
| `test-misure-pagina-v1` | La prima lista del seed come fixture; il caso 2 tautologico; il 13 su `max(misura)`; il 12 dipende dal preset del seed | Lista e preset propri |
| `test-lista-colonna-campo-sorgente-in-vista-v1` | Casi 1-2 su tutto il catalogo (verdi su un catalogo vuoto); il 3 sulle liste geografiche del seed; il 5 `skip` se manca `storico.comuni` | `skip` motivato per 1-3; il 5 con una relazione costruita |
| `test-lista-definizione-multi-emittente-v1`, casi 7-8 | La prima lista non certificata del seed | La lista che il file già costruisce |
| `test-lista-definizione-perimetro-emittente-v1`, casi 2-3 | La lista del seed `vendite.famiglie_documento` (senza seed è rosso, non verde, ma il soggetto è il seed) | `skip` motivato, o fra i controlli del seed |
| `test-fn-lista-colonne-ricerca-full-v1`, fixture 2 | La prima lista accesa del seed con un campo vero | Lista su tabella temporanea |

Chiusi dai giri precedenti: l'aggiramento dello z90 (ritirato nel giro 1a), il caso 4 di perimetro-emittente, il motivo
del runner di `test-fn-resolve-dashboard-config` (M13).

⚠️ **`test-lista-definizione-perimetro-emittente-v1` da owner**, il rosso delle regressioni dei giri 3 e 6a. Da owner
l'INSERT della lista di prova nasce come riga di seed; il caso 4 è rosso perché il guard delle dichiarazioni lascia
passare il proprietario. Poi la `DELETE` nuda della riga di prova si ferma su `E_SEED_RIGA_NON_CANCELLABILE` e interrompe il
file. Il commento che spiega il caso 4 («da owner a rifiutare è il CHECK») è superato dal default
`perimetro_emittente = true`. Come app il file è verde: la correzione è il commento e la `DELETE` (spegnere, non
cancellare).

**Casi non costruiti — ancora scoperti** (coperti: la preferenza malformata, ordinamento e filtri su colonne spente o
bloccate, i legami di U14, la data del contenuto scritta a mano, `widget_nuovi` dopo il filtro, la dashboard spenta, la
misura uscita dal catalogo, l'UPDATE di `misura`, il catalogo senza default, `dimensione_max` non valido, lo spegnimento
della lista con figli accesi, la veste NULL con due identità).

* il secondo profilo di ruolo, e lo spareggio fra preset di ruolo;
* il preset d'azienda nella cascata del resolver con l'azienda accesa (c'è solo su `fn_preset_di_base`);
* lo snapshot della dashboard col valore passato dall'app; il cambio di base e snapshot nello stesso UPDATE;
* il preset di base spento: che non diventi base, e `preset_base_cambiato` quando si spegne la base salvata;
* il widget che compare con l'area e l'azione concesse e sparisce senza (oggi si prova solo la FK);
* `fn_lista_colonne_livello` col profilo REPARTO;
* `fn_lista_da_codice(NULL)`;
* la cascata dei permessi alla cancellazione della colonna, e la FK senza azione della composizione (la `DELETE` di una
  colonna o di un widget citati da un preset);
* `chk_ui_lista_colonna_priorita_non_negativa`;
* `valida_vista_sql`: il salto su una lista spenta con una vista che non c'è, il cambio del solo `schema_dati`, la vista
  materializzata.

**Intestazioni con id di changeSet e nomi di brief:** 30 file su 31 (pulito solo
`test-ui-misura-lista-e-contesto-ricerca-v1`), compresi tutti quelli nati nei giri 1-5.

**Le decisioni (Tid, 2026-11-22): Q52 (b), Q53 (a).**

* **Q52 — Le intestazioni dei pgTAP.** §5 le aveva segnate come debito, ma nessuna regola scritta le vieta: la guida dei
  pgTAP non ne parla, i test dei giri 1-5 (e del resto del progetto) portano «Brief:» e «ChangeSet:» in testa come
  rimando. (a) Si tolgono da tutti e 30, come per i COMMENT; (b) restano, e la voce si toglie da §5. Raccomandata **(b)**:
  in un test il rimando dice da dove viene il caso e non finisce in nessuna scheda; il §5d vale per ciò che si legge come
  definizione dell'oggetto. Si correggono solo le intestazioni che dicono il falso (piano, funzione, test citati). ✅ **Deciso da Tid il 2026-11-22: (b).** I rimandi restano; si corregge ciò che è falso.
* **Q53 — Il perimetro del 6c.** (a) Tutto: i dieci test e i casi scoperti; (b) i dieci test, e i casi scoperti in
  un brief nuovo; (c) i dieci test e i casi che toccano un difetto chiuso in questo brief (i preset di ruolo, la base
  spenta, `fn_lista_da_codice(NULL)`, la FK della composizione), il resto nel brief nuovo. Raccomandata **(a)**: è il
  mandato di §5, e i casi scoperti sono regole del modello che oggi nessun test prova. ✅ **Deciso da Tid il 2026-11-22: (a).**


**Il giro 6c, fatto** (sessione DB, 2026-11-22). Nessun changeSet: soli pgTAP. Provati sullo scratch
(`prova_changeset.py`, come veicolo `20261121-36`, già applicato: l'estratto non cambia niente), cioè **da owner**; la
corsa vera è come app, di Tid.

| Test | Che cosa cambia | Da owner, prima → dopo |
| --- | --- | --- |
| `test-lista-definizione-perimetro-emittente-v1` | Casi 1-3 e 6-8 dichiarati controlli del seed; il caso 4 da proprietario è uno `skip` motivato (il guard lascia passare il proprietario); via la `DELETE` della lista di prova, che non serviva (nasce col perimetro) e da proprietario fermava il file; il commento superato riscritto | interrotto → 8 su 8 |
| `test-lista-definizione-multi-emittente-v1` | I casi 7-8 su una lista costruita, che nessun altro caso tocca (prima: la prima lista non certificata del seed) | 4/5 → 4/5 (rossi della veste) |
| `test-fn-lista-colonne-ricerca-full-v1` | La fixture 2 è una lista costruita senza vista (prima: la prima lista del seed con un campo vero); l'intestazione diceva «otto colonne», sono sette | 20 → 20 |
| `test-misure-pagina-v1` | Lista e preset di base costruiti; il caso 2 giudica le proprietà della risposta, non la stessa query rifatta; il 12 vuole lo standard del preset e l'origine `sistema`; il 13 una misura diversa dallo standard | 17/1 → 17/1 (il 16, della veste) |
| `test-fn-resolve-lista-config-contatore-colonne-nuove-v1` | Lista e preset di base costruiti, il grant al profilo costruito, via i due `skip`; il commento che diceva «l'utente non è quello del contesto» riscritto | 5 → 5 |
| `test-fn-resolve-lista-config-cascata-per-chiave-v1` | Con meno di tre misure nel catalogo il file si ferma e dice perché (prima: NULL in silenzio); l'intestazione diceva plan 19 e citava un test che non c'è | 22 → 22 |
| `test-fn-resolve-lista-config-preset-aggiornato-v1` | Il caso F asserisce lo snapshot NULL, non il solo banner spento | 6 → 6 |
| `test-lista-colonna-campo-sorgente-in-vista-v1` | Casi 1-3 dichiarati presidio del catalogo; il caso 5 costruisce l'omonima (una `comuni` temporanea) invece dello `skip` su `storico.comuni` | 6 → 6 |
| `test-fn-resolve-lista-config.sql` | Il caso 11: il PORTALE della veste `CLIENTE_PORTALE` costruito se il catalogo non lo porta, e il caso dice di aver trovato il preset; indice riscritto sulle etichette vere; via la nota falsa «il file non usa `fn_pgtap_set_contesto_operatore`»; le misure scritte a mano dichiarate | 13 → 13 |
| `test-fn-resolve-dashboard-config.sql` | Il caso 10 come il caso 11 qui sopra; l'intestazione rimanda al test che prova il widget visibile col permesso | 12 → 12 |
| ⭐ `test-ui-liste-casi-del-modello-v1` (nuovo, app) | 14 casi: `fn_lista_da_codice(NULL)`; il preset d'azienda accesa nel resolver e come base; base e snapshot nella stessa UPDATE; il preset di base spento e `preset_base_cambiato`; i permessi a cascata e la FK senza azione della composizione (da proprietario `skip`: la colonna sarebbe del seed); la priorità negativa; il guard della vista su una lista spenta, alla riaccensione e al cambio del solo schema; il REPARTO, anche contro il PORTALE della veste | 14 su 14 (7-8 `skip`) |
| ⭐ `test-ui-dashboard-casi-del-modello-v1` (nuovo, owner) | 6 casi: il widget con l'azione concessa e quello senza area né azione (area e azioni costruite); lo snapshot della dashboard col valore passato e al cambio di base; la lista su una vista materializzata | 6 su 6 |

Regressione su tutti i 33 pgTAP di `ui`: esiti uguali con e senza il veicolo; da owner restano i rossi della veste dei
file che girano come app (sopra, §3.6-bis corretto). Cancelli statici verdi (`pgtap_preambolo`, `forme_changeset`).

**Che cosa non si costruisce, e perché.** Lo spareggio fra preset di ruolo: gli indici unici dei binding (uno per
identità, uno per unità organizzativa, uno per veste) danno un profilo solo per livello di priorità, quindi due profili
alla stessa priorità il modello non li ammette. Il resto dei «casi non costruiti» di §5 è coperto (voce per voce in testa
a questa sezione). Le misure scritte a mano di `test-fn-resolve-lista-config.sql` restano: servono quattro misure diverse
e il catalogo ne garantisce due; se una esce dal catalogo il guard ferma la fixture, un rosso e non un verde.

✅ **I pgTAP di `ui` verdi come app**, compresi i due nuovi e i casi 7-8 di `test-ui-liste-casi-del-modello-v1` (Tid,
2026-11-22). Committato su `dev/db-tid` il 2026-11-22. ~~Resta il `/verifica-db` dei giri 1a-6c, in una sessione nuova~~ (✅
sotto), e la chiusura (§10). Nessuna ricaduta BE/FE.

**La verifica (`/verifica-db 53440091fc`, sessione DB, 2026-11-22).** Il commit è applicato su dbdev e sullo scratch,
pushato e in `main`: ogni correzione a un changeSet vuole un changeSet nuovo. Nei dodici changeSet nessun difetto di
corpo. `-27` parte da `-41`, l'ultima versione del resolver, e cambia solo il passo 5-ter. I quattro guard di `-30` …
`-33` cambiano solo l'area, e in `ui` nessuna funzione passa più `'ui'`. La rollback di ognuno riporta il testo di prima.
Puliti anche i COMMENT di `-34` … `-37`. Ogni oggetto commentato in `00_schema` e in `20_code` nasce in un changeSet
precedente della stessa fase. In `90_end` restano solo `20260930-11`, che `-37` corregge dopo, e `20261112-30`, che
commenta vincoli che il giro non tocca. Senza COMMENT restano solo i trigger delle automazioni, e i chiamanti nominati
dai COMMENT tornano col catalogo. Tornano anche i CSV: campi per riga, nessun CRLF, e i 20 preset di U40 su una colonna
accesa e ordinabile con un campo sorgente. Trovato e corretto:
* **La pagina `manual/` del BB della misura diceva il falso** sull'errore: «con una preferenza o un preset nel catalogo,
  un catalogo senza default non ferma la risposta». Il BB calcola sempre lo standard, quindi senza un preset valido
  chiede il default dell'uso anche quando la preferenza è buona. Provato sullo scratch, in una transazione annullata,
  togliendo il default PAGINA: la preferenza nel catalogo senza preset solleva `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`.
  Il comportamento è quello del resolver di prima (`-41`) e del COMMENT: ora la pagina dice quando il default si chiede.
* **BE10 era provato solo con l'emittente NULL**: nessun caso confrontava `ui.fn_misura_lista` col resolver su un preset
  d'azienda. Il caso 2 di `ui/test-ui-liste-casi-del-modello-v1` chiede la misura anche a `fn_misura_lista`, con
  l'emittente passato. Provato con la mutazione (una `fn_misura_lista` che non passa l'emittente a `fn_preset_di_base`):
  rosso il solo caso 2.
* **La vista materializzata era provata solo sul sì**: un guard del campo che saltasse le viste materializzate passava
  il caso 6 di `ui/test-ui-dashboard-casi-del-modello-v1`. Aggiunto il caso 7 (plan 7): una colonna su un campo che la
  vista non ha dà `E_UI_CAMPO_SORGENTE_NON_TROVATO`. Provato con la mutazione (il BB della relazione che risponde «sì»
  per ogni vista materializzata): rosso il solo caso 7. Corretto anche il commento della fixture: la base nuova del caso
  4 è il secondo preset, quello spento, non il primo.
* **Il riepilogo «Che cosa si ritira» dava per ritirato il ramo `= ''` (U37)**, che il giro 4 ha tenuto apposta
  (§3.4-bis, «Corretto scrivendo, U37»). Ora il riepilogo e la scheda di U37 (§3.6) lo dicono.

Ne nasce **Q60** (§7.1), la lettura dell'utente di sessione: fuori da `ui`, e non è un difetto del giro. ✅ Decisa (a) da Tid il 2026-11-22. Una nota di
testo per Tid: la soluzione di `E_UI_CHIAMATA_NON_VALIDA` (`messaggi_errore.csv`) dice che il contesto porta «l'utente
della chiamata», ma quando lo solleva `fn_lista_colonne_ricerca_full` il contesto ha solo il codice della lista e il
valore della GUC. È un seed già applicato: lo si corregge col prossimo giro che tocca il CSV. Provati sullo scratch
`ui/test-ui-dashboard-casi-del-modello-v1` (7 su 7, da owner, il suo runner) e
`ui/test-ui-liste-casi-del-modello-v1` (14 su 14 come app; da owner 14, coi due `skip` dichiarati). ✅ Verdi tutti e due anche nella corsa di Tid (2026-11-22).
**Che cosa si ritira** (riepilogo): `DEFAULT 25` (U15); il secondo trigger z90 (U1); la copia BE della cascata (U2);
`is_default` di liste e dashboard e i due indici `uq_*_default` (Q26, sostituiti dall'UNIQUE parziale di Q30); il diff
del BE sulla composizione del preset, mai scritto (BE3, Q33); la regola di forma della
preferenza nel BE (U12, BE8); il tetto 100 da `_MAX_WIDGET_PAYLOAD` (U21, BE11); le copie dell'8 e il ramo «≤0 = nessun
tetto» nel FE (U21, FE1); `data_update` delle preferenze scritta dal BE (Q22, BE21); la dipendenza del guard di `ui` da
`vendite.vw_documento_lineage_sintesi_colonne` (U26); la copia BE di «dashboard accesa per codice» (U34); le due copie BE
della lista per codice (U39). ~~Il ramo `= ''` (U37)~~: ⚠️ resta, e il giro 4 dice perché (§3.4-bis, «Corretto scrivendo, U37»).

### 3.6-quinquies Il giro 7 (sessione DB, 2026-11-22) — Q57, Q58, Q54 e la regola del 2 applicati, pgTAP verdi

Via di Tid del 2026-11-22 («parti con le modifiche da fare»), dopo le decisioni Q54 (a), Q57 (a) e Q58 (a). Numeri
`20261122-34` e `-35`, dati da Tid (2026-11-22, con un'altra sessione DB attiva sul giornale delle corse). Scritto
nella sessione che ha fatto il `/verifica-db` del giro 6: il `/verifica-db` del giro 7 va fatto in una sessione nuova.

| changeSet | Che cosa | Voce |
| --- | --- | --- |
| `20261122-34` (20_code) | `ui.trgfn_voce_ritira_dalle_preferenze`: nel ramo della dashboard esce ogni codice che il pool non ha più, invece di cercare in `ui.widget` il codice della card ritirata. La card tolta dal pool e cancellata dal catalogo nella stessa istruzione esce dalle preferenze. Il ramo della lista non cambia | Q57 |
| `20261122-35` (20_code) | `ui.fn_get_misure_pagina`: la chiave `default_per_uso`, `{uso: misura}` costruita da `enum_range(NULL::ui.uso_misura_pagina)`, coi default di `ui.fn_misura_pagina_default`. `default_compatta` e `default_pagina` restano finché il BE non passa (BE33), poi le ritira un changeSet. Con lui il COMMENT di `ui.fn_misura_pagina_default`, che nominava fra i chiamanti il resolver: i chiamanti di oggi sono `fn_get_misure_pagina`, `fn_misura_pagina_risolta` e il trigger differito | Q58 |

CSV: `messaggi_errore.csv`, la soluzione di `E_UI_CHIAMATA_NON_VALIDA`. Il contesto dell'evento ha il codice della lista
e l'utente del contesto di sessione, e l'utente della chiamata solo quando lo segnala il backend (il loader è
`runOnChange`). pgTAP: il caso 16 di `ui/test-ui-ritiro-voce-preferenze-v1` (plan 16), cioè la CTE che toglie la card dal
pool e la cancella dal catalogo; il caso 19 di `ui/test-misure-pagina-v1` (plan 19), cioè `default_per_uso` con una chiave
per ogni uso dell'enum, il default del BB, le due chiavi di prima uguali e il corpo che legge l'enum. Pagine `manual/`:
`trgfn_voce_ritira_dalle_preferenze` («Che cosa esce»), `fn_get_misure_pagina` (riscritta; via anche il «⚠️ Che cosa
oggi non copre» sul catalogo senza default, che il trigger differito del giro 3 ha chiuso).

**La prova** (`prova_changeset.py`, sullo scratch, `-34` e `-35` in ROLLBACK, da owner, 2026-11-22). L'estratto gira
intero e il catalogo resta identico. Le preCondition passano. Le rollback riportano i COMMENT vivi, confrontati col
catalogo. `test-ui-ritiro-voce-preferenze-v1`: senza l'estratto 15/1 (rosso il 16: il difetto di Q57 riprodotto), con
l'estratto 16/0. `test-misure-pagina-v1`: senza 17/2 (rossi il 16, rosso da owner per costruzione, e il 19), con 18/1
(il solo 16). Regressione sui 34 pgTAP di `ui` e su `dbops/test-comment-al-presente-v1`: esiti uguali senza e con
l'estratto, tranne i due casi nuovi. Da owner restano i rossi della veste, già noti (§3.6-bis). ⚠️ Il caso 19 non
distingue da solo un oggetto scritto a mano coi due usi di oggi, perché con l'enum di oggi le chiavi sono le stesse: per
questo guarda anche il corpo.

✅ **Applicato** su dbdev coi pgTAP verdi (Tid, 2026-11-22). Letto dopo l'apply: i due changeSet sono nel
`databasechangelog`, `default_per_uso` risponde `{"PAGINA": 25, "COMPATTA": 10}`, e la soluzione nuova di
`E_UI_CHIAMATA_NON_VALIDA` è nella tabella dei messaggi. ⏳ **Restano**: la doc auto-generata da rigenerare (le schede
delle due funzioni e di `fn_misura_pagina_default`); il `/verifica-db` del giro in una sessione nuova; BE33 (§6), ora
sbloccata.
Garanzie ritirate: nessuna. `fn_get_misure_pagina` aggiunge una chiave e non ne toglie; il ritiro della card toglie
dalla preferenza le stesse voci di prima e, in più, quelle di una card uscita anche dal catalogo.

⚠️ **Il piano qui sotto è superato in un punto** (il cambio di firma): vedi «Q54, il giro», dopo il piano.

**Q54, il piano** (deciso (a) da Tid il 2026-11-22, col disegno «una colonna nel registro»; da scrivere in una sessione
DB nuova, con un range di numeri di Tid). Il trigger `a00` di `ui.lista_preset` (e di `ui.dashboard_preset`) è generato
dal registro `dbops.automazione_seed_primo_impianto` e monta `script.trgfn_seed_primo_impianto`, il BB di tutti gli
schemi. Quando il software scrive una riga personalizzata, il BB riporta a OLD ogni colonna dell'installazione cambiata.
Lo fa anche con `composizione_impronta`, che scrive il DB (`ui.trgfn_preset_riga_tocca_preset`) quando il software
toglie una riga della composizione. I pezzi:
* il registro: una colonna nuova, `colonne_derivate text[]` (un sottoinsieme di `colonne_installazione`: il DB le
  deriva da una tabella figlia). Il CSV del registro la valorizza per `lista_preset` e `dashboard_preset`
  (`composizione_impronta`);
* il montaggio: un quarto argomento della forma `COLONNA`, quindi il generatore delle automazioni che scrive `tgargs`
  e `dbops.fn_seed_primo_impianto_argomenti`. Questa cambia `RETURNS TABLE`: è un cambio di firma, con i suoi
  lettori da censire (il BB, le capability e i presidi che leggono gli argomenti del seed);
* il BB: nell'UPDATE del software, le colonne derivate cambiate non si riportano a OLD e non vanno negli scartati;
  nell'UPDATE dell'installazione restano colonne dell'installazione (la loro modifica personalizza, come oggi);
* il seguito: `contenuto_aggiornato_il` (fase `a20`, dopo `a00`) vede l'impronta cambiata e sposta la data della chiave
  `colonne`. Il banner del preset aggiornato si accende al ritiro, non a una scrittura dopo: è il comportamento che Q37
  voleva;
* i pgTAP: il ritiro di una colonna dal preset personalizzato come migratore, poi l'impronta uguale a quella della
  composizione; la riscrittura uguale dell'installazione dopo, che non sposta `colonne`;
* i censimenti: i lettori di `dbops.fn_seed_primo_impianto_argomenti` e di `tgargs` del seed; le altre tabelle del
  registro con colonne derivate (si cercano i trigger che scrivono una colonna dell'installazione della tabella
  padre); la pagina `manual/` di `trgfn_preset_riga_tocca_preset`, che perde il limite dichiarato; la guida
  dell'automazione e il brief del seed archiviato (QU1), che descrivono le forme.

**Q54, il giro** (via di Tid, «procedi q54», 2026-11-22; scritto nella stessa sessione del giro 7, non in una nuova;
numeri `20261122-36` … `-39`, dati da Tid con l'altra sessione DB attiva).

⚠️ **Corretto scrivendo: la firma non cambia.** Il giro della forma FIGLIA (`20261119-02`) aveva già scelto di non
cambiare il `RETURNS TABLE` di `dbops.fn_seed_primo_impianto_argomenti`, perché lo legge
`dbops.fn_seed_colonne_del_software` (`BEGIN ATOMIC`), da cui dipendono le viste della posta. La grammatica valida gli
argomenti, e il trigger li legge da `TG_ARGV`. Q54 fa lo stesso: le derivate sono il quarto argomento della forma
`COLONNA`, validate e non restituite. I lettori di `tgargs` del seed (`fn_seed_colonne_del_software`,
`fn_seed_primo_impianto_divergenze`, il runner) non ne dipendono: il primo legge le colonne del software, gli altri
confrontano o montano l'elenco intero. Nel registro c'è una sola tabella con colonne derivate, `ui.lista_preset`.
`ui.dashboard_preset` non è iscritta al seed: lì il caso non esiste. Fra le colonne dell'installazione di
`lista_preset`, la sola derivata è `composizione_impronta`. `contenuto_aggiornato_il` la sposta il trigger `a20`, dopo
`a00`, che quindi non la vede cambiare.

| changeSet | Che cosa |
| --- | --- |
| `20261122-36` (00_schema/dbops) | `dbops.automazione_seed_primo_impianto.colonne_derivate text[]`, col CHECK `chk_automazione_seed_primo_impianto_derivate` (almeno una, tutte dentro `colonne_installazione`); COMMENT di colonna, vincolo e tabella |
| `20261122-37` (20_code/dbops) | `dbops.fn_seed_primo_impianto_argomenti`: la forma `COLONNA` accetta 3 o 4 argomenti; il quarto non vuoto e dentro le colonne dell'installazione. Firma invariata |
| `20261122-38` (20_code/dbops) | `dbops.fn_seed_primo_impianto_divergenze`: con `colonne_derivate` l'atteso ha il quarto argomento. Il trigger vivo coi tre di prima diverge, e lo RIGENERA la rete di `90_end/20261117-20` a ogni migrate |
| `20261122-39` (20_code/script) | `script.trgfn_seed_primo_impianto`: nell'UPDATE del software le derivate escono dalle colonne da scartare (non tornano da OLD, non vanno in `scartati`) |

CSV: `dbops/automazione_seed_primo_impianto.csv` ha la colonna `colonne_derivate` (`{composizione_impronta}` sulla
riga 5, `NULL` sulle altre), e il caricatore `80_data/changelog/20261117-19` (`runOnChange`, `validCheckSums: ANY`)
la nomina in `columns`. pgTAP: `ui/test-seed-primo-impianto-ui-software-v1` (plan 21). Casi nuovi: 17, dopo il ritiro
del caso 5 l'impronta del preset personalizzato è quella della composizione; 18, l'impronta non è fra gli scartati; 19 e
20, la grammatica col quarto argomento; 21, il controllo del seed sul montaggio, dichiarato tale. Pagine `manual/`:
`automazione_seed_primo_impianto`, `fn_seed_primo_impianto_argomenti`, `script/trgfn_seed_primo_impianto`,
`trgfn_preset_riga_tocca_preset` (via il limite dichiarato). Toccate anche linee-guida-sql §11.7 e la guida
`automazione-db`.

**La prova** (`prova_changeset.py`, sullo scratch, `-36` … `-39` in ROLLBACK, da owner, 2026-11-22). Il CSV del
registro e la rete di `90_end` non sono nell'estratto: li simula uno YAML di prova accodato, che scrive
`colonne_derivate` sulla riga 5 e lancia il runner come la rete. L'estratto gira intero e il catalogo resta identico.
Le preCondition di `-38` e `-39` danno «non girerebbe» sullo scratch perché chiedono la colonna di `-36`, che al
migrate le precede. `test-seed-primo-impianto-ui-software-v1`: senza 16/5 (rossi i cinque nuovi: il 17 è il difetto di
Q54 riprodotto), con 21/0. Regressione su tutti i test del seed (`dbops/test-seed-primo-impianto-*`), su
`config/test-posta-solo-disattivazione-v1`, sui pgTAP di `ui` e su `dbops/test-comment-al-presente-v1`: 37 file con
esiti uguali senza e con l'estratto. Cancelli statici verdi.

⚠️ **Decisa da Tid il 2026-11-22: il BB.** Scritta in «Q54, la regola del 2», più sotto.

**Regola del 2, per Tid.** Il BB legge l'elenco delle derivate da `TG_ARGV[3]` con la stessa espressione con cui la
grammatica legge i tre elenchi (virgole, spazi tolti, voci vuote tolte). È una seconda sede della stessa lettura. La
strada pulita è un BB `dbops.fn_seed_elenco_colonne(text)` letto dai due, ma è un BB nuovo e vuole il tuo ok; il giro non
lo estrae. In alternativa si può cambiare la firma della grammatica, la strada che il giro FIGLIA ha scartato.

✅ **Applicato** su dbdev coi pgTAP verdi (Tid, 2026-11-22). Letto dopo l'apply: `-36` … `-39` sono nel
`databasechangelog`, la riga 5 del registro porta `{composizione_impronta}`, e la rete di `90_end` ha rimontato il
trigger di `ui.lista_preset` col quarto argomento `composizione_impronta`. ⏳ **Restano**: la doc auto-generata di
`dbops` e `script`; il `/verifica-db` del giro in una sessione nuova; la decisione di Tid sulla regola del 2 (sopra). Garanzie ritirate: una, sul solo `ui.lista_preset`. Prima, dopo una scrittura del software
su un preset personalizzato, `composizione_impronta` era quella di prima della scrittura. Ora è quella della
composizione. I lettori lato DB: `ui.trgfn_preset_contenuto_aggiornato` (sposta la data della chiave `colonne`, è il
comportamento voluto da Q37) e il resolver, che confronta la data col snapshot della preferenza (il banner si accende al
ritiro). Nessuno contava sull'impronta vecchia. Nessuna ricaduta BE: il BE non scrive né legge l'impronta.

**Q54, la regola del 2** (applicata, pgTAP verdi, 2026-11-23; decisa da Tid il 2026-11-22: «estrai il BB fn_seed_elenco_colonne»; numeri `20261122-41`
… `-43`, dati da Tid con l'altra sessione DB attiva, che ha il `-40`). La lettura di un elenco del montaggio (spazi
tolti, spezzato sulle virgole, voci vuote tolte) aveva quattro copie: tre nella grammatica (software, installazione,
derivate), una nel trigger (le derivate da `TG_ARGV[3]`). Censite sul catalogo di dbdev (`prosrc ~ 'string_to_array'`
negli schemi applicativi): nessun'altra funzione legge gli elenchi del seed.

| changeSet | Che cosa |
| --- | --- |
| `20261122-41` (20_code/dbops) | `dbops.fn_seed_elenco_colonne(p_elenco text) RETURNS text[]`, `LANGUAGE sql` a stringa (non legge tabelle: niente `BEGIN ATOMIC`, §5c), IMMUTABLE, PARALLEL SAFE. Un elenco `NULL` o vuoto dà `{}`, mai `NULL`. EXECUTE all'app dai default privileges di `dbops` |
| `20261122-42` (20_code/dbops) | `dbops.fn_seed_primo_impianto_argomenti`: le tre letture chiamano il BB. Firma, `RETURNS TABLE` e messaggi invariati |
| `20261122-43` (20_code/script) | `script.trgfn_seed_primo_impianto`: la lettura delle derivate chiama il BB. Il COMMENT resta quello del `-39` |

**Un caso cambia esito, nella grammatica.** Con la lettura di prima un elenco del software o dell'installazione `NULL`
(`ARRAY['COLONNA', NULL, 'b']`) dava un elenco `NULL`, e la grammatica rispondeva `valido = true`: `cardinality(NULL) =
0` non è vero, e nessun ramo rifiutava. Letto su dbdev il 2026-11-22. Col BB l'elenco è vuoto, e la forma lo rifiuta
(«i due elenchi devono essere tutti e due non vuoti»). `TG_ARGV` e `tgargs` non portano `NULL`: il caso arriva solo da
un `p_argomenti` costruito a mano. Nel trigger il comportamento non cambia.

pgTAP nuovo: `dbops/test-fn-seed-elenco-colonne-v1` (plan 8). La lettura (spazi, tab, voci vuote, ordine, `NULL`); la
grammatica che rifiuta i due elenchi `NULL` (5-6) e legge gli elenchi col BB (7); il presidio sul testo (8): la
grammatica e il trigger chiamano il BB e nessuno dei due contiene `string_to_array`. Pagine `manual/`:
`dbops/fn_seed_elenco_colonne` (nuova), `fn_seed_primo_impianto_argomenti` (la lettura, i test, che non citavano i casi
19-20 del giro, e la nota), `script/trgfn_seed_primo_impianto` (la lettura, i casi 17-18 del giro, la nota).

**La prova** (`prova_changeset.py`, sullo scratch, `-41` … `-43` in ROLLBACK, da owner, 2026-11-22). L'estratto gira
intero e il catalogo resta identico. Le preCondition di `-42` e `-43` chiedono il BB di `-41`: sullo scratch danno «non
girerebbe», perché il BB lo crea l'estratto che al migrate le precede. `test-fn-seed-elenco-colonne-v1`: senza
l'estratto si ferma al caso 1 (il BB non c'è), con l'estratto 8/0. Regressione con esiti uguali senza e con:
`ui/test-seed-primo-impianto-ui-software-v1` (21/0), `dbops/test-seed-primo-impianto-software-v1` (27/0),
`dbops/test-seed-primo-impianto-postura-v1`, `config/test-seed-primo-impianto-installazione-v1`,
`ui/test-seed-primo-impianto-ui-installazione-v1`, `config/test-posta-solo-disattivazione-v1` (i loro rossi sono
quelli da owner, uguali prima e dopo), `dbops/test-comment-al-presente-v1` (8/0). Gli attributi della grammatica e del
trigger sono invariati (sicurezza, volatilità, `PARALLEL`, `search_path`, `COST`, `ROWS`, proprietario, grant), e il
BB ha proprietario e grant della grammatica. Cancelli statici verdi.

✅ **Applicato** su dbdev coi pgTAP verdi (Tid, 2026-11-23). ⏳ **Restano**: la doc auto-generata di `dbops` (il
BB, la grammatica) e di `script` (il trigger); il `/verifica-db` insieme al resto del giro 7. Garanzie ritirate: nessuna. La grammatica ne aggiunge una:
un elenco `NULL` non passa più per valido. Lettori lato DB della grammatica: il trigger, `fn_seed_primo_impianto_divergenze`,
`fn_seed_colonne_del_software` e il runner. Tutti passano argomenti letti da un montaggio o composti dal registro, e
non danno mai un elemento `NULL`: per loro non cambia niente. Nessuna ricaduta BE.

**La verifica del giro 7** (sessione DB, 2026-11-23, sul commit `f2e702ac86`). Nessun difetto nei nove changeSet.
* I corpi vivi sono uguali agli YAML, e gli attributi sono quelli dichiarati.
* Nessun numero è doppio. Nell'autogen `-36` precede `-37`, `-38`, `-39`, e `-41` precede `-42` e `-43`: da zero le
  preCondition reggono.
* Il caricatore `80_data/20261117-19` è `runOnChange` e nomina la colonna nuova. Il CSV ha 14 campi su ogni riga.
* L'eccezione delle derivate non apre una strada per scrivere l'impronta da fuori: il lucchetto di
  `ui.trgfn_preset_contenuto_aggiornato` (`a20`, dopo `a00`) accetta solo il valore vero di `ui.fn_preset_impronta`.

Corretti:
* `ui/test-seed-primo-impianto-ui-software-v1` (plan 22). Il caso 22 è il comportamento che Q54 voleva e che nessun
  caso provava: il ritiro del caso 5 sposta la chiave `colonne` della data del contenuto, e il banner si accende al
  ritiro. 22/0 su dbdev, in una transazione chiusa da ROLLBACK. Il caso «la riscrittura uguale dell'installazione
  dopo il ritiro non sposta `colonne`», che il piano prevedeva, non si costruisce in un pgTAP. Il software e
  l'installazione si distinguono da `session_user`, e il test gira come migratore. Il caso 17 prova la premessa:
  dopo il ritiro l'impronta è già vera, quindi non resta niente da spostare.
* La guida `configurazione-iniziale-e-aggiornamenti` (§3, «Le viste salvate e le loro colonne»). Una colonna che il
  programma ritira esce anche dalle viste dell'azienda, e l'avviso si accende subito.

### 3.6-sexies Il giro 8, Q60: l'utente di sessione da una sede sola (sessione DB, 2026-11-23)

**Decisioni di Tid (2026-11-23):** Q60 (a) si fa qui, non in un brief nuovo. Perimetro **1a**: funzioni e viste; le
177 policy RLS restano fuori dal giro e se ne misura dopo la ricaduta (sotto, «Le policy»). `magazzino` **2b**: le sue
funzioni le passa questo giro, **per ultime**, dopo il commit dell'altra sessione DB, che le sta riscrivendo
(brief-db-magazzino-tutte-le-scritture-dal-verbo). Numeri da `20261123-16`, concordati da Tid con l'altra sessione.

**Il difetto.** `app.current_user_id` è l'`auth_user.id` dell'utente della richiesta, scritto dal backend nella
sessione. Le funzioni che lo leggono lo convertono ciascuna per conto suo con
`NULLIF(current_setting('app.current_user_id', true), '')::integer`: un valore che non è un intero dà il 22P02 grezzo
di PostgreSQL, senza codice. Una sola, `ui.fn_lista_colonne_ricerca_full` (giro 6a), ha un controllo suo e solleva
`E_UI_CHIAMATA_NON_VALIDA`. È la stessa lettura ripetuta in decine di sedi, con due risposte allo stesso guasto: la
regola del 2.

**Il building block** (`20261123-16`): `script.fn_utente_di_sessione(p_chi text DEFAULT NULL) RETURNS integer`.

* GUC assente o vuota: NULL. Chi la legge decide che cosa vuol dire «nessun utente», come oggi.
* Valore che non è l'id di un utente (non solo cifre, zeri in testa, zero, oltre il massimo di `integer`):
  `E_SCRIPT_CHIAMATA_NON_VALIDA` (TECNICO, già a catalogo), «Chiamata non valida a `<p_chi>`: app.current_user_id non
  è l'id di un utente.». Il valore sta nel contesto del log.
* `p_chi`: la funzione che legge, per il log e per la frase; senza, il BB stesso.
* plpgsql, STABLE (come la lettura che sostituisce in `ui`: la leggono anche funzioni e viste STABLE), INVOKER, non
  legge tabelle.
* ⚠️ Cambia, rispetto a oggi: `'0'` e un id con zeri in testa, che oggi passano come intero, si rifiutano. Nessun
  utente ha id 0 e il backend scrive l'id col suo `str()`.

**I lettori** (censimento sul catalogo di dbdev, 2026-11-23), un changeSet per schema:

| changeSet | Schema | Che cosa passa al BB |
| --- | --- | --- |
| `-17` | `ui` | `fn_lista_colonne_ricerca_full`: il controllo suo esce; il COMMENT e la nota di `E_UI_CHIAMATA_NON_VALIDA` non la nominano più (il codice resta: lo solleva il backend) |
| `-18` | `script` | `fn_blocca_credenziale`, `fn_sblocca_credenziale`, `fn_elimina_credenziale`, `fn_imposta_totp_obbligatorio`, i quattro `fn_totp_*`, `fn_get_parameter_di_sessione`, `fn_doc_azioni_permesse`, `fn_get_ba_emittente_sr_id`, `trgfn_default_emittente_fiscale`, `trgfn_doc_guard_emittente_ba`, `trgfn_guard_emittente_scope`. I quattro guard (`fn_guard_azione`, `fn_guard_livello`, `fn_guard_super_admin`, `fn_guard_utente_stesso`) ricevono l'utente come argomento e citano la lettura solo nel commento d'uso: non si riscrivono per un commento (§4.3); l'esempio si corregge quando un giro li riscrive, e intanto le linee guida e la pagina `manual/` del BB insegnano la sede giusta |
| `-19` | `anagrafiche` | `fn_id_fiscale_bloccato`, `trgfn_billing_account_guard_admin_globale`, `trgfn_billing_account_link_ef` |
| `-20` | `catalogo` | `fn_articolo_correggi_struttura`, `fn_chiudi_legame_distinta` |
| `-21` | `config` | `fn_pannello_scrivi` |
| `-22` | `dbops` | `fn_accoda_lavoro` e i sette helper pgTAP che leggono l'utente (`fn_pgtap_apri_area_per_nascita`, `fn_pgtap_azienda_di_chi_agisce`, `fn_pgtap_crea_*` ×4, `fn_pgtap_porta_a_stato`, `fn_pgtap_scope_operatore`) |
| `-23` | `pagamenti` | `fn_get_emittente_distinta` |
| `-24` | `vendite` | le 28 funzioni (annulla, cambia stato, cessa, chiudi scaduti, listini, proiezioni, reso, ddt; `fn_listini_attivi_uom_non_convertibili` e `fn_prezzi_legame_oltre_la_fine` col corpo `BEGIN ATOMIC`, trovate dal presidio) e `trgfn_event_log_deriva_scope` |
| `-25` | `vendite` | le quattro viste `vw_dash_*` |
| `-26` | `magazzino` | le 24 funzioni, **per ultime** (2b) |

Il corpo di partenza di ogni funzione si prende dal vivo di dbdev subito prima di scrivere; cambia solo la lettura.
Firma, volatilità, sicurezza e GRANT restano: CREATE OR REPLACE.

**Fuori dal giro, perché non leggono l'utente come id:** `anagrafiche.fn_provisiona_dati_di_sviluppo` e
`dbops.fn_pgtap_articolo_correggi_struttura` salvano e ripristinano il testo della GUC; `script.fn_pgtap_set_contesto_operatore`
la scrive. **Fuori per 1a:** `dbops.fn_storico_arma_scope`, che scrive le policy dello storico: va con le policy.

**Il presidio.** Un pgTAP nuovo, `script/test-fn-utente-di-sessione-v1`: le risposte del BB (assente, vuota, id,
valori rifiutati col codice), e sul catalogo nessuna funzione e nessuna vista che converte `app.current_user_id` da
sé, salvo un elenco chiuso di esenzioni con il motivo (le tre qui sopra e `fn_storico_arma_scope`; `magazzino` finché
non passa il `-26`).

**Le policy (dopo, Tid: «capire cosa comportano»).** 177 policy RLS leggono l'utente con la stessa conversione, quasi
tutte dentro `(SELECT script.fn_get_emittenti_scope_pk_ids(…))`, che il planner valuta una volta per istruzione. Da
misurare prima di decidere: chi le genera (`dbops.fn_storico_arma_scope` per lo storico, i changeSet per le altre),
se una funzione plpgsql al loro posto cambia il piano, e che cosa vede l'utente quando la GUC è sporca (oggi il 22P02
su ogni lettura della tabella).

**Il giro 8b, le policy (via di Tid, 2026-11-23): scritto e provato (sessione DB, 2026-11-23): `20261123-27` … `-36`.**
La misura (dbdev, 2026-11-23): 177 policy in nove schemi (`vendite` 71, `storico` 53, `magazzino` 24, `pratiche` 10,
`anagrafiche` 7, `pagamenti` 6, `documenti` 3, `config` 2, `dbops` 1), 321 letture, tutte nella stessa forma deparsata;
295 vanno a `fn_get_emittenti_scope_pk_ids`. Le 53 di `storico` le scrive `dbops.fn_storico_arma_scope`, le altre
vengono da changeSet a mano.

* `-27`: `dbops.fn_storico_arma_scope` scrive la policy di lettura dello storico con
  `script.fn_utente_di_sessione('<storico.tabella>.<policy>')`: una tabella nuova nasce giusta. Testata ri-ancorata:
  `p_schema_base` e `p_table_base` tornano a `dbops.storico_scope_policy.schema_tabella%TYPE` e `.nome_tabella%TYPE`,
  come alla nascita (`20260911-24`; `20261018-20` li aveva sciolti). Esce dalle esenzioni del presidio.
* `-28` … `-36`, uno per schema in `00_schema/<schema>/`: `ALTER POLICY … USING / WITH CHECK` (nome, comando, ruoli
  invariati), espressioni dal vivo lette con `search_path` vuoto, sola lettura cambiata; chi legge è
  `<schema>.<tabella>.<policy>`. La rollback riporta le espressioni di prima.
* ⚠️ **La misura di prima era sbagliata** («tutte dentro una sottoquery»): in `config.email_log` e
  `config.email_outbox` l'utente era anche un argomento diretto di `fn_scope_email_ambito_perimetro`, valutato per riga
  (4 letture). Lì il BB sta in una sottoquery sua, `( SELECT script.fn_utente_di_sessione(…) )`: una volta per
  istruzione, come le altre.
* Il costo: il BB ~0,0013 ms a chiamata (20.000 in 29,5 ms, ciclo vuoto 2,9 ms, la conversione a mano 7,9 ms; scratch
  come owner, 2026-11-23). Entra nelle economiche misurate di `script/test-policy-funzioni-cost-v1` (non legge
  tabelle, una chiamata per istruzione), che senza diventava rosso.
* I privilegi: il BB ha quelli delle funzioni di perimetro (EXECUTE a PUBLIC compreso): nessun ruolo che legge una
  tabella sotto RLS ne resta fuori.
* Il presidio `script/test-fn-utente-di-sessione-v1` ha il caso 17: nessuna policy converte la GUC da sé, senza
  esenzioni (plan 17).

Prova sullo scratch (`-27` … `-36` in ROLLBACK, da owner): estratto intero, catalogo identico dopo. Il controllo delle
espressioni (pgTAP di prova, fuori dal repo): 177/177; quello del generatore 1/1.
`script/test-fn-utente-di-sessione-v1` senza 15/2 (il 14 nomina il generatore, il 17 le policy), con 17/0.
Invariati senza e con: `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` 6/0,
`script/test-policy-funzioni-cost-v1` 4/0 (con la voce nuova), `rls/test-rls-policies-structure` 28/0,
`rls/test-rls-policies-20260420-structure` 28/0, `storico/test-storico-scope-congelato-v1` 23/0,
`dbops/test-emittente-modi-registro-v1` 16/0, `rls/test-rls-email-outbox-ambito` 3/0,
`rls/test-rls-perimetro-scoperto` 8/0, `rls/test-rls-coda-lavori-perimetro-v1` 15/0, `rls/test-rls-clienti` 13/0;
`rls/test-rls-email-log-ambito` 4/2 e `rls/test-rls-pagamenti-perimetro` 10/9 uguali senza e con (da owner, per
costruzione: vanno letti come app dopo l'apply). `guardrail_forme_changeset.py` e pre-commit verdi, nessun numero
doppio. Documenti: la guida `contratto-guc-app` (§4.1, §4.4, §7.3, §7.5 e l'esempio di policy, che mostrava ancora
`fn_scope_ef_whitelist` per riga), le linee guida SQL §10.4 e l'esempio di §10.3, la pagina `manual/` del BB, gli
esempi delle quattro `fn_scope_ef_whitelist*`. ✅ **Applicato** su dbdev, pgTAP verdi (Tid, 2026-11-23).

**La regola nella documentazione (Tid, 2026-11-23: «va specificato che si usa questa funzione per la connessione»).**
La pagina [parametri-personalizzati-(GUC)](../../postgresql/parametri-personalizzati-(GUC).md), dove si spiegano le GUC
di connessione, dice che l'utente della connessione si legge solo con `script.fn_utente_di_sessione` (funzioni,
trigger, viste, policy), con le tre risposte e il presidio; lo ripetono il contratto GUC (§4.1, §4.4, §7.3, §7.5) e le
linee guida SQL §10.4. Corrette due frasi che insegnavano la lettura a mano: la guida
`architettura-permessi-e-autorizzazioni` («il verbo lo legge da `app.current_user_id`») e la guida
`risorse-umane-e-accessi` («i trigger … usano `current_setting('app.current_user_id')`»).

**La ricaduta sul BE** (BE34, §6): un valore sporco di `app.current_user_id` dà ora `E_SCRIPT_CHIAMATA_NON_VALIDA`
invece del 22P02 grezzo, in tutte le funzioni del giro.

**Documenti:** la pagina `manual/` del BB, le linee guida SQL §10.4 (oggi insegnano `NULLIF(…)::bigint`: rimandano al
BB), le pagine `manual/` dei lettori che descrivono la lettura.

**Scritto e provato (sessione DB, 2026-11-23): `20261123-16` … `-25`.** Come:

* il corpo di ogni lettore dal vivo di dbdev (uguale sullo scratch), con la sola lettura sostituita; firma, RETURNS e
  attributi dall'ultimo changeSet che ha ancora i `%TYPE` (per `fn_get_parameter_di_sessione`,
  `fn_pgtap_crea_mondo_cliente` e `fn_pgtap_crea_preventivo_con_righe` l'ultimo li aveva persi: la firma viene da
  `20261019-05`, `20261021-68`, `20261027-31`); la rollback riporta i corpi di prima;
* ⭐ **il controllo**: un pgTAP di prova (fuori dal repo) che, dopo l'estratto, confronta la definizione viva di ogni
  funzione e vista con quella di prima cambiata solo nella lettura. Ha trovato `COST 5000` di
  `fn_get_ba_emittente_sr_id`, dato da un ALTER successivo e assente dallo YAML della firma: senza, il CREATE OR
  REPLACE l'avrebbe riportato a 100. Corretto; con l'estratto 59 funzioni e 4 viste su 59 e 4;
* le due funzioni `BEGIN ATOMIC` stanno ciascuna da sola nel suo change `sql` (pgjdbc non spezza dopo l'`END`);
* la testata ri-ancorata dove era nuda (linee-guida §5g): i sei `p_auth_user_id` di credenziali e TOTP prendono la
  ragione (`django.auth_user.id`), gli id polimorfi di `fn_doc_azioni_permesse`, `fn_pannello_scrivi` e
  `fn_pgtap_porta_a_stato` la loro, il `RETURNS` di `pagamenti.fn_get_emittente_distinta` si ancora alla colonna della
  variabile che restituisce; nel BB `p_chi` si ancora a `dbops.error_log.function_name`. `guardrail_forme_changeset.py`
  verde sui dieci file (lanciato da sé: il pre-commit lo salta sui file non in staging), e nessun `RETURNS` scalare
  perso rispetto alla storia;
* la lettura di `ui.fn_lista_colonne_ricerca_full` resta dopo il controllo della lista, come prima;
* il presidio ignora i commenti: i quattro guard di `script` citano la lettura solo nell'esempio d'uso, che si corregge
  quando un giro li riscrive (§4.3). Le loro pagine `manual/` mostrano già il BB.

Prova sullo scratch (`prova_changeset.py`, `-16` … `-25` in ROLLBACK, da owner): estratto intero, catalogo identico
dopo; le preCondition contano anche il BB, quindi lì danno uno in meno (il `-16` non è applicato): sul database che le
incontra in ordine passano. pgTAP: `script/test-fn-utente-di-sessione-v1` senza interrotto (il BB non c'è), con 16/0;
`ui/test-ui-misura-lista-e-contesto-ricerca-v1` senza 14/2 (i casi 12 e 13 asseriscono già il codice nuovo), con 16/0.
pre-commit verde sui file del giro.

Documenti scritti: la pagina `manual/` del BB; la guida [contratto-guc-app](../../guide/contratto-guc-app.md) (§4.4 e
§7.5 nuovi; corretto anche il trigger audit, che legge solo `app.jwt_user`, non `app.current_user_id`); le linee guida
SQL §10.4; le pagine `manual/` di `fn_lista_colonne_ricerca_full`, dei tre guard e di `fn_get_uo_id_for_user`; le note
di `E_UI_CHIAMATA_NON_VALIDA` e `E_SCRIPT_CHIAMATA_NON_VALIDA` in `codici_errore.csv`.

✅ **Applicato** su dbdev (`-16` … `-25`, dopo `-01` … `-11` dell'altra sessione), pgTAP verdi (Tid, 2026-11-23).
Verificato sul vivo lo stesso giorno: fuori da `magazzino` leggono la GUC da sé solo le quattro esenzioni del presidio,
il BB lo leggono 60 funzioni, nessuna vista.

**Il `-26`, `magazzino` (2b): scritto e provato (sessione DB, 2026-11-23)**, dopo il commit dell'altra sessione
(`9d0237027a`). Le 24 funzioni che leggono la GUC (le nascite `fn_aggiungi_*`, i verbi comuni dei documenti interni,
le modifiche, i blocchi, le tre poste, `trgfn_ubicazioni_guard_parent`), coi corpi vivi lasciati da quel cantiere. La
testata ri-ancorata: il `RETURNS bigint` di `fn_aggiungi_asset` e `fn_aggiungi_magazzino` diventa
`magazzino.assets.id%TYPE` e `magazzino.magazzini.id%TYPE`, come `fn_aggiungi_lotto`; i `jsonb` di campi e dati e
`p_famiglia` restano tipi espliciti (nessuna colonna di cui siano il riflesso). `guardrail_forme_changeset.py` verde,
nessun `RETURNS` scalare perso rispetto alla storia. Il presidio perde l'esenzione dello schema. Prova sullo scratch:
estratto intero, catalogo identico dopo; il controllo delle definizioni 24/24; `script/test-fn-utente-di-sessione-v1`
senza 15/1 (il 14 nomina le 24), con 16/0. Le pagine `manual/` di `magazzino` non mostrano la lettura. ✅ **Applicato**
su dbdev, pgTAP verdi (Tid, 2026-11-23); sul vivo nessuna funzione di `magazzino` legge più la GUC da sé.

### 3.7 Chiusi senza modifiche (proposti)

| Che cosa | Perché si chiude |
| --- | --- |
| `dashboard_widget` e `dashboard_preset_widget` non hanno la regola «figlio chiede padre acceso» né il blocco dello spegnimento | È voluto: righe di composizione, eccezioni ATTIVO decise il 2026-11-08 |
| Lo spegnimento di un widget, di un'area o di un'azione | Già coperto: un'area o un'azione non si spengono con widget accesi, e il widget chiede area e azione accese |
| ~~L'unicità del preset di default di una dashboard~~ | ~~Garantita da `uq_ui_dashboard_preset_default`~~. Superata da Q26: l'indice è `WHERE is_default`, che si ritira. «Un preset per posto» lo garantisce l'UNIQUE parziale `WHERE attivo` (Q30, 2026-11-20), su liste e dashboard: non è più un caso chiuso, è lavoro del giro 1a |
| Il DELETE di una misura citata da un preset dà il 23503 grezzo | Il catalogo lo scrive solo l'owner, con un changeSet. Q10 (decisa (b), 2026-11-18) riguarda le preferenze, non questo caso |
| `dimensione_max` della dashboard come seconda sede delle misure | Non lo è: è un tetto, non una scelta del paginatore (U21) |
| Un preset di ruolo prevale su un preset di emittente | È l'ordine del resolver e della sua pagina; l'emittente è il ripiego di chi non ha un preset di ruolo. La guida ora lo dice. Chiuso da Tid il 2026-11-19 (Q24-bis) |
| Il super-admin non vede una colonna sensibile senza permesso | Il livello di colonna non ha bypass: una colonna sensibile lo è per tutti. La guida ora lo dichiara |

## 4. I metadati

Nessuno cambia il comportamento: ognuno dice il falso, oppure fa cronaca a chi legge. Si correggono nel giro che apre
l'oggetto, il resto nel giro 6. Il COMMENT si riscrive intero, secondo `linee-guida-sql.md` §5d.

### 4.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `lista_preset.pagina_dimensione` | «NULL = il default», con `DEFAULT 25` (U15); porta il nome del brief |
| M2 | COMMENT `misure_pagina` | «sede UNICA per DB, backend e frontend»: il default ha una copia nel preset (U15) e una nel BE (BE10); porta decisioni datate, brief e il percorso del CSV |
| M3 | COMMENT `misure_pagina.misura` | «Non si riscrive»: niente lo impone (U17) |
| M4 | COMMENT `dashboard_preset.dimensione_max` | «mirror di `lista_preset.pagina_dimensione`»: ha un altro significato e nessun controllo; «Seed preset sistema = 8» è cronaca |
| M5 | COMMENT `lista_preferenza_utente.preset_aggiornato_ignored_at` | Confronta con `data_update`: si confronta con `contenuto_aggiornato_il`; porta «DEF-2» |
| M6 | COMMENT `fn_resolve_lista_config` e suo corpo | «il primo con colonne fra ruolo…» (U3); «AD_HOC prio 1 prevale su REPARTO/PORTALE prio 2»: PORTALE è 3 |
| M7 | COMMENT `fn_resolve_dashboard_config` | «deterministico per priorita» (U4) |
| M8 | Motivi delle eccezioni ATTIVO dei preset d'azienda delle dashboard | «non si applica già»: si applica (U7) |
| M9 | COMMENT `lista_definizione.perimetro_emittente` | «Sette liste globali al 18-09»: una fotografia stantia; porta id di changeSet, due brief e «Piano: …» |
| M10 | COMMENT `lista_colonna.campo_sorgente` | «NULL per azione»: nessun vincolo lo impone (U24) |
| M11 | COMMENT dei due trigger di validazione | `valida_campo_sorgente` tace lo schema e la lineage; `valida_vista_sql` tace lo schema e, nel corpo, dice «view o table», mentre ammette anche le viste materializzate |
| M12 | `config.messaggi_errore` | `E_UI_CAMPO_SORGENTE_NON_TROVATO`: tace la lineage, il rimedio contiene una query SQL, il messaggio dice «prima di inserire» e vale anche per l'UPDATE. `E_UI_COLONNA_IN_USO`: cita i permessi, che vanno a cascata (U30) |
| M13 | Pagine `manual/` e header dei due pgTAP delle dashboard | «il SELECT-only del ruolo applicativo è corretto»: l'app ha il DML (U31) |
| M14 | COMMENT `lista_preset.filtri_default` | «Definirlo prima di seedare i preset»: è un promemoria di cantiere |

### 4.2 Senza COMMENT

* Le colonne di quasi tutte le tredici tabelle: in particolare `id`, le FK, `attivo`, l'audit; `lista_preset` e
  `dashboard_preset` quasi per intero; `lista_preset_colonna` tranne `visibile`; `lista_colonna` tranne una manciata.
* Tutti i CHECK, gli UNIQUE, le FK e gli indici dello schema, compresi `uq_ui_lista_preset_default` e
  `uq_misure_pagina_uso_default`.
* Tutti i trigger dello schema, tranne `trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd`.
* I COMMENT di tabella di `lista_definizione`, `lista_colonna`, `lista_colonna_permesso` sono di una riga, generici e
  senza accenti; quello di `dashboard_definizione` porta «(prima: home)», quello di `dashboard_preferenza_utente` un
  generico «JSONB per resilienza».

### 4.3 Marcatori, nomi di brief, id

* **COMMENT di funzione:** tutte e diciannove portano nomi di brief, date o sigle: «P-2b», «Q1», «§11.5», «D-V1», «DEF-2»,
  «DB-A», «rev 2026-11-08 (brief-db-revisione-dbops…)», «estratta il…», «Richiesta del team BE/FE … §n», id di
  changeSet (`trgfn_ui_lista_preset_guard_pagina_dimensione`: «nasce in 90_end/…»).
* **Corpi:** `fn_resolve_lista_config` (DB-3, DB-4, F.2, DEF-2, DB-A, P-2b, «brief §4-ter», «passo 5-ter», cronaca per
  date); `fn_resolve_dashboard_config` («brief §3c», «§3b», «§4.6», «§3d», DEF-2, date); `valida_campo_sorgente`
  («rev 2026-09-27», «rev 2026-10-11 (… D-B2)»); `valida_vista_sql` («rev 2026-09-27»); `ricerca_full` («2026-09-25:
  …»). Si toccano solo nei giri che riscrivono comunque la funzione: non si apre un `CREATE OR REPLACE` per un commento.
* **Colonne e trigger:** `multi_emittente` («P-2a», brief, «Q1 e §7 punto 3»), `ricerca_min_caratteri` (brief),
  `lista_colonna_permesso.profilo_accesso_id` («PermissionResolver», una classe del BE), `widget.codice` («§3d»), il
  trigger multi («P-2b strato 1», «BE-3»).
* **Eccezioni ATTIVO** delle tabelle di `ui`: «Decisione Tid 2026-11-08, brief-db-revisione-dbops, giro 7-bis blocco c
  (§23.12)».
* **`config.codici_errore`:** `E_UI_LISTA_NON_TROVATA` («messaggi_errore.csv id 427», «trigger B1/B2»),
  `E_UI_PREFERENZA_NON_TROVATA` («DEF-2»), `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` («P-4», brief, «ci_apply», e «si
  accende SOLO dal seed»: il guard rifiuta all'app anche lo spegnimento), `E_UI_MISURA_PAGINA_NON_AMMESSA` («il caso del
  28-09», brief), `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` (percorso del CSV, brief), `E_UI_DASHBOARD_NON_TROVATA` («gemello
  del precedente», senza referente, e residui «·»). Senza note: `E_UI_PRESET_NON_TROVATO`, `E_UI_PRESET_VALIDAZIONE`,
  `E_UI_PREFERENZA_VALIDAZIONE`, `E_UI_VISTA_SQL_NON_TROVATA`, `E_UI_CAMPO_SORGENTE_NON_TROVATO`. Le note finiscono nei
  commenti di `error_policies_generated.py`: si correggono nel CSV, e il BE rigenera (BE18).

## 5. I pgTAP

Si scrivono o si correggono nel giro che apre l'oggetto; il resto nel giro 6.

* **Iterano su ciò che c'è** (verdi per sottrazione su un DB da zero, o rossi senza dichiararlo):
  * `test-fn-resolve-lista-config.sql` test 11 e `test-fn-resolve-dashboard-config.sql` test 10 prendono «dal DB reale»
    un profilo di priorità >1: se non c'è, l'INSERT dà zero righe e l'asserzione passa senza aver provato niente.
    `test-fn-resolve-lista-config.sql` scrive a mano 10, 50 e 100; il suo header dice «non usa
    `fn_pgtap_set_contesto_operatore`», e la chiama;
  * `test-fn-resolve-lista-config-contatore-colonne-nuove-v1.sql`: la prima lista accesa e un campo dal seed, con rami
    `skip` se manca l'utente;
  * `test-fn-resolve-lista-config-cascata-per-chiave-v1.sql:56-65`: tre misure dal catalogo, senza `skip()` se non ci
    sono; `:321-325` aggira lo z90 (U1);
  * `test-fn-resolve-lista-config-preset-aggiornato-v1.sql` caso F: prova lo z90 attraverso un banner che, col preset a
    NULL, è comunque spento;
  * `test-misure-pagina-v1.sql`: la prima lista attiva del seed come fixture, il test 2 tautologico, il test 13 su
    `max(misura)`;
  * `test-lista-colonna-campo-sorgente-in-vista-v1.sql` (test 1-3 sul seed, test 5 con `skip` se manca
    `storico.comuni`), `test-lista-definizione-multi-emittente-v1.sql` (la prima lista non certificata del seed),
    `test-lista-definizione-perimetro-emittente-v1.sql` test 2-4, `test-fn-lista-colonne-ricerca-full-v1.sql`
    fixture 2.
* **Casi non costruiti:** il preset di emittente nella cascata; il secondo profilo di ruolo; lo spareggio; lo z90 delle
  dashboard (nessun test) e lo z90 col cambio di preset e lo snapshot insieme; il preset di base spento; la preferenza
  malformata; ordinamento e filtri su colonne spente o bloccate; i legami incrociati di U14; la data del contenuto
  scritta a mano; `widget_nuovi` dopo il filtro; il filtro per azione e il widget visibile col permesso; la dashboard
  spenta; la misura uscita dal catalogo; l'UPDATE di `misura`; il catalogo senza default; i valori non validi di
  `dimensione_max`; `fn_lista_colonne_livello` chiamata direttamente (REPARTO, veste NULL con due identità);
  `fn_lista_da_codice` col codice NULL; la cascata dei permessi alla cancellazione della colonna; i CHECK
  `azione_non_esportabile` e `priorita_non_negativa`; lo spegnimento della lista con figli accesi; la FK NO ACTION della
  composizione; il salto di `valida_vista_sql` sulle liste spente, il cambio del solo `schema_dati`, i relkind `m` e
  `r`.
* **Header con id di changeSet e nomi di brief:** `test-fn-resolve-lista-config.sql`, `…-cascata-per-chiave-v1`,
  `…-contatore-colonne-nuove-v1`, `…-preset-aggiornato-v1`, `test-fn-resolve-dashboard-config.sql` (con un motivo del
  runner falso, M13), `test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql`, `test-ui-nell-ambito-v1`,
  `test-liste-preset-default-v1`, `test-misure-pagina-v1`, `test-lista-colonna-campo-sorgente-in-vista-v1`,
  `test-lista-definizione-multi-emittente-v1`, `test-lista-definizione-perimetro-emittente-v1`,
  `test-lista-ricerca-min-caratteri-v1`, `test-fn-lista-colonne-ricerca-full-v1`, `test-lista-colonna-testi-non-vuoti-v1`.

## 6. Ricadute su BE e FE

Da passare al team quando il giro DB corrispondente è applicato, salvo quelle «subito». ⛔ Questa sessione non tocca
`backend/` né `frontend/`.

I numeri `BEn` restano quelli già citati nelle schede; il lato si legge in testa alla voce: **BE**, **FE**, o
**BE + FE** quando la voce tocca tutti e due. ⚠️ BE25 c'è due volte: «BE25 (1b)», il codice d'errore, e «BE25 (2)»,
l'ordinamento applicato; Q37-Q39 di questa sezione sono «Q37 §6» … «Q39 §6», diverse dalle Q37-Q39 di §7.1 (testata,
2026-11-21). Il numero nuovo è BE26.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | subito | **BE.** `backend/apps/ui/services/lista_preset_admin_service.py:254-257`: il commento dice che dopo la cancellazione di un preset si lavora «sul catalogo grezzo»; vale il preset di base di oggi |
| BE2 | subito | **BE.** `backend/apps/ui/db/dashboard_repository.py:13-15`: il commento cita `fn_resolve_livello_area` e `fn_check_azione_processo`, il resolver usa `fn_get_user_permissions_map` e `fn_get_user_actions_map`. `:38-41` e `services/dashboard_service.py:56-57`: il «Risultato» non elenca `dimensione_max_standard` e `origine` |
| BE3 | ritirata | ~~**BE.** `ui_admin_repository.py:733` (`replace_preset_colonne`): … Va fatto il diff~~. Ritirata il 2026-11-20 (Q33, col mezzo di Q37 (a)): la regola «la data si sposta solo se il contenuto cambia» la tiene il DB dal giro 1b (`trgfn_preset_riga_tocca_preset`, constraint trigger differito, che confronta l'impronta della composizione a fine transazione), e il DELETE + INSERT identico del BE non sposta più niente, purché stia in una transazione sola. Il BE non cambia |
| BE4 | subito | **BE.** U30, Q18 decisa (b) il 2026-11-19: il controllo preventivo della cancellazione di una colonna conta anche i preset (`ui_admin_repository.py:528-543`); il commento «CASCADE» (`lista_colonna_admin_service.py:26`, `:276-279`; `ui_admin_repository.py:509-510`) si corregge |
| BE5 | 1a | **BE.** U2: `fetch_preset_base_snapshot` (`ui_repository.py:32-35`, `:64-145`) si ritira; `lista_preferenza_service.py:91-98` e `dashboard_preferenza_service.py:94-100` leggono `preset_base` dalla risoluzione: `{"id", "ambito", "contenuto_aggiornato_il"}` oppure `null`, e salvano `preset_base.id` in `preset_base_id` ✅ **Fatto (BE, 2026-11-20).** Il BB `fetch_preset_base_snapshot` è ritirato; i due service leggono la base con `preset_base_id_di_oggi(risoluzione)` (`apps/ui/services/_preferenza.py`), dalla stessa risoluzione e con lo stesso emittente della lettura a video. Provato sul DB vero (`test_audit_ui_dal_trigger_db`) |
| BE6 | 1a | **BE.** U1, Q1 decisa (b): l'upsert (`ui_repository.py:346`, `dashboard_repository.py:138`) non scrive più lo snapshot: lo scrive il trigger a ogni scrittura che nomina `preset_base_id` (il salvataggio è il riallineamento), e un valore passato dall'app non conta ✅ **Fatto (BE, 2026-11-20).** I due upsert non nominano più lo snapshot; `preset_base_id` resta nel SET di proposito, perché è la colonna che fa scattare il trigger. Provato sul DB vero: snapshot uguale alla data del contenuto, e riallineato al secondo salvataggio con la stessa base |
| BE7 | 1a, 1b | **BE + FE.** U5, Q3 decisa (b): dal giro 1a i due resolver rispondono `preset_base_cambiato` (boolean): la base salvata non è quella di oggi, e allora `preset_aggiornato` è falso. Il banner propone il riallineamento (salvare con `preset_base.id`): servizio, FE e i18n. Dal giro 1b snapshot e ignorato sono JSONB per chiave (Q29): il BE scrive l'ignorato della chiave che l'utente chiude ✅ **Parte 1a fatta (BE + FE, 2026-11-20)** sulle liste: `useListaConfig` espone `presetBaseCambiato` e `riallineaPresetBase` (risalva la preferenza: il BE ci scrive la base di oggi); `ListaConfigurabile` mostra il banner «base cambiata» con «Riallinea», i18n it/en. Il servizio non cambia. ✅ **Dashboard, gemelle delle liste (decisione di Tid, 2026-11-20).** Prima non avevano nessun banner, nemmeno quello del preset aggiornato (`presetAggiornato` non lo leggeva nessuna vista). Ora `useDashboardConfig` espone anche `presetBaseCambiato` e `riallineaPresetBase`, e `HomeView` mostra i due banner sopra le card (testi `home.*`; «Vedi novità» apre la modale delle card). Il markup è il BB `BannerPreset`, estratto da `ListaConfigurabile` (regola del 2, ok Tid). **Parte 1b, da fare ora: `20261120-02` … `-11` (Q37-Q39, §3.1-ter) applicati su dbdev, pgTAP verdi (Tid, 2026-11-20).** Che cosa cambia nel contratto: (1) `preset_aggiornato_ignored_at` non c'è più sulle due preferenze: «Ignora» è un salvataggio che nomina `preset_base_id` con il valore che ha già (il trigger riallinea lo snapshot), e una scrittura della colonna ritirata fallisce; (2) `preset_base_contenuto_aggiornato_il` delle preferenze, `contenuto_aggiornato_il` dei preset e `preset_base.contenuto_aggiornato_il` dei due resolver sono una mappa `{chiave: data}` (`colonne`, `ordinamento`, `filtri`, `pagina_dimensione`; `widget`, `dimensione_max`), non più un `timestamptz`; (3) chiave additiva `preset_aggiornato_chiavi` (elenco, vuoto se nessuna) nei due resolver: il banner può dire quali parti sono cambiate, e `preset_aggiornato` vale «almeno una»; (4) chi scrive `contenuto_aggiornato_il` o `composizione_impronta` di un preset riceve `E_UI_PRESET_CONTENUTO_DERIVATO` (BE25); (5) la composizione si confronta a fine transazione: il DELETE + INSERT di `replace_preset_colonne` resta corretto se sta in una transazione sola. **Il percorso da censire, elenco chiuso:** l'endpoint «ignora» (`POST …/preferenza/ignore-preset-update/` e il gemello delle dashboard, se c'è) e il suo repository, che oggi scrivono l'ignorato; ogni lettore delle tre colonne e di `preset_base.contenuto_aggiornato_il` che conta su un `timestamptz` (serializer, confronti, test Django); le scritture admin del preset che nominano `contenuto_aggiornato_il`; il FE che legge `presetAggiornato` (liste e `HomeView`), che può mostrare le parti cambiate da `preset_aggiornato_chiavi`; le pagine `docs/it/backend/ui/manual/api_ui_liste.md` e `api_ui_dashboard.md`, che descrivono l'ignorato ✅ **Parte 1b fatta (BE + FE, 2026-11-21).** «Ignora» resta un endpoint (decisione di Tid: contratto FE invariato, la nota di `E_UI_PREFERENZA_NON_TROVATA` resta vera): `UiRepository` e `DashboardRepository.riallinea_snapshot_base` (era `set_preset_aggiornato_ignored`, che scriveva la colonna ritirata: su dbdev era un 500 su liste e dashboard) riscrivono `preset_base_id = preset_base_id`, e il trigger riallinea lo snapshot; la base resta quella salvata. I due `get_preferenza` leggono lo snapshot con `jsonb_out` (arrivava come testo). FE: `useListaConfig` e `useDashboardConfig` espongono `presetAggiornatoChiavi`, e il BB `BannerPreset` dice le parti cambiate sotto il messaggio (prop `chiavi`, etichette `common.banner_preset.parte.<chiave>` it/en, una chiave senza etichetta col suo codice). Lettori censiti: nessuno confronta `preset_base.contenuto_aggiornato_il` (il BE salva solo l'id); le scritture admin del preset non nominano la data; l'unico lettore del `timestamptz` era il test di audit sul DB vero, riscritto sulla mappa per chiave (`test_audit_ui_dal_trigger_db`, 9 test, fra cui `test_ignora_riallinea_lo_snapshot`: banner acceso con `["pagina_dimensione"]`, spento dopo «Ignora»; e il gemello `test_ignora_riallinea_lo_snapshot_della_dashboard`, su una dashboard fabbricata, aggiunto dalla revisione del 2026-11-21: l'UPDATE della dashboard è un punto suo, e i mock del service non lo vedono). Le etichette delle parti stanno sotto `common.banner_preset` (la revisione le ha tolte da una radice nuova in cima, contro §7 di `i18n-namespace-radici.md`). Pagine `api_ui_liste.md` e `api_ui_dashboard.md` riscritte. Verde: `apps.ui.tests` col DB vero (219), `apps.core.tests.services` (952), vitest (1250) |
| BE8 | 2 | **BE.** U12: `lista_preferenza_service.py:188-231` e `dashboard_preferenza_service.py:161-253`: con Q6 la regola di forma sta nel guard DB, e la copia del BE si ritira nello stesso cantiere (regola del 2); il codice del guard nuovo va in policy e fallback ✅ **Fatto (BE + FE, 2026-11-22).** I due service passano il corpo com'è: whitelist, voci, tipi e codici doppi li giudica `ui.trgfn_preferenza_guard_forma` (`400 E_UI_CONFIGURAZIONE_FORMA`, già in policy e ripiego con BE26). Del BE resta la regola dell'API, nel BB `richiedi_preferenza_non_vuota` (`_preferenza.py`): un oggetto con almeno una chiave, `400 E_UI_PREFERENZA_VALIDAZIONE`. La chiave a `null` la toglie il FE (decisione di Tid, 2026-11-22): `_extractColonna` di `useListaConfig.js` e `_extractWidget` di `useDashboardConfig.js` non la mandano (le chiavi di radice a null le scartava già `chiaviScelte`). Test: sul DB vero `apps/ui/tests/db/test_forma_preferenza_db.py` (dal service, 14 forme sbagliate di lista e 10 di dashboard, fra cui la `larghezza` a null e la stringa `"120"`: tutte `400 E_UI_CONFIGURAZIONE_FORMA`; più il controllo positivo); unitari dei due service (la forma arriva intatta al repository); vitest (la larghezza svuotata e la chiave a null della card non si mandano). Doc: `api_ui_liste.md`, `api_ui_dashboard.md`, catalogo BB alle voci `ListaPreferenzaService.upsert` e `richiedi_preferenza_non_vuota` |
| BE9 | 2 | **FE.** U13: il FE non ripulisce più ordinamento e filtri da sé. Chi applica oggi l'ordinamento risolto alle API di lista lo verifica la sessione BE prima del giro 2 (Q35, 2026-11-20), e risponde qui: la voce diventa la richiesta chiusa, con l'elenco dei file ✅ **Verificato (BE, 2026-11-20): nessuno.** Né l'ordinamento né i filtri risolti arrivano a un'API di lista. **FE:** `ListaConfigurabile` riceve `sortField`/`sortOrder` dal chiamante, e lo store li prende dall'`orderBy` scritto a mano nella sua dichiarazione (`useListaStoreCore.js:187`, `:256`). Più store lo dicono «allineato all'`ordinamento_default` del preset», cioè una copia: `amministrazione/stores/auditLog.js:35`, `pagamenti/stores/rate.js:25`, `catalogo/stores/articoli.js:21-24`, `strumenti/stores/codeJobs.js:55-59` («tre sedi che devono concordare»). `useListaConfig` porta `ordinamento` e `filtri` solo nel payload del salvataggio (`useListaConfig.js:254`), e nessuna modale li tocca (`ListaConfigurabile.vue:773-779` muta colonne e misura). Il FE non ripulisce niente: la parte FE di questa voce è vuota. **BE:** ogni lista ordina col suo default (`parse_list_params(default_order=…)`, il `default=` dei repository); nessun service legge `ordinamento` o `filtri` della risoluzione, che compaiono solo nella whitelist del salvataggio (`lista_preferenza_service.py:41`, `:192-200`). **Conseguenza per il giro 2:** il filtro di U13 nel resolver e la traduzione di BE20 non cambiano niente a video finché nessuno consuma le due chiavi. **Q37 — chi applica ordinamento e filtri risolti.** ✅ **Deciso da Tid il 2026-11-20: (a)**, il lavoro è BE25. (a) Il BE di ogni lista configurabile, quando la richiesta non porta `order_by`: una sede sola, vale anche per l'export, e la risposta dice l'ordinamento applicato perché il FE accenda l'intestazione. (b) Il FE, che parte da `config.ordinamento` col campo sorgente dato dal resolver (BE20). (c) Restano dichiarativi, e la guida lo dice. Con (a) o (b) le copie negli store si ritirano. **Raccomandata (a):** il FE resta presentazione, e l'ordinamento a video e quello dell'export non possono divergere |
| BE10 | 3 | **BE.** `backend/apps/core/api/constants.py:16-19`: `DEFAULT_LIMIT = 25` ricopia il default `PAGINA`, e il suo commento cita una costante del FE ritirata. Q11-bis, deciso da Tid il 2026-11-18: le liste configurabili prendono la misura dal DB; la costante resta solo per gli endpoint fuori catalogo, dichiarata come regola dell'API, e il commento sulla costante FE ritirata si toglie ✅ **Fatto (BE, 2026-11-22).** Il commento di `DEFAULT_LIMIT` (`backend/apps/core/api/constants.py`) la dichiara regola dell'API per gli endpoint fuori catalogo, senza la costante FE ritirata. ⚠️ Resta: una lista configurabile chiamata **senza** `limit` riceve ancora 25; il ripiego sulla misura risolta può usare la stessa sede di BE25 (2) (`DomainAPIView.initial()`), ma non è fatto: chiede al DB la sola misura risolta, senza la cascata intera a ogni pagina, e oggi quella lettura non c'è (il FE manda sempre `limit` dalla configurazione). Resta come residuo ⭐ **Nel giro 6 (Tid, 2026-11-22).** La lettura c'è: `ui.fn_misura_lista(lista_codice, auth_user_id, emittente_fiscale_id)` (`20261121-28`, §3.6-bis), gemella di `ui.fn_ordinamento_lista`, con la stessa regola della configurazione (`ui.fn_misura_pagina_risolta`). ⏳ **BE**, dopo l'apply: una GET di una view che dichiara `lista_codice`, senza `limit`, prende la misura da lì nella stessa sede di BE25 (2), e `DEFAULT_LIMIT` resta per gli endpoint fuori catalogo ✅ **Fatto (BE, 2026-11-22)**, con tre decisioni di Tid dello stesso giorno: (1) la misura **non** si scrive nella query come l'ordinamento: `DomainAPIView.initial()` registra la *lettura* (`applica_misura_di_partenza`, contextvar azzerata a ogni richiesta) e `pagina_da_query`, unico lettore di `limit`, la chiama solo se pagina, una volta; utente ed emittente della risoluzione in una funzione sola (`_per_chi`, regola del 2) per ordinamento e misura; (2) una misura oltre il `max_limit` della view si riporta al tetto con un warning (difetto del catalogo), il `limit` del client oltre il tetto resta 400; (3) sulle view con `lista_codice` vince la misura: ritirati i default propri di `ApiLottoTaskRuns` (100) e `SearchUniversaleView` (25), i tetti restano. Lettura `fetch_misura_lista` accanto a `fetch_ordinamento_lista`; `JwtMockedApiTest` mocka `misura_risolta` → `DEFAULT_LIMIT`. Presidi: `core/tests/api/test_misura_di_partenza` (11), `ui/tests/db/test_misura_lista_db` (3, DB vero: stesso numero di `pagina_dimensione` della configurazione). api.md §Paginazione e catalogo BB aggiornati |
| BE11 | 2 | **BE.** U21 (il tetto della preferenza sta nel guard di forma del giro 2): `dashboard_preferenza_service.py:205-220`, il tetto 100 preso da `_MAX_WIDGET_PAYLOAD`: Q12 decisa: il tetto 100 sta nel DB (guard di forma), il BE ritira `_MAX_WIDGET_PAYLOAD` per questa regola ✅ **Fatto (BE, 2026-11-22)**, insieme a BE8: `_MAX_WIDGET_PAYLOAD` è ritirato per intero, anche come tetto del numero di card per salvataggio (una card fuori dal pool il guard la rifiuta comunque, e il corpo lo limita il tetto di Django sulla richiesta). `dimensione_max` 0, 101 e `"8"` sono `400 E_UI_CONFIGURAZIONE_FORMA` (test sul DB vero sopra) |
| FE1 | 3 | **FE.** U21: `useDashboardConfig.js:173` (`?? 8`) e `DashboardWidgetModal.vue:37` si tolgono; il ramo `max > 0` (`useDashboardConfig.js:185`, `DashboardWidgetModal.vue:81`) si toglie: «≤0 = nessun tetto» non esiste (Q12). Minore: il terzo ripiego di `ListaConfigurabile.vue:566-569` ✅ **Fatto (FE, 2026-11-22).** Via il `?? 8` e il ramo `max > 0` da `useDashboardConfig.js` e `DashboardWidgetModal.vue` (prop `dimensioneMax` a `null` finché la configurazione non è letta); spec `useDashboardConfig.spec.js` 6-7. Il terzo ripiego di `ListaConfigurabile.vue` (`misuraDefault(USO_MISURA.PAGINA)`) legge già il default dal catalogo del DB (`ui.fn_get_misure_pagina`): non è una copia, resta |
| BE12 | 4 | **BE.** U23: `codice` esce da `UPDATE_KEYS` (`lista_definizione_admin_service.py:76-80`; `ui_admin_repository.py:246-248`) e da `_COLONNA_UPDATE_COLS` (`ui_admin_repository.py:473-479`; `lista_colonna_admin_service.py:96`); il codice d'errore nuovo si mappa ✅ **Fatto (BE + FE, 2026-11-22).** `codice` fuori da `UPDATE_KEYS` e dalle colonne dell'UPDATE di definizioni e colonne: nel PATCH è un 400 sul campo (`fields=("codice",)`); i drawer lo spengono in modifica e lo tolgono dal PATCH (`fermo()` in `ListaDefinizioneDrawer.vue` e `ListaColonnaDrawer.vue`). `perimetro_emittente` non era scrivibile dall'app (mai in whitelist né nell'INSERT): ora le tre dichiarazioni si leggono nel dettaglio admin, in sola lettura, e i commenti nominano il guard nuovo e `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE`. Policy rigenerata (le cinque voci del giro 4 e il ritiro di `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE`, tutte nel CSV in git) e ripieghi senza segnaposto; il ripiego di `E_UI_COLONNA_IN_USO` allineato a Q18 («preferenze utente o preset»). `origine_campo` è nuovo nella pagina admin delle colonne, in lettura e scrittura (enum `VISTA`/`LINEAGE`, schema OpenAPI). Test: `test_update_colonna_codice_immutabile_raises`; il test del seed (`test_i_campi_del_software_non_si_cambiano`) prova il gesto del seed su `descrizione` e `formato`, perché il codice si ferma prima. ⭐ **`/verifica` (2026-11-22):** nei due drawer il codice era fermo per un `campo === 'codice'` cablato, copia del lucchetto del DB. Ora le righe admin di definizioni, colonne e preset portano `non_editable_fields` da `dbops.fn_non_editable_fields` nella SELECT (`_sql_campi_bloccati`), e i drawer lo leggono col BB FE `campoFermo` (regola del 2, ok Tid). Presidi: `test_campi_fermi_righe_admin_db` (DB vero), `campoFermo.spec.js`, `ListaColonnaDrawer.spec.js` |
| BE13 | 4 | **BE + FE.** U24, U25: i CHECK nuovi in `_CHECK_CONSTRAINTS` (`lista_colonna_admin_service.py:127`); nel drawer delle colonne (`ListaColonnaDrawer.vue`, vicino a `:155-160` e `:345`) «Esportabile» spento quando manca il campo sorgente, come già per le azioni; `lista_export_service.py:205-221` ✅ **Fatto (BE + FE, 2026-11-22).** In `_CHECK_CONSTRAINTS` della colonna i tre CHECK nuovi (e quello del campo vuoto), ognuno sul campo che lo risolve, via quello ritirato; in quello della definizione i cinque «non vuoto». ✅ **Scelta della scrittura, confermata da Tid il 2026-11-22:** la normalizzazione silenziosa «azione ⇒ `esportabile=false`» (decisione 6 di `_def.md`, nata col CHECK ritirato) **si ritira**: un valore esplicito contrario arriva al DB ed è un 400 sul campo. Restano i **default** derivati dal modello, solo per il flag non mandato: senza campo sorgente non esportabile, `LINEAGE` non filtrabile né ordinabile. Senza, ogni colonna creata senza campo sorgente era un `IntegrityError` (12 test sul DB vero rossi prima del giro). Drawer: un'azione svuota e spegne il campo sorgente, senza campo «Esportabile» è spento (in creazione si riaccende quando il campo compare), la genealogia spegne filtro, ordinamento e ricerca; spec nuovo `ListaColonnaDrawer.spec.js` (4). Export: `_filter_colonne_esportabili` legge il solo `esportabile` (il filtro sul tipo `azione` era una seconda sede) |
| BE14 | 4 | **BE.** U26: `backend/apps/core/db/_helpers.py:315-330`, la ricerca libera riceve anche i campi della lineage: con Q15 (b) si escludono le colonne marcate lineage ✅ **Verificato (BE, 2026-11-22): niente da cambiare nella ricerca.** `colonne_ricerca_accese` (`_helpers.py`) legge `ui.fn_lista_colonne_ricerca_full` e non aggiunge colonne per altra strada; nessun punto del BE decide «colonna della lineage» per nome. `unisci_sintesi_lineage` lo chiamavano i repository delle sei liste che dichiarano `legge_lineage` **e quello delle fatture**, che non lo dichiara (le sue `pratica_numero`, `pratica_id` e `fase` vengono dalla vista). ✅ **Deciso da Tid il 2026-11-22: il repository delle fatture smette di chiedere la sintesi** (fatto lo stesso giorno). Verificato prima: le colonne che la sintesi aggiunge (frontiera, discendenti, radice, transito) non le legge né il catalogo della lista 48 né `FattureSearchTable.vue`. Il presidio `test_lineage_liste_be` ora prende dal seed le liste che dichiarano `legge_lineage`: chiede la sintesi chi la dichiara, e solo lui (`test_unisce_la_sintesi_chi_dichiara_legge_lineage`). `apps.vendite` verde (2732) |
| BE15 | 4 | **BE + FE.** U22, Q13 decisa (a): il toggle «attivo» di una definizione con figli accesi smette di fallire; il ramo che intercetta `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le liste si ritira ✅ **Fatto (BE, 2026-11-22).** Nessun ramo del BE o del FE intercettava `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le liste (c'è solo il ripiego generico); il test che lo provava diventa `test_spegnere_lista_con_colonne_attive_passa` (la lista si spegne, colonna e preset restano accesi) |
| BE17 | 5 | **BE.** U34: `get_dashboard_id` (`dashboard_repository.py:66-78`) chiama il BB ✅ **Fatto (BE, 2026-11-22).** `get_dashboard_id` legge `SELECT id FROM ui.fn_dashboard_da_codice(%s)` in un savepoint e intercetta `E_UI_DASHBOARD_NON_TROVATA` (`diagnostica_db`) per dare «niente»; ogni altro errore si propaga. Provato sul DB vero (codice assente: `None`, e la transazione resta usabile) |
| BE28 | 5 | **BE + FE.** Q49 e U31: censire i lettori di `ui.dashboard_preset.attivo` che contano su «la dashboard è accesa», e chi spegne una dashboard intercettando `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`; il test `apps/ui/tests/db/test_audit_ui_dal_trigger_db.py`, che fabbrica una dashboard, la fabbrica con un ruolo che scrive il catalogo o usa la `home` del seed. Dettaglio in §3.5-bis, «Le ricadute BE/FE del giro 5» ✅ **Fatto (BE, 2026-11-22).** Censimento: nel BE e nel FE nessun lettore di `ui.dashboard_preset.attivo` (le dashboard si leggono solo dal resolver) e nessuno intercetta `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le dashboard. Il test `test_ignora_riallinea_lo_snapshot_della_dashboard` non fabbrica più la dashboard: dal giro 5 l'app non può nemmeno spostare il contenuto di un preset, quindi il banner acceso lo provano i pgTAP (da proprietario); il test prova la giuntura sulla `home` del seed («Ignora» lega, riallinea lo snapshot, banner spento) e si salta col motivo se manca |
| BE29 | 6 | **FE.** Dopo il push di U40: ritirare le copie FE dell'ordinamento di partenza sulle liste a cui il seed dà il preset (`orderBy` degli store, `defaultSortField` dei componenti: colonna «Copia FE» di U40). ⏳ Aspetta U40 (Q51 è decisa: (c), con BE30). U40 è scritto nel seed (giro 6a, 2026-11-22, §3.6-bis): parte dopo l'apply ✅ **Fatto (FE, 2026-11-22).** Verificato prima: il seed porta gli ordinamenti di U40 su dbdev, e ogni lista della tabella è servita da view che dichiarano `lista_codice` (BE applica il preset). Ritirate le copie su 16 punti: `orderBy`/`orderDir` di `titoliIvaSfondati`, `documentiInterni`, `magazzini`, `ubicazioni`, `movimenti`, `resi`; `order_by`/`order_dir` iniziali a `null` in `canaliIncasso`, `vendite/stores/lotti`, `resiCoda`; `defaultSortField` di `DisponibilitaSearchTable`, `DocumentiInterniSearchTable`, `MagazziniSearchTable`, `MovimentiSearchTable`, `CanaliIncassoSearchTable`, `ResiSearchTable`, `ResiCodaTable`; l'esempio d'uso di `createListaStore`. ⚠️ `orderDirDefault` **resta** dov'era: è il ripiego del verso quando `order_by` arriva senza verso, non una copia del preset. vitest verde (1281), eslint pulito. ⏳ A video: l'intestazione accesa alla prima apertura delle liste della tabella ✅ **Lo schema OpenAPI allineato (BE, `/verifica` del 2026-11-22, BB nuovo con ok di Tid).** Le descrizioni di `order_by`/`order_dir` scritte a mano sulle view con `lista_codice` dicevano «default X» dove ora decide il preset: le dichiara il BB `parametri_ordinamento` (`apps/core/api/openapi_params.py`), su una ottantina di view (liste ed export), e `params_lista` del magazzino è ritirato. Presidio sullo schema generato: `core/tests/api/test_openapi_params.py`. Con lo stesso giro, `limit` delle sette view che lo dichiaravano a mano passa da `parametri_finestra` (BE10) |
| BE30 | 6 | **BE.** Q51 (c), deciso da Tid il 2026-11-22: quando la colonna dell'ordinamento di partenza è la **prima** dei criteri del default del repository, il repository continua coi suoi criteri successivi come spareggio, invece del solo spareggio tecnico. Liste: `magazzino.disponibilita`, `magazzino.disponibilita_articoli`, `magazzino.inventario_piano`, `vendite.resi_da_accreditare`, `vendite.resi_da_riconsegnare` (U40, quelle ⚠️). ⭐ Vale anche per il clic dell'operatore sulla stessa colonna: è la stessa richiesta, e due ordini diversi per «ordina per articolo» sarebbero una seconda regola. ⭐ Non aspetta U40: oggi quelle liste non hanno preset, e il cambio non si vede finché il seed non lo dichiara. Prima di scriverlo: vedere se la forma ricorre (regola del 2: un parametro di `sql_order_clause`, non cinque copie) ✅ **Fatto (BE, 2026-11-22): nessun codice da cambiare, un presidio.** I cinque repository lo fanno già: la disponibilità per magazzino e il piano d'inventario chiudono con una coda fissa (`articolo_id, magazzino_id`; `articolo_id, ubicazione_id, lotto_id, asset_id`), la disponibilità per articolo ha come secondo criterio lo spareggio stesso (`articolo_id`), le due code dei resi chiudono con `v.reso_id DESC, v.resi_riga_id ASC`. Con la prima colonna e il verso del preset l'ORDER BY è identico al default, e così per il clic. Il rischio era l'opposto: portarli su `sql_order_clause` «per uniformità» toglierebbe la coda senza errore. Presidi: `magazzino/tests/services/test_ordinamento_partenza_criteri_successivi.py` (3) e `vendite/tests/services/test_ordinamento_partenza_criteri_successivi.py` (2): stessa clausola E coda attesa nominata, rossi togliendo la coda |
| BE31 | 6 | **BE.** Dal giro 6a (§3.6-bis, `20261121-29`) `ui.fn_lista_colonne_ricerca_full` con un `app.current_user_id` che non è un intero solleva `E_UI_CHIAMATA_NON_VALIDA` (TECNICO, frase chiusa) invece del 22P02 del cast: è lo stesso codice che il BE già solleva per un contesto vuoto o di un altro utente. Cambiano anche la nota (`codici_errore.csv`) e la causa (`messaggi_errore.csv`) del codice: `error_policies_generated.py` e il ripiego da rigenerare (con BE18). ⏳ **Censisci i lettori di `fn_lista_colonne_ricerca_full` (e di `colonne_ricerca_accese`) che contano sul 22P02** o su un `DataError` per riconoscere quel caso: oggi il DB risponde col codice. Già noto: `apps/core/db/_helpers.py` (`colonne_ricerca_accese`) ✅ **Fatto (BE, 2026-11-22).** Policy e ripiego già allineati (rigenerati col commit del magazzino `d609fef87`; `genera_error_policies --check` verde). Censimento: nessun lettore di `colonne_ricerca_accese` / `colonne_ricerca_attive` / `soglia_ricerca` (`ui_repository.ha_ricerca_full`, `search_repository`, `add_ricerca_full_condition`) intercetta 22P02 o `DataError`. ⚠️ **Trovato censendo:** il BE aveva lo stesso difetto di U38 in casa sua: `utente_di_sessione` (`_helpers.py`, unico lettore Python della GUC) faceva `::int` e con una GUC non intera dava il 22P02 prima ancora del DB. Ora riconosce il valore con la regola di `fn_lista_colonne_ricerca_full` (1-10 cifre, ≤ 2147483647) e solleva il codice **del dominio che chiede** (`codice_errore` obbligatorio): `E_UI_CHIAMATA_NON_VALIDA` per la guardia di `get_lista_config_per_video`, `E_PAGAMENTI_CHIAMATA_NON_VALIDA` per `emittente_nel_perimetro` (Tid, 2026-11-22). Presidio sul DB vero: `ui/tests/db/test_lista_da_codice_db` 5-8 (anche il raise di U38 dal DB, ricevuto come codice e non come `DataError`) |
| BE18 | 6 | **BE.** `error_policies_generated.py` da rigenerare dopo la pulizia delle note (§4.3): oggi le righe di `E_UI_*` (fra cui `:1979`, `:1994-1997`) portano brief, date, «il caso del 28-09». U39: `get_lista_id` e `fetch_flag_perimetro` passano dal BB ✅ **Fatto (BE, 2026-11-22).** La rigenerazione era già fatta (BE31). U39: le due letture leggono `ui.fn_lista_da_codice`. ⚠️ Rispetto a Q23 («intercetta, quei lettori vogliono niente») non si intercetta: tutti e due i chiamanti (`ListaPreferenzaService._require_lista_id`, `perimetro_emittente.guard_lista_per_codice`) traducevano il `None` nello **stesso** `E_UI_LISTA_NON_TROVATA` 404, quindi il codice del BB passa com'è e i due `require` ricopiati sono ritirati (con la costante `E_LISTA_NON_TROVATA` di `perimetro_emittente`). Ritirati i quattro test mockati del `None`; presidio sul DB vero: `ui/tests/db/test_lista_da_codice_db` 1-4 (lista accesa, spenta, inesistente) |
| BE19 | — | **BE.** U31 e U23 (`perimetro_emittente`): verificato che il BE non scrive quelle tabelle né quella colonna. Niente da fare, salvo il fallback del codice nuovo |
| BE20 | 2 | **BE + FE.** Q7: `col` di ordinamento e filtri è il codice della colonna. Il FE ordina per campo sorgente (`sortField` di PrimeVue, `ListaConfigurabile.vue:619-668`): il salvataggio della preferenza e del preset traduce il campo in codice nel BE, e il guard di forma rifiuta un `col` che non è un codice (Q34); in lettura il resolver dà anche il campo sorgente. Il test `test_lista_preferenza_service.py:63` già scrive il codice. ⚠️ **Q40 (b), Tid, 2026-11-21:** la traduzione nel BE non si scrive (nessun componente FE manda `col`, §3.2-bis); di BE20 resta la lettura del `campo_sorgente` dalla risposta (con BE25), e un 400 leggibile per il rifiuto del guard su `ordinamento_default` del preset ✅ **Fatto (BE, 2026-11-22).** La lettura del `campo_sorgente` dalla risposta di `ui.fn_ordinamento_lista` la fa il BB di BE25 (2) (`fetch_ordinamento_lista`: la voce porta il campo con cui il repository ordina, non il codice che il preset dichiara; provato sul DB vero con un codice diverso dal campo). Il 400 leggibile c'era già: il guard di `ordinamento_default` solleva `E_UI_CONFIGURAZIONE_FORMA` col campo, e il CRUD admin del preset lo consegna come 400 su `ordinamento_default` (`test_preset_col_campo_sorgente_al_posto_del_codice_400`) |
| BE21 | 5 | **BE.** Q22: `data_update` delle due preferenze la scrive il DB; l'upsert del BE (`ui_repository.py`, `dashboard_repository.py:127-179`) smette di passarla ✅ **Fatto (BE, 2026-11-22).** Via `data_update = now()` dai due upsert e dai due «Ignora»; provato sul DB vero (`test_forma_preferenza_db`: il secondo salvataggio ha `data_update` scritto dal trigger) |
| BE22 | 1a | **BE + FE.** Q26: `is_default` esce dai preset di liste e dashboard. Il BE lo toglie da `_schema_ui.py:31`, `ui_admin_repository.py:56`, `:621-658`, dal drawer dei preset e dai messaggi dell'UNIQUE; la copia della cascata in `ui_repository.py:93-132` si ritira già con Q2 ✅ **Fatto (BE + FE, 2026-11-20).** `is_default` esce da schema, repository, service (whitelist: ora è un 400), drawer, pannello e i18n. ⚠️ Resta a DB la colonna di catalogo `is_default` della lista admin dei preset (`lista_colonna.csv`, id 665): domanda nata nel brief del seed (§16.15, esito del BE), passata qui alla sua archiviazione (2026-11-20): ✅ **Spenta (sessione DB, 2026-11-21)**: `attivo = f` sulla riga 665 di `lista_colonna.csv`. Riga di seed intatta su dbdev, `attivo` è dell'installazione (riga 4 del registro): il mirror `runOnChange` (`20260806-15`) la porta al migrate. La lista 58 non ha vista, quindi il controllo del campo sorgente non scatta sul campo che non c'è più; la riga di composizione del preset 58 resta (figlia, la colonna spenta il resolver la salta). ⏳ Il migrate di Tid |
| BE23 | 1a | **BE + FE.** Q30: un posto (lista o dashboard, ambito, profilo, azienda) ha al più un preset acceso. Accendere un secondo preset nello stesso posto è rifiutato dall'UNIQUE `uq_ui_lista_preset_posto` (o `uq_ui_dashboard_preset_posto`): il servizio lo mappa (`_CHECK_CONSTRAINTS` o il ripiego dell'integrità in `lista_preset_admin_service.py`), e il drawer dice di spegnere prima quello acceso. La bozza nasce spenta. File: `backend/apps/ui/services/lista_preset_admin_service.py`, `ListaPresetDrawer.vue` ✅ **Fatto (BE + FE, 2026-11-20).** `uq_ui_lista_preset_posto` mappato sul campo `attivo` col messaggio «spegnilo prima»; la bozza nasce spenta (default `attivo=false` in service, repository e drawer) |
| BE25 | 1b | **BE.** Codice d'errore nuovo `E_UI_PRESET_CONTENUTO_DERIVATO` (TECNICO, segnaposto: il codice del preset): `error_policies_generated.py` e `error_messages_fallback.py` da rigenerare, la riga in §Tassonomia errori di `docs/it/dev/api.md`. Lo produce solo un chiamante rimasto alla forma in cui la data del contenuto si scriveva. Il codice `E_UI_PREFERENZA_NON_TROVATA` ha una nota che parla dell'endpoint «ignora» (DEF-2): resta valido se l'endpoint resta, e la nota si pulisce nel giro 6 ✅ **Fatto (BE, 2026-11-21).** `error_policies_generated.py` rigenerato (diff: la sola voce nuova, `TECNICO`; DB e git allineati sui codici), ripiego in `error_messages_fallback.py`, `--check` allineato. ⚠️ La §Tassonomia errori di `api.md` non ha una tabella dei codici `E_UI_*` (ne tiene le regole, non l'elenco): il codice sta nell'elenco dei codici UI del catalogo BB backend, accanto agli altri `E_UI_*`. Provato sul DB vero: chi scrive la data del contenuto riceve il codice, 500 (`test_data_del_contenuto_scritta_dall_app_rifiutata`) |
| BE24 | 1a | **BE.** La pagina `docs/it/backend/ui/manual/api_ui_liste.md` (righe 445, 514, 534) descrive il trigger z90 e la sua funzione, tolti dal giro 1a: lo snapshot lo scrive `ui.trgfn_preferenza_preset_base_snapshot` (BE6) ✅ **Fatto (BE, 2026-11-20).** `api_ui_liste.md` descrive il trigger nuovo, `preset_base` e `preset_base_cambiato`; `api_ui_admin_personalizzazioni.md` è senza `is_default` e con la superficie del seed |
| BE25 | 2 | **BE + FE.** Q37 decisa (a) da Tid il 2026-11-20: quando la richiesta non porta `order_by`, una lista configurabile ordina e filtra con `ordinamento` e `filtri` della configurazione risolta dell'utente, e l'export fa lo stesso. La risposta dice l'ordinamento applicato, e il FE accende l'intestazione da lì. Si ritirano gli `orderBy` ricopiati negli store e i `default_order` dei BE che ricopiano l'`ordinamento_default` del preset. Parte dopo il giro 2 (U13 filtra le voci, BE20 fissa `col` = codice), perché il BE applichi solo voci già pulite. **Approfondimento (BE, 2026-11-20).** *Ordinamento.* Nel modello ha una sede e un significato: il preset dichiara come parte la lista per ruolo, azienda o sistema, e il seed lo valorizza (`lista_preset.csv`, colonna `ordinamento_default`). Oggi lo stesso fatto sta in tre posti: il preset, l'`orderBy` dello store e il `default=` del repository; `strumenti/stores/codeJobs.js:55-59` lo scrive esplicitamente. Ritirare la colonna lascerebbe comunque due sedi nel codice, e l'ordine di partenza non si potrebbe più dare per ruolo. Con (a) le sedi diventano una. Il percorso c'è già: le liste configurabili leggono il catalogo a ogni chiamata per la ricerca libera (`colonne_ricerca_accese(lista_codice)`, `apps/core/db/_helpers.py`), quindi il repository conosce il codice della sua lista. Senza `order_by` il repository chiede l'ordinamento risolto e lo passa alla sua whitelist (`sql_order_clause`) col campo sorgente dato da BE20. L'export eredita lo stesso default, perché le righe le legge il repository della view (`build_export_response` riceve righe già ordinate). Da chiedere al DB: la sola chiave `ordinamento` della cascata, senza la risoluzione intera (colonne e permessi) a ogni pagina, da una funzione che usi lo stesso `fn_preset_di_base`. Da decidere: se il clic dell'operatore sull'intestazione si salva nella preferenza; se no, la chiave `ordinamento` della preferenza non la scrive nessuno (vedi Q39). *Filtri.* Il modello non ha la sede: `filtri_default` non dice quali filtri ha una lista (non c'è un catalogo dei filtri di lista, e i filtri degli endpoint sono parametri di query, spesso non colonne: `data_da`, `solo_aperte`). Il seed non lo scrive, il drawer admin non lo mostra, nessuno lo legge. Il contratto «formato trasparente al BE» non lo può applicare nessuno: vedi Q38 ⚠️ **La funzione chiesta al DB è nel piano del giro 2 (sessione DB, 2026-11-21):** `ui.fn_ordinamento_lista`, la sola sede dell'ordinamento risolto (§3.2-bis); i filtri non ci sono, ritirati da Q38 §6 ✅ **Fatto (BE + FE, 2026-11-22)**, con la sede centrale approvata da Tid lo stesso giorno. **BE:** BB `apps/core/services/ordinamento_di_partenza.py`, agganciato a `DomainAPIView.initial()` dopo il cancello di perimetro: su una GET di una view che dichiara `lista_codice`, senza `order_by`, legge `ui.fn_ordinamento_lista` e mette nella query la **prima** voce (Tid: `sql_order_clause` ordina per una colonna più lo spareggio) — la ricevono `parse_list_params`, le letture dirette e l'export senza toccarli; la risposta lo dice in `meta.ordinamento` (`success_response`, contextvar azzerata a ogni richiesta). I `default_order` dei BE **restano** come regola dell'API senza preset (Tid, 2026-11-22). Presidi: `test_ordinamento_di_partenza` (6), `test_ordinamento_lista_db` (3, DB vero), `test_ogni_lista_codice_ha_la_whitelist_a_registro` (ogni `lista_codice` dichiarato ha la whitelist a registro, quindi l'`order_by` iniettato è coperto da `test_whitelist_copre_le_colonne_ordinabili`); `JwtMockedApiTest` mocka la lettura (`ordinamento_risolto` → `[]`). **FE:** `useListaEmptyStateFetch` espone `ordinamentoApplicato` da `meta.ordinamento` (non in `filters`: non è un clic); `useSearchTable.paginatorProps` accende l'intestazione da lì quando l'operatore non ha ordinato. Ritirate le copie dell'ordinamento del preset su 46 punti (`orderBy` degli store, `defaultSortField` dei componenti, la factory di `codeJobs.js`) per le liste la cui view dichiara `lista_codice`, fra cui **due divergenti, ora allineate al preset**: i contratti (`valido_dal` nello store e nella tabella, `data desc` nel preset). Verde: tutta la suite BE (7447 + i nuovi), vitest (1266). ⏳ **Residuo:** 33 copie su 18 liste servite da view che **non** dichiarano `lista_codice` (quasi tutte `AdminAPIView` dell'amministrazione), dove il BE non applica il preset: `amm.processi`, `amm.reparti`, `anagrafiche.accessi_altri`, `anagrafiche.accessi_sistema`, `anagrafiche.categorie_clienti`, `anagrafiche.categorie_clienti_listini`, `anagrafiche.emittente_billing_account`, `anagrafiche.emittenti_fiscali`, `anagrafiche.operatori`, `config.email_account`, `config.email_log`, `config.email_template`, `config.tipi_ruolo_tipi_indirizzo`, `config.utilities_tipi_ruolo`, `core.sessioni_attive`, `dbops.error_log`, `storico.audit_log`, `vendite.famiglie_documento`. Restano finché le loro view non dichiarano `lista_codice` (e l'aggancio non sale in `_ApiViewBase`, dove oggi non c'è il cancello di perimetro): lì una copia divergente c'è, `amm.processi` (`codice` nella tabella, `canale` nel preset). Restano anche le copie su 13 liste il cui preset non dichiara un ordinamento (U40 e BE29: il seed le completa, il FE le ritira) e su 23 superfici fuori catalogo, che non sono copie del preset. ⭐ **`/verifica` (2026-11-22): proposto, non applicato.** Il BB ora *propone* la voce (`proponi_ordinamento`); la conferma `colonna_ordinamento`, sede unica della risoluzione delle chiavi, e solo allora `meta.ordinamento` c'è. Una lista che ordina nel browser non lo porta più. Una chiave proposta fuori whitelist (colonna `ordinabile` a catalogo, accendibile dall'amministratore, su un campo che il codice non sa ordinare) era un 400 a ogni apertura della lista: ora è `OrdinamentoPropostoRifiutato`, e `DomainAPIView.handle_exception` ritira la proposta, scrive il difetto nel log e rilegge con lo stesso handler. Un `order_by` del client fuori whitelist resta 400. Presidi: `test_ordinamento_di_partenza` (16) ✅ **Residuo fatto (BE + FE, 2026-11-22; via di Tid: (a) la partenza su ogni porta, (b) su `amm.processi` vince il preset).** Il nodo era che `lista_codice` accendeva insieme il cancello di perimetro e la partenza, dentro `DomainAPIView`: dichiararlo su una `AdminAPIView` avrebbe dato il 422 «scegli un emittente» su 7 liste admin con `perimetro_emittente = t` e `multi_emittente = f`. Ora `lista_codice` e la partenza (ordinamento, misura, rilettura sul rifiuto) stanno su `_ApiViewBase`; il cancello è un aggancio, `_cancello_di_lista`, che solo `DomainAPIView` riempie, chiamato prima della partenza. Dichiarano la lista 29 view: le 18 del residuo, `config.utilities_tipi_ruolo_usage`, le sei geografiche, `catalogo.articolo_uom`, `catalogo.note` (la fabbrica delle note riceve `lista_globale` dal repository) e il log email dell'operatore. Il presidio di copertura conta come esenti le `AdminAPIView` (chiusura sulle basi) e non dichiara superata un'esenzione «globale»; trovato un difetto vecchio: `pratiche.definizioni_workflow` era contata «coperta» da un `lista_codice` su `AdminAPIView` che non accendeva niente (ora esente con la sua ragione). **FE:** ritirate le copie delle 18 liste e quelle di altre 21 superfici di catalogo che il censimento di BE25 (2) contava «fuori catalogo» e invece hanno lista e preset (smentito sul DB il 2026-11-22): distinte, eccedenze, rate, rate fuori capienza, coda righe, flussi, lotti di magazzino, documenti generati, conversioni UoM, registri, versioni di template, approvazioni prezzo, giornale, Storia, contratti del cliente (divergeva: `valido_dal` contro `data desc`), versioni di listino, revisioni (via il parametro `orderBy` di `createRevisioniStore`), ricerca soggetti. Resta, di proposito, `TemplateAssetRiferimenti`: è una chiamata diretta che riempie una scelta, non una lista. ⚠️ Fuori: le 4 liste di `ui` (definizioni, colonne, preset, permessi), il cui preset non dichiara un ordinamento e il cui repository non risolve chiavi: la partenza non avrebbe niente da applicare. Prove: `core/tests/api/test_partenza_su_ogni_porta` (5), `test_perimetro_emittente_copertura`, `test_openapi_params` (lo schema delle 29 col BB); sul DB vero le 29 rotte, GET senza `order_by` né `limit` da super admin con un token di veste: 200 e `meta.ordinamento` uguale al preset su tutte. Suite BE e vitest verdi |
| BE26 | 2b | **BE.** I codici e i vincoli del giro 2b in policy e ripiego (`E_UI_WIDGET_IN_USO`, `E_UI_PRESET_POSTO_IMMUTABILE`, con `E_UI_CONFIGURAZIONE_FORMA` del 2a) e i nomi delle FK composite dove il servizio mappa per nome. Dettaglio in §3.2-bis, «Le ricadute BE/FE del giro 2», punto 6 |
| BE32 | Q55 | **BE.** Q56 decisa (a) da Tid il 2026-11-22: in `backend/apps/ui/services/lista_colonna_admin_service.py` via il conteggio delle preferenze da `_richiedi_colonna_non_in_uso` (resta quello dei preset), via `count_preferenze_referenced_by_colonna` (`backend/apps/ui/db/ui_admin_repository.py:609`) se non ha altri lettori, riallineati la testata del service («Soft-block DELETE») e i test che lo provano; la doc `docs/it/backend/ui/manual/` del CRUD delle colonne. In tutti e due i casi: `E_UI_WIDGET_IMMUTABILE` (`CONFLITTO_STATO`, segnaposto: la colonna) in policy e ripiego (`genera_error_policies`, `error_messages_fallback.py`); `E_UI_COLONNA_CODICE_IMMUTABILE` ora copre anche `lista_id`, che il BE non scrive in UPDATE: nessun punto da mappare, da verificare. Il pool e il catalogo delle card il BE non li scrive. ✅ L'apply è fatto (Tid, 2026-11-22): si può partire. ✅ **Fatto in parte (BE, 2026-11-22, dalla revisione del giornale delle corse):** `E_UI_WIDGET_IMMUTABILE` in policy (`genera_error_policies`, `--check` verde, una voce nuova e nessuna classe cambiata) e nel ripiego; il ripiego di `E_UI_COLONNA_CODICE_IMMUTABILE` dice anche la lista. Verificato: `lista_id` non è nella whitelist dell'UPDATE di `lista_colonna_admin_service` (riga 113), nessun punto da mappare. ~~⏳ **Resta** la parte Q56~~ ✅ **Fatta la parte Q56 (BE/FE, 2026-11-23)**: il controllo delle preferenze è uscito dal service (`_richiedi_colonna_non_in_uso` → `_richiedi_colonna_in_nessun_preset`, resta solo quello dei preset); `count_preferenze_referenced_by_colonna` ritirato dal repository (nessun altro lettore); riallineati la testata del service, i commenti di repository, view admin, `error_ui_overrides`, client e store FE, il messaggio di conferma del drawer (it/en: ora dice che la colonna esce dalle personalizzazioni e che la ferma un preset), la doc `api_ui_admin_personalizzazioni.md` (§21 e codici errore). Test: il caso «in uso da preferenze → 409» è sostituito da «non consulta le preferenze», col repository `MagicMock(spec=UiAdminRepository)`, così una chiamata al conteggio ritirato è un errore e non una chiamata muta. Verificato sulla doc DB che `ui.trgfn_voce_ritira_dalle_preferenze` è `AFTER DELETE` su `lista_colonna`. Il ripiego di `E_UI_COLONNA_IN_USO` ora dice «in uso in un preset: toglila prima dal preset, oppure disattivala». **Garanzia ritirata (lato BE)**: «una colonna che una preferenza nomina non si cancella dal pannello». Lettori: le preferenze stesse, che il DB ripulisce nello stesso DELETE (Q55), e il resolver, che già salta una voce assente; nessun altro lettore BE/FE ne dipende. ⏭️ **Richiesta al team DB**: il messaggio a catalogo di `E_UI_COLONNA_IN_USO` (`messaggi_errore.csv`, «in uso in preferenze utente o preset») dice ancora le preferenze; proposto lo stesso testo del ripiego: «La colonna è in uso in un preset: toglila prima dal preset, oppure disattivala con attivo=false invece di eliminarla.». La classe (`CONFLITTO_STATO`) non cambia. ✅ **Scritto (sessione DB, 2026-11-23)**: `messaggi_errore.csv` col testo proposto; il codice nel DB non lo solleva nessuno, e nessun pgTAP ne legge il testo. ✅ **Applicato** su dbdev (Tid, 2026-11-23) |
| BE33 | 7 | **BE + FE.** Q58 (a), giro 7 (`20261122-35`, §3.6-quinquies): `ui.fn_get_misure_pagina` risponde anche `default_per_uso`, `{uso: misura}` per ogni valore di `ui.uso_misura_pagina` (oggi `COMPATTA` e `PAGINA`). **Censisci i lettori di `default_compatta` e `default_pagina`** (l'endpoint delle misure, chi lo serializza, il FE che sceglie la misura di partenza per uso) e falli leggere da `default_per_uso`, con l'uso della lista come chiave. Già noto: `docs/it/backend/ui/manual/api_ui_liste.md` (l'esempio di risposta e le due voci). Quando nessuno legge più le due chiavi, il team DB le ritira con un changeSet: dillo nel brief. Nessuna garanzia ritirata: oggi la risposta ha una chiave in più. ⏳ Sbloccata: il giro 7 è applicato (Tid, 2026-11-22). ✅ **Fatto (BE/FE, 2026-11-23).** Censiti i lettori: l'unico che leggeva le due chiavi è il BB FE `core/misurePagina.js` (`registraMisurePagina`); il BE fa da tramite (`UiRepository.get_misure_pagina`, `ApiMisurePaginaView`), e le citano solo test, commenti e doc. Il BB ora legge `default_per_uso`: rifiuta una risposta senza la mappa, con un valore fuori dalle misure o senza uno degli usi di `USO_MISURA`; un uso nuovo dell'enum arriva senza toccare il BB (`misuraDefault(uso)`, con `Object.hasOwn`). Riallineati: lo schema OpenAPI della view (dichiara `default_per_uso`, non più le due chiavi), il commento del repository e del client FE, gli spec (`misurePagina.spec.js` coi casi nuovi, il setup di Vitest, `useListaDrawerPaginata.spec.js`), `test_lista_api`, il test sul DB vero `test_misure_pagina_db` (le chiavi di `default_per_uso` confrontate con `enum_range(NULL::ui.uso_misura_pagina)`, verde con `ZEROERP_TEST_DB_E2E=1`), la doc `api_ui_liste.md` e le voci dei due cataloghi BB. ⏭️ **Al team DB: nessuno legge più `default_compatta` e `default_pagina`**; il ritiro può partire quando questo lavoro è su `Tito-dev` (il BE passa la risposta com'è, quindi il ritiro non chiede un altro giro BE). ✅ **Scritto (sessione DB, 2026-11-23)**: `20261122-48` toglie le due chiavi e le loro righe nel COMMENT; lato DB nessuna funzione né vista le legge (pg_proc e pg_views su dbdev). Il caso 19 di `ui/test-misure-pagina-v1` asserisce che la risposta ha solo `misure` e `default_per_uso`, il caso 2 legge i default da lì. Prova sullo scratch (`prova_changeset.py`, `-48` e `-49` in ROLLBACK, da owner): preCondition passate, estratto intero, catalogo identico dopo; `test-misure-pagina-v1` senza 17/2 (il 16 da owner per costruzione, il 19 perché le chiavi ci sono ancora), con 18/1 (il solo 16); `dbops/test-comment-al-presente-v1` 8/0 senza e con. ✅ **Applicato** su dbdev con `-49` e il CSV, pgTAP verdi (Tid, 2026-11-23) |
| BE34 | 8 | **BE.** Q60 (a), giro 8 (§3.6-sexies): le funzioni del database leggono `app.current_user_id` da `script.fn_utente_di_sessione`. Un valore che non è l'id di un utente (non solo cifre, zeri in testa, `0`, oltre il massimo di `integer`) dà `E_SCRIPT_CHIAMATA_NON_VALIDA` (TECNICO, già a catalogo: verifica che sia nelle policy d'errore del BE) invece del 22P02 grezzo; la GUC assente o vuota resta NULL, come oggi. **Censisci** chi scrive la GUC (il middleware che la imposta, le corse e i comandi che la impostano a mano, i test) e chi conta oggi sul 22P02 di quella lettura (mappature di `22P02`/`InvalidTextRepresentation`, test che lo asseriscono); dimmi se qualcuno scrive un valore che il BB ora rifiuta. Dal giro 8b (`-27` … `-36`) vale anche per le letture sotto RLS: con la GUC sporca una SELECT su una tabella protetta dà il codice invece del 22P02. Nessuna garanzia ritirata: un valore sporco era già un errore, ora ha il suo codice. ✅ Sbloccata: `-16` … `-25` applicati (Tid, 2026-11-23); `magazzino` col `-26` ✅ **Fatto (BE, 2026-11-23).** **Chi scrive la GUC:** `JwtAuditAuthentication` (`str(user_id)`, sempre un intero), gli smoke (`_smoke_contesto.py` e gli altri) e i test DB (un id, oppure `''`; `test_ricerca_full_db` scrive `uid+1_000_000`, dentro il massimo): **nessuno scrive un valore che il BB rifiuta**, salvo i test che lo fanno apposta. **Chi contava sul 22P02:** nessun codice BE (le citazioni sono commenti, o 22P02 di altri cast). `E_SCRIPT_CHIAMATA_NON_VALIDA` era già in policy (`TECNICO`) e nel ripiego. **Difetto trovato:** il BB backend `utente_di_sessione` (`core/db/_helpers.py`, BE31) ricopiava la regola in Python (regex di cifre e tetto, col codice del dominio che chiede) e accettava `0` e `007`, che il BB DB rifiuta. Via di Tid (2026-11-23): il BB backend **legge dal BB DB** (`SELECT script.fn_utente_di_sessione(%s)`, `function_name` come `p_chi`); esce il parametro `codice_errore`, e una GUC sporca dai due consumatori (`UiRepository.utente_di_sessione`, `pagamenti_repository.emittente_nel_perimetro`) è `E_SCRIPT_CHIAMATA_NON_VALIDA` invece di `E_UI_`/`E_PAGAMENTI_CHIAMATA_NON_VALIDA` (stessa classe, stesso 500; i due codici restano vivi, li sollevano altri punti). Test sul DB vero `ui/tests/db/test_lista_da_codice_db` (5-9): il BB coi valori rifiutati (`0` e `007` compresi), la ricerca della lista (il caso 8 era rosso dal giro 8: aspettava `E_UI_CHIAMATA_NON_VALIDA`), e il caso nuovo 9, una SELECT su `anagrafiche.clienti` da operatore con la GUC sporca, che dà il codice (giro 8b). Verdi `apps.ui.tests`, `apps.pagamenti.tests`, `test_ricerca_full_db` con `ZEROERP_TEST_DB_E2E=1`. Riallineati la voce del catalogo BB backend (e l'indice), `api_ui_liste.md` (§codici errore). Nessuna richiesta al team DB |
| Q38 | — | ✅ **Deciso da Tid il 2026-11-20: (a), i filtri si ritirano.** **Chi cambia per primo.** (1) ✅ **Fatto (BE + FE, 2026-11-20).** FE: `_PAYLOAD_ROOT_KEYS` di `useListaConfig.js` porta solo `colonne` e `pagina_dimensione` (test 3-bis in `useListaConfig.spec.js`). BE: `filtri_default` fuori da `CREATE_KEYS`/`UPDATE_KEYS` (ora è un 400), dall'INSERT e dalla whitelist di `update_preset`, e dallo schema OpenAPI (`_schema_ui.py`); la lettura admin resta fino al ritiro. I due test DB di audit che spostavano il contenuto con `filtri_default` lo fanno con `ordinamento_default`. ⚠️ **Per la sessione DB:** il giro 1b, applicato su dbdev il 2026-11-20 e non ancora su git, ha le date del contenuto per chiave **comprese `filtri` e `ordinamento`**: il ritiro del passo (2) toglie anche quelle due chiavi da snapshot, ignorato e data del contenuto. Testo originale del passo: (1) BE/FE, subito e senza rischio: il FE smette di mandare `filtri` e `ordinamento` nel salvataggio della preferenza (`useListaConfig.js:254`). Il salvataggio è per chiave, quindi una riga vecchia che li porta (salvata prima del 2026-11-01, quando si salvava la configurazione intera) li perde al primo salvataggio, ed è l'esito voluto. Il BE smette di scrivere `filtri_default` dal CRUD admin dei preset. (2) DB, nel giro 2: via la colonna `lista_preset.filtri_default`; via le chiavi `filtri` e `ordinamento` (Q39) dalla preferenza (pulizia delle righe), dall'uscita del resolver e dal guard di forma. (3) BE, dopo l'apply: via `filtri` e `ordinamento` dalla whitelist di `lista_preferenza_service.py:41` e `:192-200`, e dalla lettura admin (`ui_admin_repository.py:82`). Prima di (3) un PUT che porta le due chiavi passa ancora. Testo della domanda: `filtri_default` del preset e la chiave `filtri` della preferenza: (a) si ritirano (colonna, chiave del resolver, whitelist di salvataggio, guard di forma del giro 2), e i filtri di partenza restano dello store (`filterDefaults`); (b) il modello si allarga con un catalogo dei filtri di lista (codice, parametro dell'endpoint, tipo), e allora il preset li può dichiarare e il BE applicarli come l'ordinamento. **Raccomandata (a):** un filtro di partenza per ruolo oggi non è una richiesta, e (b) è uno sviluppo nuovo, da aprire nel suo brief quando servirà; tenere una colonna senza contratto è peggio che non averla. ⛔ Il ritiro è lavoro DB (colonna, resolver, guard): dal BE parte la richiesta, e i lettori BE/FE da adeguare sono `ui_admin_repository.py:82`, `:668`, `:715`, `lista_preferenza_service.py:41`, `useListaConfig.js:254` |
| Q39 | — | ✅ **Deciso da Tid il 2026-11-20: (b), il clic non si ricorda.** La chiave `ordinamento` della preferenza si ritira con i filtri (stesso ordine di Q38); l'ordinamento di partenza lo dà solo il preset (`ordinamento_default`, che resta), e il BE lo applica (BE25). Testo della domanda: il clic sull'intestazione si ricorda? (a) Sì: il FE salva l'ordinamento scelto nella preferenza (chiave `ordinamento`), e alla volta dopo la lista riparte da lì; (b) no: la chiave `ordinamento` della preferenza si ritira insieme ai filtri, e l'ordinamento di partenza resta solo del preset. **Raccomandata (b)** finché nessuno chiede (a): oggi l'ordinamento cliccato vale per la sessione, e una preferenza scritta a ogni clic cambierebbe il comportamento di tutte le liste |

## 7. Le decisioni di Tid

| # | Domanda | Decisione |
| --- | --- | --- |
| Q1 | U1: chi scrive lo snapshot del preset di base | ✅ **Deciso da Tid il 2026-11-18: (b) il DB**, letto dal preset, insieme a U2; una funzione z90 sola |
| Q2 | U2: il preset di base esposto dal resolver | ✅ **Deciso da Tid il 2026-11-18: sì.** **Chiave additiva `preset_base`** per liste e dashboard, la copia BE ritirata |
| Q3 | U5: la base salvata è spenta o non è più quella di oggi | ✅ **Deciso da Tid il 2026-11-18:** **(b) un esito «base cambiata»**, chiave additiva |
| Q4 | U6: il banner per chiave | ✅ **Deciso da Tid il 2026-11-18:** **(a) una data del contenuto per chiave** sul preset; lato preferenza, snapshot e ignorato JSONB per chiave (Q29) |
| Q5 | U7: il preset di un'azienda spenta | ✅ **Deciso da Tid il 2026-11-18:** **(a) il filtro** sull'azienda accesa |
| Q6 | U12: la forma della preferenza | ✅ **Deciso da Tid il 2026-11-18:** **(a) un guard DB comune** a liste e dashboard, più i cast sicuri |
| Q7 | U13: la convenzione di `col` (codice o campo sorgente), prima di filtrare l'ordinamento nel DB | ✅ **Deciso da Tid il 2026-11-18: il codice** della colonna (l'identità, la stessa chiave delle voci `colonne`); il resolver aggiunge il campo sorgente in uscita per il FE; all'ingresso il guard rifiuta, il BE traduce (Q34) |
| Q8 | U14: un widget tolto dal pool, se un preset lo propone | ✅ **Deciso da Tid il 2026-11-18: bloccato**: si toglie prima dal preset |
| Q9 | U15: `DROP DEFAULT 25`, e le righe del seed che scrivono 25 o 10 | ✅ **Deciso da Tid il 2026-11-18: sì `DROP DEFAULT`**; i 25 e i 50 diventano NULL (seguono `PAGINA`); i 10 diventano NULL con l'uso `COMPATTA` dichiarato dalla lista (Q11 decisa (a)) |
| Q10 | U16: la misura ritirata e le preferenze | ✅ **Deciso da Tid il 2026-11-18:** **(b) il ritiro toglie la chiave** dalle preferenze |
| Q11 | U20: la lista dichiara l'uso della misura (`COMPATTA` o `PAGINA`) | ✅ **Deciso da Tid il 2026-11-18: (a) sì, e sì a Q11-bis.** La lista dichiara l'uso (iniziale `PAGINA`, le liste di righe `COMPATTA`) e il resolver ripiega sul suo default. **Q11-bis** (BE10): le liste configurabili prendono la misura dal DB; `DEFAULT_LIMIT` del BE resta solo per gli endpoint fuori catalogo, dichiarato come regola dell'API |
| Q12 | U21: il tetto della dashboard | ✅ **Deciso da Tid il 2026-11-19: (a).** `CHECK (dimensione_max > 0)` sul preset, NULL = lo standard, l'8 in una sede DB; il tetto vale fra 1 e 100 e sta nel DB (guard di forma, Q6); «≤0 = nessun tetto» non esiste |
| Q13 | U22: spegnere una lista sospende colonne e preset | ✅ **Deciso da Tid il 2026-11-19:** **(a) sì**, eccezioni ATTIVO (forma della decisione del 2026-11-08) |
| Q14 | U23: che cosa del seed scrive solo l'owner | ✅ **Deciso da Tid il 2026-11-19, tutte e cinque come raccomandato:** `perimetro_emittente` nel guard; codici di lista e di colonna immutabili; ~~la vista di una lista certificata solo dall'owner~~ (la tiene il seed per colonna, QU4); `ricerca_min_caratteri` resta all'app, colonna d'installazione nel censimento del seed (Q27) |
| Q15 | U26: la sede dei nomi della lineage | ✅ **Deciso da Tid il 2026-11-19: (b)**, più il lato lista da una sede esistente o, se manca, da (a). **(b) un marcatore sulla colonna** |
| Q16 | U27: riverificare le colonne | ✅ **Deciso da Tid il 2026-11-19:** **(a)**: controllo immediato per l'app, salto sulle liste spente con verifica all'accensione, le partizionate, un BB; la vista che perde colonne, un presidio `dbops` (Q32) |
| Q17 | U29: i permessi di colonna con la veste NULL | ✅ **Deciso da Tid il 2026-11-19:** **(b) il livello più restrittivo** fra le vesti; per la cascata dei preset il passo del ruolo si salta (Q28) |
| Q18 | U30: la composizione del preset alla cancellazione della colonna | ✅ **Deciso da Tid il 2026-11-19: (b) bloccato** (NO ACTION), coerente con Q8; controllo preventivo che conta anche i preset, messaggio e commenti veri. La raccomandazione iniziale era (a) CASCADE |
| Q19 | U31: le cinque tabelle di catalogo delle dashboard in sola lettura per l'app | ✅ **Deciso da Tid il 2026-11-19: sì** |
| Q20 | U32: «la home non è mai vuota» | ~~Un presidio `dbops`, non un trigger~~ (2026-11-19). ✅ **Superata da Q31 (2026-11-20): un constraint trigger differito**, come U18 |
| Q21 | U33: area e azione del widget | ✅ **Deciso da Tid il 2026-11-19:** se c'è l'azione, l'area è nulla oppure quella dell'azione |
| Q22 | U36: le preferenze senza audit | ✅ **Deciso da Tid il 2026-11-19: voluto.** Il COMMENT lo dice; `data_update` la scrive il DB, non il BE |
| Q23 | U39: «lista accesa per codice» per chi vuole «niente» | ✅ **Deciso da Tid il 2026-11-19:** **il BE chiama il BB** e intercetta il codice, nessun BB nuovo |
| Q24 | L'ordine dei giri (§2) | ✅ **Deciso da Tid il 2026-11-19: come in §2.** **Q24-bis:** il preset di ruolo che prevale sull'emittente resta (§3.7). Il giro 1 diviso in 1a e 1b (Q36) |
| Q25 | Una guida delle dashboard: oggi non c'è (§9) | ✅ **Deciso da Tid il 2026-11-19: (a), scritta a fine giro 5.** **Una guida `configurazione-dashboard`** sua, che rimanda alla guida delle liste per il meccanismo comune |
| Q26 | `dashboard_preset.is_default = false`: uno stato senza lettori | ✅ **Deciso da Tid il 2026-11-20: `is_default` si ritira, su liste e dashboard.** Un preset per posto, vale se acceso; la bozza si prepara spenta. Il gemello delle liste è uguale (trovato il 2026-11-19). I preset alternativi, se verranno, nascono nel brief delle viste nominate. Nel giro si riallinea la guida `configurazione-liste` (§2.3 e il passo 5 di §10), che oggi descrive `is_default`; lo stesso changeSet toglie `is_default` dalle colonne del software di `ui.lista_preset` nel registro del seed (riga 5 di `dbops.automazione_seed_primo_impianto`), o la tabella diventa `NON_CLASSIFICATA`. I due indici `uq_*_default` li sostituisce l'UNIQUE parziale `WHERE attivo` (Q30) |

### 7.1 Le decisioni dell'analisi critica (2026-11-20)

Aperte dall'analisi critica prima del via al giro 1, e **decise da Tid il 2026-11-20, tutte come raccomandate**. Ognuna
completa o sostituisce una decisione già presa: la decisione nuova sta in §7 e nella scheda del difetto, e la scelta
superata è barrata, non resta come alternativa. Q37-Q39 vengono dopo: le ha aperte il piano del giro 1b (§3.1-ter,
2026-11-20), e Tid le ha decise lo stesso giorno, come raccomandate. Q40-Q42 le ha aperte il piano del giro 2 (§3.2-bis,
2026-11-21), e Tid le ha decise lo stesso giorno: Q41 e Q42 come raccomandate, Q40 (b) dopo la verifica del team BE.
Q44-Q46 le ha aperte il piano del giro 3 (§3.3-bis, 2026-11-21), decise da Tid lo stesso giorno come raccomandate.
Q47 e Q48 le ha aperte il piano del giro 4 (§3.4-bis, 2026-11-21), decise da Tid lo stesso giorno come raccomandate. Q49 l'ha aperta la scrittura del giro 4 (2026-11-21), decisa da Tid lo stesso giorno come raccomandata.

| # | Domanda | Riapre o completa | Opzioni | Decisione |
| --- | --- | --- | --- | --- |
| Q27 | Le tabelle di catalogo di `ui` nel meccanismo del [brief del seed](../work-done/2026/brief-db-seed-primo-impianto-non-si-riscrive.md): sono mirror `runOnChange` che l'app scrive dalle pagine admin, e il migrate riscrive le modifiche dell'app (`ricerca_min_caratteri`, preset, colonne, composizione) | Q14; i giri che toccano i CSV di `ui` (Q7, Q9, Q20, Q26) | (a) Le tabelle si dichiarano nel censimento del brief del seed, ognuna con la sua specie, e i giri di `ui` che toccano i CSV partono dopo; (b) il censimento si fa qui, nel giro 4, e il brief del seed lo riceve | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: il meccanismo ha una sede sola. Le cinque tabelle delle dashboard, in sola lettura per l'app (Q19), escono dal censimento |
| Q28 | Un significato solo per la veste NULL: oggi la cascata dei preset unisce le identità (U4, parità fra due PORTALE), i permessi di colonna prendono il livello più restrittivo (Q17) | U4 (lo spareggio sull'id, superato), Q17 | (a) Con la veste NULL il passo del ruolo si salta, e la cascata parte dall'azienda; i permessi restano al più restrittivo; (b) un vincolo impedisce due profili applicabili di pari priorità per lo stesso utente; (c) lo spareggio su un attributo del modello (il tipo del profilo) | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: «il ripiego non allarga mai» vale per preset e permessi, e la parità non può più nascere |
| Q29 | La forma delle date per chiave dal lato della preferenza: lo snapshot (scritto dal DB, Q1) e l'ignorato sono una colonna ciascuno; le chiavi della dashboard non sono elencate | Q1, Q3, Q4; BE7 | (a) Snapshot e ignorato diventano un JSONB `{chiave: data}` ciascuno, chiavi validate dal guard di forma (Q6); (b) una colonna per chiave e per dato | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: le chiavi sono le stesse della `configurazione`, una chiave nuova non chiede DDL. Le chiavi della dashboard (`widget`, `dimensione_max`) si dichiarano nella decisione |
| Q30 | Che cosa garantisce «un preset per posto» quando `is_default` si ritira: gli indici `uq_*_default` sono `WHERE is_default = true` | Q26; §3.7 | (a) UNIQUE parziale `WHERE attivo` sulle stesse chiavi; lo scambio con la bozza si fa spegnendo il vecchio prima di accendere la bozza (un indice parziale non si differisce); (b) UNIQUE pieno, e la bozza vive altrove | ✅ **Deciso da Tid il 2026-11-20.** **(a)**, con l'ordine dello scambio scritto nella guida e nel messaggio dell'UNIQUE |
| Q31 | Lo stesso strumento per «il catalogo ha sempre un default» (U18, constraint trigger differito) e «la home non è mai vuota» (U32, presidio `dbops`) | Q20 (il motivo) | (a) Constraint trigger differito per tutti e due; (b) presidio `dbops` per tutti e due; (c) strumenti diversi, con la ragione sul modello scritta | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: il differito risolve i passaggi intermedi, e dopo Q19 tutti e due i cataloghi li scrive solo l'owner |
| Q32 | Una vista che perde colonne (DDL sulla vista), il caso di U27 che Q16 non copre | Q16 | (a) Un presidio `dbops` che confronta le colonne di ogni lista con la sua relazione; (b) limite accettato, dichiarato nella guida, e resta il pgTAP sul seed | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: copre le liste create dall'app, che il pgTAP sul seed non vede |
| Q33 | La sede di «la data del contenuto si sposta solo se il contenuto cambia», oggi violata dal DELETE + INSERT identico del BE (BE3) | BE3 | (a) Nel DB: ~~il trigger delle righe del preset passa per istruzione, con le transition table, e confronta l'insieme vecchio col nuovo~~ (il mezzo non regge: Q37); (b) il BE fa il diff | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: la regola vale per ogni scrittore; BE3 si ritira. Il mezzo è quello di Q37 |
| Q34 | Chi traduce in codice il campo sorgente che il FE usa come `col` (Q7) | Q7; BE20 | (a) Il guard di forma rifiuta un `col` che non è un codice della lista, e il BE traduce; (b) il guard traduce, riscrivendo il valore | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: un guard non riscrive in silenzio ciò che riceve |
| Q35 | I residui senza decisione: BE9 (chi applica oggi l'ordinamento risolto); U38 (la variabile utente non numerica); U22 (le preferenze della lista spenta, e il messaggio alla riaccensione rifiutata da Q16) | Q13, Q16; BE9, U38 | Una risposta per voce | ✅ **Deciso da Tid il 2026-11-20.** BE9: lo verifica la sessione BE prima del giro 2 e la voce diventa una richiesta chiusa; U38: un codice d'errore dedicato, non il 22P02; U22: le preferenze restano e si sospendono con la lista, la riaccensione rifiutata nomina le colonne orfane |
| Q36 | La dimensione del giro 1: U1-U9, Q26, il cambio di modello di Q4, quattro ricadute BE | Q24 | (a) Giro 1a (z90, snapshot, `preset_base`, Q28, `is_default` e Q30) e giro 1b (date per chiave, Q29, esito «base cambiata»); (b) un giro solo | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: due apply più piccoli, e 1b parte con la forma di Q29 già decisa |
| Q37 | La sede di «la data si sposta solo se la composizione cambia»: la forma di Q33 (trigger per istruzione con le transition table) non vede il DELETE + INSERT come un'operazione sola, e un constraint trigger differito esiste solo per riga (provato il 2026-11-20, §3.1-ter) | **Riapre Q33** (2026-11-20): ne tiene la sede (il DB) e cambia il mezzo | (a) Un'impronta della composizione sul preset (`composizione_impronta`, dal BB `ui.fn_preset_impronta`) e un constraint trigger differito per riga: a fine transazione la data si sposta solo se l'impronta è cambiata; (b) il diff lo fa il BE (l'opzione (b) di Q33, BE3 torna aperta); (c) il BE scrive con un `MERGE` che tocca solo le righe diverse: è (b) con un altro strumento | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: la regola vale per ogni scrittore, come voleva Q33, e toglie anche la personalizzazione finta del seed. Costo: una colonna di stato derivato e un trigger che scatta al commit |
| Q38 | L'ignorato del banner, ora che lo snapshot lo scrive il DB: il flag dipende solo dal più recente fra snapshot e ignorato, e «Ignora» può essere un riallineamento (§3.1-ter) | **Riapre Q29** (2026-11-20) per la sola parte dell'ignorato; Q1 e Q3 restano | (a) `preset_aggiornato_ignored_at` si ritira dalle due preferenze; «Ignora» è una scrittura che nomina `preset_base_id`, e il trigger riallinea lo snapshot; le righe di oggi convertono lo snapshot a `max(snapshot, ignorato)`; (b) come Q29: anche l'ignorato diventa `jsonb` per chiave, e lo scrive il BE | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: una colonna in meno, nessun JSONB scritto dall'app da validare (la validazione di Q29 aspetterebbe il guard di forma del giro 2), e BE7 si riduce a una scrittura che il BE già sa fare |
| Q39 | La forma della data per chiave dal lato del preset (Q4 la vuole per chiave, Q29 dà la forma solo per la preferenza) | **Completa Q4** | (a) `contenuto_aggiornato_il` resta col suo nome e diventa `jsonb` `{chiave: data}`, con le chiavi della `configurazione`; (b) una colonna per chiave (`colonne_aggiornate_il`, `ordinamento_aggiornato_il`, …) | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: le chiavi sono quelle della preferenza e dello snapshot, così il confronto è chiave contro chiave; una funzione sola regge le due tabelle; la riga 5 del registro del seed non cambia. Il nome dice ancora «una data»: lo dichiara il COMMENT |
| Q40 | Il campo sorgente che il FE manda come `col`, quando due colonne della stessa lista hanno lo stesso `campo_sorgente`: il modello lo ammette, e la traduzione del BE (Q34) non sa quale colonna sia (§3.2-bis) | **Completa Q34** | (a) Un UNIQUE parziale `(lista_id, campo_sorgente)` sulle colonne con il campo valorizzato: il campo dice sempre una colonna, e la traduzione è una funzione; (b) il FE manda il codice (lo ha, dalle colonne risolte) e la traduzione del BE si ritira: Q34 resta per il guard, cambia chi scrive; (c) la traduzione rifiuta il campo ambiguo | ✅ **Deciso da Tid il 2026-11-21: (b).** La verifica del team BE (§3.2-bis, «Verifica per Q40») dice che nessun componente FE scrive `col`: il codice lo scrive chi scrive, la traduzione del BE (BE20) non nasce, e l'UNIQUE di (a) non serve. Q34 resta per il rifiuto del guard |
| Q41 | La sede dei legami di U14 sulle composizioni: `lista_preset_colonna` e `dashboard_preset_widget` non portano la lista né la dashboard, e una FK composita le chiede | U14, Q8 | (a) Una colonna `lista_id` (`dashboard_id`) sulla composizione, scritta dal DB dal preset, e le FK composite verso il preset, la colonna e il pool: il legame vale per costruzione da tutti e due i lati (anche un cambio di `lista_id` della colonna); (b) un guard sulla composizione e un lucchetto su `lista_colonna.lista_id`: nessuna colonna in più, ma ogni lato ha il suo trigger | ✅ **Deciso da Tid il 2026-11-21: (a)**, come raccomandata: un vincolo non ha un lato dimenticato; il costo è una colonna derivata per tabella, che il BE non scrive |
| Q42 | Il codice di una voce della preferenza (o di `col`) al guard di forma: una colonna della lista in qualsiasi stato, o solo accesa; per la dashboard un widget del pool, o un widget qualsiasi | Q6, Q34 | (a) Della lista in qualsiasi stato, e del pool: una colonna spenta si sospende e torna (Q13), e la preferenza che la nomina resta valida; il resolver già la salta; (b) solo accesa: una preferenza scritta prima che la colonna si spenga viene rifiutata alla prima riscrittura | ✅ **Deciso da Tid il 2026-11-21: (a)**, come raccomandata: una colonna spenta si sospende e torna (Q13), e la preferenza che la nomina resta valida |
| Q43 | Chi cambia per primo nel ritiro di filtri e ordinamento (Q38/Q39 §6, passo 2): il `DROP COLUMN filtri_default` rompe la lettura admin dei preset (`ui_admin_repository.py:82`) finché il BE non la toglie (§3.2-bis, «Il riallineamento del 2026-11-21») | **Completa Q38 §6**, che dava l'ordine (1) BE/FE, (2) DB, (3) BE | (a) Il BE fa prima la parte di (3) che non aspetta il DB (whitelist e lettura admin, R-BE3), poi l'apply: nessuna finestra rotta; (b) il DB per primo, come scritto in Q38 §6: la lista admin dei preset dà errore fra l'apply e il BE, rottura accettata in sviluppo | ✅ **Deciso da Tid il 2026-11-21: (a)**, come raccomandata: il pezzo del BE è piccolo e non dipende dal DB, e (b) rompe un'API senza guadagno. L'apply del giro 2 aspetta R-BE3 |
| Q44 | Il vocabolario degli usi di una misura (`COMPATTA`, `PAGINA`): il CHECK di `misure_pagina.uso_default`, la colonna nuova di `lista_definizione` (U20) e il constraint trigger di U18, che li deve elencare | U20, U18 | (a) Un enum `ui.uso_misura_pagina`, come `ui.ambito_preset`, per le due colonne; il trigger lo legge con `enum_range`; (b) un CHECK per colonna e l'elenco nel trigger: tre copie | ✅ **Deciso da Tid il 2026-11-21: (a).** La firma di `ui.fn_misura_pagina_default` resta (`varchar`): cambia solo il confronto |
| Q45 | Il tetto 1-100 di `dashboard_preset.dimensione_max` (Q12): ha già una sede, `ui.fn_dimensione_max_ammessa` | Q12 | (a) `CHECK (dimensione_max IS NULL OR ui.fn_dimensione_max_ammessa(dimensione_max))`; (b) un CHECK letterale `BETWEEN 1 AND 100`, il 100 in due sedi | ✅ **Deciso da Tid il 2026-11-21: (a).** Il BB è `IMMUTABLE` e nasce con un numero minore (§11.14) |
| Q46 | La colonna nuova `lista_definizione.uso_misura` nel registro del seed (riga 3, per colonna, QU1) | QU1 | (a) Del software: dove il FE mostra la lista lo decide il codice; (b) dell'installazione, come `ricerca_min_caratteri` | ✅ **Deciso da Tid il 2026-11-21: (a).** |
| Q47 | La dichiarazione dal lato della lista che Q15 chiede quando il DB non sa quali liste sono documentali: `config.sorgenti` non porta la lista, `lista_definizione` non porta la sorgente (§3.4-bis) | **Completa Q15** | (a) Un flag del software `lista_definizione.legge_lineage` (NOT NULL, `false`): «il BE unisce la sintesi della lineage alle righe»; si scrive solo dal migratore, nel guard di U23. (b) Una FK `lista_definizione.sorgente_id` verso `config.sorgenti` (DOCUMENTO): la lista dichiara quale documento mostra, e la lineage si ammette dove c'è. **Raccomandata (a)**: il guard chiede proprio quella capacità, e una lista può mostrare documenti di più sorgenti (i cruscotti dei documenti aperti); la FK dichiara di più di ciò che serve, e quel di più resta senza lettore | ✅ **Deciso da Tid il 2026-11-21: (a).** |
| Q48 | Chi verifica il nome di una colonna `LINEAGE`, ritirata la dipendenza del guard di `ui` da `vendite.vw_documento_lineage_sintesi_colonne` (Q15) | **Completa Q15** | (a) Il presidio `dbops` di Q32, che `vendite` la può leggere, e il pgTAP `vendite/test-colonne-lineage-liste-v1` per il seed; il guard di `ui` controlla solo che la lista dichiari la lineage. (b) Il guard di `ui` continua a leggere la vista di `vendite`: Q15 resta a metà. **Raccomandata (a)**: la dipendenza esce da `ui`, e un nome sbagliato lo vede il presidio anche sulle liste dell'app | ✅ **Deciso da Tid il 2026-11-21: (a).** |
| Q49 | La gemella di Q13 sulle dashboard: `dashboard_preset.dashboard_id` tiene ancora il guard ATTIVO, quindi una dashboard con preset accesi non si spegne, mentre da questo giro una lista sì (§3.4-bis, trovato scrivendo il giro 4) | **Completa Q13** | (a) La stessa forma nel giro 5: la FK fra le eccezioni ATTIVO, la dashboard spenta sospende i suoi preset. (b) Resta il blocco, e la differenza fra liste e dashboard si dichiara. **Raccomandata (a)**: liste e dashboard sono gemelle, e il giro 5 apre comunque quelle tabelle | ✅ **Deciso da Tid il 2026-11-21.** **(a)**: entra nel giro 5 (§3.5) |
| Q50 | U32 con Q31 (constraint trigger: ogni dashboard accesa ha nel pool un widget acceso senza area né azione) **revoca** la decisione del 2026-07-22 ([brief-db-dashboard-home-rimuovi-benvenuto](../work-done/2026/brief-db-dashboard-home-rimuovi-benvenuto.md), validata a video): `home.benvenuto` è spento di proposito, e il «mai vuota» lo tiene il FE con due stati vuoti che dicono il vero. Le schede U32 e Q31 non citavano quel brief (§3.5-bis, trovato col piano del giro 5) | **Q20, Q31** | (a) Resta la decisione di luglio: niente trigger; la regola si scrive com'è, «nessun vuoto muto, e lo stato vuoto lo dice il FE», nel COMMENT di `dashboard_definizione`, nella pagina `manual/` di `widget` (la riga di «⚠️ Che cosa oggi non copre» diventa una regola), nel commento del catalogo grezzo del resolver e nell'header di `test-fn-resolve-dashboard-config`; Q31 resta per U18 soltanto. (b) Q31 com'è: il constraint trigger su pool, widget e definizione, e `home.benvenuto` riacceso nel CSV (la card torna a video per tutti); ogni fixture che fabbrica una dashboard accesa ci mette un widget senza area né azione. **Raccomandata (a)**: è una decisione presa sul modello e validata a video, e una card che non dice niente soddisfa la regola nella forma e non nella sostanza | ✅ **Deciso da Tid il 2026-11-21.** **(a)**: resta la decisione di luglio, niente trigger per U32 |
| Q51 | U40: sulle liste il cui default del repository ha più criteri (disponibilità, piano d'inventario, code dei resi), il preset a una colonna cambierebbe l'ordine dei pari | (a) si accetta il nuovo ordine; (b) quelle liste restano senza preset; (c) il repository tiene i suoi criteri successivi come spareggio quando la colonna del preset è la sua prima. Il team BE propone (c): l'ordine resta quello di oggi e la sede è una | ✅ **Deciso da Tid il 2026-11-22.** **(c)**: U40 vale anche per quelle liste; i repository, BE30 (✅ già così, presidiato) |
| Q54 | Il software toglie una riga dalla composizione di un preset personalizzato, e il seed (`a00`) riporta `composizione_impronta` a OLD: l'impronta resta indietro e la prima scrittura dell'installazione, anche uguale, sposta `colonne` (trovato dal `/verifica-db` dell'1b, §3.1-ter) | **Completa Q37** e QU1 del brief del seed | (a) Le colonne che il DB deriva da una tabella figlia: il seed le giudica quando scrive l'installazione, ma non le riporta a OLD quando scrive il software. Cambia il meccanismo del seed (changeSet nuovo, BB di `script`); (b) resta un limite dichiarato (oggi nella pagina `manual/`). **Raccomandata (a)**: l'impronta torna vera nel momento del ritiro | ✅ **Deciso da Tid il 2026-11-22.** **(a)**: il seed giudica le colonne derivate quando scrive l'installazione, e non le riporta a OLD quando scrive il software. Un changeSet sul BB del seed in `script`, nel giro 7, con un pgTAP che costruisce il ritiro e la riscrittura uguale dopo; la pagina `manual/` di `trgfn_preset_riga_tocca_preset` perde il limite dichiarato |
| Q55 | Una colonna della lista (o una card del pool) si ritira mentre una preferenza la nomina: la voce resta, e il guard di forma rifiuta ogni scrittura che conserva `colonne` (`widget`), anche il cambio della sola misura (trovato dal `/verifica-db` del giro 2, §3.2-bis; provato sullo scratch) | **Gemella di U16** (la misura, giro 3) e di Q42 (a) | (a) Come U16: il ritiro della colonna (`AFTER DELETE` su `ui.lista_colonna`) e della card dal pool (`AFTER DELETE` su `ui.dashboard_widget`) tolgono la voce dalle preferenze che la nominano, nella stessa istruzione; due changeSet nuovi e un pgTAP che costruisce il ritiro e il salvataggio dopo. (b) Il guard giudica l'appartenenza al contenitore solo sulle voci nuove rispetto a OLD: la riga resta con la voce morta, che il resolver salta. **Raccomandata (a)**: la riga torna vera nel momento del ritiro, come per la misura, e il guard resta una regola sola | ✅ **Deciso da Tid il 2026-11-22.** **(a)**, e per gli UPDATE (lista della colonna, dashboard e card del pool, codice della card) i lucchetti, non un ramo del trigger: §3.2-bis, «Q55, il giro» |
| Q56 | Il service delle colonne (`backend/apps/ui/services/lista_colonna_admin_service.py`, `_richiedi_colonna_non_in_uso`) rifiuta la cancellazione di una colonna che una preferenza nomina (`E_UI_COLONNA_IN_USO`). Con Q55 il database toglie la voce da sé (trovato scrivendo Q55, §3.2-bis) | **Da Q55** | (a) Il BE ritira il rifiuto per le preferenze (resta quello dei preset, che la FK tiene): cancellare una colonna ritira la voce, come fa già il migratore. (b) Il rifiuto resta, come scelta di prodotto del pannello admin («spegnere, non cancellare»): la regola vive solo nel BE, e il migratore passa lo stesso. **Raccomandata (a)**: è un rifiuto senza più una ragione nel modello, e la stessa cancellazione darebbe due esiti secondo chi la fa | ✅ **Deciso da Tid il 2026-11-22.** **(a)**: BE32 (§6) |
| Q57 | Il ritiro di una card dalle preferenze (`ui.trgfn_voce_ritira_dalle_preferenze`, `20261122-26`) cerca il codice in `ui.widget`: se la card esce dal pool e dal catalogo nello stesso statement, il codice è NULL e la voce resta, e la preferenza non si salva più (dal `/verifica-db` di Q55, 2026-11-22, §3.2-bis) | **Aperta** | (a) Un changeSet nuovo: il ramo della dashboard toglie dalle preferenze di `OLD.dashboard_id` ogni codice che il pool non ha più, con `ui.fn_configurazione_senza_codici` (la domanda della bonifica, ristretta alla dashboard), e un caso pgTAP con la CTE. (b) Si lascia: lo raggiunge solo chi scrive il catalogo, in un solo statement. **Raccomandata (a)**: il modello ammette il caso, e il difetto è quello che Q55 chiude | ✅ **Deciso da Tid il 2026-11-22.** **(a)**: un changeSet nuovo, in una sessione DB nuova |
| Q58 | `ui.fn_get_misure_pagina` scrive a mano i due usi (`default_compatta`, `default_pagina`): un valore nuovo di `ui.uso_misura_pagina` avrebbe il suo default nel catalogo, ma l'applicazione non lo vedrebbe (dal `/verifica-db` del giro 3, 2026-11-22, §3.3-bis) | **Aperta** | (a) Un changeSet sulla funzione, con i default per uso costruiti da `enum_range` in un oggetto nuovo, e la richiesta al BE/FE di leggerlo (le due chiavi di oggi restano finché il BE non passa). (b) Si dichiara debito: l'enum cambia solo con un changeSet, che allora tocca anche la funzione. **Raccomandata (a)**: è la sede del vocabolario fuori dall'enum che Q44 voleva togliere | ✅ **Deciso da Tid il 2026-11-22.** **(a)**: un changeSet sulla funzione e la richiesta al BE/FE (una voce in §6, scritta col piano), in una sessione DB nuova |
| Q60 | Fuori da `ui`. Dal giro 6a `ui.fn_lista_colonne_ricerca_full` legge `app.current_user_id` con un controllo suo: un valore che non è un intero dà `E_UI_CHIAMATA_NON_VALIDA`. Una ventina di funzioni di `script`, `config` e `magazzino` (i guard di azione, livello e super admin, `fn_get_parameter_di_sessione`, le credenziali) la leggono ancora con `NULLIF(…)::integer`, e lo stesso guasto lì dà il 22P02 grezzo. Due risposte allo stesso guasto (dal `/verifica-db` del giro 6, 2026-11-22, §3.6-quater) | **Aperta** | (a) Un BB in `script` per l'utente di sessione (GUC assente o vuota: NULL; non intera: un codice TECNICO), letto da tutte, in un brief suo perché tocca più domini. (b) Si lascia: Q35 chiedeva il codice per la sola ricerca. **Raccomandata (a)**: è la regola del 2 su una lettura già ripetuta, e `fn_lista_colonne_ricerca_full` passerebbe al BB nello stesso giro | ✅ **Deciso da Tid il 2026-11-22.** **(a)**: il BB in `script`, letto da tutte le funzioni che leggono `app.current_user_id`, con le copie ritirate nello stesso giro. Tocca più domini: va in un brief nuovo, che dichiara i brief vicini verificati e chiede al BE di censire chi conta sul 22P02 di oggi ~~in un brief nuovo~~ **Rivisto da Tid il 2026-11-23: si fa qui**, come giro 8, per non lasciare aperto un punto che passa di brief in brief. Il censimento sul catalogo di dbdev (2026-11-23) è più largo della «ventina»: circa 75 funzioni in nove schemi (magazzino 20, vendite 19, script, anagrafiche, dbops, catalogo, pagamenti, config, ui), 4 viste di `vendite` e 177 policy RLS leggono `NULLIF(current_setting('app.current_user_id', true), '')::integer` |

## 8. Giro 0 — la documentazione, 2026-11-18 (fatto)

L'ha scritto la sessione DB su richiesta di Tid, con quattro agenti per l'area dello schema (A catalogo delle liste, B
preset e risoluzione, C misure, D dashboard) e uno per la guida (E). Le pagine sono lette dai corpi
(`pg_get_functiondef`, `pg_get_triggerdef`), da `pg_constraint`, dai COMMENT e dai GRANT di dbdev, dalle schede
auto-generate e dai pgTAP. Descrivono il comportamento di oggi, difetti compresi. Ogni difetto sta al presente in una
sezione «⚠️ Che cosa oggi non copre», che si toglie quando il giro che lo corregge è applicato. I difetti di classe A (U1,
U10, U15) sono verificati sul catalogo anche dalla sessione che coordina.

### 8.1 Che cosa è scritto

* **Le 32 pagine `docs/it/dbzero/ui/manual/`.** Le 28 esistenti sono riscritte nella cornice: nove erano nel formato
  vecchio (titolo `#`, più `##`, firma e DDL in blocchi `sql`) e sono rifatte da capo; 24 non avevano la firma. Le
  quattro nuove: `trgfn_preset_contenuto_aggiornato`, `trgfn_preset_riga_tocca_preset` (descritte per le due famiglie,
  liste e dashboard), `trgfn_ui_lista_preset_guard_pagina_dimensione`,
  `trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione`.
* **`guide/configurazione-liste.md`**, riallineata al codice (§8.2).
* **`mappa-concentrica.md`:** il link alla §12 della guida, che aveva cambiato titolo. La data del documento non è
  toccata: dice a quando valgono le sue misure, e il link non è una misura.
* **Nessun blocco comune.** Le tre famiglie hanno regole diverse.

### 8.2 Le parti stantie e false tolte

* **Comuni a tutte le pagine:** «(scritta il 30-09-2026)» e «(latest review 18-08-26)» come primo paragrafo, che
  finivano nell'indice; Vedi anche senza `>` o con etichette in grassetto; firme, parametri, tabelle di colonne e di
  ritorno, DDL ed esempi; DEF-n, «brief §n», id di changeSet nel corpo.
* **Di contenuto, nelle pagine:**
  * lo z90 delle liste «azzera solo quando diventa NULL»: scatta a ogni cambio e azzera due campi; lo z90 delle dashboard
    «a differenza di quello delle liste…»: i due corpi sono identici;
  * il preset di base «il primo con colonne, di ruolo…»: per il ruolo conta solo il primo (U3); «AD_HOC prio 1 prevale
    su REPARTO/PORTALE prio 2»: PORTALE è 3;
  * «unico default per combinazione»: conta anche i preset spenti; «la preferenza si legge sempre completa in una
    query»; «la lettura passa sempre dalla funzione» (il BE legge la tabella); «una preferenza senza chiavi si cancella»
    (lo fa il BE, il DB la ammette);
  * «vincolo di seed» per i widget del preset fuori dal pool: è un buco senza presidio (U14);
  * il guard multi-emittente «impedisce che venga acceso»: rifiuta all'app ogni cambio; `valida_vista_sql` «solo UPDATE
    OF vista_sql, attivo» e «nome grezzo come relname»: parte anche su `schema_dati` e cerca nello schema della lista;
  * `misure_pagina`: «sede unica per DB, BE e FE», falso (U15, BE10); la tabella «oggi 10/25/50/100», una fotografia;
    la ricetta per spostare un default in due passaggi, che fra l'uno e l'altro lascia il catalogo senza default; «una
    misura non si toglie finché un preset la usa», che taceva le preferenze;
  * il CHECK dell'azione «impone il sorgente NULL»: impone solo che l'azione non si esporti.
* **Di contenuto, nella guida:**
  * la cascata: l'emittente era prima del ruolo, ed era descritta come «intera preferenza»: è per chiave; il catalogo
    grezzo prende tutte le colonne accese, non solo le `informazione`;
  * `LETTURA` «visibile ma non personalizzabile»: è visibile e non esportabile;
  * lo spegnimento della lista come un gesto unico (U22); la cancellazione di una colonna «a cascata» sui preset (U30);
  * «i permessi sono sempre restrittivi»: vince il profilo più specifico, e su una colonna sensibile il permesso apre;
  * il banner del preset aggiornato e l'export «in roadmap»: esistono; l'export «nell'ordine di `ordine_default`»: è
    nell'ordine dell'utente, senza le colonne nascoste né quelle in LETTURA;
  * la modale «permette di fissare le colonne»: non lo permette;
  * il bollino multi-emittente «oggi spento su tutte le liste»: è acceso su più liste;
  * la §12 «Roadmap» con DEF-n e un link a `work-in-progress/`: diventa «Che cosa le liste oggi non fanno», cinque
    limiti al presente; le funzionalità chiuse entrano nella sezione del loro tema; le due spiegazioni ripetute (lista
    in sviluppo, fallback i18n) diventano una;
  * aggiunte le misure di pagina (§2.6), che la guida non descriveva.

### 8.3 Le verifiche

* Su tutte le 32 pagine passano i sei controlli di `standard-guide.md` §«Verifica di una pagina `manual/`», rilanciati
  dalla sessione che coordina il 2026-11-18. In più: nessun link `/dbzero/…` o `/guide/…` morto, e la data è il 18
  novembre 2026 ovunque. L'unico blocco di codice è un `mermaid` in `fn_resolve_lista_config`.
* La guida passa la checklist di `standard-guide.md`; l'unico anchor esterno cambiato è quello corretto nella mappa
  concentrica.
* **La doc auto-generata non è rigenerata** (passo 3): le schede delle quattro funzioni con la pagina nuova non la
  includono ancora, e `ui/index.md` porta ancora «(scritta il 30-09-2026)» come descrizione delle misure.
* La build della doc non è lanciata.

## 9. Fuori perimetro — segnalazione per Tid

**Le dashboard non hanno una guida.** In `docs/it/guide/` nessuna guida descrive le dashboard di `ui` (catalogo dei
widget, pool, preset, contatori, permessi per area e azione): `configurazione-liste` parla solo delle liste, e
`cruscotti-fatturazione` parla d'altro. Oggi il significato sta solo nelle otto pagine `manual/`. Deciso da Tid il
2026-11-19 (Q25): una guida sua, `configurazione-dashboard`, che rimanda a `configurazione-liste` per il meccanismo
comune (cascata, preset di base, banner) senza ricopiarlo. Si scrive **a fine giro 5**, quando la home ha preso la
forma corretta. La domanda «le dashboard
seguono la stessa strada delle liste?» è aperta anche in
[sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md).

## 10. Alla chiusura

* Ogni pagina `manual/` toccata passa la verifica di `standard-guide.md` con la data aggiornata, e perde la riga di «⚠️
  Che cosa oggi non copre» del difetto chiuso.
* I pgTAP nuovi costruiscono i propri soggetti: nessuno itera su ciò che c'è.
* Il brief va in `work-done/` quando i giri sono applicati e le ricadute BE/FE chiuse o passate a un brief BE.
