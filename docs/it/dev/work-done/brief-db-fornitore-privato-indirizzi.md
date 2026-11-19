# Brief DB — Il privato può essere fornitore, senza inventarsi una sede legale

## ⏭️ Chi riparte — ✅ CHIUSO il 2026-11-19, archiviato su richiesta di Tid

**Non riparte nessuno.** Il lato DB è finito e committato (giri 1 … 7); R-5 … R-8 del BE/FE sono fatti, verdi sul DB
vero e documentati (§16), e vanno nel commit di Tid insieme a questa archiviazione. Restano fuori, ciascuno nella
sua sede: il documento passivo del fornitore privato (§7, sviluppo acquisti, rimando in PROJECT_CONTEXT) e la copia
di un indirizzo verso la chiave del drawer
([brief-db-copia-indirizzo-destinazione](../work-in-progress/brief-db-copia-indirizzo-destinazione.md), D-1 … D-3
decise il 2026-11-19).

Storia della ripartenza fino al 2026-11-18:

Il giro 7 (§15, Tid 2026-11-18): il titolare di un indirizzo è identità, due lucchetti di colonna; l'upsert fuori
transazione di `test-soggetti-ruoli-indirizzi-required` tolto; applicato su dbdev il 2026-11-18, pgTAP verdi, doc
auto-generata rigenerata, e committato (2026-11-18). Il giro 6 (§14: la lettura del
form prende il nome `fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`, tre pgTAP sul builder, i COMMENT delle
sorelle) è applicato su dbdev, pgTAP verdi, doc rigenerata, e committato (`120312f74e`, 2026-11-18). Il giro 5
(`20261116-39 … -43`: gli indirizzi che una natura proposta chiede, per il form del cambio di natura; il cambio li
porta con sé, scritti dal backend nella stessa transazione) è applicato su dbdev il 2026-11-17, pgTAP verdi, e
committato. Il giro 4 (`20261116-29 …
-38`, il requisito degli obbligatori sulla natura col ripiego, e il controllo anche alla cancellazione, al cambio di
tipo e al cambio di natura) è applicato su dbdev il 2026-11-17, pgTAP verdi, doc auto-generata rigenerata, e
committato. Il giro 3 è applicato su dbdev il 2026-11-17, pgTAP del §11.2 verdi, doc auto-generata rigenerata, e committato. R-1 … R-4 (§9.4) sono fatti dal team BE/FE e committati
(`0664df90c3`, PR #155, 2026-11-17): il picker del ruolo da assegnare non è più rotto, e la chiave di R-2 c'è; la
doc auto-generata è rigenerata. Il builder del privato (`20261116-22`, §10) è applicato su dbdev e committato
(`8311f9a078`) il 2026-11-17, pgTAP del §10.2 verdi. I giri 1
e 2 (`20261116-17 … -21` e tre CSV) sono applicati su dbdev e committati (`9a6db84d2b`) il 2026-11-17, coi pgTAP del §9.2 verdi; il censimento di D-5, ripetuto prima dell'applicazione, ha
dato zero righe. Poi il giro 4.
Decisioni prese il 2026-11-16: la (C), D-4, D-5, F-1.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | ✅ riverifica sullo stato di sviluppo (2026-11-16) | §8.1-8.2 | — |
| 2 | Tid | ✅ le decisioni: la (C), D-4, D-5, F-1 (2026-11-16) | §8.3, §8.3-bis, §8.4 | 1 |
| 3 | team DB | ✅ censimento degli indirizzi di ruolo non ammessi dalla natura (2026-11-16, zero righe); ✅ ripetuto prima dell'applicazione (2026-11-17, zero righe su 687) | §8.3 D-5, §9.3 | 2 |
| 4 | team DB | ✅ giri 1 e 2 scritti e provati in `ROLLBACK` (2026-11-17): BB degli obbligatori, check e picker del ruolo con la natura, guard, auto-clone, cambio di natura, CSV, pgTAP, doc | §9 | 2, 3 |
| 5 | Tid | ✅ giri 1 e 2 applicati su dbdev, pgTAP del §9.2 verdi (2026-11-17) | §9.2 | 4 |
| 5-bis | team DB | ✅ commit DB dei giri 1 e 2 (`9a6db84d2b`, 2026-11-17) | §9.1 | 5 |
| 6 | BE/FE | ✅ R-1 il picker del ruolo da assegnare col soggetto; R-2 la chiave i18n del motivo nuovo; R-3 la policy del codice nuovo; R-4 il fornitore privato sul DB vero (2026-11-17, committate in `0664df90c3`) | §9.4 | 5 |
| 7 | team DB | ✅ giro 3: le frasi dell'obbligatorio mancante per nome, un codice per layer (`20261116-26 … -28`, due CSV, pgTAP, doc), provato in `ROLLBACK` (2026-11-17) | §11 | 5 |
| 7-a | Tid | ✅ `20261116-26 … -28` e i due CSV applicati su dbdev, pgTAP del §11.2 verdi (2026-11-17) | §11.2 | 7 |
| 7-b | BE/FE | ✅ R-5: policy rigenerata col codice nuovo, ripiego dei due messaggi (2026-11-18, non committato) | §11.3 | 7-a |
| 7-c | team DB | ✅ commit del giro 3, con la doc auto-generata (2026-11-17) | §11 | 7-a |
| 7-bis | team DB | ✅ il builder `dbops.fn_pgtap_crea_soggetto_pf` (`20261116-22`), le cinque copie ritirate, pgTAP e doc, provati in `ROLLBACK` (2026-11-17) | §10 | — |
| 7-bis-a | Tid | ✅ `20261116-22` applicato su dbdev, i sei pgTAP del §10.2 verdi (2026-11-17) | §10.2 | 7-bis |
| 7-bis-b | team DB | ✅ commit del giro 7-bis (`8311f9a078`, 2026-11-17) | §10 | 7-bis-a |
| 8 | team DB | ✅ giro 4 scritto e provato in `ROLLBACK` (2026-11-17): il requisito degli obbligatori in sede unica, sulla natura col ripiego (Tid, 2026-11-17); il controllo alla cancellazione, al cambio di tipo (F-1) e al cambio di natura; la fixture del ruolo; pgTAP e doc | §12 | 5 |
| 8-a | Tid | ✅ `20261116-29 … -38` applicati su dbdev, pgTAP verdi, doc auto-generata rigenerata, commit (2026-11-17) | §12.3 | 8 |
| 8-b | BE/FE | ✅ R-6: i rifiuti nuovi sui percorsi di cancellazione e modifica degli indirizzi e del cambio di natura; gli smoke; la modifica dell'indirizzo del ruolo in una transazione (§16) (2026-11-18, non committato) | §12.4 | 8-a, 7-b |
| 8-c | Tid | ✅ il via al giro 5, nella forma proposta, dopo l'applicazione del giro 4 (2026-11-17) | §12.5 | — |
| 8-d | team DB | ✅ giro 5 scritto e provato in `ROLLBACK` (2026-11-17): i mancanti del ruolo e del soggetto su una natura data, letti dai guard, e la lettura per il form del cambio di natura; la madre è del backend (Tid, 2026-11-17, §13) | §13 | 8-c, 8-a |
| 8-e | Tid | ✅ `20261116-39 … -43` applicati su dbdev, pgTAP verdi (col presidio corretto, §13.3), commit (2026-11-17); resta la doc auto-generata | §13.3 | 8-d |
| 8-f | BE/FE | ✅ R-7: il cambio di natura porta gli indirizzi mancanti, nella stessa transazione (col nome del giro 6) (2026-11-18, non committato; la prova a video è di Tid) | §13.4 | 8-h ✅ |
| 8-g | team DB | ✅ giro 6 scritto e provato in `ROLLBACK` (2026-11-18): la rinomina della lettura (`20261116-44`) e i tre pgTAP sul builder del privato | §14 | — |
| 8-h | Tid | ✅ `20261116-44` applicato su dbdev, i quattro pgTAP del §14.2 verdi, doc auto-generata dei giri 5 e 6 rigenerata (2026-11-18) | §14.2 | 8-g |
| 8-i | Tid | ✅ `20261116-45` (i COMMENT di `_ruolo` e `_soggetto`, §14.4) applicato su dbdev, pgTAP verdi, doc auto-generata, commit del giro 6 (`120312f74e`, 2026-11-18) | §14.4 | 8-h |
| 10 | team DB | ✅ giro 7 scritto e provato in `ROLLBACK` (2026-11-18): i lucchetti del titolare dell'indirizzo, l'upsert del pgTAP, il §7 marcato | §15 | 8-i |
| 10-a | Tid | ✅ i tre CSV (`automation_lock_columns`, `codici_errore`, `messaggi_errore`) e `20261116-46` applicati su dbdev, `test-indirizzi-titolare-immutabile-v1` e `test-soggetti-ruoli-indirizzi-required` verdi, doc auto-generata rigenerata (2026-11-18) | §15.3 | 10 |
| 10-b | BE/FE | ✅ R-8: la policy e il ripiego dei due codici nuovi (2026-11-18, non committato) | §15.4 | 10-a ✅ |
| 10-c | team DB | ✅ commit del giro 7 (2026-11-18) | §15 | 10-a |
| 9 | chi chiude | ✅ archiviazione in `work-done/` (2026-11-19): nessun residuo da portare in un brief nuovo (§15.5) | — | tutti |

Decisioni aperte di Tid: nessuna. Decise il 2026-11-18: l'omonimo si rinomina subito (§13.3), i tre pgTAP passano
sul builder (§10.3), e `soggetto_ruolo_id` di un indirizzo è identità (§9.5, giro 7). Il giro 6 è committato
(`120312f74e`); anche il giro 7 (2026-11-18). Il via al giro 5 è dato (§12.5). Decisi il 2026-11-17: il requisito sulla natura (§9.5, vale il
ripiego) e che il cambio di natura con gli indirizzi si fa (§12.5, risposta A). Le due proposte della verifica del 2026-11-17 sono decise (§9.5): la fixture del
ruolo nel giro 4, il builder del privato per i pgTAP subito, come giro a sé (riga 7-bis). I giri 1 e 2, i pgTAP, la
doc e questo brief sono committati (`9a6db84d2b`, 2026-11-17); il giro 7-bis (§10) è applicato, verde e committato (`8311f9a078`, 2026-11-17). Il giro 3 (§11) è applicato, verde e committato (2026-11-17). Il giro 5 (§13) è applicato, verde e committato (2026-11-17); la sua doc auto-generata è da rigenerare. Il giro 4 (§12) è applicato, verde e committato
(2026-11-17).

**Brief vicini verificati (2026-11-16):** nessun brief aperto sugli stessi oggetti. Due chiusi il 2026-11-15
li hanno toccati e qui si **leggono**, non si rifanno:
[brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md) (il predicato del ruolo
in una sede, le check, i picker, gli obbligatori della plurale) e
[brief-db-cambio-natura-soggetto-conferma-e-pulizia](../work-done/brief-db-cambio-natura-soggetto-conferma-e-pulizia.md)
(Q-3: l'indirizzo del soggetto che la natura nuova non ammette è un motivo, l'operatore lo elimina).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** smoke `smoke-test-soggetti.sh` (assegnazione ruoli) e la domanda di Tid
> «un'azienda può comprare da un privato?» del 2026-10-09.
> **Stato:** 🟡 giri 1, 2 e 7-bis applicati e committati (2026-11-17, §9, §10); R-1 … R-4 del BE/FE committati
> (2026-11-17); giro 3 applicato, verde e committato (2026-11-17, §11); R-5 al BE; giro 4 applicato, verde e committato (2026-11-17,
> §12); R-6 al BE; giro 5 applicato, verde e committato (2026-11-17, §13); R-7 al BE/FE; giro 6 provato, da applicare
> (2026-11-18, §14), applicato, verde e committato; giro 7 applicato, verde e committato (2026-11-18, §15); R-5 … R-8 al BE/FE.
>
> ⚠️ **Oggetti cambiati sotto questo brief (team DB, 2026-11-15).** Con il giro 1 di
> [brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md) (§5.1,
> `20261114-84 … -91`) il predicato «il tipo di ruolo ammette il tipo di indirizzo» non sta più
> nel corpo di `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`: sta in
> `anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo`, che leggono il trigger, la check
> `fn_check_tipo_indirizzo_ruolo_su_contesto` e `fn_crea_indirizzi_ruolo` (gli obbligatori da
> copiare, ora attivi **e** validi oggi). Chi riparte da qui cambia la regola lì, una volta sola:
> i rimandi dei §2-§4 al corpo del trigger valgono per il comportamento, non per la sede.

## 1. Il caso di dominio

Un privato senza partita IVA non emette fattura, ma un'azienda **compra** da lui: una
prestazione occasionale (ricevuta, con ritenuta d'acconto quando chi paga è sostituto
d'imposta) o la vendita occasionale di un bene usato. Il privato è quindi un **fornitore**
legittimo (decisione di Tid, 2026-10-09).

Il modello lo prevede già in due punti:

* la natura: `config.tipi_ruoli_nature_ammesse` ammette FORNITORE (`FO`) per la natura `PF`, cioè
  per il privato `PR` e per la ditta individuale `DI`;
* l'anagrafica: il privato `PR` ha la P.IVA non obbligatoria e il codice fiscale obbligatorio
  (`config.tipi_soggetto_dettaglio`), e `anagrafiche.fornitori` porta già `ritenuta_acconto` e
  `ritenuta_aliquota`. **Non serve un flag «soggetto non IVA»**: è il tipo `PR`.

## 2. Che cosa dice oggi la configurazione (contratto, dal seed `80_data`, 2026-10-09)

Gli indirizzi obbligatori del ruolo `FO` (`config.tipi_ruolo_tipi_indirizzo`, tipo ruolo 2):

| Riga | Tipo indirizzo | Obbligatorio | Ripiego |
| --- | --- | --- | --- |
| 13 | `SEDELEG` (sede legale) | sì | — |
| 2 | `FATT` (fatturazione) | sì | `SEDELEG` |
| 4, 5 | `SPED`, `POSTA` | no | `SEDELEG` |

Gli indirizzi ammessi per il privato `PR` (`config.tipi_soggetto_dettaglio_tipi_indirizzo`,
dettaglio 1): `RES`, `DOMFISC`, `FATT`, `POSTA`, `SPED`, `CON`. **La sede legale non c'è**, e
correttamente: un privato non ha una sede.

Per confronto, la ditta individuale `DI` ammette `SEDELEG`, e quindi oggi può essere fornitore
senza forzature.

## 3. I due difetti

### 3.1 Il fornitore privato pretende una sede legale

`trgfn_soggetti_ruoli_guard_indirizzi_required` vuole sul ruolo un `SEDELEG` (riga 13, senza
ripiego). Per un privato il requisito non si può soddisfare con un dato vero.

### 3.2 Gli indirizzi del RUOLO non rispettano la natura del soggetto

Il controllo «questo tipo di indirizzo è ammesso per questo tipo soggetto» esiste solo sugli
indirizzi **del soggetto** (`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`, su
`anagrafiche.indirizzi_soggetti`). Sugli indirizzi **del ruolo** (`anagrafiche.indirizzi`,
`soggetto_ruolo_id`) gira solo `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`, che guarda la
matrice del **ruolo**.

⛔ Conseguenza: oggi un privato **può** diventare fornitore, ma solo dando al ruolo una «sede
legale», cioè un dato falso che sul soggetto il DB rifiuterebbe. «Privato mai fornitore» non è
la regola in vigore: è un blocco che si aggira scrivendo un dato sbagliato. È un'asimmetria del
modello, e va chiusa insieme al 3.1: corretto solo il 3.1, il 3.2 resta un varco per qualunque
ruolo.

## 4. Che cosa si chiede al team DB

### 4.1 Il requisito del fornitore, soddisfacibile da un privato

> ⚠️ *2026-11-16, superato:* la (A) e la (B) sono sostituite dalla (C), confermata da Tid (§8.3-bis): la riga 13
> diventa non obbligatoria, come il cliente. Il resto della nota è la storia.
>
> ⚠️ *2026-11-16:* la (A) così scritta **non basta**: `DOMFISC` non è nella matrice del ruolo `FO`, e il predicato
> del ruolo lo rifiuterebbe proprio dove la (A) lo chiede (§8.2, punto 1). E l'auto-clone non è più del backend:
> è `fn_crea_indirizzi_ruolo`, a DB, ed è lui a scrivere oggi la sede legale falsa (§8.2, punto 2).

**Proposta (A):** sulla riga 13 (`FO` × `SEDELEG`) il ripiego `DOMFISC`, dal CSV di `80_data`.

Il motivo sul modello: ciò che il ruolo chiede è **l'indirizzo fiscale** del fornitore. Per una
società il domicilio fiscale segue la sede legale (art. 58 DPR 600/1973: il comune della sede
legale); per una persona fisica è il domicilio fiscale. «Sede legale, o in sua assenza il domicilio fiscale» dice la stessa cosa
per tutte le nature, ed è lo stesso schema che il cliente usa già (riga 1: `FATT` con ripiego
`DOMFISC`).

Effetto sulle società: un fornitore società potrebbe nascere col solo `DOMFISC` sul ruolo. Il
soggetto società ha comunque `SEDELEG` obbligatorio sui suoi indirizzi (dettagli 3 e 4), quindi
il dato resta.

**Alternativa (B), da valutare se la (A) non regge:** la matrice degli indirizzi del ruolo per
**natura** (o dettaglio), non solo per tipo ruolo. È strutturale (una colonna e i due guard da
riscrivere) e oggi nessun altro ruolo la richiede.

⚠️ La riga 2 (`FATT`, ripiego `SEDELEG`) resta com'è: il guard legge un solo ripiego, e
portarlo a `DOMFISC` romperebbe la società che ha la sola sede legale. Per il privato `FATT`
nasce dall'auto-clone del backend (`create_indirizzi_ruolo`).

### 4.2 Gli indirizzi del ruolo rispettano la natura del soggetto

> ⚠️ *2026-11-16:* «la stessa logica di `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`» oggi ha una sede,
> `anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(natura, tipo, giorno)`: il guard nuovo la **chiama**, non la
> ricopia. E il guard non è la sola sede da toccare: la check del ruolo, l'auto-clone, il picker del tipo di
> ruolo e il cambio di natura (§8.2, punti 2-4).

Un guard (o un ramo di `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`) su
`anagrafiche.indirizzi`: il tipo di indirizzo deve essere ammesso anche da
`config.tipi_soggetto_dettaglio_tipi_indirizzo` per il dettaglio del soggetto del ruolo, con la
stessa logica (e lo stesso limite dichiarato, «senza matrice per quel dettaglio: libero») di
`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`. Codice: si riusa
`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`, con `campo` nel contesto.

⚠️ Il vincolo nuovo non deve trovare righe che lo violano: prima del guard si **censiscono** gli
indirizzi di ruolo non ammessi per il dettaglio del soggetto. Sono dati di sviluppo, ma non si
correggono d'ufficio: cosa farne lo si decide con Tid, guardandoli.

### 4.3 Il messaggio di `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`

> ✅ *2026-11-17:* fatto nel giro 3, §11: la frase nomina ruolo (o natura) e tipo richiesto col ripiego, e il
> layer soggetto ha un codice suo.

> ⚠️ *2026-11-16:* la parte su `E_TIPO_INDIRIZZO_NON_PERMESSO` è **già fatta**: la frase (id 108) è «Il ruolo %s
> non prevede l'indirizzo «%s».», con le descrizioni, e gli id stanno nel contesto. Resta
> `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` (frase id 116, invariata), che ha **due** chiamanti, non uno (§8.2, punto 6).

Oggi: «Indirizzo obbligatorio mancante per soggetto 85214 per tipo ruolo 1, fallback id 8», cioè
id al posto dei nomi, e due segnaposti che dicono il falso: «soggetto» riceve l'id del
**soggetto_ruolo**, «fallback id» riceve il tipo **richiesto**, non il ripiego (corpo del guard,
argomenti del `VARIADIC`). Si chiede
una frase che nomini il **ruolo** e il **tipo di indirizzo** (e il ripiego, se c'è), per esempio
«Il ruolo Fornitore richiede l'indirizzo Sede legale (o Domicilio fiscale)». Lo stesso vale per
`E_TIPO_INDIRIZZO_NON_PERMESSO`, che riporta `tipo_ruolo_id`.

## 5. pgTAP

Casi da costruire:

* privato `PR` con ruolo `FO` e `DOMFISC` sul ruolo → accettato;
* privato `PR` con ruolo `FO` senza `SEDELEG` né `DOMFISC` → `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`;
* privato `PR` con un indirizzo di ruolo `SEDELEG` → rifiuto (`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`);
* società con ruolo `FO` e `SEDELEG` sul ruolo → accettato (nessuna regressione);
* ditta individuale con ruolo `FO` e `SEDELEG` → accettato.

Aggiunti dalla riverifica del 2026-11-16 (§8.2), la forma esatta dipende da D-1 … D-4:

* privato `PR` fornitore creato da `fn_crea_indirizzi_ruolo` col solo indirizzo di residenza → nessun `SEDELEG`
  sul ruolo, requisito soddisfatto (D-2);
* privato `PR` con `DOMFISC` sul ruolo `FO` → il guard del ruolo **non** lo rifiuta (la riga nuova di D-1);
* la check del ruolo su un privato e `SEDELEG` → il motivo della natura; il picker del tipo di ruolo con la
  natura `PR` → `SEDELEG` non proposto;
* ditta individuale fornitore con `SEDELEG` sul ruolo, cambio di natura a `PR` → il motivo (D-4);
* presidio: il guard nuovo e la check **chiamano** `fn_tipo_indirizzo_ammesso_per_natura`, non la ricopiano.

## 6. Ricadute su BE/FE (dopo l'applicazione)

* Il flusso Fornitori (`fornitori_service`) crea un fornitore privato passando gli indirizzi del
  soggetto: da provare sul DB vero, con un test che costruisce il privato.
* Dal 2026-10-09 l'endpoint generico `POST /soggetti/{id}/ruoli/` rifiuta `FO` (ha il suo flusso),
  quindi il fornitore privato passa solo dal flusso Fornitori.
* Se il guard del 4.2 tocca percorsi esistenti, la lista di chi scrive indirizzi di ruolo è:
  `SoggettiService.create_indirizzi_ruolo` (clienti, fornitori, assegnazione ruolo) e la view
  `RuoloIndirizziView`.
  ⚠️ *2026-11-16:* `create_indirizzi_ruolo` oggi chiama il verbo `anagrafiche.fn_crea_indirizzi_ruolo`
  (`soggetti_repository.py`), che fa l'auto-clone: il BE non clona più niente, e la correzione del §8.2 punto 2
  è tutta DB.
* **Richiesta nuova (2026-11-16, dopo il giro 2):** il picker del ruolo da assegnare vuole anche la natura del
  soggetto (§8.2, punto 3). Se cambia la firma di `fn_tipi_indirizzo_proponibili_tipo_ruolo`, il percorso intero
  è: `frontend/src/anagrafiche/composables/useIndirizzoSoggettoForm.js` (161) →
  `frontend/src/core/apiCore.js` `lookupTipiIndirizzoTipoRuolo` (51) → rotta
  `lookup/tipi-ruolo/<tipo_ruolo_codice>/indirizzi/` (`backend/apps/core/api/urls_v1.py`, 134) →
  `LookupTipiIndirizzoTipoRuoloView` (`backend/apps/core/api/views_lookup.py`) →
  `LookupRepository.list_tipi_indirizzo_proponibili_tipo_ruolo` (`backend/apps/core/db/lookup_repository.py`,
  145 e 178); test `backend/apps/anagrafiche/tests/db/test_tipi_indirizzo_proponibili_db.py` (221, 228) e
  `backend/apps/core/tests/db/test_lookup_repository.py` (115). Il DB resta allineato alla firma di oggi finché
  il BE non è pronto: chi cambia per primo si decide al giro 2.
  ⚠️ *2026-11-17:* deciso al giro 2: cambia prima il DB (rotture BE ammesse), e il parametro è il **soggetto**,
  non la natura (§9.1). La richiesta, con le altre, è al §9.4.

## 7. Fuori perimetro: il documento passivo del fornitore privato

Il fornitore privato non manda fatture dallo SdI. Quando si aprirà il ciclo della fattura
passiva (cantiere acquisti, oggi col solo modello, e `contabilita` vuoto) serviranno:

* la registrazione manuale del documento come **ricevuta o nota compenso**, non come fattura;
* il calcolo della ritenuta d'acconto e del netto da pagare (i dati del fornitore ci sono già);
* la scadenza del versamento F24 e i dati per la Certificazione Unica;
* *(2026-11-16, dalla (C) del §8.3-bis)* l'obbligo «il documento ha l'indirizzo fiscale del fornitore»
  sta nel **documento** d'acquisto, come per la fattura di vendita: sede legale o domicilio fiscale, trovati
  con la cascata ruolo → soggetto (`script.fn_resolve_indirizzo_documento`). Il ruolo non lo chiede più.

Nessun brief aperto lo prevede oggi: va annotato fra le decisioni aperte del cantiere acquisti
(PROJECT_CONTEXT), non risolto qui.

⭐ **Parte dello sviluppo acquisti** (2026-11-18): non è debito di questo brief, resta qui all'archiviazione. Il
rimando sta nella voce `acquisti` di PROJECT_CONTEXT.

## 8. Riverifica sullo stato di sviluppo (team DB, 2026-11-16)

Letti il seed (`80_data/sql/config/*.csv`) e il catalogo di dbdev (`pg_get_functiondef`, `pg_trigger`): sono
fatti di **struttura**, non conteggi.

### 8.1 Che cosa regge

* §2: il seed è quello scritto. `FO` ha `SEDELEG` obbligatorio senza ripiego (riga 13), `FATT` obbligatorio con
  ripiego `SEDELEG` (riga 2), `SPED` e `POSTA` facoltativi; il privato `PR` ammette `RES`, `DOMFISC`, `FATT`,
  `POSTA`, `SPED`, `CON`; la `DI` ammette `SEDELEG`.
* §3.1: `trgfn_soggetti_ruoli_guard_indirizzi_required` è invariato (constraint trigger differito su
  `soggetti_ruoli`, `AFTER INSERT OR UPDATE`).
* §3.2: il guard degli indirizzi di ruolo legge solo `fn_tipo_indirizzo_ammesso_per_ruolo`, cioè la matrice del
  ruolo; la natura del soggetto non la guarda nessuno.
* §6: `POST /soggetti/{id}/ruoli/` rifiuta ancora `FO` (`_RUOLI_CON_FLUSSO_DEDICATO` in `soggetti_service.py`);
  `fornitori_service.py` c'è.

### 8.2 Che cosa manca o è cambiato

1. **`DOMFISC` non è ammesso sul ruolo `FO`.** La matrice di `FO` ha quattro righe (`FATT`, `SPED`, `POSTA`,
   `SEDELEG`); un tipo di ruolo con matrice ammette solo le sue coppie. La (A) che mette `DOMFISC` come ripiego
   della riga 13 chiede un indirizzo che il guard del ruolo rifiuta con `E_TIPO_INDIRIZZO_NON_PERMESSO`. Serve
   anche la riga `FO` × `DOMFISC`, non obbligatoria (D-1).
2. **È l'auto-clone a scrivere la sede legale falsa.** `fn_crea_indirizzi_ruolo` copia il primo indirizzo del
   payload su ogni tipo obbligatorio del ruolo che il predicato del ruolo ammette: per `FO`, `FATT` **e**
   `SEDELEG`, anche se il soggetto è un privato. Non guarda il ripiego (`fn_indirizzi_con_obbligatori` riceve
   solo l'elenco dei tipi). Acceso il guard del §4.2, la creazione del fornitore privato si romperebbe lì.
   L'elenco degli obbligatori da copiare deve passare anche il predicato della natura (D-2).
3. **Il §4.2 ha più sedi del trigger.** La check `fn_check_tipo_indirizzo_ruolo_su_contesto` ha due motivi (già
   presente, non ammesso dal ruolo): serve il terzo, «non ammesso dalla natura del soggetto», con
   `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`. Il contesto oggi è il solo tipo di ruolo: la firma prende anche
   la natura. Il picker del ruolo esistente (`fn_tipi_indirizzo_proponibili_ruolo`) la legge dal ruolo; quello
   del ruolo **da assegnare** (`fn_tipi_indirizzo_proponibili_tipo_ruolo(tipo_ruolo)`) non ha il soggetto e oggi
   proporrebbe `SEDELEG` a un privato: vuole la natura in ingresso, ed è una richiesta BE/FE (§6).
   `fn_copia_indirizzo_ruolo` passa dalla singolare e non va toccata.
4. **Il cambio di natura guarda solo gli indirizzi del soggetto.** Il motivo 8 di
   `fn_check_cambio_natura_soggetto` legge `anagrafiche.indirizzi_soggetti`. Una `DI` fornitore con `SEDELEG` sul
   ruolo che diventa `PR` lascerebbe sul ruolo l'indirizzo che il §4.2 vieta (D-4).
5. **Il ripiego ha due mestieri.** `script.fn_get_indirizzo` risolve l'indirizzo di un ruolo seguendo lo stesso
   `fallback_tipo_indirizzo_id` della matrice, prima di scendere al soggetto (fase 3). Con la (A), chi chiede la
   «sede legale» di un fornitore riceverebbe il `DOMFISC` del ruolo, se c'è, prima del `SEDELEG` del soggetto
   (D-3).
6. **`E_INDIRIZZO_OBBLIGATORIO_MANCANTE` ha due chiamanti.** Oltre al guard del ruolo lo solleva
   `trgfn_soggetti_guard_indirizzi_required`, con lo stesso difetto nei segnaposti («soggetto» riceve l'id del
   soggetto, poi la natura per id, poi il tipo richiesto dove la frase dice «fallback id»). La frase nuova serve
   tutti e due, o il codice si divide per layer come già quello del tipo non ammesso.

### 8.3 Le decisioni di Tid

* **D-1** — Il requisito del fornitore: la (A) completata (riga 13 con ripiego `DOMFISC` **e** riga nuova
  `FO` × `DOMFISC` non obbligatoria), oppure la (B), la matrice del ruolo per natura? Proposta: (A) completata.
  ✅ *Decisa da Tid il 2026-11-16:* (A) completata. La (B) è scartata.
  ⚠️ *Revocata lo stesso giorno* dalla (C), §8.3-bis.
* **D-2** — L'auto-clone per un tipo obbligatorio che la natura non ammette: lo **sposta sul ripiego** (`SEDELEG`
  → `DOMFISC`) o lo **salta**? Proposta: sul ripiego, se il ripiego è ammesso dalla natura; altrimenti salta, e
  decide il guard degli obbligatori.
  ✅ *Decisa da Tid il 2026-11-16:* sul ripiego, se il ripiego è ammesso dalla natura (e dal ruolo); altrimenti
  il tipo si salta. Da provare nel giro 1 col payload vero del flusso Fornitori: se contiene già `DOMFISC`, la
  copia non scatta.
  ⚠️ *Senza oggetto dal 2026-11-16* (la (C), §8.3-bis): `SEDELEG` non è più obbligatorio per `FO`. Resta la sola
  regola «la copia non scrive un tipo che la natura vieta».
* **D-3** — Va bene che la risoluzione della «sede legale» di un fornitore passi per il `DOMFISC` del ruolo prima
  del `SEDELEG` del soggetto?
  ✅ *Decisa da Tid il 2026-11-16:* va bene così; si scrive nella pagina `manual/` di `fn_get_indirizzo` e nella
  guida degli indirizzi.
  ⚠️ *Senza oggetto dal 2026-11-16* (la (C), §8.3-bis): il ripiego della riga 13 non cambia.
* **D-4** — Nel cambio di natura, gli indirizzi **di ruolo** non ammessi dalla natura nuova diventano un motivo,
  come quelli del soggetto (Q-3 del 2026-11-14)? Proposta: sì, stesso esito.
  ✅ *Decisa da Tid il 2026-11-16:* stesso trattamento di Q-3. Il motivo 8 di `fn_check_cambio_natura_soggetto`
  legge anche gli indirizzi dei ruoli del soggetto; il motivo nomina il ruolo. Nessuna pulizia automatica.
* **D-5** — Gli indirizzi di ruolo già scritti che violano la regola (il censimento del §4.2): che cosa se ne fa,
  guardandoli.
  *Censimento del 2026-11-16 (dbdev, `zeroerp_owner`, sola lettura; RLS non attiva sulle tre tabelle, 685
  indirizzi di ruolo visibili):* **nessuna** riga di ruolo ha un tipo che la natura del soggetto non ammette, e
  nessun soggetto `PR` ha oggi il ruolo `FO`. Fatto datato: non decide niente sul guard, che serve comunque
  (§3.2), e va rifatto subito prima di applicare il giro 1.
  ✅ *Chiusa da Tid il 2026-11-16:* nessuna riga da trattare. Il censimento si ripete prima dell'applicazione del
  giro 1: una riga comparsa nel frattempo riapre D-5.

### 8.3-bis La proposta (C), speculare al cliente — ✅ confermata da Tid il 2026-11-16

> ⚠️ **Revoca D-1** e rende **senza oggetto D-2 e D-3** (decise lo stesso giorno, prima di questa verifica):
> restano scritte sopra come storia. Sostituisce la (A) e la (B) del §4.1.

**Il dubbio di Tid (2026-11-16):** il cliente può essere una società (sede legale) o un privato (domicilio
fiscale) come il fornitore; la logica dev'essere speculare.

**La proposta:** la riga 13 (`FO` × `SEDELEG`) diventa `obbligatorio = f` e resta ammessa; `FATT` resta
obbligatorio come per il cliente; nessuna riga nuova e nessun ripiego nuovo. L'indirizzo fiscale sta sul
**soggetto**, dove la natura lo distingue già; l'obbligo «il documento ha la sede del fornitore» sarà del
documento d'acquisto, come per la fattura di vendita (§7).

**La verifica (struttura, non conteggi):**

| # | Che cosa | Esito |
| --- | --- | --- |
| 1 | Ogni natura ha già il suo indirizzo fiscale obbligatorio **sul soggetto** (`tipi_soggetto_dettaglio_tipi_indirizzo`, guard `trgfn_soggetti_guard_indirizzi_required`) | ✅ `PR`: `RES`, `DOMFISC`, `FATT`; `DI`: `DOMFISC`; `SC`, `SP`, `ENC`: `SEDELEG` |
| 2 | Il cliente è già così: sul ruolo `CL` solo `FATT` obbligatorio (ripiego `DOMFISC`), `SEDELEG` nemmeno ammesso | ✅ seed |
| 3 | Il modello deciso: «l'indirizzo si prende dal ruolo se c'è, altrimenti dal soggetto», e l'obbligo della sede è del documento, non del ruolo (Tid, 2026-07-31, [brief-db-snapshot-intestazione-fattura §10.3](../work-done/brief-db-snapshot-intestazione-fattura.md)) | ✅ la (C) lo **applica**, non lo cambia |
| 4 | La catena a due layer esiste: `script.fn_resolve_indirizzo_documento` (ruolo, poi soggetto) e la fase 3 di `script.fn_get_indirizzo` | ✅ catalogo |
| 5 | La guida *Gestione degli indirizzi*: gli indirizzi identitari (residenza, domicilio fiscale) sono del soggetto, quelli operativi del ruolo | ✅ coerente |
| 6 | Chi dipende dall'obbligo: nessun pgTAP; la fixture `dbops.fn_pgtap_crea_soggetto_ruolo` legge gli obbligatori dalla matrice | ✅ niente da riscrivere |
| 7 | Il flusso Fornitori: `fornitori_service` → `fn_crea_fornitore` → `fn_crea_indirizzi_ruolo`, che oggi clona il primo indirizzo come `SEDELEG`; con la (C) non lo clona più | ✅ il dato falso sparisce alla fonte |
| 8 | L'origine dell'obbligo: seed iniziale (`fc049fe513`, 2025-11-30), nessuna decisione scritta che lo motivi | ✅ nessuna decisione da revocare |

**Che cosa resta valido comunque:** il §4.2 (la natura sugli indirizzi del ruolo: oggi una sede legale sul ruolo
di un privato si scrive), D-4, D-5, il §4.3 e F-1. La regola «la copia automatica non scrive un tipo che la
natura vieta» resta, senza la parte del ripiego.

**Ricadute di documentazione:** `manual/fn_crea_fornitore.md` (riga 32: «obbligatori per un fornitore (sede
legale, fatturazione)») e la guida *Gestione degli indirizzi*.

**Osservazione, senza proposta:** neanche gli **ammessi** sono speculari: il ruolo `CL` ammette `RES` e `DOMFISC`
(identitari), il ruolo `FO` ammette `SEDELEG` (identitario). Per la guida stanno sul soggetto. Non cambia niente
qui; se ne parla solo se Tid lo vuole.

### 8.4 Fuori perimetro, segnalato

* **F-1** — Il requisito degli obbligatori si controlla solo quando si scrive il **titolare**: sul ruolo
  all'`INSERT`/`UPDATE` di `soggetti_ruoli`, sul soggetto all'`INSERT`/`UPDATE` di `soggetti`. Su
  `anagrafiche.indirizzi` e `anagrafiche.indirizzi_soggetti` non c'è un trigger di `DELETE` che lo rilegga, e
  l'app ha il `DELETE` su tutte e due (il BE cancella in `soggetti_repository.py`). Cancellare dopo la sede
  legale, o cambiarne il tipo, lascia il titolare senza obbligatorio. Decide Tid se entra qui o va nel registro
  dei residui aperti.
  Verificato il 2026-11-16: il BE cancella con un `DELETE` suo (`delete_indirizzo_ruolo`,
  `delete_indirizzo_soggetto` in `soggetti_repository.py`) e `tipo_indirizzo_id` è fra le colonne modificabili
  (`INDIRIZZO_RUOLO_UPDATE_COLS`). Il percorso di D-4 («elimina l'indirizzo non ammesso e riprova») passa di qui.
  ✅ *Decisa da Tid il 2026-11-16:* entra **qui, come giro 4**, separato dai primi tre. Forma proposta: alla
  cancellazione di un indirizzo, o al cambio del suo tipo o del titolare, il DB ricontrolla gli obbligatori del
  titolare a fine transazione (constraint trigger differito su `anagrafiche.indirizzi` e
  `anagrafiche.indirizzi_soggetti`), con `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`; tace se il titolare stesso non c'è
  più (cancellazione del soggetto o del ruolo). Il controllo degli obbligatori ha una sede sola, che leggono il
  guard del titolare e quello nuovo (regola del 2). Nessuna modifica BE: il codice esiste già.
  pgTAP: eliminare l'unico `FATT` di un ruolo `CL` → rifiuto; eliminarlo quando c'è il ripiego → accettato;
  cambiare il tipo dell'unico obbligatorio → rifiuto; eliminare la sede legale di una società sul soggetto →
  rifiuto; eliminare il ruolo con i suoi indirizzi → accettato; lo stesso sul layer soggetto.

## 9. Giri 1 e 2, fatti (team DB, 2026-11-17)

Scritti insieme, al via di Tid del 2026-11-17: il picker del ruolo da assegnare (giro 2) cambia firma nello
stesso changeSet della check (giro 1), perché è `BEGIN ATOMIC` e dipende da lei.

### 9.1 Che cosa

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| BB `fn_tipo_indirizzo_obbligatorio_per_ruolo(tipo ruolo, natura, tipo, giorno)`: riga obbligatoria della matrice del ruolo, ammessa dal ruolo e dalla natura; `BEGIN ATOMIC` | `20261116-17-create-fn-tipo-indirizzo-obbligatorio-per-ruolo` |
| `fn_check_tipo_indirizzo_ruolo_su_contesto` con la natura in coda (terzo motivo, `TIPO_NON_AMMESSO_DALLA_NATURA`); la firma completa la legge dal soggetto del ruolo; i due picker del ruolo la leggono, e quello sul tipo di ruolo riceve il **soggetto** (giro 2) | `20261116-18-update-fn-check-tipo-indirizzo-ruolo-con-la-natura` |
| `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`: il ramo della natura, dopo quello del ruolo | `20261116-19-update-trgfn-indirizzi-guard-tipo-ruolo-natura` |
| `fn_crea_indirizzi_ruolo`: gli obbligatori da copiare dal BB, sulla natura del soggetto | `20261116-20-update-fn-crea-indirizzi-ruolo-obbligatori-per-natura` |
| `fn_check_cambio_natura_soggetto`: il motivo 9, gli indirizzi dei ruoli (D-4, giro 2) | `20261116-21-update-fn-check-cambio-natura-soggetto-indirizzi-ruolo` |
| La (C): riga 13 (`FO` × `SEDELEG`) `obbligatorio = f` | `80_data/sql/config/tipi_ruolo_tipi_indirizzo.csv` |
| `E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI` (`CONFLITTO_STATO`), frase id 1509; la nota di `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` dice il secondo layer | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` |
| Il pgTAP del cantiere (24 asserzioni) | `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` |
| Pagine `manual/` del guard, della plurale e di `fn_crea_fornitore`; guida *Gestione degli indirizzi* (§ Indirizzo per ruolo, matrice in context ruolo, R5; due ancore morte verso R5 e R6 corrette) | `docs/it/dbzero/anagrafiche/manual/`, `docs/it/guide/` |

**Le scelte fatte scrivendo:**

* **Il BB nasce per la regola del 2.** «Obbligatorio per il ruolo, oggi» era scritto tre volte (l'auto-clone e i
  due picker); con la natura sarebbero state tre copie di una regola più grande. Ora lo leggono tutti e tre.
* **La natura nella check è in coda e senza default** (linee-guida-sql §5f): il comportamento di prima, la natura
  ignorata, è il difetto. Il motivo è lo **stesso** della check del soggetto (codice, `reason`, `reason_key`,
  valori): nessuna chiave i18n nuova per lui.
* **Il picker sul tipo di ruolo riceve il soggetto, non la natura.** Il drawer lo carica all'apertura, prima che
  l'operatore scelga il soggetto (`FornitoreDrawer.vue` 135, `ClienteDrawer.vue` 266): `NULL` = soggetto non
  ancora scelto, la natura non conta; un soggetto che non esiste dà nessuna riga, come un tipo di ruolo che non
  esiste. Senza default anche lui (§5f), quindi il BE si rompe finché non lo passa (R-1).
* **Il guard usa il codice del guard del soggetto**, `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`: la regola e la
  matrice sono quelle, il contesto dice il layer. Nessun DDL sul trigger.
* **Il cambio di natura ha un codice suo**, gemello di `E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI`, come i due layer
  dei guard del tipo; il dettaglio porta `indirizzi` e `ruolo` per la frase del FE (R-2).
* `SECURITY INVOKER` ora esplicito sulle funzioni riscritte. Corpi dagli ultimi YAML (`20261114-87`, `-91`, `-93`,
  `-95`, `-97`, `20261115-41`, `-61`), verificati uguali al `prosrc` vivo; firme ancorate.

### 9.2 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-17: estratto dei cinque changeSet più
l'effetto dei tre CSV (un changeSet di sola prova nello scratchpad, fuori dal repo, perché il `loadUpdateData`
non si estrae), eseguito per intero, catalogo identico dopo il `ROLLBACK`. Guardrail statici verdi (forme,
letterali, COMMENT al presente, runOnChange, preCondition, DDL sui trigger generati, timestamp).

| pgTAP | Senza l'estratto | Con l'estratto |
| --- | --- | --- |
| `test-fornitore-privato-indirizzi-v1` (nuovo) | interrotto | 24 ok / 0 |
| `test-check-tipo-indirizzo-v1`, `test-tipi-indirizzo-proponibili-v1` (riscritti: la firma nuova) | rossi / interrotti | 34 / 0, 25 / 0 |
| `test-fn-crea-indirizzi-ruolo-v1`, `test-fn-crea-fornitore-v1` (riscritti: §9.3) | verdi | 18 / 0, 16 / 0 |
| `test_indirizzi_unique_res`, `create-gestore-indirizzo-res-domfisc`, `test-indirizzo-libero-due-forme-v1` (riscritti: §9.3) | verdi | 6 / 0, 10 / 0, 28 / 0 |
| `test-copia-indirizzo-v1`, `test-indirizzi-fallback`, `test-indirizzi-istanza-cascata`, `test-indirizzi-singolare-e-plurale-v1`, `test-istanza-dello-stesso-soggetto-v1`, `test-soggetti-ruoli-guard-natura-ammessa`, `test-cambio-natura-soggetto-v1`, `test-fn-elimina-dati-societari-v1`, `test-fn-crea-cliente-v1`, `create-cliente`, `create-gestore-indirizzo-res`, `script/test-rubinetto-primo-motivo-v1`, `dbops/test-punti-canale-campo-v1`, `vendite/test-indirizzi-documento-seguono-cliente-v1`, `vendite/test-snapshot-indirizzi-lotto-v1` | verdi | invariati |
| `vendite/test-snapshot-indirizzi-fattura-v1` | 15 / **1** | 15 / **1**: rosso preesistente, non di qui |

⚠️ **Limiti dichiarati.** La prova gira da owner: le tabelle lette dai guard (`indirizzi`, `soggetti_ruoli`,
`soggetti`, le matrici) non sono sotto RLS, ma l'esito come applicazione arriva dai pgTAP di Tid.
`test-soggetti-ruoli-indirizzi-required` lo script non lo lancia (due righe `BEGIN;`); legge la regola
cliente × fatturazione su un privato, che la natura ammette. I `BEGIN ATOMIC` stanno da soli nel loro `sql:`
(guardrail verde), non provati attraverso il driver.

### 9.3 Controesempi trovati provando (fatti)

* **Quattro fixture scrivevano un indirizzo che il modello non ammette**: una **residenza** sul ruolo cliente di
  una **società di capitali** (`test-fn-crea-indirizzi-ruolo-v1`, `test_indirizzi_unique_res`,
  `create-gestore-indirizzo-res-domfisc`, `test-indirizzo-libero-due-forme-v1`). Sceglievano i tipi dalla sola
  matrice del ruolo: è il varco del §3.2, e il guard nuovo li ferma. Corretti cambiando il veicolo, non la regola
  provata: dove il tipo è un mezzo lo dà il picker del ruolo; dove la residenza è il soggetto del test il
  soggetto diventa un privato, nato dalle madri.
* **Due test sarebbero diventati verdi per sottrazione**: con la (C) il fornitore ha un solo obbligatorio, e la
  copia degli obbligatori non si esercitava più (`test-fn-crea-indirizzi-ruolo-v1` 2-3,
  `test-fn-crea-fornitore-v1` 7). Il secondo obbligatorio lo scrive ora il test.
* Il censimento di D-5 si **ripete prima dell'applicazione** (la query del 2026-11-16: indirizzi di ruolo il cui
  tipo `fn_tipo_indirizzo_ammesso_per_natura` non ammette per la natura del soggetto). Il guard non rilegge le
  righe che ci sono: una riga che lo viola resterebbe, e il cambio di natura del suo soggetto si fermerebbe sul
  motivo 9.

### 9.4 Richieste a BE/FE (elenco chiuso)

* **R-1 (BE + FE)** — `anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(tipo ruolo, soggetto)`: il secondo
  argomento è il soggetto a cui il ruolo si assegna (`uuid`), `NULL` finché non è scelto. Fino al cambio la
  rotta `lookup/tipi-ruolo/<codice>/indirizzi/` risponde errore (la funzione a un argomento non c'è più). Il
  percorso intero è al §6: `useIndirizzoSoggettoForm.js` (161, `loadMatriceRuolo`) e i due drawer che la chiamano
  all'apertura (`FornitoreDrawer.vue` 135, `ClienteDrawer.vue` 266), che la **ricaricano** quando il soggetto è
  scelto; `apiCore.js` 51; `urls_v1.py` 134; `views_lookup.py` (`LookupTipiIndirizzoTipoRuoloView`);
  `lookup_repository.py` 145 e 178; i test `test_tipi_indirizzo_proponibili_db.py` (221, 228) e
  `test_lookup_repository.py` (115).
* **R-2 (FE, prima del commit DB)** — la chiave `anagrafiche.soggetti.cambio_natura_blocco.indirizzi_ruolo` in
  `it.json` ed `en.json`, coi parametri del dettaglio `{indirizzi}` e `{ruolo}`. Proposta: «La natura scelta non
  ammette {indirizzi} indirizzi del ruolo {ruolo}: vanno eliminati dal ruolo prima del cambio.» Il pre-commit
  `check-i18n-keys` la pretende appena la doc auto-generata è rigenerata.
* **R-3 (BE)** — la policy di `E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI` (`CONFLITTO_STATO`): rigenerare
  `error_policies_generated.py`; e il suo ripiego senza segnaposto in `error_messages_fallback.py`, accanto a
  quello del gemello `E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI` (lo pretende
  `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, api.md § ripiego). Proposta: «Il tipo soggetto scelto non
  ammette alcuni indirizzi di un ruolo del soggetto: vanno eliminati dal ruolo prima del cambio.» `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` arriva ora anche dalle scritture
  sul ruolo (`RuoloIndirizziView`, `create_indirizzi_ruolo`), con lo stesso campo `tipo_indirizzo_id`: la policy
  c'è già.
* **R-4 (BE)** — il primo punto del §6: un test che crea un fornitore privato dal flusso Fornitori sul DB vero,
  con la sola fatturazione sul ruolo.

✅ *Fatte dal team BE/FE il 2026-11-17* (committate in `0664df90c3`, PR #155):

* **R-1** — la rotta prende `?soggetto_id=<uuid>` facoltativo (assente: `NULL`; non uuid: 400
  `E_VALIDATION_INPUT`), e il repository lo passa come secondo argomento. Il FE lo manda dal composable
  (`loadMatriceRuolo(tipo, soggetto)`) e i due drawer rileggono il picker a ogni soggetto scelto
  (`seguiSoggettoDelRuolo`), con il guard anti-race `useFetchVersion`: una lettura vecchia senza soggetto non
  sovrascrive quella nuova. Test: `test_lookup_tipi_indirizzo_tipo_ruolo_api.py` (nuovo), tre casi nuovi in
  `test_tipi_indirizzo_proponibili_db.py` (la natura spegne col motivo, gli obbligatori sono ammessi, soggetto
  inesistente), quattro nella spec del composable (anche: una lettura partita prima del `reset()` non
  ripopola la matrice svuotata).
* **R-1, seguito della revisione** (2026-11-17, ok Tid): la matrice del ruolo da assegnare si legge **solo** a
  soggetto scelto (la sezione indirizzi della creazione compare col soggetto), e la lettura all'apertura del
  drawer è tolta: era doppia e mai a video. La `?soggetto_id` si legge col BB nuovo `qp_uuid_optional`, che ha
  sostituito altre tre copie dello stesso giro di `optional_uuid` su query string.
* **R-2** — la chiave in `it.json` ed `en.json`, con la frase proposta; `check_i18n_keys.py` pulito.
* **R-3** — policy rigenerata (il diff porta solo i due codici di questo brief: DB e git allineati) e ripiego
  accanto al gemello.
* **R-4** — `test_clienti_fornitori_scrittura_db.py`, caso 3: il privato dal builder, il fornitore dal
  service con i soli indirizzi che il picker col soggetto segna obbligatori, i guard differiti richiusi.

### 9.5 Debito e note per i giri dopo

* **Giro 4: il requisito degli obbligatori ignora la natura.** `trgfn_soggetti_ruoli_guard_indirizzi_required`
  pretende ogni riga obbligatoria della matrice del ruolo, anche un tipo che la natura del soggetto vieta: un
  requisito che nessuna scrittura può soddisfare. Nel seed di oggi non succede (fatto datato: dopo la (C) i
  ruoli con un obbligatorio non ammesso da una loro natura ammessa sono zero); il modello lo ammette, e il pgTAP
  del cantiere lo costruisce (SEDEOP obbligatorio per `FO`, 6-7 e 19). La sede unica degli obbligatori del giro 4
  legge `fn_tipo_indirizzo_obbligatorio_per_ruolo`, con la stessa regola dell'auto-clone; resta da decidere con
  Tid che cosa vale il ripiego di una riga che la natura vieta.
  ✅ *Decisa da Tid il 2026-11-17:* **vale il ripiego**. Se la natura vieta il tipo della riga e ammette il ripiego
  (ammesso anche dal ruolo), si chiede il ripiego; se li vieta tutti e due, la riga non chiede niente. Scartate:
  saltare la riga intera (la regola che l'auto-clone aveva dal giro 1) e l'errore di configurazione. Riprende la
  D-2 del 2026-11-16, resa senza oggetto dalla (C) per il solo seed del fornitore. ✅ *Fatto* (§12).
* **Segnalato, senza proposta di cantiere:** un `UPDATE` di `anagrafiche.indirizzi.soggetto_ruolo_id` non fa
  scattare il guard (`UPDATE OF tipo_indirizzo_id`), né per il ruolo né per la natura. Il BE non scrive quella
  colonna (`INDIRIZZO_RUOLO_UPDATE_COLS`); se è identità, la forma è un lucchetto
  (`dbops.automation_lock_columns`, linee-guida-trigger § `UPDATE OF`). Decide Tid se e dove.
  ✅ *Decisa da Tid il 2026-11-18:* è identità, lucchetto, in questo brief (giro 7, §15), insieme al gemello del
  layer soggetto (`indirizzi_soggetti.soggetto_id`).
* **Verifica del 2026-11-17, una quarta copia di «obbligatorio per il ruolo».** La fixture
  `dbops.fn_pgtap_crea_soggetto_ruolo` sceglie il primo indirizzo da passare alla plurale con la sua query sulla
  matrice (`attivo AND obbligatorio`, senza la finestra di validità e senza la natura). Su un ruolo con un
  obbligatorio che la natura del soggetto vieta passerebbe proprio quel tipo, e il guard del ruolo lo rifiuterebbe.
  Oggi non pesa: lo stesso ruolo non si chiude comunque finché il requisito degli obbligatori ignora la natura (il
  primo punto). Proposta: entra nel giro 4, con la fixture che legge `fn_tipo_indirizzo_obbligatorio_per_ruolo`
  sulla natura del soggetto, in un changeSet suo.
  ✅ *Decisa da Tid il 2026-11-17:* nel giro 4. ✅ *Fatto* (§12, `20261116-38`).
* **Verifica del 2026-11-17, il privato dei pgTAP scritto tre volte.** `test_indirizzi_unique_res`,
  `create-gestore-indirizzo-res-domfisc` e `test-fornitore-privato-indirizzi-v1` creano un privato con la
  residenza con lo stesso blocco (madre `fn_crea_soggetto_pf` + `fn_crea_indirizzi_soggetto`, nella finestra
  differita). Il gemello della società c'è (`dbops.fn_pgtap_crea_soggetto_pg`), quello della persona fisica no.
  Proposta: un builder `dbops.fn_pgtap_crea_soggetto_pf` e le tre copie ritirate nello stesso giro. È un
  building block nuovo: decide Tid se e quando.
  ✅ *Decisa da Tid il 2026-11-17:* sì, subito, come giro a sé prima del 3 (riga 7-bis). Il builder nasce
  sulle madri, come il gemello della società, e i tre pgTAP lo usano nello stesso giro.
  ✅ *Fatto il 2026-11-17* (§10): il censimento ha trovato **cinque** copie, non tre.

## 10. Giro 7-bis, il builder del privato (team DB, 2026-11-17)

### 10.1 Che cosa

| Pezzo | File |
| --- | --- |
| `dbops.fn_pgtap_crea_soggetto_pf(cognome, nome, natura, stato, partita IVA)`: gemello di `fn_pgtap_crea_soggetto_pg`, dalle madri `fn_crea_soggetto_pf` e `fn_crea_indirizzi_soggetto`; apre e richiude la finestra differita | `20_code/dbops/20261116-22-create-fn-pgtap-crea-soggetto-pf` |
| Il presidio del builder (9 asserzioni) | `db/pgtap/anagrafiche/test-fn-pgtap-crea-soggetto-pf-v1.sql` |
| Le cinque copie ritirate (§10.3) | i cinque pgTAP |
| Pagina `manual/` nuova; quella del gemello e quella del ruolo rimandano al builder; la tabella delle fixture della guida pgTAP ha la riga della persona fisica | `docs/it/dbzero/dbops/manual/`, `docs/it/guide/pgtap-come-si-scrive-un-test.md` |

**Le scelte fatte scrivendo:**

* **I valori li decide la natura, come nel gemello.** Senza natura, il privato (PR) dello stato. Sesso se la
  natura lo prevede (`sesso_policy` diversa da `NONE`); partita IVA quella del test o, se la natura la pretende,
  una libera; codice fiscale libero; indirizzi dal primo tipo obbligatorio della matrice della natura, copiato
  dalla madre sugli altri.
* **Dati societari solo se la natura li pretende (`REQUIRED`)**, non anche se li ammette come fa il gemello: per
  una persona fisica sono facoltativi o vietati, e la fixture costruisce il soggetto minimo che il modello
  ammette. Una ditta individuale nasce senza; il caso `REQUIRED` su una natura PF il seed non lo ha, e il pgTAP
  lo costruisce (7).
* **Firma ancorata** (`%TYPE` su ogni argomento e sul ritorno): è una funzione nuova, nessuna identità da
  conservare (il gemello tiene `integer` sulla natura per non cambiare la sua).

### 10.2 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-17: estratto eseguito per intero, catalogo
identico dopo il `ROLLBACK`. Guardrail statici verdi (forme, letterali, COMMENT al presente, runOnChange,
preCondition, timestamp, DDL sui trigger generati, GRANT ai ruoli batch; preambolo pgTAP).

| pgTAP | Con l'estratto |
| --- | --- |
| `test-fn-pgtap-crea-soggetto-pf-v1` (nuovo) | 9 / 0 |
| `test_indirizzi_unique_res`, `create-gestore-indirizzo-res-domfisc`, `test-fornitore-privato-indirizzi-v1`, `test-risorse-umane` (riscritti) | 6 / 0, 10 / 0, 24 / 0, 8 / 0 |
| `test-soggetti-titoli-iva-tipo-soggetto-v1` (riscritto) | 19 / **2**: il 14 e il 15, di perimetro RLS (da owner rossi per costruzione); la versione committata, sullo stesso scratch, ha anche lei 19 / 2 |
| `dbops/test-builder-pgtap-vincoli-immediate-v1`, `dbops/test-riferimenti-morti-v1`, `test-comment-al-presente-v1`, `test-corpo-funzione-senza-commenti-v1`, `test-security-definer-search-path-v1` (presidi trasversali) | invariati, verdi |

⚠️ **Limite dichiarato:** la prova gira da owner; il 14 e il 15 di `titoli-iva` li dice solo la corsa di Tid.
✅ *Corsa di Tid, 2026-11-17:* `20261116-22` applicato su dbdev, i sei pgTAP verdi, compresi il 14 e il 15 di
`titoli-iva`.

### 10.3 Il censimento delle copie

La verifica ne aveva contate tre; cercando i pgTAP che chiamano `anagrafiche.fn_crea_soggetto_pf` ne sono uscite
**cinque** con lo stesso significato, «un privato (o una ditta) valido, coi suoi obbligatori, come veicolo del
test»:

* `test_indirizzi_unique_res`, `create-gestore-indirizzo-res-domfisc`, `test-fornitore-privato-indirizzi-v1` —
  le tre della verifica (madre + plurale nella finestra);
* `test-risorse-umane` — madre + **singolare**, due chiamate (RES, DOMFISC);
* `test-soggetti-titoli-iva-tipo-soggetto-v1` (`_pr2`) — madre + un **`INSERT`** diretto su
  `anagrafiche.indirizzi_soggetti`, accanto alla madre degli indirizzi.

**Non sono copie, e restano** (il significato è un altro):

* i pgTAP **della madre** e dei suoi guard (`test-fn-crea-soggetto-pf`, `test-soggetti-sesso-policy-v1`,
  `test-dati-societari-alla-nascita-v1`, `script/test-fn-guard-soggetto-pf-pura` e simili): la chiamata alla
  madre è l'oggetto del test;
* i soggetti **incompleti** di una finestra che il file non richiude (`test-cambio-natura-soggetto-v1` e
  `test-fn-elimina-dati-societari-v1`, la ditta senza indirizzi; `test-soggetti-regime-pa-v1`,
  `test-soggetti-titoli-iva-tipo-soggetto-v1` `_pr`): il test giudica la riga appena nata, non un soggetto finito.

**Segnalato, senza proposta di cantiere:** una seconda strada costruisce il privato veicolo del test con un `INSERT` diretto su
`anagrafiche.soggetti`, accanto alla madre: `create-cliente`, `test-fn-update-cliente-v1`,
`test-soggetti-ruoli-indirizzi-required` (oltre ai test dei guard sulla riga, dove l'`INSERT` è l'oggetto). È lo
stesso difetto che il gemello ha chiuso per la società il 2026-11-08 (D63 di brief-db-revisione-dbops). Se
portarli sul builder, e quando, decide Tid.

✅ *Decisa da Tid il 2026-11-18: si portano, subito.* Fatto nel giro 6 (§14).

## 11. Giro 3, le frasi dell'obbligatorio mancante (team DB, 2026-11-17)

### 11.1 Che cosa

| Pezzo | File |
| --- | --- |
| `anagrafiche.fn_nomi_tipo_indirizzo_richiesto(tipo, ripiego)`: i nomi del tipo richiesto e del suo ripiego, per descrizione, fra caporali e separati da ` / ` (`«Sede Legale» / «Domicilio Fiscale»`); `BEGIN ATOMIC` | `20_code/anagrafiche/20261116-26-create-fn-nomi-tipo-indirizzo-richiesto` |
| Il guard del ruolo: stesso codice, valori per nome (ruolo, tipi) | `20261116-27-update-trgfn-soggetti-ruoli-guard-indirizzi-required-frase` |
| Il guard del soggetto: **codice nuovo** `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`, valori per nome (natura, tipi) | `20261116-28-update-trgfn-soggetti-guard-indirizzi-required-codice-proprio` |
| Frasi: id 116 riscritta, «Il ruolo %s richiede l'indirizzo %s.»; id 1511 nuova, «Il tipo soggetto %s richiede l'indirizzo %s.», con causa e soluzione | `80_data/sql/config/messaggi_errore.csv` |
| Il codice nuovo (`DATO_ERRATO`) e la nota di quello del ruolo | `80_data/sql/config/codici_errore.csv` |
| pgTAP nuovo (10 asserzioni) | `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` |
| Le due pagine `manual/` dei guard (errori, frase, gemello, data operativa al posto di `current_date`) | `docs/it/dbzero/anagrafiche/manual/` |

**Le scelte fatte scrivendo:**

* **Un codice per layer**, la strada che il §8.2 (6) lasciava aperta. Le matrici sono due e chi rimedia corregge
  configurazioni diverse: è la stessa ragione per cui il tipo non ammesso ha già due codici
  (`E_TIPO_INDIRIZZO_NON_PERMESSO` del ruolo, `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` del soggetto). Il
  codice storico resta al **ruolo**, come nel gemello: il BE lo confronta già sul flusso Fornitori (smoke,
  `test_assegna_ruolo_indirizzi_db`), e il lato soggetto nessun call-site BE lo nomina (censito il 2026-11-17).
* **Il ripiego entra nella frase** come secondo nome dello stesso valore, `«A» / «B»`: una congiunzione italiana
  («o») composta nel plpgsql non sarebbe traducibile, e il separatore vale in ogni lingua. Il valore lo
  compongono due guard con la stessa regola: alla seconda copia, il building block (regola del 2).
* **Nessun `campo` nel contesto**: non c'è un campo del form in errore, manca una riga.
* La regola dei due guard non cambia (matrice, validità, ripiego) e il montaggio nemmeno. Il requisito del ruolo
  che ignora la natura resta al giro 4 (§9.5).

### 11.2 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-17: i tre changeSet più un estratto di sola
prova con le quattro righe dei due CSV (lo script non esegue i loader), catalogo identico dopo il `ROLLBACK`.
Guardrail statici verdi (forme, letterali, COMMENT al presente, runOnChange, preCondition, timestamp, DDL sui
trigger generati, GRANT ai ruoli batch, v1 congelato; preambolo pgTAP); segnaposti e unicità degli id dei messaggi
controllati.

| pgTAP | Senza → con l'estratto |
| --- | --- |
| `test-indirizzo-obbligatorio-mancante-frase-v1` (nuovo) | interrotto → 10 / 0 |
| `test-fornitore-privato-indirizzi-v1`, `test-fn-pgtap-crea-soggetto-pf-v1`, `test-check-tipo-indirizzo-v1` | 24 / 0, 9 / 0, 34 / 0, invariati |
| `script/test-catalogo-messaggi-errore-completo`, `script/test-rubinetto-primo-motivo-v1`, `dbops/test-codice-errore-conforme-v1`, `config/test-codici-errore-identita` | invariati, verdi |
| `dbops/test-comment-al-presente-v1`, `test-corpo-funzione-senza-commenti-v1`, `test-riferimenti-morti-v1`, `test-security-definer-search-path-v1` | invariati, verdi |

Nessun pgTAP asseriva la frase vecchia (cercati per funzione, per codice e per testo: solo commenti che la
citano come storia).

⚠️ **Limite dichiarato:** la prova gira da owner, e i messaggi vengono dall'estratto di prova, non dal loader del
CSV: l'esito vero lo dà la corsa di Tid dopo l'applicazione.
✅ *Corsa di Tid, 2026-11-17:* `20261116-26 … -28` e i due CSV applicati su dbdev, i pgTAP del §11.2 verdi
(compreso il nuovo, coi messaggi dal loader vero). La doc auto-generata dei due guard è rigenerata.

### 11.3 Richiesta a BE/FE (elenco chiuso)

* **R-5 (BE)** — sbloccata il 2026-11-17 (giro 3 applicato):
  1. rigenerare `backend/apps/core/services/error_policies_generated.py`: entra
     `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` (`DATO_ERRATO`), e cambia la nota di
     `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`;
  2. in `backend/apps/core/services/error_messages_fallback.py` il ripiego di `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`
     dice «per questo tipo soggetto», ma il codice ora è solo del ruolo: «Manca un indirizzo obbligatorio per il
     ruolo.»; e la voce nuova, accanto, per `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`: «Manca un
     indirizzo obbligatorio per il tipo soggetto.».

  Nessun'altra ricaduta: il codice del ruolo, che smoke e `test_assegna_ruolo_indirizzi_db` confrontano, non
  cambia; nessun file in `frontend/src` nomina i due codici.

## 12. Giro 4, gli obbligatori: il ripiego sulla natura e il controllo alla cancellazione (team DB, 2026-11-17)

Al via di Tid del 2026-11-17, con la decisione sul §9.5: **vale il ripiego**.

### 12.1 Che cosa

| Pezzo | File (`20_code/anagrafiche/`, salvo dove detto) |
| --- | --- |
| `fn_indirizzi_obbligatori_ruolo(tipo ruolo, natura, giorno)`: il requisito del ruolo, una riga per riga obbligatoria attiva e valida, col tipo richiesto e il ripiego che vale; `BEGIN ATOMIC` | `20261116-29-create-fn-indirizzi-obbligatori-ruolo` |
| `fn_tipo_indirizzo_obbligatorio_per_ruolo`: il corpo legge il requisito (firma invariata; auto-clone e picker non cambiano) | `20261116-30-update-fn-tipo-indirizzo-obbligatorio-per-ruolo-dal-requisito` |
| `fn_guard_indirizzi_obbligatori_ruolo(ruolo, tx)`: il controllo del layer ruolo, in sede unica | `20261116-31-create-fn-guard-indirizzi-obbligatori-ruolo` |
| `fn_guard_indirizzi_obbligatori_soggetto(soggetto, tx)`: il gemello del layer soggetto, regola invariata | `20261116-32-create-fn-guard-indirizzi-obbligatori-soggetto` |
| I due trigger dei titolari chiamano i guard (nessun DDL sui montaggi) | `20261116-33-…-ruoli-guard-indirizzi-required-sede-unica`, `20261116-34-…-soggetti-guard-indirizzi-required-sede-unica` |
| F-1: constraint trigger differiti `AFTER UPDATE OR DELETE` su `indirizzi` e `indirizzi_soggetti`: si giudica il titolare di prima | `20261116-35-create-trg-indirizzi-guard-obbligatori-ruolo`, `20261116-36-create-trg-indirizzi-soggetti-guard-obbligatori-soggetto` |
| Il cambio di natura rigiudica i ruoli del soggetto (constraint trigger differito su `soggetti`, `WHEN` la natura cambia) | `20261116-37-create-trg-soggetti-guard-obbligatori-ruoli` |
| La fixture del ruolo: il primo obbligatorio dal requisito, sulla natura (la quarta copia del §9.5) | `20_code/dbops/20261116-38-update-fn-pgtap-crea-soggetto-ruolo-obbligatori-per-natura` |
| pgTAP nuovo (27 asserzioni) | `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` |
| pgTAP riscritti (§12.2) | `test-fornitore-privato-indirizzi-v1`, `test-indirizzo-obbligatorio-mancante-frase-v1`, `test-indirizzi-istanza-cascata`, `test-indirizzi-fallback`, `vendite/test-snapshot-indirizzi-lotto-v1` |
| Doc: le pagine `manual/` dei due guard dei titolari, della plurale del ruolo e del guard del tipo; la guida *Gestione degli indirizzi* (R9 nuova, R5, tabella dei guard) | `docs/it/dbzero/anagrafiche/manual/`, `docs/it/guide/` |

**Le scelte fatte scrivendo:**

* **Il requisito è un building block a parte**, non il guard: lo leggono anche chi copia (auto-clone), chi propone
  (picker) e la fixture. Il guard dice solo «manca qualcosa?». Regola del 2: prima il requisito era scritto due
  volte, con due regole diverse (§9.5).
* **Un ripiego che il ruolo o la natura non ammettono non conta**, nemmeno quando la natura ammette il tipo: un
  indirizzo di quel tipo, sul ruolo, il guard del tipo non lo lascia scrivere. La frase non lo nomina.
* **Il cambio di natura ha un trigger suo** (`-37`). Con la natura nel requisito, un ruolo può dover avere un tipo
  che prima non doveva, senza che nessun indirizzo e nessun ruolo si scriva: il caso «tipo e ripiego vietati dalla
  natura di prima, uno dei due ammesso da quella nuova». Non era nel perimetro scritto del giro (F-1): lo apre la
  decisione sul ripiego. Il controllo è lo stesso guard.
* **Differiti, e si giudica il titolare di prima.** Sostituire un obbligatorio (cancella e riscrivi), o cancellare
  un ruolo coi suoi indirizzi (la FK verso il ruolo è `NO ACTION`: prima gli indirizzi), passano; il titolare che
  non c'è più tace. Un `UPDATE` che non cambia né il tipo né il titolare non chiede niente.
* **Il guard del soggetto prende la finestra di validità da `fn_tipo_indirizzo_ammesso_per_natura`**, non da un
  predicato ricopiato. Il controllo «la matrice ha righe?» se ne va dai due guard: senza righe obbligatorie il
  requisito è vuoto.
* Codici, frasi e chiavi del contesto non cambiano; il contesto del ruolo aggiunge la natura. Nessun codice nuovo.
* `%TYPE` su parametri, `RETURNS TABLE`, `DECLARE` e su tutte le firme (`COMMENT`, `DROP` dei rollback); la
  fixture ancora anche `p_stato_id`, il ritorno e `v_ruolo_id` (prima nudi; la firma non cambia).

### 12.2 I pgTAP esistenti che il giro tocca

Cercati per oggetto (guard, codici, fixture, madri) e per scrittura (`DELETE`/`UPDATE` su `indirizzi` e
`indirizzi_soggetti`).

* **Tre file toglievano un obbligatorio per preparare il caso** e lo rimettevano dopo (`test-indirizzi-istanza-cascata`,
  `test-indirizzi-fallback`, `vendite/test-snapshot-indirizzi-lotto-v1`): ora la finestra dei differiti si apre
  prima della cancellazione e si richiude quando il titolare è di nuovo completo, e il guard giudica lì. La pulizia
  finale di `test-indirizzi-istanza-cascata` lascia il ruolo senza obbligatorio: lì la finestra resta aperta fino
  al `ROLLBACK`, dichiarato (non c'è una regola da provare).
* **`test-fornitore-privato-indirizzi-v1`**: la riga SEDEOP obbligatoria costruita per i 6-7 e 19-20 torna
  facoltativa prima del 24, che toglie la sede legale dal ruolo della ditta (che la sede operativa non l'ha mai
  avuta). La nota «⛔ NON PROVATO» in testata rimanda al pgTAP nuovo.
* **`test-indirizzo-obbligatorio-mancante-frase-v1`, 7)**: il ripiego costruito era la consegna, che il ruolo
  fornitore non ammette. Con la regola nuova non conta e la frase non lo nomina: è il controesempio della regola,
  non un difetto. Il test aggiunge la riga facoltativa che la ammette.

### 12.3 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-17: i dieci changeSet, catalogo identico dopo
il `ROLLBACK`. Guardrail statici verdi (COMMENT al presente, forme, DDL sui trigger generati, runOnChange,
preCondition, letterali, timestamp, GRANT ai batch, v1 congelato; preambolo pgTAP).

| pgTAP | Esito |
| --- | --- |
| `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1` (nuovo) | interrotto → 27 / 0 |
| … controprova, senza il trigger del cambio di natura (`-37`) | 3, 25, 26 rossi |
| … controprova, senza i trigger della cancellazione (`-35`, `-36`) | 3, 6, 7, 11, 12, 21 rossi |
| i cinque riscritti (§12.2) | verdi, prima e dopo |
| altri 46 file che nominano fixture, guard, codici o madri toccate, o scrivono indirizzi (anagrafiche, vendite, script, dbops, config, rls) | invariati; i rossi preesistenti uguali prima e dopo (`create-soggetto-gestori` 2, `test-distinta-numerazione-registro-v1` 2, `test-rls-billing-account-returning-secondo-emittente` 1, `test-rls-pagamenti-perimetro` 9, `test-esecutivi-ba-coppia-v1` 1) |
| presidi: `test-comment-al-presente-v1`, `test-corpo-funzione-senza-commenti-v1`, `test-riferimenti-morti-v1`, `test-security-definer-search-path-v1`, `test-codice-errore-conforme-v1`, `test-rubinetto-primo-motivo-v1`, `test-catalogo-messaggi-errore-completo`, `test-codici-errore-identita` | verdi |

⚠️ **Limiti dichiarati.** La prova gira da owner; le tabelle lette dai guard non sono sotto RLS. Lo script **non
lancia** `anagrafiche/test-soggetti-ruoli-indirizzi-required` (più transazioni) né
`script/test-fn-disdetta-cliente` (non apre con `BEGIN`): restano alla corsa di Tid dopo l'applicazione.

✅ *Corsa di Tid, 2026-11-17:* `20261116-29 … -38` applicati su dbdev (verificato sul `databasechangelog`), pgTAP
verdi, doc auto-generata rigenerata.

### 12.4 Richiesta a BE/FE (elenco chiuso)

* **R-6 (BE)**, dopo l'applicazione del giro 4 e insieme a R-5 (§11.3), che ora serve anche a un percorso nuovo:
  1. `DELETE` di un indirizzo del ruolo (`views_indirizzi_ruolo.delete` → `delete_indirizzo_ruolo`) e `PATCH` che
     ne cambia il tipo (`update_indirizzo_ruolo`): possono rispondere col rifiuto `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`
     (policy esistente, `DATO_ERRATO`). Un test DB del rifiuto e del ripiego che lo evita;
  2. `DELETE` di un indirizzo del soggetto (`delete_indirizzo_soggetto`):
     `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`, il codice di R-5;
  3. `replace_indirizzo_soggetto` e il `PATCH` del soggetto che cambia la natura stanno in un
     `transaction.atomic()`: il rifiuto arriva **al commit**, all'uscita del blocco, non dall'istruzione.
     Verificare che esca col suo codice e la sua frase e non come errore tecnico;
  4. gli smoke che cancellano o cambiano di tipo indirizzi: `smoke-indirizzi-documento-catena.py` (169, 241) e
     `smoke-fattura-indirizzi-snapshot.py` (149, 157, 168). Se tolgono l'obbligatorio a un ruolo o a un soggetto
     che resta, ora sono rifiutati: la cancellazione va nella stessa transazione della riscrittura, o lascia il
     ripiego.
* **FE**: nessuna chiave nuova (i codici ci sono). Da verificare che l'eliminazione di un indirizzo, dal drawer del
  soggetto e da quello del ruolo, mostri la frase del rifiuto.

### 12.5 Il cambio di natura che chiede un indirizzo nuovo — ✅ si fa (Tid, 2026-11-17)

**Il cambio di natura che chiede un indirizzo che la natura di prima vietava.** Il `PATCH` del soggetto non porta
indirizzi. Se la natura nuova chiede a un ruolo un tipo che la vecchia vietava, l'operatore non lo può scrivere
prima (il guard del tipo lo rifiuta) e il cambio da solo è rifiutato dal guard (`-37`): dall'interfaccia la strada
non c'è. È la stessa forma che il layer soggetto ha già (un obbligatorio della natura nuova che la vecchia vietava).
Il modello lo ammette; nel seed del 2026-11-17 non succede (fatto datato). La forma possibile è un verbo di cambio
natura che riceve anche gli indirizzi da scrivere, nella stessa transazione. Decide Tid se e dove.

✅ *Decisa da Tid il 2026-11-17 (A): si fa.* Non è una decisione nuova: **completa** l'esito COMPLETA del 2026-10-11
([brief-db-cambio-natura-soggetto-conferma-e-pulizia](../work-done/brief-db-cambio-natura-soggetto-conferma-e-pulizia.md)
§2, confermato dal modello del 2026-11-14, §0): «indirizzi obbligatori della natura nuova: l'operatore li aggiunge
nello stesso salvataggio». Quella decisione non è mai stata costruita (il `PATCH` del soggetto non porta
indirizzi, `_UPDATE_SOGGETTO_KEYS`), e valeva per il solo layer soggetto: ora vale anche per i ruoli.

**Giro 5, la forma approvata da Tid il 2026-11-17** (via dopo l'applicazione del giro 4, avvenuta lo stesso giorno):

1. **Un lettore**: dato il soggetto e la natura proposta, gli indirizzi che mancherebbero, sul soggetto e su ogni
   suo ruolo (layer, ruolo, tipo richiesto, ripiego), dal requisito dei due guard: il form sa che cosa chiedere
   prima di salvare (linee-guida-sql §12.6: si propone ciò che il guard accetta).
2. **Una madre**: il cambio di natura con gli indirizzi, in una sola chiamata (linee-guida-sql §5b): aggiorna la
   natura e i dati della riga (P.IVA, flag), poi scrive gli indirizzi dati, sul soggetto e sui ruoli, con le madri
   che esistono; i guard differiti giudicano lo stato finale. Gli indirizzi si scrivono **dopo** il cambio: il guard
   del tipo li giudica sulla natura nuova.
3. **Richiesta BE/FE**: il cambio di natura passa dalla madre; il form, quando la natura cambia, chiede gli indirizzi
   che il lettore elenca.

Il cambio di natura senza indirizzi nuovi resta com'è: il `PATCH` del soggetto, coi suoi motivi.

## 13. Giro 5, il cambio di natura porta con sé gli indirizzi (team DB, 2026-11-17)

Al via di Tid del 2026-11-17 (§12.5), dopo l'applicazione del giro 4.

⚠️ **La forma è cambiata rispetto al §12.5 (Tid, 2026-11-17).** La proposta aveva una madre DB del cambio di natura.
Scrivendo: nel database non c'è un verbo che modifica il soggetto; il `PATCH` del backend scrive la riga con la sua
lista di colonne (`SOGGETTO_UPDATE_COLS`) e i dati societari col loro verbo, in un `transaction.atomic()`. Una madre
DB avrebbe dovuto ricopiare quella lista (regola del 2). Decisione di Tid: **le scritture le compone il backend**,
nella transazione che ha già; il DB dà la lettura e i guard. Il punto 2 del §12.5 è superato da questo.

### 13.1 Che cosa

| Pezzo | File (`20_code/anagrafiche/`) |
| --- | --- |
| `fn_indirizzi_obbligatori_mancanti_ruolo(ruolo, natura, giorno)`: i requisiti del ruolo, sulla natura passata, che nessun indirizzo del ruolo soddisfa; `BEGIN ATOMIC` | `20261116-39-create-fn-indirizzi-obbligatori-mancanti-ruolo` |
| `fn_indirizzi_obbligatori_mancanti_soggetto(soggetto, natura, giorno)`: il gemello del layer soggetto, con la regola del guard; `BEGIN ATOMIC` | `20261116-40-create-fn-indirizzi-obbligatori-mancanti-soggetto` |
| I due guard degli obbligatori leggono i mancanti, sulla natura del soggetto (regola, codici, frasi invariati) | `20261116-41-update-fn-guard-indirizzi-obbligatori-ruolo-dai-mancanti`, `20261116-42-update-fn-guard-indirizzi-obbligatori-soggetto-dai-mancanti` |
| `fn_indirizzi_obbligatori_mancanti(soggetto, natura)`: la lettura per il form, prima il soggetto poi ogni ruolo, col ripiego; `BEGIN ATOMIC`. ⚠️ Dal giro 6 (§14) si chiama `fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli` | `20261116-43-create-fn-indirizzi-obbligatori-mancanti` |
| pgTAP nuovo (11 asserzioni) | `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` |
| pgTAP riscritto: il presidio 1 del giro 4 (il guard arriva al requisito attraverso i mancanti) | `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1` |
| Guida *Gestione degli indirizzi*, R9: il cambio di natura porta gli indirizzi | `docs/it/guide/` |

**Le scelte fatte scrivendo:**

* **La domanda «che cosa manca» ha due lettori** (il guard sulla natura di oggi, il form sulla natura proposta): la
  natura è un **parametro**, non si legge dal soggetto. Regola del 2: i guard la leggono.
* **Gli indirizzi si scrivono dopo la natura.** Il guard del tipo giudica sulla natura del soggetto in quel
  momento: un tipo che la natura di prima vietava si scrive solo a natura cambiata. I guard degli obbligatori sono
  differiti e giudicano lo stato finale.
* **Gli indirizzi vietati dalla natura nuova non sono nella lettura**: sono motivi di `fn_check_cambio_natura_soggetto`
  e si tolgono prima (Q-3 del 2026-11-14, D-4 di questo brief).
* La natura non ha default (§5f). `NULL`: sul soggetto niente, sul ruolo la natura non conta, come nel requisito.
* Completa l'esito COMPLETA del 2026-10-11 (brief del cambio di natura, §2) e lo estende ai ruoli.

### 13.2 Il caso costruito

Nel pgTAP: per il fornitore la consegna obbligatoria (vietata al privato, ammessa alla ditta), per la ditta la
corrispondenza obbligatoria sul soggetto. Il privato fornitore, verso la ditta, deve dare la corrispondenza sul
soggetto e la consegna sul ruolo: senza la consegna il salvataggio è rifiutato col codice del ruolo; con tutti e
due passa, e dopo la lettura sulla natura nuova è vuota.

### 13.3 La prova

`scripts/prova_changeset.py` sullo scratch, 2026-11-17: i cinque changeSet, catalogo identico dopo il `ROLLBACK`.
Guardrail statici verdi.

| pgTAP | Esito |
| --- | --- |
| `test-indirizzi-obbligatori-mancanti-v1` (nuovo) | interrotto → 11 / 0 |
| `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1` (presidio 1 riscritto) | 27 / 0 |
| regressione: gli stessi 51 file del §12.3 (fra cui i due guard riscritti passano da tutti i pgTAP degli obbligatori) | invariati; nessun rosso nuovo, i rossi preesistenti gli stessi del §12.3 |

⚠️ Come nel giro 4, lo script non lancia `test-soggetti-ruoli-indirizzi-required` e `script/test-fn-disdetta-cliente`.

**Corsa di Tid (2026-11-17), giro 5 applicato su dbdev:** `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1`
26 / **1**, il presidio 1. Causa: la riga aggiunta nel giro 5 cercava `anagrafiche.fn_indirizzi_obbligatori_ruolo(`
nel corpo di `fn_indirizzi_obbligatori_mancanti_ruolo`, che è `BEGIN ATOMIC`: `pg_get_functiondef` stampa i nomi
rispetto al `search_path` di chi legge (linee-guida-sql §5c), e col path del runner lo schema non c'è. Sullo scratch
la prova girava con un altro path, ed era verde. Corretta: il nome si cerca senza schema, come le altre condizioni
sulle `BEGIN ATOMIC` dei due test; le condizioni con lo schema restano solo sulle plpgsql (testo conservato). Le
condizioni dei presidi dei due test, rilette su dbdev con il path del runner: vere. Rilanciato da Tid: verde.

**Omonimo, segnalato:** esiste già `script.fn_indirizzi_obbligatori_mancanti(ambito, tipi presenti)`, i tipi
obbligatori di un **documento** per ambito (grammatica unica dei documenti). Significato diverso, nessuna copia; ma
lo stesso nome in due schemi confonde chi cerca. Rinominare la funzione nuova (applicata su dbdev e committata in
`8b354c90e6`, al 2026-11-17 non ancora pushata) vuol dire un changeSet in più: decide Tid.

✅ *Decisa da Tid il 2026-11-18: si rinomina subito.* Nome nuovo
`anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`, nel giro 6 (§14).

### 13.4 Richiesta a BE/FE (elenco chiuso)

* **R-7 (BE)**, dopo l'applicazione del giro 6 (il nome della lettura, §14):
  1. **La lettura.** Il form del cambio di natura deve sapere quali indirizzi chiedere: la risposta di
     `motivi_cambio_natura` (`soggetti_service.py`, la stessa chiamata che oggi rende i motivi di
     `fn_check_cambio_natura_soggetto`) porta anche gli indirizzi mancanti, da
     `SELECT … FROM anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(soggetto, natura proposta)` (nome
     del giro 6, §14; è un `RETURNS TABLE`:
     `SELECT fn(…)` consegnerebbe la tupla in un campo solo). Una riga: `soggetto_ruolo_id` e `tipo_ruolo_id` (NULL =
     il soggetto), `tipo_indirizzo_id`, `ripiego_tipo_indirizzo_id`;
  2. **Il salvataggio.** Il `PATCH` del soggetto (`update_soggetto` del service) accetta due chiavi nuove: gli
     indirizzi del soggetto e gli indirizzi per ruolo (`soggetto_ruolo_id` + elenco), con la grammatica degli
     elementi che c'è già. Nel `transaction.atomic()` che esiste, **dopo** la riga del soggetto e i dati societari:
     `anagrafiche.fn_crea_indirizzi_soggetto(soggetto, elenco)` e, per ogni ruolo,
     `anagrafiche.fn_crea_indirizzi_ruolo(ruolo, elenco)`. Il ruolo deve essere del soggetto (controllo di
     appartenenza, come per gli altri endpoint del ruolo). Il rifiuto, se manca qualcosa, arriva al commit: vale il
     punto 3 di R-6;
  3. **I test.** Un test DB del percorso intero: privato verso ditta con un obbligatorio nuovo, senza l'indirizzo
     (rifiuto col codice) e con l'indirizzo (passa).
* **R-7 (FE)**: nel drawer del soggetto, quando l'operatore cambia la natura, il form mostra gli indirizzi mancanti
  (sul soggetto e sui ruoli, col ripiego come alternativa) e li manda nello stesso salvataggio. Le etichette dei
  tipi e dei ruoli vengono dai cataloghi che il form usa già; nessuna chiave i18n nuova dal DB.

## 14. Giro 6, il nome della lettura e il privato dal builder (team DB, 2026-11-18)

Le due decisioni di Tid del 2026-11-18: l'omonimo si corregge subito (§13.3), e i tre pgTAP passano sul builder
(§10.3).

### 14.1 Che cosa

| Pezzo | File |
| --- | --- |
| La lettura del form prende il nome `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`: `DROP` della firma vecchia, poi il `CREATE` con corpo, colonne e `COMMENT` del `-43` (linee-guida-sql §5f); `BEGIN ATOMIC` | `20_code/anagrafiche/20261116-44-rename-fn-indirizzi-obbligatori-mancanti-soggetto-e-ruoli` |
| Il pgTAP della lettura chiama il nome nuovo; il presidio 2 vieta anche il nome vecchio in `anagrafiche` | `test-indirizzi-obbligatori-mancanti-v1` |
| Il privato dal builder `dbops.fn_pgtap_crea_soggetto_pf`, al posto di `INSERT` su `soggetti`, contatto e indirizzi scritti a mano | `create-cliente`, `test-fn-update-cliente-v1`, `test-soggetti-ruoli-indirizzi-required` |
| Il link della guida *Gestione degli indirizzi* (R9) | `docs/it/guide/gestione-degli-indirizzi.md` |

**Le scelte fatte scrivendo:**

* **Il nome** si affianca alle due letture che compone (`_soggetto`, `_ruolo`) e dice che cosa le distingue: il
  soggetto e tutti i suoi ruoli. Nessun chiamante nel database né nel backend (R-7 non è costruita): l'unico che la
  verifica è il suo pgTAP. Un changeSet nuovo, non una modifica del `-43`, che su dbdev è applicato.
* **`test-fn-update-cliente-v1` perde l'esenzione `pgtap-differiti`.** Era un debito dichiarato
  (brief-db-pgtap-runner-rls-baseline §21: «la correzione vera è completare la fixture»). Con il builder del
  soggetto e quello del ruolo (`dbops.fn_pgtap_crea_soggetto_ruolo`, che scrive anche gli indirizzi del ruolo)
  la fixture è completa, e il file chiude con `SET CONSTRAINTS ALL IMMEDIATE` dopo il cliente.
* **`test-soggetti-ruoli-indirizzi-required`**: il soggetto di ogni caso dal builder, poi la finestra differita
  riaperta, perché il caso si regge su di essa. Via la pulizia iniziale per codice `TST-RUOLO-IND-*`, che il
  builder non usa: era fuori transazione e cercava un residuo che con il `ROLLBACK` non c'è.
* I codici fiscali scritti nei file (`PGTPCL00A01H501Y`, `RSSMRA80A01H501U`, `QMMTPK69T01G127B`) non ci sono più:
  il builder ne sceglie uno libero.

### 14.2 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-18, col `-44` in testa: catalogo identico
dopo il `ROLLBACK`. Guardrail statici verdi (forme, letterali, COMMENT al presente, runOnChange, preCondition,
timestamp, DDL sui trigger generati, GRANT ai ruoli batch; preambolo pgTAP su tutti i 1090 file).

| pgTAP | Con l'estratto |
| --- | --- |
| `test-indirizzi-obbligatori-mancanti-v1` | interrotto → 11 / 0 (senza il `-44` la funzione non c'è) |
| `create-cliente` | 8 / 0 |
| `test-fn-update-cliente-v1` | 20 / 0, ora con `IMMEDIATE` a fixture completa |
| `test-soggetti-ruoli-indirizzi-required` | ⚠️ non lanciato: il file apre una transazione per caso, e lo script ne vuole una sola. Lo dice la corsa di Tid |

✅ *Corsa di Tid, 2026-11-18:* `20261116-44` applicato su dbdev, i quattro pgTAP verdi (compreso
`test-soggetti-ruoli-indirizzi-required`), doc auto-generata rigenerata.

⚠️ **Limite dichiarato:** la prova gira da owner. `test-soggetti-ruoli-indirizzi-required` ha anche un residuo che
questo giro non tocca: l'`INSERT … ON CONFLICT` su `anagrafiche.indirizzi_dettaglio` sta fuori transazione, e quindi
committa.

### 14.3 Richiesta a BE/FE

Nessuna nuova: R-7 (§13.4) usa il nome nuovo, ed è già scritto lì.

### 14.4 Il censimento saltato: i COMMENT delle due sorelle (`20261116-45`)

Rileggendo la doc rigenerata: i `COMMENT` di `fn_indirizzi_obbligatori_mancanti_ruolo` (`-39`) e `_soggetto` (`-40`)
dicono chi li legge, e nominavano ancora `anagrafiche.fn_indirizzi_obbligatori_mancanti`. La ricerca sul nome li
aveva trovati, ed erano stati scartati come «non chiamanti»: ma il nome era citato nel testo, non chiamato, e per la regola
del §5f si censiscono anche i testi che lo citano. Il `-45` riscrive i due `COMMENT` (cambia solo il nome citato);
il rollback rimette i testi di prima. Prova sullo scratch, 2026-11-18: estratto per intero, catalogo identico dopo
il `ROLLBACK`, `test-indirizzi-obbligatori-mancanti-v1` 11 / 0, guardrail statici verdi.

Dopo il `-45`, nel repository il nome vecchio resta solo nella storia (questo brief, gli YAML del `-39`, `-40`,
`-43`) e in `script`, dove è il nome dell'altra funzione.

## 15. Giro 7, il titolare dell'indirizzo non cambia (team DB, 2026-11-18)

Le due chiusure proposte il 2026-11-18 prima dell'archiviazione, col via di Tid lo stesso giorno: il lucchetto del
§9.5 («`soggetto_ruolo_id` è identità», Tid) e l'upsert fuori transazione del §14.2.

### 15.1 Che cosa

| Pezzo | File |
| --- | --- |
| Due righe del registro dei lock: `indirizzi.soggetto_ruolo_id` e `indirizzi_soggetti.soggetto_id` | `80_data/sql/dbops/automation_lock_columns.csv` |
| Due codici `CONFLITTO_STATO`, uno per livello: `E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE`, `E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE`, con le frasi (id 1512, 1513) | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` |
| Il runner dei lock su `anagrafiche`, subito (su dbdev il job dei lock è serale) | `90_end/20261116-46-provision-lock-indirizzi-titolare` |
| pgTAP nuovo (5 asserzioni) | `db/pgtap/anagrafiche/test-indirizzi-titolare-immutabile-v1.sql` |
| L'indirizzo del ruolo del caso 2 in forma libera; via stradario e upsert | `test-soggetti-ruoli-indirizzi-required` |
| Guida *Gestione degli indirizzi*: R10 | `docs/it/guide/gestione-degli-indirizzi.md` |

**Le scelte fatte scrivendo:**

* **Il gemello del layer soggetto entra nello stesso giro.** Il §9.5 nominava il solo indirizzo di ruolo; il
  difetto è identico su `indirizzi_soggetti.soggetto_id`: il guard del tipo è `UPDATE OF tipo_indirizzo_id`, e un
  indirizzo spostato su un altro soggetto non sarebbe giudicato sulla natura nuova. Stessa regola, stesso
  significato: chiudere un livello solo sarebbe un'asimmetria.
* **Il lucchetto, non un ramo del guard** (linee-guida-trigger, «una FK di appartenenza»): il caso modello è
  `soggetti_ruoli.soggetto_id` (`20261019-86`). Il trigger lo monta il runner, il registro lo governa.
* **Nessuno scrive le due colonne dopo la nascita**: il backend non le ha fra le colonne modificabili
  (`INDIRIZZO_RUOLO_UPDATE_COLS`; per il soggetto non c'è un `UPDATE`), e nessuna funzione del database fa un
  `UPDATE` su `indirizzi` o `indirizzi_soggetti` (letto da `pg_get_functiondef` su dbdev, 2026-11-18). Nessun seed di
  `80_data` o `90_end` le aggiorna. `dbops.fn_lock_columns_divergenze('AUTO', ARRAY['anagrafiche'])` su dbdev,
  2026-11-18: nessuna divergenza, quindi il runner monta i due lucchetti e non tocca altro.
* **Chi parla per primo.** Il lucchetto ha il nome del template del framework (`…_a10_lock_columns_upd`), e fra i due
  `a10` di `indirizzi` parla prima `trg_indirizzi_a10_guard_istanza_ins_upd`: un indirizzo che porta un'istanza,
  spostato sul ruolo di un altro soggetto, è rifiutato con `E_ISTANZA_ALTRO_SOGGETTO` (il test 8 di
  `test-istanza-dello-stesso-soggetto-v1` resta com'è). Le linee guida vorrebbero l'immutabilità per prima (fase
  `a05`); il nome del lucchetto lo decide il template, uguale per tutte le tabelle, e il rifiuto c'è comunque. È lo
  stesso ordine del caso modello sul ruolo.
* **L'upsert del pgTAP non si sposta dentro i casi: si toglie.** L'indirizzo del ruolo si scrive in forma libera,
  come gli altri pgTAP: nessuna scrittura su `indirizzi_dettaglio`, tabella condivisa.

### 15.2 Il caso costruito

Due privati dal builder, ciascuno col ruolo cliente e i suoi indirizzi (`fn_pgtap_crea_soggetto_ruolo`).
L'indirizzo di ruolo di A spostato sul ruolo di B: rifiutato col codice del ruolo; riscritto sul ruolo di A: passa.
L'indirizzo del soggetto A spostato su B: rifiutato col codice del soggetto; riscritto su A: passa.

### 15.3 La prova

`scripts/prova_changeset.py` sullo scratch `zeroerp_ruoli`, 2026-11-18. Le righe dei tre CSV non le carica lo
script: entrano da un changeSet di prova nello scratchpad (`INSERT` delle stesse righe), in testa al `-46`.
Catalogo identico dopo il `ROLLBACK`. Guardrail statici verdi (forme, letterali, COMMENT al presente, runOnChange,
preCondition, timestamp, DDL sui trigger generati, GRANT ai ruoli batch; preambolo pgTAP).

| pgTAP | Senza → con l'estratto |
| --- | --- |
| `test-indirizzi-titolare-immutabile-v1` (nuovo) | 2 / 3 → 5 / 0 (senza il lucchetto passano solo i due «riscrivere lo stesso») |
| `test-soggetti-ruoli-indirizzi-required` | ⚠️ lo script non lo lancia (una transazione per caso). Provato il solo caso 2, quello toccato, in una copia a transazione unica nello scratchpad: 4 / 0. Il file intero lo dice la corsa di Tid |
| regressione: `test-istanza-dello-stesso-soggetto-v1`, `test-indirizzo-libero-due-forme-v1`, `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1`, `test-fornitore-privato-indirizzi-v1`, `test-cambio-natura-soggetto-v1`, `test-indirizzi-obbligatori-mancanti-v1`, `test-fn-pgtap-crea-soggetto-pf-v1`, `create-cliente`, `test-fn-update-cliente-v1`, `test-copia-indirizzo-v1` | invariati, verdi |
| presidi: `dbops/test-lock-columns-convergenza`, `test-non-editable-fields-dal-lock-vivo-v1`, `test-codice-errore-conforme-v1`, `test-vw-codici-errore-motivo-nominato`, `test-registri-automazioni-nomi-non-vuoti-v1`, `test-marcatori-automazione-senza-esecutore-v1`, `test-block-attivo-si-ritira-v1`, `test-delete-block-*`; `config/test-codici-errore-obsoleto-dal`, `test-messaggi-errore-causa-soluzione-non-vuote-v1` | invariati, verdi |

✅ *Corsa di Tid, 2026-11-18:* i tre CSV e il `-46` applicati su dbdev, `test-indirizzi-titolare-immutabile-v1` e
`test-soggetti-ruoli-indirizzi-required` (il file intero) verdi, doc auto-generata rigenerata.

⚠️ Le `preCondition` del `-46` lo script le legge prima delle righe di prova (attese 2, trovate 0 sullo scratch):
all'apply vero `80_data` gira prima di `90_end`. ⚠️ La prova gira da owner. ⚠️ Gli id 1512 e 1513 di
`messaggi_errore.csv` erano liberi alla scrittura (2026-11-18, massimo 1511); con un'altra sessione DB aperta, vanno
riletti prima dell'apply.

### 15.4 Richiesta a BE/FE (elenco chiuso)

* **R-8 (BE)**, dopo l'applicazione del giro 7: rigenerare `error_policies_generated.py` (`manage.py
  genera_error_policies`): i due codici nuovi, `CONFLITTO_STATO`; e i loro ripieghi in `error_messages_fallback.py`,
  accanto a quello di `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE` (lo pretende `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`).
  Proposte: «Un indirizzo appartiene per sempre al suo ruolo: se è sul ruolo sbagliato si elimina e si ricrea.» e
  «Un indirizzo appartiene per sempre al suo soggetto: se è sul soggetto sbagliato si elimina e si ricrea.» Nessun
  percorso del BE scrive le due colonne: nessun'altra modifica.

### 15.5 Che cosa resta all'archiviazione

Niente da portare in un brief nuovo: il §7 è sviluppo acquisti (marcato lì), il §9.5 è chiuso da questo giro,
l'upsert del §14.2 pure. Restano R-5 … R-8 del BE/FE.

## 16. Le richieste al BE/FE, fatte (team BE/FE, 2026-11-18)

R-5 … R-8 scritti e provati sul DB vero (dbdev, 2026-11-18); non committati.

| Richiesta | Che cosa | Prova |
| --- | --- | --- |
| R-5, R-8 | `error_policies_generated.py` rigenerato (entrano i tre codici, nessun'altra voce cambia); i ripieghi in `error_messages_fallback.py` | `test_error_policies_classi` verde; nessun codice vivo del DB senza policy o ripiego |
| R-6 | rifiuti di `DELETE`, `PATCH` e `PUT` al commit, col codice del layer; `smoke-indirizzi-documento-catena` col controllo del commit (caso 7) | `test_indirizzi_obbligatori_db` 11 / 0; smoke catena verde |
| R-7 | `motivi_cambio_natura` porta `indirizzi_mancanti`; il `PATCH` del soggetto accetta `indirizzi` e `indirizzi_ruoli`; nel `SoggettoDrawer` un `IndirizziMancantiForm` per titolare | stesso test, casi 6 … 10 |

⚠️ **Un percorso rotto dal giro 4, trovato verificando R-6.** La modifica di un indirizzo del ruolo, nel
`IndirizziSoggettoDrawer`, era `DELETE` + `POST` in due richieste: la `DELETE` dell'unico obbligatorio, giudicata al
suo commit, era rifiutata, e col `silent` della chiamata il salvataggio falliva senza messaggio. Ora è un `PUT`
(`replace_indirizzo_ruolo`, gemello di `replace_indirizzo_soggetto`: cancella e riscrive nello stesso
`transaction.atomic()`), con la sua sezione in `api_indirizzi_ruolo.md` (§3-bis). Il `PATCH` non bastava: non risolve
una via nuova in un dettaglio. Test: `test_sostituire_l_unico_obbligatorio_passa`.

`smoke-fattura-indirizzi-snapshot` non è cambiato: chiude in `ROLLBACK` e i guard sono differiti, quindi da solo non
li esercita; provato a parte col commit anticipato in coda (copia nello scratchpad), lo stato finale passa.

Dalla revisione (2026-11-18): `IndirizziMancantiForm` rifaceva la matrice a **ogni** rilettura dei motivi
(P.IVA o flag digitati, salvataggio rifiutato), e `setMatrice` svuotava gli indirizzi compilati: con un ripiego,
quello scritto sul ripiego partiva col tipo richiesto. Ora segue la firma dei tipi
(`IndirizziMancantiForm.spec.js`). Il «Cambia» del ruolo come una sola `PUT` ha il suo spec (caso 4 di
`IndirizziSoggettoDrawer.spec.js`). `api_soggetti.md` allineata: §4 (`indirizzi`, `indirizzi_ruoli`, i rifiuti
al commit), §8 (obbligatori su sostituzione ed eliminazione), §13 (`indirizzi_mancanti`).

Decisi da Tid nella revisione (2026-11-18):

* gli indirizzi del PATCH vogliono una natura **diversa** da quella salvata, non solo la chiave: la natura di oggi
  rimandata apriva una seconda porta di scrittura senza la copia degli obbligatori. Test
  `test_indirizzi_con_la_natura_di_oggi_rifiutati` (9b);
* il collegamento form/composable dell'indirizzo, ricopiato in cinque componenti, è il BB
  `collegaIndirizzoSoggettoForm` (regola del 2), col presidio che confronta le sue chiavi con prop ed eventi del form.

Dalla prova a video (Tid, 2026-11-18): la dialog di «Copia come…» non diceva da dove né verso dove. Ora porta le
righe **Da** e **Verso** (`CopiaIndirizzoDialog`, casi 4 e 5 degli spec). La copia sul servizio aperto, invece che
sulla chiave della sorgente, è un cambio del verbo e non di questo brief: sta in
[brief-db-copia-indirizzo-destinazione](../work-in-progress/brief-db-copia-indirizzo-destinazione.md), e non blocca l'archiviazione.

Chiuso il 2026-11-19, su richiesta di Tid dopo la sua prova a video: archiviato in `work-done/`; il commit è di Tid.
