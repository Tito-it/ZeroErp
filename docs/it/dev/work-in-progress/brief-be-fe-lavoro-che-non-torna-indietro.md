# Brief BE/FE — il lavoro che non torna indietro: la metà applicativa

> **Destinatario:** backend + frontend. È il seguito di
> [brief-db-lavoro-che-non-torna-indietro.md](../work-done/brief-db-lavoro-che-non-torna-indietro.md),
> che il team DB ha **chiuso il 2026-08-26** (16 changeSet, `20260826-23` …
> `20260826-38`, tutti applicati) lasciando **due consegne e un verbo** a questo
> lato.
>
> **Origine.** Il §14.11 di quel brief elenca ciò che resta, ed è tutto **fuori
> dal DB**: `BE-1` (la fatturazione è ferma), `BE-2` (le policy dei sette codici
> nuovi) e il pulsante «Riporta da emettere», che il database ha già **collaudato
> sulle 5 righe vere** e che a video non esiste.
>
> 📌 **Stato al 2026-08-26**: **BE-1, BE-2 e FE-1 fatti e verificati**, più una
> pulizia i18n che non era in programma (§5.1-bis/ter). Il resto è pianificato
> qui e **non iniziato**: si parte su «procedi», lotto per lotto.
>
> ⛔ **Un prerequisito DB è emerso scrivendo questo piano** e blocca il verbo a
> video: l'elenco su cui il pulsante dovrebbe agire **non esiste** — né la vista
> che lo produce, né la chiave che il verbo consuma. Richiesta nel **§6**.

---

## 1. Cosa ha lasciato il DB, in una tabella

| # | Cosa | Stato | Dove |
| --- | --- | --- | --- |
| **BE-1** | il ramo aggregato di `pipeline_repository` smette di scrivere `fatturato`; il metodo morto `mark_attivita_fatturata` si cancella | ✅ **fatto** (§2) | `apps/vendite/db/pipeline_repository.py` |
| **BE-2** | classe + messaggio di ripiego per i **7** codici nuovi; i **2** ritirati passano fra i ritirati | ✅ **fatto** (§3) | `apps/core/services/error_*` |
| **BE-3** | endpoint «Riporta da emettere» (check + mutazione), permesso `riporta_da_emettere` | ⏸️ **attende il §6** — decisione di Tid: il perimetro dell'endpoint nasce allineato alla lista, non prima (§4) | `apps/vendite/` |
| **BE-4** | la lista dei **residui**, che oggi non esiste a nessuna grana | ⛔ **bloccato dal §6** | `apps/vendite/` |
| **FE-1** | le chiavi i18n che il **database emette** e il frontend non risolve | ✅ **fatto** (§5.1) | `frontend/src/locales/` |
| **FE-1b** | *fuori programma*: una chiave i18n definita **due volte**, e il cancello che non poteva vederla | ✅ **fatto** (§5.1-bis, §5.1-ter) | `frontend/src/locales/` · `useLottoAzioni.js` · `scripts/check_i18n_keys.py` |
| **FE-2** | il verbo sulla card «Emesse non fatturate» | ⛔ **bloccato dal §6** | `DashboardCompetenzaView` |
| **DOC** | guida operativa: §3.1, §7.1 e il ritiro alla chiusura di un documento | ⏸️ pianificato (§7) | `docs/it/guide/cruscotti-fatturazione.md` |

---

## 2. BE-1 — la fatturazione era ferma, e non in modo silenzioso ✅

Dal changeSet `20260826-33` la colonna `vendite.attivita_fatturabili.fatturato`
è **generata**:

```text
attname     | attgenerated | attnotnull
fatturato   | s            | t
```

*(letto su `pg_attribute` del DB di sviluppo, 2026-08-26)*

Scrivere una colonna generata **non è un no-op: è un errore**. Il ramo aggregato
di `batch_insert_righe_and_mark` la nominava, quindi **ogni giro di fatturazione
sarebbe morto** al primo `UPDATE`.

**Prova, rossa prima e verde dopo** — l'errore è di riscrittura, quindi si vede
anche a zero righe e non serve toccare un dato:

```sql
BEGIN;
UPDATE vendite.attivita_fatturabili
   SET fattura_riga_id = NULL, fatturato = TRUE, stato_esecuzione = 'COMPLETED'
 WHERE false;
-- ERRORE: la colonna "fatturato" può essere modificata solo a DEFAULT
--         (è una colonna generata)
ROLLBACK;

BEGIN;
UPDATE vendite.attivita_fatturabili
   SET fattura_riga_id = NULL, stato_esecuzione = 'COMPLETED'
 WHERE false;
-- UPDATE 0
ROLLBACK;
```

**Cosa è cambiato:**

- il `SET` non nomina più `fatturato`, e sopra c'è scritto **perché** (il timbro
  si deriva da `fattura_riga_id`, che sta nello stesso `SET`: era un doppione, e
  finché i due dati erano autonomi potevano smettere di dire la stessa cosa —
  nel luglio 2026 lo hanno fatto);
- `mark_attivita_fatturata` **cancellato**, insieme al suo doppione nel finto
  repository di `test_fatture_righe_service` e all'asserzione `mark_calls == 0`
  che presidiava una chiamata che non avveniva.

⚠️ **Le letture non si toccano**: `a.fatturato IS FALSE` (righe ~1590 e ~2786)
continua a funzionare identico — una colonna generata si legge come qualunque
altra. Verificato con **due ricerche di forma diversa** (assegnazioni, e liste di
colonne di `INSERT`): scritture residue di `fatturato` in tutto `backend/`
= **zero**.

Suite: `4117` test verdi.

---

## 3. BE-2 — i sette codici nuovi ✅

⛔ `error_policies_generated.py` **non si scrive a mano**: la sorgente è il
catalogo, e il team DB ha già seminato i codici con la loro classe. Rigenerato
con `./manage-env.sh genera_error_policies`, il diff è **esattamente** quello
atteso e niente di collaterale:

| Codice | Classe | HTTP |
| --- | --- | --- |
| `E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA` | `TECNICO` | 500 |
| `E_ATTIVITA_FATTURABILE_NON_TROVATA` | `NON_TROVATO` | 404 |
| `E_ATTIVITA_ANCORA_IN_FATTURA` | `CONFLITTO_STATO` | 409 |
| `E_ATTIVITA_GIA_DA_EMETTERE` | `CONFLITTO_STATO` | 409 |
| `E_ATTIVITA_IN_LAVORAZIONE` | `CONFLITTO_STATO` | 409 |
| `E_RITIRO_SORGENTE_PARAMETRO_MANCANTE` | `TECNICO` | 500 |
| `E_SORGENTE_CON_RIGHE_EMESSE` | `CONFLITTO_STATO` | 409 |

più `E_ORD_ANNULLA_IN_COMMESSA` e `E_PREV_GIA_IN_COMMESSA` passati fra i
**ritirati** (Q-9). ⚠️ Restano e continuano a risolvere: `dbops.error_log`
contiene le loro righe e devono restare leggibili.

⭐ **E la policy non basta: serve il ripiego.** Tutti e sette i messaggi a
catalogo contengono un `%s` — il che non è un'esenzione, **è la ragione per cui
il ripiego esiste**: è proprio quando gli argomenti non arrivano che il
segnaposto finirebbe a video in chiaro. Scritte sette frasi argument-free in
`error_messages_fallback.py`, e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`
è verde.

⚠️ **Nessun `ui_action` override.** Il default della classe è giusto in tutti e
sette i casi: su un `CONFLITTO_STATO` non c'è un campo del form da accendere — il
conflitto è nella situazione, non in un valore che l'operatore ha scritto.

### 3.0-bis ⛔ Due test rossi che NON sono di questo cantiere — e non si «sistemano» rigenerando

Rilanciando la suite a fine giornata, due test cadono:

| Test | Cosa dice |
| --- | --- |
| `test_il_file_generato_e_allineato_al_catalogo` | `error_policies_generated.py` diverge dal catalogo: **793 voci nel file, 798 nel database** |
| `test_nessun_codice_nuovo_senza_policy` | 4 codici che il DB può nominare non hanno una classe |

⛔ **La mossa che sembra ovvia — rigenerare — è quella sbagliata.** Misurato il
2026-08-26 confrontando `config.vw_codici_errore_identita` con il CSV **di git**:

```text
codici nel DB: 798   |   nel CSV committato: 793
nel DB ma NON in git:  E_BA_EMITTENTE_CON_STORIA
                       E_COMMESSA_EMITTENTE_BA_INCOERENTE
                       E_COMMESSA_SORGENTE_EMITTENTE_MISTO
                       E_SORG_BA_NON_RISOLTO
                       E_SORG_EMITTENTE_NON_RISOLTO
in git ma NON nel DB:  nessuno
```

⚠️ E quei cinque **non stanno su nessun ramo** — verificato su `origin/dev/db-tid`,
`origin/Tito-dev` e `origin/main`: zero occorrenze. Esistono **solo nel database
di sviluppo condiviso**, applicati da un cantiere in corso
(`brief-db-billing-account-cambio-emittente` / `brief-db-emittente-commessa-invariante`)
il cui seed non è ancora committato.

⇒ **Il DB è AVANTI rispetto a git**, ed è la condizione in cui
[[feedback_ripiego_ogni_codice_vivo]] vieta di rigenerare: il file assorbirebbe
codici che nessun ramo contiene, descrivendo uno stato che git **non sa
ricostruire** — e in CI, dove il database nasce da git, la divergenza si
ripresenterebbe al contrario.

⭐ **I due rossi sono quindi un segnale corretto, non un guasto**: il presidio sta
dicendo che due sorgenti si sono separate. Tornano verdi da soli quando il team
DB committa il proprio seed. ✅ **La rigenerazione di BE-2 resta valida e pulita**:
verificato che `error_policies_generated.py` **non contiene** nessuno dei cinque,
e che i sette codici di questo cantiere sono nel CSV **committato**.

### 3.1 🟡 Un residuo che è del DB, non mio

`E_PREV_ANNULLA_COMMESSA_EMESSA` **resta** (Q-9), e il §9.7.4 del brief DB dice
che *«il suo testo guadagna il rimedio»*. Letto a catalogo il 2026-08-26, la sua
`soluzione` dice ancora:

> *«l'operazione va ripresa dal lato fatturazione, con una nota di credito o uno
> storno delle attività già emesse»*

cioè **la strada di prima**, non «Riporta da emettere». Non è un difetto mio e
non lo correggo dal backend: il ripiego che ho scritto non promette una via
d'uscita che il catalogo non nomina. ➡️ **Va nel §6 come richiesta al team DB.**

---

## 4. BE-3 — l'endpoint «Riporta da emettere»

Il database espone già le due metà, e sono da consumare **così come sono**:

| Oggetto DB | Cosa dà |
| --- | --- |
| `script.fn_check_attivita_riportabile_da_emettere(bigint[]) → jsonb` | i motivi ostativi, **tutti**, con `codice`/`reason_key`/`dettaglio` e gli id per il bersaglio. Pura |
| `vendite.fn_riporta_attivita_da_emettere(bigint[]) → (riportate, riemesse_attivita)` | la mutazione. Solleva il **primo** motivo |

**Forma proposta** — due endpoint, come il progetto fa già per i verbi con
capability:

```text
POST /api/v1/vendite/attivita-fatturabili/riporta-da-emettere/
     body { attivita_fatturabili_ids: [int] }
     → { riportate, riemesse_attivita }

GET  /api/v1/vendite/attivita-fatturabili/riportabili/?ids=1,2,3
     → { motivi: [...] }        # per spiegare senza far fallire
```

| Scelta | Perché |
| --- | --- |
| `post_permission = "riporta_da_emettere"` | è la riga **33** di `config.azioni_processo`, già seminata (Q-3). ⛔ Non si riusa `reset_lotto_fattura_draft`: legherebbe un verbo di recupero a chi può **cancellare** documenti |
| `require_idempotency_key=True` | modifica stato, come ogni verbo di comando |
| **una sola** `SELECT fn_…` nel repository | l'atomicità è per costruzione: la madre DB fa le due scritture e il log in una transazione. ⛔ Niente `transaction.atomic()` con due chiamate — sarebbe una seconda implementazione dell'atomicità che il DB già garantisce |
| ⛔ **niente coda** | «Riporta da emettere» è **sincrono**: due scritture, nessun job. Accodarlo per simmetria con «Rendi definitive» importerebbe il problema della dedup, che qui non esiste (§11.2 del brief DB) |
| traduzione errori via `translate_db_errors` | così `hint`, `fields` e **`targets`** arrivano all'envelope: la madre DB compone già il bersaglio (COMMESSA, poi FATTURA) |

⚠️ **Il `GET` non è un lusso.** Il codice `E_ATTIVITA_GIA_DA_EMETTERE` porta
scritto a catalogo che *«il frontend deve gate-are l'azione sui codici che ha già
in riga invece di proporla sempre: incontrare questo errore vuol dire che
l'elenco mostrato era invecchiato»*. Il `GET` è come il frontend ri-guarda prima
di agire su una selezione che ha in mano da un po'.

---

## 5. FE — dove va il verbo, e cosa manca perché ci stia

### 5.1 Le chiavi i18n che il database emette e nessuno risolveva ✅

Il patto dei tre livelli: **il DB emette l'indirizzo, il BE lo trasporta, il FE
lo risolve** — e se l'indirizzo non esiste il frontend **non segnala un errore,
mostra testo mancante**. È un difetto silenzioso, ed è già costato due volte.

Le chiavi emesse dai changeSet del 2026-08-26 e **assenti** da `it.json`/`en.json`
(verificato il 2026-08-26 — la radice `vendite.attivita` non esiste affatto):

| Chiave emessa dal DB | Da |
| --- | --- |
| `vendite.attivita.azione_reason.non_trovata` | `fn_check_attivita_riportabile_da_emettere` |
| `vendite.attivita.azione_reason.ancora_in_fattura` | idem |
| `vendite.attivita.azione_reason.gia_da_emettere` | idem |
| `vendite.attivita.azione_reason.in_lavorazione` | idem |
| `vendite.sorgenti.azione_reason.righe_commessa_emesse` | `fn_check_sorgente_chiudibile` |

⭐ Le radici sono **giuste**: `vendite.` è la cartella d'area del codice, e la
foglia non ripete l'area. ✅ **Scritte, in entrambi i file**, e
`python3 scripts/check_i18n_keys.py` è tornato verde — era **rosso su tutte e
cinque**, cioè il cancello stava facendo il suo mestiere.

⚠️ **Inserimento testuale, non round-trip JSON**, e la ragione vale oltre questo
caso: rileggere e riscrivere il file con `json.dump` **normalizza**, e
normalizzando cancella. Qui avrebbe cancellato una riga altrui — vedi §5.1-bis.

### 5.1-bis ✅ Una chiave scritta due volte — trovata per caso, e chiusa

`vendite.lotti.numera_esito` era **definita due volte nello stesso oggetto** di
`it.json` e `en.json`:

```json
"numera_esito": "Numerati {numerati} lotti.",              ← riga 2501
"numera_esito": "Fatture numerate: lotto reso definitivo", ← riga 2550
```

In JSON è **lecito**, e ogni parser tiene l'**ultima** — `JSON.parse` come
`json.load`. Quindi la prima era morta. E i consumatori erano **due, con
contratti diversi**:

| Chi | Perimetro | Cosa si aspettava |
| --- | --- | --- |
| `LottiListView.vue:414` | la numerazione **di massa**, con selezione di lotti | `t('…', { numerati })` — la frase col **conteggio** |
| `useLottoAzioni.js:143` | il verbo sul **singolo** lotto | la frase senza conteggio |

⇒ **A video la numerazione di massa diceva «lotto reso definitivo» e perdeva il
numero.** Nessun errore, nessun test rosso: il segnaposto semplicemente non
compariva, e la frase restava plausibile.

**Come è stata chiusa** — non cancellando una riga, ma dando un nome a ciascuno:

| Chiave | Chi la usa | Frase |
| --- | --- | --- |
| `numera_esito` | la massa | *«Numerati {numerati} lotti.»* |
| `numera_lotto_esito` **(nuova)** | il singolo lotto | *«Fatture numerate: lotto reso definitivo»* |

⭐ **Perché `numera_esito` resta alla massa e non al singolo**, che è la domanda
che decide: ha un **fratello**, `numera_esito_parziale`
(`{numerati}/{lotti}/{saltati}/{falliti}`), ed è la coppia «esito pieno / esito
parziale» dello stesso giro asincrono. Spezzare quella coppia per tenere insieme
`numera_header`/`numera_conferma`/`numera_esito` sarebbe costato di più — e
quella terna è **già** spezzata altrove nello stesso file (`rilancia_step` usa
`rerun_header` con `avanza_esito`), quindi non è una regola, è un'abitudine.

### 5.1-ter ⛔ Il cancello era cieco al proprio difetto — ed è la parte che vale

`scripts/check_i18n_keys.py` **non poteva vederlo**: faceva `json.load`, cioè
leggeva il dizionario **già collassato**. Guardava il *risultato* del difetto
invece del difetto. Una ricerca testuale del nome non basta neanche lei: due
definizioni possono stare a cinquanta righe di distanza ed essere entrambe
legittime se gli oggetti che le contengono sono diversi — a decidere è
l'annidamento, che solo il parser conosce.

✅ **Aggiunto il controllo 5** (`object_pairs_hook`, che vede le coppie prima che
si schiaccino), e **provato rosso prima e verde dopo** rimettendo il duplicato
esatto: un presidio che non si è mai visto fallire non è un presidio, è una
speranza.

✅ **E il guard adesso ha chi lo lancia** (decisione di Tid, 2026-08-26).
Misurato prima di agganciarlo: `check_i18n_keys.py` **non girava né in CI né in
pre-commit** — in `.github/workflows/` non compare, e in
`.pre-commit-config.yaml` c'era il solo `check_license.py`. *Un presidio che
nessuno lancia è a un passo dall'essere spento.*

Aggiunto l'hook `check-i18n-keys`, con due scelte che non sono stile:

| Scelta | Perché |
| --- | --- |
| `pass_filenames: false` | il guard è **globale**: confronta l'intero frontend con i due locales, la doc auto-gen e i seed. Un elenco di file lo restringerebbe proprio dove serve intero — ⭐ *una chiave si rompe cambiando il **locale**, non il componente che la cita*. E i nomi finirebbero comunque in `sys.argv`, che il guard legge per `--strict-roots` |
| `files` = le **quattro** sorgenti che il guard legge davvero (`SRC`, `LOCALES`, `DBDOCS`, `SEED`) più sé stesso | derivate dal suo header, non indovinate. Se una si sposta va spostata anche qui, o il guard **smette di svegliarsi** |

⛔ **E la regex sta su una riga sola, dopo un errore che stavo per lasciare
passare**: scritta come scalare `>-` di YAML, ogni a capo diventa uno **spazio
dentro il pattern** — le alternative nascono con uno spazio davanti e non
matchano più niente. Il guard non si sarebbe mai svegliato, e sarebbe stato
**verde per sottrazione**: il modo peggiore di sbagliare proprio questo file.

**Provato end-to-end**, simulando ciò che pre-commit fa (filtra lo staged con
`files` → se resta qualcosa lancia `entry` senza nomi):

| Commit simulato | Esito |
| --- | --- |
| tocca solo `backend/…/pipeline_repository.py` | hook **saltato** |
| tocca `it.json`, col duplicato rimesso | hook attivato → **exit 1, commit bloccato** |
| tocca `it.json`, duplicato rimosso | hook attivato → **exit 0** |

⚠️ **Su questa macchina non è ancora attivo**, e non è un difetto della
configurazione: `pre-commit` è dichiarato in `requirements.txt`
(`pre_commit==4.6.2`) ma non è installato qui, e `.git/hooks/pre-commit` non
esiste. Si accende con `pre-commit install` sulla macchina dove si committa —
⛔ e finché non lo si fa, l'hook è scritto e **non gira**.

### 5.2 Il verbo sta dove sta l'elenco del suo oggetto

È il principio del §11.4 del brief DB, e qui morde: «Riporta da emettere» agisce
su **attività residue**, e la card `Emesse non fatturate` dovrebbe essere l'unico
posto dove quell'elenco vive.

⛔ **Solo che quell'elenco non c'è.** Misurato leggendo il codice, non i dati:

| Card | Dove scende il drill-down oggi |
| --- | --- |
| `DA_EMETTERE` | sui **gruppi fatturabili** (lista propria, `vw_dash_competenza_gruppi`) |
| `DA_APPROVARE`, `EMESSA_NON_FATTURATA`, `FATTURATA` | sulle **commesse aggregate** — una riga per commessa |

Sotto «Emesse non fatturate» c'è quindi una lista di **commesse**, non di
attività: l'oggetto del verbo non è visibile, e la sua chiave nemmeno.

⭐ **La forma giusta è quella che il cruscotto ha già**, ed è la simmetria con
`DA_EMETTERE`: cliccando la card, il drill-down scende sui **residui** con
selezione multipla, e il verbo di massa sta sulla lista — esattamente come
«Fattura adesso» sta sui gruppi. Il pattern esiste (`useSelezioneToggle` dentro
`<ListaConfigurabile>`, slot `selection`/`selection-header`) e non va inventato.

⛔ **Scartata** la variante «verbo di riga sulla lista commesse, che riporta
tutti i residui della commessa»: l'operatore non vedrebbe **cosa** sta
riportando. Il progetto ha già scelto il contrario per l'approvazione di massa,
che è dichiaratamente *WYSIWYG con la card*.

### 5.3 ⛔ E la card conta DUE popolazioni — questo è un difetto del modello a video

`vw_dash_competenza_attivita` assegna lo stadio così:

```sql
WHEN af.fattura_riga_id IS NULL THEN 'EMESSA_NON_FATTURATA'
```

Il ramo guarda **solo** il legame con la riga di fattura. Ci finiscono quindi due
popolazioni strutturalmente diverse:

| Caso | Cos'è | Il verbo la tocca? |
| --- | --- | --- |
| emessa, non ancora presa da un lotto (`lock_in_fatturazione` falso, oppure `stato_esecuzione` `PENDING`/`RUNNING`) | **transito legittimo** | ⛔ no — e il DB la rifiuta con `E_ATTIVITA_GIA_DA_EMETTERE` / `E_ATTIVITA_IN_LAVORAZIONE` |
| lucchettata e `COMPLETED`, senza riga di fattura | **il residuo** | ✅ sì |

⚠️ **Fatto datato, 2026-08-26, contesto operatore impostato** (`app.ruolo_applicativo`
+ `app.current_user_id`, senza i quali la vista è fail-closed e risponde **zero**
— che sembra un dato): oggi nella card ci sono **5 righe su 5 residue**, nessuna
in transito.

⛔ **E la misura non decide niente**: il modello **ammette** la popolazione in
transito — si legge dal `CASE` della vista, che è struttura e non contenuto — e
un elenco costruito sui dati di oggi si romperebbe il primo giorno in cui il caso
capita. Zero occorrenze non significa che il caso non esiste.

**Conseguenza, ed è la decisione che chiedo a Tid:** la lista dei residui e il
numero della card devono raccontare la stessa cosa. Due strade:

| | Cosa vuol dire | Costo |
| --- | --- | --- |
| ⭐ **A — la card si spezza** | «Emesse non fatturate» diventa due numeri: *in transito* e *residue*. Il verbo vive sul secondo, e il primo smette di essere un allarme | una colonna in più nella vista aggregata; è la lettura onesta, e toglie di mezzo la frase della guida §3.1 che oggi dice il falso |
| **B — una lista sola, col motivo per riga** | la lista mostra entrambe e la selezione è possibile solo sulle residue, col motivo scritto accanto alle altre | meno DB; ma la card continua a contare due cose insieme, e il numero grande resta ambiguo |

✅ **DECISA da Tid il 2026-08-26: strada A**, la card si spezza in due.
La ragione è sul modello: sono situazioni con **rimedi opposti** — su una non si
fa niente e si aspetta, sull'altra si agisce. Un numero solo per due rimedi
opposti è la stessa forma di ambiguità che questo cantiere ha appena chiuso un
livello più in giù.

⭐ **E le popolazioni sono TRE, non due** — lo si vede scrivendo la richiesta DB:
«in attesa del suo lotto» e «dentro un giro vivo» sono entrambe transito, ma con
attese diverse, e sono esattamente i due rifiuti che il database sa già nominare
(`E_ATTIVITA_GIA_DA_EMETTERE`, `E_ATTIVITA_IN_LAVORAZIONE`). La dimensione
chiesta al DB ha quindi **tre** valori, non un booleano.

---

## 6. ⛔ Il prerequisito DB — passato al team, brief a parte

> ✅ **Scritto il 2026-08-26**:
> [brief-db-residui-competenza-dimensione-e-chiave.md](brief-db-residui-competenza-dimensione-e-chiave.md).
> Finché non arriva, **BE-3, BE-4 e FE-2 non partono**
> ([[feedback_be_fe_attende_prerequisiti_db]]).

⭐ **La richiesta si è ridotta scrivendola**, e vale la pena dire come: la prima
stesura chiedeva una **vista nuova** dei residui. Guardando come sono fatte le
tre liste sorelle della stessa Lente — `dash_competenza_errori`, `_gruppi`,
`_commesse` — è venuto fuori che hanno tutte `vista_sql = NULL`: **la query la
compone il backend**, la vista non esiste. Quindi non serviva un oggetto nuovo,
servivano **quattro colonne in coda a una vista che c'è già**.

| # | Richiesta | Cosa sblocca |
| --- | --- | --- |
| **D-1** | quattro colonne su `vw_dash_competenza_attivita`: `attivita_fatturabile_id`, `lock_in_fatturazione`, `stato_esecuzione` e la dimensione `motivo_non_fatturata` (`IN_ATTESA_LOTTO` / `GIRO_IN_CORSO` / `RESIDUO`) | la **chiave del verbo** e il discriminante delle tre popolazioni |
| **D-2** | `motivo_non_fatturata` entra nel `GROUP BY` di `vw_dash_competenza_mensile` | la card in due numeri (**strada A**, §5.3) |
| **D-3** | un pgTAP che lega la dimensione della vista ai codici della `fn_check_*` | impedisce che le due superfici divergano **in silenzio** |
| **D-4** | seed `ui.lista_definizione` id **44** + `ui.lista_colonna` per `vendite.dash_competenza_residui` | la lista si può rendere, esportare, personalizzare |
| **D-5** · **D-6** | i due messaggi a catalogo che mandano dalla parte sbagliata (§3.1, e il guard 4 di `fn_annulla_commessa_attivita`) | non bloccano |

⚠️ **D-2 porta un lavoro BE/FE nello stesso giro**, ed è dichiarato: aggiungere
una dimensione **cambia la cardinalità** dell'aggregata. I totali reggono perché
il pivot accumula, ma il breakdown elenca una voce per riga — senza adeguamento
il frontend mostrerebbe `EMESSA_NON_FATTURATA` **due volte**. È lo stesso effetto
collaterale già pagato il 2026-08-20 con `tipo_movimento`.

---

## 7. Documentazione, e la contesa dichiarata

| File | Cosa | Quando |
| --- | --- | --- |
| `docs/it/guide/cruscotti-fatturazione.md` §7.6 | l'avvertenza 🔴 su «Elimina dal lotto» **si toglie**: da L1 il difetto non c'è più | ⏸️ si può fare **adesso** |
| stessa guida §3.1 | la card prende un verbo; ⚠️ e va corretta la frase *«se in quella casella c'è un numero, qualcosa si è rotto»* — è vera per il **verbo di massa**, non per la casella | con FE-2 |
| stessa guida §7.1 | il verbo nuovo entra in tabella col suo permesso | con FE-2 |
| stessa guida | ⭐ **chiudere un documento adesso ritira lavoro**: è un comportamento che l'operatore deve sapere **prima**, non scoprire dopo | ⏸️ si può fare adesso |

⚠️ **La §7.1 è contesa con `brief-be-fe-rendi-definitive-sui-lotti.md`** (§11.3
del brief DB): la tabella dei verbi la riscrivono **due mani**, e se le due
modifiche viaggiano insieme una delle due si perde. Da coordinare, non da fare in
parallelo.

---

## 8. Trappole, per chi esegue

1. ⛔ **Un conteggio su queste tabelle senza contesto operatore torna zero e
   sembra un dato.** `commesse_attivita` ha RLS che si accende con
   `app.ruolo_applicativo = 'OPERATORE'`, e `vw_dash_competenza_attivita` è
   `security_invoker` **e** fail-closed su `app.current_user_id`: sono **due**
   meccanismi diversi, entrambi capaci di far sembrare pulito un database
   sporco. Le misure di questo brief sono prese con **entrambe** le GUC.
2. ⚠️ **`vendite.attivita_fatturabili` non ha RLS**, `commesse_attivita` sì. Una
   lettura che parte dalla prima è **fail-open sullo scope**, e il danno non è un
   permesso concesso a vuoto: è che la mutazione libererebbe l'attività e **non**
   riporterebbe la riga di commessa: lo stato spezzato che la primitiva
   condivisa di L1 esiste per impedire.
3. ⚠️ **`fatturato` si legge, non si scrive** — e la differenza non è visibile
   guardando il nome della colonna. Ogni scrittura nuova è un 428C9 in faccia
   alla prima fatturazione.
4. ⚠️ **Il verbo non si accoda.** È sincrono per progetto; la coda porterebbe la
   dedup, che qui non serve.
5. ⚠️ **Le 5 righe residue sono il banco di prova e non si toccano a mano.** Il
   DB le ha già attraversate in `BEGIN … ROLLBACK` (riportate 5, riemesse 5,
   casella a zero) e le ha **rimesse a posto**: il recupero vero è il primo
   gesto del frontend, ed è lì che si vede se il perimetro è giusto. Se il verbo
   non le prende, non ha fallito la bonifica: **ha fallito il perimetro**.
6. ⚠️ **L'albero git è condiviso** con altri cantieri: commit chirurgici, mai
   `git add -A`.

---

*Ultimo aggiornamento: 2026-08-26 — Tid / Claude*

---

## 9. Ereditato dal brief DB, che è stato archiviato

Il brief del team DB — [brief-db-lavoro-che-non-torna-indietro.md](../work-done/brief-db-lavoro-che-non-torna-indietro.md)
— è **chiuso e spostato in `work-done/`** il 2026-08-26: lato database tutto
consegnato e applicato (16 changeSet). ⚠️ Prima di archiviarlo i suoi punti
sospesi sono stati censiti **uno per uno**; questi tre non avevano ancora una
casa, e senza questa sezione sarebbero spariti con lui.

| # | Cosa | Stato |
| --- | --- | --- |
| **E-1** | la **guida operativa**: chiudere un documento adesso **ritira lavoro**, ed è un comportamento che l'operatore deve sapere *prima*, non scoprire dopo | ⏸️ si può fare adesso — è il §7 di questo brief |
| **E-2** | il messaggio di `E_RIGA_COMMESSA_NON_MANUALE` (guard 4 di `fn_annulla_commessa_attivita`) promette *«il rimedio è SEMPRE a monte, sul documento»*: da L7b quella frase **è vera**, e può nominare il documento invece di lasciarlo cercare | ⏸️ passato al team DB come **D-6** |
| **E-3** | 🟠 `codici-errore-baseline.sh` segnala un **rientrato**: `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` | ⏸️ **vivo, verificato il 2026-08-26** |

### 9.1 ⚠️ Su E-3, e non è una formalità

Rilanciato il presidio col contesto DB giusto, il 2026-08-26:

```text
🔵 RIENTRATO  E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO
              — non piu' misurabile o senza famiglie note (era: NOT_FOUND)
Codici presidiati: 76 · accumuli nuovi: 0 · ristretti: 0 · rientrati: 1
```

⛔ **Ed è lo script stesso a dire che non si può rimandare all'infinito**:

> *«Non è facoltativo: finché la baseline non è stretta, quelle famiglie restano
> AMMESSE e il presidio non le vedrebbe tornare.»*

Cioè il cancello è **mezzo spento** — un codice di quella famiglia potrebbe
riallargare il proprio significato senza che nessuno se ne accorga. ⚠️ **Non è di
questo cantiere** e stringerla qui nasconderebbe la storia di un altro lavoro
dentro questo (è la ragione per cui il team DB non l'ha toccata): va allineata da
chi possiede quel codice, con `scripts/codici-errore-baseline.sh --update`.

⭐ Sta scritto qui e non altrove per una ragione sola: era l'unico dei tre punti
**senza una casa**, e un debito che nessun documento nomina smette di esistere il
giorno in cui il documento che lo nominava viene archiviato.
