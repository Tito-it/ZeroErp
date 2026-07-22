# Brief DB — Dashboard home: rimuovere il widget «Benvenuto»

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-22
> · **Owner**: Tid · **Priorità**: 🟢 BASSA
> **Stato**: ✅ **CHIUSO (2026-07-22)** — applicato dal team DB via
> disattivazione, verificato end-to-end lato BE. Esito in §7.
> **Origine**: validazione in-app di Tid della dashboard home
> ([brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md)).

## 1. Cosa serve (NON come)

Il widget `home.benvenuto` **non deve più comparire** fra le card della home.

È una card che mostra soltanto un'etichetta («Benvenuto in ZeroERP»): nessun
numero, nessun deep-link, nessuna azione. Per ogni utente che ha dei permessi —
cioè la quasi totalità — occupa uno slot della griglia senza dire nulla.

Il risultato atteso è che il catalogo della dashboard `home` contenga i soli 3
widget KPI, e che chi aveva la card in preferenza smetta di vederla.

## 2. Perché era stato seedato, e perché toglierlo è comunque corretto

Non era decorativo: era **l'unico widget non-gated** del catalogo
(`area_id`/`azione_id` NULL), inserito per garantire l'invariante «mai una home
vuota» del [brief DB originale](brief-db-dashboard-home.md) §3.bis. Gli altri
tre sono gated su area vendite, quindi senza di lui un utente senza quell'area
risolve una lista di widget vuota.

Quella garanzia però riguardava il **non mostrare un vuoto muto**, e una
card-riempitivo la soddisfa peggio di un empty-state esplicito. Il FE ora
distingue i due casi e dice la verità in entrambi:

| Situazione | Messaggio mostrato |
| --- | --- |
| Ci sono widget disponibili ma nessuno attivo | «Nessuna card attiva. Usa l'ingranaggio per sceglierle.» |
| Nessun widget disponibile per il profilo | «Nessuna card disponibile per il tuo profilo.» |

Il secondo caso è esattamente quello che il widget benvenuto mascherava. Ora è
gestito onestamente, senza far credere all'utente di avere qualcosa da
configurare quando non ha nulla da attivare.

**Conseguenza accettata e voluta**: dopo questa rimozione, un utente senza area
vendite vede la sezione KPI con l'empty-state del secondo caso invece di una
card. È il comportamento corretto — l'invariante §3.bis resta soddisfatto nella
sostanza (nessun vuoto muto), non più nella forma (un widget di riempimento).

## 3. Vincoli sul risultato

- **Le preferenze utente esistenti non devono rompersi.** Chi ha già salvato una
  preferenza che include `home.benvenuto` non deve ricevere errori: la funzione
  di risoluzione fa JOIN sul catalogo filtrando `attivo = TRUE`, quindi un
  widget disattivato semplicemente sparisce dalla configurazione risolta. Da
  confermare che valga anche per la via scelta (disattivazione vs eliminazione).
- **Gli altri 3 widget non devono essere toccati**, né nel contenuto né
  nell'ordine relativo.
- **`dimensione_max` resta 8**: non va ridotto per compensare una card in meno.

## 4. Nota sulla via da scegliere (è decisione DB, non BE)

Due strade, entrambe legittime, con implicazioni diverse:

- **Disattivare** (`ui.widget.attivo = FALSE`): reversibile, conserva la storia,
  e la fn lo esclude già da sola. Lascia però una riga nel catalogo e nei preset.
- **Rimuovere dal seed** (widget + composizione `dashboard_widget` + riga nel
  preset di sistema e in quello di ruolo): più pulito, ma il preset di **sistema**
  resterebbe senza widget — va verificato che un preset vuoto sia un caso
  ammesso dalla cascata, o che convenga eliminarlo del tutto.

Il secondo punto è la ragione per cui non indico io la via: tocca la coerenza
della cascata di preset, che è territorio DB.

## 5. Cosa NON serve fare lato BE/FE

Nulla. Il FE non nomina mai `home.benvenuto`: legge il catalogo risolto dalla fn
e rende ciò che riceve. Le chiavi i18n `home.widget_benvenuto` (it/en) restano in
repo inerti — si possono ripulire in una passata successiva, non urgono e non
rompono nulla.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Scelta della via (§4) e disattivazione di `home.benvenuto` | ✅ 2026-07-22 |
| 2 | Verifica: utente con permessi vede 3 card; utente senza area vendite vede l'empty-state | ✅ (utenti 9/6/1 e 8/5) |
| 3 | Verifica: preferenza utente che includeva il widget non produce errori | ✅ |
| 4 | Apply dev + rigen doc auto-gen | ✅ |
| 5 | Validazione UI di Tid | ✅ 2026-07-22 |

## 7. Esito (2026-07-22) — CHIUSO

### 7.1 Via scelta: disattivazione

Il team DB ha scelto la **prima** delle due strade di §4:
`ui.widget.attivo = FALSE` su `home.benvenuto`. La riga resta nel catalogo e nel
preset; è la funzione di risoluzione a escluderla con il suo filtro
`attivo = TRUE`.

Stato reale del catalogo dopo l'apply:

| `ui.widget.codice` | `attivo` |
| --- | --- |
| `home.situazione_aperta` | `true` |
| `home.competenza` | `true` |
| `home.backlog` | `true` |
| `home.benvenuto` | **`false`** |

È la scelta reversibile, e ha una conseguenza pratica utile: **le chiavi i18n
`home.widget_benvenuto` (it/en) vanno lasciate in repo**, non ripulite. Se il
widget venisse riattivato servirebbero di nuovo. §5 le dava per eliminabili "in
una passata successiva": con la disattivazione, tenerle è la scelta corretta e
non un residuo.

### 7.2 Divergenza dal brief sul preset — da sapere

Il seed reale **non** è quello che il brief BE/FE §5 proponeva. Non esistono due
preset (sistema col solo benvenuto + ruolo vendite con tutti e 4): esiste un
**unico preset `home_default` di ambito `sistema`** che contiene tutti e 4 i
widget.

Funziona ugualmente, e anzi in modo più semplice: la selezione per utente non
avviene per preset di ruolo ma **per filtro permessi sul singolo widget**, che è
il meccanismo §3b. Chi ha area vendite vede i 3 KPI, chi non ce l'ha vede zero
widget e riceve l'empty-state.

Va però saputo da chi tocca questa dashboard in futuro: **non c'è un preset di
ruolo su cui intervenire**. Differenziare le card per veste richiederebbe di
crearlo, non di modificarne uno esistente.

### 7.3 Verifica eseguita

Tutti i vincoli §3 e gli step §6 verificati contro il DB reale:

| # | Verifica | Esito |
| --- | --- | --- |
| 1 | `home.benvenuto` non compare più nella config risolta | ✅ |
| 2 | Gli altri 3 widget intatti: codici, ordini (20/30/40), `contatore_key` | ✅ |
| 3 | `dimensione_max` resta 8 | ✅ |
| 4 | **Preferenza utente che referenzia il widget rimosso** | ✅ risolve senza errori: il widget sparisce, gli altri rientrano come "nuovi" nascosti |
| 5 | Utente **con** area vendite → 3 card | ✅ utenti 9, 6, 1 |
| 6 | Utente **senza** area vendite → 0 widget, empty-state onesto | ✅ utenti 8, 5 |

Il punto 6 è quello che contava: è il caso che la card benvenuto mascherava, ora
esercitato su utenti reali e non solo per design. Il FE lo rende con
«Nessuna card disponibile per il tuo profilo» (`home.kpi_empty_nessuna_disponibile`),
non con l'invito fuorviante a configurare qualcosa che non c'è.

Il record di preferenza creato durante la verifica è stato rimosso.

## 8. Riferimenti

- Brief BE/FE: [brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md)
- Invariante «mai vuota»: [brief-db-dashboard-home.md](brief-db-dashboard-home.md) §3.bis
- Seed da correggere: `db/changelog/migrations_v2/80_data/changelog/20260722-02..05`
- Empty-state FE: `frontend/src/core/views/HomeView.vue`,
  chiavi `home.kpi_empty_hint` / `home.kpi_empty_nessuna_disponibile`
