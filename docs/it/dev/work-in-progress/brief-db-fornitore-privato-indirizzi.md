# Brief DB — Il privato può essere fornitore, senza inventarsi una sede legale

## ⏭️ Chi riparte — aggiornato al 2026-11-16

**Riparte: team DB, col giro 1, al via di Tid.** Tutte le decisioni sono prese (2026-11-16): la (C), D-4
(stesso trattamento di Q-3), D-5 (nessuna riga da trattare), F-1 (giro 4, qui). La (C) è confermata (2026-11-16, §8.3-bis): il fornitore come il cliente,
sul ruolo solo `FATT` obbligatorio. D-1 revocata, D-2 e D-3 senza oggetto. Il brief è stato riverificato sul catalogo di dbdev
(§8): il caso e i due difetti reggono, ma la proposta (A) da sola non basta e il §4.2 tocca più sedi di quelle
scritte. Nessun changeSet scritto.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | ✅ riverifica sullo stato di sviluppo (2026-11-16) | §8.1-8.2 | — |
| 2 | Tid | ✅ le decisioni: la (C), D-4, D-5, F-1 (2026-11-16) | §8.3, §8.3-bis, §8.4 | 1 |
| 3 | team DB | censimento degli indirizzi di ruolo non ammessi dalla natura del soggetto (sola lettura): ✅ fatto il 2026-11-16, zero righe; si ripete prima dell'applicazione del giro 1 | §8.3 D-5 | 2 |
| 4 | team DB | giro 1: CSV della matrice `FO` (riga 13 non obbligatoria, §8.3-bis), guard del §4.2, motivo nella check del ruolo, auto-clone filtrato per natura; `manual/fn_crea_fornitore.md` e guida degli indirizzi | §4.2, §8.2, §8.3-bis | 2, 3 |
| 5 | Tid | giro 1 applicato, pgTAP | §5 | 4 |
| 6 | team DB | giro 2: motivo nel cambio di natura, picker del tipo di ruolo con la natura | §8.2 (4, 3) | 5 |
| 7 | BE/FE | il picker del tipo di ruolo con la natura (percorso al §6) | §6 | 6 |
| 8 | team DB | giro 3: la frase di `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` per i due chiamanti | §4.3, §8.2 (6) | 2 |
| 8-bis | team DB | giro 4: gli obbligatori ricontrollati alla cancellazione e al cambio di tipo (F-1) | §8.4 | 5 |
| 9 | BE/FE | il fornitore privato provato sul DB vero | §6 | 5 |
| 10 | chi chiude | archiviazione in `work-done/` | — | tutti |

Decisioni aperte di Tid: nessuna. Prese il 2026-11-16: la (C), D-4, D-5, F-1. Lavoro fatto da committare: questo aggiornamento del
brief.

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
> **Stato:** 🔵 da fare.
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

## 7. Fuori perimetro: il documento passivo del fornitore privato

Il fornitore privato non manda fatture dallo SdI. Quando si aprirà il ciclo della fattura
passiva (cantiere acquisti, oggi col solo modello, e `contabilita` vuoto) serviranno:

* la registrazione manuale del documento come **ricevuta o nota compenso**, non come fattura;
* il calcolo della ritenuta d'acconto e del netto da pagare (i dati del fornitore ci sono già);
* la scadenza del versamento F24 e i dati per la Certificazione Unica.

Nessun brief aperto lo prevede oggi: va annotato fra le decisioni aperte del cantiere acquisti
(PROJECT_CONTEXT), non risolto qui.

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
