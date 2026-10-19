## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_guard_istanza_del_ruolo()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto) — la domanda che pone
> [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/manual/trgfn_contatti_guard_contesto_soggetto) — la stessa regola sui contatti
> [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzo_ruolo) — chi crea l'indirizzo di un'istanza

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-15 del backend, decisioni D-17a … D-17d di Tid,
`brief-db-processi-accensione-per-ambiente` §6.17)

**L'istanza di un indirizzo o di un conto di un ruolo è del soggetto di quel ruolo.**

Un indirizzo del ruolo può valere per tutto il ruolo o per una sola istanza (una fornitura).
Senza questo controllo una riga poteva stare sul ruolo di un soggetto ed essere dell'istanza di un
altro: la ricerca degli indirizzi (istanza, poi ruolo, poi soggetto) avrebbe dato a un soggetto
l'indirizzo di un altro. Lo stesso vale per i conti bancari del ruolo.

Lo stesso corpo è montato su due tabelle:

| Tabella | Trigger |
| --- | --- |
| `anagrafiche.indirizzi` | `trg_indirizzi_a10_guard_istanza_ins_upd` |
| `anagrafiche.soggetti_ruoli_conti_bancari` | `trg_soggetti_ruoli_conti_bancari_a10_guard_istanza_ins_upd` |

---

### Quando scatta

* su ogni **creazione** e ogni **modifica**, chiunque scriva: le funzioni del DB e il backend, che
  può cambiare l'istanza di un indirizzo o di un conto;
* in modifica, solo se cambiano il ruolo o l'istanza: le righe di prima restano valide finché
  nessuno le tocca;
* una riga senza istanza vale per tutto il ruolo: niente da controllare.

---

### Che cosa rifiuta

| Caso | Codice | Campo |
| --- | --- | --- |
| l'istanza è di un altro soggetto | `E_ISTANZA_ALTRO_SOGGETTO` | `istanza_utility_id` |

Il campo arriva al backend col codice: il form lo mostra senza tradurlo.

---

### L'altra metà della regola

Il controllo guarda le righe che si scrivono. L'altro modo di rompere la regola sarebbe cambiare
il soggetto dell'istanza o del ruolo: non si può, tutte e due le colonne sono bloccate
(`E_ISTANZA_SOGGETTO_IMMUTABILE`, `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`).

---

### Test

`db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 3-12, 17).

---

{% include-markdown "signature-core.md" %}
