## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_lotti](/dbzero/pagamenti/tabelle/vendite_contabili_lotti) — il legame lotto–distinta che il guard presidia
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — il registro che sa da quale atto è nata una distinta
>
> Approfondimento funzioni:
>
> * [script.fn_get_sistemazione_di_contabile](/dbzero/script/funzioni/fn_get_sistemazione_di_contabile) — la domanda «c'è un atto dietro questa distinta?», posta fuori dalla row security
> * [pagamenti.trgfn_vendite_contabili_guard_ente_centro](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_ente_centro) — il guard che portava l'altra metà della regola, prima che il legame cambiasse verso

---

### 🎯 Scopo Principale

Impedisce di agganciare a un lotto di fatturazione una distinta contabile nata da una sistemazione.

⭐ Sono due mondi: un lotto raccoglie le fatture prodotte in un **giro di emissione**; una
distinta di sistemazione registra un rimborso o una compensazione decisi su documenti **già
emessi**, e non appartiene a nessun giro.

---

### ⭐ Il predicato è «di sistemazione», non «di compensazione»

La regola vale per ogni distinta che un atto di sistemazione ha generato, qualunque sia la
destinazione: anche una distinta di **rimborso** non ha niente a che fare con un lotto. In
pratica le distinte di sistemazione sono quelle di rimborso e di compensazione: il riporto
genera un fondo fattura, non una distinta.

---

### ⭐ Una porta sola, dove si aggancia

È l'atto a sapere quale distinta ha generato (`sistemazioni.contabile_id`), non la distinta a
sapere da quale atto viene. Un guard sulla distinta non avrebbe il dato su cui appoggiarsi, e
alla nascita della distinta nessun atto la cita ancora. La regola si presidia quindi dove
nasce il pericolo: nel momento in cui la distinta si aggancia al lotto.

---

### 🔴 La domanda si fa fuori dalla row security

Il guard gira con i privilegi di chi scrive (`SECURITY INVOKER`), mentre
`pagamenti.sistemazioni` ha la RLS: leggendola da qui il guard vedrebbe solo gli atti visibili
all'operatore, e potrebbe tacere proprio su una distinta il cui atto non vede. La domanda
passa perciò da
[fn_get_sistemazione_di_contabile](/dbzero/script/funzioni/fn_get_sistemazione_di_contabile),
che è `SECURITY DEFINER`: il rifiuto non dipende da che cosa vede chi scrive.

---

### Codici errore

* `E_CONTABILE_SISTEMAZIONE_CON_LOTTO` — la distinta che si sta legando al lotto è nata da una
  sistemazione.

---

### Test

* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il test 9: la distinta di un
  rimborso confermato non si aggancia a un lotto.

---

### Note di migrazione

* 2026-08-22 — sostituisce `trgfn_vendite_contabili_lotti_guard_compensazione`, che leggeva
  `vendite_contabili.compensazione_id`: girato il verso del legame (l'atto punta la distinta)
  la colonna sparisce, il predicato si allarga da «di compensazione» a «di sistemazione», e la
  regola, che aveva due guardiani (questo e un ramo di
  `trgfn_vendite_contabili_guard_ente_centro`), ne ha uno solo. Il codice
  `E_CONTABILE_SISTEMAZIONE_CON_LOTTO` prende il posto di
  `E_CONTABILE_COMPENSAZIONE_CON_LOTTO`, marcato `obsoleto_dal`.
* 2026-08-22 — la lettura passa da una funzione `SECURITY DEFINER`: allora le distinte interne
  (come quella di una compensazione) erano visibili a tutti, e un operatore di un'altra azienda
  avrebbe potuto agganciarne una al proprio lotto senza che un guard `SECURITY INVOKER` vedesse
  l'atto dietro.
* 2026-09-15 — le distinte interne sono visibili solo al loro emittente; la lettura fuori dalla
  row security resta, perché il guard non deve dipendere da ciò che l'operatore vede.

---

{% include-markdown "signature-core.md" %}
