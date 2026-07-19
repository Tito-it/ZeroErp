# Brief — Radici i18n uniformi: perimetro globale e migrazione

> **Tipo**: brief trasversale (DB + FE) · **Target**: `dev/db-tid` + `dev/backend-tid`
> · **Data**: 2026-07-19 · **Owner**: Tid · **Priorità**: 🟡 MEDIA (nessun dato a
> rischio; disordine strutturale che genera difetti silenziosi)
> **Stato**: ✅ **CHIUSO** (2026-07-19) — migrazione completa end-to-end:
> 21 radici piatte spostate sotto le rispettive aree (FE `2972ff393`, metà DB
> `77d4b6b24`), radici morte `profile`/`lista` rimosse, guard `--strict-roots`
> completamente pulito, parità it/en integra, build verde. Standard vigente in
> [i18n-namespace-radici.md](../frontend/i18n-namespace-radici.md).
> **Origine**: analisi critica di
> [brief-db-i18n-namespace-reason-ordini.md](brief-db-i18n-namespace-reason-ordini.md).
> Correggendo le reason del push ordini è emerso che il difetto non era locale:
> l'archivio i18n ha **due stili di sistemazione conviventi**, e la scelta fra i
> due era stata lasciata al caso. Deciso di disegnare il perimetro **globale**
> per non avere ripensamenti futuri.
> **Regola vigente (fonte canonica)**: [frontend-standards.md §Multilingua](../frontend/frontend-standards.md#struttura-chiavi--radici-dei-namespace)
> — lettura obbligatoria di progetto; l'approfondimento (procedura, inventario)
> è in [i18n-namespace-radici.md](../frontend/i18n-namespace-radici.md). Questo
> brief è solo l'ordine di lavoro che ha portato a quella regola: archiviato in
> work-done, **non** è la fonte della regola.

## 1. Il problema in breve

Le frasi mostrate all'utente stanno in un archivio (`locales/{it,en}.json`) e il
codice ne conosce solo l'indirizzo. Il database **emette** questi indirizzi, il
frontend li risolve. Se l'indirizzo non esiste, il frontend non mostra un errore:
non mostra nulla — l'errore è **invisibile**.

Oggi l'archivio ha **60 radici in cima** e due stili conviventi:

- raggruppato per area — `vendite.ordini.*`, `vendite.ddt.*`
- piatto per modulo — `preventivi.*`, `contratti.*`, `listini.*`, `clienti.*`

Nessuno dei due è sbagliato in sé; è **averli entrambi** che lo è, perché chi
scrive un pezzo nuovo non sa quale imitare. È esattamente così che è nato il
difetto delle reason ordini: emesse come `ordini.*` (stile piatto) mentre per
quel modulo l'archivio aveva già scelto lo stile raggruppato — banner muto per
un mese e mezzo.

**Direzione scelta: raggruppato per area.** Le motivazioni di merito stanno in
[i18n-namespace-radici.md](../frontend/i18n-namespace-radici.md) §1–2. La scelta
**non è stata fatta sul volume di lavoro**: il volume decide l'ordine di
esecuzione (§5), mai quale forma sia giusta.

### 1a. Non è la prima volta — ed è questo che rende il brief necessario

Lo stesso difetto, nella stessa identica forma, è già stato riparato in passato:
`work-done/addendum-db-stati-doc-offerte-transizioni-label-key.md` documenta le
**offerte** che emettevano `offerte.azione_emetti` mentre il frontend aveva
`vendite.offerte.*` — chiave non risolta, azione muta. Fu corretto sia nel seed
CSV sia nelle `label_key` hardcoded della capability. Poi è toccato agli
**ordini**, che è il caso da cui nasce questo brief.

Due riparazioni identiche a distanza di mesi, e in mezzo **nessuno ha toccato la
convenzione documentata**. Il motivo per cui il difetto torna è che gli standard
la descrivono al contrario:

- `frontend-standards.md` §Multilingua, tabella «Struttura chiavi»
- `work-in-progress/frontend/guida-sviluppo-frontend.md` §10, tabella «Convenzioni chiavi»

Entrambe elencano `soggetti.*`, `indirizzi.*`, `geo.*`, `amm.*` come «etichette
dominio-specifiche» — **sanciscono lo stile piatto** — e nessuna delle due nomina
`vendite.*`, che è la radice più popolosa dell'archivio con 619 stringhe. Chi ha
scritto `ordini.push_commessa_reason.*` stava, a rigore, **seguendo la
documentazione**.

Conseguenza operativa: correggere le due tabelle non è un contorno del brief, è
**la parte che impedisce la quarta occorrenza**. Va fatta insieme allo standard
(step 2 di §5), prima di qualunque spostamento di stringhe.

## 2. Inventario globale (misurato 2026-07-19 su `42214e842`)

60 radici, **3273 stringhe** per lingua, parità it/en completa (nessuna chiave
orfana fra le due lingue). Verdetti dalla procedura di §3 dello standard:

| verdetto | radici | stringhe | usi FE | emissioni DB | righe seed |
| --- | ---: | ---: | ---: | ---: | ---: |
| **SPOSTA** (dominio in radice piatta) | 21 | 1424 | 1433 | 8 | 19 |
| **AREA** (già corretta) | 8 | 1283 | 1521 | 160 | 32 |
| **TRASVERSALE** (resta in cima) | 27 | 740 | 1096 | 7 | 7 |
| **DECIDERE** (proprietà contesa) | 2 | 22 | 42 | 0 | 0 |
| **MORTA** (nessun consumatore) | 2 | 6 | 0 | 0 | 0 |

### 2a. Da spostare, per area di destinazione

| area | moduli | stringhe | usi FE |
| --- | ---: | ---: | ---: |
| `vendite` | 9 | 715 | 624 |
| `amministrazione` | 3 | 365 | 447 |
| `anagrafiche` | 6 | 201 | 201 |
| `ui` | 1 | 108 | 123 |
| `config` | 2 | 35 | 38 |

Dettaglio (stringhe · usi FE · emissioni DB · righe seed):

- **vendite**: `contratti` (215·176·0·7), `preventivi` (183·153·8·12),
  `listini` (159·168), `dashboard_competenza` (42·39), `dash_comune` (25·3),
  `dashboard_backlog` (24·23), `approvazioni_prezzo` (23·21),
  `situazione_aperta` (23·24), `lineage` (21·17)
- **amministrazione**: `amm` (172·188), `definizioni_workflow` (111·183),
  `amm_emittenti_fiscali` (82·76)
- **anagrafiche**: `clienti` (68·56), `fornitori` (49·38), `conti_bancari` (28·32),
  `indirizzo_soggetto` (22·24), `soggetti` (19·20), `contatto` (15·31)
- **ui**: `ui_admin` (108·123)
- **config**: `impostazioni` (33·36), `config_documenti` (2·2)

Applicando le regole di nome (§4 dello standard) le tre radici di amministrazione
confluiscono in `amministrazione.*` con foglia non ridondante:
`amm_emittenti_fiscali` → `amministrazione.emittenti_fiscali`,
`ui_admin` → `ui.admin`, `config_documenti` → `config.documenti`.

### 2b. Già corrette — non toccare

`vendite` (619), `catalogo` (171), `pratiche` (169), `amministrazione` (105),
`config` (94), `portale` (54), `documenti` (45), `shop` (26).

### 2c. Trasversali — restano in cima

`common` (109), `indirizzi` (59), `auth` (49), `nav_menu` (41), `geo` (31),
`search` (31), `lista_config` (25), `nav` (24), `note` (24), `sessions` (21),
`dati_societari` (17), `placeholder` (17), `ai` (12), `config_panel` (11),
`tabs` (11), `resolver` (13), `istanza_utility` (8), `billing_account` (7),
`errors` (6), `home` (6), `export_dialog` (5), `soggetto_ruolo_lookup` (5),
`confirm` (4), `dash_mesi` (4), `context` (3), `pagination` (3),
`validation` (2), `actions` (1).

⚠️ `indirizzi` resta in cima **pur esistendo** `vendite.indirizzi`: sono due
concetti diversi e la coesistenza è corretta (standard §3). Non unificarle.

### 2d. Da decidere in fase di esecuzione

- `notifications` (11·26): `ui/` al 64% dei file di dominio — sotto la soglia del
  70%. Verificare se i 5 file di `amministrazione` usano lo stesso vocabolario o
  uno proprio; nel primo caso è trasversale, nel secondo va a `ui.notifications`.
- `amm` (172·188): la dominanza è netta (95%), ma va confermato che le 172
  stringhe non contengano vocabolario già presente in `amministrazione.*`, per
  non creare doppioni nella fusione.

### 2e. Radici morte — con un'avvertenza

`lista` (3 stringhe) e `profile` (3 stringhe) hanno **zero** consumatori nel
codice.

⚠️ `lista` **non va cancellata e basta**: `sviluppo-personalizzazioni-liste_def.md`
la tiene fra le «decisioni operative aperte» come radice per le etichette di
colonna delle liste configurabili (`lista.{codice}.col_*`). È una radice piatta
di dominio **ancora da nascere**: se quella decisione si chiudesse così,
creerebbe oggi il difetto che questo brief sta rimuovendo. Va risolta applicando
lo standard — le etichette di colonna appartengono al modulo che possiede la
lista, quindi `vendite.contratti.col_*`, oppure si riusano le chiavi esistenti —
e solo dopo si rimuove la radice.

`profile` invece è morta senza vincoli: si cancella.

### 2f. Consumatore futuro da allineare

`configurazione-liste.md` §12.8 (DEF-9, ancora da fare) prevede un'API
`GET /api/v1/core/i18n/keys?prefix=...` che offre le chiavi esistenti in
autocomplete nel drawer colonna. È il posto naturale dove **far rispettare** lo
standard invece di limitarsi a documentarlo: l'autocomplete non dovrebbe
proporre radici piatte di dominio. Da tenere presente quando quell'item verrà
sviluppato, e da rifare i conti se la migrazione avviene dopo.

## 3. I quattro fronti di ogni spostamento

Una rinomina non è un'operazione solo frontend. Per ciascun modulo:

1. **Locales** — `it.json` e `en.json`, stesse foglie sotto la nuova radice.
2. **Punti di chiamata FE** — `$t()`/`te()` nei `.vue`/`.js`.
3. **Capability DB** — `label_key`/`reason_key` in `script.fn_available_actions_*`:
   corpo preso dalla doc auto-gen, mai dallo YAML (standard §5).
4. **Seed `80_data`** — `label_key` dentro il `meta` jsonb delle
   `config.transizioni_stati_*`: si edita il CSV, che i loader `runOnChange`
   ripescano; **non** si crea un loader nuovo.

Oggi i fronti 3 e 4 riguardano solo `preventivi` (8 emissioni + 12 righe seed) e
`contratti` (7 righe seed). Tutti gli altri moduli sono FE-only.

## 3a. Chi fa cosa — non è lavoro BE/FE

Ripartizione per livello, contro-intuitiva e quindi da fissare:

| livello | cosa gli spetta |
| --- | --- |
| **Backend** | **nulla.** Nessun modulo Python confronta o costruisce chiavi i18n: il backend le trasporta opache dentro l'envelope della capability. L'unico riscontro in `backend/` è un fixture di test con `can_push_commessa_reason: None`, che è un valore, non una chiave. |
| **Frontend** | il grosso: locales `it/en` e punti di chiamata `$t()`/`te()` per **21 radici**, più il guard automatico di §4. |
| **Database** | la parte che si tende a dimenticare: `label_key`/`reason_key` nelle capability e nel `meta` dei seed `config.transizioni_stati_*`. Riguarda **`preventivi`** (8 emissioni in `fn_available_actions_preventivo` + 12 righe di seed) e **`contratti`** (7 righe di seed). |

Quindi no: **non è materia che BE/FE possano chiudere da soli** — i due moduli
sopra hanno una metà che nasce nel database.

**Sull'ordine fra le due metà (contesto attuale: nessuna produzione).** In un
sistema in esercizio le due metà dovrebbero atterrare insieme, perché nella
finestra intermedia il messaggio sparirebbe senza errore. Qui **non è un
vincolo**: non c'è produzione, gli aggiornamenti sono controllati da una sola
persona e una rottura temporanea è accettabile. Il costo di sincronizzare (due
mezzi interventi coordinati, doppia verifica) è più alto del danno che evita.
Si procede quindi **senza coordinamento**, in un passaggio unico per fronte.

## 4. Verifica

- **Guard FE**: script che confronta le chiavi citate nel codice con quelle
  presenti nei locales e fallisce sulle mancanti. È il controllo che avrebbe
  intercettato il difetto ordini il giorno stesso.
- **pgTAP**: asserzione sul prefisso delle chiavi emesse dalle capability
  (es. `can_push_commessa_reason_key` di un ordine inizia per `vendite.ordini.`).
- **Parità it/en**: oggi è perfetta; va verificata di nuovo a fine migrazione.

## 5. Ordine di esecuzione — ottimizzato per sviluppo

**Premessa che determina il piano**: niente produzione, aggiornamenti
controllati da una sola persona, rottura temporanea accettabile. Cadono quindi i
due accorgimenti che servirebbero in esercizio — sincronizzare DB e FE (§3a) e
procedere un'area per volta — perché entrambi comprano sicurezza pagandola in
**passaggi ripetuti** sullo stesso materiale. Il criterio qui è l'opposto:
**toccare ogni file una volta sola**.

1. ✅ **Fix ordini** — fatto (`20260719-12`, pgTAP 9/9).
2. **Guard FE, per primo.** Lo script che confronta chiavi citate e chiavi
   presenti va scritto **prima** della migrazione, non dopo: è ciò che sostituisce
   il coordinamento. Con il guard, una rinomina sbagliata smette di essere un
   messaggio muto da scoprire per caso e diventa una lista di chiavi rotte in
   dieci secondi. È l'unico investimento che *accelera* invece di rallentare.
3. **Rinomina in un colpo solo, e scriptata.** Tutte e 21 le radici insieme —
   locales (spostamento di sottoalbero in `it.json`/`en.json`) e punti di chiamata
   (`'<radice>.` → `'<area>.<radice>.` nelle posizioni di chiave) — con uno
   script, non a mano. Sono 1433 punti di chiamata: farli a mano, per area, in
   cinque tornate, significa cinque riletture degli stessi file e cinque
   occasioni di errore diverso. Fatto meccanicamente è un'operazione sola e
   ripetibile. ⚠️ Lo script deve riconoscere le **posizioni di chiave**
   (`t(`/`$t(`/`te(`, `label_key`, `reason_key`) e non sostituire alla cieca ogni
   occorrenza del testo, altrimenti tocca rotte, path e variabili omonime.
4. **Metà DB nello stesso giro** — `preventivi` (capability + seed) e `contratti`
   (seed), senza attendere il frontend: nella finestra intermedia al massimo
   sparisce un messaggio, ed è accettabile.
5. **Una sola verifica finale** — guard FE + pgTAP + build + parità it/en (§4),
   eseguiti una volta sul risultato completo invece che dopo ogni area.
6. **Un solo giro di chiusura** — rigenerazione doc auto-gen, radici morte (§2e),
   casi contesi (§2d), commit.

**Standard e tabelle superate**: già scritti e già corretti in repo, non sono più
uno step da pianificare. Servivano a impedire che nascessero chiavi piatte
durante una migrazione lunga; con la migrazione compressa in un giro solo, il
loro valore si sposta sul dopo — restano la regola per il codice futuro.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Fix reason ordini → `vendite.ordini.*` | ✅ 2026-07-19 (`20260719-12`, pgTAP 9/9) |
| 2 | Standard scritto + tabelle superate corrette in repo | ✅ 2026-07-19 |
| 3 | Guard FE chiavi-citate vs chiavi-presenti (**prima** della rinomina) | ✅ `scripts/check_i18n_keys.py` operativo (esteso a seed CSV + doc auto-gen) |
| 4 | Rinomina scriptata di tutte e 21 le radici — locales + punti di chiamata | ✅ FE `2972ff393` (1413 rinomine, radici sotto `vendite.*`/aree) |
| 5 | Metà DB: `preventivi` (capability `20260719-14` + seed) e `contratti` (seed) | ✅ applicato + verificato sul DB vivo (`77d4b6b24`) |
| 6 | Verifica: pgTAP `plan(8)` verde, seed+capability live corretti (psql), parità it/en | ✅ guard verde su FE **e** DB dopo rigen doc auto-gen |
| 7 | Chiusura: `profile`/`lista` rimossi (radici morte) + guard irrobustito, casi §2d/§2e/§2f | ✅ 2026-07-19 |

### 6a. Stato metà DB (step 5) — dettaglio

- **Seed** `transizioni_stati_preventivi.csv` (4 `label_key`, `preventivi.azione_*`
  → `vendite.preventivi.azione_*`) e `transizioni_stati_contratti.csv` (3,
  `contratti.azione_*` → `vendite.contratti.azione_*`): editati **direttamente**,
  ripescati dai loader `runOnChange` esistenti. Guard già pulito su queste 7.
- **Capability** `fn_available_actions_preventivo`: changeset `20260719-14`,
  3 `label_key` + 5 `reason_key` → `vendite.preventivi.*`. Corpo dalla doc
  auto-gen, diff verificato (8 chiavi + commento + `COMMENT`, nessuna regressione
  su residuo/requires_righe). Il guard segnala ancora queste 8 perché legge la
  doc auto-gen, che riflette il vivo: si azzerano al migrate + rigen.
- **pgTAP** `test-fn-available-actions-preventivo-v1.sql`: `plan(7)` → `plan(8)`.
  Test 4 adattato (leggeva `preventivi.azione_annulla` dal seed, ora
  `vendite.preventivi.*`); test 8 nuovo, guard di prefisso su label_key (seed) +
  reason_key (capability).
- ⚠️ **`contratti` capability**: nessuna funzione emette `contratti.*` a runtime
  oltre al seed (le sue `reason_key`/`label_key` vivono solo nel `meta` delle
  transizioni). Verificato col guard: dopo l'edit del CSV non resta nessuna
  chiave `contratti.*` irrisolvibile. Niente changeset capability per contratti.

### 6b. Chiusura (step 7) — radici morte e casi §2d/§2e/§2f

- **§2e radici morte**: `profile.*` (3 stringhe, ruoli+«no company») e `lista.*`
  (3 col_*) rimosse da `it.json`/`en.json` — zero consumatori, statici e
  dinamici (il `portale.profile.*`, vivo, è namespace diverso e resta). Le due
  radici sono state **tolte anche dalla whitelist `TRASVERSALI` del guard**: la
  loro assenza fa sì che una futura reintroduzione venga segnalata come radice
  di dominio in cima.
- **§2e decisione `lista`**: la domanda aperta in
  [sviluppo-personalizzazioni-liste_def.md](../work-in-progress/sviluppo-personalizzazioni-liste_def.md)
  («etichette colonna: riusare chiavi esistenti o creare `lista.{codice}.col_*`?»)
  è **risolta in favore delle radici d'area**: le etichette di colonna
  appartengono al modulo che possiede la lista (`vendite.<modulo>.col_*`) o
  riusano chiavi esistenti; `lista.*` piatto non si crea. Recepito in quel doc.
- **§2d casi contesi**: risolti in esecuzione — `amm → amministrazione` fuso
  senza collisioni (172+105 foglie), `notifications` resta trasversale.
- **§2f consumatore futuro** (API `GET …/i18n/keys?prefix=` per l'autocomplete
  colonne, DEF-9): nessuna azione ora; quando verrà sviluppato, l'autocomplete
  non deve proporre radici piatte di dominio (è il punto dove far *rispettare*
  lo standard, non solo documentarlo).

## 7. Riferimenti

- Regola canonica: [frontend-standards.md §Multilingua](../frontend/frontend-standards.md#struttura-chiavi--radici-dei-namespace) · approfondimento: [i18n-namespace-radici.md](../frontend/i18n-namespace-radici.md)
- Brief d'origine: [brief-db-i18n-namespace-reason-ordini.md](brief-db-i18n-namespace-reason-ordini.md)
- **Precedente identico già riparato** (offerte):
  `docs/it/dev/work-done/addendum-db-stati-doc-offerte-transizioni-label-key.md`
- Regole superate da correggere: `frontend-standards.md` §Multilingua ·
  `work-in-progress/frontend/guida-sviluppo-frontend.md` §10
- Companion della stessa famiglia: [brief-db-ddt-reason-push-catch-all.md](../work-in-progress/brief-db-ddt-reason-push-catch-all.md)
- Capability che emettono chiavi: `docs/it/dbzero/script/funzioni/fn_available_actions_{ordine,ddt,preventivo}.md`
- Seed toccati: `db/changelog/migrations_v2/80_data/sql/config/transizioni_stati_{preventivi,ordini,ddt}.csv`
