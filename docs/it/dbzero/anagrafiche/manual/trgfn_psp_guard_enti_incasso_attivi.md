## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_psp_guard_enti_incasso_attivi`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp) — la tabella su cui il guard è montato
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali d'incasso che nominano il PSP
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp) — il verso opposto: il canale acceso vuole il PSP acceso
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — i canali d'incasso e il PSP

---

### 🎯 Scopo Principale

Un PSP con canali d'incasso accesi non si spegne: prima si spengono i canali, poi il PSP.

---

### Come decide

È montata `BEFORE UPDATE OF attivo` su `anagrafiche.psp` (`trg_psp_a10_guard_enti_incasso_attivi_upd`), e scatta
solo quando il PSP passa da acceso a spento. Conta i canali di `pagamenti.enti_incasso` accesi che nominano il
**ruolo** del PSP: il canale nomina il ruolo, non la riga dei PSP, e ogni canale che nomina un ruolo PSP è un canale
di quel PSP, qualunque sia il suo tipo.

Il legame non è una chiave esterna, perché il ruolo di un canale è polimorfo: per questo il controllo è scritto a
mano e non lo genera l'automazione dello spegnimento.

⚠️ **È `SECURITY DEFINER`.** I canali d'incasso sono sotto row level security, e chi spegne il PSP vede solo i
canali della propria azienda: da invocante il guard lascerebbe spegnere un PSP che un'altra azienda usa. La funzione
conta tutti i canali, ha il `search_path` fissato e risponde solo il rifiuto.

---

### Codici errore

* `E_PSP_ENTI_INCASSO_ATTIVI` (`CONFLITTO_STATO`) — il PSP ha canali d'incasso accesi.

---

### Test

* `db/pgtap/anagrafiche/test-ruoli-impresa-psp-vettore-gestore-v1.sql` — il PSP con un canale acceso non si spegne;
  spento il canale, sì.

---

{% include-markdown "signature-core.md" %}
