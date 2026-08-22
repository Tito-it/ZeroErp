## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_ente_incasso`

### 🎯 Scopo Principale

(rev 2026-08-22)

Dice se l'operatore ha scope su un **canale di incasso**: risolve
`canale → conto → soggetto → emittente` e delega alla canonica
[fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope).

È un membro della famiglia `fn_scope_ef_whitelist_via_*`, come `_via_fattura`,
`_via_commessa`, `_via_efba` e `_via_sr`: **prende un riferimento, lo risolve in
un emittente, e non decide niente da sé**.

---

### ⭐ Perché il canale, e non la fattura

Quando mille euro arrivano in banca **non hanno ancora una fattura**, e in questo
sistema il perimetro dell'operatore si risolve *dalla fattura*. Applicare la
regola normale renderebbe la coda «da abbinare» **invisibile a tutti** — non
«visibile a chi non dovrebbe»: invisibile. E una lista vuota sembra una lista di
cose finite.

> La regola di dominio che scioglie il nodo (**D5**): un emittente è un'azienda
> con partita IVA propria; due emittenti non possono avere la stessa partita IVA;
> quindi **hanno conti correnti diversi**. Il denaro ha un padrone **dal primo
> istante** — l'ha deciso il cliente scegliendo su quale conto pagare.

⭐ E quella verità è diventata un **vincolo** e non è rimasta un'assunzione:
`ex_src_bancari_conto_incasso_un_solo_soggetto` su
[soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)
rende impossibile che lo stesso conto `INCASSO` stia su due soggetti.

---

### Regole principali

* La catena vive **tutta** in
  [fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id),
  che è `SECURITY DEFINER` ed è **la stessa che usa il guard di scrittura**: così
  lettura e scrittura non possono divergere.
* Resta perciò `SECURITY INVOKER` come le sorelle: non ha bisogno di leggere
  niente di riservato per conto suo.
* **Fail-closed** senza doverlo scrivere: catena interrotta → emittente `NULL` →
  la canonica risponde `false` (salvo super admin). È la stessa postura di
  `_via_fattura` su una fattura inesistente.
* È `STABLE`.

### Chi la usa

La policy `rls_vendite_contabili_perimetro_incasso` su
[vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili), che il proprio
canale ce l'ha in colonna.

{% include-markdown "signature-core.md" %}
