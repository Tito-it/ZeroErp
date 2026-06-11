# Brief DB — `fn_list_preventivi_da_pushare` natura-aware (solo righe COMMESSA)

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-06-09 · **Stato**: 🟢 **IMPLEMENTATO A DB (2026-06-09)** —
> `20260609-09-update-fn-list-preventivi-da-pushare-natura-aware` + pgTAP
> `test-fn-list-preventivi-da-pushare-natura-aware-v1.sql`. Resta prerequisito
> **soddisfatto** per l'orchestratore `CONFERMA_VENDITA` (BE).
>
> **Decisione §2.1 presa**: righe con natura NULL trattate come **COMMESSA**
> (incluse), via `LEFT JOIN config.nature_vendita` + `(pr.natura_vendita_id IS NULL
> OR nv.destinazione_tipo = 'COMMESSA')`. Nessun backfill di `preventivi_righe`
> (alternativa rimandata).
>
> **Origine**: chiusura del modello a split per natura (rif.
> [brief-preventivi-ordini.md](brief-preventivi-ordini.md) §7, §8).

## 1. Il problema (verificato)

Modello voluto (brief-preventivi-ordini §2): le righe di un preventivo ACCETTATO
si smistano **per natura**:

- `destinazione_tipo='ORDINE'` (merce) → **ordine** (`fn_push_preventivo_a_ordine`);
- `destinazione_tipo='COMMESSA'` (servizio una-tantum) → **commessa** (`push_a_commessa`);
- `destinazione_tipo='CONTRATTO'` (ricorrente) → **bloccato all'inserimento** (D9).

`vendite.fn_list_preventivi_da_pushare` (alimenta il push commessa) **non
considerava la natura** → restituiva **tutte** le righe ACCETTATE eligible, merce
inclusa. L'orchestratore `CONFERMA_VENDITA` (BE) avrebbe mandato la merce in
**doppio routing** (ordine + commessa). Per questo era prerequisito bloccante.

## 2. Cosa è stato fatto (DB)

`fn_list_preventivi_da_pushare` resa **natura-aware**: include **solo** le righe la
cui natura ha `destinazione_tipo='COMMESSA'` (data-driven, non hardcoda
`SERVIZIO_UNA_TANTUM`). Tutti gli altri filtri invariati (stato ACCETTATO,
esclusione EMESSA, `p_preventivo_id` opzionale, uom canonica).

### 2.1 Righe con natura NULL — decisione

`preventivi_righe.natura_vendita_id` è NULLABLE (le righe storiche pre-trigger
2026-06-08 possono essere NULL). **Scelta**: NULL trattata come **COMMESSA**
(inclusa), per non rendere non-pushabile il pregresso (prima del modello natura
tutto andava in commessa). `LEFT JOIN` su `nature_vendita` per non perdere le
righe a natura NULL. Alternativa (backfill `preventivi_righe` + filtro stretto):
più pulita ma DML aggiuntivo — **rimandata**.

## 3. Coerenza con il gate EVASO (BE, fuori scope DB)

`fn_preventivo_ha_residuo_ordine` (`20260609-07`) esiste già per il gate EVASO:
l'orchestratore BE non evade finché restano righe merce non ordinate (D6). Questo
brief riguarda **solo** la lista del push commessa.

## 4. pgTAP (eseguiti)

`db/pgtap/vendite/test-fn-list-preventivi-da-pushare-natura-aware-v1.sql`:

- preventivo misto (MERCE + SERVIZIO_UNA_TANTUM) → solo la riga servizio;
- riga MERCE → esclusa;
- riga `natura_vendita_id IS NULL` → inclusa;
- preventivo di sole merci → lista vuota.

## 5. Dopo la consegna (BE, separato)

Sbloccato il push commessa natura-aware, l'agente BE costruisce l'orchestratore
`CONFERMA_VENDITA` (handler `vendita.push_preventivo`): split
merce→`fn_push_preventivo_a_ordine`, servizi→`push_a_commessa` (ora servizi-only),
aggancio `pratiche_sorgenti` (ordine + commessa COLLEGATO), gate EVASO via
`fn_preventivo_ha_residuo_ordine`.

---

*Brief DB — push commessa natura-aware. Prerequisito dell'orchestratore split
preventivo→(ordine+commessa). Implementato su `dev/db-tid` 2026-06-09.*
