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
> ✅ **2026-08-27 — il prerequisito DB è ARRIVATO** (merge `#1407` su `Tito-dev`,
> migrate di Tid alle 08:20). Le quattro colonne, la dimensione, il pgTAP che
> lega vista e `fn_check_*`, la lista `49` e i due messaggi: **tutto consegnato
> e vivo**, verificato sugli oggetti del database e non solo sui commit.
> ⇒ **BE-4 e FE-2 sono sbloccati.** Dettaglio nel **§6**.
>
> 🔎 **2026-08-27 — passata di REVISIONE CRITICA su tutto il cantiere**: **13
> correzioni** applicate (tre sarebbero arrivate a video, una era una mia
> «de-duplicazione» che riscriveva un BB esistente) più le **2 decisioni** poi
> prese con Tid — una ha corretto **tre** liste paginate, oltre alla mia. Suite
> **4136 verde**, catena riprovata sul DB vero. Dettaglio nel **§13**.
>
> ⛔ **Dal punto di vista dello sviluppo il cantiere è chiuso.** Resta il
> **collaudo in-app di Tid** — e le 5 righe vere sono ancora lì apposta: il
> recupero è il primo gesto, ed è lì che si vede se il perimetro è giusto.
>
> 📂 **2026-08-27 — questo è l'UNICO brief aperto del cantiere.** Gli altri due
> sono archiviati in `work-done`, entrambi consegnati per intero:
>
> | Brief | Cosa conteneva | Dove |
> | --- | --- | --- |
> | `brief-db-lavoro-che-non-torna-indietro.md` | la causa: «Elimina dal lotto» non liberava niente. 16 changeSet | [work-done](../work-done/brief-db-lavoro-che-non-torna-indietro.md) — chiuso 2026-08-26 |
> | `brief-db-residui-competenza-dimensione-e-chiave.md` | il prerequisito: la chiave del verbo, la dimensione, la lista 49 | [work-done](../work-done/brief-db-residui-competenza-dimensione-e-chiave.md) — chiuso 2026-08-27 |
>
> ⚠️ **Due punti dei brief archiviati sono vivi e stanno QUI**, per non
> perderli chiudendo il loro file: il codice errore «rientrato» (**§9, E-3**), le
> due convenzioni di `ordinamento_default` (**§11.6**). I due rilievi sulle
> offerte ereditati da `revisione-attiva-due-domande` sono stati **chiusi dal
> team DB** il 2026-08-28: averli tenuti scritti qui è il motivo per cui
> qualcuno se n'è occupato, invece di perderli con l'archiviazione. Nessuno dei due è nostro —
> sono di chi possiede quei perimetri — ma da qualche parte devono restare
> scritti, e un brief archiviato non è quella parte.
>
> ### 📋 Cosa resta aperto — al 2026-08-27
>
> | | Cosa | Di chi |
> | --- | --- | --- |
> | 🔴 | **Il collaudo in-app** — il copione è scritto: [collaudo-in-app-riporta-da-emettere.md](collaudo-in-app-riporta-da-emettere.md), **11 prove**. Le 5 righe vere (`1123`, `1130`–`1133`, luglio 2026, 5.019 €) sono ancora dove erano: il recupero è il primo gesto. ⛔ Se il verbo non le prende non ha fallito la bonifica, **ha fallito il perimetro** | **Tid** |
> | ⏸️ | **E-3** — il codice «rientrato» in `codici-errore-baseline.sh` (**§9**). ⚠️ Finché la baseline non si stringe, quella famiglia resta *dichiarata ammessa* e il presidio non la vedrebbe tornare: è un cancello mezzo spento | chi possiede quel codice |
> | ⏸️ | **§11.6** — due convenzioni per `ordinamento_default` in `ui`. Per noi indifferente: `competenza_mese` risolve con entrambe | chi possiede lo schema `ui` |
> | ✅ | **C-2 — la guida non dice più il falso su «Rendi definitive»**: ereditata il 2026-08-28 dal cantiere gemello [brief-be-fe-rendi-definitive-sui-lotti.md](../work-done/brief-be-fe-rendi-definitive-sui-lotti.md) e **fatta lo stesso giorno** (§12.3). ⛔ Due annotazioni della consegna erano sbagliate e sono corrette lì | **fatta** |
> | ✅ | **Le due voci sulle offerte sono CHIUSE dal team DB il 2026-08-28**: il `SELECT INTO` risolve ora da `config.stati_doc_offerte.is_superato` con guard **sull'arità** (due stati marcati sono lo stesso difetto di zero: senza `STRICT` ne sceglierebbe uno a caso, in silenzio), e il limite del modello non c'è più — annullata l'ultima revisione viva, il padre **rientra** da `SUPERATA` a `EMESSA`. Ricadute per noi nel **§15** | fatto |
> | ⏸️ | **In attesa del merge**: il ripiego per `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` (**§15.2**). ⛔ Non si può scrivere prima: il presidio lega ripiego e policy **nei due versi**, e la policy si rigenera dal database — che qui è **avanti rispetto a git** | noi, appena arriva |
> | 🔵 | La prova del seleziona-tutto **non gira in CI**: nel frontend non c'è un runner (**§13.6**). Non è un debito di questo cantiere, è del frontend | — |
>
> ⛔ **Tutto il resto in questo file è CHIUSO.** I §§ che leggono come richieste
> al futuro («va fatto», «si può fare adesso») sono **piani eseguiti**: restano
> perché dicono *perché* una cosa andava fatta, non perché manchi.

---

## 1. Cosa ha lasciato il DB, in una tabella

| # | Cosa | Stato | Dove |
| --- | --- | --- | --- |
| **BE-1** | il ramo aggregato di `pipeline_repository` smette di scrivere `fatturato`; il metodo morto `mark_attivita_fatturata` si cancella | ✅ **fatto** (§2) | `apps/vendite/db/pipeline_repository.py` |
| **BE-2** | classe + messaggio di ripiego per i **7** codici nuovi; i **2** ritirati passano fra i ritirati | ✅ **fatto** (§3) | `apps/core/services/error_*` |
| **BE-3** | endpoint «Riporta da emettere» (check + mutazione), permesso `riporta_da_emettere` | ✅ **fatto** (§10) — provato sul DB vero, bersaglio incluso | `apps/vendite/` |
| **BE-4** | la lista dei **residui** | ✅ **fatto** (§10) — 5 righe vere, chiave del verbo proiettata | `apps/vendite/` |
| **FE-1** | le chiavi i18n che il **database emette** e il frontend non risolve | ✅ **fatto** (§5.1) | `frontend/src/locales/` |
| **FE-1b** | *fuori programma*: una chiave i18n definita **due volte**, e il cancello che non poteva vederla | ✅ **fatto** (§5.1-bis, §5.1-ter) | `frontend/src/locales/` · `useLottoAzioni.js` · `scripts/check_i18n_keys.py` |
| **FE-1c** | le **4 intestazioni** della lista residui, che il DB ha seminato il 2026-08-27 | ✅ **fatto** (§6.2) — il cancello CI era rosso | `frontend/src/locales/` |
| **FE-2** | il verbo sulla card «Emesse non fatturate» | ✅ **fatto** (§11) — tutti i presidi verdi (§12) | `DashboardCompetenzaView` |
| **DOC** | guida operativa + doc API | ✅ **fatta** (§12) | `guide/cruscotti-fatturazione.md` · `backend/vendite/manual/` · `dev/api.md` |
| **REV** | revisione critica del codice: bug, fragilità, duplicati, valori a mano | ✅ **fatta** (§13) — 13 corrette, 2 segnalate | tutto il cantiere + i due cataloghi BB |
| **R-3** | il **registro delle righe di commessa**, che si scriveva e non si leggeva | ✅ **fatto** (2026-08-28) — nato dal collaudo, §14 | `commesse/<id>/registro/` · `CommessaRegistroDialog.vue` |

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

### 3.1 ✅ Un residuo che era del DB — chiuso dal team DB

`E_PREV_ANNULLA_COMMESSA_EMESSA` **resta** (Q-9), e il §9.7.4 del brief DB diceva
che *«il suo testo guadagna il rimedio»*. Letto a catalogo il 2026-08-26 la sua
`soluzione` prometteva ancora **la strada di prima**:

> *«l'operazione va ripresa dal lato fatturazione, con una nota di credito o uno
> storno delle attività già emesse»*

Non era un difetto mio e non l'ho corretto dal backend: il ripiego che ho scritto
non promette una via d'uscita che il catalogo non nomina.

✅ **Chiuso — riletto a catalogo il 2026-08-27**: il testo adesso nomina il verbo
per intero e dice anche dove NON arriva.

> *«…dal cruscotto competenza, sulla casella «Emesse non fatturate», il verbo
> «Riporta da emettere» rimette le righe RESIDUE a NON_EMESSA — e da lì la
> chiusura del preventivo le ritira da sé, senza che nessuno debba
> ricordarsene. Il verbo prende SOLO i residui veri: riga lucchettata, giro di
> fatturazione COMPLETED e nessuna riga di fattura. Le righe già dentro una
> fattura viva non le tocca, e per quelle la strada resta la nota di credito.»*

⭐ È il patto dei tre livelli che regge fino in fondo: il **catalogo** dichiara la
via d'uscita, il backend la trasporta senza riscriverla, il frontend la mostra.
E la frase dichiara anche il **limite** del verbo, che è la parte che di solito
manca — un rimedio che non dice dove si ferma manda a sbattere.

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

POST /api/v1/vendite/attivita-fatturabili/riportabili/
     body { attivita_fatturabili_ids: [int] }
     → { motivi: [...] }        # per spiegare senza far fallire
     # POST e non GET: 200 id non stanno in una query string. Nessun
     # side-effect, nessuna Idempotency-Key, stesso permesso del verbo.
```

| Scelta | Perché |
| --- | --- |
| `post_permission = "riporta_da_emettere"` | è la riga **33** di `config.azioni_processo`, già seminata (Q-3). ⛔ Non si riusa `reset_lotto_fattura_draft`: legherebbe un verbo di recupero a chi può **cancellare** documenti |
| `require_idempotency_key=True` | modifica stato, come ogni verbo di comando |
| **una sola** `SELECT fn_…` nel repository | l'atomicità è per costruzione: la madre DB fa le due scritture e il log in una transazione. ⛔ Niente `transaction.atomic()` con due chiamate — sarebbe una seconda implementazione dell'atomicità che il DB già garantisce |
| ⛔ **niente coda** | «Riporta da emettere» è **sincrono**: due scritture, nessun job. Accodarlo per simmetria con «Rendi definitive» importerebbe il problema della dedup, che qui non esiste (§11.2 del brief DB) |
| traduzione errori via `translate_db_errors` | così `hint`, `fields` e **`targets`** arrivano all'envelope: la madre DB compone già il bersaglio (COMMESSA, poi FATTURA) |

⚠️ **Quella lettura non è un lusso.** Il codice `E_ATTIVITA_GIA_DA_EMETTERE` porta
scritto a catalogo che *«il frontend deve gate-are l'azione sui codici che ha già
in riga invece di proporla sempre: incontrare questo errore vuol dire che
l'elenco mostrato era invecchiato»*. È come il frontend ri-guarda prima di agire su
una selezione che ha in mano da un po', ed è cablata: `riportaSelezionati`
chiama `checkRiportabili` **prima** della mutazione.

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

## 6. ✅ Il prerequisito DB — CONSEGNATO il 2026-08-27

Merge `#1407` su `Tito-dev`, fast-forward su `dev/backend-tid`, migrate di Tid
alle 08:20. ⚠️ **Verificato sugli oggetti vivi, non sui commit**: un file in git
non è una colonna nel database.

| # | Chiesto | Consegnato |
| --- | --- | --- |
| **D-1** | 4 colonne su `vw_dash_competenza_attivita` | ✅ e sono **otto**: le 4 chieste più `lotto_provenienza_id`/`_codice` e `articolo_codice`/`_descrizione` |
| **D-2** | la dimensione nel `GROUP BY` della mensile | ✅ `motivo_non_fatturata` presente |
| **D-3** | il pgTAP che lega vista e `fn_check_*` | ✅ `test-motivo-non-fatturata-v1`, **17/17** come applicazione |
| **D-4** | il seed della lista | ✅ `ui.lista_definizione` **49** (non 44), 11 colonne |
| **D-5 · D-6** | i due messaggi che mandavano dalla parte sbagliata | ✅ riscritti |

### 6.1 ⭐ Tre correzioni del team DB, e la seconda cambia il codice BE

**1. Il vocabolario ha QUATTRO valori, non tre.** Oltre ai tre chiesti c'è
`SENZA_ATTIVITA_FATTURABILE`: il `LEFT JOIN` ammette una riga di commessa a
`EMESSA` **senza** riga in `attivita_fatturabili`, e lì la chiave del verbo
sarebbe `NULL` — la lista lo proporrebbe su una riga senza bersaglio. Nessun
percorso scritto oggi la produce (cercato: non esiste un `DELETE FROM
vendite.attivita_fatturabili` in tutto il repo), **e non è una ragione per non
trattarla**.

**2. ⛔ `IS DISTINCT FROM 'COMPLETED'`, non `<>`** — ed è la correzione che vale
di più. `stato_esecuzione` è **nullable** e il `CHECK` ammette anche `ERRORE`:
col `<>` un lucchetto a `NULL` darebbe `NULL`, il `CASE` cadrebbe sul ramo dopo e
la vista direbbe **`RESIDUO` su una riga che la mutazione rifiuta** — cioè
esattamente la divergenza silenziosa che il D-3 esiste per impedire. Il
vocabolario che avevo proposto nel §3 conteneva quel `<>`.
ℹ️ Conseguenza dichiarata: `ERRORE` finisce in `GIRO_IN_CORSO`.

**3. L'id libero non era 44, era 49.** ⭐ E la lezione è generale: *«un id libero
non si dichiara in un documento — si legge dal CSV nel momento in cui si
semina»*. Il 44 era una **fotografia** del catalogo presa quando ho scritto il
brief.

### 6.2 ✅ La whitelist da usare, e cosa fa il verbo su ciascun valore

| Valore | Chiede un'azione? | Codice della mutazione |
| --- | --- | --- |
| `IN_ATTESA_LOTTO` | ⛔ no | `E_ATTIVITA_GIA_DA_EMETTERE` |
| `GIRO_IN_CORSO` | ⛔ no | `E_ATTIVITA_IN_LAVORAZIONE` |
| ⭐ `RESIDUO` | ✅ **sì** | — il verbo accetta |
| `SENZA_ATTIVITA_FATTURABILE` | ⛔ no | — **la chiave è `NULL`**: non proponibile |

⚠️ **La card si spezza su `RESIDUO` / non-`RESIDUO`**, non su quattro numeri: gli
altri tre sono «niente da fare», e distinguerli serve al **drill-down**, non al
contatore.

⭐ La lista è `WHERE motivo_non_fatturata = 'RESIDUO'`, e
`attivita_fatturabile_id` **non è a catalogo di proposito**: serve al verbo, non
all'occhio. Il backend lo proietta comunque.

### 6.3 Le due richieste del §7 del brief DB, verificate

| # | Richiesta | Esito |
| --- | --- | --- |
| **7.1** 🔴 le 4 chiavi i18n — *cancello CI rosso* | ✅ **chiuso**: aggiunte in `it.json` e `en.json` con le frasi del seed, `check_i18n_keys.py` torna verde (462 intestazioni tradotte) |
| **7.2** 🔴 il breakdown elencherebbe `EMESSA_NON_FATTURATA` due volte | ✅ **già coperto, e non per fortuna**: il BE accumula in un dizionario per `stato_fattura_codice_interno` (`voce["n_attivita"] += …`), quindi è **agnostico alla dimensione**. È il rimedio messo il 2026-08-20 per `tipo_movimento`, e ha il suo presidio: `test_breakdown_non_duplica_lo_stato_su_bucket_spezzato`. ⚠️ Verificato anche che il breakdown vive **solo** su `stadio = FATTURATA`, dove `motivo_non_fatturata` è `NULL` |

---

## 7. Documentazione, e la contesa dichiarata

> ✅ **Il piano qui sotto è ESEGUITO** (§12, 2026-08-27). Resta come piano perché
> dice *perché* ciascuna riga andava toccata.

| File | Cosa | Stato |
| --- | --- | --- |
| `docs/it/guide/cruscotti-fatturazione.md` §7.6 | l'avvertenza 🔴 su «Elimina dal lotto» **si toglie**: da L1 il difetto non c'è più | ✅ fatto |
| stessa guida §3.1 | la card prende un verbo; ⚠️ e va corretta la frase *«se in quella casella c'è un numero, qualcosa si è rotto»* — è vera per il **verbo di massa**, non per la casella | ✅ fatto — e le situazioni sono **quattro**, non tre |
| stessa guida §7.1 | il verbo nuovo entra in tabella col suo permesso | ✅ fatto — riga additiva, vedi la contesa qui sotto |
| stessa guida | ⭐ **chiudere un documento adesso ritira lavoro**: è un comportamento che l'operatore deve sapere **prima**, non scoprire dopo | ✅ fatto — è la nuova **§7.7** |

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
| **E-1** | la **guida operativa**: chiudere un documento adesso **ritira lavoro**, ed è un comportamento che l'operatore deve sapere *prima*, non scoprire dopo | ✅ **fatto** (§12): è la nuova §7.7 della guida |
| **E-2** | il messaggio di `E_RIGA_COMMESSA_NON_MANUALE` (guard 4 di `fn_annulla_commessa_attivita`) promette *«il rimedio è SEMPRE a monte, sul documento»*: da L7b quella frase **è vera**, e può nominare il documento invece di lasciarlo cercare | ✅ **consegnato dal team DB** come **D-6**: il messaggio ha il terzo segnaposto e il documento arriva risolto da `fn_get_sorgente_documento_ref` — a video si legge `ORD0000227`, non un UUID |
| **E-3** | 🟠 `codici-errore-baseline.sh` segnala un **rientrato**: `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` | ⏸️ **APERTO — l'unico dei tre.** Verificato il 2026-08-27 sul file committato `db/baseline-codici-errore-famiglie.tsv` (riga 81, ancora `NOT_FOUND`) |

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

---

## 10. BE-3 e BE-4 — fatti il 2026-08-27

| Pezzo | Dove |
| --- | --- |
| `VenditeRepository.list_dash_competenza_residui` + `DASH_COMPETENZA_RESIDUI_SORT_COLUMNS` | `db/vendite_repository.py` |
| `check_attivita_riportabili_da_emettere` · `riporta_attivita_da_emettere` | idem |
| `DashCompetenzaResiduoRow` | `types.py` |
| `fn_dash_competenza_residui` · `fn_check_attivita_riportabili` · `fn_riporta_attivita_da_emettere` · `_valida_ids_riporto` | `services/vendite_service.py` |
| `ApiDashboardCompetenzaResidui` · `ApiAttivitaRiportaDaEmettere` · `ApiAttivitaRiportabili` | `api/views_dashboard_competenza.py` + `urls_v1.py` |
| 13 test | `tests/services/test_riporta_da_emettere_service.py` |

**Rotte**: `GET /vendite/dashboard-competenza/residui/`,
`POST /vendite/attivita-fatturabili/riporta-da-emettere/` (permesso
`riporta_da_emettere`, `Idempotency-Key` obbligatoria),
`POST /vendite/attivita-fatturabili/riportabili/`.

### 10.1 ⛔ Un difetto trovato provando sul database vero, e sarebbe stato invisibile

La prima versione di `check_attivita_riportabili_da_emettere` faceva
`list(row[0] or [])`. Contro il DB vero ha risposto:

```python
{'motivi': ['[', ']']}
```

⚠️ Il `jsonb` arriva come **stringa** su questa connessione — misurato — e
`list()` ne itera i **caratteri**: `"[]"` diventa **due motivi** dove non ce
n'era nessuno. A video il verbo sarebbe risultato **bloccato su righe
perfettamente riportabili**, senza nessun errore e senza nessun test rosso.
⭐ È la stessa specie del `coerceJsonbToObject` che il frontend ha già come
difesa; corretto con lo stesso ramo, e con la ragione scritta accanto.
⚠️ Non si è potuto riusare `apps.core.db._helpers.call_jsonb_fn`, che quel ramo
ce l'ha: è annotato `-> dict` e questa funzione ritorna un **array**. Al secondo
consumatore di array si estrae.

### 10.2 Le prove, sul DB vero e sulle 5 righe reali

Tutto in transazione **rollata**: le 5 righe sono ancora dove erano.

| Cosa | Esito |
| --- | --- |
| la lista dei residui, luglio 2026 | **5 righe**, tutte `RESIDUO`, tutte con `lotto_provenienza = LTF-0000679` — ⭐ **è il lotto della fattura 834**, quella che fallì la numerazione e da cui è nato l'intero cantiere |
| `fn_check` sulle 5 | `[]` — nessun motivo |
| il verbo sulle 5 | `riportate 5, riemesse 5`; residui dopo: **0** |
| dopo il rollback | di nuovo **5** |
| su un'attività **ancora in fattura** | rifiutata: `E_ATTIVITA_ANCORA_IN_FATTURA` · 409 · `hint` presente · **`targets = (COMMESSA 322, FATTURA 20024)`** |

⭐ **L'ultima riga è la chiusura del giro cominciato con BE-2**: il bersaglio che
la madre DB compone arriva intero fino all'envelope, e a video diventerà «Apri
Fattura 20024». Nessun componente deve scrivere una riga per averlo.

### 10.3 Due scelte, con la ragione

**`translate_db_errors`, non `raise_from_database_error`.** Il secondo accetta il
codice del database **solo se dichiarato** in un elenco locale — cioè una seconda
copia del catalogo. Il vocabolario di questo dominio è appena cresciuto da tre a
quattro valori senza che il backend lo sapesse: una copia si sarebbe disallineata
in silenzio, e un codice nuovo sarebbe arrivato all'operatore come generico.

**La registrazione in `_LISTE` è stata scritta e poi RITIRATA.** Il presidio
`test_liste_configurabili_seed` è diventato rosso: la lista `49` **non ha un
preset di default** (le tre sorelle ne hanno uno ciascuna, lei zero — né a DB né
nel CSV). ⚠️ Non blocca il frontend, perché `ui.fn_resolve_lista_config` ripiega
sul catalogo e risolve **11 colonne**; ma è un'incoerenza di seed. Registrarla
ora avrebbe lasciato la CI rossa per una lista che il frontend **non monta
ancora**: la registrazione va fatta nello stesso passo del mount, ed è la stessa
regola delle «due metà concordate insieme» che il team DB ha invocato per le
chiavi i18n. ➡️ **D-7 al team DB**: manca la riga di `ui.lista_preset`.

✅ **Chiuso**: il preset è stato seminato dal team DB e **letto sull'oggetto vivo**
il 2026-08-27 — `lista 49 · dash_competenza_residui_default ·
[{"col":"competenza_mese","dir":"asc"}] · is_default`. La lista è registrata nel
presidio e il presidio è verde. ⚠️ Letto dal database, non dai commit: un
changeSet mergiato non è un oggetto applicato.

---

## 11. FE-2 — il verbo a video, scritto il 2026-08-27

| Pezzo | Dove |
| --- | --- |
| client del verbo + dei motivi | `vendite/api/attivitaFatturabili.js` (nuovo) |
| client della lista | `vendite/api/dashboardCompetenza.js` |
| sezione paginata `residui` + `STADIO_RESIDUI` | `vendite/stores/dashboardCompetenza.js` |
| card spezzata, drill-down, selezione, verbo | `vendite/views/DashboardCompetenzaView.vue` |
| 15 chiavi i18n (verbo, conferma, esiti, i **quattro** motivi) | `locales/it.json` · `en.json` |
| `n_residui` / `valore_residui` nell'aggregata + 2 test | `services/vendite_service.py` · `tests/.../test_dashboard_competenza_service.py` |

### 11.1 La card adesso dice **due** cose

Sotto il numero grande compare *«di cui N da recuperare · € …»*, oppure
*«nessuno da recuperare»*. ⛔ Il conteggio arriva dal **backend**
(`n_residui`), non si deduce dalla lista: la lista è paginata, e sommare la
pagina darebbe un parziale che sembra un totale.

⭐ È la chiusura del difetto di modello del §5.3: fino a ieri la card sommava
lavoro fermo per un difetto e lavoro in transito legittimo — due situazioni con
rimedi **opposti** — e la guida operativa diceva *«se in quella casella c'è un
numero, qualcosa si è rotto»*, che era vero solo per metà.

⚠️ **Provato costruendo il caso**: nei dati di sviluppo il transito non esiste
(5 righe su 5 residue), quindi un test sulla popolazione reale sarebbe stato
verde senza verificare niente. Il fixture `_ROWS_DUE_POPOLAZIONI` fabbrica tutte
e **quattro** le situazioni, compresa quella che nessun percorso scritto oggi
produce. E il presidio è stato **visto fallire**: rompendo il discriminante
(`stadio` invece di `motivo`) il test cade.

### 11.2 Il drill-down e la selezione

Cliccando la card si scende sui **residui**, non sulle commesse: stessa forma
già scelta per «Da emettere» → gruppi fatturabili. Ogni card scende sull'unità
del **proprio verbo**, e lo smistamento è in **un punto solo** (`loadDrillDown`).

⭐ **Ogni riga della lista è selezionabile per costruzione**, e non c'è nessun
predicato lato frontend: il backend filtra `motivo_non_fatturata = 'RESIDUO'`,
cioè esattamente il perimetro del verbo. Ri-filtrare qui sarebbe una seconda
implementazione di una regola che vive nel database.

⚠️ Il verbo chiede conferma **pur essendo reversibile** (si rifattura e si è al
punto di prima): la conferma non protegge da un danno, dichiara **quante righe**
sta per toccare. Un verbo di massa che parte al primo click su una lista
paginata è il modo di riportare indietro più di quanto si è guardato.

⚠️ E l'esito distingue: `riportate > 0` è un toast verde, **zero è un avviso** —
zero non è un successo, vuol dire che l'elenco a schermo era invecchiato.

### 11.3 ✅ L'ultimo rosso, chiuso dal team DB il 2026-08-27

`test_ogni_lista_del_seed_ha_un_preset_default` è **rosso** su
`vendite.dash_competenza_residui`: la lista non ha una riga in `ui.lista_preset`
(le tre sorelle ne hanno una ciascuna). È il **D-7** del brief DB.

⭐ **E il rosso è arrivato nell'ordine giusto**, il che dice che i presidi
funzionano: finché il frontend non montava la lista, registrarla nel registro
avrebbe reso la CI rossa per niente. Montandola, `test_registro_copre_tutte_le_liste_montate_dal_frontend`
è andato rosso **da solo** — ha imposto la registrazione — e a quel punto è
emerso il rosso vero, che è il seed mancante.

⛔ **Non l'ho aggirato e non l'ho dichiarato come eccezione**: un preset è un
seed, e i seed sono lavoro del team DB.

✅ **Consegnato con la PR #1409**: `ui/lista_preset.csv` id 49 + 11 righe di
`lista_preset_colonna`, applicato. I nove test del presidio sono verdi.

⭐ **E hanno corretto un mio suggerimento sbagliato.** Avevo scritto «sul modello
della `43`», che ha il preset **più corto** del catalogo: non è una convenzione,
è **drift** — la colonna emittente fu aggiunta il 2026-08-18 e quei preset non
furono aggiornati. Le liste nate dopo (44, 45, 47, 48) hanno preset = catalogo, e
hanno seguito quelle. ⚠️ Con `emittente_fiscale` **presente e `visibile = f`**,
non omessa: omessa sarebbe diventata «colonna nuova» per il banner DEF-2, e una
scelta dichiarata si sarebbe travestita da dimenticanza.

⭐ Hanno anche messo un **presidio pgTAP** (`test-liste-preset-default-v1`, 5
asserzioni, **viste rosse**) perché il difetto l'avevo trovato *a mano* contando
le righe delle liste sorelle — e fra le cinque ce n'è una che vale oltre questo
caso: `ui.lista_preset_colonna` ha **due FK separate** e niente obbliga la
colonna ad appartenere alla stessa lista del preset. Il modello lo ammette, e
l'effetto sarebbe una lista che mostra la colonna di un'altra **senza nessun
errore di vincolo**.

### 11.3-bis ⚠️ E una loro scelta ha corretto il MIO ordinamento

Il preset dichiara `ordinamento_default = competenza_mese ASC`. Il mio store
mandava `valore DESC`, copiato dalle liste sorelle.

⛔ La loro ragione è di dominio e batte la simmetria: **questa non è una lista di
grandezze, è una coda di recupero**. Un residuo che invecchia si avvicina al
limite di emissione, quindi il più vecchio è il più a rischio — stessa logica del
backlog (`anzianita_giorni desc`), non dei gruppi fatturabili.

⚠️ Il campo `ordinamento_default` **non è ancora consumato dal frontend**: la
convenzione è allineare lo store **a mano** (lo fanno già `auditLog` ed
`emittentiFiscali`). Allineati **entrambi i lati** — store e default del
repository — perché se divergessero l'**export**, che non passa dai filtri a
video, darebbe un ordine diverso dalla schermata e nessuno se ne accorgerebbe
aprendo il foglio. E con la primaria ASC anche il **tiebreak** è passato ad ASC:
altrimenti dentro lo stesso mese l'elenco sarebbe andato al contrario di come è
stato chiesto (il difetto corretto in 30 punti il 2026-08-03).

### 11.4 Stato dei presidi

| | |
| --- | --- |
| `check_i18n_keys.py` | ✅ verde — 462 intestazioni tradotte, parità it/en |
| `vite build` | ✅ verde |
| suite backend | ✅ **4134** test, **tutti verdi** |

### 11.6 ⏸️ Una cosa che il team DB lascia aperta, e non è nostra

`ordinamento_default` ha **due convenzioni** in giro: `clienti_default` ed
`emittenti_fiscali_default` ordinano per `campo_sorgente`, tutti gli altri per
`codice`. Non l'hanno chiusa di proposito — deciderlo dentro un test sarebbe
stabilire una convenzione fuori dal cantiere che possiede le liste.
ℹ️ Per noi è indifferente: `competenza_mese` è sia `codice` sia `campo_sorgente`,
quindi risolve con entrambe.

---

## 12. Documentazione — fatta il 2026-08-27

| File | Cosa |
| --- | --- |
| `backend/vendite/manual/api_riporta_da_emettere.md` | **nuova**: la scheda del verbo, struttura standard (Scopo · Contesto · Input · Output · Regole · Dipendenze DB · Note di migrazione) |
| `backend/vendite/manual/api_dashboard_competenza.md` | la lista dei residui e il suo export, in Input e in Output |
| `dev/api.md` | l'inventario: la riga della Lente 1 e una **voce propria** per il verbo |
| `guide/cruscotti-fatturazione.md` | §3.1, §7.1, §7.6 e la nuova **§7.7** |

### 12.1 ⭐ La guida era già stata scritta dal team DB — e in due punti era stantia

Non l'ho riscritta: il team DB l'aveva già aggiornata con la §3.1 e il caso reale.
Mancavano quattro cose, e due erano **dichiarazioni diventate false**:

| # | Cosa diceva | Cosa dice adesso |
| --- | --- | --- |
| 1 | *«Resta da fare il pulsante: a video non c'è ancora»* | ✅ c'è, con la sua lista e la selezione |
| 2 | *«dentro quella casella le situazioni sono **tre**»* (in **tre** punti della pagina) | **quattro** — la quarta è arrivata col `20260826-54` ed è un'anomalia |
| 3 | il verbo non era nella **tabella dei verbi** del §7.1 | c'è, con la nota che agisce sulle **righe spuntate** e non sul mese |
| 4 | il ritiro alla chiusura di un documento **non era documentato da nessuna parte** | è la nuova **§7.7** |

⚠️ Il punto 4 è quello che vale di più per chi usa il programma: **chiudere un
documento adesso ritira lavoro**, e prima non lo faceva. È un comportamento che
l'operatore deve sapere *prima*, non scoprire dopo — e la §7.7 dice anche cosa
fare quando il documento **rifiuta** di chiudersi perché ci sono righe già
emesse: si recuperano con «Riporta da emettere», poi il documento si chiude
portandosele via.

### 12.2 Sulla contesa dichiarata nel §11.3 del brief DB

La §7.1 è la tabella che l'altro cantiere («Rendi definitive va dove stanno i
lotti») deve riscrivere. ⚠️ Il mio intervento è **additivo** — una riga nuova in
coda alla tabella e tre note sotto — e non tocca la riga di «Rendi definitive»:
un merge fra i due lavori non ha nulla da scegliere. Resta valido l'avvertimento
di coordinarsi, non di lavorare in parallelo sulla stessa riga.

> ⭐ **Aggiornamento 2026-08-28 — la contesa non c'è più: è diventata eredità.**
> Il cantiere gemello ha chiuso il suo collaudo (16 prove verdi, numeri veri
> consumati) ed è stato archiviato in
> [work-done](../work-done/brief-be-fe-rendi-definitive-sui-lotti.md) **con la
> sua voce C-2 ancora aperta**: la riscrittura di §7.1 e §6.3. Quella voce è
> passata **qui**, nella tabella «Cosa resta aperto» in testa al file, perché
> l'ordine che la bloccava era proprio l'attesa del nostro **L5**.
>
> ➡️ **Eseguita il 2026-08-28**: il dettaglio, e le due annotazioni della
> consegna che erano sbagliate, stanno nel **§12.3** qui sotto.


### 12.3 ✅ C-2 — la guida rimessa in pari su «Rendi definitive» (2026-08-28)

La voce **C-2** è arrivata qui dal cantiere gemello, che ha chiuso il suo
collaudo (16 prove, numeri veri consumati) ed è stato archiviato **lasciandola
aperta**. È stata eseguita lo stesso giorno.

#### ⛔ Prima: due annotazioni della consegna erano sbagliate

| Annotazione | Perché è sbagliata |
| --- | --- |
| *«la riscrittura va fatta **al passo L5**»* | 🔴 **L5 era già fatto.** `L5` è un lotto del **brief DB** — «la card *Emesse non fatturate* prende un verbo» — ed è esattamente il §12 di questo brief, chiuso il 2026-08-27. L'ordine che bloccava C-2 era **decaduto da un giorno**, e la riga la dichiarava ancora bloccata |
| *«§7.1 e **§6.3** di `cruscotti-fatturazione.md`»* | 🔴 **La guida non ha un §6.3.** Ha `## 6. Come si distinguono` senza sottosezioni. `§6.3` è una sezione **del brief gemello** («Sulla Lente 1»): i due riferimenti si sono fusi passando di mano. Il punto vero da correggere nella guida era la **§7.5** |

⭐ **Ed è la specie di difetto che questo cantiere insegue da tre giorni**: non un
errore di codice, ma **un'indicazione che era vera quando è stata scritta**.
Chi avesse eseguito la consegna alla lettera avrebbe aspettato un passo già
fatto, e cercato una sezione che non esiste.

#### Cosa è stato corretto, e su cosa si è verificata la verità

⚠️ Non sulla parola del brief gemello: **sul codice**. `DashboardCompetenzaView`
non ha più il verbo sulla card `Fatturate` — ha il pulsante «Vai ai lotti (N)»
col filtro (mese + stato `EMESSA`), gated su permesso e conteggio; il verbo vive
in `LottiListView` in due forme, sui selezionati e sul mese. Sono le decisioni
**D-1 → D-3** del gemello, applicate.

| Dove | Cosa diceva | Cosa dice |
| --- | --- | --- |
| guida §7.1, tabella dei verbi | «Rendi definitive» → card `Fatturate` | ➡️ **non è più qui**: sta su Vendite → Lotti; sulla card resta il **rimando** filtrato |
| guida §7.1, nota sotto | ⚠️ *«sta sulla card `Fatturate`, non su `Emesse non fatturate`»* — una correzione di agosto che **si è a sua volta invecchiata** | ⭐ il racconto dello spostamento, con la tabella «dove c'è cosa» e la regola che lo motiva: **un verbo sta dove sta l'elenco del suo oggetto** |
| guida §7.5 | 🔴 *«dalla card `Fatturate` al lotto non si arriva: è un buco noto»* | ✅ **il buco è chiuso**: dalla card ci si arriva col rimando filtrato. Resta aperto l'aggancio **dalla singola riga**, e adesso la guida distingue le due cose |
| guida, testata | — | la revisione dichiara lo spostamento e avverte che **le regole non cambiano: cambia dove si preme** |
| `mappa-concentrica.md` | «dalle tre lenti si agisce: … «Rendi definitive» …» | corretta: «Rendi definitive» **non** è fra quelli, e al suo posto entra «Riporta da emettere» |

🔎 La riga della mappa era il **terzo punto** segnalato dal gemello, ed è l'unico
dei tre che era giusto: la stessa affermazione in un documento diverso, che chi
corregge solo la guida si lascia dietro.

---

## 13. Revisione critica del codice — 2026-08-27

Passata di rilettura su **tutto** ciò che questo cantiere ha scritto o toccato,
cercando difetti, codice fragile, duplicati e valori a mano. **13 correzioni
applicate, 2 cose segnalate e non toccate.** Suite **4136 test verde**, i18n ·
eslint · `vite build` verdi, catena riprovata **sul DB vero** con contesto
operatore e transazione rollata.

### 13.1 🔴 I tre che sarebbero arrivati a video

**1. La card e la sua lista si contraddicevano sul segno.** `valore_residui`
sommava in **valore assoluto**, ma viene reso *sotto* un totale col segno e
*sopra* una lista che mostra il valore di riga col segno. Un residuo di
**RETTIFICA** — e il verbo li tocca eccome (Q-8, nessuna whitelist su
`tipo_movimento`) — avrebbe detto «di cui 1 · 500,00 €» sotto un totale di
**−500,00 €**: due metà che non si sommano al tutto, e chi guarda non ha modo di
capire quale delle due mente. Ora è netto, come `valore` accanto a cui vive.
⭐ Test nuovo, **provato rosso prima e verde dopo**
(`test_residuo_di_rettifica_resta_negativo`).
⚠️ L'assoluto in quella funzione ha **una sede sola** ed è `valore_abs`, che
alimenta il donut di copertura — dove non compensare è proprio il punto. Il
difetto è nato copiando la riga sbagliata delle due.

**2. Una chiave i18n che non esisteva.** `motivoLabel` costruisce l'indirizzo da
`motivo_${codice.toLowerCase()}`; il quarto valore del vocabolario è
`SENZA_ATTIVITA_FATTURABILE` e la chiave scritta era `motivo_senza_attivita`. La
chiave costruita non l'avrebbe mai trovata e a video sarebbe uscito il **codice
grezzo**. ⚠️ Tre valori su quattro giusti — e il quarto è quello che **oggi non
capita mai**: è il §5.3 di questo stesso brief che dice «zero occorrenze non
significa che il caso non esiste», e l'ho sbagliato lo stesso.

**3. Il tooltip della card diceva una cosa diventata falsa.** *«qui restano solo
attività sospese, posticipate o rimaste indietro. Non avanzano da sole»*: dal
`20260826-54` è vero per **una** situazione su quattro. Riscritto in italiano e
inglese. ⚠️ È la stessa specie di difetto della guida (§12.1) rientrata dalla
porta dell'**interfaccia** — la frase stantia non era solo nel documento.

### 13.2 Due difetti strutturali

**4. `POST /riportabili/` non aveva un permesso.** Senza `post_permission`,
`ZeroERPPermission` cade sul mestiere del metodo HTTP e un POST chiede **`add`
sull'area**. Gate sbagliato nei **due versi**: chi può riportare ma non creare si
vedeva negare la spiegazione di un verbo che gli spetta, chi può creare senza
poter riportare poteva interrogarlo. Ora porta `riporta_da_emettere`, lo stesso
del verbo. ⭐ *Chi può agire può chiedere: è la stessa porta, guardata prima di
aprirla.*

**5. ⛔ `checkRiportabili` non lo chiamava nessuno.** La catena c'era tutta —
rotta, view, service, repository, il ramo difensivo sul `jsonb` — e il frontend
non la toccava mai. Il §4 di questo brief dice perché esiste; il catalogo lo dice
sul codice `E_ATTIVITA_GIA_DA_EMETTERE`. Ora `riportaSelezionati` chiama la
verifica **prima** della mutazione: se torna un motivo si avvisa (risolvendo il
`reason_key` che il DB dichiara, con `labelOrCode`), si azzera la selezione e si
rilegge l'elenco.
⚠️ Senza, il rifiuto arrivava comunque — la madre non si fida di nessuno — ma
come **un** errore per l'intero elenco, che è **atomico**: l'operatore non
saprebbe quale riga lo ha fermato né perché, e riproverebbe.
🔴 **È la specie di difetto della memoria `feedback_bb_legge_non_trasporta`**:
niente fallisce, nessun test è rosso, e la funzione a video semplicemente non
c'è. L'ho trovata contando i **consumatori** di ciò che avevo scritto, non
rileggendo il codice.

### 13.3 ⛔ Il duplicato peggiore era una mia «de-duplicazione»

Il guard `order_by`/`order_dir` era copiato **sette volte** in
`vendite_service.py`, e l'ho estratto in un helper privato.
🔴 **Sbagliato: il building block esisteva da giugno.**
`apps.core.services.list_helpers.validate_order_params` fa esattamente quello, è
usato **tredici volte** — e **una di quelle tredici è in quello stesso file**,
con accanto il commento *«`validate_order_params` — non un'altra copia inline del
blocco»*. Qualcuno quella lezione l'aveva già scritta, sopra la mia testa.

Correzione vera:

| | |
| --- | --- |
| `validate_order_params` | cresce `nullable: bool = False` — per le liste in cui «non specificato» è legittimo e l'ordine lo decide il **default del repository**. È la stessa apertura che `validate_enum_param` ha da sempre per i filtri opzionali |
| `allowed_columns` | da `frozenset[str]` a `Collection[str]`: le whitelist di vendite sono `dict[chiave esposta → colonna SQL]`, e `in`/`sorted()` su un dict guardano le chiavi. ⚠️ **L'annotazione stretta era l'unica cosa che diceva «questo BB non fa per te»** |
| `_valida_ordinamento` | resta, ma come **wrapper di dominio** che riempie l'`error_code` — stessa forma di `_validate_enum` accanto, per la stessa ragione |
| `order_dir` | ⛔ il confronto nel BB resta **case-sensitive**: chi accetta `ASC` normalizza prima di chiamare. Rilassarlo nel BB sarebbe stato un cambio di contratto silenzioso per tutti e tredici i chiamanti, introdotto di straforo da un refactoring |

⭐ **La lezione operativa**: il catalogo BB va letto **prima** di estrarre, non
dopo — è la prima difesa contro questa specie di duplicato, e stavolta ha
funzionato solo perché stavo aggiornando la documentazione.

### 13.4 Duplicazione e valori a mano — il resto

| Cosa c'era | Cosa c'è |
| --- | --- |
| `'RESIDUO'` **letterale dentro la `WHERE`** + costante gemella nel service | `MOTIVO_NON_FATTURATA_RESIDUO` in `vendite_repository.py`, passata come **parametro SQL**. ⚠️ È la lezione già pagata sul letterale `stadio`, scritta due righe più sotto nello stesso file (`TIPO_INDIRIZZO_FATTURAZIONE`) |
| `_competenza_mese_obbligatoria` esisteva già | la `GET` dei residui ne aveva una **copia**: due frasi diverse per la stessa richiesta malfatta, a seconda di quale endpoint la riceve |
| `'EMESSA_NON_FATTURATA'` a mano nel template | `STADIO_RESIDUI`, che era **già importato in quel file** |
| `residui_hint` | chiave i18n **morta** dopo la riscrittura della card. ⚠️ Il presidio vede le chiavi *rotte*, non quelle *orfane* |
| `context={"op": f"{function_name}"}` ×2 | f-string senza interpolazione |
| contratto OpenAPI: `valore (default)` | il default è `competenza_mese` ASC — **un contratto pubblicato che diceva il falso** |

### 13.5 ⚠️ Un commento che mentiva

Avevo scritto che il default `competenza_mese ASC` mette «i più vecchi in cima,
perché il residuo più vecchio è il più vicino al limite di emissione».
🔴 **Falso**: la lista è filtrata su **un mese solo**, quindi quella colonna è
**costante** e l'ordine che si vede lo decide per intero il tiebreak (commessa,
poi chiave). La clausola resta — è ciò che il catalogo dichiara, e sarebbe già
quella giusta se il filtro si allargasse a un intervallo — ma ora lo dice, nel
repository e nella scheda API.

⭐ Un commento che spiega una cosa che non succede è **peggio** di nessun
commento: il prossimo lettore ci costruisce sopra.

### 13.6 ✅ Le due decisioni — prese il 2026-08-27

Erano segnalate e non toccate. Guardandole da vicino **sono cambiate tutte e
due**: una in peggio, una in meglio.

#### A ✅ `toggleAll` — non era una trappola non vista, era una **già documentata due volte**

Cercando i consumatori è saltato fuori che il seleziona-tutto corretto per liste
paginate **esisteva già, scritto a mano, in due posti** — `useSelezioneLotti` e
la **lista gruppi di questa stessa vista** — ognuno con un commento lungo che
dice di non riusare `toggleAll` del BB. 🔴 **Io l'ho usato lo stesso, cento righe
sotto uno dei due avvertimenti.**

E non ero il solo. Il conto vero, su **sei** consumatori:

| | Consumatori | `toggleAll` |
| --- | --- | --- |
| ✅ dialog a lista **intera** | `useRigheSelezioneQta` (3 dialog) · `PreventiviSmistamentoDialog` | **corretto** — è il suo mestiere |
| ✅ paginati, riscritto **a mano** | `useSelezioneLotti` · gruppi in `DashboardCompetenzaView` | ~20 righe duplicate, due volte |
| 🔴 paginati, **col difetto** | `ResiCodaTable` · `CommessaGestioneDrawer` · residui di competenza | perdita silenziosa |

⚠️ **`CommessaGestioneDrawer` è emerso per ultimo** e non era nel conto che avevo
dato a Tid: pagina lato server e `onRighePage` non azzera la selezione, quindi ha
esattamente lo stesso difetto. **Su cinque liste paginate, tre erano rotte: il
commento come presidio aveva un tasso di riuscita del 40%.**

**Decisione (ok Tid): estrazione ADDITIVA.** Il BB offre due terne e si sceglie
in base alla lista:

| Lista | Terna |
| --- | --- |
| **INTERA** (dialog) | `toggleAll` · `allSelected` · `anySelected` — ⛔ **non toccati** |
| **PAGINATA** | `toggleAllInPagina` · `allInPagina` · `anyInPagina` |

Le due copie a mano sono collassate sul BB (−40 righe), le tre rotte sono
corrette. **Nessun comportamento cambia per i tre dialog.**

⭐ **La ragione non è togliere righe.** Il nome `toggleAll` *è* la trappola: si
legge «seleziona tutto», significa «sostituisci con questa pagina». La regola
viveva come **disciplina** — un commento «attenzione, qui non usarlo» — e chi non
lo leggeva sbagliava in silenzio. Adesso è **struttura**: la funzione giusta è
quella che si ha sotto mano. È la stessa riga della tabella con cui si chiude il
brief DB archiviato — *da «ricordati di…» a «non si può dimenticare»*.

ℹ️ `allInPagina` **è** `allSelected`, non un secondo calcolo: quello guardava già
le sole `selezionabili`, cioè la pagina. Il nome esiste perché il consumatore
paginato prenda tre nomi coerenti invece di ricordarsi che uno si chiama in un
altro modo — ed era proprio quell'incoerenza (`allSelected` di pagina,
`anySelected` globale) a rendere la coppia sbagliata plausibile.

##### La prova, e perché è stata fatta a mano

⛔ **Nel frontend non c'è un runner di test.** Un fix mai visto fallire è una
speranza, quindi la semantica è stata provata con uno script su **reattività Vue
vera**: due pagine, due righe spuntate nella prima, «seleziona tutto» nella
seconda.

```text
toggleAll        -> [4,5]      · indeterminate a pag.2 con nulla spuntato lì: true
toggleAllInPagina-> [1,2,4,5]  · indeterminate a pag.2 con nulla spuntato lì: false
toggleAllInPagina, ri-premuto  -> [1,2]   (toglie SOLO la pagina corrente)
```

Cinque asserzioni, comprese le due che verificano che **il vecchio perdesse
davvero** — senza quelle la prova non dimostrerebbe niente.
🔵 Resta scoperto: senza runner, questa prova **non gira in CI**. Se un giorno il
frontend ne prende uno, è il primo caso da portarci dentro.

#### B ✅ Il tetto di 200 — **rilievo ritirato, non è un difetto**

L'avevo presentato come un vicolo cieco di questo cantiere. Guardando oltre il
mio file, **è la convenzione di casa**:

| Costante | Verbo | Valore | Guard nel FE |
| --- | --- | --- | --- |
| `MAX_ATTIVITA_RIPORTO` | Riporta da emettere | 200 | no |
| `MAX_ACCREDITI_MASSIVI` | Accredita resi | 200 | no |
| `MAX_GRUPPI_EMISSIONE_MIRATA` | Emissione mirata | 200 | no |

Tre verbi di massa, **stesso numero e stesso comportamento**: nessuno lo
rispecchia a video, tutti e tre lasciano rifiutare il backend con un messaggio
comprensibile. L'esposizione è identica — anche le liste sorelle paginano fino a
100.

**Decisione (Tid): si lascia com'è.** Se un giorno serve l'avviso lato client è
**una** decisione per la famiglia di tre, non per questa lista, e vorrebbe dire
ricopiare il 200 in tre punti del frontend — a meno che il BE non lo esponga, che
oggi nessuno dei tre fa.

⚠️ **L'errore di metodo, che vale più del rilievo**: avevo cercato il tetto solo
dentro `vendite_service.py` e concluso che me l'ero inventato io. È la stessa
specie di misura parziale che questo cantiere ha passato due giorni a smontare —
*il perimetro si cerca, non si presume*.

### 13.7 Le prove, dopo le correzioni

Tutto in transazione **rollata** — le 5 righe vere sono ancora dove erano.

| Prova | Esito |
| --- | --- |
| lista residui, contesto operatore (`app.ruolo_applicativo='OPERATORE'` + `app.current_user_id`) | **5 residui su 5**, tutti `RESIDUO`, chiave del verbo presente su ogni riga |
| **10 colonne × 2 direzioni** su righe vere | 5 righe ciascuna, **nessun 500** |
| `check_attivita_riportabili_da_emettere` sulle 5 | `[]` — il ramo `jsonb` regge (niente `['[', ']']`) |
| stesso, su id inesistente | `E_ATTIVITA_FATTURABILE_NON_TROVATA` con `reason_key` e `dettaglio` = conteggio |
| guard: `order_by='drop_table'` · `order_dir='sideways'` | rifiutati, `E_VENDITE_VALIDATION` |
| guard: assenti · `'DESC'` maiuscolo · `'asc'` | ammessi, 5 righe — **nessuna regressione** dopo l'unificazione |

⛔ **E uno zero non è un dato.** Le prime letture rispondevano **zero** su tutto:
non era un fatto, era il **fail-closed**. La vista è `security_invoker` e filtra
sullo scope emittente letto da GUC; il canale di **sistema** quelle GUC non le
imposta, e `SUPER_ADMIN` non è il valore che `app.ruolo_applicativo` si aspetta.
Le righe si sono viste solo con un contesto **OPERATORE** e un utente davvero
mappato sull'emittente giusto (`pk 32` → `sr 72`). ⚠️ La ricetta era già scritta
nel §8 di questo brief — e l'ho ritrovata sbagliando prima.

---

## 14. R-3 — il registro che si scriveva e non si leggeva (2026-08-28)

⭐ **Non era in programma: l'ha trovato il collaudo.** Tid annulla `PRV0000133`
per la prova 10.1, la riga di commessa passa ad `ANNULLATA` come deve, e chiede:
*«non mi sembra di vedere il motivo».*

### 14.1 Il fatto

`vendite.commesse_attivita_log` **non aveva un solo `SELECT` in tutto il
backend.** Nessuna rotta, nessun pannello, nessuna tab. **Sei** tipi di evento
scritti fedelmente dal database e **irraggiungibili** da qualunque schermata:

`ONERE_AGGIUNTO` · `RIGA_MANUALE_ANNULLATA` · `RIGA_RITIRATA_DA_SORGENTE` ·
`RIGA_RIPORTATA_DA_EMETTERE` · `ACCREDITO_RICHIESTO` · `ACCREDITO_ANNULLATO`

🔴 **E la §7.7 della guida prometteva il contrario** — *«ogni riga ritirata lascia
la sua traccia nel registro della commessa, con il motivo»*. L'ho scritta io il
2026-08-27 fidandomi di ciò che il changeSet dichiarava, **senza chiedermi chi
lo legge**. Due giorni di promessa falsa, e l'operatore che scopre di non poter
distinguere «il lavoro è stato ritirato» da «il lavoro è sparito».

### 14.2 Cosa è stato fatto

| Pezzo | Dove |
| --- | --- |
| `CommesseRepository.list_registro_attivita` | `db/commesse_repository.py` |
| `fn_commessa_registro` + tetto di pagina | `services/commesse_service.py` |
| `ApiCommessaRegistro` · `GET commesse/<id>/registro/` | `api/views.py` + `urls_v1.py` |
| `CommessaRegistroEventoRow` | `types.py` |
| `listCommessaRegistro` | `vendite/api/commesse.js` |
| `CommessaRegistroDialog.vue` + voce «Registro della riga» nel kebab | `vendite/components/` |
| `EVENTO_REGISTRO_COMMESSA_MAP` + `eventoRegistroCommessaStyle` | `core/utils/severity.js` |
| 6 etichette evento + 5 chiavi pannello, it/en | `locales/` |
| **8 test** | `tests/db/test_commessa_registro.py` |

### 14.3 ⛔ Lo scope sta sulla RIGA, non sul log

`vendite.commesse_attivita_log` **non ha row level security**;
`vendite.commesse_attivita` sì. Leggere il log da solo sarebbe **fail-open**: si
vedrebbero i motivi di commesse fuori perimetro, in chiaro.

Il `JOIN` su `ca` non è una decorazione per prendere due colonne — **è il
cancello** — e vale anche per il **conteggio**: un totale calcolato senza
direbbe «12 eventi» mostrandone 3.

⚠️ **È la stessa lezione già pagata su `attivita_fatturabili`** col verbo
«Riporta da emettere» (§8 di questo brief). La seconda volta che la stessa forma
di fail-open si presenta in due settimane, su due tabelle diverse: non è un caso,
è come sono fatte le tabelle di appoggio di questo dominio — **quelle senza RLS
si leggono passando da quella che ce l'ha**.

⭐ Ed è il test che apre il file: `test_lo_scope_passa_dal_join_su_commesse_attivita`,
**provato rosso** togliendo il `JOIN`.

### 14.4 ⚠️ Il vocabolario è del database, e resta aperto

Sei eventi oggi. La query **non ne nomina nessuno** e non filtra: un evento nuovo
compare da sé. Il frontend risolve l'etichetta con `labelOrCode` e la coppia
severity/icona con un ripiego — un codice sconosciuto si **vede col proprio
nome** invece di sparire.

🔵 Un test lo presidia (`test_nessun_evento_e_nominato_nella_query`): se qualcuno
mettesse una whitelist nella query, diventa rosso.

### 14.5 ✅ Il BB estratto — `GiornaleEventi` (2026-08-28)

Il pannello era il **secondo «giornale»** dell'applicazione. Il primo è
`PraticaGiornaleTab.vue`, che portava scritto in testa *«componente riutilizzabile
— sarà usato anche da altri domini in futuro»*: stessa forma — timeline inversa,
tag per evento, chi/quando in testata, riga di dettaglio, ripiego sul codice.

⭐ **Estratto in `core/components/GiornaleEventi.vue`** (regola del 2, ok Tid), e
i due consumatori ci poggiano sopra. `PraticaGiornaleTab` passa da **161 a 91
righe**.

| Cosa resta al dominio | Cosa passa al BB |
| --- | --- |
| la **fetch** (rotta, parametri, stato di caricamento) | la resa: voce, tag, icona, «quando», dettaglio |
| `etichetta(codice)` — la frase leggibile | il ripiego quando manca |
| `stile(codice)` — severity + icona | il default sui codici sconosciuti |
| `dettaglio(evento)` — la riga sotto | la decisione se mostrarla |

⛔ **Il BB è presentazionale e basta**: non conosce rotte, non fa fetch, non sa di
quale dominio mostra la storia. Le tre decisioni arrivano come **funzioni** —
metterle dentro avrebbe voluto dire una mappa di tutti i domini in un componente
di `core/`, cioè il contrario di un BB.

⚠️ **Due dettagli che sarebbero stati facili da sbagliare:**

* **`campo-codice`**, perché il codice dell'evento si chiama diversamente nei due
  domini (`azione` per le pratiche, `evento` per le commesse). Rinominarne uno
  sarebbe stato un **cambio di contratto d'API per far tornare un nome di
  componente**.
* **`caricato` con default `true`**, che è esattamente ciò che il primo
  consumatore faceva prima: l'estrazione **non cambia il comportamento delle
  pratiche**. Chi lo passa (le commesse) distingue «non c'è niente» da «non lo
  sappiamo ancora» — un empty-state positivo su una fetch mai riuscita afferma
  il falso.

ℹ️ Registrato nel [catalogo BB frontend](../frontend/catalogo-building-block-frontend.md),
che è la prima difesa contro la terza copia.

---

## 15. Offerte — il rientro del padre, e cosa tocca a noi (2026-08-28)

Il team DB ha chiuso le **due voci** che questo brief teneva in custodia per
conto loro (§ tabella in testa). La prima non ci riguarda; la seconda **cambia il
modello**, e una parte è nostra.

### 15.1 ✅ Le tre voci che ci vengono rielencate erano GIÀ FATTE

Il loro messaggio ripropone **BE-1**, **BE-2** e **FE-1** come da fare: è il
testo del brief precedente, scritto prima di vedere il nostro lavoro. Sono state
consegnate il **2026-08-28 al mattino** e verificate sul DB vero (§ il §7 del
loro brief archiviato porta la prova):

| | Stato |
| --- | --- |
| **BE-1** — `v.is_superata IS FALSE` nei due repository, `solo_attiva` → `solo_ultima_revisione` | ✅ fatto (70 occorrenze, 13 file) |
| **BE-2** — `get_preventivo` legge `has_next_revisione` dalla vista | ✅ fatto |
| **FE-1** — il banner del drawer legge `is_superata` | ✅ fatto, col readonly motivato dallo **stato** e non dal superamento |

⭐ E il filtro «Annullato» **non è più vuoto**: da 0 per costruzione a 17.

### 15.2 ⏸️ Il codice errore nuovo — l'unica cosa in attesa

`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` (`CONFLITTO_STATO` → 409) è **già a
catalogo nel database locale**, insieme al trigger di rientro e alla transizione
`SUPERATA → EMESSA`. ⛔ **Ma i changeSet non sono ancora in git**: il merge è su
`Tito-dev` e non è arrivato qui.

⚠️ **Perché il ripiego non si può scrivere adesso.** Il presidio
`test_error_policies_classi` lega ripiego e policy **nei due versi**: un ripiego
senza il codice in `CLASSE_PER_CODICE` fa **rosso** (`test_nessun_messaggio_orfano`),
e `CLASSE_PER_CODICE` è **generato dal database**. Rigenerarlo ora vorrebbe dire
scrivere nel repo uno stato che il repo non ha — la regola è **mai rigenerare col
DB avanti rispetto a git**.

➡️ **Appena il merge arriva**: `genera_error_policies` + la frase di ripiego,
senza segnaposto. Il testo è pronto:

> *«L'offerta non può uscire dal superamento: esiste ancora una revisione viva su
> questo documento. Va prima annullata quella.»*

### 15.3 ✅ Tre dichiarazioni diventate false — corrette

`SUPERATA` **non è più uno stato senza uscite**: ne ha una, `SUPERATA → EMESSA`,
percorsa dal database da sé e seedata `manuale: false` — quindi nessuna azione,
nessun pulsante, nessun cambiamento per chi guarda.

⛔ **Ma tre punti del codice lo dichiaravano terminale «senza transizioni
uscenti»**, ed erano veri fino a ieri:

| Dove | Cosa diceva | Nota |
| --- | --- | --- |
| `offerte_service._STATI_TERMINALI` | *«no editing, no transizioni uscenti»* | 🔴 **ed è una costante MORTA**: definita e mai letta in tutto il backend. Non l'ho cancellata — è di chi possiede le offerte — ma una costante morta che dichiara anche il falso è il peggio dei due casi |
| `offerte/constants.js` | *«stati terminali (workflow morto)»* | il comportamento resta giusto (severity `warn`), cambia il **perché** |
| `OffertaDrawer.vue` | *«terminali, non puoi più fare nulla»* | vero per l'**operatore**, non più per il **documento** |

⭐ **Nessun comportamento è stato cambiato**: solo le frasi che avevano smesso di
essere vere. È la stessa specie di difetto che questo cantiere insegue da tre
giorni — e stavolta è arrivata da un cambio del modello fatto da altri, che è il
modo in cui si formano quasi sempre.

### 15.4 ℹ️ Cosa NON tocca a noi

* il guard sull'**arità** del `SELECT INTO` — DB, e nessun impatto applicativo;
* `data_emissione` non riscritta dal rientro (`COALESCE`) — DB. ⭐ Vale la pena
  notarlo lo stesso: è la stessa specie di difetto dei nostri, *un valore che si
  sovrascrive perché nessuno si è chiesto se quel campo aveva già un significato*.

