# Permessi e Autorizzazioni v3 — Sotto-Oggetti e UX Gerarchica

> Documento di pianificazione per l'evoluzione del sistema permessi oltre il livello model piatto.
> Data creazione: 2026-04-22
> Stato: **IN PIANIFICAZIONE**
> Prerequisito: v2 completata (in work-done/permessi-e-autorizzazioni-v2.md)
> Guida architetturale: `docs/it/guide/architettura-permessi-e-autorizzazioni.md`

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

Aggiungere una riga in `config.area_model_overrides` per il sotto-model:

```sql
INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
VALUES ('anagrafiche', 'indirizzo', 1)  -- area_id 1 = anagrafiche
ON CONFLICT DO NOTHING;
```

Da questo momento il catalogo sa che `indirizzo` e' configurabile come oggetto autonomo.

### 2. BE — dichiarare `model_permission` sulla view Django

Aggiungere l'attributo sulla view (o sulle view) che gestiscono il sotto-oggetto:

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

Con la v2 la configurazione degli override oggetto e' gestita nella tab Permessi
del drawer operatore: una DataTable con colonne Model / Livello / Elimina + un form
di aggiunta a fondo pagina.

Funziona con 5-10 model. Con 20-30 model (e sotto-model) diventa:
- Lista senza struttura visiva (non si capisce cosa e' padre e cosa e' figlio)
- Impossibile vedere a colpo d'occhio il profilo permessi di un operatore
- Difficile capire quali override sono "attivi" vs "ereditati dall'area"
- Impossibile gestire dipendenze (se blocco `cliente`, cosa succede agli indirizzi?)

---

## Proposta UX v3: interfaccia gerarchica

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

I model gia' registrati e attivi con `model_permission` dichiarato:

| Model | app_label | Parent logici | FE attivato |
|-------|-----------|--------------|-------------|
| soggetto | anagrafiche | — | Si' |
| cliente | anagrafiche | soggetto | Si' |
| fornitore | anagrafiche | soggetto | Si' |
| conto_bancario | anagrafiche | soggetto, cliente, fornitore | Si' |
| articolo | catalogo | — | Si' |
| unita_misura | catalogo | — | Si' |
| promo_articolo | vendite | — | Si' |

Non ancora registrati (candidati per v3):
- `anagrafiche.indirizzo` — figlio di soggetto/cliente/fornitore
- `anagrafiche.contatto` — figlio di soggetto/cliente/fornitore
- `anagrafiche.billing_account` — autonomo (ora solo in catalogo)
- `vendite.fattura`, `vendite.preventivo`, `vendite.listino`
- `pratiche.pratica`

---

## Task v3

### DB

- [ ] DB-1 — Valutare Opzione A vs B per modellare gerarchia padre/figlio
- [ ] DB-2 — Migration Liquibase per struttura scelta
- [ ] DB-3 — Seed relazioni padre/figlio per i model gia' registrati
- [ ] DB-4 — Aggiornare `fn_get_user_object_permissions_map` se necessario

### Backend

- [ ] BE-1 — Endpoint `GET /api/v1/amm-software/lookup/model-overrides/` esteso con gerarchia
- [ ] BE-2 — Endpoint `GET /api/v1/amm-software/operatori/{id}/permessi-effettivi-oggetti/`
             che ritorna mappa completa (area + model + livello risolto + is_override) per la UI
- [ ] BE-3 — Registrare `model_permission` sulle view mancanti man mano che i domini si completano

### Frontend

- [ ] FE-1 — Componente `PermessiOggettiTree.vue` — albero gerarchico aree/model/sotto-model
- [ ] FE-2 — Sostituire DataTable piatta in `OperatorePermessiTab` con il nuovo albero
- [ ] FE-3 — Attivare `useReadonlyMode` sui drawer sotto-oggetto candidati
             (IndirizziPanel, ContatiPanel quando implementato, ecc.)
- [ ] FE-4 — 1.9 differita: UI admin per gestire `area_model_overrides` (aggiunta/rimozione
             model dal catalogo) — bassa priorita', cambia raramente

---

## Dipendenze

- v2 completata ✅
- Nessuna dipendenza bloccante — i tre passi (DB/BE/FE) per ogni sotto-oggetto
  sono indipendenti e applicabili incrementalmente dominio per dominio
