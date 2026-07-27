# Brief DB — `fatturazione_immediata` nella whitelist di `fn_create_contratto`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid ·
> **Stato**: ✅ **DB CHIUSO** — changeset `20260727-40` applicato (EXECUTED
> 2026-07-27 23:55), pgTAP `plan(12)` **verde 12/12**. Resta la doc auto-gen
> dbzero da rigenerare ·
> **Priorità**: 🟢 BASSA *lato DB* — ma vedi §3: **c'è un difetto BE bloccante**
> che va chiuso a prescindere da questo brief.
>
> **Origine**: [brief-be-fe-emissione-fattura-mirata.md](brief-be-fe-emissione-fattura-mirata.md)
> step BE-6 (deviazione 1) · Fase B di
> [brief-db-emissione-fattura-per-documento-sorgente.md](brief-db-emissione-fattura-per-documento-sorgente.md).

---

## 1. Il fatto

La Fase B ha aggiunto `fatturazione_immediata` su `vendite.ordini`,
`vendite.contratti`, `vendite.ddt`. Ordini e DDT si creano con un `INSERT`
costruito lato BE, quindi la colonna è arrivata subito.

Il contratto no: si crea con la funzione madre `vendite.fn_create_contratto`,
che costruisce l'INSERT **da una whitelist sua**:

```sql
v_testata_allowed text[] := ARRAY[
    'billing_account_id', 'emittente_fiscale_id', 'istanza_utility_id',
    'utility_id', 'ambito', 'valido_dal', 'valido_al',
    'parent_contratto_id', 'data', 'listino_id',
    'tipo_variazione_globale', 'valore_variazione_globale',
    'categoria_cliente_id_snapshot', 'valuta_id', 'meta'
];
```

`fatturazione_immediata` non c'è. Una chiave fuori whitelist **non produce
errore**: viene semplicemente ignorata dal `jsonb_object_keys ... WHERE key =
ANY(...)`. Passarla dal BE significherebbe quindi **scartarla in silenzio** — il
campo sembrerebbe funzionare e non farebbe nulla.

## 2. Cosa serve

Aggiungere `'fatturazione_immediata'` a `v_testata_allowed` in
`vendite.fn_create_contratto`. Nient'altro: l'INSERT è già generico
(`jsonb_populate_record`), la colonna esiste, il default `false` resta per le
chiamate che non la passano.

Firma e `RETURNS TABLE` invariati → `CREATE OR REPLACE` puro, nessun `DROP`.

## 3. ⚠️ Perché non è bloccante — e cosa invece lo è

**Non è bloccante** perché la corsia si può decidere anche dopo la creazione,
con la PATCH in DRAFT: la scelta va fatta **prima del push in commessa**, e in
DRAFT il contratto non è ancora pushabile (`fn_list_contratti_da_pushare` filtra
lo stato `ATTIVO`). Senza questa modifica resta solo un salto in più
nell'esperienza: crea, riapri, spunta.

> ⚠️ **Correzione rispetto alla prima stesura di questo brief.** Diceva che «il
> caso d'uso è coperto per intero dalla PATCH». **Oggi non lo è**, per un
> difetto lato BE — non lato DB. Verificato su `dev/backend-tid` (`5f1c223bc`).

**Il difetto BE.** Sui contratti la catena della PATCH ha quattro anelli e ne
sono stati cablati tre:

| Anello | Stato |
|---|---|
| whitelist `_UPDATE_KEYS_TESTATA` (`contratti_service.py`) | ✅ contiene il flag |
| gate per stato — `_CONTRATTO_PATCH_ALLOWED_BY_STATE["DRAFT"]` | ✅ eredita dalla whitelist |
| **mapper `_build_update_data_testata`** | ❌ **non legge mai la chiave** |
| `write_cols` di `contratti_repository.update_contratto` | ✅ esteso |

Il mapper copia in `data` campo per campo, esplicitamente, e il flag non è tra
quelli; `data` è l'unica cosa che arriva al repository. Risultato: la colonna
aggiunta a `write_cols` è irraggiungibile.

Il sintomo dipende dal payload, e il caso reale è quello silenzioso:

- PATCH con il **solo** flag → `data` vuoto → 400 *«Nessun campo aggiornabile
  presente nel payload»* (fuorviante, ma rumoroso);
- PATCH **dal drawer** → `buildPayload()` manda sempre anche `ambito`,
  `valido_dal`, `data`, `listino_id`… → `data` non è vuoto → **200, toast
  «contratto salvato», flag non persistito**.

Quindi oggi, dalla UI, la corsia del contratto **non è impostabile** e
l'operatore non ha modo di accorgersene.

**Perché è sfuggito**: contratti è l'unico dei tre documenti con un mapper
esplicito. Ordini e DDT usano una dict-comprehension generica sul payload, dove
aggiungere la chiave alla whitelist *è* sufficiente. Lo stesso gesto su tre file
ha dato due successi e un no-op. Nessun test copre il flag su
contratti/ordini/DDT.

**Il fix** (BE, `dev/backend-tid`, in `_build_update_data_testata`):

```python
if "fatturazione_immediata" in payload:
    data["fatturazione_immediata"] = bool(payload["fatturazione_immediata"])
```

più un test che verifichi la persistenza dopo la PATCH. Va fatto **a
prescindere** da questo brief e **prima**: è il vero blocco. `bool(...)` chiude
anche il caso del valore nullo (vedi C4).

## 4. Garanzie

| # | Deve essere vero | Copertura |
|---|---|---|
| C1 | Creando un contratto **con** `fatturazione_immediata: true` nel `p_testata`, la colonna risulta `true` a DB | pgTAP `test-fn-create-contratto-v1.sql` caso 11 |
| C2 | Creando **senza** la chiave, la colonna resta `false` (default) — nessuna regressione sulle create esistenti | idem, caso 10 |
| C4 | Con la chiave **presente e a `null`** la chiamata **fallisce** (NOT NULL, `23502`): mai un NULL scritto di nascosto né un `false` dedotto in silenzio | idem, caso 12 |
| C3 | Il guard `trgfn_guard_fatturazione_immediata_immutabile` continua a respingere l'UPDATE su contratto già pushato | **già coperto** da `test-fatturazione-immediata-simmetria-sorgenti-v1.sql` caso 15 — non si ritesta qui |

> **Su C3**: riguarda l'`UPDATE`, e il guard è armato `BEFORE UPDATE OF`. La
> create non lo tocca. Resta in tabella come promemoria del perimetro, non come
> test da scrivere.
>
> **Su C4 — differenza voluta, da conoscere.** Il filtro della whitelist è sulla
> **presenza** della chiave, non sul valore. Il repository degli ordini fa
> l'opposto (omette le colonne opzionali quando valgono `None`, «None = lascia il
> DEFAULT»): lì la stessa chiamata passerebbe. Qui si preferisce l'errore al
> silenzio — meglio fermarsi che lasciar decidere la corsia a un default
> nascosto. **Contratto per il BE: omettere la chiave oppure mandare un
> booleano, mai `null`.**

## 5. A valle — checklist, non «una riga»

Quando il changeset è applicato, i punti da toccare sono sei, e quattro sono
commenti che **diventano falsi** (un commento sbagliato è peggio di nessun
commento):

| # | Dove | Cosa |
|---|---|---|
| 1 | `contratti_service.py` `_CREATE_KEYS_TESTATA` | rimettere `"fatturazione_immediata"` |
| 2 | idem, commento ⚠️ sopra `valuta_id` | **rimuovere**: dice «la fn madre non contiene *ancora* la colonna». Attenzione: il blocco è stato inserito senza riga vuota prima del commento di `valuta_id`, che ora sembra farne parte — separarli |
| 3 | `ContrattoDrawer.vue` | togliere `v-if="isEdit"` dal blocco del campo |
| 4 | idem, `handleSave()` ramo create | togliere lo scorporo `const { fatturazione_immediata: _soloInPatch, ...campiCreate }` |
| 5 | idem, commento in `buildPayload()` | aggiornare: non è più «solo in PATCH» |
| 6 | idem, commento del blocco template | aggiornare: non è più «solo in modifica» |

⚠️ **Ordine di rilascio**: la riga 1 va rilasciata **dopo** che la migration è
applicata in tutti gli ambienti. Invertirli riporta lo scarto silenzioso, che è
esattamente ciò che questo brief evita.

## 6. Proposte lasciate aperte (non fatte qui)

Due cose emerse lavorando, entrambe fuori dal perimetro di questo brief perché
cambierebbero comportamento oltre la singola colonna. Vanno decise, non
dimenticate.

**6a — La whitelist resta «fail-open».** Una chiave ignota è ancora scartata in
silenzio: fra un anno, alla colonna successiva, si ripete identico. Due rimedi
possibili, in ordine di costo:

- un test che confronti `_CREATE_KEYS_TESTATA` (meno `utility`, che è
  sotto-entità) con `v_testata_allowed`: fallisce nel momento in cui le due
  liste divergono, che è l'unico momento utile;
- rendere `fn_create_contratto` fail-loud sulle chiavi non whitelisted. Più
  pulito, ma cambia il comportamento di **tutte** le chiavi di una madre già in
  uso: da decidere, non da fare di slancio.

È la stessa filosofia del guard `20260727-08` («meglio una regola scritta che una
disciplina affidata alle persone»), applicata al livello sopra.

**6b — La finestra `ATTIVO` non è coperta da nessuno.** Il flag conta solo prima
del push. Ma:

- il push parte da `ATTIVO`;
- in `ATTIVO` la PATCH ammette solo `valido_al` e `meta`.

Fra i due c'è un vuoto: un contratto attivato il 1° e pushato a fine mese ha
settimane in cui il DB permetterebbe ancora il cambio e il BE no. Su ordini e
DDT il caso non esiste (documenti one-shot); su un contratto ricorrente
«me ne accorgo dopo l'attivazione, prima del primo push» è realistico, e oggi
l'unico rimedio è rifare il contratto. Il guard DB sa **esattamente** quando il
flag diventa intoccabile; la regola BE approssima per stato ed è più restrittiva
del dominio. Da decidere: aggiungere il flag a
`_CONTRATTO_PATCH_ALLOWED_BY_STATE["ATTIVO"]` lasciando al guard l'ultima
parola, oppure scrivere qui perché no.

## 7. Registro

### 2026-07-27 · Analisi critica del brief

Rilievi che hanno cambiato il documento: §3 poggiava su un fatto falso (il
difetto del mapper BE); mancava C4 (chiave nulla su colonna `NOT NULL`); §5
sottostimava i punti da toccare e non diceva nulla sull'ordine di rilascio; C3
era già coperto altrove. Aggiunte le due proposte aperte di §6.

### 2026-07-27 · DB sviluppato, applicato e verde ✅

| Oggetto | File |
|---|---|
| Changeset | `db/changelog/migrations_v2/20_code/vendite/20260727-40-update-fn-create-contratto-fatt-immediata-mctit.yaml` — EXECUTED 2026-07-27 23:55 |
| pgTAP | `db/pgtap/vendite/test-fn-create-contratto-v1.sql` — `plan(9)` → `plan(12)`, casi 10-12 = C2/C1/C4. **12/12 verde** |
| Baseline | riga rimossa da `db/pgtap/baseline-rossi.tsv` (rientro) |

`CREATE OR REPLACE` puro (firma e `RETURNS TABLE` invariati), `SECURITY INVOKER`
esplicito, rollback che ripristina la whitelist precedente. Corpo preso dalla doc
auto-gen, firma con `%TYPE` dal `20260707-12` (l'auto-gen li scioglie).

**Fixture riparato — il test era rosso da prima, e non per il codice.** Il file
era in `baseline-rossi.tsv` come `ERRORE_FIXTURE`: la precondizione cercava un
billing account **senza** dati precontrattuali, e non ne esistono più (42 BA su
42 ne hanno, verificato sul DB). Falliva quindi al caso 1 e abortiva l'intero
file — copertura reale zero, non parziale.

La riparazione non forza il dato: il trigger
`trgfn_contratti_snapshot_precontrattuali` non guarda il BA ma la coppia
`(istanza_utility_id, utility_id)` **del contratto**, che arriva dal payload. Il
fixture sceglie quindi la prima utility libera da precontrattuali per l'istanza
del BA, preferendo quella del BA stesso quando già lo è — il caso realistico
resta il primo candidato. La `CROSS JOIN LATERAL` scarta i BA per cui nessuna
utility è libera, così la coppia è garantita e non sperata.

Effetto collaterale utile: il file rientra dalla baseline dei rossi, che cala di
una riga (da 111 a 110).

### Prossimo passo

1. Doc auto-gen dbzero da rigenerare (`fn_create_contratto.md`) → poi il brief
   può passare in `work-done`.
2. **BE**: il fix del mapper (§3) — indipendente e prioritario, è il vero blocco.
3. **BE/FE**: la checklist di §5.
4. Decidere §6a e §6b.
