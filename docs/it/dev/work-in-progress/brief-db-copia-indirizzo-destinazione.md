# Brief DB — La copia di un indirizzo va dove lavora l'operatore

## ⏭️ Chi riparte — aggiornato al 2026-11-20

**Riparte: Tid, con l'applicazione del giro 1 (§7).** Il giro 1 è scritto e provato in transazione annullata il
2026-11-20 (changeSet `20261117-29` … `-32`, due CSV, pgTAP verdi in prova). D-1 … D-4 decise, tutte come proposte.
La verifica DB del 2026-11-20 (§4.1) corregge il §4: l'istanza di destinazione la giudica il guard che c'è già
(niente codice nuovo, R-3 ritirata), e il motivo «nessun tipo» esce dalla riga e lo porta il picker della
destinazione (D-4). ⚠️ Dopo l'apply la copia del ruolo e la lista degli indirizzi del ruolo sono rotte nel BE
fino a R-1 (§7.3): la firma a tre argomenti e la vista di azioni non esistono più.

**Brief vicini verificati** (2026-11-20): nessuno aperto in `work-in-progress/`. Il precedente è archiviato,
[brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md): questo ne revoca §4.6 punto 3
(D-1 del 2026-11-15, «la copia resta nella chiave della sorgente») e ne cambia R-3/R-4 (le superfici della lista).

| # | Chi | Che cosa | Dove | Dopo |
| --- | --- | --- | --- | --- |
| 1 | Tid | D-1 … D-3 ✅ 2026-11-19 | §5 | — |
| 2 | Tid | D-4 ✅ 2026-11-20, strada (a) | §5 | — |
| 3 | team DB | giro 1: i due verbi con la destinazione (dal ruolo, dal soggetto), il motivo secondo D-4, il registro `config.azioni_riga`, ritiro della firma vecchia, pgTAP e doc ✅ 2026-11-20, scritto e provato | §7 | 2 |
| 4 | Tid | applicazione su dbdev, pgTAP verdi, doc auto-generata, commit | — | 3 |
| 5 | BE/FE | R-1, R-2 | §6 | 4 |
| 6 | chi chiude | archiviazione in `work-done/` | — | tutti |

Decisioni aperte di Tid: nessuna. Lavoro da committare: tutto il giro 1 (§7.1) e questo brief.

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
