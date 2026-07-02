# Brief DB — Coda lavoro: esporre `stato_flusso_descrizione`

> **Tipo**: brief al team DB (dev/db-tid) · **Data**: 2026-07-01 · **Owner**: Tid
> **Priorità**: bassa (display field, nessuna logica) · **Stato**: ✅ **CONSEGNATO** via
> migration `20260701-11-update-fn-coda-lavoro-operatore-stato-descrizione` (commit
> `1ebb54295`).
>
> **⚠️ Correzione post-consegna**: questo brief era scritto sulla **base stantia**
> `20260614-02`. La versione **viva** era `20260628-07` (naming stato già bonificato). Di
> conseguenza: il §4 sotto era **già chiuso** (nessuna azione FE serviva), e il campo logico
> si chiama `stato_flusso_codice_interno` (non `stato_flusso_codice`). Contratto finale della
> fn: `stato_flusso_codice_interno` (logico) + `stato_flusso_codice` (display) +
> `stato_flusso_descrizione` (nuova). Il team DB ha giustamente ignorato la "nota
> implementativa" §2 (il JOIN suggerito non avrebbe matchato) ed esteso il CTE
> `stati_pendenti`.
>
> **Origine**: prerequisito **P0.1 (coda)** del
> [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md §8),
> emerso dalla ricognizione Fase 0 del 2026-07-01.

---

## 1. Contesto

La vista-racconto operatore (brief FE) richiede che la **coda lavoro** mostri lo stato del
flusso con la sua **descrizione umana**, non il `codice_interno` grezzo. Oggi la funzione
`pratiche.fn_coda_lavoro_operatore` espone solo il codice interno; il FE lo renderizza tale
e quale nel `Tag` di stato.

Fonte: `db/changelog/migrations_v2/20_code/pratiche/20260614-02-update-fn-coda-lavoro-operatore-esclude-terminali-mctit.yaml`.

## 2. Richiesta

Aggiungere alla `RETURNS TABLE` e alla `SELECT` finale di `fn_coda_lavoro_operatore` una
colonna display:

```
stato_flusso_descrizione   config.stati_flussi_pratiche.descrizione%TYPE
```

valorizzata dalla `descrizione` (NOT NULL) di `config.stati_flussi_pratiche` per lo stato del
flusso. La colonna esistente `stato_flusso_codice` (che oggi contiene il `codice_interno` —
vedi §4) **resta invariata**: serve al FE per la severity.

**Nessun'altra modifica**: solo un display field. La firma cambia (nuova colonna in output)
ma la semantica no.

### Nota implementativa (non vincolante)

La `flussi_base` oggi porta `sf.codice_interno AS stato_codice`; la `descrizione` non è
propagata. Approccio più semplice: nella `SELECT` finale aggiungere un
`JOIN config.stati_flussi_pratiche sfd ON sfd.codice_interno = c.stato_codice` e selezionare
`sfd.descrizione`. In alternativa estendere il CTE `stati_pendenti` con `descrizione` e
portarla lungo la pipeline. L'implementazione è vostra; il requisito è solo la colonna in
output.

Aggiornare di conseguenza la firma nel `rollback`, il `COMMENT ON FUNCTION`, e la doc
`docs/it/dbzero/pratiche/funzioni/` (se presente) + eventuale pgTAP della fn.

## 3. Impatto FE (già pianificato, non bloccante per voi)

Il FE (`PraticheCodaLavoro.vue`, punto **B2** del brief FE) leggerà
`item.stato_flusso_descrizione` come *value* del `Tag`, con fallback
`|| item.stato_flusso_codice` finché la colonna non è disponibile → **nessuna rottura** se la
modifica arriva dopo: il FE è forward-compatible.

## 4. Osservazione collaterale — trappola di naming (nessuna azione richiesta)

La `RETURNS TABLE` dichiara `stato_flusso_codice ... codice_interno%TYPE` e la valorizza con
`sf.codice_interno`: il **nome** dice "codice" ma il **valore** è il `codice_interno`. Questo
ha causato un bug FE latente (la severity veniva calcolata su un campo `stato_flusso_codice_interno`
inesistente → `undefined`), che **sistemiamo lato FE** usando `stato_flusso_codice`.

Non chiediamo un rename (romperebbe il contratto col FE che sistemiamo ora). Lo segnaliamo
solo come contesto: se un domani si volesse allineare il naming (`stato_flusso_codice` →
`stato_flusso_codice_interno`), sarebbe un breaking change da coordinare col FE.

---

*Alla presa in carico: aggiornare lo stato in testa e la riga P0.1 del brief FE §8.*
