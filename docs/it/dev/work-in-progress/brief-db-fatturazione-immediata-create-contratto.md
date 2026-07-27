# Brief DB — `fatturazione_immediata` nella whitelist di `fn_create_contratto`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid · **Stato**: ⬜ **DA FARE** ·
> **Priorità**: 🟢 BASSA (rifinitura: il caso d'uso è già coperto dalla PATCH)
>
> **Origine**: [brief-be-fe-emissione-fattura-mirata.md](brief-be-fe-emissione-fattura-mirata.md)
> step BE-6 · Fase B di
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

## 3. Perché non è bloccante

Il BE, per ora, **non manda la chiave in create** (whitelist
`_CREATE_KEYS_TESTATA` di `contratti_service`, con il motivo scritto sul posto)
e la imposta con la **PATCH in DRAFT**. Il caso d'uso è coperto per intero: la
corsia va decisa **prima del push in commessa**, e in DRAFT il contratto non è
ancora pushabile. Resta solo un salto in più nell'esperienza (crea, poi
spunta).

## 4. Garanzie

| # | Deve essere vero |
|---|---|
| C1 | Creando un contratto **con** `fatturazione_immediata: true` nel `p_testata`, la colonna risulta `true` a DB |
| C2 | Creando **senza** la chiave, la colonna resta `false` (default) — nessuna regressione sulle create esistenti |
| C3 | Il guard `trgfn_guard_fatturazione_immediata_immutabile` continua a respingere l'UPDATE su contratto già pushato |

## 5. A valle

Quando la whitelist è estesa, lato BE basta rimettere
`"fatturazione_immediata"` in `_CREATE_KEYS_TESTATA` (una riga, il commento sul
posto lo indica) e lato FE togliere il gate `isEdit` dal campo del
`ContrattoDrawer`.
