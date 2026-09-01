# Brief DB — `riferimento` si risolve dalla sorgente, non dal motore di fatturazione

> **Tipo**: brief al team DB · **Aperto**: 2026-08-18 · **Riscritto**: 2026-09-01
> · **Richiedente**: perimetro BE · **Destinazione**: `dev/db-tid`
> · **Stato**: 🟢 **DB fatto** — `20260901-04` applicato il 2026-09-01 12:31,
> pgTAP verdi, baseline `vendite` senza regressioni. ⬜ Resta da applicare
> `20260901-05` (sola correzione di due frasi nel `COMMENT ON VIEW`).
>
> **Origine**: DL-2 di
> [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md)
> §10.
>
> ⚠️ **Riscrittura del 2026-09-01.** La prima stesura era motivata su una misura
> («il 78% del tempo») e proponeva due strade che la verifica ha smentito
> entrambe. Il testo di allora è conservato al §10, **marcato**, perché il motivo
> per cui era sbagliato è la cosa più utile del documento.

---

## 1. Il difetto, sul modello

`vendite.vw_dash_competenza_gruppi` deve scrivere accanto a ogni gruppo **il
riferimento leggibile del documento sorgente** — `PRV0000202`, `ORD0005174` — e
il suo id, perché la riga possa essere aperta.

Per ottenerli risolve il documento attraverso
`vendite.vw_dash_fatturazione_documenti`, cioè una `UNION ALL` dei **sei
resolver** della fatturazione, ognuno dei quali ricalcola valori, righe,
transitato e motivo di fermo — e poi tiene **due colonne**, buttando il resto.

Tre cose, tutte strutturali:

1. ⛔ **Il predicato non è indicizzabile sotto RLS, e non può diventarlo.**
   Il confronto è `(uid)::text = sorgente_uid`. Il cast `uuid → text` non ha una
   entry in `pg_cast`: è un `CoerceViaIO`, e `contain_leaked_vars()` lo dichiara
   *leaky* perché `uuid_out` e `textin` hanno entrambe `proleakproof = f`. Un
   quale leaky **non può mai essere valutato prima del security qual della RLS**,
   quindi non può diventare un `Index Cond`. Non è una scelta del planner: è una
   regola sua.
2. ⛔ **La `LATERAL` ricostruisce il resolver intero dell'area del gruppo, una
   volta per gruppo.** Il piano contiene sei `Seq Scan` — `preventivi`,
   `ordini`, `ddt`, `contratti`, `offerte_commerciali`, `commesse` — perché
   `d.area = s.area` è un quale **correlato** e l'`Append` non si pota in fase di
   piano.
   ⚠️ **A runtime però quattro rami non partono**, e la prima stesura di questo
   §1.2 diceva il contrario: ogni ramo della UNION emette un'area **costante**,
   quindi il confronto diventa un `One-Time Filter: ('PREVENTIVI'::text =
   (s.area)::text)` per ramo, e i non corrispondenti risultano `never executed`.
   Verificato il 2026-09-01: su 48 gruppi, `loops=31` sul ramo preventivi e
   `loops=17` su ordini — uno per gruppo, non sei.
   ⭐ **Il costo vero è che quell'uno è il resolver completo**: per un gruppo
   preventivi si scandisce tutta `vendite.preventivi`, si uniscono le righe, si
   passa da `vw_preventivi_smistamento_righe`, si aggrega — e poi si tiene una
   riga, per due colonne. I buffer lo dicono: 21.813 sul ramo preventivi e 7.109
   su ordini, su 31.789 totali.
3. ⭐ **La primitiva esiste già, ed è usata dalla lente gemella.**
   `vendite.fn_get_sorgente_documento_ref(sorgente_tipo_id, sorgente_uid)`
   restituisce `(documento_id, documento_numero)` — esattamente le due colonne —
   leggendo **una** tabella, quella dichiarata da `config.sorgenti.target_table`,
   con `WHERE t.uid = $1` passando `USING v_uid::uuid`: la forma leakproof, che
   sotto RLS prende l'index scan. È già il resolver di
   `fn_list_commessa_attivita`, `fn_annulla_commessa_attivita` e
   `fn_genera_ddt_riconsegna`.

**L'argomento regge senza nessun numero**: la vista duplica, attraverso una union
dell'intero motore di fatturazione e con un predicato che la RLS non può
indicizzare, un building block che il progetto già possiede. Vale a 1 gruppo e a
4.500.

### 1.1 ⭐ E la pagano anche due lettori che quella colonna non la leggono

Verificato il 2026-09-01 sui piani, come `zeroerp_app`:

| Chi legge la vista | Usa `riferimento` | Apre le sei testate |
| --- | --- | --- |
| la lista gruppi | ✅ sì | ✅ sì — legittimo |
| `vw_dash_competenza_gruppi_riepilogo` (totali + facet) | ⛔ **no** | ✅ **sì** |
| `fn_list_emittibili_lane` | ⛔ no | ✅ sì |

PostgreSQL **non può eliminare una `LEFT JOIN LATERAL` inutilizzata** — la join
removal non copre le LATERAL. Quindi i totali in cima alla schermata e le facet
delle tendine risolvono il documento per ogni gruppo **e poi buttano via il
risultato**. ⚠️ «Apre le sei testate» è la forma del **piano**: a runtime ne
parte una per gruppo (§1.2). Il costo resta, perché quell'una è il resolver
completo.

⚠️ **Non è un argomento di velocità**, ed è il punto: se lo fosse, una vista
materializzata sarebbe una risposta legittima. È che due lettori su tre pagano
una risoluzione **che non chiedono**, e nessuno dei due può evitarla — la forma
della vista non gliene dà modo.

## 2. La verifica — fatti datati, non motivi

Tutto letto il **2026-09-01**, sul DB di sviluppo, in sola lettura.

**Contratto** (decide):

| Cosa | Valore |
| --- | --- |
| `pg_cast` per `uuid → *` | nessuna entry → il cast è `CoerceViaIO` |
| `proleakproof` | `uuid_out = f`, `textin = f`, `texteq = t`, `uuid_eq = t` |
| policy su `vendite.preventivi` | `rls_preventivi_ef_whitelist`, via `script.fn_scope_ef_whitelist` (che inlina in `fn_check_user_emittente_scope` — è il nome che compare nei piani) |
| tipo di `vw_dash_competenza_gruppi.riferimento` | `text` |
| tipo di `vw_dash_competenza_gruppi.documento_id` | `bigint` |
| firma del resolver | `TABLE(documento_id bigint, documento_numero text)` |
| grant sul resolver | `zeroerp_app`, `zeroerp_batch_fatturazione` hanno `EXECUTE` |
| `config.sorgenti` | `target_table` e `label_selector` valorizzati per **tutte e sei** le aree |

**Piani** (la prova, stessa query, tre ruoli):

| Corsa | Predicato | Piano |
| --- | --- | --- |
| `zeroerp_app`, RLS attiva | `(uid)::text = 'zzz'` | **Seq Scan** — il quale nel Filter *dopo* la policy |
| `zeroerp_app`, RLS attiva | `uid = '…'::uuid` | **Index Scan** `uq_preventivi_uid` — `Index Cond` *prima* del Filter |
| `titodb` (owner), niente RLS | `(uid)::text = 'zzz'` | **Index Scan** `ix_preventivi_uid_text` |

⭐ La terza riga è quella che chiude il discorso: l'indice funziona, ma **solo
dove la RLS non c'è**. Sul percorso applicativo è morto per costruzione.

## 3. Il difetto che si vede a video

Non è solo prestazioni. Quando il resolver non trova il documento,
`riferimento` ripiega su `COALESCE(…, commessa_codice, gruppo_key)`.

⚠️ **E il ripiego che scatta è il PRIMO dei due, sempre**: `vendite.commesse.codice`
è `NOT NULL` e `commesse_attivita.commessa_id` pure, quindi per un gruppo
documento `commessa_codice` c'è sempre e la `gruppo_key` **non è raggiungibile**.

⭐ **Questo rende il difetto peggiore, non minore.** Una `gruppo_key` a video —
`PREVENTIVO:01a0581a-…` — si vede che è rotta. Un codice commessa
(`CMM-…-000000003`) sembra un valore legittimo: la riga **nomina un oggetto
diverso** da quello di cui parla, e nessuno se ne accorge. È esattamente il
difetto che il FE si è già trovato a correggere sull'azione «Apri commessa» —
*«portava a un oggetto DIVERSO da quello scritto nella riga»*.
Verificato sul caso fabbricato (2026-09-01): risoluzione vecchia →
`riferimento = CMM-PGTAPEF202-2026-000000003`, `documento_id = NULL`;
risoluzione nuova → `PGTAP-VGRIF`, id della revisione spinta.

E `riferimento` **non è solo un'etichetta**: è colonna di **ricerca libera** e di
**ordinamento** (`DASH_COMPETENZA_GRUPPI_SEARCH_COLUMNS` /
`…_SORT_COLUMNS` in `backend/apps/vendite/db/vendite_repository.py`). Quindi su
quelle righe **la ricerca per numero non le trova**: chi cerca `PRV0000202` non
trova la riga che *è* PRV0000202.

⚠️ E `documento_id` esce dalla **stessa riga** — è deliberato, il BE lo dichiara
(«codice e id non possono più descrivere documenti diversi»). Quindi nello
stesso caso **sparisce anche la voce «Apri documento»** dal kebab.

### 3.1 Quando succede — due forme, entrambe ammesse dal modello

**a) Preventivo superato da una revisione.** `vw_dash_fatturazione_preventivi`
filtra `WHERE p.is_attiva`, e in `vw_preventivi`
`is_attiva = NOT is_abortito AND NOT is_superata`. Si spingono le attività dalla
rev. 0, si crea la rev. 1 → la rev. 0 diventa `is_superata` e cade fuori dal
resolver. Verificato che il caso non è chiuso da nessuna parte:
`fn_crea_revisione_preventivo` **non tocca** `commessa_attivita`, e
`trgfn_doc_ritira_commessa_attivita` scatta **solo** all'ingresso in uno stato
abortito.

**b) DDT con causale non fatturabile.** `vw_dash_fatturazione_ddt` filtra
`caus.fatturabile IS TRUE`. Il push controlla la causale, ma **nessuno la
ricontrolla dopo**, e `causale_trasporto_id` non è fra le colonne bloccate.
→ vedi la voce aperta al §7.

⚠️ In entrambe le forme le attività **restano fatturabili e vanno in fattura**:
il gruppo perde il nome, non il contenuto.

## 4. La direzione

> `riferimento` e `documento_id` si risolvono con
> `vendite.fn_get_sorgente_documento_ref(g.sorgente_tipo_id, g.sorgente_uid)`,
> e `vw_dash_fatturazione_documenti` torna a essere quello per cui è nata — la
> sorgente delle due lenti, non una tabella di lookup.

```sql
-- prima
LEFT JOIN LATERAL (
  SELECT d.codice, d.documento_id
    FROM vendite.vw_dash_fatturazione_documenti d
   WHERE s.area IS NOT NULL AND d.area = s.area AND d.documento_uid = g.sorgente_uid
   ORDER BY d.competenza_mese DESC NULLS LAST LIMIT 1) doc ON true

-- dopo
LEFT JOIN LATERAL vendite.fn_get_sorgente_documento_ref(
           g.sorgente_tipo_id, g.sorgente_uid) doc ON true
```

```sql
COALESCE(doc.documento_numero, g.commessa_codice, g.gruppo_key) AS riferimento
doc.documento_id
```

⭐ **Sparisce anche il `LIMIT 1`, ed è un guadagno di sostanza.** Quel `LIMIT`
non era una scelta: `vw_dash_fatturazione_documenti` **non è unica per
documento** — `vw_dash_fatturazione_commesse` raggruppa per `ca.competenza_mese`,
quindi una commessa emette una riga per mese. Era de-duplicazione forzata dalla
sorgente sbagliata. Col resolver il documento è unico per costruzione, e il
presidio anti-fan-out (§6) smette di dipendere da un «prendine una».

⭐ **Il giro è un `CREATE OR REPLACE` semplice**: i tipi coincidono già
(`text`/`bigint` da una parte e dall'altra), quindi nessun `DROP`, nessun cascade
su `vw_dash_competenza_gruppi_riepilogo`, nessuna colonna che cambia nome, tipo o
posizione.

### 4.1 Decisioni prese (Tid, 2026-09-01)

- **D-1 · Quale revisione apre il pulsante** → **la revisione spinta**, non la
  corrente. È quella da cui vengono quantità e prezzi che si stanno per
  fatturare; aprire la corrente mostrerebbe righe diverse da quelle in fattura
  senza dirlo. ⭐ È anche il comportamento che si ottiene **senza scrivere
  niente**: il resolver risolve per `uid`, e l'uid è quello della riga spinta.
  ⚠️ Il testo a video è **identico** nei due casi (`PRV0000202`):
  `label_selector` è `numero`, condiviso fra le revisioni. La decisione riguarda
  solo l'id dell'azione.
- **D-2 · Nessun filtro di lista sulle causali non fatturabili** in questo
  cantiere. Il perché sta al §7.

### 4.2 Piano B, se il costo per chiamata non convincesse

⚠️ `fn_get_sorgente_documento_ref` è plpgsql con `EXECUTE` dinamico: il piano
**non viene cachato**, si ri-pianifica a ogni chiamata — una per gruppo. È il
prezzo dell'astrazione da catalogo, e va **misurato** al passo P-2, non dato per
scontato.

Ripiego: una vista **sottile** a sei rami (`SELECT area, uid::text, numero, id
FROM …`, nessuna aggregazione) in **hash join** invece che in `LATERAL` — una
passata sola sulle sei testate, non una per gruppo. ⛔ Ma duplica ciò che
`config.sorgenti` già codifica, e un tipo sorgente nuovo richiederebbe di editare
la vista invece che il catalogo. È ripiego, non prima scelta.

## 5. I passi

| # | Cosa | Dove |
| --- | --- | --- |
| **P-1** | changeSet `CREATE OR REPLACE VIEW` | `20_code/vendite/20260901-NN-update-vw-dash-competenza-gruppi-riferimento-da-sorgente-mctit.yaml` |
| **P-2** | prova del piano **prima** di chiedere l'apply | SQL **estratto dallo YAML**, in `BEGIN; … ROLLBACK;`, come `zeroerp_app` con contesto operatore |
| **P-3** | ✅ pgTAP — 6 test nuovi, 8 suite affette riverificate | §6 |
| **P-4** | ✅ baseline `vendite` — 5 rossi su 259, **tutti noti**, zero regressioni | `scripts/pgtap-baseline.sh vendite` |
| **P-5** | ✅ doc manuale della vista | `docs/it/dbzero/vendite/manual/vw_dash_competenza_gruppi.md` |
| **P-6** | ⬜ changeSet `20260901-05` — corregge due frasi del `COMMENT ON VIEW`, **da applicare** | §5.3 |

### 5.1 · Esito di P-2 — provato il 2026-09-01, **non applicato**

SQL **estratto dallo YAML** (non trascritto) ed eseguito dentro
`BEGIN; … ROLLBACK;` scritto nel file eseguito.

⚠️ `SET ROLE zeroerp_app` è **negato** — l'owner non è membro di quel ruolo.
Si è usata la tecnica già in uso nei pgTAP RLS del progetto:
`FORCE ROW LEVEL SECURITY` sulle sei testate dentro la transazione, che rende
l'**owner** soggetto alle policy; l'identità la simulano le GUC `app.*`. Le due
misure sotto sono prese così su **entrambi** i lati, quindi sono confrontabili.

| | testate di documento aperte | nodi del piano |
| --- | --- | --- |
| lista gruppi | **6 → 0** | 159 → 37 |
| riepilogo (totali + facet) | **6 → 0** | 161 → 39 |

Controlli di non-regressione, tutti verdi:

- **firma invariata** — zero colonne diverse per nome, tipo o posizione (30 su 30);
- **`security_invoker=on`** prima e dopo;
- **rollback pulito** — definizione originale ripristinata, nessuna tabella
  lasciata con `FORCE`.

### 5.2 · Esito post-apply — applicato il 2026-09-01 12:31

`databasechangelog`: `20260901-04-…` `EXECUTED`, ordine 14842. Vista viva sul
resolver, `security_invoker=on` intatta.

**Correttezza — competenza giugno 2026, 48 gruppi, come `zeroerp_app`:**

| Confronto vecchia vs nuova risoluzione | righe |
| --- | --- |
| `riferimento` e `documento_id` **identici** | **48 / 48** |
| divergenti | 0 |
| recuperate (prima chiave grezza, ora numero) | **0** |

⭐ **Le zero righe recuperate sono il dato più importante di questa tabella.**
Sui dati di oggi il caso rotto (§3.1) **non ha occorrenze**: nessun preventivo
superato con attività spinte, nessun DDT con causale cambiata dopo il push. È
esattamente il motivo per cui i test di P-3 devono **fabbricarsi** il caso — un
test che lo cercasse fra questi dati sarebbe verde per sottrazione.
⛔ E non è un argomento per non fare il lavoro: zero occorrenze non significa che
il caso non esiste, significa che non c'è ancora un controesempio.

**Costo — stessa sessione, stesso ruolo, stessi dati:**

| | tempo | buffer |
| --- | --- | --- |
| lista nuova, intera (48 righe) | **23,97 ms** | **2.860** |
| la sola risoluzione vecchia, rimessa sopra per confronto | **~2.850 ms** | **~28.900** |

⚠️ **Non confrontabili con i 166 ms del §10**: mese e popolazione diversi, e le
tabelle sono cresciute dal 18 agosto. Confrontabili sono le due righe fra loro.

Vincoli sul changeSet, tutti già presidiati altrove:

- ⚠️ `WITH (security_invoker=on)` **ri-specificata**: non compare in
  `pg_get_viewdef` e PostgreSQL la azzera in silenzio → bypass RLS;
- ⚠️ il corpo si copia dalla **doc auto-gen**, non da uno YAML storico;
- ⚠️ `runOnChange: false` (in `20_code` il `true` è vietato dal guardrail CI),
  `logicalFilePath`, un changeSet per file;
- ⚠️ il numero `NN` è **globale per data** e scade nel minuto: ricontrollarlo
  subito prima di salvare;
- ⚠️ negli YAML si cita il **nome** del brief, mai il path `work-in-progress/`;
- ⚠️ `liquibase updateSQL` non gira in locale: l'SQL si rende **dallo YAML**.

⛔ **Nessuna migrazione viene applicata da questo brief.** L'autorizzazione la dà
Tid a parole, per quel comando.

### 5.3 · P-6 — `20260901-05`, due frasi sbagliate nel commento della vista

⛔ **Scritto, provato in `BEGIN/ROLLBACK`, NON applicato.** Non tocca DDL: la
definizione della vista e `security_invoker=on` restano quelle del `-04`.

Il `-04` ha lasciato nel `COMMENT ON VIEW` due affermazioni false. Entrambe sono
state trovate **dopo** l'apply, misurando:

1. *«apriva SEI Seq Scan per gruppo, perché `d.area = s.area` è correlato e non
   pota l'Append»* → sei è la forma del **piano**; a runtime quattro rami sono
   `never executed` (§1.2).
2. *«`riferimento` ripiegava sulla gruppo_key (a video «PREVENTIVO:01a0…»)»* →
   ripiega sul **codice commessa**; la gruppo_key è irraggiungibile (§3).

⭐ **Perché valgono un changeSet e non una riga di brief.** La prima insegna che
l'`Append` non si pota **mai** su un quale correlato: è falso, e chi diagnostica
un caso simile progetterebbe intorno a un vincolo che non esiste. La seconda fa
sembrare il difetto più visibile di quanto sia, e quindi meno urgente. *Un
commento che sbaglia il meccanismo è peggio di un commento assente: viene
creduto.*

⚠️ Nessuna delle due tocca la conclusione del `-04`, e la seconda la rafforza.

## 6. pgTAP

**Da tenere verdi** (sette file citano la vista; questi due asseriscono sul dato
che cambia sorgente):

- `test-vw-dash-competenza-gruppi-v1.sql` test 6 (*riferimento = numero
  documento*) e test 7 (*oneri → codice commessa*);
- `test-vw-dash-competenza-gruppi-cliente-v1.sql` test 3 (anti-fan-out).

⭐ **Il test 3 va guardato con occhi nuovi.** Oggi è verde grazie al `LIMIT 1`.
Tolto quello, deve restare verde perché il documento è unico *per costruzione*.
Se va rosso, è il segnale che il resolver restituisce più di una riga — e va
fermato lì, non aggirato.

**Da scrivere**, e il caso se lo **fabbricano**: un test che confronta la
popolazione esistente passerebbe a vuoto su un DB ricostruito da zero, cioè in
CI.

1. **Preventivo superato da revisione, con attività spinte** → `riferimento` è il
   numero (non la `gruppo_key`) e `documento_id` è l'id della revisione
   **spinta** (D-1). È il test che oggi sarebbe rosso, ed è il motivo del
   cantiere.
2. **La grana resta `(gruppo, stadio)` senza il `LIMIT 1`** — il conteggio righe
   non cambia su un gruppo la cui sorgente emette più righe nella vista vecchia.

Preambolo obbligatorio (`BEGIN;`, riga di contesto, `SET CONSTRAINTS ALL
IMMEDIATE`), da `db/pgtap/_TEMPLATE.sql.txt`.

## 7. Voce aperta — il cambio causale su un DDT già spinto

**Non è di questo cantiere**, ma è emersa qui e va registrata.

Verificato il 2026-09-01: la causale è controllata **solo al push**
(`fn_list_ddt_da_pushare`, `fn_ddt_push_diagnosi`); **nessuno la ricontrolla al
momento di fatturare**; `causale_trasporto_id` **non è bloccata**
(`dbops.automation_lock_columns` per il DDT ha solo `numero`, per giunta
`enabled = f`); il ritiro è montato sul DDT ma scatta **solo** sull'ingresso in
uno stato abortito.

Quindi: si cambia la causale in non fatturabile dopo il push → **le attività
restano, restano fatturabili, e vanno in fattura lo stesso**.

⛔ **La risposta NON è un filtro che le esclude dalla lista.** Nasconderebbe un
gruppo le cui attività finiscono in fattura comunque: lavoro che sparisce dallo
schermo ma non dal database. Il progetto ha già una posizione scritta su questa
forma, per il caso gemello dei gruppi bloccati — *«Segnalare, non nascondere»*
(brief emittibilità §3.1): lucchetto col motivo, accanto al nome.

⭐ **Il meccanismo giusto esiste già.** «Questo documento non alimenta più la
fatturazione» è esattamente l'evento che `trgfn_doc_ritira_commessa_attivita`
gestisce per l'annullamento. Due candidate:

1. **estendere il ritiro al cambio causale** — coerente col motore che c'è;
2. **bloccare la colonna** — ⛔ ma impedirebbe anche una correzione legittima su
   un DDT mai spinto.

La prima è quella da valutare. Cantiere suo.

## 8. Cosa NON si tocca

- **`vw_dash_fatturazione_documenti` e i sei resolver**: restano la sorgente di
  `vw_dash_backlog_documenti` e `vw_dash_aperto_documenti`, che il motore intero
  lo vogliono davvero. Cambia solo chi li usava come tabella di lookup.
- **`fn_get_sorgente_documento_ref`**: si usa, non si modifica.
- **`config.sorgenti`**: già completo, nessun seed.
- **`backend/`**: perimetro DB.
- ⛔ **Nessun indice nuovo.** Quelli funzionali sui cinque rami mancanti sarebbero
  **morti alla nascita** (§2).

### 8.1 ⛔ `ix_preventivi_uid_text` NON è orfano — il censimento smentisce

Chiudendo il cantiere avevo scritto che l'indice restava «orfano, da censire in
un giro suo». **Era una congettura, e il censimento del 2026-09-01 la smentisce.**

| Indice su `vendite.preventivi` | `idx_scan` |
| --- | --- |
| `pk_preventivi` | 2.314.872 |
| `uq_preventivi_numero_rev` | 404.197 |
| **`ix_preventivi_uid_text`** | **45.862** |
| `uq_preventivi_uid` | 3.535 |
| `ix_preventivi_emittente_fiscale_id` | 3 |

È il **terzo** più usato, quattordici volte più della UNIQUE su `uid`.

⭐ **E il motivo è la stessa diagnosi del §2, letta al contrario.** Il quale
`(uid)::text = …` è bloccato dalla barriera RLS **solo per chi la RLS ce l'ha**.
Non ce l'hanno:

| Chi | Perché |
| --- | --- |
| `titodb` | è l'**owner** di `vendite.preventivi`, e `relforcerowsecurity = false` |
| `zeroerp_batch_fatturazione` | **`BYPASSRLS`** |
| `postgres` | superuser |

⚠️ **Il ruolo batch della fatturazione scavalca la RLS**: per lui quell'indice
non è mai stato morto. «Inutilizzabile» valeva per `zeroerp_app`, e solo per lui.

**Cosa servirebbe per decidere, e perché non basta il numero qui sopra:**

1. il contatore è **cumulativo** — `pg_stat_database.stats_reset` è `NULL`, mai
   azzerato — quindi include tutto il periodo in cui la vista vecchia era viva e
   le migrazioni giravano da owner. Serve un **delta**: valore di oggi
   (**45.862**, 2026-09-01), riletto dopo qualche ciclo del batch;
2. `pg_stat_statements` **non è installata**, quindi le scansioni non sono
   attribuibili a una query. Senza, l'attribuzione si fa leggendo il codice dei
   consumatori batch;
3. il censimento va fatto sulla **lettura**, non sulla parola: nessuna delle 14
   viste che contengono `(uid)::text` lo usa come **predicato** (verificato: zero
   occorrenze di `(uid)::text =`), lo producono come colonna di output. Chi
   confronta è codice applicativo o batch, non una vista.

⛔ **Quindi: non si tocca.** Non per prudenza generica — perché la misura dice il
contrario di quello che avevo supposto, e perché il lettore plausibile è un ruolo
`BYPASSRLS` che non passa da nessuna delle viste censite.

## 9. Per BE e FE — nessun codice, due effetti da annunciare

- **BE-1** — nessuna modifica richiesta: `riferimento` e `documento_id`
  conservano nome, tipo e posizione.
- **BE-2, da sapere** — la ricerca libera su `g.riferimento` resta **senza indice
  trigram**. Migliora di molto (una lookup per gruppo invece di sei scansioni) ma
  non diventa indicizzata: il DL-2 *«ancorare la ricerca alla sorgente del
  documento»* **resta aperto**.
- **FE-1, effetto atteso senza codice** — sulle righe che oggi mostrano il
  **codice commessa** al posto del numero documento (§3) comparirà il numero, e
  **riapparirà la voce «Apri documento»**. Va annunciato, altrimenti si legge
  come un difetto nuovo.
- **FE-2, debito** — `gruppoRiferimento()` in `DashboardCompetenzaView.vue`
  ripete la catena di ripiego del DB. Dopo la correzione è codice morto. Fuori
  perimetro, da valutare.

## 10. ⛔ La prima stesura, e perché era sbagliata

Conservata perché l'errore è istruttivo, non per cronaca.

**Come era motivata.** Su una misura: *«`EXPLAIN` su 45 righe: 166 ms, di cui il
78% nella `LATERAL`»*, con una proiezione — *«450 gruppi → ~1,3 s»*. È la forma
che [AGENTS.md §«Regola zero»](../../../../.codex/AGENTS.md) rifiuta: una
previsione sui dati travestita da progetto. Togliendo la misura l'argomento si
affloscia; l'argomento vero (§1) non ha bisogno di nessun numero.

**Le due strade che proponeva, entrambe smentite:**

1. ⛔ *«Rendere utilizzabile l'indice dove già esiste»* — **non ha soluzione**.
   Non c'è niente da sbloccare: finché il cast è nel predicato, sotto RLS
   quell'indice non è raggiungibile (§2). Era presentata come «la correzione più
   economica».
2. ⛔ *«Aggiungere l'indice funzionale ai cinque rami che non ce l'hanno»* —
   costruirebbe **cinque indici morti**, per lo stesso motivo. Era il ripiego
   pratico.
   ⛔ E la variante «cura», *allineare il tipo di `sorgente_uid` a `uid`*, **non è
   applicabile**: `sorgente_uid` è `text` per progetto — è la chiave sorgente
   polimorfa governata da `config.sorgenti.key_selector`, e per `COMMESSA` il
   valore è `commesse.id::text`. La commessa non ha `uid`.

**Cosa non vedeva.** Che anche con l'indice perfetto la `LATERAL` avrebbe aperto
sei testate per gruppo (§1.2), e che il resolver a tabella singola era già in
casa (§1.3). Il §2.2 di allora — *«il campione non è il caso peggiore, è quello
fortunato»* — aveva ragione nella conclusione e torto nel motivo: non conta quale
ramo abbia l'indice, i rami girano tutti e sei sempre.

**Cosa resta buono di quella stesura**, ed è parecchio: il titolo (il costo non è
la ricerca), il vincolo che *«deve valere per tutti e sei i rami»*, l'avvertenza
di misurare **con la RLS attiva** e non da owner, e il §6 *«non togliere
`riferimento`: il problema è come si ottiene, non che ci sia»*.

## 11. Definizione di «fatto» — sulla struttura, non sui millisecondi

- [ ] il piano di `vw_dash_competenza_gruppi` **non contiene più** le sei
      `Seq Scan` sulle testate;
- [ ] ⭐ e non le contiene nemmeno il piano di
      `vw_dash_competenza_gruppi_riepilogo` (§1.1): è il lettore che quella
      risoluzione non l'ha mai chiesta, ed è la prova che la forma è cambiata e
      non solo il costo;
- [ ] `riferimento` non è mai la `gruppo_key` quando il documento **esiste**,
      revisione superata compresa;
- [ ] `riferimento` e `documento_id` continuano a descrivere **lo stesso**
      documento;
- [ ] la grana resta `(gruppo, stadio)` **senza** un `LIMIT 1` a difenderla;
- [ ] `security_invoker` ancora attiva (`test-vw-dash-security-invoker` verde);
- [ ] baseline `vendite` senza regressioni.

## 12. Riferimenti

| Cosa | Dove |
| --- | --- |
| Vista da correggere | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi.md` |
| Resolver da usare | `docs/it/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref.md` |
| Union a sei rami (resta com'è) | `docs/it/dbzero/vendite/views/vw_dash_fatturazione_documenti.md` |
| Catalogo delle sorgenti | `docs/it/dbzero/config/manual/sorgenti.md` |
| DL-2 che ha aperto il cantiere | [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md) §10 |
| Presidio anti-fan-out | `db/pgtap/vendite/test-vw-dash-competenza-gruppi-cliente-v1.sql` test 3 |
| Presidi su `riferimento` | `db/pgtap/vendite/test-vw-dash-competenza-gruppi-v1.sql` test 6-7 |
