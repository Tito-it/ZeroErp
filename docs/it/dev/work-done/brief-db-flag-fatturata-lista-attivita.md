# Brief DB — Flag `fatturata` nella lista attività di commessa

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-24 · **Owner**: Tid · **Stato**: 🟢 **DB FATTO — da applicare**
> (2026-07-24) · **Priorità**: 🟢 BASSA (nessun danno dati: è una congruenza UI
> mancante; il BE difende già).
>
> **Esito DB (2026-07-24)**: ✅ changeset §2 scritto · ✅ pgTAP §3 **4/4 verde**
> (validato end-to-end in transazione `ROLLBACK`, nulla persistito) · ☐ migrate
> da lanciare. **Handoff BE/FE aperto** (§5, fuori perimetro di questa slice).
>
> **Perimetro**: **solo DB** in questa slice (una funzione, additiva). Le modifiche
> BE (§5.1) e FE (§5.2) sono **handoff** su `dev/backend-tid`, non incluse qui.
>
> **Origine**: coda di **E-FE-2** del
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
> (§FASE E). La parte FE indipendente è già fatta (gate `canEditRighe` +
> `variazione` nascosta su bloccato); resta il gate «riga già fatturata», che
> richiede al DB di **esporre il dato** oggi assente nella lista.
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]).
>
> **Revisione critica 2026-07-24** (verificata sul codice vivo): le premesse
> reggono tutte, ma la relazione CA↔AF è **1:1** (non 1:N come assumevano D2/§6)
> e AF ha già un flag `fatturato` che il brief originale ignorava. Le due cose
> sono state corrette qui sotto — la prima *rafforza* la tesi dello «specchio
> esatto», la seconda va motivata invece che taciuta. Dettaglio nei riquadri
> ⚠️ **[rev]**.

---

## 0. Il fatto che governa il brief

Il drawer di gestione commessa (`CommessaGestioneDrawer.vue`) elenca le righe via
`vendite.fn_list_commessa_attivita` e offre per riga le azioni prezzo N5/N7/sblocco.
Il BE le **difende già**: `commesse_service._assert_non_fatturata` rifiuta il
cambio prezzo quando la riga è fatturata, leggendo `af.fattura_riga_id`
(`get_attivita_pricing`, LEFT JOIN `attivita_fatturabili`). Ma il **FE non può
nascondere** quelle azioni prima del click, perché la **lista non espone** il
dato: l'operatore le vede, le usa, e prende un errore parlante. Congruenza UI
mancante, non un buco di sicurezza.

> ✅ **[rev]** Verificato: `_assert_non_fatturata`
> ([commesse_service.py:896-906](../../../../backend/apps/vendite/services/commesse_service.py#L896))
> legge `att.get("fattura_riga_id")` ed è invocato dai **tre** endpoint prezzo
> (righe 988, 1070, 1119). Il FE `buildRowActions`
> ([CommessaGestioneDrawer.vue:285](../../../../frontend/src/vendite/components/CommessaGestioneDrawer.vue#L285))
> ha già i gate `canPrezzo` e `!prezzo_bloccato`: manca solo `!fatturata`.

**Perché non basta `stato_emissione`** (che la lista già espone): `stato_emissione
= 'EMESSA'` significa «uscita verso una fattura», **non** «fatturata in via
irreversibile». Il reset lotto DRAFT (`fn_cleanup_fatture_by_ids`) azzera
`attivita_fatturabili.fattura_riga_id` **senza** riportare indietro
`commesse_attivita.stato_emissione` (stesso fatto notato in
[brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md)
§2.1-bis, D7). Esiste quindi la riga EMESSA il cui prezzo è **legittimamente
modificabile** (lotto resettato, `fattura_riga_id IS NULL`): usare
`stato_emissione` come proxy nasconderebbe azioni lecite. Il criterio corretto è
esattamente quello del guard BE: **esiste un'AF con `fattura_riga_id` valorizzato**.

> ✅ **[rev]** Confermato: `fn_cleanup_fatture_by_ids`
> ([doc:77-78](../../dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids.md#L77))
> fa `SET fatturato = false, fattura_riga_id = NULL` ma non tocca
> `stato_emissione`. La riga «EMESSA con prezzo modificabile» è reale.

---

## 1. Decisione

| # | Decisione | Motivo |
| --- | --- | --- |
| **D1** | Esporre in `fn_list_commessa_attivita` una colonna booleana **`fatturata`** = `EXISTS` di un'`attivita_fatturabili` della riga con `fattura_riga_id IS NOT NULL` | È lo specchio esatto del guard BE `_assert_non_fatturata`: la UI non può divergere da ciò che il BE rifiuta |
| **D2** | **Booleano, non `fattura_riga_id` grezzo** | Al FE serve solo «si può toccare il prezzo?». `fattura_riga_id` grezzo esporrebbe un id di cui il FE non fa nulla. Se in futuro servisse un deep-link alla fattura dalla riga, si aggiunge `fattura_riga_id` con lo stesso pattern — additivo, nessuna rottura di contratto |
| **D3** | Colonna **in coda** alla `RETURNS TABLE` | Posizione più sicura per eventuali consumatori posizionali; il BE usa comunque colonne **nominate** (§5.1) |
| **D4** | Criterio **`fattura_riga_id IS NOT NULL`**, NON la colonna `fatturato` di AF | La lista deve specchiare **il guard BE**, che legge `fattura_riga_id`. `fatturato` è un flag denormalizzato parallelo: oggi coincide, ma è un secondo asse che potrebbe sfasarsi. Si specchia la FK reale, non il flag. Vedi ⚠️ **[rev]** in §1-bis |

### Cosa NON si fa

- Non si cambia il guard BE né `get_attivita_pricing`: restano la fonte di verità
  del rifiuto. Questo brief aggiunge solo l'**anticipo UI** dello stesso verdetto.
- Non si tocca `attivita_fatturabili` né la pipeline di fatturazione.
- Non si espone `fattura_riga_id` grezzo (YAGNI oggi; aggiungibile poi).

### 1-bis. Correzioni della revisione critica (2026-07-24)

> ⚠️ **[rev] Relazione CA↔AF: è 1:1, non 1:N.** Il brief originale motivava D2
> e il rischio §6 con «una CA può avere >1 AF». **Falso**: esiste
> `uq_attivita_fatturabili_commessa_attivita`
> ([tabella:104](../../dbzero/vendite/tabelle/attivita_fatturabili.md#L104)),
> **UNIQUE su `commessa_attivita_id`** → al massimo **una** AF per riga.
>
> Conseguenze, entrambe a favore del brief:
>
> - la motivazione «ambiguità del quale id» in D2 **non esiste** ed è stata
>   rimossa (D2 resta valida per l'altro motivo: YAGNI);
> - essendo 1:1, il `LEFT JOIN attivita_fatturabili` di `get_attivita_pricing`
>   ritorna **esattamente 0 o 1 riga** in modo deterministico. Quindi l'`EXISTS`
>   e il guard BE sono davvero **specchio esatto**, senza il rischio di
>   divergenza che il multi-AF avrebbe introdotto. Il rischio §6 «CA con più AF»
>   è un **non-problema** e va riscritto (vedi §6).

<!-- separatore riquadri rev -->

> ⚠️ **[rev] Esiste già `attivita_fatturabili.fatturato boolean`**
> ([tabella:15](../../dbzero/vendite/tabelle/attivita_fatturabili.md#L15)),
> `DEFAULT false`. Un revisore lo nota e chiede: «perché non usi il flag pronto?».
> Verificato che `fatturato` e `fattura_riga_id` si muovono **sempre in coppia**:
> `fn_generate_fatture_righe` fa `SET fattura_riga_id = ..., fatturato = true`
> insieme ([doc:85](../../dbzero/vendite/funzioni/fn_generate_fatture_righe.md#L85)),
> `fn_cleanup_fatture_by_ids` li azzera insieme. Oggi equivalenti. **La scelta di
> `fattura_riga_id` resta la giusta** (D4): specchia il guard BE, non un flag
> parallelo. Ma la scelta va *motivata* contro `fatturato`, non ignorata.

---

## 2. ✅ Piano DB — `20260724-07` (FATTO, da applicare)

Numerazione: sequenza **globale per data**
([[feedback_liquibase_numerazione_globale_per_data]]).

> ⚠️ **[rev] `20260724-06` è occupato** (dal fix `trgfn_tx_id_managed` early-exit,
> [brief-db-tx-id-uscita-anticipata.md](../work-done/brief-db-tx-id-uscita-anticipata.md)).
> Si parte da **`-07`**.

`20_code/vendite/` — `vendite.fn_list_commessa_attivita`. La firma ha
`RETURNS TABLE`: **non si modifica con `CREATE OR REPLACE`** → `DROP FUNCTION IF
EXISTS` + ricreazione ([[feedback_pg_returns_table_drop_required]]).

> ✅ **[rev] Nessun oggetto DB dipende** dalla funzione (nessuna vista/funzione la
> referenzia). Il BE la chiama via cursor con colonne **nominate**
> ([`_ATTIVITA_COLS`](../../../../backend/apps/vendite/db/commesse_repository.py#L1055)):
> l'aggiunta in coda è additiva, il `DROP+CREATE` è sicuro.

**Corpo dalla doc auto-gen** ([[feedback_db_doc_first]]:
[fn_list_commessa_attivita.md](../../dbzero/vendite/funzioni/fn_list_commessa_attivita.md)),
applicando sopra la modifica. Una sola colonna nuova in coda alla `RETURNS TABLE`:

| Colonna | Origine |
| --- | --- |
| `fatturata boolean` | `EXISTS (SELECT 1 FROM vendite.attivita_fatturabili af WHERE af.commessa_attivita_id = ca.id AND af.fattura_riga_id IS NOT NULL)` |

Note di stesura:

- La `RETURNS TABLE` va copiata dall'**ultimo YAML** che definisce la funzione
  (`20260331-16-fix-vendite-fn-e-generico-batch7`), non dalla doc auto-gen (che
  scioglie i `%TYPE` in tipi concreti) — vedi le convenzioni SQL del brief
  guard-uscita §3 ([[feedback_autogen_firma_perde_type]]).
- La colonna nuova `fatturata boolean` è un tipo **derivato** (esito di `EXISTS`),
  non specchia alcuna colonna reale → tipo **esplicito** `boolean`, non `%TYPE`.
- L'`EXISTS` come espressione nella `SELECT` list ritorna già `boolean`: nessun
  `COALESCE` necessario (EXISTS non è mai NULL).
- La subquery correlata è coperta da `ix_attivita_fatturabili_commessa_attivita_id`
  ([tabella:95](../../dbzero/vendite/tabelle/attivita_fatturabili.md#L95)): costo
  per-riga trascurabile, nessun problema con `p_limit` fino a 10000.
- La funzione è **`STABLE`**: l'`EXISTS` è read-only → resta `STABLE`, non
  cambiare il volatility marker.
- Attenzione a non alterare `WHERE`/`ORDER BY`/`LIMIT`/`OFFSET` esistenti: la
  modifica è **puramente additiva** in `SELECT` e `RETURNS`. Il `LEFT JOIN
  config.sorgenti` esistente resta invariato (la subquery non tocca la cardinalità).

---

## 3. ✅ Test — `test-lista-commessa-attivita-fatturata-v1.sql` (FATTO, 4/4 verde)

Indice in testa al file (regola AGENTS.md). Copertura minima:

| # | Test | Esito |
| --- | --- | --- |
| 1 | `fn_list_commessa_attivita` presente e ritorna la colonna `fatturata` | ✅ |
| 2 | `fatturata = false` su riga senza `attivita_fatturabili` | ✅ |
| 3 | `fatturata = false` su riga con AF ma `fattura_riga_id IS NULL` (caso reset-lotto: EMESSA ma prezzo ancora modificabile) | ✅ |
| 4 | `fatturata = true` su riga con AF e `fattura_riga_id` valorizzato | ✅ |

Fixture: riusare il pattern esistente dei test commessa
(`fn_get_or_create_commessa` + righe sourceless, [[feedback_pgtap_patterns]]);
per il caso 4 collegare un'AF con `fattura_riga_id` a una fattura di prova.

> ⚠️ **[rev]** Il caso 3 è il **discriminante** che giustifica tutto il brief:
> è la riga EMESSA-ma-modificabile su cui `stato_emissione` sbaglierebbe e
> `fattura_riga_id` no. Non ometterlo. Attenzione al guard `tipo_doc_emittibile`
> nel fixture (righe APPROVATA+NON_EMESSA esigono `tipo_doc_fiscale_id`): stessa
> trappola incontrata nei test di oggi — passare `tipo_doc` all'upsert.

---

## 4. Contratto per BE/FE

`fn_list_commessa_attivita` ritorna, in coda, `fatturata boolean`:

- `true` ⇔ esiste ≥1 `attivita_fatturabili` della riga con `fattura_riga_id`
  valorizzato ⇔ il BE **rifiuterà** ogni azione prezzo (`_assert_non_fatturata`).
- `false` ⇔ nessuna AF fatturata ⇔ prezzo ancora modificabile (compatibilmente
  con gli altri guard: `commessa_modificabile`, `prezzo_bloccato`).

> ✅ **[rev]** Con la 1:1 garantita, il «≥1» del contratto è di fatto «0 o 1»:
> l'equivalenza col guard BE è esatta, non probabilistica.

---

## 5. Impatti fuori DB — HANDOFF (fuori perimetro di questa slice DB)

> ⚠️ **[rev]** Questa slice consegna **solo il DB** (funzione + pgTAP). Le due
> modifiche qui sotto sono l'**handoff** al team BE/FE su `dev/backend-tid`: senza
> di esse la colonna `fatturata` esiste ma nessuno la consuma, e il FE continua
> a mostrare le azioni prezzo su riga fatturata (l'errore resta parlante lato BE,
> come oggi). Verificate durante la revisione ma **non applicate qui**.

### 5.1 ☐ BE — una riga (DA FARE, `dev/backend-tid`)

`backend/apps/vendite/db/commesse_repository.py`: aggiungere `"fatturata"` alla
costante **`_ATTIVITA_COLS`** (la lista di colonne nominate che
`list_commessa_attivita` seleziona da `fn_list_commessa_attivita`). Additivo: il
mapping è per nome/indice sulla stessa tupla, nessun altro punto da toccare. Il
valore è `bool` nativo → nessuna serializzazione speciale.

> ✅ **[rev]** Verificato: `_ATTIVITA_COLS`
> ([commesse_repository.py:1055](../../../../backend/apps/vendite/db/commesse_repository.py#L1055))
> è una tupla di 20 nomi; il mapping (righe 1132+) itera per indice sulla stessa
> tupla, e i type-set (`_ATTIVITA_DATE_COLS`, `_JSONB`, `_UUID`) non includono
> `fatturata` → un `bool` passa dritto. Aggiungere `"fatturata"` in coda alla
> tupla è l'unica modifica. **Ordine vincolante**: la posizione nella tupla deve
> combaciare con la coda della `RETURNS TABLE` (entrambe in fondo).

<!-- separatore riquadri rev -->

> ⚠️ **[rev] Rompe un test BE esistente.**
> `test_commesse_repository.py::test_list_commessa_attivita_maps_rows` costruisce
> una tupla di **20 valori** posizionali e il mapping fa `raw[idx]`
> ([commesse_repository.py:1137](../../../../backend/apps/vendite/db/commesse_repository.py#L1137)):
> con `_ATTIVITA_COLS` a 21 nomi, `raw[20]` va in `IndexError`. Nell'handoff BE
> va aggiunto il 21° valore (`fatturata`) alla tupla del test + un'asserzione sul
> nuovo campo. Non è una regressione: è il test che segue la colonna nuova.

### 5.2 ☐ FE — completa E-FE-2 (DA FARE, `dev/backend-tid`)

`CommessaGestioneDrawer.vue::buildRowActions`: aggiungere `visible: !row.fatturata`
(o disabilitare con tooltip) alle tre azioni prezzo, accanto ai gate già presenti
(`canPrezzo`, `canEditRighe`, e `!prezzo_bloccato` sulla variazione). Con questo
il kebab prezzi non propone più azioni che il BE rifiuterebbe su riga fatturata.

---

## 6. Rischi

| Rischio | Valutazione |
| --- | --- |
| `DROP FUNCTION` su `fn_list_commessa_attivita` | ✅ **[rev]** Verificato nessun dipendente DB; il BE la chiama via cursor (colonne nominate), l'aggiunta in coda è additiva |
| ~~CA con più AF (alcune fatturate, altre no)~~ | ⚠️ **[rev] Non-problema.** `uq_attivita_fatturabili_commessa_attivita` impone **1:1**: al massimo una AF per riga. L'`EXISTS` e il guard BE (LEFT JOIN 0/1 riga) coincidono per costruzione, nessuna ambiguità da risolvere |
| Divergenza col guard BE se un domani il criterio cambia | Documentato che `fatturata` **è** il criterio del guard (`fattura_riga_id IS NOT NULL`, non `fatturato`): se cambia il guard, si allinea qui (una sola `EXISTS`) |
| Sfasamento `fatturato` vs `fattura_riga_id` | ⚠️ **[rev]** Oggi si muovono in coppia. Usando `fattura_riga_id` (D4) il brief è immune a un eventuale sfasamento futuro del flag denormalizzato |

---

## 7. Riferimenti

- Guard BE: `apps/vendite/services/commesse_service.py::_assert_non_fatturata` ·
  fonte dato: `get_attivita_pricing` (LEFT JOIN `attivita_fatturabili`)
- Funzione: [fn_list_commessa_attivita](../../dbzero/vendite/funzioni/fn_list_commessa_attivita.md)
  · ultimo YAML che la definisce: `20260331-16-fix-vendite-fn-e-generico-batch7`
- Vincolo 1:1: `uq_attivita_fatturabili_commessa_attivita`
  ([attivita_fatturabili](../../dbzero/vendite/tabelle/attivita_fatturabili.md))
- Reset che azzera `fattura_riga_id`: [fn_cleanup_fatture_by_ids](../../dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids.md)
- Brief committente: [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md) §FASE E, E-FE-2
- Analogo recente (RETURNS TABLE + colonna additiva): [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md) §3.6 (D6)
