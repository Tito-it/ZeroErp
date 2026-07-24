# Brief DB — Flag `fatturata` nella lista attività di commessa

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-24 · **Owner**: Tid · **Stato**: ⬜ **DA SVILUPPARE** · **Priorità**: 🟢
> BASSA (nessun danno dati: è una congruenza UI mancante; il BE difende già).
>
> **Perimetro**: DB (una funzione, additiva) **+ una riga di BE** (§5.1) **+ FE**
> (§5.2, gate già predisposto). Micro-prerequisito, nessuna nuova entità.
>
> **Origine**: coda di **E-FE-2** del
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
> (§FASE E). La parte FE indipendente è già fatta (gate `canEditRighe` +
> `variazione` nascosta su bloccato); resta il gate «riga già fatturata», che
> richiede al DB di **esporre il dato** oggi assente nella lista.
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]).

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

---

## 1. Decisione

| # | Decisione | Motivo |
| --- | --- | --- |
| **D1** | Esporre in `fn_list_commessa_attivita` una colonna booleana **`fatturata`** = `EXISTS` di un'`attivita_fatturabili` della riga con `fattura_riga_id IS NOT NULL` | È lo specchio esatto del guard BE `_assert_non_fatturata`: la UI non può divergere da ciò che il BE rifiuta |
| **D2** | **Booleano, non `fattura_riga_id` grezzo** | Al FE serve solo «si può toccare il prezzo?». Una CA può avere >1 AF: l'`EXISTS` è privo dell'ambiguità del «quale id». Se in futuro servisse un deep-link alla fattura dalla riga, si aggiunge `fattura_riga_id` con lo stesso pattern — additivo, nessuna rottura di contratto |
| **D3** | Colonna **in coda** alla `RETURNS TABLE` | Posizione più sicura per eventuali consumatori posizionali; il BE usa comunque colonne **nominate** (§5.1) |

### Cosa NON si fa

- Non si cambia il guard BE né `get_attivita_pricing`: restano la fonte di verità
  del rifiuto. Questo brief aggiunge solo l'**anticipo UI** dello stesso verdetto.
- Non si tocca `attivita_fatturabili` né la pipeline di fatturazione.
- Non si espone `fattura_riga_id` grezzo (YAGNI oggi; aggiungibile poi).

---

## 2. Piano DB — `20260724-06` (o prossima numerazione libera)

Numerazione: sequenza **globale per data**
([[feedback_liquibase_numerazione_globale_per_data]]).

`20_code/vendite/` — `vendite.fn_list_commessa_attivita`. La firma ha
`RETURNS TABLE`: **non si modifica con `CREATE OR REPLACE`** → `DROP FUNCTION IF
EXISTS` + ricreazione ([[feedback_pg_returns_table_drop_required]]). Verificare
**nessun oggetto DB dipendente** (il BE la chiama via cursor, non è un dipendente
di catalogo).

**Corpo dalla doc auto-gen** ([[feedback_db_doc_first]]:
[fn_list_commessa_attivita.md](../../dbzero/vendite/funzioni/fn_list_commessa_attivita.md)),
applicando sopra la modifica. Una sola colonna nuova in coda alla `RETURNS TABLE`:

| Colonna | Origine |
| --- | --- |
| `fatturata boolean` | `EXISTS (SELECT 1 FROM vendite.attivita_fatturabili af WHERE af.commessa_attivita_id = ca.id AND af.fattura_riga_id IS NOT NULL)` |

Note di stesura:

- La `RETURNS TABLE` va copiata dall'**ultimo YAML** che definisce la funzione,
  non dalla doc auto-gen (che scioglie i `%TYPE` in tipi concreti) — vedi le
  convenzioni SQL del brief guard-uscita §3.
- L'`EXISTS` come espressione nella `SELECT` list ritorna già `boolean`: nessun
  `COALESCE` necessario (EXISTS non è mai NULL).
- Attenzione a non alterare `WHERE`/`ORDER BY`/`LIMIT`/`OFFSET` esistenti: la
  modifica è **puramente additiva** in `SELECT` e `RETURNS`.

---

## 3. Test — `db/pgtap/vendite/test-lista-commessa-attivita-fatturata-v1.sql`

Indice in testa al file (regola AGENTS.md). Copertura minima:

| # | Test |
| --- | --- |
| 1 | `fn_list_commessa_attivita` presente e ritorna la colonna `fatturata` |
| 2 | `fatturata = false` su riga senza `attivita_fatturabili` |
| 3 | `fatturata = false` su riga con AF ma `fattura_riga_id IS NULL` (caso reset-lotto: EMESSA ma prezzo ancora modificabile) |
| 4 | `fatturata = true` su riga con AF e `fattura_riga_id` valorizzato |

Fixture: riusare il pattern esistente dei test commessa
(`fn_get_or_create_commessa` + righe sourceless, [[feedback_pgtap_patterns]]);
per il caso 4 collegare un'AF con `fattura_riga_id` a una fattura di prova.

---

## 4. Contratto per BE/FE

`fn_list_commessa_attivita` ritorna, in coda, `fatturata boolean`:
- `true` ⇔ esiste ≥1 `attivita_fatturabili` della riga con `fattura_riga_id`
  valorizzato ⇔ il BE **rifiuterà** ogni azione prezzo (`_assert_non_fatturata`).
- `false` ⇔ nessuna AF fatturata ⇔ prezzo ancora modificabile (compatibilmente
  con gli altri guard: `commessa_modificabile`, `prezzo_bloccato`).

---

## 5. Impatti fuori DB

### 5.1 BE — una riga

`backend/apps/vendite/db/commesse_repository.py`: aggiungere `"fatturata"` alla
costante **`_ATTIVITA_COLS`** (la lista di colonne nominate che
`list_commessa_attivita` seleziona da `fn_list_commessa_attivita`). Additivo: il
mapping è per nome/indice sulla stessa tupla, nessun altro punto da toccare. Il
valore è `bool` nativo → nessuna serializzazione speciale.

### 5.2 FE — completa E-FE-2

`CommessaGestioneDrawer.vue::buildRowActions`: aggiungere `visible: !row.fatturata`
(o disabilitare con tooltip) alle tre azioni prezzo, accanto ai gate già presenti
(`canPrezzo`, `canEditRighe`, e `!prezzo_bloccato` sulla variazione). Con questo
il kebab prezzi non propone più azioni che il BE rifiuterebbe su riga fatturata.

---

## 6. Rischi

| Rischio | Valutazione |
| --- | --- |
| `DROP FUNCTION` su `fn_list_commessa_attivita` | Verificare nessun dipendente DB; il BE la chiama via cursor (colonne nominate), l'aggiunta in coda è additiva |
| CA con più AF (alcune fatturate, altre no) | L'`EXISTS` risolve senza ambiguità: `true` se **almeno una** è fatturata (semantica «la riga ha prodotto fattura viva») — coerente con l'intento del guard |
| Divergenza col guard BE se un domani il criterio cambia | Documentato che `fatturata` **è** il criterio del guard: se cambia il guard, si allinea qui (una sola `EXISTS`) |

---

## 7. Riferimenti

- Guard BE: `apps/vendite/services/commesse_service.py::_assert_non_fatturata` ·
  fonte dato: `get_attivita_pricing` (LEFT JOIN `attivita_fatturabili`)
- Funzione: [fn_list_commessa_attivita](../../dbzero/vendite/funzioni/fn_list_commessa_attivita.md)
- Reset che azzera `fattura_riga_id`: [fn_cleanup_fatture_by_ids](../../dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids.md)
- Brief committente: [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md) §FASE E, E-FE-2
- Analogo recente (RETURNS TABLE + colonna additiva): [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md) §3.6 (D6)
