# Brief DB — Guard sorgente polimorfa: chiudere il buco, non rattopparlo

> **Stato**: DA EVADERE (accantonato deliberatamente: emerso il 2026-07-18 durante lo step 6b
> della slice fatturazione DDT/resi, si affronta a slice chiusa).
> **Origine**: scrivendo `vw_stato_sorgente_ddt` è emerso che la chiave giusta era `id::text`
> e non l'uid — e controllando *perché* la riga DDT viva in `commesse_sorgenti` avesse un uuid
> si è scoperto che il guard che avrebbe dovuto impedirlo **non è agganciato a nulla**, e che
> il problema è più largo di una riga.
> **Decisione di metodo (Tid, 2026-07-18)**: *«i buchi vanno chiusi e non con delle toppe»* —
> questo brief esiste per chiuderlo con un lavoro completo: guard giusto, dati bonificati,
> catena di popolamento corretta, doc allineata, test.

---

## 1. I fatti (tutti verificati sul DB vivo, 2026-07-18)

### 1a. Esistono DUE modelli di colonne-sorgente, e il guard ne conosce solo uno

**Modello A — colonne tipizzate alternative** (target di progetto del guard; il suo manuale
dice *«Esempio tipico: `vendite.attivita_fatturabili`»*):

| colonna | tipo | uso |
|---|---|---|
| `sorgente_riga` | BIGINT | **è la chiave** quando `key_selector='id'` |
| `sorgente_uid` | UUID | **è la chiave** quando `key_selector='uid'` |

Dato vivo che lo conferma: in `attivita_fatturabili` la riga con sorgente COMMESSA
(`key_selector='id'`) ha `sorgente_riga` valorizzata. Il guard
`script.trgfn_guard_sorgente_polimorfa`, così com'è scritto, valida esattamente questo
modello: `selector='id'` → legge `NEW.sorgente_riga`; `selector='uid'` → legge
`NEW.sorgente_uid` (uuid).

**Modello B — chiave unica testuale** (tabelle di collegamento polimorfe:
`pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti`):

| colonna | tipo | uso |
|---|---|---|
| `sorgente_uid` | TEXT | **la chiave**, nel formato dettato da `key_selector`: `id::text` per i tipi `id`, uuid-testo per i tipi `uid` |
| `sorgente_riga` | BIGINT | ⚠️ **NON è una chiave documento**: è *«ID di una riga specifica della sorgente (es. riga preventivo)»* (manuale `pratiche_sorgenti`) — grana di riga del link, semantica diversa |

È la convenzione documentata in `config/manual/sorgenti.md` §Convenzione chiave sorgente,
quella su cui sono costruite le `vw_stato_sorgente_*` (sei rami dal 2026-07-18).

**⚠️ Conseguenza per `sorgente_riga`: NON va cancellata.** Ha due scopi legittimi e diversi:
chiave-id nel modello A, riferimento di riga nel modello B (es. `fn_link_commessa_sorgente`
la accetta come `p_sorgente_riga` per il link a grana riga). La colonna resta; ciò che va
sistemato è il guard che la interpreta male fuori dal suo modello. *(Verificato su richiesta
Tid, che sospettava uno scopo specifico: confermato dalla doc.)*

### 1b. Il guard non è agganciato a NESSUNA tabella

```sql
SELECT ... FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
 WHERE p.proname LIKE '%sorgente_polimorfa%' AND NOT t.tgisinternal;
-- (0 righe)
```

Né a `pratiche_sorgenti`, né a `commesse_sorgenti`, né ad `attivita_fatturabili` (il suo
target di progetto). La funzione esiste, la doc del manuale sorgenti la dà per **«Guard
attivo»** — è falso oggi. E attaccarlo com'è alle tabelle del modello B sarebbe peggio che
non averlo: pretenderebbe `sorgente_riga` (che lì è sempre NULL e significa altro) e
fallirebbe ogni INSERT legittimo. Ecco perché nessuno l'ha mai attaccato: **il guard non
rispecchia il modello davvero in uso** dalle tabelle di collegamento.

### 1c. `commesse_sorgenti` viola la convenzione del modello B — e nessuno se n'è accorto

Censimento vivo (2026-07-18):

| tabella | tipo | `key_selector` | righe | formato `sorgente_uid` vivo | risolve in `vw_stato_sorgente`? |
|---|---|---|---|---|---|
| pratiche_sorgenti | PREVENTIVO | uid | 45 | uuid | ✅ 45/45 |
| pratiche_sorgenti | ORDINE_VENDITA | id | 20 | **numerico** (giusto) | ✅ 20/20 |
| pratiche_sorgenti | COMMESSA | id | 19 | **numerico** (giusto) | ⛔ 0/19 — manca il ramo COMMESSA, vedi §5 |
| commesse_sorgenti | PREVENTIVO | uid | 47 | uuid | ✅ 47/47 |
| commesse_sorgenti | ORDINE_VENDITA | id | 20 | **uuid** (SBAGLIATO) | ⛔ 0/20 |
| commesse_sorgenti | CONTRATTO | id | 2 | **uuid** (SBAGLIATO) | ⛔ 0/2 |
| commesse_sorgenti | DDT_VENDITA | id | 1 | **uuid** (SBAGLIATO) | ⛔ 0/1 |

`pratiche_sorgenti` rispetta la convenzione (popolata dal service pratiche).
`commesse_sorgenti` no: la catena **lister → orchestratore push BE → `fn_link_commessa_sorgente`**
inserisce l'**uid** anche per i tipi a chiave `id` — i lister (`fn_list_ordini_da_pushare`,
`fn_list_ddt_da_pushare`, …) emettono `sorgente_uid = <doc>.uid::text` e la fn lo stocca
com'è, senza normalizzare.

**Perché è rimasto invisibile**: l'unico consumatore odierno di `script.vw_stato_sorgente` è
`backend/apps/pratiche/db/pratiche_repository.py` (proiezione stato pratiche), che legge solo
`pratiche_sorgenti` — dove la convenzione è rispettata. Le righe sbagliate di
`commesse_sorgenti` non le interroga ancora nessuno: il bug è **latente**, non innocuo. Il
giorno in cui commesse vorrà la proiezione di stato delle sue sorgenti (o il lineage
incrocerà i link commessa), quelle righe risulteranno «non risolte» in silenzio.

### 1d. Nota di contesto: i tre usi di "sorgente_uid" NON vanno confusi

| dove | tipo | contenuto | meccanismo |
|---|---|---|---|
| `pratiche_sorgenti` / `commesse_sorgenti` | TEXT | chiave secondo `key_selector` | polimorfo (questo brief) |
| `ddt.sorgente_uid`, `resi.sorgente_uid` | UUID | uid del documento padre | colonna tipizzata diretta — FUORI da questo brief |
| `commesse_attivita.sorgente_uid` | TEXT | hash md5(segment_key) (caveat C1) | interno commesse — FUORI da questo brief |

---

## 2. Cosa si fa — i cinque pezzi del lavoro completo

> Ordine pensato per non rompere mai nulla in mezzo: prima il codice tollera entrambe le
> forme, poi si bonificano i dati, poi il guard blinda la forma canonica.

### 2a. `fn_link_commessa_sorgente` normalizza la chiave (il rubinetto)

La fn legge `config.sorgenti.key_selector` del tipo che riceve e **normalizza**:
- `key_selector='id'` + valore uuid → risolve l'uuid contro `target_table` e stocca `id::text`;
- `key_selector='id'` + valore numerico → stocca com'è;
- `key_selector='uid'` → stocca l'uuid com'è;
- valore non risolvibile → errore parlante (nuovo codice, append CSV —
  [[feedback_messaggi_errore_no_new_loader]]).

Così i chiamanti esistenti (orchestratore push BE, che passa l'uid) **continuano a
funzionare senza modifiche BE** e da subito scrivono canonico. Difesa in profondità: la fn
normalizza, il guard (2c) valida.

> Alternativa scartata: cambiare i lister perché emettano `id::text` come `sorgente_uid`.
> Toccherebbe il contratto dei lister (il BE usa quel campo anche per display/log e la
> chiave di push singolo), con più superficie di rottura e zero benefici rispetto alla
> normalizzazione nel punto unico di scrittura.

### 2b. Backfill `commesse_sorgenti` (i dati già sbagliati)

Migration `80_data` una tantum: per le righe dei tipi `id` con `sorgente_uid` in formato
uuid, risolvere l'uuid contro la `target_table` del tipo e riscrivere `id::text`.
23 righe oggi (20 ordini + 2 contratti + 1 DDT). Casi:
- uuid risolve → riscrittura;
- uuid non risolve (documento sparito) → NON inventare: lasciare la riga e segnalarla
  (`meta.backfill_warning`), decisione umana a valle. ⚠️ Attenzione alla UNIQUE
  `(sorgente_tipo_id, sorgente_uid)`: se la forma canonica esiste già, la riga uuid è un
  duplicato logico → merge/rimozione, da decidere a vista sul dato reale.

### 2c. Il guard giusto — uno per modello, agganciati davvero

Il guard attuale è corretto **per il modello A**: resta (eventualmente rinominato per
chiarezza) e va **agganciato ad `attivita_fatturabili`**, il suo target dichiarato, oggi
scoperto anche lui.

Per il **modello B** serve la variante che valida `sorgente_uid` TEXT secondo
`key_selector` (`id` → `WHERE id = uid::bigint` con guardia sul formato; `uid` →
`WHERE uid = uid::uuid`), più — opzionale ma coerente — la verifica che `sorgente_riga`,
se valorizzata, esista davvero come riga della sorgente. Da **agganciare a
`pratiche_sorgenti` e `commesse_sorgenti`** (INSERT + UPDATE OF colonne sorgente).
Naming trigger: convenzione `trg_<tabella>_a10_guard_sorgente_ins_upd`.

> Forma da decidere in scrittura: due funzioni sorelle o una sola parametrizzata via
> `TG_ARGV` (modello come argomento). Criterio: leggibilità dell'errore e della doc, non
> l'eleganza — sono due semantiche diverse, va bene anche dirlo con due nomi.

### 2d. Doc allineata (quella che oggi mente)

- `config/manual/sorgenti.md` §Convenzione: «Guard attivo» → stato reale post-fix (quali
  trigger, su quali tabelle, quale variante).
- Manuale `trgfn_guard_sorgente_polimorfa`: documentare i DUE modelli e quale variante
  protegge cosa; oggi descrive solo il modello A ma la sezione «Quando si attiva» lascia
  intendere copertura generale.
- Manuale `pratiche_sorgenti` / doc `commesse_sorgenti`: esplicitare il formato di
  `sorgente_uid` e il significato (non-chiave) di `sorgente_riga`.

### 2e. pgTAP

- Modello B: INSERT canonico passa (id-testo per tipi `id`, uuid per tipi `uid`); INSERT
  con chiave inesistente → errore; INSERT uuid per tipo `id` su `commesse_sorgenti` →
  normalizzato dalla fn (si legge indietro `id::text`); `sorgente_riga` inesistente →
  errore (se si implementa la verifica).
- Modello A: INSERT `attivita_fatturabili` con `sorgente_riga` inesistente → errore.
- Post-backfill: la query di censimento del §1c torna 100% risolte (tranne eventuali
  righe `backfill_warning`).
- Regressione: `test-proiezione-stato-sorgente` (pratiche) e i pgTAP del push commesse
  restano verdi — il guard non deve rompere i flussi vivi
  ([[feedback_guard_breaks_existing_tests]]: grep pgTAP prima di attaccare trigger).

---

## 3. Decisioni aperte (da chiudere prima di scrivere)

| # | Domanda | Proposta | Stato |
|---|---|---|---|
| D1 | `sorgente_riga`: si tiene? | **SÌ, si tiene** — doppio scopo documentato (§1a). Solo chiarire la doc | ✅ orientamento Tid 2026-07-18, confermato dalla doc |
| D2 | Normalizzazione nella fn vs correzione dei lister | fn normalizza (§2a), lister intatti | ❓ |
| D3 | Guard: due funzioni o una parametrizzata | due funzioni sorelle, nomi parlanti | ❓ |
| D4 | La variante B verifica anche `sorgente_riga` come riga esistente della sorgente? | sì se il costo è basso (le tabelle righe sono note per tipo), altrimenti fase 2 | ❓ |
| D5 | Righe backfill non risolvibili / duplicati UNIQUE | flag in `meta` + decisione umana; nessuna cancellazione automatica | ❓ |
| D6 | Si aggancia anche ad `attivita_fatturabili` (modello A) nello stesso giro? | sì — è il target dichiarato del guard ed è scoperto | ❓ |

## 4. Fuori scope (dichiarato)

- Le colonne tipizzate dirette (`ddt.sorgente_uid`, `resi.sorgente_uid`) e il loro guard
  (hanno FK/guard propri di dominio).
- `commesse_attivita.sorgente_uid` (hash md5, caveat C1) — meccanismo interno commesse.
- Il ramo COMMESSA di `vw_stato_sorgente` (19 righe di `pratiche_sorgenti` oggi non
  risolvono perché **manca il ramo**, non per chiave sbagliata) → §5.

## 5. Reperto collaterale (registrato, non in questo brief)

Le 19 righe COMMESSA di `pratiche_sorgenti` sono a chiave **giusta** (`id::text`) ma non
risolvono: `script.vw_stato_sorgente` non ha (ancora) il ramo commessa. Dopo il 6b della
slice fatturazione i rami sono sei; il settimo (COMMESSA, catalogo `config.stati_commessa`)
è il naturale completamento. Piccolo, indipendente, stessa forma dei gemelli: candidarlo
alla prima slice utile.

---

*Redatto 2026-07-18 (sessione slice fatturazione DDT/resi, step 6b). Tutti i numeri e i
comportamenti citati sono stati verificati sul DB di sviluppo in quella data: prima di
evadere, ripetere il censimento §1c — i dati saranno cambiati.*
