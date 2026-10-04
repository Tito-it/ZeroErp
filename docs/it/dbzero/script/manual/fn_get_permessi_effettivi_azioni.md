## 📘 Documentazione Concettuale – Funzione `script.fn_get_permessi_effettivi_azioni()`

> 👀 **Vedi anche**
>
> **La regola del tetto:** [script.fn_area_consente_azione](/dbzero/script/funzioni/fn_area_consente_azione) · **il minimo dell'azione:** [config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
>
> **Chi la legge:** [script.fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo) · [script.fn_get_user_actions_map](/dbzero/script/funzioni/fn_get_user_actions_map) · il pannello permessi del backend
>
> **La gemella sugli oggetti:** [script.fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti)

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

Risponde, per un operatore e per ogni azione di processo, a: **questa azione la
può eseguire?** E dice anche **perché no**, quando la risposta è no per colpa
dell'area.

È l'unico posto in cui la catena delle azioni è scritta. Il controllo puntuale
del backend, la mappa di `/me/` e il pannello permessi la leggono da qui: non
possono dare risposte diverse.

---

### La catena

1. **Contesto**: se la sessione non è in veste OPERATORE, tutto negato.
2. **Identità**: senza una veste OPERATORE attiva, tutto negato.
3. **Super admin**: tutto abilitato, **prima** del tetto.
4. **Abilitata senza tetto** (`abilitata_specifica`): l'override valido
   dell'utente, altrimenti il profilo
   ([fn_get_permessi_ereditati_azioni](/dbzero/script/funzioni/fn_get_permessi_ereditati_azioni)),
   altrimenti negata.
5. **Il tetto d'area**: l'azione vale solo se il livello dell'operatore
   sull'area dell'azione arriva al minimo dichiarato dall'azione
   (`livello_minimo_area`). Vale qualunque sia la fonte del punto 4, override o
   profilo.

`limitata_da_area` è vera quando il punto 4 dice sì e il punto 5 dice no:
l'override (o il profilo) c'è, ma l'area chiusa lo tiene **dormiente**. Non viene
cancellato: se l'area si riapre (scade un override d'area, cambia il profilo o il
reparto), torna a valere.

---

### Due modi di chiamarla

| Chiamata | Cosa restituisce |
| --- | --- |
| `(utente)` | una riga per ogni azione del catalogo, attive e no |
| `(utente, codename)` | una riga sola, anche per un codename che il catalogo non ha (negata) |

Presidio: `db/pgtap/script/test-permessi-tetto-area-v1.sql` (casi a-c, g-h, e la
sede unica al test 5).

{% include-markdown "signature-core.md" %}
