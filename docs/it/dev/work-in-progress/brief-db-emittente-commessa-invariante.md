# Brief DB — l'emittente della commessa è un invariante, e oggi non lo presidia nessuno

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Tid, 2026-08-26, chiudendo la D-6 di
> [brief-db-registro-e-data-prevista-in-competenza.md](../work-done/brief-db-registro-e-data-prevista-in-competenza.md).
> Avevo segnalato come debito minore che `vendite.commesse.emittente_soggetto_ruolo_id`
> è nullable e non legata al billing account. Risposta di Tid: *«allora hai
> scoperto un bug!! la commessa dovrebbe derivare sempre l'emittente dalla
> cascata delle sorgenti, una commessa non può aggregare diversi emittenti
> insieme e di conseguenza non può avere emittente null»*.
>
> ⭐ **Guardandolo davvero, il ramo peggiore non è quello che avevo segnalato.**
>
> ✅ **Decisioni prese** (Tid, 2026-08-26): **D-1** — nessuna «cascata delle
> sorgenti», l'emittente si prende **dal billing account**, sempre derivato e mai
> passato da fuori. **H1** — la colonna **non può essere NULL**, si corregge.
>
> ⛔ **Separato**: la domanda «un BA può cambiare emittente?» (era H3/D-3) è
> **uscita da qui** ed è diventata
> [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md)
> — su richiesta di Tid, perché è una riflessione di dominio con implicazioni
> fiscali e mescolarla farebbe rimandare una correzione che invece è chiara.
>
> ✅ **Stato (2026-08-26, secondo passaggio): il piano di sviluppo è scritto —
> §7.** Le due decisioni residue (**D-2** l'override, **D-4** le sorgenti
> eterogenee) sono **chiuse in fase di piano**, con la motivazione presa sul
> modello e non sui dati: §6. Non restano domande aperte.
>
> ✅ **CANTIERE DB CHIUSO il 2026-08-26 — L1…L9, tutti eseguiti e APPLICATI.**
> ChangeSet `20260826-39` … `-45` e `-50`, `-51`, `-52`; quattro codici errore;
> tre pgTAP nuovi; 8 pagine `manual/` e 4 guide. Registro, scarti dal piano e
> **due correzioni in corsa** nel §8.
>
> ⚠️ **Migrazione applicata da Tid**, comando per comando
> ([[feedback_mai_applicare_migrazioni_db]]): «puoi iniziare lo sviluppo»
> autorizzava il lavoro, non l'apply — quello l'ha autorizzato lui.
>
> 🔴 **Resta la sola consegna BE-1** (§7.5): il backend deve smettere di passare
> `p_emittente_soggetto_ruolo_id`, che dal `-52` non esiste più. Finché non lo
> fa, il push si ferma con «funzione inesistente» — rumoroso per scelta.

---

## 1. Il difetto in una frase

`vendite.commesse.emittente_soggetto_ruolo_id` **non è un attributo della
commessa: è la sua chiave di perimetro**. Ci si appoggiano la row security della
tabella, il filtro di scope delle viste del cruscotto e il giornale degli eventi.
Ma la colonna è **nullable**, **non vincolata al billing account** e **congelata
alla nascita** — tre proprietà che per un attributo qualsiasi sarebbero
irrilevanti, e per una chiave di perimetro sono un difetto.

⚠️ **Questo brief NON dice che oggi ci siano righe sbagliate**, e non è la
domanda giusta: la domanda è *«il modello lo ammette?»*
(`.codex/AGENTS.md` § «Regola zero — le misure non disegnano il progetto»). Tutti gli argomenti qui
sotto sono letti sulla **struttura** — colonne, vincoli, policy, trigger, corpi
di funzione.

---

## 2. ⛔ H1 — con l'emittente a NULL la commessa **sparisce**, e non è un modo di dire

`vendite.commesse` ha la row security accesa, con **una** policy, e vale per
**tutti** i comandi (`polcmd = '*'`, quindi anche `UPDATE` e `DELETE`):

```sql
rls_commesse_ef_whitelist USING (
    current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
    AND script.fn_scope_ef_whitelist_via_sr(
            current_setting('app.current_user_id', true)::integer,
            emittente_soggetto_ruolo_id)
)
```

E il gemello che risolve dalla commessa lo dichiara nel proprio corpo, testuale:

> *«Commessa inesistente / emittente NULL → SR NULL → false (fail-closed se
> whitelist valorizzata)»*

⇒ Per un operatore con perimetro ristretto, una commessa con emittente NULL
**non esiste**: non la legge, non la modifica, non la cancella. E la stessa
condizione è ricopiata nel `WHERE` di `vw_dash_competenza_attivita`
(`co.emittente_soggetto_ruolo_id = ANY(escope.sr_ids)`), quindi sparisce anche
dal cruscotto competenza e da tutto ciò che ci si appoggia.

⭐ **La forma del danno è la peggiore possibile**: non un errore, non una riga
sbagliata a video. **Lavoro che esiste nel database, non compare da nessuna
parte e non viene mai fatturato** — e nessuno se ne accorge, perché una lista che
non mostra una riga ha esattamente lo stesso aspetto di una lista in cui quella
riga non c'è.

⚠️ È la classe di difetto già a registro nel progetto: *uno zero può essere
fail-closed, non un dato*. Qui però non è un conteggio: è la riga intera.

⭐ **E non è un caso isolato: è una famiglia.**
[brief-db-lavoro-che-non-torna-indietro.md](../work-done/brief-db-lavoro-che-non-torna-indietro.md)
descrive lo stesso tipo di danno per un'altra causa — un'attività che resta
marcata come fatturata dopo che la sua fattura è stata eliminata, e che nessuno
rimette mai in coda. ⚠️ Le due cose **non hanno oggetti in comune** e non vanno
unite; ma chi un giorno cercherà «perché questo lavoro non è stato fatturato»
deve trovarle **entrambe**, perché il sintomo è lo stesso e la causa no.

---

## 3. I quattro buchi, e cosa li lascia aperti

| | Buco | Cosa lo lascerebbe chiuso, e non c'è |
| --- | --- | --- |
| **H1** | La colonna è **nullable** | un `NOT NULL`. Oggi il valore lo garantisce solo il fatto che `anagrafiche.fn_get_emittente_fiscale_id` **solleva** invece di tornare NULL — cioè una proprietà di una funzione, non del dato |
| **H2** | **Nessun vincolo la lega al billing account** | un guard di coerenza. `fn_get_or_create_commessa` accetta `p_emittente_soggetto_ruolo_id` e fa `COALESCE(override, risolto dal BA)`: l'override passa **qualunque** `soggetto_ruolo_id` esista, e la sola FK non guarda il BA |
| **H4** | Le **sorgenti** si collegano senza controllo di omogeneità | un guard su `fn_link_commessa_sorgente`, che dell'emittente non sa nulla. È il «non può aggregare diversi emittenti» detto da Tid, sull'asse dei documenti invece che su quello dei BA |

> ⛔ **H3 è uscito da questo brief.** Era «la colonna è una fotografia scattata
> alla nascita, e se il mapping del BA cambia diventa stantìa». Dietro c'è una
> domanda di dominio — *un billing account può cambiare emittente?* — che ha
> implicazioni fiscali e va **pensata**, non programmata:
> [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md).
> ⭐ **E questo cantiere non la aspetta**: `NOT NULL` più il vincolo al billing
> account sono giusti qualunque risposta si dia là.

⭐ **Un indizio che il difetto è già stato sfiorato**: dentro
`fn_get_or_create_commessa` la ricerca della commessa esistente confronta
`COALESCE(c.emittente_soggetto_ruolo_id, -1) = COALESCE(v_emittente, -1)`. Quel
`COALESCE` difende da un NULL che **non dovrebbe potere esistere**. Quando il
codice si protegge da uno stato impossibile, di solito è perché impossibile non è.

---

## 4. ✅ Cosa invece è presidiato bene, e non va ridiscusso

L'**albero dei billing account** è omogeneo per emittente, e per davvero:
`anagrafiche.fn_guard_albero_ba_emittente` controlla verso il padre **e verso
tutti i figli**, è agganciata da due trigger `z95` (uno sullo spostamento del BA,
uno sul cambio di mapping), gira `SECURITY DEFINER` perché altrimenti la row
security nasconderebbe proprio il caso da bloccare, è fail-closed sul NULL e non
ha nessuna GUC di override — *«un invariante con l'interruttore non è un
invariante»*.

⇒ **Padre e figlio non possono avere due emittenti diversi.** È il modello di
presidio che manca alla commessa, e la buona notizia è che esiste già in casa: si
tratta di estenderlo di un anello, non di inventarlo.

### 4.1 ⭐ E l'anello che manca ha già **sei fratelli**, con lo stesso nome

Verificato sulla doc auto-gen il 2026-08-26. Il presidio «l'emittente del
documento concorda con quello del suo billing account» **esiste già**, ed è una
famiglia con una convenzione di nome:

| Tabella | Riempie il default | Verifica contro il BA | Codice |
| --- | --- | --- | --- |
| `vendite.ordini` | `trgfn_ordini_default_emittente` | `trgfn_ordini_guard_emittente_ba` | `E_ORDINE_EMITTENTE_BA_INCOERENTE` |
| `vendite.preventivi` | `trgfn_preventivi_default_emittente` | `trgfn_preventivi_guard_emittente_ba` | `E_PREV_…` |
| `vendite.contratti` | `trgfn_contratti_default_emittente` | `trgfn_contratti_guard_emittente_ba` | `E_CONTRATTO_…` |
| `vendite.ddt` | `trgfn_ddt_default_emittente` | `trgfn_ddt_guard_emittente_ba` | `E_DDT_…` |
| `vendite.offerte_commerciali` | — | `trgfn_offerte_commerciali_guard_emittente_ba` | `E_OFFERTA_…` |
| `vendite.resi` | — | `trgfn_resi_guard_emittente_ba` | — |
| **`vendite.commesse`** | ⛔ **niente** | ⛔ **niente** | ⛔ **niente** |

⇒ La commessa è **l'unica tabella del ciclo che porta un emittente e non ha né
il riempitore né il guard**. Non è un presidio da inventare: è una riga vuota in
una tabella che ha già sei righe piene.

⚠️ **Con una differenza, ed è quella che D-1 ha deciso.** Nei sei fratelli il
`default_emittente` lo prende dall'**operatore**
(`script.fn_resolve_emittente_for_user` sulla GUC `app.current_user_id`): sono
documenti che una persona crea in un form. La commessa **non la crea nessuno a
mano** — nasce dal push — quindi il suo riempitore prende l'emittente **dal
billing account**, che è esattamente D-1. Il guard, invece, è identico ai sei:
confronta con l'emittente risolto dal BA.

---

## 5. La forma della soluzione — ✅ **confermata, ed è diventata il §7**

> ⚠️ *Era «proposta, non decisione». Il 2026-08-26 le quattro voci qui sotto sono
> state confermate una per una e trasformate in nove lotti: **§7**. Il testo resta
> perché dice la forma in una pagina; il come sta là.*

1. **`NOT NULL` sulla colonna.** È l'unica delle quattro che non richiede
   discussione: una chiave di perimetro nullable è un buco per definizione.
2. **Una sede unica che risolve l'emittente della commessa**, chiamata sia da
   `fn_get_or_create_commessa` sia dal guard — la disciplina «si condivide la
   funzione, non una copia della sua logica», la stessa del cantiere gemello.
3. **Un guard di coerenza** sul modello di `fn_guard_albero_ba_emittente`: la
   commessa deve concordare con il proprio billing account (H2) e con le proprie
   sorgenti (H4).
4. ⛔ **Niente di più.** Il caso «e se il BA cambiasse emittente?» **non si
   progetta qui**: è l'altro brief, e questo cantiere è corretto comunque vada a
   finire là.

---

## 6. ~~❓ Le decisioni aperte~~ → ✅ **tutte chiuse (2026-08-26)**

### ✅ D-1 CHIUSA — non esiste nessuna cascata: la sede è il billing account

> ✅ **Tid, 2026-08-26**: *«hai ragione a correggermi, non esiste una cascata
> delle sorgenti; giusto che l'emittente venga preso dal billing account»*.

⇒ La frase d'origine («derivare dalla cascata delle sorgenti») voleva dire
**sempre derivato, mai passato da fuori**. La catena resta quella che c'è già —
`anagrafiche.fn_get_emittente_fiscale_id`: mapping specifico del BA, poi default
globale — e non se ne inventa una seconda.

⭐ Con questa risposta **D-2 si inclina da sola**: se l'emittente è sempre
derivato, un parametro che permette di passarlo dall'esterno non ha più una
ragione d'essere.

### ✅ D-2 CHIUSA — si toglie, **e nel frattempo lo controlla il trigger**

> ~~l'override `p_emittente_soggetto_ruolo_id` si toglie o si controlla?~~
> *Domanda originale: se l'emittente è sempre derivato, quel parametro non ha
> ragione di esistere e va tolto — ma è nella firma di una funzione che il
> backend chiama, quindi è una consegna BE, non solo DB.*

✅ **Chiusa il 2026-08-26 in fase di piano: le due risposte non sono
alternative, sono due lotti in fila.** Ed è la sequenza che le rende entrambe
possibili senza mai lasciare un buco aperto:

1. **Prima il controllo, e non nella funzione: nel trigger** (L2). Il punto è
   che la funzione è **un** solo scrittore. Un guard scritto dentro
   `fn_get_or_create_commessa` protegge da chi passa per la funzione, e non da
   una `INSERT` diretta — che nel repository esiste eccome: **22 file pgTAP**
   scrivono in `vendite.commesse` senza passare di lì (misura strutturale, non
   di popolazione: sono file, non righe). È la regola già a registro nel
   progetto — *il vincolo non sa chi lo scrive*
   ([[reference_check_tabella_e_guard_funzione_dissentono]]).
2. **Poi il parametro sparisce** (L5). Con il trigger in servizio, l'override
   può solo essere **ridondante** (uguale al derivato → passa) oppure
   **sbagliato** (diverso → l'errore lo solleva il trigger). Un parametro il cui
   unico valore ammesso è quello che la funzione sa calcolare da sé non è
   un'opzione: è una trappola per il prossimo chiamante.

⭐ **E il costo lato BE è due righe**, verificato il 2026-08-26 leggendo il
codice: l'unico punto vivo è
`backend/apps/vendite/services/commesse_source_handlers.py`, che passa
`emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id` — e `row` viene
dalle `fn_list_*_da_pushare`, che quel valore lo calcolano **già** con
`anagrafiche.fn_get_emittente_fiscale_id(billing_account_id)`. Cioè: il backend
oggi restituisce al database esattamente il valore che il database gli aveva
appena dato. ⇒ Togliere il parametro **non cambia nessun comportamento**, toglie
un giro.

⚠️ Il taglio è però **secco**: la chiamata usa parametri nominati
(`p_emittente_soggetto_ruolo_id => %s`), quindi al `DROP` della vecchia firma il
push si ferma con «funzione inesistente» finché il BE non è aggiornato. È il
motivo per cui L5 è **l'ultimo lotto e ha un cancello esplicito (BE-1)**, non
perché sia difficile.

### ~~D-3 — cambiare l'emittente di un BA che ha già commesse~~ → trasferita

⛔ **Non è più una domanda di questo cantiere.** È diventata un brief suo, perché
la risposta non è tecnica: *«non può scomparire un cliente che ha già delle
fatture con un emittente perché è andato ad un altro»* (Tid).
▶ [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md).

### ✅ D-4 CHIUSA — si bloccano, sull'**emittente** e non sul billing account

> ~~le sorgenti eterogenee (H4): si bloccano o si tollerano?~~

✅ **Chiusa il 2026-08-26 in fase di piano: si bloccano** (L6). È la frase di
Tid presa alla lettera — *«una commessa non può aggregare diversi emittenti
insieme»* — e tollerarle vorrebbe dire che la colonna di perimetro della
commessa descrive **una parte** del lavoro che ci sta sotto: che è la stessa
forma di danno del §2, spostata di un anello.

⭐ **Ma il criterio è l'emittente, non il billing account** — ed è una scelta,
non un dettaglio. Sul modello di oggi le due cose coinciderebbero: la commessa
ha `billing_account_id` `NOT NULL`, ed è una delle dimensioni della sua chiave di
raggruppamento, quindi **una commessa è di un BA solo** e ogni sua sorgente
arriva dallo stesso BA per costruzione del push. Bloccare sull'identità del BA
sarebbe più semplice e più stretto.

⛔ **E sarebbe più stretto di quello che si è deciso.** L'albero dei billing
account esiste apposta perché più BA possano stare sotto lo stesso emittente
(§4), e un guard sull'identità del BA vieterebbe per sempre che un documento di
un figlio contribuisca alla commessa del padre — una decisione di dominio che
**nessuno ha preso** e che questo cantiere non ha titolo per prendere di
straforo. Il guard dice quello che l'invariante dice: *stesso emittente*. Il
resto resta aperto, e va bene così.

⚠️ **Il costo va misurato prima, ed è la raccomandazione già scritta qui**: il
guard sta sul percorso da cui passa la costruzione delle commesse in tutti i
test ([[feedback_guard_breaks_existing_tests]]). Come si misura senza inseguire
rossi altrui — la baseline — è nel §7.8.

---

## 7. Piano di sviluppo

> ⛔ **Nessun file scritto, nessuna migrazione applicata**
> ([[feedback_mai_applicare_migrazioni_db]]): questo è il piano, l'esecuzione
> parte su «procedi», lotto per lotto.
>
> **Regole che valgono per tutti i lotti**, e non si ripetono dentro:
>
> * numerazione `NN` **globale per data** fra tutte le cartelle
>   ([[feedback_liquibase_numerazione_globale_per_data]]) — il 2026-08-26 è
>   arrivata a `26`, quindi si riparte dal primo libero **del giorno in cui si
>   scrive**, riletto e non dedotto;
> * un `changeSet` per file, `logicalFilePath` sempre, `runOnChange: false`
>   ([[feedback_runonchange_false_in_finale]]; in `00_schema` e `20_code` è un
>   divieto presidiato in CI), `validCheckSums: ANY` **al plurale**;
> * il corpo di una funzione esistente si copia dalla **doc auto-gen**, mai da
>   uno YAML ([[feedback_docs_first]]) — ⚠️ ricordando che l'auto-gen non chiude
>   il `$function$` con il `;` ([[feedback_autogen_corpo_manca_punto_virgola]]) e
>   che **la firma va presa dall'ultimo YAML**, perché l'auto-gen scioglie i
>   `%TYPE` ([[feedback_autogen_firma_perde_type]]);
> * `%TYPE` in firma, `DECLARE` e `RETURNS`
>   ([[feedback_type_anche_in_firma_e_returns_table]]);
> * errori con `script.fn_log_and_raise_error` e codici **registrati**, con la
>   regola dei tre canali: `codice` al backend, `context->>'campo'` al frontend,
>   `VARIADIC` **all'operatore** ([[feedback_error_codes_messaggi_errore]]).

### 7.0 Il quadro in una tabella

> ✅ **ESEGUITI il 2026-08-26**: L1, L2, L3, L4, L6, L7, L8 e — dopo la
> decisione di Tid di procedere senza aspettare il backend — anche **L5**.
> Registro, scarti dal piano e correzioni nel **§8**. ✅ Anche **L9** è fatto.
> Resta la sola consegna **BE-1**. Il testo qui sotto resta come pianificato.

| Lotto | Cosa | Fase | Dipende da | Sblocca |
| --- | --- | --- | --- | --- |
| **L1** | `trgfn_commesse_default_emittente` + trigger: l'emittente si **deriva dal BA** quando arriva `NULL` | `20_code` | — | rende innocuo il `NOT NULL` di L3 |
| **L2** | `trgfn_commesse_guard_emittente_ba` + trigger: rifiuta un valore **diverso** dal derivato (**H2**) | `20_code` | L1 (per ordine alfabetico) | l'invariante, per **ogni** scrittore |
| **L3** | `NOT NULL` sulla colonna (**H1**) | `00_schema` | L1 — che deve avere un `NN` **più basso** | il buco RLS del §2 |
| **L4** | `fn_get_or_create_commessa`: via il `COALESCE(…, -1)` dalla chiave di riuso | `20_code` | L3 | l'indizio del §3 |
| **L5** | `fn_get_or_create_commessa`: via il **parametro** `p_emittente_soggetto_ruolo_id` (**D-2**) | `20_code` | ⛔ **BE-1** | «sempre derivato, mai passato da fuori» |
| **L6** | omogeneità delle **sorgenti** (**H4**, **D-4**): risolutore polimorfo + check + guard | `20_code` | L2 | «una commessa non aggrega due emittenti» |
| **L7** | codici e messaggi nuovi | `80_data` | — (stesso PR di L2 e L6) | il cancello CI dei codici |
| **L8** | pgTAP: due file nuovi + adeguamento delle fixture che costruiscono lo stato impossibile | `db/pgtap` | L2, L6 | — |
| **L9** | documentazione: `manual/`, guida commesse, `COMMENT` | `docs/` | tutti | — |

⚠️ **L1 → L3 è un vincolo d'ordine vero, e non è quello che sembra.** L'autogen
**mescola** `00_schema` e `20_code` e li ordina per `NN`
([[reference_liquibase_autogen_ordina_per_numero]]): se il `NOT NULL` prendesse
un numero più basso del trigger che riempie la colonna, su un database
ricostruito da zero (cioè **in CI**) ogni `INSERT` che oggi omette l'emittente
fallirebbe nella finestra fra i due changeSet.

⭐ **L4 e L5 si fondono in un solo file se BE-1 arriva prima.** Sono separati
perché L4 è sicuro (`CREATE OR REPLACE`, firma identica) e L5 no (`DROP` +
`CREATE`, e il push si ferma finché il backend non è aggiornato): tenerli
distinti permette di consegnare L4 subito senza tenere in ostaggio niente.

---

### 7.1 L1 — Il riempitore: l'emittente si deriva dal billing account

**File**: `20_code/vendite/AAAAMMGG-NN-create-trgfn-commesse-default-emittente-mctit.yaml`

**Oggetti** da creare:

```text
vendite.trgfn_commesse_default_emittente()   -- RETURNS trigger, plpgsql
trg_commesse_a10_default_emittente_ins       -- BEFORE INSERT, FOR EACH ROW
```

**Corpo, in tre righe di logica** (modello: `trgfn_ordini_default_emittente`,
con la sorgente cambiata da «operatore» a «billing account» — §4.1):

1. se `NEW.emittente_soggetto_ruolo_id IS NOT NULL` → `RETURN NEW` (chi ha
   dichiarato un valore lo tiene: a giudicarlo ci pensa L2, e **il riempitore
   non deve mai sovrascrivere in silenzio** una scelta esplicita — una
   normalizzazione muta è la forma in cui un test diventa verde smettendo di
   verificare);
2. `NEW.emittente_soggetto_ruolo_id := anagrafiche.fn_get_emittente_fiscale_id(NEW.billing_account_id);`
3. `RETURN NEW`.

⭐ **Non serve nessun guard sul NULL residuo, ed è una proprietà della funzione
chiamata, non un'omissione**: `fn_get_emittente_fiscale_id` **solleva**
(`E_EMITTENTE_DEFAULT_MISSING`) invece di tornare `NULL`. È la stessa proprietà
che il §3 registra come «l'unica cosa che oggi garantisce il valore»: qui smette
di essere l'unica e diventa una delle due.

⚠️ **`billing_account_id` è `NOT NULL` sulla commessa**, quindi — a differenza dei
sei fratelli — **non c'è nessun ramo «BA assente» da saltare**. Scriverlo lo
stesso vorrebbe dire lasciare un ramo che nessun percorso può raggiungere.

⭐ **E c'è un effetto collaterale buono, che vale la pena sapere**: PostgreSQL
valuta il `WITH CHECK` della RLS sulla riga **finale**, cioè **dopo** i trigger
`BEFORE`. ⇒ Con L1 in servizio, la policy `rls_commesse_ef_whitelist` giudica
l'emittente **vero** invece di un `NULL` — che oggi, per un operatore con
perimetro ristretto, fa fallire l'`INSERT` in modo fail-closed. Un pezzo del §2
si chiude qui, prima ancora del `NOT NULL`.

⚠️ **Perché `BEFORE INSERT` e basta.** Un `UPDATE … SET emittente = NULL` non ha
bisogno di questo trigger: dopo L3 lo respinge il `NOT NULL`. E far «seguire» il
valore a un cambio di `billing_account_id` sarebbe una propagazione silenziosa su
una colonna di perimetro: chi sposta la commessa di cliente deve dichiarare
**anche** l'emittente, e se sbaglia lo dice L2.

---

### 7.2 L2 — Il guard: e vale per **chi scrive**, non per chi passa dalla funzione

**File**: `20_code/vendite/AAAAMMGG-NN-create-trgfn-commesse-guard-emittente-ba-mctit.yaml`

**Oggetti** da creare:

```text
vendite.trgfn_commesse_guard_emittente_ba()
trg_commesse_a10_guard_emittente_ba_ins_upd
    BEFORE INSERT OR UPDATE OF billing_account_id, emittente_soggetto_ruolo_id
```

**Corpo** (calco di `trgfn_ordini_guard_emittente_ba`, con `fn_get_emittente_fiscale_id`
— la variante `soggetto_ruolo_id` — al posto di `fn_get_emittente_fiscale_pk`):
risolve l'atteso dal BA, e se `NEW.emittente_soggetto_ruolo_id IS DISTINCT FROM`
l'atteso solleva.

⚠️ **`UPDATE OF` e non `UPDATE` nudo, ed è la riga che evita di congelare le
commesse.** Con un `UPDATE` generico, ogni modifica di stato o di competenza
rivaliderebbe l'emittente contro il BA: e nel momento in cui il mapping del BA
cambia (che è il tema dell'**altro brief**), tutte le commesse di quel cliente
diventerebbero **non più modificabili**, con un errore che parla di una colonna
che nessuno stava toccando. Con `UPDATE OF` il guard scatta solo su chi tocca
davvero la coppia, e la fotografia stantìa resta un problema dell'altro cantiere
— dove ha il suo rimedio.

⚠️ **L'ordine dei trigger `BEFORE ROW` è alfabetico**
([[reference_fk_nuova_genera_guard_che_oscura]]). Verificato sulla doc auto-gen:

```text
trg_commesse_a10_default_emittente_ins          ← L1, riempie
trg_commesse_a10_guard_emittente_ba_ins_upd     ← L2, giudica
trg_commesse_a10_guard_transizione_upd          (esistente)
trg_vendite_commesse_a10_guard_chiave_immutabile_upd (esistente, scatta per ultimo: `trg_v…`)
```

`default_` < `guard_` ⇒ **il riempitore gira prima del giudice**, che è l'unico
ordine che funziona. È la stessa disposizione degli ordini
(`trg_ordini_a10_default_emittente_ins` prima di
`trg_ordini_a10_guard_emittente_ba_ins_upd`), e non è un caso: è il motivo per
cui i nomi sono quelli.

#### 7.2.1 ⛔ Il codice nuovo è `TECNICO`, e **diverge di proposito** dai sei fratelli

Il codice si chiama **`E_COMMESSA_EMITTENTE_BA_INCOERENTE`** — il nome della
famiglia, perché chi lo incontra in `error_log` deve riconoscerlo accanto agli
altri cinque. Ma la **classe** no:

| | I sei fratelli | La commessa |
| --- | --- | --- |
| Chi fornisce il valore | una **persona**, in un form documento | **nessuno**: nasce dal push, derivato dal BA |
| Classe | `DATO_ERRATO` (400) | ⭐ **`TECNICO`** (500) |
| `context->>'campo'` | sì: il frontend accende il campo | ⛔ **no**: su un 500 non c'è nessun campo da accendere |

⭐ È il criterio scritto in `.codex/AGENTS.md` § «Sollevare un errore: tre
canali»: *si guarda **parametro per parametro**, non funzione per funzione*, e
qui a quel valore non arriva nessuna persona — solo un chiamante rotto o una
`INSERT` a mano. ⛔ E **non si riusa `E_PARAMETRO_INVALIDO`**: quel codice è un
debito con lo split rimandato, non una sede — precedente
`E_VENDITE_PRICING_ESITO_ASSENTE` (2026-08-19), nato esattamente così.

⛔ **Niente `bersaglio`.** La regola delle linee guida è che il bersaglio si mette
**solo sugli errori rimediabili**: su un `TECNICO` non c'è nessun gesto da
offrire all'operatore, e un pulsante «vai alla commessa» su un 500 è un vicolo
cieco.

**Il messaggio** (canale `VARIADIC` = la frase che legge una persona) nomina
**la commessa e i due emittenti**, non i nomi delle colonne:

> `Commessa %s: l'emittente indicato (%s) non è quello del billing account %s (%s).`

⚠️ Su una `INSERT` il `codice` della commessa **non c'è ancora** (lo genera la
funzione, non un trigger): nel messaggio va il `billing_account_id`, e il
`codice` entra solo quando `NEW.codice` è valorizzato.

---

### 7.3 L3 — `NOT NULL` (H1)

**File**: `00_schema/vendite/AAAAMMGG-NN-alter-commesse-emittente-not-null-mctit.yaml`
(⚠️ `NN` **maggiore** di L1 e L2 — §7.0)

```yaml
- addNotNullConstraint:
    schemaName: vendite
    tableName: commesse
    columnName: emittente_soggetto_ruolo_id
```

**Pre-volo, e non è un changeSet.** Prima di applicare va verificato che non ci
siano righe con la colonna a `NULL`; se ce ne sono, **si correggono a mano** —
è la regola di `AGENTS.md` § Workflow Safety (*«prima di sviluppare fix software
per correggere dati errati, chiedere se è più veloce correggere i dati a
mano»*), e vale a maggior ragione qui, dove il database di sviluppo è una
macchina con dei residui e non un ricostruito da zero
([[feedback_dev_db_non_e_ricostruito_da_zero]]).

⛔ **Nessuna bonifica dentro il changeSet.** Una `UPDATE … SET emittente = fn(...)`
sarebbe una fotografia di un minuto ([[feedback_bonifica_runonchange_false_fotografa_un_minuto]]):
lecita **solo** se il rubinetto è già chiuso — e il rubinetto è L1+L2, che stanno
prima. Se dopo L1+L2 restano righe a `NULL`, sono pregresso da guardare, non da
riscrivere alla cieca.

⚠️ **`SET NOT NULL` fa una scansione completa** e prende un `ACCESS EXCLUSIVE`:
in dev è irrilevante, va detto perché non lo sia altrove.

**Cosa diventa irraggiungibile, e resta:** `script.fn_check_commessa_pronta_fatturazione`
solleva oggi `E_COMMESSA_EMITTENTE_MANCANTE` per la commessa senza emittente.
Dopo L3 quel ramo **non è più raggiungibile**. ⭐ Non si toglie: un ramo non si
smonta perché oggi non ci si arriva (`AGENTS.md`, Regola zero) — si **dichiara**,
con un commento che dice «presidiato a monte dal `NOT NULL` del
AAAAMMGG-NN», così il prossimo lettore non lo scambia per un caso vivo. Il
codice resta a catalogo, **non** si marca `obsoleto_dal`.

---

### 7.4 L4 — Il `COALESCE(…, -1)` esce dalla chiave di riuso

**File**: `20_code/vendite/AAAAMMGG-NN-update-fn-get-or-create-commessa-emittente-non-null-mctit.yaml`
· `CREATE OR REPLACE`, **firma identica**, nessun `DROP`.

Nel `WHERE` della commessa riusabile (**SPECCHIO 2**):

```diff
-   AND COALESCE(c.emittente_soggetto_ruolo_id, -1) = COALESCE(v_emittente, -1)
+   AND c.emittente_soggetto_ruolo_id = v_emittente
```

È l'indizio del §3 — *quando il codice si protegge da uno stato impossibile, di
solito è perché impossibile non è* — e dopo L3 lo stato è davvero impossibile.
⚠️ Con un `=` puro e una colonna `NOT NULL` non si riapre la trappola del `NULL`
nella chiave ([[feedback_null_nelle_chiavi_due_forme]]): la trappola è
`IS NOT DISTINCT FROM` **dove il NULL può esserci**, e qui non può più.

⛔ **Il `COALESCE` dentro l'hash dell'advisory lock (SPECCHIO 1) NON si tocca.**
Cambiare la stringa che si hasha cambia **l'identità del lock** senza cambiare
niente di utile: due sessioni che girassero su due revisioni diverse della
funzione smetterebbero di serializzarsi. Va invece aggiunto **il commento** che
dice perché resta ([[reference_advisory_lock_2_arg_namespace]] — la forma a due
argomenti è già corretta).

⚠️ **Il commento sui «tre specchi» va aggiornato**, non lasciato: dice che i tre
vanno tenuti identici, e da qui in poi uno dei tre è deliberatamente diverso. Un
commento che descrive il codice di ieri è la forma più economica di bug.

---

### 7.5 L5 — Il parametro sparisce (D-2) · ⛔ cancello **BE-1**

**File**: `20_code/vendite/AAAAMMGG-NN-recreate-fn-get-or-create-commessa-senza-override-mctit.yaml`

`DROP` + `CREATE` **nello stesso changeSet** (è la forma già in uso nel
repo, es. `20260826-08`): togliere un parametro non si può fare con
`CREATE OR REPLACE`, e farlo in due file aprirebbe il problema dell'ordine
([[reference_liquibase_autogen_ordina_per_numero]]).

```sql
DROP FUNCTION IF EXISTS vendite.fn_get_or_create_commessa(
    bigint, integer, varchar, varchar, boolean, varchar, bigint,
    date, date, jsonb, boolean, bigint, integer);
```

⚠️ **Nessun `CASCADE`**, mai.
⚠️ La `preCondition` che verifica «esiste la vecchia firma» si scrive su
**`pronargs = 13`**, non confrontando la stringa dei tipi: quella include anche i
**nomi** dei parametri e non combacia mai, fermando il migrate
([[reference_pg_get_function_identity_arguments_include_i_nomi]]).
⚠️ Dopo il `DROP` i `GRANT` sulla funzione se ne vanno: li rimette il giro di
`90_end`/`ci_apply` — che su dev gira **la sera**, non al migrate
([[reference_automazioni_solo_ci_apply_su_migrate]]). Se il push va provato
subito, il `GRANT EXECUTE` va rimesso a mano.

**Nel corpo** resta una riga sola da cambiare:

```diff
-   v_emittente := COALESCE(p_emittente_soggetto_ruolo_id, anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id));
+   v_emittente := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);
```

⛔ **BE-1 — consegna backend.** Il perimetro DB non tocca `backend/`: qui si
chiede, non si scrive ([[feedback_perimetro_db_no_modifiche_be]]).

| Dove | Cosa |
| --- | --- |
| `backend/apps/vendite/db/commesse_repository.py` (`get_or_create_commessa`) | togliere il parametro `emittente_soggetto_ruolo_id` dalla firma e la riga `p_emittente_soggetto_ruolo_id => %s` dalla `SELECT` |
| `backend/apps/vendite/services/commesse_source_handlers.py` | togliere `emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id` dalla chiamata |
| `backend/apps/vendite/tests/services/test_commesse_repository.py` | l'asserzione sull'SQL generato |
| `backend/scripts/tests/smoke-*.py` (4 file) | le chiamate dirette alla funzione |

⚠️ `row.emittente_soggetto_ruolo_id` **resta** in `PushableRow`: le
`fn_list_*_da_pushare` continuano a esporlo e serve altrove. Cambia solo chi lo
ri-passa al database.

---

### 7.6 L6 — L'omogeneità delle sorgenti (H4 · D-4)

**File** (tre oggetti, un file ciascuno, `NN` crescente nell'ordine):

1. `20_code/script/…-create-fn-get-sorgente-billing-account-id-mctit.yaml`
2. `20_code/vendite/…-create-fn-check-commessa-sorgente-emittente-mctit.yaml`
3. `20_code/vendite/…-create-trgfn-commesse-sorgenti-guard-emittente-mctit.yaml`

#### 7.6.1 Il pezzo che manca è «di chi è questo documento?»

```sql
script.fn_get_sorgente_billing_account_id(
    p_sorgente_tipo_id config.sorgenti.id%TYPE,
    p_sorgente_uid     vendite.commesse_sorgenti.sorgente_uid%TYPE)
  RETURNS anagrafiche.billing_account.id%TYPE
  STABLE SECURITY DEFINER SET search_path TO 'pg_catalog','public'
```

Legge `target_table` e `key_selector` da `config.sorgenti` e va a prendere
`billing_account_id` nella tabella giusta con l'SQL dinamico che è **già
l'idioma di casa** per questo meccanismo — lo fanno sia
`script.trgfn_guard_sorgente_polimorfa_testuale` sia `fn_link_commessa_sorgente`
(`EXECUTE format('… FROM %s WHERE id = $1', v_tbl)`), con la stessa presenza di
colonna verificata su `pg_attribute`.

⚠️ **`SECURITY DEFINER`, e non è opzionale**: `preventivi`, `ordini`, `ddt`,
`contratti`, `offerte_commerciali` e `resi` hanno **tutti** una policy RLS
`ef_whitelist`. Da `SECURITY INVOKER` la sorgente di un altro emittente sarebbe
**invisibile**, e il guard direbbe «a posto» proprio nel caso da bloccare — è la
stessa ragione, scritta con le stesse parole, per cui
`fn_guard_albero_ba_emittente` è `DEFINER` ([[reference_trigger_guard_legge_sotto_rls]]).

⛔ **Fail-closed su tutto ciò che non risolve**: tipo non a catalogo, colonna
assente nella `target_table`, documento inesistente ⇒ errore, mai `NULL`
silenzioso. Un risolutore che risponde `NULL` fa passare il confronto a valle
e trasforma il guard in un no-op.

⭐ **Verificato il 2026-08-26 sulla doc auto-gen**: tutte le `target_table` di
`config.sorgenti` hanno una colonna `billing_account_id` (`preventivi`, `ordini`,
`ddt`, `contratti`, `attivita_consumi`, `offerte_commerciali`, `resi`, `fatture`,
`commesse`, `attivita_fatturabili`). ⚠️ In cinque casi è **nullable**: un
documento senza BA non ha un emittente da confrontare, e il guard **blocca**
invece di saltare — collegare a una commessa un documento di cui non si sa di chi
è, è esattamente il caso che l'invariante deve rifiutare.

#### 7.6.2 Il check e il guard

```sql
vendite.fn_check_commessa_sorgente_emittente_omogeneo(
    p_commessa_id, p_sorgente_tipo_id, p_sorgente_uid) RETURNS boolean
```

Pure check, nessun raise ([[feedback_read_sql_guidelines_before_script]] §5):
confronta `anagrafiche.fn_get_emittente_fiscale_id` del BA della commessa con
quello del BA della sorgente. **NULL su uno dei due ⇒ `false`** (fail-closed, e
⛔ **non** `IS NOT DISTINCT FROM`: è il calco esatto di
`fn_check_ba_coppia_emittente_omogenea`, che quella trappola l'ha già chiusa).

```text
vendite.trgfn_commesse_sorgenti_guard_emittente()
trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd
    BEFORE INSERT OR UPDATE OF commessa_id, sorgente_tipo_id, sorgente_uid
```

⚠️ **Il nome del trigger è scelto per l'ordine, non per l'estetica.** Sulla
tabella c'è già `trg_commesse_sorgenti_a10_guard_sorgente_ins_upd` (il guard
polimorfo, che verifica **che il documento esista**). I `BEFORE ROW` scattano in
ordine alfabetico: con un nome come `…a10_guard_emittente_…` il nostro girerebbe
**prima**, e proverebbe a risolvere il BA di un documento che potrebbe non
esistere — restituendo il nostro errore al posto del suo, che è più preciso.
`…a10_guard_sorgente_omogeneita_…` viene dopo `…a10_guard_sorgente_…`
(`o` > `i`), che è l'ordine giusto.

⛔ **Il guard sta sul trigger, non dentro `fn_link_commessa_sorgente`** — stessa
ragione di L2: la funzione è uno scrittore, il trigger è il vincolo.
`fn_link_commessa_sorgente` **non si tocca affatto** in questo lotto.

**Codice**: `E_COMMESSA_SORGENTE_EMITTENTE_MISTO`, classe **`TECNICO`**, per lo
stesso criterio del §7.2.1 — oggi le sorgenti le collega il push, non una
persona. ⚠️ **Da rivedere il giorno in cui il frontend offrirà un gesto
«aggiungi questo documento alla commessa»**: allora a quel valore ci arriva un
operatore, e la classe diventa `DATO_ERRATO` con `campo` e `bersaglio`. Scritto
qui perché non venga scoperto da capo.

---

### 7.7 L7 — I codici (`80_data`)

⛔ **Solo append ai due CSV, nessun loader nuovo**
([[feedback_messaggi_errore_no_new_loader]]): i mirror `runOnChange` esistenti li
ripescano da soli.

| File | Cosa si aggiunge |
| --- | --- |
| `80_data/sql/config/codici_errore.csv` | `E_COMMESSA_EMITTENTE_BA_INCOERENTE,TECNICO,NULL,"…"` · `E_COMMESSA_SORGENTE_EMITTENTE_MISTO,TECNICO,NULL,"…"` |
| `80_data/sql/config/messaggi_errore.csv` | una riga `it` per ciascuno, con `causa` e `soluzione` |

⚠️ Nella colonna `note` di `codici_errore.csv` va scritto **perché** la classe
diverge dalla famiglia `E_*_EMITTENTE_BA_INCOERENTE` (§7.2.1): senza, il primo
che farà un audit di coerenza la allineerà «per uniformità» e romperà lo status
HTTP.
⚠️ L'`id` in `messaggi_errore.csv` è un progressivo: **si rilegge il massimo al
momento di scrivere**, non si deduce da questo brief.
⚠️ **Arità**: il numero di `%s` nel messaggio deve corrispondere ai valori
passati nel `VARIADIC`, o `format()` alza `22023` e l'errore di dominio sparisce
([[reference_messaggi_errore_segnaposto_rompe_format]]).
⚠️ I `NULL` nel CSV sono il **token letterale** `NULL`, non la cella vuota
([[feedback_liquibase_csv_null_sentinel]]).

---

### 7.8 L8 — I presidi, e la parte scomoda

**Due file nuovi** (da `db/pgtap/_TEMPLATE.sql.txt`, con le tre righe di
preambolo obbligatorie — `BEGIN`, contesto operatore, `SET CONSTRAINTS ALL IMMEDIATE`):

* `db/pgtap/vendite/test-commesse-emittente-invariante-v1.sql`
  1. la colonna è `NOT NULL` (`col_not_null`);
  2. `INSERT` senza emittente ⇒ la riga nasce con quello del BA (L1);
  3. `INSERT` con un emittente **diverso** ⇒ `throws_ok(…, 'P0001')` +
     `throws_like` sulla frase (L2);
  4. `UPDATE` che sposta l'emittente su un altro ⇒ blocca;
  5. `UPDATE` di una colonna **qualsiasi** (es. lo stato) ⇒ **passa**: è
     l'asserzione che presidia la scelta `UPDATE OF` del §7.2, e senza di lei il
     giorno in cui qualcuno la toglie non se ne accorge nessuno.
* `db/pgtap/vendite/test-commessa-sorgente-emittente-omogeneo-v1.sql`
  1. sorgente dello stesso emittente ⇒ collega;
  2. sorgente di un **altro** emittente ⇒ `throws_ok(…, 'P0001')`;
  3. sorgente con BA `NULL` ⇒ blocca (fail-closed).

⚠️ `throws_ok` **sempre con lo SQLSTATE**: senza, accetta qualunque errore, anche
il crash del guard ([[feedback_pgtap_throws_ok_senza_sqlstate]]).
⚠️ Le fixture si **fabbricano** il caso (due emittenti, due BA mappati): un test
che cerca fra i dati esistenti passa a vuoto in CI, dove il database è
ricostruito da zero (`AGENTS.md`, corollario sui test).
⚠️ Niente `LIMIT 1` senza `ORDER BY` nella scelta dei soggetti
([[feedback_pgtap_limit1_senza_orderby]]).

#### 7.8.1 ⛔ La parte scomoda: **18 fixture su 22 costruiscono lo stato impossibile**

Misura **strutturale** del 2026-08-26 (sono file di test, non righe di dati):
22 file pgTAP fanno `INSERT INTO vendite.commesse (…)` diretto; di questi,
**18 non chiamano né `fn_get_emittente_fiscale_id` né `fn_get_ba_emittente_sr_id`**,
cioè scelgono l'emittente **indipendentemente** dal billing account che stanno
inserendo.

⭐ **Non è un costo di adeguamento: è il difetto, visto dall'altro lato.** Quelle
fixture costruiscono uno stato che il modello non deve ammettere, e i test che ci
girano sopra dicono qualcosa su una commessa che non potrebbe esistere. Che
diventino rossi è l'unica cosa sensata che possano fare.

**Come si esegue**, senza inseguire rossi altrui:

```bash
scripts/pgtap-baseline.sh vendite          # PRIMA di L2: fotografia del noto
# … applicazione dei lotti …
scripts/pgtap-baseline.sh vendite          # DOPO: le regressioni sono solo le nuove
scripts/pgtap-baseline.sh --update vendite # solo a file sanati
```

⚠️ La suite ha **rossi preesistenti**: un rosso non si attribuisce alla propria
modifica senza guardare quale baseline lo conosce — e in CI la baseline è
un'altra (`baseline-rossi-ci.tsv`), perché quel database è ricostruito da zero.
⚠️ Un file che fallisce **nella fixture** non esegue nessuna asserzione: la sua
copertura vale **zero**, non «parziale». Sanarlo non è cosmesi.

---

### 7.9 L9 — Documentazione

| Dove | Cosa |
| --- | --- |
| `docs/it/dbzero/vendite/manual/` | scheda per `trgfn_commesse_default_emittente`, `trgfn_commesse_guard_emittente_ba`, `trgfn_commesse_sorgenti_guard_emittente`, `fn_check_commessa_sorgente_emittente_omogeneo` |
| `docs/it/dbzero/script/manual/` | scheda per `fn_get_sorgente_billing_account_id` |
| `docs/it/guide/gestione-commesse.md` | la sezione «di chi è questa commessa»: l'emittente si deriva dal BA, non si sceglie |
| `docs/it/guide/sorgente-polimorfa.md` | il risolutore nuovo nell'elenco dei pezzi che usano il meccanismo |
| `COMMENT ON` | su ogni funzione nuova, dentro il changeSet che la crea |

⛔ **Non si toccano** i file auto-generati in `docs/it/dbzero/<schema>/{tabelle,funzioni,views}/`:
si rigenerano ([[feedback_no_hand_edit_autogen_docs]]).
⛔ **Non si lancia la build della doc** ([[feedback_no_build_doc]]): verifica con
grep mirato.
⛔ Nei `COMMENT` e negli YAML si cita **il nome del brief**, mai il path
`work-in-progress/` ([[feedback_no_path_wip_negli_yaml]]): quella stringa finisce
nel database e a cantiere chiuso il documento si sposta.

---

### 7.10 Verifica — cosa si fa prima di dire «fatto», per ogni lotto

1. `liquibase validate` e `updateSQL` (che **non** applica) — restano liberi
   dall'hook che blocca il migrate;
2. l'SQL si prova **estratto dallo YAML**, non riscritto a mano: la copia salta
   sempre i `COMMENT` e i `GRANT`, ed è lì che il migrate muore
   ([[feedback_verificare_sql_estratto_non_riscritto]]);
3. il `BEGIN; … ROLLBACK;` dev'essere **nel file che si esegue**, altrimenti psql
   scrive davvero ([[feedback_verifica_sql_wrapper_transazione]]);
4. baseline pgTAP degli schemi toccati (`vendite`, `script`, `anagrafiche`);
5. ⛔ **l'applicazione la autorizza Tid, a parole, per quel comando**: «procedi»
   autorizza il lavoro, non la migrazione ([[feedback_mai_applicare_migrazioni_db]]).

---

### 7.11 Cosa questo piano **non** fa

* ⛔ **Non tocca il caso «il BA cambia emittente»**: è
  [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md),
  e il §7.2 spiega perché la scelta di `UPDATE OF` fa sì che questo cantiere
  resti corretto qualunque cosa si decida là.
* ⛔ **Non rende immutabili le altre dimensioni della chiave di raggruppamento.**
  `billing_account_id`, `utility_id`, `tipo_commessa`, `policy_fatturazione`,
  `priorita_operativa` e la competenza sono tutte parte della chiave di
  `fn_get_or_create_commessa` e **nessuna** è bloccata dopo la nascita
  (`trgfn_commesse_guard_chiave_immutabile` presidia solo termine e modalità di
  pagamento). È un difetto della stessa famiglia, **non è questo cantiere**, e va
  scritto perché non si perda: ▶ debito nuovo, da aprire.
* ⛔ **Non toglie** `E_COMMESSA_EMITTENTE_MANCANTE` né il ramo che lo solleva
  (§7.3).
* ⛔ **Non cambia** `fn_link_commessa_sorgente` (§7.6.2).

### 7.12 ✅ D-5 CHIUSA — lo scenario «tutte le azioni disabilitate» esce dal modello e ci resta

> **Aperta e chiusa il 2026-08-26**, dopo il rosso di
> `vendite/test-guard-uscita-commessa-v1`. Era una domanda di **prodotto**, non
> di implementazione: per questo non l'ho chiusa da solo.
> ✅ **Decisione di Tid**: nessuna regola nuova. Lo `skip()` dichiarato è la
> forma giusta.

Il `NOT NULL` ha tolto l'ultima leva che rendeva raggiungibile lo scenario in cui,
da `IN_ESECUZIONE`, **tutte e tre** le azioni manuali sono spente. La
dimostrazione è nel §8 (voce «La baseline ha parlato»): `chiudi` disabilitato
**implica** `rendi_pronta` abilitato, perché un guard di riga impone
`APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`.

⚠️ **Non è una perdita qualunque.** Il test 14 nasce per distinguere *«azioni
presenti ma tutte spente»* da *«nessuna azione»* — il suo commento lo dice:
*«col vecchio `jsonb_array_length(actions) > 0` questo test fallirebbe»*.
Spostarlo su uno stato terminale lo farebbe passare **smettendo di verificare
proprio quella distinzione**.

**Le tre strade, e quella che consiglio:**

| | Strada | Costo |
| --- | --- | --- |
| **a** | I test 14a/14 dichiarano lo stato vero (`annulla` e `chiudi` spente, `rendi_pronta` accesa) e `can_change_state = true` | ⛔ si perde la sola prova che `can_change_state` non è `count(actions) > 0` |
| **b** | Si tiene il ramo «emittente mancante» come **presidio dichiarato** e i due test si marcano `skip()` motivato | ⚠️ un ramo irraggiungibile con un test che non gira: due debiti al prezzo di uno |
| ~~**c**~~ | ~~Si cerca **un'altra condizione di testata** che spenga `rendi_pronta`~~ | ⛔ **caduta**: la condizione non esiste (sotto) |

#### ⛔ Perché la **c** è caduta, ed è la parte che vale

Il candidato che avevo proposto era la **competenza**: *«una commessa con
competenza non ancora aperta non dovrebbe potersi dichiarare pronta»*. Letto il
codice della lane, non regge — e la ragione è generale.

Il filtro è `ca.competenza_mese <= v_competenza_mese`, e cioè:

* sta sulle **righe**, non sulla testata (la competenza di testata è nullable e
  la lane non la guarda affatto);
* è **cumulativo**, non «del mese»;
* e il mese è un **parametro del giro**: con `p_competenza_mese` a `NULL` il
  filtro non esiste proprio.

⇒ **Esempio (Tid, 2026-08-26)**: oggi è agosto 2026, la commessa ha righe di
competenza **settembre**. Il giro di agosto non la prende — e fa bene, non è
dovuta. Il giro di settembre, o un giro senza limite di mese, la prende.
⇒ Quella commessa **è pronta**: non è pronta *per il giro di agosto*.

⛔ Bloccarla direbbe all'operatore una cosa **falsa**, e sarebbe di nuovo *un
guard che rifiuta uno stato che il modello ammette* — lo stesso difetto trovato
poche ore prima nel risolutore delle sorgenti (§8), stavolta commesso per far
tornare verde un test.

⭐ **La distinzione da ricordare**: «non pronta» è una proprietà **della
commessa**, «non ancora presa» è una proprietà **del giro**. Metterla nella
funzione di dominio significherebbe spostarci dentro una regola dello scheduler.

⚠️ E non c'è un altro candidato: passate in rassegna le colonne di testata —
stato, tipo, policy, fatturazione immediata, condizioni di pagamento, cliente,
utility — nessuna è una condizione di *prontezza*. Con l'emittente ora garantito,
di condizioni di testata **non ne resta nessuna**.

⇒ Il test 14 riavrà un soggetto **solo** se un giorno nascerà una condizione di
testata per un suo motivo di dominio, non per riempire questo vuoto.

✅ **Nel frattempo il file è tornato verde senza barare** (2026-08-26, `plan(17)`):

* il test **14a** ora asserisce lo **stato vero** — `annulla` e `chiudi` spente,
  `rendi_pronta` accesa — e resta un'asserzione forte: diventa rosso sia se
  l'elenco delle azioni si svuota, sia se `rendi_pronta` si spegnesse insieme a
  `chiudi`, cioè se l'invariante del `tipo_doc` cadesse;
* il test **14** è uno **`skip()` dichiarato**, non un'asserzione indebolita.
  Riscriverlo su `can_change_state = true` lo farebbe passare **smettendo di
  verificare proprio la distinzione per cui era nato** — «azioni presenti ma
  tutte spente» contro «nessuna azione». Il debito resta scritto lì, e punta qui.

⚠️ Anche il marcatore `pgtap-runner: owner` di quel file è ora **senza il suo
motivo**: l'unica ragione era l'`UPDATE` che azzerava l'emittente, e quella
colonna non è più scrivibile da nessuno — owner compreso. ⛔ Non l'ho tolto:
cambiare il ruolo con cui gira l'intero file dentro un commit che sta chiudendo
un'altra cosa vorrebbe dire mescolare eventuali rossi da RLS a questi. Va
rivalutato **in un cantiere suo**, ed è dichiarato nell'intestazione del file.

## 8. Registro

### 2026-08-26 · Nascita

Nato da una segnalazione che avevo classificato **minore** chiudendo la D-6 del
cantiere «registro e data prevista». Approfondendola su richiamo di Tid è emerso
che la colonna non è un attributo ma la **chiave di perimetro** della commessa —
row security, scope delle viste del cruscotto, giornale degli eventi — e che il
ramo peggiore (**H3**, la fotografia che invecchia) non richiede nessun errore da
parte di nessuno.

⛔ Nessun file scritto, nessuna migrazione. Quattro decisioni aperte, e la prima
(che cos'è la cascata) va chiusa prima delle altre tre.

### 2026-08-26 · Prime decisioni, e una separazione

✅ **D-1 chiusa** (nessuna cascata: la sede è il billing account) e **H1
confermato** da correggere. ⭐ D-1 chiusa inclina D-2: se l'emittente è sempre
derivato, l'override non serve.

⛔ **H3 e D-3 sono usciti da questo brief** su richiesta di Tid — *«dobbiamo
riflettere su questo e non mescolare»*. Sono diventati
[brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md):
là c'è una domanda di dominio con implicazioni fiscali, qui un difetto con un
rimedio chiaro. ⭐ **Separarli serve a non far aspettare il secondo per colpa del
primo**: `NOT NULL` più il vincolo al billing account restano giusti qualunque
risposta si dia là.

### 2026-08-26 · Piano di sviluppo (§7), e le ultime due decisioni chiuse

Richiesta di Tid: *«dobbiamo fare lo sviluppo; prepara un piano all'interno dei
documenti per l'esecuzione, tenendo conto dei documenti di progetto e soprattutto
delle linee guida SQL; non iniziare lo sviluppo»*.

**Nove lotti** (§7.0), nessun file scritto. ✅ **D-2 chiusa** — l'override si
toglie *e* nel frattempo lo controlla il trigger, che non sono due risposte ma
due lotti in fila. ✅ **D-4 chiusa** — le sorgenti eterogenee si bloccano, sul
criterio **emittente** e non su quello (più stretto, e mai deciso da nessuno)
dell'identità del billing account.

⭐ **La scoperta che ha cambiato la forma del piano** è nel §4.1: il presidio
«emittente coerente col billing account» **esiste già su sei tabelle** del ciclo
di vendita, con nomi in famiglia (`trgfn_*_default_emittente` +
`trgfn_*_guard_emittente_ba`). La commessa è l'unica che porta un emittente e non
ha né l'uno né l'altro. Non c'era niente da inventare: c'era una riga vuota in
una tabella già piena.

⚠️ **Tre cose che il piano ha dovuto guardare, e non erano nel brief:**

* i **`BEFORE ROW` scattano in ordine alfabetico** — è il motivo per cui il
  riempitore si chiama `default_…` e il giudice `guard_…` (§7.2), e per cui il
  guard sulle sorgenti si chiama `…guard_sorgente_omogeneita_…` e non
  `…guard_emittente_…` (§7.6.2);
* l'autogen **mescola** `00_schema` e `20_code` ordinando per `NN`: il `NOT NULL`
  deve avere un numero **più alto** del trigger che riempie la colonna, o in CI
  si apre una finestra in cui ogni `INSERT` senza emittente fallisce (§7.0);
* **18 fixture pgTAP su 22** scelgono l'emittente della commessa senza guardare
  il billing account (§7.8.1). Non è un costo di adeguamento: è il difetto visto
  dall'altro lato — quelle fixture costruiscono uno stato che il modello non deve
  ammettere.

⛔ Nessuna migrazione applicata, nessun file scritto: l'esecuzione parte su
«procedi», lotto per lotto.

### 2026-08-26 · Esecuzione — L1, L2, L3, L4, L6, L7, L8

> ⛔ **File scritti, migrazione NON applicata** — *vero al momento in cui questa
> voce è stata scritta; Tid ha applicato più tardi lo stesso giorno.*
> ([[feedback_mai_applicare_migrazioni_db]]). Numerazione ripresa da `39`: il
> repo era arrivato a `20260826-38`.

| # | File | Lotto |
| --- | --- | --- |
| 39 | `20_code/vendite/…-create-trgfn-commesse-default-emittente-mctit.yaml` | **L1** |
| 40 | `20_code/vendite/…-create-trgfn-commesse-guard-emittente-ba-mctit.yaml` | **L2** |
| 41 | `00_schema/vendite/…-alter-commesse-emittente-not-null-mctit.yaml` | **L3** |
| 42 | `20_code/vendite/…-update-fn-get-or-create-commessa-emittente-non-null-mctit.yaml` | **L4** |
| 43 | `20_code/script/…-create-fn-get-sorgente-billing-account-id-mctit.yaml` | **L6a** |
| 44 | `20_code/vendite/…-create-fn-check-commessa-sorgente-emittente-mctit.yaml` | **L6b** |
| 45 | `20_code/vendite/…-create-trgfn-commesse-sorgenti-guard-emittente-mctit.yaml` | **L6c** |
| — | `80_data/sql/config/codici_errore.csv` · `messaggi_errore.csv` (+3 codici, id 1003–1005) | **L7** |
| — | `db/pgtap/vendite/test-commesse-emittente-invariante-v1.sql` `plan(7)` | **L8** |
| — | `db/pgtap/vendite/test-commessa-sorgente-emittente-omogeneo-v1.sql` `plan(6)` | **L8** |

**⚠️ Tre scarti dal piano, e vanno letti.**

1. ⛔ **`E_PARAMETRO_INVALIDO` NON è stato riusato nel risolutore nuovo.** Il
   piano non lo diceva, e il guard sul parametro ID sarebbe finito lì per
   inerzia: `AGENTS.md` lo vieta esplicitamente in codice nuovo — *«quel codice
   è un debito, non una sede»*. Il guard c'è (lo impone la convenzione sugli ID)
   e solleva **`E_SORG_CONF`**, che è quello che dice davvero: «configurazione
   sorgente non risolvibile».
2. ⭐ **Il check delle sorgenti ha una scorciatoia esplicita** che il piano non
   prevedeva: *stesso billing account → true senza risolvere*. È il caso normale
   del push, ed evita di propagare un difetto di configurazione (nessun gestore
   globale) su un giro che non ha niente da presidiare. È dichiarata nel corpo,
   non nascosta.
3. ⭐ **L6 è diventato tre oggetti invece di due**: al `fn_check_*` si è
   affiancato un **`fn_guard_*`** `SECURITY DEFINER` che compone la frase, e il
   `trgfn_*` è rimasto sottile. Non è barocchismo: è il calco esatto della terna
   già in servizio in `anagrafiche` (`fn_check_ba_coppia_emittente_omogenea` /
   `fn_guard_albero_ba_emittente` / `trgfn_efba_guard_albero_emittente`), e serve
   perché il messaggio va composto leggendo **sotto RLS**.

⭐ **Un'asserzione che non era nel piano e che vale**: il test 6 del file sulle
sorgenti presidia **l'ordine alfabetico dei due trigger**. Se qualcuno
rinominasse il guard nuovo, quello è l'unico posto in cui il cambiamento si
vedrebbe — prima che si metta a risolvere il billing account di un documento
fantasma.

**Verifiche fatte** (tutte statiche: nessun `migrate`, nessun `updateSQL` sul DB):

* i 7 YAML parsano; `scripts/guardrail_run_on_change.py` ✅;
  `scripts/guardrail_sql_letterali.py` ✅ (3005 changelog, nessun letterale
  aperto); `scripts/guardrail_pgtap_preambolo.py` ✅ (515 file, e il debito
  `throws_ok` senza discriminante resta **131 su soglia 131**: i nuovi passano
  tutti lo SQLSTATE);
* **arità dei messaggi verificata una per una** contro i valori nel `VARIADIC`
  ([[reference_messaggi_errore_segnaposto_rompe_format]]): 4/4/2 sui codici
  nuovi, e 1 su `E_SORG_CONF`, 1 su `E_SORG_FORMATO`, 1 su `E_SORG_KEYSEL`, 2 su
  `E_SORG_KEY_MISSING` per quelli riusati;
* ⚠️ la firma del `COMMENT ON FUNCTION` del 42 è quella **risolta**
  (`bigint, integer, character varying, …`) e non i `%TYPE`: in DDL plain non
  valgono ([[feedback_type_ddl_contexts]]).

**Cosa resta**

* ~~⛔ **L5** — la rimozione di `p_emittente_soggetto_ruolo_id`: **non scritto**,
  ha il cancello **BE-1** ed è l'ultimo lotto per costruzione.~~
  ✅ **Fatto il 2026-08-26** (`20260826-52`), su decisione di Tid: *«visto che
  non c'è produzione possiamo procedere con L5, poi passo tutto al BE»*.
  ⭐ È anche l'ordine migliore — il backend riceve il database **già nella forma
  finale**, invece di doverlo inseguire in due giri.
* ~~**L9** — documentazione `manual/` e guide.~~ ✅ **Fatto il 2026-08-26**:
  8 pagine `manual/` + 4 guide. Dettaglio nella voce di registro «Documentazione».
* ⚠️ **Il pre-volo di L3 non è stato eseguito**: la `preCondition` del 41 ferma
  il migrate se esistono commesse con l'emittente a `NULL`. Va guardato **prima**
  di autorizzare l'apply, e quelle righe si correggono a mano.
* ⚠️ **La baseline pgTAP non è stata misurata** (serve il DB): resta il §7.8.1 —
  18 fixture su 22 scelgono l'emittente senza guardare il billing account.

### 2026-08-26 · La baseline ha parlato — ⛔ e uno dei tre rossi era **mio**

Applicati i changeSet, Tid ha misurato: **1 regressione in `anagrafiche`, 3 in
`vendite`**. Due erano fixture, una era un difetto di progetto.

#### ⛔ Il difetto: il risolutore passava dalla strada sbagliata

`script.fn_get_sorgente_billing_account_id` (20260826-43) risolveva l'emittente
di un documento **passando dal suo billing account**. Letto sulla doc auto-gen:

| tabella sorgente | `billing_account_id` | `emittente_fiscale_id` |
| --- | --- | --- |
| ordini · preventivi · ddt · resi | **NULLABLE** | NOT NULL |
| contratti · offerte_commerciali | NOT NULL | NOT NULL |

⇒ Su **quattro tabelle su sei** il billing account può mancare — ed è uno stato
**legale** del modello — mentre l'emittente c'è sempre. Il risolutore si fermava
fail-closed su documenti perfettamente validi: *un guard che rifiuta uno stato
che il modello ammette non è severo, è rotto.*

⭐ **L'ha trovato un pgTAP, non un ragionamento**:
`vendite/test-ordini-guard-transizione-v1` crea ordini con
`billing_account_id = NULL` **di proposito**, e ne collega uno a una commessa.
È esattamente il corollario di `AGENTS.md`: un ramo si verifica dal percorso che
lo attraversa.

⚠️ **E la tentazione era il fail-open.** I sei guard fratelli, davanti a un BA
nullo, *saltano* (*«Skip: nessun BA su cui ancorare la coerenza»*). Copiarli qui
sarebbe stato naturale e sbagliato: **loro** confrontano il BA con l'emittente,
**questo** confronta due emittenti — e l'emittente si legge, non si deduce.

**Correzione forward-only** (`20260826-50`, `-51`):
`script.fn_get_sorgente_emittente_sr_id` risponde **«chi lo emette»** con tre
strade in ordine di direttezza — colonna SR (commesse, fatture, lotti),
`emittente_fiscale_id` tradotto in SR (i sei documenti), billing account (le due
tabelle attività). Il predecessore è `DROP`pato e il codice
`E_SORG_BA_NON_RISOLTO`, nato e ritirato lo stesso giorno, è sostituito da
`E_SORG_EMITTENTE_NON_RISOLTO`.
⭐ Il check ne esce **più semplice**: la commessa l'emittente ce l'ha addosso
(`NOT NULL` dal `-41`), quindi il confronto è fra due colonne e cade anche la
scorciatoia «stesso BA → true».

##### ⛔ E il ritiro del codice vecchio l'avevo scritto come `DELETE`. Il migrate l'ha fermato

Prima stesura del `-50`: due `DELETE` su `codici_errore` e `messaggi_errore` per
togliere `E_SORG_BA_NON_RISOLTO`, motivati con la regola *«loadUpdateData non
cancella, quindi il DELETE forward-only è l'unica forma ammessa»*. Il migrate è
fallito:

> `l'istruzione UPDATE o DELETE sulla tabella "messaggi_errore" viola il vincolo`
> `di chiave esterna "fk_error_log_messaggio_errore_id" ... La chiave (id)=(1005)`
> `è ancora referenziata dalla tabella "error_log"`

⭐ **Ha detto la cosa giusta.** Quella FK significa che il codice **era già stato
sollevato** — nelle corse pgTAP di poche ore prima — e cancellarlo vorrebbe dire
**riscrivere il giornale per far tornare i conti a una rinomina**. La regola che
avevo citato parla di righe che devono sparire; una voce di catalogo che qualcuno
ha già letto nel giornale non è una di quelle. Il pattern giusto c'era già ed è
`obsoleto_dal`, lo stesso di qualunque voce di catalogo referenziata.

⚠️ **E sotto ce n'era una peggiore, che il migrate non avrebbe fermato**: nel CSV
avevo **riusato l'id 1005** per il codice nuovo. Il loader è `loadUpdateData`:
avrebbe **rinominato in place** il messaggio a cui quelle righe di `error_log`
puntano, e da lì in avanti il giornale avrebbe raccontato un altro codice. Il
codice nuovo prende l'id **1007**.

#### ✅ Le due fixture, e sono la §7.8.1 al lavoro

* `anagrafiche/test-emittenti-fiscali` — costruiva lo stato «BA senza mapping»
  **prendendo in prestito** un cliente vero (30 commesse). Ora **se lo fabbrica**.
  ⭐ È la stessa lezione che quel file aveva già imparato una volta, un livello
  più sotto: non bastava costruire il *mapping*, andava costruito il *cliente*.
  ✅ **verde** (`plan(14)`).
* `vendite/test-vw-dash-fatturazione` — creava la commessa dell'emittente B sul
  **cliente di A**. Ora usa un cliente di B, e la condizione di skip si sposta da
  «esiste un secondo emittente» a «esiste un cliente del secondo emittente», che
  è la precondizione vera. ✅ **verde** (`plan(28)`).

#### ❓ Il terzo rosso è una domanda, non una correzione

`vendite/test-guard-uscita-commessa-v1` azzerava l'emittente per raggiungere lo
scenario «tutte e tre le azioni disabilitate». Con il `NOT NULL` quello scenario
**non è più uno stato del modello**, e non per caso:

* `chiudi` disabilitato ⟺ esiste una riga `APPROVATA + NON_EMESSA`;
* `rendi_pronta` disabilitato ⟺ **non** esiste una riga `APPROVATA + NON_EMESSA + tipo_doc`;
* e `trgfn_commesse_attivita_guard_tipo_doc_emittibile` impone
  `APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`.

⇒ **`chiudi` disabilitato implica `rendi_pronta` abilitato**: sono complementari.
⚠️ Il file stesso lo aveva previsto per l'asse delle righe e aveva tappato il
buco con l'asse della testata; ora è chiuso anche quello — e la sua intestazione
già dichiarava il ramo *«raggiungibile solo da un ruolo BYPASSRLS, mai da un
operatore»*.

✅ **D-5 chiusa lo stesso giorno** (§7.12): nessuna regola nuova. ⛔ E il
candidato che avevo proposto — la competenza — **è caduto**: quel filtro è
cumulativo, sta sulle righe ed è un **parametro del giro**, quindi una commessa
di settembre guardata ad agosto è *pronta*, solo non ancora dovuta. Bloccarla
sarebbe stato, per la seconda volta in un giorno, un guard che rifiuta uno stato
che il modello ammette — stavolta per far tornare verde un test.
✅ Il file è verde (`plan(17)`) con lo stato vero asserito e lo `skip()`
dichiarato.

### 2026-08-26 · Esecuzione di L5 — e la misura che avevo sbagliato per difetto

Decisione di Tid: si procede senza aspettare il backend, *«visto che non c'è
produzione»*. ⭐ È anche l'ordine migliore: il BE riceve il database già nella
forma finale invece di inseguirlo in due giri.

**`20260826-52`** — `DROP` + `CREATE` di `vendite.fn_get_or_create_commessa`,
da **13 a 12 parametri**. Con il guard del `-40` in servizio l'override poteva
solo essere ridondante o sbagliato: *un parametro il cui unico valore ammesso è
quello che la funzione calcola da sé non è un'opzione, è una trappola per il
prossimo chiamante, che lo legge nella firma e crede di poter scegliere.*

⛔ **I `GRANT` non si sono lasciati al giro serale.** Letti sul DB prima del
taglio (`zeroerp_app`, `zeroerp_batch_fatturazione` hanno `EXECUTE` esplicito) e
rimessi **dentro il changeSet**: il loop di `90_end`/`ci_apply` su dev passa la
sera, e fra il migrate e le 21:00 il push sarebbe morto con «permesso negato» —
un sintomo che non somiglia per niente alla causa.

#### ⚠️ Due errori miei, nello stesso lotto, e vale la pena scriverli

1. ⛔ **Avevo contato DUE file pgTAP da adeguare. Sono QUINDICI**, per 21 punti
   di chiamata. Il primo `grep` guardava poche righe di contesto dopo la
   chiamata, e i parametri stanno su righe separate. Il conteggio giusto si
   ottiene **attribuendo ogni `p_emittente_soggetto_ruolo_id` alla chiamata che
   lo contiene** — nella suite quel nome compare anche in
   `fn_get_or_create_lotto`, che non è toccata.
2. ⛔ **Lo script che li ha modificati ha rotto 12 file su 13**, e li ho scoperti
   dalla **baseline**: nessuno di quei nomi era a registro come rosso noto,
   quindi il rosso era mio. La regola sbagliata era «se il valore rimosso
   contiene una `)` allora era l'ultimo argomento» — ma `(SELECT … FROM tmp)` ne
   ha una anche a metà lista, e toglieva la virgola alla riga precedente.
   Il criterio giusto è **l'assenza della virgola finale**. Ripristinati con
   `git checkout --` e rifatti.

✅ **Tutti e 15 verdi**, verificati uno per uno. ⭐ E i chiamanti usano
**parametri nominati**: nessuno shift posizionale silenzioso — è la ragione per
cui un taglio di parametro in mezzo alla firma è stato sicuro.

### 2026-08-26 · L9 — Documentazione

**Pagine `manual/` nuove** (concettuali, non auto-generate): 4 in `vendite`
(`trgfn_commesse_default_emittente`, `trgfn_commesse_guard_emittente_ba`,
`trgfn_commesse_sorgenti_guard_emittente`), 1 in `script`
(`fn_get_sorgente_emittente_sr_id`), 3 in `anagrafiche`
(`fn_guard_ba_cambio_emittente`, `fn_get_storia_emittente_ba`,
`fn_guard_ba_gestore_globale_storia`, `trgfn_efba_guard_storia_emittente`).

**Guide toccate**, e due erano buchi veri:

* `gestione-commesse.md` — nuova sezione **«Di chi è una commessa»**. ⚠️ E la
  §API documentava ancora `p_emittente_soggetto_ruolo_id`, che dopo L5 non
  esiste più: corretta.
* `sorgente-polimorfa.md` — nuovo §2a **«Le tre domande che il meccanismo sa
  fare»** (esiste? · in che stato è? · **chi lo emette?**), con la trappola del
  cliente nullable scritta per chi domani ne scriverà un altro.
* ⛔ `generazione-cliente.md` — **non nominava mai l'emittente**, e il legame
  cliente→emittente nasce esattamente lì, da un trigger, con l'emittente
  dell'operatore che sta creando. Un cliente può quindi *nascere sbagliato* e
  non c'era scritto da nessuna parte.
* `fatturazione.md` — «l'emittente della commessa non si passa: si deriva», più
  il richiamo a monte sul cliente che non cambia emittente dopo aver fatturato.

⚠️ **Un residuo del rinomino, trovato scrivendo la doc**: la pagina
`script/manual/fn_get_sorgente_billing_account_id.md` puntava a una funzione che
il `-50` aveva `DROP`pato. Rinominata e riscritta, e corretto il link entrante
dalla pagina del guard. Tutti i collegamenti delle pagine nuove verificati uno
per uno ([[feedback_no_build_doc]]: grep mirato, nessuna build).
