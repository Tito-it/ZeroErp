# Permessi e Autorizzazioni v3 — Sotto-Oggetti e UX Gerarchica

> Documento di pianificazione per l'evoluzione del sistema permessi oltre il livello model piatto.
> Data creazione: 2026-04-22
> Stato: **IN PIANIFICAZIONE — dormiente** (nessun lavoro dal 2026-04-22)
> Prerequisito: v2 completata (in work-done/permessi-e-autorizzazioni-v2.md)
> Guida architetturale: `docs/it/guide/architettura-permessi-e-autorizzazioni.md`
>
> 🔎 **Riletto il 2026-09-26 contro il codice.** Cosa è cambiato da aprile:
>
> - il pannello permessi è stato rifatto il 2026-09-05 (tutte le voci, colonna
>   «ereditato», reset): la sezione UX qui sotto è aggiornata, e l'albero
>   gerarchico è **scartato** (decisione di Tid: si resta nel drawer);
> - il modello **piatto** su cui la v3 costruisce è **allineato dal
>   2026-09-28**: catalogo, BE, FE e pannello DB dicono la stessa cosa su ogni
>   oggetto personalizzabile, e un test lo presidia
>   ([brief-db-be-fe-catalogo-oggetti-permessi.md](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md), chiuso);
> - ✅ **il tetto d'area, da cui la gerarchia padre/figlio dipende, è CHIUSO
>   dal 2026-10-04** ([brief-db-permessi-tetto-area.md](../work-done/brief-db-permessi-tetto-area.md)):
>   un permesso specifico (oggetto, azione di processo) **può solo restringere**
>   quello della sua area — `script.fn_livello_con_tetto_area` per gli oggetti,
>   `script.fn_area_consente_azione` per le azioni. La gerarchia ha quindi una
>   semantica: un figlio non può essere più permissivo del padre. (Fino al
>   2026-10-31 qui stava scritto «difetto aperto e senza decisione».)
> - il pannello permessi dell'operatore è **per area** dal 2026-10-04 (elenco
>   delle aree, area scelta a destra), e dal 2026-10-31 lo è anche il profilo
>   del reparto (BB `ElencoDettaglio`).

---

## Contesto

La v2 ha introdotto il **livello oggetto**: l'admin puo' dare a un operatore un livello diverso
per ogni model Django registrato in `config.area_model_overrides`.

Esempio attuale funzionante:
- Mario ha TUTTO su `anagrafiche` (area)
- Ma BLOCCATO su `conto_bancario` (model override)

Il sistema funziona bene per model **flat** (uno scope = un model = una view).
Non copre ancora i **sotto-oggetti**: entita' figlio legate a un padre tramite FK,
dove il permesso utile e' "TUTTO sui clienti ma BLOCCATO sugli indirizzi dei clienti".

---

## Problema: sotto-oggetti non ancora dichiarabili

Oggi `config.area_model_overrides` non modella relazioni padre/figlio.
Un model come `indirizzo` e' registrato (o non registrato) in modo piatto,
senza sapere che e' un sotto-oggetto di `cliente` o `soggetto`.

Conseguenze:
- Non si puo' dire "blocca gli indirizzi solo quando acceduti dal drawer cliente"
- Un operatore con LETTURA su `soggetto` eredita lo stesso livello su tutto quello che
  appare nel drawer soggetto (indirizzi, contatti, conti bancari) senza granularita'
- La tab "Override Oggetti" nell'OperatorePermessiDrawer mostra una lista piatta
  che diventa ingestibile con 20+ model/sotto-model

---

## Pattern di evoluzione (gia' funzionante, da applicare caso per caso)

Aggiungere un sotto-oggetto al sistema permessi richiede tre passi coordinati:

### 1. DB — migration Liquibase

Aggiungere una riga al catalogo `config.area_model_overrides` per il sotto-model
(es. `('anagrafiche', 'indirizzo')` sull'area `anagrafiche`): una riga nel CSV
`80_data/sql/config/area_model_overrides.csv` (D-3 del
[brief del catalogo](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md)), mai un `INSERT` in una migration.
⚠️ **L'ordine è BE e FE prima, catalogo dopo**: un oggetto a catalogo che il BE
non chiede ancora nasconde i pulsanti e lascia aperta l'API. Nell'attesa
l'oggetto sta in `_IN_ATTESA_DI_CATALOGO`
(`backend/apps/core/tests/test_catalogo_oggetti_rotte.py`).

Da questo momento il catalogo sa che `indirizzo` e' configurabile come oggetto autonomo.

### 2. BE — dichiarare `model_permission` sulla view Django

Aggiungere l'attributo su **tutte** le view che leggono o scrivono il
sotto-oggetto, non su una sola. ⛔ Un oggetto a catalogo con una sola rotta che
lo applica (per esempio le sole note) fa mentire il pannello: l'override si
imposta, e sul resto dell'oggetto vale l'area.

```python
class ApiIndirizziList(DomainAPIView):
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "indirizzo")
```

Il backend ora chiama `fn_resolve_livello_oggetto` per quel model e applica il livello
risolto (override specifico, altrimenti fallback al livello area).

### 3. FE — il componente figlio dichiara il proprio scope

Il drawer o pannello che gestisce il sotto-oggetto smette di ereditare passivamente
e diventa provider autonomo:

```js
// Prima (eredita dall'area o dal drawer padre):
const isReadonly = useInjectReadonly()

// Dopo (scope autonomo con fallback area):
const { isReadonly, isBlocked } = useReadonlyMode('anagrafiche', 'indirizzo')
```

Questo permette che lo stesso drawer `IndirizziPanel` si comporti diversamente
a seconda del profilo dell'operatore, indipendentemente dal drawer padre.

---

## Problema UX: la lista piatta non scala

> ✅ **Superato in parte il 2026-09-05** (`work-done/analisi-ui-permessi-operatore.md`,
> `work-done/piano-be-fe-ui-permessi-operatore.md`). La tab Permessi del drawer operatore
> non è più una DataTable Model / Livello / Elimina con un form di aggiunta: è il
> BB `MatriceOverride`, con **tutte** le voci del catalogo, lo stato
> «Override» / «Ereditato», la colonna «ereditato» (per un oggetto: il livello
> della sua area) e il reset che torna al valore ereditato.

Dei quattro problemi di aprile ne restano due:
- ~~Impossibile vedere a colpo d'occhio il profilo permessi di un operatore~~ — risolto
- ~~Difficile capire quali override sono "attivi" vs "ereditati dall'area"~~ — risolto
- Lista senza struttura visiva (non si capisce cosa e' padre e cosa e' figlio)
- Impossibile gestire dipendenze (se blocco `cliente`, cosa succede agli indirizzi?).
  ✅ La metà «area → oggetto» di questa domanda è il **tetto d'area**, chiuso il
  2026-10-04: un override per oggetto non **sostituisce** più il livello
  dell'area, lo **limita** (vince il più restrittivo). Resta della v3 la metà
  «oggetto padre → oggetto figlio»

---

## Proposta UX v3: interfaccia gerarchica

> ⛔ **Scartata come forma il 2026-09-05** (decisione di Tid: nessun cambio di
> funzionalità, si resta nel drawer con la matrice a righe piene). Le
> caratteristiche per riga qui sotto (livello effettivo, ereditato contro
> override, rimuovi override → ereditato) sono **già fatte** in forma piatta. Resta
> valido il bisogno di mostrare padre e figlio, che arriva solo con i
> sotto-oggetti: se e quando la v3 riparte, la gerarchia si innesta sulla
> matrice, non su un componente nuovo.

### Struttura visiva ad albero

L'interfaccia mostra le aree come nodi radice, con i model come figli e i sotto-model
come nipoti. Ogni nodo mostra il livello effettivo (risolto) e se e' un override
esplicito o ereditato.

```
▼ Anagrafiche                         [TUTTO — area default]
    ├── Soggetto                       [TUTTO — ereditato]
    ├── Cliente                        [TUTTO — ereditato]
    │   ├── Indirizzo cliente          [BLOCCATO — override]  ← editabile
    │   └── Conto bancario cliente     [LETTURA — override]   ← editabile
    └── Fornitore                      [TUTTO — ereditato]
▶ Vendite                              [LETTURA — area override]
▶ Catalogo                             [TUTTO — area default]
```

Ogni riga mostra:
- Icona ad albero (indentazione padre/figlio)
- Nome model leggibile (non `app_label.model_name` grezzo)
- Livello effettivo con badge colorato (TUTTO=verde, LETTURA=giallo, BLOCCATO=rosso)
- Indicatore "ereditato" vs "override esplicito"
- Azione inline: click sul badge apre un dropdown TUTTO / LETTURA / BLOCCATO / Rimuovi override

### Comportamento

- Le aree collassate mostrano solo il livello area; si espandono per vedere i model
- I model ereditati (nessun override) mostrano il livello area in grigio
- I model con override mostrano il livello in colore pieno
- Modificare un model aggiorna il livello nel backend via PUT esistente
- Aggiungere un override su un model "ereditato" crea la riga in `user_override_oggetti`
- Rimuovere un override torna al livello ereditato

### Dati aggiuntivi necessari nel catalogo

Per supportare la gerarchia visiva, `config.area_model_overrides` deve sapere
se un model e' figlio di un altro. Opzioni:

**Opzione A** — colonna `parent_model_name` nullable in `area_model_overrides`:
```sql
ALTER TABLE config.area_model_overrides
  ADD COLUMN parent_model_name varchar;
```
Semplice, ma non modella relazioni N:M (un indirizzo puo' apparire sotto soggetto E cliente).

**Opzione B** — tabella separata `config.area_model_relations`:
```sql
CREATE TABLE config.area_model_relations (
  parent_model_id integer REFERENCES config.area_model_overrides(id),
  child_model_id  integer REFERENCES config.area_model_overrides(id),
  PRIMARY KEY (parent_model_id, child_model_id)
);
```
Piu' flessibile, supporta N:M. Un indirizzo puo' essere figlio sia di soggetto che di cliente.

**Raccomandazione**: Opzione B — il modello reale ha gia' relazioni N:M
(lo stesso drawer indirizzi appare in soggetto, cliente e fornitore).

---

## Stato attivazione attuale (base per v3)

> 🔄 **Riscritto il 2026-09-28.** Gli oggetti personalizzabili sono le righe
> `riservato = f` del CSV `80_data/sql/config/area_model_overrides.csv`, e
> `backend/apps/core/tests/test_catalogo_oggetti_rotte.py` fallisce se BE o FE
> non li applicano tutti, o ne applicano uno fuori catalogo. L'elenco sta lì, e
> qui non si ricopia: due copie divergerebbero al primo aggiornamento. Come ci
> si è arrivati: [brief del catalogo](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md).

Candidati per la v3 **non ancora** a catalogo né applicati (sotto-oggetti veri):
- `anagrafiche.indirizzo` — figlio di soggetto/cliente/fornitore
- `anagrafiche.contatto` — figlio di soggetto/cliente/fornitore

(`fattura`, `preventivo`, `listino` e `pratica`, candidati ad aprile, sono a
catalogo e applicati. `billing_account` è uscito dal catalogo: è un pezzo del
cliente, e il permesso è `cliente` — D-5 del brief del catalogo.)

---

## Task v3

### DB

- [ ] DB-1 — Valutare Opzione A vs B per modellare gerarchia padre/figlio
- [ ] DB-2 — Migration Liquibase per struttura scelta
- [ ] DB-3 — Seed relazioni padre/figlio per i model gia' registrati
- [ ] DB-4 — Aggiornare `fn_get_user_object_permissions_map` se necessario

### Backend

- [ ] BE-1 — Endpoint `GET /api/v1/amm-software/lookup/model-overrides/` (esiste, piatto,
             con `can_override`) esteso con gerarchia
- [ ] BE-2 — ~~Endpoint `permessi-effettivi-oggetti`~~ — **coperto in parte**:
             `GET /api/v1/core/users/{id}/permessi-effettivi/` restituisce già, per area,
             i suoi oggetti col livello risolto; manca `is_override`. La matrice FE lo
             ricava dagli override. Da riaprire solo se la gerarchia lo richiede
- [x] BE-3 — ~~Registrare `model_permission` sulle view mancanti~~ — spostato nel
             [brief del catalogo](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md) §3.2, chiuso il 2026-09-28

### Frontend

- [x] FE-1 — ~~Componente `PermessiOggettiTree.vue`~~ — scartato il 2026-09-05 (vedi
             «Proposta UX v3»)
- [x] FE-2 — ~~Sostituire la DataTable piatta~~ — fatto in altra forma: `MatriceOverride`
             nel tab `OperatorePermessiTab` (2026-09-05)
- [ ] FE-3 — Attivare `useReadonlyMode` sui drawer sotto-oggetto candidati
             (IndirizziPanel, ContattiPanel quando implementato, ecc.)
- [ ] FE-4 — 1.9 differita: UI admin per gestire `area_model_overrides` (aggiunta/rimozione
             model dal catalogo) — bassa priorita', cambia raramente

---

## Dipendenze

- v2 completata ✅
- ✅ **Modello piatto allineato** il 2026-09-28:
  [brief-db-be-fe-catalogo-oggetti-permessi.md](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md)
- ✅ **Tetto d'area** — chiuso il 2026-10-04
  ([brief-db-permessi-tetto-area.md](../work-done/brief-db-permessi-tetto-area.md)):
  un permesso specifico può solo restringere quello della sua area. È la
  semantica che la gerarchia padre/figlio estende un livello più in giù
- I tre passi (DB/BE/FE) per ogni sotto-oggetto restano applicabili dominio per
  dominio, **ma insieme**: catalogo, rotte e vista dello stesso oggetto nello
  stesso rilascio
