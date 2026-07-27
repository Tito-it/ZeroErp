# Brief DB — Race sul progressivo `segment_key` degli oneri manuali

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-23 · **Owner**: Tid · **Stato**: ✅ **CHIUSO lato DB — applicato e
> testato** (2026-07-23) · **Priorità**: 🔴 ALTA (perdita silenziosa di dati con
> due operatori concorrenti — entrambe le chiamate rispondevano 200 OK).
>
> **Esito**: changeset `20260723-01` applicato, `test-porta-oneri-v1.sql`
> **verde (22/22)**, doc auto-gen rigenerata (il presidio è vivo sul DB). Vedi §7.
>
> **Perimetro**: SOLO DB — `vendite.fn_aggiungi_onere_commessa`. Il service
> `aggiungi_onere_commessa` e il repository sono wrapper 1:1 della madre e **non
> cambiano** (firma invariata). ✅ **Appendice BE CHIUSA (2026-07-23)**: policy
> 409 + marker di traduzione + test — il codice 557 risponde 409 end-to-end
> (vedi §5; l'handoff originale era incompleto, mancava il marker nel service).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → fix restrittivo da subito, nessuna compatibilità.
> **Origine**: review critica 2026-07-23 della porta oneri
> ([brief-be-fe-immutabilita-quantita-e-porta-oneri.md](brief-be-fe-immutabilita-quantita-e-porta-oneri.md), step A1).

---

## 1. Problema

`vendite.fn_aggiungi_onere_commessa` calcola il progressivo della chiave con
un conteggio **senza lock** (righe 87–96 della doc auto-gen):

```sql
SELECT count(*) + 1 INTO v_progressivo
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id = p_commessa_id
   AND ca.segment_key LIKE 'MAN:%';

v_segment_key := format('MAN:%s:%s', p_commessa_id, v_progressivo);
```

Due chiamate concorrenti sulla stessa commessa (due operatori, oppure un retry
di rete con Idempotency-Key **diverse**) leggono lo stesso `count` e producono
entrambe `MAN:<commessa>:<n>`. La riga passa poi da
`fn_upsert_commessa_attivita`, che fa **upsert sulla chiave naturale**
`(commessa_id, segment_key)`: la seconda chiamata **aggiorna la riga della
prima invece di crearne una nuova**.

**Effetto**: un onere sparisce in silenzio — entrambe le chiamate tornano
200 con lo **stesso** `attivita_id`, e `commesse_attivita_log` registra due
`ONERE_AGGIUNTO` sulla stessa riga. Nessun errore da nessuna parte.

> **Severità — precisazione dalla review di realizzazione (2026-07-23).** Non è
> "un onere in meno". Il `DO UPDATE` sovrascrive con `EXCLUDED` **tutti** i
> campi portanti (`prezzo_snapshot`, `articolo_id`, `causale_onere_id`,
> `data_attivita`, `competenza_*`), mentre `meta` fa **merge** (`old || new`).
> Quindi: (a) l'importo del primo onere **non viene sommato, viene perso** →
> **sotto-fatturazione**; (b) se il secondo onere arriva **senza motivo**,
> `jsonb_strip_nulls` produce `{}` e il merge **conserva il `motivo_onere` del
> primo** → la riga sopravvissuta è una **chimera** (importo/articolo/causale
> del secondo, motivo del primo): audit trail corrotto, non solo incompleto.

La porta manuale è il **primo scrittore concorrente reale** di questa fn: i
push sorgente serializzano per costruzione (worker singolo), gli operatori no.

## 2. Richiesta

Rendere il progressivo sicuro sotto concorrenza. Due opzioni, in ordine di
preferenza:

1. **Advisory lock transazionale per commessa** prima del conteggio:

   ```sql
   PERFORM pg_advisory_xact_lock(hashtextextended('onere:' || p_commessa_id, 0));
   ```

   Serializza solo gli oneri della **stessa** commessa (commesse diverse non
   si bloccano tra loro), si rilascia da solo a fine transazione, zero oggetti
   nuovi. Il `count(*)+1` sotto lock diventa corretto.

2. In alternativa, progressivo da **sequence** dedicata (o `max(...)+1` con
   lock) — più invasivo (oggetto nuovo, buchi nei progressivi ammessi da
   dichiarare) e non necessario se l'opzione 1 basta.

Da valutare del team: se la collisione debba anche essere **impedita a valle**
(la fn upsert accetta l'update di una riga `MAN:%` esistente — per la porta
manuale un "update" non è mai legittimo: ogni chiamata è un onere NUOVO).
Un guard `E_ONERE_SEGMENT_DUPLICATO` sull'esito `updated` della upsert
trasformerebbe qualunque futura regressione da perdita silenziosa a errore
parlante (difesa in profondità, coerente con [[feedback_concentrico_no_yagni]]).

### 2bis. Decisioni di realizzazione (2026-07-23)

**Opzione 1 confermata**, con una ragione più forte di quella scritta sopra: la
numerazione progressiva per commessa **è già un contratto de facto**, fissato da
`db/pgtap/vendite/test-porta-oneri-v1.sql` test 14, che asserisce l'uguaglianza
esatta con `MAN:<commessa>:2`. Una sequence globale renderebbe il progressivo
non deterministico e romperebbe quel test. L'opzione 2 non è "più invasiva": è
**incompatibile** con la copertura esistente.

Tre scostamenti dal testo del brief, decisi in fase di realizzazione:

- **Forma della chiave di lock**: non `hashtextextended(...)` (forma a 1
  argomento) ma la forma a **2 argomenti** `(hashtext('<namespace>'),
  hashtext('<chiave>'))`, convenzione di casa (`fn_get_or_create_commessa`,
  `fn_get_next_progressivo`, `fn_push_offerta_a_contratto`). Lo spazio dei lock
  a 1 argomento è condiviso con altre feature (es.
  `catalogo.fn_duplica_componente_versione`): con il namespace la collisione è
  **strutturalmente impossibile**, non solo improbabile.
- **`MAX(...)+1` invece di `count(*)+1`** (adottato, era l'inciso dell'opzione 2).
  Il conteggio assume l'invariante *"count = max"*, che nulla garantisce: una
  sola `DELETE` di una riga `MAN:` farebbe puntare `count+1` su una chiave già
  esistente → stessa collisione, **senza nemmeno la concorrenza**. Buchi nella
  numerazione ammessi e dichiarati. Il match è sulla forma **piena** della
  chiave (`^MAN:<commessa>:[0-9]+$`): una chiave `MAN:` non auto-coerente non
  entra nel calcolo.
- **Il guard passa da "da valutare" ad adottato**, per due ragioni indipendenti
  dalla difesa in profondità: (a) **semantica** — la porta è una `CREATE`, non
  una upsert; riusa `fn_upsert_commessa_attivita` solo per non duplicarne il
  mapping a 38 parametri, e come effetto collaterale ne eredita una semantica
  che non vuole: `IF NOT v_is_new THEN raise` è l'unica riga che restituisce
  semantica *insert-only* senza duplicare nulla; (b) **indipendenza dal livello
  di isolamento** — vedi sotto. Il guard sta nel **chiamante**, mai dentro
  `fn_upsert_commessa_attivita`: là l'update è la semantica corretta (re-push
  idempotente) e spostarlo romperebbe i push.

**Assunzione da dichiarare (mancava nel brief): il lock è sufficiente solo sotto
READ COMMITTED.** Sotto `REPEATABLE READ`/`SERIALIZABLE` lo snapshot è fissato
all'inizio transazione: dopo aver preso il lock, il conteggio continuerebbe a
**non vedere** la riga dell'altra transazione → collisione di nuovo. Django gira
in READ COMMITTED (default PG) quindi il fix funziona, ma l'assunzione è ora
scritta nel corpo della funzione ed è **neutralizzata dal guard**, che sotto RR
trasforma la perdita silenziosa in errore parlante.

## 3. Accettazione

> ⚠️ **Correzione al criterio 1 (review di realizzazione, 2026-07-23).** Due
> insert **nella stessa transazione** producono già oggi progressivi distinti, e
> il test 14 lo asserisce da sempre in verde: nella stessa transazione il
> calcolo del progressivo vede la riga non ancora committata, quindi **la race
> non può manifestarsi**. Quel criterio è un ottimo test di **non-regressione**
> della numerazione, ma **non testa il fix**. La race vive solo **fra
> transazioni concorrenti**, che pgTAP (mono-sessione, `BEGIN`/`ROLLBACK`) non
> sa riprodurre.
>
> **Nota sul guard**: con `MAX(...)+1` il progressivo è per definizione il primo
> libero, quindi da una singola sessione la collisione è **irraggiungibile** e
> il guard non è esercitabile a runtime in pgTAP. Resta difesa in profondità
> pura, verificata **strutturalmente**.
>
> **Via dblink scartata**: un test a due sessioni via `dblink` sarebbe possibile
> in teoria, ma il canale è provisioning `context: disabled`
> (`20260205-42-provision-dblink-log-channel`) e condizionato a una password non
> valorizzata in sviluppo → **non eseguibile in CI**.

Criteri effettivi:

- pgTAP **non-regressione** (già presente, test 14): due insert nella stessa
  transazione/commessa producono **due** righe con progressivi distinti
  (`MAN:x:1`, `MAN:x:2`).
- pgTAP **strutturale** (test 20-21, pattern `pg_get_functiondef` di
  `test-ordini-lock-cliente.sql`): il corpo della funzione viva contiene
  `pg_advisory_xact_lock` e il guard `E_ONERE_SEGMENT_DUPLICATO`.
- pgTAP **catalogo** (test 22): codice errore 557 presente in
  `config.messaggi_errore`.
- Test di concorrenza **manuale**, due sessioni psql (script pronto in §6): la
  seconda sessione attende il lock e produce il progressivo successivo, non lo
  stesso.
- Gli smoke/test BE esistenti della porta oneri restano verdi senza modifiche
  (il contratto della fn non cambia: stessi parametri, stesso risultato).

## 4. Riferimenti

- Doc fn viva: `docs/it/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa.md`
  — per il `CREATE OR REPLACE` si è partiti da QUESTA, non dagli YAML
  ([[feedback_db_doc_first]]). Rigenerata al migrate: nella **rev 2026-07-23**
  il lock è a riga ~109, il `MAX(...)+1` a ~130, il guard a ~199 (le righe
  87–96 citate al §1 sono quelle della rev 2026-07-21, ora superate).
- Changeset del fix:
  `db/changelog/migrations_v2/20_code/vendite/20260723-01-update-fn-aggiungi-onere-commessa-race-segment-key-mctit.yaml`.
- Codice errore 557: append a
  `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv` — nessun
  loader nuovo, i `loadUpdateData` `runOnChange` esistenti ripescano il CSV.
- Doc concettuale: `docs/it/dbzero/vendite/manual/fn_aggiungi_onere_commessa.md`
  (sezione «Concorrenza: perché il progressivo si calcola sotto lock»).
- Wrapper BE: `backend/apps/vendite/db/commesse_repository.py::aggiungi_onere`;
  service `backend/apps/vendite/services/commesse_service.py::aggiungi_onere_commessa`.
- Endpoint esposto: `POST /api/v1/vendite/commesse/<id>/oneri/` (azione
  `carica_voce_manuale`).

## 5. Handoff BE — codice 557 → ✅ CHIUSO (dev/backend-tid, 2026-07-23)

Il codice `E_ONERE_SEGMENT_DUPLICATO` risponde ora **409** end-to-end.
Verificato con la DatabaseError reale del RAISE: codice tradotto
`E_ONERE_SEGMENT_DUPLICATO`, policy `http_status=409 / show_error_banner`.

> ⚠️ **L'handoff era incompleto: la policy da sola NON bastava.** La catena di
> traduzione ha due anelli, non uno. Il service `aggiungi_onere_commessa`
> cattura la `DatabaseError` e la passa a `ErrorManager.raise_from_database_error`
> con `known_markers=_ONERE_DB_ERROR_MARKERS`: un codice **non presente nei
> marker** cade sul `fallback_code="E_COMMESSA_VALIDATION"` **prima** di
> arrivare al registry → avrebbe risolto 400 nonostante la policy 409. Serviva
> quindi anche il **marker nel service**, altrimenti la policy era codice
> morto. La coppia policy+marker va sempre tenuta insieme (nota lasciata in
> entrambi i punti del codice).

Consegnato (3 pezzi + regressione):

1. **Policy 409** in `apps/core/services/error_policies.py` (come da §5), accanto
   agli altri 409 della famiglia immutabilità.
2. **Marker** `E_ONERE_SEGMENT_DUPLICATO` in
   `apps/vendite/services/commesse_service.py::_ONERE_DB_ERROR_MARKERS` — il
   pezzo mancante sopra.
3. **Test**: `test_aggiungi_onere_traduce_errori_madre` esteso al nuovo codice
   (sopravvive alla traduzione col proprio codice) + `test_post_onere_segment_
   duplicato_409` a livello API (envelope 409 vero).

## 6. Test di concorrenza manuale (due sessioni psql)

L'unica prova reale della serializzazione. `<COMMESSA>` = una commessa
esistente; servono due terminali sullo stesso database.

**Sessione A** — apre la transazione, crea l'onere, **non committa**: tiene il
lock advisory fino a fine transazione.

```sql
BEGIN;
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => <COMMESSA>,
  p_istanza_utility_id  => <ISTANZA>,
  p_articolo_onere_id   => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE'),
  p_importo             => 10.00,
  p_tipo_doc_fiscale_id => <TIPO_DOC>);
-- NON committare ancora
```

**Sessione B** — stessa commessa: la chiamata deve **restare appesa** (attende
il lock), non tornare subito.

```sql
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => <COMMESSA>,   -- STESSA commessa
  p_istanza_utility_id  => <ISTANZA>,
  p_articolo_onere_id   => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE'),
  p_importo             => 20.00,
  p_tipo_doc_fiscale_id => <TIPO_DOC>);
```

**Verifica dell'attesa** (da una terza sessione, o prima di sbloccare):

```sql
SELECT pid, wait_event_type, wait_event, left(query, 60)
  FROM pg_stat_activity
 WHERE wait_event_type = 'Lock' AND wait_event = 'advisory';
```

**Sessione A**: `COMMIT;` → la sessione B si sblocca.

**Esito atteso**: due righe distinte, progressivi consecutivi, nessun errore.

```sql
SELECT id, segment_key, prezzo_snapshot
  FROM vendite.commesse_attivita
 WHERE commessa_id = <COMMESSA> AND segment_key LIKE 'MAN:%'
 ORDER BY segment_key;
-- atteso: MAN:<COMMESSA>:<n> = 10.00  e  MAN:<COMMESSA>:<n+1> = 20.00
```

**Esito che segnala il bug (prima del fix)**: la sessione B **non attende**, e
al termine esiste **una sola** riga con importo 20.00 — quella da 10.00 è stata
sovrascritta.

## 7. Esito (2026-07-23)

**DB chiuso.** Changeset `20260723-01` applicato, `test-porta-oneri-v1.sql`
**verde 22/22**, doc auto-gen rigenerata: il presidio è vivo sul DB.

| Consegna | Esito |
| --- | --- |
| `20260723-01-update-fn-aggiungi-onere-commessa-race-segment-key-mctit.yaml` | ✅ applicato |
| Codice **557** `E_ONERE_SEGMENT_DUPLICATO` (append a `messaggi_errore.csv`) | ✅ caricato dai loader `runOnChange` esistenti |
| pgTAP `plan(19)` → `plan(22)` (test 20-21 strutturali, 22 catalogo) | ✅ 22/22 |
| Doc concettuale `manual/fn_aggiungi_onere_commessa.md` (sezione «Concorrenza») | ✅ rev 2026-07-23 |
| Doc auto-gen `funzioni/fn_aggiungi_onere_commessa.md` | ✅ rigenerata al migrate |

### Cosa resta aperto

1. **BE — codice 557 → 409** in `error_policies.py` (§5). Tracciato come riga
   **C3 ☐ DA FARE** in §8 di
   [brief-be-fe-immutabilita-quantita-e-porta-oneri.md](brief-be-fe-immutabilita-quantita-e-porta-oneri.md).
   Fino ad allora l'API risponde **400** su un evento che comunque non deve mai
   accadere: degrado accettato e consapevole.
2. **Test di concorrenza manuale** (§6): **non ancora eseguito**. È l'**unica**
   prova reale della serializzazione — i test 20-21 sono strutturali e non
   possono verificarla (vedi il riquadro al §3). Da fare prima di considerare il
   fix validato sul campo, non solo sul codice.

### Nota per chi tocca questa funzione in futuro

Il guard `E_ONERE_SEGMENT_DUPLICATO` **non deve mai scattare**. Se compare in
`dbops.error_log`, non è un caso limite da tollerare: è il sintomo di una
regressione sul lock/progressivo, oppure di un chiamante che gira con un livello
di isolamento diverso da READ COMMITTED. In entrambi i casi si indaga, non si
allarga la maglia.
