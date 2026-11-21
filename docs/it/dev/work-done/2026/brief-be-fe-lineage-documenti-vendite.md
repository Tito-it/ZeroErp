# Brief BE/FE — Lineage documenti vendite: colonna lista + pannello "Passaggi"

> **Tipo**: brief operativo BE/FE (`dev/backend-tid`) · **Data**: 2026-07-15 · **Owner**: Tid
> **Design-of-record**: [brief-design-genealogia-transiti-vendite.md](brief-design-genealogia-transiti-vendite.md)
> (G-1..G-11) — **sostituisce il piano §10 del design** (steso prima dell'estensione
> del perimetro a DDT e resi).
> **Prerequisito DB core**: [brief-db-lineage-documenti-vendite.md](brief-db-lineage-documenti-vendite.md)
> — ✅ **ESEGUITO** (commit `0cb1f9061`): `vw_documento_lineage_nodi/archi`,
> `vw_documento_lineage`, `fn_documento_lineage`, `security_invoker=on`, pgTAP
> verde, casi §5 validati (PRV0000183/184/185, commessa 186 inversa, PRA-0000818).
> **Prerequisito DB Fase B**: [brief-db-liste-lineage-colonne.md](brief-db-liste-lineage-colonne.md)
> — ✅ **ESEGUITO incl. §7 preset** (`10e8f22ee` + `9a2f59d0a`).
> Entrambi spostati in **work-done** (2026-07-15); lato DB tutto pushato e
> mergiato in `Tito-dev` (PR #988/#989).

---

## ✅✅ STATO FINALE (2026-07-15) — TUTTE LE FASI COMPLETE

Verifica attività a consuntivo (dettaglio per fase nelle sezioni sotto):

| Attività | Stato |
| --- | --- |
| DB core lineage (viste+fn+seed fase/abortito+pgTAP) | ✅ eseguito, mergiato Tito-dev |
| DB colonne liste (5 viste + seed catalogo + preset default §7) | ✅ eseguito, mergiato Tito-dev |
| BE-A1..A4 endpoint `/passaggi/` (repo, service, factory, 7 route, test, doc) | ✅ |
| FE-A5..A6 pannello "Passaggi" nei 6 drawer + apertura dettaglio impilato | ✅ validato in-app |
| BE-B1..B3 colonne nei 5 repo lista + order whitelist + test | ✅ |
| FE-B4 celle pratica/fase/transito nelle 5 liste + i18n | ✅ validato in-app (ordini, ddt) |
| Fase C slice minima (COMMESSA whitelist+route, `CommessaDrawer`, tappe cliccabili) | ✅ verificato su dati vivi |
| Review critica BE/FE (6 finding corretti: useApiHandler, freshness, simmetria, dedupe, unmount, test 7ª rotta) | ✅ suite 1173 + build verdi |
| Doc (manuale api_lineage_passaggi, api.md, cataloghi BB, brief) | ✅ |

**Restano aperti** (nessuno bloccante per la feature):

1. **Commit** del lavoro BE/FE su `dev/backend-tid` — tutto ancora NON
   committato (Tid committa). Nota: `dev/backend-tid` non contiene ancora il
   Tito-dev aggiornato coi commit DB; allineare al solito giro PR. Il brief
   `brief-db-lineage-documenti-vendite.md` è stato spostato qui in work-done
   con il contenuto finale di db-tid: al merge, sul file può comparire un
   conflitto rename-vs-modify banale (tenere la versione work-done).
2. ~~Validazione visiva in-app della Fase C~~ → ✅ **fatta da Tid (2026-07-15,
   test UI completi su tutte le fasi, tutto ok)**.
3. **Follow-on futuri fuori perimetro** (§3): dominio commesse UI completo
   (serve `vw_commesse_lista`, progetto separato); archi DB futuri reso→nota
   di credito e DDT→fattura differita (il pannello li renderà da solo);
   eventuale materializzazione della lineage se il walk full-graph peserà
   (nota prestazioni nel brief colonne §4).

---

## ✅ STATO — FASE A COMPLETATA (2026-07-15)

BE+FE del pannello "Passaggi" consegnati su `dev/backend-tid` (non committato):

- **BE**: repo lineage (`get_lineage_sorgente`/`resolve_lineage_node_uid`/
  `get_lineage_nodo`/`list_lineage_passaggi` in `vendite_repository.py` +
  TypedDict), service `get_documento_passaggi` (whitelist tipo, chiave nodo
  polimorfa data-driven da `key_selector`, frontiera normalizzata, avanti +
  indietro), factory `build_passaggi_view` (`api/lineage_views.py`) cablata
  sui **6 domini**. Test: 13 service + 3 API, verdi. Doc:
  `api_lineage_passaggi.md` + riga in api.md + catalogo BB.
- **FE**: BB `src/vendite/_shared/lineage/` (`lineageApi.js` +
  `LineagePassaggiPanel.vue`, Panel toggleable **lazy** — fetch al primo
  expand, root `app-escape`) montato come **sezione** nei 6 drawer (i drawer
  ordini/contratti/ddt/resi non hanno tabs: sezione uniforme ovunque, delta
  consapevole vs "tab" del piano). i18n `lineage.*` it+en. Build Vite verde.
- **Uniformità apertura tappe (Tid 2026-07-15)**: le tappe documento aprono
  il **dettaglio impilato** (come il link pratica → `PraticaDrawer`), non più
  la navigazione alla lista. Nuovo `LineageDocumentoDrawerHost` +
  `lineageDrawers.js` (mappa tipo→drawer con `defineAsyncComponent` per
  rompere il ciclo di import). Il BE espone `from_doc_id`/`to_doc_id` (id
  numerico, con traduzione UUID→id per preventivo/offerta) per il drawer.
- **Verificato su dati vivi** (contesto operatore): PRV0000185 → pratica
  PRA-0000818, catena A→H fino a DDT0000031 (frontiera); RESO0000011 →
  origine DDT0000057 ← ORD0000228. Endpoint HTTP vivo post `kill -HUP`.
- ~~Aperto: validazione visiva in-app; Fase B; Fase C~~ → tutto chiuso, vedi
  «STATO FINALE» in testa (validazione in-app Tid 2026-07-15, poi Fase B+C).

---

## 0. Cosa è cambiato rispetto al piano iniziale (design §10)

Il team DB ha chiuso il brief lineage **recependo due estensioni** decise il
13/07 in analisi critica:

1. **DDT nel grafo e nelle liste** — arco **H `Ordine → DDT` (1:N)** LIVE
   (evasione multi-DDT del 10/07). Le liste che ricevono la colonna diventano
   **5** (preventivi, offerte, ordini, contratti, **DDT**). La frontiera può ora
   attestarsi su un DDT: verificato vivo, `PRV0000185` → frontiera
   `DDT0000031 (SPEDITO)`, oltre l'ordine.
2. **Resi ("gestione rimborsi") come ramo inverso** — arco **R `DDT → Reso`
   (1:N)** LIVE, seed `config.sorgenti` `RESO_VENDITA(15)`. Il reso **compare**
   nel pannello "Passaggi" (flag `is_ramo_inverso=true`, merce che torna) ma è
   **escluso dalla frontiera forward**. L'arco *uscente* reso → nota di credito
   (rimborso contabile) è futuro, stesso meccanismo.

Altre decisioni DB recepite che toccano BE/FE:

- **Chiave nodo nativa polimorfa** `(tipo_id, uid)` secondo
  `config.sorgenti.key_selector`: `uid` per PREVENTIVO/OFFERTA, `id::text` per
  ORDINE/CONTRATTO/DDT/FATTURA/COMMESSA/RESO. Convenzione documentata in
  `config.manual/sorgenti.md` §"Convenzione chiave sorgente" — **leggerla prima
  di ogni join tra documenti**.
- **Fattura = nodo terminale** (Q4): la frontiera può essere «→ FT-xxxx»; niente
  colonna-lista per fatture/commesse.
- **Pratica difensiva** (Q5): la summary espone `pratica_id/pratica_numero` +
  `n_pratiche` (il DB non garantisce 1:1).
- `fase`/`is_abortito` ora seedati anche su `stati_doc_ddt/fiscale/reso` +
  `stati_commessa` → la scala fase (⚪🔵🟠🟢) copre tutti i nodi.

### Oggetti DB disponibili (contratto per il BE)

| Oggetto | Uso |
| --- | --- |
| `vendite.vw_documento_lineage` | 1 riga/documento: `tipo_id, uid, codice, stato_*, fase, is_abortito, pratica_id, pratica_numero, n_pratiche, frontiera_{tipo_id,uid,codice,stato_codice_interno,fase}, n_discendenti_diretti/attivi, is_transitato, n_sorgenti, root_{tipo_id,uid,codice}` |
| `vendite.fn_documento_lineage(p_tipo_id, p_uid, p_direzione)` | traversal: `livello, ordine, arco (A..H/R), ruolo, from_{tipo_id,uid,codice}, to_{tipo_id,uid,codice,stato_codice_interno,fase,is_abortito}, is_ramo_inverso`. Direzione `avanti`/`indietro`. Guard `ERRORE_PARAMETRI` su input invalidi |
| `vendite.vw_documento_lineage_archi` / `_nodi` | mattoni; il BE normalmente non li interroga |

Tutto `security_invoker=on` / `STABLE SECURITY INVOKER`: la RLS emittente del
chiamante si applica da sola — **niente `auth_user_id` da passare**.

---

## 1. Fase A — Pannello "Passaggi" (BE+FE, parte subito)

### BE-A1 — Repository (`db/vendite_repository.py`)

Lineage = letture generiche di schema, niente file dedicato (regola naming
AGENTS): metodi in `vendite_repository.py`.

- `get_lineage_nodo(tipo_id, node_uid)` → riga singola da
  `vw_documento_lineage` (nodo + pratica + frontiera + contatori), `None` se
  assente.
- `list_lineage_passaggi(tipo_id, node_uid, direzione)` → `SELECT ... FROM
  vendite.fn_documento_lineage(%s, %s, %s) ORDER BY ordine`.
- TypedDict in `types.py`: `LineageNodoRow`, `LineagePassaggioRow`.

### BE-A2 — Service (`services/vendite_service.py`)

`get_documento_passaggi(tipo_codice, doc_id)`:

1. whitelist `tipo_codice` ∈ {PREVENTIVO, OFFERTA_COMMERCIALE, ORDINE_VENDITA,
   CONTRATTO, DDT_VENDITA, RESO_VENDITA} (`validate_enum_param`,
   `E_VENDITE_VALIDATION`);
2. risolve la **chiave nodo** dal `doc_id` di dominio: per PREVENTIVO/OFFERTA
   mini-query `SELECT uid FROM vendite.<tab> WHERE id=%s` (404 di dominio se
   assente — la RLS fa già sparire i fuori-scope); per gli altri `str(doc_id)`
   con check esistenza via `get_lineage_nodo`;
3. ritorna `{nodo, pratica: {pratica_id, pratica_numero, n_pratiche}|None,
   avanti: [...], indietro: [...]}` — **entrambe le direzioni** in una risposta
   (un documento a metà catena ha origine E destinazioni; simmetria subito,
   [[feedback_simmetria_modello_no_meta_scope]]). Ogni passaggio decodifica
   `tipo` in `codice_interno` (il FE traduce via i18n, mai id numerici —
   [[feedback_no_hardcoded_ids]]: risolvere i `tipo_id` per JOIN a
   `config.sorgenti`, non con mappe hardcoded).

### BE-A3 — View factory + routing (`api/lineage_views.py`)

Factory `build_passaggi_view(schema_prefix, url_kwarg, tipo_codice)` sul modello
di `build_riepilogo_iva_view` (stesso file-pattern, patch dei test preservati):
`GET /api/v1/vendite/<dominio>/<id>/passaggi/` — `DomainAPIView`,
`area_funzionale="vendite"`, `@extend_schema` inline. Cablaggio su **6 domini**:
`preventivi_urls.py`, `urls_offerte.py`, `urls_ordini.py`, `urls_contratti.py`,
`urls_ddt.py`, `urls_resi.py` (il reso mostra la catena `indietro`:
reso ← DDT ← ordine ← …).

### BE-A4 — Test + doc

- `tests/services/test_lineage_service.py` (unittest + mock repo): tipo fuori
  whitelist → `E_VENDITE_VALIDATION`; doc inesistente → not found di dominio;
  shape risposta (avanti+indietro+pratica); passthrough `is_ramo_inverso`.
- `tests/api/test_lineage_api.py`: routing 6 domini + envelope.
- Manuale `docs/it/backend/vendite/manual/api_lineage_passaggi.md` (template
  standard) + riga in `api.md` §Endpoint attivi.

### FE-A5 — BB condiviso `src/vendite/_shared/lineage/`

Cinque consumer subito → si nasce BB ([[feedback_regola_del_2_estrai_bb]],
dichiarato qui):

- `lineageApi.js` — `getPassaggi(basePath, id)` (factory bindata al dominio,
  gemella `makeIndirizziDocumentoApi`).
- `LineagePassaggiPanel.vue` — pannello riusabile: props `basePath`, `docId`,
  `readonly`. Rende **Origine** (indietro) e **Destinazioni** (avanti) come
  timeline indentata per `livello`; ogni tappa = Tag tipo (i18n
  `lineage.tipo_*`) + codice + Tag fase (`faseDocumentoSeverity` +
  `dashFaseLabel` — riuso Situazione aperta, G-7); arco R (`is_ramo_inverso`)
  reso con stile "ramo di ritorno" (icona ↩ + tono attenuato); fan-out F/H =
  semplicemente N righe (design §7.2). Tappe cliccabili "apri documento" via
  `buildApriDocumentoAction`/`DASH_AREA_CONFIG` per i tipi con lista (fatture/
  commesse non cliccabili per ora). Pratica in testa al pannello: numero
  cliccabile → apre `PraticaDrawer` (già esistente, `src/pratiche/components/`).
  Watch su `docId` con `immediate` + lazy-load all'attivazione del tab
  ([[feedback_componente_riusabile_watch]]); fetch diretta axios nel pannello
  (niente store: read-only per documento).
- ⚠️ Nei drawer post-DRAFT il contenuto è `.app-readonly`: i pulsanti del
  pannello (apri documento / apri pratica) vanno in wrapper **`app-escape`**
  ([[feedback_app_escape_pannelli_processo]] — 2 bug bloccanti storici).

### FE-A6 — Tab "Passaggi" nei 6 drawer

`PreventiviDrawer`, `OffertaDrawer`, `OrdiniDrawer`, `ContrattoDrawer`,
`DdtDrawer`, `ResoDrawer`: nuovo `<Tab>/<TabPanel>` "Passaggi" (pattern tab già
in uso, es. testata+revisioni) che monta `LineagePassaggiPanel`. Visibile solo
in EDIT (documento persistito). i18n `lineage.*` in `it.json` + `en.json`
(mai stringhe hardcoded).

---

## 2. Fase B — Colonna lista sulle 5 liste (gate: brief DB colonne)

Parte a viste+seed applicati (`brief-db-liste-lineage-colonne.md`).

> **✅ STATO — FASE B BE+FE COMPLETA (2026-07-15, non committato).** DB (viste +
> seed `ui.lista_colonna`) applicato sul DB di test. BE: i 5 repo lista espongono
> le colonne (`SELECT v.*`) + decodifica `frontiera_tipo_codice` (JOIN
> `config.sorgenti`) + whitelist order_by estesa (`pratica_numero`, `fase`); test
> `test_lineage_liste_be.py` verde, suite vendite 1172. FE: 3 celle BB
> (`LineagePraticaCell`/`LineageFaseTag`/`LineageFrontieraChip`) + slot
> `#cell-pratica/fase/transito` sulle 5 SearchTable + gruppo i18n `lista.col_*`;
> build Vite verde.
> ~~⚠️ GAP visibilità~~ → **RISOLTO**: il primo seed rendeva le colonne opt-in
> (`visibile=false`); il follow-up
> [brief-db-liste-lineage-colonne.md §7](brief-db-liste-lineage-colonne.md)
> (seed del preset di default `ui.lista_preset_colonna`) è stato **eseguito dal
> team DB** (`10e8f22ee`): verificato `fn_resolve_lista_config` →
> `pratica/fase/transito` `visibile=true` su tutte e 5 le liste; validato
> in-app da Tid (ordini + ddt).

### BE-B1 — Repos liste (5 file)

Le liste leggono già dalle `vw_*_lista`: aggiungere alle SELECT le nuove colonne
(`fase`, `pratica_id`, `pratica_numero`, `n_pratiche`, `frontiera_tipo_id`,
`frontiera_codice`, `frontiera_stato_codice_interno`, `frontiera_fase`,
`n_discendenti_attivi`, `is_transitato`) in `preventivi_repository.py`,
`offerte_repository.py`, `ordini_repository.py`, `contratti_repository.py`,
`ddt_repository.py` + TypedDict `*ListRow`. Whitelist `order_by`: +
`pratica_numero`, `fase` (frontiera NON ordinabile). Nessun filtro nuovo in
questa iterazione.

### BE-B2 — Export

Gratis: l'export è config-driven (`build_export_response` risolve le colonne da
`fn_resolve_lista_config`); le nuove colonne entrano seguendo visibilità/ordine
utente ([[feedback_export_lista_rispetta_preferenza]]). Solo verificare che i
value formatter non inciampino (stringhe/bool piatti — ok).

### BE-B3 — Test

Estendere i test lista dei 5 domini: passthrough nuove colonne + order_by
`pratica_numero`/`fase` accettati, colonna non in whitelist → errore.

### FE-B4 — Celle BB + slot nelle 5 SearchTable

In `src/vendite/_shared/lineage/`:

- `LineagePraticaCell.vue` — numero pratica cliccabile (apre `PraticaDrawer`;
  stopPropagation vs row-click); "—" se NULL; badge `+N` se `n_pratiche > 1`.
- `LineageFaseTag.vue` — Tag fase (`faseDocumentoSeverity` + `dashFaseLabel`).
- `LineageFrontieraChip.vue` — chip `→ <Tag tipo> CODICE · fase`; se
  `n_discendenti_attivi > 1` suffisso `(+N attive)` (fan-out F/H aggregato,
  G-9); "—" se `is_transitato=false`.

Slot `#cell-pratica`, `#cell-fase`, `#cell-transito` in `PreventiviList`,
`OfferteSearchTable`, `OrdiniSearchTable`, `ContrattiSearchTable`,
`DdtSearchTable` (3 righe l'uno). Build Vite a chiudere.

---

## 3. Fase C — Genealogia inversa commesse (slice minima)

> **✅ STATO — FASE C (slice minima) COMPLETA (2026-07-15, non committato).**
> Scoperta in mappatura: **non esiste lista/drawer/store/api commesse** (dominio
> SQL-only, solo dashboard). La "lista commesse" del design §7.3 non ha una casa.
> Deciso con Tid (2026-07-15) di NON costruire il dominio commesse completo, ma
> una **slice minima** che riusa l'infrastruttura lineage:
>
> - **BE**: `COMMESSA` aggiunta a `LINEAGE_TIPI_DOCUMENTO`; route
>   `GET /vendite/commesse/<id>/passaggi/` (`ApiCommessaPassaggi`, stessa factory).
> - **FE**: `CommessaDrawer.vue` leggero read-only (header stato + `LineagePassaggiPanel`
>   `start-open`); `COMMESSA` registrata in `lineageDrawers.js` → le tappe COMMESSA
>   nei pannelli "Passaggi" dei 6 documenti diventano **cliccabili** e aprono il
>   drawer commessa impilato (Origine = sorgenti, Destinazioni = fatture).
>   `LineagePassaggiPanel` esteso con prop `start-open` + evento `@loaded`.
> - Verificato live: commessa 186 → Origine PRV0000183 (ROOT) + PRV0000184
>   (COLLEGATO); tappa COMMESSA da PRV0000183 con `to_doc_id=186` (cliccabile).
>   Suite vendite 1173 verde, build Vite verde.

**Follow-on ancora aperti (non in questa slice):**

1. **Dominio commesse completo** (lista utente `/vendite/commesse` + CRUD/testata):
   progetto separato, richiede una `vw_commesse_lista` dal team DB + FE dominio.
   Non necessario per la genealogia inversa (coperta dalla slice minima).
2. **Arco reso → nota di credito** (rimborso contabile) e **DDT → fattura
   differita**: si aggiungono nel DB con lo stesso meccanismo archi; BE/FE non
   cambiano (il pannello li rende da soli).

---

## 4. Ordine di lavorazione e verifica

1. **A1→A4** (BE Passaggi) → test unit verdi.
2. **A5→A6** (FE pannello) → `kill -HUP` gunicorn
   ([[project_backend_gunicorn_reload]]) + verifica in-app sui dati vivi:
   - PRV0000185 → Destinazioni: ordine → DDT0000031 (frontiera IN_CORSO);
   - DDT con reso → ramo di ritorno visibile e distinto;
   - Commessa 186 da ResoDrawer/OrdiniDrawer: origine PRV0000183 (ROOT) +
     PRV0000184;
   - pratica PRA-0000818 apribile dal pannello.
3. **Brief DB colonne** al team DB → attendere viste+seed → **B1→B4**.
4. Verifica in-app colonne (5 liste: pratica cliccabile, fase, chip transito;
   personalizzazione colonne mostra le 3 nuove; export le include).
5. Consuntivo + eventuale aggiornamento cataloghi BB (BE: factory passaggi;
   FE: famiglia `_shared/lineage/`).

## 5. Punti aperti / decisioni

| # | Punto | Stato |
| --- | --- | --- |
| P-1 | Endpoint passaggi per-dominio (factory, 6 wiring) vs endpoint generico unico `?tipo=` | ✅ **CHIUSO (Tid 2026-07-15): per-dominio** — coerente con riepilogo-IVA/indirizzi/documenti, FE ignaro di `key_selector` |
| P-2 | Pannello con entrambe le direzioni sempre | ✅ **CHIUSO (Tid 2026-07-15): sì, bidirezionale sempre** (Origine + Destinazioni; per preventivo/offerta l'origine sarà quasi sempre vuota) |
| P-3 | Visibilità default delle 3 colonne su DDT | ✅ **CHIUSO (Tid 2026-07-15): visibili di default anche su DDT** — si valuta l'effetto in-app, eventualmente si spengono dopo (flag `visibile` nel seed, recepito nel brief DB colonne §3) |
