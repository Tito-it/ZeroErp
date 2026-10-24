## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_id_da_coppia(...)`

> 👀 **Vedi anche**
>
> [fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'emittente del billing account
> [fn_scope_ef_perimetro](fn_scope_ef_perimetro.md) — la funzione di scope col perimetro
> [fn_resolve_emittente_fiscale_id](fn_resolve_emittente_fiscale_id.md) — lo stesso disegno, per l'emittente di una riga
> [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
> **Tabelle correlate:** [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account),
> [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)
>
> Brief: `brief-db-perimetro-una-volta-famiglie-residue` §4 (P-3)

---

### 🎯 Scopo Principale

(nata il 2026-10-21, `20261021-24`)

**Quale billing account è la coppia (istanza, utility)?** Alcune righe non
portano il billing account ma la coppia di colonne `istanza_utility_id`,
`utility_id`. La coppia individua al massimo un billing account
(`uq_billing_instance_utility`): questa funzione lo restituisce, o `NULL` se la
coppia non ne ha uno.

Risponde a una domanda di **fatto**, non di permesso. Per questo è
`SECURITY DEFINER`: `anagrafiche.billing_account` è sotto RLS, e letta da una
policy di un'altra tabella rieseguirebbe per ogni riga la policy del billing
account, con dentro il perimetro dell'operatore. Il permesso lo decide chi la
chiama.

---

### Chi la usa

* la policy `rls_istanze_dati_precontrattuali_ef_whitelist` su
  `anagrafiche.istanze_dati_precontrattuali`: il perimetro dell'operatore una
  volta per istruzione, per riga l'emittente del billing account della coppia;
* il modo `COPPIA` di [`dbops.fn_storico_risolvi_scope`](/dbzero/dbops/manual/fn_storico_risolvi_scope)
  (dal `20261021-28`).

⭐ Prima la stessa domanda era scritta due volte: dentro
`script.fn_scope_ef_whitelist_via_coppia`, che la policy chiamava per riga e
che è stata ritirata dal `20261021-27`, e nel ramo `COPPIA` dello storico. Ora
la risposta è una sola.

---

### Parametri e risultato

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_istanza_utility_id` | `anagrafiche.billing_account.istanza_utility_id%TYPE` | L'istanza della coppia. |
| `p_utility_id` | `anagrafiche.billing_account.utility_id%TYPE` | La utility della coppia. |

Risultato: `anagrafiche.billing_account.id%TYPE`, oppure `NULL`.

⚠️ Funziona perché la RLS è **abilitata ma non forzata**: il proprietario delle
tabelle, che è anche il proprietario della funzione, la scavalca. Con un
`FORCE ROW LEVEL SECURITY` andrebbe rivista, come `fn_resolve_emittente_fiscale_id`.

Presidi: `rls/test-rls-istanze-dati-precontrattuali-v1` (il perimetro
esercitato, con la RLS del billing account accesa) e
`script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (il piano).

---

{% include-markdown "signature-core.md" %}
