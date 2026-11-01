## 📘 Documentazione Concettuale – Funzione `vendite.fn_lotto_natura_dal_segno(p_lotto_id)`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.fn_build_fattura_key](/dbzero/vendite/manual/fn_build_fattura_key) ·
> [vendite.fn_libera_attivita_fatturabili](/dbzero/vendite/manual/fn_libera_attivita_fatturabili) ·
> [vendite.fn_popola_fatture_rettifiche](/dbzero/vendite/manual/fn_popola_fatture_rettifiche) ·
> [Guida della fatturazione](/guide/fatturazione#la-natura-la-da-il-segno-del-documento)

### 🎯 Scopo
(31-10-2026 — brief `brief-db-contratto-righe-periodiche-in-commessa` §7.9, L17, decisione D-1 di Tid)

**Un documento che somma negativo è una nota di credito.** Il verbo, chiamato una volta per
lotto, decide la natura delle attività prima che nascano le testate.

### Il percorso

1. Il lotto. `p_lotto_id` NULL o `<= 0` → `E_VENDITE_CHIAMATA_NON_VALIDA`; lotto inesistente →
   `E_LOTTO_NON_TROVATO`; natura `FATTURA` o `NOTA_CREDITO` assente dal vocabolario →
   `E_CONFIG_MANCANTE`.
2. **Rieseguibile**: le marche del lotto si ritirano (le attività tornano `FATTURA`), poi si decide
   di nuovo.
3. Le attività `FATTURA` del lotto (lucchetto del lotto, non fatturate) si raggruppano per **chiave
   di testata**, calcolata da [`fn_build_fattura_key`](/dbzero/vendite/manual/fn_build_fattura_key),
   la stessa che userà la testata. Si somma quantità × prezzo.
4. Nei gruppi a totale negativo le attività diventano `NOTA_CREDITO` con la marca
   `natura_dal_segno`. La testata nasce poi nota di credito dalla chiave, col suo registro e la sua
   serie.

Ritorna quante attività sono diventate nota di credito.

### Regole

* Il segno è del **documento** (il gruppo), non della commessa: una commessa può dare più documenti.
* Il **misto** a totale negativo è una nota di credito con dentro la riga positiva; a totale zero o
  positivo resta `FATTURA`.
* Le attività nate `NOTA_CREDITO` (l'accredito di un reso) sono un gruppo loro e non si toccano: se
  le battezzasse il segno, un accredito in una commessa con altri addebiti finirebbe compensato in
  una fattura e perderebbe il legame con la riga che rettifica.
* **Perché un verbo per lotto, e non dentro la chiave**: la chiave nasce un'attività alla volta, e il
  totale del documento a quel punto non esiste. Calcolarlo dentro la chiave vorrebbe dire ricalcolare
  le chiavi di tutto il lotto per ogni attività.
* **Reversibile**: la marca la ritirano la liberazione
  ([`fn_libera_attivita_fatturabili`](/dbzero/vendite/manual/fn_libera_attivita_fatturabili)) e la
  riemissione dalla commessa (`fn_emit_attivita_fatturabili_da_commessa`).
* La chiama il backend (`fatture_righe_service.generate_fatture_righe`) dopo «in lavorazione» e
  prima delle testate, nella stessa transazione. La regola resta qui.
* La nota di credito cita poi le fatture dei pezzi stornati:
  [`fn_popola_fatture_rettifiche`](/dbzero/vendite/manual/fn_popola_fatture_rettifiche).
* `SECURITY INVOKER`, EXECUTE a `zeroerp_app`.

### 🧪 Il presidio

`db/pgtap/vendite/test-lotto-natura-dal-segno-v1.sql`: soli storni, misto negativo, misto positivo,
accredito di reso, rieseguibile, liberazione, citazione delle fatture.

---

{% include-markdown "signature-core.md" %}
