# Analisi — La UI dei permessi di un operatore

> **Tipo**: analisi · **Data**: 2026-09-05 · **Owner**: Tid ·
> **Stato**: ✅ **CHIUSA il 2026-10-06** — collaudi a video verdi (Tid):
> [pannello](collaudo-in-app-ui-permessi-operatore.md) e
> [ereditato/veste](collaudo-in-app-permessi-ereditati-veste-operatore.md). Perimetro
> deciso il 2026-09-05 (§7), codice fatto lo stesso giorno. Il tetto d'area, che qui
> sotto risulta «aperto», è stato poi deciso e fatto in
> [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) (2026-10-04), e
> collaudato con questo pannello.
>
> 📍 *Il riquadro che segue è la fotografia al 2026-09-25, lasciata com'era.*
>
> 📍 **Dove siamo (2026-09-25)**
>
> - ✅ **Codice**: endpoint `permessi-ereditati`, BB `MatriceOverride.vue`, tab
>   convertito — vedi lo stato nel [piano](piano-be-fe-ui-permessi-operatore.md).
> - ⏳ **Collaudo a video**: copione in
>   [collaudo-in-app-ui-permessi-operatore.md](collaudo-in-app-ui-permessi-operatore.md),
>   da eseguire.
> - ✅ **pgTAP «ereditato = resolver»** (2026-09-25):
>   [brief-db-pgtap-permessi-ereditati.md](brief-db-pgtap-permessi-ereditati.md).
>   L'ereditato ora sta a DB, i resolver lo chiamano e il backend lo legge;
>   applicato, con la ricaduta BE fatta. Il brief ha corretto anche un difetto:
>   i resolver da operatore contavano i profili delle **altre vesti**
>   dell'utente (D-1, D-2, D-3).
> - ✅ *(2026-10-31) Chiuso il 2026-10-04: [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md).*
>   🔴 **Tetto d'area**: aperto, senza decisione; ora è registrato in
>   `.codex/PROJECT_CONTEXT.md` § «Aperto», così sopravvive alla chiusura di
>   questo documento.
> - 📌 Riconteggio del catalogo al 2026-09-25 in §8.
>
> ⇒ Collaudo verde + pgTAP applicato → analisi e piano vanno in `work-done/`.
>
> ✅ **Decisioni prese**: *nessun cambio di funzionalità* — il tetto d'area (§3)
> **non si fa** e resta segnalato come difetto a sé; la UI **resta nel drawer**;
> `DataTable` con tutte le righe e **niente paginazione**; **estrazione del BB
> approvata**; e le righe mostrano il **valore ereditato** dal profilo.
> Quindi è una **ristrutturazione grafica**, e §7 dice come.
>
> ➡️ **Il piano operativo è
> [piano-be-fe-ui-permessi-operatore.md](piano-be-fe-ui-permessi-operatore.md)**
> — componente, endpoint, store, test e ordine dei passi. ⛔ Le decisioni non si
> riaprono lì: si traducono.
>
> ✅ *(2026-10-31) Il tetto d'area è chiuso dal 2026-10-04:
> [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md). La frase
> qui sotto è la storia di quando era aperto.*
>
> 🔴 **Resta aperto e NON è di questo cantiere**: il tetto d'area (§3) è un
> difetto di modello vero — un'area bloccata non blocca le sue azioni di
> processo — e aspetta una decisione a sé.
>
> **La domanda.** Oggi i permessi di un utente si gestiscono in un drawer con
> tre tabelle di *override*: per aggiungerne uno si preme «Aggiungi override» e
> compare una riga vuota con due tendine. L'idea è sostituirle con **tre liste
> che mostrano tutte le voci possibili**, ognuna col suo livello, e far sì che
> **un'area bloccata blocchi tutto ciò che sta sotto**.
>
> ⭐ **La direzione è giusta, e la seconda metà non è una modifica di UI.** Il
> «blocco a cascata» oggi **non esiste nel modello**, ed è dichiarato al
> contrario nella guida di architettura: vince il livello più specifico, non il
> più restrittivo. Chi disegnasse la cascata solo a video costruirebbe una
> schermata che dice «bloccato» mentre l'API risponde `200`.

---

## 1 · Cosa c'è oggi

[`OperatorePermessiTab.vue`](../../../../frontend/src/amministrazione/components/OperatorePermessiTab.vue)
— 428 righe — porta tre `DataTable` affiancate (aree, azioni, oggetti). Ogni
riga è un **override**: una tendina per scegliere l'entità, una per il livello,
un cestino. «Aggiungi override» spinge in lista una riga vuota.

⛔ **Il problema di leggibilità non è il pulsante: è che la tabella mostra le
eccezioni e non lo stato.** Un utente senza override ha **tre tabelle vuote** —
e da lì non si capisce cosa quell'utente possa fare. Il livello che conta nasce
da una catena di cinque passi, e la schermata ne mostra **uno**.

Le dimensioni reali, misurate il 2026-09-05:

| | |
| --- | --- |
| Aree funzionali attive | **13** |
| Azioni di processo | **34** (19 Vendite, 8 Pratiche, 2+2+2+1 sparse, **7 aree a zero**) |
| Model overridabili | **12** |
| Profili di accesso | 8 |
| Utenti con almeno un override, oggi | 3 |

⇒ **59 righe in tutto.** L'idea di mostrarle tutte è praticabile: non serve
paginare niente, e nessuna delle tre liste diventa ingestibile.

---

## 2 · Il modello, per quello che fa davvero

**Aree e oggetti** — `script.fn_resolve_livello_area` /
`fn_resolve_livello_oggetto`:

```
override sull'OGGETTO → override sull'AREA → profilo del reparto → BLOCCATO
```

**Azioni di processo** — `script.fn_check_azione_processo`:

```
override sull'AZIONE → profilo del reparto → negata
```

✅ **I default sono già restrittivi**, quindi metà della richiesta è già vera:
un utente senza niente è bloccato ovunque, e le azioni non configurate sono
negate.

⚠️ **Con un'eccezione che la UI deve dire, o mente**: fra l'override e il
default c'è il **profilo del reparto**. Un utente nuovo che entra in un reparto
con un profilo **non parte bloccato affatto** — parte con quello che il profilo
gli dà. Oggi la schermata non lo mostra: fa vedere tre tabelle vuote, che l'admin
legge come «non può fare niente».

---

## 3 · 🔴 Le due cose che il modello NON fa

✅ *Nota del 2026-10-31: chiuso il 2026-10-04 da [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) — un permesso specifico ora può solo restringere quello della sua area. La frase qui sotto è la storia di quando era aperto.*

### a) Un'area bloccata **non** blocca le sue azioni di processo

[`permissions.py`](../../../backend/apps/core/api/permissions.py) — quando una
view dichiara un'azione (`<action>_permission`), il controllo **ritorna subito**:

```python
result = PermissionResolver.check_azione(user, action_perm, cache=cache)
...
return result          # ⛔ il livello d'area non viene mai consultato
```

⇒ Un operatore con l'area **Vendite BLOCCATA** e un override che abilita
`genera_fatture_lotti` **esegue l'azione**. Non è un caso di scuola: è il
percorso normale di ogni azione di processo.

### b) Un oggetto può essere **più permissivo** della sua area

`fn_resolve_livello_oggetto` **sostituisce** il livello d'area, non lo limita.
Un override `TUTTO` su `anagrafiche.cliente` vale anche se l'area Anagrafiche è
`BLOCCATA`.

⭐ **E questo è dichiarato, non dimenticato.** La guida di architettura §3 dice:
*«il livello più specifico prevale sempre su quello più generale»*.

⇒ **Quindi la richiesta è un cambio di semantica**: da *«il più specifico
vince»* a *«l'area è un tetto»*. È una decisione di modello, non un ritocco di
interfaccia, e va fatta **nel backend e nel database** — mai solo a video.

> 📌 *Fatto datato (2026-09-05, non è il motivo della scelta)*: oggi **nessuna
> configurazione cambierebbe significato**. Zero azioni abilitate su un'area
> bloccata; i 4 override oggetti esistenti sono tutti ≤ al livello della loro
> area. La finestra per cambiare la regola è aperta e costa niente.

---

## 4 · Considerazioni pratiche sulla UI

**4.1 · Una lista sola per area, non tre liste scollegate.** Azioni e oggetti
**appartengono** a un'area (`azioni_processo.area_id`,
`area_model_overrides.area_id`). Tre liste piatte affiancate buttano via
esattamente la relazione che si vuole rendere visibile. La forma che dice la
cosa giusta è **13 sezioni, una per area**, ognuna con dentro le sue azioni e i
suoi oggetti. Le 7 aree senza azioni restano corte da sole.

**4.2 · Ogni riga mostra il livello EFFETTIVO e da dove viene.** È il pezzo che
manca oggi e che fa la leggibilità:

```
Vendite                                   [Bloccato][Lettura][Tutto]   ← da: profilo «Back-office»
  ├ azioni (19)
  │   Genera fatture di lotto             ● negata                     ← da: default
  │   Annulla lotto                       ● abilitata                  ← da: override utente ✎
  └ oggetti (3)
      vendite.preventivo                  ● Tutto                      ← da: override utente ✎
      vendite.fattura                      ● Lettura                   ← da: area
```

⛔ Senza la **provenienza** l'admin non può distinguere *«bloccato perché
qualcuno l'ha deciso»* da *«bloccato perché nessuno ha detto niente»* — che è
la domanda vera quando si apre questa schermata.

**4.3 · L'override si imposta sulla riga, non con «Aggiungi».** Tre pulsanti
segmentati (Bloccato / Lettura / Tutto) sulla riga, più un **«torna al
profilo»** che *cancella* l'override invece di scriverne uno uguale. Sono due
cose diverse e oggi non si possono nemmeno esprimere: cancellare la riga è
l'unico modo, e non si vede cosa succede dopo.

**4.4 · Il tetto d'area si vede.** Se l'area è bloccata, le sue righe figlie
vanno in grigio con l'etichetta «bloccato dall'area», e i pulsanti si
disabilitano. ⚠️ Solo **se e quando** il backend applica davvero il tetto (§3):
prima di allora sarebbe una bugia gentile.

**4.5 · Il drawer è il vincolo peggiore.** 59 righe con tre colonne non stanno
in un drawer stretto. Esiste già
`PermessiRiepilogoView` (matrice operatori × aree, sola lettura; ritirata il
2026-10-06, ora è «Mostra permessi» della lista operatori): la strada naturale è una **pagina
intera** per l'editing, tenendo il drawer per la consultazione rapida.
`getLivelloSeverity` / `getLivelloLabel` in `amministrazione/constants` sono già
i mattoni dei badge.

---

## 5 · Cosa manca lato backend

`GET /users/<id>/permessi-effettivi/` oggi restituisce, per ogni area: il
`livello` effettivo, `modelli[]` con il livello effettivo per oggetto, e
`has_profilo_reparto`. È già la sorgente giusta — ma le manca il necessario:

1. ⛔ **le azioni di processo non ci sono.** `azioni_consentite` è la mappa
   livello → verbi CRUD, non l'elenco delle 34 azioni con la loro abilitazione;
2. ⛔ **la provenienza non c'è per nessuna riga.** Serve un campo `origine` con
   vocabolario chiuso — `OVERRIDE_UTENTE | PROFILO | DEFAULT` — su area, azione
   e oggetto. È l'informazione di §4.2, e nessuna delle tre catene la espone
   oggi: le funzioni SQL ritornano il valore e perdono il passo che l'ha deciso.

⚠️ Il punto 2 tocca le funzioni di risoluzione, quindi è **lavoro DB**, non
solo BE: o le funzioni restituiscono anche l'origine, o il backend rifà la
catena per conto suo — che è una seconda implementazione della regola più
delicata del sistema.

---

## 6 · Le decisioni, prima di disegnare

1. **Il tetto d'area si fa?** È un cambio di semantica (§3), tocca DB + BE, e
   oggi non romperebbe nessuna configurazione esistente.
2. **Se sì: il tetto vale anche sul profilo, o solo sugli override?** Cioè un
   profilo che dà `TUTTO` su un'azione di un'area che l'override utente ha
   bloccato — chi vince?
3. **Il tetto è un limite o una cancellazione?** Se l'area passa a BLOCCATA, gli
   override sottostanti **restano scritti e dormienti** (e tornano vivi se
   l'area si riapre) oppure vengono cancellati? La prima è più gentile, la
   seconda più onesta.
4. **Dove vive la UI**: pagina intera con il drawer in sola lettura, o tutto nel
   drawer allargato?

⇒ La 1 e la 2 vanno decise **prima** di scrivere una riga: cambiano cosa la UI
deve mostrare, non come.


---

## 7 · Il perimetro deciso — ristrutturazione grafica, dentro il drawer

> **Decisione di Tid (2026-09-05)**: non si tocca la funzionalità, si resta nel
> drawer. Restano quindi fuori il tetto d'area e la provenienza dal backend
> (§3 e §5): il primo è un difetto segnalato, il secondo un'estensione futura.

### 7.1 · ⭐ Il pattern è già deciso, e questa schermata non è mai stata convertita

La forma «tutte le voci possibili, ognuna col suo stato» non è un'idea nuova nel
progetto: è il **pattern slot/override**, adottato il 2026-04-08 sul tab
Utilities degli emittenti fiscali dopo che il CRUD libero aveva prodotto quattro
difetti ricorrenti. Le sue due regole dicono, alla lettera, cosa c'è che non va
qui:

- ❌ *combo «scegli voce» + bottone «Aggiungi»*;
- ❌ *mostrare solo le righe già override — l'operatore non vede quelle ammesse
  e non configurate*.

⇒ Il drawer permessi fa **entrambe le cose**. La ristrutturazione non introduce
un pattern: ne applica uno che questa schermata si era persa.

### 7.2 · 🔴 Perché la paginazione qui è pericolosa, non solo inutile

Il `PUT` degli override **sostituisce l'intera collezione**:

```sql
DELETE FROM config.user_override_aree WHERE auth_user_id = %s;
-- poi reinserisce SOLO gli item ricevuti
```

⇒ Con una lista **lazy server-side** il caller ha in mano una pagina sola.
Salvare dalla pagina 2 manderebbe solo quelle righe, e il `DELETE` porterebbe
via **gli override della pagina 1** — senza nessun errore, perché è
esattamente ciò che il contratto chiede di fare.

Non è un rischio teorico: è il comportamento normale del salvataggio combinato
col comportamento normale di una lista paginata. Con la lista **non paginata**
quella porta è chiusa per costruzione, non per attenzione di chi scrive.

### 7.3 · E la popolazione è limitata PER MODELLO, che è il caso ammesso

`ListaConfigurabile` ha già la prop `paginata: false`, e il suo commento
delimita quando si usa:

> ⛔ NON è un'opzione di comodo per saltare la paginazione. Si mette `false`
> quando la popolazione è limitata **per modello** (una riga per voce di
> catalogo…), non quando «oggi sono poche».

⇒ È esattamente il nostro caso: una riga per **area funzionale**, una per
**azione di processo**, una per **model overridabile**. Sono cataloghi, non dati
che crescono con l'uso. E il guard `troncamentoSospetto` del BB — che rifiuta di
disegnare se `rows.length ≠ total` — resta acceso a sorvegliare l'assunzione.

📌 A 10 righe per pagina sarebbero **2 / 4 / 2 pagine** per nascondere 59 righe
in tutto: si paga un click e si perde la vista d'insieme, che era l'obiettivo.

### 7.4 · Lista standard o DataTable semplice?

| | `ListaConfigurabile` (`paginata: false`) | `DataTable` come oggi, con tutte le righe |
| --- | --- | --- |
| Coerenza col resto dell'app | ✅ | ⚠️ ma è un pannello di configurazione, non una lista di ricerca |
| Colonne configurabili + export | ✅ | ❌ |
| Costo | **3 liste da seminare a catalogo** (`ui.lista_*` + colonne con `campo_sorgente`) — lavoro DB | zero |
| Spazio verticale nel drawer | toolbar + paginator + header | tutto alle righe |

⇒ In un drawer, dove lo spazio verticale è la risorsa scarsa, la macchina della
lista standard costa più di quanto renda: nessuno esporterà l'elenco di 13 aree.
**Raccomandazione: `DataTable` con tutte le righe**, più un campo di ricerca
locale sulle azioni (34 voci, 19 delle quali in Vendite) — una riga di codice,
e risolve l'unica lista dove scorrere è scomodo.

### 7.5 · ⛔ La trappola che trasformerebbe la grafica in un cambio funzionale

Mostrando **tutte** le righe, ognuna avrà un livello a video anche quando
override non ne ha. Il salvataggio deve mandare **solo le righe che un override
ce l'hanno davvero**.

⚠️ **Un `BLOCCATO` scritto NON è «nessun override»**: il primo è un livello
esplicito che **batte il profilo del reparto**, il secondo lascia decidere al
profilo. Mandare tutte e 59 le righe materializzerebbe 59 override reali e
cambierebbe il comportamento di ogni utente con un profilo — con la richiesta
che diceva «non modifichiamo la funzionalità».

⇒ Servono quindi **due stati distinti e visibili** su ogni riga: *«da profilo /
default»* (nessuna riga scritta) e *«override»* (riga scritta), con un'azione
esplicita per tornare dal secondo al primo. È lo stesso `Tag` «Configurata /
Non configurata» del pattern slot/override.

### 7.6 · Regola del 2 — ✅ estrazione approvata (Tid, 2026-09-05)

La memoria del pattern slot/override chiude così: *«Il componente frontend non è
stato estratto come core component: si farà al secondo uso reale.»* Questo è il
secondo uso reale, e **l'estrazione del BB è approvata**: matrice slot/override
con stato per riga ed editing inline.

⚠️ **E il BB non è una `DataTable` nuda** (indicazione di Tid): sta alle
convenzioni del progetto come qualunque altro componente — CSS `app-*` da
`theme.css`, icone da `MANAGE_ICONS`, `readonly` iniettato con
`useInjectReadonly`, testi da i18n. La scelta di §7.4 riguarda *quale telaio*
(non `ListaConfigurabile`), non il livello di finitura.

---

### 7.7 · ⭐ Mostrare il valore EREDITATO su ogni riga (Tid, 2026-09-05)

**La richiesta**: far vedere, riga per riga, cosa l'utente ha già dal profilo,
così non si rifà un override per una cosa già concessa.

⭐ **E il guadagno è più grande del tempo risparmiato.** Un override che
*ripete* il valore del profilo non è rumore innocuo: **congela l'utente**. Da
quel momento quella riga non segue più il profilo, quindi il giorno in cui il
reparto cambia livello l'utente col doppione resta indietro — e nessuno lo
segnala. Mostrare l'ereditato non evita solo un click: evita un difetto
silenzioso.

#### 🔴 Ma la sorgente NON è «il reparto»

`script.fn_get_profili_accesso_applicabili` risolve **tre** tipi di binding, con
priorità:

| Priorità | Tipo | Legato a |
| --- | --- | --- |
| **1** | `AD_HOC` | l'identità digitale dell'utente |
| 2 | `PORTALE` | il ruolo applicativo dell'identità |
| 2 | `REPARTO` | l'unità organizzativa |

e i resolver prendono `ORDER BY priorita LIMIT 1`.

⛔ L'endpoint esistente `GET /amm-software/reparti/<uo_id>/profilo/` legge
**solo** il binding `REPARTO`, per `unita_organizzativa_id`. Per un utente con un
binding `AD_HOC` mostrerebbe un valore che **non è quello applicato** — su una
schermata di sicurezza, cioè nel posto peggiore in cui dare un'informazione
plausibile e falsa.

> 📌 *Fatto datato (2026-09-05, non è il motivo)*: i bindings attivi oggi sono
> 4 `REPARTO`, 3 `PORTALE`, 1 `SUPER_ADMIN` — **nessun `AD_HOC`**. Quindi oggi
> la scorciatoia darebbe per caso la risposta giusta. Ma l'etichetta «dal
> reparto» sarebbe sbagliata di suo, e il primo `AD_HOC` la renderebbe anche
> falsa.

⇒ **Serve una piccola aggiunta BE**: un endpoint per-utente che chiami
`fn_get_profili_accesso_applicabili(auth_user_id)` — **la stessa funzione dei
resolver**, quindi nessuna seconda implementazione della catena — e restituisca,
per area e per azione, il **livello ereditato** più il **nome del profilo che lo
fornisce**. L'etichetta a video diventa allora *«da profilo «Back-office»»* e
non *«dal reparto»*.

ℹ️ È un'aggiunta in **sola lettura**: non tocca la semantica dei permessi, quindi
resta dentro il perimetro «nessun cambio di funzionalità».

#### ⚠️ Per gli oggetti l'ereditato è l'AREA, non un profilo

Non esiste `config.profili_accesso_oggetti`: la catena di un model è *override
oggetto → override area → profilo dell'**area** → BLOCCATO*. Quindi nella lista
oggetti la colonna si chiama **«ereditato dall'area»**, e il valore mostrato è
quello dell'area — non un livello di profilo che per gli oggetti non esiste.
Chiamarla come le altre due sarebbe un nome sbagliato su un valore giusto.

---

## 8 · Riconteggio al 2026-09-25

> 📌 *Fatti datati, non motivi.* I conteggi del §1 e i fatti del §3 e del §7.7
> sono del 2026-09-05. Qui li si rifà con le stesse sorgenti del pannello: i
> lookup `aree-funzionali`, `azioni-processo` e `model-overrides`
> (`AmmSoftwareRepository`), letti sul database di sviluppo. Nessuna decisione
> cambia: la scelta di mostrare tutte le righe senza paginare sta sul **modello**
> (§7.3, una riga per voce di catalogo), non sul numero.

| | 2026-09-05 | **2026-09-25** | Cosa è cambiato |
| --- | --- | --- | --- |
| Aree funzionali attive | 13 | **14** | + `ai_assistant` |
| Azioni di processo | 34 | **35** | + 1 in `magazzino` |
| Model overridabili | 12 | **12** | — (nessuno riservato) |
| **Righe del pannello** | 59 | **61** | |
| Profili di accesso | 8 | **8** | — |
| Utenti con almeno un override | 3 | **3** | 6 righe aree, 20 azioni, 4 oggetti |

Azioni per area: `vendite` 19, `pratiche` 8, `config` 2, `documenti` 2,
`strumenti` 2, `magazzino` 1, `pagamenti` 1. **Sette aree a zero**:
`anagrafiche`, `acquisti`, `catalogo`, `contabilita`, `storico`, `core`,
`ai_assistant`.

**I fatti del §3 e del §7.7, ricontrollati:**

- **Tetto d'area**: ancora **zero** azioni abilitate da override sotto un'area
  che per quell'utente risulta `BLOCCATO`, e i 4 override oggetti sono tutti
  ≤ al livello della loro area. ⇒ Cambiare la regola oggi non cambierebbe il
  significato di nessuna configurazione. Il difetto resta aperto nel codice:
  [`permissions.py`](../../../backend/apps/core/api/permissions.py) consulta
  ancora solo l'azione.
- **Binding attivi**: 4 `REPARTO`, 3 `PORTALE`, 1 `SUPER_ADMIN`, **nessun
  `AD_HOC`** — come il 05-09.
- ⚠️ **Override che ripetono l'ereditato** (il caso dell'avviso, piano §3.3):
  **5 dei 6** override aree ripetono il livello del profilo, e **3 dei 4**
  override oggetti ripetono il livello dell'area. Sono righe che *congelano*
  l'utente (§7.7): se il profilo cambia, quegli utenti restano indietro. Il
  collaudo le usa come casi veri per la prova dell'avviso; se toglierle è una
  decisione di Tid, non del collaudo.
