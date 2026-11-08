## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_articolo_ammesso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la check che chiama
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) — il verbo che apre la porta della riconsegna

### 🎯 Scopo Principale

(latest review 2026-10-14, brief-db-articoli-ammessi-per-documento A-2, A-6, D-6; Lotti 3b e 3c, `20261013-56/-57/-61`; Lotto 4, `20261014-05`: la promo)

Rifiuta una riga il cui articolo il documento non ammette, sollevando il **primo motivo** di
`script.fn_check_articolo_riga`. Il predicato sta nella check: qui si solleva soltanto
(linee guida SQL §12.5.2). Un guard per tabella, così il motivo che l'operatore legge è il primo
dell'array.

---

### Montaggio

| Tabella | Trigger | `TG_ARGV` |
| --- | --- | --- |
| `vendite.preventivi_righe` | `trg_preventivi_righe_a10_regole_articolo_ins_upd` | `('PREVENTIVO', 'preventivo_id')` |
| `vendite.ordini_righe` | `trg_ordini_righe_a10_regole_articolo_ins_upd` | `('ORDINE_VENDITA', 'ordine_id')` |
| `vendite.ddt_righe` | `trg_ddt_righe_a10_regole_articolo_ins_upd` | `('DDT_VENDITA', 'ddt_id')` |
| `vendite.offerte_commerciali_eccezioni` | `trg_offerte_eccezioni_a10_guard_articolo_ammesso_ins_upd` | `('OFFERTA_COMMERCIALE', 'offerta_id')` |
| `vendite.contratti_righe` | `trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd` | `('CONTRATTO', 'contratto_id')` |
| `vendite.listini_righe` | `trg_listini_righe_a10_guard_articolo_ammesso_ins_upd` (anche `UPDATE OF listino_versione_id`) | `('LISTINO_VERSIONE', 'listino_versione_id')` |
| `vendite.promo_articoli` | `trg_promo_articoli_a10_guard_articolo_ammesso_ins_upd` | `('PROMO_ARTICOLO', 'id')`: la promo non ha un padre, il «documento» è la promo stessa |

La distinta ha un guard suo, [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente):
lì l'articolo è `componente_id` e il padre un `uuid`. Sulla versione di listino questo guard ha
preso il posto di `trgfn_listini_righe_guard_tipologia` e `trgfn_listini_righe_guard_no_composito`
(ritirati dal `20261013-61`).

La natura (preventivo, ordine, bolla) e il tipo d'eccezione (offerta, contratto) si leggono da
`to_jsonb(NEW)`: ognuno sta solo sulle sue tabelle, e un `NEW.colonna` assente non compilerebbe.

`BEFORE INSERT OR UPDATE OF articolo_id`. L'ordine dei nomi in fascia `_a10_` è portante:

```
…_a10_lock_columns_upd          la natura non si scrive a mano
…_a10_natura_vendita_ins_upd    la natura della riga
…_a10_regole_articolo_ins_upd   questo: giudica, con la natura scritta sopra
```

Su offerta e contratto il nome lo fa parlare **prima** dei guard di riga
(`…_a10_guard_articolo_ammesso` < `…_a10_guard_erogazione_obbligatoria`, `_perimetro`):
prima i motivi dell'articolo, poi quelli della riga. Lì ha preso il posto dei guard «aggiunta
fuori listino» ed «esclusione figlio di bundle» (ritirati dal `20261013-57`).

Sulla promo parla prima del guard delle date (`…_a10_guard_articolo_ammesso` <
`…_a10_guard_data_driven`): prima l'articolo, poi le date. Una promo già scritta non può
diventare invalida dopo: l'articolo con una promo è **usato** (A-10), e il suo flag «solo
componente» non cambia più.

Il picker ([catalogo.fn_articoli_ammessi](/dbzero/catalogo/funzioni/fn_articoli_ammessi)) mostra
lo stesso motivo prima della scelta.

Sul preventivo sostituisce il guard della ricorrenza `trgfn_preventivi_righe_set_natura_vendita`
(ritirato il 2026-10-13): la regola è il motivo 2 della check, con lo stesso codice e la stessa
frase.

---

### La riconsegna è esente (A-6)

Chi riconsegna restituisce ciò che è uscito, anche se l'articolo nel frattempo è cambiato. La
natura è già esente per costruzione: la riga riconsegnata porta quella della riga resa. Il solo
componente invece è un flag vivo dell'articolo.

Al momento dell'INSERT la riga di riconsegna non ha ancora il legame col reso, e la testata di
una riconsegna legata a un ordine è uguale a quella di una bolla da ordine. Quindi l'esenzione
passa da una **porta del verbo**: `vendite.fn_genera_ddt_riconsegna` accende
`zeroerp.ddt_riconsegna` con l'id del reso mentre scrive le righe, e la spegne subito dopo.

⭐ La porta è **stretta**: esenta solo una riga il cui articolo sta fra le righe di **quel**
reso. Il verbo è `SECURITY INVOKER`, quindi manca il controllo «proprietario della tabella»
delle altre porte: senza questo vincolo una GUC accesa per sbaglio esenterebbe qualunque
articolo.

---
{% include-markdown "signature-core.md" %}
