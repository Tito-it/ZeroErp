## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_emittenti_fiscali_regime_conferma`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [dbops.vw_emittenti_regime_non_confermato](/dbzero/dbops/views/vw_emittenti_regime_non_confermato)

### 🎯 Scopo

(01-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, D-11)

**Una conferma del regime fiscale vale per il regime a cui è stata data.** Se
`regime_fiscale_rf` cambia e `regime_fiscale_confermato_il` no, la conferma (data e
autore) si azzera, e l'emittente torna nel presidio
`dbops.vw_emittenti_regime_non_confermato`.

Senza, un emittente confermato a RF01 e passato a RF17 da una strada che non scrive
la conferma (un `UPDATE` a mano, un import) direbbe «RF17, confermato il … da …»:
una conferma data a un altro regime.

### Regole

* Trigger `trg_emittenti_fiscali_a20_regime_conferma_upd`, `BEFORE UPDATE OF
  regime_fiscale_rf`. Fascia `a20`: non è un guard, scrive un valore.
* Regime riscritto uguale: niente cambia.
* Regime cambiato **con** una conferma nuova nella stessa scrittura: la conferma
  resta. È la strada del form dell'emittente.
* Non solleva: non c'è niente da rifiutare, c'è un fatto da scrivere.

### Test

`db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 22-24).

---

{% include-markdown "signature-core.md" %}
