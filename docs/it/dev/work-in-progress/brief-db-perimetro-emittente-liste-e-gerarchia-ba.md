# Il perimetro emittente non è presidiato — liste e alberi di billing account

> **Cos'è.** Il brief di **due buchi distinti** nello stesso presidio: il
> perimetro dell'emittente fiscale. Uno sta nell'**accesso alle liste**, l'altro
> nella **gerarchia dei billing account**. Sono separati per causa e per
> soluzione, ma stanno insieme perché **si coprono a vicenda**: finché uno è
> aperto, chiudere l'altro non basta.
>
> **Origine.** Emersi il **2026-08-17** analizzando la richiesta «filtrare i
> gruppi fatturabili per cliente»
> ([brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](brief-db-dash-competenza-gruppi-cliente-e-ricerca.md)).
> Sono stati messi qui perché sono cantieri loro: toccano l'anagrafica e
> l'accesso, non la dashboard.
>
> **Stato al 2026-08-17: nulla eseguito.** Nessun changeSet, nessuna migrazione,
> nessun seed. Diagnosi verificata contro il codice, **decisioni prese**, piano
> di applicazione in **§7-bis**.
>
> ⭐ **Le decisioni prese** — sei, con Tid il 2026-08-17, registrate in **§7**:
>
> 1. **solo il super admin è legittimamente multi-emittente.** Un operatore
>    senza riga in `config.user_emittenti_fiscali` è un **errore di
>    configurazione**, non uno stato del modello → il presidio va **a monte**,
>    nella catena canonica dello scope (**P-2a**), e da decisione di prodotto
>    diventa una **correzione**;
> 2. **il super admin non si obbliga in generale**: lo obbliga la singola lista
>    che non sa reggere più emittenti, via flag `multi_emittente` sul catalogo
>    (**P-2b**), default `false`, con **P-4** come prezzo del biglietto;
> 3. **il flag si accende solo dal seed**, mai da un interruttore in
>    interfaccia, e solo insieme al lavoro che lo rende vero;
> 4. **non ovunque serve lo stesso rimedio**: cancello sulle liste, **etichetta
>    di perimetro** su contatori e ricerche, dettaglio singolo fuori (**P-2c**);
> 5. **nessuna bonifica dei dati** — sono di test. Conseguenza: **i guard si
>    scrivono senza eccezioni per il pregresso** (P-1, P-3), e sono loro a far
>    emergere i casi uno alla volta;
> 6. **l'interruttore in interfaccia va impedito, non sconsigliato**: tre strati
>    in P-2b — permesso a livello di colonna, test in CI, motivo nel file.
>
> 🔴 **Il buco B (§3) resta aperto come lavoro**, e produce una fattura emessa da
> un emittente che l'operatore non può vedere. È il più grave dei due, ed è
> anche il più facile da chiudere: quello che resta in §7 è attuazione, non
> forma.

---

## 1. La tesi, in due frasi

> **Il modello è mono-emittente al *massimo*, non al *minimo*.** Un utente non
> può avere due emittenti, ma può non averne nessuno — e allora li vede tutti.
>
> **La gerarchia dei billing account non conosce l'emittente.** L'unico
> controllo che presidia la relazione padre/figlio guarda il codice fiscale, e
> il codice fiscale è identico proprio nei casi in cui servirebbe dire di no.

---

## 2. Buco A — lo scope emittente ha **tre** stati, e il terzo non è voluto

### 2.1 La regola stretta c'è

`config.user_emittenti_fiscali` ha `UNIQUE(auth_user_id)`: **al massimo una riga
per utente**, quindi al massimo un emittente. Il commento in
`script.fn_resolve_emittente_for_user` lo chiama esplicitamente *«Modello
1-a-1»*.

### 2.2 Ma la risoluzione dello scope ha tre esiti

Da `script.fn_get_emittenti_scope_pk_ids` (semantica: `NULL` = tutto, `{}` =
nessuno, array = whitelist):

| Chi | Scope risultante |
| --- | --- |
| Nessuna identità OPERATORE attiva | `{}` — nessun accesso ✅ |
| Super admin | `NULL` — **tutti** gli emittenti ✅ voluto |
| Operatore **con** riga | array di **1** elemento ✅ |
| Operatore **senza** riga | ⚠️ `NULL` — **tutti** gli emittenti |

Il quarto caso non è nascosto: la descrizione della tabella lo dichiara —
*«se l'utente non ha righe può operare su TUTTI gli emittenti»* — e la funzione
ha il commento *«NULL (whitelist vuota) = nessuna restrizione»*.

### 2.3 Perché è un problema

⭐ **Decisione Tid, 2026-08-17**: *solo* il super admin è legittimamente
multi-emittente. Quindi il quarto caso della tabella **non è uno stato del
modello: è un errore di configurazione** che il sistema oggi non rileva e non
segnala.

La mono-emittenza **non è un invariante del sistema**: è la conseguenza di
*avere* una riga. Dimenticare la riga per un operatore nuovo non produce né un
errore né un blocco — produce un operatore che vede tutti gli emittenti, **e
che dai dati è indistinguibile da un super admin**.

Le aree in cui questo pesa (elenco di Tid):

- situazione **aperte**
- **competenza** fatturazione
- **backlog** fatturazione
- **lotti**

Sono tutte liste che **non hanno un filtro emittente**. Nel quarto caso
mescolano emittenti senza dirlo, e nessuna riga a video dichiara da quale
emittente arriva.

### 2.4 Il motore per obbligare esiste già — manca il cancello

L'«emittente attivo» è implementato e completo:

- viaggia nel **JWT** e il backend lo scrive nella GUC `app.current_emittente_id`
  a ogni richiesta (`apps/core/api/jwt_audit_authentication.py`);
- c'è l'endpoint per sceglierlo (`emittente_attivo_views.py`,
  `emittente_attivo_service.py`, `emittente_attivo_repository.py`);
- `fn_get_emittenti_scope_pk_ids` lo **interseca** con lo scope di diritto, in
  un'uscita unica: `universo ∩ {X} = {X}`, e whitelist senza X → `{}`.

Quindi anche il super admin, scegliendo un emittente attivo, **diventa
mono-emittente**. Il pezzo che manca non è il meccanismo: è che **nessuno
pretende** che quelle aree girino con esattamente un emittente.

### 2.5 ⭐ La prova che «whitelist vuota = vede tutto» è un residuo, non una scelta

C'è un'**asimmetria fra lettura e scrittura** che da sola dice da che parte
stia la verità.

| Funzione | Utente con identità OPERATORE, non super admin, **senza riga** | |
| --- | --- | --- |
| `fn_check_user_can_create_ba` (**scrittura**) | **false** — non può creare un BA | ✅ fail-closed |
| `fn_get_emittenti_scope_pk_ids` (**lettura**) | `NULL` = **vede tutti gli emittenti** | ⚠️ fail-open |
| `fn_check_user_emittente_scope` (**lettura**) | `true` — *«nessuna restrizione»* | ⚠️ fail-open |

Cioè: **lo stesso utente non può creare un billing account, ma può vederli
tutti.** Il lato scrittura tratta già la riga mancante come «non configurato»;
il lato lettura la tratta come «nessun limite». Le due letture non possono
essere entrambe intenzionali.

E c'è un **precedente esplicito nella stessa catena**: il commento di
`fn_get_emittenti_scope_sr_ids` dice *«Post 2026-08-04: mappatura a vuoto → `{}`
e non `NULL` (fail-closed su emittente attivo inesistente)»*. La stessa
correzione, sullo stesso principio, è già stata fatta un ramo più in là. Qui è
rimasta indietro.

⚠️ **Corollario pratico**: `fn_scope_ef_whitelist_via_efba` e `via_sr` — gli
adapter usati dalle policy RLS — **derivano** dallo scope e trattano già
`cardinality = 0` come «nessun accesso». Correggere la funzione canonica li
sistema **per costruzione**, senza toccarli.

---

## 3. Buco B — un albero di billing account può attraversare due emittenti

### 3.1 Lo scenario, com'è stato posto

Soggetto **Tid**, P.IVA X. Da lì:

- 4 billing account sotto l'emittente **Tito**
- 4 billing account sotto l'emittente **Pippo**

Questo è **legittimo e va sostenuto**: un soggetto può essere cliente di più
emittenti. Due alberi separati, uno per emittente, nessuno che si tocca.

### 3.2 Ma i controlli non distinguono i due alberi

Tutti e otto i BA hanno lo **stesso** `id_fiscale_univoco_cf_piva`, perché il
soggetto è uno.

L'unico controllo che presidia la relazione padre/figlio è
`anagrafiche.trgfn_billing_account_guard_normalize` §2.2, e confronta **solo il
codice fiscale**. Con otto BA che condividono la stessa P.IVA, quel guard
**passa sempre** — anche mettendo un BA di *Pippo* come padre di un BA di
*Tito*.

Non è che manca un guard: è che quello che c'è **dice «ok» proprio nel caso in
cui servirebbe un «no»**.

Gli altri trigger di `billing_account` non coprono il caso: auto-riferimento,
`valido_dal` obbligatorio, coerenza CF, guard dissociazione, coerenza
soggetto↔istanza, normalizzazione, audit, storico. **Nessuno guarda l'emittente
del padre.** (Verificato sull'elenco trigger della doc auto-gen.)

### 3.3 E si costruisce per sbaglio, non solo in teoria

- L'emittente di un BA nasce dal trigger `anagrafiche.trgfn_billing_account_link_ef`,
  che lo prende **dall'operatore che lo crea** (`fn_resolve_emittente_for_user`),
  con `is_default = false`. Il mapping è `UNIQUE(billing_account_id)`: uno e uno
  solo per BA.
- La policy RLS di **INSERT** su `billing_account` è **gate-only**: verifica
  solo `ruolo_applicativo = 'OPERATORE'`. Non poteva essere altrimenti — il
  mapping all'emittente lo crea un trigger `AFTER INSERT`, quindi una
  `WITH CHECK` sullo scope rifiuterebbe ogni BA nuovo.
- Il vincolo referenziale su `parent_account_id` è un controllo di integrità:
  **non applica le policy RLS** (comportamento standard di PostgreSQL — da
  confermare con un pgTAP, ma la decisione non ci poggia: l'assenza del guard di
  §3.2 basta da sola).

Messe insieme: **un operatore di Tito può impostare come padre un BA di Pippo
che non è autorizzato nemmeno a vedere.** Nessun errore, nessun avviso.

### 3.4 Cosa succede poi — ed è la parte grave

`vendite.fn_build_fattura_key` prende l'emittente **dal padre**:
`fn_get_emittente_fiscale_id(COALESCE(parent_account_id, billing_account_id))`.

Quindi il lavoro fatto sotto **Tito** finisce su una fattura **emessa da
Pippo**: un documento che l'operatore che l'ha generato **non può vedere**, in
un registro di numerazione che non è il suo. Si scopre a fine mese.

### 3.5 La regola giusta, e quella sbagliata che le assomiglia

| | |
| --- | --- |
| ❌ *«un soggetto sta sotto un solo emittente»* | **Falso e da non imporre.** Lo scenario §3.1 è legittimo |
| ✅ *«un singolo albero padre/figlio non attraversa due emittenti»* | **Questa è la regola.** Tid può avere due alberi; quello che non deve esistere è **un** albero con un piede in Tito e uno in Pippo |

---

## 4. Buco C (minore) — il guard della coerenza fiscale è fail-open sul NULL

`trgfn_billing_account_guard_normalize` §2.2 confronta con `IS DISTINCT FROM`, e
`anagrafiche.soggetti.id_fiscale_univoco_cf_piva` è **nullable**.

Due BA **entrambi senza** codice fiscale passano il controllo anche se sono
soggetti diversi: `NULL IS DISTINCT FROM NULL` è falso, quindi il raise non
scatta. Un albero fra soggetti diversi diventa costruibile.

È il caso classico del NULL in una chiave, ed è piccolo solo finché i BA senza
codice fiscale sono pochi.

---

## 5. Perché A e B stanno nello stesso brief

Si coprono a vicenda, e questo è il motivo per cui chiuderne uno solo lascia il
problema in piedi:

- **Se l'accesso fosse davvero mono-emittente (A chiuso)**, un albero misto
  resterebbe costruibile ma l'operatore vedrebbe solo la sua metà: la fattura
  sbagliata nascerebbe lo stesso, semplicemente nessuno la vedrebbe nascere.
- **Se l'albero fosse omogeneo (B chiuso)**, un operatore multi-emittente per
  sbaglio continuerebbe a lavorare su emittenti misti in liste che non lo
  dichiarano.

E c'è un guadagno che si ottiene solo chiudendo B: **l'emittente della commessa
e quello della fattura tornano a coincidere** per la parte che dipende
dall'albero. Resta fuori un solo caso, quello dell'emittente **forzato a mano**
alla creazione della commessa (`fn_get_or_create_commessa` accetta un
`p_emittente_soggetto_ruolo_id` esplicito che vince su tutto) — misurato come
DL-1 nell'altro brief.

---

## 6. Cosa si propone

> **Proposta, non decisione.** Le domande aperte sono in §7.

### P-1 — Guard «albero omogeneo per emittente», in **due movimenti**

Il guard deve presidiare due movimenti, non uno. Il secondo è quello che si
dimentica sempre, e da solo rende inutile il primo:

1. **si imposta o si cambia `parent_account_id`** → padre e figlio devono avere
   lo stesso emittente;
2. **si cambia l'emittente di un BA** (riga in
   `anagrafiche.emittenti_fiscali_billing_account`) → non deve spaccare un
   albero esistente, né verso il padre né verso i figli.

Note di costruzione:

- il movimento 2 vive su una tabella **diversa** da quella del movimento 1: due
  trigger, non uno;
- `fn_check_*` puro per la verifica, `fn_guard_*` per il fail-fast, secondo le
  convenzioni;
- errore con **codice registrato**, mai `E_GENERICO`; nuovo codice = solo append
  al CSV dei messaggi, mai un loader upsert nuovo;
- ⚠️ prima di aggiungere un `BEFORE UPDATE` su `billing_account`: **grep dei
  pgTAP esistenti**. Un guard restrittivo che entra rompe le fixture che
  scrivevano liberamente, e il rosso sembra una regressione altrui.

#### ⛔ Il guard si scrive **come se i dati fossero già giusti** · *decisione Tid, 2026-08-17*

> **Nessuna eccezione, nessuna clausola per il pregresso, nessun override.**

Il guard afferma l'invariante e basta: *padre e figlio hanno lo stesso
emittente*. Non conosce la storia della riga, non chiede se il difetto c'era
prima, non ha un ramo «era già così, lascia passare».

**Conseguenza, voluta:** un albero misto preesistente diventa **immodificabile**
finché qualcuno non lo sistema. Toccare una qualunque colonna di quel BA fa
scattare l'errore.

**E questa è la proprietà buona, non il prezzo da pagare.** Un dato sbagliato
che blocca **si annuncia**, nel momento in cui qualcuno ci mette le mani, con un
messaggio che ne nomina la causa. Un dato sbagliato tollerato continua a
produrre in silenzio la fattura emessa da un emittente invisibile (§3.4), e
quella non si annuncia mai. Fra le due, la prima si corregge in dieci minuti a
mano; la seconda si scopre a fine mese e non si sa da dove venga.

⚠️ **Una clausola di grandfathering sarebbe un fallback transitorio** — la cosa
che in questo progetto non si fa. E i fallback transitori non sono mai
transitori: nessuno torna a toglierli, perché toglierli fa rumore ed è
esattamente il rumore che erano stati messi lì a sopprimere.

⚠️ **Niente GUC di override.** `script.trgfn_lock_columns` ne ha uno
(`zeroerp.allow_lock_columns_override`) ed è il precedente che verrà citato per
chiederne uno anche qui: **non vale**. Quello protegge una colonna da modifiche
accidentali e prevede una manutenzione legittima; questo protegge un invariante
di dominio da cui dipende su quale fattura finisce il lavoro. Un invariante con
l'interruttore non è un invariante.

**Il collegamento con la decisione «niente bonifica» (§7)** è diretto e non è
una contraddizione: i dati non si bonificano *in blocco e adesso*, si sistemano
*uno alla volta, quando si presentano*. Il guard è ciò che li fa presentare.

### P-2a — Fail-closed nella catena canonica dello scope ⭐ *correzione, non decisione*

Dopo la decisione di §2.3, questo non è più un cambio di postura: è **allineare
la lettura alla scrittura** (§2.5). Due punti, e basta:

| Funzione | Oggi | Deve diventare |
| --- | --- | --- |
| `script.fn_get_emittenti_scope_pk_ids` | non-super-admin senza riga → `NULL` (tutto) | → `'{}'` (nessuno) |
| `script.fn_check_user_emittente_scope` | stesso caso → `true` | → `false` |

Il super admin continua a passare dal suo ramo (`fn_is_super_admin` → `NULL` =
universo) e **non è toccato**. `fn_get_emittenti_scope_sr_ids` e i due adapter
`fn_scope_ef_whitelist_via_*` ereditano la correzione senza modifiche (§2.5).

**Perché è la strada giusta e non il cancello sulle liste**: il presidio sta in
**un punto solo**, vale per ogni consumatore presente e futuro — liste, viste
RLS, ricerca universale — e non va ricordato ogni volta che si scrive una lista
nuova. Un cancello per-lista è una regola che qualcuno prima o poi dimentica.

⚠️ **Va fatto insieme, o non è fatto:**

1. **DL-A prima di applicare** (§7): contare gli utenti con identità OPERATORE,
   non super admin, **senza** riga. Dopo la correzione **non vedono più nulla**
   — che è il comportamento corretto, ma va anticipato aggiungendo le loro
   righe, non scoperto da una segnalazione;
2. **`COMMENT ON TABLE config.user_emittenti_fiscali` va riscritto.** Oggi
   dichiara *«se l'utente non ha righe può operare su TUTTI gli emittenti»*:
   dopo la correzione è **falso**, e una descrizione falsa nella doc auto-gen è
   peggio di nessuna descrizione;
3. valutare una **vista di diagnostica** (`dbops.vw_*`) che elenchi gli
   operatori senza riga: trasforma un errore silenzioso in una cosa che si
   guarda.

### P-2b — Il multi-emittente è una **capacità dichiarata dalla lista** ⭐ *decisione Tid, 2026-08-17*

Con P-2a applicata, **l'unico attore multi-emittente rimasto è il super admin**.
E la decisione presa è che **non lo si obbliga a scegliere in generale**: lo
obbliga la **singola lista che non sa reggere più emittenti**.

> Il super admin non è vincolato dal sistema. È vincolato dalla lista in cui sta
> entrando, e solo finché quella lista non sa mostrare da quale emittente
> arrivano le righe.

Non è una sfumatura: sposta la domanda da *«che tipo di utente sei»* a *«questa
schermata è in grado di dirmi cosa sto guardando»*. La seconda è una proprietà
verificabile della lista; la prima è una convenzione che invecchia.

#### La forma

Un flag sul catalogo delle liste, che è già la sede di ogni altra proprietà
della lista:

```sql
ALTER TABLE ui.lista_definizione
    ADD COLUMN multi_emittente boolean NOT NULL DEFAULT false;
```

| Valore | Significato | Effetto quando lo scope ha **più di un** emittente |
| --- | --- | --- |
| `false` (default) | la lista **non** sa reggere più emittenti | chiede di sceglierne uno prima di entrare |
| `true` | la lista dichiara di saperlo reggere | risponde normalmente |

**Perché il default è `false`.** Una lista nuova nasce **non certificata**, e
nessuno deve ricordarsi di dichiararla. Il contrario — default `true` con un
elenco di eccezioni — è la forma che smette di funzionare al primo che si
dimentica: diventa una lista di eccezioni che nessuno mantiene, invece di un
registro di debito che cala.

**Copertura verificata (2026-08-17):** tutte e quattro le aree indicate sono già
nel catalogo, quindi il flag le raggiunge senza inventare un secondo registro —
`vendite.lotti` (12), `vendite.dash_aperto_documenti` (39),
`vendite.dash_backlog_documenti` (40), `vendite.dash_competenza_errori` (41),
`vendite.dash_competenza_gruppi` (42), `vendite.dash_competenza_commesse` (43).
Su **44 liste** in catalogo.

#### Il prezzo del biglietto per mettere `true` ⭐

Questa è la parte che rende il flag una regola e non un interruttore:

> **Una lista può dichiarare `multi_emittente = true` solo se espone
> l'emittente nella riga.**

Cioè **P-4 non è più una proposta indipendente: è la condizione di ammissione**.
Una lista che mescola emittenti senza dire quale sia quale non è
«multi-emittente»: è una lista ambigua con un flag ottimista addosso. Il flag
diventa così qualcosa che si **guadagna** facendo un lavoro, non qualcosa che si
mette per far sparire un fastidio.

È anche una regola **verificabile a macchina**: un controllo può confrontare
l'elenco delle liste con `multi_emittente = true` contro quelle che hanno una
colonna emittente in `ui.lista_colonna`.

#### ⛔ Che l'interruttore non nasca: **tre strati, non un commento** · *decisione Tid, 2026-08-17*

La decisione «solo dal seed, mai da interfaccia» è stata presa (§7, decisione
3). Ma una decisione scritta in un brief è una raccomandazione, e le
raccomandazioni vengono infrante — succede in questo stesso progetto, ed è il
motivo per cui esistono gli hook e i guardrail. Servono **cancelli**, in ordine
di forza:

**Strato 1 — il permesso (il solo che non si può aggirare scrivendo codice)**

Togliere all'applicazione il diritto di scrivere quella colonna. In PostgreSQL
il privilegio `UPDATE` a livello tabella copre tutte le colonne: per restringere
serve revocarlo e riconcederlo **per colonna**, elencando quelle lecite. Il
migrate gira come owner e non è toccato; il seed continua a funzionare.

Il costo è una lista di colonne da mantenere — ed è un costo che **paga**: una
colonna nuova nasce **non scrivibile** finché qualcuno non la concede
esplicitamente. Fail-closed nella direzione giusta.

⚠️ **Da verificare prima**: che nessun changeSet di `90_end` ri-conceda `UPDATE`
a livello di tabella su `ui.lista_definizione` (in quella cartella ci sono già
diversi `grant-*-app`). Un grant di resync più avanti nella timeline
annullerebbe la revoca **in silenzio**, e su dev non si vedrebbe.

**Strato 2 — il test che lo blocca in CI**

Un test che asserisce che `multi_emittente` **non** compare in `_CREATE_KEYS`
né in `_UPDATE_KEYS` di `apps/ui/services/lista_definizione_admin_service.py`.
Costa tre righe, gira a ogni PR, e fallisce con un messaggio che spiega il
perché invece di far scoprire il problema in esercizio.

È lo strato che serve davvero **il giorno del refactor**, quando qualcuno
riscrive il servizio admin in buona fede e riallinea le whitelist «per
coerenza».

**Strato 3 — il perché, scritto accanto alla whitelist**

Non nel brief: **nel file**, sulla riga sopra. Il commento locale dichiara
*«Tutti i campi sono mutabili (nessun immutabile per design)»*, quindi
`multi_emittente` è l'**unica eccezione a una convenzione esplicita** — e
un'eccezione senza motivo scritto viene tolta dal primo che passa, convinto di
star sistemando una svista.

> I tre strati non sono alternative. Il primo impedisce, il secondo avverte, il
> terzo spiega. Se ne resta solo uno, che sia il primo.

#### Cosa il flag **non** è

⚠️ **Non è un permesso.** Non decide *cosa* un utente può vedere — quello lo
decide lo scope (P-2a) e la RLS. Decide se una schermata è **leggibile** nella
condizione in cui sta per essere aperta. Chi lo implementa come un controllo di
autorizzazione crea una seconda via d'accesso accanto a quella vera, ed è
esattamente il tipo di duplicazione che poi diverge.

⚠️ **Non si attiva quasi mai.** Con P-2a lo scope di un operatore ha cardinalità
1 **sempre**: il cancello non scatta e la funzione è invisibile al 99% degli
utenti. Riguarda solo chi ha davvero l'universo davanti.

⚠️ **Il cancello va scritto sulla cardinalità dello scope, non sul ruolo.** «Se
non è super admin» sembra equivalente e non lo è: si appoggia a un'identità
invece che al perimetro effettivo, e smette di proteggere il giorno in cui nasce
un terzo caso.

#### Note di costruzione

- **Dove si legge**: `ui.fn_resolve_lista_config` è già il risolutore della
  configurazione di lista e restituisce un envelope JSON — aggiungere la chiave
  è additivo e non rompe i consumatori;
- **Dove si applica**: **un solo punto** lato BE (un helper in `apps/core`, non
  un controllo per endpoint), che traduce il rifiuto in un **codice errore
  registrato** con la sua azione UI in `error_policies.py`. Mai `E_GENERICO`, e
  nuovo codice = **solo append al CSV**, mai un loader upsert nuovo;
- **Seed**: `lista_definizione.csv` guadagna una colonna → il loader
  `loadUpdateData` va **esteso in place** (è il mirror vivo del CSV),
  **backfillando prima**. E `CAMPI_DEF` in `scripts/gen_seed_lista.py` va
  aggiornato, o il generatore riscriverà il CSV senza la colonna nuova;
- ⚠️ **Ordine Liquibase**: l'`ALTER TABLE` sta in `00_schema`, il
  `CREATE OR REPLACE` di `fn_resolve_lista_config` in `20_code`, e
  `changelog-autogen.yaml` **mescola le due cartelle ordinando per numero**. La
  funzione che legge la colonna deve avere un numero **più alto** di quello che
  la crea, o l'apply su un DB ricostruito fallisce e su dev no;
- **Dashboard**: **niente flag lì.** Il rimedio per un aggregato è diverso ed è
  in **P-2c**. `ui.dashboard_definizione` resta fuori dal cancello.

### P-2c — Le altre superfici: cancello dove serve, **etichetta** dove basta ⭐ *decisione Tid, 2026-08-17*

Una lista non è l'unico posto dove i dati compaiono. Le altre superfici hanno lo
stesso problema di leggibilità, **ma non lo stesso rimedio** — e applicare il
cancello ovunque sarebbe più semplice da scrivere e peggio da usare. Una
funzione fastidiosa è una funzione che qualcuno prima o poi disattiva.

#### La regola che divide i due rimedi

> **Se il perimetro si può dichiarare in un punto solo, basta dichiararlo.**
> **Se l'ambiguità è riga per riga, dichiararla non serve: bisogna toglierla.**

Su una **lista**, scrivere in cima *«questa lista contiene più emittenti»* non
risolve niente: le righe restano indistinguibili una dall'altra. Si sa che c'è
confusione e non si sa dove. Serve la colonna, o il cancello.

Su un **numero**, invece, il perimetro è **uno solo**. «Da fatturare: 240.000 €
— *tutti gli emittenti*» è informazione completa: non è rimasto niente da
distinguere. Lì l'etichetta è una **cura**, non un cerotto.

#### Le cinque superfici

| Superficie | Rimedio | Perché |
| --- | --- | --- |
| **Liste** | **Cancello** (P-2b) | Ambiguità riga per riga: solo la colonna o il blocco la tolgono |
| **Export** | **Niente** — ✅ coperto gratis | Passa dallo stesso catalogo delle liste: eredita il flag senza lavoro |
| **Contatori di dashboard** | **Etichetta di perimetro** sul riquadro | Un aggregato ha un perimetro solo: dichiararlo lo rende non ambiguo |
| **Ricerca e tendine di scelta** | **Etichetta** sulla voce | Il rischio non è «non capisco», è «scelgo fra due voci uguali». Bloccare una ricerca è sproporzionato |
| **Dettaglio di un singolo documento** | **Fuori, e scritto perché** | Un documento **si dichiara**: c'è scritto chi lo ha emesso, e non c'è niente accanto con cui confonderlo |

#### Perché i contatori non prendono il cancello

Verificato il 2026-08-17: esiste **una sola dashboard**, `home` («Home
operatore»), con quattro widget — `home.benvenuto`, `home.situazione_aperta`,
`home.competenza`, `home.backlog`. **Tre contatori su tre delle aree in
questione**: il problema è concreto, non teorico.

Ma la `home` è la **pagina di atterraggio**. Metterci un cancello significa che
la prima cosa dopo il login è «scegli un emittente» — pesante, per un problema
che l'etichetta risolve del tutto.

La forma che ne esce ha una sua logica, e non è un compromesso:

> **La dashboard è il panorama: può essere di tutti, purché lo dica.**
> **La lista è il posto dove si lavora: deve avere un perimetro.**

Il super admin apre la home e vede i totali di tutto, **dichiarati come tali**.
Clicca su «Da fatturare», entra in un'area di lavoro, e quella gli chiede di
scegliere. Due momenti diversi, non due regole in contraddizione.

⚠️ **L'ultima riga della tabella conta quanto le altre.** Il dettaglio singolo
resta fuori **con la ragione scritta**: senza, fra sei mesi qualcuno rifà questa
analisi da zero — o, peggio, aggiunge il cancello anche lì «per coerenza».

### P-3 — Chiudere il fail-open del NULL (§4)

Nel guard §2.2, trattare il NULL come «non confrontabile» e quindi **rifiutare**
l'associazione, invece di lasciarla passare. Piccolo, autonomo, indipendente da
P-1 e P-2.

Vale la stessa regola di P-1: **nessuna eccezione per il pregresso**. Il guard
afferma che una coppia padre/figlio deve avere un codice fiscale confrontabile,
punto — e le coppie che oggi non ce l'hanno emergono quando qualcuno le tocca,
non con una bonifica in blocco (§7, decisione 5).

### P-4 — Dichiarare l'emittente nella riga · *non più indipendente: è il prezzo di P-2b*

Le liste devono poter **mostrare** l'emittente: oggi nessuna riga dichiara da
dove viene, ed è il motivo per cui nessuna può onestamente dichiararsi
multi-emittente.

Con P-2a l'operatore è mono-emittente e la colonna gli dice poco — arriverebbe
**spenta**, come da merge automatico del catalogo. Serve **al super admin**, che
è l'unico a poter vedere righe di emittenti diversi affiancate, cioè
esattamente il caso in cui non saperlo fa danno.

⭐ **Dopo la decisione su P-2b, P-4 smette di essere una proposta a sé**: è la
condizione che una lista deve soddisfare per poter mettere
`multi_emittente = true`. Le due cose sono due metà della stessa regola, e
tenerle separate era il modo per non farne mai nessuna delle due.

---

## 7. Decisioni prese e domande ancora aperte

> ✅ **Chiusa il 2026-08-17 (1)**: *«un operatore senza riga è un errore o uno
> stato legittimo?»* → **errore di configurazione**; solo il super admin è
> legittimamente multi-emittente, e per restringersi ha già il filtro emittente
> attivo. Conseguenza: il presidio va a monte (**P-2a**), non sulle liste.
>
> ✅ **Chiusa il 2026-08-17 (2)**: *«il super admin deve scegliere un
> emittente?»* → **non in generale**. Lo obbliga la **singola lista** che non sa
> reggere più emittenti, via flag `multi_emittente` sul catalogo (**P-2b**), con
> default `false` e P-4 come condizione per metterlo a `true`.
>
> ✅ **Chiusa il 2026-08-17 (3)** — *chi accende il flag, e quando*:
>
> - **solo dal seed** (`lista_definizione.csv`), con revisione e migrazione.
>   **Nessun interruttore in interfaccia**: il flag descrive una *capacità del
>   software*, non una preferenza dell'utente, e una capacità non si dichiara
>   per stanchezza;
> - si accende **insieme** al lavoro di P-4 sulla stessa lista, o comunque
>   **dopo** — mai prima: accenderlo prima apre una finestra in cui la lista
>   mescola emittenti senza dirlo e nessuno avverte;
> - **serve un controllo automatico** che elenchi le liste con
>   `multi_emittente = true` **prive** di una colonna emittente in
>   `ui.lista_colonna`. Se ne compare una, qualcuno ha attaccato l'adesivo
>   «collaudato» senza collaudare.
>
> **Il senso**: il flag deve essere un **registro di debito che cala** — parte da
> «nessuna lista è pronta» e si accorcia. Se diventa un interruttore comodo si
> trasforma in un elenco di eccezioni che cresce, e tanto valeva non averlo.
>
> ⚠️ **Trappola concreta, verificata il 2026-08-17.** Esiste già un CRUD di
> amministrazione su `ui.lista_definizione`
> (`apps/ui/services/lista_definizione_admin_service.py`), con `PATCH` su una
> **whitelist** di chiavi mutabili. La whitelist protegge: una colonna nuova
> **non** diventa modificabile da sola. Ma il commento locale dichiara *«Tutti i
> campi sono mutabili (nessun immutabile per design)»* — quindi chi aggiungerà
> la colonna sarà naturalmente portato a metterla anche lì, e in quel momento
> l'interruttore in interfaccia esiste, contro questa decisione.
>
> 🚫 **`multi_emittente` NON va in `_CREATE_KEYS` né in `_UPDATE_KEYS`**, e il
> perché va scritto **accanto alla whitelist**, non solo qui: è l'unica
> eccezione a una convenzione locale, e un'eccezione senza motivo scritto viene
> tolta dal primo che passa.
>
> ✅ **Chiusa il 2026-08-17 (4)** — *il cancello vale anche fuori dalle liste?*
> → **no, e non ovunque serve lo stesso rimedio**. Cancello sulle liste,
> **etichetta** su contatori e ricerche, export coperto gratis, dettaglio
> singolo fuori con la ragione scritta. Dettaglio in **P-2c**.
>
> ✅ **Chiusa il 2026-08-17 (5)** — *bonifica dei dati esistenti*: **nessuna, per
> ora**. I dati di sviluppo sono di test; se e quando creeranno problemi se ne
> riparla. Conseguenza diretta: **il guard non fa eccezioni per il pregresso**
> (P-1), e sarà il guard stesso a far emergere i casi uno alla volta, nel
> momento in cui qualcuno li tocca.
>
> ✅ **Chiusa il 2026-08-17 (6)** — *l'interruttore in interfaccia*: non basta
> scriverlo, va **impedito**. Tre strati in P-2b — permesso a livello di
> colonna, test in CI sulla whitelist, motivo scritto nel file.

**Il buco A (§2) è chiuso come decisioni.** Quelle che restano sono di
attuazione, non di forma:

1. **Ordine di applicazione**: vedi §7-bis. Da confermare come sequenza.
2. **Verifica sui grant di `90_end`**: che nessun changeSet ri-conceda `UPDATE`
   a livello di tabella su `ui.lista_definizione`, annullando lo strato 1 di
   P-2b in silenzio.

⚠️ **DL-B e DL-C non spariscono, cambiano scopo.** Non servono più a dimensionare
una bonifica che non si fa: servono a sapere **quanti guard scatteranno** una
volta applicato P-1, cioè quanto rumore aspettarsi. Restano utili, **non
bloccano**.

### Da misurare prima di applicare

| # | Cosa | Blocca |
| --- | --- | --- |
| **DL-A** | Utenti con identità OPERATORE, **non** super admin, **senza** riga in `config.user_emittenti_fiscali` | ⛔ **Blocca P-2a**: dopo la correzione non vedono più nulla |
| **DL-B** | Alberi BA che attraversano due emittenti | 🔵 Informativo: quanti guard scatteranno dopo P-1 |
| **DL-C** | BA con `parent_account_id` valorizzato e `id_fiscale_univoco_cf_piva` NULL su uno dei due lati | 🔵 Informativo: quanti guard scatteranno dopo P-3 |

⚠️ **DL-A non è coperto dalla decisione «niente bonifica»**, ed è una differenza
importante: non è dato sporco da tollerare, è **configurazione mancante**. Un
operatore senza riga, dopo P-2a, smette di vedere qualunque cosa — non è un
guard che si annuncia, è una schermata vuota senza spiegazione. Le righe vanno
aggiunte **prima**, e costano un `INSERT` a testa.

---

## 7-bis. Ordine di applicazione proposto

Le proposte sono in gran parte indipendenti, ma **la sequenza non è indifferente**:
alcune riducono il danno delle altre, e una sola ha un prerequisito duro.

| Passo | Cosa | Perché in questa posizione |
| --- | --- | --- |
| **1** | **DL-A** — contare gli operatori senza riga, e **aggiungere le righe mancanti** | ⛔ Prerequisito duro di P-2a: senza, il passo 2 li lascia al buio |
| **2** | **P-2a** — fail-closed nella catena dello scope + `COMMENT ON TABLE` riscritto | È **una correzione**, non una decisione: prima si chiude il buco che perde, poi si costruisce sopra. E riduce da subito il danno di un albero misto già esistente |
| **3** | **P-3** — fail-open del NULL nel guard CF (§4) | Piccolo e autonomo. Va **prima** di P-1, altrimenti P-1 nasce sopra un guard che ha ancora una porta aperta di fianco |
| **4** | **P-1** — guard albero omogeneo, **due movimenti**, **senza eccezioni per il pregresso** | Il pezzo più grosso. Da qui in poi la fattura non può più nascere da un emittente invisibile. **Nessuna bonifica**: i casi emergono uno alla volta quando qualcuno li tocca |
| **5** | **P-4** su una lista pilota, poi **P-2b** su quella lista | Nell'ordine: prima la colonna, poi il flag. **Mai al contrario** — accendere il flag prima apre una finestra in cui la lista mescola senza dirlo |
| **6** | **P-2c** — etichette di perimetro su contatori e ricerche | Indipendente da tutto: si può anticipare in qualunque momento, non blocca né è bloccato |

⚠️ **Il passo 5 non si fa «per tutte le liste».** Si fa **una lista alla volta**,
e ogni volta è lavoro vero. Il flag resta a `false` su tutte le altre, ed è
giusto così: è un registro di debito che cala, e il giorno in cui lo si volesse
accendere in blocco vorrebbe dire che ha smesso di significare qualcosa.

⚠️ **Il passo 2 è quello che si è tentati di rimandare** perché «tanto oggi
funziona». Funziona nel senso che nessuno se ne lamenta: un operatore
configurato a metà vede tutti gli emittenti e non lo sa né lui né nessun altro.

---

## 8. Cosa NON è in perimetro

- **La RLS non si allenta.** Nessuna eccezione, nessuna policy che «faccia
  vedere il padre a chi vede il figlio»: sarebbe un'apertura di visibilità, e
  la causa si toglie a monte rendendo l'albero omogeneo;
- **`fn_build_fattura_key` e la pipeline di fatturazione** non si toccano;
- **Il modello 1-a-1** `user_emittenti_fiscali` non si tocca: il problema è
  l'assenza della riga, non la sua unicità;
- **`ui.dashboard_definizione` non prende il flag**: per un aggregato il rimedio
  è l'etichetta (P-2c), non il cancello;
- **Il dettaglio di un singolo documento resta fuori**, e la ragione è scritta
  in P-2c: un documento dichiara già chi lo ha emesso;
- **Nessun interruttore in interfaccia** per `multi_emittente` (§7, decisione 3);
- **La dashboard Competenza**: sta nell'altro brief, e non aspetta questo.

---

## 9. Note per chi scriverà i test

- ⚠️ **Svuotare `app.current_user_id` NON è fail-closed** in un test di scope:
  `fn_scope_ef_whitelist_via_sr(NULL)` risponde TRUE. Il cancello vero è
  `app.ruolo_applicativo`. Un test che «verifica il fail-closed» azzerando lo
  user id è verde per sottrazione;
- i pgTAP girano come **applicazione** (`zeroerp_app` + contesto operatore): le
  policy RLS sono attive a ogni corsa, e una fixture che scrive dove
  l'applicazione non scrive non passa;
- `throws_ok` **sempre con SQLSTATE** (`'P0001'` per un errore di dominio):
  senza, accetta anche il crash del guard stesso;
- prima di dare per rossa la propria modifica: `scripts/pgtap-baseline.sh
  anagrafiche`.

---

## 10. Riferimenti

| Cosa | Dove |
| --- | --- |
| Scope emittenti (funzione canonica) | `docs/it/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids.md` |
| Wrapper su soggetto_ruolo_id | `docs/it/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids.md` |
| Resolver utente → emittente | `docs/it/dbzero/script/funzioni/fn_resolve_emittente_for_user.md` |
| Tabella dello scope (UNIQUE + semantica) | `docs/it/dbzero/config/tabelle/user_emittenti_fiscali.md` |
| Auto-link BA → emittente | `docs/it/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef.md` |
| Mapping BA → emittente | `docs/it/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account.md` |
| Guard padre/figlio (CF) | `docs/it/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize.md` §2.2 |
| Gerarchia BA (manuale) | `docs/it/dbzero/anagrafiche/manual/billing_account.md` |
| Policy RLS BA (lettura + scrittura) | `db/changelog/migrations_v2/00_schema/anagrafiche/20260601-36-…`, `20260603-25-…` |
| GUC emittente attivo (BE) | `backend/apps/core/api/jwt_audit_authentication.py` |
| Cantiere che ha fatto emergere i buchi | [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](brief-db-dash-competenza-gruppi-cliente-e-ricerca.md) |
| Architettura multi-face auth | `docs/it/guide/architettura-multi-face-auth.md` |
