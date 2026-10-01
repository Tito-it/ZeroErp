## 📘 Documentazione Concettuale – Vista `dbops.vw_emittenti_regime_non_confermato`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali)

### 🎯 Scopo

(01-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, D-1, D-11)

**Gli emittenti fiscali attivi il cui regime fiscale nessuno ha confermato**
(`regime_fiscale_confermato_il` vuoto). **Deve restare vuota.**

⛔ Copre un guasto che non assomiglia a un errore. Il regime ha il default RF01
(D-1): un emittente in IVA per cassa lasciato a RF01 emette **tutte** le fatture a
esigibilità immediata, e nessun controllo lo dice. Un default è un regime che
nessuno ha dichiarato, e questa vista lo rende visibile.

### Perché tutti i regimi e non solo RF01

La conferma si azzera anche quando il regime cambia senza una conferma nuova: un
RF17 non confermato è lo stesso fatto, «nessuno ha dichiarato questo regime».
Filtrare su RF01 sarebbe un letterale di codice in un presidio, e un buco.

### Colonne

| Colonna | Significato |
|---|---|
| `emittente_fiscale_id` | l'emittente |
| `emittente_codice` | il suo codice |
| `regime_fiscale_rf` | il regime che nessuno ha confermato |

### A catalogo

`dbops.presidi`: natura `ZERO`, cadenza `SETTIMANALE` (è una condizione di
prontezza, non un incidente), perimetro `LIBERO` (`anagrafiche.emittenti_fiscali`
non ha RLS). Si svuota confermando il regime dal form dell'emittente.

---

{% include-markdown "signature-core.md" %}
