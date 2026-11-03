## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_lotti`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — il lotto di fatturazione, un lato del legame
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta contabile, l'altro lato, e il perimetro da cui la riga eredita la visibilità
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — il registro che dice se una distinta è nata da una sistemazione
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile) — la funzione che scrive il legame quando riceve un lotto
> * [pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione) — il guard che tiene fuori le distinte di sistemazione

---

### 🎯 Scopo Principale

Tabella ponte fra i lotti di fatturazione (`vendite.fatturazione_lotti`) e le distinte contabili vendite (`pagamenti.vendite_contabili`): dice quali distinte sono state generate da un giro di emissione.

La coppia lotto–distinta è unica: lo stesso legame non si scrive due volte. Lo scrive
`fn_get_or_create_vendite_contabile` quando la chiamano con un lotto, e la stessa funzione lo
usa per ritrovare la distinta già aperta di quel lotto invece di crearne un'altra.

---

### ⛔ Una distinta nata da una sistemazione non entra in un lotto

Un lotto raccoglie le fatture prodotte in un giro di emissione; una distinta di sistemazione
(rimborso o compensazione) registra una decisione presa su documenti **già emessi**, e non
appartiene a nessun giro. Il divieto lo tiene
[trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione),
che chiede al registro delle sistemazioni se dietro la distinta c'è un atto.

---

### 🔒 Chi la vede: chi vede la distinta

La policy di perimetro risale dalla **distinta** (`contabile_id`) all'emittente, e non nomina
il lotto. Il legame è un satellite della distinta: non è mai più chiuso della sua testata, e un
operatore non può appendere un legame alla distinta di un'altra azienda. Senza veste
applicativa la tabella non mostra niente (fail-closed).

---

### Codici errore

* `E_CONTABILE_SISTEMAZIONE_CON_LOTTO` — si lega a un lotto una distinta nata da una
  sistemazione (lo solleva il guard).

---

### Test

* `db/pgtap/rls/test-rls-vendite-contabili-lotti.sql` — la policy risale dalla distinta e non
  dal lotto, ciascun operatore vede solo i legami delle proprie distinte (anche interne), il
  satellite non è più chiuso della testata, la scrittura sulla distinta altrui è negata, e
  senza veste è fail-closed.
* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il test 9: la distinta di una
  sistemazione non si aggancia a un lotto.
* `db/pgtap/pagamenti/test-fn-get-or-create-vendite-contabile.sql` — il legame scritto e
  riusato dalla funzione che crea le distinte.

---

### Note di migrazione

* 2026-08-22 — il divieto, prima riservato alle testate con `compensazione_id` valorizzato,
  passa a tutte le distinte nate da una sistemazione: la colonna `compensazione_id` di
  `vendite_contabili` non esiste più, e il legame lo porta l'atto.
* 2026-09-10 — la tabella entra nel perimetro emittente con la sua policy, che risale dalla
  distinta.
* 2026-09-15 — le distinte interne smettono di essere visibili a tutti: anche il loro legame
  col lotto lo vede solo il loro emittente.

---

{% include-markdown "signature-core.md" %}
