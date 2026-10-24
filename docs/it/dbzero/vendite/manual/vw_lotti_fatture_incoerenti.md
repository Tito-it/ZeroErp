## 📘 Documentazione Concettuale – Vista `vendite.vw_lotti_fatture_incoerenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
>
Approfondimento funzioni:
> • [vendite.fn_guard_lotto_fatture_stato_coerente](/dbzero/vendite/funzioni/fn_guard_lotto_fatture_stato_coerente)
> • [vendite.trgfn_lotto_fatture_guard_stato_coerente](/dbzero/vendite/funzioni/trgfn_lotto_fatture_guard_stato_coerente)

---
### 🎯 Scopo Principale

(rev 2026-10-24, R-1)

Elenca le fatture il cui **stato fiscale non coincide** con quello del lotto che le contiene.
È una **lista di lavoro**, non una vista di presentazione: in condizioni normali deve essere
**vuota**.

⭐ Dal 2026-10-24 è anche la **sede unica** della regola: il guard
`vendite.fn_guard_lotto_fatture_stato_coerente` legge le fatture incoerenti da qui, invece di
ripetere il filtro. Vista e guard non possono più dire cose diverse.

Serve a due cose diverse:

* **diagnosticare** — l'invariante è presidiata da tre `CONSTRAINT TRIGGER` differiti, che
  però falliscono al `COMMIT` e non dicono *quale* riga sia colpevole. Questa vista risponde a
  quella domanda;
* **misurare** — se contiene righe, sono incoerenze che i guard **non hanno intercettato**:
  arrivate prima che esistessero, o entrate con i trigger disabilitati.

---

### Che cosa considera incoerente

Una fattura il cui stato è **diverso** da quello del lotto, con una sola eccezione.

⭐ **La fattura `critical` rimasta indietro è esclusa di proposito.** Una fattura marcata
critica è un'anomalia *già nota e già segnalata*: il suo stato può legittimamente restare
indietro rispetto al lotto, perché è stata messa da parte. Includerla qui riempirebbe la lista
di casi conosciuti e la renderebbe inutile — una lista di lavoro vale finché è breve.

⛔ **Ma una fattura critical già congelata** (definitiva o oltre, non annullata) **dentro un
lotto non congelato** è incoerente ed entra in elenco: un documento definitivo non convive con
uno in errore nello stesso lotto (R-1 di Tid, 2026-10-24). Il «congelato» si legge dal
vocabolario degli stati (`congela_fiscale`, `is_abortito`). La colonna `fattura_critical`, in
coda, dice quale dei due casi è la riga.

⚠️ Il `COALESCE(f.critical, false)`: una `critical` nulla vale «non critica», quindi la fattura
**entra** in elenco. È il verso giusto — nel dubbio si segnala — ma va saputo leggendo i
risultati.

`IS DISTINCT FROM` invece di `<>` non è un dettaglio di stile: con `<>` una fattura o un lotto
con stato `NULL` non risulterebbe mai diverso, e l'incoerenza peggiore — quella dove lo stato
manca — sfuggirebbe.

---

### Il rapporto con i guard

L'invariante è presidiata da `trgfn_lotto_fatture_guard_stato_coerente`, il dispatcher
agganciato a tre `CONSTRAINT TRIGGER` `DEFERRABLE INITIALLY DEFERRED` su
`fatturazione_lotti`, `fatture` e sul ponte. Quelli **impediscono** che l'incoerenza si crei;
questa vista **trova** quelle già esistenti.

⚠️ Un elenco vuoto non prova che i guard funzionino, e un elenco pieno non prova che siano
rotti: potrebbero essere semplicemente più recenti dei dati.

---

### Scope

`WITH (security_invoker = on)`: eredita la RLS di chi interroga. Sia `vendite.fatture` sia
`vendite.fatturazione_lotti` hanno la RLS attiva, e il ponte è agganciato con **`JOIN`
interni**.

⚠️ Conseguenza da non sottovalutare per una lista di lavoro: **la vista è vuota anche quando
le incoerenze ci sono ma sono fuori dal perimetro** di chi guarda. Per una misura complessiva
va interrogata con una veste che veda tutto — altrimenti «zero incoerenze» significa
«nessuna che io possa vedere», che è un'altra cosa.

---

{% include-markdown "signature-core.md" %}
