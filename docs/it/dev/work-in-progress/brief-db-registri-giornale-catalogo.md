# Brief DB — I registri del giornale hanno bisogno di un catalogo

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-19. **A chi:** team DB.
> **Origine:** rilettura critica del pezzo G dell'osservabilità
> (`piano-be-fe-osservabilita-pallino-e-superfici.md`, registro del 19-09) e
> decisione di Tid dello stesso giorno («ok procedi» sulla strada del catalogo).
>
> **In una riga:** il vocabolario dei **registri** che `script.vw_giornale_entita`
> cuce (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, `FATTURA_LOG`) oggi vive in
> **tre sedi che non si conoscono** — i letterali dei quattro rami `UNION ALL`
> della vista, la costante `GIORNALE_REGISTRI` del backend, l'array `REGISTRI`
> della view Vue — e **nessuna** porta l'etichetta: la tendina «Registro» del
> giornale mostra `EVENT_LOG` grezzo, un testo a video che non passa da `$t()`.
>
> ⇒ **Serve un catalogo** `config.registri_giornale` (§4), nella forma delle
> tabelle di configurazione che il lookup generico sa leggere, più **un pgTAP**
> che tenga la vista e il catalogo allineati nei due versi (§4.3). È lo stesso
> stampo di `config.tipi_entita` e `config.eventi_dominio`, i due vocabolari
> gemelli che la vista già porta in colonna.
>
> ⛔ **Il backend si ferma qui e aspetta**: BE/FE solo con prerequisiti DB
> pronti. Ciò che fa appena il seed è a DB è al §5, ed è poca roba.

---

## 1. Il fatto, letto dalla struttura

`script.vw_giornale_entita` (doc auto-gen `docs/it/dbzero/script/views/`) è
quattro `SELECT` in `UNION ALL`, e ogni ramo scrive il proprio registro come
**letterale**:

```sql
    'EVENT_LOG'::text   AS registro,   -- ramo 1, vendite.event_log
    'LOTTO_LOG'::text   AS registro,   -- ramo 2, fatturazione_lotti_log
    'TASK_RUN'::text    AS registro,   -- ramo 3, fatturazione_lotti_task_runs
    'FATTURA_LOG'::text AS registro,   -- ramo 4, fatture_log
```

Il commento della vista dichiara da sé che i registri **cresceranno** («i
registri di eventi del progetto sono **sei** … la domanda "cosa è successo a
questa pratica" arriverà. Un ramo nuovo entra con un `UNION ALL`»). Quel giorno
il quinto letterale entra nella vista; le altre due sedi **no**, e nessuna
delle due fallisce:

| Sede | Cosa succede col quinto registro |
| --- | --- |
| `GIORNALE_REGISTRI` (BE, `vendite_repository.py`) | il filtro `?registro=PRATICHE_GIORNALE` risponde **400** — corretto ma cieco: la riga c'è e non si può chiedere |
| `REGISTRI` (FE, `GiornaleListView.vue`) | la tendina **non lo mostra**. Nessun errore: le righe passano nel «tutti» e basta |

⚠️ La misura che segue è un **fatto datato**, non il motivo: al 19-09 le tre
sedi coincidono (quattro valori ovunque). Il motivo è sul modello — un
vocabolario che la vista **emette** e che due consumatori **validano e
mostrano** ha una sede sola, o diverge in silenzio. È già successo alla
tendina gemella «Entità»: sette codici ricopiati a mano contro **nove** a
catalogo (`FLUSSO`, `DEFINIZIONE_WORKFLOW` mancavano), chiuso il 19-09 con un
lookup su `config.tipi_entita`. Lì la sede c'era; qui **va creata**.

### 1.1 Il secondo difetto: l'etichetta

`config.tipi_entita` e `config.eventi_dominio` — gli altri due vocabolari che
la vista porta in colonna — dichiarano entrambi `etichetta_key`, l'indirizzo
i18n che il frontend risolve con `labelOrCode`. Il registro **no**: non ha
dove dichiararlo, quindi la tendina e la colonna «Registro» mostrano il codice
macchina. È l'unico testo del giornale che l'operatore legge in inglese
maiuscolo, e non per scelta.

## 2. Perché un catalogo e non le alternative

| Strada | Cosa risolve | Cosa lascia |
| --- | --- | --- |
| **A. Catalogo `config.registri_giornale`** + pgTAP di allineamento | una sede, l'etichetta dichiarata dal DB, lookup generico senza codice nuovo, il quinto registro = una riga di CSV | un changeSet e un pgTAP |
| B. Il backend espone `registri_ammessi` nell'envelope (da `GIORNALE_REGISTRI`) | la copia FE | la copia BE resta seconda sede rispetto alla vista; l'etichetta va inventata nel FE |
| C. `SELECT DISTINCT registro FROM vw_giornale_entita` | tutto, a parole | una scansione dei quattro registri per popolare una tendina: no |
| D. Una `fn_giornale_registri()` in `script` accanto alla vista | la sede unica | una funzione da tenere allineata a mano alla vista come la costante — sposta il problema in `script` |

**A**, perché è la forma che il progetto ha già scelto due volte per lo stesso
genere di dato (§1.1), e perché il pgTAP del §4.3 è l'unico presidio che
**lega la vista al catalogo nei due versi**: un ramo nuovo senza la sua riga fa
rosso, una riga senza il suo ramo fa rosso.

## 3. Cosa NON cambia

- La vista **non** fa `JOIN` sul catalogo: il registro resta un letterale nel
  ramo (è l'identità del ramo, non un dato da risolvere), e il catalogo lo
  **descrive**. Un `JOIN` per riga su quattro registri comprerebbe niente e
  costerebbe su ogni lettura del giornale.
- Nessuna FK da `vw_giornale_entita` (è una vista) né dalle quattro tabelle
  sorgente: il legame lo tiene il pgTAP, come per i `CHECK` che `valori_check`
  specchia lato Python.
- `GIORNALE_REGISTRI` nel backend **resta** finché il seed non è a DB; dopo, o
  si legge dal catalogo (§5) o si pinna al catalogo con un test — come
  `_CLASSI`/`_CANALI` di `processi_service` sono pinnate ai loro `CHECK`.

## 4. La richiesta

### 4.1 Tabella `config.registri_giornale` (`00_schema`)

Nella forma che `dbops.fn_get_lookup_codici` pretende — `id` intero,
`codice`, `codice_interno`, `descrizione`, `attivo` — più `etichetta_key` e
`obsoleto_dal` come le due sorelle:

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `smallint` IDENTITY, PK | il lookup generico vuole un id intero |
| `codice` | `text` NOT NULL, UNIQUE | mutabile, per la UI |
| `codice_interno` | `text` NOT NULL, UNIQUE, **immutabile** (`script.trgfn_lock_columns`) | è il valore che la vista **emette** in `registro` e che il BE valida — la chiave stabile |
| `descrizione` | `text` NOT NULL | italiano, per il lookup e l'export |
| `etichetta_key` | `text` NOT NULL | `config.registri_giornale.<codice_interno minuscolo>` — stesso patto di `tipi_entita` |
| `sorgente` | `regclass` o `text` NOT NULL | la tabella che il ramo legge (`vendite.event_log`, …): documenta il ramo e serve al pgTAP |
| `attivo` | `boolean` NOT NULL DEFAULT true | come ogni tabella config |
| `obsoleto_dal` | `date` NULL | ritiro senza cancellare (le righe vecchie del diario restano leggibili) |
| audit | `data_insert`/`user_insert`/`data_update`/`user_update` | standard |

### 4.2 Seed (`80_data/sql/config/registri_giornale.csv`, mirror `loadUpdateData`)

| codice_interno | descrizione | sorgente |
| --- | --- | --- |
| `EVENT_LOG` | Eventi di dominio | `vendite.event_log` |
| `LOTTO_LOG` | Log del lotto di fatturazione | `vendite.fatturazione_lotti_log` |
| `TASK_RUN` | Corse dei task di pipeline | `vendite.fatturazione_lotti_task_runs` |
| `FATTURA_LOG` | Log della fattura | `vendite.fatture_log` |

⚠️ `codice` = `codice_interno` alla nascita, come nelle sorelle. Le
`etichetta_key` le porta il frontend nei locales nello stesso giro del §5
(`check_i18n_keys.py` le trova nel CSV da sé: scandisce ogni CSV di `80_data`).

### 4.3 Il presidio (pgTAP, `db/pgtap/script/test-giornale-registri-catalogo-v1.sql`)

Dal template `_TEMPLATE.sql.txt`, con il contesto operatore. Due asserzioni,
**entrambe senza dati** — si legge la **definizione** della vista, non le sue
righe (regola zero: una prova che itera sul contenuto passa a vuoto in CI):

1. **ogni registro che la vista emette è a catalogo**: i letterali
   `'X'::text AS registro` estratti da `pg_get_viewdef('script.vw_giornale_entita')`
   sono tutti in `config.registri_giornale.codice_interno` con
   `obsoleto_dal IS NULL`;
2. **ogni registro vivo a catalogo ha il suo ramo**: il verso opposto — una riga
   seminata senza `UNION ALL` è una promessa che il giornale non mantiene.

Più il classico: `attivo`/`obsoleto_dal` coerenti, `codice_interno` bloccato dal
trigger (`throws_ok` su `UPDATE … SET codice_interno`).

⭐ È il pgTAP che rende il catalogo una **sede** e non una quarta copia: senza,
sarebbe la strada D con una tabella al posto della funzione.

### 4.4 Postura

Solo `SELECT` all'app, come le sorelle; niente RLS (vocabolario globale, come
`tipi_entita`). Nessun `GRANT` a ruoli batch nel changeSet (AGENTS.md §privilegi).

## 5. Cosa fa il backend appena il seed è a DB (nello stesso giro)

- `config.registri_giornale` entra in `_REL_CONSENTITE` (`dbops_repository`):
  il frontend monta `<LookupSelect rel="config.registri_giornale" value-field="codice_interno">`
  e l'array `REGISTRI` della view **sparisce**, come `TIPI_ENTITA` il 19-09.
- `GIORNALE_REGISTRI` si **pinna al catalogo** con un test su DB provvisto
  (`richiedi_db_provvisto`: l'insieme Python = `codice_interno` vivi), oppure
  il service la legge dal catalogo — decido alla consegna guardando il costo:
  la validazione del filtro sta su una richiesta di lista, e una `SELECT` da
  quattro righe per chiamata non è un problema, ma la costante pinnata è a
  zero round-trip e fa rosso alla prima divergenza, che è ciò che conta.
- La colonna «Registro» della lista `vendite.giornale` (seed `lista_colonna`
  887) prende un `formato` o uno slot che rende `labelOrCode` sull'etichetta:
  oggi mostra il codice grezzo.
- Locales: nove chiavi (`config.registri_giornale.*`, it/en), e la parola
  «Registro» sulla tendina resta.

## 6. Domande aperte al team DB

- **D1.** `sorgente` come `regclass` (si rompe se la tabella viene rinominata:
  è un pregio, dice subito che il ramo è da rivedere) o `text` (inerte)? Propongo
  `regclass`.
- **D2.** Il pgTAP legge `pg_get_viewdef` con una regex sui letterali
  `'…'::text AS registro`: è la forma con cui la vista è scritta oggi. Se il
  team DB preferisce, la vista può esporre i registri in un **commento
  strutturato** o in una `fn_giornale_registri()` `IMMUTABLE` usata dai rami
  stessi (`registro := 'EVENT_LOG'` → la funzione garantisce che sia a
  catalogo). Propongo la regex: non tocca la vista, e la vista è già stata
  riscritta due volte questo mese.

## 7. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-19 | Brief scritto. Backend in attesa; la tendina «Registro» del giornale resta sulla costante FE, dichiarata come seconda sede nel commento della view. |
