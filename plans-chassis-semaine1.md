# Robot Bric-à-Brac — Plan de montage Semaine 1
## Châssis Lego grand format (50×35 cm)

### Pièces nécessaires (set EV3 + extras)

| Qté | Pièce | Réf. Lego |
|-----|-------|-----------|
| 4 | Poutre 15 trous | 60484 |
| 6 | Poutre 11 trous | 60483 |
| 8 | Poutre 7 trous | 60485 (ou 32348) |
| 4 | Poutre 3 trous | 60483 |
| 12 | Chevilles longueur 3 (friction) | 6558 |
| 20 | Chevilles longueur 2 (friction) | 2780 |
| 16 | Chevilles longueur 2 (lisses) | 4274 |
| 8 | Équerres 3×5 | 32013 |
| 6 | Croix bloc 2×2 | 87407 |
| 2 | Moteur large EV3 | 95648 |
| 2 | Roue EV3 (81.6×15 mm) | 64712 |
| 1 | Roue folle / bille | extras |
| 1 | Plaque 11×17 | 37301 (ou assembler plusieurs plaques) |
| 4 | Axe 5 modules | 32073 |
| 2 | Axe 7 modules | 44294 |
| 2 | Engrenage 24 dents | 3648 |
| 2 | Manchon | 32474 |

---

### Étape 1 — Base rectangulaire (5 min)

1. Prendre **2 poutres de 15 trous** et **2 poutres de 11 trous**.
2. Les assembler en rectangle avec des **chevilles friction** aux coins :
   - Les poutres de 15 sont les grands côtés (longueur).
   - Les poutres de 11 sont les petits côtés (largeur).
   - Utiliser les trous 1 et 15 des poutres de 15, et 1 et 11 des poutres de 11.
3. Ajouter **3 poutres de 11** en travers au milieu (trous 4, 8, 12 des poutres de 15).
   - Fixer avec chevilles friction aux 2 extrémités.
   - Ces traverses rigidifient le châssis et serviront d'accroche pour les moteurs.

```
    ┌──── 15 trous ────┐
    │                  │
    11 ─ ─ ─ ─ ─ ─ ─ 11  (traverses)
    │                  │
    └──── 15 trous ────┘
```

### Étape 2 — Renforts diagonaux (5 min)

1. Pour rigidifier, ajouter des **poutres de 7 trous** en diagonale dans chaque coin.
   - Fixer avec chevilles friction.
   - Chaque diagonale relie un coin à la traverse la plus proche.

### Étape 3 — Supports moteur (10 min)

1. Prendre **2 poutres de 7 trous**.
2. Les fixer perpendiculairement à la traverse centrale (trous 5–6), espacées de la largeur des moteurs EV3.
3. Fixer les **moteurs EV3** debout (verticalement) sur ces supports avec des chevilles.
   - Les moteurs regardent vers l'extérieur du châssis.
   - L'axe de sortie est horizontal, à environ 1 cm du sol.

### Étape 4 — Transmission (5 min)

1. Sur chaque moteur, enfiler un **engrenage 24 dents** sur l'axe de sortie.
2. Fixer un **axe de 5 modules** avec un **manchon** de l'autre côté de l'engrenage.
3. Emboîter la **roue EV3** à l'extrémité.

### Étape 5 — Roue folle (5 min)

1. À l'opposé des moteurs (à l'avant du robot), fixer une **roue folle** ou une **bille**.
   - Utiliser 2 poutres de 3 trous pour faire un support triangulaire.
   - La bille doit être à la même hauteur que les roues motrices.

### Étape 6 — Pont supérieur (10 min)

1. Prendre **4 poutres de 15 trous**.
2. Les fixer verticalement (en colonne) aux 4 coins du châssis avec des chevilles.
   - Hauteur : 2 trous au-dessus du châssis (≈ 3 cm).
3. Poser la **plaque 11×17** (ou assemblage de plaques) dessus pour former le plancher du 1er étage.
   - Fixer avec des chevilles lisses.

### Étape 7 — Fixation RPi4 (10 min)

1. Sur le pont supérieur, fixer **4 poutres de 3 trous** verticalement aux coins de la zone RPi.
2. Poser le RPi4 dessus (sur ses entretoises si tu en as, ou sur 4 chevilles lisses en Lego).
3. Maintenir avec des élastiques ou un ruban Velcro — pas définitif, on améliorera plus tard.

### Étape 8 — Laser range finder

1. Fixer le laser sur une **poutre de 7 trous** montée verticalement à l'avant droit du pont supérieur.
2. Le laser doit dépasser du châssis pour avoir un champ libre.

---

### Vue d'ensemble finale

```
        ┌─── RPi4 ───┐
        │            │
   ════╪════════════╪════  ← Laser
   ║   │            │   ║
   ║   │  plaques   │   ║
   ║   │  (pont)    │   ║
   ║   └────────────┘   ║
   ║                    ║
   ╟── ════════════ ────╢  ← Traverses
   ║   ┌────  ────┐    ║
   ║   │  Moteur  │    ║
   ║   └────  ────┘    ║
   ║                    ║
   ╟── ════════════ ────╢
   ║                    ║
   └─────  roue  ───────┘
         ●        ●
```

### Prochaine étape : câblage et premier test

Une fois le châssis monté, on branche :
- Moteurs EV3 → RPi4 via un adaptateur (ou brique EV3 → RPi4)
- Laser → GPIO du RPi4
- Alimentation du RPi4 (batterie Lego ou power bank)

On code un `robot.py` qui fait avancer / reculer / tourner.