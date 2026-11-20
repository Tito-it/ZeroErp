# Brief DB — La copia di un indirizzo va dove lavora l'operatore

## ⏭️ Chi riparte — aggiornato al 2026-11-20

**Riparte: Tid, con la prova a video e il commit del giro BE/FE (§8).** Il giro 1 del DB è applicato su dbdev e
committato (changeSet `20261117-29` … `-32`). R-1 e R-2 sono fatte il 2026-11-20 sul branch `dev/backend-tid`,
non committate: i test sul DB vero e lo spec del drawer sono verdi (§8.3), e la revisione dello stesso giorno ha
corretto tre punti (§8.5). D-1 … D-4 decise, tutte come proposte.
La verifica DB del 2026-11-20 (§4.1) corregge il §4: l'istanza di destinazione la giudica il guard che c'è già
(niente codice nuovo, R-3 ritirata), e il motivo «nessun tipo» esce dalla riga e lo porta il picker della
destinazione (D-4).

**Brief vicini verificati** (2026-11-20): nessuno aperto in `work-in-progress/`. Il precedente è archiviato,
[brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md): questo ne revoca §4.6 punto 3
(D-1 del 2026-11-15, «la copia resta nella chiave della sorgente») e ne cambia R-3/R-4 (le superfici della lista).

| # | Chi | Che cosa | Dove | Dopo |
| --- | --- | --- | --- | --- |
| 1 | Tid | D-1 … D-3 ✅ 2026-11-19 | §5 | — |
| 2 | Tid | D-4 ✅ 2026-11-20, strada (a) | §5 | — |
| 3 | team DB | giro 1: i due verbi con la destinazione (dal ruolo, dal soggetto), il motivo secondo D-4, il registro `config.azioni_riga`, ritiro della firma vecchia, pgTAP e doc ✅ 2026-11-20, scritto e provato | §7 | 2 |
| 4 | Tid | applicazione su dbdev, pgTAP verdi, doc auto-generata, commit ✅ 2026-11-20 | — | 3 |
| 5 | BE/FE | R-1, R-2 ✅ 2026-11-20, scritte e provate | §8 | 4 |
| 5-bis | BE/FE | revisione del giro (`/verifica`) ✅ 2026-11-20 | §8.5 | 5 |
| 6 | Tid | prova a video del caso del §1, commit del giro BE/FE | §8.4 | 5-bis |
| 7 | chi chiude | archiviazione in `work-done/` | — | tutti |

Decisioni aperte di Tid: nessuna. Lavoro da committare: il giro BE/FE (§8.1) e questo brief.

## 1. Il caso (prova a video di Tid, 2026-11-18)

Il cliente ha un servizio (un'istanza utility). L'operatore apre gli indirizzi **del servizio**, sceglie la
Spedizione **del ruolo** e la copia come Fatturazione: vuole la fatturazione **del servizio** su cui sta lavorando.

Il verbo invece la scrive sul **ruolo**: `anagrafiche.fn_copia_indirizzo_ruolo(ruolo, indirizzo, tipi[])` copia
«nello stesso ruolo e nella stessa istanza della sorgente» (COMMENT del verbo). È la regola decisa in
[brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md) (§4.6 punto 3, D-1): la copia
resta nel layer e nell'istanza della sorgente, e la copia **fra layer** è un gesto diverso, lasciato fuori.

Il caso di Tid è un gesto con una **destinazione** diversa dalla sorgente, e il modello di oggi non sa dirlo: copiando
dal servizio una riga del ruolo, la copia non arriva dove l'operatore la cerca, e nessun errore lo segnala.

## 2. Che cosa c'è già (FE, 2026-11-18, non committato)

`CopiaIndirizzoDialog` mostra due righe: **Da** (tipo, indirizzo, titolare della sorgente: il soggetto, il ruolo,
il servizio) e **Verso** (oggi «il ruolo, dove sta l'indirizzo di partenza», cioè ciò che il verbo fa). È una
descrizione di ciò che succede: non cambia dove va la copia.

## 3. Che cosa si chiede

La copia scrive sulla **chiave di destinazione** che il chiamante indica: il ruolo (istanza `NULL`) o una sua
istanza. La sorgente può stare in un'altra chiave dello stesso ruolo, e nel layer del soggetto (D-2).

## 4. La proposta per il giro 1 (team DB)

1. **Il verbo con la destinazione.** `fn_copia_indirizzo_ruolo(p_soggetto_ruolo_id, p_indirizzo_id, p_tipi[],
   p_istanza_utility_id_destinazione)`, dove la destinazione è il ruolo stesso (istanza `NULL`) o una sua istanza.
   Il parametro è **obbligatorio** e la firma di oggi a tre argomenti **si ritira** (D-3): niente `DEFAULT NULL`,
   che accanto alla firma vecchia darebbe due overload ambigui su tre argomenti. Per dire «il ruolo» si passa
   `NULL` esplicito.
2. ⚠️ *Superato dal §4.1 punto A: l'istanza è del soggetto, non del ruolo, e il guard c'è già.*
   **L'istanza di destinazione dev'essere del ruolo**: altrimenti un codice `NON_TROVATO` (proposta
   `E_INDIRIZZO_COPIA_DESTINAZIONE_NON_TROVATA`). La sorgente resta «del ruolo» (`E_INDIRIZZO_RUOLO_NON_TROVATO`),
   in qualunque sua chiave.
3. ⚠️ *La parte sulla check di riga è superata dal §4.1 punto B (D-4).*
   **La check e il picker giudicano la destinazione**, non la sorgente: «tipo già presente» si guarda sulla chiave
   di destinazione. Il picker c'è già (`fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza)`), con l'istanza di
   destinazione. La check di riga (`fn_check_copia_indirizzo_ruolo`, «Copia come…» spento col motivo) va rivista:
   oggi dice se la copia è possibile sulla chiave della sorgente.
4. **La scrittura resta della singolare** `fn_crea_indirizzo_ruolo`, con l'istanza di destinazione: tutti i guard
   della tabella valgono, tutto o niente come oggi.
5. **Il gemello dal soggetto al ruolo** (D-2): la sorgente è una riga di `indirizzi_soggetti` del soggetto del
   ruolo, la destinazione una chiave del ruolo (il ruolo o una sua istanza). Stessa regola dei punti 2-4: la
   sorgente dev'essere del soggetto del ruolo, la check e il picker giudicano la destinazione, la scrittura è
   `fn_crea_indirizzo_ruolo`. Il nome lo sceglie il team DB, nella famiglia dei verbi di copia.

⚠️ *L'elenco pgTAP qui sotto è corretto dal §4.1 punto E.* pgTAP: la copia da una riga del ruolo verso una sua
istanza; da un'istanza al ruolo; verso un'istanza di un altro ruolo, rifiutata; «tipo già presente» sulla
destinazione, non sulla sorgente; il tipo assente sulla sorgente e presente sulla destinazione, e il contrario. Per
il gemello: dal soggetto al ruolo e a una sua istanza; una riga di un altro soggetto, rifiutata. La firma vecchia a
tre argomenti non esiste più.

### 4.1 Verifica DB del 2026-11-20 — correzioni al §4

Letti sul contratto (doc auto-generata, allineata: nessun changeSet sugli oggetti dopo la sua rigenerazione) e su
`config.azioni_riga`.

**A. L'istanza di destinazione la giudica il guard che c'è già: niente codice nuovo.** Un'istanza è del
**soggetto**: `anagrafiche.istanze_utilities` ha `soggetto_id`, non `soggetto_ruolo_id`. Il modello non sa dire
«istanza di un altro ruolo»: un'istanza del soggetto vale per ogni suo ruolo. La regola che il modello ha già è
«l'istanza è del soggetto del ruolo», ed è di `anagrafiche.trgfn_guard_istanza_del_ruolo` sulla tabella
(`E_ISTANZA_ALTRO_SOGGETTO`), che la singolare `fn_crea_indirizzo_ruolo` attraversa per ogni riga. Un codice della
copia per la stessa regola sarebbe una seconda copia del guard (regola del 2): `E_INDIRIZZO_COPIA_DESTINAZIONE_NON_TROVATA`
non nasce, e con lui la R-3. Un'istanza inesistente la rifiuta la FK `fk_indirizzi_istanze_utilities`, come per
«Aggiungi». ⚠️ Legare l'istanza al ruolo (non al soggetto) sarebbe un cambio di modello per **tutti** gli indirizzi
del ruolo, non della copia: non è in questo brief.

**B. Il motivo «nessun tipo» non è più di riga (D-4).** `fn_check_copia_indirizzo_ruolo(indirizzo)` dice
`NESSUN_TIPO_PROPONIBILE` quando il picker della chiave **della sorgente** non ha un tipo ammesso. Con D-1 la chiave
giudicata è quella di destinazione, e allora il motivo **non dipende più dalla riga**: è lo stesso per tutte le righe
del drawer. La vista per riga `anagrafiche.vw_indirizzi_ruolo_azioni`, che è la `superficie` di
`COPIA_INDIRIZZO_RUOLO` in `config.azioni_riga`, non può conoscere la chiave del drawer. Le strade sono in D-4.

**C. Il gemello dal soggetto al ruolo (§4 punto 5) è un'azione di riga nuova.** In contesto ruolo, le righe del
soggetto della cascata oggi portano l'azione `COPIA_INDIRIZZO_SOGGETTO` (superficie `vw_indirizzi_soggetti_azioni`,
verbo `fn_copia_indirizzo_soggetto`), che copia sul soggetto. Con D-1 e D-2, in contesto ruolo quelle righe copiano
sul ruolo: verbo nuovo, e una riga nuova in `config.azioni_riga` (nome dal team DB, superficie e check secondo D-4).
In contesto soggetto resta `COPIA_INDIRIZZO_SOGGETTO`, invariata: la chiave del drawer è il soggetto.

**D. La sorgente del gemello**: la riga di `indirizzi_soggetti` dev'essere del soggetto del ruolo, col codice che
c'è già, `E_INDIRIZZO_SOGGETTO_NON_TROVATO`. Il picker e la scrittura sono quelli del ruolo (§4 punti 3-4).

**E. pgTAP, al posto dell'elenco del §4.**

* ruolo: da una riga del ruolo verso una sua istanza; da un'istanza al ruolo; da un'istanza a un'altra istanza
  dello stesso soggetto; verso un'istanza di **un altro soggetto**, rifiutata con `E_ISTANZA_ALTRO_SOGGETTO` (il
  caso «istanza di un altro ruolo» non esiste nel modello); «tipo già presente» sulla destinazione e non sulla
  sorgente, nei due versi; tutto o niente su due tipi col secondo rifiutato sulla destinazione;
* gemello: dal soggetto al ruolo e a una sua istanza; una riga di un altro soggetto, rifiutata
  (`E_INDIRIZZO_SOGGETTO_NON_TROVATO`);
* il motivo «nessun tipo», secondo D-4, costruito su una destinazione senza tipi ammessi e con la sorgente che ne
  ha;
* la firma a tre argomenti non esiste più (`hasnt_function`);
* da adeguare alla firma nuova: `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql`,
  `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql`; `test-azioni-riga-registro-v1.sql` verde con le righe del
  registro cambiate.

## 5. Decisioni di Tid — ✅ decise il 2026-11-19, come proposte

* **D-1 — La destinazione è la chiave del drawer.** ✅ Sì. Il FE manda sempre la chiave su cui l'operatore
  lavora (il ruolo o il servizio aperto). Una copia sulla chiave della sorgente resta possibile aprendo quella chiave.
* **D-2 — Anche dal soggetto al ruolo.** Nella cascata, in contesto ruolo, la lista mostra anche gli indirizzi del
  soggetto, e oggi la loro copia resta sul soggetto. ✅ Sì, nello stesso giro, perché è lo stesso gesto (la
  destinazione è la chiave del drawer) e un'asimmetria si chiude subito.
* **D-3 — La firma.** ✅ La firma vecchia si ritira e la destinazione diventa obbligatoria. Il progetto non è
  in produzione e il chiamante è uno solo, il BE.

### ✅ Decisa il 2026-11-20, strada (a)

* **D-4 — Dove va il motivo «nessun tipo» (§4.1 B).** ✅ Strada (a), come proposta. Le strade:
  * **(a) ✅ scelta: il motivo esce dalla riga.** Se la chiave del drawer non ammette nessun tipo, sono spenti
    insieme «Aggiungi» e «Copia come…», e il motivo lo porta già il picker della destinazione
    (`fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza)`, nessuna riga con `ammesso`). Le due check di riga del
    ruolo si ritirano (la vista di azioni e la check), e la riga del registro `config.azioni_riga` si spegne.
    Perché: un motivo uguale per tutte le righe è un motivo del drawer, e il drawer lo ha già. ⚠️ Come si è
    scritto nel giro 1 (§7.2): il verbo **non** solleva `E_INDIRIZZO_COPIA_NESSUN_TIPO`, e il registro non ha
    righe «col solo verbo» (superficie, colonne e check sono `NOT NULL`);
  * (b) scartata: una check con la destinazione, `fn_check_copia_indirizzo_ruolo(indirizzo, istanza_destinazione)`, letta
    dal BE come funzione e non come vista: tiene la forma «riga spenta col motivo», ma il motivo resta uguale su
    ogni riga e la superficie del registro smette di essere una vista.

  Con (a) il drawer non ha più «Copia come…» spento riga per riga; con (b) sì, con lo stesso testo ovunque.

## 6. Richieste a BE/FE (dopo il giro 1)

⚠️ *Completate il 2026-11-20 (§4.1): R-1 e R-2 portano anche le superfici della lista; R-3 ritirata.*
✅ *R-1 e R-2 fatte il 2026-11-20: §8.*

* **R-1 (BE)**: `POST /ruoli/{id}/indirizzi/{id}/copia/` prende `istanza_utility_id` di destinazione (assente =
  il ruolo), e lo passa al verbo; il gemello per la sorgente del soggetto (D-2), con la stessa destinazione: in
  contesto ruolo, le righe del livello soggetto della cascata chiamano il verbo nuovo, non più
  `fn_copia_indirizzo_soggetto`. La lista `GET ruoli/<id>/indirizzi/` (D-4 a) non unisce più
  `vw_indirizzi_ruolo_azioni` né, sul livello soggetto, `vw_indirizzi_soggetti_azioni` (le colonne
  `copia_blocco_reason*` escono dalle righe del ruolo). La lista
  `GET soggetti/<id>/indirizzi/` (contesto soggetto) non cambia. Codici: nessuno nuovo
  (`E_ISTANZA_ALTRO_SOGGETTO`, `E_INDIRIZZO_SOGGETTO_NON_TROVATO`, `E_INDIRIZZO_COPIA_NESSUN_TIPO` hanno già policy).
  Le firme e i file, dopo il giro 1, sono in §7.3.
* **R-2 (FE)**: `IndirizziSoggettoDrawer` manda la chiave del drawer (`istanzaUtilityId`), legge il picker sulla
  destinazione, e la riga «Verso» della dialog dice la chiave del drawer (`copiaDestinazione`, oggi «come la
  sorgente»); in contesto ruolo «Copia come…» sulle righe del soggetto usa la rotta del gemello. Con D-4 (a),
  in contesto ruolo «Copia come…» e «Aggiungi» si spengono insieme dal picker, non più dal motivo di riga.
* ~~**R-3 (BE)**: policy e ripiego del codice nuovo~~ — ritirata il 2026-11-20: il codice nuovo non nasce (§4.1 A).

## 7. Giro 1 — scritto e provato il 2026-11-20 (team DB)

### 7.1 Che cosa c'è

| Oggetto | ChangeSet / file |
| --- | --- |
| BB `anagrafiche.fn_crea_copie_indirizzo_ruolo(ruolo, elemento jsonb, istanza, tipi text[]) → bigint[]`: una riga per tipo sulla chiave data, dalla singolare, tutto o niente. Due consumatori, i due verbi qui sotto (regola del 2) | `20261117-29` |
| `anagrafiche.fn_copia_indirizzo_ruolo(ruolo, indirizzo, tipi text[], istanza_destinazione)`: la sorgente in qualunque chiave del ruolo, la riga nuova sulla destinazione. DROP della firma a tre argomenti (D-3) | `20261117-30` |
| `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(ruolo, indirizzo_soggetto, tipi text[], istanza_destinazione)`, il gemello di D-2: la sorgente è una riga del soggetto del ruolo (`E_INDIRIZZO_SOGGETTO_NON_TROVATO`) | `20261117-31` |
| Ritiro di `anagrafiche.vw_indirizzi_ruolo_azioni` e `anagrafiche.fn_check_copia_indirizzo_ruolo` (D-4 a) | `20261117-32` |
| La riga `COPIA_INDIRIZZO_RUOLO` del registro spenta (`attivo = f`) | `80_data/sql/config/azioni_riga.csv` |
| Le note di `E_INDIRIZZO_RUOLO_NON_TROVATO` ed `E_INDIRIZZO_COPIA_NESSUN_TIPO` | `80_data/sql/config/codici_errore.csv` |
| pgTAP nuovo, 28 casi costruiti (§4.1 E) | `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` |
| La parte del ruolo esce dal test del soggetto (plan 26 → 16) | `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` |
| Il conteggio dei siti dell'helper del primo motivo: 63 → 62 (il verbo del ruolo non lo chiama più) | `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` |
| La guida, §R2: la copia va sulla chiave aperta | `docs/it/guide/gestione-degli-indirizzi.md` |

`%TYPE` in firma, `DECLARE`, `COMMENT` e `DROP`, anche nei rollback dei nuovi. Restano a tipo esplicito, con la
ragione accanto: gli array (`text[]`, `bigint[]`: `%TYPE[]` non esiste), l'elemento `jsonb` e il `record` della
sorgente. Le ancore risolvono a `bigint` (`indirizzi.id`, `indirizzi.istanza_utility_id`, `indirizzi_soggetti.id`,
`soggetti_ruoli.id`) e `uuid` (`soggetti_ruoli.soggetto_id`), letti dal catalogo.

### 7.2 Due scelte prese scrivendo, dentro D-4 (a)

* **Il verbo non solleva `E_INDIRIZZO_COPIA_NESSUN_TIPO`.** Senza la check di riga, il «nessun tipo» su una
  destinazione piena lo dice la singolare col motivo **del tipo chiesto** (`E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`,
  o il tipo non ammesso), come per «Aggiungi»: un motivo più preciso, e nessun predicato ricopiato. Il codice resta
  per la copia sul soggetto. Lo prova il caso 21.
* **La riga del registro si spegne, non si svuota**: `superficie`, colonne e `fn_check` sono `NOT NULL`, e il
  presidio del registro legge solo le righe attive. La riga resta nel CSV con `attivo = f`; il gemello non si
  iscrive, perché non ha un motivo di riga.

### 7.3 Ricadute sul BE/FE (R-1, R-2), con i file

| Chi | File | Che cosa |
| --- | --- | --- |
| BE | `backend/apps/anagrafiche/db/soggetti_repository.py` (la chiamata a `fn_copia_indirizzo_ruolo`, oggi a tre argomenti) | `SELECT anagrafiche.fn_copia_indirizzo_ruolo(%s::bigint, %s::bigint, %s::text[], %s::bigint)`, la destinazione dal body (assente = `NULL`, il ruolo) |
| BE | stesso repository e `api/views_indirizzi_ruolo.py` | la rotta del gemello: `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(ruolo, indirizzo_soggetto, tipi, istanza_destinazione)` per le righe del livello soggetto in contesto ruolo |
| BE | `backend/apps/anagrafiche/db/_helpers.py` (`JOIN_COPIA_RUOLO`, e `JOIN_COPIA_SOGGETTO` sul livello soggetto della lista del ruolo) | la lista del ruolo non unisce più le viste di azioni: `vw_indirizzi_ruolo_azioni` non esiste. In contesto soggetto `JOIN_COPIA_SOGGETTO` resta |
| BE | `error_policies_generated.py` | si rigenera col DB allineato (le note dei due codici sono cambiate; nessun codice nuovo) |
| BE | `docs/it/backend/anagrafiche/manual/api_indirizzi_ruolo.md`, `api_soggetti.md`; il catalogo BB backend se nomina la vista | il verbo con la destinazione, il gemello, `E_INDIRIZZO_COPIA_NESSUN_TIPO` non più del ruolo |
| FE | `frontend/src/anagrafiche/components/IndirizziSoggettoDrawer.vue` (`useAzioneRiga('COPIA_INDIRIZZO_RUOLO')`, `copiaDestinazione`) | l'azione del ruolo non arriva più dal registro: «Copia come…» in contesto ruolo si spegne dal picker della destinazione, insieme ad «Aggiungi»; manda `istanzaUtilityId` del drawer; la riga «Verso» dice la chiave del drawer |
| FE | il catalogo BB frontend, se nomina `COPIA_INDIRIZZO_RUOLO` | idem |

⚠️ Chi cambia per primo: il DB. Fra l'apply e R-1 la copia del ruolo risponde «funzione inesistente» e la lista
`GET ruoli/<id>/indirizzi/` fallisce sulla join della vista ritirata. Il progetto non è in produzione e le rotture
del BE sono accettate (D-3); R-1 va subito dopo l'apply.

### 7.4 Prova (2026-11-20, `scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, da owner, ROLLBACK)

* Estratto dei quattro changeSet eseguito per intero; catalogo identico prima e dopo.
* `test-copia-indirizzo-destinazione-v1`: senza l'estratto si ferma (le funzioni non esistono), con l'estratto **28/28**.
  Il caso 6 (la riga del registro spenta) passa solo con il CSV, che la prova non applica: provato aggiungendo un
  changeSet usa-e-getta con l'`UPDATE` della riga, fuori dal repo.
* `test-copia-indirizzo-v1`: 16/16 prima e dopo.
* `test-rubinetto-primo-motivo-v1`: 7/7 con l'estratto (senza, rosso il conteggio, come atteso: 63 contro 62).
* `test-azioni-riga-registro-v1`: 8/8 con l'estratto e la riga spenta; con la riga ancora attiva è rosso su 2-6,
  che è il motivo per cui il CSV va nello stesso apply.
* Non provati: i rollback (testo ricopiato dagli YAML del 2026-11-15, o un `DROP`), e l'esito come applicazione.
* Guardrail sui quattro file: `guardrail_forme_changeset`, `guardrail_comment_al_presente`, `guardrail_run_on_change`
  verdi.

## 8. Giro BE/FE — R-1 e R-2, fatte il 2026-11-20

### 8.1 Che cosa c'è

| Lato | File | Che cosa |
| --- | --- | --- |
| BE | `apps/anagrafiche/db/soggetti_repository.py` | `copia_indirizzo_ruolo` a quattro argomenti (la destinazione, `None` = il ruolo); `copia_indirizzo_soggetto_su_ruolo`, il gemello |
| BE | `apps/anagrafiche/services/soggetti_service.py` | i due verbi leggono `istanza_utility_id` dal corpo (assente o `null` = il ruolo; un non intero positivo è un 400 `E_ANAG_VALIDAZIONE` sul campo) |
| BE | `apps/anagrafiche/api/views_indirizzi_ruolo.py`, `api/urls.py` | `RuoloIndirizziCopiaView` con la destinazione; rotta nuova del gemello `POST ruoli/<id>/indirizzi-soggetto/<id>/copia/` (`RuoloIndirizziSoggettoCopiaView`); la lista del ruolo senza le viste di azioni sui tre livelli |
| BE | `apps/anagrafiche/db/_helpers.py` | `JOIN_COPIA_RUOLO` ritirato; `COLONNE_COPIA` e `JOIN_COPIA_SOGGETTO` restano per la lista in contesto soggetto |
| BE | `apps/core/services/error_policies_generated.py` | rigenerato: cambiano le sole note di `E_INDIRIZZO_COPIA_NESSUN_TIPO` ed `E_INDIRIZZO_RUOLO_NON_TROVATO` |
| FE | `src/anagrafiche/api/anagrafiche.js` | `copiaRuoloIndirizzo(ruolo, indirizzo, tipi, istanzaUtilityId)`; `copiaSoggettoIndirizzoSuRuolo`, il gemello |
| FE | `src/anagrafiche/components/IndirizziSoggettoDrawer.vue` | in contesto ruolo la copia va sulla chiave del drawer per ogni riga della cascata; i tipi dal picker di quella chiave; `useAzioneRiga('COPIA_INDIRIZZO_RUOLO')` tolto; la riga «Verso» dice la chiave del drawer |
| FE | `src/locales/it.json`, `en.json` | tolta `anagrafiche.indirizzi.copia.verso_come_origine` |
| Doc | `docs/it/backend/anagrafiche/manual/api_indirizzi_ruolo.md` (§5, §5-bis nuovo), `api_soggetti.md` (§8.3), i due cataloghi BB, l'indice BB backend rigenerato | il contratto delle due rotte e i building block cambiati |

### 8.2 Scelte prese scrivendo

* **La rotta del gemello** è `ruoli/<soggetto_ruolo_id>/indirizzi-soggetto/<indirizzo_soggetto_id>/copia/`: sotto il
  ruolo, perché la destinazione è una chiave del ruolo, e con un segmento suo perché l'id è di `indirizzi_soggetti`
  e non di `indirizzi`.
* **«Copia come…» spenta in contesto ruolo** quando il picker della chiave del drawer non ha un tipo ammesso, su
  ogni riga, con la frase che c'era già (`anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile`). «Aggiungi»
  in quel caso non compare, come prima.
* **La riga «Verso» sul servizio** porta il codice dell'utility quando la lista ha almeno una riga di quel servizio
  (è lì che il BE lo espone); altrimenti dice «il servizio» senza codice.
* **In contesto soggetto niente cambia**: verbo del soggetto, motivo di riga dal registro.

### 8.3 Prova (2026-11-20)

* `apps.anagrafiche.tests.db.test_copia_indirizzo_db` sul DB vero (`ZEROERP_TEST_DB_E2E=1`): **13/13**, nessuno
  saltato. Casi costruiti col builder `dbops.fn_pgtap_crea_cliente_ba`: senza destinazione la copia va sul ruolo;
  con l'istanza va sull'istanza; l'istanza di un altro soggetto è un 400 `E_ISTANZA_ALTRO_SOGGETTO`; la destinazione
  non intera è un 400 senza chiamare il DB; il gemello sul ruolo e sulla sua istanza; la riga di un altro soggetto è
  un 404 `E_INDIRIZZO_SOGGETTO_NON_TROVATO`; la lista del ruolo si legge e non porta `copia_blocco_reason`.
* Tutta l'app `apps.anagrafiche`: 735 test verdi; `mypy apps/anagrafiche` pulito.
* `IndirizziSoggettoDrawer.spec.js`: 9/9 (casi 5-9 nuovi o riscritti); i test di `src/anagrafiche` e di
  `src/vendite/_shared/indirizzi`: 70/70; `eslint src/anagrafiche` pulito; guard i18n e indice BB verdi.
* Non provato: il gesto a video, e gli smoke bash.

### 8.4 Che cosa resta

* Tid: la prova a video del caso del §1 (dal servizio, la Spedizione del ruolo copiata come Fatturazione: deve
  nascere sul servizio), poi il commit.

### 8.5 Revisione del giro (2026-11-20, `/verifica`)

Tre correzioni, sul codice non committato del §8.1.

* **La rotta del gemello usciva dallo schema OpenAPI senza corpo della richiesta.** I campi delle due copie stavano
  in un dizionario di modulo condiviso dai due `inline_serializer`: un campo DRF si lega al primo serializer che lo
  riceve, e il secondo componente (`IndirizzoSoggettoSuRuoloCopiaReq`) non nasceva. Gli endpoint rispondevano uguale
  e nessun test lo vedeva. Ora è una factory (`_campi_copia_su_ruolo`, come `campi_indirizzo_madre`). Presidio:
  `test_indirizzi_ruolo_api.TestSchemaCopiaSuRuolo`, rosso col dizionario condiviso (provato).
* **Le due rotte non erano provate dalla rotta al repository**: i test sul DB vero chiamano il service. Aggiunto
  `TestCopiaSuRuoloApi` (repository `autospec`): id del percorso, tipi e destinazione arrivano al verbo giusto;
  senza `istanza_utility_id` arriva `None`.
* **Il picker che non risponde spegneva «Copia come…» col motivo «nessun tipo»** su ogni riga del ruolo: la lettura
  fallita lasciava la matrice vuota, uguale a «nessun tipo ammesso». Ora l'azione si spegne solo se il picker ha
  risposto (`matriceCaricata`); altrimenti resta accesa, e il clic rilegge il picker con l'errore a video. Spec,
  caso 10, rosso col codice di prima (provato).

In più, senza test: la chiave `v-for` delle card porta la fonte, perché in contesto ruolo la cascata unisce righe di
`indirizzi` e di `indirizzi_soggetti`, con id che possono coincidere. La lista si rimonta a ogni ricarica, quindi la
chiave doppia non arrivava a un riallineamento: non c'è un caso che diventi rosso.

**Un intero oltre bigint nel corpo** (ok di Tid, 2026-11-20). `istanza_utility_id: 10^30` passava la validazione e
tornava dal DB come 22003: un 400 `E_DATABASE` tecnico, senza campo e loggato come errore. Il tetto sta ora nel BB
`PayloadValidator` (`require_positive_int` / `optional_positive_int`, `BIGINT_MAX`), per ogni endpoint che lo usa: è
un 400 di validazione sul campo. Nello stesso punto `isdigit` è diventato `isdecimal` (`"²"` passava `isdigit` e
`int` sollevava `ValueError`). Prova: `test_payload_helpers` 19b, 19c, 22b, rossi col codice di prima (provato); il
caso sta anche in `test_copia_indirizzo_db` 5d. Lo stesso tetto è in `guard_positive_int`, che giudica gli id già
interi (percorso, argomenti): oltre bigint è «identificatore non valido», prova 7b, rossa col codice di prima.

Doc: `api_indirizzi_ruolo.md` §5 dice anche l'istanza di destinazione inesistente (`E_DATABASE` 400, dalla chiave
esterna, come per «Aggiungi»: §4.1 A).

Prova: `apps.anagrafiche` con `ZEROERP_TEST_DB_E2E=1`, più `test_schema_openapi_registro` e
`test_copertura_doc_api`: 757 verdi; ruff sui file toccati e mypy a cricchetto puliti. `src/anagrafiche` e
`src/vendite/_shared/indirizzi`: 71/71; eslint, guard i18n, classi morte e indice BB verdi.
