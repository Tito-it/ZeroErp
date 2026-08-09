# Brief DB→FE — Reason di offerte e preventivi che l'utente non vede mai

> **Tipo**: mini-brief DB con **azione richiesta al FE** · **Target**: `dev/db-tid` (DB)
> + `dev/backend-tid` (FE) · **Data**: 2026-07-19 · **Owner**: Tid
> · **Priorità**: 🟡 MEDIA (nessun dato errato: sono messaggi che non compaiono)
> **Stato**: ✅ **CHIUSO** (2026-07-19) — DB applicato e live, doc auto-gen
> rigenerata, 7 traduzioni it/en aggiunte, guard verde sul fronte DB. In più,
> **oltre il perimetro originale**: i drawer di offerte e preventivi sono stati
> cablati per *mostrare* davvero le reason (la premessa del §3 «i messaggi si
> accendono da soli» era falsa — `OffertaDrawer` non leggeva alcuna reason e il
> ramo `genera_ordine` dei preventivi non era reso; senza il cablaggio 5 delle 7
> traduzioni sarebbero rimaste mute). Vedi §7.
> **Origine**: primo giro del guard `scripts/check_i18n_keys.py`, scritto durante
> il fix delle reason ordini. Ha trovato **7 chiavi emesse dal DB che nei locales
> non esistono**: l'utente vede un pulsante disabilitato senza alcuna spiegazione.
> **Famiglia**: [brief-db-i18n-namespace-reason-ordini.md](brief-db-i18n-namespace-reason-ordini.md)
> (stesso difetto, ordini) · [brief-i18n-radici-uniformi.md](brief-i18n-radici-uniformi.md)
> (convenzione generale) · `work-done/addendum-db-stati-doc-offerte-transizioni-label-key.md`
> (stesso difetto, offerte, già riparato una volta a maggio).

## 1. Perché è invisibile

Il DB non manda il testo del messaggio: manda **l'indirizzo** della traduzione.
Se l'indirizzo non esiste, il frontend non segnala un errore — semplicemente non
scrive nulla. Il pulsante resta grigio e il motivo non compare. Nessun log,
nessuna spia: si scopre solo guardando la schermata e chiedendosi perché.

## 2. Sono DUE difetti diversi, con due proprietari diversi

⚠️ Non trattarli come un blocco unico: hanno cause e rimedi distinti.

### 2a. Offerte — namespace sbagliato (rimedio **DB**)

`script.fn_available_actions_offerta` emette 3 reason sotto la radice **`offerte.*`**,
che nei locales **non esiste**: l'i18n delle offerte vive sotto `vendite.offerte.*`.

| `reason` (codice, **non cambia**) | `reason_key` oggi | deve diventare |
| --- | --- | --- |
| `OFFERTA_CONTRATTO_GIA_GENERATO` | `offerte.push_reason.gia_generato` | `vendite.offerte.push_reason.gia_generato` |
| `OFFERTA_ORDINE_GIA_GENERATO` | `offerte.push_reason.ordine_gia_generato` | `vendite.offerte.push_reason.ordine_gia_generato` |
| `OFFERTA_NON_ACCETTATA` | `offerte.push_reason.non_accettata` | `vendite.offerte.push_reason.non_accettata` |

Le 3 chiavi compaiono in **6 assegnazioni**: ciascuna serve sia
`can_push_contratto_reason_key` sia `can_genera_ordine_reason_key`.

È **esattamente** il difetto degli ordini, e nella stessa forma interna: nello
stesso corpo le `azione_reason` usano già `vendite.offerte.azione_reason.*`
— namespace giusto — mentre le `push_reason` poche righe sotto usano `offerte.`.
È inoltre la **seconda volta** che le offerte inciampano qui: a maggio fu
riparato lo stesso difetto sulle `label_key` delle transizioni (addendum in
`work-done`), ma le `push_reason` non erano state guardate.

### 2b. Preventivi — traduzioni mai scritte (rimedio **FE**)

`script.fn_available_actions_preventivo` emette 4 reason il cui indirizzo è
**coerente con la convenzione attuale** del modulo: il difetto non è il
namespace, è che **la traduzione non è mai stata scritta**, in nessuna lingua.

| `reason_key` emessa | presente nei locales? |
| --- | --- |
| `preventivi.push_commessa_reason.non_accettato` | ✅ sì (l'unica) |
| `preventivi.push_commessa_reason.nessuna_riga` | ❌ no |
| `preventivi.push_commessa_reason.senza_billing_account` | ❌ no |
| `preventivi.genera_ordine_reason.non_accettato` | ❌ no |
| `preventivi.genera_ordine_reason.nessuna_riga` | ❌ no |

**Il DB qui non si tocca.** L'intervento è solo lato locales.

## 3. Cosa deve fare il FE

Sette chiavi da aggiungere in `it.json` **e** `en.json`. I testi sono proposte:
adattateli, purché dicano *perché* l'azione non è disponibile.

**Sotto `vendite.offerte.push_reason.*`** (nuovo sottoalbero, dopo il fix DB §2a):

- `gia_generato` — «Contratto già generato da questa offerta.»
- `ordine_gia_generato` — «Ordine già generato da questa offerta.»
- `non_accettata` — «Disponibile dopo l'accettazione dell'offerta.»

**Sotto `preventivi.*`** (radice attuale, vedi §4):

- `push_commessa_reason.nessuna_riga` — «Nessuna riga da inviare a commessa.»
- `push_commessa_reason.senza_billing_account` — «Manca il billing account: impostalo per inviare a commessa.»
- `genera_ordine_reason.non_accettato` — «La generazione dell'ordine sarà disponibile dopo l'accettazione del preventivo.»
- `genera_ordine_reason.nessuna_riga` — «Nessuna riga: aggiungi almeno una riga per generare l'ordine.»

Nessun altro adeguamento: i drawer leggono `can_*_reason_key` e sono già
data-driven, i messaggi si accendono da soli appena la chiave è risolvibile.

## 4. Perché i preventivi restano su radice piatta (e non è una svista)

`preventivi.*` è una radice piatta che
[brief-i18n-radici-uniformi.md](brief-i18n-radici-uniformi.md) prevede di
spostare sotto `vendite.preventivi.*` insieme alle altre 20. **Le 4 chiavi nuove
vanno scritte sotto la radice attuale**, non sotto quella futura: la migrazione
sposta l'intero sottoalbero con uno script, quindi nasceranno nel posto vecchio e
si sposteranno con le altre 183 senza un solo minuto di lavoro aggiuntivo.
Scriverle già sotto `vendite.preventivi.*` le renderebbe invece irrisolvibili
oggi — cioè ricreerebbe adesso il difetto che questo brief chiude.

Le offerte sono il caso opposto: `vendite.offerte.*` **è già** la destinazione
finale, quindi il fix DB di §2a è definitivo e non verrà ritoccato.

## 5. Avanzamento

| # | Step | Owner | Stato |
| --- | --- | --- | --- |
| 1 | 3 `reason_key` offerte → `vendite.offerte.push_reason.*` (6 assegnazioni) — changeset `20260719-13` | DB | ✅ applicato |
| 2 | pgTAP test 19 (prefisso reason_key), `plan(18)` → `plan(19)` | DB | ✅ applicato |
| 3 | Apply dev + rigen doc auto-gen | DB | ✅ live, doc rigenerata |
| 4 | 3 traduzioni offerte it/en (§3) | FE | ✅ |
| 5 | 4 traduzioni preventivi it/en (§3) | FE | ✅ |
| 6 | Riesecuzione `python3 scripts/check_i18n_keys.py` → 0 chiavi DB irrisolvibili | FE | ✅ verde |
| 7 | **Extra (§7)**: cablaggio drawer offerte/preventivi per rendere le reason | FE | ✅ |

## 7. Cablaggio drawer (extra, oltre il perimetro del brief)

Il §3 assumeva che bastassero le traduzioni perché «i drawer leggono
`can_*_reason_key` e sono già data-driven». **Falso, verificato in-app:**

- `OffertaDrawer.vue` non leggeva **nessuna** reason: né `can_push_contratto_reason_key`
  né `can_genera_ordine_reason_key`. Le 3 chiavi offerte sarebbero rimaste mute.
- `PreventiviDrawer.vue` mostrava solo il ramo `push_commessa`; il ramo gemello
  `genera_ordine` non era reso, quindi le 2 chiavi `genera_ordine_reason.*`
  sarebbero rimaste mute.

Solo le 2 `push_commessa_reason.*` dei preventivi avevano già un consumatore.
Cablati entrambi i drawer col pattern già in uso in Ordini/DDT (banner `<Message
severity="info">` sotto `DrawerActionsBar`, guardato da `te(key)`):

- `OffertaDrawer.vue`: computed `pushReasons` che unisce i due rami disabilitati
  con reason risolvibile, reso con `v-for`;
- `PreventiviDrawer.vue`: aggiunto il banner del ramo `genera_ordine`, speculare
  a quello `push_commessa` già presente.

Verifica: build Vite verde; guard `check_i18n_keys.py` con 0 chiavi DB irrisolvibili.

## 6. Riferimenti

- Guard che li ha trovati: `scripts/check_i18n_keys.py`
- Definizioni vive: `docs/it/dbzero/script/funzioni/fn_available_actions_{offerta,preventivo}.md`
- Convenzione: [i18n-namespace-radici.md](../frontend/i18n-namespace-radici.md)
- Consumatori FE: `frontend/src/vendite/offerte/` e `frontend/src/vendite/preventivi/`
  (drawer) + `frontend/src/locales/{it,en}.json`
