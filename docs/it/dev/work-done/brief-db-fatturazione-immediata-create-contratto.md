# Brief DB — `fatturazione_immediata` nella whitelist di `fn_create_contratto`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid ·
> **Stato**: ✅ **CHIUSO** (2026-07-28) — DB (changeset `20260727-40`, pgTAP
> 12/12, doc auto-gen rigenerata in `1f8759d3d`) + BE/FE (difetto §3 corretto,
> checklist §5 applicata, 3 guardrail, 14 test nuovi). Decisioni §6 entrambe
> prese ·
> **Fuori perimetro, tracciato**: la variante *fail-loud* della fn madre (§6a)
> resta una proposta del team DB; la validazione a schermo è routine di
> rilascio.
>
> **Origine**: [brief-be-fe-emissione-fattura-mirata.md](brief-be-fe-emissione-fattura-mirata.md)
> step BE-6 (deviazione 1) · Fase B di
> [brief-db-emissione-fattura-per-documento-sorgente.md](../work-in-progress/brief-db-emissione-fattura-per-documento-sorgente.md).

---

## 1. Il fatto

La Fase B ha aggiunto `fatturazione_immediata` su `vendite.ordini`,
`vendite.contratti`, `vendite.ddt`. Ordini e DDT si creano con un `INSERT`
costruito lato BE, quindi la colonna è arrivata subito.

Il contratto no: si crea con la funzione madre `vendite.fn_create_contratto`,
che costruisce l'INSERT **da una whitelist sua**:

```sql
v_testata_allowed text[] := ARRAY[
    'billing_account_id', 'emittente_fiscale_id', 'istanza_utility_id',
    'utility_id', 'ambito', 'valido_dal', 'valido_al',
    'parent_contratto_id', 'data', 'listino_id',
    'tipo_variazione_globale', 'valore_variazione_globale',
    'categoria_cliente_id_snapshot', 'valuta_id', 'meta'
];
```

`fatturazione_immediata` non c'è. Una chiave fuori whitelist **non produce
errore**: viene semplicemente ignorata dal `jsonb_object_keys ... WHERE key =
ANY(...)`. Passarla dal BE significherebbe quindi **scartarla in silenzio** — il
campo sembrerebbe funzionare e non farebbe nulla.

## 2. Cosa serve

Aggiungere `'fatturazione_immediata'` a `v_testata_allowed` in
`vendite.fn_create_contratto`. Nient'altro: l'INSERT è già generico
(`jsonb_populate_record`), la colonna esiste, il default `false` resta per le
chiamate che non la passano.

Firma e `RETURNS TABLE` invariati → `CREATE OR REPLACE` puro, nessun `DROP`.

## 3. ⚠️ Perché non è bloccante — e cosa invece lo è

**Non è bloccante** perché la corsia si può decidere anche dopo la creazione,
con la PATCH in DRAFT: la scelta va fatta **prima del push in commessa**, e in
DRAFT il contratto non è ancora pushabile (`fn_list_contratti_da_pushare` filtra
lo stato `ATTIVO`). Senza questa modifica resta solo un salto in più
nell'esperienza: crea, riapri, spunta.

> ⚠️ **Correzione rispetto alla prima stesura di questo brief.** Diceva che «il
> caso d'uso è coperto per intero dalla PATCH». **Oggi non lo è**, per un
> difetto lato BE — non lato DB. Verificato su `dev/backend-tid` (`5f1c223bc`).

**Il difetto BE.** Sui contratti la catena della PATCH ha quattro anelli e ne
sono stati cablati tre:

| Anello | Stato |
|---|---|
| whitelist `_UPDATE_KEYS_TESTATA` (`contratti_service.py`) | ✅ contiene il flag |
| gate per stato — `_CONTRATTO_PATCH_ALLOWED_BY_STATE["DRAFT"]` | ✅ eredita dalla whitelist |
| **mapper `_build_update_data_testata`** | ❌ **non legge mai la chiave** |
| `write_cols` di `contratti_repository.update_contratto` | ✅ esteso |

Il mapper copia in `data` campo per campo, esplicitamente, e il flag non è tra
quelli; `data` è l'unica cosa che arriva al repository. Risultato: la colonna
aggiunta a `write_cols` è irraggiungibile.

Il sintomo dipende dal payload, e il caso reale è quello silenzioso:

- PATCH con il **solo** flag → `data` vuoto → 400 *«Nessun campo aggiornabile
  presente nel payload»* (fuorviante, ma rumoroso);
- PATCH **dal drawer** → `buildPayload()` manda sempre anche `ambito`,
  `valido_dal`, `data`, `listino_id`… → `data` non è vuoto → **200, toast
  «contratto salvato», flag non persistito**.

Quindi oggi, dalla UI, la corsia del contratto **non è impostabile** e
l'operatore non ha modo di accorgersene.

**Perché è sfuggito**: contratti è l'unico dei tre documenti con un mapper
esplicito. Ordini e DDT usano una dict-comprehension generica sul payload, dove
aggiungere la chiave alla whitelist *è* sufficiente. Lo stesso gesto su tre file
ha dato due successi e un no-op. Nessun test copre il flag su
contratti/ordini/DDT.

**Il fix** (BE, `dev/backend-tid`, in `_build_update_data_testata`):

```python
if "fatturazione_immediata" in payload:
    data["fatturazione_immediata"] = bool(payload["fatturazione_immediata"])
```

più un test che verifichi la persistenza dopo la PATCH. Va fatto **a
prescindere** da questo brief e **prima**: è il vero blocco. `bool(...)` chiude
anche il caso del valore nullo (vedi C4).

## 4. Garanzie

| # | Deve essere vero | Copertura |
|---|---|---|
| C1 | Creando un contratto **con** `fatturazione_immediata: true` nel `p_testata`, la colonna risulta `true` a DB | pgTAP `test-fn-create-contratto-v1.sql` caso 11 |
| C2 | Creando **senza** la chiave, la colonna resta `false` (default) — nessuna regressione sulle create esistenti | idem, caso 10 |
| C4 | Con la chiave **presente e a `null`** la chiamata **fallisce** (NOT NULL, `23502`): mai un NULL scritto di nascosto né un `false` dedotto in silenzio | idem, caso 12 |
| C3 | Il guard `trgfn_guard_fatturazione_immediata_immutabile` continua a respingere l'UPDATE su contratto già pushato | **già coperto** da `test-fatturazione-immediata-simmetria-sorgenti-v1.sql` caso 15 — non si ritesta qui |

> **Su C3**: riguarda l'`UPDATE`, e il guard è armato `BEFORE UPDATE OF`. La
> create non lo tocca. Resta in tabella come promemoria del perimetro, non come
> test da scrivere.
>
> **Su C4 — differenza voluta, da conoscere.** Il filtro della whitelist è sulla
> **presenza** della chiave, non sul valore. Il repository degli ordini fa
> l'opposto (omette le colonne opzionali quando valgono `None`, «None = lascia il
> DEFAULT»): lì la stessa chiamata passerebbe. Qui si preferisce l'errore al
> silenzio — meglio fermarsi che lasciar decidere la corsia a un default
> nascosto. **Contratto per il BE: omettere la chiave oppure mandare un
> booleano, mai `null`.**

## 5. A valle — checklist, non «una riga»

Quando il changeset è applicato, i punti da toccare sono sei, e quattro sono
commenti che **diventano falsi** (un commento sbagliato è peggio di nessun
commento):

| # | Dove | Cosa |
|---|---|---|
| 1 | `contratti_service.py` `_CREATE_KEYS_TESTATA` | rimettere `"fatturazione_immediata"` |
| 2 | idem, commento ⚠️ sopra `valuta_id` | **rimuovere**: dice «la fn madre non contiene *ancora* la colonna». Attenzione: il blocco è stato inserito senza riga vuota prima del commento di `valuta_id`, che ora sembra farne parte — separarli |
| 3 | `ContrattoDrawer.vue` | togliere `v-if="isEdit"` dal blocco del campo |
| 4 | idem, `handleSave()` ramo create | togliere lo scorporo `const { fatturazione_immediata: _soloInPatch, ...campiCreate }` |
| 5 | idem, commento in `buildPayload()` | aggiornare: non è più «solo in PATCH» |
| 6 | idem, commento del blocco template | aggiornare: non è più «solo in modifica» |

⚠️ **Ordine di rilascio**: la riga 1 va rilasciata **dopo** che la migration è
applicata in tutti gli ambienti. Invertirli riporta lo scarto silenzioso, che è
esattamente ciò che questo brief evita.

## 6. Le due proposte emerse — entrambe chiuse (2026-07-28)

Erano fuori dal perimetro del brief perché cambierebbero comportamento oltre la
singola colonna. Chiuse entrambe: **6a** con un guardrail lato BE, **6b** con
una decisione di non fare — scritta qui col perché e con la condizione di
riapertura, così una revisione futura sa cosa rimettere in discussione e su
quale segnale.

**6a — ✅ CHIUSA lato BE (2026-07-28): guardrail scritto, su ENTRAMBE le whitelist.**

`ContrattiWhitelistCreateAllineataAlDbTests` confronta le whitelist BE con
quelle della fn madre lette dalla **doc auto-gen** — che riflette l'oggetto
vivo, gira senza DB (CI-safe) ed è la fonte prevista dalla regola di casa.
Verifica nei due sensi: chiavi BE ignote al DB (scarto silenzioso, il caso
grave) e chiavi DB non esposte dal BE (capacità irraggiungibile).

| Whitelist BE | Whitelist DB |
|---|---|
| `_CREATE_KEYS_TESTATA` meno `utility` (sotto-entità) | `v_testata_allowed` |
| `_UTILITY_CREATE_KEYS` più `istanza_utility_id`/`utility_id` (iniettate dal service, non dal payload) | `v_util_allowed` |

⚠️ **La seconda riga è stata aggiunta dopo una domanda di Tid** («sicuro che il
fail-loud non sia già fatto?»). Verificando si è visto che no, non lo è — ma
soprattutto che **`p_utility` ha la stessa identica struttura fail-open della
testata**, e non era presidiata da nessuno. Stessa trappola, un livello sotto:
presidiata ora, non perché sia già successo ma perché è il meccanismo che è già
costato un giro sulla testata.

Entrambi i guardrail sono stati provati aggiungendo una chiave finta: **entrambi
falliscono**, e con il messaggio giusto.

> Reperto minore: alla prima stesura il guardrail utility era rosso su
> `param_1_num`/`param_2_txt`. Non era una divergenza reale — era la regex del
> test, `[a-z_]+`, che non copre le cifre. Corretta in `[a-z0-9_]+`.
>
> ⚠️ **Correzione di un mio commento**: avevo scritto che una regex lossy
> avrebbe potuto produrre un falso VERDE nascondendo il problema. Non è così, e
> il team DB l'ha rilevato: il lato BE **non è parsato** (viene dal frozenset
> Python), quindi perdere chiavi nel parsing del lato DB può solo far crescere
> `be - db` → **falso rosso sul caso grave, mai falso verde**. Era il modo
> sicuro di sbagliare. Conseguenza pratica: la regex **non va irrobustita
> oltre**.

**Limite del guardrail, scritto nel docstring**: è vero quanto l'ultima
rigenerazione della doc auto-gen. Non confronta il BE con il *database* ma con
un *documento*: se la fn madre cambia e la doc non viene rigenerata, il
confronto avviene contro una definizione stale e il test può restare verde
mentre il DB diverge. La rigenerazione fa parte del rilascio di ogni changeset
che tocchi la funzione — il presidio la presuppone, non la sostituisce.

### 6a-bis — il guardrail che mancava davvero: la catena di UPDATE ✅

Indicato dal team DB come «il solo guardrail da aggiungere, se se ne aggiunge
uno», e hanno ragione: **il difetto del 2026-07-27 non è nato sulla create ma
sull'update**, dove l'allineamento è a tre e l'anello di mezzo non era
presidiato da nulla.

```
_UPDATE_KEYS_TESTATA  →  _build_update_data_testata  →  _UPDATE_WRITE_COLS
(cosa si accetta)        (cosa si mappa)                (cosa si scrive)
```

Basta che una colonna manchi in **uno solo** dei tre e l'UPDATE non la scrive,
senza un fiato. È stato corretto a mano, e a mano si sarebbe ripetuto.

`ContrattiCatenaUpdateTests`, 3 casi:

| # | Anello | Cosa verifica |
|---|---|---|
| 1 | — | ogni chiave della whitelist ha un **campione** nel test: è il gancio che costringe a passare di qui quando si allarga la whitelist |
| 2 ⭐ | 1 → 2 | ogni chiave **attraversa il mapper** e arriva al repository, una alla volta, dal service pubblico |
| 3 | 1 ↔ 3 | ciò che si accetta è esattamente ciò che si sa scrivere |

Il caso 2 è quello che sarebbe stato rosso sul difetto reale. Verificato
simulando entrambi i modi di romperlo — mapper che perde la chiave, e chiave
nuova in whitelist senza campione: **entrambi rilevati**.

Ha richiesto una modifica minima al repository: `write_cols` era una tupla
**locale** dentro `update_contratto`, quindi il terzo anello non era
ispezionabile da nessun test. Promossa a costante di classe
`_UPDATE_WRITE_COLS`, nessun cambio di comportamento.

⚠️ **Perimetro**: copre la testata del **contratto**. Ordini e DDT hanno mapper
generici (dict-comprehension), dove la whitelist è già l'unico anello — per loro
il rischio non esiste nella stessa forma.

---

La seconda proposta — rendere la fn madre **fail-loud** — **resta aperta e resta
del team DB**: cambia il comportamento di tutte le chiavi di una madre già in
uso (e la stessa forma vale per `p_utility`), mentre il guardrail intercetta
comunque la divergenza nel momento in cui nasce, a rischio zero.

~~**6a — La whitelist resta «fail-open».**~~ Una chiave ignota è ancora scartata in
silenzio: fra un anno, alla colonna successiva, si ripete identico. Due rimedi
possibili, in ordine di costo:

- un test che confronti `_CREATE_KEYS_TESTATA` (meno `utility`, che è
  sotto-entità) con `v_testata_allowed`: fallisce nel momento in cui le due
  liste divergono, che è l'unico momento utile;
- rendere `fn_create_contratto` fail-loud sulle chiavi non whitelisted. Più
  pulito, ma cambia il comportamento di **tutte** le chiavi di una madre già in
  uso: da decidere, non da fare di slancio.

È la stessa filosofia del guard `20260727-08` («meglio una regola scritta che una
disciplina affidata alle persone»), applicata al livello sopra.

**6b — ✅ DECISA (Tid, 2026-07-28): la finestra `ATTIVO` NON si apre.**

### Il vuoto, descritto per bene

Il flag conta solo prima del push, e il push parte da `ATTIVO`
(`fn_list_contratti_da_pushare` filtra quello stato). In `ATTIVO` la PATCH
ammette solo `valido_al` e `meta`. Quindi:

| Momento del contratto | Il DB lascia cambiare il flag? | Il BE? |
|---|---|---|
| `DRAFT` | sì (nessuna riga in `commesse_sorgenti`) | sì |
| `ATTIVO`, **non ancora pushato** | **sì** | **no** ← il vuoto |
| pushato in commessa | no (guard `20260727-08`) | no |

Il vuoto è reale: il DB ragiona sul **fatto** («esiste una riga in
`commesse_sorgenti`?»), il BE sullo **stato**, che del push è solo
un'approssimazione — e approssima per eccesso.

⚠️ **Non è una contraddizione con §B3** del brief principale («l'indicazione si
stabilisce prima che il lavoro entri in commessa»): in quella riga il lavoro in
commessa non c'è ancora. `ATTIVO` e `pushato` non sono la stessa cosa, ed è la
confusione fra i due che fa sembrare la questione un rimpallo fra DB e BE. Non
lo è: il brief DB metteva due strade sul tavolo senza sceglierne una.

### Perché si è deciso di NON aprire

1. **Il caso d'uso ha già una risposta, ed è migliore.** «Me ne accorgo dopo, e
   voglio fatturare subito quel lavoro» è coperto **interamente**
   dall'**emissione mirata** (Parte A di questa stessa slice): si seleziona il
   gruppo e si fattura, senza toccare la corsia. Aprire il flag darebbe due modi
   di ottenere la stessa cosa — cioè due posti dove decidere la stessa cosa, che
   è esattamente la ragione per cui **D-6** ha escluso il flag dai consumi.
2. **La regola «in `ATTIVO` si tocca solo `valido_al` e `meta`» non è un
   dettaglio**: è una disciplina dichiarata («per cambi sostanziali serve un
   nuovo contratto, eventualmente con `parent_contratto_id` — pattern
   audit-friendly»). Il flag decide su quale corsia fiscale finisce il lavoro:
   è un cambio sostanziale, non una rifinitura. Fargli un'eccezione apre una
   crepa in una regola netta, e la prossima eccezione si chiede più facilmente.
3. **La finestra è più stretta di quanto sembri.** `commesse_sorgenti` ha
   `UNIQUE` **globale** su `(sorgente_tipo_id, sorgente_uid)`: un contratto è
   legato a **una sola commessa per sempre**, e la corsia si fissa al **primo**
   push. Il vuoto quindi non riguarda «ogni mese di un contratto ricorrente» ma
   solo l'intervallo *attivazione → primo push*. Passato quello, il flag è
   inerte per costruzione e nessuna regola BE lo cambierebbe.
4. **Che il BE sia più restrittivo del DB non è un difetto.** Il guard DB è
   l'ultima linea e ragiona sul fatto; la regola BE è politica di dominio e può
   legittimamente essere più stretta. Difese a granularità diversa sono la
   norma, non un'incoerenza da sanare.

**Nessuna modifica al codice**: `_CONTRATTO_PATCH_ALLOWED_BY_STATE["ATTIVO"]`
resta `{valido_al, meta}`.

### Quando riaprire

Il caso che questa decisione **non** copre è diverso da quello discusso: non
«fattura subito questo lavoro» (risolto dalla mirata), ma «il **prossimo** push
di questo contratto deve partire sulla corsia veloce», su un contratto attivato
e non ancora pushato. Segnale concreto da tenere d'occhio: **operatori che
rifanno un contratto solo per cambiare la corsia**. Se succede più di
aneddoticamente, si riapre — e la strada è quella già individuata (flag in
whitelist `ATTIVO`, ultima parola al guard DB), non una nuova.

## 7. Registro

### 2026-07-28 · BE/FE — difetto chiuso, checklist applicata ✅

**Il difetto di §3 è confermato** e corretto. Verificato sul codice prima di
accettarlo: `_build_update_data_testata` copia campo per campo e la chiave non
era fra quelle. La diagnosi del brief era esatta, sintomo compreso.

**Un anello in più di quelli elencati.** La checklist §5 dava il punto 1
(«rimettere la chiave in `_CREATE_KEYS_TESTATA`») come sufficiente per la
create: non lo era. Anche **`_build_create_data_testata` è un mapper esplicito**
— stessa trappola, stesso file, dieci righe sopra. Con la sola whitelist la
create avrebbe ripetuto il no-op silenzioso della PATCH.

Per non lasciare la stessa trappola una terza volta, la lettura del flag è ora
**un metodo unico** `_apply_fatturazione_immediata(payload, data)` chiamato dai
due mapper: aggiungere un percorso senza accorgersene resta possibile, ma
almeno non ci sono due implementazioni da tenere allineate.

**Scostamento dal fix proposto.** §3 suggeriva
`data[...] = bool(payload["fatturazione_immediata"])`. Non l'ho usato:
`bool("false")` è `True`, quindi una stringa dal client avrebbe messo il
contratto sulla corsia veloce. Si usa `PayloadValidator.optional_bool`, che
rifiuta i non-booleani con un 400 parlante — è il validator già in uso in questo
service, e la disciplina «niente coercion silenziosa» è quella di casa.

**Il contratto C4 è rispettato in modo più stretto**: chiave assente *o* `null`
→ la chiave viene **omessa** dal dict, quindi la fn madre non la vede mai e
resta il `DEFAULT false`. Il BE non manda `null`, come richiesto.

**Difetto FE evitato togliendo il `v-if="isEdit"`**: il campo usava
`:disabled="isLocked(...)"` senza il guard `isEdit &&` che tutti gli altri campi
del drawer hanno. In creazione il blob capabilities non esiste, quindi `isLocked`
è `true` e il toggle sarebbe nato **disabilitato** — il campo appena sbloccato,
inutilizzabile. Allineato al pattern del file.

**Checklist §5**: 6/6 applicati (whitelist, i 4 commenti diventati falsi, gate
`isEdit` del template, scorporo in `handleSave`).

**Test — il buco segnalato in §3 («nessun test copre il flag») è chiuso**:

| Dominio | Casi |
|---|---|
| contratti | 6 — create con/senza/`null`, PATCH persiste, `false` è un valore non un'assenza, tipo non booleano rifiutato |
| ordini | 3 — create con/senza flag, PATCH persiste |
| DDT | 2 — create, PATCH persiste |

Verificato che i test **presidino davvero il difetto**: simulando la rimozione
della chiamata al mapper, 2 casi diventano rossi.

Totale `apps.vendite`: 1347 → **1358**, baseline invariata (17 fail + 84 error,
identici a HEAD). Build FE verde.

**Nota sull'ordine di rilascio (§5)**: rispettato — il changeset `20260727-40`
risulta EXECUTED prima della modifica BE, e l'ambiente è uno solo
([[project_no_produzione_solo_sviluppo]]).


### 2026-07-27 · Analisi critica del brief

Rilievi che hanno cambiato il documento: §3 poggiava su un fatto falso (il
difetto del mapper BE); mancava C4 (chiave nulla su colonna `NOT NULL`); §5
sottostimava i punti da toccare e non diceva nulla sull'ordine di rilascio; C3
era già coperto altrove. Aggiunte le due proposte aperte di §6.

### 2026-07-27 · DB sviluppato, applicato e verde ✅

| Oggetto | File |
|---|---|
| Changeset | `db/changelog/migrations_v2/20_code/vendite/20260727-40-update-fn-create-contratto-fatt-immediata-mctit.yaml` — EXECUTED 2026-07-27 23:55 |
| pgTAP | `db/pgtap/vendite/test-fn-create-contratto-v1.sql` — `plan(9)` → `plan(12)`, casi 10-12 = C2/C1/C4. **12/12 verde** |
| Baseline | riga rimossa da `db/pgtap/baseline-rossi.tsv` (rientro) |

`CREATE OR REPLACE` puro (firma e `RETURNS TABLE` invariati), `SECURITY INVOKER`
esplicito, rollback che ripristina la whitelist precedente. Corpo preso dalla doc
auto-gen, firma con `%TYPE` dal `20260707-12` (l'auto-gen li scioglie).

**Fixture riparato — il test era rosso da prima, e non per il codice.** Il file
era in `baseline-rossi.tsv` come `ERRORE_FIXTURE`: la precondizione cercava un
billing account **senza** dati precontrattuali, e non ne esistono più (42 BA su
42 ne hanno, verificato sul DB). Falliva quindi al caso 1 e abortiva l'intero
file — copertura reale zero, non parziale.

La riparazione non forza il dato: il trigger
`trgfn_contratti_snapshot_precontrattuali` non guarda il BA ma la coppia
`(istanza_utility_id, utility_id)` **del contratto**, che arriva dal payload. Il
fixture sceglie quindi la prima utility libera da precontrattuali per l'istanza
del BA, preferendo quella del BA stesso quando già lo è — il caso realistico
resta il primo candidato. La `CROSS JOIN LATERAL` scarta i BA per cui nessuna
utility è libera, così la coppia è garantita e non sperata.

Effetto collaterale utile: il file rientra dalla baseline dei rossi, che cala di
una riga (da 111 a 110).

### 2026-07-28 · Chiusura

Tutte le voci del perimetro sono chiuse. Consuntivo:

| | Prodotto |
|---|---|
| **DB** | changeset `20260727-40` (whitelist estesa), pgTAP `plan(9)`→`plan(12)` verde, fixture riparato, una riga rientrata dalla baseline dei rossi, doc auto-gen rigenerata (`1f8759d3d`) |
| **BE** | difetto del mapper corretto su **entrambi** i percorsi (update *e* create), lettura del flag estratta in un metodo unico, `write_cols` promossa a costante di classe per renderla ispezionabile |
| **FE** | campo disponibile anche in creazione, scorporo rimosso, 4 commenti diventati falsi aggiornati, guard `isEdit &&` sul `disabled` |
| **Guardrail** | 3 — whitelist create testata, whitelist create utility, **catena di update a tre anelli** |
| **Test** | 14 nuovi (6 contratti flag, 3 ordini, 2 DDT, 3 catena update) + 2 whitelist create; ognuno provato rompendo di proposito ciò che deve intercettare |
| **Baseline** | invariata: 17 fail + 84 error su `apps.vendite`, identici a HEAD |

**Cosa ha insegnato questo brief, al di là della colonna.** Lo stesso gesto —
«aggiungi la chiave alla whitelist» — su tre domini ha prodotto due successi e
un no-op silenzioso, perché il contratto è l'unico con mapper espliciti. Il
difetto non stava in nessuna delle due whitelist ma **fra** di esse, ed è per
questo che nessuna revisione delle liste lo avrebbe trovato. I guardrail nati
qui presidiano gli **spazi fra gli anelli**, non gli anelli.

### Resta fuori perimetro (tracciato, non dimenticato)

| Cosa | Di chi | Note |
|---|---|---|
| Variante **fail-loud** della fn madre (§6a) | team DB | Cambia il comportamento di tutte le chiavi di `p_testata` **e** `p_utility` di una madre già in uso. I due guardrail intercettano comunque la divergenza nel momento in cui nasce, a rischio zero |
| Riapertura di **§6b** | Tid | Solo sul segnale scritto in §6: operatori che rifanno un contratto per cambiare corsia |
| Validazione a schermo del campo sui tre domini | Tid | Routine di rilascio, non un residuo di progetto |
