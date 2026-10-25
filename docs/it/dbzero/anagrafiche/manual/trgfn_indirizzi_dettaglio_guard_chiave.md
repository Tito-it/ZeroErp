## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/manual/indirizzi_dettaglio) — §«Unicità del civico»
>
**Approfondimento funzioni:**
>
[anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_normalize) — gira prima
> [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea» che ci passa
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — R7

---
### 🎯 Scopo Principale
(25-10-2026 — `brief-db-unicita-civico-indirizzi-dettaglio`, decisioni D2-a, D6 e D8 di Tid)

**Dire all'operatore che cosa non va nella chiave di un civico**, con un codice e il nome
del campo da correggere, invece di un errore tecnico del database (un `CHECK` o
l'indice unico).

---

### Le regole

| Regola | Quando | Codice | Campo |
| --- | --- | --- | --- |
| il civico, se c'è, è maggiore di zero | `INSERT` e `UPDATE` | `E_INDIRIZZO_CIVICO_NON_POSITIVO` | `civico` |
| estensione, palazzina, scala, piano e interno hanno almeno una lettera o una cifra | `INSERT` e `UPDATE` | `E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE` | la colonna |
| la riga non finisce sulla chiave di un'altra | solo `UPDATE` | `E_INDIRIZZO_DETTAGLIO_DUPLICATO` | — (l'indirizzo intero) |

* **«Senza numero civico»** si dice lasciando vuoto il civico. Lo zero o un negativo non
  sono un modo di dirlo: sarebbero due chiavi diverse per lo stesso indirizzo.
* **Soli segni** (`/`, `-`, `.`) non distinguono niente. `/A`, `-1` (piano interrato) e
  `BIS` passano; gli spazi da soli sono già diventati `NULL` nella normalizzazione.
* **Il doppione** si controlla solo in modifica. La modifica sul posto vuol dire
  «correggo l'indirizzo per tutti quelli che lo usano», e la frase nomina l'indirizzo che
  esiste già. In inserimento il doppione lo cerca il «trova o crea», e la corsa fra due
  sessioni la chiude l'indice: un errore qui, in quella finestra, gli toglierebbe la
  ri-lettura.

---

### Quando scatta

* `BEFORE INSERT OR UPDATE`, in fascia **z10**: dopo `trg_indirizzi_dettaglio_normalize_ins_upd`,
  quindi giudica i valori come si salvano (maiuscolo, vuoto → `NULL`, prefisso `/`).
* Un `UPDATE` che non tocca la chiave (via, civico e le cinque colonne del dettaglio) esce
  subito: le righe di prima restano valide finché nessuno le tocca, e la riattivazione
  fatta dal «trova o crea» passa senza giudizio.

---

### Le reti

I `CHECK` `chk_indirizzi_dettaglio_civico_positivo` e
`chk_indirizzi_dettaglio_dettaglio_leggibile` e l'indice `uq_indirizzi_dettaglio_norm_v2`
presidiano le scritture che non passano dai trigger. Il guard è la sede che parla.

---
{% include-markdown "signature-core.md" %}
