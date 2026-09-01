# Brief DB — `riferimento` si risolve dalla sorgente, non dal motore di fatturazione

> **Tipo**: brief al team DB · **Aperto**: 2026-08-18 · **Riscritto**: 2026-09-01
> · **Richiedente**: perimetro BE · **Destinazione**: `dev/db-tid`
> · **Stato**: 🟢 **DB fatto** — `20260901-04` applicato il 2026-09-01 12:31,
> pgTAP verdi, baseline `vendite` senza regressioni. 🟢 **Anche `20260901-05`
> applicato** (sola correzione di due frasi nel `COMMENT ON VIEW`): la doc
> auto-gen di `vw_dash_competenza_gruppi` riporta il testo corretto, quindi il
> commento vivo e' quello del `-05`. ⚠️ Questa riga diceva *«resta da
> applicare»*: era stantia, corretta il 2026-09-01 al passo BE/FE.
> · 🟢 **BE/FE fatto** — vedi §9.
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
| **P-6** | ✅ changeSet `20260901-05` — corregge due frasi del `COMMENT ON VIEW` | §5.3 |
| **P-7** | ✅ BE/FE — contratto stretto, catena di ripiego duplicata rimossa | §9 |

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

✅ **Applicato** (verificato il 2026-09-01 dal passo BE/FE: la doc auto-gen della
vista riporta il testo di questa revisione, non quello del `-04`). Non tocca DDL:
la definizione della vista e `security_invoker=on` restano quelle del `-04`.
⚠️ Questo capoverso diceva *«scritto, provato in `BEGIN/ROLLBACK`, NON
applicato»*, ed era rimasto indietro rispetto all'apply.

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

## 9. Per BE e FE — 🟢 fatto il 2026-09-01

La previsione era *«nessun codice»*. È rimasta vera sulla **lettura** — nessun
adeguamento è stato necessario per far funzionare la vista nuova — e falsa su una
cosa che il giro ha reso visibile: il ripiego duplicato non era solo debito, era
**legittimato da una dichiarazione di tipo sbagliata**. Le due cose si tolgono
insieme o non si toglie nessuna delle due.

| | Cosa | Esito |
| --- | --- | --- |
| **BE-1** | nessuna modifica di lettura: `riferimento` e `documento_id` conservano nome, tipo e posizione | ✅ confermato — e il presidio contro il ritorno di una seconda risoluzione lato Python era già in casa (`test_id_documento_dalla_vista_non_da_una_seconda_risoluzione`) |
| **BE-1b** | `DashCompetenzaGruppoRow.riferimento` dichiarava `str \| None` | ✅ stretto a `str` (decisione di Tid, 2026-09-01) — vedi sotto |
| **BE-1c** | il MAPPING del repository emetteva ancora `None` in un campo dichiarato non-nullable | ✅ corretto — trovato dalla revisione critica, §9.4 |
| **BE-1d** | il commento della whitelist di ricerca descriveva la LATERAL a sei rami | ✅ corretto — §9.4 |
| **BE-2** | ricerca libera su `g.riferimento` senza indice trigram | ⬜ **resta aperto**: il DL-2 *«ancorare la ricerca alla sorgente del documento»* è cantiere suo |
| **FE-1** | sulle righe che mostravano il **codice commessa** compare il numero e **riappare «Apri documento»** | ✅ nessun codice — e il percorso a valle regge: D-1 apre la revisione **spinta**, cioè `is_superata = true`, che `PreventiviDrawer` già riconosce (tag «superseded», banner, readonly) |
| **FE-2** | `gruppoRiferimento()` ripeteva la catena di ripiego del DB | ✅ **rimossa** |
| **FE-3** | il toast dei gruppi «non serviti» nominava la COMMESSA | ✅ corretto — §9.2 |
| **FE-4** | `row.riferimento ?? ''` difendeva da un caso che il contratto esclude | ✅ tolto — §9.4 |
| **P** | il contratto stretto non aveva presidio | ✅ `test_mapping_espone_riferimento_non_nullo` (24-octies) |
| **D** | doc API dell'endpoint | ✅ `docs/it/backend/vendite/manual/api_dashboard_competenza.md` — §9.5 |

### 9.1 · Perché il tipo si stringe, e perché prima di togliere il ripiego

`riferimento` era dichiarato `str | None` in `backend/apps/vendite/types.py`. La
vista non può produrre NULL: il `COALESCE` finisce su `gruppo_key`, che è la
chiave del gruppo. ⭐ **Finché il contratto ammetteva il NULL, il ripiego nel
frontend era difendibile** — e infatti c'era. Il difetto non era la riga di
frontend: era la dichiarazione che la giustificava.

⭐ **E l'argomento per togliere il ripiego non è sui dati, è sulla forma.** La
catena FE era `riferimento || commessa_codice || gruppo_key`, e `riferimento`
**è** `COALESCE(documento_numero, commessa_codice, gruppo_key)`: il 2° e il 3°
termine sono gli stessi due del `COALESCE`, quindi **irraggiungibili per
costruzione**. Non «oggi non capitano»: non possono capitare. Era la stessa
regola scritta in due posti, cioè la forma in cui le due copie divergono.

### 9.2 · FE-3 — la stessa specie di difetto, in un toast

Il messaggio dei gruppi richiesti ma rimasti fuori li nominava con
`commessa_codice || gruppo_key`, mentre la lista sopra li nomina con
`riferimento`. ⭐ **È il §3 su un'altra superficie**: lo stesso gruppo con due
nomi a seconda di dove lo si legge, e il codice commessa che «sembra un valore
legittimo». Ora entrambi passano da `etichettaGruppoKey(key, ripiego)`, col
codice commessa come ripiego per le righe uscite dalla lista nel frattempo.

⚠️ Il `ripiego` è un **parametro** e non un ramo fisso perché i due percorsi
hanno in mano cose diverse: «non serviti» porta anche il codice commessa,
«fatturati altrove» le sole chiavi.

⛔ E non va passata **nuda** a `elencoTroncato`, che fa `.map(fmt)`: passerebbe
l'**indice** come `ripiego`. Il call site di «fatturati altrove» è stato avvolto
per questo — un difetto che sarebbe uscito muto, con un `1` a video al posto di
un numero documento.

### 9.3 · Collaudo — e cosa NON prova

Verde: `apps.vendite.tests` (**1866**, +1 nuovo), `apps.core.tests` (832),
`scripts/check_i18n_keys.py`, build Vite. Il conteggio delle `DataTable` grezze è
invariato (57).

⚠️ **Il collaudo in-app di FE-1 non è esercitabile sui dati di oggi**: il caso
rotto ha **zero occorrenze** (§5.2). Chi lo cercasse fra questi dati leggerebbe
un verde per sottrazione. O si fabbrica il caso — revisione su un preventivo con
attività spinte — o si dichiara **non esercitato**. Il presidio vero resta il
pgTAP di P-3, che il caso se lo costruisce.

### 9.4 · ⭐ La revisione critica, e perché è la parte più utile di questo §

Il giro «togli il ripiego + stringi il tipo» era **dichiarato finito e non lo
era**. Una rilettura critica ha trovato tre cose, e la prima è dello **stesso
difetto** che il cantiere stava correggendo, spostato di un livello.

1. ⛔ **Il produttore contraddiceva il contratto appena stretto.**
   `types.py` diceva `riferimento: str`, ma il mapping di
   `list_dash_competenza_gruppi` faceva ancora
   `None if row[3] is None else str(row[3])`: un campo dichiarato non-nullable
   che il repository poteva emettere `None`.
   ⭐ **Stringere un tipo senza guardare chi lo produce non è stringere niente**:
   è aggiungere una seconda affermazione sul contratto, e lasciarle discordi.
   Corretto in `str(row[3])`, che è anche **la convenzione del file** —
   `gruppo_key` e `tipo_gruppo`, ugualmente NOT NULL, sono mappati così due
   righe sopra. Non è stata inventata una policy: è stato tolto un caso
   speciale.
2. ⛔ **Un commento che insegnava un meccanismo inesistente.** La whitelist
   `DASH_COMPETENZA_GRUPPI_SEARCH_COLUMNS` era annotata *«`riferimento` è
   `COALESCE(doc.codice, …)` su una LEFT JOIN LATERAL che unisce sei rami»*.
   È il **gemello lato BE** delle due frasi che il `-05` ha corretto a DB
   (§5.3), e vale la stessa ragione: *un commento che sbaglia il meccanismo è
   peggio di un commento assente, perché viene creduto* — chi ottimizzasse «le
   sei scansioni» lavorerebbe su una cosa che non esiste più.
   ⚠️ Riscritto tenendo ciò che **non** cambia: la ricerca resta non
   indicizzata, il DL-2 resta aperto.
3. ⛔ **Una difesa contro l'impossibile, nello stesso file che ora dice il
   contrario.** `buildApriDocumentoAction` riceveva `row.riferimento ?? ''`:
   doppiamente irraggiungibile — il campo è NOT NULL, e quella voce si rende
   solo quando `documento_id` c'è. Lasciarla significava che lo stesso file
   affermava due cose opposte sullo stesso contratto.

⭐ **E il contratto stretto non aveva un presidio.** Il mapping legge **per
indice**: un riordino del `SELECT` farebbe scorrere i valori sulle chiavi
sbagliate senza rompere niente, e il test di larghezza (`24-septies`) resterebbe
verde perché la larghezza non cambia. Aggiunto `24-octies`
(`test_mapping_espone_riferimento_non_nullo`), gemello del test 24: quello
presidia il NULL che deve **sopravvivere**, questo il valore che non deve **mai**
esserlo.

⚠️ Trovato di rimbalzo, e corretto perché il file era già aperto:
`test_larghezza_riga_finta_uguale_al_select` esisteva nel codice come
`24-septies` e **non compariva nell'indice** in testa al file, che
[AGENTS.md](../../../../.codex/AGENTS.md) richiede. Un indice che non elenca un
test è il primo passo perché quel test smetta di essere manutenuto.

### 9.5 · Doc API dell'endpoint

`docs/it/backend/vendite/manual/api_dashboard_competenza.md`:

- `documento_id` era **assente** dall'elenco dei campi di riga, pur essendo ciò
  con cui il client apre il drawer. Aggiunto;
- nuova sezione sul contratto delle due colonne: `riferimento` NOT NULL col
  perché **strutturale**, il divieto esplicito di rimettere la catena lato
  client, il cambio di sorgente `20260901-04/-05` con **contratto HTTP
  invariato**, l'effetto visibile sulle righe prima etichettate col codice
  commessa, la scelta della revisione **spinta**, e il costo di ricerca che
  resta non indicizzato.

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
