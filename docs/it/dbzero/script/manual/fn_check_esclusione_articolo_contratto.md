## 📘 Documentazione Concettuale – Funzione `script.fn_check_esclusione_articolo_contratto`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle](/dbzero/vendite/funzioni/trgfn_contratti_righe_guard_esclusione_figlio_bundle) — il guard, che solleva il **primo** motivo
> • [vendite.fn_contratto_righe_preview](/dbzero/vendite/funzioni/fn_contratto_righe_preview) — la superficie, che **spegne «Escludi»** (`escludi_blocco_codice`)
>
> **Sorgenti:** [vendite.contratti](/dbzero/vendite/tabelle/contratti) · [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti) · [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore)
>
> **Verifica:** `db/pgtap/vendite/test-contratto-righe-lista-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-09-28, `20260928-29`; rev `-36` lo stesso giorno)

**I motivi per cui un articolo NON si può escludere da un contratto.** Ritorna
`[]` se si può, altrimenti l'array **ordinato** dei motivi:
`[{codice, reason, reason_key, dettaglio, valori}, …]` (linee-guida-sql §12.5).

---

### ⭐ Perché esiste come funzione a sé

«Escludi» su un componente di un bundle del listino è rifiutato dal guard (il
bundle si vende come unità: si esclude il padre, mai il figlio). Ma il drawer
non lo sapeva: il pulsante era acceso e il rifiuto arrivava **dopo** il click.

Servono quindi due lettori della stessa regola: la lista delle righe del
contratto che spegne il pulsante, e il guard che rifiuta. ⭐ **Il guard chiama
questa funzione**, non riscrive il predicato: tooltip ed errore non possono
divergere.

---

### I motivi

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `FIGLIO_DI_BUNDLE` | `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` | l'articolo è componente di un bundle nella versione del listino che vale per il contratto |

`reason_key`: `vendite.contratti.escludi_blocco.figlio_di_bundle` (tooltip).
`valori`: l'articolo, lo stesso VARIADIC che il guard passava prima.

**Quale versione del listino**: se il contratto è attivo, quella fissata
all'attivazione; se è in bozza, quella in vigore oggi
([vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore)).
Senza listino: nessun bundle, nessun motivo.

---

### Forma

- Prende i **valori** (contratto, articolo), non l'id di una riga: una riga
  «dal listino» non esiste in `contratti_righe` finché non la si esclude.
- `STABLE`, `SECURITY INVOKER`, come il guard che la chiama.
- Nessun codice nuovo: nomina quello già a catalogo.

---

{% include-markdown "signature-core.md" %}
