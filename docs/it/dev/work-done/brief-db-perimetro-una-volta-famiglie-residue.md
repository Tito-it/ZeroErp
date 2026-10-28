# Brief DB — Il perimetro una volta per istruzione: le famiglie che restano

## ⏭️ Chi riparte — aggiornato al 2026-10-21

✅ **Chiuso e archiviato il 2026-10-21. Nessuno riparte.** Tutti e cinque i giri applicati su dbdev, pgTAP verdi (Tid); il debito del presidio è a zero.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | P-1 = prima le tre righe «operatore», poi le altre famiglie; P-2 = tutte in questo brief; P-3 = risolutore a due valori (2026-10-21) | §4 | — |
| 1-bis | ✅ Tid | il via allo sviluppo (2026-10-21) | — | — |
| 2 | ✅ sessione DB | giro 1 scritto e provato in transazione: `20261021-24…-28`, sei pgTAP aggiornati | §5 | — |
| 2-bis | ✅ Tid | apply del giro 1 su dbdev, pgTAP verdi, nessuna regressione (2026-10-21) | §5.3 | 2 |
| 3 | ✅ sessione DB | giro 2, cliente portale: scritto e provato in transazione, `20261021-29…-32`, quattro pgTAP aggiornati | §6 | 2-bis |
| 3-bis | ✅ Tid | apply del giro 2 su dbdev; pgTAP verdi dopo la correzione delle tre regex del §6.4, nessuna regressione (2026-10-21) | §6.4 | 3 |
| 4 | ✅ sessione DB | giro 3, cliente (ordini e ricevute): scritto e provato in transazione, `20261021-33…-36`, un pgTAP nuovo e quattro aggiornati | §7 | 3-bis |
| 4-bis | ✅ Tid | apply del giro 3 su dbdev, pgTAP verdi (2026-10-21) | §7.4 | 4 |
| 5 | ✅ sessione DB | giro 4, shop e note di cliente e shop insieme: scritto e provato in transazione, `20261021-37…-40`, due pgTAP nuovi al posto di due ritirati, tre aggiornati | §8 | 4-bis |
| 5-bis | ✅ Tid | apply del giro 4 su dbdev, pgTAP verdi (2026-10-21) | §8.4 | 5 |
| 6 | ✅ sessione DB | giro 5, fornitore ed email: scritto e provato in transazione, `20261021-41…-43`, un pgTAP nuovo e quattro aggiornati. Debito del presidio a zero | §9 | 5-bis |
| 6-bis | ✅ Tid | apply del giro 5 su dbdev, pgTAP verdi (2026-10-21) | §9.4 | 6 |
| 7 | ✅ sessione DB | archiviazione: brief in `work-done/`, D36 chiuso nel registro, nota per il backend consegnata in chat a Tid (2026-10-21) | §9.6 | 6-bis |

Decisioni aperte di Tid: nessuna. Da committare (Tid): il brief archiviato, i changeSet dei giri 1-5, i pgTAP (due file cancellati al §8.3) e la doc dei §5.4, §6.6, §7.6, §8.6 e §9.5.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-18. **A chi:** Tid.
> **Origine:** il debito residuo di
> [brief-db-plancache-funzioni-con-query-incorporate](brief-db-plancache-funzioni-con-query-incorporate.md)
> (D-3b-2, §5quinquies), archiviato il 2026-10-18. Voce nel registro: **D36** di
> [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).
> **Ricadute BE/FE:** nessuna prevista.

## 1. Il difetto, sul modello

Una policy che chiede «chi guarda vede questa riga?» calcola una parte della risposta che **non
dipende dalla riga**: il perimetro di chi guarda (super admin, veste, whitelist, il cliente o il
fornitore della sessione). Se lo calcola dentro la funzione chiamata per riga, lo ricalcola a ogni
riga letta: costo per costruzione **righe lette × catena**.

Il brief d'origine l'ha curato per tutta la famiglia dell'**operatore** (ef_whitelist): il perimetro
in una sottoquery scalare non correlata, valutata una volta per istruzione, e per riga solo
l'appartenenza (`script.fn_scope_ef_perimetro`, `script.fn_resolve_emittente_fiscale_id`;
linee-guida-sql §10.3). Restano le policy elencate al §2.

## 2. Che cosa resta (censimento, dbdev, 2026-10-18)

Fatto datato, `pg_policies` su 310 policy:

| Funzione di scope nelle policy | Policy | Schemi | Famiglia |
| --- | --- | --- | --- |
| `fn_scope_ba_ownership_via_fattura` | 10 | vendite | cliente portale |
| `fn_scope_ba_ownership` | 5 | anagrafiche, vendite | cliente portale |
| `fn_scope_ba_ownership_via_fattura_sdi` | 1 | vendite | cliente portale |
| `fn_scope_cliente_ownership` | 3 | shop, vendite | cliente |
| `fn_scope_cliente_ownership_via_ordine` | 3 | vendite | cliente |
| `fn_scope_cliente_ownership_via_ordine_riga` | 2 | vendite | cliente |
| `fn_scope_shop_via_ordine` | 3 | vendite | shop |
| `fn_scope_shop_via_ordine_riga` | 2 | vendite | shop |
| `fn_scope_shop_via_ba` | 1 | anagrafiche | shop |
| `fn_scope_fornitore_ownership` | 2 | acquisti | fornitore portale |
| `fn_scope_email_ambito` | 2 | config | email |
| `fn_scope_note_cliente` | 1 | vendite | note |
| `fn_scope_note_shop` | 1 | vendite | note |
| `fn_scope_note_ef_whitelist` | 1 | vendite | note, **operatore** |
| `fn_scope_note_magazzino_ef_whitelist` | 1 | magazzino | note, **operatore** |
| `fn_scope_ef_whitelist_via_coppia` | 1 | anagrafiche | **operatore** |

⚠️ Le tre righe «operatore» sono della famiglia già curata, ma restano per riga:

* `fn_scope_note_ef_whitelist` e `fn_scope_note_magazzino_ef_whitelist` non hanno il prefisso
  `via_*`, quindi il test 5 del presidio `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1`
  **non le vede** (guarda gli adattatori `fn_scope_ef_whitelist_via_*`). Debito non dichiarato fino
  a oggi: dichiarato qui.
* `fn_scope_ef_whitelist_via_coppia` (`anagrafiche.istanze_dati_precontrattuali`): la chiave è una
  **coppia** di colonne (istanza, utility) e il risolutore prende un valore solo. È l'unico nome
  nell'elenco del debito del test 5.

## 3. La forma che c'è già

Dal brief d'origine, applicata e misurata: il perimetro in **una** sottoquery (due lo calcolano
due volte per istruzione e le letture di una riga pagano il doppio); l'emittente — qui: la cosa di
cui chiede la famiglia — risolto per riga da una funzione `SECURITY DEFINER` con una lettura per
chiave, senza rieseguire la policy del padre; presidio sul testo **e sul piano**. Ogni famiglia
porta una domanda sua (il cliente della riga, il billing account, l'ambito email), e prima di
scrivere va guardato se esiste già la funzione che risponde in forma di **insieme** (regola del 2:
per l'operatore c'era `script.fn_get_emittenti_scope_pk_ids`).

## 4. Decisioni attese

* **P-1** ✅ (Tid, 2026-10-21) — le tre righe «operatore» per prime, con la forma già pronta. Poi le
  altre famiglie.
  ⚠️ Le due `fn_scope_note_*` dell'operatore stanno anche nel perimetro del **lotto 3** di
  [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md) (V6, i codici di
  `target_tipo`). Non c'è conflitto, ma chi arriva per secondo riparte dal corpo della doc
  auto-generata, non dal proprio YAML. La nota è scritta anche in quel brief (2026-10-21, §5.4).
* **P-2** ✅ (Tid, 2026-10-21) — tutte le famiglie si curano **in questo brief**. Il lavoro DB si
  chiude per intero prima di passare ad altro: il progetto non è in produzione e conviene farlo in un
  colpo solo. La premessa dell'altra strada non regge: nessun brief WIP nomina le funzioni di scope
  di cliente, shop, fornitore o email (grep del 2026-10-21). Nessun cantiere le sta ridisegnando.
* **P-3** ✅ (Tid, 2026-10-21) — `via_coppia` passa da un **risolutore a due valori**: dalla coppia
  (istanza, utility) restituisce il billing account con una lettura per chiave, `SECURITY DEFINER`,
  senza rieseguire la policy di `anagrafiche.billing_account`. La policy prende la forma del BA
  (§10.3, ondata 2): `fn_scope_ef_perimetro((SELECT …sr_ids…), fn_get_ba_emittente_sr_id(<BA della coppia>))`.
  Nessuna colonna nuova. Motivo, sul contratto: la coppia è `NOT NULL` e porta la FK
  `fk_idp_billing_account_coppia` verso la UNIQUE `uq_billing_instance_utility`, quindi ogni riga ha
  esattamente un BA. Una colonna `billing_account_id` ripeterebbe un dato già determinato, con
  backfill, allineamento (vincolo e trigger) e una possibile ricaduta BE. Entra nel giro 1. Uscito
  dalla policy, `via_coppia` esce anche dall'elenco del debito del test 5.
  ⚠️ Il dubbio aperto al momento della decisione (il BA letto sotto RLS contro il risolutore
  `DEFINER`, che lo vede sempre) è chiuso al §5.2, sulla struttura e col caso costruito.

## 5. Giro 1 — le tre policy dell'operatore (2026-10-21)

Scritto e provato in transazione il 2026-10-21. ✅ **Applicato** su dbdev, pgTAP verdi e nessuna regressione (Tid, 2026-10-21).

### 5.1 I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `20261021-24` | nasce `script.fn_get_ba_id_da_coppia(istanza, utility)`: il BA della coppia, `SECURITY DEFINER`, una lettura per chiave (P-3) |
| `20261021-25` | nascono `script.fn_scope_note_ef_perimetro` e `fn_scope_note_magazzino_ef_perimetro`: gli smistatori dei padri delle note ricevono il perimetro e per riga risolvono l'emittente con lo stesso modo della partizione (P-1) |
| `20261021-26` | le tre policy: i due padri `vendite.note` e `magazzino.note` sugli smistatori nuovi, `istanze_dati_precontrattuali` nella forma del BA col BA della coppia |
| `20261021-27` | si ritirano `fn_scope_note_ef_whitelist`, `fn_scope_note_magazzino_ef_whitelist` e `fn_scope_ef_whitelist_via_coppia`: nessun altro lettore (funzioni, viste, policy, pgTAP, backend; censimento su `pg_get_functiondef`) |
| `20261021-28` | il modo `COPPIA` di `dbops.fn_storico_risolvi_scope` chiede il BA a `fn_get_ba_id_da_coppia`: era la **seconda copia** della stessa domanda (regola del 2), trovata censendo i lettori di `via_coppia` |

Le firme sono ancorate con `%TYPE`; dove non c'è una colonna (il perimetro `bigint[]`, `p_riga jsonb`,
`p_profondita`) il motivo è scritto accanto. `COST 5000` sulle tre funzioni nuove.

### 5.2 Perché le risposte non cambiano

* **Note**: il vecchio smistatore chiamava `via_<famiglia>(utente, id)` =
  `fn_check_user_emittente_scope(utente, fn_resolve_emittente_fiscale_id('<modo>', id))`. Il nuovo chiama
  `fn_scope_ef_perimetro(fn_get_emittenti_scope_pk_ids(utente), fn_resolve_emittente_fiscale_id('<modo>', id))`.
  Il controllo sull'emittente attivo che la canonica fa in più è già dentro il perimetro, che lo
  interseca. I modi sono quelli delle policy delle partizioni (`pg_policies`, 2026-10-21) e l'`ELSE false`
  resta, anche per il super admin.
* **Coppia**: per la veste OPERATORE l'unica policy di SELECT di `billing_account` è
  `rls_billing_account_ef_whitelist`, cioè la stessa domanda di `via_efba`. Il BA della coppia era
  visibile esattamente quando `via_efba` rispondeva `true`. Leggerlo `DEFINER` toglie la policy
  rieseguita, non cambia la risposta. Lo prova `rls/test-rls-istanze-dati-precontrattuali-v1` con la RLS
  del BA **forzata**: A vede il proprio cliente (4), non quello di B (5), non scrive sulla coppia di B (6).
* **Storico**: stessa lettura per chiave, e la funzione era già `DEFINER` dello stesso proprietario.
  I casi `COPPIA` (28-ter, 28-quater) di `dbops/test-storico-scope-policy-v1` restano verdi.

### 5.3 Le prove (scratch `zeroerp_ruoli`, come `zeroerp_owner`, 2026-10-21)

L'SQL estratto dai cinque YAML con le loro preCondition, in `BEGIN … ROLLBACK`: tutte le preCondition
vere, firme e risultato identici al vivo, una funzione per nome. Il rollback in ordine inverso riporta le
tre policy (md5 del testo) e `fn_storico_risolvi_scope` (md5 di corpo e COMMENT) **identici** a prima.
`plpgsql_check` sul corpo nuovo dello storico: nessun errore (gli avvisi sono quelli del corpo vivo).
Scratch verificato pulito dopo le prove.

I pgTAP, ciascuno senza e con l'SQL estratto in testa:

| pgTAP | Senza | Con |
| --- | --- | --- |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (aggiornato) | 4/5 | 5/5 |
| `rls/test-rls-note-padre` (aggiornato) | 8/9 | 9/9 |
| `rls/test-rls-magazzino-perimetro-v1` (aggiornato) | 11/12 | 12/12 |
| `rls/test-rls-istanze-dati-precontrattuali-v1` (commento) | 8/8 | 8/8 |
| `script/test-policy-funzioni-cost-v1` | 4/4 | 4/4 |
| `anagrafiche/test-istanza-nasce-col-ba-v1` (commento) | 13/13 | 13/13 |
| `anagrafiche/test-istanze-dati-precontrattuali` (commento) | 8/8 | 8/8 |
| `rls/test-rls-perimetro-scoperto` | 8/8 | 8/8 |
| `vendite/test-note-partitioning` | 23/23 | 23/23 |
| `anagrafiche/test-clienti-sync-utility-pdp-policy` | 14/14 | 14/14 |
| `dbops/test-storico-scope-policy-v1` | 36/36 | 36/36 |

I tre rossi «senza» sono attesi: sono i presidi aggiornati che vedono il difetto prima della cura.

Cosa cambia nei presidi:

* `test-scope-ef-perimetro-una-volta-per-istruzione-v1`: la «funzione di scope col perimetro» comprende
  gli smistatori delle note (test 1, 3, 4: le loro tabelle entrano anche nel controllo del **piano**).
  Il test 5 vede ora anche gli smistatori per riga (`fn_scope_note_*ef_whitelist`), e il suo debito
  dichiarato è a **zero**: prima le note non le vedeva, perché il loro nome non era `via_*`.
* `test-rls-note-padre` (4) e `test-rls-magazzino-perimetro-v1` (12): i rami contro il `CHECK` si leggono
  dagli smistatori nuovi. Nel primo uno smistatore mancante ora è **rosso** (`coalesce` sul sorgente):
  prima un nome sbagliato lo rendeva verde per sottrazione.

⚠️ Restano da fare dopo l'apply: la corsa **come app** (Tid) e la misura dei tempi, che dall'owner non si
prende. Il test 4 del presidio guarda il piano col `FORCE` acceso, quindi la forma è già provata.

### 5.4 Documentazione

* `linee-guida-sql.md` §10.3: la coppia e gli smistatori delle note nella forma col perimetro; il debito
  dichiarato non c'è più.
* `manual/`: nuove `fn_get_ba_id_da_coppia` e `fn_scope_note_magazzino_ef_perimetro`; cancellate
  quelle delle due ritirate (`fn_scope_note_magazzino_ef_whitelist`, `fn_scope_ef_whitelist_via_coppia`).
  Aggiornati i rimandi in sette pagine `via_*`, in `istanze_dati_precontrattuali` e in
  `fn_storico_risolvi_scope`. ⚠️ Le pagine auto-generate si allineano alla prossima rigenerazione.
* La nota per il lotto 3 è in [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md)
  §11.3 (le note), e la voce D36 del registro è aggiornata.

## 6. Giro 2 — il cliente portale (2026-10-21)

Scritto e provato in transazione il 2026-10-21. ✅ **Applicato** su dbdev, pgTAP verdi e nessuna regressione dopo la correzione del §6.4 (Tid, 2026-10-21).

### 6.1 Il disegno, che vale per tutte le famiglie di controparte

Le vesti di controparte (cliente portale, shop, fornitore) fanno tutte la **stessa** domanda: «la
riga è del mio soggetto?». Le loro funzioni di scope ricalcolavano a ogni riga la parte che non
dipende dalla riga: esiste l'identità, è nella veste giusta, è utilizzabile oggi
(`fn_veste_utilizzabile`, quattro tabelle). La forma è quella dell'operatore (§3), con tre building
block nuovi:

| Building block | Che cosa | Una volta / per riga |
| --- | --- | --- |
| `script.fn_get_identita_sr_perimetro(identità, vesti)` | il soggetto dell'identità, se è in una delle vesti ed è utilizzabile; `NULL` = **nessuno** | una volta per istruzione (sottoquery) |
| `script.fn_resolve_controparte_sr_id(modo, chiave)` | il soggetto della riga, `SECURITY DEFINER`: nessuna policy del padre rieseguita; un modo sconosciuto solleva | per riga |
| `script.fn_scope_sr_perimetro(perimetro, soggetto)` | il confronto, puro e incorporato | per riga, gratis |

⭐ La policy passa **la propria veste** al perimetro. Il middleware imposta
`app.ruolo_applicativo` e `app.current_identita_id` dalla stessa riga di `identita_digitali`
(`jwt_audit_authentication.py`), quindi le due coincidono. Un contesto incoerente non vede niente.
Il risolutore nasce con i modi del giro 2 (`billing_account`, `fattura`, `fattura_sdi`); ogni giro
aggiunge i suoi, come è successo con `fn_resolve_emittente_fiscale_id`.
⚠️ Prima di scrivere ho cercato un building block che desse il soggetto dell'identità in forma di
perimetro: non c'era (`fn_current_identita_context` legge i GUC, `fn_has_identita_attiva` parte
dalla credenziale).

### 6.2 I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `20261021-29` | nascono `fn_get_identita_sr_perimetro` e `fn_scope_sr_perimetro` |
| `20261021-30` | nasce `fn_resolve_controparte_sr_id` (modi `billing_account`, `fattura`, `fattura_sdi`) |
| `20261021-31` | `fn_scope_ba_ownership`, `_via_fattura`, `_via_fattura_sdi` diventano la **composizione** dei building block. Restano per la domanda su una riga: `fn_scope_ba_ownership` è nel catalogo `config.scope_policy`, e le chiamano ancora `fn_scope_shop_via_ba` e `fn_scope_note_cliente`. Così la regola `BA_OWNERSHIP` resta scritta una volta (regola del 2) |
| `20261021-32` | le 16 policy: 15 del portale (`billing_account`, `clienti`, `fatture` e i suoi undici satelliti, `note_fatture`) e `rls_billing_account_shop`. Generato dal testo vivo; rollback = i testi di prima |

### 6.3 Perché le risposte non cambiano, e l'unica differenza

* Il soggetto della riga è lo stesso che leggevano le funzioni vecchie: il cliente del billing account
  (della fattura, dell'invio SDI). Sulla riga di `billing_account` è la sua colonna `soggetto_ruolo_id`.
* Il perimetro è la stessa condizione: identità, veste, `fn_veste_utilizzabile`.
* ⚠️ **La differenza, voluta e dichiarata.** `fn_scope_ba_ownership` accettava le due vesti di cliente,
  `_via_fattura` nessun controllo di veste: due copie della stessa regola che dicevano due cose. Ora le
  policy chiedono la veste del proprio gate, e le funzioni per una riga le due vesti di cliente (come
  dice il catalogo `scope_policy`). Nel percorso reale non cambia niente, per il motivo del §6.1.

### 6.4 Le prove (scratch `zeroerp_ruoli`, come `zeroerp_owner`, 2026-10-21)

L'SQL estratto con le preCondition, in `BEGIN … ROLLBACK`: preCondition vere, una funzione per nome,
firme delle tre funzioni riscritte identiche al vivo. Il rollback riporta le 16 policy e le tre
funzioni (md5 di corpo e COMMENT) **identiche**. Un modo sconosciuto del risolutore solleva
`E_PARAMETRO_INVALIDO`. `plpgsql_check` sul risolutore: nessun errore (lo stesso avviso della sorella
sul `PERFORM` dell'errore). Il confronto puro è incorporato: nel piano resta
`COALESCE(soggetto = (InitPlan 1), false)`, e 20.000 righe costano quanto un filtro vuoto (1,9 ms).
Scratch verificato pulito.

| pgTAP | Senza | Con |
| --- | --- | --- |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (aggiornato) | 5/6 | 6/6 |
| `rls/test-rls-policies-structure` (aggiornato: 4, 16, 28) | 25/28 | 28/28 |
| `script/test-fn-veste-utilizzabile-v1` (aggiornato: 26) | 27/28 | 28/28 |
| `script/test-policy-funzioni-cost-v1` (aggiornato: economiche) | 4/4 | 4/4 |
| `rls/test-rls-policies-20260420-structure` | 28/28 | 28/28 |
| `script/test-fn-scope-ba-ownership`, `-via-fattura`, `rls/test-fn-scope-ba-ownership-ruolo-aware` | 6, 4, 5 | uguali |
| `rls/test-rls-clienti`, `-commesse-satelliti`, `-fatture-residuo`, `-fatture-satelliti-functional`, `-fatture-stampa-coda`, `-fondi-fattura-source-functional`, `-ddt-satelliti`, `-lotti-satelliti`, `-ordini-multipolicy`, `-ordini-satelliti`, `-note-padre`, `-perimetro-scoperto` | tutti verdi | tutti verdi |
| `anagrafiche/test-billing-account-auto-link-ef`, `script/test-fn-current-identita-context` | verdi | verdi |
| `dbops/test-security-definer-search-path-v1`, `-postura-proprietario-rls-v1`, `-catalogo-presidi-v1` | verdi | verdi |

I rossi «senza» sono quelli attesi: i test aggiornati che vedono il difetto o la forma nuova.

Cosa cambia nel presidio (`test-scope-ef-perimetro-una-volta-per-istruzione-v1`, plan 6):

* `fn_scope_sr_perimetro` è una «funzione di scope col perimetro» (test 1, 3, 4);
* test 4: nel piano non devono restare per riga né il perimetro di controparte né
  `fn_veste_utilizzabile`, salvo sulle tabelle con una policy nel debito dichiarato;
* test 6, nuovo: nessuna policy chiama una funzione di scope di controparte per riga fuori dal
  **debito dichiarato**, un elenco solo letto anche dal test 4.
  ⭐ Il test 4 l'ha già dimostrato: dopo il `-31` il pianificatore incorpora la catena di
  `fn_scope_note_cliente` dentro la policy di `vendite.note`, e il perimetro per riga diventa visibile
  nel piano. È debito dichiarato (le note del cliente), non una regressione: senza il `-31` la stessa
  chiamata per riga c'era, nascosta dentro una funzione non incorporata.

⚠️ Dopo l'apply: la corsa **come app** (Tid) e i tempi, che dall'owner non si misurano.

⛔ **Corretto dopo la corsa di Tid (2026-10-21).** `rls/test-rls-policies-structure` 4, 16 e 28 erano
rossi come app: le regex pretendevano `script.fn_get_identita_sr_perimetro(`, ma come app `script` è
nel search_path e il catalogo stampa il nome senza schema (da owner sullo scratch lo stampava, per
questo la prova era verde). Lo schema ora è facoltativo; regex verificate sul testo vivo di dbdev come
app e il file 28/28 sullo scratch. Gli altri test del giro non cercano lo schema nel testo.

### 6.5 Il debito che resta (test 6 del presidio)

`fn_scope_cliente_ownership`, `_via_ordine`, `_via_ordine_riga`; `fn_scope_shop_via_ordine`,
`_via_ordine_riga`, `_via_ba`; `fn_scope_fornitore_ownership`; `fn_scope_email_ambito`;
`fn_scope_note_cliente`, `fn_scope_note_shop`. Ogni giro aggiunge i suoi modi al risolutore e toglie le
sue voci dall'elenco.

### 6.6 Documentazione

* `linee-guida-sql.md` §10.3: la forma di controparte, con l'esempio e la convenzione `NULL` = nessuno.
* `manual/`: nuove `fn_get_identita_sr_perimetro` e `fn_resolve_controparte_sr_id`; in
  `fn_scope_ba_ownership` e `fn_scope_ba_ownership_via_fattura` la sezione sull'implementazione descrive
  la composizione (e la veste ora pretesa da `_via_fattura`).

## 7. Giro 3 — il cliente: ordini e ricevute (2026-10-21)

Scritto e provato in transazione il 2026-10-21. ✅ **Applicato** su dbdev, pgTAP verdi (Tid, 2026-10-21).

### 7.1 Che cosa

Stessa forma del giro 2 (§6.1), nessun building block nuovo: il risolutore impara gli ordini.

| ChangeSet | Che cosa |
| --- | --- |
| `20261021-33` | `fn_resolve_controparte_sr_id`: modi `ordine` (la colonna `soggetto_ruolo_id` dell'ordine) e `ordine_riga` (quella del suo ordine). Corpo dal vivo, solo i due rami, il messaggio dei modi ammessi e il COMMENT |
| `20261021-34` | `fn_scope_cliente_ownership` e `_via_ordine` diventano la composizione dei building block. Restano per la domanda su una riga: le chiamano `fn_scope_shop_via_ordine` e `fn_scope_note_cliente` (giri successivi) |
| `20261021-35` | le 8 policy: `ordini` (portale e shop), `ordini_righe`, `ordini_indirizzi`, `note_ordini`, `ordini_righe_componenti`, `ordini_righe_fulfillment` (portale), `shop.ricevute` (shop). Generato dal testo vivo; rollback = i testi di prima |
| `20261021-36` | si ritira `fn_scope_cliente_ownership_via_ordine_riga`: dopo il `-35` non la chiama nessuno (censimento su funzioni, viste, pgTAP, backend). Al suo posto il modo `ordine_riga` |

### 7.2 Perché le risposte non cambiano

Il cliente della riga è lo stesso: la colonna dell'ordine, o della ricevuta. La funzione vecchia lo
leggeva sotto la RLS dell'ordine, e per le vesti di cliente la policy dell'ordine è la stessa domanda.
Il perimetro è la stessa condizione di `fn_scope_cliente_ownership` (identità, vesti di cliente,
`fn_veste_utilizzabile`). La differenza dichiarata è quella del giro 2: le policy pretendono la veste
del proprio gate (§6.3).

### 7.3 Il caso costruito che mancava

I test esistenti provavano solo il **no**: una veste che non possiede l'ordine non vede niente. Un
perimetro che non lasciasse vedere nulla a nessuno li avrebbe passati tutti. Il pgTAP nuovo
`rls/test-rls-cliente-perimetro-ordini-v1` (plan 9) costruisce il **sì**:
- due aziende, un cliente ciascuna, un ordine con una riga per cliente, una veste `CLIENTE_PORTALE`
  per il cliente A;
- i due modi nuovi del risolutore, e il risolutore su un ordine che non c'è;
- il perimetro nella veste giusta e in quella sbagliata;
- con la RLS forzata su ordini e righe: A vede il proprio ordine e la propria riga, non quelli di B, e
  senza veste non vede niente.

Senza il giro 3 il file muore sul modo `ordine`, che non esiste ancora: è il segnale atteso.

### 7.4 Le prove (scratch `zeroerp_ruoli`, come `zeroerp_owner`, 2026-10-21)

L'SQL estratto con le preCondition, in `BEGIN … ROLLBACK`: preCondition vere, firme identiche al
vivo. Il rollback riporta le 8 policy e le tre funzioni toccate (md5 di corpo e COMMENT)
**identiche**. `plpgsql_check` sul risolutore: nessun errore. Scratch pulito.
⭐ I due test di struttura girano **anche** col `search_path` dell'app (la trappola del §6.4): verdi.

| pgTAP | Senza | Con |
| --- | --- | --- |
| `rls/test-rls-cliente-perimetro-ordini-v1` (**nuovo**) | muore sul modo `ordine` | 9/9 |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (debito: −3) | 5/6 | 6/6 |
| `rls/test-rls-policies-structure` (12) | 27/28 | 28/28, anche col search_path dell'app |
| `rls/test-rls-policies-20260420-structure` (4) | 27/28 | 28/28, anche col search_path dell'app |
| `script/test-fn-veste-utilizzabile-v1` (26) | 27/28 | 28/28 |
| `script/test-policy-funzioni-cost-v1`, `script/test-fn-scope-cliente-ownership` | verdi | verdi |
| `rls/test-rls-ordini-multipolicy`, `-ordini-satelliti`, `-note-padre`, `-perimetro-scoperto` | verdi | verdi |
| `vendite/test-note-partitioning`, `script/test-fn-current-identita-context`, `dbops/test-security-definer-search-path-v1` | verdi | verdi |

### 7.5 Il debito che resta (test 6 del presidio)

`fn_scope_shop_via_ordine`, `_via_ordine_riga`, `_via_ba`; `fn_scope_fornitore_ownership`;
`fn_scope_email_ambito`; `fn_scope_note_cliente`, `fn_scope_note_shop`.
Quando lo shop e le note del cliente saranno curati, `fn_scope_cliente_ownership`, `_via_ordine`,
`fn_scope_ba_ownership_via_fattura` e `_via_fattura_sdi` resteranno senza lettori: si ritirano in
quel giro. `fn_scope_ba_ownership` resta, perché è nel catalogo `config.scope_policy`.

### 7.6 Documentazione

* `manual/fn_resolve_controparte_sr_id`: i due modi nuovi e il presidio funzionale.
* `manual/fn_scope_cliente_ownership`: la composizione e il ritiro di `_via_ordine_riga`.

## 8. Giro 4 — lo shop e le note di cliente e shop (2026-10-21)

Scritto e provato in transazione il 2026-10-21. ✅ **Applicato** su dbdev, pgTAP verdi (Tid, 2026-10-21).

⭐ **Due famiglie in un giro, e perché.** `fn_scope_note_shop` chiamava `fn_scope_shop_via_ordine`, e
`fn_scope_note_cliente` chiamava `fn_scope_ba_ownership_via_fattura` e `fn_scope_cliente_ownership_via_ordine`.
Curarle in due giri avrebbe lasciato in vita composizioni intermedie. Insieme si chiude l'intero lato
cliente e si ritirano tutte le funzioni per riga.

### 8.1 I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `20261021-37` | `fn_resolve_controparte_sr_id`: modi `billing_account_shop`, `ordine_shop`, `ordine_riga_shop`. Danno la controparte **solo se la riga è nata dallo shop**, `NULL` altrimenti: la seconda condizione della veste `SHOP_CUSTOMER` sta nel modo |
| `20261021-38` | nascono `fn_scope_note_cliente_perimetro` e `fn_scope_note_shop_perimetro`: gli smistatori del padre `vendite.note` ricevono il perimetro, come quello dell'operatore (`20261021-25`) |
| `20261021-39` | le 8 policy: le 6 shop (`clienti`, `note_ordini`, `ordini_indirizzi`, `ordini_righe`, `ordini_righe_componenti`, `ordini_righe_fulfillment`) e le 2 del padre `vendite.note` (cliente e shop). Generato dal testo vivo; rollback = i testi di prima |
| `20261021-40` | si ritirano **nove** funzioni per riga: `fn_scope_cliente_ownership`, `_via_ordine`, `fn_scope_ba_ownership_via_fattura`, `_via_fattura_sdi`, `fn_scope_shop_via_ordine`, `_via_ordine_riga`, `_via_ba`, `fn_scope_note_cliente`, `fn_scope_note_shop`. Si chiamavano solo fra loro (censimento su funzioni, viste, catalogo `scope_policy`, backend). Il rollback le ricrea in ordine di dipendenza |

Resta `fn_scope_ba_ownership`: è la funzione della regola nel catalogo `config.scope_policy`, ed è
già una composizione dei building block (`20261021-31`).

### 8.2 Perché le risposte non cambiano

* Lo shop chiedeva due cose per riga: la proprietà (`fn_scope_cliente_ownership` / `fn_scope_ba_ownership`)
  e `canale_origine = 'SHOP'` della testata. Ora la proprietà è il perimetro, e il canale è il modo
  `_shop`, che fuori canale risponde `NULL`, cioè nessuno.
* Le note: stessi rami (`FATTURA`, `ORDINE` per il cliente; `ORDINE` per lo shop), stesso `ELSE false`,
  gli stessi modi delle policy delle partizioni.
* La differenza dichiarata è quella dei giri 2 e 3 (§6.3).

### 8.3 I pgTAP: due test nuovi al posto di due ritirati

| pgTAP | Che cosa |
| --- | --- |
| `script/test-fn-get-identita-sr-perimetro-v1` (**nuovo**, plan 12) | il perimetro (identità inesistente, `NULL`, spenta; veste giusta, sbagliata, entrambe) e il confronto (uguale, diverso, perimetro `NULL`, soggetto `NULL`). Tutto costruito. Prende il posto di `script/test-fn-scope-cliente-ownership` (**cancellato**) |
| `script/test-fn-resolve-controparte-sr-id-v1` (**nuovo**, plan 13) | ogni modo del risolutore, costruito, nei due versi dove ce ne sono due: BA da shop e da ADMIN, fattura e invio SDI, ordine e riga ADMIN e SHOP, chiave `NULL`, modo sconosciuto che solleva. Prende il posto di `script/test-fn-scope-ba-ownership-via-fattura` (**cancellato**), che i casi li **pescava** fra le fatture esistenti |
| `rls/test-rls-clienti` (3, 12) | la policy shop chiede il modo `billing_account_shop`; il modo dice il vero nei due versi |
| `script/test-fn-veste-utilizzabile-v1` (21a/b) | il perimetro del cliente al posto di `fn_scope_cliente_ownership` |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` | gli smistatori nuovi sono funzioni col perimetro; il debito scende a due voci |

⭐ Il primo ordine e il primo billing account del canale SHOP costruiti in un pgTAP: nessun test lo
faceva, e i guard li accettano.

### 8.4 Le prove (scratch `zeroerp_ruoli`, come `zeroerp_owner`, 2026-10-21)

SQL estratto con le preCondition, in `BEGIN … ROLLBACK`: preCondition vere; dopo il `-40` restano le
tre funzioni attese. Il rollback riporta le 8 policy e le dieci funzioni toccate (md5 di corpo e
COMMENT) **identiche**. `plpgsql_check` sul risolutore: nessun errore. Scratch pulito.

| pgTAP | Senza | Con |
| --- | --- | --- |
| `script/test-fn-resolve-controparte-sr-id-v1` (nuovo) | muore sul modo `billing_account_shop` | 13/13 |
| `script/test-fn-get-identita-sr-perimetro-v1` (nuovo) | 12/12 | 12/12 |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` | 4/6 | 6/6 |
| `rls/test-rls-clienti` | muore sul modo `billing_account_shop` | 13/13, anche col search_path dell'app |
| `script/test-fn-veste-utilizzabile-v1` | 28/28 | 28/28 |
| `rls/test-rls-policies-structure`, `-policies-20260420-structure` | 28/28 | 28/28, anche col search_path dell'app |
| `rls/test-rls-note-padre`, `-ordini-satelliti`, `-ordini-multipolicy`, `-cliente-perimetro-ordini-v1`, `-perimetro-scoperto`, `-fatture-satelliti-functional`, `-fatture-residuo`, `-fn-scope-ba-ownership-ruolo-aware` | verdi | verdi |
| `script/test-policy-funzioni-cost-v1`, `script/test-fn-scope-ba-ownership`, `vendite/test-note-partitioning`, `dbops/test-security-definer-search-path-v1` | verdi | verdi |

### 8.5 Il debito che resta (test 6 del presidio)

`fn_scope_fornitore_ownership` (2 policy di `acquisti`, catalogo `scope_policy`) e `fn_scope_email_ambito`
(2 policy di `config`).

⚠️ **Al backend, non bloccante:** un commento in `backend/apps/vendite/services/vendite_service.py`
(riga ~2020) cita `fn_scope_ba_ownership_via_fattura`, ritirata. È solo un commento, ma ora punta a
una funzione che non esiste: va riscritto citando il modo `fattura` di
`script.fn_resolve_controparte_sr_id`.

### 8.6 Documentazione

* `manual/`: cancellate `fn_scope_ba_ownership_via_fattura` e `fn_scope_cliente_ownership`. La spiegazione
  del ritiro sta in `fn_resolve_controparte_sr_id` (con la tabella dei modi `_shop`) e in
  `fn_scope_ba_ownership`. Rimandi aggiornati in `fn_veste_utilizzabile`,
  `fn_scope_ef_whitelist_via_fattura` e `shop/manual/ricevute`.
* Guide: `architettura-multi-face-auth` (l'esempio della policy shop) e `contratto-guc-app` (la
  famiglia ownership).

## 9. Giro 5 — fornitore ed email (2026-10-21)

Scritto e provato in transazione il 2026-10-21. ✅ **Applicato** su dbdev, pgTAP verdi (Tid, 2026-10-21).

Due famiglie piccole e indipendenti (due policy ciascuna), nello stesso giro per chiudere il brief.

### 9.1 Il disegno dell'email

La regola delle email dipende dall'**ambito** della riga (`SISTEMA`, `REPARTO`, `OPERATORE`). Chiedeva
per ogni riga quattro cose di chi guarda: super admin, reparto, identità di processo, perimetro
emittenti. Nessuna dipende dalla riga.
- Le quattro risposte passano in **quattro** sottoquery non correlate, una per domanda, valutate una
  volta per istruzione. Non contraddice «una sottoquery, non due» (§3): quella regola vieta di
  calcolare due volte la **stessa** cosa.
- Per riga resta una funzione **pura**, che decide per ambito (~4 µs a riga, nessuna lettura).
- ⚠️ Non ho introdotto un tipo composto per «il perimetro dell'email»: nel progetto non ce ne sono, e
  quattro sottoquery ottengono lo stesso risultato senza un oggetto nuovo da mantenere.

### 9.2 I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `20261021-41` | nasce `fn_scope_email_ambito_perimetro`: la regola dell'ambito con chi guarda già calcolato. Pura |
| `20261021-42` | `fn_scope_email_ambito` e `fn_scope_fornitore_ownership` diventano composizioni. **Restano**: la prima è la sonda dei test Django delle email (`richiedi_db_provvisto`) e la sede citata dai commenti del backend; la seconda è la funzione di `FORNITORE_OWNERSHIP` nel catalogo `config.scope_policy` |
| `20261021-43` | le 4 policy: `acquisti.ordini` e `acquisti.ddt` (forma di controparte, veste `FORNITORE_PORTALE`), `config.email_outbox` e `config.email_log` (USING e WITH CHECK, processo `send_pending_emails` per il log e `false` per l'outbox, come prima). Generato dal testo vivo; rollback = i testi di prima |

### 9.3 Perché le risposte non cambiano

* Fornitore: stessa identità, stessa veste (era già solo `FORNITORE_PORTALE`), stessa
  `fn_veste_utilizzabile`, stesso soggetto della riga.
* Email: stessi rami, stesso `ELSE false`, stesso `COALESCE`. L'emittente si confronta con
  `fn_scope_ef_perimetro` sul perimetro dell'utente invece che con `fn_scope_ef_whitelist`. La canonica
  controlla in più l'emittente attivo, ma il perimetro lo interseca già: stessa risposta, anche con
  emittente `NULL` e con utente `NULL` (lì ogni ramo è comunque falso).

### 9.4 Le prove (scratch `zeroerp_ruoli`, come `zeroerp_owner`, 2026-10-21)

SQL estratto con le preCondition, in `BEGIN … ROLLBACK`: preCondition vere, firme identiche al vivo.
Il rollback riporta le 4 policy e le due funzioni (md5 di corpo e COMMENT) **identiche**. Scratch pulito.

| pgTAP | Senza | Con |
| --- | --- | --- |
| `script/test-fn-scope-email-ambito-perimetro-v1` (**nuovo**, plan 14: ogni ramo nei due versi) | — | 14/14 |
| `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (debito **a zero**) | 5/6 | 6/6 |
| `script/test-policy-funzioni-cost-v1` (economiche: `fn_scope_email_ambito_perimetro`, `fn_is_super_admin`, con le misure) | 4/4 | 4/4 |
| `rls/test-rls-policies-structure` (20, 24) | 26/28 | 28/28, anche col search_path dell'app |
| `script/test-fn-veste-utilizzabile-v1` (26) | 27/28 | 28/28 |
| `script/test-fn-scope-fornitore-ownership`, `rls/test-rls-email-outbox-ambito`, `rls/test-rls-perimetro-scoperto`, `script/test-fn-get-identita-sr-perimetro-v1` | verdi | verdi |
| `config/test-fn-email-sistema`, `-email-guard-solo-bozza`, `-fn-resolve-email-account`, `script/test-fn-scope-identita-processo`, `dbops/test-vw-email-da-guardare`, `dbops/test-security-definer-search-path-v1` | verdi | verdi |

⚠️ Il test 2 dei costi, alla prima corsa, ha visto `fn_scope_email_ambito_perimetro` e
`fn_is_super_admin` nel testo di una policy, a `COST` 100. La seconda sta in una sottoquery, una volta
per istruzione; la prima non legge tabelle. Le ho misurate ed elencate fra le economiche, con la misura.

⚠️ Il test Django `backend/apps/core/tests/db/test_email_bozza_invio_db.py` usa come sonda la firma di
`fn_scope_email_ambito`, che resta identica: nessuna ricaduta.

### 9.5 Documentazione

* `linee-guida-sql.md` §10.3: il caso «chi guarda è più di un perimetro» (le quattro sottoquery) e il
  debito del presidio a zero.
* `manual/`: nuova `fn_scope_email_ambito_perimetro`; `fn_scope_fornitore_ownership` descrive la
  composizione.

### 9.6 Archiviazione (2026-10-21)

Giro 5 applicato e verde (Tid, 2026-10-21). Con lui nessuna policy calcola per riga ciò che dipende
solo da chi guarda, e il presidio `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` non
ammette eccezioni: l'elenco del debito dei test 4 e 6 è vuoto.

* Brief spostato in `work-done/`; **D36** chiuso nel registro; PROJECT_CONTEXT e mappa concentrica
  aggiornati.
* La nota per il backend del §8.5 (un commento in `vendite_service.py` che cita
  `fn_scope_ba_ownership_via_fattura`, ritirata) è consegnata in chat a Tid, che la gira alla sessione
  BE: si corregge al volo, non apre un brief (decisione di Tid, 2026-10-21).
* La misura dei tempi **come app** non è stata presa: è colore, non una condizione di chiusura. La
  forma è provata dal piano (test 4 del presidio).
