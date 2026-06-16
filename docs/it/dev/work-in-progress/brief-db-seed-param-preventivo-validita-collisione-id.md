# Brief DB — Param `VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG` mancante (collisione id=38 nel seed)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🔴 URGENTE — rompe il form-defaults del preventivo (valuta/termine/iva).
> **Data**: 2026-06-15 · **Stato**: 🟥 APERTO (da applicare)
>
> **Origine**: diagnosi "aprendo il preventivo da pratica la valuta del BA non
> viene applicata". Causa root a DB (seed parametri), non nel codice BE/FE.

---

## 1. Sintomo

Aprendo il drawer preventivo (CREATE), i default **BA-derived** (valuta, termine
pagamento, iva) **non vengono applicati**. Il cliente/BA si compila, ma la valuta
resta vuota. Vale sia aprendo da pratica (BA prefillato) sia, in generale, ogni
volta che il FE interroga l'endpoint form-defaults del preventivo.

## 2. Causa root — collisione di `id` nel seed parametri

Il parametro **`VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG`** NON esiste in
`config.parameters`:

```
SELECT count(*) FROM config.parameters WHERE code='VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG';
-- 0
```

Il seed che dovrebbe crearlo —
`db/changelog/migrations_v2/80_data/sql/config/parameters_vendite_defaults.csv`
(changeset `20260430-62-upsert-parameters-vendite-defaults`, `loadUpdateData`
con `primaryKey: "id"`) — gli assegna **`id=38`**. Ma in DB **`id=38` è già
occupato** da un parametro di un altro dominio:

```
 id |                code               | default_value
----+-----------------------------------+--------------
 38 | documenti_allegato_upload_max_mb  | 25            <-- occupa l'id 38
 39 | VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA | false
 40 | VENDITE_CONTRATTO_DEFAULT_AMBITO  | COMMODITY
 ...
```

Il fratello `..._FATTURAZIONE_IMMEDIATA` (id=39) e tutti gli altri (40,42–50) sono
presenti: **solo l'id=38 è "saltato"** perché il `loadUpdateData` by-PK trova l'id
già esistente (di un altro dominio) e non inserisce la riga vendite. Risultato: il
param validità preventivo non viene mai creato.

### Perché rompe la valuta (catena BE→FE)

- `apps/vendite/services/vendite_form_defaults_service.fn_get_preventivo_form_defaults`
  richiede questo param: `ParameterService().get_defaults(["VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG"])`.
- `get_defaults` su un **codice non registrato** in `config.parameters`
  **solleva** (`fn_log_and_raise_error`: *"Parametro … non trovato nella tabella"*).
- L'eccezione fa **fallire l'intero endpoint** form-defaults (500), prima ancora
  di risolvere la valuta.
- Il FE (`PreventiviDrawer`, fetch dei defaults) cattura l'errore in un `try/catch`
  best-effort e prosegue: nessun crash, ma **valuta/termine/iva non applicati**.
  (NB: i BA in dataset hanno `valuta_id` diretto NULL → la valuta dipende
  interamente da questo endpoint, che risolve la catena BA→EF-del-BA→EF-utente.)

## 3. Cosa serve

1. **Inserire** in `config.parameters` il parametro mancante:
   - `code = VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG`, `default_value = '30'`,
     description come da CSV.
2. **Correggere la fragilità del seed** che ha causato la collisione (il *come* è
   vostro): preferibile far girare `loadUpdateData` con **`primaryKey: "code"`**
   (upsert per chiave di business) invece dell'`id` cablato, così l'id lo assegna
   la sequence e non si ripetono collisioni cross-dominio. In alternativa,
   assegnare a VALIDITA_GG un id libero.

### Nota collaterale (severità minore, stesso file)

Il changeset cita `VENDITE_CONTRATTO_DEFAULT_MODALITA = A` (id 41), ma il CSV
**salta da 40 a 42**: la riga manca e il param non è in DB. Oggi **non** è
richiesto dal service form-defaults BE (nessuna regressione nota), ma è comunque
un buco del seed: valutarne l'aggiunta mentre si sistema il file.

## 4. Criterio di accettazione

- `SELECT code, default_value FROM config.parameters WHERE code='VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG';`
  → 1 riga, valore `30`.
- Nessun altro param del CSV perso per collisione id (verifica che i 13 codici del
  changeset siano tutti presenti).
- In app: aprendo un preventivo (anche da pratica con BA), la **valuta** (e
  termine/iva) BA-derived viene applicata; l'endpoint form-defaults non dà 500.

## 5. Fuori scope

- Nessuna modifica BE/FE necessaria: il codice è corretto, attende solo il param.
  (`vendite_form_defaults_service` ha già il fallback `_param_int(..., 30)`; il
  problema è solo la registrazione mancante del codice.)
</content>
