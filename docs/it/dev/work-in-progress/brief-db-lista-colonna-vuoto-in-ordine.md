# Brief DB — Dove va il vuoto quando una lista ordina: si dichiara in `ui.lista_colonna`

## ⏭️ Chi riparte — 2026-11-24 (team BE/FE, apertura)

**Riparte: la sessione DB**, con la proposta di §4 (la colonna nuova, il seed delle 13 colonne di §3.1, le correzioni di
testo di §3.2, il COMMENT, il pgTAP).
Poi il team BE/FE con le ricadute di §5, che **aspettano l'apply**: fino ad allora il BE resta com'è, con i `COALESCE`
scritti a mano nelle whitelist. Decisioni di Tid prese il 2026-11-24 (§2). Una domanda aperta per la sessione DB (§6).

| # | Chi | Che cosa | Dove | Aspetta |
|---|---|---|---|---|
| 1 | Sessione DB | La colonna nuova, il seed delle 13 righe, le correzioni di testo, COMMENT, pgTAP; risposta a §6 | §3, §4, §6 | — |
| 2 | Tid | Apply | — | 1 |
| 3 | Team BE/FE | Le ricadute: `sql_order_direction`, lettura dal catalogo, ritiro dei `COALESCE`, presidio | §5 | 2 |

Decisioni aperte di Tid: nessuna (la domanda di §6 la porta la sessione DB, se serve). Da committare: questo brief.

**Brief vicini verificati** (2026-11-24): `brief-db-revisione-ui` tocca lo schema `ui` (documentazione, difetti, metadati) ed è alla chiusura; non tratta l'ordinamento delle liste né `ui.lista_colonna` come sede di una regola di ordinamento: non basta, e non va fuso. Nessun altro brief aperto su ordinamento, `NULLS` o `COALESCE` di whitelist.
**Guide verificate** (`guide_coinvolte.py --oggetti ui.lista_colonna`): [configurazione-liste.md](../../guide/configurazione-liste.md) — coerente (non descrive dove va il vuoto quando una lista ordina); dopo l'apply è **guida indietro** e si aggiorna (§4, punto 6).

---

## 1. Il problema

Quando una lista ordina per una colonna che ha righe vuote, qualcuno deve decidere dove vanno i vuoti. Oggi lo decidono
due regole, entrambe nel BE:

- **la regola generale**: il vuoto vale come il **minimo** (`sql_order_direction`: `ASC NULLS FIRST` /
  `DESC NULLS LAST`, decisione di Tid del 2026-07-19). È il caso del «non ancora»: il numero di una bozza, una data di
  evasione che non è ancora arrivata;
- **l'eccezione**: su una fine validità il vuoto vuol dire «non scade mai», quindi vale come il **massimo**. È scritta a
  mano dentro le whitelist di ordinamento, come `COALESCE(col, 'infinity'::date)` (decisione di Tid del 2026-08-01).

L'eccezione è un **fatto della colonna** (cosa vuol dire il vuoto lì), ma sta nel codice delle query. Si vede dove
diverge (§3.1): quattro colonne in cui il vuoto vuol dire «non scade» non hanno il `COALESCE` nella whitelist, quindi i
loro vuoti vanno ordinati come il minimo, cioè al contrario di quello che vogliono dire.

## 2. Le decisioni di Tid (2026-11-24)

1. **Il default resta il minimo.** Il vuoto è «non ancora» quasi sempre.
2. **L'eccezione «vuoto = massimo» si dichiara nel catalogo, in `ui.lista_colonna`**, al posto dei `COALESCE` scritti a
   mano nel BE. Il BE la legge e la applica da sé.
3. Fuori da questo brief, stesso giorno: la regola «le date partono decrescenti» è ritirata, nel FE e nel BE
   (`colonne_desc` / `e_chiave_data`). Non tocca il DB, ma spiega perché qui si parla solo di **dove va il vuoto** e non
   del verso di partenza.

## 3. Le colonne da dichiarare (censimento del 2026-11-24)

Il censimento serve a trovare le divergenze, non a decidere la regola: la regola è quella di §2 e vale per ogni colonna
in cui il vuoto vuol dire «non finisce». Per ogni colonna si è verificato sul DB (2026-11-24) che la colonna di origine
può essere vuota, e il significato del vuoto dal COMMENT della colonna, dall'etichetta del catalogo o dal modello.

### 3.1 Il seed: `true` su queste 13 righe di `ui.lista_colonna`

| `lista_colonna.id` | Lista | `campo_sorgente` | Colonna di origine | Il vuoto vuol dire | Oggi nel BE |
|---|---|---|---|---|---|
| 45 | `vendite.contratti` | `valido_al` | `vendite.contratti.valido_al` | contratto senza scadenza | `COALESCE` ✅ |
| 67 | `vendite.preventivi` | `validita_al` | `vendite.preventivi.validita_al` | «NULL non scade mai» (`script.fn_check_preventivo_accettabile`) | `COALESCE` ✅ |
| 87 | `vendite.offerte` | `validita_al` | `vendite.offerte_commerciali.validita_al` | come il preventivo | `COALESCE` ✅ |
| 1154 | `vendite.listini_versioni` | `valido_al` | `vendite.listini_versioni.valido_al` | versione aperta (etichetta) | ❌ **divergenza** |
| 1053 | `catalogo.articolo_componenti` | `valido_al` | `catalogo.articoli_componenti.valido_al` | componente senza fine | `COALESCE` ✅ |
| 297 | `catalogo.conversioni_uom` | `valido_al` | `catalogo.unita_misura_conversioni.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 376 | `anagrafiche.categorie_clienti_listini` | `valido_al` | `anagrafiche.categorie_clienti_listini.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 343 | `anagrafiche.operatori` | `valido_al` | `anagrafiche.risorse_umane.valido_al` | identità senza scadenza (etichetta) | `COALESCE` ✅ |
| 246 | `config.tipi_ruolo_tipi_indirizzo` | `valido_al` | `config.tipi_ruolo_tipi_indirizzo.valido_al` | regola senza fine | `COALESCE` ✅ |
| 974 | `documenti.template_versioni` | `valido_al` | `documenti.template_documenti_versioni.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 924 | `magazzino.lotti` | `data_scadenza` | `magazzino.lotti.data_scadenza` | «NULL = non scade» (COMMENT) | ❌ **divergenza** |
| 957 | `pratiche.flussi` | `data_scadenza` | `pratiche.flussi.data_scadenza` | nessuna scadenza (etichetta) | ❌ **divergenza** |
| 255 | `pratiche.pratiche` | `data_scadenza` | `pratiche.pratiche.data_scadenza` | nessuna scadenza prevista | ❌ **divergenza** |

⚠️ La sessione DB verifica la colonna di origine nella vista della lista, se la vista la riprende da un'altra tabella:
qui è indicata la tabella che la scrive.

### 3.2 Correzioni di testo che il censimento ha trovato

- **`pratiche.pratiche.data_scadenza` e `pratiche.flussi.data_scadenza`**: il COMMENT dice solo «Scadenza prevista»
  e non dice cosa vuol dire il vuoto. Va scritto («NULL = nessuna scadenza»), come in `magazzino.lotti`.
- **`vendite.promo_articoli` (riga 304)**: l'etichetta estesa dice «vuoto significa senza scadenza», ma
  `vendite.promo_articoli.valido_al` è **NOT NULL**. L'etichetta va corretta, e la riga **non** si dichiara.

### 3.3 Esclusi, e perché

- **Le scadenze delle rate** (`pagamenti.rate` 754, `pagamenti.rate_fuori_capienza` 597, `pagamenti.distinta_righe`
  775): vengono da `vendite.fatture_scadenze.data_scadenza`, che è NOT NULL. Il vuoto non c'è.
- **Le inizio validità** (`*_dal`): il vuoto vuol dire «da sempre», cioè il minimo, che è già il default. Due whitelist
  del BE hanno `COALESCE(col, '-infinity'::date)` e danno lo stesso ordine del default: il BE li toglie, senza
  dichiarazione.

### 3.4 Fuori dal seed: il BE ordina, ma il catalogo non ha la colonna

- **Gli asset documentali** (`documenti.template_asset`): la whitelist del BE ordina per `valido_al` con il `COALESCE`
  (`ASSET_ORDER_COLUMNS` in `documenti_repository.py`), ma la lista di catalogo non ha la colonna, quindi il FE non la
  può chiedere. Il team BE la toglie dalla whitelist. Se Tid vuole la colonna a video, la sessione DB la aggiunge al
  catalogo con la dichiarazione a `true` (`documenti.template_asset.valido_al`: «NULL = senza fine», dal COMMENT).
- **I giorni rimanenti dei listini** (`giorni_rimanenti`, il vuoto è «non in scadenza», oggi `2147483647` in
  `listini_repository.py`): non sono una colonna del catalogo. Il team BE ne fa il censimento con le ricadute di §5.

## 4. La richiesta alla sessione DB

1. **Una colonna nuova in `ui.lista_colonna`** che dice dove va il vuoto quando la lista ordina per quella colonna.
   Proposta: `vuoto_ordinato_come_massimo boolean NOT NULL DEFAULT false` (`false` = il default, il minimo). La forma
   (boolean o vocabolario) e il nome li decide la sessione DB secondo le linee guida. Il default deve essere il minimo:
   le colonne che non dicono niente restano come oggi.
2. **Il seed**: `true` sulle 13 righe di §3.1; le correzioni di testo di §3.2.
3. **Il COMMENT** della colonna: cosa vuol dire, e che vale per l'ordinamento della lista, non per i filtri.
4. **Il pgTAP**: il default, il vincolo se ce n'è uno (per esempio: la dichiarazione ha senso solo su una colonna
   ordinabile), e le righe del seed.
5. **Dove il BE la legge**: la superficie di lettura che il BE usa per il catalogo delle colonne
   (`UiRepository.list_colonne_by_codice`, o `ui.fn_resolve_lista_config` se la sessione DB preferisce esporla da lì).
   Il brief dice quale, così il BE la legge da un posto solo.
6. Aggiornare la guida [configurazione-liste.md](../../guide/configurazione-liste.md) e la pagina `manual/` della
   tabella, se c'è.

## 5. Le ricadute sul BE (team BE/FE, dopo l'apply)

Le fa il team BE/FE, su `dev/backend-tid`, dopo l'apply. La sessione DB non tocca `backend/`.

1. `sql_order_direction` impara il caso «vuoto = massimo»: `ASC NULLS LAST` / `DESC NULLS FIRST`. Così vale per ogni
   tipo, senza `COALESCE` e senza un valore «infinito» per tipo.
2. `sql_order_clause` riceve dal catalogo, per la lista che ordina, l'insieme delle colonne dichiarate. Le view
   dichiarano già il loro `lista_codice`: la lettura passa di lì.
3. Si tolgono i `COALESCE(…, 'infinity')` e `COALESCE(…, '-infinity')` dalle whitelist e il valore
   `_SQL_GIORNI_SENZA_SCADENZA`, con i test che li asseriscono. Restano solo dove non sono ordinamento di lista (per
   esempio il filtro «non scaduto» in `pagamenti_repository.py`, che è un `WHERE`).
4. Un presidio: una colonna dichiarata nel catalogo e ordinata dal BE senza la dichiarazione è rossa.

⚠️ Una lista che il BE ordina **senza** catalogo (nessuna riga in `ui.lista_definizione`) non può leggere la
dichiarazione. Il team BE ne fa il censimento quando scrive il punto 2, e porta a Tid i casi che restano.

## 6. Domanda aperta per la sessione DB

Va bene che la dichiarazione stia sulla **colonna della lista** (`ui.lista_colonna`) e non sulla **colonna della
tabella** (un COMMENT o un metadato sullo schema di dominio)? Il significato del vuoto è del dato, e la stessa colonna
compare in più liste: con la dichiarazione per lista, due liste dello stesso dato potrebbero dichiarare due cose
diverse. Tid ha scelto `ui.lista_colonna`. Se la sessione DB vede un motivo di modello per l'altra sede, lo porta a Tid
prima di scrivere.
