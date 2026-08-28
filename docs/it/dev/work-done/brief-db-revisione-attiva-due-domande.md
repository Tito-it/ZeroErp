# Brief DB — `is_attiva` risponde a due domande con un flag solo: separarle

> **Destinatario:** team DB (`dev/db-tid`), con due richieste al BE e una al FE (§7).
>
> **Origine.** Collaudo in-app di Tid del **2026-08-28**, «Riporta da emettere»:
> provando l'annullamento di `PRV0000133` il documento **sparisce dalla lista** e
> non lo riporta a galla nessun filtro di stato. Il collaudo
> ([collaudo-in-app-riporta-da-emettere.md](collaudo-in-app-riporta-da-emettere.md))
> dice esplicitamente che un difetto trovato lì va guardato **dove appartiene**:
> questo non riguarda il verbo, la card o la lista dei residui, quindi apre un
> cantiere suo.
>
> **Stato.** 2026-08-28 — analisi sulla **struttura** (definizioni vive delle tre
> viste dalla doc auto-gen, colonne di `config.stati_doc_*`, corpo del trigger di
> revisione, filtri dei due repository BE, predicato del drawer FE).
>
> ✅ **DB CHIUSO in giornata.** I quattro changeSet (`20260828-07` … `-10`) sono
> stati **applicati da Tid** il 2026-08-28, doc auto-gen rigenerata, pgTAP nuovi e
> preesistenti verdi, **nessuna regressione**. Restano fuori BE-1, BE-2 e FE-1
> (§7): finché il repository filtra su `is_attiva`, il difetto **si vede ancora in
> interfaccia** — il DB ora espone il predicato giusto, ma nessuno lo chiede.
>
> ⭐ **Non è una richiesta di ristrutturare le revisioni.** Il meccanismo che
> nasconde le revisioni superate funziona ed è quello che il toggle dichiara di
> fare. Il difetto è che a quel meccanismo se n'è aggiunto un secondo, dentro lo
> stesso flag, **senza un nome suo**.

---

## 0. Le voci in una riga

| # | Voce | Dove | Stato |
| --- | --- | --- | --- |
| **D1** | `vw_preventivi.is_attiva` risponde a due domande in AND: non sono separabili a valle | `vendite.vw_preventivi` | 🛠️ §5.2 |
| **D2** | Idem sulle offerte, scritto come letterale `NOT IN ('SUPERATA','ANNULLATA')` | `vendite.vw_offerte_commerciali_lista` | 🛠️ §5.1 + §5.4 |
| **D3** | Metà del predicato delle offerte (`ANNULLATA`) è **già** dichiarato a catalogo come `is_abortito`, e la vista lo ignora: due sedi per lo stesso fatto | `config.stati_doc_offerte` | 🛠️ §5.4 |
| **D4** | `has_next_revision` è calcolata a mano nel backend: stessa logica in due posti, uno fuori dal DB | `preventivi_repository.get_preventivo` | 🛠️ §5.2 + §7 BE-2 |
| **BE-1** | Il toggle «Mostra storico revisioni» deve passare a `is_superata`, non a `is_attiva` | `preventivi_repository`, `offerte_repository` | 📩 §7 |
| **FE-1** | `PreventiviDrawer.vue` legge `!is_attiva` come «revisione superata»: su un annullato è una frase falsa | `frontend/src/vendite/preventivi/` | 📩 §7 |
| **A1** | Il gemello acquisti, ancora da costruire, eredita il difetto se nasce com'è scritto oggi | `sviluppo-preventivi-acquisti.md` §9.2 | ✅ doc corretta |
| **N1** | Listini: **non** affetti — il versionamento non ha nessun flag composto | `vendite.listini_versioni` | ✅ §8.3 |

> ✅ **D1–D4 applicati** (Tid, 2026-08-28). ⚠️ **BE-1 / BE-2 / FE-1 sono ciò che
> tiene aperto il cantiere**: il DB espone `is_superata`, ma la lista continua a
> filtrare `is_attiva` — cioè `PRV0000133` **sparisce ancora**. Una colonna che
> nessuno legge non ha corretto niente.

---

## 1. Il fatto, letto dal contratto

`vendite.vw_preventivi.is_attiva`, definizione viva (changeSet `20260708-07`):

```sql
   NOT EXISTS (rev con stato is_abortito = TRUE  →  è questa)     -- (a)
AND NOT EXISTS (rev superiore con stato non abortito)             -- (b)
```

Sono **due predicati distinti** legati da un AND. Ognuno dei due risponde a una
domanda che ha senso da sola:

| | Domanda | Predicato |
| --- | --- | --- |
| **(b)** | «è l'**ultima** revisione?» — nessuno l'ha rimpiazzata | il secondo `NOT EXISTS` |
| **(a)** | «**non** è annullata?» | il primo `NOT EXISTS` |

⛔ **Una congiunzione non si inverte.** Da `is_attiva = FALSE` non si può risalire
a *quale* dei due termini è falso: l'informazione è stata distrutta nel momento in
cui è stata composta. Chiunque legga la vista può chiedere solo la domanda
composta, mai una delle due.

L'offerta ha lo stesso difetto in un'altra forma
(`vw_offerte_commerciali_lista`):

```sql
sdo.codice_interno NOT IN ('SUPERATA', 'ANNULLATA')   AS is_attiva
```

`SUPERATA` è la domanda (b), `ANNULLATA` è la (a). Stessa congiunzione, stesso
vicolo cieco.

### 1.1 ⚠️ La misura del collaudo, come fatto datato

> **2026-08-28, DB di sviluppo**: 18 preventivi in stato `ANNULLATO` su 18 hanno
> `is_attiva = false`.

Questo numero **non è il motivo** del cantiere: è un controesempio che conferma
che il caso è raggiungibile. Il motivo sta sul modello ed è quello del §1 — un AND
non è invertibile, e la lista filtra su quell'AND. Reggerebbe identico con **un**
annullato, o con nessuno: uno stato che il modello ammette va potuto interrogare
anche quando oggi nessuna riga ci si trova. *Togli la misura e l'argomento resta
in piedi.*

---

## 2. ⛔ Perché non è «basta togliere il termine (a)»

È la correzione che viene in mente per prima, ed è sbagliata.

Il termine (a) — lo stato proprio — è stato aggiunto **di proposito** dal
changeSet `20260708-07`, per una ragione strutturale: senza, un annullato **in
cima** alla catena si auto-dichiarava attivo (il predicato guardava solo verso
l'alto), e per «rev0 EMESSO + rev1 ANNULLATO» risultavano attive **entrambe**.
L'unicità — *esattamente una revisione attiva per numero* — è una garanzia che i
cruscotti e i resolver di fatturazione usano.

✅ **`is_attiva` resta esattamente com'è**, formula e valori. Il difetto non è che
sbagli: è che **non esiste nessun'altra colonna** a cui chiedere una sola delle
due domande.

---

## 3. Dove il difetto si vede, e sono due posti

### 3.1 La lista: un filtro di stato vuoto per costruzione

`preventivi_repository.list_preventivi` applica `v.is_attiva IS TRUE` quando il
parametro `solo_attiva` è vero — che è il **default**. Un documento annullato ha
`is_attiva = FALSE` **per definizione** (termine (a)), quindi:

* il filtro di stato «Annullato» non può restituire **niente**. Mai. Non è un dato
  che manca: è il predicato di default che lo esclude prima che il filtro arrivi;
* il documento riappare **solo** togliendo il toggle «Mostra storico revisioni» —
  che però promette un'altra cosa. *Un documento annullato non è una revisione
  storica*: è l'ultima revisione del suo numero, e l'operatore l'ha appena chiusa.

Identico su `offerte_repository.list_offerte` (stesso parametro `solo_attiva`).

### 3.2 Il drawer: un banner che afferma il falso

`PreventiviDrawer.vue` calcola:

```js
const isSuperseded = computed(() => detail.value?.is_attiva === false)
```

e da lì deriva il readonly. Su un preventivo **annullato che è l'ultima revisione
del numero** nessuno l'ha superato: `is_superseded` è vero perché il flag è
composto, non perché esista una revisione successiva. È lo stesso difetto del §3.1
che esce da una seconda porta — e conferma che la sede della cura è la vista, non
il chiamante.

⚠️ Il commento sopra quel `computed` descrive correttamente il caso «rev0 EMESSO +
rev1 ANNULLATO», che infatti funziona. Il caso che non aveva guardato è
l'annullato **senza predecessore**.

---

## 4. La forma: le due domande prendono un nome

Su **entrambe** le famiglie le viste espongono, oltre a `is_attiva`:

| Colonna | Domanda | Preventivi | Offerte |
| --- | --- | --- | --- |
| `is_superata` | «qualcuno l'ha **rimpiazzata**?» | derivata: esiste una rev superiore non abortita | `stati_doc_offerte.is_superato` (stato `SUPERATA`) |
| `is_abortito` | «è stata **annullata**?» | `stati_doc_preventivi.is_abortito` | `stati_doc_offerte.is_abortito` |
| `has_next_revisione` | «qualcuno ha **provato** a revisionarla?» | esiste una rev superiore, qualunque stato | `EXISTS` figlio (c'era già) |

E:

```sql
is_attiva = NOT is_abortito AND NOT is_superata
```

⭐ **`is_attiva` è *derivata* dalle due componenti, non riscritta in parallelo.**
Nei preventivi un `CROSS JOIN LATERAL` calcola le tre `EXISTS` una volta sola e
`is_attiva` le compone. Così non può driftare da loro. Riscriverla a parte avrebbe
ricreato, *dentro la stessa vista*, il difetto che il cantiere sta togliendo: due
sedi per lo stesso fatto.

⭐ **«È l'ultima revisione?» è `is_superata IS FALSE`**, e da sola. È tutto ciò che
il cantiere doveva produrre.

### 4.1 ⚠️ `is_superata` e `has_next_revisione` non sono la stessa cosa

| Caso (preventivi) | `has_next_revisione` | `is_superata` | `is_attiva` |
| --- | --- | --- | --- |
| rev 0 EMESSO, rev 1 DRAFT | `TRUE` | `TRUE` | `FALSE` |
| rev 0 EMESSO, rev 1 ANNULLATO | `TRUE` | **`FALSE`** | `TRUE` |
| rev 0 ANNULLATO, unica | `FALSE` | **`FALSE`** | `FALSE` |

Una revisione abortita **non rimpiazza nessuno**: è ciò che regge il flusso «ho
sbagliato a revisionare, annullo e torno a operare sul predecessore». La terza riga
è `PRV0000133`.

---

## 5. Piano di sviluppo — quattro changeSet

Numerazione **globale per data**: il 2026-08-28 arrivava a `-06`.

### 5.1 `20260828-07` — `config.stati_doc_offerte.is_superato`

`00_schema/config/20260828-07-alter-stati-doc-offerte-add-is-superato-mctit.yaml`

`ALTER … ADD COLUMN is_superato BOOLEAN NOT NULL DEFAULT false` + backfill su
`codice_interno = 'SUPERATA'` (stessa forma del `20260714-05` che aveva aggiunto
`is_abortito`), e colonna aggiunta al CSV `80_data/sql/config/stati_doc_offerte.csv`
letto dal mirror `20260524-04` (`loadUpdateData`, `runOnChange`).

⚠️ Nessun nuovo loader: il seed si cambia **dal CSV**.

⚠️ **Il `columns:` del mirror non è stato toccato, ed è deliberato.** Quella lista
non elenca già oggi `fase`, `terminale` e `is_abortito`, che pure stanno nel CSV:
serve a fissare i *tipi*, non a decidere quali colonne entrano. In entrambe le
letture possibili l'esito è corretto — se il mirror carica anche le colonne non
elencate, `is_superato` arriva dal CSV; se le ignora, il valore resta quello messo
dal backfill del `20260828-07`, che gira **prima** (fase `00_schema`). Se un
giorno servisse forzarne il tipo, il precedente è nello stesso file (`pdf_mode` /
`pdf_allow_allegati`, 2026-07-11): il mirror è `runOnChange: true` +
`validCheckSums: ANY`, quindi ri-editarlo è il comportamento previsto.

### 5.2 `20260828-08` — `vendite.vw_preventivi`

Aggiunge `is_superata`, `is_abortito`, `has_next_revisione` **in coda** (un
`CREATE OR REPLACE VIEW` ammette solo l'append) e ricava `is_attiva` da loro.

⚠️ La lista colonne è **esplicita** al posto di `p.*`: se domani
`vendite.preventivi` guadagna una colonna, `p.*` la inserirebbe **prima** di
`is_attiva` e il `CREATE OR REPLACE` successivo fallirebbe.

### 5.3 `20260828-09` — `vendite.vw_preventivi_lista`

Propaga le tre colonne. Serve perché la lista **non legge `vw_preventivi`**: legge
questa, ed è qui che il repository applica il filtro. Una vista non propaga ciò che
non nomina.

### 5.4 `20260828-10` — `vendite.vw_offerte_commerciali_lista`

Espone `is_superata` (`= sdo.is_superato`) e `is_abortito`, e riscrive `is_attiva`
come `NOT is_superato AND NOT is_abortito`.

⚠️ **Nessun valore cambia**: `is_superato` è vero sul solo `SUPERATA`,
`is_abortito` sul solo `ANNULLATA` — esattamente l'insieme che il letterale
selezionava. Il pgTAP lo verifica **sul catalogo**, stato per stato (§6 della lista
test), non sui documenti di oggi.

### 5.5 pgTAP

✅ Entrambi verdi al 2026-08-28, insieme ai preesistenti che toccano lo stesso
dominio (`test-vw-dash-preventivi-revisione-attiva`,
`test-fn-crea-revisione-preventivo`, `test_offerte_commerciali_revisione_trigger`,
`test_fn_crea_revisione_offerta`, `test_offerte_commerciali_state_machine`).

| File | Cosa presidia |
| --- | --- |
| `db/pgtap/vendite/test-vw-preventivi-superata-vs-abortito-v1.sql` | 12 test: i tre scenari **costruiti** (annullato in cima, annullato unico, superamento vero), l'invariante di composizione, l'unicità di `is_attiva` invariata, la **non coincidenza dei due predicati**, e la propagazione alla vista di lista |
| `db/pgtap/vendite/offerte_commerciali/test-vw-offerte-lista-superata-vs-abortito.sql` | 11 test: seed di catalogo (`is_superato` sul solo `SUPERATA`), **equivalenza col vecchio letterale stato per stato**, i due scenari costruiti, la non coincidenza |

⚠️ Entrambi **fabbricano** i casi invece di cercarli fra i dati esistenti: su un DB
ricostruito da zero (CI) verificano le stesse cose. E in entrambi i conteggi sono
asseriti **insieme al numero di righe confrontate**, per non essere verdi per
sottrazione quando la RLS non fa vedere niente.

---

## 6. ⭐ Perché una colonna a catalogo, e non un letterale

Sul lato offerte il letterale `codice_interno = 'SUPERATA'` sarebbe **lecito**:
`linee-guida-sql` §6d lo ammette esplicitamente, perché `codice_interno` è la
chiave stabile (l'antipattern è il confronto contro `codice`). Quindi la scelta va
motivata, non data per ovvia.

**Tre ragioni, in ordine di peso:**

1. ⛔ **Metà del predicato era già dichiarata altrove.** `is_abortito` esiste dal
   `20260714-05` e vale `true` sul solo `ANNULLATA`. La vista lo ignorava e si
   ridichiarava la stessa cosa per conto suo: **due sedi per un fatto solo**, che
   possono divergere senza che nessun errore lo dica. Questa metà andava sanata a
   prescindere dal cantiere.
2. ⚠️ **Con il letterale, la vista sarebbe l'unico posto dove sta scritto *che
   cosa* significa `SUPERATA`.** Uno stato nuovo che volesse dire la stessa cosa
   non entrerebbe nel predicato, e il silenzio sarebbe totale. Con la colonna il
   significato sta dove stanno già `fase`, `esito`, `terminale` e `is_abortito`:
   nel catalogo che descrive gli stati.
3. ✅ **La vista smette di nominare stati.** Dopo il `20260828-10` non c'è più
   nessun `codice_interno` letterale nel calcolo dei flag di revisione, su nessuna
   delle due famiglie.

⚠️ **Non basta la proiezione di dominio.** `RIFIUTATA`, `SUPERATA` e `ANNULLATA`
hanno tutte e tre `fase = CHIUSO`, `esito = NEGATIVO`, `terminale = sì`: da lì i
due assi non si distinguono. Servono le due colonne.

### 6.1 Alternative valutate e scartate

* ⛔ **Togliere il termine (a) da `is_attiva`** → perde l'unicità, §2.
* ⛔ **Derivare `is_superata` delle offerte dalla relazione** (`EXISTS` figlio non
  abortito, come nei preventivi) → sanerebbe anche il limite noto del §8.2, ma
  farebbe divergere il flag dallo **stato persistito**: una riga in `SUPERATA` con
  `is_superata = false`. È ristrutturare le revisioni, che è fuori perimetro
  dichiarato.
* ⛔ **Un `is_superato` anche su `config.stati_doc_preventivi`** → non avrebbe
  nessuna riga da marcare: nei preventivi non esiste uno stato `SUPERATO`, il
  superamento è una relazione fra righe. Le due famiglie restano **diverse nel
  meccanismo e uguali in ciò che espongono**, ed è la cosa giusta.

---

## 7. 📩 Richieste al BE e al FE

> ⛔ Perimetro DB: `backend/` e `frontend/` non sono stati toccati. Qui c'è cosa
> serve e perché.

**BE-1 — il toggle dello storico cambia predicato** (`dev/backend-tid`).
In `preventivi_repository._build_filters` e `offerte_repository._build_offerte_filters`
il ramo `if solo_attiva:` deve diventare:

```python
conditions.append("v.is_superata IS FALSE")   # era: v.is_attiva IS TRUE
```

Motivo: il parametro si chiama `solo_attiva` ma il FE lo accende dal toggle
«Mostra storico revisioni», e quel toggle promette di nascondere le revisioni
**rimpiazzate**, non gli annullamenti. Con `is_attiva` il filtro di stato
«Annullato»/«Annullata» non può restituire nulla.
⚠️ Vale la pena rinominare il parametro in `solo_ultima_revisione`: il nome
`solo_attiva` è metà della ragione per cui il difetto non si vedeva.
⚠️ ⛔ **Non toccare** i cruscotti (`vw_dash_fatturazione_preventivi`): lì la
domanda è davvero «il documento è vivo e corrente», e `is_attiva` è il predicato
giusto. La distinzione è il punto del cantiere.

**BE-2 — smettere di ricalcolare `has_next_revision`** (`dev/backend-tid`).
`preventivi_repository.get_preventivo` contiene un `EXISTS` inline che duplica la
logica ora esposta come `has_next_revisione`. Va letta dalla vista. (Il nome
esposto all'API resta una scelta del BE; nel DB la colonna è in italiano come le
gemelle delle offerte.)

**FE-1 — il banner «revisione superata»** (`dev/backend-tid` / frontend).
`PreventiviDrawer.vue` deve calcolare `isSuperseded` da `is_superata`, non da
`!is_attiva`. Serve che il dettaglio esponga il campo (BE).
⚠️ Il **readonly** è un'altra decisione: un annullato va probabilmente in readonly
lo stesso, ma per il suo stato terminale, non perché «superato». Sono due
motivazioni diverse e vanno scritte come tali — un motivo sbagliato che produce
l'effetto giusto è comunque un motivo sbagliato.

---

## 8. Le famiglie vicine — cosa è affetto e cosa no

### 8.1 🟠 Preventivi di acquisto: il gemello non ancora nato

`sviluppo-preventivi-acquisti.md` §9.2 prescrive per `acquisti.vw_preventivi` il
predicato `is_attiva` **nella forma pre-`20260708-07`** (solo il termine (b)). Se
quel gemello nascesse com'è scritto oggi erediterebbe il difetto — anzi due, perché
gli manca anche il self-term che ripristina l'unicità.
✅ Il §9.2 è stato aggiornato con la forma a tre colonne. Non c'è codice da
correggere: la tabella non esiste ancora.

### 8.2 ⚠️ Offerte, il limite noto che **resta**

Se l'ultima revisione di un lineage viene annullata **senza successore**, il padre
resta `SUPERATA` e nessuna offerta del lineage risulta attiva: lo stato non
rifluisce all'indietro. Era già documentato come limite del modello a trigger, ed è
**invariato** — qui `is_superata` continua a dire ciò che il modello ha scritto.
La cura è §6.1, seconda voce, e non appartiene a questo cantiere.

⚠️ Nel frattempo, un rilievo trovato leggendo il trigger:
`vendite.trgfn_offerte_commerciali_revisione` fa `SELECT id INTO v_stato_superata_id
… WHERE codice_interno = 'SUPERATA'` **senza guard sul non-trovato**. Se quello
stato mancasse, la variabile resterebbe `NULL` e l'`UPDATE` scriverebbe `NULL` su
una colonna `NOT NULL`: l'errore arriverebbe, ma con la frase sbagliata. È un
rilievo aperto, non toccato qui.

### 8.3 ✅ Listini: **non** affetti

`vendite.listini_versioni` non ha nessun flag composto. Il versionamento è
modellato per intero con colonne separate:

* `stato` (`BOZZA` / `ATTIVA` / `CHIUSA`) — il ciclo di vita, con guard sulle
  transizioni;
* `attivo` — il ritiro;
* `validita` (`daterange`) + `EXCLUDE ex_listini_versioni_no_overlap` — «qual è la
  versione corrente» è una domanda **temporale**, risolta da un lookup, non da un
  booleano.

Le due domande di questo cantiere lì sono già distinte, e sono tre. **Niente da
fare.**
⚠️ Esiste un rilievo *diverso* già documentato su questa famiglia (una versione
scaduta resta `stato = ATTIVA` finché non gira il job di chiusura, quindi un badge
UI basato sul solo `stato` mente per una finestra): è un problema di
**sincronizzazione temporale**, non di flag composto, e ha sede sua.

### 8.4 ✅ Contratti e ordini: nessuna revisione

`vw_contratti_lista` e `vw_ordini_lista` non espongono `is_attiva` né colonne di
revisione: quei documenti non hanno il concetto. Niente da fare.

---

## 9. Come si collauda (in app, dopo l'apply e BE-1)

1. **Il filtro di stato smette di essere vuoto.** Lista preventivi, toggle
   «Mostra storico revisioni» **spento**, filtro stato = «Annullato» → deve
   comparire `PRV0000133`. Prima non compariva mai.
2. **Lo storico continua a nascondere ciò che deve.** Un numero con due revisioni
   vive (rev0 superata da rev1) → col toggle spento si vede **solo** rev1. È il
   comportamento che già funzionava e non deve cambiare.
3. **Il ritorno al predecessore.** rev0 EMESSO + rev1 ANNULLATO → col toggle spento
   si vedono **entrambe**: rev0 perché è la viva, rev1 perché è l'ultima revisione
   e non l'ha rimpiazzata nessuno. ⚠️ È un **cambio visibile** rispetto a oggi, ed
   è quello richiesto: prima rev1 spariva senza appello.
4. **I cruscotti non si muovono.** «Riporta da emettere» e il backlog preventivi
   devono mostrare esattamente le stesse righe di prima: girano su `is_attiva`, che
   non è cambiata.
5. **Offerte, stesso giro** con `ANNULLATA` al posto di `ANNULLATO`.

---

## 10. Cosa NON serve

* ⛔ Nessun trigger, nessuna colonna persistita: tutto resta **derivato**. Un flag
  scritto è la cosa che questo dominio ha già tolto una volta
  (`is_revision_attiva`, droppata dal `20260515-05`) proprio perché driftava.
* ⛔ Nessuna riga nel catalogo liste (`ui.lista_colonna`): i tre flag sono
  predicati del repository, non colonne mostrate all'operatore. Se un giorno
  servisse una colonna «superata» in lista, si aggiunge lì — è un'altra decisione.
* ⛔ Nessun codice errore nuovo: non c'è niente da sollevare, è una vista che
  espone di più.
