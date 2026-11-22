## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_ruolo_di_altro_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il soggetto del ruolo, che non cambia
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_istanza_di_altro_soggetto) — la stessa domanda per l'istanza
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — il guard dei contatti
> * [pratiche.trgfn_pratiche_guard_contesto](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_contesto) — il guard delle pratiche

---

### 🎯 Scopo Principale

`anagrafiche.fn_ruolo_di_altro_soggetto` risponde alla domanda «questo ruolo è di un altro soggetto?»:
restituisce il soggetto del ruolo quando non è quello dato, e niente altrimenti. È la gemella di
`anagrafiche.fn_istanza_di_altro_soggetto`.

---

### Che cosa risponde

| Caso | Risposta |
| --- | --- |
| Il ruolo è del soggetto dato | nessun valore |
| Il ruolo è di un altro soggetto | il soggetto del ruolo |
| Nessun ruolo, o nessun soggetto | nessun valore: non c'è niente da confrontare |
| Un ruolo che non esiste | nessun valore: lo rifiuta la chiave esterna della tabella che lo nomina |

---

### ⭐ Una domanda, non un controllo

La funzione non rifiuta niente: il rifiuto lo dà chi la chiama, col suo codice e col suo campo. Così due
guard su tabelle diverse fanno la stessa domanda con la stessa risposta, e ciascuno dice il proprio errore:

* `anagrafiche.trgfn_contatti_guard_contesto_soggetto` — un contatto sta su un ruolo del suo soggetto
  (`E_RUOLO_ALTRO_SOGGETTO`);
* `pratiche.trgfn_pratiche_guard_contesto` — il ruolo di una pratica è del soggetto della pratica.

La risposta è stabile perché il soggetto di un ruolo non cambia (`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`):
basta controllare la riga che nomina il ruolo quando la si scrive.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — i quattro casi della tabella (test 2), il
  contatto sul ruolo di un altro soggetto (test 13 e 16), il soggetto del ruolo che non si cambia (test 17).

---

### Note di migrazione

* 2026-10-19 — nasce dalla regola 3 dei guard delle pratiche, dove il confronto era scritto a mano, quando la
  stessa domanda serve ai contatti (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}
