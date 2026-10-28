## 📘 Documentazione Concettuale – Funzione `vendite.fn_chiudi_versioni_listino_scadute()`

> 👀 **Vedi anche**
>
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) ·
> [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze) ·
> [vendite.fn_cessa_contratti_scaduti](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti) (il gemello)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-2)

**La chiusura per scadenza delle versioni di listino** (ATTIVA → CHIUSA). Lo chiama il job della
chiusura per scadenza, che lo legge dalla colonna `verbo_chiusura` del suo registro.

### Regole

* Chiude le versioni ATTIVE con la fine validità passata (< data operativa), nel perimetro
  dell'utente della sessione (la funzione è `SECURITY DEFINER`, col predicato della policy).
* È un passaggio di processo: la causa è la data, non l'operatore, quindi nessuna azione.
* Nessun parametro: chiunque lo chiami chiude solo ciò che il job chiuderebbe. Ritorna quante
  versioni ha chiuso.

---

{% include-markdown "signature-core.md" %}
