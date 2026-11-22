# Brief DB — Componenti BoM non inizializzati su riga contratto composita FISSA

> **Status**: ✅ **COMPLETATO** — 2026-05-27. Fix applicato dal team DB su
> `dev/db-tid`: l'init dei componenti del padre composito ora risolve
> correttamente la quantità del padre anche per fonte `FISSA` (quantità in
> `qta_operativa` con `quantita` base NULL). Verificato live: un articolo
> composito AGGIUNTA al contratto crea i componenti, l'espansione li mostra e
> i prezzi dei componenti sono editabili. Lato FE/BE nessuna modifica
> necessaria (coerce JSONB→array, aggregazione `componenti` in `list_righe`,
> expander e pannello editabile erano già pronti).
> **Target team**: DB (`dev/db-tid`)
> **Origine**: smoke FE contratti — AGGIUNTA di un articolo composito con
> fonte `FISSA` non crea i componenti (lista senza espansione, EDIT mostra
> "nessun componente BoM").
> **Tipo**: bug di modello (fn init + interazione trigger qta).

---

## Sintomo

Carico manualmente un articolo composito su un contratto (riga AGGIUNTA),
fonte_quantita_attesa = `FISSA`, qta_operativa = 1. Dopo il save:
`vendite.contratti_righe_componenti` resta vuota per quella riga → niente
chevron di espansione in lista, ComponentiPanel EDIT vuoto.

## Diagnosi (dati reali)

| riga | fonte | `quantita` | `qta_operativa` | n. componenti |
|---|---|---|---|---|
| contratto #92 (rotta) | FISSA | **NULL** | 1 | **0** |
| contratto #39 (ok) | DERIVATA_COMPONENTI | 1 | NULL | 2 |
| offerta ecc. #39 (ok) | FISSA | **1** | NULL | 2 |

Catena causale:

1. `vendite.fn_contratto_riga_componenti_init` fa **no-op se `cr.quantita`
   (base) IS NULL** (`IF v_qta_padre IS NULL THEN RETURN 0`). Usa la
   quantità **base**, non `qta_operativa`.
2. Per fonte `FISSA` il FE/BE valorizza `qta_operativa` (+ uom), **non**
   `quantita`. La base dovrebbe derivare dal trigger
   `script.trgfn_qta_from_operativa`, ma quel trigger ha uno **short-circuit**:
   `IF NEW.qta_operativa IS NOT NULL AND NEW.uom_operativa_id IS NOT NULL
   THEN RETURN NEW` → non ricalcola `quantita`, che resta NULL.
3. Quindi all'`init` `cr.quantita` è NULL → no-op → zero componenti.

Le **offerte** (stesso identico modello: `quantita` + `qta_operativa` +
`fonte_quantita_attesa`, stessa fn init, stesso trigger) funzionano solo
perché lì il path popola direttamente `quantita` (vedi offerta #39:
`quantita=1`, `qta_operativa=NULL`). È un'asimmetria di come la quantità
del padre composito atterra in colonna, non una differenza di modello.

## Richiesta

Rendere l'init dei componenti del padre composito indipendente da **quale**
colonna porta la quantità del padre, per fonte FISSA. A scelta del team DB
(decidete voi il punto corretto nel modello):

- la fn `fn_contratto_riga_componenti_init` risolve la quantità del padre
  con fallback `qta_operativa` quando `quantita` (base) è NULL (es.
  `COALESCE`, con la conversione factor_to_base se pertinente); **oppure**
- il trigger `trgfn_qta_from_operativa` popola comunque `quantita` (base)
  quando arriva `qta_operativa` + uom su riga composita FISSA (rivedere lo
  short-circuit per questo caso).

Verificare la simmetria con `fn_offerta_eccezione_componenti_init` (stesso
guard `v_qta_padre IS NULL`): se l'allineamento del contratto sposta la
quantità su `quantita`, il caso offerta resta coperto; se invece si sceglie
il fallback in fn, valutare di applicarlo a entrambe per coerenza.

## Fuori scope

Nessuna modifica BE/FE prevista da questo brief: il fix vive in DB. Il FE
contratti invia già `qta_operativa` + uom + fonte coerenti (il guard
applicativo `_apply_fonte_quantita_logic` per FISSA pretende già
`quantita > 0` OR `qta_operativa > 0`).

---

*Brief DB — init componenti contratto composito FISSA. Speculare al fix
componenti offerta commerciale gia' atterrato.*
