# Brief DB — `fn_list_preventivi_da_pushare` natura-aware (solo righe COMMESSA)

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`). Spiega
> *cosa* fare e *perché*; **niente DDL pronto**.
>
> **Data**: 2026-06-09 · **Stato**: 🟡 APERTO — **prerequisito** dell'orchestratore
> `CONFERMA_VENDITA` (BE).
>
> **Origine**: chiusura del modello a split per natura (rif.
> [brief-preventivi-ordini.md](brief-preventivi-ordini.md) §7.1, §8). Il DB
> 2026-06-09 ha consegnato `fn_push_preventivo_a_ordine` (merce→ordine) + blocco
> ricorrente (D9), **ma** non ha reso natura-aware il push commessa.

## 1. Il problema (verificato)

Modello voluto (brief-preventivi-ordini §2): le righe di un preventivo ACCETTATO
si smistano **per natura**:

- `destinazione_tipo='ORDINE'` (merce) → **ordine** (`fn_push_preventivo_a_ordine`);
- `destinazione_tipo='COMMESSA'` (servizio una-tantum) → **commessa** (`push_a_commessa`);
- `destinazione_tipo='CONTRATTO'` (ricorrente) → **bloccato all'inserimento** (D9).

**Verificato**: `vendite.fn_list_preventivi_da_pushare` (alimenta il push commessa,
ultima versione `20260510-07`) **non considera la natura** → restituisce **tutte**
le righe ACCETTATE eligible, **incluse le righe merce**. Il commit natura
`3144cf642` non l'ha toccata.

**Conseguenza**: l'orchestratore `CONFERMA_VENDITA` (BE, da scrivere) che chiama
`fn_push_preventivo_a_ordine` per la merce **e** `push_a_commessa` per i servizi
manderebbe le **righe merce in entrambe** le destinazioni (ordine + commessa) =
doppio routing. Per questo l'orchestratore BE **non è sviluppabile** finché il
push commessa non esclude la merce.

## 2. Cosa fare (DB)

Rendere `vendite.fn_list_preventivi_da_pushare` **natura-aware**: includere
**solo** le righe la cui natura ha `destinazione_tipo='COMMESSA'`.

- JOIN `vendite.preventivi_righe pr → config.nature_vendita nv ON nv.id = pr.natura_vendita_id`,
  filtro `nv.destinazione_tipo = 'COMMESSA'` (data-driven, **non** hardcodare il
  codice `SERVIZIO_UNA_TANTUM`: la regola è sulla *destinazione*, coerente con il
  guard ricorrente data-driven di D9).
- Mantenere invariati gli altri filtri (stato ACCETTATO, esclusione righe già
  EMESSA in commessa, `p_preventivo_id` opzionale, uom canonica, ecc.).

### 2.1 Punto da decidere — righe con natura NULL

`preventivi_righe.natura_vendita_id` è **NULLABLE** ed è valorizzata dal trigger
di derivazione solo all'INSERT/cambio articolo. Le righe **storiche** (create
prima del trigger 2026-06-08) possono avere `natura_vendita_id IS NULL`.
Il filtro deve decidere il comportamento per NULL:

- **Opzione consigliata**: trattare `NULL` come **COMMESSA** (le includo nel push
  commessa), per non rendere "non-pushabile" il pregresso. Coerente col fatto che
  prima del modello natura tutto andava in commessa.
- Alternativa: backfill `preventivi_righe.natura_vendita_id` dall'articolo (come
  fatto per `articoli`) e poi `destinazione_tipo='COMMESSA'` stretto. Più pulito
  ma è DML aggiuntivo. **Da valutare col team DB.**

## 3. Coerenza con il gate EVASO (BE, fuori scope DB)

`fn_preventivo_ha_residuo_ordine` (`20260609-07`) già esiste per il gate EVASO:
l'orchestratore BE non evade il preventivo finché restano righe merce non
ordinate (D6). Questo brief riguarda **solo** la lista del push commessa; il
gate EVASO resta lavoro BE.

## 4. pgTAP (suggeriti)

- Preventivo ACCETTATO **misto** (1 riga MERCE + 1 riga SERVIZIO_UNA_TANTUM) →
  `fn_list_preventivi_da_pushare` ritorna **solo** la riga servizio.
- Preventivo di sole righe merce → lista **vuota** (niente da pushare a commessa).
- Riga con `natura_vendita_id IS NULL` → inclusa (per l'opzione NULL=COMMESSA).
- Regressione: preventivo di soli servizi → comportamento invariato.

## 5. Dopo la consegna (BE, separato)

Sbloccato il push commessa natura-aware, l'agente BE costruisce l'orchestratore
`CONFERMA_VENDITA` (handler `vendita.push_preventivo`): split merce→`fn_push_preventivo_a_ordine`,
servizi→`push_a_commessa` (ora servizi-only), aggancio `pratiche_sorgenti`
(ordine + commessa COLLEGATO), gate EVASO via `fn_preventivo_ha_residuo_ordine`.

---

*Brief DB — push commessa natura-aware. Prerequisito dell'orchestratore split
preventivo→(ordine+commessa). Da passare a `dev/db-tid`.*
