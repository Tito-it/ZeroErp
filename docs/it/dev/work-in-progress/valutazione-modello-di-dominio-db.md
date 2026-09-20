# Valutazione del modello di dominio — la *forma* dei dati (lato DB)

> **Cos'è.** La valutazione del **modello di dominio** del database: **329
> tabelle** in dieci schemi (`vendite`, `acquisti`, `magazzino`, `pagamenti`,
> `pratiche`, `documenti`, `anagrafiche`, `catalogo`, `config`, `shop`), **4886
> colonne**, letto **dal solo repository** — le pagine autogenerate
> (`docs/it/dbzero/**`, prodotte da `scripts/gen_db_docs.py`) e i changeSet
> Liquibase (`db/changelog/**`). Misure datate **2026-09-20**.
>
> **Perché esiste.** [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> ha valutato lo strato DB sul **governo** (catalogo, policy, GRANT, fixture,
> copertura dei test) e parte di quelle voci ha generato lavoro chiuso. Questa
> guarda l'altra metà, che nessuno ha mai misurato: **la forma dei dati** —
> tipi, identità, puntatori, stati, vocabolari, ripetizioni fra padre e figlia.
> Le due valutazioni hanno **unità di misura diverse** e non vanno fuse: là si
> contano presidi e righe di registro, qui si contano colonne e dichiarazioni.
>
> **Come si legge.** §1 i tre limiti della misura (da leggere prima di citare un
> numero) · §2 i **fatti** (V-1…V-8), ognuno con l'effetto e la **destinazione** ·
> §3 le **opinioni** (O-1…O-4), in appendice e separate · §4 che cosa **non** è
> un difetto · §5 come si chiude.
>
> **⛔ Regola del documento.** Un fatto qui dentro non è un motivo per fare
> niente: è una riga di struttura con la sua data e la sua unità di misura.
> La decisione — accogliere o respingere — è di Tid, e una delle due strade è
> sempre «non si fa nulla, e si sappia perché».
>
> **Stato:** 🔵 nuova, **non** discussa con Tid.

---

## 1 · I tre limiti della misura

**1. Le pagine autogenerate perdono la forma dei tipi.** Il generatore legge
`information_schema.columns.data_type` (`scripts/gen_db_docs.py:119`), che **non
porta** la scala di un `numeric` né la lunghezza di una `varchar`. Prova:
`vendite/fatture_scadenze.md` legge `importo | numeric`, ma il changeSet lo
dichiara `numeric(18,6)`. ⇒ le misure di **scala e lunghezza** si prendono dai
changeSet, non dalle pagine — e il fatto V-1 nasce proprio da questa perdita.

**2. I conteggi sui changeSet sono *dichiarazioni*, non colonne.** Sommano tutte
le migrazioni, comprese quelle poi alterate o ritirate. Servono a dire *con che
grafia si scrive il modello*, non *com'è il database oggi*.

**3. È un'istantanea, e non sostituisce il DB vivo.** Dove il repo non basta il
fatto è marcato **«da rifinire con una query»**, con la query accanto: chi ha
accesso al database la esegue e chiude la voce.

---

## 2 · I fatti

### V-1 · La pagina più letta del modello non dice la forma di un numero né di una stringa

**Fatto.** Nelle pagine autogenerate, **167 colonne** di dominio si leggono
`numeric` senza che nulla dica se una scala ce l'hanno; **639** `character
varying` hanno perso la lunghezza; **159** `character` (i codici a lunghezza
fissa delle `anagrafiche`) hanno perso la loro `n`. Due colonne che il modello
tratta in modo diverso si leggono identiche: `vendite.fatture_scadenze.importo`
è `numeric(18,6)` e `pagamenti.vendite_contabili_righe.importo` è `numeric`
**senza scala** (`20260213-10`, il P-8).

**Effetto.** La pagina che il sito pubblica **non è un contratto sui tipi**, e
un difetto di forma non è visibile da lì: il P-8 è stato trovato *contro il
database*, non sulla documentazione. Chi legge le pagine crede di leggere il
modello.

**Dove va.** Una `SELECT` più larga nel generatore
(`numeric_precision`, `numeric_scale`, `character_maximum_length`, `udt_name`):
è il **generatore** che perde il dato, non il modello. Cantiere `docs`.

### V-2 · Due grafie per lo stesso tipo, e la scelta non è una regola

**Fatto** (dichiarazioni di tipo nei changeSet, tutte le migrazioni):
`text` **492**; `varchar(n)` in una quindicina di lunghezze diverse, accanto a
`character varying(50)` **29** e a `character varying` **nudo 12** — cioè
`varchar` e `character varying`, la stessa cosa, convivono. Sui numeri:
`numeric(18, 6)` **36** e `numeric(18,6)` **18** (stessa scala, due spaziature)
e **19** dichiarazioni di `numeric` **senza scala**.

**Effetto.** Chi legge un changeSet non sa se una differenza vuol dire qualcosa.
E il `numeric` nudo è la porta del P-8: un valore con quattordici decimali entra
in una colonna che *non* li dichiara, e il guard di capienza rifiuta poi un
importo che *era* lo spazio.

**Dove va.** Una riga di convenzione in `linee-guida-sql.md` §tipi **più un
guardrail sui changeSet** (dove il difetto nasce, non a valle), sullo stampo
della regola zero della lista lato frontend.

### V-3 · Il fuso orario: una convenzione nel dominio, un'altra nello schema `ui`

**Fatto.** Nel dominio **671** colonne `timestamp with time zone` contro **4**
`timestamp without time zone` (`config.parameters` e `config.parameter_overrides`,
`data_insert`/`data_update`). Fuori dal dominio la convenzione cambia: **tutto lo
schema `ui`** (`lista_*`, `dashboard_*`, `widget`) e alcune shadow dello `storico`
usano `timestamp without time zone` — e su entrambe le famiglie il default è
`now()`.

**Effetto.** Lo stesso `now()` finisce in colonne di due famiglie che **non si
confrontano senza conversione**, e chi legge due righe da due schemi non lo sa.
È il difetto che la §Nota di metodo chiama «un'asimmetria che si scopre scrivendo
una query», cioè nel momento peggiore.

**Dove va.** O si allinea (`alter column … type timestamptz`, un changeSet), o si
scrive per **una riga** che `ui` è un'eccezione e perché. **Decisione di Tid**,
non un cantiere: le due strade costano poco, ma vanno scelte.

### V-4 · Cinque modi per dire «questa riga è viva, e in che stato è»

**Fatto** (tabelle di dominio che portano la colonna): `attivo` **154**,
`validita` (daterange) **21**, `obsoleto_dal` **9**, `stato` (stringa) **12**,
più gli `stato_*_id` a catalogo. Il registro del debito
(`dbops.rls_perimetro_debito`) **non** le copre: guarda il perimetro RLS, non la
forma.

**Effetto.** La stessa domanda — *questa riga vale oggi?* — si pone con cinque
chiavi diverse, e chi scrive una vista, un export o un presidio deve saperlo
tabella per tabella. È il gemello «di dominio» di ciò che il perimetro RLS ha
risolto con un criterio: là un elenco a mano, qui cinque convenzioni.

**Dove va.** Un **censimento a criterio**: una vista che classifica *come* ogni
tabella dichiara la vita della riga (come `vw_rls_perimetro_scoperto` fa per il
perimetro). Da lì una decisione di forma — quante forme si ammettono (probabile
risposta: FK a catalogo per lo stato di processo, `validita` per l'anagrafica) e
quali si migrano. **Prima la mappa, poi il lavoro.**

### V-5 · `codice` e `codice_interno`: la regola c'è, e metà del vocabolario non la segue

**Fatto.** **62** tabelle di dominio hanno **entrambe** le colonne, **50** hanno
solo `codice`, **4** solo `codice_interno`. La regola del progetto
(`brief-naming-stato-codice-interno.md` + guardrail in CI) dice: `codice_interno`
**immutabile** per la logica, `codice` **mutabile** per il display — ed è nata da
bug reali (`WHERE codice = 'X'`).

**Effetto.** Nelle 50 tabelle con il solo `codice` la colonna immutabile **non
esiste**: se una di quelle è letta come chiave di logica, il difetto non è tolto,
è rimandato. Il guardrail cerca l'**uso** sbagliato, non l'**assenza** della sede
giusta — e non poteva trovarla.

**Dove va.** L'elenco delle 50 (una `SELECT` sul DB o sulle pagine), poi una
domanda secca: *quali di queste vengono lette come chiave?* Quelle diventano un
`codice_interno`; le altre restano display e si dichiarano tali.

### V-6 · Il nome uguale con il tipo diverso: 42 colonne

**Fatto.** Nei dieci schemi di dominio **42 nomi di colonna** compaiono con più
di un tipo. I casi grossi: `id` con **cinque** tipi (le PK delle 329 tabelle sono
`bigint` **228**, `integer` **62**, `character varying` **25**, `text` **6**,
`smallint` **4**, `uuid` **4**); `stato_id`, `stato_da_id`, `stato_a_id` con
**tre**; `descrizione` in tre grafie (`character`, `character varying`, `text`);
`codice` in due; `data_insert` in due (è V-3).

**Effetto.** È esattamente il difetto che il progetto ha già pagato su
`sorgente_uid` — *lo stesso nome che significava due cose* — e il solo pattern
`id`+`uid` (uuidv7) è presente su **22 tabelle su 329**: l'identità esterna non è
una convenzione, è un'abitudine.

**Dove va.** Nessun lavoro di massa: **una regola** — `id` è `bigint`, `uid` è
`uuid` dove serve un'identità esportabile, le eccezioni si dichiarano. Il
censimento dei 42 nomi è in questo documento e si aggiorna con lo stesso script.

### V-7 · I puntatori senza vincolo: 35 colonne `*_id` intere senza FK

**Fatto.** **35** colonne di dominio finiscono in `_id`, sono intere e **non**
hanno una FK nella loro tabella. I gruppi: i **polimorfi dichiarati**
(`target_riga_id` 9, `target_id` 3), gli **attraversamenti di schema**
(`auth_user_id` 11 verso `django`, `unita_organizzativa_id` 10, `pratica_id` 10),
le **coppie di transizione** (`stato_da_id`/`stato_a_id`, 24 colonne su
`transizioni_*`), e i **singoli da spiegare** (`uom_id` 10, `valuta_id` 2,
`sorgente_tipo_id` 2, `documento_id`, `documento_origine_id`).

**Effetto.** Dove il puntatore è polimorfo il progetto ha già la sua risposta (il
guard della sorgente polimorfa); dove **non** è dichiarato nulla, il puntatore
può restare appeso e nessun presidio lo dice. ⚠️ La misura è **grezza**: un `_id`
senza FK può essere legittimo, e alcune FK esistono verso oggetti che le pagine
non documentano (il ponte `django`). Va rifinita sul DB vivo:

```sql
-- le colonne *_id intere senza FK, sul database vivo
select c.table_schema, c.table_name, c.column_name
from information_schema.columns c
join information_schema.tables t
  on t.table_schema = c.table_schema and t.table_name = c.table_name
where c.table_schema = any(array['vendite','acquisti','magazzino','pagamenti',
      'pratiche','documenti','anagrafiche','catalogo','config','shop'])
  and c.column_name like '%\_id' escape '\'
  and c.data_type in ('bigint','integer','smallint')
  and not exists (select 1 from information_schema.table_constraints tc
                    join information_schema.key_column_usage k
                      on k.constraint_name = tc.constraint_name
                   where tc.table_schema = c.table_schema
                     and tc.table_name = c.table_name
                     and tc.constraint_type = 'FOREIGN KEY'
                     and k.column_name = c.column_name);
```

**Dove va.** La lista, con una domanda per riga: *polimorfa (e allora vuole il
suo guard) o manca la FK?*

### V-8 · La figlia ripete la chiave del padre, e non sempre c'è chi lo controlla

**Fatto.** Le coppie documento/righe condividono più di dieci colonne:
`vendite.ordini_righe` **11** colonne di `vendite.ordini` (fra cui
`stato_doc_ordine_id`, `sorgente_tipo_id`, `sorgente_uid`), `acquisti.ordini_righe`
**12**, `vendite.fatture_righe` **10**, `vendite.commesse_attivita` **10** (con
`competenza_dal/al`), `vendite.ddt_righe` **8**.

**Effetto.** La figlia porta una copia di un dato che il padre **può cambiare**:
lo stato di un ordine cambia, e la riga conserva il valore del giorno prima. Se
un guard non li tiene allineati la divergenza è silenziosa — ed è la classe di
difetto su cui il progetto ha già scritto *«una condizione scritta in tre posti
diverge, e diverge in silenzio»*. Alcune coppie il guard ce l'hanno
(`vendite.trgfn_lotto_fatture_guard_stato_coerente` esiste per un altro caso),
altre no: **quali** è la misura che manca.

**Dove va.** Una misura, non un lavoro: per ogni coppia, *esiste un trigger che
tiene la copia allineata?* Le coppie senza guard sono il lavoro; le altre sono
una risposta scritta.

---

## 3 · Appendice — le opinioni

> Queste **non sono fatti**: sono letture di chi ha scritto la valutazione, e
> ognuna sta in piedi solo con un «sì» di Tid. Accoglierle è un lavoro (piccolo,
> indicato); respingerle è **una riga** in questa sezione, non un silenzio: una
> valutazione senza esito esplicito è la premessa di un'altra valutazione uguale
> fra tre mesi.

### O-1 · Il modello non ha un «registro dei tipi», e senza quello V-2 e V-6 non si chiudono

Il progetto ha imparato a governare **cataloghi** (presidi, registri del debito,
liste) e non ha mai governato **tipi**: nessuna sede dice «un importo è
`numeric(18,6)`, un codice è `text`, una data-ora è `timestamptz`, un `id` è
`bigint`». Senza quella sede, ogni valutazione futura rimisurerà gli stessi 19
`numeric` nudi e le stesse 42 colonne omonime, e P-8 non sarà l'ultimo.

* **Se si accoglie**: una pagina di convenzioni + un guardrail che rifiuta la
  dichiarazione **nuova** fuori standard, sui changeSet. Costo: una pagina e un
  guardrail — la stessa forma della regola zero della lista, che ha funzionato.
* **Se si respinge**: si accetta che la forma dei dati non sia un contratto, e
  allora V-1 (la pagina che non dice la scala) smette di essere un problema e
  diventa una scelta. Va scritto, però.

### O-2 · La riga di `SELECT` che manca è la più preziosa che il repo possa aggiungere

V-1 costa una `SELECT` nel generatore. È l'intervento con il miglior rapporto
costo/effetto di tutto questo documento, perché non corregge un dato: **rende
visibile una classe di dati** — e la pagina autogenerata è ciò che le guide, il
sito e i nuovi arrivati leggono come modello.

* **Se si accoglie**: dopo il primo rigenero si sa **quante** colonne hanno una
  scala e quante no, con i nomi. Il P-8 di domani si trova leggendo, non
  sbattendo.
* **Se si respinge**: resta una documentazione che *sembra* dire i tipi e non li
  dice — che è peggio di una documentazione che tace.

### O-3 · `ui` con un'altra convenzione temporale è debito di forma mai votato

`ui` è metadato di presentazione, quindi «non conta» — ma è anche lo schema che
il frontend legge in ogni sessione, e le sue colonne di audit non si confrontano
con quelle del dominio senza conversione. Non è un difetto grave: è un difetto
**non deciso**, che è la categoria peggiore perché non si vede finché non fa
danno.

* **Se si accoglie**: un changeSet di allineamento (o, più onesto, una riga che
  dice perché `ui` è diverso e da oggi è un'eccezione **dichiarata**).
* **Se si respinge**: la domanda tornerà la prima volta che qualcuno unisce due
  registri, e tornerà nel formato «perché questa query dà risultati strani?».

### O-4 · Servono **due** documenti, non uno: governo e forma

`migliorie-generali-da-test-valutazione.md` ha 930 righe fra catalogo, policy,
GRANT, trigger e fixture: se ci si aggiunge la forma dei dati, il documento
diventa il posto dove nessuno trova niente. Le due cose hanno unità di misura
diverse (presidi/righe di registro contro colonne/dichiarazioni), destinatari
diversi e cicli diversi: il governo si misura a ogni cantiere, la forma cambia
quando cambia il modello.

* **Se si accoglie**: questo documento resta quello della forma, e il vecchio
  resta il registro del governo con le sue voci chiuse.
* **Se si respinge**: si riapre il vecchio e ci si scrive dentro, sapendo che fra
  tre mesi nessuno saprà più quale metà è aggiornata.

---

## 4 · Che cosa **non** è un difetto

Le voci qui sotto sembrano irregolarità e sono invece decisioni: stanno scritte
perché nessuno le riapra per errore.

* **`meta` jsonb su 238 tabelle**: è la convenzione, ed è rispettata. Le altre
  40 colonne `jsonb` sono casi dichiarati (`snapshot`, `handler_params`,
  `contesto_json`, `risultato`).
* **Il blocco di audit** (`tx_id`, `data_insert`, `user_insert`, `data_update`,
  `user_update`, `storicizza`): uniforme in tutto il dominio (671 `timestamptz`),
  ed è ciò che rende `storico` e `dbops.audit_log` possibili.
* **`character(n)` per i codici a lunghezza fissa delle anagrafiche** (CF, IBAN,
  CAP): è la forma **giusta**. Il difetto è che la pagina non dice `n` (V-1).
* **Le PK composite su `note` e `note_*`** (`target_tipo, id`): è la
  partizione dichiarata del building block note, non un errore di modello.
* **39 `boolean` nullable su 476**: dove il dominio ha davvero tre valori
  (sì / no / non applicabile) il terzo stato è informazione, non ambiguità. Da
  guardare caso per caso, **non** da normalizzare in massa.
* **I polimorfi dichiarati** (`sorgente_tipo_id` + `sorgente_uid`,
  `target_tipo` + `target_id`): sono la soluzione, non il problema — e hanno il
  loro guard (V-7).

---

## 5 · Come si chiude

1. **I fatti che si chiudono con una query** — V-3, V-5, V-7, V-8: chi le prende
   (team DB) esegue, annota il risultato **dentro la voce**, e la voce diventa
   una decisione (allineare / dichiarare / migrare / non fare).
2. **I fatti che sono decisioni di forma** — V-1 (`docs`), V-2 (`dbops`), V-4
   (decisione di Tid, poi eventuale migrazione), V-6 (una regola): se accolti,
   ognuno è **un brief piccolo**, con la sua destinazione già scritta qui sopra.
3. **Le opinioni** — restano tali finché non c'è un «sì». Accoglierle è un
   lavoro; respingerle è una riga in §3.
4. **Questo documento non si aggiorna a mano due volte**: la prossima
   valutazione della forma è un documento nuovo, con la sua data, e questo resta
   la fotografia del 2026-09-20.
