# Brief DB — Il livello dell'area è un tetto per i suoi permessi

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6, §7), che **attende** la consegna DB.
> **Origine:** il difetto 🔴 «Il tetto d'area dei permessi non esiste»
> (`.codex/PROJECT_CONTEXT.md` § «Aperto»), descritto in
> [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §3, con le domande aperte
> in §6. Riaperto il 2026-10-04 dal restyle del pannello permessi (§7): raggruppare per area
> azioni e oggetti suggerisce una gerarchia che oggi il modello non applica.
> **Decisioni:** di Tid, 2026-10-04 (§3).
> **Stato:** ✅ **DB chiuso**: `20261004-50 → -59` + mirror del CSV **applicati il 2026-10-04**,
> pgTAP verdi (Tid). ⏳ Resta il giro BE/FE (§9.7, poi §7). **Da leggere per primo: §9.7.**

## 1. La regola

Un permesso **specifico** (un oggetto, un'azione di processo) **può solo restringere** quello
della sua area, **mai allargarlo**. Il livello effettivo di una voce è il **più restrittivo**
fra il livello dell'area e quello che la voce avrebbe da sola.

```
oggetto:  effettivo = il più restrittivo fra  (override oggetto → area)   e   livello area
azione:   abilitata = (override azione → profilo → negata)  E  livello area ≥ minimo dell'azione
```

Vale **da qualunque parte venga** il permesso specifico: override utente o profilo (D-2). Il
super admin resta un bypass totale, **prima** del tetto, come oggi.

⭐ La regola sostituisce quella dichiarata nella guida di architettura §3, «il livello più
specifico prevale sempre su quello più generale». Non è un ritocco: è un cambio di semantica, e
per questo va **a DB**, che è la sede dei resolver. Una cascata disegnata solo a video
mostrerebbe «bloccato» mentre l'API risponde `200`.

## 2. Il difetto di oggi

| Sede | Cosa fa | Effetto |
| --- | --- | --- |
| `script.fn_check_azione_processo` | catena override → profilo → negata; l'area **non** è consultata | area Vendite `BLOCCATO` + override che abilita `genera_fatture_lotti` ⇒ l'azione **si esegue** |
| `script.fn_get_user_actions_map` | stessa catena, per tutte le azioni (alimenta `/me/` → `azioni_abilitate`) | il pulsante dell'azione **si vede** nella UI |
| `script.fn_resolve_livello_oggetto` | override oggetto **sostituisce** l'area (passo 3 → `RETURN`) | `TUTTO` su `anagrafiche.cliente` con Anagrafiche `BLOCCATO` ⇒ accesso pieno |
| `script.fn_get_user_object_permissions_map` | restituisce i soli override **grezzi** (alimenta `/me/` → `permessi_oggetto`) | il FE riscrive la catena (`auth.js` `getLivelloOggetto`: override ?? area) — §6.3 |

I guard dei verbi di scrittura (`fn_guard_azione`, `fn_guard_livello`) **chiamano** i resolver:
erediteranno il tetto senza modifiche. Va verificato, non riscritto (R7).

## 3. Le decisioni (Tid, 2026-10-04)

| # | Domanda (analisi §6) | Decisione |
| --- | --- | --- |
| D-1 | Il tetto d'area si fa? | **Sì**, a DB. |
| D-2 | Vale anche sul profilo o solo sugli override? | **Su tutto.** Il tetto è il livello **effettivo** dell'area, qualunque sia la fonte del permesso specifico. Un tetto solo sugli override sarebbe un'asimmetria del modello. |
| D-3 | Gli override sotto un'area chiusa: limite o cancellazione? | **Limite.** Restano scritti e **dormienti**; tornano validi se l'area si riapre. Il tetto si applica **in risoluzione**, non in scrittura: nessun guard rifiuta un override più permissivo della sua area, perché il livello dell'area può cambiare dopo (scadenza di un override d'area, cambio di profilo, cambio di reparto). |
| D-4 | Con l'area in `LETTURA` le azioni passano? | Lo dichiara **l'azione**: colonna nuova col livello d'area minimo, default `TUTTO` (R1). |

> 📌 *Fatto datato, non motivo* (analisi §8, 2026-09-25): sul DB di sviluppo nessuna
> configurazione cambierebbe significato. La decisione sta sul modello e varrebbe identica con
> configurazioni che cambiano significato.

## 4. Richiesta

L'enum `config.livello_accesso` è già ordinato **`TUTTO < LETTURA < BLOCCATO`** (lo usa
`fn_guard_livello`): «il più restrittivo» è `GREATEST`, e non serve una tabella di ranghi. ⚠️ Il
verso è controintuitivo: va scritto nel commento di ogni funzione che lo usa, come fa già
`fn_guard_livello`.

| # | Cosa |
| --- | --- |
| R1 | **`config.azioni_processo.livello_minimo_area`** `config.livello_accesso NOT NULL DEFAULT 'TUTTO'`, con `CHECK (livello_minimo_area <> 'BLOCCATO')` (un minimo `BLOCCATO` non vieterebbe niente). Valorizzazione dal CSV `80_data/sql/config/azioni_processo.csv`, mai con `UPDATE` (linee-guida-sql §11.2). Il team DB rilegge le 35 azioni: `LETTURA` solo per un'azione che **non scrive** (consultazione, export); nel dubbio `TUTTO`. Aggiornare `config/manual/azioni_processo.md` (§ «Catena di risoluzione azioni»). |
| R2 | **`script.fn_check_azione_processo`**: dopo il super admin (passo 2) e prima degli override, il tetto. L'area è `azioni_processo.area_id` (NOT NULL), il suo livello `fn_resolve_livello_area`; se il livello è più restrittivo di `livello_minimo_area` ⇒ `false`. Il resto della catena invariato. |
| R3 | **`script.fn_get_user_actions_map`**: lo stesso tetto, set-based (la mappa delle aree c'è già in `fn_get_user_permissions_map`, o una CTE sugli stessi BB). ⛔ La regola del confronto deve avere **una sede sola** fra R2 e R3, per esempio una funzione pura `script.fn_area_consente_azione(p_livello_area, p_livello_minimo) RETURNS boolean`: due copie del confronto divergono al primo ritocco. |
| R4 | **`script.fn_resolve_livello_oggetto`**: il risultato è `GREATEST(livello specifico, livello area)`. ⭐ **L'area è quella dell'oggetto** (`fn_area_di_oggetto`), non quella che passa il chiamante: oggi `p_area_schema_db` viene dalla view (`IsAuthenticatedZeroERP._resolve_area`, che per una view con `model_permission` può usare `area_funzionale` della view), e col tetto un'area sbagliata diventa un tetto sbagliato. Proposta: la funzione ricava l'area da sé e il parametro **si ritira** (breaking change ammesso, il BE si allinea: §6.1). Se il team DB preferisce tenerlo, lo dica nella consegna con il motivo. |
| R5 | **`script.fn_get_user_object_permissions_map`**: restituisce il livello **effettivo** (col tetto) e non l'override grezzo, per ogni oggetto con un override valido **e** per ogni oggetto di `config.area_model_overrides` (quelli la cui area non è l'`app_label`). Per gli altri oggetti il FE ripiega sull'area di `app_label`, che è esattamente la regola di `fn_area_di_oggetto`. Così `/me/` dà già la risposta, e il FE smette di ricalcolare la catena (§6.3). Aggiornare il `COMMENT` (oggi «Mappa override oggetti set-based»). |
| R6 | **La provenienza del tetto, per il pannello.** Il pannello deve poter dire «abilitata, ma **limitata dall'area**», o mostra un override che non vale niente. Serve, per un operatore: per ogni azione attiva e per ogni oggetto del catalogo `area_model_overrides` ∪ oggetti con override, il valore **senza tetto**, il valore **effettivo** e `limitato_da_area boolean`. ⭐ Forma suggerita, senza riscrivere la catena: i resolver si spezzano in un BB «specifico» (la catena di oggi, senza tetto) e nel resolver pubblico = specifico + tetto; la funzione del pannello li chiama tutti e due. La forma la sceglie il team DB; il vincolo è **una sede sola** della catena. Nome proposto: `script.fn_get_permessi_effettivi_operatore(p_auth_user_id)`. |
| R7 | **Verifica dei chiamanti**: elencare tutto ciò che chiama i quattro resolver/mappe (funzioni, guard dei verbi, trigger, job, RLS) e confermare che il tetto è il comportamento voluto per ciascuno. In particolare `fn_guard_azione` e `fn_guard_livello` (devono ereditarlo senza modifiche) e i resolver con contesto non-OPERATORE (il gate di contesto resta il passo 0, prima di tutto). |
| R8 | **pgTAP costruiti**, non sulla popolazione: un operatore fabbricato nel test con (a) area `BLOCCATO` + override azione abilitata ⇒ negata; (b) area `LETTURA` + azione con minimo `TUTTO` ⇒ negata, con minimo `LETTURA` ⇒ abilitata; (c) area `BLOCCATO` + azione abilitata **dal profilo** ⇒ negata (D-2); (d) area `BLOCCATO` + override oggetto `TUTTO` ⇒ `BLOCCATO`; (e) area `LETTURA` + override oggetto `TUTTO` ⇒ `LETTURA`; (f) override oggetto `BLOCCATO` + area `TUTTO` ⇒ `BLOCCATO` (il tetto non allarga); (g) l'override d'area che scade ⇒ l'override sottostante torna valido (D-3); (h) super admin ⇒ bypass; (i) mappe = resolver puntuali su tutti i casi sopra; (j) R6: `limitato_da_area` vero esattamente nei casi (a)-(e). Aggiornare i test esistenti che provano «il più specifico vince» (`test-permessi-funzioni-risoluzione`, `test-fn-resolve-regression-operatore`): ⛔ si riscrivono sulla regola nuova, non si cancellano. |

Nessun codice di errore nuovo: un rifiuto per tetto è `E_PERMESSO_NEGATO`, lo stesso di oggi.

## 5. Fuori perimetro

* La **validità** degli override, il gate di contesto, l'identità attiva e lo spareggio dei
  profili (`fn_get_permessi_ereditati_*`) non cambiano.
* La **coerenza interna di un profilo** (un profilo che abilita un'azione in un'area che lui
  stesso blocca) non diventa un guard: col tetto l'azione è semplicemente dormiente. Mostrarlo
  nella schermata dei profili è un lavoro FE a sé.
* La v3 dei permessi (sotto-oggetti, dormiente) non è toccata.

## 6. Lato BE, a consegna DB fatta

1. **`PermissionResolver.get_livello_oggetto`** e tutti i suoi chiamanti: se R4 ritira il
   parametro area, si allinea la firma e si prova il binding con una chiamata **reale** sul DB
   (i mock non vedono una firma cambiata). `get_area_schema_db` resta per il messaggio di
   diniego.
2. **`core/api/permissions.py`**, ramo `<chiave>_permission`: nessun cambio di logica, il tetto
   arriva da `check_azione`. Il diniego resta `AZIONE_NEGATA`; ⚠️ da valutare se il messaggio
   debba dire «l'area X non lo consente» (servirebbe il motivo dal DB, R6).
3. **`/me/`** (`me_view.py`): `permessi_oggetto` ora contiene livelli effettivi (R5). Va
   aggiornata la descrizione del campo nello schema OpenAPI e in `api.md`.
4. **Pannello**: l'endpoint dei permessi di un operatore espone R6 (`effettivo`,
   `limitato_da_area` per azione e oggetto), accanto all'ereditato di oggi. Il BE non calcola
   niente: legge.
5. **Cache dei permessi**: nessuna chiave nuova, ma il cambio di `livello_minimo_area`
   (seed) deve invalidare la cache come un cambio di profilo.
6. **Doc**: guida di architettura §3 («il più specifico prevale» → «l'area è un tetto»), guida
   permessi per l'utente, `api_amm_software.md`.

### 6.3 Lato FE, nello stesso giro

`stores/auth.js` `getLivelloOggetto` oggi è **una seconda sede della catena** (override ?? area).
Con R5 diventa: `permessiOggetto[key] ?? getLivelloArea(appLabel)`, cioè una **lettura** di ciò
che il DB ha già deciso. Il commento va riscritto di conseguenza.

## 7. L'interfaccia del pannello permessi (BE/FE, dopo §6)

> Per contesto del team DB: è la ragione per cui R6 serve. Il dettaglio diventerà un piano
> FE a parte.

### 7.1 Il problema di oggi

[`OperatorePermessiTab.vue`](../../../../frontend/src/amministrazione/components/OperatorePermessiTab.vue)
divide per **tipo**: tutte le aree, poi tutte le azioni, poi tutti gli oggetti, poi l'ambito
emittenti, ognuno col suo «Salva». La pagina è lunga e le informazioni di un'area sono sparse
in tre tabelle (analisi §4.1). Una tab per area (14 aree attive al 2026-09-25) non scala: le tab
vanno a capo o scorrono, e si perde il colpo d'occhio sulle aree.

### 7.2 La forma: master-detail con l'elenco delle aree a sinistra

```
┌─ Permessi ─┬─ Ambito emittenti ─┐
│ ☐ Solo con override        🔍 cerca…                      │
├──────────────────────────┬────────────────────────────────┤
│ Vendite       Tutto   ●2 │ VENDITE                         │
│ Acquisti      Lettura    │ Livello area  [Tutto ▾]         │
│ Magazzino     Bloccato   │   ereditato: Lettura (Commerc.) │
│ Contabilità   Lettura ●1 │ ── Oggetti ─────────────────    │
│ …                        │ Contratti     Lettura  [— ▾]    │
│ ── Trasversali ──        │ ── Azioni ──────────────────    │
│ Documenti     Lettura    │ Genera fatture  Negata [Ab. ▾]  │
│ Strumenti     Tutto      │   ⚠ limitata dall'area          │
│ Assistente    Bloccato   │                                 │
└──────────────────────────┴────────────────────────────────┘
```

* **Due tab in alto**, non di più: «Permessi» e «Ambito emittenti». L'ambito non appartiene a
  nessuna area: è l'unica cosa che merita una tab propria.
* **Colonna sinistra = la matrice delle aree.** Per ogni area: descrizione, livello
  **effettivo**, un pallino col numero di override (aree + azioni + oggetti dell'area), un
  pallino diverso se ci sono modifiche non salvate. È il colpo d'occhio di oggi, compresso.
* **Raggruppamento**: le aree di dominio prima, poi un'intestazione «Trasversali» per quelle
  senza processo proprio (documenti, strumenti, assistente, config, core, storico). ⚠️ Quali
  siano non si scrive in un elenco nel FE: o lo dice il catalogo (`aree_funzionali`, una
  colonna di raggruppamento — **richiesta da valutare col team DB**, non bloccante), o si
  rinuncia al raggruppamento e l'elenco resta piatto nell'ordine del catalogo.
* **Pannello destro = l'area selezionata**: il suo livello (ereditato + override, come oggi), i
  suoi **oggetti** e le sue **azioni**, con lo stesso BB `MatriceOverride` filtrato per area.
  Le aree senza azioni (sette al 2026-09-25) mostrano la sola sezione che hanno.
* **Filtro «Solo con override»**: nasconde nell'elenco le aree senza override e, nel dettaglio,
  le righe senza override. È il caso d'uso più frequente: «cosa ha di diverso dal profilo?».
* **Ricerca** trasversale: filtra l'elenco delle aree a quelle che contengono una voce che
  corrisponde (oggi la ricerca è per tabella).

### 7.3 Il tetto a video

* Una voce con `limitato_da_area` (R6) mostra il valore effettivo e l'etichetta «limitata
  dall'area»; l'override resta modificabile (D-3: è dormiente, non vietato).
* ⚠️ **Prima del salvataggio** l'admin cambia il livello dell'area e vorrebbe vedere subito le
  voci limitate. Proposta, **da confermare con Tid**: un'anteprima FE, dichiarata tale,
  che confronta il livello d'area a video con `livello_minimo_area` (azioni) o col livello
  dell'oggetto; dopo il salvataggio il pannello ricarica R6 e la verità torna del DB. La
  regola del confronto lato FE va in **una** funzione con uno spec che la prova contro i casi
  di R8. L'alternativa è niente anteprima: le etichette si aggiornano solo dopo il salvataggio.

### 7.4 Salvataggio

**Un solo «Salva» nel footer** (`AppDrawer` `footer="form"`, oggi `"chiudi"`), che invia **solo
le sezioni modificate** fra aree, azioni, oggetti e ambito (le fotografie per sezione di
`unisciFotografie` ci sono già). I tre endpoint di oggi restano; cambia solo chi li chiama. Una
modifica in un'area tocca spesso più di un endpoint: con i tre «Salva» di oggi l'admin dovrebbe
sapere quali premere.

### 7.5 Sedi e BB

* Componente master-detail: cercare nel catalogo BB FE prima di scriverne uno
  (`ListaColonnaPanel` è un master-detail su select, non su elenco; `useFormInline` è
  elenco-sopra/form-sotto). Se nasce, è un BB solo al secondo uso (regola del 2).
* `OperatorePermessiTab` resta il BB condiviso fra `OperatoreDrawer` e
  `OperatorePermessiDrawer`: il restyle si fa lì, una volta.
* Il collaudo in-app
  ([collaudo-in-app-ui-permessi-operatore.md](collaudo-in-app-ui-permessi-operatore.md)) va
  aggiornato alla forma nuova.

## 8. Ordine dei lavori

1. **DB**: R1-R8 su `dev/db-tid`, consegna con l'elenco dei changeSet e l'esito dei pgTAP.
2. **BE + FE §6**: allineamento firma, `/me/`, `auth.js`, endpoint del pannello; nello stesso
   giro, perché `/me/` e `auth.js` cambiano significato insieme.
3. **FE §7**: il restyle del pannello. ⭐ La parte di forma (master-detail, tab, filtro, Salva
   unico) **non dipende dal DB** e si può fare anche prima; le etichette del tetto (§7.3)
   aspettano R6.

## 9. Consegna DB (2026-10-04) — ✅ applicata, pgTAP verdi

> Numerazione da `-50`: un altro cantiere dello stesso giorno occupa `-40 … -49`.

### 9.1 ChangeSet

| # | File | Cosa |
| --- | --- | --- |
| `-50` | `00_schema/config/…-alter-azioni-processo-add-livello-minimo-area` | R1: `livello_minimo_area config.livello_accesso NOT NULL DEFAULT 'TUTTO'`, `chk_azioni_processo_livello_minimo_area` (≠ `BLOCCATO`) |
| CSV | `80_data/sql/config/azioni_processo.csv` + mirror `80_data/20260228-18` | colonna in coda, `TUTTO` su **tutte** le 39 righe: rilette una per una, nessuna è di sola consultazione (anche `code_manage` agisce su code altrui). Mirror: `- column: livello_minimo_area` |
| `-51` | `script.fn_area_consente_azione(livello_area, minimo)` | R3: la regola del tetto per le azioni, **sede unica** (`livello <= minimo`, NULL = no). Pura, IMMUTABLE |
| `-52` | `script.fn_livello_con_tetto_area(specifico, area)` | R4: la regola del tetto per gli oggetti, sede unica (`GREATEST`, specifico NULL → area, area NULL → BLOCCATO) |
| `-53` | `script.fn_get_permessi_effettivi_azioni(utente, codename DEFAULT NULL)` | R2/R3/R6: **la catena delle azioni scritta una volta**, col tetto. Colonne: `abilitata_specifica`, `livello_area`, `livello_minimo_area`, `abilitata`, `limitata_da_area` |
| `-54` | `script.fn_get_permessi_effettivi_oggetti(utente, app DEFAULT NULL, model DEFAULT NULL)` | R4/R5/R6: **la catena degli oggetti scritta una volta**. Colonne: `area_schema_db`, `livello_override`, `livello_area`, `livello_specifico`, `livello`, `limitato_da_area` |
| `-55` | `fn_check_azione_processo` | legge `-53` (una riga) |
| `-56` | `fn_get_user_actions_map` | aggrega `-53` (azioni attive) |
| `-57` | `fn_resolve_livello_oggetto` | legge `-54`; l'area è quella **dell'oggetto** |
| `-58` | `fn_get_user_object_permissions_map` | aggrega `-54`: livello **effettivo** per ogni oggetto del catalogo |
| `-59` | `dbops.fn_pgtap_concedi_azione` (fixture) | concedere un'azione ne apre anche l'area **al minimo** (vedi §9.4) |

Rollback di `-55 → -59`: il corpo vivo preso dalla doc auto-gen.

### 9.2 Le scelte, e dove si scostano dalla richiesta

* ⭐ **R6 sono DUE funzioni, non una** (`fn_get_permessi_effettivi_azioni` e `…_oggetti`,
  gemelle di `fn_get_permessi_ereditati_aree/_azioni`), invece di
  `fn_get_permessi_effettivi_operatore`. Non è un'aggiunta per il pannello: sono **la sede
  della catena**. Prima la catena delle azioni stava scritta due volte (resolver puntuale e
  mappa); il pannello ne avrebbe voluto una terza. Ora resolver, mappe e pannello leggono la
  stessa funzione: le copie sono ritirate in questo giro (regola del 2). Il presidio è il
  test 5 di `test-permessi-tetto-area-v1`.
  Il pannello (§6.4) chiama `SELECT … FROM script.fn_get_permessi_effettivi_azioni(%s)` e
  `…_oggetti(%s)`, come fa già con gli ereditati.
* ⚠️ **R4: il parametro `p_area_schema_db` NON si ritira.** La funzione ricava l'area da sé
  (`fn_area_di_oggetto`) e il parametro non si legge più, ma resta in firma: il backend passa i
  parametri per posizione, e una firma accorciata rompe ogni punto di chiamata e i pgTAP,
  mentre tenerla non ne tocca nessuno (regola di Tid del 2026-10-04 sulle firme). Per il
  backend non cambia niente: oggi gli passa `get_area_schema_db(app_label, model_name)`, che
  è già la regola di `fn_area_di_oggetto`. ❓ **Il ritiro lo decide Tid** (§9.6). Quindi
  §6.1 non serve più come allineamento di firma.
* **R5: la mappa copre tutto il catalogo** `area_model_overrides`, non «override ∪ catalogo»:
  un override esiste solo per un oggetto a catalogo (FK composita
  `fk_user_override_oggetti_catalogo`), quindi l'unione è il catalogo. Riservati compresi
  (valgono la loro area).
* **R5 prende anche il gate.** La mappa vecchia dava gli override grezzi anche fuori dalla veste
  OPERATORE e senza identità; ora, come gli altri resolver, lì è tutto `BLOCCATO`.
* **Due casi limite che cambiano**, tutti e due chiamate rotte che oggi nessuno fa:
  `fn_check_azione_processo` con codename NULL → `false` anche per il super admin (prima
  `true`; `fn_guard_azione` la ferma comunque prima); `fn_resolve_livello_oggetto` con oggetto
  NULL → `BLOCCATO` (prima: il livello dell'area passata).
* Il codename fuori catalogo resta com'era: negato, **abilitato per il super admin**.

### 9.3 R7 — chi chiama i quattro resolver (letto da `pg_proc` su dbdev e da `grep`)

| Chiamante | Cosa eredita | Voluto? |
| --- | --- | --- |
| `script.fn_guard_azione` → i verbi (`fn_posta_*`, ecc.) | il tetto sulle azioni, senza modifiche | ✅ (test 11 del pgTAP nuovo) |
| `script.fn_guard_livello` → `config.fn_pannello_scrivi` | il tetto sugli oggetti, senza modifiche | ✅ (test 18) |
| `script.fn_get_user_profile` (`/me/`) | `azioni_abilitate` col tetto, `permessi_oggetto` effettivi | ✅ è R5 |
| `ui.fn_resolve_dashboard_config` | un widget legato a un'azione fermata dall'area sparisce | ✅ |
| BE `PermissionResolver` (`check_azione`, `get_livello_oggetto`), `permissions.py`, viste di magazzino e pagamenti, `dashboard_repository`, tool AI | il tetto, senza modifiche | ✅ |
| policy RLS, viste, trigger, job | nessuno li chiama | — |

Il gate di contesto resta il passo 0, prima di tutto (test 25-26).

### 9.4 La fixture dei pgTAP (`-59`), il pezzo che non si vedeva

37 pgTAP (magazzino e vendite) concedono un'azione all'operatore di
`fn_pgtap_crea_emittente_operatore`, che ha **tutte** le aree `BLOCCATO`. Col tetto quell'override
non basterebbe più, e i 37 file cadrebbero sul permesso invece che sul loro soggetto.
`fn_pgtap_concedi_azione` ora apre l'area dell'azione **al minimo** (non di più), con un override
d'area come lo scrive il pannello; se il test ha già chiuso l'area con un override suo, la fixture
non lo scavalca: RAISE.

### 9.5 Prova (2026-10-04, `zeroerp_ci`, da owner, SQL estratto con `updateSQL` offline)

* Tutti i changeSet + il mirror del CSV (upsert su **tutte** le 39 righe) in una transazione
  ritirata: verdi. `plpgsql_check`: zero errori sulle nove funzioni; un solo avviso, voluto
  (`p_area_schema_db` non usato).
* pgTAP con l'SQL in testa: `test-permessi-tetto-area-v1` **26/26** (nuovo);
  `test-permessi-funzioni-risoluzione` 34/34, `test-fn-guard-azione-v1` 9/9,
  `test-fn-guard-livello-v1` 12/12, `test-fn-resolve-regression-operatore` 11/11,
  `test-fn-get-permessi-ereditati-v1` 27/27 (i cinque riscritti); `dbops/test-riferimenti-morti-v1`
  9/9, `script/test-rubinetto-primo-motivo-v1` 7/7; profilo utente, dashboard e catalogo oggetti
  verdi.
* **Mutazione**: il pgTAP nuovo con i resolver VECCHI (senza `-55 → -58`) dà 14 rossi, cioè i
  casi del tetto. Prova qualcosa.
* I 37 pgTAP che usano `fn_pgtap_concedi_azione`: **stessi esiti con e senza** le modifiche,
  file per file e asserzione per asserzione. I rossi che hanno (24 file) sono rossi da owner
  che c'erano già (privilegi, scope emittente: la prova non gira come app).
* ⚠️ Non provato qui: la corsa **come app** e su dbdev (lì la DDL vuole `titodb`), e
  `test-fn-resolve-regression-operatore` gira a vuoto su `zeroerp_ci`, che non ha l'utente
  `tid`. È la corsa di Tid dopo l'apply.

#### pgTAP riscritti (⛔ riscritti sulla regola nuova, non cancellati)

| File | Cosa cambia |
| --- | --- |
| `test-permessi-funzioni-risoluzione` | 8 e 12: l'area si apre (12: quella **dell'azione**); 31-34: la mappa dà il livello effettivo, non `{}` |
| `test-fn-guard-azione-v1` | 7-9: vendite aperta; 9 non è più verde per coincidenza (oggetto a catalogo, area sbagliata nel quarto parametro → TUTTO) |
| `test-fn-guard-livello-v1` | l'override d'area di magazzino si scrive dopo il test 5, non al test 11 |
| `test-fn-resolve-regression-operatore` | l'area dell'azione si costruisce (prima era la seconda area per id, per caso) |
| `test-fn-get-permessi-ereditati-v1` | test 4 (sede unica) su cinque funzioni; scarti delle azioni = ereditato **e** tetto; test 13 legge lo specifico |

### 9.5-bis Apply e corsa (2026-10-04 sera)

* Applicati `20261004-50 → -59` e il mirror `80_data/20260228-18`; su `zeroerp_ci` il
  `databasechangelog` li registra alle 20:09.
* Corsa pgTAP di Tid: **verde**. Copre quello che la prova pre-apply non poteva coprire (§9.5):
  il percorso come app e la CI ricostruita da zero.

### 9.6 Per Tid

1. ~~Apply e corsa pgTAP~~ — ✅ fatti il 2026-10-04 (§9.5-bis).
2. ❓ **Ritiro di `p_area_schema_db`** da `fn_resolve_livello_oggetto` (§9.2): tenerlo costa
   un parametro morto, ritirarlo costa un giro BE + pgTAP. Raccomandazione: tenerlo finché un
   cantiere non tocca comunque quella firma.
3. Raggruppamento «Trasversali» delle aree (§7.2): **non fatto**, nessuna colonna nuova su
   `aree_funzionali`. Resta una richiesta da valutare, non bloccante.

### 9.7 Al BE/FE — ⏳ si può partire (aggiorna §6)

* §6.1 **non serve**: firma invariata.
* §6.3 `/me/` → `permessi_oggetto`: contiene **tutti** gli oggetti del catalogo col livello
  effettivo (non più i soli override). `auth.js` `getLivelloOggetto` diventa
  `permessiOggetto[key] ?? getLivelloArea(appLabel)`, nello stesso giro.
* §6.4 pannello: leggere `fn_get_permessi_effettivi_azioni(uid)` e `…_oggetti(uid)`
  (`abilitata`/`livello`, `limitata_da_area`/`limitato_da_area`, `livello_area`). Anche
  l'anteprima FE di §7.3, se Tid la conferma, deve dare gli stessi esiti delle due regole
  (`fn_area_consente_azione`, `fn_livello_con_tetto_area`): lo spec FE si costruisce sui casi
  della tabella di §9.5 (test 3-4 del pgTAP).
* §6.5 cache: anche il cambio di `livello_minimo_area` (seed).
* ⚠️ **Test Django con DB vero** che danno un'azione con il solo override e poi la eseguono
  (opt-in `ZEROERP_TEST_DB_E2E`): col tetto vanno rossi se non aprono anche l'area. Da censire
  lato BE (`grep user_override_azioni apps/*/tests`); i file toccati dal `grep` di oggi
  (`test_permissions_audit`, `test_pannello_verbo_db`, `test_override_oggetti_catalogo_db`)
  provano scritture, non risoluzioni.
