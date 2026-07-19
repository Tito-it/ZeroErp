# Brief DB — Dashboard home: catalogo widget + preferenza utente

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🟠 ALTA (prerequisito bloccante: senza queste
> strutture il lavoro BE/FE sulla home non può partire)
> **Stato**: ☐ DA REALIZZARE
> **Origine**: revisione della home page. Le 4 card `Dash 1..4` di
> `HomeView.vue` sono placeholder statici dal giorno uno; la visione già scritta
> in [layout-menu-navigazione.md §9.2](frontend/layout-menu-navigazione.md)
> («la home diventerà una dashboard personalizzata per utente, composta da card
> configurabili») non è mai stata istruita perché manca ogni struttura di
> persistenza.

## 1. Cosa serve (NON come)

Serve **persistere a DB quali card KPI un utente vede in home, in che ordine**,
con un default sensato per chi non ha mai personalizzato nulla.

Tre capacità, in ordine di dipendenza:

1. **Un catalogo dei widget disponibili**, censiti a sistema — non un elenco
   hardcodato nel frontend. Ogni widget è una card KPI: un numero, una soglia di
   attenzione, e un deep-link a una vista in stato preimpostato.
2. **Un default per ruolo**: quali widget vede un utente che non ha mai toccato
   la home. Deve poter variare per veste applicativa (chi lavora le pratiche non
   vede le stesse card di chi fattura).
3. **Un override per utente**: selezione e ordine scelti dall'utente, che
   vincono sul default.

Il tutto risolto da **una singola funzione di lettura** che, dato un utente,
ritorna la configurazione effettiva della sua home — già filtrata per i permessi
di quell'utente, senza che il BE debba ricomporre nulla.

### Vincolo forte: nessuna home vuota

Un utente nuovo, senza preferenza e senza preset di ruolo applicabile, **deve
comunque ricevere una home popolata**. Una home vuota al primo accesso è peggio
delle 4 card placeholder di oggi. La risoluzione deve degradare fino al
catalogo grezzo, mai a lista vuota.

### Vincolo: i widget sono filtrati dai permessi

Un widget che deep-linka a una vista che l'utente non può aprire **non deve
comparire**, né come card né nel pool selezionabile della personalizzazione. Il
filtro è responsabilità della risoluzione lato DB, non del frontend: il FE non
deve mai ricevere un widget che poi nasconde.

### Fuori dal perimetro di questo brief

- **Quali KPI** entrano nel catalogo iniziale e con che soglie: si decide nel
  brief BE/FE, non qui. Al DB serve che il catalogo *esista*, popolarlo è un
  seed successivo.
- **Come si calcola** ciascun contatore: sono query/endpoint BE sui domini già
  esistenti (pratiche, lenti fatturazione, resi, push commessa). Nessuna
  materializzazione, nessun job.
- **I preferiti-route attuali** (localStorage, `navigation.js`): restano dove
  sono. Migrarli a DB è coerente ma è un refactor a sé che non blocca la home.
- Widget non-KPI (grafici, liste embedded): non ora.

## 2. Il precedente da ricalcare

Il meccanismo esiste già, applicato a un problema quasi identico: la
personalizzazione delle liste, schema `ui`.

| Liste (esistente) | Dashboard (da fare) |
| --- | --- |
| `ui.lista_definizione` — catalogo liste | catalogo dashboard (oggi una sola: `home`) |
| `ui.lista_colonna` — catalogo elementi selezionabili | catalogo widget |
| `ui.lista_preset` + `lista_preset_colonna` — default per ambito `sistema`/`ruolo`/`emittente_fiscale` | default dashboard per ambito |
| `ui.lista_colonna_permesso` — livello accesso per profilo | filtro permessi dei widget (vedi §3) |
| `ui.lista_preferenza_utente` — override utente in JSONB | override utente |
| `ui.fn_resolve_lista_config` — cascata + merge + normalizzazione | risoluzione dashboard |

**La raccomandazione è di restare nello schema `ui` e replicare questa
famiglia**, non di creare una `config.user_preferences` generica. Motivi di
merito, non di comodità:

- La cascata di `fn_resolve_lista_config` è già collaudata e risolve esattamente
  i problemi che si ripresentano qui: preferenza utente prima, poi ruolo (con
  `profili_accesso.priorita` a rompere i pareggi), poi emittente, poi sistema,
  poi catalogo grezzo come rete di sicurezza.
- Il merge automatico degli **elementi nuovi** (step 3 di quella funzione:
  colonne apparse in catalogo dopo che l'utente ha salvato la sua preferenza,
  aggiunte con `visibile=FALSE` e conteggiate in `colonne_nuove`) serve
  identico qui: quando aggiungeremo un widget al catalogo, chi ha già
  personalizzato la home non deve restare cieco né vedersela riscritta.
- Il flag `preset_aggiornato` + `preset_aggiornato_ignored_at` risolve il caso
  "il default di ruolo è cambiato, avviso l'utente che ha un override": vale
  tale e quale.
- Una tabella chiave/valore generica non avrebbe niente di tutto questo, e ce lo
  ritroveremmo da riscrivere a mano nel BE.

Sono agganci da valutare, non un vincolo: se il team DB vede una ragione per
divergere, la decisione è sua — purché le tre capacità di §1 e i due vincoli
restino soddisfatti.

## 3. Punti che chiedono una decisione esplicita

Sono i punti dove la simmetria con le liste non è ovvia, e dove una scelta presa
distrattamente costa cara dopo.

**3a — Il widget appartiene alla dashboard o è globale?**
In `ui`, una colonna appartiene a una lista (`lista_colonna.lista_id`). Per i
widget la simmetria non è scontata: «resi da accreditare» ha senso in home oggi
e potrebbe averlo in una dashboard di magazzino domani. Le due strade sono
widget-per-dashboard (simmetrico, semplice, duplicazione se il widget serve
altrove) o widget globale + tabella di composizione (più flessibile, una FK in
più). Con una sola dashboard oggi non c'è evidenza per decidere sul campo:
serve una scelta consapevole, non ereditata.

**3b — Come si filtrano i permessi dei widget.**
Le liste hanno una tabella dedicata (`ui.lista_colonna_permesso`, livello per
profilo) perché una colonna può essere in sola lettura o mascherata. Un widget
non ha stati intermedi: **o lo vedi o non lo vedi**. Replicare la tabella
sarebbe sovradimensionato. L'aggancio naturale è che ogni widget dichiari l'area
funzionale / azione che deep-linka, e la risoluzione riusi il filtro
autorizzativo già esistente (`config.aree_funzionali`, override utente in
`config.user_override_*`). Da confermare che quel filtro sia interrogabile dalla
funzione di risoluzione.

**3c — Quante card in home.**
Oggi sono 4 e i preferiti hanno `FAVORITES_PER_DOMAIN_MAX = 4`: due limiti
scorrelati che coincidono per caso. Se il layout ha un massimo, va fissato
esplicitamente come dato (sul preset, come `lista_preset.pagina_dimensione`),
non lasciato implicito nel CSS del frontend.

**3d — Chiavi funzionali stabili.**
Convenzione già viva nello schema `ui`: i JSONB di configurazione referenziano
il `codice` stringa, mai l'`id` numerico, per resistere ai cross-ambiente.
Vale identico per i widget.

**3e — FK verso `django.auth_user`.**
Come `ui.lista_preferenza_utente`, va aggiunta in fase `90_end` perché
`auth_user` è creata da Django migrate dopo Liquibase.

## 4. Verifica attesa

Casi che devono essere esercitati prima di dichiarare fatto — sono le
condizioni al contorno di §1, non un elenco di cortesia:

1. Utente **senza preferenza e senza preset di ruolo** → riceve comunque widget
   (degradazione al catalogo grezzo).
2. Utente con **preferenza** → la preferenza vince sul preset di ruolo.
3. Utente con **due profili di accesso** applicabili → vince quello a priorità
   più bassa, deterministicamente (stesso comportamento di
   `fn_resolve_lista_config` step 2b).
4. **Widget aggiunto al catalogo** dopo che l'utente ha salvato → compare come
   nuovo/non visibile, la preferenza esistente non viene riscritta.
5. Utente **senza permesso** sull'area di un widget → quel widget non compare né
   fra le card né nel pool selezionabile.
6. Widget **disattivato** (`attivo = FALSE`) → sparisce da tutti gli utenti,
   inclusi quelli che l'avevano in preferenza.

## 5. Cosa comunicare indietro a BE/FE

Alla chiusura servono, per poter scrivere il brief BE/FE:

- **firma della funzione di risoluzione** e **forma del JSONB** di ritorno (è il
  contratto che il FE consuma);
- **forma del JSONB** della preferenza utente (è ciò che il FE scrive al salva);
- **codice della dashboard** home e nomi delle tabelle, per il seed del catalogo
  widget che faremo subito dopo;
- eventuali **divergenze** da §2/§3: se il modello adottato non è quello delle
  liste, va detto, perché il BE riuserebbe altrimenti i pattern di
  `lista_preferenza_service.py` per analogia.

Nessun adeguamento FE è pendente: oggi la home mostra card statiche, non c'è
codice da rompere.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Decisioni §3a–3e prese e motivate | ☐ |
| 2 | Catalogo widget + default per ambito + preferenza utente | ☐ |
| 3 | Funzione di risoluzione con cascata, merge nuovi, filtro permessi | ☐ |
| 4 | Verifica §4 (6 casi) | ☐ |
| 5 | Apply dev + rigen doc auto-gen + comunicazione §5 a BE/FE | ☐ |

## 7. Riferimenti

- Visione home: `docs/it/dev/work-in-progress/frontend/layout-menu-navigazione.md` §9
  (§9.1 stato attuale, §9.2 visione futura, §Persistenza preferiti riga 527)
- Precedente di design sulla grammatica launcher:
  `docs/it/dev/work-done/brief-fe-home-operatore-launcher.md` §2.2
- Modello da ricalcare: `docs/it/dbzero/ui/` (tabelle `lista_definizione`,
  `lista_colonna`, `lista_preset`, `lista_preset_colonna`,
  `lista_colonna_permesso`, `lista_preferenza_utente`)
- Funzione di riferimento: `docs/it/dbzero/ui/funzioni/fn_resolve_lista_config.md`
  + `docs/it/dbzero/ui/manual/fn_resolve_lista_config.md`
- Consumatori attuali della home: `frontend/src/core/views/HomeView.vue`,
  `frontend/src/stores/navigation.js`,
  `frontend/src/core/composables/useNavigationFavorites.js`
- Dashboard esistenti (candidate a fornire i KPI):
  `docs/it/dev/work-in-progress/brief-design-fatturazione-due-lenti.md`
