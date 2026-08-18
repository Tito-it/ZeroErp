# Il perimetro emittente non è presidiato — liste e alberi di billing account

> **Cos'è.** Il brief di **due buchi distinti** nello stesso presidio: il
> perimetro dell'emittente fiscale. Uno sta nell'**accesso alle liste**, l'altro
> nella **gerarchia dei billing account**. Sono separati per causa e per
> soluzione, ma stanno insieme perché **uno tiene aperto l'altro**: finché il
> primo è aperto, il secondo è raggiungibile — e chiuderne uno solo non basta.
> *(La prima stesura diceva «si coprono a vicenda», simmetrico. Non lo è: la
> misura è in §11.1.)*
>
> **Origine.** Emersi il **2026-08-17** analizzando la richiesta «filtrare i
> gruppi fatturabili per cliente»
> ([brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md)).
> Sono stati messi qui perché sono cantieri loro: toccano l'anagrafica e
> l'accesso, non la dashboard.
>
> ✅ **Stato al 2026-08-18 — passi 1, 2, 3, 4 e 6 APPLICATI, nessuna regressione
> sui test.** Dodici changeSet (`20260818-01`, `-02`, `-03`, `-05`, `-08`→`-15`),
> pgTAP nuovi verdi, baseline senza regressioni. Restano il **passo 5** (P-2c,
> etichette — FE/BE, indipendente), il **passo 7** (P-2b, con l'`ALTER TABLE`
> non reversibile) e il **passo 8** (le altre cinque liste), più le richieste al
> backend del §13. ⚠️ **BE-2 è ora bloccante**: la vista e il catalogo del passo
> 6 sono a posto, ma finché il repository di dominio non seleziona il campo la
> colonna si spunta e **resta vuota** — cioè *sembra* la garanzia che P-2b
> pretenderà, e non lo è.
>
> ~~**Stato al 2026-08-17: nulla eseguito.** Nessun changeSet, nessuna
> migrazione, nessun seed; il prossimo passo è il DL-A, che è una misura.~~ —
> superato dall'esecuzione del 2026-08-18. Resta vero il resto: diagnosi
> verificata contro il codice, **undici decisioni prese** (sei di forma in §7,
> cinque di attuazione in Q1–Q5), piano eseguibile in **§12**.
>
> 🔬 **Revisione critica del 2026-08-17 (§11).** Tutte le sei decisioni reggono e
> non ne cambia nessuna. Cambiano invece **quattro cose di attuazione**, e una è
> un blocco vero:
>
> | | Cosa è emerso | Effetto |
> | --- | --- | --- |
> | 🔴 | Lo **Strato 1 di P-2b** (permesso a livello di colonna) **non regge**: un changeSet `runOnChange` ri-concede `UPDATE` di tabella su tutto lo schema `ui` a ogni passata | Il permesso va sostituito da un **trigger** (§11.5) |
> | 🟠 | La **ricerca universale è fail-open sullo scope vuoto**: lo scope esce dal DB con tre significati e rientra da Python con due | ✅ **Q2 chiusa**: le due funzioni di ricerca **si risolvono lo scope da sé** (passo 1). Non è più una dipendenza dal BE |
> | 🟠 | «L'emittente di un BA» **non è la riga di mapping**: è una risoluzione *specifico ∨ default globale* | P-1 confronta il **valore risolto**, e il movimento 2 ha **tre** eventi, non uno (§11.2, §11.3) |
> | 🟢 | **P-4 esiste già su 6 liste**: c'è un pattern da copiare, non da inventare | Il costo vero è nelle **viste**, non nel seed (§11.4) |
>
> E una correzione di merito: il §5 sbaglia il meccanismo con cui A e B si
> coprono. Non si coprono a vicenda — **B è raggiungibile quasi solo dove A è
> aperto**, più il super admin (§11.1). La conclusione operativa non cambia; il
> motivo sì, e il motivo è quello che si usa per scrivere i test.
>
> ✅ **Q1, Q2 e Q3 chiuse il 2026-08-17** (§7 in fondo). Q1 → **trigger**,
> accettando che copra una colonna sola. Q2 → **P-2a non aspetta nessuno**, e la
> ricerca universale **si risolve lo scope da sé** (passo 1): non per l'urgenza
> di una finestra — argomento ritirato, non siamo in produzione — ma perché una
> convenzione a tre stati non sopravvive al viaggio attraverso Python. Q3 →
> **sì al guard** sul cambio di `is_default`, scritto sulla **coppia mista**.
>
> Q4 → pilota **Competenza — gruppi fatturabili**, e l'ordine delle altre cinque
> per lavoro condiviso, non per gravità. Q5 → il messaggio d'errore provvisorio
> **non si tocca**: sparisce da sé con P-1.
>
> ⛔ **Nessuna domanda aperta. Il cantiere è pronto a partire dal passo 0.1**
> (§12) — e da lì in poi è esecuzione.
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
>    in P-2b — ~~permesso a livello di colonna~~ → **trigger** (§11.5), test in
>    CI, motivo nel file. *La decisione non cambia: cambia l'attrezzo, perché
>    quello scelto si spegneva da solo ogni notte.*
>
> 🔴 **Il buco B (§3) resta aperto come lavoro**, e produce una fattura emessa da
> un emittente che l'operatore non può vedere. È il più grave dei due, ed è
> anche il più facile da chiudere: quello che resta in §7 è attuazione, non
> forma. ⚠️ **Ma il bersaglio è più stretto di come sembrava**: dopo §11.1 l'unico
> attore che oggi può costruirlo *senza* passare dal buco A è il **super
> admin** — e dopo P-2a sarà l'unico e basta.

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

> ⚠️ **Rettifica del 2026-08-17 (§11.1): «passa sempre» è vero solo per chi vede
> entrambi i rami.** Quella lettura del padre gira **sotto RLS**, quindi a un
> operatore di *Tito* il BA di *Pippo* risulta invisibile e il guard solleva —
> con il messaggio sbagliato, ma solleva. Il caso passa davvero per il **super
> admin**, per l'**operatore senza riga** (buco A) e per la coppia con **entrambi
> i CF NULL** (buco C). Dettaglio e conseguenze sui test in §11.1.

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

> 🔴 **Il primo dei due punti qui sotto è sbagliato, e la correzione è in §11.1.**
> Resta scritto perché è il ragionamento che ha portato a tenere i due buchi
> insieme — conclusione giusta, meccanismo no.

- ~~**Se l'accesso fosse davvero mono-emittente (A chiuso)**, un albero misto
  resterebbe costruibile ma l'operatore vedrebbe solo la sua metà: la fattura
  sbagliata nascerebbe lo stesso, semplicemente nessuno la vedrebbe nascere.~~
  → **Falso**: con A chiuso l'operatore non riesce nemmeno a impostare quel
  padre, perché il guard §2.2 legge il padre sotto RLS e non lo trova (§11.1).
  Restano scoperti il **super admin** e la coppia con **entrambi i CF NULL**.
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

> ⚠️ **Revisione del 2026-08-17.** I movimenti **non sono due, sono quattro**, e
> «lo stesso emittente» **non è la stessa riga di mapping**: è un valore
> *risolto* (mapping specifico ∨ gestore globale). Entrambe le cose in §11.2 e
> §11.3 — leggerle prima di scrivere il guard, perché cambiano cosa confronta.

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

> 🔴 **Verificato il 2026-08-17: uno c'è, ed è quello centrale.** Non è un
> problema di ordine — è un `runOnChange` che ri-esegue a ogni passata, quindi
> non esiste un numero abbastanza alto. **Lo Strato 1 va cambiato di forma**: non
> un permesso, un **trigger**. Prova e rimedio in **§11.5**.

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

> ⚠️ **Rettifica del 2026-08-17 (§11.4): «nessuna riga» è falso, e la differenza
> è utile.** Sei liste documento (contratti, preventivi, offerte, ordini, DDT,
> resi) hanno **già** la colonna emittente a catalogo. A non averla sono
> esattamente le sei del perimetro. Quindi P-4 non si inventa: **si copia**. Il
> costo vero non è la riga di CSV — è che le viste del perimetro espongono l'`id`
> dell'emittente ma **non la ragione sociale**.

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
> scriverlo, va **impedito**. Tre strati in P-2b — ~~permesso a livello di
> colonna~~ **trigger** (rettifica del 2026-08-17, §11.5: il permesso viene
> ri-concesso a ogni passata di `ci_apply`), test in CI sulla whitelist, motivo
> scritto nel file.

**Il buco A (§2) è chiuso come decisioni.** Quelle che restano sono di
attuazione, non di forma:

1. ~~**Ordine di applicazione**: vedi §7-bis. Da confermare come sequenza.~~
   → riscritto come piano eseguibile in **§12**; da confermare lì.
2. ~~**Verifica sui grant di `90_end`**~~ → ✅ **fatta il 2026-08-17, ed è
   negativa**: un changeSet ri-concede eccome (§11.5). Ne è nata **Q1**.

⚠️ **DL-B e DL-C non spariscono, cambiano scopo.** Non servono più a dimensionare
una bonifica che non si fa: servono a sapere **quanti guard scatteranno** una
volta applicato P-1, cioè quanto rumore aspettarsi. Restano utili, **non
bloccano**.

### ✅ Aperte dalla revisione del 2026-08-17 — cinque, **tutte chiuse il 2026-08-17**

> Nessuna riapre una decisione già presa. Sono tutte **nate dalla verifica**
> (§11), e due di esse cambiano cosa si scrive, non solo quando.

#### ✅ Q1 — CHIUSA il 2026-08-17: **trigger**

> **Decisione Tid.** Lo Strato 1 di P-2b si fa con un **trigger** su
> `ui.lista_definizione`, non con un permesso a livello di colonna.
>
> **Si accetta consapevolmente il baratto**: il trigger nomina **una** colonna e
> non copre quelle future, mentre il permesso — sulla carta — le avrebbe coperte
> tutte. Ma quella copertura **oggi non esiste**, perché il presidio che la
> offriva si annulla a ogni passata di `ci_apply` (§11.5). Si sceglie una difesa
> che tiene su una colonna invece di una che sembra coprirle tutte e non ne
> copre nessuna.
>
> Perimetro del trigger, per non doverlo ridedurre: **una tabella, una colonna**
> (§11.4-bis). Tutto il resto di `ui.lista_definizione` resta come oggi.

*La domanda com'era posta, per la storia:*

##### Q1 ⛔ *blocca il passo 7* — Lo Strato 1 diventa un trigger. Si accetta il baratto?

Il permesso a livello di colonna **non tiene** (§11.5). Il rimedio proposto è un
trigger. Ma **non è lo stesso presidio con un altro attrezzo**, e la differenza va
detta prima e non dopo:

| | Permesso (com'era deciso) | Trigger (come si può fare) |
| --- | --- | --- |
| Tiene? | ❌ ri-concesso a ogni `ci_apply` | ✅ sì |
| Copre le colonne **future** | ✅ sì — una colonna nuova nasce non scrivibile | ❌ no: nomina **una** colonna |
| Dove vive | file di infrastruttura condiviso da 14 schemi | accanto alla colonna che protegge |

Si perde la proprietà più elegante della proposta originale — *fail-closed nella
direzione giusta anche per ciò che non esiste ancora*. Si perde però una
proprietà che **oggi non c'è**, perché il presidio che la offriva si spegne ogni
notte.

> ⭐ **Proposta**: trigger. Un presidio che tiene su una colonna vale più di un
> presidio che si spegne su tutte.

#### Q2 — P-2a dipende da una correzione BE. La si aspetta, o si toglie la dipendenza?

`search_repository.py` è fail-open sullo scope vuoto (§11.6, BE-1): applicare
P-2a prima di quella correzione **allarga** la visibilità sulla ricerca
universale invece di restringerla. E la correzione sta in `backend/`, cioè fuori
perimetro, su un altro branch.

⭐ **Aggiornamento del 2026-08-17: c'è una terza strada, ed è dentro il perimetro
DB.** Verificato: `fn_search_soggetti_universale` e `fn_get_search_detail` **non
leggono nessuna GUC** — si fidano interamente dell'array che il backend passa.
Sono le uniche due funzioni della famiglia a farlo, e sono chiamate **da un solo
punto ciascuna**, tutto sul percorso web (nessun batch).

| | Cosa comporta | Il difetto |
| --- | --- | --- |
| **A. Aspettare BE-1** | il cantiere DB si ferma su una dipendenza che non controlla | corregge **l'istanza**: il prossimo che scrive `if ids:` lo riapre |
| **B. Applicare comunque** | finestra in cui l'operatore non configurato non vede niente **tranne** nella ricerca, dove vede tutto | è il difetto del brief, in miniatura — e colpisce **proprio** la persona per cui P-2a esiste |
| ⭐ **C. Togliere la dipendenza** | le due funzioni **risolvono lo scope da sé** dalla GUC, via `fn_get_emittenti_scope_sr_ids`; il parametro resta ma può solo **restringere**, mai allargare | corregge **la classe**: nessun errore del chiamante può più aprire |

**Perché C, e perché non è una furbizia:**

- è **DB-first**: lo scope è una regola di dominio, e il posto giusto in cui
  vive è il database. Che il backend risolva lo scope in Python e lo spedisca
  come array è una **seconda sede della stessa verità** — la duplicazione che il
  progetto non ammette;
- **il pattern esiste già in casa, ed è quello vendite**: `get_scope_user_id`
  passa l'`auth_user_id` e le funzioni SQL risolvono internamente
  ([api.md §Scope emittente](../api.md)). Delle due strade che convivono, C
  adotta quella che non si rompe;
- **anche l'invariante è già in casa**: *«solo restringente, mai allargante»* è
  la regola con cui l'emittente attivo si interseca con lo scope di diritto
  (rev 2026-08-04). Qui si applica al parametro invece che alla GUC, ed è lo
  stesso ragionamento;
- **toglie il blocco**: P-2a non aspetta più nessuno.

⚠️ **BE-1 non si annulla, cambia grado.** Con C il difetto Python non può più
aprire niente, ma resta un punto che scrive una cosa falsa: retrocede da 🟠
*bloccante* a 🔵 *igiene*, da fare quando comodo. E la **regola generale** di
§11.6 — questa convenzione a tre stati non si legge mai con un test di verità —
vale lo stesso, perché il prossimo consumatore potrebbe non essere una funzione
che possiamo blindare.

⚠️ **Da decidere dentro C**, e va scritto prima di scrivere il codice: cosa fa la
funzione quando `app.current_user_id` è **vuota** (job, canale di sistema). La
convenzione della famiglia è *attore nullo → nessun filtro*
(`fn_scope_ef_whitelist_via_efba` ramo 1). Coerenza dice di seguirla; il fatto
che oggi nessun batch chiami queste due funzioni dice che si può anche essere
più stretti. **Proposta: seguire la convenzione** — una famiglia che si comporta
in due modi è peggio di un ramo largo e dichiarato.

> ⭐ **Proposta**: **C**, con BE-1 declassato a igiene. Aspettare corregge un
> punto; spostare la decisione nel database chiude la strada.

##### ✅ Q2 — CHIUSA il 2026-08-17: **B per la sequenza, C per il merito** — e non erano alternative

> **Obiezione di Tid, ed è fondata**: *«non siamo in produzione, quindi la
> finestra non costa niente. Se C si sceglie, si sceglie perché è meglio
> tecnicamente — non perché il BE ha un problema temporaneo.»*
>
> ⛔ **L'argomento della finestra è ritirato.** Era il perno di tutta la
> domanda, ed era debole: una finestra su un ambiente senza produzione non è un
> costo, è un fastidio. Averla usata per ordinare i passi ha prodotto una scelta
> a tre vie che **non esisteva**.

**Tolta la finestra, le opzioni si riducono e si separano:**

| | Esito |
| --- | --- |
| **A** — aspettare BE-1 | ⛔ **decade**: esisteva **solo** per evitare la finestra |
| **B** — non bloccare P-2a | ✅ è una scelta di **sequenza** |
| **C** — lo scope si risolve nel DB | ✅ è una scelta di **progetto** |

> **B e C non erano in concorrenza: rispondevano a due domande diverse.**
> «P-2a aspetta?» → no (B). «La ricerca resta com'è?» → no (C). Le avevo messe
> in alternativa perché le tenevo insieme la finestra, che era il presupposto
> sbagliato.

**Perché C regge anche senza l'argomento della finestra** — la ragione è una
sola, e non è «il BE ha sbagliato»:

> ⭐ **La convenzione a tre stati non sopravvive al viaggio.** Lo scope esce dal
> database con tre significati distinti (`NULL` = tutto, `{}` = niente, array =
> whitelist), attraversa Python e **rientra con due**: in Python `[]` e `None`
> sono entrambi falsi, e ogni idioma naturale del linguaggio — `if ids:`,
> `ids or []` — li fonde. Non è una svista di chi ha scritto quella riga: è un
> **canale che perde per costruzione**, e infatti la stessa fusione è già
> avvenuta in due punti indipendenti.
>
> C non «corregge il backend»: **toglie il viaggio**. Una risposta che non esce
> dal database non può degradarsi nel tragitto.

Due ragioni di contorno, vere ma non decisive da sole:

- **la famiglia è altrimenti uniforme**: tutti gli adapter `fn_scope_ef_whitelist_via_*`
  risolvono internamente da `p_auth_user_id`; queste due sono **le uniche** che
  accettano un array già calcolato. Una famiglia con due convenzioni è una
  famiglia in cui bisogna ricordarsi in quale si è;
- **le policy RLS risolvono lo scope da sole**, dalle GUC. Oggi convivono quindi
  due meccanismi di applicazione dello scope con **due modelli di fiducia
  diversi**, e solo uno dei due può essere aggirato da chi chiama.

⚠️ **Il costo di C, per onestà**: le due funzioni diventano **dipendenti dal
contesto** (leggono una GUC), quindi un pgTAP deve impostarlo e un futuro
chiamante batch cade nel ramo *«nessun attore → nessun filtro»*. È il prezzo che
il progetto **paga già ovunque**, e in cambio si compra che quel ramo sia scritto
una volta in un posto invece che assunto a ogni chiamata.

**Decisione operativa:**

1. **P-2a non aspetta nessuno** (passo 2 sbloccato — era Q2/B);
2. **C si fa**, come passo **a sé**, per merito architetturale e non per urgenza:
   diventa il **passo 1** del piano, che da «richiesta al BE» si trasforma in
   lavoro DB (§12);
3. **BE-1 decade a 🔵 igiene** — o sparisce del tutto, perché con C quella riga
   non decide più niente. Resta in §13 con la sua ragione: la **regola** che ne
   discende (⚠️ *questa convenzione non si legge mai con un test di verità*) vale
   per il prossimo consumatore, che potrebbe non essere una funzione blindabile.

#### ✅ Q3 — CHIUSA il 2026-08-17: **sì al guard**

> **Decisione Tid.** Il quarto movimento (cambio di `is_default`) prende il suo
> guard, scritto sulla **coppia mista**: un BA non mappato con padre o figlio
> mappato. Non su «esiste un albero».
>
> **La domanda di principio decade**: non c'era da decidere se il gestore globale
> sia modificabile, perché dall'applicazione **non lo è già oggi** — tre presidi
> in esercizio lo impediscono, e resta raggiungibile solo da una migrazione o da
> un intervento manuale (verifica qui sotto). Il guard non toglie una libertà:
> mette un avviso sull'unica strada che resta.
>
> ⚠️ **Conseguenza accettata**, e non è una domanda nuova: uno spostamento
> *legittimo* del gestore globale richiederà di mappare **prima** i BA delle
> coppie miste. È la stessa forma della decisione 5 — *il guard afferma
> l'invariante, i casi emergono quando qualcuno li tocca* — applicata a
> un'operazione che tocca N righe invece di una.
>
> **Resta da fare, ma è misura non decisione**: la sottomisura di `DL-D` (quante
> coppie miste esistono), che dimensiona il rumore senza bloccare niente.

*La domanda com'era posta, per la storia:*

> ~~Spostare `is_default` cambia in blocco l'emittente di tutti i BA non mappati
> (§11.3), quindi un guard **congela il gestore globale** appena esiste un albero
> appeso al default. La domanda di principio: il gestore globale è una
> configurazione che si cambia, o un dato d'impianto che si sceglie una volta?~~

##### 🔬 Perché era mal posta — verifica del 2026-08-17: **è già congelato**

> **La premessa «il guard congela il gestore globale» è falsa**, e va corretta
> prima di rispondere: dall'applicazione **il gestore globale non si può già
> spostare oggi**. Il guard non toglierebbe una libertà che c'è: presidierebbe
> una strada che passa solo da un intervento deliberato sul database.

Tre presidi già in esercizio, che si chiudono a tenaglia:

| Presidio | Cosa impedisce |
| --- | --- |
| `uq_emittenti_fiscali_ba_default` — indice unico parziale su `is_default` | **non possono esistere due default**: creare quello di *Pippo* mentre esiste quello di *Tito* viola l'indice |
| `trgfn_emittenti_fiscali_default_guard` — ⚠️ `CONSTRAINT TRIGGER … DEFERRABLE INITIALLY DEFERRED` | al **commit** pretende **esattamente un** default: cancellare quello di *Tito* e fermarsi lì fallisce |
| Il repository **non ha** un `update_mapping` | esistono `create_mapping` e `delete_mapping`, non una modifica: l'emittente di un mapping non si cambia dall'API |

**Messi insieme**: spostare il default richiede `DELETE` + `INSERT` **nella
stessa transazione** — che è esattamente ciò che il trigger differito consente e
che due chiamate HTTP separate **non sono**. Dall'interfaccia la sequenza
fallisce a metà, e non esiste un verbo che la faccia atomicamente.

> **Quindi il quarto movimento è raggiungibile solo da una migrazione o da un
> intervento manuale sul database.** Cioè da un atto deliberato, raro, fatto da
> chi sa cosa sta facendo — e proprio per la rarità mai coperto da un test.

**Cosa cambia nella decisione:**

- **il costo quotidiano del guard è ~zero**: non può scattare a un operatore,
  perché un operatore non ci arriva;
- **il valore è alto proprio dove serve**: presidia l'unica operazione del
  cantiere con **raggio N**, quella in cui un errore è silenzioso e grande;
- ⭐ **e non congela niente, se scritto sulla condizione giusta.** Spostare il
  default rompe un albero **solo** quando un BA non mappato ha padre o figlio
  **mappato**. Se entrambi i lati sono non mappati si spostano insieme e
  l'albero resta omogeneo; se entrambi sono mappati non si sposta nessuno.
  **La condizione da presidiare è la coppia mista**, non «esiste un albero».

⚠️ **Conseguenza su DL-D**: la misura utile non è «quanti BA senza mapping» — è
la sua sottomisura, **quanti BA senza mapping stanno in coppia padre/figlio con
un BA mappato**. Solo quelli farebbero scattare il guard, e sono verosimilmente
molti meno.

> ⭐ **Proposta rivista, poi accettata**: **sì al guard**. Non stiamo scegliendo
> se il gestore globale sia modificabile — è già di fatto un dato d'impianto.
> Stiamo scegliendo se l'unico modo di cambiarlo, a mano sul database, debba
> **avvisare** quando sta per spaccare qualcosa. Costa un ramo in una funzione
> che stiamo comunque scrivendo.

#### ✅ Q4 — CHIUSA il 2026-08-17: pilota **Competenza — gruppi fatturabili**

> **Decisione Tid.** Si comincia da **Competenza — gruppi fatturabili**
> (`vendite.dash_competenza_gruppi`), e le altre cinque seguono nell'ordine
> stabilito qui sotto — che **non è alfabetico né per gravità**: è per *quanto
> lavoro condividono*.
>
> Il criterio che ha deciso, e che vale anche per i cantieri futuri: **fra due
> candidate, si sceglie quella in cui il lavoro è dentro il perimetro.** «Lotti
> di fatturazione» sembrava più semplice, ma i suoi dati nascono da SQL scritto
> nel backend: era semplice *perché non era nostro*, e un pilota che non tocca
> il database non collauda il pattern che va replicato cinque volte.

#### Q4 — la domanda, e come è stata istruita

> ℹ️ **I numeri fra parentesi non sono dati di sviluppo.** Sono gli `id` del
> catalogo delle liste, che vive in `80_data/sql/ui/lista_definizione.csv` — un
> file **versionato nel repository** e applicato da una migrazione, quindi
> identico su ogni database, compreso uno ricostruito da zero. Restano indicati
> perché servono a chi scriverà il seed, ma **la lista si nomina per nome**: un
> numero da solo non dice niente a chi legge.

**Le sei schermate del perimetro** — quelle che oggi non dichiarano da quale
emittente arriva la riga:

| Schermata | `codice` | id |
| --- | --- | --- |
| Lotti di fatturazione | `vendite.lotti` | 12 |
| Situazione aperta — documenti | `vendite.dash_aperto_documenti` | 39 |
| Backlog — documenti fermi | `vendite.dash_backlog_documenti` | 40 |
| Competenza — errori vivi | `vendite.dash_competenza_errori` | 41 |
| **Competenza — gruppi fatturabili** | `vendite.dash_competenza_gruppi` | 42 |
| Competenza — drill-down commesse | `vendite.dash_competenza_commesse` | 43 |

**La domanda è una sola: da quale si comincia.** Il lavoro è lo stesso su tutte
e sei; la prima serve a collaudare il metodo, le altre vengono a ricalco.

Proposta: **Competenza — gruppi fatturabili**. È dove l'operatore **sceglie cosa
fatturare**, quindi il posto in cui l'ambiguità di emittente si paga subito.
Alternativa considerata: **Lotti di fatturazione**, che sembrava più semplice.

##### 🔬 Verifica del 2026-08-17 — «più semplice» era sbagliato: **Lotti non fa lavoro DB**

| | **Lotti di fatturazione** | **Competenza — gruppi fatturabili** |
| --- | --- | --- |
| **Da dove nascono le righe** | SQL grezzo nel repository BE (`vendite_repository.list_lotti`), direttamente su `vendite.fatturazione_lotti` — **nessuna vista** | la vista `vw_dash_competenza_gruppi` |
| **L'emittente c'è già?** | ✅ `emittente_soggetto_ruolo_id`, `NOT NULL` sulla tabella | ✅ `emittente_soggetto_ruolo_id` in proiezione |
| **Lavoro DB** | ⚠️ **nessuno** | la JOIN che produce `emittente_ragione_sociale` |
| **Lavoro BE** | JOIN + colonna + mapping | colonna + mapping |
| **C'è un'azione attaccata?** | numera, ristampa | ⭐ **emissione mirata**: da lì si sceglie *cosa* fatturare |

**Cinque ragioni per 42, e la prima da sola basterebbe:**

1. ⭐ **è l'unica delle due che fa lavoro DB.** Su `lotti` il perimetro di questo
   cantiere non ha niente da fare: la lista nasce da SQL scritto nel backend. Un
   pilota che non tocca il database **non collauda il pattern** che dobbiamo
   replicare cinque volte, e sposta il lavoro fuori perimetro — quindi lo
   rallenta, non lo semplifica. *«Più semplice» era una misura sbagliata: era
   semplice per noi perché non era nostro;*
2. **il pattern è già scritto sei volte**, identico:
   `s_ef.ragione_sociale_completa AS emittente_ragione_sociale`
   (`vw_ordini_lista`, `vw_contratti_lista`, `vw_preventivi_lista`,
   `vw_offerte_commerciali_lista`, `vw_ddt_lista`, `vw_resi_lista`);
3. **la vista è già mezza pronta**: fa **già** la JOIN a `soggetti`, per il
   cliente (`sog.ragione_sociale_completa AS cliente_fatturazione_display`).
   Quella dell'emittente è la stessa JOIN una seconda volta;
4. **è il posto dove la scelta ha una conseguenza.** Da lì parte l'emissione
   mirata: si selezionano i gruppi e si fattura. Una lista che mescola emittenti
   senza dirlo, **con un pulsante «fattura» sotto**, è il caso peggiore. E
   quando il flag entrerà, il cancello dirà *«scegli un emittente prima di
   decidere cosa fatturare»* — la richiesta giusta nel momento giusto;
5. **niente collisione**: la vista è stata toccata oggi dall'altro cantiere
   (commit `4ec3d9f5c`), ma quel lavoro è **chiuso e committato**.

##### ⭐ E ne esce anche l'ordine delle altre cinque

| Giro | Schermate | Perché insieme |
| --- | --- | --- |
| **1° (pilota)** | Competenza — gruppi fatturabili | vista propria, JOIN ai soggetti già presente, azione attaccata |
| **2°** | Situazione aperta — documenti **+** Backlog — documenti fermi | sono **due proiezioni della stessa vista a monte** (`vw_dash_fatturazione_documenti`): la JOIN si aggiunge **una volta sola** e ne escono due schermate |
| **3°** | Competenza — errori vivi · Competenza — drill-down commesse | viste proprie, stesso pattern del pilota |
| **ultima** | Lotti di fatturazione | ⚠️ **interamente lavoro BE**: nessuna vista da estendere. In fondo non perché conti meno, ma perché non insegna niente al database e dipende da un altro branch |

#### ✅ Q5 — CHIUSA il 2026-08-17: **non si tocca**

> **Decisione Tid.** Il messaggio provvisorio resta com'è fino a P-1.
>
> **Il criterio, e vale oltre questo caso**: non essendoci produzione, un difetto
> *cosmetico e temporaneo* non giustifica codice intermedio. Ogni correzione di
> passaggio è codice che qualcuno dovrà togliere, e in questo progetto ciò che si
> mette «per ora» tende a restare.

Fino a P-1, l'albero misto tentato da un operatore configurato viene rifiutato
con `E_ID_FISCALI_DIVERSI` **su due BA che hanno il CF identico** (§11.1). Con
P-1 il messaggio giusto arriva e questo sparisce da sé.

⚠️ **Una cosa però resta, e non è cosmetica**: quello stesso messaggio può far
passare un pgTAP **per la ragione sbagliata** (§9, §11.1). Non è un motivo per
correggerlo — è un motivo per **asserire sempre il codice errore atteso** nei
test di P-1, che è già scritto nel passo 4 e in §9. La decisione di non toccare
il messaggio non tocca quel presidio.

### Da misurare prima di applicare

| # | Cosa | Blocca |
| --- | --- | --- |
| **DL-A** | Utenti con identità OPERATORE, **non** super admin, **senza** riga in `config.user_emittenti_fiscali` | ⛔ **Blocca P-2a**: dopo la correzione non vedono più nulla |
| **DL-D** ⭐ | Billing account **senza** riga in `anagrafiche.emittenti_fiscali_billing_account` (quindi appesi al gestore globale) — e la **sottomisura che conta davvero**: quanti di quelli stanno in coppia padre/figlio con un BA **mappato** | 🔵 Informativo: i primi sono i falsi positivi del guard P-1 se lo si scrive sulla riga invece che sul valore risolto (§11.2); **i secondi sono gli unici** che farebbero scattare il guard sul cambio di `is_default` (Q3) |
| **DL-B** | Alberi BA che attraversano due emittenti | 🔵 Informativo: quanti guard scatteranno dopo P-1 |
| **DL-C** | BA con `parent_account_id` valorizzato e `id_fiscale_univoco_cf_piva` NULL su uno dei due lati | 🔵 Informativo: quanti guard scatteranno dopo P-3 |

⚠️ **DL-A non è coperto dalla decisione «niente bonifica»**, ed è una differenza
importante: non è dato sporco da tollerare, è **configurazione mancante**. Un
operatore senza riga, dopo P-2a, smette di vedere qualunque cosa — non è un
guard che si annuncia, è una schermata vuota senza spiegazione. Le righe vanno
aggiunte **prima**, e costano un `INSERT` a testa.

---

## 7-bis. Ordine di applicazione proposto

> ⚠️ **Superata in parte dal 2026-08-17 — resta come motivazione, non come
> istruzione.** Il *perché* di ogni posizione è ancora valido ed è il motivo per
> cui questa tabella non si cancella. Ma la sequenza eseguibile è in **§12**, che
> ne aggiunge due passi che qui mancavano (una richiesta al BE che **precede**
> P-2a, e una misura in più) e cambia la forma di un passo (§11.5).

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

- 🔴 **La trappola più costosa è in §11.1, e va letta prima di scrivere il test
  di P-1.** Con un contesto operatore ristretto, il guard **già esistente**
  solleva sull'albero misto — perché legge il padre sotto RLS e non lo trova, non
  perché lo giudichi. Un test scritto così **passa senza aver mai eseguito il
  codice nuovo**: è la forma più subdola del verde per sottrazione, perché il
  rosso c'è, arriva, e ha persino l'aria giusta. Asserire **il codice errore
  nuovo**, e costruire il caso sul percorso che attraversa davvero il ramo;
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

## 11. Analisi critica — cosa regge, cosa no · *revisione 2026-08-17*

> **Metodo.** Ogni affermazione qui sotto è stata verificata leggendo la
> definizione **viva** degli oggetti (doc auto-generata in `docs/it/dbzero/`), il
> seed, i changeSet e il codice Python — mai uno YAML di migration preso da solo.
> Dove il brief e il codice divergono, il codice ha ragione e il brief è stato
> marcato sul posto.
>
> **Esito in una riga:** la diagnosi regge tutta, le sei decisioni non si toccano,
> **l'attuazione cambia in quattro punti**. Uno dei quattro è un blocco (§11.5).

### 11.1 🔴 Il §5 sbaglia il meccanismo: B è raggiungibile quasi solo dove A è aperto

Il guard §2.2 legge l'anagrafica del padre così:

```sql
SELECT s2.id_fiscale_univoco_cf_piva
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.istanze_utilities iu2 ON iu2.id = ba.istanza_utility_id
  JOIN anagrafiche.soggetti s2          ON s2.id  = iu2.soggetto_id
 WHERE ba.id = NEW.parent_account_id;
```

Quella `SELECT` **non è privilegiata**. `trgfn_billing_account_guard_normalize`
non è `SECURITY DEFINER`, quindi gira con l'identità di chi ha fatto la scrittura
— l'applicazione — e su `anagrafiche.billing_account` la Row Level Security è
**attiva** (`20260601-40-enable-rls-ondata2-billing-account`, `ENABLE`, no
`FORCE`). La policy di lettura è `rls_billing_account_ef_whitelist`, che passa da
`fn_scope_ef_whitelist_via_efba`.

Conseguenza, ed è l'opposto di quanto scritto in §3.2/§5:

| Chi scrive | Vede il padre di *Pippo*? | Cosa fa il guard oggi |
| --- | --- | --- |
| Operatore **con** riga (scope = 1 emittente) | ❌ no | `v_cf_parent` resta NULL → `v_cf_child IS DISTINCT FROM NULL` è **vero** → **solleva** `E_ID_FISCALI_DIVERSI` |
| Operatore **senza** riga (buco A) | ✅ sì (vede tutto) | stesso CF → **passa**: albero misto creato |
| **Super admin** | ✅ sì | stesso CF → **passa**: albero misto creato |
| Chiunque, ma **entrambi i CF NULL** (buco C) | irrilevante | `NULL IS DISTINCT FROM NULL` è falso → **passa** |

**Tre cose cambiano, e nessuna indebolisce il cantiere:**

1. **Il difetto non si è mai visto perché è quasi irraggiungibile dal basso.**
   Chi è configurato bene viene già fermato — da un errore che nomina la causa
   sbagliata («id fiscali diversi» quando sono identici), ma viene fermato. È
   fermato *per effetto collaterale della cecità*, non perché qualcuno abbia
   deciso di fermarlo: è la definizione di un presidio che non c'è.
2. **P-1 non serve meno: serve su un bersaglio diverso.** Il bersaglio vero è il
   **super admin**, che è l'unico attore che resta legittimamente in grado di
   vedere due alberi e unirli. E dopo P-2a è anche l'**unico**.
3. ⛔ **Il guard di P-1 non deve leggere il padre sotto RLS.** Se lo fa, eredita
   la stessa ambiguità: un padre invisibile e un padre di un altro emittente
   producono la **stessa** risposta (niente), e il guard non sa distinguere «non
   posso vederlo» da «è di un altro». La lettura dell'emittente del padre va
   fatta da una funzione **`SECURITY DEFINER`** che risponde sempre, e la
   decisione di rifiutare va presa sul **valore**, non sull'assenza.

> ⚠️ **Per chi scriverà i test.** Un pgTAP che tenta l'albero misto **con un
> contesto operatore ristretto** vedrà il guard sollevare **anche senza P-1**, e
> passerà per la ragione sbagliata. Il test di P-1 va scritto sul percorso che
> attraversa davvero il ramo — super admin, oppure scope che copre entrambi gli
> emittenti — e deve asserire il **codice errore nuovo**, non un generico rosso.
> (È la stessa trappola di `feedback_verifica_dal_percorso_reale`: una fixture
> può *confermare* un ramo morto.)

### 11.2 🟠 «L'emittente di un BA» non è la riga di mapping: è un valore risolto

Due funzioni, indipendenti fra loro, risolvono l'emittente di un billing account
con la **stessa** catena a due livelli:

| Funzione | Livello 1 | Livello 2 |
| --- | --- | --- |
| `anagrafiche.fn_get_emittente_fiscale_id` (usata da `fn_build_fattura_key`) | mapping specifico su `billing_account_id` | fallback alla riga `is_default = true` |
| `script.fn_check_ba_visible_for_emittenti` (usata dalla RLS) | mapping specifico | fallback al default **se e solo se** il BA non ha alcun mapping |

Quindi **un BA senza riga in `emittenti_fiscali_billing_account` non è «senza
emittente»: è del gestore globale.** E i BA senza riga esistono per costruzione,
non per incidente: `trgfn_billing_account_link_ef` esce in testa quando
`app.current_user_id` è vuota — cioè su ogni creazione da seed, da batch o da
qualunque canale che non sia una richiesta web autenticata.

**Tre conseguenze operative per P-1:**

1. il guard confronta il **valore risolto** dei due lati, mai la presenza della
   riga. Un guard scritto sulle righe giudicherebbe sul NULL, cioè
   riprodurrebbe il difetto che P-3 sta chiudendo (§4) su un'altra colonna;
2. la risoluzione deve essere **la stessa** che usa `fn_build_fattura_key`, cioè
   `anagrafiche.fn_get_emittente_fiscale_id`. Un secondo risolutore che dice una
   cosa diversa produrrebbe l'esito peggiore possibile: un albero **dichiarato
   omogeneo** che la fatturazione spacca comunque. Meglio nessun guard che un
   guard che mente;
3. ⚠️ **attenzione al tipo.** Il `COMMENT` di quella funzione lo dice in
   maiuscolo: *«nonostante il nome, restituisce `soggetto_ruolo_id`, NON
   `emittenti_fiscali.id`»*. Il confronto va fatto su SR **da entrambi i lati**.
   È esattamente la coppia PK/SR su cui il progetto è già inciampato una volta.

### 11.3 🟠 Il movimento 2 di P-1 ha tre eventi, non uno

`anagrafiche.emittenti_fiscali_billing_account` ha `billing_account_id`
**nullable**, e la UNIQUE è su quella colonna: la riga del gestore globale ha
`billing_account_id` NULL e `is_default = true` (presidiata a sua volta da un
indice parziale unico). Ne segue che l'emittente di un BA può cambiare in **tre**
modi, e il brief ne prevede uno:

| Evento sulla tabella di mapping | Effetto | Nel brief? |
| --- | --- | --- |
| `UPDATE` di `emittente_soggetto_ruolo_id` | il BA cambia emittente | ✅ sì |
| `DELETE` della riga specifica | il BA **ricade sul gestore globale** → cambia emittente senza che nessuno abbia scritto un emittente | ❌ no |
| `UPDATE`/`INSERT` che sposta `is_default` | cambia in blocco l'emittente di **tutti** i BA non mappati | ❌ no |

Il terzo è il più pericoloso perché ha **raggio N**: una riga sola può spaccare
un numero arbitrario di alberi. È anche l'unico caso in cui un guard riga-per-riga
non basta e serve una verifica d'insieme.

⚠️ **E il movimento 2 gira in condizioni diverse dal movimento 1.** Quella tabella
**non ha RLS** — nessuna policy, nessun `ENABLE` — quindi il guard vede tutto e
non ha la cecità descritta in §11.1. Due guard con due visibilità diverse
producono due messaggi diversi per lo stesso difetto: è una cosa da decidere
scrivendoli, non da scoprire in collaudo.

⚠️ Nota di contorno: quella tabella non ha nemmeno `tx_id` né storico. **Un cambio
di emittente oggi non lascia traccia.** Non è in perimetro qui, ma è il genere di
cosa che si vorrà aver saputo il giorno in cui si chiederà «da quando questa
fattura esce da Pippo?».

### 11.4 🟢 P-4 è già stata fatta sei volte: il costo vero sta nelle viste

Misurato sul seed (`80_data/sql/ui/lista_colonna.csv`, 476 righe, 44 liste):

| | Liste | Colonna emittente a catalogo |
| --- | --- | --- |
| Documenti vendite | contratti (4), preventivi (5), offerte (6), ordini (7), DDT (8), resi (9) | ✅ presente — `campo_sorgente = emittente_ragione_sociale`, `tipo_colonna = informazione`, `attivo = t` |
| **Perimetro di questo brief** | lotti (12), dash aperto (39), dash backlog (40), competenza errori (41), gruppi (42), commesse (43) | ❌ **zero colonne emittente**, su 57 colonne totali |

C'è quindi un **pattern in esercizio da copiare**, non una forma da inventare — ed
è una buona notizia per il «prezzo del biglietto» di P-2b: il biglietto ha già un
listino.

Ma la misura dice anche dove sta il lavoro vero, e **non è il CSV**:

- le viste del perimetro espongono già `emittente_fiscale_id` /
  `emittente_soggetto_ruolo_id` (verificato su `vw_dash_aperto_documenti`,
  `vw_dash_backlog_documenti`, `vw_dash_competenza_errori`,
  `vw_dash_competenza_gruppi`) — **ma non la ragione sociale**, che è ciò che la
  colonna deve mostrare. Un id a video non è «dichiarare l'emittente»: è
  spostare l'ambiguità di un passo;
- ⚠️ le sei liste del perimetro hanno `vista_sql = NULL`: i dati non arrivano da
  una vista di catalogo ma dal repository di dominio, quindi la colonna
  `campo_sorgente` deve corrispondere a una chiave che **il backend produce**.
  Aggiungerla al CSV senza il campo a monte crea una colonna che si può spuntare
  e resta vuota — che è peggio di non averla, perché *sembra* la garanzia che il
  flag pretende;
- ✅ il controllo automatico chiesto in §7 (decisione 3) resta però **facile e
  onesto**, perché è puro catalogo: `multi_emittente = true` senza una riga
  emittente in `ui.lista_colonna` è una query di due join, e non ha bisogno di
  sapere niente delle viste.

### 11.4-bis ⚠️ Due cose che si chiamano quasi uguale — e non sono la stessa

Il cantiere ne maneggia **due**, legate da una regola ma diverse per tabella, per
mestiere e per chi le scrive. Confonderle è facile, ed è già successo:

| | `multi_emittente` (P-2b) | la colonna emittente (P-4) |
| --- | --- | --- |
| **Cos'è** | un sì/no: *«questa lista sa dire da quale emittente arriva ogni riga»* | una colonna **visibile a video** con la ragione sociale dell'emittente |
| **Dove sta** | `ui.lista_definizione` — una riga per **lista** | `ui.lista_colonna` — una riga per **colonna** di una lista |
| **Chi la scrive** | ⛔ **solo** il seed, presidiato dal trigger (§11.5) | il seed, come qualunque altra colonna di catalogo |
| **Chi la guarda** | il cancello all'ingresso della lista | l'operatore |

**La regola che le lega**, ed è l'unica: il flag si può mettere a `true` **solo**
su una lista che ha già la colonna. Quindi si fanno **in quest'ordine** — prima
la colonna, poi il flag — e mai al contrario.

> Detto in una riga: **la colonna è il lavoro, il flag è la ricevuta.** Una
> ricevuta senza il lavoro è esattamente il difetto che il flag doveva impedire.

⚠️ **Il trigger di §11.5 sorveglia una tabella e una colonna**: `multi_emittente`
su `ui.lista_definizione`. Non tocca `ui.lista_colonna`, e non tocca le altre
colonne di `lista_definizione` (`codice`, `descrizione`, `schema_dati`,
`vista_sql`, `note`, `attivo`) — che restano scrivibili dall'amministrazione
super-admin esattamente come oggi, con la whitelist del service come unico
filtro.

### 11.5 🔴 Lo Strato 1 di P-2b non regge — e il modo in cui cede è invisibile su dev

Il brief chiedeva di verificare *«che nessun changeSet di `90_end` ri-conceda
`UPDATE` a livello di tabella su `ui.lista_definizione`»*. **Uno lo fa, ed è
quello che concede i permessi a tutta l'applicazione:**

`db/changelog/migrations_v2/90_end/ci_apply/20260205-41-apply-runtime-grants-ci-mctit.yaml`

```yaml
context: ci_apply
runOnChange: true
validCheckSums: [ANY]
```

Il suo corpo cicla su 14 schemi — **`ui` compreso** — e per ogni tabella posseduta
esegue:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE <tabella> TO zeroerp_app;
```

In PostgreSQL l'`UPDATE` concesso a livello di **tabella** copre **tutte** le
colonne, presenti e future: una `REVOKE` seguita da `GRANT UPDATE (col, col, …)`
viene **annullata** dal giro successivo.

⛔ **E non è un problema d'ordine, quindi non si risolve numerando più avanti.**
Essendo `runOnChange: true` in contesto `ci_apply`, quel changeSet ri-esegue **a
ogni passata di quel contesto**, e quel contesto è sempre **l'ultimo**.

#### ⚠️ Chi lo esegue davvero — verificato il 2026-08-17

> 🔴 **Una prima stesura di questo paragrafo diceva «ci pensa il giro serale del
> pgagent». È falso, e la correzione conta**: il *quando* cambia da «ogni notte»
> a «ogni build della CI», e cambia in peggio.

| Dove | Chi lancia | Quando |
| --- | --- | --- |
| **CI** | il workflow, `update --contexts=ci_apply` | ⚠️ **a ogni build**, e sempre **dopo** `update --contexts="!provision"` che ha applicato la revoca |
| **Sviluppo** | una persona, `make db-ci-apply` (o `make db-setup`, che lo concatena) | solo quando qualcuno lo digita — **niente lo pianifica** |

⚠️ **I job pgagent non c'entrano.** Verificato: i nove job di `85_pgagent` hanno
tutti step di tipo SQL (`jstkind = 's'`) e chiamano `maintenance.proc_*` —
automazioni `tx_id` / `audit` / `storico` / `attivo` / `lock_columns`, policy
indici FK, cleanup. **Nessuno di essi esegue un `GRANT`.** La confusione nasce
dal fatto che automazioni e grant **condividono il contesto `ci_apply`**, ma
hanno due esecutori diversi: le automazioni ne hanno **due** (Liquibase +
pgagent), i grant **uno solo** (Liquibase).

**La conseguenza è peggiore di quella che avevo scritto, non migliore:**

- su **sviluppo** la revoca sopravvive fino al successivo `make db-ci-apply`. Non
  è una notte: è finché nessuno riallinea il database. Sembra funzionare, e più a
  lungo — il che la rende più credibile;
- in **CI** non funziona **mai**, nemmeno per un istante utile. Il database è
  ricostruito da zero: la passata `!provision` applica la revoca, la passata
  `ci_apply` che viene **dopo** la annulla, nello stesso build. Su un database
  nuovo la colonna è scrivibile **sempre**.

> È il caso di scuola della divergenza dev/CI, nella forma più insidiosa: la
> difesa più forte fra le tre proposte funziona **solo** dove la si prova a mano,
> e **non** dove conta. Una difesa che si spegne è peggio di una difesa che non
> c'è, perché la prima la dai per buona.

**Le tre strade, e quale si sceglie:**

| | Come | Costo | Tiene? |
| --- | --- | --- | --- |
| ⭐ **Trigger** | `BEFORE UPDATE OF multi_emittente` su `ui.lista_definizione` che solleva se `current_user` è il ruolo applicativo | un oggetto, ~15 righe | ✅ **sì** — i trigger non li tocca il giro dei grant |
| Grant per colonna nel loop | mettere mano a `20260205-41` perché su quella tabella conceda per colonna | permanente, su un file condiviso da 14 schemi; ogni colonna nuova diventa un intervento lì | ✅ sì, ma il presidio finisce lontano dalla cosa che presidia |
| Rinuncia | Strati 2+3 soltanto, dichiarandolo | zero | ❌ no |

**Si sceglie il trigger**, e non è un ripiego: è più piccolo, sta **accanto** alla
colonna che protegge invece che in un file di infrastruttura condiviso da 14
schemi, e non introduce una lista di colonne da mantenere allineata a mano.

⚠️ **Senza GUC di override, e per la stessa ragione di P-1.** Il seed passa perché
il migrate gira come *owner*, non perché qualcuno accende un interruttore: la
condizione è `current_user`, e non c'è niente da accendere. Un invariante con
l'interruttore non è un invariante — vale qui come vale là.

⚠️ **Lo Strato 1 così cambia natura, e va detto.** Non è più «l'applicazione non
ha il diritto», è «il database rifiuta la scrittura». Si perde la proprietà
buona che il brief citava — *una colonna nuova nasce non scrivibile* — perché il
trigger nomina **una** colonna. È un prezzo reale: si compra un presidio che
tiene, si vende un presidio che si estendeva da solo. Dato che il secondo non
teneva, il baratto è a favore.

### 11.6 🟠 P-2a ha una superficie di rottura in più, e sta nel backend

`backend/apps/core/db/search_repository.py`, righe **42** e **98**, identiche:

```python
pg_emittente_ids = emittente_ids if emittente_ids else None
```

In Python **la lista vuota è falsa**. Quindi `[]` — che nella convenzione dello
scope significa *«nessun accesso»* — diventa `None`. E a valle,
`script.fn_search_soggetti_universale` applica il filtro con:

```sql
IF v_tipo_ruolo_codice = 'CL' AND p_emittente_ids IS NOT NULL THEN …
```

cioè `NULL` significa *«nessuna restrizione»*. **I due estremi opposti della
convenzione collassano sullo stesso valore, e collassano dalla parte che apre.**

- **Oggi** è già un difetto vivo, indipendente da questo cantiere: chi non ha
  identità OPERATORE attiva riceve `{}` dal database e la ricerca universale gli
  risponde **come se vedesse tutto**;
- **dopo P-2a** lo scope vuoto diventa lo stato **normale** dell'operatore non
  configurato. Il difetto passa da latente a sistematico, e per giunta proprio
  sulla superficie a cui P-2c assegna «etichetta, non cancello» — cioè la meno
  presidiata.

⚠️ **Questo è un difetto BE e va corretto PRIMA di P-2a**, non dopo: applicare
P-2a per primo trasformerebbe una correzione fail-closed in un **allargamento di
visibilità** su quella superficie. La richiesta è in **§13**.

Gli altri consumatori sono stati controllati e sono corretti (`apps/core/mixins.py`,
`billing_account_repository.py`, `istanze_utility_repository.py`: tutti su
`is not None`). ⚠️ La regola generale, che vale per il prossimo consumatore:
**questa convenzione a tre stati non si legge mai con un test di verità.**

### 11.7 Due imprecisioni minori, da correggere per non far perdere tempo in collaudo

- **§2.5, riga «scrittura».** `fn_check_user_can_create_ba` **non consulta
  `fn_is_super_admin`**: anche un super admin senza riga e senza emittente attivo
  riceve `false`, e passa solo se l'istanza ha zero emittenti attivi. L'asimmetria
  lettura/scrittura che il brief usa come prova **regge, anzi è più netta** — ma
  la tabella di §2.5 non ha la riga «super admin», e in collaudo quel caso salta
  fuori subito. (È anche il motivo per cui il super admin, in pratica, un
  billing account lo crea **scegliendo un emittente attivo**: la GUC è il suo
  primo ramo.)
- **§3.3, terzo punto.** *«Il vincolo referenziale su `parent_account_id` non
  applica le policy RLS»* è corretto ed è comportamento documentato di
  PostgreSQL. Ma il pgTAP che il brief propone per confermarlo **misurerebbe
  PostgreSQL, non noi**: il fatto che serve verificare è un altro, ed è §11.1 —
  *che cosa vede il guard quando legge il padre*. Quello sì va scritto, ed è il
  test che oggi non c'è.

### 11.8 Cosa il brief prende giusto — verificato riga per riga

Non è una formalità: sono i punti su cui **non serve tornare**.

| Affermazione | Esito |
| --- | --- |
| `UNIQUE(auth_user_id)` su `config.user_emittenti_fiscali` | ✅ `uq_user_emittenti_fiscali_auth_user` |
| La descrizione della tabella dichiara il fail-open | ✅ testuale: *«se l'utente non ha righe può operare su TUTTI gli emittenti»* |
| I tre esiti di `fn_get_emittenti_scope_pk_ids` + il quarto caso | ✅ il ramo `ELSE` fa `array_agg` su zero righe → `NULL` |
| `fn_check_user_emittente_scope` → `true` su whitelist vuota | ✅ ramo 5, col commento *«nessuna restrizione»* |
| Il precedente di `fn_get_emittenti_scope_sr_ids` (2026-08-04, fail-closed) | ✅ testuale nel `coalesce(…, '{}')`, col commento che spiega perché |
| Gli adapter ereditano la correzione senza modifiche | ✅ `via_efba` → `_sr_ids` → `_pk_ids`, e tratta già `cardinality = 0` come `false` |
| Il motore dell'emittente attivo è completo (GUC, endpoint, intersezione) | ✅ tutti e tre |
| `fn_build_fattura_key` prende l'emittente dal padre | ✅ `fn_get_emittente_fiscale_id(COALESCE(parent_account_id, billing_account_id))` |
| La RLS di INSERT su `billing_account` è gate-only, e il perché | ✅ ed è **scritto nel changeSet stesso**, con la stessa motivazione del brief |
| Le sei liste del perimetro sono tutte a catalogo, su 44 | ✅ id 12, 39, 40, 41, 42, 43 |
| Esiste una sola dashboard (`home`) con quattro widget | ✅ e tre dei quattro sono sulle aree in questione |
| Il CRUD admin su `ui.lista_definizione` ha una whitelist che protegge | ✅ `_UPDATE_KEYS = _CREATE_KEYS`, sei chiavi, `multi_emittente` non ci sarebbe |
| Il commento «Tutti i campi sono mutabili (nessun immutabile per design)» | ✅ riga 192 del service — la trappola è reale |
| Il loader del CSV è `loadUpdateData` + `runOnChange` + `validCheckSums: ANY` | ✅ estendibile in place, come previsto |
| `ui.fn_resolve_lista_config` restituisce un envelope JSON estendibile | ✅ e **accetta già `p_emittente_fiscale_id`** come parametro |

---

## 12. Piano di sviluppo

> **Come leggerlo.** Otto passi in quattro fasi. Ogni passo dichiara **cosa
> produce**, **come si verifica** e **quando è finito**. I passi con ⛔ hanno un
> prerequisito duro: iniziarli prima è lavoro che va rifatto.
>
> ⚠️ **Numerazione Liquibase**: gli `NN` indicati sono segnaposto. Il numero vero
> è il **prossimo libero della giornata di applicazione**, in sequenza **globale
> fra tutte le cartelle** — il 2026-08-17 la giornata è già a `-14`.
>
> ⛔ **Nessun passo di questo piano applica migrazioni.** Si scrive, si valida
> (`liquibase validate` / `updateSQL`, che non applicano), si consegna. L'apply
> lo autorizza Tid a voce, per quel comando.

### Fase 0 — Misure e prerequisiti · *non produce changeSet*

> ✅ **ESEGUITE il 2026-08-18** (sola lettura, come owner per non contare sotto
> RLS — [[feedback_conteggi_rls_zero_non_errore]]).
>
> | Misura | Valore | Cosa vuol dire |
> | --- | ---: | --- |
> | **DL-A** operatori non configurati | **2 → ✅ 0** | ⛔ era il prerequisito di P-2a. **Sanato il 2026-08-18**: `auth_user_id` **8** (*Rossi Mario*) → **EMI-TEST** (`ef.id` 44, P.IVA 45807930719), **187** (*Renchi Luigi*) → **PGTAP** (`ef.id` 32, P.IVA 09999999999). Fatto con la funzione di dominio `script.fn_change_user_emittenti_scope`, non con un `INSERT` a mano. ⚠️ Verificato che l'operatore scelto da `fn_pgtap_set_contesto_operatore` **non cambi** (resta il 5): entrambi gli id nuovi sono più alti, altrimenti sarebbe cambiato il contesto di tutta la suite |
> | **DL-B** alberi misti | **0** | — |
> | **DL-C** coppie con CF NULL | **0** | — |
> | **DL-D** BA senza mapping specifico | **0** | tutti e 42 i BA hanno il loro mapping: il ripiego sul gestore globale **oggi non è in gioco** |
> | **DL-D2** coppie miste per mapping | **0** | il guard del 4° movimento (Q3) non ha nulla da far scattare |
>
> 🔴 **E il numero che conta più di tutti: `parent_account_id` è valorizzato su
> ZERO billing account.** Su 42 BA non esiste **nessun albero**. Quindi:
>
> - **P-1 e P-3 non faranno scattare niente sul pregresso**: rumore atteso zero,
>   e la decisione «nessuna bonifica» non ha nulla da bonificare;
> - ⚠️ **ma i dati di sviluppo qui non misurano proprio niente.** La gerarchia
>   padre/figlio in dev **non è mai stata usata**: il guard §2.2 non è mai
>   scattato, e `fn_build_fattura_key` non ha mai preso l'emittente dal padre.
>   È territorio inesplorato, non territorio sano — la domanda resta «può
>   succedere?», non «è successo?» ([[feedback_dati_test_non_misurano_la_gravita]]);
> - ⭐ **conseguenza operativa: i test devono costruirsi l'albero.** Non c'è
>   niente su cui appoggiarsi, e un test che «cerca una coppia esistente»
>   salterebbe sempre.
>
> ⭐ **Due cose utili emerse dalla stessa misura**, entrambe usate subito:
>
> - ci sono **2 emittenti attivi** (SR **72** *Gestore Test pgTAP*, che è anche
>   il gestore globale, e SR **159** *Azienda SC REQUIRED con dati*): una
>   fixture a due emittenti **è possibile**, quindi il «buco dichiarato» del
>   test del passo 1 si può chiudere e P-1 può costruire un albero misto vero;
> - **1 BA è mappato su SR 159**, cioè è **invisibile** all'operatore di
>   contesto pgTAP (che ha scope `{72}`): è lo scenario di §11.1 **riproducibile
>   in un test**, e infatti il passo 3 lo verifica.

| # | Cosa | Blocca |
| --- | --- | --- |
| **0.1** | **DL-A** — operatori con identità OPERATORE, non super admin, senza riga in `config.user_emittenti_fiscali`. **Aggiungere le righe mancanti.** | ⛔ P-2a (passo 2) |
| **0.2** | **DL-D** — billing account senza riga in `emittenti_fiscali_billing_account` (§11.2). Non si bonifica: serve a dimensionare il rumore e a scegliere le fixture | 🔵 informa P-1 |
| **0.3** | **DL-B / DL-C** — alberi che attraversano due emittenti; coppie padre/figlio con un CF NULL | 🔵 informa P-1 e P-3 |
| **0.4** | **Grep pgTAP** su `anagrafiche.billing_account`: **14 file** scrivono su quella tabella, 3 sono specificamente sui suoi guard (`test-billing-account-guard-parent`, `test-billing-account-auto-link-ef`, `test-trgfn-billing-account-guard-soggetto-coerenza-istanza-v1`). È il raggio d'urto di P-1 | ⛔ P-1 (passo 4) |
| **0.5** | `scripts/pgtap-baseline.sh anagrafiche` **prima** di toccare qualsiasi cosa | ⛔ tutto: senza, un rosso preesistente sembrerà una regressione propria |

> ⚠️ **DL-A non è «dato sporco che si tollera».** La decisione 5 («niente
> bonifica») riguarda i dati; questa è **configurazione mancante**, e la
> differenza è che un guard si annuncia mentre una schermata vuota no. Le righe
> costano un `INSERT` a testa e vanno messe **prima**.

### Fase 1 — Chiudere il perimetro di lettura

#### Passo 1 · La ricerca universale si risolve lo scope da sé · *decisione Q2/C*

> ⚠️ **Questo passo era «richiesta al BE, e blocca il passo 2». Non lo è più.**
> Con la decisione Q2 il lavoro rientra nel perimetro DB e **non blocca niente**:
> si fa perché è il posto giusto, non perché qualcosa lo aspetta.

`script.fn_search_soggetti_universale` e `script.fn_get_search_detail` sono **le
uniche due** funzioni di scope che si fidano di un array calcolato dal chiamante
invece di risolverlo. Passano a risolverlo da sé.

✅ **APPLICATO il 2026-08-18 — nessuna regressione sui test.** Tre changeSet + un pgTAP, su
`dev/db-tid`. Nessuna migrazione eseguita, nessun commit.

| File | Cartella | Cosa |
| --- | --- | --- |
| `20260818-01-create-fn-get-emittenti-scope-sr-effettivo-mctit.yaml` | `20_code/script` | ⭐ **il pezzo nuovo**: `diritto ∩ richiesto`, con NULL = universo su entrambi i lati. Estratto perché serve a **due** chiamanti |
| `20260818-02-update-fn-search-soggetti-universale-scope-interno-mctit.yaml` | `20_code/script` | il filtro si accende su `v_scope IS NOT NULL` invece che su `p_emittente_ids IS NOT NULL` |
| `20260818-03-update-fn-get-search-detail-scope-interno-mctit.yaml` | `20_code/script` | ramo CL: `v_scope IS NULL OR …` al posto di `p_emittente_ids IS NULL OR …` |
| `db/pgtap/script/test-search-scope-interno-v1.sql` | `db/pgtap` | 12 asserzioni (vedi sotto) |

**Verifica fatta prima di consegnare** — il corpo nuovo è stato **diffato contro
la definizione viva** (doc auto-gen) per entrambe le funzioni: le uniche
differenze sono le righe volute. Il blocco di SQL dinamico di
`fn_search_soggetti_universale` è identico byte per byte, il che è ciò che conta
di più — è la parte che una ricopiatura a mano degrada senza dirlo.

⚠️ **Due trappole pagate scrivendolo, entrambe già in memoria e sfuggite lo
stesso:**

1. **firma e `RETURNS TABLE` presi dalla doc auto-gen**, che scioglie i `%TYPE`.
   Corretto: vanno dall'ultimo YAML;
2. ⭐ **e «l'ultimo YAML» non basta.** Per `fn_get_search_detail` l'ultima
   revisione (`20260628-10`) aveva **già** i `%TYPE` sciolti — era stata a sua
   volta ricostruita dall'auto-gen. Copiarla non avrebbe degradato la firma:
   l'avrebbe resa **definitiva**. La firma buona stava due revisioni indietro
   (`20260410-02`). La regola va letta per il suo scopo: **l'ultimo YAML che li
   ha ancora**. Due indizi visibili a colpo d'occhio: la firma su **una riga
   sola** e i `DEFAULT NULL::integer` con cast esplicito — è la punteggiatura di
   `pg_get_functiondef`, non di una firma scritta a mano.
   ⛔ E non si cerca «l'ultimo» con `ls -t`: ordina per data di modifica del
   file, che dopo un `git checkout` non dice niente. Conta l'ordine della
   **timeline**, cioè il nome.

**Regole di costruzione**

- ⭐ **il parametro può solo restringere.** `scope_effettivo = scope_dalla_GUC ∩
  p_emittente_ids`, con `NULL` = universo su entrambi i lati. È lo stesso
  invariante *«solo restringente, mai allargante»* dell'emittente attivo
  (rev 2026-08-04): non si inventa una regola, se ne riusa una;
- **il parametro non si toglie dalla firma.** Toglierlo romperebbe i due
  chiamanti e obbligherebbe a coordinare un rilascio BE — che è esattamente la
  dipendenza da cui questo passo ci sta liberando. Resta, e diventa innocuo;
- **attore nullo → nessun filtro**, come `fn_scope_ef_whitelist_via_efba` ramo 1
  (decisione dentro Q2: si segue la convenzione della famiglia);
- ⚠️ `fn_search_soggetti_universale` applica lo scope **solo per tipo ruolo `CL`**:
  non è un difetto da correggere qui, ma va **saputo** — sulle altre tipologie
  non c'è scope da restringere, e il passo non lo introduce.

**Verifica** — `db/pgtap/script/test-search-scope-interno-v1.sql`, **12
asserzioni**, di cui la prima è una **precondizione dichiarata**: il contesto
pgTAP è un operatore con scope proprio. Senza quella, i primi cinque test
confronterebbero `NULL` con `NULL` e sarebbero verdi per sottrazione.

| # | Cosa | Deterministico? |
| --- | --- | --- |
| 0 | precondizione: scope del contesto ≠ NULL | ✅ |
| 1 ⭐ | restrizione assente (`NULL`) **non** significa più «nessuna restrizione» | ✅ |
| 2 | restrizione assente → vale lo scope di diritto | ✅ |
| 3 | `'{}'` resta `'{}'`: non degrada mai a `NULL` | ✅ |
| 4 | restrizione **fuori** scope → `'{}'` (non allarga) | ✅ |
| 5 | restrizione = proprio scope → invariato (il caso del backend di oggi) | ✅ |
| 6 | attore nullo senza restrizione → `NULL` (convenzione famiglia) | ✅ |
| 7 | attore nullo **con** restrizione → la restrizione resta | ✅ |
| 8–9 | ricerca CL: `NULL` == proprio scope · restrizione fuori scope → 0 righe | 🟡 skip dichiarato se non c'è un cliente utilizzabile |
| 10–11 | idem su `fn_get_search_detail` | 🟡 come sopra |

⚠️ **Il «fuori scope» non si pesca dai dati**: è un `soggetto_ruolo_id` che **non
esiste** (`MAX(id) + 1000000`). Scegliere un secondo emittente reale renderebbe
il test dipendente dalla popolazione — l'istanza potrebbe averne uno solo — e
passerebbe a giorni alterni.

🕳️ **Buco dichiarato, non coperto per sbaglio**: i test 8–11 verificano
l'*invariante* «il parametro non decide più», confrontando due chiamate. **Non**
dimostrano che un cliente di un altro emittente sparisce: per quello servirebbe
una fixture a **due** emittenti con un cliente ciascuno, che questo file non
costruisce. È scritto nell'intestazione del test, non solo qui.

**Fatto quando**: le 12 asserzioni sono verdi e nessun valore passato dal
chiamante può più **allargare** ciò che la funzione mostra.

⚠️ **Residuo, non chiuso qui**: il filtro emittente si applica **solo al tipo
ruolo `CL`** — è l'unico che ha un billing account da cui derivare l'emittente. I
rami `FO` ed `ELSE` non ne hanno mai avuto uno. Il passo 1 non lo amplia, e
l'obiettivo dichiarato regge lo stesso: *nessun valore del chiamante può
allargare*. Ma resta vero che una ricerca fornitori non conosce perimetro.

#### Passo 2 · P-2a — fail-closed nella catena canonica · *prerequisito sciolto*

✅ **APPLICATO il 2026-08-18 — nessuna regressione sui test.** Il prerequisito DL-A è stato
sanato lo stesso giorno (sopra), quindi il passo non è più bloccato.

| File | Cartella | Cosa |
| --- | --- | --- |
| `20260818-11-update-fn-get-emittenti-scope-pk-ids-fail-closed` | `20_code/script` | ramo `ELSE`: `coalesce(array_agg(…), '{}')` |
| `20260818-12-update-fn-check-user-emittente-scope-fail-closed` | `20_code/script` | ramo 5: `v_cnt = 0` → `false` |
| `20260818-13-comment-user-emittenti-fiscali-fail-closed` | `20_code/config` | il `COMMENT` che dichiarava il contrario |
| `20260818-14-create-vw-operatori-senza-emittente` | `20_code/dbops` | la diagnostica |
| `db/pgtap/script/test-scope-emittenti-fail-closed-v1.sql` | — | 8 asserzioni |

✅ **Dopo l'applicazione: 8 su 8 verdi.**

⭐ **La misura PRIMA di applicare, che è quella che vale** (tenuta qui perché è
la prova che il test misurava il difetto e non se stesso): a changeSet non
applicati **4 asserzioni su 8 fallivano, ed erano esattamente le quattro della
correzione**, con i vecchi valori (`NULL`, `true`). Il ramo super admin passava
già, cioè non veniva toccato. ⚠️ Un test scritto dopo la correzione e verde al
primo colpo non dice niente: questo è stato visto rosso per la ragione giusta.

⚠️ **La fixture del test ha dovuto ricreare il difetto**: DL-A è ormai a zero,
quindi un operatore senza riga **non esiste più** e va costruito togliendo lo
scope a un operatore vero con `fn_change_user_emittenti_scope(x, '{}')`, dentro
la transazione. Si evita di proposito l'operatore del **contesto pgTAP**: è
quello da cui dipendono le policy RLS durante la corsa.

#### 🔬 Applicato il 2026-08-18 — e ha rotto quattro asserzioni che erano il **vecchio contratto**

Tre file di `script` sono diventati rossi, con **quattro** asserzioni:

| File | Asserzione |
| --- | --- |
| `test-fn-scope-ef-whitelist.sql` | *«whitelist vuota → true (accesso globale)»* |
| `test-permessi-fn-check-emittente-scope.sql` | *«OPERATIVO senza whitelist → true»* |
| `test-permessi-funzioni-risoluzione.sql` | idem, **e** *«…scope_sr_ids → NULL»* |

⚠️ **Non erano fixture rimaste indietro: erano la regola precedente, scritta.**
Qualcuno l'aveva messa a contratto in quattro punti, con la nota «nessuna
restrizione» accanto.

> 🔴 **Questo corregge, in parte, una frase di §2.5.** Il brief intitola quel
> paragrafo *«la prova che "whitelist vuota = vede tutto" è un **residuo**, non
> una scelta»*. Quattro asserzioni che lo affermano dicono che **una scelta c'è
> stata**, in qualche momento. Ciò che regge intatto è l'**argomento**, non la
> ricostruzione storica: il lato scrittura rifiutava già lo stesso utente
> (`fn_check_user_can_create_ba` → `false`), e le due letture non potevano
> essere entrambe intenzionali. Era una scelta, ed era incoerente con l'altra
> metà del sistema — che è una tesi più forte, non più debole.

Le quattro sono state **riscritte, non riallineate**: valore invertito *e*
motivo scritto sopra, perché un'asserzione girata senza spiegazione è il
prossimo che la rigira. Dopo: `script` **12 rossi su 59, tutti già noti,
nessuna regressione**.

⚠️ **Errore di processo mio, da non ripetere**: il grep pgTAP del passo 0.4 lo
avevo fatto solo su `anagrafiche.billing_account`, cioè sulla **tabella** del
guard. Ma P-2a tocca delle **funzioni**, e i test che le esercitano stanno in un
altro schema. Il perimetro del grep è *ciò che si modifica*, non *la tabella su
cui si scrive*.

⭐ **I test 6 e 7 misurano l'eredità invece di assumerla.** Il brief sostiene
che gli adapter si sistemano «per costruzione» perché trattano già
`cardinality = 0` come nessun accesso. Sostenerlo non basta: `_sr_ids` e
`via_efba` hanno la loro asserzione, e oggi falliscono entrambe — il che prova
che la catena è davvero quella e non un'altra.

<!-- il piano originale del passo 2 resta qui sotto -->

##### Il piano com'era scritto

| File (indicativo) | Cartella | Cosa |
| --- | --- | --- |
| `AAAAMMGG-NN-update-fn-get-emittenti-scope-pk-ids-fail-closed-mctit.yaml` | `20_code/script` | ramo `ELSE`: `array_agg` a vuoto → `'{}'` invece di `NULL` |
| `AAAAMMGG-NN-update-fn-check-user-emittente-scope-fail-closed-mctit.yaml` | `20_code/script` | ramo 5: `v_cnt = 0` → `false` invece di `true` |
| `AAAAMMGG-NN-comment-user-emittenti-fiscali-fail-closed-mctit.yaml` | `20_code/config` | riscrive il `COMMENT ON TABLE` (oggi dichiara il contrario) |
| `AAAAMMGG-NN-create-vw-operatori-senza-emittente-mctit.yaml` | `20_code/dbops` | vista di diagnostica: chi è configurato a metà |

**Regole di costruzione**

- corpo **dalla doc auto-generata**, firma e `RETURNS` **dall'ultimo YAML** — la
  auto-gen scioglie i `%TYPE`;
- `runOnChange: false` (è `20_code`: obbligatorio, presidiato in CI);
- il ramo super admin **non si tocca**;
- `fn_get_emittenti_scope_sr_ids` e i due `fn_scope_ef_whitelist_via_*` **non si
  toccano**: ereditano (§11.8).

**Verifica** — pgTAP `db/pgtap/script/test-scope-emittenti-fail-closed-v1.sql`:

1. operatore **con** riga → array di 1 (invariato);
2. operatore **senza** riga → `'{}'` **e** `fn_check_user_emittente_scope` false;
3. super admin → `NULL` (invariato);
4. super admin **con emittente attivo** → array di 1 (l'intersezione regge);
5. `fn_scope_ef_whitelist_via_efba` per l'operatore senza riga → **false**
   (l'eredità è verificata, non assunta).

> ⚠️ **Non azzerare `app.current_user_id` per «verificare il fail-closed»**:
> `fn_scope_ef_whitelist_via_sr(NULL)` risponde **TRUE**. Il cancello vero è
> `app.ruolo_applicativo`. Un test che azzera lo user id è **verde per
> sottrazione**.

**Fatto quando**: i cinque casi sono verdi, la baseline `script` non ha
regressioni, e il `COMMENT` non dice più una cosa falsa.

### Fase 2 — Chiudere il perimetro di scrittura

#### Passo 3 · P-3 — il fail-open del NULL nel guard CF

✅ **APPLICATO il 2026-08-18 — nessuna regressione sui test.**

| File | Cosa |
| --- | --- |
| `20260818-05-update-trgfn-billing-account-guard-normalize-soggetto-confrontabile-mctit.yaml` | `20_code/anagrafiche` — il §2.2 riscritto |
| `codici_errore.csv` · `messaggi_errore.csv` | **append** di 2 codici, classe `DATO_ERRATO` |
| `db/pgtap/anagrafiche/test-billing-account-guard-cf-confrontabile-v1.sql` | 7 asserzioni |

⚠️ **DUE SCOSTAMENTI dal testo di P-2/P-3, entrambi voluti.** Il brief diceva:
*«trattare il NULL come non confrontabile e quindi rifiutare»*.

**1. Non si rifiuta sul NULL: si ripiega sul soggetto.** Rifiutare ogni coppia
con un CF mancante avrebbe rotto un caso **legittimo** — due BA dello **stesso**
soggetto, che semplicemente non ha il codice fiscale valorizzato. Il difetto che
§4 descrive è *«un albero fra soggetti **diversi** diventa costruibile»*, e il
soggetto è sempre disponibile: risponde alla domanda vera. Il CF resta il
criterio primario (due soggetti diversi con lo **stesso** CF continuano a
passare: quella è identità fiscale, ed è ciò che il guard presidia).
→ nuovo codice `E_PARENT_SOGGETTO_DIVERSO`.

**2. «Padre non raggiungibile» diventa un caso suo.** È §11.1 chiuso **al passo
3 invece che al passo 4**: la `SELECT` sul padre passa dalle policy RLS, quindi
un padre di un altro emittente non viene trovato e prima cadeva su
`E_ID_FISCALI_DIVERSI` — con i due CF **identici**. Ora ha il suo codice.
⚠️ Il guard **non finge** di distinguere «non esiste» da «non lo vedi»: non può,
e il messaggio lo dichiara.
→ nuovo codice `E_PARENT_NON_RAGGIUNGIBILE`.

> 🔗 **Questo tocca Q5**, che diceva «il messaggio sbagliato non si corregge,
> sparisce da sé con P-1». Sparisce **prima**, e senza codice usa-e-getta: non è
> una correzione di passaggio, è il guard che smette di dire una cosa falsa
> mentre lo si sta comunque riscrivendo. La decisione di Q5 — *niente codice
> intermedio* — resta rispettata.

**Verifica** — 7 asserzioni, di cui tre sono il cuore:

| # | Caso | Atteso |
| --- | --- | --- |
| 1 | stesso soggetto, CF presente | ✅ passa (nessuna regressione) |
| 2 | soggetti diversi, CF diversi | ❌ `E_ID_FISCALI_DIVERSI` (invariato) |
| 3 ⭐ | soggetti diversi, **entrambi senza CF** | ❌ `E_PARENT_SOGGETTO_DIVERSO` — **era il fail-open** |
| 4 ⭐ | **stesso** soggetto senza CF | ✅ passa — il falso positivo evitato |
| 5 ⭐ | padre **fuori dal perimetro RLS** | ❌ `E_PARENT_NON_RAGGIUNGIBILE` — lo scenario §11.1, riprodotto |
| 6 | padre inesistente | ❌ stesso codice (il guard `BEFORE` precede la FK) |

⚠️ **I codici si discriminano con `throws_like` sulla frase, non con
`throws_ok('P0001')`**: `P0001` dice *«è un errore di dominio»*, non **quale** —
e qui i tre casi che contano si distinguono solo per il codice.

⚠️ **La fixture azzera il CF dentro la transazione** (chiusa in `ROLLBACK`).
Non è bonifica: nell'istanza esiste **un solo** soggetto senza CF, e un test che
dipendesse da quello misurerebbe la popolazione invece della regola.

**Stato al 2026-08-18: 6 asserzioni su 7 verdi**, e la settima e' bloccata da un
difetto che il test ha scoperto (sotto). Baseline `anagrafiche`: **nessuna
regressione** — l'unico rosso nuovo e' questo file stesso.

#### 🔴 Difetto trovato eseguendo il test: tre messaggi del catalogo mandano in crash `format()`

Il test 2 falliva cosi':

```
error message: 'identificatore di tipo format() non riconosciuto ")"'
doesn't match: '%id fiscale diverso%'
```

`script.fn_log_and_raise_error` compone il messaggio con `format(...)`. Tre righe
di `config.messaggi_errore` hanno un segnaposto che `format()` **rifiuta**:

| Codice | Segnaposto rotto | Argomenti passati |
| --- | --- | --- |
| `E_ID_FISCALI_DIVERSI` | `%` nudo, tre volte | 3 ✅ |
| `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO` | `%S` maiuscola (`format` e' case-sensitive) | 2 ✅ |
| `E_SOGGETTI_RUOLI_RACE` | `%."` in coda | 3 ✅ |

**Nessuno dei tre e' un problema di argomenti**: il numero passato dai chiamanti
e' giusto. E' proprio il segnaposto scritto male.

⚠️ **La conseguenza e' peggiore di un messaggio brutto: l'errore di dominio
sparisce.** `format()` solleva un `22023`, non il `P0001` che il contratto
DB→backend richiede — quindi il campo `CONSTRAINT` non arriva, il codice non
viene riconosciuto e l'operatore riceve un errore tecnico al posto della frase
che qualcuno aveva scritto per lui.

⚠️ **E si vede solo quando l'errore scatta davvero.** `E_ID_FISCALI_DIVERSI` e'
rotto da sempre e non se n'e' accorto nessuno per la ragione misurata in Fase 0:
**non esiste nessun albero di billing account**, quindi quel guard non e' mai
scattato. Un messaggio non esercitato non e' un messaggio funzionante.

**Corretti tutti e tre nel CSV** (`messaggi_errore.csv`, mirror `runOnChange`:
si riallinea al prossimo migrate). Gli altri due sono fuori dal perimetro di
questo cantiere, ma sono lo stesso difetto di un carattere trovato dalla stessa
misura: lasciarli rotti sapendolo sarebbe stato peggio che correggerli.

#### ⚠️ Tre trappole nella fixture, tutte pagate eseguendo

Nessuna era prevedibile leggendo il brief, e valgono per chiunque scrivera' test
su `billing_account`:

1. **`ON COMMIT DROP` va DOPO l'elenco colonne.** Regge prima solo nella forma
   `CREATE TEMP TABLE x ON COMMIT DROP AS SELECT …`;
2. **`SET CONSTRAINTS ALL IMMEDIATE` non puo' stare in testa**, qui: il
   constraint differito `trg_istanze_utilities_z90_require_utility_dichiarata_ins`
   pretende che ogni istanza abbia gia' un satellite, e la fixture ne crea due
   in due istruzioni. Va **dopo** la fixture — ed e' l'avvertenza del template,
   che dice «dove l'unita' di lavoro e' completa», non «sempre in testa»;
3. ⭐ **`soggetti.id_fiscale_univoco_cf_piva` e' una colonna GENERATA**
   (`CASE` su `codice_fiscale`/`partita_iva`): non si scrive. E azzerare le
   sorgenti **non basta** — il guard `trgfn_soggetti_guard_cf_piva_obbligatori`
   legge da `config.tipi_soggetto_dettaglio` se CF/PIVA sono obbligatori, e
   **nessun tipo configurato oggi li ammette entrambi nulli**: esce in testa solo
   se il tipo non e' dichiarato.

> 🔎 **Il punto 3 restringe — onestamente — la portata dello scostamento (1) di
> P-3.** Il «caso legittimo» che il ripiego sul soggetto protegge (due BA dello
> stesso soggetto senza CF) e' raggiungibile **solo** per un soggetto senza tipo
> dettaglio, cioe' un record configurato a meta'. La scelta resta giusta — lo
> schema ammette il NULL e un guard si scrive contro lo schema, non contro i
> flag che una tabella di configurazione ha **oggi** — ma non e' il caso
> frequente che potevo lasciar intendere.

**Fatto quando**: le 7 asserzioni sono verdi. Le prime 6 lo sono; la settima lo
diventa al primo migrate che ricarica `messaggi_errore.csv`.

#### Passo 4 · P-1 — l'albero omogeneo, in **quattro** movimenti

Il pezzo grosso. Si costruisce dal basso.

✅ **APPLICATO il 2026-08-18 — nessuna regressione sui test.**

| File | Cosa |
| --- | --- |
| `20260818-08-create-fn-guard-albero-ba-emittente-mctit.yaml` | il check puro + i due guard `SECURITY DEFINER` |
| `20260818-09-create-trg-billing-account-guard-albero-emittente-mctit.yaml` | movimento 1 |
| `20260818-10-create-trg-efba-guard-albero-emittente-mctit.yaml` | movimenti 2, 3, 4 |
| `codici_errore.csv` · `messaggi_errore.csv` | `E_ALBERO_EMITTENTE_MISTO`, classe `DATO_ERRATO` |
| `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` | 8 asserzioni |

⚠️ **Tre scoperte che hanno cambiato la costruzione rispetto al piano:**

**1. Il 4a non serve — e non farlo è la scelta giusta.** Il piano prevedeva una
`SECURITY DEFINER` nuova che risolvesse l'emittente senza essere cieca. Ma
`anagrafiche.fn_get_emittente_fiscale_id` **legge solo `emittenti_fiscali_billing_account`,
che non ha RLS** (verificato: `relrowsecurity = false`): non è cieca già di suo.
Scriverne un'altra sarebbe stato **un secondo risolutore** — proprio ciò che
§11.2 vieta. Si usa quella, cioè **la stessa che usa `fn_build_fattura_key`**:
è l'unico modo perché *«albero omogeneo»* e *«la fattura esce da un solo
emittente»* siano la stessa affermazione.
La cecità resta invece sulla lettura di **`billing_account`** (padre e figli):
lì i due `fn_guard_*` **sono** `SECURITY DEFINER`.

**2. 🔴 Il guard del movimento 1 non può essere un `BEFORE` in fascia `a10`.**
L'emittente di un BA nasce dal mapping che crea `trg_billing_account_z90_link_ef_ins`,
che è **AFTER INSERT**. Un guard `BEFORE INSERT` risolverebbe l'emittente del
figlio sul **gestore globale** — il ripiego — invece che su quello che il figlio
avrà un istante dopo: **rifiuterebbe ogni albero creato da un operatore il cui
emittente non è il gestore globale**. È lo stesso motivo per cui la policy RLS
di INSERT è gate-only, ed è scritto nel suo changeSet.
→ trigger **`AFTER`**, fascia **`z95`** per ordinarsi dopo `z90_link_ef` (i
trigger di pari timing scattano in ordine alfabetico). La deroga alla
convenzione `_a10_` è motivata nel file.

**3. 🔴 Migrate fallito al primo tentativo — preCondition su un dato di `80_data`.**
Il `-08` verificava che `E_ALBERO_EMITTENTE_MISTO` fosse già in
`config.codici_errore`. Non può esserci: il catalogo dei codici si semina in
**`80_data`, che gira DOPO `20_code`**. Errore:
`SQL Precondition failed. Expected '1' got '0'`.
→ preCondition rimossa, con la ragione scritta nel file. La regola generale:
una preCondition può verificare **oggetti** della stessa fase o precedenti
(tabelle, funzioni), **mai un dato** — il dato serve quando l'errore *scatta*,
non quando la funzione nasce. Censite tutte e 7 le changeSet del cantiere: era
l'unica.

**4. Nessuna riga in `dbops.sec_functions_owner`.** Le `SECURITY DEFINER` che
richiedono `postgres` vanno registrate lì; queste no: `billing_account` e il
migrate sono **entrambi `titodb`**, quindi la funzione nasce di proprietà
dell'owner e supera la RLS senza `FORCE`.

✅ **Applicato e verde il 2026-08-18: 8/8, e la baseline `anagrafiche` non ha
regressioni** (27 rossi, tutti già noti). Anche il test di P-3 è rientrato:
era 6/7 in attesa della correzione del messaggio, ora è verde.

⚠️ **Il primo giro era 5/8, e i tre rossi erano tutti del TEST, non del codice.**
Vale la pena tenerli scritti, perché sono la trappola di §9 pagata da chi
l'aveva scritta:

| Rosso | Causa vera |
| --- | --- |
| «padre di un altro emittente» rispondeva `E_PARENT_NON_RAGGIUNGIBILE` | ⭐ **il codice aveva ragione**: spostato il padre sull'altro emittente, l'operatore non lo **vede** più, e il guard di coerenza (BEFORE) arriva prima. È §11.1 alla lettera |
| «cancellare il mapping» non sollevava niente | dopo lo spostamento, ogni `UPDATE` successivo su quel BA toccava **zero righe in silenzio** — sempre la RLS. L'albero non era mai stato ricostruito |
| il check «non cieco» tornava `true` | conseguenza del precedente: senza albero, la `DELETE` passava e il figlio ricadeva sul gestore globale |

**Il rimedio non è stato ammorbidire le asserzioni: è stato cambiare attore.**
Le asserzioni 2–7 girano ora nel contesto del **super admin**, che è l'unico a
vedere entrambi i rami — cioè l'unico che un albero misto lo può davvero
costruire. Provarlo da operatore misurava un'altra cosa, ed è precisamente
l'avvertenza che §9 dà a chi scrive i test.

> ⭐ **La conferma migliore del cantiere arriva da qui**: il difetto è
> irraggiungibile dal basso non perché sia improbabile, ma perché la RLS lo
> nasconde — e resta perfettamente raggiungibile da chi la RLS non ce l'ha.

**Verifica** — 8 asserzioni:

| # | Caso | Movimento |
| --- | --- | --- |
| 1 | albero omogeneo | — (nessuna regressione) |
| 2 ⭐ | padre di un altro emittente | 1 |
| 3 ⭐ | si sposta il **figlio** | 2 |
| 4 ⭐ | si sposta il **padre** — il verso *verso i figli*, quello che si dimentica | 2 |
| 5 ⭐ | si **cancella** il mapping: ricaduta sul gestore globale | 3 |
| 6 | **due alberi separati** dello stesso soggetto su emittenti diversi → passa | §3.1, la regola sbagliata che assomiglia a quella giusta |
| 7 | il check vede un BA **fuori perimetro** | §11.1: da `SECURITY INVOKER` questo passerebbe |

🕳️ **Non coperto, e dichiarato: il movimento 4** (spostamento del gestore
globale). Spostarlo richiede `DELETE`+`INSERT` della riga default nella stessa
transazione, perché il constraint differito `trgfn_emittenti_fiscali_default_guard`
pretende esattamente un default **al COMMIT** — e un file pgTAP chiude in
`ROLLBACK`, quindi quel COMMIT non arriva mai. Il ramo passa dalla **stessa**
funzione del test 5, ma verificarlo davvero richiede un test non transazionale.

---

**4a — il risolutore che non è cieco.** Una `SECURITY DEFINER` che risponde
«qual è l'emittente di questo BA» **sempre**, anche quando chi chiede non lo
vedrebbe (§11.1), delegando la catena a `anagrafiche.fn_get_emittente_fiscale_id`
per non diventare un secondo risolutore (§11.2).

- `AAAAMMGG-NN-create-fn-get-emittente-ba-privilegiato-mctit.yaml` → `20_code/anagrafiche`
- ⚠️ `SECURITY DEFINER` di proprietà di `postgres` ⇒ serve
  `dbops.fn_sync_functions_owner`;
- ⚠️ restituisce **SR id**, e il nome deve dirlo — la funzione da cui deriva ha
  già pagato quell'ambiguità con un `COMMENT` in maiuscolo.

**4b — il check puro.** `fn_check_albero_ba_omogeneo(p_ba_id, p_parent_id)`:
boolean, nessun raise, confronta i due valori risolti da 4a.

**4c — i due guard.**

| Trigger | Tabella | Eventi | Copre |
| --- | --- | --- | --- |
| `trg_billing_account_a10_guard_albero_emittente_ins_upd` | `anagrafiche.billing_account` | `INSERT`, `UPDATE OF parent_account_id` | movimento 1 |
| `trg_emittenti_fiscali_ba_a10_guard_albero_emittente_ins_upd_dlt` | `anagrafiche.emittenti_fiscali_billing_account` | `INSERT`, `UPDATE`, **`DELETE`** | movimenti 2, 3, 4 (§11.3) |

Il secondo verifica, per il BA toccato, **padre e figli**. Sul cambio di
`is_default` la verifica è d'insieme: sono i BA **senza** mapping specifico a
cambiare padrone, ed è l'unico caso a raggio N.

**4d — il codice errore.** Nuovo, registrato, con la sua `classe` — mai
`E_GENERICO`. Il messaggio deve nominare **i due emittenti**: è ciò che
trasforma il blocco in un'istruzione. E l'errore di §11.1 (`E_ID_FISCALI_DIVERSI`
sollevato quando i CF sono identici) **sparisce da solo**, perché il nuovo guard
risponde prima e per la ragione giusta.

⛔ **Nessuna eccezione per il pregresso, nessuna GUC di override** — decisione
già presa e non si riapre. Il guard afferma l'invariante e basta.

**Verifica** — `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql`:

| # | Caso | Atteso |
| --- | --- | --- |
| 1 | padre e figlio stesso emittente | ✅ passa |
| 2 | padre e figlio emittenti diversi, **contesto che vede entrambi** | ❌ `P0001`, codice nuovo |
| 3 | padre **senza mapping** (default globale) uguale all'emittente del figlio | ✅ passa — è il caso che un guard scritto sulle righe sbaglierebbe |
| 4 | padre senza mapping, default globale **diverso** | ❌ rifiuta |
| 5 | `UPDATE` del mapping che spacca un albero esistente | ❌ rifiuta |
| 6 | **`DELETE`** del mapping che fa ricadere il figlio su un default diverso | ❌ rifiuta |
| 7 | spostamento di `is_default` con BA non mappati appesi | ❌ rifiuta |

> ⚠️ **Il caso 2 è quello che si sbaglia.** Con un contesto operatore ristretto
> il guard **vecchio** solleva già, e il test passerebbe senza che il codice
> nuovo sia mai stato eseguito. Va scritto sul percorso che attraversa davvero il
> ramo, e deve asserire il **codice nuovo** — non un rosso qualunque.

**Fatto quando**: sette casi verdi, la baseline `anagrafiche` aggiornata con
motivazione per gli eventuali file di 0.4 che il guard rende rossi, e i rossi
nuovi **classificati** (fixture da adeguare ≠ regressione).

### Fase 3 — Rendere leggibile quello che resta

#### Passo 5 · P-2c — le etichette di perimetro

Indipendente da tutto: **si può anticipare in qualunque momento**, non blocca né
è bloccato. Etichetta sui contatori della `home` e sulle voci di ricerca; il
dettaglio del singolo documento resta fuori **con la ragione scritta**, che è la
metà che si dimentica.

⚠️ Con §11.6 ancora aperto, l'etichetta sulla ricerca direbbe «tutti gli
emittenti» a chi **non dovrebbe vederne nessuno**. Onesta rispetto a ciò che
succede, sbagliata rispetto a ciò che dovrebbe succedere: è un motivo in più per
mettere il passo 1 davanti.

#### Passo 6 · P-4 sulla pilota — **Competenza — gruppi fatturabili** · *decisione Q4*

È l'unità dell'emissione mirata, cioè il posto dove l'operatore **sceglie cosa
fatturare**: se c'è una schermata in cui l'ambiguità di emittente si paga
subito, è quella.

1. estendere `vendite.vw_dash_competenza_gruppi` con la **ragione sociale**
   dell'emittente (oggi c'è solo l'id — §11.4) → `20_code/vendite`.
   ⭐ La vista fa **già** la JOIN a `soggetti` per il cliente
   (`sog.ragione_sociale_completa AS cliente_fatturazione_display`): questa è la
   stessa JOIN una seconda volta, nella forma delle sei viste documento
   (`s_ef.ragione_sociale_completa AS emittente_ragione_sociale`);
2. **append** a `lista_colonna.csv`, copiando la riga delle sei liste documento
   (`campo_sorgente = emittente_ragione_sociale`, `tipo_colonna = informazione`);
3. ⚠️ **richiesta al BE** (BE-2): `vista_sql` è NULL, quindi le righe le compone
   il repository di dominio — che oggi elenca le colonne **esplicitamente**
   (`vendite_repository`, `SELECT g.gruppo_key, …`). Senza aggiungerla lì, la
   colonna si spunta e **resta vuota**: cioè la garanzia che il flag pretende,
   non mantenuta.

✅ **APPLICATO il 2026-08-18 — nessuna regressione sui test.**

| File | Cosa |
| --- | --- |
| `20260818-15-update-vw-dash-competenza-gruppi-emittente-ragione-sociale` | `20_code/vendite` — la vista espone la ragione sociale |
| `lista_colonna.csv` | **append** di una riga (id 478, lista 42, `ordine_default` 100) |
| `db/pgtap/ui/test-lista-competenza-gruppi-colonna-emittente-v1.sql` | 5 asserzioni |

**Applicato e collaudato**: i 5 test del file nuovo sono verdi, baseline senza
regressioni. ⚠️ **I dati restano non verificati**, ed è una lacuna della misura
e non del passo:
`vw_dash_competenza_gruppi` in questa istanza è **vuota** (nessuna attività
fatturabile aperta), quindi un `count(emittente_ragione_sociale)` sarebbe
`0 = 0` — verde per sottrazione. Il test asserisce la **struttura**, che è ciò
che il passo introduce.

⚠️ **Due vincoli di `CREATE OR REPLACE VIEW` rispettati, entrambi silenziosi se
sbagliati:** `security_invoker=on` va **ri-specificata** o PostgreSQL la azzera
(e questa vista ci appoggia lo scope emittente), e si possono solo **appendere**
colonne in coda — la nuova è per forza ultima.

⭐ **Il test che conta è il 4: coerenza catalogo → vista.** Il «prezzo del
biglietto» di P-2b dice che una lista può dichiararsi multi-emittente solo se
espone l'emittente nella riga. Una riga di catalogo che punta a un campo
**inesistente** è una colonna che si spunta e resta vuota: *sembra* la garanzia,
e non lo è. Il test verifica che il `campo_sorgente` dichiarato esista davvero
nella vista. Sta in coppia col test 3 (esistenza): da solo sarebbe verde anche
senza la riga.

⚠️ **Il test 5 è il registro di debito**: asserisce che **una sola** delle sei
liste del perimetro ha la colonna. Se quel numero sale senza che nessuno abbia
fatto il lavoro, qualcuno ha attaccato l'adesivo «collaudato» senza collaudare.

**Fatto quando**: la colonna si spunta e **mostra un nome** — e la seconda metà
è **BE-2**, non il database. Il DB garantisce che il campo esista; che il
repository lo selezioni no.

##### L'ordine delle altre cinque · *deciso con Q4*

| Giro | Schermate | Perché insieme |
| --- | --- | --- |
| **2°** | Situazione aperta — documenti **+** Backlog — documenti fermi | due proiezioni della **stessa vista a monte** (`vw_dash_fatturazione_documenti`): una JOIN sola, due schermate |
| **3°** | Competenza — errori vivi · Competenza — drill-down commesse | viste proprie, stesso pattern della pilota |
| **ultima** | Lotti di fatturazione | ⚠️ **niente lavoro DB**: le righe nascono da SQL nel backend (`vendite_repository.list_lotti`, su `vendite.fatturazione_lotti`, che ha già `emittente_soggetto_ruolo_id NOT NULL`). Va in fondo perché è **tutta** una richiesta al BE |

#### Passo 7 · P-2b — il flag, e il cancello che lo protegge

**Solo su una lista che ha passato il passo 6. Mai prima.**

| File (indicativo) | Cartella | Nota |
| --- | --- | --- |
| `…-alter-ui-lista-definizione-add-multi-emittente-mctit.yaml` | `00_schema/ui` | `boolean NOT NULL DEFAULT false` |
| `…-create-trgfn-lista-definizione-guard-multi-emittente-mctit.yaml` | `20_code/ui` | **Strato 1, nella forma nuova** (§11.5) |
| `…-update-fn-resolve-lista-config-multi-emittente-mctit.yaml` | `20_code/ui` | additivo sull'envelope |
| `…-create-vw-liste-multi-emittente-non-certificate-mctit.yaml` | `20_code/dbops` | il controllo automatico della decisione 3 |
| — | `80_data` | colonna nuova nel CSV **e** nel `columns:` del loader, **backfill prima** |

⚠️ **Ordine Liquibase**: l'`ALTER TABLE` sta in `00_schema`, la funzione che legge
la colonna in `20_code`, e `changelog-autogen.yaml` **mescola le due cartelle
ordinando per numero**. Chi legge deve avere numero **più alto** di chi crea, o
l'apply su un DB ricostruito fallisce e su dev no.

⚠️ **`scripts/gen_seed_lista.py`**: `CAMPI_DEF` (riga 297) va esteso, o il
generatore riscriverà il CSV **senza** la colonna nuova. È un rigeneratore, non
un lettore: la dimenticanza non dà errore, toglie il campo.

🚫 **`multi_emittente` NON entra in `_CREATE_KEYS` né in `_UPDATE_KEYS`**
(`lista_definizione_admin_service.py`), e il perché va scritto **accanto alla
whitelist** — è l'unica eccezione a una convenzione dichiarata sulla riga 192, e
un'eccezione senza motivo scritto viene tolta dal primo che passa convinto di
star sistemando una svista. Strato 2: test in CI su quelle due `frozenset`.

✅ **SCRITTO il 2026-08-18 — non applicato.** ⚠️ **Metà passo**: c'è tutto il
**presidio**, manca la **lettura** (vedi in fondo).

| File | Cosa |
| --- | --- |
| `20260818-16-alter-ui-lista-definizione-add-multi-emittente` | `00_schema/ui` — la colonna, `NOT NULL DEFAULT false` |
| `20260818-17-create-trgfn-lista-definizione-guard-multi-emittente` | `20_code/ui` — **lo strato 1, nella forma nuova** |
| `20260818-18-create-vw-liste-multi-emittente-non-certificate` | `20_code/dbops` — il controllo automatico |
| `lista_definizione.csv` · loader `20260507-06` · `gen_seed_lista.py` | seed: colonna su tutte e 44 le righe (a `f`), `columns:` del loader, `CAMPI_DEF` |
| `codici_errore.csv` · `messaggi_errore.csv` | `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE`, classe `NON_PERMESSO` |
| `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql` | 6 asserzioni |

⭐ **Il trigger non nomina il ruolo: legge il proprietario della tabella** da
`pg_class` e usa `pg_has_role(current_user, owner, 'USAGE')`. Un nome di ruolo
scritto a mano sarebbe giusto su questa istanza e falso sulla prossima. Il
migrate passa perché *è* il proprietario — non perché qualcuno accende un
interruttore, e infatti non c'è nessun interruttore da accendere.

⚠️ **L'ordine Liquibase è rispettato e verificato**: `ALTER` a **-16**, i due
lettori a **-17** e **-18**. `changelog-autogen.yaml` mescola `00_schema` e
`20_code` ordinando per numero: al contrario, l'apply su un database ricostruito
da zero fallirebbe e su dev no.

⚠️ **Il `CAMPI_DEF` del generatore è stato esteso**, con il perché sulla riga
sopra: senza, `gen_seed_lista.py` riscriverebbe il CSV **senza** la colonna,
spegnendo il flag su tutte le liste in silenzio.

**Il test** — 6 asserzioni, di cui la **0 è la più importante del file**:
dichiara che il test gira **come applicazione**, non come proprietario. Girando
come owner le asserzioni 3 e 4 lascerebbero passare la scrittura e il file
sarebbe verde **verificando il contrario di quel che dice**. Nel dry-run la 0
passa già; le altre attendono l'apply.

| # | Cosa |
| --- | --- |
| 0 | precondizione: si gira come applicazione |
| 1–2 | la colonna esiste, il default è `false` |
| 3 ⭐ | l'applicazione **non** può accendere il flag |
| 4 ⭐ | né crearne una già accesa |
| 5 | il registro di debito parte pieno: **zero** liste certificate |
| 6 | la vista di controllo è a zero righe |

#### ⚠️ Quello che manca al passo 7: la lettura

`ui.fn_resolve_lista_config` deve restituire il flag nell'envelope (chiave
additiva, non rompe i consumatori). **Non è stato fatto in questo giro**, e la
ragione è concreta: è una funzione di **oltre 400 righe** che un altro lavoro ha
appena modificato (`20260818-04`, il contatore delle colonne nuove). Ricopiarla
in coda a un giro lungo è il modo in cui si regredisce il lavoro di qualcun
altro senza accorgersene — e il progetto ha già pagato per quello.

Va fatta come pezzo a sé, con la verifica che ha funzionato al passo 1: **corpo
dalla doc auto-generata, poi diff del risultato contro la definizione viva** per
provare che l'unica differenza è la chiave nuova.

**Fatto quando**: il flag esiste, è `false` su tutte e 44 le liste, il trigger
rifiuta la scrittura dal ruolo applicativo, la vista di controllo restituisce
**zero righe** — e `fn_resolve_lista_config` lo espone. I primi quattro sono
scritti; il quinto no.

#### Passo 8 · Le liste restanti — una alla volta, e non tutte

Ogni lista rifà i passi 6 e 7. Il flag resta `false` sulle altre, **ed è giusto
così**: è un registro di debito che cala. Il giorno in cui lo si volesse
accendere in blocco vorrebbe dire che ha smesso di significare qualcosa.

### Quadro d'insieme

| Passo | Perimetro | Prerequisito | Reversibile |
| --- | --- | --- | --- |
| 0.1–0.5 | misure | — | n/a |
| 1 — scope interno alla ricerca | `20_code/script` | — (non blocca, e non è bloccato) | sì |
| 2 — P-2a | `20_code/script`, `config`, `dbops` | ⛔ 0.1 | sì (`CREATE OR REPLACE` inverso) |
| 3 — P-3 | `20_code/anagrafiche` | 0.5 | sì |
| 4 — P-1 | `20_code/anagrafiche` | ⛔ 0.4, 0.5; **dopo** 3 | sì (drop dei due trigger) |
| 5 — P-2c | FE/BE | — | sì |
| 6 — P-4 pilota | `20_code/vendite`, `80_data` | — | sì |
| 7 — P-2b | `00_schema/ui`, `20_code/ui`, `80_data`, BE | ⛔ 6 sulla stessa lista | ⚠️ l'`ALTER TABLE` **no** |
| 8 — le altre | come 6+7 | 7 | sì |

⚠️ **L'unico passo non reversibile a costo zero è l'`ALTER TABLE` del passo 7**, e
sta apposta in fondo: si aggiunge una colonna solo quando c'è già una lista che
può metterla a `true`.

⚠️ **Il passo 2 è quello che si è tentati di rimandare**, perché «tanto oggi
funziona». Funziona nel senso che nessuno se ne lamenta: un operatore configurato
a metà vede tutti gli emittenti e non lo sa né lui né nessun altro.

---

## 13. Richieste al backend

> Perimetro DB: qui si scrive la richiesta, il codice lo scrive il BE.

### BE-1 🔵 `search_repository`: la lista vuota non è «nessun filtro» · *declassata*

> ⚠️ **Era 🟠 e bloccava P-2a. Dal 2026-08-17 non blocca più niente** (decisione
> Q2/C): il passo 1 fa risolvere lo scope alla funzione SQL, quindi quella riga
> Python **non decide più** cosa si vede. Resta qui perché continua a scrivere
> una cosa falsa, e perché la **regola** che ne discende vale oltre questo punto.
> Da fare quando comodo, o mai — ma la regola in fondo va letta comunque.

**Dove**: `backend/apps/core/db/search_repository.py`, righe **42** e **98**.

```python
# oggi — [] è falsy e diventa None, cioè "nessuna restrizione"
pg_emittente_ids = emittente_ids if emittente_ids else None
```

**Cosa serve**: distinguere i **tre** stati della convenzione, non due.

| Valore | Significato | Oggi | Deve |
| --- | --- | --- | --- |
| `None` | nessuna restrizione | nessun filtro ✅ | invariato |
| `[]` | **nessun accesso** | ⚠️ nessun filtro | **zero risultati** |
| lista | whitelist | filtro ✅ | invariato |

Il passaggio `[] → None` va rimosso (`if emittente_ids is not None`). Poiché
`fn_search_soggetti_universale` interpreta `NULL` come «tutto», l'array vuoto
deve **arrivare come array vuoto** — e se la funzione SQL su `'{}'` non
restituisce zero righe, la seconda metà è una richiesta al team DB e va aperta
qui.

~~**Perché prima e non dopo**: P-2a rende `[]` lo stato normale dell'operatore non
configurato. Applicata per prima, una correzione pensata per **chiudere** si
tradurrebbe in un **allargamento** su quella superficie.~~
→ **Ritirato**: l'argomento poggiava sulla «finestra», e su un ambiente senza
produzione la finestra non è un costo (obiezione di Tid, Q2). Il passo 1 chiude
comunque quella superficie, dal lato database.

**Come si verifica**: un test con `emittenti = []` che asserisce **zero
risultati**, non «nessun errore».

⚠️ La regola generale, che vale per il prossimo consumatore di questa convenzione:
**non si legge mai con un test di verità.** `if ids:` e `ids or []` collassano i
due estremi opposti sullo stesso valore, e lo fanno dalla parte che apre.

### BE-2 🔴 Competenza — gruppi fatturabili: la ragione sociale dell'emittente nella riga · *sbloccata, e ora è la metà che manca*

> ⚠️ **Non è più «quando»: è adesso.** Il passo 6 è applicato dal 2026-08-18 —
> `vendite.vw_dash_competenza_gruppi` **espone** `emittente_ragione_sociale` e la
> riga di catalogo esiste (`lista_colonna` id 478). Da qui in poi la colonna è
> spuntabile e **esce vuota** finché il backend non la seleziona: il DB ha fatto
> la sua metà, e la metà che resta è l'unica visibile all'operatore.

Il repository deve **portarla nella riga** con quella chiave. Non è automatico:
`vendite_repository` elenca le colonne **esplicitamente** (`SELECT g.gruppo_key,
g.tipo_gruppo, …`), quindi una colonna nuova nella vista **non arriva a video da
sola** — e la lista ha `vista_sql = NULL`, quindi il catalogo non può pescarla.

Serve: una riga nel `SELECT`, una nel mapping della `DashCompetenzaGruppoRow`.
Senza, la colonna a catalogo si spunta e resta vuota — che è peggio di non
averla, perché *sembra* la garanzia che il flag pretende.

### BE-4 🔵 Lotti di fatturazione: l'emittente nella riga · *ultima del giro P-4*

Fuori dal perimetro DB **per intero**: `vendite_repository.list_lotti` costruisce
la lista con SQL diretto su `vendite.fatturazione_lotti`, senza passare da
nessuna vista. Il dato c'è già sulla tabella (`emittente_soggetto_ruolo_id`,
`NOT NULL`): serve la JOIN a `soggetti_ruoli`/`soggetti`, la colonna e il
mapping. È il motivo per cui questa schermata è **l'ultima** del giro (Q4).

### BE-3 🔵 `multi_emittente`: cancello e non raccomandazione

Dipende dal passo 7. Tre cose, in ordine di forza:

1. **`multi_emittente` NON entra** in `_CREATE_KEYS` né `_UPDATE_KEYS` di
   `apps/ui/services/lista_definizione_admin_service.py`;
2. un test in CI che lo **asserisce** — tre righe, gira a ogni PR, ed è lo strato
   che serve il giorno del refactor, quando qualcuno riallinea le whitelist «per
   coerenza»;
3. il **perché scritto accanto alla whitelist**, non solo nel brief: la riga 192
   dichiara *«Tutti i campi sono mutabili (nessun immutabile per design)»*, quindi
   questa è l'unica eccezione a una convenzione esplicita.

Il rifiuto lato DB (§11.5) diventerà un errore con **codice registrato**, da
mappare in `error_policies.py` come tutti gli altri.

---

## 14. Riferimenti

> ℹ️ Questa sezione era numerata **§10**. È stata spostata in fondo il 2026-08-17
> per far posto ad analisi (§11), piano (§12) e richieste al BE (§13): un elenco
> di link non deve stare in mezzo a cose che si eseguono.

### Verificati nella revisione del 2026-08-17 (§11)

| Cosa | Dove | Serve a |
| --- | --- | --- |
| **Il giro dei grant che annulla lo Strato 1** | `db/changelog/migrations_v2/90_end/ci_apply/20260205-41-apply-runtime-grants-ci-mctit.yaml` | §11.5 |
| RLS attiva su `billing_account` (`ENABLE`, no `FORCE`) | `00_schema/anagrafiche/20260601-40-enable-rls-ondata2-billing-account-mctit.yaml` | §11.1 |
| Risoluzione emittente *specifico ∨ default* | `docs/it/dbzero/script/funzioni/fn_check_ba_visible_for_emittenti.md` · `anagrafiche/funzioni/fn_get_emittente_fiscale_id.md` | §11.2 |
| `billing_account_id` nullable + default globale | `docs/it/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account.md` | §11.3 |
| Le colonne emittente già a catalogo (6 liste) | `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv` | §11.4 |
| Le viste del perimetro: id sì, ragione sociale no | `docs/it/dbzero/vendite/views/vw_dash_*.md` | §11.4 |
| **Il fail-open sullo scope vuoto** | `backend/apps/core/db/search_repository.py` righe 42, 98 | §11.6 · §13 |
| Il filtro che applica solo su `IS NOT NULL` | `docs/it/dbzero/script/funzioni/fn_search_soggetti_universale.md` | §11.6 |
| Whitelist CRUD + commento «tutti mutabili» | `backend/apps/ui/services/lista_definizione_admin_service.py` righe 51–65, 192 | §11.8 · §13 |
| `CAMPI_DEF` del generatore di seed | `scripts/gen_seed_lista.py` riga 297 | passo 7 |
| Loader `loadUpdateData` del catalogo liste | `80_data/changelog/20260507-06-seed-ui-lista-definizione-mctit.yaml` | passo 7 |

### Già citati nella prima stesura

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
| Cantiere che ha fatto emergere i buchi | [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md) |
| Architettura multi-face auth | `docs/it/guide/architettura-multi-face-auth.md` |
