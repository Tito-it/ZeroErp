## Documentazione Concettuale – Funzione `script.fn_guard_soggetto_pf_pura`

> **Vedi anche**
>
**Tabelle correlate:**
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Funzioni correlate:**
>
[script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
**Trigger chiamanti:**
>
[anagrafiche.trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`script.fn_guard_soggetto_pf_pura`** verifica che un soggetto
sia una **persona fisica "pura"**, cioè idoneo ad essere collegato ad un
`auth_user` nella veste di operatore interno (ruolo applicativo `OPERATORE`).

Funzione `fn_guard_*`: fail-fast, solleva eccezione via `fn_log_and_raise_error`
se la condizione non è soddisfatta. Altrimenti restituisce l'id passato
(pattern "pass-through" che permette la chain in query).

---

### Parametri di input

| Parametro       | Tipo                                  | Descrizione                              |
| --------------- | ------------------------------------- | ---------------------------------------- |
| `p_soggetto_id` | `anagrafiche.soggetti.id%TYPE` (uuid) | ID del soggetto da verificare. NOT NULL. |

---

### Output

Ritorna `anagrafiche.soggetti.id%TYPE`: lo stesso `p_soggetto_id` se il
soggetto supera tutti i guard. In caso contrario, solleva eccezione (non
ritorna).

---

### Regole di dominio verificate

1. **`p_soggetto_id` NOT NULL** — altrimenti `E_PARAMETRO_INVALIDO`.
2. **Soggetto esistente** in `anagrafiche.soggetti` — altrimenti `E_SOGGETTO_NOT_FOUND`.
3. **Partita IVA NULL** — un soggetto con partita_iva è un professionista o
   una ditta individuale, non una persona fisica pura. Se presente:
   `E_AUTH_USER_SOGGETTO_CON_PIVA`.
4. **Codice fiscale NOT NULL** — indispensabile per identificare univocamente
   la persona fisica. Se assente: `E_AUTH_USER_SOGGETTO_SENZA_CF`.

I guard 3 e 4 sono in sequenza (IF/ELSIF), quindi al primo fallimento la
funzione solleva e termina (fail-fast).

---

### Origine e razionale

La funzione estrae e generalizza la logica inline precedentemente presente
in `anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica`.
Motivazione (§4.2 WIP multi-face-auth):

* Il vincolo "solo PF pura" si applica a due bridge distinti:
  `risorse_umane_auth_user` (storico, per operatori) e `identita_digitali`
  con `ruolo_applicativo = OPERATORE`.
* Evitare duplicazione di logica (rischio di divergenza tra i due guard).
* Favorire la testabilità in isolamento (pgTAP) passando un `soggetto_id`
  noto piuttosto che simulare un intero INSERT sul bridge.

---

### Regole implementative

* Linguaggio `plpgsql`, volatile (fa side effect tramite
  `fn_log_and_raise_error` che scrive nel log errori).
* Uso di `%TYPE` su firma, RETURN e variabili locali per coerenza automatica
  con le colonne sorgente.
* Codici errore riusati dal modello legacy (`E_AUTH_USER_SOGGETTO_CON_PIVA`,
  `E_AUTH_USER_SOGGETTO_SENZA_CF`) per compatibilità di messaggistica con
  gli utenti che già conoscevano questi errori.

---

### Esempio d'uso

```sql
-- Dentro un trigger BEFORE INSERT di un bridge auth_user:
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
BEGIN
    -- (risolvi v_soggetto_id dal NEW del trigger)
    PERFORM script.fn_guard_soggetto_pf_pura(v_soggetto_id);
    -- se il guard passa, prosegui; altrimenti exception dal guard.
    RETURN NEW;
END;
```

---

{% include-markdown "signature-core.md" %}
