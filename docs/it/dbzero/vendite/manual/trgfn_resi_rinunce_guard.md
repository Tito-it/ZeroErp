## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_resi_rinunce_guard()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce) (presidiata) ·
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso)
>
> Gemello:
> [vendite.trgfn_resi_riconsegne_guard](/dbzero/vendite/funzioni/trgfn_resi_riconsegne_guard)
> · pattern d'origine:
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

Presidia il ponte delle **rinunce**: non si può dichiarare definitiva più merce di
quanta ne sia rientrata, e non si può rinunciare a merce che non era destinata a
tornare al cliente.

Trigger `BEFORE INSERT OR UPDATE OF qta, resi_riga_id` su
`vendite.resi_righe_rinunce` (fase `_a10_` = guard).

### L'invariante — e perché serve da due lati

Le due uscite di una riga reso — ri-spedire e dichiarare definitivo — **consumano la
stessa copertura**:

```text
quantita ≥ Σ riconsegnate + Σ rinunciate
```

Per questo l'invariante è presidiato **simmetricamente**: questo guard sul ponte delle
rinunce, e il gemello `trgfn_resi_riconsegne_guard` su quello delle ri-consegne — che il
2026-07-26 è stato **esteso** proprio per tenerne conto. Prima sommava solo le
ri-consegne: su una riga da 10 con 7 rinunciati avrebbe visto residuo 10 e lasciato
ri-spedire 10, portando `Σric + Σrin = 17 > 10`. Presidiare un solo lato non basta.

### Regole applicate, in ordine

1. `qta > 0` — difesa oltre al `CHECK` della tabella (`E_QTA_NON_POSITIVA`).
2. **Lock** `FOR UPDATE` su `resi_righe` **e su entrambi i ponti**: rinuncia e
   ri-consegna concorrenti si serializzano sulla **stessa riga padre**, senza alcun
   advisory lock. È il pattern di casa (mirror di
   `trgfn_ordini_ful_guard_consistenza`) e protegge anche le scritture dirette sul
   ponte, non solo quelle che passano dalle funzioni madri.
3. Il tipo reso deve essere `riapre_residuo = true`
   (`E_RESO_RICONSEGNA_TIPO_NON_VALIDO`, riuso del codice del gemello): su una riga
   *a credito* non c'è nulla da ri-consegnare, quindi nulla a cui rinunciare.
4. `Σ ric + Σ rin ≤ quantita`, escludendo la riga corrente in `UPDATE`
   (`E_RESO_RINUNCIA_SUPERA_RESO`, **560** — nome simmetrico a
   `E_RESO_RICONSEGNA_SUPERA_RESO`, 534).

### Perché la formula è inline e non dall'helper

`fn_resi_riga_residuo_riconsegna` calcola la stessa cosa, ma il guard deve **escludere
la riga in corso di modifica** (`TG_OP <> 'UPDATE' OR id <> NEW.id`) — cosa che l'helper,
pensato per la lettura, non sa fare. Stessa formula valutata su un insieme diverso:
l'helper resta il punto unico per i consumatori in **lettura**.
