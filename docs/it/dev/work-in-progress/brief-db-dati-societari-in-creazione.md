# Brief DB — Dati societari in creazione: la porta di creazione non scrive tutta la sezione

## ⏭️ Chi riparte — aggiornato al 2026-10-14

**Riparte: Tid, per E-1 (§4). Poi il team DB scrive (§5), e dopo l'apply la sessione BE/FE si allinea (§6).**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | decide E-1 (dove si scrive la sezione per la ditta individuale) | §4 | — |
| 2 | team DB | changeSet, pgTAP, manuali | §5 | 1 |
| 3 | Tid | apply e corsa pgTAP | — | 2 |
| 4 | sessione BE/FE | `crea_soggetto_pg` / `_create_pf`, via la prop `showDataCostituzione` | §6 | 3 |
| 5 | Tid | collaudo a video: SC e DI create con la sezione intera | §6 | 4 |
| 6 | chi chiude | archiviazione, riga di PROJECT_CONTEXT, D34 nel registro DB | — | 5 |

Decisioni aperte di Tid: **E-1**. Lavoro da committare: questo file (2026-10-14).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-14, chiudendo
> `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md` (§9.5, richiesta della sessione BE).
> **A chi:** team DB; poi BE/FE (§6).
> **Stato:** 📝 aperto, non iniziato.

## 1. Il difetto, sul modello

Dal 2026-10-10 la sezione «dati societari» ha **una porta sola**, il verbo
`anagrafiche.fn_scrivi_dati_societari`, che riceve lo **stato intero** (B-1, B-2, B-4 del brief
d'origine). In modifica la sezione arriva intera. **In creazione no**, per due strade:

| Natura | Porta di creazione | Cosa si perde |
| --- | --- | --- |
| SP, SC, ENC | `anagrafiche.fn_crea_soggetto_pg` | la **data di costituzione**: la funzione chiama il verbo con `p_data_costituzione := NULL` e non ha un parametro per riceverla |
| DI (ditta individuale, `dati_societari_policy = OPTIONAL`) | `anagrafiche.fn_crea_soggetto_pf` | **tutta la sezione**: la funzione non conosce i dati societari |

Fonti: corpo vivo di `fn_crea_soggetto_pg` (rev `20261011-01`) e firma di `fn_crea_soggetto_pf` (rev
`20261009-26`), doc auto-gen letta il 2026-10-14.

### 1.1 Ditta individuale: la sezione si perde in silenzio

Il FE mostra la sezione quando la natura non la esclude (`useSoggettoForm.showDatiSocietari`:
policy diversa da `NONE`), quindi anche per la DI. In creazione `SoggettoDrawer.handleSave` mette
`dati_societari` nel payload. Ma `SoggettiService.create_soggetto` manda la DI in `_create_pf`, che
la chiave non la legge, e `fn_crea_soggetto_pf` non ha parametri per riceverla. L'operatore compila
forma, REA, canale FE e PEC, legge «creato», e alla riapertura la sezione è vuota.

Lo stesso difetto che la Parte B del brief d'origine ha chiuso in modifica («salvato», e alla
riapertura i valori vecchi). In creazione è rimasto aperto sulla porta delle persone fisiche.

### 1.2 Data di costituzione: oggi il FE la nasconde

Per non perderla in silenzio, il FE offre la data **solo in modifica** (`DatiSocietariForm.vue`,
prop `showDataCostituzione`). È un ripiego: la regola «in creazione questo campo non c'è» non è del
dominio, è un limite della porta.

## 2. Che cosa NON cambia

- Il verbo resta l'unica sede della scrittura e non cambia firma. Le regole (forma ammessa dalla
  natura, REA e capitale per policy, canale FE) restano nei suoi trigger.
- Nessuna regola nuova, nessun codice di errore nuovo.

## 3. Che cosa si propone

**Per `fn_crea_soggetto_pg`:** un parametro `p_data_costituzione` **in coda**, con `DEFAULT NULL`,
passato al verbo al posto del `NULL`. Tipo ancorato alla colonna
(`anagrafiche.dati_societari.data_costituzione%TYPE`, §7e di `linee-guida-sql.md`).

⚠️ Per il team DB: cambia la firma, quindi `CREATE OR REPLACE` non basta. Serve `DROP FUNCTION` della
firma vecchia e `CREATE`; altrimenti nascono due overload e una chiamata con i soli parametri vecchi
diventa ambigua. Dopo il `DROP` vanno rimessi `COMMENT` e privilegi. Censire i chiamanti: il BE
(`soggetti_repository.py`, parametri nominati) e 4 pgTAP (`test-soggetti-sesso-policy-v1`,
`test-fn-scrivi-dati-societari-v1`, `test-emittenti-fiscali`, `dbops/test-character-n-v1`). Nessuna
funzione del DB la chiama (doc auto-gen, 2026-10-14).

**Per la ditta individuale:** E-1.

## 4. Decisioni attese da Tid

| # | Domanda | Proposta della sessione DB |
| --- | --- | --- |
| **E-1** | **Dove si scrive la sezione di una DI che nasce.** | **(a)** `fn_crea_soggetto_pf` riceve i dati societari, con parametri in coda, e chiama il verbo come `fn_crea_soggetto_pg` (B-4): la creazione è **una** chiamata, atomica nel DB, e le due porte si comportano allo stesso modo. **(b)** Il BE, nella stessa transazione, crea la persona fisica e poi chiama il verbo: niente firma nuova, ma la creazione di una DI diventa un'orchestrazione del BE, e le due porte divergono. ⭐ Proposta: **(a)**. È la stessa scelta già fatta per le società, e il «soggetto più la sua sezione» resta una sola operazione del DB. |

## 5. Lavoro DB (dopo E-1)

- changeSet `20_code/anagrafiche`: `fn_crea_soggetto_pg` con `p_data_costituzione` (§3);
- con E-1 (a): changeSet `20_code/anagrafiche` per `fn_crea_soggetto_pf`, con i parametri della
  sezione in coda e la chiamata al verbo, solo se la natura ammette i dati societari e i parametri
  sono passati (la regola `REQUIRED`/`NONE` resta al guard `trgfn_soggetti_guard_dati_societari_required`);
- pgTAP: SC creata con data di costituzione, letta dalla tabella; DI creata con forma «Ditta
  individuale» e canale FE; DI creata **senza** sezione (policy `OPTIONAL`); PR con la sezione →
  rifiuto dal guard della natura, come oggi in modifica;
- manuali `fn_crea_soggetto_pg`, `fn_crea_soggetto_pf`, `dati_societari`.

## 6. Ricadute BE/FE (dopo l'apply)

- **BE:** `crea_soggetto_pg` e `_create_pg` passano `data_costituzione`. Con E-1 (a), `_create_pf`
  legge la chiave `dati_societari` (stesso contratto di `_valida_dati_societari`) e la passa a
  `crea_soggetto_pf` con parametri nominati. Test sul DB vero: SC con data, DI con la sezione.
- **FE:** via la prop `showDataCostituzione` (il campo si mostra sempre, come gli altri della
  sezione). Il ramo di creazione di `handleSave` già manda la sezione: niente da cambiare.
- ⛔ Finché il DB non è pronto, BE/FE non toccano niente.

## 7. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-14 | Aperto chiudendo `brief-db-dati-fiscali-e-societari-del-soggetto` (§9.5, richiesta della sessione BE sulla data di costituzione). Rileggendo la creazione: anche la DI perde la sezione (§1.1), entra qui. In attesa di E-1. |
