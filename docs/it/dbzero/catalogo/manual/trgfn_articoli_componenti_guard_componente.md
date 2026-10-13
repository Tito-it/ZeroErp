## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_componenti_guard_componente`

> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la check che chiama (documento `ARTICOLO`)
> [catalogo.articoli_componenti](/dbzero/catalogo/manual/articoli_componenti) — la tabella su cui opera
> [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva) · [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva) — i lati articolo delle stesse regole

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento Lotto 3c)

Il guard di tabella della **distinta**. Rifiuta un componente che la distinta non ammette,
sollevando il primo motivo di `script.fn_check_articolo_riga` per il documento `ARTICOLO`, con
il padre (`prodotto_id`):

| # | Motivo | Codice |
| --- | --- | --- |
| 1 | il componente è il padre stesso | `E_BOM_COMPONENTE_PADRE` |
| 2 | il componente è a sua volta composito (la distinta ha un livello, D-4) | `E_BOM_COMPONENTE_COMPOSITO` |
| 3 | il componente ha un'IVA diversa dal padre | `E_BOM_IVA_DISCORDANTE` |

Il predicato sta nella check; qui si solleva soltanto. Il «componente uguale al padre» lo
fermava già il CHECK `chk_articoli_componenti_no_selfref`, ma senza codice: ora parla prima il
guard, col motivo che vede anche il picker, e il CHECK resta la rete.

---

### Quando giudica

Trigger `trg_articoli_componenti_a10_guard_riga_componente_ins_upd`, **BEFORE INSERT OR UPDATE
OF componente_id, prodotto_id, attivo**. Giudica un legame **attivo** quando nasce, quando si
attiva, e quando cambia il componente o il padre. Un legame spento non si giudica. Un UPDATE di
un legame già attivo che non tocca componente né padre non si rigiudica: l'IVA di un articolo in
una distinta in vigore non cambia (lo tiene il lato articolo).

Il nome lo fa parlare **dopo** i guard sul padre (`block_solo_componente`, `guard_is_composito`):
prima la testata, poi la riga.

### Perché un guard suo

Il guard di tabella dei documenti (`script.trgfn_righe_guard_articolo_ammesso`) legge
`articolo_id` e un padre `bigint`. Nella distinta l'articolo è `componente_id` e il padre è
`prodotto_id`, un `uuid`. La regola resta una sola, nella check.

### Che cosa ha sostituito

`catalogo.trgfn_articoli_componenti_guard_un_livello` (Lotto 1) e
`catalogo.trgfn_articoli_componenti_guard_iva`, ritirati dal `20261013-61`.

---
{% include-markdown "signature-core.md" %}
