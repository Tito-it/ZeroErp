## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_istanza_di_altro_soggetto()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/manual/fn_ruolo_di_altro_soggetto) — la gemella per il ruolo
> [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/manual/trgfn_guard_istanza_del_ruolo) — il guard di indirizzi e conti del ruolo
> [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/manual/trgfn_contatti_guard_contesto_soggetto) — il guard dei contatti

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-15 del backend, decisioni D-17a … D-17d di Tid,
`brief-db-processi-accensione-per-ambiente` §6.17)

**Risponde alla domanda «questa istanza è di un altro soggetto?».**

Un'istanza (una fornitura) appartiene a un soggetto. Quando una riga porta un'istanza — un
indirizzo, un contatto, un conto, un billing account, una pratica — l'istanza deve essere del
soggetto della riga, o del suo ruolo. Altrimenti il dato di un soggetto finirebbe a un altro.

---

### Che cosa risponde

| Caso | Risposta |
| --- | --- |
| l'istanza è del soggetto dato | `NULL` |
| l'istanza è di un altro soggetto | il soggetto dell'istanza |
| nessuna istanza, o nessun soggetto | `NULL`: non c'è niente da confrontare |
| un'istanza che non esiste | `NULL`: la rifiuta la chiave esterna della tabella |

⭐ È una domanda, non un controllo: **il rifiuto lo dà chi la chiama**, ognuno col suo codice
d'errore e il suo campo. Per questo la stessa regola può avere codici diversi su tabelle diverse
(il billing account e le pratiche tengono i loro).

---

### Chi la usa

* `anagrafiche.trgfn_guard_istanza_del_ruolo` (indirizzi e conti del ruolo);
* `anagrafiche.trgfn_contatti_guard_contesto_soggetto` (contatti);
* `anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza` (billing account);
* `pratiche.trgfn_pratiche_guard_contesto` (pratiche, regola 4).

Prima il confronto era scritto a mano nel guard del billing account e in quello delle pratiche.

---

### Test

`db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 1).

---

{% include-markdown "signature-core.md" %}
