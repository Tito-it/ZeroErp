## 📘 Documentazione Funzione – `dbops.fn_storico_risolvi_scope`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.storico_scope_policy](/dbzero/dbops/manual/storico_scope_policy) — la mappa che legge
>
**Approfondimento funzioni:**
>
• [script.fn_get_ba_emittente_sr_id](/dbzero/script/manual/fn_get_ba_emittente_sr_id) — il ramo `BA`
• [script.trgfn_storico_generic](/dbzero/script/manual/trgfn_storico_generic) — chi la chiamerà
>

### 🎯 Scopo Principale
(latest review 11-09-2026)

Data una tabella (schema e nome) e una sua riga in forma `jsonb` — quella che il
trigger di storico ha già in mano — risponde con **l'emittente fiscale a cui
quella riga appartiene**, seguendo la strada scritta in
`dbops.storico_scope_policy`. Il trigger scrive quel valore nella tabella di
storico, dove resta congelato.

```sql
-- 77: la colonna c'è e si copia
SELECT dbops.fn_storico_risolvi_scope('vendite', 'ddt', '{"emittente_fiscale_id": 77}');

-- l'emittente della fattura 123, risalendo dalla riga
SELECT dbops.fn_storico_risolvi_scope('vendite', 'fatture_righe', '{"fattura_id": 123}');
```

Brief: `brief-db-rls-storico-scope-congelato`, §4b.

---

### Che cosa fa, modo per modo

| `modo` | La funzione… |
| --- | --- |
| `EF` | legge la colonna e la restituisce |
| `SR` | legge la colonna e cerca l'emittente fiscale con quel soggetto-ruolo (è 1 a 1) |
| `BA` | legge il billing account, ne prende l'unico emittente con `script.fn_get_ba_emittente_sr_id` (mapping specifico, altrimenti il gestore globale) e lo converte |
| `PADRE` | legge la chiave verso il padre, **carica la riga del padre** per `id` e **si richiama** sulla riga di mappa del padre — così una catena a più salti si risolve da sola |
| `COPPIA` | legge le due colonne dichiarate (istanza, utility), cerca il billing account di quella coppia e ne prende l'emittente come nel modo `BA`; coppia senza BA → `NULL` (dal 2026-10-09). Dal 2026-10-21 il BA lo dice [`fn_get_ba_id_da_coppia`](/dbzero/script/manual/fn_get_ba_id_da_coppia), la stessa risposta della policy dei dati precontrattuali |
| `NESSUNO` | risponde `NULL` |

Una tabella **senza riga di mappa** risponde `NULL` come un `NESSUNO`: il
controllo `test-storico-scope-policy-v1` la vede.

---

### ⭐ Perché gira come il proprietario (`SECURITY DEFINER`)

La chiama il trigger di storico, che gira **come chi sta scrivendo** la tabella —
cioè l'applicazione, sotto row level security. Il padre di un satellite può non
essere visibile a chi scrive (un processo di sistema, una veste diversa): se la
risalita leggesse con i permessi del chiamante, troverebbe niente, scriverebbe
`NULL`, e quella versione **sparirebbe a tutti** in silenzio.

Catturare lo scope è un atto di sistema: si legge come il proprietario delle
tabelle. ⚠️ Attraversa la RLS solo perché chi migra possiede anche le tabelle (la
RLS del progetto è `ENABLE` senza `FORCE`): non lo si presume, lo asserisce il
test 13 del pgTAP. ⚠️ Non è una porta aperta: restituisce **un solo numero**,
derivato da una riga che il chiamante ha già in mano.

---

### ⚠️ Perché non solleva errori, tranne in un caso

Una tabella non mappata, una colonna vuota, un padre sparito danno **`NULL`**. La
storicizzazione non deve fermare la scrittura della tabella per un difetto della
mappa; e il `NULL` sulla tabella di storico è **chiuso** (la versione non si vede)
e **visibile** al controllo automatico. L'unico caso in cui solleva è la catena
che non termina — un ciclo nella mappa — perché lì l'alternativa sarebbe girare
per sempre: `E_STORICO_SCOPE_CATENA_CICLICA`, un errore tecnico, non di dati.

---

### Dettagli tecnici

* Il padre si cerca per **`id`**, castando il testo del `jsonb` al tipo vero della
  colonna (`bigint`, `integer`, `smallint`, `uuid`): così usa l'indice.
* Il padre si risolve per nome qualificato con `to_regclass`, quindi vale anche
  per tabelle temporanee (`pg_temp`): è ciò che permette al pgTAP di costruire una
  catena di prova senza dipendere dai dati.
* `search_path` fissato a `pg_catalog, pg_temp`; ogni oggetto è nominato con lo
  schema.
* `EXECUTE` a `zeroerp_app` (lo chiama il trigger), non a `PUBLIC`.
