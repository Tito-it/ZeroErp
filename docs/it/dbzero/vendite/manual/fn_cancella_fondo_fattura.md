## 📘 Documentazione Concettuale – Funzione `vendite.fn_cancella_fondo_fattura`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — l'atto che il gesto cancella
>
> Approfondimento funzioni:
>
> * [vendite.fn_applica_cancellazione_fondo_fattura](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura) — la primitiva: perimetro, criterio e i tre `DELETE`
> * [vendite.fn_check_fondo_cancellabile](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile) — il criterio, che sta altrove
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il permesso: l'azione `governa_fondo_fattura`
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — l'altra strada che fa cadere un fondo: il riporto sbagliato, col suo permesso
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — chi decide su un fondo, e come
> * [Architettura permessi](/guide/architettura-permessi-e-autorizzazioni) §7.4 — il verbo e la primitiva

---

### 🎯 Scopo Principale

Il verbo del gesto **«cancella il fondo»**: cancella un atto di fondo fattura che non è ancora
diventato un fatto, oppure **rifiuta, dicendo perché**. È la funzione che chiama l'endpoint
`DELETE /api/v1/vendite/fondi-fattura/{id}/`, dal kebab dell'elenco «Fondi da decidere».

---

### Chi la chiama, e con quale permesso

È il verbo dell'endpoint. Gira come proprietario (`SECURITY DEFINER`), fuori dalla row security,
quindi permesso e perimetro li controlla il database:

* **il permesso**, in prima riga: l'azione `governa_fondo_fattura`
  ([`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione)), la stessa dell'endpoint.
  Chi arriva dall'interfaccia non riceve un rifiuto nuovo. Senza l'azione: `E_PERMESSO_NEGATO`;
* **il perimetro**, sull'atto: lo rimette la primitiva che il verbo chiama. Un atto di un'altra
  azienda «non c'è» (`E_FONDO_NON_TROVATO`, la stessa risposta di un atto inesistente).

**Le porte spente all'ingresso.** Il verbo spegne la GUC delle righe contabili e quella del reset
del lotto prima di fare qualunque cosa. Una GUC accesa davanti dall'applicazione non cambia
l'esito: in particolare non fa saltare il controllo della fattura figlia congelata.

---

### Che cosa fa: chiama la primitiva

Il lavoro lo fa
[`vendite.fn_applica_cancellazione_fondo_fattura`](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura),
riservata al proprietario: rimette il perimetro sull'atto, legge **una volta** il criterio
([`vendite.fn_check_fondo_cancellabile`](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile)) e
fa i tre `DELETE` nell'ordine che le chiavi esterne impongono, oppure rifiuta. Il dettaglio sta
nella sua scheda.

⭐ **Perché il verbo è separato dalla primitiva.** Un fondo cade da tre strade, ognuna col suo
permesso: questo gesto (`governa_fondo_fattura`), l'annullo di un riporto confermato (il livello
sull'area `pagamenti`) e il reset dei fondi dentro i verbi del reset del lotto. Se il permesso
stesse nella primitiva, chi annulla una sistemazione dovrebbe avere anche `governa_fondo_fattura`.

⭐ **Si cancella, non si annulla**: un atto che non è mai diventato un fatto non lascia una riga di
registro, lascia il posto vuoto che aveva prima.

---

### ⚠️ Due conseguenze da conoscere

1. **Il `DELETE` è definitivo**: la tabella non è storicizzata. Per il fondo `AUTOMATICA` della
   lista «da decidere» non c'è registro, e non se ne inventa uno: quell'atto non ha mai mosso
   denaro.
2. **Cancellare riapre la rigenerazione automatica**: il giro successivo può proporre un fondo
   nuovo, letto sul residuo di quel momento.

---

### Codici errore

* `E_PERMESSO_NEGATO` — manca l'azione `governa_fondo_fattura`, o manca l'utente.
* I codici della primitiva: `E_FONDO_NON_TROVATO`, `E_FONDO_NON_CANCELLABILE`,
  `E_FONDO_FIGLIA_CONGELATA`, `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE`,
  `E_VENDITE_CHIAMATA_NON_VALIDA`. Quando li solleva, e che cosa dicono, sta nella sua scheda.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: il verbo è
  `SECURITY DEFINER` e l'app lo esegue; senza `governa_fondo_fattura` risponde `E_PERMESSO_NEGATO`;
  l'atto di un'altra azienda risponde `E_FONDO_NON_TROVATO` e resta com'era.
* `db/pgtap/vendite/test-fondo-fattura-cancellazione.sql` — il gesto e i suoi rifiuti.

---

### Note di migrazione

* 2026-08-31 — nasce come sede unica dei tre `DELETE` del fondo; il reset dei fondi smette di
  scriverli da sé (brief-db-fondo-fattura-ricalcolo-e-governo, D-21).
* 2026-09-14 — il `DELETE` delle righe contabili passa dal guard del contenuto della distinta, e
  la funzione ne apre la porta.
* 2026-11-25 — diventa il verbo pubblico, `SECURITY DEFINER` col guard di `governa_fondo_fattura`;
  il corpo passa alla primitiva `fn_applica_cancellazione_fondo_fattura`, che rimette il perimetro
  prima dato dalla row security. Firma e risultato non cambiano
  (brief-db-porte-aperte-dalla-sola-guc, giro 8).

---

{% include-markdown "signature-core.md" %}
