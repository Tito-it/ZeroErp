# Brief DB — Il livello dell'area è un tetto per i suoi permessi

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6, §7), che **attende** la consegna DB.
> **Origine:** il difetto 🔴 «Il tetto d'area dei permessi non esiste»
> (`.codex/PROJECT_CONTEXT.md` § «Aperto»), descritto in
> [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §3, con le domande aperte
> in §6. Riaperto il 2026-10-04 dal restyle del pannello permessi (§7): raggruppare per area
> azioni e oggetti suggerisce una gerarchia che oggi il modello non applica.
> **Decisioni:** di Tid, 2026-10-04 (§3).
> **Stato:** 🟡 da fare (DB).

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
