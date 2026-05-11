## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_componenti_propaga_qta()`

> 👀 **Vedi anche**
>
> [script.trgfn_componenti_calcola_quantita](/dbzero/script/funzioni/trgfn_componenti_calcola_quantita) — complementare: calcola quantita al momento dell'INSERT
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima tabella figli che la usa

Trigger function **AFTER UPDATE OF quantita** sulla riga padre. Quando la quantita della riga padre cambia, aggiorna la `quantita` di tutti i componenti figli attivi come `coeff_qta_snapshot × NEW.quantita`.

---

### 🎯 Scopo Principale

Mantiene la quantita dei componenti allineata alla quantita della riga padre in tempo reale. La quantita di un componente non è un valore libero — è sempre derivata dalla quantita padre moltiplicata per il coefficiente di BoM.

---

### TG_ARGV layout

```
TG_ARGV[0]  schema           (es. 'vendite')
TG_ARGV[1]  tab_figli        (es. 'preventivi_righe_componenti')
TG_ARGV[2]  col FK figli->padre (es. 'riga_preventivo_id')
```

---

### Logica

1. **Guard difensivo**: se `NEW.quantita IS NOT DISTINCT FROM OLD.quantita` → ritorna NULL senza fare nulla (l'`UPDATE OF quantita` già garantisce il cambio, ma il guard protegge da chiamate accidentali).
2. **UPDATE figli**: `quantita = coeff_qta_snapshot × NEW.quantita` su tutti i componenti con `attivo = TRUE` e `<col_fk_padre> = NEW.id`.

---

### Applicazione

Registrata sulla **tabella padre** (es. `vendite.preventivi_righe`):

- Timing: **AFTER UPDATE OF quantita**
- Fase: **`_z90_`** (es. `trg_preventivi_righe_z90_propaga_qta_componenti_upd`)
- Scope: **FOR EACH ROW**
- `UPDATE OF quantita`: efficiente — il trigger non scatta per UPDATE su altre colonne.

Ordine lessicografico: `_z90_propaga_` (`p`) precede `_z90_ricalcola_` (`r`) — la propagazione ai figli avviene prima del ricalcolo dei totali del preventivo (che legge il nuovo prezzo padre aggiornato dai componenti).

---

### Note operative

- Solo figli `attivo = TRUE` vengono aggiornati: i componenti disattivati mantengono la loro quantita storica.
- L'UPDATE sui figli attiva a cascata `_z90_ricalcola_padre` (perché le quantita cambiano ma non i prezzi, il prezzo padre rimane invariato). Questo è corretto: il prezzo padre dipende da `prezzo × coeff`, non da `quantita`.
