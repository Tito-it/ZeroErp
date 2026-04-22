## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_componenti_block_modifica_struttura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
>
> **Approfondimento funzioni:**
>
> • [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)  
>
---

### 🎯 Scopo Principale

(latest review 22-04-2026)
La funzione **`catalogo.trgfn_articoli_componenti_block_modifica_struttura()`**
protegge l'immutabilita' strutturale della distinta base
(`catalogo.articoli_componenti`) dopo l'inserimento della riga.

La regola operativa e': una riga di BoM non si corregge modificandone la
struttura o cancellandola, ma chiudendo la validita' della riga corrente
(`valido_al`) e inserendo una nuova riga con la struttura aggiornata.

---

### Contesto

`catalogo.articoli_componenti` rappresenta la BoM lato vendita con
versionamento temporale. Per mantenere una cronologia leggibile e impedire
modifiche retroattive della struttura, il trigger applica il pattern
**chiudi + inserisci**:

* la riga storica resta disponibile per il periodo in cui era valida;
* la nuova configurazione viene inserita come nuova riga;
* il vincolo `ex_articoli_componenti_no_overlap` impedisce sovrapposizioni di
  validita' per la stessa coppia prodotto/componente.

---

### Evento trigger

La funzione e' pensata per il trigger:

```sql
trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt
```

su `catalogo.articoli_componenti`, in fase `BEFORE UPDATE OR DELETE`.

---

### Regole

La funzione applica quattro regole principali:

* `DELETE` sempre bloccato: una riga BoM non deve essere eliminata.
* `UPDATE` dei campi di struttura bloccato.
* `UPDATE` del solo `valido_al` ammesso, con controllo che non sia precedente a
  `OLD.valido_dal`.
* `UPDATE` di campi non strutturali ammesso, inclusi `attivo`, `note`, `meta` e
  campi di audit.

---

### Campi strutturali bloccati

Sono considerati parte della struttura della BoM e quindi non modificabili:

| Campo | Motivo |
|-------|--------|
| `coeff_qta` | Cambia il coefficiente quantitativo del componente. |
| `componente_id` | Cambia il componente collegato al prodotto. |
| `obbligatorio` | Cambia la presenza obbligatoria del componente. |
| `esposto_in_fattura` | Cambia il comportamento di esposizione documentale. |
| `partecipa_qta` | Cambia la partecipazione del componente alla quantita'. |
| `determina_qta_padre` | Cambia la derivazione della quantita' del prodotto padre. |
| `valido_dal` | Cambia l'inizio della validita' storica. |
| `validita` | Cambia il range derivato della validita'. |

`validita` e' incluso come controllo di difesa anche se viene ricalcolato dal
trigger dedicato a partire da `valido_dal` e `valido_al`.

---

### Operazioni consentite

| Operazione | Esito |
|------------|-------|
| Inserimento nuova riga BoM | Non gestito da questa funzione; resta consentito se passa gli altri vincoli. |
| Chiusura riga con `UPDATE valido_al = ...` | Consentita se `valido_al` non e' precedente a `OLD.valido_dal`. |
| Aggiornamento di `attivo`, `note`, `meta` | Consentito. |
| Aggiornamento campi audit (`user_update`, `data_update`, `tx_id`) | Consentito. |

---

### Operazioni bloccate

| Operazione | Errore |
|------------|--------|
| `DELETE` della riga | `E_BOM_MODIFICA_VIETATA` |
| Modifica di un campo strutturale | `E_BOM_MODIFICA_VIETATA` |
| `valido_al < OLD.valido_dal` | `E_BOM_VALIDO_AL_INVALIDO` |

Il caso `valido_al = valido_dal` resta coperto dal check tecnico
`chk_articoli_componenti_valid_dates`.

---

### Errori applicativi

| Codice | Quando viene sollevato | Hint operativo |
|--------|------------------------|----------------|
| `E_BOM_MODIFICA_VIETATA` | `DELETE` o modifica di campi strutturali. | Chiudere la riga impostando `valido_al` e inserire una nuova riga. |
| `E_BOM_VALIDO_AL_INVALIDO` | `valido_al` precedente a `OLD.valido_dal`. | Usare una data di chiusura coerente con l'inizio validita'. |

---

### Esempi d'uso operativo

Chiusura corretta di una riga BoM:

```sql
UPDATE catalogo.articoli_componenti
SET valido_al = DATE '2026-04-30'
WHERE id = :articolo_componente_id;
```

Inserimento della nuova versione:

```sql
INSERT INTO catalogo.articoli_componenti (
    prodotto_id,
    componente_id,
    coeff_qta,
    valido_dal,
    obbligatorio
)
VALUES (
    :prodotto_id,
    :componente_id,
    :nuovo_coeff_qta,
    DATE '2026-05-01',
    true
);
```

---

### Dipendenze DB

| Oggetto | Ruolo |
|---------|-------|
| `catalogo.articoli_componenti` | Tabella protetta dalla trigger function. |
| `script.fn_log_and_raise_error` | Gestione standard degli errori applicativi. |
| `ex_articoli_componenti_no_overlap` | Vincolo anti-overlap sulla validita' della BoM. |
| `chk_articoli_componenti_valid_dates` | Check tecnico sulla coerenza delle date. |

---

### Note operative

* La funzione protegge la storia della BoM da correzioni retroattive.
* La modifica di struttura deve sempre produrre una nuova riga, non un update
  della riga esistente.
* Il campo `valido_al` e' il meccanismo previsto per chiudere una versione.
* Le modifiche descrittive o amministrative (`note`, `meta`, `attivo`, audit)
  restano consentite.

---

{% include-markdown "signature-core.md" %}
