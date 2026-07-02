# Brief DB — Roll-out proiezione stato di dominio: OFFERTA · ORDINE · CONTRATTO

> **Tipo**: brief DB (DDL + seed + viste) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟠 media · **Data**: 2026-07-02 · **Stato**: 🟡 **DA PRENDERE IN CARICO**
>
> **Scope confermato da Tid (2026-07-02)**: (1) le pratiche OFFERTA/CONTRATTO ancoreranno
> il documento come **ROOT con `flusso_id`** (simmetria con PREVENTIVI); (2) si **accende
> anche l'ORDINE** in questo giro — quindi la vista d'àncora condivisa
> `script.vw_pratica_doc_sorgente` (nota (b)/(c)) entra **in scope**, non è più opzionale.
>
> **Origine / autorevole**: [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md)
> (voce **V10**) + increment PREVENTIVI già chiuso
> ([brief-db-proiezione-stato-dominio.md](../work-done/brief-db-proiezione-stato-dominio.md)).
> Qui si **replica lo stesso playbook** (D1→D2→D3) sui tre domini residui. Modello,
> principio (proiezione ≠ mirror), vocabolario universale e vincoli sono nel brief di
> design: leggerlo prima. Le 5 decisioni A-E dell'increment PREVENTIVI restano valide.
>
> **Perché ora, benché le pratiche offerte/ordini/contratti non esistano ancora**: il
> layer DB (mappa + resolver + union) proietta lo stato del **documento**, non della
> pratica; i tavoli `config.stati_doc_*` e le testate `vendite.{offerte_commerciali,
> ordini,contratti}` **esistono già**. È **puramente additivo** (`feedback_concentrico_no_yagni`):
> un dominio con resolver ma senza pratica che lo referenzia non cambia nulla a video;
> quando i flussi arriveranno, MOSTRA si accende da solo. Nessuna regressione: senza
> resolver un tipo sorgente restava `UNKNOWN` (`risolto=false`), con resolver diventa
> proiettabile.

---

## 1. Cosa è stato verificato sul DB vivo (recon 2026-07-02, `docs/it/dbzero`)

| Dominio | Sorgente (`config.sorgenti`) | `target_table` | `key_selector` | Testata → colonna stato |
|---|---|---|---|---|
| Offerta | `OFFERTA_COMMERCIALE` (id 14) | `vendite.offerte_commerciali` | **`uid`** | `stato_doc_offerta_id` |
| Ordine | `ORDINE_VENDITA` (id 6) | `vendite.ordini` | **`id`** | `stato_doc_ordine_id` |
| Contratto | `CONTRATTO` (id 4) | `vendite.contratti` | **`id`** | `stato_doc_contratto_id` |

- Tutte e tre le testate hanno **sia `uid uuid` sia `id bigint`**: il resolver deve
  emettere `sorgente_uid` **coerente col `key_selector`** della sorgente (uid per
  offerta, id per ordine/contratto), come fa il resolver preventivo con `(uid)::text`.
- `config.stati_doc_{offerte,ordini,contratti}`: **nessuna** colonna di normalizzazione
  (`fase`/`esito`/`terminale`) → D1 è nuovo per tutti e tre (identico a PREVENTIVI).
- Prerequisiti motore **già consegnati** dall'increment PREVENTIVI e **riusabili così
  come sono**: `esiti_flussi_pratiche.is_verdetto`, guard generico
  `config.trgfn_stati_doc_guard_esito_verdetto` (basta agganciarne il trigger alle nuove
  tabelle), wrapper `pratiche.fn_stato_sorgente`, vista union `script.vw_stato_sorgente`.
- **Ambiguità da chiarire lato DB** (⚠️): `config.stati_doc_ordini` è agganciata via
  trigger di deattivazione sia a `acquisti.ordini` sia a `vendite.ordini`. La sorgente
  `ORDINE_VENDITA` punta a **`vendite.ordini`**: il resolver legge quella. Verificare che
  il vocabolario stati sia semanticamente condiviso (lo è: entrambi sono cicli-ordine) —
  la mappa §2 vale per entrambi, la colonna D1 serve tutti i consumatori.

## 2. D1 — Mappa di normalizzazione per dominio (seed completo, già derivato)

Applicazione **1:1** del vocabolario universale (brief design §3, brief DB PREVENTIVI §2)
ai seed reali (`80_data/sql/config/stati_doc_*.csv`). Copertura **100%** per tutti e tre
→ `fase NOT NULL` fattibile ovunque. Invariante CHECK: `terminale ⇒ fase='CHIUSO'`.

### Offerta (`stati_doc_offerte`)
| `codice_interno` | `fase` | `esito` | `terminale` |
|---|---|---|---|
| BOZZA | APERTO | — | false |
| EMESSA | IN_ATTESA | — | false |
| ACCETTATA | IN_CORSO | POSITIVO | false |
| RIFIUTATA | CHIUSO | NEGATIVO | true |
| SUPERATA | CHIUSO | NEGATIVO | true |
| ANNULLATA | CHIUSO | NEGATIVO | true |

### Ordine (`stati_doc_ordini`)
| `codice_interno` | `fase` | `esito` | `terminale` |
|---|---|---|---|
| DRAFT | APERTO | — | false |
| CONFERMATO | IN_CORSO | — | false |
| ALLOCATO | IN_CORSO | — | false |
| SPEDITO | IN_CORSO | — | false |
| CONSEGNATO | IN_CORSO | — | false |
| EVASO | CHIUSO | POSITIVO | true |
| FATTURATO | CHIUSO | POSITIVO | true |
| ANNULLATO | CHIUSO | NEGATIVO | true |

### Contratto (`stati_doc_contratti`)
| `codice_interno` | `fase` | `esito` | `terminale` |
|---|---|---|---|
| DRAFT | APERTO | — | false |
| ATTIVO | IN_CORSO | — | false |
| CESSATO | CHIUSO | POSITIVO | true |
| ANNULLATO (`is_abortito=true`) | CHIUSO | NEGATIVO | true |

> `is_abortito` **non si tocca** (decisione E): `terminale` è l'asse uniforme, `is_abortito`
> conserva la sua semantica di abbandono-revisione. Coesistono.

**Seed** (playbook `is_abortito` / increment PREVENTIVI): backfill `UPDATE` keyed su
`codice_interno` in `00_schema` (DB vivo) + colonne `fase`/`terminale` nelle CSV (DB fresh);
`esito` via changeset `UPDATE` idempotente in `80_data` (il `nullValue:""` delle CSV non
esprime NULL — memoria `feedback_liquibase_csv_null_sentinel`). Agganciare il trigger guard
generico `trgfn_stati_doc_guard_esito_verdetto` (fase `_a10_..._ins_upd`) a ciascuna delle
tre tabelle.

## 3. D2 — Resolver per dominio (specchio di `vw_stato_sorgente_preventivo`)

Tre viste in `vendite`, identiche per forma al resolver preventivo (stesse colonne del
descrittore §4). Differenza unica: **il cast di `sorgente_uid` segue il `key_selector`**.

- `vendite.vw_stato_sorgente_offerta` — join `offerte_commerciali oc` →
  `sorgenti` (`codice_interno='OFFERTA_COMMERCIALE' AND attivo`) →
  `stati_doc_offerte sdo ON sdo.id = oc.stato_doc_offerta_id`; `sorgente_uid = (oc.uid)::text`.
- `vendite.vw_stato_sorgente_ordine` — join `ordini o` →
  `sorgenti` (`codice_interno='ORDINE_VENDITA' AND attivo`) →
  `stati_doc_ordini sdor ON sdor.id = o.stato_doc_ordine_id`; `sorgente_uid = (o.id)::text`.
- `vendite.vw_stato_sorgente_contratto` — join `contratti c` →
  `sorgenti` (`codice_interno='CONTRATTO' AND attivo`) →
  `stati_doc_contratti sdc ON sdc.id = c.stato_doc_contratto_id`; `sorgente_uid = (c.id)::text`.

Contratto resolver: **al più una riga per (tipo, uid)**. `sorgente_tipo_id` sempre risolto
via join su `codice_interno` (mai id letterale — `feedback_no_hardcoded_ids`).

## 4. D3 — Estensione vista union (decisione A: niente `resolver_key`)

`script.vw_stato_sorgente` diventa `UNION ALL` di **4 rami** (preventivo + i 3 nuovi).
Ogni ramo aggiunge `risolto=true` e normalizza i tipi a `text`. Registrare un dominio =
aggiungere un ramo (changeset nuovo additivo). **`pratiche.fn_stato_sorgente` invariato**
(già wrapper scalare sulla vista con fallback `UNKNOWN`). Nessuna modifica BE/FE: il
frammento `_doc_sorgente_lateral` e il consumo FE (`faseSorgenteSeverity`) sono agnostici.

## 5. ⚠️ Note critiche di roll-out (dalla review 2026-07-02) — leggere prima di stimare

### (a) Indice a espressione per il pushdown — **tutti e quattro i domini**
Il resolver espone `sorgente_uid` **castando la chiave nativa a `text`** (`(uid)::text` per
offerta/preventivo, `(id)::text` per ordine/contratto). La LATERAL del percorso/coda filtra
`vw_stato_sorgente.sorgente_uid = ps.sorgente_uid`: il predicato cade sull'**espressione**,
non sull'indice btree nativo. Al crescere dei volumi serve un **indice a espressione** per
dominio:
- `((uid::text))` su `vendite.preventivi` e `vendite.offerte_commerciali`;
- `((id::text))` su `vendite.ordini` e `vendite.contratti`.

(Voce già annotata in testa al brief design per PREVENTIVI: qui si **generalizza** e si
include l'indice mancante anche sul preventivo.)

### (b) 🔴 ORDINE (e COMMESSA) nascono `COLLEGATO` **senza `flusso_id`** → serve l'àncora pratica-level

Confermato su DB (`trgfn_pratiche_sorgenti_guard_coerenza_flusso`, regola 1): «i link
`COLLEGATO` a valle (commessa/ordine dai push handler) nascono con `flusso_id` NULL». Il BE
aggancia oggi con `_doc_sorgente_lateral(anchor_cond)`, due varianti **statiche**:

- **dettaglio/lista** → `ps.ruolo_link = 'ROOT'` (àncora ROOT);
- **percorso/coda** → `ps.flusso_id = f.id` (àncora per-flusso).

Un ordine `COLLEGATO` non è ROOT e non ha `flusso_id` → **nessuna delle due lo proietta**.
Per accenderlo (scope 2) si introduce la vista d'àncora condivisa già prevista dal codice
(commento `pratiche_repository._doc_sorgente_lateral`, righe 68-71) e da D4:

**`script.vw_pratica_doc_sorgente`** — dato `pratica_id`, sceglie **il documento che
rappresenta lo stato vivo della pratica** e ne espone il descrittore (join a
`vw_stato_sorgente`). Il **dettaglio/lista** consuma questa vista al posto dell'àncora
ROOT-only → ordine/commessa `COLLEGATO` si accende come "documento corrente" della pratica.

> **🟠 Decisione di modello (regola d'àncora) — da confermare.** L'attuale «ROOT preferito,
> poi link più recente» **non basta per l'ordine**: una pratica evoluta preventivo→ordine ha
> il preventivo ROOT (spesso già **terminale**, es. EVASO) che vincerebbe **sempre** sul-
> l'ordine `COLLEGATO` vivo → l'ordine non si vedrebbe mai. **Proposta**: àncora = **link
> più vivo** = `ORDER BY (NOT terminale) DESC, ps.id DESC` (documento non-terminale più
> recente; ROOT come tiebreaker naturale nel caso mono-documento). Così una pratica sul solo
> preventivo mostra il preventivo; una evoluta a ordine mostra l'**ordine** vivo. Da
> validare con Tid: è l'unica scelta di merito di questo roll-out.

**Percorso narrativo (pinning per-milestone del `COLLEGATO`)** — mostrare l'ordine
*appeso al suo step* (CONFERMA_ORDINE) sul racconto **richiede** che lo step dichiari il
tipo-sorgente che produce (mappa step→sorgente): è la stessa informazione che serve a **D4
(GUIDA)** per "avanza-su-esito-proiettato". Per non introdurre config prematura e divergente
(`feedback_concentrico_no_yagni`), il pinning per-step del flusso-less resta a **D4**; qui
l'ordine si accende a livello **pratica** (dettaglio/lista), che copre il bisogno primario
§6 del design ("vedere cosa sta accadendo senza uscire dalla pratica"). NON si forza
`flusso_id` sui `COLLEGATO` (`feedback_no_quick_fix_soluzione_assoluta`).

### (c) La regola dell'àncora vive solo nel frammento Python `_doc_sorgente_lateral`
Per D4 (GUIDA) il motore dovrà risolvere la **stessa** àncora a livello DB → la vista
`vw_pratica_doc_sorgente` del punto (b) è il posto giusto. Decisione di sequencing sotto.

## 6. Matrice di prontezza (fin dove arriva davvero il "portarci avanti")

| Dominio | Layer DB (D1+D2+D3) | Accensione MOSTRA | Livello a cui si vede |
|---|---|---|---|
| **Offerta** | ✅ in scope | con la futura pratica OFFERTA (ROOT-con-`flusso_id`) | percorso + dettaglio/lista |
| **Contratto** | ✅ in scope | con la futura pratica CONTRATTO (ROOT-con-`flusso_id`) | percorso + dettaglio/lista |
| **Ordine** | ✅ in scope (+ `vw_pratica_doc_sorgente`) | subito, via àncora pratica-level (nota b) | **dettaglio/lista** ora; percorso per-step → D4 |
| **Commessa** | ⚠️ fuori scope descrittore | — | non ha `stati_doc_*` a ciclo-vita (è PIPELINE_MARKER) |

> **Confermato da Tid (2026-07-02)**: OFFERTA/CONTRATTO ancorano ROOT-con-`flusso_id` →
> pienamente anticipabili. ORDINE acceso a livello pratica via `vw_pratica_doc_sorgente`
> (dettaglio/lista); il pinning per-milestone sul percorso è rinviato a D4 (richiede la mappa
> step→sorgente, condivisa con GUIDA). **Commessa**: modello a parte, fuori da questo giro.

## 7. Deliverable e file (numerazione: prossimo `NN` libero per data 2026-07-02+)

Un changeset per file, `logicalFilePath` sempre. Il team DB assegna gli `NN` effettivi.

**D1 (per dominio ×3):** alter `stati_doc_{offerte,ordini,contratti}` add `fase`/`esito`/
`terminale` + backfill mappa §2 + SET NOT NULL fase + CHECK fase + CHECK terminale⇒CHIUSO +
FK esito; changeset seed `esito` (UPDATE idempotente) in `80_data`; aggiornare le 3 CSV
(`+fase`,`+terminale`); agganciare trigger guard `trgfn_stati_doc_guard_esito_verdetto`.

**D2 (×3):** `20_code/vendite/…-create-vw-stato-sorgente-{offerta,ordine,contratto}-…yaml`.

**D3 (×1):** `20_code/script/…-update-vw-stato-sorgente-…yaml` — `CREATE OR REPLACE` con i
4 rami (nuovo file numerato, **mai** editare lo YAML mergiato — regola changelog).

**D3b (×1) — àncora pratica-level (scope 2, per l'ordine):**
`20_code/script/…-create-vw-pratica-doc-sorgente-…yaml`. `script.vw_pratica_doc_sorgente`:
per ogni `pratica_id` una riga col descrittore del **documento più vivo** (regola d'àncora
§5b: `ORDER BY (NOT terminale) DESC, ps.id DESC LIMIT 1` per pratica, join a
`vw_stato_sorgente`). È la promozione a DB della regola oggi inline nel BE (nota c): unica
sede, riusabile da D4.

**Nota (a) — indici a espressione (×4):** `((uid::text))` su preventivi/offerte_commerciali,
`((id::text))` su ordini/contratti (in `90_end` o `00_schema` per tabella).

**BE (follow-on, gated da D3b — lo faccio io dopo la consegna DB):** commutare l'àncora
**dettaglio/lista** di `_doc_sorgente_lateral` da ROOT-only al consumo di
`vw_pratica_doc_sorgente` → accende ordine/commessa a livello pratica. Percorso/coda
per-flusso invariati. Nessun altro intervento FE (già agnostico).

**pgTAP:** estendere `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` con i casi
per-dominio (§8 sotto) **+ `vw_pratica_doc_sorgente`** (pratica mono-doc → ROOT; pratica
evoluta preventivo-terminale→ordine-vivo → proietta l'**ordine**). **Doc**: manuali dei 3
resolver + `vw_pratica_doc_sorgente` + update `vw_stato_sorgente`,
`stati_doc_{offerte,ordini,contratti}`; rigenerare dbzero.

## 8. Criteri di accettazione

- Le tre `stati_doc_*` hanno `fase`/`esito`/`terminale` seedati secondo §2 (copertura 100%).
- `fn_stato_sorgente(tipo_offerta, uid)` su offerta **EMESSA** → `risolto=true, fase=IN_ATTESA,
  esito=NULL, terminale=false, stato_descrizione='Emessa'`; su **ACCETTATA** →
  `fase=IN_CORSO, esito=POSITIVO`; su **SUPERATA** → `fase=CHIUSO, esito=NEGATIVO, terminale=true`.
- `fn_stato_sorgente(tipo_ordine, id)` su **CONSEGNATO** → `fase=IN_CORSO, esito=NULL`; su
  **EVASO/FATTURATO** → `fase=CHIUSO, esito=POSITIVO, terminale=true`.
- `fn_stato_sorgente(tipo_contratto, id)` su **ATTIVO** → `fase=IN_CORSO`; su **CESSATO** →
  `fase=CHIUSO, esito=POSITIVO, terminale=true`; su **ANNULLATO** → `esito=NEGATIVO` (+`is_abortito` intatto).
- `script.vw_stato_sorgente` join-abile a `pratiche_sorgenti`: ≤1 riga per (tipo, uid) per ramo.
- Guard `is_verdetto` blocca `esito` di instradamento/inesistente su tutte e tre le tabelle.
- Un tipo sorgente ancora senza resolver → `UNKNOWN` (`risolto=false`) senza errore (invariato).

## 9. Sequenza consigliata

1. **DB — D1+D2+D3 sui 3 domini** + indici (a): additivi, nessun blocco. Offerta/contratto
   si accendono da soli con le future pratiche ROOT-con-`flusso_id`.
2. **DB — D3b** `vw_pratica_doc_sorgente` (regola d'àncora §5b confermata da Tid) + pgTAP.
3. **BE — commutazione àncora dettaglio/lista** su `vw_pratica_doc_sorgente` (gated da D3b):
   accende l'**ordine** a livello pratica. Lo eseguo io dopo la consegna DB.
4. **FE**: **nessun intervento** — già agnostico. Si accende per configurazione, non codice.
5. **D4 (dopo)**: pinning per-milestone del `COLLEGATO` sul percorso (mappa step→sorgente,
   condivisa con GUIDA) + "avanza-su-esito-proiettato". Fuori da questo giro.

---

*Brief vivo. A presa in carico: aggiornare lo stato in testa. A chiusura: riga V10 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) e stato del
[brief design](brief-design-proiezione-stato-dominio.md). Regola `feedback_db_actions_passaggio_team`:
DDL/trigger/viste/pgTAP eseguiti dal team DB su `dev/db-tid`, non da qui.*
