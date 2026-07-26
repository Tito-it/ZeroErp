## 📘 Documentazione Concettuale – Funzione `vendite.fn_resi_riga_residuo_riconsegna(...)`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne)
> [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce)
>
> Consumatori:
> [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) ·
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare) ·
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) ·
> [vendite.fn_chiudi_riconsegna_reso](/dbzero/vendite/funzioni/fn_chiudi_riconsegna_reso)
>
> Da non confondere con:
> [vendite.fn_ordine_riga_qta_riconsegna](/dbzero/vendite/funzioni/fn_ordine_riga_qta_riconsegna)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

Risponde a **una sola domanda**: di questa riga reso, quanta merce resta ancora da
lavorare — cioè da ri-spedire al cliente oppure da dichiarare definitiva?

```text
residuo = resi_righe.quantita − Σ riconsegnate − Σ rinunciate
```

È il **punto unico** di quella formula. Prima esisteva in **tre** implementazioni
indipendenti (la vista dell'elenco, la madre della ri-spedizione, il guard del ponte) e
l'arrivo delle rinunce ne avrebbe richiesto una quarta: quattro copie da tenere
allineate a mano. Ora i consumatori la chiamano invece di ripetere il calcolo.

### ⚠️ Da non confondere con `fn_ordine_riga_qta_riconsegna`

Nomi simili, addendi diversi:

| Funzione | Risponde a | Letta da |
| --- | --- | --- |
| **questa** | «quanto resta da lavorare su **questa riga reso**?» | elenco ri-spedizione, madri, coda accrediti |
| `fn_ordine_riga_qta_riconsegna` | «quanta merce resa pesa ancora sul residuo di **quella riga d'ordine**?» | `fn_ordine_ha_residuo_evasione`, guard fulfillment |

La seconda **non** sottrae le ri-consegne: quelle sono già contate come `evaso` dal
fulfillment, e sottrarle di nuovo le conterebbe due volte.

### Regole chiave

- **Non filtra** stato del reso, `attivo`, né tipo `riapre_residuo`: è pura aritmetica di
  copertura sulla singola riga. I filtri di dominio restano ai chiamanti — la vista li ha
  nella `WHERE`, il guard deve poter valutare la copertura *mentre* la riga cambia.
  Metterli qui renderebbe la funzione inutilizzabile dal guard.
- **Riga inesistente → 0, non errore.** È letta da viste che la valutano su insiemi in
  movimento: un raise le farebbe fallire per una riga cancellata.
- **Mai negativa** (`GREATEST(0, …)`): l'invariante `quantita ≥ Σric + Σrin` è presidiato
  dai due guard dei ponti; qui si evita solo che un'eventuale incoerenza si propaghi come
  numero negativo nelle viste.
- `STABLE`, sola lettura. Guard di parametro standard (id `NULL` o `≤ 0` → errore
  parlante, mai normalizzazione silenziosa).

### Perché non la usano i guard

`trgfn_resi_riconsegne_guard` e `trgfn_resi_rinunce_guard` calcolano la stessa formula
**inline**, e non è una svista: il guard deve escludere la riga corrente in `UPDATE`
(`TG_OP <> 'UPDATE' OR id <> NEW.id`), cosa che questa funzione — pensata per la lettura —
non sa fare. Stessa formula, insieme diverso.
