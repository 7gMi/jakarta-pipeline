# Jakarta Pipeline — Analyse Sentinel-2 inondations mars 2025

Script Python automatisant le pipeline d'analyse Sentinel-2 L2A appliqué à la
comparaison du 25 octobre 2024 (avant) et du 28 mai 2025 (après) pour la
cartographie des inondations urbaines à Jakarta.

## Contexte

- Cours : Télédétection — M1 G2M Université Paris 8
- Enseignante : Mme Malvina Dupays (IGN)
- Méthodologie : calée sur le TD Burkina Faso
- Auteurs : Mihai Gaina & Ali Tadjer
- Avril 2026

## Pipeline en 7 étapes

1. Rééchantillonnage de la bande SWIR B11 de 20 m à 10 m
2. Concaténation des cinq bandes B2-B3-B4-B8-B11
3. Découpe sur la ROI 40 km centrée sur Jakarta (~1 186 km²)
4. Compositions colorées RGB / IRC / IRC_agri
5. Calcul des cinq indices spectraux (NDVI, NDWI, SAVI, MNDWI, NDBI)
6. Différences temporelles (Δ MNDWI, Δ NDBI)
7. Préparation des entrées pour la classification supervisée OTB

L'étape 8 (classification supervisée Random Forest via Orfeo Toolbox) nécessite
des polygones d'apprentissage tracés manuellement dans QGIS — non automatisée.

## Temps d'exécution

Sur une machine standard (Intel i5, 16 Go RAM, SSD NVMe), l'exécution complète
des sept étapes prend **environ 10 minutes** pour les deux tuiles Sentinel-2
(scène d'octobre 2024 + scène de mai 2025, ~700 Mo chacune avant traitement,
ROI 40 × 40 km après découpe).

Le temps peut varier sensiblement selon :

- la configuration matérielle (SSD vs HDD impact majeur sur les étapes 1–3),
- la taille de la ROI (par défaut 40 km, ajustable via les constantes du script),
- le nombre de bandes/indices à calculer (les étapes 4–5 sont vectorisables).

## Exécution

Depuis la console Python de QGIS Processing :

```python
exec(open("chemin/vers/01_pipeline_7_etapes.py").read())
```

## Dépendances

- QGIS 3.40 Bratislava
- Orfeo Toolbox (OTB)
- Python 3.x avec PyQGIS

## Données d'entrée

Tuiles Sentinel-2 L2A téléchargées depuis Copernicus Data Space Ecosystem :

- `T48MXU_20241025T025811` (25 octobre 2024)
- `T48MXU_20250528T025529` (28 mai 2025)

## Reproductibilité

Le script est paramétrable (constantes en tête de fichier) et peut être
appliqué à tout autre couple de tuiles Sentinel-2 L2A en ajustant les
préfixes et les chemins.
