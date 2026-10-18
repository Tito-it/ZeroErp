## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_soggetto()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) — la singolare, che questa usa
> [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo) — la gemella del ruolo
> [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/manual/fn_indirizzo_elemento) — la grammatica dell'indirizzo

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-12 del backend, decisione D-16a di Tid,
`brief-db-processi-accensione-per-ambiente` §6.16)

**Scrive gli indirizzi di un soggetto, e dice quanti ne ha scritti.** È la gemella della plurale
del ruolo: stesse regole, cambia solo la matrice da cui si leggono i tipi obbligatori.

---

### Le regole

1. Ogni indirizzo passa dalla grammatica comune
   ([`fn_indirizzo_elemento`](/dbzero/anagrafiche/manual/fn_indirizzo_elemento)).
2. **La copia degli obbligatori** (attiva se non si dice il contrario): per ogni tipo
   obbligatorio del **tipo di soggetto** che manca, nasce una copia del primo indirizzo con quel
   tipo. Se l'operatore compila un indirizzo solo, gli obbligatori non compilati ricevono quello.
   La copia la fa il BB `fn_indirizzi_con_obbligatori`, comune alle due plurali.
3. **Un tipo che il soggetto ha già si salta.**
4. Ogni riga la scrive la singolare
   [`fn_crea_indirizzo_soggetto`](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto).

| Caso | Esito |
| --- | --- |
| il soggetto non esiste | `E_SOGGETTO_NOT_FOUND` |
| gli indirizzi non sono un elenco | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| elenco vuoto | 0, nessuna copia |

⚠️ I tipi obbligatori si leggono come nella gemella del ruolo: righe attive della matrice, senza
guardare la finestra di validità.

---

### Chi ne ha preso il posto

Fino al 19-10-2026 la copia degli obbligatori e il ciclo sugli indirizzi del soggetto erano una
procedura del backend (`SoggettiService._apply_auto_clone` e `_create_indirizzi_batch`): il
backend la ritira e chiama questa funzione.

---

### Test

`db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` (test 1-2, 10-14).

---

{% include-markdown "signature-core.md" %}
