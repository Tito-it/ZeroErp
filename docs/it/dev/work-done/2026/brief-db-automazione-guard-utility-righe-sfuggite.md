# Brief DB — La guard utility→tipo_ruolo passa al CSV

> **Origine**: ultimo rosso del baseline `dbops` —
> `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql`.
> **Stato**: ✅ **CHIUSO il 2026-08-18** lato DB. Da applicare: `20260818-56`
> (`20_code/dbops`) e `20260818-57` (`80_data`) + il CSV.
> ⛔ Niente applicato: le verifiche sono girate in transazioni chiuse in `ROLLBACK`.

---

## 1. Il rosso era due difetti sovrapposti

Il file era in baseline classificato `ERRORE_FIXTURE`. Non lo era.

| | Cosa | Sintomo | Esito |
| --- | --- | --- | --- |
| a | **Permesso** | «bisogna essere proprietari della relazione `categorie_clienti_listini`» | marcatore `-- pgtap-runner: owner` |
| b | **Difetto vero** | il test 2 restava rosso **anche** come owner | `20260818-56` + `-57` |

⚠️ **La classificazione sbagliata ha nascosto (b) per mesi**, ed è un modo di
sbagliare che si ripete: un file che muore nel *fixture* non esegue nessuna
asserzione, quindi sembra un problema del test. Qui bastava rigirarlo come owner
per vedere che sotto al permesso c'era dell'altro.

## 2. (a) Il permesso

Il test chiama `dbops.fn_apply_automazione_guard_utility_tipo_ruolo('AUTO', false)`,
che fa `DROP`/`CREATE TRIGGER` **su tutte le tabelle configurate**, non solo su
quella in esame — il primo rosso arrivava infatti da
`anagrafiche.categorie_clienti_listini`, che il test non nomina nemmeno.

Applicare un'automazione è un'operazione di migrazione (gira in contesto
`ci_apply`, `90_end`), non dell'applicazione: il ruolo applicativo il privilegio
`TRIGGER` su quelle tabelle non ce l'ha e **non deve averlo**. È il caso da
marcatore, stessa natura di `anagrafiche/test-fn-create-indirizzo-v1`.

## 3. (b) La configurazione era ferma a sei mesi fa

`dbops.automazione_guard_utility_tipo_ruolo` era popolata da
`fn_seed_automazione_guard_utility_tipo_ruolo`, che **rileva dallo schema e
scrive**, chiudendo con `ON CONFLICT (schema_name, table_name) DO NOTHING`.

⭐ **Quel `DO NOTHING` è il difetto strutturale**: una riga scritta una volta non
si raddrizzava mai più. La configurazione è rimasta ferma al 2026-02-16 mentre
lo schema andava avanti. Misurato il 2026-08-18, delle 7 righe **4 descrivevano
tabelle che non qualificano più**:

| Riga | Cosa è successo |
| --- | --- |
| `bank_branches`, `fornitori`, `vettori` | hanno perso la colonna `utility_id` |
| `reseller` | la tabella è stata **rinominata `resellers`** (che comunque non ha `utility_id`) |

e una quinta, `emittenti_fiscali_utilities`, nominava `soggetto_ruolo_id` —
colonna che **quella tabella non ha**: la sua è `emittente_soggetto_ruolo_id`,
ed è già quella che il trigger vivo usa.

### ⚠️ Nessuna tabella era però rimasta scoperta

Va detto perché cambia la gravità, e perché nel corso dell'analisi me ne ero
fatto un'idea sbagliata. Le uniche due tabelle che **oggi** qualificano davvero
(`categorie_clienti_listini`, `emittenti_fiscali_utilities`) hanno entrambe il
loro trigger, corretto. Il danno non era una guard mancante: era una
configurazione che **dichiarava protezioni inesistenti** — cinque righe
`enabled = true` che `fn_apply_*` scartava in silenzio (filtra su
`LIKE '%_soggetto_ruolo_id'`, che il nome generico non passa) — e un catalogo
che diceva una cosa mentre il database ne faceva un'altra, **col database che
aveva ragione per caso**.

### La coincidenza che aveva confuso le acque

Il `20260216-06` faceva la bonifica giusta (droppa i trigger, spegne le righe col
ruolo generico), ma è `runOnChange: false` ed è girato **in mezzo** al
popolamento — `data_insert` alla mano:

```text
15:30  seed  ->  clienti, emittenti_fiscali_utilities
15:41  -06   ->  spegne clienti          <- l'unica col generico che esisteva
15:47..15:53 seed -> bank_branches, fornitori, reseller, vettori   <- mai viste
```

È la regola delle «due mosse» vista dal lato che non si prevede: un changeSet di
bonifica `runOnChange: false` fotografa lo stato di **quel minuto**. Ma è la
causa prossima, non quella vera — quella vera è che la configurazione la
scriveva del codice.

## 4. La soluzione: il CSV, non una bonifica SQL

⚠️ **Prima avevo scritto una bonifica SQL** (`UPDATE`/`DELETE` in `80_data`).
Tid l'ha fermata, e la regola è quella di casa:

> «tutti i seed devono girare da CSV — un misto di script SQL e CSV lo abbiamo
> verificato diverse volte, fa casino e non si applica»

Ed è documentata in `.codex/AGENTS.md` («I dati di `80_data` si cambiano dal CSV,
non con `UPDATE` diretti»): mirror e SQL divergono fra sviluppo e CI, perché il
mirror è `runOnChange` e ri-legge a ogni migrate mentre l'SQL gira una volta sola.

⚠️ E c'era un indizio che avrei dovuto leggere prima: `automazione_guard_utility_tipo_ruolo`
era **l'unica** tabella `automazione_*` di `dbops` senza CSV. Le sorelle —
`automazione_chiusura_scadenze`, `automation_scope`, `automation_rules_tbl`,
`automation_lock_columns`, `automation_fk_exclusions` — sono tutte mirror di un
file in `80_data/sql/dbops/`.

### `20260818-56` — il seed smette di scrivere (`20_code/dbops`)

Resta la metà utile: percorre gli schemi in scope, trova le tabelle che
qualificano e, se una non è nel CSV, **lo dice con un `RAISE NOTICE`**. Non
scrive niente. È l'opt-in esplicito, la stessa forma di `dbops.fk_index_policy`.

⚠️ Firma e punto di chiamata invariati: `90_end/ci_apply/20250627-31` continua a
chiamarla e **non va toccato**. Era l'altra via possibile — togliere la riga da
lì — ed è peggiore: quel changeSet esegue in fila altre sette automazioni, e
riscriverlo per toglierne una avrebbe messo a rischio le altre sette per un
motivo che non le riguarda.

⚠️ Il `NOTICE` è un compromesso dichiarato: si legge se lo si va a cercare. La
sede giusta per una diagnosi è una vista accanto alle altre di `dbops`; non è
stata aggiunta per non allargare il perimetro, ed è il primo posto dove tornare
se quella segnalazione dovesse servire davvero.

### `20260818-57` + CSV — la configurazione diventa un mirror (`80_data`)

`80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv`, sette righe, `id`
conservati. **Due accese** e **cinque spente**:

```text
4   emittenti_fiscali_utilities  emittente_soggetto_ruolo_id  t
11  categorie_clienti_listini    emittente_soggetto_ruolo_id  t
3   clienti        soggetto_ruolo_id  f   qualifica, ma ruolo generico
5   bank_branches  soggetto_ruolo_id  f   non ha più utility_id
7   fornitori      soggetto_ruolo_id  f   non ha più utility_id
9   vettori        soggetto_ruolo_id  f   non ha più utility_id
8   reseller       soggetto_ruolo_id  f   tabella rinominata resellers
```

⚠️ **Perché spente e non tolte.** `loadUpdateData` non cancella: togliere le
righe dal CSV le lascerebbe sul database di sviluppo **esattamente come stanno
oggi**, `enabled = true` e con colonne che non esistono, e il mirror non potrebbe
farci niente. Portarle nel CSV spente è l'unico modo di convergere restando
dentro alla regola: niente `DELETE`, niente SQL accanto al mirror, e sviluppo e
database ricostruito finiscono nello stesso stato.

E non è un ripiego: una riga spenta **dice qualcosa** — che quella tabella è
stata considerata ed è fuori — cosa che l'assenza della riga non direbbe. È la
stessa scelta del `-06` su `clienti`, e la stessa logica di
`dbops.fk_index_policy`, dove `consentito = false` è un dato e non un vuoto.

⚠️ Cancellarle davvero resta possibile ed è una **decisione di Tid**: è l'unico
`DELETE` che AGENTS ammette accanto a un mirror CSV. Non l'ho scritto perché
cancella dati e perché quelle righe, spente, non fanno danno.

⚠️ `meta` **non** è nel CSV di proposito: è provenienza (chi ha seedato, quando,
perché è stata spenta), non configurazione. Lasciandola fuori, il mirror non
cancella la storia che le righe si portano dietro dal 2026-02-16.

## 5. Il test, riscritto

Prima i test 1 e 2 chiamavano il seed e poi verificavano che la riga ci fosse:
**verificavano il seed contro sé stesso**. Ora la sorgente è il CSV, quindi:

1. a catalogo `emittenti_fiscali_utilities` è configurata e abilitata;
2. …con le colonne che la tabella ha davvero ← *è il test che ha trovato tutto*;
3. **ogni riga abilitata nomina colonne che esistono davvero** (nuovo — si
   verifica contro il catalogo di sistema, non contro una costante);
4. l'apply crea il trigger;
5. il trigger è `BEFORE INSERT/UPDATE`;
6. **chiamare il seed non cambia la configurazione** (nuovo — presidia la regola;
   confronta l'impronta `md5` del contenuto, non il conteggio: un seed che
   inserisse e cancellasse lascerebbe il conteggio invariato e passerebbe).

## 6. Verifiche (tutte in transazione chiusa in `ROLLBACK`)

| Verifica | Esito |
| --- | --- |
| CSV vs loader | 7 righe, colonne allineate alla dichiarazione |
| configurazione dopo il mirror | 2 accese e corrette, 5 spente |
| test 2, 3, 6 | **verdi** |
| `fn_apply_*` dopo il mirror | installa i trigger delle sole abilitate |
| suite `dbops` | 1 rosso su 16, quello noto — nessuna regressione |

## 7. Cosa resta

1. **Un `migrate`.** Finché non gira, il file resta rosso: è in
   `baseline-rossi.tsv` con la causa riclassificata da `ERRORE_FIXTURE` ad
   `ASSERZIONE` e con scritto quando va tolto. **Al migrate si toglie la riga.**
2. Il `NOTICE` del `-56` segnalerà `anagrafiche.billing_account`: ha `utility_id`
   ma solo la colonna di ruolo generica, quindi non qualifica per la regola del
   `-06`. Se un giorno si volesse coprirla, la strada è aggiungere la riga al
   CSV — non toccare il filtro.
