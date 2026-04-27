"""
PIPELINE ANALYSE INONDATIONS JAKARTA — Sentinel-2 L2A
Comparaison 25 octobre 2024 (AVANT) vs 28 mai 2025 (APRÈS)
Méthodologie : TD Burkina Faso (Prof Malvian Dupayas, IGN)

Étapes 1-7 automatiques (la 8 = classification supervisée, nécessite training polygons manuels)

USAGE : dans la Console Python QGIS, coller :
    exec(open("C:/tmp_qgis/jakarta_pipeline.py").read())
"""

import os
import processing
from qgis.core import QgsProject, QgsRasterLayer

# ============================================================
# CONFIG — chemins et paramètres
# ============================================================
PROJ_ROOT = "F:/Projets_Télédéction/Analyse_Inondations_Jakarta"
IN_D1 = f"{PROJ_ROOT}/INPUT/25 octobre 2024"
IN_D2 = f"{PROJ_ROOT}/INPUT/28 mai 2025"
OUT = f"{PROJ_ROOT}/OUTPUT_2026-04-21"

# Noms de fichiers INPUT (préfixe T48MXU_20XXXXXX)
D1_PREFIX = "T48MXU_20241025T025811"
D2_PREFIX = "T48MXU_20250528T025529"
D1_LABEL = "24oct"  # label court pour noms de sortie
D2_LABEL = "28mai"

# Bandes Sentinel-2 utilisées (convention TD Burkina)
BANDS_10M = {"B02": "Blue", "B03": "Green", "B04": "Red", "B08": "NIR"}
BANDS_20M = {"B11": "SWIR1"}

# ROI : on réutilise l'extent du 40km existant (convertie au ROI commun)
# L'extent sera extrait dynamiquement du fichier ROI_Jakarta_28mai_40Km.tif existant
REF_ROI = f"{PROJ_ROOT}/OUTPUT/3_ROI_Extrait/ROI_Jakarta_28mai_40Km.tif"

project = QgsProject.instance()


def log(msg):
    print(f">>> {msg}")


def band_path(in_dir, prefix, band):
    """Retourne le chemin JP2 d'une bande."""
    if band == "B11":
        return f"{in_dir}/{prefix}_{band}_20m.jp2"
    return f"{in_dir}/{prefix}_{band}_10m.jp2"


def add_layer(path, name, group_name=None):
    """Ajoute une couche raster au projet."""
    lyr = QgsRasterLayer(path, name)
    if lyr.isValid():
        project.addMapLayer(lyr, addToLegend=True)
        return lyr
    else:
        log(f"[ERREUR] Impossible d'ajouter {name} ({path})")
        return None


# ============================================================
# ÉTAPE 1 — Rééchantillonnage B11 20m → 10m
# ============================================================
log("=" * 60)
log("ÉTAPE 1 — Rééchantillonnage B11 20m -> 10m")
log("=" * 60)

reech_out = {
    D1_LABEL: f"{OUT}/1_Reechantillonnage/{D1_LABEL}_B11_10m.tif",
    D2_LABEL: f"{OUT}/1_Reechantillonnage/{D2_LABEL}_B11_10m.tif",
}

for label, in_dir, prefix in [(D1_LABEL, IN_D1, D1_PREFIX), (D2_LABEL, IN_D2, D2_PREFIX)]:
    src = band_path(in_dir, prefix, "B11")
    dst = reech_out[label]
    # Utiliser la résolution de B02 (10m) comme référence
    ref_10m = band_path(in_dir, prefix, "B02")
    if not os.path.exists(src):
        log(f"[SKIP] Source manquante : {src}")
        continue
    log(f"Rééchantillonnage {label} B11 -> 10m")
    processing.run("gdal:warpreproject", {
        'INPUT': src,
        'TARGET_CRS': None,  # garde CRS d'entrée
        'RESAMPLING': 1,  # bilinear
        'TARGET_RESOLUTION': 10,
        'OUTPUT': dst,
    })
    log(f"  -> {dst}")

# ============================================================
# ÉTAPE 2 — Concaténation B234811 (5 bandes)
# ============================================================
log("=" * 60)
log("ÉTAPE 2 — Concaténation B234811 (5 bandes)")
log("=" * 60)

concat_out = {
    D1_LABEL: f"{OUT}/2_Concatenation_Bandes/{D1_LABEL}_B234811.tif",
    D2_LABEL: f"{OUT}/2_Concatenation_Bandes/{D2_LABEL}_B234811.tif",
}

for label, in_dir, prefix in [(D1_LABEL, IN_D1, D1_PREFIX), (D2_LABEL, IN_D2, D2_PREFIX)]:
    # Ordre classique TD Burkina : B2, B3, B4, B8, B11
    bands_in_order = [
        band_path(in_dir, prefix, "B02"),
        band_path(in_dir, prefix, "B03"),
        band_path(in_dir, prefix, "B04"),
        band_path(in_dir, prefix, "B08"),
        reech_out[label],  # B11 rééchantillonné
    ]
    if not all(os.path.exists(b) for b in bands_in_order):
        log(f"[SKIP] Bandes manquantes pour {label}")
        continue
    dst = concat_out[label]
    log(f"Concat B234811 {label}")
    processing.run("gdal:merge", {
        'INPUT': bands_in_order,
        'PCT': False,
        'SEPARATE': True,  # IMPORTANT : bandes séparées
        'OUTPUT': dst,
    })
    log(f"  -> {dst}")

# ============================================================
# ÉTAPE 3 — ROI (découpe zone Jakarta)
# ============================================================
log("=" * 60)
log("ÉTAPE 3 — ROI Jakarta (40 km, extent commun)")
log("=" * 60)

roi_out = {
    D1_LABEL: f"{OUT}/3_ROI/{D1_LABEL}_ROI_B234811.tif",
    D2_LABEL: f"{OUT}/3_ROI/{D2_LABEL}_ROI_B234811.tif",
}

# Récupérer l'extent de référence du ROI 40 km existant
from osgeo import gdal
ref_ds = gdal.Open(REF_ROI)
gt = ref_ds.GetGeoTransform()
xmin = gt[0]
ymax = gt[3]
xmax = xmin + gt[1] * ref_ds.RasterXSize
ymin = ymax + gt[5] * ref_ds.RasterYSize
log(f"Extent ROI (EPSG:32748 UTM 48S) : [{xmin:.0f}, {ymin:.0f}, {xmax:.0f}, {ymax:.0f}]")
log(f"Dimensions ROI : {xmax-xmin:.0f} m x {ymax-ymin:.0f} m")
ref_ds = None

extent_str = f"{xmin},{xmax},{ymin},{ymax} [EPSG:32748]"

for label in [D1_LABEL, D2_LABEL]:
    src = concat_out[label]
    dst = roi_out[label]
    if not os.path.exists(src):
        log(f"[SKIP] Concat manquant pour {label}")
        continue
    log(f"Découpe ROI {label}")
    processing.run("gdal:cliprasterbyextent", {
        'INPUT': src,
        'PROJWIN': extent_str,
        'NODATA': None,
        'OPTIONS': '',
        'OUTPUT': dst,
    })
    log(f"  -> {dst}")

# ============================================================
# ÉTAPE 4 — Compositions colorées (RGB + IRC + IRC_agriculture)
# ============================================================
log("=" * 60)
log("ÉTAPE 4 — Compositions colorées (pour visualisation)")
log("=" * 60)

# Dans B234811 concat : bande 1=B2, 2=B3, 3=B4, 4=B8, 5=B11
# RGB vraie couleur : B4, B3, B2 -> bandes 3, 2, 1
# IRC (infrarouge classique) : B8, B4, B3 -> bandes 4, 3, 2
# IRC agriculture : B11, B8, B4 -> bandes 5, 4, 3

# Les compositions colorées peuvent se faire dans QGIS via setRenderer,
# mais pour générer des fichiers autonomes on utilise gdal_translate avec
# sélection de bandes.

def extract_3bands(src, dst, bands_order):
    """Extrait 3 bandes dans l'ordre donné."""
    processing.run("gdal:translate", {
        'INPUT': src,
        'OPTIONS': f"-b {bands_order[0]} -b {bands_order[1]} -b {bands_order[2]}",
        'OUTPUT': dst,
    })


for label in [D1_LABEL, D2_LABEL]:
    src = roi_out[label]
    if not os.path.exists(src):
        continue
    rgb = f"{OUT}/4_Compositions/{label}_RGB_B432.tif"
    irc = f"{OUT}/4_Compositions/{label}_IRC_B843.tif"
    irc_agri = f"{OUT}/4_Compositions/{label}_IRC_agri_B1184.tif"
    log(f"Compositions {label}")
    extract_3bands(src, rgb, [3, 2, 1])
    extract_3bands(src, irc, [4, 3, 2])
    extract_3bands(src, irc_agri, [5, 4, 3])
    log(f"  -> RGB, IRC, IRC_agri")

# ============================================================
# ÉTAPE 5 — Indices (NDVI, NDWI, SAVI, MNDWI, NDBI)
# ============================================================
log("=" * 60)
log("ÉTAPE 5 — Indices (5 indices x 2 dates = 10 rasters)")
log("=" * 60)


def compute_index(src_concat, formula, out_path, label_idx):
    """Calcule un indice via Raster Calculator GDAL.
    src_concat : raster 5 bandes (B2,B3,B4,B8,B11)
    Les bandes sont nommées A, B, C, D, E dans gdal_calc
    """
    log(f"  {label_idx} : {formula}")
    processing.run("gdal:rastercalculator", {
        'INPUT_A': src_concat, 'BAND_A': 1,  # B2
        'INPUT_B': src_concat, 'BAND_B': 2,  # B3
        'INPUT_C': src_concat, 'BAND_C': 3,  # B4
        'INPUT_D': src_concat, 'BAND_D': 4,  # B8
        'INPUT_E': src_concat, 'BAND_E': 5,  # B11
        'FORMULA': formula,
        'NO_DATA': None,
        'RTYPE': 5,  # Float32
        'OPTIONS': '',
        'EXTRA': '',
        'OUTPUT': out_path,
    })


# Formules (sur raster concat 5 bandes : A=B2, B=B3, C=B4, D=B8, E=B11)
INDICES = {
    "NDVI": "(D.astype(float) - C) / (D + C + 1e-10)",       # (NIR-Red)/(NIR+Red)
    "NDWI": "(B.astype(float) - D) / (B + D + 1e-10)",       # (Green-NIR)/(Green+NIR)
    "SAVI": "(D.astype(float) - C) * 1.5 / (D + C + 0.5)",   # (NIR-Red)*1.5/(NIR+Red+0.5)
    "MNDWI": "(B.astype(float) - E) / (B + E + 1e-10)",      # (Green-SWIR1)/(Green+SWIR1)
    "NDBI": "(E.astype(float) - D) / (E + D + 1e-10)",       # (SWIR1-NIR)/(SWIR1+NIR)
}

indices_out = {}  # indices_out[label][idx_name] = path
for label in [D1_LABEL, D2_LABEL]:
    src = roi_out[label]
    if not os.path.exists(src):
        continue
    indices_out[label] = {}
    for idx_name, formula in INDICES.items():
        dst = f"{OUT}/5_Indices/{label}_{idx_name}.tif"
        compute_index(src, formula, dst, f"{label} {idx_name}")
        indices_out[label][idx_name] = dst

# ============================================================
# ÉTAPE 6 — Différences temporelles (après - avant)
# ============================================================
log("=" * 60)
log("ÉTAPE 6 — Différences temporelles (28mai - 24oct)")
log("=" * 60)

diffs_out = {}
for idx_name in INDICES.keys():
    src_before = indices_out[D1_LABEL][idx_name]
    src_after = indices_out[D2_LABEL][idx_name]
    dst = f"{OUT}/6_Differences/DIFF_{idx_name}.tif"
    log(f"DIFF {idx_name} = {D2_LABEL} - {D1_LABEL}")
    processing.run("gdal:rastercalculator", {
        'INPUT_A': src_after, 'BAND_A': 1,
        'INPUT_B': src_before, 'BAND_B': 1,
        'FORMULA': "A - B",
        'NO_DATA': None,
        'RTYPE': 5,  # Float32
        'OUTPUT': dst,
    })
    diffs_out[idx_name] = dst

# ============================================================
# ÉTAPE 7 — Concaténation finale (pour classification)
# ============================================================
log("=" * 60)
log("ÉTAPE 7 — Concaténation finale (stack pour classification)")
log("=" * 60)

# Stack pertinent pour classification : bandes des 2 dates + indices clés + différences
# Total : 5 bandes x 2 dates + NDVI x 2 + NDWI x 2 + MNDWI x 2 + NDBI x 2 + 5 différences = 23 bandes
stack_list = [
    roi_out[D1_LABEL],  # 5 bandes date 1
    roi_out[D2_LABEL],  # 5 bandes date 2
    indices_out[D1_LABEL]["NDVI"],
    indices_out[D2_LABEL]["NDVI"],
    indices_out[D1_LABEL]["NDWI"],
    indices_out[D2_LABEL]["NDWI"],
    indices_out[D1_LABEL]["MNDWI"],
    indices_out[D2_LABEL]["MNDWI"],
    indices_out[D1_LABEL]["NDBI"],
    indices_out[D2_LABEL]["NDBI"],
    diffs_out["NDVI"],
    diffs_out["NDWI"],
    diffs_out["MNDWI"],
    diffs_out["NDBI"],
    diffs_out["SAVI"],
]

stack_out = f"{OUT}/7_Concatenation_Finale/STACK_final_classification.tif"
log("Stack final : 5+5 bandes spectrales + 10 indices + 5 diffs = 25 bandes")
processing.run("gdal:merge", {
    'INPUT': stack_list,
    'PCT': False,
    'SEPARATE': True,
    'OUTPUT': stack_out,
})
log(f"  -> {stack_out}")

# ============================================================
# AJOUTER LES COUCHES CLÉS AU PROJET QGIS
# ============================================================
log("=" * 60)
log("Ajout des couches clés au projet QGIS...")
log("=" * 60)

# Compositions colorées (pour visualisation)
for label in [D1_LABEL, D2_LABEL]:
    add_layer(f"{OUT}/4_Compositions/{label}_RGB_B432.tif", f"{label}_RGB_B432")
    add_layer(f"{OUT}/4_Compositions/{label}_IRC_B843.tif", f"{label}_IRC_B843")

# Indices pour les 2 dates
for label in [D1_LABEL, D2_LABEL]:
    for idx_name in INDICES.keys():
        add_layer(f"{OUT}/5_Indices/{label}_{idx_name}.tif", f"{label}_{idx_name}")

# Différences
for idx_name in INDICES.keys():
    add_layer(f"{OUT}/6_Differences/DIFF_{idx_name}.tif", f"DIFF_{idx_name}")

# Stack final
add_layer(stack_out, "STACK_final_25bandes")

# Sauvegarder projet
project.write()

log("=" * 60)
log("✅ PIPELINE TERMINÉ !")
log("=" * 60)
log(f"Résultats : {OUT}/")
log("Étape suivante = Étape 8 : Classification supervisée")
log("  1. Créer training.shp avec polygones de chaque classe (Eau, Végétation, Urbain, Autre)")
log("  2. Lancer OTB TrainImagesClassifier (Processing > OTB)")
log("  3. Puis OTB ImageClassifier pour appliquer au raster STACK")
