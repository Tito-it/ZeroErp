## 📘 Documentazione Concettuale – Funzione `vendite.fn_clona_versione_listino(p_sorgente_id, p_codice_versione, p_valido_dal, p_valido_al)`

> 👀 **Vedi anche**
>
> [script.fn_check_versione_listino_clonabile](/dbzero/script/funzioni/fn_check_versione_listino_clonabile) ·
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) ·
> [vendite.fn_elimina_versione_listino](/dbzero/vendite/funzioni/fn_elimina_versione_listino)

### 🎯 Scopo
(29-10-2026 — brief `brief-modello-documento-vendita` §16.14, C-1; rivisto il 1-11-2026)

**Il verbo «Clona» di una versione di listino.** Il «cambio prezzi»: si copia una versione in una
nuova, si cambiano i prezzi che cambiano, si attiva la nuova. Copia la versione con i suoi prezzi
(righe e componenti dei compositi) e i suoi kit, in una sola transazione. Prende il posto della copia che il
backend faceva su tre tabelle.

### Il percorso

1. La versione da copiare, da qualunque stato. Non trovata o fuori perimetro:
   `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`.
2. Prima ciò che vieta: il primo motivo di
   [`script.fn_check_versione_listino_clonabile`](/dbzero/script/funzioni/fn_check_versione_listino_clonabile)
   (la copia comincerebbe prima della sorgente), sul campo `valido_dal`.
3. La versione nuova, dello stesso listino, con codice e date scelti: nasce in bozza.
4. Le righe attive della sorgente, con la loro periodicità.
5. I componenti attivi, con la validità ricalcolata sul periodo comune alla distinta e alla
   versione nuova: i prezzi valgono per il periodo nuovo.
6. I kit ([`vendite.listini_kit`](/dbzero/vendite/manual/listini_kit)), con la loro periodicità.

Fino al 31-10-2026 la periodicità delle righe non si copiava: una versione clonata da un listino
di quota fissa la perdeva (`20261031-38`, brief `brief-db-contratto-righe-periodiche-in-commessa`
§7.7).

Restituisce la versione nuova, quante righe e quanti componenti ha copiato e quanti componenti ha
saltato.

### Regole

* Un componente che non ha giorni in comune fra la distinta e la versione nuova si salta (per
  esempio la distinta lo toglie prima che la copia cominci): il conteggio lo dice.
* Le righe spente non si copiano; nella copia tutto nasce acceso.
* Gira con i permessi di chi la chiama (`SECURITY INVOKER`). Il permesso d'area lo chiede il
  backend.

### 🧪 Il presidio

`db/pgtap/vendite/test-fn-chiudi-clona-versione-listino-v1.sql`.

---

{% include-markdown "signature-core.md" %}
