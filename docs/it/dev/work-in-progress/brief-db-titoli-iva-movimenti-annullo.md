# Brief DB — l'annullo di una forzatura vuole una colonna, non un campo in `meta`

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e sblocca la slice
> `T3-b` del piano
> [brief-be-fe-titoli-iva-soggetto.md](brief-be-fe-titoli-iva-soggetto.md).
>
> **Origine.** Richiesta di Tid del 2026-08-29, sul piano BE/FE di `I7`:
> *«dovrebbe essere permesso l'annullamento di una riga forzata/manuale; solo
> annullamento, deve rimanere traccia ma no delete»*.
>
> **Stato.** 2026-08-29 — verificato sulla **struttura** (`pg_constraint`,
> corpo dell'accumulatore dalla doc auto-generata). Nessuna misura sui dati.
>
> ⭐ **Rev. 2026-08-30 — RISPOSTO dal team DB: §5.** Il meccanismo e' approvato
> senza riserve; la **richiesta va riscritta** (§6). I due presidi proposti
> non bastano, e «append-only» — su cui poggia tutto il §1 — oggi **non lo
> impone niente**. ⛔ Da leggere prima di scrivere SQL: **§5.2, §5.3, §5.4,
> §5.8**.
>
> ✅ **Rev. 2026-08-30 — le tre decisioni sono PRESE** (§5.12: registro
> solo-aggiunte, niente catene di annulli, pulsante spento col motivo), ed e'
> scritto il **piano di sviluppo, §6**.
>
> ✅ **Rev. 2026-08-31 — SVILUPPATO E APPLICATO**: sei changeSet
> `20260830-21…26` (`EXECUTED` alle 00:19), tre codici errore, due file pgTAP,
> doc auto-gen rigenerata. Stato e cosa resta: **§7.5** e **§7.6**.
> ✅ **Rev. 2026-08-31 (2) — PERIMETRO DB CHIUSO**: pgTAP verdi, cinque manuali
> scritti, tre esistenti sanati (§7.6), doc rigenerata e agganciata.
> 🔴 Restano solo **FE** (cinque `reason_key`, l'unica cosa che blocca la CI) e
> **BE** (`genera_error_policies`).
>
> 🔴 **La cosa piu' urgente non e' l'annullo**: e' il §5.11 — alla PRIMA
> forzatura salvata da un operatore diventa rosso un pgTAP di un altro
> dominio, e nessuno lo collegherebbe a questa slice.
>
> **Correlati:**
> [soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) ·
> [trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) ·
> [brief-db-be-iva-risolutore-e-regime-cliente §8-ter](brief-db-be-iva-risolutore-e-regime-cliente.md)

---

## 1. Il meccanismo, e perché non è un flag

Una forzatura sbagliata si annulla registrando **una seconda riga `FORZATURA` di
segno opposto**. Non un `DELETE` (Tid: *«deve rimanere traccia»*) e non un flag
`annullato`.

⭐ **Le ragioni sono quattro, e la seconda riguarda direttamente il DB:**

1. il registro resta **append-only**, che è il punto di `D5`: *«una forzatura che
   sovrascrive non lascia traccia del perché; una forzatura che è una riga **è**
   la traccia»*. Un flag sarebbe di nuovo un valore sovrascritto sopra a un altro;
2. ⭐ **l'accumulatore non si tocca.**
   `trgfn_soggetti_titoli_iva_movimenti_accumulatore` fa
   `SELECT COALESCE(SUM(m.imponibile), 0) … WHERE m.titolo_iva_id = …` — **senza
   filtri**. Un contro-movimento riporta `imponibile_utilizzato` al valore giusto
   da solo. Un flag imporrebbe di aggiungere `WHERE NOT annullato`, cioè di
   mettere le mani **nel cuore di `I7`** per un caso di correzione;
3. la **data dell'annullo** è essa stessa un'informazione — quando qualcuno si è
   accorto dell'errore. Un flag la perde, una riga la porta in `data_movimento`;
4. la traccia è **più forte**: si vedono entrambe le righe, l'errore e la
   correzione, ognuna col suo motivo.

⚠️ **I `CHECK` esistenti lo ammettono già**, verificato: `chk_stiva_movimenti_segno`
vuole `imponibile <> 0` sulle forzature (quindi il segno opposto passa),
`chk_stiva_movimenti_documento` vuole `fattura_id IS NULL` sulle forzature, e
`chk_stiva_movimenti_motivo_forzatura` pretende il motivo — che sull'annullo è
proprio la cosa da scrivere. **Nessun vincolo va toccato.**

---

## 2. La richiesta

**Una colonna di collegamento su `anagrafiche.soggetti_titoli_iva_movimenti`**:

```text
annulla_movimento_id  bigint  NULL
    REFERENCES anagrafiche.soggetti_titoli_iva_movimenti(id)
```

⛔ **Perché non in `meta`**, ed è la ragione per cui questo brief esiste invece di
una riga di codice BE: un riferimento strutturale dentro un jsonb non ha FK, non
è interrogabile e non ha unicità — sarebbe una relazione dichiarata **a parole**
dentro un campo libero. Il frontend deve poter dire «questa riga è annullata» e
il backend deve poter rifiutare il doppio annullo: entrambe le cose vogliono una
colonna vera.

⭐ **Con, se il team DB concorda sul merito, due presidi che la rendono onesta:**

* un **UNIQUE parziale** su `annulla_movimento_id WHERE annulla_movimento_id IS NOT NULL`
  → una forzatura si annulla **una volta sola**. Senza, due contro-movimenti
  sulla stessa riga porterebbero `imponibile_utilizzato` dalla parte opposta, e
  il registro racconterebbe due annulli di un annullo solo;
* un **guard** che pretenda che il movimento annullato sia `tipo_movimento =
  'FORZATURA'` e che l'annullante lo sia a sua volta. ⚠️ Non è un `CHECK` di
  colonna: la regola legge **un'altra riga** della stessa tabella — la stessa
  ragione per cui `E_TITOLO_IVA_PLAFOND_MANCANTE` è un trigger e non un `CHECK`.
  📌 Un annullo di un movimento `FATTURA` non si corregge così: si corregge dal
  documento, con una nota di credito, ed è di `I4`.

📌 Serve anche una riga di `dbops.fk_index_policy` per la FK nuova, come per le
undici di `I7`. Se il «sì» o il «no» all'indice sia da rimandare lo decide il
team DB: la colonna si legge dal movimento annullato verso l'annullante, e oggi
quel verso non ha consumatori.

---

## 3. Presidio atteso

⭐ **Il test che conta non guarda il totale**: annullata una forzatura, il
registro deve avere **due righe** e `imponibile_utilizzato` deve essere tornato
al valore precedente.

⚠️ Un test che verificasse **solo** il totale passerebbe identico anche con un
`DELETE` della riga originale — cioè proprio con la cosa che Tid ha escluso, e
che è il motivo per cui questa voce esiste.

Più i due che negano: **doppio annullo** rifiutato (dall'UNIQUE parziale), e
**annullo di un `FATTURA`** rifiutato (dal guard).

---

## 4. Cosa succede lato BE/FE quando è applicato

Slice `T3-b` del piano: il verbo «Annulla» sulla sola riga `FORZATURA` non ancora
annullata, che scrive il contro-movimento; la riga annullata resa con il suo
segno barrato e il rimando alla riga che la annulla.

⚠️ Finché non c'è, `T3-a` va avanti lo stesso — registro in lettura e creazione
della forzatura non dipendono da questa colonna. È l'annullo, e solo l'annullo,
che aspetta.

---

## 5. 🔍 Analisi critica del team DB — 2026-08-30

> **Esito in una riga: il meccanismo è giusto, la richiesta è incompleta.**
> Il contro-movimento invece del flag è la forma corretta e le quattro ragioni del
> §1 reggono (con una da riscrivere, §5.7). Ma i due presidi proposti — UNIQUE
> parziale + guard sul tipo — **non bastano a rendere vero il presidio che il §3
> stesso pretende**, e ne mancano altri tre.
>
> **Verificato sulla struttura viva** (`pg_constraint`, `pg_trigger`, `pg_policy`,
> corpo dell'accumulatore), non sui dati.

### 5.1 ✅ Cosa il brief azzecca, e l'ho ricontrollato

| Affermazione del brief | Esito |
| --- | --- |
| L'accumulatore somma **senza filtri** | ✅ vero: `SELECT COALESCE(SUM(m.imponibile),0) … WHERE m.titolo_iva_id = v_titolo_id`, nient'altro. Un contro-movimento riporta il totale da sé |
| I tre `CHECK` ammettono già il contro-movimento | ✅ vero, letti da `pg_constraint`: `chk_stiva_movimenti_segno` chiede `imponibile <> 0` sulle forzature, `chk_stiva_movimenti_documento` chiede `fattura_id IS NULL`, `chk_stiva_movimenti_motivo_forzatura` pretende il motivo |
| `meta` è il posto sbagliato | ✅ concordo, e senza riserve |
| Il test non deve guardare il totale | ✅ ed è l'osservazione migliore del brief |

⭐ E l'accumulatore gira **anche su UPDATE e DELETE**
(`trg_stiva_movimenti_z90_accumulatore_ins_upd_dlt`), quindi la promessa «il
totale non può mentire» è mantenuta qualunque cosa succeda al registro. È il
motivo per cui il §3 ha ragione a diffidare del totale come unico presidio.

### 5.2 ⛔ Manca il vincolo che rende vero il §3: **l'importo**

Né l'UNIQUE parziale né il guard sul tipo impongono che il contro-movimento sia
**l'opposto esatto** di quello annullato. Il modello ammetterebbe un «annullo» di
100 su una forzatura di 250, e `imponibile_utilizzato` **non tornerebbe al valore
precedente** — cioè esattamente la cosa che il §3 dichiara essere il presidio.

> ⚠️ Il test proposto passerebbe lo stesso, perché la **fixture** scriverebbe il
> numero giusto. È il caso classico di un verde che non prova la regola ma la
> popolazione che il test si è fabbricato.

**Il guard deve pretendere `NEW.imponibile = - annullata.imponibile`.**

⭐ E c'è un corollario che cambia il contratto verso il BE: se l'importo è
**derivabile**, il backend non deve passarlo affatto. Una madre
`fn_annulla_movimento_titolo_iva(p_movimento_id, p_motivo)` che compone la riga
da sé è più difficile da usare male di una `INSERT` guidata da un guard — ed è la
convenzione della casa per le operazioni di dominio.

### 5.3 ⛔ Il guard legge un'altra riga della STESSA tabella, e lì c'è la RLS

`anagrafiche.soggetti_titoli_iva_movimenti` ha `relrowsecurity = t` con la policy
`rls_soggetti_titoli_iva_movimenti_ef_whitelist`, che pretende
`app.ruolo_applicativo = 'OPERATORE'` **e** la whitelist emittente risolta via
`soggetti_titoli_iva.emittente_fiscale_id`.

Il guard richiesto deve leggere la **riga annullata** per sapere che è una
`FORZATURA`. Quella lettura avviene **sotto RLS**, e da lì due conseguenze:

1. ⛔ un guard `SECURITY INVOKER` **non distingue «la riga non esiste» da «non la
   vedo»**: davanti a zero righe deve scegliere fra rifiutare con un messaggio
   fuorviante e passare su una premessa non verificata;
2. ⛔ **la FK non ha lo stesso problema, e questo li fa divergere.** In PostgreSQL
   i controlli di integrità referenziale **scavalcano sempre la RLS**. Quindi la
   FK accetterebbe un riferimento a una riga che il chiamante non vede, mentre il
   guard la tratterebbe come inesistente.

**Il guard va `SECURITY DEFINER`, con la ragione scritta nel corpo.** È lo stesso
caso già incontrato altrove nel progetto: *un trigger guard legge sotto RLS, e
non è ciò che si vuole quando la regola riguarda l'integrità e non la visibilità.*

### 5.4 ⛔ Il collegamento può puntare al **titolo sbagliato**

Niente, nella proposta, impone che la riga annullata appartenga **allo stesso
titolo IVA** dell'annullante. Con `annulla_movimento_id` su un movimento di un
altro titolo:

* il contro-movimento **decurta il plafond sbagliato**;
* il titolo della forzatura originale **resta gonfiato**;
* e i due totali sono entrambi «coerenti» per l'accumulatore, che somma per
  titolo e non sa niente del collegamento.

⛔ È il difetto peggiore dei cinque, perché **non solleva niente** e si vede solo
guardando due plafond insieme.

**Il guard deve pretendere `NEW.titolo_iva_id = annullata.titolo_iva_id`.**

### 5.5 ⛔ Due buchi che l'UNIQUE parziale non chiude

**a) L'auto-annullo.** Nulla vieta `annulla_movimento_id = id`: una riga che
annulla sé stessa. Si chiude con un `CHECK` di colonna — ed è uno dei pochi casi
in cui il `CHECK` è la sede giusta, perché confronta due colonne della **stessa**
riga:

```sql
CHECK (annulla_movimento_id IS NULL OR annulla_movimento_id <> id)
```

**b) La catena di annulli.** `A ← B ← C`. L'UNIQUE parziale impedisce **due righe
che annullano la stessa**, non la catena — e il guard proposto («entrambi
`FORZATURA`») **non la ferma**, perché l'annullante *è* una forzatura.

> ❓ **Decisione di dominio, e non la prende il DB**: annullare un annullo
> significa **ripristinare** la forzatura originale? Se sì, è un caso legittimo
> e va dichiarato (con l'attenzione che il §5.2 diventa una catena di segni). Se
> no — ed è la lettura che darei, perché «annullo» in questo registro vuol dire
> *correggere un errore*, non *fare avanti e indietro* — il guard deve pretendere
> anche `annullata.annulla_movimento_id IS NULL` e che **nessuno annulli già**
> quella riga.

### 5.6 ⚠️ Il §2 contraddice il §4 sull'indice — ma il punto è comunque risolto

* **§2**: *«la colonna si legge dal movimento annullato verso l'annullante, e oggi
  quel verso non ha consumatori»*;
* **§4**: *«la riga annullata resa con il suo segno barrato e **il rimando alla
  riga che la annulla**»* — che è **esattamente quel verso**, ed è un consumatore.

⭐ La contraddizione però si scioglie da sé, e in favore del brief: l'**UNIQUE
parziale** `WHERE annulla_movimento_id IS NOT NULL` **copre già la FK**. Le linee
guida (§8.7) ammettono come coperta una FK il cui indice ha predicato «assente
oppure una congiunzione di soli `<colonna della FK> IS NOT NULL`», ed è
letteralmente questo caso. Quindi `dbops.vw_fk_senza_indice` non la vedrà mai
scoperta e `apply_fk_index_policy()` non creerebbe nulla **nemmeno a
`consentito=true`**.

**La riga di seed serve solo a *governare* la FK**, non a farle nascere un indice:
`consentito=false`, con `dll_command` **valorizzato lo stesso** (regola di casa:
quel campo non resta vuoto neanche a flag spento). Va nel CSV dedicato del
cantiere, `80_data/sql/anagrafiche/fk_index_policy_titoli_iva.csv`, che ha già le
undici righe di `I7` e il suo loader.

### 5.7 ⚠️ Una ragione del §1 è imprecisa, e va riscritta

Il §1 punto 1 argomenta che un `DELETE` non lascerebbe traccia. **Non è
esatto**: esiste `storico.soggetti_titoli_iva_movimenti` e il trigger
`trg_soggetti_titoli_iva_movimenti_z90_storico_upd_dlt` (`BEFORE DELETE OR
UPDATE`). Una riga cancellata finirebbe lì.

La conclusione non cambia — il contro-movimento resta la forma giusta — ma la
**ragione** sì, ed è più forte di quella scritta:

> Lo storico è un **audit tecnico**, non un documento che l'operatore legge. Un
> `DELETE` toglierebbe dal **registro visibile** la data della correzione e il suo
> motivo, cioè proprio le due informazioni per cui l'annullo esiste.

⚠️ *Una ragione sbagliata è quella che il prossimo smonta*, portandosi via anche
la conclusione giusta.

### 5.8 ⛔ E il pezzo che manca del tutto: **«append-only» non è presidiato**

Tutto il §1 poggia su *«il registro resta append-only»*. Nel database **non c'è
nulla che lo imponga**: nessun guard su `UPDATE`, nessuno su `DELETE`. I trigger
presenti sono audit, `tx_id`, storico, `require_active_parent` e l'accumulatore —
nessuno rifiuta.

Il §3 lo sa (*«un test che verificasse solo il totale passerebbe identico anche
con un `DELETE`»*) e propone un **test**. ⛔ Ma un test verifica che la funzione
giusta faccia la cosa giusta: **non impedisce a nessuno di cancellare**.

> **Delle due l'una, e va scelta:**
>
> * se «append-only» è il **progetto**, va scritto nel DB — un guard `_a10_`
>   `BEFORE UPDATE OR DELETE` che rifiuta, con l'eventuale eccezione motivata
>   (bonifiche a rubinetto chiuso);
> * se è una **convenzione di scrittura del BE**, va detto così — e allora il §1
>   punto 1 non è un argomento strutturale ma una promessa che qualcuno mantiene.
>
> ⚠️ Oggi il brief la usa come argomento strutturale, e non lo è ancora.

### 5.9 ⚠️ Un rifiuto che l'operatore non capirà

L'accumulatore alza `E_TITOLO_IVA_UTILIZZATO_NEGATIVO` quando la somma scende
sotto zero. **L'annullo può farcela scendere**: basta che nel frattempo le note
di credito superino le fatture su quel titolo.

L'operatore che preme «Annulla» leggerebbe un messaggio sull'*utilizzato
negativo* — vero, ma che in quel contesto non dice **perché quell'annullo non si
può fare**. È la stessa classe del pulsante grigio col tooltip sbagliato.

Non è bloccante e non chiede per forza un codice nuovo: chiede una **decisione
dichiarata**. Se si accetta, si scrive che si accetta.

### 5.10 ⚠️ Note minori, da correggere prima di scrivere SQL

* **«UNIQUE parziale» in PostgreSQL non è un constraint**: è
  `CREATE UNIQUE INDEX … WHERE …`. La tabella ha già esattamente questa forma
  (`uq_stiva_movimenti_documento`), quindi il nome segue **quella**:
  `uq_stiva_movimenti_annulla`. La FK invece segue la forma lunga usata dalle
  altre tre: `fk_soggetti_titoli_iva_movimenti_annulla`.
* ⚠️ **La doc auto-gen di questa tabella è stantia**: non elenca il trigger di
  storico, che nel database c'è. Non cambia le conclusioni del brief, ma la
  verifica dei trigger va rifatta su `pg_trigger` — non su quella pagina.
* Il codice errore del guard, se nuovo, ha **tre sedi** e non due: il catalogo DB
  (`codici_errore.csv` + `messaggi_errore.csv`), il file **generato** del backend
  (`error_policies_generated.py`, via `manage.py genera_error_policies`), e i
  locales del frontend **solo** se diventa anche una `reason_key` di capability.
  Qui è un `RAISE`, quindi le sedi sono le prime due — ma la seconda si dimentica.

---

### 5.11 🔴 Un presidio che SCADE nel momento in cui questa slice entra in uso

> ### In due righe, prima del dettaglio
>
> C'è un test che fa da **lista di controllo**: *«quando cancello una fattura, ho
> ripulito tutte le tabelle collegate?»*. Il registro dei movimenti di plafond è
> in quella lista come **eccezione con alibi** — *«per ora non ci pensiamo, tanto
> è vuota e non ci scrive nessuno»* — e il test **controlla che l'alibi regga**:
> conta le righe e pretende zero.
>
> ⭐ **È fatto apposta**: il giorno che qualcuno ci scrive, si accende e dice
> *«l'alibi è scaduto, adesso decidete cosa deve fare la pulizia»*.
>
> ⛔ **Ma si accenderebbe per il motivo sbagliato.** La tabella sta per riempirsi
> di **forzature**, che con le fatture non c'entrano niente: una forzatura non ha
> una fattura dietro, glielo vieta `chk_stiva_movimenti_documento`. L'alibi
> difende le righe **figlie di una fattura**; il conteggio le guarda **tutte**.
>
> ✅ **Non richiede nessuna decisione.** Si conta solo ciò che una fattura ce l'ha
> davvero — una riga di SQL dentro quel test, `F-2` del piano. La decisione vera
> (*cosa deve fare la pulizia con i movimenti di plafond quando si cancella una
> fattura in bozza*) **non è di oggi e non è di questo brief**: è di `I5`, e
> resta rimandata esattamente com'era.
>
> ⚠️ Sta scritto qui, e non in un `TODO`, per un motivo solo: se non lo si fa in
> questo giro, quel rosso arriva **da solo giorni dopo**, in un file che parla di
> fatture e non di IVA, e chi lo trova non lo collega a questa slice.
>
> **Non è nel brief, e non è di questo brief: è una cosa che questa slice fa
> succedere a un altro cantiere.** Va scritta qui perché è qui che qualcuno la
> leggerà in tempo.

`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` verifica che la
pulizia di una fattura copra **tutte** le sue tabelle figlie, lette dal catalogo
(`pg_constraint`). `anagrafiche.soggetti_titoli_iva_movimenti` è figlia di
`vendite.fatture` e di `vendite.fatture_righe`, e nell'elenco compare come
**eccezione `SCOPERTA_NOTA`**, con questa motivazione:

> *«consumo di plafond di un titolo IVA: **0 righe** e nessuno scrittore
> (`fn_consuma_plafond_titolo_iva` non ha chiamanti). […] la categoria definitiva
> dipende da `I5`: consumo all'EMISSIONE → `BLOCCO_VOLUTO`; consumo già in bozza
> → `GESTITA`, e la pulizia deve **stornare** il movimento prima di cancellare,
> altrimenti il plafond di un terzo resta mangiato da un documento che non esiste
> più.»*

E l'**asserzione 5** di quel file pretende che le tabelle `SCOPERTA_NOTA` siano
**ancora vuote**: conta le righe e vuole zero.

#### ⛔ Cosa succede alla prima forzatura

`T3-a` (creazione della forzatura) è **già implementata lato BE**:
`titoli_iva_repository.create_forzatura` scrive direttamente nel registro. La
tabella è a **zero righe** oggi (verificato il 2026-08-30) solo perché nessuno ha
ancora usato la funzione.

> **Il giorno in cui il primo operatore salva una forzatura, quell'asserzione
> diventa rossa** — in una suite che non c'entra niente con i titoli IVA, e per
> un motivo che chi la legge non collegherà a questa slice.

⚠️ Ed è un rosso **giusto come meccanismo e sbagliato come misura**: l'eccezione
parla di *figlie della fattura*, ma il conteggio è su **tutta la tabella**. Una
forzatura ha `fattura_id IS NULL` — glielo impone `chk_stiva_movimenti_documento`
— quindi **non è figlia di nessuna fattura** e non ha niente a che vedere con la
pulizia che quel test presidia.

#### ✅ Cosa fare, ed è una riga

Restringere il conteggio a ciò che l'eccezione difende davvero:

```sql
SELECT count(*) FROM anagrafiche.soggetti_titoli_iva_movimenti
 WHERE fattura_id IS NOT NULL
```

Così il presidio **resta vivo per il caso vero** — il giorno in cui `I4` scriverà
i movimenti `FATTURA`/`NOTA_CREDITO`, che figlie lo sono davvero — e smette di
accendersi su righe che non sono mai state il suo problema.

⚠️ **Va fatto nello stesso giro di questa slice**, non dopo: un rosso che arriva
da solo, giorni dopo, in un file di un altro dominio, è il modo più efficiente di
far perdere mezza giornata a qualcuno.

⭐ **E c'è una convergenza che vale la pena vedere.** La nota dell'eccezione dice
che, per i movimenti da fattura, *«la pulizia deve **stornare** il movimento prima
di cancellare»*. Lo storno di un movimento con un movimento di segno opposto è
**esattamente il meccanismo che questa slice sta costruendo**. Quando `I5`
deciderà, la risposta potrebbe non essere codice nuovo: potrebbe essere questo,
riusato — con la differenza che lì lo storno lo scrive la pulizia e non un
operatore, quindi il `motivo` non è digitato ma dichiarato.

⚠️ Un dettaglio da non perdere: quel file porta il marcatore
`pgtap-runner: owner`, e la ragione è scritta in testa — quel conteggio sotto RLS
non distinguerebbe «la tabella è vuota» da «non la vedo», e il presidio si
autoassolverebbe. Chi tocca l'asserzione non tolga il marcatore.

---

### 5.12 ✅ Le tre decisioni — prese da Tid il 2026-08-30

| # | Domanda | Risposta | Cosa comporta |
| --- | --- | --- | --- |
| **B-1** | Il registro è «solo aggiunte» per progetto o per convenzione? | ✅ **Per progetto: si vieta sia `DELETE` sia `UPDATE`** | guard `_a10_` `BEFORE UPDATE OR DELETE`. ⭐ L'argomento del §1 diventa **vero** invece che sperato |
| **B-2** | Si può annullare un annullo? | ✅ **No: se la forzatura serve ancora, se ne scrive una nuova** | il guard pretende che la riga annullata **non sia essa stessa un annullo** e **non sia già annullata**. Niente catene: `annulla_movimento_id` è profondo uno |
| **B-3** | Cosa vede l'operatore quando l'annullo non si può fare? | ✅ **Il pulsante già spento, col motivo** | serve una `fn_check_*` per riga + il motivo su una superficie che il drawer legge + la `reason_key` nei locales |

#### ⭐ B-1: cosa costa davvero, misurato

Cercato il 2026-08-30 su `db/pgtap`, `backend/apps`, `db/changelog`, `scripts` e
`frontend/src`: **nessuno** fa `DELETE`/`UPDATE` su quella tabella oggi. Il guard
non rompe niente — ma la ricerca testuale **non vede l'SQL dinamico**, ed è
esattamente il caso del §5.12: la pulizia della fattura scopre le figlie da
`pg_constraint` e le cancella per nome costruito.

> ⛔ **Quindi il guard deve nascere sapendo che un giorno la pulizia dovrà
> passare.** Le due strade, e la seconda è quella che il §5.12 già indica:
>
> * un'**apertura dichiarata** per le bonifiche (una GUC che la pulizia accende e
>   richiude — il progetto ha già questa forma altrove);
> * oppure, meglio, **la pulizia non cancella: storna** — e allora il guard non ha
>   bisogno di eccezioni, perché nessuno cancella davvero.
>
> Non va deciso adesso: va **scritto nel corpo del guard**, così chi arriverà con
> `I5` trova la domanda invece di trovare un muro.

#### ⭐ B-3: la forma esiste già, e non va inventata

Il progetto ha già il pattern per le **azioni per riga** (linee guida SQL §12.5),
ed è stato costruito per un caso quasi identico — l'annullo di un accredito su un
reso:

* una `script.fn_check_<azione>(<id_riga>)` **pura**, che torna `[]` se ammesso e
  altrimenti un array **ordinato** di `{codice, reason, reason_key, dettaglio}`;
* ⭐ **la madre CHIAMA la check** e solleva il codice del primo motivo, invece di
  riscrivere il predicato: così i due non *coincidono oggi*, **non possono
  divergere**;
* il motivo arriva al frontend come **una colonna della vista di riga**, con un
  nome che dice **quale verbo** (`annullo_blocco_codice`) — ⛔ mai riusando la
  colonna di un altro verbo;
* ⚠️ e la colonna va sulla superficie **da cui si preme il pulsante**, non su
  quella che «parla di quella cosa». È l'errore che nel caso dei resi è costato un
  changeSet in più.

⛔ **Oggi per il registro dei movimenti non esiste nessuna vista.** È lo stesso
punto di partenza dei resi, dove è nata `vw_resi_righe_dettaglio` proprio perché
il motivo di blocco poteva arrivare solo dove non serviva. Va messo in conto: la
vista di riga del registro è **parte di B-3**, non un extra.

---

## 6. 🛠️ Piano di sviluppo

> ⛔ **Nessuna riga scritta.** Questo capitolo è il piano, non il lavoro: al
> 2026-08-30 non esiste nessun changeSet, nessun pgTAP, nessun seed. Lo sviluppo
> parte su richiesta esplicita di Tid.
>
> **Perimetro**: solo DB (`dev/db-tid`). L'unica cosa che questo piano chiede a un
> altro perimetro è **una riga di testo al frontend** (§6.6), e va chiesta nello
> stesso giro.

### 6.0 Il principio d'ordine

> **Ogni fase deve lasciare il registro in uno stato in cui l'annullo o è
> completo o non esiste.**

È il criterio che tiene insieme A-1 e A-2: consegnare la colonna senza i guard
significa aprire una strada — «scrivi una riga con `annulla_movimento_id`» — che
il database non sa ancora difendere. Un annullo con l'importo sbagliato è peggio
di nessun annullo, perché il totale mente **e sembra a posto** (§5.2).

### 6.1 ⭐ La forma: una madre, e i guard come difesa

Le decisioni cambiano la forma della consegna rispetto al §2, e vale la pena
dirlo prima dell'elenco dei file.

Il brief chiedeva **una colonna** e lasciava al BE il compito di comporre la riga.
Con B-1/B-2/B-3 presi, la strada giusta è **una madre di dominio**:

```sql
anagrafiche.fn_annulla_movimento_titolo_iva(p_movimento_id bigint, p_motivo varchar)
    RETURNS bigint   -- l'id della riga di annullo
```

⭐ **Perché non è un ornamento**: l'importo e il titolo del contro-movimento sono
**derivabili** dalla riga annullata. Se li deriva la madre, due dei cinque
controlli del guard smettono di essere «errori che l'operatore può fare» e
diventano **difesa contro una scrittura diretta** — che è il posto giusto per
loro. Il BE passa due cose sole: *quale riga* e *perché*.

⚠️ **I guard restano comunque**, e non sono ridondanti: la tabella è scrivibile
anche senza passare dalla madre, e un guard che esiste solo perché «tanto ci si
passa dalla madre» è un guard che il primo `INSERT` diretto scavalca.

⭐ E la madre **chiama la check**, non riscrive il predicato (§6.3): così i due
non *coincidono oggi*, **non possono divergere**.

### 6.2 Fase A — lo schema

**Un changeSet**, in `00_schema/anagrafiche/`:
`20260830-21-alter-stiva-movimenti-annulla-movimento-id-mctit.yaml`

⚠️ **La numerazione parte da `21`** (Tid, 2026-08-30): i changeSet di questa
slice sono `20260830-21`, `-22`, … ⛔ Non si riparte dal primo libero trovato
con un `find`: il repo è attivo su più cantieri e quel numero si muove nel giro
di ore. Il blocco è **riservato**.

| # | Oggetto | Forma |
| --- | --- | --- |
| A-1a | colonna | `annulla_movimento_id bigint NULL` |
| A-1b | FK | `fk_soggetti_titoli_iva_movimenti_annulla` → `(id)` della stessa tabella. ⚠️ `ON DELETE NO ACTION`: con B-1 nessuno cancella, e una `SET NULL` messa «per sicurezza» disarmerebbe in silenzio il vincolo del passo dopo |
| A-1c | CHECK | `chk_stiva_movimenti_auto_annullo`: `annulla_movimento_id IS NULL OR annulla_movimento_id <> id` (§5.5a) |
| A-1d | indice unique parziale | `CREATE UNIQUE INDEX uq_stiva_movimenti_annulla … WHERE annulla_movimento_id IS NOT NULL` — ⚠️ **indice, non constraint**: PostgreSQL non ha UNIQUE parziali come vincoli di tabella. Il nome segue la tabella, che usa già `uq_` per un indice parziale (`uq_stiva_movimenti_documento`) |

⭐ **Il `CHECK` di A-1c è uno dei pochi casi in cui il `CHECK` è la sede giusta**:
confronta due colonne della **stessa** riga, quindi non ha bisogno di leggerne
un'altra. Tutto il resto è materia di guard, per la ragione che il §2 già dava.

### 6.3 Fase B — i guard e la check

Tre changeSet in `20_code/`, e l'ordine conta.

#### B-a · Il registro diventa «solo aggiunte» — decisione B-1

`20_code/anagrafiche/…-create-trgfn-stiva-movimenti-append-only-mctit.yaml`, con
il trigger `trg_stiva_movimenti_a10_append_only_upd_dlt`
(`BEFORE UPDATE OR DELETE`) che solleva `E_STIVA_MOVIMENTO_IMMUTABILE`.

⚠️ **Tre cose da scrivere nel corpo, non da lasciare dedurre:**

1. ⛔ **La pulizia della fattura, un giorno, dovrà passare.** Oggi non tocca
   questa tabella (è un'eccezione `SCOPERTA_NOTA`, §5.11), ma la nota di quel
   test dice che con `I5` *«la pulizia deve stornare il movimento prima di
   cancellare»*. Le due strade — un'apertura dichiarata via GUC, oppure **storno
   invece di cancellazione** — vanno **nominate nel corpo del guard**, così chi
   arriva con `I5` trova la domanda invece di un muro. ⭐ La seconda è preferibile
   e non richiede nessuna eccezione: se nessuno cancella, il guard non ha buchi.
2. ⚠️ **Dal guard in poi, tre rami diventano irraggiungibili**: la branca `UPDATE`
   dell'accumulatore, quella dello storico e quella dell'audit. ⛔ **Non si
   tolgono** — sono difesa in profondità — ma vanno **dichiarati tali**, o il
   prossimo che legge l'accumulatore crederà che il caso «un movimento cambia
   titolo» sia vivo. Quel commento oggi lo descrive come reale.
3. ⚠️ **Nessuna eccezione per l'owner**: il guard è un trigger e scatta per tutti.
   Una bonifica futura passerà dalla porta dichiarata, non dal ruolo.

#### B-b · La check per riga — decisione B-3

`20_code/script/…-create-fn-check-annullo-movimento-titolo-iva-mctit.yaml`

`script.fn_check_annullo_movimento_titolo_iva(p_movimento_id bigint) RETURNS jsonb`
— **pura**, `STABLE`, non solleva: `[]` se ammesso, altrimenti array **ordinato**
di `{codice, reason, reason_key, dettaglio}`.

| ordine | `reason` | quando |
| --- | --- | --- |
| 1 | `NON_FORZATURA` | il movimento non è una `FORZATURA` — un `FATTURA` si corregge dal documento, con una nota di credito, ed è di `I4` |
| 2 | `E_UN_ANNULLO` | il movimento **è** esso stesso un annullo (decisione B-2) |
| 3 | `GIA_ANNULLATO` | esiste già una riga che lo annulla |
| 4 | `PLAFOND_NEGATIVO` | l'annullo porterebbe l'usato del titolo sotto zero (§5.9) |

⚠️ **L'ordine dell'array è il contratto**: la superficie mostra il **primo**
motivo, e la madre solleva il codice del primo. Se divergessero, il tooltip
direbbe una cosa e l'errore un'altra.

⛔ **`SECURITY DEFINER`, con la ragione scritta** (§5.3): la check legge un'altra
riga di una tabella con RLS attiva, e da `SECURITY INVOKER` non distinguerebbe
«non esiste» da «non la vedo» — mentre la FK, che la RLS la scavalca sempre,
accetterebbe lo stesso riferimento. I due divergerebbero **in silenzio**.

#### B-c · Il guard dell'annullo

`20_code/anagrafiche/…-create-trgfn-stiva-movimenti-guard-annullo-mctit.yaml`, con
il trigger `trg_stiva_movimenti_a10_guard_annullo_ins`
(`BEFORE INSERT`, `WHEN (NEW.annulla_movimento_id IS NOT NULL)`).

Solleva il codice del **primo** motivo restituito dalla check, **più** i due
controlli che la check non fa perché non riguardano l'ammissibilità ma la
**coerenza della riga scritta**:

* `NEW.titolo_iva_id = annullata.titolo_iva_id` (§5.4 — il difetto peggiore:
  decurta il plafond sbagliato e **non solleva niente**);
* `NEW.imponibile = - annullata.imponibile` (§5.2 — senza, il presidio del §3 lo
  rende vero la fixture, non la regola).

⭐ Passando dalla madre questi due sono **derivati**, quindi qui sono difesa
contro l'`INSERT` diretto: è giusto che ci siano ed è giusto che il messaggio
dica che qualcuno ha scritto a mano.

### 6.4 Fase C — la madre

`20_code/anagrafiche/…-create-fn-annulla-movimento-titolo-iva-mctit.yaml`

`SECURITY INVOKER` (convenzione delle madri: RLS e scope restano applicati),
**una sola `SELECT`** per il chiamante, atomica per costruzione.

1. guard di parametro (`p_movimento_id > 0`, `p_motivo` non vuoto);
2. **chiama** `fn_check_annullo_movimento_titolo_iva` e, se torna motivi, solleva
   il codice del primo — ⛔ **non riscrive il predicato**;
3. compone la riga: `titolo_iva_id` e `imponibile` **derivati** dalla riga
   annullata, `tipo_movimento = 'FORZATURA'`, `fattura_id`/`fattura_riga_id` a
   `NULL` (glielo impone già `chk_stiva_movimenti_documento`), `data_movimento`
   = oggi, `motivo` = `p_motivo`, `annulla_movimento_id` = `p_movimento_id`;
4. ritorna l'id della riga nuova.

⚠️ `data_movimento` è **la data dell'annullo**, non quella della forzatura: è il
punto 3 del §1 del brief, ed è l'unica informazione che un flag avrebbe perso.

### 6.5 Fase D — la superficie da cui si preme il pulsante

⛔ **Oggi non esiste nessuna vista sul registro dei movimenti.** È lo stesso punto
di partenza dei resi, dove il motivo di blocco poteva arrivare solo dove non
serviva, e da cui è nata una vista di dettaglio apposta.

`20_code/anagrafiche/…-create-vw-stiva-movimenti-dettaglio-mctit.yaml`

* `security_invoker=on` — ⛔ da **ri-specificare**: un `CREATE OR REPLACE VIEW`
  che non la ripete la **azzera**, e la vista scavalcherebbe la RLS senza dirlo;
* le colonne del registro + il tipo di titolo, per la lettura;
* ⭐ **`annullo_blocco_codice`** e **`annullo_blocco_reason_key`**: il `reason` del
  primo motivo (`NULL` = ammesso). Un verbo, una colonna, con un nome che dice
  **quale verbo** — ⛔ mai riusando la colonna di un altro;
* la riga annullata e quella che la annulla, così il frontend può barrare la
  prima e rimandare alla seconda (§4).

### 6.6 Fase E — catalogo, seed, e la riga che tocca al frontend

| # | Cosa | Dove |
| --- | --- | --- |
| E-1 | `E_STIVA_MOVIMENTO_IMMUTABILE` — classe `CONFLITTO_STATO` (non c'è un campo da correggere: è la natura del registro) | append a `codici_errore.csv` + `messaggi_errore.csv` |
| E-2 | `E_STIVA_ANNULLO_NON_AMMESSO` — classe `CONFLITTO_STATO`, **un codice solo** per i quattro `reason` della check | idem |
| E-3 | `E_STIVA_ANNULLO_INCOERENTE` — classe **`TECNICO`**: titolo diverso o importo non opposto li può produrre **solo un chiamante rotto**, non una persona in un form. ⚠️ Su un `TECNICO` la chiave `campo` **esce** dal contesto | idem |
| E-4 | riga in `fk_index_policy_titoli_iva.csv`: `consentito=false`, `dll_command` **valorizzato lo stesso** | append al CSV del cantiere (§5.6) |
| E-5 | 🔴 **le `reason_key` nei locales** — `it.json` **e** `en.json` | ⛔ **frontend, nello stesso giro** |

⚠️ **E-5 non è un dettaglio di cortesia**: una `reason_key` emessa dal database e
assente dai locales è un pulsante grigio col **tooltip vuoto**, cioè il difetto
che B-3 esisteva per evitare, in forma peggiore — e `scripts/check_i18n_keys.py`
fa **fallire la CI**. ⚠️ Il cancello legge la doc auto-gen, quindi diventa rosso
**al primo migrate + rigenerazione**, non prima: la riga va chiesta al FE
**adesso**, non quando la build si accende.

⚠️ E ogni codice errore nuovo ha **tre sedi**, non due: catalogo DB, il file
**generato** del backend (`error_policies_generated.py`, via
`manage.py genera_error_policies`), e i locales — questi ultimi solo per ciò che
diventa `reason_key`. La seconda è quella che si dimentica.

⛔ **Nessun append al CSV con `csv.writer` di Python senza `lineterminator='\n'`**:
il default è `\r\n`, e un ritorno carrello in quei file uccide il `COPY` del
mirror con un errore che indica la riga giusta e non la causa. Invisibile nel
diff.

### 6.7 Fase F — i presidi

**F-1 · Il pgTAP nuovo**: `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`.
Il §3 ne chiedeva tre; con le decisioni prese ne servono **nove**.

| # | Caso | Da dove nasce |
| --- | --- | --- |
| 1 | annullata una forzatura: **due righe** nel registro e `imponibile_utilizzato` tornato al valore precedente | §3 |
| 2 | **doppio annullo** rifiutato | §3 (dall'indice unique) |
| 3 | **annullo di un `FATTURA`** rifiutato | §3 (dalla check) |
| 4 | ⭐ **importo diverso dall'opposto** rifiutato — è ciò che rende vero il n. 1 invece di lasciarlo alla fixture | §5.2 |
| 5 | ⭐ **collegamento a un movimento di un altro titolo** rifiutato | §5.4 |
| 6 | **auto-annullo** rifiutato | §5.5a |
| 7 | ⭐ **annullo di un annullo** rifiutato | decisione B-2 |
| 8 | ⭐ `DELETE` e `UPDATE` sul registro **rifiutati** | decisione B-1 |
| 9 | ⭐ la check **vede la riga annullata anche fuori perimetro RLS**, costruito con **due emittenti** | §5.3 — senza, il `SECURITY DEFINER` è una parola che nessuno verifica |

⚠️ `throws_ok` **sempre** con lo SQLSTATE (`'P0001'`), o `throws_like` sulla frase
dove la frase è la posta in gioco. ⚠️ Niente `LIMIT 1` senza `ORDER BY`.

**F-2 · 🔴 Il presidio che scade** (§5.11): restringere a
`WHERE fattura_id IS NOT NULL` il conteggio dell'asserzione 5 di
`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql`.

⛔ **Va fatto in questo giro**, non dopo: alla prima forzatura salvata quel test
diventa rosso, in un file di un altro dominio, per un motivo che nessuno
collegherà a questa slice. ⚠️ E **non si tocca il marcatore `pgtap-runner: owner`**
in testa a quel file: quel conteggio sotto RLS non distinguerebbe «vuota» da «non
la vedo», e il presidio si autoassolverebbe.

**F-3 · La ricerca che l'ultima volta è costata una regressione.** Prima di
consegnare, `grep` sui pgTAP per il nome di **ogni** oggetto toccato — tabella,
viste, funzioni — non solo del più importante:

```bash
grep -rl "soggetti_titoli_iva_movimenti" db/pgtap/
grep -rl "<ogni nome di funzione o vista nuova>" db/pgtap/ backend/apps
```

⚠️ E la ricerca testuale **non vede l'SQL dinamico**: la pulizia della fattura
scopre le figlie da `pg_constraint` e le cancella per nome costruito. È il motivo
per cui F-2 esiste.

### 6.8 La verifica prima dell'apply

⛔ **Nessuna migrazione si applica**: il piano si ferma ai file scritti e alla
verifica in transazione annullata. L'`update` lo autorizza Tid, a voce, per quel
comando.

1. i blocchi `changes[].sql.sql` si **estraggono dagli YAML** e si eseguono
   **interi**, `ON_ERROR_STOP=1`, in una transazione che si annulla. ⚠️ Riscrivere
   l'SQL a mano non prova il changeSet: si salterebbero `COMMENT` e `GRANT`, che
   è dove vive il difetto dell'apostrofo;
2. DDL **+ il pgTAP nuovo nella stessa transazione annullata** — ⚠️ girando prima
   del migrate ci si connette da **owner**, quindi la RLS **non è esercitata**:
   il caso 9 va rifatto dal runner dopo l'apply;
3. il mirror dei CSV si prova **rifacendo l'upsert su tutte le righe** dei file
   toccati, in transazione annullata;
4. i cancelli statici (`guardrail_sql_letterali.py`, `guardrail_run_on_change.py`,
   `guardrail_pgtap_preambolo.py`) si lanciano a mano, non si aspetta la CI;
5. dopo l'apply: `scripts/testpgtap.sh` sui due file e
   `scripts/pgtap-baseline.sh anagrafiche vendite`.

### 6.9 ⛔ Cosa questo piano NON fa

* **non applica migrazioni**, nemmeno dopo un «procedi»;
* **non tocca `backend/` né `frontend/`** — l'unica richiesta è E-5, scritta qui;
* **non tocca l'accumulatore**: il §1 punto 2 del brief ha ragione, e resta vero
  anche con i guard;
* **non decide la categoria dell'eccezione `SCOPERTA_NOTA`**: F-2 restringe la
  misura al perimetro che l'eccezione difende, la categoria la decide `I5`;
* **non conia un codice per `PLAFOND_NEGATIVO`**: quel motivo lo espone la check
  per spegnere il pulsante, e chi ci passa comunque incontra
  `E_TITOLO_IVA_UTILIZZATO_NEGATIVO` dall'accumulatore — che a quel punto arriva
  a un chiamante che ha ignorato un pulsante spento;
* **non commette**.

---

## 7. ✅ Sviluppo eseguito — 2026-08-30/31

> **I file ci sono tutti. Niente è applicato**: `databasechangelog` non conosce
> nessuno dei sei changeSet. L'`update` lo autorizza Tid, a voce, per quel
> comando.

### 7.1 I file

| # | File | Cosa |
| --- | --- | --- |
| A | `00_schema/anagrafiche/20260830-21-alter-stiva-movimenti-annulla-movimento-id` | colonna + FK + `CHECK` anti auto-annullo + indice unique parziale |
| B-a | `20_code/anagrafiche/20260830-22-create-trgfn-stiva-movimenti-append-only` | il registro diventa solo-aggiunte (**B-1**) |
| B-b | `20_code/script/20260830-23-create-fn-check-annullo-movimento-titolo-iva` | i cinque motivi, `SECURITY DEFINER` (**B-3**) |
| B-c | `20_code/anagrafiche/20260830-24-create-trgfn-stiva-movimenti-guard-annullo` | chiama la check + i due controlli di coerenza |
| C | `20_code/anagrafiche/20260830-25-create-fn-annulla-movimento-titolo-iva` | la madre: deriva importo e titolo |
| D | `20_code/anagrafiche/20260830-26-create-vw-stiva-movimenti-dettaglio` | la superficie da cui si preme il pulsante |
| E | `80_data/sql/config/codici_errore.csv` · `messaggi_errore.csv` · `anagrafiche/fk_index_policy_titoli_iva.csv` | tre codici (1027-1029) + la riga di policy |
| F-1 | `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` | **12** asserzioni |
| F-2 | `db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` | il conteggio ristretto a `fattura_id IS NOT NULL` |

⚠️ **La numerazione è `20260830-21…26`** — il blocco riservato da Tid — anche se
i file sono stati scritti a cavallo della mezzanotte. Il numero è una **chiave di
ordinamento**, non la data in cui si è digitato: `21…26` sta dopo tutto il 30 e
prima di tutto il 31, ed è il posto giusto. ✅ Verificato che il blocco fosse
libero: nessuna collisione.

### 7.2 ⭐ Cinque cose trovate scrivendo

**1. L'ordine di estrazione non è l'ordine delle cartelle.** La prima estrazione
per la verifica metteva la check (`-23`, in `script/`) **dopo** il guard che la
chiama (`-24`, in `anagrafiche/`), perché ordinava per cartella. L'autogen
**ordina per numero** mescolando `00_schema` e `20_code`: la verifica va fatta
con lo stesso ordine, o prova una sequenza che non esisterà mai.

**2. Due titoli dello stesso soggetto non si possono avere**, e giustamente:
`ex_soggetti_titoli_iva_no_overlap` vieta due titoli con stesso tipo, emittente e
soggetto su validità sovrapposte. La fixture usa quindi **due soggetti diversi**
— ⭐ e il test ne esce **più forte**, perché il caso peggiore del collegamento
incrociato è proprio un annullo che decurta il plafond **di un altro cliente**.

**3. Il doppio annullo esce `P0001`, non `23505`.** Il guard chiama la check, che
risponde `GIA_ANNULLATO`, e solleva **prima** che l'indice venga valutato.
L'indice resta la difesa finale per chi scrivesse col guard spento — ma non è lui
a parlare all'operatore. Il commento del test lo dice, perché la prima stesura
diceva il contrario.

**4. Il guard dell'annullo doveva essere `SECURITY DEFINER` anche lui**, non solo
la check: deve rileggere la riga annullata per confrontare titolo e importo, e da
`INVOKER` una riga fuori perimetro si sarebbe letta come «non esiste».

**5. ⛔ Il `%TYPE` mancava nelle FIRME** (rilievo di Tid, 2026-08-31). Nei
`DECLARE` c'era ovunque — `v_new_id`, `v_somma_post`, `v_tipo_descr`, `v_tx_id` —
e nella firma della madre c'era su `p_motivo`. Ma `p_movimento_id` era `bigint`
nudo in **entrambe** le funzioni, e la madre dichiarava `RETURNS bigint`.

Corretto: le due firme ancorano a
`anagrafiche.soggetti_titoli_iva_movimenti.id%TYPE`, e la madre ritorna lo stesso.

> ⚠️ **Perché è facile che sfugga proprio lì**: nel `DECLARE` il `%TYPE` si scrive
> mentre si pensa al dato, nella firma si scrive mentre si pensa all'interfaccia —
> e un `bigint` in firma «funziona» identico, quindi niente lo segnala. Non lo
> vede nessun cancello.

⭐ **E la verifica giusta non è rileggere la firma, è guardare cosa risolve.**
`%TYPE` viene sciolto da PostgreSQL alla creazione: se i tipi risolti non
coincidessero con quelli scritti in `COMMENT ON FUNCTION`, `GRANT`, `REVOKE` e nel
`DROP` del rollback, quelle istruzioni fallirebbero con «la funzione non esiste».
Provato: le firme risolvono a `bigint` / `character varying`, e
`obj_description` è valorizzata su entrambe — cioè il `COMMENT` la funzione l'ha
trovata.

⚠️ Corollario per chi le modificherà: la doc auto-generata **scioglie i `%TYPE`**
e mostrerà `bigint`. La firma vera si legge dallo YAML, non da lì.

### 7.3 Come è stato verificato

Tutto in **transazioni annullate**: nessun `liquibase update`, nessun `make db-*`.

| # | Verifica | Esito |
| --- | --- | --- |
| 1 | `guardrail_sql_letterali.py` (3110 changelog), `guardrail_run_on_change.py`, `guardrail_pgtap_preambolo.py` | ✅ — il debito `throws_ok` resta **131 su 131** |
| 2 | I sei blocchi `changes[].sql.sql` **estratti dagli YAML**, in ordine di numero, eseguiti **interi** con `ON_ERROR_STOP=1` | ✅ |
| 3 | ⭐ DDL **+ il pgTAP nuovo nella stessa transazione** | ✅ **12 su 12**, con la 12ª **saltata e dichiarata** (§7.4): da owner il perimetro cieco non esiste |
| 4 | ⭐ **F-2 nei due sensi**: il test cleanup passa oggi (11/11 dal runner vero), **e passa anche con una forzatura in tabella** — cioè il caso che prima lo faceva diventare rosso | ✅ |
| 5 | Mirror CSV: upsert rifatto su **tutte** le righe dei tre file (codici, messaggi, policy FK) | ✅ |

⚠️ **Cosa questa verifica non prova**: girando prima del migrate ci si connette da
**owner**, quindi la **RLS non è stata esercitata**. Dopo l'apply vanno rilanciati
`scripts/testpgtap.sh` sui due file e `scripts/pgtap-baseline.sh anagrafiche vendite`.

### 7.4 ✅ Il debito è CHIUSO — e non serviva un secondo emittente

> ⚠️ **Questa sezione diceva il contrario.** Sosteneva che la prova del
> `SECURITY DEFINER` richiedesse «due emittenti e un secondo contesto operatore,
> che questa fixture non costruisce», e la lasciava come debito. **Era una
> difficoltà immaginata**: la riga la si costruisce dal perimetro che *può*
> scriverla, e poi si sposta soltanto **chi guarda**.

Il pgTAP ha ora **12 asserzioni**, e la dodicesima è la prova che mancava: la
riga non si vede da un perimetro cieco, e `fn_check_annullo_movimento_titolo_iva`
la vede lo stesso, rispondendo `GIA_ANNULLATO` invece di
`MOVIMENTO_NON_TROVATO`. ⛔ Togliendo `SECURITY DEFINER` domani, quel test — e
solo quello — diventa rosso.

#### ⛔ Il GUC non si svuota, si sposta su un id concreto

Misurato il 2026-08-31: `script.fn_check_user_emittente_scope(NULL, …)` risponde
**`true`**, cioè **fail-OPEN**. Svuotare `app.current_user_id` renderebbe visibile
tutto, e il test passerebbe per il motivo sbagliato. Un id **concreto senza
whitelist** risponde `false`, ed è la via giusta — calcolato
(`max(auth_user_id) + 1000`) e non scritto a mano, così non collide quando gli
utenti crescono.

#### ⚠️ E la precondizione si MISURA, non si suppone

Il test controlla per prima cosa che la riga sia davvero invisibile. Se si vede
lo stesso, la RLS a quel ruolo **non si applica** — è il caso di chi gira come
**owner**, dove `relforcerowsecurity = false` — e allora il soggetto del test non
esiste: si **salta dichiarando il motivo**, invece di asserire e prendersi un
verde per costruzione.

> ⭐ **È esattamente cosa è successo nella verifica pre-apply**, e vale la pena
> scriverlo: quel giro si connette come `titodb`, che è **l'owner della tabella**,
> quindi il perimetro cieco non esiste e l'asserzione salta — con il motivo a
> video. ✅ Verificato che nel giro vero non salti: `zeroerp_app` non ha
> `BYPASSRLS` e non è owner.

⚠️ **Un test che salta non presidia niente**: finché non gira da
`scripts/testpgtap.sh`, il `SECURITY DEFINER` resta non verificato. La differenza
con prima è che ora **il file lo dice**, invece di tacere.

### 7.5 📍 Stato al 2026-08-31 — APPLICATO

> ⚠️ Il §7.3 (le verifiche) è stato scritto **prima** dell'apply e resta com'era:
> è la storia del momento in cui i file sono stati consegnati.

| | |
| --- | --- |
| **Migrazione** | ✅ **applicata** — i sei changeSet `20260830-21…26` sono in `databasechangelog`, `EXECUTED`, 2026-08-31 alle 00:19 |
| **Oggetti vivi** | ✅ colonna, indice unique parziale, `CHECK`, **4 funzioni**, **3 trigger**, la vista |
| **Catalogo errori** | ✅ i tre codici (1027-1029) sono in `config.codici_errore` con la loro classe |
| **Seed policy FK** | ✅ la riga è nel DB: `consentito = false`, `dll_command` valorizzato |
| **Doc auto-gen** | ✅ **rigenerata** — la colonna e la vista ci sono |
| **pgTAP** | ⏳ **li lancia Tid** |

#### ⭐ Una previsione dell'analisi ora è MISURATA

Il §5.6 argomentava che l'indice unique parziale **copre già la FK**, quindi la
riga di policy serve a *governarla* e non a farle nascere un indice. Verificato
sul database dopo l'apply:

```sql
SELECT count(*) FROM dbops.vw_fk_senza_indice
 WHERE constraint_name = 'fk_soggetti_titoli_iva_movimenti_annulla';   -- 0
```

La FK **non risulta scoperta**: `apply_fk_index_policy()` non creerebbe un indice
gemello nemmeno a `consentito = true`. Era un argomento, ora è un fatto.

#### 🔴 Il cancello i18n è ROSSO, come previsto

`scripts/check_i18n_keys.py` esce **1**:

```
[X] 5 CHIAVI EMESSE DAL DB e assenti dai locales
    anagrafiche.titoli_iva.annullo_blocco.{non_trovato, non_forzatura,
                                          e_un_annullo, gia_annullato,
                                          plafond_negativo}
```

⚠️ Prima dell'apply **taceva**, perché il controllo legge la **doc auto-gen**,
cioè l'oggetto vivo. È il momento esatto che il piano aveva previsto, e da adesso
**blocca la CI**.

### 7.6 ✅ Documentazione manuale — fatta (2026-08-31)

**Cinque manuali nuovi**, uno per oggetto:

| Oggetto | Cosa porta il manuale |
| --- | --- |
| `trgfn_stiva_movimenti_append_only` | perché si vietano **entrambe** le operazioni e non solo il `DELETE`; i tre rami che diventano irraggiungibili e perché restano; le due strade per `I5` |
| `fn_check_annullo_movimento_titolo_iva` | i cinque motivi in ordine; perché `SECURITY DEFINER` e perché la FK non ha lo stesso problema; perché `PLAFOND_NEGATIVO` sta fra i motivi e non fra gli errori |
| `trgfn_stiva_movimenti_guard_annullo` | le due famiglie di controlli; ⛔ perché quello sul **titolo** è il più importante e **non si vede**; perché quello sull'**importo** è ciò che rende vera la promessa |
| `fn_annulla_movimento_titolo_iva` | perché importo e titolo si **derivano**; perché chiama la check invece di riscriverla; perché la lettura `INVOKER` del passo 3 non è un buco |
| `vw_stiva_movimenti_dettaglio` | la domanda che decide la sede (*da dove si preme quel pulsante?*); un verbo una colonna; il perimetro dal titolo |

**Tre manuali esistenti erano diventati non conformi**, ed è la parte che valeva
più dei cinque nuovi:

| File | Cosa non era più vero |
| --- | --- |
| `trgfn_soggetti_titoli_iva_movimenti_accumulatore` | 🔴 una sezione intera — *«Il caso che si sbaglia se non ci si pensa»*, il movimento spostato da un titolo a un altro — descriveva come **vivo** un caso che ora è **impossibile**: vorrebbe un `UPDATE`. E la motivazione del ricalcolo citava tre casi tutti irraggiungibili. Marcati, non cancellati: il **codice** resta, ed è difesa in profondità |
| `soggetti_titoli_iva_movimenti` | non conosceva né la colonna, né l'append-only, né l'annullo: mancavano due sezioni intere |
| `soggetti_titoli_iva` | diceva che una forzatura è «una riga con il suo motivo» — vero, ma taceva che anche **correggerla** è una riga |

> ⭐ **La più utile delle tre è la prima**, e non per la quantità di testo: era
> l'unica che avrebbe fatto **ragionare su un caso inesistente**. Nulla, nel corpo
> dell'accumulatore, dice che quei rami non arrivano più — è esattamente il tipo di
> cosa che invecchia in silenzio.

✅ **Verificato**: nessun link `/dbzero/…` rotto fra quelli introdotti; toccati
**solo** file sotto `manual/` (le modifiche agli auto-gen nel diff sono la
rigenerazione, non mie — e con essa è rientrata anche la staleness segnalata nel
§5.10, dove il trigger di storico non compariva).

✅ **E l'aggancio c'è**: la doc è stata rigenerata dopo la scrittura dei manuali,
quindi tutte e cinque le pagine auto-generate portano ora il loro
`include-markdown`. ⚠️ L'ordine conta e vale la pena saperlo: lo script scrive il
rimando **solo se il file manuale esiste già**, quindi una rigenerazione fatta
prima dei manuali non li avrebbe agganciati.

⚠️ Cercato anche altrove: **nessuna guida** parla di plafond, e nel brief padre `I7`
l'annullo non figurava fra i residui. Niente altro da sanare.

### 7.7 Cosa resta — il perimetro DB è chiuso

| # | Cosa | Chi |
| --- | --- | --- |
| 1 | ✅ ~~pgTAP~~ — **verdi** (Tid, 2026-08-31) | — |
| 2 | ✅ ~~Rigenerare la doc~~ — **fatta**: i cinque `include-markdown` sono agganciati | — |
| 3 | 🔴 **Le cinque `reason_key` nei locales**, `it.json` **e** `en.json` — l'unica cosa che **blocca la CI** | **FE** |
| 4 | 🟠 `./manage.py genera_error_policies` — senza, il backend non sa mappare i tre codici a 409 / 500 | **BE** |

> ⭐ **Il perimetro DB è CHIUSO.** Schema, codice, seed, presidi e documentazione:
> non resta niente di database in questo cantiere. Le due voci aperte sono di
> altri perimetri, indipendenti fra loro, e si possono fare in parallelo.

## 8. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-29 | Brief nato dalla richiesta di Tid sul piano BE/FE di `I7`. ⭐ Il meccanismo proposto (contro-movimento invece di flag) **non richiede modifiche all'accumulatore**, verificato sul corpo della funzione: la somma non ha filtri. Resta una sola cosa che il BE non può darsi da solo, ed è il **collegamento** fra la riga annullata e quella che la annulla |
| 2026-08-30 | ⭐ **Analisi critica del team DB (§5)**: meccanismo approvato, richiesta riscritta. I due presidi proposti non bastano — mancano l'**importo opposto** (senza, il test del §3 lo rende vero la fixture, non la regola), lo **stesso titolo IVA** (il difetto peggiore: decurta il plafond sbagliato e non solleva niente) e il **SECURITY DEFINER** sul guard, che legge un'altra riga di una tabella con RLS mentre la FK la RLS la scavalca. ⛔ E «append-only», su cui poggia tutto il §1, **non e' presidiato da niente**: il §3 se ne accorge e propone un test, che non impedisce a nessuno di cancellare. Tre decisioni aperte, e i pgTAP passano da tre a sette (nove dopo le decisioni, §6.7) |
| 2026-08-30 | ✅ **Decisioni di Tid (§5.12)**: il registro diventa **solo-aggiunte** per progetto (niente DELETE, niente UPDATE) — cosi' l'argomento del §1 e' vero invece che sperato; **l'annullo non si annulla** (se la forzatura serve ancora se ne scrive una nuova, col suo motivo); e il rifiuto per plafond negativo si vede col **pulsante gia' spento**, non dopo il clic. ⭐ Da li' la forma cambia: una **madre** che deriva importo e titolo, e i guard come difesa contro la scrittura diretta. Piano completo in §6, in nove pgTAP invece di tre. ⛔ Nessuna riga scritta |
| 2026-08-31 | ✅ **Sviluppo eseguito (§7)**: sei changeSet `20260830-21…26`, tre codici errore (1027-1029), il pgTAP nuovo a 11 asserzioni e la correzione del presidio che scadeva. ⭐ Scrivendo sono emerse quattro cose (la quinta l'ha trovata Tid, riga sotto): l'estrazione per la verifica va ordinata **per numero** e non per cartella (la prima metteva la check dopo il guard che la chiama); due titoli dello stesso soggetto non si possono avere, quindi la fixture usa **due soggetti** — e il test ne esce piu' forte, perche' il caso peggiore e' decurtare il plafond di un ALTRO cliente; il doppio annullo esce `P0001` e non `23505`, perche' il guard parla prima dell'indice; e il guard doveva essere `SECURITY DEFINER` anche lui. ⚠️ Manca il test RLS a due emittenti: dichiarato in §7.4, non dimenticato. ⛔ Niente applicato, niente committato |
| 2026-08-31 | ⛔ **Rilievo di Tid: `%TYPE` mancante nelle FIRME.** Nei `DECLARE` c'era ovunque, ma `p_movimento_id` era `bigint` nudo in entrambe le funzioni nuove e la madre dichiarava `RETURNS bigint`. Corretto su firme e ritorno. ⭐ Verificato non rileggendo la firma ma guardando **cosa risolve**: `bigint`/`character varying`, gli stessi tipi che `COMMENT`, `GRANT` e il `DROP` del rollback dichiarano — e `obj_description` valorizzata prova che il `COMMENT` ha trovato la funzione. pgTAP di nuovo 11/11. ⚠️ Sfugge proprio nella firma perche' li' un `bigint` nudo funziona identico e nessun cancello lo vede |
| 2026-08-31 | ✅ **Il debito del SECURITY DEFINER e' CHIUSO (§7.4)**, e non serviva un secondo emittente: la riga si costruisce dal perimetro che la puo' scrivere e poi si sposta **chi guarda**. ⛔ Ma il GUC non si svuota: misurato, `fn_check_user_emittente_scope(NULL, …)` risponde **true**, cioe' fail-OPEN — serve un id concreto senza whitelist, calcolato e non scritto a mano. ⭐ E la precondizione si MISURA: se la riga si vede lo stesso, la RLS a quel ruolo non si applica e il test **salta dichiarandolo**, invece di prendersi un verde per costruzione. E' cio' che succede nella verifica pre-apply, che gira da owner. pgTAP 12/12 |
| 2026-08-31 | 📍 **MIGRAZIONE APPLICATA** (Tid): i sei changeSet sono `EXECUTED` alle 00:19, gli oggetti sono vivi (colonna, indice, CHECK, 4 funzioni, 3 trigger, vista), i tre codici errore a catalogo e la riga di policy FK nel DB; doc auto-gen rigenerata. ⭐ E una previsione dell'analisi e' diventata una misura: la FK **non** risulta in `vw_fk_senza_indice`, cioe' l'indice unique parziale la copre davvero (§5.6). 🔴 `check_i18n_keys.py` e' passato a **rosso** — prima taceva perche' legge la doc auto-gen: e' il momento che il piano aveva previsto. ⏳ pgTAP a carico di Tid |
| 2026-08-31 | ✅ **pgTAP verdi** (Tid) e **documentazione manuale completata** (§7.6): cinque manuali nuovi, uno per oggetto. ⭐ Ma la parte che valeva di piu' sono i **tre esistenti diventati non conformi** — soprattutto quello dell'accumulatore, che descriveva come vivo il caso «un movimento spostato da un titolo a un altro», ora **impossibile** perche' vorrebbe un UPDATE. Marcato e non cancellato: il codice resta come difesa in profondita', ma chi lo legge ora sa che quel ramo non arriva piu'. ✅ Nessun link rotto, toccati solo file sotto `manual/`; nessuna guida parla di plafond e il brief padre non aveva residui sull'annullo. ⚠️ Serve una rigenerazione perche' gli `include-markdown` si aggancino. Il perimetro DB e' chiuso |
| 2026-08-31 | ✅ **PERIMETRO DB CHIUSO.** Doc rigenerata dopo i manuali, quindi i cinque `include-markdown` sono agganciati — ⚠️ e l'ordine conta: lo script scrive il rimando solo se il file manuale esiste gia'. Non resta niente di database in questo cantiere: schema, codice, seed, presidi e documentazione sono completi. Aperte solo le due voci di altri perimetri (cinque `reason_key` al FE, `genera_error_policies` al BE) |
