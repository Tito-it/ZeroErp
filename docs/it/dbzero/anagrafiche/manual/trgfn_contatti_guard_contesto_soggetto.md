## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_contatti_guard_contesto_soggetto()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/manual/fn_ruolo_di_altro_soggetto) — la domanda sul ruolo
> [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto) — la domanda sull'istanza
> [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/manual/trgfn_guard_istanza_del_ruolo) — la stessa regola su indirizzi e conti

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-15 del backend, decisioni D-17a e D-17c di Tid,
`brief-db-processi-accensione-per-ambiente` §6.17)

**Il ruolo e l'istanza di un contatto sono del soggetto del contatto.**

Un contatto è sempre di un soggetto e, se serve, di un suo ruolo (cliente, fornitore, …) e di una
sua istanza (una fornitura). Senza questo controllo un contatto poteva stare sul ruolo o
sull'istanza di un altro soggetto.

---

### Quando scatta

Su ogni creazione e modifica della tabella `anagrafiche.contatti`; in modifica, solo se cambiano
il soggetto, il ruolo o l'istanza. Un contatto del solo soggetto non ha niente da controllare.

---

### Che cosa rifiuta

| Caso | Codice | Campo |
| --- | --- | --- |
| il ruolo è di un altro soggetto | `E_RUOLO_ALTRO_SOGGETTO` | `soggetto_ruolo_id` |
| l'istanza è di un altro soggetto | `E_ISTANZA_ALTRO_SOGGETTO` | `istanza_utility_id` |

Si controlla prima il ruolo. Spostare un contatto su un altro soggetto lasciandogli il ruolo di
prima è rifiutato per il ruolo.

---

### Test

`db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 13-16).

---

{% include-markdown "signature-core.md" %}
