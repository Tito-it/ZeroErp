## 📘 Documentazione Concettuale – View `dbops.vw_credenziali_da_sanare`

> 👀 **Vedi anche**
>
> [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) ·
> [dbops.presidi](/dbzero/dbops/tabelle/presidi)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-2)

**Presidio a zero delle credenziali.** Una riga per credenziale da sanare, col motivo:

| Motivo | Che cosa vuol dire | Come si sana |
| --- | --- | --- |
| `NESSUNA_VESTE` | la credenziale non ha alcuna veste, nemmeno spenta: non entra da nessuna porta, e la lista operatori non la mostra più | dandole una veste, o cancellandola (spegnerla in Django non basta) |
| `PERSONA_E_SISTEMA` | vesti di persona e di macchina sulla stessa credenziale: il guard ora le rifiuta, qui escono quelle nate prima o in una gara fra transazioni | separando le due nature su due credenziali |

⭐ **Perimetro (V-3)**: una credenziale con **sole vesti spente** è una persona disattivata,
uno stato legittimo, e **non** entra. `NESSUNA_VESTE` si legge da
`vw_accessi_altri.nessun_accesso`: una regola, non due.

Nel catalogo [dbops.presidi](/dbzero/dbops/tabelle/presidi): `ZERO`, `SETTIMANALE` (non è un
incidente di oggi), `LIBERO` (il conteggio non dipende dalla RLS).

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 14, 15, 17).
