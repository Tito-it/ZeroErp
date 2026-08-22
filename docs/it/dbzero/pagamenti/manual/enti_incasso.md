## 📘 Documentazione Concettuale – Tabella `pagamenti.enti_incasso`
### 🎯 Scopo Principale
La tabella `pagamenti.enti_incasso` rappresenta i canali di provenienza dei flussi di incasso (banca, poste, PSP, altro), collegando il canale ai riferimenti anagrafici e operativi necessari all'import e riconciliazione.

### ⭐ Il conto su cui atterra il denaro — dal 2026-08-22

`soggetto_ruolo_conto_bancario_id` (**obbligatorio**, FK a
[soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari))
dice **su quale conto dell'azienda finisce il denaro di questo canale**.

⭐ **E' il perimetro dei soldi non ancora attribuiti** (D5). Quando mille euro
arrivano in banca non hanno ancora una fattura, e il perimetro dell'operatore in
questo sistema si risolve *dalla fattura*: senza questa colonna la coda «da
abbinare» sarebbe invisibile **a tutti** — che e' peggio di visibile a chi non
dovrebbe, perche' una lista vuota sembra una lista di cose finite. Il denaro ha
un padrone dal primo istante: l'ha deciso il cliente scegliendo su quale conto
pagare.

> ⚠️ **Obbligatorio su TUTTI i tipi**, non solo su `BANCA` come lo e'
> `bank_branch_id`. Un ente `POSTE`, `PSP` o `ALTRO` senza conto sarebbe lo stesso
> difetto travestito, con la coda invisibile spostata su un altro `tipo`. E il
> dato c'e': un conto corrente postale ha un IBAN, il saldo di un PSP arriva sul
> conto di accredito dell'emittente.
>
> ⚠️ **Da non confondere con `bank_branch_id`**, che e' la **filiale** e resta
> obbligatoria solo per `tipo = BANCA`: e' un fatto diverso, e non e' il
> perimetro.
>
> ⚠️ **La FK sa che la riga esiste, non che cosa e'.** Che il conto sia di
> **incasso** lo impone
> [trgfn_enti_incasso_guard_conto_incasso](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_conto_incasso):
> senza di lui un ente potrebbe appoggiarsi al conto dei **pagamenti**, che sta
> fuori dall'unicita' «un conto INCASSO -> un solo soggetto» — e il perimetro
> tornerebbe a essere un'assunzione senza che nessun errore lo dica.
>
> 📮 **Conseguenza operativa, ed e' voluta**: finche' i due emittenti non hanno un
> conto con `uso = 'INCASSO'` censito, **nessun canale e' configurabile**. Si
> fallisce alla configurazione, dove se ne accorge chi puo' rimediare, e non in
> esercizio dove non se ne accorge nessuno.

---

### Relazioni e vincoli principali
- FK verso `anagrafiche.soggetti_ruoli_conti_bancari` (`soggetto_ruolo_conto_bancario_id`, **obbligatoria**).
- FK verso `pagamenti.centri_riscossione` (`centro_riscossione_id`).
- FK verso `anagrafiche.soggetti_ruoli` (`soggetto_ruolo_id`).
- FK verso `anagrafiche.bank_branches` (`bank_branch_id`).
- `tipo` ammesso: `BANCA`, `POSTE`, `PSP`, `ALTRO`.
- Se `tipo = BANCA`, `bank_branch_id` e` obbligatorio; negli altri casi deve essere `NULL`.
- Vincoli applicativi tramite trigger:
  - `pagamenti.trgfn_enti_incasso_guard_psp()` — coerenza `tipo = PSP` / ruolo PSP
  - `pagamenti.trgfn_enti_incasso_guard_conto_incasso()` — il conto agganciato
    deve avere `uso = 'INCASSO'`

### Note operative
- Per `tipo = PSP` il `soggetto_ruolo_id` deve essere coerente con ruolo `PSP` e censito in `anagrafiche.psp`.
- `regole_match` puo` contenere configurazioni per matching automatico movimenti.

{% include-markdown "signature-core.md" %}
