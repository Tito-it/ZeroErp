# Mini-brief DB — Seed colonne lista UI coda accrediti (forma contatore)

> **Tipo**: mini-brief al team DB (companion) · **Target**: `dev/db-tid` · **Data**: 2026-07-18 · **Owner**: Tid
> **Stato**: ✅ **REALIZZATO E CHIUSO** (2026-07-19) — seed applicato dal team DB (colonne
> `ui.lista_colonna` 200-203, applicato non pushato) con **deviazione motivata**: l'opt-in
> di `tenuti`/`fatturati` richiedeva un preset che la lista 10 non aveva — e nessuna delle
> tre liste resi (9/10/11) ne aveva uno → creati `resi_default`,
> `resi_da_accreditare_default`, `resi_da_riconsegnare_default` (comportamento odierno
> replicato, sole `tenuti`/`fatturati` nascoste; `ordinamento_default` volutamente vuoto
> per non scavalcare l'ordine BE). Note recepite: `tipo_dato = numeric` (l'enum non ha
> `number`); `filtrabile` solo su `etichetta`; gruppo nuovo **Accredito**; seedata anche
> `priorita` responsive per l'intera famiglia resi (accredito_dovuto 98 = il risultato,
> tenuti/fatturati 15 = gli addendi). ⚠️ Effetto DEF-2 attivo da ora: con un preset in
> gioco le preferenze utente salvano `preset_base_id` e un futuro ritocco al preset
> mostrerà il banner "preset aggiornato".
> **Parte FE chiusa (2026-07-19)**: 4 chiavi i18n `col_*` it+en create, **verificato
> end-to-end live** su `ui.fn_resolve_lista_config`: accredito_dovuto/etichetta visibili,
> tenuti/fatturati opt-in, `etichetta_i18n_key` combacianti; parità it/en programmatica,
> build Vite verde.
> **Origine**: sviluppo BE/FE di [brief-be-fe-ddt-resi-dashboard.md](../work-in-progress/brief-be-fe-ddt-resi-dashboard.md).
> La `vw_resi_da_accreditare` in forma contatore (`20260718-01`) espone quattro colonne nuove
> — `accredito_dovuto`, `etichetta`, `tenuti`, `fatturati` — ma il **catalogo lista UI**
> `vendite.resi_da_accreditare` (`ui.lista_definizione` id **10**, colonne 161-172) è rimasto
> alla forma vecchia: le colonne nuove **non compaiono** nella `<ListaConfigurabile>` finché
> non sono a catalogo. Il BE le espone già (`SELECT v.*` + order_cols aggiornate), il FE ha
> già gli slot di rendering: manca solo il seed.

## 1. Cosa serve

Append a `ui.lista_colonna` (loader `runOnChange`) per `lista_id = 10`, quattro righe:

| codice | campo_sorgente | tipo_dato | note |
| --- | --- | --- | --- |
| `accredito_dovuto` | `accredito_dovuto` | number | **l'informazione centrale della coda** («fatturata per 10, tenuta 7 → accredito 3»): visibile di default, posizione prominente (dopo `descrizione`), ordinabile |
| `etichetta` | `etichetta` | string | `DOVUTA` \| `FACOLTATIVA` — il FE la rende come Tag i18n (slot già scritto); visibile di default, ordinabile, filtrabile |
| `tenuti` | `tenuti` | number | il conto della partita — opt-in (non nei preset), ordinabile |
| `fatturati` | `fatturati` | number | idem | 

Etichette i18n FE già pronte non servono a catalogo (`etichetta_i18n_key` nuova famiglia
`vendite.resi_da_accreditare.col_*` come le righe 161-172 esistenti — le chiavi col_* le
aggiungiamo noi lato FE quando arriva il seed, come da flusso standard).

## 2. Contorno (decidete voi)

- `quantita` (169) resta: è la quantità resa della riga, diversa da `accredito_dovuto`.
- ⚠️ `ddt_numero` (165) ora è **nullable** (join LEFT nella vista): nessuna azione a
  catalogo, il FE mostra già "—".
- Se all'append aggiornate anche la colonna `azioni` (172) o i preset, nessun vincolo
  dal FE.

## 3. Perché non lo facciamo noi

Seed/changeset DB passano dal team DB ([[feedback_db_actions_passaggio_team]]). Tutto il
resto (BE order_cols, filtro `etichetta` whitelisted, slot FE, i18n) è **già sviluppato e
in attesa**: all'apply del seed le colonne compaiono senza altro rilascio.
